# implementation_writer prompt specification

## Purpose

Phase 8c node body executor for `n08c_implementation_drafting`. Drafts the
Implementation section (Part B, Section 3) covering work plan, WP descriptions,
Gantt, deliverables, milestones, management, risk, consortium, and resources.
Produces `implementation_section.json` (schema
`orch.tier5.implementation_section.v1`).

**Budget gate prerequisite (absolute and unconditional):** `gate_09_budget_consistency`
must have passed before any Phase 8 activity begins.

## Invocation context

- Node binding: `n08c_implementation_drafting`
- Phase: `phase_08c_implementation_drafting`
- Entry gate: none
- Exit gate: `gate_10c_implementation_completeness`
- Budget gate prerequisite: `gate_09_budget_consistency` must have passed (unconditional)
- Parallel siblings: `n08a_excellence_drafting`, `n08b_impact_drafting`

## Inputs

| Input | Location |
|-------|----------|
| Application form | `docs/tier2a_instrument_schemas/application_forms/` |
| Evaluation form | `docs/tier2a_instrument_schemas/evaluation_forms/` |
| Extracted schemas | `docs/tier2a_instrument_schemas/extracted/` |
| Project data | `docs/tier3_project_instantiation/` |
| WP structure | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` |
| Gantt + milestones | `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/` |
| Implementation arch | `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/` |
| Budget gate | `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/` |

## Reasoning sequence

1. Verify budget gate passed.
2. Read WP structure (`wp_structure.json`), Gantt (`gantt.json`), implementation architecture.
3. Read Tier 3 project data (consortium, roles, risks).
4. Read Tier 2A evaluation form — identify Quality criterion scoring logic.
5. Draft sub-sections: work plan, WP descriptions, Gantt narrative, deliverables table, milestones table, management structure, risk register summary, consortium description, resources.
6. Populate `wp_table_refs` with all WP IDs from `wp_structure.json`.
7. Set `gantt_ref`, `milestone_refs`, `risk_register_ref` to source artifact paths.
8. Build `validation_status` and `traceability_footer`.
9. Apply `proposal-section-traceability-check` and `constitutional-compliance-check`.
10. Write `docs/tier5_deliverables/proposal_sections/implementation_section.json` (schema: `orch.tier5.implementation_section.v1`). `artifact_status` must be absent.
