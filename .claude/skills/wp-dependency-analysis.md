---
skill_id: wp-dependency-analysis
purpose_summary: >
  Analyse inter-WP and inter-task dependencies, producing a directed acyclic graph
  representation that identifies the critical path, dependency cycles, and dependencies
  incompatible with project duration.
used_by_agents:
  - dependency_mapper
  - wp_designer
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
constitutional_constraints:
  - "Must flag dependency cycles; must not silently remove them"
  - "Critical path must be traceable to the dependency map"
  - "Must not declare the map complete with undeclared dependencies"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact (read from the phase output directory) | work_packages[].wp_id; work_packages[].tasks[].task_id; work_packages[].dependencies[].depends_on_wp_id, dependency_type; dependency_map.nodes; dependency_map.edges | `orch.phase3.wp_structure.v1` | Provides the initial WP and task structure with declared dependencies; this skill extends the dependency_map with cross-WP task edges and identifies cycles or critical path issues |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — updated in place with completed dependency_map | `orch.phase3.wp_structure.v1` | schema_id, run_id, work_packages (unchanged from input; only dependency_map is extended), dependency_map (object: nodes array expanded to include all task_ids, edges array with all cross-WP task edges added, edge_type for each edge), partner_role_matrix (unchanged) | Yes — must carry the same run_id as the producing phase run | dependency_map.nodes expanded from work_packages[].wp_id and work_packages[].tasks[].task_id; dependency_map.edges derived from work_packages[].dependencies[] entries plus cross-WP task edges identified by the agent; any detected cycle must be flagged in the dependency_map (not silently removed) |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. If dependency cycles are detected, the artifact must carry an explicit cycle_flags array documenting the cycle rather than silently removing the cycle edges. The wp_structure.json is written or updated by both `work-package-normalization` and `wp-dependency-analysis`; the final gated version must satisfy the complete schema.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | Yes — artifact_id: a_t4_phase3 (directory); canonical file within that directory | n03_wp_design (dependency_mapper agent within this node) |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
