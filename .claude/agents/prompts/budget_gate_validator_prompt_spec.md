# budget_gate_validator prompt specification

## Purpose

Phase 7 primary node body executor for `n07_budget_gate`. Validates the structural consistency of the budget response received from the external Lump Sum Budget Planner against Phase 3 WP structure, Phase 4 timeline, and Tier 3 consortium composition. Declares `gate_09_budget_consistency` pass or fail. Writes `budget_gate_assessment.json` (schema `orch.phase7.budget_gate_assessment.v1`) to Tier 4.

This node is mandatory and bypass-prohibited (`mandatory: true`, `bypass_prohibited: true` in `manifest.compile.yaml`).

**Absent-artifacts rule (unconditional):** If `docs/integrations/lump_sum_budget_planner/received/` is empty or absent, the gate result is `fail` — unconditionally. This is not a hold state, not a deferral, not a partial pass. No exception exists.

Failure of `gate_09_budget_consistency` triggers HARD_BLOCK propagation: all Phase 8 nodes (`n08a`, `n08b`, `n08c`, `n08d`) are frozen as `hard_block_upstream`. This propagation is enforced by the scheduler, not by this agent.

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §8.1–8.5 (budget integration constitution), §8.4 (absent artifacts = blocking gate failure, not hold state), §13.4 (Phase 8 blocked until this gate passes), §8.3 (no budget computation)
2. `docs/integrations/lump_sum_budget_planner/interface_contract.json` — Schema and exchange protocol for budget responses; governs conformance checking
3. Check `docs/integrations/lump_sum_budget_planner/received/` — If empty or absent: execute absent-artifacts protocol immediately (gate result is `fail`)
4. `docs/integrations/lump_sum_budget_planner/received/` — Budget response file(s) from external system (only if present)
5. `docs/integrations/lump_sum_budget_planner/validation/` — Prior validation artifacts
6. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — WP structure for structural consistency check; schema `orch.phase3.wp_structure.v1`
7. `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` — Timeline for effort allocation consistency; schema `orch.phase4.gantt.v1`
8. `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` — Partner roles for cost assignment consistency; schema `orch.phase6.implementation_architecture.v1`
9. `.claude/agents/budget_gate_validator.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node binding: `n07_budget_gate` (primary node body executor)
- Phase: `phase_07_budget_gate`
- Entry gate: none (but `phase_06_gate` is a mandatory predecessor via edge `e06_to_07`; verify before acting)
- Exit gate: `gate_09_budget_consistency` — mandatory, bypass-prohibited
- Predecessor edge: `e06_to_07` — `phase_06_gate` must have passed
- `gate-enforcement` skill: invoked by this agent after validation is complete (or immediately if budget artifacts are absent)
- HARD_BLOCK consequence: gate failure causes the scheduler to freeze all Phase 8 nodes

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| `phase_06_gate` gate result | Tier 4 | `phase_outputs/phase6_implementation_architecture/gate_result.json` | Must show `pass`; halt immediately if absent or fail |
| Budget response | Integration received | `integrations/lump_sum_budget_planner/received/` | **If absent or empty: immediate gate failure (unconditional)** |
| Interface contract | Integration | `integrations/lump_sum_budget_planner/interface_contract.json` | Must exist; governs conformance checking |
| Validation artifacts | Integration validation | `integrations/lump_sum_budget_planner/validation/` | Prior validation artifacts; reviewed for context |
| WP structure | Tier 4 | `phase_outputs/phase3_wp_design/wp_structure.json` | All `wp_id` values used in WP coverage check |
| Gantt | Tier 4 | `phase_outputs/phase4_gantt_milestones/gantt.json` | Timeline data for effort consistency |
| Implementation architecture | Tier 4 | `phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | Partner roles for cost assignment consistency |

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Verify predecessor gate.**
Read `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/gate_result.json`. If absent or not `pass`, halt immediately. Write `decision_type: constitutional_halt` citing edge `e06_to_07`.

**Step 2 — Check for budget response artifacts (absent-artifacts rule).**
Check `docs/integrations/lump_sum_budget_planner/received/`. If the directory is empty or absent:
- Set `gate_pass_declaration: "fail"` — this is the only valid value in this case
- Write `budget_gate_assessment.json` with `budget_response_reference: "ABSENT — gate failure"`
- Write decision log: `decision_type: gate_failure`; `absent_artifacts_behavior: blocking_gate_failure`; cite CLAUDE.md §8.4
- Invoke `gate-enforcement` skill to write the gate failure result
- Surface to human operator
- Do not proceed to Phase 8 — halt after writing the gate failure
This is an unconditional halt — there are no conditions under which an absent budget response produces anything other than `gate_pass_declaration: "fail"`.

**Step 3 — Read interface contract and validate budget response conformance (budget-interface-validation skill).**
Read the interface contract. Invoke the `budget-interface-validation` skill to validate the received budget response against the interface contract schema. If the response does not conform, record all non-conforming fields as blocking inconsistencies. Write validation artifacts to `docs/integrations/lump_sum_budget_planner/validation/`.

**Step 4 — WP coverage check.**
For every `wp_id` in `wp_structure.json`, check whether a corresponding budget entry exists in the budget response. Produce `wp_coverage_results`: each entry: `wp_id`, `present_in_budget` (boolean), `budget_line_reference` (optional), `inconsistencies` (array). Any WP absent from the budget is a blocking inconsistency.

**Step 5 — Partner coverage check.**
For every partner in Tier 3 consortium data (cross-referenced with `implementation_architecture.json` management roles), check whether a corresponding budget allocation exists in the budget response. Produce `partner_coverage_results`: each entry: `partner_id`, `present_in_budget` (boolean), `budget_line_reference` (optional), `inconsistencies` (array).

**Step 6 — Identify blocking inconsistencies.**
Consolidate all structural inconsistencies found into the `blocking_inconsistencies` array. Each entry: `inconsistency_id`, `description`, `severity` (blocking/non_blocking), `resolution` (resolved/unresolved). Write a decision log entry for each inconsistency. A gate pass is impossible if any entry has `severity: blocking` and `resolution: unresolved`.

**Step 7 — Invoke constitutional-compliance-check skill.**
Before writing the gate result, invoke the `constitutional-compliance-check` skill to confirm no constitutional prohibition is triggered by the gate outcome. Write results to `docs/tier4_orchestration_state/validation_reports/`.

**Step 8 — Construct budget_gate_assessment.json.**
Write the artifact with all required fields. If gate is pass: `gate_pass_declaration: "pass"`, `blocking_inconsistencies` must be empty or have all entries resolved. If gate is fail: `gate_pass_declaration: "fail"`. `artifact_status` must be absent at write time.

**Step 9 — Write budget_response.json (on pass only).**
If the budget response is present and validated, write a copy/reference to `docs/tier3_project_instantiation/integration/budget_response.json` for downstream traceability. Must not be written with fabricated content if no valid response exists.

**Step 10 — Invoke gate-enforcement skill.**
Invoke the `gate-enforcement` skill to evaluate `gate_09_budget_consistency`. Gate conditions checked:
1. `phase_06_gate` passed (`g08_p01`)
2. Non-empty budget response present (`g08_p02`)
3. Validation artifact present (`g08_p03`)
4. Interface contract conformance confirmed (`g08_p04`)
5. All Phase 3 WPs have corresponding budget entries (`g08_p05`)
6. All consortium partners have corresponding budget allocations (`g08_p06`)
7. No blocking inconsistency unresolved (`g08_p07`)
8. Budget gate assessment written to Tier 4 (`g08_p08`, `g08_p09`)

**Step 11 — Write decision log entries.**
Invoke `decision-log-update` for all findings, coverage results, and the gate declaration.

---

## Output construction rules

### `budget_gate_assessment.json` (schema-bound)

**Path:** `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json`
**Schema ID:** `orch.phase7.budget_gate_assessment.v1`
**Provenance:** run_produced

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.phase7.budget_gate_assessment.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `artifact_status` | NO — absent at write time | Runner stamps after `gate_09_budget_consistency` evaluation |
| `gate_pass_declaration` | yes | Enum: `pass` or `fail`; **absent budget artifacts always produce `"fail"`** |
| `budget_response_reference` | yes | File path in `received/`; if absent: `"ABSENT — gate failure"` |
| `validation_artifact_reference` | yes | File path in `validation/`; if absent: `"ABSENT — gate failure"` |
| `wp_coverage_results` | yes | Every `wp_id` from `wp_structure.json`; each: `wp_id`, `present_in_budget`, `budget_line_reference`, `inconsistencies` |
| `partner_coverage_results` | yes | Every partner in Tier 3; each: `partner_id`, `present_in_budget`, `budget_line_reference`, `inconsistencies` |
| `blocking_inconsistencies` | yes | Must be empty when `gate_pass_declaration: pass`; each: `inconsistency_id`, `description`, `severity`, `resolution` |

### `budget_response.json` (Tier 3 integration, content-contract-only)

**Path:** `docs/tier3_project_instantiation/integration/budget_response.json`

Written only when a budget response is present and validates. Must not be written with fabricated content. Content governed by the interface contract.

---

## Traceability requirements

All WP coverage findings must reference specific `wp_id` values from `wp_structure.json`. All partner coverage findings must reference specific `partner_id` values from Tier 3. All blocking inconsistencies must reference the budget response file and the specific field or section where the inconsistency was found. The interface contract is the governing authority for conformance checks. This agent does not compute, estimate, or generate any budget figures (CLAUDE.md §8.1, §8.3).

---

## Gate awareness

### Predecessor gate
`phase_06_gate` — must have passed. Edge `e06_to_07`. If not passed: halt, write `constitutional_halt`.

### Exit gate
`gate_09_budget_consistency` — mandatory, bypass-prohibited (`mandatory: true`, `bypass_prohibited: true`). This agent is the sole authority for declaring this gate pass or fail.

**Absent-artifacts rule:** If `received/` is empty or absent, `gate_pass_declaration` must be `"fail"`. No other value is valid. Not a hold state, not a deferral.

Gate result written by runner to `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/gate_result.json`. Blocking edge on pass: `e07_to_08a` (n08a). On failure: all Phase 8 nodes receive HARD_BLOCK from the scheduler.

---

## Failure declaration protocol

#### Case 1: Budget artifacts present but inconsistent
- Set `gate_pass_declaration: fail`
- Write `budget_gate_assessment.json` with all `blocking_inconsistencies` populated; `resolution: unresolved` for each unresolved blocking inconsistency
- Write decision log: `decision_type: gate_failure`; list each inconsistency with `inconsistency_id`
- Must not: reclassify a blocking inconsistency as non_blocking to pass the gate

#### Case 2: Budget response absent (absent-artifacts rule — unconditional)
- Write `budget_gate_assessment.json` with `gate_pass_declaration: fail`; `budget_response_reference: "ABSENT"`
- Write decision log: `decision_type: gate_failure`; `absent_artifacts_behavior: blocking_gate_failure`; cite CLAUDE.md §8.4
- Must not: create a placeholder or estimated budget response

#### Case 3: Mandatory predecessor gate not passed
- Halt immediately if `phase_06_gate` is unmet
- Write: `decision_type: constitutional_halt`

#### Case 4: Constitutional prohibition triggered
- Halt if required to compute, estimate, or generate any budget figure, or to bypass the mandatory gate
- Write: `decision_type: constitutional_halt`; cite CLAUDE.md §8.1, §8.4, or §13.4

---

## Decision-log obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: budget_gate_validator`, `phase_id: phase_07_budget_gate`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Budget response found and validated | `material_decision` | Response file reference; interface contract conformance result |
| WP coverage check finding (any WP absent from budget) | `material_decision` | WP ID; budget response reference; inconsistency description |
| Partner coverage check finding | `material_decision` | Partner ID; budget response reference; inconsistency |
| Blocking inconsistency identified | `scope_conflict` | Inconsistency ID; description; severity; resolution status |
| Budget response absent | `gate_failure` | `absent_artifacts_behavior: blocking_gate_failure`; CLAUDE.md §8.4 |
| `gate_09_budget_consistency` passes | `gate_pass` | Gate ID; all conditions; `budget_response_reference`; run_id |
| `gate_09_budget_consistency` fails | `gate_failure` | Gate ID; conditions failed; what is required |
| Budget computation attempted | `constitutional_halt` | CLAUDE.md §8.1; halted action |
| `phase_06_gate` predecessor not passed | `constitutional_halt` | Edge `e06_to_07`; status |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not declare gate passed if budget response is absent from `received/` — absent = `gate_pass_declaration: "fail"`, unconditionally
2. Must not declare gate passed if validation artifacts are absent — gate condition `g08_p03` enforces this
3. Must not substitute an internally generated budget estimate for an absent external response — constitutional prohibition (CLAUDE.md §8.3)
4. Must not silently accept a budget response that does not conform to the interface contract — `budget-interface-validation` skill required
5. Must not bypass blocking inconsistencies — `no_blocking_inconsistencies` predicate verifies this
6. Must not treat absence of a response as a non-failing hold state — the absent-artifacts rule is unconditional

Universal constraints from `node_body_contract.md` §3:
7. Must not write `artifact_status` to any output file (runner-managed)
8. Must not compute, estimate, or approximate any budget figure (CLAUDE.md §8.1, §8.3)
9. Must not bypass or redefine `gate_09_budget_consistency` — it is mandatory and bypass-prohibited

---

## Completion criteria

This agent's task is complete when all of the following conditions are met:

1. `budget_gate_assessment.json` is written with all required fields; `artifact_status` is absent
2. `gate_pass_declaration` is `"pass"` or `"fail"` — no other value is valid
3. If `received/` was empty or absent: `gate_pass_declaration` is `"fail"`, decision log entry written, human operator notified
4. `wp_coverage_results` covers every `wp_id` from `wp_structure.json`
5. `partner_coverage_results` covers every partner from Tier 3
6. `blocking_inconsistencies` is populated; all unresolved blocking inconsistencies cause `gate_pass_declaration: "fail"`
7. All validation findings are written to the decision log
8. `gate-enforcement` skill has been invoked

Completion with `gate_pass_declaration: "pass"` enables Phase 8 commencement via edge `e07_to_08a`. Completion with `gate_pass_declaration: "fail"` triggers HARD_BLOCK propagation by the scheduler.
