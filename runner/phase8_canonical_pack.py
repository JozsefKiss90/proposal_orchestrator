"""
Canonical reference pack builder for Phase 8 drafting consistency.

Reads authoritative Tier 3 and Tier 4 sources and writes a single
deterministic JSON artifact that drafting skills use as the canonical
reference for objective titles, WP titles, deliverable identities,
partner names, and outcome titles.

No LLM calls.  No inference.  No alias generation.  Source values are
preserved exactly.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CANONICAL_PACK_REL = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase8_drafting_review/canonical_reference_pack.json"
)

SCHEMA_ID = "orch.phase8.canonical_reference_pack.v1"


def _read_json(path: Path) -> dict | None:
    """Read a JSON file, returning None on any error."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8-sig")
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None


def _extract_objectives(data: dict) -> list[dict[str, Any]]:
    """Extract objectives preserving id, title, measurable_target, responsible_partner."""
    result: list[dict[str, Any]] = []
    for obj in data.get("objectives", []):
        if not isinstance(obj, dict):
            continue
        entry: dict[str, Any] = {}
        for key in ("id", "title", "measurable_target",
                     "responsible_partner", "contributing_partners"):
            if key in obj:
                entry[key] = obj[key]
        if entry.get("id"):
            result.append(entry)
    return result


def _extract_outcomes(data: dict) -> list[dict[str, Any]]:
    """Extract outcomes preserving id, title, linked_objectives, linked_wp_ids."""
    result: list[dict[str, Any]] = []
    for out in data.get("outcomes", []):
        if not isinstance(out, dict):
            continue
        entry: dict[str, Any] = {}
        for key in ("id", "title", "linked_objectives", "linked_wp_ids",
                     "linked_deliverable_ids"):
            if key in out:
                entry[key] = out[key]
        if entry.get("id"):
            result.append(entry)
    return result


def _extract_wps_and_deliverables(
    data: dict,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract WPs and deliverables from wp_structure.json."""
    wps: list[dict[str, Any]] = []
    deliverables: list[dict[str, Any]] = []
    for wp in data.get("work_packages", []):
        if not isinstance(wp, dict):
            continue
        wp_entry: dict[str, Any] = {}
        for key in ("wp_id", "title", "lead_partner"):
            if key in wp:
                wp_entry[key] = wp[key]
        if wp_entry.get("wp_id"):
            wps.append(wp_entry)
        for deliv in wp.get("deliverables", []):
            if not isinstance(deliv, dict):
                continue
            d_entry: dict[str, Any] = {}
            for key in ("deliverable_id", "title", "due_month", "type"):
                if key in deliv:
                    d_entry[key] = deliv[key]
            d_entry["parent_wp"] = wp.get("wp_id", "")
            if d_entry.get("deliverable_id"):
                deliverables.append(d_entry)
    return wps, deliverables


def _extract_partners(data: dict) -> list[dict[str, Any]]:
    """Extract partners preserving short_name, legal_name, country, role."""
    result: list[dict[str, Any]] = []
    for p in data.get("partners", []):
        if not isinstance(p, dict):
            continue
        entry: dict[str, Any] = {}
        for key in ("short_name", "legal_name", "country", "role"):
            if key in p:
                entry[key] = p[key]
        if entry.get("short_name") or entry.get("legal_name"):
            result.append(entry)
    return result


def build_phase8_canonical_reference_pack(
    repo_root: Path,
    run_id: str,
) -> Path:
    """Build the canonical reference pack from Tier 3/4 sources.

    Returns the absolute path of the written artifact.
    """
    objectives_path = (
        repo_root / "docs" / "tier3_project_instantiation"
        / "architecture_inputs" / "objectives.json"
    )
    outcomes_path = (
        repo_root / "docs" / "tier3_project_instantiation"
        / "architecture_inputs" / "outcomes.json"
    )
    wp_path = (
        repo_root / "docs" / "tier4_orchestration_state"
        / "phase_outputs" / "phase3_wp_design" / "wp_structure.json"
    )
    partners_path = (
        repo_root / "docs" / "tier3_project_instantiation"
        / "consortium" / "partners.json"
    )

    objectives: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    wps: list[dict[str, Any]] = []
    deliverables: list[dict[str, Any]] = []
    partners: list[dict[str, Any]] = []

    obj_data = _read_json(objectives_path)
    if obj_data is not None:
        objectives = _extract_objectives(obj_data)

    out_data = _read_json(outcomes_path)
    if out_data is not None:
        outcomes = _extract_outcomes(out_data)

    wp_data = _read_json(wp_path)
    if wp_data is not None:
        wps, deliverables = _extract_wps_and_deliverables(wp_data)

    partner_data = _read_json(partners_path)
    if partner_data is not None:
        partners = _extract_partners(partner_data)

    pack = {
        "schema_id": SCHEMA_ID,
        "run_id": run_id,
        "objectives": objectives,
        "outcomes": outcomes,
        "wps": wps,
        "deliverables": deliverables,
        "partners": partners,
        "aliases": [],
    }

    out_path = repo_root / CANONICAL_PACK_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(pack, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Canonical reference pack written: %s", out_path)
    return out_path
