---
skill_id: concept-alignment-check
purpose_summary: >
  Check the alignment between the project concept and the call expected outcomes and
  scope requirements, identifying vocabulary gaps, framing mismatches, and uncovered
  expected outcomes.
used_by_agents:
  - concept_refiner
reads_from:
  - docs/tier3_project_instantiation/project_brief/
  - docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json
  - docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Alignment must be tested against Tier 2B extracted files, not assumed from concept vocabulary"
  - "Uncovered expected outcomes must be flagged, not silently assumed covered"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
