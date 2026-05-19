# Internal LLM Backend Migration Plan
## From Claude CLI Transport to Backend-Agnostic Internal LLM Architecture

**Version:** 1.0
**Date:** 2026-05-18
**Status:** STRATEGIC PLAN — NOT YET IMPLEMENTED
**Scope:** Transport layer refactoring, TAPM compatibility, remote GPU deployment, Ollama pilot
**Constitutional authority:** CLAUDE.md (this plan is subordinate; implementation must comply)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current-State Architecture Analysis](#2-current-state-architecture-analysis)
3. [Target-State Architecture](#3-target-state-architecture)
4. [A — Transport Layer Refactoring](#4-a--transport-layer-refactoring)
5. [B — TAPM Compatibility](#5-b--tapm-compatibility)
6. [C — Remote GPU Server Blueprint](#6-c--remote-gpu-server-blueprint)
7. [D — Ollama Pilot Strategy](#7-d--ollama-pilot-strategy)
8. [E — Security & Governance](#8-e--security--governance)
9. [F — Validation Strategy](#9-f--validation-strategy)
10. [Migration Phases](#10-migration-phases)
11. [Risk Analysis](#11-risk-analysis)
12. [Recommended Implementation Order](#12-recommended-implementation-order)
13. [Recommended First Pilot Milestone](#13-recommended-first-pilot-milestone)

---

## 1. Executive Summary

This plan defines the migration of the Proposal Orchestrator from its current Claude CLI transport architecture (`runner/claude_transport.py` → `claude -p`) to a backend-agnostic internal LLM transport architecture capable of operating in a closed-network, zero-data-egress environment.

**Primary objectives:**

1. Replace the Claude CLI transport with an abstracted transport layer supporting multiple backends (Ollama, vLLM, TGI, Claude CLI as fallback).
2. Preserve the three-layer execution model: DAGScheduler → agent runtime → skill runtime.
3. Preserve TAPM semantics with local tool emulation replacing Claude Code's Read/Glob tools.
4. Deploy on an internal GPU server accessible only through VPN/internal network.
5. Enable IP-sensitive Horizon Europe proposal development with no data egress.

**What does NOT change:**

- The DAG scheduler, gate evaluator, and all 102 deterministic predicates
- The 5-step node dispatch contract
- Artifact schema validation, atomic writes, and SkillResult/AgentResult/NodeExecutionResult contracts
- The constitutional authority hierarchy (CLAUDE.md governs)
- Gate semantics, HARD_BLOCK propagation, and fail-closed behaviour
- The call slicer (Step 0) and dependency normalizer (Phase B+)
- All pure-Python preprocessing and validation layers

**What changes:**

- `runner/claude_transport.py` becomes a thin adapter delegating to a pluggable backend
- TAPM tool execution (Read/Glob) moves from Claude Code's built-in tools to a local tool executor
- The `claude` CLI dependency is replaced by HTTP API calls to an internal LLM endpoint
- Semantic predicate dispatch (`runner/semantic_dispatch.py`) routes through the same abstracted transport

**Migration surface analysis:**

| Module | Transport coupling | Change required |
|--------|-------------------|----------------|
| `claude_transport.py` | **Direct** — subprocess.run(["claude",...]) | Replace with backend abstraction |
| `skill_runtime.py` | Indirect — calls `invoke_claude_text()` | No change to calling code; tool loop addition for TAPM |
| `semantic_dispatch.py` | Indirect — calls `invoke_claude_text()` | No change to calling code |
| `agent_runtime.py` | None — calls `run_skill()` | No change |
| `dag_scheduler.py` | None — calls `run_agent()` + `evaluate_gate()` | No change |
| `gate_evaluator.py` | None — calls deterministic predicates + `dispatch_semantic_predicate()` | No change |
| `runtime_models.py` | None — data contracts only | No change |
| `call_slicer.py` | None — pure Python | No change |
| `dependency_normalizer.py` | None — pure Python | No change |

Only **two files** have direct transport coupling. The migration is surgically scoped.

---

## 2. Current-State Architecture Analysis

### 2.1 Transport Layer (`runner/claude_transport.py`)

The current transport is a single function — `invoke_claude_text()` — that:

1. Builds a CLI command: `["claude", "-p", "--model", model]`
2. Optionally appends `--tools Read,Glob` for TAPM mode
3. Passes the system prompt via `--system-prompt` flag (or embeds in user prompt when >24KB)
4. Pipes the user prompt via stdin to `subprocess.run()`
5. Returns raw stdout text
6. Raises typed exceptions: `ClaudeCLIUnavailableError`, `ClaudeCLITimeoutError`, `ClaudeTransportError`

**Key interface contract:**
```python
def invoke_claude_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    timeout_seconds: int = 300,
    tools: list[str] | None = None,
) -> str:
```

**Constants:**
- `DEFAULT_TIMEOUT_SECONDS = 300` (5 min for cli-prompt skills)
- `TAPM_TIMEOUT_SECONDS = 1200` (20 min for TAPM skills, in skill_runtime.py)
- `_MAX_SYSTEM_PROMPT_CLI_LENGTH = 24000` (Windows CreateProcess limit)

### 2.2 Execution Modes

**cli-prompt mode** (10 skills): All inputs serialized into prompt, piped to `claude -p`. No tools. Response is raw text containing JSON.

**TAPM mode** (12+ skills): Bounded prompt (~5-30KB) with declared input paths. Invoked with `--tools "Read,Glob"`. Claude reads files from disk during execution. Response is raw text containing JSON.

### 2.3 Skill Runtime Integration Points

`skill_runtime.py` calls `invoke_claude_text()` in two places:

1. **TAPM path** (line ~1198): `invoke_claude_text(..., tools=["Read", "Glob"], timeout_seconds=TAPM_TIMEOUT_SECONDS)`
2. **cli-prompt path** (line ~1281): `invoke_claude_text(...)`  (no tools, default timeout)

`semantic_dispatch.py` calls `invoke_claude_text()` in one place:

3. **Semantic predicate dispatch** (line ~646): `invoke_claude_text(system_prompt=..., user_prompt=..., model=AGENT_MODEL, max_tokens=AGENT_MAX_TOKENS)`

These are the **only three call sites** in the entire codebase. All other modules are transport-agnostic.

### 2.4 Tool Behaviour in TAPM

When Claude is invoked with `--tools "Read,Glob"`, Claude Code's internal tool loop handles file reads transparently. The orchestrator sees only the final text response. Claude's Read/Glob tool calls are invisible to the Python runtime — they happen within the `claude -p` process. The Python runtime has **no visibility into or control over** which files Claude reads during a TAPM invocation. Enforcement is prompt-based only (declared input boundary instructions).

### 2.5 Response Processing Pipeline

All three call sites feed responses into the same downstream pipeline:
1. `_extract_json_response()` — extracts JSON from raw text (handles bare JSON, markdown fences, mixed prose)
2. `_validate_skill_output()` — validates schema conformance, run_id, schema_id
3. `_atomic_write()` — writes atomically to canonical path

This pipeline is completely transport-agnostic and requires no modification.

---

## 3. Target-State Architecture

### 3.1 Architecture Overview

```
UNCHANGED LAYERS (no modification):
  DAGScheduler._dispatch_node()
    1. set state "running"
    2. evaluate_gate(entry_gate)       [gate_evaluator.py — unchanged]
    3. run_agent(agent_id, ...)        [agent_runtime.py — unchanged]
       → run_skill(skill_id, ...)      [skill_runtime.py — tool loop added]
    4. evaluate_gate(exit_gate)        [gate_evaluator.py — unchanged]
    5. return NodeExecutionResult      [runtime_models.py — unchanged]

MODIFIED LAYERS:
  runner/transport/                    [NEW — backend abstraction package]
    __init__.py                        # TransportBackend protocol, get_transport()
    base.py                            # TransportBackend abstract class
    claude_cli.py                      # ClaudeCLITransport (current behaviour)
    openai_compatible.py               # OpenAICompatibleTransport (Ollama, vLLM, TGI)
    config.py                          # Backend selection, endpoint configuration
    tool_executor.py                   # Local Read/Glob tool emulation for TAPM

  runner/claude_transport.py           [MODIFIED — thin adapter delegating to transport/]
    invoke_claude_text()               # Preserved interface, delegates to active backend

  runner/skill_runtime.py              [MODIFIED — TAPM tool loop added]
    _invoke_tapm_with_tools()          # New: iterative tool-call loop for non-Claude backends
```

### 3.2 Backend Selection

```
runner/transport/config.py

TRANSPORT_BACKEND = env("ORCHESTRATOR_TRANSPORT_BACKEND", default="claude_cli")
# Valid values: "claude_cli", "ollama", "openai_compatible"

TRANSPORT_ENDPOINT = env("ORCHESTRATOR_TRANSPORT_ENDPOINT", default=None)
# Required for ollama/openai_compatible: "https://gpu-server.internal:8443/v1"

TRANSPORT_MODEL = env("ORCHESTRATOR_TRANSPORT_MODEL", default=None)
# Override model per backend: "qwen3:32b", "llama3.3:70b", etc.

TRANSPORT_API_KEY = env("ORCHESTRATOR_TRANSPORT_API_KEY", default=None)
# Optional: for authenticated endpoints

TRANSPORT_TLS_CERT = env("ORCHESTRATOR_TRANSPORT_TLS_CERT", default=None)
# Optional: client certificate for mTLS
```

### 3.3 Preserved Invariants

These invariants are constitutionally mandated and must survive the migration:

1. **Artifact write authority**: Python runtime controls all writes. No LLM backend has write access.
2. **Validation authority**: `_validate_skill_output()` validates all responses. No silent repair.
3. **Scheduling authority**: DAG dispatch, gate evaluation, state transitions remain in Python.
4. **Fail-closed semantics**: Transport failures produce `SkillResult(status="failure")`, never fabricated completion.
5. **Budget gate integrity**: Phase 7 gate cannot be bypassed. Phase 8 blocked until gate_09 passes.
6. **No fabrication**: LLM responses are validated against schemas; ungrounded claims are constitutional violations.
7. **Gate evaluation is scheduler-only**: No agent, skill, or transport layer evaluates gates.

---

## 4. A — Transport Layer Refactoring

### 4.1 Backend Abstraction Strategy

**Principle:** The existing `invoke_claude_text()` function signature is preserved as the public API. All consumers (`skill_runtime.py`, `semantic_dispatch.py`) continue calling it unchanged. The function body delegates to the active transport backend.

```python
# runner/transport/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class TransportResponse:
    """Normalized response from any backend."""
    text: str                           # Raw response text
    finish_reason: str | None = None    # "stop", "length", "tool_calls", etc.
    tool_calls: list[dict] | None = None  # Pending tool calls (for tool loop)
    usage: dict | None = None           # Token usage metadata (optional)

class TransportBackend(ABC):
    """Abstract transport backend protocol."""

    @abstractmethod
    def invoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        timeout_seconds: int,
        tools: list[dict] | None = None,    # Tool schemas (not names)
        messages: list[dict] | None = None,  # For multi-turn tool loops
    ) -> TransportResponse:
        """Send a prompt to the LLM and return the response."""
        ...

    @abstractmethod
    def supports_native_tools(self) -> bool:
        """Whether this backend handles tool calls internally (e.g. Claude CLI)."""
        ...

    @property
    @abstractmethod
    def backend_id(self) -> str:
        """Identifier string for logging and diagnostics."""
        ...
```

### 4.2 ClaudeCLITransport (Existing Behaviour)

```python
# runner/transport/claude_cli.py

class ClaudeCLITransport(TransportBackend):
    """Wraps the existing claude -p CLI invocation."""

    def invoke(self, *, system_prompt, user_prompt, model, max_tokens,
               timeout_seconds, tools=None, messages=None) -> TransportResponse:
        # Existing subprocess.run(["claude", "-p", ...]) logic
        # tools parameter → --tools "Read,Glob" (Claude handles tool loop internally)
        # Returns TransportResponse(text=stdout)
        ...

    def supports_native_tools(self) -> bool:
        return True  # Claude CLI handles Read/Glob internally

    @property
    def backend_id(self) -> str:
        return "claude_cli"
```

Key: When `supports_native_tools()` returns `True`, the skill runtime skips the local tool loop and sends a single request. Claude handles tools internally. This preserves exact current TAPM behaviour.

### 4.3 OpenAICompatibleTransport (Ollama, vLLM, TGI)

```python
# runner/transport/openai_compatible.py

import httpx  # or requests

class OpenAICompatibleTransport(TransportBackend):
    """OpenAI-compatible /v1/chat/completions endpoint.

    Works with:
    - Ollama (native OpenAI compatibility)
    - vLLM (--served-model-name, OpenAI-compatible API)
    - TGI (Messages API with OpenAI-compatible tool use)
    """

    def __init__(
        self,
        *,
        base_url: str,           # e.g. "https://gpu-server.internal:8443/v1"
        api_key: str | None = None,
        tls_cert: str | None = None,
        tls_verify: bool | str = True,
        default_model: str | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=10.0, read=None, write=30.0, pool=30.0),
            verify=tls_verify if tls_cert is None else tls_cert,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )
        self._default_model = default_model

    def invoke(self, *, system_prompt, user_prompt, model, max_tokens,
               timeout_seconds, tools=None, messages=None) -> TransportResponse:
        effective_model = self._default_model or model

        if messages is None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

        payload = {
            "model": effective_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.0,    # Deterministic for reproducibility
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = self._client.post(
                "/chat/completions",
                json=payload,
                timeout=timeout_seconds,
            )
            resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ClaudeCLITimeoutError(
                f"LLM endpoint timed out after {timeout_seconds}s",
                timeout_seconds=timeout_seconds,
            )
        except httpx.HTTPStatusError as exc:
            raise ClaudeTransportError(
                f"LLM endpoint returned {exc.response.status_code}: "
                f"{exc.response.text[:500]}"
            )
        except httpx.RequestError as exc:
            raise ClaudeTransportError(
                f"LLM endpoint connection failed: {exc}"
            )

        data = resp.json()
        choice = data["choices"][0]
        message = choice["message"]

        tool_calls_raw = message.get("tool_calls")
        parsed_tool_calls = None
        if tool_calls_raw:
            parsed_tool_calls = [
                {
                    "id": tc["id"],
                    "type": tc["type"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                }
                for tc in tool_calls_raw
            ]

        return TransportResponse(
            text=message.get("content") or "",
            finish_reason=choice.get("finish_reason"),
            tool_calls=parsed_tool_calls,
            usage=data.get("usage"),
        )

    def supports_native_tools(self) -> bool:
        return False  # Local tool loop required

    @property
    def backend_id(self) -> str:
        return "openai_compatible"
```

### 4.4 OllamaTransport (Convenience Wrapper)

```python
# runner/transport/ollama.py

class OllamaTransport(OpenAICompatibleTransport):
    """Convenience subclass for direct Ollama deployments.

    Pre-configures base_url for Ollama's default endpoint and sets
    Ollama-specific defaults.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434/v1",
        default_model: str = "qwen3:32b",
        **kwargs,
    ):
        super().__init__(
            base_url=base_url,
            default_model=default_model,
            **kwargs,
        )

    @property
    def backend_id(self) -> str:
        return "ollama"
```

### 4.5 Backend Selection Mechanism

```python
# runner/transport/config.py

import os
from runner.transport.base import TransportBackend

def get_transport() -> TransportBackend:
    """Factory: return the configured transport backend.

    Selection order:
    1. ORCHESTRATOR_TRANSPORT_BACKEND env var
    2. Default: "claude_cli" (preserves current behaviour)
    """
    backend = os.environ.get("ORCHESTRATOR_TRANSPORT_BACKEND", "claude_cli")

    if backend == "claude_cli":
        from runner.transport.claude_cli import ClaudeCLITransport
        return ClaudeCLITransport()

    elif backend == "ollama":
        from runner.transport.ollama import OllamaTransport
        endpoint = os.environ.get(
            "ORCHESTRATOR_TRANSPORT_ENDPOINT",
            "http://localhost:11434/v1"
        )
        model = os.environ.get("ORCHESTRATOR_TRANSPORT_MODEL", "qwen3:32b")
        return OllamaTransport(base_url=endpoint, default_model=model)

    elif backend == "openai_compatible":
        from runner.transport.openai_compatible import OpenAICompatibleTransport
        endpoint = os.environ.get("ORCHESTRATOR_TRANSPORT_ENDPOINT")
        if not endpoint:
            raise ValueError(
                "ORCHESTRATOR_TRANSPORT_ENDPOINT required for openai_compatible backend"
            )
        model = os.environ.get("ORCHESTRATOR_TRANSPORT_MODEL")
        api_key = os.environ.get("ORCHESTRATOR_TRANSPORT_API_KEY")
        tls_cert = os.environ.get("ORCHESTRATOR_TRANSPORT_TLS_CERT")
        return OpenAICompatibleTransport(
            base_url=endpoint,
            default_model=model,
            api_key=api_key,
            tls_cert=tls_cert,
        )

    else:
        raise ValueError(f"Unknown transport backend: {backend!r}")
```

### 4.6 Adapter Bridge (`claude_transport.py` Modification)

The existing `invoke_claude_text()` function is preserved with identical signature. The body delegates to the active backend:

```python
# runner/claude_transport.py (modified)

from runner.transport.config import get_transport

_transport_cache: TransportBackend | None = None

def _get_cached_transport() -> TransportBackend:
    global _transport_cache
    if _transport_cache is None:
        _transport_cache = get_transport()
    return _transport_cache

def invoke_claude_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    tools: list[str] | None = None,
) -> str:
    backend = _get_cached_transport()

    if backend.supports_native_tools():
        # Claude CLI: pass tool names directly; Claude handles tool loop
        response = backend.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            tools=tools,  # Tool names for CLI --tools flag
        )
        if not response.text or not response.text.strip():
            raise ClaudeTransportError("Backend returned empty output")
        return response.text

    else:
        # Non-Claude backend: convert tool names to OpenAI tool schemas
        # and run tool loop locally
        from runner.transport.tool_executor import run_tool_loop

        if tools:
            tool_schemas = _build_tool_schemas(tools)
            result = run_tool_loop(
                backend=backend,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
                tool_schemas=tool_schemas,
            )
        else:
            response = backend.invoke(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            )
            result = response.text

        if not result or not result.strip():
            raise ClaudeTransportError("Backend returned empty output")
        return result
```

### 4.7 Failure Semantics

The existing exception hierarchy is preserved:

| Exception | When raised | Preserved? |
|-----------|------------|------------|
| `ClaudeCLIUnavailableError` | Backend endpoint unreachable | Yes — renamed semantics to "transport unavailable" |
| `ClaudeCLITimeoutError` | Request exceeds timeout | Yes |
| `ClaudeTransportError` | Non-zero status, empty output, other | Yes |

All downstream error handling in `skill_runtime.py` and `semantic_dispatch.py` catches these exact types. The exception class names may be aliased for clarity but the types themselves remain backward-compatible:

```python
# Backward-compatible aliases
TransportUnavailableError = ClaudeCLIUnavailableError
TransportTimeoutError = ClaudeCLITimeoutError
TransportError = ClaudeTransportError
```

### 4.8 Compatibility Constraints

| Constraint | Enforcement |
|-----------|-------------|
| `invoke_claude_text()` signature unchanged | All three call sites unmodified |
| Exception types unchanged | All catch blocks unmodified |
| Response is raw text (str) | All backends return `response.text` |
| TAPM tool behaviour preserved for Claude CLI | `supports_native_tools() == True` bypasses local tool loop |
| Non-Claude backends use local tool loop | `supports_native_tools() == False` triggers tool executor |
| `temperature=0.0` for reproducibility | Set in OpenAICompatibleTransport payload |
| No silent retry | Transport returns/raises on first attempt |

### 4.9 Gate/Runtime Authority Separation

The refactoring preserves the constitutional authority separation:

- **Gate evaluator** (`gate_evaluator.py`) calls `dispatch_semantic_predicate()` for semantic predicates. The semantic dispatch calls `invoke_claude_text()`. The transport layer has no knowledge of gate logic.
- **Skill runtime** (`skill_runtime.py`) calls `invoke_claude_text()`. The transport layer has no knowledge of artifact schemas, writes, or validation.
- **Agent runtime** (`agent_runtime.py`) calls `run_skill()`. It never touches the transport layer.
- **Scheduler** (`dag_scheduler.py`) calls `run_agent()` and `evaluate_gate()`. It never touches the transport layer.

No transport backend implementation may invoke gates, write artifacts, or modify scheduler state.

---

## 5. B — TAPM Compatibility

### 5.1 The Problem

TAPM currently relies on Claude Code's built-in Read and Glob tools. When `claude -p --tools "Read,Glob"` is invoked, Claude Code's internal tool loop handles file access transparently. The orchestrator receives only the final text response.

Non-Claude backends (Ollama, vLLM, TGI) expose an OpenAI-compatible API. They support tool use via the standard `tools` parameter in `/v1/chat/completions`, but:

1. **No built-in Read/Glob tools exist.** Tools must be defined and executed locally.
2. **The tool loop must be external.** The orchestrator must handle the request → tool_calls → tool_results → request cycle.
3. **File access must be sandboxed.** Claude Code's Read tool has OS-level access; local emulation must enforce boundaries.

### 5.2 Local Tool Schemas

```python
# runner/transport/tool_executor.py

READ_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "Read",
        "description": (
            "Read a file from the local filesystem. Returns file content as text. "
            "For JSON files, returns the raw JSON text. "
            "The file_path must be an absolute path."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-based). Optional.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of lines to read. Optional.",
                },
            },
            "required": ["file_path"],
        },
    },
}

GLOB_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "Glob",
        "description": (
            "Find files matching a glob pattern in a directory. "
            "Returns a list of matching file paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g. '**/*.json')",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in. Must be an absolute path.",
                },
            },
            "required": ["pattern"],
        },
    },
}
```

### 5.3 Local Tool Execution Model

```python
# runner/transport/tool_executor.py

import json
import glob as glob_module
from pathlib import Path

# Security constants
MAX_TOOL_ROUNDS = 25          # Maximum tool call rounds per invocation
MAX_FILE_READ_BYTES = 512_000  # 500KB per file read
MAX_TOTAL_READ_BYTES = 5_000_000  # 5MB total across all reads in one invocation
MAX_GLOB_RESULTS = 200        # Maximum glob matches returned

class ToolSandboxViolation(Exception):
    """Raised when a tool call violates sandbox boundaries."""

class ToolExecutor:
    """Executes Read and Glob tool calls within a sandboxed repository boundary."""

    def __init__(self, repo_root: Path, allowed_prefixes: list[str] | None = None):
        self._repo_root = repo_root.resolve()
        self._total_bytes_read = 0
        self._files_read: list[str] = []

        # Allowed path prefixes (repo-relative). If None, all repo paths allowed.
        # For TAPM: set to the skill's declared reads_from paths.
        self._allowed_prefixes = allowed_prefixes

    def execute_tool_call(self, tool_name: str, arguments: dict) -> str:
        """Execute a single tool call and return the result as a string."""
        if tool_name == "Read":
            return self._execute_read(arguments)
        elif tool_name == "Glob":
            return self._execute_glob(arguments)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def _execute_read(self, arguments: dict) -> str:
        file_path_str = arguments.get("file_path", "")
        offset = arguments.get("offset")
        limit = arguments.get("limit")

        # Resolve and validate path
        try:
            file_path = Path(file_path_str).resolve()
        except (ValueError, OSError):
            return json.dumps({"error": f"Invalid path: {file_path_str}"})

        # Sandbox check: must be within repo_root
        if not self._is_within_sandbox(file_path):
            return json.dumps({
                "error": f"Access denied: path is outside the repository boundary"
            })

        # Declared-input enforcement (when allowed_prefixes is set)
        if self._allowed_prefixes is not None:
            if not self._is_in_allowed_prefixes(file_path):
                return json.dumps({
                    "error": (
                        "Access denied: path is not in the declared inputs. "
                        "Read only files listed in the Declared Inputs section."
                    )
                })

        if not file_path.is_file():
            return json.dumps({"error": f"File not found: {file_path_str}"})

        # Size guard
        try:
            file_size = file_path.stat().st_size
        except OSError:
            return json.dumps({"error": f"Cannot stat file: {file_path_str}"})

        if file_size > MAX_FILE_READ_BYTES:
            return json.dumps({
                "error": f"File too large ({file_size} bytes, limit {MAX_FILE_READ_BYTES})"
            })

        if self._total_bytes_read + file_size > MAX_TOTAL_READ_BYTES:
            return json.dumps({
                "error": f"Total read budget exceeded ({MAX_TOTAL_READ_BYTES} bytes)"
            })

        # Read the file
        try:
            content = file_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            return json.dumps({"error": f"Cannot read file: {exc}"})

        self._total_bytes_read += len(content.encode("utf-8"))
        self._files_read.append(str(file_path))

        # Apply offset/limit (line-based, matching Claude Code Read behaviour)
        if offset is not None or limit is not None:
            lines = content.splitlines(keepends=True)
            start = (offset - 1) if offset and offset > 0 else 0
            end = (start + limit) if limit else None
            content = "".join(lines[start:end])

        return content

    def _execute_glob(self, arguments: dict) -> str:
        pattern = arguments.get("pattern", "")
        search_path = arguments.get("path")

        if search_path:
            try:
                base = Path(search_path).resolve()
            except (ValueError, OSError):
                return json.dumps({"error": f"Invalid path: {search_path}"})
        else:
            base = self._repo_root

        # Sandbox check
        if not self._is_within_sandbox(base):
            return json.dumps({
                "error": "Access denied: search path is outside the repository boundary"
            })

        # Execute glob
        try:
            full_pattern = str(base / pattern)
            matches = sorted(glob_module.glob(full_pattern, recursive=True))
        except (OSError, ValueError) as exc:
            return json.dumps({"error": f"Glob failed: {exc}"})

        # Limit results
        matches = matches[:MAX_GLOB_RESULTS]

        return "\n".join(matches) if matches else "(no matches)"

    def _is_within_sandbox(self, path: Path) -> bool:
        """Check that path is within repo_root."""
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self._repo_root))
        except (ValueError, OSError):
            return False

    def _is_in_allowed_prefixes(self, path: Path) -> bool:
        """Check that path falls within declared reads_from prefixes."""
        resolved = path.resolve()
        rel_path = str(resolved.relative_to(self._repo_root)).replace("\\", "/")
        for prefix in self._allowed_prefixes:
            norm_prefix = prefix.replace("\\", "/").rstrip("/")
            if rel_path == norm_prefix or rel_path.startswith(norm_prefix + "/"):
                return True
            # Also check if the prefix is a direct file match
            if rel_path == norm_prefix:
                return True
        return False

    @property
    def files_read(self) -> list[str]:
        """Return list of files read during this execution (for audit logging)."""
        return list(self._files_read)
```

### 5.4 Tool Loop Architecture

```python
# runner/transport/tool_executor.py (continued)

def run_tool_loop(
    *,
    backend: TransportBackend,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    timeout_seconds: int,
    tool_schemas: list[dict],
    repo_root: Path | None = None,
    allowed_prefixes: list[str] | None = None,
) -> str:
    """Execute an LLM invocation with iterative tool call resolution.

    Implements the tool call loop for backends that don't handle tools
    internally (i.e., supports_native_tools() == False).

    The loop:
    1. Send initial request with tool schemas
    2. If response contains tool_calls → execute locally → append results → re-send
    3. Repeat until response has no tool_calls or MAX_TOOL_ROUNDS reached
    4. Return final text response

    Returns the final text content from the LLM.
    """
    from runner.paths import find_repo_root
    if repo_root is None:
        repo_root = find_repo_root()

    executor = ToolExecutor(repo_root, allowed_prefixes=allowed_prefixes)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    deadline = time.monotonic() + timeout_seconds

    for round_num in range(MAX_TOOL_ROUNDS):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ClaudeCLITimeoutError(
                f"Tool loop timed out after {timeout_seconds}s "
                f"({round_num} rounds completed)",
                timeout_seconds=timeout_seconds,
            )

        response = backend.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            timeout_seconds=int(remaining),
            tools=tool_schemas,
            messages=messages,
        )

        # If no tool calls, we have the final response
        if not response.tool_calls:
            return response.text

        # Process tool calls
        # Append assistant message with tool_calls to conversation
        assistant_msg = {"role": "assistant", "content": response.text or ""}
        assistant_msg["tool_calls"] = response.tool_calls
        messages.append(assistant_msg)

        # Execute each tool call and append results
        for tc in response.tool_calls:
            func_name = tc["function"]["name"]
            try:
                func_args = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, TypeError):
                func_args = {}

            tool_result = executor.execute_tool_call(func_name, func_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            })

    # Exhausted rounds — make one final call without tools to force text response
    response = backend.invoke(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        max_tokens=max_tokens,
        timeout_seconds=max(int(deadline - time.monotonic()), 30),
        messages=messages,
    )
    return response.text
```

### 5.5 Declared-Input Enforcement

For TAPM invocations, the skill runtime passes `allowed_prefixes` derived from the skill catalog's `reads_from` field:

```python
# In skill_runtime.py, TAPM path modification:

if not backend.supports_native_tools():
    from runner.transport.tool_executor import run_tool_loop
    response_text = run_tool_loop(
        backend=backend,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=SKILL_MODEL,
        max_tokens=SKILL_MAX_TOKENS,
        timeout_seconds=TAPM_TIMEOUT_SECONDS,
        tool_schemas=[READ_TOOL_SCHEMA, GLOB_TOOL_SCHEMA],
        repo_root=repo_root,
        allowed_prefixes=reads_from + (optional_reads_from or []),
    )
```

This provides **hard enforcement** of the declared-input boundary — a stronger guarantee than Claude CLI's prompt-based enforcement (CLAUDE.md §2.5 compliance improvement).

### 5.6 Security Boundaries

| Boundary | Enforcement mechanism |
|----------|---------------------|
| Repository root sandbox | `ToolExecutor._is_within_sandbox()` — resolved path must start with `repo_root` |
| Declared-input boundary | `ToolExecutor._is_in_allowed_prefixes()` — path must match `reads_from` |
| Per-file size limit | `MAX_FILE_READ_BYTES = 512KB` per read |
| Total read budget | `MAX_TOTAL_READ_BYTES = 5MB` per invocation |
| Glob result limit | `MAX_GLOB_RESULTS = 200` |
| Tool round limit | `MAX_TOOL_ROUNDS = 25` |
| No Write/Edit tools | Tool schemas only define Read and Glob |
| No Bash tool | Not in schema; cannot be invoked |
| Timeout enforcement | `deadline` checked each round; `ClaudeCLITimeoutError` raised |

### 5.7 Prevention of Unrestricted Repository Traversal

The local tool executor enforces three layers of containment:

1. **Schema layer:** Only Read and Glob tool schemas are provided to the LLM. Write, Edit, Bash, and all other tools are structurally unavailable.

2. **Sandbox layer:** All paths are resolved to absolute paths and checked against `repo_root`. Symlink traversal is blocked by `.resolve()`. Parent directory escapes (`../`) are resolved and rejected if they leave the sandbox.

3. **Declared-input layer:** When `allowed_prefixes` is set (always for TAPM skills), only paths matching the skill's `reads_from` declaration are accessible. This is strictly stronger than Claude CLI's prompt-based enforcement.

**Improvement over current architecture:** The current Claude CLI TAPM mode has no hard file-access enforcement — Claude Code can read any file, constrained only by prompt instructions. The local tool executor provides deterministic path validation that cannot be bypassed by prompt injection or model behaviour.

---

## 6. C — Remote GPU Server Blueprint

### 6.1 Network Topology

```
┌──────────────────────────────────────────────────────────┐
│  INTERNAL NETWORK (university/institution VPN)           │
│                                                          │
│  ┌─────────────────────┐     ┌────────────────────────┐  │
│  │  ORCHESTRATOR HOST   │     │  GPU SERVER             │  │
│  │  (user workstation)  │     │  (inference endpoint)   │  │
│  │                      │     │                         │  │
│  │  ┌────────────────┐  │     │  ┌──────────────────┐   │  │
│  │  │ Python runtime  │  │     │  │ Reverse proxy    │   │  │
│  │  │ DAG scheduler   │──┼─────┼─▶│ (nginx/caddy)    │   │  │
│  │  │ skill_runtime   │  │     │  │ :8443 (mTLS)     │   │  │
│  │  │ transport layer │  │     │  └────────┬─────────┘   │  │
│  │  └────────────────┘  │     │           │              │  │
│  │                      │     │  ┌────────▼─────────┐   │  │
│  │  ┌────────────────┐  │     │  │ Ollama / vLLM    │   │  │
│  │  │ docs/ (tiers)   │  │     │  │ :11434 (local)   │   │  │
│  │  │ .claude/        │  │     │  │ Model weights    │   │  │
│  │  │ runner/         │  │     │  │ GPU(s)           │   │  │
│  │  └────────────────┘  │     │  └──────────────────┘   │  │
│  └─────────────────────┘     └────────────────────────┘  │
│                                                          │
│  ┌─────────────────────┐                                 │
│  │  DNS / VPN Gateway   │  ← Only internal resolution    │
│  │  No outbound internet│  ← GPU server has NO egress    │
│  └─────────────────────┘                                 │
└──────────────────────────────────────────────────────────┘
```

### 6.2 Component Distribution

| Component | Runs on | Notes |
|-----------|---------|-------|
| Python runtime (runner/) | Orchestrator host | User workstation or CI server |
| docs/ tier hierarchy | Orchestrator host | Source truth, never leaves host |
| .claude/ workflows | Orchestrator host | Specs only, never sent to GPU server |
| Reverse proxy (nginx) | GPU server | TLS termination, auth, rate limiting |
| Ollama / vLLM / TGI | GPU server | Inference only; no file access to orchestrator |
| Model weights | GPU server | Downloaded once, stored locally |
| Prompt/response logs | GPU server | Retained per policy, encrypted at rest |

### 6.3 Communication Paths

| Path | Protocol | Direction | Content |
|------|----------|-----------|---------|
| Orchestrator → GPU server | HTTPS (mTLS) | Request | JSON: system_prompt, user_prompt, model, tools |
| GPU server → Orchestrator | HTTPS (mTLS) | Response | JSON: content, tool_calls, usage |

**No other communication paths are permitted:**
- GPU server has no access to the orchestrator's filesystem
- GPU server has no outbound internet access
- GPU server does not initiate connections to the orchestrator
- No file transfer protocol between hosts
- No shared filesystem mount

### 6.4 VPN/Internal Network Requirements

- All hosts on the same VPN or institutional LAN
- GPU server hostname resolves only within internal DNS (e.g., `gpu-inference.internal`)
- VPN must support TLS 1.3 transit encryption
- Split-tunnel VPN acceptable if GPU server subnet is always routed through VPN

### 6.5 API Gateway / Reverse Proxy Layer

**nginx configuration (production):**

```nginx
server {
    listen 8443 ssl;
    server_name gpu-inference.internal;

    # mTLS
    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;
    ssl_client_certificate /etc/nginx/certs/ca.crt;
    ssl_verify_client on;

    # TLS hardening
    ssl_protocols TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=llm:10m rate=10r/s;

    # Request size limit (prompts can be large)
    client_max_body_size 2m;

    # Timeouts (TAPM skills may take 20 min)
    proxy_read_timeout 1200s;
    proxy_send_timeout 60s;
    proxy_connect_timeout 10s;

    location /v1/ {
        limit_req zone=llm burst=20 nodelay;

        # API token validation
        if ($http_authorization != "Bearer ${INTERNAL_API_TOKEN}") {
            return 401;
        }

        proxy_pass http://127.0.0.1:11434/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Request-ID $request_id;
        proxy_set_header X-Forwarded-For $remote_addr;

        # Response buffering for large outputs
        proxy_buffering on;
        proxy_buffer_size 16k;
        proxy_buffers 8 32k;
    }

    # Health check (unauthenticated)
    location /health {
        proxy_pass http://127.0.0.1:11434/api/tags;
    }
}
```

### 6.6 TLS/mTLS Strategy

| Level | Implementation |
|-------|---------------|
| Server TLS | Self-signed CA for internal use; institutional CA preferred if available |
| Client certificates (mTLS) | One client cert per orchestrator host; rotated annually |
| Certificate storage | Server: `/etc/nginx/certs/` on GPU server; Client: `~/.orchestrator/certs/` |
| Verification | Server verifies client cert against internal CA; client verifies server cert |

For the **Ollama pilot**, mTLS may be deferred in favour of API token + VPN-only access. mTLS is required for production.

### 6.7 API Token / Service Account Strategy

- One API token per project/deployment (not per user)
- Token stored in environment variable `ORCHESTRATOR_TRANSPORT_API_KEY`
- Token validated by nginx `$http_authorization` header check
- Token rotation: quarterly or on personnel change
- No token in repository; no token in committed configuration

### 6.8 Firewall Rules

**GPU server firewall (iptables/nftables):**

```
# Default: deny all
-P INPUT DROP
-P FORWARD DROP
-P OUTPUT DROP

# Allow established/related
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH from management subnet only
-A INPUT -s 10.0.0.0/24 -p tcp --dport 22 -j ACCEPT

# Allow HTTPS from internal network only
-A INPUT -s 10.0.0.0/16 -p tcp --dport 8443 -j ACCEPT

# Allow loopback
-A INPUT -i lo -j ACCEPT
-A OUTPUT -o lo -j ACCEPT

# BLOCK ALL OUTBOUND INTERNET — critical for IP protection
# No DNS resolution to external servers
# No HTTP/HTTPS to external endpoints
# No NTP to external servers (use internal NTP)
```

### 6.9 Endpoint Exposure Policy

- Port 8443 (HTTPS/mTLS): internal network only
- Port 11434 (Ollama): localhost only (127.0.0.1 bind)
- No port exposed to public internet
- No port forwarding through NAT/firewall to external networks

### 6.10 Storage Requirements

| Item | Size | Location |
|------|------|----------|
| Model weights (32B param, Q4) | ~20GB | `/opt/models/` |
| Model weights (70B param, Q4) | ~40GB | `/opt/models/` |
| Prompt/response logs (30 days) | ~2-5GB | `/var/log/llm/` |
| Docker images | ~5GB | `/var/lib/docker/` |
| OS + nginx | ~10GB | `/` |
| **Total disk** | **~80-100GB** | SSD recommended |
| **GPU VRAM** | **24-80GB** | Depends on model (see §7) |

### 6.11 Logging Policy

| Log type | Retention | Content | Storage |
|----------|-----------|---------|---------|
| Access logs (nginx) | 90 days | Timestamp, source IP, request size, response code, latency | `/var/log/nginx/` |
| Prompt/response logs | 30 days | Full request/response JSON (for debugging) | `/var/log/llm/` (encrypted at rest) |
| Error logs | 90 days | Stack traces, transport failures | `/var/log/llm/errors/` |
| Model load events | Indefinite | Model name, load timestamp, VRAM usage | `/var/log/llm/models/` |

### 6.12 Prompt/Output Retention Policy

- Prompt and response content is logged for debugging and audit purposes
- Logs are stored on the GPU server only (not transmitted)
- Logs are encrypted at rest using LUKS or dm-crypt
- Logs are rotated and purged after 30 days
- No prompt or response content is transmitted to any external service
- No telemetry, analytics, or usage reporting to external services

### 6.13 Outbound Internet Restrictions

**The GPU server MUST have no outbound internet access.** This is the primary data-egress prevention mechanism.

- No DNS resolution to external servers (use internal DNS only, or hosts file)
- No HTTP/HTTPS outbound to any external endpoint
- No NTP to external servers (use internal NTP server or GPS clock)
- Model weights are downloaded once via a bastion host and transferred via physical media or internal network
- Ollama pull / model updates are performed via offline model import

### 6.14 Monitoring

| Metric | Source | Alert threshold |
|--------|--------|----------------|
| GPU utilization | `nvidia-smi` / Prometheus exporter | < 5% for 10 min (model may have crashed) |
| VRAM usage | `nvidia-smi` | > 95% (OOM risk) |
| Inference latency (p95) | nginx access log | > 120s for cli-prompt, > 600s for TAPM |
| Request error rate | nginx error log | > 10% over 5 min |
| Disk usage | node_exporter | > 85% |
| Ollama process health | systemd / Docker healthcheck | Process not running |
| TLS certificate expiry | certbot / cron check | < 30 days |

### 6.15 Deployment Model

**Recommended: Docker Compose (pilot) → Kubernetes (production)**

```yaml
# docker-compose.yml (pilot deployment)
version: "3.8"
services:
  ollama:
    image: ollama/ollama:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - OLLAMA_HOST=127.0.0.1:11434
      - OLLAMA_KEEP_ALIVE=24h
    volumes:
      - ollama-models:/root/.ollama
      - /var/log/llm:/var/log/llm
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "8443:8443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - ollama
    restart: unless-stopped

volumes:
  ollama-models:
    driver: local
```

---

## 7. D — Ollama Pilot Strategy

### 7.1 Pilot Objectives

1. Validate the transport abstraction layer with a real non-Claude backend
2. Validate the local tool executor (Read/Glob emulation) with TAPM skills
3. Measure inference quality delta vs. Claude for orchestration tasks
4. Establish baseline latency and throughput numbers
5. Confirm closed-network operation with zero data egress

### 7.2 Recommended Initial Models

| Model | Parameters | VRAM (Q4) | Use case | Priority |
|-------|-----------|-----------|----------|----------|
| **Qwen3-32B** | 32B | ~20GB | Primary pilot model. Strong structured JSON output, tool use support, multilingual. Fits single A100-40GB or RTX 4090. | **First** |
| **Llama 3.3-70B** | 70B | ~40GB | Stronger reasoning. Requires A100-80GB or 2x RTX 4090. | Second |
| **Qwen3-8B** | 8B | ~6GB | Smoke-test model. Fits any GPU. Used for transport validation, not quality validation. | Smoke-test |
| **DeepSeek-R1-32B** | 32B | ~20GB | Strong reasoning, extended thinking. Alternative to Qwen3. | Alternative |

**Rationale for Qwen3-32B as primary:**
- Native tool/function calling support in Ollama (critical for TAPM tool loop)
- Strong JSON output adherence (critical for `_extract_json_response()`)
- 32B fits a single commodity GPU (RTX 4090 24GB with Q4 quantization)
- Multilingual capability (EU proposal context may include non-English references)
- Apache 2.0 license (no usage restrictions for institutional deployment)

### 7.3 Minimum GPU Requirements

| Tier | GPU | VRAM | Models supported | Recommended for |
|------|-----|------|-----------------|-----------------|
| **Pilot minimum** | 1x RTX 4090 | 24GB | Qwen3-32B (Q4), Qwen3-8B | Transport validation, pilot testing |
| **Pilot recommended** | 1x A100-40GB | 40GB | Qwen3-32B (Q5/Q6), Llama 3.3-70B (Q3) | Quality validation |
| **Production minimum** | 1x A100-80GB | 80GB | Llama 3.3-70B (Q5), Qwen3-32B (Q8) | Full orchestration runs |
| **Production recommended** | 2x A100-80GB | 160GB | Any model at full precision; concurrent requests | Parallel Phase 8 drafting |

### 7.4 Expected Performance Limitations

**Inference speed:**
- Ollama with Qwen3-32B on RTX 4090: ~20-40 tok/s (vs. Claude's ~100+ tok/s)
- For a skill producing ~2000 output tokens: ~50-100s (vs. ~20s on Claude)
- For TAPM skills with 5-10 Read tool rounds: each round adds ~5-10s of roundtrip
- Total TAPM skill execution: ~2-5 min (vs. ~30-60s on Claude)

**Quality:**
- Structured JSON adherence will be lower than Claude; `_extract_json_response()` fallback parsing becomes more important
- Schema compliance (run_id, schema_id fields) will require more explicit prompting
- Constitutional reasoning (semantic predicates) may be significantly weaker
- Impact on gate pass rates: semantic predicates may produce more false positives/negatives

**Context window:**
- Qwen3-32B: 128K context (sufficient for all current prompts)
- cli-prompt skills: largest prompt ~80KB (~20K tokens) — within limits
- TAPM skills: prompt ~5-30KB + tool results ~50-100KB — within limits

### 7.5 Pilot Scope

**Phase 1 (Weeks 1-2): Transport validation**
- Deploy Ollama with Qwen3-8B on any available GPU
- Validate `OpenAICompatibleTransport` end-to-end
- Validate tool loop with Read/Glob emulation
- Run against synthetic test fixtures (not real proposal data)
- Success criteria: all transport tests pass, tool loop completes

**Phase 2 (Weeks 3-4): Single-phase validation**
- Upgrade to Qwen3-32B
- Run Phase 1 (Call Analysis) end-to-end
- Compare output quality against Claude baseline artifacts
- Measure latency for all 4 Phase 1 skills
- Success criteria: Phase 1 gate passes; output quality is assessable

**Phase 3 (Weeks 5-8): Multi-phase validation**
- Run Phases 1-3 sequentially
- Validate TAPM tool loop with real Tier 2B/3 data
- Validate dependency normalizer + gantt builder (cli-prompt mode)
- Identify and document quality gaps
- Success criteria: Phases 1-3 gates pass; gaps documented

**Phase 4 (Weeks 9-12): Full pipeline validation**
- Run Phases 1-7 (excluding budget-dependent Phase 8)
- Validate semantic predicates with local backend
- Test parallel Phase 4/5 execution
- Success criteria: All gates through Phase 7 pass; decision to proceed/iterate

### 7.6 Testing Milestones

| Milestone | Test | Pass criteria |
|-----------|------|---------------|
| M1: Transport alive | `GET /health` returns 200 | Ollama running, model loaded |
| M2: JSON output | Single cli-prompt invocation returns parseable JSON | `_extract_json_response()` succeeds |
| M3: Tool call loop | TAPM invocation with Read tool completes | Tool loop terminates, JSON returned |
| M4: Schema compliance | Skill output passes `_validate_skill_output()` | run_id, schema_id, required fields present |
| M5: Phase 1 gate pass | `python -m runner --phase 1` exits 0 | All Phase 1 gate predicates pass |
| M6: Phase 3 gate pass | Phase 3 with WP structure + dependency mapping | Structural output valid |
| M7: Semantic predicate | `no_unresolved_scope_conflicts` produces valid result | `validate_semantic_result()` passes |
| M8: Full pipeline | Phases 1-7 complete | All gates pass; Phase 8 unblocked |

### 7.7 Smoke-Test Strategy

Before any pilot phase, run a minimal smoke test:

```bash
# 1. Verify Ollama is serving
curl -s http://localhost:11434/v1/models | python -m json.tool

# 2. Verify basic completion
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"Return only: {\"status\":\"ok\"}"}],"temperature":0}' \
  | python -m json.tool

# 3. Verify tool use
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:32b","messages":[{"role":"user","content":"Read the file at /tmp/test.json"}],"tools":[...tool schemas...],"temperature":0}' \
  | python -m json.tool

# 4. Run transport unit tests
ORCHESTRATOR_TRANSPORT_BACKEND=ollama python -m pytest tests/test_transport/ -v
```

### 7.8 Fallback Procedures

| Failure | Fallback |
|---------|----------|
| Ollama crashes mid-invocation | `ClaudeTransportError` propagates; skill returns `SkillResult(failure)` ; node blocked at exit |
| Model produces unparseable output | `_extract_json_response()` returns `None`; skill fails with `INCOMPLETE_OUTPUT` |
| Tool loop exceeds `MAX_TOOL_ROUNDS` | Final no-tools call forces text response; may be incomplete |
| GPU OOM | Ollama returns 500; transport raises `ClaudeTransportError` |
| Quality too low for gate pass | Switch to larger model or fallback to Claude CLI |

### 7.9 Rollback Procedures

Rollback to Claude CLI is a single environment variable change:

```bash
# Switch back to Claude CLI
unset ORCHESTRATOR_TRANSPORT_BACKEND
# or explicitly:
export ORCHESTRATOR_TRANSPORT_BACKEND=claude_cli
```

No code changes required. No artifact migration. No state cleanup. The transport layer is stateless; switching backends between runs has no side effects.

---

## 8. E — Security & Governance

### 8.1 Prompt Confidentiality

- Prompts contain Tier 3 project data (consortium details, IP, strategic positioning)
- Prompts are transmitted only to the internal GPU server over mTLS
- No prompt content is transmitted to any external service
- Prompt logs on GPU server are encrypted at rest and purged after 30 days

### 8.2 Output Confidentiality

- LLM outputs contain candidate proposal text (IP-sensitive)
- Outputs are transmitted only back to the orchestrator host over mTLS
- Outputs are written to `docs/` tier hierarchy on the orchestrator host
- Output logs on GPU server are encrypted and purged per retention policy

### 8.3 Auditability

- Every LLM invocation is logged with: timestamp, skill_id, node_id, run_id, model, token usage, latency
- Tool executor logs all file reads (path, bytes read) for each TAPM invocation
- Diagnostic bundles (`.claude/skill_diag/`) continue to be written for transport failures
- Gate results record which predicates passed/failed and why
- Run summaries record full node execution traces

### 8.4 Model Isolation

- Models run exclusively on the internal GPU server
- No model weights are stored on or transmitted from the orchestrator host
- Model updates are performed via offline import (air-gapped transfer)
- No model phoning home, telemetry, or external API calls

### 8.5 Role Separation

| Role | Access | Responsibility |
|------|--------|---------------|
| **Proposal author** | Orchestrator host (full), GPU server (none) | Populate Tier 3, run scheduler |
| **Infrastructure admin** | GPU server (full), Orchestrator host (none) | Deploy models, manage certs, monitor |
| **Reviewer** | Orchestrator host (read-only docs/), GPU server (none) | Review Tier 5 deliverables |

### 8.6 Authentication & Authorization

| Layer | Mechanism |
|-------|-----------|
| VPN access | Institutional credentials (SSO/LDAP) |
| GPU server SSH | Key-based only; password auth disabled |
| LLM API endpoint | API token in `Authorization: Bearer` header |
| mTLS | Client certificate per orchestrator host |
| Orchestrator host | OS-level user permissions |

### 8.7 Operational Governance

- Model changes (new model, quantization change) require infrastructure admin approval
- Configuration changes (`ORCHESTRATOR_TRANSPORT_*`) are logged and reviewed
- API token rotation: quarterly
- Certificate rotation: annually
- Log review: monthly (for anomalous access patterns)

### 8.8 Model Update Governance

- New models are evaluated against the pilot test suite before deployment
- Model updates follow a staging → production promotion path
- Staging runs: full Phase 1-7 pipeline with test data
- Production promotion requires: all gates pass, quality assessment documented
- Rollback to previous model: immediate (Ollama supports multiple model versions)

### 8.9 Incident Handling

| Incident | Response | Escalation |
|----------|----------|------------|
| Transport failure (timeout, 5xx) | Automatic: SkillResult(failure), node blocked | None (normal operation) |
| Repeated gate failures | Manual: review diagnostic bundles, assess model quality | Infrastructure admin |
| Suspected data exfiltration | Immediate: isolate GPU server, audit logs | Security team + PI |
| Model produces harmful/biased content | Review output, adjust system prompt, switch model | PI + ethics advisor |
| GPU hardware failure | Failover to Claude CLI backend | Infrastructure admin |

### 8.10 Logging Boundaries

**What IS logged (GPU server):**
- Full request/response JSON (for debugging)
- Latency, token counts, model identifier
- Error details on failure

**What is NOT logged:**
- No logs transmitted to external services
- No anonymized usage analytics
- No model performance telemetry to model providers
- No prompt/response content to any third party

---

## 9. F — Validation Strategy

### 9.1 Transport-Layer Validation

```
tests/test_transport/
  test_backend_factory.py         # get_transport() returns correct backend for each env config
  test_claude_cli_transport.py    # Existing tests, refactored to use ClaudeCLITransport class
  test_openai_compatible.py       # HTTP request format, response parsing, error handling
  test_ollama_transport.py        # Ollama-specific defaults, health check
  test_transport_response.py      # TransportResponse normalization across backends
  test_exception_compatibility.py # All three exception types raised consistently
```

**Key test scenarios:**
- Backend returns valid JSON → response.text contains it
- Backend returns non-JSON → response.text contains raw text (downstream parsing handles it)
- Backend returns 500 → `ClaudeTransportError` raised
- Backend times out → `ClaudeCLITimeoutError` raised
- Backend unreachable → `ClaudeCLIUnavailableError` raised
- Invalid backend name → `ValueError` from `get_transport()`

### 9.2 TAPM Compatibility Tests

```
tests/test_transport/
  test_tool_executor.py           # Read/Glob emulation, sandboxing, limits
  test_tool_loop.py               # Multi-round tool call loop, timeout, max rounds
  test_tapm_integration.py        # Full TAPM path with mocked backend
```

**Critical test scenarios:**
- Read within sandbox → content returned
- Read outside sandbox → error returned (not exception — tool results are strings)
- Read outside allowed_prefixes → error returned
- Read non-existent file → error returned
- Read file > 500KB → error returned
- Total reads > 5MB → error returned
- Glob within sandbox → paths returned
- Glob outside sandbox → error returned
- Tool loop completes in < MAX_TOOL_ROUNDS → final text returned
- Tool loop reaches MAX_TOOL_ROUNDS → forced final call, text returned
- Tool loop timeout → `ClaudeCLITimeoutError` raised
- Backend returns no tool_calls → single-round, text returned
- Backend returns malformed tool_calls → graceful error handling

### 9.3 Semantic Predicate Compatibility Tests

```
tests/test_transport/
  test_semantic_dispatch_transport.py  # semantic_dispatch through non-Claude backend
```

**Key concern:** Semantic predicates require nuanced constitutional reasoning. The test suite must validate:
- Response conforms to §4.9 schema (predicate_id, function, status, findings, etc.)
- `validate_semantic_result()` passes on well-formed responses
- Dispatch error results are produced correctly for transport failures
- Finding fields (violated_rule, evidence_path, severity) are populated

### 9.4 Scheduler Integrity Tests

The existing 1600+ test suite validates scheduler behaviour independently of the transport layer. These tests must continue to pass with no modification:

```bash
# Full test suite — must pass before and after migration
python -m pytest tests/ -v --tb=short
```

No scheduler test should be modified as part of this migration. If a test fails, the transport layer has a bug.

### 9.5 Gate Equivalence Validation

For each gate (11 total, 102 predicates):

1. Run the phase with Claude CLI backend → collect gate result artifacts
2. Run the same phase with Ollama backend → collect gate result artifacts
3. Compare deterministic predicate results (must be identical — they don't use the LLM)
4. Compare semantic predicate results (may differ — document quality delta)

**Deterministic predicates:** Must produce identical results regardless of backend. If they differ, the test infrastructure has a bug (deterministic predicates don't invoke the LLM).

**Semantic predicates:** Results may differ. Document the delta. Establish quality thresholds for each semantic predicate.

### 9.6 Regression Validation Strategy

After each migration step:

1. Run the full test suite (`python -m pytest tests/`)
2. Run a Phase 1 end-to-end with Claude CLI → verify gate pass
3. Run a Phase 1 end-to-end with the new backend → compare
4. Verify diagnostic bundles are written correctly for failures

### 9.7 Staged Migration Validation

| Stage | Scope | Validation |
|-------|-------|------------|
| 1. Transport abstraction | `claude_transport.py` refactored | All existing tests pass; `invoke_claude_text()` behaviour unchanged |
| 2. Claude CLI backend class | `ClaudeCLITransport` extracted | Exact same subprocess invocation; mock tests + one real invocation |
| 3. OpenAI-compatible backend | `OpenAICompatibleTransport` | HTTP mock tests; one real Ollama invocation |
| 4. Tool executor | `ToolExecutor` | Sandboxing tests; file read tests; glob tests |
| 5. Tool loop | `run_tool_loop()` | Multi-round mock tests; timeout tests |
| 6. Integration: cli-prompt | cli-prompt skill through Ollama | Phase 1 skill (small) produces parseable JSON |
| 7. Integration: TAPM | TAPM skill through Ollama + tool loop | Phase 1 TAPM skill reads files and produces output |
| 8. Full pipeline | Phases 1-7 | All gates pass |

### 9.8 Highest-Risk Migration Areas

1. **JSON output quality** (HIGH): Open-source models produce less reliable structured JSON than Claude. The `_extract_json_response()` fallback parsing becomes critical. Mitigation: test extensively with real prompts; add JSON schema enforcement in system prompt.

2. **Tool call format** (HIGH): Different models format `tool_calls` differently. Ollama's OpenAI-compatible mode may have subtle differences in `function.arguments` formatting. Mitigation: extensive integration testing with real tool schemas.

3. **Schema field compliance** (MEDIUM): Models may omit `run_id`, `schema_id`, or include `artifact_status` despite instructions. Current `_validate_skill_output()` rejects these. Mitigation: strengthen system prompt instructions; consider one-time field injection for non-Claude backends (constitutional compliance question — must not silently repair).

4. **Semantic predicate quality** (HIGH): Constitutional reasoning requires understanding of CLAUDE.md, tier hierarchy, and nuanced compliance rules. Smaller models will be significantly weaker. Mitigation: may need to retain Claude CLI for semantic predicates initially.

5. **TAPM tool loop latency** (MEDIUM): Each tool round-trip adds network + inference latency. A skill requiring 10 Read calls may take 5-10 minutes on Ollama vs. 30-60s on Claude. Mitigation: Accept higher latency for pilot; optimize with batched reads for production.

### 9.9 Semantic Degradation Risks

| Capability | Claude (current) | Expected with Qwen3-32B | Mitigation |
|-----------|-----------------|------------------------|------------|
| Structured JSON output | Excellent | Good (occasional formatting issues) | Robust parsing in `_extract_json_response()` |
| Schema field compliance | Excellent | Moderate (may omit metadata fields) | Explicit schema in system prompt |
| Tool call adherence | Excellent | Good (may not call tools when should) | Retry logic; explicit tool-use instructions |
| Constitutional reasoning | Strong | Moderate-weak | Consider hybrid: local for skills, Claude for semantic predicates |
| Proposal writing quality | Strong | Moderate | Accept quality delta; iterate on prompts |
| Long-context coherence | Excellent (1M context) | Good (128K context) | Context fits within Qwen3 limits |

---

## 10. Migration Phases

### Phase 0: Preparation (Week 0)

- [ ] Inventory all `invoke_claude_text()` call sites (confirmed: 3)
- [ ] Document current test coverage for transport layer
- [ ] Set up GPU server with Ollama and Qwen3-8B for smoke testing
- [ ] Create `runner/transport/` package structure
- [ ] Write `TransportBackend` abstract class and `TransportResponse`

### Phase 1: Transport Abstraction (Weeks 1-2)

- [ ] Extract `ClaudeCLITransport` from current `claude_transport.py`
- [ ] Implement `get_transport()` factory with env-var selection
- [ ] Modify `invoke_claude_text()` to delegate to backend
- [ ] Verify all 1600+ existing tests pass without modification
- [ ] Verify Claude CLI behaviour is byte-for-byte identical

### Phase 2: OpenAI-Compatible Backend (Weeks 2-3)

- [ ] Implement `OpenAICompatibleTransport`
- [ ] Implement `OllamaTransport` convenience subclass
- [ ] Write HTTP mock tests
- [ ] Validate against live Ollama endpoint (Qwen3-8B)
- [ ] Validate error handling (timeout, 5xx, connection refused)

### Phase 3: Local Tool Executor (Weeks 3-4)

- [ ] Implement `ToolExecutor` with Read/Glob emulation
- [ ] Implement sandbox enforcement and declared-input boundary
- [ ] Write comprehensive sandboxing tests
- [ ] Implement `run_tool_loop()` with round limits and timeout
- [ ] Write tool loop tests with mocked backend

### Phase 4: Integration Validation (Weeks 4-6)

- [ ] Run Phase 1 end-to-end with Ollama + Qwen3-32B
- [ ] Compare outputs against Claude baseline
- [ ] Document quality delta
- [ ] Iterate on system prompts if needed
- [ ] Validate diagnostic bundle writing

### Phase 5: Multi-Phase Validation (Weeks 6-10)

- [ ] Run Phases 1-7 with Ollama backend
- [ ] Validate all 11 gates
- [ ] Measure latency across all skills
- [ ] Document semantic predicate quality
- [ ] Decide: full local deployment vs. hybrid (local skills + Claude semantics)

### Phase 6: Production Hardening (Weeks 10-14)

- [ ] Deploy reverse proxy with mTLS
- [ ] Implement monitoring and alerting
- [ ] Implement log rotation and encryption
- [ ] Document operational runbook
- [ ] Conduct security review

---

## 11. Risk Analysis

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| JSON output quality insufficient | Medium | High | Robust parsing; prompt engineering; model selection |
| Tool call loop never terminates | Low | High | MAX_TOOL_ROUNDS + timeout deadline |
| Semantic predicates unusable | High | Medium | Hybrid mode: local for skills, Claude for semantics |
| VRAM exhaustion during inference | Low | Medium | Model quantization; VRAM monitoring; auto-restart |
| Prompt size exceeds model context | Low | Low | All prompts < 128K tokens; verified by measurement |
| `_validate_skill_output()` rejects all outputs | Medium | High | Iterative prompt engineering; consider relaxed metadata for non-Claude |

### 11.2 Architectural Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Transport abstraction introduces subtle behavioural differences | Low | High | Comprehensive integration testing; Claude CLI as golden reference |
| Tool executor sandbox bypass | Low | Critical | Path resolution with `.resolve()`; symlink handling; test coverage |
| TAPM tool loop interacts poorly with model reasoning | Medium | Medium | Model-specific prompt tuning; round count monitoring |
| Multi-turn conversation state exceeds context | Low | Medium | Message truncation strategy; monitoring |

### 11.3 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| GPU server hardware failure | Low | High | Instant fallback to Claude CLI; no state on GPU server |
| Model update breaks schema compliance | Medium | Medium | Staging environment; gate pass validation before promotion |
| VPN connectivity loss | Medium | Low | Retry with backoff; fallback to Claude CLI |
| Certificate expiry | Low | Medium | Monitoring alert at 30 days; cron rotation |

### 11.4 Quality Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Proposal text quality drops significantly | High | High | A/B comparison; retain Claude for Phase 8 drafting if needed |
| Constitutional compliance reasoning degraded | High | Medium | Hybrid mode for semantic predicates |
| Evaluator-oriented writing quality insufficient | High | High | Larger model (70B); multi-shot prompting; human review |

---

## 12. Recommended Implementation Order

```
Week 0:    GPU server setup + smoke test
Weeks 1-2: Transport abstraction + ClaudeCLI extraction
Week 2-3:  OpenAICompatibleTransport + Ollama Transport
Weeks 3-4: Tool executor + tool loop
Weeks 4-6: Phase 1 end-to-end with Ollama
Weeks 6-8: Phases 1-3 with Ollama
Weeks 8-10: Phases 1-7 with Ollama
Weeks 10-12: Production hardening (mTLS, monitoring, logs)
Weeks 12-14: Full pipeline validation + quality assessment
Week 14:   Go/no-go decision for production deployment
```

**Critical path:** Transport abstraction (Phase 1) must preserve exact Claude CLI behaviour. Every subsequent phase depends on this foundation. Do not proceed to Phase 2 until all existing tests pass.

**Parallel work:** GPU server setup (Phase 0) can proceed in parallel with transport abstraction (Phase 1). Tool executor development (Phase 3) can begin once the backend abstraction is stable.

---

## 13. Recommended First Pilot Milestone

**Milestone: Phase 1 Gate Pass with Ollama Backend**

**Definition:** Run `python -m runner --phase 1 --run-id <uuid>` with `ORCHESTRATOR_TRANSPORT_BACKEND=ollama` and have the Phase 1 gate (`phase_01_gate`) pass with all 15 deterministic predicates satisfied.

**Why this milestone:**
1. Phase 1 exercises both execution modes (TAPM for `call-requirements-extraction`, `evaluation-matrix-builder`, `instrument-schema-normalization`, `topic-scope-check`; cli-prompt for none — all Phase 1 skills are TAPM)
2. The call slicer (Step 0) runs before any LLM invocation, so the bounded-input path is exercised
3. Phase 1 gate has 15 deterministic predicates covering file existence, JSON schema conformance, and field presence — a comprehensive structural validation
4. Phase 1 has no upstream dependencies, so it can be validated in isolation
5. Success here proves: transport abstraction works, tool loop works, JSON output parsing works, schema validation passes, gate evaluation passes

**Success criteria:**
- `overall_status: "pass"` in run_summary.json
- `phase_01_gate` result: `status: "pass"`, all predicate_refs satisfied
- All 6 Tier 2B extracted JSON files present and non-empty
- No `ClaudeTransportError` exceptions in logs
- Tool executor audit log shows reads only within declared `reads_from` paths
- Execution completes within 30 minutes (vs. ~5 minutes on Claude — acceptable for pilot)

**Fallback if milestone is not met:**
- Review diagnostic bundles in `.claude/skill_diag/`
- Identify which skills failed and why (JSON parsing? Schema compliance? Tool loop?)
- Iterate on system prompts for the specific failure mode
- If structural issues persist, try Qwen3-32B at higher quantization or switch to Llama 3.3-70B
- If tool loop issues: review tool call format compatibility with Ollama's OpenAI mode

---

## Appendix A: Constitutional Amendment Required

When the migration is complete and validated, CLAUDE.md Section 17 must be amended per Section 14 (Constitutional Change Rules):

| Field | Value |
|-------|-------|
| Section to be amended | Section 17 (Runtime Execution Architecture) — §17.1, §17.5 |
| Current rule | Section 17 describes the skill runtime as invoking Claude through `runner/claude_transport.py` which routes through the local `claude` CLI. |
| Planned rule | Section 17 will describe a backend-agnostic transport layer (`runner/transport/`) supporting multiple backends (Claude CLI, OpenAI-compatible, Ollama). The skill runtime invokes the active backend through `invoke_claude_text()` (interface preserved). For non-Claude backends, a local tool executor handles TAPM Read/Glob tool calls with deterministic sandbox enforcement. All external governance (scheduler, gates, artifact validation, fail-closed semantics) remains unchanged. |
| Reason for change | Migration from Claude CLI-dependent transport to backend-agnostic internal LLM architecture for closed-network deployment. |
| Impacted components | `runner/claude_transport.py`, `runner/transport/` (new package), `runner/skill_runtime.py` (tool loop integration for non-Claude backends). Scheduler, gate evaluator, agent runtime, runtime contracts, and failure semantics are unchanged. |

This amendment must be applied by explicit human instruction per CLAUDE.md §14.5.

---

## Appendix B: Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORCHESTRATOR_TRANSPORT_BACKEND` | No | `claude_cli` | Backend selection: `claude_cli`, `ollama`, `openai_compatible` |
| `ORCHESTRATOR_TRANSPORT_ENDPOINT` | For non-Claude | None | Base URL: `https://gpu-server.internal:8443/v1` |
| `ORCHESTRATOR_TRANSPORT_MODEL` | No | Backend default | Model override: `qwen3:32b`, `llama3.3:70b` |
| `ORCHESTRATOR_TRANSPORT_API_KEY` | No | None | API token for authenticated endpoints |
| `ORCHESTRATOR_TRANSPORT_TLS_CERT` | No | None | Client certificate path for mTLS |

---

## Appendix C: File Inventory — New and Modified Files

**New files:**
```
runner/transport/__init__.py
runner/transport/base.py              # TransportBackend, TransportResponse
runner/transport/claude_cli.py        # ClaudeCLITransport
runner/transport/openai_compatible.py # OpenAICompatibleTransport
runner/transport/ollama.py            # OllamaTransport
runner/transport/config.py            # get_transport(), env var handling
runner/transport/tool_executor.py     # ToolExecutor, run_tool_loop()
tests/test_transport/                 # All transport tests
```

**Modified files:**
```
runner/claude_transport.py            # invoke_claude_text() delegates to backend
runner/skill_runtime.py               # TAPM path: tool loop for non-Claude backends
```

**Unchanged files (all other runner/ modules):**
```
runner/dag_scheduler.py
runner/agent_runtime.py
runner/gate_evaluator.py
runner/semantic_dispatch.py
runner/runtime_models.py
runner/run_context.py
runner/call_slicer.py
runner/dependency_normalizer.py
runner/predicates/*.py
runner/gate_library.py
runner/manifest_reader.py
runner/node_resolver.py
runner/paths.py
runner/versions.py
runner/upstream_inputs.py
runner/phase8_*.py
runner/__main__.py
```

**Total modified production files: 2. Total new production files: 7.**

---

*This plan is subordinate to CLAUDE.md. Implementation must comply with all constitutional rules. No implementation step may silently bypass gates, fabricate completion, or violate the authority hierarchy.*
