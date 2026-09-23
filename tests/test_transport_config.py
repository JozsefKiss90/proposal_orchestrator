"""
Tests for ``runner.transport.config`` — provider configuration resolution.

Covers:
    - Bedrock config resolution (URL, model ID, API key)
    - Together AI config resolution
    - Ollama config resolution
    - Generic openai_compatible config resolution
    - Claude CLI default
    - Invalid backend rejection
    - Bedrock model ID validation
    - Missing credential errors
    - API key never stored in ProviderConfig
    - Default URL construction from AWS_REGION

All tests use environment variable patching.  No real backends are contacted.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from runner.transport.config import (
    DEFAULT_AWS_REGION,
    DEFAULT_BEDROCK_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_TOGETHER_AI_URL,
    VALID_BACKENDS,
    ProviderConfig,
    resolve_provider_config,
    validate_bedrock_model_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(**overrides: str) -> dict[str, str]:
    """Build a clean environment dict with only the specified overrides."""
    return overrides


# ---------------------------------------------------------------------------
# Test: Default backend
# ---------------------------------------------------------------------------


class TestDefaultBackend:
    """Default backend is claude_cli when no env vars are set."""

    def test_default_is_claude_cli(self):
        with patch.dict(os.environ, {}, clear=True):
            config = resolve_provider_config()
        assert config.backend_name == "claude_cli"
        assert config.base_url is None
        assert config.api_key_set is False

    def test_claude_cli_capabilities(self):
        with patch.dict(os.environ, {}, clear=True):
            config = resolve_provider_config()
        assert config.capabilities.openai_compatible is False
        assert config.capabilities.auth_type == "cli_subscription"


# ---------------------------------------------------------------------------
# Test: Invalid backend
# ---------------------------------------------------------------------------


class TestInvalidBackend:
    """Invalid backend names are rejected."""

    def test_invalid_backend_raises(self):
        with patch.dict(os.environ, {"ORCHESTRATOR_TRANSPORT_BACKEND": "gpt4all"}, clear=True):
            with pytest.raises(ValueError, match="Invalid backend"):
                resolve_provider_config()

    def test_valid_backends_listed_in_error(self):
        with patch.dict(os.environ, {"ORCHESTRATOR_TRANSPORT_BACKEND": "nope"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                resolve_provider_config()
            # All valid backends should be mentioned
            for name in VALID_BACKENDS:
                assert name in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test: Bedrock config
# ---------------------------------------------------------------------------


class TestBedrockConfig:
    """Bedrock provider configuration resolution."""

    def test_bedrock_with_explicit_endpoint(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_ENDPOINT": "https://bedrock-mantle.us-east-1.api.aws/v1",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "br-key-123",
            "ORCHESTRATOR_TRANSPORT_MODEL": "anthropic.claude-sonnet-4-20250514-v1:0",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.backend_name == "bedrock"
        assert config.base_url == "https://bedrock-mantle.us-east-1.api.aws/v1"
        assert config.model == "anthropic.claude-sonnet-4-20250514-v1:0"
        assert config.api_key_set is True

    def test_bedrock_default_url_from_aws_region(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "br-key-123",
            "AWS_REGION": "eu-central-1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.base_url == "https://bedrock-mantle.eu-central-1.api.aws/v1"

    def test_bedrock_default_url_uses_eu_west_1(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "br-key-123",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.base_url == f"https://bedrock-mantle.{DEFAULT_AWS_REGION}.api.aws/v1"

    def test_bedrock_default_model(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "br-key-123",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.model == DEFAULT_BEDROCK_MODEL

    def test_bedrock_missing_api_key_raises(self):
        env = {"ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="ORCHESTRATOR_TRANSPORT_API_KEY is required"):
                resolve_provider_config()

    def test_bedrock_invalid_model_id_raises(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "br-key-123",
            "ORCHESTRATOR_TRANSPORT_MODEL": "claude-sonnet-4",  # missing provider prefix
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Invalid Bedrock model ID"):
                resolve_provider_config()

    def test_bedrock_capabilities(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "br-key-123",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.capabilities.openai_compatible is True
        assert config.capabilities.tool_calling is True
        assert config.capabilities.streaming is True
        assert config.capabilities.usage_streaming == "unverified"
        assert config.capabilities.auth_type == "bearer"
        assert config.capabilities.structured_output == "model_dependent"

    def test_api_key_value_not_in_config(self):
        """ProviderConfig must NOT contain the actual API key value."""
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "super-secret-key",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        # The config should only have api_key_set=True, never the value
        config_str = str(config)
        assert "super-secret-key" not in config_str
        assert config.api_key_set is True


# ---------------------------------------------------------------------------
# Test: Together AI config
# ---------------------------------------------------------------------------


class TestTogetherAIConfig:
    """Together AI provider configuration resolution."""

    def test_together_ai_with_defaults(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "together_ai",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "tai-key",
            "ORCHESTRATOR_TRANSPORT_MODEL": "meta-llama/Llama-3.1-405B",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.backend_name == "together_ai"
        assert config.base_url == DEFAULT_TOGETHER_AI_URL
        assert config.model == "meta-llama/Llama-3.1-405B"

    def test_together_ai_missing_api_key_raises(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "together_ai",
            "ORCHESTRATOR_TRANSPORT_MODEL": "test",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="ORCHESTRATOR_TRANSPORT_API_KEY is required"):
                resolve_provider_config()

    def test_together_ai_custom_endpoint(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "together_ai",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_ENDPOINT": "https://custom.together.ai/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.base_url == "https://custom.together.ai/v1"


# ---------------------------------------------------------------------------
# Test: Ollama config
# ---------------------------------------------------------------------------


class TestOllamaConfig:
    """Ollama provider configuration resolution."""

    def test_ollama_defaults(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "ollama",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.backend_name == "ollama"
        assert config.base_url == DEFAULT_OLLAMA_URL
        assert config.api_key_set is False

    def test_ollama_custom_endpoint(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "ollama",
            "ORCHESTRATOR_TRANSPORT_ENDPOINT": "http://gpu-server:11434/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.base_url == "http://gpu-server:11434/v1"

    def test_ollama_no_auth(self):
        env = {"ORCHESTRATOR_TRANSPORT_BACKEND": "ollama"}
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()
        assert config.capabilities.auth_type == "none"


# ---------------------------------------------------------------------------
# Test: Generic openai_compatible config
# ---------------------------------------------------------------------------


class TestGenericConfig:
    """Generic openai_compatible provider configuration."""

    def test_generic_requires_endpoint(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "openai_compatible",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="ORCHESTRATOR_TRANSPORT_ENDPOINT is required"):
                resolve_provider_config()

    def test_generic_with_all_vars(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "openai_compatible",
            "ORCHESTRATOR_TRANSPORT_ENDPOINT": "https://my-server/v1",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "my-key",
            "ORCHESTRATOR_TRANSPORT_MODEL": "my-model",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.backend_name == "openai_compatible"
        assert config.base_url == "https://my-server/v1"
        assert config.api_key_set is True
        assert config.model == "my-model"


# ---------------------------------------------------------------------------
# Test: Bedrock model ID validation
# ---------------------------------------------------------------------------


class TestBedrockModelIdValidation:
    """Bedrock model ID format validation."""

    @pytest.mark.parametrize(
        "model_id",
        [
            "anthropic.claude-sonnet-4-20250514-v1:0",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "meta.llama3-1-70b-instruct-v1:0",
            "deepseek.v3.2",
            "writer.palmyra-x5",
        ],
    )
    def test_valid_bedrock_model_ids(self, model_id: str):
        assert validate_bedrock_model_id(model_id) is True

    @pytest.mark.parametrize(
        "model_id",
        [
            "claude-sonnet-4",  # missing provider prefix
            "gpt-4o",  # no provider dot
            "",  # empty
            ".",  # just a dot
            "anthropic.",  # trailing dot only
            ".claude",  # leading dot
        ],
    )
    def test_invalid_bedrock_model_ids(self, model_id: str):
        assert validate_bedrock_model_id(model_id) is False
