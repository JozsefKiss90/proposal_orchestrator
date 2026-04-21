---
skill_id: gantt-schedule-builder
purpose_summary: >
  Assign all tasks to months consistent with the normalized dependency constraints,
  define milestone due months and verifiable achievement criteria, identify the
  critical path, and produce the canonical gantt.json artifact (schema orch.phase4.gantt.v1).
used_by_agents:
  - gantt_designer
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/scheduling_constraints.json
  - docs/tier3_project_instantiation/call_binding/selected_call.json
  - docs/tier3_project_instantiation/consortium/roles.json
  - docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json
constitutional_constraints:
  - "Must not assign tasks to months beyond the project duration from selected_call.json"
  - "Must not schedule a task start before prerequisite task completion per strict constraints"
  - "Must not produce milestones without verifiable achievement criteria"
  - "Must not silently adjust project duration to accommodate scheduling conflicts"
---

## Output Nature

The output of this skill is the **canonical Phase 4 gate artifact** `gantt.json` (schema `orch.phase4.gantt.v1`). It must contain every task from `wp_structure.json` with assigned start/end months, every milestone with a verifiable criterion, and a non-empty critical path.

The scheduling decisions must respect the normalized dependency constraints from `scheduling_constraints.json`: strict constraints (task-level `finish_to_start`) enforce temporal ordering; non-strict constraints (reclassified WP-level edges, `data_input` edges) are informational and do not enforce ordering.

---

## Canonical Inputs and Outputs

### Inputs

| Path | Content | Purpose |
|------|---------|---------|
| `wp_structure.json` | WP structure with tasks, deliverables, dependency_map | Source of all task_ids, wp_ids, partner assignments |
| `scheduling_constraints.json` | Normalized strict/non-strict edge classifications | Determines which dependencies enforce temporal ordering |
| `selected_call.json` | Project duration in months | Authoritative temporal bound (`max_project_duration_months` or `project_duration_months`) |
| `roles.json` | Partner role assignments per WP | Validates task responsible_partner assignments |
| `milestones_seed.json` | Pre-existing milestone definitions | Source for milestone_id, title, due_month, verifiable_criterion |

### Output

| Path | Schema ID | Required Fields |
|------|-----------|-----------------|
| `gantt.json` | `orch.phase4.gantt.v1` | `schema_id`, `run_id`, `tasks` (array), `milestones` (array), `critical_path` (array) |

`artifact_status` must be ABSENT at write time (runner stamps post-gate).

---

## Execution Specification

### 1. Input Validation

- Step 1.1: Confirm `wp_structure.json` exists and contains a non-empty `work_packages` array and a `dependency_map` with `edges`. If absent or empty: return failure with `MISSING_INPUT`.
- Step 1.2: Confirm `scheduling_constraints.json` exists with `strict_constraints` and `non_strict_constraints` arrays. If absent: return failure with `MISSING_INPUT`.
- Step 1.3: Confirm `selected_call.json` exists and contains a project duration field (`max_project_duration_months` or `project_duration_months`). If absent or null: return failure with `MISSING_INPUT`.
- Step 1.4: Confirm `roles.json` exists. If absent: return failure with `MISSING_INPUT`.
- Step 1.5: Read `milestones_seed.json`. If it contains a `milestones` array, use those milestone definitions as the basis for the output milestones. If absent or empty, derive milestones from WP deliverable completion points.
- Step 1.6: Check `dependency_map` for cycles (`cycle_detected` field). If cycles are present: return failure with `CONSTRAINT_VIOLATION` — do not schedule tasks on a cyclic graph.

### 2. Task-to-Month Assignment

For every task in every WP in `wp_structure.json`:

- Extract WP temporal bounds from `scheduling_constraints.json` `wp_bounds` (or from `workpackage_seed.json` if referenced in wp_structure).
- Assign `start_month` and `end_month` respecting:
  - `start_month >= 1`
  - `end_month <= project_duration_months` (from `selected_call.json`)
  - For each **strict constraint** in `scheduling_constraints.json.strict_constraints`: if a strict edge `from → to` exists, the `to` task's `start_month` must be > the `from` task's `end_month`.
  - **Non-strict constraints** (data_input, reclassified WP-level edges) do NOT enforce temporal ordering — tasks may overlap.
- Each task must have: `task_id` (matching wp_structure), `wp_id` (parent WP), `start_month`, `end_month`, `responsible_partner` (from roles.json or wp_structure task data).

If any task cannot be assigned months within the project duration due to strict constraints, do NOT silently adjust the duration. Record the conflict and return the schedule as-is — the gate predicate `dependency_schedule_consistency` will catch violations.

### 3. Milestone Definition

For each milestone in `milestones_seed.json` (or derived from deliverable completion points):

- Assign `milestone_id` (from seed, or generated as "MS1", "MS2", etc.)
- Assign `title` (from seed, or derived from linked WP/deliverable)
- Assign `due_month`: must be consistent with task completion months for the linked WP. Must be ≤ project_duration_months.
- Write a `verifiable_criterion`: a concrete, externally verifiable statement. Must NOT be a placeholder like "work package completed" or "deliverables submitted". Must describe what specific evidence or result demonstrates milestone achievement.
- Assign `responsible_wp` (wp_id from wp_structure)

### 4. Critical Path Identification

Identify the critical path: the longest chain of strict-dependency-linked tasks from project start to project end.

- The critical path must be a non-empty array of `task_id` and/or `milestone_id` strings.
- Derive from the strict constraints and the task month assignments.

### 5. Output Construction

Construct `gantt.json`:

```json
{
  "schema_id": "orch.phase4.gantt.v1",
  "run_id": "<propagated from invoking context>",
  "tasks": [ ... ],
  "milestones": [ ... ],
  "critical_path": [ ... ]
}
```

Do NOT include `artifact_status` (runner-managed).

Return this as a single JSON object — no markdown wrapping, no explanatory prose.

---

## Output Minimization Rules

1. Return only one JSON object. No markdown wrapping, no commentary.
2. `tasks[].task_id` must exactly match `wp_structure.json` task_ids — do not rename.
3. `milestones[].verifiable_criterion` must be concrete and specific, not generic.
4. Do not add fields beyond those required by the schema.
5. Do not include rationale or explanatory text inside field values.

---

## Failure Protocol

### MISSING_INPUT
Missing or empty wp_structure.json, scheduling_constraints.json, selected_call.json, or roles.json. No output written.

### CONSTRAINT_VIOLATION
Dependency cycles detected in the input graph. No output written.

### INCOMPLETE_OUTPUT
If scheduling is fundamentally impossible (e.g., strict constraints create an irreconcilable conflict within the project duration), write the best-effort schedule and let the gate predicates identify specific violations. Do not fabricate completion — a schedule with acknowledged violations is a valid output; the gate determines pass/fail.

### CONSTITUTIONAL_HALT
Not applicable to this skill. Duration manipulation and partner fabrication are prevented by the constitutional constraints above.

---

## Constitutional Constraint Enforcement

### "Must not assign tasks to months beyond the project duration"
Every `tasks[].end_month` must be ≤ `project_duration_months` from `selected_call.json`. Gate predicate `timeline_within_duration` verifies this.

### "Must not schedule a task start before prerequisite task completion"
For each strict constraint `from → to` in `scheduling_constraints.json`, `to` task start_month must be > `from` task end_month. Gate predicate `dependency_schedule_consistency` verifies this.

### "Must not produce milestones without verifiable achievement criteria"
Every `milestones[].verifiable_criterion` must be non-empty and concrete. Gate predicate `all_milestones_have_criteria` verifies this.

### "Must not silently adjust project duration"
The project duration is read from `selected_call.json` and used as-is. If tasks cannot fit: produce the schedule and let the gate fail. Per CLAUDE.md §13.7: silent duration manipulation is prohibited.

---

## Runtime Contract

This skill is governed by the skill runtime contract. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
