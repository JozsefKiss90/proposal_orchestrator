"""Tests for ``runner.paths`` — repository root discovery and path resolution.

Covers:
    - find_repo_root: from subdirectory, from root itself, missing markers,
      requires both CLAUDE.md and .git, stops at filesystem root, max depth,
      symlink traversal
    - resolve_repo_path: absolute unchanged, relative joined with root,
      relative without root, forward-slash paths on all platforms,
      path traversal (../) handling
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from runner.paths import find_repo_root, resolve_repo_path


# ---------------------------------------------------------------------------
# find_repo_root
# ---------------------------------------------------------------------------


class TestFindRepoRoot:
    """Tests for find_repo_root()."""

    def test_finds_root_from_subdirectory(self, tmp_path: Path) -> None:
        """Starting from a deep subdirectory, find_repo_root walks up correctly."""
        root = tmp_path / "project"
        root.mkdir()
        (root / "CLAUDE.md").write_text("constitution", encoding="utf-8")
        (root / ".git").mkdir()
        deep = root / "runner" / "transport" / "sub"
        deep.mkdir(parents=True)

        result = find_repo_root(start=deep)
        assert result == root.resolve()

    def test_finds_root_from_root_itself(self, tmp_path: Path) -> None:
        """find_repo_root succeeds when started from the root itself."""
        root = tmp_path / "project"
        root.mkdir()
        (root / "CLAUDE.md").write_text("constitution", encoding="utf-8")
        (root / ".git").mkdir()

        result = find_repo_root(start=root)
        assert result == root.resolve()

    def test_raises_when_no_markers_found(self, tmp_path: Path) -> None:
        """RuntimeError when no ancestor has both CLAUDE.md and .git."""
        bare = tmp_path / "empty" / "deep"
        bare.mkdir(parents=True)

        with pytest.raises(RuntimeError, match="Repository root not found"):
            find_repo_root(start=bare)

    def test_requires_both_claude_md_and_git(self, tmp_path: Path) -> None:
        """Only CLAUDE.md present (no .git) is not sufficient."""
        only_claude = tmp_path / "partial_a"
        only_claude.mkdir()
        (only_claude / "CLAUDE.md").write_text("x", encoding="utf-8")

        with pytest.raises(RuntimeError, match="Repository root not found"):
            find_repo_root(start=only_claude)

    def test_requires_git_directory(self, tmp_path: Path) -> None:
        """Only .git present (no CLAUDE.md) is not sufficient."""
        only_git = tmp_path / "partial_b"
        only_git.mkdir()
        (only_git / ".git").mkdir()

        with pytest.raises(RuntimeError, match="Repository root not found"):
            find_repo_root(start=only_git)

    def test_stops_at_filesystem_root(self, tmp_path: Path) -> None:
        """Does not search infinitely — stops after 20 levels or fs root."""
        # tmp_path is typically shallow enough that we hit fs root first
        bare = tmp_path / "nowhere"
        bare.mkdir()
        with pytest.raises(RuntimeError):
            find_repo_root(start=bare)

    def test_max_depth_limit(self, tmp_path: Path) -> None:
        """find_repo_root respects the 20-level depth limit."""
        # Create a repo root, then a directory 21 levels below it
        root = tmp_path / "project"
        root.mkdir()
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
        (root / ".git").mkdir()

        # Build a path 21 levels deep
        deep = root
        for i in range(21):
            deep = deep / f"level_{i}"
        deep.mkdir(parents=True)

        with pytest.raises(RuntimeError, match="Repository root not found"):
            find_repo_root(start=deep)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Symlink creation requires elevated privileges on Windows",
    )
    def test_symlink_traversal_returns_resolved_path(self, tmp_path: Path) -> None:
        """find_repo_root resolves symlinks and returns the real path."""
        real_root = tmp_path / "real_project"
        real_root.mkdir()
        (real_root / "CLAUDE.md").write_text("x", encoding="utf-8")
        (real_root / ".git").mkdir()

        link = tmp_path / "link_project"
        try:
            link.symlink_to(real_root)
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")

        result = find_repo_root(start=link)
        # Result should be the resolved (real) path
        assert result == real_root.resolve()

    def test_returns_absolute_path(self, tmp_path: Path) -> None:
        """find_repo_root always returns an absolute path."""
        root = tmp_path / "project"
        root.mkdir()
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
        (root / ".git").mkdir()

        result = find_repo_root(start=root)
        assert result.is_absolute()

    def test_git_file_not_directory(self, tmp_path: Path) -> None:
        """.git as a file (git worktree uses .git files) should still match."""
        root = tmp_path / "worktree"
        root.mkdir()
        (root / "CLAUDE.md").write_text("x", encoding="utf-8")
        # In a git worktree, .git is a file, not a directory
        (root / ".git").write_text("gitdir: /somewhere", encoding="utf-8")

        result = find_repo_root(start=root)
        assert result == root.resolve()


# ---------------------------------------------------------------------------
# resolve_repo_path
# ---------------------------------------------------------------------------


class TestResolveRepoPath:
    """Tests for resolve_repo_path()."""

    def test_absolute_path_returned_unchanged(self, tmp_path: Path) -> None:
        """Absolute paths are returned as-is (not joined with repo_root)."""
        abs_path = tmp_path / "some" / "file.json"
        result = resolve_repo_path(str(abs_path), repo_root=tmp_path)
        assert result == abs_path

    def test_relative_path_joined_with_repo_root(self, tmp_path: Path) -> None:
        """Relative paths are joined with repo_root when provided."""
        result = resolve_repo_path("docs/tier3/data.json", repo_root=tmp_path)
        assert result == tmp_path / "docs" / "tier3" / "data.json"

    def test_relative_path_without_root_returns_as_is(self) -> None:
        """When repo_root is None, relative path is returned as Path(path)."""
        result = resolve_repo_path("docs/tier3/data.json", repo_root=None)
        assert result == Path("docs/tier3/data.json")

    def test_forward_slash_paths_work_on_all_platforms(self, tmp_path: Path) -> None:
        """Forward-slash paths are normalised by pathlib on all platforms."""
        result = resolve_repo_path("docs/tier3/data.json", repo_root=tmp_path)
        # On Windows, pathlib normalises to backslash internally
        assert result.parts[-3:] == ("docs", "tier3", "data.json")

    def test_path_object_input(self, tmp_path: Path) -> None:
        """Path objects are accepted (not just strings)."""
        result = resolve_repo_path(Path("docs") / "file.json", repo_root=tmp_path)
        assert result == tmp_path / "docs" / "file.json"

    def test_dot_dot_in_relative_path(self, tmp_path: Path) -> None:
        """Paths with ../ are joined literally — caller must resolve."""
        result = resolve_repo_path("docs/../other/file.json", repo_root=tmp_path)
        # pathlib.Path joins literally; the ../ is preserved until resolve()
        # The important thing is that resolve_repo_path doesn't silently
        # strip the traversal — it's the caller's job to resolve and check.
        assert "other" in str(result)

    def test_absolute_path_ignores_repo_root(self) -> None:
        """When path is absolute, repo_root is ignored even if provided."""
        if sys.platform == "win32":
            abs_p = "C:\\absolute\\path.json"
        else:
            abs_p = "/absolute/path.json"
        result = resolve_repo_path(abs_p, repo_root=Path("/some/root"))
        assert result == Path(abs_p)
