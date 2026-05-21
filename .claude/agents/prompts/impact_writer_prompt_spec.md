# impact_writer prompt specification

## Purpose

Phase 8b node body executor for `n08b_impact_drafting`. Drafts the Impact section
(Part B, Section 2) covering expected impacts, impact pathways, DEC measures,
and sustainability. Produces `impact_section.json` (schema
`orch.tier5.impact_section.v1`).

**Budget gate prerequisite (absolute and unconditional):** `gate_09_budget_consistency`
must have passed before any Phase 8 activity begins.

## Invocation context

- Node binding: `n08b_impact_drafting`
- Phase: `phase_08b_impact_drafting`
- Entry gate: none
- Exit gate: `gate_10b_impact_completeness`
- Budget gate prerequisite: `gate_09_budget_consistency` must have passed (unconditional)
- Parallel siblings: `n08a_excellence_drafting`, `n08c_implementation_drafting`

## Inputs

| Input | Location |
|-------|----------|
| Application form | `docs/tier2a_instrument_schemas/application_forms/` |
| Evaluation form | `docs/tier2a_instrument_schemas/evaluation_forms/` |
| Extracted schemas | `docs/tier2a_instrument_schemas/extracted/` |
| Project data | `docs/tier3_project_instantiation/` |
| Impact architecture | `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/` |
| WP structure | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` |
| Budget gate | `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/` |
| Expected outcomes/impacts | `docs/tier2b_topic_and_call_sources/extracted/` |

## Reasoning sequence

1. Verify budget gate passed.
2. Read impact architecture from Phase 5 (`impact_architecture.json`).
3. Read Tier 2B expected outcomes and expected impacts.
4. Read WP structure from Phase 3 (to ground impact claims in project activities).
5. Read Tier 3 project data (outcomes, impacts, consortium).
6. Execute `impact-section-drafting` skill: draft sub-sections (expected impacts, impact pathways, DEC measures, sustainability), populate `impact_pathway_refs`, set `dec_coverage` booleans, build `validation_status` and `traceability_footer`. Write `impact_section.json`. If any material claim is unresolved, return declared failure instead of writing a gate-blocking artifact.
7. Apply `proposal-section-traceability-check` skill on the produced `impact_section.json`.
8. Apply `constitutional-compliance-check` skill on the produced `impact_section.json`.

