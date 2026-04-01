"""
Shared result types and failure-category constants for gate predicates.

The ``PredicateResult`` dataclass is the uniform return type for every
predicate function in this package.  Its ``failure_category`` field maps
directly to the ``failure_category`` entries in the GateResult schema
(gate_rules_library_plan.md §6.2) and must be present on every failing
result.

The five failure-category constants are defined verbatim from
gate_rules_library_plan.md §3 ("Failure categories for deterministic
predicates").  Step 3 file predicates use only
``MISSING_MANDATORY_INPUT`` and ``MALFORMED_ARTIFACT``.  The remaining
three are defined here so that later-step predicate modules can import
from a single authoritative location rather than re-declaring constants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Failure category constants
# Source: gate_rules_library_plan.md §3
# ---------------------------------------------------------------------------

MISSING_MANDATORY_INPUT: str = "MISSING_MANDATORY_INPUT"
"""
A required artifact file or directory does not exist.

Operator action: supply the missing artifact before re-running
(re-run the producing phase or the external system).
"""

MALFORMED_ARTIFACT: str = "MALFORMED_ARTIFACT"
"""
Artifact exists but is not in the expected form: not valid JSON, empty,
wrong type (e.g. a directory where a file is expected), or missing a
required top-level field.

Operator action: the producing agent has a defect or was interrupted;
regenerate the artifact.
"""

CROSS_ARTIFACT_INCONSISTENCY: str = "CROSS_ARTIFACT_INCONSISTENCY"
"""
Content in one artifact is inconsistent with content in another
(coverage, cycle, or timeline failures).

Operator action: identify which artifact is wrong, correct it, and
re-run the phase that produced it.
"""

POLICY_VIOLATION: str = "POLICY_VIOLATION"
"""
Artifact is structurally valid but violates a workflow or constitutional
rule (e.g. source references absent, ethics self-assessment omitted, WP
count limit exceeded).

Operator action: review produced content; correct the agent's behaviour
before re-running.
"""

STALE_UPSTREAM_MISMATCH: str = "STALE_UPSTREAM_MISMATCH"
"""
An artifact exists but its ``run_id`` does not match the current run, or
a freshness bound is violated.

Operator action: re-evaluate the upstream gate under the current run
before proceeding, or register the artifact in the reuse policy.
"""

FAILURE_CATEGORIES: frozenset[str] = frozenset(
    {
        MISSING_MANDATORY_INPUT,
        MALFORMED_ARTIFACT,
        CROSS_ARTIFACT_INCONSISTENCY,
        POLICY_VIOLATION,
        STALE_UPSTREAM_MISMATCH,
    }
)
"""Complete set of valid ``failure_category`` values."""


# ---------------------------------------------------------------------------
# PredicateResult
# ---------------------------------------------------------------------------


@dataclass
class PredicateResult:
    """
    Uniform return type for every gate predicate function.

    The runner's ``evaluate_gate`` function (Step 10) accumulates these
    results and assembles them into the GateResult artifact written to
    Tier 4.  The ``failure_category`` field is the primary triage signal
    for the human operator; it must be present on every failing result
    and absent (``None``) on every passing result.

    Attributes
    ----------
    passed:
        ``True`` iff the predicate condition is satisfied.
    failure_category:
        One of the five constants in ``FAILURE_CATEGORIES``.  Must be
        ``None`` when ``passed`` is ``True``; must be non-``None`` when
        ``passed`` is ``False``.
    reason:
        Human-readable explanation of the failure.  Should be specific
        enough for an operator to act on without consulting source code.
        ``None`` when ``passed`` is ``True``.
    details:
        Supplementary structured data (resolved path, byte count, JSON
        parse error, etc.).  Always present; empty dict when there is
        nothing useful to add.  The ``"path"`` key, when present, always
        holds the string of the *resolved* (absolute or repo-relative)
        path so that the runner can record it unambiguously in the
        GateResult.

    Invariants
    ----------
    These are enforced in ``__post_init__`` and cannot be violated by
    predicate implementations without raising ``ValueError`` at
    construction time:

    * ``passed=True``  →  ``failure_category is None`` and
                          ``reason is None``.
    * ``passed=False`` →  ``failure_category`` is a member of
                          ``FAILURE_CATEGORIES``.
    """

    passed: bool
    failure_category: Optional[str] = None
    reason: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.passed:
            if self.failure_category is not None:
                raise ValueError(
                    "A passing PredicateResult must not carry a failure_category; "
                    f"got: {self.failure_category!r}"
                )
            if self.reason is not None:
                raise ValueError(
                    "A passing PredicateResult must not carry a reason; "
                    f"got: {self.reason!r}"
                )
        else:
            if self.failure_category is None:
                raise ValueError(
                    "A failing PredicateResult must carry a failure_category.  "
                    "The plan requires predicates to return the category — "
                    "the runner must not infer it after the fact."
                )
            if self.failure_category not in FAILURE_CATEGORIES:
                raise ValueError(
                    f"Unknown failure_category: {self.failure_category!r}.  "
                    f"Must be one of: {sorted(FAILURE_CATEGORIES)}"
                )
