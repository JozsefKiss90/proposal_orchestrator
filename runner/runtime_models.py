"""
Runtime contract data types for the Skill Runtime + Agent Runtime
Integration Layer.

This module defines the structured result types exchanged between the
three runtime layers:

    DAGScheduler  ->  AgentRuntime  ->  SkillRuntime
                  <-                <-

All types are frozen dataclasses (immutable after construction).
This module contains **no business logic** -- only data definitions
and validation constants.

Authoritative source:
    runtime_integration_plan.md §4 (Runtime Contracts)
    runtime_integration_plan.md §10 (Failure Semantics)

Constitutional authority:
    Subordinate to CLAUDE.md. This module does not evaluate gates,
    invoke agents, invoke skills, or modify scheduler state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Valid failure_origin values for NodeExecutionResult.
#: See runtime_integration_plan.md §10.1.
FAILURE_ORIGINS: frozenset[str] = frozenset(
    {"entry_gate", "agent_body", "exit_gate"}
)

#: Valid failure_category values for SkillResult.
#: See runtime_integration_plan.md §4.3 and skill_runtime_contract.md §6.2.
SKILL_FAILURE_CATEGORIES: frozenset[str] = frozenset(
    {
        "MISSING_INPUT",
        "MALFORMED_ARTIFACT",
        "CONSTRAINT_VIOLATION",
        "INCOMPLETE_OUTPUT",
        "CONSTITUTIONAL_HALT",
    }
)

#: Valid failure_category values for AgentResult.
#: Superset of SKILL_FAILURE_CATEGORIES with agent-specific categories.
#: See runtime_integration_plan.md §4.1.
AGENT_FAILURE_CATEGORIES: frozenset[str] = SKILL_FAILURE_CATEGORIES | {
    "SKILL_FAILURE",
    "AGENT_EXECUTION_ERROR",
}


# ---------------------------------------------------------------------------
# SkillResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillResult:
    """Structured return type from ``run_skill()`` to the agent runtime.

    Aligns with ``skill_runtime_contract.md`` §6.2 and
    ``runtime_integration_plan.md`` §4.3.

    Every code path in ``run_skill()`` must return a ``SkillResult``.
    On failure, ``failure_reason`` must be non-null.
    """

    status: str
    """``"success"`` or ``"failure"``."""

    outputs_written: list[str] = field(default_factory=list)
    """Paths of artifacts written, relative to *repo_root*."""

    validation_report: str | None = None
    """Path to validation report written, if any."""

    failure_reason: str | None = None
    """Human-readable failure description; required when *status* is
    ``"failure"``."""

    failure_category: str | None = None
    """One of :data:`SKILL_FAILURE_CATEGORIES`, or ``None`` on success."""

    payload: dict[str, Any] | None = None
    """In-memory payload for ``output_contract: "payload"`` skills.

    When a skill's output contract is ``"payload"`` (e.g. gate-enforcement),
    the parsed response is returned here instead of being written to a
    canonical artifact path.  The invoking agent or runner consumes the
    payload directly.  ``None`` for artifact-producing skills."""


# ---------------------------------------------------------------------------
# SkillInvocationRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillInvocationRecord:
    """Record of a single skill invocation within an agent execution.

    Collected by the agent runtime for inclusion in :class:`AgentResult`.
    See ``runtime_integration_plan.md`` §4.1 ``invoked_skills``.
    """

    skill_id: str
    """Skill identifier matching ``skill_catalog.yaml``."""

    status: str
    """``"success"`` or ``"failure"``."""

    failure_reason: str | None = None
    """Human-readable failure description; ``None`` on success."""

    failure_category: str | None = None
    """One of :data:`SKILL_FAILURE_CATEGORIES`, or ``None`` on success."""

    outputs_written: list[str] = field(default_factory=list)
    """Paths of artifacts written by this skill invocation."""


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentResult:
    """Structured return type from the agent runtime to the scheduler
    integration layer.

    See ``runtime_integration_plan.md`` §4.1.

    ``failure_origin`` is always ``"agent_body"`` -- this type is only
    constructed by the agent runtime, never by the scheduler or gate
    evaluator.

    The scheduler uses ``can_evaluate_exit_gate`` as the **sole** decision
    input for whether to call ``evaluate_gate()`` on the exit gate.
    """

    status: str
    """``"success"`` or ``"failure"``."""

    can_evaluate_exit_gate: bool
    """``True`` if all artifacts required by the node's exit-gate predicates
    have been durably written to their canonical paths, are complete, and
    are schema-valid where applicable.  ``False`` otherwise.
    When ``False``, the scheduler MUST skip exit gate evaluation."""

    failure_origin: str = "agent_body"
    """Always ``"agent_body"``.  This field exists so that the scheduler can
    record it in ``RunContext`` without transformation."""

    failure_reason: str | None = None
    """Human-readable failure description; required when *status* is
    ``"failure"``."""

    failure_category: str | None = None
    """One of :data:`AGENT_FAILURE_CATEGORIES`, or ``None`` on success."""

    outputs_written: list[str] = field(default_factory=list)
    """Paths of artifacts written, relative to *repo_root*."""

    validation_reports: list[str] = field(default_factory=list)
    """Paths of validation reports written, if any."""

    decision_log_writes: list[str] = field(default_factory=list)
    """Paths of decision log entries written, if any."""

    invoked_skills: list[SkillInvocationRecord] = field(default_factory=list)
    """Ordered record of skill invocations and their results."""


# ---------------------------------------------------------------------------
# NodeExecutionResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeExecutionResult:
    """Composite result returned by ``_dispatch_node()`` to the scheduler's
    ``run()`` loop.

    See ``runtime_integration_plan.md`` §4.2.

    This type captures the full outcome of a node dispatch: which failure
    origin applied (if any), whether the exit gate was evaluated, and the
    detailed agent and gate results.
    """

    node_id: str
    """Canonical manifest node ID."""

    final_state: str
    """One of the existing terminal states: ``"released"``,
    ``"blocked_at_entry"``, ``"blocked_at_exit"``,
    ``"hard_block_upstream"``."""

    exit_gate_evaluated: bool
    """``True`` only when ``evaluate_gate()`` was actually called on the
    exit gate.  ``False`` for entry-gate failures and agent-body failures."""

    failure_origin: str | None = None
    """``"entry_gate"`` | ``"agent_body"`` | ``"exit_gate"`` | ``None``.
    ``None`` when the node was released successfully."""

    gate_result: dict[str, Any] | None = None
    """Last gate result dict, or ``None`` if no gate was evaluated."""

    agent_result: AgentResult | None = None
    """``None`` when entry gate failed before agent execution."""

    failure_reason: str | None = None
    """Human-readable failure description, or ``None`` on success."""

    failure_category: str | None = None
    """Failure category from the failing layer, or ``None`` on success."""
