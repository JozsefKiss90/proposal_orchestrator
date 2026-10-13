"""Reading a historical pre-evaluation profile against the matrix it was authored from.

A historical profile scores a closed call's submission under that call's rules.
Its whole claim is that each of its elements is either sourced to a row of an
equivalence matrix, or declared open because a row of that matrix is open. This
module reads the written profile and reports where that claim does not hold.

It is a separate module from the tool that writes the profile on purpose. A tool
that both wrote a record and certified it would be judging its own output, and
the finding that matters here is exactly the one such a tool would never report:
an element that claims a row which does not say what the element needs.

Six ways the claim can fail, each a finding rather than a sentence in a report:

* **An element names a row that is not in the matrix.** The source is a label,
  not a citation.
* **An element is sourced to a row that cannot source it.** A row recording that
  something is unresolved cannot establish a value. An element resting on one
  claims the matrix settled what it recorded as open.
* **A row no element reads.** The matrix is the profile's whole source, so a row
  nobody reads is a rule the profile ignores in silence.
* **A limitation whose row is no longer open.** The matrix has since sourced it,
  and the profile is understating what is known.
* **A pinned input that moved.** The profile was derived from particular bytes.
  Different bytes make it stale, and scoring under a stale profile is scoring
  under rules nobody checked.
* **A status the matrix cannot carry.** A profile cannot be more certain than
  the matrix it is authored from.

This module names no instrument and no year. The declaration supplies both.

Constitutional authority:
    Subordinate to CLAUDE.md. Out-of-band QA; reads the profile and the matrix
    read-only and writes nothing. Never a runtime gate. See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from harness.record_binding import (
    REVIEW_STATES,
    STATUSES,
    file_sha256,
    one_line,
    wrap,
)

__all__ = [
    "SCHEMA",
    "PROFILE_DIR",
    "discover_declarations",
    "SOURCING_VERDICTS",
    "HistoricalProfileError",
    "SourcedElement",
    "DeclaredLimitation",
    "PinnedInput",
    "HistoricalProfile",
    "ProfileCheck",
    "load_historical_profile",
    "load_matrix_rows",
    "check",
    "render",
]

#: The schema this reader understands. The authoring tool carries its own copy,
#: and the tests assert the two agree. Deliberate double entry: a tool may not
#: import this package.
SCHEMA = "pre_evaluation_profile/historical/1"

#: Verdicts that state what a closed call's rule was, and so may source an
#: element. Anything else records that something is open.
SOURCING_VERDICTS: tuple[str, ...] = ("equivalent", "differs", "era_neutral")


#: Where profile declarations live, relative to the repository root.
PROFILE_DIR = Path("harness/profiles")


class HistoricalProfileError(ValueError):
    """A declaration this reader refuses to read."""


def discover_declarations(repo_root: Path) -> list[Path]:
    """Every declaration under :data:`PROFILE_DIR` carrying :data:`SCHEMA`.

    Found by schema rather than by filename, because a filename would name an
    instrument and this package may not. A caller that gets other than one
    path asks the operator which, rather than picking.
    """
    found: list[Path] = []
    for path in sorted((repo_root / PROFILE_DIR).glob("*.json")):
        try:
            head = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        if f'"{SCHEMA}"' in head:
            found.append(path)
    return found


# --------------------------------------------------------------------------- #
# The declaration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SourcedElement:
    """One profile element and the rows that establish its value."""

    name: str
    rows: tuple[str, ...]
    #: The verdict the declaration recorded for each row, in the same order.
    #: Compared against the matrix, so a declaration that went stale shows up.
    declared_verdicts: tuple[str, ...]


@dataclass(frozen=True)
class DeclaredLimitation:
    """One element the matrix leaves open, and what the profile says instead."""

    element: str
    row: str
    declared_verdict: str
    limitation: str


@dataclass(frozen=True)
class PinnedInput:
    """A record the profile was derived from, pinned by the hash of its bytes."""

    name: str
    path: str
    sha256: str


@dataclass(frozen=True)
class HistoricalProfile:
    """A historical profile declaration, parsed."""

    profile_id: str
    label: str
    authored_on: str
    review_state: str
    declared_status: str
    purpose: str
    sourced: tuple[SourcedElement, ...]
    limitations: tuple[DeclaredLimitation, ...]
    harness_own: tuple[SourcedElement, ...]
    inputs: tuple[PinnedInput, ...]
    counterpart: PinnedInput | None
    #: Where this declaration was read from.
    source: str = ""
    written_by: str = ""

    def elements_read(self) -> frozenset[str]:
        """Every matrix row this profile reads, however it reads it."""
        rows: set[str] = set()
        for element in self.sourced:
            rows.update(element.rows)
        for element in self.harness_own:
            rows.update(element.rows)
        for limitation in self.limitations:
            rows.add(limitation.row)
        return frozenset(rows)


def _required(raw: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in raw:
        raise HistoricalProfileError(f"{where}: {key} is missing")
    return raw[key]


def _one_of(value: Any, allowed: tuple[str, ...], field_name: str, where: str) -> str:
    if value not in allowed:
        raise HistoricalProfileError(
            f"{where}: {field_name} is {value!r}; expected one of {', '.join(allowed)}"
        )
    return str(value)


def _pin(raw: Mapping[str, Any], name: str, where: str) -> PinnedInput:
    return PinnedInput(
        name=name,
        path=str(_required(raw, "path", where)),
        sha256=str(_required(raw, "sha256", where)),
    )


def load_historical_profile(path: Path) -> HistoricalProfile:
    """Read a historical profile declaration, fail-closed."""
    source = path.as_posix()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise HistoricalProfileError(f"{source}: not readable JSON ({exc})") from exc
    if not isinstance(raw, Mapping):
        raise HistoricalProfileError(f"{source}: not a JSON object")
    schema = raw.get("schema")
    if schema != SCHEMA:
        raise HistoricalProfileError(f"{source}: schema is {schema!r}, expected {SCHEMA!r}")

    sourced_raw = _required(raw, "sourced_from_the_matrix", source)
    if not isinstance(sourced_raw, Mapping):
        raise HistoricalProfileError(f"{source}: sourced_from_the_matrix is not an object")
    sourced: list[SourcedElement] = []
    for name, body in sourced_raw.items():
        where = f"{source}: element {name}"
        rows = tuple(str(r) for r in _required(body, "matrix_rows", where))
        verdicts = tuple(str(v) for v in _required(body, "verdicts", where))
        if len(rows) != len(verdicts):
            raise HistoricalProfileError(
                f"{where}: {len(rows)} rows and {len(verdicts)} verdicts; one per row"
            )
        if not rows:
            raise HistoricalProfileError(f"{where}: sourced, yet names no row")
        sourced.append(SourcedElement(name=name, rows=rows, declared_verdicts=verdicts))

    limitations: list[DeclaredLimitation] = []
    for body in _required(raw, "declared_limitations", source):
        where = f"{source}: a declared limitation"
        element = str(_required(body, "element", where))
        limitation = str(_required(body, "limitation", where))
        if not limitation.strip():
            raise HistoricalProfileError(
                f"{source}: element {element} is declared limited and says nothing"
            )
        limitations.append(
            DeclaredLimitation(
                element=element,
                row=str(_required(body, "matrix_row", where)),
                declared_verdict=str(_required(body, "verdict", where)),
                limitation=limitation,
            )
        )

    harness_own: list[SourcedElement] = []
    for body in raw.get("the_harness_own_instruments", ()) or ():
        where = f"{source}: a harness-own element"
        element = str(_required(body, "element", where))
        why = str(_required(body, "why", where))
        if not why.strip():
            raise HistoricalProfileError(
                f"{source}: element {element} is declared this harness's own and says nothing"
            )
        harness_own.append(
            SourcedElement(
                name=element,
                rows=tuple(str(r) for r in _required(body, "matrix_rows", where)),
                declared_verdicts=(),
            )
        )

    authored_from = _required(raw, "authored_from", source)
    inputs = tuple(
        _pin(authored_from[key], key, f"{source}: authored_from/{key}")
        for key in authored_from
        if isinstance(authored_from.get(key), Mapping)
    )
    if not inputs:
        raise HistoricalProfileError(f"{source}: authored_from pins nothing")

    counterpart_raw = raw.get("counterpart")
    counterpart = (
        _pin(counterpart_raw, "counterpart", f"{source}: counterpart")
        if isinstance(counterpart_raw, Mapping)
        else None
    )

    return HistoricalProfile(
        profile_id=str(_required(raw, "profile_id", source)),
        label=str(raw.get("label", "")),
        authored_on=str(_required(raw, "authored_on", source)),
        review_state=_one_of(
            _required(raw, "review_state", source), REVIEW_STATES, "review_state", source
        ),
        declared_status=_one_of(
            _required(raw, "declared_status", source), STATUSES, "declared_status", source
        ),
        purpose=str(_required(raw, "purpose", source)),
        sourced=tuple(sourced),
        limitations=tuple(limitations),
        harness_own=tuple(harness_own),
        inputs=inputs,
        counterpart=counterpart,
        source=source,
        written_by=str(raw.get("written_by", "")),
    )


def load_matrix_rows(path: Path) -> dict[str, str]:
    """Row id to verdict, for the matrix a profile was authored from."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise HistoricalProfileError(f"{path.as_posix()}: not readable JSON ({exc})") from exc
    rows: dict[str, str] = {}
    for row in raw.get("rows", ()):
        rows[str(row["id"])] = str(row["verdict"])
    if not rows:
        raise HistoricalProfileError(f"{path.as_posix()}: carries no rows")
    return rows


# --------------------------------------------------------------------------- #
# The check
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProfileCheck:
    """A historical profile read against its matrix and its pinned inputs."""

    elements_naming_a_missing_row: tuple[str, ...] = ()
    elements_sourced_to_a_row_that_cannot_source: tuple[str, ...] = ()
    rows_no_element_reads: tuple[str, ...] = ()
    limitations_whose_row_is_no_longer_open: tuple[str, ...] = ()
    verdicts_the_declaration_has_wrong: tuple[str, ...] = ()
    stale_inputs: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    counterpart_moved: tuple[str, ...] = ()
    status_the_matrix_cannot_carry: tuple[str, ...] = ()

    @property
    def green(self) -> bool:
        return not any(getattr(self, f) for f in self.__dataclass_fields__)

    @property
    def findings_total(self) -> int:
        return sum(len(getattr(self, f)) for f in self.__dataclass_fields__)

    def lines(self) -> tuple[str, ...]:
        out: list[str] = []
        for attr in self.__dataclass_fields__:
            label = attr.replace("_", " ").upper()
            for item in getattr(self, attr):
                out.append(f"{label}: {item}")
        return tuple(out)


def check(
    profile: HistoricalProfile,
    matrix_rows: Mapping[str, str],
    repo_root: Path,
    matrix_status: str = "",
) -> ProfileCheck:
    """Read *profile* against *matrix_rows* and the bytes it pinned.

    The finding that matters is the second: an element resting on a row that
    records something as open. That is the profile claiming the matrix settled
    what the matrix said it had not.
    """
    missing_row: list[str] = []
    cannot_source: list[str] = []
    wrong_verdict: list[str] = []
    no_longer_open: list[str] = []

    for element in profile.sourced:
        for position, row_id in enumerate(element.rows):
            verdict = matrix_rows.get(row_id)
            if verdict is None:
                missing_row.append(f"{element.name}: {row_id}")
                continue
            if verdict not in SOURCING_VERDICTS:
                cannot_source.append(f"{element.name}: {row_id} is {verdict}")
            declared = element.declared_verdicts[position]
            if declared != verdict:
                wrong_verdict.append(
                    f"{element.name}: {row_id} declared {declared}, the matrix says {verdict}"
                )

    for element in profile.harness_own:
        for row_id in element.rows:
            if row_id not in matrix_rows:
                missing_row.append(f"{element.name}: {row_id}")

    for limitation in profile.limitations:
        verdict = matrix_rows.get(limitation.row)
        if verdict is None:
            missing_row.append(f"{limitation.element}: {limitation.row}")
            continue
        if verdict in SOURCING_VERDICTS:
            # The matrix has since settled it. The profile is understating what
            # is known, which is a smaller fault than overstating it and still
            # a drift between two committed records.
            no_longer_open.append(
                f"{limitation.element}: {limitation.row} is now {verdict}"
            )
        if limitation.declared_verdict != verdict:
            wrong_verdict.append(
                f"{limitation.element}: {limitation.row} declared "
                f"{limitation.declared_verdict}, the matrix says {verdict}"
            )

    unread = tuple(sorted(set(matrix_rows) - profile.elements_read()))

    stale: list[str] = []
    missing: list[str] = []
    for pinned in profile.inputs:
        path = repo_root / pinned.path
        if not path.is_file():
            missing.append(f"{pinned.name}: {pinned.path}")
        elif file_sha256(path) != pinned.sha256:
            stale.append(f"{pinned.name}: {pinned.path}")

    moved: list[str] = []
    if profile.counterpart is not None:
        path = repo_root / profile.counterpart.path
        if not path.is_file():
            missing.append(f"counterpart: {profile.counterpart.path}")
        elif file_sha256(path) != profile.counterpart.sha256:
            # The ticket requires the other profile be left alone. Its bytes
            # moving is that requirement failing, reported here because this is
            # the record that pinned them.
            moved.append(profile.counterpart.path)

    over_certain: list[str] = []
    if matrix_status and profile.declared_status != matrix_status:
        order = {name: position for position, name in enumerate(STATUSES)}
        if order.get(profile.declared_status, 99) < order.get(matrix_status, 99):
            over_certain.append(
                f"the profile declares {profile.declared_status} and the matrix it was "
                f"authored from declares {matrix_status}"
            )

    return ProfileCheck(
        elements_naming_a_missing_row=tuple(missing_row),
        elements_sourced_to_a_row_that_cannot_source=tuple(cannot_source),
        rows_no_element_reads=unread,
        limitations_whose_row_is_no_longer_open=tuple(no_longer_open),
        verdicts_the_declaration_has_wrong=tuple(wrong_verdict),
        stale_inputs=tuple(stale),
        missing_inputs=tuple(missing),
        counterpart_moved=tuple(moved),
        status_the_matrix_cannot_carry=tuple(over_certain),
    )


# --------------------------------------------------------------------------- #
# The reading
# --------------------------------------------------------------------------- #


def render(profile: HistoricalProfile, matrix_rows: Mapping[str, str]) -> str:
    """The reading a human checks the profile by."""
    lines: list[str] = []
    add = lines.append

    add(f"# Historical pre-evaluation profile — {profile.label or profile.profile_id}")
    add("")
    add(f"Authored {profile.authored_on}. Profile `{profile.profile_id}`, schema `{SCHEMA}`,")
    add(f"written by `{profile.written_by}`.")
    add("")
    add(f"Review state: **{profile.review_state.replace('_', ' ')}**.")
    add(f"The profile's own reading of its sources is declared **{profile.declared_status}**.")
    add("")
    add(wrap(profile.purpose))
    add("")

    add("## What the matrix sources")
    add("")
    add("| Element | Matrix rows | Verdicts |")
    add("|---|---|---|")
    for element in sorted(profile.sourced, key=lambda e: e.name):
        verdicts = ", ".join(matrix_rows.get(r, "not in the matrix") for r in element.rows)
        add(f"| {element.name} | {', '.join(f'`{r}`' for r in element.rows)} | {verdicts} |")
    add("")

    if profile.limitations:
        add("## What the matrix leaves open")
        add("")
        for limitation in profile.limitations:
            verdict = matrix_rows.get(limitation.row, "not in the matrix")
            add(f"**{limitation.element}** — row `{limitation.row}` ({verdict})")
            add("")
            add(wrap(limitation.limitation))
            add("")

    if profile.harness_own:
        add("## What neither call states")
        add("")
        add(
            wrap(
                "These are this harness's own instruments, not rules of either call. The matrix "
                "carries their rows as era neutral, so reusing them is a reuse of an instrument "
                "and not a finding that a call prescribed it."
            )
        )
        add("")
        add("| Element | Matrix rows |")
        add("|---|---|")
        for element in profile.harness_own:
            add(f"| {element.name} | {', '.join(f'`{r}`' for r in element.rows)} |")
        add("")

    add("## What it was derived from")
    add("")
    add("| Record | Path | sha256 |")
    add("|---|---|---|")
    for pinned in profile.inputs:
        add(f"| {pinned.name} | `{pinned.path}` | `{pinned.sha256}` |")
    if profile.counterpart is not None:
        add(
            f"| counterpart, not edited | `{profile.counterpart.path}` | "
            f"`{profile.counterpart.sha256}` |"
        )
    add("")
    add(
        wrap(
            "Every one is pinned by the sha256 of its bytes. A profile read beside a record "
            "that has moved is stale, and the check reports it rather than scoring under it."
        )
    )
    add("")
    return "\n".join(lines) + "\n"
