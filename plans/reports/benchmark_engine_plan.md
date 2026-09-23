# Benchmarking Subsystem / LLM Orchestration Observability Layer

## Implementation and Migration Plan

**Status:** Draft
**Branch:** `benchmark_engine`
**Constitutional authority:** Subordinate to CLAUDE.md. This subsystem does not modify gate logic, artifact schemas, phase semantics, tier authority, or the scheduler dispatch contract.

---

## Table of Contents

1. [Proposed Subsystem Architecture](#1-proposed-subsystem-architecture)
2. [Runtime Integration Points](#2-runtime-integration-points)
3. [Data Model Design](#3-data-model-design)
4. [Artifact Schema Strategy](#4-artifact-schema-strategy)
5. [Benchmark Artifact Locations](#5-benchmark-artifact-locations)
6. [Telemetry Lifecycle](#6-telemetry-lifecycle)
7. [Token Estimation Strategy](#7-token-estimation-strategy)
8. [Runtime Timing Strategy](#8-runtime-timing-strategy)
9. [Failure Isolation Strategy](#9-failure-isolation-strategy)
10. [Provider Projection Strategy](#10-provider-projection-strategy)
11. [OpenAI-Compatible Migration Strategy](#11-openai-compatible-migration-strategy)
12. [Future Heterogeneous Routing Architecture](#12-future-heterogeneous-routing-architecture)
13. [Security and Privacy Implications](#13-security-and-privacy-implications)
14. [Runtime Overhead Analysis](#14-runtime-overhead-analysis)
15. [Incremental Implementation Phases](#15-incremental-implementation-phases)
16. [Required Code Modifications by File](#16-required-code-modifications-by-file)
17. [Required New Modules and Files](#17-required-new-modules-and-files)
18. [Testing Strategy](#18-testing-strategy)
19. [Migration Risk Analysis](#19-migration-risk-analysis)
20. [Recommended Implementation Order](#20-recommended-implementation-order)

---

## 1. Proposed Subsystem Architecture

### 1.1 Design Principles

The benchmarking subsystem operates as a **passive observability sidecar** within the existing three-layer execution stack. It observes invocations without participating in orchestration decisions:

```
                    ┌──────────────────────────────────────────────────┐
                    │              DAGScheduler.run()                   │
                    │  ┌──────────────────────────────────────────┐    │
                    │  │         BenchmarkRunCollector             │    │
                    │  │  (run-scoped, created at run() entry)    │    │
                    │  └──────────────────────────────────────────┘    │
                    │         │ observes                                │
                    │  ┌──────▼──────────────────────────────────────┐ │
                    │  │     _dispatch_node(node_id)                 │ │
                    │  │  ┌──────────────────────────────────────┐   │ │
                    │  │  │     run_agent()                      │   │ │
                    │  │  │  ┌──────────────────────────────┐    │   │ │
                    │  │  │  │     run_skill()               │    │   │ │
                    │  │  │  │  ┌──────────────────────┐     │    │   │ │
                    │  │  │  │  │  invoke_claude_text() │     │    │   │ │
                    │  │  │  │  │  ┌────────────────┐   │     │    │   │ │
                    │  │  │  │  │  │ InstrumentedXport│  │     │    │   │ │
                    │  │  │  │  │  │  → BenchRecord  │  │     │    │   │ │
                    │  │  │  │  │  └────────────────┘   │     │    │   │ │
                    │  │  │  │  └──────────────────────┘     │    │   │ │
                    │  │  │  └──────────────────────────────┘    │   │ │
                    │  │  └──────────────────────────────────────┘   │ │
                    │  └────────────────────────────────────────────┘ │
                    │         │ collects                                │
                    │  ┌──────▼──────────────────────────────────────┐ │
                    │  │     BenchmarkLedger                          │ │
                    │  │  (append-only invocation log)               │ │
                    │  └──────────────────────────────────────────────┘ │
                    │         │ writes at run completion                │
                    │  ┌──────▼──────────────────────────────────────┐ │
                    │  │  .claude/benchmark/<run_id>/                 │ │
                    │  │  ├── invocation_ledger.jsonl                 │ │
                    │  │  ├── run_benchmark_summary.json              │ │
                    │  │  ├── phase_analytics.json                    │ │
                    │  │  ├── token_economics.json                    │ │
                    │  │  └── provider_projection.json                │ │
                    │  └──────────────────────────────────────────────┘ │
                    └──────────────────────────────────────────────────┘
```

### 1.2 Architectural Layers

The subsystem consists of five logical layers, each with a single responsibility:

| Layer | Module | Responsibility | Depends on |
|-------|--------|---------------|------------|
| **L1: Transport Instrumentation** | `runner/benchmark/transport_hook.py` | Wraps `invoke_claude_text()` to capture per-invocation telemetry without modifying the transport function's signature or return value | `runner/claude_transport.py` |
| **L2: Invocation Ledger** | `runner/benchmark/ledger.py` | Append-only, thread-safe collection of `BenchmarkInvocationRecord` instances during a run | None (pure data) |
| **L3: Token Estimation** | `runner/benchmark/token_estimator.py` | Estimates input/output token counts from character-level measurements using model-specific ratios | None (pure computation) |
| **L4: Analytics Engine** | `runner/benchmark/analytics.py` | Computes phase-level, node-level, and skill-level aggregate statistics from the ledger | L2, L3 |
| **L5: Provider Projection** | `runner/benchmark/provider_projection.py` | Projects observed invocation patterns onto alternative provider cost/latency models | L2, L3, L4 |

### 1.3 Relationship to Existing Architecture

```
CLAUDE.md §17 Execution Stack (unchanged)
──────────────────────────────────────────

  DAGScheduler ──→ run_agent() ──→ run_skill() ──→ invoke_claude_text()
       │                │               │                    │
       │                │               │                    ▼
       │                │               │           claude_transport.py
       │                │               │           (UNCHANGED — sole
       │                │               │            transport boundary)
       │                │               │
  Benchmark             │               │
  integration:          │               │
       │                │               │
  BenchmarkRunCollector BenchmarkRunCollector     InstrumentedTransport
  (node-level timing)   (agent-level     (invocation-level telemetry:
                         aggregation)     prompt sizes, wall-clock time,
                                          model, mode, tools, timeout)
```

**Key invariant:** `invoke_claude_text()` is NOT modified. The instrumentation layer wraps it at the call site, not at the definition site. This preserves the transport's constitutional role as a transport-only module with no knowledge of upstream semantics.

### 1.4 Constitutional Compliance

| CLAUDE.md Section | Compliance Mechanism |
|---|---|
| §17.1 (call-graph constraints) | Benchmark modules never call scheduler, agent runtime, or gate evaluator. They only observe. |
| §17.2 (node execution model) | No node states are introduced. No gate conditions are modified. |
| §17.3 (failure semantics) | Benchmark failures produce log warnings, never `SkillResult` failures or `AgentResult` failures. |
| §17.5 (transport principle) | `claude_transport.py` is unchanged. Instrumentation wraps at call sites. |
| §17.6 (runtime prohibitions) | Benchmark modules never write gate results, invoke skills, or evaluate gates. |
| §8 (budget integration) | Benchmark modules never generate, estimate, or substitute budget figures. |
| §9 (state and memory) | Benchmark artifacts are runtime execution memory (`.claude/`), not constitutional source truth (`docs/`). |

---

## 2. Runtime Integration Points

### 2.1 Integration Point Map

There are exactly **three call sites** for `invoke_claude_text()` in the runtime:

| Call Site | File | Line Context | Invocation Type | Mode |
|-----------|------|-------------|-----------------|------|
| **CS1** | `runner/skill_runtime.py` | TAPM path (`invoke_claude_text(..., tools=["Read", "Glob"], timeout_seconds=TAPM_TIMEOUT_SECONDS)`) | Skill execution | TAPM |
| **CS2** | `runner/skill_runtime.py` | cli-prompt path (`invoke_claude_text(...)`) | Skill execution | cli-prompt |
| **CS3** | `runner/semantic_dispatch.py` | `invoke_agent()` (`invoke_claude_text(...)`) | Semantic predicate evaluation | cli-prompt (agent) |

Each call site receives a thin instrumentation wrapper that captures telemetry before and after the call. The wrapper:
- Records wall-clock start time (`time.monotonic()`)
- Measures `len(system_prompt)` and `len(user_prompt)` in characters
- Records model, timeout, tools configuration
- Calls the original `invoke_claude_text()`
- Records wall-clock end time
- Measures `len(response_text)` in characters
- Emits a `BenchmarkInvocationRecord` to the run-scoped ledger
- Returns the original response text (or re-raises the original exception)

### 2.2 Scheduler-Level Integration

The `DAGScheduler` is the only module that creates and finalizes the benchmark collector:

| Event | Integration Point | Action |
|-------|------------------|--------|
| `run()` entry | After `started_at` timestamp | Create `BenchmarkRunCollector(run_id)` |
| `_dispatch_node()` entry | After `set_node_state("running")` | Record `node_dispatch_start(node_id)` |
| `_dispatch_node()` exit | Before `return NodeExecutionResult` | Record `node_dispatch_end(node_id, result)` |
| `run()` exit | Before `summary.write()` | Finalize and write benchmark artifacts |

### 2.3 Agent Runtime Integration

The `run_agent()` function provides skill-level sequencing telemetry:

| Event | Integration Point | Action |
|-------|------------------|--------|
| Skill invocation start | Before `run_skill()` call | Record `skill_invocation_start(skill_id, node_id)` |
| Skill invocation end | After `run_skill()` returns | Record `skill_invocation_end(skill_id, result)` |
| Skill skip (reuse) | At `"reuse_skipped"` branch | Record `skill_skipped(skill_id, "reuse")` |
| Skill skip (not_applicable) | At `"not_applicable"` branch | Record `skill_skipped(skill_id, "not_applicable")` |

### 2.4 Gate Evaluator Integration

Gate evaluation telemetry captures the split between deterministic and semantic work:

| Event | Integration Point | Action |
|-------|------------------|--------|
| Deterministic predicate batch | After all deterministic predicates evaluated | Record `deterministic_predicates_evaluated(gate_id, count, elapsed)` |
| Semantic predicate dispatch | Per `dispatch_semantic_predicate()` call | Already captured by CS3 transport hook |
| Gate result write | After `result_path.write_text()` | Record `gate_evaluated(gate_id, status, elapsed)` |

### 2.5 Integration Injection Mechanism

The benchmark collector is injected via a **module-level context variable**, not constructor parameters. This avoids modifying function signatures across the stack:

```python
# runner/benchmark/context.py
from __future__ import annotations
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runner.benchmark.ledger import BenchmarkLedger

# Set by DAGScheduler.run() at run start; cleared at run end.
# When None, all benchmark recording is silently skipped (zero overhead).
_active_ledger: ContextVar[BenchmarkLedger | None] = ContextVar(
    "_active_ledger", default=None
)

def get_ledger() -> BenchmarkLedger | None:
    """Return the active benchmark ledger, or None if benchmarking is disabled."""
    return _active_ledger.get()

def set_ledger(ledger: BenchmarkLedger | None) -> None:
    """Set the active benchmark ledger for the current execution context."""
    _active_ledger.set(ledger)
```

This uses Python's `contextvars` for safe scoping. When `get_ledger()` returns `None`, all recording calls are no-ops — zero allocation, zero I/O.

---

## 3. Data Model Design

### 3.1 BenchmarkInvocationRecord

The atomic unit of telemetry. One record per `invoke_claude_text()` call.

```python
@dataclass(frozen=True)
class BenchmarkInvocationRecord:
    """Immutable record of a single Claude invocation."""

    # ── Identity ──
    invocation_id: str           # UUID4, unique per invocation
    run_id: str                  # DAG run UUID
    node_id: str | None          # Manifest node ID (None for standalone calls)
    skill_id: str | None         # Skill ID (None for semantic predicates)
    predicate_id: str | None     # Semantic predicate ID (None for skills)

    # ── Classification ──
    invocation_type: str         # "skill_tapm" | "skill_cli_prompt" | "semantic_predicate"
    execution_mode: str          # "tapm" | "cli-prompt"

    # ── Model Configuration ──
    model: str                   # e.g. "claude-sonnet-4-6"
    max_tokens_requested: int    # Value passed to invoke_claude_text()
    timeout_seconds: int         # Configured timeout
    tools_enabled: list[str]     # e.g. ["Read", "Glob"] or []

    # ── Prompt Metrics ──
    system_prompt_chars: int     # len(system_prompt)
    user_prompt_chars: int       # len(user_prompt)
    effective_prompt_chars: int  # len(effective_user_prompt) after embedding
    system_prompt_via_flag: bool # True if --system-prompt flag was used

    # ── Response Metrics ──
    response_chars: int | None   # len(response_text), None on failure
    response_status: str         # "success" | "timeout" | "error" | "empty"

    # ── Timing ──
    wall_clock_start: float      # time.monotonic() before subprocess.run()
    wall_clock_end: float        # time.monotonic() after subprocess.run()
    wall_clock_seconds: float    # end - start
    timestamp_utc: str           # ISO-8601 UTC timestamp for correlation

    # ── Token Estimates ──
    estimated_input_tokens: int  # Estimated from prompt chars
    estimated_output_tokens: int # Estimated from response chars

    # ── Transport Metadata ──
    cli_command_args: list[str]  # ["claude", "-p", "--model", ...] (no prompt content)
    subprocess_returncode: int | None  # None on timeout/exception
    had_stderr: bool             # True if stderr was non-empty

    # ── Error Context ──
    error_class: str | None      # Exception class name, None on success
    error_message: str | None    # Exception message (truncated), None on success

    # ── Derived Fields ──
    prompt_total_chars: int      # system_prompt_chars + user_prompt_chars
    chars_per_second: float | None  # response_chars / wall_clock_seconds
```

### 3.2 NodeBenchmarkRecord

Aggregated per-node statistics, derived from invocation records:

```python
@dataclass(frozen=True)
class NodeBenchmarkRecord:
    """Aggregated benchmark data for a single node dispatch."""

    node_id: str
    phase_number: int | None

    # ── Timing ──
    dispatch_wall_clock_seconds: float  # Total _dispatch_node() time
    entry_gate_seconds: float | None    # Entry gate evaluation time
    agent_body_seconds: float           # run_agent() time
    exit_gate_seconds: float | None     # Exit gate evaluation time

    # ── Invocation Counts ──
    total_invocations: int              # All invoke_claude_text() calls
    skill_invocations: int              # Skill-only invocations
    semantic_invocations: int           # Semantic predicate invocations
    deterministic_predicates_count: int # Deterministic (zero-LLM) predicates

    # ── Token Aggregates ──
    total_estimated_input_tokens: int
    total_estimated_output_tokens: int
    total_estimated_tokens: int

    # ── Prompt Size Aggregates ──
    total_prompt_chars: int
    max_prompt_chars: int               # Largest single invocation
    mean_prompt_chars: float

    # ── Failure Counts ──
    failed_invocations: int
    timeout_invocations: int

    # ── Reuse ──
    reuse_decision: str | None          # "reused" | "not_reused" | None
    skills_skipped_by_reuse: list[str]

    # ── Mode Split ──
    tapm_invocations: int
    cli_prompt_invocations: int
```

### 3.3 PhaseBenchmarkRecord

Phase-level aggregation:

```python
@dataclass(frozen=True)
class PhaseBenchmarkRecord:
    """Aggregated benchmark data for a complete phase."""

    phase_number: int
    phase_id: str                       # e.g. "phase1_call_analysis"

    # ── Timing ──
    total_wall_clock_seconds: float
    queue_idle_seconds: float           # Time between node dispatches

    # ── Aggregates ──
    nodes_dispatched: int
    total_invocations: int
    total_estimated_input_tokens: int
    total_estimated_output_tokens: int
    total_estimated_tokens: int
    total_prompt_chars: int

    # ── Breakdown ──
    skill_invocations: int
    semantic_invocations: int
    deterministic_predicates_total: int
    deterministic_vs_model_ratio: float # det_predicates / (det + semantic)

    # ── Failure ──
    failed_invocations: int
    timeout_invocations: int

    # ── Reuse ──
    nodes_reused: int
    tokens_saved_by_reuse: int          # Estimated tokens not spent due to reuse
```

### 3.4 RunBenchmarkSummary

Top-level summary for the entire run:

```python
@dataclass
class RunBenchmarkSummary:
    """Complete benchmark summary for a DAG run."""

    run_id: str
    benchmark_version: str              # Schema version for forward compat

    # ── Run Metadata ──
    started_at: str
    completed_at: str
    overall_status: str                 # From RunSummary
    phase_scope: int | None

    # ── Execution Footprint ──
    phases_executed: list[int]
    nodes_dispatched: int
    agents_invoked: int                 # Unique agent_ids
    skills_invoked: int                 # Total skill invocations (inc. failures)
    unique_skills_invoked: int          # Distinct skill_ids
    semantic_predicates_invoked: int
    deterministic_predicates_evaluated: int
    total_invocations: int              # Total invoke_claude_text() calls

    # ── Deterministic vs Model Split ──
    deterministic_work_fraction: float  # det_predicates / total_predicates
    model_mediated_work_fraction: float # 1 - deterministic_work_fraction

    # ── Token Economics ──
    total_estimated_input_tokens: int
    total_estimated_output_tokens: int
    total_estimated_tokens: int
    phase8_estimated_tokens: int        # Phase 8 drafting cost isolated
    phases_1_7_estimated_tokens: int    # Pre-drafting cost isolated
    semantic_predicate_tokens: int      # Semantic gate evaluation cost
    largest_single_invocation_tokens: int
    largest_single_invocation_skill: str

    # ── Runtime Performance ──
    total_wall_clock_seconds: float
    total_model_seconds: float          # Sum of all invocation wall-clock times
    total_idle_seconds: float           # total_wall - total_model
    mean_invocation_seconds: float
    p50_invocation_seconds: float
    p95_invocation_seconds: float
    p99_invocation_seconds: float
    timeout_count: int
    retry_count: int                    # (placeholder — no retry in current arch)

    # ── Prompt Economics ──
    total_prompt_chars: int
    total_response_chars: int
    tapm_invocation_count: int
    cli_prompt_invocation_count: int
    tapm_mean_prompt_chars: float
    cli_prompt_mean_prompt_chars: float
    prompt_reduction_ratio: float       # tapm_mean / cli_prompt_mean

    # ── Reuse Effectiveness ──
    nodes_reused: int
    nodes_not_reused: int
    estimated_tokens_saved_by_reuse: int
    reuse_savings_percentage: float

    # ── Phase Breakdown ──
    phase_records: list[dict]           # Serialized PhaseBenchmarkRecords

    # ── Node Breakdown ──
    node_records: list[dict]            # Serialized NodeBenchmarkRecords

    # ── Provider Projections (populated by L5) ──
    provider_projections: dict | None   # Populated when projection engine runs
```

---

## 4. Artifact Schema Strategy

### 4.1 Schema Versioning

All benchmark artifacts carry a `benchmark_schema_version` field for forward compatibility:

```json
{
  "benchmark_schema_version": "1.0.0",
  "run_id": "...",
  ...
}
```

Version semantics:
- **Patch** (1.0.x): New optional fields added. Old consumers ignore them.
- **Minor** (1.x.0): New required fields added. Old consumers must be updated.
- **Major** (x.0.0): Breaking schema change. Requires migration.

### 4.2 Schema Relationship to Tier 4/5

Benchmark artifacts are **NOT** Tier 4 orchestration state. They are **runtime execution memory** per CLAUDE.md §9.2:

> `.claude/agent-memory/`, `.claude/cache/`, `.claude/logs/`, and `.claude/runs/` contain runtime execution state. These directories support operational continuity but are not constitutional source truth.

Benchmark artifacts live in `.claude/benchmark/` — a new runtime execution memory directory at the same constitutional level as `.claude/runs/`, `.claude/logs/`, `.claude/skill_diag/`, and `.claude/semantic_diag/`.

### 4.3 Schema Independence

Benchmark schemas are **independent** from artifact_schema_specification.yaml. They are not registered in the schema registry, not validated by gate predicates, and not produced by skills. They are produced by the benchmark analytics engine, a pure-Python post-processing layer.

---

## 5. Benchmark Artifact Locations

```
.claude/
├── benchmark/                          # NEW — benchmark root
│   ├── <run_id>/                       # Per-run benchmark artifacts
│   │   ├── invocation_ledger.jsonl     # Append-only invocation log (JSONL)
│   │   ├── run_benchmark_summary.json  # Top-level summary
│   │   ├── phase_analytics.json        # Phase-level breakdown
│   │   ├── token_economics.json        # Token estimation details
│   │   ├── timing_profile.json         # Latency distribution
│   │   └── provider_projection.json    # Provider cost/latency projections
│   ├── cross_run/                      # Cross-run comparison artifacts
│   │   ├── run_index.json              # Index of all benchmarked runs
│   │   └── trend_data.json             # Historical trend data
│   └── config/                         # Benchmark configuration
│       ├── provider_catalog.json       # Provider pricing/capability data
│       └── token_ratios.json           # Model-specific char-to-token ratios
├── runs/                               # Existing — run state (unchanged)
├── skill_diag/                         # Existing — skill diagnostics (unchanged)
├── semantic_diag/                      # Existing — semantic diagnostics (unchanged)
└── ...
```

### 5.1 File Format Choices

| Artifact | Format | Rationale |
|----------|--------|-----------|
| `invocation_ledger.jsonl` | JSON Lines | Append-only, streamable, one record per line. Survives partial writes (crash during run). Each line is independently parseable. |
| `run_benchmark_summary.json` | JSON | Single structured document. Written once at run completion. |
| `phase_analytics.json` | JSON | Derived from ledger. Written once at run completion. |
| `token_economics.json` | JSON | Derived from ledger. Written once at run completion. |
| `timing_profile.json` | JSON | Derived from ledger. Written once at run completion. |
| `provider_projection.json` | JSON | Derived from analytics. Written once at run completion. |

### 5.2 Append-Only Guarantee

The invocation ledger is the single mutable artifact during a run. It is append-only:
- Each `BenchmarkInvocationRecord` is serialized as a single JSON line and appended
- No lines are ever modified or deleted during a run
- File handle is opened once at run start and flushed after each append
- On crash, all previously flushed records are recoverable
- Post-run artifacts are derived from the ledger and written atomically

---

## 6. Telemetry Lifecycle

### 6.1 Lifecycle Phases

```
Phase 1: INITIALIZE
    DAGScheduler.run() creates BenchmarkRunCollector
    Opens invocation_ledger.jsonl file handle
    Records run metadata (run_id, started_at, phase_scope)

Phase 2: COLLECT (during dispatch loop)
    Per invoke_claude_text() call:
        InstrumentedTransport wrapper records BenchmarkInvocationRecord
        Record appended to ledger (JSONL line)
        Record accumulated in in-memory list for analytics

    Per _dispatch_node() call:
        Node timing recorded (start/end monotonic timestamps)
        Gate evaluation timing recorded
        Agent body timing recorded

Phase 3: ANALYZE (after dispatch loop, before RunSummary.write())
    Analytics engine processes in-memory invocation records
    Computes phase/node/skill aggregates
    Computes token economics
    Computes timing distributions

Phase 4: PROJECT (after analysis)
    Provider projection engine maps observed patterns
    Estimates alternative provider costs
    Generates routing recommendations

Phase 5: PERSIST (after projection)
    Writes all derived artifacts atomically to .claude/benchmark/<run_id>/
    Updates cross-run index
    Closes ledger file handle
    Clears context variable

Phase 6: REPORT (optional, on-demand)
    CLI command: python -m runner.benchmark --run-id <id>
    Reads persisted artifacts and renders human-readable report
```

### 6.2 Telemetry Collection Guarantees

1. **Non-blocking:** All telemetry writes use best-effort semantics. A write failure is logged and silently swallowed. No orchestration outcome is ever affected by a telemetry failure.

2. **Append-only:** The ledger file is only appended to, never read during collection. This eliminates read-write races.

3. **Monotonic timing:** All wall-clock measurements use `time.monotonic()`, which is immune to system clock adjustments.

4. **Character-level measurement:** Prompt and response sizes are measured in characters (Python `len()`), not bytes or tokens. Token estimates are derived post-hoc.

5. **No prompt content capture:** The ledger records prompt **sizes** and **metadata**, never prompt **content**. Prompt content may contain project-specific data (Tier 3) that must not leak into benchmark artifacts.

---

## 7. Token Estimation Strategy

### 7.1 Problem Statement

The current transport (`claude -p`) does not expose token usage metadata. The Claude CLI does not return `usage.input_tokens` or `usage.output_tokens` in its stdout. Therefore, token counts must be **estimated** from character-level measurements.

### 7.2 Estimation Method

Character-to-token ratios are model-specific and empirically calibrated:

```python
# runner/benchmark/token_estimator.py

# Empirical char-to-token ratios for common models.
# These are conservative estimates (slightly over-counting tokens).
# Source: empirical measurement against Claude tokenizer.
# English text: ~4 chars/token. JSON/code: ~3.2 chars/token.
# We use a blended ratio for mixed content (skill prompts contain
# both natural language and embedded JSON).

CHAR_TO_TOKEN_RATIOS: dict[str, float] = {
    # Claude models
    "claude-sonnet-4-6": 3.5,
    "claude-opus-4-6": 3.5,
    "claude-haiku-4-5": 3.5,

    # OpenAI-compatible models (for projection)
    "gpt-4o": 3.8,
    "gpt-4o-mini": 3.8,
    "gpt-4-turbo": 3.7,

    # Open-weight models (for projection)
    "llama-3.1-70b": 3.6,
    "llama-3.1-405b": 3.6,
    "mixtral-8x22b": 3.4,
    "qwen-2.5-72b": 3.3,
    "deepseek-v3": 3.4,

    # Default fallback
    "_default": 3.5,
}


def estimate_tokens(char_count: int, model: str) -> int:
    """Estimate token count from character count and model."""
    ratio = CHAR_TO_TOKEN_RATIOS.get(model, CHAR_TO_TOKEN_RATIOS["_default"])
    return max(1, int(char_count / ratio))
```

### 7.3 Estimation Accuracy

Expected accuracy: **±15-25%** for blended content. This is sufficient for:
- **Cost comparison:** Relative cost ranking between providers is preserved even with ±25% error.
- **Trend analysis:** Run-over-run token growth is detectable at ±25% because the systematic bias is constant.
- **Budget planning:** Conservative over-counting means cost estimates are upper bounds.

This is NOT sufficient for:
- **Exact billing reconciliation** — requires actual token counts from the provider API.
- **Token budget enforcement** — requires transport-level token counting.

### 7.4 Future Token Count Sources

When the transport is migrated to a provider API (see §11), exact token counts will be available from the response metadata. The estimation layer will then switch to a **prefer-actual, fallback-estimated** mode:

```python
def get_tokens(
    actual_input: int | None,
    actual_output: int | None,
    prompt_chars: int,
    response_chars: int,
    model: str,
) -> tuple[int, int, str]:
    """Return (input_tokens, output_tokens, source)."""
    if actual_input is not None and actual_output is not None:
        return actual_input, actual_output, "actual"
    return (
        estimate_tokens(prompt_chars, model),
        estimate_tokens(response_chars, model),
        "estimated",
    )
```

### 7.5 TAPM Token Estimation Complexity

TAPM invocations present a unique estimation challenge. The initial prompt is small (~5-30KB), but Claude performs multiple Read/Glob tool calls during execution, each of which adds to the total input tokens consumed. The `claude -p --tools "Read,Glob"` transport does not report the total tokens consumed including tool-call round-trips.

**Strategy for TAPM:**

1. **Prompt tokens:** Estimate from `system_prompt_chars + user_prompt_chars` (the initial prompt).
2. **Tool-read tokens:** Estimate from the skill's `reads_from` paths by computing `sum(file_size for file in reads_from)` as an upper bound on tool-read content. This is a **ceiling estimate** — Claude may not read all declared inputs.
3. **Output tokens:** Estimate from `response_chars`.
4. **Label:** Mark TAPM estimates with `token_source: "estimated_tapm_ceiling"` to distinguish from cli-prompt estimates.

```python
def estimate_tapm_total_input_tokens(
    prompt_chars: int,
    reads_from_total_chars: int,
    model: str,
) -> int:
    """Upper-bound estimate for TAPM input tokens.

    Includes prompt tokens + ceiling estimate for tool-read content.
    """
    return estimate_tokens(prompt_chars + reads_from_total_chars, model)
```

---

## 8. Runtime Timing Strategy

### 8.1 Timing Layers

The system already has timing instrumentation at the skill level (`_skill_t0 = time.monotonic()` in `run_skill()`). The benchmark subsystem extends this with consistent timing across all layers:

| Layer | What is timed | Existing? | Benchmark addition |
|-------|--------------|-----------|-------------------|
| Transport | `subprocess.run()` wall clock | Partial (timeout tracking) | Full start/end monotonic timestamps in `BenchmarkInvocationRecord` |
| Skill | `run_skill()` wall clock | Yes (`_skill_t0`) | Captured as `skill_wall_clock_seconds` |
| Agent | `run_agent()` wall clock | No | Add `_agent_t0 = time.monotonic()` at entry |
| Node | `_dispatch_node()` wall clock | No | Add `_node_t0 = time.monotonic()` at entry |
| Gate | `evaluate_gate()` wall clock | No | Measure around each `evaluate_gate()` call in `_dispatch_node()` |
| Phase | Sum of node dispatch times + idle | No | Derived from node timing records |
| Run | `run()` wall clock | Yes (`started_at` / `completed_at` as ISO timestamps) | Convert to monotonic delta |

### 8.2 Timing Decomposition

For each node dispatch, the total wall clock decomposes as:

```
_dispatch_node() total
├── Entry gate time (evaluate_gate() for entry gate)
├── Agent body time (run_agent())
│   ├── Spec loading time (negligible, not timed)
│   ├── Input resolution time (disk I/O, not timed individually)
│   ├── Skill 1 time
│   │   ├── Prompt assembly time
│   │   ├── Claude invocation time (invoke_claude_text())
│   │   │   ├── Subprocess overhead (startup, piping)
│   │   │   └── Model reasoning time (indistinguishable from subprocess)
│   │   ├── Response parsing time
│   │   └── Atomic write time
│   ├── Skill 2 time
│   │   └── ... (same decomposition)
│   └── Gate-readiness check time
├── Exit gate time (evaluate_gate() for exit gate)
│   ├── Deterministic predicate time (sum)
│   └── Semantic predicate time (sum of invoke_claude_text() calls)
└── RunContext save time (negligible)
```

### 8.3 Claude CLI Overhead vs. Model Reasoning

The current transport bundles CLI startup, prompt piping, model reasoning, and response collection into a single `subprocess.run()` call. These cannot be separated from the outside.

**Heuristic decomposition:**
- **CLI overhead estimate:** Empirically measured as ~1-3 seconds for `claude -p` startup. This is approximately constant regardless of prompt size.
- **Model reasoning estimate:** `wall_clock_seconds - CLI_OVERHEAD_ESTIMATE_SECONDS`

This decomposition is labeled as `"estimated_decomposition"` in the benchmark output. It becomes unnecessary when the transport migrates to a direct API, which reports processing time separately.

```python
# Empirical constant — measured on the development machine.
# Varies by machine, CLI version, and authentication state.
CLI_OVERHEAD_ESTIMATE_SECONDS: float = 2.0
```

### 8.4 Queue Idle Time

Queue idle time is the time the scheduler spends between node dispatches when no work is happening. This captures scheduler overhead and the cost of sequential dispatch:

```python
# Measured as:
phase_idle = phase_total_wall_clock - sum(node_dispatch_wall_clocks)
```

---

## 9. Failure Isolation Strategy

### 9.1 Core Principle

**Benchmark failures MUST NEVER alter orchestration outcomes.** This is achieved through three mechanisms:

### 9.2 Mechanism 1: Exception Swallowing

Every benchmark operation is wrapped in a try/except that logs and swallows:

```python
def _safe_record(ledger: BenchmarkLedger | None, record: BenchmarkInvocationRecord) -> None:
    """Append a record to the ledger. Never raises."""
    if ledger is None:
        return
    try:
        ledger.append(record)
    except Exception:
        logger.debug(
            "Benchmark record append failed for invocation %s (non-blocking)",
            record.invocation_id,
            exc_info=True,
        )
```

### 9.3 Mechanism 2: Context Variable Guard

When `get_ledger()` returns `None`, all benchmark code paths are no-ops:

```python
def instrumented_invoke(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    timeout_seconds: int,
    tools: list[str] | None = None,
    # Benchmark metadata (not passed to transport)
    _bench_skill_id: str | None = None,
    _bench_node_id: str | None = None,
    _bench_predicate_id: str | None = None,
    _bench_invocation_type: str = "unknown",
) -> str:
    """Instrumented wrapper around invoke_claude_text().

    Captures telemetry when a benchmark ledger is active.
    Falls through to plain invoke_claude_text() when benchmarking is off.
    """
    ledger = get_ledger()

    if ledger is None:
        # Benchmarking disabled — zero overhead path
        return invoke_claude_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            tools=tools,
        )

    # Benchmarking enabled — capture telemetry
    t0 = time.monotonic()
    ts = datetime.now(timezone.utc).isoformat()
    # ... capture, invoke, record ...
```

### 9.4 Mechanism 3: Separate I/O Path

Benchmark artifacts write to `.claude/benchmark/`, completely separate from:
- Tier 4 state (`docs/tier4_orchestration_state/`)
- Run state (`.claude/runs/`)
- Skill diagnostics (`.claude/skill_diag/`)
- Gate results (Tier 4 phase outputs)

A corrupted or missing benchmark directory has zero impact on orchestration.

### 9.5 Failure Categories

| Failure | Impact | Handling |
|---------|--------|----------|
| Ledger file open fails | No telemetry for run | Log warning, continue without benchmarking |
| Ledger append fails | Missing record | Log debug, continue |
| Analytics computation fails | No summary artifacts | Log warning, write partial or skip |
| Provider projection fails | No projection artifacts | Log warning, skip projection |
| Benchmark dir creation fails | No benchmark artifacts | Log warning, continue without benchmarking |
| Token estimation NaN/overflow | Bad estimate | Clamp to 0, log debug |

---

## 10. Provider Projection Strategy

### 10.1 Provider Catalog

The projection engine uses a provider catalog that maps providers to their pricing, capabilities, and constraints:

```json
// .claude/benchmark/config/provider_catalog.json
{
  "catalog_version": "1.0.0",
  "providers": {
    "anthropic_claude_code_max": {
      "display_name": "Anthropic (Claude Code Max subscription)",
      "billing_model": "subscription",
      "monthly_cost_usd": 200.0,
      "models": {
        "claude-sonnet-4-6": {
          "supports_tools": true,
          "supports_system_prompt": true,
          "max_context_tokens": 200000,
          "max_output_tokens": 64000
        }
      },
      "notes": "Current transport. No per-token cost but monthly cap."
    },
    "anthropic_api": {
      "display_name": "Anthropic API (direct)",
      "billing_model": "per_token",
      "models": {
        "claude-sonnet-4-6": {
          "input_cost_per_mtok": 3.00,
          "output_cost_per_mtok": 15.00,
          "supports_tools": true,
          "supports_system_prompt": true,
          "max_context_tokens": 200000,
          "max_output_tokens": 64000
        }
      }
    },
    "together_ai": {
      "display_name": "Together AI",
      "billing_model": "per_token",
      "models": {
        "meta-llama/Llama-3.1-70B-Instruct-Turbo": {
          "input_cost_per_mtok": 0.88,
          "output_cost_per_mtok": 0.88,
          "supports_tools": true,
          "supports_system_prompt": true,
          "max_context_tokens": 131072,
          "max_output_tokens": 32768,
          "openai_compatible": true
        },
        "meta-llama/Llama-3.1-405B-Instruct-Turbo": {
          "input_cost_per_mtok": 3.50,
          "output_cost_per_mtok": 3.50,
          "supports_tools": true,
          "supports_system_prompt": true,
          "max_context_tokens": 131072,
          "max_output_tokens": 32768,
          "openai_compatible": true
        }
      }
    },
    "fireworks_ai": {
      "display_name": "Fireworks AI",
      "billing_model": "per_token",
      "models": {
        "accounts/fireworks/models/llama-v3p1-70b-instruct": {
          "input_cost_per_mtok": 0.90,
          "output_cost_per_mtok": 0.90,
          "supports_tools": true,
          "supports_system_prompt": true,
          "max_context_tokens": 131072,
          "max_output_tokens": 32768,
          "openai_compatible": true
        }
      }
    },
    "aws_bedrock": {
      "display_name": "AWS Bedrock",
      "billing_model": "per_token",
      "models": {
        "anthropic.claude-sonnet-4-6-v1": {
          "input_cost_per_mtok": 3.00,
          "output_cost_per_mtok": 15.00,
          "supports_tools": true,
          "supports_system_prompt": true,
          "max_context_tokens": 200000,
          "max_output_tokens": 64000,
          "requires_aws_credentials": true
        },
        "meta.llama3-1-70b-instruct-v1:0": {
          "input_cost_per_mtok": 2.65,
          "output_cost_per_mtok": 3.50,
          "supports_tools": false,
          "supports_system_prompt": true,
          "max_context_tokens": 128000,
          "max_output_tokens": 8192
        }
      }
    },
    "azure_openai": {
      "display_name": "Azure OpenAI / Azure AI Foundry",
      "billing_model": "per_token",
      "models": {
        "gpt-4o": {
          "input_cost_per_mtok": 2.50,
          "output_cost_per_mtok": 10.00,
          "supports_tools": true,
          "supports_system_prompt": true,
          "max_context_tokens": 128000,
          "max_output_tokens": 16384,
          "openai_compatible": true
        }
      }
    },
    "local_vllm": {
      "display_name": "Local vLLM / TGI / Ollama",
      "billing_model": "infrastructure",
      "models": {
        "meta-llama/Llama-3.1-70B-Instruct": {
          "input_cost_per_mtok": 0.0,
          "output_cost_per_mtok": 0.0,
          "supports_tools": true,
          "supports_system_prompt": true,
          "max_context_tokens": 131072,
          "max_output_tokens": 32768,
          "openai_compatible": true,
          "requires_gpu": true,
          "min_vram_gb": 140,
          "notes": "Cost is infrastructure (GPU rental/ownership), not per-token."
        }
      }
    }
  }
}
```

### 10.2 Projection Computation

For each observed invocation pattern, the projection engine computes:

```python
@dataclass
class ProviderProjection:
    """Projected cost and feasibility for a single provider+model."""

    provider_id: str
    model_id: str
    display_name: str

    # ── Cost ──
    projected_input_cost_usd: float
    projected_output_cost_usd: float
    projected_total_cost_usd: float
    cost_vs_current: str            # "cheaper" | "similar" | "more_expensive"
    cost_ratio: float               # projected / current (if current has per-token pricing)

    # ── Feasibility ──
    context_window_sufficient: bool  # All invocations fit in context window?
    oversized_invocations: int       # Count of invocations exceeding context window
    tool_support_sufficient: bool    # Supports tools if TAPM is used?
    system_prompt_supported: bool

    # ── Capability ──
    supports_all_modes: bool         # Can handle both TAPM and cli-prompt patterns
    openai_compatible: bool
    migration_complexity: str        # "drop_in" | "adapter_needed" | "significant_work"

    # ── Latency Estimate ──
    estimated_latency_multiplier: float | None  # vs current, if data available
```

### 10.3 Projection Report Structure

```json
{
  "benchmark_schema_version": "1.0.0",
  "run_id": "...",
  "projection_timestamp": "...",
  "observed_workload": {
    "total_invocations": 47,
    "total_estimated_input_tokens": 1250000,
    "total_estimated_output_tokens": 180000,
    "max_single_invocation_input_tokens": 85000,
    "requires_tool_support": true,
    "requires_system_prompt": true
  },
  "projections": [
    { "provider_id": "anthropic_api", "model_id": "claude-sonnet-4-6", "...": "..." },
    { "provider_id": "together_ai", "model_id": "meta-llama/...", "...": "..." },
    "..."
  ],
  "recommendations": {
    "lowest_cost": "together_ai/meta-llama/Llama-3.1-70B-Instruct-Turbo",
    "best_capability_match": "anthropic_api/claude-sonnet-4-6",
    "best_cost_capability_ratio": "...",
    "migration_warnings": [
      "TAPM mode requires tool support — 2 providers lack this",
      "3 invocations exceed 128K context — exclude Llama-70B for those"
    ]
  }
}
```

---

## 11. OpenAI-Compatible Migration Strategy

### 11.1 Current Transport Analysis

The current transport (`runner/claude_transport.py`) has a clean, narrow interface:

```python
def invoke_claude_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    timeout_seconds: int = 300,
    tools: list[str] | None = None,
) -> str:
```

This interface maps directly to the OpenAI Chat Completions API:

| Current parameter | OpenAI equivalent |
|---|---|
| `system_prompt` | `messages[0] = {"role": "system", "content": system_prompt}` |
| `user_prompt` | `messages[1] = {"role": "user", "content": user_prompt}` |
| `model` | `model` |
| `max_tokens` | `max_tokens` / `max_completion_tokens` |
| `timeout_seconds` | Client-level timeout |
| `tools` | `tools` (with schema adaptation for TAPM) |

### 11.2 Transport Abstraction Interface

The future transport layer introduces a `TransportBackend` protocol:

```python
# runner/transport/backend.py (future — not implemented in Phase 1)

from typing import Protocol

class TransportBackend(Protocol):
    """Provider-agnostic inference transport."""

    def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        timeout_seconds: int,
        tools: list[dict] | None = None,
    ) -> TransportResult:
        """Invoke the backend and return a structured result."""
        ...

@dataclass(frozen=True)
class TransportResult:
    """Structured result from any transport backend."""

    text: str                          # Response text
    input_tokens: int | None           # Actual input tokens (None if unavailable)
    output_tokens: int | None          # Actual output tokens (None if unavailable)
    model_id: str                      # Actual model ID used
    finish_reason: str | None          # "stop" | "max_tokens" | "tool_use" | None
    wall_clock_seconds: float          # Wall-clock time for the invocation
    provider_metadata: dict | None     # Provider-specific metadata
```

### 11.3 Backend Implementations (Future)

| Backend | Transport | Auth | Tools Support |
|---------|-----------|------|--------------|
| `ClaudeCLIBackend` | Current `claude -p` subprocess | Claude Code Max subscription | `--tools "Read,Glob"` |
| `AnthropicAPIBackend` | `anthropic.Anthropic().messages.create()` | API key | Native tool_use |
| `OpenAICompatBackend` | `openai.OpenAI(base_url=...).chat.completions.create()` | API key | Native tools |
| `BedrockBackend` | `boto3.client("bedrock-runtime").invoke_model()` | AWS credentials | Converse API tools |
| `AzureOpenAIBackend` | `openai.AzureOpenAI().chat.completions.create()` | Azure AD / API key | Native tools |
| `LocalOpenAIBackend` | `openai.OpenAI(base_url="http://localhost:PORT/v1")` | None | vLLM/TGI tool support |

### 11.4 TAPM Tool Translation

The current TAPM mode uses `--tools "Read,Glob"` to give Claude access to filesystem tools. When migrating to API-based transports, these tools must be translated to the provider's tool schema:

```python
# Current (Claude CLI):
# --tools "Read,Glob" → Claude Code's built-in Read/Glob tools

# OpenAI-compatible translation:
TAPM_TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the local filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": "Find files matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g. '**/*.json')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in"
                    }
                },
                "required": ["pattern"]
            }
        }
    }
]
```

For API-based TAPM, the transport backend must implement a tool execution loop:
1. Send initial prompt with tool definitions
2. Receive response with tool_use blocks
3. Execute tool calls (read file, glob)
4. Send tool results back
5. Repeat until model responds with text (no more tool calls)
6. Return final text response

This is a **significant implementation complexity** that is out of scope for the observability phase but must be planned for.

---

## 12. Future Heterogeneous Routing Architecture

### 12.1 Routing Concept

Heterogeneous routing allows different invocation types to be routed to different backends based on complexity, cost, and capability requirements:

```
Invocation Classification:
─────────────────────────

  ┌─────────────────────┐     ┌──────────────────────────┐
  │ Semantic Predicates  │────▶│ High-capability backend   │
  │ (constitutional      │     │ (Claude Sonnet/Opus,       │
  │  compliance, open-   │     │  GPT-4o, Llama-405B)      │
  │  ended reasoning)    │     └──────────────────────────┘
  └─────────────────────┘

  ┌─────────────────────┐     ┌──────────────────────────┐
  │ Phase 8 Drafting     │────▶│ High-capability backend   │
  │ (excellence, impact, │     │ (requires strong writing,  │
  │  implementation)     │     │  domain knowledge)         │
  └─────────────────────┘     └──────────────────────────┘

  ┌─────────────────────┐     ┌──────────────────────────┐
  │ Phase 1-7 Skills     │────▶│ Mid-capability backend    │
  │ (extraction, norm-   │     │ (Llama-70B, Mixtral,      │
  │  alization, mapping) │     │  Qwen-72B, GPT-4o-mini)   │
  └─────────────────────┘     └──────────────────────────┘

  ┌─────────────────────┐     ┌──────────────────────────┐
  │ Gate Enforcement     │────▶│ Mid-capability backend    │
  │ (structured JSON     │     │ (structured output is      │
  │  output, bounded)    │     │  the key requirement)      │
  └─────────────────────┘     └──────────────────────────┘

  ┌─────────────────────┐     ┌──────────────────────────┐
  │ Deterministic        │────▶│ No backend (pure Python)  │
  │ Predicates           │     │ Already zero-LLM.         │
  └─────────────────────┘     └──────────────────────────┘
```

### 12.2 Routing Table

The routing table maps invocation classifications to backend preferences:

```python
@dataclass
class RoutingRule:
    """A single routing rule for invocation classification."""
    invocation_type: str        # "skill_tapm" | "skill_cli_prompt" | "semantic_predicate"
    skill_id: str | None        # Specific skill, or None for all
    phase_number: int | None    # Specific phase, or None for all
    preferred_backend: str      # Backend ID from provider catalog
    fallback_backend: str       # Fallback if preferred is unavailable
    min_capability_tier: str    # "high" | "mid" | "low"
```

### 12.3 Routing Decision Data

The benchmark subsystem's primary contribution to heterogeneous routing is **empirical data** about which invocations can tolerate lower-capability models. This comes from:

1. **Prompt complexity analysis:** Skills with highly structured prompts (extraction, normalization) are more likely to work with smaller models.
2. **Output schema rigidity:** Skills requiring strict JSON conformance need models with strong structured output support.
3. **Token volume:** Skills that process large inputs (Phase 8 TAPM, 100KB+ reads) need large context windows.
4. **Semantic depth:** Semantic predicates require constitutional reasoning — harder to delegate to smaller models.

### 12.4 Routing Implementation Location

Routing decisions are made in the **transport layer**, not the scheduler or agent runtime. This preserves the existing call-graph constraints (CLAUDE.md §17.1):

```
skill_runtime.run_skill()
    └── invoke_claude_text()  ← Currently: calls claude CLI directly
            ↓
        [Future: RoutingDispatcher]
            ├── route_to_backend(invocation_metadata)
            ├── selected_backend.invoke(...)
            └── return response text
```

The scheduler, agent runtime, and skill runtime remain unaware of which backend served a specific invocation. This is essential for preserving deterministic gate behavior — the gate evaluator evaluates artifacts, not backend choices.

---

## 13. Security and Privacy Implications

### 13.1 Prompt Content Protection

**The benchmark subsystem MUST NOT capture or store prompt content.** Prompts contain:
- Tier 3 project data (partner names, capabilities, budgets — confidential)
- Tier 2B call extracts (publicly available but context-sensitive)
- Skill specifications (repository intellectual property)
- Constitutional rules (publicly available but context-binding)

The ledger records only:
- `system_prompt_chars: int` — character count, not content
- `user_prompt_chars: int` — character count, not content
- `response_chars: int | None` — character count, not content
- Metadata about the invocation (skill_id, model, timing, etc.)

### 13.2 Provider Catalog Sensitivity

The provider catalog (`.claude/benchmark/config/provider_catalog.json`) contains only public pricing information. It does not contain:
- API keys
- Authentication credentials
- Endpoint URLs specific to a user's deployment

### 13.3 Benchmark Artifact Sensitivity

Benchmark artifacts contain:
- Timing data (not sensitive)
- Token estimates (not sensitive — derived from character counts)
- Skill IDs and node IDs (repository-internal identifiers, low sensitivity)
- Model names (public information)
- Error messages (may contain path fragments — sanitize before external sharing)

**Recommendation:** Benchmark artifacts should be `.gitignore`-d by default (they are already under `.claude/`, which is typically git-ignored). If benchmark artifacts are to be shared externally (e.g., for provider evaluation), error messages should be sanitized to remove absolute paths.

### 13.4 Provider Projection Privacy

When projecting costs to external providers, the projection engine operates on **aggregated statistics** (total tokens, invocation counts, context window requirements), not on prompt content. No prompt content is sent to any external service during projection.

---

## 14. Runtime Overhead Analysis

### 14.1 Per-Invocation Overhead

When benchmarking is **enabled**:

| Operation | Estimated time | Notes |
|-----------|---------------|-------|
| `get_ledger()` context var lookup | ~50ns | Python ContextVar — effectively free |
| `time.monotonic()` × 2 | ~200ns | Two calls (before/after) |
| `len(system_prompt)` + `len(user_prompt)` | ~100ns | Python len() on strings |
| `len(response_text)` | ~50ns | Python len() on string |
| `BenchmarkInvocationRecord` construction | ~500ns | Frozen dataclass construction |
| Token estimation (2 multiplications) | ~100ns | Pure arithmetic |
| `json.dumps(record)` + file write | ~50μs | JSONL append, buffered |
| **Total per-invocation overhead** | **~51μs** | **vs. 10-1200s invocation time** |

**Overhead ratio:** 51μs / 10,000ms (minimum invocation) = **0.0005%**. Effectively zero.

When benchmarking is **disabled** (default):

| Operation | Estimated time |
|-----------|---------------|
| `get_ledger()` returning None | ~50ns |
| Early return (no further work) | ~0ns |
| **Total overhead when disabled** | **~50ns** |

### 14.2 Per-Run Overhead

| Operation | Estimated time | Notes |
|-----------|---------------|-------|
| Ledger file open | ~1ms | Once per run |
| Analytics computation | ~10-50ms | In-memory aggregation over ~50-200 records |
| Provider projection | ~5-20ms | Arithmetic over catalog × invocations |
| Artifact writes (5-7 JSON files) | ~5-10ms | Small files, buffered I/O |
| **Total per-run overhead** | **~20-80ms** | **vs. 30-120 minute run time** |

### 14.3 Memory Overhead

| Data structure | Estimated memory | Notes |
|----------------|-----------------|-------|
| In-memory invocation records | ~200 bytes × N invocations | ~10KB for 50 invocations |
| Node timing records | ~100 bytes × N nodes | ~1.3KB for 13 nodes |
| Analytics results | ~5KB | Aggregated statistics |
| Provider projections | ~3KB | Per-provider summaries |
| **Total memory overhead** | **~20KB** | **Negligible** |

### 14.4 Disk Overhead

| Artifact | Estimated size | Notes |
|----------|---------------|-------|
| `invocation_ledger.jsonl` | ~50KB per run | ~1KB per invocation × 50 invocations |
| `run_benchmark_summary.json` | ~15KB | Comprehensive summary |
| `phase_analytics.json` | ~5KB | Phase breakdown |
| `token_economics.json` | ~3KB | Token details |
| `timing_profile.json` | ~5KB | Latency distributions |
| `provider_projection.json` | ~10KB | Multi-provider projections |
| **Total disk per run** | **~90KB** | **Trivial** |

---

## 15. Incremental Implementation Phases

### Phase A: Foundation (Passive Observability)

**Goal:** Capture invocation telemetry without any routing or provider changes.

**Deliverables:**
1. `runner/benchmark/__init__.py` — Package init
2. `runner/benchmark/context.py` — Context variable for active ledger
3. `runner/benchmark/models.py` — Data model classes (§3)
4. `runner/benchmark/ledger.py` — Append-only invocation ledger
5. `runner/benchmark/transport_hook.py` — Instrumented transport wrapper
6. `runner/benchmark/token_estimator.py` — Character-to-token estimation

**Integration changes (minimal):**
- `runner/skill_runtime.py`: Replace 2 `invoke_claude_text()` calls with `instrumented_invoke()` wrapper
- `runner/semantic_dispatch.py`: Replace 1 `invoke_claude_text()` call with `instrumented_invoke()` wrapper
- `runner/dag_scheduler.py`: Add ledger creation/finalization in `run()`, node timing in `_dispatch_node()`

**Tests:** ~80-120 new tests covering data models, ledger append, transport hook, token estimation.

**Risk:** Minimal. All changes are additive. No existing behavior is modified when benchmarking is disabled.

### Phase B: Analytics Engine

**Goal:** Compute aggregate statistics from collected telemetry.

**Deliverables:**
1. `runner/benchmark/analytics.py` — Phase/node/skill analytics
2. `runner/benchmark/timing.py` — Latency distribution computation
3. `runner/benchmark/report_builder.py` — Summary artifact construction

**Integration changes:**
- `runner/dag_scheduler.py`: Call analytics engine after dispatch loop, before `RunSummary.write()`

**Tests:** ~60-80 new tests covering analytics computation, edge cases (empty runs, single-node runs, timeout-heavy runs).

### Phase C: Provider Projection

**Goal:** Project observed workload onto alternative providers.

**Deliverables:**
1. `runner/benchmark/provider_projection.py` — Projection engine
2. `.claude/benchmark/config/provider_catalog.json` — Provider pricing data
3. `.claude/benchmark/config/token_ratios.json` — Model-specific char-to-token ratios
4. `runner/benchmark/routing_analyzer.py` — Routing recommendation engine

**Integration changes:**
- `runner/dag_scheduler.py`: Call projection engine after analytics, before artifact write

**Tests:** ~40-60 new tests covering projection computation, provider catalog parsing, routing analysis.

### Phase D: Reporting CLI

**Goal:** Human-readable benchmark reports from the command line.

**Deliverables:**
1. `runner/benchmark/__main__.py` — CLI entry point (`python -m runner.benchmark`)
2. `runner/benchmark/formatters.py` — Terminal-friendly output formatting
3. Cross-run comparison capability

**Tests:** ~20-30 CLI tests.

### Phase E: Transport Abstraction (Future — Not in Initial Implementation)

**Goal:** Introduce the `TransportBackend` protocol and first alternative backend.

**Deliverables:**
1. `runner/transport/__init__.py` — Transport package
2. `runner/transport/backend.py` — `TransportBackend` protocol
3. `runner/transport/result.py` — `TransportResult` dataclass
4. `runner/transport/claude_cli.py` — Current transport wrapped as backend
5. `runner/transport/openai_compat.py` — OpenAI-compatible HTTP backend
6. `runner/transport/router.py` — Backend selection/routing

**Integration changes:**
- `runner/claude_transport.py`: Refactored to delegate to `TransportBackend`
- `runner/skill_runtime.py`: Updated to consume `TransportResult`
- `runner/semantic_dispatch.py`: Updated to consume `TransportResult`

**Tests:** ~100-150 new tests for transport abstraction, backend implementations, routing logic.

### Phase F: Heterogeneous Routing (Future)

**Goal:** Route different invocation types to different backends.

**Requires:** Phase E complete. Empirical data from Phase A-C runs.

---

## 16. Required Code Modifications by File

### 16.1 `runner/claude_transport.py`

**Phase A changes: NONE.** The transport module is unchanged. Instrumentation wraps at call sites, not at the transport definition.

**Phase E changes (future):** Refactor `invoke_claude_text()` to delegate to a `TransportBackend` instance obtained from a registry. The function signature remains identical for backward compatibility.

### 16.2 `runner/skill_runtime.py`

**Phase A changes:**

```
Location: TAPM invoke (around line 1197-1205)
Change:   Replace direct invoke_claude_text() with instrumented_invoke()
          Add _bench_skill_id=skill_id, _bench_node_id=node_id,
          _bench_invocation_type="skill_tapm"

Location: cli-prompt invoke (around line 1280-1286)
Change:   Replace direct invoke_claude_text() with instrumented_invoke()
          Add _bench_skill_id=skill_id, _bench_node_id=node_id,
          _bench_invocation_type="skill_cli_prompt"

Location: imports (line 44-49)
Change:   Add import of instrumented_invoke from benchmark.transport_hook

Note:     The existing time.monotonic() timing in run_skill() is preserved.
          The benchmark hook adds transport-level timing INSIDE the existing
          skill-level timing.
```

Lines affected: ~15 lines changed, ~3 lines added (imports).

### 16.3 `runner/semantic_dispatch.py`

**Phase A changes:**

```
Location: invoke_agent() Claude invocation (around line 646-651)
Change:   Replace direct invoke_claude_text() with instrumented_invoke()
          Add _bench_predicate_id=pred_id, _bench_node_id=None,
          _bench_invocation_type="semantic_predicate"

Location: imports (line 56-60)
Change:   Add import of instrumented_invoke from benchmark.transport_hook
```

Lines affected: ~8 lines changed, ~2 lines added.

### 16.4 `runner/dag_scheduler.py`

**Phase A changes:**

```
Location: run() entry (after line 1229 started_at)
Change:   Create BenchmarkRunCollector, set context variable
          ~8 lines added

Location: _dispatch_node() entry (after line 1453)
Change:   Record node dispatch start time
          ~3 lines added

Location: _dispatch_node() exit (before each return NodeExecutionResult)
Change:   Record node dispatch end time and result
          ~4 lines added per return point (5 return points = ~20 lines)

Location: run() after dispatch loop (around line 1315)
Change:   Run analytics, projections, write benchmark artifacts
          ~15 lines added

Location: run() exit/exception (before summary.write())
Change:   Finalize benchmark collector, clear context variable
          ~5 lines added

Location: imports
Change:   Add benchmark imports
          ~3 lines added
```

Lines affected: ~55 lines added.

### 16.5 `runner/agent_runtime.py`

**Phase A changes:**

```
Location: run_agent() skill invocation loop (around line 1246)
Change:   No direct changes needed. Skill-level timing is already captured
          by the transport hook inside run_skill(). Agent-level timing is
          captured by the scheduler's _dispatch_node() timing.

Optional Phase B enhancement:
          Add agent_body_start/end timing for finer decomposition.
          ~6 lines added.
```

### 16.6 `runner/gate_evaluator.py`

**Phase A changes:**

```
No direct changes needed. Semantic predicate timing is captured by the
transport hook in semantic_dispatch.py. Deterministic predicate timing
is not LLM-mediated and is captured by the scheduler's gate-level timing.

Optional Phase B enhancement:
          Emit deterministic predicate batch timing to the benchmark ledger.
          ~10 lines added.
```

### 16.7 `runner/runtime_models.py`

**No changes.** Runtime contracts are unchanged. Benchmark data models live in `runner/benchmark/models.py`.

### 16.8 `runner/run_context.py`

**No changes.** Run state management is unchanged. Benchmark state is managed by the `BenchmarkRunCollector`, which is independent of `RunContext`.

### 16.9 `.gitignore`

```
Add: .claude/benchmark/
(Note: .claude/ may already be gitignored entirely)
```

---

## 17. Required New Modules and Files

### 17.1 Python Modules

| File | Phase | Purpose | Estimated LOC |
|------|-------|---------|---------------|
| `runner/benchmark/__init__.py` | A | Package init, public API surface | ~30 |
| `runner/benchmark/context.py` | A | ContextVar for active ledger | ~40 |
| `runner/benchmark/models.py` | A | All data model classes (§3) | ~250 |
| `runner/benchmark/ledger.py` | A | Append-only JSONL ledger | ~120 |
| `runner/benchmark/transport_hook.py` | A | Instrumented transport wrapper | ~180 |
| `runner/benchmark/token_estimator.py` | A | Char-to-token estimation | ~80 |
| `runner/benchmark/analytics.py` | B | Phase/node/skill analytics | ~300 |
| `runner/benchmark/timing.py` | B | Latency distribution computation | ~100 |
| `runner/benchmark/report_builder.py` | B | Summary artifact construction | ~200 |
| `runner/benchmark/provider_projection.py` | C | Provider cost projection | ~250 |
| `runner/benchmark/routing_analyzer.py` | C | Routing recommendation engine | ~150 |
| `runner/benchmark/__main__.py` | D | CLI entry point | ~150 |
| `runner/benchmark/formatters.py` | D | Terminal output formatting | ~200 |

**Total new Python code (Phases A-D): ~2,050 LOC**

### 17.2 Configuration Files

| File | Phase | Purpose |
|------|-------|---------|
| `.claude/benchmark/config/provider_catalog.json` | C | Provider pricing data |
| `.claude/benchmark/config/token_ratios.json` | A | Model char-to-token ratios |

### 17.3 Test Files

| File | Phase | Estimated tests |
|------|-------|----------------|
| `tests/runner/benchmark/test_models.py` | A | ~30 |
| `tests/runner/benchmark/test_ledger.py` | A | ~25 |
| `tests/runner/benchmark/test_transport_hook.py` | A | ~35 |
| `tests/runner/benchmark/test_token_estimator.py` | A | ~20 |
| `tests/runner/benchmark/test_context.py` | A | ~10 |
| `tests/runner/benchmark/test_analytics.py` | B | ~40 |
| `tests/runner/benchmark/test_timing.py` | B | ~20 |
| `tests/runner/benchmark/test_report_builder.py` | B | ~25 |
| `tests/runner/benchmark/test_provider_projection.py` | C | ~30 |
| `tests/runner/benchmark/test_routing_analyzer.py` | C | ~20 |
| `tests/runner/benchmark/test_cli.py` | D | ~20 |
| `tests/runner/benchmark/test_integration.py` | A-D | ~30 |

**Total new tests: ~305 tests**

---

## 18. Testing Strategy

### 18.1 Unit Testing

Each benchmark module is unit-tested in isolation:

- **Data models:** Construction, serialization, field validation, edge cases (None values, empty lists, zero counts).
- **Ledger:** Append, flush, concurrent append (thread safety), file corruption recovery, read-back parsing.
- **Transport hook:** Mock `invoke_claude_text()`, verify record fields, verify exception re-raising, verify timing accuracy, verify zero-overhead when disabled.
- **Token estimator:** Known char→token mappings, unknown models (fallback), edge cases (0 chars, very large strings).
- **Analytics:** Known invocation sets → expected aggregates. Edge cases: empty run, single invocation, all failures, all timeouts.
- **Provider projection:** Known workload → expected costs. Context window overflow detection. Tool support checking.

### 18.2 Integration Testing

- **Transport hook + skill_runtime:** Verify that wrapping `invoke_claude_text()` does not alter `SkillResult` outcomes. Mock at `subprocess.run` level.
- **Transport hook + semantic_dispatch:** Verify that wrapping does not alter semantic predicate results.
- **Scheduler + benchmark collector:** Verify that enabling benchmarking does not alter `RunSummary` outcomes. Compare `RunSummary` with and without benchmarking on identical synthetic DAGs.
- **Full-stack benchmark:** Synthetic run with mocked Claude responses → verify all benchmark artifacts are produced and internally consistent.

### 18.3 Regression Testing

- **Orchestration invariance:** The existing 1600+ tests must continue to pass with no modification. The benchmark subsystem is strictly additive — it adds new tests without modifying existing ones.
- **Transport contract preservation:** Tests that mock `invoke_claude_text` must work identically whether the benchmark hook is active or not.

### 18.4 Performance Testing

- **Overhead measurement:** Micro-benchmark comparing `invoke_claude_text()` vs `instrumented_invoke()` with and without active ledger. Target: <100μs overhead per invocation.
- **Memory measurement:** Track memory allocation during a synthetic 200-invocation run with benchmarking enabled. Target: <1MB additional memory.

### 18.5 Mock Strategy

All tests mock at the same point the existing test suite uses: `runner.claude_transport.invoke_claude_text`. The benchmark transport hook wraps this function, so mocking the underlying transport works transparently:

```python
# Existing test pattern (unchanged):
@mock.patch("runner.claude_transport.invoke_claude_text")
def test_skill_execution(mock_invoke):
    mock_invoke.return_value = '{"schema_id": "...", ...}'
    result = run_skill("my-skill", run_id, repo_root)
    assert result.status == "success"

# Benchmark tests add ledger verification:
@mock.patch("runner.claude_transport.invoke_claude_text")
def test_skill_execution_with_benchmark(mock_invoke):
    mock_invoke.return_value = '{"schema_id": "...", ...}'
    ledger = BenchmarkLedger()
    set_ledger(ledger)
    try:
        result = run_skill("my-skill", run_id, repo_root)
        assert result.status == "success"
        assert len(ledger.records) == 1
        assert ledger.records[0].skill_id == "my-skill"
    finally:
        set_ledger(None)
```

---

## 19. Migration Risk Analysis

### 19.1 Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Benchmark hook alters invocation timing measurement | Low | Medium | Use separate `time.monotonic()` calls inside the hook; do not rely on existing `_skill_t0` |
| Benchmark JSONL write blocks on full disk | Very Low | Low | Best-effort write with exception swallowing. Set max ledger size with rotation. |
| Context variable leaks across runs | Low | Low | Explicit `set_ledger(None)` in `finally` block at `run()` exit |
| Token estimation inaccuracy misleads provider selection | Medium | Medium | Label all estimates with `token_source: "estimated"`. Document accuracy bounds. |
| Provider catalog pricing becomes stale | High | Low | Catalog is a configuration file, not a live feed. Document last-updated date. |
| Transport hook breaks existing test mocking | Low | High | Hook wraps at call site, not at definition site. Existing mocks of `invoke_claude_text` continue to work. Verified by running full test suite. |
| Phase E transport abstraction introduces latency | Medium | Medium | Phase E is deferred until benchmarking data validates the migration benefit. |
| TAPM token estimation is wildly inaccurate | Medium | Medium | Use ceiling estimate (total `reads_from` file sizes). Label as `"estimated_tapm_ceiling"`. |
| Benchmark artifacts accumulate unbounded disk usage | Medium | Low | Add `--clean-benchmarks --older-than 30d` CLI command. Add disk usage warning in report. |
| Import of benchmark package slows runner startup | Low | Low | Lazy imports only — benchmark modules are imported at `run()` entry, not at module load time. |

### 19.2 Rollback Strategy

Every phase has a clean rollback:

- **Phase A:** Remove `runner/benchmark/` package. Revert 3 files (`skill_runtime.py`, `semantic_dispatch.py`, `dag_scheduler.py`) to remove instrumented calls. Zero residual impact.
- **Phase B:** Remove analytics modules. Phase A continues to produce raw ledger.
- **Phase C:** Remove projection modules. Phases A-B continue to work.
- **Phase D:** Remove CLI. Phases A-C continue to work.
- **Phase E:** Revert transport abstraction. Return to direct `claude -p` calls.

### 19.3 Constitutional Risk Assessment

| Concern | Assessment |
|---------|-----------|
| Does this modify gate behavior? | **No.** Benchmark modules never evaluate gates. |
| Does this modify artifact schemas? | **No.** Benchmark schemas are independent of `artifact_schema_specification.yaml`. |
| Does this modify the scheduler dispatch contract? | **No.** Node states, failure origins, and state machine are unchanged. |
| Does this modify the transport function signature? | **No** (Phase A-D). Phase E modifies internal implementation but preserves the external signature. |
| Does this introduce new runtime dependencies? | **No.** All benchmark code uses stdlib only (`dataclasses`, `json`, `time`, `contextvars`, `pathlib`). |
| Does this store data in `docs/`? | **No.** All artifacts are in `.claude/benchmark/` (runtime execution memory). |
| Does this modify Tier 1-5 state? | **No.** Benchmark is read-only with respect to tiered state. |

---

## 20. Recommended Implementation Order

### Step 1: Data Models and Token Estimator (Day 1)

Files: `runner/benchmark/models.py`, `runner/benchmark/token_estimator.py`, `runner/benchmark/context.py`
Tests: `tests/runner/benchmark/test_models.py`, `tests/runner/benchmark/test_token_estimator.py`, `tests/runner/benchmark/test_context.py`

Rationale: Pure data definitions with no integration. Can be reviewed and tested independently.

### Step 2: Ledger (Day 1-2)

Files: `runner/benchmark/ledger.py`
Tests: `tests/runner/benchmark/test_ledger.py`

Rationale: Depends only on models. JSONL append logic is self-contained.

### Step 3: Transport Hook (Day 2-3)

Files: `runner/benchmark/transport_hook.py`
Tests: `tests/runner/benchmark/test_transport_hook.py`

Rationale: The core instrumentation wrapper. Must be thoroughly tested before integration.

### Step 4: Integration into Call Sites (Day 3-4)

Files modified: `runner/skill_runtime.py`, `runner/semantic_dispatch.py`
Tests: Existing test suite must pass. New integration tests.

Rationale: Minimal changes — replace 3 `invoke_claude_text()` calls with `instrumented_invoke()`.

### Step 5: Scheduler Integration (Day 4-5)

Files modified: `runner/dag_scheduler.py`
Tests: Existing scheduler tests must pass. New benchmark lifecycle tests.

Rationale: Create/finalize benchmark collector in `run()`, add node timing in `_dispatch_node()`.

### Step 6: Analytics Engine (Day 5-7)

Files: `runner/benchmark/analytics.py`, `runner/benchmark/timing.py`, `runner/benchmark/report_builder.py`
Tests: `tests/runner/benchmark/test_analytics.py`, `tests/runner/benchmark/test_timing.py`, `tests/runner/benchmark/test_report_builder.py`

Rationale: Post-processing layer. No integration changes — reads from in-memory ledger.

### Step 7: Provider Projection (Day 7-8)

Files: `runner/benchmark/provider_projection.py`, `runner/benchmark/routing_analyzer.py`, `.claude/benchmark/config/provider_catalog.json`
Tests: `tests/runner/benchmark/test_provider_projection.py`, `tests/runner/benchmark/test_routing_analyzer.py`

Rationale: Read-only projection. No integration changes.

### Step 8: CLI and Formatting (Day 8-9)

Files: `runner/benchmark/__main__.py`, `runner/benchmark/formatters.py`
Tests: `tests/runner/benchmark/test_cli.py`

Rationale: User-facing reporting. No integration changes.

### Step 9: Full Integration Test (Day 9-10)

Files: `tests/runner/benchmark/test_integration.py`

Rationale: End-to-end validation with synthetic DAG run. Verify:
- All 1600+ existing tests pass unchanged
- Benchmark artifacts are produced for instrumented runs
- `RunSummary` outcomes are identical with and without benchmarking
- Provider projections are internally consistent

---

## Appendix A: Current Architecture Analysis

### A.1 Transport Boundary Analysis

`runner/claude_transport.py` is a clean, narrow transport boundary:
- **Single function:** `invoke_claude_text()` — no state, no side effects beyond subprocess invocation.
- **Parameters:** `system_prompt`, `user_prompt`, `model`, `max_tokens`, `timeout_seconds`, `tools`.
- **Returns:** Raw response text (str).
- **Exceptions:** `ClaudeTransportError`, `ClaudeCLITimeoutError`, `ClaudeCLIUnavailableError`.
- **System prompt handling:** Uses `--system-prompt` flag when under 24,000 chars; embeds in user prompt when over.
- **No retry logic:** Single attempt; failure is immediate and propagated.

This interface is **already transport-agnostic in signature**. The benchmarking subsystem can instrument it without modifying it. The future transport abstraction (Phase E) can replace the subprocess implementation without changing the function signature.

### A.2 TAPM Semantics Analysis

TAPM (Tool-Augmented Prompt Mode) is used by 12+ skills:
- Skills with `execution_mode: "tapm"` in skill_catalog.yaml
- Prompt is ~5-30KB (task metadata + skill spec, no serialized inputs)
- Claude reads inputs from disk via `Read` and `Glob` tools
- Timeout: 1200 seconds (vs. 300 for cli-prompt)
- Tools: `["Read", "Glob"]`

**Benchmark implications:**
- TAPM invocations have higher variance in token consumption (depends on how many files Claude reads)
- TAPM invocations have higher wall-clock time (multiple tool round-trips)
- Token estimation for TAPM requires separate handling (see §7.5)
- TAPM mode determines which providers can serve the invocation (requires tool support)

### A.3 Semantic Predicate Dispatch Analysis

`runner/semantic_dispatch.py` handles 7 registered semantic predicates:
- `no_unresolved_scope_conflicts`
- `no_cross_tier_contradictions`
- `no_unsupported_tier5_claims`
- `no_budget_gate_contradiction`
- `no_higher_tier_contradiction`
- `no_forbidden_schema_authority`
- `no_gap_masked_as_confirmed`

Each semantic predicate invocation:
- Reads artifact content from disk
- Builds system + user prompts with artifact content embedded
- Invokes `claude-sonnet-4-6` via `invoke_claude_text()` (cli-prompt mode, no tools)
- Parses structured JSON response
- Validates against §4.9 result schema
- Model: `AGENT_MODEL = "claude-sonnet-4-6"`, `max_tokens = 2048`

**Benchmark implications:**
- Semantic predicates are a distinct invocation class from skills
- They use the same model but different prompt structure
- They are invoked only when all deterministic predicates pass
- Their cost scales with the number of semantic-bearing gates (currently gates with semantic predicates are Phase 2, Phase 8e, Phase 8f)
- Provider migration must preserve constitutional reasoning quality

### A.4 Gate Evaluation Flow Analysis

`runner/gate_evaluator.py` orchestrates:
1. Load gate rules library
2. Resolve predicates (Approach B via manifest, fallback to Approach A)
3. Compute input fingerprints
4. Evaluate deterministic predicates (40+ registered, no LLM calls)
5. If all pass: evaluate semantic predicates (LLM calls via CS3)
6. Write GateResult to Tier 4
7. Update RunContext node state
8. Apply HARD_BLOCK propagation

**Benchmark implications:**
- Deterministic predicates are zero-LLM-cost work — the benchmark must track this to compute the deterministic/model-mediated work split
- Semantic evaluation is skipped when deterministic predicates fail — the benchmark must record this as "skipped_semantic" to avoid undercounting potential semantic cost
- Gate evaluation time includes both deterministic (fast) and semantic (slow) components — the benchmark must decompose these

### A.5 Reuse Mechanics Analysis

Phase 8 reuse (`runner/phase8_reuse.py`):
- Reuse-eligible nodes: `n08a_excellence_drafting`, `n08b_impact_drafting`, `n08c_implementation_drafting`
- Reuse skips the expensive drafting skill but still runs audit skills
- Reuse decision is recorded in `RunContext` and `RunSummary`

**Benchmark implications:**
- Reuse saves the most expensive invocations (Phase 8 drafting = TAPM, 1200s timeout, large outputs)
- The benchmark must track `tokens_saved_by_reuse` to quantify reuse effectiveness
- The benchmark must distinguish "reuse_skipped" skills from "not_applicable" skills

### A.6 Phase 8 Specialization Analysis

Phase 8 is structurally distinct from Phases 1-7:
- 6 sub-nodes (n08a through n08f) vs. 1 node per phase for Phases 1-7
- Drafting skills use TAPM with 1200s timeout
- Audit skills (traceability-check, compliance-check) run after drafting
- Gate predicates include Phase 8-specific checks (section predicates, criterion predicates)
- Assembly and revision nodes have unique skill sequences

**Benchmark implications:**
- Phase 8 cost must be reported separately from Phases 1-7
- Phase 8 TAPM drafting is the dominant cost center (likely 60-80% of total run tokens)
- Phase 8 reuse is the primary cost optimization lever
- Phase 8 node decomposition (drafting vs. audit vs. gate) provides the most actionable optimization data

---

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **Invocation** | A single call to `invoke_claude_text()` — the atomic unit of LLM interaction. |
| **Ledger** | The append-only JSONL file recording all invocations in a run. |
| **Transport hook** | The instrumentation wrapper around `invoke_claude_text()` at each call site. |
| **Token estimate** | A character-count-derived approximation of actual token usage. |
| **Provider projection** | An estimated cost/latency/feasibility analysis for an alternative inference provider. |
| **Routing rule** | A mapping from invocation classification to preferred backend (future). |
| **TAPM** | Tool-Augmented Prompt Mode — Claude reads inputs from disk via tools instead of receiving them serialized in the prompt. |
| **CLI-prompt** | Classical execution mode where all inputs are serialized into the prompt and piped to `claude -p`. |
| **Deterministic predicate** | A gate predicate evaluated by pure Python code (no LLM). |
| **Semantic predicate** | A gate predicate evaluated by Claude (requires LLM invocation). |
| **Ceiling estimate** | An upper-bound token estimate for TAPM, based on total declared input file sizes. |

---

## Appendix C: CLAUDE.md Amendment Requirements

When the benchmarking subsystem is implemented and validated, a constitutional amendment to CLAUDE.md will be required:

**Section to amend:** Section 17 (Runtime Execution Architecture)

**New subsection:** §17.7 — Benchmarking and Observability Layer

**Content summary:**
- Declares the benchmarking subsystem as a passive observability layer subordinate to the execution stack
- Establishes `.claude/benchmark/` as a runtime execution memory directory (§9.2 class)
- Affirms that benchmark failures never alter orchestration outcomes
- Affirms that benchmark modules never evaluate gates, invoke skills, or write Tier 4/5 state
- Establishes the transport hook as the sole instrumentation point for invocation telemetry

**Amendment trigger:** After Phase A is implemented, tested (all 1600+ existing tests pass), and validated in at least one production-equivalent run.

---

*Plan version: 1.0.0. Produced for the `benchmark_engine` branch.*
