---
agent_id: wp_designer
phase_id: phase_03_wp_design_and_dependency_mapping
node_ids:
  - n03_wp_design
role_summary: >
  Designs the full work package structure from project objectives and concept,
  aligned with instrument structural constraints; produces WP definitions,
  task structures, deliverables, milestones, and partner assignments, and
  coordinates with dependency_mapper for the dependency map.
constitutional_scope: "Phase 3"
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
  - docs/tier3_project_instantiation/architecture_inputs/objectives.json
  - docs/tier3_project_instantiation/consortium/
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
writes_to:
  - docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
invoked_skills:
  - work-package-normalization
  - wp-dependency-analysis
  - milestone-consistency-check
  - instrument-schema-normalization
  - gate-enforcement
entry_gate: null
exit_gate: phase_03_gate
---

# wp_designer

## Purpose

Phase 3 node body executor for `n03_wp_design`. Reads Tier 3 architecture inputs and Tier 2A section schema to produce a complete WP structure with tasks, deliverables, dependencies, and partner assignments. Coordinates with `dependency_mapper` (declared as `sub_agent` in `manifest.compile.yaml`) to produce the inter-WP dependency map required by `phase_03_gate`.

Requires `phase_02_gate` to have passed before execution begins.

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`
Schema: `orch.phase3.wp_structure.v1`

## Sub-Agent Relationship

`dependency_mapper` is declared as `sub_agent` of `n03_wp_design` in `manifest.compile.yaml`. The dependency map is a required component of `wp_structure.json`. `dependency_mapper` must complete before `phase_03_gate` can be evaluated.

## Skill Bindings

### `work-package-normalization`
**Purpose:** Normalize a work package structure to ensure each WP has all required elements: unique identifier, title, objective, tasks, deliverables, milestones with verifiable criteria, and a responsible lead.
**Trigger:** After reading `workpackage_seed.json` and `objectives.json`; normalises the seeded WP structure against Tier 2A section schema constraints.
**Output / side-effect:** Normalized WP structure written to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/`.
**Constitutional constraints:**
- WP leads must be drawn from Tier 3 consortium data only.
- WP count must not exceed instrument limits from Tier 2A.
- Deliverables must have due months within project duration.

### `wp-dependency-analysis`
**Purpose:** Analyse inter-WP and inter-task dependencies; produce a directed acyclic graph; identify critical path, dependency cycles, and incompatible dependencies.
**Trigger:** After WP normalization completes; invoked in coordination with `dependency_mapper` sub-agent.
**Output / side-effect:** Dependency map embedded in `wp_structure.json` as the `dependency_map` field; populated by `dependency_mapper`.
**Constitutional constraints:**
- Must flag dependency cycles; must not silently remove them.
- Critical path must be traceable to the dependency map.
- Must not declare the map complete with undeclared dependencies.

### `milestone-consistency-check`
**Purpose:** Verify milestone due months against task schedule and deliverable due months; confirm every milestone has a verifiable achievement criterion.
**Trigger:** After WP structure and task schedule are defined; checks milestone coherence within Phase 3 outputs.
**Output / side-effect:** Consistency check result written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Milestones with non-verifiable criteria must be flagged.
- Milestone due months must be consistent with task completion months.

### `instrument-schema-normalization`
**Purpose:** Resolve the active instrument type to its application form section schema.
**Trigger:** When checking WP structure against instrument-specific structural constraints (e.g. maximum WP count, deliverable naming conventions).
**Output / side-effect:** Section schema constraints applied to the WP structure; `section_schema_registry.json` consulted but not modified.
**Constitutional constraints:**
- Must resolve from the actual Tier 2A application form, not from generic memory.
- Must never substitute a Grant Agreement Annex as a section schema source.
- Page limits and section constraints must be read from the template, not assumed.

### `gate-enforcement`
**Purpose:** Evaluate whether a phase gate condition is met, declare pass or failure, and write gate status to Tier 4.
**Trigger:** After all Phase 3 outputs (WP structure, dependency map) have been produced and validated; evaluates `phase_03_gate` conditions.
**Output / side-effect:** Gate pass/fail result written to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/`.
**Constitutional constraints:**
- Gate conditions are defined in the workflow and in CLAUDE.md; they must not be weakened.
- Gate failure must be declared explicitly; fabricated completion is a constitutional violation.
- A gate cannot be declared passed without confirming all gate conditions.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` | tier3 | manually_placed | — | Initial WP seeds to be elaborated and normalized |
| `docs/tier3_project_instantiation/architecture_inputs/objectives.json` | tier3 | manually_placed | — | Project objectives to ground WP design |
| `docs/tier3_project_instantiation/consortium/` | tier3 | manually_placed | — | Partner data for WP lead and task lead assignments |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | tier2a_extracted | manually_placed | — | Instrument structural constraints (WP count limits, deliverable rules) |
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | tier4_phase_output | run_produced | `orch.phase2.concept_refinement_summary.v1` | Refined concept vocabulary and topic mapping |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` | tier3_updated | manually_placed | — | Updated WP seed reflecting finalized WP structure |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | Phase 3 canonical gate artifact including dependency_map; run_id required |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not assign WP leads or task leads to partners not present in Tier 3 consortium data.
- Must not exceed instrument WP count limits from Tier 2A.
- Must not produce WPs without at least one deliverable.
- Must not operate before `phase_02_gate` has passed.
- Must not declare `phase_03_gate` passed without a completed dependency map in Tier 4.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`phase_02_gate` must have passed. Verify before any action is taken.

---

## Output Schema Contracts

### 1. `wp_structure.json` — Primary Canonical Output

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`
**Schema ID:** `orch.phase3.wp_structure.v1`
**Provenance:** run_produced
**Note:** `dependency_mapper` (sub-agent) contributes the `dependency_map` field to this artifact; the artifact is jointly owned but `wp_designer` is the primary writer.

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.phase3.wp_structure.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after `phase_03_gate` evaluation |
| `work_packages` | array | **yes** | Must be non-empty; derived from `workpackage_seed.json` and `objectives.json`; each WP entry requires: `wp_id` (unique string), `title`, `objectives` (non-empty array), `lead_partner` (from Tier 3 consortium), `tasks` (non-empty array), `deliverables` (non-empty array), `dependencies` (array, may be empty) |
| `work_packages[].tasks[].task_id` | string | **yes** | Unique across all WPs; used as join key in `gantt.json` |
| `work_packages[].tasks[].responsible_partner` | string | **yes** | Must match a partner_id in Tier 3 `partners.json` |
| `work_packages[].deliverables[].deliverable_id` | string | **yes** | Unique; used as join key in impact architecture KPI traceability |
| `work_packages[].deliverables[].type` | string | **yes** | Enum: report / dataset / software / other |
| `work_packages[].deliverables[].due_month` | integer | **yes** | 1-based; must be within project duration from `selected_call.json` |
| `work_packages[].deliverables[].responsible_partner` | string | **yes** | From Tier 3 consortium |
| `dependency_map` | object | **yes** | Populated by `dependency_mapper` sub-agent; must not be null or empty; requires: `nodes` (array of wp_id and task_id strings), `edges` (array of directed edges with `from`, `to`, `edge_type` enum: finish_to_start / start_to_start / data_input / partial_output) |
| `partner_role_matrix` | array | **yes** | Non-empty; each entry: `partner_id`, `wps_as_lead` (array), `wps_as_contributor` (array) |

### 2. `workpackage_seed.json` — Tier 3 Updated Output (no schema_id in spec)

**Canonical path:** `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json`
**Provenance:** tier3_updated (listed as `manually_placed` — no schema_id_value defined in spec)

This agent overwrites the input seed with the finalized WP structure after Phase 3 completes. The update must reflect the WP IDs and task IDs written to `wp_structure.json` so that the seed and the canonical artifact remain consistent.

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements

**Predecessor:** `phase_02_gate` — must have passed. Source: edge `e02_to_03` in `manifest.compile.yaml`. Verify via `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/gate_result.json`.

If `phase_02_gate` has not passed, halt immediately. Write `decision_type: constitutional_halt` to the decision log.

**Entry gate:** none.

### Exit Gate

**Exit gate:** `phase_03_gate` — evaluated after both `wp_designer` and `dependency_mapper` complete.

Gate conditions this agent (primary) is responsible for (source: `manifest.compile.yaml`, `quality_gates.yaml`):
1. `phase_02_gate` predecessor passed (`g04_p01`)
2. Full WP structure written to Tier 4 (`g04_p02`, `g04_p02b`)
3. Dependency map written to Tier 4 (`g04_p03`) — requires `dependency_mapper` sub-agent completion
4. All WPs have at least one deliverable and a responsible lead (`g04_p04`)
5. WP count compliant with Tier 2A instrument constraints (`g04_p05`)
6. No dependency cycles in the dependency map (`g04_p06`)
7. All assigned partners present in Tier 3 consortium data (`g04_p07`)

Gate result: `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json`. Blocking edges on pass: `e03_to_04` (`n04`), `e03_to_05` (`n05`), `e03_to_06` (`n06`).

**Sub-agent coordination:** `dependency_mapper` must complete its `dependency_map` field contribution before `gate-enforcement` skill is invoked. `phase_03_gate` cannot pass if `dependency_map` is absent or null.

### Failure Protocol

#### Case 1: Gate condition not met (`phase_03_gate` fails)
- **Halt:** Do not proceed.
- **Write:** `wp_structure.json` with the complete data produced; document which gate conditions failed in `call_analysis_notes`-equivalent field or via gate-enforcement skill output.
- **Decision log:** `decision_type: gate_failure`; list failed conditions (e.g., a WP without a deliverable, WP count over limit, dependency cycle detected).
- **Must not:** Remove a detected dependency cycle to pass the gate. Must not assign a WP lead to a partner not in Tier 3.

#### Case 2: Required input absent
- **Halt:** If `workpackage_seed.json`, `objectives.json`, or `concept_refinement_summary.json` are absent or empty, halt.
- **Write:** Decision log entry with missing path; `decision_type: gate_failure`.
- **Must not:** Design WPs from generic programme knowledge without a populated Tier 3 seed.

#### Case 3: Mandatory predecessor gate not passed
- **Halt immediately** if `phase_02_gate` result is fail or absent.
- **Write:** `decision_type: constitutional_halt`.
- **Must not:** Begin WP design before Phase 2 is validated.

#### Case 4: Constitutional prohibition triggered
- **Halt** if assigning WP leads to partners not in Tier 3 (CLAUDE.md §13.3), or exceeding instrument WP count limits (CLAUDE.md §13.1 indirect — Tier 2A governs structure).
- **Write:** `decision_type: constitutional_halt` with specific prohibition.

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: wp_designer`, `phase_id: phase_03_wp_design_and_dependency_mapping`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| WP structure design decisions (e.g., split/merge of seed WPs) | `material_decision` | WP IDs involved; rationale; Tier 3 and Tier 2A sources |
| Partner assigned to a WP role based on inference from consortium data | `assumption` | Partner ID; inference basis; Tier 3 source |
| WP count conflict with Tier 2A instrument constraints | `scope_conflict` | Instrument limit source; resolution |
| Dependency mapper sub-agent produces a cycle — cycle flagged | `material_decision` | Cycle nodes; resolution or unresolved status |
| `phase_03_gate` passes | `gate_pass` | Gate ID; all conditions confirmed; run_id |
| `phase_03_gate` fails | `gate_failure` | Gate ID; which conditions failed |
| Predecessor `phase_02_gate` not passed | `constitutional_halt` | Edge `e02_to_03`; predecessor gate status |

---

## Constitutional Review

### 1. Scope compliance

`reads_from` and `writes_to` in the front matter exactly match `agent_catalog.yaml`. Within the `writes_to` targets, the concrete canonical artifacts are: `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` (Tier 3 update) and `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` (primary canonical output). The `dependency_map` field within `wp_structure.json` is contributed by `dependency_mapper` sub-agent, but the file path itself is within this agent's declared write scope. No undeclared path access is implied.

### 2. Manifest authority compliance

Node binding is `n03_wp_design`. Exit gate is `phase_03_gate` — matches manifest. `dependency_mapper` is declared as `sub_agent` in the manifest for `n03_wp_design`. This file correctly describes the sub-agent relationship and states that gate authority belongs to `wp_designer` as primary node agent. The `gate-enforcement` skill is in the manifest skill list for `n03_wp_design` and is used by this agent. Runner stamps `gate_result.json` and `artifact_status`; agent does not self-declare gate pass.

The must_not constraint "Must not declare `phase_03_gate` passed without a completed dependency map in Tier 4" is correctly treated as an output completeness requirement, not as a gate-passing authority claim. Gate result is produced by the runner.

### 3. Forbidden-action review against CLAUDE.md §13

- **§13.3 — Fabricated project facts (partner assignments):** The must_not list explicitly prohibits assigning WP leads or task leads to partners not in Tier 3 consortium data. The output schema requires `responsible_partner` values that match Tier 3 `partners.json`. Failure protocol Case 4 cites CLAUDE.md §13.3 for this violation. Risk: low.
- **§13.1 — Grant Agreement Annex as schema source:** The `instrument-schema-normalization` skill constrains WP structural checks to derive from the actual Tier 2A application form, not an annex template. Risk: low.
- **§13.2 — Fabricated call constraints:** This agent does not extract or create call constraints. It reads them as consumed inputs. Risk: not applicable as a producer.
- **§13.3 risk for WP design fabrication:** Failure protocol Case 2 prohibits designing WPs from generic programme knowledge without a populated Tier 3 seed. Risk: low.
- **§13.9 — Generic knowledge substitution:** Must_not includes "Operate before `phase_02_gate` has passed". Risk: low.
- **§13.5 — Durable decisions in memory:** Decision-log write obligations table covers material events. Risk: low.
- **§13.7 — Silent dependency cycle removal:** Must_not does not include an explicit prohibition on silently resolving cycles, but the body text (Failure Protocol Case 1 and the sub-agent coordination section) states that cycles must be flagged, not removed. This is stronger than the must_not list alone. Risk: low.
- **Budget-dependent content / Phase 8:** Phase 3 does not produce Tier 5 content. Not applicable.

### 4. Must-not integrity

All five must_not items from `agent_catalog.yaml` are present verbatim. Step 6–7 additions do not weaken any of them. The output schema contracts strengthen the partner-assignment constraint by making it mechanically verifiable (the `all_partners_in_tier3` predicate joins the WP structure against Tier 3 `partners.json`).

### 5. Conflict status

Constitutional review result: no conflict identified
