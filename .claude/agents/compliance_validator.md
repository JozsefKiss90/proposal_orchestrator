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

## Skill Bindings

### `constitutional-compliance-check`
**Purpose:** Verify that a phase output or deliverable does not violate any prohibition in CLAUDE.md; checks for fabricated project facts, fabricated call constraints, budget-dependent content before gate, grant annex schema usage, and other constitutional violations.
**Trigger:** Invoked at any gate or on demand; reads the target artifact(s) and CLAUDE.md to check against Section 13 prohibitions.
**Output / side-effect:** Compliance report written to `docs/tier4_orchestration_state/validation_reports/`; one report per invocation.
**Constitutional constraints:**
- Must check against CLAUDE.md Section 13 prohibitions as a minimum.
- Constitutional violations must be flagged; they must not be silently resolved.
- CLAUDE.md governs this skill; this skill does not govern CLAUDE.md.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** For every compliance finding; each finding that would affect downstream use must produce a decision log entry.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`; one entry per finding.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

## Canonical Inputs

Inputs are determined at invocation time by the calling agent or operator. The following paths represent the full scope of possible inputs:

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `CLAUDE.md` | constitutional | — | — | Authority source for all compliance checks |
| `docs/tier1_normative_framework/extracted/` | tier1_extracted | manually_placed | — | Compliance principles and participation conditions |
| `docs/tier2a_instrument_schemas/extracted/` | tier2a_extracted | manually_placed | — | Instrument constraints for compliance checking |
| `docs/tier4_orchestration_state/phase_outputs/` | tier4_phase_output | run_produced | _(phase-specific)_ | Phase outputs being checked |
| `docs/tier5_deliverables/` | tier5_deliverable | run_produced | _(deliverable-specific)_ | Deliverables being checked |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/validation_reports/` | tier4_validation | run_produced | — | One compliance report per invocation |
| `docs/tier4_orchestration_state/decision_log/` | tier4_decision_log | run_produced | — | One decision entry per compliance finding |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not approve content that violates constitutional prohibitions.
- Must not substitute Tier 1 document knowledge for reading Tier 1 extracted files when present.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Node Binding

This agent has no `node_ids` binding because it is not assigned to any specific node in `manifest.compile.yaml`. It is invoked by other agents or by the operator at gate evaluation time. It carries no own entry or exit gate.
