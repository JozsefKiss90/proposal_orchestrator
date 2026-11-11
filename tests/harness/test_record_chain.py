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
import re
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
from harness.blind_assessment import (
    BlindAssessmentError,
    CandidateHashMismatch,
    candidate_hash,
    load_candidate,
    load_report,
)
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


# --------------------------------------------------------------------------- #
# Ticket 06: every link loads through the chain module
# --------------------------------------------------------------------------- #


def _sole(directory: Path, pattern: str) -> Path:
    (found,) = directory.glob(pattern)
    return found


def _edit_candidate(candidate: Path) -> None:
    section = next(Path(candidate).glob("*.json"))
    data = json.loads(section.read_text(encoding="utf-8"))
    data["sub_sections"][0]["content"] += " An added sentence."
    _write_json(section, data)


class TestTheTicket06Refusals:
    """The two refusals ticket 06 names. Both already refused before the
    ticket, so they are characterisations of the behaviour the chain keeps."""

    def test_an_audit_over_a_baseline_whose_frozen_report_was_edited_is_refused(
        self, inputs, capsys
    ):
        world, bundle_ = inputs["world"], inputs["bundle"]
        copy = inputs["frozen"].copy_path
        recorded, actual = _edit_json(copy, lambda d: d.__setitem__("edited", True))
        with pytest.raises(ia.IntegrityAuditError) as exc:
            ia.bind_baseline(
                inputs["baseline"], candidate_digest="sha256:" + "0" * 64, snapshot_id=""
            )
        message = str(exc.value)
        assert "the frozen report copy" in message
        assert copy.name in message
        _names_both(message, recorded, actual)

        audits = world.parent / "audits"
        code = cmd.main(
            ["audit", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(audits),
             "--repo-root", str(world), "--profile", str(bundle_.profile.source_path),
             "--baseline-dir", str(inputs["baseline"])],
            clock=lambda: FROZEN,
        )
        assert code == 2
        assert "the frozen report copy" in capsys.readouterr().err
        assert not list(audits.glob("integrity_*.json")) if audits.is_dir() else True

    def test_an_operator_review_over_a_comparison_whose_candidate_moved_is_refused(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        comparison = _sole(out, "comparison_*.json")
        profile = inputs["bundle"].profile
        recorded = candidate_hash(load_candidate(inputs["candidate"], profile))
        _edit_candidate(inputs["candidate"])
        actual = candidate_hash(load_candidate(inputs["candidate"], profile))
        with pytest.raises(orv.OperatorReviewError) as exc:
            orv.resolve_inputs(comparison, repo_root=inputs["world"], profile=profile)
        assert type(exc.value) is orv.OperatorReviewError
        _names_both(str(exc.value), recorded, actual)

    def test_an_operator_review_over_a_comparison_whose_esr_record_moved_is_refused(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        comparison = _sole(out, "comparison_*.json")
        recorded, actual = _edit_json(
            inputs["esr"], lambda d: d["observations"][0].__setitem__("text", "Reworded.")
        )
        with pytest.raises(orv.OperatorReviewError) as exc:
            orv.resolve_inputs(
                comparison, repo_root=inputs["world"], profile=inputs["bundle"].profile
            )
        assert type(exc.value) is orv.OperatorReviewError
        assert "the ESR record" in str(exc.value)
        _names_both(str(exc.value), recorded, actual)


_FLAG_CHANGES = pytest.mark.parametrize(
    "change",
    [{"record_type": "other"}, {"advisory": False}, {"blocking": True}],
    ids=["record_type", "advisory", "blocking"],
)


class TestEveryLinkRefusesWithItsOwnClass:
    """Characterisation: each link's loader refuses a wrong type or flag with
    its own error class, exactly."""

    @_FLAG_CHANGES
    def test_the_preflight(self, inputs, change):
        path = _sole(inputs["world"] / "reports_preflight", "preflight_*.json")
        _edit_json(path, lambda d: d.update(change))
        with pytest.raises(BlindAssessmentError) as exc:
            load_preflight(path)
        assert type(exc.value) is BlindAssessmentError

    @_FLAG_CHANGES
    def test_the_blind_report(self, inputs, change):
        path = _sole(inputs["world"] / "reports", "blind_*.json")
        _edit_json(path, lambda d: d.update(change))
        with pytest.raises(BlindAssessmentError) as exc:
            load_report(path, inputs["candidate"], inputs["bundle"].profile)
        assert type(exc.value) is BlindAssessmentError

    @_FLAG_CHANGES
    def test_the_blind_baseline(self, inputs, change):
        _edit_json(inputs["frozen"].freeze_path, lambda d: d.update(change))
        with pytest.raises(bb.BlindBaselineError) as exc:
            bb.load_frozen_baseline(inputs["baseline"])
        assert type(exc.value) is bb.BlindBaselineError

    @_FLAG_CHANGES
    def test_the_integrity_audit(self, tmp_path, change):
        good = {
            "record_type": ia.AUDIT_RECORD_TYPE, "advisory": True, "blocking": False,
            "candidate_hash": "sha256:" + "0" * 64, "profile_version": "x",
            "checks": [], "grounding": {}, "baseline": {},
        }
        path = _write_json(tmp_path / "a.json", {**good, **change})
        with pytest.raises(ia.IntegrityAuditError) as exc:
            ia.load_audit(path)
        assert type(exc.value) is ia.IntegrityAuditError

    @_FLAG_CHANGES
    def test_the_review_notes(self, tmp_path, change):
        path = _write_json(tmp_path / "n.json", {**_notes("0" * 64), **change})
        with pytest.raises(orv.OperatorReviewError) as exc:
            orv.load_review_notes(path)
        assert type(exc.value) is orv.OperatorReviewError

    def test_a_blind_report_over_a_candidate_that_moved_keeps_its_own_refusal(self, inputs):
        path = _sole(inputs["world"] / "reports", "blind_*.json")
        _edit_candidate(inputs["candidate"])
        with pytest.raises(CandidateHashMismatch):
            load_report(path, inputs["candidate"], inputs["bundle"].profile)

    def test_a_preflight_missing_a_field_is_refused(self, inputs):
        path = _sole(inputs["world"] / "reports_preflight", "preflight_*.json")
        _edit_json(path, lambda d: d.pop("pack_set_hash"))
        with pytest.raises(BlindAssessmentError, match="pack_set_hash"):
            load_preflight(path)

    def test_a_baseline_whose_copy_is_gone_is_refused(self, inputs):
        inputs["frozen"].copy_path.unlink()
        with pytest.raises(bb.BlindBaselineError, match="frozen report copy"):
            bb.load_frozen_baseline(inputs["baseline"])


class TestEveryLinkWritesTheNumberedRule:
    def test_the_preflight_and_the_report_take_the_first_number(self, inputs):
        world = inputs["world"]
        assert re.fullmatch(
            r"preflight_[0-9a-f]{12}_0001\.json",
            _sole(world / "reports_preflight", "preflight_*.json").name,
        )
        assert re.fullmatch(
            r"blind_[0-9a-f]{12}_0001\.json", _sole(world / "reports", "blind_*.json").name
        )

    def test_a_review_writes_its_markdown_pair_under_one_sequence_number(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        comparison = _sole(out, "comparison_*.json")
        notes = _write_json(
            inputs["world"] / "docs" / "review" / "notes.json", _notes(file_hash(comparison))
        )
        reviews = inputs["world"] / "reviews"
        for _ in range(2):
            code = cmd.main(
                ["review", "--comparison", str(comparison), "--notes", str(notes),
                 "--repo-root", str(inputs["world"]),
                 "--profile", str(inputs["bundle"].profile.source_path),
                 "--out-dir", str(reviews)],
                clock=lambda: FROZEN,
            )
            assert code in (0, 1)
        short = short_hash(file_hash(comparison))
        assert sorted(p.name for p in reviews.iterdir()) == [
            f"operator_decisions_{short}_0001.md", f"operator_decisions_{short}_0002.md",
            f"operator_review_{short}_0001.md", f"operator_review_{short}_0002.md",
        ]


_COMMITTED_FREEZES = sorted(DN.glob("baselines/*/blind_baseline_*.freeze.json"))
_COMMITTED_AUDITS = sorted((DN / "audit").glob("integrity_*.json"))
_COMMITTED_NOTES = sorted((DN / "esr").glob("review_notes_*.json"))


class TestTicket06RecordsWrittenBeforeLoad:
    @pytest.mark.parametrize("path", _COMMITTED_FREEZES, ids=lambda p: p.parent.name)
    def test_a_committed_baseline_loads(self, path):
        frozen = bb.load_frozen_baseline(path.parent)
        assert frozen.record["report_sha256"] == file_hash(frozen.copy_path)

    @pytest.mark.parametrize("path", _COMMITTED_AUDITS, ids=lambda p: p.name)
    def test_a_committed_audit_loads(self, path):
        assert ia.load_audit(path)["record_type"] == ia.AUDIT_RECORD_TYPE

    @pytest.mark.parametrize("path", _COMMITTED_NOTES, ids=lambda p: p.name)
    def test_committed_review_notes_load(self, path):
        assert orv.load_review_notes(path).sha256 == file_hash(path)


# --------------------------------------------------------------------------- #
# The boundary: DN record modules load predecessors only through the chain
# --------------------------------------------------------------------------- #

#: The modules that hold a DN record kind.
_DN_RECORD_MODULES = (
    "evidence_preflight",
    "blind_assessment",
    "blind_baseline",
    "integrity_audit",
    "esr_comparison",
    "comparison_diff",
    "operator_review",
)

#: Each link's loader and writer, by module. Every loader goes through
#: ``load_record``; every writer through ``write_record`` or ``write_rendering``.
#: The baseline freeze writes two fixed names, not a numbered path, so its
#: writer is not here (the names are a record format this ticket keeps).
_LOADERS = {
    "evidence_preflight": ("load_preflight",),
    "blind_assessment": ("load_report",),
    "blind_baseline": ("load_frozen_baseline",),
    "integrity_audit": ("load_audit",),
    "esr_comparison": ("load_comparison",),
    "comparison_diff": ("load_pair_member", "load_diff"),
    "operator_review": ("load_review_notes", "resolve_inputs"),
}
_WRITERS = {
    "evidence_preflight": ("write_preflight",),
    "blind_assessment": ("write_report",),
    "integrity_audit": ("write_audit",),
    "esr_comparison": ("write_comparison",),
    "comparison_diff": ("write_diff",),
    "operator_review": ("write_review",),
}

#: Where a DN record module may still hash a file itself: hashing what it is
#: about to freeze or write, or an input outside the chain (the ESR record,
#: the dispositions, the register and the audits a comparison is given, an
#: import manifest a preflight pins, and the records the review notes name).
_OWN_HASHING = {
    ("blind_baseline", "freeze_baseline"),
    ("evidence_preflight", "_manifest_pin"),
    ("esr_comparison", "load_esr_record"),
    ("esr_comparison", "load_dispositions"),
    ("esr_comparison", "load_register"),
    ("esr_comparison", "load_audits"),
    ("operator_review", "_approval_record"),
    ("operator_review", "_adjudication_record"),
}

_NUMBERING = {"next_numbered_path", "next_report_path", "next_markdown_path", "_next_report_path"}
_HASHING = {"file_hash", "file_sha256"}


def _tree(module: str):
    import ast

    return ast.parse((REPO / "harness" / f"{module}.py").read_text(encoding="utf-8"))


def _called(node) -> set[str]:
    import ast

    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            names.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    return names


def _functions(tree) -> dict[str, object]:
    import ast

    return {
        n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


class TestTheChainBoundary:
    @pytest.mark.parametrize("module", _DN_RECORD_MODULES)
    def test_no_module_reads_the_advisory_or_blocking_flag_itself(self, module):
        import ast

        def is_flag(node) -> bool:
            return (
                isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "get"
                and bool(node.args)
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in ("advisory", "blocking")
            )

        # A flag compared is a check; a flag printed in a rendering is not.
        reads = [
            sub.lineno
            for sub in ast.walk(_tree(module))
            if isinstance(sub, ast.Compare) and any(map(is_flag, [sub.left, *sub.comparators]))
        ]
        assert not reads, f"harness/{module}.py checks a record's flags at lines {reads}"

    @pytest.mark.parametrize("module", _DN_RECORD_MODULES)
    def test_no_module_numbers_its_own_paths(self, module):
        tree = _tree(module)
        assert not (_called(tree) & _NUMBERING)
        assert not (set(_functions(tree)) & _NUMBERING)

    @pytest.mark.parametrize(
        "module, name", [(m, n) for m, names in _LOADERS.items() for n in names]
    )
    def test_every_loader_goes_through_the_chain(self, module, name):
        assert "load_record" in _called(_functions(_tree(module))[name])

    @pytest.mark.parametrize(
        "module, name", [(m, n) for m, names in _WRITERS.items() for n in names]
    )
    def test_every_writer_goes_through_the_chain(self, module, name):
        assert _called(_functions(_tree(module))[name]) & {"write_record", "write_rendering"}

    @pytest.mark.parametrize("module", _DN_RECORD_MODULES)
    def test_no_module_re_hashes_a_predecessor_itself(self, module):
        hashing = {
            (module, name)
            for name, fn in _functions(_tree(module)).items()
            if _called(fn) & _HASHING
        }
        assert hashing <= _OWN_HASHING, sorted(hashing - _OWN_HASHING)
        assert "hashlib" not in (REPO / "harness" / f"{module}.py").read_text(encoding="utf-8")
