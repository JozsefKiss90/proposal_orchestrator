---
agent_id: gantt_designer
phase_id: phase_04_gantt_and_milestones
node_ids:
  - n04_gantt_milestones
role_summary: >
  Produces the project timeline by assigning all tasks to months consistent
  with the dependency map; defines milestone due months and verifiable
  achievement criteria; identifies critical path and scheduling conflicts.
constitutional_scope: "Phase 4"
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier3_project_instantiation/call_binding/selected_call.json
  - docs/tier3_project_instantiation/consortium/roles.json
writes_to:
  - docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
invoked_skills:
  - milestone-consistency-check
  - gate-enforcement
  - decision-log-update
entry_gate: null
exit_gate: phase_04_gate
---

# gantt_designer

## Purpose

Phase 4 node body executor for `n04_gantt_milestones`. Reads the Phase 3 WP structure and dependency map, the project duration from `selected_call.json`, and consortium roles to produce `gantt.json` in Tier 4 and update `milestones_seed.json` in Tier 3.

Requires `phase_03_gate` to have passed before execution begins.

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json`
Schema: `orch.phase4.gantt.v1`

## Additional Output

`docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json` — updated from the produced Gantt schedule.

## Skill Bindings

### `milestone-consistency-check`
**Purpose:** Verify milestone due months against task schedule and deliverable due months; confirm every milestone has a verifiable achievement criterion testable at the stated due month.
**Trigger:** After task-to-month assignments are produced; verifies milestone coherence before gate evaluation.
**Output / side-effect:** Consistency check result written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Milestones with non-verifiable criteria must be flagged.
- Milestone due months must be consistent with task completion months.

### `gate-enforcement`
**Purpose:** Evaluate whether a phase gate condition is met, declare pass or failure, and write gate status to Tier 4.
**Trigger:** After `gantt.json` and `milestones_seed.json` are complete and milestone consistency has been verified; evaluates `phase_04_gate`.
**Output / side-effect:** Gate pass/fail result written to `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/`.
**Constitutional constraints:**
- Gate conditions are defined in the workflow and in CLAUDE.md; they must not be weakened.
- Gate failure must be declared explicitly; fabricated completion is a constitutional violation.
- A gate cannot be declared passed without confirming all gate conditions.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** When scheduling conflicts, critical path decisions, or duration adjustments are resolved during n04 execution.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | WP structure and dependency map for task scheduling |
| `docs/tier3_project_instantiation/call_binding/selected_call.json` | tier3 | manually_placed | — | Project duration constraint |
| `docs/tier3_project_instantiation/consortium/roles.json` | tier3 | manually_placed | — | Partner roles for task assignment |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | tier4_phase_output | run_produced | `orch.phase4.gantt.v1` | Phase 4 canonical gate artifact; run_id required |
| `docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json` | tier3_updated | manually_placed | — | Milestone definitions updated from Gantt schedule |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not assign tasks to months beyond the project duration.
- Must not schedule a task start before prerequisite task completion.
- Must not produce milestones without verifiable achievement criteria.
- Must not silently adjust project duration to accommodate an oversized WP structure.
- Must not operate before `phase_03_gate` has passed.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`phase_03_gate` must have passed. Verify before any action is taken.

---

## Output Schema Contracts

### 1. `gantt.json` — Primary Canonical Output

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json`
**Schema ID:** `orch.phase4.gantt.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.phase4.gantt.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after `phase_04_gate` evaluation |
| `tasks` | array | **yes** | Every `task_id` from `wp_structure.json` `work_packages[].tasks[]` must appear; each entry: `task_id` (join key — must match wp_structure), `wp_id` (parent WP), `start_month` (1-based integer ≥ 1), `end_month` (1-based integer ≤ `start_month`), `responsible_partner` (from Tier 3 `partners.json`) |
| `tasks[].end_month` | integer | **yes** | Must be ≤ project_duration_months from `selected_call.json`; `timeline_within_duration` predicate verifies this |
| `milestones` | array | **yes** | Every milestone must have: `milestone_id` (unique, e.g., "MS1"), `title`, `due_month` (non-null 1-based integer), `verifiable_criterion` (non-empty, concrete, externally verifiable string — not a placeholder), `responsible_wp` (wp_id from wp_structure) |
| `critical_path` | array | **yes** | Non-empty ordered list of `task_id` and `milestone_id` strings forming the critical path; `critical_path_present` verifies non-empty |

### 2. `milestones_seed.json` — Tier 3 Updated Output (no schema_id in spec)

**Canonical path:** `docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json`
**Provenance:** tier3_updated (no schema_id_value defined in spec)

Required content: Updated from the Gantt `milestones` array. Each milestone from `gantt.json` must have a corresponding entry with at least: `milestone_id`, `title`, `due_month`, `verifiable_criterion`. Gate condition `g05_p07` verifies this file is populated.

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements

**Predecessor:** `phase_03_gate` — must have passed. Source: edge `e03_to_04`. Verify via `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json`.

If `phase_03_gate` has not passed, halt immediately. Write `decision_type: constitutional_halt`.

**Entry gate:** none.

### Exit Gate

**Exit gate:** `phase_04_gate` — evaluated after this agent writes all canonical outputs.

Gate conditions (source: `manifest.compile.yaml`, `quality_gates.yaml`):
1. `phase_03_gate` predecessor passed (`g05_p01`)
2. Gantt structure written to Tier 4 (`g05_p02`, `g05_p02b`)
3. All tasks assigned to months within project duration (`g05_p03`, `g05_p04`)
4. All milestones have verifiable criteria and due months (`g05_p05`)
5. Critical path identified and consistent with dependency map (`g05_p06`)
6. `milestones_seed.json` populated in Tier 3 (`g05_p07`)

Gate result: `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gate_result.json`. Blocking edge on pass: `e04_to_06` (`n06_implementation_architecture`).

### Failure Protocol

#### Case 1: Gate condition not met (`phase_04_gate` fails)
- **Halt:** Do not proceed.
- **Write:** `gantt.json` with the schedule as produced; document which conditions failed (e.g., tasks beyond project duration, milestones without verifiable criteria).
- **Decision log:** `decision_type: gate_failure`; list failed conditions.
- **Must not:** Silently adjust project duration to make tasks fit (CLAUDE.md §13 — Tier 3 call binding governs duration). Must not write placeholder milestone criteria.

#### Case 2: Required input absent
- **Halt:** If `wp_structure.json` is absent or `selected_call.json` project duration is absent, halt.
- **Write:** Decision log `decision_type: gate_failure`.

#### Case 3: Mandatory predecessor gate not passed
- **Halt immediately** if `phase_03_gate` is not passed.
- **Write:** `decision_type: constitutional_halt`.

#### Case 4: WP structure has dependency cycle (inherited from Phase 3)
- **Halt:** Do not schedule tasks on a cyclic dependency graph.
- **Write:** `decision_type: gate_failure` — note the Phase 3 artifact has an unresolved cycle that blocks scheduling.
- **Must not:** Proceed with scheduling by ignoring declared dependency cycles.

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: gantt_designer`, `phase_id: phase_04_gantt_and_milestones`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Task scheduling decision (start/end month assignment) | `material_decision` | Task ID; month assignment; dependency basis |
| Schedule conflict resolved by prioritizing one dependency | `assumption` | Conflict; resolution; alternative considered |
| Critical path identified | `material_decision` | Path node list; derivation from dependency map |
| Scheduling conflict that cannot be resolved within project duration | `scope_conflict` | Conflicting tasks; why unresolvable; what is needed |
| `phase_04_gate` passes | `gate_pass` | Gate ID; all conditions confirmed; run_id |
| `phase_04_gate` fails | `gate_failure` | Gate ID; failed conditions |
| `phase_03_gate` predecessor not passed | `constitutional_halt` | Edge `e03_to_04`; status |

---

## Constitutional Review

### 1. Scope compliance

`reads_from` and `writes_to` in the front matter exactly match `agent_catalog.yaml`. Within the `writes_to` targets, the concrete canonical artifacts are: `docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json` (Tier 3 update) and `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` (primary canonical output). No undeclared path access is implied. This agent does not write to any Tier 5 deliverable path.

### 2. Manifest authority compliance

Node binding is `n04_gantt_milestones`. Exit gate is `phase_04_gate` — matches manifest. The `gate-enforcement` skill is in the manifest skill list for `n04_gantt_milestones` and is legitimately used. Runner stamps `gate_result.json` and `artifact_status`. Agent does not self-declare gate pass.

### 3. Forbidden-action review against CLAUDE.md §13

- **§13.3 — Fabricated project facts (duration, partner roles):** Must_not list prohibits assigning tasks to months beyond project duration and scheduling tasks before prerequisite completion. The output schema field `end_month` must be ≤ `project_duration_months` from `selected_call.json`. Partner data for task assignments must come from Tier 3 `roles.json`. Risk: low.
- **§13.7 — Silent duration manipulation:** Must_not explicitly prohibits "silently adjust project duration to accommodate an oversized WP structure." Failure Protocol Case 1 reinforces: if tasks cannot fit, declare gate failure, do not silently adjust. This directly addresses CLAUDE.md §13.7 for this agent's domain. Risk: low.
- **§13.5 — Durable decisions in memory:** Decision-log write obligations table covers all material scheduling events. Risk: low.
- **§13.2/§13.9 — Generic knowledge:** Must_not "Operate before `phase_03_gate` has passed" prevents acting without source WP structure. Risk: low.
- **Milestone fabrication (§13.3):** Must_not prohibits "produce milestones without verifiable achievement criteria." The output schema field `verifiable_criterion` is required, non-empty, and explicitly not a placeholder. Risk: low.
- **Budget-dependent content / Phase 8:** Phase 4 does not produce Tier 5 content. Not applicable.

### 4. Must-not integrity

All five must_not items from `agent_catalog.yaml` are present verbatim. Step 6–7 additions do not weaken them. The output schema contracts strengthen the "no milestones without verifiable criteria" constraint by requiring the `verifiable_criterion` field to be "non-empty, concrete, externally verifiable string — not a placeholder."

**Universal constraint note:** `artifact_status` must not be written by the agent — confirmed in the Output Schema Contracts field table.

### 5. Conflict status

Constitutional review result: no conflict identified
