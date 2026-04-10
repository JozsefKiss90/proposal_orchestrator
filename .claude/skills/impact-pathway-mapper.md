---
skill_id: impact-pathway-mapper
purpose_summary: >
  Map project outputs to call expected outcomes and expected impacts, producing a
  structured pathway showing output-to-outcome-to-impact chains with source references
  for call-side expectations and project-side mechanisms.
used_by_agents:
  - impact_architect
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/outcomes.json
  - docs/tier3_project_instantiation/architecture_inputs/impacts.json
  - docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json
  - docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
constitutional_constraints:
  - "Every call expected impact must be explicitly mapped or flagged as uncovered"
  - "Impact claims must trace to a named WP deliverable or activity"
  - "Generic impact language must not substitute for project-specific pathways"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` | outcomes.json — Tier 3 architecture input | Project-specific outcome entries: outcome_id, description, linked_wp_ids, timeframe | N/A — Tier 3 source artifact | Provides the project's own stated intermediate outcomes to be positioned on the impact pathway; outcomes must be traceable to WP activities |
| `docs/tier3_project_instantiation/architecture_inputs/impacts.json` | impacts.json — Tier 3 architecture input | Project-specific impact entries: impact_id, description, target_group, mechanism | N/A — Tier 3 source artifact | Provides the project's own stated broader impacts; these are mapped against call expected impacts to produce the pathway |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | expected_outcomes.json — Tier 2B extracted | expected_outcome entries: outcome_id, description, source_section, source_document, status | N/A — Tier 2B extracted artifact | Call-required expected outcomes that must appear as nodes on at least one pathway; uncovered outcomes must be flagged |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | expected_impacts.json — Tier 2B extracted | expected_impact entries: impact_id (join key), description, source_section, source_document, status | N/A — Tier 2B extracted artifact | Call-required expected impacts; every impact_id must be mapped to at least one pathway for the all_impacts_mapped predicate to pass |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].deliverables[].deliverable_id (join key for KPIs); work_packages[].wp_id; work_packages[].tasks[] | `orch.phase3.wp_structure.v1` | Provides deliverable_ids and WP activities that are the project-side mechanism in each pathway; KPIs must reference valid deliverable_ids from this artifact |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | impact_architecture.json | `orch.phase5.impact_architecture.v1` | schema_id, run_id, impact_pathways (array: pathway_id, expected_impact_id, project_outputs[deliverable_id], outcomes[outcome_id, description, timeframe], impact_narrative, tier2b_source_ref per pathway), kpis (array: kpi_id, description, baseline, target, measurement_method, traceable_to_deliverable[deliverable_id], due_month per KPI), dissemination_plan (object: activities[activity_type, target_audience, responsible_partner, timing], open_access_policy), exploitation_plan (object: activities[activity_type, expected_result, responsible_partner, timing], ipr_strategy), sustainability_mechanism (object: description, responsible_partners, post_project_timeline) | Yes | impact_pathways: expected_impact_id from expected_impacts.json; project_outputs from wp_structure.json deliverable_ids; outcomes from outcomes.json; impact_narrative from impacts.json + Tier 2B framing; kpis: traceable_to_deliverable from wp_structure.json deliverable_ids; dissemination/exploitation/sustainability from impacts.json; responsible_partners from impacts.json responsible_partner fields or provided by invoking agent as context |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. Every expected_impact_id from Tier 2B expected_impacts.json must appear in at least one pathway or be explicitly flagged as uncovered.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | Yes — artifact_id: a_t4_phase5 (directory); canonical file within that directory | n05_impact_architecture |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` exists and is non-empty. If absent or empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="expected_impacts.json not found or empty; call-requirements-extraction must run before impact-pathway-mapper") and halt.
- Step 1.2: Presence check — confirm `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` exists and is non-empty. If absent or empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="expected_outcomes.json not found or empty") and halt.
- Step 1.3: Presence check — confirm `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="outcomes.json not found in Tier 3; project outcomes must be provided") and halt.
- Step 1.4: Presence check — confirm `docs/tier3_project_instantiation/architecture_inputs/impacts.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="impacts.json not found in Tier 3; project impacts must be provided") and halt.
- Step 1.5: Presence check and schema check — confirm `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` exists with `schema_id` = "orch.phase3.wp_structure.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="wp_structure.json not found or schema mismatch") and halt.
- Step 1.6: Validated state check — check `wp_structure.json` for `artifact_status` field. If `artifact_status` = "invalid": return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="wp_structure.json has artifact_status: invalid; the artifact was invalidated by a prior gate failure and cannot be used as input until Phase 3 gate passes") and halt.

### 2. Core Processing Logic

- Step 2.1: Extract all `impact_id` values from `expected_impacts.json`. These are the **required coverage set** — every impact_id must appear in at least one pathway or be explicitly flagged as uncovered.
- Step 2.2: Extract all `outcome_id` values from `expected_outcomes.json`. Build a lookup map keyed by outcome_id.
- Step 2.3: Extract all `deliverable_id` values from `wp_structure.json work_packages[].deliverables[]`. Build a lookup map keyed by deliverable_id with `wp_id` for each. These are the **valid deliverable reference set** for KPI traceability.
- Step 2.4: Extract project outcomes from `outcomes.json` (Tier 3). Each entry has `outcome_id`, `description`, `linked_wp_ids`, `timeframe`.
- Step 2.5: Extract project impacts from `impacts.json` (Tier 3). Each entry has `impact_id`, `description`, `target_group`, `mechanism`. Also extract dissemination, exploitation, and sustainability data if present as sub-objects or separate entries.
- Step 2.6: Build the `impact_pathways` array. For each expected_impact entry from `expected_impacts.json` (by `impact_id`):
  - Step 2.6.1: Find matching project impact(s) in `impacts.json` by matching the subject matter or domain of the expected impact description against the project impact descriptions. A match exists when the project impact's `mechanism` or `description` addresses the same outcome area as the expected impact. If no project impact matches: this expected_impact_id is **uncovered** — add it to the uncovered_impacts accumulator for Step 2.11 (NOT added to pathways), then create a pathway entry with `project_outputs: []`, `outcomes: []`, `impact_narrative: "UNCOVERED — no project mechanism identified for this expected impact"`, mark this as requiring resolution. This skill does not write a decision log entry; uncovered impacts are returned in the SkillResult payload and the invoking agent routes them to decision-log-update.
  - Step 2.6.2: For a matched expected impact: find contributing WP deliverables by identifying which WPs have deliverables whose title or type are plausibly contributing to this impact area (based on the matching project impact's `mechanism` and `linked_wp_ids` from related outcomes). The `project_outputs` array must contain only `deliverable_id` values that exist in the valid deliverable reference set (Step 2.3). Do not invent deliverable_ids.
  - Step 2.6.3: Find intermediate outcomes from `outcomes.json` that are on the pathway from the selected deliverables to the expected impact. Match by `linked_wp_ids` overlap with the deliverable's WP.
  - Step 2.6.4: Build pathway entry: `{ pathway_id: "PWY-<n>", expected_impact_id: <from expected_impacts.json>, project_outputs: [deliverable_ids from Step 2.6.2], outcomes: [{outcome_id, description, timeframe}], impact_narrative: <string from project impacts.json description + Tier 2B expected impact framing>, tier2b_source_ref: <source_section + source_document from expected_impacts.json entry> }`.
- Step 2.7: Build the `kpis` array. For each project outcome and project impact that requires measurement:
  - Assign `kpi_id` (unique, e.g., "KPI-01").
  - Derive `description` from the outcome or impact description.
  - Set `target` from any quantitative statements in the project impact data; if none, use a qualitative target statement.
  - Set `measurement_method` from the project impact `mechanism` or outcome `timeframe`.
  - Set `traceable_to_deliverable`: must be a `deliverable_id` from the valid deliverable reference set (Step 2.3) that is the primary deliverable contributing to this KPI. Do not use a deliverable_id that does not exist in wp_structure.json. If no deliverable is identifiable: flag as Unresolved in the KPI entry.
- Step 2.8: Build `dissemination_plan` from `impacts.json` dissemination data (if present). If `impacts.json` does not contain dissemination data, the structure must be provided by the invoking agent as context; this skill does not read `docs/tier3_project_instantiation/project_brief/` (not in reads_from):
  - `activities`: array — each activity must have `activity_type`, `target_audience` (specific group name, not "general public"), `responsible_partner` (from impacts.json responsible_partner fields or provided by invoking agent as context), `timing`.
  - `open_access_policy`: string — non-empty statement about the project's open access approach.
- Step 2.9: Build `exploitation_plan` from `impacts.json` exploitation data:
  - `activities`: array — each activity must have `activity_type`, `expected_result`, `responsible_partner`, `timing`.
  - `ipr_strategy`: string — optional.
- Step 2.10: Build `sustainability_mechanism`:
  - `description`: string — how project outputs will be sustained post-project (from impacts.json sustainability data if present; otherwise must be provided by invoking agent as context).
  - `responsible_partners`: array — partner_id values from impacts.json responsible_partner fields (if populated); if absent, partner_ids must be provided by the invoking agent as context. This skill does not read `docs/tier3_project_instantiation/consortium/partners.json` (not in reads_from).
  - `post_project_timeline`: string — optional.
- Step 2.11: For each uncovered expected_impact_id identified in Step 2.6.1: record it in the `uncovered_impacts` array of the SkillResult payload (format: `{ impact_id, description }` from expected_impacts.json, `resolution_required: true`). Do not write a decision log entry directly — this skill does not write to decision_log/. The invoking agent must invoke decision-log-update with decision_type: "uncovered_expected_impact" for each entry in the SkillResult payload's uncovered_impacts array to produce durable decision log records.

### 3. Output Construction

**`impact_architecture.json`:**
- `schema_id`: set to "orch.phase5.impact_architecture.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `impact_pathways`: derived from Step 2.6 — array of `{pathway_id, expected_impact_id, project_outputs[], outcomes[], impact_narrative, tier2b_source_ref}`
- `kpis`: derived from Step 2.7 — array of `{kpi_id, description, baseline, target, measurement_method, traceable_to_deliverable, due_month}`
- `dissemination_plan`: derived from Step 2.8 — `{activities[], open_access_policy}`
- `exploitation_plan`: derived from Step 2.9 — `{activities[], ipr_strategy}`
- `sustainability_mechanism`: derived from Step 2.10 — `{description, responsible_partners[], post_project_timeline}`

### 4. Conformance Stamping

- `schema_id`: set to "orch.phase5.impact_architecture.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/` if not present.
- Step 5.2: Write `impact_architecture.json` to `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json`.
- Step 5.3: Return the SkillResult payload to the invoking agent. If any uncovered impacts were identified in Step 2.11, they must be included in the SkillResult payload's `uncovered_impacts` array so the invoking agent can invoke decision-log-update. This skill does not write to `docs/tier4_orchestration_state/decision_log/`.

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Every call expected impact must be explicitly mapped or flagged as uncovered"

**Decision point in execution logic:** Step 2.6 — at the point each expected_impact entry from `expected_impacts.json` is processed; and Step 2.11 — at the point the uncovered_impacts list is compiled.

**Exact failure condition:** Any `impact_id` from `expected_impacts.json` has no corresponding entry in the `impact_pathways` array of `impact_architecture.json`. OR: an uncovered impact exists but is not recorded in the SkillResult payload's `uncovered_impacts` array, preventing the invoking agent from writing a durable decision log entry for it.

**Enforcement mechanism:** In Step 2.6.1, the required coverage set (all impact_ids from expected_impacts.json, extracted in Step 2.1) must be checked exhaustively. For every impact_id that could not be matched: a pathway entry must be created with an explicit `impact_narrative: "UNCOVERED — no project mechanism identified for this expected impact"` AND the impact_id must be added to the `uncovered_impacts` array in the SkillResult payload (Step 2.11). At output construction time (Step 5.2), the skill must verify that every impact_id from the required coverage set appears in `impact_pathways` — either as a matched pathway or as an uncovered entry. If any impact_id is absent: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Expected impact <impact_id> from expected_impacts.json is absent from impact_pathways; every call expected impact must be explicitly mapped or flagged as uncovered per skill constitutional constraints and CLAUDE.md §12.4"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). No `impact_architecture.json` written.

**Hard failure confirmation:** Yes — omitting an expected impact from the mapping is a constitutional violation equivalent to fabricated completion.

**CLAUDE.md §13 cross-reference:** §12.4 — "Missing mandatory inputs must trigger a gate failure; they must not be papered over." §7 Phase 5 gate — "Every expected_impact_id from expected_impacts.json appears in at least one pathway."

---

### Constraint 2: "Impact claims must trace to a named WP deliverable or activity"

**Decision point in execution logic:** Step 2.6.2 and Step 2.7 — at the point `project_outputs` deliverable_ids are assigned to pathways, and at the point `traceable_to_deliverable` is set for KPIs.

**Exact failure condition:** (a) A pathway entry has a non-empty `project_outputs` array containing a `deliverable_id` that does not exist in the valid deliverable reference set from `wp_structure.json` (Step 2.3); OR (b) a KPI entry has a `traceable_to_deliverable` value that is not in the valid deliverable reference set; OR (c) a KPI or pathway asserts an impact without naming any deliverable or activity from wp_structure.json.

**Enforcement mechanism:** In Step 2.6.2: every `deliverable_id` written to `project_outputs` must be verified against the valid deliverable reference set before being written. If a deliverable_id does not exist in wp_structure.json: it must NOT be written to `project_outputs` — it must be flagged as Unresolved in the pathway entry. In Step 2.7: before setting `traceable_to_deliverable`, verify the deliverable_id exists in the valid reference set. If it does not exist: set `traceable_to_deliverable` to null with a flag: "No deliverable found to trace this KPI; operator review required". Writing any deliverable_id not in the valid reference set triggers: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="deliverable_id <id> in pathway/KPI does not exist in wp_structure.json; impact claims must trace to a named WP deliverable per skill constitutional constraints and CLAUDE.md §13.3"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No `impact_architecture.json` written.

**Hard failure confirmation:** Yes — fabricated deliverable_ids are a constitutional violation per CLAUDE.md §13.3 (inventing project facts not present in Tier 3/4).

**CLAUDE.md §13 cross-reference:** §13.3 — inventing project facts (including deliverable_ids not present in Tier 3/4). §11.4 — "Tier 5 deliverables are the output layer; they must be derived from Tier 1–4 state."

---

### Constraint 3: "Generic impact language must not substitute for project-specific pathways"

**Decision point in execution logic:** Step 2.6.4 — at the point `impact_narrative` is set for each pathway entry.

**Exact failure condition:** Any pathway's `impact_narrative` contains boilerplate or generic language such as: "the project will have a positive impact on society", "results will benefit stakeholders", "broad societal impact is expected", "the project will contribute to European competitiveness", or any equivalent phrase that does not name the specific project mechanism, target group, or outcome chain for this pathway.

**Enforcement mechanism:** In Step 2.6.4, after constructing each `impact_narrative` string, the skill must apply the following check: the narrative must include at least one of: (a) a reference to a specific project activity, task_id, or deliverable_id from wp_structure.json; OR (b) a named specific target group (not "stakeholders" or "society"); OR (c) a specific metric or quantifiable outcome from impacts.json. If the constructed narrative fails all three criteria: it must not be written as-is. The narrative must be revised to include project-specific content, OR the pathway entry must be flagged as Unresolved with `impact_narrative: "INCOMPLETE — generic narrative replaced; project-specific pathway mechanism required"`. Writing a generic narrative as if it were a project-specific pathway is a constitutional violation. If this condition is detected at write time: return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="Pathway <pathway_id> has a generic impact_narrative that does not trace to project-specific mechanisms; CLAUDE.md §11.1 requires evaluator-oriented, project-specific impact content"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION"). No `impact_architecture.json` written.

**Hard failure confirmation:** Yes — generic impact language as a substitute for project-specific pathways is a constitutional violation per CLAUDE.md §11.1.

**CLAUDE.md §13 cross-reference:** §11.1 — "All deliverables in Tier 5 must be evaluator-oriented. They must address evaluation criteria directly, in the language and frame of reference established by the applicable evaluation form and call-specific expected impacts." §13.3 — generic statements not grounded in Tier 3 data constitute fabricated project-specific claims.

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` is absent or empty → `failure_reason="expected_impacts.json not found or empty; call-requirements-extraction must run before impact-pathway-mapper"`
- Step 1.2: `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` is absent or empty → `failure_reason="expected_outcomes.json not found or empty"`
- Step 1.3: `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` is absent → `failure_reason="outcomes.json not found in Tier 3; project outcomes must be provided"`
- Step 1.4: `docs/tier3_project_instantiation/architecture_inputs/impacts.json` is absent → `failure_reason="impacts.json not found in Tier 3; project impacts must be provided"`
- Step 1.5: `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` is absent or schema mismatch → `failure_reason="wp_structure.json not found or schema mismatch"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.6: `wp_structure.json` has `artifact_status: "invalid"` → `failure_reason="wp_structure.json has artifact_status: invalid; the artifact was invalidated by a prior gate failure and cannot be used as input until Phase 3 gate passes"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Skill halts immediately.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
- Constraint 3 (no generic impact language): Any pathway's `impact_narrative` contains boilerplate language that does not reference a specific project mechanism, named target group, or specific metric from `impacts.json` → `failure_reason="Pathway <pathway_id> has a generic impact_narrative that does not trace to project-specific mechanisms; CLAUDE.md §11.1 requires evaluator-oriented, project-specific impact content"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the failure.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 1 (every call expected impact explicitly mapped or flagged): At output construction time (Step 5.2), any `impact_id` from `expected_impacts.json` is absent from `impact_pathways` — neither as a matched pathway nor as an uncovered entry → `failure_reason="Expected impact <impact_id> from expected_impacts.json is absent from impact_pathways; every call expected impact must be explicitly mapped or flagged as uncovered per skill constitutional constraints and CLAUDE.md §12.4"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 2 (impact claims trace to named WP deliverable): Any `deliverable_id` written to `project_outputs` or `traceable_to_deliverable` does not exist in the valid deliverable reference set from `wp_structure.json` → `failure_reason="deliverable_id <id> in pathway/KPI does not exist in wp_structure.json; impact claims must trace to a named WP deliverable per skill constitutional constraints and CLAUDE.md §13.3"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No `impact_architecture.json` written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the constitutional halt.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` is `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/` only; no exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Validates output construction against artifact_schema_specification.yaml.*

---

### Canonical Artifact: `impact_architecture.json`

**Schema ID verified:** `orch.phase5.impact_architecture.v1` ✓

**Required fields checked:**

| Field | Required | Status | Notes |
|-------|----------|--------|-------|
| schema_id | true | ✓ Implemented | Set to "orch.phase5.impact_architecture.v1" in Step 3 and Step 4 |
| run_id | true | ✓ Implemented | Propagated from invoking agent run_id |
| artifact_status | false | ✓ Absent at write time | Runner-stamped post-gate |
| impact_pathways | true | ✓ Implemented | Built in Step 2.6 with pathway_id, expected_impact_id, project_outputs[], outcomes[outcome_id, description, timeframe], impact_narrative, tier2b_source_ref |
| kpis | true | ✓ Implemented | Built in Step 2.7 with kpi_id, description, target, measurement_method, traceable_to_deliverable per entry |
| dissemination_plan | true | ✓ Implemented | Built in Step 2.8 with activities[activity_type, target_audience, responsible_partner] and open_access_policy |
| exploitation_plan | true | ✓ Implemented | Built in Step 2.9 with activities[activity_type, expected_result, responsible_partner] |
| sustainability_mechanism | true | ✓ Implemented | Built in Step 2.10 with description and responsible_partners[] |

**Reads_from compliance:** All output fields derived from declared reads_from sources (outcomes.json, impacts.json, expected_outcomes.json, expected_impacts.json, wp_structure.json). Where dissemination/sustainability data is not present in impacts.json, the skill explicitly requires the invoking agent to provide it as context — partner_brief and partners.json are not in reads_from and are explicitly excluded.

**Corrections applied:** None. Output Construction lists every required schema field with correct schema_id.

<!-- Step 8 complete: schema validation performed -->
