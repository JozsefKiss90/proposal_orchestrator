"""AN10 — the anonymised derivative's identity, configuration and register.

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN10:

1. Configuration completion refuses to redeclare the sanitised copy, as it does
   today, and accepts the derivative's own identity.
2. Neither existing register renderer renders the derivative, and the new
   renderer renders nothing else.
3. The integrity audit on a fixture derivative words its scope as a derivative
   of the original.

The verification runs the pipeline's own stages on the AN3 synthetic fixture,
in a temporary directory outside the repository: A0 intake, A2 redaction, A4
table synthesis and A6 structural fidelity. It then takes the derivative down
the route the original takes: the V08 dry import, a V17 configuration input,
the V17 private graph root and the import, which renders the register. The
audit's own provenance reader reads that register back.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

pymupdf = pytest.importorskip("pymupdf")

from harness import candidate_provenance as cp  # noqa: E402
from runner import anonymisation_fidelity as af  # noqa: E402
from runner import anonymisation_intake as ai  # noqa: E402
from runner import anonymisation_policy as ap  # noqa: E402
from runner import anonymisation_redaction as ar  # noqa: E402
from runner import anonymisation_table as at  # noqa: E402
from runner import original_configuration as oc  # noqa: E402
from runner.paths import find_repo_root  # noqa: E402
from tests import _anonymisation_fixture as fx  # noqa: E402
from tools import author_anonymised_register as aar  # noqa: E402
from tools import author_msca_dn_workspace as ws  # noqa: E402
from tools import author_original_workspace as ows  # noqa: E402
from tools import dry_import_original as dio  # noqa: E402
from tools import import_external_proposal as ie  # noqa: E402

REPO = find_repo_root()

CONFIG_FILE = "derivative_configuration.json"
POLICY_REL = "policy/anonymisation_policy.json"
DRY_DIR = "v08_dry_import"
WORKSPACE = "workspaces/msca_dn_derivative"
PRIVATE_DIR = "private/msca_dn_derivative"
REVISION_ID = "anonymised_v1"
#: Plainly synthetic: a test must not look like it names a real commit.
PIPELINE_REVISION = "0123456789abcdef0123456789abcdef01234567"
SUBMISSION_ID = "MSCA-DN-2025-FIXTURE-NOT-THE-REAL-NUMBER"
CALL_ID = "HORIZON-MSCA-2025-DN-01"

#: The words the copy's register header uses about itself. None of them may
#: describe the derivative.
_COPY_WORDS = ("saniti", "generalised", "reflow of a 34-page")

GRAPHICAL_PAGES = [1, 2, 3]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


# --------------------------------------------------------------------------- #
# The pipeline on the fixture, then the V08/V17 route over its derivative
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """A0, A2, A4 and A6 on the synthetic fixture, all under one private root."""
    root = tmp_path_factory.mktemp("an10")
    policy_path = root / POLICY_REL
    policy_path.parent.mkdir(parents=True)
    policy_path.write_bytes(ap.STARTING_POLICY_PATH.read_bytes())
    policy = ap.load(policy_path)

    built = fx.build(root / "fixture")
    intake = ai.intake(pdf=built.pdf, expected_sha256=_sha(built.pdf), out_dir=root / "a0")
    private = root / "private"
    dictionary = fx.write_dictionary(private)
    redacted = ar.redact(
        pdf=built.pdf,
        intake_record=intake.intake_record,
        policy=policy,
        policy_sha256=policy.sha256,
        dictionary=dictionary,
        dictionary_sha256=ap.policy_sha256(fx.DICTIONARY),
        out_dir=root / "a2",
    )
    synthesised = at.synthesise(
        derivative=redacted.derivative,
        redaction_log=redacted.edit_log,
        intake_record=intake.intake_record,
        policy=policy,
        policy_sha256=policy.sha256,
        dictionary=dictionary,
        dictionary_sha256=ap.policy_sha256(fx.DICTIONARY),
        spec=fx.write_table_spec(private),
        spec_sha256=ap.policy_sha256(fx.TABLE_SPEC),
        out_dir=root / "a4",
    )
    review = root / "a6_review" / "figure_review.json"
    review.parent.mkdir(parents=True)
    review.write_text(
        json.dumps(
            {
                "schema": af.REVIEW_SCHEMA,
                "record_type": af.REVIEW_RECORD_TYPE,
                "derivative_sha256": synthesised.derivative_sha256,
                "pages": [
                    {"page": p, "verdict": "preserved", "basis": "operator_visual_comparison",
                     "reviewed_by": "operator", "reviewed_on": "2026-10-16", "note": ""}
                    for p in GRAPHICAL_PAGES
                ],
            }
        ),
        encoding="utf-8",
    )
    fidelity = af.fidelity(
        derivative=synthesised.derivative,
        derivative_sha256=synthesised.derivative_sha256,
        intake_record=intake.intake_record,
        policy=policy,
        policy_sha256=policy.sha256,
        stage_logs=[redacted.edit_log, synthesised.log],
        figure_review=review,
        out_dir=root / "a6",
    )
    assert fidelity.passed
    return {
        "root": root,
        "source": built.pdf,
        "intake": intake,
        "redacted": redacted,
        "synthesised": synthesised,
        "fidelity": fidelity,
        "policy": policy,
    }


@pytest.fixture(scope="module")
def root(world: dict[str, Any]) -> Path:
    """The private root, with the V08 dry import run over the derivative."""
    base: Path = world["root"]
    derivative: Path = world["synthesised"].derivative
    assert dio.main(
        [
            "--document", ie.ANONYMISED_DERIVATIVE.config_id,
            "--pdf", str(derivative),
            "--expect-sha256", world["synthesised"].derivative_sha256,
            "--out", str(base / DRY_DIR),
            "--submission-id", SUBMISSION_ID,
            "--call-id", CALL_ID,
        ]
    ) == 0
    return base


def _inventory(root: Path) -> dict[str, Any]:
    return json.loads((root / DRY_DIR / dio.INVENTORY_FILE).read_text(encoding="utf-8-sig"))


def _body_size(root: Path) -> str:
    distribution = _inventory(root)["point_sizes"]["distribution"]
    return max(distribution.items(), key=lambda kv: (kv[1], kv[0]))[0]


def _sub_section(sid: str, section: str, page: int, marker: str) -> dict[str, Any]:
    return {
        "sub_section_id": sid,
        "section_id": section,
        "declared_pages": [page, page],
        "marker": marker,
        "declared_title": None,
        "exact_marker": False,
    }


def _document(world: dict[str, Any], root: Path) -> dict[str, Any]:
    """The derivative's configuration input, as a plain mapping."""
    derivative: Path = world["synthesised"].derivative
    return {
        "schema": oc.SCHEMA,
        "record_type": oc.RECORD_TYPE,
        "config_id": "anonymised_derivative",
        "declared_by": "the operator, reconciling against the derivative",
        "declared_on": "2026-10-16",
        "declared_status": "Assumed",
        "status_note": "Declared from the dry import of this fixture's derivative.",
        "authenticated_sha256": world["synthesised"].derivative_sha256,
        "measurement": {
            "path": f"{DRY_DIR}/{dio.INVENTORY_FILE}",
            "sha256": _sha(root / DRY_DIR / dio.INVENTORY_FILE),
        },
        "dry_import_dir": DRY_DIR,
        "workspace_rel": WORKSPACE,
        "declarations_dir_rel": f"{PRIVATE_DIR}/declarations",
        "scorecard_rel": None,
        "expected_pages": 3,
        "body_point_size": _body_size(root),
        "marker_page_tolerance": 0,
        "sub_sections": [
            _sub_section("1.1", "excellence_section", 1, "1.1."),
            _sub_section("1.4", "excellence_section", 2, "1.4."),
            _sub_section("3.1", "implementation_section", 3, "3.1."),
        ],
        "criterion_heading_markers": [],
        "work_package_layout": None,
        "dn_type": None,
        "pages_outside_the_map": [],
        "revisions": [
            {
                "revision_id": REVISION_ID,
                "pdf_rel": _rel(root, derivative),
                "source_id_prefix": "SRC-DN-ANON",
                "manifest_name": "MSCA-DN-2025_part_b_anonymised.json",
                "register_rel": f"{PRIVATE_DIR}/fidelity_register_anonymised.json",
                "candidate_role": (
                    "Current assessment artifact: an anonymised derivative of the Part B as "
                    "submitted. Not the submitted text."
                ),
                "candidate_version": "anonymised derivative, 3 pages",
                "summary": "The fixture's anonymised derivative, imported in a private root.",
                "expected_pages": None,
                "supersedes": None,
                "change_id": None,
            }
        ],
        "derivation": {
            "pipeline_revision": PIPELINE_REVISION,
            "intake_record": _rel(root, world["intake"].intake_record),
            "policy": POLICY_REL,
            "fidelity_report": _rel(root, world["fidelity"].report),
            "stage_logs": [
                _rel(root, world["redacted"].edit_log),
                _rel(root, world["synthesised"].log),
            ],
        },
    }


@pytest.fixture
def document(world: dict[str, Any], root: Path) -> dict[str, Any]:
    return _document(world, root)


def _write(root: Path, doc: dict[str, Any], name: str) -> Path:
    path = root / name
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def configuration(world: dict[str, Any], root: Path) -> oc.OriginalConfiguration:
    return oc.load_configuration(_write(root, _document(world, root), CONFIG_FILE), root)


@pytest.fixture(scope="module")
def completed(configuration: oc.OriginalConfiguration) -> ie.DocumentConfig:
    return ie.complete_from_input(ie.ANONYMISED_DERIVATIVE, configuration)


@pytest.fixture(scope="module")
def imported(
    root: Path, configuration: oc.OriginalConfiguration, completed: ie.DocumentConfig
) -> list[str]:
    """The private graph root authored, then the derivative imported into it."""
    ows.author(root, configuration)
    return ie.author(root, completed)


@pytest.fixture(scope="module")
def register(root: Path, imported: list[str], completed: ie.DocumentConfig) -> dict[str, Any]:
    path = root / completed.revisions[0].register_rel
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# The identity: a third document
# --------------------------------------------------------------------------- #


class TestTheDerivativeIsAThirdDocument:
    def test_it_is_declared_beside_the_other_two(self) -> None:
        assert ie.ANONYMISED_DERIVATIVE in ie.DOCUMENTS
        assert ie.document_by_id("anonymised_derivative") is ie.ANONYMISED_DERIVATIVE

    def test_it_is_neither_the_submitted_text_nor_the_copy(self) -> None:
        doc = ie.ANONYMISED_DERIVATIVE
        assert doc.is_submitted_document is False
        assert doc.is_anonymised_derivative is True
        assert ie.SANITISED_DERIVATIVE.is_anonymised_derivative is False
        assert ie.OFFICIAL_ORIGINAL.is_anonymised_derivative is False

    def test_its_identity_is_its_own(self) -> None:
        doc = ie.ANONYMISED_DERIVATIVE
        for other in (ie.SANITISED_DERIVATIVE, ie.OFFICIAL_ORIGINAL):
            for field in (
                "intake_id", "document_id", "title", "role", "short_name", "page_statement",
                "reader_caveat_key", "reader_caveat", "first_revision_key", "claim_ledger_note",
                "status_note", "summary",
            ):
                assert getattr(doc, field), field
                assert getattr(doc, field) != getattr(other, field), (other.config_id, field)

    def test_nothing_is_inherited_from_the_copy(self) -> None:
        doc = ie.ANONYMISED_DERIVATIVE
        copy_config = ie.SANITISED_DERIVATIVE
        assert doc.workspace_rel is None
        assert doc.sub_sections == ()
        assert doc.expected_pages is None
        assert doc.body_point_size is None
        assert doc.work_package_layout is None
        assert doc.revisions == ()
        assert doc.declaration_contract() != copy_config.declaration_contract()
        described = " ".join(
            str(getattr(doc, field))
            for field in (
                "title", "role", "short_name", "page_statement", "reader_caveat",
                "claim_ledger_note", "status_note", "first_revision_key",
            )
        ).lower()
        for word in _COPY_WORDS:
            assert word not in described, word

    def test_it_says_it_is_a_derivative_of_the_original(self) -> None:
        doc = ie.ANONYMISED_DERIVATIVE
        for text in (doc.role, doc.page_statement, doc.reader_caveat):
            assert "derivative" in text.lower()
            assert "original" in text.lower() or "submitted" in text.lower()

    def test_it_can_be_measured_but_not_imported_until_completed(self) -> None:
        doc = ie.ANONYMISED_DERIVATIVE
        assert doc.dry_import_missing_fields() == ()
        assert set(doc.missing_fields()) == {
            "workspace_rel", "sub_sections", "expected_pages", "body_point_size", "revisions",
        }

    def test_a_document_may_not_be_both_submitted_and_a_derivative(self) -> None:
        with pytest.raises(ie.ImportRefused) as exc:
            replace(ie.ANONYMISED_DERIVATIVE, is_submitted_document=True)
        assert "submitted" in str(exc.value)


# --------------------------------------------------------------------------- #
# Criterion 1 — completion refuses the copy and accepts the derivative
# --------------------------------------------------------------------------- #


class TestCompletingTheDerivative:
    def test_the_copy_may_still_not_be_redeclared(
        self, world: dict[str, Any], root: Path, document: dict[str, Any]
    ) -> None:
        document["config_id"] = "sanitised_derivative"
        configuration = oc.load_configuration(_write(root, document, "copy.json"), root)
        with pytest.raises(ie.ImportRefused) as exc:
            ie.complete_from_input(ie.SANITISED_DERIVATIVE, configuration)
        assert "already complete" in str(exc.value)

    def test_the_derivatives_own_input_completes_it(self, completed: ie.DocumentConfig) -> None:
        assert completed.config_id == "anonymised_derivative"
        assert completed.missing_fields() == ()
        completed.require_complete()
        assert completed.is_anonymised_derivative is True
        assert completed.expected_pages == 3
        assert ie.config_for(completed.revisions[0]) is completed

    def test_the_configuration_was_checked_against_the_derivatives_own_measurement(
        self, configuration: oc.OriginalConfiguration, root: Path, world: dict[str, Any]
    ) -> None:
        report = oc.check(configuration, root)
        assert report.green, report.findings
        assert _inventory(root)["sha256"] == world["synthesised"].derivative_sha256

    def test_an_input_naming_the_derivative_cannot_complete_the_original(
        self, configuration: oc.OriginalConfiguration
    ) -> None:
        with pytest.raises(ie.ImportRefused) as exc:
            ie.complete_from_input(ie.OFFICIAL_ORIGINAL, configuration)
        assert "anonymised_derivative" in str(exc.value)

    def test_the_derivative_needs_a_derivation(
        self, root: Path, document: dict[str, Any]
    ) -> None:
        del document["derivation"]
        configuration = oc.load_configuration(_write(root, document, "no_derivation.json"), root)
        with pytest.raises(ie.ImportRefused) as exc:
            ie.complete_from_input(ie.ANONYMISED_DERIVATIVE, configuration)
        assert "derivation" in str(exc.value)

    def test_the_original_may_not_declare_one(
        self, root: Path, document: dict[str, Any]
    ) -> None:
        document["config_id"] = "official_original"
        configuration = oc.load_configuration(_write(root, document, "original.json"), root)
        with pytest.raises(ie.ImportRefused) as exc:
            ie.complete_from_input(ie.OFFICIAL_ORIGINAL, configuration)
        assert "derivation" in str(exc.value)


class TestTheDerivationIsReadFailClosed:
    def test_it_reads_back(self, configuration: oc.OriginalConfiguration) -> None:
        derivation = configuration.derivation
        assert derivation is not None
        assert derivation.pipeline_revision == PIPELINE_REVISION
        assert derivation.policy == POLICY_REL
        assert len(derivation.stage_logs) == 2

    def test_an_absent_block_reads_as_none(self, root: Path, document: dict[str, Any]) -> None:
        del document["derivation"]
        configuration = oc.load_configuration(_write(root, document, "none.json"), root)
        assert configuration.derivation is None

    @pytest.mark.parametrize(
        "field", ["pipeline_revision", "intake_record", "policy", "fidelity_report", "stage_logs"]
    )
    def test_a_missing_field_is_refused_and_named(
        self, root: Path, document: dict[str, Any], field: str
    ) -> None:
        del document["derivation"][field]
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(_write(root, document, f"missing_{field}.json"), root)
        assert field in str(exc.value)

    def test_a_revision_that_is_not_a_commit_is_refused(
        self, root: Path, document: dict[str, Any]
    ) -> None:
        document["derivation"]["pipeline_revision"] = "main"
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(_write(root, document, "branch.json"), root)
        assert "pipeline_revision" in str(exc.value)

    def test_no_stage_log_is_refused(self, root: Path, document: dict[str, Any]) -> None:
        document["derivation"]["stage_logs"] = []
        with pytest.raises(oc.ConfigurationRefused) as exc:
            oc.load_configuration(_write(root, document, "no_logs.json"), root)
        assert "stage_logs" in str(exc.value)

    def test_its_paths_are_checked_against_the_private_root(
        self, root: Path, document: dict[str, Any]
    ) -> None:
        document["derivation"]["policy"] = "../outside/policy.json"
        configuration = oc.load_configuration(_write(root, document, "escape.json"), root)
        report = oc.check(configuration, root)
        assert any(
            name == "path_outside_the_private_root" and "derivation.policy" in detail
            for name, detail in report.findings
        )


# --------------------------------------------------------------------------- #
# Criterion 2 — three renderers, each for its own document
# --------------------------------------------------------------------------- #


class TestEachRendererRendersOnlyItsOwnDocument:
    def test_the_copys_renderer_refuses_the_derivative(
        self, root: Path, completed: ie.DocumentConfig
    ) -> None:
        with pytest.raises(ws.AuthoringError) as exc:
            ws.render_register(root, completed.revisions[0])
        assert "anonymised derivative" in str(exc.value)

    def test_the_submitted_renderer_refuses_the_derivative(
        self, root: Path, completed: ie.DocumentConfig
    ) -> None:
        with pytest.raises(ows.AuthoringRefused) as exc:
            ows.render_submitted_register(root, completed.revisions[0])
        assert "not the submitted text" in str(exc.value)

    def test_the_new_renderer_refuses_the_copy(self) -> None:
        for revision in (ie.REVISION_ORIGINAL, ie.REVISION_RESOLVED_FIXES):
            with pytest.raises(aar.AuthoringRefused) as exc:
                aar.render_anonymised_register(REPO, revision)
            assert "not an anonymised derivative" in str(exc.value)

    def test_the_new_renderer_refuses_the_submitted_text(
        self, completed: ie.DocumentConfig, tmp_path: Path
    ) -> None:
        original = replace(
            ie.OFFICIAL_ORIGINAL,
            revisions=(replace(completed.revisions[0], revision_id="as_submitted_an10"),),
        )
        ie.register_document(original)
        with pytest.raises(aar.AuthoringRefused) as exc:
            aar.render_anonymised_register(tmp_path, original.revisions[0])
        assert "not an anonymised derivative" in str(exc.value)

    def test_the_importer_chooses_the_new_renderer_by_the_documents_flag(
        self, root: Path, register: dict[str, Any], completed: ie.DocumentConfig
    ) -> None:
        assert ie.register_of(root, completed.revisions[0]) == register
        assert register["record_type"] == "fidelity_register"
        assert register["record_type"] == ws.REGISTER_RECORD_TYPE == aar.REGISTER_RECORD_TYPE

    def test_the_copys_register_still_renders_byte_equal(self) -> None:
        from runner.atomic_write import canonical_json_bytes

        rendered = canonical_json_bytes(ie.register_of(REPO, ie.REVISION_ORIGINAL))
        assert rendered == (REPO / ie.REVISION_ORIGINAL.register_rel).read_bytes()


# --------------------------------------------------------------------------- #
# The register states the derivative's own facts
# --------------------------------------------------------------------------- #


class TestTheRegisterStatesTheDerivativesFacts:
    def test_the_assessed_file_is_the_derivative(
        self, register: dict[str, Any], world: dict[str, Any]
    ) -> None:
        artifact = register["provenance"]["current_assessment_artifact"]
        assert artifact["sha256"] == world["synthesised"].derivative_sha256
        assert artifact["is_submitted_document"] is False
        assert artifact["pages"] == 3

    def test_it_was_derived_from_the_authenticated_original(
        self, register: dict[str, Any], world: dict[str, Any]
    ) -> None:
        derived_from = register["provenance"]["current_assessment_artifact"]["derived_from"]
        assert derived_from["route"] == cp.DERIVATION_ROUTE_ANONYMISATION
        assert derived_from["original_sha256"] == _sha(world["source"])
        assert derived_from["declared_status"] == "Confirmed"

    def test_it_names_the_pipeline_revision_and_the_policy(
        self, register: dict[str, Any], world: dict[str, Any]
    ) -> None:
        derivation = register["provenance"]["derivation"]
        assert derivation["pipeline_revision"]["value"] == PIPELINE_REVISION
        assert derivation["pipeline_revision"]["declared_status"] == "Assumed"
        assert derivation["policy"]["version"] == world["policy"].version
        assert derivation["policy"]["sha256"] == world["policy"].sha256
        assert derivation["policy"]["declared_status"] == "Confirmed"

    def test_it_binds_the_stage_logs_and_the_fidelity_report(
        self, register: dict[str, Any], world: dict[str, Any]
    ) -> None:
        derivation = register["provenance"]["derivation"]
        assert [s["stage"] for s in derivation["stage_logs"]] == ["A2", "A4"]
        assert derivation["stage_logs"][-1]["output_sha256"] == (
            world["synthesised"].derivative_sha256
        )
        fidelity = derivation["structural_fidelity"]
        assert fidelity["sha256"] == _sha(world["fidelity"].report)
        assert fidelity["verdict"] == "pass"
        assert set(fidelity["counts"]) == set(af.CATEGORIES)

    def test_the_layout_is_preserved(self, register: dict[str, Any]) -> None:
        reflow = register["provenance"]["transformation"]["reflow"]
        assert reflow["applied"] is False
        assert reflow["layout"] == "preserved"
        assert reflow["current_pages"] == 3

    def test_the_figures_are_counted_by_verdict(self, register: dict[str, Any]) -> None:
        figures = register["provenance"]["transformation"]["figures"]
        assert figures["by_verdict"] == {"preserved": 3, "masked": 0, "redrawn": 0}
        assert figures["pages_looked_at"] == 3

    def test_the_citation_markers_keep_their_count(self, register: dict[str, Any]) -> None:
        """The fixture's self-citation entries became neutral markers, and its
        numbered markers all survived: none lost, two neutral markers added."""
        markers = register["provenance"]["transformation"]["citation_markers"]
        assert markers["count_kept"] is True
        assert markers["markers_lost"] == 0
        assert markers["reference_kept"] == markers["derivative_kept"] == 5
        assert markers["neutral_markers"] == 2
        assert markers["identifiers_removed"] == {"doi": 2, "url": 2}
        assert markers["differences_explained"] == markers["differences"]

    def test_table_1_4_1_is_synthetic(self, register: dict[str, Any]) -> None:
        table = register["provenance"]["transformation"]["table_1_4_1"]
        assert table["synthetic"] is True
        assert table["page"] == fx.SUPERVISOR_TABLE_PAGE
        assert table["data_rows"] > 0
        assert table["declared_status"] == "Confirmed"

    def test_its_declared_words_are_in_the_audits_vocabulary(
        self, register: dict[str, Any]
    ) -> None:
        transformation = register["provenance"]["transformation"]
        assert cp.declared_word(transformation["identifiers"]) in (
            cp.IDENTIFIERS_GENERALISED_WORDS
        )
        assert cp.declared_word(transformation["citations"]) in cp.CITATIONS_PRESENT_WORDS

    def test_it_borrows_no_wording_from_the_copy(self, register: dict[str, Any]) -> None:
        header = json.dumps(
            {k: v for k, v in register["provenance"].items() if k != "inputs"}
        ).lower()
        for word in _COPY_WORDS:
            assert word not in header, word

    def test_it_stays_private(self, register: dict[str, Any]) -> None:
        storage = register["provenance"]["storage"]
        assert storage["stored_in_the_public_repository"] is False


class TestTheRegisterRefusesWhatItCannotStand:
    def _render(self, root: Path, completed: ie.DocumentConfig) -> dict[str, Any]:
        return aar.render_anonymised_register(root, completed.revisions[0])

    def test_a_failing_fidelity_report_is_refused(
        self, root: Path, world: dict[str, Any], completed: ie.DocumentConfig, imported: list[str]
    ) -> None:
        report = world["fidelity"].report
        original = report.read_bytes()
        record = json.loads(original)
        record["verdict"] = "fail"
        try:
            report.write_text(json.dumps(record), encoding="utf-8")
            with pytest.raises(aar.AuthoringRefused) as exc:
                self._render(root, completed)
            assert "verdict" in str(exc.value)
        finally:
            report.write_bytes(original)

    def test_a_policy_other_than_the_reports_is_refused(
        self, root: Path, completed: ie.DocumentConfig, imported: list[str]
    ) -> None:
        path = root / POLICY_REL
        original = path.read_bytes()
        record = json.loads(original)
        record["policy_version"] = record["policy_version"] + 1
        try:
            path.write_text(json.dumps(record), encoding="utf-8")
            with pytest.raises(aar.AuthoringRefused) as exc:
                self._render(root, completed)
            assert "policy" in str(exc.value)
        finally:
            path.write_bytes(original)

    def test_a_stage_log_other_than_the_reports_is_refused(
        self, root: Path, world: dict[str, Any], completed: ie.DocumentConfig, imported: list[str]
    ) -> None:
        log = world["redacted"].edit_log
        original = log.read_bytes()
        try:
            log.write_bytes(original + b"\n")
            with pytest.raises(aar.AuthoringRefused) as exc:
                self._render(root, completed)
            assert "stage log" in str(exc.value)
        finally:
            log.write_bytes(original)

    def test_a_chain_without_a_table_synthesis_is_refused(
        self, root: Path, world: dict[str, Any], completed: ie.DocumentConfig, imported: list[str]
    ) -> None:
        """The derivative replaces Table 1.4.1; a file that does not is not it."""
        log = world["synthesised"].log
        original = log.read_bytes()
        record = json.loads(original)
        record["schema"] = "not_a_table_synthesis/1"
        report = world["fidelity"].report
        report_bytes = report.read_bytes()
        bound = json.loads(report_bytes)
        try:
            log.write_text(json.dumps(record), encoding="utf-8")
            bound["input"]["stage_logs"][-1]["log_sha256"] = _sha(log)
            report.write_text(json.dumps(bound), encoding="utf-8")
            with pytest.raises(aar.AuthoringRefused) as exc:
                self._render(root, completed)
            assert "A4" in str(exc.value)
        finally:
            log.write_bytes(original)
            report.write_bytes(report_bytes)

    def test_a_kept_marker_the_original_does_not_carry_is_refused(
        self, root: Path, world: dict[str, Any], completed: ie.DocumentConfig, imported: list[str]
    ) -> None:
        inventory = world["fidelity"].derivative_inventory
        original = inventory.read_bytes()
        record = json.loads(original)
        record["citation_markers"]["counts"]["bracketed_numbers"] += 1
        report = world["fidelity"].report
        report_bytes = report.read_bytes()
        bound = json.loads(report_bytes)
        try:
            inventory.write_text(json.dumps(record), encoding="utf-8")
            bound["input"]["derivative_inventory_sha256"] = _sha(inventory)
            report.write_text(json.dumps(bound), encoding="utf-8")
            with pytest.raises(aar.AuthoringRefused) as exc:
                self._render(root, completed)
            assert "No policy rule adds a marker" in str(exc.value)
        finally:
            inventory.write_bytes(original)
            report.write_bytes(report_bytes)

    def test_a_report_over_another_derivative_is_refused(
        self, root: Path, world: dict[str, Any], completed: ie.DocumentConfig, imported: list[str]
    ) -> None:
        report = world["fidelity"].report
        original = report.read_bytes()
        record = json.loads(original)
        record["input"]["derivative_sha256"] = "0" * 64
        try:
            report.write_text(json.dumps(record), encoding="utf-8")
            with pytest.raises(aar.AuthoringRefused) as exc:
                self._render(root, completed)
            assert "another derivative" in str(exc.value)
        finally:
            report.write_bytes(original)


# --------------------------------------------------------------------------- #
# Criterion 3 — the audit words its scope as a derivative of the original
# --------------------------------------------------------------------------- #


class TestTheAuditWordsItsScopeAsADerivative:
    def _resolved(self, root: Path, completed: ie.DocumentConfig) -> cp.CandidateProvenance:
        return cp.resolve_provenance(
            repo_root=root,
            graph_root=root / WORKSPACE,
            document_id=completed.document_id or "",
        )

    def test_the_scope_is_a_derivative_of_the_original(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        resolved = self._resolved(root, completed)
        assert resolved.is_submitted_document is False
        assert resolved.identity_scope == cp.IDENTITY_ANONYMISED_DERIVATIVE
        assert not resolved.identities_are_comparable
        assert "derivative of the original" in resolved.identity_statement
        assert "sanitisation" not in resolved.identity_statement
        assert resolved.flags == ()

    def test_the_audit_words_its_findings_with_the_fixtures_own_provenance(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig, tmp_path: Path
    ) -> None:
        """Criterion 3, joined: the provenance resolved from the fixture
        derivative's own register drives the audit's DC check. The candidate
        the audit parses is the audit tests' DC world, because the fixture
        carries no DC table to compare."""
        from harness import integrity_audit as ia
        from harness.rubrics import load_profile_bundle
        from tests.harness.test_blind_leakage import _graph_profile
        from tests.harness.test_integrity_audit import _audit, _findings, _named_hosts_world

        resolved = self._resolved(root, completed)
        profile = load_profile_bundle(_graph_profile(tmp_path), repo_root=tmp_path)
        report = _audit(tmp_path, profile, _named_hosts_world(), provenance=resolved)
        details = [
            f.detail for f in _findings(report, "dc_table_vs_projects")
            if f.kind == ia.KIND_NOT_COMPARABLE
        ]
        assert len(details) == 2
        assert all(d.endswith(cp.STATEMENT_ANONYMISED_DERIVATIVE) for d in details)
        assert all("derivative of the original" in d for d in details)

    def test_the_grounding_cause_follows_the_measured_markers(
        self, root: Path, imported: list[str], completed: ie.DocumentConfig
    ) -> None:
        """The derivative keeps its five numbered markers, so the measurement
        names sources present. Nothing names sanitisation."""
        resolved = self._resolved(root, completed)
        assert resolved.grounding_cause == cp.CAUSE_SOURCES_PRESENT
        assert "sanitisation" not in resolved.grounding_reason


class TestTheProvenanceRule:
    """The scope is read from the register's declarations, and a register that
    contradicts itself is flagged rather than read as either side."""

    def _register(self, **artifact: Any) -> dict[str, Any]:
        return {
            "record_type": "fidelity_register",
            "provenance": {
                "current_assessment_artifact": {
                    "is_submitted_document": False,
                    "derived_from": {"route": cp.DERIVATION_ROUTE_ANONYMISATION},
                    **artifact,
                },
                "transformation": {
                    "identifiers": "pseudonymised: replaced by codes",
                    "citations": "kept: counts and positions",
                },
            },
            "derived": {"citation_marker_counts": {"bracketed_numbers": 2}},
        }

    def _resolve(self, tmp_path: Path, register: dict[str, Any]) -> cp.CandidateProvenance:
        (tmp_path / "register.json").write_text(json.dumps(register), encoding="utf-8")
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "document": {"node_id": "n", "document_id": "d"},
                    "candidate": {"fidelity_register": "register.json"},
                    "claims": {"declared_status": "Unresolved"},
                }
            ),
            encoding="utf-8",
        )
        return cp.provenance_from_manifest(manifest, repo_root=tmp_path)

    def test_a_pseudonymised_derivative_is_scoped_as_one(self, tmp_path: Path) -> None:
        resolved = self._resolve(tmp_path, self._register())
        assert resolved.identity_scope == cp.IDENTITY_ANONYMISED_DERIVATIVE
        assert resolved.grounding_cause == cp.CAUSE_SOURCES_PRESENT

    def test_without_the_route_pseudonymised_reads_as_generalised(self, tmp_path: Path) -> None:
        register = self._register()
        del register["provenance"]["current_assessment_artifact"]["derived_from"]
        resolved = self._resolve(tmp_path, register)
        assert resolved.identity_scope == cp.IDENTITY_GENERALISED

    def test_an_unknown_route_is_flagged(self, tmp_path: Path) -> None:
        register = self._register(derived_from={"route": "something_else"})
        resolved = self._resolve(tmp_path, register)
        assert resolved.identity_scope == cp.IDENTITY_UNSTATED
        assert any("route" in flag for flag in resolved.flags)

    def test_a_malformed_derived_from_is_flagged_as_malformed(self, tmp_path: Path) -> None:
        resolved = self._resolve(tmp_path, self._register(derived_from="the original"))
        assert resolved.identity_scope == cp.IDENTITY_UNSTATED
        assert any("not a JSON object" in flag for flag in resolved.flags)

    def test_a_derivative_declaring_itself_submitted_is_flagged(self, tmp_path: Path) -> None:
        resolved = self._resolve(tmp_path, self._register(is_submitted_document=True))
        assert resolved.identity_scope == cp.IDENTITY_UNSTATED
        assert any("submitted" in flag for flag in resolved.flags)

    def test_a_derivative_declaring_its_identifiers_unchanged_is_flagged(
        self, tmp_path: Path
    ) -> None:
        register = self._register()
        register["provenance"]["transformation"]["identifiers"] = "unchanged: as submitted"
        resolved = self._resolve(tmp_path, register)
        assert resolved.identity_scope == cp.IDENTITY_UNSTATED
        assert any("identifiers" in flag for flag in resolved.flags)

    def test_the_route_constant_is_the_registers(self) -> None:
        assert aar.DERIVATION_ROUTE == cp.DERIVATION_ROUTE_ANONYMISATION


# --------------------------------------------------------------------------- #
# Nothing private reaches this repository
# --------------------------------------------------------------------------- #


class TestNothingPrivateReachesThisRepository:
    def test_the_renderer_refuses_a_root_inside_this_repository(
        self, completed: ie.DocumentConfig
    ) -> None:
        with pytest.raises((aar.AuthoringRefused, oc.ConfigurationRefused)):
            aar.render_anonymised_register(REPO, completed.revisions[0])

    def test_the_committed_template_declares_no_derivation(self) -> None:
        """The template is the original's, and completing the original from an
        input that declares a derivation is refused."""
        template = json.loads(
            (REPO / "tools/original_configuration_template.json").read_text(encoding="utf-8")
        )
        assert "derivation" not in template

    def test_the_graph_root_readme_names_the_derivative(
        self, root: Path, imported: list[str]
    ) -> None:
        readme = (root / WORKSPACE / "README.md").read_text(encoding="utf-8")
        assert "anonymised derivative" in readme
        assert "The assessment artifact under the register is the submitted text" not in readme


def test_the_fixture_is_unchanged_by_the_route(world: dict[str, Any]) -> None:
    """Every stage output stays as its stage wrote it: the route reads them."""
    assert _sha(world["synthesised"].derivative) == world["synthesised"].derivative_sha256
    assert copy.deepcopy(world["policy"].record) == world["policy"].record
