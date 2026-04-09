---
skill_id: gate-enforcement
purpose_summary: >
  Evaluate whether a phase gate condition is met, declare pass or failure, write
  the gate status to Tier 4, and block downstream phases if the gate has not passed.
used_by_agents:
  - call_analyzer
  - wp_designer
  - gantt_designer
  - impact_architect
  - implementation_architect
  - budget_gate_validator
  - proposal_writer
  - revision_integrator
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier3_project_instantiation/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Gate conditions are defined in this workflow and in CLAUDE.md; they must not be weakened"
  - "Gate failure must be declared explicitly; fabricated completion is a constitutional violation"
  - "A gate cannot be declared passed without confirming all gate conditions"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
