"""
Tests for Phase 6 field production — ethics_assessment, instrument_sections_addressed,
and constitutional-compliance-check applicability.

Verifies that:
  1. governance-model-builder output contract includes non-null ethics_assessment
     and non-empty instrument_sections_addressed after the fix
  2. risk-register-builder preserves non-risk fields (ethics_assessment,
     instrument_sections_addressed) through merge-on-write
  3. constitutional-compliance-check does not hard-fail in Phase 6 solely
     because docs/tier5_deliverables/ is absent
  4. Phase 6 agent body can reach exit-gate evaluation when governance and
     risk production both succeed

Root cause addressed: run 71c050d4 showed that ethics_assessment remained null
and instrument_sections_addressed remained [] because no executed skill populated
them. The governance-model-builder has been extended to produce these fields from
compliance_profile.json and section_schema_registry.json. The constitutional-
compliance-check had docs/tier5_deliverables/ as a required reads_from, which
doesn't exist during Phase 6; it has been moved to optional_reads_from.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runner.skill_runtime import (
    _get_skill_entry,
    _load_skill_catalog,
    run_skill,
)
from runner.runtime_models import SkillResult

# ---------------------------------------------------------------------------
# Fixtures — real repo paths
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


# ===========================================================================
# A. Skill catalog contract tests
# ===========================================================================


class TestGovernanceModelBuilderCatalogContract:
    """Verify the skill catalog declares the new reads_from entries."""

    def test_reads_from_includes_compliance_profile(self) -> None:
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier3_project_instantiation/call_binding/compliance_profile.json" in reads

    def test_reads_from_includes_selected_call(self) -> None:
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier3_project_instantiation/call_binding/selected_call.json" in reads

    def test_reads_from_includes_section_schema_registry(self) -> None:
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json" in reads

    def test_ethics_constraint_present(self) -> None:
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        constraints = entry.get("constitutional_constraints", [])
        assert any("ethics" in c.lower() for c in constraints)


class TestConstitutionalComplianceCheckCatalog:
    """Verify TAPM config: Tier 5 optional, broad phase_outputs/ removed."""

    def test_tier5_not_in_reads_from(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier5_deliverables/" not in reads

    def test_tier5_in_optional_reads_from(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        optional = entry.get("optional_reads_from", [])
        assert "docs/tier5_deliverables/" in optional

    def test_broad_phase_outputs_not_in_reads_from(self) -> None:
        """TAPM migration: broad directory removed from reads_from."""
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier4_orchestration_state/phase_outputs/" not in reads

    def test_claude_md_still_required(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "CLAUDE.md" in reads

    def test_execution_mode_is_tapm(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"


# ===========================================================================
# B. Governance-model-builder output contract tests
# ===========================================================================


def _make_gov_env(tmp_path: Path) -> Path:
    """Create a minimal repo environment for governance-model-builder."""
    repo_root = tmp_path
    for rel in [
        ".claude/workflows/system_orchestration/skill_catalog.yaml",
        ".claude/workflows/system_orchestration/artifact_schema_specification.yaml",
    ]:
        src = _REPO_ROOT / rel
        dst = repo_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")
    src_spec = _REPO_ROOT / ".claude" / "skills" / "governance-model-builder.md"
    dst_spec = repo_root / ".claude" / "skills" / "governance-model-builder.md"
    dst_spec.parent.mkdir(parents=True, exist_ok=True)
    dst_spec.write_text(src_spec.read_text(encoding="utf-8-sig"), encoding="utf-8")
    (repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
     / "phase6_implementation_architecture").mkdir(parents=True, exist_ok=True)
    return repo_root


def _gov_response_with_fields(run_id: str) -> str:
    """A valid governance-model-builder response with all required fields."""
    return json.dumps({
        "schema_id": "orch.phase6.implementation_architecture.v1",
        "run_id": run_id,
        "governance_matrix": [
            {
                "body_name": "Project Management Board",
                "composition": ["P1", "P2"],
                "decision_scope": "Strategic decisions",
                "meeting_frequency": "Quarterly",
                "escalation_path": "To coordinator",
            }
        ],
        "management_roles": [
            {
                "role_id": "COORD-01",
                "role_name": "Coordinator",
                "assigned_to": "P1",
                "responsibilities": ["Overall management"],
            }
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
                "the project involves ethics-sensitive activities in the healthcare "
                "demonstrator (WP5). Ethics approval has been initiated."
            ),
        },
        "instrument_sections_addressed": [
            {"section_id": "3.2", "section_name": "Management structure", "status": "addressed"},
            {"section_id": "3.2.1", "section_name": "Risk management", "status": "addressed"},
            {"section_id": "3.2.2", "section_name": "Ethics", "status": "addressed"},
        ],
    })


class TestGovernanceModelBuilderFieldProduction:
    """Verify governance-model-builder produces non-null ethics_assessment
    and non-empty instrument_sections_addressed."""

    def test_output_contains_ethics_assessment(self, tmp_path: Path) -> None:
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-gov-ethics-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_fields(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        # Verify the written artifact
        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["ethics_assessment"] is not None
        assert isinstance(artifact["ethics_assessment"], dict)
        assert "ethics_issues_identified" in artifact["ethics_assessment"]
        assert "self_assessment_statement" in artifact["ethics_assessment"]
        assert len(artifact["ethics_assessment"]["self_assessment_statement"]) > 0

    def test_output_contains_instrument_sections(self, tmp_path: Path) -> None:
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-gov-sections-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_fields(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert isinstance(artifact["instrument_sections_addressed"], list)
        assert len(artifact["instrument_sections_addressed"]) > 0
        for entry in artifact["instrument_sections_addressed"]:
            assert "section_id" in entry
            assert "status" in entry

    def test_risk_register_is_placeholder(self, tmp_path: Path) -> None:
        """risk_register should be [] — populated by risk-register-builder."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-gov-risk-placeholder"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_fields(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["risk_register"] == []


# ===========================================================================
# C. Risk-register-builder field preservation tests
# ===========================================================================


def _make_risk_env(tmp_path: Path, *, pre_existing_artifact: dict) -> Path:
    """Create a repo with an existing implementation_architecture.json."""
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

    # Write pre-existing implementation_architecture.json
    artifact_dir = (
        repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
        / "phase6_implementation_architecture"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "implementation_architecture.json").write_text(
        json.dumps(pre_existing_artifact, indent=2), encoding="utf-8"
    )
    return repo_root


class TestRiskRegisterBuilderFieldPreservation:
    """Verify risk-register-builder preserves ethics_assessment and
    instrument_sections_addressed when enriching the risk_register."""

    def _pre_existing_artifact(self, run_id: str) -> dict:
        return {
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": run_id,
            "governance_matrix": [{"body_name": "PMB", "composition": ["P1"], "decision_scope": "Strategic"}],
            "management_roles": [{"role_id": "COORD-01", "role_name": "Coordinator", "assigned_to": "P1", "responsibilities": ["Manage"]}],
            "risk_register": [],
            "ethics_assessment": {
                "ethics_issues_identified": True,
                "issues": [{"issue_id": "ETH-01", "description": "Data privacy", "mitigation": "GDPR compliance"}],
                "self_assessment_statement": "Project involves personal data processing.",
            },
            "instrument_sections_addressed": [
                {"section_id": "3.2", "section_name": "Management", "status": "addressed"},
            ],
        }

    def _risk_response(self, run_id: str) -> str:
        """enrich_artifact response: only risk_register plus metadata."""
        return json.dumps({
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": run_id,
            "risk_register": [
                {
                    "risk_id": "RISK-01",
                    "description": "Technical integration risk",
                    "category": "technical",
                    "likelihood": "medium",
                    "impact": "high",
                    "mitigation": "Addressed in T2-02 (task_id: T2-02, WP2)",
                    "responsible_partner": "P1",
                }
            ],
        })

    def test_ethics_assessment_preserved_after_risk_enrichment(self, tmp_path: Path) -> None:
        run_id = "test-risk-preserve-01"
        pre = self._pre_existing_artifact(run_id)
        repo_root = _make_risk_env(tmp_path, pre_existing_artifact=pre)

        with patch(_TRANSPORT_TARGET, return_value=self._risk_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        # ethics_assessment must be preserved from pre-existing artifact
        assert artifact["ethics_assessment"] is not None
        assert artifact["ethics_assessment"]["ethics_issues_identified"] is True
        assert artifact["ethics_assessment"]["self_assessment_statement"] == pre["ethics_assessment"]["self_assessment_statement"]

    def test_instrument_sections_preserved_after_risk_enrichment(self, tmp_path: Path) -> None:
        run_id = "test-risk-preserve-02"
        pre = self._pre_existing_artifact(run_id)
        repo_root = _make_risk_env(tmp_path, pre_existing_artifact=pre)

        with patch(_TRANSPORT_TARGET, return_value=self._risk_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        # instrument_sections_addressed must be preserved from pre-existing artifact
        assert len(artifact["instrument_sections_addressed"]) == 1
        assert artifact["instrument_sections_addressed"][0]["section_id"] == "3.2"

    def test_risk_register_is_populated(self, tmp_path: Path) -> None:
        run_id = "test-risk-populated-01"
        pre = self._pre_existing_artifact(run_id)
        repo_root = _make_risk_env(tmp_path, pre_existing_artifact=pre)

        with patch(_TRANSPORT_TARGET, return_value=self._risk_response(run_id)):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert len(artifact["risk_register"]) > 0


# ===========================================================================
# D. Constitutional-compliance-check applicability tests
# ===========================================================================


def _make_compliance_env(tmp_path: Path, *, with_tier5: bool = False) -> Path:
    """Create a repo for constitutional-compliance-check testing."""
    repo_root = tmp_path
    for rel in [
        ".claude/workflows/system_orchestration/skill_catalog.yaml",
        ".claude/workflows/system_orchestration/artifact_schema_specification.yaml",
    ]:
        src = _REPO_ROOT / rel
        dst = repo_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")
    src_spec = _REPO_ROOT / ".claude" / "skills" / "constitutional-compliance-check.md"
    dst_spec = repo_root / ".claude" / "skills" / "constitutional-compliance-check.md"
    dst_spec.parent.mkdir(parents=True, exist_ok=True)
    dst_spec.write_text(src_spec.read_text(encoding="utf-8-sig"), encoding="utf-8")

    # CLAUDE.md (required reads_from)
    (repo_root / "CLAUDE.md").write_text("# Constitution\nTest.", encoding="utf-8")

    # Tier 4 phase outputs (required reads_from)
    phase_dir = repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
    phase_dir.mkdir(parents=True, exist_ok=True)
    p6_dir = phase_dir / "phase6_implementation_architecture"
    p6_dir.mkdir(parents=True, exist_ok=True)
    (p6_dir / "implementation_architecture.json").write_text(
        json.dumps({
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": "test-compliance-01",
            "governance_matrix": [],
            "management_roles": [],
            "risk_register": [],
            "ethics_assessment": {"ethics_issues_identified": False, "issues": [], "self_assessment_statement": "No issues."},
            "instrument_sections_addressed": [],
        }),
        encoding="utf-8",
    )

    if with_tier5:
        t5_dir = repo_root / "docs" / "tier5_deliverables" / "proposal_sections"
        t5_dir.mkdir(parents=True, exist_ok=True)
        (t5_dir / "section_1.json").write_text("{}", encoding="utf-8")

    return repo_root


class TestConstitutionalComplianceCheckApplicability:
    """Verify constitutional-compliance-check does not hard-fail when Tier 5 is absent."""

    def test_no_missing_input_failure_without_tier5(self, tmp_path: Path) -> None:
        """Phase 6 context: Tier 5 doesn't exist. Skill must NOT fail with MISSING_INPUT."""
        repo_root = _make_compliance_env(tmp_path, with_tier5=False)
        compliance_response = json.dumps({
            "report_id": "compliance-test-01",
            "skill_id": "constitutional-compliance-check",
            "invoking_agent": "implementation_architect",
            "run_id_reference": "test-compliance-01",
            "artifact_audited": "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json",
            "section13_checks": [],
            "summary": {"total_prohibitions_checked": 12, "violations_found": 0},
            "timestamp": "2026-04-23T00:00:00Z",
        })
        with patch(_TRANSPORT_TARGET, return_value=compliance_response):
            result = run_skill("constitutional-compliance-check", "test-compliance-01", repo_root)

        # Must NOT be a MISSING_INPUT failure for Tier 5
        if result.status == "failure":
            assert "tier5_deliverables" not in (result.failure_reason or "").lower(), (
                f"constitutional-compliance-check failed on Tier 5 absence: {result.failure_reason}"
            )


# ===========================================================================
# E. Phase 6 exit-gate reachability tests
# ===========================================================================


class TestPhase6ExitGateReachability:
    """Verify Phase 6 agent body can reach exit-gate evaluation."""

    def test_gate_relevant_artifact_check(self, tmp_path: Path) -> None:
        """After governance + risk skills write the artifact, the agent runtime
        should determine can_evaluate_exit_gate=True."""
        from runner.agent_runtime import _determine_can_evaluate_exit_gate

        repo_root = tmp_path

        # Copy manifest
        src_manifest = _REPO_ROOT / ".claude" / "workflows" / "system_orchestration" / "manifest.compile.yaml"
        dst_manifest = repo_root / ".claude" / "workflows" / "system_orchestration" / "manifest.compile.yaml"
        dst_manifest.parent.mkdir(parents=True, exist_ok=True)
        dst_manifest.write_text(src_manifest.read_text(encoding="utf-8-sig"), encoding="utf-8")

        # Write the Phase 6 canonical artifact
        artifact_dir = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture"
        )
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "implementation_architecture.json").write_text(
            json.dumps({
                "schema_id": "orch.phase6.implementation_architecture.v1",
                "run_id": "test-gate-reach",
                "governance_matrix": [{"body_name": "PMB", "composition": ["P1"], "decision_scope": "Strategic"}],
                "management_roles": [{"role_id": "COORD-01", "role_name": "Coord", "assigned_to": "P1", "responsibilities": ["Manage"]}],
                "risk_register": [{"risk_id": "R1", "description": "Test", "category": "technical", "likelihood": "low", "impact": "low", "mitigation": "Addressed in T1 (task_id: T1, WP1)"}],
                "ethics_assessment": {"ethics_issues_identified": False, "issues": [], "self_assessment_statement": "No issues identified."},
                "instrument_sections_addressed": [{"section_id": "3.2", "section_name": "Management", "status": "addressed"}],
            }),
            encoding="utf-8",
        )

        # Clear caches
        import runner.agent_runtime as _ar
        _ar._artifact_registry_cache.clear()

        can_evaluate = _determine_can_evaluate_exit_gate(
            "n06_implementation_architecture",
            repo_root,
            manifest_path=dst_manifest,
        )
        assert can_evaluate is True, (
            "Phase 6 artifact is present and non-empty but "
            "_determine_can_evaluate_exit_gate returned False"
        )


# ===========================================================================
# F. Traceability-footer production tests (§13.9 fix)
# ===========================================================================


def _gov_response_with_traceability_footer(run_id: str) -> str:
    """A valid governance-model-builder response including traceability_footer."""
    return json.dumps({
        "schema_id": "orch.phase6.implementation_architecture.v1",
        "run_id": run_id,
        "governance_matrix": [
            {
                "body_name": "General Assembly",
                "composition": ["P1", "P2"],
                "decision_scope": "Strategic governance",
                "meeting_frequency": "Annual",
                "escalation_path": "To coordinator",
            }
        ],
        "management_roles": [
            {
                "role_id": "COORD-01",
                "role_name": "Coordinator",
                "assigned_to": "P1",
                "responsibilities": ["Overall management"],
            }
        ],
        "risk_register": [],
        "ethics_assessment": {
            "ethics_issues_identified": True,
            "issues": [
                {
                    "issue_id": "ETH-01",
                    "description": "AI ethics in healthcare demonstrator",
                    "mitigation": "Ethics committee oversight",
                }
            ],
            "self_assessment_statement": (
                "Based on implementation_constraints.json: ethics_self_assessment_required."
            ),
        },
        "instrument_sections_addressed": [
            {"section_id": "A.4", "section_name": "Ethics and Security", "status": "addressed"},
            {"section_id": "B.3.1", "section_name": "Work plan and resources", "status": "addressed"},
        ],
        "traceability_footer": {
            "primary_sources": [
                {
                    "tier": 1,
                    "source_path": "docs/tier1_normative_framework/extracted/governance_principles.json",
                    "relevant_fields": [
                        "no_prescribed_governance_body_names",
                        "consortium_agreement_guidance",
                        "escalation_path_constraint",
                    ],
                },
                {
                    "tier": 1,
                    "source_path": "docs/tier1_normative_framework/extracted/implementation_constraints.json",
                    "relevant_fields": [
                        "ethics_self_assessment_required",
                        "civil_focus_constraint",
                        "gender_equality_plan_eligibility",
                    ],
                },
                {
                    "tier": 2,
                    "source_path": "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json",
                },
                {
                    "tier": 3,
                    "source_path": "docs/tier3_project_instantiation/consortium/partners.json",
                },
                {
                    "tier": 3,
                    "source_path": "docs/tier3_project_instantiation/consortium/roles.json",
                },
                {
                    "tier": 3,
                    "source_path": "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                },
                {
                    "tier": 4,
                    "source_path": "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
                },
            ],
        },
    })


class TestTraceabilityFooterProduction:
    """Verify governance-model-builder produces traceability_footer with
    full repo-relative Tier 1 paths, satisfying §13.9."""

    def test_traceability_footer_written_to_artifact(self, tmp_path: Path) -> None:
        """traceability_footer must be present in the written artifact."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-trace-footer-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_traceability_footer(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert "traceability_footer" in artifact
        assert "primary_sources" in artifact["traceability_footer"]

    def test_traceability_footer_contains_tier1_paths(self, tmp_path: Path) -> None:
        """primary_sources must contain at least two Tier 1 entries with
        full docs/tier1_normative_framework/extracted/ paths."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-trace-tier1-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_traceability_footer(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        sources = artifact["traceability_footer"]["primary_sources"]

        tier1_sources = [s for s in sources if s.get("tier") == 1]
        assert len(tier1_sources) >= 2, (
            f"Expected at least 2 Tier 1 sources, found {len(tier1_sources)}"
        )

        tier1_paths = [s["source_path"] for s in tier1_sources]
        assert any(
            "docs/tier1_normative_framework/extracted/governance_principles.json" in p
            for p in tier1_paths
        ), f"governance_principles.json not found in Tier 1 paths: {tier1_paths}"
        assert any(
            "docs/tier1_normative_framework/extracted/implementation_constraints.json" in p
            for p in tier1_paths
        ), f"implementation_constraints.json not found in Tier 1 paths: {tier1_paths}"

    def test_traceability_footer_uses_full_paths(self, tmp_path: Path) -> None:
        """All source_path values must be full repo-relative paths starting
        with 'docs/', not abbreviated file names."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-trace-fullpath-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_traceability_footer(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        sources = artifact["traceability_footer"]["primary_sources"]

        for source in sources:
            path = source["source_path"]
            assert path.startswith("docs/"), (
                f"source_path {path!r} does not start with 'docs/' — "
                f"abbreviated file names do not satisfy §13.9"
            )

    def test_traceability_footer_preserved_after_risk_enrichment(self, tmp_path: Path) -> None:
        """risk-register-builder merge must preserve traceability_footer
        from the base artifact."""
        run_id = "test-trace-preserve-01"
        pre_artifact = {
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": run_id,
            "governance_matrix": [{"body_name": "PMB", "composition": ["P1"], "decision_scope": "Strategic"}],
            "management_roles": [{"role_id": "COORD-01", "role_name": "Coordinator", "assigned_to": "P1", "responsibilities": ["Manage"]}],
            "risk_register": [],
            "ethics_assessment": {
                "ethics_issues_identified": True,
                "issues": [{"issue_id": "ETH-01", "description": "Test", "mitigation": "Test"}],
                "self_assessment_statement": "Ethics self-assessment.",
            },
            "instrument_sections_addressed": [
                {"section_id": "A.4", "section_name": "Ethics", "status": "addressed"},
            ],
            "traceability_footer": {
                "primary_sources": [
                    {"tier": 1, "source_path": "docs/tier1_normative_framework/extracted/governance_principles.json"},
                    {"tier": 1, "source_path": "docs/tier1_normative_framework/extracted/implementation_constraints.json"},
                ],
            },
        }
        repo_root = _make_risk_env(tmp_path, pre_existing_artifact=pre_artifact)

        risk_response = json.dumps({
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": run_id,
            "risk_register": [
                {
                    "risk_id": "RISK-01",
                    "description": "Integration risk",
                    "category": "technical",
                    "likelihood": "medium",
                    "impact": "high",
                    "mitigation": "Modular architecture (task_id: T2-02, WP2)",
                    "responsible_partner": "P1",
                }
            ],
        })

        with patch(_TRANSPORT_TARGET, return_value=risk_response):
            result = run_skill("risk-register-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        # traceability_footer must survive the merge
        assert "traceability_footer" in artifact, (
            "traceability_footer was lost during risk-register-builder merge"
        )
        tier1_paths = [
            s["source_path"]
            for s in artifact["traceability_footer"]["primary_sources"]
            if s.get("tier") == 1
        ]
        assert len(tier1_paths) >= 2, (
            "Tier 1 sources lost during risk-register-builder merge"
        )

    def test_existing_fields_preserved_with_traceability_footer(self, tmp_path: Path) -> None:
        """Adding traceability_footer must not break existing required fields."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-trace-compat-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_traceability_footer(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        # All existing required fields must still be present
        assert artifact["schema_id"] == "orch.phase6.implementation_architecture.v1"
        assert artifact["run_id"] == run_id
        assert isinstance(artifact["governance_matrix"], list)
        assert len(artifact["governance_matrix"]) > 0
        assert isinstance(artifact["management_roles"], list)
        assert isinstance(artifact["risk_register"], list)
        assert isinstance(artifact["ethics_assessment"], dict)
        assert isinstance(artifact["instrument_sections_addressed"], list)
        assert "artifact_status" not in artifact


class TestTraceabilityFooterSchemaRegistration:
    """Verify the artifact schema accepts traceability_footer as optional."""

    def test_schema_has_traceability_footer(self) -> None:
        """artifact_schema_specification.yaml Section 1.6 must include
        traceability_footer as an optional field."""
        schema_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml"
        )
        spec = yaml.safe_load(schema_path.read_text(encoding="utf-8-sig"))
        impl_arch = spec["tier4_phase_output_schemas"]["implementation_architecture"]
        fields = impl_arch["fields"]

        assert "traceability_footer" in fields, (
            "traceability_footer not found in implementation_architecture schema"
        )
        assert fields["traceability_footer"]["required"] is False, (
            "traceability_footer must be optional (required: false)"
        )

    def test_schema_traceability_footer_has_primary_sources(self) -> None:
        """traceability_footer schema must define primary_sources array."""
        schema_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "artifact_schema_specification.yaml"
        )
        spec = yaml.safe_load(schema_path.read_text(encoding="utf-8-sig"))
        footer = spec["tier4_phase_output_schemas"]["implementation_architecture"]["fields"]["traceability_footer"]
        ps = footer["fields"]["primary_sources"]

        assert ps["type"] == "array"
        assert ps["required"] is True


# ===========================================================================
# G. Gender-dimension §13.2 regression tests
# ===========================================================================


# Violating phrases: any call-specific assertion about the topic exemption
# without Tier 2B traceability.
_VIOLATING_PHRASES = [
    "this call does not exempt the topic",
    "this call does not exempt",
    "the topic does not state non-relevance",
    "the topic does not exempt",
    "this topic does not exempt",
    "no exemption is stated in the topic",
]


def _gov_response_with_gender_violation(run_id: str) -> str:
    """governance-model-builder response containing a §13.2-violating
    gender-dimension assertion WITHOUT a Tier 2B traceability source."""
    return json.dumps({
        "schema_id": "orch.phase6.implementation_architecture.v1",
        "run_id": run_id,
        "governance_matrix": [
            {
                "body_name": "General Assembly",
                "composition": ["P1", "P2"],
                "decision_scope": "Strategic",
                "meeting_frequency": "Annual",
                "escalation_path": "To coordinator",
            }
        ],
        "management_roles": [
            {
                "role_id": "COORD-01",
                "role_name": "Coordinator",
                "assigned_to": "P1",
                "responsibilities": ["Overall management"],
            }
        ],
        "risk_register": [],
        "ethics_assessment": {
            "ethics_issues_identified": True,
            "issues": [
                {
                    "issue_id": "ETH-01",
                    "description": "AI ethics in healthcare demonstrator",
                    "mitigation": "Ethics committee oversight",
                }
            ],
            "self_assessment_statement": (
                "Integration of the gender dimension is mandatory; "
                "this call does not exempt the topic, so integration is required."
            ),
        },
        "instrument_sections_addressed": [
            {"section_id": "A.4", "section_name": "Ethics and Security", "status": "addressed"},
        ],
        "traceability_footer": {
            "primary_sources": [
                {
                    "tier": 1,
                    "source_path": "docs/tier1_normative_framework/extracted/governance_principles.json",
                },
                {
                    "tier": 1,
                    "source_path": "docs/tier1_normative_framework/extracted/implementation_constraints.json",
                },
                {
                    "tier": 3,
                    "source_path": "docs/tier3_project_instantiation/consortium/partners.json",
                },
                {
                    "tier": 3,
                    "source_path": "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                },
            ],
        },
    })


def _gov_response_with_safe_gender_wording(run_id: str) -> str:
    """governance-model-builder response with the correct safe wording
    (no call-specific assertion, no Tier 2B traceability needed)."""
    return json.dumps({
        "schema_id": "orch.phase6.implementation_architecture.v1",
        "run_id": run_id,
        "governance_matrix": [
            {
                "body_name": "General Assembly",
                "composition": ["P1", "P2"],
                "decision_scope": "Strategic",
                "meeting_frequency": "Annual",
                "escalation_path": "To coordinator",
            }
        ],
        "management_roles": [
            {
                "role_id": "COORD-01",
                "role_name": "Coordinator",
                "assigned_to": "P1",
                "responsibilities": ["Overall management"],
            }
        ],
        "risk_register": [],
        "ethics_assessment": {
            "ethics_issues_identified": True,
            "issues": [
                {
                    "issue_id": "ETH-01",
                    "description": "AI ethics in healthcare demonstrator",
                    "mitigation": "Ethics committee oversight",
                }
            ],
            "self_assessment_statement": (
                "Integration of the gender dimension in research and innovation "
                "content follows the Tier 1 default rule that it is mandatory "
                "unless the topic explicitly states non-relevance. No Tier 2B "
                "exemption source is currently cited in this Phase 6 artifact; "
                "Phase 8 drafting must either add the relevant Tier 2B topic-source "
                "reference or keep the claim framed as pending call-specific "
                "confirmation."
            ),
        },
        "instrument_sections_addressed": [
            {"section_id": "A.4", "section_name": "Ethics and Security", "status": "addressed"},
        ],
        "traceability_footer": {
            "primary_sources": [
                {
                    "tier": 1,
                    "source_path": "docs/tier1_normative_framework/extracted/governance_principles.json",
                },
                {
                    "tier": 1,
                    "source_path": "docs/tier1_normative_framework/extracted/implementation_constraints.json",
                },
                {
                    "tier": 3,
                    "source_path": "docs/tier3_project_instantiation/consortium/partners.json",
                },
                {
                    "tier": 3,
                    "source_path": "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
                },
            ],
        },
    })


def _gov_response_with_tier2b_backed_assertion(run_id: str) -> str:
    """governance-model-builder response with a call-specific assertion
    THAT IS backed by a Tier 2B traceability source — should be valid."""
    return json.dumps({
        "schema_id": "orch.phase6.implementation_architecture.v1",
        "run_id": run_id,
        "governance_matrix": [
            {
                "body_name": "General Assembly",
                "composition": ["P1", "P2"],
                "decision_scope": "Strategic",
                "meeting_frequency": "Annual",
                "escalation_path": "To coordinator",
            }
        ],
        "management_roles": [
            {
                "role_id": "COORD-01",
                "role_name": "Coordinator",
                "assigned_to": "P1",
                "responsibilities": ["Overall management"],
            }
        ],
        "risk_register": [],
        "ethics_assessment": {
            "ethics_issues_identified": True,
            "issues": [
                {
                    "issue_id": "ETH-01",
                    "description": "AI ethics in healthcare demonstrator",
                    "mitigation": "Ethics committee oversight",
                }
            ],
            "self_assessment_statement": (
                "Integration of the gender dimension is mandatory; "
                "the topic text has been reviewed and does not state non-relevance "
                "(Tier 2B: scope_requirements.json)."
            ),
        },
        "instrument_sections_addressed": [
            {"section_id": "A.4", "section_name": "Ethics and Security", "status": "addressed"},
        ],
        "traceability_footer": {
            "primary_sources": [
                {
                    "tier": 1,
                    "source_path": "docs/tier1_normative_framework/extracted/implementation_constraints.json",
                },
                {
                    "tier": 2,
                    "source_path": "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
                    "relevant_fields": ["gender_dimension_exemption_check"],
                },
            ],
        },
    })


class TestGenderDimensionTraceability:
    """Regression tests for §13.2: governance-model-builder must not emit
    unsupported call-specific gender-exemption assertions without Tier 2B
    traceability in the traceability_footer."""

    def test_skill_spec_contains_gender_wording_constraint(self) -> None:
        """governance-model-builder.md must contain the Step 2.7.1 gender
        dimension wording guard."""
        spec_path = _REPO_ROOT / ".claude" / "skills" / "governance-model-builder.md"
        content = spec_path.read_text(encoding="utf-8-sig")
        assert "Step 2.7.1" in content
        assert "Gender-dimension wording constraint" in content
        assert "13.2" in content

    def test_skill_spec_contains_constraint_3(self) -> None:
        """governance-model-builder.md must declare Constraint 3 for
        gender-dimension Tier 2B traceability."""
        spec_path = _REPO_ROOT / ".claude" / "skills" / "governance-model-builder.md"
        content = spec_path.read_text(encoding="utf-8-sig")
        assert "Constraint 3" in content
        assert "gender-dimension exemption require Tier 2B traceability" in content

    def test_skill_spec_prohibits_unsupported_call_assertion(self) -> None:
        """The spec must contain the prohibition language so Claude sees it."""
        spec_path = _REPO_ROOT / ".claude" / "skills" / "governance-model-builder.md"
        content = spec_path.read_text(encoding="utf-8-sig")
        assert "MUST NOT assert" in content
        assert "this call does not exempt the topic" in content

    def test_skill_spec_prescribes_safe_fallback_wording(self) -> None:
        """The spec must contain the exact safe fallback wording."""
        spec_path = _REPO_ROOT / ".claude" / "skills" / "governance-model-builder.md"
        content = spec_path.read_text(encoding="utf-8-sig")
        assert (
            "No Tier 2B exemption source is currently cited in this Phase 6 artifact"
            in content
        )

    def test_violating_response_detectable_in_artifact(self, tmp_path: Path) -> None:
        """If Claude returns a violating phrase, verify it lands in the
        artifact so a downstream compliance-check would catch it.
        This test proves the problem is in the production path, not the checker."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-gender-violation-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_gender_violation(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        stmt = artifact["ethics_assessment"]["self_assessment_statement"]

        # The violating phrase is present in the artifact
        assert "this call does not exempt the topic" in stmt

        # AND no Tier 2B source is in the traceability_footer
        sources = artifact.get("traceability_footer", {}).get("primary_sources", [])
        tier2b_sources = [
            s for s in sources
            if s.get("source_path", "").startswith("docs/tier2b_topic_and_call_sources/extracted/")
        ]
        assert len(tier2b_sources) == 0, (
            "Test fixture should have no Tier 2B source to demonstrate the violation"
        )

    def test_safe_wording_has_no_violating_phrase(self, tmp_path: Path) -> None:
        """An artifact produced with the safe wording must not contain any
        of the known violating phrases."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-gender-safe-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_safe_gender_wording(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        stmt = artifact["ethics_assessment"]["self_assessment_statement"].lower()

        for phrase in _VIOLATING_PHRASES:
            assert phrase not in stmt, (
                f"Safe wording still contains violating phrase: {phrase!r}"
            )

    def test_safe_wording_contains_tier2b_deferral(self, tmp_path: Path) -> None:
        """The safe wording must contain the Tier 2B deferral language."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-gender-deferral-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_safe_gender_wording(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        stmt = artifact["ethics_assessment"]["self_assessment_statement"]

        assert "No Tier 2B exemption source" in stmt
        assert "Phase 8 drafting" in stmt

    def test_tier2b_backed_assertion_is_permitted(self, tmp_path: Path) -> None:
        """When a Tier 2B source IS present in the traceability footer,
        a call-specific assertion is valid (no violation)."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-gender-tier2b-backed-01"
        with patch(_TRANSPORT_TARGET, return_value=_gov_response_with_tier2b_backed_assertion(run_id)):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        # Tier 2B source is present in traceability_footer
        sources = artifact.get("traceability_footer", {}).get("primary_sources", [])
        tier2b_sources = [
            s for s in sources
            if s.get("source_path", "").startswith("docs/tier2b_topic_and_call_sources/extracted/")
        ]
        assert len(tier2b_sources) >= 1, (
            "Tier 2B-backed assertion must have a Tier 2B source in traceability_footer"
        )

    def test_current_artifact_uses_safe_wording(self) -> None:
        """The actual implementation_architecture.json in the repo must use
        the safe wording (regression guard for the production artifact)."""
        artifact_path = (
            _REPO_ROOT / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        stmt = artifact["ethics_assessment"]["self_assessment_statement"].lower()

        for phrase in _VIOLATING_PHRASES:
            assert phrase not in stmt, (
                f"Production artifact still contains violating phrase: {phrase!r}"
            )

        # Must contain the safe deferral language
        assert "no tier 2b exemption source" in stmt


# ===========================================================================
# H. Compliance-profile derivative labeling tests (§13.2 traceability-chain)
# ===========================================================================


class TestComplianceProfileDerivativeLabeling:
    """Regression tests for §13.2: governance-model-builder must not emit
    call-specific mandate claims sourced only to compliance_profile.json
    without Tier 2B traceability or derivative labeling."""

    def test_skill_spec_contains_constraint_4(self) -> None:
        """governance-model-builder.md must declare Constraint 4 for
        compliance-profile derivative labeling."""
        spec_path = _REPO_ROOT / ".claude" / "skills" / "governance-model-builder.md"
        content = spec_path.read_text(encoding="utf-8-sig")
        assert "Constraint 4" in content
        assert "compliance_profile.json require Tier 2B traceability or derivative labeling" in content

    def test_skill_spec_contains_step_2_7_2(self) -> None:
        """governance-model-builder.md must contain Step 2.7.2 derivative
        labeling constraint."""
        spec_path = _REPO_ROOT / ".claude" / "skills" / "governance-model-builder.md"
        content = spec_path.read_text(encoding="utf-8-sig")
        assert "Step 2.7.2" in content
        assert "Compliance-profile derivative labeling constraint" in content

    def test_skill_catalog_has_constraint_5(self) -> None:
        """skill_catalog.yaml must declare the §13.2 constraint for
        governance-model-builder."""
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        constraints = entry.get("constitutional_constraints", [])
        assert any(
            "compliance_profile.json" in c and "13.2" in c
            for c in constraints
        ), f"No §13.2 compliance_profile constraint found in: {constraints}"

    def test_reads_from_includes_tier2b_scope_requirements(self) -> None:
        """governance-model-builder must declare Tier 2B scope_requirements.json
        in reads_from."""
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json" in reads

    def test_reads_from_includes_tier2b_call_constraints(self) -> None:
        """governance-model-builder must declare Tier 2B call_constraints.json
        in reads_from."""
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json" in reads

    def test_current_artifact_has_tier2b_in_traceability_footer(self) -> None:
        """The production artifact must have at least one Tier 2B entry in
        traceability_footer.primary_sources[] with a path starting with
        docs/tier2b_topic_and_call_sources/extracted/."""
        artifact_path = (
            _REPO_ROOT / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        sources = artifact.get("traceability_footer", {}).get("primary_sources", [])
        tier2b_sources = [
            s for s in sources
            if s.get("source_path", "").startswith(
                "docs/tier2b_topic_and_call_sources/extracted/"
            )
        ]
        assert len(tier2b_sources) >= 1, (
            "Production artifact traceability_footer has no Tier 2B source; "
            f"found sources: {[s.get('source_path') for s in sources]}"
        )

    def test_current_artifact_wp9_cites_tier2b_for_ai_on_demand(self) -> None:
        """WPL-WP9 source_basis must cite Tier 2B extracted source for the
        AI-on-demand platform requirement, not only compliance_profile.json."""
        artifact_path = (
            _REPO_ROOT / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        wp9_role = next(
            (r for r in artifact["management_roles"] if r["role_id"] == "WPL-WP9"),
            None,
        )
        assert wp9_role is not None, "WPL-WP9 not found in management_roles"
        sb = wp9_role["source_basis"]
        assert "docs/tier2b_topic_and_call_sources/extracted/" in sb, (
            f"WPL-WP9 source_basis does not cite Tier 2B: {sb}"
        )
        assert "scope_requirements.json" in sb or "call_constraints.json" in sb, (
            f"WPL-WP9 source_basis does not cite scope_requirements or call_constraints: {sb}"
        )

    def test_current_artifact_ethics_not_asserted_as_call_mandate(self) -> None:
        """ETH-01 through ETH-04 source_basis must NOT assert
        compliance_profile.json ethics_review_required as a confirmed
        call mandate without Tier 2B evidence."""
        artifact_path = (
            _REPO_ROOT / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        issues = artifact["ethics_assessment"]["issues"]

        # The violating pattern: bare "compliance_profile.json ethics_review_required: true."
        # presented as a call condition without derivative framing
        violating_pattern = "compliance_profile.json ethics_review_required: true."

        for issue in issues:
            sb = issue.get("source_basis", "")
            if violating_pattern in sb:
                # Check that it's properly framed as derivative
                assert "Tier 3" in sb or "compliance flag" in sb or "derived during call binding" in sb, (
                    f"{issue['issue_id']} source_basis asserts ethics_review_required "
                    f"as a call mandate without derivative labeling: {sb}"
                )

    def test_current_artifact_self_assessment_ethics_derivative(self) -> None:
        """self_assessment_statement must frame ethics_review_required as
        a Tier 3 derivative, not as a Tier 2B topic-specific mandate."""
        artifact_path = (
            _REPO_ROOT / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        stmt = artifact["ethics_assessment"]["self_assessment_statement"]

        # Must NOT have the old bare assertion pattern
        assert "compliance_profile.json ethics_review_required: true)" not in stmt, (
            "self_assessment_statement still contains bare ethics_review_required "
            "assertion without derivative framing"
        )

    def test_response_with_compliance_only_mandate_is_detectable(self, tmp_path: Path) -> None:
        """If Claude returns a response asserting a call mandate sourced only
        to compliance_profile.json, the artifact should contain the assertion
        so downstream compliance-check can detect it."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-compliance-mandate-01"
        # Response with ETH-01 asserting ethics as a call mandate from compliance_profile only
        response = json.dumps({
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": run_id,
            "governance_matrix": [
                {"body_name": "GA", "composition": ["P1"], "decision_scope": "All",
                 "meeting_frequency": "Annual", "escalation_path": "To coordinator"}
            ],
            "management_roles": [
                {"role_id": "COORD", "role_name": "Coordinator",
                 "assigned_to": "P1", "responsibilities": ["Manage"]}
            ],
            "risk_register": [],
            "ethics_assessment": {
                "ethics_issues_identified": True,
                "issues": [{
                    "issue_id": "ETH-01",
                    "category": "AI",
                    "description": "AI system ethics",
                    "relevant_wps": ["WP2"],
                    "source_basis": (
                        "compliance_profile.json ethics_review_required: true. "
                        "section_schema_registry.json A.4."
                    ),
                }],
                "self_assessment_statement": "Ethics required per compliance_profile.",
            },
            "instrument_sections_addressed": [
                {"section_id": "A.4", "section_name": "Ethics", "status": "addressed"}
            ],
            "traceability_footer": {
                "primary_sources": [
                    {"tier": 1, "source_path": "docs/tier1_normative_framework/extracted/implementation_constraints.json"},
                    {"tier": 3, "source_path": "docs/tier3_project_instantiation/call_binding/compliance_profile.json"},
                ],
            },
        })
        with patch(_TRANSPORT_TARGET, return_value=response):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        # Verify no Tier 2B source in footer (demonstrating the violation condition)
        sources = artifact.get("traceability_footer", {}).get("primary_sources", [])
        tier2b = [s for s in sources if s.get("source_path", "").startswith(
            "docs/tier2b_topic_and_call_sources/extracted/")]
        assert len(tier2b) == 0, "Test fixture should have no Tier 2B source"

        # The bare compliance_profile assertion IS present (compliance-check would catch this)
        eth01 = artifact["ethics_assessment"]["issues"][0]
        assert "compliance_profile.json ethics_review_required: true" in eth01["source_basis"]

    def test_response_with_tier2b_backed_open_science_is_valid(self, tmp_path: Path) -> None:
        """When AI-on-demand platform requirement cites Tier 2B, it must
        appear in both source_basis AND traceability_footer."""
        repo_root = _make_gov_env(tmp_path)
        run_id = "test-tier2b-open-science-01"
        response = json.dumps({
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": run_id,
            "governance_matrix": [
                {"body_name": "GA", "composition": ["P1"], "decision_scope": "All",
                 "meeting_frequency": "Annual", "escalation_path": "To coordinator"}
            ],
            "management_roles": [
                {"role_id": "WPL-WP9", "role_name": "WP9 Lead",
                 "assigned_to": "P1", "responsibilities": ["Dissemination"],
                 "source_basis": (
                     "AI-on-demand platform requirement confirmed in "
                     "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json "
                     "(SR-10)."
                 )}
            ],
            "risk_register": [],
            "ethics_assessment": {
                "ethics_issues_identified": False,
                "issues": [],
                "self_assessment_statement": "No issues.",
            },
            "instrument_sections_addressed": [
                {"section_id": "B.2.2", "section_name": "Dissemination", "status": "addressed"}
            ],
            "traceability_footer": {
                "primary_sources": [
                    {"tier": 1, "source_path": "docs/tier1_normative_framework/extracted/governance_principles.json"},
                    {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
                     "relevant_fields": ["requirements[9] (SR-10)"]},
                ],
            },
        })
        with patch(_TRANSPORT_TARGET, return_value=response):
            result = run_skill("governance-model-builder", run_id, repo_root)
        assert result.status == "success"

        artifact_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture" / "implementation_architecture.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        # Tier 2B source present in footer
        sources = artifact["traceability_footer"]["primary_sources"]
        tier2b = [s for s in sources if s.get("source_path", "").startswith(
            "docs/tier2b_topic_and_call_sources/extracted/")]
        assert len(tier2b) >= 1

        # WP9 source_basis cites Tier 2B
        wp9 = artifact["management_roles"][0]
        assert "scope_requirements.json" in wp9.get("source_basis", "")
