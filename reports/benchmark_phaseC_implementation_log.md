# Benchmark Phase C Implementation Log — Provider Projection

**Date:** 2026-05-19
**Branch:** `benchmark_enginge`
**Phase:** C — Provider Projection (read-only, offline)

---

## 1. Files Created

| File | Purpose |
|------|---------|
| `runner/benchmark/provider_projection.py` | Core projection engine: load catalog, extract observed workload, compute cost/feasibility/migration/security per provider, build recommendations |
| `runner/benchmark/routing_analyzer.py` | Offline advisory workload classification: segment workload, produce routing recommendations |
| `.claude/benchmark/config/provider_catalog.json` | Static provider catalog with 7 providers, 12 models, no secrets |
| `tests/runner/benchmark/test_provider_projection.py` | 24 tests: catalog loading, cost projection, feasibility, migration, workload, recommendations, edge cases |
| `tests/runner/benchmark/test_routing_analyzer.py` | 12 tests: workload classification, routing recommendations, empty workload |
| `tests/runner/benchmark/test_phase_c_integration.py` | 17 tests: integration with real fixtures, failure isolation, backward compat, real catalog |

## 2. Files Modified

| File | Change |
|------|--------|
| `runner/benchmark/report_builder.py` | Added `run_benchmark_reports()` general entry point, `_run_phase_c_projection()`, `_expand_summary_with_phase_c()`. Phase B `run_phase_b_analytics()` preserved as backward-compatible wrapper. |
| `runner/dag_scheduler.py` | Changed scheduler benchmark finalization to call `run_benchmark_reports()` instead of `run_phase_b_analytics()`, passing `repo_root` for catalog resolution. Error message updated. |

## 3. Provider Projection Implemented

### Provider Catalog
- 7 providers: current_claude_code_max, anthropic_api, together_ai, fireworks_ai, aws_bedrock, azure_openai, local_openai_compatible
- 12 models across providers
- All pricing is static, labeled as configurable/not authoritative
- No API keys, secrets, tenant IDs, or organization IDs
- Catalog is versioned in `.claude/benchmark/config/`

### Observed Workload Extraction
- Reads `token_economics.json` and `phase_analytics.json` from Phase B
- Extracts: total tokens (input/output/total), max single invocation, TAPM/CLI/semantic predicate counts, phase 8 vs phases 1-7 breakdown, tool support requirement

### Cost Projection
- **per_token**: `tokens / 1M * cost_per_mtok` for input and output separately
- **subscription**: reports `estimated_monthly_cost_usd` from catalog
- **infrastructure**: reports $0 token cost with warning about external infra costs

### Feasibility Checks
- `context_window_sufficient`: max single invocation tokens vs model context window
- `oversized_invocations`: count of invocations exceeding context (conservative)
- `tool_support_sufficient`: TAPM workload requires tool support
- `system_prompt_supported`: all invocations use system prompts

### Migration Complexity
- `drop_in`: OpenAI-compatible + tools + context sufficient
- `adapter_needed`: non-OpenAI but supports required capabilities
- `significant_work`: API/tool loop/adapter/infrastructure needed
- `not_suitable`: cannot support required context/tools/modes
- Respects `migration_complexity_hint` from catalog entries

### Security Posture
- `private_networking_possible`, `data_residency_possible`, `zero_data_retention_possible`
- Qualitative fields with "possible" / "requires provider-specific contract" language
- Not a compliance certificate

### Recommendations
- `lowest_projected_cost`: cheapest suitable per-token provider
- `best_capability_match`: highest capability tier among suitable
- `best_openai_compatible_candidate`: best suitable OpenAI-compatible
- `best_private_network_candidate`: best suitable with private networking
- `not_suitable`: list of display names that cannot serve the workload
- `migration_warnings`: advisory warnings for significant_work / not_suitable

## 4. Routing Analyzer Implemented

- Advisory-only workload classification
- Segments: `phase_1_7_skill_work`, `phase_8_drafting_work`, `semantic_predicate_work`, `tapm_tool_augmented_work`, `cli_prompt_work`
- Each segment: estimated tokens, candidate tier, advisory notes
- No runtime routing, no scheduler modification, no transport changes
- Output included as `routing_recommendations` in `provider_projection.json`

## 5. Integration Summary

### Report Builder
- New `run_benchmark_reports()` function: runs Phase B, then Phase C
- Phase C is failure-isolated: if Phase C fails, Phase B artifacts are preserved
- Phase B `run_phase_b_analytics()` preserved as backward-compatible wrapper
- Summary expansion: Phase C adds `provider_projection_summary`, `phase_c_artifact_paths`, updates `benchmark_stage`

### Scheduler
- `dag_scheduler.py` now calls `run_benchmark_reports()` instead of `run_phase_b_analytics()`
- Passes `repo_root` for catalog resolution
- Single benchmark finalization call — no multiple scheduler-side pipelines

## 6. Fixture Validation

Using real Phase B fixture (run_id: `028d48e4-0d0d-48d9-8882-502a45bc9bf8`):

| Metric | Value |
|--------|-------|
| Total invocations | 4 |
| Total estimated input tokens | 40,402 |
| Total estimated output tokens | 22,170 |
| Total estimated tokens | 62,572 |
| TAPM count | 4 |
| CLI prompt count | 0 |
| Phases 1-7 tokens | 62,572 |
| Phase 8 tokens | 0 |
| Semantic predicate tokens | 0 |
| Generated artifact | `provider_projection.json` |

Internal consistency verified:
- `input + output == total` (40402 + 22170 == 62572)
- `TAPM total == total` (all invocations TAPM)
- `phases_1_7 == total`, `phase_8 == 0`

## 7. Behavioral Guarantees Verified

- [x] Phase A collection unchanged (no modifications to context.py, ledger.py, transport_hook.py, models.py, token_estimator.py)
- [x] Phase B analytics preserved (run_phase_b_analytics backward-compatible, all Phase B tests pass)
- [x] No transport abstraction added
- [x] No runtime provider API calls
- [x] No routing execution
- [x] No Tier 4 / Tier 5 writes (all artifacts under `.claude/benchmark/`)
- [x] No prompt/response content persisted in any artifact
- [x] Benchmark failures swallowed (Phase C failure does not break Phase B or orchestration)
- [x] Provider catalog contains no secrets

## 8. Tests Added

| Test File | Test Count | Categories |
|-----------|------------|------------|
| `test_provider_projection.py` | 24 | Catalog loading, per-token cost, subscription billing, infrastructure billing, context overflow, tool support, system prompt, migration complexity, observed workload, recommendations, edge cases, schema structure |
| `test_routing_analyzer.py` | 12 | TAPM classification, Phase 1-7 classification, Phase 8 classification, semantic predicate classification, CLI prompt classification, empty workload, advisory-only validation |
| `test_phase_c_integration.py` | 17 | Real fixture integration, Phase C stage, provider projection summary, Phase A/B preservation, observed workload, routing recommendations, no prompt content, catalog secrets, failure isolation (Phase C fail, Phase B fail), backward compat, real catalog structure, recommendations populated |

**Total new Phase C tests: 53**

## 9. Test Results

### Phase C tests
```
53 passed in 0.64s
```

### All benchmark tests
```
204 passed in 1.33s
```

### Full test suite
```
2765 passed, 7 failed, 2 skipped in 152.49s
```

### Pre-existing failures (not caused by Phase C)
All 7 failures are pre-existing drafting skill size/hygiene tests:
- `test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[excellence-section-drafting.md]`
- `test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[impact-section-drafting.md]`
- `test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[implementation-section-drafting.md]`
- `test_phase8_canonicalization.py::TestSpecLeanness::test_impact_no_component_keyword_scan`
- `test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[excellence-section-drafting.md]`
- `test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[impact-section-drafting.md]`
- `test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[implementation-section-drafting.md]`

**Zero new regressions from Phase C.**

## 10. Known Limitations

- Static catalog pricing is not authoritative — configurable estimates only
- No live provider pricing lookup
- No exact token billing (estimates based on character-to-token ratios)
- No provider API integration or connectivity testing
- No runtime routing — all recommendations are advisory
- No transport abstraction layer
- TAPM tool-read tokens remain estimated/limited by Phase A telemetry
- Max single invocation is taken from aggregate `largest_invocation_by_estimated_total_tokens` — per-invocation detail not available for exact oversized counting
- Security posture is qualitative ("possible"), not a compliance assessment

## 11. Deferred Work

- **Phase D**: CLI/reporting — not implemented
- **Phase E**: Transport abstraction — not implemented
- **Phase F**: Heterogeneous routing — not implemented
- Cross-run benchmarking — not implemented
- Benchmark cleanup commands — not implemented
- Live pricing integration — not implemented
- Provider API connectivity testing — not implemented
