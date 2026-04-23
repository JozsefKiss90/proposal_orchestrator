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
    """Verify Tier 5 is optional_reads_from, not reads_from."""

    def test_tier5_not_in_reads_from(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier5_deliverables/" not in reads

    def test_tier5_in_optional_reads_from(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        optional = entry.get("optional_reads_from", [])
        assert "docs/tier5_deliverables/" in optional

    def test_tier4_still_required(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier4_orchestration_state/phase_outputs/" in reads


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
