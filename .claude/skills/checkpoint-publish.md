---
skill_id: checkpoint-publish
purpose_summary: >
  Write a formal checkpoint artifact to Tier 4 checkpoints/ confirming that a phase
  or phase group has completed with a known validated state, preserving a reproducible
  snapshot of the state at the checkpoint.
used_by_agents:
  - revision_integrator
  - state_recorder
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier3_project_instantiation/
writes_to:
  - docs/tier4_orchestration_state/checkpoints/
constitutional_constraints:
  - "Validated checkpoints must not be overwritten by subsequent reruns"
  - "A checkpoint must not be published before all gate conditions for the phase are met"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
