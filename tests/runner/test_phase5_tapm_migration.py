"""
Tests for Phase 5 TAPM migration — impact-pathway-mapper transport remediation.

Verifies that:
  - impact-pathway-mapper runs in TAPM mode (execution_mode: "tapm")
  - TAPM prompt uses declared tools (Read, Glob) rather than serialized content
  - Phase 5 artifact production path still targets the canonical file
  - Downstream DEC check still depends on the produced artifact directory
  - dissemination-exploitation-communication-check remains in cli-prompt mode
  - Rollback is a one-line config change

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
# Test 1: impact-pathway-mapper is configured for TAPM mode
# ---------------------------------------------------------------------------


class TestImpactPathwayMapperTapmConfig:
    """Verify the skill catalog declares TAPM mode for impact-pathway-mapper."""

    def test_execution_mode_is_tapm(self) -> None:
        """impact-pathway-mapper must have execution_mode: 'tapm'."""
        entry = _get_skill_entry("impact-pathway-mapper", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm", (
            "impact-pathway-mapper must be set to TAPM mode in skill_catalog.yaml; "
            f"found execution_mode={entry.get('execution_mode')!r}"
        )

    def test_reads_from_paths_present(self) -> None:
        """The skill declares its canonical input paths."""
        entry = _get_skill_entry("impact-pathway-mapper", _REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        assert len(reads_from) == 5, (
            f"impact-pathway-mapper should have 5 reads_from entries; "
            f"found {len(reads_from)}"
        )

    def test_writes_to_phase5_directory(self) -> None:
        """The skill writes to the canonical Phase 5 output directory."""
        entry = _get_skill_entry("impact-pathway-mapper", _REPO_ROOT)
        writes_to = entry.get("writes_to", [])
        assert any(
            "phase5_impact_architecture" in w for w in writes_to
        ), f"writes_to must target phase5_impact_architecture/; found {writes_to}"

    def test_rollback_is_single_field_change(self) -> None:
        """Verify rollback simplicity: only execution_mode needs to change."""
        entry = _get_skill_entry("impact-pathway-mapper", _REPO_ROOT)
        # The only field that changes for TAPM migration is execution_mode.
        # All other fields (reads_from, writes_to, constraints) are unchanged.
        assert "reads_from" in entry
        assert "writes_to" in entry
        assert "constitutional_constraints" in entry
        # Rollback: set execution_mode back to "cli-prompt" or remove it.
        assert entry.get("execution_mode") == "tapm"


# ---------------------------------------------------------------------------
# Test 2: TAPM prompt assembly for impact-pathway-mapper
# ---------------------------------------------------------------------------


class TestImpactPathwayMapperTapmPrompt:
    """Verify TAPM prompt properties for impact-pathway-mapper."""

    def _assemble_prompt(self) -> tuple[str, str]:
        """Helper to build the TAPM prompt from the real skill spec."""
        entry = _get_skill_entry("impact-pathway-mapper", _REPO_ROOT)
        skill_spec = _load_skill_spec("impact-pathway-mapper", _REPO_ROOT)
        return _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="impact-pathway-mapper",
            run_id="test-run-001",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
            node_id="n05_impact_architecture",
        )

    def test_prompt_size_under_50kb(self) -> None:
        """TAPM prompt must be dramatically smaller than cli-prompt (139KB)."""
        sys_p, usr_p = self._assemble_prompt()
        total = len(sys_p) + len(usr_p)
        assert total < 50_000, (
            f"TAPM prompt total size is {total} chars; "
            f"must be under 50KB (cli-prompt was 139KB)"
        )

    def test_system_prompt_under_24kb(self) -> None:
        """System prompt must fit in the CLI --system-prompt arg."""
        sys_p, _ = self._assemble_prompt()
        assert len(sys_p) < 24_000

    def test_user_prompt_contains_skill_spec(self) -> None:
        """The skill spec text must appear in the user prompt."""
        _, usr_p = self._assemble_prompt()
        assert "impact-pathway-mapper" in usr_p
        assert "impact_architecture.json" in usr_p

    def test_user_prompt_contains_declared_input_paths(self) -> None:
        """Declared reads_from paths must appear in the user prompt."""
        _, usr_p = self._assemble_prompt()
        assert "outcomes.json" in usr_p
        assert "impacts.json" in usr_p
        assert "expected_outcomes.json" in usr_p
        assert "expected_impacts.json" in usr_p
        assert "phase3_wp_design" in usr_p

    def test_user_prompt_does_not_serialize_file_contents(self) -> None:
        """Critical TAPM invariant: actual file JSON must not be in the prompt."""
        _, usr_p = self._assemble_prompt()
        # If the user prompt contained serialized wp_structure.json, it would
        # have WP IDs like "WP1" or "work_packages" as JSON array content.
        # In TAPM mode, only the *path* to wp_structure.json appears.
        # We check that the prompt doesn't contain a telltale JSON dump pattern:
        assert "```json" not in usr_p, (
            "TAPM prompt should not contain JSON code fences from "
            "serialized input files"
        )

    def test_prompt_contains_tools_instruction(self) -> None:
        """System prompt must instruct Claude about Read/Glob tools."""
        sys_p, _ = self._assemble_prompt()
        assert "Read" in sys_p
        assert "Glob" in sys_p
        assert "Do not read files outside" in sys_p

    def test_prompt_contains_node_id(self) -> None:
        """The node_id must appear in task metadata."""
        _, usr_p = self._assemble_prompt()
        assert "n05_impact_architecture" in usr_p

    def test_prompt_contains_schema_hints(self) -> None:
        """Schema hints for impact_architecture.json should appear."""
        _, usr_p = self._assemble_prompt()
        assert "orch.phase5.impact_architecture.v1" in usr_p


# ---------------------------------------------------------------------------
# Test 3: Phase 5 artifact production path
# ---------------------------------------------------------------------------


class TestPhase5ArtifactProductionPath:
    """Verify that TAPM mode produces the canonical Phase 5 artifact."""

    def _make_phase5_env(self, tmp_path: Path) -> Path:
        """Create a minimal environment for Phase 5 TAPM skill execution."""
        repo_root = tmp_path

        # Copy real skill catalog
        src_catalog = _REPO_ROOT / ".claude" / "workflows" / "system_orchestration" / "skill_catalog.yaml"
        dst_catalog = repo_root / ".claude" / "workflows" / "system_orchestration" / "skill_catalog.yaml"
        dst_catalog.parent.mkdir(parents=True, exist_ok=True)
        dst_catalog.write_text(src_catalog.read_text(encoding="utf-8-sig"), encoding="utf-8")

        # Copy real artifact schema spec
        src_schema = _REPO_ROOT / ".claude" / "workflows" / "system_orchestration" / "artifact_schema_specification.yaml"
        dst_schema = repo_root / ".claude" / "workflows" / "system_orchestration" / "artifact_schema_specification.yaml"
        dst_schema.write_text(src_schema.read_text(encoding="utf-8-sig"), encoding="utf-8")

        # Copy real skill spec
        src_spec = _REPO_ROOT / ".claude" / "skills" / "impact-pathway-mapper.md"
        dst_spec = repo_root / ".claude" / "skills" / "impact-pathway-mapper.md"
        dst_spec.parent.mkdir(parents=True, exist_ok=True)
        dst_spec.write_text(src_spec.read_text(encoding="utf-8-sig"), encoding="utf-8")

        # Create output directory parent
        (repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs").mkdir(
            parents=True, exist_ok=True
        )

        return repo_root

    def test_tapm_invocation_passes_tools(self, tmp_path: Path) -> None:
        """run_skill() for impact-pathway-mapper must pass tools=["Read", "Glob"]."""
        repo_root = self._make_phase5_env(tmp_path)

        valid_response = json.dumps({
            "schema_id": "orch.phase5.impact_architecture.v1",
            "run_id": "test-run-002",
            "impact_pathways": [{"pathway_id": "PWY-1", "expected_impact_id": "EI-01", "project_outputs": ["D1-01"], "outcomes": [], "impact_narrative": "test", "tier2b_source_ref": "test"}],
            "kpis": [{"kpi_id": "KPI-01", "description": "test", "target": "1", "measurement_method": "test", "traceable_to_deliverable": "D1-01"}],
            "dissemination_plan": {"activities": [{"activity_type": "pub", "target_audience": "researchers", "responsible_partner": "P1"}], "open_access_policy": "OA"},
            "exploitation_plan": {"activities": [{"activity_type": "license", "expected_result": "spin-off", "responsible_partner": "P1"}]},
            "sustainability_mechanism": {"description": "community", "responsible_partners": ["P1"]},
        })

        with patch(_TRANSPORT_TARGET, return_value=valid_response) as mock:
            result = run_skill(
                "impact-pathway-mapper", "test-run-002", repo_root,
                node_id="n05_impact_architecture",
            )

        assert result.status == "success"
        # Verify TAPM tools were requested
        call_kwargs = mock.call_args
        assert call_kwargs.kwargs.get("tools") == ["Read", "Glob"]

    def test_canonical_artifact_written(self, tmp_path: Path) -> None:
        """The canonical impact_architecture.json must be written to disk."""
        repo_root = self._make_phase5_env(tmp_path)

        valid_response = json.dumps({
            "schema_id": "orch.phase5.impact_architecture.v1",
            "run_id": "test-run-003",
            "impact_pathways": [{"pathway_id": "PWY-1", "expected_impact_id": "EI-01", "project_outputs": ["D1-01"], "outcomes": [], "impact_narrative": "test", "tier2b_source_ref": "test"}],
            "kpis": [{"kpi_id": "KPI-01", "description": "test", "target": "1", "measurement_method": "test", "traceable_to_deliverable": "D1-01"}],
            "dissemination_plan": {"activities": [{"activity_type": "pub", "target_audience": "researchers", "responsible_partner": "P1"}], "open_access_policy": "OA"},
            "exploitation_plan": {"activities": [{"activity_type": "license", "expected_result": "spin-off", "responsible_partner": "P1"}]},
            "sustainability_mechanism": {"description": "community", "responsible_partners": ["P1"]},
        })

        with patch(_TRANSPORT_TARGET, return_value=valid_response):
            result = run_skill(
                "impact-pathway-mapper", "test-run-003", repo_root,
                node_id="n05_impact_architecture",
            )

        assert result.status == "success"
        canonical_path = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase5_impact_architecture" / "impact_architecture.json"
        )
        assert canonical_path.exists(), (
            f"Canonical artifact not written: {canonical_path}"
        )
        content = json.loads(canonical_path.read_text(encoding="utf-8"))
        assert content["schema_id"] == "orch.phase5.impact_architecture.v1"
        assert content["run_id"] == "test-run-003"

    def test_tapm_timeout_uses_600s(self, tmp_path: Path) -> None:
        """TAPM mode must use the extended 600s timeout, not the 300s default."""
        repo_root = self._make_phase5_env(tmp_path)

        valid_response = json.dumps({
            "schema_id": "orch.phase5.impact_architecture.v1",
            "run_id": "test-run-004",
            "impact_pathways": [],
            "kpis": [],
            "dissemination_plan": {"activities": [], "open_access_policy": "OA"},
            "exploitation_plan": {"activities": []},
            "sustainability_mechanism": {"description": "test", "responsible_partners": []},
        })

        with patch(_TRANSPORT_TARGET, return_value=valid_response) as mock:
            run_skill(
                "impact-pathway-mapper", "test-run-004", repo_root,
                node_id="n05_impact_architecture",
            )

        call_kwargs = mock.call_args
        timeout = call_kwargs.kwargs.get("timeout_seconds")
        assert timeout == 600, (
            f"TAPM timeout should be 600s (not the default 300s); got {timeout}"
        )


# ---------------------------------------------------------------------------
# Test 4: DEC check dependency on impact_architecture directory
# ---------------------------------------------------------------------------


class TestDecCheckDependency:
    """Verify that dissemination-exploitation-communication-check depends on
    the Phase 5 artifact directory and remains in cli-prompt mode."""

    def test_dec_check_reads_from_phase5_directory(self) -> None:
        """DEC check's reads_from must include the Phase 5 output directory."""
        entry = _get_skill_entry(
            "dissemination-exploitation-communication-check", _REPO_ROOT
        )
        reads_from = entry.get("reads_from", [])
        assert any(
            "phase5_impact_architecture" in r for r in reads_from
        ), (
            "DEC check must read from phase5_impact_architecture/; "
            f"found reads_from={reads_from}"
        )

    def test_dec_check_remains_cli_prompt(self) -> None:
        """DEC check must NOT be migrated to TAPM in this change."""
        entry = _get_skill_entry(
            "dissemination-exploitation-communication-check", _REPO_ROOT
        )
        mode = entry.get("execution_mode", "cli-prompt")
        assert mode == "cli-prompt", (
            "dissemination-exploitation-communication-check must remain "
            f"in cli-prompt mode; found execution_mode={mode!r}"
        )


# ---------------------------------------------------------------------------
# Test 5: No regression to other Phase 5 cli-prompt skills
# ---------------------------------------------------------------------------


class TestPhase5CliPromptSkillsUnchanged:
    """Verify that other Phase 5 skills are not affected by this migration."""

    def test_dec_check_no_execution_mode_set(self) -> None:
        """DEC check should have no execution_mode (defaults to cli-prompt)."""
        entry = _get_skill_entry(
            "dissemination-exploitation-communication-check", _REPO_ROOT
        )
        # No execution_mode field means default cli-prompt
        assert entry.get("execution_mode") is None or entry.get("execution_mode") == "cli-prompt"

    def test_gate_enforcement_remains_tapm(self) -> None:
        """gate-enforcement was already TAPM; must not be changed."""
        entry = _get_skill_entry("gate-enforcement", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_proposal_section_traceability_check_unchanged(self) -> None:
        """proposal-section-traceability-check should not have TAPM set."""
        entry = _get_skill_entry(
            "proposal-section-traceability-check", _REPO_ROOT
        )
        # This skill is skipped at Phase 5 (Tier 5 not populated) so mode
        # doesn't matter, but it should not have been changed.
        mode = entry.get("execution_mode")
        assert mode is None or mode == "cli-prompt", (
            f"proposal-section-traceability-check should not be TAPM; "
            f"found execution_mode={mode!r}"
        )


# ---------------------------------------------------------------------------
# Test 6: Skill spec has TAPM input boundary instructions
# ---------------------------------------------------------------------------


class TestSkillSpecTapmInstructions:
    """Verify that the impact-pathway-mapper.md skill spec contains TAPM
    input-boundary instructions."""

    def test_skill_spec_contains_tapm_section(self) -> None:
        """The skill spec must have a TAPM input access section."""
        spec = _load_skill_spec("impact-pathway-mapper", _REPO_ROOT)
        assert "Input Access (TAPM Mode)" in spec, (
            "impact-pathway-mapper.md must contain an 'Input Access (TAPM Mode)' section"
        )

    def test_skill_spec_lists_declared_input_files(self) -> None:
        """The TAPM section must list the specific input files to read."""
        spec = _load_skill_spec("impact-pathway-mapper", _REPO_ROOT)
        assert "outcomes.json" in spec
        assert "impacts.json" in spec
        assert "expected_outcomes.json" in spec
        assert "expected_impacts.json" in spec
        assert "wp_structure.json" in spec

    def test_skill_spec_has_boundary_constraints(self) -> None:
        """The TAPM section must include boundary constraints."""
        spec = _load_skill_spec("impact-pathway-mapper", _REPO_ROOT)
        assert "Do not read files outside" in spec
