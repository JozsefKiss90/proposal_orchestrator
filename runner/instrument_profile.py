"""
Instrument-profile resolver.

Phase 8 and its gates must read the mandatory section/sub-section set, the
hard page limit, the budget regime, and which upstream phases are in scope
from a **per-instrument profile** keyed on the selected call's
``instrument_type`` — so the same engine serves MSCA-PF and RIA with no
instrument literal baked into the drafting path (CLAUDE.md §2, programme-
agnostic mission).

The profile is a *consolidation layer* over two Tier 2A extracted registries,
both keyed by ``instrument_type``:

  * ``section_schema_registry.json`` — the sub-section set and the hard Part B
    page limit (``part_b_page_limit_hard``), extracted from the application
    form (§10.6, page limit read from the form, not assumed).
  * ``instrument_registry.json`` — instrument-level metadata: the budget
    regime (``lump_sum`` | ``unit_cost``, the source ``gate_09`` branches on
    per C1) and the phases in scope.

This module performs **no domain reasoning** and reads only durable Tier 2A/3
state.  It **fails closed** (raises :class:`InstrumentProfileError`) when the
instrument type is absent or unknown, or when any required profile field is
missing — never a silent default (ticket-2 acceptance criterion; §12.4).

Constitutional authority:
    Subordinate to CLAUDE.md.  This resolver does not invent instrument facts;
    every value it returns traces to a Tier 2A extracted registry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SELECTED_CALL_REL: str = (
    "docs/tier3_project_instantiation/call_binding/selected_call.json"
)
SECTION_SCHEMA_REGISTRY_REL: str = (
    "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json"
)
INSTRUMENT_REGISTRY_REL: str = (
    "docs/tier2a_instrument_schemas/extracted/instrument_registry.json"
)

#: Valid budget regimes.  ``gate_09`` branches on this per the C1 amendment:
#: ``lump_sum`` → external Lump Sum Budget Planner response; ``unit_cost`` →
#: internal deterministic derivation (§8.1, §8.4).
VALID_BUDGET_REGIMES: frozenset[str] = frozenset({"lump_sum", "unit_cost"})


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class InstrumentProfileError(Exception):
    """Raised when an instrument profile cannot be resolved.

    Covers: absent/unknown ``instrument_type``, an instrument missing from a
    registry, or a required profile field missing or malformed.  The resolver
    never returns a partial or defaulted profile — it fails closed.
    """


# ---------------------------------------------------------------------------
# InstrumentProfile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InstrumentProfile:
    """The resolved per-instrument profile consumed by Phase 8 and its gates."""

    instrument_type: str
    """The selected call's instrument type (e.g. ``"RIA"``, ``"MSCA-PF"``)."""

    sub_sections: list[dict[str, Any]] = field(default_factory=list)
    """The full sub-section set from ``section_schema_registry.json`` — each a
    dict with at least ``section_id``, ``section_name``, ``mandatory``,
    ``section_type``.  Phase 8 reads section structure from here, not from an
    instrument literal."""

    hard_page_limit: int = 0
    """The hard Part B page limit (``part_b_page_limit_hard``) read from the
    application form.  The drafting path's target length derives from this,
    not from an assumed constant."""

    budget_regime: str = ""
    """``"lump_sum"`` or ``"unit_cost"`` — the source ``gate_09`` branches on
    (C1).  Never assumed; read from ``instrument_registry.json``."""

    phases_in_scope: list[int] = field(default_factory=list)
    """The canonical phase numbers in scope for this instrument (e.g.
    ``[1, 2, 3, 4, 5, 6, 7, 8]``).  The DAG topology is unchanged; this is the
    profile the engine consults."""

    @property
    def mandatory_sub_section_ids(self) -> list[str]:
        """Section ids of the mandatory sub-sections, in registry order."""
        return [
            s["section_id"]
            for s in self.sub_sections
            if s.get("mandatory") and s.get("section_id")
        ]

    @property
    def drafting_sub_sections(self) -> list[dict[str, Any]]:
        """Sub-sections that are drafted prose (``section_type`` in the
        proposal/implementation set) — the Phase 8 drafting granularity."""
        return [
            s
            for s in self.sub_sections
            if s.get("section_type")
            in ("proposal_section", "implementation_section")
        ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path, label: str) -> Any:
    """Read and parse a JSON file, failing closed on any issue."""
    if not path.is_file():
        raise InstrumentProfileError(f"{label} not found: {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise InstrumentProfileError(f"Cannot read {label}: {exc}") from exc
    if not text.strip():
        raise InstrumentProfileError(f"{label} is empty: {path}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise InstrumentProfileError(
            f"{label} is not valid JSON: {exc}"
        ) from exc


def _find_instrument_entry(
    data: Any, instrument_type: str, label: str
) -> dict[str, Any]:
    """Find the ``instruments[]`` entry for *instrument_type*.

    Expects the canonical registry shape ``{"instruments": [ {...}, ... ]}``
    where each entry carries an ``instrument_type`` key.  Fails closed when the
    registry is empty, malformed, or does not contain *instrument_type* — no
    silent default.
    """
    if not isinstance(data, dict):
        raise InstrumentProfileError(
            f"{label} root is not an object"
        )
    instruments = data.get("instruments")
    if not isinstance(instruments, list) or not instruments:
        raise InstrumentProfileError(
            f"{label} has no 'instruments' entries; cannot resolve "
            f"{instrument_type!r} (registry may be an unpopulated skeleton)"
        )
    for entry in instruments:
        if isinstance(entry, dict) and entry.get("instrument_type") == instrument_type:
            return entry
    known = [
        e.get("instrument_type")
        for e in instruments
        if isinstance(e, dict)
    ]
    raise InstrumentProfileError(
        f"Instrument {instrument_type!r} not found in {label}. "
        f"Known instruments: {known}"
    )


def resolve_instrument_type(repo_root: Path) -> str:
    """Resolve ``instrument_type`` from the Tier 3 call binding, fail-closed.

    Reads ``selected_call.json`` and returns its ``instrument_type``.  Raises
    :class:`InstrumentProfileError` when the file is missing/malformed or the
    field is absent or blank — never a default.
    """
    data = _read_json(repo_root / SELECTED_CALL_REL, "selected_call.json")
    if not isinstance(data, dict):
        raise InstrumentProfileError("selected_call.json root is not an object")
    value = data.get("instrument_type")
    if not isinstance(value, str) or not value.strip():
        raise InstrumentProfileError(
            "selected_call.json has no valid 'instrument_type' field"
        )
    return value.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_instrument_profile(
    repo_root: Path,
    instrument_type: Optional[str] = None,
) -> InstrumentProfile:
    """Resolve the per-instrument profile for the selected call.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root.
    instrument_type:
        The instrument type to resolve.  When ``None`` (the default), it is
        resolved from ``selected_call.json`` (fail-closed).

    Returns
    -------
    InstrumentProfile
        The consolidated profile: sub-section set, hard page limit, budget
        regime, and phases in scope.

    Raises
    ------
    InstrumentProfileError
        When the instrument type is absent or unknown, when an instrument is
        missing from either registry, or when a required field is missing or
        malformed.  The resolver never returns a partial or defaulted profile.
    """
    if instrument_type is None:
        instrument_type = resolve_instrument_type(repo_root)
    if not isinstance(instrument_type, str) or not instrument_type.strip():
        raise InstrumentProfileError(
            "instrument_type is absent or blank; cannot resolve profile"
        )
    instrument_type = instrument_type.strip()

    # ── Section structure + hard page limit (from the section schema) ──
    section_data = _read_json(
        repo_root / SECTION_SCHEMA_REGISTRY_REL, "section_schema_registry.json"
    )
    section_entry = _find_instrument_entry(
        section_data, instrument_type, "section_schema_registry.json"
    )

    sub_sections = section_entry.get("sections")
    if not isinstance(sub_sections, list) or not sub_sections:
        raise InstrumentProfileError(
            f"Instrument {instrument_type!r} has no 'sections' in "
            f"section_schema_registry.json"
        )

    hard_page_limit = section_entry.get("part_b_page_limit_hard")
    if not isinstance(hard_page_limit, int) or isinstance(hard_page_limit, bool):
        raise InstrumentProfileError(
            f"Instrument {instrument_type!r} has no integer "
            f"'part_b_page_limit_hard' in section_schema_registry.json "
            f"(page limit must be read from the form, not assumed)"
        )

    # ── Instrument-level metadata (budget regime + phases in scope) ────
    instrument_data = _read_json(
        repo_root / INSTRUMENT_REGISTRY_REL, "instrument_registry.json"
    )
    instrument_entry = _find_instrument_entry(
        instrument_data, instrument_type, "instrument_registry.json"
    )

    budget_regime = instrument_entry.get("budget_regime")
    if budget_regime not in VALID_BUDGET_REGIMES:
        raise InstrumentProfileError(
            f"Instrument {instrument_type!r} has invalid 'budget_regime' "
            f"{budget_regime!r} in instrument_registry.json; "
            f"expected one of {sorted(VALID_BUDGET_REGIMES)}"
        )

    phases_in_scope = instrument_entry.get("phases_in_scope")
    if (
        not isinstance(phases_in_scope, list)
        or not phases_in_scope
        or not all(
            isinstance(p, int) and not isinstance(p, bool)
            for p in phases_in_scope
        )
    ):
        raise InstrumentProfileError(
            f"Instrument {instrument_type!r} has invalid 'phases_in_scope' "
            f"in instrument_registry.json; expected a non-empty list of "
            f"integers"
        )

    return InstrumentProfile(
        instrument_type=instrument_type,
        sub_sections=sub_sections,
        hard_page_limit=hard_page_limit,
        budget_regime=budget_regime,
        phases_in_scope=list(phases_in_scope),
    )
