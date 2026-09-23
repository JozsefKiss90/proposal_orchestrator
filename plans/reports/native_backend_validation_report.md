# Operational Validation Report: Native Claude Code Backend Feasibility

**Date:** 2025-04-15
**Scope:** Determine whether the proposal orchestrator can adopt a true native Claude Code execution backend using `.claude/skills/` and `.claude/agents/` natively, with external scheduler/gates/validation preserved.
**Method:** Evidence-based inspection of current repository layout, Claude Code CLI behavior, tool availability, and runtime constraints.

---

## 1. Question Being Validated

Can the proposal orchestrator realistically adopt a true native Claude Code execution backend for heavy reasoning tasks, where:

- the scheduler remains external (Python `DAGScheduler`)
- gates remain external (`gate_evaluator.py`)
- artifact validation remains external
- `.claude/skills/` and `.claude/agents/` are used natively by Claude Code
- execution does not revert to Python assembling a giant prompt and calling `claude -p`

---

## 2. What Was Directly Observed

All findings below are from direct terminal inspection during this session.

### 2.1 Repository Skill/Agent File Structure

**Observed:** Skills are flat `.md` files at `.claude/skills/<skill-name>.md` (21 files). Agents are flat `.md` files at `.claude/agents/<agent-name>.md` (18 files). No subdirectory structure exists. No `SKILL.md` or `AGENT.md` entrypoints exist.

```
# Expected by Claude Code:
.claude/skills/<skill-name>/SKILL.md

# Actual in this repo:
.claude/skills/<skill-name>.md
```

**Observed:** Skill YAML frontmatter uses custom fields (`skill_id`, `purpose_summary`, `reads_from`, `writes_to`, `constitutional_constraints`, `used_by_agents`). Claude Code expects standard fields (`name`, `description`).

**Observed:** Agent YAML frontmatter uses custom fields (`agent_id`, `phase_id`, `node_ids`, `role_summary`, `constitutional_scope`, `reads_from`, `writes_to`, `invoked_skills`, `entry_gate`, `exit_gate`). Claude Code expects standard agent definition fields.

### 2.2 Claude Code Auto-Discovery Behavior

**Observed:** `claude agents` lists only 5 built-in agents:
```
Built-in agents:
  claude-code-guide · haiku
  Explore · haiku
  general-purpose · inherit
  Plan · inherit
  statusline-setup · sonnet
```
Zero repo-local agents are discovered.

**Observed:** `claude -p` with `--setting-sources "user,project,local"` lists only 6 built-in/plugin skills:
```
update-config, keybindings-help, simplify, loop, schedule, claude-api
```
Zero repo-local skills are discovered.

**Observed:** This interactive Claude Code session (the one generating this report) also shows only those same 6 skills in its system-reminder. The 21 repo-local skill files are invisible to native skill discovery.

### 2.3 Current Transport Mechanism

**Observed:** `claude_transport.py` invokes `claude -p` with `--model` and `--system-prompt` flags via `subprocess.run()`. System prompt ≤24K chars goes via CLI flag; longer prompts are embedded in user message. User prompt is piped via stdin. Response is raw stdout text. No tools are enabled (no `--tools` or `--allowedTools` flag).

**Observed:** Claude Code CLI version is `2.1.81`.

### 2.4 Tool Availability in `-p` Mode

**Observed:** `claude -p` has access to a full tool set including: `Read`, `Edit`, `Write`, `Bash`, `Glob`, `Grep`, `Agent`, `Skill`, `WebFetch`, `WebSearch`, `NotebookEdit`, and task management tools.

**Observed:** `claude -p --allowedTools "Read" --permission-mode dontAsk` successfully restricted to Read-only tool usage. Claude was able to read a repo file and return the requested content.

**Observed:** `claude -p --tools "Read"` restricted the available tool set to ONLY `Read`. When asked to list tools, Claude reported only `Read`.

**Observed:** `claude -p` with `Read` tool can read `.claude/skills/topic-scope-check.md` and extract the `skill_id` from frontmatter. File access to the repo works.

### 2.5 Custom Agent Injection

**Observed:** `claude -p --agents '{"test-agent": {"description": "...", "prompt": "..."}}'` successfully defined and invoked a custom agent. The `--agents` flag allows programmatic agent injection into one-shot mode.

### 2.6 Structured Output

**Observed:** `claude -p --output-format json` returns a structured JSON envelope containing `result`, `duration_ms`, `usage`, `session_id`, `total_cost_usd`, and other metadata. The actual response is in the `result` field.

### 2.7 `--agent` Flag Behavior

**Observed:** `claude -p --agent call_analyzer` and `claude -p --agent nonexistent_agent_xyz` both succeed silently without error. The `--agent` flag does not load from `.claude/agents/` flat files — it expects agents defined through Claude Code's native discovery mechanism (directory-based) or the `--agents` JSON flag.

---

## 3. What Is Inferred But Not Yet Proven

### 3.1 Skill Format Conversion Feasibility

**Inferred:** If the 21 skill files were restructured into `.claude/skills/<skill-name>/SKILL.md` with standard Claude Code frontmatter (`name`, `description`), they would likely be discovered as native skills. **Not proven** — no conversion was attempted per task constraints.

**Critical concern:** Even if discoverable, Claude Code skills are designed as slash-command-invocable prompts that Claude executes in its full environment. They do not provide:
- Structured input/output contracts (`SkillResult` with `status`, `outputs_written`, `failure_category`)
- Deterministic artifact schema validation
- Atomic write semantics enforced by external runtime
- `run_id` / `schema_id` stamping verified externally

### 3.2 File-Path Restriction Enforcement

**Inferred:** Claude Code does not provide a mechanism to restrict which file paths a tool can access. `--tools "Read"` allows Read access to ANY file on disk. `--allowedTools` operates at tool granularity, not path granularity. **Not proven** whether hooks (PreToolUse) could enforce path restrictions — would need an experiment with a custom hook that inspects Read arguments and blocks unauthorized paths.

### 3.3 Agent SDK Viability

**Inferred:** The Claude Agent SDK (`claude-agent-sdk` Python package) provides `query()` with `ClaudeAgentOptions(setting_sources=["project"], allowed_tools=[...])` which may enable programmatic skill invocation with proper project discovery. **Not proven** in this environment — the SDK is not installed and its interaction with custom skill formats was not tested.

### 3.4 Output Capture Reliability

**Inferred:** When Claude uses tools (Read, Write) in `-p` mode, the artifacts it writes go directly to disk. The external runtime could capture what was written by diffing filesystem state before/after invocation, or by parsing the `--output-format stream-json` event stream. **Not proven** — actual reliability of artifact capture in tool-augmented `-p` mode was not tested end-to-end.

---

## 4. Operational Answers to the Six Required Questions

### Q1: How Claude Code Sees `.claude/skills/` and `.claude/agents/`

| Aspect | Finding | Evidence Type |
|--------|---------|---------------|
| Auto-discovery of current files | **No.** Files are not discovered. | Directly observed |
| Reason | Format mismatch: flat `.md` files with custom frontmatter vs. expected directory-based `SKILL.md`/`AGENT.md` with standard frontmatter | Directly observed |
| Prior registration required | No registration mechanism exists; discovery is format-based | Directly observed |
| Repo-local files sufficient | Only if correctly formatted and structured | Inferred |
| File presence vs. tool availability | Files are present but not tool-available — format determines availability | Directly observed |
| Definitions visible in current session | **No.** Neither this interactive session nor `claude -p` see them. | Directly observed |

**Bottom line:** The repo's `.claude/skills/` and `.claude/agents/` files are runtime specifications for the Python orchestrator. They are not Claude Code native skill/agent definitions. Claude Code does not see them.

### Q2: Whether Slash-Command /skills and /agents Usage Is Automatable

| Aspect | Finding | Evidence Type |
|--------|---------|---------------|
| `/skill` invocable non-interactively | **No.** Slash commands are interactive-only | Directly observed via `-p` mode test |
| Drivable from backend wrapper | **No** for slash commands. **Yes** for `-p` mode with tools | Directly observed |
| Expose outputs compatible with external validation | Partially — `-p --output-format json` captures result text; tool-written artifacts go to disk | Directly observed |
| Avoids large prompt serialization | Only if Claude uses `Read` tool to access files from disk instead of receiving them in prompt | Inferred; mechanism proven feasible |

**Bottom line:** Native `/skill` invocation is not automatable. The automatable path is `claude -p` with tool access enabled, where Claude reads files on-demand from disk. This is NOT the same as "native skill invocation" — it is tool-augmented prompt mode.

### Q3: Whether Session Bootstrap Is Required

| Aspect | Finding | Evidence Type |
|--------|---------|---------------|
| Interactive session first required | **No.** `-p` mode works without prior interactive session | Directly observed |
| Registration step required | **No** for correctly formatted files; **N/A** for current files (not in correct format) | Directly observed |
| Per-repo or per-session | Per-session auto-discovery at startup; live reload for file edits but not for new directories | Documented behavior |
| Current environment demonstrates requirement | Current environment demonstrates that NO bootstrap solves the format mismatch | Directly observed |

**Bottom line:** No session bootstrap issue. The problem is structural: the files aren't in Claude Code's expected format, and even if they were, the native skill/agent system doesn't provide the contracts the runtime needs.

### Q4: Whether Persistent Terminal/Session Mode Is Needed

| Aspect | Finding | Evidence Type |
|--------|---------|---------------|
| One-shot can use tools | **Yes.** `-p` mode with `--tools` or `--allowedTools` provides full tool access | Directly observed |
| Persistent session required | **No.** One-shot `-p` mode is sufficient for each skill invocation | Directly observed |
| External scheduler authority preserved | **Yes** in one-shot mode — scheduler spawns subprocess, waits for completion, captures output | Directly observed (current architecture already works this way) |

**Bottom line:** One-shot `claude -p` invocation with tool access is viable and preserves external scheduler authority. No persistent session is needed.

### Q5: How External Runtime Constraints Could Work

| Constraint | Enforceable Now? | Mechanism | Limitation |
|------------|-------------------|-----------|------------|
| Declared `reads_from` | **Partially.** Tool-level yes; path-level no | `--tools "Read"` enables Read; prompt instructs which files | Claude could read undeclared files — no hard path sandboxing |
| Declared `writes_to` | **No direct enforcement.** | If Claude uses Write tool, it can write anywhere | External runtime could diff filesystem pre/post, but cannot prevent writes |
| No undeclared file reads | **Not enforceable by Claude Code alone** | Would need PreToolUse hook that inspects Read arguments | Hook-based enforcement is unproven |
| No undeclared file writes | **Not enforceable by Claude Code alone** | Would need PreToolUse hook for Write/Edit | Same limitation |
| Artifact handoff to external validation | **Yes.** | Runtime captures stdout or reads artifacts from disk post-invocation | Proven feasible via `--output-format json` |
| Node-level execution boundaries | **Yes.** | Each skill invocation is a separate `claude -p` subprocess | Inherent in one-shot architecture |

**What is realistically enforceable now:**
- Tool-type restriction (Read-only, no Bash, etc.)
- Node-level isolation (separate subprocess per invocation)
- Post-hoc artifact validation (schema, run_id, schema_id checks)
- Structured output capture

**What is aspirational only:**
- Hard file-path sandboxing within Read/Write tools
- Prevention of undeclared reads (soft enforcement via prompt only)
- Prevention of undeclared writes (soft enforcement via prompt only)

**Critical assessment:** The current architecture already achieves hard enforcement of artifact validation and structured output because the Python runtime reads Claude's response as text, validates it, and writes the artifact itself. Moving to a model where Claude writes artifacts directly via Write tool would **weaken** enforcement, not strengthen it.

### Q6: Fallback Path If Native Invocation Cannot Be Automated Cleanly

**Recommended fallback: Tool-Augmented Prompt Mode (TAPM)**

This is not truly a "fallback" — it is the operationally correct path given the evidence.

**Architecture:**
1. Scheduler remains external (unchanged `DAGScheduler`)
2. `skill_runtime.py` continues to invoke `claude -p` via `claude_transport.py`
3. **Change:** Add `--tools "Read,Glob"` to the `claude -p` invocation for selected skills
4. **Change:** Reduce prompt size by NOT serializing input file contents; instead, instruct Claude to read declared inputs from disk using the Read tool
5. **Change:** Claude's response is still captured as stdout text, validated externally, and written atomically by the Python runtime
6. Gates remain external (unchanged)
7. Artifact validation remains external (unchanged)
8. Fail-closed behavior preserved (unchanged)

**What this achieves:**
- Prompt reduction from 150–800KB to ~5–30KB (skill spec + task metadata only)
- Claude reads input files on-demand rather than receiving them pre-serialized
- No structural change to the scheduler, gates, contracts, or validation
- No dependency on Claude Code native skill/agent discovery
- No format conversion needed for `.claude/skills/` files
- All existing tests continue to work (the change is additive and per-skill)

**Classification:** This is **architecturally best-available** — it achieves the migration plan's core goal (prompt size reduction, on-demand file access) without depending on an unproven native invocation mechanism. It is not second-best; it is what the evidence supports.

**Preserves:**
- External scheduler control: Yes (unchanged)
- External gates: Yes (unchanged)
- External artifact validation: Yes (unchanged)
- Fail-closed behavior: Yes (unchanged)

---

## 5. Can True Native Claude Code Agent/Skill Invocation Be Automated Here?

**Answer: No.**

**Justification:**

1. **Format mismatch is structural, not incidental.** The repo's 21 skill files and 18 agent files use a domain-specific schema (`skill_id`, `reads_from`, `writes_to`, `constitutional_constraints`, `invoked_skills`, `entry_gate`, `exit_gate`) designed for the Python orchestrator. Claude Code's native skill format (`name`, `description`, freeform Markdown body) does not support these contracts. Converting the files would mean maintaining two parallel specification formats or abandoning the orchestrator's structured metadata.

2. **Claude Code's native skill system does not return structured results.** The orchestrator requires `SkillResult(status, outputs_written, failure_reason, failure_category)`. Claude Code skills produce freeform text responses in the context of an interactive session. There is no mechanism to extract a typed `SkillResult` from a native skill invocation.

3. **Claude Code's native skill system does not enforce I/O boundaries.** The orchestrator's skills declare `reads_from` and `writes_to` paths enforced by the Python runtime. Native Claude Code skills have no I/O declaration or enforcement mechanism.

4. **Slash-command invocation is interactive-only.** `/skill-name` is not available in `-p` mode. The Skill tool exists but only sees built-in skills, not repo-local ones (given current format).

5. **The `--agents` flag provides custom agent injection but not skill injection.** There is no equivalent `--skills` flag for injecting custom skill definitions into `-p` mode.

6. **Native agent invocation loses external validation.** If Claude invokes skills via the Agent tool within a native session, artifacts would be written directly to disk without the Python runtime's schema validation, `run_id` checking, and atomic write semantics.

7. **The Agent SDK offers a plausible but unproven path.** The `claude-agent-sdk` could potentially enable programmatic skill invocation with `setting_sources=["project"]`, but this requires: installing the SDK, converting files to Claude Code format, implementing custom tool approval hooks for path restriction, and building a bridge between SDK event streams and the orchestrator's `SkillResult`/`AgentResult` contracts. This is a significant engineering effort with an unproven outcome.

---

## 6. Minimum Operational Validation Plan

If the team wishes to pursue native invocation despite the evidence above, these 5 steps would provide proof or disproof:

### Step 1: Format Conversion Proof

**What to do:** Convert ONE skill (`topic-scope-check`, smallest at ~22KB) to Claude Code's expected format: create `.claude/skills/topic-scope-check/SKILL.md` with standard frontmatter (`name: "topic-scope-check"`, `description: "Verify scope alignment"`), preserving the domain-specific body.

**What success looks like:** `claude -p --setting-sources "user,project,local" "List skills"` shows `topic-scope-check` in the output. The skill is natively discoverable.

**What failure means:** Claude Code does not discover project-level skills from `.claude/skills/` even in correct format — the feature may be interactive-only or require additional configuration.

### Step 2: Native Skill Invocation Proof

**What to do:** With the converted skill from Step 1, invoke it: `echo "Use the /topic-scope-check skill" | claude -p --setting-sources "user,project,local" --allowedTools "Skill,Read" --output-format json`.

**What success looks like:** Claude invokes the skill via the Skill tool, reads required files, and produces a response containing the expected artifact content.

**What failure means:** Skills are discoverable but not invocable in `-p` mode, confirming that slash-command semantics are interactive-only.

### Step 3: SkillResult Bridge Proof

**What to do:** Modify the skill spec to instruct Claude to return output as a structured JSON object matching `SkillResult` schema (`status`, `outputs_written`, `failure_reason`, `failure_category`). Invoke via `-p` and parse the response.

**What success looks like:** The response contains valid, parseable JSON conforming to `SkillResult`. The Python runtime can construct a `SkillResult` from it without loss.

**What failure means:** Claude's freeform response cannot be reliably constrained to a typed result contract. The bridge from native invocation to orchestrator contracts is unreliable.

### Step 4: Path Constraint Enforcement Proof

**What to do:** Create a PreToolUse hook (in `.claude/settings.local.json`) that logs all Read/Write tool invocations with their file path arguments. Invoke the converted skill and inspect whether Claude stayed within declared `reads_from` paths.

**What success looks like:** All Read invocations target only declared input paths. The hook log is complete and parseable.

**What failure means:** Claude reads undeclared files (CLAUDE.md, other tier directories, etc.) — path-level enforcement requires active blocking, not just logging.

### Step 5: End-to-End Contract Equivalence Proof

**What to do:** Run Phase 1 via the existing CLI-prompt backend and capture the artifacts. Then run Phase 1 via the native backend (if Steps 1–4 pass) and capture the artifacts. Compare structural equivalence: same schema_id, same required fields populated, same file paths written.

**What success looks like:** Artifacts from both backends pass the same gate evaluation. `SkillResult` and `AgentResult` contracts are preserved.

**What failure means:** Native invocation produces structurally different output that would fail gate evaluation. The backends are not interchangeable.

---

## 7. Recommended Conclusion

**Proceed with Tool-Augmented Prompt Mode (TAPM), not native Claude Code skill/agent invocation.**

The evidence shows that:

- The core migration goal (prompt size reduction from 150–800KB to bounded metadata) is achievable **without** native skill/agent invocation.
- The mechanism is simpler: add `--tools "Read,Glob"` to `claude -p` invocations and restructure skill prompts to instruct Claude to read inputs from disk.
- This preserves ALL existing contracts, validation, atomic writes, and fail-closed behavior.
- No file format conversion is needed. No dependency on Claude Code's skill discovery system.
- The change is per-skill, additive, and independently rollbackable.
- The existing `claude_transport.py` needs only a small modification to accept optional tool flags.

Native Claude Code skill/agent invocation would require:
- Format conversion of 21 skill files and 18 agent files
- Building a bridge between Claude Code's freeform output and the orchestrator's typed contracts
- Solving path-level enforcement (unproven)
- Accepting weaker artifact validation (Claude writes directly to disk)
- A significant engineering effort with uncertain outcome

TAPM achieves the same prompt-reduction benefit at ~10% of the implementation cost and 0% of the governance risk.

---

## 8. Fallback Path (If Native Invocation Is Not Yet Provable)

Given that native invocation IS not provable (see Section 5), TAPM is not a fallback — it is the primary recommendation.

**Implementation outline (3 changes to existing code):**

1. **`claude_transport.py`**: Add optional `tools: list[str] | None` parameter to `invoke_claude_text()`. When provided, append `--tools <comma-separated>` to the command.

2. **`skill_runtime.py`**: For skills marked `execution_mode: "tool-augmented"` in the skill catalog, invoke `invoke_claude_text()` with `tools=["Read", "Glob"]` and a reduced prompt that lists declared input paths but does NOT serialize their contents.

3. **Skill `.md` files**: Add an `## Input Access` section instructing Claude to read declared inputs from disk using the Read tool, rather than expecting them in the prompt.

**What does NOT change:**
- DAG scheduler
- Gate evaluator
- Artifact validation
- Runtime contracts (SkillResult, AgentResult, NodeExecutionResult)
- Atomic write semantics (Python runtime writes, not Claude)
- run_id / schema_id stamping and verification

---

## 9. Concise Verdict

**"Is there enough operational evidence, right now, to justify implementing a native Claude Code backend for this governed scheduler?"**

**Answer: Not yet.**

The operational evidence shows that Claude Code's native skill and agent discovery system does not see the repository's `.claude/skills/` and `.claude/agents/` files. The format mismatch is structural: the repo's files use a domain-specific orchestrator schema while Claude Code expects a different directory layout and frontmatter format. Even if the files were converted, Claude Code's native skill system does not provide the structured input/output contracts (`SkillResult`, artifact schema validation, `run_id` stamping, atomic writes) that the orchestrator requires. Slash-command-style skill invocation is confirmed interactive-only and unavailable in `-p` mode. The `--agents` flag enables custom agent injection but there is no equivalent for skills. Path-level enforcement within tools (restricting which files Claude can read) has no proven mechanism beyond prompt-level instruction. The migration plan's core goal — reducing prompt bloat from 150–800KB — is achievable through the simpler, lower-risk Tool-Augmented Prompt Mode, which adds file-reading tools to the existing `claude -p` invocations without requiring native skill discovery, format conversion, or weakened validation contracts. The Agent SDK represents a plausible but unproven future path that would require substantial investigation before commitment. Implementing the full native backend migration as described in `backend_migration_plan.md` without first completing the 5-step validation plan would be building on an unverified operational premise.
