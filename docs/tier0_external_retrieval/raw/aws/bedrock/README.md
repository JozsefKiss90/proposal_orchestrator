# AWS Bedrock — Context7-Only Retrieval Corpus

## Purpose

This corpus contains **only Context7-derived external retrieval** from the authoritative AWS Bedrock User Guide documentation.

## Exclusions

- **Local AWS folders are intentionally excluded.** No local markdown files, PDFs, or developer guide snapshots stored in this repository were inspected, referenced, or used as source material.
- **No local validation was performed.** The content in this corpus has not been cross-validated against any local documentation.
- **No memory-derived information is included.** All content was retrieved via Context7 queries against the `/websites/aws_amazon_bedrock_userguide` library.

## Objective

This corpus exists to **measure Context7 retrieval capability** for AWS Bedrock documentation. It establishes a baseline of what Context7 can independently resolve and retrieve from authoritative external sources.

## Provenance

- **Context7 Library ID:** `/websites/aws_amazon_bedrock_userguide`
- **Source Reputation:** High
- **Benchmark Score:** 78.7
- **Code Snippets Available:** 8,698
- **Manifest:** `docs/tier0_external_retrieval/context7_manifest/aws_bedrock_sources.json`

## Corpus Structure

```
raw/aws/bedrock/
├── runtime/           # Bedrock Runtime service overview
├── converse/          # Converse API documentation
├── invoke_model/      # InvokeModel API and Claude boto3 invocation
├── auth/              # IAM requirements and authentication
├── model_ids/         # Model identifiers and cross-region inference
├── streaming/         # Streaming invocation (ConverseStream, InvokeModelWithResponseStream)
├── tool_use/          # Tool use / toolConfig
├── guardrails/        # Guardrails configuration
├── schemas/           # Request and response schemas
├── error_handling/    # Error handling patterns
├── regional_endpoints/# Regional endpoint configuration
├── rate_limits/       # Rate limits and throttling guidance
└── retry_patterns/    # Retry configuration patterns
```

## File Format

Every file in this corpus includes:

1. **YAML frontmatter** with schema ID `orch.external.context7.snapshot.v1`, Context7 provenance metadata, and retrieval status.
2. **Retrieval Provenance** section documenting the exact Context7 library ID, source URLs, retrieval timestamp, and query.
3. **Retrieved Documentation** section containing only material returned by Context7 queries.
4. **Integration Relevance** section describing implications for backend transport, authentication, request construction, response parsing, error handling, streaming, and tool use.

## Coverage Limitations

All 16 target topics received Context7 retrieval results. However, coverage depth varies:

- **Strong coverage:** Converse API, InvokeModel API, Claude boto3 invocation, streaming, tool use, guardrails, error handling, retry patterns, rate limits.
- **Partial coverage:** Model IDs (only IDs appearing in examples, not comprehensive list), request/response schemas (extracted from examples, not dedicated schema reference), authentication (derived from IAM examples), regional endpoints (format and cross-region patterns, not full availability list).
