---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-claude-boto3-invocation"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_InvokeModel_AnthropicClaude_section.md"
source_title: "Invoke Anthropic Claude Model with Python SDK"
retrieval_query: "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "claude_boto3_invocation"
components:
  - "InvokeModel"
  - "Converse"
  - "boto3"
  - "anthropic.claude"
notes:
  - "Covers both InvokeModel (native) and Converse API patterns for Claude"
---

# Anthropic Claude Invocation via boto3

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_InvokeModel_AnthropicClaude_section.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-3-haiku.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"

## Retrieved Documentation

### InvokeModel (Native API) Pattern

Uses the model's native request format with `anthropic_version` and `messages` fields.

```python
import boto3
import json
from botocore.exceptions import ClientError

# Create a Bedrock Runtime client in the AWS Region of your choice.
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Set the model ID, e.g., Claude 3 Haiku.
model_id = "anthropic.claude-3-haiku-20240307-v1:0"

# Define the prompt for the model.
prompt = "Describe the purpose of a 'hello world' program in one line."

# Format the request payload using the model's native structure.
native_request = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 512,
    "temperature": 0.5,
    "messages": [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    ],
}

# Convert the native request to JSON.
request = json.dumps(native_request)

try:
    # Invoke the model with the request.
    response = client.invoke_model(modelId=model_id, body=request)
except (ClientError, Exception) as e:
    print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
    exit(1)

# Decode the response body.
model_response = json.loads(response["body"].read())

# Extract and print the response text.
response_text = model_response["content"][0]["text"]
print(response_text)
```

### Converse API Pattern

Uses the unified Converse API with structured `messages` parameter.

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

### Key Differences

| Aspect | InvokeModel (Native) | Converse API |
|--------|---------------------|--------------|
| Request body | Model-native JSON with `anthropic_version` | Unified `messages` structure |
| Content format | `[{"type": "text", "text": "..."}]` | `[{"text": "..."}]` |
| Response parsing | `response["body"].read()` + JSON parse | Direct dict access `response["output"]` |
| Anthropic version | Required: `"bedrock-2023-05-31"` | Not required |
| Recommended | When native control needed | General use |

### Required Native Request Fields for Claude

- `anthropic_version`: `"bedrock-2023-05-31"` (required)
- `max_tokens`: integer (required)
- `messages`: array of message objects (required)
- `temperature`: float (optional)

## Integration Relevance

- **Backend transport:** Two invocation paths exist for Claude on Bedrock. The Converse API is preferred for new integrations due to its unified interface.
- **Authentication:** Both patterns use the same boto3 client with IAM credentials.
- **Request construction:** The native API requires `anthropic_version: "bedrock-2023-05-31"` and model-specific content formatting. The Converse API uses a simpler, unified format.
- **Response parsing:** Native API requires reading the response body stream. Converse API returns a structured dict.
- **Error handling:** Both raise `ClientError` from botocore.
- **Streaming:** Native streaming uses `invoke_model_with_response_stream()`. Converse streaming uses `converse_stream()`.
- **Tool use:** The Converse API is recommended for tool use integrations.
