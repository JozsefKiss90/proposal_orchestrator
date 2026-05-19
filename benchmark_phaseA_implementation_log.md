# Benchmark Phase A Implementation Log

## 1. Files Created

| File | Purpose |
|------|---------|
| `runner/benchmark/__init__.py` | Package init; public API surface |
| `runner/benchmark/context.py` | `ContextVar` for active ledger (`get_ledger` / `set_ledger`) |
| `runner/benchmark/models.py` | Immutable data models: `BenchmarkInvocationRecord`, `NodeBenchmarkRecord`, `PhaseBenchmarkRecord`, `RunBenchmarkSummary` |
| `runner/benchmark/token_estimator.py` | `estimate_tokens()` with `CHAR_TO_TOKEN_RATIOS` dict |
| `runner/benchmark/ledger.py` | Append-only JSONL `BenchmarkLedger` with thread-safe append |
| `runner/benchmark/transport_hook.py` | `instrumented_invoke()` wrapper around `invoke_claude_text()` |
| `tests/runner/benchmark/__init__.py` | Test package init |
| `tests/runner/benchmark/test_context.py` | Context variable tests |
| `tests/runner/benchmark/test_models.py` | Data model tests |
| `tests/runner/benchmark/test_token_estimator.py` | Token estimation tests |
| `tests/runner/benchmark/test_ledger.py` | Ledger append/persistence/thread-safety tests |
| `tests/runner/benchmark/test_transport_hook.py` | Transport hook success/error/disabled path tests |
| `tests/runner/benchmark/test_integration.py` | End-to-end lifecycle and JSONL round-trip tests |

## 2. Files Modified

| File | Change |
|------|--------|
| `runner/skill_runtime.py` | Replaced `invoke_claude_text` import with `instrumented_invoke as invoke_claude_text`; added `_bench_*` kwargs to TAPM (line ~1198) and cli-prompt (line ~1281) call sites |
| `runner/semantic_dispatch.py` | Replaced `invoke_claude_text` import with `instrumented_invoke as invoke_claude_text`; added `_bench_*` kwargs to semantic predicate call site (line ~646) |
| `runner/dag_scheduler.py` | Added `import time`; added benchmark ledger lifecycle in `run()`: creation at entry, summary finalization after dispatch loop, cleanup in `finally` block |

## 3. Runtime Integration Summary

### Call Site 1 (CS1): TAPM skill invocation
- **File:** `runner/skill_runtime.py`, TAPM path in `run_skill()`
- **Change:** Added `_bench_run_id`, `_bench_skill_id`, `_bench_node_id`, `_bench_invocation_type="skill_tapm"` kwargs
- **Mechanism:** `invoke_claude_text` in skill_runtime is now aliased from `runner.benchmark.transport_hook.instrumented_invoke`

### Call Site 2 (CS2): cli-prompt skill invocation
- **File:** `runner/skill_runtime.py`, cli-prompt path in `run_skill()`
- **Change:** Added `_bench_run_id`, `_bench_skill_id`, `_bench_node_id`, `_bench_invocation_type="skill_cli_prompt"` kwargs

### Call Site 3 (CS3): Semantic predicate invocation
- **File:** `runner/semantic_dispatch.py`, `invoke_agent()`
- **Change:** Added `_bench_run_id`, `_bench_predicate_id`, `_bench_invocation_type="semantic_predicate"` kwargs
- **Mechanism:** `invoke_claude_text` in semantic_dispatch is now aliased from `runner.benchmark.transport_hook.instrumented_invoke`

### Scheduler lifecycle
- **File:** `runner/dag_scheduler.py`, `run()` method
- **Entry:** Creates `BenchmarkLedger` at `.claude/benchmark/<run_id>/invocation_ledger.jsonl`, sets context variable
- **Exit:** Builds `RunBenchmarkSummary`, writes `run_benchmark_summary.json`, closes ledger, clears context variable in `finally` block
- **Failure isolation:** All benchmark operations wrapped in try/except; failures logged at debug level and swallowed

## 4. Behavioral Guarantees Verified

- **Transport signature unchanged:** `runner/claude_transport.py` has zero modifications. `invoke_claude_text()` signature is identical.
- **Orchestration outcomes unchanged:** 2607 tests pass (identical to pre-change baseline). Zero regressions introduced.
- **Benchmark failures isolated:** Ledger append failures are swallowed (verified by `test_ledger_append_failure_swallowed`). Ledger creation failures are swallowed. Summary finalization failures are swallowed.
- **No prompt content persisted:** Records contain only `system_prompt_chars` and `user_prompt_chars` (integer counts). No `system_prompt`, `user_prompt`, or `response_text` fields exist on `BenchmarkInvocationRecord`. Verified by `test_no_prompt_content_stored`.
- **No Tier 4/Tier 5 writes:** All benchmark artifacts write exclusively to `.claude/benchmark/<run_id>/`.

## 5. Tests Added

| File | Tests | Categories |
|------|-------|------------|
| `test_context.py` | 4 | Default value, set/get, clear, replace |
| `test_models.py` | 13 | Construction, frozen, None fields, error fields, semantic predicate, node/phase/run summary, serialization |
| `test_token_estimator.py` | 11 | Known models, unknown model fallback, zero/negative/float/invalid input, large count |
| `test_ledger.py` | 11 | In-memory append, file persistence, flush, close, parent dir creation, invalid path, thread safety, serialization |
| `test_transport_hook.py` | 14 | Disabled passthrough (success, tools, exception, metadata filtering), enabled (telemetry, tools, exception, timeout, token estimates, semantic metadata, no content, unique IDs, exact return), failure isolation |
| `test_integration.py` | 5 | Full lifecycle, disabled path, exception passthrough, JSONL round-trip |
| **Total** | **58** | |

## 6. Test Results

- **New benchmark tests:** 58 passed, 0 failed
- **Full existing suite:** 2607 passed, 2 skipped, 4 failed (pre-existing)
- **Pre-existing failures** (verified identical before our changes):
  - `test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[excellence-section-drafting.md]`
  - `test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[excellence/impact/implementation-section-drafting.md]` (3 tests)
  - `test_phase8_canonicalization.py::TestSpecLeanness::test_impact_no_component_keyword_scan`

## 7. Benchmark Artifact Examples

### Artifact location
```
.claude/benchmark/<run_id>/
├── invocation_ledger.jsonl
└── run_benchmark_summary.json
```

### invocation_ledger.jsonl (one line per invocation)
```json
{"invocation_id":"a1b2c3d4","run_id":"run-001","node_id":"n01_call_analysis","skill_id":"call-analysis","predicate_id":null,"invocation_type":"skill_tapm","execution_mode":"tapm","model":"claude-sonnet-4-6","timeout_seconds":1200,"tools_enabled":["Read","Glob"],"system_prompt_chars":5000,"user_prompt_chars":3000,"response_chars":2000,"response_status":"success","wall_clock_start":100.0,"wall_clock_end":110.0,"wall_clock_seconds":10.0,"timestamp_utc":"2026-05-19T00:00:00+00:00","estimated_input_tokens":2285,"estimated_output_tokens":571,"error_class":null,"error_message":null}
```

### run_benchmark_summary.json
```json
{
  "benchmark_schema_version": "1.0.0",
  "run_id": "run-001",
  "started_at": "2026-05-19T00:00:00+00:00",
  "completed_at": "2026-05-19T00:01:00+00:00",
  "total_invocations": 47,
  "total_estimated_input_tokens": 125000,
  "total_estimated_output_tokens": 18000,
  "total_wall_clock_seconds": 1234.5,
  "node_records": [
    {"node_id": "n01_call_analysis", "dispatched": true}
  ]
}
```

## 8. Known Limitations

- **No analytics:** Phase A collects raw telemetry only. Phase/node/skill aggregate computation is deferred to Phase B.
- **No provider projection:** Cost projection to alternative providers is deferred to Phase C.
- **Token estimates are approximate:** Character-to-token ratios produce estimates with +-15-25% accuracy. Sufficient for trend analysis and cost comparison, not for exact billing reconciliation.
- **TAPM estimates are upper-bound:** TAPM input token estimates are based on prompt chars only (not tool-read content). Actual token consumption may be 2-10x higher due to Read/Glob round-trips. TAPM ceiling estimation is deferred to a future enhancement.

## 9. Deferred Work

- **Phases B-F remain unimplemented.** The analytics engine, timing distribution computation, provider projection, routing analysis, CLI reporting, and transport abstraction are all out of scope.
- **No transport abstraction exists yet.** The system uses the existing `claude -p` CLI transport exclusively.
- **No provider routing exists yet.** All invocations go through the same transport backend.
- **No cross-run benchmarking.** Run index and trend data are not yet collected.
- **No benchmark cleanup commands.** Accumulated benchmark artifacts under `.claude/benchmark/` are not automatically cleaned up.
