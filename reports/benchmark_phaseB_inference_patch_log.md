# Phase B Inference Patch Log

**Date:** 2026-05-19
**Branch:** `benchmark_enginge`

## Bug Summary

Phase B analytics produced empty `phases_observed`, `nodes_observed`, `per_phase`, and `per_node` when invocation ledger records lacked `node_id` (which is the case for all Phase A records). `phases_1_7_estimated_total_tokens` was 0 despite all invocations belonging to Phase 1.

Root causes:
1. `_enrich_with_phase()` only set `_phase` — it never inferred or assigned `node_id`, so per-node aggregation was always empty for records without explicit `node_id`.
2. `build_token_economics()` called `_enrich_with_phase(r, None)` — hardcoded `None` for `run_summary`, making phase inference always fail for records without `node_id`.

## Files Changed

| File | Change |
|------|--------|
| `runner/benchmark/analytics.py` | Replaced `_enrich_with_phase` + `_infer_phase_from_run_summary` with `_enrich_record` + `_resolve_single_node` implementing full A-E inference precedence. Added `run_summary` and `phase_a_summary` params to `build_token_economics`. |
| `runner/benchmark/report_builder.py` | Pass `run_summary` and `phase_a_summary` to `build_token_economics()` call (1-line change). |
| `tests/runner/benchmark/test_analytics.py` | Added `TestInferenceSingleNode` (8 tests), `TestInferenceAmbiguousMultiNode` (4 tests), and 1 token economics inference test. |
| `tests/runner/benchmark/test_report_builder.py` | Added `TestReportBuilderInference` (2 tests). |
| `tests/runner/benchmark/test_phase_b_integration.py` | Added 4 fixture regression tests: `test_phase_analytics_nodes_observed`, `test_per_phase_invocations`, `test_per_node_invocations`, `test_phases_1_7_token_total`. |

## Inference Precedence Implemented

When a record lacks `node_id`:

| Step | Source | Condition | Assigns |
|------|--------|-----------|---------|
| A | record.node_id | exists | phase from prefix; keep node_id |
| B | run_summary.phase_scope_nodes | exactly 1 entry | that node_id + phase_scope |
| C | run_summary.dispatched_nodes | exactly 1 entry | that node_id + phase from prefix or phase_scope |
| D | phase_a_summary.node_records | exactly 1 dispatched entry | that node_id + phase from prefix |
| E | (multiple nodes possible) | ambiguous | node_id=None; phase from phase_scope only |

## Tests Added

- `TestInferenceSingleNode`: 8 tests covering B/C/D paths and explicit node_id preservation
- `TestInferenceAmbiguousMultiNode`: 4 tests for multi-node safety + malformed summary resilience
- `TestBuildTokenEconomics.test_phases_1_7_with_inference_from_run_summary`: 1 test
- `TestReportBuilderInference`: 2 end-to-end report builder inference tests
- `TestPhaseBIntegrationWithRealFixtures`: 4 new fixture regression tests

**Total new tests: 19**

## Test Results

| Suite | Result |
|-------|--------|
| `tests/runner/benchmark/test_analytics.py` | 34 passed |
| `tests/runner/benchmark/test_report_builder.py` | 17 passed |
| `tests/runner/benchmark/test_phase_b_integration.py` | 17 passed |
| All benchmark tests | 151 passed |
| Full test suite | 2712 passed, 7 failed (pre-existing), 2 skipped |

Zero new regressions.

## Confirmations

- Phase A collection unchanged: `transport_hook.py`, `ledger.py`, `context.py`, `models.py`, `token_estimator.py` not modified
- `runner/claude_transport.py` not modified
- `runner/dag_scheduler.py` not modified
- No provider projection, routing, or transport abstraction added
- No prompt/response content stored in any artifact

## Final Validation Checklist

- [x] Phase 1 analytics now reports phases_observed [1]
- [x] Phase 1 analytics now reports node n01_call_analysis
- [x] per_phase["1"].invocations == 4 for fixture
- [x] per_node["n01_call_analysis"].invocations == 4 for fixture
- [x] phases_1_7_estimated_total_tokens == total_estimated_tokens for fixture
- [x] ambiguous multi-node cases do not assign arbitrary node_id
- [x] records with explicit node_id still work
- [x] Phase A collection unchanged
- [x] no provider projection/routing/transport abstraction added
