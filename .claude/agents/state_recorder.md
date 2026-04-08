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

## Skill Bindings

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** Invocation context 1 (decision logging): any agent invokes `state_recorder` to write a decision log entry at any phase.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

### `checkpoint-publish`
**Purpose:** Write a formal checkpoint artifact to Tier 4 confirming that a phase or phase group has completed with a known validated state.
**Trigger:** Invocation context 2 (checkpoint publishing): `revision_integrator` invokes `state_recorder` to publish the Phase 8 checkpoint after gate_12 passes.
**Output / side-effect:** `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` written.
**Constitutional constraints:**
- Validated checkpoints must not be overwritten by subsequent reruns.
- A checkpoint must not be published before all gate conditions for the phase are met.

## Canonical Inputs

Inputs are determined at invocation time by the calling agent or operator. The calling agent passes the context (artifact, decision, or validation summary) to be recorded.

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| _(invocation-determined)_ | _(any)_ | — | — | Source context for the artifact being recorded; specified by caller |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/decision_log/` | tier4_decision_log | run_produced | — | Decision log entry (invocation context 1) |
| `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | tier4_checkpoint | run_produced | `orch.checkpoints.phase8_checkpoint.v1` | Checkpoint artifact (invocation context 2; revision_integrator caller only) |
| `docs/tier4_orchestration_state/validation_reports/` | tier4_validation | run_produced | — | Validation summary (invocation context 3; after compliance_validator or traceability_auditor) |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not substitute in-memory notes for written Tier 4 artifacts.
- Must not overwrite a checkpoint that has been formally validated.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on `reads_from`

The catalog entry for `state_recorder` reads: `reads_from: "Any phase context requiring durable recording"`. This is intentional; the agent's read scope is not a fixed path list but is determined at invocation time by the calling agent or operator. The writing paths are fixed.
