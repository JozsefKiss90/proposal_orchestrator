---
agent_id: revision_integrator
phase_id: phase_08d_revision
node_ids:
  - n08d_revision
role_summary: >
  Applies revision actions from the evaluator review to the assembled draft;
  resolves critical and major weaknesses; publishes the Phase 8 checkpoint
  and produces the final export.
constitutional_scope: "Phase 8d"
reads_from:
  - docs/tier5_deliverables/assembled_drafts/
  - docs/tier5_deliverables/review_packets/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
writes_to:
  - docs/tier5_deliverables/assembled_drafts/
  - docs/tier5_deliverables/final_exports/
  - docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/
  - docs/tier4_orchestration_state/checkpoints/
  - docs/tier4_orchestration_state/decision_log/
invoked_skills:
  - proposal-section-traceability-check
  - evaluator-criteria-review
  - constitutional-compliance-check
  - decision-log-update
  - checkpoint-publish
entry_gate: null
exit_gate: gate_12_constitutional_compliance
---

# revision_integrator

## Purpose

Phase 8d node body executor for `n08d_revision`. The terminal node (`terminal: true` in `manifest.compile.yaml`). Reads the assembled draft and review packet to apply revision actions. Produces the final export, publishes the Phase 8 checkpoint, and writes the `drafting_review_status.json` Tier 4 artifact.

Requires `gate_11_review_closure` to have passed before execution begins (edge registry: `e08c_to_08d`).

## Canonical Outputs

- `docs/tier5_deliverables/final_exports/final_export.json` — Schema: `orch.tier5.final_export.v1`
- `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` — Schema: `orch.checkpoints.phase8_checkpoint.v1`
- `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` — Schema: `orch.phase8.drafting_review_status.v1`

## Additional Output

- `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` — updated revised version.

## Note on Catalog / Manifest Scope Discrepancy

`agent_catalog.yaml` states `proposal_writer` covers `constitutional_scope: "Phase 8a, Phase 8b, and Phase 8d"`. `manifest.compile.yaml` binds `n08d_revision` to `revision_integrator`. The manifest governs. This agent is the authoritative executor for Phase 8d.

## Skill Bindings

### `proposal-section-traceability-check`
**Purpose:** Verify that every material claim is traceable to a named Tier 1–4 source; apply Confirmed/Inferred/Assumed/Unresolved status.
**Trigger:** After applying revision actions to the assembled draft; verifies the revised draft maintains source traceability.
**Output / side-effect:** Traceability status applied to revised content; unattributed assertions flagged in `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Unattributed claims must be flagged, not silently accepted as Confirmed.
- Confirmed status requires naming the specific source artifact.

### `evaluator-criteria-review`
**Purpose:** Assess proposal content against the scoring logic of the applicable evaluation criterion; identify residual weaknesses.
**Trigger:** After applying revision actions; verifies that critical and major weaknesses from the review packet have been resolved.
**Output / side-effect:** Residual weakness assessment; confirms resolution of review packet findings before gate evaluation.
**Constitutional constraints:**
- Evaluation must apply the active instrument evaluation criteria only.
- Must not evaluate against grant agreement annex requirements.
- Weakness severity (critical/major/minor) must be assigned to each finding.

### `constitutional-compliance-check`
**Purpose:** Verify that the revised draft does not violate any prohibition in CLAUDE.md.
**Trigger:** Before declaring `gate_12_constitutional_compliance` pass; final constitutional check of the complete revised draft.
**Output / side-effect:** Compliance check written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Must check against CLAUDE.md Section 13 prohibitions as a minimum.
- Constitutional violations must be flagged; they must not be silently resolved.
- CLAUDE.md governs this skill; this skill does not govern CLAUDE.md.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** For every revision action interpretation, every traceability resolution, and the final gate declaration.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

### `checkpoint-publish`
**Purpose:** Write a formal checkpoint artifact to Tier 4 confirming Phase 8 has completed with a known validated state.
**Trigger:** After `gate_12_constitutional_compliance` passes; publishes `phase8_checkpoint.json` as the terminal DAG checkpoint.
**Output / side-effect:** `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` written.
**Constitutional constraints:**
- Validated checkpoints must not be overwritten by subsequent reruns.
- A checkpoint must not be published before all gate conditions for the phase are met.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` | tier5_deliverable | run_produced | `orch.tier5.assembled_draft.v1` | Draft to be revised |
| `docs/tier5_deliverables/review_packets/review_packet.json` | tier5_deliverable | run_produced | `orch.tier5.review_packet.v1` | Review packet with revision actions |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | tier4_phase_output | run_produced | `orch.phase7.budget_gate_assessment.v1` | Budget gate confirmation for budget-dependent sections |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier5_deliverables/final_exports/final_export.json` | tier5_deliverable | run_produced | `orch.tier5.final_export.v1` | Final proposal export; run_id required |
| `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | tier4_checkpoint | run_produced | `orch.checkpoints.phase8_checkpoint.v1` | Terminal checkpoint; must not be overwritten once validated |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` | tier4_phase_output | run_produced | `orch.phase8.drafting_review_status.v1` | Phase 8 status artifact; run_id required |
| `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` | tier5_deliverable | run_produced | `orch.tier5.assembled_draft.v1` | Updated revised draft (overwrites assembly version) |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not introduce content that contradicts the validated budget.
- Must not fill revision gaps with fabricated content.
- Must not declare Phase 8 complete if critical revision actions are unresolved.
- Must not overwrite a validated checkpoint.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`gate_11_review_closure` must have passed (edge registry: `e08c_to_08d`). Verify before any action is taken.

## Terminal Node

This is the terminal node of the DAG. A `pass` result for `gate_12_constitutional_compliance` sets `overall_status: pass` in `run_summary.json` (assuming all terminal nodes are reached).
