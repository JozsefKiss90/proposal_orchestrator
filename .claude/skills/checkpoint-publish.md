---
skill_id: checkpoint-publish
purpose_summary: >
  Write a formal checkpoint artifact to Tier 4 checkpoints/ confirming that a phase
  or phase group has completed with a known validated state, preserving a reproducible
  snapshot of the state at the checkpoint.
used_by_agents:
  - revision_integrator
  - state_recorder
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier3_project_instantiation/
writes_to:
  - docs/tier4_orchestration_state/checkpoints/
constitutional_constraints:
  - "Validated checkpoints must not be overwritten by subsequent reruns"
  - "A checkpoint must not be published before all gate conditions for the phase are met"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool.

**Declared input files to read (in order):**
1. `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` — existing checkpoint guard; if present with `status: "published"`, halt immediately
2. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/gate_result.json` — gate_09_budget_consistency
3. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10a_result.json` — gate_10a_excellence_completeness
4. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10b_result.json` — gate_10b_impact_completeness
5. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10c_result.json` — gate_10c_implementation_completeness
6. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10d_result.json` — gate_10d_cross_section_consistency
7. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_11_result.json` — gate_11_review_closure
8. `docs/tier3_project_instantiation/call_binding/selected_call.json` — Tier 3 snapshot (non-blocking if absent)
9. `docs/tier3_project_instantiation/consortium/partners.json` — Tier 3 snapshot (non-blocking if absent)

**Input boundary rules:**
- Read ONLY the files listed above. Do not read files outside the declared set.
- Do NOT read or require `gate_10_result.json` (legacy monolithic gate — no longer exists).
- Do NOT read or require `gate_12_result.json` (gate_12_constitutional_compliance is the exit gate of n08f_revision, evaluated by the runner AFTER this skill completes).

Return a SINGLE valid JSON object matching the output schema below.
Do not include ANY text before or after the JSON object — no prose, no
markdown fencing. The response must begin with `{` and end with `}`.

## Execution Specification

### Step 1 — Existing checkpoint guard

Read `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`.
If it exists and has `status` = `"published"`: HALT immediately.
Return `{"status": "failure", "failure_category": "CONSTRAINT_VIOLATION", "failure_reason": "Validated checkpoint already exists; overwrite prohibited per CLAUDE.md §5 Tier 4 constraints"}`.
If the file does not exist or is not valid JSON, proceed.

### Step 2 — Read and validate the six required gate result files

Read each of the six gate result files (items 2–7 in the Declared Inputs).
For each file, verify:
- **Presence**: if absent, return `{"status": "failure", "failure_category": "MISSING_INPUT", "failure_reason": "Gate result file <path> not found; all six gate results required for checkpoint"}`.
- **Schema**: `schema_id` must equal `"orch.gate_result.v1"`. If not, return `{"status": "failure", "failure_category": "MALFORMED_ARTIFACT", "failure_reason": "Gate result at <path> has unexpected schema_id"}`.
- **Status**: `status` must equal `"pass"`. If not, return `{"status": "failure", "failure_category": "MISSING_INPUT", "failure_reason": "Gate <gate_id> has status '<status>'; all required gates must have status 'pass'"}`.
- **Run ID**: `run_id` must match the current run_id. If not, return `{"status": "failure", "failure_category": "MALFORMED_ARTIFACT", "failure_reason": "Gate result at <path> has run_id mismatch"}`.

### Step 3 — Read Tier 3 snapshot data

- From `selected_call.json`: extract `call_id` and `topic_id`.
- From `partners.json`: extract the list of `partner_id` values.
- If either file is absent: record as Assumed in a note field — do not halt.

### Step 4 — Construct and write the checkpoint

Build `gate_results_confirmed` from the gate_id field of each verified gate result:
`["gate_09_budget_consistency", "gate_10a_excellence_completeness", "gate_10b_impact_completeness", "gate_10c_implementation_completeness", "gate_10d_cross_section_consistency", "gate_11_review_closure"]`

Write `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`:

```json
{
  "schema_id": "orch.checkpoints.phase8_checkpoint.v1",
  "run_id": "<current run_id>",
  "status": "published",
  "published_at": "<ISO 8601 timestamp>",
  "gate_results_confirmed": ["gate_09_budget_consistency", "gate_10a_excellence_completeness", "gate_10b_impact_completeness", "gate_10c_implementation_completeness", "gate_10d_cross_section_consistency", "gate_11_review_closure"],
  "tier3_snapshot": {
    "call_id": "<from selected_call.json or null>",
    "topic_id": "<from selected_call.json or null>",
    "partner_ids": ["<from partners.json or empty>"]
  }
}
```

- `status` must equal exactly `"published"`.
- `artifact_status` must NOT be added (does not apply to checkpoint artifacts).
- Once written with `status: "published"`, this file must never be overwritten.

## Failure Rules

- Every failure returns a JSON object with `status`, `failure_category`, and `failure_reason`.
- No checkpoint file is written when any failure fires.
- Failure categories: `CONSTRAINT_VIOLATION` (existing checkpoint), `MISSING_INPUT` (absent or non-pass gate), `MALFORMED_ARTIFACT` (schema_id or run_id mismatch).
- Failure is a correct output. Fabricated completion is a constitutional violation (CLAUDE.md §15).
