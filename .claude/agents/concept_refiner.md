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

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not invent a new project concept not grounded in Tier 3.
- Must not fabricate coverage of an expected outcome not addressed by the project.
- Must not operate before `phase_01_gate` has passed.
- Must not produce a topic mapping with unmapped mandatory expected outcomes without flagging them.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`phase_01_gate` must have passed. Verify before any action is taken.

---

## Output Schema Contracts

### 1. `concept_refinement_summary.json` — Primary Canonical Output

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json`
**Schema ID:** `orch.phase2.concept_refinement_summary.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.phase2.concept_refinement_summary.v1"` |
| `run_id` | string | **yes** | Propagated verbatim from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after `phase_02_gate` evaluation |
| `topic_mapping_rationale` | object | **yes** | Must not be empty; each entry corresponds to a call topic element from Tier 2B `expected_outcomes.json` or `scope_requirements.json`; each entry requires: `topic_element_id` (Tier 2B identifier), `mapping_to_concept` (how the project addresses it), `tier2b_source_ref` (Tier 2B section/file), `tier3_evidence_ref` (Tier 3 path/field providing project evidence) |
| `scope_conflict_log` | array | **yes** | Empty array is valid when no conflicts exist; when conflicts exist, each entry: `conflict_id`, `description`, `resolution_status` (resolved / unresolved), `resolution_note` (required when resolved), `tier2b_source_ref`; any `resolution_status: unresolved` entry blocks `phase_02_gate` |
| `strategic_differentiation` | string | **yes** | Must not be empty or a placeholder; narrative explaining the project's differentiation within the call scope; grounded in Tier 3 project brief |

### 2. `topic_mapping.json` — Tier 3 Output (no schema_id in spec)

**Canonical path:** `docs/tier3_project_instantiation/call_binding/topic_mapping.json`
**Provenance:** tier3_updated (listed as `manually_placed` in artifact registry — no schema_id_value defined)

Required content (gate condition `g03_p02`, `g03_p03`):
- Non-empty mapping entries; each entry must carry: `topic_element_id`, `project_element_ref` (Tier 3 concept or objective element), `tier2b_source_ref` (source section in work programme or call extract)
- All mappings must carry source references (`g03_p03` predicate)

### 3. `compliance_profile.json` — Tier 3 Output (no schema_id in spec)

**Canonical path:** `docs/tier3_project_instantiation/call_binding/compliance_profile.json`
**Provenance:** tier3_updated (listed as `manually_placed` — no schema_id_value defined)

Required content (gate condition `g03_p04`):
- Non-empty compliance profile; derived from Tier 2B `eligibility_conditions.json` and `call_constraints.json`
- Each entry: `condition_id`, `compliance_status` (compliant / requires_action / not_applicable), `evidence_ref` (Tier 3 source), `tier2b_source_ref`

---

## Gate Awareness and Failure Behaviour

### Predecessor Gate Requirements

**Predecessor:** `phase_01_gate` — must have passed before this agent acts. Source: edge `e01_to_02` in `manifest.compile.yaml` edge_registry. This is verified via the gate result artifact at `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json`.

If `phase_01_gate` has not passed, halt immediately — do not read Tier 2B files or any Phase 1 outputs. Write `decision_type: constitutional_halt` to the decision log.

**Entry gate:** none (this node has no `entry_gate` in the manifest).

### Exit Gate

**Exit gate:** `phase_02_gate` — evaluated after this agent writes all canonical outputs.

Gate conditions this agent is responsible for satisfying (source: `manifest.compile.yaml`, `quality_gates.yaml`):
1. `phase_01_gate` must have passed (`g03_p01`) — predecessor check
2. `topic_mapping.json` non-empty and all mappings carry source references (`g03_p02`, `g03_p03`)
3. `compliance_profile.json` non-empty (`g03_p04`)
4. `concept_refinement_summary.json` written to Tier 4 (`g03_p05`, `g03_p07`)
5. No unresolved scope conflicts in `scope_conflict_log` (`g03_p06`)

Gate result written to `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/gate_result.json` by runner. Blocking edges on pass: `e02_to_03` (`n03_wp_design`), `e02_to_05` (`n05_impact_architecture` — also requires `phase_03_gate`).

### Failure Protocol

#### Case 1: Gate condition not met (`phase_02_gate` fails)
- **Halt:** Do not proceed.
- **Write:** `concept_refinement_summary.json` identifying which conditions failed; populate `scope_conflict_log` with all unresolved conflicts.
- **Decision log:** `decision_type: gate_failure`; list failed conditions with predicate refs.
- **Must not:** Mark a scope conflict resolved when it is not. Must not produce a `topic_mapping.json` with entries missing source references.

#### Case 2: Required input absent
- **Halt:** If `phase1_call_analysis/call_analysis_summary.json` is absent, or if Tier 2B extracted files are empty, halt.
- **Write:** Decision log entry with the missing input path; `decision_type: gate_failure`.
- **Must not:** Reconstruct call constraints from memory.

#### Case 3: Mandatory predecessor gate not passed
- **Halt immediately:** If `phase_01_gate` gate result shows `fail` or is absent.
- **Write:** `decision_type: constitutional_halt` — records which predecessor gate was unmet.
- **Must not:** Proceed with concept alignment before Phase 1 is complete.

#### Case 4: Constitutional prohibition triggered
- **Halt:** If fabricating concept alignment (inventing that an expected outcome is addressed when it is not — CLAUDE.md §13.3, §13.2).
- **Write:** `decision_type: constitutional_halt`; identify the prohibited action.
- **Must not:** Produce a `topic_mapping.json` entry that claims coverage of an expected outcome not addressed by the project.

### Decision-Log Write Obligations

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
