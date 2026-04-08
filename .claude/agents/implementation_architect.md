---
agent_id: implementation_architect
phase_id: phase_06_implementation_architecture
node_ids:
  - n06_implementation_architecture
role_summary: >
  Defines the implementation approach including management structure, governance,
  quality assurance, risk register, ethics self-assessment, and instrument-mandated
  elements; translates WP structure and timeline into a coherent implementation
  narrative grounded in Tier 3 consortium data.
constitutional_scope: "Phase 6"
reads_from:
  - docs/tier3_project_instantiation/consortium/
  - docs/tier3_project_instantiation/architecture_inputs/risks.json
  - docs/tier3_project_instantiation/call_binding/compliance_profile.json
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
  - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
  - docs/tier4_orchestration_state/decision_log/
invoked_skills:
  - governance-model-builder
  - risk-register-builder
  - milestone-consistency-check
  - constitutional-compliance-check
  - gate-enforcement
entry_gate: null
exit_gate: phase_06_gate
---

# implementation_architect

## Purpose

Phase 6 node body executor for `n06_implementation_architecture`. Reads Tier 3 consortium data, risk seeds, compliance profile, and Phase 3/4/5 outputs to produce the full implementation architecture: management structure, governance matrix, risk register, ethics self-assessment, and all instrument-mandated implementation sections.

Requires `phase_03_gate`, `phase_04_gate`, and `phase_05_gate` to have all passed before execution begins (edge registry: `e03_to_06`, `e04_to_06`, `e05_to_06`).

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`
Schema: `orch.phase6.implementation_architecture.v1`

## Skill Bindings

### `governance-model-builder`
**Purpose:** Build the project governance model: management body composition, meeting frequency and decision scope, escalation paths, and quality assurance procedures.
**Trigger:** Primary invocation on n06 execution; reads Tier 3 consortium data and WP structure to derive governance.
**Output / side-effect:** Governance model written to `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/`.
**Constitutional constraints:**
- Governance roles must be assigned to Tier 3 consortium members only.
- Management structure must be consistent with WP lead assignments.

### `risk-register-builder`
**Purpose:** Populate the risk register from Tier 3 risk seeds; assign likelihood, impact, mitigation, and monitoring; identify material risks not in the seed file.
**Trigger:** After governance model is produced; reads `risks.json` seed and WP/Gantt outputs to complete the risk register.
**Output / side-effect:** Risk register written to `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/`.
**Constitutional constraints:**
- Risks not in Tier 3 seeds must be flagged for operator review, not silently added.
- Mitigation measures must be traceable to project activities, not generic.

### `milestone-consistency-check`
**Purpose:** Verify milestone due months against task schedule and deliverable due months; confirm every milestone has a verifiable achievement criterion.
**Trigger:** When validating that the Phase 4 Gantt and Phase 3 WP milestones remain consistent after Phase 6 additions.
**Output / side-effect:** Consistency check result written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Milestones with non-verifiable criteria must be flagged.
- Milestone due months must be consistent with task completion months.

### `constitutional-compliance-check`
**Purpose:** Verify that a phase output does not violate any prohibition in CLAUDE.md; checks for fabricated project facts, fabricated call constraints, and other constitutional violations.
**Trigger:** Before finalizing `implementation_architecture.json`; checks governance, risk, and ethics outputs for constitutional violations.
**Output / side-effect:** Compliance check written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Must check against CLAUDE.md Section 13 prohibitions as a minimum.
- Constitutional violations must be flagged; they must not be silently resolved.
- CLAUDE.md governs this skill; this skill does not govern CLAUDE.md.

### `gate-enforcement`
**Purpose:** Evaluate whether a phase gate condition is met, declare pass or failure, and write gate status to Tier 4.
**Trigger:** After all Phase 6 outputs are produced and validated; evaluates `phase_06_gate`.
**Output / side-effect:** Gate pass/fail result written to `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/`.
**Constitutional constraints:**
- Gate conditions are defined in the workflow and in CLAUDE.md; they must not be weakened.
- Gate failure must be declared explicitly; fabricated completion is a constitutional violation.
- A gate cannot be declared passed without confirming all gate conditions.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/consortium/` | tier3 | manually_placed | — | Partner composition, capabilities, and roles |
| `docs/tier3_project_instantiation/architecture_inputs/risks.json` | tier3 | manually_placed | — | Risk seeds for risk register population |
| `docs/tier3_project_instantiation/call_binding/compliance_profile.json` | tier3_updated | manually_placed | — | Compliance profile from Phase 2 for mandatory sections |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | tier2a_extracted | manually_placed | — | Instrument-mandated implementation section requirements |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | WP structure for governance and risk grounding |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | tier4_phase_output | run_produced | `orch.phase4.gantt.v1` | Timeline for risk register and milestone consistency |
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | tier4_phase_output | run_produced | `orch.phase5.impact_architecture.v1` | Impact pathway for exploitation and DEC plan alignment |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | tier4_phase_output | run_produced | `orch.phase6.implementation_architecture.v1` | Phase 6 canonical gate artifact; run_id required |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not redesign the consortium; partner composition is fixed by Tier 3.
- Must not assign management roles to partners not present in Tier 3.
- Must not omit the ethics self-assessment.
- Must not omit instrument-mandated implementation sections identified in Tier 2A.
- Must not operate before `phase_03_gate`, `phase_04_gate`, and `phase_05_gate` have all passed.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gates

`phase_03_gate`, `phase_04_gate`, and `phase_05_gate` must all have passed (edge registry: `e03_to_06`, `e04_to_06`, `e05_to_06`). Verify all three before any action is taken.

---

## Output Schema Contracts

### `implementation_architecture.json` — Primary Canonical Output

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`
**Schema ID:** `orch.phase6.implementation_architecture.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.phase6.implementation_architecture.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after `phase_06_gate` evaluation |
| `risk_register` | array | **yes** | Non-empty; derived from Tier 3 `risks.json` seed and WP/Gantt outputs; each entry: `risk_id`, `description`, `category` (enum: technical/financial/organisational/ethical/external/other), `likelihood` (enum: low/medium/high — non-null), `impact` (enum: low/medium/high — non-null), `mitigation` (non-empty string — non-null) |
| `ethics_assessment` | object | **yes** | Must not be null, empty, or the sentinel `"N/A"`; fields: `ethics_issues_identified` (boolean, explicitly present), `issues` (array — non-empty when `ethics_issues_identified: true`, may be empty otherwise), `self_assessment_statement` (non-empty string — explicitly present) |
| `governance_matrix` | array | **yes** | Non-empty; each governance body entry: `body_name`, `composition` (array of partner identifiers), `decision_scope` (non-empty string) |
| `management_roles` | array | **yes** | Every role's `assigned_to` must match a `partner_id` in Tier 3 `partners.json` (`all_management_roles_in_tier3`); each entry: `role_id`, `role_name`, `assigned_to`, `responsibilities` (non-empty array) |
| `instrument_sections_addressed` | array | **yes** | Every mandatory section from `section_schema_registry.json` for the active instrument must appear with `status: addressed` or `status: not_applicable`; entry fields: `section_id`, `section_name`, `status` (enum: addressed/not_applicable/deferred) |

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements

**Predecessors:** `phase_03_gate`, `phase_04_gate`, AND `phase_05_gate` must all have passed. Sources: edges `e03_to_06`, `e04_to_06`, `e05_to_06`. Verify all three gate result artifacts.

If any predecessor gate has not passed, halt immediately. Write `decision_type: constitutional_halt` identifying the unmet edge.

**Entry gate:** none.

### Exit Gate

**Exit gate:** `phase_06_gate` — evaluated after this agent writes all canonical outputs.

Gate conditions (source: `manifest.compile.yaml`, `quality_gates.yaml`):
1. All three predecessor gates passed (`g07_p01`, `g07_p02`, `g07_p03`)
2. Implementation architecture written to Tier 4 (`g07_p04`, `g07_p04b`)
3. Risk register populated (`g07_p05`)
4. Ethics self-assessment explicitly present — not omitted (`g07_p06`)
5. Governance matrix defined (`g07_p07`)
6. All management roles assigned to Tier 3 consortium members (`g07_p08`)
7. All instrument-mandated implementation sections addressed per Tier 2A schema (`g07_p09`)

Gate result: `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/gate_result.json`. Blocking edge on pass: `e06_to_07` (`n07_budget_gate`).

### Failure Protocol

#### Case 1: Gate condition not met (`phase_06_gate` fails)
- **Halt:** Do not proceed to Phase 7.
- **Write:** `implementation_architecture.json` with content produced; document which sections are absent or incomplete.
- **Decision log:** `decision_type: gate_failure`; list failed conditions (e.g., ethics assessment null, management role assigned to partner not in Tier 3).
- **Must not:** Write a placeholder ethics assessment (CLAUDE.md §13 — ethics self-assessment must be explicit). Must not assign management roles to invented partners.

#### Case 2: Required input absent
- **Halt:** If `risks.json`, consortium data, or `compliance_profile.json` are absent, halt.
- **Write:** Decision log `decision_type: gate_failure`.
- **Must not:** Invent risk entries or governance roles from generic programme knowledge.

#### Case 3: Mandatory predecessor gate(s) not passed
- **Halt immediately** if any of the three predecessor gates are unmet.
- **Write:** `decision_type: constitutional_halt`; name the unmet edge.

#### Case 4: Constitutional prohibition triggered
- **Halt** if required to redesign consortium composition (CLAUDE.md §13.3), assign roles to non-Tier-3 partners, or omit ethics assessment.
- **Write:** `decision_type: constitutional_halt`.

### Decision-Log Write Obligations

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
