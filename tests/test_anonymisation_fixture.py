"""AN3 — the synthetic Part B fixture with planted entities.

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN3:

1. The fixture builds outside the repository, and building it twice gives
   identical bytes.
2. Every policy category has at least one planted entity, listed in the
   planted-entity manifest.
3. The dry-import measurement of the fixture lists the supervisor table, both
   figures, the metadata and the citation markers.

Every later anonymisation ticket tests against this fixture, so this file also
holds the manifest to the PDF: each planting the manifest declares is present
where it says, in the form it says. A manifest that lists a planting the PDF
does not carry would let a redaction test pass on an entity that was never
there.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import dry_import as di  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fx.BuiltFixture:
    return fx.build(tmp_path_factory.mktemp("an3_fixture"))


@pytest.fixture(scope="module")
def manifest(built: fx.BuiltFixture) -> dict[str, Any]:
    return json.loads(built.manifest.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def inventory(built: fx.BuiltFixture) -> dict[str, Any]:
    return di.measure(built.pdf)


def _page_text(pdf: Path, page: int, band: tuple[float, float] | None = None) -> str:
    doc = pymupdf.open(pdf)
    try:
        clip = None if band is None else pymupdf.Rect(0, band[0], 10_000, band[1])
        return doc[page - 1].get_text(clip=clip)
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# Criterion 1: outside the repository, and byte-identical on a rebuild
# --------------------------------------------------------------------------- #


class TestBuildsOutsideTheRepositoryReproducibly:
    def test_the_fixture_is_written_outside_the_repository(self, built: fx.BuiltFixture) -> None:
        for path in (built.pdf, built.manifest):
            assert path.is_file()
            assert not path.resolve().is_relative_to(REPO)

    def test_a_target_inside_the_repository_is_refused(self) -> None:
        with pytest.raises(fx.FixtureRefused, match="inside the repository"):
            fx.build(REPO / ".scratch" / "an3_fixture_must_not_exist")
        assert not (REPO / ".scratch" / "an3_fixture_must_not_exist").exists()

    def test_the_repository_boundary_is_not_an_argument(self) -> None:
        # The V17 pattern: inside is measured from the module's own location.
        assert fx.THIS_REPOSITORY == REPO
        assert list(inspect.signature(fx.build).parameters) == ["target"]

    def test_every_timestamp_in_the_pdf_is_pinned(self, built: fx.BuiltFixture) -> None:
        # Two builds in the same second agree whatever the clock says, so the
        # byte comparison alone cannot catch an unpinned date.
        doc = pymupdf.open(built.pdf)
        try:
            dates = [
                doc.xref_get_key(xref, key)[1]
                for xref in range(1, doc.xref_length())
                for key in ("CreationDate", "ModDate", "Params/CreationDate", "Params/ModDate")
                if doc.xref_get_key(xref, key)[0] != "null"
            ]
            assert len(dates) >= 4
            assert set(dates) == {fx.PINNED_DATE}
            assert "Date" not in doc.get_xml_metadata()
        finally:
            doc.close()

    def test_two_builds_give_identical_bytes(
        self, built: fx.BuiltFixture, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        again = fx.build(tmp_path_factory.mktemp("an3_fixture_again"))
        assert again.pdf.read_bytes() == built.pdf.read_bytes()
        assert again.manifest.read_bytes() == built.manifest.read_bytes()

    def test_the_manifest_records_the_pdf_it_describes(
        self, built: fx.BuiltFixture, manifest: dict[str, Any]
    ) -> None:
        assert manifest["pdf_sha256"] == hashlib.sha256(built.pdf.read_bytes()).hexdigest()
        assert manifest["pdf_name"] == built.pdf.name


# --------------------------------------------------------------------------- #
# Criterion 2: every policy category planted, and listed
# --------------------------------------------------------------------------- #


class TestEveryCategoryIsPlanted:
    def test_the_categories_are_the_handoff_table_rows(self) -> None:
        # One id per row of the handoff's §5 A1 table, in its order.
        assert [c for c, _ in fx.CATEGORIES] == [
            "person_name",
            "institution",
            "project_identity",
            "location",
            "facility",
            "dataset_cohort",
            "grant",
            "self_citation",
            "niche_topic",
            "identifying_number",
            "identifying_figure",
        ]

    def test_every_category_has_a_planted_entity(self, manifest: dict[str, Any]) -> None:
        planted = {e["category"] for e in manifest["entities"] if e["plantings"]}
        assert planted == {c for c, _ in fx.CATEGORIES}

    def test_every_regex_class_is_planted(self, manifest: dict[str, Any]) -> None:
        classes = {e["regex_class"] for e in manifest["entities"] if e.get("regex_class")}
        assert classes == set(fx.REGEX_CLASSES)

    def test_every_entity_is_planted_at_least_once(self, manifest: dict[str, Any]) -> None:
        assert all(e["plantings"] for e in manifest["entities"])

    def test_entity_ids_are_unique(self, manifest: dict[str, Any]) -> None:
        ids = [e["id"] for e in manifest["entities"]]
        assert len(ids) == len(set(ids))

    def test_the_named_hard_cases_are_planted(self, manifest: dict[str, Any]) -> None:
        forms = {(p["layer"], p["form"]) for e in manifest["entities"] for p in e["plantings"]}
        layers = {layer for layer, _ in forms}
        assert {"body", "table", "figure_text", "image", "metadata", "xmp"} <= layers
        assert {"embedded_file_name", "reference_list", "header", "footer", "drawing"} <= layers
        kinds = {form for _, form in forms}
        assert {"hyphenated_line_break", "line_break", "initial", "possessive", "diacritic"} <= kinds
        hyphenated = [
            e for e in manifest["entities"]
            if any(p["form"] == "hyphenated_line_break" for p in e["plantings"])
        ]
        assert len(hyphenated) >= 2

    def test_the_niche_topic_is_flagged_and_never_auto_edited(
        self, manifest: dict[str, Any]
    ) -> None:
        niche = [e for e in manifest["entities"] if e["category"] == "niche_topic"]
        assert niche and all(e["auto_edit"] is False for e in niche)
        assert all(e["auto_edit"] is True for e in manifest["entities"] if e not in niche)


class TestTheManifestMatchesThePdf:
    """Each declared planting is where the manifest says, in the form it says."""

    def test_every_text_planting_is_in_its_layer_band(
        self, built: fx.BuiltFixture, manifest: dict[str, Any]
    ) -> None:
        missing = []
        for entity in manifest["entities"]:
            for p in entity["plantings"]:
                if p["layer"] not in fx.TEXT_LAYERS:
                    continue
                band = fx.LAYER_BANDS[(p["page"], p["layer"])]
                if p["text"] not in _page_text(built.pdf, p["page"], band):
                    missing.append((entity["id"], p))
        assert missing == []

    def test_a_layer_band_holds_only_its_own_layer(self, built: fx.BuiltFixture) -> None:
        table = _page_text(built.pdf, fx.SUPERVISOR_TABLE_PAGE,
                           fx.LAYER_BANDS[(fx.SUPERVISOR_TABLE_PAGE, "table")])
        assert "h-index 37" not in table
        assert all(cell in table for row in fx.SUPERVISOR_ROWS for cell in row)

    def test_a_hyphenated_planting_really_breaks_across_lines(
        self, manifest: dict[str, Any]
    ) -> None:
        for entity in manifest["entities"]:
            for p in entity["plantings"]:
                if p["form"] == "hyphenated_line_break":
                    head, tail = p["text"].split("-\n")
                    assert head and tail
                    assert (head + tail).casefold() in entity["surface"].casefold()

    def test_metadata_xmp_and_embedded_plantings_are_in_the_pdf(
        self, built: fx.BuiltFixture, manifest: dict[str, Any]
    ) -> None:
        doc = pymupdf.open(built.pdf)
        try:
            for entity in manifest["entities"]:
                for p in entity["plantings"]:
                    if p["layer"] == "metadata":
                        assert p["text"] in doc.metadata[p["field"]], entity["id"]
                    elif p["layer"] == "xmp":
                        assert p["text"] in doc.get_xml_metadata(), entity["id"]
                    elif p["layer"] == "embedded_file_name":
                        assert p["text"] in doc.embfile_names()[0], entity["id"]
                    elif p["layer"] == "image":
                        assert doc[p["page"] - 1].get_images(full=True), entity["id"]
        finally:
            doc.close()

    def test_every_table_planting_is_its_addressed_cell(
        self, built: fx.BuiltFixture, manifest: dict[str, Any]
    ) -> None:
        doc = pymupdf.open(built.pdf)
        try:
            page = doc[fx.SUPERVISOR_TABLE_PAGE - 1]
            (table,) = page.find_tables(strategy="lines_strict").tables
            cells = table.extract()
        finally:
            doc.close()
        plantings = [p for e in manifest["entities"] for p in e["plantings"]
                     if p["layer"] == "table"]
        assert plantings
        assert [cells[p["row"]][p["col"]] for p in plantings] == [p["text"] for p in plantings]

    def test_every_metric_cell_is_planted(self, manifest: dict[str, Any]) -> None:
        addressed = {(p["row"], p["col"]) for e in manifest["entities"]
                     if e["category"] == "identifying_number"
                     for p in e["plantings"] if p["layer"] == "table"}
        assert addressed == {(row + 1, col) for row in range(len(fx.SUPERVISOR_ROWS))
                             for col in fx.METRIC_COLUMNS}

    def test_the_diagram_planting_is_a_vector_figure(
        self, built: fx.BuiltFixture, manifest: dict[str, Any]
    ) -> None:
        doc = pymupdf.open(built.pdf)
        try:
            for entity in manifest["entities"]:
                for p in entity["plantings"]:
                    if p["layer"] == "drawing":
                        assert doc[p["page"] - 1].get_drawings(), entity["id"]
        finally:
            doc.close()

    def test_every_country_carries_its_status(self, manifest: dict[str, Any]) -> None:
        countries = [e for e in manifest["entities"] if e["eu_status"]]
        assert {e["eu_status"] for e in countries} == {"member_state", "associated_country"}
        assert all(not e["invented"] for e in countries)

    def test_the_manifest_declares_itself_synthetic(self, manifest: dict[str, Any]) -> None:
        assert manifest["record_type"] == fx.MANIFEST_RECORD_TYPE
        assert manifest["synthetic"] is True
        assert all(isinstance(e["invented"], bool) for e in manifest["entities"])
        real = [e for e in manifest["entities"] if not e["invented"]]
        assert all(e["category"] == "location" for e in real)


# --------------------------------------------------------------------------- #
# Criterion 3: the dry import sees what the later stages must handle
# --------------------------------------------------------------------------- #


class TestTheDryImportListsWhatWasPlanted:
    def test_the_supervisor_table_is_listed_with_its_header(
        self, inventory: dict[str, Any]
    ) -> None:
        tables = inventory["tables"]["per_table"]
        assert len(tables) == 1
        table = tables[0]
        assert table["page"] == fx.SUPERVISOR_TABLE_PAGE
        assert table["cols"] == len(fx.SUPERVISOR_TABLE_HEADER)
        assert table["header"] == list(fx.SUPERVISOR_TABLE_HEADER)
        assert table["rows"] == 1 + len(fx.SUPERVISOR_ROWS)
        assert inventory["tables"]["every_row_parses"] is True

    def test_both_figures_are_listed(self, inventory: dict[str, Any]) -> None:
        figures = inventory["figures"]
        assert figures["pages_with_images"] == [fx.LOGO_PAGE]
        assert fx.DIAGRAM_PAGE in figures["pages_with_vector_drawings"]

    def test_the_diagram_carries_a_text_layer(
        self, built: fx.BuiltFixture
    ) -> None:
        text = _page_text(built.pdf, fx.DIAGRAM_PAGE)
        assert all(label in text for label in fx.DIAGRAM_LABELS)

    def test_the_metadata_is_listed(self, inventory: dict[str, Any]) -> None:
        metadata = inventory["metadata"]
        assert metadata["fields"]["author"]["populated"] is True
        assert metadata["fields"]["title"]["populated"] is True
        assert metadata["fields"]["producer"]["populated"] is True
        assert metadata["xmp"]["present"] is True
        assert inventory["figures"]["embedded_files"] == 1

    def test_the_citation_markers_are_listed(self, inventory: dict[str, Any]) -> None:
        counts = inventory["citation_markers"]["counts"]
        assert counts["bracketed_numbers"] >= 3
        assert counts["doi"] >= 2
        assert counts["url"] >= 1

    def test_the_heading_candidates_are_the_fixture_sections(
        self, inventory: dict[str, Any]
    ) -> None:
        assert [c["marker"] for c in inventory["heading_candidates"]] == [
            m for m, _ in fx.SECTIONS
        ]
