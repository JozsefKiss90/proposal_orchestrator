# Agent Generation Plan
## Horizon Europe Proposal Orchestration System — Agent Execution Layer

**Package:** `system_orchestration` v1.1
**Plan status:** Fully implemented — Steps 1–10 complete. 16 agent files + `node_body_contract.md` + 16 prompt specs + `validation_checklist.md` produced.
**Constitutional authority:** Subordinate to `CLAUDE.md`. This plan operationalizes; it does not override.

---

## 1. Mandatory Sources — Required Reading in Authority Order

No agent implementation may be generated, modified, or reviewed without first reading all of the following sources in the order listed. The order reflects the constitutional authority hierarchy (CLAUDE.md §3).

| Priority | File | Why Mandatory |
|----------|------|---------------|
| 1 | `CLAUDE.md` | Highest interpretive authority. Defines forbidden actions, tier model, phase sequence, gate semantics, and all constitutional prohibitions (§13). |
| 2 | `.claude/workflows/system_orchestration/manifest.compile.yaml` | Binding execution model: node registry, edge registry, gate registry, artifact registry. Defines every `node_id`, `agent`, `skills`, `entry_gate`, `exit_gate`, and `terminal` flag. |
| 3 | `.claude/workflows/system_orchestration/agent_catalog.yaml` | Declarative role descriptions, `reads_from`, `writes_to`, and `must_not` constraints for every agent. The authoritative source of agent scope. |
| 4 | `.claude/workflows/system_orchestration/artifact_schema_specification.yaml` | Field-level schemas for every canonical artifact. Defines `schema_id_value`, `canonical_path`, required fields, and `artifact_status` semantics. No output contract may be defined without reading the relevant schema here. |
| 5 | `.claude/workflows/system_orchestration/skill_catalog.yaml` | Skill definitions, purposes, `reads_from`, `writes_to`, and constitutional constraints. Required before binding skills to agents. |
| 6 | `.claude/workflows/system_orchestration/quality_gates.yaml` | Gate condition details. An agent must understand the gate it must satisfy before implementing the body that produces the gate's required outputs. |
| 7 | `CLAUDE.md` §7 | Phase definitions and gate conditions (re-read explicitly). Each phase's `required inputs`, `required outputs`, and `gate condition` directly bound agent canonical inputs and outputs. |

**Enforcement rule:** A generator that skips any of these sources and proceeds from memory violates CLAUDE.md §10.6 and §13.9. The resulting agent is constitutionally invalid and must not be used.

## 1.1 Mandatory Source Usage — Execution Rule

The sources listed in §1 are not a one-time reading step.

They must be actively referenced and re-consulted during EVERY implementation step.

Requirements:

- No step may rely on memory of a source without re-checking it when:
  - binding canonical inputs/outputs
  - assigning schema IDs
  - defining gate conditions
  - interpreting agent scope or constraints

- Whenever a step uses:
  - artifact paths → MUST re-check `manifest.compile.yaml`
  - schema fields → MUST re-check `artifact_schema_specification.yaml`
  - agent scope → MUST re-check `agent_catalog.yaml`
  - skill usage → MUST re-check `skill_catalog.yaml`
  - gate logic → MUST re-check `quality_gates.yaml`

- If a step proceeds without re-validating these sources, the result is invalid.


---

## 2. Objectives and Outputs of the Generation Process

### 2.1 Goal

Produce a complete, constitutionally compliant set of agent implementation files that the DAG scheduler can invoke as node body executors. Each file must implement exactly one agent from `agent_catalog.yaml`, scoped to the node(s) it serves in `manifest.compile.yaml`.

### 2.2 Output Artifacts

The generation process produces the following file sets:

#### A. Agent definition files — `.claude/agents/<agent_id>.md`
One Markdown file per agent. Contains the agent's YAML front matter (role, scope, inputs, outputs, skills, gate awareness, constraints) and a structured body prompt that the Claude Code agent runtime executes.

**Required front matter fields (YAML block at top of file):**
```yaml
---
agent_id: <id from agent_catalog.yaml>
phase_id: <phase_id from manifest.compile.yaml>
node_ids: [<list of node_ids this agent serves>]
role_summary: <one sentence>
constitutional_scope: <from agent_catalog.yaml>
reads_from: [<canonical input paths>]
writes_to: [<canonical output paths>]
invoked_skills: [<skill ids from skill_catalog.yaml>]
entry_gate: <gate_id or null>
exit_gate: <gate_id>
---
```

#### B. Prompt specification files — `.claude/agents/prompts/<agent_id>_prompt_spec.md`
For each agent, a structured natural-language prompt specification that defines: reading instructions, reasoning steps, output construction rules, traceability obligations, and failure declaration protocol. This is the generator's input to the agent body; it is not the agent file itself.

#### C. Node-body contract document — `.claude/agents/node_body_contract.md`
A single shared contract document (see §3) that all agent files must conform to. Defines the standard obligations that apply to every agent body regardless of phase.

#### D. Agent execution wrappers (if runtime requires)
If the Claude Code agent runner requires a wrapper script to pass the correct `reads_from` paths and `run_id` to the agent at invocation time, a corresponding wrapper is generated as `.claude/agents/wrappers/<agent_id>_wrapper.sh` or `.py`. Wrappers are execution aids only; they do not alter agent scope or constitutional obligations.

### 2.3 What the Generation Process Does NOT Produce
- Budget computation logic (prohibited by CLAUDE.md §8.1)
- New artifact paths not defined in `manifest.compile.yaml` or `artifact_schema_specification.yaml`
- New phase definitions or gate conditions
- Any file that modifies `manifest.compile.yaml`, `CLAUDE.md`, or `artifact_schema_specification.yaml`

---

## 3. Node-Body Contract — Minimum Requirements for Every Agent Implementation

Every `.claude/agents/<agent_id>.md` file must satisfy the following contract. This is the generation unit specification.

### 3.1 Agent Identity
| Field | Requirement |
|-------|-------------|
| `agent_id` | Must exactly match the `id` field in `agent_catalog.yaml` |
| `role_summary` | ≤ 2 sentences; must not expand the scope defined in `agent_catalog.yaml` |
| `constitutional_scope` | Must match `constitutional_scope` from `agent_catalog.yaml`; may not be widened |

### 3.2 Allowed Scope
The agent may only read from paths listed in its `reads_from` in `agent_catalog.yaml` and write to paths listed in its `writes_to`. It may not access any path outside these declared lists. Cross-phase reads require explicit listing in `agent_catalog.yaml`.

### 3.3 Must-Not Constraints
The agent body must include an explicit enumeration of all `must_not` entries from `agent_catalog.yaml` as hard-coded refusal conditions. A `must_not` constraint is never advisory; the agent must refuse or halt if the constraint would be violated.

Additional universal must-not constraints (apply to every agent regardless of catalog entry):
- Must not fabricate project facts not present in Tier 3
- Must not invent call constraints not present in Tier 2B source documents
- Must not declare a gate passed without confirming every gate condition is satisfied
- Must not proceed if the predecessor gate condition for its phase has not passed
- Must not store a decision in agent memory without writing it to `docs/tier4_orchestration_state/decision_log/`
- Must not produce outputs that are not traceable to named Tier 1–4 sources

### 3.4 Canonical Inputs
The agent body must explicitly list every input artifact it reads, including:
- The canonical artifact path
- The schema ID (from `artifact_schema_specification.yaml`) it expects
- What it extracts from each artifact and for what purpose

Inputs must be verified as present and non-empty before the agent proceeds. Absent mandatory inputs trigger a declared failure, not substitution.

### 3.5 Canonical Outputs
The agent body must explicitly list every artifact it produces, including:
- The canonical artifact path
- The schema ID the artifact must carry
- All required fields and their derivation source
- The `run_id` field (carried from the invoking run context)

### 3.6 Expected Artifact Schemas
For every output artifact:
- The `schema_id` field must be set to the `schema_id_value` from `artifact_schema_specification.yaml`
- All `required: true` fields must be populated
- The `artifact_status` field must be left absent at write time (the runner stamps it after gate evaluation)

### 3.7 Invoked Skills
The agent must list all skills from `skill_catalog.yaml` that it invokes, in the order it invokes them. For each skill:
- State the trigger condition (when it is invoked)
- State what input it receives
- State what output or side-effect it produces

Skills may not be invoked for purposes outside their `purpose` definition in `skill_catalog.yaml`.

### 3.8 Gate Awareness
The agent must explicitly state:
- Which gate it must satisfy (its `exit_gate` from the manifest)
- Which gate(s) it requires to have already passed (predecessor gates)
- What constitutes a gate pass vs. gate failure for its exit gate
- That it will write the gate result to the canonical path in `GATE_RESULT_PATHS`

For `gate_09_budget_consistency` (Phase 7 exit gate): the agent must include explicit handling for the absent-artifacts-always-fail rule (CLAUDE.md §8.4, manifest `absent_artifacts_behavior: blocking_gate_failure`).

### 3.9 Failure Behaviour
The agent must implement the following failure protocol:
1. **Gate condition not met:** Write a gate failure report to the canonical Tier 4 phase output path. Include which conditions failed and why. Do not proceed downstream. Do not fabricate completion.
2. **Required input absent:** Declare a blocked state. Write the missing input to the decision log. Do not substitute, infer, or hallucinate the missing content.
3. **Mandatory predecessor gate not passed:** Halt immediately. Write a constitutional violation note to the decision log.
4. **Constitutional prohibition triggered:** Halt immediately. Do not produce partial output. Write the triggered prohibition to the decision log.

### 3.10 Decision-Log Obligations
The agent must write a decision log entry for:
- Every material decision made during execution (not just failures)
- Every assumption adopted where source data was absent or ambiguous
- Every scope conflict or inconsistency between tiers
- Every gate pass or gate failure it declares

Decision log entries must include: `agent_id`, `phase_id`, `run_id`, `timestamp`, `decision_type` (one of: material_decision / assumption / scope_conflict / gate_pass / gate_failure / constitutional_halt), and a `rationale` field with source references.

---

## 4. Node-to-Agent Mapping Table

Derived from `manifest.compile.yaml`, `agent_catalog.yaml`, and `artifact_schema_specification.yaml`. This table is the authoritative binding for the generation process.

| `node_id` | `phase_id` | `agent` | `skills` | Required Output (canonical artifact) | Target Schema ID |
|-----------|------------|---------|----------|--------------------------------------|-----------------|
| `n01_call_analysis` | `phase_01_call_analysis` | `call_analyzer` + `instrument_schema_resolver` | `call-requirements-extraction`, `evaluation-matrix-builder`, `instrument-schema-normalization`, `topic-scope-check`, `gate-enforcement` | `phase1_call_analysis/call_analysis_summary.json` | `orch.phase1.call_analysis_summary.v1` |
| `n02_concept_refinement` | `phase_02_concept_refinement` | `concept_refiner` | `concept-alignment-check`, `topic-scope-check`, `proposal-section-traceability-check`, `decision-log-update` | `phase2_concept_refinement/concept_refinement_summary.json` | `orch.phase2.concept_refinement_summary.v1` |
| `n03_wp_design` | `phase_03_wp_design_and_dependency_mapping` | `wp_designer` (primary), `dependency_mapper` (sub-agent) | `work-package-normalization`, `wp-dependency-analysis`, `milestone-consistency-check`, `instrument-schema-normalization`, `gate-enforcement` | `phase3_wp_design/wp_structure.json` | `orch.phase3.wp_structure.v1` |
| `n04_gantt_milestones` | `phase_04_gantt_and_milestones` | `gantt_designer` | `milestone-consistency-check`, `gate-enforcement`, `decision-log-update` | `phase4_gantt_milestones/gantt.json` | `orch.phase4.gantt.v1` |
| `n05_impact_architecture` | `phase_05_impact_architecture` | `impact_architect` | `impact-pathway-mapper`, `dissemination-exploitation-communication-check`, `proposal-section-traceability-check`, `gate-enforcement` | `phase5_impact_architecture/impact_architecture.json` | `orch.phase5.impact_architecture.v1` |
| `n06_implementation_architecture` | `phase_06_implementation_architecture` | `implementation_architect` | `governance-model-builder`, `risk-register-builder`, `milestone-consistency-check`, `constitutional-compliance-check`, `gate-enforcement` | `phase6_implementation_architecture/implementation_architecture.json` | `orch.phase6.implementation_architecture.v1` |
| `n07_budget_gate` | `phase_07_budget_gate` | `budget_gate_validator` (primary), `budget_interface_coordinator` (pre-gate) | `budget-interface-validation`, `gate-enforcement`, `decision-log-update`, `constitutional-compliance-check` | `phase7_budget_gate/budget_gate_assessment.json` | `orch.phase7.budget_gate_assessment.v1` |
| `n08a_section_drafting` | `phase_08a_section_drafting` | `proposal_writer` | `proposal-section-traceability-check`, `evaluator-criteria-review`, `constitutional-compliance-check` | `tier5_deliverables/proposal_sections/<section_id>.json` | `orch.tier5.proposal_section.v1` (per section) |
| `n08b_assembly` | `phase_08b_assembly` | `proposal_writer` | `proposal-section-traceability-check`, `constitutional-compliance-check` | `tier5_deliverables/assembled_drafts/assembled_draft.json` | `orch.tier5.assembled_draft.v1` |
| `n08c_evaluator_review` | `phase_08c_evaluator_review` | `evaluator_reviewer` | `evaluator-criteria-review`, `proposal-section-traceability-check`, `constitutional-compliance-check` | `tier5_deliverables/review_packets/review_packet.json` | `orch.tier5.review_packet.v1` |
| `n08d_revision` | `phase_08d_revision` | `revision_integrator` | `proposal-section-traceability-check`, `evaluator-criteria-review`, `constitutional-compliance-check`, `decision-log-update`, `checkpoint-publish` | `tier5_deliverables/final_exports/final_export.json` + `checkpoints/phase8_checkpoint.json` | `orch.tier5.final_export.v1` + `orch.checkpoints.phase8_checkpoint.v1` |

**Cross-phase agents** (not mapped to a single node; invocable at any phase gate):

| `agent_id` | Invocation scope | Primary output path |
|------------|-----------------|---------------------|
| `compliance_validator` | Any gate; especially gates 10–12 | `tier4_orchestration_state/validation_reports/` |
| `traceability_auditor` | Any gate; especially on assembled drafts | `tier4_orchestration_state/validation_reports/` |
| `state_recorder` | Any agent at any decision point | `tier4_orchestration_state/decision_log/`, `checkpoints/` |

### 4.1 Additional Output Bindings (non-primary)

| `node_id` | Additional outputs | Paths |
|-----------|-------------------|-------|
| `n01_call_analysis` | 6 Tier 2B extracted files + 2 Tier 2A extracted files | `docs/tier2b_topic_and_call_sources/extracted/{call_constraints, expected_outcomes, expected_impacts, scope_requirements, eligibility_conditions, evaluation_priority_weights}.json`; `docs/tier2a_instrument_schemas/extracted/{section_schema_registry, evaluator_expectation_registry}.json` |
| `n02_concept_refinement` | 2 Tier 3 binding artifacts | `docs/tier3_project_instantiation/call_binding/topic_mapping.json`; `docs/tier3_project_instantiation/call_binding/compliance_profile.json` |
| `n04_gantt_milestones` | 1 Tier 3 updated artifact | `docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json` |
| `n07_budget_gate` (pre-gate) | Budget request (pre-gate coordinator) | `docs/tier3_project_instantiation/integration/budget_request.json` |
| `n07_budget_gate` (validator) | Budget response record | `docs/tier3_project_instantiation/integration/budget_response.json` |
| `n08d_revision` | Phase 8 Tier 4 status | `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` (schema: `orch.phase8.drafting_review_status.v1`) |

---

## 5. Non-Goals

The following are explicitly outside the scope of this generation plan. No generated agent file, wrapper, or prompt spec may implement or imply any of these.

**5.1 No parallel orchestration.**
The DAG scheduler is synchronous and single-threaded. Agents must not implement parallel dispatch, concurrent tool calls across node boundaries, or asynchronous gate evaluation. This constraint is structural, not temporary.

**5.2 Do not modify the scheduler contract.**
Agent files have no authority over `runner/dag_scheduler.py`, `manifest.compile.yaml`, or any scheduler runtime behavior. The scheduler calls agents; agents do not call or configure the scheduler. Any change to the scheduler contract requires a separate plan and explicit human instruction.

**5.3 Do not write a budget computer.**
Budget computation is the exclusive responsibility of the external Lump Sum Budget Planner. No agent may generate, estimate, approximate, or invent budget figures. The `budget_interface_coordinator` prepares requests; it does not compute anything. The `budget_gate_validator` validates structural consistency; it does not compute anything. CLAUDE.md §8.1–8.5 governs this without exception.

**5.4 Do not invent new artifact paths.**
All canonical artifact paths are defined in `manifest.compile.yaml` (artifact registry) and `artifact_schema_specification.yaml`. Agents must not write to any path not listed in their `writes_to` in `agent_catalog.yaml`. A new artifact path requires an amendment to both `manifest.compile.yaml` and `artifact_schema_specification.yaml` before it may be introduced.

**5.5 Do not override the constitutional hierarchy.**
No agent file may redefine a phase boundary, weaken a gate condition, reinterpret a tier meaning, or supersede a constitutional prohibition from CLAUDE.md. Agent scope is always subordinate to CLAUDE.md. If a generated agent file appears to relax a constitutional rule, the file is constitutionally invalid.

**5.6 Do not generate Phase 8 agents before the budget gate architecture is confirmed.**
Phase 8 agents (`proposal_writer` for n08a/n08b, `evaluator_reviewer` for n08c, `revision_integrator` for n08d) depend on `gate_09_budget_consistency` having passed. Their generation may proceed structurally, but any prompt spec that assumes a budget-confirmed state must explicitly verify Phase 7 gate passage as its first step.

---

## 6. Implementation Sequence

Execute the steps in order. Do not begin a step before all prior steps are complete. No step may be skipped.

### Step 1 — Initialize generation context ✓ Implemented
Confirm all mandatory sources (§1) are available and readable.
Do not assume prior reading persists across steps.

### Step 2 — Scaffold all agent files ✓ Implemented
Create an empty (front-matter-only) `.claude/agents/<agent_id>.md` for each agent in the mapping table (§4), including cross-phase agents. Use the front matter schema from §2.2A. At this stage, the body may be a placeholder. Target: 14 agent files + the `node_body_contract.md`.

**Agent file list:**
```
.claude/agents/call_analyzer.md
.claude/agents/instrument_schema_resolver.md
.claude/agents/concept_refiner.md
.claude/agents/wp_designer.md
.claude/agents/dependency_mapper.md
.claude/agents/gantt_designer.md
.claude/agents/impact_architect.md
.claude/agents/implementation_architect.md
.claude/agents/budget_interface_coordinator.md
.claude/agents/budget_gate_validator.md
.claude/agents/proposal_writer.md
.claude/agents/evaluator_reviewer.md
.claude/agents/revision_integrator.md
.claude/agents/compliance_validator.md
.claude/agents/traceability_auditor.md
.claude/agents/state_recorder.md
.claude/agents/node_body_contract.md
```

### Step 3 — Fill in standard front matter for each agent ✓ Implemented
For each scaffolded file, populate all front matter fields from §2.2A using `manifest.compile.yaml` and `agent_catalog.yaml` as the exclusive sources. Verify:
- `agent_id` matches `agent_catalog.yaml` exactly
- `node_ids` matches the manifest `agent` field for each node
- `reads_from` and `writes_to` match `agent_catalog.yaml` exactly
- `exit_gate` matches the manifest `exit_gate` for the node(s) served

### Step 4 — Bind skills ✓ Implemented
For each agent, add the `invoked_skills` list populated from `manifest.compile.yaml` `skills` field for the corresponding node(s). For each skill:
- Read its entry in `skill_catalog.yaml`
- Add a one-line description of trigger condition and expected output
- Confirm the skill's `constitutional_constraints` are reflected in the agent's `must_not` section

### Step 5 — Bind canonical inputs and outputs ✓ Implemented
For each agent:
- Populate `canonical_inputs` from `agent_catalog.yaml` `reads_from`, cross-referenced against the `artifact_registry` in `manifest.compile.yaml`
- Populate `canonical_outputs` from `agent_catalog.yaml` `writes_to`, cross-referenced against the `artifact_registry`
- For each canonical output, record its `schema_id_value` from `artifact_schema_specification.yaml`

### Step 6 — Align with artifact schemas ✓ Implemented
For each canonical output:
- Read the full field specification in `artifact_schema_specification.yaml` for the relevant schema
- Add a field-level output spec to the agent body covering all `required: true` fields
- Confirm `run_id` inheritance and `schema_id` stamping are implemented
- Confirm `artifact_status` is left absent at write time (runner-stamped post-gate)

### Step 7 — Implement gate awareness and failure behaviour ✓ Implemented
For each agent:
- Add explicit predecessor gate verification logic (§3.8)
- Add the failure protocol from §3.9 as named handling cases
- Add the decision-log obligations from §3.10 as explicit write steps
- For `budget_gate_validator`: add the absent-artifacts-always-fail rule as an unconditional branch

### Step 8 — Review for constitutional conflicts ✓ Implemented
For each completed agent file:
- Re-read CLAUDE.md §13 (Forbidden Actions and Anti-Patterns)
- Confirm no generated agent violates any prohibition
- Confirm no `writes_to` path is outside the agent's catalog-declared scope
- Confirm no `must_not` from the catalog has been softened or omitted
- Flag any conflict for human review; do not silently resolve

### Step 9 — Write prompt specification files ✓ Implemented
For each agent, produce the corresponding `prompts/<agent_id>_prompt_spec.md`:
- Reading instructions (which files to read, in what order)
- Reasoning steps (how to derive outputs from inputs)
- Output construction rules (field-by-field for canonical artifacts)
- Traceability footer requirements (Confirmed/Inferred/Assumed/Unresolved)
- Failure declaration protocol (verbatim steps from §3.9)

### Step 10 — Add a validation checklist ✓ Implemented
After all agent files and prompt specs are complete, create `.claude/agents/validation_checklist.md` containing:
- A row per agent confirming: front matter complete, skills bound, canonical I/O specified, schemas aligned, gate awareness implemented, failure protocol implemented, constitutional review passed, prompt spec written
- For each agent marked incomplete, a specific gap description
- A final row confirming `node_body_contract.md` is cross-referenced by every agent file

---

## 7. Artifact Schema Quick Reference

| Phase | Canonical artifact | Schema ID | Producing agent |
|-------|--------------------|-----------|-----------------|
| 1 | `phase1_call_analysis/call_analysis_summary.json` | `orch.phase1.call_analysis_summary.v1` | `call_analyzer` |
| 2 | `phase2_concept_refinement/concept_refinement_summary.json` | `orch.phase2.concept_refinement_summary.v1` | `concept_refiner` |
| 3 | `phase3_wp_design/wp_structure.json` | `orch.phase3.wp_structure.v1` | `wp_designer` + `dependency_mapper` |
| 4 | `phase4_gantt_milestones/gantt.json` | `orch.phase4.gantt.v1` | `gantt_designer` |
| 5 | `phase5_impact_architecture/impact_architecture.json` | `orch.phase5.impact_architecture.v1` | `impact_architect` |
| 6 | `phase6_implementation_architecture/implementation_architecture.json` | `orch.phase6.implementation_architecture.v1` | `implementation_architect` |
| 7 | `phase7_budget_gate/budget_gate_assessment.json` | `orch.phase7.budget_gate_assessment.v1` | `budget_gate_validator` |
| 8 (status) | `phase8_drafting_review/drafting_review_status.json` | `orch.phase8.drafting_review_status.v1` | `revision_integrator` |
| 8 (draft) | `tier5_deliverables/assembled_drafts/assembled_draft.json` | `orch.tier5.assembled_draft.v1` | `proposal_writer` |
| 8 (review) | `tier5_deliverables/review_packets/review_packet.json` | `orch.tier5.review_packet.v1` | `evaluator_reviewer` |
| 8 (export) | `tier5_deliverables/final_exports/final_export.json` | `orch.tier5.final_export.v1` | `revision_integrator` |
| 8 (checkpoint) | `checkpoints/phase8_checkpoint.json` | `orch.checkpoints.phase8_checkpoint.v1` | `revision_integrator` |
| per-section | `tier5_deliverables/proposal_sections/<id>.json` | `orch.tier5.proposal_section.v1` | `proposal_writer` |

All paths above are relative to `docs/tier4_orchestration_state/` for Tier 4 artifacts and to `docs/` for Tier 5 artifacts. See `manifest.compile.yaml` artifact_registry for exact paths.

---

## 8. DAG Execution Context for Agent Implementors

Agents are invoked as node body executors by the DAG scheduler. The following runtime facts govern every agent implementation:

- **The scheduler is synchronous.** At most one node body runs at a time. There is no concurrency to coordinate.
- **`run_id` is passed to the agent at invocation.** It must be propagated to every artifact the agent writes (as the `run_id` field in canonical JSON artifacts).
- **The scheduler evaluates gates; agents produce gate inputs.** An agent's job is to write the artifacts that gate predicates evaluate. The agent does not call `evaluate_gate()` itself.
- **`artifact_status` is runner-managed.** Agents must not set this field. After the agent completes, the scheduler calls `evaluate_gate()`. If the gate passes, the runner stamps `artifact_status: valid`; if it fails, `artifact_status: invalid`.
- **Gate failure is a correct output.** An agent that declares a gate condition unmet and writes a failure report has done its job correctly. It must not attempt to satisfy the gate through fabrication.
- **The DAG scheduler reads `run_summary.json` for orchestration state.** Agents must not write to this file. Its path and schema are owned by `runner/dag_scheduler.py`.

*Agent generation plan. Effective from creation. Implementation complete 2026-04-09. Amendments require explicit human instruction. No amendment may widen agent scope, weaken gate conditions, or relax any constitutional prohibition.*
