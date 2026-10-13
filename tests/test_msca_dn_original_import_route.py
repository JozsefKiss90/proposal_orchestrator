"""V17 and V18 — the original's configuration route and its register.

Acceptance, from ``plans/msca_dn_historical_validation_tickets.md``:

V17 (the configuration route)
  1. The five fields the official original is missing are declared in a private
     input, never in this repository, and the input is read fail-closed.
  2. Every declared value the dry import measured is checked against that
     measurement, and what cannot be checked is reported as unchecked.
  3. A private graph root is authored outside this repository, by the pattern of
     ``tools/author_msca_dn_workspace.py``, and a root inside it is refused.
  4. A completed configuration inherits nothing from the sanitised copy, and the
     copy's own configuration cannot be redeclared from an input.
  5. Both sanitised configurations still reproduce byte-equal.

V18 (the register of a submitted document)
  1. The submitted text has a register renderer of its own, and neither renderer
     will render the other's document.
  2. Its header declares the submitted document's own facts: no sanitisation, no
     transformation and no reflow.
  3. What the extraction loses is the V08 reconciliation, and the register is
     not authored over an open or inadmissible one.
  4. The integrity audit can still read it: the two declarations it reads are
     there, in the vocabulary it recognises.
  5. No private content reaches this repository.

The verification is this module. It builds a four-page non-sensitive Part B
shape with pymupdf in a temporary directory outside the repository, runs the
V08 dry import over it, authors a configuration input beside it, authors the
private graph root, imports the document and reads the register back. The real
original is the operator's, and
``plans/msca_dn_v08_original_dry_import_procedure.md`` is their procedure.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pytest

pymupdf = pytest.importorskip("pymupdf")

from runner import dry_import as di  # noqa: E402
from runner import original_configuration as oc  # noqa: E402
from runner.dev_graph.intake import INTAKE_REL  # noqa: E402
from runner.paths import find_repo_root  # noqa: E402
from tools import author_msca_dn_workspace as ws  # noqa: E402
from tools import author_original_workspace as ows  # noqa: E402
from tools import dry_import_original as dio  # noqa: E402
from tools import fidelity_declarations as fd  # noqa: E402
from tools import import_external_proposal as ie  # noqa: E402

REPO = find_repo_root()
TEMPLATE = REPO / "tools/original_configuration_template.json"
#: The reader's own source, for the two tests that hold its findings against
#: the cases below. Reading the source is the only way a test notices a finding
#: nobody wrote a case for.
_SOURCE = (REPO / "runner/original_configuration.py").read_text(encoding="utf-8")

SUBMISSION_ID = "MSCA-DN-2025-FIXTURE-NOT-THE-REAL-NUMBER"
CALL_ID = "HORIZON-MSCA-2025-DN-01"
CONFIG_FILE = "original_configuration.json"
DRY_DIR = "v08_dry_import"
WORKSPACE = "workspaces/msca_dn_original"
PRIVATE_DIR = "private/msca_dn_original"
REVISION_ID = "as_submitted_v1"

#: The vocabulary the copy's register header uses about itself. None of it may
#: appear in the submitted document's identity or transformation fields.
_COPY_WORDS = ("saniti", "derivative", "reflow", "generalised")


# --------------------------------------------------------------------------- #
# The fixture document, and the chain over it
# --------------------------------------------------------------------------- #


def _page(doc: Any) -> Any:
    return doc.new_page(width=595, height=842)


def _line(page: Any, y: float, text: str, size: float = 12) -> None:
    page.insert_text((72, y), text, fontsize=size)


@pytest.fixture(scope="module")
def pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A four-page Part B shape: three sections, a work-package header, a figure."""
    path = tmp_path_factory.mktemp("v17_source") / "part_b_as_submitted.pdf"
    doc = pymupdf.open()
    p1 = _page(doc)
    _line(p1, 72, "1.1. Research objectives")
    _line(p1, 110, "The network trains 12 doctoral candidates over 36 months.")
    _line(p1, 140, "Nine beneficiaries host the candidates across four countries.")
    _line(p1, 800, "1 A footnote set below the body size.", size=7)
    p2 = _page(doc)
    _line(p2, 72, "1.2. Research methodology")
    _line(p2, 110, "Three work packages deliver the training programme.")
    p3 = _page(doc)
    _line(p3, 72, "2.1. Impact pathway")
    _line(p3, 110, "Two industrial partners take up the results.")
    p4 = _page(doc)
    _line(p4, 72, "3. Quality and Efficiency of the Implementation")
    _line(p4, 130, "3.1. Work plan and resources")
    _line(p4, 170, "WP Number: 1")
    _line(p4, 200, "WP title: Training programme")
    _line(p4, 230, "Lead participant: Beneficiary A")
    _line(p4, 270, "The work plan runs for 48 months.")
    p4.draw_line(pymupdf.Point(72, 330), pymupdf.Point(500, 330))
    for n in range(3):
        p4.draw_rect(
            pymupdf.Rect(90 + n * 40, 340 + n * 14, 180 + n * 60, 352 + n * 14),
            color=(0, 0, 0),
            fill=(0.3, 0.5, 0.8),
        )
    doc.save(path)
    doc.close()
    return path


@pytest.fixture(scope="module")
def sha256(pdf: Path) -> str:
    return hashlib.sha256(pdf.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def root(pdf: Path, sha256: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The private root: the PDF, the dry import's records, nothing public."""
    base = tmp_path_factory.mktemp("v17_private")
    (base / PRIVATE_DIR).mkdir(parents=True)
    target = base / PRIVATE_DIR / pdf.name
    target.write_bytes(pdf.read_bytes())
    assert dio.main(
        [
            "--pdf", str(target),
            "--expect-sha256", sha256,
            "--out", str(base / DRY_DIR),
            "--submission-id", SUBMISSION_ID,
            "--call-id", CALL_ID,
        ]
    ) == 0
    return base


@pytest.fixture(scope="module")
def inventory(root: Path) -> dict[str, Any]:
    return json.loads(
        (root / DRY_DIR / dio.INVENTORY_FILE).read_text(encoding="utf-8-sig")
    )


def _inventory_sha256(root: Path) -> str:
    return hashlib.sha256((root / DRY_DIR / dio.INVENTORY_FILE).read_bytes()).hexdigest()


def _document(root: Path, sha256: str) -> dict[str, Any]:
    """A complete configuration input for the fixture, as a plain mapping."""
    return {
        "schema": oc.SCHEMA,
        "record_type": oc.RECORD_TYPE,
        "config_id": "official_original",
        "declared_by": "the operator, reconciling against the PDF",
        "declared_on": "2026-10-13",
        "declared_status": "Assumed",
        "status_note": "Declared from the V08 reconciliation of this fixture document.",
        "authenticated_sha256": sha256,
        "measurement": {
            "path": f"{DRY_DIR}/{dio.INVENTORY_FILE}",
            "sha256": _inventory_sha256(root),
        },
        "dry_import_dir": DRY_DIR,
        "workspace_rel": WORKSPACE,
        "declarations_dir_rel": f"{PRIVATE_DIR}/declarations",
        "scorecard_rel": None,
        "expected_pages": 4,
        "body_point_size": "12.0",
        "marker_page_tolerance": 0,
        "sub_sections": [
            {
                "sub_section_id": "1.1",
                "section_id": "excellence_section",
                "declared_pages": [1, 1],
                "marker": "1.1.",
                "declared_title": None,
                "exact_marker": False,
            },
            {
                "sub_section_id": "1.2",
                "section_id": "excellence_section",
                "declared_pages": [2, 2],
                "marker": "1.2.",
                "declared_title": None,
                "exact_marker": False,
            },
            {
                "sub_section_id": "2.1",
                "section_id": "impact_section",
                "declared_pages": [3, 3],
                "marker": "2.1.",
                "declared_title": None,
                "exact_marker": False,
            },
            {
                "sub_section_id": "3.1",
                "section_id": "implementation_section",
                "declared_pages": [4, 4],
                "marker": "3.1.",
                "declared_title": None,
                "exact_marker": False,
            },
        ],
        "criterion_heading_markers": [
            {"section_id": "implementation_section", "marker": "3.", "page": 4}
        ],
        "work_package_layout": {
            "sub_section_id": "3.1",
            "header_labels": ["WP Number:", "WP title:", "Lead participant:"],
            "register_declared_labels": ["WP Number:", "WP title:"],
            "consequence": (
                "A work package whose labels ran into its 'WP Number:' block has no separate "
                "'WP title:' block, so a reader that splits a work package by its labels does "
                "not see its fields."
            ),
        },
        "dn_type": {
            "value": "standard Doctoral Network",
            "marker": "Training programme",
            "page": 4,
        },
        "pages_outside_the_map": [],
        "revisions": [
            {
                "revision_id": REVISION_ID,
                "pdf_rel": f"{PRIVATE_DIR}/part_b_as_submitted.pdf",
                "source_id_prefix": "SRC-DN-ORIG",
                "manifest_name": "MSCA-DN-2025_part_b_as_submitted.json",
                "register_rel": f"{PRIVATE_DIR}/fidelity_register_as_submitted.json",
                "candidate_role": (
                    "Current assessment artifact: the Part B of the 2025 submission, as "
                    "submitted. The submitted text itself."
                ),
                "candidate_version": "as submitted, 4 pages",
                "summary": "The submitted Part B, imported inside the private network.",
                "expected_pages": None,
                "supersedes": None,
                "change_id": None,
            }
        ],
    }


@pytest.fixture
def document(root: Path, sha256: str) -> dict[str, Any]:
    return _document(root, sha256)


@pytest.fixture
def write(root: Path) -> Callable[[dict[str, Any], str], Path]:
    """Write a configuration input under the private root and return its path."""

    def _write(doc: dict[str, Any], name: str = CONFIG_FILE) -> Path:
        path = root / name
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return path

    return _write


@pytest.fixture(scope="module")
def configuration(root: Path, sha256: str) -> oc.OriginalConfiguration:
    """The fixture's configuration, written once and read back."""
    path = root / CONFIG_FILE
    path.write_text(json.dumps(_document(root, sha256), indent=2), encoding="utf-8")
    return oc.load_configuration(path, root)


@pytest.fixture(scope="module")
def report(
    configuration: oc.OriginalConfiguration, root: Path
) -> oc.ConfigurationCheck:
    return oc.check(configuration, root)


@pytest.fixture(scope="module")
def completed(configuration: oc.OriginalConfiguration) -> ie.DocumentConfig:
    return ie.complete_from_input(ie.OFFICIAL_ORIGINAL, configuration)


@pytest.fixture(scope="module")
def reconciled(root: Path) -> dict[str, Any]:
    """The acceptance record, filled in the way the procedure asks."""
    path = root / DRY_DIR / dio.ACCEPTANCE_FILE
    record = json.loads(path.read_text(encoding="utf-8-sig"))
    for row in record["items"]:
        present = row["item"] in {"gantt_chart", "table_headers"}
        row["verdict"] = "preserved" if present else "not_applicable"
        row["basis"] = (
            "operator_page_by_page_check" if present else "not_present_in_this_document"
        )
        row["reconciled_by"] = "the operator"
        row["reconciled_on"] = "2026-10-13"
    record["complete"] = True
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    assert di.check_acceptance(record) == []
    return record


@pytest.fixture(scope="module")
def authored(
    root: Path,
    configuration: oc.OriginalConfiguration,
    reconciled: dict[str, Any],
    completed: ie.DocumentConfig,
) -> list[str]:
    """The private graph root, authored."""
    return ows.author(root, configuration)


@pytest.fixture(scope="module")
def imported(
    root: Path, authored: list[str], completed: ie.DocumentConfig
) -> list[str]:
    """The document, imported under the private root."""
    return ie.author(root, completed)


@pytest.fixture(scope="module")
def register(
    root: Path, imported: list[str], completed: ie.DocumentConfig
) -> dict[str, Any]:
    path = root / completed.revisions[0].register_rel
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# V17 criterion 1 — the input is read fail-closed
# --------------------------------------------------------------------------- #


_REQUIRED = list(oc.REQUIRED_FIELDS)


class TestTheConfigurationInput:
    def test_a_complete_input_reads_back(
        self, configuration: oc.OriginalConfiguration, root: Path
    ) -> None:
        assert configuration.config_id == "official_original"
        assert configuration.path_rel == CONFIG_FILE
        assert configuration.sha256 == hashlib.sha256(
            (root / CONFIG_FILE).read_bytes()
        ).hexdigest()
        assert len(configuration.sub_sections) == 4
        assert configuration.mapped_pages == frozenset({1, 2, 3, 4})

    @pytest.mark.parametrize("field", _REQUIRED, ids=_REQUIRED)
    def test_every_required_field_is_required(
        self, document: dict[str, Any], write: Any, field: str
    ) -> None:
        document.pop(field)
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "missing.json"))
        assert field in str(exc.value)

    @pytest.mark.parametrize("field", ["declared_by", "body_point_size", "dry_import_dir"])
    def test_an_empty_field_is_not_a_declaration(
        self, document: dict[str, Any], write: Any, field: str
    ) -> None:
        document[field] = "   "
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "blank.json"))
        assert field in str(exc.value)

    def test_a_placeholder_is_not_a_declaration(
        self, document: dict[str, Any], write: Any
    ) -> None:
        document["declared_by"] = "<who reconciled the document>"
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "placeholder.json"))
        assert "placeholder" in str(exc.value)

    def test_the_committed_template_is_refused_as_a_configuration(self) -> None:
        """It is the form, not an answer, and it is refused twice over: every
        value is a placeholder, and it sits inside this repository, which no
        private root may contain."""
        with pytest.raises(oc.ConfigurationRefused):
            oc.load_configuration(TEMPLATE)
        with pytest.raises(oc.ConfigurationRefused):
            oc.require_private_root(TEMPLATE.parent)

    def test_the_template_asks_every_required_question(self) -> None:
        form = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        assert form["schema"] == oc.SCHEMA
        assert form["record_type"] == oc.RECORD_TYPE
        for field in oc.REQUIRED_FIELDS:
            assert field in form, field
        for field in ("work_package_layout", "dn_type"):
            assert field in form and form[field] is None, field
        assert not any(ch in json.dumps(form) for ch in ("sha256\": \"a", "sha256\": \"0"))

    def test_the_schema_and_the_record_type_are_both_checked(
        self, document: dict[str, Any], write: Any
    ) -> None:
        for field, value in (("schema", "other/1"), ("record_type", "something_else")):
            doc = dict(document, **{field: value})
            with pytest.raises(oc.ConfigurationRefused) as exc:
                oc.load_configuration(write(doc, "wrong.json"))
            assert field in str(exc.value)

    def test_a_status_outside_the_four_is_refused(
        self, document: dict[str, Any], write: Any
    ) -> None:
        document["declared_status"] = "Verified"
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "status.json"))
        assert "12.2" in str(exc.value)
        assert oc.STATUSES == frozenset({"Confirmed", "Inferred", "Assumed", "Unresolved"})

    def test_a_duplicate_sub_section_or_revision_is_refused(
        self, document: dict[str, Any], write: Any
    ) -> None:
        twice = copy.deepcopy(document)
        twice["sub_sections"].append(copy.deepcopy(twice["sub_sections"][0]))
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(twice, "twice.json"))
        assert "declared twice" in str(exc.value)
        revs = copy.deepcopy(document)
        revs["revisions"].append(copy.deepcopy(revs["revisions"][0]))
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(revs, "twice_rev.json"))
        assert "declared twice" in str(exc.value)

    def test_an_empty_map_and_no_revision_are_both_refused(
        self, document: dict[str, Any], write: Any
    ) -> None:
        for field in ("sub_sections", "revisions"):
            doc = copy.deepcopy(document)
            doc[field] = []
            with pytest.raises(oc.ConfigurationRefused) as exc:
                oc.load_configuration(write(doc, "empty.json"))
            assert "declares no" in str(exc.value)

    @pytest.mark.parametrize("field", ["work_package_layout", "dn_type"])
    def test_the_two_null_answers_have_to_be_written(
        self, document: dict[str, Any], write: Any, field: str
    ) -> None:
        """Null is an answer and silence is not: a document with no
        work-package table says so, and one whose network type nothing checks
        says that too."""
        document.pop(field)
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "silent.json"))
        assert field in str(exc.value)
        document[field] = None
        assert getattr(oc.load_configuration(write(document, "null.json")), field) is None

    def test_a_configuration_outside_the_private_root_is_refused(
        self, document: dict[str, Any], root: Path
    ) -> None:
        outside = root.parent / "outside_configuration.json"
        outside.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(outside, root)
        assert "private root" in str(exc.value)
        assert oc.load_configuration(outside).path_rel == outside.name

    def test_an_exact_marker_needs_a_marker(
        self, document: dict[str, Any], write: Any
    ) -> None:
        document["sub_sections"][0]["exact_marker"] = True
        document["sub_sections"][0]["marker"] = None
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "exact.json"))
        assert "whole block" in str(exc.value)

    @pytest.mark.parametrize("pages", [[0, 2], [3, 1], [1], [1, "2"]])
    def test_declared_pages_must_be_a_page_range(
        self, document: dict[str, Any], write: Any, pages: list[Any]
    ) -> None:
        document["sub_sections"][0]["declared_pages"] = pages
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "pages.json"))
        assert "declared_pages" in str(exc.value)

    def test_a_register_label_the_layout_does_not_carry_is_refused(
        self, document: dict[str, Any], write: Any
    ) -> None:
        document["work_package_layout"]["register_declared_labels"] = ["Nothing:"]
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "labels.json"))
        assert "register_declared_labels" in str(exc.value)

    def test_an_unmapped_page_needs_a_basis(
        self, document: dict[str, Any], write: Any
    ) -> None:
        document["pages_outside_the_map"] = [{"page": 1}]
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(write(document, "basis.json"))
        assert "basis" in str(exc.value)


# --------------------------------------------------------------------------- #
# V17 criterion 2 — the measurement checks the declaration
# --------------------------------------------------------------------------- #


def _mutate(
    doc: dict[str, Any],
    change: Callable[[dict[str, Any], Path], None],
    root: Path,
) -> dict[str, Any]:
    out = copy.deepcopy(doc)
    change(out, root)
    return out


def _doctored_inventory(root: Path, doc: dict[str, Any], drop: str, name: str) -> None:
    """Point the configuration at an inventory missing one measured block."""
    inventory = json.loads(
        (root / DRY_DIR / dio.INVENTORY_FILE).read_text(encoding="utf-8-sig")
    )
    inventory.pop(drop)
    path = root / name
    path.write_text(json.dumps(inventory), encoding="utf-8")
    doc["measurement"] = {
        "path": name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _unreadable_measurement(root: Path, doc: dict[str, Any]) -> None:
    """An inventory whose bytes are the ones declared and are not JSON.

    The hash matches, so the binding passes and the read is what fails. A
    corrupt file is not a wrong file, and the two findings say so separately.
    """
    path = root / "broken_inventory.json"
    path.write_bytes(b"{not json at all")
    doc["measurement"] = {
        "path": "broken_inventory.json",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _unmap_a_sub_section(doc: dict[str, Any]) -> None:
    doc["sub_sections"] = [s for s in doc["sub_sections"] if s["sub_section_id"] != "1.2"]


def _swap_the_map_order(doc: dict[str, Any]) -> None:
    doc["sub_sections"][0]["declared_pages"] = [2, 2]
    doc["sub_sections"][0]["marker"] = "1.2."
    doc["sub_sections"][1]["declared_pages"] = [1, 1]
    doc["sub_sections"][1]["marker"] = "1.1."


#: One mutation per finding, each taking the configuration and the private
#: root. Most touch the configuration alone; four need a second file under the
#: root, because an inventory missing a measured block is not something a
#: configuration can declare.
_MUTATIONS: list[tuple[str, Callable[[dict[str, Any], Path], None]]] = [
    ("page_count_disagrees_with_the_measurement", lambda d, r: d.update(expected_pages=5)),
    ("body_point_size_not_measured", lambda d, r: d.update(body_point_size="11.5")),
    ("body_point_size_is_not_the_largest_share", lambda d, r: d.update(body_point_size="7.0")),
    (
        "marker_not_measured_anywhere",
        lambda d, r: d["sub_sections"][1].update(marker="9.9."),
    ),
    (
        "marker_not_on_its_declared_page",
        lambda d, r: d["sub_sections"][1].update(declared_pages=[3, 3]),
    ),
    (
        "criterion_heading_not_on_its_declared_page",
        lambda d, r: d["criterion_heading_markers"][0].update(page=2),
    ),
    (
        "criterion_heading_not_measured",
        lambda d, r: d["criterion_heading_markers"][0].update(marker="8."),
    ),
    ("page_in_no_sub_section_and_not_declared", lambda d, r: _unmap_a_sub_section(d)),
    (
        "page_declared_outside_a_map_that_covers_it",
        lambda d, r: d.update(pages_outside_the_map=[{"page": 2, "basis": "a cover page"}]),
    ),
    (
        "page_declared_outside_the_document",
        lambda d, r: d.update(
            pages_outside_the_map=[{"page": 99, "basis": "a page nobody supplied"}]
        ),
    ),
    (
        "sub_section_page_beyond_the_document",
        lambda d, r: d["sub_sections"][3].update(declared_pages=[4, 5]),
    ),
    ("page_map_is_not_in_document_order", lambda d, r: _swap_the_map_order(d)),
    (
        "dn_type_page_beyond_the_document",
        lambda d, r: d["dn_type"].update(page=9),
    ),
    (
        "work_package_sub_section_not_in_the_map",
        lambda d, r: d["work_package_layout"].update(sub_section_id="9.9"),
    ),
    (
        "path_outside_the_private_root",
        lambda d, r: d.update(workspace_rel="../elsewhere"),
    ),
    (
        "declared_pdf_absent",
        lambda d, r: d["revisions"][0].update(pdf_rel="private/msca_dn_original/absent.pdf"),
    ),
    (
        "measurement_is_not_the_one_declared",
        lambda d, r: d["measurement"].update(sha256="0" * 64),
    ),
    (
        "measurement_absent",
        lambda d, r: d["measurement"].update(path="v08_dry_import/absent.json"),
    ),
    (
        "measurement_unreadable",
        lambda d, r: _unreadable_measurement(r, d),
    ),
    (
        "heading_candidates_not_measured",
        lambda d, r: _doctored_inventory(r, d, "heading_candidates", "no_headings.json"),
    ),
    (
        "point_sizes_not_measured",
        lambda d, r: _doctored_inventory(r, d, "point_sizes", "no_sizes.json"),
    ),
]
_MUTATION_IDS = [name for name, _change in _MUTATIONS]


class TestTheMeasurementChecksTheDeclaration:
    def test_the_fixture_configuration_agrees_with_its_measurement(
        self, report: oc.ConfigurationCheck
    ) -> None:
        assert report.findings == (), report.findings
        assert report.green is True
        assert report.measured_pages == report.declared_pages == 4
        assert report.mapped_pages == 4

    @pytest.mark.parametrize("name,change", _MUTATIONS, ids=_MUTATION_IDS)
    def test_one_change_at_a_time_is_reported(
        self,
        document: dict[str, Any],
        root: Path,
        write: Any,
        name: str,
        change: Callable[[dict[str, Any], Path], None],
    ) -> None:
        mutated = _mutate(document, change, root)
        configuration = oc.load_configuration(write(mutated, "mutated.json"), root)
        report = oc.check(configuration, root)
        assert name in [finding for finding, _detail in report.findings], report.findings
        assert not report.green

    def test_every_finding_the_module_can_raise_has_a_case(
        self, document: dict[str, Any], root: Path, write: Any
    ) -> None:
        """A finding no case produces is a refusal nobody measured.

        The names come from the module's own source rather than from a list
        here, so a finding added to the reader and not to this file fails. The
        three the sweep above cannot reach each have a case of their own, and
        they are named here rather than left to be noticed.
        """
        declared = set(
            re.findall(r'finding\(\s*\n?\s*"([a-z_]+)"', _SOURCE)
        )
        assert len(declared) >= 20, declared
        produced: set[str] = set()
        for name, change in _MUTATIONS:
            mutated = _mutate(document, change, root)
            configuration = oc.load_configuration(write(mutated, "sweep.json"), root)
            report = oc.check(configuration, root)
            produced.update(finding for finding, _detail in report.findings)
            assert name in produced, name
        by_a_case_of_its_own = {
            "measurement_measured_another_file",
            "declared_pdf_is_not_the_authenticated_file",
            "measurement_is_not_a_dry_import",
            "revision_supersedes_an_unknown_revision",
        }
        assert declared - produced == by_a_case_of_its_own, declared - produced
        assert len(set(_MUTATION_IDS)) == len(_MUTATION_IDS)

    def test_every_unchecked_answer_the_module_can_report_has_a_case(self) -> None:
        """The same rule for the other direction: an answer reported as
        unchecked is an answer that passed without a measurement, so each one
        is named by a case above."""
        declared = set(
            re.findall(r'unchecked\.append\(\s*\n?\s*\(\s*\n?\s*"([a-z_]+)"', _SOURCE)
        )
        assert declared == {
            "sub_section_opens_the_document",
            "marker_is_a_whole_block",
            "work_package_layout_declared_as_none",
            "later_revision_hash_not_authenticated_here",
        }

    def test_a_measurement_of_another_file_is_reported(
        self, document: dict[str, Any], root: Path, write: Any
    ) -> None:
        other = hashlib.sha256(b"another file entirely").hexdigest()
        mutated = _mutate(document, lambda d, r: d.update(authenticated_sha256=other), root)
        report = oc.check(oc.load_configuration(write(mutated, "other.json"), root), root)
        names = [finding for finding, _detail in report.findings]
        assert "measurement_measured_another_file" in names
        assert "declared_pdf_is_not_the_authenticated_file" in names

    def test_a_measurement_that_is_not_a_dry_import_is_reported(
        self, document: dict[str, Any], root: Path, write: Any
    ) -> None:
        path = f"{DRY_DIR}/{dio.ACCEPTANCE_FILE}"
        sha = hashlib.sha256((root / path).read_bytes()).hexdigest()
        mutated = _mutate(
            document, lambda d, r: d["measurement"].update(path=path, sha256=sha), root
        )
        report = oc.check(oc.load_configuration(write(mutated, "notdry.json"), root), root)
        assert "measurement_is_not_a_dry_import" in [n for n, _d in report.findings]

    def test_a_revision_superseding_an_unknown_one_is_reported(
        self, document: dict[str, Any], root: Path, write: Any
    ) -> None:
        def add(doc: dict[str, Any], _root: Path) -> None:
            later = copy.deepcopy(doc["revisions"][0])
            later.update(
                revision_id="as_submitted_v2",
                source_id_prefix="SRC-DN-ORIG-V2",
                manifest_name="later.json",
                register_rel=f"{PRIVATE_DIR}/fidelity_register_later.json",
                supersedes="a_revision_nobody_declared",
            )
            doc["revisions"].append(later)

        report = oc.check(
            oc.load_configuration(write(_mutate(document, add, root), "later.json"), root),
            root,
        )
        assert "revision_supersedes_an_unknown_revision" in [n for n, _d in report.findings]

    def test_a_later_revisions_bytes_are_not_authenticated_here(
        self, document: dict[str, Any], root: Path, write: Any
    ) -> None:
        def add(doc: dict[str, Any], _root: Path) -> None:
            later = copy.deepcopy(doc["revisions"][0])
            later.update(
                revision_id="as_submitted_v2",
                source_id_prefix="SRC-DN-ORIG-V2",
                manifest_name="later.json",
                register_rel=f"{PRIVATE_DIR}/fidelity_register_later.json",
                supersedes=REVISION_ID,
            )
            doc["revisions"].append(later)

        report = oc.check(
            oc.load_configuration(write(_mutate(document, add, root), "chain.json"), root),
            root,
        )
        assert report.green, report.findings
        assert "later_revision_hash_not_authenticated_here" in [
            n for n, _d in report.unchecked
        ]

    def test_what_the_measurement_cannot_reach_is_reported_unchecked(
        self, document: dict[str, Any], root: Path, write: Any
    ) -> None:
        """Three answers no candidate heading confirms: a sub-section the
        document opens with, one whose marker is a whole block, and a document
        with no work-package table. None is a finding, and none passes as
        checked either."""
        def loosen(doc: dict[str, Any], _root: Path) -> None:
            doc["sub_sections"][0].update(marker=None, declared_title="Objectives")
            doc["sub_sections"][1].update(
                marker="Beneficiary A", exact_marker=True, declared_title="Participants"
            )
            doc["work_package_layout"] = None

        configuration = oc.load_configuration(
            write(_mutate(document, loosen, root), "unchecked.json"), root
        )
        report = oc.check(configuration, root)
        names = [name for name, _detail in report.unchecked]
        assert report.green, report.findings
        assert "sub_section_opens_the_document" in names
        assert "marker_is_a_whole_block" in names
        assert "work_package_layout_declared_as_none" in names

    def test_the_summary_carries_names_and_counts_and_no_declared_value(
        self, report: oc.ConfigurationCheck, sha256: str
    ) -> None:
        text = "\n".join(report.lines())
        assert "findings: 0" in text
        assert sha256 not in text
        assert SUBMISSION_ID not in text


# --------------------------------------------------------------------------- #
# V17 criterion 3 — the private root
# --------------------------------------------------------------------------- #


class TestThePrivateRoot:
    def test_a_root_inside_this_repository_is_refused(self) -> None:
        for inside in (REPO, REPO / "workspaces", REPO / "tools"):
            with pytest.raises(oc.ConfigurationRefused) as exc:
                oc.require_private_root(inside)
            assert "inside this repository" in str(exc.value)

    def test_what_inside_means_is_the_modules_own_location(self) -> None:
        """Not an argument and not the working directory: the rule V08 set for
        the dry import, so no flag can point the check at an empty directory."""
        assert oc.THIS_REPOSITORY == REPO
        assert oc.inside_this_repository(REPO / "runner/original_configuration.py")

    def test_the_private_root_of_this_fixture_is_outside(self, root: Path) -> None:
        assert not oc.inside_this_repository(root)
        assert oc.require_private_root(root) == root.resolve()

    def test_the_skeleton_is_the_copys_pattern(
        self, authored: list[str], root: Path
    ) -> None:
        assert sorted(authored) == sorted(
            [
                f"{WORKSPACE}/README.md",
                f"{WORKSPACE}/{INTAKE_REL}/msca-dn-2025-original.json",
                f"{WORKSPACE}/{Path(INTAKE_REL).parent.as_posix()}/documents/.gitkeep",
                f"{WORKSPACE}/{Path(INTAKE_REL).parent.as_posix()}/snapshots/.gitkeep",
                f"{WORKSPACE}/{Path(INTAKE_REL).parent.as_posix()}/packages/.gitkeep",
            ]
        )

    def test_authoring_twice_changes_nothing(
        self, root: Path, configuration: oc.OriginalConfiguration, authored: list[str]
    ) -> None:
        assert ows.author(root, configuration) == []
        assert ows.check(root, configuration) == []

    def test_the_intake_is_the_dry_imports_own_record(
        self, root: Path, authored: list[str]
    ) -> None:
        recorded = json.loads(
            (root / WORKSPACE / INTAKE_REL / "msca-dn-2025-original.json").read_text(
                encoding="utf-8"
            )
        )
        authored_by_dry_import = json.loads(
            (root / DRY_DIR / "msca-dn-2025-original.json").read_text(encoding="utf-8-sig")
        )
        assert recorded == authored_by_dry_import
        assert recorded["submission_id"] == SUBMISSION_ID
        assert recorded["call_id"] == CALL_ID

    def test_the_readme_names_this_documents_own_ids(
        self, root: Path, authored: list[str], completed: ie.DocumentConfig
    ) -> None:
        text = (root / WORKSPACE / "README.md").read_text(encoding="utf-8")
        assert completed.source_id(completed.revisions[0], 1) in text
        assert "msca-dn-2025-original" in text
        assert "the submitted text itself" in text
        for word in ("sanitised", "derivative", "84"):
            assert word not in text, word

    def test_the_cli_refuses_a_root_inside_this_repository(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = ows.main(["--root", str(REPO), "--config-input", CONFIG_FILE])
        assert code == 1
        assert "inside this repository" in capsys.readouterr().err

    def test_the_cli_checks_the_authored_root(
        self, root: Path, authored: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = ows.main(
            ["--root", str(root), "--config-input", CONFIG_FILE, "--check"]
        )
        assert code == 0
        assert "up to date" in capsys.readouterr().out

    def test_the_cli_reports_a_disagreeing_configuration_and_writes_nothing(
        self, root: Path, document: dict[str, Any], write: Any,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write(_mutate(document, lambda d, r: d.update(expected_pages=9), root), "cli.json")
        code = ows.main(["--root", str(root), "--config-input", "cli.json"])
        assert code == 1
        captured = capsys.readouterr()
        assert "page_count_disagrees_with_the_measurement" in captured.out
        assert "nothing was written" in captured.err


# --------------------------------------------------------------------------- #
# V17 criterion 4 — nothing is inherited, and nothing committed is redeclared
# --------------------------------------------------------------------------- #


class TestCompletingTheDocument:
    def test_the_five_missing_fields_are_the_ones_the_input_declares(self) -> None:
        assert set(ie.OFFICIAL_ORIGINAL.missing_fields()) == {
            "workspace_rel",
            "sub_sections",
            "expected_pages",
            "body_point_size",
            "revisions",
        }

    def test_a_completed_configuration_is_importable(
        self, completed: ie.DocumentConfig
    ) -> None:
        assert completed.missing_fields() == ()
        completed.require_complete()
        assert completed.is_submitted_document is True

    def test_nothing_is_inherited_from_the_copy(
        self, completed: ie.DocumentConfig
    ) -> None:
        copy_config = ie.SANITISED_DERIVATIVE
        assert completed.expected_pages != copy_config.expected_pages
        assert completed.workspace_rel != copy_config.workspace_rel
        assert completed.intake_id != copy_config.intake_id
        assert completed.declarations_dir_rel != copy_config.declarations_dir_rel
        prefixes = {r.source_id_prefix for r in completed.revisions}
        assert prefixes.isdisjoint({r.source_id_prefix for r in copy_config.revisions})
        described = " ".join(
            str(getattr(completed, field))
            for field in (
                "title", "role", "short_name", "page_statement", "reader_caveat",
                "claim_ledger_note", "status_note", "first_revision_key",
            )
        ).lower()
        for word in _COPY_WORDS:
            assert word not in described, word

    def test_an_input_naming_another_document_is_refused(
        self, configuration: oc.OriginalConfiguration
    ) -> None:
        with pytest.raises(ie.ImportRefused) as exc:
            ie.complete_from_input(ie.SANITISED_DERIVATIVE, configuration)
        assert "official_original" in str(exc.value)

    def test_a_complete_document_may_not_be_redeclared_from_an_input(
        self, document: dict[str, Any], root: Path, write: Any
    ) -> None:
        """The copy's manifests are bound by hash into the frozen baseline, so
        its page map is not a runtime argument."""
        mutated = _mutate(
            document, lambda d, r: d.update(config_id="sanitised_derivative"), root
        )
        configuration = oc.load_configuration(write(mutated, "copy.json"), root)
        with pytest.raises(ie.ImportRefused) as exc:
            ie.complete_from_input(ie.SANITISED_DERIVATIVE, configuration)
        assert "already complete" in str(exc.value)

    def test_the_page_map_provenance_names_the_input_and_its_hash(
        self, completed: ie.DocumentConfig, configuration: oc.OriginalConfiguration
    ) -> None:
        declared = completed.page_map_declared_from
        assert CONFIG_FILE in declared
        assert configuration.sha256 in declared
        assert "No page map is declared here yet" not in declared
        assert "No page map is declared here yet" in ie.OFFICIAL_ORIGINAL.page_map_declared_from

    def test_the_status_note_names_the_measurement_that_checked_it(
        self, completed: ie.DocumentConfig, configuration: oc.OriginalConfiguration
    ) -> None:
        note = completed.status_note
        assert configuration.measurement_sha256 in note
        assert "runner/original_configuration.py" in note
        assert "unchecked" in note

    def test_the_completed_revision_resolves_to_the_original(
        self, completed: ie.DocumentConfig
    ) -> None:
        resolved = ie.config_for(completed.revisions[0])
        assert resolved.config_id == "official_original"
        assert resolved.expected_pages == completed.expected_pages

    def test_a_document_this_tool_does_not_declare_cannot_be_registered(
        self, completed: ie.DocumentConfig
    ) -> None:
        with pytest.raises(ie.ImportRefused) as exc:
            ie.register_document(replace(completed, config_id="a_third_document"))
        assert "not one this tool declares" in str(exc.value)

    def test_a_revision_the_copy_owns_cannot_be_taken(
        self, completed: ie.DocumentConfig
    ) -> None:
        stolen = replace(
            completed,
            revisions=(
                replace(completed.revisions[0], revision_id=ie.REVISION_ORIGINAL.revision_id),
            ),
        )
        with pytest.raises(ie.ImportRefused) as exc:
            ie.register_document(stolen)
        assert "already belongs to document" in str(exc.value)

    def test_the_declaration_contract_is_this_documents_own(
        self, completed: ie.DocumentConfig
    ) -> None:
        contract = completed.declaration_contract()
        assert contract.required_fields == ("presence", "extraction_fidelity")
        assert contract.record_type == "extraction_fidelity_declarations"
        assert contract.dir_rel == Path(f"{PRIVATE_DIR}/declarations")
        assert "transformation" not in contract.required_fields

    def test_the_copys_contract_is_the_module_default(self) -> None:
        assert ie.SANITISED_DERIVATIVE.declaration_contract() == fd.DEFAULT_CONTRACT
        assert fd.DEFAULT_CONTRACT.required_fields == ("presence", "transformation")
        assert fd.DEFAULT_CONTRACT.dir_rel == fd.DECLARATIONS_DIR_REL


# --------------------------------------------------------------------------- #
# V18 — the register of a submitted document
# --------------------------------------------------------------------------- #


class TestNeitherRendererRendersTheOthersDocument:
    def test_the_copys_renderer_refuses_the_submitted_text(
        self, root: Path, completed: ie.DocumentConfig
    ) -> None:
        with pytest.raises(ws.AuthoringError) as exc:
            ws.render_register(root, completed.revisions[0])
        message = str(exc.value)
        assert "submitted text" in message
        assert "sanitised derivative" in message

    def test_this_renderer_refuses_the_copy(self) -> None:
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows.render_submitted_register(REPO, ie.REVISION_ORIGINAL)
        assert "not the submitted text" in str(exc.value)

    def test_the_importer_chooses_by_the_documents_own_flag(
        self, root: Path, register: dict[str, Any], completed: ie.DocumentConfig
    ) -> None:
        chosen = ie.register_of(root, completed.revisions[0])
        assert chosen["provenance"]["current_assessment_artifact"]["is_submitted_document"]
        assert chosen == register
        copys = ie.register_of(REPO, ie.REVISION_ORIGINAL)
        assert copys["provenance"]["current_assessment_artifact"]["is_submitted_document"] is False

    def test_both_registers_carry_the_same_record_type(self) -> None:
        """One type, because one set of readers: the integrity audit reads the
        provenance header of whichever document it was pointed at."""
        assert ows.REGISTER_RECORD_TYPE == ws.REGISTER_RECORD_TYPE == "fidelity_register"


class TestTheHeaderDeclaresTheSubmittedDocumentsOwnFacts:
    def test_the_assessed_file_is_the_authenticated_original(
        self, register: dict[str, Any], sha256: str
    ) -> None:
        artifact = register["provenance"]["current_assessment_artifact"]
        assert artifact["sha256"] == sha256
        assert artifact["authentication"]["declared_sha256"] == sha256
        assert artifact["is_submitted_document"] is True
        assert artifact["pages"] == 4

    def test_no_transformation_reflow_or_sanitisation_is_declared(
        self, register: dict[str, Any]
    ) -> None:
        transformation = register["provenance"]["transformation"]
        assert transformation["applied"] is False
        assert transformation["reflow"]["applied"] is False
        assert transformation["declared_status"] == "Confirmed"
        assert "saniti" not in json.dumps(register["provenance"]).lower()
        # The values that say what this document is. One sentence elsewhere
        # does use the word 'reflowed', to say this document is not one.
        identity = json.dumps(
            [
                register["provenance"]["current_assessment_artifact"]["kind"],
                register["provenance"]["historical_submission"]["instrument"],
                transformation["identifiers"],
                transformation["citations"],
                transformation["prose"],
                transformation["figures"],
            ]
        ).lower()
        for word in ("reflow", "generalised", "derivative", "84"):
            assert word not in identity, word

    def test_the_absent_transformation_is_not_a_claim_of_preservation(
        self, register: dict[str, Any]
    ) -> None:
        statement = register["provenance"]["transformation"]["statement"]
        assert "not a declaration that the extraction preserved everything" in statement

    def test_the_relationship_to_the_esr_is_the_copys_inverted(
        self, register: dict[str, Any]
    ) -> None:
        statement = register["provenance"]["relationship_to_esr"]["statement"]
        assert "The ESR evaluated this text" in statement
        assert register["provenance"]["relationship_to_esr"]["esr_sha256"] is None

    def test_the_network_type_is_checked_on_the_page_it_is_declared_on(
        self, register: dict[str, Any]
    ) -> None:
        dn_type = register["provenance"]["historical_submission"]["dn_type"]
        assert dn_type["value"] == "standard Doctoral Network"
        assert dn_type["declared_status"] == "Confirmed"
        assert "p. 4" in dn_type["basis"]

    def test_an_undeclared_network_type_is_unresolved_and_not_the_copys(
        self, root: Path, document: dict[str, Any], write: Any,
        completed: ie.DocumentConfig,
    ) -> None:
        configuration = oc.load_configuration(
            write(_mutate(document, lambda d, r: d.update(dn_type=None), root), "nodn.json"),
            root,
        )
        block = ows._network_type(root, completed.revisions[0], configuration)
        assert block["value"] is None
        assert block["declared_status"] == "Unresolved"
        assert "not this document's" in block["basis"]

    def test_a_network_type_phrase_not_on_its_page_refuses(
        self, root: Path, document: dict[str, Any], write: Any,
        completed: ie.DocumentConfig,
    ) -> None:
        def elsewhere(doc: dict[str, Any], _root: Path) -> None:
            doc["dn_type"] = {"value": "joint doctorate", "marker": "Joint Doctorate", "page": 1}

        configuration = oc.load_configuration(
            write(_mutate(document, elsewhere, root), "wrongdn.json"), root
        )
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows._network_type(root, completed.revisions[0], configuration)
        assert "does not carry it" in str(exc.value)

    def test_the_storage_block_is_measured_not_declared(
        self, register: dict[str, Any]
    ) -> None:
        storage = register["provenance"]["storage"]
        assert storage["stored_in_the_public_repository"] is False
        assert "measured" in storage["basis"]


class TestTheReconciliationIsTheFidelityEvidence:
    def test_the_register_carries_every_reconciled_class(
        self, register: dict[str, Any], reconciled: dict[str, Any]
    ) -> None:
        block = register["provenance"]["extraction_reconciliation"]
        assert block["complete"] is True
        assert block["classes_reconciled"] == len(di.ACCEPTANCE_ITEMS)
        assert set(block["verdicts"]) == {spec.item for spec in di.ACCEPTANCE_ITEMS}
        assert block["not_proof"] == di.GRAPHICAL_PROOF_STATEMENT

    def test_an_open_reconciliation_refuses_the_register(
        self, root: Path, configuration: oc.OriginalConfiguration
    ) -> None:
        records = ows.read_dry_import(
            root, configuration, "msca-dn-2025-original", "MSCA-DN-2025_part_b_as_submitted"
        )
        open_record = copy.deepcopy(dict(records.acceptance))
        open_record["complete"] = False
        open_record["items"][0]["verdict"] = "unreconciled"
        open_record["items"][0]["basis"] = None
        open_record["items"][0]["reconciled_by"] = None
        open_record["items"][0]["reconciled_on"] = None
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows.require_complete_reconciliation(
                replace(records, acceptance=open_record)
            )
        message = str(exc.value)
        assert "not complete" in message
        assert di.ACCEPTANCE_ITEMS[0].item in message

    def test_a_record_marked_complete_over_an_open_item_is_inadmissible(
        self, root: Path, configuration: oc.OriginalConfiguration
    ) -> None:
        """V08's own finding, enforced here: the record says complete and an
        item says unreconciled, so the claim and the evidence disagree."""
        records = ows.read_dry_import(
            root, configuration, "msca-dn-2025-original", "MSCA-DN-2025_part_b_as_submitted"
        )
        lying = copy.deepcopy(dict(records.acceptance))
        lying["items"][0]["verdict"] = "unreconciled"
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows.require_complete_reconciliation(replace(records, acceptance=lying))
        assert "complete_with_unreconciled_item" in str(exc.value)

    def test_an_inadmissible_reconciliation_refuses_the_register(
        self, root: Path, configuration: oc.OriginalConfiguration
    ) -> None:
        """A 'preserved' verdict resting on a measurement equally true of a
        document whose figures are gone. V08 reports it; this refuses on it."""
        records = ows.read_dry_import(
            root, configuration, "msca-dn-2025-original", "MSCA-DN-2025_part_b_as_submitted"
        )
        bad = copy.deepcopy(dict(records.acceptance))
        bad["items"][0]["verdict"] = "preserved"
        bad["items"][0]["basis"] = "zero_character_loss"
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows.require_complete_reconciliation(replace(records, acceptance=bad))
        assert "measurement_basis_not_proof" in str(exc.value)

    def test_the_v08_records_are_each_bound_by_their_own_bytes(
        self, register: dict[str, Any], root: Path
    ) -> None:
        provenance = register["provenance"]
        bound = {
            provenance["extraction_reconciliation"]["record_file"]: provenance[
                "extraction_reconciliation"
            ]["sha256"],
            provenance["unresolved_extraction_limitations"]["record_file"]: provenance[
                "unresolved_extraction_limitations"
            ]["sha256"],
            provenance["document_provenance"]["record_file"]: provenance[
                "document_provenance"
            ]["sha256"],
        }
        from runner.atomic_write import canonical_json_bytes

        for rel, recorded in bound.items():
            record = json.loads((root / rel).read_text(encoding="utf-8-sig"))
            assert recorded == hashlib.sha256(canonical_json_bytes(record)).hexdigest(), rel

    def test_the_span_statement_travels_with_the_limitations(
        self, register: dict[str, Any]
    ) -> None:
        block = register["provenance"]["unresolved_extraction_limitations"]
        assert block["span_locates_statement"] == di.SPAN_LOCATES_STATEMENT
        assert block["limitations_recorded"] >= 1

    def test_a_reconciliation_over_other_bytes_is_refused(
        self, root: Path, document: dict[str, Any], write: Any
    ) -> None:
        other = hashlib.sha256(b"not this document").hexdigest()
        mutated = _mutate(document, lambda d, r: d.update(authenticated_sha256=other), root)
        configuration = oc.load_configuration(write(mutated, "mismatch.json"), root)
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows.read_dry_import(
                root, configuration, "msca-dn-2025-original", "MSCA-DN-2025_part_b_as_submitted"
            )
        assert "one document's reconciliation as another's" in str(exc.value)

    def test_an_intake_under_another_id_or_document_is_refused(
        self, root: Path, configuration: oc.OriginalConfiguration
    ) -> None:
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows.read_dry_import(root, configuration, "msca-dn-2025-original", "another-document")
        assert "names document" in str(exc.value)
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows.read_dry_import(root, configuration, "another-intake", None)
        assert "not under the private root" in str(exc.value)


class TestTheDeclaredHalfAsksTheSubmittedDocumentsQuestion:
    def test_its_two_fields_are_presence_and_extraction_fidelity(
        self, register: dict[str, Any]
    ) -> None:
        half = register["declared"]
        assert half["fields_per_sub_section"] == ["presence", "extraction_fidelity"]
        assert "transformation" not in half["fields_per_sub_section"]
        assert half["input_contract"]["record_type"] == "extraction_fidelity_declarations"
        assert half["input_contract"]["directory"] == f"{PRIVATE_DIR}/declarations"

    def test_it_says_the_third_claim_does_not_arise_here(
        self, register: dict[str, Any]
    ) -> None:
        assert "this document is the original" in register["declared"]["note"]

    def test_an_empty_input_is_an_empty_half(self, register: dict[str, Any]) -> None:
        assert register["declared"]["sub_sections"] == []
        assert fd.INPUT_BLOCK_KEY not in register["declared"]

    def test_a_declaration_under_the_private_root_reaches_the_register(
        self, root: Path, completed: ie.DocumentConfig, register: dict[str, Any]
    ) -> None:
        contract = completed.declaration_contract()
        path = root / contract.dir_rel / f"{REVISION_ID}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "record_type": contract.record_type,
                    "revision_id": REVISION_ID,
                    "sub_sections": [
                        {
                            "sub_section_id": "1.1",
                            "presence": {"value": "present", "basis": "read against p. 1"},
                            "extraction_fidelity": {
                                "value": "the footnote extracted away from its marker",
                                "basis": "operator page-by-page check",
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        try:
            rendered = ows.render_submitted_register(root, completed.revisions[0])
            rows = rendered["declared"]["sub_sections"]
            assert [row["sub_section_id"] for row in rows] == ["1.1"]
            assert rows[0]["extraction_fidelity"]["value"].startswith("the footnote")
            assert rendered["declared"][fd.INPUT_BLOCK_KEY]["sha256"] == fd.file_sha256(path)
        finally:
            path.unlink()

    def test_the_copys_record_type_is_refused_here(
        self, root: Path, completed: ie.DocumentConfig
    ) -> None:
        contract = completed.declaration_contract()
        path = root / contract.dir_rel / f"{REVISION_ID}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "record_type": fd.DECLARATIONS_RECORD_TYPE,
                    "revision_id": REVISION_ID,
                    "sub_sections": [],
                }
            ),
            encoding="utf-8",
        )
        try:
            with pytest.raises(fd.FidelityDeclarationsError) as exc:
                ows.render_submitted_register(root, completed.revisions[0])
            assert "extraction_fidelity_declarations" in str(exc.value)
        finally:
            path.unlink()

    def test_a_transformation_declaration_is_not_a_reconciliation(
        self, root: Path, completed: ie.DocumentConfig
    ) -> None:
        """The copy's two fields do not satisfy this document's contract: a
        row that declares a transformation of the submitted text and no
        extraction fidelity is refused, naming the field it owes."""
        contract = completed.declaration_contract()
        path = root / contract.dir_rel / f"{REVISION_ID}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "record_type": contract.record_type,
                    "revision_id": REVISION_ID,
                    "sub_sections": [
                        {
                            "sub_section_id": "1.1",
                            "presence": {"value": "present"},
                            "transformation": {"value": "identifiers generalised"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        try:
            with pytest.raises(fd.FidelityDeclarationsError) as exc:
                ows.render_submitted_register(root, completed.revisions[0])
            assert "extraction_fidelity" in str(exc.value)
        finally:
            path.unlink()


class TestTheIntegrityAuditCanStillReadIt:
    def test_the_audit_resolves_the_provenance_of_the_private_candidate(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        """End to end through the audit's own reader: it finds the manifest in
        the private graph root, reads the register the manifest names, and
        reports the identity scope of the submitted text."""
        from harness import candidate_provenance as cp

        resolved = cp.resolve_provenance(
            repo_root=root,
            graph_root=root / WORKSPACE,
            document_id=completed.document_id or "",
        )
        assert resolved.is_submitted_document is True
        assert resolved.identity_scope == cp.IDENTITY_AS_SUBMITTED
        assert resolved.expected_ledger_status == "unresolved"

    def test_the_two_declarations_it_reads_are_in_its_vocabulary(
        self, register: dict[str, Any]
    ) -> None:
        from harness import candidate_provenance as cp

        transformation = register["provenance"]["transformation"]
        assert cp.declared_word(transformation["identifiers"]) in cp.IDENTIFIERS_AS_SUBMITTED_WORDS
        assert cp.declared_word(transformation["citations"]) in cp.CITATIONS_PRESENT_WORDS

    def test_a_document_citing_nothing_measured_leaves_the_cause_unresolved(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        """The fixture carries no citation marker, so the audit flags the
        difference between a declared presence and a measured absence rather
        than naming a cause. The real original's measured count decides it."""
        from harness import candidate_provenance as cp

        resolved = cp.resolve_provenance(
            repo_root=root,
            graph_root=root / WORKSPACE,
            document_id=completed.document_id or "",
        )
        assert resolved.grounding_cause == cp.CAUSE_UNSTATED
        assert any("measured none" in flag for flag in resolved.flags)


# --------------------------------------------------------------------------- #
# The import under the private root
# --------------------------------------------------------------------------- #


class TestTheImportUnderThePrivateRoot:
    def test_it_writes_the_four_records_the_importer_owns(
        self, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        revision = completed.revisions[0]
        assert f"{WORKSPACE}/{Path('docs/tier3_project_instantiation/source_materials/sources.json').as_posix()}" in imported
        assert completed.manifest_rel(revision).as_posix() in imported
        assert revision.register_rel.as_posix() in imported

    def test_importing_twice_changes_nothing(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        assert ie.check(root, completed) == []
        assert ie.author(root, completed) == []

    def test_the_manifest_is_not_the_copys_ticket_or_claim_sentence(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        manifest = json.loads(
            (root / completed.manifest_rel(completed.revisions[0])).read_text(
                encoding="utf-8"
            )
        )
        assert manifest["ticket"] == completed.import_ticket
        assert "PE-09" in manifest["ticket"]
        assert manifest["claims"]["why"] == completed.claim_ledger_note
        assert "sanitisation" not in manifest["claims"]["why"]
        assert manifest["claims"]["count"] >= 1
        assert manifest["candidate"]["is_submitted_document"] is True

    def test_the_manifest_carries_the_pinned_extraction_environment(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        """V01's block reaches a manifest for the first time here: the copy's
        two are hash-bound and could not gain it."""
        manifest = json.loads(
            (root / completed.manifest_rel(completed.revisions[0])).read_text(
                encoding="utf-8"
            )
        )
        assert completed.manifest_records_runtime_environment is True
        assert manifest["runtime_environment"]["pymupdf"]

    def test_the_manifest_and_the_register_name_the_same_configuration(
        self, root: Path, register: dict[str, Any], completed: ie.DocumentConfig,
        configuration: oc.OriginalConfiguration,
    ) -> None:
        manifest = json.loads(
            (root / completed.manifest_rel(completed.revisions[0])).read_text(
                encoding="utf-8"
            )
        )
        recorded = register["provenance"]["configuration_input"]
        assert recorded["sha256"] == configuration.sha256
        assert recorded["sha256"] in manifest["page_map"]["declared_from"]

    def test_the_page_sources_are_this_revisions_own(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        index = json.loads(
            (root / WORKSPACE / "docs/tier3_project_instantiation/source_materials/sources.json")
            .read_text(encoding="utf-8")
        )
        ids = [source["source_id"] for source in index["sources"]]
        assert ids == [completed.source_id(completed.revisions[0], n) for n in range(1, 5)]
        assert all(sid.startswith("SRC-DN-ORIG") for sid in ids)

    def test_the_derived_half_is_the_shared_renderer(
        self, register: dict[str, Any], root: Path
    ) -> None:
        committed = json.loads(
            (REPO / ie.REVISION_ORIGINAL.register_rel).read_text(encoding="utf-8")
        )
        assert set(register["derived"]) == set(committed["derived"])
        assert register["derived"]["declared_status"] == "Confirmed"


# --------------------------------------------------------------------------- #
# V18 criterion 5 — nothing private reaches this repository
# --------------------------------------------------------------------------- #


class TestNothingPrivateReachesThisRepository:
    def test_no_register_or_graph_root_of_the_original_is_committed(self) -> None:
        for pattern in (
            "**/fidelity_register_as_submitted.json",
            "**/part_b_as_submitted.pdf",
            "workspaces/msca_dn_original/**",
        ):
            assert list(REPO.glob(pattern)) == [], pattern

    def test_the_original_still_declares_no_graph_root_here(self) -> None:
        assert ie.OFFICIAL_ORIGINAL.workspace_rel is None
        assert ie.OFFICIAL_ORIGINAL.declarations_dir_rel is None
        assert ie.OFFICIAL_ORIGINAL.configuration_input_rel is None
        assert ie.OFFICIAL_ORIGINAL.revisions == ()

    def test_the_template_carries_no_hash_and_no_private_path(self) -> None:
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "sha256" in text
        assert not any(len(word.strip('",')) == 64 and word.strip('",').islower()
                       and word.strip('",').isalnum() for word in text.split())

    def test_the_tools_write_only_under_the_root_they_are_given(
        self, root: Path, imported: list[str], authored: list[str]
    ) -> None:
        for rel in list(imported) + list(authored):
            assert (root / rel).is_file()
            assert not (REPO / rel).exists(), rel


# --------------------------------------------------------------------------- #
# The copy's route is unchanged
# --------------------------------------------------------------------------- #


class TestTheCopysRouteIsUnchanged:
    def test_the_first_committed_register_still_renders_byte_equal(self) -> None:
        """V17 criterion 5 for one revision, cheaply. The whole check over both
        revisions and every artifact is tests/test_msca_dn_import.py."""
        from runner.atomic_write import canonical_json_bytes

        rendered = canonical_json_bytes(ws.render_register(REPO, ie.REVISION_ORIGINAL))
        assert rendered == (REPO / ie.REVISION_ORIGINAL.register_rel).read_bytes()

    def test_the_copys_workspace_still_reproduces(self) -> None:
        assert ws.check(REPO) == []

    def test_the_required_field_list_grew_by_the_claim_ledger_note(self) -> None:
        """The copy declares the sentence it was already rendering, so its
        manifests keep their bytes; the original declares its own."""
        assert "claim_ledger_note" in ie.REQUIRED_DOCUMENT_FIELDS
        assert ie.SANITISED_DERIVATIVE.claim_ledger_note.startswith(
            "These are the proposal's own assertions. The sanitisation removed every citation"
        )
        assert "sanitisation" not in ie.OFFICIAL_ORIGINAL.claim_ledger_note


# --------------------------------------------------------------------------- #
# The modules' own contract
# --------------------------------------------------------------------------- #


class TestTheModulesOwnContract:
    def test_the_inventory_record_type_is_the_dry_imports(self) -> None:
        assert oc.INVENTORY_RECORD_TYPE == di.INVENTORY_RECORD_TYPE

    def test_the_file_names_are_the_dry_imports(self) -> None:
        assert ows.INVENTORY_FILE == dio.INVENTORY_FILE
        assert ows.ACCEPTANCE_FILE == dio.ACCEPTANCE_FILE
        assert ows.LIMITATIONS_FILE == dio.LIMITATIONS_FILE
        assert ows.PROVENANCE_FILE == dio.PROVENANCE_FILE
        assert ows.PROVENANCE_RECORD_TYPE == dio.PROVENANCE_RECORD_TYPE
        assert ows.ACCEPTANCE_RECORD_TYPE == di.ACCEPTANCE_RECORD_TYPE
        assert ows.LIMITATIONS_RECORD_TYPE == di.LIMITATIONS_RECORD_TYPE

    def test_the_runner_module_imports_no_tool(self) -> None:
        """The reader is the runner layer: it returns plain data and the
        importer maps it, so a document configuration never reaches here."""
        source = (REPO / "runner/original_configuration.py").read_text(encoding="utf-8")
        assert "from tools" not in source
        assert "import tools" not in source

    def test_neither_new_module_imports_harness(self) -> None:
        for rel in ("runner/original_configuration.py", "tools/author_original_workspace.py"):
            source = (REPO / rel).read_text(encoding="utf-8")
            assert "harness" not in source.replace("harness/candidate_provenance.py", ""), rel

    def test_the_procedure_and_the_runbook_are_where_the_modules_say(self) -> None:
        assert (REPO / ows.PROCEDURE_REL).is_file()
        assert (REPO / ows.RUNBOOK_REL).is_file()
        assert (REPO / ows.SPEC_REL).is_file()
