"""
Provider configuration and backend resolution.

Reads ``ORCHESTRATOR_TRANSPORT_*`` environment variables and resolves
them into a :class:`ProviderConfig` that can instantiate the appropriate
LLM transport backend.

Backend selection:
    - ``claude_cli`` (default): uses the existing Claude CLI transport.
    - ``bedrock``: AWS Bedrock via bedrock-mantle OpenAI-compatible endpoint.
    - ``together_ai``: Together AI OpenAI-compatible endpoint.
    - ``ollama``: Local Ollama OpenAI-compatible endpoint.
    - ``openai_compatible``: Generic OpenAI-compatible endpoint.

Environment variables:
    ``ORCHESTRATOR_TRANSPORT_BACKEND``
        Backend selector.  Default: ``claude_cli``.
    ``ORCHESTRATOR_TRANSPORT_ENDPOINT``
        Base URL for non-Claude backends.
    ``ORCHESTRATOR_TRANSPORT_API_KEY``
        API key / Bearer token.  Never logged.
    ``ORCHESTRATOR_TRANSPORT_MODEL``
        Model identifier override.
    ``AWS_REGION``
        AWS region for Bedrock URL construction (default: ``eu-west-1``).

Constitutional authority:
    Subordinate to CLAUDE.md.  This module resolves configuration only.
    It does not evaluate gates, invoke agents, write canonical artifacts,
    or modify scheduler state.

Authoritative sources:
    - docs/backend/phase_e_bedrock_implementation_brief.md
    - docs/internal_llm_migration_plan.md Section 4.1
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from runner.transport.capabilities import (
    CAPABILITIES_REGISTRY,
    ProviderCapabilities,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_BACKENDS: frozenset[str] = frozenset({
    "claude_cli",
    "bedrock",
    "together_ai",
    "ollama",
    "openai_compatible",
})

#: Default Bedrock model (Claude Sonnet 4 on Bedrock).
DEFAULT_BEDROCK_MODEL: str = "anthropic.claude-sonnet-4-20250514-v1:0"

#: Default AWS region for Bedrock.
DEFAULT_AWS_REGION: str = "eu-west-1"

#: Bedrock mantle URL template.
BEDROCK_URL_TEMPLATE: str = "https://bedrock-mantle.{region}.api.aws/v1"

#: Default Together AI base URL.
DEFAULT_TOGETHER_AI_URL: str = "https://api.together.ai/v1"

#: Default Ollama base URL.
DEFAULT_OLLAMA_URL: str = "http://localhost:11434/v1"

#: Regex for Bedrock model IDs: <provider>.<model>[-<version>]
_BEDROCK_MODEL_ID_PATTERN: re.Pattern[str] = re.compile(
    r"^[a-z][a-z0-9-]*\.[a-zA-Z0-9._:-]+$"
)


# ---------------------------------------------------------------------------
# ProviderConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderConfig:
    """Resolved provider configuration.

    Attributes
    ----------
    backend_name:
        One of :data:`VALID_BACKENDS`.
    base_url:
        The base URL for OpenAI-compatible backends.  ``None`` for ``claude_cli``.
    api_key_set:
        Whether an API key was provided.  The key value itself is NOT
        stored here to prevent accidental logging.
    model:
        The model identifier to use.
    capabilities:
        Static capability metadata for this provider.
    """

    backend_name: str
    base_url: str | None
    api_key_set: bool
    model: str | None
    capabilities: ProviderCapabilities


# ---------------------------------------------------------------------------
# Model ID validation
# ---------------------------------------------------------------------------


def validate_bedrock_model_id(model_id: str) -> bool:
    """Check whether *model_id* matches the Bedrock ``<provider>.<model>`` format.

    Examples of valid IDs:
        - ``anthropic.claude-sonnet-4-20250514-v1:0``
        - ``meta.llama3-1-70b-instruct-v1:0``
        - ``deepseek.v3.2``

    Returns ``True`` if the format is valid, ``False`` otherwise.
    """
    return bool(_BEDROCK_MODEL_ID_PATTERN.match(model_id))


# ---------------------------------------------------------------------------
# Configuration resolution
# ---------------------------------------------------------------------------


def resolve_provider_config() -> ProviderConfig:
    """Resolve provider configuration from environment variables.

    Reads ``ORCHESTRATOR_TRANSPORT_*`` and ``AWS_REGION`` environment
    variables.  Does not instantiate any backend — returns a pure
    configuration object.

    Returns
    -------
    ProviderConfig
        The resolved configuration.

    Raises
    ------
    ValueError
        If the backend name is invalid, or if required environment
        variables are missing for the selected backend.
    """
    backend = os.environ.get("ORCHESTRATOR_TRANSPORT_BACKEND", "claude_cli")

    if backend not in VALID_BACKENDS:
        raise ValueError(
            f"Invalid backend: {backend!r}. "
            f"Valid backends: {sorted(VALID_BACKENDS)}"
        )

    endpoint = os.environ.get("ORCHESTRATOR_TRANSPORT_ENDPOINT")
    api_key = os.environ.get("ORCHESTRATOR_TRANSPORT_API_KEY")
    model = os.environ.get("ORCHESTRATOR_TRANSPORT_MODEL")

    capabilities = CAPABILITIES_REGISTRY.get(
        backend,
        CAPABILITIES_REGISTRY["openai_compatible"],
    )

    if backend == "claude_cli":
        return ProviderConfig(
            backend_name="claude_cli",
            base_url=None,
            api_key_set=False,
            model=model,
            capabilities=capabilities,
        )

    if backend == "bedrock":
        return _resolve_bedrock(endpoint, api_key, model, capabilities)

    if backend == "together_ai":
        return _resolve_together_ai(endpoint, api_key, model, capabilities)

    if backend == "ollama":
        return _resolve_ollama(endpoint, model, capabilities)

    # Generic openai_compatible
    return _resolve_generic(endpoint, api_key, model, capabilities)


def _resolve_bedrock(
    endpoint: str | None,
    api_key: str | None,
    model: str | None,
    capabilities: ProviderCapabilities,
) -> ProviderConfig:
    """Resolve Bedrock configuration."""
    if not endpoint:
        region = os.environ.get("AWS_REGION", DEFAULT_AWS_REGION)
        endpoint = BEDROCK_URL_TEMPLATE.format(region=region)

    resolved_model = model or DEFAULT_BEDROCK_MODEL
    if not validate_bedrock_model_id(resolved_model):
        raise ValueError(
            f"Invalid Bedrock model ID: {resolved_model!r}. "
            f"Expected format: <provider>.<model> "
            f"(e.g. anthropic.claude-sonnet-4-20250514-v1:0)"
        )

    if not api_key:
        raise ValueError(
            "ORCHESTRATOR_TRANSPORT_API_KEY is required for the bedrock backend. "
            "Generate a Bedrock API key in the Amazon Bedrock console."
        )

    return ProviderConfig(
        backend_name="bedrock",
        base_url=endpoint,
        api_key_set=True,
        model=resolved_model,
        capabilities=capabilities,
    )


def _resolve_together_ai(
    endpoint: str | None,
    api_key: str | None,
    model: str | None,
    capabilities: ProviderCapabilities,
) -> ProviderConfig:
    """Resolve Together AI configuration."""
    if not api_key:
        raise ValueError(
            "ORCHESTRATOR_TRANSPORT_API_KEY is required for the together_ai backend."
        )

    return ProviderConfig(
        backend_name="together_ai",
        base_url=endpoint or DEFAULT_TOGETHER_AI_URL,
        api_key_set=True,
        model=model,
        capabilities=capabilities,
    )


def _resolve_ollama(
    endpoint: str | None,
    model: str | None,
    capabilities: ProviderCapabilities,
) -> ProviderConfig:
    """Resolve Ollama configuration."""
    return ProviderConfig(
        backend_name="ollama",
        base_url=endpoint or DEFAULT_OLLAMA_URL,
        api_key_set=False,
        model=model,
        capabilities=capabilities,
    )


def _resolve_generic(
    endpoint: str | None,
    api_key: str | None,
    model: str | None,
    capabilities: ProviderCapabilities,
) -> ProviderConfig:
    """Resolve generic OpenAI-compatible configuration."""
    if not endpoint:
        raise ValueError(
            "ORCHESTRATOR_TRANSPORT_ENDPOINT is required for the "
            "openai_compatible backend."
        )

    return ProviderConfig(
        backend_name="openai_compatible",
        base_url=endpoint,
        api_key_set=bool(api_key),
        model=model,
        capabilities=capabilities,
    )


# ---------------------------------------------------------------------------
# Backend construction
# ---------------------------------------------------------------------------


def build_openai_backend(
    config: ProviderConfig,
    *,
    tools: list[dict[str, Any]] | None = None,
    timeout_seconds: int = 300,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> Any:
    """Construct an :class:`OpenAICompatBackend` from a resolved config.

    Defers the ``httpx`` import to the point where a non-Claude backend
    is actually needed, so the Claude CLI path never requires ``httpx``.

    Parameters
    ----------
    config:
        A resolved :class:`ProviderConfig` for a non-Claude backend.
    tools:
        Optional tool schemas for TAPM-mode requests.
    timeout_seconds:
        Request timeout.
    temperature:
        Sampling temperature.
    max_tokens:
        Maximum completion tokens.

    Returns
    -------
    OpenAICompatBackend
        A backend instance conforming to the ToolLoopBackend protocol.

    Raises
    ------
    ValueError
        If the config is for ``claude_cli`` (which doesn't use this backend).
    ImportError
        If ``httpx`` is not installed.
    """
    if config.backend_name == "claude_cli":
        raise ValueError(
            "Cannot build OpenAICompatBackend for claude_cli backend. "
            "Use runner.claude_transport.invoke_claude_text instead."
        )

    if config.base_url is None:
        raise ValueError(f"base_url is required for {config.backend_name} backend")

    if config.model is None:
        raise ValueError(f"model is required for {config.backend_name} backend")

    # Deferred import: httpx is only required when actually building
    # a non-Claude backend.
    from runner.transport.openai_compatible import OpenAICompatBackend

    # Retrieve the actual API key from the environment at build time.
    # The ProviderConfig intentionally does not store the key value.
    api_key = os.environ.get("ORCHESTRATOR_TRANSPORT_API_KEY")

    return OpenAICompatBackend(
        base_url=config.base_url,
        api_key=api_key,
        model=config.model,
        tools=tools,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
    )
