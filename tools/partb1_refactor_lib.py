"""Editing primitives and validation checks for the FIELDWISE Part B-1 refactoring build.

The build (``tools/build_partb1_refactored.py``) edits the sealed, submitted Part B-1 DOCX
surgically: it replaces, deletes or inserts declared paragraphs and table cells, appends Word
footnotes, swaps the Gantt image, exports the result to PDF through Word, and validates the
PDF. This module holds the reusable, unit-tested pieces of that pipeline; it carries no
proposal content.

Markup accepted by ``parse_markup``:

* ``**bold**`` — a bold run;
* ``[^n]`` — a Word footnote anchor for footnote id ``n`` (any whitespace before the anchor
  is dropped so the superscript sits on the preceding word, as in the sealed document).
  Word accepts one anchor per footnote id; a second anchor to the same id makes Word report the
  file as corrupt, so a citation repeated in the text needs its own footnote.
"""

from __future__ import annotations

import copy
import io
import re
import statistics
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from xml.sax.saxutils import escape

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table, _Cell, _Row
from docx.text.paragraph import Paragraph

W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
FOOTNOTE_REF_STYLE = "Lbjegyzet-hivatkozs"  # the sealed document's 'Footnote Reference' style
FOOTNOTE_PARA_STYLE = "Lbjegyzetszveg"  # its 'Footnote Text' style
FOOTNOTE_CHAR_STYLE = "FootnoteCharacters"
PT_PER_MM = 72 / 25.4


# ---------------------------------------------------------------------------
# Markup
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Segment:
    text: str = ""
    bold: bool = False
    footnote: int | None = None


_MARKUP_RE = re.compile(r"(\*\*.+?\*\*|\[\^\d+\])", re.S)


def parse_markup(markup: str) -> list[Segment]:
    """Split ``markup`` into plain, bold and footnote-anchor segments."""
    markup = re.sub(r"\s+(\[\^\d+\])", r"\1", markup)
    segments: list[Segment] = []
    for part in _MARKUP_RE.split(markup):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            segments.append(Segment(text=part[2:-2], bold=True))
        elif re.fullmatch(r"\[\^\d+\]", part):
            segments.append(Segment(footnote=int(part[2:-1])))
        else:
            segments.append(Segment(text=part))
    return segments


def markup_to_plain(markup: str) -> str:
    """The text an evaluator reads: markup stripped, footnote anchors removed."""
    return "".join(s.text for s in parse_markup(markup))


def _make_run(segment: Segment, footnote_ref_style: str) -> Any:
    run = OxmlElement("w:r")
    if segment.footnote is not None:
        rpr = OxmlElement("w:rPr")
        rstyle = OxmlElement("w:rStyle")
        rstyle.set(qn("w:val"), footnote_ref_style)
        rpr.append(rstyle)
        run.append(rpr)
        ref = OxmlElement("w:footnoteReference")
        ref.set(qn("w:id"), str(segment.footnote))
        run.append(ref)
        return run
    if segment.bold:
        rpr = OxmlElement("w:rPr")
        rpr.append(OxmlElement("w:b"))
        run.append(rpr)
    text = OxmlElement("w:t")
    text.text = segment.text
    if segment.text != segment.text.strip():
        text.set(qn("xml:space"), "preserve")
    run.append(text)
    return run


def set_paragraph_markup(paragraph: Paragraph, markup: str,
                         footnote_ref_style: str = FOOTNOTE_REF_STYLE) -> None:
    """Replace every run of ``paragraph`` with runs built from ``markup``; ``w:pPr`` survives."""
    p = paragraph._p
    for child in list(p):
        if child.tag != qn("w:pPr"):
            p.remove(child)
    for segment in parse_markup(markup):
        p.append(_make_run(segment, footnote_ref_style))


# ---------------------------------------------------------------------------
# Document navigation
# ---------------------------------------------------------------------------
def norm(text: str) -> str:
    text = (text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"')
            .replace("\u201d", '"').replace("\u2013", "-").replace("\u2014", "-")
            .replace("\u00a0", " "))
    return re.sub(r"\s+", " ", text).strip()


def body_blocks(doc) -> list[Paragraph | Table]:
    blocks: list[Paragraph | Table] = []
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            blocks.append(Paragraph(child, doc))
        elif child.tag == qn("w:tbl"):
            blocks.append(Table(child, doc))
    return blocks


def find_paragraph(doc, anchor: str) -> Paragraph:
    """The unique body paragraph whose normalised text starts with ``anchor``."""
    key = norm(anchor)
    hits = [b for b in body_blocks(doc)
            if isinstance(b, Paragraph) and norm(b.text).startswith(key)]
    if len(hits) != 1:
        raise LookupError(f"paragraph anchor {anchor!r}: {len(hits)} matches")
    return hits[0]


def find_table(doc, first_header_cell: str) -> Table:
    key = norm(first_header_cell)
    hits = [b for b in body_blocks(doc)
            if isinstance(b, Table) and norm(row_cells(b.rows[0])[0].text).startswith(key)]
    if len(hits) != 1:
        raise LookupError(f"table anchor {first_header_cell!r}: {len(hits)} matches")
    return hits[0]


def row_cells(row: _Row) -> list[_Cell]:
    """Distinct cells of a row (python-docx repeats merged cells)."""
    return [_Cell(tc, row.table) for tc in row._tr.findall(qn("w:tc"))]


def find_row(table: Table, first_cell_anchor: str) -> _Row:
    key = norm(first_cell_anchor)
    hits = [r for r in table.rows if norm(row_cells(r)[0].text).startswith(key)]
    if len(hits) != 1:
        raise LookupError(f"row anchor {first_cell_anchor!r}: {len(hits)} matches")
    return hits[0]


def delete_paragraph(paragraph: Paragraph) -> None:
    paragraph._p.getparent().remove(paragraph._p)


def strip_word_ids(element) -> None:
    """Drop w14:paraId/w14:textId from a cloned subtree so ids stay unique in the package."""
    for el in element.iter():
        for attr in ("paraId", "textId"):
            el.attrib.pop("{%s}%s" % (W14_NS, attr), None)


def insert_paragraph_after(paragraph: Paragraph, markup: str) -> Paragraph:
    """Insert a new paragraph after ``paragraph`` that inherits its ``w:pPr``."""
    new_p = copy.deepcopy(paragraph._p)
    strip_word_ids(new_p)
    for child in list(new_p):
        if child.tag != qn("w:pPr"):
            new_p.remove(child)
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    set_paragraph_markup(new_para, markup)
    return new_para


def set_cell_markup(cell: _Cell, markup: str) -> None:
    """Set a table cell to one paragraph built from ``markup`` (first paragraph's pPr kept)."""
    paragraphs = cell.paragraphs
    for extra in paragraphs[1:]:
        delete_paragraph(extra)
    set_paragraph_markup(paragraphs[0], markup)


def clone_row_after(table: Table, template_row: _Row, after_row: _Row,
                    cells_markup: Sequence[str]) -> _Row:
    """Deep-copy ``template_row`` (borders, widths, cantSplit), fill it, place it after ``after_row``."""
    n_cells = len(template_row._tr.findall(qn("w:tc")))
    if n_cells != len(cells_markup):
        raise ValueError(f"row has {n_cells} cells, {len(cells_markup)} markups given")
    new_tr = copy.deepcopy(template_row._tr)
    strip_word_ids(new_tr)
    after_row._tr.addnext(new_tr)
    new_row = _Row(new_tr, table)
    for cell, markup in zip(row_cells(new_row), cells_markup):
        set_cell_markup(cell, markup)
    return new_row


def delete_row(row: _Row) -> None:
    row._tr.getparent().remove(row._tr)


def column_widths_cm(table: Table) -> list[float]:
    grid = table._tbl.find(qn("w:tblGrid"))
    return [int(col.get(qn("w:w"))) / 567 for col in grid.findall(qn("w:gridCol"))]


def set_column_widths(table: Table, widths_cm: Sequence[float]) -> None:
    """Re-balance a table's columns (grid and every cell width); the total width is unchanged."""
    grid = table._tbl.find(qn("w:tblGrid"))
    cols = grid.findall(qn("w:gridCol"))
    if len(cols) != len(widths_cm):
        raise ValueError(f"table has {len(cols)} columns, {len(widths_cm)} widths given")
    old_total = sum(int(c.get(qn("w:w"))) for c in cols)
    twips = [int(round(w * 567)) for w in widths_cm]
    if abs(sum(twips) - old_total) > 30:
        raise ValueError(f"new widths total {sum(twips)} twips, table is {old_total}")
    for col, w in zip(cols, twips):
        col.set(qn("w:w"), str(w))
    for row in table.rows:
        for cell, w in zip(row_cells(row), twips):
            tcpr = cell._tc.find(qn("w:tcPr"))
            tcw = tcpr.find(qn("w:tcW")) if tcpr is not None else None
            if tcw is not None:
                tcw.set(qn("w:w"), str(w))
                tcw.set(qn("w:type"), "dxa")


# ---------------------------------------------------------------------------
# Footnotes and package post-processing
# ---------------------------------------------------------------------------
def footnote_xml(fid: int, text: str, size_half_pts: int = 18,
                 para_style: str = FOOTNOTE_PARA_STYLE,
                 ref_style: str = FOOTNOTE_CHAR_STYLE) -> str:
    """One ``w:footnote`` element in the sealed document's footnote format (9 pt by default)."""
    rpr_text = (f'<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
                f'<w:sz w:val="{size_half_pts}"/><w:szCs w:val="{size_half_pts}"/></w:rPr>')
    return (f'<w:footnote w:id="{fid}"><w:p><w:pPr><w:pStyle w:val="{para_style}"/>'
            f'<w:spacing w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>'
            f'<w:r><w:rPr><w:rStyle w:val="{ref_style}"/>'
            f'<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
            f'<w:sz w:val="{size_half_pts}"/><w:szCs w:val="{size_half_pts}"/></w:rPr>'
            f'<w:footnoteRef/></w:r>'
            f'<w:r>{rpr_text}<w:t xml:space="preserve"> {escape(text)}</w:t></w:r></w:p></w:footnote>')


def add_footnotes(footnotes_xml: bytes, entries: dict[int, str]) -> bytes:
    """Append footnotes ``entries`` (id -> text) to a ``word/footnotes.xml`` part."""
    xml = footnotes_xml.decode("utf-8")
    existing = {int(m) for m in re.findall(r'<w:footnote [^>]*w:id="(-?\d+)"', xml)}
    for fid in entries:
        if fid in existing:
            raise ValueError(f"footnote id {fid} already exists")
    body = "".join(footnote_xml(fid, text) for fid, text in sorted(entries.items()))
    if "</w:footnotes>" not in xml:
        raise ValueError("not a footnotes part")
    return xml.replace("</w:footnotes>", body + "</w:footnotes>").encode("utf-8")


def rewrite_docx_parts(docx_path: Path, transforms: dict[str, Callable[[bytes], bytes]]) -> None:
    """Rewrite a .docx in place, applying ``transforms[name](bytes) -> bytes`` to named parts."""
    with zipfile.ZipFile(docx_path) as zin:
        items = [(info, zin.read(info.filename)) for info in zin.infolist()]
    names = {info.filename for info, _ in items}
    missing = set(transforms) - names
    if missing:
        raise KeyError(f"parts not in package: {sorted(missing)}")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in items:
            if info.filename in transforms:
                data = transforms[info.filename](data)
            zout.writestr(info.filename, data)
    docx_path.write_bytes(buffer.getvalue())


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
@dataclass
class DocxText:
    paragraphs: list[str] = field(default_factory=list)  # body paragraphs and cell paragraphs
    footnotes: dict[int, str] = field(default_factory=dict)

    @property
    def body(self) -> str:
        return "\n".join(self.paragraphs)

    @property
    def all_text(self) -> str:
        return self.body + "\n" + "\n".join(self.footnotes[k] for k in sorted(self.footnotes))


def docx_text(path: Path) -> DocxText:
    """Body paragraphs, table cells (in document order) and footnotes of a .docx."""
    from docx import Document

    doc = Document(str(path))
    out = DocxText()
    for block in body_blocks(doc):
        if isinstance(block, Paragraph):
            out.paragraphs.append(block.text)
        else:
            for row in block.rows:
                for cell in row_cells(row):
                    out.paragraphs.append(cell.text)
    with zipfile.ZipFile(path) as z:
        if "word/footnotes.xml" in z.namelist():
            from lxml import etree

            root = etree.fromstring(z.read("word/footnotes.xml"))
            w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            for fn in root.findall("{%s}footnote" % w):
                fid = int(fn.get("{%s}id" % w))
                if fid > 0:
                    out.footnotes[fid] = "".join(t.text or "" for t in fn.iter("{%s}t" % w)).strip()
    return out


# ---------------------------------------------------------------------------
# Text checks (pure functions; every failure is a sentence)
# ---------------------------------------------------------------------------
def check_forbidden(text: str, patterns: Iterable[tuple[str, str]]) -> list[str]:
    """``patterns``: (regex, reason). Case-insensitive."""
    failures = []
    for pattern, reason in patterns:
        hits = re.findall(pattern, text, flags=re.IGNORECASE)
        if hits:
            failures.append(f"forbidden ({reason}): {pattern!r} x{len(hits)}")
    return failures


def check_required(text: str, needles: Iterable[tuple[str, str]]) -> list[str]:
    """``needles``: (literal, reason). Case-sensitive, whitespace-normalised."""
    haystack = norm(text)
    return [f"missing ({reason}): {needle!r}" for needle, reason in needles
            if norm(needle) not in haystack]


def check_deliverable_ids(text: str, allowed: set[str]) -> list[str]:
    """Every ``Dn.m`` id in ``text`` must be in ``allowed`` and every allowed id must appear."""
    found = set(re.findall(r"\bD\d\.\d\b", text))
    failures = [f"unexpected deliverable id {d}" for d in sorted(found - allowed)]
    failures += [f"deliverable id never mentioned: {d}" for d in sorted(allowed - found)]
    return failures


_WP_HEADER_RE = re.compile(r"WP(\d)\s+[—–-]\s+(.+?)\s+\|\s+M(\d+)[–-]M(\d+)\s+\|\s+([\d.]+)\s+PM")


def extract_wp_headers(text: str) -> list[tuple[str, str, int, int, float]]:
    return [(f"WP{m.group(1)}", m.group(2), int(m.group(3)), int(m.group(4)), float(m.group(5)))
            for m in _WP_HEADER_RE.finditer(text)]


def check_effort_model(effort: dict[str, list[float]], period_totals: Sequence[float],
                       wp_totals: dict[str, float], grand_total: float,
                       tolerance: float = 0.051) -> list[str]:
    """The fellow-effort matrix (WP -> PM per period) must reproduce the declared totals."""
    failures = []
    periods = len(period_totals)
    for wp, row in effort.items():
        if len(row) != periods:
            failures.append(f"{wp}: {len(row)} periods, expected {periods}")
            continue
        if abs(sum(row) - wp_totals.get(wp, float("nan"))) > tolerance:
            failures.append(f"{wp}: matrix total {sum(row):.1f} != declared {wp_totals.get(wp)}")
    for i, expected in enumerate(period_totals):
        got = sum(row[i] for row in effort.values() if len(row) == periods)
        if abs(got - expected) > tolerance:
            failures.append(f"period {i + 1}: matrix total {got:.1f} != declared {expected}")
    total = sum(sum(row) for row in effort.values())
    if abs(total - grand_total) > tolerance:
        failures.append(f"grand total {total:.1f} != {grand_total}")
    if abs(sum(wp_totals.values()) - grand_total) > tolerance:
        failures.append(f"declared WP totals sum to {sum(wp_totals.values()):.1f}, not {grand_total}")
    return failures


@dataclass(frozen=True)
class Cut:
    cut_id: str
    location: str
    removed: str  # verbatim text that must exist in the baseline and be absent afterwards
    used_by: str
    lines: int


def check_cut_ledger(ledger: Sequence[Cut], baseline_text: str, output_text: str) -> list[str]:
    """Each cut id is used once; its text exists in the baseline and is gone from the output."""
    failures = []
    ids = [c.cut_id for c in ledger]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        failures.append(f"cut {dup} listed more than once")
    base, out = norm(baseline_text), norm(output_text)
    for cut in ledger:
        key = norm(cut.removed)
        if key not in base:
            failures.append(f"{cut.cut_id}: removed text not found in baseline: {cut.removed[:60]!r}")
        if key in out:
            failures.append(f"{cut.cut_id}: text still present in output: {cut.removed[:60]!r}")
    return failures


def sentence_lengths(text: str) -> list[tuple[int, str]]:
    """(word count, sentence) pairs; abbreviations and decimals do not end sentences."""
    guarded = text
    for abbrev in ("Dr.", "Prof.", "et al.", "e.g.", "i.e.", "incl.", "Kft.", "approx.", "vs."):
        guarded = guarded.replace(abbrev, abbrev.replace(".", "\x00"))
    guarded = re.sub(r"(\d)\.(\d)", "\\1\x00\\2", guarded)
    out = []
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(\d\u201c\"])", guarded):
        s = s.replace("\x00", ".").strip()
        if s:
            out.append((len(s.split()), s))
    return out


# ---------------------------------------------------------------------------
# PDF checks
# ---------------------------------------------------------------------------
def _font_embedded(doc, xref: int) -> bool:
    obj = doc.xref_object(xref, compressed=True) or ""
    if obj.strip().startswith("["):  # an indirect DescendantFonts array: follow its first entry
        m = re.search(r"(\d+) 0 R", obj)
        return _font_embedded(doc, int(m.group(1))) if m else False
    descriptor = doc.xref_get_key(xref, "FontDescriptor")
    if descriptor[0] == "xref":
        dxref = int(descriptor[1].split()[0])
        return any(doc.xref_get_key(dxref, key)[0] != "null"
                   for key in ("FontFile", "FontFile2", "FontFile3"))
    # Type0 fonts carry the descriptor on their descendant font
    descendants = doc.xref_get_key(xref, "DescendantFonts")
    m = re.search(r"(\d+) 0 R", descendants[1] or "")
    if m:
        return _font_embedded(doc, int(m.group(1)))
    return False


def pdf_report(pdf_path: Path, expected_pages: int = 10, header_mm: float = 25.0,
               footer_mm: float = 23.0, min_body_pt: float = 11.0, min_other_pt: float = 8.0,
               min_margin_mm: float = 15.0, placeholders: Iterable[str] = ()) -> dict:
    """Mechanical checks of the exported PDF; ``failures`` lists every violated requirement."""
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    report: dict = {"pages": len(doc), "encrypted": doc.is_encrypted, "failures": [],
                    "page_sizes": [], "fonts": {}, "per_page": []}
    if len(doc) != expected_pages:
        report["failures"].append(f"{len(doc)} pages, expected {expected_pages}")
    if doc.is_encrypted:
        report["failures"].append("PDF is encrypted")
    all_text = ""
    for index in range(len(doc)):
        page: Any = doc[index]
        number = index + 1
        width, height = page.rect.width, page.rect.height
        report["page_sizes"].append((round(width, 1), round(height, 1)))
        if abs(width - 595.3) > 1.5 or abs(height - 841.9) > 1.5:
            report["failures"].append(f"page {number}: size {width:.1f}x{height:.1f} pt is not A4")
        for xref, ext, ftype, basefont, name, encoding, *_ in page.get_fonts(full=True):
            embedded = _font_embedded(doc, xref)
            report["fonts"][basefont] = embedded or report["fonts"].get(basefont, False)
        body_bottom, body_top, left, right = 0.0, height, width, 0.0
        min_body, min_other = 99.0, 99.0
        line_tops: list[float] = []
        for block in page.get_text("dict")["blocks"]:
            x0, y0, x1, y1 = block["bbox"]
            in_header = y1 < header_mm * PT_PER_MM
            in_footer = y0 > height - footer_mm * PT_PER_MM
            if block["type"] == 1:  # image
                if not (in_header or in_footer):
                    body_bottom, body_top = max(body_bottom, y1), min(body_top, y0)
                    left, right = min(left, x0), max(right, x1)
                continue
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    superscript = bool(span["flags"] & 1)
                    if in_header or in_footer:
                        continue
                    size = span["size"]
                    body_bottom = max(body_bottom, span["bbox"][3])
                    body_top = min(body_top, span["bbox"][1])
                    left, right = min(left, span["bbox"][0]), max(right, span["bbox"][2])
                    if superscript:
                        continue
                    if "TimesNewRoman" in span["font"] and size >= 10.5:
                        line_tops.append(round(line["bbox"][1], 1))
                    if size >= 10.5:
                        min_body = min(min_body, size)
                    else:
                        min_other = min(min_other, size)
        tops = sorted(set(line_tops))
        gaps = [b - a for a, b in zip(tops, tops[1:]) if 10 < b - a < 16]
        pitch = statistics.median(gaps) if len(gaps) > 3 else 12.7
        text = page.get_text()
        all_text += text
        footer_match = re.search(r"Part B - Page (\d+) of (\d+)", text)
        images = len(page.get_images())
        first_lines = [ln for ln in text.split("\n")
                       if ln.strip() and not ln.startswith(("Call:", "EU Grants", "Part B - Page"))]
        per_page = {
            "page": number,
            "footer": footer_match.group(0) if footer_match else None,
            "body_top_mm": round(body_top / PT_PER_MM, 1),
            "body_bottom_mm": round(body_bottom / PT_PER_MM, 1),
            "slack_lines": round(((height - footer_mm * PT_PER_MM) - body_bottom) / pitch, 1),
            "left_margin_mm": round(left / PT_PER_MM, 1),
            "right_margin_mm": round((width - right) / PT_PER_MM, 1),
            "min_body_pt": None if min_body == 99.0 else round(min_body, 1),
            "min_other_pt": None if min_other == 99.0 else round(min_other, 1),
            "images": images,
            "first_line": first_lines[0][:80] if first_lines else "",
        }
        report["per_page"].append(per_page)
        if not footer_match or footer_match.group(1) != str(number) \
                or footer_match.group(2) != str(expected_pages):
            report["failures"].append(f"page {number}: footer is {per_page['footer']!r}")
        if per_page["min_body_pt"] is not None and per_page["min_body_pt"] < min_body_pt:
            report["failures"].append(f"page {number}: body text {per_page['min_body_pt']} pt")
        if per_page["min_other_pt"] is not None and per_page["min_other_pt"] < min_other_pt:
            report["failures"].append(f"page {number}: small text {per_page['min_other_pt']} pt")
        if per_page["left_margin_mm"] < min_margin_mm - 0.15 \
                or per_page["right_margin_mm"] < min_margin_mm - 1.1:
            # the sealed submission measured R 14.9 mm (0.1 mm rounding, accepted by the ESR);
            # we tolerate the same justified-text overhang, never a narrower page setup
            report["failures"].append(
                f"page {number}: margins L {per_page['left_margin_mm']} / R {per_page['right_margin_mm']} mm")
        if per_page["body_top_mm"] < min_margin_mm or \
                per_page["body_bottom_mm"] > (height / PT_PER_MM) - min_margin_mm:
            report["failures"].append(
                f"page {number}: body spans {per_page['body_top_mm']}-{per_page['body_bottom_mm']} mm")
    for name, embedded in report["fonts"].items():
        if not embedded:
            report["failures"].append(f"font not embedded: {name}")
    for needle in placeholders:
        if needle.lower() in all_text.lower():
            report["failures"].append(f"placeholder string present in PDF: {needle!r}")
    report["text"] = all_text
    return report


# ---------------------------------------------------------------------------
# Word export and page rendering
# ---------------------------------------------------------------------------
def export_pdf_with_word(docx_path: Path, pdf_path: Path) -> int:
    """Export through the installed Word (COM). Returns Word's own page count."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        document = word.Documents.Open(str(docx_path.resolve()), ReadOnly=True,
                                       AddToRecentFiles=False)
        try:
            document.Repaginate()
            pages = int(document.ComputeStatistics(2))  # wdStatisticPages
            document.ExportAsFixedFormat(
                str(pdf_path.resolve()), 17, OpenAfterExport=False, OptimizeFor=0, Range=0,
                Item=0, IncludeDocProps=False, KeepIRM=False, CreateBookmarks=0,
                DocStructureTags=False, BitmapMissingFonts=True, UseISO19005_1=False)
        finally:
            document.Close(0)
    finally:
        word.Quit()
    return pages


def render_pages(pdf_path: Path, out_dir: Path, stem: str, dpi: int = 110) -> list[Path]:
    import pymupdf

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    doc = pymupdf.open(str(pdf_path))
    for index in range(len(doc)):
        page: Any = doc[index]
        target = out_dir / f"{stem}_p{index + 1:02d}.png"
        page.get_pixmap(dpi=dpi).save(str(target))
        paths.append(target)
    return paths


# ---------------------------------------------------------------------------
# Gantt figure (replicates the sealed chart; only the labels are data)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GanttSpec:
    rows: Sequence[tuple[str, Sequence[tuple[int, int]], str]]  # (label, [(start, end)], colour)
    milestones: Sequence[tuple[str, int]]  # (number label, month)
    deliverables_a: Sequence[tuple[str, int]]
    deliverables_b: Sequence[tuple[str, int]]
    months: int = 30


def build_gantt_png(out_path: Path, spec: GanttSpec, size_px: tuple[int, int] = (2125, 975),
                    dpi: int = 200) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(size_px[0] / dpi, size_px[1] / dpi), dpi=dpi)
    labels = [r[0] for r in spec.rows] + ["Milestones", "Deliverables A", "Deliverables B"]
    n = len(labels)
    y_of = {label: n - i for i, label in enumerate(labels)}
    for label, spans, colour in spec.rows:
        for start, end in spans:
            ax.barh(y_of[label], end - start + 1, left=start - 0.5, height=0.42, color=colour,
                    edgecolor="none", zorder=3)
    for text, month in spec.milestones:
        ax.plot(month, y_of["Milestones"], marker="D", markersize=13, markerfacecolor="#e0e0e0",
                markeredgecolor="#333333", markeredgewidth=1.0, linestyle="none", zorder=4)
        ax.annotate(text, (month, y_of["Milestones"]), ha="center", va="center", fontsize=8.5,
                    color="#222222", zorder=5)
    for row_label, items in (("Deliverables A", spec.deliverables_a),
                             ("Deliverables B", spec.deliverables_b)):
        for text, month in items:
            ax.annotate(text, (month, y_of[row_label]), ha="center", va="center", fontsize=9,
                        color="#222222", zorder=5)
    ax.set_yticks([y_of[label] for label in labels])
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlim(0.5, spec.months + 0.5)
    ax.set_ylim(0.4, n + 0.6)
    ax.set_xticks(range(1, spec.months + 1))
    ax.tick_params(axis="x", labelsize=8.5, length=3)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Elapsed project month", fontsize=9.5)
    for month in range(1, spec.months + 1):
        ax.axvline(month + 0.5, color="#e6e6e6", linewidth=0.6, zorder=1)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#bbbbbb")
    fig.subplots_adjust(left=0.245, right=0.985, top=0.97, bottom=0.17)
    fig.savefig(out_path, dpi=dpi, metadata={"Software": None})
    plt.close(fig)
