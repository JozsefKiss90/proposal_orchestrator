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

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
