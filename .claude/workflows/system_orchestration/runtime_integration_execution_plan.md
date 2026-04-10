# Runtime Integration — Execution Plan

**Authoritative source:** `runtime_integration_plan.md` §13 (Dependency-Ordered Implementation Sequence)
**Constitutional authority:** Subordinate to `CLAUDE.md`. This plan operationalizes `runtime_integration_plan.md`; it does not override it.
**Plan status:** Ready for execution.

---

## Ordering Provenance

The 9 steps below correspond 1:1 to the 9 ordered items in `runtime_integration_plan.md` §13:

| §13 item | Execution step |
|----------|---------------|
| context initialization | Step 1 |
| runtime contract definitions | Step 2 |
| loader / resolver layer | Step 3 |
| skill runtime | Step 4 |
| agent runtime | Step 5 |
| scheduler integration | Step 6 |
| run summary extension | Step 7 |
| tests | Step 8 |
| end-to-end vertical slice scenarios | Step 9 |

No steps have been reordered, merged, split, or skipped. Each step depends only on prior steps.

---

## Runtime Execution Model (Binding Clarification)

The 16 agent `.md` files in `.claude/agents/` and the 19 skill `.md` files in `.claude/skills/` are **specifications, not executable code**. There is no interpreter that reads a Markdown execution specification and deterministically executes its steps. These files define what each agent or skill must do, what it reads, what it writes, what constraints it enforces, and how it fails — but the entity that performs the reasoning is **Claude**, invoked via the Claude API.

This clarification is architecturally binding for Steps 4 and 5.

### Skill runtime (`run_skill()`) — Claude API adapter layer

`run_skill()` is not a Markdown interpreter. It is a **Claude API adapter** that:

1. **Loads** the skill execution specification from `.claude/skills/<skill_id>.md`.
2. **Resolves** the skill's declared canonical inputs from `reads_from` paths, reading artifact content from disk.
3. **Assembles** a structured prompt comprising: the skill spec, the canonical input content, the `run_id`, the skill's `constitutional_constraints`, and output schema requirements from `artifact_schema_specification.yaml`.
4. **Invokes** the Claude API with the assembled prompt.
5. **Parses** the structured response (JSON) from Claude's output.
6. **Validates** the parsed output against the expected schema (`schema_id`, required fields, `run_id` present, `artifact_status` absent).
7. **Writes** the validated output atomically to the canonical path (temp file → validate → move).
8. **Returns** a `SkillResult` reflecting success or failure at any stage.

If Claude's response is malformed, incomplete, or violates a constitutional constraint, `run_skill()` returns a failure `SkillResult` — it does not retry or improvise.

### Agent runtime (`run_agent()`) — orchestration adapter layer

`run_agent()` is an **orchestration adapter** that:

1. **Loads** the agent definition from `.claude/agents/<agent_id>.md` and the prompt spec from `.claude/agents/prompts/<agent_id>_prompt_spec.md`.
2. **Resolves** the agent's canonical inputs from `reads_from` paths.
3. **Sequences** skill invocations through `run_skill()` (Step 4), passing context between invocations where one skill's output is another's input.
4. **Manages** failure handling: halts immediately on `CONSTITUTIONAL_HALT`; evaluates whether remaining skills can still produce required outputs on other failures.
5. **Determines** `can_evaluate_exit_gate` by inspecting whether all canonical artifacts required by the node's exit gate have been durably written.
6. **Returns** an `AgentResult` reflecting the consolidated outcome.

The agent runtime does not perform domain reasoning itself. It orchestrates the Claude API calls (via `run_skill()`) and manages the mechanical concerns: input resolution, output validation, failure propagation, and gate-readiness determination.

### Architectural precedent

This pattern is already implemented in `runner/semantic_dispatch.py`, where `invoke_agent()` reads artifacts from disk, constructs system/user prompts embedding artifact content and a constitutional rule, calls the Claude API (`claude-sonnet-4-6`), and parses the JSON response. The skill and agent runtimes follow the same pattern at runtime-integration scope — the difference is that skill/agent invocations produce canonical Tier 4/Tier 5 artifacts (not just predicate results) and are orchestrated within the `_dispatch_node()` call chain.

### What this means for implementation

- "Execute the skill's core processing logic" (Step 4) means: send the skill spec + inputs to Claude and parse the response.
- "Execute the agent body" (Step 5) means: sequence skill invocations via `run_skill()`, each of which calls Claude.
- The runtime modules contain prompt assembly, API invocation, response parsing, validation, and I/O logic — not domain knowledge.

---

## Step 1 — Context Initialization

**Read first:**
- `runtime_integration_plan.md` — Mandatory source reading (lines 22–69), §1 (Problem Statement), §2 (Invariants), §3 (Runtime Layers)
- `CLAUDE.md` — §3 (Authority Hierarchy), §6 (Workflow Execution Model), §13 (Forbidden Actions), §16 (Agent Derivation)
- `runner/run_context.py` — `NODE_STATES`, `RunContext`, `set_node_state()` current signature
- `runner/dag_scheduler.py` — `_dispatch_node()` (lines 1028–1127), `RunSummary` (lines 131–208)
- `runner/paths.py` — `find_repo_root()`, path constants
- `runner/manifest_reader.py` — `ManifestReader` class, `get_predicate_refs()` pattern
- `.claude/workflows/system_orchestration/manifest.compile.yaml` — node_registry, artifact_registry
- `.claude/agents/node_body_contract.md` — §3 (contract requirements)
- `.claude/skills/skill_runtime_contract.md` — §4–6 (runtime contract, invocation model, SkillResult)

**Target files:**
- No files created or modified.

**Goal:**
Confirm all 19 mandatory sources from `runtime_integration_plan.md` are present and readable. Confirm no structural conflicts exist between the current `runner/` implementation and the integration plan's contracts. This is a read-only verification step.

**Constraints:**
- Do not create any files.
- Do not modify any existing files.
- Do not proceed to Step 2 if any mandatory source is absent.

**Implementation requirements:**
- Verify every file listed in `runtime_integration_plan.md` mandatory sources 1–19 exists at the expected path.
- Verify `NODE_STATES` in `runner/run_context.py` matches the closed set in §2: `pending`, `running`, `released`, `blocked_at_entry`, `blocked_at_exit`, `deterministic_pass_semantic_pending`, `hard_block_upstream`.
- Verify `set_node_state()` in `runner/run_context.py` currently accepts `(node_id: str, state: str)` — confirming the extension point for §9.4.
- Verify `_dispatch_node()` in `runner/dag_scheduler.py` currently has the entry-gate → exit-gate flow with no agent-body call — confirming the insertion point for §9.2 step 3.
- Verify `RunSummary` in `runner/dag_scheduler.py` does not yet have `node_failure_details` — confirming the extension point for §9.3.

**Output:**
All mandatory sources confirmed present. Extension points in `run_context.py`, `dag_scheduler.py` confirmed structurally compatible. No blockers identified.

**Verification:**
- All 19 source file paths resolve to existing files.
- `NODE_STATES` has exactly 7 members matching the §2 invariant.
- `set_node_state()` takes exactly 2 positional args.
- `_dispatch_node()` contains no `run_node_body` or `AgentResult` references.
- `RunSummary` does not contain `node_failure_details`.

---

## Step 2 — Runtime Contract Definitions

**Read first:**
- `runtime_integration_plan.md` — §4 (Runtime Contracts: §4.1 AgentResult, §4.2 NodeExecutionResult, §4.3 SkillResult), §10 (Failure Semantics: §10.1 failure_origin model)
- `.claude/skills/skill_runtime_contract.md` — §6.2 (SkillResult definition)
- `runner/run_context.py` — current data structures

**Target files:**
- `runner/runtime_models.py` (new)

**Goal:**
Define all runtime data types required by the integration layer as frozen dataclasses in a single module. These types are consumed by every subsequent step.

**Constraints:**
- No business logic — pure data definitions only.
- All field names, types, and allowed values must match `runtime_integration_plan.md` §4 exactly.
- `failure_origin` allowed values: `"entry_gate"`, `"agent_body"`, `"exit_gate"`, `None`.
- `failure_category` allowed values for `SkillResult`: `MISSING_INPUT`, `MALFORMED_ARTIFACT`, `CONSTRAINT_VIOLATION`, `INCOMPLETE_OUTPUT`, `CONSTITUTIONAL_HALT`.
- `failure_category` allowed values for `AgentResult`: all of the above plus `SKILL_FAILURE`, `AGENT_EXECUTION_ERROR`.
- No new node states. No gate evaluation logic. No scheduler coupling.

**Implementation requirements:**

1. `SkillResult` — frozen dataclass:
   - `status: str` — `"success"` or `"failure"`
   - `outputs_written: list[str]` — paths relative to repo_root
   - `validation_report: str | None`
   - `failure_reason: str | None`
   - `failure_category: str | None`

2. `SkillInvocationRecord` — frozen dataclass:
   - `skill_id: str`
   - `status: str` — `"success"` or `"failure"`
   - `failure_reason: str | None`
   - `failure_category: str | None`
   - `outputs_written: list[str]`

3. `AgentResult` — frozen dataclass:
   - `status: str` — `"success"` or `"failure"`
   - `failure_origin: str` — always `"agent_body"`
   - `failure_reason: str | None`
   - `failure_category: str | None`
   - `can_evaluate_exit_gate: bool`
   - `outputs_written: list[str]`
   - `validation_reports: list[str]`
   - `decision_log_writes: list[str]`
   - `invoked_skills: list[SkillInvocationRecord]`

4. `NodeExecutionResult` — frozen dataclass:
   - `node_id: str`
   - `final_state: str`
   - `failure_origin: str | None` — `"entry_gate"` | `"agent_body"` | `"exit_gate"` | `None`
   - `exit_gate_evaluated: bool`
   - `gate_result: dict | None`
   - `agent_result: AgentResult | None`
   - `failure_reason: str | None`
   - `failure_category: str | None`

5. Constants:
   - `FAILURE_ORIGINS: frozenset[str]` = `{"entry_gate", "agent_body", "exit_gate"}`
   - `SKILL_FAILURE_CATEGORIES: frozenset[str]` = `{"MISSING_INPUT", "MALFORMED_ARTIFACT", "CONSTRAINT_VIOLATION", "INCOMPLETE_OUTPUT", "CONSTITUTIONAL_HALT"}`
   - `AGENT_FAILURE_CATEGORIES: frozenset[str]` = SKILL_FAILURE_CATEGORIES | `{"SKILL_FAILURE", "AGENT_EXECUTION_ERROR"}`

**Output:**
`runner/runtime_models.py` exists with all 4 dataclasses, all constants, and no business logic. Importable from `runner.runtime_models`.

**Verification:**
- All fields match §4.1, §4.2, §4.3 of `runtime_integration_plan.md` exactly.
- `from runner.runtime_models import SkillResult, AgentResult, NodeExecutionResult, SkillInvocationRecord` succeeds.
- Each dataclass is frozen (immutable after construction).
- No imports from `runner.dag_scheduler`, `runner.gate_evaluator`, or `runner.run_context` (zero coupling to existing modules).

---

## Step 3 — Loader / Resolver Layer

**Read first:**
- `runtime_integration_plan.md` — §5 (node_id → agent_id Resolution), §6 (Agent Prompt / Body Execution Model), §7 (Skill Invocation Model — manifest skill list), §11 (Special Cases: n03 sub_agent, n07 pre_gate_agent, Phase 8 proposal_writer)
- `.claude/workflows/system_orchestration/manifest.compile.yaml` — node_registry entries (agent, sub_agent, pre_gate_agent, skills, phase_id fields)
- `runner/manifest_reader.py` — existing `ManifestReader` pattern
- `runner/paths.py` — path constants and resolution

**Target files:**
- `runner/node_resolver.py` (new)

**Goal:**
Implement the resolution layer that maps `node_id` to agent identifiers, skill lists, prompt spec paths, and agent definition paths. This layer reads the manifest and file system but executes no business logic.

**Constraints:**
- Manifest node_registry is the sole authoritative source for node → agent binding (§5).
- Must handle all three agent binding types: `agent` (primary), `sub_agent`, `pre_gate_agent`.
- Must handle Phase 8 nodes where multiple node_ids share the same `agent` (`proposal_writer` for n08a and n08b).
- Must not execute agents, invoke skills, or evaluate gates.
- Must not import `runner.dag_scheduler` or `runner.gate_evaluator`.

**Implementation requirements:**

1. `NodeResolver` class:
   - `__init__(manifest_path: Path, repo_root: Path)` — loads manifest node_registry
   - `resolve_agent_id(node_id: str) -> str` — returns the `agent` field from the node's registry entry; raises `NodeResolverError` if node_id not found
   - `resolve_sub_agent_id(node_id: str) -> str | None` — returns `sub_agent` field or `None`
   - `resolve_pre_gate_agent_id(node_id: str) -> str | None` — returns `pre_gate_agent` field or `None`
   - `resolve_skill_ids(node_id: str) -> list[str]` — returns the `skills` list from the node's registry entry, in manifest order
   - `resolve_phase_id(node_id: str) -> str` — returns the `phase_id` field
   - `agent_definition_path(agent_id: str) -> Path` — returns `repo_root / ".claude" / "agents" / f"{agent_id}.md"`; raises if file does not exist
   - `agent_prompt_spec_path(agent_id: str) -> Path` — returns `repo_root / ".claude" / "agents" / "prompts" / f"{agent_id}_prompt_spec.md"`; raises if file does not exist
   - `node_ids() -> list[str]` — returns all node_ids in manifest registry order

2. `NodeResolverError(Exception)` — raised for missing node_ids or missing agent files.

**Output:**
`runner/node_resolver.py` exists with `NodeResolver` and `NodeResolverError`. All resolution methods return data from the manifest; none execute side effects.

**Verification:**
- `NodeResolver` loaded with the production `manifest.compile.yaml` can resolve all 11 node_ids (`n01_call_analysis` through `n08d_revision`).
- `resolve_sub_agent_id("n03_wp_design")` returns `"dependency_mapper"`.
- `resolve_pre_gate_agent_id("n07_budget_gate")` returns `"budget_interface_coordinator"`.
- `resolve_sub_agent_id("n01_call_analysis")` returns `None`.
- `resolve_skill_ids("n01_call_analysis")` returns the 5 skills listed in the manifest for n01.
- `agent_definition_path("call_analyzer")` returns a path that exists on disk.
- `agent_prompt_spec_path("call_analyzer")` returns a path that exists on disk.

---

## Step 4 — Skill Runtime

**Read first:**
- `runtime_integration_plan.md` — §7 (Skill Invocation Model), §8 (Canonical I/O Resolution, Atomic Canonical Write Rule), §10.2 (Skill → Agent failure propagation)
- `.claude/skills/skill_runtime_contract.md` — §4 (Skill Runtime Contract), §6 (Invocation Model: run_skill → SkillResult)
- `.claude/workflows/system_orchestration/skill_catalog.yaml` — reads_from, writes_to, constitutional_constraints per skill
- `.claude/workflows/system_orchestration/artifact_schema_specification.yaml` — schema_id_value, required fields
- `runner/paths.py` — path resolution
- `runner/runtime_models.py` (from Step 2) — `SkillResult`, `SkillInvocationRecord`

**Target files:**
- `runner/skill_runtime.py` (new)

**Goal:**
Implement the `run_skill()` Claude API adapter that loads a skill specification, assembles prompt context from canonical inputs, invokes Claude, parses the structured response, validates and writes canonical artifacts atomically, and returns a `SkillResult`. See "Runtime Execution Model" section above for the binding clarification that skill `.md` files are specifications executed by Claude, not by an interpreter.

**Constraints:**
- Skills read only from their declared `reads_from` paths in `skill_catalog.yaml`.
- Skills write only to their declared `writes_to` paths in `skill_catalog.yaml`.
- `run_id` must be propagated into every canonical Tier 4/Tier 5 artifact written.
- `artifact_status` must be left absent at write time (runner-stamped post-gate).
- `schema_id` must be stamped on canonical artifacts per `artifact_schema_specification.yaml`.
- Atomic Canonical Write Rule (§8): writes are atomic — no partial artifacts at canonical paths on failure.
- Must not invoke other skills, agents, or the scheduler.
- Must not evaluate gates.
- Must not compute budget figures.

**Implementation requirements:**

1. `run_skill(skill_id: str, run_id: str, repo_root: Path, inputs: dict) -> SkillResult`:

   **Phase A — Load and resolve:**
   - Load the skill execution specification from `.claude/skills/<skill_id>.md` (this is the prompt source, not executable code).
   - Load the skill's `reads_from`, `writes_to`, and `constitutional_constraints` from `skill_catalog.yaml`.
   - Resolve the skill's declared canonical inputs: for each `reads_from` path, read the artifact content from disk into `inputs`.
   - Validate all declared inputs (presence, non-empty, schema conformance where applicable).
   - On input validation failure: return `SkillResult(status="failure", failure_category="MISSING_INPUT" or "MALFORMED_ARTIFACT")` without invoking Claude.

   **Phase B — Prompt assembly:**
   - Construct a structured prompt comprising:
     - The skill execution specification (full `.md` content).
     - The canonical input artifacts (JSON content of each resolved input).
     - The `run_id` to stamp on outputs.
     - The output schema requirements: `schema_id` value, required fields, and field types from `artifact_schema_specification.yaml`.
     - The skill's `constitutional_constraints` (verbatim from `skill_catalog.yaml`).
     - An explicit instruction to return a structured JSON response matching the expected output schema.

   **Phase C — Claude API invocation:**
   - Call the Claude API with the assembled prompt. Follow the same invocation pattern as `runner/semantic_dispatch.py` `invoke_agent()`: system prompt + user prompt, model selection, JSON response parsing.
   - On API failure (network error, timeout, rate limit): return `SkillResult(status="failure", failure_category="AGENT_EXECUTION_ERROR")`.

   **Phase D — Response parsing and validation:**
   - Parse Claude's response as structured JSON.
   - On parse failure (non-JSON, non-dict): return `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT")`.
   - Validate the parsed output against the expected schema: confirm `schema_id` is present and correct, all `required: true` fields are populated, `run_id` matches the propagated value, `artifact_status` is absent.
   - On schema validation failure: return `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT")`.
   - Check for constitutional constraint violations in the response (e.g., fabricated project facts, budget figures). On violation: return `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT")`.

   **Phase E — Atomic canonical write:**
   - Write the validated JSON to a temp file in the same directory as the canonical path.
   - Perform a final validation read-back from the temp file.
   - Atomically move the temp file to the canonical path.
   - On write failure: clean up temp file, return `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT")`. The canonical path is untouched.

   **Phase F — Return:**
   - On success: return `SkillResult(status="success", outputs_written=[<canonical paths written>])`.

2. `SkillRuntimeError(Exception)` — raised for infrastructure failures (file I/O errors outside the normal failure protocol).

3. Internal helper: `_validate_skill_inputs(skill_id: str, reads_from: list[str], repo_root: Path) -> list[str]` — returns list of validation errors; empty list means all inputs valid.

4. Internal helper: `_atomic_write(content: dict, canonical_path: Path) -> None` — writes JSON to temp file in the same directory, validates, atomically moves to canonical path. On failure, temp file is cleaned up and canonical path is untouched.

5. Internal helper: `_assemble_skill_prompt(skill_spec: str, inputs: dict[str, Any], run_id: str, output_schema: dict, constraints: list[str]) -> tuple[str, str]` — returns `(system_prompt, user_prompt)` for Claude API invocation.

6. Internal helper: `_validate_skill_output(response: dict, expected_schema_id: str, run_id: str, required_fields: list[str]) -> list[str]` — returns list of validation errors; empty list means output is valid.

**Output:**
`runner/skill_runtime.py` exists with `run_skill()`, `SkillRuntimeError`, and internal helpers. `run_skill()` is a Claude API adapter that returns a `SkillResult` for every code path (success or failure at any phase). No partial writes occur at canonical paths on failure. Domain reasoning is performed by Claude, not by this module.

**Verification:**
- `run_skill()` with valid inputs and a successful Claude response produces `SkillResult(status="success")` and a written artifact at the canonical path.
- `run_skill()` with a missing input produces `SkillResult(status="failure", failure_category="MISSING_INPUT")` without calling the Claude API.
- `run_skill()` with a malformed Claude response (non-JSON) produces `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT")` and no artifact at the canonical path.
- `run_skill()` with a valid Claude response that fails schema validation produces `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT")` and no artifact at the canonical path.
- Written artifacts contain `schema_id` and `run_id` fields; do not contain `artifact_status`.
- No imports from `runner.dag_scheduler` or `runner.gate_evaluator`.

---

## Step 5 — Agent Runtime

**Read first:**
- `runtime_integration_plan.md` — §6 (Agent Prompt / Body Execution Model), §7 (Skill Invocation Model — ordering, halt-on-failure, merge semantics), §8 (Canonical I/O Resolution), §10.2 (failure propagation), §10.3 (CONSTITUTIONAL_HALT propagation), §11 (Special Cases)
- `.claude/agents/node_body_contract.md` — §3 (all contract requirements: identity, scope, must_not, canonical I/O, skills, gate awareness, failure behaviour, decision-log)
- `.claude/workflows/system_orchestration/agent_catalog.yaml` — reads_from, writes_to, must_not per agent
- `runner/runtime_models.py` (from Step 2) — `AgentResult`, `SkillInvocationRecord`
- `runner/node_resolver.py` (from Step 3) — `NodeResolver`
- `runner/skill_runtime.py` (from Step 4) — `run_skill()`

**Target files:**
- `runner/agent_runtime.py` (new)

**Goal:**
Implement the `run_agent()` orchestration adapter that loads agent and prompt specifications, sequences skill invocations through the `run_skill()` Claude API adapter (Step 4), manages context passing between skill invocations, handles failures, determines `can_evaluate_exit_gate`, and returns an `AgentResult`. See "Runtime Execution Model" section above for the binding clarification that agent `.md` files are specifications, and domain reasoning is performed by Claude through `run_skill()` calls.

**Constraints:**
- Agent reads only from its declared `reads_from` paths in `agent_catalog.yaml`.
- Agent writes only to its declared `writes_to` paths in `agent_catalog.yaml`.
- Skill invocation order: determined by the agent's execution specification (prompt spec), not by manifest skill list order. The manifest skill list is the authoritative set; the agent controls sequencing within that set.
- On `CONSTITUTIONAL_HALT` from any skill: agent must halt immediately, return `AgentResult(status="failure", failure_category="CONSTITUTIONAL_HALT", can_evaluate_exit_gate=False)`.
- On other skill failures: agent decides per its contract whether to halt or continue. If it cannot produce complete canonical outputs, it must set `can_evaluate_exit_gate=False`.
- `can_evaluate_exit_gate` must be `True` only when all canonical artifacts required by the node's exit gate have been durably written, are complete, and are schema-valid.
- Must not invoke the scheduler or evaluate gates.
- Must not call other agents (except: n03 primary agent may coordinate with sub_agent within the same node body execution, and n07 pre_gate_agent runs before the primary agent within the same node context — see §11).
- The agent runtime does not perform domain reasoning itself. It orchestrates Claude API calls (via `run_skill()`) and manages mechanical concerns: spec loading, input resolution, skill sequencing, context passing, failure propagation, and gate-readiness determination.

**Implementation requirements:**

1. `run_agent(agent_id: str, node_id: str, run_id: str, repo_root: Path, *, manifest_path: Path, skill_ids: list[str], phase_id: str, sub_agent_id: str | None = None, pre_gate_agent_id: str | None = None) -> AgentResult`:

   **Phase A — Spec loading:**
   - Load the agent definition from `.claude/agents/<agent_id>.md`. This provides: `reads_from`, `writes_to`, `invoked_skills`, `exit_gate`, `must_not` constraints.
   - Load the prompt spec from `.claude/agents/prompts/<agent_id>_prompt_spec.md`. This provides: the skill invocation ordering (reading instructions, reasoning steps, output construction rules), which determines the sequence in which `run_skill()` calls are made.
   - The agent definition is the structural authority (what the agent may do). The prompt spec is the sequencing authority (in what order and with what reasoning steps).

   **Phase B — Canonical input resolution:**
   - Resolve all canonical inputs from the agent's `reads_from` paths. For each path, read artifact content from disk.
   - Validate presence and non-emptiness of required inputs.
   - On missing mandatory input: return `AgentResult(status="failure", failure_category="MISSING_INPUT", can_evaluate_exit_gate=False)` without invoking any skills.

   **Phase C — Pre-gate agent (n07 special case):**
   - If `pre_gate_agent_id` is not None (n07 case): invoke the pre-gate agent's skills first via `run_skill()` for each skill in the pre-gate agent's skill set. The pre-gate agent (budget_interface_coordinator) produces the budget request artifact before the primary agent (budget_gate_validator) validates the budget response.
   - Collect `SkillInvocationRecord` for each pre-gate skill invocation.
   - On pre-gate skill failure: evaluate whether the primary agent can still proceed.

   **Phase D — Skill invocation sequencing:**
   - For each skill_id in the dependency-ordered sequence derived from the prompt spec:
     - Assemble the skill's `inputs` dict from: the agent's resolved canonical inputs (Phase B) plus any artifacts written by prior skill invocations in this agent execution.
     - Call `run_skill(skill_id, run_id, repo_root, inputs)` → `SkillResult`.
     - Record a `SkillInvocationRecord` for this invocation.
     - On `CONSTITUTIONAL_HALT`: halt immediately. Do not invoke remaining skills.
     - On other failure: evaluate whether remaining skills can still produce required canonical outputs. If not, halt. If yes, continue (the agent may still produce partial outputs that are sufficient for the exit gate).
   - If `sub_agent_id` is not None (n03 case): invoke sub-agent's skills (e.g., `wp-dependency-analysis`) at the point in the sequence where the primary agent's WP structure output is available as input.

   **Phase E — Gate-readiness determination:**
   - After all skill invocations complete (or the agent halts due to failure):
     - Call `_determine_can_evaluate_exit_gate()` to inspect whether all canonical artifacts required by the node's exit gate exist at their canonical paths, are non-empty, and are schema-valid.
     - This is a file-system inspection, not an optimistic assumption. The agent runtime checks actual written artifacts, not the `outputs_written` list from skill results.

   **Phase F — Return:**
   - Consolidate all `SkillInvocationRecord`s, all `outputs_written` paths, all `validation_reports` paths, and all `decision_log_writes` paths.
   - Return `AgentResult` with `failure_origin="agent_body"` (always), `can_evaluate_exit_gate` from Phase E, and all other fields populated.

2. `AgentRuntimeError(Exception)` — raised for infrastructure failures.

3. Internal helper: `_determine_can_evaluate_exit_gate(node_id: str, outputs_written: list[str], repo_root: Path) -> bool` — checks that all artifacts required by the node's exit gate exist at their canonical paths and are non-empty JSON. Uses the artifact_registry from `manifest.compile.yaml` to determine which artifacts the exit gate's predicates evaluate (via `produced_by` and `gate_dependency` fields).

4. Internal helper: `_resolve_skill_sequence(agent_id: str, skill_ids: list[str], prompt_spec: str) -> list[str]` — derives the dependency-ordered skill invocation sequence from the prompt spec's reasoning steps, constrained to the manifest-declared skill set. Returns skill_ids in execution order.

**Output:**
`runner/agent_runtime.py` exists with `run_agent()`, `AgentRuntimeError`, and internal helpers. `run_agent()` is an orchestration adapter that returns an `AgentResult` for every code path. `failure_origin` is always `"agent_body"`. `can_evaluate_exit_gate` is determined by inspecting written artifacts on disk, not by optimistic assumption. Domain reasoning is performed by Claude through `run_skill()` calls.

**Verification:**
- `run_agent()` with all skills succeeding returns `AgentResult(status="success", can_evaluate_exit_gate=True)`.
- `run_agent()` with a skill returning `CONSTITUTIONAL_HALT` returns `AgentResult(status="failure", failure_category="CONSTITUTIONAL_HALT", can_evaluate_exit_gate=False)` and does not invoke subsequent skills.
- `run_agent()` for n03 invokes both `wp_designer` skills and `dependency_mapper` skills via `run_skill()`.
- `run_agent()` for n07 invokes `budget_interface_coordinator` skills before `budget_gate_validator` skills.
- Context passing: a skill's output artifact is available as input to the next skill in the sequence.
- `can_evaluate_exit_gate` is `False` when required artifacts are missing from disk, even if some skills reported success.
- `invoked_skills` list is ordered and complete.
- No imports from `runner.dag_scheduler` or `runner.gate_evaluator`.

---

## Step 6 — Scheduler Integration

**Read first:**
- `runtime_integration_plan.md` — §9 (Scheduler Integration Points: §9.1 sole modification point, §9.2 revised _dispatch_node contract, §9.4 RunContext persistence), §10 (Failure Semantics — all subsections), §2 (closed state machine invariant)
- `runner/dag_scheduler.py` — `_dispatch_node()` (lines 1028–1127), `DAGScheduler.__init__()`
- `runner/run_context.py` — `set_node_state()` (line 229), `RunContext` class, `mark_hard_block_downstream()`
- `runner/gate_evaluator.py` — `evaluate_gate()` signature (must remain unchanged)
- `runner/runtime_models.py` (from Step 2) — `NodeExecutionResult`, `AgentResult`
- `runner/node_resolver.py` (from Step 3) — `NodeResolver`
- `runner/agent_runtime.py` (from Step 5) — `run_agent()`

**Target files:**
- `runner/run_context.py` (modify)
- `runner/dag_scheduler.py` (modify)

**Goal:**
Extend `set_node_state()` with failure metadata keyword arguments (§9.4). Modify `_dispatch_node()` to insert agent-body execution between entry gate and exit gate (§9.2). This is the sole scheduler modification.

**Constraints:**
- No new node states. `NODE_STATES` frozenset is unchanged.
- `set_node_state()` gains optional keyword arguments only; existing calls (2-arg positional) continue to work unchanged.
- `_dispatch_node()` gains one new call (`run_node_body`) and one new conditional branch. The entry-gate and exit-gate code blocks remain structurally identical to the current implementation.
- `evaluate_gate()` is not modified.
- `run()` loop is not modified.
- `ManifestGraph` is not modified.
- `_settle_stalled_nodes()` is not modified.
- HARD_BLOCK propagation logic is preserved identically for both `failure_origin="agent_body"` and `failure_origin="exit_gate"` when the gate is `gate_09_budget_consistency`.

**Implementation requirements:**

1. **`runner/run_context.py` — extend `set_node_state()`:**
   - Add optional keyword arguments: `failure_origin: str | None = None`, `exit_gate_evaluated: bool | None = None`, `failure_reason: str | None = None`, `failure_category: str | None = None`.
   - Store these in a parallel dict `self._manifest["node_failure_details"][node_id]` alongside the state.
   - Add `get_node_failure_details(node_id: str) -> dict | None` — returns the failure details dict or None.
   - Existing 2-arg calls to `set_node_state()` must continue to work (all kwargs default to None).

2. **`runner/dag_scheduler.py` — modify `_dispatch_node()`:**
   - After entry-gate pass (current line ~1090), before exit-gate evaluation (current line ~1092):
     - Instantiate `NodeResolver` (or receive it via `__init__`).
     - Resolve agent_id, sub_agent_id, pre_gate_agent_id, skill_ids, phase_id from node_id.
     - Call `run_agent(agent_id, node_id, self.ctx.run_id, self.repo_root, ...)` → `AgentResult`.
     - If `agent_result.status == "failure"` or `agent_result.can_evaluate_exit_gate == False`:
       - `ctx.set_node_state(node_id, "blocked_at_exit", failure_origin="agent_body", exit_gate_evaluated=False, failure_reason=..., failure_category=...)`
       - If exit_gate_id == `_HARD_BLOCK_GATE`: call `ctx.mark_hard_block_downstream()`, persist.
       - Return `NodeExecutionResult` immediately. Skip exit gate.
     - Otherwise: proceed to exit-gate evaluation (existing code).
   - Exit-gate pass: `ctx.set_node_state(node_id, "released", failure_origin=None, exit_gate_evaluated=True)`.
   - Exit-gate fail: `ctx.set_node_state(node_id, "blocked_at_exit", failure_origin="exit_gate", exit_gate_evaluated=True, ...)`.
   - Entry-gate fail: `ctx.set_node_state(node_id, "blocked_at_entry", failure_origin="entry_gate", exit_gate_evaluated=False)`.
   - `_dispatch_node()` return type changes from `dict` to `NodeExecutionResult`.

3. **`runner/dag_scheduler.py` — `DAGScheduler.__init__()` extension:**
   - Accept `manifest_path` (already present) for `NodeResolver` construction.
   - Construct `NodeResolver` once at init time.

**Output:**
`run_context.py` has extended `set_node_state()` with failure metadata kwargs. `dag_scheduler.py` has a modified `_dispatch_node()` that follows the §9.2 5-step contract exactly. All existing tests continue to pass (existing 2-arg `set_node_state()` calls still work; `_dispatch_node()` return type change may require test updates handled in Step 8).

**Verification:**
- `set_node_state(node_id, "blocked_at_exit")` (existing 2-arg call) still works.
- `set_node_state(node_id, "blocked_at_exit", failure_origin="agent_body", exit_gate_evaluated=False)` persists failure details.
- `get_node_failure_details(node_id)` returns the stored dict.
- `_dispatch_node()` for a node with a successful agent body proceeds to exit gate evaluation.
- `_dispatch_node()` for a node with a failed agent body sets `blocked_at_exit` with `failure_origin="agent_body"` and does NOT call `evaluate_gate()` for the exit gate.
- `_dispatch_node()` for n07 with agent-body failure still triggers `mark_hard_block_downstream()`.
- `NODE_STATES` frozenset is unchanged (still exactly 7 members).

---

## Step 7 — Run Summary Extension

**Read first:**
- `runtime_integration_plan.md` — §9.3 (RunSummary extension: `node_failure_details` schema, classification rules table)
- `runner/dag_scheduler.py` — `RunSummary` class (lines 131–208), `RunSummary.build()`, `to_dict()`
- `runner/run_context.py` (from Step 6) — `get_node_failure_details()`

**Target files:**
- `runner/dag_scheduler.py` (modify — `RunSummary` class only)

**Goal:**
Extend `RunSummary` to include `node_failure_details` in `to_dict()` and in `run_summary.json`.

**Constraints:**
- `node_failure_details` is populated only for nodes not in `released` or `pending` state (§9.3).
- Classification rules must match the table in §9.3 exactly.
- `overall_status` computation is unchanged.
- `to_dict()` stable aliases are unchanged.
- `RunSummary.build()` reads failure details from `RunContext.get_node_failure_details()`.

**Implementation requirements:**

1. Add field `node_failure_details: dict[str, dict]` to `RunSummary`.
2. In `RunSummary.build()`: for each node in `node_states`:
   - If state is `released` or `pending`: skip (no failure details).
   - If state is `hard_block_upstream`: include `{"failure_origin": null, "exit_gate_evaluated": false}` (frozen by propagation, not local failure).
   - If state is `blocked_at_entry` or `blocked_at_exit`: read `ctx.get_node_failure_details(node_id)` and include.
3. In `to_dict()`: include `node_failure_details` in the output dict.
4. `run_summary.json` written to disk includes the new field.

**Output:**
`RunSummary` includes `node_failure_details`. `run_summary.json` includes the field. Existing fields and aliases are unchanged.

**Verification:**
- A run where n01 fails at entry gate produces `node_failure_details["n01_call_analysis"]["failure_origin"] == "entry_gate"` and `exit_gate_evaluated == false`.
- A run where n02 fails at agent body produces `node_failure_details["n02_concept_refinement"]["failure_origin"] == "agent_body"` and `exit_gate_evaluated == false`.
- A run where n01 passes entry and exit gates: n01 is NOT present in `node_failure_details`.
- A run where n07 fails and Phase 8 is hard-blocked: Phase 8 nodes have `failure_origin: null` in `node_failure_details`.
- `run_summary.json` written to disk contains the `node_failure_details` key.
- Existing `overall_status`, `node_states`, `gate_results_index` fields are unchanged.

---

## Step 8 — Tests

**Read first:**
- `runtime_integration_plan.md` — §14 (Test Plan — all 18 test cases)
- `runner/runtime_models.py` (from Step 2)
- `runner/node_resolver.py` (from Step 3)
- `runner/skill_runtime.py` (from Step 4)
- `runner/agent_runtime.py` (from Step 5)
- `runner/dag_scheduler.py` (from Step 6)
- `runner/run_context.py` (from Step 6)
- `tests/runner/fixtures/` — existing test fixture patterns

**Target files:**
- `tests/runner/test_runtime_models.py` (new)
- `tests/runner/test_node_resolver.py` (new)
- `tests/runner/test_skill_runtime.py` (new)
- `tests/runner/test_agent_runtime.py` (new)
- `tests/runner/test_dispatch_integration.py` (new)

**Goal:**
Implement unit tests covering all 18 test cases from §14, plus structural tests for the new modules.

**Constraints:**
- Tests must use the existing fixture patterns from `tests/runner/fixtures/`.
- Tests must not modify production source files.
- Each test must be independent and deterministic.
- Existing 762 tests must continue to pass after Step 6 changes (handle `_dispatch_node()` return type change if needed).

**Implementation requirements:**

1. **`test_runtime_models.py`** — dataclass construction, field validation, immutability:
   - SkillResult construction with all fields
   - AgentResult construction, verify `failure_origin` is always `"agent_body"`
   - NodeExecutionResult construction with all three failure_origin values
   - Constants (FAILURE_ORIGINS, SKILL_FAILURE_CATEGORIES, AGENT_FAILURE_CATEGORIES) have correct members

2. **`test_node_resolver.py`** — resolution from manifest:
   - node_id → agent_id for all 11 nodes
   - sub_agent resolution (n03 → `"dependency_mapper"`, others → None)
   - pre_gate_agent resolution (n07 → `"budget_interface_coordinator"`, others → None)
   - skill list resolution for all nodes
   - agent definition path exists on disk
   - prompt spec path exists on disk
   - NodeResolverError for unknown node_id

3. **`test_skill_runtime.py`** — skill execution:
   - run_skill with valid inputs → success
   - run_skill with missing input → MISSING_INPUT failure
   - run_skill with malformed input → MALFORMED_ARTIFACT failure
   - run_id propagation into written artifacts
   - artifact_status absent in written artifacts
   - atomic write: failure leaves no partial artifact at canonical path

4. **`test_agent_runtime.py`** — agent execution:
   - successful agent → AgentResult(status="success", can_evaluate_exit_gate=True)
   - skill CONSTITUTIONAL_HALT → agent halts, can_evaluate_exit_gate=False
   - skill failure propagation to AgentResult
   - n03 sub-agent coordination
   - n07 pre_gate_agent coordination
   - invoked_skills ordering

5. **`test_dispatch_integration.py`** — scheduler integration (§14 test cases):
   - agent failure (can_evaluate_exit_gate=False) prevents exit-gate evaluation
   - successful node body + exit gate pass → released
   - HARD_BLOCK preserved after budget gate failure with failure_origin="agent_body"
   - HARD_BLOCK preserved after budget gate failure with failure_origin="exit_gate"
   - run summary `node_failure_details` classifies all three origins correctly
   - `exit_gate_evaluated` is False for entry_gate and agent_body failures
   - `exit_gate_evaluated` is True for exit_gate failures
   - CONSTITUTIONAL_HALT propagates as agent_body failure
   - RunContext persists failure_origin and exit_gate_evaluated
   - _dispatch_node() skips exit gate when can_evaluate_exit_gate is False even if status=="success"

**Output:**
All test files exist. All tests pass. Existing 762 tests continue to pass.

**Verification:**
- `python -m pytest tests/runner/test_runtime_models.py tests/runner/test_node_resolver.py tests/runner/test_skill_runtime.py tests/runner/test_agent_runtime.py tests/runner/test_dispatch_integration.py` passes.
- `python -m pytest tests/` passes (all tests including existing 762).

---

## Step 9 — End-to-End Vertical Slice Scenarios

**Read first:**
- `runtime_integration_plan.md` — §9.2 (full _dispatch_node contract), §10 (all failure semantics), §11 (all special cases), §14 (test plan)
- `tests/runner/test_dag_full_run.py` — existing end-to-end test patterns
- `tests/runner/fixtures/` — repo builder, artifact writer, gate result writer patterns

**Target files:**
- `tests/runner/test_runtime_full_run.py` (new)

**Goal:**
Implement end-to-end integration tests that exercise the complete runtime stack: scheduler → agent runtime → skill runtime → canonical writes → gate evaluation → node release/blocking.

**Constraints:**
- Tests must use synthetic repos (no real Tier 1–3 documents required).
- Tests must cover the full dispatch cycle: ready node → entry gate → agent body → exit gate → state transition.
- Tests must cover all three failure origins in a DAG context.
- Tests must verify `run_summary.json` contains correct `node_failure_details`.

**Implementation requirements:**

1. **Linear pass scenario:** All nodes from n01 through n08d succeed. `overall_status == "pass"`. `node_failure_details` is empty (all nodes released).

2. **Agent-body failure at n02:** n01 passes (entry + exit gate). n02 agent body fails. n02 state = `blocked_at_exit`, `failure_origin="agent_body"`, `exit_gate_evaluated=false`. n03+ are stalled. `RunAbortedError` raised. `run_summary.json` has correct `node_failure_details`.

3. **Exit-gate failure at n03:** n01, n02 pass. n03 agent body succeeds but exit gate fails. n03 state = `blocked_at_exit`, `failure_origin="exit_gate"`, `exit_gate_evaluated=true`. n04+ stalled.

4. **Budget gate agent-body failure (n07):** n01–n06 pass. n07 agent body fails (e.g., absent budget response). n07 state = `blocked_at_exit`, `failure_origin="agent_body"`. Phase 8 nodes = `hard_block_upstream`. `run_summary.json` confirms HARD_BLOCK.

5. **Budget gate exit-gate failure (n07):** n01–n06 pass. n07 agent body succeeds but gate_09 fails. Same HARD_BLOCK behavior. `failure_origin="exit_gate"`.

6. **CONSTITUTIONAL_HALT propagation:** n01 passes. n02 agent invokes a skill that returns CONSTITUTIONAL_HALT. n02 halts with `failure_category="CONSTITUTIONAL_HALT"`, `can_evaluate_exit_gate=False`. Downstream stalled.

7. **Phase 8 multi-node (n08a + n08b with same proposal_writer):** Verify that n08a and n08b are dispatched as separate nodes with separate agent invocations despite sharing the same agent_id.

**Output:**
`tests/runner/test_runtime_full_run.py` exists with all 7 scenarios. All pass. All existing tests pass.

**Verification:**
- `python -m pytest tests/runner/test_runtime_full_run.py -v` passes all 7 scenarios.
- `python -m pytest tests/` passes (complete suite including all existing tests).
- Each scenario's `run_summary.json` contains the expected `node_failure_details` entries.

---

## Summary

**Total steps:** 9

**Ordering confirmation:** The 9 steps correspond exactly to the 9 ordered items in `runtime_integration_plan.md` §13 (Dependency-Ordered Implementation Sequence). No items reordered, merged, split, or skipped.

**Dependency safety confirmation:**
- Step 1 (context initialization) has no code dependencies.
- Step 2 (runtime_models.py) depends only on Step 1 verification.
- Step 3 (node_resolver.py) depends on Step 2 (imports runtime_models for error context only — no dataclass dependency; may proceed independently but ordered after Step 2 per §13).
- Step 4 (skill_runtime.py) depends on Step 2 (imports SkillResult).
- Step 5 (agent_runtime.py) depends on Steps 2, 3, 4 (imports AgentResult, NodeResolver, run_skill).
- Step 6 (scheduler integration) depends on Steps 2, 3, 5 (imports NodeExecutionResult, NodeResolver, run_agent).
- Step 7 (RunSummary extension) depends on Step 6 (reads failure details from RunContext).
- Step 8 (tests) depends on Steps 2–7 (tests all modules).
- Step 9 (end-to-end) depends on Steps 2–8 (integration tests require complete stack).

No step depends on a future step. Each step is independently executable given its predecessors are complete.
