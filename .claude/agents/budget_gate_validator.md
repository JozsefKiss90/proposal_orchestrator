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

## Skill Bindings

### `budget-interface-validation`
**Purpose:** Validate budget response conformance to the interface contract and structural consistency upon receipt.
**Trigger:** After confirming a budget response exists in `received/`; validates response schema and structural consistency against WP and consortium data.
**Output / side-effect:** Validation artifacts written to `docs/integrations/lump_sum_budget_planner/validation/`; validated response written to `docs/tier3_project_instantiation/integration/budget_response.json`.
**Constitutional constraints:**
- Must not generate or estimate budget figures.
- Must not accept a response that does not conform to the interface contract.
- Must not declare the budget gate passed if blocking inconsistencies exist.
- Must not treat absent response as a non-failing state.

### `gate-enforcement`
**Purpose:** Evaluate whether a phase gate condition is met, declare pass or failure, and write gate status to Tier 4.
**Trigger:** After validation is complete; evaluates `gate_09_budget_consistency`. If `received/` is empty or absent, gate result is `fail` unconditionally.
**Output / side-effect:** Gate pass/fail result written to `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json`.
**Constitutional constraints:**
- Gate conditions are defined in the workflow and in CLAUDE.md; they must not be weakened.
- Gate failure must be declared explicitly; fabricated completion is a constitutional violation.
- A gate cannot be declared passed without confirming all gate conditions.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** For every structural consistency finding, every interface contract discrepancy, and the final gate declaration.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

### `constitutional-compliance-check`
**Purpose:** Verify that the budget gate outcome does not violate any prohibition in CLAUDE.md.
**Trigger:** Before writing the gate result; confirms no constitutional prohibition is triggered by the gate outcome.
**Output / side-effect:** Compliance check written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Must check against CLAUDE.md Section 13 prohibitions as a minimum.
- Constitutional violations must be flagged; they must not be silently resolved.
- CLAUDE.md governs this skill; this skill does not govern CLAUDE.md.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/integrations/lump_sum_budget_planner/received/` | integration_received | manually_placed | — | External budget response; absent = unconditional gate fail |
| `docs/integrations/lump_sum_budget_planner/validation/` | integration_validation | manually_placed | — | Prior validation artifacts |
| `docs/integrations/lump_sum_budget_planner/interface_contract.json` | integration | manually_placed | — | Schema and exchange protocol for budget responses |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | WP structure for structural consistency check |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | tier4_phase_output | run_produced | `orch.phase4.gantt.v1` | Timeline for effort allocation consistency |
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | tier4_phase_output | run_produced | `orch.phase6.implementation_architecture.v1` | Partner roles for cost assignment consistency |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | tier4_phase_output | run_produced | `orch.phase7.budget_gate_assessment.v1` | Phase 7 canonical gate artifact; run_id required |
| `docs/tier3_project_instantiation/integration/budget_response.json` | tier3_integration | manually_placed | — | Validated budget response for downstream consumption |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

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

---

## Output Schema Contracts

### 1. `budget_gate_assessment.json` — Primary Canonical Output

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json`
**Schema ID:** `orch.phase7.budget_gate_assessment.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.phase7.budget_gate_assessment.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after `gate_09_budget_consistency` evaluation |
| `gate_pass_declaration` | string | **yes** | Enum: `pass` or `fail`; must reflect actual validation state — `budget_gate_confirmation_present` predicate verifies this equals `"pass"` for gate satisfaction; **absent budget artifacts always produce `"fail"`** |
| `budget_response_reference` | string | **yes** | File name or path of the budget response file(s) in `docs/integrations/lump_sum_budget_planner/received/` that was validated; if absent = `"ABSENT — gate failure"` |
| `validation_artifact_reference` | string | **yes** | File name or path of the validation artifact in `docs/integrations/lump_sum_budget_planner/validation/`; if absent = `"ABSENT — gate failure"` |
| `wp_coverage_results` | array | **yes** | Coverage check: every `wp_id` from `wp_structure.json` must appear; each entry: `wp_id`, `present_in_budget` (boolean), `budget_line_reference` (optional), `inconsistencies` (array of strings, empty when consistent) |
| `partner_coverage_results` | array | **yes** | Coverage check: every partner in Tier 3 must appear; each entry: `partner_id`, `present_in_budget` (boolean), `budget_line_reference` (optional), `inconsistencies` (array of strings) |
| `blocking_inconsistencies` | array | **yes** | All structural inconsistencies found; must be empty array when `gate_pass_declaration: pass`; each entry: `inconsistency_id`, `description`, `severity` (blocking/non_blocking), `resolution` (resolved/unresolved); `no_blocking_inconsistencies` predicate fails if any entry has `resolution: unresolved` |

### 2. `budget_response.json` — Tier 3 Integration Output (no schema_id in spec)

**Canonical path:** `docs/tier3_project_instantiation/integration/budget_response.json`
**Provenance:** tier3_integration (no schema_id_value defined in spec)

This is a copy/reference of the validated external budget response for downstream traceability. Its content is governed by the interface contract, not by `artifact_schema_specification.yaml`. Written only when a budget response is present and validates. If budget response is absent, this file must not be written with fabricated content.

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements

**Predecessor:** `phase_06_gate` — must have passed. Source: edge `e06_to_07`. Verify via `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/gate_result.json`.

If `phase_06_gate` has not passed, halt immediately. Write `decision_type: constitutional_halt`.

**Entry gate:** none (node `n07_budget_gate` has no `entry_gate` in manifest).

### Exit Gate

**Exit gate:** `gate_09_budget_consistency` — mandatory, bypass-prohibited (`mandatory: true`, `bypass_prohibited: true` in manifest).

Gate conditions (source: `manifest.compile.yaml` gate_09_budget_consistency, `quality_gates.yaml`):
1. `phase_06_gate` passed (`g08_p01`)
2. Non-empty budget response present in `integrations/received/` (`g08_p02`)
3. Validation artifact present in `integrations/validation/` (`g08_p03`)
4. Interface contract conformance confirmed (`g08_p04`)
5. All Phase 3 WPs have corresponding budget entries (`g08_p05`)
6. All consortium partners have corresponding budget allocations (`g08_p06`)
7. No blocking inconsistency unresolved (`g08_p07`)
8. Budget gate assessment written to Tier 4 (`g08_p08`, `g08_p09`)

Gate result: `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/gate_result.json`. Blocking edge on pass: `e07_to_08a` (`n08a_section_drafting`).

### Budget Gate Special Handling — Absent-Artifacts Rule (Unconditional)

**If `docs/integrations/lump_sum_budget_planner/received/` is empty or absent:**
- `gate_pass_declaration` in `budget_gate_assessment.json` **must be `"fail"`** — no other value is valid.
- This is not a hold state. This is not a partial pass. This is not a deferral.
- Write the gate failure to `budget_gate_assessment.json` and to the decision log immediately.
- Surface to the human operator via the fail_action.
- Do not proceed to Phase 8 — `n08a`, `n08b`, `n08c`, `n08d` are all blocked.

Source: CLAUDE.md §8.4, §13.4; `manifest.compile.yaml` `absent_artifacts_behavior: blocking_gate_failure`.

This agent does **not** compute budget figures. This agent does **not** generate, estimate, or approximate any budget number. These are constitutional prohibitions (CLAUDE.md §8.1–8.3). Violations must be halted with `decision_type: constitutional_halt`.

### Failure Protocol

#### Case 1: Gate condition not met — budget artifacts present but inconsistent
- **Halt Phase 8:** Set `gate_pass_declaration: fail`.
- **Write:** `budget_gate_assessment.json` with all `blocking_inconsistencies` populated; `resolution: unresolved` for each unresolved blocking inconsistency.
- **Decision log:** `decision_type: gate_failure`; list each blocking inconsistency with `inconsistency_id`.
- **Must not:** Reclassify a blocking inconsistency as non_blocking to pass the gate.

#### Case 2: Budget response absent (absent-artifacts rule)
- **Unconditional gate failure** — see special handling above.
- **Write:** `budget_gate_assessment.json` with `gate_pass_declaration: fail`; `budget_response_reference: "ABSENT"`.
- **Decision log:** `decision_type: gate_failure`; `absent_artifacts_behavior: blocking_gate_failure`.
- **Must not:** Create a placeholder or estimated budget response.

#### Case 3: Mandatory predecessor gate not passed
- **Halt immediately** if `phase_06_gate` is unmet.
- **Write:** `decision_type: constitutional_halt`.

#### Case 4: Constitutional prohibition triggered
- **Halt** if required to compute, estimate, or generate any budget figure, or to bypass the mandatory gate.
- **Write:** `decision_type: constitutional_halt`; cite CLAUDE.md §8.1, §8.4, or §13.4.

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: budget_gate_validator`, `phase_id: phase_07_budget_gate`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Budget response found and validated | `material_decision` | Response file reference; interface contract conformance result |
| WP coverage check finding (any WP absent from budget) | `material_decision` | WP ID; budget response reference; inconsistency description |
| Partner coverage check finding | `material_decision` | Partner ID; budget response reference; inconsistency |
| Blocking inconsistency identified | `scope_conflict` | Inconsistency ID; description; severity; resolution status |
| Budget response absent | `gate_failure` | `absent_artifacts_behavior: blocking_gate_failure`; CLAUDE.md §8.4 |
| `gate_09_budget_consistency` passes | `gate_pass` | Gate ID; all conditions; budget_response_reference; run_id |
| `gate_09_budget_consistency` fails | `gate_failure` | Gate ID; conditions failed; what is required |
| Budget computation attempted | `constitutional_halt` | CLAUDE.md §8.1; halted action |
| `phase_06_gate` predecessor not passed | `constitutional_halt` | Edge `e06_to_07`; status |
