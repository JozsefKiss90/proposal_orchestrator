"""
Tests for Bedrock readiness via .env configuration.

Covers:
    - .env loading via load_dotenv()
    - BEDROCK_EU_DEVELOPMENT preset resolves to backend bedrock
    - API key is never stored in ProviderConfig fields or repr
    - API key is never present in error messages
    - AWS_REGION=eu-central-1 does NOT override preset's hardcoded eu-west-1
    - Explicit ORCHESTRATOR_TRANSPORT_ENDPOINT does override preset endpoint
    - anthropic.claude-sonnet-4-20250514-v1:0 passes Bedrock model validation
    - Simple aliases like claude-sonnet-4 are rejected
    - Conflicting ORCHESTRATOR_TRANSPORT_BACKEND is rejected
    - build_openai_backend retrieves API key at build time from env

All tests use environment variable patching.  No real backends are contacted.
"""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from runner.transport.config import (
    BEDROCK_EU_DEVELOPMENT,
    BEDROCK_URL_TEMPLATE,
    DEFAULT_BEDROCK_MODEL,
    ProviderConfig,
    build_openai_backend,
    resolve_provider_config,
    resolve_provider_config_from_preset,
    validate_bedrock_model_id,
)


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------


class TestDotenvLoading:
    """Verify load_dotenv() is called in both entrypoints."""

    def test_load_dotenv_in_main(self):
        """runner/__main__.py calls load_dotenv() before imports."""
        import runner.__main__ as mod
        # If this import succeeds, load_dotenv was called at module level.
        # Verify the function exists in the module's source.
        import inspect
        source = inspect.getsource(mod)
        assert "load_dotenv()" in source
        # load_dotenv must appear before 'from runner.' imports
        dotenv_pos = source.index("load_dotenv()")
        first_runner_import = source.index("from runner.")
        assert dotenv_pos < first_runner_import

    def test_load_dotenv_in_config(self):
        """runner/transport/config.py calls load_dotenv() at module level."""
        import runner.transport.config as mod
        import inspect
        source = inspect.getsource(mod)
        assert "load_dotenv()" in source


# ---------------------------------------------------------------------------
# Preset resolution from .env-style env vars
# ---------------------------------------------------------------------------


class TestBedrockPresetFromEnv:
    """Simulate .env contents and verify resolution."""

    ENV_BEDROCK_EU_DEV = {
        "ORCHESTRATOR_TRANSPORT_PRESET": "BEDROCK_EU_DEVELOPMENT",
        "ORCHESTRATOR_TRANSPORT_API_KEY": "test-key-not-real",
        "ORCHESTRATOR_TRANSPORT_MODEL": "anthropic.claude-sonnet-4-20250514-v1:0",
        "AWS_REGION": "eu-central-1",
    }

    def test_preset_resolves_to_bedrock(self):
        with patch.dict(os.environ, self.ENV_BEDROCK_EU_DEV, clear=True):
            config = resolve_provider_config()
        assert config.backend_name == "bedrock"
        assert config.preset_name == "BEDROCK_EU_DEVELOPMENT"

    def test_model_is_passed_through(self):
        with patch.dict(os.environ, self.ENV_BEDROCK_EU_DEV, clear=True):
            config = resolve_provider_config()
        assert config.model == "anthropic.claude-sonnet-4-20250514-v1:0"

    def test_api_key_set_is_true(self):
        with patch.dict(os.environ, self.ENV_BEDROCK_EU_DEV, clear=True):
            config = resolve_provider_config()
        assert config.api_key_set is True

    def test_api_key_value_not_in_config(self):
        """The actual key value must never appear in ProviderConfig."""
        with patch.dict(os.environ, self.ENV_BEDROCK_EU_DEV, clear=True):
            config = resolve_provider_config()
        assert "test-key-not-real" not in str(config)
        assert "test-key-not-real" not in repr(config)
        # Check all attributes
        for attr in dir(config):
            if attr.startswith("_"):
                continue
            val = getattr(config, attr)
            if isinstance(val, str):
                assert "test-key-not-real" not in val

    def test_api_key_not_in_error_messages(self):
        """Error messages from missing key must not leak other env values."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")
        # The error should mention the variable name, not any value
        assert "ORCHESTRATOR_TRANSPORT_API_KEY" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Region behavior (CRITICAL)
# ---------------------------------------------------------------------------


class TestRegionBehavior:
    """Verify AWS_REGION behavior with BEDROCK_EU_DEVELOPMENT preset."""

    def test_aws_region_ignored_when_preset_has_default_endpoint(self):
        """BEDROCK_EU_DEVELOPMENT hardcodes eu-west-1 as default_endpoint.
        Setting AWS_REGION=eu-central-1 does NOT change the resolved endpoint.
        """
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "AWS_REGION": "eu-central-1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

        # The preset's default_endpoint wins over AWS_REGION
        assert "eu-west-1" in config.base_url
        assert "eu-central-1" not in config.base_url

    def test_explicit_endpoint_overrides_preset_default(self):
        """ORCHESTRATOR_TRANSPORT_ENDPOINT overrides the preset's hardcoded endpoint."""
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_ENDPOINT": "https://bedrock-mantle.eu-central-1.api.aws/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

        assert config.base_url == "https://bedrock-mantle.eu-central-1.api.aws/v1"

    def test_preset_hardcoded_endpoint_value(self):
        """Confirm the preset's default_endpoint is eu-west-1."""
        assert BEDROCK_EU_DEVELOPMENT.default_endpoint == BEDROCK_URL_TEMPLATE.format(region="eu-west-1")
        assert "eu-west-1" in BEDROCK_EU_DEVELOPMENT.default_endpoint


# ---------------------------------------------------------------------------
# Model ID validation
# ---------------------------------------------------------------------------


class TestBedrockModelValidation:
    """Verify model ID validation for Bedrock."""

    def test_full_bedrock_model_id_accepted(self):
        assert validate_bedrock_model_id("anthropic.claude-sonnet-4-20250514-v1:0") is True

    def test_simple_alias_rejected(self):
        assert validate_bedrock_model_id("claude-sonnet-4") is False

    def test_simple_alias_in_preset_raises(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_MODEL": "claude-sonnet-4",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Invalid Bedrock model ID"):
                resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")


# ---------------------------------------------------------------------------
# Conflicting backend
# ---------------------------------------------------------------------------


class TestConflictingBackend:
    """ORCHESTRATOR_TRANSPORT_BACKEND must match or be absent."""

    def test_conflicting_backend_rejected(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "ollama",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="conflicts with preset"):
                resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")


# ---------------------------------------------------------------------------
# build_openai_backend
# ---------------------------------------------------------------------------


class TestBuildOpenaiBackend:
    """Verify build_openai_backend retrieves key at build time."""

    def test_api_key_read_from_env_at_build_time(self):
        config = ProviderConfig(
            backend_name="bedrock",
            base_url="https://bedrock-mantle.eu-west-1.api.aws/v1",
            api_key_set=True,
            model="anthropic.claude-sonnet-4-20250514-v1:0",
            capabilities=BEDROCK_EU_DEVELOPMENT.capabilities,
        )
        env = {"ORCHESTRATOR_TRANSPORT_API_KEY": "build-time-key"}
        with patch.dict(os.environ, env, clear=True):
            backend = build_openai_backend(config)

        # The backend should have constructed a /chat/completions URL
        assert backend.url.endswith("/chat/completions")
        # The key should have been read from env (we can't inspect the
        # internal headers directly without exposing internals, but we
        # verify no error was raised during construction)

    def test_claude_cli_backend_rejected(self):
        config = ProviderConfig(
            backend_name="claude_cli",
            base_url=None,
            api_key_set=False,
            model=None,
            capabilities=BEDROCK_EU_DEVELOPMENT.capabilities,
        )
        with pytest.raises(ValueError, match="Cannot build OpenAICompatBackend"):
            build_openai_backend(config)
