---
schema_id: "orch.external.context7.snapshot.v1"
doc_id: "aws-bedrock-tool-use-config"
provider: "aws"
service: "bedrock"
retrieval_method: "context7"
context7_library_id: "/websites/aws_amazon_bedrock_userguide"
source_url: "https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.md"
source_title: "Tool use with Amazon Bedrock"
retrieval_query: "Converse API tool use toolConfig toolChoice function calling tool_use content block tool result"
retrieved_at_utc: "2026-05-24T14:30:00Z"
validated_at_utc: "2026-05-24T14:30:00Z"
source_origin: "external"
authoritative_source: true
snapshot_generated: true
memory_generated: false
local_sources_allowed: false
retrieval_status: "retrieved"
topic: "tool_use"
components:
  - "toolConfig"
  - "toolSpec"
  - "tool_use"
  - "tool_result"
  - "Converse"
notes:
  - "Converse API is the recommended interface for tool use"
---

# Tool Use / toolConfig

## Retrieval Provenance

- **Context7 Library ID:** /websites/aws_amazon_bedrock_userguide
- **Source URLs:**
  - https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/claude-messages-extended-thinking.md
  - https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-tool-use.md
- **Retrieved UTC:** 2026-05-24T14:30:00Z
- **Query:** "Converse API tool use toolConfig toolChoice function calling tool_use content block tool result"

## Retrieved Documentation

### Overview

To enable tool use, configure the `toolConfig` parameter when calling the `converse` API. The Converse API is recommended for integrating tool use into applications.

### toolConfig Structure

```json
{
    "toolConfig": {
        "tools": [
            {
                "toolSpec": {
                    "name": "get_weather",
                    "description": "Get the current weather for a specified location",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state, e.g. San Francisco, CA"
                                },
                                "unit": {
                                    "type": "string",
                                    "enum": ["fahrenheit", "celsius"],
                                    "description": "The temperature unit to use"
                                }
                            },
                            "required": ["location", "unit"]
                        }
                    }
                }
            }
        ]
    }
}
```

### toolSpec Fields

- `name` (string, required) — The name of the tool.
- `description` (string, required) — Description of what the tool does.
- `inputSchema` (object, required) — JSON Schema defining expected input properties.
  - `json` (object) — The JSON Schema object with `type`, `properties`, and `required`.
- `strict` (boolean, optional) — When `true`, ensures the model adheres precisely to the provided input schema.

### Strict Tool Use

Setting `strict: true` on a `toolSpec` ensures the model adheres precisely to the provided input schema:

```json
{
    "toolSpec": {
        "name": "get_weather",
        "description": "Get the current weather for a specified location",
        "strict": true,
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state"
                    }
                },
                "required": ["location"]
            }
        }
    }
}
```

### Tool Use with Cache Points

The `cachePoint` field can be placed within `toolConfig` to enable caching for tool definitions:

```json
{
    "toolConfig": {
        "tools": [
            {
                "toolSpec": {
                    "name": "top_song",
                    "description": "Get the most popular song played on a radio station.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "sign": {
                                    "type": "string",
                                    "description": "The call sign for the radio station."
                                }
                            },
                            "required": ["sign"]
                        }
                    }
                }
            },
            {
                "cachePoint": {
                    "type": "default"
                }
            }
        ]
    }
}
```

### Tool Use with Extended Thinking

When using tool use with extended thinking enabled, the conversation must preserve `thinking` and `tool_use` blocks from previous assistant responses:

```json
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 10000,
    "thinking": {
        "type": "enabled",
        "budget_tokens": 4000
    },
    "tools": [
        {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": { "type": "string" }
                },
                "required": ["location"]
            }
        }
    ],
    "messages": [
        {
            "role": "user",
            "content": "What's the weather in Paris?"
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "thinking",
                    "thinking": "The user wants to know the current weather in Paris...",
                    "signature": "BDaL4VrbR2Oj0hO4XpJxT28J5TILnCrrUXoKiiNBZW9P..."
                },
                {
                    "type": "tool_use",
                    "id": "toolu_01CswdEQBMshySk6Y9DFKrfq",
                    "name": "get_weather",
                    "input": { "location": "Paris" }
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01CswdEQBMshySk6Y9DFKrfq",
                    "content": "Current temperature: 88°F"
                }
            ]
        }
    ]
}
```

### Tool Use Content Blocks

- `tool_use` — Assistant response block requesting tool invocation. Contains `id`, `name`, and `input`.
- `tool_result` — User message block providing the result of a tool invocation. Contains `tool_use_id` and `content`.
- `thinking` — Reasoning block (when extended thinking is enabled). Contains `thinking` text and `signature`.

## Integration Relevance

- **Backend transport:** Tool use is a Converse API feature. The `toolConfig` parameter must be passed alongside `messages` and `modelId` in the `converse()` call.
- **Authentication:** No additional IAM actions required for tool use beyond standard `bedrock:InvokeModel`.
- **Request construction:** Tools are defined in `toolConfig.tools` with `toolSpec` entries. Each spec requires `name`, `description`, and `inputSchema`. The `strict` flag enables strict schema adherence.
- **Response parsing:** When the model decides to use a tool, the response content includes a `tool_use` block with `id`, `name`, and `input`. The client must execute the tool and return a `tool_result` in the next message.
- **Error handling:** Standard Converse API error handling applies.
- **Streaming:** Tool use is supported in streaming via `contentBlockDelta` events with `toolUse` delta type.
- **Tool use:** The conversation must be multi-turn: send initial message → receive `tool_use` → execute tool → send `tool_result` → receive final response.
