"""
Call Slicer — deterministic input bounding layer (Step 0).

Extracts the single target call entry from a grouped work-programme JSON
before any Claude invocation, so downstream skills operate over bounded,
call-specific data only (~5-10 KB instead of 338-794 KB).

This module is pure Python.  It does not invoke Claude, does not depend
on TAPM infrastructure, and performs no domain reasoning.  It is a
deterministic lookup-and-extract function: same inputs produce the same
output (modulo timestamp).

Constitutional authority: CLAUDE.md §17 (runtime execution architecture).
Step 0 is a runtime-layer preprocessing optimisation that narrows input
breadth.  It does not modify gate logic, artifact schemas, or the
authority hierarchy.

Integration point
-----------------
Called once by ``DAGScheduler.run()`` before the dispatch loop.  Failure
is non-blocking — skills fall back to reading full grouped JSONs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("runner.call_slicer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SELECTED_CALL_PATH: str = (
    "docs/tier3_project_instantiation/call_binding/selected_call.json"
)

CALL_EXTRACTS_DIR: str = "docs/tier2b_topic_and_call_sources/call_extracts"

GROUPED_JSON_MAP: dict[str, str] = {
    "cluster_digital": "docs/tier2b_topic_and_call_sources/work_programmes/cluster_digital/cluster_CL4.grouped.json",
    "cluster_health": "docs/tier2b_topic_and_call_sources/work_programmes/cluster_health/cluster_CL1.grouped.json",
    "cluster_culture": "docs/tier2b_topic_and_call_sources/work_programmes/cluster_culture/cluster_CL2.grouped.json",
    "cluster_security": "docs/tier2b_topic_and_call_sources/work_programmes/cluster_security/cluster_CL3.grouped.json",
    "cluster_food": "docs/tier2b_topic_and_call_sources/work_programmes/cluster_food/cluster_CL5.grouped.json",
    "cluster_climate": "docs/tier2b_topic_and_call_sources/work_programmes/cluster_climate/cluster_CL6.grouped.json",
}

MAX_SLICE_BYTES: int = 20_480  # 20 KB hard limit


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class CallSlicerError(Exception):
    """Raised when call slicing fails.

    All failure modes produce this exception: missing inputs, unknown
    ``work_programme``, no matching ``topic_code``, or oversized output.
    """


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_call_slice(repo_root: Path) -> Path:
    """Extract the target call entry from the grouped work-programme JSON.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root.

    Returns
    -------
    Path
        Absolute path to the written slice file
        (``call_extracts/<topic_code>.slice.json``).

    Raises
    ------
    CallSlicerError
        On any failure: missing files, unknown work programme, no match,
        or output exceeding :data:`MAX_SLICE_BYTES`.
    """

    # 1. Read selected_call.json -------------------------------------------
    selected_path = repo_root / SELECTED_CALL_PATH
    try:
        selected = json.loads(selected_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CallSlicerError(
            f"selected_call.json not found: {selected_path}"
        )
    except json.JSONDecodeError as exc:
        raise CallSlicerError(
            f"selected_call.json is not valid JSON: {exc}"
        )

    # 2. Extract topic_code and work_programme -----------------------------
    topic_code = selected.get("topic_code")
    if not topic_code:
        raise CallSlicerError(
            "selected_call.json missing required key 'topic_code'"
        )

    work_programme = selected.get("work_programme")
    if not work_programme:
        raise CallSlicerError(
            "selected_call.json missing required key 'work_programme'"
        )

    # 3. Resolve grouped JSON path -----------------------------------------
    grouped_rel = GROUPED_JSON_MAP.get(work_programme)
    if grouped_rel is None:
        raise CallSlicerError(
            f"Unknown work_programme '{work_programme}'. "
            f"Known values: {sorted(GROUPED_JSON_MAP)}"
        )

    grouped_path = repo_root / grouped_rel
    if not grouped_path.exists():
        raise CallSlicerError(
            f"Grouped JSON not found: {grouped_path}"
        )

    # 4. Parse grouped JSON ------------------------------------------------
    try:
        grouped = json.loads(grouped_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CallSlicerError(
            f"Grouped JSON is not valid JSON ({grouped_path}): {exc}"
        )

    # 5. Linear scan with multi-field matching -----------------------------
    #    Schema A (CL3-6): call_id / original_call_id
    #    Schema B (CL1-2): identifier / topic_id
    match = None
    match_destination: str = ""
    for destination in grouped.get("destinations", []):
        for call in destination.get("calls", []):
            call_topic = call.get("call_id") or call.get("identifier")
            if (
                call_topic == topic_code
                or call.get("original_call_id") == topic_code
                or call.get("topic_id") == topic_code
            ):
                match = call
                match_destination = destination.get("destination_title", "")
                break
        if match is not None:
            break

    if match is None:
        raise CallSlicerError(
            f"topic_code '{topic_code}' not found in {grouped_path}"
        )

    # 6. Assemble slice object ---------------------------------------------
    call_slice = {
        "topic_code": topic_code,
        "source_grouped_json": grouped_rel,
        "source_destination": match_destination,
        "call_entry": match,
        "sliced_by": "runner/call_slicer.py",
        "slice_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 7. Serialize and validate size ---------------------------------------
    output_text = json.dumps(call_slice, indent=2, ensure_ascii=False)
    output_size = len(output_text.encode("utf-8"))
    if output_size > MAX_SLICE_BYTES:
        raise CallSlicerError(
            f"Slice output exceeds {MAX_SLICE_BYTES} bytes "
            f"({output_size} bytes). "
            f"This indicates a data anomaly in the grouped JSON."
        )

    # 8. Write to canonical output path ------------------------------------
    output_path = repo_root / CALL_EXTRACTS_DIR / f"{topic_code}.slice.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")

    log.info(
        "Call slice generated: %s (%d bytes, topic=%s)",
        output_path.relative_to(repo_root),
        output_size,
        topic_code,
    )
    return output_path
