"""
Tests for harness/report.py — reporting-only, advisory boundary.

Covers:
  - a report is always advisory=True, blocking=False (cannot be otherwise)
  - summary counts over boolean + score-only findings
  - to_dict carries the boundary flags and serialized findings/routing
  - build_report convenience
  - a report exposes no scheduler-consumable gate result
"""

from __future__ import annotations

import pytest

from harness.report import HarnessReport, build_report
from harness.routing import route
from harness.verdict import Verdict, majority_vote


def _v(passed=None, score=None, key="C1") -> Verdict:
    return Verdict(metric="m", property_key=key, passed=passed, score=score, rationale="r")


class TestAdvisoryBoundary:
    def test_defaults_advisory_nonblocking(self):
        r = HarnessReport(metric="m")
        assert r.advisory is True
        assert r.blocking is False

    def test_cannot_be_blocking(self):
        with pytest.raises(ValueError, match="blocking"):
            HarnessReport(metric="m", blocking=True)

    def test_cannot_be_non_advisory(self):
        with pytest.raises(ValueError, match="advisory"):
            HarnessReport(metric="m", advisory=False)

    def test_no_gate_result_api(self):
        # The report must not offer a scheduler-consumable pass/fail signal.
        r = HarnessReport(metric="m")
        for attr in ("gate_result", "blocks", "as_gate", "passed", "release"):
            assert not hasattr(r, attr), attr


class TestSummary:
    def test_counts(self):
        r = build_report(
            "m",
            [_v(passed=True), _v(passed=False), _v(passed=True), _v(score=0.5)],
        )
        s = r.summary
        assert s == {"total": 4, "passed": 2, "failed": 1, "inconclusive": 1}

    def test_empty(self):
        assert build_report("m", []).summary["total"] == 0


class TestSerialization:
    def test_to_dict(self):
        findings = [_v(passed=True), _v(passed=False, key="C2")]
        routing = [route("status_aware_faithfulness"), route("source_refs_present")]
        r = build_report(
            "status_aware_faithfulness",
            findings,
            routing=routing,
            judge_model="acme-judge-1",
            judge_version="v1",
            notes="threshold 1.0 for confirmed",
        )
        d = r.to_dict()
        assert d["record_type"] == "harness_report"
        assert d["advisory"] is True
        assert d["blocking"] is False
        assert d["judge_model"] == "acme-judge-1"
        assert len(d["findings"]) == 2
        assert len(d["routing"]) == 2
        # routing captured the deterministic refusal
        refused = [x for x in d["routing"] if not x["judge_permitted"]]
        assert refused and refused[0]["covering_predicate"] == "source_refs_present"

    def test_accepts_majority_verdict_finding(self):
        mv = majority_vote([_v(passed=True), _v(passed=True), _v(passed=False)])
        r = build_report("m", [mv])
        d = r.to_dict()
        assert d["summary"]["passed"] == 1
        assert d["findings"][0]["n"] == 3
