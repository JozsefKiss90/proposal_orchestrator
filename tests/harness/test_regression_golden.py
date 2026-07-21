"""
Standing E4 golden-set suite — the live Tier-5 sections vs the frozen goldens.

This is the CI wiring of the E4 ticket: every full-suite run diffs
``docs/tier5_deliverables/proposal_sections/*.json`` against the committed
baselines in ``harness/regression_baselines/``.  A failure here is
**merge-advisory, human-decided** — it means the section artifacts drifted
from the golden set, and the human either refreezes (intentional redraft:
``py -3.10 -m harness.regression freeze``, commit the golden diff in the same
PR) or investigates (unintentional regression).  It is never consumed by the
runtime DAG; nothing here blocks a run.

Marked ``harness_regression`` so the lane can be selected alone
(``pytest -m harness_regression``) or skipped (``-m "not harness_regression"``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import harness.regression as reg

REPO_ROOT = Path(__file__).resolve().parents[2]
SECTIONS_DIR = REPO_ROOT / reg.DEFAULT_SECTIONS_DIR
GOLDEN_DIR = REPO_ROOT / reg.DEFAULT_GOLDEN_DIR

pytestmark = pytest.mark.harness_regression


def _advisory(report: reg.RegressionReport) -> str:
    lines = ["E4 golden-set drift (merge-advisory, human-decided):"]
    for f in report.golden_set_findings:
        lines.append(f"  [{'BREAKING' if f.breaking else 'advisory'}] {f.kind}: {f.detail}")
    for r in report.results:
        for f in r.findings:
            lines.append(
                f"  [{'BREAKING' if f.breaking else 'advisory'}] "
                f"{r.section_id}/{f.kind}: {f.detail}"
            )
    lines.append(
        "If intentional: refreeze (py -3.10 -m harness.regression freeze) and "
        "commit the golden diff in the same PR. If not: investigate before merging."
    )
    return "\n".join(lines)


class TestGoldenSetStanding:
    def test_golden_baselines_are_committed(self):
        golden = reg.load_golden_set(GOLDEN_DIR)
        assert set(golden) == {
            p.stem for p in SECTIONS_DIR.glob("*.json")
        }, "every live section must have a committed golden baseline (and vice versa)"

    def test_sections_match_golden_set(self):
        golden = reg.load_golden_set(GOLDEN_DIR)
        report = reg.compare_to_golden_set(
            golden, sorted(SECTIONS_DIR.glob("*.json"))
        )
        assert report.blocking is False  # structural: never run-blocking
        assert not report.regressed, _advisory(report)

    def test_drifted_sections_are_surfaced_even_when_not_breaking(self):
        """Advisory-only drift (no breaking finding) must still be visible.

        The report is data for a human: even when nothing breaking occurred,
        ``sections_changed`` in the summary says whether any artifact moved.
        This assertion documents that contract rather than freezing behaviour.
        """
        golden = reg.load_golden_set(GOLDEN_DIR)
        report = reg.compare_to_golden_set(
            golden, sorted(SECTIONS_DIR.glob("*.json"))
        )
        summary = report.to_dict()["summary"]
        assert "sections_changed" in summary
        assert summary["sections_compared"] == len(golden)
