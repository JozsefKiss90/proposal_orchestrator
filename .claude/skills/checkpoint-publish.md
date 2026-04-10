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

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Validated checkpoints must not be overwritten by subsequent reruns"

**Decision point in execution logic:** Step 1.1 — the existing checkpoint guard is applied as the very first step, before any other processing.

**Exact failure condition:** `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` already exists with `status: "published"` — AND the skill continues past Step 1.1 to overwrite it.

**Enforcement mechanism:** Step 1.1 is an unconditional pre-check. If the checkpoint file exists with `status: "published"`: return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="Validated checkpoint already exists at docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json with status: published; overwrite is constitutionally prohibited per CLAUDE.md §5 Tier 4 constraints and state_rules.yaml checkpoint_preservation rule") and halt immediately. No further steps in this invocation execute. The invoking agent must invoke `decision-log-update` to durably record the overwrite refusal — this skill does not write to the decision log. There is no override mechanism, no force-flag, no conditional path that permits overwriting a validated checkpoint. The gate status of the new run being higher or different from the original does not justify overwrite — a new checkpoint file with a different name must be produced instead if the system requires a different checkpoint record.

**Failure output:** SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION"). Immediate halt. No file written.

**Hard failure confirmation:** Yes — unconditional halt; this is a categorical prohibition with no exceptions and no override path.

**CLAUDE.md §13 cross-reference:** §5 Tier 4 — "Tier 4 may be updated by reruns, but prior checkpoint states must be preserved when a checkpoint has been formally validated." §9.4 — "Agent working memory may assist execution. It must not override documented state in docs/." A published checkpoint is formally validated state; overwriting it destroys the reproducibility record.

---

### Constraint 2: "A checkpoint must not be published before all gate conditions for the phase are met"

**Decision point in execution logic:** Step 1.2 and Step 1.3 — at the point gate result files are read and their `status` fields are evaluated.

**Exact failure condition:** (a) Any of the four required gate result files (gate_09, gate_10, gate_11, gate_12) is absent; OR (b) any gate result has `status ≠ "pass"`; OR (c) the skill writes `phase8_checkpoint.json` with `status: "published"` when any gate result condition in Steps 1.2–1.3 was not satisfied.

**Enforcement mechanism:** Steps 1.2 and 1.3 are mandatory sequential checks. If any gate result file is absent (Step 1.2): return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="Gate result file <path> not found; all four gate results required before checkpoint can be published"). If any gate result has `status ≠ "pass"` (Step 1.3): return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="Gate <gate_id> has status '<status>'; all required gates must have status 'pass' before checkpoint can be published per CLAUDE.md §6.2 and §7"). Both checks must complete and pass before Step 2 begins. If the gate check results in a failure: no `phase8_checkpoint.json` is written. A checkpoint published before all gates pass would enable Phase 8 content to be declared complete when it is not — constitutionally equivalent to fabricated completion.

**Failure output:** SkillResult(status="failure", failure_category="MISSING_INPUT") for absent gate files or non-passing gates. No `phase8_checkpoint.json` written.

**Hard failure confirmation:** Yes — publishing a checkpoint with unpassed gates is a categorical constitutional violation per CLAUDE.md §6.2.

**CLAUDE.md §13 cross-reference:** §6.2 — "Gates are mandatory. Each phase has a gate condition. A phase is not complete until its gate condition is satisfied. A downstream phase must not begin if the gate condition of any upstream phase has not been met." §15 — "A declared failure is an honest and correct output."

**Bidirectional guarantee (IF published THEN all gates provably passed):**
A checkpoint with `status: "published"` is constitutionally valid if and only if:
- `gate_results_confirmed[]` contains exactly the four required gate_ids
- Each of those gate_ids has a gate result file at its canonical path with `status: "pass"`
- All four gate result `run_id`s match the current run_id

IF `phase8_checkpoint.json` is written with `status: "published"` but any of these conditions was not verified in Steps 1.2–1.4:
→ CONSTITUTIONAL_HALT
→ return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Checkpoint published without verifiable gate passage; publishing a checkpoint without verifiable gate passage is fabricated completion per CLAUDE.md §15")

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.2: Any of the four required gate result files is absent → `failure_reason="Gate result file <path> not found; all four gate results required for checkpoint"`
- Step 1.3: Any gate result file has `status ≠ "pass"` → `failure_reason="Gate <gate_id> has status '<status>'; all required gates must have status 'pass' before checkpoint can be published"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.2: Any gate result file's `schema_id` does not match "orch.gate_result.v1" → `failure_reason="Gate result at <path> has unexpected schema_id"`
- Step 1.4: Any gate result's `run_id` does not match the current run_id → `failure_reason="Gate result at <path> has run_id '<gate_run_id>' which does not match current run_id '<current_run_id>'"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Skill halts immediately.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
- Constraint 1 (validated checkpoints must not be overwritten): `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` already exists with `status: "published"` → `failure_reason="Validated checkpoint already exists at docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json with status: published; overwrite is constitutionally prohibited per CLAUDE.md §5 Tier 4 constraints and state_rules.yaml checkpoint_preservation rule"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No file written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent must invoke decision-log-update to durably record the overwrite refusal.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
No INCOMPLETE_OUTPUT conditions are explicitly defined. Write errors at Step 5.2 should return `failure_reason="phase8_checkpoint.json could not be written"`.

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 2 bidirectional guarantee: `phase8_checkpoint.json` is written with `status: "published"` but the gate verification conditions in Steps 1.2–1.4 were not fully satisfied → `failure_reason="Checkpoint published without verifiable gate passage; publishing a checkpoint without verifiable gate passage is fabricated completion per CLAUDE.md §15"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the constitutional halt.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` is `docs/tier4_orchestration_state/checkpoints/` only; no exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->
