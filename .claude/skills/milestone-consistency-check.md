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

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].deliverables[].deliverable_id, due_month; work_packages[].tasks[].task_id | `orch.phase3.wp_structure.v1` | Provides deliverable due months and task identifiers to cross-reference against milestone due months and task schedule in Phase 4 |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | gantt.json — canonical Phase 4 artifact | milestones[].milestone_id, due_month, verifiable_criterion, responsible_wp; tasks[].task_id, start_month, end_month | `orch.phase4.gantt.v1` | Primary artifact being validated: milestone due months checked against task end_months; verifiable_criterion checked for non-empty, concrete statement |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/validation_reports/` | Per-invocation validation report file (e.g., `milestone_consistency_<timestamp>.json`) | N/A — validation report (no canonical schema_id in artifact_schema_specification.yaml for individual validation report entries) | report_id; skill_id: "milestone-consistency-check"; invoking_agent; run_id_reference; findings array (milestone_id, due_month, task_completion_month, verifiable_criterion_present boolean, consistency_status: consistent/flagged, flag_reason); summary (total_milestones_checked, passed, flagged); timestamp | No — validation reports are not phase output canonical artifacts | findings derived by comparing gantt.json milestones[].due_month against tasks[].end_month for tasks in the same WP; verifiable_criterion_present derived from non-empty check of gantt.json milestones[].verifiable_criterion |

**Note:** The validation_reports directory is not registered as a discrete artifact in the artifact_registry. Validation report files are durable outputs written there by convention by multiple skills. The invoking agent (gantt_designer, wp_designer, or implementation_architect) determines the report file naming.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/validation_reports/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent: n03_wp_design, n04_gantt_milestones, or n06_implementation_architecture per invoking agent) |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
