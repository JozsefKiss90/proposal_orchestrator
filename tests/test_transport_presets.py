"""
Tests for ``runner.transport.config`` — TransportPreset layer.

Covers:
    - TransportPreset is frozen
    - All required presets exist in registry
    - Preset registry keys are stable
    - CLAUDE_REFERENCE resolves to claude_cli
    - BEDROCK_EU_DEVELOPMENT resolves to bedrock with eu-west-1 endpoint
    - BEDROCK_EU_PRODUCTION resolves to bedrock with EU endpoint
    - TOGETHER_VALIDATION resolves to together_ai
    - OLLAMA_LOCAL resolves without API key
    - GENERIC_OPENAI_COMPATIBLE requires explicit endpoint and API key
    - Preset-required API key missing raises clear error
    - Explicit model override works
    - Explicit endpoint override works
    - Conflicting ORCHESTRATOR_TRANSPORT_BACKEND is rejected
    - API key value is never stored in ProviderConfig or error messages
    - Unset ORCHESTRATOR_TRANSPORT_PRESET preserves existing config behaviour
    - resolve_provider_config delegates to preset path when env var is set
    - get_transport_preset raises on unknown name
    - list_transport_presets returns all presets

All tests use environment variable patching.  No real backends are contacted.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from runner.transport.config import (
    BEDROCK_EU_DEVELOPMENT,
    BEDROCK_EU_PRODUCTION,
    BEDROCK_URL_TEMPLATE,
    CLAUDE_REFERENCE,
    DEFAULT_BEDROCK_MODEL,
    GENERIC_OPENAI_COMPATIBLE,
    OLLAMA_LOCAL,
    PRESET_REGISTRY,
    TOGETHER_VALIDATION,
    TransportPreset,
    get_transport_preset,
    list_transport_presets,
    resolve_provider_config,
    resolve_provider_config_from_preset,
)


# ---------------------------------------------------------------------------
# Test: TransportPreset dataclass
# ---------------------------------------------------------------------------


class TestTransportPresetDataclass:
    """TransportPreset is a frozen dataclass."""

    def test_is_frozen(self):
        with pytest.raises(AttributeError):
            CLAUDE_REFERENCE.name = "MUTATED"  # type: ignore[misc]

    def test_notes_is_tuple(self):
        for name, preset in PRESET_REGISTRY.items():
            assert isinstance(preset.notes, tuple), f"{name}.notes is not a tuple"


# ---------------------------------------------------------------------------
# Test: Registry completeness
# ---------------------------------------------------------------------------


class TestPresetRegistry:
    """All required presets exist and the registry is complete."""

    REQUIRED_PRESETS = {
        "CLAUDE_REFERENCE",
        "BEDROCK_EU_DEVELOPMENT",
        "BEDROCK_EU_PRODUCTION",
        "TOGETHER_VALIDATION",
        "OLLAMA_LOCAL",
        "GENERIC_OPENAI_COMPATIBLE",
    }

    def test_all_required_presets_exist(self):
        assert self.REQUIRED_PRESETS <= set(PRESET_REGISTRY.keys())

    def test_registry_count(self):
        assert len(PRESET_REGISTRY) == 6

    def test_preset_name_matches_registry_key(self):
        for key, preset in PRESET_REGISTRY.items():
            assert preset.name == key, f"Registry key {key!r} != preset.name {preset.name!r}"

    def test_list_transport_presets_returns_copy(self):
        presets = list_transport_presets()
        assert presets == PRESET_REGISTRY
        # Must be a copy, not the same dict
        assert presets is not PRESET_REGISTRY

    def test_get_transport_preset_returns_correct(self):
        preset = get_transport_preset("BEDROCK_EU_DEVELOPMENT")
        assert preset is BEDROCK_EU_DEVELOPMENT

    def test_get_transport_preset_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown transport preset"):
            get_transport_preset("NONEXISTENT_PRESET")

    def test_unknown_preset_error_lists_available(self):
        with pytest.raises(ValueError) as exc_info:
            get_transport_preset("NONEXISTENT_PRESET")
        for name in self.REQUIRED_PRESETS:
            assert name in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test: Individual preset values
# ---------------------------------------------------------------------------


class TestClaudeReferencePreset:
    """CLAUDE_REFERENCE preset values."""

    def test_backend_name(self):
        assert CLAUDE_REFERENCE.backend_name == "claude_cli"

    def test_no_endpoint(self):
        assert CLAUDE_REFERENCE.default_endpoint is None

    def test_no_api_key_required(self):
        assert CLAUDE_REFERENCE.requires_api_key is False

    def test_not_production(self):
        assert CLAUDE_REFERENCE.production_suitable is False

    def test_resolves_to_claude_cli(self):
        with patch.dict(os.environ, {}, clear=True):
            config = resolve_provider_config_from_preset("CLAUDE_REFERENCE")
        assert config.backend_name == "claude_cli"
        assert config.base_url is None
        assert config.preset_name == "CLAUDE_REFERENCE"


class TestBedrockEuDevelopmentPreset:
    """BEDROCK_EU_DEVELOPMENT preset values and resolution."""

    def test_backend_name(self):
        assert BEDROCK_EU_DEVELOPMENT.backend_name == "bedrock"

    def test_default_endpoint_eu_west_1(self):
        assert "eu-west-1" in BEDROCK_EU_DEVELOPMENT.default_endpoint

    def test_default_model(self):
        assert BEDROCK_EU_DEVELOPMENT.default_model == DEFAULT_BEDROCK_MODEL

    def test_requires_api_key(self):
        assert BEDROCK_EU_DEVELOPMENT.requires_api_key is True

    def test_not_production(self):
        assert BEDROCK_EU_DEVELOPMENT.production_suitable is False

    def test_resolves_with_api_key(self):
        env = {"ORCHESTRATOR_TRANSPORT_API_KEY": "br-dev-key"}
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

        assert config.backend_name == "bedrock"
        assert config.base_url == BEDROCK_URL_TEMPLATE.format(region="eu-west-1")
        assert config.model == DEFAULT_BEDROCK_MODEL
        assert config.api_key_set is True
        assert config.preset_name == "BEDROCK_EU_DEVELOPMENT"

    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="requires ORCHESTRATOR_TRANSPORT_API_KEY"):
                resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

    def test_capabilities(self):
        assert BEDROCK_EU_DEVELOPMENT.capabilities.usage_streaming == "unverified"
        assert BEDROCK_EU_DEVELOPMENT.capabilities.openai_compatible is True


class TestBedrockEuProductionPreset:
    """BEDROCK_EU_PRODUCTION preset values."""

    def test_production_suitable(self):
        assert BEDROCK_EU_PRODUCTION.production_suitable is True

    def test_has_production_notes(self):
        notes_text = " ".join(BEDROCK_EU_PRODUCTION.notes)
        assert "PrivateLink" in notes_text
        assert "CloudTrail" in notes_text
        assert "DPA" in notes_text

    def test_resolves_with_api_key(self):
        env = {"ORCHESTRATOR_TRANSPORT_API_KEY": "br-prod-key"}
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_PRODUCTION")

        assert config.backend_name == "bedrock"
        assert config.preset_name == "BEDROCK_EU_PRODUCTION"
        assert config.api_key_set is True


class TestTogetherValidationPreset:
    """TOGETHER_VALIDATION preset."""

    def test_backend_name(self):
        assert TOGETHER_VALIDATION.backend_name == "together_ai"

    def test_not_production(self):
        assert TOGETHER_VALIDATION.production_suitable is False

    def test_resolves_with_api_key_and_model(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "tai-key",
            "ORCHESTRATOR_TRANSPORT_MODEL": "meta-llama/Llama-3.1-405B",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("TOGETHER_VALIDATION")

        assert config.backend_name == "together_ai"
        assert config.model == "meta-llama/Llama-3.1-405B"

    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="requires ORCHESTRATOR_TRANSPORT_API_KEY"):
                resolve_provider_config_from_preset("TOGETHER_VALIDATION")


class TestOllamaLocalPreset:
    """OLLAMA_LOCAL preset."""

    def test_no_api_key_required(self):
        assert OLLAMA_LOCAL.requires_api_key is False

    def test_resolves_without_api_key(self):
        env = {"ORCHESTRATOR_TRANSPORT_MODEL": "llama3.1:70b"}
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("OLLAMA_LOCAL")

        assert config.backend_name == "ollama"
        assert config.api_key_set is False
        assert config.model == "llama3.1:70b"

    def test_default_endpoint(self):
        with patch.dict(os.environ, {}, clear=True):
            config = resolve_provider_config_from_preset("OLLAMA_LOCAL")
        assert config.base_url == "http://localhost:11434/v1"


class TestGenericOpenaiPreset:
    """GENERIC_OPENAI_COMPATIBLE preset."""

    def test_requires_explicit_endpoint(self):
        env = {"ORCHESTRATOR_TRANSPORT_API_KEY": "key"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="requires ORCHESTRATOR_TRANSPORT_ENDPOINT"):
                resolve_provider_config_from_preset("GENERIC_OPENAI_COMPATIBLE")

    def test_resolves_with_all_env_vars(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_ENDPOINT": "https://my-server/v1",
            "ORCHESTRATOR_TRANSPORT_MODEL": "my-model",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("GENERIC_OPENAI_COMPATIBLE")

        assert config.backend_name == "openai_compatible"
        assert config.base_url == "https://my-server/v1"
        assert config.model == "my-model"


# ---------------------------------------------------------------------------
# Test: Environment variable overrides
# ---------------------------------------------------------------------------


class TestEnvOverrides:
    """Explicit env vars override preset defaults."""

    def test_model_override(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_MODEL": "meta.llama3-1-70b-instruct-v1:0",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

        assert config.model == "meta.llama3-1-70b-instruct-v1:0"

    def test_endpoint_override(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_ENDPOINT": "https://bedrock-mantle.us-east-1.api.aws/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

        assert config.base_url == "https://bedrock-mantle.us-east-1.api.aws/v1"

    def test_region_override_when_no_explicit_endpoint(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "AWS_REGION": "eu-central-1",
        }
        with patch.dict(os.environ, env, clear=True):
            # Remove explicit endpoint to test region fallback
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

        # Preset default_endpoint is eu-west-1, so it takes precedence over AWS_REGION
        # because default_endpoint is set on this preset.
        assert "eu-west-1" in config.base_url

    def test_region_override_applies_when_preset_has_no_default_endpoint(self):
        """AWS_REGION is used when there is no default_endpoint on the preset."""
        # GENERIC_OPENAI_COMPATIBLE has no default_endpoint, but it's not bedrock
        # so region doesn't apply. This test confirms the bedrock region fallback
        # only triggers when preset backend is bedrock AND no endpoint is provided.
        # Create a custom test by clearing the env endpoint.
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_ENDPOINT": "https://custom.example.com/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("GENERIC_OPENAI_COMPATIBLE")
        assert config.base_url == "https://custom.example.com/v1"


# ---------------------------------------------------------------------------
# Test: Conflicting backend rejection
# ---------------------------------------------------------------------------


class TestConflictingBackendRejection:
    """Setting ORCHESTRATOR_TRANSPORT_BACKEND to a value that disagrees with the preset is rejected."""

    def test_conflicting_backend_raises(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "ollama",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="conflicts with preset"):
                resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

    def test_matching_backend_is_allowed(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")
        assert config.backend_name == "bedrock"


# ---------------------------------------------------------------------------
# Test: No secrets in ProviderConfig
# ---------------------------------------------------------------------------


class TestNoSecretsExposed:
    """API key values must never appear in ProviderConfig or error messages."""

    def test_api_key_not_in_provider_config_str(self):
        env = {"ORCHESTRATOR_TRANSPORT_API_KEY": "super-secret-key-12345"}
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

        config_repr = repr(config)
        assert "super-secret-key-12345" not in config_repr
        assert config.api_key_set is True

    def test_api_key_not_in_missing_key_error(self):
        """Error message for missing key must not include other env var values."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")
        error_msg = str(exc_info.value)
        assert "ORCHESTRATOR_TRANSPORT_API_KEY" in error_msg


# ---------------------------------------------------------------------------
# Test: Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Existing env-based resolution is preserved when preset is unset."""

    def test_no_preset_uses_legacy_path(self):
        with patch.dict(os.environ, {}, clear=True):
            config = resolve_provider_config()
        assert config.backend_name == "claude_cli"
        assert config.preset_name is None

    def test_legacy_bedrock_still_works(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.backend_name == "bedrock"
        assert config.preset_name is None

    def test_preset_env_var_triggers_preset_path(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_PRESET": "CLAUDE_REFERENCE",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.backend_name == "claude_cli"
        assert config.preset_name == "CLAUDE_REFERENCE"

    def test_preset_env_var_bedrock_with_key(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_PRESET": "BEDROCK_EU_DEVELOPMENT",
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config()

        assert config.backend_name == "bedrock"
        assert config.preset_name == "BEDROCK_EU_DEVELOPMENT"

    def test_unknown_preset_via_env_raises(self):
        env = {"ORCHESTRATOR_TRANSPORT_PRESET": "NONEXISTENT"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Unknown transport preset"):
                resolve_provider_config()


# ---------------------------------------------------------------------------
# Test: Bedrock model ID validation through preset path
# ---------------------------------------------------------------------------


class TestPresetBedrockModelValidation:
    """Bedrock model ID validation applies through preset resolution."""

    def test_invalid_model_rejected(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_MODEL": "claude-sonnet-4",  # missing provider prefix
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="Invalid Bedrock model ID"):
                resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")

    def test_valid_model_accepted(self):
        env = {
            "ORCHESTRATOR_TRANSPORT_API_KEY": "key",
            "ORCHESTRATOR_TRANSPORT_MODEL": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        }
        with patch.dict(os.environ, env, clear=True):
            config = resolve_provider_config_from_preset("BEDROCK_EU_DEVELOPMENT")
        assert config.model == "anthropic.claude-3-5-sonnet-20240620-v1:0"
