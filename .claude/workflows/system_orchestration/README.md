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
├── manifest.compile.yaml             # Compiled DAG manifest (DAG-runner entry point)
├── artifact_schema_specification.yaml  # Field-level schemas for all 13 canonical artifact types
├── gate_rules_library.yaml           # Gate rules library: all 11 gates, 97 predicates
└── gate_rules_library_plan.md        # Implementation plan (reference only)
```

The runner implementation lives at the repository root (not inside this package directory):

```
runner/                               # DAG-runner implementation package
├── __init__.py                       # Runner package root / implementation sequence note
├── paths.py                          # Repository-root discovery and path resolution
├── versions.py                       # Manifest/library/constitution version constants
├── gate_result_registry.py           # §6.3 gate result path table (gate_id → tier4-relative path)
├── upstream_inputs.py                # Gate freshness: gate_id → upstream required input paths
└── predicates/
    ├── __init__.py                   # Predicate API exports
    ├── types.py                      # PredicateResult + failure-category constants
    ├── file_predicates.py            # Step 3: exists, non_empty, non_empty_json, dir_non_empty
    └── gate_pass_predicates.py       # Step 4: gate_pass_recorded
tests/
├── conftest.py                       # repo_root fixture
└── runner/predicates/
    ├── test_file_predicates.py       # Step 3 unit tests (55 tests)
    └── test_gate_pass_predicates.py  # Step 4 unit tests (9 tests)
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

**Directory argument rule:** Directory paths appear in the workflow package only in narrowly defined cases: source admissibility checks, external integration checks, section-collection predicates, and semantic scope arguments. Deterministic validation of structured workflow state operates on canonical artifact JSON files, not directories.

## Runner Implementation Status

The workflow package is now partially executable.

**Completed implementation steps**
- **Step 1 — Artifact schema specification** completed in `artifact_schema_specification.yaml`
- **Step 2 — Gate rules library scaffolding** completed in `gate_rules_library.yaml`
- **Step 3 — File predicates** completed in `runner/predicates/file_predicates.py`
- **Step 4 — Gate-pass predicate** completed in `runner/predicates/gate_pass_predicates.py`

**Current executable predicate layer**
The following predicates are implemented and tested:

File predicates (Step 3):
- `exists(path)`
- `non_empty(path)`
- `non_empty_json(path)`
- `dir_non_empty(path)`

Gate-pass predicate (Step 4):
- `gate_pass_recorded(gate_id, run_id, tier4_root, *, repo_root=None)`

Supporting modules added in Step 4:
- `runner/versions.py` — `MANIFEST_VERSION`, `LIBRARY_VERSION`, `CONSTITUTION_VERSION` constants
- `runner/gate_result_registry.py` — maps gate_id → tier4-relative canonical gate result path (§6.3)
- `runner/upstream_inputs.py` — maps gate_id → upstream artifact paths for freshness checking

All five failure categories are in use across the implemented predicates:
- `MISSING_MANDATORY_INPUT` — file/directory absent, gate result absent, unknown gate_id
- `MALFORMED_ARTIFACT` — invalid JSON, missing required fields, bad timestamps
- `STALE_UPSTREAM_MISMATCH` — run_id mismatch, manifest_version mismatch, freshness violation
- `POLICY_VIOLATION` — recorded gate status is not "pass"
- `CROSS_ARTIFACT_INCONSISTENCY` — (reserved for Steps 5–7)

**Current non-goals**
The repository does **not** yet implement:
- schema predicates
- source reference predicates
- coverage predicates
- cycle predicates
- timeline predicates
- semantic predicate dispatch
- full `evaluate_gate(...)`
- GateResult artifact writing
- run manifest / reuse policy runtime handling

**Test status**
- Step 3 file predicates: 55 tests in `tests/runner/predicates/test_file_predicates.py`
- Step 4 gate-pass predicate: 9 tests in `tests/runner/predicates/test_gate_pass_predicates.py`

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

The package now also includes an incremental runner implementation under `runner/`; this code is subordinate to the workflow/package contracts and does not replace `manifest.compile.yaml` as the orchestration entry point.

- Use `manifest.compile.yaml` as the DAG-runner entry point.
- Use the source files in this directory for reading, amending, and auditing.
- Do not use the monolithic file as the source of truth; it contains the uncorrected Phase 7 hold_behavior that this package corrects.
