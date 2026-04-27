# proposal_integrator prompt specification

## Purpose

Phase 8d node body executor for `n08d_assembly`. Assembles the three criterion-
aligned sections (excellence, impact, implementation) into a coherent Part B
draft. Performs cross-section consistency checks. Produces
`part_b_assembled_draft.json` (schema `orch.tier5.part_b_assembled_draft.v1`).

**Predecessor gates:** `gate_10a_excellence_completeness`,
`gate_10b_impact_completeness`, `gate_10c_implementation_completeness` must all
have passed before assembly begins.

## Invocation context

- Node binding: `n08d_assembly`
- Phase: `phase_08d_assembly`
- Entry gate: none
- Exit gate: `gate_10d_cross_section_consistency`
- Predecessor gates: gate_10a, gate_10b, gate_10c must have passed (all sections drafted)
- Predecessor edges: `e08a_to_08d`, `e08b_to_08d`, `e08c_to_08d` (convergent fan-in)

## Inputs

| Input | Location |
|-------|----------|
| Excellence section | `docs/tier5_deliverables/proposal_sections/excellence_section.json` |
| Impact section | `docs/tier5_deliverables/proposal_sections/impact_section.json` |
| Implementation section | `docs/tier5_deliverables/proposal_sections/implementation_section.json` |
| Application form | `docs/tier2a_instrument_schemas/application_forms/` |
| Project data | `docs/tier3_project_instantiation/` |

## Reasoning sequence

1. Verify predecessor gates passed (gate_10a, gate_10b, gate_10c).
2. Read all three section artifacts from `docs/tier5_deliverables/proposal_sections/`.
3. Verify `excellence_section.json`, `impact_section.json`, `implementation_section.json` are present.
4. Invoke `cross-section-consistency-check` to perform cross-section consistency checks (objectives, WP refs, partner names, deliverables, milestones, KPIs, impact claims, terminology) and produce `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json`.
5. After `cross-section-consistency-check` has produced the assembled draft, invoke `proposal-section-traceability-check` to audit traceability of the assembled artifact.
6. After traceability audit, invoke `constitutional-compliance-check` to audit constitutional compliance of the assembled artifact.
7. Assembly is complete. `artifact_status` must be absent at write time.
