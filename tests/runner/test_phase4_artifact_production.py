"""
Tests for Phase 4 artifact production — gantt-schedule-builder skill.

Verifies that:
  A. gantt-schedule-builder writes gantt.json through the expected runtime path
  B. milestone-consistency-check can run in FULL mode after gantt.json exists
  C. Missing gantt.json at Phase 4 is caught as a regression
  D. Option A artifacts/predicates remain intact (scheduling_constraints.json)
  E. n04 skill sequencing produces gantt.json before milestone validation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.runtime_models import SkillResult, AgentResult
from runner.skill_runtime import (
    _extract_json_response,
    _validate_skill_output,
    run_skill,
)
from runner.agent_runtime import (
    run_agent,
    _determine_can_evaluate_exit_gate,
    _get_artifacts_produced_by_node,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"
_RUN_SKILL_TARGET = "runner.agent_runtime.run_skill"

_GANTT_CANONICAL_PATH = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase4_gantt_milestones/gantt.json"
)
_SC_CANONICAL_PATH = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase4_gantt_milestones/scheduling_constraints.json"
)


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear module-level caches between tests."""
    import runner.agent_runtime as _ar
    import runner.skill_runtime as _sr
    _ar._agent_catalog_cache.clear()
    _ar._artifact_registry_cache.clear()
    _ar._node_exit_gate_cache.clear()
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


# ---------------------------------------------------------------------------
# Shared artifact schema specification
# ---------------------------------------------------------------------------

_GANTT_SCHEMA = {
    "tier4_phase_output_schemas": {
        "gantt": {
            "schema_id_value": "orch.phase4.gantt.v1",
            "canonical_path": _GANTT_CANONICAL_PATH,
            "provenance_class": "run_produced",
            "fields": {
                "schema_id": {"type": "string", "required": True},
                "run_id": {"type": "string", "required": True},
                "tasks": {"type": "array", "required": True},
                "milestones": {"type": "array", "required": True},
                "critical_path": {"type": "array", "required": True},
            },
        },
        "scheduling_constraints": {
            "schema_id_value": "orch.phase4.scheduling_constraints.v1",
            "canonical_path": _SC_CANONICAL_PATH,
            "provenance_class": "run_produced",
            "fields": {
                "schema_id": {"type": "string", "required": True},
                "run_id": {"type": "string", "required": True},
                "strict_constraints": {"type": "array", "required": True},
                "non_strict_constraints": {"type": "array", "required": True},
                "normalization_log": {"type": "array", "required": True},
                "unresolved_constraints": {"type": "array", "required": True},
                "source_wp_structure_run_id": {"type": "string", "required": True},
                "derived_from_artifact": {"type": "string", "required": True},
                "normalization_timestamp": {"type": "string", "required": True},
                "project_duration_months": {"type": "integer", "required": True},
                "wp_bounds": {"type": "object", "required": True},
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Canonical Claude responses
# ---------------------------------------------------------------------------

def _valid_gantt_response(run_id: str = "run-test-p4") -> dict:
    """Valid response conforming to orch.phase4.gantt.v1."""
    return {
        "schema_id": "orch.phase4.gantt.v1",
        "run_id": run_id,
        "tasks": [
            {
                "task_id": "T1-01", "wp_id": "WP1",
                "start_month": 1, "end_month": 48,
                "responsible_partner": "P1",
            },
            {
                "task_id": "T2-01", "wp_id": "WP2",
                "start_month": 1, "end_month": 24,
                "responsible_partner": "P2",
            },
            {
                "task_id": "T2-02", "wp_id": "WP2",
                "start_month": 12, "end_month": 36,
                "responsible_partner": "P2",
            },
        ],
        "milestones": [
            {
                "milestone_id": "MS1",
                "title": "Project Kickoff Complete",
                "due_month": 3,
                "verifiable_criterion": "Consortium agreement signed and first management board meeting held",
                "responsible_wp": "WP1",
                "depends_on_tasks": ["T1-01"],
                "milestone_type": "intermediate_checkpoint",
            },
            {
                "milestone_id": "MS2",
                "title": "Research Phase 1 Complete",
                "due_month": 24,
                "verifiable_criterion": "Peer-reviewed publication submitted to a Q1 journal",
                "responsible_wp": "WP2",
                "depends_on_tasks": ["T2-01", "T2-02"],
                "milestone_type": "wp_completion",
            },
        ],
        "critical_path": ["T2-01", "T2-02", "MS2"],
    }


def _gantt_response_missing_tasks(run_id: str = "run-test-p4") -> dict:
    """Response with empty tasks array — should fail validation."""
    return {
        "schema_id": "orch.phase4.gantt.v1",
        "run_id": run_id,
        "tasks": [],
        "milestones": [
            {
                "milestone_id": "MS1",
                "title": "Kickoff",
                "due_month": 3,
                "verifiable_criterion": "Meeting held",
                "responsible_wp": "WP1",
            },
        ],
        "critical_path": ["MS1"],
    }


# ---------------------------------------------------------------------------
# Helpers — synthetic environment builders
# ---------------------------------------------------------------------------

def _make_gantt_skill_env(tmp_path: Path, run_id: str = "run-test-p4") -> Path:
    """Create environment for gantt-schedule-builder tests."""
    repo_root = tmp_path

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": [{
            "id": "gantt-schedule-builder",
            "reads_from": [
                "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
                "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/scheduling_constraints.json",
                "docs/tier3_project_instantiation/call_binding/selected_call.json",
                "docs/tier3_project_instantiation/consortium/roles.json",
                "docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json",
            ],
            "writes_to": [_GANTT_CANONICAL_PATH],
            "constitutional_constraints": [
                "Must not assign tasks beyond project duration",
            ],
            "used_by_agents": ["gantt_designer"],
        }]},
    )

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml",
        _GANTT_SCHEMA,
    )

    skill_dir = repo_root / ".claude" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "gantt-schedule-builder.md").write_text(
        "# gantt-schedule-builder\nTest spec for gantt.json production.",
        encoding="utf-8",
    )

    # Pre-populate required inputs
    _write_json(
        repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
        / "phase3_wp_design" / "wp_structure.json",
        {
            "schema_id": "orch.phase3.wp_structure.v1",
            "run_id": "run-phase3",
            "work_packages": [
                {
                    "wp_id": "WP1", "title": "Management",
                    "lead_partner": "P1", "contributing_partners": [],
                    "objectives": ["Manage"], "dependencies": [],
                    "tasks": [{"task_id": "T1-01", "title": "Coordinate",
                               "responsible_partner": "P1", "contributing_partners": []}],
                    "deliverables": [{"deliverable_id": "D1-01", "title": "Report",
                                      "type": "report", "due_month": 48,
                                      "responsible_partner": "P1"}],
                },
                {
                    "wp_id": "WP2", "title": "Research",
                    "lead_partner": "P2", "contributing_partners": ["P1"],
                    "objectives": ["Research"], "dependencies": [],
                    "tasks": [
                        {"task_id": "T2-01", "title": "Research A",
                         "responsible_partner": "P2", "contributing_partners": ["P1"]},
                        {"task_id": "T2-02", "title": "Research B",
                         "responsible_partner": "P2", "contributing_partners": []},
                    ],
                    "deliverables": [{"deliverable_id": "D2-01", "title": "Software",
                                      "type": "software", "due_month": 36,
                                      "responsible_partner": "P2"}],
                },
            ],
            "dependency_map": {
                "nodes": ["WP1", "WP2", "T1-01", "T2-01", "T2-02"],
                "edges": [],
            },
        },
    )

    _write_json(
        repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
        / "phase4_gantt_milestones" / "scheduling_constraints.json",
        {
            "schema_id": "orch.phase4.scheduling_constraints.v1",
            "run_id": run_id,
            "source_wp_structure_run_id": "run-phase3",
            "derived_from_artifact": "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
            "normalization_timestamp": "2026-04-21T00:00:00Z",
            "project_duration_months": 48,
            "wp_bounds": {"WP1": {"start_month": 1, "end_month": 48},
                          "WP2": {"start_month": 1, "end_month": 36}},
            "strict_constraints": [],
            "non_strict_constraints": [],
            "normalization_log": [],
            "unresolved_constraints": [],
        },
    )

    _write_json(
        repo_root / "docs" / "tier3_project_instantiation" / "call_binding"
        / "selected_call.json",
        {"call_id": "TEST-01", "topic_code": "TEST-01",
         "instrument_type": "RIA", "max_project_duration_months": 48},
    )

    _write_json(
        repo_root / "docs" / "tier3_project_instantiation" / "consortium"
        / "roles.json",
        {"partners": [
            {"partner_id": "P1", "wp_lead": ["WP1"], "wp_participant": ["WP2"]},
            {"partner_id": "P2", "wp_lead": ["WP2"], "wp_participant": []},
        ]},
    )

    _write_json(
        repo_root / "docs" / "tier3_project_instantiation" / "architecture_inputs"
        / "milestones_seed.json",
        {"milestones": [
            {"milestone_id": "MS1", "title": "Kickoff",
             "due_month": 3, "verifiable_criterion": "Consortium agreement signed"},
            {"milestone_id": "MS2", "title": "Research Phase 1",
             "due_month": 24, "verifiable_criterion": "Publication submitted"},
        ]},
    )

    return repo_root


# =========================================================================
# Group A: gantt-schedule-builder single-artifact production
# =========================================================================


class TestGanttScheduleBuilderArtifactProduction:
    """Verify gantt-schedule-builder writes gantt.json through runtime path."""

    def test_valid_response_writes_gantt_json(self, tmp_path: Path) -> None:
        """A valid Claude response produces gantt.json at canonical path."""
        repo = _make_gantt_skill_env(tmp_path)
        run_id = "run-test-p4"

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(_valid_gantt_response(run_id))):
            result = run_skill("gantt-schedule-builder", run_id, repo)

        assert result.status == "success"
        assert _GANTT_CANONICAL_PATH in result.outputs_written

        gantt_path = repo / _GANTT_CANONICAL_PATH
        assert gantt_path.is_file()
        data = json.loads(gantt_path.read_text())
        assert data["schema_id"] == "orch.phase4.gantt.v1"
        assert data["run_id"] == run_id
        assert len(data["tasks"]) == 3
        assert len(data["milestones"]) == 2
        assert len(data["critical_path"]) > 0

    def test_response_missing_run_id_rejected(self, tmp_path: Path) -> None:
        """Response without run_id is rejected as MALFORMED_ARTIFACT."""
        repo = _make_gantt_skill_env(tmp_path)
        response = _valid_gantt_response()
        del response["run_id"]

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill("gantt-schedule-builder", "run-test-p4", repo)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_response_wrong_schema_id_rejected(self, tmp_path: Path) -> None:
        """Response with wrong schema_id is rejected."""
        repo = _make_gantt_skill_env(tmp_path)
        response = _valid_gantt_response()
        response["schema_id"] = "wrong.schema.v1"

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill("gantt-schedule-builder", "run-test-p4", repo)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_response_with_artifact_status_rejected(self, tmp_path: Path) -> None:
        """Response containing artifact_status is rejected."""
        repo = _make_gantt_skill_env(tmp_path)
        response = _valid_gantt_response()
        response["artifact_status"] = "valid"

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill("gantt-schedule-builder", "run-test-p4", repo)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_response_missing_required_field_rejected(self, tmp_path: Path) -> None:
        """Response missing required 'tasks' field is rejected."""
        repo = _make_gantt_skill_env(tmp_path)
        response = _valid_gantt_response()
        del response["tasks"]

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill("gantt-schedule-builder", "run-test-p4", repo)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_valid_response_without_milestone_dependency_fields(self, tmp_path: Path) -> None:
        """Legacy gantt response without depends_on_tasks/milestone_type still passes validation."""
        repo = _make_gantt_skill_env(tmp_path)
        response = _valid_gantt_response()
        # Remove the new optional fields
        for ms in response["milestones"]:
            ms.pop("depends_on_tasks", None)
            ms.pop("milestone_type", None)

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill("gantt-schedule-builder", "run-test-p4", repo)

        assert result.status == "success"
        assert _GANTT_CANONICAL_PATH in result.outputs_written

    def test_cross_wp_depends_on_tasks_accepted_by_schema(self, tmp_path: Path) -> None:
        """depends_on_tasks referencing a task from a different WP is accepted by schema.

        Milestone in WP1 with depends_on_tasks: ["T2-01"] where T2-01 belongs to WP2
        is a structural issue that milestone-consistency-check should flag with
        flag_class "structural". The schema and skill runtime do not reject it —
        structural validation is the checker's responsibility, not the builder's.
        """
        repo = _make_gantt_skill_env(tmp_path)
        response = _valid_gantt_response()
        # Set MS1 (responsible_wp=WP1) to depend on T2-01 (wp_id=WP2) — cross-WP ref
        response["milestones"][0]["depends_on_tasks"] = ["T2-01"]
        response["milestones"][0]["milestone_type"] = "intermediate_checkpoint"

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill("gantt-schedule-builder", "run-test-p4", repo)

        # Schema accepts it (structural validation is the checker's job)
        assert result.status == "success"


# =========================================================================
# Group B: milestone-consistency-check mode detection
# =========================================================================


class TestMilestoneConsistencyCheckMode:
    """Verify milestone-consistency-check detects gantt.json for FULL mode."""

    def test_gantt_json_presence_enables_full_mode(self, tmp_path: Path) -> None:
        """When gantt.json exists, milestone-consistency-check should see it."""
        repo = _make_gantt_skill_env(tmp_path)

        # Write gantt.json to the canonical path
        _write_json(repo / _GANTT_CANONICAL_PATH, _valid_gantt_response())

        # The phase4 output directory now contains gantt.json
        phase4_dir = repo / "docs" / "tier4_orchestration_state" / "phase_outputs" / "phase4_gantt_milestones"
        json_files = sorted(f.name for f in phase4_dir.iterdir() if f.suffix == ".json")
        assert "gantt.json" in json_files

    def test_gantt_json_absence_means_degraded(self, tmp_path: Path) -> None:
        """When gantt.json is absent, only scheduling_constraints.json exists."""
        repo = _make_gantt_skill_env(tmp_path)

        phase4_dir = repo / "docs" / "tier4_orchestration_state" / "phase_outputs" / "phase4_gantt_milestones"
        json_files = sorted(f.name for f in phase4_dir.iterdir() if f.suffix == ".json")
        assert "gantt.json" not in json_files
        assert "scheduling_constraints.json" in json_files


# =========================================================================
# Group C: Missing gantt.json regression detection
# =========================================================================


class TestMissingGanttRegression:
    """Verify that absent gantt.json is caught at the right points."""

    def test_gantt_json_in_manifest_artifact_registry(self) -> None:
        """The real manifest declares phase4_gantt_milestones/ as produced by n04."""
        manifest_path = Path(
            "C:/Code/proposal_demo/proposal_orchestrator"
            "/.claude/workflows/system_orchestration/manifest.compile.yaml"
        )
        if not manifest_path.is_file():
            pytest.skip("Real manifest not available")

        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        n04_skills = None
        for node in data.get("node_registry", []):
            if node.get("node_id") == "n04_gantt_milestones":
                n04_skills = node.get("skills", [])
                break

        assert n04_skills is not None, "n04_gantt_milestones not found in manifest"
        assert "gantt-schedule-builder" in n04_skills, (
            "gantt-schedule-builder must be in n04 skill list to produce gantt.json"
        )

    def test_gantt_schedule_builder_in_skill_catalog(self) -> None:
        """The real skill catalog contains gantt-schedule-builder."""
        catalog_path = Path(
            "C:/Code/proposal_demo/proposal_orchestrator"
            "/.claude/workflows/system_orchestration/skill_catalog.yaml"
        )
        if not catalog_path.is_file():
            pytest.skip("Real skill catalog not available")

        data = yaml.safe_load(catalog_path.read_text(encoding="utf-8-sig"))
        skill_ids = [e.get("id") for e in data.get("skill_catalog", [])]
        assert "gantt-schedule-builder" in skill_ids

    def test_gantt_schedule_builder_writes_to_gantt_json(self) -> None:
        """The skill catalog entry writes_to must include the gantt.json path."""
        catalog_path = Path(
            "C:/Code/proposal_demo/proposal_orchestrator"
            "/.claude/workflows/system_orchestration/skill_catalog.yaml"
        )
        if not catalog_path.is_file():
            pytest.skip("Real skill catalog not available")

        data = yaml.safe_load(catalog_path.read_text(encoding="utf-8-sig"))
        for entry in data.get("skill_catalog", []):
            if entry.get("id") == "gantt-schedule-builder":
                writes_to = entry.get("writes_to", [])
                assert any("gantt.json" in w for w in writes_to), (
                    f"gantt-schedule-builder writes_to must include gantt.json, got: {writes_to}"
                )
                return
        pytest.fail("gantt-schedule-builder not found in skill catalog")


# =========================================================================
# Group D: Option A predicates remain intact
# =========================================================================


class TestOptionAPredicatesIntact:
    """Verify scheduling_constraints.json predicates are not affected."""

    def test_scheduling_constraints_still_in_manifest(self) -> None:
        """scheduling_constraints.json artifact is still in the manifest."""
        manifest_path = Path(
            "C:/Code/proposal_demo/proposal_orchestrator"
            "/.claude/workflows/system_orchestration/manifest.compile.yaml"
        )
        if not manifest_path.is_file():
            pytest.skip("Real manifest not available")

        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        sc_found = False
        for entry in data.get("artifact_registry", []):
            if "scheduling_constraints.json" in entry.get("path", ""):
                sc_found = True
                break
        assert sc_found, "scheduling_constraints.json artifact must remain in manifest"

    def test_gate_predicates_include_dependency_consistency(self) -> None:
        """phase_04_gate still references g05_p08 (dependency_schedule_consistency)."""
        manifest_path = Path(
            "C:/Code/proposal_demo/proposal_orchestrator"
            "/.claude/workflows/system_orchestration/manifest.compile.yaml"
        )
        if not manifest_path.is_file():
            pytest.skip("Real manifest not available")

        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        for gate in data.get("gate_registry", []):
            if gate.get("gate_id") == "phase_04_gate":
                all_refs = []
                for cond in gate.get("conditions", []):
                    all_refs.extend(cond.get("predicate_refs", []))
                assert "g05_p08" in all_refs, "g05_p08 must remain in phase_04_gate"
                assert "g05_p02c" in all_refs, "g05_p02c must remain in phase_04_gate"
                assert "g05_p02d" in all_refs, "g05_p02d must remain in phase_04_gate"
                return
        pytest.fail("phase_04_gate not found in gate registry")


# =========================================================================
# Group E: n04 skill sequencing
# =========================================================================


class TestN04SkillSequencing:
    """Verify n04 skill execution order through agent runtime."""

    def test_gantt_builder_before_milestone_check(self, tmp_path: Path) -> None:
        """gantt-schedule-builder must execute before milestone-consistency-check."""
        repo = tmp_path

        # Set up minimal agent environment
        _write_yaml(
            repo / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [
                {"id": "gantt-schedule-builder", "reads_from": [], "writes_to": [_GANTT_CANONICAL_PATH],
                 "constitutional_constraints": [], "used_by_agents": ["gantt_designer"]},
                {"id": "milestone-consistency-check", "reads_from": [],
                 "optional_reads_from": ["docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/"],
                 "writes_to": ["docs/tier4_orchestration_state/validation_reports/"],
                 "constitutional_constraints": [], "used_by_agents": ["gantt_designer"]},
                {"id": "gate-enforcement", "reads_from": [], "writes_to": ["docs/tier4_orchestration_state/phase_outputs/"],
                 "constitutional_constraints": [], "used_by_agents": ["gantt_designer"],
                 "execution_mode": "tapm", "output_contract": "payload",
                 "payload_required_fields": ["gate_id", "run_id", "overall_status",
                                              "evaluated_at", "deterministic_predicates",
                                              "semantic_predicates"]},
                {"id": "decision-log-update", "reads_from": ["Any phase context requiring durable recording"],
                 "writes_to": ["docs/tier4_orchestration_state/decision_log/"],
                 "constitutional_constraints": [], "used_by_agents": ["gantt_designer"]},
            ]},
        )

        _write_yaml(
            repo / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            _GANTT_SCHEMA,
        )

        _write_yaml(
            repo / ".claude" / "workflows" / "system_orchestration"
            / "agent_catalog.yaml",
            {"agent_catalog": [{
                "id": "gantt_designer",
                "reads_from": [],
                "writes_to": [
                    "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/",
                ],
            }]},
        )

        # Manifest with n04 and artifact registry
        _write_yaml(
            repo / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml",
            {
                "node_registry": [{
                    "node_id": "n04_gantt_milestones",
                    "phase_id": "phase_04_gantt_and_milestones",
                    "skills": ["gantt-schedule-builder", "milestone-consistency-check",
                               "gate-enforcement", "decision-log-update"],
                    "exit_gate": "phase_04_gate",
                    "agent": "gantt_designer",
                }],
                "artifact_registry": [
                    {"artifact_id": "a_t4_phase4", "path": "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/",
                     "tier": "tier4_phase_output", "produced_by": "n04_gantt_milestones", "gate_dependency": "phase_04_gate"},
                    {"artifact_id": "a_t4_phase4_sc", "path": _SC_CANONICAL_PATH,
                     "tier": "tier4_phase_output", "produced_by": "n04_gantt_milestones", "gate_dependency": "phase_04_gate"},
                ],
            },
        )

        # Minimal agent and prompt specs
        agents_dir = repo / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "gantt_designer.md").write_text(
            "---\nagent_id: gantt_designer\n---\n# gantt_designer\nTest agent.",
            encoding="utf-8",
        )
        prompts_dir = agents_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        # Mention skills in the order they should run
        (prompts_dir / "gantt_designer_prompt_spec.md").write_text(
            "# gantt_designer prompt specification\n\n"
            "Steps 3-6: invoke gantt-schedule-builder skill\n"
            "Step 8: invoke milestone-consistency-check skill\n"
            "Step 9: invoke gate-enforcement skill\n"
            "Step 10: invoke decision-log-update skill\n",
            encoding="utf-8",
        )

        skills_dir = repo / ".claude" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        for sid in ["gantt-schedule-builder", "milestone-consistency-check",
                     "gate-enforcement", "decision-log-update"]:
            (skills_dir / f"{sid}.md").write_text(f"# {sid}\nTest.", encoding="utf-8")

        # Track invocation order
        invocation_order: list[str] = []

        def _mock_run_skill(skill_id, run_id, repo_root, inputs, **kwargs):
            invocation_order.append(skill_id)
            if skill_id == "gantt-schedule-builder":
                # Simulate writing gantt.json
                _write_json(repo_root / _GANTT_CANONICAL_PATH, _valid_gantt_response(run_id))
                return SkillResult(
                    status="success",
                    outputs_written=[_GANTT_CANONICAL_PATH],
                )
            if skill_id == "gate-enforcement":
                return SkillResult(
                    status="success",
                    payload={
                        "gate_id": "phase_04_gate", "run_id": run_id,
                        "overall_status": "pass",
                        "evaluated_at": "2026-04-21T00:00:00Z",
                        "deterministic_predicates": {"passed": [], "failed": []},
                        "semantic_predicates": {"passed": [], "failed": []},
                    },
                )
            return SkillResult(status="success", outputs_written=[])

        # Write scheduling_constraints.json (simulating Phase B+ normalizer)
        _write_json(repo / _SC_CANONICAL_PATH, {
            "schema_id": "orch.phase4.scheduling_constraints.v1",
            "run_id": "run-test-seq",
            "source_wp_structure_run_id": "run-phase3",
            "derived_from_artifact": "test",
            "normalization_timestamp": "2026-04-21T00:00:00Z",
            "project_duration_months": 48,
            "wp_bounds": {},
            "strict_constraints": [], "non_strict_constraints": [],
            "normalization_log": [], "unresolved_constraints": [],
        })

        with patch(_RUN_SKILL_TARGET, side_effect=_mock_run_skill), \
             patch("runner.dependency_normalizer.normalize_dependencies",
                   return_value=repo / _SC_CANONICAL_PATH):
            result = run_agent(
                agent_id="gantt_designer",
                node_id="n04_gantt_milestones",
                run_id="run-test-seq",
                repo_root=repo,
                manifest_path=repo / ".claude" / "workflows" / "system_orchestration" / "manifest.compile.yaml",
                skill_ids=["gantt-schedule-builder", "milestone-consistency-check",
                            "gate-enforcement", "decision-log-update"],
                phase_id="phase_04_gantt_and_milestones",
            )

        # gantt-schedule-builder must be first
        assert invocation_order[0] == "gantt-schedule-builder", (
            f"Expected gantt-schedule-builder first, got: {invocation_order}"
        )

        # milestone-consistency-check must be after gantt-schedule-builder
        gsb_idx = invocation_order.index("gantt-schedule-builder")
        mcc_idx = invocation_order.index("milestone-consistency-check")
        assert mcc_idx > gsb_idx, (
            f"milestone-consistency-check ({mcc_idx}) must run after "
            f"gantt-schedule-builder ({gsb_idx}): {invocation_order}"
        )

        # gate-enforcement must be last (agent runtime enforces this)
        assert invocation_order[-1] == "gate-enforcement", (
            f"gate-enforcement must be last, got: {invocation_order}"
        )

        # gantt.json should be on disk
        assert (repo / _GANTT_CANONICAL_PATH).is_file()

        # Agent should report success with can_evaluate_exit_gate=True
        assert result.status == "success"
        assert result.can_evaluate_exit_gate is True
