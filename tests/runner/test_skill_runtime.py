"""
Tests for runner.skill_runtime — skill execution via Claude runtime transport adapter.

Covers §14 test cases 4–6:
  4. run_id propagation into written artifacts
  5. canonical input binding — paths resolved relative to repo_root
  6. skill failure propagation — MISSING_INPUT, MALFORMED_ARTIFACT,
     INCOMPLETE_OUTPUT

Additional tests:
  - run_skill with valid inputs → success
  - run_skill with missing input → MISSING_INPUT failure without calling Claude
  - run_skill with malformed Claude response (non-JSON) → INCOMPLETE_OUTPUT
  - run_skill with valid response failing schema validation → MALFORMED_ARTIFACT
  - artifact_status absent in written artifacts
  - atomic write: failure leaves no partial artifact at canonical path
  - No imports from runner.dag_scheduler or runner.gate_evaluator

All tests use synthetic skill catalogs and mock the Claude runtime transport.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.claude_transport import ClaudeCLITimeoutError, ClaudeTransportError
from runner.runtime_models import SkillResult
from runner.skill_runtime import (
    _assemble_skill_prompt,
    _atomic_write,
    _extract_json_response,
    _validate_skill_inputs,
    _validate_skill_output,
    run_skill,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic skill catalog and artifact schema
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
            }
        }
    spec_path.write_text(yaml.dump(schemas), encoding="utf-8")


def _write_skill_spec(repo_root: Path, skill_id: str, content: str = "") -> None:
    """Write a synthetic skill .md file."""
    spec_path = repo_root / ".claude" / "skills" / f"{skill_id}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        content or f"# {skill_id}\nTest skill specification.",
        encoding="utf-8",
    )


def _make_skill_env(tmp_path: Path) -> Path:
    """Create a synthetic environment for skill runtime tests.

    Returns repo_root with:
      - skill catalog containing one test skill
      - artifact schema specification
      - skill spec .md file
      - input artifact on disk
    """
    repo_root = tmp_path

    # Skill catalog
    _write_skill_catalog(repo_root, [
        {
            "id": "test-skill",
            "reads_from": ["docs/tier3/input.json"],
            "writes_to": ["docs/tier4/phase1/test_output.json"],
            "constitutional_constraints": ["Must not fabricate data"],
        },
        {
            "id": "test-skill-dir-input",
            "reads_from": ["docs/tier2b/extracted/"],
            "writes_to": ["docs/tier4/phase1/test_output.json"],
            "constitutional_constraints": [],
        },
    ])

    # Artifact schema
    _write_artifact_schema(repo_root)

    # Skill spec
    _write_skill_spec(repo_root, "test-skill")
    _write_skill_spec(repo_root, "test-skill-dir-input")

    # Input artifact
    input_path = repo_root / "docs" / "tier3" / "input.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(
        json.dumps({"topic": "AI in healthcare", "run_id": "old"}),
        encoding="utf-8",
    )

    # Output directory
    (repo_root / "docs" / "tier4" / "phase1").mkdir(parents=True, exist_ok=True)

    return repo_root


@pytest.fixture()
def skill_env(tmp_path: Path) -> Path:
    """Return a fresh synthetic skill environment."""
    # Clear module-level caches so each test is independent
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    return _make_skill_env(tmp_path)


# ---------------------------------------------------------------------------
# Claude transport mock helpers
# ---------------------------------------------------------------------------

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"


def _claude_returns(response_dict: dict):
    """Patch ``invoke_claude_text`` to return a JSON-serialised dict."""
    return patch(_TRANSPORT_TARGET, return_value=json.dumps(response_dict))


def _claude_returns_text(text: str):
    """Patch ``invoke_claude_text`` to return raw text."""
    return patch(_TRANSPORT_TARGET, return_value=text)


def _claude_fails(error_msg: str):
    """Patch ``invoke_claude_text`` to raise a transport error."""
    return patch(
        _TRANSPORT_TARGET,
        side_effect=ClaudeTransportError(error_msg),
    )


def _claude_times_out(
    timeout_seconds: int = 300,
    stdout: str | None = None,
    stderr: str | None = None,
):
    """Patch ``invoke_claude_text`` to raise a timeout error with diagnostics."""
    return patch(
        _TRANSPORT_TARGET,
        side_effect=ClaudeCLITimeoutError(
            f"Claude CLI invocation timed out after {timeout_seconds}s",
            stdout=stdout,
            stderr=stderr,
            command=["claude", "-p", "--model", "claude-sonnet-4-6"],
            timeout_seconds=timeout_seconds,
            elapsed_seconds=float(timeout_seconds) + 0.123,
        ),
    )


# ---------------------------------------------------------------------------
# run_skill — success path
# ---------------------------------------------------------------------------


class TestRunSkillSuccess:
    def test_success_with_valid_inputs(self, skill_env: Path) -> None:
        response = {
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "extracted data",
        }
        with _claude_returns(response):
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "success"
        assert len(result.outputs_written) == 1
        assert result.failure_reason is None
        assert result.failure_category is None

    def test_run_id_propagated_to_written_artifact(self, skill_env: Path) -> None:
        """§14 test 4: run_id is correctly threaded into canonical artifact writes."""
        response = {
            "schema_id": "test_output_v1",
            "run_id": "run-abc-123",
            "result": "data",
        }
        with _claude_returns(response):
            result = run_skill("test-skill", "run-abc-123", skill_env)

        assert result.status == "success"
        written_path = skill_env / result.outputs_written[0]
        content = json.loads(written_path.read_text(encoding="utf-8"))
        assert content["run_id"] == "run-abc-123"

    def test_artifact_status_absent_in_written_artifact(self, skill_env: Path) -> None:
        """Written artifacts must not contain artifact_status (runner-stamped post-gate)."""
        response = {
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "data",
        }
        with _claude_returns(response):
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "success"
        written_path = skill_env / result.outputs_written[0]
        content = json.loads(written_path.read_text(encoding="utf-8"))
        assert "artifact_status" not in content

    def test_schema_id_in_written_artifact(self, skill_env: Path) -> None:
        response = {
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "data",
        }
        with _claude_returns(response):
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "success"
        written_path = skill_env / result.outputs_written[0]
        content = json.loads(written_path.read_text(encoding="utf-8"))
        assert content["schema_id"] == "test_output_v1"


# ---------------------------------------------------------------------------
# run_skill — missing input
# ---------------------------------------------------------------------------


class TestRunSkillMissingInput:
    def test_missing_input_file(self, skill_env: Path) -> None:
        """Missing input → MISSING_INPUT failure without calling Claude."""
        # Remove the input file
        (skill_env / "docs" / "tier3" / "input.json").unlink()

        with patch(_TRANSPORT_TARGET) as mock_transport:
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"
        mock_transport.assert_not_called()  # Claude not invoked

    def test_unknown_skill_id(self, skill_env: Path) -> None:
        result = run_skill("nonexistent-skill", "run-001", skill_env)
        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"


# ---------------------------------------------------------------------------
# run_skill — malformed Claude response
# ---------------------------------------------------------------------------


class TestRunSkillMalformedResponse:
    def test_non_json_response(self, skill_env: Path) -> None:
        """Non-JSON Claude response → INCOMPLETE_OUTPUT, no artifact at canonical path."""
        canonical = skill_env / "docs" / "tier4" / "phase1" / "test_output.json"
        assert not canonical.exists()

        with _claude_returns_text("This is not JSON at all"):
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
        assert not canonical.exists(), "No partial artifact at canonical path"

    def test_transport_failure(self, skill_env: Path) -> None:
        """Claude transport failure → INCOMPLETE_OUTPUT."""
        with _claude_fails("Connection timeout"):
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"


# ---------------------------------------------------------------------------
# run_skill — cli-prompt timeout diagnostics
# ---------------------------------------------------------------------------


class TestCliPromptTimeoutDiagnostics:
    """Verify that cli-prompt timeout failures write a rich diagnostic bundle."""

    def test_timeout_returns_failure_result(self, skill_env: Path) -> None:
        """Timeout still produces a failure SkillResult (contract preserved)."""
        with _claude_times_out():
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
        assert "timed out" in result.failure_reason

    def test_timeout_failure_reason_includes_diag_path(self, skill_env: Path) -> None:
        """Failure reason must include a pointer to the diagnostic file."""
        with _claude_times_out():
            result = run_skill("test-skill", "run-001", skill_env)

        assert ".claude/skill_diag/" in result.failure_reason
        assert "timeout_meta.json" in result.failure_reason

    def test_timeout_writes_meta_json(self, skill_env: Path) -> None:
        """Timeout must write a timeout_meta.json with all required fields."""
        with _claude_times_out(timeout_seconds=300, stderr="some warning"):
            run_skill("test-skill", "run-001", skill_env)

        meta_path = (
            skill_env / ".claude" / "skill_diag"
            / "test-skill_run-001_timeout_meta.json"
        )
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        assert meta["skill_id"] == "test-skill"
        assert meta["execution_mode"] == "cli-prompt"
        assert meta["run_id"] == "run-001"
        assert meta["timeout_seconds"] == 300
        assert isinstance(meta["elapsed_seconds"], float)
        assert isinstance(meta["system_prompt_size"], int)
        assert meta["system_prompt_size"] > 0
        assert isinstance(meta["user_prompt_size"], int)
        assert meta["user_prompt_size"] > 0
        assert meta["model"] is not None
        assert meta["max_tokens"] is not None
        assert isinstance(meta["command"], list)
        assert isinstance(meta["reads_from"], list)
        assert isinstance(meta["writes_to"], list)
        assert isinstance(meta["had_partial_stdout"], bool)
        assert meta["had_stderr"] is True
        assert isinstance(meta["diagnostic_files"], dict)

    def test_timeout_writes_prompt_files(self, skill_env: Path) -> None:
        """Timeout must write system_prompt.txt and user_prompt.txt."""
        with _claude_times_out():
            run_skill("test-skill", "run-001", skill_env)

        diag_dir = skill_env / ".claude" / "skill_diag"
        sys_path = diag_dir / "test-skill_run-001_system_prompt.txt"
        usr_path = diag_dir / "test-skill_run-001_user_prompt.txt"
        assert sys_path.exists()
        assert usr_path.exists()
        assert len(sys_path.read_text(encoding="utf-8")) > 0
        assert len(usr_path.read_text(encoding="utf-8")) > 0

    def test_timeout_writes_stdout_stderr_files(self, skill_env: Path) -> None:
        """stdout and stderr files are always written (even if empty)."""
        with _claude_times_out(stdout="partial data", stderr="warn"):
            run_skill("test-skill", "run-001", skill_env)

        diag_dir = skill_env / ".claude" / "skill_diag"
        stdout_path = diag_dir / "test-skill_run-001_stdout.txt"
        stderr_path = diag_dir / "test-skill_run-001_stderr.txt"
        assert stdout_path.exists()
        assert stdout_path.read_text(encoding="utf-8") == "partial data"
        assert stderr_path.exists()
        assert stderr_path.read_text(encoding="utf-8") == "warn"

    def test_timeout_with_node_id(self, skill_env: Path) -> None:
        """node_id is recorded in meta when provided."""
        with _claude_times_out():
            run_skill("test-skill", "run-001", skill_env, node_id="n01_call_analysis")

        meta_path = (
            skill_env / ".claude" / "skill_diag"
            / "test-skill_run-001_timeout_meta.json"
        )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["node_id"] == "n01_call_analysis"

    def test_non_timeout_transport_error_no_diagnostic_bundle(self, skill_env: Path) -> None:
        """Generic transport errors should NOT write timeout diagnostic files."""
        with _claude_fails("Connection reset"):
            run_skill("test-skill", "run-001", skill_env)

        meta_path = (
            skill_env / ".claude" / "skill_diag"
            / "test-skill_run-001_timeout_meta.json"
        )
        assert not meta_path.exists()


# ---------------------------------------------------------------------------
# run_skill — schema validation failure
# ---------------------------------------------------------------------------


class TestRunSkillSchemaValidation:
    def test_missing_run_id_in_response(self, skill_env: Path) -> None:
        """Response without run_id → MALFORMED_ARTIFACT."""
        response = {
            "schema_id": "test_output_v1",
            "result": "data",
            # run_id intentionally missing
        }
        canonical = skill_env / "docs" / "tier4" / "phase1" / "test_output.json"

        with _claude_returns(response):
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert not canonical.exists()

    def test_wrong_run_id_in_response(self, skill_env: Path) -> None:
        """Response with wrong run_id → MALFORMED_ARTIFACT."""
        response = {
            "schema_id": "test_output_v1",
            "run_id": "wrong-run-id",
            "result": "data",
        }
        with _claude_returns(response):
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_artifact_status_present_in_response(self, skill_env: Path) -> None:
        """Response with artifact_status → MALFORMED_ARTIFACT."""
        response = {
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "data",
            "artifact_status": "valid",
        }
        with _claude_returns(response):
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"


# ---------------------------------------------------------------------------
# §14 test 5 — canonical input binding
# ---------------------------------------------------------------------------


class TestCanonicalInputBinding:
    def test_file_input_resolved_from_disk(self, skill_env: Path) -> None:
        """Canonical input paths are resolved relative to repo_root."""
        response = {
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "processed",
        }
        with _claude_returns(response) as mock_transport:
            result = run_skill("test-skill", "run-001", skill_env)

        assert result.status == "success"
        # Verify Claude was called (inputs were resolved and passed)
        mock_transport.assert_called_once()

    def test_caller_provided_inputs_override_disk(self, skill_env: Path) -> None:
        """Pre-resolved inputs dict overrides reading from disk."""
        response = {
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "from-caller",
        }
        caller_inputs = {
            "docs/tier3/input.json": {"overridden": True},
        }
        with _claude_returns(response):
            result = run_skill(
                "test-skill", "run-001", skill_env, inputs=caller_inputs
            )

        assert result.status == "success"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestValidateSkillInputs:
    def test_all_present(self, skill_env: Path) -> None:
        resolved = {
            "docs/tier3/input.json": {"topic": "test"},
        }
        errors = _validate_skill_inputs(
            "test-skill",
            ["docs/tier3/input.json"],
            skill_env,
            resolved,
        )
        assert errors == []

    def test_missing_file(self, skill_env: Path) -> None:
        errors = _validate_skill_inputs(
            "test-skill",
            ["docs/tier3/missing.json"],
            skill_env,
            {},
        )
        assert len(errors) > 0

    def test_empty_object_allowed_for_upsert_target(self, skill_env: Path) -> None:
        """Empty {} is valid when the file is also in writes_to (upsert pattern)."""
        upsert_path = "docs/tier2a/extracted/registry.json"
        abs_path = skill_env / upsert_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text("{}", encoding="utf-8")
        resolved = {upsert_path: {}}
        errors = _validate_skill_inputs(
            "test-skill",
            [upsert_path],
            skill_env,
            resolved,
            writes_to=[upsert_path],
        )
        assert errors == []

    def test_empty_object_rejected_when_not_upsert_target(self, skill_env: Path) -> None:
        """Empty {} is still an error when the file is NOT in writes_to."""
        readonly_path = "docs/tier2a/extracted/registry.json"
        abs_path = skill_env / readonly_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text("{}", encoding="utf-8")
        resolved = {readonly_path: {}}
        errors = _validate_skill_inputs(
            "test-skill",
            [readonly_path],
            skill_env,
            resolved,
            writes_to=["docs/some/other/output.json"],
        )
        assert len(errors) == 1
        assert "empty object" in errors[0]

    def test_empty_object_rejected_when_writes_to_not_provided(self, skill_env: Path) -> None:
        """Backward compatibility: no writes_to arg means strict validation."""
        readonly_path = "docs/tier2a/extracted/registry.json"
        abs_path = skill_env / readonly_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text("{}", encoding="utf-8")
        resolved = {readonly_path: {}}
        errors = _validate_skill_inputs(
            "test-skill",
            [readonly_path],
            skill_env,
            resolved,
        )
        assert len(errors) == 1
        assert "empty object" in errors[0]


class TestValidateSkillOutput:
    def test_valid_output(self) -> None:
        errors = _validate_skill_output(
            {"schema_id": "s1", "run_id": "r1", "data": "x"},
            run_id="r1",
            expected_schema_id="s1",
            required_fields=["data"],
        )
        assert errors == []

    def test_missing_run_id(self) -> None:
        errors = _validate_skill_output(
            {"schema_id": "s1", "data": "x"},
            run_id="r1",
            expected_schema_id="s1",
            required_fields=None,
        )
        assert any("run_id" in e for e in errors)

    def test_artifact_status_forbidden(self) -> None:
        errors = _validate_skill_output(
            {"run_id": "r1", "artifact_status": "valid"},
            run_id="r1",
            expected_schema_id=None,
            required_fields=None,
        )
        assert any("artifact_status" in e for e in errors)


class TestExtractJsonResponse:
    def test_bare_json(self) -> None:
        assert _extract_json_response('{"key": "value"}') == {"key": "value"}

    def test_markdown_fenced(self) -> None:
        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        assert _extract_json_response(text) == {"key": "value"}

    def test_non_json(self) -> None:
        assert _extract_json_response("This is not JSON") is None

    def test_array_rejected(self) -> None:
        assert _extract_json_response("[1, 2, 3]") is None


class TestAtomicWrite:
    def test_success(self, tmp_path: Path) -> None:
        target = tmp_path / "output.json"
        err = _atomic_write({"key": "val"}, target)
        assert err is None
        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["key"] == "val"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested" / "output.json"
        err = _atomic_write({"a": 1}, target)
        assert err is None
        assert target.exists()

    def test_atomic_no_partial_on_failure(self, tmp_path: Path) -> None:
        """If the write fails, no file remains at the canonical path."""
        target = tmp_path / "output.json"
        # Write something that will fail atomically by patching os.write
        with patch("runner.skill_runtime.os.write", side_effect=OSError("disk full")):
            err = _atomic_write({"a": 1}, target)
        assert err is not None
        assert not target.exists()


# ---------------------------------------------------------------------------
# Multi-artifact response shape: canonical-path-keyed
# ---------------------------------------------------------------------------


def _make_multi_artifact_env(tmp_path: Path) -> Path:
    """Create a synthetic environment for multi-artifact skill tests."""
    repo_root = tmp_path

    _write_skill_catalog(repo_root, [
        {
            "id": "multi-skill",
            "reads_from": ["docs/tier3/input.json"],
            "writes_to": ["docs/tier2b/extracted/"],
            "constitutional_constraints": [],
        },
    ])

    # Two artifacts in the same directory
    _write_artifact_schema(repo_root, {
        "tier2b_extracted_schemas": {
            "call_constraints": {
                "canonical_path": "docs/tier2b/extracted/call_constraints.json",
                "fields": {
                    "constraints": {"required": True},
                },
            },
            "expected_outcomes": {
                "canonical_path": "docs/tier2b/extracted/expected_outcomes.json",
                "fields": {
                    "outcomes": {"required": True},
                },
            },
        }
    })

    _write_skill_spec(repo_root, "multi-skill")

    input_path = repo_root / "docs" / "tier3" / "input.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(json.dumps({"topic": "test"}), encoding="utf-8")

    (repo_root / "docs" / "tier2b" / "extracted").mkdir(parents=True, exist_ok=True)
    return repo_root


@pytest.fixture()
def multi_env(tmp_path: Path) -> Path:
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    return _make_multi_artifact_env(tmp_path)


class TestMultiArtifactCanonicalPathKeys:
    """Multi-artifact writer accepts full canonical-path-keyed responses."""

    def test_canonical_path_keyed_response(self, multi_env: Path) -> None:
        """Claude returns full repo-relative paths as top-level keys."""
        response = {
            "docs/tier2b/extracted/call_constraints.json": {
                "constraints": [{"id": "c1", "text": "constraint"}]
            },
            "docs/tier2b/extracted/expected_outcomes.json": {
                "outcomes": [{"id": "o1", "text": "outcome"}]
            },
        }
        with _claude_returns(response):
            result = run_skill("multi-skill", "run-001", multi_env)

        assert result.status == "success"
        assert len(result.outputs_written) == 2

        c_path = multi_env / "docs/tier2b/extracted/call_constraints.json"
        o_path = multi_env / "docs/tier2b/extracted/expected_outcomes.json"
        assert c_path.exists()
        assert o_path.exists()
        c_data = json.loads(c_path.read_text(encoding="utf-8"))
        assert "constraints" in c_data
        o_data = json.loads(o_path.read_text(encoding="utf-8"))
        assert "outcomes" in o_data

    def test_flat_shape_still_works(self, multi_env: Path) -> None:
        """Flat root-field shape is still accepted (regression guard)."""
        response = {
            "constraints": [{"id": "c1", "text": "constraint"}],
            "outcomes": [{"id": "o1", "text": "outcome"}],
        }
        with _claude_returns(response):
            result = run_skill("multi-skill", "run-001", multi_env)

        assert result.status == "success"
        assert len(result.outputs_written) == 2

    def test_basename_keyed_still_works(self, multi_env: Path) -> None:
        """Basename-keyed shape is still accepted (regression guard)."""
        response = {
            "call_constraints.json": {
                "constraints": [{"id": "c1"}]
            },
            "expected_outcomes.json": {
                "outcomes": [{"id": "o1"}]
            },
        }
        with _claude_returns(response):
            result = run_skill("multi-skill", "run-001", multi_env)

        assert result.status == "success"
        assert len(result.outputs_written) == 2

    def test_stem_keyed_still_works(self, multi_env: Path) -> None:
        """Stem-keyed shape (no .json) is still accepted (regression guard)."""
        response = {
            "call_constraints": {
                "constraints": [{"id": "c1"}]
            },
            "expected_outcomes": {
                "outcomes": [{"id": "o1"}]
            },
        }
        with _claude_returns(response):
            result = run_skill("multi-skill", "run-001", multi_env)

        assert result.status == "success"
        assert len(result.outputs_written) == 2


# ---------------------------------------------------------------------------
# Multi-target writes_to — independent output directories/files
# ---------------------------------------------------------------------------


def _make_multi_target_env(tmp_path: Path) -> Path:
    """Create an environment where one skill writes to two independent targets.

    Target A: docs/tier4/phase1/ (directory) → call_analysis_summary.json
    Target B: docs/tier2a/extracted/evaluator_expectation_registry.json (file)
    """
    repo_root = tmp_path

    _write_skill_catalog(repo_root, [
        {
            "id": "multi-target-skill",
            "reads_from": ["docs/tier3/input.json"],
            "writes_to": [
                "docs/tier4/phase1/",
                "docs/tier2a/extracted/evaluator_expectation_registry.json",
            ],
            "constitutional_constraints": [],
        },
    ])

    _write_artifact_schema(repo_root, {
        "tier4_phase_output_schemas": {
            "call_analysis_summary": {
                "canonical_path": "docs/tier4/phase1/call_analysis_summary.json",
                "schema_id_value": "orch.phase1.call_analysis_summary.v1",
                "fields": {
                    "schema_id": {"required": True},
                    "run_id": {"required": True},
                    "resolved_instrument_type": {"required": True},
                    "evaluation_matrix": {"required": True},
                    "compliance_checklist": {"required": True},
                },
            },
        },
        "tier2a_extracted_schemas": {
            "evaluator_expectation_registry": {
                "canonical_path": "docs/tier2a/extracted/evaluator_expectation_registry.json",
                "fields": {
                    "instruments": {"required": True},
                },
            },
        },
    })

    _write_skill_spec(repo_root, "multi-target-skill")

    input_path = repo_root / "docs" / "tier3" / "input.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(json.dumps({"topic": "test"}), encoding="utf-8")

    (repo_root / "docs" / "tier4" / "phase1").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "tier2a" / "extracted").mkdir(parents=True, exist_ok=True)
    return repo_root


@pytest.fixture()
def multi_target_env(tmp_path: Path) -> Path:
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    return _make_multi_target_env(tmp_path)


class TestMultiTargetWritesTo:
    """Tests for skills that write to multiple independent writes_to targets.

    Target A is a multi-field artifact (call_analysis_summary.json) with
    schema_id, run_id, resolved_instrument_type, evaluation_matrix,
    compliance_checklist.

    Target B is a single-root-field artifact (evaluator_expectation_registry.json)
    with only instruments.
    """

    def _full_response(self) -> dict:
        """Complete flat response with all required fields for both targets."""
        return {
            "schema_id": "orch.phase1.call_analysis_summary.v1",
            "run_id": "run-001",
            "resolved_instrument_type": "RIA",
            "evaluation_matrix": {"EXC": {"criterion_id": "EXC"}},
            "compliance_checklist": [{"requirement_id": "CR-01"}],
            "instruments": [{"instrument_type": "RIA", "criteria": []}],
        }

    def test_flat_mixed_response_both_written(self, multi_target_env: Path) -> None:
        """Flat response with top-level metadata + domain fields + instruments."""
        response = self._full_response()
        with _claude_returns(response):
            result = run_skill("multi-target-skill", "run-001", multi_target_env)

        assert result.status == "success"
        assert len(result.outputs_written) == 2

        # Verify both files exist on disk
        t4_path = multi_target_env / "docs/tier4/phase1/call_analysis_summary.json"
        t2a_path = multi_target_env / "docs/tier2a/extracted/evaluator_expectation_registry.json"
        assert t4_path.exists()
        assert t2a_path.exists()

        # Verify multi-field artifact has ALL domain fields
        t4_data = json.loads(t4_path.read_text(encoding="utf-8"))
        assert t4_data["evaluation_matrix"] == {"EXC": {"criterion_id": "EXC"}}
        assert t4_data["compliance_checklist"] == [{"requirement_id": "CR-01"}]
        assert t4_data["resolved_instrument_type"] == "RIA"
        assert t4_data["schema_id"] == "orch.phase1.call_analysis_summary.v1"
        assert t4_data["run_id"] == "run-001"

        # Verify single-root-field artifact
        t2a_data = json.loads(t2a_path.read_text(encoding="utf-8"))
        assert "instruments" in t2a_data

    def test_nested_keyed_multi_field_target(self, multi_target_env: Path) -> None:
        """Canonical-path-keyed shape for the multi-field target."""
        response = {
            "docs/tier4/phase1/call_analysis_summary.json": {
                "schema_id": "orch.phase1.call_analysis_summary.v1",
                "run_id": "run-001",
                "resolved_instrument_type": "RIA",
                "evaluation_matrix": {"EXC": {"criterion_id": "EXC"}},
                "compliance_checklist": [{"requirement_id": "CR-01"}],
            },
            "instruments": [{"instrument_type": "RIA", "criteria": []}],
        }
        with _claude_returns(response):
            result = run_skill("multi-target-skill", "run-001", multi_target_env)

        assert result.status == "success"
        assert len(result.outputs_written) == 2

        t4_data = json.loads(
            (multi_target_env / "docs/tier4/phase1/call_analysis_summary.json")
            .read_text(encoding="utf-8")
        )
        assert t4_data["evaluation_matrix"] == {"EXC": {"criterion_id": "EXC"}}
        assert t4_data["compliance_checklist"] == [{"requirement_id": "CR-01"}]

    def test_missing_field_in_multi_field_target(self, multi_target_env: Path) -> None:
        """Omit compliance_checklist from multi-field target; fails validation."""
        response = {
            "schema_id": "orch.phase1.call_analysis_summary.v1",
            "run_id": "run-001",
            "resolved_instrument_type": "RIA",
            "evaluation_matrix": {"EXC": {"criterion_id": "EXC"}},
            # Missing: "compliance_checklist"
            "instruments": [{"instrument_type": "RIA", "criteria": []}],
        }
        with _claude_returns(response):
            result = run_skill("multi-target-skill", "run-001", multi_target_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "compliance_checklist" in result.failure_reason

    def test_missing_second_target_fails(self, multi_target_env: Path) -> None:
        """Claude returns only first target's artifact; fails MALFORMED_ARTIFACT."""
        response = {
            "schema_id": "orch.phase1.call_analysis_summary.v1",
            "run_id": "run-001",
            "resolved_instrument_type": "RIA",
            "evaluation_matrix": {"EXC": {"criterion_id": "EXC"}},
            "compliance_checklist": [{"requirement_id": "CR-01"}],
            # Missing: "instruments" key for the second target
        }
        with _claude_returns(response):
            result = run_skill("multi-target-skill", "run-001", multi_target_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_missing_first_target_fails(self, multi_target_env: Path) -> None:
        """Claude returns only second target's artifact; fails MALFORMED_ARTIFACT."""
        response = {
            "instruments": [{"instrument_type": "RIA", "criteria": []}],
            # Missing: all domain fields for the multi-field target
        }
        with _claude_returns(response):
            result = run_skill("multi-target-skill", "run-001", multi_target_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"


# ---------------------------------------------------------------------------
# Module isolation
# ---------------------------------------------------------------------------


class TestModuleIsolation:
    def test_no_dag_scheduler_import(self) -> None:
        import runner.skill_runtime as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "runner.dag_scheduler" not in source
        assert "runner.gate_evaluator" not in source

    def test_no_anthropic_import(self) -> None:
        """After transport migration, skill_runtime must not import anthropic."""
        import runner.skill_runtime as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import anthropic" not in source
