---
agent_id: state_recorder
phase_id: cross-phase
node_ids: []
role_summary: >
  Writes durable decision log entries, checkpoint artifacts, and validation
  report summaries to Tier 4; ensures all decisions made during orchestration
  are written to docs/ rather than held only in agent memory.
constitutional_scope: "Cross-phase; invocable by any agent at any decision point"
reads_from:
  - "Any phase context requiring durable recording"
writes_to:
  - docs/tier4_orchestration_state/decision_log/
  - docs/tier4_orchestration_state/checkpoints/
  - docs/tier4_orchestration_state/validation_reports/
invoked_skills:
  - decision-log-update
  - checkpoint-publish
entry_gate: null
exit_gate: null
---

# state_recorder

## Purpose

Cross-phase agent. Not bound to any specific node in `manifest.compile.yaml`. Invocable by any agent at any decision point to write durable Tier 4 state.

Implements CLAUDE.md §9.4: "Every decision that affects future interpretation, traceability, or reproducibility must be written to `docs/tier4_orchestration_state/decision_log/` or to the relevant phase output. Decisions held only in agent memory do not constitute durable decisions."

Three invocation contexts:
1. **Decision logging** — any agent invokes `state_recorder` to write a decision log entry
2. **Checkpoint publishing** — `revision_integrator` invokes it to publish the Phase 8 checkpoint
3. **Validation summaries** — invoked after `compliance_validator` or `traceability_auditor` to persist findings

## Outputs

- `docs/tier4_orchestration_state/decision_log/` — decision log entry
- `docs/tier4_orchestration_state/checkpoints/` — checkpoint artifact (when checkpoint-publish is invoked)
- `docs/tier4_orchestration_state/validation_reports/` — validation summary (when invoked after a validator)

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 5–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not substitute in-memory notes for written Tier 4 artifacts.
- Must not overwrite a checkpoint that has been formally validated.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on `reads_from`

The catalog entry for `state_recorder` reads: `reads_from: "Any phase context requiring durable recording"`. This is intentional; the agent's read scope is not a fixed path list but is determined at invocation time by the calling agent or operator. The writing paths are fixed.
