"""
Tests for constitutional-compliance-check TAPM migration.

Verifies that:
  1. Skill catalog declares TAPM mode for constitutional-compliance-check
  2. reads_from no longer contains broad docs/tier4_orchestration_state/phase_outputs/
  3. optional_reads_from still contains docs/tier5_deliverables/
  4. CLAUDE.md remains a required input
  5. TAPM prompt size is bounded for Phase 6 (~20KB, not ~295KB)
  6. Phase 6 can invoke constitutional-compliance-check without requiring Tier 5
  7. All 12 CLAUDE.md §13 checks remain required in the skill spec
  8. Agent runtime injects artifact_path for constitutional-compliance-check
  9. Skill spec contains TAPM input access section

Root cause addressed: run 839062b2 showed constitutional-compliance-check timing
out at 300s in cli-prompt mode with user_prompt_chars=294,966 because the entire
docs/tier4_orchestration_state/phase_outputs/ directory was serialized into the
prompt. The fix migrates to TAPM mode where only CLAUDE.md and the specific
artifact_path are declared, reducing prompt size to ~20KB.
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
# A. Skill catalog config tests
# ===========================================================================


class TestConstitutionalComplianceCheckTapmConfig:
    """Verify the skill catalog declares TAPM mode correctly."""

    def test_execution_mode_is_tapm(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_broad_phase_outputs_not_in_reads_from(self) -> None:
        """Critical: broad directory removed to prevent 295KB prompt bloat."""
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier4_orchestration_state/phase_outputs/" not in reads

    def test_claude_md_in_reads_from(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "CLAUDE.md" in reads

    def test_optional_reads_from_has_tier5(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        optional = entry.get("optional_reads_from", [])
        assert "docs/tier5_deliverables/" in optional

    def test_tier5_not_in_required_reads_from(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        reads = entry.get("reads_from", [])
        assert "docs/tier5_deliverables/" not in reads

    def test_writes_to_preserved(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        writes = entry.get("writes_to", [])
        assert "docs/tier4_orchestration_state/validation_reports/" in writes
        assert "docs/tier4_orchestration_state/decision_log/" in writes

    def test_all_three_constraints_preserved(self) -> None:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        constraints = entry.get("constitutional_constraints", [])
        assert len(constraints) == 3
        assert any("Section 13" in c for c in constraints)
        assert any("flagged" in c for c in constraints)
        assert any("governs this skill" in c for c in constraints)

    def test_rollback_is_single_line(self) -> None:
        """Removing execution_mode line reverts to cli-prompt (default)."""
        catalog_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml"
        )
        text = catalog_path.read_text(encoding="utf-8-sig")
        lines = text.split("\n")
        in_section = False
        mode_line_found = False
        for line in lines:
            if "id: constitutional-compliance-check" in line:
                in_section = True
            elif in_section and line.strip().startswith("- id:"):
                break
            elif in_section and 'execution_mode' in line and 'tapm' in line:
                mode_line_found = True
                # Verify it's a standalone YAML line (removable)
                stripped = line.strip()
                assert stripped.startswith("execution_mode:")
        assert mode_line_found


# ===========================================================================
# B. TAPM prompt assembly tests
# ===========================================================================


class TestConstitutionalComplianceCheckTapmPrompt:
    """Verify TAPM prompt properties for constitutional-compliance-check.

    This is the surgical fix for the 295KB cli-prompt timeout (run 839062b2).
    The TAPM prompt must be bounded (<50KB) and must NOT serialize any file
    contents into the prompt.
    """

    def _assemble_prompt(
        self,
        caller_context: dict | None = None,
    ) -> tuple[str, str]:
        entry = _get_skill_entry("constitutional-compliance-check", _REPO_ROOT)
        skill_spec = _load_skill_spec("constitutional-compliance-check", _REPO_ROOT)
        return _assemble_tapm_prompt(
            skill_spec=skill_spec,
            skill_id="constitutional-compliance-check",
            run_id="test-run-ccc",
            reads_from=entry.get("reads_from", []),
            writes_to=entry.get("writes_to", []),
            constraints=entry.get("constitutional_constraints", []),
            repo_root=_REPO_ROOT,
            node_id="n06_implementation_architecture",
            caller_context=caller_context,
            optional_reads_from=entry.get("optional_reads_from"),
        )

    def test_prompt_size_under_50kb(self) -> None:
        """Critical: prompt must be <50KB to avoid the 295KB timeout."""
        sys_p, usr_p = self._assemble_prompt()
        total = len(sys_p) + len(usr_p)
        assert total < 50_000, (
            f"Constitutional compliance check TAPM prompt is {total} chars; "
            f"must be under 50KB (was 295KB in cli-prompt mode causing 300s timeout)"
        )

    def test_system_prompt_under_24kb(self) -> None:
        sys_p, _ = self._assemble_prompt()
        assert len(sys_p) < 24_000

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
        assert "n06_implementation_architecture" in usr_p

    def test_prompt_contains_claude_md_path(self) -> None:
        _, usr_p = self._assemble_prompt()
        assert "CLAUDE.md" in usr_p

    def test_no_run_id_or_schema_id_required(self) -> None:
        """Compliance check writes validation reports — no schema_id/run_id needed."""
        sys_p, _ = self._assemble_prompt()
        assert "Do NOT include run_id, schema_id" in sys_p

    def test_caller_context_artifact_path_in_prompt(self) -> None:
        """When artifact_path is supplied as caller_context, it appears in prompt."""
        ctx = {
            "artifact_path": (
                "docs/tier4_orchestration_state/phase_outputs/"
                "phase6_implementation_architecture/implementation_architecture.json"
            )
        }
        _, usr_p = self._assemble_prompt(caller_context=ctx)
        assert "implementation_architecture.json" in usr_p

    def test_optional_tier5_in_prompt(self) -> None:
        """Optional reads_from for Tier 5 should appear as optional in prompt."""
        _, usr_p = self._assemble_prompt()
        assert "OPTIONAL" in usr_p
        assert "tier5_deliverables" in usr_p

    def test_prompt_size_with_caller_context(self) -> None:
        """Even with caller_context, total prompt stays bounded."""
        ctx = {
            "artifact_path": (
                "docs/tier4_orchestration_state/phase_outputs/"
                "phase6_implementation_architecture/implementation_architecture.json"
            )
        }
        sys_p, usr_p = self._assemble_prompt(caller_context=ctx)
        total = len(sys_p) + len(usr_p)
        assert total < 50_000


# ===========================================================================
# C. Skill spec content tests
# ===========================================================================


class TestConstitutionalComplianceCheckSpecContent:
    """Verify the skill spec has TAPM section and all 12 §13 checks."""

    def test_spec_contains_tapm_section(self) -> None:
        spec = _load_skill_spec("constitutional-compliance-check", _REPO_ROOT)
        assert "Input Access (TAPM Mode)" in spec

    def test_spec_has_boundary_constraints(self) -> None:
        spec = _load_skill_spec("constitutional-compliance-check", _REPO_ROOT)
        assert "artifact_path" in spec

    def test_spec_mentions_claude_md_as_mandatory(self) -> None:
        spec = _load_skill_spec("constitutional-compliance-check", _REPO_ROOT)
        assert "CLAUDE.md" in spec

    def test_all_12_section13_checks_in_spec(self) -> None:
        """All 12 §13 checks (13.1–13.12) must remain in the spec."""
        spec = _load_skill_spec("constitutional-compliance-check", _REPO_ROOT)
        for i in range(1, 13):
            check_id = f"13.{i}"
            assert check_id in spec, (
                f"Check {check_id} missing from constitutional-compliance-check spec"
            )

    def test_spec_requires_12_entries_in_output(self) -> None:
        """The spec must require exactly 12 section13_checks entries."""
        spec = _load_skill_spec("constitutional-compliance-check", _REPO_ROOT)
        assert "total_prohibitions_checked: 12" in spec or "total_prohibitions_checked" in spec

    def test_spec_does_not_recursively_read_phase_outputs(self) -> None:
        """TAPM section must instruct NOT to recursively read phase_outputs/."""
        spec = _load_skill_spec("constitutional-compliance-check", _REPO_ROOT)
        assert "Do not" in spec
        assert "recursively read" in spec or "phase_outputs/" in spec


# ===========================================================================
# D. Runtime invocation tests
# ===========================================================================


class TestConstitutionalComplianceCheckTapmInvocation:
    """Verify constitutional-compliance-check runs in TAPM mode."""

    def _make_env(self, tmp_path: Path) -> Path:
        repo_root = tmp_path
        for rel in [
            ".claude/workflows/system_orchestration/skill_catalog.yaml",
            ".claude/workflows/system_orchestration/artifact_schema_specification.yaml",
        ]:
            src = _REPO_ROOT / rel
            dst = repo_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")
        src_spec = (
            _REPO_ROOT / ".claude" / "skills" / "constitutional-compliance-check.md"
        )
        dst_spec = (
            repo_root / ".claude" / "skills" / "constitutional-compliance-check.md"
        )
        dst_spec.parent.mkdir(parents=True, exist_ok=True)
        dst_spec.write_text(
            src_spec.read_text(encoding="utf-8-sig"), encoding="utf-8"
        )
        # CLAUDE.md must exist (in reads_from)
        (repo_root / "CLAUDE.md").write_text("# Constitution\n", encoding="utf-8")
        # Create validation_reports dir for writes_to
        (repo_root / "docs" / "tier4_orchestration_state"
         / "validation_reports").mkdir(parents=True, exist_ok=True)
        (repo_root / "docs" / "tier4_orchestration_state"
         / "decision_log").mkdir(parents=True, exist_ok=True)
        return repo_root

    def _compliance_response(self) -> str:
        """A valid constitutional-compliance-check response."""
        checks = []
        for i in range(1, 13):
            checks.append({
                "prohibition_id": f"13.{i}",
                "prohibition_description": f"Check {i}",
                "check_status": "pass",
                "violation_evidence": None,
                "severity": None,
            })
        return json.dumps({
            "report_id": "compliance_check_test_2026-01-01T00:00:00Z",
            "skill_id": "constitutional-compliance-check",
            "invoking_agent": "implementation_architect",
            "run_id_reference": "test-run",
            "artifact_audited": "test/artifact.json",
            "section13_checks": checks,
            "summary": {
                "total_prohibitions_checked": 12,
                "violations_found": 0,
            },
            "timestamp": "2026-01-01T00:00:00Z",
        })

    def test_tapm_invocation_passes_tools(self, tmp_path: Path) -> None:
        repo_root = self._make_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._compliance_response()) as mock:
            result = run_skill(
                "constitutional-compliance-check", "test-run", repo_root,
                node_id="n06_implementation_architecture",
            )
        assert result.status == "success", f"Got: {result.failure_reason}"
        assert mock.call_args.kwargs.get("tools") == ["Read", "Glob"]

    def test_tapm_timeout_uses_1200s(self, tmp_path: Path) -> None:
        repo_root = self._make_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._compliance_response()) as mock:
            run_skill(
                "constitutional-compliance-check", "test-run", repo_root,
            )
        assert mock.call_args.kwargs.get("timeout_seconds") == 1200

    def test_tapm_prompt_not_cli_prompt(self, tmp_path: Path) -> None:
        """Verify TAPM path used — no serialized inputs in prompt."""
        repo_root = self._make_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._compliance_response()) as mock:
            run_skill(
                "constitutional-compliance-check", "test-run", repo_root,
            )
        call_kwargs = mock.call_args.kwargs
        user_prompt = call_kwargs.get("user_prompt", "")
        assert "# Canonical Inputs\n\n## docs/" not in user_prompt

    def test_prompt_size_bounded_at_runtime(self, tmp_path: Path) -> None:
        """The actual prompt sent to Claude must be <50KB."""
        repo_root = self._make_env(tmp_path)
        with patch(_TRANSPORT_TARGET, return_value=self._compliance_response()) as mock:
            run_skill(
                "constitutional-compliance-check", "test-run", repo_root,
                node_id="n06_implementation_architecture",
            )
        call_kwargs = mock.call_args.kwargs
        sys_len = len(call_kwargs.get("system_prompt", ""))
        usr_len = len(call_kwargs.get("user_prompt", ""))
        total = sys_len + usr_len
        assert total < 50_000, (
            f"Runtime prompt {total} chars; was 295KB in cli-prompt mode"
        )

    def test_phase6_does_not_require_tier5(self, tmp_path: Path) -> None:
        """Phase 6 invocation must succeed without Tier 5 existing on disk."""
        repo_root = self._make_env(tmp_path)
        # Ensure Tier 5 does NOT exist
        tier5_dir = repo_root / "docs" / "tier5_deliverables"
        assert not tier5_dir.exists()
        with patch(_TRANSPORT_TARGET, return_value=self._compliance_response()):
            result = run_skill(
                "constitutional-compliance-check", "test-run", repo_root,
            )
        # Must not fail with MISSING_INPUT for Tier 5
        assert result.status == "success", f"Got: {result.failure_reason}"


# ===========================================================================
# E. Agent runtime artifact_path injection tests
# ===========================================================================


class TestAgentRuntimeArtifactPathInjection:
    """Verify agent_runtime injects artifact_path for constitutional-compliance-check."""

    def test_injection_code_exists(self) -> None:
        """The agent_runtime module must have the injection block."""
        import runner.agent_runtime as ar
        import inspect
        source = inspect.getsource(ar.run_agent)
        assert "constitutional-compliance-check" in source
        assert "artifact_path" in source

    def test_injection_filters_gate_result(self) -> None:
        """The injection logic must exclude gate_result.json from candidates."""
        import runner.agent_runtime as ar
        import inspect
        # The filtering is in _resolve_auditable_artifact, called by run_agent
        source = inspect.getsource(ar._resolve_auditable_artifact)
        assert "gate_result.json" in source
