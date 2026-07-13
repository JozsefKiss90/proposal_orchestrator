"""
Tier 3 ``working_assumptions.json`` declaration substrate — the shared reader
(CLAUDE.md §9 / §12.2, ticket 15).

``working_assumptions.json`` is the Tier 3 file convention by which a **human
operator** declares working assumptions.  It is the single mechanism that turns
an *honest block* into a *conscious green* (MILESTONE1_DECISION_RECORD.md D11):
the engine defaults to blocking on unconfirmed spine facts (researcher / host /
call), and the operator may declare those facts as working assumptions —
flagged ``Assumed``, never ``Confirmed`` — to unblock the run consciously.

**Two consumers, one reader (D11/D12).**  A single host declaration must unlock
*both* gates from one source:

  * the **budget gate** (ticket 8, ``runner/unit_cost_budget.py``) reads the
    declared host country to resolve the unit-cost living-allowance
    coefficient, and
  * the **claim layer** (ticket 9, the ``assumed_claims_are_operator_declared``
    W1 predicate) reads the declarations to confirm that every ``status:
    assumed`` claim maps by ``claim_id`` to a ``manually_placed`` declaration
    whose declared value equals the claim's ``claim_summary``.

The host is a *semantic* declaration, not a prose claim: the budget reads it by
key (``declared_value("host_country")`` → an ISO code), while the applier/W1
reach the spine claims it backs through :meth:`WorkingAssumptions.by_checklist_ref`
(e.g. ``HOST``).  So the operator declares the host **once** and both gates
resolve from that one entry (D11/D12) — the ``key``-vs-``claim_id`` match and the
``checklist_ref`` bridge are two distinct lookups this reader offers, not a
single value doing double duty.  This module owns those lookups; which one W1
uses is ticket 9's decision.

This module is that shared reader.  It owns the schema/convention and the
lookups both consumers use.  The **applier** (which flips ``Unresolved →
Assumed`` pre-assembly) and the **W1 predicate** remain ticket 9; this ticket
delivers only the convention, schema, and reader.

**Read-only substrate (§9).**  ``working_assumptions.json`` is
``provenance_class: manually_placed`` — user-authored, engine-read-only.  This
module *reads* it and exposes no writer.  No ``run_produced`` path may create,
modify, or back it (a ``run_produced`` artifact can never stand in for an
operator declaration — enforced downstream by W1, ticket 9).

**Absent / empty is a valid state.**  An absent file, a blank file, ``{}``,
``{"declarations": []}``, or ``{"declarations": null}`` all mean *no
declarations* — the honest block (mode α).  That is a correct terminal state
(§12.4 / §15), never an error.

**Fail-closed on a present-but-malformed file.**  A file that exists with real
declarations but is invalid JSON, has the wrong root shape, declares a bad
``provenance_class``, is missing a required per-entry field, or carries a
duplicate key raises :class:`WorkingAssumptionsError`.  A silent swallow would
hide a declaration the operator believes is active; surfacing the fault loudly
is both fail-closed and legible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def declared_claim_summary(value: Any) -> str:
    """Render an operator-declared value as the string a claim carries.

    A section claim's ``claim_summary`` is always a string (§ schema), while a
    declaration's ``value`` may be any non-null JSON scalar (an ISO country
    code, an integer duration, …).  This is the **single** normalisation both
    ticket-9 consumers share, so they cannot drift:

      * the **applier** stamps ``claim_summary = declared_claim_summary(value)``
        when it flips a declared ``unresolved → assumed`` claim, and
      * the **W1 predicate** accepts an ``assumed`` claim iff its
        ``claim_summary`` equals ``declared_claim_summary(value)`` for the
        matching declaration.

    A string value is used verbatim (identity); any non-string is rendered as
    canonical, key-sorted JSON so the mapping is deterministic and byte-stable.
    """
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

# ---------------------------------------------------------------------------
# Constants — the convention
# ---------------------------------------------------------------------------

#: Canonical Tier 3 path of the operator declaration file (repo-relative).
WORKING_ASSUMPTIONS_REL: str = (
    "docs/tier3_project_instantiation/working_assumptions.json"
)

#: The provenance class the file must declare — user-authored, engine-read-only
#: (§9; §12.2 validation vocabulary).  Enforced when the file carries real
#: declarations.
PROVENANCE_CLASS: str = "manually_placed"

#: The validation-status a declared assumption carries in any surface (§12.2).
#: A green bought by declaration is legible as ``Assumed`` — never ``Confirmed``.
DECLARED_STATUS: str = "Assumed"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class WorkingAssumptionsError(Exception):
    """Raised when a *present* ``working_assumptions.json`` is malformed.

    Reserved for a file that exists and carries content the reader cannot
    trust: invalid JSON, a non-object root, a non-array ``declarations``, a
    missing/blank required per-entry field, a null declared value, a bad
    ``provenance_class``, or a duplicate declaration key.  An **absent or
    empty** file is *not* an error — it is the honest block (α).
    """


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Declaration:
    """One operator-declared working assumption.

    Attributes
    ----------
    key:
        Stable declaration key — *either* a semantic lookup token the budget
        deriver reads (e.g. ``host_country``, ticket 8) *or* a ``claim_id`` the
        W1 predicate matches (ticket 9), depending on what the entry declares.
        A semantic declaration is bridged to the spine claims it backs via
        :attr:`checklist_ref` (see the module docstring), so one host
        declaration serves both consumers without a single value doing double
        duty.
    value:
        The operator-declared value.  Any non-null JSON scalar/string; W1
        checks it equals the backing claim's ``claim_summary``.
    declared_by:
        Attribution — who declared the assumption.
    declared_on:
        Timestamp — when it was declared (ISO 8601 by convention).
    rationale:
        Optional operator justification.
    checklist_ref:
        Optional link to a ``confirmation_checklist.json`` spine token (e.g.
        ``HOST``), so one host declaration is discoverable by the same token
        that names the gap it fills (D11/D12).
    """

    key: str
    value: Any
    declared_by: str
    declared_on: str
    rationale: Optional[str] = None
    checklist_ref: Optional[str] = None


@dataclass(frozen=True)
class WorkingAssumptions:
    """The parsed declaration substrate — the single source both consumers read.

    An empty instance (no declarations) is the honest block (α); it answers
    every lookup with ``None``/``()`` and an empty surface, so a consumer needs
    no special-casing for the absent-file case.
    """

    present: bool
    declarations: tuple[Declaration, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        """``True`` when there are no declarations (the honest block, α)."""
        return len(self.declarations) == 0

    def declaration(self, key: str) -> Optional[Declaration]:
        """Return the declaration with *key*, or ``None`` if undeclared."""
        for decl in self.declarations:
            if decl.key == key:
                return decl
        return None

    def declared_value(self, key: str) -> Optional[Any]:
        """Return the operator-declared value for *key*, or ``None``.

        The budget deriver's host lookup (ticket 8):
        ``declared_value("host_country")``.
        """
        decl = self.declaration(key)
        return decl.value if decl is not None else None

    def by_checklist_ref(self, ref: str) -> tuple[Declaration, ...]:
        """Return all declarations linked to a confirmation-checklist token.

        Lets the applier / surfacing (ticket 9 / ticket 13) find the
        declaration(s) that fill a named spine gap (e.g. ``HOST``) — the same
        source the budget reads for the coefficient (D11/D12).
        """
        return tuple(d for d in self.declarations if d.checklist_ref == ref)

    def as_surface(self) -> list[dict[str, Any]]:
        """Render the declarations as a legible *declared* surface.

        Each entry is marked ``status: Assumed`` (§12.2) and
        ``provenance_class: manually_placed`` so a green bought by declaration
        is legible as **declared, not confirmed** when surfaced in a
        confirmation checklist or a traceability footer (ticket-15 criterion;
        wired into outputs by tickets 9/13).
        """
        return [
            {
                "key": d.key,
                "declared_value": d.value,
                "status": DECLARED_STATUS,
                "provenance_class": PROVENANCE_CLASS,
                "declared_by": d.declared_by,
                "declared_on": d.declared_on,
                "checklist_ref": d.checklist_ref,
            }
            for d in self.declarations
        ]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _require_str(entry: dict[str, Any], field_name: str, index: int) -> str:
    """Return a required, non-blank string field, or raise naming it."""
    if field_name not in entry:
        raise WorkingAssumptionsError(
            f"declaration[{index}] is missing required field '{field_name}'"
        )
    value = entry[field_name]
    if not isinstance(value, str) or not value.strip():
        raise WorkingAssumptionsError(
            f"declaration[{index}] field '{field_name}' must be a non-empty "
            f"string, got {value!r}"
        )
    return value.strip()


def _parse_declaration(entry: Any, index: int) -> Declaration:
    """Validate and parse one declaration entry, failing closed."""
    if not isinstance(entry, dict):
        raise WorkingAssumptionsError(
            f"declaration[{index}] must be a JSON object, got "
            f"{type(entry).__name__}"
        )

    key = _require_str(entry, "key", index)
    declared_by = _require_str(entry, "declared_by", index)
    declared_on = _require_str(entry, "declared_on", index)

    # ``value`` may be any non-null JSON type (a string identity, an int
    # duration, ...).  An explicit null declares nothing (fail closed).
    if "value" not in entry:
        raise WorkingAssumptionsError(
            f"declaration[{index}] (key {key!r}) is missing required field "
            f"'value'"
        )
    value = entry["value"]
    if value is None:
        raise WorkingAssumptionsError(
            f"declaration[{index}] (key {key!r}) has a null 'value'; a "
            f"declaration must declare a concrete value"
        )
    # A blank string declares nothing; reject it loudly rather than let a
    # consumer silently degrade it to a block (declarations are never silent).
    if isinstance(value, str) and not value.strip():
        raise WorkingAssumptionsError(
            f"declaration[{index}] (key {key!r}) has a blank string 'value'; a "
            f"declaration must declare a concrete value"
        )

    rationale = entry.get("rationale")
    if rationale is not None and not isinstance(rationale, str):
        raise WorkingAssumptionsError(
            f"declaration[{index}] (key {key!r}) field 'rationale' must be a "
            f"string when present"
        )
    checklist_ref = entry.get("checklist_ref")
    if checklist_ref is not None and not isinstance(checklist_ref, str):
        raise WorkingAssumptionsError(
            f"declaration[{index}] (key {key!r}) field 'checklist_ref' must be "
            f"a string when present"
        )

    return Declaration(
        key=key,
        value=value,
        declared_by=declared_by,
        declared_on=declared_on,
        rationale=rationale,
        checklist_ref=checklist_ref,
    )


def load_working_assumptions(repo_root: Path) -> WorkingAssumptions:
    """Read the Tier 3 ``working_assumptions.json`` declaration substrate.

    This is the **shared reader** both consumers call (the budget deriver,
    ticket 8; the W1 claim check, ticket 9).  It reads — and never writes —
    the canonical Tier 3 file.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root.

    Returns
    -------
    WorkingAssumptions
        The parsed declarations.  An **absent** file returns
        ``WorkingAssumptions(present=False)``; a **blank / empty** file returns
        an empty-but-present instance.  Both are the honest block (α) and
        answer every lookup with ``None``/``()``.

    Raises
    ------
    WorkingAssumptionsError
        Only when the file is *present with content* and malformed — invalid
        JSON, a non-object root, a non-array ``declarations``, a bad
        ``provenance_class``, a missing/blank required per-entry field, a null
        value, or a duplicate key.  An absent or empty file never raises.
    """
    path = repo_root / WORKING_ASSUMPTIONS_REL

    if not path.is_file():
        return WorkingAssumptions(present=False)

    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise WorkingAssumptionsError(
            f"cannot read working_assumptions.json: {exc}"
        ) from exc

    # A blank file the operator created but left empty is a valid α state.
    if not text.strip():
        return WorkingAssumptions(present=True)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WorkingAssumptionsError(
            f"working_assumptions.json is not valid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise WorkingAssumptionsError(
            "working_assumptions.json root must be a JSON object"
        )

    raw_declarations = data.get("declarations", [])

    # No declarations — absent, ``null``, or ``[]`` — is the honest block (α);
    # nothing to govern, so provenance_class is not required here.  A ``null``
    # declarations value reads as "no declarations", equivalent to absent.
    if raw_declarations is None or raw_declarations == []:
        return WorkingAssumptions(present=True)

    if not isinstance(raw_declarations, list):
        raise WorkingAssumptionsError(
            "working_assumptions.json 'declarations' must be an array"
        )

    # Real declarations must follow the convention: provenance_class marks the
    # file as user-authored, engine-read-only (§9; ticket-15 criterion 1).
    provenance = data.get("provenance_class")
    if provenance != PROVENANCE_CLASS:
        raise WorkingAssumptionsError(
            f"working_assumptions.json must declare provenance_class "
            f"'{PROVENANCE_CLASS}' when it carries declarations (got "
            f"{provenance!r})"
        )

    declarations: list[Declaration] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw_declarations):
        decl = _parse_declaration(entry, index)
        if decl.key in seen:
            raise WorkingAssumptionsError(
                f"duplicate declaration key {decl.key!r}; each key must be "
                f"unique (it is the stable claim_id / declaration key)"
            )
        seen.add(decl.key)
        declarations.append(decl)

    return WorkingAssumptions(present=True, declarations=tuple(declarations))
