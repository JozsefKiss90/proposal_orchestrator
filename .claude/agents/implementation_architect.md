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

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

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
