---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-throttling-guidance"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.md"
source_title: "Scaling and throughput best practices"
retrieval_query: "error handling retry patterns rate limits throttling guidance request throttling exception handling"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "rate_limits_throttling"
components:
  - "HTTP-429"
  - "HTTP-503"
  - "Service-Quotas"
  - "RPM"
notes: []
---

# Rate Limits and Throttling Guidance

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URL:** https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "error handling retry patterns rate limits throttling guidance request throttling exception handling"

## Retrieved Documentation

### HTTP Error Responses

**HTTP 429** — Indicates the requests-per-minute (RPM) limit has been exceeded.
- Action: Reduce request rate.
- Alternative: Request a quota increase via the AWS Service Quotas console.

**HTTP 503 (transient)** — Indicates increased demand in the Region.
- Action: Reduce request rate.
- Action: Retry with exponential backoff.
- Action: Spread traffic across Regions.

**HTTP 503 (sustained)** — Indicates your request rate consistently exceeds available throughput.
- Action: Retrying will not solve the issue.
- Action: Reduce request submission rate.
- Action: Implement client-side rate limiting or request queuing.
- Action: Shed lower-priority requests.

### Throughput Strategies

**For transient errors (occasional 503):**
- Implement exponential backoff with random jitter.
- Start with a short delay, double after each failed attempt.
- Limit retries to 6 attempts.
- Most AWS SDKs and popular HTTP libraries support this pattern.

**For sustained errors (persistent 503):**
- Reduce request submission rate.
- Implement client-side rate limiting.
- Implement request queuing.
- Shed lower-priority requests.

### Service Quotas

The AWS Service Quotas console can be used to request increases to RPM limits.

## Integration Relevance

- **Backend transport:** Transport layer should implement rate awareness: track request rates, detect 429/503 responses, and apply appropriate backoff strategies.
- **Authentication:** No rate-limit-specific authentication implications.
- **Request construction:** Consider implementing request queuing to manage submission rate.
- **Response parsing:** HTTP status codes 429 and 503 indicate throttling conditions before any response body is available.
- **Error handling:** Differentiate transient from sustained errors. Transient: retry with backoff. Sustained: reduce rate.
- **Streaming:** Streaming requests are subject to the same rate limits.
- **Tool use:** Tool use conversations involve multiple API calls (initial + tool result), each counting toward rate limits.
