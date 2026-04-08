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

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 5–9 of `agent-generation-plan.md`.

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
