---
agent_id: proposal_writer
phase_id: phase_08_drafting_and_review
node_ids:
  - n08a_section_drafting
  - n08b_assembly
role_summary: >
  Drafts individual proposal sections and assembles them into a coherent whole;
  writes in evaluator-oriented language; applies traceability to Tier 1-4 sources
  throughout; does not reference budget figures not validated through Phase 7 gate.
constitutional_scope: "Phase 8a and Phase 8b"
reads_from:
  - docs/tier2a_instrument_schemas/application_forms/
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier3_project_instantiation/
  - docs/tier4_orchestration_state/phase_outputs/
writes_to:
  - docs/tier5_deliverables/proposal_sections/
  - docs/tier5_deliverables/assembled_drafts/
  - docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/
invoked_skills:
  - proposal-section-traceability-check
  - evaluator-criteria-review
  - constitutional-compliance-check
entry_gate: null
exit_gate: gate_10_part_b_completeness
---

# proposal_writer

## Purpose

Phase 8 node body executor for `n08a_section_drafting` and `n08b_assembly`. Drafts all proposal sections required by the active application form (Tier 2A) using project data from Tier 3 and phase outputs from Tier 4. Assembles drafted sections into a complete `assembled_draft.json`.

Requires `gate_09_budget_consistency` to have passed before any Phase 8 activity begins (CLAUDE.md §8.4, §13.4 — **unconditional**).

## Node Execution Contexts

- **n08a_section_drafting**: Produces per-section draft artifacts in `docs/tier5_deliverables/proposal_sections/`. Each section file conforms to schema `orch.tier5.proposal_section.v1`.
- **n08b_assembly**: Reads all drafted sections, produces `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` (schema: `orch.tier5.assembled_draft.v1`).

## Canonical Outputs

- Per section: `docs/tier5_deliverables/proposal_sections/<section_id>.json` — Schema: `orch.tier5.proposal_section.v1`
- Assembly: `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` — Schema: `orch.tier5.assembled_draft.v1`

## Note on Catalog / Manifest Scope Discrepancy

`agent_catalog.yaml` states `constitutional_scope: "Phase 8a, Phase 8b, and Phase 8d"`. However, `manifest.compile.yaml` binds `n08d_revision` to `revision_integrator`, not `proposal_writer`. **The manifest governs**. This agent's `node_ids` are therefore `[n08a_section_drafting, n08b_assembly]`. The catalog entry for Phase 8d coverage is superseded by the manifest node binding. This discrepancy is recorded here for traceability.

## Budget Gate Prerequisite (Absolute)

`gate_09_budget_consistency` must have passed. No Phase 8 activity of any kind — including preparatory drafting — may commence before this gate passes. This is a constitutional requirement (CLAUDE.md §8.4, §13.4), not a workflow preference.

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 5–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not introduce claims not grounded in Tier 1-4 state.
- Must not reference budget figures not validated through Phase 7 gate.
- Must not fill data gaps with fabricated content.
- Must not write to satisfy grant agreement annex formatting requirements.
- Must not finalize budget-dependent sections before Phase 7 gate has passed.

Universal constraints from `node_body_contract.md` §3 also apply.
