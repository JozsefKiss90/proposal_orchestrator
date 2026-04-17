"""
Tests for Phase 2 artifact production after skill-granularity refactor.

After the refactor, Phase 2 artifacts are produced by TWO skills:
  - concept-alignment-check: produces concept_refinement_summary.json (Tier 4)
  - concept-call-binding-derivation: produces topic_mapping.json + compliance_profile.json (Tier 3)

Test groups:
  A. Refactored concept-alignment-check: single-artifact summary output
  B. New concept-call-binding-derivation: dual Tier 3 artifact output
  C. Schema validation for Tier 3 required fields
  D. End-to-end run_agent with two-skill Phase 2 sequencing
  E. Fail-closed behavior for the binding skill
  F. Transport and parse failure handling
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
# Shared artifact schema specification (used by all env builders)
# ---------------------------------------------------------------------------

_ARTIFACT_SCHEMAS = {
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
}


# ---------------------------------------------------------------------------
# Canonical Claude responses
# ---------------------------------------------------------------------------

def _valid_summary_response(run_id: str = "run-test-001") -> dict:
    """Valid response for the refactored concept-alignment-check (summary only)."""
    return {
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
    }


def _valid_binding_response() -> dict:
    """Valid response for concept-call-binding-derivation (Tier 3 artifacts)."""
    return {
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

def _make_summary_skill_env(tmp_path: Path) -> Path:
    """Create environment for refactored concept-alignment-check tests.

    concept-alignment-check now writes ONLY the summary + decision log.
    """
    repo_root = tmp_path

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
            ],
            "constitutional_constraints": [],
            "used_by_agents": ["concept_refiner"],
        }]},
    )

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml",
        _ARTIFACT_SCHEMAS,
    )

    skill_dir = repo_root / ".claude" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "concept-alignment-check.md").write_text(
        "# concept-alignment-check\nTest spec for summary-only output.",
        encoding="utf-8",
    )

    return repo_root


def _make_binding_skill_env(tmp_path: Path) -> Path:
    """Create environment for concept-call-binding-derivation tests.

    Pre-populates concept_refinement_summary.json on disk (simulating
    that concept-alignment-check has already run).
    """
    repo_root = tmp_path

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": [{
            "id": "concept-call-binding-derivation",
            "execution_mode": "tapm",
            "reads_from": [
                "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
                "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json",
                "docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json",
                "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json",
                "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
            ],
            "writes_to": [
                "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
            ],
            "constitutional_constraints": [],
            "used_by_agents": ["concept_refiner"],
        }]},
    )

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml",
        _ARTIFACT_SCHEMAS,
    )

    skill_dir = repo_root / ".claude" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "concept-call-binding-derivation.md").write_text(
        "# concept-call-binding-derivation\nTest spec for Tier 3 derivation.",
        encoding="utf-8",
    )

    # Pre-populate concept_refinement_summary.json (upstream skill output)
    _write_json(
        repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
        / "phase2_concept_refinement" / "concept_refinement_summary.json",
        _valid_summary_response(),
    )

    # Tier 2B extracted files
    extracted_dir = (
        repo_root / "docs" / "tier2b_topic_and_call_sources" / "extracted"
    )
    _write_json(
        extracted_dir / "call_constraints.json",
        {"constraints": [{"constraint_id": "CC-01", "constraint_type": "scope"}]},
    )
    _write_json(
        extracted_dir / "eligibility_conditions.json",
        {"conditions": [{"condition_id": "EC-01", "condition_type": "consortium"}]},
    )
    _write_json(
        extracted_dir / "expected_outcomes.json",
        {"outcomes": [{"outcome_id": "EO-01", "description": "Improve AI"}]},
    )
    _write_json(
        extracted_dir / "scope_requirements.json",
        {"requirements": [{"requirement_id": "SR-01", "mandatory": True}]},
    )

    return repo_root


# ---------------------------------------------------------------------------
# A. Refactored concept-alignment-check: single-artifact summary output
# ---------------------------------------------------------------------------


class TestSummarySkillWrite:
    """Verify refactored concept-alignment-check writes ONLY the summary."""

    def test_summary_artifact_written(self, tmp_path: Path) -> None:
        """concept-alignment-check returns summary → 1 artifact written."""
        repo_root = _make_summary_skill_env(tmp_path)
        response = _valid_summary_response()

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-test-001", repo_root,
            )

        assert result.status == "success", result.failure_reason
        assert len(result.outputs_written) == 1

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

    def test_summary_output_path_correct(self, tmp_path: Path) -> None:
        """outputs_written contains only the summary path."""
        repo_root = _make_summary_skill_env(tmp_path)
        response = _valid_summary_response()

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-test-001", repo_root,
            )

        assert result.status == "success"
        expected = {
            "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
        }
        assert set(result.outputs_written) == expected

    def test_no_tier3_artifacts_from_summary_skill(self, tmp_path: Path) -> None:
        """concept-alignment-check must NOT write topic_mapping or compliance_profile."""
        repo_root = _make_summary_skill_env(tmp_path)
        response = _valid_summary_response()

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            run_skill("concept-alignment-check", "run-test-001", repo_root)

        tm_path = (
            repo_root
            / "docs/tier3_project_instantiation/call_binding/topic_mapping.json"
        )
        cp_path = (
            repo_root
            / "docs/tier3_project_instantiation/call_binding/compliance_profile.json"
        )
        assert not tm_path.exists(), "concept-alignment-check should not write topic_mapping.json"
        assert not cp_path.exists(), "concept-alignment-check should not write compliance_profile.json"

    def test_missing_rationale_fails(self, tmp_path: Path) -> None:
        """Summary without topic_mapping_rationale → MALFORMED_ARTIFACT."""
        repo_root = _make_summary_skill_env(tmp_path)
        response = _valid_summary_response()
        del response["topic_mapping_rationale"]

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-alignment-check", "run-test-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"


# ---------------------------------------------------------------------------
# B. New concept-call-binding-derivation: dual Tier 3 artifact output
# ---------------------------------------------------------------------------


class TestCallBindingSkillWrite:
    """Verify concept-call-binding-derivation writes both Tier 3 artifacts."""

    def test_both_tier3_artifacts_written(self, tmp_path: Path) -> None:
        """Binding skill produces topic_mapping.json and compliance_profile.json."""
        repo_root = _make_binding_skill_env(tmp_path)
        response = _valid_binding_response()

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-call-binding-derivation", "run-test-001", repo_root,
            )

        assert result.status == "success", result.failure_reason
        assert len(result.outputs_written) == 2

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
        assert "schema_id" not in cp
        assert "run_id" not in cp

    def test_binding_output_paths_correct(self, tmp_path: Path) -> None:
        """outputs_written contains both Tier 3 paths."""
        repo_root = _make_binding_skill_env(tmp_path)
        response = _valid_binding_response()

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-call-binding-derivation", "run-test-001", repo_root,
            )

        assert result.status == "success"
        expected = {
            "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
            "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
        }
        assert set(result.outputs_written) == expected


# ---------------------------------------------------------------------------
# C. Schema validation for Tier 3 required fields
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
# D. End-to-end run_agent with two-skill Phase 2 sequencing
# ---------------------------------------------------------------------------


def _make_phase2_agent_env(tmp_path: Path) -> dict:
    """Create environment for run_agent with concept_refiner (two skills)."""
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
        {"skill_catalog": [
            {
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
                ],
                "constitutional_constraints": [],
                "used_by_agents": ["concept_refiner"],
            },
            {
                "id": "concept-call-binding-derivation",
                "execution_mode": "tapm",
                "reads_from": [
                    "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
                    "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json",
                    "docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json",
                    "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json",
                    "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
                ],
                "writes_to": [
                    "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                    "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                ],
                "constitutional_constraints": [],
                "used_by_agents": ["concept_refiner"],
            },
        ]},
    )

    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml",
        _ARTIFACT_SCHEMAS,
    )

    manifest_path = repo_root / "manifest_test.yaml"
    _write_yaml(manifest_path, {
        "name": "test",
        "version": "1.1",
        "node_registry": [{
            "node_id": "n02_concept_refinement",
            "agent": "concept_refiner",
            "skills": [
                "concept-alignment-check",
                "concept-call-binding-derivation",
            ],
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
        "# concept_refiner\n"
        "Invoke concept-alignment-check first.\n"
        "Then invoke concept-call-binding-derivation.\n",
        encoding="utf-8",
    )

    # Skill spec files
    skill_dir = repo_root / ".claude" / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "concept-alignment-check.md").write_text(
        "# concept-alignment-check\nTest spec.", encoding="utf-8",
    )
    (skill_dir / "concept-call-binding-derivation.md").write_text(
        "# concept-call-binding-derivation\nTest spec.", encoding="utf-8",
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
        "skill_ids": [
            "concept-alignment-check",
            "concept-call-binding-derivation",
        ],
        "phase_id": "phase_02_concept_refinement",
    }


class TestPhase2AgentProducesArtifacts:
    """End-to-end: run_agent → two skills → all 3 artifacts."""

    def test_agent_invokes_both_skills_and_artifacts_written(
        self, tmp_path: Path
    ) -> None:
        """run_agent with concept_refiner invokes both skills in order."""
        kwargs = _make_phase2_agent_env(tmp_path)
        repo_root = kwargs["repo_root"]
        invocation_order: list[str] = []

        def _mock_run_skill(skill_id, run_id, repo_root_arg, inputs=None, **kw):
            invocation_order.append(skill_id)
            if skill_id == "concept-alignment-check":
                # Writes summary only
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
                return SkillResult(
                    status="success",
                    outputs_written=[
                        "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
                    ],
                )
            elif skill_id == "concept-call-binding-derivation":
                # Writes Tier 3 artifacts
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
                        "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                        "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                    ],
                )
            return SkillResult(status="failure", failure_reason=f"Unknown skill: {skill_id}")

        with patch(_RUN_SKILL_TARGET, side_effect=_mock_run_skill):
            result = run_agent(**kwargs)

        assert result.status == "success"

        # Verify invocation order
        assert invocation_order == [
            "concept-alignment-check",
            "concept-call-binding-derivation",
        ]

        # Verify all artifacts on disk
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

    def test_binding_skill_receives_refreshed_inputs(
        self, tmp_path: Path
    ) -> None:
        """After concept-alignment-check writes summary, binding skill can see it."""
        kwargs = _make_phase2_agent_env(tmp_path)
        repo_root = kwargs["repo_root"]
        binding_inputs_received: dict = {}

        def _mock_run_skill(skill_id, run_id, repo_root_arg, inputs=None, **kw):
            if skill_id == "concept-alignment-check":
                _write_json(
                    repo_root_arg / "docs" / "tier4_orchestration_state"
                    / "phase_outputs" / "phase2_concept_refinement"
                    / "concept_refinement_summary.json",
                    _valid_summary_response(run_id),
                )
                return SkillResult(
                    status="success",
                    outputs_written=[
                        "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
                    ],
                )
            elif skill_id == "concept-call-binding-derivation":
                # Capture what inputs were available at invocation time
                if inputs:
                    binding_inputs_received.update(inputs)
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
                        "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                        "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                    ],
                )
            return SkillResult(status="failure", failure_reason=f"Unknown: {skill_id}")

        with patch(_RUN_SKILL_TARGET, side_effect=_mock_run_skill):
            run_agent(**kwargs)

        # The summary should have been refreshed into inputs by _refresh_inputs_from_outputs
        summary_key = "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json"
        assert summary_key in binding_inputs_received
        assert binding_inputs_received[summary_key]["schema_id"] == "orch.phase2.concept_refinement_summary.v1"

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
# E. Fail-closed behavior for the binding skill
# ---------------------------------------------------------------------------


class TestCallBindingFailClosed:
    """Verify concept-call-binding-derivation fails closed on missing inputs."""

    def test_missing_summary_fails_cli_prompt(self, tmp_path: Path) -> None:
        """Binding skill fails MISSING_INPUT when summary is absent (cli-prompt mode).

        In TAPM mode, missing-input detection is Claude's responsibility
        (it reads from disk and follows the skill spec's failure protocol).
        In cli-prompt mode, the skill runtime's own input validation
        catches missing required inputs before Claude is invoked.
        This test uses cli-prompt mode to verify fail-closed at the runtime level.
        """
        repo_root = _make_binding_skill_env(tmp_path)

        # Override catalog to use cli-prompt mode for this test
        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [{
                "id": "concept-call-binding-derivation",
                "execution_mode": "cli-prompt",
                "reads_from": [
                    "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
                    "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json",
                    "docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json",
                    "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json",
                    "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
                ],
                "writes_to": [
                    "docs/tier3_project_instantiation/call_binding/topic_mapping.json",
                    "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                ],
                "constitutional_constraints": [],
                "used_by_agents": ["concept_refiner"],
            }]},
        )

        # Clear caches to pick up overridden catalog
        import runner.skill_runtime as _sr
        _sr._catalog_cache.clear()

        # Remove the pre-populated summary
        summary_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase2_concept_refinement" / "concept_refinement_summary.json"
        )
        summary_path.unlink()

        result = run_skill(
            "concept-call-binding-derivation", "run-test-001", repo_root,
        )

        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"

    def test_missing_mappings_in_response_fails(self, tmp_path: Path) -> None:
        """Binding response missing 'mappings' → MALFORMED_ARTIFACT."""
        repo_root = _make_binding_skill_env(tmp_path)
        response = _valid_binding_response()
        response["topic_mapping"] = {}

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-call-binding-derivation", "run-test-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_missing_compliance_fields_in_response_fails(self, tmp_path: Path) -> None:
        """Binding response missing compliance fields → MALFORMED_ARTIFACT."""
        repo_root = _make_binding_skill_env(tmp_path)
        response = _valid_binding_response()
        response["compliance_profile"] = {"eligibility_confirmed": True}

        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)):
            result = run_skill(
                "concept-call-binding-derivation", "run-test-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_empty_response_fails(self, tmp_path: Path) -> None:
        """Binding skill rejects empty JSON response."""
        repo_root = _make_binding_skill_env(tmp_path)

        with patch(_TRANSPORT_TARGET, return_value="{}"):
            result = run_skill(
                "concept-call-binding-derivation", "run-test-001", repo_root,
            )

        assert result.status == "failure"


# ---------------------------------------------------------------------------
# F. Transport and parse failure handling
# ---------------------------------------------------------------------------


class TestTransportFailures:
    """Verify transport/parse failures for both skills."""

    def test_summary_skill_transport_failure(self, tmp_path: Path) -> None:
        """Transport failure for concept-alignment-check → INCOMPLETE_OUTPUT."""
        from runner.claude_transport import ClaudeTransportError

        repo_root = _make_summary_skill_env(tmp_path)

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

    def test_binding_skill_transport_failure(self, tmp_path: Path) -> None:
        """Transport failure for binding skill → INCOMPLETE_OUTPUT."""
        from runner.claude_transport import ClaudeTransportError

        repo_root = _make_binding_skill_env(tmp_path)

        with patch(
            _TRANSPORT_TARGET,
            side_effect=ClaudeTransportError("CLI unavailable"),
        ):
            result = run_skill(
                "concept-call-binding-derivation", "run-fail-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
        assert not result.outputs_written

    def test_non_json_response_fails(self, tmp_path: Path) -> None:
        """Non-JSON Claude response → INCOMPLETE_OUTPUT."""
        repo_root = _make_summary_skill_env(tmp_path)

        with patch(_TRANSPORT_TARGET, return_value="I don't understand"):
            result = run_skill(
                "concept-alignment-check", "run-bad-001", repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
