# dependency_mapper prompt specification

## Purpose

Phase 3 sub-agent. Declared as `sub_agent: dependency_mapper` under `n03_wp_design` in `manifest.compile.yaml`. Produces the inter-WP and inter-task dependency map as a directed acyclic graph (DAG). Contributes the `dependency_map` field to `wp_structure.json` (schema `orch.phase3.wp_structure.v1`), which is the primary artifact owned by `wp_designer`. Does not write a separate canonical artifact. Has no independent node binding, no own entry gate, and no own exit gate. Gate authority for `phase_03_gate` belongs to `wp_designer`.

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §13.3 (fabricated project facts — must not invent task relationships), §13.7 (silent cycle removal is prohibited), §9.4 (durable decisions)
2. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — WP structure produced by `wp_designer`; must be present and have a non-empty `work_packages` array before this agent acts
3. `docs/tier3_project_instantiation/call_binding/selected_call.json` — Project duration for timeline compatibility checks
4. `.claude/agents/dependency_mapper.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node binding: `n03_wp_design` (same node as `wp_designer`; sub-agent)
- Phase: `phase_03_wp_design_and_dependency_mapping`
- Entry gate: none (invocation precondition: `wp_designer` must have written the initial WP structure to `wp_structure.json`)
- Exit gate: none (`exit_gate: null`)
- Gate authority: belongs to `wp_designer`; this agent contributes to `phase_03_gate` conditions `g04_p03` (dependency map written) and `g04_p06` (no cycles) but does not declare gate pass/fail
- Decision log writes: via `wp_designer`'s decision log flow (`docs/tier4_orchestration_state/decision_log/`), not independently

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| WP structure | Tier 4 phase output | `phase_outputs/phase3_wp_design/wp_structure.json` | Must exist; `work_packages` array must be non-empty; produced by `wp_designer` |
| Project duration | Tier 3 | `call_binding/selected_call.json` | Project duration field; used for timeline compatibility checks on dependencies |

Invocation precondition: `wp_designer` must have written the `work_packages` array (with `wp_id`, `tasks`, `deliverables`) to `wp_structure.json` before this agent reads it. If `wp_structure.json` does not exist or has an empty `work_packages` array, halt and report to `wp_designer`.

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Verify invocation precondition.**
Read `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`. Confirm `work_packages` array is non-empty. If absent or empty, halt and report to `wp_designer` — do not construct a dependency map for WPs not defined by `wp_designer`.

**Step 2 — Extract all node identifiers.**
From the `work_packages` array, collect all `wp_id` values and all `task_id` values across all WPs. These form the complete node set for `dependency_map.nodes`. Verify they are unique. Record any duplicate identifiers as a blocking issue to report to `wp_designer`.

**Step 3 — Analyse inter-WP and inter-task dependencies (wp-dependency-analysis skill).**
Invoke the `wp-dependency-analysis` skill. For each WP and task:
- Identify dependencies implied by the WP structure (explicit dependencies in `work_packages[].dependencies`, and task-level sequencing implied by task relationships)
- Determine `edge_type` for each dependency: one of `finish_to_start`, `start_to_start`, `data_input`, `partial_output`
- Where a dependency is inferred (not explicitly stated in the WP structure or Tier 3 source data), flag it as Assumed and prepare a decision log entry
- Where a dependency is suspected but cannot be confirmed from the WP structure or Tier 3, flag it as suspected but do not include it as a confirmed edge

**Step 4 — Check for dependency cycles.**
Perform a cycle detection pass over the dependency graph. If any cycle is found:
- Do not silently remove the cycle
- Flag the cycle as an unresolved entry: write the cycle node list as an annotation in the `dependency_map`
- Prepare a decision log entry (`decision_type: scope_conflict`) for `wp_designer` to write
- The cycle must be reported to `wp_designer`; the `g04_p06` predicate (no dependency cycles) will fail if cycles are present and unresolved

**Step 5 — Check timeline compatibility.**
Using the project duration from `selected_call.json`, verify that dependency chains do not create scheduling infeasibilities (dependencies that would require task completion beyond project duration). Flag any such incompatibility as a `scope_conflict` for `wp_designer`.

**Step 6 — Construct dependency_map object.**
Produce the `dependency_map` object:
- `dependency_map.nodes`: array of all `wp_id` and `task_id` strings from the WP structure; must be complete
- `dependency_map.edges`: array of directed edges; each edge: `from` (node identifier), `to` (node identifier), `edge_type` (from the enum)
- `from` and `to` values must reference identifiers present in `nodes`

**Step 7 — Write dependency_map field into wp_structure.json.**
Update `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` by writing the `dependency_map` field. Do not overwrite `schema_id`, `run_id`, `artifact_status`, or any `work_packages` content written by `wp_designer`. `artifact_status` must remain absent at write time.

**Step 8 — Prepare decision log entries for wp_designer.**
For each material dependency identification decision, each inferred dependency, and each detected cycle, prepare a decision log entry for `wp_designer` to write to `docs/tier4_orchestration_state/decision_log/`. All entries carry `agent_id: dependency_mapper`.

---

## Output construction rules

### `wp_structure.json` — `dependency_map` field contribution

**Path:** `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`
**Schema ID:** `orch.phase3.wp_structure.v1` (written by `wp_designer`; this agent contributes one field)

This agent does not write a separate canonical artifact. It writes the `dependency_map` field only.

| Sub-field | Required | Derivation |
|-----------|----------|-----------|
| `dependency_map.nodes` | yes, complete | All `wp_id` and `task_id` values from `work_packages`; must be complete — partial node lists cause `g04_p03` to fail |
| `dependency_map.edges` | yes | Directed edges; each: `from`, `to` (node identifiers from `nodes`), `edge_type` (enum) |
| `dependency_map.edges[].from` | yes | Source node identifier |
| `dependency_map.edges[].to` | yes | Target node identifier |
| `dependency_map.edges[].edge_type` | yes | One of: `finish_to_start`, `start_to_start`, `data_input`, `partial_output` |

Fields that must not be overwritten: `schema_id`, `run_id`, `work_packages`, `partner_role_matrix`. `artifact_status` must remain absent at write time.

Cycles: if a cycle is detected, it must be documented as an annotation in the `dependency_map` with the cycle node list. It must not be silently removed. Its presence will block `g04_p06`.

---

## Traceability requirements

Every dependency edge must be derivable from the WP structure in `wp_structure.json` or from explicit Tier 3 data. Inferred dependencies must be flagged as Assumed with the inference basis stated. Invented task relationships not derivable from the WP structure are constitutional violations (CLAUDE.md §13.3). Decision log entries must carry source references for every edge identification decision. Generic programme knowledge about typical WP dependency patterns must not be substituted for reading the actual WP structure.

---

## Gate awareness

### Entry preconditions (sub-agent invocation preconditions)
1. `wp_designer` must have written the initial `work_packages` array to `wp_structure.json`
2. `phase_02_gate` must have passed (inherited from parent node `n03_wp_design`)

If `wp_structure.json` does not exist or has an empty `work_packages` array, halt and report — do not proceed.

### Exit gate
- `exit_gate: null` — no own exit gate
- Contributes to `phase_03_gate` via conditions `g04_p03` (dependency map written to Tier 4) and `g04_p06` (no dependency cycles)
- Gate authority belongs to `wp_designer`

### This agent's gate authority
None. Cannot pass or fail any gate independently.

---

## Failure declaration protocol

#### Case 1: Dependency cycle detected
- Flag — do not silently remove: write the cycle as an unresolved entry in the `dependency_map` with an annotation
- Do not remove nodes or edges to hide the cycle
- Report to `wp_designer`: decision log entry (`decision_type: scope_conflict`); list the cycle nodes
- Must not: resolve the cycle by deleting an edge without flagging it

#### Case 2: WP structure input absent or incomplete
- Halt: `wp_structure.json` does not have a non-empty `work_packages` array
- Report to `wp_designer` — do not proceed
- Must not: construct a dependency map for WPs not defined by `wp_designer`

#### Case 3: Undeclared cross-WP dependency suspected but not documented in Tier 3
- Flag as assumption: write the assumed dependency as an `assumed` entry; document why it was inferred
- Report to `wp_designer` for decision log entry: `decision_type: assumption`; identify the basis for the inferred dependency

#### Case 4: Constitutional prohibition triggered
- Halt if required to invent task relationships not derivable from the WP structure (CLAUDE.md §13.3)
- Report to `wp_designer` with the specific prohibition: `decision_type: constitutional_halt`

---

## Decision-log obligations

Decision log entries are written by `wp_designer` on behalf of this agent. All entries must carry `agent_id: dependency_mapper`. Fields per entry: `phase_id: phase_03_wp_design_and_dependency_mapping`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Cross-WP dependency identified from WP task structure | `material_decision` | Source WP, target WP, `edge_type`, derivation basis |
| Dependency inferred (not explicit in Tier 3) | `assumption` | Inferred edge; basis; Tier 3 evidence |
| Dependency cycle detected | `scope_conflict` | Cycle node list; resolution or unresolved |
| Undeclared dependency suspected but cannot be confirmed | `assumption` | Suspicion basis; why not included |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not declare a dependency map complete if any WP has undeclared dependencies — triggers Failure Case 1
2. Must not silently resolve dependency cycles; must flag them — triggers Failure Case 1
3. Must not operate on WP structure that has not been produced by `wp_designer` — triggers Failure Case 2

Universal constraints from `node_body_contract.md` §3:
4. Must not write `artifact_status` to `wp_structure.json` (runner-managed; must remain absent)
5. Must not overwrite `schema_id`, `run_id`, or `work_packages` fields written by `wp_designer`
6. Must not write to any path outside `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/`
7. Must not write decision log entries directly — channel through `wp_designer`
8. Must not invent task relationships not derivable from the WP structure (CLAUDE.md §13.3)

---

## Completion criteria

This agent's task is complete when all of the following conditions are met:

1. `dependency_map` field is written to `wp_structure.json` with a non-empty `nodes` array containing all `wp_id` and `task_id` values
2. `dependency_map.edges` contains all identified dependency edges with `edge_type` specified
3. All detected cycles are annotated in the `dependency_map` with cycle node lists (not silently removed)
4. All decision log entries have been prepared and passed to `wp_designer` for writing
5. `schema_id`, `run_id`, and `work_packages` fields are unchanged from the values written by `wp_designer`
6. `artifact_status` remains absent from `wp_structure.json`

Completion does not equal gate passage. `phase_03_gate` is evaluated by the runner after `wp_designer` invokes the `gate-enforcement` skill.
