"""Claude-free extraction of an external proposal PDF into paragraphs, table
rows and candidate claims.

This is the substrate ``tools/import_external_proposal.py`` runs on (spec
``plans/msca_dn_pre_evaluation_spec.md`` PE-03). It knows nothing about any
instrument, section map or workspace: it turns one PDF into per-page
extracts, joins them into paragraphs, renders tables to rows, splits
sentences and names which sentences the claim rule selects. The importer
decides where sub-sections start and what the records look like.

What it deliberately does not do
--------------------------------
* No layout analysis beyond what pymupdf's ``blocks`` and ``find_tables``
  return. Headings are not recognised here; a heading is a prose block the
  importer identifies by its own marker.
* No de-hyphenation, no character rewriting. Whitespace is the only thing
  normalised, and it is normalised the way the source index normalises a
  page (:func:`runner.source_index.normalise_whitespace`), so a paragraph is
  a substring of the page's source text and a claim's offsets resolve into
  it.
* No inference. The claim rule is a closed set of regular expressions
  (:data:`CLAIM_RULES`), versioned by :data:`CLAIM_EXTRACTION_VERSION`.

Versions
--------
The four version strings are what an import manifest records (spec PE-05): a
hash of an output cannot say which extractor produced it, so the extractor
says so itself. Bump a version when its rule changes.

Determinism
-----------
Everything here is a pure function of the PDF bytes and these constants.
Re-running over the same file yields equal objects; the importer's check
mode relies on that.

Constitutional authority:
    Subordinate to CLAUDE.md. Reads a stored Tier 3 file, writes nothing,
    invokes no Claude, evaluates no gate.
"""

from __future__ import annotations

import contextlib
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from runner.source_index import PAGE_TEXT_METHOD, normalise_whitespace

#: pymupdf ``get_text("text")`` for the page text (as the source index), ``blocks``
#: for paragraphs, ``dict`` for point sizes, ``find_tables`` for tables.
EXTRACTOR_VERSION = "1.0.0"
#: Whitespace collapse; one paragraph per text block; a block whose centre lies
#: in a table's bounding box is table text; the page-crossing join rule of
#: :func:`join_segments`.
NORMALISATION_VERSION = "1.0.0"
#: ``find_tables(strategy="lines_strict")``; one pipe-delimited row per table
#: row, cells whitespace-collapsed, a pipe inside a cell refused.
TABLE_RENDERING_VERSION = "1.0.0"
#: :func:`split_sentences` plus :data:`CLAIM_RULES`.
CLAIM_EXTRACTION_VERSION = "1.0.0"

#: The pymupdf table-finding strategy. ``lines`` splits a wrapped header cell
#: into one row per line; ``lines_strict`` keeps a ruled cell whole.
TABLE_STRATEGY = "lines_strict"

ROW_OPEN = "| "
ROW_SEP = " | "
ROW_CLOSE = " |"

_TERMINAL = re.compile(r"[.!?:;]$")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=\S)")
#: A piece ending in one of these is not a sentence end; the next piece is
#: re-attached. Closed and versioned with the claim extraction.
_ABBREVIATIONS = re.compile(
    r"(?:\b(?:e\.g|i\.e|etc|vs|cf|approx|ca|Dr|Prof|No|Fig|Eq|Ref|et al|incl|resp)|\b[A-Z]|\b\d+)\.$"
)

#: The claim rule. A sentence is a claim when any pattern matches. The names
#: are the vocabulary a manifest and an audit report use.
CLAIM_RULES: dict[str, tuple[re.Pattern[str], ...]] = {
    "quantity": (
        re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?\s*(?:%|per cent\b|percent\b)"),
        re.compile(r"[≥≤<>]\s*\d"),
        re.compile(
            r"(?<![\w.])(?:\d+(?:[.,]\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|"
            r"eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|hundred)\s+(?:"
            r"months?|years?|weeks?|days?|hours?|doctoral candidates|DCs|candidates|researchers|"
            r"fellows|partners?|beneficiaries|organisations|institutions|countries|hospitals|"
            r"patients|secondments?|publications?|peer-reviewed publications|events?|workshops?|"
            r"schools?|modules?|courses?|datasets?|use cases|case studies|work packages|ECTS|"
            r"supervisors|sites|pilots?|participants|universities|companies|SMEs|environments|"
            r"sectors|disciplines|clinical partners|industrial partners|associated partners"
            r")\b",
            re.IGNORECASE,
        ),
        re.compile(r"(?<![\w.,/-])\d{2,}(?:[.,]\d+)?(?![\w.%/-])"),
    ),
    "evidential": (
        re.compile(
            r"\b(?:reviews?|studies|evidence|literature|data|results?|experience|surveys?|"
            r"reports?|trials?|analyses|findings)\s+"
            r"(?:confirm|show|reveal|demonstrate|indicate|suggest|establish)(?:s|ed)?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:has|have|had|is|are|was|were|been)\s+(?:(?:already|previously|successfully|"
            r"recently|widely)\s+)?(?:demonstrated|shown|validated|proven|confirmed|established|"
            r"reported|published|piloted|tested)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bstate[- ]of[- ]the[- ]art\b", re.IGNORECASE),
        re.compile(r"\btrack record\b", re.IGNORECASE),
        re.compile(
            r"\b(?:world|internationally|nationally|europe)[- ]leading\b|"
            r"\bleading (?:European|international|research|centre|center|institution)",
            re.IGNORECASE,
        ),
        re.compile(r"\bfor the first time\b|\bfirst[- ]ever\b|\bfirst of its kind\b", re.IGNORECASE),
    ),
}


class ExtractionError(RuntimeError):
    """Refusal: the PDF or a table cannot be rendered under the declared rules."""


# --------------------------------------------------------------------------- #
# Result types
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Block:
    """One prose text block of a page, whitespace-collapsed, outside every table."""

    page: int
    bbox: tuple[float, float, float, float]
    text: str


@dataclass(frozen=True)
class Table:
    """One table of a page as pymupdf found it, cells whitespace-collapsed."""

    page: int
    index: int
    bbox: tuple[float, float, float, float]
    rows: tuple[tuple[str, ...], ...]

    @property
    def cols(self) -> int:
        return len(self.rows[0]) if self.rows else 0


@dataclass(frozen=True)
class Segment:
    """One unit of a page in reading order: a prose block or a rendered row."""

    kind: str
    """``prose`` or ``row``."""
    page: int
    text: str
    table: int | None = None
    """Index of the table on its page, for a row."""
    row: int | None = None
    """Row index within that table, for a row."""


@dataclass(frozen=True)
class PageExtract:
    """Everything the extractor knows about one page."""

    page: int
    text: str
    """The page's source text: :data:`runner.source_index.PAGE_TEXT_METHOD`."""
    blocks: tuple[Block, ...]
    tables: tuple[Table, ...]
    segments: tuple[Segment, ...]
    images: int
    chars_by_point_size: dict[str, int] = field(default_factory=dict)
    """Characters per point size (``"12.0"`` → count), over every span the page carries."""
    text_by_point_size: dict[str, str] = field(default_factory=dict)
    """The span texts per point size, concatenated, so a reader can say what
    the off-size text is (bullet glyphs, say) rather than guess."""


@dataclass(frozen=True)
class Paragraph:
    """One paragraph of the joined document: prose or one table row."""

    kind: str
    text: str
    pages: tuple[int, ...]
    table: tuple[int, int] | None = None
    """``(page, table index)`` for a row."""
    row: int | None = None


# --------------------------------------------------------------------------- #
# Rows
# --------------------------------------------------------------------------- #


def render_row(cells: Sequence[str]) -> str:
    """``| a | b | c |`` — one paragraph per row, each row independently parseable."""
    for c in cells:
        if "|" in c:
            raise ExtractionError(
                f"a table cell contains a pipe and cannot be rendered unambiguously: {c!r}"
            )
    return ROW_OPEN + ROW_SEP.join(cells) + ROW_CLOSE


def is_row(text: str) -> bool:
    return text.startswith(ROW_OPEN) and text.endswith(ROW_CLOSE) and len(text) >= len(ROW_OPEN) + len(ROW_CLOSE)


def parse_row(text: str) -> tuple[str, ...]:
    """The inverse of :func:`render_row`; raises on a line that is not a row."""
    if not is_row(text):
        raise ExtractionError(f"not a rendered table row: {text[:60]!r}")
    inner = text[len(ROW_OPEN):-len(ROW_CLOSE)]
    return tuple(inner.split(ROW_SEP))


# --------------------------------------------------------------------------- #
# Page extraction
# --------------------------------------------------------------------------- #


def _centre_in(bbox: Sequence[float], boxes: Sequence[Sequence[float]]) -> bool:
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes)


def _find_tables(page: Any) -> list[Any]:
    # pymupdf prints a layout-package advertisement on every call; it is not
    # part of the extraction and would land in the importer's output.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return list(page.find_tables(strategy=TABLE_STRATEGY).tables)


def _extract_page(page: Any, page_no: int) -> PageExtract:
    text = normalise_whitespace(page.get_text("text"))
    tables: list[Table] = []
    for i, t in enumerate(_find_tables(page)):
        rows = tuple(
            tuple(normalise_whitespace(c or "") for c in row) for row in t.extract()
        )
        x0, y0, x1, y1 = (float(v) for v in t.bbox)
        tables.append(Table(page=page_no, index=i, bbox=(x0, y0, x1, y1), rows=rows))
    boxes = [t.bbox for t in tables]
    blocks: list[Block] = []
    for raw in page.get_text("blocks"):
        x0, y0, x1, y1, btext, _no, btype = raw[:7]
        if btype != 0:
            continue
        collapsed = normalise_whitespace(btext)
        if not collapsed or _centre_in((x0, y0, x1, y1), boxes):
            continue
        blocks.append(Block(page=page_no, bbox=(float(x0), float(y0), float(x1), float(y1)), text=collapsed))
    ordered: list[tuple[tuple[float, float], Segment | Table]] = []
    for b in blocks:
        ordered.append(((b.bbox[1], b.bbox[0]), Segment("prose", page_no, b.text)))
    for t in tables:
        ordered.append(((t.bbox[1], t.bbox[0]), t))
    segments: list[Segment] = []
    for _key, item in sorted(ordered, key=lambda kv: kv[0]):
        if isinstance(item, Table):
            for r, cells in enumerate(item.rows):
                segments.append(Segment("row", page_no, render_row(cells), table=item.index, row=r))
        else:
            segments.append(item)
    sizes: Counter[str] = Counter()
    texts: dict[str, list[str]] = {}
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                key = f"{round(float(span['size']), 1):.1f}"
                sizes[key] += len(span.get("text", ""))
                texts.setdefault(key, []).append(span.get("text", ""))
    return PageExtract(
        page=page_no,
        text=text,
        blocks=tuple(blocks),
        tables=tuple(tables),
        segments=tuple(segments),
        images=len(page.get_images(full=True)),
        chars_by_point_size=dict(sorted(sizes.items())),
        text_by_point_size={k: "".join(v) for k, v in sorted(texts.items())},
    )


def extract_document(pdf: Path) -> tuple[PageExtract, ...]:
    """Every page of *pdf*, in order. The page text equals
    :func:`runner.source_index.read_page_text` for that page."""
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        return tuple(_extract_page(doc[i], i + 1) for i in range(doc.page_count))
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# Joining
# --------------------------------------------------------------------------- #


def _joins(tail: str, head: str) -> bool:
    """The page-crossing rule: the paragraph at the foot of a page continues at
    the head of the next when it ends without terminal punctuation and the
    next starts in lower case, or when it ends with a hyphen."""
    if not tail or not head:
        return False
    if _TERMINAL.search(tail):
        return False
    return head[0].islower() or tail.endswith("-")


def join_segments(pages: Sequence[PageExtract]) -> tuple[Paragraph, ...]:
    """The document as one paragraph stream, rows included, page-crossing
    prose paragraphs rejoined with a single space."""
    out: list[Paragraph] = []
    for page in pages:
        for i, seg in enumerate(page.segments):
            if seg.kind == "row":
                if seg.table is None:
                    raise ExtractionError(f"row segment on page {page.page} names no table")
                out.append(
                    Paragraph("row", seg.text, (page.page,), table=(page.page, seg.table), row=seg.row)
                )
                continue
            if (
                i == 0
                and out
                and out[-1].kind == "prose"
                and out[-1].pages[-1] == page.page - 1
                and _joins(out[-1].text, seg.text)
            ):
                prev = out.pop()
                out.append(Paragraph("prose", prev.text + " " + seg.text, prev.pages + (page.page,)))
                continue
            out.append(Paragraph("prose", seg.text, (page.page,)))
    return tuple(out)


# --------------------------------------------------------------------------- #
# Sentences and claims
# --------------------------------------------------------------------------- #


def split_sentences(text: str) -> tuple[str, ...]:
    """Sentences of a collapsed paragraph: split after ``.``, ``!`` or ``?``
    followed by whitespace, except after a listed abbreviation, a single
    capital initial or a bare number."""
    pieces = [p for p in _SENTENCE_SPLIT.split(text) if p]
    out: list[str] = []
    for piece in pieces:
        if out and _ABBREVIATIONS.search(out[-1]):
            out[-1] = out[-1] + " " + piece
        else:
            out.append(piece)
    return tuple(out)


def claim_rule_matches(sentence: str) -> tuple[str, ...]:
    """The names of the :data:`CLAIM_RULES` the sentence satisfies, in rule order."""
    return tuple(
        name for name, patterns in CLAIM_RULES.items() if any(p.search(sentence) for p in patterns)
    )


def locate(text: str, needle: str) -> tuple[int, int] | None:
    """Offsets of the first occurrence of *needle* in *text*, or ``None``."""
    if not needle:
        return None
    i = text.find(needle)
    return None if i < 0 else (i, i + len(needle))


# --------------------------------------------------------------------------- #
# Accounting
# --------------------------------------------------------------------------- #


def nonws_len(text: str) -> int:
    """Characters that are not whitespace: the unit in which losses are counted,
    because every normalisation here moves whitespace and nothing else."""
    return len(re.sub(r"\s", "", text))


def page_accounting(page: PageExtract) -> dict[str, int]:
    """Non-whitespace characters of the page text against those the blocks
    and table cells carry. ``loss`` is what the import dropped (positive) or
    duplicated (negative); zero is the expected value."""
    accounted = sum(nonws_len(b.text) for b in page.blocks) + sum(
        nonws_len(c) for t in page.tables for r in t.rows for c in r
    )
    chars = nonws_len(page.text)
    return {"page": page.page, "chars": chars, "accounted": accounted, "loss": chars - accounted}


def versions() -> dict[str, str]:
    """The four version strings plus the page-text method, for a manifest."""
    return {
        "extractor": EXTRACTOR_VERSION,
        "normalisation": NORMALISATION_VERSION,
        "table_rendering": TABLE_RENDERING_VERSION,
        "claim_extraction": CLAIM_EXTRACTION_VERSION,
        "page_text_method": PAGE_TEXT_METHOD,
        "table_strategy": TABLE_STRATEGY,
    }
