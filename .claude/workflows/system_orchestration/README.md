# system_orchestration — Workflow Package

**Version:** 1.1
**Constitutional authority:** `CLAUDE.md` (authority_hierarchy_position: 8)
**DAG-runner entry point:** `manifest.compile.yaml`

---

## Package Structure

This directory is the canonical workflow specification for the Horizon Europe Proposal Orchestration System. It supersedes the monolithic `.claude/workflows/system_orchestration.yaml` (v1.0), which is retained as a reference artifact only.

```
system_orchestration/
├── README.md                         # This file
├── meta.yaml                         # Package identity, constitutional authority, instrument scope, source manifest
├── global_rules.yaml                 # Global execution rules and forbidden patterns
├── tier_bindings.yaml                # Tier model: paths, roles, read/write constraints
├── quality_gates.yaml                # All 12 quality gates
├── agent_catalog.yaml                # 16 agent definitions with scope and must_not constraints
├── skill_catalog.yaml                # 19 skill definitions with constitutional constraints
├── state_rules.yaml                  # State durability, checkpoint, decision logging rules
├── integration_rules.yaml            # Lump Sum Budget Planner integration rules (v1.1 corrected)
├── design_notes.yaml                 # Design rationale and architectural decisions
├── workflow_phases/
│   ├── phase_01_call_analysis.yaml
│   ├── phase_02_concept_refinement.yaml
│   ├── phase_03_wp_design.yaml
│   ├── phase_04_gantt_milestones.yaml
│   ├── phase_05_impact_architecture.yaml
│   ├── phase_06_implementation_architecture.yaml
│   ├── phase_07_budget_gate.yaml     # Phase 7 semantic correction applied (see below)
│   └── phase_08_drafting_review.yaml # Contains substeps 08a–08d
└── manifest.compile.yaml             # Compiled DAG manifest (DAG-runner entry point)
```

---

## Constitutional Hierarchy

This workflow package is subordinate to `CLAUDE.md`. In all interpretive conflicts:

```
CLAUDE.md  >  this workflow  >  agent definitions  >  skill definitions  >  agent memory
```

Any provision of this workflow that conflicts with `CLAUDE.md` is invalid. Conflicts must be logged and resolved; they must not be silently resolved in favour of the workflow.

---

## Phase Sequence and Gate Logic

The workflow executes as a DAG. All gates are blocking. Gate failure is a valid output; fabricated completion is a constitutional violation.

| Phase | Node ID | Agent | Exit Gate |
|-------|---------|-------|-----------|
| 1 — Call Analysis | n01 | call_analyzer | phase_01_gate |
| 2 — Concept Refinement | n02 | concept_refiner | phase_02_gate |
| 3 — WP Design & Dependency Mapping | n03 | wp_designer + dependency_mapper | phase_03_gate |
| 4 — Gantt & Milestones | n04 | gantt_designer | phase_04_gate |
| 5 — Impact Architecture | n05 | impact_architect | phase_05_gate |
| 6 — Implementation Architecture | n06 | implementation_architect | phase_06_gate |
| 7 — Budget Gate | n07 | budget_gate_validator | gate_09_budget_consistency |
| 8a — Section Drafting | n08a | proposal_writer | gate_10_part_b_completeness |
| 8b — Assembly | n08b | proposal_writer | gate_10_part_b_completeness |
| 8c — Evaluator Review | n08c | evaluator_reviewer | gate_11_review_closure |
| 8d — Revision | n08d | revision_integrator | gate_12_constitutional_compliance |

**Parallel paths:** Phase 4 and Phase 5 can proceed concurrently after Phase 3. Phase 6 requires Phases 3, 4, and 5. Phase 5 requires both Phase 2 and Phase 3 gates to have passed (edges e02_to_05 + e03_to_05 with additional_condition: phase_03_gate); it is not independently parallel after Phase 2.

---

## Phase 7 Semantic Correction (v1.0 → v1.1)

The monolithic `system_orchestration.yaml` (v1.0) contained a `hold_behavior` key in Phase 7 and a `response_absent` failure mode classified as a non-failing "budget hold" state. This conflicted with:

- **CLAUDE.md §8.4:** Budget gate must pass before Phase 8 finalization.
- **CLAUDE.md §7 (Phase 7 gate condition):** Requires a validated budget response to be present.

**Correction applied in v1.1:**

- `hold_behavior` key removed from `phase_07_budget_gate.yaml`.
- `response_absent` in `integration_rules.yaml` reclassified as a **blocking gate failure**.
- `design_notes.yaml` updated to document the removal of the hold/failure distinction.
- `manifest.compile.yaml` gate_09 sets `absent_artifacts_behavior: blocking_gate_failure`.
- `agent_catalog.yaml` budget_gate_validator `must_not` list includes: `"Treat absence of a response as a non-failing hold state"`.

**Effect:** Absent budget artifacts in `docs/integrations/lump_sum_budget_planner/received/` always produce a blocking gate failure in all compiled representations. Phase 8 cannot proceed in any mode — preparation or finalization — until the budget gate passes.

---

## How to Amend This Package

1. Identify the source file containing the concern to amend (see package structure above).
2. Read `CLAUDE.md` §14 to confirm the amendment is constitutionally admissible.
3. Edit the relevant source file.
4. If the amendment affects phase definitions, gate conditions, agent scopes, or integration rules, review `CLAUDE.md` for alignment.
5. Regenerate `manifest.compile.yaml` to reflect the amended source state.
6. Log the amendment decision in `docs/tier4_orchestration_state/decision_log/`.

**Amendments must be made by explicit human instruction.** Agents and skills may not autonomously amend this workflow package.

---

## Migration Note

The monolithic `.claude/workflows/system_orchestration.yaml` (v1.0) is superseded by this package. It is retained as a historical reference. When operating this system:

- Use `manifest.compile.yaml` as the DAG-runner entry point.
- Use the source files in this directory for reading, amending, and auditing.
- Do not use the monolithic file as the source of truth; it contains the uncorrected Phase 7 hold_behavior that this package corrects.
