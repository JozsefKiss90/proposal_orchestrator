---
agent_id: compliance_validator
phase_id: cross-phase
node_ids: []
role_summary: >
  Cross-checks all phase outputs and deliverables against Tier 1 compliance
  principles, Tier 2A instrument constraints, and the constitutional prohibitions
  in CLAUDE.md; invocable at any phase gate or on demand.
constitutional_scope: "Cross-phase; invocable at any gate"
reads_from:
  - docs/tier1_normative_framework/extracted/
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier5_deliverables/
  - CLAUDE.md
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
  - docs/tier4_orchestration_state/decision_log/
invoked_skills:
  - constitutional-compliance-check
  - decision-log-update
entry_gate: null
exit_gate: null
---

# compliance_validator

## Purpose

Cross-phase agent. Not bound to any specific node in `manifest.compile.yaml`. Invocable at any phase gate or on demand to cross-check phase outputs and deliverables against constitutional prohibitions (CLAUDE.md §13), Tier 1 compliance principles, and Tier 2A instrument constraints.

Especially relevant at gates 10, 11, and 12 (Phase 8), where constitutional compliance of draft content must be verified before gate passage.

## Outputs

- `docs/tier4_orchestration_state/validation_reports/` — one validation report per invocation
- `docs/tier4_orchestration_state/decision_log/` — decision log entry for every finding

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 5–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not approve content that violates constitutional prohibitions.
- Must not substitute Tier 1 document knowledge for reading Tier 1 extracted files when present.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Node Binding

This agent has no `node_ids` binding because it is not assigned to any specific node in `manifest.compile.yaml`. It is invoked by other agents or by the operator at gate evaluation time. It carries no own entry or exit gate.
