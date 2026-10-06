"""Render the Tier 5 Part B draft as a readable PDF.

Reads the final export bundle (`docs/tier5_deliverables/final_exports/part_b_json_bundle.json`)
and the Tier 3 call binding, and writes a typeset PDF next to the bundle.

This is a presentation renderer. It adds no content: every paragraph, table and heading in the
output comes from the bundle, and the front matter carries only identity, validation status and
source paths read from Tier 3 and Tier 5 artifacts.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "docs/tier5_deliverables/final_exports/part_b_json_bundle.json"
CALL_BINDING = REPO / "docs/tier3_project_instantiation/call_binding/selected_call.json"
PROJECT_SUMMARY = REPO / "docs/tier3_project_instantiation/project_brief/project_summary.json"
CANDIDATES = REPO / "docs/tier5_deliverables/candidates"
DEFAULT_OUT = REPO / "docs/tier5_deliverables/final_exports/part_b_draft.pdf"


def document_id() -> str:
    """Read the Part B document id from the Tier 5 candidate artifact; never invent one."""
    for p in sorted(CANDIDATES.glob("*_part_b.json")):
        try:
            return json.loads(p.read_text(encoding="utf-8"))["document_id"]
        except Exception:
            continue
    return "part_b"

SECTION_TITLES = {
    "excellence": "Excellence",
    "impact": "Impact",
    "implementation": "Quality and efficiency of the implementation",
}
SECTION_ORDER = ["excellence", "impact", "implementation"]

INK = colors.HexColor("#1A1A1A")
ACCENT = colors.HexColor("#1F4E5F")
RULE = colors.HexColor("#B8C6CC")
MUTED = colors.HexColor("#5A6A70")
BAND = colors.HexColor("#EDF2F4")

STATUS_FILL = {
    "confirmed": colors.HexColor("#E3F0E6"),
    "inferred": colors.HexColor("#FBF2DC"),
    "assumed": colors.HexColor("#FBE9DC"),
    "unresolved": colors.HexColor("#F7DEDE"),
}

PAGE_W, PAGE_H = A4
MARGIN_X = 22 * mm
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X


# --------------------------------------------------------------------------- fonts


def register_fonts() -> tuple[str, str]:
    """Register a serif body face and a sans heading face from the system font directory.

    Cambria is preferred for the body: it carries lining figures, which matter in a document
    that cites identifiers such as EO-02, WP1 and D3.2 on nearly every line. Constantia is the
    fallback, then the built-in Times/Helvetica pair.
    """
    fonts = Path("C:/Windows/Fonts")

    def family(alias: str, faces: list[tuple[str, str, int]]) -> bool:
        try:
            for suffix, filename, index in faces:
                name = alias + suffix
                pdfmetrics.registerFont(TTFont(name, str(fonts / filename), subfontIndex=index))
            pdfmetrics.registerFontFamily(
                alias, normal=alias, bold=alias + "-Bold",
                italic=alias + "-Italic", boldItalic=alias + "-BoldItalic",
            )
            return True
        except Exception:
            return False

    body = "Times-Roman"
    for faces in (
        [("", "cambria.ttc", 0), ("-Bold", "cambriab.ttf", 0),
         ("-Italic", "cambriai.ttf", 0), ("-BoldItalic", "cambriaz.ttf", 0)],
        [("", "constan.ttf", 0), ("-Bold", "constanb.ttf", 0),
         ("-Italic", "constani.ttf", 0), ("-BoldItalic", "constanz.ttf", 0)],
    ):
        if family("Body", faces):
            body = "Body"
            break

    head = "Helvetica"
    if family("Head", [("", "calibri.ttf", 0), ("-Bold", "calibrib.ttf", 0),
                       ("-Italic", "calibrii.ttf", 0), ("-BoldItalic", "calibriz.ttf", 0)]):
        head = "Head"
    return body, head


# --------------------------------------------------------------------------- styles


def build_styles(body: str, head: str) -> dict[str, ParagraphStyle]:
    s: dict[str, ParagraphStyle] = {}
    s["body"] = ParagraphStyle(
        "body", fontName=body, fontSize=10, leading=14.6, alignment=TA_JUSTIFY,
        textColor=INK, spaceAfter=7,
    )
    s["lead"] = ParagraphStyle("lead", parent=s["body"], spaceBefore=2)
    s["bullet"] = ParagraphStyle(
        "bullet", parent=s["body"], leftIndent=9 * mm, bulletIndent=3.5 * mm,
        spaceAfter=3.5, alignment=TA_LEFT,
    )
    s["h1"] = ParagraphStyle(
        "h1", fontName=head + "-Bold", fontSize=19, leading=23, textColor=ACCENT,
        spaceBefore=0, spaceAfter=2,
    )
    s["h1num"] = ParagraphStyle(
        "h1num", fontName=head + "-Bold", fontSize=10, leading=12, textColor=MUTED,
        spaceAfter=3,
    )
    s["h2"] = ParagraphStyle(
        "h2", fontName=head + "-Bold", fontSize=13.5, leading=17, textColor=ACCENT,
        spaceBefore=13, spaceAfter=3, keepWithNext=1,
    )
    s["h3"] = ParagraphStyle(
        "h3", fontName=head + "-Bold", fontSize=11, leading=14, textColor=INK,
        spaceBefore=10, spaceAfter=2, keepWithNext=1,
    )
    s["h4"] = ParagraphStyle(
        "h4", fontName=head + "-BoldItalic", fontSize=10, leading=13, textColor=colors.HexColor("#33444A"),
        spaceBefore=7, spaceAfter=1, keepWithNext=1,
    )
    s["caption"] = ParagraphStyle(
        "caption", fontName=head, fontSize=8, leading=10.5, textColor=MUTED, spaceAfter=8,
    )
    s["th"] = ParagraphStyle(
        "th", fontName=head + "-Bold", fontSize=8, leading=10.2, textColor=colors.white,
        alignment=TA_LEFT,
    )
    s["td"] = ParagraphStyle(
        "td", fontName=head, fontSize=8, leading=10.6, textColor=INK, alignment=TA_LEFT,
    )
    s["cover_kicker"] = ParagraphStyle(
        "cover_kicker", fontName=head + "-Bold", fontSize=10.5, leading=14, textColor=ACCENT,
    )
    s["cover_title"] = ParagraphStyle(
        "cover_title", fontName=head + "-Bold", fontSize=25, leading=30, textColor=INK, spaceAfter=6,
    )
    s["cover_sub"] = ParagraphStyle(
        "cover_sub", fontName=body + "-Italic", fontSize=12.5, leading=17, textColor=colors.HexColor("#33444A"),
    )
    s["cover_meta_k"] = ParagraphStyle(
        "cover_meta_k", fontName=head + "-Bold", fontSize=8.6, leading=12, textColor=MUTED,
    )
    s["cover_meta_v"] = ParagraphStyle(
        "cover_meta_v", fontName=head, fontSize=9.4, leading=12.6, textColor=INK,
    )
    s["note"] = ParagraphStyle(
        "note", fontName=head, fontSize=8.8, leading=12.2, textColor=colors.HexColor("#4A3520"),
    )
    s["toc1"] = ParagraphStyle(
        "toc1", fontName=head + "-Bold", fontSize=10.5, leading=17, textColor=ACCENT, spaceBefore=7,
    )
    s["toc2"] = ParagraphStyle(
        "toc2", fontName=head, fontSize=9.6, leading=14.4, textColor=INK, leftIndent=8 * mm,
    )
    s["toc3"] = ParagraphStyle(
        "toc3", fontName=head, fontSize=9, leading=13, textColor=MUTED, leftIndent=16 * mm,
    )
    s["mono"] = ParagraphStyle(
        "mono", fontName="Courier", fontSize=7.6, leading=10.4, textColor=colors.HexColor("#33444A"),
    )
    return s


# --------------------------------------------------------------------------- inline markup

_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)


def esc(value) -> str:
    """Escape a plain field for placement inside hand-built markup."""
    return html.escape("" if value is None else str(value), quote=False)


def inline(text: str) -> str:
    """Escape XML and convert `**bold**` to reportlab markup. No other inline syntax is used."""
    out = html.escape(text, quote=False)
    return _BOLD.sub(lambda m: "<b>%s</b>" % m.group(1), out)


# --------------------------------------------------------------------------- headings with TOC


class TocParagraph(Paragraph):
    """A heading that registers itself with the document outline and table of contents."""

    def __init__(self, text: str, style: ParagraphStyle, level: int, key: str):
        super().__init__(text, style)
        self.toc_level = level
        self.toc_key = key


class Rule(Flowable):
    def __init__(self, width: float, thickness: float = 0.7, color=RULE, pad: float = 2):
        super().__init__()
        self.width, self.thickness, self.color, self.pad = width, thickness, color, pad
        self.height = thickness + pad

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.pad, self.width, self.pad)


# --------------------------------------------------------------------------- tables


def split_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:|-]+\|?", line.strip()))


CELL_PAD = 10.0  # left + right padding inside a table cell


def _text_width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(re.sub(r"\*\*", "", text), font, size)


def column_widths(
    rows: list[list[str]], total: float, font: str, size: float, head_font: str | None = None
) -> list[float]:
    """Auto-layout the columns the way a browser does.

    Each column reports the width it needs to hold its longest unbreakable word (its minimum)
    and the width it would take on one line (its natural width). Columns are given their
    natural width when the table fits, and otherwise share the available width in proportion
    to how much more than their minimum they want.
    """
    n = max(len(r) for r in rows)
    head_font = head_font or font
    mins, naturals = [], []
    for i in range(n):
        # The header row is set in bold, so it is measured in bold; a label must never wrap
        # mid-word into "Numbe / r".
        cells = [(r[i], head_font if j == 0 else font) for j, r in enumerate(rows) if i < len(r)]
        longest_word = max(
            (_text_width(w, f, size) for c, f in cells for w in (c.split() or [""])), default=0.0
        )
        mins.append(min(total / n, longest_word + CELL_PAD))
        naturals.append(max([_text_width(c, f, size) + CELL_PAD for c, f in cells] or [0.0]))

    if sum(naturals) <= total:
        slack = total - sum(naturals)
        return [w + slack * w / sum(naturals) for w in naturals]

    free = total - sum(mins)
    if free <= 0:
        scale = total / sum(mins)
        return [w * scale for w in mins]
    want = [max(0.0, naturals[i] - mins[i]) for i in range(n)]
    if sum(want) == 0:
        return [total / n] * n
    return [mins[i] + free * want[i] / sum(want) for i in range(n)]


def make_table(rows: list[list[str]], st: dict) -> Table:
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    head, body = rows[0], rows[1:]
    data = [[Paragraph(inline(c), st["th"]) for c in head]]
    data += [[Paragraph(inline(c), st["td"]) for c in r] for r in body]
    widths = column_widths(rows, CONTENT_W, st["td"].fontName, st["td"].fontSize, st["th"].fontName)
    t = Table(data, colWidths=widths, repeatRows=1, splitByRow=1, splitInRow=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), BAND))
    t.setStyle(TableStyle(style))
    return t


# --------------------------------------------------------------------------- markdown block parser


def render_markdown(text: str, st: dict, drop_title: str | None, key_prefix: str) -> list:
    """Turn one sub-section's markdown body into flowables.

    Recognises the constructs the drafter emits: `#`/`##`/`###` headings, pipe tables,
    `-` bullets and paragraphs with `**bold**` run-ins.
    """
    flow: list = []
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    para: list[str] = []
    bullets: list[str] = []
    seq = 0

    def flush_para():
        nonlocal para
        if para:
            flow.append(Paragraph(inline(" ".join(para)), st["body"]))
            para = []

    def flush_bullets():
        nonlocal bullets
        for b in bullets:
            flow.append(Paragraph(inline(b), st["bullet"], bulletText="\u2013"))
        if bullets:
            flow.append(Spacer(1, 4))
        bullets = []

    def flush_all():
        flush_para()
        flush_bullets()

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            flush_all()
            i += 1
            continue

        if line.startswith("|"):
            flush_all()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not is_separator(lines[i]):
                    rows.append(split_row(lines[i]))
                i += 1
            if rows:
                flow.append(Spacer(1, 3))
                flow.append(make_table(rows, st))
                flow.append(Spacer(1, 9))
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_all()
            depth, label = len(m.group(1)), m.group(2).strip()
            norm = re.sub(r"[^a-z0-9]+", "", label.lower())
            # The drafter repeats the sub-section title as its own first heading in most
            # sub-sections, at either depth. The heading is printed once, from the metadata.
            if depth <= 2 and drop_title and norm == drop_title:
                i += 1
                continue
            seq += 1
            key = "%s-%d" % (key_prefix, seq)
            if depth <= 2:
                flow.append(TocParagraph(inline(label), st["h3"], 2, key))
            else:
                flow.append(Paragraph(inline(label), st["h4"]))
            i += 1
            continue

        m = re.match(r"^[-*]\s+(.*)$", line)
        if m:
            flush_para()
            bullets.append(m.group(1).strip())
            i += 1
            continue

        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m:
            flush_para()
            bullets.append("%s. %s" % (m.group(1), m.group(2).strip()))
            i += 1
            continue

        flush_bullets()
        para.append(line)
        i += 1

    flush_all()
    return flow


# --------------------------------------------------------------------------- front matter


def kv_table(pairs: list[tuple[str, str]], st: dict) -> Table:
    """Values arrive as finished markup, so they are placed verbatim; callers escape their fields."""
    data = [[Paragraph(k.upper(), st["cover_meta_k"]), Paragraph(v, st["cover_meta_v"])] for k, v in pairs]
    t = Table(data, colWidths=[36 * mm, CONTENT_W - 36 * mm], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -2), 0.35, RULE),
            ]
        )
    )
    return t


def cover(bundle: dict, call: dict, summary: dict, st: dict) -> list:
    concept = summary.get("concept", {}) or {}
    title = concept.get("working_title") or "Part B technical description"
    acronym = concept.get("acronym")
    duration = call.get("project_duration_months")
    flow: list = [
        Spacer(1, 16 * mm),
        Paragraph("Horizon Europe &mdash; Research and Innovation Action", st["cover_kicker"]),
        Paragraph("Part B: technical description", st["cover_kicker"]),
        Spacer(1, 10 * mm),
        Rule(CONTENT_W, thickness=1.6, color=ACCENT, pad=0),
        Spacer(1, 7 * mm),
        Paragraph(inline(title), st["cover_title"]),
        Paragraph(inline(concept.get("one_line", "")), st["cover_sub"]),
        Spacer(1, 11 * mm),
        kv_table(
            [
                ("Topic", "%s<br/>%s" % (esc(call.get("topic_code")), esc(call.get("topic_title")))),
                ("Call", "%s &mdash; %s" % (esc(call.get("call_id")), esc(call.get("call_name")))),
                ("Destination", esc(call.get("destination"))),
                ("Type of action", "%s (%s), %s budget regime"
                 % (esc(call.get("type_of_action")), esc(call.get("instrument_type")),
                    esc(str(call.get("budget_regime", "")).replace("_", " ")))),
                ("Duration", "%s months" % duration if duration else "not set"),
                ("Call deadline", "%s, %s" % (esc(call.get("submission_deadline")),
                                              esc(call.get("submission_deadline_time")))),
                ("Acronym", esc(acronym) if acronym else "none coined (%s)"
                 % esc(str(concept.get("acronym_status", "")).lower())),
                ("Document", esc(document_id()) + " &mdash; Part B draft"),
                ("Source", esc("docs/tier5_deliverables/final_exports/part_b_json_bundle.json")),
            ],
            st,
        ),
        Spacer(1, 12 * mm),
    ]
    note = (
        "<b>Draft status.</b> This is an orchestration demonstration draft, not a submission. "
        "Every section carries an overall validation status of <i>assumed</i>: the call framing is "
        "confirmed against the work programme, while partners, effort and most implementation detail "
        "are pseudonymous placeholders. The status page overleaf gives the claim counts per section."
    )
    box = Table([[Paragraph(note, st["note"])]], colWidths=[CONTENT_W], hAlign="LEFT")
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBF2DC")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D8B96A")),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flow.append(box)
    return flow


def status_page(bundle: dict, st: dict) -> list:
    flow: list = [
        TocParagraph("Document status and provenance", st["h1"], 0, "status"),
        Rule(CONTENT_W, thickness=1.2, color=ACCENT),
        Spacer(1, 6),
    ]

    rows = [["Section", "Overall status", "Confirmed", "Inferred", "Assumed", "Unresolved", "Words"]]
    for sid in SECTION_ORDER:
        sec = bundle["sections_content"][sid]
        counts = Counter(c["status"] for c in sec["validation_status"].get("claim_statuses", []))
        words = sum(ss.get("word_count", 0) for ss in sec["sub_sections"])
        rows.append(
            [
                SECTION_TITLES[sid],
                str(sec["validation_status"].get("overall_status", "")).title(),
                str(counts.get("confirmed", 0)),
                str(counts.get("inferred", 0)),
                str(counts.get("assumed", 0)),
                str(counts.get("unresolved", 0)),
                "{:,}".format(words),
            ]
        )
    flow.append(Paragraph("Claim status per section", st["h3"]))
    flow.append(
        Paragraph(
            "Counts come from the <i>validation_status</i> block of each section artifact. A section's "
            "overall status is the weakest status among its claims.",
            st["caption"],
        )
    )
    widths = [52 * mm, 24 * mm] + [17 * mm] * 4 + [CONTENT_W - 52 * mm - 24 * mm - 4 * 17 * mm]
    t = Table(
        [[Paragraph(inline(c), st["th"] if i == 0 else st["td"]) for c in r] for i, r in enumerate(rows)],
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
    )
    tstyle = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
        ("ALIGN", (2, 1), (-1, -1), "CENTER"),
    ]
    for i in range(1, len(rows)):
        tstyle.append(("BACKGROUND", (1, i), (1, i), STATUS_FILL.get(rows[i][1].lower(), BAND)))
    t.setStyle(TableStyle(tstyle))
    flow += [t, Spacer(1, 12)]

    log = bundle["assembled_draft"].get("consistency_log", [])
    if log:
        flow.append(Paragraph("Cross-section consistency checks", st["h3"]))
        flow.append(
            Paragraph(
                "Recorded by the assembly step. A finding is reproduced in the cell, so the table "
                "answers its own question.",
                st["caption"],
            )
        )
        rows = [["Check", "What it compares", "Result", "Finding"]]
        for e in log:
            rows.append(
                [
                    e.get("check_id", ""),
                    e.get("description", ""),
                    str(e.get("status", "")).replace("_", " "),
                    e.get("inconsistency_note") or "\u2014",
                ]
            )
        widths = [14 * mm, 74 * mm, 22 * mm, CONTENT_W - 110 * mm]
        data = [[Paragraph(inline(c), st["th"] if i == 0 else st["td"]) for c in r] for i, r in enumerate(rows)]
        ct = Table(data, colWidths=widths, repeatRows=1, splitByRow=1, splitInRow=1, hAlign="LEFT")
        cstyle = [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("BOX", (0, 0), (-1, -1), 0.6, RULE),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
        ]
        for i in range(1, len(rows)):
            if i % 2 == 0:
                cstyle.append(("BACKGROUND", (0, i), (-1, i), BAND))
        ct.setStyle(TableStyle(cstyle))
        flow += [ct, Spacer(1, 12)]

    footer = bundle["assembled_draft"].get("traceability_footer", {})
    sources = footer.get("primary_sources", [])
    if sources:
        flow.append(Paragraph("Primary sources", st["h3"]))
        for p in sources:
            flow.append(Paragraph(p, st["mono"]))
        flow.append(Spacer(1, 6))
    if footer.get("derivation_note"):
        flow.append(Paragraph("<i>%s</i>" % inline(footer["derivation_note"]), st["caption"]))
    return flow


def toc_page(st: dict) -> list:
    toc = TableOfContents()
    toc.levelStyles = [st["toc1"], st["toc2"], st["toc3"]]
    toc.dotsMinLevel = 1
    return [
        Paragraph("Contents", st["h1"]),
        Rule(CONTENT_W, thickness=1.2, color=ACCENT),
        Spacer(1, 8),
        toc,
    ]


# --------------------------------------------------------------------------- document


class PartBDoc(BaseDocTemplate):
    def __init__(self, path: str, footer_text: str, head_font: str, **kw):
        super().__init__(path, pagesize=A4, **kw)
        self.footer_text = footer_text
        self.head_font = head_font
        frame = Frame(
            MARGIN_X, MARGIN_BOTTOM, CONTENT_W,
            PAGE_H - MARGIN_TOP - MARGIN_BOTTOM, id="body",
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[frame]),
                PageTemplate(id="body", frames=[frame], onPage=self._furniture),
            ]
        )

    def _furniture(self, canv, doc):
        canv.saveState()
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.5)
        y = MARGIN_BOTTOM - 6 * mm
        canv.line(MARGIN_X, y, PAGE_W - MARGIN_X, y)
        canv.setFont(self.head_font, 7.6)
        canv.setFillColor(MUTED)
        canv.drawString(MARGIN_X, y - 9, self.footer_text)
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, TocParagraph):
            self.notify("TOCEntry", (flowable.toc_level, flowable.getPlainText(), self.page, flowable.toc_key))
            self.canv.bookmarkPage(flowable.toc_key)
            self.canv.addOutlineEntry(
                flowable.getPlainText()[:120], flowable.toc_key, level=flowable.toc_level, closed=flowable.toc_level > 0
            )


class NumberedCanvas(pdfcanvas.Canvas):
    """Two-pass canvas so the footer can print 'page n of N'."""

    def __init__(self, *a, **kw):
        self.head_font = kw.pop("head_font", "Helvetica")
        super().__init__(*a, **kw)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.saveState()
                self.setFont(self.head_font, 7.6)
                self.setFillColor(MUTED)
                y = MARGIN_BOTTOM - 6 * mm - 9
                self.drawRightString(
                    PAGE_W - MARGIN_X, y, "Page %d of %d" % (self._pageNumber, total)
                )
                self.restoreState()
            super().showPage()
        super().save()


def build(bundle_path: Path, out_path: Path) -> tuple[Path, int]:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    call = json.loads(CALL_BINDING.read_text(encoding="utf-8"))
    summary = json.loads(PROJECT_SUMMARY.read_text(encoding="utf-8"))

    body_font, head_font = register_fonts()
    st = build_styles(body_font, head_font)

    story: list = [NextPageTemplate("body")]
    story += cover(bundle, call, summary, st)
    story.append(PageBreak())
    story += toc_page(st)
    story.append(PageBreak())
    story += status_page(bundle, st)

    total_words = 0
    for n, sid in enumerate(SECTION_ORDER, start=1):
        sec = bundle["sections_content"][sid]
        story.append(PageBreak())
        story.append(Paragraph("Section %d" % n, st["h1num"]))
        story.append(TocParagraph("%d. %s" % (n, SECTION_TITLES[sid]), st["h1"], 0, "sec-%s" % sid))
        story.append(Rule(CONTENT_W, thickness=1.2, color=ACCENT))
        story.append(Spacer(1, 7))
        for ss in sec["sub_sections"]:
            sid_label = ss.get("sub_section_id", "")
            title = ss.get("title", "")
            words = ss.get("word_count")
            total_words += words or 0
            key = "ss-%s" % re.sub(r"\W+", "-", str(sid_label))
            heading = TocParagraph(inline("%s  %s" % (sid_label, title)), st["h2"], 1, key)
            caption = Paragraph("%s words" % "{:,}".format(words) if words else "", st["caption"])
            story.append(KeepTogether([heading, caption]))
            drop = re.sub(r"[^a-z0-9]+", "", ("%s %s" % (sid_label, title)).lower())
            story += render_markdown(ss.get("content", ""), st, drop, key)

    doc = PartBDoc(
        str(out_path),
        footer_text="Part B draft \u00b7 %s \u00b7 %s"
        % (document_id(), call.get("topic_code", "")),
        head_font=head_font,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="Part B technical description \u2014 %s" % call.get("topic_code", ""),
        author="Horizon Europe Proposal Orchestration System",
        subject=call.get("topic_title", ""),
    )
    doc.multiBuild(story, canvasmaker=lambda *a, **kw: NumberedCanvas(*a, head_font=head_font, **kw))
    return out_path, total_words


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, default=BUNDLE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    path, words = build(args.bundle, args.out)
    size_kb = path.stat().st_size / 1024
    print("wrote %s (%.0f KB, %s words of draft prose)" % (path, size_kb, "{:,}".format(words)))


if __name__ == "__main__":
    main()
