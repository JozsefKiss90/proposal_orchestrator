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

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 5–9 of `agent-generation-plan.md`.

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
