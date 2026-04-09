---
skill_id: risk-register-builder
purpose_summary: >
  Populate the risk register from Tier 3 risk seeds, assigning likelihood, impact,
  mitigation, and monitoring for each risk, and flagging any material risks not in the
  seed file for Tier 3 update.
used_by_agents:
  - implementation_architect
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/risks.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
constitutional_constraints:
  - "Risks not in Tier 3 seeds must be flagged for operator review, not silently added"
  - "Mitigation measures must be traceable to project activities, not generic"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
