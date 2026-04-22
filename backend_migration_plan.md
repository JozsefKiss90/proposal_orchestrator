# Hybrid Architecture Migration Plan

## Revision History

| Rev | Date | Change |
|-----|------|--------|
| 1.0 | 2025-04-15 | Original plan: native Claude Code backend as primary migration target |
| 2.0 | 2025-04-15 | Revised after operational validation. TAPM is now the immediate implementation path. True native Claude Code backend deferred to conditional future path pending operational proof. See `native_backend_validation_report.md` for full evidence. |
| 3.0 | 2026-04-15 | Revised Step 0 from brief placeholder into fully defined **Call Slicer (Deterministic Input Bounding Layer)**. Step 0 is now a pure Python preprocessing layer that runs before all Claude invocations, deterministically extracts the target call from grouped JSONs, and bounds downstream inputs to ~10-15KB. Updated `call-requirements-extraction` `reads_from` to reference Step 0 output instead of full grouped JSONs. Updated TAPM interaction, test plan, and rollout order to reflect Step 0's elevated role. All governance semantics unchanged. |

---

## Current Migration Status (as of 2026-04-22, post Phase 5 enricher fix)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 | COMPLETE | Call slicer + TAPM stable |
| Phase 2 | OPERATIONAL | scope_coverage fix → semantic gate stable. Output quality depends on Tier 3 concept content; gate pass does not guarantee evaluator-grade alignment. |
| Phase 3 | OPERATIONAL | CLI mode; structural output stable. Dependency semantics now handled by Phase 4-side normalization layer (not by mutating Phase 3 output). |
| Phase 4 | OPERATIONAL | Remediation validated: normalizer + gantt-schedule-builder + gate hardening + FULL milestone validation. Gate passed on runtime rerun. |
| Phase 5 | REMEDIATED | Core-builder succeeds (TAPM). Enricher converted to `enrich_artifact` output contract: emits only DEC fields (~7KB), runtime merges into base artifact. DEC-check migrated to TAPM (was 234KB cli-prompt, 300s timeout). Pending rerun validation. |

---

## Context

The proposal orchestrator currently assembles all inputs into a single text prompt piped to `claude -p` via stdin for every skill invocation. This creates a prompt-size bottleneck: for Phase 1 the prompt reaches ~400-800KB (98.5% irrelevant), and for Phase 8 it reaches 150-500KB per skill invocation with redundant re-serialization across sequential skills. The root causes are: (1) no call-level input slicing — entire grouped JSONs with 64+ topics are serialized when only 1 matters, (2) `claude -p` without `--tools` cannot read files from disk so everything must be in the prompt, (3) per-skill re-resolution of the same inputs within an agent's skill sequence.

The migration preserves the DAG scheduler, external gates, external artifact validation, and fail-closed semantics while transitioning heavy reasoning tasks from externally-assembled prompt execution to **tool-augmented prompt mode (TAPM)**. In TAPM, the external runtime passes a bounded skill prompt (~5-30KB of task metadata plus the skill spec) and enables `--tools "Read,Glob"` so Claude can read declared inputs from disk on demand rather than receiving them serialized in the prompt. The external runtime retains exclusive control of scheduling, gate evaluation, artifact validation, and state persistence.

### Revision 2.0 — What Changed and Why

**Rev 1.0** proposed a "native Claude Code backend" where Claude Code would load skill definitions from `.claude/skills/` via its own discovery mechanism, read files from disk in its repo-aware environment, and operate as a repo-native agent rather than a prompted text function.

**Operational validation** (`native_backend_validation_report.md`) proved that this premise is not yet operationally viable:

1. **Repo-local skills/agents are invisible to Claude Code.** The 21 skill files and 18 agent files use flat `.md` format with domain-specific frontmatter (`skill_id`, `reads_from`, `writes_to`). Claude Code expects `.claude/skills/<name>/SKILL.md` with standard frontmatter (`name`, `description`). `claude agents` shows zero repo-local agents. `claude -p` with `--setting-sources "user,project,local"` shows zero repo-local skills.
2. **Slash-command skill invocation is interactive-only.** `/skill-name` is unavailable in `-p` mode. The Skill tool exists but sees only built-in skills.
3. **No path-level file-access enforcement.** `--tools "Read"` grants Read access to all files. No mechanism restricts which paths Claude accesses within a tool.
4. **The `--agent` flag silently ignores unknown agents.** `claude -p --agent call_analyzer` proceeds without error and without loading the repo's agent definition.

**What operational validation confirmed works:**

1. `claude -p --tools "Read,Glob"` enables Claude to read files from disk on demand.
2. `claude -p --allowedTools "Read" --permission-mode dontAsk` restricts tool access at the tool-type level.
3. `--output-format json` returns structured metadata including cost, duration, and the result field.
4. Claude in `-p` mode with Read tool can access repo files, parse frontmatter, and return structured content.
5. `--agents` flag enables custom agent injection as JSON in one-shot mode.

**Conclusion:** The immediate migration target is TAPM — still `claude -p`, but with `--tools "Read,Glob"` enabled and prompts restructured so Claude reads inputs from disk. This achieves ~95% of the prompt-reduction benefit without dependency on unproven native skill/agent discovery.

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

**Confirmed from CLI help and operational testing**: `claude -p` supports `--tools "Read,Glob"`, `--output-format json`, `--json-schema`, `--permission-mode`, and `--allowedTools`. When `--tools "Read,Glob"` is added, Claude can read files from disk on demand during execution. This is the operational basis for TAPM.

---

## 2. Immediate Path vs. Future Path

This section replaces the original Section 2 ("Target Hybrid Architecture"). The migration now has two distinct paths with different readiness levels.

### 2.0 Immediate Path: Tool-Augmented Prompt Mode (TAPM)

**What it is**: The existing `claude -p` transport with two additions: (1) `--tools "Read,Glob"` enabled for selected skills, and (2) prompt restructured to provide task metadata and the skill spec without serializing input file contents. Claude reads declared inputs from disk on demand via the Read tool.

**What it is not**: This is not a "native Claude Code backend." It does not depend on Claude Code discovering or loading skill definitions from `.claude/skills/`. It does not use slash commands, the Skill tool, or the Agent tool. It is an enhancement to the existing CLI prompt transport that eliminates the need to serialize large input corpora into the prompt.

**Execution model**:
```
run_skill(skill_id, ...)
  if execution_mode == "tapm":
    Phase A': Build TAPM prompt:
              - Skill spec (read from .claude/skills/{skill_id}.md by Python)
              - Task metadata: node_id, run_id, declared reads_from paths, writes_to targets
              - Output schema requirements
              - Input-boundary instructions: "Read these files from disk using Read tool"
              - Total prompt: ~5-30KB (vs. 150-800KB in current mode)
    Phase B': invoke_claude_text() with tools=["Read", "Glob"]
              -> Claude reads declared inputs from disk as needed
              -> Claude produces candidate artifact content as structured JSON in stdout
    Phase C': Receive stdout response
    Phase D:  _extract_json_response()  [UNCHANGED]
    Phase E:  _atomic_write()           [UNCHANGED]
    Phase F:  return SkillResult        [UNCHANGED]
  else:
    Phase A-F: [UNCHANGED — existing cli-prompt backend]
```

**Key property**: Python still reads the skill spec file and assembles the prompt. Python still receives Claude's response as text, validates it, and writes artifacts. The only change is that input file contents are NOT serialized into the prompt — Claude reads them on demand via the Read tool.

**What this achieves**:
- Prompt reduction from 150-800KB to ~5-30KB for input-heavy skills
- Step 0 call slicing deterministically bounds input to ~10-15KB before any Claude invocation
- No dependency on Claude Code's skill/agent discovery
- No format conversion of `.claude/skills/` or `.claude/agents/` files
- All existing contracts, validation, and fail-closed behavior preserved
- Python runtime retains full control of artifact writes

### 2.1 Future Path: True Native Claude Code Backend (DEFERRED)

**Status: BLOCKED.** This path is not part of the immediate implementation sequence. It is deferred pending operational proof of the assumptions listed in Section 3.

**What it would be**: Claude Code loads skill definitions from `.claude/skills/` via native discovery, reads declared inputs from disk, and produces candidate artifacts — all without Python assembling a prompt. The external runtime would hand off ~1-5KB of task metadata, not a prompt.

**Why it is deferred**: Operational validation proved that:
- Repo-local `.claude/skills/` files are not discovered by Claude Code in their current format
- Slash-command invocation is interactive-only
- No mechanism exists for path-bounded file access enforcement
- The structured input/output contracts (`SkillResult`, schema validation, atomic writes) required by the runtime have no equivalent in Claude Code's native skill system

**Conditions for unblocking**: All items in Section 3 ("Operationally Unproven Assumptions") must be resolved. Each item specifies what proof is needed.

**If and when unblocked**: The migration would extend TAPM by replacing the Python-assembled prompt with a native execution handoff. The execution request contract (Section 2.3), artifact write discipline (Section 2.5), and all external governance (scheduler, gates, validation) would remain unchanged.

### 2.2 Architecture Diagram (TAPM)

```
UNCHANGED EXTERNAL CONTROL PLANE:
  DAGScheduler._dispatch_node()
    1. set state "running"
    2. evaluate_gate(entry_gate)     [gate_evaluator.py — unchanged]
    3. run_agent(agent_id, ...)      [agent_runtime.py — unchanged orchestration]
       -> run_skill(skill_id, ...)   [skill_runtime.py — TAPM mode added]
    4. evaluate_gate(exit_gate)      [gate_evaluator.py — unchanged]
    5. return NodeExecutionResult    [runtime_models.py — unchanged contract]

WITHIN run_skill() — TWO MODES:

  Mode A: "tapm" (for input-heavy skills)
    Phase A': Build TAPM prompt (~5-30KB):
              - Skill spec text (read from .claude/skills/{skill_id}.md by Python)
              - Task metadata: node_id, run_id
              - Declared reads_from paths (paths only, NOT contents)
              - Declared writes_to targets
              - Expected artifact schemas
              - Input-boundary instructions
    Phase B': invoke_claude_text() with tools=["Read", "Glob"]
              -> Claude reads declared inputs from disk via Read tool
              -> Claude performs domain reasoning
              -> Claude produces candidate artifact as structured JSON in stdout
    Phase C': Receive stdout response
    Phase D:  _extract_json_response()  [UNCHANGED]
    Phase E:  _atomic_write()           [UNCHANGED]
    Phase F:  return SkillResult        [UNCHANGED]

  Mode B: "cli-prompt" (existing, for light skills)
    Phase A:  _resolve_inputs()         [UNCHANGED]
    Phase B:  _assemble_skill_prompt()  [UNCHANGED]
    Phase C:  _invoke_claude()          [UNCHANGED — invoke_claude_text()]
    Phase D-F: [UNCHANGED]
```

### 2.3 Boundaries

| Responsibility | Owner | Changes? |
|---|---|---|
| DAG dispatch, ordering, stall detection | `dag_scheduler.py` | No |
| Entry/exit gate evaluation | `gate_evaluator.py` | No |
| Gate predicate logic | `gate_library.py` | No |
| HARD_BLOCK propagation (budget gate) | `dag_scheduler.py` | No |
| Node state persistence | `run_context.py` | No |
| Agent spec loading, skill sequencing, context passing | `agent_runtime.py` | No |
| `can_evaluate_exit_gate` (disk inspection) | `agent_runtime.py` | No |
| Mode selection per skill | `skill_runtime.py` | **Yes** — new branching |
| TAPM prompt assembly | `skill_runtime.py` | **Yes** — new `_assemble_tapm_prompt()` |
| Transport with tools flag | `claude_transport.py` | **Yes** — optional `tools` parameter |
| Call slicing (Step 0, deterministic pre-execution) | New `runner/call_slicer.py` | **Yes** — new module, pure Python, no Claude |
| Response parsing, schema validation, atomic write | `skill_runtime.py` | No |
| Runtime contracts (SkillResult, AgentResult, etc.) | `runtime_models.py` | No |

### 2.4 Call-Graph Preservation (CLAUDE.md Section 17.1)

The three-layer call graph is preserved without modification:
- Scheduler calls `run_agent()` — never calls skills directly
- `run_agent()` calls `run_skill()` — never calls gates
- `run_skill()` invokes Claude via `invoke_claude_text()` — same transport, new `tools` parameter
- Gate evaluator called by scheduler only — never by agents or skills

### 2.5 Context Access Invariant

**Risk**: With `--tools "Read,Glob"`, Claude can read any file in the repository. Without explicit containment, Claude could read files outside the node's declared input boundary.

**Invariant**: TAPM execution is constrained to declared `reads_from` inputs only. This is a mandatory execution invariant, not a soft guideline.

**Enforcement (TAPM)**:
1. The TAPM prompt lists only the declared `reads_from` paths. No other paths are communicated.
2. The skill spec includes explicit input-boundary instructions: *"Read only the files listed in the Declared Inputs section. Do not read files outside the declared set."*
3. `--tools "Read,Glob"` is the minimum tool set. Write, Edit, and Bash are NOT enabled.
4. Enforcement is prompt-based plus post-hoc audit. Hard path sandboxing is not available from Claude Code (see Section 3, item 5).

**Compliance testing during migration**:
- After each TAPM skill execution, audit the `--output-format stream-json` event log for Read tool invocations.
- Compare every file path read against the skill's declared `reads_from` set.
- Flag any read of an undeclared file as a containment violation.

### 2.6 Artifact Write Discipline

**Invariant**: The governed runtime — not Claude — controls all artifact writes. Claude produces candidate output as structured JSON in its stdout response. The existing write pipeline (`_extract_json_response()` → `_validate_skill_output()` → `_atomic_write()`) accepts or rejects this output.

**Write-side constraints (TAPM)**:
1. `--tools "Read,Glob"` does NOT include Write or Edit. Claude cannot write files to disk.
2. Claude returns candidate artifact content as JSON in stdout. The Python runtime parses, validates, and writes atomically.
3. Extra fields, missing required fields, or malformed schema trigger `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT")`.
4. Atomic write semantics (temp file → rename) prevent partial outputs at canonical paths.

**This is stronger than the Rev 1.0 plan**, which could not prevent Claude from writing directly to disk via the Write tool in native execution mode. TAPM does not grant write access.

---

## 3. Operationally Unproven Assumptions

These assumptions underlie the deferred "true native Claude Code backend" (Section 2.1). Each must be proven before the native backend can be unblocked. None of these assumptions affect the immediate TAPM path.

### 3.1 Repo-Local `.claude/skills/` Discovery

**What was observed**: Claude Code does not discover the 21 skill files in `.claude/skills/`. The files use flat `.md` format (`call-requirements-extraction.md`) with domain-specific YAML frontmatter (`skill_id`, `purpose_summary`, `reads_from`, `writes_to`, `constitutional_constraints`). Claude Code expects directory-based layout (`.claude/skills/<name>/SKILL.md`) with standard frontmatter (`name`, `description`). Testing with `--setting-sources "user,project,local"` showed zero repo-local skills discovered.

**Why it blocks native backend**: The native backend design assumed Claude Code would load skill definitions from `.claude/skills/` via its own discovery mechanism. Without discovery, the native execution model cannot work — Claude has no way to load the skill spec natively.

**Proof needed**: Convert one skill (e.g., `topic-scope-check`) to Claude Code's expected format (`.claude/skills/topic-scope-check/SKILL.md` with standard frontmatter). Verify it appears in `claude -p --setting-sources "user,project,local" "List skills"`. If discoverable, test whether it is invocable via the Skill tool in `-p` mode.

### 3.2 Repo-Local `.claude/agents/` Discovery

**What was observed**: `claude agents` lists only 5 built-in agents (claude-code-guide, Explore, general-purpose, Plan, statusline-setup). Zero repo-local agents from the 18 agent files in `.claude/agents/` are discovered. The files use flat `.md` format with domain-specific frontmatter (`agent_id`, `phase_id`, `node_ids`, `invoked_skills`, `entry_gate`, `exit_gate`). `claude -p --agent call_analyzer` proceeds silently without loading the agent definition.

**Why it blocks native backend**: The native backend design assumed agents defined in `.claude/agents/` would be loadable and invocable. Without discovery, the native execution model's agent layer cannot function.

**Proof needed**: Convert one agent to Claude Code's expected format (`.claude/agents/<name>/<name>.md`). Verify it appears in `claude agents`. Test invocation via `claude -p --agent <name>`.

### 3.3 Slash-Command Automation

**What was observed**: Slash commands (`/skill-name`) are available only in interactive terminal sessions. In `-p` (print/non-interactive) mode, slash commands are not available. The Skill tool exists in `-p` mode but only sees built-in skills, not repo-local ones. There is no `--skill` CLI flag to directly invoke a named skill.

**Why it blocks native backend**: The native backend assumed skill invocation would be automatable via slash commands or an equivalent mechanism. Without automation, each skill invocation would require Python to assemble a prompt anyway — collapsing back to the existing model.

**Proof needed**: Demonstrate that a repo-local skill (once discoverable per 3.1) can be invoked in `-p` mode via the Skill tool or another mechanism. The invocation must return structured output capturable by the external runtime.

### 3.4 Session Bootstrap Assumptions

**What was observed**: No explicit session bootstrap or registration step is needed for built-in skills/agents — they are available immediately. However, new top-level `.claude/skills/` directories created after session start require a restart for discovery. Agent files require session restart for changes to take effect. In one-shot `-p` mode, each invocation is a fresh session.

**Why it blocks native backend**: If per-session initialization overhead is significant, or if state must persist across skill invocations within a single agent's sequence, the one-shot invocation model may not support the native backend's assumed execution continuity.

**Proof needed**: Measure session startup overhead for a repo with populated `.claude/skills/` and `.claude/agents/` directories in Claude Code's expected format. Verify that one-shot `-p` invocations discover repo-local skills without prior interactive use.

### 3.5 Path-Bounded File-Read Enforcement

**What was observed**: `--tools "Read"` enables Read access to ALL files on disk. `--allowedTools` and `--permission-mode` operate at tool granularity, not path granularity. There is no CLI flag or configuration option to restrict which file paths the Read tool may access. The only path-level constraint mechanism available is prompt-based instruction.

**Why it blocks native backend**: The native backend design required that Claude read only declared `reads_from` paths. Without hard enforcement, the native backend's context-access invariant (Section 2.5) relies entirely on prompt-level instruction and post-hoc audit — which is acceptable for TAPM but insufficient for the higher trust level required by the native backend (where Claude would also have write access).

**Proof needed**: Demonstrate a mechanism for path-level file-access restriction. Candidates: (a) PreToolUse hooks that inspect Read arguments and deny unauthorized paths, (b) `--add-dir` flag used as an exclusive constraint (not just additive), (c) Agent SDK `tool_approval_callback` that enforces path allowlists. Any candidate must work in `-p` mode.

---

## 4. Division of Responsibilities

### 4.1 Node/Skill Decision Table

| Component | Classification | Migrate to TAPM | Rationale |
|---|---|---|---|
| **n01** `call-requirements-extraction` | tapm | **First** | Highest waste: 338-794KB prompt, 5KB relevant. Call slicing + TAPM Read eliminates 98% |
| **n01** `evaluation-matrix-builder` | tapm | ~~Later~~ **First** | ~~Reads evaluation forms (~50KB), benefits from selective reading~~ **Promoted 2026-04-16: actual user_prompt 58KB, 300s timeout with zero output. Active Phase 1 bottleneck after other n01 skills migrated.** |
| **n01** `instrument-schema-normalization` | ~~cli-prompt~~ **tapm** | ~~Never~~ **First** | ~~Small inputs (~15KB), well-bounded~~ **Reclassified 2026-04-16: actual user_prompt 78KB (run 0ace9e49), 300s timeout with zero output. Same prompt-bottleneck pattern as call-requirements-extraction.** |
| **n01** `topic-scope-check` | ~~cli-prompt~~ **tapm** | ~~Never~~ **First** | ~~Small inputs (~10KB), 2 extracted JSONs~~ **Reclassified 2026-04-16: actual user_prompt 74KB (run 0ace9e49), 300s timeout with zero output. Prompt includes full skill spec + serialized extracted JSONs.** |
| **n02** `concept-alignment-check` | tapm | Later | Reads project_brief/ + extracted (~80KB) |
| **n03** `work-package-normalization` | tapm | Later | Reads WP seed + consortium + schema (~30KB) |
| **n03** `wp-dependency-analysis` | cli-prompt | Never | Reads only Phase 3 outputs (~20KB) |
| **n04** `gantt-schedule-builder` | cli-prompt | Later | Moderate: Phase 3+4 outputs + Tier 3 (~40-50KB); TAPM not required for correctness |
| **n04** `milestone-consistency-check` | cli-prompt | Never | Small: Phase 3+4 outputs (~20KB) |
| **n05** `impact-pathway-mapper` | tapm | Later | 4 paths across tiers (~80KB) |
| **n06** `governance-model-builder` | tapm | Later | Consortium + Phase 3 outputs (~40KB) |
| **n06** `risk-register-builder` | cli-prompt | Never | risks.json + Phase 3-4 (~30KB) |
| **n07** `budget-interface-validation` | cli-prompt | Never | Structured validation, bounded inputs |
| **n08** `proposal-section-traceability-check` | tapm | **First** (with Phase 8) | 200KB+, reads all tiers |
| **n08** `evaluator-criteria-review` | tapm | **First** (with Phase 8) | 100KB+, reads draft + forms |
| **n08** `constitutional-compliance-check` | tapm | **First** (with Phase 8) | 150KB+, reads CLAUDE.md + all outputs |
| `gate-enforcement` | cli-prompt | Never | Deterministic checks, small inputs |
| `decision-log-update` | cli-prompt | Never | Writes only, minimal reads |
| `checkpoint-publish` | cli-prompt | Never | Writes checkpoint, minimal reads |
| `dissemination-exploitation-communication-check` | ~~cli-prompt~~ **tapm** | ~~Never~~ **Migrated** | ~~Phase 5 + extracted (~30KB)~~ **Reclassified 2026-04-22: actual user_prompt 234KB (run c3066a3c), 300s timeout with zero output. Original estimate (~30KB) was based on declared reads_from sizes; actual cli-prompt serializes full impact_architecture.json (~200KB) + skill spec + Tier 2A/2B extracted files. Phase 5 operational blocker.** |
| **Gate evaluation** | permanently external | Never | Constitutional: external, deterministic |
| **Schema validation** | permanently external | Never | Constitutional: external, no silent repair |
| **Atomic writes** | permanently external | Never | File I/O, no reasoning |
| **Run context / state persistence** | permanently external | Never | State management |
| **HARD_BLOCK propagation** | permanently external | Never | Scheduler-only responsibility |

### 4.2 Summary Counts

- **Migrate first (TAPM)**: 7 skills (`call-requirements-extraction`, `evaluation-matrix-builder`, `instrument-schema-normalization`, `topic-scope-check`, `proposal-section-traceability-check`, `evaluator-criteria-review`, `constitutional-compliance-check`)
- **Migrate later (TAPM)**: 5 skills (`concept-alignment-check`, `work-package-normalization`, `impact-pathway-mapper`, `governance-model-builder`, `gantt-schedule-builder`)
- **Never migrate**: 8 skills (small/bounded inputs, deterministic checks, validation-only)
- **Permanently external**: 6 functions (gates, validation, writes, state, HARD_BLOCK)

> **Reclassification note (2026-04-16):** `instrument-schema-normalization` and `topic-scope-check` moved from "Never migrate" to "Migrate first" based on runtime telemetry from run `0ace9e49`. Original estimates (~15KB, ~10KB) were based on declared `reads_from` sizes; actual cli-prompt user prompts measured at 78KB and 74KB respectively, causing 300s timeouts with zero partial output. Classification decisions must be validated against runtime prompt-size telemetry, not static input estimates.

### 4.3 First Migration Target: `call-requirements-extraction`

The first skill to migrate to TAPM is **`call-requirements-extraction`** (node n01).

**Why this skill**:
1. **Highest waste ratio** (98.5%): Prompts are 338-794KB, of which ~5KB is relevant. No other skill has this disproportion.
2. **Single phase, single node**: Executes only in Phase 1 (n01), with no cross-phase input dependencies at runtime. Failure is isolated to one node.
3. **Well-defined outputs**: Produces exactly 6 Tier 2B extracted JSON files with known schemas. Output correctness is mechanically verifiable via `_validate_skill_output()`.
4. **Baseline comparison available**: The existing cli-prompt mode produces reference outputs. Post-migration outputs can be diffed against this baseline.
5. **One-line rollback**: Reverting `execution_mode` in `skill_catalog.yaml` restores cli-prompt behavior immediately.
6. **Call slicing synergy**: Step 0 (call slicer) directly targets this skill's input waste.

---

## 5. Grouped JSON Input Strategy

### 5.1 Current Waste

`selected_call.json` identifies `topic_code: "HORIZON-CL4-2026-05-DIGITAL-EMERGING-02"`. The `call_analyzer` agent's `reads_from` includes `docs/tier2b_topic_and_call_sources/work_programmes/`. The `_resolve_directory_recursive()` function reads **every file** under that directory tree, including `cluster_CL4.grouped.json` (338KB, 64 topics). Only 5,181 bytes (1.5%) is the target call.

### 5.2 Call Slice Strategy (Implemented by Step 0)

The call slice strategy is fully defined in **Step 0 — Call Slicer (Deterministic Input Bounding Layer)** in Section 6. Step 0 is the authoritative specification for input bounding. This section summarizes the strategy for context.

**Pre-execution step** (new `runner/call_slicer.py`, invoked by scheduler before first dispatch):

1. Read `docs/tier3_project_instantiation/call_binding/selected_call.json` to get `topic_code` and `work_programme`
2. Map `work_programme` to the grouped JSON via deterministic lookup table
3. Linear scan: extract the single matching call entry by `call_id` / `original_call_id`
4. Write focused slice to `docs/tier2b_topic_and_call_sources/call_extracts/<topic_code>.slice.json`
5. Fail-closed on missing inputs, missing match, or output > 20KB

**Slice content** (~4-10KB): Single call entry with full scope, expected_outcome, eligibility_conditions, deadlines, budget figures, and all other fields from the grouped JSON call entry. Wrapped with source references and provenance metadata.

**Complement**: The existing curated call extract at `docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.json` (~4KB) provides structured interpretation (outcomes array, research areas, FSTP details). Together the slice (~5-8KB) and extract (~4KB) provide ~10-15KB of bounded, call-specific input.

### 5.3 What Remains for Traceability vs. Runtime

| Artifact | Purpose | Used at runtime? |
|---|---|---|
| `cluster_CL4.grouped.json` (338KB) | Traceability — full work programme source | **No** — not read by skills (source for Step 0 slicer only) |
| `<topic_code>.slice.json` (5-8KB) | Runtime — bounded call data (Step 0 output) | **Yes** — read by Claude via Read tool |
| `<topic_code>.json` call extract (4KB) | Runtime — structured call interpretation | **Yes** — read by Claude via Read tool |
| `selected_call.json` (1KB) | Runtime — call binding metadata | **Yes** — read by Claude via Read tool |

### 5.4 How TAPM Skills Use Call Data (After Step 0)

With Step 0 in place, TAPM skills operate over **pre-sliced, bounded inputs only**. The TAPM prompt declares:
```
## Declared Inputs (read these from disk using the Read tool)
  docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.slice.json
  docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.json
  docs/tier3_project_instantiation/call_binding/selected_call.json
```

Claude reads these 3 files on demand (~10-15KB total) vs. 338-794KB previously. Claude does NOT read grouped JSON files — Step 0 has already extracted the relevant entry. TAPM's `Read` tool calls are bounded to small, pre-sliced files.

---

## 6. Step-by-Step Migration Plan (TAPM)

### Step 0 — Call Slicer (Deterministic Input Bounding Layer)

**Goal**: Eliminate input breadth at the source — before any Claude invocation, before TAPM prompt assembly, and before any skill or agent executes. Step 0 deterministically pre-selects the exact call-specific input slice so that all downstream steps operate over bounded, call-specific data only.

**Classification**: Pure Python runtime preprocessing. Step 0 is NOT a skill, NOT an agent, NOT a TAPM operation. It does not invoke Claude. It does not depend on TAPM infrastructure. It runs entirely in Python as a deterministic function.

#### 0.1 Why Step 0 Exists

The current plan reduces prompt size via TAPM (Claude reads files from disk instead of receiving them serialized). But TAPM alone still leaves Claude to discover and navigate large input corpora via `Read` — e.g., `cluster_CL4.grouped.json` (338KB, 64 topics) when only 1 topic (~5KB) matters. Even with TAPM, Claude would read 338KB through the Read tool, parse it, and find the 5KB entry. This is unnecessary work, unnecessary token consumption, and a source of non-determinism (Claude's file-reading strategy is not guaranteed).

Step 0 eliminates this by performing the lookup in Python before any Claude invocation. The downstream skill receives a single, bounded, call-specific JSON object — not a grouped corpus to search through.

**Input breadth reduction chain**:
```
Without Step 0 + Without TAPM:  338-794KB serialized in prompt (current state)
Without Step 0 + With TAPM:     338-794KB read via Read tool (Claude navigates)
With Step 0    + With TAPM:     5-8KB read via Read tool (pre-sliced, bounded)
With Step 0    + Without TAPM:  5-8KB serialized in prompt (also works)
```

Step 0 is orthogonal to TAPM. It reduces input breadth; TAPM reduces prompt serialization. Both are needed. Either works independently.

#### 0.2 Inputs

Step 0 reads exactly two categories of file:

1. **`docs/tier3_project_instantiation/call_binding/selected_call.json`** — contains `topic_code` (e.g., `"HORIZON-CL4-2026-05-DIGITAL-EMERGING-02"`) and `work_programme` (e.g., `"cluster_digital"`), which together identify the target call and the grouped JSON that contains it.

2. **The grouped JSON file** determined by `work_programme` — e.g., `docs/tier2b_topic_and_call_sources/work_programmes/cluster_digital/cluster_CL4.grouped.json`. The mapping from `work_programme` value to grouped JSON path is a deterministic lookup table in `call_slicer.py`:
   ```
   cluster_digital  → work_programmes/cluster_digital/cluster_CL4.grouped.json
   cluster_health   → work_programmes/cluster_health/cluster_CL1.grouped.json
   cluster_culture  → work_programmes/cluster_culture/cluster_CL2.grouped.json
   cluster_security → work_programmes/cluster_security/cluster_CL3.grouped.json
   cluster_food     → work_programmes/cluster_food/cluster_CL5.grouped.json
   cluster_climate  → work_programmes/cluster_climate/cluster_CL6.grouped.json
   ```

#### 0.3 Algorithm

The slicer is a pure function with no branching ambiguity:

```python
def generate_call_slice(repo_root: Path) -> Path:
    # 1. Read selected_call.json
    selected = json.loads((repo_root / SELECTED_CALL_PATH).read_text())
    topic_code = selected["topic_code"]
    work_programme = selected["work_programme"]

    # 2. Resolve grouped JSON path from lookup table
    grouped_path = repo_root / GROUPED_JSON_MAP[work_programme]

    # 3. Parse grouped JSON
    grouped = json.loads(grouped_path.read_text())

    # 4. Linear scan: find the single matching call entry
    match = None
    for destination in grouped["destinations"]:
        for call in destination["calls"]:
            if call["call_id"] == topic_code or call.get("original_call_id") == topic_code:
                match = call
                break
        if match:
            break

    # 5. Fail-closed if no match
    if match is None:
        raise CallSlicerError(
            f"topic_code '{topic_code}' not found in {grouped_path}"
        )

    # 6. Assemble the bounded call slice object
    call_slice = {
        "topic_code": topic_code,
        "source_grouped_json": str(grouped_path.relative_to(repo_root)),
        "source_destination": destination["destination_title"],
        "call_entry": match,
        "sliced_by": "runner/call_slicer.py",
        "slice_timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # 7. Write to canonical output path
    output_path = repo_root / CALL_SLICE_OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(call_slice, indent=2, ensure_ascii=False))

    return output_path
```

**Key properties**:
- Deterministic: same inputs → same output (modulo timestamp)
- Fail-closed: missing `selected_call.json`, missing grouped JSON, or no matching `topic_code` raises an exception — never produces a partial or empty slice
- Single-match: extracts exactly one call entry. If multiple matches exist, takes the first (grouped JSONs have unique `call_id` values by construction)

#### 0.4 Output

**Canonical output path**: `docs/tier2b_topic_and_call_sources/call_extracts/<topic_code>.slice.json`

Example: `docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.slice.json`

**Output structure**:
```json
{
  "topic_code": "HORIZON-CL4-2026-05-DIGITAL-EMERGING-02",
  "source_grouped_json": "docs/tier2b_topic_and_call_sources/work_programmes/cluster_digital/cluster_CL4.grouped.json",
  "source_destination": "Achieving open strategic autonomy in digital and emerging enabling technologies (2026-27)",
  "call_entry": {
    "call_id": "HORIZON-CL4-2026-05-DIGITAL-EMERGING-02",
    "call_title": "...",
    "scope": "...",
    "expected_outcome": "...",
    "eligibility_conditions": "...",
    "technology_readiness_level": "...",
    "indicative_budget": 38000000,
    "max_contribution": 19000000,
    "deadline": "2026-04-15",
    "...": "all fields from the grouped JSON call entry"
  },
  "sliced_by": "runner/call_slicer.py",
  "slice_timestamp": "2026-04-15T10:30:00Z"
}
```

**Output contains**:
- Full scope text from the grouped JSON call entry
- Expected outcomes (from `expected_outcome` field)
- Eligibility conditions, technology readiness level, procedure text
- Budget figures (indicative budget, max contribution)
- Deadlines, opening dates, funding links
- Source references (grouped JSON path, destination title)

**Output does NOT contain**:
- Any other call entries from the grouped JSON
- Destination-level metadata for other destinations
- Data from other cluster grouped JSONs

**Size bound**: The output must be < 20KB. A single call entry from the grouped JSON is typically 3-8KB. With the wrapper metadata, the slice is 4-10KB. If the output exceeds 20KB, this indicates a data anomaly and the slicer must raise an error.

#### 0.5 Relationship to Existing Call Extract

The repository already contains a manually curated call extract at:
`docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.json`

This file (~4KB) contains curated fields: structured `expected_outcomes` (array), `scope_summary`, `scope_research_areas`, structured `eligibility_restrictions`, `fstp_provisions`, `mandatory_cohesion_activities`, and `platform_requirements`.

The Step 0 slice and the existing call extract are **complementary, not redundant**:

| Artifact | Source | Content | Role |
|---|---|---|---|
| `*.slice.json` (Step 0 output) | Grouped JSON (machine-extracted) | Raw call entry with full scope text, expected_outcome string, all fields | Primary call data — complete, unedited |
| `*.json` (existing call extract) | Manual curation from PDF | Structured outcomes array, research areas, FSTP details, platform requirements | Supplementary — structured interpretation |

Both files are small (< 10KB each). Together they provide ~10-15KB of bounded, call-specific input. The `call-requirements-extraction` skill reads both.

#### 0.6 Execution Position

Step 0 runs **before all other steps** in the migration plan. It is also **before all DAG node dispatches** at runtime:

```
Runtime execution order:
  1. generate_call_slice()          ← Step 0 (Python, no Claude)
  2. DAGScheduler.run()             ← existing dispatch loop
     2a. _dispatch_node(n01)        ← entry gate → agent body → exit gate
         → run_agent() → run_skill("call-requirements-extraction")
           → TAPM prompt references *.slice.json + *.json (Step 0 output)
     2b. _dispatch_node(n02) ...
```

**Integration point**: `runner/dag_scheduler.py` — add `generate_call_slice()` call before the dispatch loop (~5 lines). The slicer is invoked once per run, not per node.

#### 0.7 What Changes Downstream

**`call-requirements-extraction` no longer reads**:
- `docs/tier2b_topic_and_call_sources/work_programmes/` (entire directory tree)
- Full grouped JSON files (`cluster_CL4.grouped.json`, etc.)

**`call-requirements-extraction` now reads ONLY**:
- `docs/tier2b_topic_and_call_sources/call_extracts/<topic_code>.slice.json` (Step 0 output, 4-10KB)
- `docs/tier2b_topic_and_call_sources/call_extracts/<topic_code>.json` (existing call extract, ~4KB)
- `docs/tier3_project_instantiation/call_binding/selected_call.json` (call binding metadata, ~1KB)

**Total input to `call-requirements-extraction`**: ~10-15KB (vs. 338-794KB previously).

This means that when TAPM is applied in Step 4, Claude's `Read` tool calls access only these small, pre-sliced files. There is no large corpus to navigate. The combination of Step 0 (input bounding) + TAPM (read delegation) reduces the effective input from 338-794KB serialized to 10-15KB read on demand.

#### 0.8 TAPM Interaction After Step 0

With Step 0 in place, TAPM operates over **bounded inputs only**. The TAPM prompt for `call-requirements-extraction` becomes:

```
## Declared Inputs (read these from disk using the Read tool)
  docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.slice.json
  docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.json
  docs/tier3_project_instantiation/call_binding/selected_call.json
```

Claude uses `Read` only for:
- The sliced call JSON (Step 0 output) — bounded, single-call
- The curated call extract — bounded, single-call
- Small auxiliary files (`selected_call.json`) — ~1KB

Claude does NOT use `Read` for:
- Grouped JSON files (eliminated by Step 0)
- Work programme directories (eliminated by Step 0)
- Any file > 20KB (no such file exists in the declared input set)

#### 0.9 Implementation

**New file**: `runner/call_slicer.py` (~100-120 lines)

Contents:
- `SELECTED_CALL_PATH` constant
- `GROUPED_JSON_MAP` lookup table (6 entries)
- `CALL_SLICE_OUTPUT_PATH` template
- `CallSlicerError` exception class
- `generate_call_slice(repo_root: Path) -> Path` function
- Size validation (output < 20KB)
- Logging of slice size and source

**Modified file**: `runner/dag_scheduler.py` — add ~5 lines before dispatch loop:
```python
from runner.call_slicer import generate_call_slice

# In run() method, before dispatch loop:
call_slice_path = generate_call_slice(self.repo_root)
logger.info(f"Call slice generated: {call_slice_path}")
```

**What remains unchanged**: All existing skill_runtime, agent_runtime, gate_evaluator, transport, runtime_models, manifest_reader, node_resolver code. Step 0 touches only `call_slicer.py` (new) and `dag_scheduler.py` (5-line addition).

#### 0.10 Testability

**Unit test**: `tests/runner/test_call_slicer.py`

Required test cases:

| # | Test | Assertion |
|---|---|---|
| 1 | Happy path: valid `selected_call.json` + matching grouped JSON | Exactly one call extracted; output valid JSON; `topic_code` matches |
| 2 | Output size bound | Output file size < 20KB |
| 3 | No other calls included | `call_entry.call_id` == target `topic_code`; no other `call_id` values in output |
| 4 | Missing `selected_call.json` | Raises `CallSlicerError` |
| 5 | Missing grouped JSON | Raises `CallSlicerError` |
| 6 | `topic_code` not found in grouped JSON | Raises `CallSlicerError` |
| 7 | Unknown `work_programme` value | Raises `CallSlicerError` (not in lookup table) |
| 8 | Idempotency | Running twice with same inputs produces identical output (modulo timestamp) |
| 9 | Grouped JSON unmodified | Grouped JSON file is byte-identical before and after slicing |
| 10 | Output path correctness | Output written to `call_extracts/<topic_code>.slice.json` |

**Verification command**:
```bash
# Unit tests
python -m pytest tests/runner/test_call_slicer.py -v

# Manual verification
python -c "
from pathlib import Path
from runner.call_slicer import generate_call_slice
path = generate_call_slice(Path('.'))
import json, os
data = json.loads(path.read_text())
size = os.path.getsize(path)
print(f'Output: {path}')
print(f'Size: {size} bytes')
print(f'Topic: {data[\"topic_code\"]}')
print(f'Call ID in entry: {data[\"call_entry\"][\"call_id\"]}')
assert size < 20480, f'Output too large: {size} bytes'
assert data['topic_code'] == data['call_entry']['call_id'] or data['topic_code'] == data['call_entry'].get('original_call_id')
print('PASS')
"
```

**Success signals**: `*.slice.json` exists, is < 20KB, contains exactly one call entry matching `topic_code`, valid JSON. Grouped JSON files are unmodified.

**Failure signals**: Missing `selected_call.json`, no matching `topic_code` in grouped JSON, output > 20KB (slicing failed or wrong entry extracted), multiple call entries in output.

#### 0.11 Governance Preservation

Step 0 does NOT:
- Modify the DAG scheduler's dispatch logic, gate evaluation, or state management
- Modify gate conditions or gate predicates
- Modify artifact schemas or introduce new artifact types consumed by gates
- Modify the agent runtime or skill runtime
- Invoke Claude or any LLM
- Move any reasoning logic into Python (the slicer is a lookup + extract, not interpretation)
- Alter the constitutional authority hierarchy or tier semantics

Step 0 IS:
- A deterministic preprocessing optimization that narrows input breadth
- Aligned with the existing call-extract pattern (writes to `call_extracts/`)
- A runtime-layer enhancement consistent with CLAUDE.md Section 17 (runtime execution architecture)
- Independently testable and independently rollbackable

**Rollback**: Delete `call_slicer.py`, remove the 5-line scheduler call, revert `reads_from` in skill catalog. No downstream dependencies break — skills fall back to reading grouped JSONs (larger but functionally equivalent).

---

### Step 1: Transport Enhancement — Add `tools` Parameter to `invoke_claude_text()`

**Goal**: Enable the existing transport to pass `--tools` flag to the `claude` CLI, so Claude can use Read and Glob tools during execution.

**What changes**:
- Modified: `runner/claude_transport.py` — add optional `tools: list[str] | None` parameter to `invoke_claude_text()`. When provided, append `--tools <comma-joined>` to the command list. (~10 lines added)

**What remains unchanged**: All existing callers pass `tools=None` (default). Existing behavior is bit-identical. The function signature gains one optional parameter. No behavioral change for any existing code path.

**How to test immediately**:
```bash
# Unit test (mocked subprocess)
python -m pytest tests/runner/test_claude_transport.py -v

# Verify existing behavior unchanged:
# All existing tests pass without modification

# Manual smoke test (real invocation):
python -c "
from runner.claude_transport import invoke_claude_text
result = invoke_claude_text(
    system_prompt='You are a test assistant.',
    user_prompt='Read the file docs/tier3_project_instantiation/call_binding/selected_call.json and return the topic_code value. Reply with ONLY the topic_code string.',
    model='haiku',
    max_tokens=200,
    tools=['Read', 'Glob']
)
print(result)
"
```

**Success signals**: Smoke test returns the correct `topic_code` value. Existing tests pass unchanged. The `--tools` flag appears in the subprocess command when `tools` is not None.

**Failure signals**: `claude` CLI rejects the `--tools` flag (would indicate CLI version incompatibility). Existing tests break (would indicate parameter addition broke the function signature).

**Rollback**: Revert the one-file change. No callers use the new parameter yet.

---

### Step 2: TAPM Prompt Assembly — `_assemble_tapm_prompt()`

**Goal**: Create the prompt assembly function for TAPM mode that provides task metadata and the skill spec WITHOUT serializing input file contents.

**What changes**:
- Modified: `runner/skill_runtime.py` — add `_assemble_tapm_prompt()` function (~80 lines). This function:
  1. Reads the skill spec text from `.claude/skills/{skill_id}.md` (Python reads it, same as existing)
  2. Builds a system prompt containing: skill spec, node_id, run_id, output schema requirements
  3. Builds a user prompt containing: declared `reads_from` paths (paths only, NOT contents), `writes_to` targets, input-boundary instructions, output format instructions
  4. Total prompt: ~5-30KB depending on skill spec size

**What remains unchanged**: `_resolve_inputs()`, `_assemble_skill_prompt()`, and all existing cli-prompt logic. The new function is additive — it is not called by any existing code path yet.

**How to test immediately**:
```bash
# Unit test
python -m pytest tests/runner/test_skill_runtime_tapm.py -v

# Verify prompt size:
# - call-requirements-extraction TAPM prompt should be <30KB
# - Compare to existing cli-prompt: >400KB
# Verify prompt contains: skill spec text, reads_from path list, writes_to targets
# Verify prompt does NOT contain: file contents from reads_from paths
```

**Success signals**: TAPM prompt for `call-requirements-extraction` is <30KB. Contains input-boundary instructions. Does NOT contain contents of `cluster_CL4.grouped.json` or any other input file.

**Failure signals**: Prompt exceeds 50KB (skill spec too large — may need trimming). Prompt accidentally includes file contents (assembly logic error).

**Rollback**: Remove the new function. No callers yet.

---

### Step 3: Mode Selection in `run_skill()`

**Goal**: Add mode selection that dispatches to TAPM or cli-prompt based on skill catalog configuration.

**What changes**:
- Modified: `runner/skill_runtime.py` — modify `run_skill()` to read `execution_mode` from skill catalog entry and branch (~30 lines added):
  ```python
  mode = entry.get("execution_mode", "cli-prompt")
  if mode == "tapm":
      system_prompt, user_prompt = _assemble_tapm_prompt(skill_id, skill_spec, node_context)
      raw = invoke_claude_text(
          system_prompt=system_prompt,
          user_prompt=user_prompt,
          model=model,
          max_tokens=max_tokens,
          tools=["Read", "Glob"]
      )
  else:
      # Existing Phases A-C (unchanged)
  ```
- Modified: `.claude/workflows/system_orchestration/skill_catalog.yaml` — add optional `execution_mode` field definition (no skill changed yet)

**What remains unchanged**: `run_skill()` function signature and return type. `SkillResult` contract. Phases D-F (parsing, validation, atomic write) — shared by both modes. All existing skills default to `"cli-prompt"`.

**How to test immediately**:
```bash
python -m pytest tests/runner/test_skill_runtime.py -v  # ALL existing tests pass
python -m pytest tests/runner/test_skill_runtime_tapm.py -v  # new TAPM mode tests

# Verify: existing skills with no execution_mode field use cli-prompt
# Verify: TAPM mode calls _assemble_tapm_prompt() and passes tools=["Read", "Glob"]
# Verify: TAPM mode does NOT call _resolve_inputs() or _assemble_skill_prompt()
# Verify: Phases D-F work identically for both modes
```

**Success signals**: All 988+ existing tests pass. TAPM path produces valid SkillResult in test.

**Failure signals**: Existing tests break (mode selection altered default path). TAPM path called `_resolve_inputs()` (should not).

**Rollback**: Revert `run_skill()` changes. No skills use TAPM yet, so zero behavioral impact.

---

### Step 4: Migrate First Skill — `call-requirements-extraction` (PILOT)

**Goal**: Opt-in the highest-impact skill to TAPM. Validate end-to-end on node `n01_call_analysis`.

**What changes**:
- Modified: `skill_catalog.yaml` — add `execution_mode: "tapm"` to `call-requirements-extraction`
- Modified: `.claude/skills/call-requirements-extraction.md` — add input-boundary instructions:
  ```
  ## Input Access (TAPM Mode)
  Read the files listed in the Declared Inputs section from disk using the Read tool.
  For call data, read the Step 0 call slice (*.slice.json) and the curated call extract file.
  Do not read grouped JSON files (cluster_CL*.grouped.json) or work programme directories.
  Do not read files outside the declared input set.
  Return your output as a single JSON object in your response.
  ```
- Modified: `reads_from` for `call-requirements-extraction` updated to reference Step 0 output:
  - **Removed**: `docs/tier2b_topic_and_call_sources/work_programmes/` (entire directory tree)
  - **Added**: `docs/tier2b_topic_and_call_sources/call_extracts/<topic_code>.slice.json` (Step 0 output)
  - **Retained**: `docs/tier2b_topic_and_call_sources/call_extracts/<topic_code>.json` (existing call extract)
  - **Retained**: `docs/tier3_project_instantiation/call_binding/selected_call.json`
- Execution flow: Step 0 generates `*.slice.json` → `run_skill()` selects TAPM mode → `_assemble_tapm_prompt()` builds ~10KB prompt referencing Step 0 output → `invoke_claude_text(tools=["Read", "Glob"])` → Claude reads ~10-15KB of pre-sliced call data from disk → returns 6 extracted JSON files as candidate artifact → external validation and atomic write

**What remains unchanged**: `reads_from`, `writes_to`, constraints, output schema, agent runtime, scheduler, gates. The skill spec body (domain reasoning instructions) is unchanged.

**How to test immediately**:
```bash
# Full Phase 1 execution
python -m runner --run-id test-tapm-001 --phase 1 --verbose

# Verify outputs:
cat docs/tier2b_topic_and_call_sources/extracted/call_constraints.json | python -m json.tool | head -5
cat docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json | python -m json.tool | head -5
# ... repeat for all 6 extracted files

# Verify: all 6 files non-empty and valid JSON
# Verify: all entries reference topic_code HORIZON-CL4-2026-05-DIGITAL-EMERGING-02
# Verify: no data from other topics leaked
# Verify: exit gate passes

# Quality comparison:
# 1. Save TAPM outputs
# 2. Temporarily set execution_mode: "cli-prompt", re-run with same inputs
# 3. Diff outputs — structural equivalence expected (exact text may differ)
```

**Success signals**: All 6 Tier 2B extracted files populated. Exit gate passes. Schema validation passes. Prompt size in logs is <30KB (vs. 400-800KB baseline).

**Failure signals**: Empty or malformed output (Claude failed to read inputs via Read tool). Gate failure (output doesn't meet gate predicates). Claude read undeclared files (containment violation — check stream-json log).

**Rollback**: Change `execution_mode` back to `"cli-prompt"` in `skill_catalog.yaml`. One line change, immediate revert.

---

### Step 5: Migrate Phase 2-6 Skills to TAPM

**Goal**: Migrate medium-input skills progressively to TAPM.

**What changes**:
- Modified: `skill_catalog.yaml` — set `execution_mode: "tapm"` for: `concept-alignment-check`, `work-package-normalization`, `evaluation-matrix-builder`, `impact-pathway-mapper`, `governance-model-builder`
- Modified: corresponding `.claude/skills/*.md` files — add input-boundary instructions

**What remains unchanged**: Scheduler, gates, agent runtime, output contracts, cli-prompt skills.

**How to test immediately**:
```bash
# Run Phases 2-6 sequentially
python -m runner --run-id test-tapm-002 --phase 2 --verbose
python -m runner --run-id test-tapm-003 --phase 3 --verbose
python -m runner --run-id test-tapm-004 --phase 4 --verbose
python -m runner --run-id test-tapm-005 --phase 5 --verbose
python -m runner --run-id test-tapm-006 --phase 6 --verbose

# Verify each phase's exit gate passes
# Verify phase outputs in docs/tier4_orchestration_state/phase_outputs/phase{N}_*/
```

**Success signals**: All phases complete. Mixed-mode execution works end-to-end (some skills TAPM, some cli-prompt within the same agent's sequence).

**Failure signals**: Agent runtime fails to handle mixed modes (TAPM and cli-prompt skills in the same agent sequence). Gate failures due to output quality differences.

**Rollback**: Revert `execution_mode` fields individually in `skill_catalog.yaml`. Each skill is independently rollbackable.

---

### Step 6: Migrate Phase 8 Skills to TAPM (Highest Value)

**Goal**: Migrate the three heaviest cross-cutting skills to TAPM.

**What changes**:
- Modified: `skill_catalog.yaml` — set `execution_mode: "tapm"` for: `proposal-section-traceability-check`, `evaluator-criteria-review`, `constitutional-compliance-check`
- Modified: corresponding `.claude/skills/*.md` files — add input-boundary instructions with per-invocation scoping

**What remains unchanged**: Scheduler, gates, agent runtime, output contracts.

**How to test immediately**:
```bash
# Full Phase 8 execution (requires all prior phases passed)
python -m runner --run-id test-tapm-008 --phase 8 --verbose

# Verify:
ls docs/tier5_deliverables/proposal_sections/
ls docs/tier5_deliverables/assembled_drafts/
ls docs/tier5_deliverables/review_packets/

# Verify exit gates pass
# Verify no fabricated content
# Verify no budget-dependent content without gate pass
```

**Success signals**: Phase 8 completes. Per-skill prompt size dramatically reduced (150-500KB → 10-30KB).

**Failure signals**: Claude reads too many files via Read tool (latency regression). Output quality degradation from not having full context pre-assembled.

**Rollback**: Revert 3 `execution_mode` fields in `skill_catalog.yaml`.

---

### Step 7: Documentation and Cleanup

**Goal**: Update CLAUDE.md Section 17 to reflect TAPM architecture.

**What changes**:
- Modified: `CLAUDE.md` — update Section 17.5 ("Claude Runtime Transport Principle") to describe TAPM mode:
  - Section 17.5.2 updated: skill runtime selects between cli-prompt mode (external prompt assembly) and TAPM mode (tool-augmented prompt with `--tools "Read,Glob"`) based on skill catalog configuration
  - Section 17.1.3 updated: skill runtime dispatches to the selected mode; mode selection does not alter the call-graph
- Modified: `CLAUDE.md` — add Constitutional Amendment Record documenting TAPM as an additional execution mode within the existing transport

**What remains unchanged**: All other CLAUDE.md sections. All governance semantics. The amendment explicitly states that TAPM is a transport-layer optimization, not a change to workflow logic, gate logic, DAG structure, or failure semantics.

**Rollback**: Revert CLAUDE.md changes.

---

## 7. Per-Step Test Plan

| Step | Test Type | Command | Success Signal |
|---|---|---|---|
| 0 | Unit | `pytest tests/runner/test_call_slicer.py` | All 10 test cases pass (happy path, size bound, no leakage, fail-closed errors, idempotency, path correctness) |
| 0 | Manual | Read `<topic_code>.slice.json` | Contains exactly one call entry matching `topic_code`; output < 20KB; valid JSON; grouped JSON unmodified |
| 1 | Unit | `pytest tests/runner/test_claude_transport.py` | All existing tests pass; new tools-parameter tests pass |
| 1 | Smoke | Real `invoke_claude_text(tools=["Read"])` call | Claude reads a file and returns content |
| 2 | Unit | `pytest tests/runner/test_skill_runtime_tapm.py` | TAPM prompt is <30KB; no file contents in prompt |
| 3 | Unit | `pytest tests/runner/test_skill_runtime.py` | ALL existing tests pass (regression) |
| 3 | Unit | `pytest tests/runner/test_skill_runtime_tapm.py` | TAPM mode produces valid SkillResult |
| 4 | E2E | `python -m runner --phase 1` | Phase 1 exit gate passes; 6 extracted files populated |
| 5 | E2E | `python -m runner --phase 2` through `--phase 6` | Each exit gate passes |
| 6 | E2E | `python -m runner --phase 8` | Tier 5 deliverables present; review packet valid |
| All | Regression | `pytest tests/ -v` | Full test suite passes after every step |

---

## 8. Risks and Mitigations

### Risk 1: Claude Fails to Read Files Via Read Tool in `-p` Mode

**Severity**: High (blocks TAPM)
**Description**: Claude in `-p` mode with `--tools "Read"` might not reliably use the Read tool to access declared inputs, or might produce inconsistent results compared to receiving inputs in the prompt.
**Mitigation**: Step 1 smoke test validates that `invoke_claude_text(tools=["Read"])` works. Step 4 (pilot migration) validates end-to-end with real skill execution. The pilot is specifically chosen to be independently rollbackable.
**Evidence from validation**: `claude -p` with `--allowedTools "Read"` successfully read a repo file and returned structured content. Tool-augmented `-p` mode works.

### Risk 2: Prompt-Based Input Boundary Is Not Respected

**Severity**: Medium
**Description**: Claude might read undeclared files outside the `reads_from` set, violating the context-access invariant. In TAPM mode, the Read tool enables access to all files; only prompt instructions constrain behavior.
**Mitigation**: Input-boundary instructions in the skill spec. Post-hoc audit of Read tool invocations via `--output-format stream-json`. Containment violations are flagged but do not invalidate the output (the output still passes through external schema validation). Hard enforcement is an unsolved problem — see Section 3.5.

### Risk 3: Latency from Multiple Read Tool Calls

**Severity**: Low-Medium
**Description**: Multiple Read tool calls add per-call overhead vs. a single prompt.
**Mitigation**: Call slicing reduces reads to ~3-5 small files. Each Read call adds ~1-2s. Net trade: massive tokenization overhead (100K+ tokens) traded for 5-10 Read calls. Expected: similar or faster for large-input skills.

### Risk 4: Output Quality Differences Between Modes

**Severity**: Medium
**Description**: Claude reading files on demand might process them differently than when files are pre-serialized in the prompt (different token ordering, attention patterns, selective reading).
**Mitigation**: Step 4 includes quality comparison: run the same skill in both modes on identical inputs, diff outputs. External schema validation catches structural issues. Gate evaluation catches semantic issues.

### Risk 5: Constitutional Compliance

**Severity**: High (governance)
**Description**: CLAUDE.md Section 17 describes current transport. Adding TAPM mode without amendment is a violation.
**Mitigation**: Step 7 amends Section 17 per Section 14 rules. TAPM is explicitly a transport-layer enhancement, not a change to governance semantics.

### Risk 6: Regression in Existing cli-prompt Skills

**Severity**: Low
**Description**: Changes to `run_skill()` could break the existing cli-prompt path.
**Mitigation**: Mode selection is strictly additive — cli-prompt is the default when `execution_mode` is absent. All 988+ existing tests must pass after every step.

---

## 9. Recommended Rollout Order

### Phase A: Foundation (Steps 0-1) — Zero-Risk, Additive
Step 0 (call slicer) and Step 1 (transport enhancement) are independent additive changes with no existing behavior changes. Step 0 is a pure Python preprocessing layer that deterministically bounds input breadth before any Claude invocation. Step 1 enables tool-augmented transport. Both can be implemented in parallel. Step 0 must complete before Step 4 (pilot migration), since Step 4's `reads_from` references Step 0's output.

### Phase B: TAPM Integration (Steps 2-3) — Low Risk
TAPM prompt assembly and mode selection added to `run_skill()`. All skills default to cli-prompt. No behavioral change.

### Phase C: First Validation (Step 4) — MINIMUM VIABLE MIGRATION
One skill (`call-requirements-extraction`) migrates to TAPM. Validates the entire pipeline end-to-end. **If Step 4 succeeds, TAPM is validated. If it fails, rollback is a single YAML line.**

### Phase D: Progressive Rollout (Steps 5-6) — Incremental
Each skill migration is a single YAML field change. Independent rollback per skill.

### Phase E: Documentation (Step 7) — Governance
Constitutional amendment to reflect the validated architecture.

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

Note: `dag_scheduler.py` gains a call to `generate_call_slice()` before the dispatch loop (Step 0). This is a deterministic, pure-Python pre-execution step that runs before any Claude invocation. It does not modify dispatch logic, gate evaluation, state management, or the DAG structure. The dispatch loop itself (`run()`, `_dispatch_node()`) is unchanged. Step 0 is not a skill, not an agent, and not TAPM-dependent.

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
- No fabrication: constitutional constraints in skill spec unchanged
- Artifact schema validation: `run_id`, `schema_id`, required field checks unchanged
- Atomic writes: temp file + rename unchanged
- Durable state in Tier 4: canonical path writes unchanged
- Gate independence from agents: `evaluate_gate()` called only by scheduler
- **NEW**: Write-tool exclusion — TAPM mode grants Read and Glob only; Claude cannot write to disk

### Existing Test Suite — Must Pass After Every Step

- `test_dag_scheduler.py` (94KB, ~200+ tests)
- `test_gate_evaluator.py` (48KB)
- `test_gate_scenarios.py` (51KB)
- `test_runtime_models.py` (10KB)
- `test_skill_runtime.py` (43KB)
- `test_agent_runtime.py` (35KB)

---

## 11. Gate-Enforcement Containment

Gate-enforcement skills must not become the new prompt-bloat sink after input-heavy skills migrate to TAPM.

### 11.1 Permitted Inputs for Gate-Enforcement

Gate-enforcement must consume only:
- The **canonical phase artifact** it is evaluating
- The **minimal gate-relevant context**: gate condition definition and evaluation criteria
- **Declared inputs only**: specific files listed in the gate-enforcement skill's `reads_from`

### 11.2 Prohibited Inputs for Gate-Enforcement

Gate-enforcement must not be fed:
- Broad phase output directories (entire `phase_outputs/` tree)
- Large Tier 2 source corpora (full work programme documents, grouped JSONs)
- Unrelated artifacts from other phases or tiers

### 11.3 Purpose of Containment

Gate-enforcement is a compliance-checking step, not a reasoning step. Its prompt must remain bounded (~10-20KB). Gate-enforcement remains on cli-prompt mode permanently.

---

## 12. Prompt-Budget Enforcement as Permanent Rule

### 12.1 The Rule

**Prompt-budget enforcement remains mandatory for all execution modes.** TAPM's ability to read files from disk via Read tool does not justify unbounded corpus ingestion.

### 12.2 Specific Constraints

1. **Bounded input selection remains mandatory.** Every skill invocation must operate on a declared, bounded set of inputs.
2. **Step 0 call slicing is the mandatory input bounding strategy.** Step 0 deterministically extracts the target call before any Claude invocation. Even when Claude can read files from disk via TAPM, navigating 338KB of irrelevant topic data through Read tool calls is wasteful and non-deterministic. Step 0 eliminates this at the source.
3. **TAPM access does not justify broad corpus ingestion.** Skills must read only what is necessary. The `reads_from` set constrains what is declared available.
4. **Input budgets apply to both modes.** CLI-prompt skills: total prompt <50KB. TAPM skills: TAPM prompt <30KB; declared `reads_from` sets must remain bounded.

### 12.3 Why This Rule is Permanent

The prompt-budget bottleneck was caused by unbounded input serialization. TAPM solves the serialization mechanism but does not solve unbounded input selection. Without this rule, future `reads_from` over-declaration could re-introduce waste.

---

## 13. TAPM Advantages Over the Deferred Native Backend

This section explains why TAPM is architecturally preferable as the immediate path, not merely a compromise.

| Property | TAPM | Native Backend (Deferred) |
|---|---|---|
| Artifact write control | **Python-exclusive** — Claude has no Write tool; cannot write to disk | Requires enforcement; Claude would have repo write access |
| Schema validation | External, guaranteed — Python validates before write | Same, but risk of Claude pre-writing |
| Skill spec delivery | Python reads and embeds — deterministic | Claude loads natively — depends on discovery |
| Input boundary enforcement | Prompt-based + post-hoc audit | Same mechanism (no hard sandboxing available) |
| Rollback granularity | One YAML field per skill | Same |
| Implementation complexity | ~120 lines changed across 2 files + 1 new module | ~350 lines across 3 new modules + format conversion of 21 skill files |
| Dependency on Claude Code features | `--tools` flag only (confirmed working) | Skill discovery, agent discovery, slash-command automation (all unproven) |
| Governance risk | Zero — same transport, same contracts | Medium — new execution model, new trust boundary |

**TAPM is not a weaker version of the native backend.** It is a stronger version for artifact write discipline (Claude has no write access) with equivalent prompt-reduction benefit, lower implementation cost, and zero dependency on unproven Claude Code features.

---

## 14. Invariant Checklist After Each Step

This checklist must be re-verified after every migration step (Steps 0-7).

| # | Invariant | Why it matters | How to verify |
|---|---|---|---|
| 1 | Scheduler still blocks invalid nodes | DAG scheduler must refuse to dispatch nodes whose entry gates have not passed | Run a phase with a deliberately missing upstream artifact. Confirm `blocked_at_entry`. |
| 2 | Gate failure still prevents downstream release | Exit gate failure must prevent downstream nodes from executing | Inject a malformed phase artifact. Confirm exit gate fails and downstream nodes are `hard_block_upstream`. |
| 3 | Artifacts remain reproducible from same inputs | Same `reads_from` inputs and `run_id` must produce structurally equivalent output regardless of mode | Run migrated skill in both modes on identical inputs. Confirm both pass `_validate_skill_output()`. |
| 4 | No undeclared file reads occurred | TAPM Claude must not read files outside declared `reads_from` set | Audit `--output-format stream-json` log for Read tool calls. Compare against declared `reads_from`. |
| 5 | No undeclared file writes occurred | Claude must not write to disk (Write tool not granted in TAPM) | Confirm `--tools "Read,Glob"` does not include Write. Verify `git status` shows no unexpected changes. |
| 6 | Run summary remains deterministic | `run_summary.json` must have same structural fields regardless of mode | Compare `run_summary.json` between cli-prompt and TAPM runs. |
| 7 | Artifact validation remains external | `_validate_skill_output()` runs after Claude returns, not inside Claude's reasoning | Confirm validation is called in `run_skill()` after response parsing, for both modes. |
| 8 | Gate evaluation remains external | `evaluate_gate()` called by scheduler only | Confirm no new `evaluate_gate()` call sites in skill_runtime or agent_runtime. |
| 9 | Fail-closed behavior remains intact | Malformed output → `SkillResult(status="failure")` | Send deliberately malformed response through TAPM path. Confirm failure result. |
| 10 | Mode choice does not alter DAG semantics | Same manifest, same inputs, same gate conditions → same node state transitions | Run full DAG in cli-prompt mode, then with TAPM skills. Compare `run_summary.json` node states. |

---

## 15. Logical Skill/Agent Split Recommendations

### 15.1 No Splits Needed for TAPM Migration

With TAPM, Claude reads only the declared input files from disk rather than receiving a serialized corpus. The current single-skill designs work well because:
- Call slicing eliminates the grouped JSON waste at the source
- Per-file Read calls are bounded by the `reads_from` declaration
- No skill's declared inputs exceed a reasonable Read budget (~10 files)

### 15.2 Future Consideration: Per-Invocation Scoping for Phase 8

When `proposal-section-traceability-check` is invoked 3 times during Phase 8, the agent runtime's context passing should narrow the `reads_from` set to the section being checked. This is an agent-runtime enhancement, not a skill split.

---

## 16. Future Path: True Native Claude Code Backend

### 16.1 Status

**BLOCKED.** Not part of the immediate implementation sequence.

### 16.2 Conditions for Unblocking

All five items in Section 3 ("Operationally Unproven Assumptions") must be resolved with positive evidence:

1. Repo-local `.claude/skills/` discovery confirmed working
2. Repo-local `.claude/agents/` discovery confirmed working
3. Automatable skill invocation in `-p` mode or via Agent SDK
4. Session bootstrap requirements understood and acceptable
5. Path-bounded file-read enforcement mechanism demonstrated

### 16.3 Migration Path If Unblocked

If all conditions are met, the native backend would extend TAPM:

1. Convert skill files to Claude Code's expected format (directory-based, standard frontmatter)
2. Replace TAPM prompt assembly with execution request handoff (~1-5KB metadata)
3. Claude Code loads skill definition natively (Python no longer reads it)
4. Artifact write discipline, schema validation, and atomic writes remain external
5. All governance semantics unchanged

The TAPM infrastructure (mode selection in `run_skill()`, transport `tools` parameter, call slicer) would remain in place. The native backend would be a third mode option alongside cli-prompt and TAPM.

### 16.4 Agent SDK as Potential Bridge

The Claude Agent SDK (`claude-agent-sdk` Python package) offers `query()` with `ClaudeAgentOptions(setting_sources=["project"], allowed_tools=[...])`. This could enable programmatic skill invocation if:
- The SDK is installed and compatible with the Claude Code Max subscription
- `setting_sources=["project"]` loads repo-local skills in the correct format
- `tool_approval_callback` can enforce path restrictions
- Streaming output can be captured and parsed into `SkillResult`

The Agent SDK represents the most plausible bridge to the native backend but requires dedicated investigation not included in the immediate TAPM migration.

---

## 17. Summary of Changes from Rev 1.0

| Section | Rev 1.0 | Rev 2.0 |
|---|---|---|
| Context | Native Claude Code backend as target | TAPM as immediate target; native backend deferred |
| Section 2 (Target Architecture) | Native Claude Code execution model | TAPM execution model; native backend → Section 16 (future) |
| Section 2.0 (Anti-Goal) | Explicitly rejected `--tools "Read"` approach | Removed — TAPM is the `--tools "Read,Glob"` approach, now the recommended path |
| Section 2.1 (Architecture) | `native-claude-code` adapter | `tapm` mode within existing transport |
| Section 2.4 (Execution Adapter) | Two adapters: cli-prompt and native-claude-code | Two modes: cli-prompt and tapm (same transport, different prompt assembly) |
| Section 2.5 (Context Access) | Execution request containment | Prompt-based containment + post-hoc audit |
| Section 2.6 (Write Discipline) | Claude produces JSON in response, cannot write directly — but no hard Write-tool exclusion stated | Claude has no Write tool in TAPM — stronger write discipline |
| Section 3 | N/A | NEW: Operationally Unproven Assumptions (5 items with evidence) |
| Section 6 Steps | Steps 1-2: NativeExecutionAdapter, ExecutionRequest | Steps 1-2: Transport enhancement, TAPM prompt assembly |
| Section 6 Step labels | `native-claude-code` throughout | `tapm` throughout |
| Section 9 rollout | Dependent on native adapter | Dependent only on transport `tools` parameter |
| Section 13 | N/A | NEW: TAPM advantages over deferred native backend |
| Section 16 | N/A | NEW: Future path for native backend with unblocking conditions |
| New modules | `native_backend.py`, `execution_request.py` | Neither needed — changes are within existing `skill_runtime.py` and `claude_transport.py` |

### What Was NOT Changed

- Section 1 (Diagnosis) — unchanged
- Section 4 (Division of Responsibilities) — skill classifications unchanged; label changed from `native-claude-code` to `tapm`
- Section 5 (Grouped JSON Strategy) — unchanged
- Section 10 (External/Unchanged Modules) — unchanged
- Section 11 (Gate-Enforcement Containment) — unchanged
- Section 12 (Prompt-Budget Enforcement) — unchanged
- Section 14 (Invariant Checklist) — unchanged except Write-tool exclusion added
- Manifest/DAG semantics — unchanged
- Runtime contracts — unchanged
- Fail-closed behavior — unchanged
- External scheduler/gates/validation — unchanged

---

## 18. Phase 3 — Migration Status

Phase 3 is operationally complete but not fully optimized.

**Current characteristics:**
- Uses CLI prompt mode (not TAPM)
- Produces `wp_structure.json` (~30KB structured artifact)
- Includes dependency graph construction

**Known limitations:**
- No TAPM migration for core skills:
  - `work-package-normalization`
  - `wp-dependency-analysis`
  - `gate-enforcement`
- Global token limit (8192) may be insufficient for large WP structures

**Migration actions:**
- Add `execution_mode: "tapm"` to Phase 3 skills
- Introduce per-skill `max_tokens` override (≥16384)

---

## 19. Phase 4 — Migration Readiness (OPERATIONAL — VALIDATED)

Phase 4 is operationally complete. Remediation was implemented and validated by a successful Phase 4 gate pass at runtime.

### Remediation applied (4 components)

1. **Dependency normalization layer** (`runner/dependency_normalizer.py`):
   - Pure-Python deterministic preprocessor, no Claude invocation
   - Reads Phase 3 `wp_structure.json` + Tier 3 `workpackage_seed.json` + `selected_call.json`
   - Reclassifies 16 infeasible WP-level `finish_to_start` edges as `non_strict`
   - Preserves 3 feasible task-level `finish_to_start` edges as `strict`
   - Writes `scheduling_constraints.json` to Phase 4 output directory
   - Integrated via `agent_runtime.py` Phase B+ (before agent body, after input resolution)

2. **Gantt-producing skill** (`gantt-schedule-builder`):
   - Skill spec: `.claude/skills/gantt-schedule-builder.md`
   - Registered in `skill_catalog.yaml`, added to n04 manifest skill list
   - Reads: wp_structure.json, scheduling_constraints.json, selected_call.json, roles.json, milestones_seed.json
   - Writes: `gantt.json` (schema `orch.phase4.gantt.v1`) — the canonical Phase 4 gate artifact
   - Executes before `milestone-consistency-check` so the validation skill sees gantt.json on disk and runs in FULL mode
   - Uses cli-prompt mode; TAPM migration deferred (moderate input size ~40-50KB, not a bottleneck)

3. **Gate hardening** (`g05_p02c`, `g05_p02d`, `g05_p08`):
   - `g05_p02c`/`g05_p02d`: file existence + run ownership for `scheduling_constraints.json`
   - `g05_p08` (`dependency_schedule_consistency`): validates gantt.json task schedule respects all strict normalized constraints
   - Non-strict constraints are not enforced (informational data flow only)

4. **Skill sequencing**:
   - n04 skill execution order: `gantt-schedule-builder` → `milestone-consistency-check` → `decision-log-update` → `gate-enforcement`
   - `gantt.json` written to disk before milestone validation; skill detects it and runs in FULL mode
   - `gate-enforcement` always last (enforced by agent runtime)

### Previous blocking issues (resolved)

1. ~~Dependency semantics mismatch~~ → Normalizer reclassifies infeasible edges
2. ~~Gate incompleteness~~ → `g05_p08` predicate added
3. ~~No gantt-producing skill~~ → `gantt-schedule-builder` added to n04
4. ~~Milestone validation in DEGRADED mode~~ → gantt.json now present before milestone-consistency-check runs

### Phase 4 TAPM Suitability

Phase 4 input size (~40-50KB) is moderate. `gantt-schedule-builder` uses cli-prompt mode.

TAPM is:
- Not required for correctness
- Recommended for consistency and future scaling

Priority: Phase 1 >> Phase 3 > Phase 4

---

## 20. Predicate Layer Expansion (Phase 4)

The Phase 4 predicate set has been extended for temporal correctness.

**Implemented:**

- `dependency_schedule_consistency` (`g05_p08`) — validates gantt.json task schedule respects strict normalized constraints from scheduling_constraints.json. Operational and gate-enforced.

**Recommended future additions (not yet implemented):**

- `milestone_traceability` — verify each milestone is linked to at least one deliverable or task
- `task_duration_positive` — verify every task has `end_month > start_month`

These would further extend gate validation but are not required for current Phase 4 gate passage.

---

## 21. Migration Guardrail

No phase implementation may proceed if:

- artifact schema ≠ gate expectations
- dependency semantics are ambiguous
- required predicates are missing

This enforces fail-closed migration discipline.
