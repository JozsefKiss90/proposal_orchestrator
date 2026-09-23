"""
Deterministic content fingerprints for gate input artifacts.

This is the single source of truth for how an input artifact is reduced to a
content fingerprint.  It is imported by both the *writer* side
(:mod:`runner.gate_evaluator`, which records ``input_artifact_fingerprints``
in every gate result at evaluation time) and the *reader* side
(:func:`runner.predicates.gate_pass_predicates.is_gate_fresh`, which recomputes
the current fingerprint of an upstream input to decide whether a gate result is
stale by *content* rather than wall-clock mtime — ST-1).

The writer and reader **must** hash identically: if they diverged, a
content-identical file would spuriously mismatch its recorded fingerprint and a
fresh gate would be judged stale.  Keeping the algorithm in one module makes
that divergence structurally impossible.

The helper cannot live in :mod:`runner.gate_evaluator` because
``gate_evaluator`` imports ``gate_pass_recorded`` from
``runner.predicates.gate_pass_predicates`` — importing the helper back from
``gate_evaluator`` would form an import cycle.  This module depends only on
``runner.paths`` (a leaf) and the standard library.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from runner.paths import resolve_repo_path

# Fingerprint recorded for a path that does not exist at hashing time.  A path
# transitioning to/from this sentinel is a real content change (an input
# appeared or disappeared) and therefore invalidates freshness.
MISSING_FINGERPRINT = "sha256:MISSING"


def fingerprint_path(path: Path) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of *path*.

    * **File**: SHA-256 of raw file bytes.
    * **Directory**: SHA-256 of a JSON-encoded sorted list of direct-child
      names (non-recursive).  This detects additions and removals of direct
      children but not changes inside subdirectories.
    * **Missing**: returns :data:`MISSING_FINGERPRINT` rather than raising, so
      fingerprinting never blocks gate evaluation or freshness checking.
    """
    if not path.exists():
        return MISSING_FINGERPRINT
    if path.is_dir():
        entries = sorted(p.name for p in path.iterdir())
        content = json.dumps(entries).encode("utf-8")
    else:
        content = path.read_bytes()
    return "sha256:" + hashlib.sha256(content).hexdigest()


def compute_fingerprints(
    artifact_paths: list[str],
    repo_root: Optional[Path],
) -> tuple[dict[str, str], str]:
    """
    Compute per-artifact fingerprints and a combined fingerprint.

    Parameters
    ----------
    artifact_paths:
        List of repo-relative (or absolute) path strings.
    repo_root:
        Repository root for resolving relative paths.

    Returns
    -------
    per_artifact:
        ``{path_string: "sha256:<hex>"}`` mapping, stable-sorted by path.
    combined:
        A single SHA-256 fingerprint derived from the stable JSON encoding
        of *per_artifact*.  Used for the ``input_fingerprint`` field.
    """
    per_artifact: dict[str, str] = {}
    for p in sorted(artifact_paths):  # sort for stability
        resolved = resolve_repo_path(p, repo_root)
        per_artifact[p] = fingerprint_path(resolved)

    combined_bytes = json.dumps(per_artifact, sort_keys=True).encode("utf-8")
    combined = "sha256:" + hashlib.sha256(combined_bytes).hexdigest()
    return per_artifact, combined
