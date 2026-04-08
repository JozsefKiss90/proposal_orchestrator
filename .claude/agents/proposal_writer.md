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

## Skill Bindings

### `proposal-section-traceability-check`
**Purpose:** Verify that every material claim in a proposal section is traceable to a named Tier 1–4 source; apply Confirmed/Inferred/Assumed/Unresolved status.
**Trigger:** Invoked in both n08a and n08b contexts: after each section draft (n08a) and after assembly (n08b) to verify the assembled draft.
**Output / side-effect:** Traceability status applied to all claims; unattributed assertions flagged in `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Unattributed claims must be flagged, not silently accepted as Confirmed.
- Confirmed status requires naming the specific source artifact.

### `evaluator-criteria-review`
**Purpose:** Assess proposal content against the scoring logic of the applicable evaluation criterion; identify weaknesses by severity.
**Trigger:** During n08a section drafting; self-review of each section draft against evaluation criteria before finalizing.
**Output / side-effect:** Weakness identification used to strengthen drafts; results can feed into `docs/tier5_deliverables/review_packets/` if a pre-assembly review is requested.
**Constitutional constraints:**
- Evaluation must apply the active instrument evaluation criteria only.
- Must not evaluate against grant agreement annex requirements.
- Weakness severity (critical/major/minor) must be assigned to each finding.

### `constitutional-compliance-check`
**Purpose:** Verify that a phase output or deliverable does not violate any prohibition in CLAUDE.md.
**Trigger:** Before finalizing any section (n08a) and before completing assembly (n08b); checks for fabricated facts, budget-dependent content without gate, and grant annex schema usage.
**Output / side-effect:** Compliance check written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Must check against CLAUDE.md Section 13 prohibitions as a minimum.
- Constitutional violations must be flagged; they must not be silently resolved.
- CLAUDE.md governs this skill; this skill does not govern CLAUDE.md.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier2a_instrument_schemas/application_forms/` | tier2a_source | manually_placed | — | Application form template defining sections to draft |
| `docs/tier2a_instrument_schemas/evaluation_forms/` | tier2a_source | manually_placed | — | Evaluation form for self-review during drafting |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | tier2a_extracted | manually_placed | — | Section identifiers, page limits, and structural constraints |
| `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` | tier2a_extracted | manually_placed | — | Evaluator expectation patterns for section-level drafting |
| `docs/tier3_project_instantiation/` | tier3 | manually_placed | — | All project-specific facts; sole authoritative source for project claims |
| `docs/tier4_orchestration_state/phase_outputs/` | tier4_phase_output | run_produced | _(multiple)_ | All phase 1–7 outputs as grounding for proposal content |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | tier4_phase_output | run_produced | `orch.phase7.budget_gate_assessment.v1` | Budget gate confirmation; must show pass before any drafting |
| `docs/tier5_deliverables/proposal_sections/` | tier5_deliverable | run_produced | `orch.tier5.proposal_section.v1` | (n08b only) Drafted sections consumed for assembly |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier5_deliverables/proposal_sections/<section_id>.json` | tier5_deliverable | run_produced | `orch.tier5.proposal_section.v1` | (n08a) Per-section draft artifact; run_id required |
| `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` | tier5_deliverable | run_produced | `orch.tier5.assembled_draft.v1` | (n08b) Assembled draft from all sections; run_id required |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not introduce claims not grounded in Tier 1-4 state.
- Must not reference budget figures not validated through Phase 7 gate.
- Must not fill data gaps with fabricated content.
- Must not write to satisfy grant agreement annex formatting requirements.
- Must not finalize budget-dependent sections before Phase 7 gate has passed.

Universal constraints from `node_body_contract.md` §3 also apply.
