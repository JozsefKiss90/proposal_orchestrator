"""
Tests for Phase 5 TAPM migration — transport remediation via skill decomposition.

Originally tested impact-pathway-mapper TAPM migration. Updated to reflect the
decomposition into impact-pathway-core-builder + impact-dec-enricher.

Verifies that:
  - Phase 5 producing skills run in TAPM mode
  - TAPM prompts use declared tools (Read, Glob) rather than serialized content
  - Phase 5 artifact production path still targets the canonical file
  - Downstream DEC check still depends on the produced artifact directory
  - dissemination-exploitation-communication-check remains in cli-prompt mode
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

    def test_tapm_timeout_uses_600s(self, tmp_path: Path) -> None:
        repo_root = self._make_phase5_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._valid_response("r3")) as mock:
            run_skill("impact-pathway-core-builder", "r3", repo_root)
        assert mock.call_args.kwargs.get("timeout_seconds") == 600


# ---------------------------------------------------------------------------
# Test 4: DEC check dependency on impact_architecture directory
# ---------------------------------------------------------------------------


class TestDecCheckDependency:
    def test_dec_check_reads_from_phase5_directory(self) -> None:
        entry = _get_skill_entry("dissemination-exploitation-communication-check", _REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        assert any("phase5_impact_architecture" in r for r in reads_from)

    def test_dec_check_remains_cli_prompt(self) -> None:
        entry = _get_skill_entry("dissemination-exploitation-communication-check", _REPO_ROOT)
        mode = entry.get("execution_mode", "cli-prompt")
        assert mode == "cli-prompt"


# ---------------------------------------------------------------------------
# Test 5: No regression to other Phase 5 cli-prompt skills
# ---------------------------------------------------------------------------


class TestPhase5CliPromptSkillsUnchanged:
    def test_dec_check_no_execution_mode_set(self) -> None:
        entry = _get_skill_entry("dissemination-exploitation-communication-check", _REPO_ROOT)
        assert entry.get("execution_mode") is None or entry.get("execution_mode") == "cli-prompt"

    def test_gate_enforcement_remains_tapm(self) -> None:
        entry = _get_skill_entry("gate-enforcement", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_proposal_section_traceability_check_unchanged(self) -> None:
        entry = _get_skill_entry("proposal-section-traceability-check", _REPO_ROOT)
        mode = entry.get("execution_mode")
        assert mode is None or mode == "cli-prompt"


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
