"""
Tests for runner.runtime_models — runtime contract data types.

Covers:
  - SkillResult construction with all fields
  - SkillInvocationRecord construction
  - AgentResult construction; ``failure_origin`` is always ``"agent_body"``
  - NodeExecutionResult construction with all three failure_origin values
  - Constants (FAILURE_ORIGINS, SKILL_FAILURE_CATEGORIES, AGENT_FAILURE_CATEGORIES)
  - Frozen (immutable) enforcement for all dataclasses
"""

from __future__ import annotations

import pytest

from runner.runtime_models import (
    AGENT_FAILURE_CATEGORIES,
    FAILURE_ORIGINS,
    SKILL_FAILURE_CATEGORIES,
    AgentResult,
    NodeExecutionResult,
    SkillInvocationRecord,
    SkillResult,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_failure_origins_members(self) -> None:
        assert FAILURE_ORIGINS == frozenset(
            {"entry_gate", "agent_body", "exit_gate"}
        )

    def test_skill_failure_categories_members(self) -> None:
        assert SKILL_FAILURE_CATEGORIES == frozenset(
            {
                "MISSING_INPUT",
                "MALFORMED_ARTIFACT",
                "CONSTRAINT_VIOLATION",
                "INCOMPLETE_OUTPUT",
                "CONSTITUTIONAL_HALT",
            }
        )

    def test_agent_failure_categories_superset(self) -> None:
        assert SKILL_FAILURE_CATEGORIES < AGENT_FAILURE_CATEGORIES

    def test_agent_failure_categories_extra_members(self) -> None:
        extra = AGENT_FAILURE_CATEGORIES - SKILL_FAILURE_CATEGORIES
        assert extra == {"SKILL_FAILURE", "AGENT_EXECUTION_ERROR"}

    def test_constants_are_frozensets(self) -> None:
        assert isinstance(FAILURE_ORIGINS, frozenset)
        assert isinstance(SKILL_FAILURE_CATEGORIES, frozenset)
        assert isinstance(AGENT_FAILURE_CATEGORIES, frozenset)


# ---------------------------------------------------------------------------
# SkillResult
# ---------------------------------------------------------------------------


class TestSkillResult:
    def test_success_construction(self) -> None:
        r = SkillResult(
            status="success",
            outputs_written=["docs/tier4/foo.json"],
        )
        assert r.status == "success"
        assert r.outputs_written == ["docs/tier4/foo.json"]
        assert r.failure_reason is None
        assert r.failure_category is None
        assert r.validation_report is None

    def test_failure_construction(self) -> None:
        r = SkillResult(
            status="failure",
            failure_reason="missing call_constraints.json",
            failure_category="MISSING_INPUT",
        )
        assert r.status == "failure"
        assert r.failure_reason == "missing call_constraints.json"
        assert r.failure_category == "MISSING_INPUT"
        assert r.outputs_written == []

    def test_defaults(self) -> None:
        r = SkillResult(status="success")
        assert r.outputs_written == []
        assert r.validation_report is None
        assert r.failure_reason is None
        assert r.failure_category is None

    def test_frozen(self) -> None:
        r = SkillResult(status="success")
        with pytest.raises(AttributeError):
            r.status = "failure"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SkillInvocationRecord
# ---------------------------------------------------------------------------


class TestSkillInvocationRecord:
    def test_construction(self) -> None:
        rec = SkillInvocationRecord(
            skill_id="call-scope-extraction",
            status="success",
            outputs_written=["docs/tier2b/extracted/scope.json"],
        )
        assert rec.skill_id == "call-scope-extraction"
        assert rec.status == "success"
        assert rec.failure_reason is None
        assert rec.failure_category is None
        assert rec.outputs_written == ["docs/tier2b/extracted/scope.json"]

    def test_failure_record(self) -> None:
        rec = SkillInvocationRecord(
            skill_id="call-scope-extraction",
            status="failure",
            failure_reason="missing input",
            failure_category="MISSING_INPUT",
        )
        assert rec.status == "failure"
        assert rec.failure_category == "MISSING_INPUT"

    def test_frozen(self) -> None:
        rec = SkillInvocationRecord(skill_id="x", status="success")
        with pytest.raises(AttributeError):
            rec.skill_id = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------


class TestAgentResult:
    def test_success_construction(self) -> None:
        r = AgentResult(
            status="success",
            can_evaluate_exit_gate=True,
            outputs_written=["docs/tier4/phase1/summary.json"],
            invoked_skills=[
                SkillInvocationRecord(skill_id="s1", status="success"),
            ],
        )
        assert r.status == "success"
        assert r.can_evaluate_exit_gate is True
        assert r.failure_origin == "agent_body"
        assert r.failure_reason is None
        assert r.failure_category is None
        assert len(r.invoked_skills) == 1

    def test_failure_origin_always_agent_body(self) -> None:
        r = AgentResult(status="failure", can_evaluate_exit_gate=False)
        assert r.failure_origin == "agent_body"

    def test_failure_origin_default_is_agent_body(self) -> None:
        r = AgentResult(status="success", can_evaluate_exit_gate=True)
        assert r.failure_origin == "agent_body"

    def test_failure_construction(self) -> None:
        r = AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason="CONSTITUTIONAL_HALT from skill",
            failure_category="CONSTITUTIONAL_HALT",
        )
        assert r.status == "failure"
        assert r.can_evaluate_exit_gate is False
        assert r.failure_category == "CONSTITUTIONAL_HALT"

    def test_defaults(self) -> None:
        r = AgentResult(status="success", can_evaluate_exit_gate=True)
        assert r.outputs_written == []
        assert r.validation_reports == []
        assert r.decision_log_writes == []
        assert r.invoked_skills == []

    def test_frozen(self) -> None:
        r = AgentResult(status="success", can_evaluate_exit_gate=True)
        with pytest.raises(AttributeError):
            r.status = "failure"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# NodeExecutionResult
# ---------------------------------------------------------------------------


class TestNodeExecutionResult:
    def test_released_construction(self) -> None:
        r = NodeExecutionResult(
            node_id="n01_call_analysis",
            final_state="released",
            exit_gate_evaluated=True,
            failure_origin=None,
        )
        assert r.node_id == "n01_call_analysis"
        assert r.final_state == "released"
        assert r.exit_gate_evaluated is True
        assert r.failure_origin is None
        assert r.gate_result is None
        assert r.agent_result is None

    def test_entry_gate_failure(self) -> None:
        r = NodeExecutionResult(
            node_id="n01_call_analysis",
            final_state="blocked_at_entry",
            exit_gate_evaluated=False,
            failure_origin="entry_gate",
            gate_result={"status": "fail"},
        )
        assert r.failure_origin == "entry_gate"
        assert r.exit_gate_evaluated is False
        assert r.agent_result is None

    def test_agent_body_failure(self) -> None:
        agent_r = AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_category="CONSTITUTIONAL_HALT",
        )
        r = NodeExecutionResult(
            node_id="n02_concept_refinement",
            final_state="blocked_at_exit",
            exit_gate_evaluated=False,
            failure_origin="agent_body",
            agent_result=agent_r,
            failure_category="CONSTITUTIONAL_HALT",
        )
        assert r.failure_origin == "agent_body"
        assert r.exit_gate_evaluated is False
        assert r.agent_result is not None
        assert r.agent_result.failure_category == "CONSTITUTIONAL_HALT"

    def test_exit_gate_failure(self) -> None:
        agent_r = AgentResult(status="success", can_evaluate_exit_gate=True)
        r = NodeExecutionResult(
            node_id="n01_call_analysis",
            final_state="blocked_at_exit",
            exit_gate_evaluated=True,
            failure_origin="exit_gate",
            gate_result={"status": "fail"},
            agent_result=agent_r,
        )
        assert r.failure_origin == "exit_gate"
        assert r.exit_gate_evaluated is True
        assert r.agent_result.status == "success"

    def test_all_three_failure_origins(self) -> None:
        for origin in FAILURE_ORIGINS:
            r = NodeExecutionResult(
                node_id="n01_call_analysis",
                final_state="blocked_at_exit",
                exit_gate_evaluated=False,
                failure_origin=origin,
            )
            assert r.failure_origin == origin

    def test_frozen(self) -> None:
        r = NodeExecutionResult(
            node_id="n01_call_analysis",
            final_state="released",
            exit_gate_evaluated=True,
        )
        with pytest.raises(AttributeError):
            r.node_id = "n02_concept_refinement"  # type: ignore[misc]
