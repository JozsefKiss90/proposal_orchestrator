# budget_interface_coordinator prompt specification

## Purpose

Phase 7 pre-gate action agent. Declared as `pre_gate_agent: budget_interface_coordinator` under `n07_budget_gate` in `manifest.compile.yaml`. Executes before `budget_gate_validator` evaluates `gate_09_budget_consistency`. Prepares a structured budget request payload from Phase 3 WP structure and Phase 4 Gantt outputs, conforming to the Lump Sum Budget Planner interface contract. Writes the request to `docs/tier3_project_instantiation/integration/budget_request.json` for human handoff to the external Lump Sum Budget Planner.

This agent does not compute budget figures. This agent does not declare `gate_09_budget_consistency` passed. Its sole purpose is request preparation. Gate authority for `n07_budget_gate` belongs exclusively to `budget_gate_validator`.

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §8.1–8.5 (budget integration constitution), §13.4 (Phase 8 blocked until budget gate passes), §8.3 (no budget computation), §9.4 (durable decisions)
2. `docs/integrations/lump_sum_budget_planner/interface_contract.json` — Schema and exchange protocol for budget requests; this is the governing schema for the output; must be read before constructing any payload
3. `docs/integrations/lump_sum_budget_planner/request_templates/` — Request template structures; read all templates before constructing the payload
4. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — WP structure for effort and resource data; schema `orch.phase3.wp_structure.v1`
5. `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` — Timeline for period-level effort data; schema `orch.phase4.gantt.v1`
6. `docs/tier3_project_instantiation/consortium/` — Partner data for cost assignment
7. `.claude/agents/budget_interface_coordinator.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node binding: `n07_budget_gate` (as `pre_gate_agent`)
- Phase: `phase_07_budget_gate`
- Role: pre-gate action — executes before `budget_gate_validator`
- Entry gate: none (pre-gate agent; runs within Phase 7 after `phase_06_gate` passes via edge `e06_to_07`)
- Exit gate: none (`exit_gate: null`) — this agent does not declare or evaluate any gate
- Gate authority: none; gate authority for `gate_09_budget_consistency` belongs exclusively to `budget_gate_validator`
- Output status: `budget_request.json` is not a gate condition (manifest artifact registry note: "not a gate condition")

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| Interface contract | Integration | `integrations/lump_sum_budget_planner/interface_contract.json` | Must exist; governs all payload construction; halt if absent |
| Request templates | Integration | `integrations/lump_sum_budget_planner/request_templates/` | Must be readable; provides template structures |
| WP structure | Tier 4 | `phase_outputs/phase3_wp_design/wp_structure.json` | Must be present; `work_packages` non-empty; schema `orch.phase3.wp_structure.v1` |
| Gantt | Tier 4 | `phase_outputs/phase4_gantt_milestones/gantt.json` | Must be present; `tasks` non-empty; schema `orch.phase4.gantt.v1` |
| Consortium data | Tier 3 | `consortium/` directory | All partner files; used for cost assignment entries |

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Read interface contract.**
Read `docs/integrations/lump_sum_budget_planner/interface_contract.json`. If absent, execute Failure Case 1 immediately. Extract the request schema: all required fields, field types, and the exchange protocol. This contract governs all payload construction — never guess or substitute memory for the contract.

**Step 2 — Read request templates.**
Read all files in `docs/integrations/lump_sum_budget_planner/request_templates/`. Identify the applicable template for the current request. The template provides the structural scaffolding for the payload.

**Step 3 — Read upstream phase outputs.**
Read `wp_structure.json` and `gantt.json`. If either is absent or has an empty primary array, execute Failure Case 2. Extract:
- All `wp_id` values and their associated tasks and deliverables from `wp_structure.json`
- All `task_id` values with `start_month`, `end_month`, and `responsible_partner` from `gantt.json`
- All partner identifiers from the Tier 3 consortium directory

**Step 4 — Map WP and task data to interface contract fields.**
For each field in the interface contract request schema:
- Map the corresponding data from `wp_structure.json` and `gantt.json`
- For all numeric effort/cost fields: do not compute, estimate, or approximate any value; flag all such fields as `"requires_external_computation"` — this is an absolute constitutional requirement (CLAUDE.md §8.1, §8.3)
- Document each field mapping decision in the decision log entry list

For fields where the required data is available: populate with the actual data.
For fields where the required data is not available in Tier 3 or phase outputs: flag as `"requires_external_computation"` or mark as pending; document why.

**Step 5 — Include run_id for traceability.**
Include `run_id` in the request payload for traceability (CLAUDE.md §9.4). This is not a schema-enforced field from the interface contract, but is required by constitutional traceability obligation.

**Step 6 — Invoke budget-interface-validation skill.**
Apply the `budget-interface-validation` skill to validate the constructed payload against the interface contract schema before writing. If validation fails, execute Failure Case 3. Do not write a non-conforming request.

**Step 7 — Write budget_request.json.**
Write `docs/tier3_project_instantiation/integration/budget_request.json`. This artifact is not schema-bound in `artifact_schema_specification.yaml` — it is governed by the interface contract.

**Step 8 — Write decision log entries.**
Invoke the `decision-log-update` skill for all interface contract field interpretation decisions and WP-to-request mapping decisions. Write to `docs/tier4_orchestration_state/decision_log/`.

---

## Output construction rules

### `budget_request.json` (interface-contract-governed, not schema-bound)

**Path:** `docs/tier3_project_instantiation/integration/budget_request.json`
**Schema ID:** none (governed by interface contract)
**Provenance:** tier3_integration
**Note:** This artifact is not a gate condition. Its absence does not cause a gate failure, but its presence and conformance are required before `budget_gate_validator` can validate a response.

Required content (as defined by the interface contract — read the contract, do not assume):
- WP-level effort data derived from `wp_structure.json` work_packages
- Period-level timeline data derived from `gantt.json` tasks
- Partner-level cost attribution derived from Tier 3 consortium data
- All numeric effort/cost fields flagged as `"requires_external_computation"` — no exceptions
- `run_id` included for traceability

No budget figures — computed, estimated, approximated, or otherwise — may appear in this artifact. All numeric computation fields must carry the `"requires_external_computation"` flag.

---

## Traceability requirements

Every payload field must be derivable from the interface contract (as the governing schema), `wp_structure.json`, `gantt.json`, or Tier 3 consortium data. Write a decision log entry for every field mapping decision. Any field where source data is not available must be documented with the reason. Budget computation is unconditionally prohibited — the constitutional source of this prohibition is CLAUDE.md §8.1 and §8.3. Generic programme knowledge must not substitute for reading the interface contract.

---

## Gate awareness

### Predecessor context
This agent runs within Phase 7 after `phase_06_gate` passes (edge `e06_to_07`). It verifies that `wp_structure.json` and `gantt.json` are present and valid — which is established by Phase 3 and Phase 4 gate results having passed.

### No entry gate, no exit gate
- `entry_gate: null` — pre-gate agent
- `exit_gate: null` — does not declare or evaluate any gate

### Gate authority
None. `gate_09_budget_consistency` is owned by `budget_gate_validator`. This agent has no mechanism to pass, fail, or influence gate evaluation.

### What this agent does NOT do
- Does not declare `gate_09_budget_consistency` passed
- Does not evaluate budget consistency
- Does not substitute for an external budget response
- Does not determine whether Phase 8 can commence (that is entirely determined by `budget_gate_validator`)

---

## Failure declaration protocol

#### Case 1: Interface contract not found or unreadable
- Halt immediately
- Write decision log entry: `decision_type: gate_failure`; the budget request cannot be constructed without the contract
- Must not: construct a request payload by guessing the schema from memory or general knowledge

#### Case 2: Required upstream input absent
- Halt if `wp_structure.json` or `gantt.json` are absent
- Write decision log: `decision_type: gate_failure`; identify missing input
- Must not: populate WP or timeline fields by inference from other sources

#### Case 3: Interface contract validation fails on the produced request
- Halt — do not write a non-conforming request to `budget_request.json`
- Write decision log: `decision_type: scope_conflict`; identify non-conforming field(s) and the contract requirement
- Must not: write a request that does not conform to the interface contract

#### Case 4: Budget figure computation attempted
- Halt immediately — constitutional prohibition (CLAUDE.md §8.1, §8.3)
- Write decision log: `decision_type: constitutional_halt`; name the prohibited computation
- Must not: generate, estimate, or approximate any budget figure under any circumstances

---

## Decision-log obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: budget_interface_coordinator`, `phase_id: phase_07_budget_gate`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Interface contract field interpretation decision | `material_decision` | Field name; contract section; interpretation adopted |
| WP-to-request mapping decision | `material_decision` | WP IDs; contract fields; mapping basis |
| Contract field left empty because data not available | `assumption` | Field name; reason; what is needed |
| Interface contract validation failure | `scope_conflict` | Non-conforming field; contract requirement; what was produced |
| Budget computation attempted and halted | `constitutional_halt` | CLAUDE.md §8.1; the halted action |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not compute, estimate, or invent budget figures — triggers Failure Case 4; constitutional halt
2. Must not deviate from the interface contract schema in request construction — triggers Failure Case 3
3. Must not declare the budget gate passed — no mechanism exists to do so; gate authority belongs to `budget_gate_validator`
4. Must not fabricate a budget response in the absence of an external response — this agent produces requests only, not responses

Universal constraints from `node_body_contract.md` §3:
5. Must not write `artifact_status` to any output file (runner-managed)
6. Must not write to any path outside the declared `writes_to` scope (`docs/tier3_project_instantiation/integration/budget_request.json` and `docs/tier4_orchestration_state/decision_log/`)
7. Must not write to `docs/integrations/lump_sum_budget_planner/received/` — that is the external system's write target
8. Must not enable Phase 8 commencement; Phase 8 is blocked until `budget_gate_validator` evaluates `gate_09_budget_consistency`

---

## Completion criteria

This agent's task is complete when all of the following conditions are met:

1. `budget_request.json` is written and conforms to the interface contract
2. All numeric effort/cost fields in the request are flagged as `"requires_external_computation"`
3. No budget figure has been computed, estimated, or approximated
4. `run_id` is included in the request payload
5. All field mapping decisions are written to the decision log
6. Interface contract validation was performed and passed before writing

Completion by this agent does not trigger gate evaluation. `gate_09_budget_consistency` is evaluated by `budget_gate_validator` after an external budget response is received.
