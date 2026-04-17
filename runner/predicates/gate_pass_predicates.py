"""
Gate-pass predicate: gate_pass_recorded.

Confirms that a gate result artifact exists at its canonical path (§6.3 of
artifact_schema_specification.yaml), records status: pass, carries a run_id
that matches the current run, has an input_fingerprint field, and has an
evaluated_at timestamp that is not older than the mtime of any upstream
required input artifact.

See gate_rules_library_plan.md §3 and §6.3 for the full specification.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.paths import resolve_repo_path
from runner.predicates.types import (
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
    STALE_UPSTREAM_MISMATCH,
    PredicateResult,
)
from runner.upstream_inputs import UPSTREAM_REQUIRED_INPUTS
from runner.versions import MANIFEST_VERSION

PathLike = str | os.PathLike[str]

# Every GateResult artifact must carry all of these fields with non-null values.
_MANDATORY_FIELDS: frozenset[str] = frozenset({
    "gate_id",
    "run_id",
    "status",
    "evaluated_at",
    "input_fingerprint",
    "manifest_version",
    "library_version",
    "constitution_version",
})


def _parse_iso8601(ts: Any) -> Optional[datetime]:
    """Parse an ISO 8601 string to an aware UTC datetime.

    Returns None if ts is not a string or cannot be parsed.
    Trailing Z (UTC designator) is normalised to +00:00 for broad Python
    3.7–3.10 compatibility. Naive timestamps are treated as UTC.
    """
    if not isinstance(ts, str):
        return None
    normalised = ts.strip()
    if normalised.endswith("Z"):
        normalised = normalised[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalised)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _max_upstream_mtime(
    gate_id: str,
    repo_root: Optional[Path],
) -> Optional[float]:
    """Return the maximum mtime (POSIX float) of upstream required inputs.

    Only paths that currently exist are considered; non-existent paths are
    silently skipped (their absence is checked by file predicates elsewhere).
    Directories use their own mtime (not a recursive child scan).
    Returns None if no upstream path exists.
    """
    paths = UPSTREAM_REQUIRED_INPUTS.get(gate_id, [])
    max_ts: Optional[float] = None
    for raw in paths:
        resolved = resolve_repo_path(raw, repo_root)
        if resolved.exists():
            mtime = resolved.stat().st_mtime
            if max_ts is None or mtime > max_ts:
                max_ts = mtime
    return max_ts


def _check_continuation_acceptance(
    gate_id: str,
    current_run_id: str,
    recorded_run_id: str,
    repo_root: Optional[Path],
) -> bool:
    """Check whether *gate_id*'s run_id mismatch was explicitly accepted.

    Returns ``True`` when the current run's continuation bootstrap recorded
    an acceptance of *gate_id* with *recorded_run_id* as the original run.
    Returns ``False`` in all other cases (no RunContext, no acceptance record,
    original_run_id mismatch, status != pass, or any error).

    This is a **narrow** continuation-contract check — it does not globally
    relax run_id enforcement.  It only accepts mismatches that were
    explicitly recorded by :func:`bootstrap_phase_prerequisites`.
    """
    if repo_root is None:
        return False
    try:
        from runner.run_context import RunContext, RUNS_DIR_REL

        manifest_path = (
            repo_root / RUNS_DIR_REL / current_run_id / "run_manifest.json"
        )
        if not manifest_path.exists():
            return False
        ctx = RunContext.load(repo_root, current_run_id)
        accepted = ctx.get_accepted_upstream_gate(gate_id)
        if accepted is None:
            return False
        if accepted.get("original_run_id") != recorded_run_id:
            return False
        if accepted.get("status") != "pass":
            return False
        return True
    except Exception:  # noqa: BLE001
        # Any infrastructure failure — fail closed
        return False


def gate_pass_recorded(
    gate_id: str,
    run_id: str,
    tier4_root: PathLike,
    *,
    repo_root: Optional[Path] = None,
) -> PredicateResult:
    """Confirm that a passed gate result is on record for the current run.

    Checks performed in order:

    1. gate_id is registered in GATE_RESULT_PATHS.
    2. Canonical gate result file exists at tier4_root / GATE_RESULT_PATHS[gate_id].
    3. File contains valid, non-empty JSON with a dict root.
    4. All mandatory GateResult fields are present and non-null.
    5. Recorded run_id matches the current run_id.
    6. Recorded manifest_version matches the current MANIFEST_VERSION.
    7. Recorded status equals "pass".
    8. input_fingerprint is a non-empty string.
    9. evaluated_at is not older than the mtime of any upstream required input.

    Args:
        gate_id:    ID of the gate whose result is being checked (must be a
                    key in GATE_RESULT_PATHS).
        run_id:     UUID of the current execution run, injected by the runner
                    at DAG startup (Step 10). Must match the run_id field in
                    the stored GateResult.
        tier4_root: Base directory for Tier 4 artifacts.  In the live
                    repository this is docs/tier4_orchestration_state/.
                    The canonical gate result path is constructed as:
                      Path(tier4_root) / GATE_RESULT_PATHS[gate_id]
                    Pass an absolute path or one resolvable via repo_root.
        repo_root:  Repository root used to resolve upstream input paths in
                    UPSTREAM_REQUIRED_INPUTS.  If None, relative upstream
                    paths are resolved against the current working directory.

    Returns:
        PredicateResult(passed=True) on success.
        PredicateResult(passed=False, failure_category=...) on any failure;
        failure_category is one of the five runner-defined categories.
    """
    # 1 — gate_id must be registered
    if gate_id not in GATE_RESULT_PATHS:
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=(
                f"Gate ID '{gate_id}' is not registered in GATE_RESULT_PATHS. "
                "Check gate_result_registry.py for valid gate IDs."
            ),
            details={"gate_id": gate_id},
        )

    # Construct canonical path
    tier4_resolved = resolve_repo_path(tier4_root, repo_root)
    result_path = tier4_resolved / GATE_RESULT_PATHS[gate_id]

    # 2 — file must exist and be a regular file
    if not result_path.exists():
        return PredicateResult(
            passed=False,
            failure_category=MISSING_MANDATORY_INPUT,
            reason=(
                f"Gate result file for '{gate_id}' is absent. "
                f"Expected: {result_path}"
            ),
            details={"gate_id": gate_id, "expected_path": str(result_path)},
        )

    if result_path.is_dir():
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Gate result path is a directory, not a file: {result_path}"
            ),
            details={"gate_id": gate_id, "path": str(result_path)},
        )

    # 3 — valid non-empty JSON with dict root
    try:
        raw = result_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Cannot read gate result file for '{gate_id}': {exc}",
            details={"gate_id": gate_id, "path": str(result_path)},
        )

    if not raw.strip():
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=f"Gate result file for '{gate_id}' is empty: {result_path}",
            details={"gate_id": gate_id, "path": str(result_path)},
        )

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Gate result file for '{gate_id}' is not valid JSON: {exc}"
            ),
            details={
                "gate_id": gate_id,
                "path": str(result_path),
                "error_line": exc.lineno,
                "error_col": exc.colno,
            },
        )

    if not isinstance(data, dict):
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Gate result JSON root for '{gate_id}' must be an object; "
                f"found {type(data).__name__}."
            ),
            details={
                "gate_id": gate_id,
                "path": str(result_path),
                "json_type": type(data).__name__,
            },
        )

    # 4 — all mandatory fields present and non-null
    missing = sorted(f for f in _MANDATORY_FIELDS if f not in data or data[f] is None)
    if missing:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Gate result for '{gate_id}' is missing mandatory fields: "
                f"{missing}"
            ),
            details={
                "gate_id": gate_id,
                "path": str(result_path),
                "missing_fields": missing,
            },
        )

    # 5 — run_id must match (or be accepted via continuation bootstrap)
    recorded_run_id: str = data["run_id"]
    if recorded_run_id != run_id:
        # Check if this gate was explicitly accepted as upstream evidence
        # during the current run's phase-scoped continuation bootstrap.
        accepted = _check_continuation_acceptance(
            gate_id, run_id, recorded_run_id, repo_root
        )
        if not accepted:
            return PredicateResult(
                passed=False,
                failure_category=STALE_UPSTREAM_MISMATCH,
                reason=(
                    f"Gate result for '{gate_id}' was produced by a different run. "
                    f"Expected run_id='{run_id}', found '{recorded_run_id}'."
                ),
                details={
                    "gate_id": gate_id,
                    "path": str(result_path),
                    "expected_run_id": run_id,
                    "recorded_run_id": recorded_run_id,
                },
            )

    # 6 — manifest_version must match current library's MANIFEST_VERSION
    recorded_manifest: str = data["manifest_version"]
    if recorded_manifest != MANIFEST_VERSION:
        return PredicateResult(
            passed=False,
            failure_category=STALE_UPSTREAM_MISMATCH,
            reason=(
                f"Gate result for '{gate_id}' was produced under manifest "
                f"v{recorded_manifest}; current manifest is v{MANIFEST_VERSION}. "
                "Re-evaluate the gate under the current manifest."
            ),
            details={
                "gate_id": gate_id,
                "path": str(result_path),
                "expected_manifest_version": MANIFEST_VERSION,
                "recorded_manifest_version": recorded_manifest,
            },
        )

    # 7 — status must be "pass"
    status: str = data["status"]
    if status != "pass":
        return PredicateResult(
            passed=False,
            failure_category=POLICY_VIOLATION,
            reason=(
                f"Gate '{gate_id}' did not pass in the current run. "
                f"Recorded status: '{status}'."
            ),
            details={
                "gate_id": gate_id,
                "path": str(result_path),
                "recorded_status": status,
            },
        )

    # 8 — input_fingerprint must be a non-empty string
    fingerprint: Any = data["input_fingerprint"]
    if not isinstance(fingerprint, str) or not fingerprint.strip():
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Gate result for '{gate_id}' has an empty or non-string "
                "input_fingerprint. The artifact was not properly produced."
            ),
            details={
                "gate_id": gate_id,
                "path": str(result_path),
                "input_fingerprint_value": repr(fingerprint),
            },
        )

    # 9 — freshness: evaluated_at must not predate any upstream input's mtime
    evaluated_at_dt = _parse_iso8601(data["evaluated_at"])
    if evaluated_at_dt is None:
        return PredicateResult(
            passed=False,
            failure_category=MALFORMED_ARTIFACT,
            reason=(
                f"Gate result for '{gate_id}' has an unparseable evaluated_at "
                f"timestamp: {data['evaluated_at']!r}"
            ),
            details={
                "gate_id": gate_id,
                "path": str(result_path),
                "evaluated_at": data["evaluated_at"],
            },
        )

    evaluated_at_posix = evaluated_at_dt.timestamp()
    max_mtime = _max_upstream_mtime(gate_id, repo_root)

    if max_mtime is not None and evaluated_at_posix < max_mtime:
        stale_inputs = []
        for raw_path in UPSTREAM_REQUIRED_INPUTS.get(gate_id, []):
            resolved = resolve_repo_path(raw_path, repo_root)
            if resolved.exists() and resolved.stat().st_mtime > evaluated_at_posix:
                stale_inputs.append(str(resolved))
        return PredicateResult(
            passed=False,
            failure_category=STALE_UPSTREAM_MISMATCH,
            reason=(
                f"Gate result for '{gate_id}' is stale: one or more upstream "
                "input artifacts were modified after the gate was evaluated."
            ),
            details={
                "gate_id": gate_id,
                "path": str(result_path),
                "evaluated_at": data["evaluated_at"],
                "stale_inputs": stale_inputs,
            },
        )

    # All checks passed
    return PredicateResult(
        passed=True,
        details={
            "gate_id": gate_id,
            "path": str(result_path),
            "run_id": run_id,
            "manifest_version": recorded_manifest,
            "status": status,
            "evaluated_at": data["evaluated_at"],
        },
    )
