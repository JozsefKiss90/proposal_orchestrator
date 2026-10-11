"""
Candidate provenance — what the audit may say about one imported candidate (ticket V05).

Why this exists
---------------
The integrity audit (:mod:`harness.integrity_audit`) reports every claim in a
candidate's ledger ``Unresolved``, and it reports the recruiting participant
against the host line as *not comparable*.  Both statements need a reason, and
the reason is a fact about **the document that was imported**, not about the
audit.  A sanitised derivative lost its citations and its identifiers, so
corroboration is missing because the transformation removed it.  A document
that carries its references and its real partner names lost nothing: its
claims are still unresolved here, but for a different reason, and its host
line *is* comparable with its table.  One constant applied to both would
misstate one of them.

So the reason and the identity wording are derived, per candidate, from the
records the import wrote.

What it reads
-------------
Two records, both already committed beside the candidate:

* the **import manifest** (``<graph root>/docs/tier4_orchestration_state/dev_graph/imports/*.json``),
  which names the candidate's fidelity register and declares the status its
  claim ledger carries; and
* the **fidelity register** that manifest names, whose ``provenance.transformation``
  half is the operator's declaration about what the transformation did, and
  whose ``derived`` half is the importer's own measurement over the stored
  bytes.

A declaration and a measurement are different kinds of evidence, and the
measurement governs.  The register declares that citations were removed; the
importer counted zero bracketed numbers, DOIs, URLs and author-year markers in
the bytes.  Agreement makes the cause ``Confirmed`` in substance; disagreement
is a flag, not a silent choice.

The derivation
--------------
*The grounding cause* needs three statements to agree before the audit may
name sanitisation:

1. the register declares that citations were removed,
2. the importer measured no citation marker in the candidate, and
3. the register declares the candidate is not the submitted document.

All three: :data:`CAUSE_SANITISATION`.  A measured marker count above zero:
:data:`CAUSE_SOURCES_PRESENT` — the candidate cites sources and this
repository has no route that resolves them.  Anything else, including a
missing record and an unrecognised declaration: :data:`CAUSE_UNSTATED`, whose
reason says the cause is Unresolved and borrows no other candidate's
explanation.

*The identity scope* comes from the register's declared ``identifiers`` value
alone, because no measurement can tell a real partner name from a generalised
one.  :data:`IDENTITY_GENERALISED` makes the host line not comparable with the
table and supplies the sentence that says why.  :data:`IDENTITY_AS_SUBMITTED`
makes the two comparable, and the audit compares them.
:data:`IDENTITY_UNSTATED` leaves them not comparable, for the stated reason
that nothing declares which they are — never for the sanitisation reason.

*The expected ledger status* is the status the import manifest declares its
ledger carries.  Without a manifest there is no declared expectation, and the
audit says so rather than assuming one.

Reading a declared value
------------------------
A declared transformation field is prose an operator wrote.  Only its leading
word is read, against a closed vocabulary (:data:`CITATIONS_REMOVED_WORDS` and
the three sets beside it), after an optional leading ``all``.  So ``"all
removed; no bracketed numbers, author-year, DOIs, URLs or reference list"``
reads as *removed* and ``"generalised (project acronym, partner names, people,
places)"`` as *generalised*.  A value whose leading word is in no vocabulary is
reported unstated with the value quoted, never read as either side.  The rule
is narrow on purpose: a sentence an operator phrased differently must produce
an explicit gap, not a guess.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA; reads committed import and
    fidelity records read-only and writes nothing.  Never a runtime gate.
    See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "IMPORT_MANIFESTS_REL",
    "CAUSE_SANITISATION",
    "CAUSE_SOURCES_PRESENT",
    "CAUSE_UNSTATED",
    "GROUNDING_CAUSES",
    "REASON_SANITISATION",
    "REASON_SOURCES_PRESENT",
    "REASON_UNSTATED",
    "GROUNDING_REASONS",
    "IDENTITY_GENERALISED",
    "IDENTITY_AS_SUBMITTED",
    "IDENTITY_UNSTATED",
    "IDENTITY_SCOPES",
    "STATEMENT_GENERALISED",
    "STATEMENT_UNSTATED",
    "IDENTITY_STATEMENTS",
    "CITATIONS_REMOVED_WORDS",
    "CITATIONS_PRESENT_WORDS",
    "IDENTIFIERS_GENERALISED_WORDS",
    "IDENTIFIERS_AS_SUBMITTED_WORDS",
    "CandidateProvenanceError",
    "CandidateProvenance",
    "UNSTATED_PROVENANCE",
    "declared_word",
    "find_import_manifest",
    "provenance_from_manifest",
    "resolve_provenance",
    "render_provenance",
]

#: Where an external import leaves its manifest, relative to the graph root.
#: Mirrors the importer's own constant; the harness cannot import ``tools``.
IMPORT_MANIFESTS_REL: str = "docs/tier4_orchestration_state/dev_graph/imports"

# --------------------------------------------------------------------------- #
# The vocabulary
# --------------------------------------------------------------------------- #

#: The transformation removed the candidate's supporting sources.
CAUSE_SANITISATION: str = "supporting_sources_removed_by_sanitisation"
#: The candidate carries source markers and nothing here resolves them.
CAUSE_SOURCES_PRESENT: str = "supporting_sources_present_and_unresolved"
#: No record states why corroboration is missing.
CAUSE_UNSTATED: str = "unstated"
#: The closed set of grounding causes.
GROUNDING_CAUSES: tuple[str, ...] = (CAUSE_SANITISATION, CAUSE_SOURCES_PRESENT, CAUSE_UNSTATED)

#: Spec decision 15's reason, now the reason of one cause rather than of every
#: document.  Byte-identical to the wording the committed sanitised audits carry.
REASON_SANITISATION: str = "supporting sources removed by sanitisation"
#: The reason for a candidate that still cites its sources.
REASON_SOURCES_PRESENT: str = (
    "the candidate carries supporting source markers and no imported-claim route resolves them"
)
#: The reason when provenance states no cause.  Explicitly Unresolved, never borrowed.
REASON_UNSTATED: str = (
    "the candidate's recorded provenance states no grounding cause; why corroboration is "
    "missing is Unresolved"
)
#: Cause to reason, one entry per cause.
GROUNDING_REASONS: Mapping[str, str] = {
    CAUSE_SANITISATION: REASON_SANITISATION,
    CAUSE_SOURCES_PRESENT: REASON_SOURCES_PRESENT,
    CAUSE_UNSTATED: REASON_UNSTATED,
}

#: The identifiers were generalised; a name in one place cannot be matched to another.
IDENTITY_GENERALISED: str = "identifiers_generalised"
#: The identifiers are the submitted document's own; names are comparable.
IDENTITY_AS_SUBMITTED: str = "identifiers_as_submitted"
#: Nothing declares which; the audit compares nothing and says that.
IDENTITY_UNSTATED: str = "identifiers_unstated"
#: The closed set of identity scopes.
IDENTITY_SCOPES: tuple[str, ...] = (IDENTITY_GENERALISED, IDENTITY_AS_SUBMITTED, IDENTITY_UNSTATED)

#: The clause a not-comparable identity finding carries when identifiers were
#: generalised.  Byte-identical to the committed sanitised audits' wording.
STATEMENT_GENERALISED: str = (
    "The identifiers were removed by sanitisation, so the two cannot be compared"
)
#: The clause it carries when no record states the identity scope.
STATEMENT_UNSTATED: str = (
    "The candidate's recorded provenance does not state whether the identifiers are the "
    "submitted document's own, so the two cannot be compared"
)
#: Scope to the clause a not-comparable finding carries, one entry per scope.
#: :data:`IDENTITY_AS_SUBMITTED` maps to the empty clause: the audit compares
#: the two names under that scope, and a comparison needs no excuse.
IDENTITY_STATEMENTS: Mapping[str, str] = {
    IDENTITY_GENERALISED: STATEMENT_GENERALISED,
    IDENTITY_AS_SUBMITTED: "",
    IDENTITY_UNSTATED: STATEMENT_UNSTATED,
}

#: Leading words of a declared ``citations`` value that mean the sources are gone.
CITATIONS_REMOVED_WORDS: frozenset[str] = frozenset({"removed", "stripped", "deleted"})
#: Leading words of a declared ``citations`` value that mean they are still there.
CITATIONS_PRESENT_WORDS: frozenset[str] = frozenset(
    {"present", "retained", "kept", "unchanged", "intact"}
)
#: Leading words of a declared ``identifiers`` value that mean they were generalised.
IDENTIFIERS_GENERALISED_WORDS: frozenset[str] = frozenset(
    {"generalised", "generalized", "anonymised", "anonymized", "pseudonymised",
     "pseudonymized", "redacted", "removed", "withheld"}
)
#: Leading words of a declared ``identifiers`` value that mean they are as submitted.
IDENTIFIERS_AS_SUBMITTED_WORDS: frozenset[str] = frozenset(
    {"unchanged", "retained", "kept", "intact", "present", "original"}
)

#: The measured counts whose sum is the candidate's citation-marker capability.
_CITATION_COUNT_BLOCK: str = "citation_marker_counts"

#: How one declared transformation value reads: the transformation changed what
#: the field names, left it as submitted, or said something the vocabulary of
#: that field does not hold.  One tri-state over two vocabularies, so citations
#: and identifiers are read by one rule.
_DECLARED_CHANGED: str = "changed"
_DECLARED_UNCHANGED: str = "unchanged"
_DECLARED_UNREADABLE: str = "unreadable"


class CandidateProvenanceError(Exception):
    """A provenance record was named and could not be read."""


# --------------------------------------------------------------------------- #
# The record
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CandidateProvenance:
    """What the audit may say about one candidate, and on whose authority.

    The two wordings are **derived, not stored**: the reason is
    :data:`GROUNDING_REASONS` of the cause and the statement is
    :data:`IDENTITY_STATEMENTS` of the scope.  A record carrying a cause and
    another cause's reason therefore cannot be built at all, which is a
    stronger guarantee than rejecting one.

    Attributes
    ----------
    grounding_cause:
        One of :data:`GROUNDING_CAUSES`.  :attr:`grounding_reason` is the
        sentence every grounding row then carries.
    identity_scope:
        One of :data:`IDENTITY_SCOPES`.  :data:`IDENTITY_AS_SUBMITTED` is the
        only scope under which a name in a table may be compared with a name
        in prose.
    expected_ledger_status:
        The status the import manifest declares its claim ledger carries, in
        lower case, or ``None`` when no manifest declared one.  ``None`` is not
        ``"unresolved"``: it means the audit has no declared contract to check
        an entry against.
    is_submitted_document:
        The register's declaration, or ``None`` when unread.
    sources:
        Repo-relative paths of the records read, in read order.
    basis:
        One line per statement the derivation rests on, so a reader can check
        the wording against the record without reopening it.
    flags:
        Contradictions and gaps.  The audit carries these into its own flags,
        which makes the command exit non-zero.
    """

    grounding_cause: str
    identity_scope: str
    expected_ledger_status: str | None = None
    is_submitted_document: bool | None = None
    sources: tuple[str, ...] = ()
    basis: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.grounding_cause not in GROUNDING_CAUSES:
            raise ValueError(f"unknown grounding cause {self.grounding_cause!r}.")
        if self.identity_scope not in IDENTITY_SCOPES:
            raise ValueError(f"unknown identity scope {self.identity_scope!r}.")

    @property
    def grounding_reason(self) -> str:
        """The sentence every grounding row carries, one per cause."""
        return GROUNDING_REASONS[self.grounding_cause]

    @property
    def identity_statement(self) -> str:
        """The clause a not-comparable identity finding carries.

        Empty under :data:`IDENTITY_AS_SUBMITTED`, because a comparison that
        was made needs no excuse.
        """
        return IDENTITY_STATEMENTS[self.identity_scope]

    @property
    def identities_are_comparable(self) -> bool:
        """True only when a declaration says the identifiers are as submitted."""
        return self.identity_scope == IDENTITY_AS_SUBMITTED


def _unstated(*, basis: tuple[str, ...], flags: tuple[str, ...] = (),
              sources: tuple[str, ...] = ()) -> CandidateProvenance:
    return CandidateProvenance(
        grounding_cause=CAUSE_UNSTATED,
        identity_scope=IDENTITY_UNSTATED,
        sources=sources,
        basis=basis,
        flags=flags,
    )


def render_provenance(provenance: CandidateProvenance) -> str:
    """The derivation behind the audit's wording, for the operator's screen.

    The persisted audit report keeps its schema and gains no key, so this is
    the trail that satisfies CLAUDE.md §12.1 for the reason the report carries:
    the cause, the records read, and one line per statement it rests on.
    """
    lines = [
        f"provenance: grounding cause {provenance.grounding_cause}; identity "
        f"{provenance.identity_scope}; expected ledger status "
        f"{provenance.expected_ledger_status or 'none declared'}",
    ]
    for source in provenance.sources or ("none read",):
        lines.append(f"    read: {source}")
    for line in provenance.basis:
        lines.append(f"    basis: {line}")
    return "\n".join(lines)


#: What the audit knows about a candidate whose provenance it was never given.
#: Every wording it carries says so; none is borrowed from another document.
UNSTATED_PROVENANCE: CandidateProvenance = _unstated(
    basis=("no provenance record was resolved for this candidate",),
)


# --------------------------------------------------------------------------- #
# Reading a declared value
# --------------------------------------------------------------------------- #


def declared_word(value: Any) -> str:
    """The leading word of a declared transformation value, lower-cased.

    An optional leading ``all`` is dropped (``"all removed; no DOIs"`` reads as
    ``removed``), and trailing punctuation is cut.  A non-string, or a value
    with no word at all, yields ``""`` — which matches no vocabulary and so
    reads as unstated.
    """
    if not isinstance(value, str):
        return ""
    words = [w.strip(".,;:()'\"") for w in value.strip().lower().split()]
    words = [w for w in words if w]
    if words and words[0] == "all":
        words = words[1:]
    return words[0] if words else ""


def _how_it_reads(value: Any, changed: frozenset[str], unchanged: frozenset[str]) -> str:
    """One declared value read against one field's vocabulary.

    :data:`_DECLARED_CHANGED`, :data:`_DECLARED_UNCHANGED` or
    :data:`_DECLARED_UNREADABLE`.  The same rule serves ``citations``, where
    *changed* means removed, and ``identifiers``, where it means generalised.
    """
    word = declared_word(value)
    if word in changed:
        return _DECLARED_CHANGED
    if word in unchanged:
        return _DECLARED_UNCHANGED
    return _DECLARED_UNREADABLE


def _citation_markers_measured(register: Mapping[str, Any]) -> tuple[int | None, str]:
    """The measured citation-marker total, and the line that reports it.

    ``None`` when the register's derived half carries no count block: the
    capability was not measured, and nothing may be concluded from silence.
    """
    derived = register.get("derived")
    counts = derived.get(_CITATION_COUNT_BLOCK) if isinstance(derived, Mapping) else None
    if not isinstance(counts, Mapping) or not counts:
        return None, f"derived.{_CITATION_COUNT_BLOCK} is absent; the markers were not measured"
    numbers = [v for v in counts.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(numbers) != len(counts):
        return None, f"derived.{_CITATION_COUNT_BLOCK} carries a non-numeric count; not measured"
    total = int(sum(numbers))
    detail = ", ".join(f"{k} {counts[k]}" for k in sorted(counts))
    return total, f"derived.{_CITATION_COUNT_BLOCK} measures {total} marker(s): {detail}"


def _portable(path: Path, repo_root: Path | str) -> str:
    """*path* as the repo-relative POSIX path when it lies under the root.

    A record read from inside the repository is named the way every other
    harness artifact names one, so a basis line stays portable between
    machines.  ``blind_baseline`` and the module command each hold a private
    helper of this shape; the harness has no paths module to share one through,
    and a public one here would be a third name for the same two lines.
    """
    try:
        return Path(path).resolve().relative_to(Path(repo_root).resolve()).as_posix()
    except (ValueError, OSError):
        return Path(path).as_posix()


def _read_json(path: Path, what: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise CandidateProvenanceError(f"{what} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CandidateProvenanceError(f"{what} {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping):
        raise CandidateProvenanceError(f"{what} {path} is not a JSON object.")
    return data


# --------------------------------------------------------------------------- #
# Finding the manifest
# --------------------------------------------------------------------------- #


def find_import_manifest(
    graph_root: Path | str,
    *,
    node_id: str = "",
    document_id: str = "",
) -> Path | None:
    """The import manifest describing *node_id*, or the one of *document_id*.

    Every manifest under the graph root's imports directory is read and matched
    on ``document.node_id`` first, because one document has one manifest per
    revision and only the node id names a revision.  A match on
    ``document.document_id`` is the fallback for a caller holding no node id;
    with more than one revision's manifest present that is ambiguous, so
    ``None`` is returned rather than a guess.  Returns ``None`` when the
    directory is absent or nothing matches.
    """
    directory = Path(graph_root) / IMPORT_MANIFESTS_REL
    if not directory.is_dir():
        return None
    by_node: dict[str, Path] = {}
    by_document: dict[str, list[Path]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            data = _read_json(path, "import manifest")
        except CandidateProvenanceError:
            continue
        document = data.get("document")
        if not isinstance(document, Mapping):
            continue
        node = str(document.get("node_id") or "")
        doc = str(document.get("document_id") or "")
        if node:
            by_node[node] = path
        if doc:
            by_document.setdefault(doc, []).append(path)
    if node_id and node_id in by_node:
        return by_node[node_id]
    if document_id:
        candidates = by_document.get(document_id) or []
        if len(candidates) == 1:
            return candidates[0]
    return None


# --------------------------------------------------------------------------- #
# The derivation
# --------------------------------------------------------------------------- #


def provenance_from_manifest(
    manifest_path: Path | str, *, repo_root: Path | str
) -> CandidateProvenance:
    """Derive one candidate's provenance from its import manifest and register.

    Fail-closed on a named record that cannot be read: a manifest or register
    the caller names and the file system does not hold raises
    :class:`CandidateProvenanceError`, because deriving wording from a record
    that was not read would be the fabricated completion CLAUDE.md §15 forbids.
    A record that is readable but states nothing recognisable yields
    :data:`CAUSE_UNSTATED` with the gap flagged.
    """
    manifest = Path(manifest_path)
    data = _read_json(manifest, "import manifest")
    sources: list[str] = [_portable(manifest, repo_root)]
    basis: list[str] = []
    flags: list[str] = []

    claims = data.get("claims")
    declared_ledger = claims.get("declared_status") if isinstance(claims, Mapping) else None
    expected: str | None = None
    if isinstance(declared_ledger, str) and declared_ledger.strip():
        expected = declared_ledger.strip().lower()
        basis.append(f"the manifest declares its claim ledger carries status {expected!r}")
    else:
        flags.append(
            f"import manifest {sources[0]} declares no claims.declared_status; the audit "
            "has no declared ledger contract to check an entry against"
        )

    candidate = data.get("candidate")
    register_rel = candidate.get("fidelity_register") if isinstance(candidate, Mapping) else None
    if not isinstance(register_rel, str) or not register_rel.strip():
        flags.append(
            f"import manifest {sources[0]} names no candidate.fidelity_register; the "
            "grounding cause and the identity scope rest on no record"
        )
        return _unstated(
            basis=tuple(basis + ["no fidelity register was named"]),
            flags=tuple(flags),
            sources=tuple(sources),
        )

    register_path = Path(repo_root) / register_rel
    register = _read_json(register_path, "fidelity register")
    sources.append(register_rel)

    provenance = register.get("provenance")
    provenance = provenance if isinstance(provenance, Mapping) else {}
    transformation = provenance.get("transformation")
    transformation = transformation if isinstance(transformation, Mapping) else {}
    artifact = provenance.get("current_assessment_artifact")
    artifact = artifact if isinstance(artifact, Mapping) else {}

    submitted = artifact.get("is_submitted_document")
    submitted = submitted if isinstance(submitted, bool) else None
    if submitted is None:
        flags.append(
            f"fidelity register {register_rel} declares no "
            "provenance.current_assessment_artifact.is_submitted_document"
        )
    else:
        basis.append(f"the register declares is_submitted_document {submitted}")

    # --- the grounding cause -------------------------------------------------
    citations_raw = transformation.get("citations")
    citations = _how_it_reads(citations_raw, CITATIONS_REMOVED_WORDS, CITATIONS_PRESENT_WORDS)
    measured, measured_line = _citation_markers_measured(register)
    basis.append(measured_line)
    if citations == _DECLARED_UNREADABLE:
        basis.append(
            f"the register's declared citations value {citations_raw!r} is in no recognised "
            "vocabulary and is read as neither removed nor present"
        )
    else:
        read_as = "removed" if citations == _DECLARED_CHANGED else "present"
        basis.append(f"the register declares citations {citations_raw!r}, read as {read_as}")

    cause = CAUSE_UNSTATED
    if measured is not None and measured > 0:
        cause = CAUSE_SOURCES_PRESENT
        if citations == _DECLARED_CHANGED:
            flags.append(
                f"fidelity register {register_rel} declares the citations removed and the "
                f"importer measured {measured} marker(s); the measurement governs and the "
                "grounding cause is that sources are present"
            )
    elif measured == 0 and citations == _DECLARED_CHANGED and submitted is False:
        cause = CAUSE_SANITISATION
    elif measured == 0 and citations == _DECLARED_UNCHANGED:
        flags.append(
            f"fidelity register {register_rel} declares the citations present and the importer "
            "measured none; the cause of the missing corroboration is Unresolved"
        )
    elif measured == 0 and citations == _DECLARED_CHANGED and submitted is not False:
        flags.append(
            f"fidelity register {register_rel} declares the citations removed but does not "
            "declare the candidate a derivative; sanitisation is not named on that basis"
        )
    else:
        flags.append(
            f"fidelity register {register_rel} states no cause for the missing corroboration; "
            "the grounding reason is Unresolved"
        )

    # --- the identity scope --------------------------------------------------
    identifiers_raw = transformation.get("identifiers")
    identifiers = _how_it_reads(
        identifiers_raw, IDENTIFIERS_GENERALISED_WORDS, IDENTIFIERS_AS_SUBMITTED_WORDS
    )
    if identifiers == _DECLARED_CHANGED:
        scope = IDENTITY_GENERALISED
        basis.append(f"the register declares identifiers {identifiers_raw!r}, read as generalised")
    elif identifiers == _DECLARED_UNCHANGED:
        scope = IDENTITY_AS_SUBMITTED
        basis.append(
            f"the register declares identifiers {identifiers_raw!r}, read as the submitted "
            "document's own; the host line and the recruitment table are comparable"
        )
    else:
        scope = IDENTITY_UNSTATED
        flags.append(
            f"fidelity register {register_rel} declares identifiers {identifiers_raw!r}, which is "
            "in no recognised vocabulary; the identity scope is Unresolved"
        )

    return CandidateProvenance(
        grounding_cause=cause,
        identity_scope=scope,
        expected_ledger_status=expected,
        is_submitted_document=submitted,
        sources=tuple(sources),
        basis=tuple(basis),
        flags=tuple(flags),
    )


def resolve_provenance(
    *,
    repo_root: Path | str,
    manifest_path: Path | str | None = None,
    graph_root: Path | str | None = None,
    node_id: str = "",
    document_id: str = "",
) -> CandidateProvenance:
    """The provenance of the candidate a caller can name, or an unstated one.

    *manifest_path* is read when given, and a path that does not resolve is a
    refusal, not a fallback.  Otherwise the graph root's imports directory is
    searched for the manifest of *node_id* (or of *document_id* when only one
    revision's manifest is present).  Nothing found: :data:`UNSTATED_PROVENANCE`
    with a flag saying no record was read, so the run says what it does not
    know instead of borrowing a reason.
    """
    if manifest_path is not None:
        return provenance_from_manifest(manifest_path, repo_root=repo_root)
    found = None
    if graph_root is not None:
        found = find_import_manifest(graph_root, node_id=node_id, document_id=document_id)
    if found is not None:
        return provenance_from_manifest(found, repo_root=repo_root)
    named = node_id or document_id or "this candidate"
    return _unstated(
        basis=("no provenance record was resolved for this candidate",),
        flags=(
            f"no import manifest was found for {named}; the grounding reason and the identity "
            "wording state that the cause is Unresolved, and neither is derived from a record",
        ),
    )
