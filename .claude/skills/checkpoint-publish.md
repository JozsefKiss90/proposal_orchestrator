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

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/` | Phase output directory — gate result files confirming all gates passed for the phase group being checkpointed | gate_result.json files for gate_09_budget_consistency, gate_10_part_b_completeness, gate_11_review_closure, gate_12_constitutional_compliance (for the Phase 8 checkpoint); status[pass] field from each | `orch.gate_result.v1` (per gate result file) | Confirms that all gate conditions for the phase(s) being checkpointed have passed; a checkpoint must not be published until all gate results carry status: "pass" |
| `docs/tier3_project_instantiation/` | Tier 3 project data snapshot | selected_call.json (call_id, topic_id); partners.json (partner_ids); architecture_inputs state | N/A — Tier 3 source directory (semantic scope root) | Provides the Tier 3 state at checkpoint time; included in the checkpoint's state snapshot for reproducibility |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | phase8_checkpoint.json | `orch.checkpoints.phase8_checkpoint.v1` | schema_id, run_id, status[published], published_at (ISO 8601), gate_results_confirmed (array of gate_ids: must include gate_09_budget_consistency, gate_10_part_b_completeness, gate_11_review_closure, gate_12_constitutional_compliance) | Yes | status: set to "published" only when all required gate results carry status: "pass"; published_at: ISO 8601 timestamp at time of checkpoint publication; gate_results_confirmed: list of gate_ids confirmed at checkpoint time, derived from reading gate result files in phase_outputs/ |

**Critical constraint:** A validated checkpoint must not be overwritten by subsequent reruns (CLAUDE.md §5 Tier 4 constraints). If `phase8_checkpoint.json` already exists with status: "published", this skill must refuse to overwrite it and return a CONSTRAINT_VIOLATION failure. This skill does not write to the decision log; the invoking agent must call decision-log-update if durable logging of the overwrite refusal is required.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | Yes — artifact_id: a_t4_checkpoint_phase8 (directory); canonical file within that directory; immutable_after_creation: true | n08d_revision |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: **Existing checkpoint guard** — check whether `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` already exists. If it does exist: read it and check `status` field. If `status` = "published": HALT immediately. Do not overwrite. Return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="Validated checkpoint already exists; overwrite prohibited per CLAUDE.md §5 Tier 4 constraints; checkpoint_preservation rule violated"). The invoking agent must invoke decision-log-update with decision_type: "gate_failure", decision_description: "phase8_checkpoint.json already exists with status: published; overwrite is constitutionally prohibited per CLAUDE.md §5 Tier 4 constraints", tier_authority_applied: "CLAUDE.md §5 Tier 4 / state_rules.yaml checkpoint_preservation" to produce the durable decision log record. This skill does not write to the decision log.
- Step 1.2: Read the four required gate result files. For each, confirm presence and schema:
  - `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/gate_result.json` — schema_id must equal "orch.gate_result.v1"
  - `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10_result.json` — schema_id must equal "orch.gate_result.v1"
  - `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_11_result.json` — schema_id must equal "orch.gate_result.v1"
  - `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_12_result.json` — schema_id must equal "orch.gate_result.v1"
  - If any file is absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="Gate result file <path> not found; all four gate results required for checkpoint") and halt.
  - If any schema_id does not match "orch.gate_result.v1": return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="Gate result at <path> has unexpected schema_id") and halt.
- Step 1.3: For each gate result file from Step 1.2: read the `status` field. If ANY gate result has `status` ≠ "pass": return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="Gate <gate_id> has status '<status>'; all required gates must have status 'pass' before checkpoint can be published") and halt.
- Step 1.4: For each gate result: confirm `run_id` matches the current invoking agent's `run_id` context parameter. If any `run_id` does not match: return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="Gate result at <path> has run_id '<gate_run_id>' which does not match current run_id '<current_run_id>'") and halt.

### 2. Core Processing Logic

- Step 2.1: Read the confirmed passing gate result files (all four from Step 1.2). Extract `gate_id` from each to build the `gate_results_confirmed` array: ["gate_09_budget_consistency", "gate_10_part_b_completeness", "gate_11_review_closure", "gate_12_constitutional_compliance"].
- Step 2.2: Read Tier 3 snapshot data:
  - From `docs/tier3_project_instantiation/call_binding/selected_call.json`: extract `call_id` and `topic_id`.
  - From `docs/tier3_project_instantiation/consortium/partners.json`: extract the list of `partner_id` values.
  - If either file is absent: record as Assumed in a note field — do not halt. The checkpoint can still be published; the absence of Tier 3 snapshot data is a gap but not a blocking failure at this point (the Phase 8 gate has already confirmed Tier 3 completeness).
- Step 2.3: Set `status` to "published". This field must equal exactly "published" — no other value is valid for a gate-satisfying checkpoint.
- Step 2.4: Set `published_at` to the ISO 8601 timestamp at the moment of checkpoint publication (current time at write time).
- Step 2.5: Set `run_id` to the current invoking agent's run_id parameter.

### 3. Output Construction

**`phase8_checkpoint.json`:**
- `schema_id`: set to "orch.checkpoints.phase8_checkpoint.v1"
- `run_id`: from invoking agent's run_id context parameter
- `status`: set to "published"
- `published_at`: ISO 8601 timestamp at write time
- `gate_results_confirmed`: derived from Step 2.1 — array of gate_id strings: ["gate_09_budget_consistency", "gate_10_part_b_completeness", "gate_11_review_closure", "gate_12_constitutional_compliance"]

### 4. Conformance Stamping

- `schema_id`: set to "orch.checkpoints.phase8_checkpoint.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: this field does NOT apply to checkpoint artifacts — do not add it

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier4_orchestration_state/checkpoints/` if not present.
- Step 5.2: Write `phase8_checkpoint.json` to `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`.
- Note: once written with `status: "published"`, this file must never be overwritten by any subsequent invocation of this skill (enforced by Step 1.1 on future invocations).

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
