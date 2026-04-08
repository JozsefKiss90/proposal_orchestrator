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
  - impact-pathway-mapper
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

### `impact-pathway-mapper`
**Purpose:** Map project outputs to call expected outcomes and expected impacts; produce a structured pathway showing output-to-outcome-to-impact chains with source references.
**Trigger:** Primary invocation on n05 execution; reads Tier 3 outcomes/impacts and Tier 2B expected impacts/outcomes.
**Output / side-effect:** Structured impact pathway with output-to-outcome-to-impact chains written to `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/`.
**Constitutional constraints:**
- Every call expected impact must be explicitly mapped or flagged as uncovered.
- Impact claims must trace to a named WP deliverable or activity.
- Generic impact language must not substitute for project-specific pathways.

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

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

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
