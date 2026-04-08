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

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not declare a dependency map complete if any WP has undeclared dependencies.
- Must not silently resolve dependency cycles; must flag them.
- Must not operate on WP structure that has not been produced by `wp_designer`.

Universal constraints from `node_body_contract.md` §3 also apply.

## Note on Exit Gate

This sub-agent carries `exit_gate: null` because it does not independently satisfy a gate; the gate that evaluates its output (`phase_03_gate`) is the exit gate of the parent node `n03_wp_design`, evaluated after both `wp_designer` and `dependency_mapper` have completed.
