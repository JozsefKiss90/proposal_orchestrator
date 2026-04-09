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

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
