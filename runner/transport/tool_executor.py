"""
Local Read/Glob tool executor for TAPM compatibility.

Emulates the file-access tools that Claude Code provides natively when
invoked with ``--tools "Read,Glob"``.  This executor is used by
non-Claude LLM backends (Ollama, vLLM, TGI) where the tool loop must
be managed externally by the Python runtime.

Security invariants
-------------------
These invariants are constitutional requirements (CLAUDE.md §17) and
must hold for every code path in this module:

1.  **Tool execution is Python-side only.**  The LLM never receives
    unrestricted filesystem access.  It emits tool-call requests; this
    module decides whether to honour them.

2.  **The model may only request Read/Glob on declared input roots.**
    When ``allowed_prefixes`` is provided (always for TAPM skills),
    only paths matching the skill's ``reads_from`` declaration are
    accessible.

3.  **The executor performs all path authorisation after resolving
    symlinks.**  Symlinks that escape the repository root or the
    declared-input boundary are denied.

4.  **No Write/Edit/Delete tool exists.**  This module provides
    read-only filesystem access.  Artifact writes remain exclusively
    the responsibility of the Python skill runtime
    (``skill_runtime._atomic_write``).

5.  **Tool errors are returned as structured JSON values, not silently
    ignored.**  Every denial produces a ``{"error": "..."}`` response
    that the LLM receives as a tool result.

6.  **Gate evaluation and artifact writes remain outside the tool
    executor.**  This module has no knowledge of gates, schemas,
    SkillResult, or the DAG scheduler.

Authoritative source:
    docs/internal_llm_migration_plan.md §5 (TAPM Compatibility)
"""

from __future__ import annotations

import glob as glob_module
import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maximum bytes returned by a single Read call.
MAX_FILE_READ_BYTES: int = 512_000  # 500 KB

#: Maximum cumulative bytes read across all Read calls in one executor
#: instance (one skill invocation).
MAX_TOTAL_READ_BYTES: int = 5_000_000  # 5 MB

#: Maximum number of paths returned by a single Glob call.
MAX_GLOB_RESULTS: int = 200

#: Tool names recognised by the executor.
KNOWN_TOOLS: frozenset[str] = frozenset({"Read", "Glob"})

#: OpenAI function-calling tool schemas for Read and Glob.
#: Provided to LLM backends that require explicit tool definitions.
READ_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Read",
        "description": (
            "Read a file from the local filesystem. Returns file content "
            "as text. The file_path must be an absolute path."
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
                    "description": (
                        "Line number to start reading from (1-based). "
                        "Optional."
                    ),
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

GLOB_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Glob",
        "description": (
            "Find files matching a glob pattern in a directory. "
            "Returns a newline-separated list of matching absolute paths."
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
                    "description": (
                        "Directory to search in. Must be an absolute path. "
                        "Defaults to the repository root if omitted."
                    ),
                },
            },
            "required": ["pattern"],
        },
    },
}


# ---------------------------------------------------------------------------
# Path safety helpers
# ---------------------------------------------------------------------------


def is_within(path: Path, root: Path) -> bool:
    """Return ``True`` when *path* (resolved) is inside *root* (resolved).

    Uses :meth:`pathlib.Path.relative_to` which raises ``ValueError``
    when *path* is not a sub-path of *root*.  This is safe against
    ``../`` escapes and symlink traversal because both sides are
    ``.resolve()``-d first.

    **Do not** replace this with ``str(path).startswith(str(root))``
    which is vulnerable to prefix collisions (e.g. ``/repo-evil``
    matching ``/repo``).
    """
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _make_error(message: str) -> str:
    """Return a deterministic JSON error string."""
    return json.dumps({"error": message}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# ToolExecutor
# ---------------------------------------------------------------------------


class ToolExecutor:
    """Executes Read and Glob tool calls within a sandboxed repository.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root.  All file access is
        confined to this tree.
    allowed_prefixes:
        Optional list of repo-relative path prefixes.  When provided,
        only paths whose resolved location falls within one of these
        prefix subtrees (relative to *repo_root*) are accessible.
        This enforces the TAPM declared-input boundary.  When ``None``,
        any path inside the repo root is allowed (used for testing or
        non-TAPM invocations).
    """

    def __init__(
        self,
        repo_root: Path,
        allowed_prefixes: list[str] | None = None,
    ) -> None:
        self._repo_root: Path = repo_root.resolve()
        self._allowed_prefixes: list[str] | None = allowed_prefixes
        self._total_bytes_read: int = 0
        self._files_read: list[str] = []

    # -- public API --------------------------------------------------------

    def execute_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a single tool call and return the result as a string.

        Unknown tool names produce a structured JSON error.
        """
        if tool_name == "Read":
            return self._execute_read(arguments)
        if tool_name == "Glob":
            return self._execute_glob(arguments)
        return _make_error(f"Unknown tool: {tool_name!r}")

    @property
    def total_bytes_read(self) -> int:
        return self._total_bytes_read

    @property
    def files_read(self) -> list[str]:
        """Paths of files successfully read (for audit logging)."""
        return list(self._files_read)

    # -- Read --------------------------------------------------------------

    def _execute_read(self, arguments: dict[str, Any]) -> str:
        file_path_str = arguments.get("file_path")
        if not isinstance(file_path_str, str) or not file_path_str.strip():
            return _make_error("file_path is required and must be a non-empty string")

        offset = arguments.get("offset")
        limit = arguments.get("limit")

        # Resolve the raw path.  If relative, anchor to repo_root so
        # that repo-relative paths sent by the model still work.
        raw_path = Path(file_path_str)
        if not raw_path.is_absolute():
            raw_path = self._repo_root / raw_path

        try:
            resolved = raw_path.resolve()
        except (ValueError, OSError):
            return _make_error(f"Invalid path: {file_path_str}")

        # Sandbox: must be inside repo root
        if not is_within(resolved, self._repo_root):
            return _make_error(
                "Access denied: path is outside the repository boundary"
            )

        # Declared-input boundary
        if self._allowed_prefixes is not None:
            if not self._is_in_allowed_prefixes(resolved):
                return _make_error(
                    "Access denied: path is not in the declared inputs. "
                    "Read only files listed in the Declared Inputs section."
                )

        # Must be a regular file (not a directory)
        if resolved.is_dir():
            return _make_error(
                f"Access denied: path is a directory, not a file: "
                f"{file_path_str}"
            )

        if not resolved.is_file():
            return _make_error(f"File not found: {file_path_str}")

        # Per-file size guard
        try:
            file_size = resolved.stat().st_size
        except OSError as exc:
            return _make_error(f"Cannot stat file: {exc}")

        if file_size > MAX_FILE_READ_BYTES:
            return _make_error(
                f"File too large ({file_size} bytes, "
                f"limit {MAX_FILE_READ_BYTES})"
            )

        # Total budget guard
        if self._total_bytes_read + file_size > MAX_TOTAL_READ_BYTES:
            return _make_error(
                f"Total read budget exceeded "
                f"({MAX_TOTAL_READ_BYTES} bytes)"
            )

        # Read file content
        try:
            content = resolved.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            # Fall back to latin-1 for binary-ish files
            try:
                content = resolved.read_text(encoding="latin-1")
            except OSError as exc:
                return _make_error(f"Cannot read file: {exc}")
        except OSError as exc:
            return _make_error(f"Cannot read file: {exc}")

        # Truncate to byte limit (content is text; approximate via
        # encode length — cheaper than reading as bytes first)
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > MAX_FILE_READ_BYTES:
            # Truncate conservatively
            content = content[: MAX_FILE_READ_BYTES]
            content_bytes = len(content.encode("utf-8"))

        self._total_bytes_read += content_bytes
        self._files_read.append(str(resolved))

        # Apply line-based offset/limit (matches Claude Code Read)
        if offset is not None or limit is not None:
            lines = content.splitlines(keepends=True)
            start = (offset - 1) if offset and offset > 0 else 0
            end = (start + limit) if limit else None
            content = "".join(lines[start:end])

        return content

    # -- Glob --------------------------------------------------------------

    def _execute_glob(self, arguments: dict[str, Any]) -> str:
        pattern = arguments.get("pattern")
        if not isinstance(pattern, str) or not pattern.strip():
            return _make_error(
                "pattern is required and must be a non-empty string"
            )

        search_path_str = arguments.get("path")
        if search_path_str:
            base = Path(search_path_str)
            if not base.is_absolute():
                base = self._repo_root / base
        else:
            base = self._repo_root

        try:
            base_resolved = base.resolve()
        except (ValueError, OSError):
            return _make_error(f"Invalid search path: {search_path_str}")

        # Sandbox: base must be inside repo root
        if not is_within(base_resolved, self._repo_root):
            return _make_error(
                "Access denied: search path is outside the repository boundary"
            )

        # Declared-input boundary: base must fall within an allowed prefix
        if self._allowed_prefixes is not None:
            if not self._is_in_allowed_prefixes(base_resolved):
                return _make_error(
                    "Access denied: search path is not in the declared inputs"
                )

        # Execute glob
        try:
            full_pattern = str(base_resolved / pattern)
            raw_matches = glob_module.glob(full_pattern, recursive=True)
        except (OSError, ValueError) as exc:
            return _make_error(f"Glob failed: {exc}")

        # Filter: resolve each match, keep only those inside sandbox AND
        # inside allowed prefixes (symlinks may escape)
        filtered: list[str] = []
        for m in raw_matches:
            try:
                m_resolved = Path(m).resolve()
            except (ValueError, OSError):
                continue
            if not is_within(m_resolved, self._repo_root):
                continue
            if self._allowed_prefixes is not None:
                if not self._is_in_allowed_prefixes(m_resolved):
                    continue
            filtered.append(str(m_resolved))

        # Deterministic order and limit
        filtered.sort()
        filtered = filtered[: MAX_GLOB_RESULTS]

        if not filtered:
            return "(no matches)"
        return "\n".join(filtered)

    # -- prefix check ------------------------------------------------------

    def _is_in_allowed_prefixes(self, resolved_path: Path) -> bool:
        """Check *resolved_path* falls within a declared allowed prefix.

        Uses :func:`is_within` (``relative_to``-based) for each prefix,
        not string-prefix matching.
        """
        assert self._allowed_prefixes is not None
        for prefix in self._allowed_prefixes:
            # Build the absolute path of the prefix root
            prefix_abs = (self._repo_root / prefix).resolve()
            # The prefix itself may be a file or a directory.
            # Allow exact match (file) or subtree containment (directory).
            if resolved_path == prefix_abs:
                return True
            if is_within(resolved_path, prefix_abs):
                return True
        return False
