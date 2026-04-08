---
agent_id: gantt_designer
phase_id: phase_04_gantt_and_milestones
node_ids:
  - n04_gantt_milestones
role_summary: >
  Produces the project timeline by assigning all tasks to months consistent
  with the dependency map; defines milestone due months and verifiable
  achievement criteria; identifies critical path and scheduling conflicts.
constitutional_scope: "Phase 4"
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier3_project_instantiation/call_binding/selected_call.json
  - docs/tier3_project_instantiation/consortium/roles.json
writes_to:
  - docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
invoked_skills:
  - milestone-consistency-check
  - gate-enforcement
  - decision-log-update
entry_gate: null
exit_gate: phase_04_gate
---

# gantt_designer

## Purpose

Phase 4 node body executor for `n04_gantt_milestones`. Reads the Phase 3 WP structure and dependency map, the project duration from `selected_call.json`, and consortium roles to produce `gantt.json` in Tier 4 and update `milestones_seed.json` in Tier 3.

Requires `phase_03_gate` to have passed before execution begins.

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json`
Schema: `orch.phase4.gantt.v1`

## Additional Output

`docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json` — updated from the produced Gantt schedule.

## Skill Bindings

### `milestone-consistency-check`
**Purpose:** Verify milestone due months against task schedule and deliverable due months; confirm every milestone has a verifiable achievement criterion testable at the stated due month.
**Trigger:** After task-to-month assignments are produced; verifies milestone coherence before gate evaluation.
**Output / side-effect:** Consistency check result written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Milestones with non-verifiable criteria must be flagged.
- Milestone due months must be consistent with task completion months.

### `gate-enforcement`
**Purpose:** Evaluate whether a phase gate condition is met, declare pass or failure, and write gate status to Tier 4.
**Trigger:** After `gantt.json` and `milestones_seed.json` are complete and milestone consistency has been verified; evaluates `phase_04_gate`.
**Output / side-effect:** Gate pass/fail result written to `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/`.
**Constitutional constraints:**
- Gate conditions are defined in the workflow and in CLAUDE.md; they must not be weakened.
- Gate failure must be declared explicitly; fabricated completion is a constitutional violation.
- A gate cannot be declared passed without confirming all gate conditions.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** When scheduling conflicts, critical path decisions, or duration adjustments are resolved during n04 execution.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | WP structure and dependency map for task scheduling |
| `docs/tier3_project_instantiation/call_binding/selected_call.json` | tier3 | manually_placed | — | Project duration constraint |
| `docs/tier3_project_instantiation/consortium/roles.json` | tier3 | manually_placed | — | Partner roles for task assignment |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | tier4_phase_output | run_produced | `orch.phase4.gantt.v1` | Phase 4 canonical gate artifact; run_id required |
| `docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json` | tier3_updated | manually_placed | — | Milestone definitions updated from Gantt schedule |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not assign tasks to months beyond the project duration.
- Must not schedule a task start before prerequisite task completion.
- Must not produce milestones without verifiable achievement criteria.
- Must not silently adjust project duration to accommodate an oversized WP structure.
- Must not operate before `phase_03_gate` has passed.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`phase_03_gate` must have passed. Verify before any action is taken.
