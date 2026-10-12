"""An open-deferral register: every item an approval left open, and what closes it.

A register is read from a JSON declaration. This module is the reader and the
checker. It carries no instrument name, no call name and no row list of its own
— those are the declaration's, exactly as a lane's areas are the declaration's
and not :mod:`harness.acceptance_lane`'s.

Why a register and not a ticket checkbox
----------------------------------------
An approval settles some things and defers others. The deferred ones then sit in
several records at once: a disposition row that says the private network has to
establish something, a table in the approval prose, a validation case kept for a
later run, a ticket criterion whose own precondition is unmet. Each is open for
its own reason, and none of them is closed by the package that contains it being
approved.

That is the failure this module exists to prevent. A milestone that accepts a
package inherits its deferrals, and an inherited deferral has no owner, no
closure evidence and no record that it is still open. A checkbox in a ticket
cannot hold one, because a checkbox has no room for the evidence that would
close it.

So a :class:`Row` names four things: what is open, who closes it, the evidence
that would close it, and whether that evidence requires a document this
repository does not hold. :func:`check` then enforces the one rule that makes
the register more than a list — a row marked ``closed`` with no closure
evidence fails.

What a register binds, and what it may not edit
-----------------------------------------------
A register is a successor artifact. It points at the records it reads and binds
each by sha256, under one of two roles:

* ``immutable_evidence`` — a historical record. Its bytes moving is an edit, and
  :attr:`RegisterCheck.edited_immutable_sources` reports it as one.
* ``tracked_input`` — a record allowed to move, such as a ticket ledger. Its
  bytes moving means the register is out of date, which
  :attr:`RegisterCheck.stale_tracked_inputs` reports separately.

Both fail the check. They are separate findings because an edited historical
record and a stale register are different defects with different fixes.

Every :class:`Row` cites one of those declared sources as ``path#pointer``, so
no row points at a record the register has not bound. The pointer has to resolve
as well: into a JSON record by field, and into any other record as text. A
reworded criterion or a renamed heading therefore fails the check instead of
pointing nowhere.

Statements are measured, not asserted
-------------------------------------
A register also carries :class:`Statement` rows — the sentences a reader needs
in order to not misread the numbers around them. Each declares at least one
:class:`Measurement`: a field of a bound record and the value it must hold. A
statement with no measurement fails the check, and a measurement the records
contradict fails it too. So the register's prose cannot drift away from the
records it describes, which is the rule V05 established for audit wording.

The measurement grammar is deliberately small: a ``/``-separated key path into
objects, with ``#N`` for a position in a list, and either ``expected`` or
``expected_length``. It is **not** the register-pointer dialect of
:func:`harness.esr_comparison.resolve_pointer`, which resolves a bare segment on
a keyed list by identity. Nothing here resolves by identity, and a reader should
not carry that rule across.

Nothing in this module writes. :func:`render_report` returns the reading for a
human as a string, and ``harness.commands.deferral_register`` is what puts it on
disk. The register itself is authored by a deterministic tool outside this
package — ``tools/author_deferral_register.py`` for the 2026-10-08 approval —
which may not import the harness, under the one-way boundary
``tests/harness/test_boundary.py`` enforces. The split is also the right one on
its own terms: a tool that both wrote a record and certified it would be judging
its own output.

This module stays importable and offline, so a declaration is testable on its
own.
"""

from __future__ import annotations

import hashlib
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from runner.paths import find_repo_root

#: The declaration schema this reader understands. An authoring tool carries its
#: own copy, because it may not import this package; a register's own test
#: module is where the two are asserted equal.
SCHEMA = "deferral_register/1"


class DeferralRegisterError(ValueError):
    """A declaration this reader refuses to read."""


#: What kind of open item a row holds. Closed, so a new category is a decision
#: rather than a typo that reads as one.
KINDS: tuple[str, ...] = (
    # A ticket acceptance criterion left unchecked because its own precondition
    # is unmet.
    "ticket_criterion",
    # A row an approval deferred to a decision made outside this repository.
    "operator_decision_required",
    # A row carrying an agent's declaration the approval did not address.
    "agent_recommendation",
    # A row whose disposition is settled and whose interpretation is qualified
    # or deferred anyway.
    "qualified_interpretation",
    # A case kept for a later assessor run rather than acted on now.
    "assessor_validation_case",
    # A row whose declared status is Unresolved.
    "unresolved_disposition",
    # A question an approval's own prose defers, with the evidence it needs.
    "deferred_question",
)

#: A row is open or closed. There is no third state: a row half-closed is open,
#: and its progress belongs in its subject rather than in a status word.
STATES: tuple[str, ...] = ("open", "closed")

#: How a bound record is treated when its bytes move.
SOURCE_ROLES: tuple[str, ...] = ("immutable_evidence", "tracked_input")

#: Who has reviewed the register. The vocabulary the sibling Tier 4 records use,
#: so a reader does not meet a third spelling of the same fact.
REVIEW_STATES: tuple[str, ...] = ("agent_drafted_pending_operator_review", "operator_reviewed")

#: The four evidence statuses CLAUDE.md section 12.2 defines.
STATUSES: tuple[str, ...] = ("Confirmed", "Inferred", "Assumed", "Unresolved")


def file_sha256(path: Path) -> str:
    """The sha256 of *path*'s bytes, hex, no prefix."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# The declaration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Source:
    """One record the register reads, bound by hash."""

    #: Repository-relative, POSIX separators.
    path: str
    sha256: str
    #: One of :data:`SOURCE_ROLES`.
    role: str
    #: What this record holds, in a sentence. Read by a human, so a row's
    #: pointer can be followed without opening the file first.
    holds: str


@dataclass(frozen=True)
class Row:
    """One open item."""

    id: str
    #: One of :data:`KINDS`.
    kind: str
    #: What is open, in a sentence.
    subject: str
    #: Who closes it. A role, never a name this repository does not hold.
    owner: str
    #: The evidence that would close it. Required: a row without one is an item
    #: nobody can finish, not an item waiting.
    closure_evidence: str
    #: Whether the closure evidence requires the submitted original, which this
    #: repository does not hold.
    original_required: bool
    #: ``path#pointer`` into a declared source.
    source: str
    #: One of :data:`STATES`.
    state: str = "open"
    #: What must happen before this row can even be worked. An unmet
    #: precondition is why a criterion stays unchecked rather than failing.
    precondition: str = ""
    #: The observations this row is about, where it is about any. Several rows
    #: can name one observation for different reasons, and one row can name
    #: several. Both are what let a reader see the overlap rather than count
    #: one thing twice.
    observation_ids: tuple[str, ...] = ()
    #: Where the closure is recorded. Required when :attr:`state` is closed.
    closed_by: tuple[str, ...] = ()
    closed_on: str = ""

    @property
    def closure_cited(self) -> tuple[str, ...]:
        """The non-empty closure references."""
        return tuple(ref for ref in self.closed_by if ref.strip())


@dataclass(frozen=True)
class Measurement:
    """A field of a bound record, and the value it must hold."""

    id: str
    #: What this measurement shows, in a few words.
    claim: str
    #: Repository-relative path of a declared source.
    record: str
    #: A ``/``-separated key path. ``#N`` indexes a list by position.
    field: str
    #: Exactly one of these is declared.
    expected: Any = None
    expected_length: int | None = None


@dataclass(frozen=True)
class Statement:
    """A sentence the register asserts, and the measurements that carry it."""

    id: str
    claim: str
    measurements: tuple[Measurement, ...]


@dataclass(frozen=True)
class Register:
    """A register declaration, as read from its JSON file."""

    name: str
    #: What the register is of. Data, so this module names no instrument.
    subject: str
    authored_on: str
    #: Why the register exists, in the author's words.
    purpose: str
    #: Who has reviewed the register, in the vocabulary the sibling records use.
    #: Required: a register with no review state reads as reviewed.
    review_state: str
    #: The status of the register's own reading of its records, in the four
    #: terms CLAUDE.md section 12.2 defines. Required for the same reason.
    declared_status: str
    #: What this register supersedes, or why it supersedes nothing. Required: a
    #: register whose relationship to an earlier one is absent reads as the
    #: first.
    supersedes: str
    #: What the register's author is unsure of. Held in the artifact rather
    #: than only in a report, so a reader of the record alone sees it.
    uncertainties: tuple[str, ...]
    sources: tuple[Source, ...]
    statements: tuple[Statement, ...]
    rows: tuple[Row, ...]
    #: Where this declaration was read from, repository-relative.
    source: str
    #: What wrote the declaration. Printed in the reading, so a human knows
    #: which command re-derives it.
    written_by: str = ""

    # -- reading the rows --------------------------------------------------- #

    def open_rows(self) -> tuple[Row, ...]:
        return tuple(r for r in self.rows if r.state == "open")

    def closed_rows(self) -> tuple[str, ...]:
        return tuple(r.id for r in self.rows if r.state == "closed")

    def open_rows_by_kind(self) -> dict[str, int]:
        """Open rows counted per kind, in :data:`KINDS` order.

        Kinds with no open row are left out, so the mapping reads as what is
        open rather than as a table of zeroes.
        """
        counts = {kind: 0 for kind in KINDS}
        for row in self.open_rows():
            counts[row.kind] += 1
        return {kind: n for kind, n in counts.items() if n}

    def rows_requiring_the_original(self) -> tuple[str, ...]:
        """Open rows whose closure evidence this repository cannot hold."""
        return tuple(r.id for r in self.open_rows() if r.original_required)

    def observations(self) -> dict[str, tuple[str, ...]]:
        """Each named observation mapped to the rows that name it.

        Several rows over one observation is the normal case: a deferred
        question and a qualified interpretation can both be open about the same
        observation. The mapping is what keeps a reader from reading them as
        independent items.
        """
        found: dict[str, list[str]] = {}
        for row in self.rows:
            for observation_id in row.observation_ids:
                found.setdefault(observation_id, []).append(row.id)
        return {key: tuple(value) for key, value in sorted(found.items())}

    def source_paths(self) -> tuple[str, ...]:
        return tuple(s.path for s in self.sources)


# --------------------------------------------------------------------------- #
# Reading a declaration
# --------------------------------------------------------------------------- #


def _root(repo_root: Path | None) -> Path:
    """*repo_root*, or the root this file sits in."""
    if repo_root is not None:
        return repo_root
    return find_repo_root(Path(__file__).resolve().parent)


def _required(raw: Mapping[str, Any], key: str, source: str) -> Any:
    if key not in raw:
        raise DeferralRegisterError(f"{source}: the declaration has no {key!r}")
    return raw[key]


def _one_of(value: Any, allowed: Sequence[str], field: str, source: str) -> str:
    if value not in allowed:
        raise DeferralRegisterError(
            f"{source}: {field} is {value!r}; expected one of {', '.join(allowed)}"
        )
    return str(value)


def _measurement(raw: Mapping[str, Any], source: str) -> Measurement:
    ident = _required(raw, "id", source)
    has_value = "expected" in raw
    has_length = "expected_length" in raw
    if has_value == has_length:
        raise DeferralRegisterError(
            f"{source}: measurement {ident} declares "
            + ("both expected and expected_length" if has_value else "no expected value")
        )
    return Measurement(
        id=ident,
        claim=_required(raw, "claim", source),
        record=_required(raw, "record", source),
        field=_required(raw, "field", source),
        expected=raw.get("expected"),
        expected_length=int(raw["expected_length"]) if has_length else None,
    )


def _row(raw: Mapping[str, Any], source: str) -> Row:
    ident = _required(raw, "id", source)
    where = f"{source}: row {ident}"
    original = _required(raw, "original_required", source)
    if not isinstance(original, bool):
        raise DeferralRegisterError(f"{where}: original_required is not a boolean")
    return Row(
        id=ident,
        kind=_one_of(_required(raw, "kind", source), KINDS, "kind", where),
        subject=_required(raw, "subject", source),
        owner=_required(raw, "owner", source),
        closure_evidence=_required(raw, "closure_evidence", source),
        original_required=original,
        source=_required(raw, "source", source),
        state=_one_of(raw.get("state", "open"), STATES, "state", where),
        precondition=str(raw.get("precondition", "")),
        observation_ids=tuple(raw.get("observation_ids", ()) or ()),
        closed_by=tuple(raw.get("closed_by", ()) or ()),
        closed_on=str(raw.get("closed_on", "")),
    )


def load_register(path: Path, repo_root: Path | None = None) -> Register:
    """Read a register declaration.

    Fails closed on a missing field, an unknown kind, an unknown state and an
    unknown source role. A register read with half a declaration would report a
    green check over half a claim, which is the inheritance this module exists
    to stop.
    """
    root = _root(repo_root)
    try:
        source = path.relative_to(root).as_posix()
    except ValueError:
        source = path.as_posix()
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    schema = raw.get("schema")
    if schema != SCHEMA:
        raise DeferralRegisterError(f"{source}: schema is {schema!r}, expected {SCHEMA!r}")

    sources = tuple(
        Source(
            path=_required(s, "path", source),
            sha256=_required(s, "sha256", source),
            role=_one_of(_required(s, "role", source), SOURCE_ROLES, "role", source),
            holds=_required(s, "holds", source),
        )
        for s in _required(raw, "sources", source)
    )
    statements = tuple(
        Statement(
            id=_required(st, "id", source),
            claim=_required(st, "claim", source),
            measurements=tuple(
                _measurement(m, source) for m in _required(st, "measurements", source)
            ),
        )
        for st in raw.get("statements", ())
    )
    rows = tuple(_row(r, source) for r in _required(raw, "rows", source))
    return Register(
        name=_required(raw, "register_name", source),
        subject=_required(raw, "subject", source),
        authored_on=_required(raw, "authored_on", source),
        purpose=_required(raw, "purpose", source),
        review_state=_one_of(
            _required(raw, "review_state", source), REVIEW_STATES, "review_state", source
        ),
        declared_status=_one_of(
            _required(raw, "declared_status", source), STATUSES, "declared_status", source
        ),
        supersedes=_required(raw, "supersedes", source),
        uncertainties=tuple(_required(raw, "uncertainties", source)),
        sources=sources,
        statements=statements,
        rows=rows,
        source=source,
        written_by=str(raw.get("written_by", "")),
    )


# --------------------------------------------------------------------------- #
# Resolving a measurement
# --------------------------------------------------------------------------- #


class _Unresolved:
    """The field did not resolve. Distinct from a resolved ``None``."""


UNRESOLVED = _Unresolved()


@dataclass(frozen=True)
class _Unreadable:
    """A bound record that could not be parsed, and why."""

    why: str


def resolve_field(data: Any, field: str) -> Any:
    """Resolve *field* into *data*, or :data:`UNRESOLVED`.

    A segment indexes an object by key. ``#N`` indexes a list by position.
    Nothing resolves by identity — see this module's docstring on why that rule
    is deliberately absent.
    """
    node: Any = data
    for seg in [s for s in field.split("/") if s != ""]:
        if isinstance(node, Mapping):
            if seg not in node:
                return UNRESOLVED
            node = node[seg]
        elif isinstance(node, list) and seg.startswith("#"):
            index = seg[1:]
            if not index.lstrip("-").isdigit():
                return UNRESOLVED
            try:
                node = node[int(index)]
            except IndexError:
                return UNRESOLVED
        else:
            return UNRESOLVED
    return node


# --------------------------------------------------------------------------- #
# Checking
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RegisterCheck:
    """A register read against the records it binds."""

    closed_without_evidence: tuple[str, ...] = ()
    closed_without_date: tuple[str, ...] = ()
    open_rows_carrying_closure: tuple[str, ...] = ()
    rows_missing_field: tuple[str, ...] = ()
    duplicate_row_ids: tuple[str, ...] = ()
    rows_citing_undeclared_source: tuple[str, ...] = ()
    rows_whose_pointer_does_not_resolve: tuple[str, ...] = ()
    measurements_citing_undeclared_source: tuple[str, ...] = ()
    missing_sources: tuple[str, ...] = ()
    edited_immutable_sources: tuple[str, ...] = ()
    stale_tracked_inputs: tuple[str, ...] = ()
    statements_without_measurement: tuple[str, ...] = ()
    failed_measurements: tuple[str, ...] = ()

    @property
    def green(self) -> bool:
        """Every finding empty."""
        return not any(getattr(self, f.name) for f in self.__dataclass_fields__.values())

    def lines(self) -> tuple[str, ...]:
        """The check for a human, one finding per line."""
        labels = (
            ("closed_without_evidence", "CLOSED WITHOUT EVIDENCE"),
            ("closed_without_date", "CLOSED WITHOUT A DATE   "),
            ("open_rows_carrying_closure", "OPEN, EVIDENCE FILED   "),
            ("rows_missing_field", "ROW FIELD EMPTY        "),
            ("duplicate_row_ids", "DUPLICATE ROW ID       "),
            ("rows_citing_undeclared_source", "ROW CITES UNBOUND      "),
            ("rows_whose_pointer_does_not_resolve", "ROW POINTER LOST       "),
            ("measurements_citing_undeclared_source", "MEASURES UNBOUND       "),
            ("missing_sources", "SOURCE ABSENT          "),
            ("edited_immutable_sources", "EDITED HISTORICAL      "),
            ("stale_tracked_inputs", "STALE AGAINST INPUT    "),
            ("statements_without_measurement", "STATEMENT UNMEASURED   "),
            ("failed_measurements", "MEASUREMENT FAILED     "),
        )
        out: list[str] = []
        for attr, label in labels:
            for item in getattr(self, attr):
                out.append(f"{label}  {item}")
        return tuple(out)


def _pointer_resolves(path: Path, pointer: str) -> bool:
    """Whether *pointer* names something in the record at *path*.

    A JSON record resolves it with :func:`resolve_field`. Any other record —
    the Markdown an approval is written in, say — must carry it as text, so a
    renamed heading or a reworded criterion is caught rather than silently
    pointing nowhere.
    """
    if not pointer:
        return True
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except ValueError:
            return False
        return resolve_field(data, pointer) is not UNRESOLVED
    return pointer in path.read_text(encoding="utf-8-sig")


def _check_rows(
    register: Register, repo_root: Path, unreadable: frozenset[str]
) -> dict[str, tuple[str, ...]]:
    closed_without_evidence: list[str] = []
    closed_without_date: list[str] = []
    open_carrying: list[str] = []
    missing_field: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    declared = set(register.source_paths())
    unbound: list[str] = []
    lost: list[str] = []

    for row in register.rows:
        if row.id in seen:
            if row.id not in duplicates:
                duplicates.append(row.id)
        seen.add(row.id)

        for name in ("subject", "owner", "closure_evidence", "source"):
            if not str(getattr(row, name)).strip():
                missing_field.append(f"{row.id}: {name}")

        if row.state == "closed":
            if not row.closure_cited:
                closed_without_evidence.append(row.id)
            if not row.closed_on.strip():
                closed_without_date.append(row.id)
        elif row.closure_cited:
            open_carrying.append(row.id)

        path, _, pointer = row.source.partition("#")
        if path and path not in declared:
            unbound.append(f"{row.id}: {path}")
        elif path and path not in unreadable and not _pointer_resolves(repo_root / path, pointer):
            lost.append(f"{row.id}: {pointer}")

    return {
        "closed_without_evidence": tuple(closed_without_evidence),
        "closed_without_date": tuple(closed_without_date),
        "open_rows_carrying_closure": tuple(open_carrying),
        "rows_missing_field": tuple(missing_field),
        "duplicate_row_ids": tuple(duplicates),
        "rows_citing_undeclared_source": tuple(unbound),
        "rows_whose_pointer_does_not_resolve": tuple(lost),
    }


def _check_sources(register: Register, repo_root: Path) -> dict[str, tuple[str, ...]]:
    missing: list[str] = []
    edited: list[str] = []
    stale: list[str] = []
    for source in register.sources:
        path = repo_root / source.path
        if not path.is_file():
            missing.append(source.path)
            continue
        if file_sha256(path) != source.sha256:
            if source.role == "immutable_evidence":
                edited.append(source.path)
            else:
                stale.append(source.path)
    return {
        "missing_sources": tuple(missing),
        "edited_immutable_sources": tuple(edited),
        "stale_tracked_inputs": tuple(stale),
    }


def _check_statements(register: Register, repo_root: Path) -> dict[str, tuple[str, ...]]:
    unmeasured = tuple(st.id for st in register.statements if not st.measurements)
    declared = set(register.source_paths())
    unbound: list[str] = []
    failed: list[str] = []
    cache: dict[str, Any] = {}

    for statement in register.statements:
        for m in statement.measurements:
            if m.record not in declared:
                unbound.append(f"{m.id}: {m.record}")
                continue
            if m.record not in cache:
                path = repo_root / m.record
                try:
                    cache[m.record] = json.loads(path.read_text(encoding="utf-8-sig"))
                except (OSError, ValueError) as exc:
                    # Kept distinct from a lost field. A record that cannot be
                    # read at all is a different defect from one whose shape
                    # moved, and reporting the second for the first sends a
                    # reader to the wrong place.
                    cache[m.record] = _Unreadable(f"{type(exc).__name__}")
            data = cache[m.record]
            if isinstance(data, _Unreadable):
                failed.append(f"{m.id}: {m.record} is not readable JSON ({data.why})")
                continue
            value = resolve_field(data, m.field)
            if value is UNRESOLVED:
                failed.append(f"{m.id}: {m.field} does not resolve")
                continue
            if m.expected_length is not None:
                if not isinstance(value, (list, tuple, str, dict)):
                    failed.append(f"{m.id}: {m.field} has no length")
                elif len(value) != m.expected_length:
                    failed.append(
                        f"{m.id}: {m.field} has length {len(value)}, "
                        f"expected {m.expected_length}"
                    )
            elif value != m.expected:
                failed.append(f"{m.id}: {m.field} is {value!r}, expected {m.expected!r}")

    return {
        "statements_without_measurement": unmeasured,
        "measurements_citing_undeclared_source": tuple(unbound),
        "failed_measurements": tuple(failed),
    }


def check(register: Register, repo_root: Path | None = None) -> RegisterCheck:
    """Read *register* against the records it binds.

    The rule that matters is the first finding: a row marked ``closed`` with no
    closure evidence fails. Everything else keeps the register readable — a row
    that cites a record the register has not bound, a historical record whose
    bytes moved, a statement with nothing measuring it.
    """
    root = _root(repo_root)
    sources = _check_sources(register, root)
    # A pointer into a record that is not on disk is one defect, not two: the
    # absent source is already reported.
    unreadable = frozenset(sources["missing_sources"])
    findings: dict[str, tuple[str, ...]] = {}
    findings.update(_check_rows(register, root, unreadable))
    findings.update(sources)
    findings.update(_check_statements(register, root))
    return RegisterCheck(**findings)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _one_line(text: str) -> str:
    """*text* with its newlines collapsed, for a table cell."""
    return " ".join(str(text).split())


def _wrap(text: str) -> str:
    """*text* hard-wrapped, the width the repository's rendered reports use."""
    return "\n".join(textwrap.wrap(_one_line(text), width=98))


def _kind_heading(kind: str) -> str:
    return kind.replace("_", " ")


def render_report(register: Register) -> str:
    """The register for a human reader."""
    out: list[str] = []
    add = out.append
    open_rows = register.open_rows()
    by_kind = register.open_rows_by_kind()
    needing = register.rows_requiring_the_original()

    add(f"# Open-deferral register — {register.subject}")
    add("")
    add(f"Authored {register.authored_on}. Register `{register.name}`,")
    add(f"schema `{SCHEMA}`, written by `{register.written_by}`.")
    add("")
    add(f"Review state: **{register.review_state.replace('_', ' ')}**.")
    add(f"The register's own reading of its records is declared **{register.declared_status}**.")
    add(f"Relationship to earlier versions: {register.supersedes}")
    add("")
    observed = register.observations()
    unobserved = sum(1 for r in register.rows if not r.observation_ids)
    closed = register.closed_rows()
    tally = (
        f"{len(open_rows)} items are open and none is closed."
        if not closed
        else f"{len(open_rows)} items are open and {len(closed)} are closed, each with the "
        "evidence that closed it."
    )
    add(
        _wrap(
            f"{tally} {len(needing)} of the open ones need the submitted original, which this "
            f"repository does not hold. They are not {len(register.rows)} independent items: "
            f"{len(register.rows) - unobserved} rows name {len(observed)} distinct observations "
            f"between them, and the other {unobserved} name none. Closing one row closes "
            "neither the other rows over its observation nor the observation itself. Every row "
            "is derived from a record bound below by sha256. A row marked closed without "
            "closure evidence fails `harness.deferral_register.check`."
        )
    )
    add("")

    add("## What is open")
    add("")
    add("| Kind | Open | Needs the original |")
    add("|---|---|---|")
    for kind, count in by_kind.items():
        needs = sum(1 for r in open_rows if r.kind == kind and r.original_required)
        add(f"| {_kind_heading(kind)} | {count} | {needs} |")
    add(f"| **total** | **{len(open_rows)}** | **{len(needing)}** |")
    add("")

    add("## What the numbers do not say")
    add("")
    for statement in register.statements:
        add(f"**{statement.id}.** {statement.claim}")
        add("")
        add("| Measurement | Record | Field |")
        add("|---|---|---|")
        for m in statement.measurements:
            add(f"| {m.claim} | `{m.record.rsplit('/', 1)[-1]}` | `{m.field}` |")
        add("")

    add("## The rows")
    add("")
    for kind in KINDS:
        rows = [r for r in register.rows if r.kind == kind]
        if not rows:
            continue
        add(f"### {_kind_heading(kind).capitalize()} ({len(rows)})")
        add("")
        for row in rows:
            add(f"#### {row.id}")
            add("")
            add(row.subject)
            add("")
            if row.precondition:
                add(f"- Precondition: {row.precondition}")
            add(f"- Owner: {row.owner}")
            add(f"- Closes on: {row.closure_evidence}")
            add(f"- Needs the original: {'yes' if row.original_required else 'no'}")
            add(f"- State: {row.state}")
            if row.state == "closed":
                add(f"- Closed on: {row.closed_on or 'no date recorded'}")
                for ref in row.closure_cited:
                    add(f"- Closed by: {ref}")
            add(f"- Source: `{row.source}`")
            add("")

    observations = {k: v for k, v in observed.items() if len(v) > 1}
    if observations:
        add("## Rows that name the same observation")
        add("")
        add(
            _wrap(
                "Several rows over one observation is the normal case. One row can defer a "
                "question while another carries an unresolved status over the same observation. "
                "The rows are not independent items, and closing one closes neither the other "
                "nor the observation."
            )
        )
        add("")
        add("| Observation | Rows |")
        add("|---|---|")
        for key, ids in observations.items():
            add(f"| {key} | {', '.join(ids)} |")
        add("")

    if register.uncertainties:
        add("## What the author of this register is unsure of")
        add("")
        for item in register.uncertainties:
            add(f"- {item}")
        add("")

    add("## The records this register binds")
    add("")
    add("| Record | Role | Holds |")
    add("|---|---|---|")
    for source in register.sources:
        add(f"| `{source.path}` | {source.role.replace('_', ' ')} | {source.holds} |")
    add("")
    add(
        _wrap(
            "An immutable record whose bytes move is an edit and fails the check. A tracked "
            "input is allowed to move, and the register is then stale and has to be re-derived."
        )
    )
    add("")
    return "\n".join(out)
