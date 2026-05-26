---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-error-handling-patterns"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.md"
source_title: "Scaling and throughput best practices / Understanding HTTP error responses"
retrieval_query: "error handling retry patterns rate limits throttling guidance request throttling exception handling"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "error_handling"
components:
  - "ClientError"
  - "ModelNotReadyException"
  - "HTTP-429"
  - "HTTP-503"
notes: []
---

# Error Handling Patterns

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/invoke-imported-model.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_InvokeModel_AnthropicClaude_section.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "error handling retry patterns rate limits throttling guidance request throttling exception handling"

## Retrieved Documentation

### HTTP Error Responses

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 429 | RPM limit exceeded | Reduce request rate or request increase via Service Quotas console |
| 503 (transient) | Increased demand in the Region | Retry with exponential backoff |
| 503 (sustained) | Request rate exceeds available throughput | Reduce request submission rate; retrying will not help |

### Exception Types

- **`ClientError`** (botocore) — General AWS SDK error for API failures.
- **`ModelNotReadyException`** — Raised when an imported/custom model is not yet ready for inference.
- **`AmazonBedrockRuntimeException`** (.NET SDK) — .NET equivalent of runtime errors.
- **`SdkClientException`** (Java SDK) — Java SDK client-side errors.

### Python Error Handling Pattern

```python
from botocore.exceptions import ClientError

try:
    response = client.invoke_model(modelId=model_id, body=request)
except (ClientError, Exception) as e:
    print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
    exit(1)
```

### Error Response Metadata

```python
except ClientError as err:
    message = err.response['Error']['Message']
    request_id = err.response['ResponseMetadata']['RequestId']
    logger.error("A client error occurred: %s", message)
```

### Transient Error Strategy

Implement exponential backoff with random jitter:
- Start with a short delay.
- Double the delay after each failed attempt.
- Limit retries to 6 attempts.
- Most AWS SDKs and popular HTTP libraries support this pattern.

### Sustained Error Strategy

When 503 errors are sustained, retrying will not solve the issue:
- Reduce request submission rate.
- Implement client-side rate limiting or request queuing.
- Shed lower-priority requests.

## Integration Relevance

- **Backend transport:** Transport layer must handle `ClientError` exceptions and differentiate between transient (retryable) and sustained (non-retryable) error conditions.
- **Authentication:** `AccessDeniedException` indicates missing IAM permissions.
- **Request construction:** Invalid request payloads result in `ValidationException`.
- **Response parsing:** Error responses include `Error.Message` and `ResponseMetadata.RequestId`.
- **Error handling:** Implement exponential backoff with jitter for transient 503 errors. Do not retry sustained 503s. HTTP 429 requires rate reduction.
- **Streaming:** Errors may occur mid-stream, interrupting event delivery.
- **Tool use:** No tool-use-specific error handling differences.
