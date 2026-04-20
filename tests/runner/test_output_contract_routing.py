"""
Tests for output_contract-based validation routing in skill_runtime.py.

Covers the fix for incorrect multi-artifact validation treatment of
gate-enforcement.  The root cause was that gate-enforcement's broad
``writes_to`` paths resolved to all 8+ canonical phase output schemas,
triggering the multi-artifact validation branch, which expected
unrelated fields (e.g. ``resolved_instrument_type`` for Phase 1,
``work_packages`` for Phase 3).

The fix introduces an explicit ``output_contract`` field in the skill
catalog with three modes:

  - ``"single_artifact"`` (default): single canonical artifact write
  - ``"multi_artifact"``: multiple canonical artifact writes
  - ``"payload"``: in-memory payload returned in SkillResult.payload

These tests prove:
  A. gate-enforcement uses payload validation (not multi-artifact)
  B. Multi-artifact validation does not trigger from inputs alone
  C. True multi-artifact skills still use multi-artifact validation
  D. Missing required gate-enforcement fields still fail
  E. No regression in Phase 3 path
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.runtime_models import SkillResult
from runner.skill_runtime import run_skill


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"


def _claude_returns(response_dict: dict):
    """Patch invoke_claude_text to return a JSON-serialised dict."""
    return patch(_TRANSPORT_TARGET, return_value=json.dumps(response_dict))


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def _write_skill_spec(repo_root: Path, skill_id: str, content: str = "") -> None:
    spec_path = repo_root / ".claude" / "skills" / f"{skill_id}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        content or f"# {skill_id}\nTest skill specification.",
        encoding="utf-8",
    )


def _clear_caches() -> None:
    """Clear skill_runtime caches to prevent test pollution."""
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_gate_enforcement_env(tmp_path: Path) -> Path:
    """Create a synthetic environment mimicking gate-enforcement's real config.

    gate-enforcement writes_to includes broad directories that resolve to
    many canonical schemas.  With the fix, output_contract: "payload"
    prevents the multi-artifact validation path from activating.
    """
    repo_root = tmp_path

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": [{
            "id": "gate-enforcement",
            "execution_mode": "tapm",
            "output_contract": "payload",
            "payload_required_fields": [
                "gate_id",
                "run_id",
                "overall_status",
                "evaluated_at",
                "deterministic_predicates",
                "semantic_predicates",
            ],
            "reads_from": [
                "docs/tier4_orchestration_state/phase_outputs/",
                "docs/tier3_project_instantiation/",
            ],
            "writes_to": [
                "docs/tier4_orchestration_state/phase_outputs/",
                "docs/tier4_orchestration_state/decision_log/",
            ],
            "constitutional_constraints": [],
        }]},
    )

    # Artifact schema with MANY canonical schemas under phase_outputs/ —
    # this is what triggered the original bug.
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml",
        {
            "tier4_phase_output_schemas": {
                "call_analysis_summary": {
                    "canonical_path": "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
                    "schema_id_value": "orch.phase1.call_analysis_summary.v1",
                    "fields": {
                        "schema_id": {"required": True},
                        "run_id": {"required": True},
                        "resolved_instrument_type": {"required": True},
                        "evaluation_matrix": {"required": True},
                        "compliance_checklist": {"required": True},
                    },
                },
                "concept_refinement_summary": {
                    "canonical_path": "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
                    "schema_id_value": "orch.phase2.concept_refinement_summary.v1",
                    "fields": {
                        "schema_id": {"required": True},
                        "run_id": {"required": True},
                        "topic_mapping_rationale": {"required": True},
                    },
                },
                "wp_structure": {
                    "canonical_path": "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
                    "schema_id_value": "orch.phase3.wp_structure.v1",
                    "fields": {
                        "schema_id": {"required": True},
                        "run_id": {"required": True},
                        "work_packages": {"required": True},
                    },
                },
                "gantt": {
                    "canonical_path": "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json",
                    "schema_id_value": "orch.phase4.gantt.v1",
                    "fields": {
                        "schema_id": {"required": True},
                        "run_id": {"required": True},
                        "tasks": {"required": True},
                    },
                },
            },
        },
    )

    _write_skill_spec(repo_root, "gate-enforcement")

    # Create input directories (required to exist for TAPM prompt assembly
    # to succeed, even though TAPM mode skips input validation)
    (repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs").mkdir(
        parents=True, exist_ok=True
    )
    (repo_root / "docs" / "tier4_orchestration_state" / "decision_log").mkdir(
        parents=True, exist_ok=True
    )
    (repo_root / "docs" / "tier3_project_instantiation").mkdir(
        parents=True, exist_ok=True
    )

    return repo_root


@pytest.fixture()
def gate_env(tmp_path: Path) -> Path:
    _clear_caches()
    return _make_gate_enforcement_env(tmp_path)


# ---------------------------------------------------------------------------
# Test A: gate-enforcement uses payload validation (single-result)
# ---------------------------------------------------------------------------


class TestGateEnforcementPayloadValidation:
    """gate-enforcement is validated against its real gate-evaluation result
    contract, not treated as a multi-artifact producer."""

    def test_valid_gate_pass_response_accepted(self, gate_env: Path) -> None:
        """A representative gate-enforcement response with the normal
        gate-evaluation object is accepted and not treated as multi-artifact."""
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-001",
            "overall_status": "pass",
            "hard_block": False,
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {
                "passed": ["artifact_present", "schema_id_match"],
                "failed": [],
            },
            "semantic_predicates": {
                "passed": ["all_partners_in_tier3"],
                "failed": [],
            },
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "success"
        assert result.payload is not None
        assert result.payload["gate_id"] == "phase_03_gate"
        assert result.payload["overall_status"] == "pass"

    def test_valid_gate_fail_response_accepted(self, gate_env: Path) -> None:
        """Gate failure is a valid and correct output — SkillResult.status
        is still "success" because the skill executed correctly."""
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-001",
            "overall_status": "fail",
            "hard_block": False,
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {
                "passed": ["artifact_present"],
                "failed": [
                    {"predicate_id": "run_id_match", "fail_message": "mismatch"},
                ],
            },
            "semantic_predicates": {
                "passed": [],
                "failed": [],
            },
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "success"
        assert result.payload is not None
        assert result.payload["overall_status"] == "fail"

    def test_decision_log_entry_extracted_and_written(self, gate_env: Path) -> None:
        """When the response contains a decision_log_entry, it is written
        to the decision log directory."""
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-001",
            "overall_status": "fail",
            "hard_block": False,
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {
                "passed": [],
                "failed": [{"predicate_id": "p1", "fail_message": "missing"}],
            },
            "semantic_predicates": {"passed": [], "failed": []},
            "decision_log_entry": {
                "decision_id": "gate_failure_phase_03_gate_2026",
                "decision_type": "gate_failure",
                "gate_id": "phase_03_gate",
                "failure_reason": "predicate p1 failed",
            },
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "success"
        log_path = (
            gate_env / "docs" / "tier4_orchestration_state" / "decision_log"
            / "gate_failure_phase_03_gate_2026.json"
        )
        assert log_path.exists()
        log_data = json.loads(log_path.read_text(encoding="utf-8"))
        assert log_data["decision_type"] == "gate_failure"
        assert "gate_failure_phase_03_gate_2026" in (
            result.outputs_written[0] if result.outputs_written else ""
        )

    def test_no_canonical_artifact_written_to_phase_outputs(
        self, gate_env: Path
    ) -> None:
        """Payload-mode skills do NOT write canonical artifacts to
        phase_outputs/ directories."""
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-001",
            "overall_status": "pass",
            "hard_block": False,
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {"passed": ["p1"], "failed": []},
            "semantic_predicates": {"passed": [], "failed": []},
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "success"
        # No file should be written to any phase output directory
        phase_out = gate_env / "docs" / "tier4_orchestration_state" / "phase_outputs"
        json_files = list(phase_out.rglob("*.json"))
        assert len(json_files) == 0, (
            f"Expected no phase output files, found: {json_files}"
        )

    def test_response_not_validated_against_unrelated_schemas(
        self, gate_env: Path
    ) -> None:
        """The response is NOT checked for fields from unrelated schemas
        like resolved_instrument_type, work_packages, tasks, etc.

        This is the exact bug that was fixed — gate-enforcement should
        never be validated against Phase 1/2/3/4 artifact schemas."""
        # Response has valid gate-evaluation fields but does NOT contain
        # any Phase-specific artifact fields.
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-001",
            "overall_status": "pass",
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {"passed": [], "failed": []},
            "semantic_predicates": {"passed": [], "failed": []},
            # None of these are present:
            # resolved_instrument_type, evaluation_matrix,
            # topic_mapping_rationale, work_packages, tasks
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        # Must succeed — not fail with "missing resolved_instrument_type"
        assert result.status == "success"
        assert result.payload is not None


# ---------------------------------------------------------------------------
# Test B: Multi-artifact validation does not trigger from inputs alone
# ---------------------------------------------------------------------------


class TestMultiArtifactNotTriggeredByInputs:
    """A skill with many reads_from paths but a single-result contract
    must NOT enter multi-artifact validation."""

    @pytest.fixture()
    def single_output_many_inputs_env(self, tmp_path: Path) -> Path:
        _clear_caches()
        repo_root = tmp_path

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [{
                "id": "many-input-skill",
                # No output_contract → defaults to "single_artifact"
                "reads_from": [
                    "docs/tier4/phase1/",
                    "docs/tier4/phase2/",
                    "docs/tier4/phase3/",
                    "docs/tier3/consortium/",
                ],
                "writes_to": ["docs/tier4/phase6/"],
                "constitutional_constraints": [],
            }]},
        )

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            {
                "tier4_phase_output_schemas": {
                    "impl_arch": {
                        "canonical_path": "docs/tier4/phase6/implementation_architecture.json",
                        "schema_id_value": "orch.phase6.impl_arch.v1",
                        "fields": {
                            "schema_id": {"required": True},
                            "run_id": {"required": True},
                            "risk_register": {"required": True},
                        },
                    },
                },
            },
        )

        _write_skill_spec(repo_root, "many-input-skill")

        # Create input directories with content
        for d in ["docs/tier4/phase1", "docs/tier4/phase2",
                   "docs/tier4/phase3", "docs/tier3/consortium"]:
            (repo_root / d).mkdir(parents=True, exist_ok=True)
            (repo_root / d / "dummy.json").write_text('{"ok": true}')

        (repo_root / "docs" / "tier4" / "phase6").mkdir(parents=True, exist_ok=True)

        return repo_root

    def test_single_artifact_with_many_inputs(
        self, single_output_many_inputs_env: Path
    ) -> None:
        """A skill reading from 4 directories but producing one artifact
        uses single-artifact validation, not multi-artifact."""
        response = {
            "schema_id": "orch.phase6.impl_arch.v1",
            "run_id": "run-001",
            "risk_register": [{"id": "R1", "description": "risk"}],
        }
        with _claude_returns(response):
            result = run_skill(
                "many-input-skill", "run-001", single_output_many_inputs_env
            )

        assert result.status == "success"
        assert len(result.outputs_written) == 1
        assert "implementation_architecture.json" in result.outputs_written[0]


# ---------------------------------------------------------------------------
# Test C: True multi-artifact skill still uses multi-artifact validation
# ---------------------------------------------------------------------------


class TestTrueMultiArtifactStillWorks:
    """When output_contract is explicitly "multi_artifact", the
    multi-artifact validation path is used and works correctly."""

    @pytest.fixture()
    def multi_artifact_env(self, tmp_path: Path) -> Path:
        _clear_caches()
        repo_root = tmp_path

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [{
                "id": "extraction-skill",
                "output_contract": "multi_artifact",
                "reads_from": ["docs/input/data.json"],
                "writes_to": ["docs/extracted/"],
                "constitutional_constraints": [],
            }]},
        )

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            {
                "tier2b_extracted_schemas": {
                    "constraints": {
                        "canonical_path": "docs/extracted/constraints.json",
                        "fields": {"constraints": {"required": True}},
                    },
                    "outcomes": {
                        "canonical_path": "docs/extracted/outcomes.json",
                        "fields": {"outcomes": {"required": True}},
                    },
                },
            },
        )

        _write_skill_spec(repo_root, "extraction-skill")

        (repo_root / "docs" / "input").mkdir(parents=True, exist_ok=True)
        (repo_root / "docs" / "input" / "data.json").write_text('{"x": 1}')
        (repo_root / "docs" / "extracted").mkdir(parents=True, exist_ok=True)

        return repo_root

    def test_multi_artifact_explicit_declaration_works(
        self, multi_artifact_env: Path
    ) -> None:
        """With output_contract: "multi_artifact", both sub-artifacts
        are validated and written."""
        response = {
            "constraints": [{"id": "c1", "text": "constraint"}],
            "outcomes": [{"id": "o1", "text": "outcome"}],
        }
        with _claude_returns(response):
            result = run_skill(
                "extraction-skill", "run-001", multi_artifact_env
            )

        assert result.status == "success"
        assert len(result.outputs_written) == 2

    def test_missing_sub_artifact_fails(
        self, multi_artifact_env: Path
    ) -> None:
        """Multi-artifact validation still fails when a sub-artifact is missing."""
        response = {
            "constraints": [{"id": "c1"}],
            # Missing: outcomes
        }
        with _claude_returns(response):
            result = run_skill(
                "extraction-skill", "run-001", multi_artifact_env
            )

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "outcomes" in result.failure_reason


# ---------------------------------------------------------------------------
# Test D: Missing required gate-enforcement fields still fail
# ---------------------------------------------------------------------------


class TestGateEnforcementFailClosed:
    """Payload validation fails closed when required fields are missing."""

    def test_missing_gate_id_fails(self, gate_env: Path) -> None:
        response = {
            # Missing: gate_id
            "run_id": "run-001",
            "overall_status": "pass",
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {"passed": [], "failed": []},
            "semantic_predicates": {"passed": [], "failed": []},
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "gate_id" in result.failure_reason

    def test_missing_overall_status_fails(self, gate_env: Path) -> None:
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-001",
            # Missing: overall_status
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {"passed": [], "failed": []},
            "semantic_predicates": {"passed": [], "failed": []},
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "overall_status" in result.failure_reason

    def test_missing_deterministic_predicates_fails(self, gate_env: Path) -> None:
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-001",
            "overall_status": "pass",
            "evaluated_at": "2026-04-20T12:00:00Z",
            # Missing: deterministic_predicates
            "semantic_predicates": {"passed": [], "failed": []},
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "failure"
        assert "deterministic_predicates" in result.failure_reason

    def test_run_id_mismatch_fails(self, gate_env: Path) -> None:
        response = {
            "gate_id": "phase_03_gate",
            "run_id": "wrong-run-id",
            "overall_status": "pass",
            "evaluated_at": "2026-04-20T12:00:00Z",
            "deterministic_predicates": {"passed": [], "failed": []},
            "semantic_predicates": {"passed": [], "failed": []},
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "run_id mismatch" in result.failure_reason

    def test_malformed_json_still_fails(self, gate_env: Path) -> None:
        """Non-JSON responses still produce INCOMPLETE_OUTPUT failures."""
        with patch(_TRANSPORT_TARGET, return_value="This is not JSON"):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"

    def test_multiple_missing_fields_all_reported(self, gate_env: Path) -> None:
        """When multiple required fields are missing, all are reported."""
        response = {
            # Only run_id present — gate_id, overall_status, evaluated_at,
            # deterministic_predicates, semantic_predicates all missing
            "run_id": "run-001",
        }
        with _claude_returns(response):
            result = run_skill("gate-enforcement", "run-001", gate_env)

        assert result.status == "failure"
        assert "gate_id" in result.failure_reason
        assert "overall_status" in result.failure_reason
        assert "evaluated_at" in result.failure_reason
        assert "deterministic_predicates" in result.failure_reason
        assert "semantic_predicates" in result.failure_reason


# ---------------------------------------------------------------------------
# Test E: No regression in Phase 3 path
# ---------------------------------------------------------------------------


class TestPhase3NoRegression:
    """Integration-style test confirming gate-enforcement no longer fails
    because of unrelated artifact-field expectations during Phase 3."""

    @pytest.fixture()
    def phase3_env(self, tmp_path: Path) -> Path:
        """Mimics the real Phase 3 environment with gate-enforcement as
        the last skill in n03_wp_design.

        The artifact schema includes multiple phase output schemas under
        the phase_outputs/ directory — the exact condition that triggered
        the original bug.
        """
        _clear_caches()
        repo_root = tmp_path

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [
                {
                    "id": "work-package-normalization",
                    "execution_mode": "tapm",
                    "reads_from": [
                        "docs/tier3/architecture_inputs/workpackage_seed.json",
                    ],
                    "writes_to": [
                        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/",
                    ],
                    "constitutional_constraints": [],
                },
                {
                    "id": "gate-enforcement",
                    "execution_mode": "tapm",
                    "output_contract": "payload",
                    "payload_required_fields": [
                        "gate_id", "run_id", "overall_status",
                        "evaluated_at", "deterministic_predicates",
                        "semantic_predicates",
                    ],
                    "reads_from": [
                        "docs/tier4_orchestration_state/phase_outputs/",
                        "docs/tier3/",
                    ],
                    "writes_to": [
                        "docs/tier4_orchestration_state/phase_outputs/",
                        "docs/tier4_orchestration_state/decision_log/",
                    ],
                    "constitutional_constraints": [],
                },
            ]},
        )

        # Schema includes all 4 phase output schemas — the same
        # condition that triggered the original multi-artifact bug.
        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            {
                "tier4_phase_output_schemas": {
                    "call_analysis_summary": {
                        "canonical_path": "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
                        "schema_id_value": "orch.phase1.call_analysis_summary.v1",
                        "fields": {
                            "schema_id": {"required": True},
                            "run_id": {"required": True},
                            "resolved_instrument_type": {"required": True},
                        },
                    },
                    "wp_structure": {
                        "canonical_path": "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
                        "schema_id_value": "orch.phase3.wp_structure.v1",
                        "fields": {
                            "schema_id": {"required": True},
                            "run_id": {"required": True},
                            "work_packages": {"required": True},
                        },
                    },
                    "gantt": {
                        "canonical_path": "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json",
                        "schema_id_value": "orch.phase4.gantt.v1",
                        "fields": {
                            "schema_id": {"required": True},
                            "run_id": {"required": True},
                            "tasks": {"required": True},
                        },
                    },
                },
            },
        )

        _write_skill_spec(repo_root, "work-package-normalization")
        _write_skill_spec(repo_root, "gate-enforcement")

        # Create directories
        for d in [
            "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design",
            "docs/tier4_orchestration_state/phase_outputs",
            "docs/tier4_orchestration_state/decision_log",
            "docs/tier3/architecture_inputs",
            "docs/tier3",
        ]:
            (repo_root / d).mkdir(parents=True, exist_ok=True)

        # Populate required inputs
        (repo_root / "docs" / "tier3" / "architecture_inputs"
         / "workpackage_seed.json").write_text(
            json.dumps({"work_packages": [{"id": "WP1", "title": "Test"}]}),
            encoding="utf-8",
        )

        return repo_root

    def test_gate_enforcement_succeeds_in_phase3_context(
        self, phase3_env: Path
    ) -> None:
        """gate-enforcement invoked in Phase 3 context succeeds with a
        standard gate-evaluation response — no multi-artifact validation
        errors about resolved_instrument_type or tasks."""
        gate_response = {
            "gate_id": "phase_03_gate",
            "run_id": "run-phase3",
            "overall_status": "fail",
            "hard_block": False,
            "evaluated_at": "2026-04-20T15:00:00Z",
            "deterministic_predicates": {
                "passed": [
                    "artifact_present",
                    "schema_id_match",
                    "work_packages_non_empty",
                ],
                "failed": [
                    {
                        "predicate_id": "run_id_match",
                        "fail_message": "artifact from prior run",
                    },
                ],
            },
            "semantic_predicates": {
                "passed": ["all_partners_in_tier3"],
                "failed": [],
            },
        }
        with _claude_returns(gate_response):
            result = run_skill(
                "gate-enforcement", "run-phase3", phase3_env
            )

        # The skill must succeed — NOT fail with "missing
        # resolved_instrument_type for call_analysis_summary.json"
        assert result.status == "success", (
            f"Expected success but got failure: {result.failure_reason}"
        )
        assert result.payload is not None
        assert result.payload["gate_id"] == "phase_03_gate"
        assert result.payload["overall_status"] == "fail"

    def test_wp_normalization_still_works_as_single_artifact(
        self, phase3_env: Path
    ) -> None:
        """work-package-normalization (no output_contract → default
        single_artifact) still writes to its canonical path correctly."""
        wp_response = {
            "schema_id": "orch.phase3.wp_structure.v1",
            "run_id": "run-phase3",
            "work_packages": [
                {
                    "id": "WP1",
                    "title": "Test WP",
                    "lead_partner": "P1",
                    "deliverables": [{"id": "D1.1"}],
                },
            ],
        }
        with _claude_returns(wp_response):
            result = run_skill(
                "work-package-normalization", "run-phase3", phase3_env
            )

        assert result.status == "success"
        assert len(result.outputs_written) == 1
        assert "wp_structure.json" in result.outputs_written[0]
        # Verify file was actually written
        written = phase3_env / result.outputs_written[0]
        assert written.exists()
        data = json.loads(written.read_text(encoding="utf-8"))
        assert data["work_packages"][0]["id"] == "WP1"


# ---------------------------------------------------------------------------
# Test: Default output_contract is single_artifact
# ---------------------------------------------------------------------------


class TestDefaultOutputContract:
    """Skills without an explicit output_contract field default to
    single_artifact behavior, even if writes_to resolves to many schemas."""

    @pytest.fixture()
    def default_contract_env(self, tmp_path: Path) -> Path:
        """A skill with broad writes_to but no output_contract.

        Previously this would have entered multi-artifact mode via the
        len(dir_artifacts) > 1 heuristic.  Now it uses single-artifact
        mode (the first resolved canonical artifact).
        """
        _clear_caches()
        repo_root = tmp_path

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [{
                "id": "broad-writer",
                # No output_contract field
                "reads_from": ["docs/input/data.json"],
                "writes_to": ["docs/outputs/"],
                "constitutional_constraints": [],
            }]},
        )

        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml",
            {
                "tier4_phase_output_schemas": {
                    "artifact_a": {
                        "canonical_path": "docs/outputs/a.json",
                        "schema_id_value": "orch.a.v1",
                        "fields": {
                            "schema_id": {"required": True},
                            "run_id": {"required": True},
                            "field_a": {"required": True},
                        },
                    },
                    "artifact_b": {
                        "canonical_path": "docs/outputs/b.json",
                        "schema_id_value": "orch.b.v1",
                        "fields": {
                            "schema_id": {"required": True},
                            "run_id": {"required": True},
                            "field_b": {"required": True},
                        },
                    },
                },
            },
        )

        _write_skill_spec(repo_root, "broad-writer")

        (repo_root / "docs" / "input").mkdir(parents=True, exist_ok=True)
        (repo_root / "docs" / "input" / "data.json").write_text('{"x": 1}')
        (repo_root / "docs" / "outputs").mkdir(parents=True, exist_ok=True)

        return repo_root

    def test_default_contract_uses_single_artifact(
        self, default_contract_env: Path
    ) -> None:
        """Without output_contract, the first resolved canonical artifact
        is used for single-artifact validation — NOT multi-artifact."""
        response = {
            "schema_id": "orch.a.v1",
            "run_id": "run-001",
            "field_a": "value_a",
        }
        with _claude_returns(response):
            result = run_skill(
                "broad-writer", "run-001", default_contract_env
            )

        # Should succeed using single-artifact path with artifact_a schema
        assert result.status == "success"
        assert len(result.outputs_written) == 1
        assert "a.json" in result.outputs_written[0]
