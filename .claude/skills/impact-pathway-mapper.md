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

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
