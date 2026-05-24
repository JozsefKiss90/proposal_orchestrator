# Phase E Bedrock Implementation Brief

**Version:** 1.0
**Date:** 2026-05-22
**Status:** IMPLEMENTATION BRIEF — Ready for engineering
**Scope:** AWS Bedrock OpenAI-compatible transport backend
**Constitutional authority:** CLAUDE.md (this brief is subordinate; implementation must comply)

---

## Objective

Implement an AWS Bedrock backend within the existing `OpenAICompatBackend` transport abstraction, using the `bedrock-mantle` OpenAI-compatible endpoint. The Bedrock backend reuses the same HTTP `POST /v1/chat/completions` pathway as Together AI, differing only in endpoint URL, authentication mechanism, and model identifier format.

No new backend class is required. Bedrock is a configuration variant of the OpenAI-compatible backend.

---

## Required AWS Documents Indexed

| Document | Size | Pages Referenced | Categories Covered |
|----------|------|-----------------|-------------------|
| `AWS/bedrock-ug.pdf` | 58.2 MB | 593-606, 1096-1102, 1178-1190, 1198-1224, 1243-1249, 2276-2277, 2374-2400, 2425-2451, 4575-4581 | All 15 |

**Context7 libraries queried:**
- `/websites/aws_amazon_bedrock_userguide` (8698 snippets, score 78.7)
- `/websites/aws_amazon_bedrock` (21792 snippets, score 77.4)
- `/jparkerweb/bedrock-wrapper` (154 snippets, OpenAI compat reference)

**Repository security assessment:**
- `docs/benchmark_reports/aws_bedrock_security_assessment.md` — 12/12 PASS

---

## Endpoint Configuration

### Base URL Format

```
https://bedrock-mantle.<region>.api.aws/v1
```

Examples:
- `https://bedrock-mantle.us-east-1.api.aws/v1`
- `https://bedrock-mantle.eu-west-1.api.aws/v1`
- `https://bedrock-mantle.eu-central-1.api.aws/v1`

### Required Path

```
POST /v1/chat/completions
```

This is the standard OpenAI Chat Completions path. The `bedrock-mantle` endpoint includes `/v1` in its base URL, so the full request URL is:

```
https://bedrock-mantle.<region>.api.aws/v1/chat/completions
```

### Alternative Endpoint (NOT used for Phase E)

The `bedrock-runtime` endpoint (`https://bedrock-runtime.<region>.amazonaws.com`) uses the native Converse/Invoke API and requires AWS Signature V4 authentication. Phase E uses `bedrock-mantle` exclusively because it provides OpenAI Chat Completions compatibility with API key authentication.

### Example Request (HTTP)

```bash
curl -X POST $OPENAI_BASE_URL/chat/completions \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer $OPENAI_API_KEY" \
   -d '{
    "model": "anthropic.claude-sonnet-4-20250514-v1:0",
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "stream": true
}'
```

### Example Request (Python OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI()  # reads OPENAI_API_KEY and OPENAI_BASE_URL from env

response = client.chat.completions.create(
    model="anthropic.claude-sonnet-4-20250514-v1:0",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)
```

---

## Authentication Model

### Primary Path: Bedrock API Key (used for Phase E)

| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | Bedrock API key (generated in Amazon Bedrock console) |
| `OPENAI_BASE_URL` | `https://bedrock-mantle.<region>.api.aws/v1` |

The `bedrock-mantle` endpoint accepts standard `Authorization: Bearer <api_key>` headers, identical to Together AI and other OpenAI-compatible providers.

**Key types:**
- **Short-term keys:** Auto-refresh, recommended for production
- **Long-term keys:** Static, simpler for development

**Key generation:** Amazon Bedrock console > API keys section.

### Alternative Path: IAM / AWS Signature V4 (NOT required for Phase E)

The `bedrock-runtime` endpoint uses IAM authentication with AWS Signature V4. This requires:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_BEARER_TOKEN_BEDROCK` (for bearer token auth variant)
- IAM permissions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`

Phase E does NOT use IAM authentication. The `bedrock-mantle` API key path eliminates this complexity entirely.

### Credential Precedence

For `bedrock-mantle`: `OPENAI_API_KEY` environment variable > OpenAI client constructor `api_key` parameter.

No AWS credential chain (profiles, instance metadata, STS) is involved when using the `bedrock-mantle` endpoint with API keys.

---

## OpenAI Compatibility Surface

### Supported via `bedrock-mantle`

| Feature | Status | Notes |
|---------|--------|-------|
| `POST /v1/chat/completions` | Supported | Standard OpenAI Chat Completions API |
| `messages` array (system/user/assistant) | Supported | All standard roles |
| `model` parameter | Supported | Uses Bedrock model IDs (see Model Identifier Rules) |
| `temperature` | Supported | Standard float 0.0-2.0 |
| `max_tokens` | Supported | Model-dependent limits |
| `stream` | Supported | SSE streaming with standard chunk format |
| `tools` / function calling | Supported | Client-side tool calling only |
| `top_p` | Supported | Standard nucleus sampling |
| `stop` / `stop_sequences` | Supported | Array or string format |

### NOT Supported via `bedrock-mantle`

| Feature | Status | Notes |
|---------|--------|-------|
| Server-side tool calling | Not supported | Only available on `bedrock-runtime` endpoint |
| `response_format` (JSON mode) | Model-dependent | Supported on some models via Converse API; verify per model |
| Token counting endpoint | Not supported | No `/v1/tokenize` equivalent |
| Intelligent prompt routing | Not supported | Explicit model selection required |

### Compatibility with Proposal Orchestrator

The orchestrator uses client-side tool calling via the local `ToolExecutor` and `ToolLoop` modules. This is fully compatible with `bedrock-mantle` because:
1. Tool definitions are sent in the `tools` parameter of the Chat Completions request
2. The model returns `tool_calls` in its response
3. The local `ToolLoop` handles execution and re-submission
4. Server-side tool calling is not needed

---

## Tool Calling Behaviour

### Client-Side Tool Calling (used by Proposal Orchestrator)

The `bedrock-mantle` endpoint supports OpenAI-format tool definitions:

```json
{
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_most_popular_song",
      "description": "Returns the most popular song on a radio station",
      "parameters": {
        "type": "object",
        "properties": {
          "station_name": {"type": "string", "description": "Name of the radio station"}
        },
        "required": ["station_name"]
      }
    }
  }]
}
```

Response contains standard `tool_calls` array:

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "get_most_popular_song",
          "arguments": "{\"station_name\": \"Neo Tokyo FM\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

### Integration with ToolLoop

The existing `runner/transport/tool_loop.py` `ToolLoopBackend` protocol expects:
- A response dict with `choices[0].message.tool_calls` for tool invocations
- A response dict with `choices[0].message.content` for final text
- `finish_reason` of `"tool_calls"` to continue the loop, `"stop"` or `"length"` to terminate

Bedrock via `bedrock-mantle` returns exactly this format. No adapter translation is needed.

---

## Structured Output Behaviour

Structured outputs (JSON schema enforcement) are supported on the `bedrock-runtime` endpoint via the Converse API for supported models. On `bedrock-mantle`, structured output support is model-dependent.

**Implementation approach:** The Proposal Orchestrator does not rely on `response_format` JSON schema enforcement. Skill outputs are validated post-response by `skill_runtime.py` against artifact schemas. No `bedrock-mantle`-specific structured output handling is required.

---

## Streaming Behaviour

### SSE Streaming via `bedrock-mantle`

When `stream: true`, the endpoint returns Server-Sent Events (SSE) in standard OpenAI format:

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Streaming Event Sequence

1. Initial chunk with `role` in `delta`
2. Content chunks with `delta.content` text fragments
3. Tool call chunks with `delta.tool_calls` (if applicable)
4. Final chunk with `finish_reason` (`"stop"`, `"length"`, or `"tool_calls"`)
5. `[DONE]` sentinel

### Tool Calls in Streaming

Tool call arguments are streamed incrementally as partial JSON in `delta.tool_calls[].function.arguments`. The client must accumulate these fragments before parsing.

**Note:** Bedrock UG (p.1189) states that when using streaming with tool calls, the client must resubmit the complete tool call signature in subsequent requests.

---

## Usage Accounting

### Response Usage Object

```json
{
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 150,
    "total_tokens": 175
  }
}
```

### Additional Fields (when available)

- `cacheReadInputTokensCount` — tokens read from prompt cache (if prompt caching enabled)
- `cacheWriteInputTokensCount` — tokens written to prompt cache

### Streaming Usage

In streaming mode, the `usage` object appears in the final chunk or in the `metadata` event (Converse API). For `bedrock-mantle` Chat Completions streaming, usage is returned in the final chunk when `stream_options: {"include_usage": true}` is set, following the OpenAI convention.

### Integration with Benchmark Engine

The Phase D benchmark engine (`docs/benchmark_reports/migration_summary.md`) already records token usage via the `usage` field in OpenAI-compatible responses. No changes needed — the same extraction logic applies to Bedrock responses.

---

## Error Handling Strategy

### Error Taxonomy (from Bedrock UG pp. 4575-4581)

| Error | HTTP Status | Retryable | Description |
|-------|------------|-----------|-------------|
| `ThrottlingException` | 429 | Yes | Rate limit exceeded |
| `ServiceUnavailable` | 503 | Yes | Bedrock service temporarily down |
| `InternalFailure` | 500 | Yes | Internal Bedrock service error |
| `RequestExpired` | 400 | No | Request timestamp too old |
| `AccessDeniedException` | 403 | No | Missing permissions or model access |
| `InvalidClientTokenId` | 403 | No | Invalid API key |
| `NotAuthorized` | 403 | No | Insufficient IAM permissions |
| `ValidationError` | 400 | No | Malformed request body |
| `ResourceNotFound` | 404 | No | Model ID not found in region |
| `ModelNotReadyException` | 424 | Yes (delayed) | Model still loading |
| Connection timeout/reset | N/A | Yes | Network-level failure |

### Mapping to Orchestrator Failure Categories

| Bedrock Error | Orchestrator `failure_category` |
|---------------|-------------------------------|
| `ThrottlingException` | `CONSTRAINT_VIOLATION` (retryable) |
| `ServiceUnavailable` / `InternalFailure` | `AGENT_EXECUTION_ERROR` (retryable) |
| `AccessDeniedException` / `InvalidClientTokenId` / `NotAuthorized` | `CONSTITUTIONAL_HALT` (credential failure) |
| `ValidationError` | `MALFORMED_ARTIFACT` |
| `ResourceNotFound` | `MISSING_INPUT` (model not available in region) |
| Connection timeout | `AGENT_EXECUTION_ERROR` (retryable) |

---

## Retry Strategy

### Retryable Errors

1. **`ThrottlingException` (429):** Exponential backoff with jitter. Initial delay 1s, max delay 60s, max retries 5.
2. **`ServiceUnavailable` (503):** Exponential backoff. Initial delay 2s, max delay 120s, max retries 3.
3. **`InternalFailure` (500):** Exponential backoff. Initial delay 2s, max delay 120s, max retries 3.
4. **Connection timeout/reset:** Retry once with same timeout. Do not retry on persistent failure.

### Non-Retryable Errors

- `AccessDeniedException`, `InvalidClientTokenId`, `NotAuthorized` — credential/permission issue; fail immediately
- `ValidationError` — request is malformed; fail immediately
- `ResourceNotFound` — model not available; fail immediately
- `RequestExpired` — clock skew; fail immediately (log warning about clock sync)

### Backoff Formula

```
delay = min(base_delay * (2 ** attempt) + random_jitter(0, 1), max_delay)
```

This matches AWS best practices (Bedrock UG p.2449-2451).

---

## Timeout Strategy

### Orchestrator Timeout Constants (unchanged)

| Mode | Timeout | Source |
|------|---------|--------|
| CLI-prompt skills | 300s | `DEFAULT_TIMEOUT_SECONDS` in `claude_transport.py` |
| TAPM skills | 1200s | `TAPM_TIMEOUT_SECONDS` in `skill_runtime.py` |

### Bedrock-Specific Timeout Considerations

- Bedrock does not expose a server-side timeout parameter in the Chat Completions API
- The client must enforce timeouts via HTTP client configuration (`httpx` timeout or `requests` timeout)
- For streaming responses, set both a connection timeout (30s) and a read timeout (per-chunk, 60s)
- Total request timeout should match the orchestrator's mode-specific constant

### Implementation

```python
# Non-streaming
timeout = httpx.Timeout(connect=30.0, read=timeout_seconds, write=30.0, pool=30.0)

# Streaming
timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
# Plus a total wall-clock guard at the ToolLoop level
```

---

## Rate Limits And Quotas

### Default Quotas

- Quotas are per-account, per-region, per-model
- Default limits are not publicly enumerated per model — they depend on regional factors, payment history, and account age
- Quota increase requests are submitted via AWS console > Service Quotas

### Service Tiers

| Tier | Commitment | Use Case |
|------|-----------|----------|
| **Standard** | Pay-per-token, no commitment | Development, testing |
| **Priority** | Time-based commitment | Higher throughput production |
| **Flex** | Lower cost, flexible scheduling | Non-time-sensitive batch |
| **Reserved** | Term commitment, dedicated throughput | Predictable production workloads |

Phase E implementation should use **Standard** tier initially. No provisioning required.

### Rate Limit Detection

Rate limits manifest as `ThrottlingException` (HTTP 429). The retry strategy above handles this. No proactive rate limit header parsing is documented for `bedrock-mantle`.

---

## Model Identifier Rules

### Bedrock Model ID Format

```
<provider>.<model-name>[-<version>]
```

Examples:
- `anthropic.claude-sonnet-4-20250514-v1:0`
- `anthropic.claude-3-5-sonnet-20240620-v1:0`
- `meta.llama3-1-70b-instruct-v1:0`
- `deepseek.v3.2`
- `writer.palmyra-x5`

### Model ID in Chat Completions Request

The `model` parameter in the Chat Completions request uses the Bedrock model ID directly:

```json
{"model": "anthropic.claude-sonnet-4-20250514-v1:0"}
```

### Key Models for Proposal Orchestrator

| Model | Bedrock ID | Use Case |
|-------|-----------|----------|
| Claude Sonnet 4 | `anthropic.claude-sonnet-4-20250514-v1:0` | Primary skill/agent model |
| Llama 3.1 70B | `meta.llama3-1-70b-instruct-v1:0` | Cost-optimized alternative |

### Model Lifecycle

- **Active:** Full production support
- **Legacy:** Extended access period, then end-of-life
- Lifecycle status is listed in the Bedrock console model catalog

---

## Regional Constraints

### Inference Options

| Option | Data Residency | Throughput | Latency |
|--------|---------------|-----------|---------|
| **In-Region** | Strict — single region | Baseline | Lowest |
| **Geo Cross-Region** | Within geography (US, EU, APAC) | Higher | Moderate |
| **Global Cross-Region** | Worldwide | Maximum | Variable |

### EU-Compliant Regions (for Horizon Europe proposals)

| Region | Code | In-Region | Geo |
|--------|------|-----------|-----|
| Frankfurt | `eu-central-1` | Yes | Yes |
| Stockholm | `eu-north-1` | Yes | Yes |
| Milan | `eu-south-1` | Yes | Yes |
| Ireland | `eu-west-1` | Yes | Yes |
| London | `eu-west-2` | Yes | Yes |
| Paris | `eu-west-3` | Yes | Yes |

### Geo Cross-Region: EU

- Source region: `eu-west-1` (Ireland)
- Destination regions: `eu-central-1`, `eu-north-1`, `eu-south-1`, `eu-west-1`, `eu-south-2`, `eu-west-3`
- Data never leaves EU geography

### Recommendation for Proposal Orchestrator

Use **`eu-west-1` (Ireland)** with **Geo Cross-Region** inference for EU data residency compliance with higher throughput. Fall back to **In-Region** if strict single-region residency is required by institutional policy.

### Model Availability by Region

Not all models are available in all regions. Model availability must be verified in the Bedrock console for the target region before configuring the backend. Claude models are generally available in `us-east-1`, `us-west-2`, and `eu-west-1`.

---

## Required Environment Variables

```bash
# --- Bedrock Transport (bedrock-mantle endpoint) ---
AWS_REGION=eu-west-1
OPENAI_API_KEY=<bedrock-api-key>
OPENAI_BASE_URL=https://bedrock-mantle.eu-west-1.api.aws/v1

# --- Orchestrator Backend Selection ---
ORCHESTRATOR_TRANSPORT_BACKEND=openai_compatible
ORCHESTRATOR_TRANSPORT_ENDPOINT=https://bedrock-mantle.eu-west-1.api.aws/v1
ORCHESTRATOR_TRANSPORT_API_KEY=<bedrock-api-key>
ORCHESTRATOR_TRANSPORT_DEFAULT_MODEL=anthropic.claude-sonnet-4-20250514-v1:0
```

The `OPENAI_API_KEY` and `OPENAI_BASE_URL` variables are set for direct OpenAI SDK usage. The `ORCHESTRATOR_TRANSPORT_*` variables are consumed by the Proposal Orchestrator's backend configuration layer (`runner/transport/config.py`).

---

## Backend Integration Mapping

### Architecture Position

```
OpenAICompatBackend
  |
  +-- Together AI  (api.together.ai, Bearer token)
  +-- AWS Bedrock  (bedrock-mantle.<region>.api.aws, Bedrock API key)  <-- Phase E
  +-- Ollama       (localhost:11434, no auth)
```

### Affected Components

| Component | Path | Change Required |
|-----------|------|----------------|
| Backend config | `runner/transport/config.py` | Add Bedrock as a named configuration preset |
| OpenAI compat backend | `runner/transport/openai_compatible.py` | None — Bedrock uses the same HTTP transport |
| Tool loop | `runner/transport/tool_loop.py` | None — Bedrock returns standard tool_calls format |
| Tool executor | `runner/transport/tool_executor.py` | None — local tool execution is backend-agnostic |
| Skill runtime | `runner/skill_runtime.py` | None — calls backend through transport abstraction |
| Semantic dispatch | `runner/semantic_dispatch.py` | None — calls backend through transport abstraction |
| Claude transport | `runner/claude_transport.py` | None — remains as Claude CLI fallback backend |
| DAG scheduler | `runner/dag_scheduler.py` | None |
| Gate evaluator | `runner/gate_evaluator.py` | None |
| Agent runtime | `runner/agent_runtime.py` | None |

### What Changes

1. **`runner/transport/config.py`** — Add a `bedrock` preset that instantiates `OpenAICompatibleTransport` with:
   - `base_url` from `ORCHESTRATOR_TRANSPORT_ENDPOINT` (or default `https://bedrock-mantle.<AWS_REGION>.api.aws/v1`)
   - `api_key` from `ORCHESTRATOR_TRANSPORT_API_KEY`
   - `default_model` from `ORCHESTRATOR_TRANSPORT_DEFAULT_MODEL`

2. **Error normalization** — Map Bedrock-specific HTTP error responses to orchestrator failure categories (see Error Handling Strategy above). This may require a thin error-mapping layer in the OpenAI-compatible backend or in a Bedrock-specific subclass.

3. **Model ID validation** — Add validation that Bedrock model IDs follow the `<provider>.<model>` format when the `bedrock` preset is active.

### What Does NOT Change

- DAG scheduler, gate evaluator, 102 deterministic predicates
- 5-step node dispatch contract
- Artifact schema validation, atomic writes
- SkillResult/AgentResult/NodeExecutionResult contracts
- Constitutional authority hierarchy
- Gate semantics, HARD_BLOCK propagation, fail-closed behaviour
- Call slicer (Step 0) and dependency normalizer
- Tool loop and tool executor
- All 1600+ existing tests (transport-agnostic; mock `invoke_claude_text`)

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Model not available in target EU region | Medium | Verify model availability in Bedrock console before deployment; fall back to `us-east-1` for testing |
| Bedrock API key rate limits insufficient for TAPM tool loops | Medium | Monitor `ThrottlingException` frequency; request quota increase if needed |
| Streaming tool call accumulation differs from Together AI | Low | Bedrock uses standard OpenAI SSE format; test with actual tool-calling skills |
| `response_format` / JSON mode not supported on `bedrock-mantle` for all models | Low | Orchestrator does not depend on JSON mode; post-validation handles this |
| Clock skew causing `RequestExpired` errors | Low | Ensure NTP sync on deployment host |
| Bedrock API key rotation during long-running orchestration | Low | Use short-term auto-refresh keys in production |

---

## Unknowns Requiring Validation

1. **Exact rate limits for target model in target region.** Default quotas are not publicly listed per model. Must be determined empirically or via AWS console after account setup.

2. **Streaming `usage` field availability.** Confirm that `bedrock-mantle` returns token usage in the final streaming chunk with `stream_options: {"include_usage": true}`. If not, usage accounting may require a separate mechanism.

3. **Tool call ID format.** Confirm that Bedrock's `tool_calls[].id` values are stable and unique per request, as the ToolLoop uses these IDs for result correlation.

4. **Maximum request body size.** Bedrock may impose a maximum request payload size. TAPM prompts can reach 30KB; verify this is within limits.

5. **`top_k` parameter support.** Some Bedrock models support `top_k` in addition to `top_p`. Confirm whether `bedrock-mantle` passes this through or silently ignores it.

6. **EU Geo Cross-Region model availability.** Confirm that Claude models are routable via Geo inference from `eu-west-1`.

---

## Minimal Implementation Plan

| Step | Action | Files Affected |
|------|--------|---------------|
| 1 | Add `bedrock` preset to backend config | `runner/transport/config.py` |
| 2 | Add Bedrock error-code-to-failure-category mapping | `runner/transport/openai_compatible.py` or new `runner/transport/bedrock_errors.py` |
| 3 | Add Bedrock model ID validation helper | `runner/transport/config.py` |
| 4 | Add integration test: non-streaming Chat Completions against `bedrock-mantle` | `tests/integration/test_bedrock_transport.py` |
| 5 | Add integration test: streaming Chat Completions against `bedrock-mantle` | `tests/integration/test_bedrock_transport.py` |
| 6 | Add integration test: tool calling round-trip via ToolLoop against `bedrock-mantle` | `tests/integration/test_bedrock_tool_loop.py` |
| 7 | Run single-phase orchestration (Phase 1) with `ORCHESTRATOR_TRANSPORT_BACKEND=bedrock` and compare outputs against Claude CLI baseline | Manual validation |
| 8 | Document validated configuration in `docs/backend/bedrock_validated_config.md` | New file |

---

*Implementation brief complete. Ready for engineering.*
