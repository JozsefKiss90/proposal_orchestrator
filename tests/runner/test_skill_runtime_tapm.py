"""
Tests for ``_assemble_tapm_prompt()`` — TAPM prompt assembly (Step 2).

Verifies that the TAPM prompt:
  - Contains the skill spec, task metadata, and declared input paths
  - Does NOT contain serialized file contents (critical TAPM invariant)
  - Includes schema hints when artifact schemas match writes_to paths
  - Respects the 24KB system prompt size limit
  - Handles edge cases (empty inputs, missing node_id, directory writes_to)

All tests use synthetic environments on ``tmp_path``.  No Claude transport
mock is needed because ``_assemble_tapm_prompt()`` only constructs strings.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.skill_runtime import _assemble_tapm_prompt


# ---------------------------------------------------------------------------
# Fixtures — synthetic skill environment
# ---------------------------------------------------------------------------


def _write_skill_catalog(repo_root: Path, entries: list[dict]) -> None:
    """Write a synthetic skill_catalog.yaml."""
    catalog_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml"
    )
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        yaml.dump({"skill_catalog": entries}), encoding="utf-8"
    )


def _write_artifact_schema(repo_root: Path, schemas: dict | None = None) -> None:
    """Write a synthetic artifact_schema_specification.yaml."""
    spec_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml"
    )
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    if schemas is None:
        schemas = {
            "tier4_phase_output_schemas": {
                "test_output": {
                    "canonical_path": "docs/tier4/phase1/test_output.json",
                    "schema_id_value": "test_output_v1",
                    "fields": {
                        "schema_id": {"required": True},
                        "run_id": {"required": True},
                        "result": {"required": True},
                    },
                }
            },
            "tier2b_extracted_schemas": {
                "call_constraints": {
                    "canonical_path": "docs/tier2b/extracted/call_constraints.json",
                    "fields": {
                        "constraints": {"required": True},
                        "source_refs": {"required": True},
                    },
                },
                "expected_outcomes": {
                    "canonical_path": "docs/tier2b/extracted/expected_outcomes.json",
                    "schema_id_value": "expected_outcomes_v1",
                    "fields": {
                        "outcomes": {"required": True},
                    },
                },
            },
        }
    spec_path.write_text(yaml.dump(schemas), encoding="utf-8")


def _make_tapm_env(tmp_path: Path) -> Path:
    """Create a synthetic environment for TAPM prompt assembly tests.

    Returns repo_root with:
      - artifact schema specification
      - input files on disk (to verify they are NOT read by the function)
    """
    repo_root = tmp_path

    # Artifact schema
    _write_artifact_schema(repo_root)

    # Input files with a distinctive marker to verify they are not in the prompt
    input_dir = repo_root / "docs" / "tier3" / "data"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "input.json").write_text(
        json.dumps({"MARKER_CONTENT_SHOULD_NOT_APPEAR_IN_PROMPT": True}),
        encoding="utf-8",
    )

    # Directory input with files
    dir_input = repo_root / "docs" / "tier2b" / "sources"
    dir_input.mkdir(parents=True, exist_ok=True)
    (dir_input / "source.json").write_text(
        json.dumps({"ANOTHER_MARKER_MUST_NOT_LEAK": "secret data"}),
        encoding="utf-8",
    )

    # Output directories
    (repo_root / "docs" / "tier4" / "phase1").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "tier2b" / "extracted").mkdir(parents=True, exist_ok=True)

    return repo_root


@pytest.fixture()
def tapm_env(tmp_path: Path) -> Path:
    """Return a fresh synthetic TAPM environment."""
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    return _make_tapm_env(tmp_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SKILL_SPEC = "# test-skill\nTest skill specification for TAPM."

_READS_FROM = [
    "docs/tier3/data/input.json",
    "docs/tier2b/sources/",
]

_WRITES_TO_FILE = ["docs/tier4/phase1/test_output.json"]
_WRITES_TO_DIR = ["docs/tier2b/extracted/"]

_CONSTRAINTS = [
    "Must not fabricate data",
    "Must carry source references",
]


def _call_tapm(
    tapm_env: Path,
    *,
    skill_spec: str = _SKILL_SPEC,
    skill_id: str = "test-skill",
    run_id: str = "run-001",
    reads_from: list[str] = _READS_FROM,
    writes_to: list[str] = _WRITES_TO_FILE,
    constraints: list[str] = _CONSTRAINTS,
    node_id: str | None = None,
) -> tuple[str, str]:
    """Convenience wrapper for ``_assemble_tapm_prompt``."""
    return _assemble_tapm_prompt(
        skill_spec=skill_spec,
        skill_id=skill_id,
        run_id=run_id,
        reads_from=reads_from,
        writes_to=writes_to,
        constraints=constraints,
        repo_root=tapm_env,
        node_id=node_id,
    )


# ---------------------------------------------------------------------------
# TestAssembleTapmPromptBasic — core contract
# ---------------------------------------------------------------------------


class TestAssembleTapmPromptBasic:
    def test_returns_tuple_of_two_strings(self, tapm_env: Path) -> None:
        result = _call_tapm(tapm_env)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_system_prompt_contains_role_preamble(self, tapm_env: Path) -> None:
        sys_p, _ = _call_tapm(tapm_env)
        assert "skill execution engine" in sys_p
        assert "Horizon Europe" in sys_p

    def test_system_prompt_contains_constraints(self, tapm_env: Path) -> None:
        sys_p, _ = _call_tapm(tapm_env)
        assert "Must not fabricate data" in sys_p
        assert "Must carry source references" in sys_p

    def test_system_prompt_contains_run_id_instruction(self, tapm_env: Path) -> None:
        sys_p, _ = _call_tapm(tapm_env)
        assert "run-001" in sys_p

    def test_system_prompt_contains_input_boundary_instructions(
        self, tapm_env: Path
    ) -> None:
        sys_p, _ = _call_tapm(tapm_env)
        assert "Read ONLY" in sys_p
        assert "Declared Inputs" in sys_p
        assert "Do not read files outside" in sys_p

    def test_system_prompt_under_24kb(self, tapm_env: Path) -> None:
        sys_p, _ = _call_tapm(tapm_env)
        assert len(sys_p) < 24_000

    def test_user_prompt_contains_skill_spec(self, tapm_env: Path) -> None:
        _, usr_p = _call_tapm(tapm_env)
        assert _SKILL_SPEC in usr_p

    def test_user_prompt_contains_declared_input_paths(
        self, tapm_env: Path
    ) -> None:
        _, usr_p = _call_tapm(tapm_env)
        for rel_path in _READS_FROM:
            abs_path = str(tapm_env / rel_path)
            assert abs_path in usr_p

    def test_user_prompt_does_not_contain_file_contents(
        self, tapm_env: Path
    ) -> None:
        """Critical TAPM invariant: file contents must not appear in prompt."""
        sys_p, usr_p = _call_tapm(tapm_env)
        combined = sys_p + usr_p
        assert "MARKER_CONTENT_SHOULD_NOT_APPEAR_IN_PROMPT" not in combined
        assert "ANOTHER_MARKER_MUST_NOT_LEAK" not in combined

    def test_user_prompt_contains_writes_to_paths(self, tapm_env: Path) -> None:
        _, usr_p = _call_tapm(tapm_env)
        assert "docs/tier4/phase1/test_output.json" in usr_p

    def test_user_prompt_contains_run_id(self, tapm_env: Path) -> None:
        _, usr_p = _call_tapm(tapm_env)
        assert "run-001" in usr_p


# ---------------------------------------------------------------------------
# TestAssembleTapmPromptSchemaHints — schema integration
# ---------------------------------------------------------------------------


class TestAssembleTapmPromptSchemaHints:
    def test_schema_id_hint_present_for_known_writes_to(
        self, tapm_env: Path
    ) -> None:
        _, usr_p = _call_tapm(tapm_env, writes_to=_WRITES_TO_FILE)
        assert "test_output_v1" in usr_p

    def test_required_fields_hint_present(self, tapm_env: Path) -> None:
        _, usr_p = _call_tapm(tapm_env, writes_to=_WRITES_TO_FILE)
        assert "result" in usr_p

    def test_no_schema_hint_when_no_match(self, tapm_env: Path) -> None:
        """Unmatched writes_to path produces no schema hint (no crash)."""
        _, usr_p = _call_tapm(
            tapm_env, writes_to=["docs/unknown/output.json"]
        )
        assert "schema_id" not in usr_p.lower().split("output requirements")[1] or \
            "Expected output schemas" not in usr_p

    def test_directory_writes_to_resolves_schemas(self, tapm_env: Path) -> None:
        """Directory writes_to finds all schemas under that prefix."""
        _, usr_p = _call_tapm(tapm_env, writes_to=_WRITES_TO_DIR)
        # Both tier2b extracted schemas should appear
        assert "call_constraints.json" in usr_p
        assert "expected_outcomes.json" in usr_p
        assert "expected_outcomes_v1" in usr_p


# ---------------------------------------------------------------------------
# TestAssembleTapmPromptEdgeCases
# ---------------------------------------------------------------------------


class TestAssembleTapmPromptEdgeCases:
    def test_empty_reads_from(self, tapm_env: Path) -> None:
        sys_p, usr_p = _call_tapm(tapm_env, reads_from=[])
        assert "(no declared inputs)" in usr_p
        assert isinstance(sys_p, str)

    def test_empty_writes_to(self, tapm_env: Path) -> None:
        sys_p, usr_p = _call_tapm(tapm_env, writes_to=[])
        # Should still produce valid prompts
        assert isinstance(sys_p, str)
        assert isinstance(usr_p, str)

    def test_empty_constraints(self, tapm_env: Path) -> None:
        sys_p, _ = _call_tapm(tapm_env, constraints=[])
        # No constraint text but still a valid prompt
        assert "skill execution engine" in sys_p
        assert "hard failures" not in sys_p

    def test_node_id_included_when_provided(self, tapm_env: Path) -> None:
        _, usr_p = _call_tapm(tapm_env, node_id="n01_call_analysis")
        assert "n01_call_analysis" in usr_p

    def test_node_id_absent_when_none(self, tapm_env: Path) -> None:
        _, usr_p = _call_tapm(tapm_env, node_id=None)
        assert "node_id:" not in usr_p

    def test_large_skill_spec_in_user_prompt_not_system_prompt(
        self, tapm_env: Path
    ) -> None:
        """Large skill spec stays in user prompt; system prompt stays small."""
        large_spec = "# Large Skill\n" + ("x" * 30_000)
        sys_p, usr_p = _call_tapm(tapm_env, skill_spec=large_spec)
        assert large_spec in usr_p
        assert len(sys_p) < 24_000
        assert "x" * 100 not in sys_p


# ---------------------------------------------------------------------------
# TestAssembleTapmPromptSizeConstraints
# ---------------------------------------------------------------------------


class TestAssembleTapmPromptSizeConstraints:
    def test_total_prompt_size_small_inputs(self, tapm_env: Path) -> None:
        """Small skill spec + 3 paths → total under 10KB."""
        small_spec = "# Small Skill\nDo something simple."
        sys_p, usr_p = _call_tapm(
            tapm_env,
            skill_spec=small_spec,
            reads_from=["a.json", "b.json", "c.json"],
            writes_to=["out.json"],
        )
        total = len(sys_p) + len(usr_p)
        assert total < 10_000

    def test_total_prompt_size_large_spec(self, tapm_env: Path) -> None:
        """Large skill spec (~33KB) + 3 paths → total under 50KB."""
        large_spec = "# Large Skill\n" + ("detailed instructions\n" * 1500)
        sys_p, usr_p = _call_tapm(
            tapm_env,
            skill_spec=large_spec,
            reads_from=["a.json", "b.json", "c.json"],
        )
        total = len(sys_p) + len(usr_p)
        assert total < 50_000


# ---------------------------------------------------------------------------
# TestAssembleTapmPromptAbsolutePaths
# ---------------------------------------------------------------------------


class TestAssembleTapmPromptAbsolutePaths:
    def test_declared_inputs_use_absolute_paths(self, tapm_env: Path) -> None:
        """Declared input paths are absolute (joined with repo_root)."""
        _, usr_p = _call_tapm(
            tapm_env,
            reads_from=["docs/tier3/data/input.json"],
        )
        expected_abs = str(tapm_env / "docs/tier3/data/input.json")
        assert expected_abs in usr_p


# ---------------------------------------------------------------------------
# TestRunSkillTapmMode — run_skill() TAPM mode integration tests (Step 3)
# ---------------------------------------------------------------------------

from unittest.mock import patch

from runner.claude_transport import ClaudeTransportError
from runner.runtime_models import SkillResult
from runner.skill_runtime import run_skill


def _write_skill_spec(repo_root: Path, skill_id: str, content: str = "") -> None:
    """Write a synthetic skill .md file."""
    spec_path = repo_root / ".claude" / "skills" / f"{skill_id}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        content or f"# {skill_id}\nTest skill specification.",
        encoding="utf-8",
    )


def _make_tapm_skill_env(tmp_path: Path) -> Path:
    """Create an environment for run_skill() TAPM mode tests.

    Returns repo_root with:
      - skill catalog containing a TAPM skill and a cli-prompt skill
      - artifact schema specification
      - skill spec .md files
      - output directories
      - input files on disk (TAPM mode should NOT pre-read these)
    """
    repo_root = tmp_path

    # Skill catalog with execution_mode field
    _write_skill_catalog(repo_root, [
        {
            "id": "tapm-skill",
            "execution_mode": "tapm",
            "reads_from": ["docs/tier3/data/input.json"],
            "writes_to": ["docs/tier4/phase1/test_output.json"],
            "constitutional_constraints": ["Must not fabricate data"],
        },
        {
            "id": "cli-skill",
            # No execution_mode — defaults to "cli-prompt"
            "reads_from": ["docs/tier3/data/input.json"],
            "writes_to": ["docs/tier4/phase1/test_output.json"],
            "constitutional_constraints": ["Must not fabricate data"],
        },
        {
            "id": "bad-mode-skill",
            "execution_mode": "unknown-mode",
            "reads_from": [],
            "writes_to": ["docs/tier4/phase1/test_output.json"],
            "constitutional_constraints": [],
        },
    ])

    # Artifact schema
    _write_artifact_schema(repo_root)

    # Skill specs
    _write_skill_spec(repo_root, "tapm-skill")
    _write_skill_spec(repo_root, "cli-skill")
    _write_skill_spec(repo_root, "bad-mode-skill")

    # Input file on disk
    input_dir = repo_root / "docs" / "tier3" / "data"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "input.json").write_text(
        json.dumps({"topic": "AI in healthcare"}), encoding="utf-8",
    )

    # Output directory
    (repo_root / "docs" / "tier4" / "phase1").mkdir(parents=True, exist_ok=True)

    return repo_root


@pytest.fixture()
def tapm_skill_env(tmp_path: Path) -> Path:
    """Return a fresh environment for run_skill() TAPM mode tests."""
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    return _make_tapm_skill_env(tmp_path)


_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"

_VALID_RESPONSE = json.dumps({
    "schema_id": "test_output_v1",
    "run_id": "run-001",
    "result": "extracted data",
})


class TestRunSkillTapmMode:
    """Integration tests for run_skill() TAPM mode selection (Step 3)."""

    def test_default_mode_is_cli_prompt(self, tapm_skill_env: Path) -> None:
        """Skill without execution_mode uses cli-prompt path."""
        response = {
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "data",
        }
        with patch(_TRANSPORT_TARGET, return_value=json.dumps(response)) as mock:
            result = run_skill("cli-skill", "run-001", tapm_skill_env)

        assert result.status == "success"
        # cli-prompt path: transport called WITHOUT tools
        call_kwargs = mock.call_args
        assert call_kwargs.kwargs.get("tools") is None

    def test_tapm_mode_passes_tools(self, tapm_skill_env: Path) -> None:
        """TAPM skill passes tools=["Read", "Glob"] to transport."""
        with patch(_TRANSPORT_TARGET, return_value=_VALID_RESPONSE) as mock:
            result = run_skill("tapm-skill", "run-001", tapm_skill_env)

        assert result.status == "success"
        call_kwargs = mock.call_args
        assert call_kwargs.kwargs.get("tools") == ["Read", "Glob"]

    def test_tapm_mode_skips_resolve_inputs(self, tapm_skill_env: Path) -> None:
        """TAPM mode succeeds even when input files are missing from disk."""
        # Remove the input file — would cause MISSING_INPUT in cli-prompt
        (tapm_skill_env / "docs" / "tier3" / "data" / "input.json").unlink()

        with patch(_TRANSPORT_TARGET, return_value=_VALID_RESPONSE):
            result = run_skill("tapm-skill", "run-001", tapm_skill_env)

        # TAPM doesn't validate inputs in Python — should succeed
        assert result.status == "success"

    def test_tapm_mode_skips_skill_prompt_assembly(
        self, tapm_skill_env: Path
    ) -> None:
        """TAPM mode does not call _assemble_skill_prompt."""
        with patch(_TRANSPORT_TARGET, return_value=_VALID_RESPONSE), \
             patch(
                 "runner.skill_runtime._assemble_skill_prompt",
                 side_effect=AssertionError("should not be called"),
             ):
            result = run_skill("tapm-skill", "run-001", tapm_skill_env)

        assert result.status == "success"

    def test_tapm_mode_writes_artifact(self, tapm_skill_env: Path) -> None:
        """TAPM mode writes artifact to canonical path via shared Phases D-F."""
        with patch(_TRANSPORT_TARGET, return_value=_VALID_RESPONSE):
            result = run_skill("tapm-skill", "run-001", tapm_skill_env)

        assert result.status == "success"
        assert len(result.outputs_written) == 1
        written_path = tapm_skill_env / result.outputs_written[0]
        assert written_path.exists()
        content = json.loads(written_path.read_text(encoding="utf-8"))
        assert content["run_id"] == "run-001"
        assert content["schema_id"] == "test_output_v1"
        assert "artifact_status" not in content

    def test_tapm_mode_transport_failure(self, tapm_skill_env: Path) -> None:
        """Claude transport failure in TAPM mode returns INCOMPLETE_OUTPUT."""
        with patch(
            _TRANSPORT_TARGET,
            side_effect=ClaudeTransportError("timeout"),
        ):
            result = run_skill("tapm-skill", "run-001", tapm_skill_env)

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"

    def test_tapm_mode_malformed_response(self, tapm_skill_env: Path) -> None:
        """Non-JSON response in TAPM mode returns INCOMPLETE_OUTPUT."""
        with patch(_TRANSPORT_TARGET, return_value="This is not JSON"):
            result = run_skill("tapm-skill", "run-001", tapm_skill_env)

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"

    def test_tapm_mode_schema_validation_failure(
        self, tapm_skill_env: Path
    ) -> None:
        """TAPM response without run_id returns MALFORMED_ARTIFACT."""
        bad_response = json.dumps({
            "schema_id": "test_output_v1",
            # run_id intentionally missing
            "result": "data",
        })
        with patch(_TRANSPORT_TARGET, return_value=bad_response):
            result = run_skill("tapm-skill", "run-001", tapm_skill_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_node_id_forwarded_to_tapm_prompt(
        self, tapm_skill_env: Path
    ) -> None:
        """node_id parameter appears in TAPM prompt."""
        with patch(_TRANSPORT_TARGET, return_value=_VALID_RESPONSE) as mock:
            run_skill(
                "tapm-skill", "run-001", tapm_skill_env,
                node_id="n01_call_analysis",
            )

        call_kwargs = mock.call_args
        user_prompt = call_kwargs.kwargs.get("user_prompt", "")
        assert "n01_call_analysis" in user_prompt

    def test_node_id_none_works_for_tapm(self, tapm_skill_env: Path) -> None:
        """TAPM mode works when node_id is None (default)."""
        with patch(_TRANSPORT_TARGET, return_value=_VALID_RESPONSE) as mock:
            result = run_skill("tapm-skill", "run-001", tapm_skill_env)

        assert result.status == "success"
        call_kwargs = mock.call_args
        user_prompt = call_kwargs.kwargs.get("user_prompt", "")
        assert "node_id:" not in user_prompt

    def test_unknown_execution_mode(self, tapm_skill_env: Path) -> None:
        """Unrecognized execution_mode returns CONSTRAINT_VIOLATION."""
        result = run_skill("bad-mode-skill", "run-001", tapm_skill_env)

        assert result.status == "failure"
        assert result.failure_category == "CONSTRAINT_VIOLATION"
        assert "unknown-mode" in result.failure_reason
