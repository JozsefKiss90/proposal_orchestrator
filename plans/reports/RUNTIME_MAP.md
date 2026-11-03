# RUNTIME_MAP.md — runtime module map

Mental model of the `runner/` runtime, for fast orientation when debugging. Vocabulary lives in
`runner/CONTEXT.md` (runtime) and `harness/CONTEXT.md` (evaluation harness); see `CONTEXT-MAP.md`.
Refreshed 2026-11-03. Authoritative source is
`CLAUDE.md` §17 (Runtime Execution Architecture) — this file is a navigation aid, not a contract.
Check the decision logs in `docs/tier4_orchestration_state/decision_log/` for ADRs in any area you touch.

> **TAPM banner:** `CLAUDE.md` §17 still marks the Hybrid/TAPM migration (`backend_migration_plan.md`)
> as IN PROGRESS. Whether it is done is an open operator decision (`plans/overhaul_2026-11_plan.md` §6).
> Until §17 is amended, §17 as written remains in force.

## Execution stack (three layers + gate evaluator)
One caller per layer — violating the call graph is a constitutional violation (§17.1), so a "bug" that
looks like a layering shortcut is usually intended and the real fault is elsewhere.

| Layer | Module | Called by | Calls |
|-------|--------|-----------|-------|
| Scheduler | `runner/dag_scheduler.py` (`DAGScheduler`, `_dispatch_node()`) | CLI `runner/__main__.py` | agent runtime, gate evaluator |
| Agent runtime | `runner/agent_runtime.py` (`run_agent()`) | scheduler | skill runtime, deterministic components |
| Skill runtime | `runner/skill_runtime.py` (`run_skill()`) | agent runtime | Claude transport |
| Transport | `runner/claude_transport.py` | skill runtime + `semantic_dispatch.py` | local `claude` CLI (Max sub, no API key) |
| Gate evaluator | `runner/gate_evaluator.py` | **scheduler only** | predicate library |

Node dispatch is a fixed 5-step contract (§17.2): set `running` → entry gate → agent body (`run_agent`)
→ exit gate → `NodeExecutionResult`. Exit gate is skipped iff entry failed, agent body failed, or
`can_evaluate_exit_gate == False` (the flag is set by inspecting artifacts **on disk**, §17.6.6).

## Data contracts — `runner/runtime_models.py`
`SkillResult` (run_skill→agent), `AgentResult` (agent→scheduler; carries `invoked_skills`,
`invoked_components`, `can_evaluate_exit_gate`), `NodeExecutionResult` (dispatch→run loop). Failure is
classified by exactly one `failure_origin` ∈ {`entry_gate`,`agent_body`,`exit_gate`}. Metadata persists
via `runner/run_context.py` (`RunContext`) into `run_summary.json`.

## Residuals
The July 2026 residual list (4.2 transport hang, 4.5a preseed suppression, 4.5b gate-result
`schema_id`, gate_10b appositive predicate, checkpoint-publish run_id) was removed on 2026-11-03.
4.2 was fixed in `5570857f`; the others are unverified here. Current open work is tracked in
`.scratch/overhaul-2026-11/` and `plans/overhaul_2026-11_plan.md`.

## Deterministic, Claude-free components (§17.5.3) — not skills
Invoked inside the node body by the agent runtime; each guarantees byte-equal replay / pure lookup and
writes canonical artifacts via `_atomic_write`. The set: section assembler (`runner/section_assembler.py`),
assumption applier (`runner/assumption_applier.py`), canonical-pack derivers
(`runner/phase8_canonical_pack.py`, `runner/graph_canonical_pack.py`), unit-cost budget
(`runner/unit_cost_budget.py`), Call Slicer (`runner/call_slicer.py`, Step 0), decomposed drafting
(`runner/decomposed_drafting.py`). Recorded in `AgentResult.invoked_components`.

## Graph (M2 / `--from-graph`) track
`runner/graph_compiler.py`, `graph_config.py`, `graph_schema.py`, `vault_reader.py`,
`graph_projector.py`, `vault_scaffold.py` (+ `graph_canonical_pack.py`). Vault → `--from-graph` compile
to staging → `tools/promote_graph_staging.py` promotes to `docs/`. The **mtime-staleness residual (4.3)**
originates in that promote rewriting `architecture_inputs/*.json`.

## Predicate library — `runner/predicates/`
Gate predicates grouped by concern: `coverage_`, `criterion_`, `cycle_`, `file_`, `gate_pass_`,
`phase8_section_`, `schema_`, `scope_coverage_`, `source_ref_`, `timeline_`. Called only via the gate
evaluator; agents never evaluate gates (§17.6.2).

## Pointers
- Contract: `CLAUDE.md` (§6 phases/gates, §8 budget, §17 runtime).
- Debug plan: `plans/DEBUG_KICKOFF_phase8_calibration.md` (lane assignment + loops + prompts).
- Thread state: `HANDOFF_phase8_m2t10_2026-07-22.md`.
- Decisions/ADRs: `docs/tier4_orchestration_state/decision_log/`.
- Eval/calibration: `harness/HARNESS.md`, `harness/ACCEPTANCE_LANE.md`, `plans/harness_plan/`.
- DN pre-evaluation: `plans/msca_dn_pre_evaluation_spec.md`, `plans/msca_dn_pe09_runbook.md`.
