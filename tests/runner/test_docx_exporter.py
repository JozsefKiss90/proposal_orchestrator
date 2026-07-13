"""Tests for runner.docx_exporter — the Part B .docx renderer (ticket 12).

Covers:
  - rendering individual section artifacts into a .docx (headings + content),
  - "renders whatever sections exist" (Excellence-only tracer bullet, and the
    full B1 once all three exist),
  - following the assembled Part B draft's section order when present,
  - the fidelity contract: no content is invented — every heading/paragraph
    traces to the section JSON,
  - nothing-to-export (returns None, writes no file),
  - atomic overwrite, and the standalone CLI entry point.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docx import Document

from runner.docx_exporter import (
    ASSEMBLED_DRAFT_REL,
    FINAL_EXPORTS_REL,
    PROPOSAL_SECTIONS_REL,
    export_part_b_docx,
    main,
)

RUN_ID = "run-docx-1"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _section(slug: str, criterion: str, subs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_id": f"orch.tier5.{slug}_section.v1",
        "run_id": RUN_ID,
        "criterion": criterion,
        "sub_sections": subs,
        "validation_status": {"overall_status": "confirmed", "claim_statuses": []},
        "traceability_footer": {
            "primary_sources": [],
            "no_unsupported_claims_declaration": True,
        },
    }


def _write_excellence(repo_root: Path) -> None:
    _write(
        repo_root / PROPOSAL_SECTIONS_REL / "excellence_section.json",
        _section(
            "excellence",
            "Excellence",
            [
                {
                    "sub_section_id": "1.1",
                    "title": "Objectives and ambition",
                    "content": "First paragraph of objectives.\n\nSecond paragraph.",
                    "word_count": 6,
                },
                {
                    "sub_section_id": "1.2",
                    "title": "Methodology",
                    "content": "Methodology prose here.",
                    "word_count": 3,
                },
            ],
        ),
    )


def _write_impact(repo_root: Path) -> None:
    _write(
        repo_root / PROPOSAL_SECTIONS_REL / "impact_section.json",
        _section(
            "impact",
            "Impact",
            [{"sub_section_id": "2.1", "title": "Career", "content": "Career prose."}],
        ),
    )


def _doc_texts(path: Path) -> list[str]:
    return [p.text for p in Document(str(path)).paragraphs]


def _doc_by_style(path: Path) -> list[tuple[str, str]]:
    return [
        (p.style.name if p.style else "", p.text)
        for p in Document(str(path)).paragraphs
    ]


# ---------------------------------------------------------------------------
# Rendering individual section artifacts
# ---------------------------------------------------------------------------


class TestRenderSections:
    def test_renders_excellence_headings_and_content(self, tmp_path: Path) -> None:
        _write_excellence(tmp_path)
        out = export_part_b_docx(tmp_path)
        assert out == tmp_path / FINAL_EXPORTS_REL / "part_b.docx"
        assert out.is_file()

        texts = _doc_texts(out)
        assert "Proposal Part B" in texts
        assert "Excellence" in texts
        assert "1.1 Objectives and ambition" in texts
        assert "1.2 Methodology" in texts
        # Content prose is present verbatim (split into paragraphs on blanks).
        assert "First paragraph of objectives." in texts
        assert "Second paragraph." in texts
        assert "Methodology prose here." in texts

    def test_heading_levels(self, tmp_path: Path) -> None:
        _write_excellence(tmp_path)
        out = export_part_b_docx(tmp_path)
        styled = _doc_by_style(out)
        # Title, criterion at Heading 1, sub-section at Heading 2.
        assert ("Title", "Proposal Part B") in styled
        assert ("Heading 1", "Excellence") in styled
        assert ("Heading 2", "1.1 Objectives and ambition") in styled

    def test_renders_whatever_exists_excellence_only(self, tmp_path: Path) -> None:
        """Only Excellence present → renders it and nothing about Impact."""
        _write_excellence(tmp_path)
        out = export_part_b_docx(tmp_path)
        texts = _doc_texts(out)
        assert "Excellence" in texts
        assert "Impact" not in texts

    def test_renders_all_three_sections_in_order(self, tmp_path: Path) -> None:
        _write_excellence(tmp_path)
        _write_impact(tmp_path)
        out = export_part_b_docx(tmp_path)
        texts = [t for t in _doc_texts(out) if t in ("Excellence", "Impact")]
        assert texts == ["Excellence", "Impact"]


# ---------------------------------------------------------------------------
# Fidelity — no content invented
# ---------------------------------------------------------------------------


class TestFidelity:
    def test_every_paragraph_traces_to_json(self, tmp_path: Path) -> None:
        """Every non-empty paragraph is either the fixed document title, a
        heading derived from the JSON, or verbatim section content."""
        _write_excellence(tmp_path)
        out = export_part_b_docx(tmp_path)

        allowed = {
            "Proposal Part B",
            "Excellence",
            "1.1 Objectives and ambition",
            "1.2 Methodology",
            "First paragraph of objectives.",
            "Second paragraph.",
            "Methodology prose here.",
        }
        for text in _doc_texts(out):
            if text.strip():
                assert text in allowed, f"unexpected (invented) text: {text!r}"


# ---------------------------------------------------------------------------
# Assembled Part B draft ordering
# ---------------------------------------------------------------------------


class TestAssembledDraftOrdering:
    def test_follows_assembled_section_order(self, tmp_path: Path) -> None:
        """When an assembled draft exists, its ``order`` drives section order —
        here Impact (order 1) before Excellence (order 2)."""
        _write_excellence(tmp_path)
        _write_impact(tmp_path)
        _write(
            tmp_path / ASSEMBLED_DRAFT_REL,
            {
                "schema_id": "orch.tier5.part_b_assembled_draft.v1",
                "run_id": RUN_ID,
                "sections": [
                    {
                        "section_id": "2",
                        "criterion": "Impact",
                        "order": 1,
                        "artifact_path": f"{PROPOSAL_SECTIONS_REL}/impact_section.json",
                    },
                    {
                        "section_id": "1",
                        "criterion": "Excellence",
                        "order": 2,
                        "artifact_path": f"{PROPOSAL_SECTIONS_REL}/excellence_section.json",
                    },
                ],
            },
        )
        out = export_part_b_docx(tmp_path)
        headings = [t for t in _doc_texts(out) if t in ("Excellence", "Impact")]
        assert headings == ["Impact", "Excellence"]


# ---------------------------------------------------------------------------
# Nothing to export / atomicity / CLI
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_no_sections_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / PROPOSAL_SECTIONS_REL).mkdir(parents=True, exist_ok=True)
        out = export_part_b_docx(tmp_path)
        assert out is None
        assert not (tmp_path / FINAL_EXPORTS_REL / "part_b.docx").exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        _write_excellence(tmp_path)
        first = export_part_b_docx(tmp_path)
        assert first is not None and first.is_file()
        # Re-export must overwrite atomically (no leftover temp files).
        second = export_part_b_docx(tmp_path)
        assert second == first
        leftovers = list((tmp_path / FINAL_EXPORTS_REL).glob("*.tmp"))
        assert leftovers == []

    def test_cli_main_success(self, tmp_path: Path) -> None:
        _write_excellence(tmp_path)
        rc = main(["--repo-root", str(tmp_path)])
        assert rc == 0
        assert (tmp_path / FINAL_EXPORTS_REL / "part_b.docx").is_file()

    def test_cli_main_nothing_to_export(self, tmp_path: Path) -> None:
        (tmp_path / PROPOSAL_SECTIONS_REL).mkdir(parents=True, exist_ok=True)
        rc = main(["--repo-root", str(tmp_path)])
        assert rc == 0
