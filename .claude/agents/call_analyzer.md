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

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not invent call constraints not present in source work programme or call extract documents.
- Must not paraphrase expected outcomes or expected impacts; must quote or closely restate source text.
- Must not operate without a populated `selected_call.json`.
- Must not substitute generic programme knowledge for source document content.
- Must not declare `phase_01_gate` passed if any Tier 2B extracted file is empty.

Universal constraints from `node_body_contract.md` §3 also apply.

---

## Output Schema Contracts

### 1. `call_analysis_summary.json` — Primary Canonical Output

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json`
**Schema ID:** `orch.phase1.call_analysis_summary.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.phase1.call_analysis_summary.v1"` — no other value permitted |
| `run_id` | string | **yes** | Propagated verbatim from the invoking DAG-runner run context (UUID established at scheduler startup) |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps `valid` or `invalid` after `phase_01_gate` evaluation; agent must not write this field |
| `resolved_instrument_type` | string | **yes** | Read from `docs/tier3_project_instantiation/call_binding/selected_call.json` instrument_type field; must match an entry in `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` |
| `evaluation_matrix` | object | **yes** | Constructed from the active Tier 2A evaluation form + `evaluation_priority_weights.json`; must not be empty `{}`; each entry requires: `criterion_id` (from evaluation form label), `criterion_name` (from evaluation form), `source_section` (Tier 2B section identifier), `source_document` (Tier 2B file name); `weight` is optional (null if unweighted) |
| `compliance_checklist` | array | **yes** | Extracted from Tier 2B `eligibility_conditions.json` and `call_constraints.json`; must not be empty; each entry requires: `requirement_id`, `description`, `status` (enum: confirmed / requires_review / not_applicable), `source_section`, `source_document` |
| `call_analysis_notes` | string | no | Optional free-text; not gate-evaluated |

### 2. Tier 2B Extracted Files — Content Contract (no schema_id in spec)

These six files are produced by this agent within the Phase 1 execution context. They have no `schema_id_value` defined in `artifact_schema_specification.yaml` and are not schema-bound by the runner. Their gate-relevance is through `phase_01_gate` conditions (`g02_p01`–`g02_p12`). Each file must be non-empty and carry source section references on every extracted element.

| Canonical path | Required content |
|----------------|-----------------|
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | Binding call constraints; each entry: `constraint_id`, `description`, `source_section`, `source_document` |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | Expected outcomes; each entry: `outcome_id`, `description`, `source_section`, `source_document` |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Expected impacts; each entry: `impact_id`, `description`, `source_section`, `source_document` |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | Topic scope boundary; each entry: `scope_id`, `description`, `source_section`, `source_document` |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | Eligibility requirements; each entry: `condition_id`, `description`, `source_section`, `source_document` |
| `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | Evaluation weights; each entry: `criterion_id`, `weight` (nullable), `source_section`, `source_document` |

Note: Tier 2A extracted files (`section_schema_registry.json`, `evaluator_expectation_registry.json`) are produced by `instrument_schema_resolver` within this phase; their output contracts are defined in that agent's file.

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements

**Entry gate:** `gate_01_source_integrity` — evaluated by the DAG scheduler before this node body is invoked. This agent cannot begin execution until the entry gate has passed. If the entry gate fails, the scheduler does not invoke this agent; the fail_action is "Halt workflow; report missing sources to human operator."

Entry gate checks (source: `manifest.compile.yaml` gate_registry, `quality_gates.yaml`):
- `selected_call.json` present and non-empty
- At least one work programme document present in `docs/tier2b_topic_and_call_sources/work_programmes/`
- At least one call extract matching the topic code present
- Application form template for the resolved instrument type present
- Evaluation form for the resolved instrument type present

**No upstream DAG edges:** `n01_call_analysis` is the first node in the DAG; there are no predecessor edges.

### Exit Gate

**Exit gate:** `phase_01_gate` — evaluated after this agent writes all canonical outputs.

Gate conditions this agent is responsible for satisfying (source: `manifest.compile.yaml` phase_01_gate, `quality_gates.yaml`):
1. All six Tier 2B extracted JSON files non-empty with source section references (`g02_p01`–`g02_p12`)
2. `selected_call.json` confirmed populated and consistent with Tier 2B source (`g02_p13`)
3. Instrument type resolved to a Tier 2A application form and evaluation form (`g02_p14`, `g02_p15`)
4. Evaluation matrix written to Tier 4 phase output (`g02_p16`)
5. Compliance checklist written to Tier 4 phase output (`g02_p17`)

Gate result written to `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json` (schema: `orch.gate_result.v1`) by the runner after evaluation. This agent produces the artifacts; the runner stamps the gate result.

Blocking edges on pass: `e01_to_02` (unblocks `n02_concept_refinement`).

### Failure Protocol

#### Case 1: Gate condition not met (`phase_01_gate` fails)
- **Halt:** Do not signal downstream readiness; do not proceed.
- **Write:** `call_analysis_summary.json` with `gate_pass_declaration` equivalent content identifying which conditions failed and why (e.g., which Tier 2B file is empty, which source section reference is missing).
- **Decision log:** Entry with `decision_type: gate_failure`; list each failed condition and its predicate reference; include source document references.
- **Must not:** Fabricate or pad content to satisfy a gate condition. Must not declare gate passed with any condition unmet.

#### Case 2: Required input absent
- **Halt:** If `selected_call.json` is absent or empty, or if source directories are empty — halt before any extraction.
- **Write:** Entry to `docs/tier4_orchestration_state/decision_log/` identifying the missing canonical path and what it blocks.
- **Decision log:** Entry with `decision_type: gate_failure`; identify the entry gate condition that cannot be satisfied.
- **Must not:** Substitute generic programme knowledge for absent source documents (CLAUDE.md §13.9). Must not infer the topic from agent memory.

#### Case 3: Mandatory predecessor gate not passed
- Not applicable as first node; entry gate is evaluated by the scheduler. Documented for constitutional completeness: if somehow invoked without a passed entry gate, halt immediately and write `decision_type: constitutional_halt` to the decision log.

#### Case 4: Constitutional prohibition triggered
- **Halt immediately** if any extraction step would require inventing call constraints (CLAUDE.md §13.2), paraphrasing Tier 2B material in a way that changes scope meaning, or substituting agent memory for source documents (CLAUDE.md §13.9).
- **Write:** Entry to `docs/tier4_orchestration_state/decision_log/` with `decision_type: constitutional_halt`; name the triggered prohibition section.
- **Must not:** Produce partial output and proceed. Must not write an optimistic summary for content that could not be faithfully extracted.

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry must include: `agent_id: call_analyzer`, `phase_id: phase_01_call_analysis`, `run_id` (from run context), `timestamp` (ISO 8601), `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Instrument type resolved from `selected_call.json` | `material_decision` | Resolved instrument type value; source file and field name |
| Extraction where source text is ambiguous and an interpretation is adopted | `assumption` | The interpretation adopted; the exact source text; the reason for this reading |
| Conflict between work programme and call extract on a constraint or scope element | `scope_conflict` | Both source references; which prevailed; constitutional authority for that choice |
| `phase_01_gate` passes | `gate_pass` | Gate ID `phase_01_gate`; all six Tier 2B files confirmed non-empty; run_id |
| `phase_01_gate` fails | `gate_failure` | Gate ID; which conditions failed; what is required to resolve before re-run |
| Constitutional halt triggered | `constitutional_halt` | CLAUDE.md section triggered; action halted; what would have been required |

---

## Constitutional Review

### 1. Scope compliance

`reads_from` and `writes_to` in the front matter exactly match `agent_catalog.yaml`. No body text implies access to any path outside those declarations. The Tier 2A extracted files (`section_schema_registry.json`, `evaluator_expectation_registry.json`) are explicitly noted as produced by `instrument_schema_resolver` within this phase — this agent does not claim write authority over them. The canonical writes within `docs/tier2b_topic_and_call_sources/extracted/` are bounded to the six named files produced by this phase. No undeclared path access is implied.

### 2. Manifest authority compliance

Node binding is `n01_call_analysis`. Entry gate (`gate_01_source_integrity`) and exit gate (`phase_01_gate`) match `manifest.compile.yaml` exactly. The `gate-enforcement` skill is listed in the manifest under `n01_call_analysis` — it is legitimately used by this agent. Gate result artifacts (`gate_result.json`) are described as written by the runner after evaluation — not self-declared by this agent. The agent body correctly states the runner stamps `artifact_status`; the agent must not write that field. Invocation of `instrument_schema_resolver` as an auxiliary agent within Phase 1 is consistent with the manifest `skills` list and the catalog scope.

### 3. Forbidden-action review against CLAUDE.md §13

- **§13.2 — Fabricated call constraints:** The must_not list explicitly prohibits inventing call constraints not present in source work programme or call extract documents. The extraction section reinforces this: every extracted element must carry `source_section` and `source_document`. Risk: low.
- **§13.3 — Fabricated project facts:** This agent does not write project facts; it extracts call-side data. The only project-side artifact it reads is `selected_call.json` to identify the topic and instrument type — it does not invent content in that file. Risk: low.
- **§13.9 — Generic programme knowledge substitution:** The must_not list explicitly prohibits substituting generic programme knowledge for source document content. Failure protocol Case 4 explicitly halts if this would be required. Risk: low.
- **§13.1 — Grant Agreement Annex as schema source:** The `instrument-schema-normalization` skill constraint and the `instrument_schema_resolver` auxiliary agent both include explicit prohibitions against using Grant Agreement Annex templates. Risk: low.
- **Budget-dependent content before Phase 7:** This agent does not produce Tier 5 content. No budget-related content is produced. Not applicable.
- **§13.5 — Durable decisions in memory only:** Decision-log write obligations table covers all material decision events. Risk: low.
- **§13.7 — Silent gate bypass:** The gate-enforcement skill and failure protocols prohibit fabricated completion. The gate condition checklist is fully enumerated. Risk: low.
- **§13.10 — Tier 5 outputs not traceable:** This agent does not produce Tier 5 outputs. Not applicable.

### 4. Must-not integrity

All five must_not items from `agent_catalog.yaml` are present verbatim in the Must-Not Constraints section. The Step 6–7 additions (output schema contracts, gate awareness, failure behaviour) do not weaken any must_not. The gate awareness section's "Fabricated Completion" language is additive. The universal node_body_contract §3 reference preserves any universal constraints. No weakening detected.

**Universal node_body_contract constraint:** `artifact_status` must not be written by the agent — confirmed in Output Schema Contracts field table (marked "NO — absent at write time").

### 5. Conflict status

Constitutional review result: no conflict identified
