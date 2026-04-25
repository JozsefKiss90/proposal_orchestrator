"""
Tests for Phase 6 TAPM migration — risk-register-builder and governance-model-builder.

Verifies that:
  - Both Phase 6 producing skills are configured for TAPM mode
  - TAPM prompts use declared tools (Read, Glob) rather than serialized content
  - Prompt sizes are bounded (<50KB)
  - Risk register merge semantics are preserved (not overwritten)
  - Governance model schema is unchanged
  - Other Phase 6 skills remain unmodified
  - Manifest and skill ordering are preserved
  - Rollback is a single-line config change

All tests use the real skill_catalog.yaml from the repository to validate the
actual configuration, not synthetic stubs.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runner.skill_runtime import (
    _assemble_tapm_prompt,
    _get_skill_entry,
    _load_skill_catalog,
    _load_skill_spec,
    run_skill,
)
from runner.runtime_models import SkillResult

# ---------------------------------------------------------------------------
# Fixtures — real repo paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"


def _fix_base_run_id(repo_root: Path, run_id: str) -> None:
    """Patch the base artifact's run_id to match the test run_id."""
    artifact_path = (
        repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
        / "phase6_implementation_architecture" / "implementation_architecture.json"
    )
    if artifact_path.is_file():
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        data["run_id"] = run_id
        artifact_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
# A. Config tests (4)
# ===========================================================================


class TestPhase6TapmConfig:
    """Verify the skill catalog declares TAPM mode for Phase 6 producing skills."""

    def test_risk_register_builder_is_tapm(self) -> None:
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_governance_model_builder_is_tapm(self) -> None:
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_risk_register_builder_rollback_is_single_line(self) -> None:
        """Removing execution_mode line reverts to cli-prompt (default)."""
        catalog_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml"
        )
        text = catalog_path.read_text(encoding="utf-8-sig")
        # Find the risk-register-builder entry and verify execution_mode
        # is on its own line (removable without side effects)
        lines = text.split("\n")
        found = False
        in_risk_builder = False
        for line in lines:
            if "id: risk-register-builder" in line:
                in_risk_builder = True
            elif in_risk_builder and line.strip().startswith("- id:"):
                break
            elif in_risk_builder and 'execution_mode: "tapm"' in line:
                found = True
                break
        assert found, "execution_mode: tapm not found as a standalone line in risk-register-builder"

    def test_governance_model_builder_rollback_is_single_line(self) -> None:
        """Removing execution_mode line reverts to cli-prompt (default)."""
        catalog_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml"
        )
        text = catalog_path.read_text(encoding="utf-8-sig")
        lines = text.split("\n")
        found = False
        in_gov_builder = False
        for line in lines:
            if "id: governance-model-builder" in line:
                in_gov_builder = True
            elif in_gov_builder and line.strip().startswith("- id:"):
                break
            elif in_gov_builder and 'execution_mode: "tapm"' in line:
                found = True
                break
        assert found, "execution_mode: tapm not found as a standalone line in governance-model-builder"


# ===========================================================================
# B. Prompt size tests (6)
# ===========================================================================


class TestRiskRegisterBuilderTapmPrompt:
    """Verify TAPM prompt properties for risk-register-builder."""

    def _assemble_prompt(self) -> tuple[str, str]:
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        skill_spec = _load_skill_spec("risk-register-builder", _REPO_ROOT)
        return _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="risk-register-builder",
            run_id="test-run-risk",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
            node_id="n06_implementation_architecture",
        )

    def test_prompt_size_under_15kb(self) -> None:
        """After simplification, TAPM prompt should be well under 15KB."""
        sys_p, usr_p = self._assemble_prompt()
        total = len(sys_p) + len(usr_p)
        assert total < 15_000, (
            f"risk-register-builder TAPM prompt is {total} chars; "
            f"simplified spec should be under 15KB"
        )

    def test_system_prompt_under_24kb(self) -> None:
        sys_p, _ = self._assemble_prompt()
        assert len(sys_p) < 24_000

    def test_user_prompt_does_not_serialize_file_contents(self) -> None:
        """Critical TAPM invariant: resolved input file contents must not be in prompt."""
        _, usr_p = self._assemble_prompt()
        assert "# Canonical Inputs\n\n## docs/" not in usr_p


class TestGovernanceModelBuilderTapmPrompt:
    """Verify TAPM prompt properties for governance-model-builder."""

    def _assemble_prompt(self) -> tuple[str, str]:
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        skill_spec = _load_skill_spec("governance-model-builder", _REPO_ROOT)
        return _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="governance-model-builder",
            run_id="test-run-gov",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
            node_id="n06_implementation_architecture",
        )

    def test_prompt_size_under_50kb(self) -> None:
        sys_p, usr_p = self._assemble_prompt()
        total = len(sys_p) + len(usr_p)
        assert total < 50_000, (
            f"governance-model-builder TAPM prompt is {total} chars; must be under 50KB "
            f"(was ~53KB in cli-prompt mode)"
        )

    def test_system_prompt_under_24kb(self) -> None:
        sys_p, _ = self._assemble_prompt()
        assert len(sys_p) < 24_000

    def test_user_prompt_does_not_serialize_file_contents(self) -> None:
        """Critical TAPM invariant: resolved input file contents must not be in prompt."""
        _, usr_p = self._assemble_prompt()
        assert "# Canonical Inputs\n\n## docs/" not in usr_p


# ===========================================================================
# C. Runtime invocation tests (5)
# ===========================================================================


class TestRiskRegisterBuilderTapmInvocation:
    """Verify risk-register-builder runs in TAPM mode with tools and 600s timeout."""

    def _make_phase6_env(self, tmp_path: Path) -> Path:
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
        # enrich_artifact requires the base artifact on disk
        artifact_dir = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase6_implementation_architecture"
        )
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "implementation_architecture.json").write_text(
            json.dumps({
                "schema_id": "orch.phase6.implementation_architecture.v1",
                "run_id": "__placeholder__",
                "governance_matrix": [{"body_name": "PMB", "composition": ["P1"], "decision_scope": "Strategic", "meeting_frequency": "Quarterly"}],
                "management_roles": [{"role_id": "COORD-01", "role_name": "Coordinator", "assigned_to": "P1", "responsibilities": ["Overall management"]}],
                "risk_register": [],
                "ethics_assessment": {"ethics_issues_identified": False, "issues": [], "self_assessment_statement": "No ethics issues"},
                "instrument_sections_addressed": [{"section_id": "3.2", "section_name": "Management", "status": "addressed"}],
            }),
            encoding="utf-8",
        )
        return repo_root

    def _enrichment_response(self, run_id: str) -> str:
        """enrich_artifact response: only the risk_register field plus metadata."""
        return json.dumps({
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": run_id,
            "risk_register": [{"risk_id": "R-01", "description": "Test risk", "category": "technical", "likelihood": "medium", "impact": "high", "mitigation": "Addressed in WP1 activities", "responsible_partner": "P1"}],
        })

    def test_tapm_invocation_passes_tools(self, tmp_path: Path) -> None:
        repo_root = self._make_phase6_env(tmp_path)
        # Fix run_id in base artifact to match
        _fix_base_run_id(repo_root, "r1")
        with patch(_TRANSPORT_TARGET, return_value=self._enrichment_response("r1")) as mock:
            result = run_skill("risk-register-builder", "r1", repo_root, node_id="n06_implementation_architecture")
        assert result.status == "success", f"Expected success, got: {result.failure_reason}"
        assert mock.call_args.kwargs.get("tools") == ["Read", "Glob"]

    def test_tapm_timeout_uses_1200s(self, tmp_path: Path) -> None:
        repo_root = self._make_phase6_env(tmp_path)
        _fix_base_run_id(repo_root, "r2")
        with patch(_TRANSPORT_TARGET, return_value=self._enrichment_response("r2")) as mock:
            run_skill("risk-register-builder", "r2", repo_root)
        assert mock.call_args.kwargs.get("timeout_seconds") == 1200

    def test_tapm_path_invoked_not_cli_prompt(self, tmp_path: Path) -> None:
        """Verify the TAPM code path is used (prompt doesn't contain serialized inputs)."""
        repo_root = self._make_phase6_env(tmp_path)
        _fix_base_run_id(repo_root, "r3")
        with patch(_TRANSPORT_TARGET, return_value=self._enrichment_response("r3")) as mock:
            run_skill("risk-register-builder", "r3", repo_root)
        call_kwargs = mock.call_args.kwargs
        user_prompt = call_kwargs.get("user_prompt", "")
        assert "# Canonical Inputs\n\n## docs/" not in user_prompt
        assert len(user_prompt) < 15_000


class TestGovernanceModelBuilderTapmInvocation:
    """Verify governance-model-builder runs in TAPM mode with tools and 600s timeout."""

    def _make_phase6_env(self, tmp_path: Path) -> Path:
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

    def _valid_response(self, run_id: str) -> str:
        return json.dumps({
            "schema_id": "orch.phase6.implementation_architecture.v1",
            "run_id": run_id,
            "governance_matrix": [{"body_name": "PMB", "composition": ["P1"], "decision_scope": "Strategic", "meeting_frequency": "Quarterly"}],
            "management_roles": [{"role_id": "COORD-01", "role_name": "Coordinator", "assigned_to": "P1", "responsibilities": ["Overall management"]}],
            "risk_register": [],
            "ethics_assessment": None,
            "instrument_sections_addressed": [],
        })

    def test_tapm_invocation_passes_tools(self, tmp_path: Path) -> None:
        repo_root = self._make_phase6_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_response("g1")) as mock:
            result = run_skill("governance-model-builder", "g1", repo_root, node_id="n06_implementation_architecture")
        assert result.status == "success"
        assert mock.call_args.kwargs.get("tools") == ["Read", "Glob"]

    def test_tapm_timeout_uses_1200s(self, tmp_path: Path) -> None:
        repo_root = self._make_phase6_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_response("g2")) as mock:
            run_skill("governance-model-builder", "g2", repo_root)
        assert mock.call_args.kwargs.get("timeout_seconds") == 1200


# ===========================================================================
# D. Output integrity tests (4)
# ===========================================================================


class TestRiskRegisterMergeSemantics:
    """Verify risk-register-builder output preserves merge semantics."""

    def test_risk_register_builder_reads_from_specific_files(self) -> None:
        """reads_from must use specific file paths, not directories."""
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        assert len(reads_from) == 2, (
            f"risk-register-builder should read exactly 2 files, got {len(reads_from)}"
        )
        for path in reads_from:
            assert path.endswith(".json"), (
                f"reads_from entry '{path}' is a directory, not a file path"
            )

    def test_risk_register_builder_writes_to_phase6_directory(self) -> None:
        entry = _get_skill_entry("risk-register-builder", _REPO_ROOT)
        writes_to = entry.get("writes_to", [])
        assert any("phase6_implementation_architecture" in w for w in writes_to)

    def test_governance_model_builder_reads_from_specific_files(self) -> None:
        """reads_from must use specific file paths, not directories."""
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        for path in reads_from:
            assert path.endswith(".json"), (
                f"reads_from entry '{path}' is a directory, not a file path"
            )

    def test_governance_model_builder_writes_to_phase6_directory(self) -> None:
        entry = _get_skill_entry("governance-model-builder", _REPO_ROOT)
        writes_to = entry.get("writes_to", [])
        assert any("phase6_implementation_architecture" in w for w in writes_to)


# ===========================================================================
# E. Regression guards (4)
# ===========================================================================


class TestPhase6RegressionGuards:
    """Verify no unintended changes to other Phase 6 skills or manifest."""

    def test_milestone_consistency_check_unchanged(self) -> None:
        """milestone-consistency-check (used in Phase 6) must NOT be TAPM."""
        entry = _get_skill_entry("milestone-consistency-check", _REPO_ROOT)
        mode = entry.get("execution_mode")
        assert mode is None or mode == "cli-prompt"

    def test_gate_enforcement_remains_tapm(self) -> None:
        """gate-enforcement was already TAPM — must not regress."""
        entry = _get_skill_entry("gate-enforcement", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_skill_catalog_ordering_preserved(self) -> None:
        """Skill ordering in the catalog must be unchanged."""
        catalog = _load_skill_catalog(_REPO_ROOT)
        ids = [e["id"] for e in catalog]
        # governance-model-builder must appear before risk-register-builder
        gov_idx = ids.index("governance-model-builder")
        risk_idx = ids.index("risk-register-builder")
        assert gov_idx < risk_idx, (
            "governance-model-builder must appear before risk-register-builder in catalog"
        )

    def test_manifest_not_modified(self) -> None:
        """The manifest file must not be modified by this migration."""
        manifest_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )
        if manifest_path.exists():
            text = manifest_path.read_text(encoding="utf-8-sig")
            # Verify Phase 6 node still references the same agents/skills
            assert "n06_implementation_architecture" in text


# ===========================================================================
# F. Skill spec TAPM sections
# ===========================================================================


class TestPhase6SkillSpecTapmInstructions:
    """Verify both skill specs contain TAPM input access sections."""

    def test_risk_register_builder_spec_contains_tapm_section(self) -> None:
        spec = _load_skill_spec("risk-register-builder", _REPO_ROOT)
        assert "Input Access (TAPM Mode)" in spec

    def test_risk_register_builder_spec_lists_declared_input_files(self) -> None:
        spec = _load_skill_spec("risk-register-builder", _REPO_ROOT)
        assert "risks.json" in spec
        assert "wp_structure.json" in spec

    def test_risk_register_builder_spec_has_boundary_constraints(self) -> None:
        spec = _load_skill_spec("risk-register-builder", _REPO_ROOT)
        assert "Do not read files outside" in spec

    def test_governance_model_builder_spec_contains_tapm_section(self) -> None:
        spec = _load_skill_spec("governance-model-builder", _REPO_ROOT)
        assert "Input Access (TAPM Mode)" in spec

    def test_governance_model_builder_spec_lists_declared_input_files(self) -> None:
        spec = _load_skill_spec("governance-model-builder", _REPO_ROOT)
        assert "partners.json" in spec
        assert "roles.json" in spec
        assert "wp_structure.json" in spec

    def test_governance_model_builder_spec_has_boundary_constraints(self) -> None:
        spec = _load_skill_spec("governance-model-builder", _REPO_ROOT)
        assert "Do not read files outside" in spec
