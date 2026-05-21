---
skill_id: milestone-consistency-check
purpose_summary: >
  Verify milestone due months against deliverable due months and (when available)
  task schedule, confirming every milestone has a verifiable achievement criterion
  testable at its stated due month.  Operates in dual mode: DEGRADED (WP-level
  validation only, when gantt.json is absent) or FULL (schedule-level validation,
  when gantt.json is present).
used_by_agents:
  - gantt_designer
  - wp_designer
  - implementation_architect
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
input_optionality:
  wp_structure.json:
    required: true
    behavior: "Always required.  Absence triggers MISSING_INPUT failure."
  gantt.json:
    required: false
    behavior:
      - "If present → FULL validation mode (schedule-level checks)"
      - "If absent  → DEGRADED validation mode (WP-level checks only)"
constitutional_constraints:
  - "Milestones with non-verifiable criteria must be flagged"
  - "Milestone due months must be consistent with task completion months (FULL mode) or WP duration bounds (DEGRADED mode)"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Required | Fields Extracted | Schema ID | Purpose |
|------|--------------------|----------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | **YES** | work_packages[].wp_id, title, start_month, end_month (or duration); work_packages[].deliverables[].deliverable_id, due_month; work_packages[].tasks[].task_id; milestones data (if represented at WP level) | `orch.phase3.wp_structure.v1` | Provides WP structure, deliverable due months, and task identifiers.  In DEGRADED mode this is the sole validation source. |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | gantt.json — canonical Phase 4 artifact | **NO — optional** | milestones[].milestone_id, due_month, verifiable_criterion, responsible_wp; tasks[].task_id, start_month, end_month | `orch.phase4.gantt.v1` | When present, enables FULL validation: milestone due months checked against task end_months; verifiable_criterion checked for non-empty, concrete statement.  When absent, skill operates in DEGRADED mode using wp_structure.json only. |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/validation_reports/` | Per-invocation validation report file (e.g., `milestone_consistency_<timestamp>.json`) | N/A — validation report (no canonical schema_id in artifact_schema_specification.yaml for individual validation report entries) | report_id; skill_id: "milestone-consistency-check"; invoking_agent; run_id_reference; **mode**: "DEGRADED" or "FULL"; **validated_scope**: array of input artifact names validated; findings array (milestone_id, due_month, task_completion_month or null, verifiable_criterion_present boolean, consistency_status: consistent/flagged, flag_reason); summary (total_milestones_checked, passed, flagged); timestamp | No — validation reports are not phase output canonical artifacts | In FULL mode: findings derived by comparing gantt.json milestones[].due_month against tasks[].end_month for tasks in the same WP; verifiable_criterion_present derived from non-empty check of gantt.json milestones[].verifiable_criterion.  In DEGRADED mode: findings derived from wp_structure.json deliverable/milestone due_month bounds and verifiable_criterion checks against WP duration. |

**Note:** The validation_reports directory is not registered as a discrete artifact in the artifact_registry. Validation report files are durable outputs written there by convention by multiple skills. The invoking agent (gantt_designer, wp_designer, or implementation_architect) determines the report file naming.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/validation_reports/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent: n03_wp_design, n04_gantt_milestones, or n06_implementation_architecture per invoking agent) |

## Execution Specification

### 0. Mode Detection

- Step 0.1: Check whether `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` exists on disk.
- Step 0.2: **If gantt.json exists** → set `validation_mode = "FULL"`.
- Step 0.3: **If gantt.json does not exist** → set `validation_mode = "DEGRADED"`.
- Step 0.4: Record the selected mode. This value is written to the output report's `mode` field.

**Rationale:** gantt.json is a Phase 4 artifact. When this skill is invoked during Phase 3 (n03_wp_design), gantt.json does not yet exist. Failing on its absence would be a phase-leakage defect — the skill would fail not because of an actual inconsistency but because a downstream artifact has not yet been produced. DEGRADED mode validates what can be validated from WP structure alone, without referencing task schedules or dependency graph timing.

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="wp_structure.json not found") and halt.
- Step 1.2: Schema conformance check — confirm `wp_structure.json` has `schema_id` = "orch.phase3.wp_structure.v1". If mismatch: return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="wp_structure.json schema_id mismatch") and halt.
- Step 1.3 **(FULL mode only):** Schema conformance check — confirm `gantt.json` has `schema_id` = "orch.phase4.gantt.v1". If mismatch: return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="gantt.json schema_id mismatch") and halt.
- Step 1.4 **(FULL mode only):** Non-empty checks — confirm `gantt.json` has a non-empty `milestones` array and a non-empty `tasks` array. If either is empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="gantt.json milestones or tasks array is empty") and halt.

### 2. Core Processing Logic

#### 2A. DEGRADED Mode (Phase 3 — WP-level validation)

Activated when `validation_mode == "DEGRADED"`.

Uses ONLY `wp_structure.json`. Does NOT reference tasks, schedule sequencing, or dependency graph timing.

- Step 2A.1: Extract the project duration from the invoking context or from `wp_structure.json` metadata (if available). If project duration is not determinable, use the maximum `end_month` across all WPs as the upper bound.

- Step 2A.2: Build a **milestone inventory**. Collect milestones from:
  - `wp_structure.json` top-level `milestones` array (if present), OR
  - `milestones_seed.json` from Tier 3 architecture inputs (as fallback reference for milestone metadata if wp_structure.json does not embed milestones directly).
  If no milestones are found in either source, record a single finding: `consistency_status: "flagged"`, `flag_reason: "No milestones found in wp_structure.json or milestones_seed.json; cannot perform milestone consistency validation"`. Proceed to output construction (do not halt — absence of milestones is a valid finding, not a MISSING_INPUT failure).

- Step 2A.3: Build a **WP duration bounds map** from `wp_structure.json`: for each WP, record `{ wp_id, start_month, end_month }`. Derive `start_month` from the WP's declared start or M1 if undeclared; derive `end_month` from the WP's declared end or the latest deliverable `due_month` within the WP.

- Step 2A.4: For each milestone in the milestone inventory:
  - Step 2A.4.1: **Unique ID check** — verify `milestone_id` is unique across all milestones. If duplicate: record finding with `consistency_status: "flagged"`, `flag_reason: "Duplicate milestone_id '<id>'; milestone IDs must be unique"`.
  - Step 2A.4.2: **WP linkage check** — verify the milestone is linked to at least one WP (via `responsible_wp` or `linked_wps`). If not linked to any WP: record finding with `consistency_status: "flagged"`, `flag_reason: "Milestone '<id>' is not linked to any work package"`.
  - Step 2A.4.3: **Duration bounds check** — if `responsible_wp` is identified, verify `milestone.due_month` falls within the WP's duration bounds (≥ WP start_month and ≤ WP end_month). Also verify `due_month` does not exceed project duration. If out of bounds: record finding with `consistency_status: "flagged"`, `flag_reason: "Milestone due_month (<m>) is outside WP '<wp_id>' duration bounds (<start>–<end>)"` or `"Milestone due_month (<m>) exceeds project duration (<d>)"`.
  - Step 2A.4.4: **Verifiable criterion check** — identical to Step 2.4.3 in FULL mode (see below). The field must be a non-empty string and must not be a placeholder.
  - Step 2A.4.5: **Deliverable–milestone alignment check** — for each WP linked to the milestone, check whether at least one deliverable has a `due_month` that is ≤ the milestone `due_month`. If no deliverable precedes or coincides with the milestone: record finding with `consistency_status: "flagged"`, `flag_reason: "Milestone '<id>' at M<m> has no preceding or coinciding deliverable in WP '<wp_id>'; logical alignment unclear"`. This is advisory, not necessarily invalid.
  - Step 2A.4.6: Build the finding record: `{ milestone_id, due_month, task_completion_month: null, verifiable_criterion_present: boolean, consistency_status: "consistent"/"flagged", flag_reason: string or null }`. Note: `task_completion_month` is always `null` in DEGRADED mode (no task schedule available).

- Step 2A.5: Count results: `total_milestones_checked`, `passed` (consistency_status = "consistent" AND verifiable_criterion_present = true), `flagged` (any other combination).

#### 2B. FULL Mode (Phase 4+ — schedule-level validation)

Activated when `validation_mode == "FULL"`.

Uses both `wp_structure.json` and `gantt.json`.

- Step 2B.1: Build a **task schedule map** from `gantt.json`: for each task entry, record `{ task_id, wp_id, start_month, end_month }`. Key the map by `task_id`.
- Step 2B.2: Build a **WP task completion month map**: for each `wp_id`, find all tasks in the task schedule map that have this `wp_id`. Compute `max_task_end_month[wp_id]` = the maximum `end_month` value across all tasks in that WP. Additionally, build a **task end month lookup**: for each `task_id`, record its `end_month` and `wp_id`. Key by `task_id`.
- Step 2B.3: Build a **deliverable due month map** from `wp_structure.json`: for each WP, for each deliverable, record `deliverable_id`, `wp_id`, `due_month`. Key by `deliverable_id`.
- Step 2B.4: For each milestone in `gantt.json milestones[]`:
  - Step 2B.4.1: Look up `responsible_wp` in `max_task_end_month`. If `responsible_wp` is not found in the map (i.e., the WP has no tasks in gantt.json): record a finding with `consistency_status: "flagged"`, `flag_reason: "Milestone responsible_wp '<wp_id>' has no tasks in gantt.json; cannot validate timing"`.
  - Step 2B.4.2: **Three-tier milestone timing validation.** Evaluate the milestone using the first applicable tier:

    **Tier A — Explicit task-dependency validation (highest priority):**
    If the milestone has a `depends_on_tasks` field that is a non-empty array:
    - **Structural check — cross-WP reference:** For each `task_id` in `depends_on_tasks`, look up the task in the task schedule map. If the task's `wp_id` does not match the milestone's `responsible_wp`: record with `consistency_status: "flagged"`, `flag_reason: "depends_on_tasks task '<task_id>' belongs to WP '<wp_id>', not responsible_wp '<responsible_wp>'"`, `flag_class: "structural"`. This is a structural error in the milestone's dependency declaration.
    - If any `task_id` in `depends_on_tasks` is not found in the task schedule map at all: record with `consistency_status: "flagged"`, `flag_reason: "depends_on_tasks references unknown task_id '<id>'"`, `flag_class: "structural"`.
    - If all structural checks pass: compute `max_dependent_end_month` = max(`end_month` for each `task_id` in `depends_on_tasks`). If `milestone.due_month` >= `max_dependent_end_month`: record with `consistency_status: "consistent"`, `flag_class: "task_dependency"`. If `milestone.due_month` < `max_dependent_end_month`: record with `consistency_status: "flagged"`, `flag_reason: "Milestone due_month (<m>) precedes completion of dependent tasks (max end_month of depends_on_tasks: <n>)"`, `flag_class: "task_dependency"`.
    - Do NOT also check against `max_task_end_month[responsible_wp]`. Explicit task dependency supersedes the WP-level heuristic.

    **Tier B — WP-completion validation:**
    If the milestone has `milestone_type == "wp_completion"` AND `depends_on_tasks` is absent or empty:
    - Compare `milestone.due_month` against `max_task_end_month[responsible_wp]`. If `milestone.due_month` >= `max_task_end_month[responsible_wp]`: record with `consistency_status: "consistent"`, `flag_class: "wp_completion"`. If `milestone.due_month` < `max_task_end_month[responsible_wp]`: record with `consistency_status: "flagged"`, `flag_reason: "wp_completion milestone due_month (<m>) precedes completion of all tasks in responsible WP (max task end_month: <n>)"`, `flag_class: "wp_completion"`.

    **Tier C — Heuristic fallback (no explicit semantics):**
    If neither `depends_on_tasks` (or it is empty) NOR `milestone_type` is present:
    - Compare `milestone.due_month` against `max_task_end_month[responsible_wp]`. If `milestone.due_month` >= `max_task_end_month[responsible_wp]`: record with `consistency_status: "consistent"`, `flag_class: "heuristic"`. If `milestone.due_month` < `max_task_end_month[responsible_wp]`: record with `consistency_status: "flagged"`, `flag_reason: "Milestone due_month (<m>) precedes completion of all tasks in responsible WP (max task end_month: <n>); no depends_on_tasks or milestone_type specified — flagged as heuristic"`, `flag_class: "heuristic"`. This preserves the current behavior for milestones without explicit dependency semantics.
  - Step 2B.4.3: Check `verifiable_criterion` for the milestone: the field must be a non-empty string. Additionally, check whether the value is a placeholder — any of the following constitute a non-verifiable criterion: empty string, "TBD", "to be defined", "to be determined", "N/A", "placeholder". If the criterion is empty or a placeholder: record `verifiable_criterion_present: false` and add flag_reason: "verifiable_criterion is absent or a placeholder; must be a concrete, externally observable statement of milestone achievement". Otherwise set `verifiable_criterion_present: true`.
  - Step 2B.4.4: Build the finding record: `{ milestone_id, due_month: milestone.due_month, task_completion_month: <see below>, verifiable_criterion_present: boolean, consistency_status: "consistent"/"flagged", flag_reason: string or null, flag_class: string or null }`. The `task_completion_month` value depends on which tier was applied: Tier A sets it to `max_dependent_end_month` (the max end_month of tasks in depends_on_tasks); Tiers B and C set it to `max_task_end_month[responsible_wp]` (unchanged from prior behavior). The `flag_class` field is one of: `"task_dependency"` (Tier A), `"wp_completion"` (Tier B), `"heuristic"` (Tier C), or `"structural"` (cross-WP or unknown task_id reference). `flag_class` is present only in FULL mode findings.
- Step 2B.5: Count results: `total_milestones_checked`, `passed` (consistency_status = "consistent" AND verifiable_criterion_present = true), `flagged` (any other combination).

### 3. Output Construction

**Validation report file (e.g., `milestone_consistency_<agent_id>_<timestamp>.json`):**
- `report_id`: string — `"milestone_consistency_<agent_id>_<ISO8601_timestamp>"`
- `skill_id`: string — `"milestone-consistency-check"`
- `invoking_agent`: string — from agent context
- `run_id_reference`: string — current run_id from agent context
- `mode`: string — `"DEGRADED"` or `"FULL"` (from Step 0)
- `validated_scope`: array of strings — `["wp_structure"]` in DEGRADED mode; `["wp_structure", "gantt"]` in FULL mode
- `findings`: array — derived from Step 2A.4 (DEGRADED) or Step 2B.4 (FULL) — each entry: `{milestone_id, due_month, task_completion_month, verifiable_criterion_present, consistency_status, flag_reason, flag_class}`. The `flag_class` field is present only in FULL mode findings and is one of: `"task_dependency"`, `"wp_completion"`, `"heuristic"`, or `"structural"`
- `summary`: object — derived from Step 2A.5 (DEGRADED) or Step 2B.5 (FULL) — `{total_milestones_checked, passed, flagged}`
- `timestamp`: ISO 8601 timestamp

### 4. Conformance Stamping

Validation reports are not phase output canonical artifacts. No `schema_id`, `artifact_status` field applies.

### 5. Write Sequence

- Step 5.1: Write the validation report to `docs/tier4_orchestration_state/validation_reports/<report_id>.json`

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Milestones with non-verifiable criteria must be flagged"

**Decision point in execution logic:** Step 2A.4.4 (DEGRADED mode) or Step 2B.4.3 (FULL mode) — at the point each milestone's `verifiable_criterion` field is evaluated for adequacy.

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

**Applies in both modes:** This constraint is enforced identically in DEGRADED and FULL modes. The verifiable_criterion check does not depend on gantt.json data.

**Failure output:** Individual milestone failures → recorded as findings with `verifiable_criterion_present: false` in the report (not a SkillResult failure); report write failure → SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT").

**Hard failure confirmation:** Yes — every non-verifiable criterion must produce a flagged finding in the report; silently passing it is prohibited.

**CLAUDE.md §13 cross-reference:** §12.2 — validation status vocabulary requires accurate flagging; accepting a non-verifiable criterion as "consistent" is equivalent to assigning "Confirmed" status without evidence. §7 Phase 4 gate — "All milestones have a defined verifiable criterion."

---

### Constraint 2: "Milestone due months must be consistent with task completion months (FULL mode) or WP duration bounds (DEGRADED mode)"

**Decision point in execution logic:** Step 2B.4.2 (FULL mode) — milestone due_month vs. max_task_end_month comparison; Step 2A.4.3 (DEGRADED mode) — milestone due_month vs. WP duration bounds comparison.

**Exact failure condition (FULL mode):** A milestone's `due_month` is earlier than the applicable task completion reference (determined by three-tier validation: Tier A uses max end_month of `depends_on_tasks` when present; Tier B uses max end_month of all WP tasks for `wp_completion` milestones; Tier C uses max end_month of all WP tasks as heuristic fallback), AND the finding is NOT written with `consistency_status: "flagged"` in the validation report. OR: the comparison is performed but the flag is suppressed or overridden to "consistent" by agent judgment. Additionally, any `depends_on_tasks` entry referencing a task_id not found in the task schedule map, or referencing a task whose `wp_id` does not match `responsible_wp`, must be flagged with `flag_class: "structural"`.

**Exact failure condition (DEGRADED mode):** A milestone's `due_month` falls outside the duration bounds of its responsible WP, or exceeds the project duration, AND the finding is NOT written with `consistency_status: "flagged"`.

**Enforcement mechanism:** In both modes, the timing comparison is deterministic. When the condition holds, `consistency_status` must be set to "flagged" — no agent override is permitted. The `flag_reason` must state the specific values so the issue is human-reviewable. The `flag_class` must accurately identify which validation tier was applied. Setting `consistency_status: "consistent"` when the condition holds is a constitutional violation.

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
- Step 1.4 (FULL mode only): `gantt.json` has an empty `milestones` array or empty `tasks` array → `failure_reason="gantt.json milestones or tasks array is empty"`

**NOT a trigger:** Absence of `gantt.json` is NOT a MISSING_INPUT condition. It triggers DEGRADED mode (Step 0.3), not a failure.

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.2: `wp_structure.json` has `schema_id` ≠ "orch.phase3.wp_structure.v1" → `failure_reason="wp_structure.json schema_id mismatch"`
- Step 1.3 (FULL mode only): `gantt.json` has `schema_id` ≠ "orch.phase4.gantt.v1" → `failure_reason="gantt.json schema_id mismatch"`

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
- Constraint 2 (milestone due months consistent with task completion months / WP duration bounds): Validation report write fails after a timing inconsistency is identified → `failure_reason="<write error>"`
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
6. **Absence of gantt.json is never a failure.** It triggers DEGRADED mode, which performs WP-level validation. This is a correct and complete validation for the Phase 3 invocation context.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. This is a Group C skill whose sole output is a validation report file in `docs/tier4_orchestration_state/validation_reports/`. There is no canonical `schema_id` in `artifact_schema_specification.yaml` for individual validation reports; conformance is governed by CLAUDE.md §12.1 (reviewability) and §12.2 (validation status vocabulary).*

---

### Upstream input schema verification

- **`wp_structure.json`** (`orch.phase3.wp_structure.v1`) — skill reads `work_packages[].deliverables[].due_month`, `work_packages[].tasks[].task_id`, and WP-level duration fields. Field path matches spec §1.3. Compliant.
- **`gantt.json`** (`orch.phase4.gantt.v1`) — **FULL mode only.** Skill reads `milestones[].milestone_id, due_month, verifiable_criterion, responsible_wp, depends_on_tasks (optional), milestone_type (optional)` and `tasks[].task_id, wp_id, start_month, end_month`. All field names match spec §1.4 exactly. The optional fields `depends_on_tasks` and `milestone_type` enable three-tier validation when present; their absence triggers Tier C heuristic fallback. Compliant. In DEGRADED mode, this artifact is not read.

### Artifact: `milestone_consistency_<agent_id>_<timestamp>.json` (validation report)

**Canonical schema:** None — validation reports are operational artifacts not defined in the schema registry.

**Output Construction fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `report_id` | Yes (Step 3) | skill-defined | Yes |
| `skill_id` | Yes — "milestone-consistency-check" | matches frontmatter | Yes |
| `invoking_agent` | Yes | agent context | Yes |
| `run_id_reference` | Yes | current run_id from agent context | Yes |
| `mode` | Yes (Step 0, Step 3) | "DEGRADED" or "FULL" | Yes |
| `validated_scope` | Yes (Step 3) | ["wp_structure"] or ["wp_structure", "gantt"] | Yes |
| `findings[]` | Yes (Step 2A.4 or 2B.4, Step 3) | each finding: milestone_id, due_month, task_completion_month (null in DEGRADED), verifiable_criterion_present (bool), consistency_status (enum: consistent/flagged), flag_reason, flag_class (FULL mode only: task_dependency/wp_completion/heuristic/structural) | Yes |
| `summary` | Yes (Step 2A.5 or 2B.5, Step 3) | total_milestones_checked/passed/flagged | Yes |
| `timestamp` | Yes | ISO 8601 | Yes |

**CLAUDE.md §12.2 vocabulary note:** The skill's finding-level `consistency_status` (consistent/flagged) is domain-specific scheduling vocabulary. This is an operational classification distinct from the §12.2 Confirmed/Inferred/Assumed/Unresolved enum, which applies to evaluated-element statuses in validation reports. Where a flagged finding could be mapped to §12.2: a timing inconsistency corresponds to "Unresolved" (requires human resolution before downstream use); a non-verifiable criterion corresponds to "Unresolved". The skill's `flag_reason` field satisfies the §12.2 requirement to declare the basis for the non-Confirmed status. No correction required — the operational vocabulary is consistent with §12.2 semantics.

**`schema_id` / `run_id` / `artifact_status`:** Step 4 correctly states these fields do not apply to validation report files. `run_id_reference` is an informational back-pointer, not the same as the canonical `run_id` that would require stamping.

**reads_from compliance:** Declared paths in frontmatter match the paths read in Steps 1.1–1.4. `gantt.json` path is declared in `reads_from` to cover FULL mode; its absence in DEGRADED mode is handled by Step 0, not by omitting the declaration. Compliant.

**writes_to compliance:** Writes only to `docs/tier4_orchestration_state/validation_reports/`. Declared in frontmatter. Compliant.

**Gaps identified:** None.

**Corrections applied:** None.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
