"""
Phase-8 final-export writer — deterministic node-body component.

This module writes the terminal Tier-5 export artifacts for ``n08f_revision``.
It is a **deterministic component** (CLAUDE.md §17.5.3 / C2, bound in the
manifest per §16.5 / C3): a pure-Python, Claude-free node-body pass that reads
declared input artifacts and writes canonical artifacts via an atomic write.
It closes the gap found in run 5952b165: ``final_export.json`` was schema-bound
(``orch.tier5.final_export.v1``), gate-checked (``gate_12`` predicates
``g11_p05`` / ``g11_p05b``), and named as the revision integrator's primary
canonical output — but no skill or component produced it, so ``n08f`` could
never satisfy its §17.6.6 disk check.

What it does
------------
Reads the assembled Part B draft (``part_b_assembled_draft.json``, written by
``n08d_assembly``) and produces two files in
``docs/tier5_deliverables/final_exports/``:

1. ``part_b_json_bundle.json`` — the exported proposal itself: a self-contained
   JSON bundle embedding the assembled draft **verbatim** plus each referenced
   section artifact **verbatim** (``final_exports/`` is a terminal directory;
   the export must not require chasing references back into the repo).
2. ``final_export.json`` — the schema-bound export manifest
   (``orch.tier5.final_export.v1``): ``export_format: "json_bundle"``,
   ``export_path`` naming the bundle, and a ``section_index`` derived from the
   assembled draft's section list (sorted by its explicit ``order`` field;
   ``criterion`` supplies ``section_name``).

The manifest is written **after** the bundle, so a partial failure can never
leave a manifest pointing at a missing export.

Determinism guarantee
---------------------
Pure lookup + verbatim copy over the assembled draft and the section
artifacts.  No inference, no domain reasoning, no Claude.  The single
non-deterministic field is ``exported_at`` — a production stamp like
``gate_result.evaluated_at`` and ``phase8_checkpoint.published_at``, excluded
from the replay invariant.  The bundle itself carries no stamp and is fully
byte-equal replayable.

Unlike the phase-8 checkpoint there is **no write-once guard**: gate_12's
``g11_p05b`` (``artifact_owned_by_run``) requires the export to carry the
*current* run's ``run_id``, so every run that reaches n08f rewrites the export
deterministically from its own assembled draft.

Fail-closed (§12.4, §13.8)
--------------------------
Any structural fault — a missing/malformed/wrong-schema assembled draft, an
assembled draft owned by a different run (n08d must have produced it in this
run; assembly has no cross-run reuse), an empty/duplicate/malformed section
list, or a referenced section artifact that is absent or not valid JSON —
raises :class:`FinalExportError` **before** anything is written.  The agent
runtime surfaces a raised component fault as ``AGENT_EXECUTION_ERROR`` /
``can_evaluate_exit_gate=False``, so the exit gate (gate_12) is skipped and
n08f blocks ``blocked_at_exit``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runner.atomic_write import atomic_write_json

log = logging.getLogger(__name__)

#: Schema id of the export manifest artifact.
FINAL_EXPORT_SCHEMA_ID = "orch.tier5.final_export.v1"

#: Canonical repo-relative path of the export manifest.
FINAL_EXPORT_REL = "docs/tier5_deliverables/final_exports/final_export.json"

#: Repo-relative path of the exported proposal bundle the manifest points at.
JSON_BUNDLE_REL = "docs/tier5_deliverables/final_exports/part_b_json_bundle.json"

#: The n08d assembly artifact this export is derived from.
ASSEMBLED_DRAFT_REL = (
    "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json"
)

#: Expected schema id of the assembled draft.
ASSEMBLED_DRAFT_SCHEMA_ID = "orch.tier5.part_b_assembled_draft.v1"


class FinalExportError(Exception):
    """Raised when the final export cannot be produced — fail-closed (§12.4).

    Surfaced by the deterministic-component wrapper as an
    ``AGENT_EXECUTION_ERROR`` node block; nothing is written.
    """


def _read_json_dict(path: Path, what: str) -> dict:
    """Read *path* as a JSON object, raising :class:`FinalExportError`."""
    if not path.is_file():
        raise FinalExportError(f"{what} not found at {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise FinalExportError(f"{what} at {path} could not be read: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FinalExportError(f"{what} at {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise FinalExportError(f"{what} at {path} is not a JSON object")
    if not data:
        raise FinalExportError(f"{what} at {path} is empty")
    return data


def _validate_sections(sections: Any) -> list[dict]:
    """Validate the assembled draft's section list; return it sorted by order.

    Every entry must carry a non-empty ``section_id``, ``criterion``, and
    ``artifact_path`` and an integer ``order``; ids and orders must be unique.
    Pure structural validation — no content judgment.
    """
    if not isinstance(sections, list) or not sections:
        raise FinalExportError(
            "Assembled draft has no sections; cannot derive a final export "
            "from an empty assembly"
        )
    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    for entry in sections:
        if not isinstance(entry, dict):
            raise FinalExportError(
                f"Assembled draft section entry is not an object: {entry!r}"
            )
        section_id = entry.get("section_id")
        criterion = entry.get("criterion")
        artifact_path = entry.get("artifact_path")
        order = entry.get("order")
        if not section_id or not isinstance(section_id, str):
            raise FinalExportError(
                f"Assembled draft section entry missing section_id: {entry!r}"
            )
        if not criterion or not isinstance(criterion, str):
            raise FinalExportError(
                f"Section {section_id!r} missing criterion (section name source)"
            )
        if not artifact_path or not isinstance(artifact_path, str):
            raise FinalExportError(
                f"Section {section_id!r} missing artifact_path"
            )
        if not isinstance(order, int) or isinstance(order, bool):
            raise FinalExportError(
                f"Section {section_id!r} has non-integer order: {order!r}"
            )
        if section_id in seen_ids:
            raise FinalExportError(
                f"Duplicate section_id {section_id!r} in assembled draft"
            )
        if order in seen_orders:
            raise FinalExportError(
                f"Duplicate section order {order} in assembled draft "
                f"(at section {section_id!r}); rendering order is ambiguous"
            )
        seen_ids.add(section_id)
        seen_orders.add(order)
    return sorted(sections, key=lambda e: e["order"])


def write_final_export(run_id: str, repo_root: Path) -> list[Path]:
    """Write the Part B export bundle and manifest; return their paths.

    Parameters
    ----------
    run_id:
        Current DAG-runner run id.  The assembled draft must be owned by this
        run; the export manifest is stamped with it (``g11_p05b``).
    repo_root:
        Absolute path to the repository root.

    Raises
    ------
    FinalExportError
        On any structural fault in the assembled draft or a referenced
        section artifact — fail-closed, before anything is written.
    """
    repo_root = Path(repo_root)
    draft_path = repo_root / ASSEMBLED_DRAFT_REL

    draft = _read_json_dict(draft_path, "Assembled Part B draft")
    if draft.get("schema_id") != ASSEMBLED_DRAFT_SCHEMA_ID:
        raise FinalExportError(
            f"Assembled draft at {draft_path} has unexpected schema_id "
            f"{draft.get('schema_id')!r} (expected {ASSEMBLED_DRAFT_SCHEMA_ID!r})"
        )
    if draft.get("run_id") != run_id:
        raise FinalExportError(
            f"Assembled draft is owned by run {draft.get('run_id')!r}, not the "
            f"current run {run_id!r}. Assembly (n08d) must produce the draft "
            f"in the run that exports it; there is no cross-run assembly reuse."
        )

    sections = _validate_sections(draft.get("sections"))

    # Read every referenced section artifact verbatim — the bundle embeds them
    # so the terminal export is self-contained.
    sections_content: dict[str, dict] = {}
    for entry in sections:
        section_path = repo_root / entry["artifact_path"]
        sections_content[entry["section_id"]] = _read_json_dict(
            section_path, f"Section artifact {entry['section_id']!r}"
        )

    # 1. The exported proposal bundle (byte-equal replayable: no stamp).
    bundle: dict[str, Any] = {
        "bundle_format": "part_b_json_bundle",
        "run_id": run_id,
        "assembled_draft": draft,
        "sections_content": sections_content,
    }
    bundle_path = repo_root / JSON_BUNDLE_REL
    atomic_write_json(bundle, bundle_path, prefix="final_export_")

    # 2. The schema-bound export manifest — written last so it can never point
    #    at a bundle that failed to materialize.
    section_index = [
        {
            "section_id": entry["section_id"],
            "section_name": entry["criterion"],
            "artifact_path": entry["artifact_path"],
        }
        for entry in sections
    ]
    manifest: dict[str, Any] = {
        "schema_id": FINAL_EXPORT_SCHEMA_ID,
        "run_id": run_id,
        "export_format": "json_bundle",
        "export_path": JSON_BUNDLE_REL,
        "section_index": section_index,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = repo_root / FINAL_EXPORT_REL
    atomic_write_json(manifest, manifest_path, prefix="final_export_")

    log.info(
        "Final export written: %s (+ bundle %s, %d sections, run_id=%s)",
        manifest_path,
        bundle_path,
        len(section_index),
        run_id,
    )
    return [bundle_path, manifest_path]
