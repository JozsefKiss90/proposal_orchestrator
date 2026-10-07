"""Import the sanitised MSCA-DN Part B into the pre-evaluation graph root (PE-03).

Ticket PE-03 of ``plans/msca_dn_pre_evaluation_spec.md``: external proposal
import. Seven things, all derived from the stored PDF and the constants below,
so that the import replays byte-equal and nothing is typed where it could be
derived:

1. Extract text per page (:mod:`runner.external_proposal`).
2. Write the 84 page sources, ``SRC-DN-P01`` to ``SRC-DN-P84``, each holding
   that page's text under the source index's replay contract, so a
   ``verified_span`` resolves to a page and an offset (spec §6).
3. Map sections and sub-sections per spec §4.1 and §4.2: three section
   artifacts, fifteen sub-sections anchored ``1.1`` to ``3.2`` and ``4`` to
   ``8``. The heading of each numbered sub-section is the text block that
   starts with its marker on its declared page; ``1.1`` and ``8`` are
   unlabelled in the copy and carry declared titles.
4. Render the tables per decision 8: one pipe-delimited row per table row,
   one paragraph per row, so every row is independently selectable and the
   budget filler never splits one.
5. Extract the audit claim ledger: every sentence of the prose the closed
   claim rule selects, frozen here as ``unconfirmed`` (Unresolved by the
   lookup), with a span locating it in its page source. These are the
   proposal's own assertions with no external source, so none may declare
   ``source_grounded``, which is why the v2 tightening does not bite.
6. Emit a v2 document record through :func:`runner.dev_graph.import_candidate`.
7. Write the fidelity register's derived half: extraction losses per page,
   the figure count, the dependency keyword counts, the table render results
   and the body point-size distribution (spec decision 9).

Plus an import manifest under the workspace's ``dev_graph/imports/`` carrying
the extractor, normalisation, table-rendering and claim-extraction versions
(spec PE-05: a hash of an output cannot name the process that produced it).

What is declared and what is derived
------------------------------------
Declared: the §4.1 page map, the heading markers, the two titles of the
unlabelled sub-sections, the §4.2 grouping, the document title. Derived:
every text, every count, every offset, every hash, the heading texts, the
start page of each sub-section, and the one place the derived start page
differs from the declared one (``8`` begins on the last line of p. 75).

Ownership
---------
``tools/author_msca_dn_workspace.py`` (PE-01) owns the workspace skeleton,
the intake and the register's provenance header. This tool owns the source
index, the document record, the manifest and the register's derived half;
the workspace tool renders the register through :func:`derive_register_half`
so the two never disagree on its bytes.

The register's ``declared`` half is the operator's, and neither tool authors
it. Both read it from the revision's declaration input and carry its rows
through unchanged, so a declaration survives this tool's rewrite of the
register (:mod:`tools.fidelity_declarations`, R01).

Run it from the repository root::

    py -3.10 -m tools.import_external_proposal            # write
    py -3.10 -m tools.import_external_proposal --check    # exit 1 if any file would change

Constitutional standing: an authoring tool, not a runtime component. It
writes Tier 3 and Tier 4 artifacts of one workspace, evaluates no gate,
invokes no Claude, and coins no ``schema_id`` beyond the document snapshot's
own (CLAUDE.md §16.3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Sequence

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.dev_graph.builder import SOURCES_REL
from runner.dev_graph.documents import (
    DOCUMENT_SCHEMA_ID_V2,
    document_node_id,
    import_candidate,
    render_record,
)
from runner.dev_graph.intake import read_esr_intake
from runner.dev_graph.schema import DevGraphError
from runner.external_proposal import (
    PageExtract,
    Paragraph,
    claim_rule_matches,
    extract_document,
    is_row,
    join_segments,
    locate,
    nonws_len,
    page_accounting,
    parse_row,
    split_sentences,
    versions,
)
from runner.paths import find_repo_root
from runner.source_index import PAGE_TEXT_METHOD, SOURCE_INDEX_RECORD_TYPE
from tools import author_msca_dn_workspace as ws
from tools.fidelity_declarations import FidelityDeclarationsError, validate_inputs

# --------------------------------------------------------------------------- #
# Constants: the spec's names
# --------------------------------------------------------------------------- #

SPEC_REL = ws.SPEC_REL
WORKSPACE_REL = ws.WORKSPACE_REL
SOURCE_DIR_REL = ws.SOURCE_DIR_REL
CANDIDATE_PDF_REL = ws.CANDIDATE_PDF_REL
REGISTER_REL = ws.REGISTER_REL
INTAKE_ID = ws.INTAKE_ID
SCORECARD_REL = Path("harness/evaluator_scorecard_msca_dn.json")

#: Workspace-relative directory of import manifests, beside ``documents/``.
IMPORTS_REL = Path("docs/tier4_orchestration_state/dev_graph/imports")
MANIFEST_RECORD_TYPE = "external_proposal_import_manifest"

SOURCE_ID_FORMAT = "SRC-DN-P{page:02d}"
DOCUMENT_TITLE = "Sanitised derivative of the MSCA-DN 2025 Part B (PROJECT-X)"
#: The copy's own acronym for the project; the real one stays with the original.
EXPECTED_PAGES = 84


# --------------------------------------------------------------------------- #
# Revisions of the sanitised derivative
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Revision:
    """One revision of the sanitised derivative, and everything that is keyed
    by it.

    A revision is a new sanitised PDF of the same historical submission, so
    every revision shares the ``document_id`` and the intake, and differs in
    its bytes, its page texts and therefore its content version. Nothing is
    shared that a span could resolve through: each revision owns its
    ``source_id_prefix``, so a ``verified_span`` of one revision can never
    resolve into another revision's page text.
    """

    revision_id: str
    pdf_rel: Path
    source_id_prefix: str
    """``SRC-DN`` for the first import; a revision takes its own prefix so the
    earlier spans keep pointing at the earlier page texts."""
    manifest_name: str
    """File name of the import manifest. The first revision keeps the name it
    was committed under; a later one is suffixed."""
    register_rel: Path
    expected_pages: int
    candidate_role: str
    """The fidelity register's input-table ``role`` for this PDF."""
    candidate_version: str
    """The fidelity register's input-table ``version`` for this PDF."""
    supersedes: Optional[str] = None
    """``revision_id`` of the revision this one supersedes, or ``None``."""
    change_id: Optional[str] = None
    """Plain identifier naming the revision in the document provenance."""
    summary: str = ""
    """What this revision is, in one sentence, for the manifest and register."""

    @property
    def source_id_format(self) -> str:
        return self.source_id_prefix + "-P{page:02d}"

    def source_id(self, page: int) -> str:
        return self.source_id_format.format(page=page)


_ORIGINAL_ROLE = (
    "Current assessment artifact: a sanitised derivative of the historical submission, "
    "reflowed from 34 to 84 pages. Not the submitted text."
)

REVISION_ORIGINAL = Revision(
    revision_id="sanitised_v1",
    pdf_rel=SOURCE_DIR_REL / "sanitized_proposal_final.pdf",
    source_id_prefix="SRC-DN",
    manifest_name="MSCA-DN-2025_sanitised_part_b.json",
    register_rel=SOURCE_DIR_REL / "fidelity_register.json",
    expected_pages=84,
    candidate_role=_ORIGINAL_ROLE,
    candidate_version="sanitised derivative, 84 pages (reflow of a 34-page original)",
    summary=(
        "The first sanitised derivative imported at PE-03. Retained unchanged so its "
        "document record, its page texts and every span into them stay reproducible."
    ),
)

REVISION_RESOLVED_FIXES = Revision(
    revision_id="resolved_fixes",
    pdf_rel=SOURCE_DIR_REL / "sanitized_proposal_resolved_fixes.pdf",
    source_id_prefix="SRC-DN-RF",
    manifest_name="MSCA-DN-2025_sanitised_part_b.resolved_fixes.json",
    register_rel=SOURCE_DIR_REL / "fidelity_register_resolved_fixes.json",
    expected_pages=84,
    candidate_role=(
        "Current assessment artifact: a revised sanitised derivative of the same historical "
        "submission, reflowed from 34 to 84 pages. Not the submitted text, and not the first "
        "sanitised derivative either."
    ),
    candidate_version=(
        "revised sanitised derivative, 84 pages (reflow of a 34-page original); supersedes the "
        "first sanitised derivative"
    ),
    supersedes="sanitised_v1",
    change_id="msca-dn-2025-sanitised-resolved-fixes",
    summary=(
        "A revised sanitised derivative of the same submission. The page count, the section "
        "boundaries and 83 of the 84 page texts are unchanged; page 45 was re-typeset."
    ),
)

#: Every revision, oldest first. ``render_all`` writes all of them, so a
#: revision never silently drops the page texts an earlier span resolves into.
REVISIONS: tuple[Revision, ...] = (REVISION_ORIGINAL, REVISION_RESOLVED_FIXES)

#: The revision a new assessment reads: the newest, and the one no other
#: revision supersedes.
ACTIVE_REVISION: Revision = REVISION_RESOLVED_FIXES


def revision_by_id(revision_id: str) -> Revision:
    for rev in REVISIONS:
        if rev.revision_id == revision_id:
            return rev
    raise ImportRefused(
        f"unknown revision {revision_id!r}; known: {[r.revision_id for r in REVISIONS]}"
    )

#: Keyword counts the register's derived half records (spec §2.7), measured
#: case-insensitively over the collapsed text of every page.
DEPENDENCY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("dependenc", r"dependenc"),
    ("interdepend", r"interdepend"),
    ("Gantt", r"gantt"),
    ("critical path", r"critical path"),
    ("in WP<n>", r"\bin WP ?\d"),
    ("build(s/ing) (up)on", r"\bbuild(?:s|ing)? (?:up)?on\b"),
)
#: Citation markers the derived half counts (spec §2.8), all expected zero.
CITATION_MARKERS: tuple[tuple[str, str], ...] = (
    ("bracketed_numbers", r"\[\d+(?:\s*[,–-]\s*\d+)*\]"),
    ("doi", r"\b10\.\d{4,}/"),
    ("url", r"https?://|\bwww\."),
    ("author_year", r"\([A-Z][A-Za-z-]+(?: et al\.)?,? (?:19|20)\d{2}[a-z]?\)"),
)
#: The declared body point size (spec §2.11); every other size is reported with its text.
BODY_POINT_SIZE = "12.0"

_NUMBERING = re.compile(r"^\d+(?:\.\d+)*\.\s+")


@dataclass(frozen=True)
class SubSectionSpec:
    """One sub-section of spec §4.1 and §4.2."""

    sub_section_id: str
    section_id: str
    declared_pages: tuple[int, int]
    """Pages per spec §4.1, declared."""
    marker: Optional[str]
    """The block prefix (``1.2.``) or exact block (``Beneficiary A``) that opens it;
    ``None`` when it opens the document."""
    declared_title: Optional[str] = None
    """A title for an unlabelled sub-section; ``None`` means the heading supplies it."""
    exact_marker: bool = False
    """The marker is the whole block, not a prefix."""


SECTIONS: tuple[tuple[str, str], ...] = (
    ("excellence_section", "Excellence"),
    ("impact_section", "Impact"),
    ("implementation_section", "Quality and Efficiency of the Implementation"),
)

#: The one criterion-level heading the copy carries; it is the section's own
#: content and must be followed immediately by the first sub-section heading.
CRITERION_HEADING_MARKERS: dict[str, tuple[str, int]] = {"implementation_section": ("3.", 41)}

SUB_SECTIONS: tuple[SubSectionSpec, ...] = (
    SubSectionSpec("1.1", "excellence_section", (1, 13), None, declared_title=None),
    SubSectionSpec("1.2", "excellence_section", (14, 21), "1.2."),
    SubSectionSpec("1.3", "excellence_section", (22, 26), "1.3."),
    SubSectionSpec("1.4", "excellence_section", (27, 31), "1.4."),
    SubSectionSpec("2.1", "impact_section", (32, 33), "2.1."),
    SubSectionSpec("2.2", "impact_section", (34, 35), "2.2."),
    SubSectionSpec("2.3", "impact_section", (36, 38), "2.3."),
    SubSectionSpec("2.4", "impact_section", (39, 40), "2.4."),
    SubSectionSpec("3.1", "implementation_section", (41, 64), "3.1."),
    SubSectionSpec("3.2", "implementation_section", (65, 66), "3.2."),
    SubSectionSpec("4", "implementation_section", (67, 67), "4."),
    SubSectionSpec("5", "implementation_section", (68, 72), "5."),
    SubSectionSpec("6", "implementation_section", (73, 74), "6."),
    SubSectionSpec("7", "implementation_section", (74, 75), "7."),
    SubSectionSpec(
        "8", "implementation_section", (76, 84), "Beneficiary A",
        declared_title="Participating Organisations", exact_marker=True,
    ),
)
#: A marker is searched on its declared start page and the page before it:
#: ``8``'s opening block is the last line of p. 75 while §4.1 says 76.
MARKER_PAGE_TOLERANCE = 1

_SCHEMA_REF = (
    "No declared schema. .claude/workflows/system_orchestration/artifact_schema_specification.yaml "
    "carries no schema for an import manifest, and no schema_id is coined for it (CLAUDE.md §16.3). "
    "The shape is fixed by tools/import_external_proposal.py and checked by tests/test_msca_dn_import.py."
)


class ImportRefused(RuntimeError):
    """Refusal: an input is missing or the copy does not have the declared shape."""


# --------------------------------------------------------------------------- #
# Extraction (cached per PDF bytes)
# --------------------------------------------------------------------------- #


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=8)
def _extract(pdf: str, sha256: str) -> tuple[PageExtract, ...]:
    return extract_document(Path(pdf))


def extract(repo_root: Path, revision: Revision = REVISION_ORIGINAL) -> tuple[PageExtract, ...]:
    """Every page of *revision*'s PDF, or refuse.

    The page count is checked against the revision's declared one rather than
    assumed: a revision that reflowed to a different length must be declared,
    not discovered downstream.
    """
    pdf = repo_root / revision.pdf_rel
    if not pdf.is_file():
        raise ImportRefused(
            f"candidate missing for revision {revision.revision_id}: {revision.pdf_rel.as_posix()}"
        )
    pages = _extract(str(pdf), _sha256(pdf))
    if len(pages) != revision.expected_pages:
        raise ImportRefused(
            f"candidate {revision.pdf_rel.as_posix()}: expected {revision.expected_pages} pages, "
            f"found {len(pages)}"
        )
    return pages


# --------------------------------------------------------------------------- #
# Section map
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SubSection:
    spec: SubSectionSpec
    heading: Optional[str]
    """The heading block text, verbatim and collapsed; ``None`` for an unlabelled one."""
    title: str
    paragraphs: tuple[Paragraph, ...]
    start_page: int
    end_page: int

    @property
    def content(self) -> str:
        return "\n\n".join(p.text for p in self.paragraphs)


def _is_marker(p: Paragraph, spec: SubSectionSpec) -> bool:
    if p.kind != "prose" or spec.marker is None:
        return False
    return p.text == spec.marker if spec.exact_marker else p.text.startswith(spec.marker + " ")


def _find_heading(paragraphs: Sequence[Paragraph], spec: SubSectionSpec, start_from: int) -> int:
    lo = spec.declared_pages[0] - MARKER_PAGE_TOLERANCE
    hi = spec.declared_pages[0]
    for i in range(start_from, len(paragraphs)):
        p = paragraphs[i]
        if p.pages[0] > hi:
            break
        if lo <= p.pages[0] <= hi and _is_marker(p, spec):
            return i
    raise ImportRefused(
        f"sub-section {spec.sub_section_id}: no block starting with {spec.marker!r} on pages {lo}-{hi}"
    )


def _title_of(spec: SubSectionSpec, heading: Optional[str]) -> str:
    if spec.declared_title is not None:
        return spec.declared_title
    if heading is None:
        return ""  # 1.1: filled from the AF V6.0 heading by build_import
    return _NUMBERING.sub("", heading, count=1)


def map_sub_sections(paragraphs: Sequence[Paragraph]) -> tuple[tuple[SubSection, ...], dict[str, str]]:
    """Cut the paragraph stream at the headings. Returns the sub-sections and
    the criterion-heading content per section (``{section_id: heading}``)."""
    cuts: list[tuple[SubSectionSpec, int, Optional[str]]] = []
    cursor = 0
    for spec in SUB_SECTIONS:
        if spec.marker is None:
            cuts.append((spec, 0, None))
            continue
        i = _find_heading(paragraphs, spec, cursor)
        heading = None if spec.exact_marker else paragraphs[i].text
        cuts.append((spec, i, heading))
        cursor = i + 1
    criterion_content: dict[str, str] = {}
    out: list[SubSection] = []
    for n, (spec, i, heading) in enumerate(cuts):
        body_start = i if heading is None else i + 1
        end = cuts[n + 1][1] if n + 1 < len(cuts) else len(paragraphs)
        body = list(paragraphs[body_start:end])
        # A criterion-level heading sits at the end of the previous
        # sub-section's range; it belongs to its section, not to that prose.
        nxt = cuts[n + 1][0] if n + 1 < len(cuts) else None
        if nxt is not None and nxt.section_id in CRITERION_HEADING_MARKERS and nxt.section_id != spec.section_id:
            marker, page = CRITERION_HEADING_MARKERS[nxt.section_id]
            if not body or body[-1].kind != "prose" or not body[-1].text.startswith(marker + " ") \
                    or body[-1].pages[0] != page:
                raise ImportRefused(
                    f"section {nxt.section_id}: the criterion heading {marker!r} on p. {page} is not the "
                    f"block immediately before the {nxt.sub_section_id} heading"
                )
            criterion_content[nxt.section_id] = body.pop().text
        if not body:
            raise ImportRefused(f"sub-section {spec.sub_section_id} has no content")
        out.append(
            SubSection(
                spec=spec,
                heading=heading,
                title=_title_of(spec, heading),
                paragraphs=tuple(body),
                start_page=min(p.pages[0] for p in body) if heading is None else paragraphs[i].pages[0],
                end_page=max(p.pages[-1] for p in body),
            )
        )
    return tuple(out), criterion_content


# --------------------------------------------------------------------------- #
# Claims
# --------------------------------------------------------------------------- #


def extract_claims(
    subs: Sequence[SubSection], pages: Sequence[PageExtract], revision: Revision = REVISION_ORIGINAL
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The audit claim ledger: one claim per rule-selected sentence, first
    occurrence of a sentence text wins, each with a span into its page."""
    by_page = {p.page: p.text for p in pages}
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats: dict[str, Any] = {
        "sentences": 0, "duplicates_removed": 0, "without_span": 0, "claims_without_span": [], "rules_matched": {},
    }
    rules: dict[str, int] = {}
    for sub in subs:
        n = 0
        for para in sub.paragraphs:
            if para.kind != "prose":
                continue
            for sentence in split_sentences(para.text):
                stats["sentences"] += 1
                matched = claim_rule_matches(sentence)
                if not matched:
                    continue
                if sentence in seen:
                    stats["duplicates_removed"] += 1
                    continue
                seen.add(sentence)
                n += 1
                for r in matched:
                    rules[r] = rules.get(r, 0) + 1
                span: Optional[dict[str, Any]] = None
                for page in para.pages:
                    hit = locate(by_page[page], sentence)
                    if hit is not None:
                        span = {"source_id": revision.source_id(page), "start": hit[0], "end": hit[1]}
                        break
                claim_id = f"{sub.spec.sub_section_id}-c{n:03d}"
                if span is None:
                    stats["without_span"] += 1
                    stats["claims_without_span"].append(
                        {"claim_id": claim_id, "pages": list(para.pages), "reason": "the sentence straddles a page break and is in no single page source"}
                    )
                claim: dict[str, Any] = {
                    "claim_id": claim_id,
                    "section_id": sub.spec.section_id,
                    "text": sentence,
                    "evidence_strength": "unconfirmed",
                    "approval": "not_applicable",
                }
                if span is not None:
                    claim["verified_span"] = span
                claims.append(claim)
    stats["rules_matched"] = dict(sorted(rules.items()))
    return claims, stats


# --------------------------------------------------------------------------- #
# The import
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Import:
    revision: Revision
    pages: tuple[PageExtract, ...]
    sub_sections: tuple[SubSection, ...]
    criterion_content: dict[str, str]
    candidate: dict[str, Any]
    claims_stats: dict[str, Any]
    record: dict[str, Any]
    record_rel: str
    """Workspace-relative path of the document record."""


def _af_v6_heading(repo_root: Path, anchor: str) -> str:
    sc = json.loads((repo_root / SCORECARD_REL).read_text(encoding="utf-8-sig"))
    for crit in sc["criteria"]:
        for aspect in crit["aspects"]:
            if aspect.get("anchor") == anchor:
                return str(aspect["af_v6_heading"])
    raise ImportRefused(f"{SCORECARD_REL.as_posix()}: no aspect anchored {anchor}")


def _document_id(repo_root: Path) -> str:
    return read_esr_intake(repo_root / WORKSPACE_REL, INTAKE_ID).document_id


def node_id_of(repo_root: Path, revision: Revision) -> str:
    """The dev-graph node id *revision*'s document record has or would have.

    Derived from the revision's own PDF, never typed, so a predecessor
    reference cannot drift from the record it names.
    """
    imp = build_import(repo_root, revision)
    return document_node_id(imp.candidate["document_id"], imp.record["content_version"])


def build_document_provenance(repo_root: Path, revision: Revision) -> Optional[dict[str, Any]]:
    """The provenance *revision*'s record carries, or ``None`` for a first import.

    Uses the engine's own supersession mechanism
    (:func:`runner.dev_graph.revisions.build_provenance`): the predecessor is
    resolved against the built snapshot, so the declared predecessor version
    is the one this build actually holds, and
    :func:`runner.dev_graph.builder.build_snapshot` turns the result into the
    ``supersedes`` edge. A superseded snapshot stops being a current
    candidate, which is what lets the document id keep resolving to exactly
    one version (``harness.blind_assessment.resolve_document``).

    ``change_id`` names the revision. No change record is written for it:
    ``runner.dev_graph.changes.record_change`` accepts only the five Tier 3
    record paths and rebuilds a before/after snapshot pair, so it is neither
    applicable to a replacement source PDF nor replayable inside a byte-equal
    importer. The manifest states this where the id appears.
    """
    if revision.supersedes is None:
        return None
    from runner.dev_graph.builder import build_snapshot
    from runner.dev_graph.revisions import build_provenance

    predecessor = revision_by_id(revision.supersedes)
    previous_node = node_id_of(repo_root, predecessor)
    snapshot = build_snapshot(repo_root / WORKSPACE_REL)
    return build_provenance(
        snapshot,
        supersedes=previous_node,
        change_id=revision.change_id or revision.revision_id,
        evidence=(),
    )


def build_import(
    repo_root: Path, revision: Revision = REVISION_ORIGINAL, *, with_provenance: bool = True
) -> Import:
    """The whole import of *revision*, derived from its PDF.

    *with_provenance* resolves the superseded snapshot against the built graph,
    which needs the source index on disk. The source index is itself rendered
    from an import, so rendering it uses ``with_provenance=False``: provenance
    is not part of the content version and no source record depends on it, so
    the two renderings agree on everything the index carries.
    """
    pages = extract(repo_root, revision)
    paragraphs = join_segments(pages)
    subs, criterion_content = map_sub_sections(paragraphs)
    title_1_1 = _af_v6_heading(repo_root, "1.1")
    subs = tuple(
        SubSection(s.spec, s.heading, title_1_1, s.paragraphs, s.start_page, s.end_page)
        if s.spec.sub_section_id == "1.1" and s.spec.declared_title is None else s
        for s in subs
    )
    claims, stats = extract_claims(subs, pages, revision)
    sections = []
    for section_id, section_title in SECTIONS:
        sections.append(
            {
                "section_id": section_id,
                "title": section_title,
                "content": criterion_content.get(section_id, ""),
                "addresses": [],
                "sub_sections": [
                    {"sub_section_id": s.spec.sub_section_id, "title": s.title, "content": s.content}
                    for s in subs
                    if s.spec.section_id == section_id
                ],
            }
        )
    candidate = {
        "document_id": _document_id(repo_root),
        "title": DOCUMENT_TITLE,
        "sections": sections,
        "claims": claims,
        "commitments": [],
    }
    record, record_rel = render_record(
        candidate,
        "tools/import_external_proposal.py candidate",
        provenance=build_document_provenance(repo_root, revision) if with_provenance else None,
        schema_id=DOCUMENT_SCHEMA_ID_V2,
    )
    return Import(revision, pages, subs, criterion_content, candidate, stats, record, record_rel)


# --------------------------------------------------------------------------- #
# Rendering: sources, manifest, derived half
# --------------------------------------------------------------------------- #


def _pages_of(sub: SubSection) -> set[int]:
    return {pg for p in sub.paragraphs for pg in p.pages}


def render_source_records(repo_root: Path, imp: Import) -> list[dict[str, Any]]:
    """One ``source`` record per page of *imp*'s revision, in page order."""
    revision = imp.revision
    sha = _sha256(repo_root / revision.pdf_rel)
    claims_by_page: dict[int, list[str]] = {}
    for c in imp.candidate["claims"]:
        span = c.get("verified_span")
        if span:
            page = int(span["source_id"][-2:])
            claims_by_page.setdefault(page, []).append(c["claim_id"])
    subs_by_page: dict[int, list[str]] = {}
    for s in imp.sub_sections:
        for pg in sorted(_pages_of(s)):
            subs_by_page.setdefault(pg, []).append(s.spec.sub_section_id)
    sources = []
    for p in imp.pages:
        carries = subs_by_page.get(p.page, [])
        sources.append(
            {
                "source_id": revision.source_id(p.page),
                "title": f"{DOCUMENT_TITLE}, page {p.page} of {len(imp.pages)}",
                "kind": "call_document_page",
                "kind_note": (
                    "runner.source_index's closed transcription vocabulary has two kinds; this is the "
                    "transcribed one. The page belongs to the candidate proposal (Tier 3 source material), "
                    "not to a call document."
                ),
                "status": "Confirmed",
                "what_the_page_carries": (
                    f"sub-section(s) {', '.join(carries)} of the sanitised copy" if carries else "no mapped sub-section"
                ),
                "citation": {
                    "cited_as": f"{DOCUMENT_TITLE}, page {p.page}.",
                    "document_id": imp.candidate["document_id"],
                    "page": p.page,
                },
                "resolves_to": {
                    "class": "stored_document",
                    "stored_path": revision.pdf_rel.as_posix(),
                    "stored_path_relative_to": "the repository root, not this graph root (spec decision 2)",
                    "sha256": sha,
                    "document_id": imp.candidate["document_id"],
                    "page": p.page,
                    "what_it_holds": (
                        f"Page {p.page} of the sanitised derivative stored in this repository. "
                        "Not the submitted text (fidelity register, provenance)."
                    ),
                },
                "transcription": {
                    "state": "transcribed",
                    "method": PAGE_TEXT_METHOD,
                    "replay": (
                        "runner.source_index.read_page_text(stored_path, page); the import test re-runs "
                        "it and compares byte for byte, so this text cannot drift from the stored file."
                    ),
                },
                "text": p.text,
                "relied_on_for": [
                    {
                        "what": (
                            "The prose of the sub-sections this page carries, and the location of each "
                            "claim the ledger extracted from it."
                        ),
                        "claim_refs": claims_by_page.get(p.page, []),
                        "status": "Confirmed",
                    }
                ],
            }
        )
    return sources


def render_sources(repo_root: Path, imps: Optional[Sequence[Import]] = None) -> dict[str, Any]:
    """The graph root's whole source index: every revision's pages, oldest first.

    One file holds every revision because the dev-graph builder reads exactly
    one ``sources.json`` per graph root. Keeping the earlier revision's records
    in it is what lets the earlier document record keep resolving its spans,
    so a superseded candidate stays reproducible rather than becoming a
    dangling reference.
    """
    imps = list(imps if imps is not None else build_imports(repo_root, with_provenance=False))
    sources: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for imp in imps:
        sources.extend(render_source_records(repo_root, imp))
        candidates.append(
            {
                "revision_id": imp.revision.revision_id,
                "path": imp.revision.pdf_rel.as_posix(),
                "sha256": _sha256(repo_root / imp.revision.pdf_rel),
                "pages": len(imp.pages),
                "source_id_format": imp.revision.source_id_format,
                "supersedes_revision": imp.revision.supersedes,
            }
        )
    seen: dict[str, str] = {}
    for src in sources:
        if src["source_id"] in seen:
            raise ImportRefused(
                f"two revisions claim the source id {src['source_id']!r}; a revision needs its own prefix"
            )
        seen[src["source_id"]] = src["resolves_to"]["stored_path"]
    return {
        "record_type": SOURCE_INDEX_RECORD_TYPE,
        "schema_ref": (
            "No declared schema; see docs/tier3_project_instantiation/source_materials/sources.json "
            "for the shape rationale. runner/dev_graph/builder.py asks only for a non-empty source_id "
            "and, if present, a string text."
        ),
        "provenance_class": "derived",
        "artifact_purpose": (
            "The Tier 3 source index of the MSCA-DN pre-evaluation graph root: one source per page of "
            "each revision of the sanitised copy, each holding that page's extracted text, so a "
            "verified_span resolves to a page and an offset (spec §6). Written by PE-03."
        ),
        "spec": SPEC_REL,
        "written_by": "tools/import_external_proposal.py",
        "revision_note": (
            "Every revision keeps its own source-id prefix and its own records. A span written "
            "against an earlier revision therefore resolves into that revision's page text and never "
            "into a later one, which is what keeps a superseded document record reproducible."
        ),
        "candidates": candidates,
        "versions": versions(),
        "sources": sources,
    }


def _table_rows(imp: Import) -> dict[str, Any]:
    per_table = []
    rendered = parsed = cells = 0
    reordered: list[dict[str, Any]] = []
    for p in imp.pages:
        for t in p.tables:
            rows = [p_.text for p_ in join_segments((p,)) if p_.kind == "row" and p_.table == (p.page, t.index)]
            ok = sum(1 for r in rows if is_row(r) and len(parse_row(r)) == t.cols)
            rendered += len(rows)
            parsed += ok
            for r, row in enumerate(t.rows):
                for c, cell in enumerate(row):
                    cells += 1
                    if cell and cell not in p.text:
                        reordered.append({"page": p.page, "index": t.index, "row": r, "col": c, "cell": cell})
            per_table.append(
                {
                    "page": p.page,
                    "index": t.index,
                    "rows": len(rows),
                    "cols": t.cols,
                    "rows_parsed": ok,
                    "header": list(t.rows[0]) if t.rows else [],
                }
            )
    return {
        "strategy": versions()["table_strategy"],
        "count": len(per_table),
        "rows_rendered": rendered,
        "rows_parsed": parsed,
        "every_row_parses": rendered == parsed,
        "cells": cells,
        "cells_not_contiguous_in_page_text": reordered,
        "cells_not_contiguous_note": (
            "A wrapped cell whose lines the page's reading order interleaves with other cells, or whose "
            "glyphs pymupdf orders differently in the cell than on the page. The characters are the same; "
            "the per-page accounting balances. Recorded, not repaired."
        ),
        "per_table": per_table,
    }


def _sub_section_rows(imp: Import) -> list[dict[str, Any]]:
    claims_by_sub: dict[str, int] = {}
    for c in imp.candidate["claims"]:
        sid = c["claim_id"].rsplit("-c", 1)[0]
        claims_by_sub[sid] = claims_by_sub.get(sid, 0) + 1
    rows = []
    for s in imp.sub_sections:
        rows.append(
            {
                "sub_section_id": s.spec.sub_section_id,
                "section_id": s.spec.section_id,
                "declared_pages": list(s.spec.declared_pages),
                "derived_pages": [s.start_page, s.end_page],
                "heading": s.heading,
                "title": s.title,
                "title_source": "declared" if s.spec.declared_title is not None or s.heading is None else "candidate heading",
                "paragraphs": sum(1 for p in s.paragraphs if p.kind == "prose"),
                "table_rows": sum(1 for p in s.paragraphs if p.kind == "row"),
                "characters": len(s.content),
                "claims": claims_by_sub.get(s.spec.sub_section_id, 0),
            }
        )
    return rows


def _discrepancies(imp: Import) -> list[dict[str, Any]]:
    out = []
    for s in imp.sub_sections:
        if s.start_page != s.spec.declared_pages[0]:
            out.append(
                {
                    "sub_section_id": s.spec.sub_section_id,
                    "declared_start_page": s.spec.declared_pages[0],
                    "derived_start_page": s.start_page,
                    "note": "the opening block sits on the page before the declared one",
                }
            )
    return out


def _losses(imp: Import) -> dict[str, Any]:
    acc = [page_accounting(p) for p in imp.pages]
    reordered = _table_rows(imp)["cells_not_contiguous_in_page_text"]
    return {
        "unit": "non-whitespace characters: the only thing the normalisation moves is whitespace",
        "total_page_chars": sum(a["chars"] for a in acc),
        "total_accounted": sum(a["accounted"] for a in acc),
        "pages_with_loss": [a for a in acc if a["loss"] != 0],
        "character_order_losses": {
            "cells": len(reordered),
            "where": [{k: v for k, v in c.items() if k != "cell"} for c in reordered],
            "note": (
                "Cells whose characters are all present but not in the page's reading order; the integrity "
                "audit reads these rows and must treat their text as unordered. Listed in full under tables."
            ),
        },
    }


def _keyword_counts(imp: Import) -> dict[str, int]:
    joined = " ".join(p.text for p in imp.pages)
    return {name: len(re.findall(pattern, joined, flags=re.IGNORECASE)) for name, pattern in DEPENDENCY_KEYWORDS}


def _citation_counts(imp: Import) -> dict[str, int]:
    joined = " ".join(p.text for p in imp.pages)
    return {name: len(re.findall(pattern, joined)) for name, pattern in CITATION_MARKERS}


def _point_sizes(imp: Import) -> dict[str, Any]:
    dist: dict[str, int] = {}
    other_text: dict[str, set[str]] = {}
    for p in imp.pages:
        for size, n in p.chars_by_point_size.items():
            dist[size] = dist.get(size, 0) + n
        for size, text in p.text_by_point_size.items():
            if size != BODY_POINT_SIZE:
                other_text.setdefault(size, set()).update(text)
    return {
        "body_point_size": BODY_POINT_SIZE,
        "distribution": dict(sorted(dist.items(), key=lambda kv: -kv[1])),
        "other_sizes_character_sets": {k: "".join(sorted(v)) for k, v in sorted(other_text.items())},
        "other_sizes_are_bullets_and_spaces_only": all(v <= {"•", " "} for v in other_text.values()),
    }


def derive_register_half(repo_root: Path, revision: Revision = REVISION_ORIGINAL) -> dict[str, Any]:
    """The fidelity register's ``derived`` half (spec decision 9), from the PDF alone."""
    imp = build_import(repo_root, revision)
    labels = ("WP Number:", "WP title:", "Lead participant")
    label_counts = {
        label: sum(1 for s in imp.sub_sections for p in s.paragraphs if p.kind == "prose" and p.text.startswith(label))
        for label in labels
    }
    wp_blocks = label_counts["WP Number:"]
    return {
        "kind": "derived",
        "status": "written",
        "written_by": "PE-03, tools/import_external_proposal.py",
        "declared_status": "Confirmed",
        "basis": (
            "Derived from the stored PDF bytes by the importer under the versions below and re-derived "
            "by tests/test_msca_dn_import.py. A declaration in the provenance header is not changed by "
            "a measurement here; where the two differ the difference is recorded, not resolved."
        ),
        "candidate_sha256": _sha256(repo_root / revision.pdf_rel),
        "pages": len(imp.pages),
        "versions": versions(),
        "figures": {
            "images_on_any_page": sum(p.images for p in imp.pages),
            "pages_with_images": [p.page for p in imp.pages if p.images],
        },
        "dependency_keyword_counts": _keyword_counts(imp),
        "citation_marker_counts": _citation_counts(imp),
        "tables": _table_rows(imp),
        "table_3_1a": {
            "flattened_to_label_value_blocks": all(n > 0 for n in label_counts.values()),
            "wp_number_blocks": wp_blocks,
            "label_block_counts": label_counts,
            "basis": (
                "derived: the flattening holds when each of the three label-value lines the provenance header "
                "names opens at least one prose block inside sub-section 3.1; the counts are recorded as "
                "measured and may differ (one work package carries no 'Lead participant' line in the copy)"
            ),
        },
        "body_point_size": _point_sizes(imp),
        "per_page_extraction_losses": _losses(imp),
        "sub_sections": _sub_section_rows(imp),
        "page_map_discrepancies": _discrepancies(imp),
        "import_manifest": manifest_rel(revision).as_posix(),
    }


def _page_comparison(repo_root: Path, imp: Import, predecessor: Revision) -> dict[str, Any]:
    """Per-page comparison of *imp*'s page texts against *predecessor*'s.

    Derived, never declared: what a revision changed is measured by comparing
    the two extractions page by page under the same normalisation.
    """
    before = extract(repo_root, predecessor)
    after = imp.pages
    rows: list[dict[str, Any]] = []
    for b, a in zip(before, after):
        if b.text == a.text:
            continue
        rows.append(
            {
                "page": a.page,
                "chars_before": len(b.text),
                "chars_after": len(a.text),
                "nonws_before": nonws_len(b.text),
                "nonws_after": nonws_len(a.text),
                "blocks_before": len(b.blocks),
                "blocks_after": len(a.blocks),
                "tables_before": len(b.tables),
                "tables_after": len(a.tables),
            }
        )
    charset_before = {c for pg in before for c in pg.text if ord(c) > 127}
    charset_after = {c for pg in after for c in pg.text if ord(c) > 127}
    return {
        "compared_with_revision": predecessor.revision_id,
        "compared_with_path": predecessor.pdf_rel.as_posix(),
        "compared_with_sha256": _sha256(repo_root / predecessor.pdf_rel),
        "pages_before": len(before),
        "pages_after": len(after),
        "pages_identical": sum(1 for b, a in zip(before, after) if b.text == a.text),
        "pages_changed": [r["page"] for r in rows],
        "changed_pages": rows,
        "characters_gained": "".join(sorted(charset_after - charset_before)),
        "characters_lost": "".join(sorted(charset_before - charset_after)),
        "basis": (
            "derived: both PDFs are extracted through runner.external_proposal under the versions "
            "this manifest records, and the page texts are compared as strings. A page counted "
            "identical is byte-equal after whitespace normalisation."
        ),
    }


#: Typographic ligatures a PDF may carry as one code point. A plain-text search
#: for the unligatured spelling misses them, so their presence is recorded.
LIGATURES: str = "ﬀﬁﬂﬃﬄﬅﬆ"

#: The label-value lines Table 3.1 a was flattened to. A reader that splits a
#: work package into fields expects each of these to open its own prose block.
WP_HEADER_LABELS: tuple[str, ...] = (
    "WP Number:", "WP title:", "Start month", "Lead participant", "Participants", "DCs involved",
)
_WP_NUMBER = re.compile(r"^WP Number:\s*(\d+)(?!\d)")


def _work_package_header_blocks(imp: Import) -> dict[str, Any]:
    """Which work-package headers survived the flattening as separate blocks.

    A header whose labels all ran into the ``WP Number:`` block is still
    present as text, but a reader that splits a work package by its labels
    cannot see its fields. Measured, because a revision can break this without
    changing a single word.
    """
    sub = next(
        (s for s in imp.sub_sections if s.spec.sub_section_id == "3.1"), None
    )
    blocks = [] if sub is None else [p.text for p in sub.paragraphs if p.kind == "prose"]
    collapsed: list[dict[str, Any]] = []
    numbers: list[int] = []
    for text in blocks:
        m = _WP_NUMBER.match(text)
        if m is None:
            continue
        numbers.append(int(m.group(1)))
        inline = [lab for lab in WP_HEADER_LABELS if lab != "WP Number:" and lab in text]
        if inline:
            collapsed.append(
                {"work_package": int(m.group(1)), "labels_run_into_the_block": inline}
            )
    return {
        "wp_number_blocks": sorted(numbers),
        "headers_collapsed_into_one_block": collapsed,
        "label_blocks": {
            lab: sum(1 for t in blocks if t.startswith(lab)) for lab in WP_HEADER_LABELS
        },
        "consequence": (
            "A work package whose labels ran into its 'WP Number:' block has no separate "
            "'WP title:', 'Lead participant', 'Participants' or 'DCs involved' block. The text is "
            "all there; a reader that splits a work package by its label blocks alone does not see "
            "that work package's fields and may report it as undescribed."
        ),
        "read_by": (
            "The integrity audit (PE-07) reads both layouts: harness/integrity_audit."
            "split_header_fields treats a header field as '<label> <value>' and looks for each "
            "label only after the label before it, in the order the application form fixes, so a "
            "collapsed header yields the same fields as one paragraph per label and keeps the "
            "paragraph it was read from as its location. Any other reader that splits on label "
            "blocks alone is still subject to the consequence above."
        ),
    }


def extraction_limitations(repo_root: Path, revision: Revision) -> dict[str, Any]:
    """What a reader of this revision's text must not assume. All measured.

    Every entry is derived from the extraction, so a limitation cannot be
    declared away and cannot be forgotten when a revision changes the copy.
    """
    imp = build_import(repo_root, revision)
    pages = imp.pages
    ligature_pages: dict[str, list[int]] = {}
    ligature_counts: dict[str, int] = {}
    for page in pages:
        for ch in LIGATURES:
            n = page.text.count(ch)
            if n:
                ligature_counts[ch] = ligature_counts.get(ch, 0) + n
                ligature_pages.setdefault(ch, []).append(page.page)
    sizes = _point_sizes(imp)
    off_body_prose = {
        size: {"characters": sizes["distribution"][size], "character_set": chars}
        for size, chars in sizes["other_sizes_character_sets"].items()
        if set(chars) - {"•", " "}
    }
    losses = _losses(imp)
    return {
        "basis": (
            "derived: measured from this revision's extraction by "
            "tools/import_external_proposal.extraction_limitations, and re-derived by "
            "tests/test_msca_dn_import.py. Recorded, never repaired."
        ),
        "ligatures": {
            "present": sorted(ligature_counts),
            "counts": {ch: ligature_counts[ch] for ch in sorted(ligature_counts)},
            "pages": {ch: sorted(set(ligature_pages[ch])) for ch in sorted(ligature_pages)},
            "consequence": (
                "A ligature is one code point. A search for the unligatured spelling "
                "('Beneficiary') does not match the ligatured one ('Benefi' + U+FB01), so a reader "
                "matching names or labels over this text must fold ligatures first."
            ),
            "read_by": (
                "The integrity audit (PE-07) folds them: harness/integrity_audit.fold_ligatures "
                "supplies the comparison form and harness.integrity_audit.Folded maps a match on "
                "it back to the candidate's own text, so a ligature changes what matches and never "
                "what a finding quotes. Any other reader of this text must fold them itself."
            ),
        },
        "prose_below_the_body_point_size": {
            "body_point_size": sizes["body_point_size"],
            "sizes_carrying_more_than_bullets": off_body_prose,
            "consequence": (
                "Text set smaller than the declared body size is prose, not decoration. No "
                "page-based judgment of length or density was admissible from this file already "
                "(spec §2.11); this is a second reason."
            ),
        },
        "table_cells_not_in_page_reading_order": {
            "cells": losses["character_order_losses"]["cells"],
            "where": losses["character_order_losses"]["where"],
            "consequence": (
                "Every character is present and the per-page accounting balances, but the cell's "
                "text is not a contiguous substring of the page. A span into the page cannot be "
                "derived from such a cell."
            ),
        },
        "claims_without_a_span": {
            "count": imp.claims_stats["without_span"],
            "claims": imp.claims_stats["claims_without_span"],
            "consequence": (
                "A sentence that straddles a page break lives in no single page source, so the "
                "ledger carries it with no verified_span. It is still a claim; it is not locatable."
            ),
        },
        "work_package_header_blocks": _work_package_header_blocks(imp),
        "page_map_discrepancies": _discrepancies(imp),
        "not_the_submitted_text": (
            "This is a sanitised derivative. Figures are absent and citations were removed, so no "
            "judgment of evidence base, length or page-limit compliance is admissible from it."
        ),
    }


def _revision_block(repo_root: Path, imp: Import) -> dict[str, Any]:
    """What this revision is and what it supersedes. Declared and derived, marked."""
    revision = imp.revision
    out: dict[str, Any] = {
        "revision_id": revision.revision_id,
        "summary": revision.summary,
        "source_id_prefix": revision.source_id_prefix,
        "is_submitted_document": False,
        "is_the_first_sanitised_derivative": revision.supersedes is None,
        "all_revisions": [r.revision_id for r in REVISIONS],
    }
    if revision.supersedes is None:
        out["supersedes"] = None
        return out
    predecessor = revision_by_id(revision.supersedes)
    provenance = imp.record.get("provenance") or {}
    out["supersedes"] = {
        "revision_id": predecessor.revision_id,
        "path": predecessor.pdf_rel.as_posix(),
        "sha256": _sha256(repo_root / predecessor.pdf_rel),
        "node_id": (provenance.get("supersedes") or {}).get("id"),
        "node_version": (provenance.get("supersedes") or {}).get("version"),
        "import_manifest": manifest_rel(predecessor).as_posix(),
        "fidelity_register": predecessor.register_rel.as_posix(),
        "mechanism": (
            "runner.dev_graph.revisions.build_provenance wrote the record's provenance and "
            "runner.dev_graph.builder.build_snapshot turns it into the 'supersedes' edge. The "
            "predecessor record, its page texts and its spans are untouched; it stops being a "
            "current candidate and stays readable as history."
        ),
    }
    out["change_id"] = provenance.get("change_id")
    out["change_record"] = {
        "written": False,
        "why": (
            "runner.dev_graph.changes.record_change accepts only the five Tier 3 record paths and "
            "rebuilds a before/after snapshot pair, so it neither covers a replaced source PDF nor "
            "replays byte-equal inside this importer. The change_id names the revision; no change "
            "record stands behind it, and nothing in the build resolves it."
        ),
    }
    out["comparison_with_predecessor"] = _page_comparison(repo_root, imp, predecessor)
    return out


def manifest_rel(revision: Revision) -> Path:
    """Repo-relative path of *revision*'s import manifest."""
    return WORKSPACE_REL / IMPORTS_REL / revision.manifest_name


def render_manifest(
    repo_root: Path, imp: Optional[Import] = None, imps: Optional[Sequence[Import]] = None
) -> dict[str, Any]:
    imp = imp or build_import(repo_root)
    revision = imp.revision
    records = render_source_records(repo_root, imp)
    sources_bytes = canonical_json_bytes(render_sources(repo_root, imps))
    doc_id = imp.candidate["document_id"]
    return {
        "record_type": MANIFEST_RECORD_TYPE,
        "schema_ref": _SCHEMA_REF,
        "spec": SPEC_REL,
        "ticket": "PE-03",
        "tool": "tools/import_external_proposal.py",
        "candidate": {
            "path": revision.pdf_rel.as_posix(),
            "sha256": _sha256(repo_root / revision.pdf_rel),
            "pages": len(imp.pages),
            "is_submitted_document": False,
            "fidelity_register": revision.register_rel.as_posix(),
        },
        "revision": _revision_block(repo_root, imp),
        "versions": versions(),
        "document": {
            "document_id": doc_id,
            "title": imp.candidate["title"],
            "schema_id": imp.record["schema_id"],
            "state": imp.record["state"],
            "record_path": imp.record_rel,
            "content_version": imp.record["content_version"],
            "node_id": document_node_id(doc_id, imp.record["content_version"]),
            "sections": [
                {"section_id": s["section_id"], "sub_sections": [ss["sub_section_id"] for ss in s["sub_sections"]]}
                for s in imp.candidate["sections"]
            ],
        },
        "sources": {
            "path": SOURCES_REL.as_posix(),
            "count": len(imp.pages),
            "source_id_format": revision.source_id_format,
            "sha256": hashlib.sha256(sources_bytes).hexdigest(),
            "sha256_covers": (
                "the whole source index of the graph root, every revision's records included; one "
                "file is what runner/dev_graph/builder.py reads per graph root"
            ),
            "records_sha256": hashlib.sha256(canonical_json_bytes(records)).hexdigest(),
            "records_sha256_covers": "only this revision's own source records, in page order",
            "revisions_in_the_file": [r.revision_id for r in REVISIONS],
        },
        "page_map": {
            "declared_from": f"{SPEC_REL} §4.1",
            "sub_sections": _sub_section_rows(imp),
            "discrepancies": _discrepancies(imp),
        },
        "normalisation": {
            "whitespace": "runs of whitespace collapse to one space; nothing else is rewritten",
            "paragraphs": "one paragraph per pymupdf text block; blank-line blocks dropped",
            "page_crossing": (
                "the last prose block of a page joins the first of the next when it ends without "
                "terminal punctuation and the next starts in lower case, or when it ends with a hyphen"
            ),
            "headings": "the heading block of a numbered sub-section is its title (numbering stripped), not its content",
            "criterion_heading": "the one criterion-level heading ('3.') is its section's own content",
            "tables": "one pipe-delimited paragraph per table row, cells collapsed; a pipe inside a cell is refused",
            "hyphenation": "line-end hyphens are kept as the source carries them",
        },
        "tables": _table_rows(imp),
        "claims": {
            "count": len(imp.candidate["claims"]),
            "rule": (
                "every sentence of the prose that matches a named pattern of "
                "runner.external_proposal.CLAIM_RULES; table rows and headings are not sentences"
            ),
            **imp.claims_stats,
            "evidence_strength": "unconfirmed",
            "declared_status": "Unresolved",
            "approval": "not_applicable",
            "why": (
                "These are the proposal's own assertions. The sanitisation removed every citation "
                "(spec §2.8), so no claim has an external source and none declares source_grounded; "
                "the span locates the assertion in its page source and is not evidence for it. "
                "Nobody in this repository approves a proposal's assertions, so approval is not applicable. "
                "The integrity audit (PE-07) enumerates this ledger and reports each claim Unresolved."
            ),
        },
        "extraction_losses": _losses(imp),
        # This revision's own register, never the first revision's: each revision
        # owns the register whose derived half was measured from its extraction.
        "fidelity_register_derived_half": f"{revision.register_rel.as_posix()}#derived",
    }


# --------------------------------------------------------------------------- #
# Writing and checking
# --------------------------------------------------------------------------- #


def build_imports(repo_root: Path, *, with_provenance: bool = True) -> list[Import]:
    """Every revision's import, oldest first."""
    return [
        build_import(repo_root, revision, with_provenance=with_provenance)
        for revision in REVISIONS
    ]


def render_sources_bytes(repo_root: Path) -> bytes:
    """The source index alone, without resolving any provenance.

    The one artifact an empty graph root can be bootstrapped from: a document
    record's provenance is resolved against the built graph, and the graph
    cannot be built until every span has a source to resolve into.
    """
    return canonical_json_bytes(render_sources(repo_root, build_imports(repo_root, with_provenance=False)))


def render_all(repo_root: Path) -> dict[str, bytes]:
    """Every file PE-03 authors, as the bytes it should hold on disk.

    Every revision is rendered, not only the active one: the source index is
    one file per graph root, and a revision that stopped writing the earlier
    revision's page records would break the earlier record's spans.
    """
    imps = build_imports(repo_root)
    out: dict[str, bytes] = {
        (WORKSPACE_REL / SOURCES_REL).as_posix(): canonical_json_bytes(render_sources(repo_root, imps)),
    }
    for imp in imps:
        out[(WORKSPACE_REL / imp.record_rel).as_posix()] = canonical_json_bytes(imp.record)
        out[manifest_rel(imp.revision).as_posix()] = canonical_json_bytes(
            render_manifest(repo_root, imp, imps)
        )
        out[imp.revision.register_rel.as_posix()] = canonical_json_bytes(
            ws.render_register(repo_root, imp.revision)
        )
    return out


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent.

    Read-only, and it may refuse instead of returning: a malformed declaration
    input or a declaration a register holds alone is a refusal, not a staleness
    entry (:mod:`tools.fidelity_declarations`).
    """
    return [
        rel
        for rel, data in render_all(repo_root).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


def author(repo_root: Path) -> list[str]:
    """Write every file; return the relative paths that changed.

    The source index is written before any document record, because a record
    whose spans name records the file does not yet carry would not build. The
    declaration inputs of every register are read first, so a malformed one is
    refused before the source index is written.
    """
    validate_inputs(repo_root, [(r.revision_id, r.register_rel) for r in REVISIONS])
    changed: list[str] = []
    sources_rel = (WORKSPACE_REL / SOURCES_REL).as_posix()
    # Bootstrap: the source index is written first and without building the
    # graph, because the provenance of every later record is resolved against a
    # graph that cannot be built until the spans have sources to resolve into.
    sources_bytes = render_sources_bytes(repo_root)
    sources_target = repo_root / sources_rel
    if not sources_target.is_file() or sources_target.read_bytes() != sources_bytes:
        atomic_write_text(sources_bytes.decode("utf-8"), sources_target)
        changed.append(sources_rel)
    imps = build_imports(repo_root)
    rendered = render_all(repo_root)
    if rendered[sources_rel] != sources_bytes:  # pragma: no cover - guards the bootstrap
        raise ImportRefused(
            "the source index rendered with and without provenance differ; provenance must not "
            "reach the source index"
        )
    by_record = {(WORKSPACE_REL / imp.record_rel).as_posix(): imp for imp in imps}
    order = [rel for rel in rendered if rel != sources_rel]
    for rel in order:
        data = rendered[rel]
        target = repo_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        imp = by_record.get(rel)
        if imp is not None:
            # The engine's writer owns immutability: a changed record is a new version.
            import_candidate(
                repo_root / WORKSPACE_REL,
                imp.candidate,
                where="tools/import_external_proposal.py candidate",
                provenance=imp.record.get("provenance"),
                schema_id=DOCUMENT_SCHEMA_ID_V2,
            )
        else:
            atomic_write_text(data.decode("utf-8"), target)
        changed.append(rel)
    return changed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if any file would change")
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = args.repo_root or find_repo_root()
    try:
        if args.check:
            stale = check(repo_root)
            for rel in stale:
                print(f"would change: {rel}")
            print("up to date" if not stale else f"{len(stale)} file(s) would change")
            return 1 if stale else 0
        changed = author(repo_root)
        for rel in changed:
            print(f"wrote: {rel}")
        print("no change" if not changed else f"{len(changed)} file(s) written")
        return 0
    except (ImportRefused, DevGraphError, FidelityDeclarationsError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
