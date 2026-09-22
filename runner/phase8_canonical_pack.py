"""
Canonical reference pack builder for Phase 8 drafting consistency.

Reads authoritative Tier 3 and Tier 4 sources and writes a single
deterministic JSON artifact that drafting skills use as the canonical
reference for objective titles, WP titles, deliverable identities,
partner names, and outcome titles.

No LLM calls.  No inference.  No alias generation.  Source values are
preserved exactly.

Provenance and declared assumptions (CLAUDE.md §12.2, ticket 10)
----------------------------------------------------------------
The pack is generated from the **same** source as the prose the
canonical-preservation gates check it against: Tier 3 confirmed facts
*plus* the operator's declared working assumptions (Tier 3
``working_assumptions.json``, ticket 15).  Every entry carries a
``provenance`` tag so an assumed value can never masquerade as a
confirmed canonical fact:

  * The typed arrays (``objectives`` / ``outcomes`` / ``wps`` /
    ``deliverables`` / ``partners``) are lifted verbatim from confirmed
    Tier 3/4 sources and tagged ``provenance: "confirmed"``.
  * Operator declarations are passed through **verbatim** into a separate
    ``declared_assumptions`` array, each tagged ``provenance: "assumed"``.
    They are never merged into the confirmed arrays — the deriver does no
    inference about which typed entity (partner, objective, …) a
    declaration backs, so a declared value is *quarantined*, provenance-
    tagged, and structurally incapable of being emitted as confirmed.

This is a **deterministic component** (§17.5.3 / C2): pure-Python,
Claude-free, no inference — a lookup + verbatim copy + constant provenance
tag.  It fails closed on a present-but-malformed ``working_assumptions.json``
(via the shared reader's contract) rather than silently dropping an
operator declaration.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from runner.atomic_write import atomic_write_json
from runner.working_assumptions import load_working_assumptions

log = logging.getLogger(__name__)

CANONICAL_PACK_REL = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase8_drafting_review/canonical_reference_pack.json"
)

SCHEMA_ID = "orch.phase8.canonical_reference_pack.v1"

#: Per-entry provenance tags.  These are lowercase **machine tags** on pack
#: entries — the same casing convention the section claim layer uses for
#: ``claim.status`` (``"assumed"`` / ``"unresolved"``, see
#: ``runner/assumption_applier.py``), *not* the proper-cased §12.2
#: validation-report surface vocabulary ("Confirmed" / "Assumed", rendered by
#: ``WorkingAssumptions.as_surface()``).  Semantically a confirmed entry is
#: directly evidenced by a Tier 1–3 source (§12.2 "Confirmed") and an assumed
#: entry is an operator declaration adopted in the absence of direct evidence
#: (§12.2 "Assumed") — the tag is the machine encoding of that distinction.
#: The ``"assumed"`` tag itself is now owned by
#: :meth:`runner.working_assumptions.WorkingAssumptions.as_canonical_pack_entries`
#: (the shared declared-assumptions renderer), so only the confirmed tag lives here.
PROVENANCE_CONFIRMED = "confirmed"

#: Confirmed arrays that must be non-empty for the pack to back Phase-8
#: drafting.  A Phase-8 drafting node runs only after the upstream Phase-3/4
#: gates it is transitively gated on have passed, so these are populated in any
#: real run; the check is a fail-closed backstop (§12.4) against a corrupted or
#: partial Tier 3/4 reaching Phase 8 with an empty pack — which the preservation
#: predicates would then *vacuously* pass (they early-return on empty arrays).
#: ``partners`` is deliberately **excluded**: MSCA-PF is a single-researcher
#: instrument with no consortium ``partners.json`` (the host is declared via
#: ``working_assumptions.json``, quarantined into ``declared_assumptions``), so
#: requiring it would be a RIA-shaped assumption (ticket 2 no-RIA-leak mandate).
#:
#: ``outcomes`` is included: the vacuous-pass argument that justifies the
#: backstop applies to it identically.  ``canonical_terminology_preserved``
#: iterates ``pack_data["outcomes"]`` for outcome-title checks and
#: ``measurable_targets_preserved`` walks ``outcomes[].linked_objectives`` to
#: propagate metric enforcement from a mentioned outcome to its objectives —
#: both perform **zero** checks on an empty array.  An outcomes source that
#: silently yields nothing therefore buys a green gate over unchecked prose,
#: which is precisely the failure mode §12.4 requires be blocked rather than
#: passed.
_REQUIRED_NONEMPTY: tuple[str, ...] = (
    "objectives", "outcomes", "wps", "deliverables",
)

#: Pack fields lifted from each Tier-3 objective / outcome record, in pack order.
_OBJECTIVE_KEYS: tuple[str, ...] = (
    "id", "title", "measurable_target", "responsible_partner",
    "contributing_partners",
)
_OUTCOME_KEYS: tuple[str, ...] = (
    "id", "title", "linked_objectives", "linked_wp_ids",
    "linked_deliverable_ids",
)

#: Tier-3 source keys that carry a pack field's value under a different name,
#: as ``{pack_key: source_key}``.
#:
#: The canonical pack contract read by the Phase-8 preservation predicates is
#: ``id`` / ``title`` / ``measurable_target`` (see
#: ``runner/predicates/phase8_section_predicates.py`` — ``obj.get("id")``,
#: ``obj.get("measurable_target")``, ``outcome.get("id")``).  An operator
#: hand-lift may author the Tier-3 sources with entity-scoped id keys
#: (``objective_id``, ``outcome_id``) and its own column-derived value names
#: (``measurable_output``, named after the draft's "Verification" column;
#: ``statement`` for an outcome's text).  Without this map every record fails
#: the ``entry.get("id")`` admission test and is dropped, emptying the array.
#:
#: Each mapping is a **pure rename** — the same value under the pack's key.  It
#: adds no fact and makes no judgment, so the component remains deterministic
#: and inference-free (§17.5.3).  An alias is consulted only when the canonical
#: key is absent, so a source already speaking the pack contract is untouched.
#:
#: Deliberately **not** mapped: a hand-lifted ``involved_partners`` array does
#: not distinguish a responsible partner from contributing ones, so folding it
#: into ``responsible_partner`` / ``contributing_partners`` would be inference
#: about project facts (§13.3).  It is dropped, like any unrecognised field.
_OBJECTIVE_ALIASES: dict[str, str] = {
    "id": "objective_id",
    "measurable_target": "measurable_output",
}
_OUTCOME_ALIASES: dict[str, str] = {
    "id": "outcome_id",
    "title": "statement",
}


class CanonicalPackError(Exception):
    """Raised when the canonical reference pack cannot be built from its inputs.

    Reserved for a structurally-insufficient input state — a required confirmed
    array (:data:`_REQUIRED_NONEMPTY`) is empty because a mandatory Tier 3/4
    source is absent.  Surfaced by the component wrapper as an
    ``AGENT_EXECUTION_ERROR`` node block (fail-closed, §12.4).
    """


def _confirmed(entry: dict[str, Any]) -> dict[str, Any]:
    """Tag a lifted confirmed entry with ``provenance: "confirmed"`` (in place)."""
    entry["provenance"] = PROVENANCE_CONFIRMED
    return entry


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


def _lift(
    source: dict[str, Any],
    keys: tuple[str, ...],
    aliases: dict[str, str],
) -> dict[str, Any]:
    """Copy *keys* out of *source* verbatim, honouring *aliases* for absent keys.

    *aliases* maps a **pack** key to the Tier-3 **source** key carrying the same
    value (:data:`_OBJECTIVE_ALIASES`, :data:`_OUTCOME_ALIASES`).  The canonical
    key always wins; an alias is consulted only when the canonical key is absent,
    so a source that already speaks the pack contract round-trips unchanged.

    Values are copied by reference with no coercion, no defaults, and no
    derivation — the rename is the only transformation, keeping the deriver a
    lookup-plus-verbatim-copy (§17.5.3).  Keys absent under both their canonical
    and alias name are simply omitted, never fabricated.
    """
    entry: dict[str, Any] = {}
    for key in keys:
        if key in source:
            entry[key] = source[key]
            continue
        alias = aliases.get(key)
        if alias is not None and alias in source:
            entry[key] = source[alias]
    return entry


def _extract_objectives(data: dict) -> list[dict[str, Any]]:
    """Extract objectives preserving id, title, measurable_target, responsible_partner.

    Accepts the hand-lift Tier-3 spelling (``objective_id`` /
    ``measurable_output``) via :data:`_OBJECTIVE_ALIASES`.
    """
    result: list[dict[str, Any]] = []
    for obj in data.get("objectives", []):
        if not isinstance(obj, dict):
            continue
        entry = _lift(obj, _OBJECTIVE_KEYS, _OBJECTIVE_ALIASES)
        if entry.get("id"):
            result.append(_confirmed(entry))
    return result


def _extract_outcomes(data: dict) -> list[dict[str, Any]]:
    """Extract outcomes preserving id, title, linked_objectives, linked_wp_ids.

    Accepts the hand-lift Tier-3 spelling (``outcome_id`` / ``statement``) via
    :data:`_OUTCOME_ALIASES`.
    """
    result: list[dict[str, Any]] = []
    for out in data.get("outcomes", []):
        if not isinstance(out, dict):
            continue
        entry = _lift(out, _OUTCOME_KEYS, _OUTCOME_ALIASES)
        if entry.get("id"):
            result.append(_confirmed(entry))
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
            wps.append(_confirmed(wp_entry))
        for deliv in wp.get("deliverables", []):
            if not isinstance(deliv, dict):
                continue
            d_entry: dict[str, Any] = {}
            for key in ("deliverable_id", "title", "due_month", "type"):
                if key in deliv:
                    d_entry[key] = deliv[key]
            d_entry["parent_wp"] = wp.get("wp_id", "")
            if d_entry.get("deliverable_id"):
                deliverables.append(_confirmed(d_entry))
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
            result.append(_confirmed(entry))
    return result


def _extract_declared_assumptions(repo_root: Path) -> list[dict[str, Any]]:
    """Pass operator declarations through verbatim, tagged ``provenance: "assumed"``.

    Reads the Tier 3 ``working_assumptions.json`` substrate (ticket 15) via the
    shared reader and delegates the machine-entry rendering to
    :meth:`runner.working_assumptions.WorkingAssumptions.as_canonical_pack_entries`
    — the **single** renderer both this Tier-3-sourced deriver and the
    graph-sourced deriver (:mod:`runner.graph_canonical_pack`) share, so a
    declared value is quarantined identically in both and can never masquerade as
    a confirmed canonical fact.  No inference: the value/key/checklist_ref are
    copied verbatim.

    Fail-closed: a present-but-malformed file raises
    :class:`runner.working_assumptions.WorkingAssumptionsError`, which the
    component wrapper surfaces as an ``AGENT_EXECUTION_ERROR`` node block rather
    than silently dropping the operator's declaration.  An absent or empty file
    yields ``[]`` (the honest block, mode α).
    """
    return load_working_assumptions(repo_root).as_canonical_pack_entries()


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

    # Operator declarations (Tier 3 working_assumptions.json) — the same
    # source the prose is drafted from, quarantined here as provenance=assumed
    # so a declared value can never masquerade as a confirmed canonical fact.
    declared_assumptions = _extract_declared_assumptions(repo_root)

    pack = {
        "schema_id": SCHEMA_ID,
        "run_id": run_id,
        "objectives": objectives,
        "outcomes": outcomes,
        "wps": wps,
        "deliverables": deliverables,
        "partners": partners,
        "declared_assumptions": declared_assumptions,
        "aliases": [],
    }

    # Fail-closed backstop (§12.4): a Phase-8 drafting node reaching the deriver
    # with an empty required array means a mandatory Tier 3/4 source is absent —
    # the preservation predicates would then *vacuously* pass (they early-return
    # on empty arrays), so drafting could proceed unchecked.  Block instead.
    empty = [k for k in _REQUIRED_NONEMPTY if not pack[k]]
    if empty:
        raise CanonicalPackError(
            f"canonical reference pack has empty required array(s) {empty}; "
            f"a mandatory Tier 3/4 source is absent"
        )

    out_path = repo_root / CANONICAL_PACK_REL
    atomic_write_json(pack, out_path, prefix="canonical_pack_")
    log.info("Canonical reference pack written: %s", out_path)
    return out_path
