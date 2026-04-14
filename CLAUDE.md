# CLAUDE.md — Repository Constitution
## Horizon Europe Proposal Orchestration System

---

## 1. Purpose and Constitutional Status

This document is the constitution of the repository. It governs how the repository is interpreted, how orchestration behaves, how state progresses, and what changes are admissible. It is not a user guide, not an implementation tutorial, and not a workflow specification.

`CLAUDE.md` is the highest-priority interpretive authority in the repository, ranking above all prompts, skills, workflows, checklists, agent instructions, and local heuristics. The sole exception is an explicit, in-session human instruction that consciously and directly overrides a named constitutional rule. Such overrides apply only for the scope of the instruction that invokes them. They do not amend this constitution.

Every agent, skill, workflow, and automated process operating in this repository must read and comply with this constitution before taking action.

---

## 2. Repository Mission

This repository is a universal orchestration engine for the preparation of Horizon Europe-style research and innovation proposals.

Its mission is to transform a structured combination of normative rules, instrument schemas, topic and call sources, and project-specific instantiation data into evaluator-oriented, programme-compliant proposal deliverables.

The system is programme-agnostic and project-agnostic by default. It acquires call-specificity when Tier 2B is populated with active topic and work programme sources. It acquires project-specificity when Tier 3 is populated with project instantiation data. Neither specificity may be assumed or fabricated in the absence of that population.

The optimisation target of this system is evaluation success under the applicable Horizon Europe evaluation criteria. It is not grant-preparation formatting, grant agreement annex compliance, or financial reporting readiness. Proposal writing serves the evaluator, not the grant officer.

---

## 3. Authority Hierarchy

The following hierarchy governs all interpretive conflicts. A lower layer may operationalize a higher layer. No lower layer may override, redefine, or silently contradict a higher layer.

| Priority | Authority |
|----------|-----------|
| 1 | Explicit human instruction for the current task (in-session, named override only) |
| 2 | This constitution (`CLAUDE.md`) |
| 3 | Tier 1 — Normative framework (legislation, programme guidance, grant architecture) |
| 4 | Tier 2A — Instrument schemas (application forms, evaluation forms) |
| 5 | Tier 2B — Topic and call sources (work programmes, call extracts) |
| 6 | Tier 3 — Project instantiation (brief, consortium, call binding, architecture inputs) |
| 7 | Tier 4 — Orchestration state (phase outputs, decision log, checkpoints) |
| 8 | `.claude/workflows/` — Workflow definitions |
| 9 | `.claude/skills/` — Skill definitions |
| 10 | Agent-local memory, caches, and runtime state |

When a conflict exists between tiers and cannot be resolved by subordination, it must be logged as an unresolved conflict in `docs/tier4_orchestration_state/decision_log/` and surfaced to the human operator. It must not be silently resolved by a lower-priority authority.

---

## 4. Repository Ontology

The repository contains seven categories of artifact:

**Rules** — Normative constraints derived from legislation, programme guidance, and grant architecture documents. Rules are extracted into Tier 1 `extracted/` JSON files and govern compliance checking throughout the workflow.

**Structure** — Instrument schemas defining the sections, fields, page limits, and evaluation logic of application and evaluation forms. Structure is extracted into Tier 2A `extracted/` JSON files.

**Context** — Topic-specific and call-specific constraints, expected outcomes, expected impacts, eligibility conditions, and evaluation weighting. Context is extracted into Tier 2B `extracted/` JSON files from active work programme and call extract sources.

**Project data** — Project-specific facts: the identified call, consortium composition, capabilities, roles, objectives, outcomes, impacts, work package seeds, risk register, and milestone seeds. Project data lives in Tier 3 and is the sole authoritative source for project-specific claims in deliverables.

**Orchestration state** — The record of what the workflow has done, decided, and validated. This includes phase outputs, the decision log, checkpoints, and validation reports. Orchestration state lives in Tier 4.

**Deliverables** — Evaluator-oriented proposal sections, assembled drafts, final exports, and review packets. Deliverables live in Tier 5.

**Runtime execution memory** — Agent working memory, caches, logs, and run records. These are operational artifacts that support execution but are not constitutional source truth. Runtime execution memory lives in `.claude/`.

---

## 5. Tier Model

### Tier 1 — Normative Framework (`docs/tier1_normative_framework/`)

Contains: Primary legislation, framework programme regulation, specific programme decision, EU Financial Regulation; programme guidance including the Programme Guide, General Annexes, and Annotated Grant Agreement; grant architecture documents including Model Grant Agreements and the Framework Partnership Agreement.

Purpose: Establishes the non-negotiable legal and regulatory rules within which all proposals must operate.

Constraints: Documents in Tier 1 are source materials only. They are read to extract rules, compliance principles, participation conditions, and implementation constraints into the `extracted/` subdirectory. Tier 1 must not be modified to reflect project assumptions. Tier 1 `extracted/` files must be populated from the source documents, not authored from memory.

### Tier 2A — Instrument Schemas (`docs/tier2a_instrument_schemas/`)

Contains: Application form templates for all active Horizon Europe instruments (RIA/IA, CSA, MSCA, COFUND, ERC, EIC); evaluation form templates for those instruments; and extracted registries covering instrument definitions, section schemas, evaluator expectation patterns, and template adapter mappings.

Purpose: Defines the structural and evaluative constraints of the specific instrument type selected for the proposal. Application form templates define what must be addressed and in what form. Evaluation form templates define how evaluators will assess the submission.

Constraints: Tier 2A schemas are structural authorities for the selected instrument. They define what sections exist, what evaluators read, and what the proposal must deliver. They are not grant agreement annexes. The Grant Agreement Annex templates govern post-award reporting, not pre-award proposal writing. Using grant agreement annex structure as a proposal schema is a constitutional violation.

### Tier 2B — Topic and Call Sources (`docs/tier2b_topic_and_call_sources/`)

Contains: Work programme documents for all active Horizon Europe clusters, MSCA, ERC, research infrastructures, missions, widening, and ecosystems; call extracts for specific topics; and extracted JSON files covering call constraints, eligibility conditions, expected outcomes, expected impacts, scope requirements, and evaluation priority weights.

Purpose: Defines the call- and topic-specific constraints, vocabulary, and evaluation priorities that must be reflected in the proposal. Tier 2B is the source of the proposal's thematic framing, expected impact narrative, and scope boundaries.

Constraints: All call constraints, topic scope requirements, expected outcomes, and expected impacts used in the proposal must be traceable to Tier 2B source documents. No agent may invent or infer call constraints that are not present in Tier 2B. When Tier 2B `extracted/` files are populated, they must faithfully represent the source work programme and call documents, not paraphrase them speculatively.

### Tier 3 — Project Instantiation (`docs/tier3_project_instantiation/`)

Contains: Project brief (concept note, project summary, strategic positioning); consortium data (partners, capabilities, roles, evidence of competence); call binding (selected call, topic mapping, compliance profile); architecture inputs (objectives, outcomes, impacts, work package seed, risks, milestones seed); source materials (concept documents, partner inputs, prior proposals, reference materials); and integration artifacts for external system coordination.

Purpose: Makes the system project-specific. When Tier 3 is populated, the orchestration engine operates on a specific project targeting a specific call. When Tier 3 is empty or partially populated, the system remains generic or partially constrained.

Constraints: All project-specific facts in deliverables must be traceable to Tier 3 data. No agent may fabricate project facts (partner names, capabilities, objectives, roles, prior work, budget figures) that are not present in Tier 3. Partial population is permissible but must be explicitly acknowledged in orchestration state and flagged in deliverables. Tier 3 population does not automatically trigger workflow execution; workflow phases must be invoked explicitly.

### Tier 4 — Orchestration State (`docs/tier4_orchestration_state/`)

Contains: Phase outputs (one subdirectory per canonical workflow phase); decision log; checkpoints; and validation reports.

Purpose: Records the durable outputs of each workflow phase and the decisions made during orchestration. Tier 4 is the authoritative record of what the workflow has produced and why.

Constraints: Every canonical phase must produce its outputs to Tier 4 before downstream phases may depend on them. Agent memory alone does not constitute Tier 4 state. If a decision matters for future interpretation, it must be written to the decision log or a phase output, not held only in agent memory. Tier 4 may be updated by reruns, but prior checkpoint states must be preserved when a checkpoint has been formally validated.

### Tier 5 — Deliverables (`docs/tier5_deliverables/`)

Contains: Proposal sections, assembled drafts, final exports, and review packets.

Purpose: Contains the evaluator-facing proposal output.

Constraints: All Tier 5 content must be derivable from Tier 1–4 state. Tier 5 deliverables must not introduce claims, facts, figures, or framings that are not grounded in a higher tier. Tier 5 is the output layer; it is not an input layer for orchestration reasoning.

### Integrations (`docs/integrations/`)

Contains: The Lump Sum Budget Planner integration, comprising the interface contract, request templates, received responses, and validation artifacts.

Purpose: Mediates the exchange of budget computation data between this repository and the external Lump Sum Budget Planner system.

Constraints: This repository does not perform lump-sum budget computation. The integration directory is the exclusive channel for budget data exchange. Budget data that has not been received through the `received/` subdirectory and validated through `validation/` may not be used as the basis for finalized proposal content. The interface contract governs the structure of requests and responses.

---

## 6. Workflow Execution Model

The system operates through a sequence of canonical phases, each of which is gate-controlled. The following execution rules are unconditional:

1. **Phases are ordered.** The canonical phase sequence must not be silently reordered or skipped.
2. **Gates are mandatory.** Each phase has a gate condition. A phase is not complete until its gate condition is satisfied. A downstream phase must not begin if the gate condition of any upstream phase has not been met.
3. **Outputs are durable.** Phase outputs must be written to `docs/tier4_orchestration_state/phase_outputs/` before they are consumed by downstream phases. In-memory outputs that have not been written to Tier 4 do not satisfy gate conditions.
4. **Reruns are deterministic.** When a phase is rerun, it must update Tier 4 state deterministically from its inputs. It must not silently produce a different output by relying on in-memory state from a prior run.
5. **Gaps must be declared.** If a phase cannot complete because required inputs are absent, the system must declare a gate failure and halt. It must not fabricate completion.

---

## 7. Phase Definitions and Gate Conditions

### Phase 1 — Call Analysis

**Purpose:** Parse the selected work programme and call topic to extract the evaluation criteria, expected outcomes, expected impacts, scope requirements, eligibility conditions, and evaluation priority weights applicable to the selected topic.

**Required inputs:** Populated `docs/tier2b_topic_and_call_sources/` for the relevant work programme; `docs/tier3_project_instantiation/call_binding/selected_call.json` identifying the target topic.

**Required outputs:** Populated `docs/tier2b_topic_and_call_sources/extracted/` JSON files; phase output summary in `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/`.

**Gate condition:** All six Tier 2B extracted files are non-empty and traceable to identified source sections in the work programme. `selected_call.json` is confirmed populated and consistent with Tier 2B source.

---

### Phase 2 — Concept Refinement

**Purpose:** Align the project concept with the confirmed call scope, expected outcomes, and expected impacts. Refine the concept note and strategic positioning to reflect call-specific vocabulary and evaluation priorities.

**Required inputs:** Completed Phase 1. Populated `docs/tier3_project_instantiation/project_brief/` including concept note and project summary.

**Required outputs:** Revised concept note and strategic positioning reflecting call alignment; topic mapping in `docs/tier3_project_instantiation/call_binding/topic_mapping.json`; phase output summary in `phase2_concept_refinement/`.

**Gate condition:** Topic mapping is confirmed; concept note vocabulary is aligned with call-specific expected outcomes; strategic positioning identifies the proposal's differentiation within the call scope. No unresolved scope conflicts remain between the concept and Tier 2B.

---

### Phase 3 — Work Package Design and Dependency Mapping

**Purpose:** Design the work package structure: define work packages, tasks, deliverables, and inter-WP dependencies, grounded in the refined concept and aligned with the selected instrument's structural requirements.

**Required inputs:** Completed Phase 2. `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` and `objectives.json`.

**Required outputs:** Full work package structure with tasks, deliverables, dependencies, and responsible partners; written to `phase3_wp_design/`. Updated `workpackage_seed.json` if necessary.

**Gate condition:** All work packages have defined objectives, tasks, at least one deliverable, a responsible lead, and declared dependencies. The structure is consistent with the instrument's maximum WP count and deliverable constraints from Tier 2A.

---

### Phase 4 — Gantt and Milestones

**Purpose:** Produce the project timeline: assign tasks to months, define milestone events with verifiable achievement criteria, and confirm that the timeline fits within the project duration constraint.

**Required inputs:** Completed Phase 3. Project duration from call binding. Consortium roles from `docs/tier3_project_instantiation/consortium/roles.json`.

**Required outputs:** Gantt chart structure; milestone definitions with month, verifiable criterion, and responsible party; written to `phase4_gantt_milestones/`. Populated `docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json`.

**Gate condition:** All tasks are assigned to months. All milestones have a defined verifiable criterion. Timeline fits within the call-specified duration. No critical path dependency is unresolved.

---

### Phase 5 — Impact Architecture

**Purpose:** Construct the impact narrative: define the pathway from project outputs to expected outcomes to broader societal, scientific, or economic impacts, mapped against the call's expected impact criteria.

**Required inputs:** Completed Phase 2. `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` and `impacts.json`. Tier 2B `expected_outcomes.json` and `expected_impacts.json`.

**Required outputs:** Full impact pathway with outputs, outcomes, and impacts cross-referenced to call expected impacts; Key Performance Indicators for each impact claim; exploitation and dissemination logic; written to `phase5_impact_architecture/`.

**Gate condition:** Each expected impact specified in Tier 2B has at least one mapped project output. All impact claims are grounded in project activities from Phase 3. No impact claim is asserted without a traceable project mechanism.

---

### Phase 6 — Implementation Architecture

**Purpose:** Define the implementation approach: management structure, decision-making processes, risk management plan, ethical considerations, and gender and diversity plan where required by the instrument.

**Required inputs:** Completed Phases 3, 4, and 5. Consortium data from Tier 3. Risk seeds from `docs/tier3_project_instantiation/architecture_inputs/risks.json`. Compliance profile from `call_binding/compliance_profile.json`.

**Required outputs:** Management structure; decision-making matrix; populated risk register with mitigation measures; ethics self-assessment flags; implementation considerations mandated by the instrument; written to `phase6_implementation_architecture/`.

**Gate condition:** All instrument-mandated implementation sections are addressed. Risk register is populated. Ethics flags are explicitly stated (not omitted). Consortium management roles are assigned and non-overlapping.

---

### Phase 7 — Budget Gate

**Purpose:** Confirm that a validated budget from the external Lump Sum Budget Planner is available, internally consistent, and structurally compatible with the work package design, timeline, and consortium roles before final proposal content is completed.

**Required inputs:** Completed Phases 3, 4, and 6. A populated and validated budget response in `docs/integrations/lump_sum_budget_planner/received/`. Validation artifacts in `docs/integrations/lump_sum_budget_planner/validation/`.

**Required outputs:** Budget gate assessment written to `phase7_budget_gate/` confirming: receipt of budget response, structural consistency with WP structure, consistency with partner roles and effort, absence of blocking contradictions.

**Gate condition:** A validated budget response is present in the integration `received/` directory. Validation has confirmed structural consistency with WPs and consortium. No blocking inconsistencies are unresolved. This gate is mandatory. It cannot be bypassed, deferred, or substituted with internally generated budget estimates.

---

### Phase 8 — Drafting and Review

**Purpose:** Produce evaluator-oriented proposal section drafts for all application form sections, assemble them into a coherent whole, and conduct structured review against the evaluation criteria.

**Required inputs:** All preceding phases completed and gated. All Tier 3 data confirmed present and non-empty for the sections being drafted. Budget gate passed.

**Required outputs:** Drafted proposal sections in `docs/tier5_deliverables/proposal_sections/`; assembled draft in `docs/tier5_deliverables/assembled_drafts/`; review packet in `docs/tier5_deliverables/review_packets/`; phase output summary in `phase8_drafting_review/`.

**Gate condition:** All sections required by the active application form are drafted. Review packet distinguishes confirmed facts from inferences. No section contains content that is unresolved, contradicted by a higher tier, or dependent on a budget figure that has not been validated through the budget gate.

---

## 8. Budget Integration Constitution

The following rules govern budget data handling throughout the system and are non-negotiable:

**8.1** This repository does not compute, estimate, or generate lump-sum budgets. Budget computation is exclusively the responsibility of the external Lump Sum Budget Planner system.

**8.2** This repository may: prepare structured budget requests using templates in `docs/integrations/lump_sum_budget_planner/request_templates/`; consume validated budget responses from `docs/integrations/lump_sum_budget_planner/received/`; perform structural consistency validation between budget responses and work package/consortium design; and block workflow progress when budget data is absent, inconsistent, or unvalidated.

**8.3** No agent may invent, substitute, approximate, or silently generate budget figures. If a budget response has not been received and validated, any proposal content that depends on budget-confirmed effort allocations, resource claims, or cost justifications must be flagged as incomplete and must not be finalized.

**8.4** The budget gate (Phase 7) must pass before any Phase 8 activity begins. Phase 8 is fully blocked — including preparatory drafting — until the budget gate passes. Absent budget artifacts in `docs/integrations/lump_sum_budget_planner/received/` constitute a blocking gate failure, not a hold state. No Phase 8 substep (drafting, assembly, evaluator review, or revision) may commence before gate_09 confirms that a validated budget response is present and structurally consistent with the work package and consortium design.

**8.5** The interface contract at `docs/integrations/lump_sum_budget_planner/interface_contract.json` defines the schema and exchange protocol for budget requests and responses. All requests must conform to the interface contract. Responses that do not conform to the interface contract must be rejected and flagged, not silently accepted.

---

## 9. State, Memory, and Reproducibility Rules

**9.1** `docs/` is the authoritative repository of reproducible artifacts and source truth. Documents, extracted data, project data, orchestration state, and deliverables written to `docs/` are the durable record of the system's knowledge and decisions.

**9.2** `.claude/agent-memory/`, `.claude/cache/`, `.claude/logs/`, and `.claude/runs/` contain runtime execution state. These directories support operational continuity but are not constitutional source truth. They may be rebuilt, cleared, or invalidated without affecting the constitutional validity of the repository state in `docs/`.

**9.3** Agent working memory may assist execution. It must not override documented state in `docs/`. When a conflict exists between agent memory and documented Tier 3 or Tier 4 state, documented state governs.

**9.4** Every decision that affects future interpretation, traceability, or reproducibility must be written to `docs/tier4_orchestration_state/decision_log/` or to the relevant phase output. Decisions held only in agent memory do not constitute durable decisions.

**9.5** Orchestration outputs must be reproducible from their documented inputs. Where a process is non-deterministic, the inputs, parameters, and outputs must all be documented in Tier 4 so that the output is at minimum auditable.

**9.6** The `docs/index/` registries — `document_registry.json`, `schema_registry.json`, `rule_registry.json`, `instrument_registry.json`, `workflow_registry.json` — are the master indices of repository content. They must be maintained to reflect the current state of the repository.

---

## 10. Agent and Skill Obligations

**10.1** Every agent operating in this repository must consult this constitution before taking action on any workflow task. Constitution compliance is not optional and is not superseded by workflow instructions, skill definitions, or default agent behavior.

**10.2** Skills defined in `.claude/skills/` are execution aids. They implement specific, bounded operations. They are not authorities. A skill may not redefine phase meanings, tier meanings, gate logic, or the authority hierarchy.

**10.3** Workflows defined in `.claude/workflows/` must enforce constitutional phase sequencing and gate logic. A workflow that skips a gate, reorders phases, or silently bypasses a constitutional requirement is invalid and must not be executed.

**10.4** Agents operating within `.claude/agents/` must scope their actions to their designated task. No agent may unilaterally redefine the scope of a phase, alter the contents of a higher-tier source document, or declare a gate passed without confirming the gate condition.

**10.5** All major outputs produced by agents must be traceable to their tiered inputs. An agent must be able to identify, for each material claim in its output, the Tier 1–4 source from which the claim derives. Unattributed claims must be flagged, not asserted.

**10.6** Agents must not substitute their prior knowledge of Horizon Europe requirements for the contents of Tier 1 and Tier 2 source documents. When source documents are present, they govern. Generic programme knowledge is a fallback of last resort, and its use must be explicitly flagged.

---

## 11. Deliverable Rules

**11.1** All deliverables in Tier 5 must be evaluator-oriented. They must address evaluation criteria directly, in the language and frame of reference established by the applicable evaluation form (Tier 2A) and call-specific expected impacts and outcomes (Tier 2B).

**11.2** Deliverables must be compliant with the active instrument's application form structure and constraints. Section length, content requirements, and mandatory inclusions are governed by Tier 2A. Compliance with Tier 1 legal requirements is non-negotiable.

**11.3** Deliverables must be consistent with the active call and topic. Claims, objectives, impacts, and scope boundaries must reflect Tier 2B sources for the selected topic. Deliverables must not address calls or topics other than those confirmed in `docs/tier3_project_instantiation/call_binding/selected_call.json`.

**11.4** Tier 5 deliverables are the output layer. They must be derived from Tier 1–4 state. They must not introduce new facts, constraints, or framings that are not grounded in a higher tier.

**11.5** Final proposal text must not be produced from incomplete, contradictory, or unvalidated source state. Where source state is incomplete, the deliverable must flag the gap rather than fill it with fabricated content.

---

## 12. Validation and Review Rules

**12.1** Every phase output must be reviewable. Reviewability requires that the output identifies its source inputs by tier and file, states any inferences made, and flags any assumptions where source data was absent.

**12.2** Validation reports in `docs/tier4_orchestration_state/validation_reports/` must use the following status categories for each evaluated element:
- **Confirmed** — directly evidenced by a named source in Tier 1–3.
- **Inferred** — derived by logical reasoning from confirmed evidence; inference chain stated.
- **Assumed** — adopted in the absence of direct evidence; assumption explicitly declared.
- **Unresolved** — conflicting evidence or missing information; resolution required before downstream use.

**12.3** Contradictions between tiers must be resolved explicitly. The resolution method, the tier that prevailed, and the reasoning must be recorded in the decision log. A contradiction must not be silently resolved by selecting the more convenient source.

**12.4** Missing mandatory inputs must trigger a gate failure. They must not be papered over by hallucinated completion, generic programme knowledge, or optimistic inference. A gate failure is a valid and correct output.

**12.5** Review of Tier 5 assembled drafts must check: internal consistency; consistency with active call sources in Tier 2B; consistency with project data in Tier 3; compliance with instrument structure from Tier 2A; and absence of content that depends on an unpassed budget gate.

---

## 13. Forbidden Actions and Anti-Patterns

The following actions are constitutionally prohibited. Any agent, skill, workflow, or process that performs these actions violates this constitution:

**13.1** Treating Grant Agreement Annex templates as the governing structural schema for proposal writing. Annex templates govern post-award implementation reporting. Application form templates (Tier 2A) govern proposal writing.

**13.2** Inventing call constraints, scope requirements, expected outcomes, or expected impacts not present in Tier 2B source documents.

**13.3** Inventing project facts — partner names, capabilities, roles, objectives, prior experience, budget figures, team sizes, equipment — not present in Tier 3.

**13.4** Commencing any Phase 8 activity — including preparatory drafting — before the budget gate (Phase 7) has passed. Absent budget artifacts are a blocking gate failure. No Phase 8 substep may begin until gate_09 is satisfied. This prohibition covers all modes of Phase 8 execution without exception.

**13.5** Storing durable decisions only in agent memory without writing them to Tier 4.

**13.6** Allowing a workflow or skill to become a de facto constitutional authority by expanding its scope to redefine phase meanings, tier meanings, or gate logic.

**13.7** Silently reordering phases or weakening gate conditions to allow workflow progress when inputs are incomplete.

**13.8** Finalizing proposal text when source state is known to be incomplete, contradictory, or unvalidated, without explicitly flagging the gap in the deliverable.

**13.9** Using agent-local knowledge of Horizon Europe programme rules as a substitute for reading Tier 1 source documents when those documents are present and accessible.

**13.10** Producing outputs in Tier 5 that are not traceable to specific inputs in Tier 1–4.

**13.11** Modifying Tier 1 or Tier 2 source documents to reflect project-specific assumptions.

**13.12** Treating `CLAUDE.md` as advisory or optional.

---

## 14. Constitutional Change Rules

`CLAUDE.md` is the project constitution. Changes to it are constitutional amendments.

**14.1** Amendments must be explicit. A change to constitutional meaning effected by modifying a workflow, skill, or agent definition without amending `CLAUDE.md` is invalid and is overridden by this constitution.

**14.2** Every amendment must identify: the section amended; the prior rule; the new rule; the reason for the change; and the components (workflows, skills, agents, tier definitions) whose behavior is impacted.

**14.3** Amendments that change phase definitions, gate conditions, tier meanings, or the authority hierarchy must trigger a review of all affected workflows, skills, and agents to confirm continued compliance with the amended constitution.

**14.4** Amendments must preserve internal consistency. A change that creates a contradiction between sections of this constitution is invalid unless it simultaneously resolves the contradiction.

**14.5** Amendments may not be made by agents, skills, or workflows operating autonomously. Constitutional amendment requires explicit human instruction.

---

## 15. Final Constitutional Rule

Where any workflow component, skill, agent instruction, prompt, or cache conflicts with this constitution, this constitution governs without exception.

Where the runtime behavior of the system and the documented state in `docs/` diverge, documented constitutional state governs.

The system must prefer explicit gate failure over fabricated completion. A declared failure is an honest and correct output. A fabricated completion is a constitutional violation.

When in doubt about the admissibility of an action, the agent must consult this constitution first, then consult the tiered source materials, and may proceed only if the action is consistent with both.

---

## 16. Agent Derivation and Execution Binding

**16.1** Agents are execution-layer components derived from the workflow specification. They do not define workflow logic; they implement it.

**16.2** The authoritative source of agent scope, responsibilities, and phase alignment is:
- the compiled workflow manifest (`manifest.compile.yaml`)
- the agent catalog (`agent_catalog.yaml`)
- the artifact schema specification (`artifact_schema_specification.yaml`)

**16.3** Agents must not:
- redefine phase purposes or boundaries
- introduce new artifact types, paths, or schemas not defined in Tier 2A/2B/3/4 specifications
- produce outputs that are not compliant with canonical artifact schemas
- bypass or reinterpret gate conditions

**16.4** Each agent must:
- read only from declared tier inputs
- write only to canonical artifact paths defined in the workflow and schema specifications
- ensure that all outputs are structurally compliant with the artifact schema specification
- operate deterministically from documented inputs

**16.5** The compiled workflow manifest defines the binding between:
- phases (nodes)
- agents
- skills
- gate conditions

This binding must not be overridden by agent implementations.

**16.6** Agents are not authorities. They are execution mechanisms subordinate to:
- CLAUDE.md
- tiered sources (Tier 1–4)
- workflow definitions

**16.7** Any divergence between agent output and:
- artifact schemas
- manifest-defined expectations
- gate conditions

must be treated as a failure, not as an alternative valid interpretation.

---

## 17. Runtime Execution Architecture

This section defines the runtime execution stack that implements the workflow execution model (Section 6) and the agent derivation rules (Section 16). The runtime architecture is constitutionally binding. Implementations that violate the layering, contracts, or prohibitions defined here are constitutional violations, regardless of whether they produce correct outputs.

### 17.1 Execution Stack

The system executes through a three-layer runtime stack. Each layer has a single, defined caller:

| Layer | Module | Called by | Calls |
|-------|--------|-----------|-------|
| Scheduler | `DAGScheduler` | CLI entry point (`runner/__main__.py`) | Agent runtime, gate evaluator |
| Agent runtime | `run_agent()` | Scheduler (`_dispatch_node()`) | Skill runtime |
| Skill runtime | `run_skill()` | Agent runtime (`run_agent()`) | Claude API |

The following call-graph constraints are unconditional:

**17.1.1** The scheduler calls the agent runtime. The scheduler never calls the skill runtime directly. All skill invocations flow through the agent runtime.

**17.1.2** The agent runtime calls the skill runtime. The agent runtime never calls the gate evaluator, the scheduler, or other agents (except: the n03 sub-agent and n07 pre-gate agent are coordinated within the same node body execution, per the manifest's `sub_agent` and `pre_gate_agent` bindings).

**17.1.3** The skill runtime calls the Claude API. The skill runtime never calls the agent runtime, the scheduler, or the gate evaluator.

**17.1.4** The gate evaluator is called by the scheduler. It is never called by agents or skills.

### 17.2 Node Execution Model

Each node dispatch follows a five-step contract. This contract is the sole implementation of Section 6's phase execution rules within the scheduler:

1. **Set state to `running`.** Persist to `RunContext`.
2. **Evaluate entry gate** (if defined). On failure: set state to `blocked_at_entry`; return immediately. Agent body is never invoked.
3. **Execute node body** via `run_agent()`. The agent runtime loads the agent and prompt specifications, sequences skill invocations through `run_skill()`, and returns an `AgentResult`. On failure or when `can_evaluate_exit_gate` is `False`: set state to `blocked_at_exit` with `failure_origin="agent_body"`; skip exit gate; return immediately.
4. **Evaluate exit gate.** On pass: set state to `released`. On failure: set state to `blocked_at_exit` with `failure_origin="exit_gate"`.
5. **Return `NodeExecutionResult`** capturing the full composite outcome.

This contract is the sole modification point in the scheduler for node body execution. The `run()` dispatch loop, stall detection, `RunSummary` construction, and `ManifestGraph` are not modified by agent or skill integration.

### 17.3 Failure Semantics

All node-level failures are classified by exactly one `failure_origin` value. No new node states are introduced. The existing state machine (`pending`, `running`, `released`, `blocked_at_entry`, `blocked_at_exit`, `deterministic_pass_semantic_pending`, `hard_block_upstream`) is unchanged.

**17.3.1 Failure origins.** The closed set of failure origins is:

| Origin | When | Node state | Exit gate evaluated |
|--------|------|------------|-------------------|
| `entry_gate` | Entry gate returns status != "pass" | `blocked_at_entry` | No |
| `agent_body` | Agent runtime returns failure or `can_evaluate_exit_gate == False` | `blocked_at_exit` | No |
| `exit_gate` | Exit gate returns status != "pass" after successful agent body | `blocked_at_exit` | Yes |

**17.3.2 Exit gate skip rule.** Exit gate evaluation is skipped if and only if: (a) entry gate failed, (b) agent body failed, or (c) `AgentResult.can_evaluate_exit_gate` is `False`. In all other cases — specifically when `AgentResult.status == "success"` and `can_evaluate_exit_gate == True` — exit gate evaluation proceeds unconditionally. The `can_evaluate_exit_gate` flag is determined by inspecting actual artifacts on disk, not by optimistic assumption.

**17.3.3 CONSTITUTIONAL_HALT propagation.** A `CONSTITUTIONAL_HALT` from any skill causes the agent to halt immediately and return `AgentResult(status="failure", failure_category="CONSTITUTIONAL_HALT", can_evaluate_exit_gate=False)`. The scheduler treats this identically to any other agent-body failure.

**17.3.4 HARD_BLOCK from agent-body failure.** When `gate_09_budget_consistency` is the exit gate of a node whose agent body fails, HARD_BLOCK propagation to Phase 8 nodes is triggered, identically to how it is triggered by exit-gate failure. Agent-body failure at the budget gate node is not a lesser failure — it produces the same downstream freeze.

**17.3.5 Failure metadata persistence.** `failure_origin`, `exit_gate_evaluated`, `failure_reason`, and `failure_category` are persisted to `RunContext` alongside node state and are included in `RunSummary.node_failure_details` and `run_summary.json`.

### 17.4 Runtime Contracts

The runtime stack communicates through three structured result types. These are data contracts, not implementation details. Any runtime layer that produces results inconsistent with these contracts is in violation.

**17.4.1 `SkillResult`** — returned by `run_skill()` to the agent runtime:
- `status`: `"success"` or `"failure"`
- `outputs_written`: paths of artifacts written (relative to repo root)
- `failure_reason`: human-readable description (required on failure)
- `failure_category`: one of `MISSING_INPUT`, `MALFORMED_ARTIFACT`, `CONSTRAINT_VIOLATION`, `INCOMPLETE_OUTPUT`, `CONSTITUTIONAL_HALT` (required on failure)

**17.4.2 `AgentResult`** — returned by `run_agent()` to the scheduler:
- `status`: `"success"` or `"failure"`
- `can_evaluate_exit_gate`: `True` only when all gate-relevant artifacts exist on disk
- `failure_origin`: always `"agent_body"` (this type is only constructed by the agent runtime)
- `failure_category`: one of the skill categories plus `SKILL_FAILURE`, `AGENT_EXECUTION_ERROR`
- `invoked_skills`: ordered record of all skill invocations and their results

**17.4.3 `NodeExecutionResult`** — returned by `_dispatch_node()` to the scheduler's `run()` loop:
- `node_id`: canonical manifest node ID
- `final_state`: terminal state after dispatch
- `failure_origin`: `"entry_gate"`, `"agent_body"`, `"exit_gate"`, or `None`
- `exit_gate_evaluated`: `True` only when `evaluate_gate()` was actually called on the exit gate
- `agent_result`: the `AgentResult` (or `None` when entry gate failed before agent execution)

### 17.5 Claude API Execution Principle

**17.5.1** Skill `.md` files and agent `.md` files are **specifications, not executable code**. There is no interpreter that reads a Markdown execution specification and deterministically executes its steps. The entity that performs domain reasoning is Claude, invoked via the Claude API.

**17.5.2** The skill runtime (`run_skill()`) is a **Claude API adapter** that: loads the skill specification, resolves canonical inputs from disk, assembles a structured prompt, invokes the Claude API, parses the structured JSON response, validates it against the expected schema, writes the validated output atomically to the canonical path, and returns a `SkillResult`. It contains prompt assembly, API invocation, response parsing, validation, and I/O logic — not domain knowledge.

**17.5.3** The agent runtime (`run_agent()`) is an **orchestration adapter** that: loads agent and prompt specifications, resolves canonical inputs, sequences skill invocations through `run_skill()`, manages context passing between invocations, handles failure propagation, and determines `can_evaluate_exit_gate` from disk state. It does not perform domain reasoning itself.

**17.5.4** If Claude's response is malformed, incomplete, or violates a constitutional constraint, the runtime returns a failure result. It does not retry, improvise, or silently repair the response.

### 17.6 Runtime Prohibitions

The following runtime-layer constraints supplement the general prohibitions in Section 13:

**17.6.1** The scheduler must not invoke skills directly. All skill invocations must flow through the agent runtime.

**17.6.2** Agents must not evaluate gates. Gate evaluation is exclusively a scheduler responsibility.

**17.6.3** Skills must not write gate results. Gate result artifacts are written exclusively by the gate evaluator.

**17.6.4** Skills must not invoke other skills. Each skill is an atomic, single-invocation unit. Skill composition is managed by the agent runtime.

**17.6.5** The runtime must not silently repair Claude API responses. Missing `run_id`, incorrect `schema_id`, or presence of `artifact_status` in a skill response are validation failures, not auto-correctable conditions.

**17.6.6** `can_evaluate_exit_gate` must be determined by inspecting actual file-system state (artifacts present on disk), not by assuming that successful skill invocations imply artifact presence.

**17.6.7** No runtime layer may fabricate, estimate, or substitute budget figures. Budget computation remains exclusively the responsibility of the external Lump Sum Budget Planner system per Section 8.

---

### Constitutional Amendment Record — Section 17

| Field | Value |
|-------|-------|
| Section amended | New section added (Section 17) |
| Prior rule | No prior Section 17 existed. Runtime execution was implicit in Sections 6, 10, and 16 but not formally defined. |
| New rule | Section 17 formalizes the three-layer execution stack (scheduler → agent runtime → skill runtime → Claude API), the five-step node dispatch contract, failure origin classification, runtime result contracts, the Claude API adapter principle, and runtime-layer prohibitions. |
| Reason for change | The runtime integration layer has been fully implemented and tested (988 tests, Steps 1–9 of `runtime_integration_execution_plan.md`). The system is now an executable orchestration engine, not only a workflow specification repository. The constitution must reflect the implemented runtime architecture to prevent future modifications from violating the established layering, call-graph constraints, and failure semantics. |
| Impacted components | `runner/dag_scheduler.py` (`_dispatch_node()`), `runner/agent_runtime.py` (`run_agent()`), `runner/skill_runtime.py` (`run_skill()`), `runner/runtime_models.py` (result contracts), `runner/run_context.py` (failure metadata persistence), all agent and skill `.md` specifications (clarified as Claude API prompt sources, not executable code). |

*Repository constitution. In force from creation. Amendments require explicit human instruction per Section 14.*
