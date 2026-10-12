"""``runner.dry_import`` — the measurement behind V08's dry import.

V08 of ``plans/msca_dn_historical_validation_tickets.md``. The module measures
a PDF without a page map, without a graph root and without writing anything,
so an operator can reconcile the inventory against the document before it is
imported.

Every test builds a small PDF with pymupdf in a temporary directory. The
fixture is deliberately the shape criterion 4 is about: a vector figure and a
vector table, so the document carries **zero embedded images and zero
character loss while holding graphical evidence**. A measurement that reports
those two zeros therefore proves nothing about preservation, which is what the
acceptance record has to refuse to treat as proof.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import dry_import as di  # noqa: E402
from runner.external_proposal import (  # noqa: E402
    Block,
    PageExtract,
    extract_document,
    join_segments,
)


def _page(number: int, text: str) -> PageExtract:
    """A page whose every byte the test wrote, for the measurements that need a
    character the fixture's base-14 font cannot encode."""
    return PageExtract(
        page=number,
        text=text,
        blocks=(Block(page=number, bbox=(0.0, 0.0, 1.0, 1.0), text=text),),
        tables=(),
        segments=(),
        images=0,
        chars_by_point_size={"12.0": len(text)},
        text_by_point_size={"12.0": text},
    )

HEADING = "1.2. Soundness of the proposed methodology"
PROSE = (
    "The network trains 12 doctoral candidates over 36 months across 9 beneficiaries. "
    "Systematic reviews confirm that adoption is slowed by fragmented data environments [4]."
)
LIGATURED = "The beneﬁciary confirms the ﬁrst milestone."
FOOTNOTE = "1 A footnote set below the body size, carrying prose and not decoration."
TABLE = [
    ["Number", "Title", "Due"],
    ["D1.1", "Benchmark Report", "M18"],
]


def _draw_table(page: Any, x0: float, y0: float, rows: list[list[str]]) -> None:
    col_w, row_h = 120.0, 24.0
    for r, cells in enumerate(rows):
        for c, text in enumerate(cells):
            rect = pymupdf.Rect(
                x0 + c * col_w, y0 + r * row_h, x0 + (c + 1) * col_w, y0 + (r + 1) * row_h
            )
            page.draw_rect(rect, color=(0, 0, 0), width=0.8)
            page.insert_text((rect.x0 + 4, rect.y0 + 16), text, fontsize=10)


def _draw_gantt(page: Any, y0: float) -> None:
    """A Gantt-shaped vector figure: bars and a baseline, no raster image."""
    page.draw_line(pymupdf.Point(72, y0), pymupdf.Point(500, y0))
    for n in range(4):
        page.draw_rect(
            pymupdf.Rect(90 + n * 40, y0 + 10 + n * 14, 180 + n * 60, y0 + 22 + n * 14),
            color=(0, 0, 0),
            fill=(0.3, 0.5, 0.8),
        )


@pytest.fixture(scope="module")
def pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("dry_import") / "fixture_part_b.pdf"
    doc = pymupdf.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((72, 72), HEADING, fontsize=12)
    p1.insert_textbox(pymupdf.Rect(72, 100, 520, 170), PROSE, fontsize=12)
    p1.insert_textbox(pymupdf.Rect(72, 190, 520, 220), LIGATURED, fontsize=12)
    p1.insert_text((72, 260), "Table 3.1 b Deliverables List", fontsize=12)
    _draw_table(p1, 72, 280, TABLE)
    p1.insert_textbox(pymupdf.Rect(72, 700, 520, 730), FOOTNOTE, fontsize=7)
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((72, 72), "3.1. Work plan and resources", fontsize=12)
    _draw_gantt(p2, 140)
    p2.insert_textbox(pymupdf.Rect(72, 400, 520, 440), "Figure 2 shows the Gantt chart.", fontsize=12)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture(scope="module")
def inventory(pdf: Path) -> dict[str, Any]:
    return di.measure(pdf)


# --------------------------------------------------------------------------- #
# Criterion 1 — the measured inventory
# --------------------------------------------------------------------------- #


class TestTheInventory:
    def test_it_records_the_measured_page_count_and_hash(self, pdf: Path, inventory) -> None:
        assert inventory["pages"] == 2
        assert inventory["sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
        assert inventory["record_type"] == di.INVENTORY_RECORD_TYPE

    def test_the_page_count_is_measured_and_never_declared(self, inventory) -> None:
        """No expected page count is an input, so none can be assumed."""
        assert inventory["page_count_basis"].startswith("derived")
        assert "expected_pages" not in inventory

    def test_it_lists_one_row_per_page(self, inventory) -> None:
        rows = inventory["per_page"]
        assert [r["page"] for r in rows] == [1, 2]
        page_1 = rows[0]
        assert page_1["characters"] > 0
        assert page_1["nonws_characters"] > 0
        assert page_1["blocks"] > 0
        assert page_1["tables"] == 1
        assert page_1["images"] == 0
        assert page_1["drawings"] > 0

    def test_it_reports_the_table_inventory_with_headers(self, inventory) -> None:
        tables = inventory["tables"]
        assert tables["count"] == 1
        assert tables["per_table"][0]["page"] == 1
        assert tables["per_table"][0]["header"] == TABLE[0]
        assert tables["per_table"][0]["cols"] == 3
        assert tables["rows_rendered"] == tables["rows_parsed"]

    def test_it_reports_candidate_section_headings_with_pages(self, inventory) -> None:
        """No page map is declared, so the inventory offers the blocks that
        could open one and lets the operator declare it."""
        found = {(h["marker"], h["page"]) for h in inventory["heading_candidates"]}
        assert ("1.2.", 1) in found
        assert ("3.1.", 2) in found
        assert inventory["heading_candidates"][0]["text"] == HEADING
        assert "declared" not in inventory["heading_candidates"][0]

    def test_it_reports_no_section_map(self, inventory) -> None:
        assert inventory["section_map"]["declared"] is False
        assert "reconcil" in inventory["section_map"]["basis"]

    def test_it_records_the_extraction_environment(self, inventory) -> None:
        env = inventory["extraction_environment"]
        assert env["pymupdf"] == pymupdf.__version__
        assert env["mupdf"] == pymupdf.mupdf_version
        assert "off_pin_reason" in env
        assert "cannot_reproduce_reason" in env

    def test_it_records_the_extractor_versions(self, inventory) -> None:
        assert inventory["versions"]["extractor"]

    def test_it_writes_nothing(self, pdf: Path, inventory) -> None:
        """A dry import measures; it writes no file and builds no graph."""
        before = sorted(p.name for p in pdf.parent.iterdir())
        di.measure(pdf)
        assert sorted(p.name for p in pdf.parent.iterdir()) == before

    def test_it_refuses_a_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(di.DryImportRefused, match="not a file"):
            di.measure(tmp_path / "absent.pdf")


# --------------------------------------------------------------------------- #
# Criterion 4 — zero loss and zero images are not proof
# --------------------------------------------------------------------------- #


class TestTheFigureCensus:
    def test_the_fixture_has_no_embedded_image_and_still_carries_a_figure(
        self, inventory
    ) -> None:
        """The case criterion 4 is about, measured rather than argued."""
        figures = inventory["figures"]
        assert figures["images_on_any_page"] == 0
        assert figures["vector_drawings"] > 0
        assert figures["pages_with_vector_drawings"] == [1, 2]

    def test_character_accounting_balances_while_the_figure_is_unaccounted(
        self, inventory
    ) -> None:
        losses = inventory["character_accounting"]
        assert losses["total_page_characters"] == losses["total_accounted"]
        assert losses["pages_with_loss"] == []

    def test_the_census_says_both_zeros_prove_nothing(self, inventory) -> None:
        figures = inventory["figures"]
        assert figures["zero_images_is_not_absence_of_graphics"] is True
        assert di.GRAPHICAL_PROOF_STATEMENT == figures["not_proof_of_preservation"]
        assert "vector" in di.GRAPHICAL_PROOF_STATEMENT

    def test_the_census_counts_annotations_and_embedded_files(self, inventory) -> None:
        figures = inventory["figures"]
        assert figures["annotations"] == 0
        assert figures["embedded_files"] == 0

    def test_it_lists_the_fonts_the_pages_use(self, inventory) -> None:
        assert inventory["figures"]["fonts"]


class TestPointSizes:
    def test_it_reports_every_point_size_without_a_declared_body_size(
        self, inventory
    ) -> None:
        """A document with no declared body size has a measured distribution and
        no deviation, because there is nothing to deviate from."""
        sizes = inventory["point_sizes"]
        assert sizes["body_point_size_declared"] is None
        assert sizes["largest_share"]["size"] == "12.0"
        assert "7.0" in sizes["distribution"]

    def test_the_smallest_size_carries_prose(self, inventory) -> None:
        small = inventory["point_sizes"]["character_sets"]["7.0"]
        assert "footnote" in small or "A" in small


# --------------------------------------------------------------------------- #
# Criterion 5 — unresolved limitations, recorded before assessment
# --------------------------------------------------------------------------- #


class TestLimitations:
    def test_the_fixture_carries_no_ligature_and_the_measurement_says_so(
        self, inventory
    ) -> None:
        """The base-14 Helvetica of the fixture cannot encode U+FB01, so this
        PDF has no ligature to find. An empty measurement is the answer, not a
        skipped check; the counting itself is exercised below."""
        assert inventory["limitations"]["ligatures"]["present"] == []

    def test_it_counts_a_ligature_per_page_where_one_occurs(self) -> None:
        pages = (
            _page(1, "The benefi" + "ﬁ" + "ciary confirms the first milestone."),
            _page(2, "No ligature here."),
        )
        tables = di.table_inventory(pages)
        sizes = di.point_size_inventory(pages)
        ligatures = di.limitation_inventory(pages, tables, sizes)["ligatures"]
        assert ligatures["present"] == ["ﬁ"]
        assert ligatures["counts"] == {"ﬁ": 1}
        assert ligatures["pages"] == {"ﬁ": [1]}

    def test_it_measures_table_cells_outside_the_page_reading_order(
        self, inventory
    ) -> None:
        cells = inventory["limitations"]["table_cells_not_in_page_reading_order"]
        assert isinstance(cells["cells"], int)

    def test_it_measures_prose_below_the_largest_point_size(self, inventory) -> None:
        below = inventory["limitations"]["prose_below_the_largest_point_size"]
        assert "7.0" in below["sizes"]

    def test_the_limitations_record_holds_every_measured_limitation_unresolved(
        self, inventory
    ) -> None:
        record = di.build_unresolved_limitations(inventory)
        assert record["record_type"] == di.LIMITATIONS_RECORD_TYPE
        assert record["sha256"] == inventory["sha256"]
        assert record["limitations"], "no limitation was carried over"
        for row in record["limitations"]:
            assert row["status"] == "Unresolved"
            assert row["limitation"]
            assert row["consequence"]
            assert row["measured"] is not None

    def test_it_states_that_a_span_locates_without_corroborating(
        self, inventory
    ) -> None:
        record = di.build_unresolved_limitations(inventory)
        assert record["span_statement"] == di.SPAN_LOCATES_STATEMENT
        assert "locates" in di.SPAN_LOCATES_STATEMENT
        assert "corroborat" in di.SPAN_LOCATES_STATEMENT

    def test_it_states_that_the_record_precedes_assessment(self, inventory) -> None:
        record = di.build_unresolved_limitations(inventory)
        assert "before" in record["recorded_when"]
        assert record["resolved"] is False


# --------------------------------------------------------------------------- #
# Criterion 3 — the fidelity acceptance record
# --------------------------------------------------------------------------- #


class TestTheAcceptanceRecord:
    def test_it_covers_the_seven_named_classes_of_evidence(self, inventory) -> None:
        record = di.build_acceptance(inventory)
        items = [row["item"] for row in record["items"]]
        assert items == [spec.item for spec in di.ACCEPTANCE_ITEMS]
        assert set(items) == {
            "gantt_chart",
            "diagrams",
            "embedded_images",
            "footnotes",
            "table_headers",
            "bibliographic_references",
            "supporting_part_b_material",
        }

    def test_every_item_starts_unreconciled(self, inventory) -> None:
        record = di.build_acceptance(inventory)
        assert {row["verdict"] for row in record["items"]} == {"unreconciled"}
        assert record["complete"] is False

    def test_every_item_carries_its_measurement_and_why_it_is_not_proof(
        self, inventory
    ) -> None:
        record = di.build_acceptance(inventory)
        for row in record["items"]:
            assert row["what_must_be_reconciled"]
            assert row["measured"] is not None
            assert row["measurement_is_not_proof"]

    def test_the_gantt_item_quotes_the_vector_measurement(self, inventory) -> None:
        record = di.build_acceptance(inventory)
        gantt = next(r for r in record["items"] if r["item"] == "gantt_chart")
        assert gantt["measured"]["vector_drawings"] > 0
        assert gantt["measured"]["images_on_any_page"] == 0

    def test_the_record_names_the_document_and_its_hash(self, inventory) -> None:
        record = di.build_acceptance(inventory)
        assert record["sha256"] == inventory["sha256"]
        assert record["pages"] == inventory["pages"]
        assert record["record_type"] == di.ACCEPTANCE_RECORD_TYPE


class TestTheAcceptanceCheck:
    def _accepted(self, inventory, item: str, **fields: Any) -> dict[str, Any]:
        record = di.build_acceptance(inventory)
        for row in record["items"]:
            if row["item"] == item:
                row.update(fields)
        return record

    def test_the_default_record_carries_no_finding(self, inventory) -> None:
        assert di.check_acceptance(di.build_acceptance(inventory)) == []

    def test_a_missing_item_is_a_finding(self, inventory) -> None:
        record = di.build_acceptance(inventory)
        record["items"] = [r for r in record["items"] if r["item"] != "footnotes"]
        codes = {f["code"] for f in di.check_acceptance(record)}
        assert "item_missing" in codes

    def test_an_unknown_item_is_a_finding(self, inventory) -> None:
        record = di.build_acceptance(inventory)
        record["items"].append({"item": "cover_page", "verdict": "preserved"})
        findings = di.check_acceptance(record)
        assert {f["code"] for f in findings} >= {"unknown_item"}

    def test_an_unknown_verdict_is_a_finding(self, inventory) -> None:
        record = self._accepted(inventory, "footnotes", verdict="probably_fine")
        codes = {f["code"] for f in di.check_acceptance(record)}
        assert "unknown_verdict" in codes

    def test_a_verdict_without_a_basis_is_a_finding(self, inventory) -> None:
        record = self._accepted(inventory, "footnotes", verdict="preserved")
        findings = di.check_acceptance(record)
        assert {f["code"] for f in findings} >= {"verdict_without_attestation"}

    @pytest.mark.parametrize("basis", sorted(di.MEASUREMENT_ONLY_BASES))
    def test_zero_loss_and_zero_images_are_refused_as_proof(
        self, inventory, basis: str
    ) -> None:
        """Criterion 4, enforced rather than stated."""
        record = self._accepted(
            inventory,
            "embedded_images",
            verdict="preserved",
            basis=basis,
            reconciled_by="operator",
            reconciled_on="2026-10-12",
        )
        findings = di.check_acceptance(record)
        assert [f["code"] for f in findings] == ["measurement_basis_not_proof"]
        assert findings[0]["item"] == "embedded_images"

    def test_a_basis_outside_the_closed_vocabulary_is_a_finding(
        self, inventory
    ) -> None:
        """Free text would walk past a refusal that tests for the
        measurement's own name."""
        record = self._accepted(
            inventory,
            "embedded_images",
            verdict="preserved",
            basis="no characters were lost",
            reconciled_by="operator",
            reconciled_on="2026-10-12",
        )
        findings = di.check_acceptance(record)
        assert [f["code"] for f in findings] == ["unknown_basis"]
        assert "closed" in findings[0]["message"]

    def test_the_vocabulary_is_the_measurement_bases_plus_the_operator_bases(
        self,
    ) -> None:
        assert di.ACCEPTANCE_BASES == di.MEASUREMENT_ONLY_BASES | di.OPERATOR_BASES
        assert not (di.MEASUREMENT_ONLY_BASES & di.OPERATOR_BASES)

    @pytest.mark.parametrize("basis", sorted(di.OPERATOR_BASES))
    def test_every_operator_basis_carries_a_preserved_verdict(
        self, inventory, basis: str
    ) -> None:
        record = self._accepted(
            inventory,
            "diagrams",
            verdict="preserved",
            basis=basis,
            reconciled_by="operator",
            reconciled_on="2026-10-12",
        )
        assert di.check_acceptance(record) == []

    def test_a_measurement_basis_is_admissible_for_a_loss_verdict(
        self, inventory
    ) -> None:
        """A measurement can show that something is gone. It cannot show that
        something was preserved."""
        record = self._accepted(
            inventory,
            "embedded_images",
            verdict="lost",
            basis="zero_embedded_images",
            reconciled_by="operator",
            reconciled_on="2026-10-12",
        )
        assert di.check_acceptance(record) == []

    def test_an_operator_comparison_is_admissible_for_a_preserved_verdict(
        self, inventory
    ) -> None:
        record = self._accepted(
            inventory,
            "gantt_chart",
            verdict="preserved",
            basis="operator_visual_comparison",
            reconciled_by="operator",
            reconciled_on="2026-10-12",
            note="compared page 2 against the PDF",
        )
        assert di.check_acceptance(record) == []

    def test_completion_with_an_unreconciled_item_is_a_finding(
        self, inventory
    ) -> None:
        record = di.build_acceptance(inventory)
        record["complete"] = True
        codes = {f["code"] for f in di.check_acceptance(record)}
        assert "complete_with_unreconciled_item" in codes

    def test_completion_holds_once_every_item_is_reconciled(self, inventory) -> None:
        record = di.build_acceptance(inventory)
        for row in record["items"]:
            row.update(
                verdict="lost",
                basis="operator_visual_comparison",
                reconciled_by="operator",
                reconciled_on="2026-10-12",
            )
        record["complete"] = True
        assert di.check_acceptance(record) == []


# --------------------------------------------------------------------------- #
# The seam is pure
# --------------------------------------------------------------------------- #


class TestDeterminism:
    def test_the_inventory_replays(self, pdf: Path) -> None:
        assert di.measure(pdf) == di.measure(pdf)

    def test_the_records_replay(self, inventory) -> None:
        assert di.build_acceptance(inventory) == di.build_acceptance(inventory)
        assert di.build_unresolved_limitations(
            inventory
        ) == di.build_unresolved_limitations(inventory)

    def test_the_heading_candidates_come_from_the_paragraph_stream(
        self, pdf: Path, inventory
    ) -> None:
        paragraphs = join_segments(extract_document(pdf))
        assert di.heading_candidates(paragraphs) == inventory["heading_candidates"]
