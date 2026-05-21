# Phase 4 (Gantt & Milestones) — Readiness Diagnostic and Migration Plan

**Date:** 2026-04-21
**Branch:** phase4_refactor
**Phase 3 Gate Status:** PASS (run ca7cb19a-accb-4e30-9430-9f1a9d3c3f71, 2026-04-20T21:39:17Z)
**Constitutional Authority:** CLAUDE.md §7 (Phase 4), §6 (Execution Model), §17 (Runtime Architecture)

---

## A. Phase 4 Readiness Verdict

### **PARTIALLY READY — 3 BLOCKING issues, 5 HIGH-RISK issues, 4 ADVISORY issues**

Phase 3 gate has passed and the primary artifact (`wp_structure.json`) is structurally well-formed. However, Phase 4 first-run execution will **fail or produce an infeasible schedule** due to three blocking problems:

1. **BLOCKING-01:** WP-level `finish_to_start` dependency edges in the Phase 3 dependency map are **temporally infeasible** with the seed WP timing — they require demonstrator WPs to start after M36 but the seed allocates M12–42 for demonstrators. The gantt_designer will either produce an impossible schedule or violate the dependency constraints.

2. **BLOCKING-02:** The `milestone-consistency-check` skill is invoked at **Step 6** in the gantt_designer prompt spec, **before** `gantt.json` is written at Step 7. The skill will execute in DEGRADED mode (WP-level only), meaning the FULL schedule-level validation never runs during Phase 4 execution.

3. **BLOCKING-03:** The Phase 4 gate predicate set **lacks dependency-consistency verification**. The gate can PASS even if the produced schedule violates the dependency_map constraints. No predicate checks that task start_month/end_month assignments respect the declared edges.

---

## B. Phase 3 Input Validation

### B.1 wp_structure.json — Structural Integrity

| Check | Status | Detail |
|-------|--------|--------|
| File exists and non-empty | PASS | 989 lines, schema_id `orch.phase3.wp_structure.v1` |
| run_id present | PASS | `ca7cb19a-accb-4e30-9430-9f1a9d3c3f71` |
| All 9 WPs defined | PASS | WP1–WP9 with titles, objectives, leads |
| All WPs have tasks | PASS | 27 tasks total (3 per WP), all with task_id, title, responsible_partner |
| All WPs have deliverables | PASS | 21 deliverables total, all with deliverable_id, title, type, due_month, responsible_partner |
| Dependency map present | PASS | 36 nodes, 45 edges |
| Cycle detection | PASS | `cycle_detected: false` |
| Critical path present | PASS | `[WP2, WP5, WP8, WP9]` |
| Partner role matrix present | PASS | 8 partners with lead/contributor assignments |
| Normalization issues documented | PASS | 5 advisory-level notes |

### B.2 wp_structure.json — Content Quality

| Check | Status | Detail |
|-------|--------|--------|
| Tasks have responsible_partner | PASS | All 27 tasks have responsible_partner |
| Tasks have contributing_partners | PARTIAL | 6 tasks have empty contributing_partners (T1-01, T1-02, T1-03, T4-03 — management and single-lead tasks) |
| Deliverables have due_month | PASS | All 21 deliverables have numeric due_month |
| Deliverable due_months ≤ 48 | PASS | Max due_month is 48 (D1-03, D8-02, D9-03) |
| Dependencies include edge types | PASS | Both `finish_to_start` and `data_input` types |
| WP-level dependencies field | **EMPTY** | Each WP object has `"dependencies": []` — all dependency information is in the separate `dependency_map` |

### B.3 Supporting Tier 3 Inputs

| File | Status | Detail |
|------|--------|--------|
| `selected_call.json` | PASS | `max_project_duration_months: 48` — the critical temporal bound |
| `roles.json` | PASS | 8 partners with wp_lead and wp_participant arrays |
| `milestones_seed.json` | PASS | 11 milestones (MS1–MS11) pre-populated with months and verification criteria |
| `objectives.json` | PASS | 8 objectives (OBJ-1 through OBJ-8) with target_months and partner assignments |
| `workpackage_seed.json` | PASS | 9 WPs with start_month/end_month and person_months |
| `topic_mapping.json` | PASS | EO-01 and EO-02 mappings confirmed |

### B.4 Tier 3 Internal Consistency Issues

**ISSUE B.4.1 — roles.json ↔ wp_structure.json participant mismatch (HIGH-RISK)**

roles.json declares broader WP participation than wp_structure.json reflects:

| Partner | roles.json wp_participant | Missing from wp_structure.json |
|---------|--------------------------|-------------------------------|
| ISIA | WP2, WP4 | WP2 (participants: ATU,CERIA,BIIS,BAL), WP4 (participants: CERIA,ATU,BIIS) |
| NIHS | WP2, WP3 | WP2, WP3 (participants: BIIS,ATU,CERIA,BAL) |
| ELI | WP4 | WP4 (participants: CERIA,ATU,BIIS) |
| BAL | WP4 | WP4 (participants: CERIA,ATU,BIIS) |

This is a **Tier 3 internal contradiction**. The wp_structure.json was derived from workpackage_seed.json (which has the narrower set), while roles.json reflects the intended broader participation. The gantt_designer reads both and may encounter assignment conflicts when allocating partners to tasks.

**Impact on Phase 4:** If the gantt_designer assigns a task to a partner who appears in roles.json but NOT in wp_structure.json for that WP, the resulting gantt.json will have an inconsistent partner assignment. The phase_04_gate does not currently verify partner-WP consistency.

---

## C. Systemic Risk Assessment

### C.1 Artifact–Gate Contract Completeness

**Status: PARTIALLY COMPLETE — missing dependency-schedule consistency check**

Phase 3 outputs explicitly encode:
- ✅ WP structure (IDs, titles, objectives, leads, partners)
- ✅ Task definitions (IDs, titles, responsible partners)
- ✅ Deliverable definitions (IDs, titles, types, due months)
- ✅ Dependency map (nodes, edges with types)
- ✅ Cycle detection result
- ✅ Critical path

Phase 3 outputs do NOT encode:
- ❌ Task durations or effort estimates (Phase 4 must derive these)
- ❌ Task-level temporal constraints (only WP-level start/end from seed)
- ❌ Explicit statement of which dependency edges are binding scheduling constraints vs. informational

**Rule applied:** If something is not explicitly encoded → it does NOT exist. Task durations do not exist in Phase 3 outputs. The gantt_designer must compute them, but has no authoritative source for task-level effort allocation.

### C.2 Absence vs. Negative Ambiguity

**Status: AMBIGUITY DETECTED in 3 areas**

1. **WP-level `dependencies: []`** — Every WP object has an empty dependencies array, but the dependency_map has 19 WP-level edges. The empty array could be interpreted as "no dependencies" (contradicting the map) or "dependencies are in the map, not here" (requiring the agent to know to look elsewhere). **AMBIGUITY → FAIL RISK.**

2. **`project_duration_months: null`** in section_schema_registry.json — The schema says duration is null for RIA. The actual duration (48 months) is in selected_call.json. Predicate `g05_p04` (timeline_within_duration) must resolve this from selected_call.json, not the schema. **If the predicate reads from the wrong source → FAIL.**

3. **`finish_to_start` vs. `data_input` edge semantics** — The dependency_map uses both types but neither Phase 3 outputs nor the artifact schema specification formally defines whether `finish_to_start` at WP level means "all tasks in source WP must complete before any task in target WP starts" or something weaker. **AMBIGUITY → scheduling infeasibility.**

### C.3 Fail-Closed Semantics Verification

**Status: PARTIALLY SATISFIED**

| Dimension | Explicitly Enumerated | Fail-Closed |
|-----------|----------------------|-------------|
| WP definitions | ✅ 9 WPs | ✅ |
| Task definitions | ✅ 27 tasks | ✅ |
| Deliverable definitions | ✅ 21 deliverables | ✅ |
| Dependency edges | ✅ 45 edges | ✅ |
| Partner assignments | ✅ 8 partners | ✅ |
| Task temporal assignments | ❌ Not in Phase 3 | ⚠️ Relies on Phase 4 agent inference |
| Task durations | ❌ Not in any source | ⚠️ Must be inferred from WP bounds |
| Dependency scheduling semantics | ❌ Not formally defined | ❌ **Inference required** |

The dependency scheduling semantics reliance on inference violates fail-closed principles. The agent must INFER what `finish_to_start` means for scheduling because it is not formally defined at the task level.

### C.4 Source-of-Truth Mapping

| Mapping | Status | Evidence |
|---------|--------|----------|
| objectives → WPs | ✅ EXPLICIT | wp_structure.json WPs have no direct objective links, BUT workpackage_seed.json has `objectives_addressed` arrays per WP |
| WPs → tasks | ✅ EXPLICIT | wp_structure.json nests tasks under WPs |
| tasks → deliverables | ⚠️ IMPLICIT | Tasks and deliverables are siblings under WPs; no explicit task→deliverable mapping exists |
| deliverables → milestones | ⚠️ IMPLICIT | milestones_seed.json has `linked_work_packages` but NOT linked_deliverables or linked_tasks |
| dependency edges → scheduling | ⚠️ AMBIGUOUS | See C.2 point 3 |

**Missing mapping: task → deliverable.** No explicit mapping exists showing which task(s) produce which deliverable(s). Phase 4 needs this to link milestones to both tasks and deliverables for traceability.

### C.5 Structured vs. Narrative Outputs

**Status: PASS — Phase 3 outputs are fully structured JSON**

- wp_structure.json: structured, machine-verifiable
- gate_result.json: structured, machine-verifiable
- milestones_seed.json: structured, machine-verifiable
- objectives.json: structured, machine-verifiable

No narrative-only outputs that Phase 4 depends on.

---

## D. Coverage & Traceability Gaps

### D.1 Objective → WP Coverage

| Objective | Covered by WP(s) | Source |
|-----------|-------------------|--------|
| OBJ-1 | WP2 | workpackage_seed.json `objectives_addressed` |
| OBJ-2 | WP3 | workpackage_seed.json |
| OBJ-3 | WP4 | workpackage_seed.json |
| OBJ-4 | WP5 | workpackage_seed.json |
| OBJ-5 | WP6 | workpackage_seed.json |
| OBJ-6 | WP7 | workpackage_seed.json |
| OBJ-7 | WP8, WP9 | workpackage_seed.json |
| OBJ-8 | WP2, WP3, WP4, WP8 | workpackage_seed.json |

**Status: FULL COVERAGE** — all 8 objectives mapped to at least one WP.

**BUT NOTE:** This mapping is in workpackage_seed.json, NOT in wp_structure.json. The wp_structure.json (Phase 3 output) does NOT carry `objectives_addressed`. The gantt_designer prompt spec says "Read wp_structure.json" — it does NOT say "Read workpackage_seed.json for objective mappings." The objective→WP mapping may be invisible to Phase 4 unless the agent also reads the seed.

### D.2 Deliverable → Task Mapping

**Status: NOT EXPLICIT — gap identified**

wp_structure.json has tasks and deliverables as parallel arrays under each WP. There is no `produced_by_task` or `linked_tasks` field on deliverables. The relationship is inferred from co-location within the same WP.

**Impact on Phase 4:** Milestone definitions require linking to deliverables and/or tasks. Without an explicit deliverable→task mapping, milestones can only be linked at WP granularity, reducing traceability precision.

### D.3 Dependency Graph Completeness

**Status: STRUCTURALLY COMPLETE but SEMANTICALLY PROBLEMATIC**

The dependency_map has:
- 19 WP-level edges (15 `finish_to_start`, 4 `data_input`)
- 26 task-level edges (2 `finish_to_start` — T2-03→T8-02, T3-03→T8-02, T4-03→T8-02; 23 `data_input`)

Wait — let me recount. Actually from the edges:

WP-level finish_to_start: WP2→WP5, WP3→WP5, WP4→WP5, WP2→WP6, WP3→WP6, WP4→WP6, WP2→WP7, WP3→WP7, WP4→WP7, WP2→WP8, WP3→WP8, WP4→WP8, WP5→WP8, WP6→WP8, WP7→WP8, WP8→WP9 = **16 finish_to_start**

WP-level data_input: WP2→WP9, WP3→WP9, WP4→WP9 = **3 data_input**

Task-level finish_to_start: T2-03→T8-02, T3-03→T8-02, T4-03→T8-02 = **3 finish_to_start**

Task-level data_input: remaining 23 edges = **23 data_input**

**All task-level inter-WP edges are `data_input`** (allowing overlap), which is consistent with the overlapping WP timing in the seed. But the WP-level edges are overwhelmingly `finish_to_start` (16 of 19), which **contradicts** the overlapping timing.

---

## E. Temporal / Structural Risk Map

### E.1 CRITICAL — WP-Level finish_to_start Infeasibility

This is the single most important finding in this diagnostic.

**The dependency_map declares 16 WP-level `finish_to_start` edges that are temporally infeasible:**

| Edge | Source WP ends | Target WP starts | Gap | Status |
|------|---------------|-------------------|-----|--------|
| WP2→WP5 | M36 | M12 | -24 | **INFEASIBLE** |
| WP3→WP5 | M30 | M12 | -18 | **INFEASIBLE** |
| WP4→WP5 | M36 | M12 | -24 | **INFEASIBLE** |
| WP2→WP6 | M36 | M12 | -24 | **INFEASIBLE** |
| WP3→WP6 | M30 | M12 | -18 | **INFEASIBLE** |
| WP4→WP6 | M36 | M12 | -24 | **INFEASIBLE** |
| WP2→WP7 | M36 | M12 | -24 | **INFEASIBLE** |
| WP3→WP7 | M30 | M12 | -18 | **INFEASIBLE** |
| WP4→WP7 | M36 | M12 | -24 | **INFEASIBLE** |
| WP2→WP8 | M36 | M6 | -30 | **INFEASIBLE** |
| WP3→WP8 | M30 | M6 | -24 | **INFEASIBLE** |
| WP4→WP8 | M36 | M6 | -30 | **INFEASIBLE** |
| WP5→WP8 | M42 | M6 | -36 | **INFEASIBLE** |
| WP6→WP8 | M42 | M6 | -36 | **INFEASIBLE** |
| WP7→WP8 | M42 | M6 | -36 | **INFEASIBLE** |
| WP8→WP9 | M48 | M1 | -47 | **INFEASIBLE** |

**ALL 16 `finish_to_start` WP-level edges are temporally infeasible** given the WP start/end months in workpackage_seed.json.

**Root cause:** Phase 3 synthesized the dependency_map with `finish_to_start` semantics at the WP level to represent logical dependencies (demonstrators depend on research outputs). But in Horizon Europe proposals, research and demonstration WPs routinely overlap — demonstrators start with use case definition while core research is still running, then integrate results as they mature.

**The correct edge type for these WP-level edges should be `data_input`** (allowing temporal overlap), not `finish_to_start` (requiring sequential completion).

### E.2 Task-Level Dependency Consistency

At the **task level**, the dependency_map correctly uses `data_input` for cross-WP edges (e.g., T2-02→T5-02), allowing temporal overlap. Only 3 task-level edges are `finish_to_start` (T2-03→T8-02, T3-03→T8-02, T4-03→T8-02), representing the genuine requirement that integration (WP8 T8-02) can only proceed after the final research outputs from each pillar.

These 3 task-level finish_to_start edges ARE feasible:
- T2-03 (WP2, ends ≤ M36) → T8-02 (WP8, can start M36+) → WP8 runs M6–48, so T8-02 starting at M36 within bounds ✅
- T3-03 (WP3, ends ≤ M30) → T8-02 → starts at M30 or later ✅
- T4-03 (WP4, ends ≤ M36) → T8-02 → starts at M36 or later ✅

**Conclusion:** The task-level edges are well-constructed. The problem is exclusively at the WP level.

### E.3 Dependency Graph — Cycle Analysis

**Status: NO CYCLES** — Phase 3 already confirmed `cycle_detected: false`. The graph is a DAG at both WP and task levels.

### E.4 Temporal Feasibility — Duration Bounds

| Constraint | Value | Source | Verified |
|-----------|-------|--------|----------|
| Project duration | 48 months | selected_call.json | ✅ |
| WP1 | M1–48 | workpackage_seed.json | ✅ within 48 |
| WP2 | M1–36 | workpackage_seed.json | ✅ |
| WP3 | M1–30 | workpackage_seed.json | ✅ |
| WP4 | M3–36 | workpackage_seed.json | ✅ |
| WP5 | M12–42 | workpackage_seed.json | ✅ |
| WP6 | M12–42 | workpackage_seed.json | ✅ |
| WP7 | M12–42 | workpackage_seed.json | ✅ |
| WP8 | M6–48 | workpackage_seed.json | ✅ |
| WP9 | M1–48 | workpackage_seed.json | ✅ |

All WP bounds fit within the 48-month project duration. No WP exceeds the temporal envelope.

### E.5 Milestone Temporal Consistency

All 11 milestones from milestones_seed.json have due months within the project duration and within their linked WP durations:

| Milestone | Month | Linked WPs | Within WP bounds | Within 48 months |
|-----------|-------|------------|------------------|------------------|
| MS1 | 3 | WP1,2,3,4,8 | ✅ | ✅ |
| MS2 | 12 | WP2 | ✅ (M1–36) | ✅ |
| MS3 | 12 | WP3 | ✅ (M1–30) | ✅ |
| MS4 | 15 | WP4 | ✅ (M3–36) | ✅ |
| MS5 | 12 | WP5,6,7 | ✅ (all start M12) | ✅ |
| MS6 | 24 | WP2,3,4,8 | ✅ | ✅ |
| MS7 | 30 | WP5,6,7 | ✅ | ✅ |
| MS8 | 36 | WP2,3,4 | ✅ | ✅ |
| MS9 | 42 | WP5,6,7,8 | ✅ | ✅ |
| MS10 | 45 | WP8,9 | ✅ | ✅ |
| MS11 | 48 | WP1,9 | ✅ | ✅ |

**Status: ALL MILESTONES TEMPORALLY CONSISTENT** with WP bounds and project duration.

### E.6 Traceability Gap — Milestones ↔ Deliverables

milestones_seed.json links milestones to WPs (`linked_work_packages`) but NOT to specific deliverables or tasks. Phase 4 must produce milestones linked to deliverables/tasks in the gantt.json artifact, but the schema only requires `responsible_wp` (a single WP), not `linked_deliverables` or `linked_tasks`.

**This means milestone→deliverable traceability is NOT enforced at the artifact level.**

---

## F. Phase 4 Gate Failure Prediction

### F.1 Gate Predicate Analysis

| Predicate | Type | Prediction | Risk |
|-----------|------|------------|------|
| g05_p01 | gate_pass | **PASS** | Phase 3 gate already passed |
| g05_p02 | file: gantt.json non-empty | **PASS** (if agent writes file) | Low — standard file-write |
| g05_p02b | file: gantt.json owned by run | **PASS** (if run_id correct) | Low |
| g05_p03 | coverage: all_tasks_have_months | **HIGH RISK** | See F.2 |
| g05_p04 | timeline: timeline_within_duration | **HIGH RISK** | See F.3 |
| g05_p05 | timeline: all_milestones_have_criteria | **PASS** (if agent copies from seed) | Medium — agent must produce non-placeholder criteria |
| g05_p06 | timeline: critical_path_present | **PASS** (if agent computes path) | Low |
| g05_p07 | file: milestones_seed.json populated | **PASS** (already populated) | Low — already non-empty |

### F.2 Risk: g05_p03 — all_tasks_have_months

The predicate checks that ALL tasks in gantt.json have `start_month` and `end_month`. The gantt_designer must assign months to all 27 tasks.

**Failure scenario:** If the gantt_designer encounters the infeasible WP-level `finish_to_start` edges and cannot resolve the contradiction, it may:
- Fail to assign months to demonstrator tasks (→ g05_p03 FAIL)
- Or silently ignore the WP-level edges and only use task-level edges (→ g05_p03 PASS but dependency contract violated)

**Predicted outcome:** If the agent is constitutionally rigorous, it will halt upon encountering the infeasible dependencies. If it uses heuristic scheduling, it may produce a schedule that passes the gate but violates the stated dependencies.

### F.3 Risk: g05_p04 — timeline_within_duration

This predicate checks all task end_months ≤ project_duration_months.

**Key question:** Where does `project_duration_months` come from?
- section_schema_registry.json: `project_duration_months: null` ← WRONG SOURCE
- selected_call.json: `max_project_duration_months: 48` ← CORRECT SOURCE
- workpackage_seed.json: max end_month = 48 (implicit) ← INFERRED

If the predicate resolves duration from the wrong source, it may:
- Treat null as "no constraint" → passes everything (unsound)
- Treat null as "unknown" → fails (overly strict)

**This needs to be verified in the predicate implementation.** The predicate function `timeline_within_duration` must be confirmed to read from `selected_call.json`.

### F.4 Predicted First-Run Outcome

**Most likely outcome:** `blocked_at_exit` with `failure_origin="agent_body"`

**Reasoning:** The gantt_designer prompt spec instructs the agent to "assign tasks to months respecting dependency map" and "ensure task start not before prerequisite completion." When the agent encounters the 16 infeasible WP-level `finish_to_start` edges, it will be unable to construct a valid schedule. Per the failure protocol, it should halt with a gate_failure declaration.

**If the agent somehow produces a schedule** (e.g., by ignoring WP-level edges or treating them as `data_input`):
- Node state: `blocked_at_exit` or `released` depending on whether g05_p03 and g05_p04 pass
- But the schedule would violate the stated dependency map — a constitutional issue even if the gate passes

### F.5 Missing Predicates That Would Catch Real Failures

| Missing Predicate | What It Would Check | Risk of Omission |
|-------------------|---------------------|------------------|
| `dependency_consistency` | Task start/end months respect dependency_map edges | Schedule can violate dependencies and still pass gate |
| `milestone_traceability` | Each milestone linked to at least one deliverable/task | Milestones can be orphaned from work structure |
| `task_duration_non_zero` | Every task has end_month > start_month | Zero-duration tasks could pass all existing predicates |
| `partner_wp_consistency` | Task responsible_partner is a participant in the task's WP | Partner assignments can be inconsistent with WP membership |

---

## G. Backend Migration Gaps (Phase 4)

### G.1 TAPM Suitability Assessment

**Phase 4 input size:**
| Input | Approx. Size |
|-------|-------------|
| wp_structure.json | ~30 KB |
| selected_call.json | ~1 KB |
| roles.json | ~3 KB |
| milestones_seed.json | ~3 KB |
| objectives.json | ~3 KB |
| workpackage_seed.json | ~3 KB |
| **Total** | **~43 KB** |

**Assessment:** Phase 4 falls in the **moderate** input range. The inputs are already pre-sliced (no grouped JSON requiring a call slicer). TAPM would provide modest benefit (~30-40% prompt reduction) by letting Claude read inputs on demand rather than serializing all upfront.

**Recommendation:** Phase 4 is a **secondary TAPM migration candidate** — lower priority than Phase 1 (which has 150-800KB inputs) but higher than lightweight phases. It should be migrated after Phase 1 TAPM is proven.

### G.2 Input Bounding — "Milestone Slicer" Not Needed

Unlike Phase 1 (which needs the Call Slicer to extract a single topic from grouped work programme JSONs), Phase 4 inputs are already topic-specific and project-specific. No Step 0 preprocessing slicer is needed.

However, a **dependency graph pre-processor** (deterministic Python, no Claude) could be beneficial:
- Topologically sort the dependency_map
- Resolve WP-level edges to task-level constraints
- Compute earliest-start / latest-finish windows per task
- Output a `scheduling_constraints.json` intermediate artifact

This would reduce the reasoning burden on Claude and make the scheduling deterministic where possible.

### G.3 Intermediate Artifact Requirements

The current artifact schema defines ONE Phase 4 output: `gantt.json` (schema `orch.phase4.gantt.v1`).

**Recommended intermediate artifacts for debuggability and TAPM readiness:**

| Artifact | Purpose | Schema ID (proposed) |
|----------|---------|---------------------|
| `scheduling_constraints.json` | Resolved temporal constraints per task from dependency map | `orch.phase4.scheduling_constraints.v1` |
| `timeline_validation_report.json` | Pre-gate schedule validation results | `orch.phase4.timeline_validation.v1` |

These are NOT strictly required for the current architecture but would:
- Improve auditability of scheduling decisions
- Provide intermediate checkpoints for debugging
- Enable future decomposition of Phase 4 into multiple skills

### G.4 Missing Predicate Functions

The following predicate functions would need to be implemented for the recommended gate improvements (Section F.5):

| Predicate Function | Type | Implementation Notes |
|-------------------|------|---------------------|
| `dependency_schedule_consistency` | timeline | For each edge in dependency_map: if `finish_to_start`, verify source task end_month ≤ target task start_month. If `data_input`, no strict temporal constraint. |
| `milestone_deliverable_traceability` | coverage | For each milestone, verify at least one linked deliverable or task exists in wp_structure.json |
| `task_duration_positive` | timeline | For each task, verify end_month > start_month (or end_month ≥ start_month if single-month tasks are allowed) |
| `partner_wp_membership` | coverage | For each task, verify responsible_partner is lead or contributor in the parent WP per wp_structure.json |

---

## H. Required Fixes (BLOCKING)

### FIX-01 [BLOCKING] — Reclassify WP-level dependency edges

**Problem:** 16 WP-level `finish_to_start` edges in wp_structure.json dependency_map are temporally infeasible.

**Fix:** Reclassify the 16 infeasible WP-level edges from `finish_to_start` to `data_input`. This correctly represents the Horizon Europe project execution model where demonstrators overlap with research activities.

**Files to modify:**
- `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — change `edge_type` from `"finish_to_start"` to `"data_input"` for the 16 edges listed in Section E.1

**Retain as `finish_to_start`:**
- WP8→WP9 may remain `finish_to_start` IF the intent is that WP9 final outputs depend on WP8 completion. However, WP9 starts at M1 (dissemination runs the whole project), so this should ALSO be `data_input`. **Reclassify all 16 + this 1 = all WP-level finish_to_start edges.**

**Keep `finish_to_start` only at task level:** T2-03→T8-02, T3-03→T8-02, T4-03→T8-02 (genuine sequential dependencies for integration task).

**Constitutional note:** This is a Tier 4 correction of a Phase 3 artifact. Per CLAUDE.md §9.4, the decision must be recorded in the decision log with reasoning.

**Decision log entry required:**
```json
{
  "decision_id": "phase4-diag-fix01",
  "timestamp": "<current>",
  "phase": "phase_4_readiness_diagnostic",
  "decision": "Reclassify 16 WP-level finish_to_start edges to data_input in wp_structure.json dependency_map",
  "reason": "All 16 edges are temporally infeasible: source WPs end at M30-48 while target WPs start at M1-12. finish_to_start semantics require sequential completion, but Horizon Europe RIA projects require research and demonstrator WPs to overlap. Task-level data_input edges correctly capture the actual dependencies. WP-level edges should reflect the same semantics.",
  "tier_source": "workpackage_seed.json (WP timing), wp_structure.json (dependency_map), selected_call.json (48-month duration)",
  "status": "PROPOSED",
  "impact": "Enables Phase 4 gantt_designer to construct a feasible schedule within 48 months"
}
```

### FIX-02 [BLOCKING] — Reorder milestone-consistency-check invocation in prompt spec

**Problem:** The gantt_designer prompt spec invokes `milestone-consistency-check` at Step 6 BEFORE writing `gantt.json` at Step 7. The skill therefore runs in DEGRADED mode (WP-level only) and the FULL schedule-level validation never executes during Phase 4.

**Fix:** Reorder the prompt spec execution sequence:

**Current order:** Steps 3-5 → Step 6 (invoke skill) → Step 7 (write gantt.json) → Step 8-9
**Corrected order:** Steps 3-5 → Step 7 (write gantt.json) → Step 6 (invoke skill in FULL mode) → Step 8-9

**Files to modify:**
- `.claude/agents/prompts/gantt_designer_prompt_spec.md` — swap Steps 6 and 7

**Alternative fix:** Invoke the skill TWICE — once at Step 6 in DEGRADED mode for early validation, and again after Step 7 in FULL mode for schedule-level validation. This is more thorough but adds a Claude invocation.

### FIX-03 [BLOCKING] — Add dependency_schedule_consistency predicate to phase_04_gate

**Problem:** The gate can pass even if the produced schedule violates dependency_map constraints. No predicate verifies that task start/end months respect the declared edges.

**Fix:** Add a new predicate `g05_p08` to phase_04_gate:

```yaml
- predicate_id: g05_p08
  predicate_type: timeline
  predicate_function: dependency_schedule_consistency
  description: >
    For each finish_to_start edge in wp_structure.json dependency_map:
    verify that source node's max task end_month ≤ target node's min task start_month
    in gantt.json. For data_input edges: no strict temporal ordering required.
  artifact_inputs:
    - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json
    - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json
```

**Files to modify:**
- `.claude/workflows/system_orchestration/gate_rules_library.yaml` — add g05_p08 under phase_04_gate
- `runner/` — implement `dependency_schedule_consistency` predicate function

---

## I. Optional Improvements

### IMP-01 — Add milestone_traceability predicate

Add a predicate verifying each milestone in gantt.json is linked to at least one deliverable or task. This enforces CLAUDE.md §7 Phase 4 requirement: "milestones linked to deliverables/tasks."

**Priority:** HIGH (should arguably be blocking, but existing milestones_seed.json has `linked_work_packages` which provides WP-level traceability)

### IMP-02 — Add task_duration_positive predicate

Add a predicate verifying every task has `end_month > start_month` (or `≥` if single-month tasks are acceptable). Prevents zero-duration or negative-duration tasks from passing the gate.

**Priority:** MEDIUM

### IMP-03 — Add partner_wp_membership predicate

Add a predicate verifying each task's `responsible_partner` is a declared participant (lead or contributor) of the parent WP in wp_structure.json. Catches partner-WP assignment inconsistencies.

**Priority:** MEDIUM (especially given the roles.json ↔ wp_structure.json discrepancies in B.4.1)

### IMP-04 — Reconcile roles.json with wp_structure.json

The participant discrepancies identified in B.4.1 should be resolved before Phase 4 runs. Either:
- Update wp_structure.json to include the broader participation from roles.json
- Or narrow roles.json to match wp_structure.json

This is a Tier 3 data quality issue, not a structural fix.

**Priority:** MEDIUM (doesn't block Phase 4 gate but may cause inconsistent partner assignments)

### IMP-05 — Add `objectives_addressed` to wp_structure.json schema

The objective→WP mapping exists only in workpackage_seed.json, not in the Phase 3 output artifact. Adding it to the wp_structure.json schema would make the mapping available to Phase 4+ without requiring reads from seed files.

**Priority:** LOW (involves Phase 3 artifact schema change)

### IMP-06 — Add explicit task→deliverable mapping to wp_structure.json

Add a `produced_by_tasks` array to each deliverable in wp_structure.json, or a `produces_deliverables` array to each task. This would make the task→deliverable traceability explicit rather than inferred from WP co-location.

**Priority:** LOW (involves Phase 3 artifact schema change)

### IMP-07 — Deterministic dependency graph pre-processor

Implement a deterministic Python function (no Claude) that:
1. Topologically sorts the dependency graph
2. Computes earliest-start / latest-finish windows per task from WP bounds and edge constraints
3. Outputs `scheduling_constraints.json`

This would reduce the Claude reasoning burden and make scheduling decisions more reproducible. Aligns with the TAPM migration strategy's emphasis on deterministic preprocessing (like the Call Slicer).

**Priority:** LOW (optimization, not correctness)

---

## Appendix: Documentation Alignment

### CLAUDE.md

| Section | Issue | Fix |
|---------|-------|-----|
| §7 Phase 4 | States "assign tasks to months" and "milestone events with verifiable achievement criteria" — consistent with gate predicates. No amendment needed. | None |
| §7 Phase 4 gate condition | States "No critical path dependency is unresolved" — but the gate predicate set does NOT verify dependency consistency (see FIX-03). The constitutional gate condition is STRONGER than the implemented predicates. | Either amend the constitution to match implemented predicates OR (preferred) implement the missing predicate to match the constitution. FIX-03 addresses this. |

### README.md

| Section | Issue | Fix |
|---------|-------|-----|
| §6 Phase Sequence | Shows n04 and n05 as parallel after Phase 3 — correct per manifest. No issue. | None |
| §6 Gate Behaviour | "Deterministic predicates verify ... timeline validity, and dependency cycles" — dependency cycle check is in Phase 3 gate, not Phase 4 gate. Phase 4 gate does NOT check cycles. Wording is accurate at a general level but could be more precise. | Optional: add note that dependency cycle checking is Phase 3's responsibility |

### backend_migration_plan.md

| Section | Issue | Fix |
|---------|-------|-----|
| Scope | Plan focuses on Phase 1 (call-requirements-extraction) as the first TAPM target. Phase 4 is not mentioned. | Add Phase 4 as a secondary TAPM migration candidate in the "Progressive Migration" section, noting its ~43KB input size and moderate TAPM suitability. |
| Step 0 — Call Slicer | Correctly scoped to Phase 1. Phase 4 does not need a slicer. | None |
| Deferred candidates | No mention of Phase 4 skill decomposition. | Optional: note that Phase 4 `gantt_designer` could be decomposed into scheduling + milestone + validation skills for finer-grained TAPM execution if Phase 1 TAPM succeeds. |

---

## Summary of Actions by Priority

| # | Action | Type | Priority | Blocks Phase 4 |
|---|--------|------|----------|----------------|
| FIX-01 | Reclassify 16 WP-level finish_to_start edges to data_input | Data fix | **BLOCKING** | YES |
| FIX-02 | Reorder milestone-consistency-check invocation after gantt.json write | Spec fix | **BLOCKING** | YES |
| FIX-03 | Add dependency_schedule_consistency predicate to phase_04_gate | Code + config | **BLOCKING** | YES (gate soundness) |
| IMP-01 | Add milestone_traceability predicate | Code + config | HIGH | No (but reduces gate bypass risk) |
| IMP-02 | Add task_duration_positive predicate | Code + config | MEDIUM | No |
| IMP-03 | Add partner_wp_membership predicate | Code + config | MEDIUM | No |
| IMP-04 | Reconcile roles.json ↔ wp_structure.json | Data fix | MEDIUM | No |
| IMP-05 | Propagate objectives_addressed to wp_structure.json | Schema change | LOW | No |
| IMP-06 | Add task→deliverable explicit mapping | Schema change | LOW | No |
| IMP-07 | Deterministic dependency pre-processor | New module | LOW | No |

---

*This diagnostic was produced by fail-closed analysis of all Phase 3 outputs, Tier 2A/2B/3 inputs, gate rules, manifest definitions, agent/skill specifications, and the backend migration plan. No data was invented. No milestones were constructed. All findings are traceable to specific files and fields in the repository.*
