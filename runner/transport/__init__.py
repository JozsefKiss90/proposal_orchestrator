"""
Transport abstraction layer for the Proposal Orchestrator.

This package provides backend-agnostic LLM transport infrastructure:

- **tool_executor / tool_loop**: Local Read/Glob tool execution and the
  iterative tool-call loop for TAPM compatibility.
- **openai_compatible**: HTTP backend for OpenAI-compatible endpoints
  (AWS Bedrock via bedrock-mantle, Together AI, Ollama).
- **config**: Provider configuration resolution from environment variables.
- **errors**: Error types and HTTP error normalization.
- **capabilities**: Static per-provider capability metadata.

The ``openai_compatible`` module requires ``httpx``.  All other modules
are pure-stdlib and safe to import without additional dependencies.

Constitutional authority:
    Subordinate to CLAUDE.md.  This package does not evaluate gates,
    invoke agents, write canonical artifacts, or modify scheduler state.
"""

# Re-export lightweight types that do not require httpx.
from runner.transport.capabilities import (  # noqa: F401
    CAPABILITIES_REGISTRY,
    ProviderCapabilities,
)
from runner.transport.config import (  # noqa: F401
    PRESET_REGISTRY,
    VALID_BACKENDS,
    ProviderConfig,
    TransportPreset,
    get_transport_preset,
    list_transport_presets,
    resolve_provider_config,
    resolve_provider_config_from_preset,
)
from runner.transport.errors import (  # noqa: F401
    ErrorCategory,
    OpenAICompatTransportError,
)
from runner.transport.tool_executor import (  # noqa: F401
    GLOB_TOOL_SCHEMA,
    READ_TOOL_SCHEMA,
    ToolExecutor,
)
from runner.transport.tool_loop import (  # noqa: F401
    FakeBackend,
    ToolLoopBackend,
    ToolLoopResponse,
    run_tool_loop,
)

# OpenAICompatBackend is NOT re-exported here to avoid forcing an
# httpx import.  Callers that need it should import directly:
#     from runner.transport.openai_compatible import OpenAICompatBackend
