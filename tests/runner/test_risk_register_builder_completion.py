"""
Tests for risk-register-builder completion fix.

Verifies that the simplified risk-register-builder skill:
  1. Completes through the expected runtime path (enrich_artifact mode)
  2. Produces a non-empty risk_register in the merged artifact
  3. Preserves existing fields (ethics_assessment, instrument_sections_addressed)
     through the enrich_artifact merge
  4. Does not silently add unsourced risks
  5. Does not regress schema or merge behavior
  6. TAPM prompt is small enough to avoid timeout

Root cause: run ad0d47cc showed risk-register-builder timing out at 600s in TAPM
mode due to overly complex skill spec (255 lines, gap-risk scanning, full WP
catalogue building). The fix converts to enrich_artifact output contract and
simplifies the spec to ~80 lines of near-mechanical transformation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from runner.skill_runtime import (
    _assemble_tapm_prompt,
    _get_skill_entry,
    _load_skill_spec,
    run_skill,
)
from runner.runtime_models import SkillResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear skill_runtime caches before each test."""
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    yield
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


def _base_artifact(run_id: str) -> dict:
    """Create a base implementation_architecture.json as produced by governance-model-builder."""
    return {
        "schema_id": "orch.phase6.implementation_architecture.v1",
        "run_id": run_id,
        "governance_matrix": [
            {
                "body_name": "Project Management Board",
                "composition": ["ATU", "BIIS", "CERIA"],
                "decision_scope": "Strategic decisions and financial oversight",
                "meeting_frequency": "Quarterly",
                "escalation_path": "To coordinator, then funding agency",
            }
        ],
        "management_roles": [
            {
                "role_id": "COORD-01",
                "role_name": "Project Coordinator",
                "assigned_to": "ATU",
                "responsibilities": ["Overall project management", "Report submission"],
            },
            {
                "role_id": "WPL-WP2",
                "role_name": "WP2 Lead",
                "assigned_to": "ATU",
                "responsibilities": ["Lead WP2 activities"],
            },
        ],
        "risk_register": [],
        "ethics_assessment": {
            "ethics_issues_identified": True,
            "issues": [
                {
                    "issue_id": "ETH-01",
                    "description": "Clinical data processing in healthcare demonstrator",
                    "mitigation": "Ethics approval submitted; data anonymisation layer",
                }
            ],
            "self_assessment_statement": (
                "Based on the compliance profile (ethics_review_required: true), "
                "the project involves ethics-sensitive activities."
            ),
        },
        "instrument_sections_addressed": [
            {"section_id": "3.2", "section_name": "Management structure", "status": "addressed"},
            {"section_id": "3.2.1", "section_name": "Risk management", "status": "addressed"},
        ],
    }


def _enrichment_response(run_id: str, num_risks: int = 3) -> str:
    """Build a valid enrich_artifact response with N risk entries."""
    risks = []
    for i in range(1, num_risks + 1):
        risks.append({
            "risk_id": f"RISK-{i:02d}",
            "description": f"Test risk {i} description",
            "category": "technical",
            "likelihood": "medium",
            "impact": "high",
            "mitigation": f"Seed mitigation for risk {i} [Affects: WP{i+1} (Test WP)]",
            "responsible_partner": "ATU",
        })
    return json.dumps({
        "schema_id": "orch.phase6.implementation_architecture.v1",
        "run_id": run_id,
        "risk_register": risks,
    })


def _make_env(tmp_path: Path, run_id: str) -> Path:
    """Create a minimal repo environment with base artifact on disk."""
    repo_root = tmp_path
    for rel in [
        ".claude/workflows/system_orchestration/skill_catalog.yaml",
        ".claude/workflows/system_orchestration/artifact_schema_specification.yaml",
    ]:
        src = _REPO_ROOT / rel
        dst = repo_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")
    src_spec = _REPO_ROOT / ".claude" / "skills" / "risk-register-builder.md"
    dst_spec = repo_root / ".claude" / "skills" / "risk-register-builder.md"
    dst_spec.parent.mkdir(parents=True, exist_ok=True)
    dst_spec.write_text(src_spec.read_text(encoding="utf-8-sig"), encoding="utf-8")

    # Write base artifact (produced by governance-model-builder)
    artifact_dir = (
        repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
        / "phase6_implementation_architecture"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "implementation_architecture.json").write_text(
        json.dumps(_base_artifact(run_id), indent=2), encoding="utf-8"
    )
    return repo_root


# ===========================================================================
# A. Catalog configuration tests
# ===========================================================================


class TestRiskRegisterBuilderCatalogConfig:
    """Verify the skill catalog is correctly configured for enrich_artifact."""

    def test_output_contract_is_enrich_artifact(self) -> None:
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        assert entry.get("output_contract") == "enrich_artifact"

    def test_enrichment_base_artifact_declared(self) -> None:
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        base = entry.get("enrichment_base_artifact", "")
        assert "implementation_architecture.json" in base

    def test_execution_mode_is_tapm(self) -> None:
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_gantt_not_in_reads_from(self) -> None:
        """gantt.json removed — not gate-required for risk register."""
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        for path in reads:
            assert "gantt" not in path, (
                f"gantt.json should not be in reads_from: {path}"
            )


# ===========================================================================
# B. Completion and merge tests
# ===========================================================================


class TestRiskRegisterBuilderCompletion:
    """Verify risk-register-builder completes and produces populated risk_register."""

    def test_completes_with_non_empty_risk_register(self, tmp_path: Path) -> None:
        """The core fix: skill completes and risk_register is populated."""
        run_id = "test-complete-01"
        repo_root = _make_env(tmp_path, run_id)
        with patch(_TRANSPORT_TARGET, return_value=_enrichment_response(run_id, 11)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success", (
            f"Expected success, got failure: {result.failure_reason}"
        )

        # Verify the merged artifact on disk
        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert len(artifact["risk_register"]) == 11
        for entry in artifact["risk_register"]:
            assert entry.get("risk_id") is not None
            assert entry.get("likelihood") in ("low", "medium", "high")
            assert entry.get("impact") in ("low", "medium", "high")
            assert entry.get("mitigation") and len(entry["mitigation"]) > 0

    def test_ethics_assessment_preserved(self, tmp_path: Path) -> None:
        """enrich_artifact must preserve existing ethics_assessment."""
        run_id = "test-preserve-ethics"
        repo_root = _make_env(tmp_path, run_id)
        with patch(_TRANSPORT_TARGET, return_value=_enrichment_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["ethics_assessment"] is not None
        assert artifact["ethics_assessment"]["ethics_issues_identified"] is True
        assert "ETH-01" in artifact["ethics_assessment"]["issues"][0]["issue_id"]
        assert len(artifact["ethics_assessment"]["self_assessment_statement"]) > 0

    def test_instrument_sections_preserved(self, tmp_path: Path) -> None:
        """enrich_artifact must preserve existing instrument_sections_addressed."""
        run_id = "test-preserve-sections"
        repo_root = _make_env(tmp_path, run_id)
        with patch(_TRANSPORT_TARGET, return_value=_enrichment_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert len(artifact["instrument_sections_addressed"]) == 2
        assert artifact["instrument_sections_addressed"][0]["section_id"] == "3.2"

    def test_governance_matrix_preserved(self, tmp_path: Path) -> None:
        """enrich_artifact must preserve existing governance_matrix."""
        run_id = "test-preserve-gov"
        repo_root = _make_env(tmp_path, run_id)
        with patch(_TRANSPORT_TARGET, return_value=_enrichment_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert len(artifact["governance_matrix"]) == 1
        assert artifact["governance_matrix"][0]["body_name"] == "Project Management Board"

    def test_management_roles_preserved(self, tmp_path: Path) -> None:
        """enrich_artifact must preserve existing management_roles."""
        run_id = "test-preserve-roles"
        repo_root = _make_env(tmp_path, run_id)
        with patch(_TRANSPORT_TARGET, return_value=_enrichment_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert len(artifact["management_roles"]) == 2


# ===========================================================================
# C. Constitutional constraint tests
# ===========================================================================


class TestRiskRegisterBuilderConstraints:
    """Verify constitutional constraints are enforced."""

    def test_prompt_contains_seed_constraint(self) -> None:
        """System prompt must contain the 'not silently added' constraint."""
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        skill_spec = _load_skill_spec("risk-register-builder", _REPO_ROOT)
        sys_p, _usr_p = _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="risk-register-builder",
            run_id="test",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
        )
        assert "flagged for operator review, not silently added" in sys_p

    def test_prompt_contains_traceability_constraint(self) -> None:
        """System prompt must contain the mitigation traceability constraint."""
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        skill_spec = _load_skill_spec("risk-register-builder", _REPO_ROOT)
        sys_p, _usr_p = _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="risk-register-builder",
            run_id="test",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
        )
        assert "traceable to project activities" in sys_p

    def test_spec_forbids_unsourced_risks(self) -> None:
        """Skill spec must instruct not to add risks beyond seeds."""
        spec = _load_skill_spec("risk-register-builder", _REPO_ROOT)
        assert "Do NOT invent or add risks beyond" in spec or \
               "exactly as many entries as there are seeds" in spec

    def test_base_artifact_missing_fails(self, tmp_path: Path) -> None:
        """enrich_artifact should fail when base artifact is missing."""
        run_id = "test-missing-base"
        repo_root = tmp_path
        # Set up catalog and skill spec but NO base artifact
        for rel in [
            ".claude/workflows/system_orchestration/skill_catalog.yaml",
            ".claude/workflows/system_orchestration/artifact_schema_specification.yaml",
        ]:
            src = _REPO_ROOT / rel
            dst = repo_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")
        src_spec = _REPO_ROOT / ".claude" / "skills" / "risk-register-builder.md"
        dst_spec = repo_root / ".claude" / "skills" / "risk-register-builder.md"
        dst_spec.parent.mkdir(parents=True, exist_ok=True)
        dst_spec.write_text(src_spec.read_text(encoding="utf-8-sig"), encoding="utf-8")
        # Create the directory but NOT the file
        (repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
         / "phase6_implementation_architecture").mkdir(parents=True, exist_ok=True)

        with patch(_TRANSPORT_TARGET, return_value=_enrichment_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "failure"
        assert "MISSING_INPUT" in (result.failure_category or "")


# ===========================================================================
# D. Prompt size and timeout tests
# ===========================================================================


class TestRiskRegisterBuilderPromptSize:
    """Verify the simplified spec produces a bounded prompt."""

    def _assemble_prompt(self) -> tuple[str, str]:
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        skill_spec = _load_skill_spec("risk-register-builder", _REPO_ROOT)
        return _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="risk-register-builder",
            run_id="test-prompt-size",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
            node_id="n06_implementation_architecture",
        )

    def test_total_prompt_under_15kb(self) -> None:
        """Simplified spec should produce a prompt well under 15KB."""
        sys_p, usr_p = self._assemble_prompt()
        total = len(sys_p) + len(usr_p)
        assert total < 15_000, (
            f"TAPM prompt is {total} chars; simplified spec should be under 15KB "
            f"(was ~27.7KB before fix)"
        )

    def test_user_prompt_under_10kb(self) -> None:
        """User prompt should be dramatically smaller than the pre-fix 26.5KB."""
        _, usr_p = self._assemble_prompt()
        assert len(usr_p) < 10_000, (
            f"User prompt is {len(usr_p)} chars; should be under 10KB "
            f"(was 26,524 chars before fix)"
        )

    def test_prompt_lists_only_two_declared_inputs(self) -> None:
        """Prompt should list exactly 2 declared inputs (risks.json, wp_structure.json)."""
        _, usr_p = self._assemble_prompt()
        assert "risks.json" in usr_p
        assert "wp_structure.json" in usr_p
        assert "gantt.json" not in usr_p


# ===========================================================================
# E. Schema validation on merged result
# ===========================================================================


class TestRiskRegisterBuilderSchemaValidation:
    """Verify the merged artifact passes schema validation."""

    def test_merged_artifact_has_all_required_fields(self, tmp_path: Path) -> None:
        run_id = "test-schema-01"
        repo_root = _make_env(tmp_path, run_id)
        with patch(_TRANSPORT_TARGET, return_value=_enrichment_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        # All required fields must be present
        assert artifact["schema_id"] == "orch.phase6.implementation_architecture.v1"
        assert artifact["run_id"] == run_id
        assert "artifact_status" not in artifact
        assert isinstance(artifact["risk_register"], list)
        assert isinstance(artifact["governance_matrix"], list)
        assert isinstance(artifact["management_roles"], list)
        assert isinstance(artifact["ethics_assessment"], dict)
        assert isinstance(artifact["instrument_sections_addressed"], list)

    def test_schema_id_mismatch_in_patch_fails(self, tmp_path: Path) -> None:
        """Enrichment patch with wrong schema_id should be rejected."""
        run_id = "test-schema-mismatch"
        repo_root = _make_env(tmp_path, run_id)
        bad_response = json.dumps({
            "schema_id": "wrong.schema.v1",
            "run_id": run_id,
            "risk_register": [{"risk_id": "R-01", "description": "x", "category": "technical",
                               "likelihood": "low", "impact": "low", "mitigation": "y",
                               "responsible_partner": "P1"}],
        })
        with patch(_TRANSPORT_TARGET, return_value=bad_response):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "failure"
        assert "schema_id mismatch" in (result.failure_reason or "").lower()
