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

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/` | Phase output directory — gate result files confirming all gates passed for the phase group being checkpointed | gate_result.json files for gate_09_budget_consistency, gate_10_part_b_completeness, gate_11_review_closure, gate_12_constitutional_compliance (for the Phase 8 checkpoint); status[pass] field from each | `orch.gate_result.v1` (per gate result file) | Confirms that all gate conditions for the phase(s) being checkpointed have passed; a checkpoint must not be published until all gate results carry status: "pass" |
| `docs/tier3_project_instantiation/` | Tier 3 project data snapshot | selected_call.json (call_id, topic_id); partners.json (partner_ids); architecture_inputs state | N/A — Tier 3 source directory (semantic scope root) | Provides the Tier 3 state at checkpoint time; included in the checkpoint's state snapshot for reproducibility |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | phase8_checkpoint.json | `orch.checkpoints.phase8_checkpoint.v1` | schema_id, run_id, status[published], published_at (ISO 8601), gate_results_confirmed (array of gate_ids: must include gate_09_budget_consistency, gate_10_part_b_completeness, gate_11_review_closure, gate_12_constitutional_compliance) | Yes | status: set to "published" only when all required gate results carry status: "pass"; published_at: ISO 8601 timestamp at time of checkpoint publication; gate_results_confirmed: list of gate_ids confirmed at checkpoint time, derived from reading gate result files in phase_outputs/ |

**Critical constraint:** A validated checkpoint must not be overwritten by subsequent reruns (CLAUDE.md §5 Tier 4 constraints). If `phase8_checkpoint.json` already exists with status: "published", this skill must refuse to overwrite it and must write a gate failure to the decision log instead.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | Yes — artifact_id: a_t4_checkpoint_phase8 (directory); canonical file within that directory; immutable_after_creation: true | n08d_revision |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
