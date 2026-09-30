"""The Tier 3 source index — what instance two's concept rests on, and how much
of that rests on something a reader can check.

The dev-graph snapshot builder turns ``source_materials/sources.json`` into
``source`` nodes, and a claim's ``verified_span`` resolves byte offsets against a
source's ``text`` (:mod:`runner.dev_graph.builder`). The builder asks for very
little: a non-empty ``source_id`` and, if present, a string ``text``. That is
deliberate — the builder indexes records, it does not judge them. Judging them is
this module's job.

Why a source index needs its own verifier
-----------------------------------------
A source record is the one place in Tier 3 where a claim can be laundered. Write
a plausible citation, add a quotation nobody stored, point a span at it, and the
graph reports a ``source_grounded`` claim that no document supports. Nothing in
the builder catches that, because the builder has no way to know whether the text
is real. So the rule this module enforces is narrow and mechanical:

    **A source carries verbatim text only when that text can be re-derived from
    a file stored in this repository, byte for byte.**

Everything else is a *reference*: a citation, an anchor showing where the project
names it, and an identifier that is recorded rather than resolved. A reference
carries no text and therefore no span, so no claim can ever be verified against
it. That is the honest shape, and it is why :data:`TRANSCRIPTION_STATES` has
exactly two members with no third "paraphrased" option.

The two source kinds
--------------------
``call_document_page``
    One page of a stored document, transcribed by :func:`read_page_text` and
    checked byte-equal on every run. ``text`` is present, spans resolve into it,
    and the status is Confirmed because the check is mechanical.

``external_reference``
    A public framework, dataset, policy instrument or paper. No copy is stored
    and this workspace has no verified network egress, so nothing is
    transcribed. Each one carries an *anchor*: a verbatim string in a stored
    artifact that names it, checked to occur there. The anchor is what makes the
    reference resolvable; the external identifier beside it is recorded from
    prior knowledge, flagged Assumed under CLAUDE.md §10.6, and never treated as
    verified.

The name partition
------------------
"Each source cited in the concept has an entry" is only checkable if the set of
cited sources is *derived* rather than hand-listed. :func:`candidate_names`
derives it: every acronym and every multi-word capitalised name in the concept
brief and the consortium registry. Each candidate must then be either claimed by
a source's ``names`` or declared in ``names_that_are_not_sources`` with a reason.
An unclassified candidate fails the check, so a framework added to the concept
later cannot slip through silently.

The derivation has one known limit, recorded rather than hidden: a *single*
capitalised word cannot be told from a sentence opener mechanically, so
single-word names (Copernicus, FuturEO) are listed in
:data:`SINGLE_WORD_EXTERNALS` and are a hand list. Naming the limit is the point;
see the ticket's findings.

Constitutional standing
-----------------------
Subordinate to CLAUDE.md. Pure, deterministic and Claude-free: it reads files and
reports. It writes nothing, evaluates no gate (§17.6.2) and invents no fact
(§13.3). It is not a deterministic component under §17.5.3 — no node body binds
it, and it writes no canonical artifact.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from runner.dev_graph.builder import SOURCES_REL as _SOURCES_REL

# ---------------------------------------------------------------------------
# Locations and vocabularies
# ---------------------------------------------------------------------------

#: The index the dev-graph builder reads. Taken from the builder rather than
#: re-typed, so the writer, the reader and the verifier can never disagree about
#: where it lives.
SOURCES_REL: str = _SOURCES_REL.as_posix()

#: The index declares what it is through ``record_type``, not through a coined
#: ``schema_id``. ``artifact_schema_specification.yaml`` declares no shape for
#: ``sources.json`` — the builder asks only for ``source_id`` and an optional
#: string ``text`` — and ``docs/index/schema_registry.json`` registers
#: ``orch.*`` ids for run-produced artifacts. No Tier 3 source artifact carries
#: one, as ``partners.json`` and ``roles.json`` both say of themselves, and
#: §16.3 forbids introducing a schema the specifications do not define. The
#: discriminator is still needed, so it is this: a file that does not declare
#: itself a source index is refused rather than read.
SOURCE_INDEX_RECORD_TYPE = "source_index"

#: The four status categories of CLAUDE.md §12.2.
STATUSES: frozenset[str] = frozenset({"Confirmed", "Inferred", "Assumed", "Unresolved"})

#: Exactly two transcription states, and no third. ``transcribed`` means the text
#: is re-derivable from a stored file; ``cited_only`` means there is no text at
#: all. A "paraphrased" or "summarised" state would be a claim about a document
#: nobody can check, which is the failure this module exists to prevent.
TRANSCRIPTION_STATES: frozenset[str] = frozenset({"transcribed", "cited_only"})

#: The closed source-kind set, one per transcription state.
SOURCE_KINDS: dict[str, str] = {
    "call_document_page": "transcribed",
    "external_reference": "cited_only",
}

#: How a source is reached. A stored document resolves inside this repository; an
#: external identifier does not, and is recorded rather than resolved.
RESOLUTION_CLASSES: frozenset[str] = frozenset({"stored_document", "external_identifier"})

#: The transcription method the page sources declare. The name is the replay
#: contract: :func:`read_page_text` is the only implementation, and the byte-equal
#: check in :func:`verify` re-runs it.
PAGE_TEXT_METHOD = "pymupdf_page_text_whitespace_normalised"

#: The Tier 3 artifacts swept for external names, as repo-relative paths. The
#: brief is the concept in prose and in claims; the consortium registry carries
#: the capabilities the concept's claims cite, so a framework a partner capability
#: names is cited by the concept just as surely as one the prose names.
NAMED_IN_PATHS: tuple[str, ...] = (
    "docs/tier3_project_instantiation/project_brief/concept_note.md",
    "docs/tier3_project_instantiation/project_brief/strategic_positioning.md",
    "docs/tier3_project_instantiation/project_brief/project_summary.json",
    "docs/tier3_project_instantiation/consortium/partners.json",
    "docs/tier3_project_instantiation/consortium/roles.json",
)

#: The concept's structured claims, which a source's ``claim_refs`` point into.
PROJECT_SUMMARY_REL = "docs/tier3_project_instantiation/project_brief/project_summary.json"

#: The stored-document registry, which a page source's ``document_id`` must name.
DOCUMENT_REGISTRY_REL = "docs/index/document_registry.json"

#: A multi-word capitalised name: two or more capitalised words, optionally joined
#: by a lower-case function word ("Global Ecosystem Typology", "Birds Directive").
_PHRASE_RE = re.compile(r"\b[A-Z][A-Za-z]+(?:[ -](?:of|the|and|for)? ?[A-Z][A-Za-z]+)+\b")

#: An acronym of three letters or more, with an optional mission number
#: ("GBIF", "EUNIS", "SAGE").
_ACRONYM_RE = re.compile(r"\b[A-Z]{3,}(?:-[0-9]+)?\b")

#: A mission or product designation ("Sentinel-2").
_MISSION_RE = re.compile(r"\b[A-Z][A-Za-z]+-[0-9]\b")

#: Single capitalised words that name an external and cannot be derived.
#:
#: The derivation in :func:`candidate_names` takes acronyms and multi-word names
#: because both are unambiguous. A single capitalised word is not: in English
#: prose most are sentence openers, and no mechanical rule separates "Copernicus"
#: from "Proposals" without reading the sentence. Listing them by hand is the
#: honest option, and it means the completeness guarantee covers the derived
#: candidates only. The ticket records that as a finding rather than claiming the
#: sweep is exhaustive.
SINGLE_WORD_EXTERNALS: frozenset[str] = frozenset(
    {
        "Copernicus",
        "FuturEO",
        "Galileo",
        "Sentinel",
    }
)


class SourceIndexError(Exception):
    """Raised when the index cannot be read at all.

    Fail-closed: a missing or unparseable index means no check ran, and a check
    that did not run must not report clean (CLAUDE.md §15).
    """


# ---------------------------------------------------------------------------
# Text normalisation and page transcription
# ---------------------------------------------------------------------------


def normalise_whitespace(text: str) -> str:
    """Collapse a PDF's line breaks and runs of spaces to one space each.

    Transcription normalises whitespace and nothing else. Line breaks in a PDF
    are a layout artifact, so keeping them would make an offset depend on the
    column width of the page rather than on the words. Every other character —
    curly quotes, en dashes, bullets — is carried through unchanged, because a
    span that silently rewrote its source would defeat the check.
    """
    return re.sub(r"\s+", " ", text).strip()


def read_page_text(pdf: Path, page: int) -> str:
    """The normalised text of one 1-based printed page of *pdf*.

    The single implementation of :data:`PAGE_TEXT_METHOD`. Both the generator
    that writes a page source and the verifier that checks it call this, so the
    byte-equal check compares a record against the same function that produced
    it — which is what makes the transcription replayable rather than trusted.

    Does not skip when pymupdf is absent: reading the document is the whole
    verification, so an absent reader must fail loudly rather than let a check
    that never ran report green. pymupdf is declared in ``requirements.txt``.
    """
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        if not 1 <= page <= doc.page_count:
            raise SourceIndexError(
                f"{pdf.name}: page {page} is outside the document (1-{doc.page_count})"
            )
        return normalise_whitespace(doc[page - 1].get_text())
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceProblem:
    """One thing wrong with the index, located precisely enough to fix."""

    where: str
    """``sources[3]``, ``SRC-GBIF``, or a candidate name."""
    kind: str
    """``shape``, ``resolution``, ``transcription``, ``span``, ``anchor``,
    ``overclaim`` or ``coverage``."""
    message: str


@dataclass(frozen=True)
class SourceIndexReport:
    """The outcome of a verification pass."""

    sources_checked: tuple[str, ...]
    transcribed: tuple[str, ...]
    spans_resolved: int
    candidates: tuple[str, ...]
    problems: tuple[SourceProblem, ...]

    @property
    def ok(self) -> bool:
        return not self.problems

    def format(self) -> str:
        head = (
            f"{len(self.sources_checked)} source(s), "
            f"{len(self.transcribed)} transcribed, "
            f"{self.spans_resolved} span(s) resolved, "
            f"{len(self.candidates)} external name(s) classified"
        )
        if self.ok:
            return f"[source-index] OK — {head}."
        lines = [f"[source-index] FAIL — {len(self.problems)} problem(s) ({head}):"]
        for problem in self.problems:
            lines.append(f"  {problem.where}: [{problem.kind}] {problem.message}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _read_json(path: Path, what: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise SourceIndexError(f"{what} is unreadable: {exc}") from exc
    except ValueError as exc:
        raise SourceIndexError(f"{what} is not valid JSON: {exc}") from exc


@dataclass(frozen=True)
class SourceIndex:
    """The parsed index, with nothing checked yet."""

    sources: tuple[dict[str, Any], ...]
    not_sources: dict[str, str]
    raw: dict[str, Any]

    def by_id(self) -> dict[str, dict[str, Any]]:
        return {s["source_id"]: s for s in self.sources if isinstance(s.get("source_id"), str)}


def load_index(repo_root: Path) -> SourceIndex:
    """Read and shallow-parse the index, or refuse it.

    Refuses rather than returns empty: an absent index is the one case where a
    caller could mistake "nothing to check" for "nothing wrong".
    """
    path = repo_root / SOURCES_REL
    if not path.is_file():
        raise SourceIndexError(f"{SOURCES_REL} is absent")
    doc = _read_json(path, SOURCES_REL)
    if not isinstance(doc, dict):
        raise SourceIndexError(f"{SOURCES_REL} is not a JSON object")
    if doc.get("record_type") != SOURCE_INDEX_RECORD_TYPE:
        raise SourceIndexError(
            f"{SOURCES_REL}: record_type {doc.get('record_type')!r} is not "
            f"{SOURCE_INDEX_RECORD_TYPE!r}"
        )
    sources = doc.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SourceIndexError(f"{SOURCES_REL}: 'sources' must be a non-empty list")
    if not all(isinstance(s, dict) for s in sources):
        raise SourceIndexError(f"{SOURCES_REL}: every entry of 'sources' must be an object")
    not_sources = doc.get("names_that_are_not_sources", {})
    if not isinstance(not_sources, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and v.strip()
        for k, v in not_sources.items()
    ):
        raise SourceIndexError(
            f"{SOURCES_REL}: 'names_that_are_not_sources' must map each name to a "
            f"non-empty reason"
        )
    return SourceIndex(tuple(sources), dict(not_sources), doc)


# ---------------------------------------------------------------------------
# The candidate derivation
# ---------------------------------------------------------------------------


def candidate_names(repo_root: Path) -> dict[str, tuple[str, ...]]:
    """Derive the external-name candidates from the concept, with their files.

    Returns each candidate mapped to the repo-relative paths that name it, sorted.
    A path in :data:`NAMED_IN_PATHS` that does not exist is skipped, so the
    derivation reports on the artifacts the branch actually has.
    """
    found: dict[str, set[str]] = {}
    for rel in NAMED_IN_PATHS:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig")
        for pattern in (_PHRASE_RE, _ACRONYM_RE, _MISSION_RE):
            for match in pattern.finditer(text):
                found.setdefault(match.group(0), set()).add(rel)
        for name in SINGLE_WORD_EXTERNALS:
            if re.search(r"\b" + re.escape(name), text):
                found.setdefault(name, set()).add(rel)
    return {name: tuple(sorted(paths)) for name, paths in sorted(found.items())}


# ---------------------------------------------------------------------------
# Per-record checks
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = ("source_id", "title", "kind", "status", "citation", "resolves_to",
                  "transcription", "relied_on_for")

_ID_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(?:[-#][A-Za-z0-9]+)*$")


def _check_shape(rec: dict[str, Any], where: str) -> list[SourceProblem]:
    problems: list[SourceProblem] = []

    def bad(kind: str, message: str) -> None:
        problems.append(SourceProblem(where, kind, message))

    for key in _REQUIRED_KEYS:
        if key not in rec:
            bad("shape", f"missing required key {key!r}")
    if problems:
        return problems
    sid = rec["source_id"]
    if not isinstance(sid, str) or not _ID_RE.match(sid):
        bad("shape", f"source_id {sid!r} is not a plain identifier")
    if not isinstance(rec["title"], str) or not rec["title"].strip():
        bad("shape", "title is empty")
    kind = rec["kind"]
    if kind not in SOURCE_KINDS:
        bad("shape", f"kind {kind!r} is not in {sorted(SOURCE_KINDS)}")
    if rec["status"] not in STATUSES:
        bad("shape", f"status {rec['status']!r} is not in {sorted(STATUSES)}")
    citation = rec["citation"]
    if not isinstance(citation, dict) or not isinstance(citation.get("cited_as"), str) \
            or not citation["cited_as"].strip():
        bad("shape", "citation.cited_as is missing or empty")
    relied = rec["relied_on_for"]
    if not isinstance(relied, list) or not relied:
        bad("shape", "relied_on_for is empty: a source nothing relies on is not a source")
    else:
        for i, use in enumerate(relied):
            at = f"{where}.relied_on_for[{i}]"
            if not isinstance(use, dict):
                problems.append(SourceProblem(at, "shape", "not an object"))
                continue
            if not isinstance(use.get("what"), str) or not use["what"].strip():
                problems.append(SourceProblem(at, "shape", "'what' is missing or empty"))
            if use.get("status") not in STATUSES:
                problems.append(
                    SourceProblem(at, "shape", f"status {use.get('status')!r} is not a §12.2 status")
                )
    return problems


def _check_resolution(rec: dict[str, Any], repo_root: Path, where: str,
                      registry: set[str]) -> list[SourceProblem]:
    """Every source must resolve: to a stored file, or to a declared identifier."""
    problems: list[SourceProblem] = []
    res = rec.get("resolves_to")
    if not isinstance(res, dict):
        return [SourceProblem(where, "resolution", "resolves_to is not an object")]
    cls = res.get("class")
    if cls not in RESOLUTION_CLASSES:
        return [SourceProblem(where, "resolution",
                              f"class {cls!r} is not in {sorted(RESOLUTION_CLASSES)}")]
    if not isinstance(res.get("what_it_holds"), str) or not res["what_it_holds"].strip():
        problems.append(SourceProblem(where, "resolution",
                                      "what_it_holds is missing: a location must say what "
                                      "resolving it gets the reader"))
    if cls == "stored_document":
        stored = res.get("stored_path")
        if not isinstance(stored, str) or not (repo_root / stored).is_file():
            problems.append(SourceProblem(where, "resolution",
                                          f"stored_path {stored!r} is not a file in this repository"))
        doc_id = res.get("document_id")
        if not isinstance(doc_id, str) or doc_id not in registry:
            problems.append(SourceProblem(where, "resolution",
                                          f"document_id {doc_id!r} is not registered in "
                                          f"{DOCUMENT_REGISTRY_REL} (§9.6)"))
    else:
        identifier = res.get("identifier")
        has_identifier = isinstance(identifier, str) and identifier.strip()
        if not has_identifier:
            # An identifier nobody could verify is better left null than guessed,
            # but the source must still resolve somewhere. An anchor into a stored
            # document is that somewhere: the reader can at least reach the text
            # that names it. A source with neither resolves to nothing at all.
            anchored = _has_anchor(rec)
            if identifier is not None:
                problems.append(SourceProblem(where, "resolution",
                                              "identifier must be a non-empty string or null"))
            elif res.get("identifier_status") != "Unresolved":
                problems.append(SourceProblem(where, "resolution",
                                              "a null identifier must carry "
                                              "identifier_status Unresolved"))
            elif not anchored:
                problems.append(SourceProblem(where, "resolution",
                                              "no identifier and no anchor: the source resolves "
                                              "to nothing a reader can reach"))
        if res.get("identifier_status") not in STATUSES:
            problems.append(SourceProblem(where, "resolution",
                                          f"identifier_status {res.get('identifier_status')!r} is "
                                          f"not a §12.2 status"))
        elif res["identifier_status"] == "Confirmed":
            problems.append(SourceProblem(where, "resolution",
                                          "an external identifier cannot be Confirmed on this "
                                          "branch: nothing resolved it, so it is recorded from "
                                          "prior knowledge and §10.6 requires that to be flagged"))
        if not isinstance(res.get("basis"), str) or not res["basis"].strip():
            problems.append(SourceProblem(where, "resolution",
                                          "basis is missing: an unresolved identifier must say "
                                          "where it came from"))
    return problems


def _check_transcription(rec: dict[str, Any], repo_root: Path,
                         where: str) -> tuple[list[SourceProblem], Optional[str]]:
    """Check the transcription state against the record, and return the text.

    The byte-equal leg is the anti-fabrication guarantee: ``text`` must equal
    :func:`read_page_text` re-run on the stored page, exactly.

    The returned text is what the record *declares*, not what replayed. When the
    replay fails or the method is one this module cannot re-run, a problem is
    reported and the declared text is still returned, so the span checks give
    their own diagnosis rather than collapsing into "no text". Both problems
    reach :func:`verify`, so a source in that state can never pass.
    """
    problems: list[SourceProblem] = []
    tr = rec.get("transcription")
    if not isinstance(tr, dict):
        return [SourceProblem(where, "transcription", "transcription is not an object")], None
    state = tr.get("state")
    if state not in TRANSCRIPTION_STATES:
        return [SourceProblem(where, "transcription",
                              f"state {state!r} is not in {sorted(TRANSCRIPTION_STATES)}")], None
    kind = rec.get("kind")
    if kind in SOURCE_KINDS and SOURCE_KINDS[kind] != state:
        problems.append(SourceProblem(where, "transcription",
                                      f"kind {kind!r} requires state "
                                      f"{SOURCE_KINDS[kind]!r}, not {state!r}"))
    text = rec.get("text")
    if state == "cited_only":
        if text is not None:
            problems.append(SourceProblem(where, "transcription",
                                          "a cited_only source carries text, so a span could be "
                                          "pointed at a document nobody stored"))
        if rec.get("spans"):
            problems.append(SourceProblem(where, "transcription",
                                          "a cited_only source carries spans"))
        if not isinstance(tr.get("reason"), str) or not tr["reason"].strip():
            problems.append(SourceProblem(where, "transcription",
                                          "reason is missing: an untranscribed source must say why"))
        return problems, None
    # transcribed
    if tr.get("method") != PAGE_TEXT_METHOD:
        problems.append(SourceProblem(where, "transcription",
                                      f"method {tr.get('method')!r} is not {PAGE_TEXT_METHOD!r}, "
                                      f"the only method this module can replay"))
        return problems, text if isinstance(text, str) else None
    if not isinstance(text, str) or not text.strip():
        problems.append(SourceProblem(where, "transcription", "text is missing or empty"))
        return problems, None
    res = rec.get("resolves_to") or {}
    stored, page = res.get("stored_path"), res.get("page")
    if not isinstance(stored, str) or not isinstance(page, int) or isinstance(page, bool):
        problems.append(SourceProblem(where, "transcription",
                                      "a transcribed source needs resolves_to.stored_path and "
                                      "an integer resolves_to.page to replay against"))
        return problems, text
    path = repo_root / stored
    if not path.is_file():
        problems.append(SourceProblem(where, "transcription",
                                      f"stored_path {stored!r} is absent, so the transcription "
                                      f"cannot be replayed"))
        return problems, text
    replayed = read_page_text(path, page)
    if replayed != text:
        problems.append(SourceProblem(where, "transcription",
                                      f"text is not byte-equal to {PAGE_TEXT_METHOD} re-run on "
                                      f"{stored} page {page} "
                                      f"(stored {len(text)} chars, replayed {len(replayed)})"))
    return problems, text


def span_id(source_id: str, start: int, end: int) -> str:
    """The canonical id of a span: ``<source_id>#<start>-<end>``.

    Lives here rather than in the generator because the id encodes the offsets,
    so a verifier that only checked the id were non-empty would accept a record
    whose id names offsets the record no longer has. The generator imports this
    and :func:`_check_spans` recomputes it, which is the same shared-function
    rule that makes the transcription replay meaningful.
    """
    return f"{source_id}#{start}-{end}"


def _check_spans(rec: dict[str, Any], text: Optional[str], where: str,
                 claim_ids: set[str]) -> tuple[list[SourceProblem], set[str]]:
    """Check every span and return the ids of those that resolved.

    The returned set is what :func:`_check_no_overclaim` needs: a use may claim
    Confirmed only against a span that actually resolved, not merely against one
    the record declares.
    """
    problems: list[SourceProblem] = []
    spans = rec.get("spans") or []
    if not isinstance(spans, list):
        return [SourceProblem(where, "span", "spans is not a list")], set()
    resolved: set[str] = set()
    seen: set[str] = set()
    for i, span in enumerate(spans):
        at = f"{where}.spans[{i}]"
        if not isinstance(span, dict):
            problems.append(SourceProblem(at, "span", "not an object"))
            continue
        declared_id, start, end = span.get("span_id"), span.get("start"), span.get("end")
        quote = span.get("quote")
        if not isinstance(declared_id, str) or not declared_id.strip():
            problems.append(SourceProblem(at, "span", "span_id is missing"))
        elif declared_id in seen:
            problems.append(SourceProblem(at, "span", f"span_id {declared_id!r} is declared twice"))
        else:
            seen.add(declared_id)
        if not isinstance(start, int) or not isinstance(end, int) \
                or isinstance(start, bool) or isinstance(end, bool):
            problems.append(SourceProblem(at, "span", "start and end must be integers"))
            continue
        if start < 0 or end <= start:
            problems.append(SourceProblem(at, "span", f"offset range {start}-{end} is empty"))
            continue
        if not isinstance(quote, str) or not quote:
            problems.append(SourceProblem(at, "span", "quote is missing"))
            continue
        if text is None:
            problems.append(SourceProblem(at, "span", "the source carries no text to resolve into"))
            continue
        if end > len(text):
            problems.append(SourceProblem(at, "span",
                                          f"offset range {start}-{end} exceeds the text "
                                          f"({len(text)} chars)"))
            continue
        if text[start:end] != quote:
            problems.append(SourceProblem(at, "span",
                                          f"quote is not the text at {start}-{end}: the record "
                                          f"says {quote[:60]!r}, the text says "
                                          f"{text[start:end][:60]!r}"))
            continue
        canonical = span_id(str(rec.get("source_id")), start, end)
        if declared_id != canonical:
            problems.append(SourceProblem(at, "span",
                                          f"span_id {declared_id!r} does not encode its own "
                                          f"offsets: the canonical id is {canonical!r}"))
            continue
        resolved.add(declared_id)
        for ref in span.get("claim_refs") or []:
            if ref not in claim_ids:
                problems.append(SourceProblem(at, "span",
                                              f"claim_ref {ref!r} is not a concept claim in "
                                              f"{PROJECT_SUMMARY_REL}"))
    return problems, resolved


def _has_anchor(rec: dict[str, Any]) -> bool:
    """Whether the record declares an anchor at all.

    Only the declaration. Whether the anchor holds is :func:`_check_anchor`'s
    question, and the two must not answer it differently.
    """
    anchor = rec.get("anchor")
    return isinstance(anchor, dict) and bool(anchor.get("via_source") or anchor.get("artifact"))


def _check_anchor(rec: dict[str, Any], repo_root: Path, where: str,
                  by_id: dict[str, dict[str, Any]]) -> list[SourceProblem]:
    """An external reference must be anchored in a stored artifact that names it.

    The anchor is what makes a reference resolvable without a stored copy: some
    file in this repository says this name, verbatim. A reference whose anchor
    string is not in the artifact it names is a reference the project does not
    actually cite, and it fails here.

    Two strengths, and the difference matters. A ``via_source`` anchor must land
    inside the ``quote`` of a declared span of that source, so it sits in text
    replayed byte-for-byte at an offset the record gives. An ``artifact`` anchor
    only asks that the string occur *somewhere* in the named text file, which is
    all that can be checked of a file with no span structure.

    Nothing in the current index uses the ``artifact`` branch: every reference is
    anchored in the call text. It exists for the case findings F4 and F10 name —
    a source the concept cites that the call never mentions, whose only anchor is
    a Tier 3 artifact — and is covered by its own test rather than left untested.
    """
    problems: list[SourceProblem] = []
    anchor = rec.get("anchor")
    if not isinstance(anchor, dict):
        return [SourceProblem(where, "anchor",
                              "an external_reference needs an anchor naming a stored artifact "
                              "that names it")]
    artifact, verbatim = anchor.get("artifact"), anchor.get("verbatim")
    if not isinstance(verbatim, str) or not verbatim.strip():
        problems.append(SourceProblem(where, "anchor", "anchor.verbatim is missing or empty"))
        return problems
    via = anchor.get("via_source")
    if via is not None:
        if via not in by_id:
            problems.append(SourceProblem(where, "anchor",
                                          f"anchor.via_source {via!r} is not a source in this index"))
            return problems
        host = by_id[via]
        host_text = host.get("text")
        if not isinstance(host_text, str):
            problems.append(SourceProblem(where, "anchor",
                                          f"anchor.via_source {via!r} carries no transcribed text"))
            return problems
        span_id = anchor.get("span_id")
        spans = {s.get("span_id"): s for s in (host.get("spans") or []) if isinstance(s, dict)}
        if span_id not in spans:
            problems.append(SourceProblem(where, "anchor",
                                          f"anchor.span_id {span_id!r} is not a span of {via}"))
            return problems
        quote = spans[span_id].get("quote")
        if not isinstance(quote, str) or verbatim not in quote:
            problems.append(SourceProblem(where, "anchor",
                                          f"anchor.verbatim {verbatim!r} does not occur in span "
                                          f"{span_id} of {via}"))
        return problems
    if not isinstance(artifact, str):
        problems.append(SourceProblem(where, "anchor",
                                      "anchor needs either via_source or artifact"))
        return problems
    path = repo_root / artifact
    if not path.is_file():
        problems.append(SourceProblem(where, "anchor",
                                      f"anchor.artifact {artifact!r} is not a file in this "
                                      f"repository"))
        return problems
    if path.suffix.lower() not in {".json", ".md", ".yaml", ".yml", ".txt", ".csv"}:
        problems.append(SourceProblem(where, "anchor",
                                      f"anchor.artifact {artifact!r} is not a text file, so the "
                                      f"anchor cannot be checked here"))
        return problems
    if verbatim not in path.read_text(encoding="utf-8-sig"):
        problems.append(SourceProblem(where, "anchor",
                                      f"anchor.verbatim {verbatim!r} does not occur in {artifact}"))
    return problems


def _check_no_overclaim(rec: dict[str, Any], where: str, resolved: set[str],
                        claim_ids: set[str]) -> list[SourceProblem]:
    """A use of a source may only be Confirmed against a span that resolved.

    This is the ticket's third criterion in code. ``relied_on_for`` is where a
    record says what the project takes from a source, and the only thing that
    can make such a use Confirmed is a span whose quote was found at its own
    offsets in replayed text. *resolved* carries exactly those, so a declared
    span that failed to resolve cannot be leant on.

    ``claim_refs`` is checked here too. A use that names a claim the concept
    does not make is the plainest form of describing a source as supporting
    something it does not: nothing on either side of the reference exists.

    A use that names no span keeps whatever lower status it declares. Declared
    status and verified span stay two separate fields, neither inferred from the
    other.
    """
    problems: list[SourceProblem] = []
    for i, use in enumerate(rec.get("relied_on_for") or []):
        if not isinstance(use, dict):
            continue
        at = f"{where}.relied_on_for[{i}]"
        claims = use.get("claim_refs")
        if not isinstance(claims, list):
            problems.append(SourceProblem(at, "overclaim", "claim_refs is not a list"))
        else:
            absent = [c for c in claims if c not in claim_ids]
            if absent:
                problems.append(SourceProblem(at, "overclaim",
                                              f"claim_refs name claims the concept does not make: "
                                              f"{absent}"))
        refs = use.get("span_refs")
        if not isinstance(refs, list):
            problems.append(SourceProblem(at, "overclaim", "span_refs is not a list"))
            continue
        unknown = [r for r in refs if r not in resolved]
        if unknown:
            problems.append(SourceProblem(at, "overclaim",
                                          f"span_refs name spans this source does not declare, or "
                                          f"that failed to resolve: {unknown}"))
        if use.get("status") == "Confirmed" and not refs:
            problems.append(SourceProblem(at, "overclaim",
                                          "Confirmed with no span_refs: nothing verified this use, "
                                          "so it may not carry Confirmed (§12.2)"))
    return problems


def _swept_texts(repo_root: Path) -> dict[str, str]:
    """The Tier 3 artifacts the name checks read, read once per pass."""
    return {rel: (repo_root / rel).read_text(encoding="utf-8-sig")
            for rel in NAMED_IN_PATHS if (repo_root / rel).is_file()}


def _check_names(rec: dict[str, Any], texts: dict[str, str], where: str) -> list[SourceProblem]:
    """Each alias a reference claims must actually appear in a swept artifact."""
    problems: list[SourceProblem] = []
    names = rec.get("names")
    if not isinstance(names, list) or not names or not all(isinstance(n, str) and n.strip()
                                                           for n in names):
        return [SourceProblem(where, "coverage",
                              "an external_reference needs a non-empty 'names' list: it is what "
                              "the concept calls this source")]
    for name in names:
        if not any(name in text for text in texts.values()):
            problems.append(SourceProblem(where, "coverage",
                                          f"name {name!r} appears in no swept Tier 3 artifact, so "
                                          f"this source claims a citation the concept does not make"))
    return problems


# ---------------------------------------------------------------------------
# The whole pass
# ---------------------------------------------------------------------------


def _registered_document_ids(repo_root: Path) -> set[str]:
    path = repo_root / DOCUMENT_REGISTRY_REL
    if not path.is_file():
        raise SourceIndexError(f"{DOCUMENT_REGISTRY_REL} is absent")
    doc = _read_json(path, DOCUMENT_REGISTRY_REL)
    entries = doc.get("document_registry") if isinstance(doc, dict) else None
    if not isinstance(entries, list):
        raise SourceIndexError(f"{DOCUMENT_REGISTRY_REL}: 'document_registry' is not a list")
    return {e["document_id"] for e in entries
            if isinstance(e, dict) and isinstance(e.get("document_id"), str)}


def _concept_claim_ids(repo_root: Path) -> set[str]:
    path = repo_root / PROJECT_SUMMARY_REL
    if not path.is_file():
        return set()
    doc = _read_json(path, PROJECT_SUMMARY_REL)
    claims = doc.get("concept_claims") if isinstance(doc, dict) else None
    if not isinstance(claims, list):
        return set()
    return {c["claim_id"] for c in claims
            if isinstance(c, dict) and isinstance(c.get("claim_id"), str)}


def _check_coverage(index: SourceIndex, candidates: dict[str, tuple[str, ...]]
                    ) -> list[SourceProblem]:
    """Every derived candidate is claimed by a source or declared not to be one.

    The partition, and the reason the "each cited source has an entry" criterion
    is a check rather than an assertion. Two directions are enforced: no
    candidate is left unclassified, and no name is declared twice.
    """
    problems: list[SourceProblem] = []
    claimed: dict[str, str] = {}
    for rec in index.sources:
        sid = rec.get("source_id")
        for name in rec.get("names") or []:
            if not isinstance(name, str):
                continue
            if name in claimed:
                problems.append(SourceProblem(name, "coverage",
                                              f"claimed by both {claimed[name]} and {sid}"))
            else:
                claimed[name] = str(sid)
    for name in sorted(set(claimed) & set(index.not_sources)):
        problems.append(SourceProblem(name, "coverage",
                                      f"claimed by {claimed[name]} and also declared not to be a "
                                      f"source"))
    for name, paths in candidates.items():
        if name in claimed or name in index.not_sources:
            continue
        problems.append(SourceProblem(name, "coverage",
                                      f"named in {', '.join(paths)} but neither claimed by a "
                                      f"source nor declared in names_that_are_not_sources"))
    for name in sorted(index.not_sources):
        if name not in candidates:
            problems.append(SourceProblem(name, "coverage",
                                          "declared not to be a source, but the derivation does "
                                          "not produce it: a dead entry hides a drift in the sweep"))
    return problems


def verify(repo_root: Path) -> SourceIndexReport:
    """Run every check over the index and report. Writes nothing."""
    index = load_index(repo_root)
    registry = _registered_document_ids(repo_root)
    claim_ids = _concept_claim_ids(repo_root)
    swept = _swept_texts(repo_root)
    by_id = index.by_id()
    problems: list[SourceProblem] = []
    checked: list[str] = []
    transcribed: list[str] = []
    resolved_total = 0

    seen_ids: set[str] = set()
    for i, rec in enumerate(index.sources):
        where = rec.get("source_id") if isinstance(rec.get("source_id"), str) else f"sources[{i}]"
        shape = _check_shape(rec, where)
        problems.extend(shape)
        if shape:
            continue
        sid = rec["source_id"]
        if sid in seen_ids:
            problems.append(SourceProblem(where, "shape", "source_id is declared twice"))
            continue
        seen_ids.add(sid)
        checked.append(sid)
        problems.extend(_check_resolution(rec, repo_root, where, registry))
        transcription_problems, text = _check_transcription(rec, repo_root, where)
        problems.extend(transcription_problems)
        if text is not None:
            transcribed.append(sid)
        span_problems, resolved = _check_spans(rec, text, where, claim_ids)
        problems.extend(span_problems)
        resolved_total += len(resolved)
        problems.extend(_check_no_overclaim(rec, where, resolved, claim_ids))
        if rec["kind"] == "external_reference":
            problems.extend(_check_anchor(rec, repo_root, where, by_id))
            problems.extend(_check_names(rec, swept, where))

    candidates = candidate_names(repo_root)
    problems.extend(_check_coverage(index, candidates))
    return SourceIndexReport(
        sources_checked=tuple(checked),
        transcribed=tuple(transcribed),
        spans_resolved=resolved_total,
        candidates=tuple(candidates),
        problems=tuple(problems),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Verify the Tier 3 source index. Exit 0 when it holds, 1 when it does not."""
    parser = argparse.ArgumentParser(
        prog="python -m runner.source_index",
        description="Verify docs/tier3_project_instantiation/source_materials/sources.json: "
                    "transcriptions replay byte-equal, spans resolve, references are anchored, "
                    "and every external name the concept uses is classified.",
    )
    parser.add_argument("--repo-root", default=None,
                        help="Repository root (default: discovered from the working directory).")
    args = parser.parse_args(argv)
    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        from runner.paths import find_repo_root

        repo_root = find_repo_root()
    try:
        report = verify(repo_root)
    except SourceIndexError as exc:
        # Exit 3, as runner/leakage_scan.py does: "the check could not run" is a
        # different answer from "the check ran and failed", and collapsing them
        # into 1 would let a caller read an unreadable index as a bad index.
        print(f"[source-index] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3
    print(report.format())
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
