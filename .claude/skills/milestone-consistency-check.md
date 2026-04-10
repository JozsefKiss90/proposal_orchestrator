---
skill_id: milestone-consistency-check
purpose_summary: >
  Verify milestone due months against task schedule and deliverable due months,
  confirming every milestone has a verifiable achievement criterion testable at its
  stated due month.
used_by_agents:
  - gantt_designer
  - wp_designer
  - implementation_architect
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
constitutional_constraints:
  - "Milestones with non-verifiable criteria must be flagged"
  - "Milestone due months must be consistent with task completion months"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].deliverables[].deliverable_id, due_month; work_packages[].tasks[].task_id | `orch.phase3.wp_structure.v1` | Provides deliverable due months and task identifiers to cross-reference against milestone due months and task schedule in Phase 4 |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | gantt.json — canonical Phase 4 artifact | milestones[].milestone_id, due_month, verifiable_criterion, responsible_wp; tasks[].task_id, start_month, end_month | `orch.phase4.gantt.v1` | Primary artifact being validated: milestone due months checked against task end_months; verifiable_criterion checked for non-empty, concrete statement |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/validation_reports/` | Per-invocation validation report file (e.g., `milestone_consistency_<timestamp>.json`) | N/A — validation report (no canonical schema_id in artifact_schema_specification.yaml for individual validation report entries) | report_id; skill_id: "milestone-consistency-check"; invoking_agent; run_id_reference; findings array (milestone_id, due_month, task_completion_month, verifiable_criterion_present boolean, consistency_status: consistent/flagged, flag_reason); summary (total_milestones_checked, passed, flagged); timestamp | No — validation reports are not phase output canonical artifacts | findings derived by comparing gantt.json milestones[].due_month against tasks[].end_month for tasks in the same WP; verifiable_criterion_present derived from non-empty check of gantt.json milestones[].verifiable_criterion |

**Note:** The validation_reports directory is not registered as a discrete artifact in the artifact_registry. Validation report files are durable outputs written there by convention by multiple skills. The invoking agent (gantt_designer, wp_designer, or implementation_architect) determines the report file naming.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/validation_reports/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent: n03_wp_design, n04_gantt_milestones, or n06_implementation_architecture per invoking agent) |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="wp_structure.json not found") and halt.
- Step 1.2: Schema conformance check — confirm `wp_structure.json` has `schema_id` = "orch.phase3.wp_structure.v1". If mismatch: return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="wp_structure.json schema_id mismatch") and halt.
- Step 1.3: Presence check — confirm `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="gantt.json not found; gantt_designer must produce gantt.json before milestone-consistency-check") and halt.
- Step 1.4: Schema conformance check — confirm `gantt.json` has `schema_id` = "orch.phase4.gantt.v1". If mismatch: return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="gantt.json schema_id mismatch") and halt.
- Step 1.5: Non-empty checks — confirm `gantt.json` has a non-empty `milestones` array and a non-empty `tasks` array. If either is empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="gantt.json milestones or tasks array is empty") and halt.

### 2. Core Processing Logic

- Step 2.1: Build a **task schedule map** from `gantt.json`: for each task entry, record `{ task_id, wp_id, start_month, end_month }`. Key the map by `task_id`.
- Step 2.2: Build a **WP task completion month map**: for each `wp_id`, find all tasks in the task schedule map that have this `wp_id`. Compute `max_task_end_month[wp_id]` = the maximum `end_month` value across all tasks in that WP.
- Step 2.3: Build a **deliverable due month map** from `wp_structure.json`: for each WP, for each deliverable, record `deliverable_id`, `wp_id`, `due_month`. Key by `deliverable_id`.
- Step 2.4: For each milestone in `gantt.json milestones[]`:
  - Step 2.4.1: Look up `responsible_wp` in `max_task_end_month`. If `responsible_wp` is not found in the map (i.e., the WP has no tasks in gantt.json): record a finding with `consistency_status: "flagged"`, `flag_reason: "Milestone responsible_wp '<wp_id>' has no tasks in gantt.json; cannot validate timing"`.
  - Step 2.4.2: If `responsible_wp` is found: compare `milestone.due_month` against `max_task_end_month[responsible_wp]`. If `milestone.due_month` < `max_task_end_month[responsible_wp]`: record a finding with `consistency_status: "flagged"`, `flag_reason: "Milestone due_month (<m>) precedes completion of all tasks in responsible WP (max task end_month: <n>); milestone may be achieved before all contributing tasks complete"`. This is flagged but not necessarily invalid — record for human review. If `milestone.due_month` >= `max_task_end_month[responsible_wp]`: record with `consistency_status: "consistent"`.
  - Step 2.4.3: Check `verifiable_criterion` for the milestone: the field must be a non-empty string. Additionally, check whether the value is a placeholder — any of the following constitute a non-verifiable criterion: empty string, "TBD", "to be defined", "to be determined", "N/A", "placeholder". If the criterion is empty or a placeholder: record `verifiable_criterion_present: false` and add flag_reason: "verifiable_criterion is absent or a placeholder; must be a concrete, externally observable statement of milestone achievement". Otherwise set `verifiable_criterion_present: true`.
  - Step 2.4.4: Build the finding record: `{ milestone_id, due_month: milestone.due_month, task_completion_month: max_task_end_month[responsible_wp] or null, verifiable_criterion_present: boolean, consistency_status: "consistent"/"flagged", flag_reason: string or null }`.
- Step 2.5: Count results: `total_milestones_checked`, `passed` (consistency_status = "consistent" AND verifiable_criterion_present = true), `flagged` (any other combination).

### 3. Output Construction

**Validation report file (e.g., `milestone_consistency_<agent_id>_<timestamp>.json`):**
- `report_id`: string — `"milestone_consistency_<agent_id>_<ISO8601_timestamp>"`
- `skill_id`: string — `"milestone-consistency-check"`
- `invoking_agent`: string — from agent context
- `run_id_reference`: string — current run_id from agent context
- `findings`: array — derived from Step 2.4 — each entry: `{milestone_id, due_month, task_completion_month, verifiable_criterion_present, consistency_status, flag_reason}`
- `summary`: object — derived from Step 2.5 — `{total_milestones_checked, passed, flagged}`
- `timestamp`: ISO 8601 timestamp

### 4. Conformance Stamping

Validation reports are not phase output canonical artifacts. No `schema_id`, `artifact_status` field applies.

### 5. Write Sequence

- Step 5.1: Write the validation report to `docs/tier4_orchestration_state/validation_reports/<report_id>.json`

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Milestones with non-verifiable criteria must be flagged"

**Decision point in execution logic:** Step 2.4.3 — at the point each milestone's `verifiable_criterion` field is evaluated for adequacy.

**Exact failure condition:** Any milestone has a `verifiable_criterion` that is empty, null, or a placeholder string (TBD, "to be defined", "to be determined", "N/A", "placeholder"), AND the corresponding finding is NOT written to the validation report with `verifiable_criterion_present: false` and an appropriate `flag_reason`.

**Enforcement mechanism:**

DETERMINISTIC WRITE RULE:
IF `verifiable_criterion` is empty OR is one of {TBD, "to be defined", "to be determined", N/A, placeholder} (case-insensitive):
→ `verifiable_criterion_present` MUST be set to false
→ `flag_reason` MUST be non-empty
→ THEN write to validation report

IF validation report write fails after the above:
→ return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Validation report write failed; milestones with non-verifiable criteria must be flagged in the durable validation report per skill constitutional constraints and CLAUDE.md §12.2")

Omitting this flag or recording `verifiable_criterion_present: true` for a placeholder is a constitutional violation. There is no threshold below which a non-verifiable criterion can be silently accepted.

**Failure output:** Individual milestone failures → recorded as findings with `verifiable_criterion_present: false` in the report (not a SkillResult failure); report write failure → SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT").

**Hard failure confirmation:** Yes — every non-verifiable criterion must produce a flagged finding in the report; silently passing it is prohibited.

**CLAUDE.md §13 cross-reference:** §12.2 — validation status vocabulary requires accurate flagging; accepting a non-verifiable criterion as "consistent" is equivalent to assigning "Confirmed" status without evidence. §7 Phase 4 gate — "All milestones have a defined verifiable criterion."

---

### Constraint 2: "Milestone due months must be consistent with task completion months"

**Decision point in execution logic:** Step 2.4.2 — at the point each milestone's `due_month` is compared against `max_task_end_month[responsible_wp]`.

**Exact failure condition:** A milestone's `due_month` is earlier than the latest task `end_month` for its `responsible_wp`, AND the finding is NOT written with `consistency_status: "flagged"` in the validation report. OR: the comparison is performed but the flag is suppressed or overridden to "consistent" by agent judgment.

**Enforcement mechanism:** In Step 2.4.2, the timing comparison is deterministic: if `milestone.due_month < max_task_end_month[responsible_wp]`, `consistency_status` must be set to "flagged" — no agent override is permitted. The `flag_reason` must state the specific due_month and max task end_month values so the issue is human-reviewable. Setting `consistency_status: "consistent"` when this condition holds is a constitutional violation. The check must fire for every milestone; there is no skip condition.

**Failure output:** Individual inconsistency → recorded as `consistency_status: "flagged"` in findings (not a SkillResult failure; the gate will fail on this). Report write failure → SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT").

**Hard failure confirmation:** Yes — timing inconsistency must be flagged in the report; suppressing the flag is prohibited.

**CLAUDE.md §13 cross-reference:** §7 Phase 4 gate condition — "All tasks are assigned to months … No critical path dependency is unresolved." Milestone-task timing inconsistencies are gate-relevant and must be surfaced. §15 — explicit gate failure (via flagged findings) is preferred over fabricated completion.

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` does not exist → `failure_reason="wp_structure.json not found"`
- Step 1.3: `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` does not exist → `failure_reason="gantt.json not found; gantt_designer must produce gantt.json before milestone-consistency-check"`
- Step 1.5: `gantt.json` has an empty `milestones` array or empty `tasks` array → `failure_reason="gantt.json milestones or tasks array is empty"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.2: `wp_structure.json` has `schema_id` ≠ "orch.phase3.wp_structure.v1" → `failure_reason="wp_structure.json schema_id mismatch"`
- Step 1.4: `gantt.json` has `schema_id` ≠ "orch.phase4.gantt.v1" → `failure_reason="gantt.json schema_id mismatch"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Skill halts immediately.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use INCOMPLETE_OUTPUT (validation report write failure) as appropriate. Individual milestone findings are written to the validation report as `consistency_status: "flagged"` entries — not as SkillResult failures.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 1 (milestones with non-verifiable criteria must be flagged): Validation report write fails after a non-verifiable criterion is identified → `failure_reason="Validation report write failed; milestones with non-verifiable criteria must be flagged in the durable validation report per skill constitutional constraints and CLAUDE.md §12.2"`
- Constraint 2 (milestone due months consistent with task completion months): Validation report write fails after a timing inconsistency is identified → `failure_reason="<write error>"`
- Step 5.1: Validation report write fails for any reason → `failure_reason="Validation report could not be written to validation_reports/"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
No CONSTITUTIONAL_HALT conditions are defined for this skill. Individual milestone failures (non-verifiable criterion, timing inconsistency) are recorded as flagged findings in the validation report, not as CONSTITUTIONAL_HALT. The skill's constitutional constraints are enforced through the completeness of reporting, not through halting on individual milestone failures.

**Artifact write behavior:** Not applicable.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: this skill's `writes_to` includes `docs/tier4_orchestration_state/validation_reports/`; a failure record MAY be written there even when the primary output fails — but only if the directory is accessible.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. This is a Group C skill whose sole output is a validation report file in `docs/tier4_orchestration_state/validation_reports/`. There is no canonical `schema_id` in `artifact_schema_specification.yaml` for individual validation reports; conformance is governed by CLAUDE.md §12.1 (reviewability) and §12.2 (validation status vocabulary).*

---

### Upstream input schema verification

- **`wp_structure.json`** (`orch.phase3.wp_structure.v1`) — skill reads `work_packages[].deliverables[].due_month` and `work_packages[].tasks[].task_id`. Field path matches spec §1.3. Compliant.
- **`gantt.json`** (`orch.phase4.gantt.v1`) — skill reads `milestones[].milestone_id, due_month, verifiable_criterion, responsible_wp` and `tasks[].task_id, wp_id, start_month, end_month`. All field names match spec §1.4 exactly. Compliant.

### Artifact: `milestone_consistency_<agent_id>_<timestamp>.json` (validation report)

**Canonical schema:** None — validation reports are operational artifacts not defined in the schema registry.

**Output Construction fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `report_id` | Yes (Step 3) | skill-defined | Yes |
| `skill_id` | Yes — "milestone-consistency-check" | matches frontmatter | Yes |
| `invoking_agent` | Yes | agent context | Yes |
| `run_id_reference` | Yes | current run_id from agent context | Yes |
| `findings[]` | Yes (Step 2.4, Step 3) | each finding: milestone_id, due_month, task_completion_month, verifiable_criterion_present (bool), consistency_status (enum: consistent/flagged), flag_reason | Yes |
| `summary` | Yes (Step 2.5, Step 3) | total_milestones_checked/passed/flagged | Yes |
| `timestamp` | Yes | ISO 8601 | Yes |

**CLAUDE.md §12.2 vocabulary note:** The skill's finding-level `consistency_status` (consistent/flagged) is domain-specific scheduling vocabulary. This is an operational classification distinct from the §12.2 Confirmed/Inferred/Assumed/Unresolved enum, which applies to evaluated-element statuses in validation reports. Where a flagged finding could be mapped to §12.2: a timing inconsistency corresponds to "Unresolved" (requires human resolution before downstream use); a non-verifiable criterion corresponds to "Unresolved". The skill's `flag_reason` field satisfies the §12.2 requirement to declare the basis for the non-Confirmed status. No correction required — the operational vocabulary is consistent with §12.2 semantics.

**`schema_id` / `run_id` / `artifact_status`:** Step 4 correctly states these fields do not apply to validation report files. `run_id_reference` is an informational back-pointer, not the same as the canonical `run_id` that would require stamping.

**reads_from compliance:** Declared paths in frontmatter match the paths read in Steps 1.1–1.4. Compliant.

**writes_to compliance:** Writes only to `docs/tier4_orchestration_state/validation_reports/`. Declared in frontmatter. Compliant.

**Gaps identified:** None.

**Corrections applied:** None.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
