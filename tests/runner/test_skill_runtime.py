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

from runner.claude_transport import ClaudeTransportError
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
