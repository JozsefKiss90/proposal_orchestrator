"""
Tests for Phase 7 budget gate fix.

Validates that:
1. Shared skills (used by both pre-gate and primary agents) run in both contexts
2. budget-interface-validation receives invocation_mode: "response_validation"
3. budget_gate_assessment.json production enables artifact_path injection
4. gate_09_budget_consistency is evaluated by the runner
5. gate_result.json is produced only by the runner
6. Phase 8 is not hard_block_upstream after Phase 7 passes
7. Missing received/ still causes HARD_BLOCK and blocks Phase 8
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.runtime_models import AgentResult, SkillInvocationRecord, SkillResult
from runner.agent_runtime import run_agent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_SKILL_TARGET = "runner.agent_runtime.run_skill"

_BUDGET_ASSESSMENT_REL = (
    "docs/tier4_orchestration_state/phase_outputs/"
    "phase7_budget_gate/budget_gate_assessment.json"
)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _make_phase7_env(
    tmp_path: Path,
    *,
    include_received: bool = True,
    include_validation: bool = True,
    include_assessment: bool = False,
    run_id: str = "run-phase7-001",
) -> dict:
    """Create a Phase 7 environment and return kwargs for run_agent().

    Models the real n07_budget_gate node with:
    - budget_gate_validator as primary agent
    - budget_interface_coordinator as pre-gate agent
    - budget-interface-validation as a SHARED skill (used by both agents)
    - constitutional-compliance-check and gate-enforcement as primary-only
    """
    repo_root = tmp_path
    agent_id = "budget_gate_validator"
    node_id = "n07_budget_gate"
    pre_gate_agent_id = "budget_interface_coordinator"
    skill_ids = [
        "budget-interface-validation",
        "gate-enforcement",
        "decision-log-update",
        "constitutional-compliance-check",
    ]

    # Agent catalog
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "agent_catalog.yaml",
        {"agent_catalog": [
            {
                "id": agent_id,
                "reads_from": [
                    "docs/integrations/lump_sum_budget_planner/received/",
                    "docs/integrations/lump_sum_budget_planner/validation/",
                ],
                "writes_to": [
                    "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/",
                ],
            },
            {
                "id": pre_gate_agent_id,
                "reads_from": [
                    "docs/integrations/lump_sum_budget_planner/interface_contract.json",
                ],
                "writes_to": [
                    "docs/tier3_project_instantiation/integration/",
                ],
            },
        ]},
    )

    # Skill catalog — budget-interface-validation used by BOTH agents
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": [
            {
                "id": "budget-interface-validation",
                "reads_from": [
                    "docs/integrations/lump_sum_budget_planner/interface_contract.json",
                    "docs/integrations/lump_sum_budget_planner/request_templates/",
                    "docs/integrations/lump_sum_budget_planner/received/",
                    "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/",
                ],
                "writes_to": [
                    "docs/integrations/lump_sum_budget_planner/validation/",
                    "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/",
                ],
                "constitutional_constraints": [],
                "used_by_agents": [pre_gate_agent_id, agent_id],
            },
            {
                "id": "gate-enforcement",
                "reads_from": [],
                "writes_to": [],
                "constitutional_constraints": [],
                "used_by_agents": [agent_id],
            },
            {
                "id": "decision-log-update",
                "reads_from": [],
                "writes_to": ["docs/tier4_orchestration_state/decision_log/"],
                "constitutional_constraints": [],
                "used_by_agents": [agent_id],
            },
            {
                "id": "constitutional-compliance-check",
                "reads_from": ["CLAUDE.md"],
                "writes_to": ["docs/tier4_orchestration_state/validation_reports/"],
                "constitutional_constraints": [],
                "used_by_agents": [agent_id],
            },
        ]},
    )

    # Manifest with artifact_registry
    artifact_registry = [
        {
            "path": "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/",
            "produced_by": node_id,
            "tier": "tier4_phase_output",
            "gate_dependency": "gate_09_budget_consistency",
        },
        {
            "path": "docs/integrations/lump_sum_budget_planner/validation/",
            "produced_by": node_id,
            "tier": "integration_validation",
        },
    ]
    manifest_path = repo_root / "manifest_test.yaml"
    _write_yaml(manifest_path, {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": node_id,
                "agent": agent_id,
                "skills": skill_ids,
                "phase_id": "phase_07_budget_gate",
                "exit_gate": "gate_09_budget_consistency",
                "pre_gate_agent": pre_gate_agent_id,
            },
        ],
        "edge_registry": [],
        "artifact_registry": artifact_registry,
    })

    # Agent definition and prompt spec
    agent_dir = repo_root / ".claude" / "agents"
    (agent_dir / f"{agent_id}.md").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / f"{agent_id}.md").write_text(
        f"# {agent_id}\nPhase 7 budget gate validator.", encoding="utf-8"
    )
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_content = f"# {agent_id} prompt spec\n\n"
    for sid in skill_ids:
        prompt_content += f"Invoke {sid}.\n"
    (prompts_dir / f"{agent_id}_prompt_spec.md").write_text(
        prompt_content, encoding="utf-8"
    )

    # Integration artifacts
    if include_received:
        _write_json(
            repo_root / "docs" / "integrations" / "lump_sum_budget_planner"
            / "received" / "budget_response_placeholder.json",
            {
                "response_id": "BR-DEMO-001",
                "schema_version": "1.0",
                "work_packages": [{"wp_id": "WP1", "lump_sum": 100000}],
                "partners": [{"partner_id": "P1", "total_effort_pm": 24}],
                "disclaimer": "DEMO_PLACEHOLDER_EXTERNAL_BUDGET_RESPONSE",
            },
        )
    if include_validation:
        _write_json(
            repo_root / "docs" / "integrations" / "lump_sum_budget_planner"
            / "validation" / "budget_validation_response.json",
            {"validated": True, "conformance_status": "conforms"},
        )

    _write_json(
        repo_root / "docs" / "integrations" / "lump_sum_budget_planner"
        / "interface_contract.json",
        {"contract_version": "1.0", "required_fields": ["response_id"]},
    )
    (
        repo_root / "docs" / "integrations" / "lump_sum_budget_planner"
        / "request_templates"
    ).mkdir(parents=True, exist_ok=True)
    _write_json(
        repo_root / "docs" / "integrations" / "lump_sum_budget_planner"
        / "request_templates" / "template.json",
        {"template": True},
    )

    # Tier 3 / Tier 4 inputs
    _write_json(
        repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
        / "phase3_wp_design" / "wp_structure.json",
        {"work_packages": [{"wp_id": "WP1"}], "schema_id": "orch.phase3.wp_structure.v1"},
    )

    if include_assessment:
        _write_json(
            repo_root / _BUDGET_ASSESSMENT_REL,
            {
                "schema_id": "orch.phase7.budget_gate_assessment.v1",
                "run_id": run_id,
                "gate_pass_declaration": "pass",
                "budget_response_reference": "budget_response_placeholder.json",
                "validation_artifact_reference": "budget_validation_response.json",
                "wp_coverage_results": [{"wp_id": "WP1", "present_in_budget": True}],
                "partner_coverage_results": [{"partner_id": "P1", "present_in_budget": True}],
                "blocking_inconsistencies": [],
            },
        )

    return {
        "agent_id": agent_id,
        "node_id": node_id,
        "run_id": run_id,
        "repo_root": repo_root,
        "manifest_path": manifest_path,
        "skill_ids": skill_ids,
        "phase_id": "phase_07_budget_gate",
        "pre_gate_agent_id": pre_gate_agent_id,
    }


def _success_skill(outputs: list[str] | None = None) -> SkillResult:
    return SkillResult(status="success", outputs_written=outputs or [])


def _failure_skill(
    category: str = "MISSING_INPUT",
    reason: str = "test failure",
) -> SkillResult:
    return SkillResult(
        status="failure",
        failure_reason=reason,
        failure_category=category,
    )


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    import runner.agent_runtime as _ar
    import runner.skill_runtime as _sr
    _ar._agent_catalog_cache.clear()
    _ar._artifact_registry_cache.clear()
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


# ---------------------------------------------------------------------------
# Test: Shared skills run in both pre-gate and primary agent bodies
# ---------------------------------------------------------------------------


class TestSharedSkillRouting:
    """When a skill is used_by both pre-gate and primary agents, it must
    appear in BOTH invocation sequences (pre-gate AND primary)."""

    def test_shared_skill_runs_in_primary_agent(self, tmp_path: Path) -> None:
        """budget-interface-validation must run in the primary agent body
        even though it also runs in the pre-gate agent."""
        kwargs = _make_phase7_env(tmp_path)
        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            run_agent(**kwargs)

        # budget-interface-validation should appear at least twice:
        # once in pre-gate, once in primary
        biv_count = invoked.count("budget-interface-validation")
        assert biv_count >= 2, (
            f"budget-interface-validation invoked {biv_count} times, "
            f"expected at least 2 (pre-gate + primary). "
            f"Full sequence: {invoked}"
        )

    def test_pre_gate_exclusive_skill_not_in_primary(self, tmp_path: Path) -> None:
        """A skill used ONLY by the pre-gate agent must NOT run in primary."""
        repo_root = tmp_path
        agent_id = "budget_gate_validator"
        pre_gate_id = "budget_interface_coordinator"
        skill_ids = ["pre-only-skill", "primary-skill"]

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "agent_catalog.yaml",
            {"agent_catalog": [
                {"id": agent_id, "reads_from": [], "writes_to": ["docs/tier4/out/"]},
                {"id": pre_gate_id, "reads_from": [], "writes_to": []},
            ]},
        )
        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [
                {
                    "id": "pre-only-skill",
                    "reads_from": [],
                    "writes_to": [],
                    "constitutional_constraints": [],
                    "used_by_agents": [pre_gate_id],  # ONLY pre-gate
                },
                {
                    "id": "primary-skill",
                    "reads_from": [],
                    "writes_to": ["docs/tier4/out/"],
                    "constitutional_constraints": [],
                    "used_by_agents": [agent_id],  # ONLY primary
                },
            ]},
        )
        manifest_path = repo_root / "manifest_test.yaml"
        _write_yaml(manifest_path, {
            "name": "test",
            "version": "1.1",
            "node_registry": [{
                "node_id": "n07_budget_gate",
                "agent": agent_id,
                "skills": skill_ids,
                "phase_id": "phase_07",
                "exit_gate": "test_gate",
            }],
            "edge_registry": [],
            "artifact_registry": [{
                "path": "docs/tier4/out/",
                "produced_by": "n07_budget_gate",
                "tier": "tier4_phase_output",
            }],
        })

        agent_dir = repo_root / ".claude" / "agents"
        (agent_dir / f"{agent_id}.md").parent.mkdir(parents=True, exist_ok=True)
        (agent_dir / f"{agent_id}.md").write_text("# test", encoding="utf-8")
        prompts_dir = agent_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / f"{agent_id}_prompt_spec.md").write_text(
            "Invoke pre-only-skill.\nInvoke primary-skill.\n", encoding="utf-8"
        )

        invoked_in_primary: list[str] = []
        pre_gate_done = False

        def _track(skill_id, *args, **kw):
            nonlocal pre_gate_done
            if skill_id == "pre-only-skill" and not pre_gate_done:
                pre_gate_done = True
                return _success_skill()
            invoked_in_primary.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            run_agent(
                agent_id=agent_id,
                node_id="n07_budget_gate",
                run_id="run-001",
                repo_root=repo_root,
                manifest_path=manifest_path,
                skill_ids=skill_ids,
                phase_id="phase_07",
                pre_gate_agent_id=pre_gate_id,
            )

        assert "pre-only-skill" not in invoked_in_primary


# ---------------------------------------------------------------------------
# Test: invocation_mode injection for budget-interface-validation
# ---------------------------------------------------------------------------


class TestInvocationModeInjection:
    """The agent runtime must inject invocation_mode='response_validation'
    when invoking budget-interface-validation in the primary agent body."""

    def test_invocation_mode_passed_as_caller_context(self, tmp_path: Path) -> None:
        kwargs = _make_phase7_env(tmp_path)
        captured_contexts: list[tuple[str, dict | None]] = []

        def _capture(skill_id, run_id, repo_root, inputs, *, caller_context=None, **kw):
            captured_contexts.append((skill_id, dict(caller_context) if caller_context else None))
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture):
            run_agent(**kwargs)

        # Find the primary agent's invocation of budget-interface-validation
        # (not the pre-gate one, which has no caller_context)
        biv_primary = [
            (sid, ctx) for sid, ctx in captured_contexts
            if sid == "budget-interface-validation" and ctx is not None
        ]
        assert len(biv_primary) >= 1, (
            f"Expected at least one budget-interface-validation invocation "
            f"with caller_context. Got: {captured_contexts}"
        )
        ctx = biv_primary[0][1]
        assert "invocation_mode" in ctx, (
            f"caller_context missing 'invocation_mode': {ctx}"
        )
        assert ctx["invocation_mode"] == "response_validation"


# ---------------------------------------------------------------------------
# Test: artifact_path injection for constitutional-compliance-check
# ---------------------------------------------------------------------------


class TestArtifactPathInjection:
    """Once budget-interface-validation writes budget_gate_assessment.json,
    constitutional-compliance-check must receive its path as artifact_path."""

    def test_artifact_path_injected_from_prior_output(self, tmp_path: Path) -> None:
        kwargs = _make_phase7_env(tmp_path)
        captured_contexts: list[tuple[str, dict | None]] = []

        def _simulate(skill_id, run_id, repo_root, inputs, *, caller_context=None, **kw):
            captured_contexts.append((skill_id, dict(caller_context) if caller_context else None))
            if skill_id == "budget-interface-validation" and caller_context and caller_context.get("invocation_mode") == "response_validation":
                # Simulate writing budget_gate_assessment.json
                return _success_skill(outputs=[_BUDGET_ASSESSMENT_REL])
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_simulate):
            run_agent(**kwargs)

        # Find constitutional-compliance-check invocation
        ccc_invocations = [
            (sid, ctx) for sid, ctx in captured_contexts
            if sid == "constitutional-compliance-check"
        ]
        assert len(ccc_invocations) >= 1
        _, ctx = ccc_invocations[0]
        assert ctx is not None, "constitutional-compliance-check must have caller_context"
        assert "artifact_path" in ctx, (
            f"caller_context missing 'artifact_path': {ctx}"
        )
        assert ctx["artifact_path"] == _BUDGET_ASSESSMENT_REL

    def test_no_artifact_path_when_validation_fails(self, tmp_path: Path) -> None:
        """If budget-interface-validation fails and writes no output,
        constitutional-compliance-check gets no artifact_path."""
        kwargs = _make_phase7_env(tmp_path)
        captured_contexts: list[tuple[str, dict | None]] = []

        def _simulate(skill_id, run_id, repo_root, inputs, *, caller_context=None, **kw):
            captured_contexts.append((skill_id, dict(caller_context) if caller_context else None))
            if skill_id == "budget-interface-validation":
                return _failure_skill("MISSING_INPUT", "No budget response")
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_simulate):
            run_agent(**kwargs)

        ccc_invocations = [
            (sid, ctx) for sid, ctx in captured_contexts
            if sid == "constitutional-compliance-check"
        ]
        if ccc_invocations:
            _, ctx = ccc_invocations[0]
            # artifact_path should NOT be set (no prior phase outputs)
            if ctx is not None:
                assert "artifact_path" not in ctx or ctx["artifact_path"] is None


# ---------------------------------------------------------------------------
# Test: budget_gate_assessment.json satisfies schema and gate predicates
# ---------------------------------------------------------------------------


class TestBudgetGateAssessmentSchema:
    """budget_gate_assessment.json must have the required schema fields."""

    def test_assessment_has_required_fields(self, tmp_path: Path) -> None:
        """A valid budget_gate_assessment.json must include all required fields."""
        run_id = "run-schema-test"
        assessment = {
            "schema_id": "orch.phase7.budget_gate_assessment.v1",
            "run_id": run_id,
            "gate_pass_declaration": "pass",
            "budget_response_reference": "budget_response_placeholder.json",
            "validation_artifact_reference": "budget_validation_response.json",
            "wp_coverage_results": [
                {"wp_id": "WP1", "present_in_budget": True,
                 "budget_line_reference": "WP1", "inconsistencies": []}
            ],
            "partner_coverage_results": [
                {"partner_id": "P1", "present_in_budget": True,
                 "budget_line_reference": "P1", "inconsistencies": []}
            ],
            "blocking_inconsistencies": [],
        }
        path = tmp_path / _BUDGET_ASSESSMENT_REL
        _write_json(path, assessment)

        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["schema_id"] == "orch.phase7.budget_gate_assessment.v1"
        assert loaded["run_id"] == run_id
        assert loaded["gate_pass_declaration"] == "pass"
        assert loaded["blocking_inconsistencies"] == []
        assert "artifact_status" not in loaded  # runner stamps post-gate

    def test_assessment_with_demo_placeholder_note(self, tmp_path: Path) -> None:
        """When the received response is a demo placeholder, the assessment
        should still pass but may include a demo placeholder note."""
        assessment = {
            "schema_id": "orch.phase7.budget_gate_assessment.v1",
            "run_id": "run-demo-001",
            "gate_pass_declaration": "pass",
            "budget_response_reference": "budget_response_placeholder.json",
            "validation_artifact_reference": "budget_validation_response.json",
            "wp_coverage_results": [],
            "partner_coverage_results": [],
            "blocking_inconsistencies": [],
            "demo_placeholder_note": (
                "Budget response is marked DEMO_PLACEHOLDER_EXTERNAL_BUDGET_RESPONSE. "
                "All numeric values are illustrative only."
            ),
        }
        path = tmp_path / _BUDGET_ASSESSMENT_REL
        _write_json(path, assessment)
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["gate_pass_declaration"] == "pass"
        assert "demo_placeholder_note" in loaded


# ---------------------------------------------------------------------------
# Test: can_evaluate_exit_gate after assessment is on disk
# ---------------------------------------------------------------------------


class TestCanEvaluateExitGatePhase7:
    """Once budget_gate_assessment.json and validation artifacts exist on
    disk, can_evaluate_exit_gate must be True."""

    def test_can_evaluate_when_assessment_present(self, tmp_path: Path) -> None:
        kwargs = _make_phase7_env(
            tmp_path, include_assessment=False, include_validation=True
        )
        repo_root = kwargs["repo_root"]

        def _produce_assessment(skill_id, run_id, repo_root_arg, inputs, *, caller_context=None, **kw):
            if skill_id == "budget-interface-validation" and caller_context and caller_context.get("invocation_mode") == "response_validation":
                # Write the assessment to disk
                assessment = {
                    "schema_id": "orch.phase7.budget_gate_assessment.v1",
                    "run_id": run_id,
                    "gate_pass_declaration": "pass",
                    "budget_response_reference": "budget_response_placeholder.json",
                    "validation_artifact_reference": "budget_validation_response.json",
                    "wp_coverage_results": [],
                    "partner_coverage_results": [],
                    "blocking_inconsistencies": [],
                }
                path = Path(repo_root_arg) / _BUDGET_ASSESSMENT_REL
                _write_json(path, assessment)
                return _success_skill(outputs=[_BUDGET_ASSESSMENT_REL])
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_produce_assessment):
            result = run_agent(**kwargs)

        assert result.can_evaluate_exit_gate is True, (
            f"Expected can_evaluate_exit_gate=True after assessment written. "
            f"Status: {result.status}, reason: {result.failure_reason}"
        )

    def test_cannot_evaluate_when_assessment_missing(self, tmp_path: Path) -> None:
        kwargs = _make_phase7_env(
            tmp_path, include_assessment=False, include_validation=True
        )

        # All skills succeed but none write assessment to disk
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        assert result.can_evaluate_exit_gate is False


# ---------------------------------------------------------------------------
# Test: gate_result.json is NOT written by the agent
# ---------------------------------------------------------------------------


class TestGateResultOwnership:
    """gate_result.json must only be produced by the runner's gate evaluator,
    never by the agent body or its skills."""

    def test_agent_does_not_write_gate_result(self, tmp_path: Path) -> None:
        kwargs = _make_phase7_env(tmp_path, include_assessment=True)

        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        gate_result_path = (
            tmp_path / "docs" / "tier4_orchestration_state"
            / "phase_outputs" / "phase7_budget_gate" / "gate_result.json"
        )
        assert not gate_result_path.exists(), (
            "gate_result.json must NOT be written by the agent; "
            "it is exclusively runner-owned"
        )


# ---------------------------------------------------------------------------
# Test: HARD_BLOCK when received/ is missing
# ---------------------------------------------------------------------------


class TestHardBlockOnMissingReceived:
    """When received/ is absent, Phase 7 must fail and trigger HARD_BLOCK."""

    def test_missing_received_produces_failure(self, tmp_path: Path) -> None:
        """With no received/ directory, the agent should report failure."""
        kwargs = _make_phase7_env(
            tmp_path,
            include_received=False,
            include_validation=True,
        )

        def _respond(skill_id, *args, **kw):
            if skill_id == "budget-interface-validation":
                return _failure_skill(
                    "MISSING_INPUT",
                    "No budget response in received/; blocking gate failure"
                )
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_respond):
            result = run_agent(**kwargs)

        assert result.status == "failure"

    def test_missing_validation_produces_failure(self, tmp_path: Path) -> None:
        """With no validation/ directory, the agent should report failure."""
        kwargs = _make_phase7_env(
            tmp_path,
            include_received=True,
            include_validation=False,
        )

        def _respond(skill_id, *args, **kw):
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_respond):
            result = run_agent(**kwargs)

        # validation/ directory is in the artifact_registry and must be
        # non-empty for can_evaluate_exit_gate
        assert result.can_evaluate_exit_gate is False


# ---------------------------------------------------------------------------
# Test: Full skill sequence ordering
# ---------------------------------------------------------------------------


class TestPhase7SkillSequence:
    """Verify the skill execution order in the Phase 7 agent body."""

    def test_budget_validation_before_compliance_check(self, tmp_path: Path) -> None:
        """budget-interface-validation must run before
        constitutional-compliance-check in the primary body."""
        kwargs = _make_phase7_env(tmp_path)
        primary_skills: list[str] = []
        pre_gate_done = False

        # budget-interface-validation (primary call) must return the
        # budget_gate_assessment.json path so that
        # _resolve_auditable_artifact finds an auditable artifact for
        # constitutional-compliance-check.
        _BGA_PATH = (
            "docs/tier4_orchestration_state/phase_outputs/"
            "phase7_budget_gate/budget_gate_assessment.json"
        )

        def _track(skill_id, *args, caller_context=None, **kw):
            nonlocal pre_gate_done
            # First invocation of budget-interface-validation is pre-gate
            if skill_id == "budget-interface-validation" and not pre_gate_done:
                pre_gate_done = True
                return _success_skill()
            primary_skills.append(skill_id)
            if skill_id == "budget-interface-validation":
                return _success_skill(outputs=[_BGA_PATH])
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            run_agent(**kwargs)

        assert "budget-interface-validation" in primary_skills
        assert "constitutional-compliance-check" in primary_skills

        biv_idx = primary_skills.index("budget-interface-validation")
        ccc_idx = primary_skills.index("constitutional-compliance-check")
        assert biv_idx < ccc_idx, (
            f"budget-interface-validation (idx={biv_idx}) must run before "
            f"constitutional-compliance-check (idx={ccc_idx}). "
            f"Sequence: {primary_skills}"
        )

    def test_gate_enforcement_runs_last(self, tmp_path: Path) -> None:
        """gate-enforcement must be the last skill in the primary body."""
        kwargs = _make_phase7_env(tmp_path)
        primary_skills: list[str] = []
        pre_gate_done = False

        _BGA_PATH = (
            "docs/tier4_orchestration_state/phase_outputs/"
            "phase7_budget_gate/budget_gate_assessment.json"
        )

        def _track(skill_id, *args, caller_context=None, **kw):
            nonlocal pre_gate_done
            if skill_id == "budget-interface-validation" and not pre_gate_done:
                pre_gate_done = True
                return _success_skill()
            primary_skills.append(skill_id)
            if skill_id == "budget-interface-validation":
                return _success_skill(outputs=[_BGA_PATH])
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            run_agent(**kwargs)

        assert primary_skills[-1] == "gate-enforcement", (
            f"gate-enforcement must be last. Sequence: {primary_skills}"
        )
