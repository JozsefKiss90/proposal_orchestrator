# gantt_designer prompt specification

## Purpose

Phase 4 node body executor for `n04_gantt_milestones`. Reads the Phase 3 WP structure and dependency map, the project duration from `selected_call.json`, and consortium roles to produce `gantt.json` (schema `orch.phase4.gantt.v1`) in Tier 4 and update `milestones_seed.json` in Tier 3. Assigns all tasks to months consistent with the dependency map, defines milestone due months and verifiable achievement criteria, and identifies the critical path. `phase_04_gate` is evaluated by the runner after this agent writes all canonical outputs.

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §7 Phase 4 gate condition, §13.3 (fabricated project facts — task assignments and duration), §13.7 (silent duration manipulation prohibited), §9.4 (durable decisions)
2. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json` — Verify `phase_03_gate` has passed before any further action
3. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — WP structure and dependency map; schema `orch.phase3.wp_structure.v1`
4. `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/scheduling_constraints.json` — Normalized scheduling constraints (produced by dependency_normalizer before this agent runs); classifies dependency edges as strict vs non-strict
5. `docs/tier3_project_instantiation/call_binding/selected_call.json` — Project duration constraint (authoritative source)
6. `docs/tier3_project_instantiation/consortium/roles.json` — Partner roles for task assignment
7. `.claude/agents/gantt_designer.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node binding: `n04_gantt_milestones`
- Phase: `phase_04_gantt_and_milestones`
- Entry gate: none (but `phase_03_gate` is a mandatory predecessor; verify before acting)
- Exit gate: `phase_04_gate`
- Predecessor edge: `e03_to_04` — `phase_03_gate` must have passed
- `gate-enforcement` skill: invoked by this agent after all outputs are complete

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| `phase_03_gate` gate result | Tier 4 | `phase_outputs/phase3_wp_design/gate_result.json` | Must show `pass`; halt immediately if absent or fail |
| WP structure and dependency map | Tier 4 | `phase_outputs/phase3_wp_design/wp_structure.json` | Must be present; `work_packages` and `dependency_map` non-empty; schema `orch.phase3.wp_structure.v1` |
| Normalized scheduling constraints | Tier 4 | `phase_outputs/phase4_gantt_milestones/scheduling_constraints.json` | Must be present (produced by dependency_normalizer before this agent runs); `strict_constraints` and `non_strict_constraints` arrays; schema `orch.phase4.scheduling_constraints.v1` |
| Project duration | Tier 3 | `call_binding/selected_call.json` | Must contain a non-null project duration in months; this is the authoritative scheduling constraint |
| Partner roles | Tier 3 | `consortium/roles.json` | Must be present; used for task-to-partner assignment verification |

Verify `wp_structure.json` has a populated `dependency_map` (contributed by `dependency_mapper`). If `dependency_map` is absent or null, this indicates Phase 3 did not complete properly — halt with Failure Case 2. Check for any declared dependency cycles in `dependency_map` — if cycles are present, execute Failure Case 4 (inherited Phase 3 cycle blocks scheduling).

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Verify predecessor gate.**
Read `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json`. If absent or not `pass`, halt immediately. Write `decision_type: constitutional_halt` citing edge `e03_to_04`.

**Step 2 — Read all inputs.**
Read `wp_structure.json`, `selected_call.json` (extract project duration in months), and `consortium/roles.json`. Extract all `task_id` values from all WPs. Check for dependency cycles in `dependency_map` — if any unresolved cycles are present, execute Failure Case 4.

**Steps 3–6 — Invoke `gantt-schedule-builder` skill.**
The `gantt-schedule-builder` skill executes the following as a single Claude invocation:
- Assign tasks to months respecting strict constraints from `scheduling_constraints.json`
- Define milestone due months and verifiable criteria from `milestones_seed.json`
- Identify the critical path from strict dependency chains
- Construct and write `gantt.json` to `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json`
This skill must complete and write `gantt.json` to disk BEFORE `milestone-consistency-check` runs, so that the validation skill can operate in FULL mode (schedule-level validation).

**Step 7 — milestones_seed.json.**
Gate condition `g05_p07` verifies `milestones_seed.json` is populated. This file is already pre-populated in Tier 3 and is consumed as input by `gantt-schedule-builder`. No overwrite is required unless the Phase 4 run determines that milestone definitions have materially changed.

**Step 8 — Invoke milestone-consistency-check skill.**
Invoke the `milestone-consistency-check` skill to verify:
- All milestone `due_month` values are consistent with task completion months
- No milestone `due_month` exceeds project duration
- All `verifiable_criterion` values are concrete and non-empty
Write the check result to `docs/tier4_orchestration_state/validation_reports/`. Flag any inconsistencies.
Note: `gantt.json` must already be written to disk (Step 6) so the skill runs in FULL mode with schedule-level validation. If `gantt.json` is absent, the skill falls back to DEGRADED mode (WP-level only).

**Step 9 — Invoke gate-enforcement skill.**
Invoke the `gate-enforcement` skill to evaluate `phase_04_gate`. Gate conditions:
1. `phase_03_gate` passed (`g05_p01`)
2. Gantt structure written to Tier 4 (`g05_p02`, `g05_p02b`)
3. All tasks assigned to months within project duration (`g05_p03`, `g05_p04`)
4. All milestones have verifiable criteria and due months (`g05_p05`)
5. Critical path identified and consistent with dependency map (`g05_p06`)
6. `milestones_seed.json` populated in Tier 3 (`g05_p07`)
7. Normalized scheduling constraints written to Tier 4 (`g05_p02c`, `g05_p02d`)
8. Schedule respects all strict dependency constraints (`g05_p08`)

**Step 10 — Write decision log entries.**
Invoke the `decision-log-update` skill for all material scheduling decisions, conflict resolutions, and the gate result.

---

## Output construction rules

### `gantt.json` (schema-bound)

**Path:** `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json`
**Schema ID:** `orch.phase4.gantt.v1`
**Provenance:** run_produced

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.phase4.gantt.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `artifact_status` | NO — absent at write time | Runner stamps after `phase_04_gate` evaluation |
| `tasks` | yes, non-empty array | Every `task_id` from `wp_structure.json` must appear; each: `task_id`, `wp_id`, `start_month`, `end_month`, `responsible_partner` |
| `tasks[].start_month` | yes, ≥ 1 | 1-based integer respecting dependency constraints |
| `tasks[].end_month` | yes, ≤ project_duration_months | Must not exceed project duration from `selected_call.json` |
| `tasks[].responsible_partner` | yes | From Tier 3 `partners.json` |
| `milestones` | yes, non-empty array | Each: `milestone_id`, `title`, `due_month` (1-based, non-null), `verifiable_criterion` (non-empty, concrete, not a placeholder), `responsible_wp` |
| `critical_path` | yes, non-empty array | Ordered list of `task_id` and `milestone_id` strings |

### `milestones_seed.json` (Tier 3 update, content-contract-only)

**Path:** `docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json`

Each milestone from `gantt.json` must have a corresponding entry with at minimum: `milestone_id`, `title`, `due_month`, `verifiable_criterion`.

---

## Traceability requirements

Task-to-month assignments must be traceable to the dependency map from `wp_structure.json` and to the project duration from `selected_call.json`. Partner assignments for tasks must trace to Tier 3 `roles.json`. Milestone verifiable criteria must trace to the WP deliverables or task outcomes defined in `wp_structure.json`. Critical path derivation must reference specific `dependency_map.edges`. Write `material_decision` entries for every scheduling decision.

---

## Gate awareness

### Predecessor gate
`phase_03_gate` — must have passed. Verified via `phase_outputs/phase3_wp_design/gate_result.json`. Edge `e03_to_04`. If not passed: halt, write `constitutional_halt`.

### Exit gate
`phase_04_gate` — evaluated after this agent writes all canonical outputs. This agent invokes `gate-enforcement` skill.

Gate conditions:
1. `phase_03_gate` passed (`g05_p01`)
2. Gantt structure written to Tier 4 (`g05_p02`, `g05_p02b`)
3. All tasks assigned to months within project duration (`g05_p03`, `g05_p04`)
4. All milestones have verifiable criteria and due months (`g05_p05`)
5. Critical path identified (`g05_p06`)
6. `milestones_seed.json` populated (`g05_p07`)
7. Normalized scheduling constraints written to Tier 4 (`g05_p02c`, `g05_p02d`)
8. Schedule respects all strict dependency constraints (`g05_p08`)

Gate result written by runner to `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gate_result.json`. Blocking edge on pass: `e04_to_06` (n06).

---

## Failure declaration protocol

#### Case 1: Gate condition not met (phase_04_gate fails)
- Do not proceed
- Write `gantt.json` with the schedule as produced; document which conditions failed
- Write decision log: `decision_type: gate_failure`; list failed conditions
- Must not: silently adjust project duration to make tasks fit (CLAUDE.md §13 — Tier 3 call binding governs duration)
- Must not: write placeholder milestone criteria

#### Case 2: Required input absent
- Halt if `wp_structure.json` is absent or project duration is absent from `selected_call.json`
- Write decision log: `decision_type: gate_failure`

#### Case 3: Mandatory predecessor gate not passed
- Halt immediately if `phase_03_gate` is not passed
- Write: `decision_type: constitutional_halt`

#### Case 4: WP structure has dependency cycle (inherited from Phase 3)
- Halt — do not schedule tasks on a cyclic dependency graph
- Write: `decision_type: gate_failure` — note the Phase 3 artifact has an unresolved cycle
- Must not: proceed with scheduling by ignoring declared dependency cycles

---

## Decision-log obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: gantt_designer`, `phase_id: phase_04_gantt_and_milestones`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Task scheduling decision (start/end month assignment) | `material_decision` | Task ID; month assignment; dependency basis |
| Schedule conflict resolved by prioritizing one dependency | `assumption` | Conflict; resolution; alternative considered |
| Critical path identified | `material_decision` | Path node list; derivation from dependency map |
| Scheduling conflict that cannot be resolved within project duration | `scope_conflict` | Conflicting tasks; why unresolvable; what is needed |
| `phase_04_gate` passes | `gate_pass` | Gate ID; all conditions confirmed; run_id |
| `phase_04_gate` fails | `gate_failure` | Gate ID; failed conditions |
| `phase_03_gate` predecessor not passed | `constitutional_halt` | Edge `e03_to_04`; status |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not assign tasks to months beyond the project duration — triggers Failure Case 1
2. Must not schedule a task start before prerequisite task completion — enforced via dependency map
3. Must not produce milestones without verifiable achievement criteria — triggers Failure Case 1
4. Must not silently adjust project duration to accommodate an oversized WP structure — triggers Failure Case 1 (declare failure instead)
5. Must not operate before `phase_03_gate` has passed — triggers Failure Case 3

Universal constraints from `node_body_contract.md` §3:
6. Must not write `artifact_status` to any output file (runner-managed)
7. Must not write `gate_result.json` (runner-managed)
8. Must not schedule tasks ignoring declared dependency cycles from Phase 3

---

## Completion criteria

This agent's task is complete when all of the following conditions are met:

1. `gantt.json` is written with all required fields; every `task_id` from `wp_structure.json` appears; `artifact_status` is absent
2. All tasks have `end_month` ≤ project duration from `selected_call.json`
3. All milestones have non-empty, concrete `verifiable_criterion` values
4. `critical_path` is a non-empty array
5. `milestones_seed.json` in Tier 3 is updated
6. All material scheduling decisions are written to the decision log
7. `gate-enforcement` skill has been invoked

Completion does not equal gate passage. `phase_04_gate` is evaluated by the runner.
