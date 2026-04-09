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
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | impact_architecture.json | `orch.phase5.impact_architecture.v1` | schema_id, run_id, impact_pathways (array: pathway_id, expected_impact_id, project_outputs[deliverable_id], outcomes[outcome_id, description, timeframe], impact_narrative, tier2b_source_ref per pathway), kpis (array: kpi_id, description, baseline, target, measurement_method, traceable_to_deliverable[deliverable_id], due_month per KPI), dissemination_plan (object: activities[activity_type, target_audience, responsible_partner, timing], open_access_policy), exploitation_plan (object: activities[activity_type, expected_result, responsible_partner, timing], ipr_strategy), sustainability_mechanism (object: description, responsible_partners, post_project_timeline) | Yes | impact_pathways: expected_impact_id from expected_impacts.json; project_outputs from wp_structure.json deliverable_ids; outcomes from outcomes.json; impact_narrative from impacts.json + Tier 2B framing; kpis: traceable_to_deliverable from wp_structure.json deliverable_ids; dissemination/exploitation/sustainability from impacts.json and Tier 3 consortium data |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. Every expected_impact_id from Tier 2B expected_impacts.json must appear in at least one pathway or be explicitly flagged as uncovered.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | Yes — artifact_id: a_t4_phase5 (directory); canonical file within that directory | n05_impact_architecture |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
