---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-regional-endpoint-config"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.md"
source_title: "Endpoints supported by Amazon Bedrock"
retrieval_query: "Bedrock Runtime API overview supported operations Converse InvokeModel endpoints service quotas regional availability"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "regional_endpoint_configuration"
components:
  - "bedrock-runtime"
  - "endpoint"
  - "cross-region"
  - "global-inference"
notes:
  - "Regional availability list not retrieved — only endpoint format and cross-region patterns"
---

# Regional Endpoint Configuration

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/global-cross-region-inference.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-4-1.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Bedrock Runtime API overview supported operations Converse InvokeModel endpoints service quotas regional availability"

## Retrieved Documentation

### Endpoint Format

The Bedrock Runtime endpoint follows this format:

```
https://bedrock-runtime.{region}.amazonaws.com
```

Examples:
- `https://bedrock-runtime.us-east-1.amazonaws.com`
- `https://bedrock-runtime.us-west-2.amazonaws.com`

### Client Configuration

The region is specified when creating the boto3 client:

```python
import boto3

# Direct regional access
client = boto3.client("bedrock-runtime", region_name="us-east-1")
```

### Cross-Region Inference

Cross-region inference allows routing requests across multiple regions for higher availability:

**Global inference prefix:** `global.{model-id}`
```python
model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

**Geo inference prefix:** `{geo}.{model-id}` (e.g., `us.`)
```python
model_id = "us.anthropic.claude-opus-4-1-20250805-v1:0"
```

### Cross-Region Example

```python
import boto3

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
response = bedrock.converse(
    messages=[{"role": "user", "content": [{"text": "Explain cloud computing in 2 sentences."}]}],
    modelId=model_id,
)

print("Response:", response['output']['message']['content'][0]['text'])
print("Token usage:", response['usage'])
```

### Model-Specific Endpoint Notes

Not all models support all inference modes:
- Some models support global inference (`global.` prefix).
- Some models support geo inference only (`us.` prefix).
- Some models support neither (direct regional invocation only).

Example (Claude Opus 4.1):
- Model ID: `anthropic.claude-opus-4-1-20250805-v1:0`
- Geo inference ID: `us.anthropic.claude-opus-4-1-20250805-v1:0`
- Global inference: Not supported.

## Integration Relevance

- **Backend transport:** The `region_name` parameter in the boto3 client constructor determines the endpoint. For cross-region inference, use model ID prefixes (`global.` or `us.`) instead of changing the client region.
- **Authentication:** IAM policies can be scoped to specific regions via resource ARNs.
- **Request construction:** Region is a client-level configuration, not a per-request parameter. Cross-region routing is controlled via the model ID prefix.
- **Response parsing:** No region-specific response differences.
- **Error handling:** Regional capacity constraints may cause HTTP 503 errors. Spreading traffic across regions can mitigate this.
- **Streaming:** Same regional configuration applies to streaming endpoints.
- **Tool use:** No regional configuration differences for tool use.
