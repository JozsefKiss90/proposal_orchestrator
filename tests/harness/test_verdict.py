"""
Tests for harness/verdict.py — Inferred verdict types + N≥3 majority scaffold.

Covers:
  - Inferred enforcement           — Confirmed/Assumed verdicts cannot be built
  - Verdict score bounds           — score must lie in [0, 1]
  - majority_vote N≥3 floor        — fewer than 3 samples is rejected
  - majority_vote same-property    — mixed metric/property_key rejected
  - majority boolean rule + ties   — tie resolves conservatively to False
  - majority score rule            — mean of non-None scores
  - agreement + score-only panels  — agreement None when no booleans
"""

from __future__ import annotations

import pytest

from harness.verdict import (
    EVIDENCE_TYPE_INFERRED,
    MIN_MAJORITY_SAMPLES,
    MajorityVerdict,
    Verdict,
    majority_vote,
)


def _v(passed=None, score=None, *, metric="m", key="C01", rationale="r") -> Verdict:
    return Verdict(
        metric=metric,
        property_key=key,
        passed=passed,
        score=score,
        rationale=rationale,
    )


# --------------------------------------------------------------------------- #
# Inferred enforcement
# --------------------------------------------------------------------------- #


class TestInferredEnforcement:
    def test_default_verdict_is_inferred(self):
        assert _v(passed=True).evidence_type == EVIDENCE_TYPE_INFERRED
        assert EVIDENCE_TYPE_INFERRED == "Inferred"

    @pytest.mark.parametrize("bad", ["Confirmed", "Assumed", "Unresolved", "inferred", ""])
    def test_verdict_rejects_non_inferred(self, bad):
        with pytest.raises(ValueError, match="evidence_type"):
            Verdict(metric="m", property_key="C01", evidence_type=bad)

    def test_majority_verdict_rejects_non_inferred(self):
        with pytest.raises(ValueError, match="evidence_type"):
            MajorityVerdict(
                metric="m",
                property_key="C01",
                passed=True,
                score=None,
                agreement=1.0,
                n=3,
                members=(),
                evidence_type="Confirmed",
            )


class TestVerdictScoreBounds:
    @pytest.mark.parametrize("score", [-0.01, 1.01, 2.0, -1.0])
    def test_out_of_range_score_rejected(self, score):
        with pytest.raises(ValueError, match=r"\[0.0, 1.0\]"):
            _v(score=score)

    @pytest.mark.parametrize("score", [0.0, 0.5, 1.0])
    def test_in_range_score_accepted(self, score):
        assert _v(score=score).score == score

    def test_none_score_ok(self):
        assert _v(score=None).score is None

    def test_to_dict_roundtrip_fields(self):
        d = _v(passed=False, score=0.25, rationale="because").to_dict()
        assert d["passed"] is False
        assert d["score"] == 0.25
        assert d["evidence_type"] == "Inferred"
        assert d["rationale"] == "because"


# --------------------------------------------------------------------------- #
# majority_vote — guards
# --------------------------------------------------------------------------- #


class TestMajorityGuards:
    def test_min_samples_is_three(self):
        assert MIN_MAJORITY_SAMPLES == 3

    @pytest.mark.parametrize("n", [0, 1, 2])
    def test_fewer_than_three_rejected(self, n):
        with pytest.raises(ValueError, match="at least 3 samples"):
            majority_vote([_v(passed=True) for _ in range(n)])

    def test_mixed_property_key_rejected(self):
        panel = [_v(passed=True, key="C01"), _v(passed=True, key="C01"), _v(passed=True, key="C02")]
        with pytest.raises(ValueError, match="same"):
            majority_vote(panel)

    def test_mixed_metric_rejected(self):
        panel = [_v(passed=True, metric="a"), _v(passed=True, metric="a"), _v(passed=True, metric="b")]
        with pytest.raises(ValueError, match="same"):
            majority_vote(panel)


# --------------------------------------------------------------------------- #
# majority_vote — boolean rule
# --------------------------------------------------------------------------- #


class TestMajorityBoolean:
    def test_unanimous_true(self):
        mv = majority_vote([_v(passed=True) for _ in range(3)])
        assert mv.passed is True
        assert mv.agreement == 1.0
        assert mv.n == 3

    def test_two_of_three_true(self):
        mv = majority_vote([_v(passed=True), _v(passed=True), _v(passed=False)])
        assert mv.passed is True
        assert mv.agreement == pytest.approx(2 / 3)

    def test_two_of_three_false(self):
        mv = majority_vote([_v(passed=False), _v(passed=False), _v(passed=True)])
        assert mv.passed is False
        assert mv.agreement == pytest.approx(2 / 3)

    def test_tie_resolves_to_false(self):
        # 4-member panel, 2 true / 2 false — integrity-weighted tie -> False.
        mv = majority_vote(
            [_v(passed=True), _v(passed=True), _v(passed=False), _v(passed=False)]
        )
        assert mv.passed is False
        assert mv.agreement == 0.5

    def test_none_passed_members_ignored_in_boolean(self):
        # score-only members don't count toward the boolean majority.
        mv = majority_vote(
            [_v(passed=True, score=0.9), _v(passed=True, score=0.9), _v(passed=None, score=0.1)]
        )
        assert mv.passed is True
        # only 2 boolean members, both true
        assert mv.agreement == 1.0


# --------------------------------------------------------------------------- #
# majority_vote — score rule & score-only panels
# --------------------------------------------------------------------------- #


class TestMajorityScore:
    def test_mean_score(self):
        mv = majority_vote([_v(score=0.0), _v(score=0.5), _v(score=1.0)])
        assert mv.score == pytest.approx(0.5)

    def test_score_only_panel_has_no_boolean(self):
        mv = majority_vote([_v(score=0.2), _v(score=0.4), _v(score=0.6)])
        assert mv.passed is None
        assert mv.agreement is None
        assert mv.score == pytest.approx(0.4)

    def test_no_scores_yields_none_score(self):
        mv = majority_vote([_v(passed=True) for _ in range(3)])
        assert mv.score is None

    def test_rationale_and_dict(self):
        mv = majority_vote([_v(passed=True, score=1.0), _v(passed=True, score=1.0), _v(passed=False, score=0.0)])
        assert "majority over n=3" in mv.rationale
        d = mv.to_dict()
        assert d["evidence_type"] == "Inferred"
        assert len(d["members"]) == 3
        assert d["n"] == 3
