"""
Tests for harness/calibration.py — precision/recall meta-eval + graduation.

Covers:
  - ConfusionMatrix cells, precision/recall/rates, divide-by-zero -> None
  - GraduationThreshold bounds
  - calibrate(): requires labeled, alignment, records the guardrail four
  - meets(): fail-safe when precision/recall undefined
  - applies_to(): repin invalidation
  - graduation_for(): the 4-branch fail-safe cascade
  - calibrate_with_judge(): fake judge end-to-end, provenance, passed-None error
  - CalibrationLog: append / latest_for / reload across instances
"""

from __future__ import annotations

from typing import Any

import pytest

from harness.calibration import (
    DEFAULT_GRADUATION_THRESHOLD,
    GRADUATION_ADVISORY,
    GRADUATION_GATING_PERMITTED,
    CalibrationError,
    CalibrationLog,
    ConfusionMatrix,
    GraduationThreshold,
    calibrate,
    calibrate_with_judge,
    confusion_from_labels,
    graduation_for,
)
from harness.gold_set import GoldPair, GoldSet
from harness.judge import Judge, JudgeConfig


FIXED_CLOCK = lambda: "2026-07-20T00:00:00+00:00"


def _gs(*labels, ids=None) -> GoldSet:
    pairs = []
    for i, sup in enumerate(labels):
        pairs.append(
            GoldPair(
                pair_id=(ids[i] if ids else f"g{i+1}"),
                claim=f"claim {i}",
                source_ref="docs/x.json",
                source_excerpt=f"excerpt {i}",
                supported=sup,
            )
        )
    return GoldSet(pairs=tuple(pairs), gold_set_id="gs")


def _cfg(model="acme-judge-1", version="v1") -> JudgeConfig:
    return JudgeConfig(model=model, version=version)


# --------------------------------------------------------------------------- #
# ConfusionMatrix
# --------------------------------------------------------------------------- #


class TestConfusion:
    def test_cells_and_metrics(self):
        # truth vs pred (supported=True positive)
        cm = confusion_from_labels([True, True, False, False], [True, False, True, False])
        assert (cm.tp, cm.fn, cm.fp, cm.tn) == (1, 1, 1, 1)
        assert cm.precision == 0.5
        assert cm.recall == 0.5
        assert cm.accuracy == 0.5
        assert cm.fp == 1  # a false positive here = the judge blessed a gap
        assert cm.gap_detection_recall == 0.5  # tn/(tn+fp)

    def test_perfect(self):
        cm = confusion_from_labels([True, False], [True, False])
        assert cm.precision == 1.0
        assert cm.recall == 1.0
        assert cm.f1 == 1.0

    def test_no_positive_predictions_precision_none(self):
        cm = confusion_from_labels([True, False], [False, False])
        assert cm.precision is None  # tp+fp == 0
        assert cm.recall == 0.0

    def test_no_positive_truth_recall_none(self):
        cm = confusion_from_labels([False, False], [True, False])
        assert cm.recall is None  # tp+fn == 0

    def test_length_mismatch(self):
        with pytest.raises(CalibrationError, match="lengths differ"):
            confusion_from_labels([True], [True, False])


class TestThreshold:
    @pytest.mark.parametrize("p,r", [(-0.1, 0.5), (0.5, 1.1), (2.0, 0.5)])
    def test_out_of_range(self, p, r):
        with pytest.raises(ValueError):
            GraduationThreshold(min_precision=p, min_recall=r)

    def test_default_is_conservative(self):
        assert DEFAULT_GRADUATION_THRESHOLD.min_precision >= 0.9


# --------------------------------------------------------------------------- #
# calibrate (pure)
# --------------------------------------------------------------------------- #


class TestCalibrate:
    def test_records_guardrail_four(self):
        gs = _gs(True, True, False, False)
        rep = calibrate(gs, [True, False, True, False], judge_model="m", judge_version="v", clock=FIXED_CLOCK)
        d = rep.to_dict()
        for f in ("judge_model", "judge_version", "precision", "recall"):
            assert f in d
        assert d["judge_model"] == "m"
        assert rep.precision == 0.5
        assert rep.n_pairs == 4

    def test_requires_labeled(self):
        gs = GoldSet(pairs=(GoldPair(pair_id="g", claim="c", source_ref="s", supported=None),))
        with pytest.raises(Exception):  # GoldSetError (unlabeled)
            calibrate(gs, [True], judge_model="m", judge_version="v")

    def test_alignment_enforced(self):
        gs = _gs(True, False)
        with pytest.raises(CalibrationError, match="align"):
            calibrate(gs, [True], judge_model="m", judge_version="v")

    def test_graduated_true_when_perfect(self):
        gs = _gs(True, False, True, False)
        rep = calibrate(gs, [True, False, True, False], judge_model="m", judge_version="v",
                        threshold=GraduationThreshold(0.9, 0.8), clock=FIXED_CLOCK)
        assert rep.graduated is True

    def test_graduated_false_when_below(self):
        gs = _gs(True, True, False, False)
        rep = calibrate(gs, [True, False, True, False], judge_model="m", judge_version="v",
                        threshold=GraduationThreshold(0.9, 0.8), clock=FIXED_CLOCK)
        assert rep.graduated is False  # precision/recall 0.5

    def test_meets_fail_safe_on_undefined(self):
        gs = _gs(True, False)
        rep = calibrate(gs, [False, False], judge_model="m", judge_version="v",
                        threshold=GraduationThreshold(0.0, 0.0), clock=FIXED_CLOCK)
        # precision undefined (no positive preds) -> never meets, even a 0-bar.
        assert rep.precision is None
        assert rep.meets() is False


# --------------------------------------------------------------------------- #
# applies_to + graduation_for cascade
# --------------------------------------------------------------------------- #


class TestGraduationCascade:
    def _perfect_report(self, model="acme-judge-1", version="v1"):
        gs = _gs(True, False, True, False)
        return calibrate(gs, [True, False, True, False], judge_model=model, judge_version=version,
                         threshold=GraduationThreshold(0.9, 0.8), clock=FIXED_CLOCK)

    def test_no_report_advisory(self):
        d = graduation_for(_cfg(), None)
        assert d.status == GRADUATION_ADVISORY
        assert not d.gating_permitted

    def test_repin_advisory(self):
        rep = self._perfect_report(version="v1")
        d = graduation_for(_cfg(version="v2"), rep)  # version changed => stale
        assert d.status == GRADUATION_ADVISORY
        assert d.applies is False
        assert "repin" in d.reason

    def test_model_repin_advisory(self):
        rep = self._perfect_report(model="acme-judge-1")
        d = graduation_for(_cfg(model="acme-judge-2"), rep)
        assert d.status == GRADUATION_ADVISORY

    def test_below_bar_advisory(self):
        gs = _gs(True, True, False, False)
        rep = calibrate(gs, [True, False, True, False], judge_model="acme-judge-1", judge_version="v1",
                        threshold=GraduationThreshold(0.9, 0.8), clock=FIXED_CLOCK)
        d = graduation_for(_cfg(), rep)
        assert d.status == GRADUATION_ADVISORY
        assert d.applies is True
        assert "below" in d.reason

    def test_cleared_bar_gating(self):
        rep = self._perfect_report()
        d = graduation_for(_cfg(), rep)
        assert d.status == GRADUATION_GATING_PERMITTED
        assert d.gating_permitted is True
        assert d.applies is True

    def test_decision_threshold_override(self):
        # A report that graduated at its own bar can be re-judged at a stricter one.
        rep = self._perfect_report()
        d = graduation_for(_cfg(), rep, threshold=GraduationThreshold(1.0, 1.0))
        assert d.gating_permitted is True  # perfect judge still clears 1.0/1.0


# --------------------------------------------------------------------------- #
# calibrate_with_judge (fake judge end-to-end)
# --------------------------------------------------------------------------- #


class _Backend:
    def __init__(self, contents: list[str]) -> None:
        self._contents = list(contents)

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        c = self._contents.pop(0) if self._contents else '{"passed": true, "rationale": "x"}'
        return {"content": c, "tool_calls": None}


def _v(passed: bool) -> str:
    return '{"passed": %s, "rationale": "r"}' % ("true" if passed else "false")


class TestCalibrateWithJudge:
    def test_end_to_end_confusion(self, tmp_path):
        from harness.provenance import ProvenanceLog

        gs = _gs(True, True, False, False)  # truth
        backend = _Backend([_v(True), _v(False), _v(True), _v(False)])  # tp, fn, fp, tn
        judge = Judge(_cfg(), backend=backend)
        log = ProvenanceLog(tmp_path / "prov.jsonl")

        rep, results = calibrate_with_judge(gs, judge, threshold=GraduationThreshold(0.9, 0.8),
                                            provenance_log=log, clock=FIXED_CLOCK)
        assert rep.confusion.tp == 1 and rep.confusion.fp == 1
        assert rep.precision == 0.5
        assert rep.judge_model == "acme-judge-1"
        assert len(results) == 4
        assert len(log) == 4  # provenance for every verdict

    def test_passed_none_raises(self):
        gs = _gs(True)
        backend = _Backend(['{"score": 0.5, "rationale": "no boolean"}'])  # score-only
        judge = Judge(_cfg(), backend=backend)
        with pytest.raises(CalibrationError, match="no boolean"):
            calibrate_with_judge(gs, judge)


# --------------------------------------------------------------------------- #
# CalibrationLog
# --------------------------------------------------------------------------- #


class TestCalibrationLog:
    def _report(self, model, version):
        gs = _gs(True, False)
        return calibrate(gs, [True, False], judge_model=model, judge_version=version, clock=FIXED_CLOCK)

    def test_append_and_latest_for(self, tmp_path):
        log = CalibrationLog(tmp_path / "cal.jsonl")
        log.append(self._report("m1", "v1"))
        log.append(self._report("m1", "v2"))
        log.append(self._report("m1", "v2"))  # newer v2
        assert len(log) == 3
        latest = log.latest_for("m1", "v2")
        assert latest is not None
        assert latest["judge_version"] == "v2"
        assert log.latest_for("m1", "v9") is None

    def test_reload_across_instances(self, tmp_path):
        p = tmp_path / "cal.jsonl"
        CalibrationLog(p).append(self._report("m1", "v1"))
        log2 = CalibrationLog(p)
        assert len(log2) == 1
        log2.append(self._report("m1", "v2"))
        assert len(CalibrationLog(p)) == 2
