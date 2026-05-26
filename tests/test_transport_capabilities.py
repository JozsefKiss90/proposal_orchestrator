"""
Tests for ``runner.transport.capabilities`` — provider capability metadata.

Covers:
    - ProviderCapabilities frozen dataclass
    - Pre-defined capability sets (bedrock, together_ai, ollama, claude_cli)
    - CAPABILITIES_REGISTRY completeness
    - Bedrock-specific capability values per validation report
"""

from __future__ import annotations

import pytest

from runner.transport.capabilities import (
    BEDROCK_CAPABILITIES,
    CAPABILITIES_REGISTRY,
    CLAUDE_CLI_CAPABILITIES,
    GENERIC_OPENAI_CAPABILITIES,
    OLLAMA_CAPABILITIES,
    TOGETHER_AI_CAPABILITIES,
    ProviderCapabilities,
)


# ---------------------------------------------------------------------------
# Test: Frozen dataclass
# ---------------------------------------------------------------------------


class TestProviderCapabilitiesDataclass:
    """ProviderCapabilities is a frozen dataclass."""

    def test_is_frozen(self):
        with pytest.raises(AttributeError):
            BEDROCK_CAPABILITIES.streaming = False  # type: ignore[misc]

    def test_equality(self):
        cap1 = ProviderCapabilities(
            streaming=True, tool_calling=True, structured_output="full",
            usage_streaming="confirmed", auth_type="bearer", openai_compatible=True,
        )
        cap2 = ProviderCapabilities(
            streaming=True, tool_calling=True, structured_output="full",
            usage_streaming="confirmed", auth_type="bearer", openai_compatible=True,
        )
        assert cap1 == cap2


# ---------------------------------------------------------------------------
# Test: Bedrock capabilities
# ---------------------------------------------------------------------------


class TestBedrockCapabilities:
    """Bedrock capability values match validation report."""

    def test_streaming(self):
        assert BEDROCK_CAPABILITIES.streaming is True

    def test_tool_calling(self):
        assert BEDROCK_CAPABILITIES.tool_calling is True

    def test_structured_output_model_dependent(self):
        assert BEDROCK_CAPABILITIES.structured_output == "model_dependent"

    def test_usage_streaming_unverified(self):
        """Per validation report: stream_options.include_usage is UNVERIFIED."""
        assert BEDROCK_CAPABILITIES.usage_streaming == "unverified"

    def test_auth_type_bearer(self):
        assert BEDROCK_CAPABILITIES.auth_type == "bearer"

    def test_openai_compatible(self):
        assert BEDROCK_CAPABILITIES.openai_compatible is True


# ---------------------------------------------------------------------------
# Test: Other provider capabilities
# ---------------------------------------------------------------------------


class TestOtherProviderCapabilities:
    """Other providers have expected capability values."""

    def test_together_ai_usage_streaming_confirmed(self):
        assert TOGETHER_AI_CAPABILITIES.usage_streaming == "confirmed"

    def test_ollama_no_auth(self):
        assert OLLAMA_CAPABILITIES.auth_type == "none"

    def test_claude_cli_not_openai_compatible(self):
        assert CLAUDE_CLI_CAPABILITIES.openai_compatible is False

    def test_claude_cli_cli_subscription_auth(self):
        assert CLAUDE_CLI_CAPABILITIES.auth_type == "cli_subscription"

    def test_generic_openai_bearer_auth(self):
        assert GENERIC_OPENAI_CAPABILITIES.auth_type == "bearer"


# ---------------------------------------------------------------------------
# Test: Registry
# ---------------------------------------------------------------------------


class TestCapabilitiesRegistry:
    """CAPABILITIES_REGISTRY covers all valid backend names."""

    def test_registry_keys(self):
        from runner.transport.config import VALID_BACKENDS
        assert set(CAPABILITIES_REGISTRY.keys()) == VALID_BACKENDS

    def test_all_values_are_provider_capabilities(self):
        for name, caps in CAPABILITIES_REGISTRY.items():
            assert isinstance(caps, ProviderCapabilities), f"{name} is not ProviderCapabilities"
