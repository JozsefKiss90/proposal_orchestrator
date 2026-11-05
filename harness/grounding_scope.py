"""
The grounding scope — what a blind run claims to have assessed (ticket V06).

Why this exists
---------------
A cell's coverage verdict judges two different things.  *Addressal* asks
whether the section addresses the expectation.  *Grounding* asks whether the
claims it makes are supported.  The second needs a claim ledger in the
evidence pack, and the blind lane over an imported proposal withholds that
ledger: ``--no-claims`` never opens it, so every cell's grounding is
``unassessable`` by construction.

Nothing in the records said so.  A later reader saw ten graded cells, a total
and no grounding findings, and could not tell an unassessable run from an
assessed one with nothing to report.  Proposal-internal coherence, scientific
plausibility, fidelity to the submitted text and independent factual support
are four different claims, and a record that leaves grounding unstated invites
the strongest of them to be read into the weakest evidence.

So every preflight, report and freeze now carries a **grounding scope**: the
operator's declaration of which assessment was intended, beside the
measurement of what the run could actually judge.

The two scope choices
---------------------
They are the readiness audit's own two, and no third exists:

:data:`SCOPE_CONTENT_FOCUSED`
    Blind assessment of proposal content and credibility, with grounding
    reported unassessable and the sources reviewed by a human instead.

:data:`SCOPE_SOURCE_GROUNDED`
    A claim that the proposal has been source-grounded or factually verified.
    This needs the imported-claim route — claims loading with resolvable
    sources, statuses backed by evidence, and E2 grounding over that ledger.
    None of the three exists yet, so :data:`IMPORTED_CLAIM_ROUTE_IMPLEMENTED`
    is ``False`` and :func:`declare_scope` refuses the declaration.  Ticket
    X01 implements and validates the route and flips the flag.

The measurement, and why it is not the declaration
--------------------------------------------------
:func:`measure` counts how many graded units carried a claim ledger and
returns :data:`GROUNDING_UNASSESSABLE`, :data:`GROUNDING_PARTLY_ASSESSED` or
:data:`GROUNDING_ASSESSED`.  It is arithmetic over the realised packs or the
recorded cells, so it cannot be overstated.  The declaration can: it is the
operator's intent, and the whole point of recording both is that the two can
be compared.  A ``source_grounded`` declaration over anything but a fully
assessed run is refused, and that rule outlives X01.

:attr:`GroundingScope.reason` is a property, not a stored sentence.  The
wording therefore cannot drift from the numbers beside it — the same reason
V05 stopped the audit's grounding wording coming from a constant.

A record that declares nothing
------------------------------
Reports written before this ticket carry no declaration.  :func:`measured_only`
builds their scope from the cells alone, and its ``declared`` is ``None``.
Derivation can only ever produce the conservative value, because
``source_grounded`` is a declaration and never a measurement; so a
measured-only record states what the run could judge and claims nothing.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA; pure vocabulary and arithmetic,
    reads and writes nothing.  Never a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

__all__ = [
    "SCOPE_CONTENT_FOCUSED",
    "SCOPE_SOURCE_GROUNDED",
    "GROUNDING_SCOPES",
    "GROUNDING_IN_VERDICT",
    "GROUNDING_UNASSESSABLE",
    "GROUNDING_PARTLY_ASSESSED",
    "GROUNDING_ASSESSED",
    "GROUNDING_MEASUREMENTS",
    "CELL_GROUNDING_VALUES",
    "UNIT_PACK",
    "UNIT_CELL",
    "DECLARED_BY_THE_RUN",
    "MEASURED_HERE",
    "IMPORTED_CLAIM_ROUTE_IMPLEMENTED",
    "GroundingScopeError",
    "GroundingScope",
    "measure",
    "count_grounded",
    "check_declarable",
    "declare_scope",
    "measured_only",
    "scope_for",
    "scope_lines",
    "declared_scope_of",
    "scope_from_record",
]

#: Blind assessment of proposal content and credibility; grounding is reported
#: unassessable and the sources are reviewed by a human instead.
SCOPE_CONTENT_FOCUSED: str = "content_focused"

#: A claim that the proposal has been source-grounded or factually verified.
#: Refused until the imported-claim route exists (ticket X01).
SCOPE_SOURCE_GROUNDED: str = "source_grounded"

#: The closed set of scope choices, least-claiming first.
GROUNDING_SCOPES: tuple[str, ...] = (SCOPE_CONTENT_FOCUSED, SCOPE_SOURCE_GROUNDED)

#: One cell's grounding value.  ``in_verdict``: the pack carried claim-ledger
#: entries, so the coverage verdict judged addressal and grounding together.
#: ``unassessable``: the pack carried no ledger — withheld
#: (``include_claims=False``) or empty — so grounding is neither passed nor
#: failed, and the addressal value must not be read as a clean score of both.
GROUNDING_IN_VERDICT: str = "in_verdict"
GROUNDING_UNASSESSABLE: str = "unassessable"

#: The run-level measurement, between the two extremes.
GROUNDING_PARTLY_ASSESSED: str = "partly_assessed"
GROUNDING_ASSESSED: str = "assessed"

#: The closed set of run-level measurements, least-assessed first.
GROUNDING_MEASUREMENTS: tuple[str, ...] = (
    GROUNDING_UNASSESSABLE,
    GROUNDING_PARTLY_ASSESSED,
    GROUNDING_ASSESSED,
)

#: The closed set of per-cell grounding values :func:`count_grounded` accepts.
CELL_GROUNDING_VALUES: tuple[str, ...] = (GROUNDING_IN_VERDICT, GROUNDING_UNASSESSABLE)

#: What was counted: a preflight counts realised packs, a report counts cells.
UNIT_PACK: str = "pack"
UNIT_CELL: str = "cell"

#: Where the scope in a record came from.
DECLARED_BY_THE_RUN: str = "declared_by_the_run"
MEASURED_HERE: str = "measured_here_the_run_declared_none"

#: Whether the imported-claim grounding route exists.  ``False`` until all
#: three of its parts do: imported-section claims loading with resolvable
#: sources, supported statuses backed by evidence, and E2 grounding running
#: over that ledger.  Ticket X01 implements and validates them and flips this.
#: :func:`declare_scope` and the baseline freeze both read this one flag, so a
#: source-grounded declaration cannot be made anywhere while it is ``False``.
IMPORTED_CLAIM_ROUTE_IMPLEMENTED: bool = False

#: What X01 owes, named in the refusal so the reader need not look it up.
_MISSING_INTEGRATIONS: tuple[str, ...] = (
    "imported-section claims loading with resolvable sources",
    "supported claim statuses backed by evidence",
    "E2 grounding running over that ledger",
)


class GroundingScopeError(Exception):
    """A grounding scope cannot be declared, or a record's scope is not what it claims."""


def measure(*, include_claims: bool, with_claims: int, total: int) -> str:
    """Which of :data:`GROUNDING_MEASUREMENTS` *with_claims* of *total* gives.

    Raises :class:`GroundingScopeError` on a count that cannot have happened:
    more grounded units than units, or a grounded unit at all when the ledger
    was withheld from every pack.
    """
    if with_claims < 0 or total < 0:
        raise GroundingScopeError(
            f"a negative count of graded units ({with_claims} of {total}) is not a measurement."
        )
    if with_claims > total:
        raise GroundingScopeError(
            f"{with_claims} unit(s) carried a claim ledger out of {total} graded; "
            "a count above the total is not a measurement."
        )
    if not include_claims and with_claims:
        raise GroundingScopeError(
            f"the claim ledger was withheld from every pack, yet {with_claims} unit(s) "
            "carry one; the run contradicts itself."
        )
    if with_claims == 0:
        return GROUNDING_UNASSESSABLE
    if with_claims < total:
        return GROUNDING_PARTLY_ASSESSED
    return GROUNDING_ASSESSED


def count_grounded(cells: Iterable[Mapping[str, Any]]) -> tuple[int, int]:
    """How many of *cells* carried a claim ledger, and how many there are.

    Reads each cell's recorded ``grounding`` value, so a persisted report can
    be re-measured without rebuilding its packs.  A cell carrying no grounding
    value, or one outside :data:`CELL_GROUNDING_VALUES`, is a refusal: an
    absent value would silently count as not grounded.
    """
    with_claims = total = 0
    for i, cell in enumerate(cells):
        total += 1
        value = cell.get("grounding") if isinstance(cell, Mapping) else None
        if value is None:
            raise GroundingScopeError(
                f"cell {i} carries no grounding value; grounding cannot be measured from it."
            )
        if value not in CELL_GROUNDING_VALUES:
            raise GroundingScopeError(
                f"cell {i} carries grounding {value!r}, not one of {CELL_GROUNDING_VALUES}."
            )
        with_claims += int(value == GROUNDING_IN_VERDICT)
    return with_claims, total


@dataclass(frozen=True)
class GroundingScope:
    """One run's declared scope beside what its grounding could be measured as.

    Build it through :func:`declare_scope` (an operator declared a scope) or
    :func:`measured_only` (the run declared none and this is the measurement).
    """

    declared: str | None
    measured: str
    include_claims: bool
    unit: str
    with_claims: int
    total: int

    def __post_init__(self) -> None:
        if self.declared is not None and self.declared not in GROUNDING_SCOPES:
            raise GroundingScopeError(f"unknown grounding scope {self.declared!r}.")
        if self.measured not in GROUNDING_MEASUREMENTS:
            raise GroundingScopeError(f"unknown grounding measurement {self.measured!r}.")
        if self.unit not in (UNIT_PACK, UNIT_CELL):
            raise GroundingScopeError(f"unknown graded unit {self.unit!r}.")

    @property
    def declaration_source(self) -> str:
        """:data:`DECLARED_BY_THE_RUN`, or :data:`MEASURED_HERE` when none was."""
        return DECLARED_BY_THE_RUN if self.declared is not None else MEASURED_HERE

    @property
    def assessable(self) -> bool:
        """Whether any graded unit's grounding was judged at all."""
        return self.measured != GROUNDING_UNASSESSABLE

    @property
    def reason(self) -> str:
        """Why grounding reads as it does, derived from the counts beside it."""
        unit = self.unit
        if self.total == 0:
            return f"no {unit} was produced, so grounding could not be judged"
        if self.measured == GROUNDING_UNASSESSABLE and not self.include_claims:
            return (
                "the claim ledger was withheld from every evidence pack, so no "
                f"{unit} carries one and grounding could not be judged"
            )
        if self.measured == GROUNDING_UNASSESSABLE:
            return (
                f"the claim ledger was offered but no {unit} carried an entry, so "
                "grounding could not be judged"
            )
        if self.measured == GROUNDING_PARTLY_ASSESSED:
            return (
                f"{self.with_claims} of {self.total} {unit}(s) carried a claim ledger; "
                "grounding could be judged for those alone"
            )
        return (
            f"every one of {self.total} {unit}(s) carried a claim ledger, so the coverage "
            "verdict judges addressal and grounding together"
        )

    @property
    def headline(self) -> str:
        """The one line every renderer prints, so all three print the same words."""
        return (
            f"GROUNDING  [{self.measured.upper()}]  declared scope: "
            f"{self.declared or 'none declared'}  "
            f"({self.with_claims} of {self.total} {self.unit}(s) carried a claim ledger)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "declared": self.declared,
            "declaration_source": self.declaration_source,
            "measured": self.measured,
            "include_claims": self.include_claims,
            "unit": self.unit,
            "with_claims": self.with_claims,
            "total": self.total,
            "reason": self.reason,
        }


def check_declarable(declared: str | None) -> None:
    """Refuse a scope nothing could make true, before a run happens.

    The two refusals that need no measurement: a value outside
    :data:`GROUNDING_SCOPES`, and :data:`SCOPE_SOURCE_GROUNDED` while
    :data:`IMPORTED_CLAIM_ROUTE_IMPLEMENTED` is ``False``.  A command calls
    this at parse time so a refused declaration costs no assessor quota;
    :func:`declare_scope` calls it again with the counts in hand.
    """
    if declared not in GROUNDING_SCOPES:
        raise GroundingScopeError(
            f"unknown grounding scope {declared!r}; declare one of {GROUNDING_SCOPES}."
        )
    if declared == SCOPE_SOURCE_GROUNDED and not IMPORTED_CLAIM_ROUTE_IMPLEMENTED:
        raise GroundingScopeError(
            f"a {SCOPE_SOURCE_GROUNDED!r} scope is refused: the imported-claim grounding "
            "route is not implemented, and three of its parts are missing — "
            + "; ".join(_MISSING_INTEGRATIONS)
            + f". Ticket X01 builds and validates them. Declare {SCOPE_CONTENT_FOCUSED!r} "
            "and have a human review the sources."
        )


def declare_scope(
    declared: str | None,
    *,
    include_claims: bool,
    with_claims: int,
    total: int,
    unit: str,
) -> GroundingScope:
    """The operator's *declared* scope, measured against what the run can judge.

    Raises :class:`GroundingScopeError` when *declared* is not one of
    :data:`GROUNDING_SCOPES`, when it is :data:`SCOPE_SOURCE_GROUNDED` while
    :data:`IMPORTED_CLAIM_ROUTE_IMPLEMENTED` is ``False``, or when it is
    :data:`SCOPE_SOURCE_GROUNDED` over a run whose grounding did not measure
    :data:`GROUNDING_ASSESSED`.  The last rule outlives X01.
    """
    check_declarable(declared)
    measured = measure(include_claims=include_claims, with_claims=with_claims, total=total)
    if declared == SCOPE_SOURCE_GROUNDED and measured != GROUNDING_ASSESSED:
        raise GroundingScopeError(
            f"a {SCOPE_SOURCE_GROUNDED!r} scope is refused: grounding measures "
            f"{measured!r} ({with_claims} of {total} {unit}(s) carried a claim ledger). "
            "Every graded unit must carry one."
        )
    return GroundingScope(
        declared=declared,
        measured=measured,
        include_claims=include_claims,
        unit=unit,
        with_claims=with_claims,
        total=total,
    )


def measured_only(
    *, include_claims: bool, with_claims: int, total: int, unit: str
) -> GroundingScope:
    """The measurement alone, for a run that declared no scope.

    ``declared`` is ``None`` and stays ``None``: derivation produces a
    measurement, never a claim.
    """
    return GroundingScope(
        declared=None,
        measured=measure(include_claims=include_claims, with_claims=with_claims, total=total),
        include_claims=include_claims,
        unit=unit,
        with_claims=with_claims,
        total=total,
    )


def scope_from_record(record: Mapping[str, Any]) -> GroundingScope | None:
    """The :class:`GroundingScope` *record* carries, or ``None`` when it carries none.

    The measurement is re-derived from the recorded counts rather than read,
    and a stored ``measured`` the counts do not give is a refusal.  So a
    reader cannot be told one thing by the label and another by the numbers.
    """
    block = record.get("grounding_scope")
    if not isinstance(block, Mapping):
        return None
    declared = block.get("declared")
    unit = block.get("unit")
    with_claims, total = block.get("with_claims"), block.get("total")
    if not isinstance(with_claims, int) or not isinstance(total, int):
        raise GroundingScopeError(
            f"the grounding scope records with_claims={with_claims!r} and total={total!r}; "
            "both must be whole numbers."
        )
    include_claims = block.get("include_claims")
    if not isinstance(include_claims, bool):
        raise GroundingScopeError(
            f"the grounding scope records include_claims={include_claims!r}; it must be a boolean."
        )
    if unit not in (UNIT_PACK, UNIT_CELL):
        raise GroundingScopeError(
            f"the grounding scope records unit={unit!r}; a record that does not say what it "
            f"counted cannot be re-measured. One of {(UNIT_PACK, UNIT_CELL)}."
        )
    scope = GroundingScope(
        declared=str(declared) if declared else None,
        measured=measure(include_claims=include_claims, with_claims=with_claims, total=total),
        include_claims=include_claims,
        unit=str(unit),
        with_claims=with_claims,
        total=total,
    )
    recorded = block.get("measured")
    if recorded is not None and recorded != scope.measured:
        raise GroundingScopeError(
            f"the grounding scope records measured={recorded!r}; {with_claims} of {total} "
            f"{scope.unit}(s) with a claim ledger gives {scope.measured!r}."
        )
    return scope


def scope_for(
    declared: str | None,
    *,
    include_claims: bool,
    with_claims: int,
    total: int,
    unit: str,
) -> GroundingScope:
    """The scope of a run: *declared* when one was, else the measurement alone.

    The one entry point every producer uses — the preflight, the report and the
    freeze — so "a declaration when there is one, a measurement when there is
    not" is written once rather than three times.
    """
    counts = {
        "include_claims": include_claims,
        "with_claims": with_claims,
        "total": total,
        "unit": unit,
    }
    if declared is None:
        return measured_only(**counts)
    return declare_scope(declared, **counts)


#: How far the reason is indented under its headline, in all three renderers.
_REASON_INDENT: str = " " * 11


def scope_lines(
    record: Mapping[str, Any], measured: Callable[[], GroundingScope]
) -> list[str]:
    """The two lines every renderer prints for one record's grounding scope.

    *measured* is called only when *record* carries no ``grounding_scope``
    block, and returns the scope measured from the record's own graded units.
    A record written before the declaration existed therefore still gets a
    grounding line — an absent one is the defect the block exists to close —
    and a record whose numbers cannot be measured says so rather than printing
    nothing.

    The headline and the reason are re-derived here, never read from the file,
    so a stored sentence cannot be printed beside numbers it contradicts.
    """
    try:
        scope = scope_from_record(record) or measured()
    except GroundingScopeError as exc:
        return [f"GROUNDING  [NOT MEASURABLE]  {exc}"]
    return [scope.headline, f"{_REASON_INDENT}{scope.reason}"]


def declared_scope_of(record: Mapping[str, Any]) -> str | None:
    """The scope *record* declares under ``grounding_scope``, or ``None``.

    Reads the declaration and nothing else, unlike :func:`scope_from_record`,
    which re-measures the whole block and refuses one it cannot.  That is the
    point for a caller comparing two records' declarations: a preflight whose
    recorded measurement has gone stale must still report the *declaration*
    that moved, rather than being refused before the comparison happens.

    ``None`` covers all three ways a record can decline to say: no block, a
    null block, and a block without a ``declared`` value.
    """
    block = record.get("grounding_scope")
    if not isinstance(block, Mapping):
        return None
    declared = block.get("declared")
    return str(declared) if declared else None
