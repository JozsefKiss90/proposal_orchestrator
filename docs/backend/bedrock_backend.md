# AWS Bedrock Backend — Configuration Guide

**Status:** Phase E implementation
**Transport:** `bedrock-mantle` OpenAI-compatible endpoint
**Backend class:** `OpenAICompatBackend` (configuration variant, not a separate class)

---

## Quick Start

```bash
export ORCHESTRATOR_TRANSPORT_BACKEND=bedrock
export ORCHESTRATOR_TRANSPORT_API_KEY=<your-bedrock-api-key>

# Optional: override defaults
export ORCHESTRATOR_TRANSPORT_MODEL=anthropic.claude-sonnet-4-20250514-v1:0
export AWS_REGION=eu-west-1
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORCHESTRATOR_TRANSPORT_BACKEND` | Yes | `claude_cli` | Set to `bedrock` to enable Bedrock transport |
| `ORCHESTRATOR_TRANSPORT_API_KEY` | Yes | — | Bedrock API key (generated in Amazon Bedrock console) |
| `ORCHESTRATOR_TRANSPORT_ENDPOINT` | No | `https://bedrock-mantle.<AWS_REGION>.api.aws/v1` | Override the base URL |
| `ORCHESTRATOR_TRANSPORT_MODEL` | No | `anthropic.claude-sonnet-4-20250514-v1:0` | Bedrock model ID |
| `AWS_REGION` | No | `eu-west-1` | AWS region for default URL construction |

---

## How It Works

Bedrock is a **configuration variant** of `OpenAICompatBackend`, not a separate transport class. The same `POST /v1/chat/completions` pathway used by Together AI and Ollama is used for Bedrock via the `bedrock-mantle` endpoint.

```
OpenAICompatBackend
  ├── Together AI  (api.together.ai, Bearer token)
  ├── AWS Bedrock  (bedrock-mantle.<region>.api.aws, Bedrock API key)
  └── Ollama       (localhost:11434, no auth)
```

Authentication uses `Authorization: Bearer <API_KEY>`, identical to Together AI. No IAM Signature V4 is required at request time.

---

## Model ID Format

Bedrock model IDs follow the `<provider>.<model>[-<version>]` format:

```
anthropic.claude-sonnet-4-20250514-v1:0
meta.llama3-1-70b-instruct-v1:0
deepseek.v3.2
```

The config layer validates this format. Standard model names like `claude-sonnet-4` (without provider prefix) will be rejected.

---

## Known Limitations

1. **Streaming usage accounting is UNVERIFIED.** `stream_options: {"include_usage": true}` support on `bedrock-mantle` is not confirmed by documentation. Non-streaming usage fields (`prompt_tokens`, `completion_tokens`, `total_tokens`) are confirmed. If streaming usage is absent, it is recorded as `None` without failing the run.

2. **Short-term API key generation may require IAM credentials.** Long-term keys generated via the Bedrock console have no IAM runtime dependency and are recommended for initial setup. Short-term key rotation can be added as a production hardening step.

3. **Native `bedrock-runtime` Converse/InvokeModel API is out of Phase E scope.** Phase E uses `bedrock-mantle` exclusively for OpenAI compatibility.

4. **EU region model availability.** Claude model availability in EU regions via `bedrock-mantle` should be verified in the Bedrock console before production deployment.

---

## Dependencies

The OpenAI-compatible backend requires `httpx`:

```bash
pip install httpx
```

The Claude CLI backend (`claude_cli`) does not require `httpx`. The import is deferred so that the Claude CLI path continues to work without it.

---

## Switching Back to Claude CLI

```bash
unset ORCHESTRATOR_TRANSPORT_BACKEND
# or explicitly:
export ORCHESTRATOR_TRANSPORT_BACKEND=claude_cli
```

The Claude CLI transport (`runner/claude_transport.py`) is unchanged and remains the default backend.

---

## What Is NOT Changed

- DAG scheduler, gate evaluator, agent runtime
- 102 deterministic predicates
- 5-step node dispatch contract
- Artifact schema validation, atomic writes
- SkillResult / AgentResult / NodeExecutionResult contracts
- ToolLoop and ToolExecutor
- TAPM semantics
- All existing tests (transport-agnostic; mock `invoke_claude_text`)

---

*Phase E implementation. See `docs/backend/phase_e_bedrock_implementation_brief.md` for the full specification.*
