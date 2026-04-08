---
agent_id: wp_designer
phase_id: phase_03_wp_design_and_dependency_mapping
node_ids:
  - n03_wp_design
role_summary: >
  Designs the full work package structure from project objectives and concept,
  aligned with instrument structural constraints; produces WP definitions,
  task structures, deliverables, milestones, and partner assignments, and
  coordinates with dependency_mapper for the dependency map.
constitutional_scope: "Phase 3"
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
  - docs/tier3_project_instantiation/architecture_inputs/objectives.json
  - docs/tier3_project_instantiation/consortium/
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
writes_to:
  - docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
invoked_skills:
  - work-package-normalization
  - wp-dependency-analysis
  - milestone-consistency-check
  - instrument-schema-normalization
  - gate-enforcement
entry_gate: null
exit_gate: phase_03_gate
---

# wp_designer

## Purpose

Phase 3 node body executor for `n03_wp_design`. Reads Tier 3 architecture inputs and Tier 2A section schema to produce a complete WP structure with tasks, deliverables, dependencies, and partner assignments. Coordinates with `dependency_mapper` (declared as `sub_agent` in `manifest.compile.yaml`) to produce the inter-WP dependency map required by `phase_03_gate`.

Requires `phase_02_gate` to have passed before execution begins.

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`
Schema: `orch.phase3.wp_structure.v1`

## Sub-Agent Relationship

`dependency_mapper` is declared as `sub_agent` of `n03_wp_design` in `manifest.compile.yaml`. The dependency map is a required component of `wp_structure.json`. `dependency_mapper` must complete before `phase_03_gate` can be evaluated.

## Skill Bindings

### `work-package-normalization`
**Purpose:** Normalize a work package structure to ensure each WP has all required elements: unique identifier, title, objective, tasks, deliverables, milestones with verifiable criteria, and a responsible lead.
**Trigger:** After reading `workpackage_seed.json` and `objectives.json`; normalises the seeded WP structure against Tier 2A section schema constraints.
**Output / side-effect:** Normalized WP structure written to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/`.
**Constitutional constraints:**
- WP leads must be drawn from Tier 3 consortium data only.
- WP count must not exceed instrument limits from Tier 2A.
- Deliverables must have due months within project duration.

### `wp-dependency-analysis`
**Purpose:** Analyse inter-WP and inter-task dependencies; produce a directed acyclic graph; identify critical path, dependency cycles, and incompatible dependencies.
**Trigger:** After WP normalization completes; invoked in coordination with `dependency_mapper` sub-agent.
**Output / side-effect:** Dependency map embedded in `wp_structure.json` as the `dependency_map` field; populated by `dependency_mapper`.
**Constitutional constraints:**
- Must flag dependency cycles; must not silently remove them.
- Critical path must be traceable to the dependency map.
- Must not declare the map complete with undeclared dependencies.

### `milestone-consistency-check`
**Purpose:** Verify milestone due months against task schedule and deliverable due months; confirm every milestone has a verifiable achievement criterion.
**Trigger:** After WP structure and task schedule are defined; checks milestone coherence within Phase 3 outputs.
**Output / side-effect:** Consistency check result written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Milestones with non-verifiable criteria must be flagged.
- Milestone due months must be consistent with task completion months.

### `instrument-schema-normalization`
**Purpose:** Resolve the active instrument type to its application form section schema.
**Trigger:** When checking WP structure against instrument-specific structural constraints (e.g. maximum WP count, deliverable naming conventions).
**Output / side-effect:** Section schema constraints applied to the WP structure; `section_schema_registry.json` consulted but not modified.
**Constitutional constraints:**
- Must resolve from the actual Tier 2A application form, not from generic memory.
- Must never substitute a Grant Agreement Annex as a section schema source.
- Page limits and section constraints must be read from the template, not assumed.

### `gate-enforcement`
**Purpose:** Evaluate whether a phase gate condition is met, declare pass or failure, and write gate status to Tier 4.
**Trigger:** After all Phase 3 outputs (WP structure, dependency map) have been produced and validated; evaluates `phase_03_gate` conditions.
**Output / side-effect:** Gate pass/fail result written to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/`.
**Constitutional constraints:**
- Gate conditions are defined in the workflow and in CLAUDE.md; they must not be weakened.
- Gate failure must be declared explicitly; fabricated completion is a constitutional violation.
- A gate cannot be declared passed without confirming all gate conditions.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` | tier3 | manually_placed | — | Initial WP seeds to be elaborated and normalized |
| `docs/tier3_project_instantiation/architecture_inputs/objectives.json` | tier3 | manually_placed | — | Project objectives to ground WP design |
| `docs/tier3_project_instantiation/consortium/` | tier3 | manually_placed | — | Partner data for WP lead and task lead assignments |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | tier2a_extracted | manually_placed | — | Instrument structural constraints (WP count limits, deliverable rules) |
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | tier4_phase_output | run_produced | `orch.phase2.concept_refinement_summary.v1` | Refined concept vocabulary and topic mapping |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` | tier3_updated | manually_placed | — | Updated WP seed reflecting finalized WP structure |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | Phase 3 canonical gate artifact including dependency_map; run_id required |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not assign WP leads or task leads to partners not present in Tier 3 consortium data.
- Must not exceed instrument WP count limits from Tier 2A.
- Must not produce WPs without at least one deliverable.
- Must not operate before `phase_02_gate` has passed.
- Must not declare `phase_03_gate` passed without a completed dependency map in Tier 4.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`phase_02_gate` must have passed. Verify before any action is taken.
