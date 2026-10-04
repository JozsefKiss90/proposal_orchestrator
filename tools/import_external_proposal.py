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
    page_accounting,
    parse_row,
    split_sentences,
    versions,
)
from runner.paths import find_repo_root
from runner.source_index import PAGE_TEXT_METHOD, SOURCE_INDEX_RECORD_TYPE
from tools import author_msca_dn_workspace as ws

# --------------------------------------------------------------------------- #
# Constants: the spec's names
# --------------------------------------------------------------------------- #

SPEC_REL = ws.SPEC_REL
WORKSPACE_REL = ws.WORKSPACE_REL
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


@lru_cache(maxsize=2)
def _extract(pdf: str, sha256: str) -> tuple[PageExtract, ...]:
    return extract_document(Path(pdf))


def extract(repo_root: Path) -> tuple[PageExtract, ...]:
    pdf = repo_root / CANDIDATE_PDF_REL
    if not pdf.is_file():
        raise ImportRefused(f"candidate missing: {CANDIDATE_PDF_REL.as_posix()}")
    pages = _extract(str(pdf), _sha256(pdf))
    if len(pages) != EXPECTED_PAGES:
        raise ImportRefused(f"candidate: expected {EXPECTED_PAGES} pages, found {len(pages)}")
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
    subs: Sequence[SubSection], pages: Sequence[PageExtract]
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
                        span = {"source_id": SOURCE_ID_FORMAT.format(page=page), "start": hit[0], "end": hit[1]}
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


def build_import(repo_root: Path) -> Import:
    pages = extract(repo_root)
    paragraphs = join_segments(pages)
    subs, criterion_content = map_sub_sections(paragraphs)
    title_1_1 = _af_v6_heading(repo_root, "1.1")
    subs = tuple(
        SubSection(s.spec, s.heading, title_1_1, s.paragraphs, s.start_page, s.end_page)
        if s.spec.sub_section_id == "1.1" and s.spec.declared_title is None else s
        for s in subs
    )
    claims, stats = extract_claims(subs, pages)
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
        candidate, "tools/import_external_proposal.py candidate", schema_id=DOCUMENT_SCHEMA_ID_V2
    )
    return Import(pages, subs, criterion_content, candidate, stats, record, record_rel)


# --------------------------------------------------------------------------- #
# Rendering: sources, manifest, derived half
# --------------------------------------------------------------------------- #


def _pages_of(sub: SubSection) -> set[int]:
    return {pg for p in sub.paragraphs for pg in p.pages}


def render_sources(repo_root: Path, imp: Optional[Import] = None) -> dict[str, Any]:
    imp = imp or build_import(repo_root)
    sha = _sha256(repo_root / CANDIDATE_PDF_REL)
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
                "source_id": SOURCE_ID_FORMAT.format(page=p.page),
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
                    "stored_path": CANDIDATE_PDF_REL.as_posix(),
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
            "the sanitised copy, each holding that page's extracted text, so a verified_span resolves "
            "to a page and an offset (spec §6). Written by PE-03."
        ),
        "spec": SPEC_REL,
        "written_by": "tools/import_external_proposal.py",
        "candidate": {"path": CANDIDATE_PDF_REL.as_posix(), "sha256": sha, "pages": len(imp.pages)},
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


def derive_register_half(repo_root: Path) -> dict[str, Any]:
    """The fidelity register's ``derived`` half (spec decision 9), from the PDF alone."""
    imp = build_import(repo_root)
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
        "candidate_sha256": _sha256(repo_root / CANDIDATE_PDF_REL),
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
        "import_manifest": (WORKSPACE_REL / IMPORTS_REL / f"{imp.candidate['document_id']}.json").as_posix(),
    }


def render_manifest(repo_root: Path, imp: Optional[Import] = None) -> dict[str, Any]:
    imp = imp or build_import(repo_root)
    sources_bytes = canonical_json_bytes(render_sources(repo_root, imp))
    doc_id = imp.candidate["document_id"]
    return {
        "record_type": MANIFEST_RECORD_TYPE,
        "schema_ref": _SCHEMA_REF,
        "spec": SPEC_REL,
        "ticket": "PE-03",
        "tool": "tools/import_external_proposal.py",
        "candidate": {
            "path": CANDIDATE_PDF_REL.as_posix(),
            "sha256": _sha256(repo_root / CANDIDATE_PDF_REL),
            "pages": len(imp.pages),
            "is_submitted_document": False,
            "fidelity_register": REGISTER_REL.as_posix(),
        },
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
            "source_id_format": SOURCE_ID_FORMAT,
            "sha256": hashlib.sha256(sources_bytes).hexdigest(),
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
        "fidelity_register_derived_half": f"{REGISTER_REL.as_posix()}#derived",
    }


# --------------------------------------------------------------------------- #
# Writing and checking
# --------------------------------------------------------------------------- #


def render_all(repo_root: Path) -> dict[str, bytes]:
    """Every file PE-03 authors, as the bytes it should hold on disk."""
    imp = build_import(repo_root)
    doc_id = imp.candidate["document_id"]
    return {
        (WORKSPACE_REL / SOURCES_REL).as_posix(): canonical_json_bytes(render_sources(repo_root, imp)),
        (WORKSPACE_REL / imp.record_rel).as_posix(): canonical_json_bytes(imp.record),
        (WORKSPACE_REL / IMPORTS_REL / f"{doc_id}.json").as_posix(): canonical_json_bytes(render_manifest(repo_root, imp)),
        REGISTER_REL.as_posix(): canonical_json_bytes(ws.render_register(repo_root)),
    }


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent."""
    return [
        rel
        for rel, data in render_all(repo_root).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


def author(repo_root: Path) -> list[str]:
    """Write every file; return the relative paths that changed."""
    imp = build_import(repo_root)
    changed: list[str] = []
    record_rel = (WORKSPACE_REL / imp.record_rel).as_posix()
    for rel, data in render_all(repo_root).items():
        target = repo_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        if rel == record_rel:
            # The engine's writer owns immutability: a changed record is a new version.
            import_candidate(
                repo_root / WORKSPACE_REL,
                imp.candidate,
                where="tools/import_external_proposal.py candidate",
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
    except (ImportRefused, DevGraphError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
