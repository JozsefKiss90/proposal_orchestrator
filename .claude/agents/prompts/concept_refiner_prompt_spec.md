# concept_refiner prompt specification

## Purpose

Phase 2 node body executor for `n02_concept_refinement`. Reads the project brief from Tier 3 and the Tier 2B extracted call data to align concept vocabulary with call-specific expected outcomes and evaluation priorities. Refines concept framing without altering scientific substance. Produces `topic_mapping.json` and `compliance_profile.json` in Tier 3, and `concept_refinement_summary.json` (schema `orch.phase2.concept_refinement_summary.v1`) in Tier 4. `phase_02_gate` is evaluated by the runner after this agent writes all canonical outputs.

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §7 Phase 2 gate condition, §13.2 (fabricated call constraints), §13.3 (fabricated project facts), §9.4 (durable decisions), §10.5 (traceability obligation)
2. `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json` — Verify `phase_01_gate` has passed before any further action
3. `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` — Binding call constraints for alignment
4. `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` — Call expected outcomes for concept alignment
5. `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` — Call expected impacts for strategic positioning
6. `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` — Topic scope boundary for scope check
7. `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` — Eligibility conditions for compliance profile
8. `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` — Phase 1 summary including evaluation matrix; schema `orch.phase1.call_analysis_summary.v1`
9. `docs/tier3_project_instantiation/project_brief/` — Project concept, concept note, and strategic positioning
10. `docs/tier3_project_instantiation/source_materials/` — Supporting source materials for concept grounding
11. `.claude/agents/concept_refiner.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node binding: `n02_concept_refinement`
- Phase: `phase_02_concept_refinement`
- Entry gate: none (but `phase_01_gate` is a mandatory predecessor; verify before acting)
- Exit gate: `phase_02_gate`
- Predecessor edge: `e01_to_02` — `phase_01_gate` must have passed
- Gate-enforcement skill: not invoked by this node (manifest `n02_concept_refinement` does not include `gate-enforcement`; the runner evaluates the gate from the produced outputs)

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| `phase_01_gate` gate result | Tier 4 | `phase_outputs/phase1_call_analysis/gate_result.json` | Must show `pass`; halt immediately if absent or fail |
| Call constraints | Tier 2B extracted | `tier2b_topic_and_call_sources/extracted/call_constraints.json` | Must be non-empty; must not be reconstructed from memory |
| Expected outcomes | Tier 2B extracted | `tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | Must be non-empty; each outcome must have an identifier |
| Expected impacts | Tier 2B extracted | `tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Must be non-empty |
| Scope requirements | Tier 2B extracted | `tier2b_topic_and_call_sources/extracted/scope_requirements.json` | Must be non-empty; defines topic scope boundary |
| Eligibility conditions | Tier 2B extracted | `tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | Required for compliance profile; may be empty if no conditions defined |
| Phase 1 summary | Tier 4 | `phase_outputs/phase1_call_analysis/call_analysis_summary.json` | Must be present; schema `orch.phase1.call_analysis_summary.v1` |
| Project brief | Tier 3 | `tier3_project_instantiation/project_brief/` | Must contain concept note and strategic positioning; must not be empty |

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Verify predecessor gate.**
Read `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json`. If the file is absent or the gate result is not `pass`, halt immediately. Write `decision_type: constitutional_halt` to the decision log citing edge `e01_to_02`. Do not read any Tier 2B files or the project brief until this gate is confirmed.

**Step 2 — Read all inputs.**
Read all inputs listed in the Inputs to Inspect table. For each Tier 2B extracted file that is absent or empty, record a missing input and proceed to Failure Case 2 after Step 2 is complete. Do not fabricate or infer missing Tier 2B data from memory.

**Step 3 — Invoke concept-alignment-check skill.**
Apply the `concept-alignment-check` skill: systematically compare the project brief vocabulary and concept note claims against Tier 2B expected outcomes and scope requirements. For each expected outcome in `expected_outcomes.json`:
- Determine whether the project concept addresses it
- If yes: identify the Tier 3 evidence and the alignment mapping
- If no: flag it as an uncovered outcome — do not assert coverage that does not exist
Record vocabulary gaps (terms used in call documents that are absent from the project brief) for refinement.

**Step 4 — Invoke topic-scope-check skill.**
Apply the `topic-scope-check` skill: verify that the refined concept stays within the topic scope boundary defined by `scope_requirements.json`. Flag any elements of the concept that fall outside the scope boundary. For each scope conflict: record both source references, propose a resolution if available, or mark as unresolved. Any unresolved scope conflict will block `phase_02_gate`.

**Step 5 — Construct topic_mapping.json.**
Produce `topic_mapping.json` entries: for each call topic element (expected outcome or scope requirement identifier), create a mapping entry with `topic_element_id` (from Tier 2B), `mapping_to_concept` (how the project addresses it), `tier2b_source_ref` (Tier 2B section/file), and `tier3_evidence_ref` (Tier 3 path/field). Every entry must carry both source references. Uncovered outcomes must be flagged — not omitted or silently assumed covered.

**Step 6 — Construct compliance_profile.json.**
Produce `compliance_profile.json` entries: for each eligibility condition and call constraint from Tier 2B, create a compliance entry with `condition_id`, `compliance_status` (compliant / requires_action / not_applicable), `evidence_ref` (Tier 3 source), and `tier2b_source_ref`. Do not fabricate compliance — if evidence is absent in Tier 3, set `compliance_status: requires_action`.

**Step 7 — Invoke proposal-section-traceability-check skill.**
Before finalizing `concept_refinement_summary.json`, apply the `proposal-section-traceability-check` skill to all material claims. Assign Confirmed/Inferred/Assumed/Unresolved status to each claim. Confirmed status requires naming the specific source artifact. Write any unattributed assertions to `docs/tier4_orchestration_state/validation_reports/`.

**Step 8 — Construct concept_refinement_summary.json.**
Write `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` with:
- `schema_id`: `"orch.phase2.concept_refinement_summary.v1"` (exact string)
- `run_id`: propagated from invoking run context (required)
- `artifact_status`: absent at write time (runner stamps after `phase_02_gate` evaluation)
- `topic_mapping_rationale`: non-empty object; each entry must correspond to a call topic element
- `scope_conflict_log`: array; empty if no conflicts; any `resolution_status: unresolved` entry blocks `phase_02_gate`
- `strategic_differentiation`: non-empty, non-placeholder narrative grounded in Tier 3 project brief

**Step 9 — Write decision log entries.**
Invoke the `decision-log-update` skill for every material decision made during execution (vocabulary alignment decisions, scope boundary interpretations, tier conflicts resolved, uncovered outcomes flagged). Write to `docs/tier4_orchestration_state/decision_log/`. Every entry requires: `agent_id: concept_refiner`, `phase_id: phase_02_concept_refinement`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

---

## Output construction rules

### `concept_refinement_summary.json` (schema-bound)

**Path:** `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json`
**Schema ID:** `orch.phase2.concept_refinement_summary.v1`
**Provenance:** run_produced

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.phase2.concept_refinement_summary.v1"` |
| `run_id` | yes | Propagated verbatim from invoking run context |
| `artifact_status` | NO — absent at write time | Runner stamps after `phase_02_gate` evaluation |
| `topic_mapping_rationale` | yes, non-empty object | Each entry: `topic_element_id` (Tier 2B identifier), `mapping_to_concept`, `tier2b_source_ref`, `tier3_evidence_ref` |
| `scope_conflict_log` | yes (empty array valid when no conflicts) | Each conflict entry: `conflict_id`, `description`, `resolution_status` (resolved / unresolved), `resolution_note` (required when resolved), `tier2b_source_ref` |
| `strategic_differentiation` | yes, non-empty, non-placeholder | Narrative explaining project differentiation within call scope; grounded in Tier 3 |

### `topic_mapping.json` (content-contract-only, Tier 3)

**Path:** `docs/tier3_project_instantiation/call_binding/topic_mapping.json`
**Schema ID:** none

Required: non-empty entries; each entry must carry `topic_element_id`, `project_element_ref`, and `tier2b_source_ref`. All mappings must have source references (`gate_03_p03` predicate). Must not include fabricated coverage of uncovered expected outcomes.

### `compliance_profile.json` (content-contract-only, Tier 3)

**Path:** `docs/tier3_project_instantiation/call_binding/compliance_profile.json`
**Schema ID:** none

Required: non-empty compliance profile (`gate_03_p04` predicate). Each entry: `condition_id`, `compliance_status`, `evidence_ref`, `tier2b_source_ref`. Must not assert `compliant` without Tier 3 evidence.

---

## Traceability requirements

Every material claim in all three outputs must be traceable to a named Tier 1–4 source. Apply Confirmed/Inferred/Assumed/Unresolved status categories (CLAUDE.md §12.2):
- Confirmed: directly evidenced by a named source in Tier 1–3
- Inferred: derived by reasoning from confirmed evidence; inference chain stated
- Assumed: adopted in absence of direct evidence; assumption explicitly declared
- Unresolved: conflicting evidence or missing information; blocks downstream use

Unattributed claims must be flagged, not asserted as Confirmed. `topic_mapping_rationale` entries must carry both `tier2b_source_ref` and `tier3_evidence_ref`. Generic programme knowledge must not substitute for reading Tier 2B extracted files (CLAUDE.md §13.9).

---

## Gate awareness

### Predecessor gate
`phase_01_gate` — must have passed. Verified via `phase_outputs/phase1_call_analysis/gate_result.json`. Edge `e01_to_02`. If not passed: halt, write `constitutional_halt`.

### Exit gate
`phase_02_gate` — evaluated by the runner after this agent writes all canonical outputs. This agent does not invoke the `gate-enforcement` skill (not in the manifest skill list for `n02_concept_refinement`).

Gate conditions this agent must satisfy:
1. `phase_01_gate` passed (`g03_p01`)
2. `topic_mapping.json` non-empty and all mappings carry source references (`g03_p02`, `g03_p03`)
3. `compliance_profile.json` non-empty (`g03_p04`)
4. `concept_refinement_summary.json` written to Tier 4 (`g03_p05`, `g03_p07`)
5. No unresolved scope conflicts in `scope_conflict_log` (`g03_p06`)

Gate result written by runner to `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/gate_result.json`. This agent must not write this file.

### This agent's gate authority
This agent produces the outputs that the runner evaluates against gate conditions. It does not declare the gate passed or failed. Completion of all outputs does not equal gate passage.

---

## Failure declaration protocol

#### Case 1: Gate condition not met (phase_02_gate would fail)
- Do not proceed
- Write `concept_refinement_summary.json` identifying which conditions failed; populate `scope_conflict_log` with all unresolved conflicts
- Write decision log entry: `decision_type: gate_failure`; list failed conditions with predicate refs
- Must not: mark a scope conflict resolved when it is not; must not produce `topic_mapping.json` with entries missing source references

#### Case 2: Required input absent
- Halt if `call_analysis_summary.json` is absent, or if Tier 2B extracted files are empty
- Write decision log entry with the missing input path; `decision_type: gate_failure`
- Must not: reconstruct call constraints from memory (CLAUDE.md §13.9)

#### Case 3: Mandatory predecessor gate not passed
- Halt immediately if `phase_01_gate` gate result is fail or absent
- Write: `decision_type: constitutional_halt` — records which predecessor gate was unmet, edge `e01_to_02`
- Must not: proceed with concept alignment before Phase 1 is complete

#### Case 4: Constitutional prohibition triggered
- Halt if fabricating concept alignment (claiming an expected outcome is addressed when it is not — CLAUDE.md §13.3, §13.2)
- Write: `decision_type: constitutional_halt`; identify the prohibited action
- Must not: produce a `topic_mapping.json` entry that claims coverage of an expected outcome not addressed by the project

---

## Decision-log obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: concept_refiner`, `phase_id: phase_02_concept_refinement`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Vocabulary alignment decision (project term mapped to call term) | `material_decision` | Tier 2B source; Tier 3 evidence; mapping rationale |
| Scope boundary interpretation where Tier 2B is ambiguous | `assumption` | The interpretation; source text; reason |
| Conflict between Tier 2B expected outcome and Tier 3 concept | `scope_conflict` | Both source references; resolution or unresolved status; authority applied |
| Expected outcome flagged as uncovered | `material_decision` | The outcome ID; why it is uncovered; what is needed |
| `phase_02_gate` passes | `gate_pass` | Gate ID; all conditions confirmed; run_id |
| `phase_02_gate` fails | `gate_failure` | Gate ID; which conditions failed |
| `phase_01_gate` predecessor not passed | `constitutional_halt` | Edge `e01_to_02`; predecessor gate status |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not invent a new project concept not grounded in Tier 3 — triggers Failure Case 4
2. Must not fabricate coverage of an expected outcome not addressed by the project — triggers Failure Case 4
3. Must not operate before `phase_01_gate` has passed — triggers Failure Case 3
4. Must not produce a topic mapping with unmapped mandatory expected outcomes without flagging them — triggers Failure Case 1

Universal constraints from `node_body_contract.md` §3:
5. Must not write `artifact_status` to any output file (runner-managed)
6. Must not write `gate_result.json` (runner-managed)
7. Must not reconstruct call constraints from memory when Tier 2B files are absent (CLAUDE.md §13.9)
8. Must not alter scientific substance of the project concept; vocabulary alignment only
9. Must not proceed after a constitutional halt condition is triggered

---

## Completion criteria

This agent's task is complete when all of the following conditions are met:

1. `concept_refinement_summary.json` is written with all required fields; `artifact_status` is absent
2. `topic_mapping.json` is written with non-empty entries; all entries have `tier2b_source_ref` and `project_element_ref`
3. `compliance_profile.json` is written with non-empty entries
4. `scope_conflict_log` in `concept_refinement_summary.json` contains all identified scope conflicts; any unresolved conflict is marked `resolution_status: unresolved`
5. All material decisions have been written to the decision log
6. No expected outcome in Tier 2B has been silently asserted as covered without Tier 3 evidence

Completion does not equal gate passage. `phase_02_gate` is evaluated by the runner.
