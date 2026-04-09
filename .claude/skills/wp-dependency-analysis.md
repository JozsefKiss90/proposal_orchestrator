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

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="wp_structure.json not found; work-package-normalization must run before wp-dependency-analysis") and halt.
- Step 1.2: Schema conformance check — read `wp_structure.json`; confirm `schema_id` field equals "orch.phase3.wp_structure.v1". If it does not match: return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="wp_structure.json schema_id does not match expected 'orch.phase3.wp_structure.v1'") and halt.
- Step 1.3: Non-empty check — confirm `work_packages` array in `wp_structure.json` is non-empty. If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="wp_structure.json work_packages array is empty") and halt.
- Step 1.4: Confirm `dependency_map` object exists in `wp_structure.json` with `nodes` and `edges` arrays (may be empty arrays at this stage). If `dependency_map` is absent: return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="wp_structure.json missing dependency_map field") and halt.
- Step 1.5: Check `artifact_status` field: if present and equals "invalid", log this as a note (prior gate failure); continue processing since this skill is re-executing to repair or extend.

### 2. Core Processing Logic

- Step 2.1: Extract the full WP set from `wp_structure.json`: collect all `wp_id` values. Extract all `task_id` values from `work_packages[].tasks[]`. Build a comprehensive **node set** = all wp_ids + all task_ids.
- Step 2.2: Build the **complete edge set** from two sources:
  - Source A (WP-level edges): from `work_packages[].dependencies[]` — for each entry: edge `{ from: depends_on_wp_id, to: current_wp_id, edge_type: dependency_type }`. These edges are already present in `dependency_map.edges`; verify they are there and supplement any that are missing.
  - Source B (cross-WP task edges): examine each task in each WP. For each task that depends on a deliverable from a different WP (identifiable if the task's contributing inputs reference a different WP's deliverable_id), add an edge `{ from: <delivering_task_id or wp_id>, to: <this_task_id>, edge_type: "data_input" }`. If the invoking agent's context identifies specific cross-WP task dependencies not represented in the seed, add those edges.
- Step 2.3: Apply **cycle detection** using Kahn's topological sort algorithm over the directed graph defined by the node set (Step 2.1) and edge set (Step 2.2):
  - Compute in-degree for each node.
  - Enqueue all nodes with in-degree = 0.
  - Process queue: for each dequeued node, decrement in-degree of all successors; enqueue any successor whose in-degree reaches 0.
  - After processing: if any nodes remain with in-degree > 0, they are part of a cycle.
  - If cycles are detected: identify the cycle members (the remaining nodes). For each cycle edge (an edge where both endpoints remain with in-degree > 0), create a `cycle_flags` entry: `{ cycle_id: "CYCLE-<n>", nodes_involved: [...], edges_in_cycle: [{from, to, edge_type}], detected_by: "Kahn topological sort" }`. Do NOT remove cycle edges from the graph. Set `cycle_detected: true` in the output.
  - If no cycles: set `cycle_detected: false`.
- Step 2.4: If no cycles were detected, compute the **critical path** using longest-path algorithm over the DAG:
  - Assign a weight of 1 to each edge (representing one phase of work).
  - For each source node (in-degree = 0 in the original graph), apply dynamic programming: for each node in topological order, compute the longest path to that node.
  - The critical path is the sequence of nodes forming the longest path from any source to any sink. Record as an ordered list of node identifiers (wp_ids and task_ids).
  - If cycles exist, the critical path cannot be computed — set `critical_path` in the output to an empty array and note that cycle resolution is required.
- Step 2.5: Extend `dependency_map.nodes` to include all task_ids identified in Step 2.1 (in addition to wp_ids already present). Extend `dependency_map.edges` to include all edges from Step 2.2 (including any new cross-WP task edges).

### 3. Output Construction

**`wp_structure.json`** (updated in place — all existing fields preserved; only `dependency_map` is extended):
- `schema_id`: preserved as "orch.phase3.wp_structure.v1" (unchanged)
- `run_id`: preserved from the existing file (unchanged)
- `work_packages`: preserved unchanged from input
- `partner_role_matrix`: preserved unchanged from input
- `dependency_map.nodes`: derived from Step 2.5 — expanded array including all wp_ids and task_ids
- `dependency_map.edges`: derived from Step 2.5 — expanded array including all WP-level and cross-WP task-level edges; each edge: `{from, to, edge_type}`
- `cycle_detected`: boolean — derived from Step 2.3 — true if any cycle was found
- `cycle_flags`: array — derived from Step 2.3 — list of `{cycle_id, nodes_involved[], edges_in_cycle[]}` entries; empty array if no cycles
- `critical_path_nodes`: array of node identifiers — derived from Step 2.4 — ordered critical path; empty array if cycles present

### 4. Conformance Stamping

- `schema_id`: preserved as "orch.phase3.wp_structure.v1" (this skill does not change schema_id)
- `run_id`: preserved from input (this skill does not change run_id)
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Read the full contents of `wp_structure.json` into memory.
- Step 5.2: Apply extensions to `dependency_map`, add `cycle_detected`, `cycle_flags`, and `critical_path_nodes` fields.
- Step 5.3: Write the updated object back to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`, preserving all other fields exactly.

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
