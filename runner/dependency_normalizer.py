"""
Deterministic dependency normalization for Phase 4 scheduling.

Reads the Phase 3 dependency_map from wp_structure.json, WP temporal bounds
from workpackage_seed.json, and project duration from selected_call.json.
Produces a normalized scheduling_constraints.json artifact that classifies
each dependency edge as strict (temporally enforceable) or non-strict
(informational / data-input).

WP-level ``finish_to_start`` edges whose source WP ends after the target WP
starts (per seed bounds) are reclassified as non-strict — they represent
logical data dependencies, not strict full-WP sequencing.  Task-level
``finish_to_start`` edges are preserved as strict.  ``data_input`` edges are
always non-strict.

This module is a pure-Python deterministic preprocessor.  It does not invoke
Claude, does not modify wp_structure.json, and fails closed on any input
error.  It follows the same architectural pattern as ``runner/call_slicer.py``
(Step 0 deterministic preprocessing) but is Phase 4-specific and integrated
via ``agent_runtime.py`` rather than the scheduler.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WP_STRUCTURE_REL = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase3_wp_design/wp_structure.json"
)
WP_SEED_REL = (
    "docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json"
)
SELECTED_CALL_REL = (
    "docs/tier3_project_instantiation/call_binding/selected_call.json"
)
OUTPUT_REL = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase4_gantt_milestones/scheduling_constraints.json"
)
SCHEMA_ID = "orch.phase4.scheduling_constraints.v1"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class DependencyNormalizerError(Exception):
    """Raised when dependency normalization cannot produce a valid artifact."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path, label: str) -> dict[str, Any]:
    """Read and parse a JSON file.  Fail-closed on any issue."""
    if not path.is_file():
        raise DependencyNormalizerError(f"{label} not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DependencyNormalizerError(f"Cannot read {label}: {exc}") from exc
    if not text.strip():
        raise DependencyNormalizerError(f"{label} is empty: {path}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DependencyNormalizerError(
            f"{label} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise DependencyNormalizerError(
            f"{label} top-level value must be an object, got {type(data).__name__}"
        )
    return data


def _build_wp_bounds(seed: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Build {wp_id: {start_month, end_month}} from workpackage_seed.json."""
    wps = seed.get("work_packages")
    if not isinstance(wps, list):
        raise DependencyNormalizerError(
            "workpackage_seed.json missing 'work_packages' array"
        )
    bounds: dict[str, dict[str, int]] = {}
    for wp in wps:
        if not isinstance(wp, dict):
            continue
        wp_id = wp.get("id")
        start = wp.get("start_month")
        end = wp.get("end_month")
        if wp_id is None or start is None or end is None:
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        bounds[str(wp_id)] = {"start_month": start, "end_month": end}
    if not bounds:
        raise DependencyNormalizerError(
            "workpackage_seed.json contains no WPs with valid start/end months"
        )
    return bounds


def _build_task_to_wp(wp_structure: dict[str, Any]) -> dict[str, str]:
    """Build {task_id: wp_id} from wp_structure.json work_packages[].tasks[]."""
    wps = wp_structure.get("work_packages")
    if not isinstance(wps, list):
        raise DependencyNormalizerError(
            "wp_structure.json missing 'work_packages' array"
        )
    mapping: dict[str, str] = {}
    for wp in wps:
        if not isinstance(wp, dict):
            continue
        wp_id = wp.get("wp_id")
        if wp_id is None:
            continue
        tasks = wp.get("tasks")
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if isinstance(task, dict) and task.get("task_id"):
                mapping[str(task["task_id"])] = str(wp_id)
    return mapping


def _get_project_duration(call_data: dict[str, Any]) -> int:
    """Extract project duration in months, trying both field name variants."""
    duration = call_data.get("project_duration_months")
    if duration is None:
        duration = call_data.get("max_project_duration_months")
    if duration is None:
        raise DependencyNormalizerError(
            "selected_call.json has neither 'project_duration_months' "
            "nor 'max_project_duration_months'"
        )
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise DependencyNormalizerError(
            f"Project duration must be a positive integer, got: {duration!r}"
        )
    return duration


def _is_wp_node(node_id: str, wp_bounds: dict[str, dict[str, int]]) -> bool:
    """Check whether a dependency node is a WP-level node."""
    return node_id in wp_bounds


def _classify_edge(
    edge: dict[str, Any],
    wp_bounds: dict[str, dict[str, int]],
) -> tuple[str, str, str]:
    """Classify one dependency edge.

    Returns (normalized_type, action, reason) where:
    - normalized_type: "strict" or "non_strict"
    - action: "preserved" or "reclassified"
    - reason: human-readable explanation
    """
    from_node = str(edge.get("from", ""))
    to_node = str(edge.get("to", ""))
    edge_type = str(edge.get("edge_type", ""))

    # data_input edges are always non-strict
    if edge_type == "data_input":
        return "non_strict", "preserved", "data_input edge: no temporal ordering enforced"

    # finish_to_start at WP level: check temporal feasibility
    if edge_type == "finish_to_start":
        from_is_wp = _is_wp_node(from_node, wp_bounds)
        to_is_wp = _is_wp_node(to_node, wp_bounds)

        if from_is_wp and to_is_wp:
            from_end = wp_bounds[from_node]["end_month"]
            to_start = wp_bounds[to_node]["start_month"]
            if from_end <= to_start:
                return (
                    "strict",
                    "preserved",
                    f"WP-level finish_to_start is feasible: "
                    f"{from_node} ends M{from_end}, {to_node} starts M{to_start}",
                )
            else:
                return (
                    "non_strict",
                    "reclassified",
                    f"WP-level finish_to_start infeasible: "
                    f"{from_node} ends M{from_end}, {to_node} starts M{to_start}",
                )

        # Task-level finish_to_start: preserve as strict
        # (feasibility verified by gate predicate after gantt.json exists)
        return (
            "strict",
            "preserved",
            "task-level finish_to_start: enforceable temporal constraint",
        )

    # Any other edge_type: treat as non-strict (conservative)
    return (
        "non_strict",
        "preserved",
        f"edge_type '{edge_type}': treated as non-strict (no scheduling rule defined)",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_dependencies(run_id: str, repo_root: Path) -> Path:
    """Normalize Phase 3 dependency_map into scheduling constraints.

    Reads wp_structure.json, workpackage_seed.json, and selected_call.json.
    Writes scheduling_constraints.json to the Phase 4 output directory.

    Parameters
    ----------
    run_id : str
        Current DAG-runner run UUID.
    repo_root : Path
        Absolute path to the repository root.

    Returns
    -------
    Path
        Absolute path to the written scheduling_constraints.json.

    Raises
    ------
    DependencyNormalizerError
        On any input validation failure, missing file, or malformed data.
    """
    # ── Read inputs ──────────────────────────────────────────────────────
    wp_structure = _read_json(
        repo_root / WP_STRUCTURE_REL, "wp_structure.json"
    )
    seed = _read_json(repo_root / WP_SEED_REL, "workpackage_seed.json")
    call_data = _read_json(repo_root / SELECTED_CALL_REL, "selected_call.json")

    # ── Build lookup structures ──────────────────────────────────────────
    wp_bounds = _build_wp_bounds(seed)
    task_to_wp = _build_task_to_wp(wp_structure)
    project_duration = _get_project_duration(call_data)

    # ── Extract source run_id ─���──────────────────────────────────────────
    source_run_id = wp_structure.get("run_id", "unknown")

    # ── Extract edges ────────────────────────────────────────────────────
    dep_map = wp_structure.get("dependency_map")
    if not isinstance(dep_map, dict):
        raise DependencyNormalizerError(
            "wp_structure.json missing 'dependency_map' object"
        )
    edges = dep_map.get("edges")
    if not isinstance(edges, list):
        raise DependencyNormalizerError(
            "wp_structure.json dependency_map missing 'edges' array"
        )

    # ── Classify each edge ───────────────────────────────────────────────
    strict: list[dict[str, str]] = []
    non_strict: list[dict[str, str]] = []
    log_entries: list[dict[str, Any]] = []

    for edge in edges:
        if not isinstance(edge, dict):
            raise DependencyNormalizerError(
                f"dependency_map edge is not an object: {edge!r}"
            )
        from_node = str(edge.get("from", ""))
        to_node = str(edge.get("to", ""))
        original_type = str(edge.get("edge_type", ""))

        if not from_node or not to_node:
            raise DependencyNormalizerError(
                f"dependency_map edge missing 'from' or 'to': {edge!r}"
            )

        normalized_type, action, reason = _classify_edge(edge, wp_bounds)

        entry = {
            "from": from_node,
            "to": to_node,
            "original_edge_type": original_type,
            "action": action,
            "reason": reason,
        }

        if normalized_type == "strict":
            strict.append(entry)
        else:
            non_strict.append(entry)

        log_entries.append({
            "edge": {"from": from_node, "to": to_node},
            "original_type": original_type,
            "normalized_type": normalized_type,
            "action": action,
            "reason": reason,
        })

    # ── Assemble output ──────────────────────────────────────────────────
    artifact = {
        "schema_id": SCHEMA_ID,
        "run_id": run_id,
        "source_wp_structure_run_id": str(source_run_id),
        "derived_from_artifact": WP_STRUCTURE_REL,
        "normalization_timestamp": datetime.now(timezone.utc).isoformat(),
        "project_duration_months": project_duration,
        "wp_bounds": wp_bounds,
        "strict_constraints": strict,
        "non_strict_constraints": non_strict,
        "normalization_log": log_entries,
        "unresolved_constraints": [],
    }

    # ── Atomic write ─────────────────────────────────────────────────────
    output_path = repo_root / OUTPUT_REL
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = json.dumps(artifact, indent=2, ensure_ascii=False)

    # Write to temp file then rename (atomic on same filesystem)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(output_path.parent),
        suffix=".tmp",
        prefix="scheduling_constraints_",
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        fd = -1
        # On Windows, target must not exist for os.rename
        if output_path.exists():
            output_path.unlink()
        os.rename(tmp_path, str(output_path))
    except Exception:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    logger.info(
        "scheduling_constraints.json written: %d strict, %d non-strict, "
        "%d unresolved",
        len(strict),
        len(non_strict),
        0,
    )
    return output_path
