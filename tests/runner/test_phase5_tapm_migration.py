"""
Tests for Phase 5 TAPM migration — transport remediation via skill decomposition.

Originally tested impact-pathway-mapper TAPM migration. Updated to reflect the
decomposition into impact-pathway-core-builder + impact-dec-enricher, and the
subsequent TAPM migration of dissemination-exploitation-communication-check.

Verifies that:
  - Phase 5 producing skills run in TAPM mode
  - TAPM prompts use declared tools (Read, Glob) rather than serialized content
  - Phase 5 artifact production path still targets the canonical file
  - Downstream DEC check depends on the produced artifact directory
  - dissemination-exploitation-communication-check runs in TAPM mode
  - DEC check TAPM prompt is bounded (no 234K serialized prompt)
  - Rollback is a config change

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


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear skill_runtime caches before each test."""
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    yield
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


# ---------------------------------------------------------------------------
# Test 1: Phase 5 producing skills are configured for TAPM mode
# ---------------------------------------------------------------------------


class TestPhase5TapmConfig:
    """Verify the skill catalog declares TAPM mode for Phase 5 producing skills."""

    def test_core_builder_is_tapm(self) -> None:
        entry = _get_skill_entry("impact-pathway-core-builder", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_dec_enricher_is_tapm(self) -> None:
        entry = _get_skill_entry("impact-dec-enricher", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_core_builder_reads_from_paths_present(self) -> None:
        entry = _get_skill_entry("impact-pathway-core-builder", _REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        assert len(reads_from) == 5

    def test_core_builder_writes_to_phase5_directory(self) -> None:
        entry = _get_skill_entry("impact-pathway-core-builder", _REPO_ROOT)
        writes_to = entry.get("writes_to", [])
        assert any("phase5_impact_architecture" in w for w in writes_to)


# ---------------------------------------------------------------------------
# Test 2: TAPM prompt assembly for core builder
# ---------------------------------------------------------------------------


class TestCoreBuilderTapmPrompt:
    """Verify TAPM prompt properties for impact-pathway-core-builder."""

    def _assemble_prompt(self) -> tuple[str, str]:
        entry = _get_skill_entry("impact-pathway-core-builder", _REPO_ROOT)
        skill_spec = _load_skill_spec("impact-pathway-core-builder", _REPO_ROOT)
        return _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="impact-pathway-core-builder",
            run_id="test-run-001",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
            node_id="n05_impact_architecture",
        )

    def test_prompt_size_under_50kb(self) -> None:
        sys_p, usr_p = self._assemble_prompt()
        total = len(sys_p) + len(usr_p)
        assert total < 50_000, (
            f"TAPM prompt total size is {total} chars; must be under 50KB"
        )

    def test_system_prompt_under_24kb(self) -> None:
        sys_p, _ = self._assemble_prompt()
        assert len(sys_p) < 24_000

    def test_user_prompt_contains_skill_spec(self) -> None:
        _, usr_p = self._assemble_prompt()
        assert "impact-pathway-core-builder" in usr_p
        assert "impact_architecture.json" in usr_p

    def test_user_prompt_contains_declared_input_paths(self) -> None:
        _, usr_p = self._assemble_prompt()
        assert "outcomes.json" in usr_p
        assert "impacts.json" in usr_p
        assert "expected_outcomes.json" in usr_p
        assert "expected_impacts.json" in usr_p
        assert "phase3_wp_design" in usr_p

    def test_user_prompt_does_not_serialize_file_contents(self) -> None:
        """Critical TAPM invariant: resolved input file contents must not be in prompt.

        The skill spec itself may contain JSON code fences as examples — that's
        expected. What must NOT appear is serialized content from the declared
        reads_from files (e.g. actual wp_structure.json content with WP arrays).
        """
        _, usr_p = self._assemble_prompt()
        # The TAPM prompt should not contain a "## Canonical Inputs" section
        # with serialized JSON blocks (the cli-prompt pattern).
        assert "# Canonical Inputs\n\n## docs/" not in usr_p

    def test_prompt_contains_tools_instruction(self) -> None:
        sys_p, _ = self._assemble_prompt()
        assert "Read" in sys_p
        assert "Glob" in sys_p
        assert "Do not read files outside" in sys_p

    def test_prompt_contains_node_id(self) -> None:
        _, usr_p = self._assemble_prompt()
        assert "n05_impact_architecture" in usr_p

    def test_prompt_contains_schema_hints(self) -> None:
        _, usr_p = self._assemble_prompt()
        assert "orch.phase5.impact_architecture.v1" in usr_p


# ---------------------------------------------------------------------------
# Test 3: Phase 5 artifact production path via core builder
# ---------------------------------------------------------------------------


class TestPhase5ArtifactProductionPath:
    """Verify that TAPM mode produces the canonical Phase 5 artifact."""

    def _make_phase5_env(self, tmp_path: Path) -> Path:
        repo_root = tmp_path
        for rel in [
            ".claude/workflows/system_orchestration/skill_catalog.yaml",
            ".claude/workflows/system_orchestration/artifact_schema_specification.yaml",
        ]:
            src = _REPO_ROOT / rel
            dst = repo_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")
        src_spec = _REPO_ROOT / ".claude" / "skills" / "impact-pathway-core-builder.md"
        dst_spec = repo_root / ".claude" / "skills" / "impact-pathway-core-builder.md"
        dst_spec.parent.mkdir(parents=True, exist_ok=True)
        dst_spec.write_text(src_spec.read_text(encoding="utf-8-sig"), encoding="utf-8")
        (repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs").mkdir(
            parents=True, exist_ok=True
        )
        return repo_root

    def _valid_response(self, run_id: str) -> str:
        return json.dumps({
            "schema_id": "orch.phase5.impact_architecture.v1",
            "run_id": run_id,
            "impact_pathways": [{"pathway_id": "PWY-1", "expected_impact_id": "EI-01", "project_outputs": ["D1-01"], "outcomes": [], "impact_narrative": "test narrative for WP1", "tier2b_source_ref": "test"}],
            "kpis": [{"kpi_id": "KPI-01", "description": "test", "target": "1", "measurement_method": "test", "traceable_to_deliverable": "D1-01"}],
            "dissemination_plan": None,
            "exploitation_plan": None,
            "sustainability_mechanism": None,
        })

    def test_tapm_invocation_passes_tools(self, tmp_path: Path) -> None:
        repo_root = self._make_phase5_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_response("r1")) as mock:
            result = run_skill("impact-pathway-core-builder", "r1", repo_root, node_id="n05_impact_architecture")
        assert result.status == "success"
        assert mock.call_args.kwargs.get("tools") == ["Read", "Glob"]

    def test_canonical_artifact_written(self, tmp_path: Path) -> None:
        repo_root = self._make_phase5_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_response("r2")):
            result = run_skill("impact-pathway-core-builder", "r2", repo_root)
        assert result.status == "success"
        canonical = repo_root / "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json"
        assert canonical.exists()
        content = json.loads(canonical.read_text(encoding="utf-8"))
        assert content["schema_id"] == "orch.phase5.impact_architecture.v1"

    def test_tapm_timeout_uses_1200s(self, tmp_path: Path) -> None:
        repo_root = self._make_phase5_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_response("r3")) as mock:
            run_skill("impact-pathway-core-builder", "r3", repo_root)
        assert mock.call_args.kwargs.get("timeout_seconds") == 1200


# ---------------------------------------------------------------------------
# Test 4: DEC check dependency on impact_architecture directory
# ---------------------------------------------------------------------------


class TestDecCheckDependency:
    def test_dec_check_reads_from_phase5_directory(self) -> None:
        entry = _get_skill_entry("dissemination-exploitation-communication-check", _REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        assert any("phase5_impact_architecture" in r for r in reads_from)

    def test_dec_check_is_tapm(self) -> None:
        """DEC check migrated to TAPM after 234K cli-prompt timeout (run c3066a3c)."""
        entry = _get_skill_entry("dissemination-exploitation-communication-check", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"


# ---------------------------------------------------------------------------
# Test 5: No regression to other Phase 5 cli-prompt skills
# ---------------------------------------------------------------------------


class TestPhase5OtherSkillsUnchanged:
    def test_gate_enforcement_remains_tapm(self) -> None:
        entry = _get_skill_entry("gate-enforcement", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_proposal_section_traceability_check_is_tapm(self) -> None:
        entry = _get_skill_entry("proposal-section-traceability-check", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"


# ---------------------------------------------------------------------------
# Test 6: Skill specs have TAPM input boundary instructions
# ---------------------------------------------------------------------------


class TestSkillSpecTapmInstructions:
    def test_core_builder_spec_contains_tapm_section(self) -> None:
        spec = _load_skill_spec("impact-pathway-core-builder", _REPO_ROOT)
        assert "Input Access (TAPM Mode)" in spec

    def test_core_builder_spec_lists_declared_input_files(self) -> None:
        spec = _load_skill_spec("impact-pathway-core-builder", _REPO_ROOT)
        assert "outcomes.json" in spec
        assert "impacts.json" in spec
        assert "expected_outcomes.json" in spec
        assert "expected_impacts.json" in spec
        assert "wp_structure.json" in spec

    def test_core_builder_spec_has_boundary_constraints(self) -> None:
        spec = _load_skill_spec("impact-pathway-core-builder", _REPO_ROOT)
        assert "Do not read files outside" in spec

    def test_dec_check_spec_contains_tapm_section(self) -> None:
        spec = _load_skill_spec("dissemination-exploitation-communication-check", _REPO_ROOT)
        assert "Input Access (TAPM Mode)" in spec

    def test_dec_check_spec_lists_declared_input_files(self) -> None:
        spec = _load_skill_spec("dissemination-exploitation-communication-check", _REPO_ROOT)
        assert "impact_architecture.json" in spec
        assert "section_schema_registry.json" in spec
        assert "expected_impacts.json" in spec

    def test_dec_check_spec_has_boundary_constraints(self) -> None:
        spec = _load_skill_spec("dissemination-exploitation-communication-check", _REPO_ROOT)
        assert "Do not read files outside" in spec


# ---------------------------------------------------------------------------
# Test 7: DEC check TAPM prompt assembly — bounded prompt, no serialized bulk
# ---------------------------------------------------------------------------


class TestDecCheckTapmPrompt:
    """Verify TAPM prompt properties for dissemination-exploitation-communication-check.

    This is the surgical fix for the 234K cli-prompt timeout (run c3066a3c).
    The TAPM prompt must be bounded (<50KB) and must NOT serialize the full
    impact_architecture.json into the prompt.
    """

    def _assemble_prompt(self) -> tuple[str, str]:
        entry = _get_skill_entry("dissemination-exploitation-communication-check", _REPO_ROOT)
        skill_spec = _load_skill_spec("dissemination-exploitation-communication-check", _REPO_ROOT)
        return _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="dissemination-exploitation-communication-check",
            run_id="test-run-dec",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
            node_id="n05_impact_architecture",
        )

    def test_prompt_size_under_50kb(self) -> None:
        """Critical: prompt must be <50KB to avoid the 234K timeout."""
        sys_p, usr_p = self._assemble_prompt()
        total = len(sys_p) + len(usr_p)
        assert total < 50_000, (
            f"DEC check TAPM prompt is {total} chars; must be under 50KB "
            f"(was 234K in cli-prompt mode causing 300s timeout)"
        )

    def test_system_prompt_under_24kb(self) -> None:
        sys_p, _ = self._assemble_prompt()
        assert len(sys_p) < 24_000

    def test_user_prompt_contains_declared_input_paths(self) -> None:
        _, usr_p = self._assemble_prompt()
        assert "impact_architecture.json" in usr_p
        assert "section_schema_registry.json" in usr_p
        assert "expected_impacts.json" in usr_p

    def test_user_prompt_does_not_serialize_file_contents(self) -> None:
        """Critical TAPM invariant: input contents must not be in prompt."""
        _, usr_p = self._assemble_prompt()
        # cli-prompt mode serializes inputs under "# Canonical Inputs"
        assert "# Canonical Inputs\n\n## docs/" not in usr_p

    def test_prompt_contains_tools_instruction(self) -> None:
        sys_p, _ = self._assemble_prompt()
        assert "Read" in sys_p
        assert "Glob" in sys_p
        assert "Do not read files outside" in sys_p

    def test_prompt_contains_node_id(self) -> None:
        _, usr_p = self._assemble_prompt()
        assert "n05_impact_architecture" in usr_p

    def test_no_run_id_or_schema_id_required(self) -> None:
        """DEC check writes validation reports — no schema_id or run_id needed."""
        sys_p, _ = self._assemble_prompt()
        assert "Do NOT include run_id, schema_id" in sys_p


# ---------------------------------------------------------------------------
# Test 8: DEC check TAPM invocation path
# ---------------------------------------------------------------------------


class TestDecCheckTapmInvocation:
    """Verify DEC check runs in TAPM mode with tools and 600s timeout."""

    def _make_dec_env(self, tmp_path: Path) -> Path:
        """Create a minimal environment for DEC check invocation."""
        repo_root = tmp_path
        for rel in [
            ".claude/workflows/system_orchestration/skill_catalog.yaml",
            ".claude/workflows/system_orchestration/artifact_schema_specification.yaml",
        ]:
            src = _REPO_ROOT / rel
            dst = repo_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")
        src_spec = _REPO_ROOT / ".claude" / "skills" / "dissemination-exploitation-communication-check.md"
        dst_spec = repo_root / ".claude" / "skills" / "dissemination-exploitation-communication-check.md"
        dst_spec.parent.mkdir(parents=True, exist_ok=True)
        dst_spec.write_text(src_spec.read_text(encoding="utf-8-sig"), encoding="utf-8")
        # Create the validation_reports directory (writes_to target)
        (repo_root / "docs" / "tier4_orchestration_state" / "validation_reports").mkdir(
            parents=True, exist_ok=True
        )
        return repo_root

    def _valid_dec_response(self) -> str:
        return json.dumps({
            "report_id": "dec_check_test_2026-04-22T00_00_00Z",
            "skill_id": "dissemination-exploitation-communication-check",
            "invoking_agent": "impact_architect",
            "run_id_reference": "test-dec-run",
            "dec_findings": [
                {
                    "plan_type": "dissemination",
                    "finding_id": "F-001",
                    "check_description": "target_audience specificity",
                    "status": "pass",
                    "flag_reason": None,
                    "instrument_section_ref": None,
                    "tier2b_source_ref": None,
                }
            ],
            "summary": {"total_checks": 1, "passed": 1, "flagged": 0},
            "timestamp": "2026-04-22T00:00:00Z",
        })

    def test_tapm_invocation_passes_tools(self, tmp_path: Path) -> None:
        repo_root = self._make_dec_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_dec_response()) as mock:
            result = run_skill(
                "dissemination-exploitation-communication-check",
                "test-dec-run", repo_root,
                node_id="n05_impact_architecture",
            )
        assert result.status == "success"
        assert mock.call_args.kwargs.get("tools") == ["Read", "Glob"]

    def test_tapm_timeout_uses_1200s(self, tmp_path: Path) -> None:
        repo_root = self._make_dec_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_dec_response()) as mock:
            run_skill(
                "dissemination-exploitation-communication-check",
                "test-dec-run", repo_root,
            )
        assert mock.call_args.kwargs.get("timeout_seconds") == 1200

    def test_validation_report_written(self, tmp_path: Path) -> None:
        """DEC check output goes to validation_reports/ not phase5 directory."""
        repo_root = self._make_dec_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_dec_response()):
            result = run_skill(
                "dissemination-exploitation-communication-check",
                "test-dec-run", repo_root,
            )
        assert result.status == "success"
        assert len(result.outputs_written) == 1
        assert "validation_reports" in result.outputs_written[0]

    def test_no_input_serialization_in_prompt(self, tmp_path: Path) -> None:
        """Verify the prompt piped to Claude does NOT contain serialized inputs."""
        repo_root = self._make_dec_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_dec_response()) as mock:
            run_skill(
                "dissemination-exploitation-communication-check",
                "test-dec-run", repo_root,
            )
        # The user_prompt is the second positional arg or 'user_prompt' kwarg
        call_kwargs = mock.call_args.kwargs
        user_prompt = call_kwargs.get("user_prompt", "")
        # Must NOT contain the cli-prompt serialized inputs pattern
        assert "# Canonical Inputs\n\n## docs/" not in user_prompt
        # Prompt must be well under the 234K threshold
        assert len(user_prompt) < 50_000
