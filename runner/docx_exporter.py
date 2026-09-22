"""
Part B ``.docx`` exporter (D14 — the milestone's primary deliverable format).

The orchestration engine assembles evaluator-facing proposal content as JSON:
per-criterion section artifacts (``proposal_sections/<slug>_section.json``,
written by the section assembler) optionally composed into a Part B document
(``assembled_drafts/part_b_assembled_draft.json``).  This module renders that
JSON into a Microsoft Word ``.docx`` written to ``final_exports/`` — replacing
the JSON-only output the pipeline produced before.

Fidelity contract (ticket 12):
    The exporter **invents no content**.  Every heading and paragraph comes
    verbatim from the section JSON — the ``criterion`` string, each
    sub-section's ``sub_section_id`` / ``title``, and its ``content`` prose.
    The only text the exporter adds is the fixed structural document title
    (a label, not proposal content).  It renders **whatever sections exist**:
    the assembled Part B when present, otherwise whatever individual section
    artifacts are on disk (so it works for the Excellence-only tracer bullet
    as well as the full B1).

This is a pure-Python, Claude-free renderer.  It performs no domain reasoning
and fails soft: when no section content exists it returns ``None`` (nothing to
render) rather than writing an empty document.

Constitutional note:
    Tier 5 is the output layer (§5, §11.4).  This exporter derives its output
    solely from existing Tier 5 section artifacts; it introduces no new facts,
    claims, or framings (§13.10 — traceable to a higher tier by construction,
    since it copies section text verbatim).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from runner.atomic_write import atomic_write_via

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROPOSAL_SECTIONS_REL: str = "docs/tier5_deliverables/proposal_sections"
ASSEMBLED_DRAFT_REL: str = (
    "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json"
)
FINAL_EXPORTS_REL: str = "docs/tier5_deliverables/final_exports"
DEFAULT_OUTPUT_NAME: str = "part_b.docx"

#: Part B ordering of the criterion sections, used when rendering the
#: individual section artifacts directly (no assembled draft present).
_SECTION_SLUG_ORDER: tuple[str, ...] = ("excellence", "impact", "implementation")

#: Fixed structural document title.  This is a document label, not proposal
#: content — no claim or fact is invented by naming the document.
_DOCUMENT_TITLE: str = "Proposal Part B"

#: Decision-log glob that signals an active synthetic-data override
#: (SYN-SPINE-01, the §3 human override that fabricated the identity spine for
#: a demonstration run).  When present, the exported document carries a visible
#: "not for submission" marker so no demo artifact can be mistaken for a real
#: proposal (a synthetic person is attached to a real institution).
_SYNTHETIC_OVERRIDE_GLOB: str = (
    "docs/tier4_orchestration_state/decision_log/synthetic-spine*.json"
)
_SYNTHETIC_MARKER: str = "SYNTHETIC DEMO — NOT FOR SUBMISSION"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class DocxExportError(Exception):
    """Raised when the Part B document cannot be rendered or written."""


def _synthetic_override_active(repo_root: Path) -> bool:
    """Return ``True`` when a synthetic-data override record is present.

    Detects SYN-SPINE-01 (the §3 operator override that fabricated the
    identity spine for a demonstration run) by the presence of its durable
    decision-log record.  The exporter uses this to stamp a visible
    not-for-submission marker on demo artifacts — automatically, so the marker
    can never be forgotten while the override is active, and absent on a real
    (non-synthetic) run.
    """
    log_dir = repo_root / "docs/tier4_orchestration_state/decision_log"
    if not log_dir.is_dir():
        return False
    return any(log_dir.glob("synthetic-spine*.json"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_optional_json(path: Path) -> Optional[dict[str, Any]]:
    """Read a JSON object, returning ``None`` when absent or unreadable.

    The exporter is best-effort (post-run output layer): an absent or corrupt
    section artifact is skipped with a warning rather than aborting the export.
    Named ``_read_optional_json`` to distinguish it from the *raising* readers in
    the deterministic components (e.g. ``unit_cost_budget._read_json``).
    """
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        logger.warning("docx exporter: skipping unreadable JSON %s", path)
        return None
    return data if isinstance(data, dict) else None


def _resolve_section_paths(repo_root: Path) -> list[Path]:
    """Resolve the ordered list of section artifact paths to render.

    Prefers the assembled Part B draft (``sections[].artifact_path`` in
    Part B order); falls back to whatever ``<slug>_section.json`` files exist
    under ``proposal_sections/`` (in canonical Part B order).  Only existing,
    readable files are returned — the exporter renders whatever is present.
    """
    assembled = _read_optional_json(repo_root / ASSEMBLED_DRAFT_REL)
    if assembled is not None:
        sections = assembled.get("sections")
        if isinstance(sections, list) and sections:
            ordered = sorted(
                (s for s in sections if isinstance(s, dict)),
                key=lambda s: s.get("order", 0),
            )
            paths: list[Path] = []
            for entry in ordered:
                rel = entry.get("artifact_path")
                if isinstance(rel, str) and rel:
                    candidate = repo_root / rel
                    if candidate.is_file():
                        paths.append(candidate)
            if paths:
                return paths

    # Fallback: individual section artifacts on disk, in Part B order.
    sections_dir = repo_root / PROPOSAL_SECTIONS_REL
    paths = []
    for slug in _SECTION_SLUG_ORDER:
        candidate = sections_dir / f"{slug}_section.json"
        if candidate.is_file():
            paths.append(candidate)
    return paths


def split_content_blocks(content: str) -> list[str]:
    """Split section *content* into its paragraph blocks (blank-line split).

    This split defines the draft ¶-numbering scheme: any consumer that
    anchors to rendered paragraphs must share this function so its ¶
    indices can never drift from the rendered output.
    """
    return [b for b in re.split(r"\n\s*\n", content.strip()) if b.strip()]


def _add_content_paragraphs(doc: Any, content: str) -> None:
    """Render *content* verbatim as one or more paragraphs.

    Splits on blank lines into paragraphs and preserves intra-paragraph line
    breaks — no text is added, removed, or reordered.
    """
    for block in split_content_blocks(content):
        para = doc.add_paragraph()
        lines = block.split("\n")
        for i, line in enumerate(lines):
            run = para.add_run(line)
            if i < len(lines) - 1:
                run.add_break()


def _render_section(doc: Any, section: dict[str, Any]) -> bool:
    """Render one section artifact into *doc*.  Returns True if anything was
    rendered (a criterion heading or at least one sub-section)."""
    criterion = section.get("criterion")
    rendered = False
    if isinstance(criterion, str) and criterion.strip():
        doc.add_heading(criterion, level=1)
        rendered = True

    sub_sections = section.get("sub_sections")
    if not isinstance(sub_sections, list):
        return rendered

    for sub in sub_sections:
        if not isinstance(sub, dict):
            continue
        title = sub.get("title")
        sub_id = sub.get("sub_section_id")
        heading_parts = [
            str(p) for p in (sub_id, title) if isinstance(p, str) and p.strip()
        ]
        if heading_parts:
            doc.add_heading(" ".join(heading_parts), level=2)
            rendered = True
        content = sub.get("content")
        if isinstance(content, str) and content.strip():
            _add_content_paragraphs(doc, content)
            rendered = True
    return rendered


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_part_b_docx(
    repo_root: Path,
    *,
    output_name: str = DEFAULT_OUTPUT_NAME,
) -> Optional[Path]:
    """Render the assembled Part B (or whatever sections exist) to ``.docx``.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root.
    output_name:
        File name written under ``final_exports/`` (default ``part_b.docx``).

    Returns
    -------
    Optional[Path]
        Absolute path to the written ``.docx``, or ``None`` when there is no
        section content to render (nothing is written in that case).

    Raises
    ------
    DocxExportError
        When ``python-docx`` is not installed, or the document cannot be
        written.
    """
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise DocxExportError(
            "python-docx is required to export .docx (add 'python-docx' to "
            "requirements.txt and install it)"
        ) from exc

    section_paths = _resolve_section_paths(repo_root)
    if not section_paths:
        logger.info(
            "docx exporter: no section artifacts found under %s or %s; "
            "nothing to export",
            PROPOSAL_SECTIONS_REL,
            ASSEMBLED_DRAFT_REL,
        )
        return None

    doc = Document()
    doc.add_heading(_DOCUMENT_TITLE, level=0)

    # Stamp a visible not-for-submission marker when the run used the
    # synthetic-spine override (SYN-SPINE-01): a synthetic person is attached
    # to a real institution, so no output may be mistaken for a real proposal.
    if _synthetic_override_active(repo_root):
        marker = doc.add_paragraph()
        run = marker.add_run(_SYNTHETIC_MARKER)
        run.bold = True
        logger.info("docx exporter: synthetic-override marker stamped")

    any_rendered = False
    for path in section_paths:
        section = _read_optional_json(path)
        if section is None:
            continue
        if _render_section(doc, section):
            any_rendered = True

    if not any_rendered:
        logger.info(
            "docx exporter: section artifacts had no renderable content; "
            "nothing to export"
        )
        return None

    output_path = repo_root / FINAL_EXPORTS_REL / output_name
    atomic_write_via(output_path, doc.save, prefix="docx_export_")
    logger.info(
        "Part B exported to %s (%d section artifact(s))",
        output_path,
        len(section_paths),
    )
    return output_path


# ---------------------------------------------------------------------------
# Standalone entry point — ``python -m runner.docx_exporter``
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """CLI: render the Part B ``.docx`` from the current repo state.

    Exit codes: ``0`` on success (or nothing-to-export), ``1`` on error.
    """
    import argparse

    from runner.paths import find_repo_root

    parser = argparse.ArgumentParser(
        prog="python -m runner.docx_exporter",
        description="Render the assembled Part B proposal to .docx.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: auto-discovered).",
    )
    parser.add_argument(
        "--output-name",
        default=DEFAULT_OUTPUT_NAME,
        help=f"Output file name under final_exports/ (default: {DEFAULT_OUTPUT_NAME}).",
    )
    args = parser.parse_args(argv)

    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    )
    try:
        out = export_part_b_docx(repo_root, output_name=args.output_name)
    except DocxExportError as exc:
        print(f"[ERROR] {exc}")
        return 1
    if out is None:
        print("[docx] No section content to export.")
    else:
        print(f"[docx] Exported Part B to {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main())
