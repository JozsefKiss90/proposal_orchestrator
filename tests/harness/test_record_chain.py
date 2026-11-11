"""
The DN record chain (overhaul ticket 05): one way to load a record against its
predecessors on disk.

Four groups:

* Refusals: a predecessor whose bytes moved is refused, naming the record, the
  predecessor and both hashes; a record whose type or flags are wrong is
  refused with its kind's own error class.
* The chain end to end: preflight, blind report, blind baseline, integrity
  audit, ESR comparison, operator review and comparison diff, untouched, load.
* Records written before the ticket: the committed comparisons and diffs load
  while their predecessors are unchanged.
* Writing: the next numbered path, atomically, with its file hash.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import harness.blind_baseline as bb
import harness.commands.blind_assessment as cmd
import harness.comparison_diff as cd
import harness.esr_comparison as ec
import harness.integrity_audit as ia
import harness.operator_review as orv
import harness.record_chain as rc
from harness.blind_assessment import BlindAssessmentError, candidate_hash, load_candidate, load_report
from harness.content_hash import file_hash, short_hash
from harness.evidence_preflight import load_preflight
from runner.paths import find_repo_root
from tests.harness.test_blind_baseline import _write_json, bundle, world  # noqa: F401 - fixtures
from tests.harness.test_blind_leakage import FROZEN
from tests.harness.test_comparison_diff import (  # noqa: F401 - fixtures
    _fork_dispositions,
    _write_comparison,
    loaded,
    pair,
)
from tests.harness.test_esr_comparison import (  # noqa: F401 - fixtures
    _compare,
    _rewrite,
    _row,
    frozen_world,
    inputs,
)
from tests.harness.test_operator_review import _notes

REPO = find_repo_root()
DN = REPO / "docs/tier4_orchestration_state/msca_dn"


def _edit_json(path: Path, mutate) -> tuple[str, str]:
    """Edit a JSON file in place; return its file hash before and after."""
    before = file_hash(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    mutate(data)
    _write_json(path, data)
    return before, file_hash(path)


def _names_both(message: str, recorded: str, actual: str) -> None:
    assert recorded != actual
    assert short_hash(recorded) in message
    assert short_hash(actual) in message


# --------------------------------------------------------------------------- #
# The four refusals the ticket names
# --------------------------------------------------------------------------- #


class TestAMovedPredecessorIsRefused:
    def test_a_diff_over_a_pair_whose_shared_baseline_report_moved_is_refused(self, inputs, pair):
        before, after = pair
        copy = inputs["frozen"].copy_path
        recorded, actual = _edit_json(copy, lambda d: d.__setitem__("edited", True))
        for path, what in ((before, "predecessor"), (after, "successor")):
            with pytest.raises(BlindAssessmentError) as exc:
                cd.load_pair_member(path, what=what)
            message = str(exc.value)
            assert "the baseline report" in message
            assert path.name in message
            _names_both(message, recorded, actual)

    def test_the_diff_command_refuses_the_pair_and_writes_nothing(self, inputs, pair, capsys):
        before, after = pair
        _edit_json(inputs["frozen"].copy_path, lambda d: d.__setitem__("edited", True))
        out = inputs["world"] / "diffs"
        code = cmd.main(
            [
                "diff", "--before", str(before), "--after", str(after),
                "--repo-root", str(inputs["world"]),
                "--profile", str(inputs["bundle"].profile.source_path),
                "--out-dir", str(out),
            ],
            clock=lambda: FROZEN,
        )
        assert code == 2
        assert "the baseline report" in capsys.readouterr().err
        assert not out.exists()

    def test_a_diff_whose_member_revisions_artifact_moved_is_refused(self, inputs, loaded):
        before, after = loaded
        out = inputs["world"] / "diffs"
        written, _ = cd.write_diff(cd.diff_comparisons(before, after, clock=lambda: FROZEN), out)
        recorded, actual = _edit_json(
            after.revisions_path, lambda d: d["open"].reverse()
        )
        with pytest.raises(cd.ComparisonDiffError) as exc:
            cd.load_diff(written)
        message = str(exc.value)
        assert "the successor revisions artifact" in message
        assert written.name in message
        _names_both(message, recorded, actual)

    def test_a_pair_whose_revisions_artifact_is_bound_elsewhere_is_refused(self, loaded):
        """A comparison records no hash of its revisions artifact, so the run
        checks what the artifact itself binds: the same baseline, ESR record
        and dispositions as the comparison beside it."""
        _, after = loaded
        _edit_json(after.revisions_path, lambda d: d.__setitem__("dispositions_sha256", "0" * 64))
        with pytest.raises(cd.ComparisonDiffError, match="revisions artifact"):
            cd.load_pair_member(after.path, what="successor")

    def test_loading_a_comparison_whose_esr_record_moved_is_refused(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        comparison = next(out.glob("comparison_*.json"))
        recorded, actual = _edit_json(
            inputs["esr"], lambda d: d["observations"][0].__setitem__("text", "Reworded.")
        )
        with pytest.raises(ec.EsrComparisonError) as exc:
            ec.load_comparison(comparison)
        message = str(exc.value)
        assert "the ESR record" in message
        assert comparison.name in message
        _names_both(message, recorded, actual)

    def test_loading_a_comparison_whose_dispositions_moved_is_refused(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        comparison = next(out.glob("comparison_*.json"))
        recorded, actual = _edit_json(
            inputs["dispositions"], lambda d: d.__setitem__("declared_on", "2026-10-08")
        )
        with pytest.raises(ec.EsrComparisonError) as exc:
            ec.load_comparison(comparison)
        assert "the dispositions" in str(exc.value)
        _names_both(str(exc.value), recorded, actual)

    def test_loading_a_comparison_whose_register_moved_is_refused(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        comparison = next(out.glob("comparison_*.json"))
        recorded, actual = _edit_json(inputs["register"], lambda d: d.__setitem__("edited", True))
        with pytest.raises(ec.EsrComparisonError) as exc:
            ec.load_comparison(comparison)
        assert "the fidelity register" in str(exc.value)
        _names_both(str(exc.value), recorded, actual)

    def test_loading_a_comparison_whose_audit_moved_is_refused(self, inputs):
        digest = candidate_hash(load_candidate(inputs["candidate"], inputs["bundle"].profile))
        audit = _write_json(inputs["world"] / "audits" / "a.json", {
            "record_type": ia.AUDIT_RECORD_TYPE, "advisory": True, "blocking": False,
            "candidate_hash": digest, "profile_version": "x",
            "checks": [{"check_id": "x", "findings": []}], "grounding": {}, "baseline": {},
        })
        code, out = _compare(inputs, "--audit", "audits/a.json")
        assert code == 0
        comparison = next(out.glob("comparison_*.json"))
        assert ec.load_comparison(comparison)["audits"][0]["path"] == "audits/a.json"
        recorded, actual = _edit_json(audit, lambda d: d.__setitem__("profile_version", "y"))
        with pytest.raises(ec.EsrComparisonError) as exc:
            ec.load_comparison(comparison)
        assert "an integrity audit" in str(exc.value)
        _names_both(str(exc.value), recorded, actual)

    def test_a_missing_predecessor_is_refused_by_name(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        comparison = next(out.glob("comparison_*.json"))
        inputs["esr"].unlink()
        with pytest.raises(ec.EsrComparisonError, match="the ESR record .* not a file"):
            ec.load_comparison(comparison)


class _OwnError(Exception):
    """A kind's own error class, unrelated to any harness base."""


_OWN_KIND = rc.RecordKind(
    name="synthetic record", record_type="synthetic_record", error=_OwnError, prefix="synthetic"
)


class TestTheKindsOwnErrorClass:
    @pytest.mark.parametrize(
        "change",
        [
            {"record_type": "something_else"},
            {"advisory": False},
            {"blocking": True},
            {"advisory": "true"},
        ],
        ids=["record_type", "advisory", "blocking", "advisory_not_a_bool"],
    )
    def test_a_wrong_type_or_flag_is_refused_with_the_kinds_error(self, tmp_path, change):
        good = {"record_type": "synthetic_record", "advisory": True, "blocking": False}
        path = _write_json(tmp_path / "r.json", {**good, **change})
        with pytest.raises(_OwnError) as exc:
            rc.load_record(_OWN_KIND, path)
        assert type(exc.value) is _OwnError

    @pytest.mark.parametrize(
        "load, error, record_type",
        [
            (ec.load_comparison, ec.EsrComparisonError, ec.COMPARISON_RECORD_TYPE),
            (cd.load_diff, cd.ComparisonDiffError, cd.DIFF_RECORD_TYPE),
        ],
        ids=["comparison", "diff"],
    )
    @pytest.mark.parametrize(
        "change",
        [{"record_type": "other"}, {"advisory": False}, {"blocking": True}],
        ids=["record_type", "advisory", "blocking"],
    )
    def test_the_comparison_and_the_diff_refuse_with_their_own_class(
        self, tmp_path, load, error, record_type, change
    ):
        path = _write_json(
            tmp_path / "r.json",
            {"record_type": record_type, "advisory": True, "blocking": False, **change},
        )
        with pytest.raises(error) as exc:
            load(path)
        assert type(exc.value) is error

    def test_a_file_that_is_not_json_is_refused_with_the_kinds_error(self, tmp_path):
        path = tmp_path / "r.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(_OwnError, match="not valid JSON"):
            rc.load_record(_OWN_KIND, path)


# --------------------------------------------------------------------------- #
# The chain end to end
# --------------------------------------------------------------------------- #


class TestAnUntouchedChainLoads:
    def test_preflight_report_baseline_audit_comparison_review_diff(self, inputs):
        world, bundle_ = inputs["world"], inputs["bundle"]
        profile = bundle_.profile

        (preflight,) = (world / "reports_preflight").glob("preflight_*.json")
        assert load_preflight(preflight)["record_type"]
        (report,) = (world / "reports").glob("blind_*.json")
        frozen = bb.load_frozen_baseline(inputs["baseline"])
        assert load_report(report, inputs["candidate"], profile)["candidate_hash"] == (
            frozen.record["bindings"]["candidate_hash"]
        )
        assert file_hash(report) == frozen.record["report_sha256"]

        audits = world.parent / "audits"
        code = cmd.main(
            ["audit", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(audits),
             "--repo-root", str(world), "--profile", str(profile.source_path)],
            clock=lambda: FROZEN,
        )
        assert code in (0, 1)
        (audit,) = audits.glob("integrity_*.json")
        assert ia.load_audit(audit)["candidate_hash"] == frozen.record["bindings"]["candidate_hash"]

        before = _write_comparison(inputs, "before")
        data = ec.load_comparison(before)
        assert data["baseline"]["report_sha256"] == frozen.record["report_sha256"]

        notes = _write_json(world / "docs" / "review" / "notes.json", _notes(file_hash(before)))
        reviews = world / "reviews"
        code = cmd.main(
            ["review", "--comparison", str(before), "--notes", str(notes),
             "--repo-root", str(world), "--profile", str(profile.source_path),
             "--out-dir", str(reviews)],
            clock=lambda: FROZEN,
        )
        assert code in (0, 1)
        assert list(reviews.glob("operator_review_*.md"))
        assert orv.load_review_notes(notes).comparison_sha256 == file_hash(before)

        _fork_dispositions(inputs, "after")
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(explanation="Reworded by the review."))
        after = _write_comparison(inputs, "after")
        diffs = world / "diffs"
        written, _ = cd.write_diff(
            cd.diff_comparisons(
                cd.load_pair_member(before, what="predecessor"),
                cd.load_pair_member(after, what="successor"),
                repo_root=world,
                clock=lambda: FROZEN,
            ),
            diffs,
        )
        diff = cd.load_diff(written)
        assert diff["predecessor"]["comparison_sha256"] == file_hash(before)
        assert diff["successor"]["comparison_sha256"] == file_hash(after)
        assert diff["rows_changed"] == 1


# --------------------------------------------------------------------------- #
# Records written before this ticket
# --------------------------------------------------------------------------- #


_COMMITTED_COMPARISONS = sorted((DN / "comparisons").glob("comparison_*.json"))
_COMMITTED_DIFFS = sorted((DN / "comparisons").glob("review_diff_*.json"))


@pytest.mark.skipif(not _COMMITTED_COMPARISONS, reason="no committed comparison")
class TestRecordsWrittenBeforeTheTicket:
    @pytest.mark.parametrize("path", _COMMITTED_COMPARISONS, ids=lambda p: p.name)
    def test_a_committed_comparison_loads(self, path):
        data = ec.load_comparison(path)
        assert data["record_type"] == ec.COMPARISON_RECORD_TYPE
        member = cd.load_pair_member(path, what="successor")
        assert member.sha256 == file_hash(path)

    @pytest.mark.parametrize("path", _COMMITTED_DIFFS, ids=lambda p: p.name)
    def test_a_committed_diff_loads(self, path):
        assert cd.load_diff(path)["record_type"] == cd.DIFF_RECORD_TYPE

    def test_a_committed_comparison_copied_elsewhere_resolves_under_an_explicit_root(self, tmp_path):
        path = _COMMITTED_COMPARISONS[0]
        copy = tmp_path / path.name
        shutil.copyfile(path, copy)
        assert ec.load_comparison(copy, repo_root=REPO)["record_type"] == ec.COMPARISON_RECORD_TYPE


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #


class TestWriting:
    def _record(self) -> dict:
        return {"record_type": "synthetic_record", "advisory": True, "blocking": False, "n": 1}

    def test_the_next_numbered_path_and_its_file_hash(self, tmp_path):
        digest = "sha256:" + "ab" * 32
        first = rc.write_record(_OWN_KIND, self._record(), tmp_path, digest=digest)
        second = rc.write_record(_OWN_KIND, self._record(), tmp_path, digest="ab" * 32)
        assert first.path.name == f"synthetic_{'ab' * 6}_0001.json"
        assert second.path.name == f"synthetic_{'ab' * 6}_0002.json"
        assert first.sha256 == file_hash(first.path)
        assert rc.load_record(_OWN_KIND, first.path).data == self._record()

    def test_the_record_can_name_its_own_path(self, tmp_path):
        written = rc.write_record(
            _OWN_KIND, self._record(), tmp_path, digest="cd" * 32,
            complete=lambda target: {**self._record(), "writes": [target.name]},
        )
        assert rc.load_record(_OWN_KIND, written.path).data["writes"] == [written.path.name]

    @pytest.mark.parametrize("change", [{"record_type": "other"}, {"blocking": True}])
    def test_a_record_of_another_kind_is_not_written(self, tmp_path, change):
        with pytest.raises(_OwnError):
            rc.write_record(_OWN_KIND, {**self._record(), **change}, tmp_path, digest="ef" * 32)
        assert not list(tmp_path.iterdir())
