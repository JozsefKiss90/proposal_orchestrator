# DAG Runner Blueprint

Extracted from the Horizon Europe Proposal Orchestration System runtime. This document catalogs every architectural feature, design decision, and operational pattern needed to bootstrap an equivalent DAG runner in another project.

---

## 1. Three-Layer Execution Stack

The runtime is a strict three-layer call graph. Each layer has exactly one caller and one callee direction. No layer may skip, recurse, or reverse the call direction.

```
DAGScheduler._dispatch_node()
  → run_agent(agent_id, ...)        # agent runtime
      → run_skill(skill_id, ...)    # skill runtime
          → invoke_claude_text(...)  # transport
```

### Call-Graph Constraints

| Rule | Enforced by |
|------|-------------|
| Scheduler calls `run_agent()` — never calls `run_skill()` directly | `_dispatch_node()` only calls `run_agent()` |
| Agent runtime calls `run_skill()` — never calls `evaluate_gate()` or other agents | `run_agent()` sequences skills, never imports gate evaluator |
| Skill runtime calls `invoke_claude_text()` — never calls agent runtime or scheduler | `run_skill()` only calls transport |
| Gate evaluator is called by scheduler only | `evaluate_gate()` imported only by `dag_scheduler.py` |

### Why This Matters

Without strict layering, you get: skills evaluating their own gates (circular), agents invoking the scheduler (reentrancy), or transport logic leaking into orchestration. Each violation creates a class of bugs that is invisible in happy-path testing and catastrophic in failure paths.

---

## 2. Agent–Skill Interaction Model

### Agents Are Orchestration Adapters, Not Reasoners

An agent loads its specification + prompt spec, resolves inputs, sequences skill invocations, propagates failures, and determines gate-readiness. It does NOT perform domain reasoning — Claude does that inside `run_skill()`.

```python
def run_agent(agent_id, node_id, run_id, repo_root, *, manifest_path, skill_ids, phase_id, sub_agent_id=None, pre_gate_agent_id=None) -> AgentResult:
    # Phase A: Load agent spec + prompt spec from .claude/agents/
    # Phase B: Resolve canonical inputs from agent's reads_from paths
    # Phase C: Handle pre-gate agents (special cases like budget validation)
    # Phase D: Sequence skill invocations through run_skill()
    #          - Derive execution order from prompt spec (document-order heuristic)
    #          - Build caller_context for context-sensitive skills
    #          - Propagate CONSTITUTIONAL_HALT immediately (halt all further skills)
    #          - Record SkillInvocationRecord for each skill
    # Phase E: Determine can_evaluate_exit_gate from actual disk state
    # Return AgentResult
```

### Skills Are Transport Adapters, Not Interpreters

A skill loads its `.md` spec, assembles a prompt, invokes Claude, parses the JSON response, validates it against schema, and writes atomically. The `.md` file is a specification document, not executable code.

```python
def run_skill(skill_id, run_id, repo_root, inputs=None, *, node_id=None, caller_context=None) -> SkillResult:
    # Phase A: Load catalog entry + skill spec from .claude/skills/
    # Mode selection: "cli-prompt" or "tapm" from skill catalog
    # [cli-prompt]: resolve inputs → assemble full prompt → invoke claude (no tools)
    # [tapm]: assemble bounded prompt → invoke claude with Read,Glob tools
    # Phase D: Extract JSON from response (_extract_json_response)
    # Phase E: Validate against schema (_validate_skill_output)
    # Phase F: Atomic write (temp file → rename)
    # Return SkillResult
```

### Context Passing Between Agent and Skills

The agent runtime builds `caller_context` for context-sensitive skills — content that the agent has already loaded but that isn't part of the skill's declared `reads_from`. This avoids redundant disk reads and ensures the skill sees exactly the content the agent evaluated.

```python
_SKILL_CONTEXT_SOURCES = {
    "topic-scope-check": (
        "docs/.../concept_note.md",
        "docs/.../strategic_positioning.md",
        "docs/.../project_summary.json",
    ),
}
```

### Skill Sequencing

The agent derives execution order from the prompt spec using a document-order heuristic: scan the prompt spec for skill-ID mentions in document order, sort by position. Skills in the manifest set but not mentioned are appended at the end.

---

## 3. Agent–Skill Invocation Contracts

### Three Structured Result Types

All inter-layer communication flows through frozen dataclasses (immutable after construction):

**SkillResult** (skill → agent):
```python
@dataclass(frozen=True)
class SkillResult:
    status: str                    # "success" or "failure"
    outputs_written: list[str]     # repo-relative paths of artifacts written
    validation_report: str | None  # path to validation report, if any
    failure_reason: str | None     # required on failure
    failure_category: str | None   # MISSING_INPUT | MALFORMED_ARTIFACT | CONSTRAINT_VIOLATION | INCOMPLETE_OUTPUT | CONSTITUTIONAL_HALT
```

**AgentResult** (agent → scheduler):
```python
@dataclass(frozen=True)
class AgentResult:
    status: str                        # "success" or "failure"
    can_evaluate_exit_gate: bool       # True only when all gate-relevant artifacts exist on disk
    failure_origin: str = "agent_body" # always "agent_body"
    failure_reason: str | None
    failure_category: str | None       # skill categories + SKILL_FAILURE | AGENT_EXECUTION_ERROR
    invoked_skills: list[SkillInvocationRecord]  # ordered record of all invocations
```

**NodeExecutionResult** (scheduler internal):
```python
@dataclass(frozen=True)
class NodeExecutionResult:
    node_id: str
    final_state: str                # released | blocked_at_entry | blocked_at_exit | hard_block_upstream
    exit_gate_evaluated: bool       # True only when evaluate_gate() was actually called
    failure_origin: str | None      # entry_gate | agent_body | exit_gate | None
    agent_result: AgentResult | None  # None when entry gate failed
```

### Failure Category Taxonomy

Closed set — no new categories allowed without constitutional amendment:

| Category | Meaning |
|----------|---------|
| `MISSING_INPUT` | Required input file/directory absent or unreadable |
| `MALFORMED_ARTIFACT` | Output JSON is structurally invalid, has extra/missing fields |
| `CONSTRAINT_VIOLATION` | Constitutional or domain constraint violated |
| `INCOMPLETE_OUTPUT` | Claude returned empty/partial output, or transport timeout |
| `CONSTITUTIONAL_HALT` | Hard constitutional violation — agent halts immediately |
| `SKILL_FAILURE` | Agent-level: a skill returned failure |
| `AGENT_EXECUTION_ERROR` | Agent-level: infrastructure error during agent execution |

---

## 4. Division of Responsibilities

### What the External Runtime Controls (Python)

| Responsibility | Module | Never delegated to Claude |
|---|---|---|
| DAG dispatch, ordering, stall detection | `dag_scheduler.py` | Yes |
| Entry/exit gate evaluation | `gate_evaluator.py` | Yes (gate evaluation calls Claude for semantic predicates, but the decision is external) |
| HARD_BLOCK propagation | `dag_scheduler.py` | Yes |
| Node state persistence | `run_context.py` | Yes |
| Skill sequencing, context passing | `agent_runtime.py` | Yes |
| `can_evaluate_exit_gate` determination | `agent_runtime.py` (disk inspection) | Yes |
| Mode selection per skill | `skill_runtime.py` | Yes |
| Response parsing, schema validation | `skill_runtime.py` | Yes |
| Atomic artifact writes | `skill_runtime.py` (temp → rename) | Yes |
| Deterministic input slicing | `call_slicer.py` | Yes (pure Python, no Claude) |

### What Claude Controls (via transport)

| Responsibility | Invoked via |
|---|---|
| Domain reasoning within skill specs | `run_skill()` → `invoke_claude_text()` |
| Structured JSON output generation | Claude's response to skill prompts |
| Semantic predicate evaluation (within gate evaluation) | `evaluate_gate()` → `invoke_agent()` |

### The Critical Boundary

Python does all I/O, validation, state management, and orchestration. Claude does domain reasoning and content generation. Claude never writes to disk (in TAPM mode, only Read and Glob tools are granted). Python validates and writes Claude's output.

---

## 5. Repo-Local Skills/Agents Visibility to Claude Code

### Current State (Operationally Validated)

Claude Code does **NOT** natively discover repo-local skill/agent files:

1. **Skills**: `.claude/skills/` files use flat `.md` format with domain-specific frontmatter (`skill_id`, `reads_from`, `writes_to`). Claude Code expects `.claude/skills/<name>/SKILL.md` with standard frontmatter (`name`, `description`). Zero repo-local skills are discovered.

2. **Agents**: `.claude/agents/` files use flat `.md` with domain frontmatter (`agent_id`, `phase_id`, `node_ids`). `claude agents` lists only built-in agents. `--agent <name>` silently ignores unknown agents.

3. **Slash commands**: Unavailable in `-p` mode. The Skill tool only sees built-in skills.

### Architectural Consequence

The runtime **cannot rely on Claude Code's native discovery**. Instead, Python reads skill/agent specs from disk and embeds them into the prompt. This is the fundamental design decision: skill `.md` files are prompt source material, not Claude Code skill definitions.

### For Your New DAG Runner

- Don't assume Claude Code will load your skill definitions natively
- Build your own spec-loading layer that reads `.md` files and injects them into prompts
- Keep skill/agent files as specifications, not executable code
- If/when Claude Code adds reliable repo-local discovery, this becomes a third execution mode

---

## 6. Path-Bounded File-Read Enforcement

### Problem

`--tools "Read"` grants Read access to ALL files on disk. No CLI flag or configuration option restricts which file paths the Read tool may access.

### Current Enforcement (Prompt-Based + Post-Hoc Audit)

1. TAPM prompt lists **only** the declared `reads_from` paths
2. Skill spec includes explicit boundary instructions: *"Read only the files listed in the Declared Inputs section. Do not read files outside the declared set."*
3. Only `Read` and `Glob` tools are enabled — `Write`, `Edit`, `Bash` are NOT granted
4. Post-hoc: audit `--output-format stream-json` event log for Read tool invocations; compare against declared `reads_from`

### For Your New DAG Runner

- Accept that hard path sandboxing is not available from Claude Code
- Enforce via prompt instructions + post-execution audit
- Never grant Write/Edit/Bash tools to skills
- Consider PreToolUse hooks as a potential future enforcement mechanism
- Log all tool invocations for compliance auditing

---

## 7. Native Claude Code Backend vs. `claude -p` Usage

### The Two Modes

**Mode A — `cli-prompt` (current default):**
All inputs serialized into the prompt, piped to `claude -p` via stdin. Claude is a stateless text function. No tools.

**Mode B — `tapm` (Tool-Augmented Prompt Mode):**
Only task metadata + skill spec in prompt (~5-30KB). `claude -p --tools "Read,Glob"` enabled. Claude reads declared inputs from disk on demand.

### Native Claude Code Backend (DEFERRED — not operationally viable)

Would require: skill discovery, agent discovery, slash-command automation, path-bounded enforcement, session bootstrap. All unproven. See Section 5 above.

### Transport Implementation

```python
def invoke_claude_text(*, system_prompt, user_prompt, model, max_tokens, timeout_seconds=300, tools=None) -> str:
    cmd = ["claude", "-p", "--model", model]
    if tools:
        cmd.extend(["--tools", ",".join(tools)])
    # System prompt: --system-prompt flag when <24KB, else embedded in user_prompt
    # User prompt: always via stdin
    completed = subprocess.run(cmd, input=user_prompt, capture_output=True, text=True, timeout=timeout_seconds)
    # Validate: non-zero exit → error, empty stdout → error
    return completed.stdout
```

### Key Design Decisions

- No Anthropic API key required — uses Claude Code Max subscription
- System prompt falls back to stdin embedding when >24KB (OS command-line limits)
- Structured exception hierarchy: `ClaudeTransportError` → `ClaudeCLIUnavailableError` | `ClaudeCLITimeoutError`
- Transport module has ZERO knowledge of skills, agents, gates, or workflow

---

## 8. Bottleneck Diagnosis

### Root Causes Identified

1. **No input slicing**: Entire grouped JSONs (338-794KB, 64 topics) serialized when only 1 topic (~5KB) matters
2. **No file-reading delegation**: `claude -p` without tools is text-in/text-out — every byte must be in the prompt
3. **Redundant re-serialization**: Same inputs serialized per-skill within an agent's sequence

### Measurement Protocol

- **Classification must use runtime telemetry, not static estimates.** Original estimates (15KB, 10KB) were based on declared `reads_from` sizes; actual prompts measured at 74-78KB, causing 300s timeouts with zero output.
- Track: `len(system_prompt)`, `len(user_prompt)`, elapsed time, timeout events
- Write timeout diagnostics to `.claude/skill_diag/` for post-mortem analysis

### Prompt Assembly Pipeline (the actual bottleneck)

```
_resolve_inputs()              → reads ALL files from every reads_from path into memory
  _resolve_directory_recursive() → recurses directories with 600KB text budget, 400KB per-PDF
_assemble_skill_prompt()       → serializes everything into system_prompt + user_prompt
invoke_claude_text()           → pipes entire prompt through subprocess stdin
```

### For Your New DAG Runner

- Instrument prompt sizes from day one
- Set hard prompt-budget limits: cli-prompt <50KB, TAPM <30KB
- Never classify skills by estimated input size — measure actual prompts
- Build input slicing before you need it, not after timeouts start

---

## 9. Tool-Augmented Prompt Mode (TAPM) Requirements

### What TAPM Is

The existing `claude -p` transport with two additions:
1. `--tools "Read,Glob"` enabled for selected skills
2. Prompt restructured to provide task metadata and skill spec WITHOUT serializing input file contents

### What TAPM Is NOT

- Not a "native Claude Code backend"
- Does not depend on Claude Code discovering skill definitions
- Does not use slash commands, Skill tool, or Agent tool
- Is an enhancement to the existing CLI transport

### Execution Model

```
run_skill(skill_id, ...)
  if mode == "tapm":
    Phase A': Build TAPM prompt (~5-30KB):
              - Skill spec (read from .claude/skills/{skill_id}.md by Python)
              - Task metadata: node_id, run_id, declared reads_from paths, writes_to
              - Output schema requirements + schema hints
              - Input-boundary instructions
              - Caller-supplied context (from invoking agent)
    Phase B': invoke_claude_text(tools=["Read", "Glob"])
              → Claude reads declared inputs from disk as needed
              → Returns structured JSON in stdout
    Phase C': Receive stdout
    Phase D:  _extract_json_response()  [UNCHANGED]
    Phase E:  _validate_skill_output()  [UNCHANGED]
    Phase F:  _atomic_write()           [UNCHANGED]
  else:
    Phase A-F: [existing cli-prompt path]
```

### Mode Selection

Per-skill, via `execution_mode` field in skill catalog YAML:
```yaml
- id: call-requirements-extraction
  execution_mode: tapm   # or "cli-prompt" (default)
```

One-line rollback: change the field back to `"cli-prompt"`.

### Migration Classification Table

| Classification | Criteria | Example |
|---|---|---|
| `tapm` — migrate first | Actual prompt >50KB, high waste ratio | `call-requirements-extraction` (800KB prompt, 5KB relevant) |
| `tapm` — migrate later | Actual prompt 30-80KB, moderate benefit | `concept-alignment-check` |
| `cli-prompt` — never migrate | Actual prompt <30KB, well-bounded inputs | `wp-dependency-analysis` |
| Permanently external | Deterministic, no Claude reasoning | Gate evaluation, schema validation, atomic writes |

---

## 10. Prompt Assembly Pipeline

### CLI-Prompt Mode

```python
def _assemble_skill_prompt(skill_spec, inputs, run_id, writes_to, constraints, repo_root):
    system_prompt = "You are a skill execution engine..."
    system_prompt += constitutional_constraints
    system_prompt += run_id/schema_id instructions (conditional on artifact type)

    user_prompt = "# Skill Execution Specification\n" + skill_spec
    user_prompt += "# Canonical Inputs\n"
    for path, content in inputs.items():
        user_prompt += f"## {path}\n```json\n{json.dumps(content)}\n```"
    user_prompt += "# Output Requirements\n" + writes_to + schema instructions
    return system_prompt, user_prompt
```

### TAPM Mode

```python
def _assemble_tapm_prompt(skill_spec, skill_id, run_id, reads_from, writes_to, ...):
    system_prompt = "You are a skill execution engine..."
    system_prompt += "## Tool Access and Input Boundary\n"
    system_prompt += "Read ONLY the files listed in Declared Inputs..."
    system_prompt += constitutional_constraints
    system_prompt += schema_hints (looked up from artifact_schema_specification.yaml)

    user_prompt = "# Skill Execution Specification\n" + skill_spec
    user_prompt += "# Task Metadata\n" + skill_id, run_id, node_id
    user_prompt += "# Declared Inputs\n"  # paths only, NOT contents
    for path in reads_from:
        user_prompt += f"- {absolute_path}"
    user_prompt += "# Caller-Supplied Context\n"  # content from invoking agent
    user_prompt += "# Output Requirements\n" + schema_hints
    return system_prompt, user_prompt
```

### Key Differences

| Aspect | CLI-Prompt | TAPM |
|--------|-----------|------|
| Input delivery | Serialized in prompt | Paths listed; Claude reads from disk |
| Prompt size | 50-800KB | 5-30KB |
| Tools granted | None | Read, Glob |
| System prompt overflow | Embedded in user prompt when >24KB | Usually fits in --system-prompt |
| Caller context | Merged into resolved inputs | Rendered as separate section |

---

## 11. Artifact Write Discipline

### The Invariant

The governed runtime — not Claude — controls all artifact writes. Claude produces candidate output as structured JSON in stdout. The write pipeline accepts or rejects this output.

### Write Pipeline

```
Claude response (stdout text)
  → _extract_json_response()     # find JSON in response text
  → _validate_skill_output()     # schema validation
      - run_id present and correct
      - schema_id present and correct
      - no artifact_status field (forbidden)
      - all required fields present
      - no extra unknown fields (configurable)
  → _atomic_write()              # temp file + os.replace()
  → SkillResult with outputs_written
```

### Atomic Write Semantics

```python
# Write to temp file first, then atomic rename
with tempfile.NamedTemporaryFile(dir=target_dir, delete=False, suffix=".tmp") as tmp:
    tmp.write(json_bytes)
os.replace(tmp.name, canonical_path)  # atomic on same filesystem
```

### TAPM Write Safety

In TAPM mode, `--tools "Read,Glob"` does NOT include Write or Edit. Claude **cannot write to disk**. This is stronger than a native backend where Claude would have repo write access.

### For Your New DAG Runner

- Never let Claude write directly to disk
- Validate all output before writing
- Use atomic writes (temp + rename) to prevent partial artifacts
- Define a schema validation layer between Claude's response and disk writes
- Log every artifact write with path and size

---

## 12. Operationally Unproven Assumptions (Claude Code Platform)

These are the five assumptions that would need to be proven before a "native Claude Code backend" could replace the current transport. They apply to any project considering native Claude Code integration.

### 12.1 Repo-Local Skill Discovery

Claude Code does not discover flat `.md` skill files with domain frontmatter. Expected format: `.claude/skills/<name>/SKILL.md` with standard frontmatter. **Status: UNPROVEN.**

### 12.2 Repo-Local Agent Discovery

`claude agents` shows only built-in agents. Repo-local `.claude/agents/` files are invisible. `--agent <name>` silently ignores unknown agents. **Status: UNPROVEN.**

### 12.3 Slash-Command Automation in Non-Interactive Mode

`/skill-name` is interactive-only. No `--skill` CLI flag exists. The Skill tool in `-p` mode only sees built-in skills. **Status: UNPROVEN.**

### 12.4 Session Bootstrap Requirements

Per-session initialization overhead, state persistence across skill invocations, one-shot `-p` discovery behavior — all need measurement. **Status: UNPROVEN.**

### 12.5 Path-Bounded File-Read Enforcement

`--tools "Read"` grants access to ALL files. `--allowedTools` and `--permission-mode` operate at tool granularity, not path granularity. Candidates: PreToolUse hooks, `--add-dir` as exclusive constraint, Agent SDK `tool_approval_callback`. **Status: UNPROVEN.**

---

## 13. Runtime Bundling

### Catalog-Driven Configuration

All runtime configuration is catalog-driven, not hardcoded:

- **Skill catalog** (`skill_catalog.yaml`): `id`, `reads_from`, `writes_to`, `constitutional_constraints`, `execution_mode`, `used_by_agents`
- **Agent catalog** (`agent_catalog.yaml`): `id`, `reads_from`, `writes_to`, `must_not`, `invoked_skills`, `phase_id`, `node_ids`
- **Compiled manifest** (`manifest.compile.yaml`): `node_registry` (nodes → agents, skills, gates, dependencies), `artifact_registry` (artifacts → producers, tiers, gate dependencies)
- **Artifact schema specification** (`artifact_schema_specification.yaml`): canonical paths, schema_id values, required fields, field types
- **Gate rules library** (`gate_rules_library.yaml`): predicates per gate, deterministic vs. semantic, evaluation order

### Caching Strategy

All catalogs and specs are loaded once and cached per `repo_root`:
```python
_catalog_cache: dict[str, list[dict]] = {}  # keyed by str(repo_root)
```

### Runtime State Persistence

- Per-run state in `.claude/runs/<run-id>/`: `run_manifest.json`, `run_summary.json`
- Node states, gate results, failure metadata persisted to `RunContext`
- Gate results written as durable artifacts to Tier 4

---

## 14. Boundaries and Scope

### What Must Remain External (Never Modified by Migration)

| Module | Responsibility |
|---|---|
| `dag_scheduler.py` dispatch loop | DAG ordering, readiness checking, stall detection |
| `gate_evaluator.py` | Gate predicate evaluation |
| `gate_library.py` | Gate predicate logic |
| `run_context.py` | Node state persistence, HARD_BLOCK propagation |
| `runtime_models.py` | SkillResult, AgentResult, NodeExecutionResult contracts |
| `manifest_reader.py` | YAML manifest loading |
| `node_resolver.py` | Manifest node lookup (agent_id, skill_ids, gates) |

### Behavioral Properties That Must Be Preserved

| Property | How Verified |
|---|---|
| Fail-closed | `_validate_skill_output()` unchanged; no silent repair |
| Budget gate mandatory blocking | `_HARD_BLOCK_GATE` logic unchanged |
| No fabrication | Constitutional constraints in skill spec |
| Atomic writes | temp file + rename |
| Durable state in Tier 4 | Canonical path writes |
| Gate independence from agents | `evaluate_gate()` called only by scheduler |
| Write-tool exclusion (TAPM) | Only Read,Glob granted |

---

## 15. Context Access and Containment

### Context Access Invariant

TAPM execution is constrained to declared `reads_from` inputs only. This is a mandatory execution invariant, not a soft guideline.

### Enforcement Layers

1. **Prompt-level**: TAPM prompt lists only declared paths; includes explicit boundary instructions
2. **Tool-level**: Only Read and Glob enabled; Write/Edit/Bash excluded
3. **Post-hoc audit**: Compare Read tool invocations against declared `reads_from` set
4. **Schema validation**: Output validated against expected schema regardless of what was read

### Prompt-Budget Enforcement (Permanent Rule)

- CLI-prompt skills: total prompt <50KB
- TAPM skills: TAPM prompt <30KB; declared `reads_from` must remain bounded
- Step 0 call slicing is mandatory input bounding strategy
- TAPM access does NOT justify broad corpus ingestion

### Gate-Enforcement Containment

Gate-enforcement skills must consume only:
- The canonical phase artifact being evaluated
- The minimal gate-relevant context
- Declared inputs only (specific files in `reads_from`)

Gate-enforcement must NOT be fed broad phase output directories, large Tier 2 corpora, or unrelated artifacts.

---

## 16. DAG Runner Structural Validity and Controlled Execution

### Five-Step Dispatch Contract

Every node dispatch follows this exact sequence:

```
1. Set state to "running" — persist to RunContext
2. Evaluate entry gate (if defined)
   → On failure: state = "blocked_at_entry", return immediately
   → Agent body is NEVER invoked
3. Execute node body via run_agent()
   → On failure OR can_evaluate_exit_gate == False:
     state = "blocked_at_exit", failure_origin = "agent_body"
     Skip exit gate, return immediately
4. Evaluate exit gate
   → On pass: state = "released"
   → On failure: state = "blocked_at_exit", failure_origin = "exit_gate"
5. Return NodeExecutionResult
```

### Node State Machine

```
pending → running → released              (happy path)
pending → running → blocked_at_entry      (entry gate failed)
pending → running → blocked_at_exit       (agent or exit gate failed)
pending → hard_block_upstream             (budget gate failure propagation)
```

### Readiness Checking

A node is ready when:
- All upstream dependency nodes are `released`
- Entry gate prerequisites are satisfied (durable gate result artifacts exist)
- Node is not `hard_block_upstream`

### Phase-Scoped Execution

```bash
python -m runner --run-id <uuid> --phase 1  # only Phase 1 nodes dispatched
```

- Only nodes in the requested phase are eligible
- Full DAG prerequisites still checked (no bypass)
- Each invocation uses a new `--run-id`
- Prior run states bootstrapped from durable Tier 4 gate result artifacts

### Stall Detection

When no nodes can make progress (all pending nodes have unsatisfied dependencies and no running nodes can release them), the scheduler declares stall:
- `overall_status = "aborted"`
- `stalled_nodes` array explains which upstream conditions are unmet
- Exit code 2

### HARD_BLOCK Propagation

When `gate_09_budget_consistency` fails (either exit gate or agent body failure), all Phase 8 nodes are immediately frozen with `hard_block_upstream`. This is a special constitutional blocking mechanism.

---

## 17. Drifts and Contradictions

### Architecture Drift Risks

1. **Catalog/spec divergence**: Skill catalog declares `reads_from` but skill spec mentions different files → prompt contains paths that don't match what Claude reads
2. **Mode misclassification**: A skill classified as `cli-prompt` actually has >50KB prompts → timeouts without diagnosis
3. **Gate predicate staleness**: Gate predicates check for artifacts that the skill no longer produces → false failures
4. **Agent skill-list drift**: Manifest declares skills for a node that don't match what the agent spec describes → sequencing errors

### Contradiction Detection

- **Tier hierarchy violations**: Lower tier contradicting higher tier must be logged and surfaced, never silently resolved
- **Gate/skill inconsistency**: Skill writes artifacts to paths that gates don't check, or gates check paths that skills don't write
- **Schema evolution**: Artifact schema changes without updating validation logic → false passes or false failures

### Constitutional Authority

All conflicts are resolved by the authority hierarchy:
```
1. Explicit human instruction (in-session, named override only)
2. CLAUDE.md (constitution)
3. Tier 1-4 source materials
4. Workflows > Skills > Agent memory
```

A workflow, skill, or agent that contradicts the constitution is invalid regardless of whether it produces correct outputs.

---

## 18. Deterministic Input Bounding (Call Slicer / Step 0)

### Pattern

A pure Python preprocessing step that runs BEFORE any Claude invocation, BEFORE TAPM prompt assembly, and BEFORE any skill or agent executes. It deterministically pre-selects the exact input slice so downstream steps operate over bounded data only.

### Implementation

```python
def generate_call_slice(repo_root: Path) -> Path:
    # 1. Read selected_call.json → get topic_code and work_programme
    # 2. Resolve grouped JSON path from deterministic lookup table
    # 3. Parse grouped JSON
    # 4. Linear scan: find the single matching entry
    # 5. Fail-closed: no match → raise exception
    # 6. Assemble bounded slice object with provenance metadata
    # 7. Validate output size < 20KB
    # 8. Write to canonical output path
    return output_path
```

### Properties

- **Deterministic**: Same inputs → same output (modulo timestamp)
- **Fail-closed**: Missing inputs, no match, or oversized output → exception
- **Independent of TAPM**: Works with either execution mode
- **Idempotent**: Running twice produces identical output
- **Rollback**: Delete the module and revert 5-line scheduler call

### Input Breadth Reduction Chain

```
Without Step 0 + Without TAPM:  338-794KB serialized in prompt
Without Step 0 + With TAPM:     338-794KB read via Read tool
With Step 0    + With TAPM:     5-8KB read via Read tool (pre-sliced)
With Step 0    + Without TAPM:  5-8KB serialized in prompt
```

### For Your New DAG Runner

- Identify your equivalent of "grouped JSONs" — large input corpora where only a small slice is relevant
- Build deterministic slicing in Python before any LLM invocation
- Don't rely on the LLM to navigate large inputs even with tool access
- Step 0 is orthogonal to TAPM: it reduces input breadth; TAPM reduces serialization

---

## 19. Failure Semantics

### Failure Origin Classification

Every node-level failure is classified by exactly one `failure_origin`:

| Origin | When | Node State | Exit Gate Evaluated? |
|--------|------|-----------|---------------------|
| `entry_gate` | Entry gate returns status != "pass" | `blocked_at_entry` | No |
| `agent_body` | Agent returns failure OR `can_evaluate_exit_gate == False` | `blocked_at_exit` | No |
| `exit_gate` | Exit gate returns status != "pass" after successful agent | `blocked_at_exit` | Yes |

### Exit Gate Skip Rule

Exit gate evaluation is skipped if and only if:
1. Entry gate failed
2. Agent body failed
3. `can_evaluate_exit_gate` is `False`

In ALL other cases — specifically when `AgentResult.status == "success"` AND `can_evaluate_exit_gate == True` — exit gate evaluation proceeds unconditionally.

### `can_evaluate_exit_gate` Determination

Determined by inspecting **actual file-system state**, not by optimistic assumption:

```python
def _determine_can_evaluate_exit_gate(node_id, repo_root):
    for artifact_path in get_artifacts_produced_by_node(node_id):
        if is_directory(artifact_path):
            if not exists or no .json files inside → return False
        else:
            if not exists or not valid JSON or empty → return False
    return True
```

### CONSTITUTIONAL_HALT Propagation

A `CONSTITUTIONAL_HALT` from any skill causes the agent to halt immediately:
```python
AgentResult(status="failure", failure_category="CONSTITUTIONAL_HALT", can_evaluate_exit_gate=False)
```
The scheduler treats this identically to any other agent-body failure.

### Fail-Closed Principle

The system prefers explicit gate failure over fabricated completion. A declared failure is an honest and correct output. A fabricated completion is a constitutional violation.

- Malformed output → `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT")`
- Missing inputs → gate failure, not optimistic inference
- Empty Claude response → transport error, not silent skip
- No silent repair of Claude responses

---

## 20. Run Summary and Observability

### Run Summary Contract

Every run produces `run_summary.json`:

```json
{
  "run_id": "...",
  "overall_status": "pass|partial_pass|fail|aborted",
  "node_states": {"n01_call_analysis": "released", ...},
  "terminal_nodes_reached": [...],
  "stalled_nodes": [...],
  "hard_blocked_nodes": [...],
  "gate_results_index": {"gate_id": "path/to/result.json"},
  "node_failure_details": {
    "node_id": {
      "failure_origin": "exit_gate",
      "exit_gate_evaluated": true,
      "failure_reason": "...",
      "failure_category": "..."
    }
  },
  "dispatched_nodes": [...]
}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All terminal nodes released |
| 1 | Partial or failed (some gates failed) |
| 2 | Aborted (stall detected) |
| 3 | Configuration error |

### Diagnostic Artifacts

- Timeout diagnostics: `.claude/skill_diag/{skill_id}_{run_id}_timeout_meta.json`
- Transport failures: `.claude/skill_diag/{skill_id}_{run_id}_transport_fail.txt`
- Gate results: `docs/tier4_.../gate_result.json` with predicate-level pass/fail

---

## 21. Invariant Checklist (Verify After Every Change)

| # | Invariant | Verification Method |
|---|-----------|-------------------|
| 1 | Scheduler blocks invalid nodes | Run with missing upstream artifact → confirm `blocked_at_entry` |
| 2 | Gate failure prevents downstream | Inject malformed artifact → confirm exit gate fails, downstream `hard_block_upstream` |
| 3 | Artifacts reproducible from same inputs | Run same skill both modes → both pass `_validate_skill_output()` |
| 4 | No undeclared file reads | Audit stream-json log, compare against `reads_from` |
| 5 | No undeclared file writes | Confirm no Write tool; verify `git status` clean |
| 6 | Run summary deterministic | Compare `run_summary.json` between modes |
| 7 | Artifact validation external | Confirm validation called after response parsing, both modes |
| 8 | Gate evaluation external | Confirm no `evaluate_gate()` calls in skill/agent runtime |
| 9 | Fail-closed intact | Send malformed response → confirm `SkillResult(status="failure")` |
| 10 | Mode choice doesn't alter DAG semantics | Same manifest + inputs → same node state transitions |

---

## 22. Additional Features from README / Migration Plan

### 22.1 Dry-Run Mode

Preview which nodes are ready without executing:
```bash
python -m runner --run-id <uuid> --dry-run [--phase 1]
```
Creates run context but does not evaluate gates or execute node bodies.

### 22.2 JSON Output Mode

Machine-readable event stream:
```bash
python -m runner --run-id <uuid> --json
```
Each line is a self-contained JSON event: `run_start`, `ready`, `dispatch`, `summary`.

### 22.3 Phase-Scoped Continuation (Bootstrap)

`bootstrap_phase_prerequisites()` seeds upstream nodes as `released` from durable Tier 4 gate result artifacts, enabling phase-by-phase execution with new `--run-id` per invocation. This is a **seed step**, not resume logic.

### 22.4 Manifest Graph (Read-Only DAG)

`ManifestGraph` is a read-only in-memory graph built from `manifest.compile.yaml`:
- `is_ready(node_id)` — check all upstream dependencies satisfied
- `entry_gate(node_id)` / `exit_gate(node_id)` — gate ID lookup
- Topological ordering for dispatch sequence
- No mutation after construction

### 22.5 Gate Architecture (Deterministic + Semantic)

Gates evaluate predicates in two tiers:
1. **Deterministic predicates**: File existence, JSON schema conformance, field presence, cross-artifact coverage, timeline validity, dependency cycles — evaluated first
2. **Semantic predicates**: Claude-invoked checks for constitutional compliance, no fabrication, no unresolved conflicts — evaluated only if all deterministic predicates pass

This two-tier approach avoids expensive Claude invocations when cheap checks already fail.

### 22.6 Timeout-Specific Diagnostics

On Claude CLI timeout, the runtime writes a structured diagnostic bundle:
```
.claude/skill_diag/{skill_id}_{run_id}_timeout_meta.json   # metadata
.claude/skill_diag/{skill_id}_{run_id}_timeout_system.txt  # system prompt
.claude/skill_diag/{skill_id}_{run_id}_timeout_user.txt    # user prompt
```
This enables post-mortem analysis of what was sent when a timeout occurs.

### 22.7 Skill Applicability Guard

Some skills are phase-sensitive: `proposal-section-traceability-check` audits Tier 5 deliverables, which don't exist until Phase 8. The guard checks actual disk state (not phase number) and returns "not_applicable" instead of `MISSING_INPUT` when the skill's targets don't yet exist.

### 22.8 Contextual Descriptor Detection

Some skills declare `reads_from` entries that are prose descriptions rather than filesystem paths (e.g., `"Any phase context requiring durable recording"`). The runtime detects these via whitespace heuristic and skips them during path resolution.

### 22.9 Schema-Aware Output Validation

The runtime looks up artifact schemas from `artifact_schema_specification.yaml` to:
- Determine whether `run_id` and `schema_id` fields are required for each artifact
- Include schema hints in TAPM prompts so Claude knows what fields to produce
- Validate that output conforms to the expected schema before writing

### 22.10 Prompt-Budget Enforcement as Permanent Rule

TAPM's ability to read from disk does NOT justify unbounded corpus ingestion:
- Every skill invocation must operate on a declared, bounded set of inputs
- Step 0 deterministic slicing is mandatory
- `reads_from` sets must remain bounded even when Claude can read on demand
- Input budgets apply to both modes

---

## 23. Checklist for Bootstrapping Your New DAG Runner

### Minimum Viable Features (in implementation order)

1. **Runtime contracts**: Define your SkillResult, AgentResult, NodeExecutionResult equivalents as frozen/immutable data types with a closed failure category taxonomy
2. **Transport layer**: `invoke_claude_text()` — subprocess wrapper for `claude -p` with timeout handling, error classification, and optional `--tools` flag
3. **Skill runtime**: Load skill spec from disk, assemble prompt, invoke transport, parse JSON response, validate schema, atomic write
4. **Agent runtime**: Load agent spec, sequence skill invocations, propagate failures, determine gate readiness from disk state
5. **Gate evaluator**: Deterministic predicates first, semantic predicates second, external to agents/skills
6. **DAG scheduler**: Manifest graph, topological dispatch, five-step contract, stall detection, run summary
7. **Catalogs**: Skill catalog, agent catalog, artifact schema specification — all YAML, cached per repo_root
8. **Input slicing**: Deterministic preprocessing before any Claude invocation
9. **TAPM mode**: Bounded prompts with tool-augmented file reading
10. **Observability**: Run summary, exit codes, diagnostic artifacts, prompt size logging

### Design Principles to Carry Forward

- **Specs are not code**: `.md` files are prompt source material loaded by Python, not executable definitions
- **Python owns all I/O**: Claude never writes to disk; Python validates and writes
- **Fail-closed everywhere**: Missing input → failure, not inference. Malformed output → failure, not repair
- **Measure, don't estimate**: Prompt sizes must be measured from runtime telemetry
- **Catalogs, not hardcoding**: All skill/agent/artifact configuration is catalog-driven YAML
- **Layering is non-negotiable**: Scheduler → Agent → Skill → Transport, no exceptions
- **Gates are external**: No skill or agent may evaluate its own gate
- **Atomic writes**: temp + rename, never direct write to canonical path
- **Post-hoc auditability**: Log all tool invocations, artifact writes, gate evaluations
