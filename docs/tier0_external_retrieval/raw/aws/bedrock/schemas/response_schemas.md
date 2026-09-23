---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-response-schemas"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.md"
source_title: "Bedrock Runtime response schemas"
retrieval_query: "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "response_schemas"
components:
  - "Converse"
  - "InvokeModel"
  - "ConverseStream"
  - "response-body"
notes:
  - "Response schemas extracted from Context7 retrieval across multiple queries"
  - "Coverage is partial — limited to fields observed in retrieved examples"
---

# Response Schemas

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/inference-messages-api.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_InvokeModel_AnthropicClaude_section.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"

## Retrieved Documentation

### Converse API Response Schema

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
    "stopReason": "end_turn | max_tokens | guardrail_intervened",
    "usage": {
        "inputTokens": 22,
        "outputTokens": 123,
        "totalTokens": 145
    },
    "metrics": {
        "latencyMs": 100.0
    },
    "trace": {
        "guardrail": {}
    }
}
```

**Response fields:**

- `output.message.role` (string) — Always `"assistant"`.
- `output.message.content` (array) — Array of content blocks.
  - `text` (string) — Text content.
  - `tool_use` (object) — Tool use request (when model invokes a tool). Contains `id`, `name`, `input`.
- `stopReason` (string) — Reason the model stopped generating. Values: `"end_turn"`, `"max_tokens"`, `"guardrail_intervened"`.
- `usage` (object) — Token usage metrics.
  - `inputTokens` (integer) — Input token count.
  - `outputTokens` (integer) — Output token count.
  - `totalTokens` (integer) — Total token count.
- `metrics` (object) — Performance metrics.
  - `latencyMs` (float) — Latency in milliseconds.
- `trace` (object, optional) — Guardrail trace data (when trace is enabled).

### InvokeModel Response Schema (Anthropic Claude Native)

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

**Accessing the InvokeModel response:**

```python
model_response = json.loads(response["body"].read())
response_text = model_response["content"][0]["text"]
```

### ConverseStream Response Events Schema

Events are emitted in this order:

1. **messageStart:**
   ```json
   {"messageStart": {"role": "assistant"}}
   ```

2. **contentBlockStart** (tool use only):
   ```json
   {"contentBlockStart": {...}}
   ```

3. **contentBlockDelta** (one or more):
   ```json
   {"contentBlockDelta": {"delta": {"text": "partial text"}, "contentBlockIndex": 0}}
   ```
   Delta types: `text`, `reasoningContent`, `toolUse`.

4. **contentBlockStop:**
   ```json
   {"contentBlockStop": {...}}
   ```

5. **messageStop:**
   ```json
   {"messageStop": {"stopReason": "max_tokens"}}
   ```

6. **metadata:**
   ```json
   {
       "metadata": {
           "usage": {"inputTokens": 47, "outputTokens": 20, "totalTokens": 67},
           "metrics": {"latencyMs": 100.0}
       }
   }
   ```

### Key Schema Differences

| Field | Converse Response | InvokeModel Response (Claude) |
|-------|------------------|------------------------------|
| Text access | `output.message.content[0].text` | `content[0].text` |
| Content type | Implicit (text blocks) | Explicit `type` field |
| Token usage | `usage` (top-level) | Not in retrieved examples |
| Metrics | `metrics` (top-level) | Not in retrieved examples |
| Stop reason | `stopReason` (top-level) | Not in retrieved examples |
| Body access | Direct dict | `response["body"].read()` then JSON parse |

## Integration Relevance

- **Backend transport:** Response format depends on the API used. Converse API returns structured dicts; InvokeModel returns a streaming body that must be read and parsed.
- **Authentication:** No response-specific authentication implications.
- **Request construction:** Not applicable.
- **Response parsing:** Converse API: access `response["output"]["message"]["content"]`. InvokeModel: call `response["body"].read()`, then `json.loads()`, then access `content[0]["text"]`.
- **Error handling:** Responses include `stopReason` which may indicate `guardrail_intervened` or `max_tokens`.
- **Streaming:** Stream responses arrive as ordered events. Use `contentBlockIndex` to correlate delta events. Token usage and metrics arrive in the final `metadata` event.
- **Tool use:** Tool use responses include `tool_use` content blocks with `id`, `name`, and `input` fields.
