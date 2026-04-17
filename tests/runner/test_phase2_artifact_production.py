"""
Tests for Phase 2 Tier 3 call-binding artifact production.

Verifies that concept-alignment-check produces substantive, non-empty:
  - docs/tier3_project_instantiation/call_binding/topic_mapping.json
  - docs/tier3_project_instantiation/call_binding/compliance_profile.json

alongside the existing concept_refinement_summary.json output.

Test groups:
  A. Multi-artifact write produces all three outputs
  B. Empty {} is rejected at schema validation level
  C. Missing required fields fail validation
  D. End-to-end run_agent for concept_refiner
  E. run_skill with TAPM writes Tier 3 artifacts
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.runtime_models import SkillResult
from runner.skill_runtime import (
    _extract_json_response,
    _validate_skill_output,
    run_skill,
)
from runner.agent_runtime import run_agent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"
_RUN_SKILL_TARGET = "runner.agent_runtime.run_skill"


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
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


# ---------------------------------------------------------------------------
# Canonical Claude response for multi-artifact concept-alignment-check
# ---------------------------------------------------------------------------

def _valid_claude_response(run_id: str = "run-test-001") -> dict:
    """Build a valid multi-artifact response for concept-alignment-check.

    Flat structure for concept_refinement_summary fields,
    nested structure for topic_mapping and compliance_profile.
    """
    return {
        # concept_refinement_summary fields (flat at top level)
        "schema_id": "orch.phase2.concept_refinement_summary.v1",
        "run_id": run_id,
        "topic_mapping_rationale": {
            "EO-01": {
                "topic_element_id": "EO-01",
                "mapping_to_concept": "Pillar 1 addresses autonomy",
                "tier2b_source_ref": "Section 2.1 of work_programme.json",
                "tier3_evidence_ref": "project_brief/concept_note.md line 5",
                "status": "Confirmed",
                "vocabulary_gaps": [],
            }
        },
        "scope_conflict_log": [],
        "strategic_differentiation": "Integrated co-design of three pillars",

        # topic_mapping (nested)
        "topic_mapping": {
            "mappings": [
                {
                    "topic_element_id": "EO-01",
                    "tier2b_source_ref": "Section 2.1 of work_programme.json",
                    "tier3_evidence_ref": "project_brief/concept_note.md line 5",
                    "mapping_description": "Pillar 1 addresses autonomy",
                }
            ]
        },

        # compliance_profile (nested)
        "compliance_profile": {
            "eligibility_confirmed": True,
            "ethics_review_required": False,
            "gender_plan_required": True,
            "open_science_requirements": [
                "Open access to publications required"
            ],
        },
    }


# ---------------------------------------------------------------------------
# Helpers — synthetic environment builders
# ---------------------------------------------------------------------------

def _make_phase2_skill_env(tmp_path: Path) -> Path:
    """Create a synthetic environment for concept-alignment-check tests.

    Returns repo_root with all necessary catalog/schema/spec files.
    """
    repo_root = tmp_path

    # Skill catalog
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": [{
            "id": "concept-alignment-check",
            "execution_mode": "tapm",
            "reads_from": [
                "docs/tier3_project_instantiation/project_brief/",
                "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json",
                "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
                "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json",
                "docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json",
            ],
            "writes_to": [
                "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/",
                "docs/tier4_orchestration_state/decision_log/",
                "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
            ],
            "constitutional_constraints": [],
            "used_by_agents": ["concept_refiner"],
        }]},
    )

    # Artifact schema specification — include schemas for all 3 output artifacts
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml",
        {
            "tier4_phase_output_schemas": {
                "concept_refinement_summary": {
                    "schema_id_value": "orch.phase2.concept_refinement_summary.v1",
                    "canonical_path": "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
                    "provenance_class": "run_produced",
                    "fields": {
                        "schema_id": {"type": "string", "required": True},
                        "run_id": {"type": "string", "required": True},
                        "topic_mapping_rationale": {
                            "type": "object", "required": True,
                        },
                        "scope_conflict_log": {
                            "type": "array", "required": True,
                        },
                        "strategic_differentiation": {
                            "type": "string", "required": True,
                        },
                    },
                },
            },
            "tier3_source_schemas": {
                "topic_mapping": {
                    "canonical_path": "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                    "provenance_class": "manually_placed",
                    "fields": {
                        "mappings": {
                            "type": "array", "required": True,
                        },
                    },
                },
                "compliance_profile": {
                    "canonical_path": "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                    "provenance_class": "manually_placed",
                    "fields": {
                        "eligibility_confirmed": {
                            "type": "boolean", "required": True,
                        },
                        "ethics_review_required": {
                            "type": "boolean", "required": True,
                        },
                        "gender_plan_required": {
                            "type": "boolean", "required": True,
                        },
                        "open_science_requirements": {
                            "type": "array", "required": True,
                        },
                    },
                },
            },
        },
    )

    # Skill spec file
    skill_dir = repo_root / ".claude" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "concept-alignment-check.md").write_text(
        "# concept-alignment-check\nTest spec for multi-artifact output.",
        encoding="utf-8",
    )

    return repo_root


# ---------------------------------------------------------------------------
# A. Multi-artifact write produces all three outputs
# ---------------------------------------------------------------------------


class TestMultiArtifactWrite:
    """Verify run_skill with multi-artifact writes_to produces all 3 files."""

    def test_three_artifacts_written(self, tmp_path: Path) -> None:
        """Claude returns valid multi-artifact response → all 3 files written."""
        repo_root = _make_phase2_skill_env(tmp_path)
        response = _valid_claude_response()

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-test-001", repo_root,
            )

        assert result.status == "success", result.failure_reason
        assert len(result.outputs_written) == 3

        # Check concept_refinement_summary.json
        crs_path = (
            repo_root
            / "docs/tier4_orchestration_state/phase_outputs"
            / "phase2_concept_refinement/concept_refinement_summary.json"
        )
        assert crs_path.exists()
        crs = json.loads(crs_path.read_text(encoding="utf-8"))
        assert crs["schema_id"] == "orch.phase2.concept_refinement_summary.v1"
        assert crs["run_id"] == "run-test-001"
        assert "topic_mapping_rationale" in crs

        # Check topic_mapping.json
        tm_path = (
            repo_root
            / "docs/tier3_project_instantiation/call_binding/topic_mapping.json"
        )
        assert tm_path.exists()
        tm = json.loads(tm_path.read_text(encoding="utf-8"))
        assert "mappings" in tm
        assert len(tm["mappings"]) > 0
        assert tm["mappings"][0]["topic_element_id"] == "EO-01"
        # Tier 3: no schema_id or run_id
        assert "schema_id" not in tm
        assert "run_id" not in tm

        # Check compliance_profile.json
        cp_path = (
            repo_root
            / "docs/tier3_project_instantiation/call_binding/compliance_profile.json"
        )
        assert cp_path.exists()
        cp = json.loads(cp_path.read_text(encoding="utf-8"))
        assert cp["eligibility_confirmed"] is True
        assert cp["ethics_review_required"] is False
        assert cp["gender_plan_required"] is True
        assert isinstance(cp["open_science_requirements"], list)
        # Tier 3: no schema_id or run_id
        assert "schema_id" not in cp
        assert "run_id" not in cp

    def test_outputs_written_paths_correct(self, tmp_path: Path) -> None:
        """Verify outputs_written contains correct repo-relative paths."""
        repo_root = _make_phase2_skill_env(tmp_path)
        response = _valid_claude_response()

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-test-001", repo_root,
            )

        assert result.status == "success"
        expected_paths = {
            "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
            "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
            "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
        }
        assert set(result.outputs_written) == expected_paths


# ---------------------------------------------------------------------------
# B. Empty {} is rejected at schema validation level
# ---------------------------------------------------------------------------


class TestEmptyArtifactRejection:
    """Verify that empty artifacts are caught by schema validation."""

    def test_missing_mappings_field_fails(self, tmp_path: Path) -> None:
        """Response missing 'mappings' key → MALFORMED_ARTIFACT."""
        repo_root = _make_phase2_skill_env(tmp_path)
        response = _valid_claude_response()
        # Remove the mappings from topic_mapping
        response["topic_mapping"] = {}

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-test-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_missing_compliance_fields_fails(self, tmp_path: Path) -> None:
        """Response missing compliance_profile fields → MALFORMED_ARTIFACT."""
        repo_root = _make_phase2_skill_env(tmp_path)
        response = _valid_claude_response()
        # Remove required fields from compliance_profile
        response["compliance_profile"] = {"eligibility_confirmed": True}

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-test-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_missing_summary_rationale_fails(self, tmp_path: Path) -> None:
        """Response missing topic_mapping_rationale → MALFORMED_ARTIFACT."""
        repo_root = _make_phase2_skill_env(tmp_path)
        response = _valid_claude_response()
        del response["topic_mapping_rationale"]

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-test-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"


# ---------------------------------------------------------------------------
# C. Missing required fields fail validation
# ---------------------------------------------------------------------------


class TestRequiredFieldValidation:
    """Verify _validate_skill_output catches missing required fields."""

    def test_validate_topic_mapping_requires_mappings(self) -> None:
        """topic_mapping without 'mappings' field fails validation."""
        errors = _validate_skill_output(
            response={},
            run_id="run-001",
            expected_schema_id=None,
            required_fields=["mappings"],
            require_run_id=False,
        )
        assert any("mappings" in e for e in errors)

    def test_validate_compliance_profile_requires_all_fields(self) -> None:
        """compliance_profile without required fields fails validation."""
        errors = _validate_skill_output(
            response={"eligibility_confirmed": True},
            run_id="run-001",
            expected_schema_id=None,
            required_fields=[
                "eligibility_confirmed",
                "ethics_review_required",
                "gender_plan_required",
                "open_science_requirements",
            ],
            require_run_id=False,
        )
        assert len(errors) == 3  # 3 missing fields
        missing = [e for e in errors if "Required field missing" in e]
        assert len(missing) == 3

    def test_validate_tier3_no_run_id_or_schema_id(self) -> None:
        """Tier 3 artifacts should NOT be validated for run_id/schema_id."""
        errors = _validate_skill_output(
            response={"mappings": [{"topic_element_id": "EO-01"}]},
            run_id="run-001",
            expected_schema_id=None,
            required_fields=["mappings"],
            require_run_id=False,
        )
        assert errors == []


# ---------------------------------------------------------------------------
# D. End-to-end run_agent for concept_refiner
# ---------------------------------------------------------------------------


def _make_phase2_agent_env(tmp_path: Path) -> dict:
    """Create environment for run_agent with concept_refiner."""
    repo_root = tmp_path

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "agent_catalog.yaml",
        {"agent_catalog": [{
            "id": "concept_refiner",
            "reads_from": [
                "docs/tier3_project_instantiation/project_brief/",
                "docs/tier2b_topic_and_call_sources/extracted/",
            ],
            "writes_to": [
                "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/",
            ],
        }]},
    )

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": [{
            "id": "concept-alignment-check",
            "execution_mode": "tapm",
            "reads_from": [
                "docs/tier3_project_instantiation/project_brief/",
                "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json",
                "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
            ],
            "writes_to": [
                "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/",
                "docs/tier4_orchestration_state/decision_log/",
                "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
            ],
            "constitutional_constraints": [],
            "used_by_agents": ["concept_refiner"],
        }]},
    )

    manifest_path = repo_root / "manifest_test.yaml"
    _write_yaml(manifest_path, {
        "name": "test",
        "version": "1.1",
        "node_registry": [{
            "node_id": "n02_concept_refinement",
            "agent": "concept_refiner",
            "skills": ["concept-alignment-check"],
            "phase_id": "phase_02_concept_refinement",
            "exit_gate": "phase_02_gate",
        }],
        "edge_registry": [],
        "artifact_registry": [{
            "path": "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
            "produced_by": "n02_concept_refinement",
            "tier": "tier4_phase_output",
        }],
    })

    agent_dir = repo_root / ".claude" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "concept_refiner.md").write_text(
        "# concept_refiner\nPhase 2.", encoding="utf-8",
    )
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "concept_refiner_prompt_spec.md").write_text(
        "# concept_refiner\nInvoke concept-alignment-check.\n",
        encoding="utf-8",
    )

    # Input artifacts
    brief_dir = (
        repo_root / "docs" / "tier3_project_instantiation" / "project_brief"
    )
    brief_dir.mkdir(parents=True, exist_ok=True)
    (brief_dir / "concept_note.md").write_text(
        "# Test Concept\nAI agent architecture.", encoding="utf-8"
    )
    _write_json(brief_dir / "project_summary.json", {"acronym": "TEST"})

    extracted_dir = (
        repo_root / "docs" / "tier2b_topic_and_call_sources" / "extracted"
    )
    _write_json(
        extracted_dir / "expected_outcomes.json",
        {"outcomes": [{"outcome_id": "EO-01", "description": "Improve AI"}]},
    )
    _write_json(
        extracted_dir / "scope_requirements.json",
        {"requirements": [{"requirement_id": "SR-01", "mandatory": True}]},
    )

    return {
        "agent_id": "concept_refiner",
        "node_id": "n02_concept_refinement",
        "run_id": "run-test-002",
        "repo_root": repo_root,
        "manifest_path": manifest_path,
        "skill_ids": ["concept-alignment-check"],
        "phase_id": "phase_02_concept_refinement",
    }


class TestPhase2AgentProducesArtifacts:
    """End-to-end: run_agent → concept-alignment-check → 3 artifacts."""

    def test_agent_invokes_skill_and_artifacts_written(
        self, tmp_path: Path
    ) -> None:
        """run_agent with concept_refiner produces Tier 3 artifacts."""
        kwargs = _make_phase2_agent_env(tmp_path)
        repo_root = kwargs["repo_root"]

        # Write gate-relevant artifact
        _write_json(
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase2_concept_refinement" / "concept_refinement_summary.json",
            {"placeholder": True},
        )

        def _mock_run_skill(skill_id, run_id, repo_root_arg, inputs=None, **kw):
            # Simulate concept-alignment-check writing all 3 artifacts
            _write_json(
                repo_root_arg / "docs" / "tier4_orchestration_state"
                / "phase_outputs" / "phase2_concept_refinement"
                / "concept_refinement_summary.json",
                {
                    "schema_id": "orch.phase2.concept_refinement_summary.v1",
                    "run_id": run_id,
                    "topic_mapping_rationale": {"EO-01": {}},
                    "scope_conflict_log": [],
                    "strategic_differentiation": "Test diff",
                },
            )
            _write_json(
                repo_root_arg / "docs" / "tier3_project_instantiation"
                / "call_binding" / "topic_mapping.json",
                {"mappings": [{"topic_element_id": "EO-01"}]},
            )
            _write_json(
                repo_root_arg / "docs" / "tier3_project_instantiation"
                / "call_binding" / "compliance_profile.json",
                {
                    "eligibility_confirmed": True,
                    "ethics_review_required": False,
                    "gender_plan_required": True,
                    "open_science_requirements": [],
                },
            )
            return SkillResult(
                status="success",
                outputs_written=[
                    "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
                    "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                    "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                ],
            )

        with patch(_RUN_SKILL_TARGET, side_effect=_mock_run_skill):
            result = run_agent(**kwargs)

        assert result.status == "success"

        # Verify artifacts on disk
        tm = json.loads(
            (repo_root / "docs" / "tier3_project_instantiation"
             / "call_binding" / "topic_mapping.json")
            .read_text(encoding="utf-8")
        )
        assert tm["mappings"]
        assert tm["mappings"][0]["topic_element_id"] == "EO-01"

        cp = json.loads(
            (repo_root / "docs" / "tier3_project_instantiation"
             / "call_binding" / "compliance_profile.json")
            .read_text(encoding="utf-8")
        )
        assert cp["eligibility_confirmed"] is True

    def test_skill_failure_propagated(self, tmp_path: Path) -> None:
        """When concept-alignment-check fails, agent reports failure."""
        kwargs = _make_phase2_agent_env(tmp_path)

        def _fail_skill(skill_id, *args, **kw):
            return SkillResult(
                status="failure",
                failure_reason="Empty response from Claude",
                failure_category="INCOMPLETE_OUTPUT",
            )

        with patch(_RUN_SKILL_TARGET, side_effect=_fail_skill):
            result = run_agent(**kwargs)

        assert result.status == "failure"
        assert result.failure_category == "SKILL_FAILURE"


# ---------------------------------------------------------------------------
# E. run_skill with TAPM writes Tier 3 artifacts
# ---------------------------------------------------------------------------


class TestTapmMultiArtifactProduction:
    """Verify TAPM mode correctly handles multi-artifact write for Tier 3."""

    def test_flat_response_also_works(self, tmp_path: Path) -> None:
        """When Claude returns all fields flat (no nesting), extraction works."""
        repo_root = _make_phase2_skill_env(tmp_path)
        # Flat response: all fields at top level
        response = {
            "schema_id": "orch.phase2.concept_refinement_summary.v1",
            "run_id": "run-flat-001",
            "topic_mapping_rationale": {"EO-01": {"status": "Confirmed"}},
            "scope_conflict_log": [],
            "strategic_differentiation": "Integrated approach",
            "mappings": [
                {
                    "topic_element_id": "EO-01",
                    "tier2b_source_ref": "Section 1",
                    "tier3_evidence_ref": "concept_note.md",
                    "mapping_description": "Maps to Pillar 1",
                }
            ],
            "eligibility_confirmed": True,
            "ethics_review_required": True,
            "gender_plan_required": True,
            "open_science_requirements": ["FAIR data"],
        }

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-flat-001", repo_root,
            )

        assert result.status == "success", result.failure_reason
        assert len(result.outputs_written) == 3

        # Verify topic_mapping
        tm = json.loads(
            (repo_root / "docs" / "tier3_project_instantiation"
             / "call_binding" / "topic_mapping.json")
            .read_text(encoding="utf-8")
        )
        assert tm["mappings"][0]["topic_element_id"] == "EO-01"

        # Verify compliance_profile
        cp = json.loads(
            (repo_root / "docs" / "tier3_project_instantiation"
             / "call_binding" / "compliance_profile.json")
            .read_text(encoding="utf-8")
        )
        assert cp["eligibility_confirmed"] is True
        assert cp["ethics_review_required"] is True

    def test_transport_failure_returns_skill_failure(
        self, tmp_path: Path
    ) -> None:
        """Transport failure → INCOMPLETE_OUTPUT, no artifacts written."""
        from runner.claude_transport import ClaudeTransportError

        repo_root = _make_phase2_skill_env(tmp_path)

        with patch(
            _TRANSPORT_TARGET,
            side_effect=ClaudeTransportError("CLI unavailable"),
        ):
            result = run_skill(
                "concept-alignment-check", "run-fail-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
        assert not result.outputs_written

    def test_non_json_response_fails(self, tmp_path: Path) -> None:
        """Non-JSON Claude response → INCOMPLETE_OUTPUT."""
        repo_root = _make_phase2_skill_env(tmp_path)

        with patch(_TRANSPORT_TARGET, return_value="I don't understand"):
            result = run_skill(
                "concept-alignment-check", "run-bad-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
