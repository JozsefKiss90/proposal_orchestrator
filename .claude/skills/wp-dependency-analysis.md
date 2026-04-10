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

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Must flag dependency cycles; must not silently remove them"

**Decision point in execution logic:** Step 2.3 — at the completion of Kahn's topological sort algorithm when cycles are detected.

**Exact failure condition:** (a) The topological sort identifies one or more cycle members (nodes remaining with in-degree > 0 after processing), AND the skill silently removes the cycle edges from `dependency_map.edges` instead of flagging them; OR (b) `cycle_detected` is set to false when cycles are actually present; OR (c) `cycle_flags` array is empty when cycles exist.

**Enforcement mechanism:** When Kahn's algorithm identifies cycle members (Step 2.3): the cycle edges MUST be retained in `dependency_map.edges`; they must NOT be removed. `cycle_detected` must be set to true. `cycle_flags` must contain at least one entry per detected cycle. If the cycle detection result conflicts with a desire to produce a "clean" dependency map: the constitutional constraint governs — cycles are flagged, not removed. Silently removing cycle edges to produce a valid-looking DAG is equivalent to fabricated completion per CLAUDE.md §15 and is a constitutional violation. If the skill detects a cycle and cannot write the correct output (e.g., a write error): return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). But cycles themselves do not cause a SkillResult failure — they are correctly represented in the output.

**Failure output:** If cycle removal is attempted instead of flagging: SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Dependency cycle detected but cycle edges were scheduled for removal; cycles must be flagged, not silently removed per skill constitutional constraints and CLAUDE.md §15").

**Hard failure confirmation:** Yes — cycle removal is a categorical prohibition; flagging is the only permitted response.

**CLAUDE.md §13 cross-reference:** §15 — "The system must prefer explicit gate failure over fabricated completion." Silently removing cycles produces a fabricated valid DAG. §12.4 — "Missing mandatory inputs must trigger a gate failure; they must not be papered over."

---

### Constraint 2: "Critical path must be traceable to the dependency map"

**Decision point in execution logic:** Step 2.4 — at the point `critical_path_nodes` is computed.

**Exact failure condition:** `critical_path_nodes` contains node identifiers that are not present in `dependency_map.nodes`; OR the critical path was computed from a different edge/node set than the one stored in `dependency_map`; OR `critical_path_nodes` contains nodes derived from agent prior knowledge rather than the actual dependency graph.

**Enforcement mechanism:** In Step 2.4, the critical path algorithm must operate exclusively on the node set and edge set constructed in Steps 2.1–2.5. After computing the critical path: the skill must verify that every node identifier in `critical_path_nodes` exists in `dependency_map.nodes`. If any node in `critical_path_nodes` is not in `dependency_map.nodes`: return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="Critical path contains node <node_id> not present in dependency_map.nodes; critical path must be traceable to the dependency map") and halt without writing output. If cycles prevent critical path computation: `critical_path_nodes` must be an empty array (not a guessed path).

**Failure output:** SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION"). Updated `wp_structure.json` not written.

**Hard failure confirmation:** Yes — untraceable critical path is a hard failure; guessing the path is not permitted.

**CLAUDE.md §13 cross-reference:** §10.5 — every material claim (including structural analysis results) must be traceable to its Tier 4 source. §9.5 — orchestration outputs must be reproducible from documented inputs.

---

### Constraint 3: "Must not declare the map complete with undeclared dependencies"

**Decision point in execution logic:** Step 5.3 — at the point the updated `wp_structure.json` is written.

**Exact failure condition:** The skill returns SkillResult(status="success") and writes the updated `wp_structure.json` with `dependency_map` when the invoking agent's context identifies specific cross-WP task dependencies that have NOT been included in `dependency_map.edges`.

**Enforcement mechanism:** Before writing the output, the skill must verify that all cross-WP dependencies provided by the invoking agent context (Step 2.2 Source B) have been added to `dependency_map.edges`. If the invoking agent's context contains a dependency that is not in the edges array: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Cross-WP dependency <from> → <to> provided by invoking agent context was not added to dependency_map.edges; the map must not be declared complete with undeclared dependencies") and halt. Additionally: if at any point the skill is aware of a structural dependency between WP activities (e.g., WP2 inputs are produced by WP1) but that dependency is not represented in the edges array, this must be logged as an Unresolved finding — not silently ignored.

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). No output written.

**Hard failure confirmation:** Yes — declaring the map complete with known undeclared dependencies is equivalent to fabricated completion.

**CLAUDE.md §13 cross-reference:** §15 — "A declared failure is an honest and correct output. A fabricated completion is a constitutional violation." §12.5 — "Review … must check … internal consistency."

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` does not exist → `failure_reason="wp_structure.json not found; work-package-normalization must run before wp-dependency-analysis"`
- Step 1.3: `work_packages` array in `wp_structure.json` is empty → `failure_reason="wp_structure.json work_packages array is empty"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.2: `wp_structure.json` `schema_id` field does not equal "orch.phase3.wp_structure.v1" → `failure_reason="wp_structure.json schema_id does not match expected 'orch.phase3.wp_structure.v1'"`
- Step 1.4: `dependency_map` object is absent in `wp_structure.json` → `failure_reason="wp_structure.json missing dependency_map field"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Skill halts immediately.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
- Constraint 2 (critical path traceable to dependency map): Any node identifier in `critical_path_nodes` is not present in `dependency_map.nodes` → `failure_reason="Critical path contains node <node_id> not present in dependency_map.nodes; critical path must be traceable to the dependency map"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Updated `wp_structure.json` not written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the failure.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 3 (map not declared complete with undeclared dependencies): Any cross-WP dependency provided by the invoking agent context has not been added to `dependency_map.edges` before write → `failure_reason="Cross-WP dependency <from> → <to> provided by invoking agent context was not added to dependency_map.edges; the map must not be declared complete with undeclared dependencies"`
- Write error at Step 5.3: If the write of the updated `wp_structure.json` fails after detecting a cycle (cycle must be flagged, not removed) → `failure_reason="<write error>"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 1 (cycles flagged, not silently removed): Cycle detection identifies cycle members and the skill schedules removal of cycle edges from `dependency_map.edges` rather than flagging them → `failure_reason="Dependency cycle detected but cycle edges were scheduled for removal; cycles must be flagged, not silently removed per skill constitutional constraints and CLAUDE.md §15"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the constitutional halt.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` is `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` only; no exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->
