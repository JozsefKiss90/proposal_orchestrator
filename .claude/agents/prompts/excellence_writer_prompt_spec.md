# excellence_writer prompt specification

## Purpose

Phase 8a node body executor for `n08a_excellence_drafting`. Drafts the Excellence
section (Part B, Section 1) covering objectives, relation to work programme,
concept and methodology, ambition, interdisciplinarity, and gender dimension.
Produces `excellence_section.json` (schema `orch.tier5.excellence_section.v1`).

**Budget gate prerequisite (absolute and unconditional):** `gate_09_budget_consistency`
must have passed before any Phase 8 activity begins.

## Invocation context

- Node binding: `n08a_excellence_drafting`
- Phase: `phase_08a_excellence_drafting`
- Entry gate: none
- Exit gate: `gate_10a_excellence_completeness`
- Budget gate prerequisite: `gate_09_budget_consistency` must have passed (unconditional)
- Parallel siblings: `n08b_impact_drafting`, `n08c_implementation_drafting`

## Inputs

| Input | Location |
|-------|----------|
| Application form | `docs/tier2a_instrument_schemas/application_forms/` |
| Evaluation form | `docs/tier2a_instrument_schemas/evaluation_forms/` |
| Extracted schemas | `docs/tier2a_instrument_schemas/extracted/` |
| Project data | `docs/tier3_project_instantiation/` |
| Call analysis | `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/` |
| Concept refinement | `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/` |
| WP structure | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` |
| Budget gate | `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/` |

## Reasoning sequence

1. Verify budget gate passed (read `budget_gate_assessment.json`, check `gate_pass_declaration: "pass"`).
2. Read Tier 2A evaluation form — identify Excellence criterion scoring logic.
3. Read refined concept (Phase 2), WP structure (Phase 3), call analysis (Phase 1).
4. Read Tier 3 project data (objectives, consortium, concept note).
5. Draft sub-sections: objectives, relation to work programme, concept and methodology, ambition, interdisciplinarity, gender dimension.
6. Build `validation_status` with per-claim classification (confirmed/inferred/assumed/unresolved).
7. Build `traceability_footer` with `primary_sources` array.
8. Apply `proposal-section-traceability-check` skill.
9. Apply `constitutional-compliance-check` skill.
10. Write `docs/tier5_deliverables/proposal_sections/excellence_section.json` (schema: `orch.tier5.excellence_section.v1`). `artifact_status` must be absent.
