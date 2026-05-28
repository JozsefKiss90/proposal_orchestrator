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
    ``ORCHESTRATOR_TRANSPORT_PRESET``
        Optional preset name (e.g. ``BEDROCK_EU_DEVELOPMENT``).
        When set, supplies default backend, endpoint, model, and
        capabilities.  Explicit ``ORCHESTRATOR_TRANSPORT_*`` variables
        override preset defaults.
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
from dotenv import load_dotenv

load_dotenv()
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
    "bedrock_converse",
    "together_ai",
    "ollama",
    "openai_compatible",
})

#: Backends allowed when ORCHESTRATOR_PRODUCTION_MODE=true.
PRODUCTION_BACKENDS: frozenset[str] = frozenset({
    "bedrock_converse",
    "bedrock",
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
# TransportPreset
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransportPreset:
    """Static transport configuration preset.

    Presets are named bundles of default configuration values that reduce
    operational mistakes when switching between providers.  They are
    static aids, not dynamic capability detection.

    Explicit ``ORCHESTRATOR_TRANSPORT_*`` environment variables override
    preset defaults.

    Attributes
    ----------
    name:
        Unique preset identifier (e.g. ``BEDROCK_EU_DEVELOPMENT``).
    backend_name:
        The backend this preset targets (one of :data:`VALID_BACKENDS`).
    description:
        Human-readable summary.
    default_endpoint:
        Default base URL.  ``None`` if no default (must be env-supplied).
    default_model:
        Default model identifier.  ``None`` if none.
    requires_api_key:
        Whether the preset requires ``ORCHESTRATOR_TRANSPORT_API_KEY``.
    default_region:
        Default AWS region (Bedrock presets only).  ``None`` otherwise.
    capabilities:
        Static capability metadata.
    intended_use:
        Short description of when to use this preset.
    production_suitable:
        Whether the preset is intended for institutional production use.
    notes:
        Operational notes and caveats.
    """

    name: str
    backend_name: str
    description: str
    default_endpoint: str | None
    default_model: str | None
    requires_api_key: bool
    default_region: str | None
    capabilities: ProviderCapabilities
    intended_use: str
    production_suitable: bool
    notes: tuple[str, ...] = ()


# -- Pre-defined presets ---------------------------------------------------

CLAUDE_REFERENCE = TransportPreset(
    name="CLAUDE_REFERENCE",
    backend_name="claude_cli",
    description="Claude CLI reference backend for output equivalence testing",
    default_endpoint=None,
    default_model=None,
    requires_api_key=False,
    default_region=None,
    capabilities=CAPABILITIES_REGISTRY["claude_cli"],
    intended_use="reference backend / output equivalence testing",
    production_suitable=False,
    notes=(
        "Uses the local claude CLI via subscription.",
        "Not closed-network; prompts transit Anthropic infrastructure.",
    ),
)

BEDROCK_EU_DEVELOPMENT = TransportPreset(
    name="BEDROCK_EU_DEVELOPMENT",
    backend_name="bedrock",
    description="AWS Bedrock via bedrock-mantle, EU (Ireland), development",
    default_endpoint=BEDROCK_URL_TEMPLATE.format(region="eu-west-1"),
    default_model=DEFAULT_BEDROCK_MODEL,
    requires_api_key=True,
    default_region="eu-west-1",
    capabilities=CAPABILITIES_REGISTRY["bedrock"],
    intended_use="EU Bedrock development validation",
    production_suitable=False,
    notes=(
        "Uses eu-west-1 (Ireland) region.",
        "Streaming usage accounting (stream_options.include_usage) is UNVERIFIED.",
        "Use long-term API keys for development; short-term key rotation is a production step.",
    ),
)

BEDROCK_EU_PRODUCTION = TransportPreset(
    name="BEDROCK_EU_PRODUCTION",
    backend_name="bedrock",
    description="AWS Bedrock via bedrock-mantle, EU, institutional production",
    default_endpoint=BEDROCK_URL_TEMPLATE.format(region="eu-west-1"),
    default_model=DEFAULT_BEDROCK_MODEL,
    requires_api_key=True,
    default_region="eu-west-1",
    capabilities=CAPABILITIES_REGISTRY["bedrock"],
    intended_use="EU institutional deployment",
    production_suitable=True,
    notes=(
        "Production use requires region and model availability validation in the Bedrock console.",
        "Configure VPC endpoint via PrivateLink for closed-network operation.",
        "Enable CloudTrail logging for Bedrock API calls.",
        "Download and execute GDPR DPA via AWS Artifact.",
        "Implement short-term API key rotation via BedrockTokenGenerator SDK.",
        "Streaming usage accounting (stream_options.include_usage) is UNVERIFIED.",
    ),
)

TOGETHER_VALIDATION = TransportPreset(
    name="TOGETHER_VALIDATION",
    backend_name="together_ai",
    description="Together AI for low-friction OpenAI-compatible validation",
    default_endpoint=DEFAULT_TOGETHER_AI_URL,
    default_model=None,
    requires_api_key=True,
    default_region=None,
    capabilities=CAPABILITIES_REGISTRY["together_ai"],
    intended_use="low-friction OpenAI-compatible provider validation",
    production_suitable=False,
    notes=(
        "Useful for rapid Phase E iteration and cost-optimized testing.",
        "Not suitable for institutional production (3 security GAPs, 4 PARTIALs).",
    ),
)

OLLAMA_LOCAL = TransportPreset(
    name="OLLAMA_LOCAL",
    backend_name="ollama",
    description="Local Ollama instance for backend smoke testing",
    default_endpoint=DEFAULT_OLLAMA_URL,
    default_model=None,
    requires_api_key=False,
    default_region=None,
    capabilities=CAPABILITIES_REGISTRY["ollama"],
    intended_use="local backend smoke testing",
    production_suitable=False,
    notes=(
        "Requires a running Ollama instance on localhost:11434.",
        "Model must be pulled locally before use.",
    ),
)

GENERIC_OPENAI_COMPATIBLE = TransportPreset(
    name="GENERIC_OPENAI_COMPATIBLE",
    backend_name="openai_compatible",
    description="Generic OpenAI-compatible endpoint (endpoint required via env)",
    default_endpoint=None,
    default_model=None,
    requires_api_key=True,
    default_region=None,
    capabilities=CAPABILITIES_REGISTRY["openai_compatible"],
    intended_use="generic OpenAI-compatible backend integration",
    production_suitable=False,
    notes=(
        "ORCHESTRATOR_TRANSPORT_ENDPOINT must be set explicitly.",
        "ORCHESTRATOR_TRANSPORT_MODEL must be set explicitly.",
    ),
)

BEDROCK_CONVERSE_US = TransportPreset(
    name="BEDROCK_CONVERSE_US",
    backend_name="bedrock_converse",
    description="Native Bedrock Converse API via boto3, US region, IAM auth",
    default_endpoint=None,
    default_model="us.anthropic.claude-sonnet-4-6",
    requires_api_key=False,
    default_region="us-east-1",
    capabilities=CAPABILITIES_REGISTRY["bedrock_converse"],
    intended_use="Native Bedrock access with Claude via inference profiles",
    production_suitable=True,
    notes=(
        "Uses boto3 with IAM credentials (env vars, ~/.aws/credentials, or instance profile).",
        "Model IDs are inference profile IDs (e.g. us.anthropic.claude-sonnet-4-6).",
        "No API key needed — authentication is via standard AWS credential chain.",
        "Does not use bedrock-mantle OpenAI-compatible proxy.",
    ),
)

#: Registry of all available presets, keyed by name.
PRESET_REGISTRY: dict[str, TransportPreset] = {
    p.name: p
    for p in (
        CLAUDE_REFERENCE,
        BEDROCK_EU_DEVELOPMENT,
        BEDROCK_EU_PRODUCTION,
        TOGETHER_VALIDATION,
        OLLAMA_LOCAL,
        GENERIC_OPENAI_COMPATIBLE,
        BEDROCK_CONVERSE_US,
    )
}


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
    preset_name: str | None = None


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
# Production mode enforcement
# ---------------------------------------------------------------------------


def is_production_mode() -> bool:
    """Return ``True`` when ``ORCHESTRATOR_PRODUCTION_MODE`` is ``"true"``."""
    return os.environ.get("ORCHESTRATOR_PRODUCTION_MODE", "").lower() == "true"


def _enforce_production_backend(config: ProviderConfig) -> None:
    """Reject non-production backends when production mode is active.

    Raises
    ------
    ValueError
        If the resolved backend is not in :data:`PRODUCTION_BACKENDS`.
    """
    if config.backend_name not in PRODUCTION_BACKENDS:
        raise ValueError(
            f"ORCHESTRATOR_PRODUCTION_MODE=true but backend "
            f"{config.backend_name!r} is not production-suitable. "
            f"Production-allowed backends: {sorted(PRODUCTION_BACKENDS)}. "
            f"Set ORCHESTRATOR_TRANSPORT_PRESET or "
            f"ORCHESTRATOR_TRANSPORT_BACKEND to a production backend."
        )


# ---------------------------------------------------------------------------
# Preset helpers
# ---------------------------------------------------------------------------


def list_transport_presets() -> dict[str, TransportPreset]:
    """Return a copy of the preset registry."""
    return dict(PRESET_REGISTRY)


def get_transport_preset(name: str) -> TransportPreset:
    """Look up a preset by name.

    Raises
    ------
    ValueError
        If *name* is not a recognised preset.
    """
    if name not in PRESET_REGISTRY:
        raise ValueError(
            f"Unknown transport preset: {name!r}. "
            f"Available presets: {sorted(PRESET_REGISTRY.keys())}"
        )
    return PRESET_REGISTRY[name]


def resolve_provider_config_from_preset(preset_name: str) -> ProviderConfig:
    """Resolve a :class:`ProviderConfig` from a named preset.

    The preset supplies default values for backend, endpoint, model,
    region, and capabilities.  Explicit ``ORCHESTRATOR_TRANSPORT_*``
    environment variables override preset defaults, with one safety
    rule: if ``ORCHESTRATOR_TRANSPORT_BACKEND`` is set and disagrees
    with the preset's ``backend_name``, a ``ValueError`` is raised to
    prevent accidental mixed configuration.

    Parameters
    ----------
    preset_name:
        A key from :data:`PRESET_REGISTRY`.

    Returns
    -------
    ProviderConfig
        The resolved configuration.

    Raises
    ------
    ValueError
        If the preset is unknown, if a required API key is missing, or
        if ``ORCHESTRATOR_TRANSPORT_BACKEND`` conflicts with the preset.
    """
    preset = get_transport_preset(preset_name)

    # Production mode: reject non-production presets.
    if is_production_mode() and not preset.production_suitable:
        raise ValueError(
            f"ORCHESTRATOR_PRODUCTION_MODE=true but preset "
            f"{preset_name!r} is not production-suitable "
            f"(production_suitable=False). Use a production preset "
            f"(e.g. BEDROCK_CONVERSE_US, BEDROCK_EU_PRODUCTION)."
        )

    # Safety: reject conflicting backend override.
    explicit_backend = os.environ.get("ORCHESTRATOR_TRANSPORT_BACKEND")
    if explicit_backend is not None and explicit_backend != preset.backend_name:
        raise ValueError(
            f"ORCHESTRATOR_TRANSPORT_BACKEND={explicit_backend!r} conflicts "
            f"with preset {preset_name!r} (backend_name={preset.backend_name!r}). "
            f"Remove ORCHESTRATOR_TRANSPORT_BACKEND or use a matching preset."
        )

    # Resolve with env overrides falling back to preset defaults.
    endpoint = os.environ.get("ORCHESTRATOR_TRANSPORT_ENDPOINT")
    api_key = os.environ.get("ORCHESTRATOR_TRANSPORT_API_KEY")
    model = os.environ.get("ORCHESTRATOR_TRANSPORT_MODEL")

    # Endpoint: env override > preset default > region-based construction.
    resolved_endpoint = endpoint or preset.default_endpoint
    if not resolved_endpoint and preset.backend_name == "bedrock":
        region = os.environ.get("AWS_REGION", preset.default_region or DEFAULT_AWS_REGION)
        resolved_endpoint = BEDROCK_URL_TEMPLATE.format(region=region)

    # Model: env override > preset default.
    resolved_model = model or preset.default_model

    # API key validation.
    if preset.requires_api_key and not api_key:
        raise ValueError(
            f"Preset {preset_name!r} requires ORCHESTRATOR_TRANSPORT_API_KEY. "
            f"Set the environment variable before using this preset."
        )

    # Bedrock model ID validation.
    if preset.backend_name == "bedrock" and resolved_model:
        if not validate_bedrock_model_id(resolved_model):
            raise ValueError(
                f"Invalid Bedrock model ID: {resolved_model!r}. "
                f"Expected format: <provider>.<model> "
                f"(e.g. anthropic.claude-sonnet-4-20250514-v1:0)"
            )

    # Generic openai_compatible requires explicit endpoint.
    if preset.backend_name == "openai_compatible" and not resolved_endpoint:
        raise ValueError(
            f"Preset {preset_name!r} requires ORCHESTRATOR_TRANSPORT_ENDPOINT. "
            f"Set the environment variable before using this preset."
        )

    return ProviderConfig(
        backend_name=preset.backend_name,
        base_url=resolved_endpoint,
        api_key_set=bool(api_key),
        model=resolved_model,
        capabilities=preset.capabilities,
        preset_name=preset_name,
    )


# ---------------------------------------------------------------------------
# Configuration resolution
# ---------------------------------------------------------------------------


def resolve_provider_config() -> ProviderConfig:
    """Resolve provider configuration from environment variables.

    If ``ORCHESTRATOR_TRANSPORT_PRESET`` is set, delegates to
    :func:`resolve_provider_config_from_preset`.  Otherwise reads
    ``ORCHESTRATOR_TRANSPORT_BACKEND`` and related variables directly.

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
    # Preset path: if ORCHESTRATOR_TRANSPORT_PRESET is set, use it.
    preset_name = os.environ.get("ORCHESTRATOR_TRANSPORT_PRESET")
    if preset_name is not None:
        # Preset path includes its own production enforcement.
        return resolve_provider_config_from_preset(preset_name)

    # Legacy path: direct env var resolution.
    production_mode = is_production_mode()
    backend = os.environ.get("ORCHESTRATOR_TRANSPORT_BACKEND", "claude_cli")

    if backend not in VALID_BACKENDS:
        raise ValueError(
            f"Invalid backend: {backend!r}. "
            f"Valid backends: {sorted(VALID_BACKENDS)}"
        )

    # Production mode: reject non-production backends early.
    if production_mode and backend not in PRODUCTION_BACKENDS:
        raise ValueError(
            f"ORCHESTRATOR_PRODUCTION_MODE=true but backend "
            f"{backend!r} is not production-suitable. "
            f"Production-allowed backends: {sorted(PRODUCTION_BACKENDS)}. "
            f"Set ORCHESTRATOR_TRANSPORT_PRESET or "
            f"ORCHESTRATOR_TRANSPORT_BACKEND to a production backend."
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

    if backend == "bedrock_converse":
        return _resolve_bedrock_converse(model, capabilities)

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


def _resolve_bedrock_converse(
    model: str | None,
    capabilities: ProviderCapabilities,
) -> ProviderConfig:
    """Resolve native Bedrock Converse configuration."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    return ProviderConfig(
        backend_name="bedrock_converse",
        base_url=None,
        api_key_set=False,
        model=model,
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


def build_converse_backend(
    config: ProviderConfig,
    *,
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> Any:
    """Construct a :class:`BedrockConverseBackend` from a resolved config.

    Parameters
    ----------
    config:
        A resolved :class:`ProviderConfig` with ``backend_name="bedrock_converse"``.
    tools:
        Optional tool schemas for TAPM-mode requests (OpenAI format, converted internally).
    temperature:
        Sampling temperature.
    max_tokens:
        Maximum completion tokens.
    """
    if config.backend_name != "bedrock_converse":
        raise ValueError(
            f"build_converse_backend requires bedrock_converse backend, "
            f"got {config.backend_name!r}"
        )
    if config.model is None:
        raise ValueError("model is required for bedrock_converse backend")

    from runner.transport.bedrock_converse import BedrockConverseBackend

    region = os.environ.get("AWS_REGION", "us-east-1")

    return BedrockConverseBackend(
        model_id=config.model,
        region_name=region,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
    )
