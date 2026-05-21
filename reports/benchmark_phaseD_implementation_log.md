# Benchmark Phase D Implementation Log — CLI and Human-Readable Reporting

**Date:** 2026-05-20
**Branch:** `benchmark_enginge`
**Phase:** D — CLI and Human-Readable Reporting (read-only)

---

## 1. Files Created

| File | Purpose |
|------|---------|
| `runner/benchmark/__main__.py` | CLI entry point: argparse, artifact loading, section dispatch, --list, --json, exit codes |
| `runner/benchmark/formatters.py` | Pure formatting functions: summary, tokens, timing, providers, routing, quality, full, JSON |
| `tests/runner/benchmark/test_cli.py` | 22 tests: CLI commands, exit codes, partial runs, no writes, no API calls |
| `tests/runner/benchmark/test_formatters.py` | 33 tests: all report sections, quality warnings, JSON output, missing artifacts, Phase 8 incomplete |

## 2. Files Modified

None. No existing files were modified.

## 3. CLI Commands Implemented

| Command | Description |
|---------|-------------|
| `python -m runner.benchmark --run-id <id>` | Full human-readable report |
| `python -m runner.benchmark --run-id <id> --section summary` | Summary section only |
| `python -m runner.benchmark --run-id <id> --section tokens` | Token report only |
| `python -m runner.benchmark --run-id <id> --section timing` | Timing report only |
| `python -m runner.benchmark --run-id <id> --section providers` | Provider projection only |
| `python -m runner.benchmark --run-id <id> --section routing` | Routing advisory only |
| `python -m runner.benchmark --run-id <id> --section quality` | Data quality report only |
| `python -m runner.benchmark --run-id <id> --json` | Merged JSON output |
| `python -m runner.benchmark --list` | List available benchmark runs |
| `python -m runner.benchmark --benchmark-root <path> --list` | Custom benchmark root |

Exit codes:
- 0: report generated (including with quality warnings)
- 1: run_id not found
- 2: invalid CLI arguments
- 3: unexpected internal error

## 4. Report Sections Implemented

### Summary
- Run ID, benchmark stage, timestamps, total invocations
- Estimated input/output/total tokens
- Total wall-clock seconds
- Phases and nodes observed
- Provider projection availability (suitable count, lowest cost)
- Data quality warning count

### Tokens
- Total input/output/total token estimates
- TAPM vs CLI-prompt token split
- Semantic predicate token total
- Phase 8 vs Phases 1-7 token totals
- Top skills by estimated tokens (table)
- Largest invocation by tokens and by prompt chars
- Token-estimation disclaimer

### Timing
- Total wall-clock, sum invocation time, idle estimate
- Mean/median/P95/P99 invocation seconds
- Timeout and failed invocation counts
- Slowest skills by total time (table)

### Providers
- Pricing basis warning (static estimates)
- Observed workload summary
- Recommendations: lowest cost, best capability, best OpenAI-compatible, best private network
- Full provider table: display name, cost, suitable, migration complexity
- Subscription billing marked with `/mo`, infrastructure with `*`
- Not-suitable providers and migration warnings

### Routing Advisory
- Advisory-only disclaimer
- Workload segments with estimated tokens and candidate tier
- Per-segment notes

### Data Quality
- Warning count and numbered list
- Disclaimer: Phase D does not repair issues

## 5. Data Quality Warnings Implemented

| Warning Rule | Condition |
|-------------|-----------|
| Missing artifacts | run_benchmark_summary.json, phase_analytics.json, token_economics.json, timing_profile.json, provider_projection.json, invocation_ledger.jsonl |
| phases_observed empty | total_invocations > 0 but phases_observed is empty |
| nodes_observed empty | node_records has dispatched nodes but nodes_observed is empty |
| Phase 8 tokens zero | n08* nodes present but phase_8_estimated_total_tokens == 0 |
| Phases 1-7 tokens zero | n01-n07 nodes present but phases_1_7_estimated_total_tokens == 0 |
| TAPM count mismatch | provider_projection TAPM count == 0 but token_economics TAPM total > 0 |
| Stale benchmark stage | Stage not phase_b_analytics or phase_c_provider_projection |
| Failed invocations | failed_invocation_count > 0 |
| Timed-out invocations | timeout_count > 0 |

## 6. Partial Run Handling

- All artifact loading uses `_read_json_safe()` returning None on missing/malformed files
- Each formatter checks its input for None and renders a `[WARNING] ... missing` message
- `compute_quality_warnings()` flags all missing artifacts individually
- Partial runs (e.g., only ledger + summary) render available sections with warnings, exit 0
- Empty run directories render a full report with all-missing warnings, exit 0
- JSON mode includes `loaded_artifacts` list and `data_quality_warnings`

## 7. Behavioral Guarantees Verified

- [x] No runtime changes (no modifications to dag_scheduler.py, skill_runtime.py, semantic_dispatch.py, agent_runtime.py)
- [x] No transport abstraction added
- [x] No provider API calls (CLI reads from disk only)
- [x] No routing execution
- [x] No Tier 4 / Tier 5 writes (all reads from `.claude/benchmark/`)
- [x] No prompt/response content persisted or printed (formatters never access prompt text)
- [x] Read-only reporting only (verified by mtime comparison test)
- [x] No modifications to existing benchmark modules (context.py, ledger.py, transport_hook.py, models.py, token_estimator.py, analytics.py, timing.py, report_builder.py, provider_projection.py, routing_analyzer.py)

## 8. Tests Added

| Test File | Test Count | Categories |
|-----------|------------|------------|
| `test_formatters.py` | 33 | Summary (5), tokens (4), timing (3), providers (4), routing (3), quality warnings (6), full report (3), JSON report (3), Phase 8 incomplete (1), no prompt content (1) |
| `test_cli.py` | 22 | Full report (1), sections (6), JSON (2), list (3), exit codes (4), partial artifacts (3), load artifacts (2), no API calls (1), no writes (1) |

**Total new Phase D tests: 55**

## 9. Test Results

### Phase D tests
```
55 passed in 0.52s
```

### All benchmark tests
```
259 passed in 1.62s
```

### Full test suite
```
2821 passed, 8 failed, 2 skipped in 127.15s
```

### Pre-existing failures (not caused by Phase D)
All 8 failures are pre-existing:
- `test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[excellence-section-drafting.md]`
- `test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[impact-section-drafting.md]`
- `test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[implementation-section-drafting.md]`
- `test_phase6_field_production.py::TestComplianceProfileDerivativeLabeling::test_current_artifact_wp9_cites_tier2b_for_ai_on_demand`
- `test_phase8_canonicalization.py::TestSpecLeanness::test_impact_no_component_keyword_scan`
- `test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[excellence-section-drafting.md]`
- `test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[impact-section-drafting.md]`
- `test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[implementation-section-drafting.md]`

**Zero new regressions from Phase D.**

## 10. Known Limitations

- Plain-text reporting only — no HTML, PDF, or dashboard output
- No cleanup/delete commands (by design: read-only)
- No cross-run trend database
- Static provider pricing remains non-authoritative (configurable estimates)
- Token values remain estimates based on character-to-token ratios
- No terminal color support (plain text only, by design)

## 11. Deferred Work

- **Phase E**: Transport abstraction — not implemented
- **Phase F**: Heterogeneous routing — not implemented
- Cross-run comparison / trend analysis — not implemented
- Benchmark cleanup commands — not implemented
- Live pricing integration — not implemented
- HTML/PDF export — not implemented

## 12. Live Validation

Tested against real benchmark run `10d3ecfb-ade3-4fd6-aa32-f6d0bcb9f7ab` (Phase 8 partial):

| Metric | Value |
|--------|-------|
| total_invocations | 9 |
| total_estimated_tokens | 108,655 |
| all invocations | TAPM |
| total wall clock | 3,213.703s |
| benchmark_stage | phase_c_provider_projection |
| providers evaluated | 11 |
| suitable providers | 11 |
| lowest projected cost | $0.030682 (GPT-4o Mini, Azure OpenAI) |
| quality warnings | 4 (phases_observed empty, nodes_observed empty, Phase 8 tokens zero, TAPM count mismatch) |

Report renders correctly with all quality warnings surfaced. No crashes on partial data.

## 13. Final Validation Checklist

- [x] `python -m runner.benchmark --run-id <run_id>` works
- [x] `--section summary` works
- [x] `--section tokens` works
- [x] `--section timing` works
- [x] `--section providers` works
- [x] `--section routing` works
- [x] `--section quality` works
- [x] `--json` works
- [x] `--list` works
- [x] Missing artifacts produce warnings, not crashes
- [x] Partial Phase 8 benchmark data is reportable
- [x] No files are modified by reporting commands
- [x] No provider API calls are made
- [x] No runtime routing added
- [x] No transport abstraction added
- [x] No prompt/response content is printed
- [x] Phase D tests pass (55/55)
- [x] All benchmark tests pass (259/259)
- [x] Full suite has zero new regressions (8 pre-existing failures only)
