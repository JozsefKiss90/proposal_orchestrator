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

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not approve content that violates constitutional prohibitions.
- Must not substitute Tier 1 document knowledge for reading Tier 1 extracted files when present.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Node Binding

This agent has no `node_ids` binding because it is not assigned to any specific node in `manifest.compile.yaml`. It is invoked by other agents or by the operator at gate evaluation time. It carries no own entry or exit gate.

---

## Output Schema Contracts

### Validation Reports — Content Contract (no schema_id in spec)

**Canonical path:** `docs/tier4_orchestration_state/validation_reports/<invocation_id>_compliance_report.json`
**Provenance:** run_produced
**Schema ID:** None defined in `artifact_schema_specification.yaml` for validation reports

This agent writes one compliance report per invocation. No schema_id_value is defined in the spec for validation report artifacts. Required content per report:

| Required element | Description |
|-----------------|-------------|
| `agent_id` | `"compliance_validator"` |
| `run_id` | Propagated from invoking run context |
| `invocation_id` | Unique identifier for this invocation (used in file naming) |
| `target_artifact` | Path(s) of the artifact(s) checked |
| `gate_context` | The gate ID being evaluated (if invoked at a gate), or `"on_demand"` |
| `findings` | Array of findings; each: `finding_id`, `prohibition_ref` (CLAUDE.md §13.x), `description`, `severity` (critical/major/minor), `resolution_required` (boolean) |
| `overall_compliance` | `compliant` or `non_compliant` |
| `timestamp` | ISO 8601 |

### Decision Log Entries

One entry per finding that would affect downstream use. Written to `docs/tier4_orchestration_state/decision_log/`.

---

## Gate Awareness and Failure Behaviour

### Invocation Preconditions (Cross-Phase Agent)

This agent has no own predecessor gates. Invocation preconditions are context-dependent:
- When invoked at a specific gate (e.g., `gate_10`, `gate_11`, `gate_12`): the invoking agent or operator must have identified a need for compliance checking at that gate.
- When invoked on demand: no preconditions; the operator or calling agent provides the target artifact path(s).

The agent does not declare any phase gate passed or failed directly. It produces a compliance report that gate predicates or calling agents may consume.

### No Own Exit Gate

This agent carries `exit_gate: null`. It does not satisfy any gate condition by itself. Its outputs (validation reports) are consumed by gate predicates and by the calling agent's gate-enforcement logic.

### Failure Protocol

#### Case 1: Constitutional violation found in target artifact
- **Write:** Compliance report with `overall_compliance: non_compliant`; populate `findings` with the specific prohibition(s) triggered.
- **Decision log:** One entry per finding with `decision_type: constitutional_halt` (for critical violations) or `material_decision` (for non-critical findings).
- **Must not:** Approve content that violates constitutional prohibitions even if the invoking agent requests approval (CLAUDE.md §10.5).

#### Case 2: Target artifact absent
- **Write:** Compliance report with `findings` noting the absent artifact; `overall_compliance: non_compliant`.
- **Must not:** Issue a compliant determination for an artifact that cannot be read.

#### Case 3: Tier 1 source documents present but not read
- **Must read the Tier 1 extracted files** — must not substitute agent knowledge of Horizon Europe compliance requirements (CLAUDE.md §13.9).
- **Halt and flag** if Tier 1 extracted files are referenced but absent.

#### Case 4: Constitutional prohibition triggered by this agent's own action
- **Halt:** If the compliance check itself would require fabricating data, halt.
- **Write:** `decision_type: constitutional_halt`.

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: compliance_validator`, `phase_id` (of the target or `cross-phase`), `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Constitutional violation found | `constitutional_halt` | Finding ID; CLAUDE.md §13.x; target artifact; description |
| Non-critical finding requiring operator awareness | `material_decision` | Finding ID; prohibition reference; description; severity |
| Compliant determination issued | `gate_pass` | Invocation ID; target artifact(s); gate context; all checks confirmed |
| Target artifact absent | `gate_failure` | Invocation ID; missing path |
