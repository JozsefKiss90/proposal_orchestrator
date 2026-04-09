---
skill_id: topic-scope-check
purpose_summary: >
  Verify that a project concept or proposal section is within the thematic scope
  defined by Tier 2B scope requirements, and flag any out-of-scope claims to the
  decision log.
used_by_agents:
  - call_analyzer
  - concept_refiner
reads_from:
  - docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
  - docs/tier2b_topic_and_call_sources/extracted/call_constraints.json
writes_to:
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Scope boundary is defined by Tier 2B only; must not infer scope from generic programme knowledge"
  - "Out-of-scope flags must be written to decision log"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
