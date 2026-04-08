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

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not substitute in-memory notes for written Tier 4 artifacts.
- Must not overwrite a checkpoint that has been formally validated.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on `reads_from`

The catalog entry for `state_recorder` reads: `reads_from: "Any phase context requiring durable recording"`. This is intentional; the agent's read scope is not a fixed path list but is determined at invocation time by the calling agent or operator. The writing paths are fixed.

---

## Output Schema Contracts

### Decision Log Entries — Content Contract (no schema_id in spec)

**Canonical path:** `docs/tier4_orchestration_state/decision_log/<entry_id>.json` (or appended to an existing log file)
**Provenance:** run_produced
**Schema ID:** None defined in `artifact_schema_specification.yaml`

Required fields per entry (from `node_body_contract.md` §3.10):

| Field | Required | Content |
|-------|----------|---------|
| `agent_id` | **yes** | ID of the agent recording the decision (the calling agent, not `state_recorder` itself) |
| `phase_id` | **yes** | Phase during which the decision was made |
| `run_id` | **yes** | From invoking run context |
| `timestamp` | **yes** | ISO 8601 |
| `decision_type` | **yes** | One of: `material_decision`, `assumption`, `scope_conflict`, `gate_pass`, `gate_failure`, `constitutional_halt` |
| `rationale` | **yes** | Human-readable explanation; must reference source artifacts |
| Source references | **yes** | File paths or artifact IDs that ground the decision |

### `phase8_checkpoint.json` — Checkpoint Artifact (invocation context 2)

**Canonical path:** `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`
**Schema ID:** `orch.checkpoints.phase8_checkpoint.v1`
**Provenance:** run_produced

This agent writes this artifact only when invoked by `revision_integrator` after `gate_12_constitutional_compliance` passes.

| Field | Type | Required | Derivation |
|-------|------|----------|-----------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.checkpoints.phase8_checkpoint.v1"` |
| `run_id` | string | **yes** | From invoking run context |
| `status` | string | **yes** | Must equal `"published"`; only written after all Phase 8 gates confirmed |
| `published_at` | string | **yes** | ISO 8601 timestamp |
| `gate_results_confirmed` | array | **yes** | Must include: `gate_09_budget_consistency`, `gate_10_part_b_completeness`, `gate_11_review_closure`, `gate_12_constitutional_compliance` |

`artifact_status` must be absent at write time (runner-stamped). This checkpoint must not be overwritten once published with `status: published`.

### Validation Report Summaries — Content Contract (invocation context 3)

**Canonical path:** `docs/tier4_orchestration_state/validation_reports/<invocation_id>_summary.json`
**Schema ID:** None defined in spec.

Written after `compliance_validator` or `traceability_auditor` invocations to persist findings as a summary record.

---

## Gate Awareness and Failure Behaviour

### Invocation Preconditions (Cross-Phase Agent)

This agent has no own predecessor gates. It is always available for invocation by any agent at any phase.

**Checkpoint-publish context exception:** `phase8_checkpoint.json` must not be written until `gate_12_constitutional_compliance` has passed. The invoking agent (`revision_integrator`) is responsible for gate verification before triggering this invocation context.

### No Own Exit Gate

This agent carries `exit_gate: null`. It does not satisfy any gate condition by itself.

### Failure Protocol

#### Case 1: Checkpoint publish requested but gate_12 not passed
- **Halt:** Do not write `phase8_checkpoint.json`.
- **Write:** Decision log entry `decision_type: constitutional_halt`; cite CLAUDE.md §9.4 and checkpoint-publish constitutional constraint.
- **Must not:** Publish a checkpoint with `status: published` before all Phase 8 gates have passed.

#### Case 2: Checkpoint already exists with `status: published`
- **Halt:** Do not overwrite.
- **Write:** Decision log entry `decision_type: constitutional_halt`; the prior checkpoint is immutable.
- **Must not:** Overwrite a validated checkpoint (CLAUDE.md §9.4).

#### Case 3: Required fields missing in the decision context passed by the caller
- **Halt:** If the calling agent does not provide `agent_id`, `phase_id`, `run_id`, or `rationale`, do not write an incomplete entry.
- **Write:** Decision log entry noting the incomplete invocation context.
- **Must not:** Write a decision log entry with empty or null required fields.

#### Case 4: Constitutional prohibition triggered by this agent's own action
- **Halt:** Halt and surface to the calling agent.

### Decision-Log Write Obligations

`state_recorder` is the mechanism for writing decision log entries on behalf of other agents. Its own decisions are minimal. When it does act as a decision-maker:

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Checkpoint published | `gate_pass` | `agent_id: state_recorder`; gate IDs confirmed; run_id; published_at |
| Checkpoint publish blocked (overwrite attempt) | `constitutional_halt` | Reason; existing checkpoint reference; CLAUDE.md §9.4 |
| Checkpoint publish blocked (gate not passed) | `constitutional_halt` | Gate ID not yet passed; invoking agent; CLAUDE.md §9.4 |

---

## Constitutional Review

### 1. Scope compliance

`reads_from` and `writes_to` in the front matter exactly match `agent_catalog.yaml`. Concrete write targets: `docs/tier4_orchestration_state/decision_log/`, `docs/tier4_orchestration_state/checkpoints/`, and `docs/tier4_orchestration_state/validation_reports/`. The read scope is declared as "Any phase context requiring durable recording" — acknowledged as intentional and invocation-determined. No body text implies write access to any path beyond the three declared write targets. This agent does not write to Tier 5 deliverables, Tier 3, or any Tier 2 directory.

**Checkpoint write constraint:** Within `docs/tier4_orchestration_state/checkpoints/`, the only artifact this agent is permitted to write is `phase8_checkpoint.json`, and only when invoked by `revision_integrator` after `gate_12_constitutional_compliance` passes. This is the sole canonically permitted checkpoint artifact for this agent.

### 2. Manifest authority compliance

This agent has no node binding (`node_ids: []`). It is a cross-phase auxiliary with `entry_gate: null` and `exit_gate: null`. The body text correctly states that `overall_status: pass` in `run_summary.json` is set by the runner (scheduler), not by this agent. The checkpoint artifact is the only gate-adjacent output, and the body text correctly conditions it on `gate_12_constitutional_compliance` passing, with gate verification responsibility placed on the invoking agent (`revision_integrator`).

**No authority to redefine workflow logic:** This agent's function is purely to persist state. No language implies authority over phase definitions, gate conditions, or the authority hierarchy. Risk: none.

### 3. Forbidden-action review against CLAUDE.md §13 and §9

- **§9.4 — Decisions held only in memory:** This agent is the implementation mechanism for §9.4. Its purpose is to convert in-memory decisions into durable Tier 4 records. Must_not includes "substitute in-memory notes for written Tier 4 artifacts." Risk: low.
- **§9.4 / checkpoint immutability:** Must_not includes "overwrite a checkpoint that has been formally validated." Failure Protocol Case 2 halts and writes a constitutional_halt entry on any overwrite attempt. Risk: low.
- **Checkpoint before gate (§9.4 / §6.4):** Failure Protocol Case 1 prohibits publishing the checkpoint before all Phase 8 gates are passed. The checkpoint-publish skill constraint states "A checkpoint must not be published before all gate conditions for the phase are met." Risk: low.
- **§13.5 — Durable decisions in memory:** This agent is the anti-§13.5 mechanism. Its function is the solution, not a risk. Risk: none.
- **§13.6 — Agent as de facto authority:** This agent writes but does not decide. It is a recording mechanism, not an authority. Risk: none.
- **No Tier 5 content production:** Not applicable.
- **No gate-passing authority:** Cannot declare any gate passed (the `gate_pass` decision log type records that a gate passed, as reported by the invoking agent — it does not constitute a gate pass declaration by this agent).

### 4. Must-not integrity

Both must_not items from `agent_catalog.yaml` are present verbatim. Step 6–7 additions do not weaken them. The Checkpoint-publish context exception in the invocation preconditions section adds a specific gate-enforcement requirement for the checkpoint write path.

**Runner-owned artifact boundary:** `run_summary.json` and `artifact_status` are runner-owned artifacts and must not be written by this agent. No body text claims write authority over these. `artifact_status` is absent from the checkpoint schema field table (marked "absent at write time"). Correct.

### 5. Conflict status

Constitutional review result: no conflict identified
