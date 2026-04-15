# Hybrid Architecture Migration Plan

## Context

The proposal orchestrator currently assembles all inputs into a single text prompt piped to `claude -p` via stdin for every skill invocation. This creates a prompt-size bottleneck: for Phase 1 the prompt reaches ~400-800KB (98.5% irrelevant), and for Phase 8 it reaches 150-500KB per skill invocation with redundant re-serialization across sequential skills. The root causes are: (1) no call-level input slicing — entire grouped JSONs with 64+ topics are serialized when only 1 matters, (2) `claude -p` without `--tools` cannot read files from disk so everything must be in the prompt, (3) per-skill re-resolution of the same inputs within an agent's skill sequence.

The migration preserves the DAG scheduler, external gates, external artifact validation, and fail-closed semantics while transitioning heavy reasoning tasks from externally-assembled prompt execution to native Claude Code execution. In the native backend, the external runtime hands off a bounded execution request (~1–5KB of task metadata) and Claude Code operates in its repo-aware environment — loading skill definitions from `.claude/skills/`, reading declared inputs from disk, and producing candidate artifacts for external validation. The external runtime retains exclusive control of scheduling, gate evaluation, artifact validation, and state persistence.

---

## 1. Diagnosis of the Current Bottleneck

### 1.1 Prompt Assembly Pipeline

The bottleneck is in `runner/skill_runtime.py` lines 563-664 (`_assemble_skill_prompt()`). For each skill invocation, the pipeline:

1. `_resolve_inputs()` (line 359) reads ALL files from every `reads_from` path into memory
2. `_resolve_directory_recursive()` (line 432) recurses directories with a 600KB text budget (`DIR_MAX_TEXT_CHARS`, line 75) and 400KB per-PDF (`PDF_MAX_CHARS_PER_FILE`, line 72)
3. `_assemble_skill_prompt()` (line 563) serializes everything into `system_prompt + user_prompt`
4. `invoke_claude_text()` (`claude_transport.py` line 101) pipes the entire prompt through `subprocess.run(["claude", "-p", ...], input=user_prompt)`

### 1.2 Concrete Size Measurements

**Node n01 (`call-requirements-extraction` skill)**:
- `cluster_CL4.grouped.json`: 338KB containing 64 topics — target call occupies 5KB (1.5%)
- `cluster_CL5.grouped.json`: 794KB — even worse ratio
- Application/evaluation form PDFs: up to 400KB text extraction each
- Skill spec: ~33KB
- **Effective prompt: ~400-830KB, of which ~10KB is relevant**

**Node n08a (`proposal_writer` agent, 3 sequential skills)**:
- `reads_from` includes `docs/tier3_project_instantiation/` (entire tree) and `docs/tier4_orchestration_state/phase_outputs/` (entire tree, growing with each phase)
- Each of 3 skills independently re-resolves and re-serializes all inputs
- **Per-skill prompt: 150-500KB, serialized 3 times**

### 1.3 Three Inefficiencies

1. **No input slicing**: Entire grouped JSONs read when only 1 call entry needed
2. **No file-reading delegation**: `claude -p` (without tools) is text-in/text-out — every byte must be in the prompt
3. **Redundant re-serialization**: Same inputs serialized per-skill within an agent's sequence

### 1.4 Why Current Transport Cannot Fix This

`claude -p` without `--tools` treats Claude as a stateless text function. It cannot read files. The `--system-prompt` flag has a 24KB limit (`_MAX_SYSTEM_PROMPT_CLI_LENGTH`, line 58). Everything over that gets embedded in stdin. The transport has no mechanism for selective file access.

**Confirmed from CLI help**: `claude -p` supports `--tools "Read"`, `--output-format json`, `--json-schema`, and `--permission-mode`. These capabilities remain available for the CLI prompt backend. The native Claude Code backend uses a fundamentally different execution model (see Section 2.0).

---

## 2. Target Hybrid Architecture

### 2.0 Anti-Goal: This Migration Is Not a Prompt Wrapper Rename

This migration is **not**:
- Renaming the existing `claude -p` transport and calling it "native"
- Wrapping the same externally-assembled prompt flow in a new adapter name with a smaller prompt
- Adding `--tools "Read"` to `claude -p` and calling that a "native backend"
- Replacing 400KB prompts with 30KB prompts that still externally serialize skill specs, context manifests, and output requirements into a single text prompt

The target backend for heavy reasoning tasks is a **genuine transition from externally-assembled prompt execution to native Claude Code execution** — where Claude Code operates in its repo-aware environment, loads skill and agent definitions from `.claude/skills/` and `.claude/agents/`, reads declared inputs from disk, and produces candidate artifacts. The external governed runtime hands off bounded task metadata, not a serialized corpus prompt.

The existing CLI prompt backend (`invoke_claude_text()` via `claude -p`) remains unchanged for light/bounded skills. The new native backend is a fundamentally different execution model, not a variation of the same transport.

### 2.1 Architecture Diagram

```
UNCHANGED EXTERNAL CONTROL PLANE:
  DAGScheduler._dispatch_node()
    1. set state "running"
    2. evaluate_gate(entry_gate)     [gate_evaluator.py — unchanged]
    3. run_agent(agent_id, ...)      [agent_runtime.py — unchanged orchestration]
       -> run_skill(skill_id, ...)   [skill_runtime.py — backend selection added]
    4. evaluate_gate(exit_gate)      [gate_evaluator.py — unchanged]
    5. return NodeExecutionResult    [runtime_models.py — unchanged contract]

WITHIN run_skill() — TWO BACKENDS:

  Backend A: "native-claude-code" (for input-heavy skills)
    Phase A': Prepare execution request (~1-5KB of task metadata):
              - node_id, skill_id, run_id
              - declared reads_from paths
              - declared writes_to targets
              - expected artifact schemas
              - execution constraints
    Phase B': Invoke native Claude Code execution
              -> Claude Code operates in repo-aware environment
              -> Loads skill definition from .claude/skills/{skill_id}.md
              -> Reads declared inputs from disk (reads_from paths only)
              -> Performs domain reasoning using native repo context
              -> Produces candidate artifact content as structured JSON
    Phase C': Receive candidate output from Claude Code
    Phase D:  _extract_json_response()  [UNCHANGED]
    Phase E:  _atomic_write()           [UNCHANGED]
    Phase F:  return SkillResult        [UNCHANGED]

  Backend B: "cli-prompt" (existing, for light skills)
    Phase A:  _resolve_inputs()         [UNCHANGED]
    Phase B:  _assemble_skill_prompt()  [UNCHANGED]
    Phase C:  _invoke_claude()          [UNCHANGED — invoke_claude_text()]
    Phase D-F: [UNCHANGED]
```

### 2.2 Boundaries

| Responsibility | Owner | Changes? |
|---|---|---|
| DAG dispatch, ordering, stall detection | `dag_scheduler.py` | No |
| Entry/exit gate evaluation | `gate_evaluator.py` | No |
| Gate predicate logic | `gate_library.py` | No |
| HARD_BLOCK propagation (budget gate) | `dag_scheduler.py` | No |
| Node state persistence | `run_context.py` | No |
| Agent spec loading, skill sequencing, context passing | `agent_runtime.py` | No |
| `can_evaluate_exit_gate` (disk inspection) | `agent_runtime.py` | No |
| Backend selection per skill | `skill_runtime.py` | **Yes** — new branching |
| Native execution adapter | New `native_backend.py` | **Yes** — new module |
| Call slicing (pre-execution) | New `call_slicer.py` | **Yes** — new module |
| Execution request builder | New `execution_request.py` | **Yes** — new module |
| Response parsing, schema validation, atomic write | `skill_runtime.py` | No |
| Runtime contracts (SkillResult, AgentResult, etc.) | `runtime_models.py` | No |

### 2.3 Call-Graph Preservation (CLAUDE.md Section 17.1)

The three-layer call graph is preserved without modification:
- Scheduler calls `run_agent()` — never calls skills directly
- `run_agent()` calls `run_skill()` — never calls gates
- `run_skill()` invokes the selected backend — backend implementation changes, contract unchanged
- Gate evaluator called by scheduler only — never by agents or skills

### 2.4 Execution Adapter Contract

The plan introduces a stable **execution backend adapter** abstraction. This is the seam between the governed runtime (scheduler, agent runtime, gate evaluator, validation) and the reasoning backend that performs domain work.

Two adapter implementations exist:

| Adapter | Execution model | Used by |
|---|---|---|
| `cli-prompt` | External prompt assembly → `invoke_claude_text()` via `claude -p` → parse response. Python reads inputs, serializes skill spec + inputs into prompt, Claude is a stateless text function. | Light/bounded skills, gate-enforcement, decision-log-update |
| `native-claude-code` | Bounded execution handoff → Claude Code repo-aware execution → external artifact validation. Python provides task metadata only (~1–5KB). Claude Code loads the skill definition from `.claude/skills/`, reads declared inputs from disk, and performs domain reasoning in its native repo environment. | Input-heavy skills migrated per Section 3.1 |

**Key distinction**: In the `cli-prompt` backend, Python assembles the complete execution context (skill spec + serialized inputs) into a prompt. In the `native-claude-code` backend, Python provides only task identity and constraints — Claude Code assembles its own execution context by loading the skill definition and reading inputs from the repository. This is a genuine difference in execution model, not a prompt-size optimization.

**Execution request contract** — the `native-claude-code` adapter passes:
- Node identity (`node_id`, `skill_id`)
- Declared `reads_from` paths (from skill catalog)
- Declared `writes_to` targets (from skill catalog)
- Expected artifact schemas
- `run_id` and node execution context
- Execution constraints (constitutional rules, output format requirements)

The execution request is bounded task metadata (~1–5KB). It does not contain serialized file contents, the skill specification text, or any pre-read input data. Claude Code loads all of that from the repository.

**Adapter output contract** — both adapters ultimately yield:
- Candidate artifact content (structured JSON) for external validation and write

**Adapter prohibitions** — the adapter must not:
- Evaluate or influence gate outcomes
- Perform artifact validation (that remains in `_validate_skill_output()`)
- Decide node state transitions (that remains in the scheduler)
- Select which files to write (that remains in the governed write path)
- Alter the `SkillResult`, `AgentResult`, or `NodeExecutionResult` contracts
- Decide node release semantics (that remains exclusively with the scheduler)

**Governance preservation in native execution**: Even when Claude Code operates in its native repo-aware environment:
- The scheduler remains the sole authority on node dispatch, ordering, and release
- DAG semantics remain external and are not interpretable by the native backend
- Gate evaluation remains external — Claude Code does not evaluate gates
- Artifact validation remains external — Claude Code produces candidates; the governed runtime accepts or rejects
- Node state transitions remain external — Claude Code does not set node states

**Backend selection is a skill-catalog property.** The scheduler and agent runtime are backend-agnostic. They call `run_skill()`, which reads `execution_backend` from the skill catalog entry and dispatches to the appropriate adapter. Backend selection must not leak into scheduler semantics, gate logic, or agent orchestration.

### 2.5 Context Access Invariant

**Risk**: Native Claude Code execution operates within the full repository working directory. Without explicit containment, Claude can read any file in the repository — including files outside the node's declared input boundary, prior phase artifacts not relevant to the current task, Tier 1/2 source corpora unrelated to the active call, and agent memory or runtime state from `.claude/`.

**Invariant**: Native Claude execution is constrained to declared `reads_from` inputs only. This is a mandatory execution invariant, not a soft guideline.

**Enforcement**:
1. The execution request (Section 2.1, Phase A') enumerates only the declared `reads_from` paths from the skill catalog. No other paths are communicated to Claude Code.
2. The skill definitions in `.claude/skills/` must include explicit input-boundary instructions: *"Read only the files declared in the execution request. Do not read files outside the declared reads_from set."*
3. The execution request is the primary containment mechanism. Claude Code's repo-awareness means it *can* read any file; the execution request and skill definition constrain what it *should* read.
4. Hard sandboxing (e.g., symlinked isolated directory, workspace isolation) is a future hardening option but is not required for initial migration. Execution-request containment plus post-hoc audit is sufficient for migration validation.

**Compliance testing during migration**:
- After each migrated skill execution, audit which files Claude Code actually read during the session.
- Compare every file path read against the skill's declared `reads_from` set.
- Flag any read of an undeclared file as a containment violation.
- Regression: re-run with an intentionally absent declared file to confirm Claude Code does not silently substitute an alternative source from elsewhere in the repository.

### 2.6 Artifact Write Discipline

**Risk**: Native Claude execution could theoretically produce outputs to undeclared paths, create unexpected files, or leave partial artifacts at canonical locations.

**Invariant**: The governed runtime — not Claude — controls all artifact writes. Claude produces candidate output as structured JSON in its response. The existing write pipeline (`_extract_json_response()` → `_validate_skill_output()` → `_atomic_write()`) accepts or rejects this output.

**Write-side constraints**:
1. Native Claude Code execution produces candidate artifact content as structured JSON in its output. It does not write directly to canonical artifact paths. The governed runtime is the sole writer to canonical paths.
2. The execution request specifies `writes_to` targets. Claude Code's output must correspond to these targets. The governed runtime rejects output that does not match declared `writes_to`.
3. The governed runtime writes only to declared `writes_to` targets. Undeclared outputs in the response are rejected by `_validate_skill_output()`.
4. Atomic write semantics (temp file → rename) prevent partial outputs at canonical paths. A failed write leaves no partial artifact.
5. Extra fields, missing required fields, or malformed schema in the response trigger `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT")`.

**Post-write validation**: After every skill execution (both backends), the existing validation pipeline confirms:
- All declared `writes_to` artifacts exist
- All artifacts conform to their declared schema
- No undeclared files were created in canonical output directories

---

## 3. Division of Responsibilities

### 3.1 Node/Skill Decision Table

| Component | Classification | Migrate | Rationale |
|---|---|---|---|
| **n01** `call-requirements-extraction` | native-claude-code | **First** | Highest waste: 338-794KB prompt, 5KB relevant. Call slicing + native read eliminates 98% |
| **n01** `evaluation-matrix-builder` | native-claude-code | Later | Reads evaluation forms (~50KB), benefits from selective reading |
| **n01** `instrument-schema-normalization` | cli-prompt | Never | Small inputs (~15KB), well-bounded |
| **n01** `topic-scope-check` | cli-prompt | Never | Small inputs (~10KB), 2 extracted JSONs |
| **n02** `concept-alignment-check` | native-claude-code | Later | Reads project_brief/ + extracted (~80KB) |
| **n03** `work-package-normalization` | native-claude-code | Later | Reads WP seed + consortium + schema (~30KB) |
| **n03** `wp-dependency-analysis` | cli-prompt | Never | Reads only Phase 3 outputs (~20KB) |
| **n04** `milestone-consistency-check` | cli-prompt | Never | Small: Phase 3+4 outputs (~20KB) |
| **n05** `impact-pathway-mapper` | native-claude-code | Later | 4 paths across tiers (~80KB) |
| **n06** `governance-model-builder` | native-claude-code | Later | Consortium + Phase 3 outputs (~40KB) |
| **n06** `risk-register-builder` | cli-prompt | Never | risks.json + Phase 3-4 (~30KB) |
| **n07** `budget-interface-validation` | cli-prompt | Never | Structured validation, bounded inputs |
| **n08** `proposal-section-traceability-check` | native-claude-code | **First** (with Phase 8) | 200KB+, reads all tiers |
| **n08** `evaluator-criteria-review` | native-claude-code | **First** (with Phase 8) | 100KB+, reads draft + forms |
| **n08** `constitutional-compliance-check` | native-claude-code | **First** (with Phase 8) | 150KB+, reads CLAUDE.md + all outputs |
| `gate-enforcement` | cli-prompt | Never | Deterministic checks, small inputs |
| `decision-log-update` | cli-prompt | Never | Writes only, minimal reads |
| `checkpoint-publish` | cli-prompt | Never | Writes checkpoint, minimal reads |
| `dissemination-exploitation-communication-check` | cli-prompt | Never | Phase 5 + extracted (~30KB) |
| **Gate evaluation** | permanently external | Never | Constitutional: external, deterministic |
| **Schema validation** | permanently external | Never | Constitutional: external, no silent repair |
| **Atomic writes** | permanently external | Never | File I/O, no reasoning |
| **Run context / state persistence** | permanently external | Never | State management |
| **HARD_BLOCK propagation** | permanently external | Never | Scheduler-only responsibility |

### 3.2 Summary Counts

- **Migrate first**: 4 skills (`call-requirements-extraction`, `proposal-section-traceability-check`, `evaluator-criteria-review`, `constitutional-compliance-check`)
- **Migrate later**: 5 skills (`evaluation-matrix-builder`, `concept-alignment-check`, `work-package-normalization`, `impact-pathway-mapper`, `governance-model-builder`)
- **Never migrate**: 9 skills (small/bounded inputs, deterministic checks)
- **Permanently external**: 6 functions (gates, validation, writes, state, HARD_BLOCK)

### 3.3 First Migration Target: `call-requirements-extraction`

The first skill to migrate to the native-claude-code backend is **`call-requirements-extraction`** (node n01). This is not a suggestion; it is the explicit migration-entry strategy.

**Why this skill**:
1. **Highest waste ratio** (98.5%): Prompts are 338–794KB, of which ~5KB is relevant. No other skill has this disproportion.
2. **Single phase, single node**: Executes only in Phase 1 (n01), with no cross-phase input dependencies at runtime. Failure is isolated to one node.
3. **Well-defined outputs**: Produces exactly 6 Tier 2B extracted JSON files with known schemas. Output correctness is mechanically verifiable via `_validate_skill_output()`.
4. **Baseline comparison available**: The existing cli-prompt backend produces reference outputs. Post-migration outputs can be diffed against this baseline to detect quality regressions.
5. **One-line rollback**: Reverting `execution_backend` in `skill_catalog.yaml` restores cli-prompt behavior immediately. No code changes required.
6. **Call slicing synergy**: Step 0 (call slicer) directly targets this skill's input waste, so Steps 0 and 4 validate together as a cohesive unit.

**Why not other candidates**:
- **Phase 8 skills** (`proposal-section-traceability-check`, `evaluator-criteria-review`, `constitutional-compliance-check`) are higher absolute value but depend on all prior phases completing successfully. Debugging a migration failure in Phase 8 requires ruling out 7 prior phases of state. They migrate in Step 6, after the pipeline is proven.
- **Phase 2–6 native-claude-code skills** have moderate input sizes (30–80KB). They benefit from migration but are not the stress test needed to validate the architecture. They migrate in Step 5, after `call-requirements-extraction` has proven the end-to-end path.
- **Gate-enforcement, decision-log-update, and other cli-prompt skills** have small inputs (<20KB) and no migration value. They remain on cli-prompt permanently.

---

## 4. Grouped JSON Input Strategy

### 4.1 Current Waste

`selected_call.json` identifies `topic_code: "HORIZON-CL4-2026-05-DIGITAL-EMERGING-02"`. The `call_analyzer` agent's `reads_from` includes `docs/tier2b_topic_and_call_sources/work_programmes/`. The `_resolve_directory_recursive()` function reads **every file** under that directory tree, including `cluster_CL4.grouped.json` (338KB, 64 topics). Only 5,181 bytes (1.5%) is the target call.

### 4.2 Call Slice Strategy

**Pre-execution step** (new `runner/call_slicer.py`, invoked by scheduler before first dispatch):

1. Read `docs/tier3_project_instantiation/call_binding/selected_call.json` to get `topic_code` and `work_programme` (e.g., `"cluster_digital"`)
2. Map `work_programme` to the grouped JSON directory: `work_programmes/cluster_digital/`
3. Find the grouped JSON file (`cluster_CL4.grouped.json`)
4. Parse and extract the matching call entry from `destinations[].calls[]` where `call_id` matches
5. Write focused slice to `docs/tier2b_topic_and_call_sources/extracted/call_slice.json`

**Slice content** (~5-6KB):
```json
{
  "source_file": "cluster_CL4.grouped.json",
  "destination_title": "...",
  "call_id": "HORIZON-CL4-2026-05-DIGITAL-EMERGING-02",
  "call_title": "...",
  "call_type": "Research and Innovation Actions",
  "expected_outcome": "[full text]",
  "scope": "[full text]",
  "expected_eu_contribution": "...",
  "indicative_budget": ...,
  "deadline": "...",
  ...
}
```

**Complement**: The call extract at `docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.json` (4,158 bytes) already exists with expected_outcomes, scope_research_areas, eligibility_restrictions, etc. Together these two files (~10KB) contain everything the `call-requirements-extraction` skill needs — eliminating 98% of prompt waste.

### 4.3 What Remains for Traceability vs. Runtime

| Artifact | Purpose | Used at runtime? |
|---|---|---|
| `cluster_CL4.grouped.json` (338KB) | Traceability — full work programme source | **No** — not read by native-claude-code skills |
| `call_slice.json` (5KB) | Runtime — focused call data | **Yes** — read by Claude via Read tool |
| `HORIZON-CL4-...json` call extract (4KB) | Runtime — supplementary call detail | **Yes** — read by Claude via Read tool |
| Work programme PDFs (deleted) | Historical — replaced by grouped JSON | **No** |

### 4.4 How Native-Claude Skills Use Call Data

The execution request for a native-claude-code skill declares these `reads_from` paths:
```
Available files:
  docs/tier2b_topic_and_call_sources/extracted/call_slice.json (5KB, json)
  docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-...json (4KB, json)
  docs/tier3_project_instantiation/call_binding/selected_call.json (1KB, json)
```

In native-claude-code execution, Claude Code reads the call_slice.json (~5KB) and call extract (~4KB) from disk. Total: ~10KB read natively vs. 338–794KB externally serialized in a prompt.

---

## 5. Logical Skill/Agent Split Recommendations

### 5.1 Recommended: Split `call-requirements-extraction` Post-Migration

**Current**: Single skill that reads entire `work_programmes/` + `call_extracts/` + forms, produces all 6 Tier 2B extracted files in one Claude invocation.

**Post-migration consideration**: With native-claude-code backend and call slicing, Claude Code reads only ~10KB of focused call data from disk instead of receiving ~400KB serialized in a prompt. At that scale, the current single-skill design works well. **No split needed** — the call slicer eliminates the problem at the source.

### 5.2 Recommended: Scope `proposal-section-traceability-check` Per Invocation

**Current**: Reads ALL of `tier5/proposal_sections/` + ALL extracted files. When invoked 3 times during Phase 8 (n08a, n08b, n08c), each invocation re-reads everything.

**Recommendation**: When migrated to native-claude-code, add a `section_context` parameter in the agent runtime's context passing. The skill spec should instruct Claude: "Read only the section file identified in `section_context`, not all sections." This scopes native execution to relevant files without requiring a formal skill split. The skill remains one skill; its behavior narrows per invocation context.

### 5.3 No Splits Recommended for Other Skills

All other skills have well-bounded inputs or benefit sufficiently from native-claude-code selective reading. No formal splits are necessary. The native-claude-code backend inherently solves the input-scope problem because Claude Code reads only declared inputs from disk rather than receiving a serialized corpus.

---

## 6. Step-by-Step Migration Plan

### Step 0: Call Slice Generator

**Goal**: Eliminate the grouped JSON bottleneck by producing a focused call slice before any node executes.

**Files affected**:
- New: `runner/call_slicer.py` (~100 lines)
- Modified: `runner/dag_scheduler.py` — add `generate_call_slice()` call before dispatch loop (~5 lines)

**What changes**:
- New function `generate_call_slice(repo_root: Path) -> Path`:
  1. Reads `selected_call.json` to get `topic_code` and `work_programme`
  2. Maps work_programme to cluster directory via lookup table
  3. Loads the grouped JSON, searches `destinations[].calls[]` for matching `call_id`
  4. Writes matching entry + destination context to `extracted/call_slice.json`
- `DAGScheduler.run()` calls `generate_call_slice()` before dispatch loop starts

**What doesn't change**: All existing skill_runtime, agent_runtime, gate_evaluator, transport code.

**Dependencies**: None.

**Test procedure**:
```bash
# Unit test
python -m pytest tests/runner/test_call_slicer.py -v

# Manual verification
python -c "from pathlib import Path; from runner.call_slicer import generate_call_slice; print(generate_call_slice(Path('.')))"
cat docs/tier2b_topic_and_call_sources/extracted/call_slice.json | python -m json.tool | head -20

# Verify: output contains HORIZON-CL4-2026-05-DIGITAL-EMERGING-02
# Verify: output is <10KB
# Verify: grouped JSON files are unmodified
```

**Expected output**: `call_slice.json` containing single call entry (~5-6KB).

**Rollback**: Delete `call_slicer.py`, remove the 5-line call in scheduler. No downstream dependencies.

---

### Step 1: Native Execution Adapter — `native_backend.py`

**Goal**: Create the adapter that invokes Claude Code in its native repo-aware execution mode, as distinct from the existing CLI prompt transport.

**Files affected**:
- New: `runner/native_backend.py` (~150 lines)
- New tests: `tests/runner/test_native_backend.py`

**What this module does**:

`native_backend.py` is the adapter between the governed runtime and native Claude Code execution. It is **not** another cli-prompt wrapper. It does not serialize skill specs or input file contents into a prompt.

```python
class NativeExecutionAdapter:
    """Adapter for native Claude Code execution of heavy reasoning tasks.

    Receives a bounded execution request from the governed runtime.
    Invokes Claude Code in its repo-aware environment.
    Claude Code loads the skill definition and reads declared inputs natively.
    Returns candidate artifact content for external validation.
    """

    def execute(self, request: ExecutionRequest) -> NativeExecutionResult:
        """Execute a skill via native Claude Code.

        The execution request contains task metadata only (~1-5KB):
        node_id, skill_id, reads_from, writes_to, run_id, constraints.

        Claude Code loads .claude/skills/{skill_id}.md from the repository,
        reads declared inputs from disk, and produces candidate artifacts.
        """
```

**What makes this different from `invoke_claude_text()`**:

| Property | CLI prompt backend | Native Claude Code backend |
|---|---|---|
| Skill spec delivery | Serialized into prompt by Python | Loaded by Claude Code from `.claude/skills/` |
| Input data delivery | Read by Python, serialized into prompt | Read by Claude Code from disk |
| Prompt content | Skill spec + serialized inputs (150–800KB) | Execution request metadata only (~1–5KB) |
| Claude's role | Stateless text function | Repo-aware agent |
| Context assembly | Done by Python externally | Done by Claude Code from repo |

**What doesn't change**: `invoke_claude_text()` is untouched. All existing callers continue using it. The CLI prompt backend remains the default.

**Dependencies**: None (independent of Step 0).

**Test procedure**:
```bash
# Unit tests (mocked Claude Code invocation)
python -m pytest tests/runner/test_native_backend.py -v

# Verify: execution request contains only task metadata, no serialized file contents
# Verify: adapter does not read input files or skill specs into memory
# Verify: error handling: timeout, invalid response, missing output
# Verify: adapter does not evaluate gates, validate artifacts, or set node state

# Integration smoke test (real Claude Code)
python -c "
from runner.native_backend import NativeExecutionAdapter
from runner.execution_request import ExecutionRequest
req = ExecutionRequest(
    node_id='test', skill_id='topic-scope-check',
    reads_from=[], writes_to=[], run_id='smoke-001',
    constraints={}
)
adapter = NativeExecutionAdapter(repo_root=Path('.'))
# Verify adapter instantiates and accepts request structure
print(req.to_dict())
"
```

**Expected output**: Working adapter module. Smoke test confirms request structure.

**Rollback**: Delete the new module. No callers depend on it.

---

### Step 2: Execution Request Builder

**Goal**: Create the structured execution request that the native backend adapter uses to hand off task metadata to Claude Code.

**Files affected**:
- New: `runner/execution_request.py` (~120 lines)
- New tests: `tests/runner/test_execution_request.py`

**What changes**:
```python
@dataclass
class ExecutionRequest:
    """Bounded task metadata for native Claude Code execution.

    This is NOT a prompt. It contains only task identity and constraints.
    Claude Code loads the skill definition and reads inputs from the repository.
    """
    node_id: str
    skill_id: str              # maps to .claude/skills/{skill_id}.md
    run_id: str
    reads_from: list[str]      # declared input paths from skill catalog
    writes_to: list[str]       # declared output paths from skill catalog
    expected_schemas: dict     # artifact schema requirements
    constraints: dict          # constitutional rules, output format
    repo_root: Path

    def validate_preconditions(self) -> list[str]:
        """Check declared reads_from paths exist. Returns validation errors.
        Does NOT read file contents — only checks existence."""

    def to_dict(self) -> dict:
        """Serialize to dict for handoff. Total size: ~1-5KB."""
```

- For each `reads_from` path: verify existence on disk (stat only, no content read)
- `to_dict()` produces ~1–5KB of structured metadata — node identity, path lists, constraints
- This replaces the old `ContextManifest` concept: instead of building a prompt section listing file paths, the execution request provides task identity so Claude Code can load its own context

**What doesn't change**: `_resolve_inputs()` remains for the CLI prompt backend.

**Dependencies**: None.

**Test procedure**:
```bash
python -m pytest tests/runner/test_execution_request.py -v

# Verify from call-requirements-extraction skill catalog entry:
# - ExecutionRequest.to_dict() output is <5KB
# - validate_preconditions() catches missing reads_from files
# - No file contents are read during request construction
# - skill_id maps to an existing .claude/skills/{skill_id}.md file
```

**Expected output**: ExecutionRequest class that provides bounded task metadata for native execution.

**Rollback**: Delete the new file. No dependencies.

---

### Step 3: Backend Selection in `run_skill()`

**Goal**: Add backend selection within `run_skill()` that dispatches to either the CLI prompt backend or the native Claude Code backend based on skill catalog configuration.

**Files affected**:
- Modified: `runner/skill_runtime.py` — add `_dispatch_native()`, modify `run_skill()` (~80 lines added)
- Modified: `.claude/workflows/system_orchestration/skill_catalog.yaml` — add optional `execution_backend` field definition (no skill changed yet)

**What changes**:

In `run_skill()` (line ~881), after loading the skill catalog entry:
```python
backend = entry.get("execution_backend", "cli-prompt")
if backend == "native-claude-code":
    # Phase A': Build ExecutionRequest from skill catalog entry
    # Phase B': Invoke NativeExecutionAdapter.execute(request)
    #           -> Claude Code loads .claude/skills/{skill_id}.md
    #           -> Claude Code reads declared inputs from disk
    #           -> Returns candidate artifact JSON
    # Phase C': Receive candidate output
else:
    # Existing Phases A-C (unchanged — cli-prompt backend)
```

The native path does **not** assemble a prompt. It builds an `ExecutionRequest` (~1–5KB of task metadata) and delegates to `NativeExecutionAdapter.execute()`. Claude Code loads the skill definition and inputs from the repository — the governed runtime does not read, serialize, or embed them.

**What doesn't change**:
- `run_skill()` function signature and return type
- `SkillResult` contract
- Phases D-F (response parsing, validation, atomic write) — shared by both backends
- All existing skills default to `"cli-prompt"` — zero behavioral change

**Dependencies**: Steps 1 (native adapter) and 2 (execution request).

**Test procedure**:
```bash
python -m pytest tests/runner/test_skill_runtime.py -v  # ALL existing tests pass
python -m pytest tests/runner/test_skill_runtime_native.py -v  # new native-backend tests

# Verify: existing skills with no execution_backend field use cli-prompt
# Verify: native path builds ExecutionRequest, not a serialized prompt
# Verify: native path does not call _resolve_inputs() or _assemble_skill_prompt()
# Verify: Phases D-F (parsing, validation, atomic write) work identically for both backends
```

**Expected output**: `run_skill()` works identically for all existing skills. Native path available but not activated.

**Rollback**: Revert `run_skill()` changes. No skills use native-claude-code yet, so zero behavioral impact.

---

### Step 4: Migrate First Skill — `call-requirements-extraction`

**Goal**: Opt-in the highest-impact skill to the native Claude Code backend. Validate end-to-end.

**Files affected**:
- Modified: `skill_catalog.yaml` — add `execution_backend: "native-claude-code"` to `call-requirements-extraction`
- Modified: `.claude/skills/call-requirements-extraction.md` — add input-boundary instructions

**What changes**:
- Skill catalog gains: `execution_backend: "native-claude-code"`
- Skill spec adds input-boundary instructions:
  ```
  ## Input Boundary
  Read only the files declared in your execution request's reads_from set.
  For call data, use call_slice.json and the call extract file.
  Do not read grouped JSON files or files outside the declared input set.
  ```
- Execution flow: `run_skill()` selects native-claude-code backend → builds ExecutionRequest (~2KB metadata) → Claude Code loads this skill definition from `.claude/skills/call-requirements-extraction.md` → reads declared inputs from disk (~10KB of call data) → returns 6 extracted JSON files as candidate artifacts → external validation and atomic write

**What doesn't change**: `reads_from`, `writes_to`, constraints, output schema, agent runtime, scheduler, gates.

**Dependencies**: Steps 0-3.

**Test procedure**:
```bash
# Full Phase 1 execution
python -m runner --run-id test-native-001 --phase 1 --verbose

# Verify outputs:
cat docs/tier2b_topic_and_call_sources/extracted/call_constraints.json | python -m json.tool | head -5
cat docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json | python -m json.tool | head -5
# ... repeat for all 6 extracted files

# Verify: all 6 files non-empty
# Verify: all entries reference topic_code HORIZON-CL4-2026-05-DIGITAL-EMERGING-02
# Verify: no data from other topics leaked
# Verify: exit gate passes

# Quality comparison (optional):
# Temporarily set execution_backend: "cli-prompt", re-run, diff outputs
```

**Expected output**: Identical Tier 2B extracted files produced via native Claude Code execution — no externally-assembled prompt required for this skill.

**Rollback**: Change `execution_backend` back to `"cli-prompt"` in `skill_catalog.yaml`. One line change, immediate revert.

---

### Step 5: Migrate Phase 2-6 Skills to Native Claude Code

**Goal**: Migrate medium-input skills progressively to native Claude Code execution.

**Files affected**:
- Modified: `skill_catalog.yaml` — set `execution_backend: "native-claude-code"` for: `concept-alignment-check`, `work-package-normalization`, `evaluation-matrix-builder`, `impact-pathway-mapper`, `governance-model-builder`
- Modified: corresponding `.claude/skills/*.md` files — add input-boundary instructions

**What changes**: 5 skills switch to native Claude Code backend. Each is a single-line YAML change + skill spec input-boundary addendum. Claude Code loads each skill definition natively and reads declared inputs from disk.

**What doesn't change**: Scheduler, gates, agent runtime, output contracts, CLI prompt skills.

**Dependencies**: Step 4 validated successfully.

**Test procedure**:
```bash
# Run Phases 2-6 sequentially
python -m runner --run-id test-native-002 --phase 2 --verbose
python -m runner --run-id test-native-003 --phase 3 --verbose
python -m runner --run-id test-native-004 --phase 4 --verbose
python -m runner --run-id test-native-005 --phase 5 --verbose
python -m runner --run-id test-native-006 --phase 6 --verbose

# Verify each phase's exit gate passes
# Verify phase outputs in docs/tier4_orchestration_state/phase_outputs/phase{N}_*/
```

**Expected output**: All phases complete. Mixed backend execution works end-to-end.

**Rollback**: Revert `execution_backend` fields in `skill_catalog.yaml`.

---

### Step 6: Migrate Phase 8 Skills to Native Claude Code (Highest Value)

**Goal**: Migrate the three heaviest cross-cutting skills used by proposal_writer and evaluator_reviewer to native Claude Code execution.

**Files affected**:
- Modified: `skill_catalog.yaml` — set `execution_backend: "native-claude-code"` for: `proposal-section-traceability-check`, `evaluator-criteria-review`, `constitutional-compliance-check`

**What changes**: The 3 heaviest skills (150–500KB externally-assembled prompts each) transition to native Claude Code execution. Claude Code loads each skill definition from `.claude/skills/` and reads declared inputs from disk. The governed runtime receives candidate artifacts, validates them, and writes to canonical paths. This is where the largest absolute improvement occurs — these skills move from externally-serialized corpus prompts to native repo-aware execution.

**What doesn't change**: Scheduler, gates, agent runtime, output contracts.

**Dependencies**: Steps 0-5. Budget gate (Phase 7) must have valid test data for Phase 8.

**Test procedure**:
```bash
# Full Phase 8 execution (requires all prior phases passed)
python -m runner --run-id test-native-008 --phase 8 --verbose

# Verify:
ls docs/tier5_deliverables/proposal_sections/
ls docs/tier5_deliverables/assembled_drafts/
ls docs/tier5_deliverables/review_packets/

# Verify exit gates pass
# Verify no fabricated content (traceability claims trace to tier 1-4 sources)
# Verify no budget-dependent content without gate pass
```

**Expected output**: Phase 8 completes with dramatically smaller prompts per skill invocation.

**Rollback**: Revert 3 `execution_backend` fields in `skill_catalog.yaml`.

---

### Step 7: Documentation and Cleanup

**Goal**: Update CLAUDE.md Section 17 to reflect hybrid architecture. Clean up.

**Files affected**:
- Modified: `CLAUDE.md` — update Section 17.5 ("Claude Runtime Transport Principle") to describe the dual-backend architecture
- Modified: `CLAUDE.md` — add Constitutional Amendment Record for native Claude Code backend

**What changes**:
- Section 17.5.2 updated: skill runtime selects between CLI prompt backend (`invoke_claude_text` — external prompt assembly) and native Claude Code backend (`NativeExecutionAdapter` — repo-aware execution via bounded handoff) based on skill catalog configuration
- Section 17.1.3 updated: skill runtime dispatches to the selected backend; backend selection does not alter the call-graph
- Amendment record: documents the backend architecture change, explicitly states that governance semantics (gates, validation, state, scheduling) are unchanged

**What doesn't change**: All other CLAUDE.md sections. All governance semantics.

**Dependencies**: Steps 0-6 validated.

---

## 7. Per-Step User Test Plan

| Step | Test Type | Command | Success Signal |
|---|---|---|---|
| 0 | Unit | `pytest tests/runner/test_call_slicer.py` | All tests pass; `call_slice.json` exists and is <10KB |
| 0 | Manual | Read `call_slice.json` | Contains only target topic, valid JSON |
| 1 | Unit | `pytest tests/runner/test_native_backend.py` | Adapter accepts execution request; does not serialize inputs |
| 1 | Smoke | Real `NativeExecutionAdapter.execute()` call | Returns candidate artifact JSON |
| 2 | Unit | `pytest tests/runner/test_execution_request.py` | Request <5KB; validates preconditions; no file content read |
| 3 | Unit | `pytest tests/runner/test_skill_runtime.py` | ALL existing tests pass (regression) |
| 3 | Unit | `pytest tests/runner/test_skill_runtime_native.py` | Native path produces valid SkillResult |
| 4 | E2E | `python -m runner --phase 1` | Phase 1 exit gate passes; 6 extracted files populated |
| 5 | E2E | `python -m runner --phase 2` through `--phase 6` | Each exit gate passes |
| 6 | E2E | `python -m runner --phase 8` | Tier 5 deliverables present; review packet valid |
| All | Regression | `pytest tests/ -v` | Full test suite passes after every step |

---

## 8. Risks and Mitigations

### Risk 1: Native Claude Code Invocation Mechanism
**Severity**: High (blocks entire migration)
**Description**: The native backend requires a reliable mechanism to invoke Claude Code in its repo-aware environment, pass a bounded execution request, and capture structured output. The exact invocation mechanism (CLI subcommand, SDK, or other interface) must support: repo-aware execution, native skill loading from `.claude/skills/`, structured output capture, and timeout management.
**Mitigation**: Step 1 implements and tests the `NativeExecutionAdapter` as an isolated module before any skill migrates. If the initial invocation mechanism proves unreliable, the adapter encapsulates the transport — alternatives can be substituted without changing the execution request contract, the output contract, or any upstream code. The adapter's contract (bounded request in, candidate JSON out) is stable regardless of the underlying invocation mechanism.

### Risk 2: Output Format Wrapping
**Severity**: Medium
**Description**: `--output-format json` may wrap Claude's response in session metadata, not just raw JSON.
**Mitigation**: Step 1 tests actual output format. If wrapped, the parser extracts the content field. If unreliable, use `--output-format text` and rely on existing `_extract_json_response()` which already handles JSON-in-text extraction.

### Risk 3: Native Execution Produces Different Quality
**Severity**: Medium
**Description**: Claude Code operating in native repo-aware mode may reason differently than Claude receiving a fully serialized prompt — it may skip declared inputs, read partially, or interpret the skill definition differently.
**Mitigation**: Execution request explicitly declares `reads_from` paths. Skill spec includes input-boundary instructions and mandatory-read declarations. External schema validation catches missing or malformed content. Quality comparison tests in Step 4 validate output parity between backends.

### Risk 4: Increased Latency from Tool Calls
**Severity**: Low-Medium
**Description**: Multiple Read tool calls add overhead vs. single prompt.
**Mitigation**: Call slicing reduces reads to ~3-5 small files. Each Read call adds ~1-2s. Net trade: massive tokenization overhead (100K+ tokens) traded for 5-10 Read calls. Expected: similar or faster for large-input skills.

### Risk 5: Constitutional Compliance
**Severity**: High (governance)
**Description**: CLAUDE.md Section 17 describes current transport. Changing transport without amendment is a violation.
**Mitigation**: Step 7 amends Section 17 per Section 14 rules. All other architectural constraints preserved. Migration only changes transport implementation, not governance semantics.

### Risk 6: Working Directory and Repo Context
**Severity**: Medium
**Description**: Native Claude Code execution must operate in the correct repository root to resolve `reads_from` paths and load skill definitions from `.claude/skills/`.
**Mitigation**: `NativeExecutionAdapter` receives `repo_root` at construction. All `reads_from` paths in the execution request are repo-relative. The adapter ensures Claude Code executes in the correct working directory. Step 1 smoke test validates path resolution.

### Risk 7: Regression in Prompt-Assembly Skills
**Severity**: Low
**Description**: Changes to `run_skill()` could break the existing path.
**Mitigation**: Branching is strictly additive — cli-prompt is the default when `execution_backend` is absent. All 988+ existing tests must pass after every step.

---

## 9. Recommended Rollout Order

### Phase A: Foundation (Steps 0-2) — Zero-Risk, Additive
All three steps are independent additive modules. No existing behavior changes. Can be implemented in parallel.

### Phase B: Backend Integration (Step 3) — Low Risk
Adds branching in `run_skill()` but all skills default to cli-prompt. No behavioral change.

### Phase C: First Validation (Step 4) — MINIMUM VIABLE MIGRATION
One skill (`call-requirements-extraction`) migrates. Validates the entire pipeline end-to-end. **If Step 4 succeeds, the approach is validated. If it fails, rollback is a single YAML line.**

### Phase D: Progressive Rollout (Steps 5-6) — Incremental
Each skill migration is a single YAML field change. Independent rollback per skill.

### Phase E: Documentation (Step 7) — Governance
Constitutional amendment to reflect the validated architecture.

### What Migrates First
`call-requirements-extraction` — highest waste ratio (98.5%), well-isolated (Phase 1 only), easy to validate (6 output files with known schemas). See Section 3.3 for full rationale and why other candidates are deferred.

### What Stays Unchanged Longest
Gate evaluation (`gate_evaluator.py`, `gate_library.py`) and the scheduler dispatch loop (`_dispatch_node()`) are **never modified** in this migration. They remain the external governance backbone.

---

## 10. What Must Remain External and Unchanged

### Modules — Zero Modification

| Module | File | Lines |
|---|---|---|
| DAG dispatch loop | `runner/dag_scheduler.py` | `run()`, `_dispatch_node()` |
| Gate evaluator | `runner/gate_evaluator.py` | `evaluate_gate()` |
| Gate predicate library | `runner/gate_library.py` | All predicates |
| Semantic dispatch | `runner/semantic_dispatch.py` | `invoke_agent()` |
| Run context | `runner/run_context.py` | All state persistence |
| Runtime contracts | `runner/runtime_models.py` | `SkillResult`, `AgentResult`, `NodeExecutionResult` |
| Manifest reader | `runner/manifest_reader.py` | YAML loading |
| Node resolver | `runner/node_resolver.py` | Manifest lookup |

### Contracts — Unchanged

- `SkillResult` fields: `status`, `outputs_written`, `failure_reason`, `failure_category`
- `AgentResult` fields: all unchanged; `can_evaluate_exit_gate` still from disk inspection
- `NodeExecutionResult` fields: all unchanged
- Failure categories: `MISSING_INPUT`, `MALFORMED_ARTIFACT`, `CONSTRAINT_VIOLATION`, `INCOMPLETE_OUTPUT`, `CONSTITUTIONAL_HALT` — no new categories
- Failure origins: `entry_gate`, `agent_body`, `exit_gate` — no new origins
- Five-step dispatch contract: set running → entry gate → agent body → exit gate → return

### Behavioral Properties — Preserved

- Fail-closed: `_validate_skill_output()` unchanged; no silent repair
- Budget gate mandatory blocking: `_HARD_BLOCK_GATE` logic unchanged
- No fabrication: constitutional constraints in system prompt unchanged
- Artifact schema validation: `run_id`, `schema_id`, required field checks unchanged
- Atomic writes: temp file + rename unchanged
- Durable state in Tier 4: canonical path writes unchanged
- Gate independence from agents: `evaluate_gate()` called only by scheduler

### Existing Test Suite — Must Pass After Every Step

- `test_dag_scheduler.py` (94KB, ~200+ tests)
- `test_gate_evaluator.py` (48KB)
- `test_gate_scenarios.py` (51KB)
- `test_runtime_models.py` (10KB)
- `test_skill_runtime.py` (43KB)
- `test_agent_runtime.py` (35KB)

---

## 11. Gate-Enforcement Containment

Gate-enforcement skills (the `gate-enforcement` skill invoked within agent bodies to prepare gate-relevant summaries) must not become the new prompt-bloat sink after input-heavy skills migrate to native-claude-code.

### 11.1 Permitted Inputs for Gate-Enforcement

Gate-enforcement must consume only:
- The **canonical phase artifact** it is evaluating (the specific output file from the current phase)
- The **minimal gate-relevant context**: the gate condition definition from the manifest and the specific evaluation criteria for that gate
- **Declared inputs only**: only the specific files listed in the gate-enforcement skill's `reads_from` in the skill catalog

### 11.2 Prohibited Inputs for Gate-Enforcement

Gate-enforcement must not be fed:
- Broad phase output directories (e.g., the entire `phase_outputs/` tree)
- Large Tier 2 source corpora (e.g., full work programme documents, grouped JSONs)
- Unrelated artifacts from other phases or tiers
- The full execution request or declared inputs of the preceding skill

### 11.3 Purpose of Containment

Gate-enforcement is a compliance-checking step, not a reasoning step. Its prompt must remain bounded (~10–20KB). If gate-enforcement grows to require the same input volume as the skills it checks, the migration has merely shifted the bottleneck rather than eliminating it. Containment here preserves the gains achieved by migrating skills to native-claude-code.

---

## 12. Prompt-Budget Enforcement as Permanent Rule

Moving heavy reasoning tasks to native Claude Code does **not** eliminate the need for prompt and input budgeting. This section establishes a durable architectural rule that survives the migration.

### 12.1 The Rule

**Prompt-budget enforcement remains mandatory for all execution backends.** Native backend access — including Claude's ability to read files from disk via the Read tool — does not justify unbounded corpus ingestion.

### 12.2 Specific Constraints

1. **Bounded input selection remains mandatory.** Every skill invocation — whether cli-prompt or native-claude-code — must operate on a declared, bounded set of inputs. The execution request's declared `reads_from` for native-claude-code skills is the input boundary; it must not grow to include "everything available."
2. **Grouped JSON call slicing remains the preferred runtime strategy** for call-specific work. Even when Claude can read files from disk, serializing 338KB of irrelevant topic data is wasteful. The call slicer (Step 0) produces a focused slice; this pattern applies to any future grouped input source.
3. **Native backend access does not justify broad corpus ingestion.** The ability to read files from disk does not mean all files should be read. Skills must read only what is necessary for their declared task. The execution request's `reads_from` set constrains what is declared available; the skill specification constrains what should actually be read.
4. **Input budgets apply to both backends.** CLI-prompt skills: total prompt <50KB (current budget). Native-claude-code skills: execution request <5KB; declared `reads_from` sets must remain bounded and justified per skill — no skill may declare entire directory trees as inputs without explicit justification.

### 12.3 Why This Rule is Permanent

The prompt-budget bottleneck diagnosed in Section 1 was caused by unbounded input serialization. The native-claude-code backend solves the serialization mechanism but does not solve unbounded input selection. Without this rule, future skill development could re-introduce the same class of waste by listing broad directory trees in `reads_from` and relying on Claude Code to "figure out what's relevant." That pattern violates the declared-input principle (Section 2.5) and reintroduces unbounded input ingestion through `reads_from` over-declaration rather than through prompt serialization.

---

## Invariant checklist after each step

This checklist must be re-verified after every migration step (Steps 0–7). Each invariant protects a governance property that must survive the migration intact.

| # | Invariant | Why it matters | How to verify |
|---|---|---|---|
| 1 | Scheduler still blocks invalid nodes | The DAG scheduler must refuse to dispatch nodes whose entry gates have not passed. If backend changes leak into scheduler logic, invalid nodes could execute. | Run a phase with a deliberately missing upstream artifact. Confirm the node is set to `blocked_at_entry` and never dispatched. |
| 2 | Gate failure still prevents downstream release | Exit gate failure must prevent downstream nodes from executing. If gate evaluation is weakened or bypassed by the new backend, the fail-closed contract breaks. | Inject a malformed phase artifact (e.g., empty JSON). Confirm the exit gate fails and downstream nodes are set to `hard_block_upstream`. |
| 3 | Artifacts remain reproducible from the same declared inputs | Given the same `reads_from` inputs and `run_id`, the same skill must produce structurally equivalent output regardless of backend. Non-determinism in Claude's reasoning is acceptable; structural schema compliance is not. | Run the migrated skill with both backends on identical inputs. Confirm both outputs pass `_validate_skill_output()` and conform to the same schema. |
| 4 | No undeclared file reads occurred | Native Claude Code must not read files outside the declared `reads_from` set. An undeclared read means the skill's output depends on inputs not declared in the skill catalog, breaking traceability. | Audit the native execution session for file reads. Compare every read path against the skill's declared `reads_from` set. Flag any undeclared read. |
| 5 | No undeclared file writes occurred | The governed runtime must write only to declared `writes_to` paths. If extra files appear, the migration has introduced uncontrolled side effects. | After skill execution, compare the working tree (`git status` or directory listing) against declared `writes_to`. Flag any undeclared new or modified file. |
| 6 | Run summary remains deterministic | `run_summary.json` must contain the same structural fields (`node_id`, `final_state`, `failure_origin`, `exit_gate_evaluated`) regardless of backend. If the run summary format changes, downstream tooling and human review break. | Compare `run_summary.json` structure between cli-prompt and native-claude-code runs. Confirm identical keys and state-machine values. |
| 7 | Artifact validation remains external | `_validate_skill_output()` must run after Claude returns, not inside Claude's reasoning. If validation moves into the prompt, Claude can silently self-validate and mask errors. | Confirm that `_validate_skill_output()` is called in `run_skill()` after `_extract_json_response()`, for both backends. Inspect the code path; do not rely on output alone. |
| 8 | Gate evaluation remains external | `evaluate_gate()` must be called by the scheduler, not by agents or skills. If gate evaluation moves into Claude's reasoning, constitutional gate semantics are violated. | Confirm that `evaluate_gate()` call sites are exclusively in `dag_scheduler.py._dispatch_node()`. No new call sites in `skill_runtime.py` or `agent_runtime.py`. |
| 9 | Fail-closed behavior remains intact | When Claude returns malformed output, missing fields, or an empty response, the system must return `SkillResult(status="failure")`. It must not retry, silently repair, or accept partial output. | Send a deliberately malformed Claude response through the native-claude-code path. Confirm `SkillResult.status == "failure"` and `failure_category` is set. |
| 10 | Backend choice does not alter DAG semantics | The same DAG (same manifest, same inputs, same gate conditions) must produce the same node state transitions regardless of which backend executes each skill. If backend choice alters DAG behavior, the scheduler is no longer backend-agnostic. | Run the full DAG with all skills on cli-prompt, then with migrated skills on native-claude-code. Compare `run_summary.json` node states. All `final_state` values must match (modulo non-deterministic Claude reasoning that might cause a gate to pass or fail differently — structural states must match). |
