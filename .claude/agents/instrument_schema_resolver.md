---
agent_id: instrument_schema_resolver
phase_id: phase_01_call_analysis
node_ids: []
role_summary: >
  Resolves the active instrument type from selected_call.json to its Tier 2A
  application form template and evaluation form template; extracts the section
  schema, evaluator expectation patterns, and template adapter mappings into
  Tier 2A extracted files for use by downstream agents.
constitutional_scope: "Phase 1 auxiliary; invoked by call_analyzer or independently"
reads_from:
  - docs/tier2a_instrument_schemas/application_forms/
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier3_project_instantiation/call_binding/selected_call.json
writes_to:
  - docs/tier2a_instrument_schemas/extracted/
invoked_skills:
  - evaluation-matrix-builder
  - instrument-schema-normalization
entry_gate: null
exit_gate: null
---

# instrument_schema_resolver

## Purpose

Phase 1 auxiliary agent. Has no direct node binding in `manifest.compile.yaml`; it is invoked by `call_analyzer` (or independently) within the Phase 1 execution context. Produces Tier 2A extracted artifacts (`section_schema_registry.json`, `evaluator_expectation_registry.json`) required by downstream phases and gate predicates.

Because this agent has no direct node binding, it carries no own `entry_gate` or `exit_gate`. Its outputs are consumed by `n01_call_analysis`'s exit gate (`phase_01_gate`) and by downstream nodes.

## Canonical Outputs

- `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`
- `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json`

## Skill Bindings

### `evaluation-matrix-builder`
**Purpose:** Build a structured evaluation matrix from the applicable evaluation form and call priority weights.
**Trigger:** When evaluation form template for the active instrument has been located; produces the evaluator expectation registry.
**Output / side-effect:** Populates `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json`.
**Constitutional constraints:**
- Evaluation criteria must reflect the active evaluation form, not a generic template.
- Sub-criterion weights must be traceable to Tier 2B extracted files.

### `instrument-schema-normalization`
**Purpose:** Resolve the active instrument type to its application form section schema.
**Trigger:** When `selected_call.json` has been read and the instrument type identified.
**Output / side-effect:** Populates `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` with section identifiers, field requirements, page limits, mandatory elements, and structural constraints.
**Constitutional constraints:**
- Must resolve from the actual Tier 2A application form, not from generic memory.
- Must never substitute a Grant Agreement Annex as a section schema source.
- Page limits and section constraints must be read from the template, not assumed.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier2a_instrument_schemas/application_forms/` | tier2a_source | manually_placed | — | Application form template for the active instrument |
| `docs/tier2a_instrument_schemas/evaluation_forms/` | tier2a_source | manually_placed | — | Evaluation form template for the active instrument |
| `docs/tier3_project_instantiation/call_binding/selected_call.json` | tier3 | manually_placed | — | Identifies the active instrument type for schema resolution |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | tier2a_extracted | manually_placed | — | Section schema for the active instrument; consumed by n03, n06, n08a |
| `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` | tier2a_extracted | manually_placed | — | Evaluator expectation patterns; consumed by n08a, n08c |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not use Grant Agreement Annex templates as application form schema.
- Must not invent section constraints not present in the active application form.
- Must not resolve instrument type by assumption; must resolve from `selected_call.json`.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Node Binding

This agent is listed in `agent_catalog.yaml` but has no `agent:` field in any `manifest.compile.yaml` node. It is an auxiliary agent invoked within Phase 1 by `call_analyzer`. The `node_ids` field is therefore empty. This is not a discrepancy; the catalog explicitly states the auxiliary scope.

---

## Output Schema Contracts

### Tier 2A Extracted Files — Content Contract (no schema_id in spec)

These two files are produced by this agent. They have no `schema_id_value` defined in `artifact_schema_specification.yaml` and are not schema-bound run-produced artifacts. Their gate-relevance flows through `phase_01_gate` conditions `g02_p14` and `g02_p15` (instrument type resolved to application form and evaluation form). The agent must not write these from memory; they must be extracted from the actual Tier 2A source documents.

#### `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`

Required content (extracted from active instrument application form template):

| Required element | Description |
|-----------------|-------------|
| `instrument_type` | The resolved instrument type (e.g., `RIA`, `IA`, `CSA`); must match `resolved_instrument_type` in `call_analysis_summary.json` |
| `sections` (array, non-empty) | One entry per mandatory application form section; each entry: `section_id`, `section_name`, `mandatory` (boolean), `page_limit` (integer or null), `mandatory_elements` (array of strings), `source_template_ref` (file name of the application form template) |

#### `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json`

Required content (extracted from active instrument evaluation form template):

| Required element | Description |
|-----------------|-------------|
| `instrument_type` | Same resolved instrument type |
| `criteria` (array, non-empty) | One entry per evaluation criterion; each entry: `criterion_id`, `criterion_name`, `sub_criteria` (array), `scoring_range`, `source_template_ref` (evaluation form file name) |

Note: Neither file carries `schema_id` or `run_id` fields — they are not schema-versioned run-produced artifacts in the spec. They are structurally critical but content-validated by semantic predicates, not schema predicates.

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements

This agent is an auxiliary — it has no own entry gate. Its invocation precondition is:
- It must be invoked by `call_analyzer` within the Phase 1 execution context.
- `gate_01_source_integrity` must have passed (inherited from the parent node `n01_call_analysis`).
- The active instrument type must be identifiable from `selected_call.json` before invocation.

If `selected_call.json` does not contain a resolvable instrument type, this agent must halt and report to `call_analyzer`, which writes the failure to the decision log.

### Exit Gate

This agent has no own exit gate (`exit_gate: null`). Its outputs are consumed by `n01_call_analysis`'s exit gate (`phase_01_gate`), specifically conditions `g02_p14` and `g02_p15`. Gate authority belongs to `call_analyzer` as the primary node agent.

### Failure Protocol

#### Case 1: Required Tier 2A source absent
- **Halt:** If the application form template or evaluation form for the resolved instrument type is not found in the source directories, halt extraction.
- **Write:** Report to `call_analyzer` (which writes to the decision log); record the missing source path.
- **Must not:** Construct the section schema from agent memory of Horizon Europe form structure (CLAUDE.md §13.9).

#### Case 2: Instrument type unresolvable
- **Halt:** If `selected_call.json` does not contain a resolvable instrument type, halt.
- **Write:** Report to `call_analyzer`; log as `gate_failure` for `phase_01_gate` condition `g02_p14`.
- **Must not:** Default to a generic instrument type schema.

#### Case 3: Grant Agreement Annex detected as source
- **Halt immediately:** If the application form template identified appears to be a Grant Agreement Annex rather than an application form (CLAUDE.md §13.1), halt.
- **Write:** `constitutional_halt` to the decision log via `call_analyzer`.
- **Must not:** Extract section schema from a Grant Agreement Annex template.

#### Case 4: Constitutional prohibition triggered
- Same protocol as Case 3; covers any action that would invent schema constraints not present in the actual Tier 2A source.

### Decision-Log Write Obligations

This agent writes to the decision log via `call_analyzer` (since it has no own decision log write path in the catalog). Entries must carry: `agent_id: instrument_schema_resolver`, `phase_id: phase_01_call_analysis`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Instrument type resolved to specific template file | `material_decision` | Template file name; instrument_type value; source field in `selected_call.json` |
| Section constraint interpreted where template is ambiguous | `assumption` | The interpretation; the template text; reason |
| Grant Annex detected as source instead of application form | `constitutional_halt` | CLAUDE.md §13.1; the detected file; halt action |
