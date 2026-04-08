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

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not use Grant Agreement Annex templates as application form schema.
- Must not invent section constraints not present in the active application form.
- Must not resolve instrument type by assumption; must resolve from `selected_call.json`.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Node Binding

This agent is listed in `agent_catalog.yaml` but has no `agent:` field in any `manifest.compile.yaml` node. It is an auxiliary agent invoked within Phase 1 by `call_analyzer`. The `node_ids` field is therefore empty. This is not a discrepancy; the catalog explicitly states the auxiliary scope.
