"""Measure a PDF before it is imported, and hold the result (V08).

V08 of ``plans/msca_dn_historical_validation_tickets.md``. Extraction
accounting is not semantic fidelity. A balanced character count proves that the
importer dropped no character of the text it could see. It proves nothing about
reading order, cell association, mathematical meaning, image content or figure
completeness, and a deficit on one page can offset a surplus on another inside
an aggregate.

So a document that is going to be assessed gets measured first, by an operator,
against the PDF in front of them. This module is that measurement. It is
deliberately weaker than an import:

* **No page map.** :func:`measure` takes a PDF and nothing else. It reports the
  blocks that *could* open a section — their marker, their page and their text
  — and leaves the map to the operator. An import needs a declared page map;
  a dry import is how one is arrived at.
* **No graph root, no writes.** Nothing here opens a workspace, writes a
  document record, a source index or a snapshot, or returns a path. It returns
  plain JSON-able mappings. The caller decides where, if anywhere, they go.
* **No declared page count.** The count is measured. There is no expected value
  to check it against, because the point of the exercise is to find out.

Three records come out of it (:func:`measure`,
:func:`build_unresolved_limitations`, :func:`build_acceptance`), and one rule is
enforced rather than stated.

Zero is not proof
-----------------
A vector figure is not an embedded image and carries no characters. A Gantt
chart drawn as paths, a diagram drawn as lines, a table drawn as rectangles:
each yields **zero embedded images and zero character loss** while being
graphical evidence an evaluator read. The sanitised derivative of this case
measures both zeros, and in its case the figures really are gone — but the
measurement is not what established that.

So :data:`MEASUREMENT_ONLY_BASES` names the measurements that may not stand
behind a ``preserved`` verdict, and :func:`check_acceptance` reports a finding
when one does. A measurement may support a ``lost`` verdict: an absence can be
measured. Presence has to be looked at.

Constitutional standing: a measurement behind an authoring tool, not a runtime
component. It reads one file, writes none, evaluates no gate and invents no
fact (CLAUDE.md §13.3). Every value it reports is derived from the bytes it
was given, and everything else it reports as undeclared rather than filled
(§12.2, §12.4). It is not a §17.5.3 deterministic component: no manifest node
binds it, no ``AgentResult.invoked_components`` records it, and nothing it
writes is bound by a hash anywhere.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from runner.extraction_environment import (
    PINNED_MUPDF,
    PINNED_PYMUPDF,
    cannot_reproduce_reason,
    measure as measure_environment,
    off_pin_reason,
)
from runner.external_proposal import (
    PageExtract,
    Paragraph,
    extract_document,
    is_row,
    join_segments,
    nonws_len,
    page_accounting,
    parse_row,
    versions,
)

INVENTORY_RECORD_TYPE = "dry_import_inventory"
ACCEPTANCE_RECORD_TYPE = "extraction_fidelity_acceptance"
LIMITATIONS_RECORD_TYPE = "unresolved_extraction_limitations"

#: Typographic ligatures a PDF may carry as one code point. Measured because a
#: plain-text search for the unligatured spelling misses them.
LIGATURES: str = "ﬀﬁﬂﬃﬄﬅﬆ"

#: A block that opens a numbered sub-section: ``1.2.`` or ``3.`` at the start,
#: followed by a space. The marker alone, never the title, because the title is
#: what the operator reads off the page.
_HEADING = re.compile(r"^(\d+(?:\.\d+)*\.)\s+\S")

#: What a page reference buys and what it does not (criterion 5). Carried by the
#: limitations record verbatim, so the statement travels with the record rather
#: than living in a report nobody reads beside it.
SPAN_LOCATES_STATEMENT: str = (
    "A page reference or a source span locates an assertion in the extracted text. It does not "
    "corroborate it. The span says where the sentence sits; it says nothing about whether the "
    "sentence is true, whether the evidence it names exists, or whether a figure the sentence "
    "points at survived extraction."
)

#: Why the two zeros an extraction most readily produces are not preservation
#: (criterion 4).
GRAPHICAL_PROOF_STATEMENT: str = (
    "Zero embedded images and zero character loss are not proof that graphical evidence was "
    "preserved. A Gantt chart, a diagram or a table drawn as vector paths is not an embedded "
    "image and carries no characters, so both counts stay at zero whether the figure is present "
    "or absent. Only a page-by-page comparison against the PDF settles it."
)

#: Measurement bases that may not stand behind a ``preserved`` verdict. Each can
#: be true of a document whose figures are gone and of one whose figures are
#: vector art, so neither discriminates.
MEASUREMENT_ONLY_BASES: frozenset[str] = frozenset(
    {
        "zero_character_loss",
        "zero_embedded_images",
        "character_accounting",
        "extraction_accounting",
        "balanced_page_accounting",
    }
)

#: The verdicts an acceptance item may carry. ``unreconciled`` is the state
#: every item starts in, and the only one that needs no attestation.
ACCEPTANCE_VERDICTS: frozenset[str] = frozenset(
    {"unreconciled", "preserved", "partly_lost", "lost", "not_applicable"}
)

#: Bases that stand on something a measurement cannot supply: an operator who
#: looked at the page, or who declares a fact about the document. These are the
#: only ones a ``preserved`` verdict may rest on.
OPERATOR_BASES: frozenset[str] = frozenset(
    {
        "operator_visual_comparison",
        "operator_page_by_page_check",
        "operator_declaration",
        "not_present_in_this_document",
    }
)

#: Every basis an acceptance item may name. Closed, because free text would let
#: a measurement in under a wording the refusal does not recognise: a verdict
#: of ``preserved`` on the basis of "no characters were lost" is the finding
#: criterion 4 exists to raise, and a set-membership test alone would miss it.
ACCEPTANCE_BASES: frozenset[str] = MEASUREMENT_ONLY_BASES | OPERATOR_BASES


#: The document information fields the metadata census reports, in PDF order.
METADATA_FIELDS: tuple[str, ...] = (
    "title",
    "author",
    "subject",
    "keywords",
    "creator",
    "producer",
    "creationDate",
    "modDate",
    "trapped",
)

#: Why the metadata census counts and does not copy. Carried by the inventory
#: verbatim, so a reader of the counts knows where the values are.
METADATA_WITHHELD_STATEMENT: str = (
    "Metadata values are withheld, and so are their lengths. A document's author and title are "
    "the fields most likely to name a person or a project, and the length of a name is itself a "
    "signal. Whether each field is populated is enough to compare two measurements. The values "
    "stay in the PDF, where a reader who may see them reads them."
)


class DryImportRefused(RuntimeError):
    """Refusal: the input is not a readable file, or a record is malformed."""


# --------------------------------------------------------------------------- #
# The acceptance catalogue (criterion 3)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AcceptanceItem:
    """One class of evidence an operator must reconcile against the PDF."""

    item: str
    what_must_be_reconciled: str
    measurement_is_not_proof: str
    measured_from: tuple[str, ...]
    """Inventory keys whose measurement this item carries, in order. A path of
    one or two keys, so the record quotes what was measured beside what it does
    not settle."""


#: The seven classes V08 criterion 3 names. Each is carried explicitly, because
#: an item a record does not name is an item nobody reconciled.
ACCEPTANCE_ITEMS: tuple[AcceptanceItem, ...] = (
    AcceptanceItem(
        "gantt_chart",
        "Every bar, month label and dependency arrow of the Gantt chart, against the PDF page "
        "it sits on.",
        "A Gantt chart drawn as vector paths is no embedded image and carries no characters. "
        "Its month labels may extract as loose text in no reading order.",
        ("figures",),
    ),
    AcceptanceItem(
        "diagrams",
        "Every diagram: its boxes, its arrows, the direction of each arrow, and any text inside "
        "it that the extraction placed elsewhere on the page.",
        "A diagram's labels can extract as prose and balance the character accounting while the "
        "structure they labelled is gone.",
        ("figures",),
    ),
    AcceptanceItem(
        "embedded_images",
        "Every raster image: that it is present, what it depicts, and whether its caption still "
        "names what the reader sees.",
        "An image count of zero is consistent with a document that never carried a raster image "
        "and with one whose images were stripped.",
        ("figures",),
    ),
    AcceptanceItem(
        "footnotes",
        "Every footnote: its marker, its text, and the sentence it belongs to.",
        "A footnote extracts as prose set below the body size. The character accounting balances "
        "whether or not the footnote stayed attached to its marker.",
        ("point_sizes", "limitations"),
    ),
    AcceptanceItem(
        "table_headers",
        "Every table's header row, and that each data row still associates with the header cell "
        "above it.",
        "A row that parses into the right number of cells can still carry the cells in the wrong "
        "order, and a header flattened into its first cell parses as a row.",
        ("tables",),
    ),
    AcceptanceItem(
        "bibliographic_references",
        "Every citation marker and the reference it resolves to, including a reference list "
        "carried as a figure or a footnote.",
        "A citation-marker count of zero is consistent with a document that cites nothing and "
        "with one whose citations were removed.",
        ("citation_markers",),
    ),
    AcceptanceItem(
        "supporting_part_b_material",
        "Any Part B material outside the prose: an annex, a letter, a table of supervisors, a "
        "secondment plan, a continuation page the page map does not reach.",
        "The inventory measures the pages it was given. A page nobody supplied is not reported "
        "missing, because the measurement has no count to compare against.",
        ("pages", "per_page"),
    ),
)

_ITEM_BY_NAME: dict[str, AcceptanceItem] = {spec.item: spec for spec in ACCEPTANCE_ITEMS}


# --------------------------------------------------------------------------- #
# The graphical census: what the text extraction cannot see
# --------------------------------------------------------------------------- #


def graphical_census(pdf: Path) -> dict[str, Any]:
    """Per-page images, vector drawings, annotations and fonts of *pdf*.

    Read from the PDF directly rather than from a
    :class:`~runner.external_proposal.PageExtract`, because a vector drawing is
    not text and the extraction substrate has no reason to carry it. Keeping it
    here leaves every byte-bound import artifact untouched.
    """
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        rows: list[dict[str, Any]] = []
        fonts: set[str] = set()
        for index in range(doc.page_count):
            page = doc[index]
            fonts.update(str(font[3]) for font in page.get_fonts())
            rows.append(
                {
                    "page": index + 1,
                    "images": len(page.get_images(full=True)),
                    "drawings": len(page.get_drawings()),
                    "annotations": len(list(page.annots())),
                    "links": len(page.get_links()),
                }
            )
        return {
            "per_page": rows,
            "fonts": sorted(fonts),
            "embedded_files": int(doc.embfile_count()),
        }
    finally:
        doc.close()


def metadata_census(pdf: Path) -> dict[str, Any]:
    """Which metadata *pdf* carries: the information fields and the XMP packet.

    Flagged, never copied or measured (:data:`METADATA_WITHHELD_STATEMENT`). A field is
    populated when its value holds a character other than whitespace. Embedded
    files are counted once, by the graphical census.
    """
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        info = doc.metadata or {}
        xmp = doc.get_xml_metadata() or ""
        fields: dict[str, dict[str, Any]] = {}
        for name in METADATA_FIELDS:
            value = str(info.get(name) or "")
            fields[name] = {"populated": bool(value.strip())}
        return {
            "fields": fields,
            "xmp": {"present": bool(xmp.strip())},
            "values_withheld": METADATA_WITHHELD_STATEMENT,
        }
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# Section candidates: the page map the operator has yet to declare
# --------------------------------------------------------------------------- #


def heading_candidates(paragraphs: Sequence[Paragraph]) -> list[dict[str, Any]]:
    """Blocks that could open a numbered sub-section, in document order.

    Reported, not resolved. A numbered block is a candidate heading whatever it
    turns out to be: a declared page map says which candidates are sub-section
    openings, and no page map is declared here.
    """
    out: list[dict[str, Any]] = []
    for para in paragraphs:
        if para.kind != "prose":
            continue
        match = _HEADING.match(para.text)
        if match is None:
            continue
        out.append(
            {
                "marker": match.group(1),
                "page": para.pages[0],
                "pages": list(para.pages),
                "text": para.text,
                "characters": len(para.text),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# The measured blocks
# --------------------------------------------------------------------------- #


def table_inventory(pages: Sequence[PageExtract]) -> dict[str, Any]:
    """Every table, its header row, its shape and whether its rows parse."""
    per_table: list[dict[str, Any]] = []
    rendered = parsed = cells = 0
    not_contiguous: list[dict[str, Any]] = []
    for page in pages:
        for table in page.tables:
            rows = [
                p.text
                for p in join_segments((page,))
                if p.kind == "row" and p.table == (page.page, table.index)
            ]
            ok = sum(1 for row in rows if is_row(row) and len(parse_row(row)) == table.cols)
            rendered += len(rows)
            parsed += ok
            for r, row in enumerate(table.rows):
                for c, cell in enumerate(row):
                    cells += 1
                    if cell and cell not in page.text:
                        not_contiguous.append(
                            {"page": page.page, "index": table.index, "row": r, "col": c}
                        )
            per_table.append(
                {
                    "page": page.page,
                    "index": table.index,
                    "rows": len(rows),
                    "cols": table.cols,
                    "rows_parsed": ok,
                    "header": list(table.rows[0]) if table.rows else [],
                }
            )
    return {
        "strategy": versions()["table_strategy"],
        "count": len(per_table),
        "rows_rendered": rendered,
        "rows_parsed": parsed,
        "every_row_parses": rendered == parsed,
        "cells": cells,
        "cells_not_contiguous_in_page_text": not_contiguous,
        "per_table": per_table,
        "not_proof": (
            "A row that parses into the declared number of cells may still carry the cells in "
            "another order, and a header flattened into its first cell parses as a row. The "
            "header row above is what the operator reconciles."
        ),
    }


def figure_inventory(census: dict[str, Any]) -> dict[str, Any]:
    """The graphical census, with the statement that its zeros prove nothing.

    Takes the census and not the pages: every value here is something the text
    extraction cannot see, which is the whole reason the census exists.
    """
    rows = census["per_page"]
    images = sum(int(r["images"]) for r in rows)
    drawings = sum(int(r["drawings"]) for r in rows)
    return {
        "images_on_any_page": images,
        "pages_with_images": [int(r["page"]) for r in rows if r["images"]],
        "vector_drawings": drawings,
        "pages_with_vector_drawings": [int(r["page"]) for r in rows if r["drawings"]],
        "annotations": sum(int(r["annotations"]) for r in rows),
        "pages_with_annotations": [int(r["page"]) for r in rows if r["annotations"]],
        "links": sum(int(r["links"]) for r in rows),
        "embedded_files": int(census["embedded_files"]),
        "fonts": list(census["fonts"]),
        "zero_images_is_not_absence_of_graphics": True,
        "not_proof_of_preservation": GRAPHICAL_PROOF_STATEMENT,
    }


def point_size_inventory(pages: Sequence[PageExtract]) -> dict[str, Any]:
    """The measured point-size distribution, with no declared body size.

    The importer reports deviation from a declared body size. There is nothing
    declared here, so the largest share is reported as the largest share and
    not as the body size: calling it the body size would be the declaration
    this measurement exists to inform.
    """
    distribution: dict[str, int] = {}
    character_sets: dict[str, set[str]] = {}
    for page in pages:
        for size, n in page.chars_by_point_size.items():
            distribution[size] = distribution.get(size, 0) + n
        for size, text in page.text_by_point_size.items():
            character_sets.setdefault(size, set()).update(text)
    ordered = dict(sorted(distribution.items(), key=lambda kv: (-kv[1], kv[0])))
    largest = next(iter(ordered.items()), None)
    return {
        "body_point_size_declared": None,
        "basis": (
            "derived: every character's point size, counted. The largest share is reported as "
            "the largest share; which size is the body size is a declaration this measurement "
            "informs and does not make."
        ),
        "distribution": ordered,
        "largest_share": (
            None if largest is None else {"size": largest[0], "characters": largest[1]}
        ),
        "character_sets": {
            size: "".join(sorted(chars)) for size, chars in sorted(character_sets.items())
        },
    }


def character_accounting(pages: Sequence[PageExtract]) -> dict[str, Any]:
    """Non-whitespace characters of each page against those its blocks carry."""
    accounting = [page_accounting(page) for page in pages]
    return {
        "unit": "non-whitespace characters: the only thing the normalisation moves is whitespace",
        "total_page_characters": sum(a["chars"] for a in accounting),
        "total_accounted": sum(a["accounted"] for a in accounting),
        "pages_with_loss": [a for a in accounting if a["loss"] != 0],
        "not_proof": (
            "A balanced total means no character of the text the extractor saw was dropped or "
            "duplicated. It says nothing about order, cell association or anything the extractor "
            "did not see, and a deficit on one page can offset a surplus on another."
        ),
    }


def limitation_inventory(
    pages: Sequence[PageExtract], tables: dict[str, Any], sizes: dict[str, Any]
) -> dict[str, Any]:
    """What a reader of this extraction must not assume. All measured."""
    counts: dict[str, int] = {}
    where: dict[str, list[int]] = {}
    for page in pages:
        for ch in LIGATURES:
            n = page.text.count(ch)
            if n:
                counts[ch] = counts.get(ch, 0) + n
                where.setdefault(ch, []).append(page.page)
    largest = (sizes["largest_share"] or {}).get("size")
    below = {
        size: {"characters": sizes["distribution"][size], "character_set": chars}
        for size, chars in sizes["character_sets"].items()
        if largest is not None and size != largest and set(chars) - {"•", " "}
    }
    return {
        "basis": (
            "derived: measured from this PDF's extraction by runner.dry_import. Recorded, never "
            "repaired."
        ),
        "ligatures": {
            "present": sorted(counts),
            "counts": {ch: counts[ch] for ch in sorted(counts)},
            "pages": {ch: sorted(set(where[ch])) for ch in sorted(where)},
            "consequence": (
                "A ligature is one code point. A search for the unligatured spelling does not "
                "match the ligatured one, so a reader matching names or labels over this text "
                "must fold ligatures first."
            ),
        },
        "prose_below_the_largest_point_size": {
            "largest_point_size": largest,
            "sizes": below,
            "consequence": (
                "Text set smaller than the largest size is prose, not decoration. A footnote, a "
                "table note or a figure caption lives here, and a page-based judgment of length "
                "or density does not see it as body text."
            ),
        },
        "table_cells_not_in_page_reading_order": {
            "cells": len(tables["cells_not_contiguous_in_page_text"]),
            "where": list(tables["cells_not_contiguous_in_page_text"]),
            "consequence": (
                "Every character is present and the per-page accounting balances, but the cell's "
                "text is not a contiguous substring of the page. A span into the page cannot be "
                "derived from such a cell."
            ),
        },
    }


def citation_inventory(pages: Sequence[PageExtract]) -> dict[str, Any]:
    """Citation markers, counted. Zero is a count and not an expectation."""
    joined = " ".join(page.text for page in pages)
    patterns = (
        ("bracketed_numbers", r"\[\d+(?:\s*[,–-]\s*\d+)*\]"),
        ("doi", r"\b10\.\d{4,}/"),
        ("url", r"https?://|\bwww\."),
        ("author_year", r"\([A-Z][A-Za-z-]+(?: et al\.)?,? (?:19|20)\d{2}[a-z]?\)"),
    )
    return {
        "counts": {name: len(re.findall(p, joined)) for name, p in patterns},
        "not_proof": (
            "A marker count of zero is consistent with a document that cites nothing and with "
            "one whose citations were removed. A reference list carried as a figure is counted "
            "by neither."
        ),
    }


# --------------------------------------------------------------------------- #
# The inventory
# --------------------------------------------------------------------------- #


def measure(pdf: Path) -> dict[str, Any]:
    """Measure *pdf*. Writes nothing, declares nothing, maps nothing.

    The returned mapping is the dry-import inventory: the authenticated hash,
    the measured page count, per-page accounting, the table and figure
    inventories, the candidate section headings and the extraction limitations.
    """
    pdf = Path(pdf)
    if not pdf.is_file():
        raise DryImportRefused(f"{pdf.name} is not a file, so there is nothing to measure")
    pages = extract_document(pdf)
    if not pages:
        raise DryImportRefused(f"{pdf.name} carries no page")
    census = graphical_census(pdf)
    if len(census["per_page"]) != len(pages):
        raise DryImportRefused(
            f"{pdf.name}: the graphical census read {len(census['per_page'])} pages and the text "
            f"extraction read {len(pages)}. A per-page row would pair the wrong two measurements."
        )
    tables = table_inventory(pages)
    sizes = point_size_inventory(pages)
    environment = measure_environment()
    candidates = heading_candidates(join_segments(pages))
    per_page = []
    for page, row in zip(pages, census["per_page"]):
        accounting = page_accounting(page)
        per_page.append(
            {
                "page": page.page,
                "characters": len(page.text),
                "nonws_characters": nonws_len(page.text),
                "blocks": len(page.blocks),
                "tables": len(page.tables),
                "images": int(row["images"]),
                "drawings": int(row["drawings"]),
                "annotations": int(row["annotations"]),
                "accounted": accounting["accounted"],
                "loss": accounting["loss"],
            }
        )
    return {
        "record_type": INVENTORY_RECORD_TYPE,
        "purpose": (
            "A dry import: what this PDF measurably carries, for an operator to reconcile against "
            "the document page by page before it is imported or assessed. No page map is declared "
            "here, no graph state is written, and no value is taken from another document."
        ),
        "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "bytes": pdf.stat().st_size,
        "pages": len(pages),
        "page_count_basis": "derived from the PDF; no expected count was supplied to check it against",
        "section_map": {
            "declared": False,
            "basis": (
                "A page map is a declaration. The candidate headings below are the blocks that "
                "could open one; the operator declares the map from the reconciliation against "
                "the PDF."
            ),
            "candidates": len(candidates),
        },
        "heading_candidates": candidates,
        "per_page": per_page,
        "tables": tables,
        "figures": figure_inventory(census),
        "metadata": metadata_census(pdf),
        "point_sizes": sizes,
        "citation_markers": citation_inventory(pages),
        "character_accounting": character_accounting(pages),
        "limitations": limitation_inventory(pages, tables, sizes),
        "versions": versions(),
        "extraction_environment": {
            "pymupdf": environment.pymupdf,
            "mupdf": environment.mupdf,
            "python": environment.python,
            "pinned_pymupdf": PINNED_PYMUPDF,
            "pinned_mupdf": PINNED_MUPDF,
            "off_pin_reason": off_pin_reason(environment),
            "cannot_reproduce_reason": cannot_reproduce_reason(environment),
        },
        "writes": {
            "graph_state": False,
            "basis": (
                "A dry import measures. It writes no document record, no source index and no "
                "snapshot, so nothing it produces can be read as an imported document."
            ),
        },
    }


# --------------------------------------------------------------------------- #
# The records (criteria 3 and 5)
# --------------------------------------------------------------------------- #


def _measured_for(inventory: dict[str, Any], spec: AcceptanceItem) -> Any:
    """The inventory values *spec* carries, by the keys it names."""
    if len(spec.measured_from) == 1:
        return inventory[spec.measured_from[0]]
    return {key: inventory[key] for key in spec.measured_from}


def build_acceptance(inventory: dict[str, Any]) -> dict[str, Any]:
    """The fidelity acceptance record, every item unreconciled.

    One row per class of evidence V08 names, each carrying the measurement that
    bears on it and the reason that measurement does not settle it. The operator
    fills in a verdict, a basis and an attestation; :func:`check_acceptance`
    says whether what they filled in is admissible.
    """
    return {
        "record_type": ACCEPTANCE_RECORD_TYPE,
        "purpose": (
            "What an operator reconciled against the PDF, class of evidence by class of "
            "evidence. An item nobody reconciled stays unreconciled, and the record is not "
            "complete while one does."
        ),
        "sha256": inventory["sha256"],
        "pages": inventory["pages"],
        "complete": False,
        "verdicts": sorted(ACCEPTANCE_VERDICTS),
        "bases": sorted(ACCEPTANCE_BASES),
        "inadmissible_bases_for_preserved": sorted(MEASUREMENT_ONLY_BASES),
        "rule": GRAPHICAL_PROOF_STATEMENT,
        "basis_rule": (
            "A measurement may stand behind a 'lost' verdict: an absence can be measured. It may "
            "not stand behind 'preserved' or 'partly_lost'. Presence has to be looked at, page by "
            "page, against the PDF. The basis vocabulary is closed: a basis outside it is a "
            "finding, so a measurement cannot enter under a wording of its own."
        ),
        "items": [
            {
                "item": spec.item,
                "what_must_be_reconciled": spec.what_must_be_reconciled,
                "measurement_is_not_proof": spec.measurement_is_not_proof,
                "measured": _measured_for(inventory, spec),
                "verdict": "unreconciled",
                "basis": None,
                "reconciled_by": None,
                "reconciled_on": None,
                "note": "",
            }
            for spec in ACCEPTANCE_ITEMS
        ],
    }


def check_acceptance(record: dict[str, Any]) -> list[dict[str, str]]:
    """Findings against an acceptance record, most structural first.

    Each finding is ``{code, item, message}``. An empty list means the record is
    admissible as it stands, which for an untouched record means *every item is
    still unreconciled and the record does not claim otherwise*.
    """
    findings: list[dict[str, str]] = []

    def finding(code: str, item: str, message: str) -> None:
        findings.append({"code": code, "item": item, "message": message})

    rows = record.get("items")
    if not isinstance(rows, list):
        raise DryImportRefused("acceptance record carries no 'items' list")
    present = {row.get("item") for row in rows if isinstance(row, dict)}
    for spec in ACCEPTANCE_ITEMS:
        if spec.item not in present:
            finding(
                "item_missing",
                spec.item,
                f"{spec.item} is not an item of this record; an item nobody names is an item "
                f"nobody reconciled",
            )
    unreconciled: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise DryImportRefused("an acceptance item is not a mapping")
        item = str(row.get("item"))
        if item not in _ITEM_BY_NAME:
            finding(
                "unknown_item",
                item,
                f"{item} is not one of the classes the acceptance catalogue declares",
            )
            continue
        verdict = row.get("verdict")
        if verdict not in ACCEPTANCE_VERDICTS:
            finding(
                "unknown_verdict",
                item,
                f"verdict {verdict!r} is not in {sorted(ACCEPTANCE_VERDICTS)}",
            )
            continue
        if verdict == "unreconciled":
            unreconciled.append(item)
            continue
        basis = row.get("basis")
        if not basis or not row.get("reconciled_by") or not row.get("reconciled_on"):
            finding(
                "verdict_without_attestation",
                item,
                f"verdict {verdict!r} needs a basis, a reconciled_by and a reconciled_on; a "
                f"verdict nobody signed is a verdict nobody reached",
            )
            continue
        if basis not in ACCEPTANCE_BASES:
            finding(
                "unknown_basis",
                item,
                f"basis {basis!r} is not in {sorted(ACCEPTANCE_BASES)}. The vocabulary is closed, "
                f"because a measurement written as free text would pass a refusal that tests for "
                f"the measurement's own name.",
            )
            continue
        if verdict in {"preserved", "partly_lost"} and basis in MEASUREMENT_ONLY_BASES:
            finding(
                "measurement_basis_not_proof",
                item,
                f"verdict {verdict!r} rests on {basis!r}, a measurement that is equally true of a "
                f"document whose graphical evidence is gone. {GRAPHICAL_PROOF_STATEMENT}",
            )
    if record.get("complete") and unreconciled:
        finding(
            "complete_with_unreconciled_item",
            ", ".join(sorted(unreconciled)),
            f"the record is marked complete while {len(unreconciled)} item(s) are still "
            f"unreconciled",
        )
    return findings


def build_unresolved_limitations(inventory: dict[str, Any]) -> dict[str, Any]:
    """The extraction limitations this PDF carries, every one Unresolved.

    Written before an assessment, not after it. Each row holds the measurement
    and what it costs a reader; none holds a resolution, because none of these
    is repairable by the importer. The record carries
    :data:`SPAN_LOCATES_STATEMENT`, so a reader who reaches a span through this
    extraction reads what the span does and does not buy.
    """
    limitations = inventory["limitations"]
    figures = inventory["figures"]
    rows: list[dict[str, Any]] = [
        {
            "limitation": "ligatures_in_the_extracted_text",
            "measured": {
                "present": limitations["ligatures"]["present"],
                "counts": limitations["ligatures"]["counts"],
                "pages": limitations["ligatures"]["pages"],
            },
            "consequence": limitations["ligatures"]["consequence"],
            "status": "Unresolved",
        },
        {
            "limitation": "prose_below_the_largest_point_size",
            "measured": limitations["prose_below_the_largest_point_size"]["sizes"],
            "consequence": limitations["prose_below_the_largest_point_size"]["consequence"],
            "status": "Unresolved",
        },
        {
            "limitation": "table_cells_outside_the_page_reading_order",
            "measured": {
                "cells": limitations["table_cells_not_in_page_reading_order"]["cells"],
                "where": limitations["table_cells_not_in_page_reading_order"]["where"],
            },
            "consequence": limitations["table_cells_not_in_page_reading_order"]["consequence"],
            "status": "Unresolved",
        },
        {
            "limitation": "graphical_evidence_is_not_in_the_extracted_text",
            "measured": {
                "images_on_any_page": figures["images_on_any_page"],
                "vector_drawings": figures["vector_drawings"],
                "annotations": figures["annotations"],
                "embedded_files": figures["embedded_files"],
            },
            "consequence": GRAPHICAL_PROOF_STATEMENT,
            "status": "Unresolved",
        },
        {
            "limitation": "no_declared_page_map",
            "measured": {
                "heading_candidates": inventory["section_map"]["candidates"],
                "pages": inventory["pages"],
            },
            "consequence": (
                "Without a declared page map no sub-section boundary is settled, so no "
                "sub-section-scoped result over this document is admissible yet."
            ),
            "status": "Unresolved",
        },
        {
            "limitation": "citation_markers_are_counted_not_resolved",
            "measured": inventory["citation_markers"]["counts"],
            "consequence": inventory["citation_markers"]["not_proof"],
            "status": "Unresolved",
        },
    ]
    return {
        "record_type": LIMITATIONS_RECORD_TYPE,
        "purpose": (
            "The extraction limitations of this document, recorded before any assessment reads "
            "its text. None is repaired here and none is resolved by being listed."
        ),
        "sha256": inventory["sha256"],
        "pages": inventory["pages"],
        "recorded_when": (
            "before assessment: the record is produced by the dry import, which precedes the "
            "import and therefore every result over the document"
        ),
        "resolved": False,
        "span_statement": SPAN_LOCATES_STATEMENT,
        "basis": limitations["basis"],
        "limitations": rows,
    }
