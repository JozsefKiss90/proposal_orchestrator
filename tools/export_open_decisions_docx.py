"""
OD round-3 handout ``.docx`` export — deterministic, Claude-free
(plans/partb_final_drafting_strategy_2026-09-03.md §4: the handout circulates
as markdown plus a docx copy alongside the annotated draft).

Renders the authored markdown handout
(``plans/reports/FIELDWISE_open_decisions_round3_2026-09-04.md``) into a
Word document for circulation.  This is a faithful renderer of the handout's
own markdown subset — headings, paragraphs, ``**bold**`` runs, blockquotes,
bullet/numbered lists, tables and rules.  It adds no content: every word in
the docx comes from the markdown file (single-asterisk emphasis markers are
stripped; the emphasised words are kept verbatim).

Determinism: the output is a pure function of the markdown file, so two
renders produce identical document XML (the .docx zip container carries entry
mtimes; determinism is at the XML-part level, as in Stage 1).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_IMPORT))

from runner.atomic_write import atomic_write_via  # noqa: E402

DEFAULT_HANDOUT_REL: str = (
    "plans/reports/FIELDWISE_open_decisions_round3_2026-09-04.md"
)


class HandoutExportError(Exception):
    """Raised when the handout cannot be read or rendered."""


# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------


def parse_inline_runs(text: str) -> list[tuple[str, bool]]:
    """Split *text* into ``(segment, bold)`` runs on paired ``**`` markers.

    Paired single-asterisk emphasis markers are stripped (the words stay,
    verbatim, as plain text).  After that stripping, an unpaired ``**`` makes
    the whole remaining line literal plain text — the renderer never drops
    characters it cannot interpret.
    """
    # Strip paired single-asterisk emphasis first (never inside ** pairs,
    # which are handled below): *word* -> word.
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+)\*(?!\*)", r"\1", text)
    runs: list[tuple[str, bool]] = []
    parts = text.split("**")
    if len(parts) % 2 == 0:
        # Unpaired ** — treat the whole line as literal plain text.
        return [(text, False)]
    for i, part in enumerate(parts):
        if part:
            runs.append((part, i % 2 == 1))
    return runs or [("", False)]


def _add_runs(paragraph: Any, text: str) -> None:
    for segment, bold in parse_inline_runs(text):
        run = paragraph.add_run(segment)
        run.bold = bold


# ---------------------------------------------------------------------------
# Block-level parsing
# ---------------------------------------------------------------------------

_LIST_ITEM_RE = re.compile(r"^(?:[-*] |\d+\. )")


def _flush_paragraph(doc: Any, buffer: list[str], style: Optional[str]) -> None:
    if not buffer:
        return
    para = doc.add_paragraph(style=style)
    _add_runs(para, " ".join(buffer))
    buffer.clear()


def _render_table(doc: Any, rows: list[str]) -> None:
    parsed: list[list[str]] = []
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue  # header separator row
        parsed.append(cells)
    if not parsed:
        return
    n_cols = max(len(r) for r in parsed)
    table = doc.add_table(rows=len(parsed), cols=n_cols)
    table.style = "Table Grid"
    for i, cells in enumerate(parsed):
        for j, cell in enumerate(cells):
            para = table.rows[i].cells[j].paragraphs[0]
            _add_runs(para, cell)
            if i == 0:
                for run in para.runs:
                    run.bold = True


def _render_quote_block(doc: Any, lines: list[str]) -> None:
    """Render one blockquote: each list item (with its hard-wrapped
    continuation lines) becomes its own quote paragraph; runs of plain lines
    are joined into a single quote paragraph."""
    buffer: list[str] = []
    for line in lines:
        if _LIST_ITEM_RE.match(line):
            _flush_paragraph(doc, buffer, "Quote")
            buffer.append(line)
        elif not line:
            _flush_paragraph(doc, buffer, "Quote")
        else:
            # continuation of the running item or plain quote paragraph
            buffer.append(line)
    _flush_paragraph(doc, buffer, "Quote")


def _render_markdown(doc: Any, text: str) -> None:
    lines = text.split("\n")
    i = 0
    buffer: list[str] = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped == "---":
            _flush_paragraph(doc, buffer, None)
            i += 1
            continue

        if stripped.startswith("# ") and not stripped.startswith("## "):
            _flush_paragraph(doc, buffer, None)
            doc.add_heading(stripped[2:].strip(), level=0)
            i += 1
            continue

        if stripped.startswith("## "):
            _flush_paragraph(doc, buffer, None)
            doc.add_heading(stripped[3:].strip(), level=1)
            i += 1
            continue

        if stripped.startswith(">"):
            _flush_paragraph(doc, buffer, None)
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            _render_quote_block(doc, quote_lines)
            continue

        if stripped.startswith("|"):
            _flush_paragraph(doc, buffer, None)
            table_rows: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_rows.append(lines[i])
                i += 1
            _render_table(doc, table_rows)
            continue

        if _LIST_ITEM_RE.match(stripped):
            _flush_paragraph(doc, buffer, None)
            item_lines = [stripped]
            i += 1
            # continuation lines are indented and not new items
            while (
                i < len(lines)
                and lines[i].strip()
                and lines[i].startswith("  ")
                and not _LIST_ITEM_RE.match(lines[i].strip())
                and not lines[i].strip().startswith(("|", ">", "#"))
            ):
                item_lines.append(lines[i].strip())
                i += 1
            style = (
                "List Bullet"
                if item_lines[0].startswith(("- ", "* "))
                else "List Number"
            )
            para = doc.add_paragraph(style=style)
            _add_runs(
                para, re.sub(_LIST_ITEM_RE, "", " ".join(item_lines), count=1)
            )
            continue

        buffer.append(stripped)
        i += 1
    _flush_paragraph(doc, buffer, None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_handout_docx(
    repo_root: Path,
    *,
    handout_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """Render the handout markdown to ``.docx`` and return the output path."""
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise HandoutExportError("python-docx is required") from exc

    source = (
        handout_path
        if handout_path is not None
        else repo_root / DEFAULT_HANDOUT_REL
    )
    if not source.is_file():
        raise HandoutExportError(f"handout not found: {source}")
    text = source.read_text(encoding="utf-8-sig")

    if output_path is None:
        output_path = source.with_suffix(".docx")

    doc = Document()
    _render_markdown(doc, text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_via(output_path, doc.save, prefix="od_round3_")
    return output_path


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    from runner.paths import find_repo_root

    parser = argparse.ArgumentParser(
        prog="python tools/export_open_decisions_docx.py",
        description="Render the OD round-3 handout markdown to .docx.",
    )
    parser.add_argument("--repo-root", default=None)
    parser.add_argument(
        "--handout",
        default=None,
        help=f"Handout markdown path (default: {DEFAULT_HANDOUT_REL})",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output .docx path (default: the handout path with .docx)",
    )
    args = parser.parse_args(argv)

    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    )
    try:
        out = export_handout_docx(
            repo_root,
            handout_path=Path(args.handout) if args.handout else None,
            output_path=Path(args.output) if args.output else None,
        )
    except HandoutExportError as exc:
        print(f"[ERROR] {exc}")
        return 1
    print(f"[stage2] Handout docx written to {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
