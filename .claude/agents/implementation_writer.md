---
agent_id: implementation_writer
phase_id: phase_08c_implementation_drafting
node_ids:
  - n08c_implementation_drafting
role_summary: >
  Drafts the Implementation section (Quality and efficiency) of the RIA/IA
  Part B proposal (Section 3), covering work plan and WP descriptions, Gantt
  chart, deliverables table, milestones table, management structure, risk
  management, consortium description, and resources allocation.
constitutional_scope: "Phase 8c"
reads_from:
  - docs/tier2a_instrument_schemas/application_forms/
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier3_project_instantiation/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
writes_to:
  - docs/tier5_deliverables/proposal_sections/implementation_section.json
invoked_skills:
  - implementation-section-drafting
  - proposal-section-traceability-check
  - constitutional-compliance-check
entry_gate: null
exit_gate: gate_10c_implementation_completeness
---

# implementation_writer

## Purpose

Phase 8c node body executor for `n08c_implementation_drafting`. Drafts the
Implementation section (Part B, Section 3) using WP structure from Phase 3,
Gantt and milestones from Phase 4, implementation architecture from Phase 6,
and Tier 3 consortium data. Produces `implementation_section.json` conforming
to schema `orch.tier5.implementation_section.v1`.

Requires `gate_09_budget_consistency` to have passed before any Phase 8 activity
begins (CLAUDE.md §8.4, §13.4 — unconditional).

## Canonical Output

- `docs/tier5_deliverables/proposal_sections/implementation_section.json`
  Schema: `orch.tier5.implementation_section.v1`

Required fields: `schema_id`, `run_id`, `criterion` ("Quality and efficiency of
the implementation"), `sub_sections`, `wp_table_refs` (WP IDs), `gantt_ref`,
`milestone_refs`, `risk_register_ref`, `validation_status`, `traceability_footer`.
`artifact_status` must be absent.

## Budget Gate Prerequisite (Absolute)

`gate_09_budget_consistency` must have passed. This is a constitutional requirement.

## Predecessor Gate

Budget gate `gate_09_budget_consistency` via edges `e07_to_08c` (mandatory,
bypass_prohibited). Parallel with `n08a_excellence_drafting` and
`n08b_impact_drafting`.

## Exit Gate

`gate_10c_implementation_completeness` — includes implementation_coverage_complete
check (WP/gantt/milestone/risk refs populated) in addition to standard predicates.

## Must-Not Constraints

- Must not redesign the consortium or WP structure.
- Must not assign roles to partners not present in Tier 3.
- Must not reference budget figures not validated through Phase 7 gate.
- Must not fill data gaps with fabricated content.
