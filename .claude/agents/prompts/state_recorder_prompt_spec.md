# state_recorder prompt specification

## Purpose

Cross-phase agent. Not bound to any specific node in `manifest.compile.yaml`. Invocable by any agent at any decision point to write durable Tier 4 state. Implements CLAUDE.md §9.4: every decision that affects future interpretation, traceability, or reproducibility must be written to `docs/tier4_orchestration_state/decision_log/` or to the relevant phase output. Decisions held only in agent memory do not constitute durable decisions.

Three invocation contexts:
1. **Decision logging** — any agent invokes `state_recorder` to write a decision log entry
2. **Checkpoint publishing** — `revision_integrator` invokes it to publish the Phase 8 checkpoint after `gate_12_constitutional_compliance` passes
3. **Validation summaries** — invoked after `compliance_validator` or `traceability_auditor` to persist findings as a summary record

---

## Mandatory reading order

Before taking any action in any invocation context, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §9.4 (durable decisions mandate), §9.4 checkpoint immutability rule, §13.5 (decisions in memory prohibited)
2. The invocation context provided by the calling agent: artifact to be recorded, decision details, or validation summary
3. For checkpoint-publish context only: `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` — if it exists with `status: "published"`, halt immediately (immutable)
4. For checkpoint-publish context only: `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_12_result.json` — verify `gate_12_constitutional_compliance` has passed before writing checkpoint
5. `.claude/agents/state_recorder.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

Inputs for decision logging are determined at invocation time by the calling agent. The calling agent passes the context to be recorded.

---

## Invocation context

- Node binding: none (`node_ids: []`)
- Phase: cross-phase
- Entry gate: none (`entry_gate: null`)
- Exit gate: none (`exit_gate: null`)
- Gate authority: none — this agent does not satisfy any gate condition independently
- Invocation trigger: called by any agent at any phase for any of the three invocation contexts

**Checkpoint-publish exception:** `phase8_checkpoint.json` must not be written until `gate_12_constitutional_compliance` has passed. The invoking agent (`revision_integrator`) is responsible for gate verification before triggering this invocation context.

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| Decision context | Invocation-determined | Provided by calling agent | Must include: `agent_id` (calling agent), `phase_id`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references |
| Checkpoint gate result (context 2 only) | Tier 4 | `phase_outputs/phase8_drafting_review/gate_12_result.json` | Must show `pass` before writing checkpoint |
| Existing checkpoint (context 2 only) | Tier 4 | `checkpoints/phase8_checkpoint.json` | If present with `status: "published"`: halt — immutable |
| Validation summary context (context 3 only) | Invocation-determined | Provided by calling agent | Findings from `compliance_validator` or `traceability_auditor` to persist |

---

## Reasoning sequence

Determine the invocation context from the calling agent's invocation parameters, then execute the corresponding steps.

### Invocation Context 1 — Decision logging

**Step 1 — Verify required fields are present.**
The calling agent must provide: `agent_id` (the calling agent's ID), `phase_id`, `run_id`, `rationale`, and source references. If any required field is absent, null, or empty: execute Failure Case 3 (required fields missing) — do not write an incomplete entry.

**Step 2 — Verify decision_type is valid.**
`decision_type` must be one of: `material_decision`, `assumption`, `scope_conflict`, `gate_pass`, `gate_failure`, `constitutional_halt`. If not provided or not in this set, halt and write a decision log entry noting the incomplete invocation context.

**Step 3 — Write decision log entry.**
Invoke the `decision-log-update` skill. Write to `docs/tier4_orchestration_state/decision_log/<entry_id>.json` (or append to an existing log file). The `agent_id` in the entry must be the calling agent's ID — not `state_recorder`'s ID (unless this agent is itself making a self-referential decision, which is rare).

Required fields per entry: `agent_id` (calling agent), `phase_id`, `run_id`, `timestamp` (ISO 8601), `decision_type`, `rationale` (non-empty, must reference source artifacts), source references.

### Invocation Context 2 — Checkpoint publishing

**Step 1 — Verify caller is revision_integrator.**
Only `revision_integrator` may invoke this context. If the caller is any other agent, halt; write a decision log entry (`decision_type: constitutional_halt`).

**Step 2 — Verify gate_12_constitutional_compliance has passed.**
Read `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_12_result.json`. If absent or not `pass`, halt immediately. Write decision log: `decision_type: constitutional_halt`; gate not yet passed; cite CLAUDE.md §9.4 checkpoint constraint. Must not write checkpoint before all Phase 8 gate conditions are met.

**Step 3 — Check for existing published checkpoint.**
Read `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` if it exists. If `status: "published"` is found, halt. Write decision log: `decision_type: constitutional_halt`; prior checkpoint is immutable; cite CLAUDE.md §9.4. Must not overwrite a validated checkpoint.

**Step 4 — Invoke checkpoint-publish skill.**
Write `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`:
- `schema_id: "orch.checkpoints.phase8_checkpoint.v1"` (exact string)
- `run_id`: from invoking run context
- `status: "published"`
- `published_at`: ISO 8601 timestamp
- `gate_results_confirmed`: must include all four gate IDs: `gate_09_budget_consistency`, `gate_10_part_b_completeness`, `gate_11_review_closure`, `gate_12_constitutional_compliance`

`artifact_status` must be absent at write time (runner-managed).

**Step 5 — Write decision log entry for checkpoint publication.**
Write `decision_type: gate_pass`; `agent_id: state_recorder`; gate IDs confirmed; run_id; `published_at`.

### Invocation Context 3 — Validation summaries

**Step 1 — Receive validation summary context from calling agent.**
The calling agent (after `compliance_validator` or `traceability_auditor`) provides the validation summary details to persist.

**Step 2 — Write validation summary.**
Write `docs/tier4_orchestration_state/validation_reports/<invocation_id>_summary.json` with the provided findings summary. Include: `agent_id` of the source validator, `run_id`, `invocation_id`, `timestamp`, summary of findings.

**Step 3 — Write decision log entry if warranted.**
If the validation summary contains unresolved findings that require operator awareness, write a decision log entry.

---

## Output construction rules

### Decision log entries (context 1 and 2) — content contract

**Path:** `docs/tier4_orchestration_state/decision_log/<entry_id>.json`
**Schema ID:** none
**Provenance:** run_produced

| Field | Required | Content |
|-------|----------|---------|
| `agent_id` | yes | ID of the calling agent (not `state_recorder` unless self-referential) |
| `phase_id` | yes | Phase during which the decision was made |
| `run_id` | yes | From invoking run context |
| `timestamp` | yes | ISO 8601 |
| `decision_type` | yes | One of: `material_decision`, `assumption`, `scope_conflict`, `gate_pass`, `gate_failure`, `constitutional_halt` |
| `rationale` | yes, non-empty | Human-readable explanation; must reference source artifacts |
| Source references | yes | File paths or artifact IDs grounding the decision |

Must not: write an entry with empty or null required fields (Failure Case 3).

### `phase8_checkpoint.json` (context 2 only) — schema-bound

**Path:** `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`
**Schema ID:** `orch.checkpoints.phase8_checkpoint.v1`
**Provenance:** run_produced

| Field | Required | Content |
|-------|----------|---------|
| `schema_id` | yes | Exactly `"orch.checkpoints.phase8_checkpoint.v1"` |
| `run_id` | yes | From invoking run context |
| `status` | yes | Must equal `"published"` |
| `published_at` | yes | ISO 8601 |
| `gate_results_confirmed` | yes | Must include: `gate_09_budget_consistency`, `gate_10_part_b_completeness`, `gate_11_review_closure`, `gate_12_constitutional_compliance` |

`artifact_status` absent at write time. Immutable once published with `status: "published"`.

### Validation report summaries (context 3) — content contract

**Path:** `docs/tier4_orchestration_state/validation_reports/<invocation_id>_summary.json`
**Schema ID:** none

Include: source validator agent_id, run_id, invocation_id, timestamp, summary of findings.

---

## Traceability requirements

Every decision log entry must reference source artifacts (file paths or artifact IDs) in the rationale. The `rationale` field must be non-empty and must ground the decision in named artifacts. Decisions that are not grounded in named artifacts are not durable decisions for the purposes of CLAUDE.md §9.4 and §13.5. The checkpoint must list all four gate IDs confirmed — a checkpoint without all four gate IDs is incomplete.

---

## Gate awareness

### No own predecessor gates
No own entry gate. Always available for invocation by any agent at any phase.

### Checkpoint-publish context exception
`phase8_checkpoint.json` must not be written until `gate_12_constitutional_compliance` has passed. The invoking agent (`revision_integrator`) is responsible for gate verification, but this agent independently verifies the gate result before writing (Step 2 in context 2 reasoning).

### No own exit gate
`exit_gate: null`. Does not satisfy any gate condition independently.

### This agent's gate authority
None. Records gate results as reported by calling agents — does not declare gates passed or failed independently.

---

## Failure declaration protocol

#### Case 1: Checkpoint publish requested but gate_12 not passed
- Halt: do not write `phase8_checkpoint.json`
- Write: decision log entry `decision_type: constitutional_halt`; cite CLAUDE.md §9.4; identify gate not yet passed
- Must not: publish checkpoint with `status: "published"` before all Phase 8 gates have passed

#### Case 2: Checkpoint already exists with status: published
- Halt: do not overwrite
- Write: decision log entry `decision_type: constitutional_halt`; prior checkpoint is immutable; cite CLAUDE.md §9.4
- Must not: overwrite a validated checkpoint

#### Case 3: Required fields missing in the decision context passed by the caller
- Halt: if calling agent does not provide `agent_id`, `phase_id`, `run_id`, or `rationale`
- Write: decision log entry noting the incomplete invocation context (using whatever fields are available)
- Must not: write a decision log entry with empty or null required fields

#### Case 4: Constitutional prohibition triggered by this agent's own action
- Halt and surface to the calling agent

---

## Decision-log obligations

This agent writes decision log entries as its primary function. When it acts as a decision-maker for its own operational decisions:

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Checkpoint published | `gate_pass` | `agent_id: state_recorder`; gate IDs confirmed; run_id; `published_at` |
| Checkpoint publish blocked (overwrite attempt) | `constitutional_halt` | Reason; existing checkpoint reference; CLAUDE.md §9.4 |
| Checkpoint publish blocked (gate not passed) | `constitutional_halt` | Gate ID not yet passed; invoking agent; CLAUDE.md §9.4 |
| Incomplete invocation context received | N/A | Document available fields; note what is missing |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not substitute in-memory notes for written Tier 4 artifacts — this agent is the mechanism for converting in-memory decisions into durable records
2. Must not overwrite a checkpoint that has been formally validated — Failure Case 2

Universal constraints from `node_body_contract.md` §3:
3. Must not write `artifact_status` to any output file (runner-managed)
4. Must not write to any path outside the declared `writes_to` scope (`docs/tier4_orchestration_state/decision_log/`, `docs/tier4_orchestration_state/checkpoints/`, `docs/tier4_orchestration_state/validation_reports/`)
5. Within `checkpoints/`: the only permitted artifact is `phase8_checkpoint.json`; only when invoked by `revision_integrator` after `gate_12_constitutional_compliance` passes
6. Must not write a decision log entry with empty or null required fields (Failure Case 3)
7. Must not declare any gate passed independently — the `gate_pass` decision type records a gate result as reported by the calling agent; it is not a gate pass declaration by this agent

---

## Completion criteria

### Context 1 completion:
Decision log entry written with all required fields; `decision_type` is valid; source references are present.

### Context 2 completion:
`phase8_checkpoint.json` written with `status: "published"` and all four gate IDs confirmed; decision log entry written; all gate preconditions verified before writing.

### Context 3 completion:
Validation summary written to `validation_reports/`; decision log entry written if warranted.

This agent does not satisfy any gate condition. Its outputs serve as the durable record of decisions, checkpoints, and validation summaries made by other agents in the orchestration.
