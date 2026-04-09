---
skill_id: proposal-section-traceability-check
purpose_summary: >
  Verify that every material claim in a proposal section is traceable to a named
  Tier 1–4 source, flagging unattributed assertions and applying
  Confirmed/Inferred/Assumed/Unresolved status to each claim.
used_by_agents:
  - proposal_writer
  - revision_integrator
  - traceability_auditor
reads_from:
  - docs/tier5_deliverables/proposal_sections/
  - docs/tier5_deliverables/assembled_drafts/
  - docs/tier1_normative_framework/extracted/
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier2b_topic_and_call_sources/extracted/
  - docs/tier3_project_instantiation/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
constitutional_constraints:
  - "Unattributed claims must be flagged, not silently accepted as Confirmed"
  - "Confirmed status requires naming the specific source artifact"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
