"""
Tests for Phase F TAPM tool emulation — skill runtime integration with
``run_tool_loop()`` for non-Claude OpenAI-compatible backends.

Covers:
    - TAPM skill dispatch via tool loop with FakeBackend
    - Capability gating: TAPM rejected when tool_calling=False
    - CLI-prompt skill dispatch via OpenAI-compatible backend
    - Empty response handling from tool loop
    - Transport backend resolution and caching
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from runner.runtime_models import SkillResult
from runner.skill_runtime import (
    _reset_transport_backend_cache,
    run_skill,
)
from runner.transport.capabilities import ProviderCapabilities
from runner.transport.config import ProviderConfig


# ---------------------------------------------------------------------------
# Fixtures — synthetic skill environment
# ---------------------------------------------------------------------------


def _write_skill_catalog(repo_root: Path, entries: list[dict]) -> None:
    catalog_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml"
    )
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        yaml.dump({"skill_catalog": entries}), encoding="utf-8"
    )


def _write_artifact_schema(repo_root: Path) -> None:
    spec_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml"
    )
    spec_path.parent.mkdir(parents=True, exist_ok=True)
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
            }
        },
    }
    spec_path.write_text(yaml.dump(schemas), encoding="utf-8")


def _write_skill_spec(repo_root: Path, skill_id: str, content: str = "") -> None:
    spec_path = repo_root / ".claude" / "skills" / f"{skill_id}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        content or f"# {skill_id}\nTest skill specification.",
        encoding="utf-8",
    )


def _make_tool_call(
    name: str,
    arguments: dict[str, Any],
    call_id: str = "call_1",
) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments),
        },
    }


TOOL_CALLING_CAPS = ProviderCapabilities(
    streaming=True,
    tool_calling=True,
    structured_output="partial",
    usage_streaming="unverified",
    auth_type="bearer",
    openai_compatible=True,
)

NO_TOOL_CALLING_CAPS = ProviderCapabilities(
    streaming=True,
    tool_calling=False,
    structured_output="partial",
    usage_streaming="unverified",
    auth_type="bearer",
    openai_compatible=True,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear skill runtime caches between tests."""
    from runner.skill_runtime import _catalog_cache, _schema_spec_cache
    _catalog_cache.clear()
    _schema_spec_cache.clear()
    _reset_transport_backend_cache()
    yield
    _catalog_cache.clear()
    _schema_spec_cache.clear()
    _reset_transport_backend_cache()


# ---------------------------------------------------------------------------
# Helper: build a fake OpenAI-compatible backend
# ---------------------------------------------------------------------------


def _make_fake_openai_backend(responses: list[dict[str, Any]]) -> MagicMock:
    """Build a mock that behaves like OpenAICompatBackend.__call__."""
    responses_iter = iter(responses)
    default_final = {"content": '{"status": "done"}', "tool_calls": None}

    def _call(messages: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            return next(responses_iter)
        except StopIteration:
            return default_final

    mock_backend = MagicMock()
    mock_backend.side_effect = _call
    return mock_backend


# ---------------------------------------------------------------------------
# Test: TAPM skill via tool loop with non-Claude backend
# ---------------------------------------------------------------------------


class TestTAPMToolLoopIntegration:
    """End-to-end tests for TAPM skills dispatched through run_tool_loop()."""

    def test_tapm_skill_via_tool_loop_success(self, tmp_path: Path) -> None:
        """TAPM skill on non-Claude backend: FakeBackend reads a file then
        returns valid artifact JSON. run_skill() writes the artifact."""
        repo_root = tmp_path

        # Set up skill environment
        _write_skill_catalog(repo_root, [
            {
                "id": "tapm-test",
                "execution_mode": "tapm",
                "reads_from": ["docs/tier3/data/"],
                "writes_to": ["docs/tier4/phase1/test_output.json"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(repo_root)
        _write_skill_spec(repo_root, "tapm-test")

        # Create input file
        data_dir = repo_root / "docs" / "tier3" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "input.json").write_text(
            '{"key": "value"}', encoding="utf-8"
        )

        run_id = "test-run-1234-5678-abcd-ef0123456789"

        # The valid artifact response the fake backend will return
        artifact_json = json.dumps({
            "schema_id": "test_output_v1",
            "run_id": run_id,
            "result": {"analysis": "complete"},
        })

        # Provider config for a non-Claude backend
        config = ProviderConfig(
            backend_name="together_ai",
            base_url="https://api.together.ai/v1",
            api_key_set=True,
            model="meta-llama/Llama-3.1-405B",
            capabilities=TOOL_CALLING_CAPS,
        )

        # Build the fake backend that reads a file then returns the artifact
        file_path = str(repo_root / "docs" / "tier3" / "data" / "input.json")
        fake_backend = _make_fake_openai_backend([
            # Round 1: model asks to read a file
            {
                "content": "",
                "tool_calls": [
                    _make_tool_call("Read", {"file_path": file_path}),
                ],
            },
            # Round 2: model returns the final artifact JSON
            {
                "content": artifact_json,
                "tool_calls": None,
            },
        ])

        with (
            patch(
                "runner.skill_runtime._resolve_transport_backend",
                return_value=config,
            ),
            patch(
                "runner.transport.config.build_openai_backend",
                return_value=fake_backend,
            ),
        ):
            result = run_skill(
                skill_id="tapm-test",
                run_id=run_id,
                repo_root=repo_root,
                node_id="n01_test",
            )

        assert result.status == "success"
        assert len(result.outputs_written) == 1
        assert "test_output.json" in result.outputs_written[0]

        # Verify the artifact was written to disk
        output_path = repo_root / "docs" / "tier4" / "phase1" / "test_output.json"
        assert output_path.exists()
        written = json.loads(output_path.read_text(encoding="utf-8"))
        assert written["schema_id"] == "test_output_v1"
        assert written["run_id"] == run_id
        assert written["result"] == {"analysis": "complete"}

    def test_tapm_capability_gating_rejects_incapable_backend(
        self, tmp_path: Path
    ) -> None:
        """TAPM skill fails immediately when backend has tool_calling=False."""
        repo_root = tmp_path

        _write_skill_catalog(repo_root, [
            {
                "id": "tapm-gated",
                "execution_mode": "tapm",
                "reads_from": ["docs/tier3/data/"],
                "writes_to": ["docs/tier4/phase1/test_output.json"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(repo_root)
        _write_skill_spec(repo_root, "tapm-gated")

        config = ProviderConfig(
            backend_name="ollama",
            base_url="http://localhost:11434/v1",
            api_key_set=False,
            model="llama3.1:7b",
            capabilities=NO_TOOL_CALLING_CAPS,
        )

        with patch(
            "runner.skill_runtime._resolve_transport_backend",
            return_value=config,
        ):
            result = run_skill(
                skill_id="tapm-gated",
                run_id="test-run-0000",
                repo_root=repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"
        assert "tool calling" in result.failure_reason.lower()
        assert "ollama" in result.failure_reason.lower()

    def test_tapm_tool_loop_empty_response(self, tmp_path: Path) -> None:
        """TAPM skill fails when tool loop returns empty text."""
        repo_root = tmp_path

        _write_skill_catalog(repo_root, [
            {
                "id": "tapm-empty",
                "execution_mode": "tapm",
                "reads_from": [],
                "writes_to": ["docs/tier4/phase1/test_output.json"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(repo_root)
        _write_skill_spec(repo_root, "tapm-empty")

        config = ProviderConfig(
            backend_name="together_ai",
            base_url="https://api.together.ai/v1",
            api_key_set=True,
            model="meta-llama/Llama-3.1-405B",
            capabilities=TOOL_CALLING_CAPS,
        )

        # Backend returns empty content immediately (no tool calls)
        fake_backend = _make_fake_openai_backend([
            {"content": "", "tool_calls": None},
        ])

        with (
            patch(
                "runner.skill_runtime._resolve_transport_backend",
                return_value=config,
            ),
            patch(
                "runner.transport.config.build_openai_backend",
                return_value=fake_backend,
            ),
        ):
            result = run_skill(
                skill_id="tapm-empty",
                run_id="test-run-0000",
                repo_root=repo_root,
            )

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
        assert "empty response" in result.failure_reason.lower()

    def test_tapm_claude_cli_path_unchanged(self, tmp_path: Path) -> None:
        """When backend is claude_cli, TAPM skills use invoke_claude_text
        (the existing path), not run_tool_loop."""
        repo_root = tmp_path

        _write_skill_catalog(repo_root, [
            {
                "id": "tapm-cli",
                "execution_mode": "tapm",
                "reads_from": [],
                "writes_to": ["docs/tier4/phase1/test_output.json"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(repo_root)
        _write_skill_spec(repo_root, "tapm-cli")

        run_id = "test-run-cli-path"
        artifact_json = json.dumps({
            "schema_id": "test_output_v1",
            "run_id": run_id,
            "result": {"from": "claude_cli"},
        })

        from runner.transport.capabilities import CLAUDE_CLI_CAPABILITIES

        config = ProviderConfig(
            backend_name="claude_cli",
            base_url=None,
            api_key_set=False,
            model=None,
            capabilities=CLAUDE_CLI_CAPABILITIES,
        )

        with (
            patch(
                "runner.skill_runtime._resolve_transport_backend",
                return_value=config,
            ),
            patch(
                "runner.skill_runtime.invoke_claude_text",
                return_value=artifact_json,
            ) as mock_invoke,
        ):
            result = run_skill(
                skill_id="tapm-cli",
                run_id=run_id,
                repo_root=repo_root,
            )

        assert result.status == "success"
        # invoke_claude_text was called (not run_tool_loop)
        assert mock_invoke.called
        call_kwargs = mock_invoke.call_args
        assert call_kwargs.kwargs.get("tools") == ["Read", "Glob"]


# ---------------------------------------------------------------------------
# Test: CLI-prompt skill via OpenAI-compatible backend
# ---------------------------------------------------------------------------


class TestCLIPromptOpenAICompatible:
    """Tests for cli-prompt skills dispatched through OpenAICompatBackend."""

    def test_cli_prompt_via_openai_backend_success(self, tmp_path: Path) -> None:
        """CLI-prompt skill on non-Claude backend: single-round call."""
        repo_root = tmp_path

        _write_skill_catalog(repo_root, [
            {
                "id": "cli-test",
                "execution_mode": "cli-prompt",
                "reads_from": ["docs/tier3/input.json"],
                "writes_to": ["docs/tier4/phase1/test_output.json"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(repo_root)
        _write_skill_spec(repo_root, "cli-test")

        # Create input file
        input_dir = repo_root / "docs" / "tier3"
        input_dir.mkdir(parents=True, exist_ok=True)
        (input_dir / "input.json").write_text(
            '{"data": "test"}', encoding="utf-8"
        )

        run_id = "test-run-cli-compat"
        artifact_json = json.dumps({
            "schema_id": "test_output_v1",
            "run_id": run_id,
            "result": {"from": "openai_backend"},
        })

        config = ProviderConfig(
            backend_name="together_ai",
            base_url="https://api.together.ai/v1",
            api_key_set=True,
            model="meta-llama/Llama-3.1-405B",
            capabilities=TOOL_CALLING_CAPS,
        )

        # Single-round backend: returns artifact JSON directly
        fake_backend = _make_fake_openai_backend([
            {"content": artifact_json, "tool_calls": None},
        ])

        with (
            patch(
                "runner.skill_runtime._resolve_transport_backend",
                return_value=config,
            ),
            patch(
                "runner.transport.config.build_openai_backend",
                return_value=fake_backend,
            ),
        ):
            result = run_skill(
                skill_id="cli-test",
                run_id=run_id,
                repo_root=repo_root,
            )

        assert result.status == "success"
        assert len(result.outputs_written) == 1

        # Verify artifact written correctly
        output_path = repo_root / "docs" / "tier4" / "phase1" / "test_output.json"
        assert output_path.exists()
        written = json.loads(output_path.read_text(encoding="utf-8"))
        assert written["result"] == {"from": "openai_backend"}

    def test_cli_prompt_claude_cli_path_unchanged(self, tmp_path: Path) -> None:
        """When backend is claude_cli, cli-prompt skills use
        invoke_claude_text (the existing path)."""
        repo_root = tmp_path

        _write_skill_catalog(repo_root, [
            {
                "id": "cli-original",
                "execution_mode": "cli-prompt",
                "reads_from": ["docs/tier3/input.json"],
                "writes_to": ["docs/tier4/phase1/test_output.json"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(repo_root)
        _write_skill_spec(repo_root, "cli-original")

        input_dir = repo_root / "docs" / "tier3"
        input_dir.mkdir(parents=True, exist_ok=True)
        (input_dir / "input.json").write_text(
            '{"data": "test"}', encoding="utf-8"
        )

        run_id = "test-run-cli-orig"
        artifact_json = json.dumps({
            "schema_id": "test_output_v1",
            "run_id": run_id,
            "result": {"from": "claude_cli"},
        })

        from runner.transport.capabilities import CLAUDE_CLI_CAPABILITIES

        config = ProviderConfig(
            backend_name="claude_cli",
            base_url=None,
            api_key_set=False,
            model=None,
            capabilities=CLAUDE_CLI_CAPABILITIES,
        )

        with (
            patch(
                "runner.skill_runtime._resolve_transport_backend",
                return_value=config,
            ),
            patch(
                "runner.skill_runtime.invoke_claude_text",
                return_value=artifact_json,
            ) as mock_invoke,
        ):
            result = run_skill(
                skill_id="cli-original",
                run_id=run_id,
                repo_root=repo_root,
            )

        assert result.status == "success"
        assert mock_invoke.called
        # cli-prompt does not pass tools
        call_kwargs = mock_invoke.call_args
        assert call_kwargs.kwargs.get("tools") is None


# ---------------------------------------------------------------------------
# Test: Transport backend resolution
# ---------------------------------------------------------------------------


class TestTransportBackendResolution:
    """Tests for _resolve_transport_backend() and cache behaviour."""

    def test_default_resolves_to_claude_cli(self) -> None:
        """With no env vars, resolves to claude_cli."""
        _reset_transport_backend_cache()
        with patch.dict(os.environ, {}, clear=False):
            # Remove any transport env vars
            for key in list(os.environ):
                if key.startswith("ORCHESTRATOR_TRANSPORT_"):
                    del os.environ[key]
            _reset_transport_backend_cache()
            from runner.skill_runtime import _resolve_transport_backend
            config = _resolve_transport_backend()
        assert config.backend_name == "claude_cli"

    def test_resolution_caches_result(self) -> None:
        """Second call returns cached config without re-resolving."""
        _reset_transport_backend_cache()
        from runner.skill_runtime import _resolve_transport_backend
        with patch(
            "runner.skill_runtime.resolve_provider_config"
        ) as mock_resolve:
            mock_resolve.return_value = ProviderConfig(
                backend_name="claude_cli",
                base_url=None,
                api_key_set=False,
                model=None,
                capabilities=TOOL_CALLING_CAPS,
            )
            c1 = _resolve_transport_backend()
            c2 = _resolve_transport_backend()
        assert c1 is c2
        assert mock_resolve.call_count == 1
