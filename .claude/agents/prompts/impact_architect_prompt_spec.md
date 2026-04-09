# impact_architect prompt specification

## Purpose

Phase 5 node body executor for `n05_impact_architecture`. Reads Tier 3 architecture inputs (outcomes, impacts) and Tier 2B extracted call expectations to produce the full impact architecture: output-to-outcome-to-impact pathways, KPI definitions, dissemination and exploitation logic, communication strategy, and sustainability mechanisms. Maps all pathways against call expected impacts from Tier 2B. Produces `impact_architecture.json` (schema `orch.phase5.impact_architecture.v1`) in Tier 4. `phase_05_gate` is evaluated by the runner after this agent writes all canonical outputs.

Requires both `phase_02_gate` AND `phase_03_gate` to have passed (edges `e02_to_05` and `e03_to_05`).

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §7 Phase 5 gate condition, §13.2 (fabricated call constraints — expected impacts), §13.3 (fabricated project facts — impact mechanisms), §13.9 (generic impact language prohibited), §9.4 (durable decisions), §10.5 (traceability obligation)
2. `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/gate_result.json` — Verify `phase_02_gate` has passed
3. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json` — Verify `phase_03_gate` has passed (both predecessors must pass)
4. `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` — Call expected outcomes for pathway mapping
5. `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` — Call expected impacts for pathway mapping; every `expected_impact_id` must appear in at least one pathway
6. `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` — Evaluation weights for impact narrative prioritisation
7. `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` — Project-specific outcome definitions
8. `docs/tier3_project_instantiation/architecture_inputs/impacts.json` — Project-specific impact definitions
9. `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` — Refined concept vocabulary; schema `orch.phase2.concept_refinement_summary.v1`
10. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — WP deliverables as traceable project mechanisms; schema `orch.phase3.wp_structure.v1`
11. `.claude/agents/impact_architect.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node binding: `n05_impact_architecture`
- Phase: `phase_05_impact_architecture`
- Entry gate: none (but both `phase_02_gate` and `phase_03_gate` are mandatory predecessors)
- Exit gate: `phase_05_gate`
- Predecessor edges: `e02_to_05` (`phase_02_gate`) and `e03_to_05` (`phase_03_gate`)
- `gate-enforcement` skill: invoked by this agent after all outputs are complete

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| `phase_02_gate` gate result | Tier 4 | `phase_outputs/phase2_concept_refinement/gate_result.json` | Must show `pass`; halt immediately if absent or fail |
| `phase_03_gate` gate result | Tier 4 | `phase_outputs/phase3_wp_design/gate_result.json` | Must show `pass`; halt immediately if absent or fail |
| Expected outcomes | Tier 2B extracted | `tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | Must be non-empty; must not be inferred from memory |
| Expected impacts | Tier 2B extracted | `tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Must be non-empty; every `expected_impact_id` must appear in at least one pathway |
| Evaluation priority weights | Tier 2B extracted | `tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | Required for narrative prioritisation |
| Project outcomes | Tier 3 | `architecture_inputs/outcomes.json` | Must be non-empty; project-specific outcome definitions |
| Project impacts | Tier 3 | `architecture_inputs/impacts.json` | Must be non-empty; project-specific impact definitions |
| Phase 2 summary | Tier 4 | `phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | Must be present; schema `orch.phase2.concept_refinement_summary.v1` |
| WP structure | Tier 4 | `phase_outputs/phase3_wp_design/wp_structure.json` | Must be present; `work_packages` and `deliverables` used as traceable project mechanisms |

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Verify both predecessor gates.**
Read both gate result files. If either is absent or not `pass`, halt immediately. Write `decision_type: constitutional_halt` identifying the unmet edge (`e02_to_05` or `e03_to_05` or both).

**Step 2 — Read all inputs.**
Read all inputs in the Inputs to Inspect table. Extract all `expected_impact_id` values from `expected_impacts.json` — these form the mandatory mapping set. Extract all `deliverable_id` values from `wp_structure.json` — these are the traceable project mechanisms for impact claims. If `expected_impacts.json` is absent or empty, execute Failure Case 2.

**Step 3 — Invoke impact-pathway-mapper skill.**
Apply the `impact-pathway-mapper` skill: for each `expected_impact_id` from Tier 2B `expected_impacts.json`:
- Map the call expected impact to at least one project output (identified by `deliverable_id` from `wp_structure.json`)
- Define the outcome intermediate step (output → outcome)
- Define the impact narrative (outcome → broader impact)
- Record `tier2b_source_ref` for the expected impact source
If any call expected impact cannot be mapped to a project output, flag it as an uncovered impact — do not fabricate a project output to satisfy the mapping. Record it in the decision log as `scope_conflict`. An unmapped expected impact will block `phase_05_gate` condition `g06_p04`.

**Step 4 — Define KPIs.**
For each impact pathway, define at least one KPI:
- `kpi_id`: unique
- `description`: non-empty
- `target`: non-empty
- `measurement_method`: non-empty
- `traceable_to_deliverable`: must reference a `deliverable_id` from `wp_structure.json`
KPIs not traceable to a named WP deliverable are constitutional violations (CLAUDE.md §13.3). If a KPI target is set by inference from project context, flag it as an assumption and document it.

**Step 5 — Invoke dissemination-exploitation-communication-check skill.**
Define the dissemination plan, exploitation plan, and sustainability mechanism. Apply the `dissemination-exploitation-communication-check` skill to verify:
- Dissemination activities: non-empty, specific to the project, with defined `target_audience` and `responsible_partner` from Tier 3
- Exploitation activities: non-empty, with `expected_result` and `responsible_partner`
- Sustainability: non-empty `description` with `responsible_partners` array
DEC plans must not be generic templates — all elements must be grounded in project activities and Tier 3 consortium data.

**Step 6 — Invoke proposal-section-traceability-check skill.**
Before finalizing, apply the `proposal-section-traceability-check` skill to all impact claims. Assign Confirmed/Inferred/Assumed/Unresolved status. Any impact claim without a named WP deliverable mechanism must be flagged as Unresolved, not asserted as Confirmed (CLAUDE.md §13.3). Write unattributed assertions to `docs/tier4_orchestration_state/validation_reports/`.

**Step 7 — Construct impact_architecture.json.**
Write `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` with all required fields. `artifact_status` must be absent at write time.

**Step 8 — Invoke gate-enforcement skill.**
Invoke the `gate-enforcement` skill to evaluate `phase_05_gate`. Gate conditions:
1. Both `phase_02_gate` and `phase_03_gate` passed (`g06_p01`, `g06_p02`)
2. Full impact architecture written to Tier 4 (`g06_p03`, `g06_p03b`)
3. All call expected impacts have at least one mapped project output (`g06_p04`)
4. KPI set defined and traceable to WP deliverables (`g06_p05`)
5. Dissemination and exploitation logic defined (`g06_p06`, `g06_p07`)
6. Sustainability mechanism defined (`g06_p08`)

**Step 9 — Write decision log entries.**
Invoke `decision-log-update` for all material decisions: impact pathway constructions, unmapped expected impacts, inferred KPI targets, DEC partner assignments.

---

## Output construction rules

### `impact_architecture.json` (schema-bound)

**Path:** `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json`
**Schema ID:** `orch.phase5.impact_architecture.v1`
**Provenance:** run_produced

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.phase5.impact_architecture.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `artifact_status` | NO — absent at write time | Runner stamps after `phase_05_gate` evaluation |
| `impact_pathways` | yes, non-empty array | Every `expected_impact_id` from Tier 2B must appear (`all_impacts_mapped` predicate); each: `pathway_id`, `expected_impact_id`, `project_outputs` (non-empty, `deliverable_id` join keys), `outcomes` (array), `impact_narrative` (non-empty prose), `tier2b_source_ref` |
| `kpis` | yes, non-empty array | Each KPI: `kpi_id`, `description`, `target`, `measurement_method`, `traceable_to_deliverable` (join key from `wp_structure.json`) |
| `dissemination_plan` | yes, non-null | `activities` (non-empty array with `activity_type`, `target_audience`, `responsible_partner`); `open_access_policy` (non-empty) |
| `exploitation_plan` | yes, non-null | `activities` (non-empty array with `activity_type`, `expected_result`, `responsible_partner`) |
| `sustainability_mechanism` | yes, non-null | `description` (non-empty); `responsible_partners` (non-empty array) |

---

## Traceability requirements

Every impact claim must reference a specific WP deliverable (`deliverable_id` from `wp_structure.json`) as the project mechanism. Generic programme-level impact language is prohibited (CLAUDE.md §13.9, must-not). Every pathway entry must carry a `tier2b_source_ref` to the call expected impact. KPI targets derived by inference must be flagged as Assumed. All Tier 2B expected impacts must be addressed or explicitly flagged as uncovered — silent omission is prohibited.

---

## Gate awareness

### Predecessor gates
Both `phase_02_gate` (edge `e02_to_05`) AND `phase_03_gate` (edge `e03_to_05`) must have passed. Verify both before any action. If either is unmet: halt, write `constitutional_halt` identifying which edge.

### Exit gate
`phase_05_gate` — evaluated after this agent writes all canonical outputs. This agent invokes `gate-enforcement` skill.

Gate conditions:
1. Both predecessors passed (`g06_p01`, `g06_p02`)
2. Impact architecture written to Tier 4 (`g06_p03`, `g06_p03b`)
3. All call expected impacts mapped (`g06_p04`)
4. KPIs traceable to WP deliverables (`g06_p05`)
5. Dissemination and exploitation defined (`g06_p06`, `g06_p07`)
6. Sustainability defined (`g06_p08`)

Gate result written by runner to `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json`. Blocking edge on pass: `e05_to_06` (n06).

---

## Failure declaration protocol

#### Case 1: Gate condition not met (phase_05_gate fails)
- Do not proceed
- Write `impact_architecture.json` with full content produced; document unmapped expected impact IDs
- Write decision log: `decision_type: gate_failure`; list unmapped `expected_impact_id` values from Tier 2B
- Must not: fabricate a project output to satisfy the `all_impacts_mapped` predicate (CLAUDE.md §13.3)

#### Case 2: Required input absent
- Halt if `expected_impacts.json`, `expected_outcomes.json`, or `wp_structure.json` are absent
- Write decision log: `decision_type: gate_failure`
- Must not: infer expected impacts from agent memory (CLAUDE.md §13.2)

#### Case 3: Mandatory predecessor gate(s) not passed
- Halt immediately if either `phase_02_gate` or `phase_03_gate` is unmet
- Write: `decision_type: constitutional_halt`; name the unmet edge

#### Case 4: Impact claim without traceable project mechanism
- Flag as Unresolved — do not assert as Confirmed
- Write traceability flag to validation_reports via `proposal-section-traceability-check` skill
- Write decision log: `assumption` or `scope_conflict`
- Must not: assert impact claims without a named WP deliverable (CLAUDE.md §13.3)

---

## Decision-log obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: impact_architect`, `phase_id: phase_05_impact_architecture`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Impact pathway construction (output → outcome → impact) | `material_decision` | Pathway ID; Tier 2B source; WP deliverable(s) used |
| Expected impact that cannot be mapped to any project output | `scope_conflict` | Expected impact ID; Tier 2B source; what is missing |
| KPI target set by inference from project context | `assumption` | KPI ID; inference basis; Tier 3 source |
| DEC activity assigned to a partner by inference | `assumption` | Activity; partner; Tier 3 evidence |
| `phase_05_gate` passes | `gate_pass` | Gate ID; all impacts mapped; run_id |
| `phase_05_gate` fails | `gate_failure` | Gate ID; unmapped expected impact IDs |
| Predecessor gate(s) not passed | `constitutional_halt` | Edge ID; predecessor status |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not fabricate coverage of a call expected impact not addressed by a project output — triggers Failure Case 1 and 4
2. Must not assert impact claims without a traceable project mechanism — triggers Failure Case 4
3. Must not use generic programme-level impact language without project-specific grounding — any such content must be flagged
4. Must not produce KPIs not traceable to named WP deliverables — `traceable_to_deliverable` field required
5. Must not operate before both `phase_02_gate` and `phase_03_gate` have passed — triggers Failure Case 3

Universal constraints from `node_body_contract.md` §3:
6. Must not write `artifact_status` to any output file (runner-managed)
7. Must not write `gate_result.json` (runner-managed)
8. Must not infer expected impacts from agent memory when Tier 2B files are present (CLAUDE.md §13.9)

---

## Completion criteria

This agent's task is complete when all of the following conditions are met:

1. `impact_architecture.json` is written with all required fields; every `expected_impact_id` from Tier 2B appears in at least one pathway; `artifact_status` is absent
2. Every `kpi.traceable_to_deliverable` references a `deliverable_id` from `wp_structure.json`
3. `dissemination_plan`, `exploitation_plan`, and `sustainability_mechanism` are non-null and non-empty
4. All unmapped expected impacts are documented in the decision log
5. All material decisions are written to the decision log
6. `gate-enforcement` skill has been invoked

Completion does not equal gate passage. `phase_05_gate` is evaluated by the runner.
