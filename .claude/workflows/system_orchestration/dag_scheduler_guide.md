# DAG Scheduler — Operator and Developer Guide

Concise reference for running, consuming, and testing the scheduler.

---

## CLI invocation

```bash
python -m runner \
    --run-id <uuid>                          # required
    [--repo-root <path>]                     # default: auto-discovered via find_repo_root()
    [--manifest-path <path>]                 # default: <repo_root>/manifest.compile.yaml
    [--library-path <path>]                  # default: <repo_root>/gate_rules_library.yaml
    [--dry-run]                              # enumerate ready nodes; skip gate evaluation
    [--json]                                 # emit progress as JSON lines to stdout
```

Minimum invocation (from the repository root):

```bash
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())")
```

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Run completed; `overall_status == "pass"` |
| `1` | Run completed; `overall_status` is `"fail"` or `"partial_pass"` |
| `2` | Run aborted (`RunAbortedError`); pending nodes remained after dispatch |
| `3` | Configuration error (`DAGSchedulerError`) or unhandled exception |

---

## Dry-run mode

`--dry-run` is **side-effect-minimizing**, not side-effect-free.

What it does:
- Calls `RunContext.initialize()`, writing `.claude/runs/<run_id>/run_manifest.json` and `reuse_policy.json`
- Enumerates nodes where `ManifestGraph.is_ready()` returns `True` against the fresh context
- Prints (or emits `"ready"` JSON events for) each ready node, then exits 0

What it does **not** do:
- Evaluate any gates
- Write `run_summary.json`

---

## `run_summary.json` — contents and location

**Written to:** `.claude/runs/<run_id>/run_summary.json`

**Written when:** At the end of every `DAGScheduler.run()` call — whether the run
succeeded, partially passed, failed, or was aborted. The file is always written
*before* `run()` returns or raises.

**Schema (plan fields):**

```json
{
  "run_id": "...",
  "manifest_version": "...",
  "library_version": "...",
  "constitution_version": "...",
  "started_at": "2026-04-08T...",
  "completed_at": "2026-04-08T...",
  "overall_status": "pass | partial_pass | fail | aborted",
  "terminal_nodes_reached": ["n08d_revision"],
  "stalled_nodes": [],
  "hard_blocked_nodes": [],
  "node_states": {
    "n01_call_analysis": "released",
    "n02_concept_refinement": "released"
  },
  "gate_results_index": {
    "gate_01_source_integrity": "docs/tier4_orchestration_state/...",
    "phase_01_gate": "docs/tier4_orchestration_state/..."
  },
  "dispatched_nodes": ["n01_call_analysis", "n02_concept_refinement"]
}
```

`overall_status` values:

| Status | Meaning |
|--------|---------|
| `"pass"` | All terminal nodes reached |
| `"partial_pass"` | Some but not all terminal nodes reached |
| `"fail"` | No terminal nodes reached; some blocked |
| `"aborted"` | Pending nodes remained; `RunAbortedError` was raised |

---

## `RunAbortedError`

Raised by `DAGScheduler.run()` when pending nodes remain after the dispatch
loop exits — meaning one or more nodes could not be dispatched because all
their predecessors are blocked.

**Attributes:**

```python
exc.summary      # RunSummary dataclass — authoritative; written to run_summary.json
exc.result       # dict — stable compat alias; always exactly exc.summary.to_dict()
exc.args[0]      # human-readable message string
```

**Typical handling:**

```python
try:
    summary = sched.run()
except RunAbortedError as exc:
    summary = exc.summary          # or exc.result for dict access
    # summary.overall_status == "aborted"
    # summary.stalled_nodes  — list of {node_id, unsatisfied_conditions} dicts
    # summary.hard_blocked_nodes — nodes frozen by gate_09 HARD_BLOCK
```

---

## `RunSummary` — stable compatibility surface

`RunSummary` is a typed dataclass returned by `DAGScheduler.run()` (and
attached to `RunAbortedError.summary`).  Dict-style access (`summary["key"]`,
`"key" in summary`) is supported and delegates to `to_dict()`.

The following aliases are **stable public contract** in `to_dict()` and will
not be removed:

| Alias | Derived from |
|-------|-------------|
| `released_nodes` | nodes in `"released"` state |
| `blocked_nodes` | nodes in `"blocked_at_entry"` or `"blocked_at_exit"` |
| `pending_nodes` | nodes in `"pending"` state |
| `stall_report` | alias for `stalled_nodes` |
| `stalled` | `True` when `overall_status == "aborted"` |
| `aborted` | same as `stalled` |

These aliases are *not* written to `run_summary.json`; they exist for
in-process consumers only.

---

## Intentionally out-of-scope behaviors

The scheduler is a **gate-evaluation dispatch loop over pre-produced
artifacts**.  The following are out of scope and will not be added to this
module:

- **Node body execution** — invoking agents, skills, or tools on behalf of nodes
- **Parallel dispatch** — concurrent evaluation of multiple ready nodes
- **Rerun / resume logic** — replaying or skipping previously-run nodes
- **Semantic agent orchestration** — any action beyond calling `evaluate_gate()`
- **Budget computation** — the lump-sum budget is handled by the external Budget Planner integration
