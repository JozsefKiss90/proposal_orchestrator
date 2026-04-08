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

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 5–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not invent call constraints not present in source work programme or call extract documents.
- Must not paraphrase expected outcomes or expected impacts; must quote or closely restate source text.
- Must not operate without a populated `selected_call.json`.
- Must not substitute generic programme knowledge for source document content.
- Must not declare `phase_01_gate` passed if any Tier 2B extracted file is empty.

Universal constraints from `node_body_contract.md` §3 also apply.
