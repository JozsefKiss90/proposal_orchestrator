---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-invoke-model-api"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/inference-messages-api.md"
source_title: "InvokeModel API / Messages API"
retrieval_query: "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "invoke_model_api"
components:
  - "InvokeModel"
  - "invoke_model()"
  - "bedrock-runtime"
notes:
  - "InvokeModel uses model-native request/response formats"
---

# InvokeModel API

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/inference-messages-api.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_InvokeModel_AnthropicClaude_section.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"

## Retrieved Documentation

### Overview

The `InvokeModel` API provides direct model access using the model's native request/response format. It offers more control over request/response formats compared to the Converse API.

### Endpoint

```
POST /invoke-model
Endpoint: https://bedrock-runtime.{region}.amazonaws.com
```

### Request Parameters

- `modelId` (string, required) — The model ID to use (e.g., `anthropic.claude-sonnet-4-6-v1`).
- `body` (bytes/string, required) — The model's native request payload as JSON.
- `accept` (string, optional) — MIME type for the response body. Default: `application/json`.
- `contentType` (string, optional) — MIME type for the request body. Default: `application/json`.
- `guardrailIdentifier` (string, optional) — Guardrail identifier to apply.
- `guardrailVersion` (string, optional) — Guardrail version to apply.
- `trace` (string, optional) — Set to `'ENABLED'` for guardrail trace.

### Anthropic Claude Native Request Body

```json
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1024,
    "temperature": 0.5,
    "messages": [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Your prompt here"}]
        }
    ]
}
```

**Request body fields:**

- `anthropic_version` (string, required) — Set to `"bedrock-2023-05-31"`.
- `max_tokens` (integer, required) — Maximum number of tokens to generate.
- `temperature` (float, optional) — Sampling temperature.
- `messages` (array, required) — Array of message objects.
  - `role` (string) — `"user"` or `"assistant"`.
  - `content` (array) — Array of content blocks, each with `type` and `text`.

### Response Structure

```json
{
    "content": [
        {
            "type": "text_block",
            "text": "Response text here."
        }
    ],
    "role": "assistant"
}
```

**Response fields:**

- `content` (array) — Array of content blocks.
  - `type` (string) — Content block type (e.g., `"text_block"`).
  - `text` (string) — The generated text.
- `role` (string) — Always `"assistant"`.

### Python boto3 Example

```python
import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

model_id = "anthropic.claude-sonnet-4-6-v1"

response = client.invoke_model(
    modelId=model_id,
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": "Explain quantum computing in one sentence."}
        ]
    })
)

result = json.loads(response["body"].read())
print(result["content"][0]["text"])
```

### Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.invoke_model(modelId=model_id, body=request)
except (ClientError, Exception) as e:
    print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
```

## Integration Relevance

- **Backend transport:** InvokeModel sends model-native payloads. The transport must serialize the model-specific JSON body and pass it as the `body` parameter.
- **Authentication:** Standard IAM-based authentication via boto3 client.
- **Request construction:** Body must be JSON-serialized and model-specific. For Anthropic Claude, requires `anthropic_version`, `max_tokens`, and `messages` fields.
- **Response parsing:** Response body is a streaming object; must call `response["body"].read()` and JSON-parse the result. Content is in `content[0]["text"]`.
- **Error handling:** Catches `ClientError` from botocore.
- **Streaming:** Use `invoke_model_with_response_stream()` for streaming.
- **Tool use:** For tool use, the Converse API is recommended over InvokeModel.
