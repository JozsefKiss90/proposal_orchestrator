# Retrieval Logs

## Purpose

This directory records the outcomes of Context7 retrieval attempts for external documentation acquisition.

## Retrieval Coverage Measurement Objective

The retrieval process is designed to measure what Context7 can independently resolve and retrieve from authoritative external documentation sources. This includes:

- **Successful retrievals** — Topics where Context7 returned relevant documentation from the target library.
- **Failed retrievals** — Topics where Context7 returned no relevant results or insufficient results.
- **Partial retrievals** — Topics where Context7 returned some relevant information but coverage was incomplete.

## Constraints

- **No memory-derived information is permitted.** If Context7 cannot retrieve information for a topic, it is recorded as missing or partially covered. No information from training data, prior knowledge, or local sources is substituted.
- **No local source validation.** Retrieved content is not cross-referenced against local documentation to measure retrieval quality in isolation.
- **Provenance is mandatory.** Every retrieval result is traceable to a specific Context7 query, library ID, and source URL.

## Retrieval Session: 2026-05-24

### Context7 Library Resolution

- **Query:** "AWS Bedrock"
- **Resolved Library ID:** `/websites/aws_amazon_bedrock_userguide`
- **Source Reputation:** High
- **Benchmark Score:** 78.7
- **Status:** Successfully resolved

### Topic Retrieval Summary

| # | Topic | Status | Notes |
|---|-------|--------|-------|
| 1 | Bedrock Runtime overview | Retrieved | Endpoint format, supported APIs |
| 2 | Converse API | Retrieved | Full request/response, code examples |
| 3 | InvokeModel API | Retrieved | Full request/response, code examples |
| 4 | Anthropic Claude via boto3 | Retrieved | Native and Converse patterns |
| 5 | AWS IAM requirements | Retrieved | IAM actions, policy examples, ARN formats |
| 6 | Model IDs | Retrieved | Partial — only IDs from examples |
| 7 | Streaming invocation | Retrieved | ConverseStream events, Python/.NET/JS examples |
| 8 | Tool use / toolConfig | Retrieved | toolSpec, strict mode, cachePoint, thinking |
| 9 | Guardrails | Retrieved | Converse and InvokeModel patterns |
| 10 | Request schemas | Retrieved | Partial — from examples, not schema reference |
| 11 | Response schemas | Retrieved | Partial — from examples, not schema reference |
| 12 | Error handling patterns | Retrieved | HTTP 429/503, exception types |
| 13 | Authentication requirements | Retrieved | Partial — derived from IAM examples |
| 14 | Regional endpoint config | Retrieved | Partial — format and cross-region, not availability |
| 15 | Rate limits / throttling | Retrieved | Transient/sustained error strategies |
| 16 | Retry patterns | Retrieved | botocore Config, exponential backoff |

### Failed Retrievals

No complete retrieval failures occurred. All 16 topics received at least partial Context7 results.

### Retrieval Failure Log Files

- `context7_resolution_failed.md` — Created only if Context7 library resolution fails. Not generated for this session.
