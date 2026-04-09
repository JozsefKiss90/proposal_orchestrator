---
skill_id: decision-log-update
purpose_summary: >
  Write a durable decision record to the Tier 4 decision log, capturing the decision
  taken, alternatives considered, the tier authority applied, and the rationale,
  whenever a material interpretation is made or a conflict is resolved.
used_by_agents:
  - concept_refiner
  - wp_designer
  - gantt_designer
  - impact_architect
  - implementation_architect
  - budget_gate_validator
  - revision_integrator
  - state_recorder
  - compliance_validator
  - traceability_auditor
reads_from:
  - "Any phase context requiring durable recording"
writes_to:
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Decisions held only in agent memory do not constitute durable decisions"
  - "Every resolved tier conflict must produce a decision log entry"
  - "Decision log entries must identify the tier authority applied"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
