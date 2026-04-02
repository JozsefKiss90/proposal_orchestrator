"""
Step 3 — File predicates.
Step 10 extension — artifact_owned_by_run.

Implements the four pure filesystem predicates defined in
gate_rules_library_plan.md §4.1:

    exists(path)
    non_empty(path)
    non_empty_json(path)
    dir_non_empty(path)

Step 10 adds:

    artifact_owned_by_run(path, run_id, *, reuse_policy_path=None, repo_root=None)

All functions accept a ``repo_root`` keyword argument.  Paths that are
relative strings are resolved via ``runner.paths.resolve_repo_path``.
Absolute paths are used unchanged.

Design constraints (from gate_rules_library_plan.md §4.1 and the Step 3
implementation brief):

* No YAML loading, no manifest traversal, no agent invocation, no
  provenance classification, no run_id logic, no GateResult writing.
* These predicates are stateless.  They read from the filesystem only.
* UTF-8 is the mandatory encoding for JSON reading.  Byte-order marks
  (BOM) are stripped via ``utf-8-sig`` encoding.
* ``dir_non_empty`` scans direct children only (non-recursive).  There
  is no existing runner convention for recursive scanning; this is the
  deliberate default.  See the function docstring.

Policy note
-----------
``dir_non_empty`` is a coarse presence check reserved for
externally-supplied source directories and integration directories where
no single canonical file can be mandated.  The gate_rules_library.yaml
header and artifact_schema_specification.yaml (§ directory exception
note) document which directory paths are permitted uses of this predicate.
Predicate implementations do not enforce that policy; the library YAML
and its review process do.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from runner.paths import resolve_repo_path
from runner.predicates.types import (
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    STALE_UPSTREAM_MISMATCH,
    PredicateResult,
)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# exists
# ---------------------------------------------------------------------------


def exists(path: PathLike, *, repo_root: Optional[Path] = None) -> PredicateResult:
    """
    Pass iff *path* exists (file or directory).

    Contract (gate_rules_library_plan.md §4.1)
    -------------------------------------------
    Pass condition: the path exists (file or directory).

    Failure category: ``MISSING_MANDATORY_INPUT`` — the required path is
    absent from the filesystem.

    Parameters
    ----------
    path:
        Repository-relative or absolute path string / ``Path``.
    repo_root:
        Repository root used to resolve relative paths.  When ``None``
        the path is resolved relative to ``os.getcwd()``.
    """
    resolved = resolve_repo_path(path, repo_root)
    if resolved.exists():
        return PredicateResult(
            passed=True,
            details={
                "path": str(resolved),
                "is_file": resolved.is_file(),
                "is_dir": resolved.is_dir(),
            },
        )
    return PredicateResult(
        passed=False,
        failure_category=MISSING_MANDATORY_INPUT,
        reason=f"Path does not exist: {resolved}",
        details={"path": str(resolved)},
    )


# ---------------------------------------------------------------------------
# non_empty
# ---------------------------------------------------------------------------


def non_empty(path: PathLike, *, repo_root: Optional[Path] = None) -> PredicateResult:
    """
    Pass iff *path* exists, is a regular file, and has byte size > 0.

    Contract (gate_rules_library_plan.md §4.1)
    -------------------------------------------
    Pass condition: path exists AND is a file AND byte size > 0.

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Path exists but is a directory (not a file), or is a zero-byte
        file.  The artifact is present but not in the expected form.

    Parameters
    ----------
    path:
        Repository-relative or absolute path string / ``Path``.
    repo_root:
        Repository root used to resolve relative paths.
    """
    resolved = resolve_repo_path(path, repo_root)

    if not resolved.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Path does not exist: {resolved}",
            details={"path": str(resolved)},
        )

    if resolved.is_dir():
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Expected a regular file but found a directory: {resolved}.  "
                "non_empty must not be called on directory paths."
            ),
            details={"path": str(resolved), "is_dir": True},
        )

    size = resolved.stat().st_size
    if size == 0:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"File exists but is zero bytes: {resolved}",
            details={"path": str(resolved), "size_bytes": 0},
        )

    return PredicateResult(
        passed=True,
        details={"path": str(resolved), "size_bytes": size},
    )


# ---------------------------------------------------------------------------
# non_empty_json
# ---------------------------------------------------------------------------


def non_empty_json(
    path: PathLike, *, repo_root: Optional[Path] = None
) -> PredicateResult:
    """
    Pass iff *path* is a readable file containing valid, non-empty JSON.

    Contract (gate_rules_library_plan.md §4.1)
    -------------------------------------------
    Pass condition:
        * path exists
        * path is a file (not a directory)
        * file content is valid UTF-8
        * file content parses as JSON without error
        * parsed value is **not** ``null``, ``{}``, or ``[]``

    Scalar JSON values (string, number, boolean)
    --------------------------------------------
    The contract enumerates only ``null``, ``{}``, and ``[]`` as failing
    values.  A bare JSON scalar (e.g. ``"hello"``, ``42``, ``true``)
    therefore passes this predicate.  In practice every canonical
    artifact in this system is a JSON object, so the scalar case should
    never arise for gate-relevant files; it is permitted rather than
    excluded to avoid divergence from the literal contract.

    Encoding
    --------
    Files are read as UTF-8.  The ``utf-8-sig`` variant is used so that
    a leading byte-order mark is silently stripped rather than treated as
    a parse error.  Any ``UnicodeDecodeError`` is reported as
    ``MALFORMED_ARTIFACT``.

    JSON parsing
    ------------
    Strict: ``json.loads`` with no extra flags.  Type coercion is not
    performed.  Parse errors are reported verbatim as ``MALFORMED_ARTIFACT``.

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist.
    ``MALFORMED_ARTIFACT``
        Path is a directory; file is empty or whitespace-only; file is
        not valid UTF-8; file contains invalid JSON; or parsed value is
        ``null``, ``{}``, or ``[]``.

    Parameters
    ----------
    path:
        Repository-relative or absolute path string / ``Path``.
    repo_root:
        Repository root used to resolve relative paths.
    """
    resolved = resolve_repo_path(path, repo_root)

    if not resolved.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Path does not exist: {resolved}",
            details={"path": str(resolved)},
        )

    if resolved.is_dir():
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Expected a JSON file but found a directory: {resolved}.  "
                "non_empty_json must not be called on directory paths."
            ),
            details={"path": str(resolved), "is_dir": True},
        )

    # UTF-8 read; utf-8-sig strips BOM silently
    try:
        text = resolved.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"File is not valid UTF-8: {exc}",
            details={"path": str(resolved), "encoding_error": str(exc)},
        )

    if not text.strip():
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"File is empty (no non-whitespace content): {resolved}",
            details={"path": str(resolved), "size_bytes": resolved.stat().st_size},
        )

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Invalid JSON in {resolved}: {exc}",
            details={
                "path": str(resolved),
                "json_error": str(exc),
                "error_line": exc.lineno,
                "error_col": exc.colno,
            },
        )

    # Empty structured values fail even though they are technically valid JSON
    if parsed is None or parsed == {} or parsed == []:
        parsed_repr = repr(parsed)
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"JSON parsed to empty structured value ({parsed_repr}): {resolved}.  "
                "Artifact must contain substantive content."
            ),
            details={
                "path": str(resolved),
                "parsed_type": type(parsed).__name__,
                "empty_value": parsed_repr,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved),
            "parsed_type": type(parsed).__name__,
        },
    )


# ---------------------------------------------------------------------------
# dir_non_empty
# ---------------------------------------------------------------------------


def dir_non_empty(
    path: PathLike, *, repo_root: Optional[Path] = None
) -> PredicateResult:
    """
    Pass iff *path* is a directory containing at least one non-empty file.

    Contract (gate_rules_library_plan.md §4.1)
    -------------------------------------------
    Pass condition:
        * path exists
        * path is a directory
        * directory contains at least one direct-child file with byte
          size > 0

    Scan depth
    ----------
    This predicate scans **direct children only** (non-recursive).
    There is no existing runner convention for recursive scanning in this
    repository.  Subdirectories within *path* are not descended into and
    do not contribute to the "non-empty" determination.  If the directory
    contains only subdirectories and no files, the predicate fails.

    Policy note
    -----------
    This predicate is a coarse presence check.  Its permitted uses are
    restricted to externally-supplied source directories and integration
    directories where no single canonical file can be mandated.
    Permitted directory paths are listed in gate_rules_library.yaml
    (header comments) and artifact_schema_specification.yaml.  This
    function does not enforce that policy; it evaluates the path it is
    given.

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        Path does not exist; or path is a file where a directory is
        expected; or directory exists but contains no direct-child files
        with size > 0.  In all these cases the required usable input is
        absent.

    Parameters
    ----------
    path:
        Repository-relative or absolute path string / ``Path``.
    repo_root:
        Repository root used to resolve relative paths.
    """
    resolved = resolve_repo_path(path, repo_root)

    if not resolved.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Path does not exist: {resolved}",
            details={"path": str(resolved)},
        )

    if not resolved.is_dir():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=(
                f"Expected a directory but found a file: {resolved}.  "
                "The required source directory is absent."
            ),
            details={"path": str(resolved), "is_file": True},
        )

    # Scan direct children only (non-recursive by design — see docstring)
    children = list(resolved.iterdir())
    non_empty_files = [
        child
        for child in children
        if child.is_file() and child.stat().st_size > 0
    ]

    if not non_empty_files:
        all_files = [c for c in children if c.is_file()]
        if not all_files:
            reason = (
                f"Directory exists but contains no files in direct children "
                f"({len(children)} total children, none are files): {resolved}"
            )
        else:
            reason = (
                f"Directory contains {len(all_files)} file(s) but all are "
                f"zero bytes (direct children only): {resolved}"
            )
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=reason,
            details={
                "path": str(resolved),
                "total_children": len(children),
                "file_count": len(all_files),
                "non_empty_file_count": 0,
            },
        )

    return PredicateResult(
        passed=True,
        details={
            "path": str(resolved),
            "non_empty_file_count": len(non_empty_files),
        },
    )


# ---------------------------------------------------------------------------
# artifact_owned_by_run  (Step 10)
# ---------------------------------------------------------------------------


def artifact_owned_by_run(
    path: PathLike,
    run_id: str,
    *,
    reuse_policy_path: Optional[PathLike] = None,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """
    Verify that a canonical artifact was produced by the current run.

    Contract (gate_rules_library_plan.md §7 and Step 10)
    ------------------------------------------------------
    Pass conditions:
        * path exists and is a readable JSON file
        * the artifact's top-level ``run_id`` field equals *run_id*, OR
        * the artifact path appears in the reuse policy's ``approved_artifacts``
          list (approved inherited artifact from a prior run)

    Failure categories
    ------------------
    ``MISSING_MANDATORY_INPUT``
        The artifact file does not exist.
    ``MALFORMED_ARTIFACT``
        The file cannot be read or parsed as a JSON object.
    ``STALE_UPSTREAM_MISMATCH``
        The artifact exists but its ``run_id`` does not match the current
        run and it has not been approved in the reuse policy.

    Reuse policy
    ------------
    When *reuse_policy_path* is provided and the artifact's run_id mismatches,
    the predicate checks ``approved_artifacts`` in the reuse policy JSON.
    If the path appears there (as a string key, matched against the resolved
    path or the original path argument), the predicate passes with an
    ``approved_via_reuse_policy: true`` flag in details.

    Parameters
    ----------
    path:
        Repository-relative or absolute path to the canonical artifact file.
    run_id:
        The current run's UUID string.
    reuse_policy_path:
        Optional path to the run's ``reuse_policy.json`` file.
    repo_root:
        Repository root for resolving relative paths.
    """
    resolved = resolve_repo_path(path, repo_root)

    if not resolved.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=f"Artifact not found: {resolved}",
            details={"path": str(resolved)},
        )

    if resolved.is_dir():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=(
                f"Expected a JSON artifact file but found a directory: {resolved}.  "
                "artifact_owned_by_run requires a canonical artifact file path."
            ),
            details={"path": str(resolved), "is_dir": True},
        )

    try:
        text = resolved.read_text(encoding="utf-8-sig")
        artifact = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Cannot read artifact as JSON: {exc}",
            details={"path": str(resolved), "error": str(exc)},
        )

    if not isinstance(artifact, dict):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Artifact top-level value must be a JSON object; "
                f"got {type(artifact).__name__}: {resolved}"
            ),
            details={"path": str(resolved), "actual_type": type(artifact).__name__},
        )

    artifact_run_id = artifact.get("run_id")
    if artifact_run_id == run_id:
        return PredicateResult(
            passed=True,
            details={"path": str(resolved), "run_id": run_id},
        )

    # Mismatch: check reuse policy before failing
    if reuse_policy_path is not None:
        policy_resolved = resolve_repo_path(reuse_policy_path, repo_root)
        if policy_resolved.exists():
            try:
                policy = json.loads(
                    policy_resolved.read_text(encoding="utf-8-sig")
                )
                approved: list = policy.get("approved_artifacts", [])
                # Match against original path arg or resolved path string
                if str(path) in approved or str(resolved) in approved:
                    return PredicateResult(
                        passed=True,
                        details={
                            "path": str(resolved),
                            "approved_via_reuse_policy": True,
                            "artifact_run_id": artifact_run_id,
                            "current_run_id": run_id,
                        },
                    )
            except Exception:
                pass  # policy read failure falls through to stale mismatch

    return PredicateResult(
        passed=False,
        failure_category=STALE_UPSTREAM_MISMATCH,
        reason=(
            f"Artifact run_id {artifact_run_id!r} does not match current run "
            f"{run_id!r}: {resolved}.  Re-run the producing phase under the "
            "current run_id, or add this artifact path to the reuse policy's "
            "approved_artifacts list."
        ),
        details={
            "path": str(resolved),
            "artifact_run_id": artifact_run_id,
            "expected_run_id": run_id,
        },
    )
