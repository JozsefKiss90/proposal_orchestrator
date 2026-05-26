---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-request-schemas"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/inference-messages-api.md"
source_title: "Bedrock Runtime request schemas"
retrieval_query: "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "request_schemas"
components:
  - "Converse"
  - "InvokeModel"
  - "request-body"
  - "inferenceConfig"
notes:
  - "Request schemas extracted from Context7 retrieval across multiple queries"
  - "Coverage is partial — limited to fields observed in retrieved examples"
---

# Request Schemas

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/inference-messages-api.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-runtime_example_bedrock-runtime_InvokeModel_AnthropicClaude_section.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Bedrock Runtime overview Converse API InvokeModel API request response schemas Anthropic Claude model invocation boto3 code examples"

## Retrieved Documentation

### Converse API Request Schema

```python
response = client.converse(
    modelId="string",                    # Required
    messages=[                           # Required
        {
            "role": "user" | "assistant",
            "content": [
                {"text": "string"},
                {"guardContent": {"text": {"text": "string"}}}
            ]
        }
    ],
    system=[                             # Optional
        {"text": "string"}
    ],
    inferenceConfig={                    # Optional
        "maxTokens": int,
        "temperature": float,
        "topP": float
    },
    toolConfig={                         # Optional
        "tools": [
            {
                "toolSpec": {
                    "name": "string",
                    "description": "string",
                    "strict": bool,      # Optional
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
            },
            {
                "cachePoint": {"type": "default"}  # Optional
            }
        ]
    },
    guardrailConfig={                    # Optional
        "guardrailIdentifier": "string",
        "guardrailVersion": "string",
        "trace": "enabled",
        "streamProcessingMode": "sync" | "async"
    }
)
```

### InvokeModel API Request Schema (Anthropic Claude Native)

```python
response = client.invoke_model(
    modelId="string",                    # Required
    body=json.dumps({                    # Required - model-native JSON
        "anthropic_version": "bedrock-2023-05-31",  # Required
        "max_tokens": int,               # Required
        "temperature": float,            # Optional
        "messages": [                    # Required
            {
                "role": "user" | "assistant",
                "content": [
                    {"type": "text", "text": "string"}
                ]
                # Or for tool results:
                # "content": [
                #     {"type": "tool_result", "tool_use_id": "string", "content": "string"}
                # ]
            }
        ],
        "thinking": {                    # Optional (extended thinking)
            "type": "enabled",
            "budget_tokens": int
        },
        "tools": [                       # Optional (native tool use)
            {
                "name": "string",
                "description": "string",
                "input_schema": {}
            }
        ]
    }),
    accept="application/json",           # Optional
    contentType="application/json",      # Optional
    guardrailIdentifier="string",        # Optional
    guardrailVersion="string",           # Optional
    trace="ENABLED"                      # Optional
)
```

### Key Schema Differences

| Field | Converse API | InvokeModel (Claude Native) |
|-------|-------------|---------------------------|
| Content format | `[{"text": "..."}]` | `[{"type": "text", "text": "..."}]` |
| Max tokens | `inferenceConfig.maxTokens` | `max_tokens` (top-level) |
| Temperature | `inferenceConfig.temperature` | `temperature` (top-level) |
| Tool definition | `toolConfig.tools[].toolSpec` | `tools[]` (with `input_schema`) |
| System prompt | `system` parameter | Not in retrieved examples |
| Anthropic version | Not required | Required: `"bedrock-2023-05-31"` |
| Guardrails | `guardrailConfig` parameter | `guardrailIdentifier`/`guardrailVersion` parameters |

## Integration Relevance

- **Backend transport:** Request schema determines the payload structure. The two APIs have fundamentally different request formats.
- **Authentication:** Request schemas do not affect authentication.
- **Request construction:** Converse API requests are SDK-structured (dict parameters). InvokeModel requests require JSON-serialized body strings matching the model's native format.
- **Response parsing:** Different request schemas correspond to different response schemas.
- **Error handling:** Schema violations result in `ValidationException`.
- **Streaming:** Streaming variants (`converse_stream`, `invoke_model_with_response_stream`) use the same request schemas as their non-streaming counterparts.
- **Tool use:** Tool definitions differ between APIs: Converse uses `toolSpec` with `inputSchema.json`, native uses `input_schema` directly.
