---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-runtime-overview"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.md"
source_title: "Endpoints supported by Amazon Bedrock / APIs supported by Amazon Bedrock"
retrieval_query: "Bedrock Runtime API overview supported operations Converse InvokeModel endpoints service quotas regional availability"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "bedrock_runtime_overview"
components:
  - "bedrock-runtime"
  - "Converse"
  - "InvokeModel"
  - "ConverseStream"
  - "InvokeModelWithResponseStream"
notes:
  - "Aggregated from multiple Context7 retrieval results"
---

# Bedrock Runtime Overview

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/apis.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api-ex-cli.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Bedrock Runtime API overview supported operations Converse InvokeModel endpoints service quotas regional availability"

## Retrieved Documentation

### Service Endpoint

The `bedrock-runtime` endpoint is used for running any model supported by Amazon Bedrock.

Endpoint format: `bedrock-runtime.{region}.amazonaws.com`

### Supported APIs

The `bedrock-runtime` endpoint provides access to the following APIs:

1. **Converse API** — A unified interface for all models supporting messages. Recommended over InvokeModel when supported. Simplifies multi-turn conversations.

2. **Invoke API (InvokeModel)** — For single transactions and large payloads with direct model access. Offers more control over request/response formats.

3. **Messages API** — Anthropic-native interface via InvokeModel.

4. **Chat Completions API** — OpenAI-compatible stateless chat.

### Converse vs InvokeModel

The Converse API provides a unified inference request interface across Bedrock models. It is recommended over InvokeModel when the model supports it. InvokeModel provides direct model access with more control over request/response formats.

### CLI Example (Converse)

```bash
aws bedrock-runtime converse \
--model-id amazon.nova-lite-v1:0 \
--messages '[{"role": "user", "content": [{"text": "Describe the purpose of a \"hello world\" program in one line."}]}]' \
--inference-config '{"maxTokens": 512, "temperature": 0.5, "topP": 0.9}'
```

### Streaming Operations

- `ConverseStream` — Streaming variant of the Converse API
- `InvokeModelWithResponseStream` — Streaming variant of InvokeModel

Both support client-side tool use and allow tracking usage and costs.

## Integration Relevance

- **Backend transport:** The `bedrock-runtime` endpoint is the primary service endpoint for model invocation. Transport must target `bedrock-runtime.{region}.amazonaws.com`.
- **Authentication:** All API calls require IAM-based authentication via AWS credentials.
- **Request construction:** Two paradigms exist — Converse API (unified, recommended) and InvokeModel (native, model-specific payloads).
- **Response parsing:** Converse API returns structured `output.message.content` objects. InvokeModel returns model-native JSON.
- **Error handling:** Standard AWS SDK error handling applies (ClientError, HTTP 429/503).
- **Streaming:** Both Converse and InvokeModel support streaming variants.
- **Tool use:** Supported via `toolConfig` parameter in Converse API.
