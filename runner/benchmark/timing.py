"""
Pure timing and statistical helpers for benchmark analytics.

All functions operate on plain lists of floats. No external dependencies
beyond the standard library. All edge cases (empty input, single value,
NaN/inf) are handled deterministically.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def mean(values: list[float]) -> float:
    """Arithmetic mean. Returns 0.0 for empty input."""
    clean = _clean(values)
    if not clean:
        return 0.0
    return sum(clean) / len(clean)


def median(values: list[float]) -> float:
    """Median value. Returns 0.0 for empty input."""
    clean = _clean(values)
    if not clean:
        return 0.0
    s = sorted(clean)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def percentile(values: list[float], p: float) -> float:
    """Percentile using nearest-rank method. Returns 0.0 for empty input.

    Parameters
    ----------
    p : float
        Percentile in [0, 100].
    """
    clean = _clean(values)
    if not clean:
        return 0.0
    if p <= 0:
        return min(clean)
    if p >= 100:
        return max(clean)
    s = sorted(clean)
    # Nearest-rank: rank = ceil(p/100 * n)
    rank = math.ceil(p / 100.0 * len(s))
    return s[max(0, rank - 1)]


def build_timing_profile(
    records: list[dict],
    *,
    total_wall_clock_seconds: float | None = None,
) -> dict[str, Any]:
    """Build a timing profile from a list of invocation record dicts.

    Parameters
    ----------
    records
        List of dicts, each with at least ``wall_clock_seconds``,
        ``invocation_type``, ``response_status``. Optional: ``skill_id``,
        ``predicate_id``.
    total_wall_clock_seconds
        The run-level total wall clock (from the benchmark summary or
        run summary). Used to compute idle time estimate.

    Returns
    -------
    dict
        Timing profile artifact payload.
    """
    durations = [
        r["wall_clock_seconds"]
        for r in records
        if _is_finite(r.get("wall_clock_seconds"))
    ]

    sum_invocation = sum(durations)
    total_wc = total_wall_clock_seconds if total_wall_clock_seconds is not None else sum_invocation

    # Idle / non-model time: total run wall clock minus sum of invocation durations
    idle_seconds = max(0.0, total_wc - sum_invocation)

    timeout_count = sum(
        1 for r in records if r.get("response_status") == "timeout"
    )
    failed_count = sum(
        1 for r in records
        if r.get("response_status") in ("error", "timeout")
    )

    profile: dict[str, Any] = {
        "total_wall_clock_seconds": round(total_wc, 4),
        "sum_invocation_wall_clock_seconds": round(sum_invocation, 4),
        "idle_non_model_seconds_estimate": round(idle_seconds, 4),
        "mean_invocation_seconds": round(mean(durations), 4),
        "median_invocation_seconds": round(median(durations), 4),
        "p95_invocation_seconds": round(percentile(durations, 95), 4),
        "p99_invocation_seconds": round(percentile(durations, 99), 4),
        "min_invocation_seconds": round(min(durations), 4) if durations else 0.0,
        "max_invocation_seconds": round(max(durations), 4) if durations else 0.0,
        "timeout_count": timeout_count,
        "failed_invocation_count": failed_count,
    }

    # Timing by invocation type
    by_type: dict[str, list[float]] = defaultdict(list)
    for r in records:
        wc = r.get("wall_clock_seconds")
        if _is_finite(wc):
            by_type[r.get("invocation_type", "unknown")].append(wc)

    profile["timing_by_invocation_type"] = {
        k: _group_timing_summary(v) for k, v in sorted(by_type.items())
    }

    # Timing by skill id
    by_skill: dict[str, list[float]] = defaultdict(list)
    for r in records:
        sid = r.get("skill_id")
        wc = r.get("wall_clock_seconds")
        if sid and _is_finite(wc):
            by_skill[sid].append(wc)

    profile["timing_by_skill_id"] = {
        k: _group_timing_summary(v) for k, v in sorted(by_skill.items())
    }

    # Timing by semantic predicate id
    by_pred: dict[str, list[float]] = defaultdict(list)
    for r in records:
        pid = r.get("predicate_id")
        wc = r.get("wall_clock_seconds")
        if pid and _is_finite(wc):
            by_pred[pid].append(wc)

    profile["timing_by_semantic_predicate_id"] = {
        k: _group_timing_summary(v) for k, v in sorted(by_pred.items())
    }

    return profile


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean(values: list[float]) -> list[float]:
    """Filter out non-finite values."""
    return [v for v in values if _is_finite(v)]


def _is_finite(v: Any) -> bool:
    """Return True if v is a finite number."""
    if not isinstance(v, (int, float)):
        return False
    return math.isfinite(v)


def _group_timing_summary(durations: list[float]) -> dict[str, Any]:
    """Build a summary dict for a group of durations."""
    return {
        "count": len(durations),
        "total_seconds": round(sum(durations), 4),
        "mean_seconds": round(mean(durations), 4),
        "median_seconds": round(median(durations), 4),
        "min_seconds": round(min(durations), 4) if durations else 0.0,
        "max_seconds": round(max(durations), 4) if durations else 0.0,
    }
