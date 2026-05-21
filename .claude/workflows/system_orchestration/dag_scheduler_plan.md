# DAG Scheduler — Implementation Plan

**Status:** Fully implemented — Steps 1–6 complete. 762 tests pass.
**Applies to:** `system_orchestration` package v1.1
**Prerequisite:** Gate rules library (Approach A) and manifest-driven predicate composition (Approach B) are complete. `evaluate_gate()` is fully implemented.
**Scope:** DAG scheduler, HARD_BLOCK propagation, run summary artifact, and CLI entry point.

---

## 1. Problem Statement

`evaluate_gate()` can evaluate a single gate in isolation but nothing orchestrates a full run. Given `manifest.compile.yaml` and an initialised `RunContext`, there is no component that:

- reads the node and edge registries to determine which nodes are ready to execute,
- dispatches nodes in dependency order,
- propagates gate failures through the downstream subgraph,
- enforces the `HARD_BLOCK` freeze rule for Phase 8 nodes when `gate_09` fails,
- produces a durable run summary artifact.

This plan implements the DAG scheduler as a new module `runner/dag_scheduler.py` plus a thin CLI entry point `runner/__main__.py`. It builds exclusively on existing interfaces: `RunContext`, `evaluate_gate()`, and `manifest.compile.yaml`.

---

## 2. Concepts and Invariants

### 2.1 Node states

Node states are defined in `runner/run_context.py` and must be used as-is. The scheduler drives transitions between them:

| State | Meaning |
|-------|---------|
| `pending` | Not yet dispatched |
| `running` | Dispatched; gate evaluation in progress |
| `blocked_at_entry` | Entry gate failed; node body not executed |
| `blocked_at_exit` | Exit gate failed; node body ran but gate did not pass |
| `released` | Exit gate passed; downstream edges are unblocked |
| `deterministic_pass_semantic_pending` | Deterministic predicates passed; semantic evaluation outstanding |
| `hard_block_upstream` | Frozen by `HARD_BLOCK` propagation from `gate_09` |

The scheduler must only call `set_node_state()` with these values. It must never invent new state strings.

### 2.2 Ready condition

A node is ready to execute when:

1. Its state is `pending`.
2. **All** edges whose `to_node` is this node have their `gate_condition` satisfied — i.e., the source node is in state `released`.
3. Where an edge carries an `additional_condition`, that gate's source node is also in state `released`.

A node with no incoming edges (n01_call_analysis) is immediately ready.

### 2.3 Settled condition

A node is settled when its state is any terminal value: `released`, `blocked_at_entry`, `blocked_at_exit`, or `hard_block_upstream`. Settled nodes are never re-dispatched.

### 2.4 Blocking propagation

When a node's exit gate fails (state → `blocked_at_exit`), all downstream nodes that depend on that gate remain `pending` indefinitely — they never become ready because the gate condition on their incoming edge is never satisfied. The scheduler detects this as a stall: no nodes are ready and no nodes are running, but unsettled nodes remain. This is not a bug; it is correct behaviour. The scheduler must surface it as a declared run failure, not a hang.

### 2.5 HARD_BLOCK (gate_09)

When `gate_09_budget_consistency` fails and `RunContext.mark_hard_block_downstream()` has been called, the four Phase 8 node IDs (`n08a_section_drafting`, `n08b_assembly`, `n08c_evaluator_review`, `n08d_revision`) are set to `hard_block_upstream`. The scheduler calls `mark_hard_block_downstream()` immediately after `evaluate_gate()` returns a failing result for `gate_09_budget_consistency`. These nodes are never dispatched regardless of edge conditions.

### 2.6 Entry gates

`n01_call_analysis` has an entry gate (`gate_01_source_integrity`) evaluated before the node body runs. The scheduler must call `evaluate_gate()` for the entry gate before marking the node `running` and again for the exit gate after. If the entry gate fails, the node transitions to `blocked_at_entry` and is settled without execution.

No other node in the current manifest has an `entry_gate` field. The scheduler must read `entry_gate` from the node definition and apply this logic generically, not hardcode n01 as a special case.

---

## 3. Module: `runner/dag_scheduler.py`

### 3.1 ManifestGraph

A lightweight in-memory graph built from `manifest.compile.yaml` at scheduler startup. It does not duplicate `RunContext` state; it provides read-only structural queries.

```
ManifestGraph
  .load(manifest_path: Path | None, *, repo_root: Path | None) -> ManifestGraph
  .node_ids() -> list[str]                         # in registry order
  .entry_gate(node_id: str) -> str | None          # None if node has no entry gate
  .exit_gate(node_id: str) -> str | None           # None if terminal/no gate
  .is_terminal(node_id: str) -> bool
  .incoming_conditions(node_id: str) -> list[IncomingCondition]
  .is_ready(node_id: str, ctx: RunContext) -> bool  # ready condition §2.2
```

`IncomingCondition` is a simple dataclass: `gate_id: str, source_node_id: str`.

`load()` raises `DAGSchedulerError` if the manifest is missing or its node/edge registries are malformed.

### 3.2 DAGScheduler

The main orchestration class.

```
DAGScheduler
  .__init__(graph: ManifestGraph, ctx: RunContext, repo_root: Path,
            library_path: Path | None, manifest_path: Path | None)
  .run() -> RunSummary
  ._dispatch_node(node_id: str) -> None
  ._settle_stalled_nodes() -> None
```

**`run()` algorithm:**

```
while True:
    ready = [n for n in graph.node_ids()
             if ctx.get_node_state(n) == "pending"
             and n not in hard_blocked
             and graph.is_ready(n, ctx)]
    if not ready:
        break   # all nodes settled, stalled, or hard-blocked
    for node_id in ready:
        _dispatch_node(node_id)

_settle_stalled_nodes()
summary = RunSummary.build(ctx=ctx, graph=graph, ...)
summary.write(ctx.run_dir)
return summary  # raises RunAbortedError instead when pending nodes remain
```

This is a synchronous, single-threaded loop. Parallelism is deferred (see §7).

**`_dispatch_node(node_id)`:**

1. Set node state → `running`.
2. If `entry_gate` is not None: call `evaluate_gate(entry_gate, ...)`. If result status is not `pass`: set state → `blocked_at_entry`, return.
3. Call `evaluate_gate(exit_gate, ...)`.
4. If result status is `pass`: set state → `released`.
5. If result status is not `pass`:
   - If gate_id is `gate_09_budget_consistency`: call `ctx.mark_hard_block_downstream()`; set state → `blocked_at_exit`.
   - Otherwise: set state → `blocked_at_exit`.

The scheduler does not call the agent or run the node body. At this stage, node body execution is out of scope (see §7). The scheduler drives the gate evaluation loop against already-produced artifacts, consistent with the existing `evaluate_gate()` contract.

**`_settle_stalled_nodes()`:**

After the dispatch loop exits, any node still `pending` is unreachable (blocked by upstream failure). Write a log entry for each stalled node identifying which gate condition was never satisfied. Do not change their state — they remain `pending` in `RunContext` as evidence of the stall.

### 3.3 Exceptions

```python
class DAGSchedulerError(Exception):
    """Raised for scheduler configuration or manifest structural errors."""

class RunAbortedError(DAGSchedulerError):
    """Raised when run() detects that no progress is possible and
    at least one non-terminal node is unsettled."""
```

`RunAbortedError` is raised at the end of `run()` when any node remains `pending` after the dispatch loop exits. `RunSummary` is built and written to disk before raising. The exception carries `.summary` (the authoritative `RunSummary` object) and `.result` (`summary.to_dict()` — stable compatibility surface for callers that previously indexed a plain dict).

---

## 4. Run Summary Artifact

**Path:** `.claude/runs/<run_id>/run_summary.json`

Written by `RunSummary.build()` and persisted to disk at the end of every `run()` call, whether the run succeeded or aborted.

**Schema:**

```json
{
  "run_id": "...",
  "manifest_version": "1.1",
  "library_version": "1.0",
  "constitution_version": "...",
  "started_at": "<ISO-8601>",
  "completed_at": "<ISO-8601>",
  "overall_status": "pass | partial_pass | fail | aborted",
  "terminal_nodes_reached": ["n08d_revision"],
  "stalled_nodes": [],
  "hard_blocked_nodes": [],
  "node_states": {
    "n01_call_analysis": "released",
    "n02_concept_refinement": "released",
    "..."
  },
  "gate_results_index": {
    "gate_01_source_integrity": "docs/tier4_orchestration_state/.../gate_01_source_integrity.json",
    "phase_01_gate": "docs/tier4_orchestration_state/.../phase_01_gate.json",
    "..."
  }
}
```

**`overall_status` values:**

| Value | Condition |
|-------|-----------|
| `pass` | All terminal nodes reached and all exit gates passed |
| `partial_pass` | At least one terminal node reached but not all |
| `fail` | No terminal node reached; at least one gate failed |
| `aborted` | `RunAbortedError` raised; no terminal node reached; stalled or hard-blocked nodes present |

The `gate_results_index` maps each evaluated gate_id to the canonical Tier 4 path where its `GateResult` JSON file was written. This uses `runner.gate_result_registry` which is already implemented.

---

## 5. CLI Entry Point: `runner/__main__.py`

Invoked as `python -m runner`.

**Arguments:**

```
python -m runner \
  --run-id <run_id> \
  [--repo-root <path>]            # default: auto-discovered via find_repo_root()
  [--library-path <path>]         # default: repo_root / LIBRARY_REL_PATH
  [--manifest-path <path>]        # default: repo_root / MANIFEST_REL_PATH
  [--dry-run]                     # print ready nodes and exit without evaluating
  [--json]                        # emit progress as JSON lines to stdout
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Run completed; `overall_status` is `pass` |
| 1 | Run completed; `overall_status` is `fail` or `partial_pass` |
| 2 | Run aborted (`RunAbortedError`) |
| 3 | Configuration error (`DAGSchedulerError`) or unhandled exception |

**Stdout format (default):**

```
[RUN]   run_id=abc123
[READY] n01_call_analysis
[GATE]  gate_01_source_integrity → pass
[GATE]  phase_01_gate → pass
[DONE]  n01_call_analysis → released
[READY] n02_concept_refinement
...
[SUMMARY] overall_status=pass  nodes_released=11  stalled=0  hard_blocked=0
```

With `--json`, each line is a JSON object with `event`, `node_id` or `gate_id`, `status`, and `timestamp` fields.

---

## 6. Implementation Sequence

### Step 1 — ManifestGraph ✓ Implemented

Implement `ManifestGraph.load()` and all read methods. No RunContext dependency. Cover:
- Loading the node registry and edge registry from `manifest.compile.yaml`.
- `incoming_conditions(node_id)` returning all `(gate_id, source_node_id)` pairs from edges pointing to the node, including `additional_condition` edges.
- `is_ready(node_id, ctx)` enforcing §2.2.
- `entry_gate()` and `exit_gate()` reading from node definitions.

**Tests:** Unit tests using synthetic manifest dicts (no file I/O required). Cover: single-node graph, linear chain, fork-join (n03→n04 and n03→n05→n06), additional_condition (e02_to_05), no-incoming-edge node is immediately ready.

### Step 2 — DAGScheduler core loop ✓ Implemented

Implement `DAGScheduler.__init__()`, `run()`, and `_dispatch_node()`. At this stage, `_dispatch_node()` calls `evaluate_gate()` for real.

**Tests:** Use synthetic repos from `tests/runner/fixtures/`. Cover:
- Single-node graph: entry gate passes → node released.
- Single-node graph: entry gate fails → `blocked_at_entry`.
- Two-node linear: first node released, second becomes ready, second released.
- Two-node linear: first node gate fails → second never dispatched; `_settle_stalled_nodes()` logs stall.
- `gate_09` failure → `propagate_hard_block()` called → Phase 8 nodes `hard_block_upstream`.

### Step 3 — HARD_BLOCK and stall detection ✓ Implemented

Implement `_settle_stalled_nodes()` and `RunAbortedError` raising logic. Ensure `RunSummary` is written before the exception propagates.

**Tests:** Cover: stalled subgraph after upstream failure; mixed settled/stalled; HARD_BLOCK with Phase 8 nodes present.

### Step 4 — RunSummary ✓ Implemented

Implement `RunSummary.build()` and disk write. Cover all four `overall_status` values.

**Tests:** Unit tests constructing RunSummary from mock RunContext state. Verify correct JSON schema, correct `overall_status`, correct `gate_results_index` paths.

### Step 5 — CLI entry point ✓ Implemented

Implement `runner/__main__.py`. Include `--dry-run` and `--json` modes.

**Tests:** Subprocess tests invoking `python -m runner` with a synthetic repo. Verify exit codes, stdout format, and that `run_summary.json` is written to `.claude/runs/<run_id>/`.

### Step 6 — Full DAG integration scenarios ✓ Implemented

End-to-end tests against a fully populated synthetic repo covering:
- Linear pass through all 11 gates (n01 → n08d).
- Phase 4 + Phase 5 parallel paths: both dispatched after n03 released; both must pass before n06 becomes ready.
- Early gate failure (Phase 2) halts n03, n04, n05, n06, n07, n08*: all stall; `RunAbortedError` raised; summary written.
- `gate_09` HARD_BLOCK: n07 fails → n08a/b/c/d frozen → `run_summary.json` `hard_blocked_nodes` populated.
- Partial pass: some terminal nodes reached, others stalled.

---

## 7. Out of Scope for This Plan

The following are not part of this plan and must not be implemented speculatively:

**Node body execution.** The scheduler drives gate evaluation against already-produced artifacts. It does not invoke agents, call skills, or produce phase outputs. Node body execution (calling `call_analyzer`, `concept_refiner`, etc.) is the subject of the Skill Runtime + Agent Runtime Integration Plan, which bridges the agent layer (16 agents, Steps 1–7 complete) and the skill layer (19 skills, Steps 1–10 complete) with the DAG scheduler's dispatch loop.

**Parallel dispatch.** The run loop is single-threaded. Phase 4 and Phase 5 are identified as a parallel path in the manifest but the scheduler evaluates them sequentially within a single iteration of the ready-node loop. True concurrent dispatch is deferred pending a concurrency model decision.

**Re-run / resume logic.** The scheduler starts from RunContext as initialised. It does not inspect prior run_summary.json files or implement incremental re-entry into an in-progress run. Each `run()` call operates on the current RunContext state.

**Agent-in-loop semantic evaluation.** `evaluate_gate()` calls `invoke_agent()` for semantic predicates. The scheduler does not need to know about this — it calls `evaluate_gate()` and reads the result status. The agent loop is already implemented in `runner/semantic_dispatch.py`.

---

## 8. File Summary

| File | Action | Description |
|------|--------|-------------|
| `runner/dag_scheduler.py` | New | `ManifestGraph`, `DAGScheduler`, `RunSummary`, `DAGSchedulerError`, `RunAbortedError` |
| `runner/__main__.py` | New | CLI entry point (`python -m runner`) |
| `tests/runner/test_manifest_graph.py` | New | Unit tests for ManifestGraph (Step 1) |
| `tests/runner/test_dag_scheduler.py` | New | Unit + integration tests for DAGScheduler (Steps 2–5) |
| `tests/runner/test_dag_full_run.py` | New | End-to-end full-DAG scenarios (Step 6) |
| `runner/run_context.py` | No change | HARD_BLOCK propagation already implemented |
| `runner/gate_evaluator.py` | No change | Already accepts `library_path` and `manifest_path` kwargs |
| `manifest.compile.yaml` | No change | Node and edge registries already define the graph |

---

## 9. Test Count (Actual)

| Test file | Actual tests |
|-----------|-------------|
| `test_manifest_graph.py` | 21 |
| `test_dag_scheduler.py` | 122 |
| `test_dag_full_run.py` | 55 |
| **DAG scheduler total** | **198** |
| **Cumulative total** | **762** |

---

## 10. Implemented Contract (Finalization Reference)

### Entry points

```python
graph   = ManifestGraph.load(manifest_path)               # or repo_root=
ctx     = RunContext.initialize(repo_root, run_id)
sched   = DAGScheduler(graph, ctx, repo_root,
                        library_path=..., manifest_path=...)
summary = sched.run()                                      # may raise RunAbortedError
```

### Return / exception behavior

| Outcome | Return | Side effect |
|---------|--------|-------------|
| All terminal nodes reached | `RunSummary` (overall_status=`pass`) | `run_summary.json` written |
| Some terminal nodes reached | `RunSummary` (overall_status=`partial_pass`) | `run_summary.json` written |
| No terminal node reached, no pending | `RunSummary` (overall_status=`fail`) | `run_summary.json` written |
| Pending nodes remain (stall) | raises `RunAbortedError` | `run_summary.json` written first |

### Summary artifact

Written to: `.claude/runs/<run_id>/run_summary.json`

Key fields: `run_id`, `overall_status`, `terminal_nodes_reached`, `stalled_nodes`,
`hard_blocked_nodes`, `node_states`, `gate_results_index`, `dispatched_nodes`,
`started_at`, `completed_at`.

### CLI invocation

```
python -m runner --run-id <uuid> [--repo-root <path>] [--library-path <path>]
                  [--manifest-path <path>] [--dry-run] [--json]
```

Exit codes: `0` = pass, `1` = fail/partial_pass, `2` = aborted, `3` = config error.

Dry-run semantics: initializes RunContext, prints initially-ready nodes, exits 0.
Does NOT evaluate gates or write `run_summary.json`.

### Stable compatibility surface

`RunSummary` supports `summary["key"]` and `"key" in summary` (delegates to `to_dict()`).
`to_dict()` includes the plan-schema fields plus the following stable aliases:
`released_nodes`, `blocked_nodes`, `pending_nodes`, `stall_report`, `stalled`, `aborted`.

`RunAbortedError.result` is always exactly `exc.summary.to_dict()`.

---

*Plan authored 2026-04-07. Implementation complete 2026-04-08. Amendments require explicit human instruction.*
