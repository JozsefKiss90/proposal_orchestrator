"""
Tests for harness/status_calibration.py — E3's status-label drift metric.

Fully offline (injected fake backends).  Load-bearing cases: a supplied E2
result costs zero confirmed-direction judge calls; the underclaimed bar is
exactly E2's confirmed bar (boolean at n=1, score floor only under a majority
panel); duplicate claim_ids never collapse; underclaimed is never hard.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

import harness.status_calibration as sc
import harness.status_faithfulness as sf
from harness.judge import Judge, JudgeConfig
from harness.verdict import Verdict, majority_vote
from runner.working_assumptions import WorkingAssumptions


class RuleBackend:
    def __init__(self, rule: Callable[[str, str], dict[str, Any]]) -> None:
        self._rule = rule
        self.calls: list[tuple[str, str]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        system = messages[0]["content"]
        user = messages[1]["content"]
        self.calls.append((system, user))
        return {"content": json.dumps(self._rule(system, user)), "tool_calls": None}


def make_judge(rule: Callable[[str, str], dict[str, Any]]) -> tuple[Judge, RuleBackend]:
    backend = RuleBackend(rule)
    return Judge(JudgeConfig(model="acme-judge-1", version="v1"), backend=backend), backend


def always(payload):
    return lambda system, user: dict(payload)


EMPTY_WA = WorkingAssumptions(present=True)


def claim(cid="C1", summary="the claim", status="confirmed", ref="docs/x.json", idx=None):
    return sf.SectionClaim(
        claim_id=cid, claim_summary=summary, status=status, source_ref=ref, entry_index=idx
    )


def fixed_source(text: str):
    return lambda source_ref, repo_root: text


def e2_finding(cid="C1", status="confirmed", severity=sf.SEVERITY_NONE, idx=None, passed=True):
    return sf.ClaimFaithfulness(
        claim_id=cid, status=status, comparison=sf.COMPARISON_SOURCE,
        comparison_ref="x", severity=severity, entry_index=idx,
        verdict=Verdict(metric="m", property_key=cid, passed=passed),
    )


def e2_result(findings, section="s"):
    return sf.StatusFaithfulnessResult(
        section_id=section, findings=tuple(findings),
        judge_model="acme-judge-1", judge_version="v1",
    )


# --------------------------------------------------------------------------- #
# classify_underclaimed — the pure bar
# --------------------------------------------------------------------------- #


class TestClassifyUnderclaimed:
    def _v(self, passed=None, score=None, idx=None):
        return Verdict(metric="m", property_key="k", passed=passed, score=score,
                       sample_index=idx)

    def test_n1_boolean_governs(self):
        assert sc.classify_underclaimed(self._v(passed=True), n=1) is True
        assert sc.classify_underclaimed(self._v(passed=False), n=1) is False

    def test_n1_score_never_drives(self):
        # a lone sample's 0.80 score does not block the boolean at n=1
        assert sc.classify_underclaimed(self._v(passed=True, score=0.80), n=1) is True

    def test_n3_score_floor_applies(self):
        low = majority_vote([self._v(passed=True, score=0.80, idx=i) for i in range(3)])
        high = majority_vote([self._v(passed=True, score=0.95, idx=i) for i in range(3)])
        assert sc.classify_underclaimed(low, n=3) is False
        assert sc.classify_underclaimed(high, n=3) is True


# --------------------------------------------------------------------------- #
# Overclaimed direction
# --------------------------------------------------------------------------- #


class TestOverclaimed:
    def test_e2_integrity_maps_to_hard_overclaimed(self):
        res = e2_result([
            e2_finding("C1", severity=sf.SEVERITY_INTEGRITY, idx=0, passed=False),
            e2_finding("C2", severity=sf.SEVERITY_NONE, idx=1),
        ])
        judge, backend = make_judge(always({"passed": True, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [], judge, repo_root=Path("."), working_assumptions=EMPTY_WA,
            e2_result=res,
        )
        over = out.overclaimed()
        assert [f.entry_key for f in over] == ["C1#0"]
        assert over[0].is_hard_finding is True
        assert out.drift_counts[sc.DRIFT_NONE] == 1
        assert out.e2_reused is True
        assert backend.calls == []  # zero confirmed-direction judge calls

    def test_e2_unresolved_maps_to_unverifiable_not_overclaimed(self):
        res = e2_result([e2_finding("C1", severity=sf.SEVERITY_UNRESOLVED, idx=3, passed=None)])
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [], judge, repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=res,
        )
        assert out.overclaimed() == ()
        assert [f.entry_key for f in out.unverifiable()] == ["C1#3"]
        assert out.unverifiable()[0].is_hard_finding is False

    def test_internal_e2_run_when_no_result_supplied(self):
        judge, backend = make_judge(always({"passed": False, "score": 0.1, "rationale": "no"}))
        out = sc.evaluate_status_calibration(
            [claim("C1", status="confirmed", idx=0)], judge,
            repo_root=Path("."), working_assumptions=EMPTY_WA,
            source_text_resolver=fixed_source("SRC"),
        )
        assert out.e2_reused is False
        assert len(backend.calls) == 1  # the internal E2 confirmed judgment
        assert [f.entry_key for f in out.overclaimed()] == ["C1#0"]

    def test_e2_result_not_covering_a_confirmed_claim_surfaces_unverifiable(self):
        # An e2_result produced with a claim_filter covers C1 but not C2 —
        # C2's drift row must be surfaced, never silently missing.
        res = e2_result([e2_finding("C1", severity=sf.SEVERITY_NONE, idx=0)])
        judge, backend = make_judge(always({"passed": True, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [claim("C1", status="confirmed", idx=0),
             claim("C2", status="confirmed", idx=1)],
            judge, repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=res,
        )
        unver = out.unverifiable()
        assert [f.entry_key for f in unver] == ["C2#1"]
        assert "does not cover" in unver[0].reason
        assert backend.calls == []  # still zero confirmed-direction judge calls

    def test_e2_result_for_another_section_raises(self):
        res = e2_result([e2_finding("C1", idx=0)], section="impact")
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        with pytest.raises(sc.StatusCalibrationError, match="different|impact"):
            sc.evaluate_status_calibration(
                [], judge, repo_root=Path("."), working_assumptions=EMPTY_WA,
                e2_result=res, section_id="excellence",
            )

    def test_supplied_e2_result_filters_to_confirmed_only(self):
        res = e2_result([
            e2_finding("C1", status="confirmed", severity=sf.SEVERITY_NONE, idx=0),
            e2_finding("I1", status="inferred", severity=sf.SEVERITY_SOFT, idx=1, passed=False),
        ])
        judge, _ = make_judge(always({"passed": False, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [], judge, repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=res,
        )
        # the inferred E2 finding is not the calibration's confirmed direction
        assert [f.entry_key for f in out.findings] == ["C1#0"]


# --------------------------------------------------------------------------- #
# Underclaimed direction
# --------------------------------------------------------------------------- #


class TestUnderclaimed:
    def test_inferred_judged_under_confirmed_standard(self):
        judge, backend = make_judge(always({"passed": True, "score": 0.95, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [claim("I1", status="inferred", idx=5)], judge,
            repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=e2_result([]),
            source_text_resolver=fixed_source("SRC"),
        )
        system, _user = backend.calls[0]
        assert "stamped this claim CONFIRMED" in system  # the strict E2 standard
        under = out.underclaimed()
        assert [f.entry_key for f in under] == ["I1#5"]
        assert under[0].is_hard_finding is False  # soft, always
        assert under[0].flagged is True

    def test_inferred_not_clearing_bar_is_no_drift(self):
        judge, _ = make_judge(always({"passed": False, "rationale": "framing only"}))
        out = sc.evaluate_status_calibration(
            [claim("I1", status="inferred")], judge,
            repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=e2_result([]),
            source_text_resolver=fixed_source("SRC"),
        )
        assert out.underclaimed() == ()
        assert out.drift_counts[sc.DRIFT_NONE] == 1

    def test_n3_low_score_does_not_fire(self):
        judge, backend = make_judge(always({"passed": True, "score": 0.80, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [claim("I1", status="inferred")], judge,
            repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=e2_result([]),
            source_text_resolver=fixed_source("SRC"), n=3,
        )
        assert out.underclaimed() == ()  # 0.80 < 0.90 floor with a panel behind it
        assert len(backend.calls) == 3

    def test_unresolvable_source_is_unverifiable(self):
        def raising_resolver(source_ref, repo_root):
            raise sf.SourceResolutionError("no such source")

        judge, backend = make_judge(always({"passed": True, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [claim("I1", status="inferred", idx=2)], judge,
            repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=e2_result([]),
            source_text_resolver=raising_resolver,
        )
        assert [f.entry_key for f in out.unverifiable()] == ["I1#2"]
        assert backend.calls == []  # never judged

    def test_duplicate_claim_ids_produce_distinct_rows(self):
        judge, _ = make_judge(always({"passed": True, "score": 0.95, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [claim("C01", "fact one", status="inferred", idx=7),
             claim("C01", "unrelated fact", status="inferred", idx=90)],
            judge, repo_root=Path("."), working_assumptions=EMPTY_WA,
            e2_result=e2_result([]), source_text_resolver=fixed_source("SRC"),
        )
        assert [f.entry_key for f in out.underclaimed()] == ["C01#7", "C01#90"]
        assert [r.property_key for r in out.routing] == ["C01#7", "C01#90"]


# --------------------------------------------------------------------------- #
# Result / report / validation
# --------------------------------------------------------------------------- #


class TestResultAndValidation:
    def test_other_statuses_skipped_visibly(self):
        judge, backend = make_judge(always({"passed": True, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [claim("A1", status="assumed", idx=4)], judge,
            repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=e2_result([]),
        )
        assert out.skipped_entry_keys == ("A1#4",)
        assert out.findings == ()
        assert backend.calls == []

    def test_n2_rejected(self):
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        with pytest.raises(ValueError, match="n=2"):
            sc.evaluate_status_calibration(
                [], judge, repo_root=Path("."), working_assumptions=EMPTY_WA, n=2,
            )

    def test_report_boundary_and_notes(self):
        res = e2_result(
            [e2_finding("C1", severity=sf.SEVERITY_INTEGRITY, idx=0, passed=False)],
            section="excellence",
        )
        judge, _ = make_judge(always({"passed": True, "score": 0.95, "rationale": "r"}))
        out = sc.evaluate_status_calibration(
            [claim("I1", status="inferred", idx=1)], judge,
            repo_root=Path("."), working_assumptions=EMPTY_WA, e2_result=res,
            source_text_resolver=fixed_source("SRC"), section_id="excellence",
        )
        report = out.build_report()
        assert report.advisory is True and report.blocking is False
        assert report.metric == sc.STATUS_CALIBRATION_METRIC
        assert "OVERCLAIMED=1" in report.notes
        assert "underclaimed=1" in report.notes
        assert "e2_reused=True" in report.notes
        d = out.to_dict()
        assert d["hard_finding_keys"] == ["C1#0"]
        assert d["underclaimed_keys"] == ["I1#1"]
