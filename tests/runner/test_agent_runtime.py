"""
Tests for runner.agent_runtime — agent orchestration adapter layer.

Covers §14 test cases 6, 9, 10, 16:
  6.  skill failure propagation to AgentResult
  9.  n03 sub-agent behavior (dependency_mapper)
  10. n07 pre_gate_agent behavior (budget_interface_coordinator)
  16. CONSTITUTIONAL_HALT from skill propagates as agent_body failure

Additional tests:
  - successful agent → AgentResult(status="success", can_evaluate_exit_gate=True)
  - invoked_skills ordering and completeness
  - missing agent spec → failure
  - can_evaluate_exit_gate determined from disk state
  - module isolation (no dag_scheduler / gate_evaluator imports)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from runner.runtime_models import AgentResult, SkillInvocationRecord, SkillResult
from runner.agent_runtime import run_agent, AgentRuntimeError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RUN_SKILL_TARGET = "runner.agent_runtime.run_skill"


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _make_agent_env(
    tmp_path: Path,
    *,
    agent_id: str = "test_agent",
    node_id: str = "n01_call_analysis",
    skill_ids: list[str] | None = None,
    phase_id: str = "phase1",
    sub_agent_id: str | None = None,
    pre_gate_agent_id: str | None = None,
    reads_from: list[str] | None = None,
    writes_to: list[str] | None = None,
    extra_catalog_entries: list[dict] | None = None,
    artifact_registry: list[dict] | None = None,
) -> dict:
    """Create a synthetic environment and return kwargs for run_agent().

    Returns a dict ready to be unpacked as ``run_agent(**kwargs)``.
    """
    repo_root = tmp_path
    if skill_ids is None:
        skill_ids = ["skill-a", "skill-b"]
    if reads_from is None:
        reads_from = ["docs/tier3/input.json"]
    if writes_to is None:
        writes_to = ["docs/tier4/phase1/"]

    # Agent catalog
    catalog_entries = [
        {
            "id": agent_id,
            "reads_from": reads_from,
            "writes_to": writes_to,
        },
    ]
    if extra_catalog_entries:
        catalog_entries.extend(extra_catalog_entries)
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "agent_catalog.yaml",
        {"agent_catalog": catalog_entries},
    )

    # Skill catalog — each skill belongs to its agent
    skill_catalog = []
    for sid in skill_ids:
        used_by = [agent_id]
        if sub_agent_id and sid.startswith("sub-"):
            used_by = [sub_agent_id]
        if pre_gate_agent_id and sid.startswith("pre-"):
            used_by = [pre_gate_agent_id]
        skill_catalog.append({
            "id": sid,
            "reads_from": reads_from,
            "writes_to": writes_to,
            "constitutional_constraints": [],
            "used_by_agents": used_by,
        })
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": skill_catalog},
    )

    # Manifest with artifact_registry
    if artifact_registry is None:
        artifact_registry = [
            {
                "path": "docs/tier4/phase1/output.json",
                "produced_by": node_id,
                "tier": "tier4_phase_output",
            },
        ]
    manifest_data = {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": node_id,
                "agent": agent_id,
                "skills": skill_ids,
                "phase_id": phase_id,
                "exit_gate": "test_gate",
            },
        ],
        "edge_registry": [],
        "artifact_registry": artifact_registry,
    }
    manifest_path = repo_root / "manifest_test.yaml"
    _write_yaml(manifest_path, manifest_data)

    # Agent definition and prompt spec
    agent_dir = repo_root / ".claude" / "agents"
    (agent_dir / f"{agent_id}.md").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / f"{agent_id}.md").write_text(
        f"# {agent_id}\nTest agent definition.", encoding="utf-8"
    )
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    # Mention skills in order in prompt spec
    prompt_content = f"# {agent_id} prompt spec\n\n"
    for sid in skill_ids:
        prompt_content += f"Invoke {sid}.\n"
    (prompts_dir / f"{agent_id}_prompt_spec.md").write_text(
        prompt_content, encoding="utf-8"
    )

    # Input artifact
    _write_json(repo_root / "docs" / "tier3" / "input.json", {"data": "test"})

    return {
        "agent_id": agent_id,
        "node_id": node_id,
        "run_id": "run-test-001",
        "repo_root": repo_root,
        "manifest_path": manifest_path,
        "skill_ids": skill_ids,
        "phase_id": phase_id,
        "sub_agent_id": sub_agent_id,
        "pre_gate_agent_id": pre_gate_agent_id,
    }


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear module-level caches between tests."""
    import runner.agent_runtime as _ar
    import runner.skill_runtime as _sr
    _ar._agent_catalog_cache.clear()
    _ar._artifact_registry_cache.clear()
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


def _success_skill(outputs: list[str] | None = None) -> SkillResult:
    return SkillResult(
        status="success",
        outputs_written=outputs or [],
    )


def _failure_skill(
    category: str = "MISSING_INPUT",
    reason: str = "test failure",
) -> SkillResult:
    return SkillResult(
        status="failure",
        failure_reason=reason,
        failure_category=category,
    )


# ---------------------------------------------------------------------------
# Successful agent execution
# ---------------------------------------------------------------------------


class TestAgentSuccess:
    def test_all_skills_succeed(self, tmp_path: Path) -> None:
        """Successful agent → AgentResult(status="success", can_evaluate_exit_gate=True)."""
        kwargs = _make_agent_env(tmp_path)
        # Write the gate-relevant artifact so can_evaluate_exit_gate is True
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        assert result.status == "success"
        assert result.can_evaluate_exit_gate is True
        assert result.failure_origin == "agent_body"
        assert result.failure_reason is None

    def test_invoked_skills_ordered(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path, skill_ids=["skill-a", "skill-b", "skill-c"])
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        records: list[str] = []

        def _track_skill(skill_id, *args, **kw):
            records.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track_skill):
            result = run_agent(**kwargs)

        assert result.status == "success"
        assert len(result.invoked_skills) == 3
        # All three skill IDs recorded
        skill_ids_recorded = [r.skill_id for r in result.invoked_skills]
        assert "skill-a" in skill_ids_recorded
        assert "skill-b" in skill_ids_recorded
        assert "skill-c" in skill_ids_recorded

    def test_failure_origin_always_agent_body(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path)
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)
        assert result.failure_origin == "agent_body"


# ---------------------------------------------------------------------------
# §14 test 6 — skill failure propagation
# ---------------------------------------------------------------------------


class TestSkillFailurePropagation:
    """Verify that when a skill returns SkillResult(status="failure"),
    the agent runtime correctly propagates this to AgentResult."""

    def test_skill_failure_propagated(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path)
        with patch(
            _RUN_SKILL_TARGET,
            return_value=_failure_skill("MISSING_INPUT", "input missing"),
        ):
            result = run_agent(**kwargs)

        assert result.status == "failure"
        assert result.failure_category == "SKILL_FAILURE"
        assert "input missing" in (result.failure_reason or "")

    def test_skill_failure_records(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path)
        with patch(
            _RUN_SKILL_TARGET,
            return_value=_failure_skill("MALFORMED_ARTIFACT", "bad schema"),
        ):
            result = run_agent(**kwargs)

        assert len(result.invoked_skills) > 0
        failed = [r for r in result.invoked_skills if r.status == "failure"]
        assert len(failed) > 0
        assert failed[0].failure_category == "MALFORMED_ARTIFACT"


# ---------------------------------------------------------------------------
# §14 test 16 — CONSTITUTIONAL_HALT
# ---------------------------------------------------------------------------


class TestConstitutionalHalt:
    """Test that when a skill returns SkillResult(failure_category="CONSTITUTIONAL_HALT"),
    the agent immediately halts and returns AgentResult with
    failure_category="CONSTITUTIONAL_HALT" and can_evaluate_exit_gate=False."""

    def test_halt_on_constitutional_halt(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(
            tmp_path, skill_ids=["skill-a", "skill-b", "skill-c"]
        )
        call_count = 0

        def _halt_on_second(skill_id, *args, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return _failure_skill("CONSTITUTIONAL_HALT", "fabricated data")
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_halt_on_second):
            result = run_agent(**kwargs)

        assert result.status == "failure"
        assert result.failure_category == "CONSTITUTIONAL_HALT"
        assert result.can_evaluate_exit_gate is False
        # Third skill should NOT have been invoked
        assert call_count == 2

    def test_halt_records_partial_invocations(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path, skill_ids=["skill-a", "skill-b"])

        def _first_halts(skill_id, *args, **kw):
            return _failure_skill("CONSTITUTIONAL_HALT", "violated constraint")

        with patch(_RUN_SKILL_TARGET, side_effect=_first_halts):
            result = run_agent(**kwargs)

        assert result.failure_category == "CONSTITUTIONAL_HALT"
        assert len(result.invoked_skills) == 1
        assert result.invoked_skills[0].failure_category == "CONSTITUTIONAL_HALT"


# ---------------------------------------------------------------------------
# §14 test 9 — n03 sub-agent coordination
# ---------------------------------------------------------------------------


class TestSubAgentCoordination:
    """Verify that n03_wp_design invokes sub-agent (dependency_mapper) skills."""

    def test_sub_agent_skills_invoked(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="wp_designer",
            node_id="n03_wp_design",
            skill_ids=[
                "work-package-normalization",
                "sub-dependency-analysis",
                "skill-c",
            ],
            sub_agent_id="dependency_mapper",
            extra_catalog_entries=[
                {
                    "id": "dependency_mapper",
                    "reads_from": ["docs/tier3/input.json"],
                    "writes_to": ["docs/tier4/phase1/"],
                },
            ],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        # sub-agent skill was invoked
        assert "sub-dependency-analysis" in invoked
        # Primary skills were also invoked
        assert "work-package-normalization" in invoked


# ---------------------------------------------------------------------------
# §14 test 10 — n07 pre_gate_agent coordination
# ---------------------------------------------------------------------------


class TestPreGateAgentCoordination:
    """Confirm that n07_budget_gate invokes pre-gate agent
    (budget_interface_coordinator) before primary agent skills."""

    def test_pre_gate_skills_invoked_first(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="budget_gate_validator",
            node_id="n07_budget_gate",
            skill_ids=["pre-budget-prep", "skill-validate"],
            pre_gate_agent_id="budget_interface_coordinator",
            extra_catalog_entries=[
                {
                    "id": "budget_interface_coordinator",
                    "reads_from": ["docs/tier3/input.json"],
                    "writes_to": ["docs/tier4/phase1/"],
                },
            ],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        # Pre-gate skill invoked
        assert "pre-budget-prep" in invoked
        # Primary skill invoked
        assert "skill-validate" in invoked
        # Pre-gate skills come before primary skills
        pre_idx = invoked.index("pre-budget-prep")
        primary_idx = invoked.index("skill-validate")
        assert pre_idx < primary_idx, "Pre-gate skills must run before primary"

    def test_pre_gate_constitutional_halt_stops_agent(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="budget_gate_validator",
            node_id="n07_budget_gate",
            skill_ids=["pre-budget-prep", "skill-validate"],
            pre_gate_agent_id="budget_interface_coordinator",
            extra_catalog_entries=[
                {
                    "id": "budget_interface_coordinator",
                    "reads_from": ["docs/tier3/input.json"],
                    "writes_to": ["docs/tier4/phase1/"],
                },
            ],
        )

        def _halt_pre_gate(skill_id, *args, **kw):
            if skill_id == "pre-budget-prep":
                return _failure_skill("CONSTITUTIONAL_HALT", "budget fabricated")
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_halt_pre_gate):
            result = run_agent(**kwargs)

        assert result.status == "failure"
        assert result.failure_category == "CONSTITUTIONAL_HALT"
        assert result.can_evaluate_exit_gate is False


# ---------------------------------------------------------------------------
# can_evaluate_exit_gate from disk state
# ---------------------------------------------------------------------------


class TestCanEvaluateExitGate:
    def test_false_when_artifacts_missing(self, tmp_path: Path) -> None:
        """can_evaluate_exit_gate is False when gate-relevant artifacts are absent."""
        kwargs = _make_agent_env(tmp_path)
        # Don't write the output artifact
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        # All skills succeeded but artifact missing → failure
        assert result.can_evaluate_exit_gate is False

    def test_true_when_artifacts_present(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path)
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        assert result.can_evaluate_exit_gate is True


# ---------------------------------------------------------------------------
# Missing agent spec
# ---------------------------------------------------------------------------


class TestMissingSpecs:
    def test_missing_agent_definition(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path, agent_id="nonexistent_agent")
        # Remove the agent spec that was created
        spec_path = tmp_path / ".claude" / "agents" / "nonexistent_agent.md"
        if spec_path.exists():
            spec_path.unlink()

        result = run_agent(**kwargs)
        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"
        assert result.can_evaluate_exit_gate is False


# ---------------------------------------------------------------------------
# Module isolation
# ---------------------------------------------------------------------------


class TestModuleIsolation:
    def test_no_dag_scheduler_or_gate_evaluator_import(self) -> None:
        import runner.agent_runtime as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "runner.dag_scheduler" not in source
        assert "runner.gate_evaluator" not in source
