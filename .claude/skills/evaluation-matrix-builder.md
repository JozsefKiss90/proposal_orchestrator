---
skill_id: evaluation-matrix-builder
purpose_summary: >
  Build a structured evaluation matrix from the applicable evaluation form and call
  priority weights, mapping evaluation criteria, sub-criteria, scoring thresholds,
  and relative weights.
used_by_agents:
  - call_analyzer
  - instrument_schema_resolver
reads_from:
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
constitutional_constraints:
  - "Evaluation criteria must reflect the active evaluation form, not a generic template"
  - "Sub-criterion weights must be traceable to Tier 2B extracted files"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
