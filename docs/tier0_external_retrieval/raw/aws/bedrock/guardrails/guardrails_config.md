---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-guardrails-config"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-converse-api.md"
source_title: "Use guardrails with the Converse API"
retrieval_query: "IAM requirements authentication model IDs regional endpoints streaming invocation tool use toolConfig guardrails configuration"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "guardrails"
components:
  - "guardrailConfig"
  - "guardrailIdentifier"
  - "guardrailVersion"
  - "guardContent"
  - "streamProcessingMode"
notes:
  - "Guardrails supported on both Converse and InvokeModel APIs"
---

# Guardrails Configuration

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-converse-api.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-test.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-mmfilter.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-openai.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "IAM requirements authentication model IDs regional endpoints streaming invocation tool use toolConfig guardrails configuration"

## Retrieved Documentation

### Guardrails with Converse API

The `guardrailConfig` parameter is used to apply guardrails when calling the Converse API:

```python
guardrail_config = {
    "guardrailIdentifier": guardrail_id,
    "guardrailVersion": guardrail_version,
    "trace": "enabled"
}

response = bedrock_client.converse(
    modelId=model_id,
    messages=messages,
    guardrailConfig=guardrail_config
)
```

**guardrailConfig fields:**

- `guardrailIdentifier` (string, required) — The ID of the guardrail to apply.
- `guardrailVersion` (string, required) — The version of the guardrail (e.g., `"DRAFT"` or a version number).
- `trace` (string, optional) — Set to `"enabled"` to enable trace for guardrail activity.
- `streamProcessingMode` (string, optional) — For streaming: `"sync"` or `"async"`.

### Guard Content in Messages

Use `guardContent` within message content to specify text that should be assessed by the guardrail:

```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "text": "Only answer with a list of songs.",
            },
            {
                "guardContent": {
                    "text": {
                        "text": "Create a playlist of 2 heavy metal songs."
                    }
                }
            }
        ]
    }
]
```

### Guardrails with InvokeModel API

For InvokeModel, guardrails are applied via request parameters and request body:

**Request parameters:**
- `guardrailIdentifier` — Guardrail ID.
- `guardrailVersion` — Guardrail version.
- `trace` — Set to `'ENABLED'` for trace.

**Request body:**
```json
{
    "amazon-bedrock-guardrailConfig": {
        "tagSuffix": "string",
        "streamProcessingMode": "SYNCHRONOUS | ASYNCHRONOUS"
    }
}
```

**InvokeModel headers (for direct API calls):**
- `X-Amzn-Bedrock-GuardrailIdentifier` — Guardrail identifier.
- `X-Amzn-Bedrock-GuardrailVersion` — Guardrail version.
- `X-Amzn-Bedrock-Trace` — Set to `ENABLED` for trace.

### InvokeModel Python Example with Guardrails

```python
import boto3
import json

bedrock_runtime = boto3.client("bedrock-runtime")

response = bedrock_runtime.invoke_model(
    modelId=model_id,
    body=json.dumps(native_request),
    guardrailIdentifier=guardrail_id,
    guardrailVersion=guardrail_version,
    trace='ENABLED',
)
```

### Guardrail Response Handling

When a guardrail intervenes:

- `stopReason` is set to `"guardrail_intervened"` in the Converse API response.
- `amazon-bedrock-guardrailAction` is `"INTERVENED"` or `"NONE"` in InvokeModel responses.
- Trace information is available in `response['trace']['guardrail']` when trace is enabled.

```python
if response['stopReason'] == "guardrail_intervened":
    trace = response['trace']
    print("Guardrail trace:")
    print(json.dumps(trace['guardrail'], indent=4))
```

### Streaming with Guardrails

```python
guardrail_config = {
    "guardrailIdentifier": guardrail_id,
    "guardrailVersion": guardrail_version,
    "trace": "enabled",
    "streamProcessingMode": "sync"
}

response = bedrock_client.converse_stream(
    modelId=model_id,
    messages=messages,
    guardrailConfig=guardrail_config
)

stream = response.get('stream')
if stream:
    for event in stream:
        if 'messageStart' in event:
            print(f"\nRole: {event['messageStart']['role']}")
        if 'contentBlockDelta' in event:
            print(event['contentBlockDelta']['delta']['text'], end="")
        if 'messageStop' in event:
            print(f"\nStop reason: {event['messageStop']['stopReason']}")
        if 'metadata' in event:
            metadata = event['metadata']
            if 'trace' in metadata:
                print(json.dumps(metadata['trace'], indent=4))
```

### Guardrail Error Conditions

- An error occurs if the guardrail is enabled but `amazon-bedrock-guardrailConfig` is missing from the request body.
- An error occurs if the guardrail is disabled but `amazon-bedrock-guardrailConfig` is present in the request body.
- An error occurs if the guardrail is enabled but `contentType` is not `application/json`.

## Integration Relevance

- **Backend transport:** Guardrails are an optional layer applied at the API level. They do not change the transport mechanism but add parameters to requests and additional fields to responses.
- **Authentication:** No additional IAM actions required for guardrail application beyond standard invocation permissions.
- **Request construction:** Converse API uses `guardrailConfig` dict parameter. InvokeModel uses `guardrailIdentifier` and `guardrailVersion` parameters plus `amazon-bedrock-guardrailConfig` in the request body.
- **Response parsing:** Responses may include `guardrail_intervened` stop reason and trace data. Parsing logic must handle the case where guardrail intervention replaces normal model output.
- **Error handling:** Mismatched guardrail configuration (enabled without config, or config without enabled) causes errors.
- **Streaming:** Streaming with guardrails supports `streamProcessingMode` of `"sync"` or `"async"`. Trace data appears in `metadata` events.
- **Tool use:** Guardrails and tool use can be combined in the same Converse API call.
