---
agent_id: dependency_mapper
phase_id: phase_03_wp_design_and_dependency_mapping
node_ids:
  - n03_wp_design
role_summary: >
  Produces the inter-WP and inter-task dependency map as a directed acyclic
  graph; identifies dependency cycles, critical paths, and dependencies
  incompatible with project duration; operates as a required sub-agent within
  Phase 3 under wp_designer.
constitutional_scope: "Phase 3 sub-task"
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier3_project_instantiation/call_binding/selected_call.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
invoked_skills:
  - wp-dependency-analysis
entry_gate: null
exit_gate: null
---

# dependency_mapper

## Purpose

Phase 3 sub-agent. Declared as `sub_agent: dependency_mapper` under `n03_wp_design` in `manifest.compile.yaml`. Has no independent node binding and no own exit gate; it operates within the Phase 3 execution context under `wp_designer` and its outputs are part of the `wp_structure.json` artifact that `phase_03_gate` evaluates.

Reads WP structure produced by `wp_designer` from the Phase 3 Tier 4 output directory, produces the `dependency_map` field required by `wp_structure.json` (schema: `orch.phase3.wp_structure.v1`).

## Output Destination

Contributes to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — specifically the `dependency_map` object. Does not write a separate canonical artifact; the dependency map is embedded in the WP structure artifact.

## Skill Bindings

### `wp-dependency-analysis`
**Purpose:** Analyse inter-WP and inter-task dependencies; produce a directed acyclic graph; identify critical path, dependency cycles, and incompatible dependencies.
**Trigger:** After `wp_designer` has written the initial WP structure to `phase3_wp_design/`; reads it and produces the `dependency_map` object.
**Output / side-effect:** `dependency_map` field populated in `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`.
**Constitutional constraints:**
- Must flag dependency cycles; must not silently remove them.
- Critical path must be traceable to the dependency map.
- Must not declare the map complete with undeclared dependencies.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | WP structure produced by `wp_designer`; dependency map embedded here |
| `docs/tier3_project_instantiation/call_binding/selected_call.json` | tier3 | manually_placed | — | Project duration for timeline compatibility checks |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | Contributes `dependency_map` field; not a separate artifact |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not declare a dependency map complete if any WP has undeclared dependencies.
- Must not silently resolve dependency cycles; must flag them.
- Must not operate on WP structure that has not been produced by `wp_designer`.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Exit Gate

This sub-agent carries `exit_gate: null` because it does not independently satisfy a gate; the gate that evaluates its output (`phase_03_gate`) is the exit gate of the parent node `n03_wp_design`, evaluated after both `wp_designer` and `dependency_mapper` have completed.

---

## Output Schema Contracts

### `wp_structure.json` — Shared Canonical Output (sub-agent contribution)

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`
**Schema ID:** `orch.phase3.wp_structure.v1`
**Provenance:** run_produced (jointly with `wp_designer`)

This sub-agent does not write a separate canonical artifact. It contributes the `dependency_map` field to `wp_structure.json` produced by `wp_designer`. The field is required by the schema; its absence constitutes an incomplete artifact that will fail `phase_03_gate` condition `g04_p03`.

**`dependency_map` field contract** (from `artifact_schema_specification.yaml` schema `orch.phase3.wp_structure.v1`):

| Sub-field | Type | Required | Derivation |
|-----------|------|----------|-----------|
| `dependency_map.nodes` | array of strings | **yes** | All `wp_id` and `task_id` values present in `work_packages`; must be complete |
| `dependency_map.edges` | array | **yes** | Directed edges (from → to); `from` and `to` must be node identifiers from `nodes`; `edge_type` must be one of: `finish_to_start`, `start_to_start`, `data_input`, `partial_output` |
| `dependency_map.edges[].from` | string | **yes** | Source node identifier (wp_id or task_id) |
| `dependency_map.edges[].to` | string | **yes** | Target node identifier (wp_id or task_id) |
| `dependency_map.edges[].edge_type` | string | **yes** | Enum as above |

The `dependency_map` must represent an acyclic directed graph (DAG). If a cycle is detected, it must be flagged — not silently removed.

`schema_id` and `run_id` are written by `wp_designer` as primary artifact owner. This agent must not overwrite those fields. `artifact_status` must remain absent at write time.

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements (Sub-Agent Invocation Preconditions)

This agent is a sub-agent; it has no independent entry gate. Invocation preconditions:
1. `wp_designer` must have written the initial WP structure (work_packages, tasks, deliverables) to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` before this agent reads it.
2. `phase_02_gate` must have passed (inherited from the parent node `n03_wp_design`).

If `wp_structure.json` does not exist or has an empty `work_packages` array, halt and report to `wp_designer`.

### Exit Gate

No own exit gate. Contributes to `phase_03_gate` via condition `g04_p03` (dependency map written to Tier 4) and `g04_p06` (no dependency cycles). Gate authority belongs to `wp_designer`.

### Failure Protocol

#### Case 1: Dependency cycle detected
- **Flag — do not silently remove:** Write the cycle as an unresolved entry in the dependency map with an annotation; do not remove nodes or edges to hide the cycle.
- **Write:** Decision log entry via `wp_designer`'s decision log path with `decision_type: scope_conflict`; list the cycle nodes.
- **Must not:** Resolve the cycle by deleting an edge without flagging it.

#### Case 2: WP structure input absent or incomplete
- **Halt:** If `wp_structure.json` does not have a non-empty `work_packages` array, halt and report.
- **Must not:** Construct a dependency map for WPs not defined by `wp_designer`.

#### Case 3: Undeclared cross-WP dependency suspected but not documented in Tier 3
- **Flag as assumption:** Write the assumed dependency as an `assumed` entry; document why it was inferred.
- **Decision log:** `decision_type: assumption`; identify the basis for the inferred dependency.

#### Case 4: Constitutional prohibition triggered
- **Halt** if required to invent task relationships not derivable from the WP structure. Write `decision_type: constitutional_halt` via the parent node's decision log.

### Decision-Log Write Obligations

Written via `wp_designer`'s decision log flow (same path). Entry fields: `agent_id: dependency_mapper`, `phase_id: phase_03_wp_design_and_dependency_mapping`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Cross-WP dependency identified from WP task structure | `material_decision` | Source WP, target WP, edge_type, derivation basis |
| Dependency inferred (not explicit in Tier 3) | `assumption` | Inferred edge; basis; Tier 3 evidence |
| Dependency cycle detected | `scope_conflict` | Cycle node list; resolution or unresolved |
| Undeclared dependency suspected but cannot be confirmed | `assumption` | Suspicion basis; why not included |

---

## Constitutional Review

### 1. Scope compliance

`reads_from` and `writes_to` in the front matter exactly match `agent_catalog.yaml`. The only write target is `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` — specifically contributing the `dependency_map` field to `wp_structure.json`. This agent does not write a separate canonical artifact; it modifies a field within the primary artifact jointly owned with `wp_designer`. No undeclared path access is implied. Decision log entries are written via `wp_designer`'s decision log flow — this is consistent with the agent not having `docs/tier4_orchestration_state/decision_log/` in its own `writes_to` list.

### 2. Manifest authority compliance

This sub-agent is listed as `sub_agent: dependency_mapper` under `n03_wp_design` in the manifest. It has `node_ids: [n03_wp_design]` in the front matter (same node as `wp_designer`). It carries `entry_gate: null` and `exit_gate: null`. The body text correctly states gate authority belongs to `wp_designer`. No language implies this agent can independently pass or fail `phase_03_gate`. The sub-agent contributes to `g04_p03` (dependency map written) and `g04_p06` (no cycles), but gate evaluation is performed by the runner over the completed artifact.

**Auxiliary/sub-agent constraint:** The body text explicitly requires invocation only after `wp_designer` has written the initial WP structure. The invocation precondition section states: "Must not operate on WP structure that has not been produced by `wp_designer`." No implicit claim to independent gate authority exists.

### 3. Forbidden-action review against CLAUDE.md §13

- **§13.3 — Fabricated project facts (task relationships):** Must_not includes "Must not declare a dependency map complete if any WP has undeclared dependencies" and "Must not operate on WP structure that has not been produced by `wp_designer`." Failure Protocol Case 4 prohibits inventing task relationships not derivable from the WP structure. Risk: low.
- **§13.7 — Silent cycle removal:** Must_not explicitly states "Must not silently resolve dependency cycles; must flag them." Failure Protocol Case 1 reinforces: cycles must be written as unresolved entries, not removed. Risk: low.
- **§13.5 — Durable decisions in memory:** Decision log entries are written via parent agent's flow, but all trigger events are enumerated. Risk: low.
- **§13.2/§13.9 — Generic knowledge or invented relationships:** Failure Protocol Case 4 halts if required to invent task relationships. Case 3 requires flagging inferred dependencies as assumptions. Risk: low.
- **Budget-dependent content / Phase 8:** Not applicable; this agent operates in Phase 3 only.
- **No Tier 5 outputs:** Not applicable.

### 4. Must-not integrity

All three must_not items from `agent_catalog.yaml` are present verbatim. Step 6–7 additions do not weaken them. The cycle-flagging requirement is explicitly stronger than the catalog constraint (the catalog says "must flag them"; the body specifies that cycles must be written as unresolved entries with annotations, not silently removed).

**Universal constraint note:** `schema_id` and `run_id` are written by `wp_designer` as primary artifact owner; this agent must not overwrite those fields — stated explicitly in the Output Schema Contracts section. `artifact_status` must remain absent at write time — also stated.

### 5. Conflict status

Constitutional review result: no conflict identified
