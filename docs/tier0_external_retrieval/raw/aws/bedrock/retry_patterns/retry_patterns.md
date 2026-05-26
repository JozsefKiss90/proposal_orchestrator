---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-retry-patterns"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.md"
source_title: "Scaling and throughput best practices / Configure retry strategy"
retrieval_query: "error handling retry patterns rate limits throttling guidance request throttling exception handling"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "retry_patterns"
components:
  - "botocore.config.Config"
  - "retries"
  - "exponential-backoff"
notes: []
---

# Retry Patterns

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/invoke-imported-model.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "error handling retry patterns rate limits throttling guidance request throttling exception handling"

## Retrieved Documentation

### SDK Retry Configuration

Configure the AWS SDK for Python (boto3) retry behavior using `botocore.config.Config`:

```python
import boto3
from botocore.config import Config

config = Config(retries={"total_max_attempts": 6, "mode": "standard"})
client = boto3.client("bedrock-runtime", config=config)
```

### Retry Configuration for ModelNotReadyException

For imported or custom models that may not be immediately ready:

```python
import json
import boto3
from botocore.config import Config

REGION_NAME = "us-east-1"
MODEL_ID = "arn:aws:bedrock:us-east-1:123456789012:imported-model/model-id"

config = Config(
    retries={
        'total_max_attempts': 10,  # customizable
        'mode': 'standard'
    }
)

session = boto3.session.Session()
br_runtime = session.client(
    service_name='bedrock-runtime',
    region_name=REGION_NAME,
    config=config
)

try:
    invoke_response = br_runtime.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({'prompt': "Hello"}),
        accept="application/json",
        contentType="application/json"
    )
    invoke_response["body"] = json.loads(invoke_response["body"].read().decode("utf-8"))
    print(json.dumps(invoke_response, indent=4))
except Exception as e:
    print(e)
```

### Retry Configuration Fields

- `total_max_attempts` (integer) — Maximum number of retry attempts including the initial request. Recommended: 6 for general use, up to 10 for `ModelNotReadyException`.
- `mode` (string) — Retry mode. Value: `"standard"` — uses exponential backoff with jitter.

### Exponential Backoff Strategy

For transient errors (occasional 503 responses):
1. Start with a short delay.
2. Double the delay after each failed attempt.
3. Add random jitter to prevent thundering herd.
4. Limit retries to 6 attempts.
5. Most AWS SDKs and popular HTTP libraries support this pattern natively.

### When NOT to Retry

For sustained 503 errors, retrying will not solve the issue. Instead:
- Reduce request submission rate.
- Implement client-side rate limiting or request queuing.
- Shed lower-priority requests.

## Integration Relevance

- **Backend transport:** The `botocore.config.Config` retry configuration should be applied when creating the Bedrock Runtime client. This enables automatic retry with exponential backoff for transient failures.
- **Authentication:** No retry-specific authentication implications.
- **Request construction:** Retry configuration is a client-level setting, not per-request.
- **Response parsing:** Retried requests return the same response format as initial requests.
- **Error handling:** The `standard` retry mode handles transient errors automatically. Application code should still handle non-retryable errors (sustained 503, 429).
- **Streaming:** Retry applies to the initial request. A failed mid-stream connection requires re-initiating the entire streaming request.
- **Tool use:** Each API call in a tool use conversation is independently subject to retry behavior.
