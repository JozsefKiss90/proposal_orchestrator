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

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 5–9 of `agent-generation-plan.md`.

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
