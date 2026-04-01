"""
Gate predicate implementations for the DAG runner.

Public API (Step 3 — file predicates):
    exists, non_empty, non_empty_json, dir_non_empty

Public API (Step 4 — gate-pass predicate):
    gate_pass_recorded

All predicates return a ``PredicateResult``.  The ``failure_category``
field on a failing result is the primary triage signal consumed by the
GateResult writer (Step 10).
"""

from runner.predicates.file_predicates import (
    dir_non_empty,
    exists,
    non_empty,
    non_empty_json,
)
from runner.predicates.gate_pass_predicates import gate_pass_recorded
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    FAILURE_CATEGORIES,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
    STALE_UPSTREAM_MISMATCH,
    PredicateResult,
)

__all__ = [
    # types
    "PredicateResult",
    "FAILURE_CATEGORIES",
    "MISSING_MANDATORY_INPUT",
    "MALFORMED_ARTIFACT",
    "CROSS_ARTIFACT_INCONSISTENCY",
    "POLICY_VIOLATION",
    "STALE_UPSTREAM_MISMATCH",
    # file predicates (Step 3)
    "exists",
    "non_empty",
    "non_empty_json",
    "dir_non_empty",
    # gate-pass predicate (Step 4)
    "gate_pass_recorded",
]
