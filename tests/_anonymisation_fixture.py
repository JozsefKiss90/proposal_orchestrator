"""A synthetic Part B with planted entities, for the anonymisation tickets (AN3).

Every ticket of ``.scratch/msca-dn-anonymisation/tickets.md`` after AN3 tests
against this document: intake pins it, redaction removes what it plants, the
leak scan finds what it plants, the structural comparison measures it. So the
document carries one planted entity at least in every category of the
handoff's §5 A1 table, and every hard case the handoff names: a supervisor
table shaped like Table 1.4.1, a figure with a text layer, a logo image, PDF
metadata and XMP carrying a name, names hyphenated across line breaks,
initials, a possessive, a diacritic variant, self-citations, identifying grant
numbers and a niche topic combination.

:func:`build` writes two files: the PDF and the **planted-entity manifest**,
which says, for each entity, its category, its surface form and every place it
was planted (page, layer and the exact text). A test asks the manifest what a
stage should have found.

What is invented and what is not
--------------------------------
Every person, institution, project, facility, dataset, grant, reference and
contact identifier here is invented. Four sit in ranges reserved for examples:
the e-mail and web addresses under ``example.org``, the DOIs under the
``10.5555`` test prefix, and the ORCID, which is the identifier ORCID publishes
as its own documentation example. Two do not. The telephone number and the
grant number were made up to match the real formats, and no reserved range
exists for either, so neither is checked against a real holder. The two
countries are real, because a country names no one and the policy treats
countries by status, and the manifest marks them ``invented: false``.

The supervisor table's columns are modelled on the fields the handoff's §5 A4
says an evaluator scores. They are a shape for testing, not a claim about the
MSCA-DN application form (Tier 2A governs that, CLAUDE.md §10.6).

Where it may be written
-----------------------
Outside this repository, which :data:`THIS_REPOSITORY` measures from this
module's own location and :func:`build` does not take as an argument (the
V17/V18 pattern). The fixture is not private, but the stages it stands in for
write private artifacts beside it, and a test that wrote them here would
rehearse the one thing the pipeline must never do.

Reproducible
------------
Same code, same PyMuPDF build, same bytes. Every timestamp the PDF carries is
pinned, the file identifier is not regenerated, and the logo is drawn from
fixed pixels.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

THIS_REPOSITORY: Path = Path(__file__).resolve().parents[1]

MANIFEST_RECORD_TYPE = "planted_entity_manifest"
PDF_NAME = "synthetic_part_b.pdf"
MANIFEST_NAME = "planted_entities.json"

#: One id per row of the handoff's §5 A1 table, in its order, with the row's
#: label. AN2's policy names its categories with these ids.
CATEGORIES: tuple[tuple[str, str], ...] = (
    ("person_name", "Person names (supervisors, PIs, staff)"),
    ("institution", "Institutions, departments, companies"),
    ("project_identity", "Project acronym and title"),
    ("location", "Cities, regions, countries"),
    ("facility", "Unique facilities and named infrastructure"),
    ("dataset_cohort", "Named datasets and cohorts"),
    ("grant", "Prior and current grants (ids, acronyms, funders when identifying)"),
    ("self_citation", "Self-citations and citations of consortium members"),
    ("niche_topic", "Niche topic combinations"),
    ("identifying_number", "Numbers that identify (budgets per partner, staff counts, h-index)"),
    ("identifying_figure", "Figures with logos, maps, photos, names"),
)

#: The regex classes of the handoff's §5 A2, each planted at least once.
REGEX_CLASSES: tuple[str, ...] = ("doi", "grant_number", "orcid", "email", "url", "phone")

#: Layers whose plantings are found in the page's extracted text.
TEXT_LAYERS: frozenset[str] = frozenset(
    {"header", "footer", "body", "table", "figure_text", "reference_list"}
)

_PINNED_DATE = "D:20250101000000Z"
_WIDTH, _HEIGHT = 595, 842
_LEFT = 72

LOGO_PAGE = 1
SUPERVISOR_TABLE_PAGE = 2
DIAGRAM_PAGE = 3

_TABLE_TOP = 170
_ROW_HEIGHT = 18
_DIAGRAM_TOP = 130
_REFERENCES_TOP = 230

#: The numbered headings, one per page, in page order.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("1.1.", "Research objectives"),
    ("1.4.", "Quality of the supervision"),
    ("3.1.", "Work plan and resources"),
)

#: Body lines, set one per line so a hyphen at a line end stays a line break.
_PAGE_ONE = (
    "KELVARA (Kelp-Derived Lichen Varnishes for Arctic Resilience) is coordinated by the",
    "University of Kelpmoor, Department of Cryobiology, in Brennmark, Finland, with",
    "Fenwardt Biosystems GmbH in Austria. The scientific lead, Prof. Orsolya Vant-",
    "rell, built the programme on cryo-electron tomography of lichen photobionts in",
    "high-altitude permafrost, a combination few groups in Europe pursue [1, 2].",
    "O. Vantrell's ERC Consolidator Grant VARNISH (grant agreement No 109999417)",
    "funded the pilot at the Brennmark Tidal Flux Observatory, using samples from the",
    "VARNA-7 Longitudinal Lichen Cohort (n=1,283) [3].",
    "Contact: o.vantrell@kelpmoor.example.org, ORCID 0000-0002-1825-0097,",
    "+358 9 555 0142, https://kelvara.example.org.",
    "Dr Halvard Quist leads the training programme at the University of Kelp-",
    "moor. Prof. Vántrell chairs the Supervisory Board of KELVARA.",
    "Secondments also run in Upper Talvenia, Norway, an associated country.",
)

_HEADER = "KELVARA Part B"
_FOOTER = "University of Kelpmoor, page {page} of 3"
_PAGES = (1, 2, 3)

_PAGE_TWO = (
    "Each doctoral candidate has a main supervisor and a co-supervisor.",
    "Prof. Vantrell (h-index 37) leads a team of 23 staff holding EUR 412,560.",
)

#: One column per field the handoff's §5 A4 keeps in a synthetic row, plus the
#: name and the beneficiary it removes.
SUPERVISOR_TABLE_HEADER: tuple[str, ...] = (
    "Supervisor",
    "Beneficiary",
    "Degree",
    "Career stage",
    "h-index",
    "Publications",
    "PhDs",
    "Postdocs",
    "Role in the DN",
    "Expertise",
)

SUPERVISOR_ROWS: tuple[tuple[str, ...], ...] = (
    ("O. Vantrell", "Univ. of Kelpmoor", "PhD", "Full professor", "37", "142", "9", "6",
     "Coordinator", "Lichen symbiosis"),
    ("H. Quist", "Univ. of Kelpmoor", "PhD", "Associate prof.", "21", "64", "4", "3",
     "WP2 lead", "Cryo-ET imaging"),
    ("M. Ostrander", "Fenwardt Biosystems", "PhD", "Senior scientist", "15", "38", "2", "1",
     "Secondment host", "Industrial coatings"),
)

#: The columns holding a supervisor's career metrics, which the policy bands.
METRIC_COLUMNS: tuple[int, ...] = (4, 5, 6, 7)

_COLUMN_WIDTHS = (52, 68, 26, 58, 30, 44, 26, 34, 56, 72)

#: The vertical band of each (page, layer) that carries text, so a test reads a
#: table planting from the table and not from a body line that happens to hold
#: the same characters.
LAYER_BANDS: dict[tuple[int, str], tuple[float, float]] = {
    **{(page, "header"): (0, 30) for page in _PAGES},
    **{(page, "footer"): (_HEIGHT - 35, _HEIGHT) for page in _PAGES},
    (1, "body"): (80, _HEIGHT - 35),
    (2, "body"): (80, _TABLE_TOP),
    (2, "table"): (_TABLE_TOP, _TABLE_TOP + _ROW_HEIGHT * (1 + len(SUPERVISOR_ROWS))),
    (3, "figure_text"): (_DIAGRAM_TOP, _DIAGRAM_TOP + 40),
    (3, "reference_list"): (_REFERENCES_TOP, _HEIGHT),
}

#: The text layer of the work-plan diagram, one label per box.
DIAGRAM_LABELS: tuple[str, ...] = (
    "KELVARA WP1: Sampling",
    "Univ. of Kelpmoor",
    "Brennmark Observatory",
)

_REFERENCES = (
    "[1] Vantrell, O. and Quist, H. (2021) Lichen varnish at altitude. doi:10.5555/kelvara.2021.001",
    "[2] Quist, H. (2022) Photobiont tomography in permafrost. doi:10.5555/kelvara.2022.014",
    "[3] VARNA-7 Cohort Consortium (2020) Cohort profile. https://varna7.example.org",
)

_METADATA = {
    "author": "Orsolya Vantrell",
    "title": "KELVARA Part B",
    "subject": "Kelp-Derived Lichen Varnishes for Arctic Resilience",
    "keywords": "",
    "creator": "University of Kelpmoor",
    "producer": "University of Kelpmoor Typesetting Unit",
    "creationDate": _PINNED_DATE,
    "modDate": _PINNED_DATE,
}

_XMP = (
    '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
    'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description '
    'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator><rdf:Seq><rdf:li>'
    "Orsolya Vantrell</rdf:li></rdf:Seq></dc:creator></rdf:Description></rdf:RDF>"
    "</x:xmpmeta>"
)

_EMBEDDED_FILE = "kelvara_budget_notes.txt"


def _p(layer: str, form: str, text: str | None, page: int | None = None, **extra: str) -> dict:
    return {"layer": layer, "form": form, "page": page, "text": text, **extra}


def _entity(
    eid: str,
    category: str,
    surface: str,
    plantings: list[dict],
    *,
    regex_class: str | None = None,
    invented: bool = True,
    eu_status: str | None = None,
) -> dict[str, Any]:
    return {
        "id": eid,
        "category": category,
        "surface": surface,
        "regex_class": regex_class,
        "invented": invented,
        # A country's status is what the policy keeps when it generalises it.
        "eu_status": eu_status,
        # A niche combination is flagged for the rewrite and the attack, never
        # edited automatically (handoff §5 A1).
        "auto_edit": category != "niche_topic",
        "plantings": plantings,
    }


def _cell(row: int, col: int) -> dict:
    """A planting in the supervisor table, addressed by data row and column."""
    return _p("table", "cell", SUPERVISOR_ROWS[row][col], SUPERVISOR_TABLE_PAGE,
              row=row + 1, col=col)


def _every_page(layer: str, form: str, text: str) -> list[dict]:
    return [_p(layer, form, text, page) for page in _PAGES]


#: Every planted entity, and every place it was planted. The builder sets the
#: text above; the test file holds this list to the PDF it produces.
ENTITIES: tuple[dict[str, Any], ...] = (
    _entity("E01", "person_name", "Orsolya Vantrell", [
        _p("body", "hyphenated_line_break", "Vant-\nrell", 1),
        _p("body", "possessive", "O. Vantrell's", 1),
        _p("body", "diacritic", "Vántrell", 1),
        _p("body", "surname", "Prof. Vantrell", 2),
        {**_cell(0, 0), "form": "initial"},
        _p("reference_list", "citation_name", "Vantrell, O.", 3),
        _p("metadata", "exact", "Orsolya Vantrell", field="author"),
        _p("xmp", "exact", "Orsolya Vantrell"),
    ]),
    _entity("E02", "person_name", "Halvard Quist", [
        _p("body", "exact", "Halvard Quist", 1),
        {**_cell(1, 0), "form": "initial"},
        _p("reference_list", "citation_name", "Quist, H.", 3),
    ]),
    _entity("E03", "person_name", "Mats Ostrander", [
        {**_cell(2, 0), "form": "initial"},
    ]),
    _entity("E04", "person_name", "o.vantrell@kelpmoor.example.org", [
        _p("body", "exact", "o.vantrell@kelpmoor.example.org", 1),
    ], regex_class="email"),
    _entity("E05", "person_name", "0000-0002-1825-0097", [
        _p("body", "exact", "0000-0002-1825-0097", 1),
    ], regex_class="orcid"),
    _entity("E06", "person_name", "+358 9 555 0142", [
        _p("body", "exact", "+358 9 555 0142", 1),
    ], regex_class="phone"),
    _entity("E07", "institution", "University of Kelpmoor", [
        _p("body", "exact", "University of Kelpmoor", 1),
        _p("body", "hyphenated_line_break", "Kelp-\nmoor", 1),
        {**_cell(0, 1), "form": "abbreviation"},
        {**_cell(1, 1), "form": "abbreviation"},
        _p("figure_text", "abbreviation", "Univ. of Kelpmoor", 3),
        *_every_page("footer", "exact", "University of Kelpmoor"),
        _p("metadata", "exact", "University of Kelpmoor", field="creator"),
        _p("metadata", "exact", "University of Kelpmoor", field="producer"),
    ]),
    _entity("E08", "institution", "Department of Cryobiology", [
        _p("body", "exact", "Department of Cryobiology", 1),
    ]),
    _entity("E09", "institution", "Fenwardt Biosystems GmbH", [
        _p("body", "exact", "Fenwardt Biosystems GmbH", 1),
        {**_cell(2, 1), "form": "short_name"},
    ]),
    _entity("E10", "project_identity", "KELVARA", [
        _p("body", "exact", "KELVARA", 1),
        _p("figure_text", "exact", "KELVARA", 3),
        *_every_page("header", "exact", "KELVARA"),
        _p("metadata", "exact", "KELVARA", field="title"),
        _p("embedded_file_name", "lowercase", "kelvara"),
    ]),
    _entity("E11", "project_identity", "Kelp-Derived Lichen Varnishes for Arctic Resilience", [
        _p("body", "exact", "Kelp-Derived Lichen Varnishes for Arctic Resilience", 1),
        _p("metadata", "exact", "Kelp-Derived Lichen Varnishes for Arctic Resilience",
           field="subject"),
    ]),
    _entity("E12", "project_identity", "https://kelvara.example.org", [
        _p("body", "exact", "https://kelvara.example.org", 1),
    ], regex_class="url"),
    _entity("E13", "location", "Brennmark", [
        _p("body", "exact", "Brennmark", 1),
        _p("figure_text", "exact", "Brennmark", 3),
    ]),
    _entity("E14", "location", "Finland", [_p("body", "exact", "Finland", 1)],
            invented=False, eu_status="member_state"),
    _entity("E15", "location", "Austria", [_p("body", "exact", "Austria", 1)],
            invented=False, eu_status="member_state"),
    _entity("E30", "location", "Upper Talvenia", [_p("body", "exact", "Upper Talvenia", 1)]),
    _entity("E31", "location", "Norway", [_p("body", "exact", "Norway", 1)],
            invented=False, eu_status="associated_country"),
    _entity("E16", "facility", "Brennmark Tidal Flux Observatory", [
        _p("body", "exact", "Brennmark Tidal Flux Observatory", 1),
        _p("figure_text", "short_name", "Brennmark Observatory", 3),
    ]),
    _entity("E17", "dataset_cohort", "VARNA-7 Longitudinal Lichen Cohort", [
        _p("body", "exact", "VARNA-7 Longitudinal Lichen Cohort", 1),
        _p("reference_list", "short_name", "VARNA-7 Cohort Consortium", 3),
    ]),
    _entity("E18", "grant", "VARNISH", [_p("body", "exact", "VARNISH", 1)]),
    _entity("E19", "grant", "109999417", [
        _p("body", "exact", "109999417", 1),
    ], regex_class="grant_number"),
    _entity("E20", "self_citation", "Vantrell, O. and Quist, H. (2021)", [
        _p("reference_list", "reference_entry", "Vantrell, O. and Quist, H. (2021)", 3),
        _p("body", "marker", "[1, 2]", 1),
    ]),
    _entity("E32", "self_citation", "Quist, H. (2022)", [
        _p("reference_list", "reference_entry", "Quist, H. (2022)", 3),
    ]),
    _entity("E21", "self_citation", "10.5555/kelvara.2021.001", [
        _p("reference_list", "exact", "10.5555/kelvara.2021.001", 3),
    ], regex_class="doi"),
    _entity("E22", "self_citation", "10.5555/kelvara.2022.014", [
        _p("reference_list", "exact", "10.5555/kelvara.2022.014", 3),
    ], regex_class="doi"),
    _entity("E23", "niche_topic",
            "cryo-electron tomography of lichen photobionts in high-altitude permafrost", [
        _p("body", "line_break",
           "cryo-electron tomography of lichen photobionts in\nhigh-altitude permafrost", 1),
    ]),
    _entity("E24", "identifying_number", "h-index 37", [
        _p("body", "exact", "h-index 37", 2),
        _cell(0, 4),
    ]),
    _entity("E25", "identifying_number", "23 staff", [_p("body", "exact", "23 staff", 2)]),
    _entity("E26", "identifying_number", "EUR 412,560", [_p("body", "exact", "EUR 412,560", 2)]),
    _entity("E27", "identifying_figure", "the University of Kelpmoor logo", [
        _p("image", "logo", None, LOGO_PAGE),
    ]),
    _entity("E28", "identifying_number", "the supervisors' career metrics", [
        _cell(row, col)
        for row in range(len(SUPERVISOR_ROWS))
        for col in METRIC_COLUMNS
        if (row, col) != (0, 4)
    ]),
    _entity("E29", "identifying_figure", "the work-plan diagram, which names the project, "
            "the coordinator and the facility", [
        _p("drawing", "vector_figure_with_names", None, DIAGRAM_PAGE),
    ]),
)


class FixtureRefused(RuntimeError):
    """The fixture was asked to build somewhere it must not."""


@dataclass(frozen=True)
class BuiltFixture:
    pdf: Path
    manifest: Path


def _logo_png() -> bytes:
    """A 32-pixel two-colour logo, drawn from fixed pixels."""
    import pymupdf

    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 32, 32), 0)
    pix.set_rect(pix.irect, (20, 70, 140))
    pix.set_rect(pymupdf.IRect(8, 8, 24, 24), (230, 190, 40))
    return pix.tobytes("png")


def _lines(page: Any, lines: tuple[str, ...], y: float, size: float = 10) -> float:
    for line in lines:
        page.insert_text((_LEFT, y), line, fontsize=size)
        y += size * 1.4
    return y


def _table(page: Any, y0: float) -> None:
    import pymupdf

    row_height = _ROW_HEIGHT
    rows = (SUPERVISOR_TABLE_HEADER, *SUPERVISOR_ROWS)
    right = _LEFT + sum(_COLUMN_WIDTHS)
    bottom = y0 + row_height * len(rows)
    for r in range(len(rows) + 1):
        y = y0 + r * row_height
        page.draw_line(pymupdf.Point(_LEFT, y), pymupdf.Point(right, y))
    x = _LEFT
    for width in (0, *_COLUMN_WIDTHS):
        x += width
        page.draw_line(pymupdf.Point(x, y0), pymupdf.Point(x, bottom))
    for r, row in enumerate(rows):
        x = _LEFT
        for width, cell in zip(_COLUMN_WIDTHS, row):
            page.insert_text((x + 2, y0 + r * row_height + 12), cell, fontsize=6)
            x += width


def _diagram(page: Any, y0: float) -> None:
    import pymupdf

    boxes = []
    for n, label in enumerate(DIAGRAM_LABELS):
        rect = pymupdf.Rect(_LEFT + n * 155, y0, _LEFT + n * 155 + 135, y0 + 40)
        page.draw_rect(rect, color=(0, 0, 0), fill=(0.85, 0.9, 1.0))
        page.insert_text((rect.x0 + 6, rect.y0 + 24), label, fontsize=8)
        boxes.append(rect)
    for left, right in zip(boxes, boxes[1:]):
        mid = (left.y0 + left.y1) / 2
        page.draw_line(pymupdf.Point(left.x1, mid), pymupdf.Point(right.x0, mid))


PINNED_DATE = _PINNED_DATE


def _pin_timestamps(doc: Any) -> None:
    """Pin every creation and modification date, the embedded file's included."""
    for xref in range(1, doc.xref_length()):
        for key in ("CreationDate", "ModDate", "Params/CreationDate", "Params/ModDate"):
            if doc.xref_get_key(xref, key)[0] != "null":
                doc.xref_set_key(xref, key, f"({_PINNED_DATE})")


def _running_text(doc: Any) -> None:
    for page in _PAGES:
        doc[page - 1].insert_text((_LEFT, 20), _HEADER, fontsize=8)
        doc[page - 1].insert_text((_LEFT, _HEIGHT - 20), _FOOTER.format(page=page), fontsize=8)


def _render(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    try:
        headings = iter(SECTIONS)

        p1 = doc.new_page(width=_WIDTH, height=_HEIGHT)
        p1.insert_image(pymupdf.Rect(480, 30, 523, 73), stream=_logo_png())
        marker, title = next(headings)
        p1.insert_text((_LEFT, 100), f"{marker} {title}", fontsize=12)
        _lines(p1, _PAGE_ONE, 130)

        p2 = doc.new_page(width=_WIDTH, height=_HEIGHT)
        marker, title = next(headings)
        p2.insert_text((_LEFT, 100), f"{marker} {title}", fontsize=12)
        _lines(p2, _PAGE_TWO, 130)
        _table(p2, _TABLE_TOP)

        p3 = doc.new_page(width=_WIDTH, height=_HEIGHT)
        marker, title = next(headings)
        p3.insert_text((_LEFT, 100), f"{marker} {title}", fontsize=12)
        _diagram(p3, _DIAGRAM_TOP)
        p3.insert_text((_LEFT, _REFERENCES_TOP + 10), "References", fontsize=10)
        _lines(p3, _REFERENCES, _REFERENCES_TOP + 30, size=8)

        _running_text(doc)
        doc.set_metadata(_METADATA)
        doc.set_xml_metadata(_XMP)
        doc.embfile_add(_EMBEDDED_FILE, b"Synthetic notes.", filename=_EMBEDDED_FILE)
        _pin_timestamps(doc)
        doc.save(path, garbage=4, deflate=True, no_new_id=True)
    finally:
        doc.close()


def _manifest(pdf: Path) -> dict[str, Any]:
    return {
        "record_type": MANIFEST_RECORD_TYPE,
        "synthetic": True,
        "purpose": (
            "What the synthetic Part B fixture plants, and where, so a test can check what a "
            "stage of the anonymisation pipeline found. Every entity is invented except the "
            "two countries."
        ),
        "pdf_name": pdf.name,
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "categories": [{"id": cid, "handoff_row": label} for cid, label in CATEGORIES],
        "regex_classes": list(REGEX_CLASSES),
        "entities": list(ENTITIES),
    }


DICTIONARY_NAME = "entity_dictionary.json"


def _d(eid: str, category: str, surface: str, replacements: list[str], *,
       variants: tuple[str, ...] = (), **extra: Any) -> dict[str, Any]:
    return {"id": eid, "category": category, "surface": surface, "variants": list(variants),
            "replacements": replacements, **extra}


def _person(given: str, family: str) -> dict[str, Any]:
    return {"given": given, "family": family, "match_family_alone": True}


#: The entity dictionary an operator would author for this fixture (AN5). Entry
#: ids are the manifest's. Each replacement list ends in one short enough for
#: the smallest box the entity occupies. Identifying numbers are absent: no
#: honest band fits the box of the number it replaces, so they wait for A3/A4.
DICTIONARY: dict[str, Any] = {
    "schema": "anonymisation_entity_dictionary/1",
    "record_type": "anonymisation_entity_dictionary",
    "synthetic": True,
    "entries": [
        _d("E01", "person_name", "Orsolya Vantrell", ["Supervisor S01", "S01"],
           person=_person("Orsolya", "Vantrell")),
        _d("E02", "person_name", "Halvard Quist", ["Supervisor S02", "S02"],
           person=_person("Halvard", "Quist")),
        _d("E03", "person_name", "Mats Ostrander", ["Supervisor S03", "S03"],
           person=_person("Mats", "Ostrander")),
        _d("E07", "institution", "University of Kelpmoor",
           ["Beneficiary B1 (university, EU Member State)", "Beneficiary B1", "B1"],
           variants=("Univ. of Kelpmoor",)),
        _d("E08", "institution", "Department of Cryobiology", ["a department of Beneficiary B1", "a B1 department"]),
        _d("E09", "institution", "Fenwardt Biosystems GmbH",
           ["Partner P1 (company, EU Member State)", "Partner P1"],
           variants=("Fenwardt Biosystems",)),
        _d("E10", "project_identity", "KELVARA", ["PROJ"]),
        _d("E11", "project_identity", "Kelp-Derived Lichen Varnishes for Arctic Resilience",
           ["Project Title Withheld"]),
        _d("E13", "location", "Brennmark", ["a coastal town", "a town"]),
        _d("E30", "location", "Upper Talvenia", ["a northern region", "a region"]),
        _d("E14", "location", "Finland", [], country=True),
        _d("E15", "location", "Austria", [], country=True),
        _d("E31", "location", "Norway", [], country=True),
        _d("E16", "facility", "Brennmark Tidal Flux Observatory",
           ["a national tidal observatory", "an observatory"],
           variants=("Brennmark Observatory",)),
        _d("E17", "dataset_cohort", "VARNA-7 Longitudinal Lichen Cohort",
           ["a national longitudinal cohort", "a cohort"],
           variants=("VARNA-7 Cohort Consortium", "VARNA-7")),
        _d("E18", "grant", "VARNISH", ["a grant"], match_case=True),
        _d("E20", "self_citation", "Vantrell, O. and Quist, H. (2021)",
           ["[R1] reference withheld", "[R1]"]),
        _d("E32", "self_citation", "Quist, H. (2022)", ["[R2] reference withheld", "[R2]"]),
        _d("E23", "niche_topic",
           "cryo-electron tomography of lichen photobionts in high-altitude permafrost", []),
    ],
    "regex_classes": {
        "doi": {"category": "self_citation", "replacements": ["[DOI withheld]", "[DOI]"]},
        "grant_number": {"category": "grant", "replacements": ["[number withheld]", "[no.]"]},
        "orcid": {"category": "person_name", "replacements": ["[ORCID withheld]"]},
        "email": {"category": "person_name", "replacements": ["[e-mail withheld]"]},
        "url": {"category": "project_identity", "replacements": ["[URL withheld]"]},
        "phone": {"category": "person_name", "replacements": ["[phone withheld]"]},
    },
}


TABLE_SPEC_NAME = "table_spec.json"


def _column(index: int, field: str, rule: str, **extra: Any) -> dict[str, Any]:
    return {"index": index, "header": SUPERVISOR_TABLE_HEADER[index], "field": field,
            "rule": rule, **extra}


#: The Table 1.4.1 specification an operator would author for this fixture
#: (AN7). It says which column is which, and how each is synthesised. The
#: bands and the maps are a shape for testing, not a claim about how an
#: evaluator reads a career stage.
TABLE_SPEC: dict[str, Any] = {
    "schema": "anonymisation_table_spec/1",
    "record_type": "anonymisation_table_spec",
    "synthetic": True,
    "table": {"page": SUPERVISOR_TABLE_PAGE, "index": 0, "header_rows": 1},
    "columns": [
        _column(0, "supervisor", "pseudonym", category="person_name", row_key=True),
        _column(1, "beneficiary", "pseudonym", category="institution"),
        _column(2, "degree_level", "keep"),
        _column(3, "career_stage", "map", map={
            "Full professor": "Senior",
            "Associate prof.": "Established",
            "Senior scientist": "Established",
        }),
        _column(4, "h_index", "band", bands=[[0, 9], [10, 19], [20, 29], [30, 39], [40, None]]),
        _column(5, "publication_count", "band",
                bands=[[0, 49], [50, 99], [100, 199], [200, None]]),
        _column(6, "phds_supervised", "band", bands=[[0, 4], [5, 9], [10, None]]),
        _column(7, "postdocs_supervised", "band", bands=[[0, 4], [5, 9], [10, None]]),
        _column(8, "dn_role", "keep"),
        _column(9, "expertise_kind", "map", map={
            "Lichen symbiosis": "Plant biology",
            "Cryo-ET imaging": "Structural imaging",
            "Industrial coatings": "Materials science",
        }),
    ],
}


def _write_private(target: Path, name: str, record: dict[str, Any], what: str) -> Path:
    target = Path(target).resolve()
    if target.is_relative_to(THIS_REPOSITORY):
        raise FixtureRefused(f"{target} is inside the repository; the {what} is private.")
    target.mkdir(parents=True, exist_ok=True)
    path = target / name
    path.write_bytes((json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return path


def write_dictionary(target: Path) -> Path:
    """Write :data:`DICTIONARY` into *target*, outside this repository."""
    return _write_private(target, DICTIONARY_NAME, DICTIONARY, "dictionary")


def write_table_spec(target: Path, spec: dict[str, Any] | None = None) -> Path:
    """Write *spec* (by default :data:`TABLE_SPEC`) into *target*, outside this repository."""
    return _write_private(target, TABLE_SPEC_NAME, TABLE_SPEC if spec is None else spec,
                          "table specification")


def build(target: Path) -> BuiltFixture:
    """Write the fixture PDF and its manifest into *target*, outside this repository."""
    target = Path(target).resolve()
    if target.is_relative_to(THIS_REPOSITORY):
        raise FixtureRefused(
            f"{target} is inside the repository. The fixture is built outside it, where the "
            "stages it stands in for write their private artifacts."
        )
    target.mkdir(parents=True, exist_ok=True)
    pdf = target / PDF_NAME
    _render(pdf)
    manifest = target / MANIFEST_NAME
    text = json.dumps(_manifest(pdf), indent=2, ensure_ascii=False) + "\n"
    manifest.write_bytes(text.encode("utf-8"))
    return BuiltFixture(pdf=pdf, manifest=manifest)
