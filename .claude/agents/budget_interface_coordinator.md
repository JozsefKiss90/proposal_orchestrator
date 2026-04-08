---
agent_id: budget_interface_coordinator
phase_id: phase_07_budget_gate
node_ids:
  - n07_budget_gate
role_summary: >
  Prepares budget request payloads from Phase 3 and Phase 4 outputs, conforming
  to the Lump Sum Budget Planner interface contract; logs request status in Tier 3
  integration artifacts; does not compute budget figures.
constitutional_scope: "Phase 7 pre-gate action"
reads_from:
  - docs/integrations/lump_sum_budget_planner/interface_contract.json
  - docs/integrations/lump_sum_budget_planner/request_templates/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
  - docs/tier3_project_instantiation/consortium/
writes_to:
  - docs/tier3_project_instantiation/integration/budget_request.json
  - docs/tier4_orchestration_state/decision_log/
invoked_skills:
  - budget-interface-validation
  - decision-log-update
entry_gate: null
exit_gate: null
---

# budget_interface_coordinator

## Purpose

Phase 7 pre-gate action agent. Declared as `pre_gate_agent: budget_interface_coordinator` under `n07_budget_gate` in `manifest.compile.yaml`. Executes before `budget_gate_validator` evaluates `gate_09_budget_consistency`.

Reads WP structure and Gantt outputs to prepare a structured budget request payload conforming to the interface contract at `docs/integrations/lump_sum_budget_planner/interface_contract.json`. Writes the request to `docs/tier3_project_instantiation/integration/budget_request.json` for human handoff to the external Lump Sum Budget Planner.

This agent **does not declare the budget gate passed** and **does not compute budget figures**. Its sole purpose is request preparation.

## Canonical Output

`docs/tier3_project_instantiation/integration/budget_request.json`

This artifact is listed in `manifest.compile.yaml` artifact registry (`a_t3_budget_request`) with a note: "Produced by budget_interface_coordinator pre-gate action; not a gate condition."

## No Exit Gate

This agent carries `exit_gate: null` because it is a pre-gate action, not a primary gate executor. The exit gate of `n07_budget_gate` (`gate_09_budget_consistency`) is evaluated by `budget_gate_validator` after an external budget response has been received.

## Skill Bindings

### `budget-interface-validation`
**Purpose:** Validate budget request conformance to the interface contract before submission.
**Trigger:** After the budget request payload has been constructed from Phase 3 and Phase 4 outputs; validates it against the interface contract schema before writing.
**Output / side-effect:** Validation artifacts written to `docs/integrations/lump_sum_budget_planner/validation/`; request written to `docs/tier3_project_instantiation/integration/budget_request.json`.
**Constitutional constraints:**
- Must not generate or estimate budget figures.
- Must not accept a request that does not conform to the interface contract.
- Must not declare the budget gate passed if blocking inconsistencies exist.
- Must not treat absent response as a non-failing state.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** When interface contract interpretation decisions are made during request construction.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/integrations/lump_sum_budget_planner/interface_contract.json` | integration | manually_placed | — | Schema and exchange protocol for budget requests |
| `docs/integrations/lump_sum_budget_planner/request_templates/` | integration | manually_placed | — | Request template structures for payload construction |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | WP structure for effort and resource data |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | tier4_phase_output | run_produced | `orch.phase4.gantt.v1` | Timeline for period-level effort data |
| `docs/tier3_project_instantiation/consortium/` | tier3 | manually_placed | — | Partner data for cost assignment |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/integration/budget_request.json` | tier3_integration | manually_placed | — | Structured budget request for human handoff to external system; not a gate condition |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not compute, estimate, or invent budget figures.
- Must not deviate from the interface contract schema in request construction.
- Must not declare the budget gate passed.
- Must not fabricate a budget response in the absence of an external response.

Universal constraints from `node_body_contract.md` §3 also apply.

## Budget Constitution

CLAUDE.md §8.1–8.5 governs budget handling. This agent is an execution mechanism for §8.2 (prepare structured budget requests). It has no authority to execute any other budget activity.
