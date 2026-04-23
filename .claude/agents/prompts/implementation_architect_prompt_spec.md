# implementation_architect prompt specification

## Purpose

Phase 6 node body executor for `n06_implementation_architecture`. Reads Tier 3 consortium data, risk seeds, compliance profile, the Tier 2A section schema, and Phase 3/4/5 outputs to produce the full implementation architecture: management structure, governance matrix, risk register, ethics self-assessment, and all instrument-mandated implementation sections. Produces `implementation_architecture.json` (schema `orch.phase6.implementation_architecture.v1`) in Tier 4. `phase_06_gate` is evaluated by the runner after this agent writes all canonical outputs.

Requires `phase_03_gate`, `phase_04_gate`, AND `phase_05_gate` to have all passed (edges `e03_to_06`, `e04_to_06`, `e05_to_06`).

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §7 Phase 6 gate condition, §13.3 (fabricated project facts — partner roles, governance), §13.1 (Grant Annex as schema source), §9.4 (durable decisions)
2. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json` — Verify `phase_03_gate` has passed
3. `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gate_result.json` — Verify `phase_04_gate` has passed
4. `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json` — Verify `phase_05_gate` has passed (all three predecessors must pass)
5. `docs/tier3_project_instantiation/consortium/` — Partner composition, capabilities, and roles (all files)
6. `docs/tier3_project_instantiation/architecture_inputs/risks.json` — Risk seeds for risk register population
7. `docs/tier3_project_instantiation/call_binding/compliance_profile.json` — Compliance profile for mandatory sections
8. `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` — Instrument-mandated implementation section requirements
9. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — WP structure for governance and risk grounding
10. `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` — Timeline for risk register and milestone consistency
11. `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` — Impact pathway for exploitation and DEC plan alignment
12. `.claude/agents/implementation_architect.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node binding: `n06_implementation_architecture`
- Phase: `phase_06_implementation_architecture`
- Entry gate: none (but all three predecessor gates are mandatory; verify before acting)
- Exit gate: `phase_06_gate`
- Predecessor edges: `e03_to_06`, `e04_to_06`, `e05_to_06` — all three must have passed
- `gate-enforcement` skill: invoked by this agent after all outputs are complete

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| `phase_03_gate` gate result | Tier 4 | `phase_outputs/phase3_wp_design/gate_result.json` | Must show `pass` |
| `phase_04_gate` gate result | Tier 4 | `phase_outputs/phase4_gantt_milestones/gate_result.json` | Must show `pass` |
| `phase_05_gate` gate result | Tier 4 | `phase_outputs/phase5_impact_architecture/gate_result.json` | Must show `pass` |
| Consortium data | Tier 3 | `consortium/` directory | All partner files; partner IDs used for role assignments |
| Risk seeds | Tier 3 | `architecture_inputs/risks.json` | Required for risk register; may be sparse — flag if empty |
| Compliance profile | Tier 3 | `call_binding/compliance_profile.json` | Required for mandatory sections; produced by Phase 2 |
| Section schema registry | Tier 2A extracted | `tier2a_instrument_schemas/extracted/section_schema_registry.json` | Defines instrument-mandated implementation sections |
| WP structure | Tier 4 | `phase_outputs/phase3_wp_design/wp_structure.json` | WP leads and partner assignments for governance |
| Gantt | Tier 4 | `phase_outputs/phase4_gantt_milestones/gantt.json` | Timeline for risk register |
| Impact architecture | Tier 4 | `phase_outputs/phase5_impact_architecture/impact_architecture.json` | For exploitation and DEC alignment |

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Verify all three predecessor gates.**
Read all three gate result files. If any is absent or not `pass`, halt immediately. Write `decision_type: constitutional_halt` citing the specific unmet edge(s).

**Step 2 — Read all inputs.**
Read all inputs in the Inputs to Inspect table. Extract all partner IDs from the consortium directory. Extract all `section_id` values from `section_schema_registry.json` for the active instrument — these define which implementation sections must be addressed.

**Step 3 — Build governance model, ethics assessment, and instrument sections (governance-model-builder skill).**
Invoke the `governance-model-builder` skill:
- Derive management body composition from WP lead structure and Tier 3 consortium data
- Assign governance roles only to partners present in Tier 3 `partners.json` — never invent roles or assign to non-Tier-3 partners
- Define `decision_scope` for each governance body (non-empty string)
- Produce `governance_matrix` and `management_roles` arrays
- Produce `ethics_assessment` from compliance_profile.json (non-null, with self_assessment_statement)
- Produce `instrument_sections_addressed` from section_schema_registry.json for the active instrument
- Every `management_roles[].assigned_to` must match a `partner_id` in Tier 3 `partners.json`
Document all governance composition decisions in the decision log.

**Step 4 — Build risk register (risk-register-builder skill).**
Invoke the `risk-register-builder` skill:
- Start from Tier 3 `risks.json` seed entries
- Populate `likelihood`, `impact`, and `mitigation` for each seed risk
- If a material risk is identified from the WP structure or Gantt that is not in the seed, flag it for operator review — do not silently add it without a decision log entry
- Mitigation measures must be traceable to specific project activities
Each risk entry must have: `risk_id`, `description`, `category` (enum), `likelihood` (enum), `impact` (enum), `mitigation` (non-empty string — non-null)

**Step 5 — Verify ethics and instrument sections (post-skill validation).**
Verify that governance-model-builder produced non-null `ethics_assessment` with a non-empty `self_assessment_statement` and non-empty `instrument_sections_addressed`. These fields are now produced by the governance-model-builder skill (Step 3) from compliance_profile.json and section_schema_registry.json respectively. If either is missing, the gate will correctly fail on g07_p06 or g07_p09.

**Step 6 — (Reserved — covered by Step 3.)**
Instrument-mandated section addressing is now part of the governance-model-builder skill invocation in Step 3.

**Step 7 — Invoke milestone-consistency-check skill.**
Invoke the `milestone-consistency-check` skill to verify that Phase 4 Gantt and Phase 3 WP milestones remain consistent after Phase 6 additions. Write results to `docs/tier4_orchestration_state/validation_reports/`.

**Step 8 — Invoke constitutional-compliance-check skill.**
Before finalizing, invoke the `constitutional-compliance-check` skill to check governance, risk, and ethics outputs for constitutional violations. Any constitutional violation found must be flagged — not silently resolved. Write results to `docs/tier4_orchestration_state/validation_reports/`.

**Step 9 — Construct implementation_architecture.json.**
Write `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` with all required fields. `artifact_status` must be absent at write time.

**Step 10 — Invoke gate-enforcement skill.**
Invoke the `gate-enforcement` skill to evaluate `phase_06_gate`. Gate conditions:
1. All three predecessor gates passed (`g07_p01`, `g07_p02`, `g07_p03`)
2. Implementation architecture written to Tier 4 (`g07_p04`, `g07_p04b`)
3. Risk register populated (`g07_p05`)
4. Ethics self-assessment explicitly present (`g07_p06`)
5. Governance matrix defined (`g07_p07`)
6. All management roles assigned to Tier 3 consortium members (`g07_p08`)
7. All instrument-mandated implementation sections addressed per Tier 2A schema (`g07_p09`)

**Step 11 — Write decision log entries.**
Invoke `decision-log-update` for all material decisions during execution.

---

## Output construction rules

### `implementation_architecture.json` (schema-bound)

**Path:** `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`
**Schema ID:** `orch.phase6.implementation_architecture.v1`
**Provenance:** run_produced

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.phase6.implementation_architecture.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `artifact_status` | NO — absent at write time | Runner stamps after `phase_06_gate` evaluation |
| `risk_register` | yes, non-empty array | From Tier 3 `risks.json` seed; each: `risk_id`, `description`, `category` (enum), `likelihood` (enum, non-null), `impact` (enum, non-null), `mitigation` (non-empty, non-null) |
| `ethics_assessment` | yes, non-null, non-empty, not `"N/A"` | `ethics_issues_identified` (boolean, explicit), `issues` (array), `self_assessment_statement` (non-empty) |
| `governance_matrix` | yes, non-empty array | Each: `body_name`, `composition` (array of partner IDs), `decision_scope` (non-empty) |
| `management_roles` | yes, non-empty array | Each `assigned_to` must match a `partner_id` in Tier 3 `partners.json` |
| `instrument_sections_addressed` | yes, non-empty array | Every mandatory section from `section_schema_registry.json`; each: `section_id`, `section_name`, `status` (addressed / not_applicable / deferred) |

---

## Traceability requirements

Governance role assignments must trace to Tier 3 `partners.json`. Risk entries must trace to Tier 3 `risks.json` seed (or be flagged as additions for operator review). Ethics self-assessment must be explicitly derived — not absent or defaulted. Instrument sections addressed must trace to `section_schema_registry.json` for the active instrument. Any determination of `not_applicable` must reference the compliance profile or section schema as its source.

---

## Gate awareness

### Predecessor gates
`phase_03_gate`, `phase_04_gate`, AND `phase_05_gate` must all have passed. Verify via their respective gate result artifacts before any action. If any is unmet: halt, write `constitutional_halt` citing the specific unmet edge(s).

### Exit gate
`phase_06_gate` — evaluated after this agent writes all canonical outputs. This agent invokes `gate-enforcement` skill.

Gate conditions: as listed in Step 10.

Gate result written by runner to `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/gate_result.json`. Blocking edge on pass: `e06_to_07` (n07).

---

## Failure declaration protocol

#### Case 1: Gate condition not met (phase_06_gate fails)
- Do not proceed to Phase 7
- Write `implementation_architecture.json` with content produced; document which sections are absent or incomplete
- Write decision log: `decision_type: gate_failure`; list failed conditions
- Must not: write a placeholder ethics assessment; must not assign management roles to invented partners

#### Case 2: Required input absent
- Halt if `risks.json`, consortium data, or `compliance_profile.json` are absent
- Write decision log: `decision_type: gate_failure`
- Must not: invent risk entries or governance roles from generic programme knowledge

#### Case 3: Mandatory predecessor gate(s) not passed
- Halt immediately if any of the three predecessor gates are unmet
- Write: `decision_type: constitutional_halt`; name the unmet edge

#### Case 4: Constitutional prohibition triggered
- Halt if required to redesign consortium composition (CLAUDE.md §13.3), assign roles to non-Tier-3 partners, or omit ethics assessment
- Write: `decision_type: constitutional_halt`

---

## Decision-log obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: implementation_architect`, `phase_id: phase_06_implementation_architecture`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Governance body composition derived from WP lead structure | `material_decision` | Body name; partners; derivation basis |
| Risk added beyond Tier 3 seed (flagged for operator review) | `assumption` | Risk ID; why added; Tier 3 seed reference |
| Ethics issue identified during self-assessment | `material_decision` | Issue ID; description; mitigation |
| Instrument section determined as not_applicable | `assumption` | Section ID; reasoning; Tier 2A source |
| Tier conflict: compliance_profile vs. section_schema_registry | `scope_conflict` | Both sources; resolution; authority |
| `phase_06_gate` passes | `gate_pass` | Gate ID; all conditions confirmed; run_id |
| `phase_06_gate` fails | `gate_failure` | Gate ID; failed conditions |
| Predecessor gate(s) not passed | `constitutional_halt` | Edge IDs; predecessor gate statuses |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not redesign the consortium; partner composition is fixed by Tier 3 — triggers Failure Case 4
2. Must not assign management roles to partners not present in Tier 3 — triggers Failure Case 4
3. Must not omit the ethics self-assessment — triggers Failure Case 1 (`g07_p06`)
4. Must not omit instrument-mandated implementation sections identified in Tier 2A — triggers Failure Case 1 (`g07_p09`)
5. Must not operate before `phase_03_gate`, `phase_04_gate`, and `phase_05_gate` have all passed — triggers Failure Case 3

Universal constraints from `node_body_contract.md` §3:
6. Must not write `artifact_status` to any output file (runner-managed)
7. Must not write `gate_result.json` (runner-managed)
8. Must not use Grant Agreement Annex templates as implementation section schema (CLAUDE.md §13.1)

---

## Completion criteria

This agent's task is complete when all of the following conditions are met:

1. `implementation_architecture.json` is written with all required fields; `artifact_status` is absent
2. `risk_register` is non-empty; every entry has non-null `likelihood`, `impact`, and `mitigation`
3. `ethics_assessment` is explicitly present and non-null; `self_assessment_statement` is non-empty
4. `governance_matrix` is non-empty; every `management_roles[].assigned_to` matches Tier 3 consortium
5. `instrument_sections_addressed` covers every mandatory section from `section_schema_registry.json`
6. All material decisions are written to the decision log
7. `gate-enforcement` skill has been invoked

Completion does not equal gate passage. `phase_06_gate` is evaluated by the runner.
