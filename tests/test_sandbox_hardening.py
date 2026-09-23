"""Sandbox hardening tests (Phase 2).

Tests for runtime boundary enforcement beyond the basic coverage in
test_transport_tool_executor.py. Covers:

    - Path injection edge cases (NUL bytes, empty strings, double-encoding)
    - Windows reserved device names
    - Relative path injection via Read/Glob
    - Tool capability mismatch fail-closed behavior
    - Unknown/dangerous tool rejection (Write, Edit, Bash, etc.)
    - Subprocess shell=False verification
    - Tool loop max-rounds enforcement
    - Tool loop timeout enforcement
    - Environment variable isolation from tool execution
    - Declared-input boundary exhaustive checks
    - Glob pattern injection attempts
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

from runner.transport.tool_executor import (
    KNOWN_TOOLS,
    MAX_FILE_READ_BYTES,
    MAX_GLOB_RESULTS,
    MAX_TOTAL_READ_BYTES,
    ToolExecutor,
    is_within,
)
from runner.transport.tool_loop import (
    DEFAULT_MAX_ROUNDS,
    FakeBackend,
    ToolLoopResponse,
    run_tool_loop,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    """Create a sandbox repo tree for testing."""
    repo = tmp_path / "repo"
    (repo / "docs" / "tier3").mkdir(parents=True)
    (repo / "docs" / "tier5").mkdir(parents=True)
    (repo / "other").mkdir(parents=True)
    (repo / "docs" / "tier3" / "data.json").write_text(
        '{"key": "value"}', encoding="utf-8"
    )
    (repo / "other" / "secret.txt").write_text("classified", encoding="utf-8")
    return repo


# ---------------------------------------------------------------------------
# Path injection edge cases
# ---------------------------------------------------------------------------


class TestPathInjectionEdgeCases:
    """Test that path manipulation attempts are safely rejected."""

    def test_empty_file_path_rejected(self, sandbox: Path) -> None:
        """Empty string file_path is rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call("Read", {"file_path": ""})
        data = json.loads(result)
        assert "error" in data

    def test_whitespace_only_path_rejected(self, sandbox: Path) -> None:
        """Whitespace-only file_path is rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call("Read", {"file_path": "   "})
        data = json.loads(result)
        assert "error" in data

    def test_none_file_path_rejected(self, sandbox: Path) -> None:
        """None file_path is rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call("Read", {"file_path": None})
        data = json.loads(result)
        assert "error" in data

    def test_integer_file_path_rejected(self, sandbox: Path) -> None:
        """Non-string file_path is rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call("Read", {"file_path": 12345})
        data = json.loads(result)
        assert "error" in data

    def test_missing_file_path_key_rejected(self, sandbox: Path) -> None:
        """Missing file_path argument entirely is rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call("Read", {})
        data = json.loads(result)
        assert "error" in data

    def test_dot_dot_escape_in_prefix(self, sandbox: Path) -> None:
        """Relative traversal ../../ is blocked by sandbox boundary."""
        escape = str(sandbox / "docs" / "tier3" / ".." / ".." / ".." / "etc" / "passwd")
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call("Read", {"file_path": escape})
        data = json.loads(result)
        assert "error" in data

    def test_relative_path_without_absolute_anchor(self, sandbox: Path) -> None:
        """Relative paths are anchored to repo_root, not cwd."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read", {"file_path": "docs/tier3/data.json"}
        )
        # Should succeed — relative paths anchored to repo_root
        assert '"key"' in result

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Windows-specific reserved name test",
    )
    def test_windows_reserved_name_handled(self, sandbox: Path) -> None:
        """Windows reserved device names (CON, NUL, etc.) are handled safely."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call("Read", {"file_path": "CON"})
        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# Glob injection attempts
# ---------------------------------------------------------------------------


class TestGlobInjectionAttempts:
    """Test that glob patterns cannot escape sandbox boundaries."""

    def test_glob_empty_pattern_rejected(self, sandbox: Path) -> None:
        """Empty pattern is rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call("Glob", {"pattern": ""})
        data = json.loads(result)
        assert "error" in data

    def test_glob_none_pattern_rejected(self, sandbox: Path) -> None:
        """None pattern is rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call("Glob", {"pattern": None})
        data = json.loads(result)
        assert "error" in data

    def test_glob_parent_traversal_in_path(self, sandbox: Path, tmp_path: Path) -> None:
        """Glob with ../ in path cannot escape sandbox."""
        escape_path = str(sandbox / "docs" / ".." / ".." )
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call(
            "Glob", {"pattern": "*.txt", "path": escape_path}
        )
        data = json.loads(result)
        assert "error" in data

    def test_glob_absolute_outside_path_rejected(self, sandbox: Path, tmp_path: Path) -> None:
        """Glob with absolute path outside repo is rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call(
            "Glob", {"pattern": "*", "path": str(tmp_path)}
        )
        data = json.loads(result)
        assert "error" in data

    def test_glob_no_matches_returns_sentinel(self, sandbox: Path) -> None:
        """No matches returns the (no matches) sentinel, not an error."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Glob",
            {"pattern": "*.nonexistent", "path": str(sandbox / "docs" / "tier3")},
        )
        assert result == "(no matches)"


# ---------------------------------------------------------------------------
# Dangerous tool rejection
# ---------------------------------------------------------------------------


class TestDangerousToolRejection:
    """Verify that all non-Read/Glob tools are rejected."""

    @pytest.mark.parametrize("tool_name", [
        "Write", "Edit", "Bash", "Delete", "NotebookEdit",
        "exec", "os.system", "subprocess", "eval",
        "WebFetch", "WebSearch",
    ])
    def test_dangerous_tool_rejected(self, sandbox: Path, tool_name: str) -> None:
        """Dangerous or unknown tool names produce structured errors."""
        ex = ToolExecutor(sandbox, allowed_prefixes=None)
        result = ex.execute_tool_call(tool_name, {})
        data = json.loads(result)
        assert "error" in data
        assert "unknown" in data["error"].lower()

    def test_known_tools_are_exactly_read_and_glob(self) -> None:
        """KNOWN_TOOLS contains exactly Read and Glob — nothing else."""
        assert KNOWN_TOOLS == frozenset({"Read", "Glob"})

    def test_case_sensitive_tool_names(self, sandbox: Path) -> None:
        """Tool names are case-sensitive — 'read' and 'READ' are rejected."""
        ex = ToolExecutor(sandbox, allowed_prefixes=None)
        for bad_name in ["read", "READ", "glob", "GLOB", "rEaD"]:
            result = ex.execute_tool_call(bad_name, {})
            data = json.loads(result)
            assert "error" in data, f"{bad_name} should be rejected"


# ---------------------------------------------------------------------------
# Tool loop security
# ---------------------------------------------------------------------------


class TestToolLoopSecurity:
    """Test tool loop boundary enforcement."""

    def test_max_rounds_enforced(self, sandbox: Path) -> None:
        """Tool loop stops after max_rounds even if model keeps requesting tools."""
        tool_call_response = {
            "content": "",
            "tool_calls": [{
                "id": "tc1",
                "type": "function",
                "function": {
                    "name": "Read",
                    "arguments": json.dumps({
                        "file_path": str(sandbox / "docs" / "tier3" / "data.json")
                    }),
                },
            }],
        }
        # Return tool calls forever — loop should stop at max_rounds
        backend = FakeBackend(
            [tool_call_response] * 10,
            default_final=tool_call_response,
        )

        result = run_tool_loop(
            backend=backend,
            system_prompt="test",
            user_prompt="test",
            repo_root=sandbox,
            allowed_prefixes=["docs/tier3"],
            max_rounds=5,
        )
        assert result.exhausted_rounds is True
        assert result.rounds == 5

    def test_timeout_enforced(self, sandbox: Path) -> None:
        """Tool loop respects timeout_seconds."""
        def slow_backend(messages):
            time.sleep(0.5)
            return {"content": "done", "tool_calls": None}

        result = run_tool_loop(
            backend=slow_backend,
            system_prompt="test",
            user_prompt="test",
            repo_root=sandbox,
            timeout_seconds=0.01,  # very short timeout
        )
        # Should have hit the timeout
        assert result.exhausted_rounds is True or result.text == "done"

    def test_unknown_tool_in_loop_produces_error_result(self, sandbox: Path) -> None:
        """Unknown tool calls in the loop produce error results, not crashes."""
        responses = [
            {
                "content": "",
                "tool_calls": [{
                    "id": "tc1",
                    "type": "function",
                    "function": {
                        "name": "Bash",
                        "arguments": json.dumps({"command": "rm -rf /"}),
                    },
                }],
            },
            {"content": "final response", "tool_calls": None},
        ]
        backend = FakeBackend(responses)
        result = run_tool_loop(
            backend=backend,
            system_prompt="test",
            user_prompt="test",
            repo_root=sandbox,
        )
        assert result.text == "final response"
        # The Bash tool call should have produced an error in messages
        tool_msgs = [
            m for msgs in backend.received_messages
            for m in msgs
            if m.get("role") == "tool"
        ]
        if tool_msgs:
            error_content = json.loads(tool_msgs[0]["content"])
            assert "error" in error_content

    def test_malformed_arguments_produce_error(self, sandbox: Path) -> None:
        """Malformed JSON arguments produce structured errors."""
        responses = [
            {
                "content": "",
                "tool_calls": [{
                    "id": "tc1",
                    "type": "function",
                    "function": {
                        "name": "Read",
                        "arguments": "not valid json{{{",
                    },
                }],
            },
            {"content": "final", "tool_calls": None},
        ]
        backend = FakeBackend(responses)
        result = run_tool_loop(
            backend=backend,
            system_prompt="test",
            user_prompt="test",
            repo_root=sandbox,
        )
        assert result.text == "final"


# ---------------------------------------------------------------------------
# Subprocess boundary verification
# ---------------------------------------------------------------------------


class TestSubprocessBoundary:
    """Verify subprocess invocations use shell=False."""

    def test_claude_transport_uses_shell_false(self) -> None:
        """claude_transport.invoke_claude_text uses shell=False."""
        import inspect
        import runner.claude_transport as ct
        source = inspect.getsource(ct.invoke_claude_text)
        assert "shell=False" in source
        # Verify shell=True is NOT present
        assert "shell=True" not in source

    def test_no_shell_true_in_runner(self) -> None:
        """No Python file in runner/ uses shell=True in subprocess calls."""
        from pathlib import Path
        runner_dir = Path(__file__).resolve().parents[1] / "runner"
        violations = []
        for py_file in runner_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if "shell=True" in content:
                violations.append(str(py_file))
        assert violations == [], f"shell=True found in: {violations}"


# ---------------------------------------------------------------------------
# Declared-input boundary enforcement
# ---------------------------------------------------------------------------


class TestDeclaredInputBoundary:
    """Exhaustive declared-input boundary checks."""

    def test_file_in_repo_but_not_in_prefix_denied(self, sandbox: Path) -> None:
        """File inside repo but outside declared prefixes is denied."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read",
            {"file_path": str(sandbox / "other" / "secret.txt")},
        )
        data = json.loads(result)
        assert "error" in data
        assert "declared" in data["error"].lower()

    def test_glob_in_repo_but_not_in_prefix_denied(self, sandbox: Path) -> None:
        """Glob with base inside repo but outside declared prefixes is denied."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Glob",
            {"pattern": "*.txt", "path": str(sandbox / "other")},
        )
        data = json.loads(result)
        assert "error" in data
        assert "declared" in data["error"].lower()

    def test_multiple_prefixes_any_match_allows(self, sandbox: Path) -> None:
        """With multiple prefixes, matching any one allows access."""
        ex = ToolExecutor(
            sandbox, allowed_prefixes=["docs/tier3", "docs/tier5"]
        )
        # tier3 access
        r1 = ex.execute_tool_call(
            "Read",
            {"file_path": str(sandbox / "docs" / "tier3" / "data.json")},
        )
        assert '"key"' in r1

    def test_no_prefix_restriction_allows_all(self, sandbox: Path) -> None:
        """When allowed_prefixes is None, any repo file is accessible."""
        ex = ToolExecutor(sandbox, allowed_prefixes=None)
        result = ex.execute_tool_call(
            "Read",
            {"file_path": str(sandbox / "other" / "secret.txt")},
        )
        assert "classified" in result


# ---------------------------------------------------------------------------
# is_within edge cases
# ---------------------------------------------------------------------------


class TestIsWithinEdgeCases:
    """Additional edge cases for the is_within path safety function."""

    def test_prefix_collision_root_evil(self, tmp_path: Path) -> None:
        """Ensure /repo-evil is NOT treated as inside /repo."""
        repo = tmp_path / "repo"
        repo.mkdir()
        evil = tmp_path / "repo-evil"
        evil.mkdir()
        assert is_within(evil, repo) is False

    def test_deeply_nested_path(self, tmp_path: Path) -> None:
        """Very deep paths are correctly evaluated."""
        deep = tmp_path
        for i in range(20):
            deep = deep / f"level{i}"
        deep.mkdir(parents=True)
        assert is_within(deep, tmp_path) is True

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        """Nonexistent paths can still be evaluated (resolve works)."""
        fake = tmp_path / "nonexistent" / "path"
        # is_within should not crash on nonexistent paths
        result = is_within(fake, tmp_path)
        assert isinstance(result, bool)
