---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-converse-api"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.md"
source_title: "Converse API / Conversation inference"
retrieval_query: "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "converse_api"
components:
  - "Converse"
  - "converse()"
  - "bedrock-runtime"
notes:
  - "Converse API is the recommended unified interface for Bedrock model invocation"
---

# Converse API

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-openai.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-3-haiku.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"

## Retrieved Documentation

### Overview

The Converse API (`converse`) provides a unified interface for conversational interactions across all Bedrock models that support messages. It is the recommended approach over `InvokeModel` when supported.

### Request Structure

```python
response = client.converse(
    modelId=model_id,
    messages=messages,
    system=system,
    inferenceConfig={
        "maxTokens": 150,
        "temperature": 0.7,
        "topP": 0.9
    },
)
```

**Parameters:**

- `modelId` (string, required) — The unique identifier of the model.
- `messages` (list, required) — A list of message objects representing the conversation history.
  - `role` (string, required) — The role of the message sender (`"user"` or `"assistant"`).
  - `content` (list, required) — The content of the message.
    - `text` (string) — The text content of the message.
- `system` (list, optional) — System prompt.
  - `text` (string) — The system prompt text.
- `inferenceConfig` (dict, optional) — Inference configuration.
  - `maxTokens` (integer) — Maximum number of tokens to generate.
  - `temperature` (float) — Sampling temperature.
  - `topP` (float) — Top-p sampling parameter.
- `toolConfig` (dict, optional) — Tool use configuration.
- `guardrailConfig` (dict, optional) — Guardrail configuration.

### Response Structure

```json
{
    "output": {
        "message": {
            "role": "assistant",
            "content": [
                {
                    "text": "Response text here..."
                }
            ]
        }
    },
    "stopReason": "end_turn",
    "usage": {
        "inputTokens": 22,
        "outputTokens": 123,
        "totalTokens": 145
    },
    "metrics": {
        "latencyMs": 100.0
    }
}
```

**Response fields:**

- `output.message.role` — Always `"assistant"`.
- `output.message.content` — Array of content blocks, each with a `text` field.
- `stopReason` — Reason the model stopped generating (e.g., `"end_turn"`, `"max_tokens"`, `"guardrail_intervened"`).
- `usage` — Token usage metrics (`inputTokens`, `outputTokens`, `totalTokens`).
- `metrics` — Latency metrics.

### Python boto3 Example

```python
import boto3

client = boto3.client('bedrock-runtime', region_name='us-east-1')
response = client.converse(
    modelId='anthropic.claude-3-haiku-20240307-v1:0',
    messages=[
        {
            'role': 'user',
            'content': [{'text': 'Can you explain the features of Amazon Bedrock?'}]
        }
    ]
)
print(response)
```

### AWS CLI Example

```bash
aws bedrock-runtime converse \
--model-id amazon.nova-lite-v1:0 \
--messages '[{"role": "user", "content": [{"text": "Describe the purpose of a \"hello world\" program in one line."}]}]' \
--inference-config '{"maxTokens": 512, "temperature": 0.5, "topP": 0.9}'
```

## Integration Relevance

- **Backend transport:** The Converse API is the recommended unified interface. It abstracts model-specific payload formats.
- **Authentication:** Standard IAM-based authentication via boto3 client.
- **Request construction:** Structured `messages` array with `role` and `content` fields. Supports `system`, `inferenceConfig`, `toolConfig`, and `guardrailConfig`.
- **Response parsing:** Response is in `output.message.content` array. Each content block has a `text` field. Token usage is in `usage`.
- **Error handling:** Raises `ClientError` (botocore) on failure.
- **Streaming:** Use `converse_stream()` for streaming responses.
- **Tool use:** Supported via `toolConfig` parameter.
