"""
Path resolution utilities for the DAG runner.

All artifact paths in gate_rules_library.yaml are repository-relative strings,
e.g. "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json".
This module resolves them to absolute filesystem paths in a deterministic,
OS-agnostic way using pathlib.

No path resolution should be performed inline inside predicate functions.
All predicates call ``resolve_repo_path`` with an explicit ``repo_root``
argument supplied by the caller (typically the runner's ``evaluate_gate``
function, which establishes the root at DAG startup).
"""

from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]


def find_repo_root(start: Optional[Path] = None) -> Path:
    """
    Locate the repository root by walking up from *start* (default: cwd).

    The root is identified as the first ancestor directory that contains
    both ``CLAUDE.md`` and ``.git/``.  Both markers must be present to
    avoid false positives in deeply nested checkouts.

    Parameters
    ----------
    start:
        Starting directory for the upward search.  If ``None``, the
        current working directory is used.

    Returns
    -------
    Path
        Absolute path to the repository root.

    Raises
    ------
    RuntimeError
        If no matching directory is found within 20 levels of *start*.
    """
    candidate = (start or Path.cwd()).resolve()
    for _ in range(20):
        if (candidate / "CLAUDE.md").exists() and (candidate / ".git").exists():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            # filesystem root reached without finding the repo
            break
        candidate = parent
    raise RuntimeError(
        "Repository root not found: no ancestor directory contains both "
        f"CLAUDE.md and .git/.  Search started at: {start or Path.cwd()}"
    )


def resolve_repo_path(path: PathLike, repo_root: Optional[Path] = None) -> Path:
    """
    Resolve *path* to an absolute ``Path``.

    Rules
    -----
    * If *path* is already absolute, return it unchanged.
    * If *path* is relative and *repo_root* is provided, return
      ``repo_root / path``.
    * If *path* is relative and *repo_root* is ``None``, return
      ``Path(path)`` as-is — the caller is responsible for ensuring
      ``os.getcwd()`` is the repository root, or for always passing an
      explicit root.

    Separators in string paths are normalised by ``pathlib``; no manual
    ``os.sep`` handling is required.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    if repo_root is not None:
        return repo_root / p
    return p
