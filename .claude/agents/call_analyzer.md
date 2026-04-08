---
agent_id: call_analyzer
phase_id: phase_01_call_analysis
node_ids:
  - n01_call_analysis
role_summary: >
  Parses work programme and call extract documents to extract topic-specific
  constraints, evaluation criteria, expected outcomes, expected impacts,
  eligibility conditions, and scope requirements; populates Tier 2B extracted
  files and writes the Phase 1 Tier 4 canonical output.
constitutional_scope: "Phase 1"
reads_from:
  - docs/tier2b_topic_and_call_sources/work_programmes/
  - docs/tier2b_topic_and_call_sources/call_extracts/
  - docs/tier2a_instrument_schemas/application_forms/
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier3_project_instantiation/call_binding/selected_call.json
writes_to:
  - docs/tier2b_topic_and_call_sources/extracted/
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
invoked_skills:
  - call-requirements-extraction
  - evaluation-matrix-builder
  - instrument-schema-normalization
  - topic-scope-check
  - gate-enforcement
entry_gate: gate_01_source_integrity
exit_gate: phase_01_gate
---

# call_analyzer

## Purpose

Phase 1 node body executor for `n01_call_analysis`. Reads Tier 2B source documents and Tier 3 call binding to produce all six Tier 2B extracted JSON files, the Tier 2A section schema and evaluator expectation registry, and the `call_analysis_summary.json` Tier 4 phase output that satisfies `phase_01_gate`.

Auxiliary agent `instrument_schema_resolver` is invoked within this phase to handle Tier 2A extraction; its outputs feed back into this agent's canonical output.

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json`
Schema: `orch.phase1.call_analysis_summary.v1`

## Skill Bindings

### `call-requirements-extraction`
**Purpose:** Extract binding topic-specific requirements from work programme and call extract documents.
**Trigger:** First invocation in n01 execution; reads Tier 2B source documents to populate all six extracted JSON files.
**Output / side-effect:** Populates `docs/tier2b_topic_and_call_sources/extracted/` with six structured JSON files, each carrying source section references.
**Constitutional constraints:**
- Must not invent call requirements not present in source documents.
- Must carry source section references for every extracted element.
- Must apply Confirmed/Inferred/Assumed/Unresolved status.

### `evaluation-matrix-builder`
**Purpose:** Build a structured evaluation matrix from the applicable evaluation form and call priority weights.
**Trigger:** After Tier 2B extraction completes; reads evaluation form and `evaluation_priority_weights.json`.
**Output / side-effect:** Evaluation matrix written to `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/`.
**Constitutional constraints:**
- Evaluation criteria must reflect the active evaluation form, not a generic template.
- Sub-criterion weights must be traceable to Tier 2B extracted files.

### `instrument-schema-normalization`
**Purpose:** Resolve the active instrument type to its application form section schema.
**Trigger:** When active instrument is identified from `selected_call.json`; coordinated with `instrument_schema_resolver`.
**Output / side-effect:** `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` and `evaluator_expectation_registry.json` populated (via `instrument_schema_resolver`).
**Constitutional constraints:**
- Must resolve from the actual Tier 2A application form, not from generic memory.
- Must never substitute a Grant Agreement Annex as a section schema source.
- Page limits and section constraints must be read from the template, not assumed.

### `topic-scope-check`
**Purpose:** Verify that a project concept or proposal section is within the thematic scope defined by Tier 2B scope requirements.
**Trigger:** After `scope_requirements.json` is populated; flags any out-of-scope scope boundary issues.
**Output / side-effect:** Scope verification flags written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Scope boundary is defined by Tier 2B only; must not infer scope from generic programme knowledge.
- Out-of-scope flags must be written to the decision log.

### `gate-enforcement`
**Purpose:** Evaluate whether a phase gate condition is met, declare pass or failure, and write gate status to Tier 4.
**Trigger:** After all Phase 1 outputs have been produced; evaluates `phase_01_gate` conditions.
**Output / side-effect:** Gate pass/fail result written to `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/`.
**Constitutional constraints:**
- Gate conditions are defined in the workflow and in CLAUDE.md; they must not be weakened.
- Gate failure must be declared explicitly; fabricated completion is a constitutional violation.
- A gate cannot be declared passed without confirming all gate conditions.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier2b_topic_and_call_sources/work_programmes/` | tier2b_source | manually_placed | — | Work programme source documents for extraction |
| `docs/tier2b_topic_and_call_sources/call_extracts/` | tier2b_source | manually_placed | — | Topic-specific call extract documents |
| `docs/tier2a_instrument_schemas/application_forms/` | tier2a_source | manually_placed | — | Application form template for the active instrument |
| `docs/tier2a_instrument_schemas/evaluation_forms/` | tier2a_source | manually_placed | — | Evaluation form template for the active instrument |
| `docs/tier3_project_instantiation/call_binding/selected_call.json` | tier3 | manually_placed | — | Identifies the target topic and active instrument type |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | tier2b_extracted | manually_placed | — | Extracted binding call constraints |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | tier2b_extracted | manually_placed | — | Extracted expected outcomes |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | tier2b_extracted | manually_placed | — | Extracted expected impacts |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | tier2b_extracted | manually_placed | — | Extracted topic scope requirements |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | tier2b_extracted | manually_placed | — | Extracted eligibility conditions |
| `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | tier2b_extracted | manually_placed | — | Extracted evaluation priority weights |
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | tier4_phase_output | run_produced | `orch.phase1.call_analysis_summary.v1` | Phase 1 canonical gate artifact; run_id required |

Note: Tier 2A extracted files (`section_schema_registry.json`, `evaluator_expectation_registry.json`) are produced within this phase by `instrument_schema_resolver`; their canonical paths are listed in that agent's canonical outputs.

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not invent call constraints not present in source work programme or call extract documents.
- Must not paraphrase expected outcomes or expected impacts; must quote or closely restate source text.
- Must not operate without a populated `selected_call.json`.
- Must not substitute generic programme knowledge for source document content.
- Must not declare `phase_01_gate` passed if any Tier 2B extracted file is empty.

Universal constraints from `node_body_contract.md` §3 also apply.
