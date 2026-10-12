"""V08 — dry-import inventory and original-provenance records.

Acceptance, from ``plans/msca_dn_historical_validation_tickets.md`` V08:

1. A dry-import mode reports measured section, table and figure inventory,
   page count and extraction limitations without writing graph state.
2. Separate intake and original-document provenance records exist, including
   the authenticated input hash of the original PDF.
3. A fidelity acceptance record covers Gantt, diagrams, embedded images,
   footnotes, table headers, bibliographic references and any supporting
   Part B material explicitly.
4. Neither zero character loss nor zero embedded images is accepted as proof
   that graphical evidence was preserved.
5. Unresolved extraction limitations are recorded before assessment, and the
   record states that a page or source span locates an assertion without
   corroborating it.
6. The private original PDF and its derived text are not committed to this
   repository.

The ticket's verification runs the dry import on a non-sensitive fixture
document. This file builds that fixture with pymupdf in a temporary directory
outside the repository, which is also the only place the tool will write for
the submitted document. The real original is the operator's, and
``plans/msca_dn_v08_original_dry_import_procedure.md`` is their procedure.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import dry_import as di  # noqa: E402
from runner.dev_graph.intake import INTAKE_REL, INTAKE_SCHEMA_ID  # noqa: E402
from runner.paths import find_repo_root  # noqa: E402
from tools import dry_import_original as dio  # noqa: E402
from tools import import_external_proposal as ie  # noqa: E402

REPO = find_repo_root()
ORIGINAL = ie.OFFICIAL_ORIGINAL
PROCEDURE = REPO / "plans/msca_dn_v08_original_dry_import_procedure.md"

SUBMISSION_ID = "MSCA-DN-2025-FIXTURE-NOT-THE-REAL-NUMBER"
CALL_ID = "HORIZON-MSCA-2025-DN-01"


def _draw_gantt(page: Any, y0: float) -> None:
    page.draw_line(pymupdf.Point(72, y0), pymupdf.Point(500, y0))
    for n in range(4):
        page.draw_rect(
            pymupdf.Rect(90 + n * 40, y0 + 10 + n * 14, 180 + n * 60, y0 + 22 + n * 14),
            color=(0, 0, 0),
            fill=(0.3, 0.5, 0.8),
        )


@pytest.fixture(scope="module")
def pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A non-sensitive two-page Part B shape, outside the repository."""
    path = tmp_path_factory.mktemp("v08_private") / "fixture_part_b.pdf"
    doc = pymupdf.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((72, 72), "1.1. Research objectives", fontsize=12)
    p1.insert_textbox(
        pymupdf.Rect(72, 100, 520, 180),
        "The network trains 12 doctoral candidates over 36 months across 9 beneficiaries.",
        fontsize=12,
    )
    p1.insert_textbox(
        pymupdf.Rect(72, 700, 520, 730),
        "1 A footnote set below the body size.",
        fontsize=7,
    )
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((72, 72), "3.1. Work plan and resources", fontsize=12)
    _draw_gantt(p2, 140)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture(scope="module")
def sha256(pdf: Path) -> str:
    return hashlib.sha256(pdf.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def out(pdf: Path, sha256: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One dry import of the fixture, run once for the whole module."""
    target = tmp_path_factory.mktemp("v08_out")
    code = dio.main(
        [
            "--pdf", str(pdf),
            "--expect-sha256", sha256,
            "--out", str(target),
            "--submission-id", SUBMISSION_ID,
            "--call-id", CALL_ID,
        ]
    )
    assert code == 0
    return target


def _read(out: Path, name: str) -> dict[str, Any]:
    return json.loads((out / name).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def inventory(out: Path) -> dict[str, Any]:
    return _read(out, dio.INVENTORY_FILE)


@pytest.fixture(scope="module")
def provenance(out: Path) -> dict[str, Any]:
    return _read(out, dio.PROVENANCE_FILE)


@pytest.fixture(scope="module")
def intake(out: Path) -> dict[str, Any]:
    return _read(out, f"{ORIGINAL.intake_id}.json")


# --------------------------------------------------------------------------- #
# Criterion 1 — the dry-import mode
# --------------------------------------------------------------------------- #


class TestTheDryImportMode:
    def test_it_writes_the_six_files_and_nothing_else(self, out: Path) -> None:
        assert sorted(p.name for p in out.iterdir()) == sorted(
            [
                dio.INVENTORY_FILE,
                dio.PROVENANCE_FILE,
                dio.ACCEPTANCE_FILE,
                dio.LIMITATIONS_FILE,
                dio.WORKSHEET_FILE,
                f"{ORIGINAL.intake_id}.json",
            ]
        )

    def test_it_writes_no_graph_state(self, out: Path) -> None:
        """No document record, no source index, no snapshot, no intake
        directory: a dry import produces nothing a snapshot could read."""
        assert not (out / "docs").exists()
        assert not (out / INTAKE_REL).exists()
        names = {p.name for p in out.rglob("*")}
        assert "sources.json" not in names
        assert "snapshots" not in names
        assert "documents" not in names

    def test_the_inventory_reports_the_measured_page_count(self, inventory) -> None:
        assert inventory["pages"] == 2
        assert inventory["page_count_basis"].startswith("derived")

    def test_the_inventory_reports_the_section_candidates_and_no_map(
        self, inventory
    ) -> None:
        assert inventory["section_map"]["declared"] is False
        markers = {h["marker"] for h in inventory["heading_candidates"]}
        assert markers == {"1.1.", "3.1."}

    def test_the_inventory_reports_the_table_and_figure_inventory(
        self, inventory
    ) -> None:
        assert "count" in inventory["tables"]
        assert inventory["figures"]["vector_drawings"] > 0

    def test_the_inventory_reports_the_extraction_limitations(self, inventory) -> None:
        assert set(inventory["limitations"]) >= {
            "ligatures",
            "prose_below_the_largest_point_size",
            "table_cells_not_in_page_reading_order",
        }

    def test_the_inventory_is_the_measurement_seam_unchanged(
        self, pdf: Path, inventory
    ) -> None:
        """The tool adds the operator's declarations around the measurement; it
        does not reinterpret it."""
        measured = di.measure(pdf)
        assert {k: inventory[k] for k in measured} == measured

    def test_the_worksheet_is_what_the_operator_reconciles(self, out: Path) -> None:
        text = (out / dio.WORKSHEET_FILE).read_text(encoding="utf-8")
        assert "1.1." in text and "3.1." in text
        assert "Reconcile" in text
        for spec in di.ACCEPTANCE_ITEMS:
            assert spec.item in text

    def test_the_worksheet_keeps_a_table_cell_on_one_row(self) -> None:
        """A PDF cell's text can carry a newline, and a newline inside a
        markdown cell breaks the row it sits in."""
        assert dio._cell("WP\ntitle: A | B", 90) == "WP title: A \\| B"
        assert dio._cell("x" * 200, 10) == "x" * 9 + "…"

    def test_the_worksheet_counts_read_as_english(self) -> None:
        assert dio._count(1, "page") == "1 page"
        assert dio._count(0, "page") == "0 pages"
        assert dio._count(84, "page") == "84 pages"

    def test_rerunning_it_replays(self, pdf: Path, sha256: str, tmp_path: Path) -> None:
        argv = [
            "--pdf", str(pdf),
            "--expect-sha256", sha256,
            "--submission-id", SUBMISSION_ID,
            "--call-id", CALL_ID,
        ]
        first, second = tmp_path / "a", tmp_path / "b"
        assert dio.main([*argv, "--out", str(first)]) == 0
        assert dio.main([*argv, "--out", str(second)]) == 0
        for name in sorted(p.name for p in first.iterdir()):
            assert (first / name).read_bytes() == (second / name).read_bytes(), name

    def test_inventory_only_writes_the_inventory_and_the_worksheet(
        self, pdf: Path, sha256: str, tmp_path: Path
    ) -> None:
        code = dio.main(
            [
                "--pdf", str(pdf),
                "--expect-sha256", sha256,
                "--out", str(tmp_path),
                "--inventory-only",
            ]
        )
        assert code == 0
        assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
            [dio.INVENTORY_FILE, dio.WORKSHEET_FILE]
        )


# --------------------------------------------------------------------------- #
# Criterion 2 — two records, and an authenticated hash
# --------------------------------------------------------------------------- #


class TestTheProvenanceRecords:
    def test_the_intake_and_the_provenance_are_separate_records(
        self, intake, provenance
    ) -> None:
        assert intake["schema_id"] == INTAKE_SCHEMA_ID
        assert provenance["record_type"] == dio.PROVENANCE_RECORD_TYPE
        assert "sha256" not in intake
        assert provenance["intake"]["intake_id"] == intake["intake_id"]

    def test_the_intake_is_the_originals_own_and_not_the_copys(
        self, intake
    ) -> None:
        assert intake["intake_id"] == ORIGINAL.intake_id
        assert intake["intake_id"] != ie.SANITISED_DERIVATIVE.intake_id
        assert intake["document_id"] == ORIGINAL.document_id
        assert intake["document_id"] != ie.SANITISED_DERIVATIVE.document_id

    def test_the_intake_carries_only_operator_declarations(self, intake) -> None:
        assert intake["submission_id"] == SUBMISSION_ID
        assert intake["call_id"] == CALL_ID
        assert intake["esr_availability"] == "unknown"
        assert intake["esr_reference"] is None

    def test_the_intake_validates_against_its_schema(self, out: Path, intake) -> None:
        from runner.dev_graph.intake import normalise_intake

        assert normalise_intake(intake, "fixture").to_dict() == intake

    def test_the_provenance_carries_the_authenticated_input_hash(
        self, provenance, sha256: str
    ) -> None:
        record = provenance["input"]
        assert record["sha256"] == sha256
        assert record["sha256_declared_by_operator"] == sha256
        assert record["authenticated"] is True
        assert "refuses" in record["authentication"]

    def test_the_provenance_names_the_document_as_the_submitted_text(
        self, provenance
    ) -> None:
        assert provenance["document"]["is_submitted_document"] is True
        assert provenance["document"]["config_id"] == ORIGINAL.config_id
        assert provenance["document"]["title"] == ORIGINAL.title

    def test_the_provenance_states_that_nothing_is_stored_here(
        self, provenance
    ) -> None:
        """Both flags are measured from the paths the run was given, not
        declared from the document's role."""
        storage = provenance["storage"]
        assert storage["pdf_stored_in_this_repository"] is False
        assert storage["derived_text_stored_in_this_repository"] is False
        assert storage["basis"].startswith("measured")

    def test_the_storage_flags_follow_the_paths_and_not_the_role(
        self, pdf: Path, sha256: str, tmp_path: Path
    ) -> None:
        from dataclasses import replace

        copy_like = replace(ORIGINAL, is_submitted_document=False)
        dio.dry_import(
            copy_like,
            pdf=pdf,
            out_dir=tmp_path,
            expected_sha256=sha256,
            declarations=dio.Declarations(submission_id=SUBMISSION_ID, call_id=CALL_ID),
        )
        storage = _read(tmp_path, dio.PROVENANCE_FILE)["storage"]
        assert storage["pdf_stored_in_this_repository"] is False
        assert dio.inside_this_repository(REPO / "runner") is True
        assert dio.inside_this_repository(pdf) is False

    def test_the_provenance_records_no_page_map(self, provenance) -> None:
        assert provenance["page_map"]["declared"] is False

    def test_the_provenance_records_the_extraction_environment(
        self, provenance
    ) -> None:
        assert provenance["extraction_environment"]["pymupdf"] == pymupdf.__version__

    def test_the_provenance_binds_the_three_other_records_by_hash(
        self, out: Path, provenance
    ) -> None:
        for key, name in (
            ("dry_import", dio.INVENTORY_FILE),
            ("acceptance", dio.ACCEPTANCE_FILE),
            ("limitations", dio.LIMITATIONS_FILE),
        ):
            block = provenance[key]
            assert block["record_file"] == name
            assert block["sha256"] == hashlib.sha256((out / name).read_bytes()).hexdigest()

    def test_it_refuses_a_hash_the_bytes_do_not_match(
        self, pdf: Path, tmp_path: Path
    ) -> None:
        code = dio.main(
            [
                "--pdf", str(pdf),
                "--expect-sha256", "0" * 64,
                "--out", str(tmp_path),
                "--submission-id", SUBMISSION_ID,
                "--call-id", CALL_ID,
            ]
        )
        assert code == 1
        assert list(tmp_path.iterdir()) == []

    def test_it_refuses_a_hash_that_is_not_a_hash(
        self, pdf: Path, tmp_path: Path
    ) -> None:
        with pytest.raises(di.DryImportRefused, match="sha256"):
            dio.dry_import(
                ORIGINAL,
                pdf=pdf,
                out_dir=tmp_path,
                expected_sha256="not-a-hash",
                declarations=dio.Declarations(
                    submission_id=SUBMISSION_ID, call_id=CALL_ID
                ),
            )

    def test_it_refuses_a_document_whose_identity_is_undeclared(
        self, pdf: Path, tmp_path: Path, sha256: str
    ) -> None:
        from dataclasses import replace

        nameless = replace(ORIGINAL, title=None, short_name="")
        with pytest.raises(ie.ImportRefused) as exc:
            dio.dry_import(
                nameless,
                pdf=pdf,
                out_dir=tmp_path,
                expected_sha256=sha256,
                declarations=dio.Declarations(
                    submission_id=SUBMISSION_ID, call_id=CALL_ID
                ),
            )
        assert "title" in str(exc.value) and "short_name" in str(exc.value)

    def test_the_official_original_is_dry_importable_as_declared(self) -> None:
        """V07 left it refusing an import for want of a page map. A dry import
        is how the page map is arrived at, so it must not need one."""
        assert ORIGINAL.missing_fields()
        assert ORIGINAL.dry_import_missing_fields() == ()


# --------------------------------------------------------------------------- #
# Criterion 3 — the fidelity acceptance record
# --------------------------------------------------------------------------- #


class TestTheAcceptanceRecord:
    def test_it_covers_the_seven_named_classes(self, out: Path) -> None:
        record = _read(out, dio.ACCEPTANCE_FILE)
        assert [row["item"] for row in record["items"]] == [
            "gantt_chart",
            "diagrams",
            "embedded_images",
            "footnotes",
            "table_headers",
            "bibliographic_references",
            "supporting_part_b_material",
        ]

    def test_every_item_is_unreconciled_and_the_record_is_not_complete(
        self, out: Path
    ) -> None:
        record = _read(out, dio.ACCEPTANCE_FILE)
        assert {row["verdict"] for row in record["items"]} == {"unreconciled"}
        assert record["complete"] is False
        assert di.check_acceptance(record) == []

    def test_the_committed_acceptance_record_is_the_operators_to_fill(
        self, out: Path
    ) -> None:
        record = _read(out, dio.ACCEPTANCE_FILE)
        for row in record["items"]:
            assert row["reconciled_by"] is None
            assert row["basis"] is None


class TestCheckingAFilledRecord:
    """The admissibility rule is a command, not a pasted Python expression."""

    def test_the_untouched_record_checks_clean_and_exits_zero(
        self, out: Path, capsys
    ) -> None:
        code = dio.main(["--check-acceptance", str(out / dio.ACCEPTANCE_FILE)])
        assert code == 0
        assert "admissible as it stands" in capsys.readouterr().out

    def test_an_inadmissible_record_exits_one_and_prints_the_finding(
        self, out: Path, tmp_path: Path, capsys
    ) -> None:
        record = _read(out, dio.ACCEPTANCE_FILE)
        for row in record["items"]:
            if row["item"] == "gantt_chart":
                row.update(
                    verdict="preserved",
                    basis="zero_embedded_images",
                    reconciled_by="operator",
                    reconciled_on="2026-10-12",
                )
        target = tmp_path / "filled.json"
        target.write_text(json.dumps(record), encoding="utf-8")
        assert dio.main(["--check-acceptance", str(target)]) == 1
        printed = capsys.readouterr().out
        assert "measurement_basis_not_proof: gantt_chart" in printed
        assert "not admissible" in printed

    def test_it_measures_nothing_and_needs_no_pdf(self, out: Path) -> None:
        assert dio.main(["--check-acceptance", str(out / dio.ACCEPTANCE_FILE)]) == 0

    def test_it_refuses_a_record_of_another_kind(
        self, out: Path, capsys
    ) -> None:
        assert dio.main(["--check-acceptance", str(out / dio.PROVENANCE_FILE)]) == 1
        assert dio.PROVENANCE_RECORD_TYPE in capsys.readouterr().err

    def test_it_refuses_a_file_that_is_not_there(self, tmp_path: Path) -> None:
        with pytest.raises(di.DryImportRefused, match="not a file"):
            dio.check_filled_acceptance(tmp_path / "absent.json")

    def test_it_refuses_unreadable_json(self, tmp_path: Path) -> None:
        target = tmp_path / "broken.json"
        target.write_text("{not json", encoding="utf-8")
        with pytest.raises(di.DryImportRefused, match="unreadable JSON"):
            dio.check_filled_acceptance(target)

    def test_measuring_without_a_pdf_is_refused_rather_than_argparse_exiting(
        self, capsys
    ) -> None:
        """The three measuring flags stopped being argparse-required so that
        --check-acceptance can stand alone; the refusal names them."""
        assert dio.main([]) == 1
        assert "--pdf, --expect-sha256, --out required" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Criterion 4 — the two zeros are not proof
# --------------------------------------------------------------------------- #


class TestZeroIsNotProof:
    def test_the_fixture_measures_both_zeros_and_still_carries_a_figure(
        self, inventory
    ) -> None:
        assert inventory["figures"]["images_on_any_page"] == 0
        assert inventory["character_accounting"]["pages_with_loss"] == []
        assert inventory["figures"]["vector_drawings"] > 0

    def test_the_acceptance_record_names_the_inadmissible_bases(
        self, out: Path
    ) -> None:
        record = _read(out, dio.ACCEPTANCE_FILE)
        assert set(record["inadmissible_bases_for_preserved"]) >= {
            "zero_character_loss",
            "zero_embedded_images",
        }

    def test_a_preserved_verdict_on_a_zero_count_is_refused(self, out: Path) -> None:
        record = _read(out, dio.ACCEPTANCE_FILE)
        for row in record["items"]:
            if row["item"] == "gantt_chart":
                row.update(
                    verdict="preserved",
                    basis="zero_character_loss",
                    reconciled_by="operator",
                    reconciled_on="2026-10-12",
                )
        findings = di.check_acceptance(record)
        assert [f["code"] for f in findings] == ["measurement_basis_not_proof"]

    def test_the_worksheet_says_so_where_it_reports_the_zeros(self, out: Path) -> None:
        text = (out / dio.WORKSHEET_FILE).read_text(encoding="utf-8")
        assert "not proof" in text.lower()
        assert "vector" in text


# --------------------------------------------------------------------------- #
# Criterion 5 — limitations recorded before assessment
# --------------------------------------------------------------------------- #


class TestTheLimitationsRecord:
    def test_every_limitation_is_unresolved(self, out: Path) -> None:
        record = _read(out, dio.LIMITATIONS_FILE)
        assert record["resolved"] is False
        assert {row["status"] for row in record["limitations"]} == {"Unresolved"}

    def test_it_states_that_a_span_locates_without_corroborating(
        self, out: Path
    ) -> None:
        record = _read(out, dio.LIMITATIONS_FILE)
        assert record["span_statement"] == di.SPAN_LOCATES_STATEMENT

    def test_it_precedes_the_import_and_so_every_assessment(self, out: Path) -> None:
        record = _read(out, dio.LIMITATIONS_FILE)
        assert "before assessment" in record["recorded_when"]

    def test_it_carries_the_undeclared_page_map_as_a_limitation(
        self, out: Path
    ) -> None:
        record = _read(out, dio.LIMITATIONS_FILE)
        assert "no_declared_page_map" in {row["limitation"] for row in record["limitations"]}


# --------------------------------------------------------------------------- #
# Criterion 6 — nothing private reaches this repository
# --------------------------------------------------------------------------- #


class TestNothingPrivateIsCommitted:
    def test_the_tool_refuses_an_output_directory_inside_the_repository(
        self, pdf: Path, sha256: str
    ) -> None:
        with pytest.raises(di.DryImportRefused, match="inside this repository"):
            dio.dry_import(
                ORIGINAL,
                pdf=pdf,
                out_dir=REPO / "workspaces" / "msca_dn" / "v08_scratch",
                expected_sha256=sha256,
                declarations=dio.Declarations(
                    submission_id=SUBMISSION_ID, call_id=CALL_ID
                ),
            )
        assert not (REPO / "workspaces" / "msca_dn" / "v08_scratch").exists()

    def test_no_argument_moves_where_this_repository_is(self) -> None:
        """A caller-supplied root would let an operator point the check at an
        empty directory, write the derived text here anyway, and have the
        provenance record state that nothing was stored here."""
        import inspect

        assert dio.THIS_REPOSITORY == REPO
        assert "repo_root" not in inspect.signature(dio.dry_import).parameters
        assert "repo-root" not in inspect.getsource(dio.main)

    def test_the_tool_refuses_a_pdf_inside_the_repository(self, tmp_path: Path) -> None:
        stored = REPO / ie.REVISION_ORIGINAL.pdf_rel
        if not stored.is_file():  # pragma: no cover - the copy is committed
            pytest.skip("the sanitised candidate is not stored in this checkout")
        with pytest.raises(di.DryImportRefused, match="inside this repository"):
            dio.dry_import(
                ORIGINAL,
                pdf=stored,
                out_dir=tmp_path,
                expected_sha256=hashlib.sha256(stored.read_bytes()).hexdigest(),
                declarations=dio.Declarations(
                    submission_id=SUBMISSION_ID, call_id=CALL_ID
                ),
            )

    def test_the_originals_graph_root_stays_undeclared(self) -> None:
        assert ORIGINAL.workspace_rel is None

    def test_no_intake_record_for_the_original_is_committed(self) -> None:
        matches = list(REPO.rglob(f"{ORIGINAL.intake_id}.json"))
        assert matches == [], matches

    def test_no_document_record_for_the_original_is_committed(self) -> None:
        assert ORIGINAL.document_id is not None
        matches = [
            p
            for p in REPO.glob("**/dev_graph/documents/*")
            if p.name == ORIGINAL.document_id
        ]
        assert matches == [], matches

    def test_the_procedure_document_commits_no_hash_and_no_path(self) -> None:
        """The operator's procedure describes the run. It carries no hash of the
        original and no path into the private network."""
        text = PROCEDURE.read_text(encoding="utf-8")
        import re

        assert re.search(r"\b[0-9a-f]{64}\b", text) is None
        assert "<" in text, "the procedure should use placeholders, not real paths"

    def test_the_procedure_names_the_commands_the_tool_accepts(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        assert "tools.dry_import_original" in text
        for flag in ("--pdf", "--expect-sha256", "--out", "--submission-id", "--call-id"):
            assert flag in text, flag

    def test_the_procedure_states_the_operator_runs_it(self) -> None:
        text = PROCEDURE.read_text(encoding="utf-8")
        assert "has not been run in this repository" in text


# --------------------------------------------------------------------------- #
# The declared document id, held against the record that owns it
# --------------------------------------------------------------------------- #


class TestTheDeclaredDocumentId:
    def test_the_copys_declared_id_equals_the_id_its_intake_record_holds(
        self,
    ) -> None:
        """The intake record is authoritative for an imported document. The
        configuration declares the id so a dry import can author the intake
        record of a document that has none yet; a drift between the two would
        import one document and describe another."""
        from runner.dev_graph.intake import read_esr_intake

        config = ie.SANITISED_DERIVATIVE
        intake = read_esr_intake(REPO / config.workspace_rel, config.intake_id)
        assert config.document_id == intake.document_id

    def test_the_two_documents_declare_different_ids(self) -> None:
        assert ie.SANITISED_DERIVATIVE.document_id != ORIGINAL.document_id

    def test_the_originals_id_carries_none_of_the_copys_vocabulary(self) -> None:
        assert ORIGINAL.document_id is not None
        lowered = ORIGINAL.document_id.lower()
        for word in ("sanitis", "sanitiz", "derivative", "84"):
            assert word not in lowered
