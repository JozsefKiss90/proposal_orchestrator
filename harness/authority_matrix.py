"""A rule-equivalence matrix between a historical call and the call a profile was written for.

The problem this exists for
---------------------------
A proposal submitted under one year's call is assessed by a profile written for
another year's. Copying the profile and leaving a rule unchanged where no source
states a difference is a *defaulting policy*. It is not evidence that the rule
applied in the historical year, and a matrix that records it as equivalence
turns an absence of evidence into a sourced fact.

So this module's central rule is one refusal: a row may be marked
``equivalent`` or ``differs`` only when a citation behind it resolves into a
**historical-era** source the index records as obtained. A row resting only on
current-era sources is ``defaulted``, and a ``defaulted`` row has to name the
rule its defaulting affects. There is no verdict that means *nobody found a
difference*.

Two artifacts, one reader
-------------------------
A :class:`SourceIndex` is the authority documents, each pinned by sha256 and
each declaring three things a citation is checked against: which era's rules it
states, what class of authority it is, and how its bytes are vouched for. A
:class:`Matrix` is the rows, and it binds its index by hash — so an index edit
makes the matrix stale rather than silently changing what a row rests on.

The index is where a document's *absence* is recorded too. A required document
that has not been obtained is an entry with ``authentication: not_obtained``,
and a citation of one fails the check. That is what keeps a row from resting on
a document somebody intends to fetch.

Three ways a citation can overreach
-----------------------------------
Each is a finding rather than a sentence in a report, because each is a way the
matrix could read as sourced while not being so:

* **Beyond a record's measured scope.** A source may declare
  :class:`ScopeRestriction` entries: a field prefix, and the areas a passage
  under it settles. A form-equivalence record that measured section structure
  settles section structure. A citation of it from a row about thresholds is
  reported, not accepted.
* **Submission evidence read as a call rule.** A class in
  :data:`SUBMISSION_SCOPED_CLASSES` — an evaluation output, a record over the
  submission itself — evidences what was applied to *that* submission. A row
  claiming a call-wide rule on it alone is reported.
* **Confirmed on unvouched bytes.** A row may declare ``Confirmed`` only when a
  citation behind it rests on a source whose hash came from the issuing body. A
  document sitting in a repository with no recorded provenance is pinned, not
  authenticated, and a row over it is ``Inferred`` at best. An entry claiming
  any rank above ``computed_only`` must say where that is recorded, or the claim
  is the index author's own word — which is what the rank is supposed to improve
  on.

What this module is not
-----------------------
It carries no instrument name, no call identifier, no year and no row of its
own. The areas a matrix must cover are the declaration's ``required_areas``, the
era labels are the declaration's, and the rows are the authoring tool's. It
writes nothing: :func:`render_matrix` returns a reading as a string and
``harness.commands.authority_matrix`` is what puts it on disk. The matrix itself
is authored by a deterministic tool outside this package, which may not import
the harness under the one-way boundary ``tests/harness/test_boundary.py``
enforces — and which should not check its own output anyway.

Verbatim passages are re-derived, not checked here. A document citation declares
a page and the quote found on it; :func:`check` verifies the page exists in the
pinned document, and the matrix's own test module re-extracts the quote. This
module stays importable and offline, so a declaration is testable on its own.

Constitutional authority:
    Subordinate to CLAUDE.md. Out-of-band QA; reads declarations and the records
    they bind read-only and writes nothing. Never a runtime gate. See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from harness.record_binding import (
    REVIEW_STATES,
    SOURCE_ROLES,
    STATUSES,
    check_bindings,
    file_sha256,
)
from harness.record_binding import Unreadable as _Unreadable
from harness.record_binding import one_line as _one_line
from harness.record_binding import wrap as _wrap
from harness.record_pointer import UNRESOLVED, resolve_field
from runner.paths import find_repo_root

__all__ = [
    "AuthorityMatrixError",
    "SCHEMA_INDEX",
    "SCHEMA_MATRIX",
    "SOURCE_CLASSES",
    "ERAS",
    "AUTHENTICATIONS",
    "UNVOUCHED_AUTHENTICATIONS",
    "AUTHENTICATIONS_NEEDING_A_BASIS",
    "SUBMISSION_SCOPED_CLASSES",
    "VERDICTS",
    "SOURCED_VERDICTS",
    "SETTLEMENTS",
    "AFFECTS",
    "SOURCE_ROLES",
    "REVIEW_STATES",
    "STATUSES",
    "ScopeRestriction",
    "Source",
    "SourceIndex",
    "Citation",
    "Defaulting",
    "Measurement",
    "Row",
    "Matrix",
    "MatrixCheck",
    "file_sha256",
    "load_source_index",
    "load_matrix",
    "check",
    "render_index",
    "render_matrix",
]

#: The source-index schema this reader understands. An authoring tool carries
#: its own copy, because it may not import this package.
SCHEMA_INDEX = "authority_source_index/1"

#: The matrix schema this reader understands.
SCHEMA_MATRIX = "authority_equivalence_matrix/1"

#: What kind of authority a document is. Closed, so a new class is a decision
#: rather than a typo that reads as one.
SOURCE_CLASSES: tuple[str, ...] = (
    # The call's own conditions or topic text.
    "call_document",
    # The work programme part the call sits in.
    "work_programme",
    # Programme-wide guidance: general annexes, a programme guide.
    "programme_guidance",
    # The instrument's application form or Part B template.
    "instrument_application_form",
    # The instrument's evaluation form.
    "instrument_evaluation_form",
    # The evaluation output over one submission.
    "evaluation_output",
    # A provenance or fidelity record over the submission itself.
    "submission_record",
    # A configuration this repository derived from the documents above.
    "derived_configuration",
    # A decision record of this repository.
    "repository_decision",
)

#: Which era's rules a source states. The years themselves are the
#: declaration's: this module never names one.
ERAS: tuple[str, ...] = ("historical", "current", "cross_era")

#: How a source's bytes are vouched for.
AUTHENTICATIONS: tuple[str, ...] = (
    # An expected hash from the issuing body, matched against the file.
    "issuer_hash_confirmed",
    # The operator supplied the document itself, from the channel that issued it
    # to them. The bytes are pinned; no independent hash vouches for them.
    "operator_supplied",
    # Hashed in this tree. Nothing records where the bytes came from.
    "computed_only",
    # Not obtained. The entry records the absence.
    "not_obtained",
)

#: Authentications that claim somebody vouched for the bytes, and therefore
#: need a record saying who and where. ``computed_only`` claims nothing, so it
#: needs nothing.
AUTHENTICATIONS_NEEDING_A_BASIS: tuple[str, ...] = (
    "issuer_hash_confirmed",
    "operator_supplied",
)

#: Authentications that cannot carry a ``Confirmed`` row.
UNVOUCHED_AUTHENTICATIONS: tuple[str, ...] = (
    "operator_supplied",
    "computed_only",
    "not_obtained",
)

#: Classes whose evidence settles what was applied to one submission, and not a
#: rule of the call it was submitted to.
SUBMISSION_SCOPED_CLASSES: tuple[str, ...] = ("evaluation_output", "submission_record")

#: What a row concludes.
VERDICTS: tuple[str, ...] = (
    # The historical and the current rule are the same, and a historical source
    # says so.
    "equivalent",
    # They differ, and a historical source says so.
    "differs",
    # The current rule is carried forward because no historical source states
    # it. Not equivalence.
    "defaulted",
    # No source states the rule in either era, or the sources conflict.
    "unresolved",
    # The rule is not a call rule at all. It belongs to the assessing harness,
    # and no era states it.
    "era_neutral",
)

#: Verdicts that assert a relation between the two eras, and therefore need a
#: historical citation.
SOURCED_VERDICTS: tuple[str, ...] = ("equivalent", "differs")

#: How widely a row's conclusion reaches.
SETTLEMENTS: tuple[str, ...] = ("as_applied_to_this_submission", "call_wide")

#: What moves if a row's rule is wrong. The audit's own distinction.
AFFECTS: tuple[str, ...] = ("a number", "an interpretation", "both")

class AuthorityMatrixError(ValueError):
    """A declaration this reader refuses to read."""


# --------------------------------------------------------------------------- #
# The source index
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ScopeRestriction:
    """What a passage under one field prefix of a source settles, and no more.

    A record can measure one thing and be read as settling another. A
    form-equivalence record that measured section structure is the case this
    exists for: it settles section structure, and a row about weights that cites
    it has overreached.
    """

    #: A field-pointer prefix into the source.
    field_prefix: str
    #: The row areas a passage under that prefix may settle.
    settles_areas: tuple[str, ...]
    #: What was actually measured, in a sentence.
    measured: str

    def covers(self, field: str) -> bool:
        return bool(field) and field.startswith(self.field_prefix)


@dataclass(frozen=True)
class Source:
    """One authority document or record, pinned."""

    #: Repository-relative, POSIX separators.
    path: str
    #: One of :data:`SOURCE_CLASSES`.
    cls: str
    #: One of :data:`ERAS`.
    era: str
    #: One of :data:`AUTHENTICATIONS`.
    authentication: str
    #: What this source states, in a sentence.
    states: str
    #: One of :data:`SOURCE_ROLES`.
    role: str
    #: Where the authentication is recorded. Required when the authentication
    #: is one of :data:`AUTHENTICATIONS_NEEDING_A_BASIS`: a rank above
    #: ``computed_only`` has to point at the record that vouches for the bytes.
    authentication_basis: str = ""
    #: sha256 of the bytes. Empty exactly when the source is not obtained.
    sha256: str = ""
    #: The document's page count, where it is a paginated document. A page
    #: citation beyond it does not resolve.
    pages: int | None = None
    #: The version the document declares, where it declares one.
    version: str = ""
    #: Whether the matrix needs this source. A required source that is not
    #: obtained is the gap the index exists to record.
    required: bool = True
    #: The rows that would move if this source arrived. Derived by the authoring
    #: tool from the rows themselves, so it cannot drift from them.
    would_settle: tuple[str, ...] = ()
    scope_restrictions: tuple[ScopeRestriction, ...] = ()

    @property
    def obtained(self) -> bool:
        return self.authentication != "not_obtained"

    @property
    def vouched(self) -> bool:
        """Whether a ``Confirmed`` row may rest on this source."""
        return self.authentication not in UNVOUCHED_AUTHENTICATIONS

    @property
    def submission_scoped(self) -> bool:
        return self.cls in SUBMISSION_SCOPED_CLASSES

    def restriction_for(self, field: str) -> ScopeRestriction | None:
        for restriction in self.scope_restrictions:
            if restriction.covers(field):
                return restriction
        return None


@dataclass(frozen=True)
class SourceIndex:
    """The authority documents a matrix may cite."""

    name: str
    #: What the index is of. Data, so this module names no instrument.
    subject: str
    authored_on: str
    purpose: str
    #: How the declaration labels the two eras, for the reading.
    historical_label: str
    current_label: str
    #: Who has reviewed the index, in the vocabulary the sibling records use.
    review_state: str
    #: The status of the index's own reading of its documents.
    declared_status: str
    #: What this index supersedes, or why it supersedes nothing.
    supersedes: str
    #: What the author is unsure of, held in the artifact and not only a report.
    uncertainties: tuple[str, ...]
    sources: tuple[Source, ...]
    #: Where this declaration was read from, repository-relative.
    source: str
    written_by: str = ""

    def by_path(self) -> dict[str, Source]:
        return {s.path: s for s in self.sources}

    def obtained(self) -> tuple[Source, ...]:
        return tuple(s for s in self.sources if s.obtained)

    def missing_required(self) -> tuple[Source, ...]:
        return tuple(s for s in self.sources if s.required and not s.obtained)

    def by_era(self, era: str) -> tuple[Source, ...]:
        return tuple(s for s in self.sources if s.era == era)


# --------------------------------------------------------------------------- #
# The matrix
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Citation:
    """One located passage, and what it states."""

    #: The path of a source declared in the index.
    source: str
    #: What the passage states, in the author's words.
    states: str
    #: A pointer into a JSON source, or — where the source is not JSON and not
    #: paginated — the passage itself, which has to occur in the record as text.
    #: Exactly one of this and :attr:`page`.
    field: str = ""
    #: A page of a paginated source.
    page: int | None = None
    #: The verbatim passage, where the source is a document. Required with a
    #: page: a page number alone locates nothing a reader can check.
    quote: str = ""

    @property
    def locator(self) -> str:
        if self.page is not None:
            return f"page {self.page}"
        return self.field


@dataclass(frozen=True)
class Defaulting:
    """What a defaulted row carries forward, and what rides on it."""

    #: The source the rule is carried from.
    carried_from: str
    #: The rule the defaulting affects. Required: defaulting is recorded as
    #: defaulting, with its rule named.
    affected_rule: str
    #: What goes wrong if the historical rule turns out to differ.
    risk: str


@dataclass(frozen=True)
class Measurement:
    """A field of a bound source, and the value it must hold."""

    id: str
    claim: str
    record: str
    field: str
    expected: Any = None
    expected_length: int | None = None


@dataclass(frozen=True)
class Row:
    """One rule, and what the sources say about it across the two eras."""

    id: str
    #: The rule's area. Checked against the matrix's ``required_areas``.
    area: str
    #: The rule, in a sentence.
    rule: str
    #: One of :data:`AFFECTS`.
    affects: str
    #: One of :data:`VERDICTS`.
    verdict: str
    #: One of :data:`SETTLEMENTS`.
    settles: str
    #: One of :data:`STATUSES`, for this row's own conclusion.
    declared_status: str
    status_basis: str
    citations: tuple[Citation, ...]
    historical_value: str = ""
    current_value: str = ""
    #: Required when :attr:`verdict` is ``differs``.
    difference: str = ""
    #: Required when :attr:`verdict` is ``defaulted``.
    defaulting: Defaulting | None = None
    #: Required when :attr:`verdict` is ``unresolved``.
    limitation: str = ""
    #: Required when :attr:`verdict` is ``era_neutral``.
    why_era_neutral: str = ""
    #: What a historical profile must do about this row. The matrix's output to
    #: the profile authored from it.
    consequence: str = ""
    #: Paths of unobtained sources that would settle this row.
    would_be_settled_by: tuple[str, ...] = ()
    measurements: tuple[Measurement, ...] = ()

    @property
    def asserts_a_relation(self) -> bool:
        return self.verdict in SOURCED_VERDICTS


@dataclass(frozen=True)
class Matrix:
    """A matrix declaration, as read from its JSON file."""

    name: str
    subject: str
    authored_on: str
    purpose: str
    review_state: str
    declared_status: str
    supersedes: str
    uncertainties: tuple[str, ...]
    #: The areas this matrix must cover. The declaration's, not this module's.
    required_areas: tuple[str, ...]
    #: The index, by repository-relative path, and the hash it is bound at.
    index_path: str
    index_sha256: str
    rows: tuple[Row, ...]
    source: str
    written_by: str = ""

    def areas(self) -> tuple[str, ...]:
        seen: list[str] = []
        for row in self.rows:
            if row.area not in seen:
                seen.append(row.area)
        return tuple(seen)

    def rows_by_verdict(self) -> dict[str, tuple[Row, ...]]:
        """Rows grouped by verdict, in :data:`VERDICTS` order, empties dropped."""
        grouped = {v: tuple(r for r in self.rows if r.verdict == v) for v in VERDICTS}
        return {verdict: rows for verdict, rows in grouped.items() if rows}

    def rows_in(self, area: str) -> tuple[Row, ...]:
        return tuple(r for r in self.rows if r.area == area)

# --------------------------------------------------------------------------- #
# Reading a declaration
# --------------------------------------------------------------------------- #


def _root(repo_root: Path | None) -> Path:
    if repo_root is not None:
        return repo_root
    return find_repo_root(Path(__file__).resolve().parent)


def _parse(path: Path, source: str) -> Any:
    """*path* as JSON, or a refusal naming the file.

    A malformed declaration is refused here rather than raised as a decoder
    error from inside a loader, so every caller meets one exception type.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        raise AuthorityMatrixError(f"{source}: not readable JSON ({exc})") from exc


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _required(raw: Mapping[str, Any], key: str, source: str) -> Any:
    if key not in raw:
        raise AuthorityMatrixError(f"{source}: the declaration has no {key!r}")
    return raw[key]


def _one_of(value: Any, allowed: Sequence[str], field: str, source: str) -> str:
    if value not in allowed:
        raise AuthorityMatrixError(
            f"{source}: {field} is {value!r}; expected one of {', '.join(allowed)}"
        )
    return str(value)


def _source(raw: Mapping[str, Any], source: str) -> Source:
    path = _required(raw, "path", source)
    where = f"{source}: source {path}"
    authentication = _one_of(
        _required(raw, "authentication", source), AUTHENTICATIONS, "authentication", where
    )
    sha = str(raw.get("sha256", ""))
    # The two ways an entry can lie about being obtained. Both are refused at
    # load, because either one makes every later check read the wrong document.
    if authentication == "not_obtained" and sha:
        raise AuthorityMatrixError(f"{where}: not obtained, yet a sha256 is declared")
    if authentication != "not_obtained" and not sha:
        raise AuthorityMatrixError(f"{where}: obtained, yet no sha256 is declared")
    pages = raw.get("pages")
    return Source(
        path=path,
        cls=_one_of(_required(raw, "class", source), SOURCE_CLASSES, "class", where),
        era=_one_of(_required(raw, "era", source), ERAS, "era", where),
        authentication=authentication,
        states=_required(raw, "states", source),
        role=_one_of(_required(raw, "role", source), SOURCE_ROLES, "role", where),
        authentication_basis=str(raw.get("authentication_basis", "")),
        sha256=sha,
        pages=int(pages) if pages is not None else None,
        version=str(raw.get("version", "")),
        required=bool(raw.get("required", True)),
        would_settle=tuple(raw.get("would_settle", ()) or ()),
        scope_restrictions=tuple(
            ScopeRestriction(
                field_prefix=_required(r, "field_prefix", where),
                settles_areas=tuple(_required(r, "settles_areas", where)),
                measured=_required(r, "measured", where),
            )
            for r in raw.get("scope_restrictions", ()) or ()
        ),
    )


def load_source_index(path: Path, repo_root: Path | None = None) -> SourceIndex:
    """Read a source-index declaration.

    Fails closed on a missing field, an unknown class, era, authentication or
    role, and on the two ways an entry can lie about being obtained: a hash on
    an absent document, and an obtained document with no hash.
    """
    root = _root(repo_root)
    source = _rel(path, root)
    raw = _parse(path, source)
    schema = raw.get("schema")
    if schema != SCHEMA_INDEX:
        raise AuthorityMatrixError(f"{source}: schema is {schema!r}, expected {SCHEMA_INDEX!r}")
    return SourceIndex(
        name=_required(raw, "index_name", source),
        subject=_required(raw, "subject", source),
        authored_on=_required(raw, "authored_on", source),
        purpose=_required(raw, "purpose", source),
        historical_label=_required(raw, "historical_label", source),
        current_label=_required(raw, "current_label", source),
        review_state=_one_of(
            _required(raw, "review_state", source), REVIEW_STATES, "review_state", source
        ),
        declared_status=_one_of(
            _required(raw, "declared_status", source), STATUSES, "declared_status", source
        ),
        supersedes=_required(raw, "supersedes", source),
        uncertainties=tuple(_required(raw, "uncertainties", source)),
        sources=tuple(_source(s, source) for s in _required(raw, "sources", source)),
        source=source,
        written_by=str(raw.get("written_by", "")),
    )


def _citation(raw: Mapping[str, Any], where: str) -> Citation:
    page = raw.get("page")
    field = str(raw.get("field", ""))
    # Exactly one locator. A citation with both is ambiguous about what was
    # read; a citation with neither locates nothing.
    if (page is None) == (not field):
        raise AuthorityMatrixError(
            f"{where}: a citation declares "
            + ("both a page and a field" if page is not None else "neither a page nor a field")
        )
    return Citation(
        source=_required(raw, "source", where),
        states=_required(raw, "states", where),
        field=field,
        page=int(page) if page is not None else None,
        quote=str(raw.get("quote", "")),
    )


def _measurement(raw: Mapping[str, Any], where: str) -> Measurement:
    ident = _required(raw, "id", where)
    has_value = "expected" in raw
    has_length = "expected_length" in raw
    if has_value == has_length:
        raise AuthorityMatrixError(
            f"{where}: measurement {ident} declares "
            + ("both expected and expected_length" if has_value else "no expected value")
        )
    return Measurement(
        id=ident,
        claim=_required(raw, "claim", where),
        record=_required(raw, "record", where),
        field=_required(raw, "field", where),
        expected=raw.get("expected"),
        expected_length=int(raw["expected_length"]) if has_length else None,
    )


def _row(raw: Mapping[str, Any], source: str) -> Row:
    ident = _required(raw, "id", source)
    where = f"{source}: row {ident}"
    defaulting_raw = raw.get("defaulting")
    defaulting = (
        Defaulting(
            carried_from=_required(defaulting_raw, "carried_from", where),
            # Not required at load: an unnamed affected rule is a finding, so
            # that a check over a committed matrix reports it rather than
            # refusing to read the matrix at all.
            affected_rule=str(defaulting_raw.get("affected_rule", "")),
            risk=_required(defaulting_raw, "risk", where),
        )
        if defaulting_raw
        else None
    )
    return Row(
        id=ident,
        area=_required(raw, "area", source),
        rule=_required(raw, "rule", source),
        affects=_one_of(_required(raw, "affects", source), AFFECTS, "affects", where),
        verdict=_one_of(_required(raw, "verdict", source), VERDICTS, "verdict", where),
        settles=_one_of(_required(raw, "settles", source), SETTLEMENTS, "settles", where),
        declared_status=_one_of(
            _required(raw, "declared_status", source), STATUSES, "declared_status", where
        ),
        status_basis=_required(raw, "status_basis", source),
        citations=tuple(_citation(c, where) for c in raw.get("citations", ()) or ()),
        historical_value=str(raw.get("historical_value", "")),
        current_value=str(raw.get("current_value", "")),
        difference=str(raw.get("difference", "")),
        defaulting=defaulting,
        limitation=str(raw.get("limitation", "")),
        why_era_neutral=str(raw.get("why_era_neutral", "")),
        consequence=str(raw.get("consequence", "")),
        would_be_settled_by=tuple(raw.get("would_be_settled_by", ()) or ()),
        measurements=tuple(_measurement(m, where) for m in raw.get("measurements", ()) or ()),
    )


def load_matrix(path: Path, repo_root: Path | None = None) -> Matrix:
    """Read a matrix declaration. Fails closed, for the reasons the index does."""
    root = _root(repo_root)
    source = _rel(path, root)
    raw = _parse(path, source)
    schema = raw.get("schema")
    if schema != SCHEMA_MATRIX:
        raise AuthorityMatrixError(f"{source}: schema is {schema!r}, expected {SCHEMA_MATRIX!r}")
    index = _required(raw, "source_index", source)
    return Matrix(
        name=_required(raw, "matrix_name", source),
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
        required_areas=tuple(_required(raw, "required_areas", source)),
        index_path=_required(index, "path", source),
        index_sha256=_required(index, "sha256", source),
        rows=tuple(_row(r, source) for r in _required(raw, "rows", source)),
        source=source,
        written_by=str(raw.get("written_by", "")),
    )


# --------------------------------------------------------------------------- #
# Checking
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MatrixCheck:
    """A matrix read against its index and the records both bind."""

    # -- the rule that matters ---------------------------------------------- #
    equivalence_without_historical_evidence: tuple[str, ...] = ()
    defaulting_without_an_affected_rule: tuple[str, ...] = ()
    # -- a row that does not say what it must ------------------------------- #
    rows_missing_field: tuple[str, ...] = ()
    duplicate_row_ids: tuple[str, ...] = ()
    areas_required_but_not_covered: tuple[str, ...] = ()
    differences_not_described: tuple[str, ...] = ()
    unresolved_without_a_limitation: tuple[str, ...] = ()
    era_neutral_without_a_justification: tuple[str, ...] = ()
    # -- a citation that does not hold -------------------------------------- #
    rows_without_a_citation: tuple[str, ...] = ()
    citations_of_undeclared_sources: tuple[str, ...] = ()
    citations_of_unobtained_sources: tuple[str, ...] = ()
    citations_that_do_not_resolve: tuple[str, ...] = ()
    document_citations_without_a_quote: tuple[str, ...] = ()
    citations_outside_their_declared_scope: tuple[str, ...] = ()
    rows_naming_an_undeclared_future_source: tuple[str, ...] = ()
    # -- a conclusion that reaches further than its evidence ---------------- #
    call_wide_claims_on_submission_evidence: tuple[str, ...] = ()
    confirmed_without_an_authenticated_source: tuple[str, ...] = ()
    # -- the records themselves --------------------------------------------- #
    missing_sources: tuple[str, ...] = ()
    edited_immutable_sources: tuple[str, ...] = ()
    stale_tracked_inputs: tuple[str, ...] = ()
    stale_source_index: tuple[str, ...] = ()
    unobtained_sources_declared_with_pages: tuple[str, ...] = ()
    authentications_claimed_without_a_basis: tuple[str, ...] = ()
    # -- a measurement that fails ------------------------------------------- #
    measurements_of_undeclared_sources: tuple[str, ...] = ()
    failed_measurements: tuple[str, ...] = ()

    @property
    def green(self) -> bool:
        """Every finding empty."""
        return not any(getattr(self, f) for f in self.__dataclass_fields__)

    @property
    def findings_total(self) -> int:
        return sum(len(getattr(self, f)) for f in self.__dataclass_fields__)

    def lines(self) -> tuple[str, ...]:
        """The check for a human, one finding per line."""
        out: list[str] = []
        for attr in self.__dataclass_fields__:
            label = attr.replace("_", " ").upper()
            for item in getattr(self, attr):
                out.append(f"{label}: {item}")
        return tuple(out)


def _check_sources(index: SourceIndex, repo_root: Path) -> dict[str, tuple[str, ...]]:
    pages_on_absent: list[str] = []
    unevidenced: list[str] = []
    for source in index.sources:
        if not source.obtained and source.pages is not None:
            # A page count over a document nobody has is a measurement of
            # nothing, and a citation would resolve against it.
            pages_on_absent.append(f"{source.path}: pages {source.pages}")
        if (
            source.authentication in AUTHENTICATIONS_NEEDING_A_BASIS
            and not source.authentication_basis.strip()
        ):
            # A rank above computed_only says somebody vouched for the bytes.
            # Without a record saying who and where, it is the index author's
            # own word, which is the thing the rank is supposed to improve on.
            unevidenced.append(f"{source.path}: {source.authentication}")
    bindings = check_bindings(index.obtained(), repo_root)
    return {
        "missing_sources": bindings.missing,
        "edited_immutable_sources": bindings.edited_immutable,
        "stale_tracked_inputs": bindings.stale_tracked,
        "unobtained_sources_declared_with_pages": tuple(pages_on_absent),
        "authentications_claimed_without_a_basis": tuple(unevidenced),
    }


def _read_json(repo_root: Path, rel: str, cache: dict[str, Any]) -> Any:
    if rel not in cache:
        try:
            cache[rel] = json.loads((repo_root / rel).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            cache[rel] = _Unreadable(type(exc).__name__)
    return cache[rel]


def _read_text(repo_root: Path, rel: str, cache: dict[str, Any]) -> Any:
    key = f"text:{rel}"
    if key not in cache:
        try:
            cache[key] = (repo_root / rel).read_text(encoding="utf-8-sig")
        except OSError as exc:
            cache[key] = _Unreadable(type(exc).__name__)
    return cache[key]


def _check_row_fields(matrix: Matrix, index: SourceIndex) -> dict[str, tuple[str, ...]]:
    missing: list[str] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    differences: list[str] = []
    unresolved: list[str] = []
    era_neutral: list[str] = []
    defaulting: list[str] = []
    dangling: list[str] = []
    declared = index.by_path()

    for row in matrix.rows:
        if row.id in seen and row.id not in duplicates:
            duplicates.append(row.id)
        seen.add(row.id)
        for name in ("area", "rule", "status_basis", "consequence"):
            if not str(getattr(row, name)).strip():
                missing.append(f"{row.id}: {name}")
        if row.verdict == "differs" and not row.difference.strip():
            differences.append(row.id)
        if row.verdict == "unresolved" and not row.limitation.strip():
            unresolved.append(row.id)
        if row.verdict == "era_neutral" and not row.why_era_neutral.strip():
            era_neutral.append(row.id)
        if row.verdict == "defaulted":
            if row.defaulting is None:
                defaulting.append(f"{row.id}: no defaulting block")
            elif not row.defaulting.affected_rule.strip():
                defaulting.append(f"{row.id}: no affected rule named")
        # A row that says which document would settle it has to name one the
        # index declares. Otherwise the promise points nowhere, and the index's
        # own derivation of what each absent document would settle omits it in
        # silence.
        for path in row.would_be_settled_by:
            if path not in declared:
                dangling.append(f"{row.id}: {path}")

    covered = set(matrix.areas())
    uncovered = tuple(a for a in matrix.required_areas if a not in covered)
    return {
        "rows_missing_field": tuple(missing),
        "duplicate_row_ids": tuple(duplicates),
        "areas_required_but_not_covered": uncovered,
        "differences_not_described": tuple(differences),
        "unresolved_without_a_limitation": tuple(unresolved),
        "era_neutral_without_a_justification": tuple(era_neutral),
        "defaulting_without_an_affected_rule": tuple(defaulting),
        "rows_naming_an_undeclared_future_source": tuple(dangling),
    }


def _check_citations(
    matrix: Matrix, index: SourceIndex, repo_root: Path, unreadable: frozenset[str]
) -> dict[str, tuple[str, ...]]:
    declared = index.by_path()
    no_citation: list[str] = []
    undeclared: list[str] = []
    unobtained: list[str] = []
    unresolved: list[str] = []
    no_quote: list[str] = []
    out_of_scope: list[str] = []
    no_historical: list[str] = []
    submission_only: list[str] = []
    unvouched_confirmed: list[str] = []
    cache: dict[str, Any] = {}

    for row in matrix.rows:
        if not row.citations:
            # era_neutral is the one verdict that can rest on nothing external:
            # its justification is that no call document states the rule.
            if row.verdict != "era_neutral":
                no_citation.append(row.id)
            continue

        historical = False
        non_submission_historical = False
        vouched = False
        for position, citation in enumerate(row.citations, 1):
            label = f"{row.id} citation {position}"
            source = declared.get(citation.source)
            if source is None:
                undeclared.append(f"{label}: {citation.source}")
                continue
            if not source.obtained:
                unobtained.append(f"{label}: {citation.source}")
                continue
            if source.era == "historical":
                historical = True
                if not source.submission_scoped:
                    non_submission_historical = True
            if source.vouched:
                vouched = True

            restriction = source.restriction_for(citation.field)
            if restriction is not None and row.area not in restriction.settles_areas:
                out_of_scope.append(
                    f"{label}: {citation.source}#{citation.field} measured "
                    f"{', '.join(restriction.settles_areas)}, cited from area {row.area}"
                )

            if citation.page is not None:
                if not citation.quote.strip():
                    no_quote.append(label)
                if source.pages is None or not 1 <= citation.page <= source.pages:
                    extent = (
                        "no page count declared"
                        if source.pages is None
                        else f"{source.pages} pages"
                    )
                    unresolved.append(
                        f"{label}: page {citation.page} of {citation.source} ({extent})"
                    )
            elif citation.source not in unreadable:
                # A JSON source resolves a field by pointer. Any other record —
                # a specification written in Markdown, say — must carry the
                # field as text, so a reworded decision is caught rather than
                # silently pointing nowhere.
                if citation.source.endswith(".json"):
                    data = _read_json(repo_root, citation.source, cache)
                    if isinstance(data, _Unreadable):
                        unresolved.append(f"{label}: {citation.source} is not readable JSON")
                    elif resolve_field(data, citation.field) is UNRESOLVED:
                        unresolved.append(f"{label}: {citation.field} does not resolve")
                else:
                    text = _read_text(repo_root, citation.source, cache)
                    if isinstance(text, _Unreadable):
                        unresolved.append(f"{label}: {citation.source} is not readable text")
                    elif citation.field not in text:
                        unresolved.append(f"{label}: {citation.field} is not in the record")

        if row.asserts_a_relation and not historical:
            no_historical.append(row.id)
        if row.asserts_a_relation and row.settles == "call_wide" and not non_submission_historical:
            submission_only.append(row.id)
        if row.declared_status == "Confirmed" and not vouched:
            unvouched_confirmed.append(row.id)

    return {
        "rows_without_a_citation": tuple(no_citation),
        "citations_of_undeclared_sources": tuple(undeclared),
        "citations_of_unobtained_sources": tuple(unobtained),
        "citations_that_do_not_resolve": tuple(unresolved),
        "document_citations_without_a_quote": tuple(no_quote),
        "citations_outside_their_declared_scope": tuple(out_of_scope),
        "equivalence_without_historical_evidence": tuple(no_historical),
        "call_wide_claims_on_submission_evidence": tuple(submission_only),
        "confirmed_without_an_authenticated_source": tuple(unvouched_confirmed),
    }


def _check_measurements(
    matrix: Matrix, index: SourceIndex, repo_root: Path
) -> dict[str, tuple[str, ...]]:
    declared = index.by_path()
    undeclared: list[str] = []
    failed: list[str] = []
    cache: dict[str, Any] = {}
    for row in matrix.rows:
        for m in row.measurements:
            if m.record not in declared:
                undeclared.append(f"{row.id}/{m.id}: {m.record}")
                continue
            data = _read_json(repo_root, m.record, cache)
            if isinstance(data, _Unreadable):
                failed.append(f"{row.id}/{m.id}: {m.record} is not readable JSON ({data.why})")
                continue
            value = resolve_field(data, m.field)
            if value is UNRESOLVED:
                failed.append(f"{row.id}/{m.id}: {m.field} does not resolve")
            elif m.expected_length is not None:
                if not isinstance(value, (list, tuple, str, dict)):
                    failed.append(f"{row.id}/{m.id}: {m.field} has no length")
                elif len(value) != m.expected_length:
                    failed.append(
                        f"{row.id}/{m.id}: {m.field} has length {len(value)}, "
                        f"expected {m.expected_length}"
                    )
            elif value != m.expected:
                failed.append(
                    f"{row.id}/{m.id}: {m.field} is {value!r}, expected {m.expected!r}"
                )
    return {
        "measurements_of_undeclared_sources": tuple(undeclared),
        "failed_measurements": tuple(failed),
    }


def check(matrix: Matrix, index: SourceIndex, repo_root: Path | None = None) -> MatrixCheck:
    """Read *matrix* against *index* and the records both bind.

    The finding that matters is the first: a row marked ``equivalent`` or
    ``differs`` with no citation into an obtained historical source. That is
    defaulting wearing the word equivalent, and it is the defect the whole
    artifact exists to prevent.
    """
    root = _root(repo_root)
    findings: dict[str, tuple[str, ...]] = {}
    sources = _check_sources(index, root)
    # A citation into a record that is not on disk is one defect, not two.
    unreadable = frozenset(sources["missing_sources"])
    findings.update(_check_row_fields(matrix, index))
    findings.update(_check_citations(matrix, index, root, unreadable))
    findings.update(sources)
    findings.update(_check_measurements(matrix, index, root))

    index_file = root / matrix.index_path
    if not index_file.is_file():
        findings["stale_source_index"] = (f"{matrix.index_path}: absent",)
    elif file_sha256(index_file) != matrix.index_sha256:
        findings["stale_source_index"] = (
            f"{matrix.index_path}: bytes differ from the hash the matrix binds",
        )
    return MatrixCheck(**findings)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _as_words(token: str) -> str:
    return token.replace("_", " ")


def render_index(index: SourceIndex) -> str:
    """The source index for a human reader."""
    out: list[str] = []
    add = out.append
    obtained = index.obtained()
    absent = index.missing_required()

    add(f"# Authority source index — {index.subject}")
    add("")
    add(f"Authored {index.authored_on}. Index `{index.name}`, schema `{SCHEMA_INDEX}`,")
    add(f"written by `{index.written_by}`.")
    add("")
    add(f"Review state: **{_as_words(index.review_state)}**.")
    add(f"The index's own reading of its documents is declared **{index.declared_status}**.")
    add(f"Relationship to earlier versions: {index.supersedes}")
    add("")
    add(
        _wrap(
            f"{len(index.sources)} documents are indexed. {len(obtained)} are obtained and pinned "
            f"by sha256, and {len(absent)} required ones are not obtained. "
            f"The {index.historical_label} era is the submission's; the {index.current_label} era "
            "is the one the current profile was written for. A citation of an unobtained document "
            "fails `harness.authority_matrix.check`."
        )
    )
    add("")

    add("## What is obtained")
    add("")
    add("| Document | Era | Class | Bytes vouched for | How | States |")
    add("|---|---|---|---|---|---|")
    for source in obtained:
        version = f" (v{source.version})" if source.version else ""
        add(
            f"| `{source.path}`{version} | {source.era} | {_as_words(source.cls)} | "
            f"{_as_words(source.authentication)} | "
            f"{_one_line(source.authentication_basis) or '—'} | "
            f"{_one_line(source.states)} |"
        )
    add("")
    add(
        _wrap(
            "No document here is authenticated by a hash from its issuing body. A document pinned "
            "in this tree with no recorded download provenance is `computed_only`: its bytes are "
            "fixed, and nothing says they are the official ones. A row resting only on such a "
            "document may not declare Confirmed, and the check reports it if it does."
        )
    )
    add("")

    if absent:
        add("## What is not obtained")
        add("")
        add("| Document | Era | Class | Rows it would settle |")
        add("|---|---|---|---|")
        for source in absent:
            rows = ", ".join(source.would_settle) if source.would_settle else "none recorded"
            add(f"| {_one_line(source.states)} | {source.era} | {_as_words(source.cls)} | {rows} |")
        add("")
        add(
            _wrap(
                "Each row is open because of a document in this table. The operator supplies "
                "them; nothing in this repository fetches one, and no row closes by assuming "
                "what one would say."
            )
        )
        add("")

    restricted = [s for s in index.sources if s.scope_restrictions]
    if restricted:
        add("## What a record settles, and no more")
        add("")
        add("| Record | Passage | Settles | Measured |")
        add("|---|---|---|---|")
        for source in restricted:
            for restriction in source.scope_restrictions:
                add(
                    f"| `{source.path.rsplit('/', 1)[-1]}` | `{restriction.field_prefix}` | "
                    f"{', '.join(_as_words(a) for a in restriction.settles_areas)} | "
                    f"{_one_line(restriction.measured)} |"
                )
        add("")
        add(
            _wrap(
                "A record that measured one thing can be read as settling another. A citation of "
                "a restricted passage from a row outside its areas is a finding, not an accepted "
                "source."
            )
        )
        add("")

    if index.uncertainties:
        add("## What the author of this index is unsure of")
        add("")
        for item in index.uncertainties:
            add(f"- {item}")
        add("")
    return "\n".join(out)


def render_matrix(matrix: Matrix, index: SourceIndex) -> str:
    """The matrix for a human reader."""
    out: list[str] = []
    add = out.append
    declared = index.by_path()
    by_verdict = matrix.rows_by_verdict()

    add(f"# Rule-equivalence matrix — {matrix.subject}")
    add("")
    add(f"Authored {matrix.authored_on}. Matrix `{matrix.name}`, schema `{SCHEMA_MATRIX}`,")
    add(f"written by `{matrix.written_by}`.")
    add("")
    add(f"Review state: **{_as_words(matrix.review_state)}**.")
    add(f"The matrix's own reading of its sources is declared **{matrix.declared_status}**.")
    add(f"Relationship to earlier versions: {matrix.supersedes}")
    add(f"Source index: `{matrix.index_path}`, bound at `sha256:{matrix.index_sha256[:12]}`.")
    add("")
    add(_wrap(matrix.purpose))
    add("")

    add("## What the rows conclude")
    add("")
    add("| Verdict | Rows | What it means |")
    add("|---|---|---|")
    meanings = {
        "equivalent": (
            "a historical source states the rule, and it is the rule the current profile holds"
        ),
        "differs": "a historical source states a different rule",
        "defaulted": (
            "the current rule is carried forward because no historical source states it — "
            "**not** equivalence"
        ),
        "unresolved": "no source states the rule, and the limitation is recorded",
        "era_neutral": "the rule is the assessing harness's own and no call document states it",
    }
    # Every verdict, including the ones no row carries. A reader has to see that
    # `defaulted` exists and is not equivalence even in a matrix with no
    # defaulted row, because that is the distinction the artifact is for.
    for verdict in VERDICTS:
        add(f"| {verdict} | {len(by_verdict.get(verdict, ()))} | {meanings[verdict]} |")
    add(f"| **total** | **{len(matrix.rows)}** | |")
    add("")
    add(
        _wrap(
            "No verdict means *no difference was found*. A row with no historical citation is "
            "`defaulted` and names the rule its defaulting affects. "
            "`harness.authority_matrix.check` reports a row marked equivalent or differs with no "
            "citation into an obtained historical source."
        )
    )
    add("")

    add("## Coverage")
    add("")
    add("| Area | Rows | Verdicts |")
    add("|---|---|---|")
    for area in matrix.required_areas:
        rows = matrix.rows_in(area)
        verdicts = ", ".join(sorted({r.verdict for r in rows})) or "none"
        add(f"| {_as_words(area)} | {len(rows)} | {verdicts} |")
    extra = [a for a in matrix.areas() if a not in matrix.required_areas]
    for area in extra:
        rows = matrix.rows_in(area)
        verdicts = ", ".join(sorted({r.verdict for r in rows}))
        add(f"| {_as_words(area)} (beyond the required set) | {len(rows)} | {verdicts} |")
    add("")

    add("## The rows")
    add("")
    for area in list(matrix.required_areas) + extra:
        rows = matrix.rows_in(area)
        if not rows:
            continue
        add(f"### {_as_words(area).capitalize()}")
        add("")
        for row in rows:
            add(f"#### {row.id} — {row.verdict}")
            add("")
            add(_wrap(row.rule))
            add("")
            add(f"- Affects: {row.affects}")
            add(f"- Settles: {_as_words(row.settles)}")
            if row.historical_value:
                add(f"- {index.historical_label}: {_one_line(row.historical_value)}")
            if row.current_value:
                add(f"- {index.current_label}: {_one_line(row.current_value)}")
            if row.difference:
                add(f"- Difference: {_one_line(row.difference)}")
            if row.defaulting is not None:
                add(f"- Carried from: {_one_line(row.defaulting.carried_from)}")
                add(f"- Rule the defaulting affects: {_one_line(row.defaulting.affected_rule)}")
                add(f"- Risk: {_one_line(row.defaulting.risk)}")
            if row.limitation:
                add(f"- Limitation: {_one_line(row.limitation)}")
            if row.why_era_neutral:
                add(f"- Why no era states it: {_one_line(row.why_era_neutral)}")
            add(f"- Status: **{row.declared_status}** — {_one_line(row.status_basis)}")
            add(f"- For the historical profile: {_one_line(row.consequence)}")
            if row.would_be_settled_by:
                add(
                    "- Would be settled by: "
                    + ", ".join(f"`{p}`" for p in row.would_be_settled_by)
                )
            add("")
            if row.citations:
                add("| Source | Era | Locator | States |")
                add("|---|---|---|---|")
                for citation in row.citations:
                    source = declared.get(citation.source)
                    era = source.era if source is not None else "UNDECLARED"
                    add(
                        f"| `{citation.source.rsplit('/', 1)[-1]}` | {era} | "
                        f"`{citation.locator}` | {_one_line(citation.states)} |"
                    )
                add("")
            for citation in row.citations:
                if citation.quote:
                    add(f"> {_one_line(citation.quote)}")
                    add("")
            for m in row.measurements:
                expected = (
                    f"length {m.expected_length}"
                    if m.expected_length is not None
                    else repr(m.expected)
                )
                add(f"- Measured: {_one_line(m.claim)} — `{m.field}` is {expected}")
            if row.measurements:
                add("")

    if matrix.uncertainties:
        add("## What the author of this matrix is unsure of")
        add("")
        for item in matrix.uncertainties:
            add(f"- {item}")
        add("")
    return "\n".join(out)
