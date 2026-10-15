"""AN4 — source intake (stage A0 of the anonymisation pipeline).

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN4:

1. Intake on the fixture pins it by hash and reproduces the fixture's own
   inventory.
2. Word route: a source that does not render to the pinned PDF is refused.
   PDF route: an overflowing replacement is refused.
3. The reference inventory is written only to a private path, and a path inside
   the repository is refused.

Every PDF here is the AN3 fixture or a variant of it, built in a temporary
directory outside the repository.
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import json
import shutil
from pathlib import Path
from typing import Any, Callable

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import anonymisation_intake as ai  # noqa: E402
from runner import dry_import as di  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fx.BuiltFixture:
    return fx.build(tmp_path_factory.mktemp("an4_fixture"))


@pytest.fixture()
def pdf(built: fx.BuiltFixture, tmp_path: Path) -> Path:
    """A private copy per test, so no test can disturb another's input."""
    target = tmp_path / "in" / fx.PDF_NAME
    target.parent.mkdir()
    shutil.copyfile(built.pdf, target)
    return target


@pytest.fixture()
def word_source(tmp_path: Path) -> Path:
    """Stands in for the .docx. The check reads its hash, never its content."""
    path = tmp_path / "in" / "part_b.docx"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"synthetic word source")
    return path


def _variant(pdf: Path, tmp_path: Path, name: str, change: Callable[[Any], Any]) -> Path:
    doc = pymupdf.open(pdf)
    try:
        change(doc)
        out = tmp_path / "renders" / name
        out.parent.mkdir(exist_ok=True)
        doc.save(out, garbage=4, deflate=True, no_new_id=True)
        return out
    finally:
        doc.close()


def _find(pdf: Path, page: int, text: str) -> tuple[float, float, float, float]:
    doc = pymupdf.open(pdf)
    try:
        rects = doc[page - 1].search_for(text)
        assert rects, f"{text!r} is not on page {page}"
        return tuple(rects[0])
    finally:
        doc.close()


def _relabel(doc: Any) -> None:
    """Change the bytes and nothing the render check compares, as a real render would."""
    doc.set_metadata({"producer": "a word processor"})


def _word(source: Path, render: Path) -> ai.WordSource:
    return ai.WordSource(
        source=source, source_sha256=_sha(source), render=render, render_sha256=_sha(render)
    )


def _text(pdf: Path, page: int) -> str:
    doc = pymupdf.open(pdf)
    try:
        return doc[page - 1].get_text()
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# Criterion 1: pin and reproduce
# --------------------------------------------------------------------------- #


class TestPin:
    def test_intake_pins_the_input_by_hash(self, pdf: Path, tmp_path: Path) -> None:
        result = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "private")
        record = json.loads(result.intake_record.read_text(encoding="utf-8"))
        assert record["schema"] == ai.SCHEMA
        assert record["input"]["sha256"] == _sha(pdf)
        assert record["input"]["basis"] == "authenticated"

    def test_a_hash_the_bytes_do_not_match_is_refused(self, pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "private"
        with pytest.raises(ai.IntakeRefused, match="not the pinned file"):
            ai.intake(pdf=pdf, expected_sha256="0" * 64, out_dir=out)
        assert not out.exists()

    def test_a_malformed_hash_is_refused(self, pdf: Path, tmp_path: Path) -> None:
        with pytest.raises(ai.IntakeRefused, match="64 lower-case hex"):
            ai.intake(pdf=pdf, expected_sha256="ABC", out_dir=tmp_path / "private")

    def test_the_reference_inventory_reproduces_the_fixtures_own(
        self, pdf: Path, built: fx.BuiltFixture, tmp_path: Path
    ) -> None:
        result = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "private")
        stored = json.loads(result.reference_inventory.read_text(encoding="utf-8"))
        assert stored == di.measure(built.pdf)

    def test_the_reference_inventory_lists_what_the_fixture_planted(
        self, pdf: Path, tmp_path: Path
    ) -> None:
        result = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "private")
        stored = json.loads(result.reference_inventory.read_text(encoding="utf-8"))
        (table,) = stored["tables"]["per_table"]
        assert table["page"] == fx.SUPERVISOR_TABLE_PAGE
        assert table["header"] == list(fx.SUPERVISOR_TABLE_HEADER)
        assert table["rows"] == 1 + len(fx.SUPERVISOR_ROWS)
        assert stored["figures"]["pages_with_images"] == [fx.LOGO_PAGE]
        assert fx.DIAGRAM_PAGE in stored["figures"]["pages_with_vector_drawings"]
        assert stored["metadata"]["fields"]["author"]["populated"] is True
        assert stored["metadata"]["xmp"]["present"] is True
        assert stored["citation_markers"]["counts"]["bracketed_numbers"] >= 3
        assert [h["marker"] for h in stored["heading_candidates"]] == [m for m, _ in fx.SECTIONS]

    def test_the_record_binds_the_inventory_by_hash(self, pdf: Path, tmp_path: Path) -> None:
        result = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "private")
        record = json.loads(result.intake_record.read_text(encoding="utf-8"))
        assert record["reference_inventory"]["sha256"] == _sha(result.reference_inventory)
        assert record["reference_inventory"]["file"] == ai.REFERENCE_INVENTORY_FILE

    def test_a_replay_gives_the_same_bytes(self, pdf: Path, tmp_path: Path) -> None:
        first = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "a")
        second = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "b")
        assert first.reference_inventory.read_bytes() == second.reference_inventory.read_bytes()
        assert first.intake_record.read_bytes() == second.intake_record.read_bytes()

    def test_a_rerun_into_the_same_directory_is_a_no_op(
        self, pdf: Path, tmp_path: Path
    ) -> None:
        out = tmp_path / "private"
        ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=out)
        again = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=out)
        assert again.reference_inventory.is_file()

    def test_a_pinned_intake_is_never_overwritten(
        self, pdf: Path, tmp_path: Path, word_source: Path
    ) -> None:
        out = tmp_path / "private"
        ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=out)
        before = (out / ai.INTAKE_RECORD_FILE).read_bytes()
        render = _variant(pdf, tmp_path, "render.pdf", _relabel)
        with pytest.raises(ai.IntakeRefused, match="already holds"):
            ai.intake(
                pdf=pdf, expected_sha256=_sha(pdf), out_dir=out, word=_word(word_source, render)
            )
        assert (out / ai.INTAKE_RECORD_FILE).read_bytes() == before

    def test_the_record_quotes_no_text_of_the_document(self, pdf: Path, tmp_path: Path) -> None:
        result = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "private")
        record = result.intake_record.read_text(encoding="utf-8")
        for entity in fx.ENTITIES:
            assert entity["surface"] not in record
        for _, title in fx.SECTIONS:
            assert title not in record


# --------------------------------------------------------------------------- #
# Criterion 2, Word route: the render check
# --------------------------------------------------------------------------- #


class TestWordRoute:
    def _intake(self, pdf: Path, out: Path, source: Path, render: Path) -> ai.IntakeResult:
        return ai.intake(
            pdf=pdf, expected_sha256=_sha(pdf), out_dir=out, word=_word(source, render)
        )

    def test_a_source_that_renders_to_the_pinned_pdf_takes_the_word_route(
        self, pdf: Path, tmp_path: Path, word_source: Path
    ) -> None:
        render = _variant(pdf, tmp_path, "same.pdf", _relabel)
        result = self._intake(pdf, tmp_path / "private", word_source, render)
        record = json.loads(result.intake_record.read_text(encoding="utf-8"))
        assert record["route"] == "word_source"
        assert record["word_source"]["sha256"] == _sha(word_source)
        assert record["word_source"]["render_sha256"] == _sha(render)
        assert record["render_check"]["findings"] == []
        assert record["render_check"]["compared"] == list(ai.RENDER_CHECKS)

    @pytest.mark.parametrize(
        ("name", "change", "code"),
        [
            ("short.pdf", lambda doc: doc.delete_page(2), "page_count"),
            (
                "heading.pdf",
                lambda doc: doc[0].insert_text((72, 780), "9.9. Inserted heading", fontsize=12),
                "headings",
            ),
            (
                "moved_heading.pdf",
                lambda doc: doc.move_page(2, 1),
                "headings",
            ),
        ],
    )
    def test_a_source_that_does_not_render_to_the_pinned_pdf_is_refused(
        self, pdf: Path, tmp_path: Path, word_source: Path, name: str, change, code: str
    ) -> None:
        render = _variant(pdf, tmp_path, name, change)
        out = tmp_path / "private"
        with pytest.raises(ai.RenderMismatch) as caught:
            self._intake(pdf, out, word_source, render)
        assert code in {f["check"] for f in caught.value.findings}
        assert "submitted PDF" in str(caught.value)
        assert not out.exists()

    def test_a_render_that_loses_the_table_is_refused(
        self, pdf: Path, tmp_path: Path, word_source: Path
    ) -> None:
        top, bottom = fx.LAYER_BANDS[(fx.SUPERVISOR_TABLE_PAGE, "table")]

        def drop_table(doc: Any) -> None:
            page = doc[fx.SUPERVISOR_TABLE_PAGE - 1]
            page.add_redact_annot(pymupdf.Rect(0, top - 2, page.rect.width, bottom + 2))
            page.apply_redactions(graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED)

        render = _variant(pdf, tmp_path, "no_table.pdf", drop_table)
        with pytest.raises(ai.RenderMismatch) as caught:
            self._intake(pdf, tmp_path / "private", word_source, render)
        assert "tables" in {f["check"] for f in caught.value.findings}

    def test_findings_quote_no_text(
        self, pdf: Path, tmp_path: Path, word_source: Path
    ) -> None:
        render = _variant(pdf, tmp_path, "moved.pdf", lambda doc: doc.move_page(2, 1))
        with pytest.raises(ai.RenderMismatch) as caught:
            self._intake(pdf, tmp_path / "private", word_source, render)
        dumped = json.dumps(caught.value.findings) + str(caught.value)
        for _, title in fx.SECTIONS:
            assert title not in dumped

    @pytest.mark.parametrize("wrong", ["source_sha256", "render_sha256"])
    def test_the_source_and_its_render_are_each_pinned(
        self, pdf: Path, tmp_path: Path, word_source: Path, wrong: str
    ) -> None:
        render = _variant(pdf, tmp_path, "render.pdf", _relabel)
        word = dataclasses.replace(_word(word_source, render), **{wrong: "1" * 64})  # type: ignore[arg-type]
        with pytest.raises(ai.IntakeRefused, match="not the pinned file"):
            ai.intake(
                pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "private", word=word
            )

    def test_a_copy_of_the_submitted_pdf_is_not_a_render(
        self, pdf: Path, tmp_path: Path, word_source: Path
    ) -> None:
        out = tmp_path / "private"
        with pytest.raises(ai.IntakeRefused, match="proves nothing about the source"):
            self._intake(pdf, out, word_source, pdf)
        assert not out.exists()

    def test_without_a_source_the_route_is_the_submitted_pdf(
        self, pdf: Path, tmp_path: Path
    ) -> None:
        result = ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "private")
        record = json.loads(result.intake_record.read_text(encoding="utf-8"))
        assert record["route"] == "submitted_pdf"
        assert record["word_source"] is None
        assert record["render_check"] is None
        assert "O1" in record["route_basis"]

    def test_the_render_check_is_pure_over_two_inventories(self, built: fx.BuiltFixture) -> None:
        inventory = di.measure(built.pdf)
        assert ai.render_check(inventory, inventory) == []


# --------------------------------------------------------------------------- #
# Criterion 2, PDF route: the edit harness
# --------------------------------------------------------------------------- #


def _pdf_intake(pdf: Path, where: Path) -> Path:
    return ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=where).intake_record


class TestPdfEditHarness:
    def _edit(self, pdf: Path, out: Path, *edits: ai.SpanEdit) -> list[dict[str, Any]]:
        record = _pdf_intake(pdf, out.parent.with_name(f"{out.parent.name}_intake"))
        return ai.apply_span_edits(pdf, record, list(edits), out)

    def test_a_replacement_that_fits_replaces_the_span(self, pdf: Path, tmp_path: Path) -> None:
        rect = _find(pdf, 1, "Fenwardt Biosystems GmbH")
        out = tmp_path / "private" / "edited.pdf"
        log = self._edit(pdf, out, ai.SpanEdit(page=1, rect=rect, replacement="Beneficiary B2"))
        text = _text(out, 1)
        assert "Fenwardt" not in text
        assert "Beneficiary B2" in text
        assert log[0]["used_points"] <= log[0]["budget_points"]

    def test_an_overflowing_replacement_is_refused(self, pdf: Path, tmp_path: Path) -> None:
        rect = _find(pdf, 1, "VARNISH")
        out = tmp_path / "private" / "edited.pdf"
        with pytest.raises(ai.ReplacementOverflow, match="length budget"):
            self._edit(
                pdf, out,
                ai.SpanEdit(page=1, rect=rect, replacement="a prior ERC Consolidator Grant"),
            )
        assert not out.exists()

    def test_one_overflow_refuses_the_whole_batch(self, pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "private" / "edited.pdf"
        with pytest.raises(ai.ReplacementOverflow):
            self._edit(
                pdf, out,
                ai.SpanEdit(page=1, rect=_find(pdf, 1, "Fenwardt Biosystems GmbH"),
                            replacement="Beneficiary B2"),
                ai.SpanEdit(page=1, rect=_find(pdf, 1, "VARNISH"),
                            replacement="a prior ERC Consolidator Grant"),
            )
        assert not out.exists()

    def test_figures_and_table_rules_survive_an_edit(self, pdf: Path, tmp_path: Path) -> None:
        out = tmp_path / "private" / "edited.pdf"
        self._edit(
            pdf, out,
            ai.SpanEdit(page=2, rect=_find(pdf, 2, "EUR 412,560"), replacement="EUR 400k"),
            ai.SpanEdit(page=1, rect=_find(pdf, 1, "Brennmark"), replacement="a city"),
        )
        before = di.graphical_census(pdf)["per_page"]
        after = di.graphical_census(out)["per_page"]
        assert [(r["images"], r["drawings"]) for r in after] == [
            (r["images"], r["drawings"]) for r in before
        ]

    def test_the_edit_replays_byte_equal(self, pdf: Path, tmp_path: Path) -> None:
        edit = ai.SpanEdit(page=1, rect=_find(pdf, 1, "Brennmark"), replacement="a city")
        a, b = tmp_path / "a" / "e.pdf", tmp_path / "b" / "e.pdf"
        self._edit(pdf, a, edit)
        self._edit(pdf, b, edit)
        assert a.read_bytes() == b.read_bytes()

    def test_the_log_quotes_no_text(self, pdf: Path, tmp_path: Path) -> None:
        log = self._edit(
            pdf, tmp_path / "private" / "e.pdf",
            ai.SpanEdit(page=1, rect=_find(pdf, 1, "Fenwardt Biosystems GmbH"),
                        replacement="Beneficiary B2"),
        )
        dumped = json.dumps(log)
        assert "Fenwardt" not in dumped
        assert "Beneficiary" not in dumped

    def test_the_log_records_the_original_font(self, pdf: Path, tmp_path: Path) -> None:
        (entry,) = self._edit(
            pdf, tmp_path / "private" / "e.pdf",
            ai.SpanEdit(page=1, rect=_find(pdf, 1, "Brennmark"), replacement="a city"),
        )
        assert entry["original_fonts"] == ["Helvetica"]
        assert entry["font"] == ai.REPLACEMENT_FONT

    def test_the_input_must_be_the_file_the_intake_pinned(
        self, pdf: Path, tmp_path: Path
    ) -> None:
        record = _pdf_intake(pdf, tmp_path / "intake")
        other = _variant(pdf, tmp_path, "other.pdf", _relabel)
        with pytest.raises(ai.IntakeRefused, match="not the pinned file"):
            ai.apply_span_edits(
                other, record,
                [ai.SpanEdit(page=1, rect=_find(pdf, 1, "Brennmark"), replacement="x")],
                tmp_path / "private" / "e.pdf",
            )

    def test_an_intake_on_the_word_route_refuses_pdf_edits(
        self, pdf: Path, tmp_path: Path, word_source: Path
    ) -> None:
        render = _variant(pdf, tmp_path, "render.pdf", _relabel)
        record = ai.intake(
            pdf=pdf, expected_sha256=_sha(pdf), out_dir=tmp_path / "intake",
            word=_word(word_source, render),
        ).intake_record
        out = tmp_path / "private" / "e.pdf"
        with pytest.raises(ai.IntakeRefused, match="route 'word_source'"):
            ai.apply_span_edits(
                pdf, record,
                [ai.SpanEdit(page=1, rect=_find(pdf, 1, "Brennmark"), replacement="x")],
                out,
            )
        assert not out.exists()

    def test_a_record_that_is_not_an_intake_is_refused(self, pdf: Path, tmp_path: Path) -> None:
        bogus = tmp_path / "bogus.json"
        bogus.write_text("{}", encoding="utf-8")
        with pytest.raises(ai.IntakeRefused, match="not an"):
            ai.apply_span_edits(pdf, bogus, [], tmp_path / "private" / "e.pdf")

    def test_a_span_with_no_text_under_it_is_refused(self, pdf: Path, tmp_path: Path) -> None:
        with pytest.raises(ai.IntakeRefused, match="no character"):
            self._edit(
                pdf, tmp_path / "private" / "e.pdf",
                ai.SpanEdit(page=1, rect=(300, 700, 400, 712), replacement="x"),
            )

    def test_a_span_on_a_page_the_document_lacks_is_refused(
        self, pdf: Path, tmp_path: Path
    ) -> None:
        with pytest.raises(ai.IntakeRefused, match="page 9"):
            self._edit(
                pdf, tmp_path / "private" / "e.pdf",
                ai.SpanEdit(page=9, rect=(72, 100, 120, 112), replacement="x"),
            )

    def test_overlapping_spans_are_refused(self, pdf: Path, tmp_path: Path) -> None:
        rect = _find(pdf, 1, "Fenwardt Biosystems GmbH")
        with pytest.raises(ai.IntakeRefused, match="overlap"):
            self._edit(
                pdf, tmp_path / "private" / "e.pdf",
                ai.SpanEdit(page=1, rect=rect, replacement="B2"),
                ai.SpanEdit(page=1, rect=rect, replacement="B3"),
            )

    def test_a_multi_line_replacement_is_refused(self, pdf: Path, tmp_path: Path) -> None:
        with pytest.raises(ai.IntakeRefused, match="one line"):
            self._edit(
                pdf, tmp_path / "private" / "e.pdf",
                ai.SpanEdit(page=1, rect=_find(pdf, 1, "Fenwardt Biosystems GmbH"),
                            replacement="B\n2"),
            )

    def test_a_span_over_two_point_sizes_is_refused(self, pdf: Path, tmp_path: Path) -> None:
        heading = _find(pdf, 1, "Research objectives")
        body = _find(pdf, 1, "KELVARA (Kelp")
        rect = (heading[0], heading[1], body[2], body[3])
        with pytest.raises(ai.IntakeRefused, match="point size"):
            self._edit(pdf, tmp_path / "private" / "e.pdf",
                       ai.SpanEdit(page=1, rect=rect, replacement="x"))


# --------------------------------------------------------------------------- #
# Criterion 3: private paths only
# --------------------------------------------------------------------------- #


class TestPrivatePaths:
    def test_an_output_inside_the_repository_is_refused(self, pdf: Path) -> None:
        out = REPO / "docs" / "an4_must_not_exist"
        with pytest.raises(ai.IntakeRefused, match="inside this repository"):
            ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=out)
        assert not out.exists()

    def test_the_repository_root_itself_is_refused(self, pdf: Path) -> None:
        with pytest.raises(ai.IntakeRefused, match="inside this repository"):
            ai.intake(pdf=pdf, expected_sha256=_sha(pdf), out_dir=REPO)

    def test_an_input_inside_the_repository_is_refused(self, tmp_path: Path) -> None:
        inside = REPO / "docs" / "infrastructure_security" / "x.pdf"
        with pytest.raises(ai.IntakeRefused, match="inside this repository"):
            ai.intake(pdf=inside, expected_sha256="0" * 64, out_dir=tmp_path / "private")

    def test_an_edited_pdf_inside_the_repository_is_refused(
        self, pdf: Path, tmp_path: Path
    ) -> None:
        out = REPO / "an4_must_not_exist.pdf"
        with pytest.raises(ai.IntakeRefused, match="inside this repository"):
            ai.apply_span_edits(
                pdf, _pdf_intake(pdf, tmp_path / "intake"),
                [ai.SpanEdit(page=1, rect=_find(pdf, 1, "Brennmark"), replacement="x")],
                out,
            )
        assert not out.exists()

    def test_the_repository_is_measured_from_the_module_not_an_argument(self) -> None:
        assert ai.THIS_REPOSITORY == REPO
        for fn in (ai.intake, ai.apply_span_edits):
            assert "repo" not in " ".join(inspect.signature(fn).parameters)
