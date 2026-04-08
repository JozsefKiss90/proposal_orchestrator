---
agent_id: traceability_auditor
phase_id: cross-phase
node_ids: []
role_summary: >
  Audits phase outputs and deliverables for source traceability; confirms that
  every material claim can be traced to a named Tier 1-4 source; applies
  Confirmed/Inferred/Assumed/Unresolved status categories and flags
  unattributed assertions.
constitutional_scope: "Cross-phase; invocable at any gate"
reads_from:
  - docs/tier1_normative_framework/extracted/
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier2b_topic_and_call_sources/extracted/
  - docs/tier3_project_instantiation/
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier5_deliverables/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
  - docs/tier4_orchestration_state/decision_log/
invoked_skills:
  - proposal-section-traceability-check
  - decision-log-update
entry_gate: null
exit_gate: null
---

# traceability_auditor

## Purpose

Cross-phase agent. Not bound to any specific node in `manifest.compile.yaml`. Invocable at any gate or on demand to audit phase outputs and Tier 5 deliverables for source traceability.

Applies the four status categories defined in CLAUDE.md §12.2:
- **Confirmed** — directly evidenced by a named source in Tier 1–3
- **Inferred** — derived by logical reasoning from confirmed evidence; inference chain stated
- **Assumed** — adopted in the absence of direct evidence; assumption explicitly declared
- **Unresolved** — conflicting evidence or missing information; resolution required before downstream use

Especially relevant when reviewing assembled drafts and final exports in Phase 8.

## Outputs

- `docs/tier4_orchestration_state/validation_reports/` — traceability audit report per invocation
- `docs/tier4_orchestration_state/decision_log/` — entry for unresolved findings

## Skill Bindings

### `proposal-section-traceability-check`
**Purpose:** Verify that every material claim in a proposal section is traceable to a named Tier 1–4 source; apply Confirmed/Inferred/Assumed/Unresolved status.
**Trigger:** Invoked at any gate or on demand; reads target phase outputs or Tier 5 deliverables and checks every material claim against Tier 1–3 sources.
**Output / side-effect:** Traceability audit report written to `docs/tier4_orchestration_state/validation_reports/`; one report per invocation.
**Constitutional constraints:**
- Unattributed claims must be flagged, not silently accepted as Confirmed.
- Confirmed status requires naming the specific source artifact.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** For every Unresolved finding that requires resolution before downstream use.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`; one entry per unresolved finding.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

## Canonical Inputs

Inputs are determined at invocation time by the calling agent or operator. The following paths represent the full scope of possible inputs:

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier1_normative_framework/extracted/` | tier1_extracted | manually_placed | — | Normative sources for Confirmed status checks |
| `docs/tier2a_instrument_schemas/extracted/` | tier2a_extracted | manually_placed | — | Instrument schema sources |
| `docs/tier2b_topic_and_call_sources/extracted/` | tier2b_extracted | manually_placed | — | Call-specific sources for traceability |
| `docs/tier3_project_instantiation/` | tier3 | manually_placed | — | Project-specific sources for traceability |
| `docs/tier4_orchestration_state/phase_outputs/` | tier4_phase_output | run_produced | _(phase-specific)_ | Phase outputs being audited |
| `docs/tier5_deliverables/` | tier5_deliverable | run_produced | _(deliverable-specific)_ | Deliverables being audited |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/validation_reports/` | tier4_validation | run_produced | — | One traceability audit report per invocation |
| `docs/tier4_orchestration_state/decision_log/` | tier4_decision_log | run_produced | — | One decision entry per Unresolved finding |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not accept unattributed claims as Confirmed.
- Must not mark a claim Confirmed without identifying the specific source artifact.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Node Binding

No `node_ids` binding. Not assigned to any specific manifest node. Carries no own entry or exit gate. Invoked by other agents or the operator.
