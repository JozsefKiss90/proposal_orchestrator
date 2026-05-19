"""
Tests for ``runner.transport.tool_loop`` — fake-backend tool-call loop.

Covers:
    - Single Read round then final text
    - Glob then Read sequence
    - Unknown tool handling
    - Malformed arguments
    - Max-rounds enforcement
    - No filesystem writes
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from runner.transport.tool_loop import (
    DEFAULT_MAX_ROUNDS,
    FakeBackend,
    ToolLoopResponse,
    run_tool_loop,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_call(
    name: str,
    arguments: dict[str, Any] | str,
    call_id: str = "call_1",
) -> dict[str, Any]:
    """Build a single OpenAI-compatible tool-call dict."""
    if isinstance(arguments, dict):
        arguments = json.dumps(arguments)
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    """Minimal sandbox with one readable file."""
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    (repo / "data" / "input.json").write_text(
        '{"hello": "world"}', encoding="utf-8"
    )
    (repo / "data" / "alpha.json").write_text(
        '{"a": 1}', encoding="utf-8"
    )
    (repo / "data" / "beta.json").write_text(
        '{"b": 2}', encoding="utf-8"
    )
    return repo


# ---------------------------------------------------------------------------
# Core loop tests
# ---------------------------------------------------------------------------


class TestToolLoopBasic:
    def test_tool_loop_executes_read_then_returns_final_text(
        self, sandbox: Path
    ) -> None:
        """Backend emits a Read tool call, receives content, then returns
        final text on the second round."""
        file_path = str(sandbox / "data" / "input.json")

        backend = FakeBackend([
            # Round 1: ask to read a file
            {
                "content": "",
                "tool_calls": [
                    _make_tool_call("Read", {"file_path": file_path}),
                ],
            },
            # Round 2: produce final JSON (no more tool calls)
            {
                "content": '{"result": "processed"}',
                "tool_calls": None,
            },
        ])

        result = run_tool_loop(
            backend=backend,
            system_prompt="You are a test.",
            user_prompt="Read the file.",
            repo_root=sandbox,
            allowed_prefixes=["data"],
        )

        assert isinstance(result, ToolLoopResponse)
        assert result.rounds == 2
        assert '"result"' in result.text
        assert result.exhausted_rounds is False
        assert len(result.files_read) == 1
        assert "input.json" in result.files_read[0]

        # Backend received correct messages
        assert backend.call_count == 2
        # Second call should include tool result
        msgs = backend.received_messages[1]
        tool_msgs = [m for m in msgs if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        assert '"hello"' in tool_msgs[0]["content"]

    def test_tool_loop_executes_glob_then_read(self, sandbox: Path) -> None:
        """Backend: Glob to discover files, then Read one of them."""
        glob_path = str(sandbox / "data")

        backend = FakeBackend([
            # Round 1: Glob
            {
                "content": "",
                "tool_calls": [
                    _make_tool_call(
                        "Glob",
                        {"pattern": "*.json", "path": glob_path},
                        call_id="call_glob",
                    ),
                ],
            },
            # Round 2: Read the first discovered file
            {
                "content": "",
                "tool_calls": [
                    _make_tool_call(
                        "Read",
                        {"file_path": str(sandbox / "data" / "alpha.json")},
                        call_id="call_read",
                    ),
                ],
            },
            # Round 3: final response
            {
                "content": '{"done": true}',
                "tool_calls": None,
            },
        ])

        result = run_tool_loop(
            backend=backend,
            system_prompt="sys",
            user_prompt="user",
            repo_root=sandbox,
            allowed_prefixes=["data"],
        )

        assert result.rounds == 3
        assert result.exhausted_rounds is False
        assert '"done"' in result.text
        # Glob round should have returned paths
        glob_tool_msgs = [
            m for m in backend.received_messages[1]
            if m.get("role") == "tool"
        ]
        assert len(glob_tool_msgs) == 1
        assert "alpha.json" in glob_tool_msgs[0]["content"]
        assert "beta.json" in glob_tool_msgs[0]["content"]

    def test_no_tool_calls_returns_immediately(self, sandbox: Path) -> None:
        """If the first response has no tool_calls, loop returns immediately."""
        backend = FakeBackend([
            {"content": "direct answer", "tool_calls": None},
        ])

        result = run_tool_loop(
            backend=backend,
            system_prompt="sys",
            user_prompt="user",
            repo_root=sandbox,
        )

        assert result.rounds == 1
        assert result.text == "direct answer"
        assert result.exhausted_rounds is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestToolLoopErrors:
    def test_tool_loop_denies_unknown_tool(self, sandbox: Path) -> None:
        """Unknown tool name produces a JSON error in the tool result,
        loop continues to next round where backend returns final text."""
        backend = FakeBackend([
            # Round 1: request an unknown tool
            {
                "content": "",
                "tool_calls": [
                    _make_tool_call("Write", {"file_path": "/tmp/evil"}),
                ],
            },
            # Round 2: backend sees error, returns final text
            {
                "content": '{"status": "gave up"}',
                "tool_calls": None,
            },
        ])

        result = run_tool_loop(
            backend=backend,
            system_prompt="sys",
            user_prompt="user",
            repo_root=sandbox,
        )

        assert result.rounds == 2
        # Verify the tool result message contains the error
        msgs_round2 = backend.received_messages[1]
        tool_msgs = [m for m in msgs_round2 if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        error_data = json.loads(tool_msgs[0]["content"])
        assert "error" in error_data
        assert "unknown" in error_data["error"].lower()

    def test_tool_loop_rejects_malformed_arguments(self, sandbox: Path) -> None:
        """Malformed JSON in function.arguments produces a structured error."""
        backend = FakeBackend([
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_bad",
                        "type": "function",
                        "function": {
                            "name": "Read",
                            "arguments": "this is not json {{{{",
                        },
                    }
                ],
            },
            {
                "content": '{"recovered": true}',
                "tool_calls": None,
            },
        ])

        result = run_tool_loop(
            backend=backend,
            system_prompt="sys",
            user_prompt="user",
            repo_root=sandbox,
        )

        assert result.rounds == 2
        msgs = backend.received_messages[1]
        tool_msgs = [m for m in msgs if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        error_data = json.loads(tool_msgs[0]["content"])
        assert "error" in error_data
        assert "malformed" in error_data["error"].lower()


# ---------------------------------------------------------------------------
# Round limits
# ---------------------------------------------------------------------------


class TestToolLoopRoundLimits:
    def test_tool_loop_stops_at_max_rounds(self, sandbox: Path) -> None:
        """Loop stops after max_rounds even if backend keeps requesting tools."""
        file_path = str(sandbox / "data" / "input.json")

        # Backend always requests another Read — never produces final text
        infinite_responses = [
            {
                "content": f"round {i}",
                "tool_calls": [
                    _make_tool_call("Read", {"file_path": file_path}, f"call_{i}"),
                ],
            }
            for i in range(50)
        ]

        backend = FakeBackend(infinite_responses)

        result = run_tool_loop(
            backend=backend,
            system_prompt="sys",
            user_prompt="user",
            repo_root=sandbox,
            allowed_prefixes=["data"],
            max_rounds=5,
        )

        assert result.rounds == 5
        assert result.exhausted_rounds is True
        assert backend.call_count == 5


# ---------------------------------------------------------------------------
# Safety: no writes
# ---------------------------------------------------------------------------


class TestToolLoopNoWrites:
    def test_tool_loop_never_writes_files(self, sandbox: Path) -> None:
        """The tool loop must never create or modify files in the repo."""
        # Snapshot the repo state before
        before = set()
        for root_dir, dirs, files in os.walk(str(sandbox)):
            for f in files:
                p = Path(root_dir) / f
                before.add((str(p), p.stat().st_mtime_ns, p.stat().st_size))

        file_path = str(sandbox / "data" / "input.json")
        backend = FakeBackend([
            {
                "content": "",
                "tool_calls": [
                    _make_tool_call("Read", {"file_path": file_path}),
                ],
            },
            {"content": "done", "tool_calls": None},
        ])

        run_tool_loop(
            backend=backend,
            system_prompt="sys",
            user_prompt="user",
            repo_root=sandbox,
            allowed_prefixes=["data"],
        )

        # Snapshot after
        after = set()
        for root_dir, dirs, files in os.walk(str(sandbox)):
            for f in files:
                p = Path(root_dir) / f
                after.add((str(p), p.stat().st_mtime_ns, p.stat().st_size))

        assert before == after, (
            "Tool loop modified the filesystem!\n"
            f"Added: {after - before}\n"
            f"Removed: {before - after}"
        )


# ---------------------------------------------------------------------------
# FakeBackend contract
# ---------------------------------------------------------------------------


class TestFakeBackend:
    def test_exhausted_responses_returns_default(self) -> None:
        """After all programmed responses, returns the default final."""
        backend = FakeBackend([
            {"content": "first", "tool_calls": None},
        ])
        r1 = backend([])
        assert r1["content"] == "first"
        r2 = backend([])
        assert r2["content"] == '{"status": "done"}'
        assert r2["tool_calls"] is None

    def test_records_messages(self) -> None:
        backend = FakeBackend([
            {"content": "ok", "tool_calls": None},
        ])
        backend([{"role": "user", "content": "hello"}])
        assert len(backend.received_messages) == 1
        assert backend.received_messages[0][0]["content"] == "hello"
        assert backend.call_count == 1

    def test_multiple_tool_calls_in_single_round(self, sandbox: Path) -> None:
        """Backend can request multiple tool calls in one round."""
        f1 = str(sandbox / "data" / "alpha.json")
        f2 = str(sandbox / "data" / "beta.json")

        backend = FakeBackend([
            {
                "content": "",
                "tool_calls": [
                    _make_tool_call("Read", {"file_path": f1}, "c1"),
                    _make_tool_call("Read", {"file_path": f2}, "c2"),
                ],
            },
            {"content": "all read", "tool_calls": None},
        ])

        result = run_tool_loop(
            backend=backend,
            system_prompt="sys",
            user_prompt="user",
            repo_root=sandbox,
            allowed_prefixes=["data"],
        )

        assert result.rounds == 2
        assert len(result.files_read) == 2
        # Check both tool results were appended
        msgs = backend.received_messages[1]
        tool_msgs = [m for m in msgs if m.get("role") == "tool"]
        assert len(tool_msgs) == 2
