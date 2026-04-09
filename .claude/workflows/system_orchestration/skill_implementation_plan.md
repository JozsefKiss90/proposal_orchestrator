# Skill Implementation Plan
## Horizon Europe Proposal Orchestration System — Skill Runtime Layer

**Package:** `system_orchestration` v1.1
**Plan status:** Authoritative specification. No skill file may be generated without reading all mandatory sources listed in §1.
**Constitutional authority:** Subordinate to `CLAUDE.md`. This plan operationalizes; it does not override.

---

## 1. Mandatory Sources — Required Reading in Authority Order

No skill implementation may be generated, modified, or reviewed without first reading all of the following sources in the order listed. The order reflects the constitutional authority hierarchy (CLAUDE.md §3).

| Priority | File | Why Mandatory |
|----------|------|---------------|
| 1 | `CLAUDE.md` | Highest interpretive authority. Defines forbidden actions, tier model, phase sequence, gate semantics, and all constitutional prohibitions (§13). No skill may act in a way that conflicts with it. |
| 2 | `.claude/workflows/system_orchestration/manifest.compile.yaml` | Binding execution model: node registry, skills listed per node, artifact registry with canonical paths. Defines which skills are bound to which nodes and what artifacts are written. |
| 3 | `.claude/workflows/system_orchestration/skill_catalog.yaml` | The authoritative source of skill identity. Defines `id`, `purpose`, `used_by_agents`, `reads_from`, `writes_to`, and `constitutional_constraints` for every skill. No skill may be implemented without reading its catalog entry. |
| 4 | `.claude/workflows/system_orchestration/agent_catalog.yaml` | Defines agent scope, reads_from, writes_to, and must_not constraints. Required to confirm that skill invocations are consistent with the agent's declared scope. |
| 5 | `.claude/workflows/system_orchestration/artifact_schema_specification.yaml` | Field-level schemas for every canonical artifact. Required before implementing any skill that writes a canonical artifact. |
| 6 | `.claude/workflows/system_orchestration/state_rules.yaml` | State durability, checkpoint preservation, decision logging, and rerun behavior rules. Applies to all skills that write to Tier 4 or Tier 5 paths. |
| 7 | `.claude/workflows/system_orchestration/design_notes.yaml` | Design rationale, especially `workflow_as_authoritative_specification`, `constitutional_subordination`, and `tier3_as_project_container`. Governs implementation intent. |
| 8 | `.claude/workflows/system_orchestration/README.md` | Contextual execution reference. Defines current package structure and execution boundaries. Must be read to prevent architectural misinterpretation (e.g. scheduler–agent–skill separation). |

**Enforcement rule:** An implementer that skips any of these sources and proceeds from memory violates CLAUDE.md §10.6 and §13.9. The resulting skill is constitutionally invalid and must not be used.

---

## 1.1 Mandatory Source Usage — Execution Rule

The sources listed in §1 are not a one-time reading step.

They must be actively referenced and re-consulted during EVERY implementation step.

Requirements:

- No step may rely on memory of a source without re-checking it when:
  - binding canonical inputs or outputs
  - applying constitutional constraints
  - referencing artifact paths or schema IDs
  - determining which agents invoke a skill

- Whenever a step uses:
  - artifact paths → MUST re-check `manifest.compile.yaml` artifact registry
  - schema fields → MUST re-check `artifact_schema_specification.yaml`
  - skill scope (reads_from / writes_to) → MUST re-check `skill_catalog.yaml`
  - agent context → MUST re-check `agent_catalog.yaml`
  - state rules → MUST re-check `state_rules.yaml`

- If a step proceeds without re-validating these sources, the result is invalid.

## 1.2 Contextual Execution Sources

The following sources are not part of the constitutional authority hierarchy but MUST be read to correctly interpret the current implementation state and execution boundaries.

| File | Purpose |
|------|--------|
| `.claude/workflows/system_orchestration/README.md` | Defines current package structure, execution boundaries, and scheduler–agent–skill separation. Prevents architectural misinterpretation during implementation. |

These sources do not override §1 Mandatory Sources but must be consulted before making implementation decisions.

---

## 2. Conceptual Position of Skills

### 2.1 Authoritative Definition

Skills are **atomic, reusable execution units** invoked by agents to perform a bounded, well-defined operation within a phase. They are implementation targets defined in `skill_catalog.yaml`. They are not runtime improvisations, not workflow components, and not authorities.

The execution model is strictly layered:

```
DAG scheduler
    └── invokes agent (node body executor)
            └── agent invokes skill(s)
                    └── skill writes artifact(s)
                            └── DAG scheduler evaluates gate
```

This layer ordering is unconditional. No element of the system may collapse or bypass any layer in this chain.

### 2.2 What Skills Are

- **Atomic.** Each skill performs one bounded operation. It does not orchestrate sub-operations across other skills.
- **Reusable.** A skill may be invoked by multiple agents across multiple phases, as declared in its `used_by_agents` field in `skill_catalog.yaml`.
- **Implementation targets.** Skills are specified in the catalog. They do not specify themselves at runtime.
- **Execution aids.** Skills implement specific operations. They are not constitutional authorities. They do not define workflow logic.

### 2.3 What Skills Are Not

Skills are not:

- **Gate evaluators.** Skills never evaluate whether a gate has passed or failed. Gate evaluation is exclusively the responsibility of the DAG scheduler, operating on written artifacts. The `gate-enforcement` skill writes gate evidence to Tier 4; it does not call the scheduler's evaluation function.
- **Orchestrators.** Skills do not control phase sequencing, call other skills, call agents, or issue commands to the DAG scheduler.
- **State owners.** Skills do not own orchestration state. They write artifacts to declared paths; the scheduler reads gate state from those paths.
- **Authorities.** A skill definition does not override CLAUDE.md, the manifest, the artifact schema specification, or any higher-tier source.

### 2.4 Scope Boundaries

Every skill operates strictly within:
- its `reads_from` paths declared in `skill_catalog.yaml`
- its `writes_to` paths declared in `skill_catalog.yaml`
- its `constitutional_constraints` declared in `skill_catalog.yaml`

A skill that reads outside its `reads_from`, writes outside its `writes_to`, or violates any `constitutional_constraint` is in constitutional violation.

### 2.5 Invocation Chain

Skills are invoked **only through agents**. The DAG scheduler never invokes a skill directly. The agent defines:
- when the skill is invoked (trigger condition within the agent's execution)
- what input it receives
- what output or side-effect it is expected to produce

A skill must not:
- call another skill autonomously
- call an agent
- issue commands to the DAG scheduler
- evaluate a gate condition
- modify scheduler state

This is structurally enforced by the execution model. Any skill implementation that attempts to cross these boundaries is unconstitutionally scoped and must not be deployed.

---

## 3. Objectives and Outputs of the Skill Implementation Process

### 3.1 Goal

Produce a fully implementable specification for:

- the skill runtime layer
- the invocation interface between agents and skills
- input/output enforcement per skill
- constitutional constraint enforcement per skill
- validation and failure semantics

The output of this plan is a complete set of skill implementation files and a shared skill runtime contract. These files form the lowest executable layer of the orchestration system below the agent layer.

### 3.2 Output Artifacts

The implementation process produces the following file sets:

#### A. Skill implementation files — `.claude/skills/<skill_id>.md`

One Markdown file per skill in `skill_catalog.yaml`. The file name must exactly match the skill `id` field.

**Required front matter fields (YAML block at top of file):**

```yaml
---
skill_id: <id from skill_catalog.yaml>
purpose_summary: <one sentence; must not expand scope beyond skill_catalog.yaml purpose>
used_by_agents: [<list from skill_catalog.yaml>]
reads_from: [<paths from skill_catalog.yaml>]
writes_to: [<paths from skill_catalog.yaml>]
constitutional_constraints: [<list from skill_catalog.yaml — verbatim>]
---
```

The body of each skill file is an **execution specification** — a precise, step-by-step definition of what the skill must do, what it reads, what it validates, what it writes, and how it fails. It is not an agent prompt. It does not instruct an LLM to reason freely. It specifies deterministic operations.

#### B. Skill runtime contract — `.claude/skills/skill_runtime_contract.md`

A single shared contract document (see §4) that all skill files must conform to. Defines the standard obligations that apply to every skill implementation regardless of purpose.

#### C. Skill registry binding (if required by runtime)

If the execution runtime requires a registry that maps `skill_id` to its callable entry point, a registry artifact is produced as `.claude/skills/skill_registry.yaml`. This artifact is a binding table only; it does not alter skill scope, constraints, or constitutional obligations.

### 3.3 What the Implementation Process Does NOT Produce

- Budget computation logic (prohibited by CLAUDE.md §8.1)
- New artifact paths not defined in `manifest.compile.yaml` or `artifact_schema_specification.yaml`
- New skills beyond those defined in `skill_catalog.yaml`
- Modifications to `skill_catalog.yaml`, `manifest.compile.yaml`, `CLAUDE.md`, or `artifact_schema_specification.yaml`
- Gate evaluation functions (these belong to the DAG scheduler, not to skills)
- Skills with scope that spans multiple phases beyond what `skill_catalog.yaml` declares

---

## 4. Skill Runtime Contract — Minimum Requirements for Every Skill Implementation

Every `.claude/skills/<skill_id>.md` file must satisfy the following contract. This is the implementation unit specification.

### 4.1 Skill Identity

| Field | Requirement |
|-------|-------------|
| `skill_id` | Must exactly match the `id` field in `skill_catalog.yaml` |
| `purpose_summary` | ≤ 2 sentences; must not expand the scope defined in `skill_catalog.yaml` purpose |
| `used_by_agents` | Must match `used_by_agents` from `skill_catalog.yaml` exactly |

### 4.2 Scope Enforcement

The skill must operate exclusively within:
- `reads_from` paths as declared in `skill_catalog.yaml`
- `writes_to` paths as declared in `skill_catalog.yaml`

The skill must not read from any path not declared in its `reads_from`. The skill must not write to any path not declared in its `writes_to`. Cross-phase reads require explicit declaration in `skill_catalog.yaml`; they may not be assumed.

**Scope violations are hard failures**, not advisory warnings. If the skill requires access to a path not declared in its catalog entry, the catalog entry must be amended before the skill may access that path.

### 4.3 Canonical Inputs

For every path listed in `reads_from`, the skill implementation must specify:
- the exact path being read
- what fields or content elements are extracted
- what purpose each extracted element serves in the skill's operation

Input validation requirements:
- **Presence check:** The artifact at the declared path must be confirmed present before the skill proceeds. Absent mandatory inputs trigger a declared failure — not inference, not substitution.
- **Non-empty check:** For JSON artifacts, the root object must be non-empty.
- **Schema conformance check:** For canonical Tier 4 artifacts, the `schema_id` field must match the expected `schema_id_value` from `artifact_schema_specification.yaml`. A mismatched `schema_id` is a `MALFORMED_ARTIFACT` failure.
- **Validated state check:** For artifacts that carry `artifact_status`, the value must be `valid`. An artifact with `artifact_status: invalid` must not be used as skill input.

### 4.4 Canonical Outputs

The skill implementation must explicitly specify every artifact it writes, including:
- the canonical artifact path from `writes_to` in `skill_catalog.yaml`
- the schema ID the artifact must carry (from `artifact_schema_specification.yaml`, where applicable)
- all required fields and their derivation source
- the `run_id` field (received from the invoking agent, which receives it from the DAG scheduler at node invocation)

Output conformance requirements:
- All output files must be written to declared `writes_to` paths and nowhere else
- For canonical Tier 4 phase output artifacts: `schema_id` must be stamped at write time
- For canonical Tier 4 phase output artifacts: `run_id` must be propagated from the invoking agent
- `artifact_status` must be left **absent** at write time — the DAG scheduler runner stamps this field after gate evaluation
- Partial outputs are not allowed. If the skill cannot produce a complete, conformant artifact, it must declare a failure and write nothing to the output path (or write a failure report to the decision log, depending on the skill's write scope)

### 4.5 Determinism

- Same inputs, same documented state → same outputs
- The skill must not rely on hidden state, agent memory, runtime randomness, or prior execution state not recorded in `docs/`
- The skill must not read from `.claude/agent-memory/`, `.claude/cache/`, or `.claude/runs/` as inputs
- If a non-deterministic process is involved, the inputs, parameters, and outputs must all be documented in Tier 4 so the output is at minimum auditable (CLAUDE.md §9.5)

### 4.6 Constitutional Constraint Enforcement

Each constraint listed in the skill's `constitutional_constraints` in `skill_catalog.yaml` must be enforced as a **hard failure condition**, not as advisory guidance.

The enforcement mechanism for each constraint must be explicit in the skill implementation. The following examples illustrate the required treatment:

| Constraint (from skill_catalog.yaml) | Required enforcement |
|--------------------------------------|----------------------|
| "Must not invent call requirements not present in source documents" (`call-requirements-extraction`) | Every extracted element must carry a named source section reference; any element lacking a source reference must be flagged as `Unresolved`, not emitted as `Confirmed` |
| "Must never substitute a Grant Agreement Annex as a section schema source" (`instrument-schema-normalization`) | The skill must verify the document is a Tier 2A application form before extracting from it; if the document is a Grant Agreement Annex, halt with a constitutional violation |
| "Must not generate or estimate budget figures" (`budget-interface-validation`) | The skill must not write any numeric budget value it has not received verbatim from `docs/integrations/lump_sum_budget_planner/received/`; generating an estimate is a halt condition |
| "Gate failure must be declared explicitly; fabricated completion is a constitutional violation" (`gate-enforcement`) | The skill must never write a gate result of `passed` unless every gate condition has been confirmed against documented artifacts |
| "Validated checkpoints must not be overwritten by subsequent reruns" (`checkpoint-publish`) | Before writing, the skill must check whether a checkpoint already exists at the target path with a validated status; if one exists, the skill must write a new file, not overwrite |

The full constraint list for each skill is defined in `skill_catalog.yaml` and must be read verbatim during implementation. No constraint may be softened, re-interpreted, or omitted.

### 4.7 Validation Status Vocabulary

Where a skill produces a validation report, phase output, or claim-bearing artifact, it must apply the following status categories to each evaluated element (per CLAUDE.md §12.2 and `state_rules.yaml` `validation_status_vocabulary`):

- **Confirmed** — directly evidenced by a named source in Tier 1–3; the source artifact must be named
- **Inferred** — derived by logical reasoning from confirmed evidence; the inference chain must be stated
- **Assumed** — adopted in the absence of direct evidence; the assumption must be explicitly declared
- **Unresolved** — conflicting evidence or missing information; resolution required before downstream use

Skills must not mark a claim `Confirmed` without identifying the specific source artifact. Skills must not silently treat an `Unresolved` element as `Confirmed`.

### 4.8 Failure Behaviour

The skill must implement the following failure protocol:

1. **Missing mandatory input:** Halt. Write the missing input to the decision log at `docs/tier4_orchestration_state/decision_log/` (if the skill has that write path), or surface the failure to the invoking agent for the agent to log. Do not substitute, infer, or hallucinate the missing content.

2. **Schema violation on input:** Halt with `MALFORMED_ARTIFACT`. Do not proceed with a malformed artifact.

3. **Constitutional constraint violation triggered:** Halt immediately. Do not produce partial output. Write the triggered constraint and the violating condition to the decision log.

4. **Output cannot be made complete and conformant:** Halt. Write a failure notice. Do not write a partial artifact to the canonical output path. A partial artifact is worse than no artifact because it may be mistaken for a completed output.

5. **Source data insufficient for required operation:** Declare the deficiency using the appropriate `Unresolved` status. Write to decision log where write scope permits. Do not fabricate completion.

**Failure is a correct and valid output.** A skill that correctly identifies and declares a failure has fulfilled its constitutional obligation. A skill that fabricates completion to avoid failure has violated the constitution.

### 4.9 Side-Effect Control

Skills may only produce the following side effects:
- Write artifacts to declared `writes_to` paths
- Write validation reports to `docs/tier4_orchestration_state/validation_reports/` (only if declared in `writes_to`)
- Write decision log entries to `docs/tier4_orchestration_state/decision_log/` (only if declared in `writes_to`)

Skills must not:
- Write to any path outside their declared `writes_to`
- Modify Tier 1 or Tier 2 source documents
- Modify `CLAUDE.md`
- Modify `manifest.compile.yaml` or `skill_catalog.yaml` or `agent_catalog.yaml`
- Modify any checkpoint artifact that has been formally validated
- Invoke another skill
- Invoke an agent
- Issue any instruction to the DAG scheduler

---

## 5. Skill-to-Agent Binding Model

### 5.1 Binding Source

The authoritative source for which skills are bound to which agents is the `node_registry` in `manifest.compile.yaml`. Each node entry contains a `skills` list. This list defines the skills the agent executing that node must invoke.

The `used_by_agents` field in `skill_catalog.yaml` is the corroborating declaration. Both sources must be consistent. If they conflict, `manifest.compile.yaml` governs per CLAUDE.md §3 (authority hierarchy position 8 for workflows vs 9 for skills).

### 5.2 Invocation Obligation

An agent that lists a skill in the manifest's `skills` field for its node must invoke that skill during its execution. Omitting a declared skill invocation without a recorded justification is a conformance failure.

### 5.3 Invocation Sequencing

Within a single agent execution, skills are invoked in the order that satisfies their input dependencies. Skills that require the output of a prior skill must be invoked after that prior skill has completed and written its output. The agent controls this sequencing; the skill does not.

### 5.4 Single-Level Invocation

Skills are invoked exclusively at one level: agent invokes skill. This means:

- A skill must not invoke another skill
- A skill must not invoke an agent
- The agent is the sole entity responsible for composing multi-skill workflows

If a skill appears to require another skill's output as input, the agent must invoke both skills in the correct order and pass the first skill's output to the second skill's input. This is agent-level composition, not skill-level orchestration.

### 5.5 Skill Reuse Across Agents

When a skill is listed under multiple agents in `used_by_agents`, each invocation is independent. The skill receives its inputs from the invoking agent's context and writes to the paths declared in its `writes_to`. It carries no state between invocations. Reuse does not imply shared state.

---

## 6. Skill Invocation Model

### 6.1 Standard Interface

Every skill must be invocable through the following standard interface:

```
run_skill(
    skill_id:   str,        # Must match skill_catalog.yaml id exactly
    run_id:     str,        # Propagated from DAG scheduler to agent to skill
    repo_root:  Path,       # Absolute path to repository root
    inputs:     dict        # Keyed by input path or input name; values are resolved artifacts
) -> SkillResult
```

### 6.2 SkillResult

```
SkillResult:
    status:              "success" | "failure"
    outputs_written:     list[str]   # Paths of artifacts written (relative to repo_root)
    validation_report:   str | None  # Path to validation report written, if any
    failure_reason:      str | None  # Human-readable failure description; required when status == "failure"
    failure_category:    str | None  # One of: MISSING_INPUT | MALFORMED_ARTIFACT |
                                     #         CONSTRAINT_VIOLATION | INCOMPLETE_OUTPUT |
                                     #         CONSTITUTIONAL_HALT
```

### 6.3 run_id Propagation

The `run_id` is assigned by the DAG scheduler at run invocation time and passed to the agent at node execution. The agent passes it to every skill it invokes. Every canonical Tier 4 and Tier 5 artifact written by a skill must carry the `run_id` as a top-level field. This enables post-hoc traceability of which run produced which artifact.

### 6.4 repo_root Scope

All file paths used by the skill must be constructed relative to `repo_root`. Absolute path construction outside of `repo_root` is not permitted. This ensures the skill operates exclusively within the repository boundary.

### 6.5 Inputs Validation Before Execution

Before performing any substantive operation, the skill must validate all declared inputs:
1. Confirm each declared input path exists
2. Confirm each input is non-empty
3. For canonical JSON artifacts: confirm schema conformance per §4.3
4. On any validation failure: return `SkillResult(status="failure", failure_category="MISSING_INPUT" or "MALFORMED_ARTIFACT")`

No substantive processing may begin until all input validations pass.

---

## 7. Skill Implementation Sequence

Execute the steps in order. Do not begin a step before all prior steps are complete. No step may be skipped.

### Step 1 — Initialize implementation context

Confirm all mandatory sources (§1) are available and readable in the order listed.

Specifically:
- Read `CLAUDE.md` — note all constitutional prohibitions in §13
- Read `manifest.compile.yaml` — extract the full `node_registry` skills lists and `artifact_registry`
- Read `skill_catalog.yaml` — extract all 19 skill entries
- Read `agent_catalog.yaml` — note `reads_from`, `writes_to`, and `must_not` for each agent
- Read `artifact_schema_specification.yaml` — note all `schema_id_value` values and `required: true` fields for artifacts that skills write
- Read `state_rules.yaml` — note all durability, checkpoint, and decision-logging rules
- Read `design_notes.yaml` — note execution separation rationale and constitutional subordination
- Read `README.md` — confirm current package structure, execution boundaries, and scheduler/agent/skill separation

Do not assume prior reading persists. Re-read before each step that makes binding decisions.

### Step 2 — Scaffold all skill files

Create an empty (front-matter-only) `.claude/skills/<skill_id>.md` for each of the 19 skills in `skill_catalog.yaml`, plus the `skill_runtime_contract.md`.

**Skill file list:**
```
.claude/skills/call-requirements-extraction.md
.claude/skills/evaluation-matrix-builder.md
.claude/skills/instrument-schema-normalization.md
.claude/skills/topic-scope-check.md
.claude/skills/concept-alignment-check.md
.claude/skills/work-package-normalization.md
.claude/skills/wp-dependency-analysis.md
.claude/skills/milestone-consistency-check.md
.claude/skills/impact-pathway-mapper.md
.claude/skills/dissemination-exploitation-communication-check.md
.claude/skills/governance-model-builder.md
.claude/skills/risk-register-builder.md
.claude/skills/budget-interface-validation.md
.claude/skills/proposal-section-traceability-check.md
.claude/skills/evaluator-criteria-review.md
.claude/skills/constitutional-compliance-check.md
.claude/skills/gate-enforcement.md
.claude/skills/decision-log-update.md
.claude/skills/checkpoint-publish.md
.claude/skills/skill_runtime_contract.md
```

At scaffold time, the body may be a placeholder. Front matter must be populated before Step 3.

### Step 3 — Fill in standard front matter for each skill

For each scaffolded file, populate all front matter fields from §3.2A using `skill_catalog.yaml` as the exclusive source. Verify:
- `skill_id` exactly matches the `id` field in `skill_catalog.yaml`
- `purpose_summary` accurately captures the `purpose` without expanding scope
- `used_by_agents` matches the `used_by_agents` list in `skill_catalog.yaml` exactly
- `reads_from` matches `reads_from` in `skill_catalog.yaml` exactly
- `writes_to` matches `writes_to` in `skill_catalog.yaml` exactly
- `constitutional_constraints` is copied verbatim from `skill_catalog.yaml` — no paraphrase, no omission

### Step 4 — Bind canonical inputs and outputs **Status: COMPLETE**

For each skill:
- Expand each path in `reads_from` to identify:
  - The specific artifact(s) at that path that the skill will read
  - The fields extracted from each artifact
  - The schema ID expected (from `artifact_schema_specification.yaml`) for canonical artifacts
- Expand each path in `writes_to` to identify:
  - The specific artifact(s) the skill will write at that path
  - The schema ID the artifact must carry (if applicable) 
  - All required fields, with their derivation sources

For each declared output:
- Cross-reference against `manifest.compile.yaml` `artifact_registry` to confirm the path is a registered artifact
- Confirm the producing phase/node is consistent with the agent invoking this skill
- Confirm `run_id` is required in the output (applies to all canonical Tier 4 and Tier 5 artifacts)

### Step 5 — Implement execution logic

For each skill, write the execution specification body. This is the step that defines *what the skill does*, expressed as a precise, ordered sequence of operations:

1. Input validation sequence (per §4.3)
2. Core processing logic — the bounded operation the skill performs
3. Output construction — field-by-field, with derivation source for each field
4. Conformance stamping — `schema_id`, `run_id`, status fields
5. Write sequence — in what order artifacts are written, and to what paths

The execution specification must be:
- **Deterministic:** same inputs → same outputs; no hidden state
- **Bounded:** no reads outside `reads_from`, no writes outside `writes_to`
- **Complete:** every field in every output artifact must be specified; no fields may be left to inference at runtime
- **Traceable:** for each output field whose value derives from a source artifact, the source artifact and field path must be named

The specification must not delegate core logic back to an LLM as "reason about the inputs and produce an output." It must prescribe the operations. Where semantic judgment is genuinely required (e.g., `concept-alignment-check` evaluating vocabulary alignment), the specification must define:
- the input elements being compared
- the criteria for each status value (Confirmed/Inferred/Assumed/Unresolved)
- what constitutes a gap or mismatch
- how the output represents the judgment result

### Step 6 — Enforce constitutional constraints

For each skill, revisit every constraint in its `constitutional_constraints` and implement explicit enforcement logic:

- Map each constraint to a specific decision point in the execution logic
- Define the exact failure condition that triggers enforcement
- Specify the failure output (decision log entry, SkillResult failure, or halt)
- Confirm the enforcement is a **hard failure**, not a warning

For constraints that are categorical prohibitions (e.g., "must not invent", "must not generate budget figures", "must not overwrite validated checkpoints"), the enforcement must be an unconditional branch that halts execution if the prohibited condition is detected.

Cross-check all constraints against CLAUDE.md §13 (Forbidden Actions and Anti-Patterns) to confirm that no constraint is weaker than the constitutional prohibition it operationalizes.

### Step 7 — Implement failure protocol

For each skill, add explicit failure handling for all failure categories defined in §4.8:

| Failure category | Trigger | Required output |
|-----------------|---------|-----------------|
| `MISSING_INPUT` | Required input artifact absent or empty | SkillResult(failure_category="MISSING_INPUT"); no partial write |
| `MALFORMED_ARTIFACT` | Input schema_id mismatch or required field absent | SkillResult(failure_category="MALFORMED_ARTIFACT"); no partial write |
| `CONSTRAINT_VIOLATION` | Constitutional constraint triggered during execution | SkillResult(failure_category="CONSTRAINT_VIOLATION"); write to decision log if write scope permits |
| `INCOMPLETE_OUTPUT` | Skill cannot produce a complete, conformant output | SkillResult(failure_category="INCOMPLETE_OUTPUT"); no partial write to canonical path |
| `CONSTITUTIONAL_HALT` | CLAUDE.md §13 prohibition triggered | SkillResult(failure_category="CONSTITUTIONAL_HALT"); halt immediately; write to decision log if scope permits |

For every failure category:
- The skill must return a `SkillResult` with `status="failure"` and a non-null `failure_reason`
- No artifact must be written to a canonical output path when a failure is declared (unless the canonical path is itself a failure report path such as `validation_reports/` or `decision_log/`)
- The invoking agent receives the failure result and is responsible for logging and halting per its own failure protocol

### Step 8 — Validate outputs against artifact schemas

For each skill that writes a canonical Tier 4 or Tier 5 artifact:
- Re-read `artifact_schema_specification.yaml` for the relevant schema
- Confirm that every `required: true` field is implemented in the output construction specification
- Confirm that `schema_id` is stamped with the exact `schema_id_value` from the specification
- Confirm that `run_id` propagation is implemented
- Confirm that `artifact_status` is left absent at write time (runner-stamped post-gate per §4.4)
- Confirm that no output field is populated from outside the skill's declared `reads_from`

For skills that write to `validation_reports/` or `decision_log/`: confirm the output structure conforms to the validation status vocabulary (§4.7).

### Step 9 — Review against CLAUDE.md

For each completed skill file:
- Re-read CLAUDE.md §13 (Forbidden Actions and Anti-Patterns)
- Confirm no generated skill violates any prohibition
- Confirm no `writes_to` path is outside the skill's catalog-declared scope
- Confirm no `constitutional_constraint` from the catalog has been softened or omitted
- Confirm the skill does not invoke another skill, invoke an agent, or evaluate a gate
- Confirm the skill does not generate, estimate, or approximate budget figures (§13 / CLAUDE.md §8)
- Confirm no Phase 8 skill touches budget-dependent content without confirming Phase 7 gate passage (CLAUDE.md §13.4)
- Flag any conflict for human review; do not silently resolve

### Step 10 — Produce validation checklist

After all skill files are complete, produce a validation checklist at `.claude/skills/validation_checklist.md` containing a row per skill confirming:

| Column | Check |
|--------|-------|
| front_matter_complete | All front matter fields populated from skill_catalog.yaml without expansion |
| inputs_bound | Every reads_from path resolved to specific artifacts with extraction spec |
| outputs_bound | Every writes_to path resolved to specific artifacts with field spec |
| schema_compliant | For canonical artifacts: schema_id, run_id, required fields all specified |
| constraints_enforced | Every constitutional_constraint maps to a hard failure condition |
| failure_protocol | All five failure categories handled |
| no_scheduler_coupling | Skill does not call another skill, agent, or scheduler |
| no_cross_tier_violation | No reads or writes outside declared scope |
| claude_md_reviewed | CLAUDE.md §13 checked; no violations |
| skill_runtime_contract_referenced | File references skill_runtime_contract.md |

For each skill marked incomplete on any column, a specific gap description is required. No cell may be left empty or marked "N/A" without a written justification.

---

## 8. Skill Catalog — Complete List

The following 19 skills are defined in `skill_catalog.yaml` and constitute the complete implementation target set. No additional skills may be invented. No skill may be removed without amending `skill_catalog.yaml`.

| skill_id | Used by agent(s) | Writes to |
|----------|-----------------|-----------|
| `call-requirements-extraction` | `call_analyzer` | `docs/tier2b_topic_and_call_sources/extracted/` |
| `evaluation-matrix-builder` | `call_analyzer`, `instrument_schema_resolver` | `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/` |
| `instrument-schema-normalization` | `instrument_schema_resolver`, `proposal_writer` | `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` |
| `topic-scope-check` | `call_analyzer`, `concept_refiner` | `docs/tier4_orchestration_state/decision_log/` |
| `concept-alignment-check` | `concept_refiner` | `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/`, `docs/tier4_orchestration_state/decision_log/` |
| `work-package-normalization` | `wp_designer` | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` |
| `wp-dependency-analysis` | `dependency_mapper`, `wp_designer` | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` |
| `milestone-consistency-check` | `gantt_designer`, `wp_designer`, `implementation_architect` | `docs/tier4_orchestration_state/validation_reports/` |
| `impact-pathway-mapper` | `impact_architect` | `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/` |
| `dissemination-exploitation-communication-check` | `impact_architect` | `docs/tier4_orchestration_state/validation_reports/` |
| `governance-model-builder` | `implementation_architect` | `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/` |
| `risk-register-builder` | `implementation_architect` | `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/` |
| `budget-interface-validation` | `budget_interface_coordinator`, `budget_gate_validator` | `docs/integrations/lump_sum_budget_planner/validation/`, `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/` |
| `proposal-section-traceability-check` | `proposal_writer`, `revision_integrator`, `traceability_auditor` | `docs/tier4_orchestration_state/validation_reports/` |
| `evaluator-criteria-review` | `evaluator_reviewer`, `revision_integrator` | `docs/tier5_deliverables/review_packets/` |
| `constitutional-compliance-check` | `compliance_validator`, `call_analyzer`, `concept_refiner`, `proposal_writer`, `revision_integrator`, `budget_gate_validator` | `docs/tier4_orchestration_state/validation_reports/`, `docs/tier4_orchestration_state/decision_log/` |
| `gate-enforcement` | `call_analyzer`, `wp_designer`, `gantt_designer`, `impact_architect`, `implementation_architect`, `budget_gate_validator`, `proposal_writer`, `revision_integrator` | `docs/tier4_orchestration_state/phase_outputs/`, `docs/tier4_orchestration_state/decision_log/` |
| `decision-log-update` | `concept_refiner`, `wp_designer`, `gantt_designer`, `impact_architect`, `implementation_architect`, `budget_gate_validator`, `revision_integrator`, `state_recorder`, `compliance_validator`, `traceability_auditor` | `docs/tier4_orchestration_state/decision_log/` |
| `checkpoint-publish` | `revision_integrator`, `state_recorder` | `docs/tier4_orchestration_state/checkpoints/` |

---

## 9. Non-Goals

The following are explicitly outside the scope of the skill implementation layer. No skill file, runtime contract, or skill registry entry may implement or imply any of the following.

**9.1 Skills do not orchestrate workflow.**
Skills do not determine phase sequencing, edge traversal, or node dispatch order. Workflow orchestration belongs exclusively to the DAG scheduler via `manifest.compile.yaml`.

**9.2 Skills do not evaluate gates.**
Gate evaluation is performed by the DAG scheduler after the agent completes and its output artifacts are written. The `gate-enforcement` skill writes gate evidence to Tier 4; the scheduler reads that evidence and evaluates the gate. The skill never calls an evaluation function or stamps a gate as passed.

**9.3 Skills do not control DAG execution.**
Skills may not call `run_node()`, `evaluate_gate()`, `halt_dag()`, or any equivalent scheduler primitive. They have no access to the scheduler's execution state.

**9.4 Skills do not generate budget values.**
No skill may compute, estimate, approximate, or invent a budget figure. The `budget-interface-validation` skill validates conformance of an externally supplied budget; it does not generate any figure within that budget. This prohibition is unconditional (CLAUDE.md §8.1, §8.3, §13.2).

**9.5 Skills do not modify Tier structure.**
Skills may not add, remove, or restructure Tier 1, Tier 2A, or Tier 2B source documents. They extract from source documents and write to declared paths; they do not alter the documents they read.

**9.6 Skills do not invent artifacts.**
Skills may not write to artifact paths not declared in their `writes_to` in `skill_catalog.yaml`. A new artifact path requires amendment of both `skill_catalog.yaml` and `manifest.compile.yaml` before any skill may write to it.

**9.7 Skills do not re-interpret constitutional authority.**
A skill definition does not redefine phase meanings, tier meanings, gate logic, or constitutional constraints. CLAUDE.md governs all of these without exception.

---

## 10. Integration with DAG Scheduler

### 10.1 Execution Separation

The DAG scheduler and the skill layer are separated by the agent layer. This separation is unconditional. The scheduler never calls a skill directly.

The call chain is:
```
DAG scheduler
  invokes: agent (via node_registry agent field in manifest.compile.yaml)
    agent invokes: skill(s) (via skills list in node_registry entry)
      skill writes: artifact(s) (to paths in skill's writes_to)
        DAG scheduler evaluates: gate (on written artifacts via gate_registry predicates)
```

### 10.2 Scheduler Contract

The DAG scheduler's responsibilities are defined in `runner/dag_scheduler.py` and `manifest.compile.yaml`. They do not include skill invocation. Any change to the scheduler contract requires a separate plan and explicit human instruction. No skill file may alter, extend, or depend on undocumented scheduler behavior.

### 10.3 Artifact-Mediated Coordination

The only communication channel between a skill and the DAG scheduler is the artifact written to `docs/`. The scheduler reads gate predicates against these artifacts. The skill does not "tell" the scheduler anything; the scheduler reads what was written. This means:

- A skill that writes a complete, schema-conformant artifact has fulfilled its role regardless of gate outcome
- A skill that fails to write a required artifact causes a gate failure by omission — not by declaration
- A skill that writes a malformed artifact causes a `MALFORMED_ARTIFACT` predicate failure — not by declaration

### 10.4 run_id Binding

The DAG scheduler assigns a `run_id` at run invocation. It is passed through the call chain:

```
scheduler assigns run_id
  → passes to agent at node invocation
    → agent passes to each skill invocation (via inputs dict or explicit parameter)
      → skill stamps run_id on every canonical artifact it writes
```

Skills must not generate or modify `run_id`. They receive it and propagate it.

### 10.5 artifact_status Lifecycle

`artifact_status` is a runner-managed field on canonical Tier 4 and Tier 5 artifacts. The lifecycle is:

1. Skill writes artifact — `artifact_status` field is **absent**
2. Agent completes execution — returns control to scheduler
3. Scheduler calls `evaluate_gate()` on the node's exit gate
4. Gate passes → scheduler stamps `artifact_status: "valid"` on the canonical artifact
5. Gate fails → scheduler stamps `artifact_status: "invalid"` on the canonical artifact

Skills must not write `artifact_status`. An artifact written with `artifact_status: "valid"` by a skill is constitutionally invalid — the field may only be stamped by the scheduler.

### 10.6 Node Registry Skill Usage

The `manifest.compile.yaml` `node_registry` `skills` list for each node defines the complete set of skills the agent executing that node must invoke. This list is the binding specification. Skills not listed in a node's `skills` entry must not be invoked by that node's agent during normal phase execution (cross-phase skills such as `constitutional-compliance-check` and `decision-log-update` are invocable more broadly, per their `used_by_agents` declarations).

---

## 11. Skill Quick Reference

| skill_id | Phase(s) | Purpose (abbreviated) | Failure category if absent output |
|----------|---------|----------------------|-----------------------------------|
| `call-requirements-extraction` | 1 | Extract topic requirements from Tier 2B sources | INCOMPLETE_OUTPUT |
| `evaluation-matrix-builder` | 1 | Build evaluation matrix from eval form + priority weights | INCOMPLETE_OUTPUT |
| `instrument-schema-normalization` | 1, 3 | Resolve instrument type to section schema | MISSING_INPUT or CONSTRAINT_VIOLATION |
| `topic-scope-check` | 1, 2 | Verify concept/section is within Tier 2B scope | INCOMPLETE_OUTPUT |
| `concept-alignment-check` | 2 | Check concept vocabulary against expected outcomes | INCOMPLETE_OUTPUT |
| `work-package-normalization` | 3 | Normalize WP structure to required elements | INCOMPLETE_OUTPUT |
| `wp-dependency-analysis` | 3 | Produce dependency DAG; flag cycles | INCOMPLETE_OUTPUT |
| `milestone-consistency-check` | 3, 4, 6 | Verify milestones against task schedule | INCOMPLETE_OUTPUT |
| `impact-pathway-mapper` | 5 | Map outputs to call expected impacts | INCOMPLETE_OUTPUT |
| `dissemination-exploitation-communication-check` | 5 | Verify DEC plans against instrument and call requirements | INCOMPLETE_OUTPUT |
| `governance-model-builder` | 6 | Build governance model from Tier 3 consortium data | INCOMPLETE_OUTPUT |
| `risk-register-builder` | 6 | Populate risk register from Tier 3 risk seeds | INCOMPLETE_OUTPUT |
| `budget-interface-validation` | 7 | Validate budget request/response against interface contract | CONSTITUTIONAL_HALT if budget estimated |
| `proposal-section-traceability-check` | 8a, 8b, 8c, 8d | Verify claim traceability to Tier 1–4 sources | INCOMPLETE_OUTPUT |
| `evaluator-criteria-review` | 8c, 8d | Assess content against evaluation criteria | INCOMPLETE_OUTPUT |
| `constitutional-compliance-check` | cross-phase | Check outputs against CLAUDE.md §13 prohibitions | CONSTITUTIONAL_HALT |
| `gate-enforcement` | 1, 3, 4, 5, 6, 7, 8a–8d | Write gate evidence; declare pass or failure | CONSTITUTIONAL_HALT if fabricated |
| `decision-log-update` | cross-phase | Write durable decision record to Tier 4 | MISSING_INPUT (log path not writable) |
| `checkpoint-publish` | 8d, cross-phase | Write formal checkpoint to Tier 4 checkpoints/ | CONSTRAINT_VIOLATION if prior checkpoint exists |

---

## 12. Validation Checklist (Required Post-Implementation)

After all 19 skill files and `skill_runtime_contract.md` are complete, produce `.claude/skills/validation_checklist.md` with the following structure:

| skill_id | front_matter_complete | inputs_bound | outputs_bound | schema_compliant | constraints_enforced | failure_protocol | no_scheduler_coupling | no_cross_tier_violation | claude_md_reviewed | contract_referenced |
|----------|----------------------|-------------|--------------|-----------------|---------------------|-----------------|----------------------|------------------------|-------------------|-------------------|
| `call-requirements-extraction` | | | | | | | | | | |
| `evaluation-matrix-builder` | | | | | | | | | | |
| `instrument-schema-normalization` | | | | | | | | | | |
| `topic-scope-check` | | | | | | | | | | |
| `concept-alignment-check` | | | | | | | | | | |
| `work-package-normalization` | | | | | | | | | | |
| `wp-dependency-analysis` | | | | | | | | | | |
| `milestone-consistency-check` | | | | | | | | | | |
| `impact-pathway-mapper` | | | | | | | | | | |
| `dissemination-exploitation-communication-check` | | | | | | | | | | |
| `governance-model-builder` | | | | | | | | | | |
| `risk-register-builder` | | | | | | | | | | |
| `budget-interface-validation` | | | | | | | | | | |
| `proposal-section-traceability-check` | | | | | | | | | | |
| `evaluator-criteria-review` | | | | | | | | | | |
| `constitutional-compliance-check` | | | | | | | | | | |
| `gate-enforcement` | | | | | | | | | | |
| `decision-log-update` | | | | | | | | | | |
| `checkpoint-publish` | | | | | | | | | | |

Each cell must be populated: `pass`, `fail: <reason>`, or `N/A: <justification>`. A checklist with empty cells is not complete and does not satisfy Step 10.

---

## 13. DAG Scheduler Context for Skill Implementors

The following runtime facts govern every skill implementation:

- **The scheduler never calls skills.** Skills are called only by agents. A skill that assumes direct scheduler invocation is architecturally incorrect.
- **`run_id` is passed through the agent.** The skill receives it as a parameter and propagates it to every canonical artifact.
- **`artifact_status` is set by the scheduler, not by skills.** Absent at write time means "not yet gate-evaluated." Skills must never write this field.
- **Gate failure is a correct output.** A skill that writes a gate failure record to Tier 4 has done its job correctly. Gate failure by evidence (absent artifact, failed predicate) is also correct. Neither is an error state.
- **The scheduler reads `run_summary.json` for orchestration state.** Skills must not write to this file. It is owned by `runner/dag_scheduler.py`.
- **Reruns are deterministic from documented inputs.** If a skill is invoked again on the same inputs, it must produce the same output. It may not rely on memory of a prior run.
- **Skill writes are the only mechanism for communicating with the scheduler.** There is no callback, no signal, no event. If an artifact is not written, the scheduler receives no information about the skill's execution.

---

*Skill implementation plan. Effective from creation. Amendments require explicit human instruction. No amendment may expand skill scope, weaken constitutional constraints, introduce scheduler coupling, or relax any constitutional prohibition from CLAUDE.md.*
