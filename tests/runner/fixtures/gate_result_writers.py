"""
Gate result writers for Step 12 gate fixture tests.

Writes canonical GateResult artifacts that satisfy the contract expected by
``gate_pass_recorded``.  The helpers here produce pre-fabricated gate results
for use as "already-passed upstream gate" fixtures.

Key design choice: ``evaluated_at`` is set to a far-future timestamp
(year 2099) so the freshness check in ``gate_pass_recorded`` always passes
regardless of when the test writes its upstream input artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.versions import CONSTITUTION_VERSION, LIBRARY_VERSION, MANIFEST_VERSION
from tests.runner.fixtures.repo_builders import write_json

# Far-future evaluated_at guarantees freshness check always passes.
_FUTURE_EVAL_TS = "2099-01-01T00:00:00+00:00"
_SYNTHETIC_FINGERPRINT = "sha256:0000000000000000000000000000000000000000000000000000000000000000"


def write_passed_gate(
    repo_root: Path,
    gate_id: str,
    run_id: str,
    *,
    manifest_version: str = MANIFEST_VERSION,
    library_version: str = LIBRARY_VERSION,
    constitution_version: str = CONSTITUTION_VERSION,
    extra: dict | None = None,
) -> Path:
    """
    Write a canonical GateResult artifact claiming ``status: "pass"`` for
    *gate_id* under *run_id*.

    The written artifact satisfies all checks performed by
    ``gate_pass_recorded``:

    * canonical path derived from GATE_RESULT_PATHS
    * all mandatory fields present and non-null
    * ``run_id`` matches
    * ``manifest_version`` matches MANIFEST_VERSION (overridable for version-
      mismatch tests)
    * ``status == "pass"``
    * ``input_fingerprint`` is a non-empty string
    * ``evaluated_at`` (year 2099) is always newer than upstream mtime

    Returns the absolute path to the written file.
    """
    if gate_id not in GATE_RESULT_PATHS:
        raise ValueError(
            f"gate_id {gate_id!r} is not in GATE_RESULT_PATHS; "
            "cannot determine canonical write path."
        )

    tier4_root = repo_root / "docs/tier4_orchestration_state"
    result_path = tier4_root / GATE_RESULT_PATHS[gate_id]

    data: dict[str, Any] = {
        "gate_id": gate_id,
        "gate_kind": "exit",
        "run_id": run_id,
        "manifest_version": manifest_version,
        "library_version": library_version,
        "constitution_version": constitution_version,
        "evaluated_at": _FUTURE_EVAL_TS,
        "input_fingerprint": _SYNTHETIC_FINGERPRINT,
        "input_artifact_fingerprints": {},
        "status": "pass",
        "deterministic_predicates": {"passed": [], "failed": []},
        "semantic_predicates": {"passed": [], "failed": []},
        "skipped_semantic": False,
        "report_written_to": str(result_path),
    }
    if extra:
        data.update(extra)

    write_json(result_path, data)
    return result_path


def write_failed_gate(
    repo_root: Path,
    gate_id: str,
    run_id: str,
    *,
    failure_category: str = "MISSING_MANDATORY_INPUT",
    reason: str = "Fixture-forced gate failure",
) -> Path:
    """Write a GateResult artifact with ``status: "fail"``."""
    tier4_root = repo_root / "docs/tier4_orchestration_state"
    result_path = tier4_root / GATE_RESULT_PATHS[gate_id]

    data: dict[str, Any] = {
        "gate_id": gate_id,
        "gate_kind": "exit",
        "run_id": run_id,
        "manifest_version": MANIFEST_VERSION,
        "library_version": LIBRARY_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "input_fingerprint": _SYNTHETIC_FINGERPRINT,
        "input_artifact_fingerprints": {},
        "status": "fail",
        "deterministic_predicates": {
            "passed": [],
            "failed": [
                {
                    "predicate_id": "fixture_pred",
                    "failure_category": failure_category,
                    "reason": reason,
                }
            ],
        },
        "semantic_predicates": {"passed": [], "failed": []},
        "skipped_semantic": True,
        "report_written_to": str(result_path),
    }
    write_json(result_path, data)
    return result_path
