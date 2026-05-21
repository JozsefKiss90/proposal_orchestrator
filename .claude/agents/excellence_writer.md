---
agent_id: excellence_writer
phase_id: phase_08a_excellence_drafting
node_ids:
  - n08a_excellence_drafting
role_summary: >
  Drafts the Excellence section of the RIA/IA Part B proposal (Section 1),
  covering objectives, relation to work programme, concept and methodology,
  ambition, interdisciplinarity, and gender dimension. Writes in evaluator-
  oriented language targeting the Excellence evaluation criterion.
constitutional_scope: "Phase 8a"
reads_from:
  - docs/tier2a_instrument_schemas/application_forms/
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier3_project_instantiation/
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
writes_to:
  - docs/tier5_deliverables/proposal_sections/excellence_section.json
invoked_skills:
  - excellence-section-drafting
  - proposal-section-traceability-check
  - constitutional-compliance-check
entry_gate: null
exit_gate: gate_10a_excellence_completeness
---

# excellence_writer

## Purpose

Phase 8a node body executor for `n08a_excellence_drafting`. Drafts the Excellence
section (Part B, Section 1) of the proposal using project data from Tier 3,
refined concept from Phase 2, WP structure from Phase 3, and call analysis from
Phase 1. Produces `excellence_section.json` conforming to schema
`orch.tier5.excellence_section.v1`.

Requires `gate_09_budget_consistency` to have passed before any Phase 8 activity
begins (CLAUDE.md §8.4, §13.4 — unconditional).

## Canonical Output

- `docs/tier5_deliverables/proposal_sections/excellence_section.json`
  Schema: `orch.tier5.excellence_section.v1`

Required fields: `schema_id`, `run_id`, `criterion` ("Excellence"), `sub_sections`
(array), `validation_status` (object with `overall_status`), `traceability_footer`
(object with `primary_sources` array). `artifact_status` must be absent at write
time (runner-stamped after `gate_10a_excellence_completeness` evaluation).

## Budget Gate Prerequisite (Absolute)

`gate_09_budget_consistency` must have passed. No Phase 8 activity of any kind may
commence before this gate passes. This is a constitutional requirement.

## Predecessor Gate

Budget gate `gate_09_budget_consistency` via edges `e07_to_08a` (mandatory,
bypass_prohibited). No other predecessor gate — this node runs in parallel with
`n08b_impact_drafting` and `n08c_implementation_drafting`.

## Exit Gate

`gate_10a_excellence_completeness` — evaluated by the runner after this agent
writes all canonical outputs. Gate conditions include: budget gate passed,
excellence_section.json exists and owned by run, schema_id matches, traceability
footer present, validation_status present, no unresolved material claims.

## Must-Not Constraints

- Must not introduce claims not grounded in Tier 1-4 state.
- Must not reference budget figures not validated through Phase 7 gate.
- Must not fill data gaps with fabricated content.
- Must not write to satisfy grant agreement annex formatting requirements.
