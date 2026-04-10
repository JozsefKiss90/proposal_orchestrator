Create a new planning document for the next implementation layer:

Target file:
- `.claude/workflows/system_orchestration/runtime_integration_plan.md`

Goal:
Write a production-grade **Skill Runtime + Agent Runtime Integration Plan** for the Horizon Europe Proposal Orchestration System.

This plan must define how the existing DAG scheduler is extended so that it can invoke **node body execution through agents**, while preserving the repository’s constitutional execution model:

- scheduler resolves `node_id -> agent_id`
- scheduler invokes an **agent runner**, not a skill
- agent runner loads and executes the agent prompt/body for that node
- agent runtime invokes the manifest-bound skills for that agent
- skills perform bounded canonical I/O and return `SkillResult`
- agent consolidates outputs and writes durable Tier 4 / Tier 5 artifacts
- scheduler then evaluates the node’s exit gate
- downstream DAG progression remains gate-controlled, blocking, and deterministic

This plan must be constitutionally aligned with `CLAUDE.md`, must preserve scheduler–agent–skill separation, and must not weaken the already implemented gate-first blocking DAG model.

Mandatory source reading — REQUIRED before writing anything:
Read these files first, in authority order, and treat them as binding sources for this task:

**Constitutional and workflow authority (read first — these govern all decisions):**

1. `CLAUDE.md` — Highest interpretive authority. Defines forbidden actions, tier model, phase sequence, gate semantics, and all constitutional prohibitions (§13).
2. `.claude/workflows/system_orchestration/manifest.compile.yaml` — Binding execution model: node registry (agent, sub_agent, pre_gate_agent, skills per node), edge registry, gate registry with predicate_refs, artifact registry with produced_by/consumed_by.
3. `.claude/workflows/system_orchestration/agent_catalog.yaml` — Agent scope, reads_from, writes_to, must_not constraints. Required for agent-body execution boundaries.
4. `.claude/workflows/system_orchestration/skill_catalog.yaml` — Skill scope, reads_from, writes_to, constitutional_constraints. Required for skill invocation boundaries.
5. `.claude/workflows/system_orchestration/artifact_schema_specification.yaml` — Field-level schemas for all 13 canonical artifact types. Required for canonical I/O resolution (§8), schema validation in `can_evaluate_exit_gate` determination, and `run_id`/`schema_id` stamping rules.
6. `.claude/workflows/system_orchestration/quality_gates.yaml` — All 11 gates with conditions and predicate_refs. Required to understand what artifacts each exit gate evaluates, which directly informs the `can_evaluate_exit_gate` contract in `AgentResult`.

**Implementation plans (read second — these define the contracts being integrated):**

7. `.claude/workflows/system_orchestration/agent-generation-plan.md` — Agent generation plan (Steps 1–10 complete). Defines the node-body contract, agent identity, canonical I/O, skill binding, gate awareness, and failure behaviour specifications.
8. `.claude/workflows/system_orchestration/skill_implementation_plan.md` — Skill implementation plan (Steps 1–10 complete). Defines the `SkillResult` contract, skill invocation model, failure categories, and scope enforcement rules.
9. `.claude/workflows/system_orchestration/dag_scheduler_plan.md` — DAG scheduler plan (Steps 1–6 complete). Defines `ManifestGraph`, `DAGScheduler`, `RunSummary`, `RunAbortedError`, node state machine, and `_dispatch_node()` contract that this plan extends.
10. `.claude/workflows/system_orchestration/README.md` — Current package structure, execution boundaries, and three-layer integration status.

**Runtime contracts (read third — these are the interfaces being extended or implemented):**

11. `.claude/agents/node_body_contract.md` — Shared contract all 16 agents must conform to. Defines agent identity, allowed scope, must_not constraints, canonical I/O, skill invocation, gate awareness, failure behaviour (§3.9), and decision-log obligations. The agent runtime must enforce this contract at invocation time.
12. `.claude/skills/skill_runtime_contract.md` — Shared contract all 19 skills must conform to. Defines the `run_skill()` → `SkillResult` interface (§6), input validation, output conformance, determinism, failure categories, and side-effect control. The skill runtime must implement this contract.

**Existing runner modules (read fourth — these are the code being extended):**

13. `runner/dag_scheduler.py` — `ManifestGraph`, `DAGScheduler`, `RunSummary`. The `_dispatch_node()` method (lines 1028–1127) is the sole modification point for agent-body insertion.
14. `runner/run_context.py` — `RunContext`, `NODE_STATES`, `set_node_state()`, `mark_hard_block_downstream()`. Must be read before extending `set_node_state()` with failure metadata (§9.4).
15. `runner/gate_evaluator.py` — `evaluate_gate()` entry point. Must remain unchanged; the integration inserts agent execution before this call, not inside it.
16. `runner/semantic_dispatch.py` — Contains `invoke_agent()`, `SemanticPredicateConfig`, `SEMANTIC_REGISTRY`. Must be read to understand the existing agent invocation pattern for semantic predicates and to avoid duplication or architectural conflict with the new agent runtime.
17. `runner/paths.py` — `find_repo_root()` and path resolution utilities. Must be read for canonical path construction in the agent and skill runtimes.
18. `runner/manifest_reader.py` — `ManifestReader` class. Loads `manifest.compile.yaml` and provides `get_predicate_refs()`. Must be read to understand how the manifest is already consumed at runtime and whether the agent runtime should reuse `ManifestReader` for node registry access.
19. `runner/__main__.py` — CLI entry point. Must be read to understand how `run_id`, `repo_root`, `library_path`, and `manifest_path` are passed into the scheduler, since the agent runtime will receive these from the same call chain.

Important reading discipline:
- Re-read the relevant source whenever making a binding decision about runtime ownership, path authority, gate timing, agent invocation, skill invocation, or run_id propagation.
- Do not proceed from memory.
- `CLAUDE.md` remains the highest interpretive authority.
- The existing scheduler implementation is already complete for gate orchestration over pre-produced artifacts; this new plan must add **node body execution** without breaking that contract. Do not silently rewrite the scheduler model.

Mandatory re-consultation rules:
- Agent scope decisions → re-read `agent_catalog.yaml` and `node_body_contract.md`
- Skill invocation decisions → re-read `skill_catalog.yaml` and `skill_runtime_contract.md`
- Canonical artifact paths or schema fields → re-read `manifest.compile.yaml` artifact_registry and `artifact_schema_specification.yaml`
- Gate predicate expectations → re-read `quality_gates.yaml` and `manifest.compile.yaml` gate_registry
- Node state transitions or RunContext extensions → re-read `runner/run_context.py`
- Path resolution → re-read `runner/paths.py`
- Existing agent invocation patterns → re-read `runner/semantic_dispatch.py`

Core architectural position the plan must preserve:
- The DAG scheduler does **not** call skills directly.
- The DAG scheduler calls a **node body / agent runtime** layer.
- The agent runtime resolves `agent_id` from `node_id` using `manifest.compile.yaml`.
- The agent runtime is responsible for executing the agent body / prompt spec for that node.
- The agent runtime invokes the node’s declared skills in dependency order.
- Skills do not invoke other skills, do not invoke agents, and do not evaluate gates.
- The scheduler evaluates the gate only **after** durable canonical outputs have been written.
- All gate semantics remain blocking.
- HARD_BLOCK behavior remains scheduler-owned.
- `run_id` propagation remains: scheduler -> agent runtime -> skill runtime -> canonical artifacts.

The document you write must be a true implementation plan, not a vague architecture note.

The plan must explicitly solve these integration requirements:
1. Resolve `node_id -> agent_id`
2. Load agent prompt/body specification by `agent_id`
3. Execute agent body for a node in a scheduler-safe way
4. Resolve the node’s declared skills from `manifest.compile.yaml`
5. Provide a standard `run_skill(...) -> SkillResult` runtime interface
6. Handle canonical input resolution for agents and for skills
7. Handle canonical output writing and merge/update behavior
8. Propagate `run_id`
9. Record outputs written, validation reports, and failures
10. Return a structured agent-run result to the scheduler
11. Preserve the existing gate evaluation contract in `evaluate_gate()`
12. Preserve current blocking DAG semantics and HARD_BLOCK behavior

Hard constraints:
- Do not modify the scheduler contract by implication.
- Do not make the scheduler call skills directly.
- Do not make agents call the scheduler.
- Do not make skills call agents.
- Do not move gate evaluation into the agent or skill layer.
- Do not introduce parallel dispatch or concurrency.
- Do not introduce rerun/resume logic unless explicitly scoped as non-goal or future work.
- Do not invent new canonical artifact paths.
- Do not weaken CLAUDE.md phase ordering, gate blocking, budget-gate blocking, or traceability obligations.
- Do not introduce any budget computation behavior.
- Do not rewrite already-completed scheduler scope; this plan must extend it, not replace it.

The plan should define the following major sections at minimum:

## 1. Problem Statement
Explain precisely what is missing today:
- current DAG scheduler evaluates gates over pre-produced artifacts
- node body execution is explicitly out of scope in the current scheduler plan
- agent and skill layers now exist as specifications but are not runtime-integrated
- therefore a runtime integration layer is needed

## 2. Constitutional and Architectural Invariants
State the non-negotiable rules:
- scheduler / agent / skill separation
- blocking gate semantics
- durable Tier 4 writes before exit-gate evaluation
- skill scope boundaries
- agent scope boundaries
- no scheduler coupling from agent files
- no direct skill invocation by scheduler
- budget gate remains mandatory and fully blocking for Phase 8
- **The scheduler state machine is closed.** No new node states may be introduced by runtime integration. The existing states (`pending`, `running`, `released`, `blocked_at_entry`, `blocked_at_exit`, `deterministic_pass_semantic_pending`, `hard_block_upstream`) are the complete and final set. All new failure semantics — including agent-body failures — must be expressed through structured failure classification fields (`failure_origin`, `failure_reason`, `failure_category`, `exit_gate_evaluated`), not through new state values. This invariant prevents state-machine divergence between the scheduler, RunContext, and RunSummary.

## 3. Runtime Layers and Responsibilities
Define the runtime stack explicitly, for example:
- `DAGScheduler`
- `NodeBodyRunner` or `AgentRuntime`
- `SkillRuntime`
- existing `evaluate_gate()`
For each layer, state:
- what it owns
- what it must not own
- what inputs it receives
- what outputs it returns

## 4. Runtime Contracts
Define concrete runtime interfaces, with typed signatures where appropriate.

At minimum specify contracts for:
- `run_node(node_id, run_id, repo_root, ...) -> NodeExecutionResult`
- `run_agent(agent_id, node_id, run_id, repo_root, ...) -> AgentResult`
- `run_skill(skill_id, run_id, repo_root, inputs) -> SkillResult`

### 4.1 AgentResult

`AgentResult` is the structured return type from the agent runtime to the scheduler integration layer. Required fields:

```
AgentResult:
    status:                  "success" | "failure"
    failure_origin:          "agent_body"          # always "agent_body" when coming from agent runtime
    failure_reason:          str | None             # human-readable; required when status == "failure"
    failure_category:        str | None             # one of: MISSING_INPUT | MALFORMED_ARTIFACT |
                                                    #         CONSTRAINT_VIOLATION | INCOMPLETE_OUTPUT |
                                                    #         CONSTITUTIONAL_HALT | SKILL_FAILURE |
                                                    #         AGENT_EXECUTION_ERROR
    can_evaluate_exit_gate:  bool                   # true if all artifacts required by the node’s exit-gate predicates have been 
                                                    # durably written to their canonical paths, are complete, and are schema-valid 
                                                    # where applicable. False otherwise.
                                                    # MUST skip exit gate evaluation.
    outputs_written:         list[str]              # paths of artifacts written (relative to repo_root)
    validation_reports:      list[str]              # paths of validation reports written, if any
    decision_log_writes:     list[str]              # paths of decision log entries written, if any
    invoked_skills:          list[SkillInvocationRecord]  # ordered record of skill invocations and results
```

**Binding rule:** The scheduler uses `can_evaluate_exit_gate` as the sole decision input for whether to call `evaluate_gate()` on the exit gate. When `can_evaluate_exit_gate is False`, exit gate evaluation is skipped unconditionally and the node transitions to `blocked_at_exit` with `failure_origin: "agent_body"`.

### 4.2 NodeExecutionResult

`NodeExecutionResult` is the composite result returned by `_dispatch_node()` to the scheduler's `run()` loop. Required fields:

```
NodeExecutionResult:
    node_id:                 str
    final_state:             str                    # one of the existing terminal states
    failure_origin:          str | None             # "entry_gate" | "agent_body" | "exit_gate" | None
    exit_gate_evaluated:     bool                   # True only when evaluate_gate() was actually called
                                                    # on the exit gate
    gate_result:             dict | None            # last gate result dict, or None if no gate was evaluated
    agent_result:            AgentResult | None     # None when entry gate failed before agent execution
    failure_reason:          str | None
    failure_category:        str | None
```

### 4.3 SkillResult (existing — reused)

Reuse or align with the existing `SkillResult` from `skill_runtime_contract.md` §6.2:

```
SkillResult:
    status:              "success" | "failure"
    outputs_written:     list[str]
    validation_report:   str | None
    failure_reason:      str | None
    failure_category:    str | None   # MISSING_INPUT | MALFORMED_ARTIFACT |
                                      # CONSTRAINT_VIOLATION | INCOMPLETE_OUTPUT |
                                      # CONSTITUTIONAL_HALT
```

These contracts must include:
- status
- outputs_written
- validation_report(s)
- failure_reason
- failure_category
- invoked_skills
- canonical artifacts touched
- decision-log writes (if any)
- whether the node body completed successfully enough for gate evaluation to proceed (expressed as `can_evaluate_exit_gate`)

## 5. node_id -> agent_id Resolution Model
Define exactly how node registry drives runtime dispatch:
- manifest node registry is the authoritative binding source
- `agent`, `sub_agent`, and `pre_gate_agent` semantics
- how `n03` and `n07` special cases are handled
- how Phase 8 repeated `proposal_writer` nodes are distinguished by node_id / phase_id / prompt context

## 6. Agent Prompt / Body Execution Model
Define how the agent runtime locates and uses:
- `.claude/agents/<agent_id>.md`
- `.claude/agents/prompts/<agent_id>_prompt_spec.md`
if both are part of the current design
Clarify:
- which file is executable authority
- which file is supporting specification
- what prompt context is passed in
- how canonical input paths are surfaced
- how skill bindings are surfaced
- how must_not constraints are enforced at runtime

## 7. Skill Invocation Model
Define:
- how agent runtime gets the skill list for a node from `manifest.compile.yaml`
- whether the manifest skill list is authoritative over any agent-local ordering hints
- how dependency ordering among skills is determined
- how agent runtime passes context into each skill
- how `SkillResult` is collected
- what happens on first failure vs accumulated failures
- when the agent must halt
- when the agent may continue to another skill
- how merge/update semantics work when multiple skills populate the same canonical artifact

## 8. Canonical I/O Resolution
Define:
- how agent runtime resolves canonical inputs from `reads_from`
- how skill runtime resolves canonical inputs from skill `reads_from`
- path resolution relative to `repo_root`
- schema expectations for canonical artifacts
- run_id propagation into canonical outputs
- artifact_status abstention at write time
- how decision_log / validation_reports / checkpoints are handled
- how co-produced artifacts are merged without ownership ambiguity

Atomic Canonical Write Rule
- A canonical artifact is considered “written” only when it has been fully constructed, schema-validated where applicable, and committed atomically to its canonical path.
- If a skill or agent fails before that point, it MUST NOT leave a partial or intermediate payload at the canonical artifact path. Any incomplete write must remain outside the canonical path (for example in a temporary path) or be discarded.
- Therefore, when AgentResult.can_evaluate_exit_gate == False, the scheduler may assume that no required canonical artifact exists in a partially-written state at its canonical location.

## 9. Scheduler Integration Points

### 9.1 Sole modification point: `_dispatch_node()`

The only scheduler method that changes is `DAGScheduler._dispatch_node()`. The `run()` loop, `ManifestGraph`, `_settle_stalled_nodes()`, and `RunSummary.build()` are unchanged in dispatch logic. `RunSummary` gains additional fields (§9.3) but its construction algorithm is unaffected.

### 9.2 Revised `_dispatch_node()` contract (prescriptive — not optional)

`_dispatch_node(node_id)` must execute the following steps in exact order:

```
1. Set node_state → "running". Persist.

2. ENTRY GATE (if present):
   - Call evaluate_gate(entry_gate_id, ...).
   - If result.status != "pass":
     - Set node_state → "blocked_at_entry".
     - Record: failure_origin = "entry_gate", exit_gate_evaluated = False.
     - Return NodeExecutionResult immediately.
     - Agent runtime is NOT invoked.

3. NODE BODY EXECUTION:
   - Call run_node_body(node_id, run_id, repo_root, ...) → AgentResult.
   - If agent_result.status == "failure":
     - Set node_state → "blocked_at_exit".
     - Record:
       - failure_origin = "agent_body"
       - failure_reason = agent_result.failure_reason
       - failure_category = agent_result.failure_category
       - exit_gate_evaluated = False
     - If exit_gate_id == "gate_09_budget_consistency":
       - Call ctx.mark_hard_block_downstream(). Persist.
     - Return NodeExecutionResult immediately.
     - Exit gate is NOT evaluated. This is unconditional.
   - If agent_result.can_evaluate_exit_gate == False (even if status == "success"):
     - Treat as agent-body failure. Same behavior as above.

4. EXIT GATE EVALUATION:
   - Call evaluate_gate(exit_gate_id, ...).
   - Record: exit_gate_evaluated = True.
   - If result.status == "pass":
     - Set node_state → "released".
     - Record: failure_origin = None.
   - If result.status != "pass":
     - Set node_state → "blocked_at_exit".
     - Record: failure_origin = "exit_gate".
     - If exit_gate_id == "gate_09_budget_consistency":
       - Call ctx.mark_hard_block_downstream(). Persist.

5. Return NodeExecutionResult with all recorded fields.
```

**No new node states are introduced.** Agent-body failure produces `blocked_at_exit` — the same terminal state as exit-gate failure. The two are distinguished by `failure_origin` and `exit_gate_evaluated`, not by node state.

### 9.3 RunSummary extension

`RunSummary` and `run_summary.json` must include the following additional fields to support failure origin classification:

```json
{
  "node_failure_details": {
    "<node_id>": {
      "failure_origin": "entry_gate" | "agent_body" | "exit_gate",
      "exit_gate_evaluated": true | false,
      "failure_reason": "..." | null,
      "failure_category": "..." | null
    }
  }
}
```

`node_failure_details` is populated only for nodes that are not in `released` or `pending` state. Nodes in `released` state have no failure. Nodes in `pending` state (stalled) have no failure details — their stall is structural (upstream blocking), not a local failure.

Classification rules:

| Node state | failure_origin | exit_gate_evaluated |
|------------|---------------|---------------------|
| `released` | (not present) | (not present) |
| `blocked_at_entry` | `"entry_gate"` | `false` |
| `blocked_at_exit` (agent failed) | `"agent_body"` | `false` |
| `blocked_at_exit` (gate failed) | `"exit_gate"` | `true` |
| `hard_block_upstream` | (not present — frozen by propagation, not local failure) | `false` |
| `pending` (stalled) | (not present) | (not present) |

### 9.4 RunContext persistence

`failure_origin` and `exit_gate_evaluated` are written to `RunContext` per-node state alongside the existing `node_state` field. This allows `RunSummary.build()` to read them without re-deriving them from gate result files. The existing `set_node_state()` API is extended with optional keyword arguments:

```python
ctx.set_node_state(node_id, "blocked_at_exit",
                   failure_origin="agent_body",
                   exit_gate_evaluated=False,
                   failure_reason="...",
                   failure_category="...")
```

These fields are metadata on the state transition, not new states. The state machine remains closed.

## 10. Failure Semantics

### 10.1 Failure Classification Model (binding decision)

All node-level failures are classified by exactly one `failure_origin` value. This is the **sole mechanism** for distinguishing failure types. No new node states are used.

#### Origin 1: `failure_origin = "entry_gate"`

| Attribute | Value |
|-----------|-------|
| When | Entry gate `evaluate_gate()` returns status != "pass" |
| Node state | `blocked_at_entry` |
| Exit gate evaluated | **No** — agent body is never invoked |
| Agent body executed | **No** |
| Durable outputs expected | **No** |
| Tier 4 failure record | Gate result written by `evaluate_gate()` to canonical gate result path |

#### Origin 2: `failure_origin = "agent_body"`

| Attribute | Value |
|-----------|-------|
| When | Agent runtime returns `AgentResult.status == "failure"` or `AgentResult.can_evaluate_exit_gate == False` |
| Node state | `blocked_at_exit` |
| Exit gate evaluated | **No** — exit gate MUST NOT run when agent body fails. Agent-body failure occurs before durable canonical outputs are guaranteed; evaluating gate predicates against absent or partial artifacts would produce misleading results. |
| Agent body executed | **Yes** (attempted; failed before completing successfully) |
| Durable outputs expected | **Not guaranteed** — partial outputs may exist but are not gate-evaluable |
| Tier 4 failure record | Agent runtime writes a failure record to `docs/tier4_orchestration_state/decision_log/` if within its write scope. `failure_reason` and `failure_category` are persisted to `RunContext` and `RunSummary.node_failure_details`. |

#### Origin 3: `failure_origin = "exit_gate"`

| Attribute | Value |
|-----------|-------|
| When | Exit gate `evaluate_gate()` returns status != "pass" after agent body completed successfully |
| Node state | `blocked_at_exit` |
| Exit gate evaluated | **Yes** |
| Agent body executed | **Yes** (completed successfully; durable outputs written) |
| Durable outputs expected | **Yes** — agent completed and `can_evaluate_exit_gate == True` |
| Tier 4 failure record | Gate result written by `evaluate_gate()` to canonical gate result path |

### 10.2 Failure propagation across layers

**Skill → Agent:** A skill returns `SkillResult(status="failure")`. The agent runtime receives this and decides whether to halt or continue to the next skill (per §7 skill invocation model). If the agent cannot produce complete canonical outputs, it returns `AgentResult(status="failure", can_evaluate_exit_gate=False)`.

**Agent → Scheduler:** The scheduler receives `AgentResult`. If `status == "failure"` or `can_evaluate_exit_gate == False`, the scheduler sets `blocked_at_exit` with `failure_origin="agent_body"` and skips exit gate evaluation. No ambiguity; no conditional logic.

**Gate → Scheduler:** Unchanged from current implementation. `evaluate_gate()` returns a result dict; the scheduler reads `status` and transitions to `released` or `blocked_at_exit` with `failure_origin="exit_gate"`.

### 10.3 Constitutional halt propagation

A `CONSTITUTIONAL_HALT` from a skill propagates through the agent (which must halt immediately per `node_body_contract.md` §3.9) and surfaces as `AgentResult(status="failure", failure_category="CONSTITUTIONAL_HALT", can_evaluate_exit_gate=False)`. The scheduler treats this identically to any other agent-body failure: `blocked_at_exit`, `failure_origin="agent_body"`, exit gate skipped.

### 10.4 Failures that prevent exit-gate evaluation (exhaustive list)

Exit gate evaluation is skipped if and only if:
1. Entry gate failed (`failure_origin="entry_gate"`) — agent was never invoked
2. Agent body failed (`failure_origin="agent_body"`) — durable outputs not guaranteed
3. `AgentResult.can_evaluate_exit_gate == False` — agent completed but cannot vouch for output completeness

In all other cases — specifically when `AgentResult.status == "success"` and `AgentResult.can_evaluate_exit_gate == True` — exit gate evaluation proceeds unconditionally.

### 10.5 Failures written to Tier 4

| Failure type | Written by | Written to |
|-------------|-----------|-----------|
| Entry gate failure | `evaluate_gate()` | Canonical gate result path in `docs/tier4_orchestration_state/` |
| Agent body failure | Agent runtime (if write scope permits) | `docs/tier4_orchestration_state/decision_log/` |
| Skill failure | Skill (if write scope permits); otherwise agent writes on behalf | `docs/tier4_orchestration_state/decision_log/` or `validation_reports/` |
| Exit gate failure | `evaluate_gate()` | Canonical gate result path in `docs/tier4_orchestration_state/` |
| Constitutional halt | Agent runtime | `docs/tier4_orchestration_state/decision_log/` |

### 10.6 How failure state reaches RunContext

The scheduler calls `ctx.set_node_state()` with the extended keyword arguments defined in §9.4. The `failure_origin`, `exit_gate_evaluated`, `failure_reason`, and `failure_category` are persisted alongside the node state. `RunSummary.build()` reads these from `RunContext` and populates `node_failure_details` in `run_summary.json`.

## 11. Special Cases
Address explicitly:
- `n03_wp_design` with `dependency_mapper` sub-agent
- `n07_budget_gate` with `pre_gate_agent: budget_interface_coordinator`
- Phase 8 nodes using `proposal_writer` across multiple substeps
- interaction with `gate-enforcement` skill, ensuring it does not become gate evaluator
- node-body behavior when a skill writes a valid failure artifact instead of a success artifact
- budget gate absent-artifact blocking behavior

## 12. Proposed Modules and File Targets
Propose a disciplined implementation structure.

For example, specify candidate modules such as:
- `runner/agent_runtime.py`
- `runner/skill_runtime.py`
- `runner/node_body_runner.py`
- `runner/runtime_models.py`
- `runner/agent_loader.py`
- `runner/prompt_loader.py`

For each proposed file, state:
- purpose
- owned abstractions
- what it must not do

Do not assume these exact filenames unless they are justified; propose the best structure.

## 13. Dependency-Ordered Implementation Sequence (Build Order Constraint)
Write a step-by-step implementation sequence, comparable in quality and precision to the existing scheduler and skill plans.

It should include:
- context initialization
- runtime contract definitions
- loader / resolver layer
- skill runtime
- agent runtime
- scheduler integration
- run summary extension if needed
- tests
- end-to-end vertical slice scenarios

Each step should define:
- target files
- objective
- constraints
- expected tests

## 14. Test Plan
Include unit and integration tests.

At minimum define tests for:
- node_id -> agent_id resolution
- prompt spec loading
- skill list resolution from manifest
- run_id propagation
- canonical input binding
- skill failure propagation to AgentResult
- agent failure (can_evaluate_exit_gate=False) preventing exit-gate evaluation
- successful node body + exit gate pass
- `n03` sub-agent behavior
- `n07` pre_gate_agent behavior
- HARD_BLOCK preserved after budget gate failure with failure_origin="agent_body"
- HARD_BLOCK preserved after budget gate failure with failure_origin="exit_gate"
- run summary `node_failure_details` correctly classifies failure_origin for all three origins
- run summary `exit_gate_evaluated` is False for entry_gate and agent_body failures
- run summary `exit_gate_evaluated` is True for exit_gate failures
- CONSTITUTIONAL_HALT from skill propagates as agent_body failure with failure_category="CONSTITUTIONAL_HALT"
- RunContext persists failure_origin and exit_gate_evaluated alongside node state
- _dispatch_node() skips exit gate when AgentResult.can_evaluate_exit_gate is False even if status=="success"

## 15. Non-Goals
Explicitly state what this new integration plan does NOT do:
- no parallel execution
- no replacement of evaluate_gate()
- no replacement of manifest DAG logic
- no scheduler-direct skill calls
- no autonomous agent orchestration outside node execution
- no budget computation
- no new artifact schema invention

Quality requirements:
- The document must read like the existing implementation plans in this repository.
- It must be concrete enough that Claude Code could implement from it later without major ambiguity.
- It must preserve all current constitutional and architectural boundaries.
- It must explicitly reconcile the current scheduler plan’s “node body execution out of scope” statement with this new plan by treating this as the next layer above the existing scheduler, not as a contradiction.

Output requirement:
Write only the new file:
- `.claude/workflows/system_orchestration/runtime_integration_plan.md`

Do not modify any other file.

At the end of your response:
- provide a concise summary of the plan you wrote
- list the key architectural invariants it preserves
- list the proposed runtime modules / artifacts