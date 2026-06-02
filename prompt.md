
● Here's a summary of the fix:

  Changes Made

  Root Cause

  The benchmark hook (transport_hook.py) only wrapped invoke_claude_text() — the Claude CLI transport. When the Bedrock backend (OpenAICompatBackend or
  BedrockConverseBackend) was active, LLM calls went through run_tool_loop(backend=...) or backend(messages) directly, completely bypassing the instrumentation layer.
  Result: 0 invocations and 0 tokens recorded for all Bedrock runs.

  Fix: InstrumentedBackend wrapper class

  runner/benchmark/transport_hook.py — Added InstrumentedBackend, a ToolLoopBackend-conforming wrapper that:
  - Records a BenchmarkInvocationRecord for every __call__ (each tool-loop round = one record)
  - Uses actual last_usage token counts from the backend when available (Bedrock returns prompt_tokens/completion_tokens)
  - Falls back to character-based estimation when last_usage is absent
  - Zero overhead when benchmarking is disabled (get_ledger() is None)
  - Preserves return values and exception semantics exactly
  - Proxies last_usage, model, url properties for callers

  runner/skill_runtime.py — Wrapped backends with InstrumentedBackend at all 4 non-Claude construction sites:
  - Bedrock Converse TAPM path
  - OpenAI-compatible TAPM path
  - Bedrock Converse cli-prompt path
  - OpenAI-compatible cli-prompt path

  runner/semantic_dispatch.py — Wrapped backends at both non-Claude call sites in _invoke_via_backend().

  Tests

  tests/runner/benchmark/test_transport_hook.py — 13 new tests covering:
  - Passthrough when benchmarking disabled
  - Telemetry recording (success, errors, timeouts)
  - Actual usage from last_usage vs. char-based fallback
  - Multiple rounds each get unique records
  - Semantic predicate metadata
  - No prompt content leakage
  - Benchmark failure isolation (never blocks backend operation)

  Results: 239 passed, 33 skipped (0 new failures introduced). The 51 pre-existing test failures in test_skill_runtime*.py are caused by the .env file setting
  ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US, which existed before this change.
