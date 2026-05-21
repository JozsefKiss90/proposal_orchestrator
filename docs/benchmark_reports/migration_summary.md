# Migration Dossier Summary

**Phase A-D Benchmark Results and Phase E Readiness Assessment**

Generated from Phase D benchmark reports. Supports the decision to proceed from Phase A-D (Benchmarking / Observability) to Phase E (Transport Abstraction).

---

## 1. Executive Summary

The Proposal Orchestrator currently runs on **Claude Code Max** using `claude -p` as the runtime transport. This backend is convenient for development but is **not closed-network** and is **not data-leak-free** for sensitive proposal artifacts. Migration to an alternative backend is necessary for institutional deployment.

Phase A-D benchmarking has produced **8 phase-level reports** covering **41 model invocations** across the full orchestration pipeline (Phases 1-8). The benchmark dataset captures an estimated **837,278 tokens** and approximately **3.0 hours of wall-clock runtime**.

**Core conclusions:**

- Benchmark evidence is sufficient to proceed to **Phase E transport abstraction**.
- Claude CLI should remain the **reference backend** for output equivalence testing.
- An **OpenAI-compatible backend** should be the first migration target.
- **Together AI** (Llama 3.1 405B) is the preferred first external candidate for validation.
- **Azure OpenAI**, **AWS Bedrock**, and **local OpenAI-compatible backends** remain important deployment and security alternatives.

---

## 2. Benchmark Methodology

The benchmark pipeline operates in four phases:

- **Phase A** collected passive invocation telemetry during live orchestration runs. Each model call was instrumented to record timing, character counts, invocation type (TAPM, cli-prompt, semantic), and skill identity. No prompt or response text was captured.
- **Phase B** computed analytics from Phase A ledger data: token estimates (character-derived), timing profiles, and per-phase breakdowns.
- **Phase C** computed provider cost projections by applying static catalog pricing to estimated token volumes across a set of candidate providers and models.
- **Phase D** rendered structured JSON reports combining ledger, analytics, and projection data into per-run benchmark artifacts.

All benchmark artifacts are stored under `.claude/benchmark/<run_id>/`.

**Important caveats:**

- Token estimates are **character-derived** (chars / 4 heuristic) and are **not billing-grade**. They are suitable for relative comparison and order-of-magnitude planning.
- Provider prices are **static catalog estimates** and are **not procurement-grade**. They are useful for transport design and relative comparison, not for exact billing reconciliation.
- No prompt or response text is captured in benchmark artifacts.
- Reports are suitable for **migration planning**, not exact financial forecasting.

---

## 3. Coverage Summary

| Phase | Node | Invocations | Estimated Tokens | Wall-Clock | TAPM Tokens | CLI Tokens | Semantic Tokens | Data Quality Warnings |
|-------|------|------------:|-----------------:|-----------:|------------:|-----------:|----------------:|----------------------:|
| 1 | n01_call_analysis | 4 | 64,906 | 1,101s | 64,906 | 0 | 0 | 0 |
| 2 | n02_concept_refinement | 5 | 85,210 | 1,147s | 41,762 | 43,448 | 10,743 | 0 |
| 3 | n03_wp_design | 5 | 115,882 | 1,346s | 56,087 | 59,795 | 0 | 0 |
| 4 | n04_gantt_milestones | 4 | 86,043 | 542s | 19,201 | 66,842 | 0 | 0 |
| 5 | n05_impact_architecture | 4 | 44,117 | 1,266s | 44,117 | 0 | 0 | 0 |
| 6 | n06_implementation_architecture | 5 | 142,113 | 1,365s | 52,591 | 89,522 | 0 | 0 |
| 7 | n07_budget_gate | 5 | 190,352 | 773s | 26,858 | 163,494 | 0 | 0 |
| 8 | n08a-n08c partial | 9 | 108,655 | 3,214s | 108,655 | 0 | 0 | 4 |

**Aggregate totals:**

- **Total invocations:** 41
- **Total estimated tokens:** 837,278
- **Total wall-clock:** approximately 10,754 seconds / 2.99 hours
- **Total TAPM tokens:** 414,177
- **Total CLI tokens:** 423,101
- **Total semantic predicate tokens:** 10,743

Note: Phase 2 semantic predicate tokens overlap with the TAPM/CLI invocation-type totals and should not be added as a separate third mode to the total token count.

---

## 4. Workload Characterization

The workload is split almost evenly between TAPM and CLI-prompt token volume (414k TAPM vs 423k CLI-prompt). This near-parity has direct implications for transport design:

- **TAPM is essential.** Many core skills depend on Read/Glob-style tool access to resolve inputs from disk during invocation. A backend that does not support function/tool calling cannot run TAPM skills.
- **CLI-prompt invocations create the largest context pressure** in Phases 3, 4, 6, and 7, where structured validation and consistency-check skills serialize large payloads into the prompt.
- **Phase 8 is fully TAPM and generative.** All Phase 8 invocations use tool-augmented mode for drafting and review operations.
- **Phase 2 contains the only observed semantic predicate workload** in the benchmark set (10,743 tokens). Semantic predicates are used for gate evaluation and require reliable structured boolean/status output.
- **Deterministic gates** (rule-based, non-model) remain outside model-cost accounting entirely.

Phase 8 partial telemetry is useful because it captures drafting/review-style token and timing behavior, but it should be treated as a **lower-bound or partial signal**, not as a clean final benchmark. The 4 data quality warnings in Phase 8 reflect attribution or completeness issues in the telemetry.

---

## 5. Major Cost and Context Drivers

| Rank | Phase | Skill | Estimated Tokens | Invocation Type | Notes |
|-----:|------:|-------|------------------:|-----------------|-------|
| 1 | 7 | budget-interface-validation | 115,432 | cli-prompt | Largest aggregate skill cost; budget-gate validation dominates Phase 7 |
| 2 | 6 | milestone-consistency-check | 89,522 | cli-prompt | Largest single invocation observed |
| 3 | 3 | milestone-consistency-check | 59,795 | cli-prompt | Large prompt/context pressure |
| 4 | 8 | proposal-section-traceability-check | 48,410 | TAPM | Dominant Phase 8 review/audit cost |
| 5 | 7 | decision-log-update | 48,062 | cli-prompt | Large structured update payload |
| 6 | 4 | milestone-consistency-check | 39,686 | cli-prompt | Recurrent schedule consistency burden |
| 7 | 8 | constitutional-compliance-check | 38,277 | TAPM | Phase 8 compliance/review overhead |
| 8 | 2 | decision-log-update | 32,705 | cli-prompt | Largest Phase 2 single invocation |

The **largest single invocation by estimated tokens** is Phase 6 `milestone-consistency-check` at 89,522 tokens. This also represents the **largest prompt character pressure** observed across all benchmark runs. Any migration backend must have a context window safely above this threshold.

---

## 6. Runtime Performance Findings

| Phase | Wall-Clock | Slowest Skill |
|------:|-----------:|---------------|
| 1 | 1,101s | instrument-schema-normalization / call-requirements-extraction |
| 2 | 1,147s | concept-alignment-check |
| 3 | 1,346s | instrument-schema-normalization |
| 4 | 542s | gantt-schedule-builder |
| 5 | 1,266s | impact-pathway-core-builder |
| 6 | 1,365s | governance-model-builder |
| 7 | 773s | gate-enforcement |
| 8 | 3,214s | proposal-section-traceability-check |

Key observations:

- **Phase 8 partial run has the highest wall-clock time** at 3,214s, driven by multiple TAPM drafting and review invocations.
- **Phase 6 and Phase 3** are also substantial at approximately 1,365s and 1,346s respectively.
- **Idle/non-model time is negligible** across reports, meaning runtime is dominated by model calls.
- **TAPM calls can be slower** even when token count is moderate, because tool round-trips and reasoning time are bundled into Claude CLI wall-clock time.
- The current benchmark **cannot separate Claude CLI startup overhead from model reasoning time**. This distinction will become measurable once direct API backends are available.

---

## 7. Provider Projection Summary

| Provider / Model | Approx. Total Projected Token Cost | Role in Migration |
|------------------|------------------------------------:|-------------------|
| Azure OpenAI / GPT-4o Mini | ~$0.19 | Lowest projected cost; quality must be validated before broad use |
| Together AI / Llama 3.1 70B | ~$0.74 | Low-cost OpenAI-compatible open-model candidate |
| Fireworks AI / Llama 3.1 70B | ~$0.75 | Similar to Together 70B; useful alternative provider |
| Together AI / Llama 3.1 405B | ~$2.93 | Preferred high-capability OpenAI-compatible migration candidate |
| Azure OpenAI / GPT-4o | ~$3.17 | Strong enterprise/cloud candidate |
| AWS Bedrock / Llama 70B | ~$2.52 | Private-network / AWS-oriented open-model candidate |
| AWS Bedrock / Claude Sonnet | ~$4.23 | Strong Claude-compatible private-network candidate |
| Anthropic API / Claude Sonnet | ~$4.23 | Closest model behavior, but does not solve closed-network requirement alone |
| Local OpenAI-compatible / Llama 70B | token cost $0 | Requires GPU infrastructure; token cost excludes hardware and operations |

**Caveats:**

- These are **static catalog estimates**, not procurement-grade prices.
- They are useful for **relative comparison** and transport design decisions.
- Provider suitability should be **validated empirically** against orchestration gate pass/fail outcomes, not inferred from cost alone.
- Actual costs will vary based on negotiated pricing, token metering differences, and usage patterns.

---

## 8. Security and Deployment Implications

### A. Current Claude Code Max

- Convenient development baseline with subscription pricing.
- **Not closed-network.** Prompts and responses transit Anthropic infrastructure.
- **Not data-leak-free** for sensitive proposal artifacts (consortium data, budget details, IP).

### B. Normal Hosted API (Anthropic API)

- Easier to migrate (closest model behavior).
- Still external data transfer to Anthropic infrastructure.
- Requires provider contractual and data-retention review.

### C. Together AI / Fireworks AI

- OpenAI-compatible migration path with minimal adapter complexity.
- Useful for open-model validation and cost optimization.
- Private/dedicated deployment options may require enterprise contract negotiation.

### D. Azure OpenAI / AWS Bedrock

- Stronger institutional procurement and security fit.
- Private networking and data residency options available.
- Adapter complexity varies (Azure uses OpenAI-compatible interface; Bedrock uses proprietary SDK).
- Suitable for organizations with existing cloud provider relationships.

### E. Local OpenAI-compatible Backend

- Strongest data-control story: no external data transfer.
- Requires GPU infrastructure and operational support.
- Likely a later-stage option after transport abstraction is validated on hosted providers.

---

## 9. Backend Requirements Derived from Benchmarks

The Phase E transport abstraction must support backends meeting the following requirements:

- **System prompts**: backend must accept a system prompt parameter.
- **OpenAI-compatible chat/completions or responses-style interface** preferred as the primary integration target.
- **Function/tool calling** sufficient to reproduce TAPM Read/Glob semantics. The backend must support tool definitions, tool calls in assistant messages, and tool results in user messages.
- **Context windows** safely above the observed largest invocation:
  - Minimum: **>90k estimated tokens** (to accommodate the 89,522-token Phase 6 invocation).
  - Preferred: **128k+**.
  - Conservative target: **200k** where available.
- **Long request timeouts**, especially for TAPM and Phase 8 workloads where individual calls can exceed 500 seconds.
- **Structured JSON output robustness**: skills expect JSON responses conforming to artifact schemas.
- **Deterministic failure reporting**: the transport must distinguish between model errors, timeout errors, and malformed responses.
- **Exact token usage** where available (for post-migration benchmark accuracy).
- **No prompt/response logging** where contractually possible (for data sensitivity).
- **Provider-specific timeout and error normalization**: the abstraction layer must normalize provider-specific error codes and timeout behavior into a common failure taxonomy.

### Phase E Acceptance Criteria

Transport abstraction is complete only if:

- Claude CLI transport remains operational unchanged
- Existing orchestration outputs remain equivalent
- Gate outcomes remain unchanged
- TAPM semantics preserved
- Scheduler unchanged
- Agent runtime unchanged
- Benchmark instrumentation unchanged
- Provider-specific errors normalized
- Token accounting integrated where provider exposes usage
- Full benchmark suite remains regression-clean

---

## 10. Recommended Migration Strategy

1. **Preserve Claude CLI as the reference backend.** All output equivalence and gate pass/fail testing should compare against Claude CLI baselines.
2. **Implement Phase E transport abstraction** without changing orchestration semantics. The DAG scheduler, gate evaluator, agent runtime, and skill runtime contracts remain unchanged.
3. **Add a local `ClaudeCLIBackend` wrapper first** to validate the abstraction layer against the current transport with zero behavioral change.
4. **Add an OpenAI-compatible backend second** as the primary migration target.
5. **Use Together AI as the first external OpenAI-compatible validation backend** (Llama 3.1 405B for capability, 70B for cost-sensitive testing).
6. **Validate phase-by-phase output equivalence** against the Claude baseline, starting from Phase 1 and progressing sequentially.
7. **Validate low-risk structured workloads** (call analysis, consistency checks) before attempting Phase 8 drafting on alternative backends.
8. **Evaluate Azure/AWS private-network options** for institutional deployment scenarios.
9. **Defer heterogeneous runtime routing** until after backend equivalence tests confirm which workloads are safe to route to alternative providers.
10. **Retain benchmark reporting as the acceptance harness** for migration. Phase A-D instrumentation should run against each new backend to produce comparable telemetry.

---

## 11. Migration Risks and Caveats

- **Token estimates are approximate.** Character-derived estimates (chars / 4) are not equivalent to provider tokenizer counts. Actual billing may differ.
- **Provider prices are static and non-authoritative.** Catalog prices change, volume discounts apply, and negotiated rates differ from list prices.
- **Phase 8 is partial and has attribution warnings.** The 4 data quality warnings indicate incomplete or uncertain telemetry attribution. Phase 8 totals should be treated as lower bounds.
- **Phase 8 may be understated** if manual artifact substitution during the benchmark run bypassed generative work that would normally occur.
- **Tool-use semantics differ across providers.** OpenAI, Anthropic, and open-model tool calling have different schema conventions, parallel tool call behavior, and error handling.
- **OpenAI-compatible does not automatically mean equivalent tool behavior.** TAPM skills rely on specific Read/Glob tool round-trip patterns that must be validated per provider.
- **Smaller/cheaper models must be quality-tested** against gate pass/fail outcomes. A model that is 10x cheaper but fails gates is not a valid migration target.
- **Semantic predicate reliability must be evaluated separately.** Semantic predicates require consistent boolean/status output; model variability here can cause false gate failures.
- **Cost alone must not determine provider choice.** Security, data residency, context window, tool-use fidelity, and output quality are all decision factors.

---

## 12. Decision and Next Step

The benchmark evidence is **sufficient to proceed to Phase E**.

Phase E should focus **only on transport abstraction**: defining a provider-agnostic backend interface, wrapping the existing Claude CLI transport, and adding an OpenAI-compatible backend implementation. No heterogeneous routing, model selection logic, or cost optimization should be implemented in Phase E.

**Key decisions:**

- **Claude CLI remains the reference backend** for output equivalence and regression testing.
- **First candidate external backend:** Together AI via OpenAI-compatible API (Llama 3.1 405B for full-capability validation).
- **Security candidates:** Azure OpenAI, AWS Bedrock, and local OpenAI-compatible deployment, to be evaluated for institutional requirements.
- **A clean full Phase 8 rerun** remains desirable for complete telemetry but is **not a blocker** for Phase E implementation.

Phase E does not require resolving provider selection, pricing negotiation, or deployment topology. It requires only that the transport layer become pluggable so that these decisions can be validated empirically in subsequent phases.

---

*This summary was produced from Phase D benchmark reports. It does not implement Phase E. No runtime code, benchmark engine code, provider catalog values, or benchmark artifacts were modified in its production.*
