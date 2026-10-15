"""Source intake for the anonymisation pipeline, stage A0 (AN4).

AN4 of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A0 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. Before anything is
edited, the pipeline pins the document it will edit and records what that
document measurably carries. Stage A6 later compares the derivative against
that record, the **reference inventory**.

The route (operator decision O1)
--------------------------------
O1 adopted the handoff's default: edit the Word source if it renders to the
submitted PDF, otherwise edit the submitted PDF in place. So :func:`intake`
takes the submitted PDF always, and a Word source optionally:

* **Word route.** The operator supplies the source and a PDF they rendered from
  it, each with the hash they declared for it. :func:`render_check` compares
  the render with the pinned PDF on page count, heading markers and their
  pages, and the table inventory. Any difference refuses the source, and
  nothing is written. This module does not render: no renderer is guaranteed
  on the private host, and the render's binding to the source is the
  operator's act, recorded by both hashes. A "render" whose bytes are the
  submitted PDF's is refused, because it proves nothing about the source.
* **PDF route.** No source, so the submitted PDF is the edit target.
  :func:`apply_span_edits` is its edit harness, and it runs only against an
  intake record whose route is the submitted PDF. It redacts a span and
  inserts replacement text in the span's own box, at the span's point size and
  on its baseline. A write that lands at another size is refused. A
  replacement wider than the box at the span's point size overflows its
  length budget and is refused,
  because a longer text would reflow the page and break stage A6's comparison.
  The replacement is set in Helvetica whatever the original font was; the
  edit log records the original fonts so stage A6 can explain the change.

A refused Word source does not fall back silently. The operator re-runs intake
without it, and the record then says the route is the submitted PDF. The Word
route's own edit harness is not built here: AN4 asks for its render check
only, so the stage that first edits a Word source must add it.

What is private
---------------
Everything this module writes. The reference inventory quotes headings and
table headers, so it may never enter this repository. :data:`THIS_REPOSITORY`
is measured from this module's own location, never taken from an argument, and
every input and output path inside it is refused (the V17/V18 pattern). The
intake record holds hashes, counts and the route. It quotes no text and names
no file, because a file name can carry the acronym.

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate, invokes no model, writes no Tier 5 artifact and declares no
fact it did not measure (CLAUDE.md §13.3). It is not a §17.5.3 deterministic
component: no manifest node binds it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, Optional, Sequence

from runner.atomic_write import atomic_write_text, atomic_write_via, canonical_json_bytes
from runner.dry_import import measure

# Measured from that module's own location, never from an argument or the
# working directory (the V17/V18 rule): the pipeline runs from the private
# network.
from runner.original_configuration import THIS_REPOSITORY, inside_this_repository

#: Schema of the intake record.
SCHEMA = "anonymisation_source_intake/1"
RECORD_TYPE = "anonymisation_source_intake"

INTAKE_RECORD_FILE = "source_intake.json"
REFERENCE_INVENTORY_FILE = "reference_inventory.json"

#: What the render check compares, in order.
RENDER_CHECKS: tuple[str, ...] = ("page_count", "headings", "tables")

#: The font the edit harness writes replacement text in. A base-14 font, so
#: the derivative embeds nothing new and the measured width is exact.
REPLACEMENT_FONT = "helv"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_ROUTE_BASIS = {
    "word_source": (
        "Operator decision O1: edit the Word source if it renders to the submitted PDF. The "
        "render check found no difference in page count, headings or tables."
    ),
    "submitted_pdf": (
        "Operator decision O1: edit the submitted PDF in place when no Word source renders to "
        "it. No Word source was supplied to this intake."
    ),
}

_RENDER_BASIS = (
    "The operator rendered the Word source to PDF. This intake compared that render with the "
    "pinned PDF and did not render the source itself, so the render's binding to the source "
    "rests on the operator and on the two hashes recorded here."
)


class IntakeRefused(RuntimeError):
    """Refusal: a path, a hash or an edit is not admissible. Nothing was written."""


class RenderMismatch(IntakeRefused):
    """The Word source's render differs from the pinned PDF."""

    def __init__(self, findings: list[dict[str, Any]]) -> None:
        self.findings = findings
        checks = sorted({f["check"] for f in findings})
        super().__init__(
            f"the Word source does not render to the submitted PDF ({len(findings)} "
            f"difference(s) in {', '.join(checks)}). Under O1 the source is refused; re-run "
            f"intake without it to edit the submitted PDF in place."
        )


class ReplacementOverflow(IntakeRefused):
    """A replacement does not fit the box of the span it replaces."""


@dataclass(frozen=True)
class IntakeResult:
    route: str
    intake_record: Path
    reference_inventory: Path


@dataclass(frozen=True)
class WordSource:
    """The Word source, the PDF the operator rendered from it, and both pins."""

    source: Path
    source_sha256: str
    render: Path
    render_sha256: str


@dataclass(frozen=True)
class SpanEdit:
    """Replace the text inside *rect* on *page* (1-based) with *replacement*."""

    page: int
    rect: tuple[float, float, float, float]
    replacement: str


# --------------------------------------------------------------------------- #
# Paths and pins
# --------------------------------------------------------------------------- #


def require_private(path: Path, what: str) -> Path:
    """*path* resolved, refused if it is inside this repository."""
    if inside_this_repository(path):
        raise IntakeRefused(
            f"{what} {Path(path).name!r} resolves inside this repository "
            f"({THIS_REPOSITORY.name}). The original, its edits and its inventories stay in the "
            f"private network, and no argument moves where here is."
        )
    return Path(path).expanduser().resolve()


def pin(path: Path, expected_sha256: str, what: str) -> str:
    """The hash of *path*, refused unless it is the one the operator declared."""
    if not _SHA256.match(expected_sha256 or ""):
        raise IntakeRefused(
            f"the expected hash for {what} is not a sha256: 64 lower-case hex digits are "
            f"required, taken from the authoritative source rather than from this file."
        )
    if not Path(path).is_file():
        raise IntakeRefused(f"{what} is not a file, so there is nothing to pin")
    measured = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if measured != expected_sha256:
        raise IntakeRefused(
            f"{what} hashes to {measured} and the operator declared {expected_sha256}: this is "
            f"not the pinned file. Nothing was written."
        )
    return measured


# --------------------------------------------------------------------------- #
# The Word route: the render check
# --------------------------------------------------------------------------- #


class _Heading(NamedTuple):
    marker: str
    page: int
    text: str


class _Table(NamedTuple):
    page: int
    rows: int
    cols: int
    header: tuple[str, ...]


def _headings(inventory: dict[str, Any]) -> list[_Heading]:
    return [
        _Heading(h["marker"], int(h["page"]), h["text"]) for h in inventory["heading_candidates"]
    ]


def _tables(inventory: dict[str, Any]) -> list[_Table]:
    return [
        _Table(int(t["page"]), int(t["rows"]), int(t["cols"]), tuple(t["header"]))
        for t in inventory["tables"]["per_table"]
    ]


def _compare(
    check: str, pinned: Sequence[NamedTuple], rendered: Sequence[NamedTuple], quoted: str
) -> list[dict[str, Any]]:
    """Count, then position by position. The *quoted* field is compared, not reported."""
    findings: list[dict[str, Any]] = []
    if len(pinned) != len(rendered):
        findings.append(
            {"check": check, "pinned_count": len(pinned), "rendered_count": len(rendered)}
        )
    for index, (mine, theirs) in enumerate(zip(pinned, rendered)):
        if mine != theirs:
            shown = [f for f in mine._fields if f != quoted]
            findings.append(
                {
                    "check": check,
                    "index": index,
                    "pinned": {f: getattr(mine, f) for f in shown},
                    "rendered": {f: getattr(theirs, f) for f in shown},
                    f"{quoted}_differs": getattr(mine, quoted) != getattr(theirs, quoted),
                }
            )
    return findings


def render_check(pinned: dict[str, Any], rendered: dict[str, Any]) -> list[dict[str, Any]]:
    """Differences between two dry-import inventories, on :data:`RENDER_CHECKS`.

    Pure. A finding names the check, the position and the measured markers,
    pages and shapes. It quotes no heading text and no table header: those are
    compared, never reported.
    """
    findings: list[dict[str, Any]] = []
    if pinned["pages"] != rendered["pages"]:
        findings.append(
            {"check": "page_count", "pinned": pinned["pages"], "rendered": rendered["pages"]}
        )
    findings += _compare("headings", _headings(pinned), _headings(rendered), "text")
    findings += _compare("tables", _tables(pinned), _tables(rendered), "header")
    return findings


# --------------------------------------------------------------------------- #
# Intake
# --------------------------------------------------------------------------- #


def _record(
    *,
    route: str,
    pdf_sha256: str,
    pdf_bytes: int,
    inventory_bytes: bytes,
    inventory: dict[str, Any],
    word: Optional[dict[str, Any]],
    render: Optional[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "record_type": RECORD_TYPE,
        "stage": "A0",
        "purpose": (
            "Pins the document the anonymisation pipeline edits, names the edit route, and binds "
            "the reference inventory that stage A6 compares the derivative against."
        ),
        "input": {
            "sha256": pdf_sha256,
            "bytes": pdf_bytes,
            "basis": "authenticated",
            "basis_statement": (
                "The file hashed to the value the operator declared from the authoritative "
                "source. Its name is not recorded, because a file name can carry the acronym."
            ),
        },
        "route": route,
        "route_basis": _ROUTE_BASIS[route],
        "word_source": word,
        "render_check": render,
        "reference_inventory": {
            "file": REFERENCE_INVENTORY_FILE,
            "sha256": hashlib.sha256(inventory_bytes).hexdigest(),
            "pages": inventory["pages"],
            "heading_candidates": len(inventory["heading_candidates"]),
            "tables": inventory["tables"]["count"],
            "measured_by": "runner.dry_import.measure",
        },
        "privacy": {
            "declared_status": "Confirmed",
            "claim": (
                "This record holds hashes, counts and the route only. The reference inventory "
                "beside it quotes headings and table headers and stays in the private network "
                "with it."
            ),
            "basis": "Every path this intake wrote to was refused if it resolved inside the repository.",
        },
    }


def intake(
    *,
    pdf: Path,
    expected_sha256: str,
    out_dir: Path,
    word: Optional[WordSource] = None,
) -> IntakeResult:
    """Pin *pdf*, choose the route under O1 and write the reference inventory.

    Writes :data:`INTAKE_RECORD_FILE` and :data:`REFERENCE_INVENTORY_FILE` into
    *out_dir*. Every refusal runs before the first write. A re-run that would
    write the same bytes is a no-op; one that would write different bytes is
    refused, because a pinned intake is never overwritten.
    """
    pdf = require_private(pdf, "the submitted PDF")
    out_dir = require_private(out_dir, "the intake directory")
    pdf_sha = pin(pdf, expected_sha256, "the submitted PDF")
    inventory = measure(pdf)

    word_record: Optional[dict[str, Any]] = None
    render: Optional[dict[str, Any]] = None
    route = "submitted_pdf"
    if word is not None:
        source = require_private(word.source, "the Word source")
        rendered = require_private(word.render, "the Word source's render")
        source_sha = pin(source, word.source_sha256, "the Word source")
        render_sha = pin(rendered, word.render_sha256, "the Word source's render")
        if render_sha == pdf_sha:
            raise IntakeRefused(
                "the Word source's render has the submitted PDF's own bytes. A copy of the PDF "
                "proves nothing about the source; render the source and pin that render."
            )
        findings = render_check(inventory, measure(rendered))
        if findings:
            raise RenderMismatch(findings)
        route = "word_source"
        word_record = {
            "sha256": source_sha,
            "render_sha256": render_sha,
            "render_basis": _RENDER_BASIS,
        }
        render = {"compared": list(RENDER_CHECKS), "findings": []}

    inventory_bytes = canonical_json_bytes(inventory)
    record = _record(
        route=route,
        pdf_sha256=pdf_sha,
        pdf_bytes=pdf.stat().st_size,
        inventory_bytes=inventory_bytes,
        inventory=inventory,
        word=word_record,
        render=render,
    )
    files = {
        REFERENCE_INVENTORY_FILE: inventory_bytes,
        INTAKE_RECORD_FILE: canonical_json_bytes(record),
    }
    for name, data in files.items():
        existing = out_dir / name
        if existing.exists() and existing.read_bytes() != data:
            raise IntakeRefused(
                f"{out_dir.name} already holds a pinned intake that differs from this one "
                f"({name}). Either the input differs or the extraction environment the "
                f"inventory records has changed. A pinned intake is never overwritten; intake "
                f"into a new directory."
            )
    for name, data in files.items():
        if not (out_dir / name).exists():
            atomic_write_text(data.decode("utf-8"), out_dir / name)
    return IntakeResult(
        route=route,
        intake_record=out_dir / INTAKE_RECORD_FILE,
        reference_inventory=out_dir / REFERENCE_INVENTORY_FILE,
    )


# --------------------------------------------------------------------------- #
# The PDF route: the edit harness
# --------------------------------------------------------------------------- #


class _Char(NamedTuple):
    c: str
    size: float
    font: str
    x: float
    baseline: float


def _chars_in(page: Any, rect: Any) -> list[_Char]:
    """Each non-space character whose box centre lies in *rect*, with its size and font."""
    out: list[_Char] = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", ()):
            for span in line["spans"]:
                for char in span["chars"]:
                    if char["c"].isspace():
                        continue
                    x0, y0, x1, y1 = char["bbox"]
                    if rect.x0 <= (x0 + x1) / 2 <= rect.x1 and rect.y0 <= (y0 + y1) / 2 <= rect.y1:
                        out.append(_Char(char["c"], round(float(span["size"]), 2), span["font"],
                                         float(x0), round(float(char["origin"][1]), 3)))
    return out


def _baseline(chars: Sequence[_Char]) -> float:
    """The baseline the span's first character sits on."""
    return min(chars, key=lambda char: char.x).baseline


def _check_edit(doc: Any, index: int, edit: SpanEdit) -> dict[str, Any]:
    import pymupdf

    where = f"edit {index} (page {edit.page})"
    if not 1 <= edit.page <= doc.page_count:
        raise IntakeRefused(f"{where}: the document has no page {edit.page}")
    if "\n" in edit.replacement or "\r" in edit.replacement:
        raise IntakeRefused(f"{where}: a replacement is one line; split it into one edit per line")
    page = doc[edit.page - 1]
    rect = pymupdf.Rect(edit.rect)
    if rect.is_empty or not page.rect.contains(rect):
        raise IntakeRefused(f"{where}: the span's box is empty or leaves the page")
    chars = _chars_in(page, rect)
    sizes = {char.size for char in chars}
    if not sizes:
        raise IntakeRefused(f"{where}: the span's box holds no character to replace")
    if len(sizes) > 1:
        raise IntakeRefused(
            f"{where}: the span's box holds text in more than one point size "
            f"({sorted(sizes)}); a replacement is written in one"
        )
    size = sizes.pop()
    used = pymupdf.get_text_length(edit.replacement, fontname=REPLACEMENT_FONT, fontsize=size)
    budget = rect.width
    if used > budget + 1e-6:
        raise ReplacementOverflow(
            f"{where}: the replacement is {used:.1f} pt wide at {size} pt and the span's box is "
            f"{budget:.1f} pt. It overflows its length budget and would reflow the page."
        )
    return {
        "edit": index,
        "page": edit.page,
        "rect": [round(v, 3) for v in (rect.x0, rect.y0, rect.x1, rect.y1)],
        "point_size": size,
        "font": REPLACEMENT_FONT,
        # A font name is a typeface, not a person; A6 reads it to explain a change of face.
        "original_fonts": sorted({char.font for char in chars}),
        "budget_points": round(budget, 3),
        "used_points": round(used, 3),
    }


def require_pdf_route(intake_record: Path) -> str:
    """The pinned hash from *intake_record*, refused unless its route is the PDF."""
    intake_record = require_private(intake_record, "the intake record")
    try:
        record = json.loads(intake_record.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise IntakeRefused(f"the intake record could not be read: {exc}") from exc
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise IntakeRefused(f"the intake record is not an {SCHEMA} record")
    if record.get("route") != "submitted_pdf":
        raise IntakeRefused(
            f"the intake chose the route {record.get('route')!r}. The PDF edit harness edits "
            f"only a document whose intake chose the submitted PDF (O1)."
        )
    return str(record["input"]["sha256"])


def apply_span_edits(
    pdf: Path, intake_record: Path, edits: Sequence[SpanEdit], out_pdf: Path
) -> list[dict[str, Any]]:
    """Apply *edits* to the PDF *intake_record* pinned and write it to *out_pdf*.

    The intake record must have chosen the submitted-PDF route, and *pdf* must
    hash to the value it pinned. Every edit is checked before any is applied,
    so one refusal writes nothing.
    Images and vector drawings under a span are left in place: only text is
    redacted. The returned edit log carries locations, sizes, widths and font
    names, and no text, original or replacement.
    """
    pdf = require_private(pdf, "the PDF to edit")
    out_pdf = require_private(out_pdf, "the edited PDF")
    pin(pdf, require_pdf_route(intake_record), "the PDF to edit")
    return _apply(pdf, edits, out_pdf)


def apply_stage_edits(
    pdf: Path, intake_record: Path, expected_sha256: str, edits: Sequence[SpanEdit],
    out_pdf: Path,
) -> list[dict[str, Any]]:
    """Apply *edits* to a stage's output and write it to *out_pdf*.

    The harness of :func:`apply_span_edits`, for a later stage that edits an
    earlier stage's derivative rather than the intake PDF. The intake record
    must still have chosen the submitted-PDF route. *pdf* must hash to
    *expected_sha256*, which the caller takes from the record of the stage
    that wrote it, never from the file itself.
    """
    pdf = require_private(pdf, "the PDF to edit")
    out_pdf = require_private(out_pdf, "the edited PDF")
    require_pdf_route(intake_record)
    pin(pdf, expected_sha256, "the stage output to edit")
    return _apply(pdf, edits, out_pdf)


def _apply(pdf: Path, edits: Sequence[SpanEdit], out_pdf: Path) -> list[dict[str, Any]]:
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        log = [_check_edit(doc, index, edit) for index, edit in enumerate(edits)]
        by_page: dict[int, list[tuple[SpanEdit, dict[str, Any]]]] = {}
        for edit, entry in zip(edits, log):
            by_page.setdefault(edit.page, []).append((edit, entry))
        for number, items in sorted(by_page.items()):
            rects = [pymupdf.Rect(edit.rect) for edit, _ in items]
            for i, a in enumerate(rects):
                for b in rects[i + 1:]:
                    if a.intersects(b):
                        raise IntakeRefused(
                            f"page {number}: two spans overlap; each character is replaced once"
                        )
            page = doc[number - 1]
            baselines = [_baseline(_chars_in(page, pymupdf.Rect(edit.rect))) for edit, _ in items]
            for edit, _ in items:
                # No text here: PyMuPDF writes redaction text with insert_textbox,
                # which needs more height than a one-line box gives and shrinks
                # the size until it fits (10 pt became 8.5 pt). The replacement
                # is written below instead, at the span's own size and baseline.
                page.add_redact_annot(
                    pymupdf.Rect(edit.rect),
                    # False, not None: None paints a white box, a drawing A6 would count.
                    fill=False,  # type: ignore[arg-type]
                )
            # Text only: a logo, a figure or a table rule under a span stays.
            # The constants exist at run time; PyMuPDF's stubs omit them.
            page.apply_redactions(
                images=pymupdf.PDF_REDACT_IMAGE_NONE,  # type: ignore[attr-defined]
                graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,  # type: ignore[attr-defined]
                text=pymupdf.PDF_REDACT_TEXT_REMOVE,  # type: ignore[attr-defined]
            )
            for (edit, entry), baseline in zip(items, baselines):
                if edit.replacement:
                    page.insert_text(
                        (edit.rect[0], baseline),
                        edit.replacement,
                        fontname=REPLACEMENT_FONT,
                        fontsize=entry["point_size"],
                    )
            for edit, entry in items:
                chars = _chars_in(page, pymupdf.Rect(edit.rect))
                if "".join(char.c for char in chars) != "".join(edit.replacement.split()):
                    raise ReplacementOverflow(
                        f"edit {entry['edit']} (page {number}): the replacement was not written "
                        f"whole inside the span's box, so it did not fit"
                    )
                if {char.size for char in chars} - {entry["point_size"]}:
                    raise IntakeRefused(
                        f"edit {entry['edit']} (page {number}): the replacement was written at "
                        f"another size than the {entry['point_size']} pt it replaces"
                    )
        atomic_write_via(
            out_pdf,
            lambda tmp: doc.save(tmp, garbage=4, deflate=True, no_new_id=True),
        )
    finally:
        doc.close()
    return log
