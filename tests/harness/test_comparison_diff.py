"""
The original-to-successor diff of two ESR comparisons (ticket R05).

Three groups:

* Binding: a pair that is not two readings of one body of evidence is refused
  by name, and nothing is written.
* Measurement: the fields that moved on each row, the counts that moved, the
  revision priorities, and the retention rule that every ESR shortcoming keeps
  a proposed revision unless its row is 'addressed'.
* The command end to end, and the committed MSCA-DN pair.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.commands.blind_assessment as cmd
import harness.comparison_diff as cd
from harness.blind_assessment import BlindAssessmentError
from runner.paths import find_repo_root
from tests.harness.test_blind_baseline import _write_json, bundle, world  # noqa: F401
from tests.harness.test_blind_leakage import FROZEN
from tests.harness.test_esr_comparison import (  # noqa: F401 - fixtures
    _compare,
    _rewrite,
    _row,
    frozen_world,
    inputs,
)

REPO = find_repo_root()
DN_COMPARISONS = REPO / "docs/tier4_orchestration_state/msca_dn/comparisons"
DN_BEFORE = DN_COMPARISONS / "comparison_f60ae6e0a2a1_0001.json"
DN_AFTER = DN_COMPARISONS / "comparison_f60ae6e0a2a1_0002.json"

PLAN = {
    "evidence": ["the quoted passage in S2"],
    "responsible_role": {"role": "Project Coordinator", "source": "S2 of the candidate"},
    "requires_confirmation": ["that month four is feasible"],
    "proposal_location": ["S2"],
    "commitment_kind": "requires_study_design",
}


# --------------------------------------------------------------------------- #
# Fixtures: a predecessor and a successor comparison over one baseline
# --------------------------------------------------------------------------- #


def _write_comparison(inputs, name: str) -> Path:
    """Run the compare command into its own directory and return the report."""
    out = inputs["world"] / "comparisons" / name
    code, _ = _compare(inputs, out=out)
    assert code == 0, name
    return next(out.glob("comparison_*.json"))


@pytest.fixture
def pair(inputs):
    """The comparison as PE-08 wrote it, and a successor with R03's changes."""
    before = _write_comparison(inputs, "before")

    def mutate(data):
        # OBS-1: the blind citation is withdrawn and a register basis named, so
        # the row drops from detected to partial.
        row = _row(data, "OBS-1")
        row["disposition"] = "partially_observable"
        row["blind_findings"] = [{"kind": "cell", "expectation_key": "aims-objectives"}]
        row["evidence_basis"] = ["derived/figures/images_on_any_page"]
        row["explanation"] = "Only the cell carries the point."
        row["proposed_revision"]["revision_plan"] = dict(PLAN, proposal_location=["S1"])
    _rewrite(inputs, mutate)
    after = _write_comparison(inputs, "after")
    return before, after


@pytest.fixture
def loaded(pair):
    before, after = pair
    return cd.load_pair_member(before, what="predecessor"), cd.load_pair_member(after, what="successor")


# --------------------------------------------------------------------------- #
# Binding
# --------------------------------------------------------------------------- #


class TestBinding:
    def test_a_comparison_without_its_revisions_artifact_is_refused(self, pair, tmp_path):
        before, _ = pair
        moved = tmp_path / before.name
        moved.write_bytes(before.read_bytes())
        with pytest.raises(cd.ComparisonDiffError, match="not beside it"):
            cd.load_pair_member(moved, what="predecessor")

    def test_a_record_that_is_not_a_comparison_is_refused(self, tmp_path):
        """Refused by the comparison loader, whose error shares the harness base."""
        bad = _write_json(tmp_path / "x.json", {"record_type": "other"})
        with pytest.raises(BlindAssessmentError, match="is not an 'esr_comparison_report'"):
            cd.load_pair_member(bad, what="successor")

    def test_the_same_comparison_twice_is_refused(self, loaded):
        before, _ = loaded
        with pytest.raises(cd.ComparisonDiffError, match="nothing to diff"):
            cd.diff_comparisons(before, before)

    def test_another_baseline_is_refused(self, loaded, tmp_path):
        before, after = loaded
        data = dict(after.data)
        data["baseline"] = dict(data["baseline"], report_sha256="9" * 64)
        other = cd.LoadedComparison(
            path=after.path, sha256="a" * 64, data=data,
            revisions_path=after.revisions_path, revisions_sha256=after.revisions_sha256,
            revisions=after.revisions,
        )
        with pytest.raises(cd.ComparisonDiffError, match="different baseline reports"):
            cd.diff_comparisons(before, other)

    def test_another_esr_record_is_refused(self, loaded):
        before, after = loaded
        data = dict(after.data)
        data["esr_record"] = dict(data["esr_record"], sha256="8" * 64)
        other = cd.LoadedComparison(
            path=after.path, sha256="b" * 64, data=data,
            revisions_path=after.revisions_path, revisions_sha256=after.revisions_sha256,
            revisions=after.revisions,
        )
        with pytest.raises(cd.ComparisonDiffError, match="different ESR records"):
            cd.diff_comparisons(before, other)

    def test_a_different_observation_set_is_refused(self, loaded):
        before, after = loaded
        data = dict(after.data)
        data["rows"] = [r for r in data["rows"] if r["observation_id"] != "OBS-4"]
        other = cd.LoadedComparison(
            path=after.path, sha256="c" * 64, data=data,
            revisions_path=after.revisions_path, revisions_sha256=after.revisions_sha256,
            revisions=after.revisions,
        )
        with pytest.raises(cd.ComparisonDiffError, match="dropped: OBS-4"):
            cd.diff_comparisons(before, other)

    def test_a_moved_score_comparison_is_refused(self, loaded):
        before, after = loaded
        data = dict(after.data)
        scores = json.loads(json.dumps(data["score_comparison"]))
        scores["total"]["blind"] = 1.0
        data["score_comparison"] = scores
        other = cd.LoadedComparison(
            path=after.path, sha256="d" * 64, data=data,
            revisions_path=after.revisions_path, revisions_sha256=after.revisions_sha256,
            revisions=after.revisions,
        )
        with pytest.raises(cd.ComparisonDiffError, match="score comparison differs"):
            cd.diff_comparisons(before, other)


# --------------------------------------------------------------------------- #
# Measurement
# --------------------------------------------------------------------------- #


class TestMeasurement:
    def test_the_moved_row_names_every_field_that_moved(self, loaded):
        diff = cd.diff_comparisons(*loaded, clock=lambda: FROZEN)
        row = next(r for r in diff["rows"] if r["observation_id"] == "OBS-1")
        assert set(row["changed"]) >= {
            "disposition", "blind_findings", "evidence_basis", "explanation", "revision_plan",
        }
        assert row["changes"]["disposition"] == {
            "before": "independently_detected", "after": "partially_observable",
        }
        blind = row["changes"]["blind_findings"]
        assert blind["withdrawn"] == ["criterion_shortcoming:aims:sample0:0"]
        assert blind["added"] == ["cell:aims-objectives"]
        assert row["changes"]["revision_plan"]["state"] == "added"

    def test_the_rows_that_did_not_move_are_listed_not_repeated(self, loaded):
        diff = cd.diff_comparisons(*loaded, clock=lambda: FROZEN)
        assert diff["rows_changed"] == 1
        assert sorted(diff["rows_unchanged"]) == ["OBS-2", "OBS-3", "OBS-4"]

    def test_the_counts_that_moved_are_reported_both_ways(self, loaded):
        diff = cd.diff_comparisons(*loaded, clock=lambda: FROZEN)
        changed = diff["counts"]["changed"]
        assert changed["by_disposition/independently_detected"] == {"before": 2, "after": 1}
        assert changed["by_disposition/partially_observable"] == {"before": 0, "after": 1}
        assert changed["detection/rate_detected"]["before"] > changed["detection/rate_detected"]["after"]
        assert diff["counts"]["before"]["observations"] == 4

    def test_a_priority_change_is_measured_from_the_revisions_artifacts(self, loaded):
        diff = cd.diff_comparisons(*loaded, clock=lambda: FROZEN)
        row = next(r for r in diff["rows"] if r["observation_id"] == "OBS-1")
        # OBS-1 is a shortcoming and stays first by severity; the disposition
        # rank moves it behind nothing, so the recorded ranks are compared.
        before, after = loaded
        assert before.priorities["OBS-1"] is not None
        assert after.priorities["OBS-1"] is not None
        assert ("priority" in row["changed"]) == (
            before.priorities["OBS-1"] != after.priorities["OBS-1"]
        )

    def test_the_score_comparison_is_declared_unchanged(self, loaded):
        diff = cd.diff_comparisons(*loaded, clock=lambda: FROZEN)
        assert diff["score_comparison_unchanged"] is True
        assert diff["flags"] == []

    def test_a_shortcoming_dropped_from_the_revision_list_is_flagged(self, loaded):
        before, after = loaded
        revisions = json.loads(json.dumps(after.revisions))
        revisions["open"] = [e for e in revisions["open"] if e["observation_id"] != "OBS-2"]
        other = cd.LoadedComparison(
            path=after.path, sha256="e" * 64, data=after.data,
            revisions_path=after.revisions_path, revisions_sha256=after.revisions_sha256,
            revisions=revisions,
        )
        diff = cd.diff_comparisons(before, other, clock=lambda: FROZEN)
        dropped = diff["shortcomings_left_out_of_the_revision_list"]
        assert [d["observation_id"] for d in dropped] == ["OBS-2"]
        assert any("only 'addressed' closes a row" in f for f in diff["flags"])


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


class TestCommand:
    def _run(self, inputs, before: Path, after: Path, out: Path) -> int:
        return cmd.main(
            [
                "diff", "--before", str(before), "--after", str(after),
                "--repo-root", str(inputs["world"]),
                "--profile", str(inputs["bundle"].profile.source_path),
                "--out-dir", str(out),
            ],
            clock=lambda: FROZEN,
        )

    def test_both_artifacts_are_written_and_bound(self, inputs, pair, capsys):
        before, after = pair
        out = inputs["world"] / "diffs"
        assert self._run(inputs, before, after, out) == 0
        written = sorted(p.name for p in out.iterdir())
        assert len(written) == 2
        data = cd.load_diff(next(out.glob("review_diff_*.json")))
        assert data["bindings"]["observations"] == 4
        assert data["predecessor"]["comparison_sha256"] != data["successor"]["comparison_sha256"]
        markdown = next(out.glob("review_diff_*.md")).read_text(encoding="utf-8")
        assert "# ESR comparison: predecessor to successor" in markdown
        assert "OBS-1" in markdown and "partially_observable" in markdown
        assert "COMPARISON DIFF" in capsys.readouterr().out

    def test_markdown_is_written_lf_only(self, inputs, pair):
        before, after = pair
        out = inputs["world"] / "diffs"
        assert self._run(inputs, before, after, out) == 0
        assert b"\r\n" not in next(out.glob("review_diff_*.md")).read_bytes()

    def test_nothing_is_overwritten(self, inputs, pair):
        before, after = pair
        out = inputs["world"] / "diffs"
        assert self._run(inputs, before, after, out) == 0
        assert self._run(inputs, before, after, out) == 0
        assert len(list(out.glob("review_diff_*.json"))) == 2

    def test_a_refused_pair_writes_nothing(self, inputs, pair, capsys):
        before, _ = pair
        out = inputs["world"] / "diffs"
        assert self._run(inputs, before, before, out) == 2
        assert "nothing to diff" in capsys.readouterr().err
        assert not out.exists()


# --------------------------------------------------------------------------- #
# The committed MSCA-DN pair
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not DN_AFTER.is_file(), reason="the successor comparison is absent")
class TestCommittedMscaDn:
    def test_the_successor_is_a_reading_of_the_same_evidence(self, tmp_path):
        before = cd.load_pair_member(DN_BEFORE, what="predecessor")
        after = cd.load_pair_member(DN_AFTER, what="successor")
        diff = cd.diff_comparisons(before, after, repo_root=REPO, clock=lambda: FROZEN)
        assert diff["bindings"]["observations"] == 29
        assert diff["score_comparison_unchanged"] is True
        assert diff["flags"] == []

    def test_every_esr_shortcoming_still_carries_a_revision(self):
        after = cd.load_pair_member(DN_AFTER, what="successor")
        shortcomings = {
            str(r["observation_id"]) for r in after.data["rows"]
            if r["kind"] != "strength"
        }
        assert shortcomings <= set(after.priorities)

    def test_the_committed_diff_reproduces_from_the_committed_pair(self, tmp_path):
        committed = sorted(DN_COMPARISONS.glob("review_diff_*.json"))
        assert committed, "no committed diff"
        recorded = cd.load_diff(committed[-1])
        before = cd.load_pair_member(DN_BEFORE, what="predecessor")
        after = cd.load_pair_member(DN_AFTER, what="successor")
        fresh = cd.diff_comparisons(before, after, repo_root=REPO, clock=lambda: FROZEN)
        volatile = {"diffed_at", "writes"}
        assert {k: v for k, v in fresh.items() if k not in volatile} == {
            k: v for k, v in recorded.items() if k not in volatile
        }
