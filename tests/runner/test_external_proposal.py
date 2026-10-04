"""``runner.external_proposal`` — the Claude-free extraction substrate behind
``tools/import_external_proposal.py`` (spec PE-03, decision 8).

Every test builds a small PDF with pymupdf in a temporary directory, so the
module is exercised on a document whose every byte the test wrote. The real
sanitised candidate is covered by ``tests/test_msca_dn_import.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner.external_proposal import (  # noqa: E402
    CLAIM_RULES,
    Paragraph,
    claim_rule_matches,
    extract_document,
    is_row,
    join_segments,
    locate,
    nonws_len,
    page_accounting,
    parse_row,
    render_row,
    split_sentences,
)
from runner.source_index import read_page_text  # noqa: E402

PARA_1 = (
    "Despite rapid advances, the current state of AI in healthcare remains "
    "correlation-driven and fragmented. Systematic reviews confirm that adoption "
    "is slowed by fragmented data environments."
)
PARA_2 = "The network trains 12 doctoral candidates over 36 months across 9 beneficiaries."
PARA_TAIL = "This paragraph does not end with a full stop and continues onto the next"
PARA_HEAD = "page where it ends with a plain statement that names nothing countable."
PARA_3 = "A second page paragraph, e.g. one with an abbreviation, stays one sentence. Then another."

TABLE = [
    ["Number", "Title", "Due"],
    ["D1.1", "Benchmark Report", "M18"],
    ["D1.2", "Framework", "M24"],
]


def _draw_table(page: "pymupdf.Page", x0: float, y0: float, rows: list[list[str]]) -> None:
    col_w, row_h = 120.0, 24.0
    for r, cells in enumerate(rows):
        for c, text in enumerate(cells):
            rect = pymupdf.Rect(x0 + c * col_w, y0 + r * row_h, x0 + (c + 1) * col_w, y0 + (r + 1) * row_h)
            page.draw_rect(rect, color=(0, 0, 0), width=0.8)
            page.insert_text((rect.x0 + 4, rect.y0 + 16), text, fontsize=10)


@pytest.fixture(scope="module")
def pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("external_proposal") / "synthetic.pdf"
    doc = pymupdf.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((72, 72), "1.2. Soundness of the proposed methodology", fontsize=12)
    p1.insert_textbox(pymupdf.Rect(72, 100, 520, 180), PARA_1, fontsize=11)
    p1.insert_textbox(pymupdf.Rect(72, 200, 520, 240), PARA_2, fontsize=11)
    p1.insert_text((72, 270), "Table 3.1 b Deliverables List", fontsize=12)
    _draw_table(p1, 72, 290, TABLE)
    p1.insert_textbox(pymupdf.Rect(72, 420, 520, 460), PARA_TAIL, fontsize=11)
    p2 = doc.new_page(width=595, height=842)
    p2.insert_textbox(pymupdf.Rect(72, 72, 520, 110), PARA_HEAD, fontsize=11)
    p2.insert_textbox(pymupdf.Rect(72, 140, 520, 200), PARA_3, fontsize=11)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture(scope="module")
def pages(pdf: Path):
    return extract_document(pdf)


# --------------------------------------------------------------------------- #
# Page extraction
# --------------------------------------------------------------------------- #


class TestPageExtract:
    def test_page_text_is_the_source_index_reader(self, pdf: Path, pages) -> None:
        assert [p.page for p in pages] == [1, 2]
        for p in pages:
            assert p.text == read_page_text(pdf, p.page)

    def test_blocks_are_collapsed_paragraphs_outside_the_table(self, pages) -> None:
        texts = [b.text for b in pages[0].blocks]
        assert texts[0] == "1.2. Soundness of the proposed methodology"
        assert PARA_1 in texts
        assert PARA_2 in texts
        assert "Table 3.1 b Deliverables List" in texts
        assert PARA_TAIL in texts
        assert not any("Benchmark Report" in t for t in texts)

    def test_the_table_renders_one_row_per_table_row(self, pages) -> None:
        (table,) = pages[0].tables
        assert table.page == 1 and table.index == 0
        assert table.cols == 3
        assert [list(r) for r in table.rows] == TABLE
        assert pages[1].tables == ()

    def test_segments_keep_reading_order_with_rows_at_the_table_position(self, pages) -> None:
        kinds = [(s.kind, s.text) for s in pages[0].segments]
        caption = kinds.index(("prose", "Table 3.1 b Deliverables List"))
        assert kinds[caption + 1] == ("row", "| Number | Title | Due |")
        assert kinds[caption + 2] == ("row", "| D1.1 | Benchmark Report | M18 |")
        assert kinds[caption + 3] == ("row", "| D1.2 | Framework | M24 |")
        assert kinds[caption + 4] == ("prose", PARA_TAIL)

    def test_no_images_and_the_point_sizes_are_counted(self, pages) -> None:
        """Every glyph the PDF carries is counted under its point size; the
        table cells are the only 10 pt text and the two headings the only 12 pt."""
        assert all(p.images == 0 for p in pages)
        sizes = pages[0].chars_by_point_size
        assert sizes["10.0"] == sum(len(c) for r in TABLE for c in r)
        assert sizes["12.0"] == len("1.2. Soundness of the proposed methodology") + len(
            "Table 3.1 b Deliverables List"
        )

    def test_accounting_loses_nothing_on_a_page_the_test_wrote(self, pages) -> None:
        for p in pages:
            acc = page_accounting(p)
            assert acc["page"] == p.page
            assert acc["chars"] == nonws_len(p.text)
            assert acc["loss"] == 0, acc


# --------------------------------------------------------------------------- #
# Rows
# --------------------------------------------------------------------------- #


class TestRows:
    def test_render_and_parse_round_trip(self) -> None:
        cells = ("D1.1", "Fairness Benchmark Report", "M18")
        line = render_row(cells)
        assert line == "| D1.1 | Fairness Benchmark Report | M18 |"
        assert parse_row(line) == cells
        assert is_row(line)

    def test_an_empty_cell_survives(self) -> None:
        assert parse_row(render_row(("", "x", ""))) == ("", "x", "")

    def test_a_pipe_inside_a_cell_is_refused_not_escaped(self) -> None:
        from runner.external_proposal import ExtractionError

        with pytest.raises(ExtractionError):
            render_row(("a | b", "c"))

    def test_prose_is_not_a_row(self) -> None:
        from runner.external_proposal import ExtractionError

        assert not is_row("A sentence | with a pipe in it.")
        with pytest.raises(ExtractionError):
            parse_row("not a row")


# --------------------------------------------------------------------------- #
# Joining pages into paragraphs
# --------------------------------------------------------------------------- #


class TestJoin:
    def test_a_paragraph_cut_by_the_page_break_is_rejoined(self, pages) -> None:
        paragraphs = join_segments(pages)
        joined = next(p for p in paragraphs if p.text.startswith(PARA_TAIL))
        assert joined.text == PARA_TAIL + " " + PARA_HEAD
        assert joined.pages == (1, 2)
        assert joined.kind == "prose"

    def test_paragraphs_ending_in_punctuation_are_not_joined(self, pages) -> None:
        paragraphs = join_segments(pages)
        assert any(p.text == PARA_2 and p.pages == (1,) for p in paragraphs)
        assert any(p.text == PARA_3 and p.pages == (2,) for p in paragraphs)

    def test_rows_are_paragraphs_of_their_own_and_never_joined(self, pages) -> None:
        rows = [p for p in join_segments(pages) if p.kind == "row"]
        assert [p.text for p in rows] == [render_row(r) for r in TABLE]
        assert all(p.pages == (1,) for p in rows)

    def test_paragraph_is_frozen_and_ordered(self) -> None:
        from dataclasses import FrozenInstanceError

        p = Paragraph(kind="prose", text="x", pages=(1,))
        with pytest.raises(FrozenInstanceError):
            p.text = "y"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Sentences and the claim rule
# --------------------------------------------------------------------------- #


class TestClaims:
    def test_sentences_split_on_terminal_punctuation_but_not_abbreviations(self) -> None:
        assert split_sentences(PARA_3) == (
            "A second page paragraph, e.g. one with an abbreviation, stays one sentence.",
            "Then another.",
        )
        assert split_sentences(PARA_1) == (
            "Despite rapid advances, the current state of AI in healthcare remains "
            "correlation-driven and fragmented.",
            "Systematic reviews confirm that adoption is slowed by fragmented data environments.",
        )

    def test_the_rule_set_is_named_and_closed(self) -> None:
        assert set(CLAIM_RULES) == {"quantity", "evidential"}

    @pytest.mark.parametrize(
        "sentence, rules",
        [
            (PARA_2, ("quantity",)),
            ("Systematic reviews confirm that adoption is slowed by fragmented data environments.", ("evidential",)),
            ("The method goes beyond the state of the art in 30% of cases.", ("quantity", "evidential")),
            ("Results have been validated in two hospitals.", ("quantity", "evidential")),
            ("This paragraph names nothing countable and asserts no evidence.", ()),
            ("Within the first three months the plan is agreed.", ("quantity",)),
            ("Within the first phase the plan is agreed.", ()),
            ("Task 1.2 builds on WP1 outputs.", ()),
        ],
    )
    def test_claim_rule_matches(self, sentence: str, rules: tuple[str, ...]) -> None:
        assert claim_rule_matches(sentence) == rules

    def test_locate_returns_offsets_into_the_page_text(self, pdf: Path, pages) -> None:
        text = read_page_text(pdf, 1)
        span = locate(text, PARA_2)
        assert span is not None
        start, end = span
        assert text[start:end] == PARA_2
        assert locate(text, "nowhere in the page") is None
        assert locate(text, "") is None
