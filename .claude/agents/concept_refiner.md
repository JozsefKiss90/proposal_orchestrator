---
agent_id: concept_refiner
phase_id: phase_02_concept_refinement
node_ids:
  - n02_concept_refinement
role_summary: >
  Aligns the project concept with confirmed call scope and evaluation priorities;
  refines the concept note vocabulary and framing without altering scientific
  substance, and produces the topic mapping and compliance profile for Tier 3.
constitutional_scope: "Phase 2"
reads_from:
  - docs/tier3_project_instantiation/project_brief/
  - docs/tier3_project_instantiation/source_materials/
  - docs/tier2b_topic_and_call_sources/extracted/
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
writes_to:
  - docs/tier3_project_instantiation/call_binding/topic_mapping.json
  - docs/tier3_project_instantiation/call_binding/compliance_profile.json
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
  - docs/tier4_orchestration_state/decision_log/
invoked_skills:
  - concept-alignment-check
  - topic-scope-check
  - proposal-section-traceability-check
  - decision-log-update
entry_gate: null
exit_gate: phase_02_gate
---

# concept_refiner

## Purpose

Phase 2 node body executor for `n02_concept_refinement`. Reads the project brief and Tier 2B extracted call data to align concept vocabulary with call-specific expected outcomes and evaluation priorities. Produces `topic_mapping.json`, `compliance_profile.json` in Tier 3, and `concept_refinement_summary.json` in Tier 4.

Requires `phase_01_gate` to have passed before execution begins.

## Canonical Output

`docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json`
Schema: `orch.phase2.concept_refinement_summary.v1`

## Additional Outputs

- `docs/tier3_project_instantiation/call_binding/topic_mapping.json`
- `docs/tier3_project_instantiation/call_binding/compliance_profile.json`

## Skill Bindings

### `concept-alignment-check`
**Purpose:** Check the alignment between the project concept and the call expected outcomes and scope requirements.
**Trigger:** Primary invocation on n02 execution; reads `project_brief/` and Tier 2B extracted files.
**Output / side-effect:** Alignment analysis written to `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/`; vocabulary gaps and uncovered expected outcomes flagged to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Alignment must be tested against Tier 2B extracted files, not assumed from concept vocabulary.
- Uncovered expected outcomes must be flagged, not silently assumed covered.

### `topic-scope-check`
**Purpose:** Verify that a project concept or proposal section is within the thematic scope defined by Tier 2B scope requirements.
**Trigger:** During concept alignment; verifies the refined concept stays within the topic scope boundary.
**Output / side-effect:** Scope flags written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Scope boundary is defined by Tier 2B only; must not infer scope from generic programme knowledge.
- Out-of-scope flags must be written to the decision log.

### `proposal-section-traceability-check`
**Purpose:** Verify that every material claim is traceable to a named Tier 1–4 source; apply Confirmed/Inferred/Assumed/Unresolved status.
**Trigger:** Before finalizing `concept_refinement_summary.json`; checks all claims in the concept output.
**Output / side-effect:** Traceability status applied to all claims; unattributed assertions flagged in `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Unattributed claims must be flagged, not silently accepted as Confirmed.
- Confirmed status requires naming the specific source artifact.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** Whenever a vocabulary alignment decision, scope boundary interpretation, or tier conflict is resolved during n02 execution.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/project_brief/` | tier3 | manually_placed | — | Project concept, concept note, and strategic positioning |
| `docs/tier3_project_instantiation/source_materials/` | tier3 | manually_placed | — | Supporting source materials for concept grounding |
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | tier2b_extracted | manually_placed | — | Binding call constraints for alignment check |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | tier2b_extracted | manually_placed | — | Call expected outcomes for concept alignment |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | tier2b_extracted | manually_placed | — | Call expected impacts for strategic positioning |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | tier2b_extracted | manually_placed | — | Topic scope boundary for scope check |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | tier2b_extracted | manually_placed | — | Eligibility conditions for compliance profile |
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | tier4_phase_output | run_produced | `orch.phase1.call_analysis_summary.v1` | Phase 1 summary including evaluation matrix |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier3_project_instantiation/call_binding/topic_mapping.json` | tier3_updated | manually_placed | — | Topic mapping produced by concept refinement |
| `docs/tier3_project_instantiation/call_binding/compliance_profile.json` | tier3_updated | manually_placed | — | Compliance profile derived from call constraints |
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | tier4_phase_output | run_produced | `orch.phase2.concept_refinement_summary.v1` | Phase 2 canonical gate artifact; run_id required |

## Contract

This agent is bound by `node_body_contract.md`. Full body implementation is deferred to Steps 6–9 of `agent-generation-plan.md`.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not invent a new project concept not grounded in Tier 3.
- Must not fabricate coverage of an expected outcome not addressed by the project.
- Must not operate before `phase_01_gate` has passed.
- Must not produce a topic mapping with unmapped mandatory expected outcomes without flagging them.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`phase_01_gate` must have passed. Verify before any action is taken.
