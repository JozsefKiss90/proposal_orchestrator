"""
Static provider capability metadata.

Declares per-provider feature surface as a frozen dataclass.  These are
static declarations consulted by the benchmark engine and error-handling
layer.  No dynamic capability detection or additional API calls.

Constitutional authority:
    Subordinate to CLAUDE.md.  This module declares provider metadata
    only.  It does not evaluate gates, invoke agents, write canonical
    artifacts, or modify scheduler state.

Authoritative source:
    docs/backend/phase_e_bedrock_validation_report.md (Validation E)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    """Static capability declaration for an LLM provider.

    All fields are static per-provider constants, not runtime-negotiated.

    Attributes
    ----------
    streaming:
        Provider supports SSE streaming responses.
    tool_calling:
        Provider supports client-side tool calling (OpenAI ``tools`` format).
    structured_output:
        Structured output / JSON mode support level.
        Values: ``"full"``, ``"partial"``, ``"model_dependent"``, ``"none"``.
    usage_streaming:
        Whether token usage is available in streaming responses.
        Values: ``"confirmed"``, ``"unverified"``, ``"unsupported"``.
    auth_type:
        Authentication mechanism.
        Values: ``"bearer"``, ``"none"``, ``"cli_subscription"``.
    openai_compatible:
        Provider exposes an OpenAI Chat Completions-compatible endpoint.
    """

    streaming: bool
    tool_calling: bool
    structured_output: str
    usage_streaming: str
    auth_type: str
    openai_compatible: bool


# ---------------------------------------------------------------------------
# Pre-defined capability sets
# ---------------------------------------------------------------------------

BEDROCK_CAPABILITIES = ProviderCapabilities(
    streaming=True,
    tool_calling=True,
    structured_output="model_dependent",
    usage_streaming="unverified",
    auth_type="bearer",
    openai_compatible=True,
)

TOGETHER_AI_CAPABILITIES = ProviderCapabilities(
    streaming=True,
    tool_calling=True,
    structured_output="partial",
    usage_streaming="confirmed",
    auth_type="bearer",
    openai_compatible=True,
)

OLLAMA_CAPABILITIES = ProviderCapabilities(
    streaming=True,
    tool_calling=True,
    structured_output="partial",
    usage_streaming="confirmed",
    auth_type="none",
    openai_compatible=True,
)

CLAUDE_CLI_CAPABILITIES = ProviderCapabilities(
    streaming=False,
    tool_calling=True,
    structured_output="full",
    usage_streaming="unsupported",
    auth_type="cli_subscription",
    openai_compatible=False,
)

GENERIC_OPENAI_CAPABILITIES = ProviderCapabilities(
    streaming=True,
    tool_calling=True,
    structured_output="partial",
    usage_streaming="unverified",
    auth_type="bearer",
    openai_compatible=True,
)

#: Lookup by backend name.
BEDROCK_CONVERSE_CAPABILITIES = ProviderCapabilities(
    streaming=False,
    tool_calling=True,
    structured_output="full",
    usage_streaming="unsupported",
    auth_type="iam",
    openai_compatible=False,
)

#: Lookup by backend name.
CAPABILITIES_REGISTRY: dict[str, ProviderCapabilities] = {
    "bedrock": BEDROCK_CAPABILITIES,
    "bedrock_converse": BEDROCK_CONVERSE_CAPABILITIES,
    "together_ai": TOGETHER_AI_CAPABILITIES,
    "ollama": OLLAMA_CAPABILITIES,
    "claude_cli": CLAUDE_CLI_CAPABILITIES,
    "openai_compatible": GENERIC_OPENAI_CAPABILITIES,
}
