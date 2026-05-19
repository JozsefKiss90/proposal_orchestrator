"""Tests for runner.benchmark.timing — pure statistical helpers."""

import math

import pytest

from runner.benchmark.timing import (
    build_timing_profile,
    mean,
    median,
    percentile,
)


# ---------------------------------------------------------------------------
# mean()
# ---------------------------------------------------------------------------

class TestMean:
    def test_basic(self):
        assert mean([1.0, 2.0, 3.0]) == 2.0

    def test_single_value(self):
        assert mean([5.0]) == 5.0

    def test_empty(self):
        assert mean([]) == 0.0

    def test_ignores_nan(self):
        assert mean([1.0, float("nan"), 3.0]) == 2.0

    def test_ignores_inf(self):
        assert mean([1.0, float("inf"), 3.0]) == 2.0

    def test_integers(self):
        assert mean([2, 4, 6]) == 4.0


# ---------------------------------------------------------------------------
# median()
# ---------------------------------------------------------------------------

class TestMedian:
    def test_odd_count(self):
        assert median([3.0, 1.0, 2.0]) == 2.0

    def test_even_count(self):
        assert median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_single_value(self):
        assert median([7.0]) == 7.0

    def test_empty(self):
        assert median([]) == 0.0

    def test_two_values(self):
        assert median([10.0, 20.0]) == 15.0

    def test_ignores_nan(self):
        result = median([1.0, float("nan"), 5.0])
        assert result == 3.0  # median of [1.0, 5.0]


# ---------------------------------------------------------------------------
# percentile()
# ---------------------------------------------------------------------------

class TestPercentile:
    def test_p95(self):
        values = list(range(1, 101))  # 1..100
        result = percentile(values, 95)
        assert result == 95

    def test_p99(self):
        values = list(range(1, 101))
        result = percentile(values, 99)
        assert result == 99

    def test_p50_is_median_odd(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert percentile(values, 50) == 3.0

    def test_p0_is_min(self):
        values = [5.0, 3.0, 8.0]
        assert percentile(values, 0) == 3.0

    def test_p100_is_max(self):
        values = [5.0, 3.0, 8.0]
        assert percentile(values, 100) == 8.0

    def test_empty(self):
        assert percentile([], 95) == 0.0

    def test_single_value(self):
        assert percentile([42.0], 95) == 42.0

    def test_ignores_invalid(self):
        # After filtering inf, [1.0, 3.0] remains. nearest-rank p50:
        # rank = ceil(0.5 * 2) = 1 -> s[0] = 1.0
        result = percentile([1.0, float("inf"), 3.0], 50)
        assert result == 1.0


# ---------------------------------------------------------------------------
# build_timing_profile()
# ---------------------------------------------------------------------------

class TestBuildTimingProfile:
    def _make_record(
        self,
        wall_clock_seconds=10.0,
        invocation_type="skill_tapm",
        response_status="success",
        skill_id=None,
        predicate_id=None,
    ):
        return {
            "wall_clock_seconds": wall_clock_seconds,
            "invocation_type": invocation_type,
            "response_status": response_status,
            "skill_id": skill_id,
            "predicate_id": predicate_id,
        }

    def test_basic_profile(self):
        records = [
            self._make_record(wall_clock_seconds=10.0),
            self._make_record(wall_clock_seconds=20.0),
            self._make_record(wall_clock_seconds=30.0),
        ]
        profile = build_timing_profile(records, total_wall_clock_seconds=100.0)

        assert profile["total_wall_clock_seconds"] == 100.0
        assert profile["sum_invocation_wall_clock_seconds"] == 60.0
        assert profile["idle_non_model_seconds_estimate"] == 40.0
        assert profile["mean_invocation_seconds"] == 20.0
        assert profile["median_invocation_seconds"] == 20.0
        assert profile["min_invocation_seconds"] == 10.0
        assert profile["max_invocation_seconds"] == 30.0

    def test_empty_records(self):
        profile = build_timing_profile([])
        assert profile["mean_invocation_seconds"] == 0.0
        assert profile["min_invocation_seconds"] == 0.0

    def test_timeout_and_failed_counts(self):
        records = [
            self._make_record(response_status="success"),
            self._make_record(response_status="timeout"),
            self._make_record(response_status="error"),
        ]
        profile = build_timing_profile(records)
        assert profile["timeout_count"] == 1
        assert profile["failed_invocation_count"] == 2

    def test_grouping_by_type(self):
        records = [
            self._make_record(invocation_type="skill_tapm", wall_clock_seconds=5.0),
            self._make_record(invocation_type="semantic_predicate", wall_clock_seconds=3.0),
        ]
        profile = build_timing_profile(records)
        assert "skill_tapm" in profile["timing_by_invocation_type"]
        assert "semantic_predicate" in profile["timing_by_invocation_type"]

    def test_grouping_by_skill(self):
        records = [
            self._make_record(skill_id="call-analysis", wall_clock_seconds=10.0),
            self._make_record(skill_id="call-analysis", wall_clock_seconds=20.0),
        ]
        profile = build_timing_profile(records)
        assert profile["timing_by_skill_id"]["call-analysis"]["count"] == 2

    def test_grouping_by_predicate(self):
        records = [
            self._make_record(
                predicate_id="scope_check",
                invocation_type="semantic_predicate",
                wall_clock_seconds=2.0,
            ),
        ]
        profile = build_timing_profile(records)
        assert "scope_check" in profile["timing_by_semantic_predicate_id"]

    def test_no_total_wall_clock_uses_sum(self):
        records = [
            self._make_record(wall_clock_seconds=10.0),
            self._make_record(wall_clock_seconds=20.0),
        ]
        profile = build_timing_profile(records)
        assert profile["total_wall_clock_seconds"] == 30.0
        assert profile["idle_non_model_seconds_estimate"] == 0.0
