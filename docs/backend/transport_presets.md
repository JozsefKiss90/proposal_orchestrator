# Transport Presets

**Status:** Phase E implementation
**Purpose:** Reduce configuration mistakes when switching between providers

---

## Overview

Transport presets are named bundles of default configuration values for the orchestrator's LLM transport backend. They supply default backend, endpoint, model, and capabilities so that switching providers requires setting one or two environment variables instead of five.

Presets are **static configuration aids**, not dynamic capability detection. They do not contact any provider at resolution time.

---

## Available Presets

| Preset | Backend | Endpoint | API Key | Model | Production |
|--------|---------|----------|---------|-------|------------|
| `CLAUDE_REFERENCE` | `claude_cli` | — | No | — | No |
| `BEDROCK_EU_DEVELOPMENT` | `bedrock` | `bedrock-mantle.eu-west-1.api.aws/v1` | Yes | Claude Sonnet 4 | No |
| `BEDROCK_EU_PRODUCTION` | `bedrock` | `bedrock-mantle.eu-west-1.api.aws/v1` | Yes | Claude Sonnet 4 | Yes |
| `TOGETHER_VALIDATION` | `together_ai` | `api.together.ai/v1` | Yes | — | No |
| `OLLAMA_LOCAL` | `ollama` | `localhost:11434/v1` | No | — | No |
| `GENERIC_OPENAI_COMPATIBLE` | `openai_compatible` | Must be set via env | Yes | Must be set via env | No |

---

## Usage

Set `ORCHESTRATOR_TRANSPORT_PRESET` to a preset name. Explicit `ORCHESTRATOR_TRANSPORT_*` variables override preset defaults.

### Claude reference (default behaviour)

```bash
export ORCHESTRATOR_TRANSPORT_PRESET=CLAUDE_REFERENCE
```

### Bedrock EU development

```bash
export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_EU_DEVELOPMENT
export ORCHESTRATOR_TRANSPORT_API_KEY=<bedrock-api-key>
```

### Bedrock EU production

```bash
export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_EU_PRODUCTION
export ORCHESTRATOR_TRANSPORT_API_KEY=<bedrock-api-key>
```

### Together AI validation

```bash
export ORCHESTRATOR_TRANSPORT_PRESET=TOGETHER_VALIDATION
export ORCHESTRATOR_TRANSPORT_API_KEY=<together-key>
export ORCHESTRATOR_TRANSPORT_MODEL=meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo
```

### Ollama local

```bash
export ORCHESTRATOR_TRANSPORT_PRESET=OLLAMA_LOCAL
export ORCHESTRATOR_TRANSPORT_MODEL=llama3.1:70b
```

### Override preset defaults

Explicit environment variables always take precedence over preset defaults:

```bash
export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_EU_DEVELOPMENT
export ORCHESTRATOR_TRANSPORT_API_KEY=<key>
export ORCHESTRATOR_TRANSPORT_ENDPOINT=https://bedrock-mantle.us-east-1.api.aws/v1
export ORCHESTRATOR_TRANSPORT_MODEL=meta.llama3-1-70b-instruct-v1:0
```

---

## Safety Rules

**Conflicting backend rejection.** If `ORCHESTRATOR_TRANSPORT_BACKEND` is set and disagrees with the preset's `backend_name`, resolution fails with a clear error. This prevents accidental mixed configuration.

```bash
# This will fail:
export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_EU_DEVELOPMENT
export ORCHESTRATOR_TRANSPORT_BACKEND=ollama  # ERROR: conflicts with preset
```

**No secrets stored.** `ProviderConfig` stores `api_key_set: bool`, never the key value itself. The key is read from the environment only at `build_openai_backend()` time.

**Backward compatibility.** When `ORCHESTRATOR_TRANSPORT_PRESET` is unset, the existing `ORCHESTRATOR_TRANSPORT_BACKEND` path is used unchanged.

---

## Warnings

- **BEDROCK_EU_PRODUCTION** still requires live AWS account validation before institutional deployment: region/model availability, VPC/PrivateLink, CloudTrail, DPA.
- **Streaming usage accounting** for Bedrock (`stream_options.include_usage`) is UNVERIFIED on `bedrock-mantle`.
- **Short-term API key generation** may require IAM credentials. Initial development should use long-term keys from the Bedrock console.

---

*Phase E implementation. See `docs/backend/phase_e_bedrock_implementation_brief.md` for the full specification.*
