"""
Tool-call loop for non-Claude LLM backends.

When an LLM backend does not handle Read/Glob tools internally
(i.e. ``supports_native_tools() == False``), this module drives the
iterative request → tool_calls → execute → re-send cycle using the
local :class:`~runner.transport.tool_executor.ToolExecutor`.

This module is deliberately decoupled from any specific LLM HTTP
client.  It accepts a *backend callable* that takes a list of messages
and returns a response dict.  For testing purposes a
:class:`FakeBackend` is provided that returns a pre-programmed sequence
of responses (including synthetic tool calls).

Security invariants
-------------------
All invariants documented in ``tool_executor.py`` apply transitively.
Additionally:

*   The tool loop **never writes** to the filesystem.
*   Unknown tool names cause the loop to inject a structured error
    result and continue (fail-closed at the tool level; the model sees
    the error and may self-correct or produce a final response).
*   Malformed tool-call arguments produce a structured error result.
*   The loop stops after ``max_rounds`` iterations to prevent runaway
    model behaviour.
*   Gate evaluation and artifact writes remain outside this module.

Authoritative source:
    docs/internal_llm_migration_plan.md §5.4 (Tool Loop Architecture)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from runner.transport.tool_executor import (
    KNOWN_TOOLS,
    ToolExecutor,
    _make_error,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default maximum number of request rounds (initial + tool-result rounds).
DEFAULT_MAX_ROUNDS: int = 25


# ---------------------------------------------------------------------------
# Response data type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolLoopResponse:
    """Final result from :func:`run_tool_loop`.

    Attributes
    ----------
    text:
        The final textual content produced by the backend after all
        tool rounds have been resolved.
    rounds:
        Number of backend invocations performed (including the initial).
    files_read:
        Absolute paths of files read by the tool executor.
    exhausted_rounds:
        ``True`` when the loop stopped because *max_rounds* was reached
        rather than because the backend returned a final (non-tool-call)
        response.
    """
    text: str
    rounds: int = 0
    files_read: list[str] = field(default_factory=list)
    exhausted_rounds: bool = False


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------


class ToolLoopBackend(Protocol):
    """Minimal protocol for the backend callable used by the tool loop.

    A conforming implementation receives a list of OpenAI-style message
    dicts and returns a response dict with the shape::

        {
            "content": str | None,
            "tool_calls": [
                {
                    "id": str,
                    "type": "function",
                    "function": {"name": str, "arguments": str}
                },
                ...
            ] | None,
        }

    If *tool_calls* is ``None`` or empty, the loop treats the response
    as final.
    """

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# FakeBackend — test-only synthetic backend
# ---------------------------------------------------------------------------


class FakeBackend:
    """Pre-programmed backend for testing the tool loop.

    Initialised with an ordered list of response dicts.  Each call to
    the instance pops and returns the next response.  When the list is
    exhausted, subsequent calls return a default final response.

    Parameters
    ----------
    responses:
        Sequence of response dicts to return in order.  Each dict
        should have ``"content"`` and optionally ``"tool_calls"``
        matching the :class:`ToolLoopBackend` protocol.
    default_final:
        Response returned once *responses* is exhausted.
    """

    def __init__(
        self,
        responses: list[dict[str, Any]],
        default_final: dict[str, Any] | None = None,
    ) -> None:
        self._responses = list(responses)
        self._default_final: dict[str, Any] = default_final or {
            "content": '{"status": "done"}',
            "tool_calls": None,
        }
        self.call_count: int = 0
        self.received_messages: list[list[dict[str, Any]]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.call_count += 1
        self.received_messages.append(list(messages))
        if self._responses:
            return self._responses.pop(0)
        return self._default_final


# ---------------------------------------------------------------------------
# run_tool_loop
# ---------------------------------------------------------------------------


def run_tool_loop(
    *,
    backend: ToolLoopBackend,
    system_prompt: str,
    user_prompt: str,
    repo_root: Path,
    allowed_prefixes: list[str] | None = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    timeout_seconds: float | None = None,
) -> ToolLoopResponse:
    """Drive the iterative tool-call loop for a non-Claude backend.

    Parameters
    ----------
    backend:
        Callable conforming to :class:`ToolLoopBackend`.
    system_prompt:
        System-level instructions for the LLM.
    user_prompt:
        User-level prompt text.
    repo_root:
        Repository root for sandbox enforcement.
    allowed_prefixes:
        Declared-input prefixes for TAPM boundary enforcement.
    max_rounds:
        Maximum number of backend invocations.
    timeout_seconds:
        Optional wall-clock timeout for the entire loop.

    Returns
    -------
    ToolLoopResponse
        Contains the final text and execution metadata.
    """
    executor = ToolExecutor(repo_root, allowed_prefixes=allowed_prefixes)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    deadline = (time.monotonic() + timeout_seconds) if timeout_seconds else None

    for round_num in range(1, max_rounds + 1):
        # Check timeout
        if deadline is not None and time.monotonic() > deadline:
            return ToolLoopResponse(
                text="",
                rounds=round_num - 1,
                files_read=executor.files_read,
                exhausted_rounds=True,
            )

        response = backend(messages)

        content = response.get("content") or ""
        tool_calls = response.get("tool_calls")

        # No tool calls → final response
        if not tool_calls:
            return ToolLoopResponse(
                text=content,
                rounds=round_num,
                files_read=executor.files_read,
            )

        # Append assistant message (with tool_calls) to conversation
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        # Execute each tool call
        for tc in tool_calls:
            func_section = tc.get("function") or {}
            func_name = func_section.get("name", "")
            raw_args = func_section.get("arguments", "{}")
            tc_id = tc.get("id", "")

            # Parse arguments — may be a JSON string or already a dict
            if isinstance(raw_args, str):
                try:
                    func_args = json.loads(raw_args)
                except (json.JSONDecodeError, TypeError):
                    func_args = None
            elif isinstance(raw_args, dict):
                func_args = raw_args
            else:
                func_args = None

            if func_args is None:
                tool_result = _make_error(
                    f"Malformed tool arguments for {func_name!r}: "
                    f"could not parse as JSON"
                )
            elif func_name not in KNOWN_TOOLS:
                tool_result = _make_error(
                    f"Unknown tool: {func_name!r}. "
                    f"Only Read and Glob are available."
                )
            else:
                tool_result = executor.execute_tool_call(func_name, func_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": tool_result,
            })

    # Exhausted max_rounds — return whatever content we have from the last
    # assistant message (may be empty).
    last_content = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            last_content = msg.get("content") or ""
            break

    return ToolLoopResponse(
        text=last_content,
        rounds=max_rounds,
        files_read=executor.files_read,
        exhausted_rounds=True,
    )
