# Handover — Phase 8 stepwise execution (n08a–f), ticket-writing session

**Date:** 2026-08-13 · **Branch/tree:** `C:\Code\proposal_demo\proposal_orchestrator` · **Constitution:** `21430b0` · **Manifest:** 1.1

## 1. What the next session must produce

Tickets — in the house style of `plans/tickets_phase8_review.md` (What to build / Blocked by / checkbox
acceptance criteria, each ticket's first criterion being "re-verify the finding against current code") —
for making Phase 8 **operator-steppable**: run n08a → n08f one sub-phase at a time, inspecting and
evaluating the output of each before releasing the next, without corrupting upstream state.

Write tickets only. No implementation in that session.

## 2. State verified today (do not re-derive)

- Run `9468e1cf-2c71-49e8-91fb-57f6e7192126`: `n01`–`n07` **released**, `n08a`–`n08f` **pending**,
  `overall_status: pass`, `phase_scope: 7`.
- `gate_09_budget_consistency` **passed** 2026-08-13T15:47Z under `budget_regime: unit_cost`
  (4 deterministic predicates passed; the 8 lump-sum predicates correctly skipped as not-applicable).
  §8.4 / §13.4 therefore no longer block Phase 8.
- `docs/tier5_deliverables/{proposal_sections,assembled_drafts,review_packets,final_exports}/` are **empty**;
  `phase_outputs/phase8_drafting_review/` does not exist. Phase 8 has never run on this instantiation.
- Phases 1–6 gate evidence is durable in Tier 4 and was accepted via `accepted_upstream_gates` in the
  run manifest — cross-run bootstrap already works for the *upstream* direction.

## 3. Phase 8 is already decomposed — the gap is execution granularity, not design

`.claude/workflows/system_orchestration/manifest.compile.yaml` already defines six nodes
(`n08a_excellence_drafting`, `n08b_impact_drafting`, `n08c_implementation_drafting`, `n08d_assembly`,
`n08e_evaluator_review`, `n08f_revision`), each with `substep: a…f`, its own agent, skill roster,
deterministic components, exit gate (`gate_10a/b/c/d`, `gate_11`, `gate_12`) and edges
(a,b,c → d → e → f). Gate results have canonical per-gate paths in `runner/gate_result_registry.py`
(`phase_outputs/phase8_drafting_review/gate_10a_result.json`, …).

**Tickets must not redesign the DAG.** What is monolithic is the *invocation*. Three concrete findings:

1. **No node-level scope.** `runner/__main__.py::_parse_phase` regexes `^(?:phase[_-]?)?0*(\d+)` — `8a`
   parses to `8`. `ManifestGraph.nodes_for_phase(8)` returns all six nodes, and the dispatch loop
   (`dag_scheduler.py` ~L1285) keeps dispatching every ready in-scope node until none remain. So
   `--phase 8` runs a→f in one process. `substep` is present in the manifest but **read by nothing in
   `runner/`** — it is the natural key for a node/substep scope.
2. **Intra-phase prerequisites are never bootstrapped.** `bootstrap_phase_prerequisites`
   (`dag_scheduler.py` ~L221) does `upstream_needed -= phase_nodes`, i.e. it deliberately refuses to seed
   nodes inside the requested phase. With a fresh run-id, `n08d` alone can never become ready even with
   `gate_10a/b/c` passed and durable on disk. Reusing the *same* run-id (`RunContext.load_or_initialize`
   preserves node states) is today's only path and is untested for the a→f sequence.
3. **Re-running a sub-step can stale a sibling's gate.** Gate acceptance runs content-based freshness
   (`is_gate_fresh`, checked both at bootstrap and at `gate_pass_recorded` step 9). Documented precedent
   is in the manifest itself: run `531ec9f0` — an `n08f` re-run rewrote `review_packet.json`, the artifact
   `gate_11` had been evaluated on, so `gate_12/g11_p01` failed `STALE_UPSTREAM_MISMATCH` on every run
   reaching the gate. Any "inspect, fix, re-run just this node" loop hits exactly this.

## 4. Invariants the tickets must preserve (non-negotiable)

- §13.7 — no silent reordering, no weakened gate conditions to make stepping work. A step that cannot
  prove its predecessor passed must fail closed, not proceed.
- §17.6.2 — gates stay scheduler-owned; no agent/skill/CLI may write or assert a gate result.
- §6.3 / §9.4 — release of a sub-phase is evidenced only by a durable Tier 4 gate result artifact with
  `status: pass`, never by operator assertion or in-memory state.
- §16.5 — node ↔ agent ↔ skill ↔ component ↔ gate bindings come from the manifest; a stepping mechanism
  must not become a second binding source.
- Cross-run inheritance, if used, goes through the existing `accepted_upstream_gates` +
  CHK-1 provenance-quad mechanism (`runner/checkpoint_publisher.py`), not a new channel.

## 5. Levers that already exist — reuse, don't reinvent

`runner/phase8_reuse.py` (fail-closed reuse of n08a/b/c section artifacts, `REUSE_ELIGIBLE_NODES`,
skip-binding shared with preseed) · `runner/phase8_preseed.py` + `--preseed-phase8-sections` ·
`runner/phase8_skip_binding.py` · `runner/checkpoint_publisher.py` (cross-run gate authorization) ·
`RunContext.record_accepted_upstream_gate` · `--dry-run` (enumerates ready nodes, evaluates no gates) ·
`--json` (machine-readable progress, useful for per-step monitoring).

## 6. Candidate ticket surface (for the ticket session to confirm, split or reject)

- **Node/substep scope for the CLI** — e.g. `--node n08b_impact_drafting` or `--phase 8b`, resolved via the
  unused `substep` field; mutually exclusive with `--phase`; scope of exactly one node.
- **Intra-phase evidence bootstrap** — seed in-phase predecessors from durable per-gate results under
  `phase_outputs/phase8_drafting_review/`, with the same evidence + freshness + fail-closed rules as the
  existing upstream bootstrap, recorded in `accepted_upstream_gates`.
- **Rerun-without-staling** — decide and encode what happens when a sub-phase is re-run after its
  successors have gated (re-run forward-invalidates? blocks? requires explicit `--force` + decision-log
  entry?). This is the ticket most likely to need an operator decision before it can be written.
- **Operator inspection surface between steps** — what a step prints/writes so the run can be judged before
  the next is launched (artifacts written, components invoked, gate predicate detail).
- **Manifest hygiene** — the artifact registry still lists retired node ids `n08a_section_drafting` and
  `n08c_evaluator_review` in `consumed_by`/`produced_by` (manifest ~L848–911). Stale ids in a registry that
  a bootstrap feature is about to read.
- **Regression tests** — a→f stepped across six invocations reaches the same terminal state and the same
  gate results as a single `--phase 8` run; a step with a missing predecessor gate fails closed.

## 7. Open questions for the operator (ask before finalising tickets)

1. One run-id for the whole a→f sequence, or a new run-id per step with evidence bootstrap? (Affects
   whether ticket 2 above is required at all.)
2. Should a step *stop* after its exit gate regardless of scope (a `--stop-after-node` semantic), or is
   single-node scope sufficient?
3. On re-running an already-gated sub-phase: forward-invalidate successors automatically, or refuse?
