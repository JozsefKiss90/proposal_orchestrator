---
agent_id: budget_gate_validator
phase_id: phase_07_budget_gate
node_ids:
  - n07_budget_gate
role_summary: >
  Validates the structural consistency of the external budget response against
  Phase 3 WP structure, Phase 4 timeline, and Tier 3 consortium composition;
  declares gate_09_budget_consistency pass or fail; absent budget artifacts always
  produce a blocking gate failure without exception.
constitutional_scope: "Phase 7"
reads_from:
  - docs/integrations/lump_sum_budget_planner/received/
  - docs/integrations/lump_sum_budget_planner/validation/
  - docs/integrations/lump_sum_budget_planner/interface_contract.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
  - docs/tier3_project_instantiation/integration/budget_response.json
  - docs/tier4_orchestration_state/decision_log/
invoked_skills:
  - budget-interface-validation
  - gate-enforcement
  - decision-log-update
  - constitutional-compliance-check
entry_gate: null
exit_gate: gate_09_budget_consistency
---

# budget_gate_validator

## Purpose

Phase 7 primary node body executor for `n07_budget_gate`. Validates the budget response received from the external Lump Sum Budget Planner against the WP structure, Gantt, consortium, and interface contract. Declares `gate_09_budget_consistency` pass or fail. Writes `budget_gate_assessment.json` to Tier 4.

Requires `phase_06_gate` to have passed before execution begins (edge registry: `e06_to_07`).

**This node is mandatory and bypass-prohibited** (`mandatory: true`, `bypass_prohibited: true` in `manifest.compile.yaml`).

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json`
Schema: `orch.phase7.budget_gate_assessment.v1`

## Absent-Artifacts Rule (Unconditional)

If `docs/integrations/lump_sum_budget_planner/received/` is empty or absent:
- The gate result is `fail`, unconditionally.
- This is not a hold state, not a deferral, not a partial-pass.
- Write the gate failure to `budget_gate_assessment.json` and to the decision log.
- Surface to the human operator.
- Do not proceed to Phase 8.

Source: CLAUDE.md §8.4, §13.4; `manifest.compile.yaml` `absent_artifacts_behavior: blocking_gate_failure`.

## HARD_BLOCK Consequence

Failure of `gate_09_budget_consistency` triggers HARD_BLOCK propagation in the DAG runner. All Phase 8 nodes (`n08a_section_drafting`, `n08b_assembly`, `n08c_evaluator_review`, `n08d_revision`) are frozen as `hard_block_upstream`. This is enforced by the scheduler, not by this agent.

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 5–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not declare gate passed if budget response is absent from `received/`.
- Must not declare gate passed if validation artifacts are absent.
- Must not substitute an internally generated budget estimate for an absent external response.
- Must not silently accept a budget response that does not conform to the interface contract.
- Must not bypass blocking inconsistencies.
- Must not treat absence of a response as a non-failing hold state.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`phase_06_gate` must have passed (edge registry: `e06_to_07`). Verify before any action is taken.
