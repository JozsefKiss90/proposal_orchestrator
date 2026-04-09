---
skill_id: milestone-consistency-check
purpose_summary: >
  Verify milestone due months against task schedule and deliverable due months,
  confirming every milestone has a verifiable achievement criterion testable at its
  stated due month.
used_by_agents:
  - gantt_designer
  - wp_designer
  - implementation_architect
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
constitutional_constraints:
  - "Milestones with non-verifiable criteria must be flagged"
  - "Milestone due months must be consistent with task completion months"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
