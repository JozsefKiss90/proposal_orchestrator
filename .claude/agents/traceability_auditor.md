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

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not accept unattributed claims as Confirmed.
- Must not mark a claim Confirmed without identifying the specific source artifact.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Node Binding

No `node_ids` binding. Not assigned to any specific manifest node. Carries no own entry or exit gate. Invoked by other agents or the operator.

---

## Output Schema Contracts

### Traceability Audit Reports — Content Contract (no schema_id in spec)

**Canonical path:** `docs/tier4_orchestration_state/validation_reports/<invocation_id>_traceability_report.json`
**Provenance:** run_produced
**Schema ID:** None defined in `artifact_schema_specification.yaml` for validation reports

One report per invocation. Required content:

| Required element | Description |
|-----------------|-------------|
| `agent_id` | `"traceability_auditor"` |
| `run_id` | Propagated from invoking run context |
| `invocation_id` | Unique identifier for this invocation |
| `target_artifact` | Path(s) of the artifact(s) audited |
| `audit_scope` | Gate context or `"on_demand"` |
| `claim_audit` | Array; each entry: `claim_id`, `claim_summary`, `status` (confirmed/inferred/assumed/unresolved), `source_ref` (required for confirmed/inferred), `assumption_declared` (for assumed), `resolution_required` (boolean — true for unresolved) |
| `overall_traceability` | `traceable` or `gaps_present` |
| `timestamp` | ISO 8601 |

Status categories applied per CLAUDE.md §12.2:
- **Confirmed** — directly evidenced by a named source in Tier 1–3
- **Inferred** — derived by logical reasoning; inference chain stated
- **Assumed** — adopted in absence of direct evidence; assumption explicitly declared
- **Unresolved** — conflicting evidence or missing information; resolution required

---

## Gate Awareness and Failure Behaviour

### Invocation Preconditions (Cross-Phase Agent)

This agent has no own predecessor gates. Invocation is context-dependent:
- When invoked at gates 10, 11, or 12: the assembled draft or final export is the primary target.
- When invoked on demand at any phase: the calling agent provides the target artifact path(s).

The agent does not declare any phase gate passed or failed. Its outputs are consumed by gate semantic predicates (`all_sections_have_traceability_footer`, `no_gap_masked_as_confirmed`, `no_unsupported_tier5_claims`) or by calling agents.

### No Own Exit Gate

This agent carries `exit_gate: null`. It does not satisfy any gate condition independently.

### Failure Protocol

#### Case 1: Unresolved claim found (no traceable source)
- **Flag as Unresolved** in `claim_audit`; set `resolution_required: true`.
- **Decision log:** Entry with `decision_type: scope_conflict`; identify the claim, section, and what source evidence is needed.
- **Must not:** Accept an unattributed claim as Confirmed (CLAUDE.md §12.2, §10.5).

#### Case 2: Claim marked Confirmed without a named source artifact
- **Downgrade to Assumed or Unresolved** in the report.
- **Write:** `decision_type: assumption` or `scope_conflict`; document the downgrade reason.
- **Must not:** Validate a Confirmed status without a specific source path.

#### Case 3: Target artifact absent
- **Write:** Audit report with `overall_traceability: gaps_present`; note the absent artifact as a blocking gap.

#### Case 4: Tier 1–3 source files needed but absent
- **Flag:** Cannot issue Confirmed status without access to source files; flag affected claims as Unresolved.
- **Write:** `decision_type: scope_conflict`; note which source files are needed.

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: traceability_auditor`, `phase_id` (target or `cross-phase`), `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Unresolved claim found (no traceable source) | `scope_conflict` | Claim ID; section; what source is needed |
| Claim downgraded from Confirmed to Assumed/Unresolved | `material_decision` | Claim ID; original status; new status; reason |
| Full traceability confirmed | `gate_pass` | Invocation ID; target artifact; audit summary |
| Gaps identified that block downstream use | `gate_failure` | Invocation ID; unresolved claim IDs |

---

## Constitutional Review

### 1. Scope compliance

`reads_from` and `writes_to` in the front matter exactly match `agent_catalog.yaml`. Write targets are `docs/tier4_orchestration_state/validation_reports/` and `docs/tier4_orchestration_state/decision_log/`. The read scope covers all four tiers (Tier 1–4 extracted, Tier 3 instantiation, Tier 4 phase outputs, Tier 5 deliverables) — all declared in the catalog. This agent does not write to any tier source, Tier 5 deliverable, or phase output directory. No undeclared path access is implied.

### 2. Manifest authority compliance

This agent has no node binding (`node_ids: []`). It is a cross-phase auxiliary with `entry_gate: null` and `exit_gate: null`. The body text states: "The agent does not declare any phase gate passed or failed." Its outputs are consumed by semantic gate predicates (`all_sections_have_traceability_footer`, `no_gap_masked_as_confirmed`, `no_unsupported_tier5_claims`) — but the gate pass/fail decision is made by the runner applying those predicates, not by this agent.

**Implied right to amend workflow logic:** No such language exists. This agent reads artifacts and writes audit reports. Risk: none.

### 3. Forbidden-action review against CLAUDE.md §13 and §12

- **§12.2 — Confirmed status without named source:** Must_not includes "mark a claim Confirmed without identifying the specific source artifact." Failure Protocol Case 2 requires downgrading Confirmed status to Assumed or Unresolved when no specific source path can be identified. Risk: low.
- **§13.9 — Generic knowledge for Confirmed status:** The audit can only issue Confirmed status for claims with a named, readable source artifact. If Tier 1–3 source files are absent, affected claims must be flagged as Unresolved (Failure Protocol Case 4). Risk: low.
- **§13.5 — Durable decisions in memory:** One decision log entry per Unresolved finding is required. Risk: low.
- **§13.6 — Skill/agent as de facto authority:** This agent reads and reports. It has no authority to modify source documents, phase outputs, or gate conditions. Risk: none.
- **No Tier 5 content production:** This agent does not produce Tier 5 content. Not applicable for §13.10.
- **No gate-passing authority:** Cannot declare any gate passed independently. Risk: none.

### 4. Must-not integrity

Both must_not items from `agent_catalog.yaml` are present verbatim. Step 6–7 additions do not weaken them. Failure Protocol Case 2 strengthens the Confirmed-without-source-artifact constraint by specifying the downgrade mechanism.

**Cross-phase scope constraint:** This agent reads broadly but writes only to validation reports and decision log. No write path approaches a source document or phase output. Scope boundary is respected.

### 5. Conflict status

Constitutional review result: no conflict identified
