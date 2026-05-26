# Phase F TAPM Tool Emulation Implementation Brief

**Version:** 1.0
**Date:** 2026-05-26
**Status:** IMPLEMENTATION BRIEF — Ready for engineering
**Scope:** TAPM tool emulation loop for non-Claude OpenAI-compatible backends
**Constitutional authority:** CLAUDE.md (this brief is subordinate; implementation must comply)
**Depends on:** Phase E transport abstraction (complete)

---

## Objective

Implement the TAPM (Tool-Augmented Prompt Mode) tool emulation loop so that any OpenAI-compatible backend can execute the same TAPM skills that currently run on Claude CLI. When Claude CLI executes a TAPM skill via `claude -p --tools "Read,Glob"`, Claude natively handles tool calls inside its subprocess. Non-Claude backends have no native file-access tooling — the model emits `tool_calls` but nothing answers them unless the Python runtime intercepts, executes, and re-injects results.

Phase F closes this gap. It provides the interception layer — a Python-side tool loop that drives the `model → tool_calls → execute → tool result → continue` cycle — with equivalent filesystem access semantics and identical governance boundaries to the Claude CLI path.

No new providers, no new transport protocols, no changes to the DAG scheduler, gate evaluator, agent runtime, or skill runtime contracts.

---

## Architecture

### Pipeline

The tool emulation loop follows a strict linear pipeline. The model never receives direct filesystem access; all tool execution is Python-controlled.

```
OpenAI-compatible model
        ↓
tool_calls emitted (assistant message)
        ↓
Python ToolLoop (runner/transport/tool_loop.py)
        ↓
ToolExecutor (runner/transport/tool_executor.py)
        ↓
tool result injection (tool role message)
        ↓
continue completion (next backend round)
```

### Module Roles

| Module | Role | Writes to disk | Evaluates gates | Domain reasoning |
|--------|------|:--------------:|:---------------:|:----------------:|
| `tool_loop.py` | Drives the iterative request → tool_calls → execute → re-send cycle | No | No | No |
| `tool_executor.py` | Executes Read and Glob tool calls within a sandboxed repository | No | No | No |
| `openai_compatible.py` | HTTP transport adapter conforming to `ToolLoopBackend` protocol | No | No | No |
| `skill_runtime.py` | Calls `run_tool_loop()` for TAPM skills on non-Claude backends; writes artifacts via `_atomic_write()` | Yes (sole write path) | No | No |

### Call Graph

```
skill_runtime.run_skill()
    │
    ├── [Claude CLI path]  claude_transport.invoke_claude_text()
    │                       (Claude handles Read/Glob natively)
    │
    └── [OpenAI-compatible path]
            │
            ├── build_openai_backend(config, tools=[READ_TOOL_SCHEMA, GLOB_TOOL_SCHEMA])
            │
            └── run_tool_loop(backend=..., system_prompt=..., user_prompt=..., repo_root=..., allowed_prefixes=...)
                    │
                    ├── backend(messages)              → OpenAICompatBackend.__call__()
                    │                                     → POST /v1/chat/completions
                    │                                     → parse response
                    │                                     → return {content, tool_calls}
                    │
                    ├── ToolExecutor.execute_tool_call()  → Read or Glob (sandboxed)
                    │
                    └── inject tool result → loop continues
```

---

## Track F.1 — Core Tool-Call Transport Compatibility

### Message Flow Contract

The round-trip message flow must work correctly across all OpenAI-compatible backends:

1. **Initial messages.** `run_tool_loop()` constructs `[system, user]` message list.
2. **Backend invocation.** `backend(messages)` sends `POST /chat/completions` and returns `{"content": str | None, "tool_calls": [...] | None}`.
3. **Tool-call extraction.** If `tool_calls` is non-empty, the assistant message (including both `content` and `tool_calls`) is appended to the conversation history.
4. **Tool execution.** Each tool call is executed sequentially via `ToolExecutor.execute_tool_call()`.
5. **Tool-result injection.** Each result is appended as `{"role": "tool", "tool_call_id": <id>, "content": <result>}`.
6. **Loop continues.** Go to step 2 with the extended message list.
7. **Termination.** When `tool_calls` is empty/`None`, the loop returns the final `content`.

### Tool Call Format

The `ToolLoopBackend` protocol expects tool calls in OpenAI format:

```json
{
    "id": "call_abc123",
    "type": "function",
    "function": {
        "name": "Read",
        "arguments": "{\"file_path\": \"/repo/docs/data.json\"}"
    }
}
```

### Tool Result Format

Tool results are injected using the OpenAI tool-result message format:

```json
{
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "{\"key\": \"value\"}"
}
```

The `tool_call_id` must exactly match the originating tool call's `id` field. Providers that do not return stable tool-call IDs will produce correlation errors. This is a provider-quality issue, not a loop defect.

### Argument Format Tolerance

The loop accepts `function.arguments` as either:
- A JSON string (standard OpenAI format): `"{\"file_path\": \"/a.txt\"}"`
- A pre-parsed dict (some providers): `{"file_path": "/a.txt"}`

Malformed arguments that cannot be parsed as JSON produce a structured error result injected back to the model:

```json
{"error": "Malformed tool arguments for 'Read': could not parse as JSON"}
```

The loop does **not** abort on malformed arguments. The model receives the error and may self-correct or produce a final response.

### Multi-Tool-Call Handling

When the assistant emits multiple `tool_calls` in a single response:

1. All calls are executed sequentially within the same round.
2. All results are injected before the next backend invocation.
3. The execution order follows the array order of `tool_calls`.

### Round Budget

`max_rounds` (default 25) bounds total backend invocations (initial + tool-result rounds). When exhausted:

- The loop returns `ToolLoopResponse(exhausted_rounds=True)` with the last available assistant content.
- No exception is raised. The caller (skill runtime) decides whether exhaustion constitutes a failure.

### Timeout Enforcement

Wall-clock `timeout_seconds` applies to the **entire loop**, not per-round:

- Before each backend invocation, the loop checks `time.monotonic()` against the deadline.
- If the deadline has passed, the loop returns `ToolLoopResponse(exhausted_rounds=True)` immediately, without invoking the backend again.
- Per-request HTTP timeouts are configured separately on the `OpenAICompatBackend` via `httpx.Timeout`.

### Content Preservation

The `content` field of assistant messages that also contain `tool_calls` is preserved in the conversation history. Some providers return `null`, some return partial text. The loop preserves whatever the backend returns.

---

## Track F.2 — Tool Schema Normalisation

### Schemas

Two tool schemas are provided in OpenAI function-calling format:

#### `READ_TOOL_SCHEMA`

```json
{
    "type": "function",
    "function": {
        "name": "Read",
        "description": "Read a file from the local filesystem. Returns file content as text. The file_path must be an absolute path.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to read"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-based). Optional."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of lines to read. Optional."
                }
            },
            "required": ["file_path"]
        }
    }
}
```

#### `GLOB_TOOL_SCHEMA`

```json
{
    "type": "function",
    "function": {
        "name": "Glob",
        "description": "Find files matching a glob pattern in a directory. Returns a newline-separated list of matching absolute paths.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g. '**/*.json')"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in. Must be an absolute path. Defaults to the repository root if omitted."
                }
            },
            "required": ["pattern"]
        }
    }
}
```

### Normalisation Requirements

| Requirement | Detail |
|-------------|--------|
| **Envelope format** | OpenAI `{"type": "function", "function": {...}}` — accepted by Bedrock (bedrock-mantle), Together AI, Ollama, and generic OpenAI-compatible endpoints. |
| **Parameter types** | JSON Schema primitives only (`string`, `integer`, `object`). No provider-specific extensions. |
| **Description terseness** | Descriptions are action-oriented and concise to minimise prompt token overhead. |
| **Delivery** | Schemas are passed to `OpenAICompatBackend` via the `tools` constructor parameter and included in every request payload when non-empty. |
| **Provider tolerance** | Providers that silently ignore the `tools` field will never emit `tool_calls`. The loop terminates on the first round with a final text-only response. This is a capability gap, not an error — surfaced by capability gating (F.4). |

### Schema Location

Both schemas are defined as module-level constants in `runner/transport/tool_executor.py` and re-exported from `runner/transport/__init__.py`.

---

## Track F.3 — Deterministic TAPM Equivalence Tests

### Equivalence Definition

For a given set of declared input files and a given skill prompt, the tool emulation path and the Claude CLI path must:

1. Access the same files (given the same tool-call sequence).
2. Enforce the same sandbox boundaries.
3. Produce structurally compatible outputs (same JSON schema, same required fields).

Field-level text equivalence is **not** required — different models produce different text. Structural and schema equivalence is.

### Test Categories

| Category | What it validates | Module under test |
|----------|-------------------|-------------------|
| **Read sandbox enforcement** | Paths outside `repo_root` are denied. Symlinks escaping the repo boundary are denied after `.resolve()`. Declared-input prefix enforcement restricts access to `reads_from` declaration. | `tool_executor.py` |
| **Read byte budgets** | Per-file limit (`MAX_FILE_READ_BYTES` = 512,000 bytes). Cumulative limit (`MAX_TOTAL_READ_BYTES` = 5,000,000 bytes). Over-budget reads return `{"error": "..."}`. | `tool_executor.py` |
| **Read line slicing** | `offset` (1-based) and `limit` produce correct line ranges matching Claude Code Read semantics. | `tool_executor.py` |
| **Glob sandbox enforcement** | Search base must be inside `repo_root`. Results filtered post-glob to remove symlink escapes. Declared-input prefix enforcement applies to search base and each result. | `tool_executor.py` |
| **Glob result limits** | Results capped at `MAX_GLOB_RESULTS` (200). Deterministic sorted order. | `tool_executor.py` |
| **Error structure equivalence** | All denial/error conditions produce `{"error": "..."}` JSON strings. | `tool_executor.py` |
| **Unknown tool rejection** | Unknown tool names (Write, Bash, Edit, etc.) produce structured errors. | `tool_executor.py` |
| **Tool loop round-trip** | Single Read, single Glob, Glob→Read chain, multi-tool single round, malformed arguments, unknown tool recovery, round exhaustion. | `tool_loop.py` |
| **No-write invariant** | Filesystem state is unchanged after tool loop execution. | `tool_loop.py` |
| **OpenAI backend protocol** | Payload construction, response parsing, tool-call extraction, usage capture, error normalisation. | `openai_compatible.py` |

### Test Implementation

All deterministic equivalence tests use `FakeBackend` with pre-programmed tool call sequences. No live model invocation is required. Test fixtures create temporary sandbox directories with controlled file layouts. Symlink tests are skipped on Windows where symlink creation requires elevated privileges.

---

## Track F.4 — Capability Gating

### Gating Rule

The `ProviderCapabilities.tool_calling` field gates TAPM skill eligibility at dispatch time:

| `tool_calling` | Behaviour |
|----------------|-----------|
| `True` | Backend may execute TAPM skills via the tool emulation loop. Tool schemas are included in request payloads. |
| `False` | Backend is restricted to cli-prompt mode skills only. TAPM skill dispatch must fail with `MISSING_INPUT` failure category **before** any backend invocation. |

### Current Provider Declarations

| Backend | `tool_calling` | TAPM eligible | Notes |
|---------|:--------------:|:-------------:|-------|
| `claude_cli` | `True` | Yes | Native — no emulation needed |
| `bedrock` | `True` | Yes | Client-side tool calling via bedrock-mantle |
| `together_ai` | `True` | Yes | OpenAI-format tool calling confirmed |
| `ollama` | `True` | Yes | Model-dependent; some quantised models may ignore tool schemas |
| `openai_compatible` | `True` | Yes | Provider-dependent |

### Runtime Gating Contract

Before constructing the tool loop for a TAPM skill invocation, the skill runtime must check `config.capabilities.tool_calling`. If `False`:

```python
return SkillResult(
    status="failure",
    outputs_written=[],
    failure_reason="Backend does not support tool calling; cannot execute TAPM skill",
    failure_category="MISSING_INPUT",
)
```

No backend invocation occurs. No HTTP request is sent.

### Model-Level Fidelity Caveat

Static capability gating confirms the provider **API** supports tool calling. It does not guarantee that a specific **model** will emit well-formed tool calls. Models that accept tool schemas but never emit `tool_calls` (or emit malformed ones) will produce empty or error-laden tool loop responses. This is a quality issue surfaced by equivalence testing (F.3), not a gating issue.

---

## Security Invariants

These invariants are constitutional requirements (CLAUDE.md §17) and must hold for every code path in this phase:

| # | Invariant | Enforcement mechanism |
|---|-----------|----------------------|
| 1 | **Tool execution is Python-side only.** The LLM never receives unrestricted filesystem access. It emits tool-call requests; the `ToolExecutor` decides whether to honour them. | `ToolExecutor.execute_tool_call()` — all authorisation logic is in Python. |
| 2 | **Read-only access.** The executor provides Read and Glob only. No Write, Edit, Delete, or Bash tool exists. | `KNOWN_TOOLS = frozenset({"Read", "Glob"})` — unknown tools are rejected. |
| 3 | **Sandbox enforcement.** All file access is confined to the repository root. Paths resolved via `.resolve()` before boundary checks. | `is_within()` uses `pathlib.Path.relative_to()`, not string-prefix matching. |
| 4 | **Declared-input boundary.** When `allowed_prefixes` is provided (always for TAPM skills), only paths matching the skill's `reads_from` declaration are accessible. | `_is_in_allowed_prefixes()` checks each resolved path against each prefix. |
| 5 | **Symlink escape prevention.** Symlinks that resolve outside the repository root or declared-input boundary are denied. | Both sides (path and root) are `.resolve()`-d before comparison. |
| 6 | **Byte budgets.** Per-file limit (500KB) and cumulative limit (5MB) prevent excessive data transfer to the model. | `MAX_FILE_READ_BYTES`, `MAX_TOTAL_READ_BYTES` checked before content return. |
| 7 | **Structured error responses.** Every denial produces `{"error": "..."}` — the model sees the denial, not a silent failure. | `_make_error()` in `tool_executor.py`. |
| 8 | **No filesystem mutations.** The tool loop and tool executor never write, delete, or modify files. | No write calls exist in either module. Test `TestToolLoopNoWrites` verifies. |
| 9 | **Artifact writes are Python-controlled.** Writes remain exclusively in `skill_runtime._atomic_write()`. | Architectural invariant; no write path exists in the tool loop. |

---

## Affected Components

| Component | Path | Change Required |
|-----------|------|----------------|
| Tool executor | `runner/transport/tool_executor.py` | **Implemented.** Read/Glob execution, sandbox enforcement, byte budgets, error handling. |
| Tool loop | `runner/transport/tool_loop.py` | **Implemented.** Iterative tool-call cycle, FakeBackend, round limits, timeout. |
| Tool schemas | `runner/transport/tool_executor.py` | **Implemented.** `READ_TOOL_SCHEMA`, `GLOB_TOOL_SCHEMA` as module constants. |
| OpenAI backend | `runner/transport/openai_compatible.py` | **Implemented.** `ToolLoopBackend` protocol, tool-call extraction, usage capture. |
| Capabilities | `runner/transport/capabilities.py` | **Implemented.** `ProviderCapabilities.tool_calling` field in all registry entries. |
| Package exports | `runner/transport/__init__.py` | **Implemented.** Re-exports `ToolExecutor`, schemas, `run_tool_loop`, `FakeBackend`, `ToolLoopResponse`. |
| Config/presets | `runner/transport/config.py` | **Implemented.** `build_openai_backend()` accepts `tools` parameter for TAPM mode. |
| Error types | `runner/transport/errors.py` | No change. Existing error normalisation applies. |
| Claude CLI transport | `runner/claude_transport.py` | No change. Remains the reference backend. |
| Skill runtime | `runner/skill_runtime.py` | **Integration point.** Must route TAPM skills to `run_tool_loop()` when backend is non-Claude, with capability check. |
| DAG scheduler | `runner/dag_scheduler.py` | No change. |
| Gate evaluator | `runner/gate_evaluator.py` | No change. |
| Agent runtime | `runner/agent_runtime.py` | No change. |

---

## Integration Point: Skill Runtime

The skill runtime (`runner/skill_runtime.py`) is the sole integration point for Phase F. When processing a TAPM skill on a non-Claude backend:

```python
# Pseudocode — integration point in run_skill()

if backend_is_openai_compatible and skill_mode == "tapm":
    # F.4: Capability gate
    if not config.capabilities.tool_calling:
        return SkillResult(
            status="failure",
            outputs_written=[],
            failure_reason="Backend does not support tool calling",
            failure_category="MISSING_INPUT",
        )

    # F.2: Build backend with tool schemas
    backend = build_openai_backend(
        config,
        tools=[READ_TOOL_SCHEMA, GLOB_TOOL_SCHEMA],
        timeout_seconds=TAPM_TIMEOUT_SECONDS,
    )

    # F.1: Run tool loop
    loop_result = run_tool_loop(
        backend=backend,
        system_prompt=assembled_system_prompt,
        user_prompt=assembled_user_prompt,
        repo_root=repo_root,
        allowed_prefixes=skill_reads_from,
        max_rounds=DEFAULT_MAX_ROUNDS,
        timeout_seconds=TAPM_TIMEOUT_SECONDS,
    )

    # Parse, validate, and write artifact
    response_text = loop_result.text
    # ... existing validation and _atomic_write() logic ...
```

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Model never emits `tool_calls` despite receiving tool schemas | Medium | Capability gating (F.4) prevents dispatch to incapable backends. For capable backends, this is a model-quality issue — surface via equivalence testing (F.3). |
| Model emits malformed `function.arguments` JSON | Low | Loop injects structured error result; model may self-correct. Persistent malformation exhausts round budget and returns failure. |
| Provider returns unstable or missing `tool_call_id` values | Low | Loop uses empty-string fallback for missing IDs. Correlation errors may occur if IDs are reused or absent. |
| Round budget (25) insufficient for complex TAPM skills | Low | Phase 8 skills may require more rounds. Monitor `exhausted_rounds` in early equivalence testing. Configurable via `max_rounds` parameter. |
| Cumulative read budget (5MB) exceeded for large-input skills | Low | The 5MB limit covers the vast majority of skills. Phase 7 budget-gate validation (largest observed: 163K tokens) is a cli-prompt skill, not TAPM. |
| Symlink test coverage incomplete on Windows | Low | Symlink tests are skipped on Windows (`sys.platform == "win32"`). Full symlink coverage requires Linux/macOS CI. |

---

## Implementation Checklist

| Step | Track | Action | Status |
|------|-------|--------|--------|
| 1 | F.1 | Implement `ToolExecutor` class with Read/Glob execution, sandbox enforcement, byte budgets | **Complete** |
| 2 | F.1 | Implement `run_tool_loop()` with round limits, timeout, message management | **Complete** |
| 3 | F.1 | Implement `FakeBackend` for test-only synthetic tool-call sequences | **Complete** |
| 4 | F.2 | Define `READ_TOOL_SCHEMA` and `GLOB_TOOL_SCHEMA` in OpenAI function-calling format | **Complete** |
| 5 | F.2 | Wire schemas through `build_openai_backend(tools=...)` in config.py | **Complete** |
| 6 | F.3 | Write `test_transport_tool_executor.py` — sandbox, budgets, slicing, errors | **Complete** |
| 7 | F.3 | Write `test_transport_tool_loop.py` — round-trip, errors, limits, no-writes | **Complete** |
| 8 | F.3 | Write `test_transport_openai_compatible.py` — payload, parsing, errors | **Complete** |
| 9 | F.4 | Declare `tool_calling` in `ProviderCapabilities` and all registry entries | **Complete** |
| 10 | F.4 | Integrate capability check in skill runtime TAPM dispatch path | **Pending** — requires skill runtime wiring |
| 11 | — | End-to-end integration test: TAPM skill via `run_tool_loop()` with `FakeBackend` producing a valid artifact | **Pending** — requires skill runtime integration |
| 12 | — | End-to-end integration test: TAPM skill via `OpenAICompatBackend` against live provider | **Pending** — requires live provider access |

---

## What Does NOT Change

- DAG scheduler, 5-step node dispatch contract, stall detection
- Gate evaluator, 102 deterministic predicates, HARD_BLOCK propagation
- Agent runtime, agent sequencing, context passing
- SkillResult / AgentResult / NodeExecutionResult contracts
- Artifact schema validation, atomic writes
- Constitutional authority hierarchy (CLAUDE.md §3)
- Call slicer (Step 0) and dependency normalizer
- Claude CLI transport (`runner/claude_transport.py`)
- All existing tests targeting `invoke_claude_text` (transport-agnostic mocks)

---

*Implementation brief complete. Tracks F.1–F.3 implemented and tested. Track F.4 capability declarations implemented; skill runtime integration pending. Ready for integration engineering.*
