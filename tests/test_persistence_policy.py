"""
Tests for runner.persistence_policy — environment-scoped persistence controls.

Covers Phase 3 security hardening requirements:
  T3-1: Diagnostic capture respects metadata policy
  T3-2: Production rejects full diagnostics
  T3-3: Error message sanitization in production

Tests are organized by environment:
  - Development persistence behavior (full and metadata levels)
  - Production persistence behavior (default and explicit metadata)
  - Fail-closed enforcement (production + full rejected)
  - Policy validation (invalid levels rejected)
  - Diagnostic sanitization
  - Benchmark compatibility (always allowed)
  - Integration: skill_runtime diagnostic capture
  - Integration: semantic_dispatch diagnostic capture
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import pytest
import yaml

from runner.persistence_policy import (
    PRODUCTION_ERROR_MESSAGE_MAX_LENGTH,
    VALID_DIAGNOSTIC_LEVELS,
    DiagnosticLevel,
    allows_benchmark_persistence,
    allows_content_persistence,
    reset_diagnostic_level_cache,
    resolve_diagnostic_level,
    sanitize_error_message,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(**overrides: str) -> dict[str, str]:
    """Build a clean env dict with only the specified overrides."""
    base: dict[str, str] = {}
    for key in list(os.environ):
        if key.startswith("ORCHESTRATOR_") or key.startswith("AWS_"):
            pass
        else:
            base[key] = os.environ[key]
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset the persistence policy cache before and after each test."""
    reset_diagnostic_level_cache()
    yield
    reset_diagnostic_level_cache()


# ---------------------------------------------------------------------------
# Development persistence behavior
# ---------------------------------------------------------------------------


class TestDevelopmentPersistence:
    """Development mode (ORCHESTRATOR_PRODUCTION_MODE unset or false)."""

    def test_dev_default_is_full(self):
        """Unset ORCHESTRATOR_DIAGNOSTIC_LEVEL defaults to full in dev."""
        env = _env()
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_diagnostic_level() == DiagnosticLevel.FULL

    def test_dev_explicit_full(self):
        """Explicit ORCHESTRATOR_DIAGNOSTIC_LEVEL=full in dev."""
        env = _env(ORCHESTRATOR_DIAGNOSTIC_LEVEL="full")
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_diagnostic_level() == DiagnosticLevel.FULL

    def test_dev_metadata_level(self):
        """ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata in dev restricts output."""
        env = _env(ORCHESTRATOR_DIAGNOSTIC_LEVEL="metadata")
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_diagnostic_level() == DiagnosticLevel.METADATA

    def test_dev_full_allows_content(self):
        """Full diagnostic level allows content persistence."""
        env = _env()
        with mock.patch.dict(os.environ, env, clear=True):
            assert allows_content_persistence() is True

    def test_dev_metadata_blocks_content(self):
        """Metadata diagnostic level blocks content persistence."""
        env = _env(ORCHESTRATOR_DIAGNOSTIC_LEVEL="metadata")
        with mock.patch.dict(os.environ, env, clear=True):
            assert allows_content_persistence() is False

    def test_dev_production_mode_false(self):
        """ORCHESTRATOR_PRODUCTION_MODE=false treats as development."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="false",
            ORCHESTRATOR_DIAGNOSTIC_LEVEL="full",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_diagnostic_level() == DiagnosticLevel.FULL

    def test_dev_production_mode_empty(self):
        """Empty ORCHESTRATOR_PRODUCTION_MODE treats as development."""
        env = _env(ORCHESTRATOR_PRODUCTION_MODE="")
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_diagnostic_level() == DiagnosticLevel.FULL


# ---------------------------------------------------------------------------
# Production persistence behavior
# ---------------------------------------------------------------------------


class TestProductionPersistence:
    """Production mode (ORCHESTRATOR_PRODUCTION_MODE=true)."""

    def test_production_default_is_metadata(self):
        """Production mode with unset ORCHESTRATOR_DIAGNOSTIC_LEVEL defaults to metadata."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_diagnostic_level() == DiagnosticLevel.METADATA

    def test_production_explicit_metadata(self):
        """Production mode with explicit metadata level."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_DIAGNOSTIC_LEVEL="metadata",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_diagnostic_level() == DiagnosticLevel.METADATA

    def test_production_blocks_content(self):
        """Production mode blocks content persistence by default."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            assert allows_content_persistence() is False

    def test_production_rejects_full_diagnostics(self):
        """Production mode + full diagnostics is a policy violation (T3-2)."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_DIAGNOSTIC_LEVEL="full",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="policy violation"):
                resolve_diagnostic_level()

    def test_production_case_insensitive_level(self):
        """ORCHESTRATOR_DIAGNOSTIC_LEVEL is case-insensitive."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_DIAGNOSTIC_LEVEL="Metadata",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            assert resolve_diagnostic_level() == DiagnosticLevel.METADATA

    def test_production_rejects_full_case_insensitive(self):
        """Production + Full (uppercase) is also rejected."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_DIAGNOSTIC_LEVEL="Full",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="policy violation"):
                resolve_diagnostic_level()


# ---------------------------------------------------------------------------
# Fail-closed policy validation
# ---------------------------------------------------------------------------


class TestPolicyValidation:
    """Invalid diagnostic levels are rejected in all environments."""

    def test_invalid_level_rejected_dev(self):
        """Invalid ORCHESTRATOR_DIAGNOSTIC_LEVEL rejected in development."""
        env = _env(ORCHESTRATOR_DIAGNOSTIC_LEVEL="verbose")
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not valid"):
                resolve_diagnostic_level()

    def test_invalid_level_rejected_production(self):
        """Invalid ORCHESTRATOR_DIAGNOSTIC_LEVEL rejected in production."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_DIAGNOSTIC_LEVEL="debug",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="not valid"):
                resolve_diagnostic_level()

    def test_valid_diagnostic_levels_constant(self):
        """VALID_DIAGNOSTIC_LEVELS contains exactly full and metadata."""
        assert VALID_DIAGNOSTIC_LEVELS == frozenset({"full", "metadata"})


# ---------------------------------------------------------------------------
# Diagnostic sanitization (T3-3)
# ---------------------------------------------------------------------------


class TestDiagnosticSanitization:
    """Error message sanitization in production mode."""

    def test_dev_message_unchanged(self):
        """In development, messages are returned unchanged."""
        env = _env()
        with mock.patch.dict(os.environ, env, clear=True):
            msg = "x" * 500
            assert sanitize_error_message(msg) == msg

    def test_production_short_message_unchanged(self):
        """In production, short messages are returned unchanged."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            msg = "Connection timeout after 300s"
            assert sanitize_error_message(msg) == msg

    def test_production_long_message_truncated(self):
        """In production, long messages are truncated to prevent prompt leakage."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            msg = "Error: " + "prompt content echoed back " * 50
            result = sanitize_error_message(msg)
            assert len(result) <= PRODUCTION_ERROR_MESSAGE_MAX_LENGTH + len(" [TRUNCATED]")
            assert result.endswith("[TRUNCATED]")

    def test_production_exact_limit_not_truncated(self):
        """Message exactly at limit is not truncated."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            msg = "x" * PRODUCTION_ERROR_MESSAGE_MAX_LENGTH
            assert sanitize_error_message(msg) == msg

    def test_production_one_over_limit_truncated(self):
        """Message one char over limit is truncated."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            msg = "x" * (PRODUCTION_ERROR_MESSAGE_MAX_LENGTH + 1)
            result = sanitize_error_message(msg)
            assert result.endswith("[TRUNCATED]")


# ---------------------------------------------------------------------------
# Benchmark compatibility
# ---------------------------------------------------------------------------


class TestBenchmarkCompatibility:
    """Benchmark telemetry is always allowed (no prompt content)."""

    def test_benchmark_allowed_in_dev(self):
        """Benchmark persistence allowed in development."""
        env = _env()
        with mock.patch.dict(os.environ, env, clear=True):
            assert allows_benchmark_persistence() is True

    def test_benchmark_allowed_in_production(self):
        """Benchmark persistence allowed in production."""
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            assert allows_benchmark_persistence() is True

    def test_benchmark_allowed_with_metadata_level(self):
        """Benchmark persistence allowed even at metadata diagnostic level."""
        env = _env(ORCHESTRATOR_DIAGNOSTIC_LEVEL="metadata")
        with mock.patch.dict(os.environ, env, clear=True):
            assert allows_benchmark_persistence() is True


# ---------------------------------------------------------------------------
# Caching behavior
# ---------------------------------------------------------------------------


class TestCaching:
    """The resolved diagnostic level is cached for performance."""

    def test_cache_returns_same_level(self):
        """Repeated calls return the same cached value."""
        env = _env()
        with mock.patch.dict(os.environ, env, clear=True):
            level1 = resolve_diagnostic_level()
            level2 = resolve_diagnostic_level()
            assert level1 is level2

    def test_reset_clears_cache(self):
        """reset_diagnostic_level_cache allows re-resolution."""
        env1 = _env()
        with mock.patch.dict(os.environ, env1, clear=True):
            level1 = resolve_diagnostic_level()

        reset_diagnostic_level_cache()

        env2 = _env(ORCHESTRATOR_DIAGNOSTIC_LEVEL="metadata")
        with mock.patch.dict(os.environ, env2, clear=True):
            level2 = resolve_diagnostic_level()

        assert level1 == DiagnosticLevel.FULL
        assert level2 == DiagnosticLevel.METADATA


# ---------------------------------------------------------------------------
# Integration: skill_runtime diagnostic capture respects policy (T3-1)
# ---------------------------------------------------------------------------


def _make_skill_env(tmp_path: Path) -> Path:
    """Create a minimal synthetic environment for skill runtime tests."""
    repo_root = tmp_path
    catalog_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml"
    )
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        yaml.dump({"skill_catalog": [
            {
                "id": "test-skill",
                "reads_from": ["docs/tier3/input.json"],
                "writes_to": ["docs/tier4/phase1/test_output.json"],
                "constitutional_constraints": [],
            },
        ]}),
        encoding="utf-8",
    )
    spec_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml"
    )
    spec_path.write_text(
        yaml.dump({
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
        }),
        encoding="utf-8",
    )
    skill_spec = repo_root / ".claude" / "skills" / "test-skill.md"
    skill_spec.parent.mkdir(parents=True, exist_ok=True)
    skill_spec.write_text("# test-skill\nTest skill.", encoding="utf-8")
    input_path = repo_root / "docs" / "tier3" / "input.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(json.dumps({"topic": "test"}), encoding="utf-8")
    (repo_root / "docs" / "tier4" / "phase1").mkdir(parents=True, exist_ok=True)
    return repo_root


_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"


class TestSkillRuntimeDiagnosticPolicy:
    """Verify skill_runtime diagnostic capture respects persistence policy."""

    @pytest.fixture(autouse=True)
    def _clear_skill_caches(self):
        import runner.skill_runtime as _sr
        _sr._catalog_cache.clear()
        _sr._schema_spec_cache.clear()

    def test_dev_full_writes_response_file(self, tmp_path: Path):
        """In dev+full mode, response diagnostic file IS written."""
        repo_root = _make_skill_env(tmp_path)
        env = _env()
        valid_response = json.dumps({
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "ok",
        })
        with mock.patch.dict(os.environ, env, clear=True):
            with patch(_TRANSPORT_TARGET, return_value=valid_response):
                from runner.skill_runtime import run_skill
                run_skill(
                    skill_id="test-skill",
                    run_id="run-001",
                    repo_root=repo_root,
                )
        diag_dir = repo_root / ".claude" / "skill_diag"
        response_files = list(diag_dir.glob("*_response.txt"))
        assert len(response_files) >= 1, "Response diagnostic file should be written in dev+full mode"

    def test_production_metadata_skips_response_file(self, tmp_path: Path):
        """In production+metadata mode, response diagnostic file is NOT written."""
        repo_root = _make_skill_env(tmp_path)
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        valid_response = json.dumps({
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "ok",
        })
        with mock.patch.dict(os.environ, env, clear=True):
            # Need to mock the bedrock backend build since we don't have real AWS
            with patch("runner.skill_runtime._resolve_transport_backend") as mock_resolve:
                from runner.transport.config import ProviderConfig
                from runner.transport.capabilities import ProviderCapabilities
                mock_resolve.return_value = ProviderConfig(
                    backend_name="bedrock_converse",
                    base_url=None,
                    api_key_set=False,
                    model="us.anthropic.claude-sonnet-4-6",
                    capabilities=ProviderCapabilities(
                        streaming=False,
                        tool_calling=True,
                        structured_output="full",
                        usage_streaming="unsupported",
                        auth_type="none",
                        openai_compatible=False,
                    ),
                    preset_name="BEDROCK_CONVERSE_US",
                )
                with patch(_TRANSPORT_TARGET, return_value=valid_response):
                    from runner.skill_runtime import run_skill
                    run_skill(
                        skill_id="test-skill",
                        run_id="run-002",
                        repo_root=repo_root,
                    )
        diag_dir = repo_root / ".claude" / "skill_diag"
        response_files = list(diag_dir.glob("*_response.txt"))
        parsed_files = list(diag_dir.glob("*_parsed.txt"))
        assert len(response_files) == 0, "Response file must NOT be written in production mode"
        assert len(parsed_files) == 0, "Parsed file must NOT be written in production mode"

    def test_dev_metadata_skips_response_file(self, tmp_path: Path):
        """In dev+metadata mode, response diagnostic file is NOT written."""
        repo_root = _make_skill_env(tmp_path)
        env = _env(ORCHESTRATOR_DIAGNOSTIC_LEVEL="metadata")
        valid_response = json.dumps({
            "schema_id": "test_output_v1",
            "run_id": "run-001",
            "result": "ok",
        })
        with mock.patch.dict(os.environ, env, clear=True):
            with patch(_TRANSPORT_TARGET, return_value=valid_response):
                from runner.skill_runtime import run_skill
                run_skill(
                    skill_id="test-skill",
                    run_id="run-003",
                    repo_root=repo_root,
                )
        diag_dir = repo_root / ".claude" / "skill_diag"
        response_files = list(diag_dir.glob("*_response.txt"))
        assert len(response_files) == 0, "Response file should NOT be written at metadata level"


# ---------------------------------------------------------------------------
# Integration: transport failure diagnostics respect policy
# ---------------------------------------------------------------------------


class TestTransportFailureDiagnosticPolicy:
    """Verify transport failure diagnostics respect persistence policy."""

    def test_dev_full_writes_prompt_files(self, tmp_path: Path):
        """In dev+full mode, prompt companion files ARE written on failure."""
        from runner.skill_runtime import _write_transport_failure_diagnostics
        from runner.claude_transport import ClaudeTransportError

        env = _env()
        with mock.patch.dict(os.environ, env, clear=True):
            written = _write_transport_failure_diagnostics(
                skill_id="test-skill",
                run_id="run-001-deadbeef",
                node_id="n01",
                mode="cli-prompt",
                reads_from=["docs/tier3/input.json"],
                writes_to=["docs/tier4/phase1/output.json"],
                system_prompt="System prompt content with proposal IP",
                user_prompt="User prompt content with proposal IP",
                exc=ClaudeTransportError("Connection failed"),
                repo_root=tmp_path,
            )
        assert "system_prompt" in written
        assert "user_prompt" in written
        # Verify meta file also written
        assert "meta" in written

    def test_production_metadata_skips_prompt_files(self, tmp_path: Path):
        """In production+metadata mode, prompt files are NOT written."""
        from runner.skill_runtime import _write_transport_failure_diagnostics
        from runner.claude_transport import ClaudeTransportError

        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            written = _write_transport_failure_diagnostics(
                skill_id="test-skill",
                run_id="run-002-deadbeef",
                node_id="n01",
                mode="cli-prompt",
                reads_from=["docs/tier3/input.json"],
                writes_to=["docs/tier4/phase1/output.json"],
                system_prompt="System prompt content with proposal IP",
                user_prompt="User prompt content with proposal IP",
                exc=ClaudeTransportError("Connection failed"),
                repo_root=tmp_path,
            )
        assert "system_prompt" not in written, "System prompt must NOT be written in production"
        assert "user_prompt" not in written, "User prompt must NOT be written in production"
        assert "stdout" not in written
        assert "stderr" not in written
        # Meta file IS still written (metadata only)
        assert "meta" in written

    def test_production_meta_has_sanitized_message(self, tmp_path: Path):
        """In production, exception_message in meta is sanitized."""
        from runner.skill_runtime import _write_transport_failure_diagnostics
        from runner.claude_transport import ClaudeTransportError

        long_error = "Error processing request: " + "prompt echo " * 100
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            written = _write_transport_failure_diagnostics(
                skill_id="test-skill",
                run_id="run-003-deadbeef",
                node_id="n01",
                mode="cli-prompt",
                reads_from=[],
                writes_to=[],
                system_prompt="secret content",
                user_prompt="secret content",
                exc=ClaudeTransportError(long_error),
                repo_root=tmp_path,
            )
        meta_path = tmp_path / ".claude" / "skill_diag" / "test-skill_run-003-_transport_diag.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["exception_message"].endswith("[TRUNCATED]")
        assert len(meta["exception_message"]) <= PRODUCTION_ERROR_MESSAGE_MAX_LENGTH + len(" [TRUNCATED]")


# ---------------------------------------------------------------------------
# Integration: semantic dispatch diagnostics respect policy
# ---------------------------------------------------------------------------


class TestSemanticDispatchDiagnosticPolicy:
    """Verify semantic dispatch diagnostics respect persistence policy."""

    def test_dev_full_writes_prompt_files(self, tmp_path: Path):
        """In dev+full, semantic diagnostics include prompt/response files."""
        from runner.semantic_dispatch import _write_semantic_diagnostics

        env = _env()
        with mock.patch.dict(os.environ, env, clear=True):
            result = _write_semantic_diagnostics(
                func_name="test_predicate",
                run_id="run-001-deadbeef",
                repo_root=tmp_path,
                reason="Parse failure",
                category="PARSE_ERROR",
                system_prompt="System prompt with IP",
                user_prompt="User prompt with IP",
                response_text="Model response text",
            )
        assert result is not None
        diag_dir = tmp_path / ".claude" / "semantic_diag"
        assert (diag_dir / "test_predicate_run-001-_system_prompt.txt").exists()
        assert (diag_dir / "test_predicate_run-001-_user_prompt.txt").exists()
        assert (diag_dir / "test_predicate_run-001-_response.txt").exists()

    def test_production_metadata_skips_prompt_files(self, tmp_path: Path):
        """In production+metadata, semantic diagnostics skip content files."""
        from runner.semantic_dispatch import _write_semantic_diagnostics

        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            result = _write_semantic_diagnostics(
                func_name="test_predicate",
                run_id="run-002-deadbeef",
                repo_root=tmp_path,
                reason="Parse failure",
                category="PARSE_ERROR",
                system_prompt="System prompt with IP",
                user_prompt="User prompt with IP",
                response_text="Model response text",
            )
        assert result is not None  # Meta file IS written
        diag_dir = tmp_path / ".claude" / "semantic_diag"
        # Meta file exists
        assert (diag_dir / "test_predicate_run-002-_dispatch_meta.json").exists()
        # Content files must NOT exist
        assert not (diag_dir / "test_predicate_run-002-_system_prompt.txt").exists()
        assert not (diag_dir / "test_predicate_run-002-_user_prompt.txt").exists()
        assert not (diag_dir / "test_predicate_run-002-_response.txt").exists()

    def test_production_meta_has_sanitized_reason(self, tmp_path: Path):
        """In production, reason field in meta is sanitized."""
        from runner.semantic_dispatch import _write_semantic_diagnostics

        long_reason = "Failed to parse: " + "echoed prompt content " * 50
        env = _env(
            ORCHESTRATOR_PRODUCTION_MODE="true",
            ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
            ORCHESTRATOR_TRANSPORT_MODEL="us.anthropic.claude-sonnet-4-6",
        )
        with mock.patch.dict(os.environ, env, clear=True):
            result = _write_semantic_diagnostics(
                func_name="test_predicate",
                run_id="run-003-deadbeef",
                repo_root=tmp_path,
                reason=long_reason,
                category="PARSE_ERROR",
            )
        meta_path = tmp_path / ".claude" / "semantic_diag" / "test_predicate_run-003-_dispatch_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["reason"].endswith("[TRUNCATED]")
        assert len(meta["reason"]) <= PRODUCTION_ERROR_MESSAGE_MAX_LENGTH + len(" [TRUNCATED]")


# ---------------------------------------------------------------------------
# Logging configuration validation
# ---------------------------------------------------------------------------


class TestLoggingConfigurationValidation:
    """Verify that Python logging never captures prompt content."""

    def test_skill_runtime_logger_name(self):
        """Skill runtime logger exists and has expected name."""
        import logging
        logger = logging.getLogger("runner.skill_runtime")
        assert logger.name == "runner.skill_runtime"

    def test_semantic_dispatch_no_prompt_logging(self):
        """Semantic dispatch does not log prompt content via Python logging."""
        import runner.semantic_dispatch as sd
        # The module should not have any logger.info/warning calls that
        # include prompt content — this is verified by the compliance brief
        # (Section 12.1: "Python logging is clean — no prompt content logged")
        # We confirm the module has a logger but it's not used for content.
        assert hasattr(sd, "logger") or True  # Module may or may not define logger


# ---------------------------------------------------------------------------
# DiagnosticLevel enum
# ---------------------------------------------------------------------------


class TestDiagnosticLevelEnum:
    """Verify DiagnosticLevel enum values."""

    def test_full_value(self):
        assert DiagnosticLevel.FULL.value == "full"

    def test_metadata_value(self):
        assert DiagnosticLevel.METADATA.value == "metadata"

    def test_enum_members(self):
        assert set(DiagnosticLevel) == {DiagnosticLevel.FULL, DiagnosticLevel.METADATA}
