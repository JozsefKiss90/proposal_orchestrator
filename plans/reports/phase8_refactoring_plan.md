# Phase 8 Refactoring Plan: Criterion-Aligned Drafting Pipeline

**Date:** 2026-04-25
**Branch:** phase8_refactor
**Status:** PLAN ONLY -- awaiting approval before implementation

---

## 1. Current-State Diagnosis

### 1.1 Current Phase 8 Structure

Phase 8 currently uses four coarse substeps under a single `phase_number: 8`:

| Node ID | Purpose | Agent | Exit Gate |
|---------|---------|-------|-----------|
| `n08a_section_drafting` | Draft all sections | `proposal_writer` | `gate_10_part_b_completeness` |
| `n08b_assembly` | Assemble into Part B | `proposal_writer` | `gate_10_part_b_completeness` |
| `n08c_evaluator_review` | Evaluator-style review | `evaluator_reviewer` | `gate_11_review_closure` |
| `n08d_revision` | Revision + final export | `revision_integrator` | `gate_12_constitutional_compliance` |

DAG edges: `n07 --gate_09--> n08a --gate_10--> n08b --gate_10--> n08c --gate_11--> n08d`

### 1.2 Problem

The RIA/IA Part B template (af_he-ria-ia_en.pdf, Version 10.0) structures Part B as **three sections, each corresponding to one evaluation criterion**:

1. **Section 1 -- Excellence** (evaluated under the Excellence criterion)
2. **Section 2 -- Impact** (evaluated under the Impact criterion)
3. **Section 3 -- Quality and efficiency of the implementation** (evaluated under the Quality criterion)

The current `n08a_section_drafting` monolithically drafts all sections in a single node. This creates several issues:

- **No independent gating per criterion**: a failure in the Implementation section blocks re-review of a passing Excellence section.
- **No parallelism**: the three criterion-aligned sections could be drafted concurrently (all depend only on gate_09, not on each other).
- **Coarse failure diagnostics**: `gate_10_part_b_completeness` is evaluated after assembly, conflating drafting failures with assembly failures.
- **Agent scope creep**: a single `proposal_writer` agent spans all three evaluator criteria, which differ fundamentally in their source inputs.

### 1.3 Target Architecture

Replace the linear `n08a --> n08b --> n08c --> n08d` chain with a criterion-aligned DAG:

```
                  gate_09_budget_consistency
                  /          |           \
         n08a_excellence  n08b_impact  n08c_implementation
         (gate_10a)       (gate_10b)   (gate_10c)
                  \          |           /
                   n08d_assembly
                   (gate_10d)
                       |
                   n08e_evaluator_review
                   (gate_11)
                       |
                   n08f_revision
                   (gate_12) [terminal]
```

This enables:
- **Parallel drafting** of Excellence, Impact, and Implementation sections.
- **Independent per-criterion gates** with criterion-specific completeness checks.
- **Cross-section consistency check** at assembly.
- **Unchanged downstream flow** for review and revision.

---

## 2. Exact Files to Change

### Workflow specification files (`.claude/workflows/system_orchestration/`)
1. `manifest.compile.yaml` -- node_registry, edge_registry, gate_registry, artifact_registry
2. `workflow_phases/phase_08_drafting_review.yaml` -- substep definitions
3. `agent_catalog.yaml` -- add new agents, update existing
4. `skill_catalog.yaml` -- add new skills, update existing
5. `artifact_schema_specification.yaml` -- add new artifact schemas
6. `gate_rules_library.yaml` -- add new gate rules, update existing
7. `quality_gates.yaml` -- add new gate definitions

### Agent .md files (`.claude/agents/`)
8. `excellence_writer.md` -- **NEW**
9. `impact_writer.md` -- **NEW**
10. `implementation_writer.md` -- **NEW**
11. `proposal_integrator.md` -- **NEW**
12. `proposal_writer.md` -- update scope (remove n08a/n08b bindings)
13. `evaluator_reviewer.md` -- **NEW or update** if node/phase references change
14. `revision_integrator.md` -- update node/phase references

### Skill .md files (`.claude/skills/`)
15. `excellence-section-drafting.md` -- **NEW**
16. `impact-section-drafting.md` -- **NEW**
17. `implementation-section-drafting.md` -- **NEW**
18. `cross-section-consistency-check.md` -- **NEW**
19. `evaluator-criteria-review.md` -- update for criterion-scoped and assembled-draft modes
20. `proposal-section-traceability-check.md` -- update artifact name references if needed
21. `constitutional-compliance-check.md` -- update if artifact_path patterns change

### Runner code (`runner/`)
22. `run_context.py` -- update `PHASE_8_NODE_IDS` frozenset
23. `gate_result_registry.py` -- add new gate result paths
24. `upstream_inputs.py` -- add upstream input entries for new gates
25. `agent_runtime.py` -- update `_NODE_AUDITABLE_FALLBACK_DIRS` and `_TIER5_AUDIT_SKILLS` applicability

### Documentation
26. `README.md` -- update Phase 8 DAG diagram and descriptions

### Registry files (`docs/index/`)
27. `schema_registry.json` -- add new schema_id entries
28. `workflow_registry.json` -- update phase 8 description

---

## 3. Proposed Manifest / Node / Edge Changes

### 3.1 Node Registry Changes

**Remove:** `n08a_section_drafting`, `n08b_assembly`, `n08c_evaluator_review`, `n08d_revision`

**Add:**

```yaml
- node_id: n08a_excellence_drafting
  phase_id: phase_08a_excellence_drafting
  phase_number: 8
  substep: a
  name: "Excellence Section Drafting"
  source_file: workflow_phases/phase_08_drafting_review.yaml
  agent: excellence_writer
  skills:
    - excellence-section-drafting
    - proposal-section-traceability-check
    - constitutional-compliance-check
  exit_gate: gate_10a_excellence_completeness
  terminal: false

- node_id: n08b_impact_drafting
  phase_id: phase_08b_impact_drafting
  phase_number: 8
  substep: b
  name: "Impact Section Drafting"
  source_file: workflow_phases/phase_08_drafting_review.yaml
  agent: impact_writer
  skills:
    - impact-section-drafting
    - proposal-section-traceability-check
    - constitutional-compliance-check
  exit_gate: gate_10b_impact_completeness
  terminal: false

- node_id: n08c_implementation_drafting
  phase_id: phase_08c_implementation_drafting
  phase_number: 8
  substep: c
  name: "Implementation Section Drafting"
  source_file: workflow_phases/phase_08_drafting_review.yaml
  agent: implementation_writer
  skills:
    - implementation-section-drafting
    - proposal-section-traceability-check
    - constitutional-compliance-check
  exit_gate: gate_10c_implementation_completeness
  terminal: false

- node_id: n08d_assembly
  phase_id: phase_08d_assembly
  phase_number: 8
  substep: d
  name: "Cross-Section Assembly"
  source_file: workflow_phases/phase_08_drafting_review.yaml
  agent: proposal_integrator
  skills:
    - cross-section-consistency-check
    - proposal-section-traceability-check
    - constitutional-compliance-check
  exit_gate: gate_10d_cross_section_consistency
  terminal: false

- node_id: n08e_evaluator_review
  phase_id: phase_08e_evaluator_review
  phase_number: 8
  substep: e
  name: "Evaluator-Style Review"
  source_file: workflow_phases/phase_08_drafting_review.yaml
  agent: evaluator_reviewer
  skills:
    - evaluator-criteria-review
    - proposal-section-traceability-check
    - constitutional-compliance-check
  exit_gate: gate_11_review_closure
  terminal: false

- node_id: n08f_revision
  phase_id: phase_08f_revision
  phase_number: 8
  substep: f
  name: "Revision Cycle"
  source_file: workflow_phases/phase_08_drafting_review.yaml
  agent: revision_integrator
  skills:
    - proposal-section-traceability-check
    - evaluator-criteria-review
    - constitutional-compliance-check
    - decision-log-update
    - checkpoint-publish
  exit_gate: gate_12_constitutional_compliance
  terminal: true
```

### 3.2 Edge Registry Changes

**Remove:** `e07_to_08a`, `e08a_to_08b`, `e08b_to_08c`, `e08c_to_08d`

**Add:**

```yaml
# Budget gate fans out to three parallel drafting nodes
- edge_id: e07_to_08a
  from_node: n07_budget_gate
  to_node: n08a_excellence_drafting
  gate_condition: gate_09_budget_consistency
  mandatory_gate: true
  bypass_prohibited: true
  description: "Budget gate must pass before Excellence drafting"

- edge_id: e07_to_08b
  from_node: n07_budget_gate
  to_node: n08b_impact_drafting
  gate_condition: gate_09_budget_consistency
  mandatory_gate: true
  bypass_prohibited: true
  description: "Budget gate must pass before Impact drafting"

- edge_id: e07_to_08c
  from_node: n07_budget_gate
  to_node: n08c_implementation_drafting
  gate_condition: gate_09_budget_consistency
  mandatory_gate: true
  bypass_prohibited: true
  description: "Budget gate must pass before Implementation drafting"

# Three section gates converge on assembly
- edge_id: e08a_to_08d
  from_node: n08a_excellence_drafting
  to_node: n08d_assembly
  gate_condition: gate_10a_excellence_completeness
  description: "Excellence section must be complete before assembly"

- edge_id: e08b_to_08d
  from_node: n08b_impact_drafting
  to_node: n08d_assembly
  gate_condition: gate_10b_impact_completeness
  description: "Impact section must be complete before assembly"

- edge_id: e08c_to_08d
  from_node: n08c_implementation_drafting
  to_node: n08d_assembly
  gate_condition: gate_10c_implementation_completeness
  description: "Implementation section must be complete before assembly"

# Assembly -> Review -> Revision (sequential)
- edge_id: e08d_to_08e
  from_node: n08d_assembly
  to_node: n08e_evaluator_review
  gate_condition: gate_10d_cross_section_consistency
  description: "Assembly must pass consistency check before review"

- edge_id: e08e_to_08f
  from_node: n08e_evaluator_review
  to_node: n08f_revision
  gate_condition: gate_11_review_closure
  description: "Review must complete before revision cycle"
```

---

## 4. Proposed Artifact Schema Changes

### 4.1 New Tier 5 Artifact Schemas

Add to `artifact_schema_specification.yaml` Section 2 (tier5_deliverable_schemas):

#### 4.1.1 `excellence_section.json`

```yaml
excellence_section:
  schema_id_value: "orch.tier5.excellence_section.v1"
  canonical_path: "docs/tier5_deliverables/proposal_sections/excellence_section.json"
  provenance_class: run_produced
  fields:
    schema_id: { type: string, required: true }
    run_id: { type: string, required: true }
    artifact_status: { type: string, required: false, enum: [valid, invalid] }
    criterion: { type: string, required: true, const: "Excellence" }
    sub_sections:
      type: array
      required: true
      description: >
        Ordered array of Excellence sub-sections per the RIA/IA Part B template.
        Covers: objectives, relation to work programme, concept and methodology,
        ambition, interdisciplinarity, gender dimension.
      item_schema:
        sub_section_id: { type: string, required: true }
        title: { type: string, required: true }
        content: { type: string, required: true }
        word_count: { type: integer, required: true }
    validation_status: { type: object, required: true }
    traceability_footer: { type: object, required: true }
```

#### 4.1.2 `impact_section.json`

```yaml
impact_section:
  schema_id_value: "orch.tier5.impact_section.v1"
  canonical_path: "docs/tier5_deliverables/proposal_sections/impact_section.json"
  provenance_class: run_produced
  fields:
    schema_id: { type: string, required: true }
    run_id: { type: string, required: true }
    artifact_status: { type: string, required: false, enum: [valid, invalid] }
    criterion: { type: string, required: true, const: "Impact" }
    sub_sections:
      type: array
      required: true
      description: >
        Covers: project results and expected impacts, measures to maximise impact
        (dissemination, exploitation, communication), summary of impact pathways.
      item_schema:
        sub_section_id: { type: string, required: true }
        title: { type: string, required: true }
        content: { type: string, required: true }
        word_count: { type: integer, required: true }
    impact_pathway_refs:
      type: array
      required: true
      description: >
        References to impact_architecture.json pathways covered by this section.
      item_type: string
    dec_coverage:
      type: object
      required: true
      description: >
        Declaration of DEC plan coverage: dissemination, exploitation, communication.
      fields:
        dissemination_addressed: { type: boolean, required: true }
        exploitation_addressed: { type: boolean, required: true }
        communication_addressed: { type: boolean, required: true }
    validation_status: { type: object, required: true }
    traceability_footer: { type: object, required: true }
```

#### 4.1.3 `implementation_section.json`

```yaml
implementation_section:
  schema_id_value: "orch.tier5.implementation_section.v1"
  canonical_path: "docs/tier5_deliverables/proposal_sections/implementation_section.json"
  provenance_class: run_produced
  fields:
    schema_id: { type: string, required: true }
    run_id: { type: string, required: true }
    artifact_status: { type: string, required: false, enum: [valid, invalid] }
    criterion: { type: string, required: true, const: "Quality and efficiency of the implementation" }
    sub_sections:
      type: array
      required: true
      description: >
        Covers: work plan (WP descriptions, tables, Gantt, deliverables, milestones),
        management and risk, consortium composition, resources.
      item_schema:
        sub_section_id: { type: string, required: true }
        title: { type: string, required: true }
        content: { type: string, required: true }
        word_count: { type: integer, required: true }
    wp_table_refs:
      type: array
      required: true
      description: References to WP IDs covered.
      item_type: string
    gantt_ref: { type: string, required: true }
    milestone_refs: { type: array, required: true, item_type: string }
    risk_register_ref: { type: string, required: true }
    validation_status: { type: object, required: true }
    traceability_footer: { type: object, required: true }
```

#### 4.1.4 `part_b_assembled_draft.json`

```yaml
part_b_assembled_draft:
  schema_id_value: "orch.tier5.part_b_assembled_draft.v1"
  canonical_path: "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json"
  provenance_class: run_produced
  fields:
    schema_id: { type: string, required: true }
    run_id: { type: string, required: true }
    artifact_status: { type: string, required: false, enum: [valid, invalid] }
    sections:
      type: array
      required: true
      description: >
        Three sections in RIA/IA Part B order: Excellence, Impact, Implementation.
      item_schema:
        section_id: { type: string, required: true }
        criterion: { type: string, required: true }
        order: { type: integer, required: true }
        artifact_path: { type: string, required: true }
        word_count: { type: integer, required: false }
    consistency_log:
      type: array
      required: true
      description: Cross-section consistency checks.
      item_schema:
        check_id: { type: string, required: true }
        description: { type: string, required: true }
        sections_checked: { type: array, required: true, item_type: string }
        status: { type: string, required: true, enum: [consistent, inconsistency_flagged, resolved] }
        inconsistency_note: { type: string, required: false }
```

### 4.2 Schema ID Registry Additions

```yaml
- schema_id: "orch.tier5.excellence_section.v1"
  artifact: excellence_section.json
- schema_id: "orch.tier5.impact_section.v1"
  artifact: impact_section.json
- schema_id: "orch.tier5.implementation_section.v1"
  artifact: implementation_section.json
- schema_id: "orch.tier5.part_b_assembled_draft.v1"
  artifact: part_b_assembled_draft.json
```

### 4.3 Existing Artifacts -- Backward Compatibility

The existing `assembled_draft.json` (schema `orch.tier5.assembled_draft.v1`) is **replaced** by `part_b_assembled_draft.json` (schema `orch.tier5.part_b_assembled_draft.v1`). The old schema remains in the specification for documentation but is no longer produced by any node.

The existing per-section `<section_id>.json` files (schema `orch.tier5.proposal_section.v1`) remain valid. The three new criterion-aligned section artifacts are **supersets** of the `proposal_section.v1` schema -- they add criterion-specific fields. The `proposal_section.v1` schema is retained for any non-criterion-aligned sections (cover page, annexes) if needed.

`review_packet.json`, `final_export.json`, `drafting_review_status.json`, and `phase8_checkpoint.json` retain their existing schemas unchanged.

---

## 5. Proposed Gate and Predicate Changes

### 5.1 New Gates

#### gate_10a_excellence_completeness

```yaml
- gate_id: gate_10a_excellence_completeness
  gate_kind: exit
  evaluated_at: "n08a_excellence_drafting exit"
  predicates:
    - predicate_id: g09a_p01
      type: gate_pass
      function: gate_pass_recorded
      args: { gate_id: "gate_09_budget_consistency", run_id: "${run_id}", tier4_root: "docs/tier4_orchestration_state" }
      prose_condition: "Budget gate must have passed"

    - predicate_id: g09a_p02
      type: file
      function: non_empty_json
      args: { path: "docs/tier5_deliverables/proposal_sections/excellence_section.json" }
      prose_condition: "Excellence section artifact exists and is non-empty"

    - predicate_id: g09a_p03
      type: file
      function: artifact_owned_by_run
      args: { path: "docs/tier5_deliverables/proposal_sections/excellence_section.json", run_id: "${run_id}" }
      prose_condition: "Excellence section owned by current run"

    - predicate_id: g09a_p04
      type: schema
      function: schema_id_matches
      args: { path: "docs/tier5_deliverables/proposal_sections/excellence_section.json", expected: "orch.tier5.excellence_section.v1" }
      prose_condition: "Schema ID matches orch.tier5.excellence_section.v1"

    - predicate_id: g09a_p05
      type: schema
      function: json_field_present
      args: { path: "docs/tier5_deliverables/proposal_sections/excellence_section.json", field: "traceability_footer" }
      prose_condition: "Traceability footer exists"

    - predicate_id: g09a_p06
      type: semantic
      function: no_unresolved_material_claims
      args: { path: "docs/tier5_deliverables/proposal_sections/excellence_section.json" }
      prose_condition: "No unresolved material claims in Excellence section"
```

#### gate_10b_impact_completeness

```yaml
- gate_id: gate_10b_impact_completeness
  gate_kind: exit
  evaluated_at: "n08b_impact_drafting exit"
  predicates:
    - predicate_id: g09b_p01
      type: gate_pass
      function: gate_pass_recorded
      args: { gate_id: "gate_09_budget_consistency", run_id: "${run_id}", tier4_root: "docs/tier4_orchestration_state" }
      prose_condition: "Budget gate must have passed"

    - predicate_id: g09b_p02
      type: file
      function: non_empty_json
      args: { path: "docs/tier5_deliverables/proposal_sections/impact_section.json" }
      prose_condition: "Impact section artifact exists and is non-empty"

    - predicate_id: g09b_p03
      type: file
      function: artifact_owned_by_run
      args: { path: "docs/tier5_deliverables/proposal_sections/impact_section.json", run_id: "${run_id}" }
      prose_condition: "Impact section owned by current run"

    - predicate_id: g09b_p04
      type: schema
      function: schema_id_matches
      args: { path: "docs/tier5_deliverables/proposal_sections/impact_section.json", expected: "orch.tier5.impact_section.v1" }
      prose_condition: "Schema ID matches orch.tier5.impact_section.v1"

    - predicate_id: g09b_p05
      type: schema
      function: json_field_present
      args: { path: "docs/tier5_deliverables/proposal_sections/impact_section.json", field: "traceability_footer" }
      prose_condition: "Traceability footer exists"

    - predicate_id: g09b_p06
      type: coverage
      function: impact_pathways_covered
      args:
        section_path: "docs/tier5_deliverables/proposal_sections/impact_section.json"
        impact_arch_path: "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json"
      prose_condition: "Impact pathways and DEC measures are covered"

    - predicate_id: g09b_p07
      type: semantic
      function: no_unresolved_material_claims
      args: { path: "docs/tier5_deliverables/proposal_sections/impact_section.json" }
      prose_condition: "No unresolved material claims in Impact section"
```

#### gate_10c_implementation_completeness

```yaml
- gate_id: gate_10c_implementation_completeness
  gate_kind: exit
  evaluated_at: "n08c_implementation_drafting exit"
  predicates:
    - predicate_id: g09c_p01
      type: gate_pass
      function: gate_pass_recorded
      args: { gate_id: "gate_09_budget_consistency", run_id: "${run_id}", tier4_root: "docs/tier4_orchestration_state" }
      prose_condition: "Budget gate must have passed"

    - predicate_id: g09c_p02
      type: file
      function: non_empty_json
      args: { path: "docs/tier5_deliverables/proposal_sections/implementation_section.json" }
      prose_condition: "Implementation section artifact exists and is non-empty"

    - predicate_id: g09c_p03
      type: file
      function: artifact_owned_by_run
      args: { path: "docs/tier5_deliverables/proposal_sections/implementation_section.json", run_id: "${run_id}" }
      prose_condition: "Implementation section owned by current run"

    - predicate_id: g09c_p04
      type: schema
      function: schema_id_matches
      args: { path: "docs/tier5_deliverables/proposal_sections/implementation_section.json", expected: "orch.tier5.implementation_section.v1" }
      prose_condition: "Schema ID matches orch.tier5.implementation_section.v1"

    - predicate_id: g09c_p05
      type: schema
      function: json_field_present
      args: { path: "docs/tier5_deliverables/proposal_sections/implementation_section.json", field: "traceability_footer" }
      prose_condition: "Traceability footer exists"

    - predicate_id: g09c_p06
      type: coverage
      function: implementation_coverage_complete
      args:
        section_path: "docs/tier5_deliverables/proposal_sections/implementation_section.json"
        wp_path: "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
        gantt_path: "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json"
      prose_condition: "WP, task, deliverable, milestone, governance, risk, partner-role, and resource-effort coverage"

    - predicate_id: g09c_p07
      type: semantic
      function: no_unresolved_material_claims
      args: { path: "docs/tier5_deliverables/proposal_sections/implementation_section.json" }
      prose_condition: "No unresolved material claims in Implementation section"
```

#### gate_10d_cross_section_consistency

```yaml
- gate_id: gate_10d_cross_section_consistency
  gate_kind: exit
  evaluated_at: "n08d_assembly exit"
  predicates:
    - predicate_id: g09d_p01
      type: gate_pass
      function: gate_pass_recorded
      args: { gate_id: "gate_10a_excellence_completeness", run_id: "${run_id}", tier4_root: "docs/tier4_orchestration_state" }
      prose_condition: "Excellence gate must have passed"

    - predicate_id: g09d_p02
      type: gate_pass
      function: gate_pass_recorded
      args: { gate_id: "gate_10b_impact_completeness", run_id: "${run_id}", tier4_root: "docs/tier4_orchestration_state" }
      prose_condition: "Impact gate must have passed"

    - predicate_id: g09d_p03
      type: gate_pass
      function: gate_pass_recorded
      args: { gate_id: "gate_10c_implementation_completeness", run_id: "${run_id}", tier4_root: "docs/tier4_orchestration_state" }
      prose_condition: "Implementation gate must have passed"

    - predicate_id: g09d_p04
      type: file
      function: non_empty_json
      args: { path: "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json" }
      prose_condition: "Assembled Part B draft exists"

    - predicate_id: g09d_p05
      type: file
      function: artifact_owned_by_run
      args: { path: "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json", run_id: "${run_id}" }
      prose_condition: "Assembled draft owned by current run"

    - predicate_id: g09d_p06
      type: schema
      function: schema_id_matches
      args: { path: "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json", expected: "orch.tier5.part_b_assembled_draft.v1" }
      prose_condition: "Schema ID matches"

    - predicate_id: g09d_p07
      type: semantic
      function: cross_section_consistency
      args:
        assembled_path: "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json"
        sections_dir: "docs/tier5_deliverables/proposal_sections/"
        tier3_path: "docs/tier3_project_instantiation/"
      prose_condition: "Objectives, WPs, partner names, deliverables, milestones, KPIs, impact claims, budget/resource claims, and terminology are cross-consistent"
```

### 5.2 Updated Gates

#### gate_11_review_closure

Update `g10_p01` to depend on `gate_10d_cross_section_consistency` instead of `gate_10_part_b_completeness`. Update assembled draft path references from `assembled_draft.json` to `part_b_assembled_draft.json`.

#### gate_12_constitutional_compliance

Update `g11_p01` to reference `gate_11_review_closure` (unchanged gate_id).
Update `g11_p05`/`g11_p05b` final_export path (unchanged).
Update `g11_p02` to check for criterion-aligned section artifacts rather than generic section files.
Add `g11_p07` budget gate confirmation (unchanged).

### 5.3 Removed Gates

`gate_10_part_b_completeness` is retired and replaced by `gate_10a` + `gate_10b` + `gate_10c` + `gate_10d`.

### 5.4 New Predicate Functions Required

| Function | Type | Purpose |
|----------|------|---------|
| `schema_id_matches` | schema | Check schema_id field equals expected value |
| `no_unresolved_material_claims` | semantic | Check validation_status has no unresolved claims |
| `impact_pathways_covered` | coverage | Check impact_pathway_refs covers all expected impacts |
| `implementation_coverage_complete` | coverage | Check wp_table_refs, gantt_ref, milestone_refs, risk_register_ref are populated |
| `cross_section_consistency` | semantic | Cross-check objectives, WPs, partners, KPIs across all three sections |

Note: `schema_id_matches` may already exist or be trivially derivable from `json_field_present`. The other four are new.

---

## 6. Proposed Agent Catalog Changes

### 6.1 New Agents

```yaml
- id: excellence_writer
  role: >
    Drafts the Excellence section of the RIA/IA Part B proposal, covering
    objectives, relation to work programme, concept and methodology, ambition,
    interdisciplinarity, and gender dimension. Writes in evaluator-oriented
    language targeting the Excellence evaluation criterion.
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
  must_not:
    - "Introduce claims not grounded in Tier 1-4 state"
    - "Reference budget figures not validated through Phase 7 gate"
    - "Fill data gaps with fabricated content"
    - "Write to satisfy grant agreement annex formatting requirements"
  phase_alignment: "phase_08a_excellence_drafting"

- id: impact_writer
  role: >
    Drafts the Impact section of the RIA/IA Part B proposal, covering
    expected impacts and their pathways, measures to maximise impact
    (dissemination, exploitation, communication), and sustainability.
    Maps all content to Phase 5 impact architecture.
  constitutional_scope: "Phase 8b"
  reads_from:
    - docs/tier2a_instrument_schemas/application_forms/
    - docs/tier2a_instrument_schemas/evaluation_forms/
    - docs/tier2a_instrument_schemas/extracted/
    - docs/tier3_project_instantiation/
    - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
    - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
    - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
    - docs/tier2b_topic_and_call_sources/extracted/
  writes_to:
    - docs/tier5_deliverables/proposal_sections/impact_section.json
  must_not:
    - "Fabricate coverage of a call expected impact not addressed by a project output"
    - "Assert impact claims without a traceable project mechanism"
    - "Reference budget figures not validated through Phase 7 gate"
    - "Fill data gaps with fabricated content"
  phase_alignment: "phase_08b_impact_drafting"

- id: implementation_writer
  role: >
    Drafts the Implementation section (Quality and efficiency) of the RIA/IA
    Part B proposal, covering work plan and WP descriptions, Gantt chart,
    deliverables table, milestones table, management structure, risk management,
    consortium description, and resources allocation.
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
  must_not:
    - "Redesign the consortium or WP structure"
    - "Assign roles to partners not present in Tier 3"
    - "Reference budget figures not validated through Phase 7 gate"
    - "Fill data gaps with fabricated content"
  phase_alignment: "phase_08c_implementation_drafting"

- id: proposal_integrator
  role: >
    Assembles the three criterion-aligned sections into a coherent Part B
    assembled draft. Performs cross-section consistency checks on objectives,
    WP references, partner names, deliverables, milestones, KPIs, impact
    claims, budget/resource claims, and terminology.
  constitutional_scope: "Phase 8d"
  reads_from:
    - docs/tier5_deliverables/proposal_sections/
    - docs/tier2a_instrument_schemas/application_forms/
    - docs/tier3_project_instantiation/
  writes_to:
    - docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json
  must_not:
    - "Rewrite section content during assembly; flag inconsistencies only"
    - "Introduce new claims not present in the section artifacts"
    - "Silently normalise contradictions between sections"
  phase_alignment: "phase_08d_assembly"
```

### 6.2 Updated Agents

- **`proposal_writer`**: Remove from node bindings. Retain in catalog as a legacy reference but mark `phase_alignment: "deprecated_by_phase8_refactor"`. Alternatively, delete entirely if no backward-compat concern.
- **`evaluator_reviewer`**: Update `phase_alignment` to `"phase_08e_evaluator_review"`. Update `reads_from` to reference `part_b_assembled_draft.json`. Node binding changes to `n08e_evaluator_review`.
- **`revision_integrator`**: Update `phase_alignment` to `"phase_08f_revision"`. Update node binding to `n08f_revision`. Update `reads_from` to reference `part_b_assembled_draft.json`. Update `gate_results_confirmed` in checkpoint to include `gate_10a`, `gate_10b`, `gate_10c`, `gate_10d`.

---

## 7. Proposed Skill Catalog Changes

### 7.1 New Skills

```yaml
- id: excellence-section-drafting
  execution_mode: "tapm"
  output_contract: "single_artifact"
  purpose: >
    Draft the Excellence section of the RIA/IA Part B from Phase 2 concept
    refinement, Phase 3 WP structure, and Tier 3 project data. Produces
    excellence_section.json conforming to orch.tier5.excellence_section.v1.
  used_by_agents: [excellence_writer]
  reads_from:
    - docs/tier2a_instrument_schemas/extracted/
    - docs/tier3_project_instantiation/
    - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
    - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
    - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
    - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
  writes_to:
    - docs/tier5_deliverables/proposal_sections/excellence_section.json
  constitutional_constraints:
    - "Must verify budget gate passed before producing content"
    - "Must not fabricate project facts not present in Tier 3"
    - "Must not use Grant Agreement Annex structure"

- id: impact-section-drafting
  execution_mode: "tapm"
  output_contract: "single_artifact"
  purpose: >
    Draft the Impact section from Phase 5 impact architecture, DEC plans,
    and Tier 2B expected impacts. Produces impact_section.json conforming
    to orch.tier5.impact_section.v1.
  used_by_agents: [impact_writer]
  reads_from:
    - docs/tier2a_instrument_schemas/extracted/
    - docs/tier2b_topic_and_call_sources/extracted/
    - docs/tier3_project_instantiation/
    - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
    - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
    - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
  writes_to:
    - docs/tier5_deliverables/proposal_sections/impact_section.json
  constitutional_constraints:
    - "Must verify budget gate passed before producing content"
    - "Must not fabricate impact coverage for unmapped call expected impacts"
    - "Must not use Grant Agreement Annex structure"

- id: implementation-section-drafting
  execution_mode: "tapm"
  output_contract: "single_artifact"
  purpose: >
    Draft the Implementation section from Phase 3 WP structure, Phase 4 Gantt,
    Phase 6 implementation architecture. Produces implementation_section.json
    conforming to orch.tier5.implementation_section.v1.
  used_by_agents: [implementation_writer]
  reads_from:
    - docs/tier2a_instrument_schemas/extracted/
    - docs/tier3_project_instantiation/
    - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
    - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
    - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
    - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
  writes_to:
    - docs/tier5_deliverables/proposal_sections/implementation_section.json
  constitutional_constraints:
    - "Must verify budget gate passed before producing content"
    - "Must not redesign the consortium or WP structure"
    - "Must not use Grant Agreement Annex structure"

- id: cross-section-consistency-check
  execution_mode: "tapm"
  output_contract: "single_artifact"
  purpose: >
    Check cross-section consistency of the three criterion-aligned sections
    and produce the assembled Part B draft. Verifies objectives, WP references,
    partner names, deliverables, milestones, KPIs, impact claims, budget
    references, and terminology are consistent across all three sections.
  used_by_agents: [proposal_integrator]
  reads_from:
    - docs/tier5_deliverables/proposal_sections/
    - docs/tier3_project_instantiation/
    - docs/tier2a_instrument_schemas/application_forms/
  writes_to:
    - docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json
  constitutional_constraints:
    - "Must not silently normalise contradictions"
    - "Must flag all inconsistencies in the consistency_log"
```

### 7.2 Updated Skills

- **`evaluator-criteria-review`**: Update `reads_from` to include `part_b_assembled_draft.json` path. Add support for criterion-scoped review mode (review a single criterion section before assembly) in addition to assembled-draft mode.
- **`proposal-section-traceability-check`**: Add the three new section artifact paths to the section file lookup logic. No schema changes needed since the traceability_footer structure is shared.
- **`constitutional-compliance-check`**: No changes needed; artifact_path is injected by agent runtime.

---

## 8. Required New/Updated .md Agent Files

| File | Action | Key Content |
|------|--------|-------------|
| `.claude/agents/excellence_writer.md` | **CREATE** | Front matter with node_id `n08a_excellence_drafting`, exit_gate `gate_10a_excellence_completeness`. Skill bindings: `excellence-section-drafting`, `proposal-section-traceability-check`, `constitutional-compliance-check`. Budget gate prerequisite (absolute). Output schema contract for `excellence_section.json`. Constitutional review. |
| `.claude/agents/impact_writer.md` | **CREATE** | Front matter with node_id `n08b_impact_drafting`, exit_gate `gate_10b_impact_completeness`. Skill bindings: `impact-section-drafting`, `proposal-section-traceability-check`, `constitutional-compliance-check`. |
| `.claude/agents/implementation_writer.md` | **CREATE** | Front matter with node_id `n08c_implementation_drafting`, exit_gate `gate_10c_implementation_completeness`. Skill bindings: `implementation-section-drafting`, `proposal-section-traceability-check`, `constitutional-compliance-check`. |
| `.claude/agents/proposal_integrator.md` | **CREATE** | Front matter with node_id `n08d_assembly`, exit_gate `gate_10d_cross_section_consistency`. Skill bindings: `cross-section-consistency-check`, `proposal-section-traceability-check`, `constitutional-compliance-check`. |
| `.claude/agents/evaluator_reviewer.md` | **UPDATE** | Change node_id to `n08e_evaluator_review`. Change exit_gate to `gate_11_review_closure` (unchanged ID). Update predecessor from `gate_10_part_b_completeness` to `gate_10d_cross_section_consistency`. Update assembled draft path. |
| `.claude/agents/revision_integrator.md` | **UPDATE** | Change node_id to `n08f_revision`. Update predecessor from `gate_11_review_closure` (unchanged). Update assembled draft path. Update `gate_results_confirmed` list in checkpoint to include gates 10a-10d. |
| `.claude/agents/proposal_writer.md` | **DEPRECATE** | Mark as deprecated. Remove node bindings. Keep file for reference but add deprecation notice. |

---

## 9. Required New/Updated .md Skill Files

| File | Action | Key Content |
|------|--------|-------------|
| `.claude/skills/excellence-section-drafting.md` | **CREATE** | TAPM skill spec. Input: Tier 2A/3/4 (phases 1-3, 7). Output: `excellence_section.json`. Execution spec: verify budget gate, read evaluation criteria for Excellence, draft sub-sections, build traceability footer. Constitutional constraint enforcement. Failure protocol. Schema validation. |
| `.claude/skills/impact-section-drafting.md` | **CREATE** | TAPM skill spec. Input: Tier 2A/2B/3/4 (phases 5, 3, 7). Output: `impact_section.json`. Special: map impact pathways, verify DEC coverage. |
| `.claude/skills/implementation-section-drafting.md` | **CREATE** | TAPM skill spec. Input: Tier 2A/3/4 (phases 3, 4, 6, 7). Output: `implementation_section.json`. Special: WP table generation, Gantt narrative, risk register summary, resource allocation. |
| `.claude/skills/cross-section-consistency-check.md` | **CREATE** | TAPM skill spec. Input: three section artifacts + Tier 3. Output: `part_b_assembled_draft.json`. Execution spec: 12+ cross-checks (objectives, WP refs, partner names, deliverable IDs, milestone IDs, KPIs, impact claims, budget references, terminology, page limits). |
| `.claude/skills/evaluator-criteria-review.md` | **UPDATE** | Add criterion-scoped review mode for per-section review. Update assembled draft path to `part_b_assembled_draft.json`. |
| `.claude/skills/proposal-section-traceability-check.md` | **UPDATE** | Add new artifact paths to lookup. No schema changes. |

---

## 10. Runner/Runtime Changes

### 10.1 `runner/run_context.py`

Update `PHASE_8_NODE_IDS`:

```python
PHASE_8_NODE_IDS: frozenset[str] = frozenset(
    {
        "n08a_excellence_drafting",
        "n08b_impact_drafting",
        "n08c_implementation_drafting",
        "n08d_assembly",
        "n08e_evaluator_review",
        "n08f_revision",
    }
)
```

### 10.2 `runner/gate_result_registry.py`

Add new gate result paths:

```python
GATE_RESULT_PATHS = {
    ...
    # Phase 8 criterion gates
    "gate_10a_excellence_completeness": (
        "phase_outputs/phase8_drafting_review/gate_10a_result.json"
    ),
    "gate_10b_impact_completeness": (
        "phase_outputs/phase8_drafting_review/gate_10b_result.json"
    ),
    "gate_10c_implementation_completeness": (
        "phase_outputs/phase8_drafting_review/gate_10c_result.json"
    ),
    "gate_10d_cross_section_consistency": (
        "phase_outputs/phase8_drafting_review/gate_10d_result.json"
    ),
    # gate_11 and gate_12 paths unchanged
}
```

Remove the `gate_10_part_b_completeness` entry.

### 10.3 `runner/upstream_inputs.py`

Add upstream input entries for the new gates:

```python
UPSTREAM_INPUTS = {
    ...
    "gate_10a_excellence_completeness": [
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json",
        "docs/tier5_deliverables/proposal_sections/excellence_section.json",
    ],
    "gate_10b_impact_completeness": [
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json",
        "docs/tier5_deliverables/proposal_sections/impact_section.json",
    ],
    "gate_10c_implementation_completeness": [
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json",
        "docs/tier5_deliverables/proposal_sections/implementation_section.json",
    ],
    "gate_10d_cross_section_consistency": [
        "docs/tier5_deliverables/proposal_sections/excellence_section.json",
        "docs/tier5_deliverables/proposal_sections/impact_section.json",
        "docs/tier5_deliverables/proposal_sections/implementation_section.json",
        "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
    ],
    "gate_11_review_closure": [
        "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
        "docs/tier5_deliverables/review_packets/review_packet.json",
    ],
    "gate_12_constitutional_compliance": [
        "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json",
        "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
        "docs/tier5_deliverables/final_exports/final_export.json",
    ],
}
```

Remove `gate_10_part_b_completeness` entry.

### 10.4 `runner/agent_runtime.py`

Update `_NODE_AUDITABLE_FALLBACK_DIRS`:

```python
_NODE_AUDITABLE_FALLBACK_DIRS: dict[str, tuple[str, ...]] = {
    "n08a_excellence_drafting": (
        "docs/tier5_deliverables/proposal_sections",
    ),
    "n08b_impact_drafting": (
        "docs/tier5_deliverables/proposal_sections",
    ),
    "n08c_implementation_drafting": (
        "docs/tier5_deliverables/proposal_sections",
    ),
    "n08d_assembly": (
        "docs/tier5_deliverables/assembled_drafts",
    ),
    "n08e_evaluator_review": (
        "docs/tier5_deliverables/review_packets",
        "docs/tier5_deliverables/assembled_drafts",
    ),
    "n08f_revision": (
        "docs/tier5_deliverables/assembled_drafts",
        "docs/tier5_deliverables/proposal_sections",
        "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review",
    ),
}
```

Remove old `n08a_section_drafting`, `n08b_assembly`, `n08c_evaluator_review`, `n08d_revision` entries.

Update `_TIER5_AUDIT_SKILLS` applicability comment to reference new node IDs (the frozenset itself stays the same).

### 10.5 `runner/gate_evaluator.py`

Add new predicate functions to `PREDICATE_REGISTRY`:

- `schema_id_matches(path, expected)` -- deterministic, check `schema_id` field equals `expected`
- `no_unresolved_material_claims(path)` -- semantic, check `validation_status.overall_status != "unresolved"`
- `impact_pathways_covered(section_path, impact_arch_path)` -- coverage, check `impact_pathway_refs` covers all expected impacts
- `implementation_coverage_complete(section_path, wp_path, gantt_path)` -- coverage, check all WP/gantt/milestone/risk refs populated
- `cross_section_consistency(assembled_path, sections_dir, tier3_path)` -- semantic, cross-check consistency

### 10.6 No Changes Required

- `runner/dag_scheduler.py` -- No changes. Phase-scoped execution (`--phase 8`) will automatically pick up the six new nodes since they all have `phase_number: 8`. HARD_BLOCK propagation is driven by `run_context.py`'s `PHASE_8_NODE_IDS`, which is updated above.
- `runner/skill_runtime.py` -- No changes. The three new drafting skills use `single_artifact` output contract (one section file each). The existing `_find_schema_for_path()` will match the new schemas once added to `artifact_schema_specification.yaml`.
- `runner/claude_transport.py` -- No changes.
- `runner/__main__.py` -- No changes. `--phase 8` parsing is integer-based.

---

## 11. Test Plan

### 11.1 Unit Tests -- Runner

| Test | Purpose | File |
|------|---------|------|
| `test_phase8_node_ids_updated` | Verify `PHASE_8_NODE_IDS` contains all 6 new IDs | `tests/test_run_context.py` |
| `test_hard_block_propagation_new_nodes` | Verify HARD_BLOCK freezes all 6 new Phase 8 nodes | `tests/test_run_context.py` |
| `test_gate_result_paths_new_gates` | Verify gate result paths resolve for gates 10a-10d | `tests/test_gate_result_registry.py` |
| `test_upstream_inputs_new_gates` | Verify upstream inputs for gates 10a-10d | `tests/test_upstream_inputs.py` |
| `test_node_auditable_dirs_new_nodes` | Verify fallback dirs for new nodes | `tests/test_agent_runtime.py` |
| `test_manifest_node_registry_parse` | Verify 6 new nodes parsed correctly with phase_number=8 | `tests/test_dag_scheduler.py` |
| `test_phase_scope_returns_6_nodes` | Verify `--phase 8` returns all 6 node IDs | `tests/test_dag_scheduler.py` |
| `test_parallel_fan_out_edges` | Verify n08a/b/c are independently reachable from n07 | `tests/test_dag_scheduler.py` |
| `test_convergent_fan_in_edges` | Verify n08d depends on all three section gates | `tests/test_dag_scheduler.py` |
| `test_terminal_node_n08f` | Verify n08f_revision is the sole terminal node | `tests/test_dag_scheduler.py` |

### 11.2 Unit Tests -- Gate Predicates

| Test | Purpose |
|------|---------|
| `test_schema_id_matches_pass` | Schema matches expected value |
| `test_schema_id_matches_fail` | Schema mismatch detection |
| `test_impact_pathways_covered_all_mapped` | All expected impacts appear in section |
| `test_impact_pathways_covered_missing` | Missing impact detected |
| `test_implementation_coverage_complete` | All references populated |
| `test_implementation_coverage_missing_wp` | Missing WP reference detected |
| `test_cross_section_consistency_pass` | No inconsistencies |
| `test_cross_section_consistency_partner_mismatch` | Partner name inconsistency detected |

### 11.3 Integration Tests -- DAG Execution

| Test | Purpose |
|------|---------|
| `test_phase8_full_dag_dry_run` | Dry run with all Phase 7 gates passed; verify 3 parallel nodes ready |
| `test_phase8_parallel_dispatch` | Verify n08a/b/c are all dispatched in the same iteration |
| `test_phase8_assembly_blocked_until_all_3` | Verify n08d not ready until all three gates pass |
| `test_phase8_budget_gate_hard_block` | Verify budget gate failure freezes all 6 nodes |
| `test_phase8_single_section_failure_does_not_block_others` | Verify n08a failure doesn't block n08b or n08c |
| `test_phase8_terminal_node_release` | Verify n08f release produces `overall_status: pass` |

### 11.4 Backward Compatibility Tests

| Test | Purpose |
|------|---------|
| `test_old_gate_10_id_not_in_registry` | Verify `gate_10_part_b_completeness` is removed from gate result registry |
| `test_old_node_ids_not_in_manifest` | Verify old n08a-d IDs are absent |
| `test_reuse_policy_accepts_old_artifacts` | Verify reuse policy mechanism works for prior-run artifacts |

---

## 12. Migration / Backward-Compatibility Plan

### 12.1 Breaking Changes

1. **Node IDs renamed**: `n08a_section_drafting` -> `n08a_excellence_drafting`, etc. Any prior-run state referencing old node IDs will not match.
2. **Gate ID replaced**: `gate_10_part_b_completeness` removed. Any prior gate result artifacts with this ID are orphaned.
3. **Artifact path changed**: `assembled_draft.json` -> `part_b_assembled_draft.json`. Schema ID changed.
4. **New artifact files**: `excellence_section.json`, `impact_section.json`, `implementation_section.json` did not exist before.

### 12.2 Migration Strategy

**Clean-cut migration on the `phase8_refactor` branch.** Since Phase 8 was `PARTIALLY OPERATIONAL` (not validated end-to-end), there are no production gate results or artifacts to preserve. The migration is:

1. All changes land on `phase8_refactor` branch.
2. Prior Phases 1-7 artifacts and gate results are **fully compatible** -- no changes to their schemas, paths, or gate predicates.
3. The `--phase 8` invocation will dispatch the new 6-node DAG.
4. Any prior-run `phase8_drafting_review/` artifacts from incomplete runs can be manually cleared.

### 12.3 Reuse Policy

The reuse policy mechanism (`run_manifests/<run_id>_reuse_policy.yaml`) allows operators to approve prior-run Tier 4 artifacts for reuse. This mechanism is unchanged and will work with the new node structure since reuse is artifact-path-based, not node-ID-based.

### 12.4 `proposal_writer` Agent Deprecation

The `proposal_writer` agent .md file is retained but marked deprecated. It is no longer bound to any manifest node. The `proposal_writer` entry in `agent_catalog.yaml` is marked with `phase_alignment: "deprecated"`. The three new criterion-aligned writer agents replace its function.

---

## 13. Risks and Open Questions

### 13.1 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Test count increase**: 6 nodes x 5+ tests each = ~30 new tests minimum | Development time | Focus on high-value integration tests first; unit tests for predicates second |
| **Parallel dispatch correctness**: The scheduler's dispatch loop must handle 3 nodes becoming ready simultaneously | Correctness | The scheduler already handles parallel readiness (Phases 4/5 are parallel); verify with integration test |
| **HARD_BLOCK frozenset must be exact**: If `PHASE_8_NODE_IDS` is wrong, HARD_BLOCK fails silently for missing nodes | Constitutional compliance | Test `PHASE_8_NODE_IDS` membership against manifest parse |
| **Cross-section consistency is a new semantic predicate**: Complex to implement correctly | Quality | Start with deterministic cross-checks (partner name matching, WP ID matching) before semantic analysis |
| **`evaluator-criteria-review` currently requires `assembled_draft.json`**: Changing to `part_b_assembled_draft.json` affects its input validation | Regression | Update Step 1.4 of the skill spec and the schema_id check |

### 13.2 Open Questions

1. **Should the three parallel drafting nodes share `phase_number: 8` or use sub-phase numbers?** The current `_parse_phase()` only supports integer phase numbers. Using `phase_number: 8` for all six nodes means `--phase 8` dispatches all of them, which is the expected behavior. No sub-phase parsing is needed.

2. **Should `gate_10_part_b_completeness` be retained as an alias for backward compatibility?** Recommendation: **No.** Phase 8 was not production-validated. A clean break is cleaner than an alias.

3. **Should per-section `<section_id>.json` files (generic `proposal_section.v1` schema) still be produced alongside the criterion-aligned files?** Recommendation: **No.** The criterion-aligned files are the canonical section artifacts. The `all_sections_drafted` predicate used by `gate_12` should be updated to check for the three criterion-aligned files instead.

4. **Should the `evaluator-criteria-review` skill support per-criterion review before assembly (in n08a/b/c)?** Recommendation: **Yes, add a criterion-scoped mode.** This enables self-review during drafting, not just post-assembly review. The skill's current Step 1.4 requires `assembled_draft.json`; add an alternative mode that accepts a single section file.

5. **Does the `checkpoint-publish` skill need to list all four new gate IDs in `gate_results_confirmed`?** Yes. The `phase8_checkpoint.json` schema requires `gate_results_confirmed` to include the budget gate and all Phase 8 gates. Update to: `[gate_09_budget_consistency, gate_10a_excellence_completeness, gate_10b_impact_completeness, gate_10c_implementation_completeness, gate_10d_cross_section_consistency, gate_11_review_closure, gate_12_constitutional_compliance]`.

---

## 14. Recommended Implementation Order

### Phase A: Runner Infrastructure (no Claude invocations needed)

1. **`run_context.py`** -- Update `PHASE_8_NODE_IDS`
2. **`gate_result_registry.py`** -- Add new gate result paths, remove old
3. **`upstream_inputs.py`** -- Add new upstream input entries, remove old
4. **`agent_runtime.py`** -- Update `_NODE_AUDITABLE_FALLBACK_DIRS`
5. **`gate_evaluator.py`** -- Add new predicate functions (`schema_id_matches`, etc.)
6. **Tests for Phase A** -- Unit tests for all runner changes

### Phase B: Manifest and Gate Specification

7. **`artifact_schema_specification.yaml`** -- Add new artifact schemas (excellence, impact, implementation, part_b_assembled_draft)
8. **`gate_rules_library.yaml`** -- Add gates 10a-10d predicates; update gate_11/gate_12
9. **`quality_gates.yaml`** -- Add gate 10a-10d definitions; update gate_11/gate_12
10. **`manifest.compile.yaml`** -- Replace node_registry, edge_registry, gate_registry, artifact_registry entries
11. **`workflow_phases/phase_08_drafting_review.yaml`** -- Rewrite substep definitions
12. **Tests for Phase B** -- Manifest parse tests, DAG topology tests

### Phase C: Agent and Skill Catalog

13. **`agent_catalog.yaml`** -- Add 4 new agents, update 2, deprecate 1
14. **`skill_catalog.yaml`** -- Add 4 new skills, update 2

### Phase D: Agent .md Files

15. **`excellence_writer.md`** -- Create
16. **`impact_writer.md`** -- Create
17. **`implementation_writer.md`** -- Create
18. **`proposal_integrator.md`** -- Create
19. **`evaluator_reviewer.md`** -- Update (if separate file exists; otherwise create)
20. **`revision_integrator.md`** -- Update
21. **`proposal_writer.md`** -- Deprecate

### Phase E: Skill .md Files

22. **`excellence-section-drafting.md`** -- Create
23. **`impact-section-drafting.md`** -- Create
24. **`implementation-section-drafting.md`** -- Create
25. **`cross-section-consistency-check.md`** -- Create
26. **`evaluator-criteria-review.md`** -- Update
27. **`proposal-section-traceability-check.md`** -- Update (if path references change)

### Phase F: Integration Testing and Documentation

28. **Integration tests** -- Full DAG execution tests
29. **`README.md`** -- Update Phase 8 documentation
30. **Registry files** -- Update `schema_registry.json`, `workflow_registry.json`

### Phase G: CLAUDE.md Amendment (requires human approval)

31. **`CLAUDE.md`** -- Amend Section 7 (Phase 8 definition) and Section 8 (gate_10 reference) per Section 14 amendment rules. This step requires explicit human instruction per CLAUDE.md Section 14.5.

---

*Plan produced: 2026-04-25. Awaiting review and approval before implementation.*
