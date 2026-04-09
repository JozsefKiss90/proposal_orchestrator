---
skill_id: evaluator-criteria-review
purpose_summary: >
  Assess proposal content against the scoring logic of the applicable evaluation
  criterion, identifying weaknesses by severity and producing structured feedback
  aligned to evaluator sub-criteria.
used_by_agents:
  - evaluator_reviewer
  - revision_integrator
reads_from:
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
  - docs/tier5_deliverables/assembled_drafts/
writes_to:
  - docs/tier5_deliverables/review_packets/
constitutional_constraints:
  - "Evaluation must apply the active instrument evaluation criteria only"
  - "Must not evaluate against grant agreement annex requirements"
  - "Weakness severity (critical/major/minor) must be assigned to each finding"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
