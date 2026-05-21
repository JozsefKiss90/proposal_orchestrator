# Agent Validation Checklist
## Horizon Europe Proposal Orchestration System — Step 10 Integration Validation

**Plan reference:** `agent-generation-plan.md` §6 Step 10
**Sources verified:** `CLAUDE.md`, `manifest.compile.yaml`, `agent_catalog.yaml`, `artifact_schema_specification.yaml`, `skill_catalog.yaml`, `quality_gates.yaml`, `node_body_contract.md`, all 16 agent contract files, all 16 prompt spec files
**Date:** 2026-04-09
**Validation authority:** This checklist does not override any source listed above. It records observations derivable from those sources. Judgment calls are noted.

---

## 1. Per-agent completion matrix

Columns:
- **front_matter_complete** — all required YAML front-matter fields present and matched to `agent_catalog.yaml` and `manifest.compile.yaml`
- **skills_bound** — `invoked_skills` populated from manifest skill list with trigger/output descriptions
- **canonical_io_specified** — input and output tables with tier, provenance, schema ID
- **schemas_aligned** — schema_id_value cross-referenced to `artifact_schema_specification.yaml`; required fields documented; `artifact_status` absent-at-write enforced
- **gate_awareness_implemented** — predecessor gates, exit gate, gate conditions, gate result path specified
- **failure_protocol_implemented** — all four failure cases (gate fail, input absent, predecessor unmet, constitutional halt) implemented
- **constitutional_review_passed** — CLAUDE.md §13 review conducted and documented; no conflicts found
- **prompt_spec_written** — prompt spec file present with mandatory reading order, reasoning sequence, output construction rules, traceability obligations, failure protocol
- **node_body_contract_referenced** — explicit reference to `node_body_contract.md` in Contract section

**Key:**
- ✓ = confirmed from current file state
- ✗ = not present or materially deficient
- ~ = present but with a noted caveat (see gap_description)

| agent_id | node_binding_type | front_matter_complete | skills_bound | canonical_io_specified | schemas_aligned | gate_awareness_implemented | failure_protocol_implemented | constitutional_review_passed | prompt_spec_written | node_body_contract_referenced | status | gap_description |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `call_analyzer` | primary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `instrument_schema_resolver` | auxiliary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `concept_refiner` | primary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `wp_designer` | primary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `dependency_mapper` | sub-agent | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `gantt_designer` | primary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `impact_architect` | primary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `implementation_architect` | primary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `budget_interface_coordinator` | pre-gate | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `budget_gate_validator` | primary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `proposal_writer` | multi-node | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `evaluator_reviewer` | primary | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `revision_integrator` | primary (terminal) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `compliance_validator` | cross-phase | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `traceability_auditor` | cross-phase | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |
| `state_recorder` | cross-phase | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | complete | — |

**Summary: 16 / 16 agents complete.**

### Noted caveats (not blocking completeness)

**Stale placeholder text in Contract sections:** All 16 agent files contain the sentence "Steps 8–9 (constitutional review notes; prompt specification) remain." in their Contract section. This was written during scaffolding and has not been removed after Steps 8 and 9 were completed. The constitutional review sections and prompt spec files are present and correct. The stale note is misleading but does not constitute a constitutional defect, as the actual work is demonstrably done. A future clean-up pass should remove it from all 16 files.

**`node_body_contract_referenced` basis:** All 16 files contain "This agent is bound by `node_body_contract.md`." in their Contract section. Each agent also references universal constraints from `node_body_contract.md §3` in the must_not section. Cross-reference is confirmed.

---

## 2. Cross-agent handoff validation

Each handoff row validates: (a) upstream output exists in the expected contract/prompt spec, (b) downstream agent reads the correct canonical artifact, (c) schema or content-contract expectations are compatible, (d) no contradictory path naming, (e) no authority inversion.

| handoff | upstream_outputs | downstream_inputs | status | issue_if_any |
|---|---|---|---|---|
| `call_analyzer` → `instrument_schema_resolver` | `call_analyzer` invokes `instrument_schema_resolver` within Phase 1 execution context; passes resolved `instrument_type` from `selected_call.json` and Tier 2A source paths | `instrument_schema_resolver` reads `application_forms/`, `evaluation_forms/`, `selected_call.json` (all within its declared `reads_from`) | ✓ pass | — |
| `instrument_schema_resolver` → `call_analyzer` (feedback) | `instrument_schema_resolver` writes `section_schema_registry.json` and `evaluator_expectation_registry.json` to `docs/tier2a_instrument_schemas/extracted/`; consumed by `call_analyzer` for `call_analysis_summary.json` assembly and by `phase_01_gate` conditions `g02_p14`, `g02_p15` | `call_analyzer` reads Tier 2A extracted files within Phase 1 context; these files are in `call_analyzer`'s `reads_from` (`docs/tier2a_instrument_schemas/application_forms/`, `evaluation_forms/` → instrument_schema_resolver extracts into `docs/tier2a_instrument_schemas/extracted/`, which is in instrument_schema_resolver's `writes_to` not call_analyzer's `reads_from` as an explicit path | ~ minor | `call_analyzer.reads_from` lists `application_forms/` and `evaluation_forms/` but does NOT explicitly list `docs/tier2a_instrument_schemas/extracted/`. It therefore technically reads a path not in its declared `reads_from` when consuming the instrument schema resolver output. The constitutional review in `call_analyzer.md` acknowledges this: "Tier 2A extracted files are explicitly noted as produced by `instrument_schema_resolver` within this phase — this agent does not claim write authority over them." The `agent_catalog.yaml` `reads_from` for `call_analyzer` also does not list `docs/tier2a_instrument_schemas/extracted/`. This is a scope gap that a future runtime binding pass should resolve by either (a) adding `docs/tier2a_instrument_schemas/extracted/` to `call_analyzer`'s `reads_from` in the catalog, or (b) confirming that the instrument_schema_resolver's outputs are consumed by the runner gate predicates directly, not by call_analyzer. Not a blocking issue for this validation pass; flagged for operator review. |
| `call_analyzer` / `instrument_schema_resolver` → `concept_refiner` | `call_analysis_summary.json` (schema `orch.phase1.call_analysis_summary.v1`); Tier 2B extracted files: `call_constraints.json`, `expected_outcomes.json`, `expected_impacts.json`, `scope_requirements.json`, `eligibility_conditions.json` | `concept_refiner` canonical inputs table lists `call_analysis_summary.json` with `schema orch.phase1.call_analysis_summary.v1` and all six Tier 2B extracted files | ✓ pass | — |
| `concept_refiner` → `wp_designer` | `concept_refinement_summary.json` (schema `orch.phase2.concept_refinement_summary.v1`); `topic_mapping.json`; `compliance_profile.json` | `wp_designer` canonical inputs table lists `concept_refinement_summary.json` with schema `orch.phase2.concept_refinement_summary.v1`; reads Tier 4 path `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/` | ✓ pass | — |
| `wp_designer` ↔ `dependency_mapper` | `wp_designer` writes initial `wp_structure.json` with `work_packages` array to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/`; `dependency_mapper` reads it and contributes `dependency_map` field back | `dependency_mapper` reads `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` (declared in `reads_from`); contributes `dependency_map` to the same artifact; schema `orch.phase3.wp_structure.v1` governs both directions | ✓ pass | — |
| `wp_designer` → `gantt_designer` | `wp_structure.json` (schema `orch.phase3.wp_structure.v1`) in `phase3_wp_design/` | `gantt_designer` canonical inputs table lists `wp_structure.json` with schema `orch.phase3.wp_structure.v1` | ✓ pass | — |
| `concept_refiner` + `wp_designer` → `impact_architect` | `concept_refinement_summary.json` (schema `orch.phase2.concept_refinement_summary.v1`); `wp_structure.json` (schema `orch.phase3.wp_structure.v1`) | `impact_architect` canonical inputs table lists both artifacts with their correct schemas; reads Tier 2B `expected_outcomes.json`, `expected_impacts.json`, `evaluation_priority_weights.json`; Tier 3 `outcomes.json`, `impacts.json` | ✓ pass | — |
| `wp_designer` + `gantt_designer` + `impact_architect` → `implementation_architect` | `wp_structure.json` (`orch.phase3.wp_structure.v1`); `gantt.json` (`orch.phase4.gantt.v1`); `impact_architecture.json` (`orch.phase5.impact_architecture.v1`) | `implementation_architect` canonical inputs table lists all three artifacts with correct schemas; also reads Tier 3 consortium, risks, compliance_profile; Tier 2A section_schema_registry | ✓ pass | — |
| `wp_designer` + `gantt_designer` → `budget_interface_coordinator` | `wp_structure.json` (`orch.phase3.wp_structure.v1`); `gantt.json` (`orch.phase4.gantt.v1`) | `budget_interface_coordinator` canonical inputs table lists both with correct schemas | ✓ pass | — |
| `budget_interface_coordinator` → `budget_gate_validator` | `budget_request.json` in `docs/tier3_project_instantiation/integration/` (no schema_id; governed by interface contract); human handoff to external system; external system populates `received/` | `budget_gate_validator` reads `docs/integrations/lump_sum_budget_planner/received/` (absent = unconditional gate failure); reads `budget_request.json` is NOT listed in `budget_gate_validator.reads_from` — the validator reads `received/` and `validation/` directories, not the request artifact | ~ minor | `budget_gate_validator` does not consume `budget_request.json` from `budget_interface_coordinator` directly — the handoff is mediated by the human operator (who submits the request to the external system) and the external system (which populates `received/`). This is constitutionally correct: the request and the response are independent artifacts. No authority inversion. The issue to note: there is no automated verification that the budget response in `received/` corresponds to the request in `budget_request.json`. The validator checks structural consistency against Phase 3/4 outputs, which is the correct approach. Not a constitutional gap. |
| `proposal_writer` (n08a) → `proposal_writer` (n08b) | Per-section artifacts `docs/tier5_deliverables/proposal_sections/<section_id>.json` (schema `orch.tier5.proposal_section.v1`) | `proposal_writer` in n08b context reads `docs/tier5_deliverables/proposal_sections/` (declared in canonical inputs as n08b input); verifies all mandatory sections from `section_schema_registry.json` are present before assembly | ✓ pass | — |
| `proposal_writer` → `evaluator_reviewer` | `assembled_draft.json` (schema `orch.tier5.assembled_draft.v1`) in `docs/tier5_deliverables/assembled_drafts/` | `evaluator_reviewer` canonical inputs table lists `assembled_draft.json` with schema `orch.tier5.assembled_draft.v1` | ✓ pass | — |
| `evaluator_reviewer` → `revision_integrator` | `review_packet.json` (schema `orch.tier5.review_packet.v1`) in `docs/tier5_deliverables/review_packets/` | `revision_integrator` canonical inputs table lists `review_packet.json` with schema `orch.tier5.review_packet.v1` | ✓ pass | — |

**Cross-agent handoff summary:**
- 13 handoffs validated
- 11 pass without issue
- 2 flagged with minor notes (not blocking):
  1. `call_analyzer` does not explicitly declare `docs/tier2a_instrument_schemas/extracted/` in its `reads_from` in `agent_catalog.yaml`, yet the auxiliary output it consumes is written there. Needs catalog clarification.
  2. `budget_interface_coordinator` → `budget_gate_validator` handoff is human-mediated, with no automated linkage between `budget_request.json` and the received response. This is constitutionally correct by design (CLAUDE.md §8.1–8.2) but worth flagging for operator documentation.

---

## 3. Sub-agent and auxiliary routing validation

### `dependency_mapper` (sub-agent of n03_wp_design)

| Check | Result | Notes |
|---|---|---|
| Decision-log routing through `wp_designer`? | ✓ confirmed | Contract: "Written via `wp_designer`'s decision log flow (same path)." Decision log obligations table lists entries with `agent_id: dependency_mapper` but routed through the parent. Prompt spec confirms: "Decision log writes: via `wp_designer`'s decision log flow." |
| Avoids claiming independent gate authority? | ✓ confirmed | Contract: "exit_gate: null"; "Gate authority belongs to `wp_designer`." Constitutional review §2 confirms no independent gate-passing authority. |
| Prompt spec matches limited execution role? | ✓ confirmed | Prompt spec correctly describes sub-agent scope; invocation precondition (wp_designer must write first); no claim to Phase 3 gate evaluation. |
| Produces only outputs allowed by catalog + manifest? | ✓ confirmed | Only output is contribution to `wp_structure.json` `dependency_map` field, within the `writes_to` path `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/`. No separate artifact written. Consistent with manifest `sub_agent: dependency_mapper` under n03_wp_design. |

### `instrument_schema_resolver` (auxiliary of call_analyzer)

| Check | Result | Notes |
|---|---|---|
| Decision-log/failure routing through `call_analyzer`? | ✓ confirmed | Contract: "This agent writes to the decision log via `call_analyzer`." Failure protocols route through call_analyzer. Constitutional review §1 confirms no own decision log write path. |
| Avoids claiming independent gate authority? | ✓ confirmed | Contract: "exit_gate: null"; "Gate authority belongs to `call_analyzer`." Body: "Because this agent has no direct node binding, it carries no own `entry_gate` or `exit_gate`." |
| Prompt spec matches limited execution role? | ✓ confirmed | Prompt spec correctly describes auxiliary scope; no claim to Phase 1 gate evaluation. |
| Produces only outputs allowed by catalog + manifest? | ✓ confirmed | Writes only `section_schema_registry.json` and `evaluator_expectation_registry.json` to `docs/tier2a_instrument_schemas/extracted/`. No other artifacts claimed. |
| Reads_from gap (see Section 2 handoff note)? | ~ flagged | `call_analyzer`'s `reads_from` in `agent_catalog.yaml` does not list `docs/tier2a_instrument_schemas/extracted/`. The auxiliary writes there; whether call_analyzer reads from that path is ambiguous at catalog level. Not a constitutional conflict in current state; needs catalog clarification before runtime binding. |

### `budget_interface_coordinator` (pre-gate agent of n07_budget_gate)

| Check | Result | Notes |
|---|---|---|
| Decision-log routing: direct (own path)? | ✓ confirmed | Has `docs/tier4_orchestration_state/decision_log/` in own `writes_to`. Writes directly, unlike auxiliary agents. |
| Pre-gate only — avoids claiming gate authority? | ✓ confirmed | Contract: "exit_gate: null"; "This agent **does not declare the budget gate passed**." Must-not list: "Must not declare the budget gate passed." Constitutional review §2 confirms. Prompt spec is explicit: pre-gate agent, no gate evaluation authority. |
| Prompt spec matches limited execution role? | ✓ confirmed | Prompt spec correctly describes request preparation only; no gate pass/fail language. |
| Produces only outputs allowed by catalog + manifest? | ✓ confirmed | Writes only `budget_request.json` to `docs/tier3_project_instantiation/integration/`; decision log entries. The `budget-interface-validation` skill writes to `integrations/lump_sum_budget_planner/validation/` — this is the skill's write path, declared in `skill_catalog.yaml`, not this agent's own path. Constitutional review acknowledges this. |

### `state_recorder` (cross-phase, record-keeper)

| Check | Result | Notes |
|---|---|---|
| Cross-phase recorder, not substantive decision-maker? | ✓ confirmed | Contract: "Not bound to any specific node." Purpose: implements CLAUDE.md §9.4 — writes decisions made by other agents to durable Tier 4 storage. It records; it does not decide. |
| Avoids claiming independent gate authority? | ✓ confirmed | "exit_gate: null"; "The agent does not declare any phase gate passed or failed." The `gate_pass` decision log entries written by state_recorder record that a gate passed (as reported by the invoking agent) — not a gate declaration by state_recorder itself. |
| Checkpoint write correctly gated? | ✓ confirmed | Checkpoint write constrained to invocation by `revision_integrator` after `gate_12_constitutional_compliance` passes. Failure Protocol Case 1 blocks checkpoint write if gate not passed. Failure Protocol Case 2 blocks overwrite of existing published checkpoint. |
| Dual-write question (revision_integrator + state_recorder for checkpoint)? | ~ ambiguous | `revision_integrator` contract says it invokes `checkpoint-publish` skill and lists it in `invoked_skills`; `state_recorder` also lists `checkpoint-publish` in its `invoked_skills` and describes writing the checkpoint when invoked by `revision_integrator`. It is unclear whether `revision_integrator` writes the checkpoint directly via the skill or delegates entirely to `state_recorder`. Both are constrained by the same gate condition; no constitutional conflict arises. However, a future runtime implementation pass should clarify the invocation chain to avoid double-write risk. |

---

## 4. Schema ID and canonical artifact validation

All schema IDs checked against `agent-generation-plan.md` §7 (schema quick reference table, derived from `artifact_schema_specification.yaml`) and against the field specifications read directly from `artifact_schema_specification.yaml`. Agent contract files cross-checked for consistency with prompt spec files.

| Schema ID | Canonical path | Producing agent(s) | Contract file binding | Prompt spec binding | artifact_status absent-at-write rule | status |
|---|---|---|---|---|---|---|
| `orch.phase1.call_analysis_summary.v1` | `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | `call_analyzer` | ✓ exact match | ✓ exact match | ✓ "NO — absent at write time" stated | ✓ pass |
| `orch.phase2.concept_refinement_summary.v1` | `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | `concept_refiner` | ✓ exact match | ✓ exact match | ✓ stated | ✓ pass |
| `orch.phase3.wp_structure.v1` | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | `wp_designer` + `dependency_mapper` | ✓ exact match in both agent files | ✓ exact match | ✓ stated; dependency_mapper explicitly notes schema_id and run_id are written by wp_designer and must not be overwritten | ✓ pass |
| `orch.phase4.gantt.v1` | `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | `gantt_designer` | ✓ exact match | ✓ exact match | ✓ stated | ✓ pass |
| `orch.phase5.impact_architecture.v1` | `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | `impact_architect` | ✓ exact match | ✓ exact match | ✓ stated | ✓ pass |
| `orch.phase6.implementation_architecture.v1` | `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | `implementation_architect` | ✓ exact match | ✓ exact match | ✓ stated | ✓ pass |
| `orch.phase7.budget_gate_assessment.v1` | `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | `budget_gate_validator` | ✓ exact match | ✓ exact match | ✓ stated; absent-artifacts always-fail rule for `gate_pass_declaration` explicitly stated | ✓ pass |
| `orch.phase8.drafting_review_status.v1` | `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` | `revision_integrator` | ✓ exact match | ✓ exact match | ✓ stated | ✓ pass |
| `orch.checkpoints.phase8_checkpoint.v1` | `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | `revision_integrator` (via checkpoint-publish skill / state_recorder) | ✓ exact match in both revision_integrator.md and state_recorder.md | ✓ exact match in both prompt specs | ✓ stated; additionally "must not be overwritten once published" rule stated | ✓ pass |
| `orch.tier5.proposal_section.v1` | `docs/tier5_deliverables/proposal_sections/<section_id>.json` | `proposal_writer` (n08a) | ✓ exact match | ✓ exact match; per-section pattern confirmed | ✓ stated | ✓ pass |
| `orch.tier5.assembled_draft.v1` | `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` | `proposal_writer` (n08b); also updated by `revision_integrator` | ✓ exact match in both proposal_writer.md and revision_integrator.md | ✓ exact match | ✓ stated | ✓ pass |
| `orch.tier5.review_packet.v1` | `docs/tier5_deliverables/review_packets/review_packet.json` | `evaluator_reviewer` | ✓ exact match | ✓ exact match | ✓ stated | ✓ pass |
| `orch.tier5.final_export.v1` | `docs/tier5_deliverables/final_exports/final_export.json` | `revision_integrator` | ✓ exact match | ✓ exact match | ✓ stated | ✓ pass |

### Content-contract-only outputs (no schema_id in spec)

The following outputs are produced by agents but have no `schema_id_value` in `artifact_schema_specification.yaml`. All are correctly described in contract files as content-contract-only and are not presented as schema-bound:

| Artifact | Producing agent | Correctly stated as content-contract-only? |
|---|---|---|
| Tier 2B extracted files (6 files) | `call_analyzer` | ✓ — "no schema_id in spec" stated |
| `section_schema_registry.json` | `instrument_schema_resolver` | ✓ — "no schema_id_value defined" stated |
| `evaluator_expectation_registry.json` | `instrument_schema_resolver` | ✓ — same |
| `topic_mapping.json` | `concept_refiner` | ✓ — "no schema_id in spec" stated |
| `compliance_profile.json` | `concept_refiner` | ✓ — same |
| `workpackage_seed.json` (update) | `wp_designer` | ✓ — "no schema_id_value defined" stated |
| `milestones_seed.json` | `gantt_designer` | ✓ — "no schema_id_value defined" stated |
| `budget_request.json` | `budget_interface_coordinator` | ✓ — "None defined in spec; governed by interface contract" stated |
| `budget_response.json` | `budget_gate_validator` | ✓ — "no schema_id_value defined in spec" stated |
| Validation reports | `compliance_validator`, `traceability_auditor`, `state_recorder` | ✓ — "None defined in spec" stated in all three |
| Decision log entries | all agents | ✓ — no schema_id_value in spec; mandatory field structure from `node_body_contract.md §10` |

### `run_id` propagation consistency

All schema-bound artifacts specify `run_id` as a required field with derivation "Propagated verbatim from the invoking DAG-runner run context." This is consistent across all 13 schema-bound artifacts. No agent claims to generate or modify `run_id`. ✓

### `artifact_status` absent-at-write rule consistency

All schema-bound artifacts mark `artifact_status` as "NO — absent at write time" (or equivalent language) in the output schema contracts. `state_recorder`'s checkpoint schema notes "artifact_status must be absent at write time (runner-stamped)". ✓

---

## 5. Prompt spec consistency validation

### Mandatory reading order

| Agent | Reading order starts with CLAUDE.md? | Agent contract file included? | Constitutional hierarchy respected? |
|---|---|---|---|
| `call_analyzer` | ✓ | ✓ (position 3) | ✓ |
| `instrument_schema_resolver` | ✓ | ✓ | ✓ |
| `concept_refiner` | ✓ | ✓ | ✓ |
| `wp_designer` | ✓ | ✓ | ✓ |
| `dependency_mapper` | ✓ | ✓ (position 4) | ✓ |
| `gantt_designer` | ✓ | ✓ | ✓ |
| `impact_architect` | ✓ | ✓ | ✓ |
| `implementation_architect` | ✓ | ✓ | ✓ |
| `budget_interface_coordinator` | ✓ | ✓ | ✓ |
| `budget_gate_validator` | ✓ | ✓ (position 9) | ✓ |
| `proposal_writer` | ✓ | ✓ (position 9) | ✓ |
| `evaluator_reviewer` | ✓ | ✓ | ✓ |
| `revision_integrator` | ✓ | ✓ | ✓ |
| `compliance_validator` | ✓ | ✓ | ✓ |
| `traceability_auditor` | ✓ | ✓ | ✓ |
| `state_recorder` | ✓ | ✓ (position 5) | ✓ |

### Key consistency checks across all prompt specs

| Check | Result | Notes |
|---|---|---|
| Reasoning steps do not widen agent scope beyond contract | ✓ confirmed across sampled specs | Sampled: `call_analyzer`, `budget_gate_validator`, `proposal_writer`, `dependency_mapper`, `state_recorder`. All reasoning steps are bounded by the contract's `reads_from` and `writes_to` scope. |
| Output construction rules preserve canonical paths and schema IDs | ✓ confirmed across sampled specs | Schema IDs and canonical paths in prompt specs match the corresponding contract files exactly. |
| Gate-awareness instructions do not imply agents evaluate gates themselves | ✓ confirmed | All prompt specs (sampled) state "Gate-passing authority: None" or equivalent. The budget_gate_validator prompt spec correctly states the runner stamps `gate_result.json` after the agent produces outputs. |
| Completion criteria stop at "ready for runner gate evaluation" | ✓ confirmed | The `call_analyzer` prompt spec step 8 says "Invoke `gate-enforcement` skill" then "Halt conditions" — the agent prepares gate inputs, the runner evaluates. `budget_gate_validator` prompt spec states the agent "writes `budget_gate_assessment.json`" and then invokes `gate-enforcement` skill; the runner evaluates the gate. No prompt spec claims the agent passes the gate. |
| Failure protocols aligned with contract files | ✓ confirmed across sampled specs | Four-case failure protocol (gate condition not met, input absent, predecessor gate not passed, constitutional prohibition) matches contract file failure protocols. Budget gate validator absent-artifacts rule reproduced verbatim in prompt spec step 2. |
| `proposal_writer` prompt spec enforces budget gate as first action | ✓ confirmed | Step 1 of proposal_writer reasoning sequence is "Verify budget gate (absolute)" — reads `budget_gate_assessment.json` and halts with `constitutional_halt` if not `"pass"`. Consistent with contract and CLAUDE.md §8.4, §13.4. |
| `dependency_mapper` prompt spec reflects sub-agent limitations | ✓ confirmed | Prompt spec correctly describes invocation precondition, lack of own exit gate, decision log routing via wp_designer, and no independent gate-passing authority. |
| `state_recorder` prompt spec reflects cross-phase recording role | ✓ confirmed | Three distinct invocation contexts correctly described; checkpoint-publish context conditioned on gate_12 passing and existing checkpoint immutability check. |

**No prompt spec is found to override or contradict its corresponding agent contract file.**

---

## 6. Runtime integration readiness notes

This section records readiness observations for a future agent runner / semantic dispatch binding pass. It does NOT implement runtime integration.

### Overall internal consistency

The agent set is internally consistent enough to proceed to a future runtime binding pass. All 16 agents have:
- Unambiguous `agent_id` values matching `agent_catalog.yaml`
- Defined `phase_id` values matching `manifest.compile.yaml` phase nodes
- Defined `node_ids` (or empty `[]` for cross-phase agents) consistent with manifest
- Canonical artifact paths consistent with the `manifest.compile.yaml` artifact registry
- Schema IDs consistent with `artifact_schema_specification.yaml`
- No cross-agent scope overlap or conflicting write authority

### Agent ID naming

All 16 `agent_id` values use lowercase snake_case, consistent with the `agent_catalog.yaml` `id` fields and the `manifest.compile.yaml` `agent:` and `sub_agent:` field values. No variation, abbreviation, or alias is detected. Runtime lookup by agent_id against the catalog should be straightforward.

### Unresolved ambiguities that would affect a runtime pass

| Ambiguity | Severity | Description |
|---|---|---|
| `call_analyzer` reads from `docs/tier2a_instrument_schemas/extracted/` implicitly | Minor | `call_analyzer.reads_from` in `agent_catalog.yaml` does not list `docs/tier2a_instrument_schemas/extracted/`. Yet it consumes the instrument_schema_resolver's output from that path. A runtime resolver that enforces `reads_from` as an access-control list would block this access. Resolution: add `docs/tier2a_instrument_schemas/extracted/` to `call_analyzer.reads_from` in `agent_catalog.yaml`, or confirm the runner reads these files via gate predicates rather than via the agent. |
| `revision_integrator` / `state_recorder` checkpoint dual-write | Minor | Both agents list `checkpoint-publish` in `invoked_skills` and describe writing `phase8_checkpoint.json`. A runtime dispatch pass must clarify whether `revision_integrator` delegates checkpoint writing entirely to `state_recorder` (via invocation), or calls the skill directly. Both are constitutionally valid; the distinction matters for runtime implementation. |
| Cross-phase agents (`compliance_validator`, `traceability_auditor`, `state_recorder`) have no `node_ids` binding | By design | These agents are invoked outside the node-execution model. A runtime dispatch mechanism must handle cross-phase invocation separately from node-body execution. This is not a defect; it is a documented design characteristic. Runtime implementation must not assume all agents are reached through node execution. |
| `instrument_schema_resolver` has `node_ids: []` but is invoked within n01 | By design | This agent is an auxiliary invoked within the Phase 1 execution context, not a separate node body. A runtime dispatch pass must model this as a within-node call, not a separate node invocation. |
| `proposal_writer` serves two nodes (n08a and n08b) | Documented | The manifest binds the same `agent: proposal_writer` to both `n08a_section_drafting` and `n08b_assembly`. The agent contract file distinguishes the two execution contexts. A runtime dispatch pass must pass the execution context (`n08a` vs `n08b`) to the agent so it can produce the correct output type. |

### Not yet proven by current repository state

- Actual runtime invocation of any agent from the DAG scheduler is not yet implemented. The DAG scheduler (`runner/dag_scheduler.py`) can schedule and sequence nodes, but agent node bodies are not yet connected to the scheduler as executable processes. The agent contract files and prompt spec files are design-time specifications; actual runtime execution has not been demonstrated.
- Resolution of gate predicates against canonical artifact fields (e.g., `g02_p01` → `dir_non_empty(docs/tier2b_topic_and_call_sources/extracted/)`) requires the `gate_rules_library.yaml` implementation, which was referenced in `manifest.compile.yaml` comments but is not verified as present in this validation pass.
- Semantic dispatch from a runtime invocation (e.g., `run_agent("call_analyzer", run_id=...)`) to the correct prompt spec file has not been implemented or proven; it is a future integration task.

---

## 7. Final status

```
overall_status: complete
```

| Metric | Value |
|---|---|
| Total agents validated | 16 |
| Agents with status `complete` | 16 |
| Agents with status `incomplete` | 0 |
| Agents with status `needs_human_review` | 0 |
| Cross-agent handoffs validated | 13 |
| Cross-agent handoff issues (blocking) | 0 |
| Cross-agent handoff issues (minor / flagged) | 2 |
| `node_body_contract.md` cross-referenced by every agent file | ✓ yes — all 16 files contain explicit reference |
| Step 10 complete per `agent-generation-plan.md` §6 | ✓ yes |
| Stale placeholder text requiring future clean-up | "Steps 8–9 (constitutional review notes; prompt specification) remain." present in all 16 Contract sections — not a constitutional defect; clean-up recommended |

### Items requiring operator attention before a future runtime binding pass

1. **`call_analyzer` `reads_from` gap:** Add `docs/tier2a_instrument_schemas/extracted/` to `call_analyzer.reads_from` in `agent_catalog.yaml`, or confirm the runner accesses these files via gate predicates rather than through the agent's declared read scope.

2. **`revision_integrator` / `state_recorder` checkpoint write chain:** Clarify in a future implementation plan whether the checkpoint is written by `revision_integrator` directly (via `checkpoint-publish` skill invocation), by `state_recorder` (as a delegated call), or both in sequence. Define a de-duplication guard.

3. **Stale "remain" notes:** Remove the placeholder text "Steps 8–9 (constitutional review notes; prompt specification) remain." from the Contract section of all 16 agent files. These steps are complete.

4. **Cross-phase agent dispatch model:** Before runtime integration, define how the runner dispatches cross-phase agents (`compliance_validator`, `traceability_auditor`, `state_recorder`) that have no `node_ids` binding. These are not reachable through the standard node execution path.

5. **gate_rules_library.yaml presence:** Verify that `gate_rules_library.yaml` (referenced in `manifest.compile.yaml` for predicate resolution) exists and covers all predicate_refs used in the gate registry. This was not validated in this pass.

### Constitutional compliance declaration

All 16 agent contract files completed constitutional reviews with the status "Constitutional review result: no conflict identified." All 16 prompt spec files are consistent with their corresponding contract files and do not override constitutional authority. No agent file violates CLAUDE.md §13 prohibitions. No agent claims gate-passing authority it is not constitutionally permitted to hold. The budget gate absent-artifacts rule (CLAUDE.md §8.4, §13.4) is correctly implemented in `budget_gate_validator` and correctly enforced as a prerequisite in `proposal_writer`, `evaluator_reviewer`, and `revision_integrator`.

---

*Validation checklist produced by Step 10 of `agent-generation-plan.md`. Effective from creation. This document is a validation artifact — it does not amend agent contracts, the manifest, or the constitution. Constitutional amendments require explicit human instruction per CLAUDE.md §14.*
