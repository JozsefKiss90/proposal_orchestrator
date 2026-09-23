---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-model-identifiers"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/foundation-models-reference.md"
source_title: "Foundation models reference / Model IDs"
retrieval_query: "Bedrock model IDs Anthropic Claude model identifiers supported models list foundation model IDs cross-region inference"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "model_identifiers"
components:
  - "foundation-model"
  - "model-id"
  - "inference-profile"
  - "cross-region"
notes:
  - "Model IDs extracted from Context7 code examples and model card pages"
  - "Not a comprehensive list — only IDs that appeared in Context7 retrieval results"
---

# Bedrock Model Identifiers

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/foundation-models-reference.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-4-1.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/global-cross-region-inference.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_InvokeModel_AnthropicClaude_section.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Bedrock model IDs Anthropic Claude model identifiers supported models list foundation model IDs cross-region inference"

## Retrieved Documentation

### Model ID Format

To use a foundation model with the Amazon Bedrock API, you need the appropriate model ID. Base models use the format:

```
{provider}.{model-name}-{version}
```

### Retrieved Anthropic Claude Model IDs

The following model IDs were observed in Context7 retrieval results:

| Model | Model ID |
|-------|----------|
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` |
| Claude Sonnet 4.6 | `anthropic.claude-sonnet-4-6-v1` |
| Claude Opus 4.1 | `anthropic.claude-opus-4-1-20250805-v1:0` |
| Claude Sonnet 4.5 | `anthropic.claude-sonnet-4-5-20250929-v1:0` (via global inference) |

### Cross-Region Inference IDs

For cross-region inference, use IDs with a geographic or global prefix:

- **Global inference prefix:** `global.{model-id}`
  - Example: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Geo inference prefix:** `us.{model-id}` (or other region prefix)
  - Example: `us.anthropic.claude-opus-4-1-20250805-v1:0`

Note: Global inference is not supported for all models. For example, Anthropic Claude Opus 4.1 supports geo inference (`us.`) but not global inference.

### Cross-Region Inference Example

```python
import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
response = bedrock.converse(
    messages=[{"role": "user", "content": [{"text": "Explain cloud computing in 2 sentences."}]}],
    modelId=model_id,
)

print("Response:", response['output']['message']['content'][0]['text'])
print("Token usage:", response['usage'])
print("Total tokens:", response['usage']['totalTokens'])
```

### Model ID Usage Contexts

- **Base model IDs:** Used for direct foundation model invocation.
- **Cross-region inference profile IDs:** Used when invoking models from the supported inference profiles page.
- **Provisioned throughput:** Requires specific model IDs or custom model ARNs.
- **Endpoint URL format:** `https://bedrock-runtime.{region}.amazonaws.com`

### Programmatic Access (Opus 4.1 Example)

- **Model ID:** `anthropic.claude-opus-4-1-20250805-v1:0`
- **Endpoint URL:** `https://bedrock-runtime.{region}.amazonaws.com`
- **Geo inference ID:** `us.anthropic.claude-opus-4-1-20250805-v1:0`
- **Global inference:** Not supported for this model.

## Integration Relevance

- **Backend transport:** The `modelId` parameter is required for every Converse and InvokeModel call. The model ID format determines whether the request uses direct invocation, cross-region inference, or provisioned throughput.
- **Authentication:** No model-ID-specific authentication differences. IAM policies can be scoped to specific model ARNs.
- **Request construction:** The `modelId` field is a top-level parameter in both `converse()` and `invoke_model()` calls.
- **Response parsing:** No model-ID-specific parsing differences.
- **Error handling:** Invalid model IDs result in `ValidationException` or `ResourceNotFoundException`.
- **Streaming:** Same model IDs apply to streaming variants.
- **Tool use:** Not all models support tool use. Model capability must be verified independently.
