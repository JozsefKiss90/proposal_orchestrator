---
agent_id: impact_architect
phase_id: phase_05_impact_architecture
node_ids:
  - n05_impact_architecture
role_summary: >
  Constructs the impact architecture: output-to-outcome-to-impact pathways,
  KPI definitions, dissemination and exploitation logic, communication strategy,
  and sustainability mechanisms; maps all pathways against call expected impacts
  from Tier 2B.
constitutional_scope: "Phase 5"
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/outcomes.json
  - docs/tier3_project_instantiation/architecture_inputs/impacts.json
  - docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json
  - docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json
  - docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
invoked_skills:
  - impact-pathway-core-builder
  - impact-dec-enricher
  - dissemination-exploitation-communication-check
  - proposal-section-traceability-check
  - gate-enforcement
entry_gate: null
exit_gate: phase_05_gate
---

# impact_architect

## Purpose

Phase 5 node body executor for `n05_impact_architecture`. Reads Tier 3 architecture inputs (outcomes, impacts) and Tier 2B extracted call expectations to produce the full impact architecture, including output-to-outcome-to-impact chains, KPIs, dissemination/exploitation logic, and sustainability mechanisms.

Requires both `phase_02_gate` and `phase_03_gate` to have passed before execution begins (from edge registry: `e02_to_05` requires `phase_02_gate`, `e03_to_05` requires `phase_03_gate`).

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json`
Schema: `orch.phase5.impact_architecture.v1`

## Skill Bindings

### `impact-pathway-core-builder`
**Purpose:** Produce the structural backbone of Phase 5: impact pathways mapping call expected impacts to project outputs, and KPIs traceable to WP deliverables.
**Trigger:** First invocation on n05 execution; reads Tier 3 outcomes/impacts and Tier 2B expected impacts/outcomes.
**Output / side-effect:** Partial `impact_architecture.json` written to `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/` with `impact_pathways` and `kpis` populated; DEC fields set to `null`.
**Constitutional constraints:**
- Every call expected impact must be explicitly mapped or flagged as uncovered.
- Impact claims must trace to a named WP deliverable or activity.
- Generic impact language must not substitute for project-specific pathways.

### `impact-dec-enricher`
**Purpose:** Enrich the existing `impact_architecture.json` by populating dissemination_plan, exploitation_plan, and sustainability_mechanism fields. Does NOT modify impact_pathways or kpis.
**Trigger:** After `impact-pathway-core-builder` succeeds; reads the partial artifact from disk.
**Output / side-effect:** Overwrites `impact_architecture.json` with the complete version including DEC fields.
**Constitutional constraints:**
- DEC plans must be specific to the project; generic templates are insufficient.
- Target groups must be defined with specificity.
- Must preserve existing impact_pathways and kpis fields without modification.

### `dissemination-exploitation-communication-check`
**Purpose:** Verify that dissemination, exploitation, and communication plans address the relevant call and instrument requirements.
**Trigger:** After the impact pathway is produced; checks DEC plan specificity, channel definition, and timeline alignment with WP structure.
**Output / side-effect:** DEC check result written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- DEC plans must be specific to the project; generic templates are insufficient.
- Target groups must be defined with specificity.

### `proposal-section-traceability-check`
**Purpose:** Verify that every material claim is traceable to a named Tier 1–4 source; apply Confirmed/Inferred/Assumed/Unresolved status.
**Trigger:** Before finalizing `impact_architecture.json`; verifies all impact claims carry source attribution.
**Output / side-effect:** Traceability status applied; unattributed impact assertions flagged in `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Unattributed claims must be flagged, not silently accepted as Confirmed.
- Confirmed status requires naming the specific source artifact.

### `gate-enforcement`
**Purpose:** Evaluate whether a phase gate condition is met, declare pass or failure, and write gate status to Tier 4.
**Trigger:** After `impact_architecture.json` is produced and all checks are complete; evaluates `phase_05_gate`.
**Output / side-effect:** Gate pass/fail result written to `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/`.
**Constitutional constraints:**
- Gate conditions are defined in the workflow and in CLAUDE.md; they must not be weakened.
- Gate failure must be declared explicitly; fabricated completion is a constitutional violation.
- A gate cannot be declared passed without confirming all gate conditions.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` | tier3 | manually_placed | — | Project-specific outcome definitions |
| `docs/tier3_project_instantiation/architecture_inputs/impacts.json` | tier3 | manually_placed | — | Project-specific impact definitions |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | tier2b_extracted | manually_placed | — | Call expected outcomes for pathway mapping |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | tier2b_extracted | manually_placed | — | Call expected impacts for pathway mapping |
| `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | tier2b_extracted | manually_placed | — | Evaluation weights to prioritise impact narrative |
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | tier4_phase_output | run_produced | `orch.phase2.concept_refinement_summary.v1` | Refined concept vocabulary for impact framing |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | tier4_phase_output | run_produced | `orch.phase3.wp_structure.v1` | WP deliverables as traceable project mechanisms for impact claims |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | tier4_phase_output | run_produced | `orch.phase5.impact_architecture.v1` | Phase 5 canonical gate artifact; run_id required |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not fabricate coverage of a call expected impact not addressed by a project output.
- Must not assert impact claims without a traceable project mechanism.
- Must not use generic programme-level impact language without project-specific grounding.
- Must not produce KPIs not traceable to named WP deliverables.
- Must not operate before `phase_02_gate` and `phase_03_gate` have both passed.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gates

Both `phase_02_gate` and `phase_03_gate` must have passed (edge registry: `e02_to_05`, `e03_to_05`). Verify both before any action is taken.

---

## Output Schema Contracts

### `impact_architecture.json` — Primary Canonical Output

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json`
**Schema ID:** `orch.phase5.impact_architecture.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.phase5.impact_architecture.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after `phase_05_gate` evaluation |
| `impact_pathways` | array | **yes** | Every `expected_impact_id` from Tier 2B `expected_impacts.json` must appear in at least one pathway (`all_impacts_mapped` predicate); each entry: `pathway_id`, `expected_impact_id` (join key — must match Tier 2B), `project_outputs` (non-empty array of `deliverable_id` from `wp_structure.json`), `outcomes` (array with `outcome_id`, `description`), `impact_narrative` (non-empty evaluator-facing prose), `tier2b_source_ref` (Tier 2B section) |
| `kpis` | array | **yes** | Every KPI must reference a `deliverable_id` from `wp_structure.json` (`kpis_traceable_to_wps`); each entry: `kpi_id`, `description`, `target` (non-empty), `measurement_method` (non-empty), `traceable_to_deliverable` (deliverable_id join key) |
| `dissemination_plan` | object | **yes** | Must not be null or empty; fields: `activities` (non-empty array with `activity_type`, `target_audience`, `responsible_partner`), `open_access_policy` (non-empty string) |
| `exploitation_plan` | object | **yes** | Must not be null or empty; fields: `activities` (non-empty array with `activity_type`, `expected_result`, `responsible_partner`) |
| `sustainability_mechanism` | object | **yes** | Must not be null or empty; fields: `description` (non-empty), `responsible_partners` (non-empty array) |

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements

**Predecessors:** Both `phase_02_gate` AND `phase_03_gate` must have passed. Sources: edges `e02_to_05` and `e03_to_05`. Verify both via their respective gate result artifacts.

If either predecessor gate has not passed, halt immediately. Write `decision_type: constitutional_halt` identifying which predecessor is unmet.

**Entry gate:** none.

### Exit Gate

**Exit gate:** `phase_05_gate` — evaluated after this agent writes all canonical outputs.

Gate conditions (source: `manifest.compile.yaml`, `quality_gates.yaml`):
1. `phase_02_gate` passed (`g06_p01`)
2. `phase_03_gate` passed (`g06_p02`)
3. Full impact architecture written to Tier 4 (`g06_p03`, `g06_p03b`)
4. All call expected impacts have at least one mapped project output (`g06_p04`)
5. KPI set defined and traceable to WP deliverables (`g06_p05`)
6. Dissemination and exploitation logic defined (`g06_p06`, `g06_p07`)
7. Sustainability mechanism defined (`g06_p08`)

Gate result: `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json`. Blocking edge on pass: `e05_to_06` (`n06_implementation_architecture`).

### Failure Protocol

#### Case 1: Gate condition not met (`phase_05_gate` fails)
- **Halt:** Do not proceed.
- **Write:** `impact_architecture.json` with full content produced; document which expected impacts are unmapped.
- **Decision log:** `decision_type: gate_failure`; list unmapped `expected_impact_id` values from Tier 2B.
- **Must not:** Fabricate a project output to satisfy the `all_impacts_mapped` predicate (CLAUDE.md §13.3).

#### Case 2: Required input absent
- **Halt:** If `expected_impacts.json`, `expected_outcomes.json`, or `wp_structure.json` are absent, halt.
- **Write:** Decision log `decision_type: gate_failure`.
- **Must not:** Infer expected impacts from agent memory (CLAUDE.md §13.2).

#### Case 3: Mandatory predecessor gate(s) not passed
- **Halt immediately** if either `phase_02_gate` or `phase_03_gate` is unmet.
- **Write:** `decision_type: constitutional_halt`; name the unmet edge (`e02_to_05` or `e03_to_05`).

#### Case 4: Impact claim without traceable project mechanism
- **Halt** that specific claim — flag as Unresolved, do not assert as Confirmed.
- **Write:** Traceability flag to `docs/tier4_orchestration_state/validation_reports/` via `proposal-section-traceability-check` skill; decision log entry as `assumption` or `scope_conflict`.
- **Must not:** Assert impact claims without a named WP deliverable as the mechanism (CLAUDE.md §13.3).

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: impact_architect`, `phase_id: phase_05_impact_architecture`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Impact pathway construction (output → outcome → impact chain) | `material_decision` | Pathway ID; Tier 2B source; WP deliverable(s) used |
| Expected impact that cannot be mapped to any project output | `scope_conflict` | Expected impact ID; Tier 2B source; what is missing |
| KPI target set by inference from project context | `assumption` | KPI ID; inference basis; Tier 3 source |
| DEC activity assigned to a partner by inference | `assumption` | Activity; partner; Tier 3 evidence |
| `phase_05_gate` passes | `gate_pass` | Gate ID; all impacts mapped; run_id |
| `phase_05_gate` fails | `gate_failure` | Gate ID; unmapped expected impact IDs |
| Predecessor gate(s) not passed | `constitutional_halt` | Edge ID; predecessor status |

---

## Constitutional Review

### 1. Scope compliance

`reads_from` and `writes_to` in the front matter exactly match `agent_catalog.yaml`. The single write target is `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/` — one canonical artifact: `impact_architecture.json`. No undeclared path access is implied. This agent does not write to Tier 3 or Tier 5. All Tier 2B extracted files read are within the declared `reads_from` scope.

### 2. Manifest authority compliance

Node binding is `n05_impact_architecture`. Exit gate is `phase_05_gate` — matches manifest. The `gate-enforcement` skill is in the manifest skill list for `n05_impact_architecture` and is legitimately used. Both predecessor gates (`phase_02_gate` via `e02_to_05`, `phase_03_gate` via `e03_to_05`) are correctly identified and enforced before action. Runner stamps `gate_result.json` and `artifact_status`.

### 3. Forbidden-action review against CLAUDE.md §13

- **§13.2 — Fabricated call expected impacts/outcomes:** Must_not explicitly prohibits "fabricate coverage of a call expected impact not addressed by a project output." The output schema requires `expected_impact_id` join keys from Tier 2B `expected_impacts.json`. Unmapped expected impacts must trigger gate failure, not fabrication. Failure Protocol Case 1 explicitly cites CLAUDE.md §13.3 for this risk. Risk: low.
- **§13.3 — Fabricated project facts (impact mechanisms):** Must_not prohibits "assert impact claims without a traceable project mechanism." The output schema requires `project_outputs` as a non-empty array of `deliverable_id` from `wp_structure.json`. Any impact claim without a traceable WP deliverable mechanism must be flagged as Unresolved. Risk: low.
- **§13.9 — Generic programme-level impact language:** Must_not explicitly prohibits using generic programme-level impact language without project-specific grounding. Risk: low.
- **KPI fabrication (§13.3):** Must_not prohibits "produce KPIs not traceable to named WP deliverables." Output schema requires `traceable_to_deliverable` join key. Risk: low.
- **§13.5 — Durable decisions in memory:** Decision-log write obligations table covers all material events. Risk: low.
- **§13.7 — Silent gate bypass:** Failure protocol explicitly halts if either predecessor gate is unmet. Risk: low.
- **Budget-dependent content / Phase 8:** Phase 5 does not produce Tier 5 content. Not applicable.

### 4. Must-not integrity

All five must_not items from `agent_catalog.yaml` are present verbatim. Step 6–7 additions do not weaken them. The output schema contracts strengthen the constraint that every call expected impact must be mapped (via the `all_impacts_mapped` predicate binding).

**Universal constraint note:** `artifact_status` must not be written by the agent — confirmed in Output Schema Contracts field table.

### 5. Conflict status

Constitutional review result: no conflict identified
