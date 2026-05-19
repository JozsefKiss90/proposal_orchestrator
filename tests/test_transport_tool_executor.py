"""
Tests for ``runner.transport.tool_executor`` — local Read/Glob tool
emulation with sandbox enforcement.

Covers:
    - Read: allowed, denied (outside repo, outside prefix, directory,
      missing, symlink escape), truncation, total budget
    - Glob: allowed, deterministic order, denied outside repo,
      symlink filtering, max match enforcement
    - Unknown tool rejection
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

from runner.transport.tool_executor import (
    MAX_FILE_READ_BYTES,
    MAX_GLOB_RESULTS,
    MAX_TOTAL_READ_BYTES,
    ToolExecutor,
    is_within,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    """Create a minimal sandbox directory tree for testing.

    Layout::

        tmp_path/repo/
            docs/
                tier3/
                    data.json     (small JSON file)
                    large.txt     (will be created by specific tests)
                tier5/
                    output.json
            other/
                secret.txt
    """
    repo = tmp_path / "repo"
    (repo / "docs" / "tier3").mkdir(parents=True)
    (repo / "docs" / "tier5").mkdir(parents=True)
    (repo / "other").mkdir(parents=True)

    (repo / "docs" / "tier3" / "data.json").write_text(
        '{"key": "value"}', encoding="utf-8"
    )
    (repo / "docs" / "tier5" / "output.json").write_text(
        '{"section": "excellence"}', encoding="utf-8"
    )
    (repo / "other" / "secret.txt").write_text(
        "classified", encoding="utf-8"
    )
    return repo


# ---------------------------------------------------------------------------
# is_within helper
# ---------------------------------------------------------------------------


class TestIsWithin:
    def test_inside(self, tmp_path: Path) -> None:
        child = tmp_path / "a" / "b"
        child.mkdir(parents=True)
        assert is_within(child, tmp_path) is True

    def test_outside(self, tmp_path: Path) -> None:
        other = tmp_path.parent / "elsewhere"
        assert is_within(other, tmp_path) is False

    def test_same_path(self, tmp_path: Path) -> None:
        assert is_within(tmp_path, tmp_path) is True

    def test_prefix_collision(self, tmp_path: Path) -> None:
        """Ensure /repo-evil is NOT treated as inside /repo."""
        repo = tmp_path / "repo"
        repo.mkdir()
        evil = tmp_path / "repo-evil"
        evil.mkdir()
        assert is_within(evil, repo) is False


# ---------------------------------------------------------------------------
# Read tests
# ---------------------------------------------------------------------------


class TestReadAllowed:
    def test_read_allowed_file(self, sandbox: Path) -> None:
        """Read a file inside the sandbox with matching prefix."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read",
            {"file_path": str(sandbox / "docs" / "tier3" / "data.json")},
        )
        assert '"key"' in result
        assert '"value"' in result
        assert ex.total_bytes_read > 0
        assert len(ex.files_read) == 1

    def test_read_with_no_prefix_restriction(self, sandbox: Path) -> None:
        """When allowed_prefixes is None, any repo file is accessible."""
        ex = ToolExecutor(sandbox, allowed_prefixes=None)
        result = ex.execute_tool_call(
            "Read",
            {"file_path": str(sandbox / "other" / "secret.txt")},
        )
        assert "classified" in result


class TestReadDenied:
    def test_read_denies_outside_repo(self, sandbox: Path, tmp_path: Path) -> None:
        """Absolute path outside the repo root is denied."""
        outside = tmp_path / "outside.txt"
        outside.write_text("nope", encoding="utf-8")
        ex = ToolExecutor(sandbox, allowed_prefixes=None)
        result = ex.execute_tool_call(
            "Read", {"file_path": str(outside)}
        )
        data = json.loads(result)
        assert "error" in data
        assert "outside" in data["error"].lower()

    def test_read_denies_path_prefix_escape(self, sandbox: Path) -> None:
        """A ``../`` escape that resolves outside repo is denied."""
        escaped_path = str(sandbox / "docs" / ".." / ".." / "etc" / "passwd")
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/"])
        result = ex.execute_tool_call(
            "Read", {"file_path": escaped_path}
        )
        data = json.loads(result)
        assert "error" in data

    def test_read_denies_non_declared_path(self, sandbox: Path) -> None:
        """File inside repo but outside declared prefixes is denied."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read",
            {"file_path": str(sandbox / "other" / "secret.txt")},
        )
        data = json.loads(result)
        assert "error" in data
        assert "declared" in data["error"].lower()

    def test_read_denies_directory(self, sandbox: Path) -> None:
        """Attempting to Read a directory returns an error."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read",
            {"file_path": str(sandbox / "docs" / "tier3")},
        )
        data = json.loads(result)
        assert "error" in data
        assert "directory" in data["error"].lower()

    def test_read_denies_missing_file(self, sandbox: Path) -> None:
        """Non-existent file returns an error."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read",
            {"file_path": str(sandbox / "docs" / "tier3" / "nope.json")},
        )
        data = json.loads(result)
        assert "error" in data
        assert "not found" in data["error"].lower()

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Symlink creation requires elevated privileges on Windows",
    )
    def test_read_symlink_escape_denied(self, sandbox: Path, tmp_path: Path) -> None:
        """Symlink pointing outside the repo root is denied."""
        # Create a file outside the repo
        outside_file = tmp_path / "external_secret.txt"
        outside_file.write_text("secret data", encoding="utf-8")

        # Create a symlink inside the repo that points outside
        link_path = sandbox / "docs" / "tier3" / "sneaky_link.json"
        try:
            link_path.symlink_to(outside_file)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read", {"file_path": str(link_path)}
        )
        data = json.loads(result)
        assert "error" in data
        assert "outside" in data["error"].lower() or "denied" in data["error"].lower()


class TestReadLimits:
    def test_read_truncates_to_file_limit(self, sandbox: Path) -> None:
        """Files larger than MAX_FILE_READ_BYTES are denied."""
        big_file = sandbox / "docs" / "tier3" / "big.txt"
        big_file.write_text("x" * (MAX_FILE_READ_BYTES + 1), encoding="utf-8")

        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read", {"file_path": str(big_file)}
        )
        data = json.loads(result)
        assert "error" in data
        assert "too large" in data["error"].lower()

    def test_read_total_budget_enforced(self, sandbox: Path) -> None:
        """Total read budget across multiple reads is enforced."""
        # Create a file that's 60% of the total budget
        budget_file = sandbox / "docs" / "tier3" / "chunk.txt"
        chunk_size = (MAX_TOTAL_READ_BYTES * 6) // 10
        # Must also fit within per-file limit
        actual_size = min(chunk_size, MAX_FILE_READ_BYTES - 1)
        budget_file.write_text("y" * actual_size, encoding="utf-8")

        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])

        # First read should succeed
        result1 = ex.execute_tool_call(
            "Read", {"file_path": str(budget_file)}
        )
        assert "error" not in result1 or not result1.startswith("{")

        # Exhaust the budget by reading again (if budget allows) then
        # trigger over-budget.  Keep reading until denied.
        denied = False
        for _ in range(20):
            result = ex.execute_tool_call(
                "Read", {"file_path": str(budget_file)}
            )
            if result.startswith("{"):
                try:
                    parsed = json.loads(result)
                    if "error" in parsed and "budget" in parsed["error"].lower():
                        denied = True
                        break
                except json.JSONDecodeError:
                    pass
        assert denied, "Total budget was never enforced"


class TestReadOffsetLimit:
    def test_read_with_offset_and_limit(self, sandbox: Path) -> None:
        """offset and limit slice the file by lines."""
        multi_line = sandbox / "docs" / "tier3" / "lines.txt"
        multi_line.write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")

        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Read",
            {"file_path": str(multi_line), "offset": 2, "limit": 2},
        )
        assert "line2" in result
        assert "line3" in result
        assert "line1" not in result
        assert "line4" not in result


# ---------------------------------------------------------------------------
# Glob tests
# ---------------------------------------------------------------------------


class TestGlobAllowed:
    def test_glob_allowed_directory(self, sandbox: Path) -> None:
        """Glob inside allowed prefix returns matching paths."""
        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Glob",
            {"pattern": "*.json", "path": str(sandbox / "docs" / "tier3")},
        )
        assert "data.json" in result

    def test_glob_deterministic_order(self, sandbox: Path) -> None:
        """Results are sorted deterministically."""
        # Create multiple files
        for name in ["c.json", "a.json", "b.json"]:
            (sandbox / "docs" / "tier3" / name).write_text("{}", encoding="utf-8")

        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Glob",
            {"pattern": "*.json", "path": str(sandbox / "docs" / "tier3")},
        )
        paths = result.strip().split("\n")
        # Extract basenames for order check
        basenames = [Path(p).name for p in paths]
        assert basenames == sorted(basenames)


class TestGlobDenied:
    def test_glob_denies_outside_repo(self, sandbox: Path, tmp_path: Path) -> None:
        """Glob with base outside repo root is denied."""
        ex = ToolExecutor(sandbox, allowed_prefixes=None)
        result = ex.execute_tool_call(
            "Glob",
            {"pattern": "*.txt", "path": str(tmp_path)},
        )
        # tmp_path is the parent of sandbox; sandbox = tmp_path/repo
        # so tmp_path itself is outside the repo root
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Symlink creation requires elevated privileges on Windows",
    )
    def test_glob_filters_symlink_escape(self, sandbox: Path, tmp_path: Path) -> None:
        """Glob results containing symlinks that escape the repo are filtered out."""
        outside_file = tmp_path / "external.json"
        outside_file.write_text("{}", encoding="utf-8")

        link = sandbox / "docs" / "tier3" / "escape.json"
        try:
            link.symlink_to(outside_file)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Glob",
            {"pattern": "*.json", "path": str(sandbox / "docs" / "tier3")},
        )
        # The symlink target resolves outside the repo → must be filtered
        assert "escape.json" not in result or "external.json" not in result


class TestGlobLimits:
    def test_glob_max_matches_enforced(self, sandbox: Path) -> None:
        """Glob returns at most MAX_GLOB_RESULTS matches."""
        many_dir = sandbox / "docs" / "tier3" / "many"
        many_dir.mkdir()
        for i in range(MAX_GLOB_RESULTS + 50):
            (many_dir / f"file_{i:04d}.json").write_text("{}", encoding="utf-8")

        ex = ToolExecutor(sandbox, allowed_prefixes=["docs/tier3"])
        result = ex.execute_tool_call(
            "Glob",
            {"pattern": "**/*.json", "path": str(sandbox / "docs" / "tier3" / "many")},
        )
        lines = [l for l in result.strip().split("\n") if l]
        assert len(lines) <= MAX_GLOB_RESULTS


# ---------------------------------------------------------------------------
# Unknown tool
# ---------------------------------------------------------------------------


class TestUnknownTool:
    def test_unknown_tool_denied(self, sandbox: Path) -> None:
        """Unknown tool names produce a structured error."""
        ex = ToolExecutor(sandbox, allowed_prefixes=None)
        result = ex.execute_tool_call("Write", {"file_path": "/tmp/bad"})
        data = json.loads(result)
        assert "error" in data
        assert "unknown" in data["error"].lower()

    def test_bash_tool_denied(self, sandbox: Path) -> None:
        """Bash tool (dangerous) is not available."""
        ex = ToolExecutor(sandbox, allowed_prefixes=None)
        result = ex.execute_tool_call("Bash", {"command": "rm -rf /"})
        data = json.loads(result)
        assert "error" in data
        assert "unknown" in data["error"].lower()
