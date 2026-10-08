"""V01 — the pinned extraction environment.

Acceptance, from ``plans/msca_dn_historical_validation_tickets.md`` V01:

* Both ``--check`` commands pass in the pinned environment.
* The committed document versions are reproduced from the PDFs, not regenerated.
* The cause of the paragraph and character divergence is recorded in the
  decision log with the four measured register differences.
* The exact Python, PyMuPDF and MuPDF versions are pinned in the repository.
* A second run in the pinned environment reproduces the same identifiers.

The first two and the last are asserted by ``tests/test_msca_dn_import.py``
``TestReplay``, which passes only under a build that reproduces. What this
module adds is the diagnosis: a build that cannot reproduce the committed
artifacts fails here with a named reason, rather than failing there as an
opaque refusal.

The suite gate is :func:`cannot_reproduce_reason`, not the pin. PyMuPDF 1.28.0
reproduces every committed artifact and is off pin, so failing the suite on the
pin would report a problem that has not been shown to exist.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from runner import extraction_environment as env
from runner.paths import find_repo_root

REPO = find_repo_root()


@pytest.fixture(scope="module")
def decision() -> dict:
    return json.loads((REPO / env.DECISION_REL).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Measuring
# --------------------------------------------------------------------------- #


class TestMeasure:
    def test_it_reports_the_running_versions(self) -> None:
        import pymupdf

        measured = env.measure()
        assert measured.pymupdf == pymupdf.__version__
        assert measured.mupdf == pymupdf.mupdf_version
        assert measured.python == ".".join(str(n) for n in sys.version_info[:3])

    def test_the_python_minor_is_the_first_two_components(self) -> None:
        assert env.measure().python_minor == ".".join(str(n) for n in sys.version_info[:2])

    def test_the_build_is_the_library_pair(self) -> None:
        measured = env.measure()
        assert measured.build == (measured.pymupdf, measured.mupdf)


# --------------------------------------------------------------------------- #
# Reproducing: the gate
# --------------------------------------------------------------------------- #


class TestReproduction:
    def test_the_running_build_reproduces_the_committed_artifacts(self) -> None:
        """The gate. A build that fails this cannot reproduce the committed
        import artifacts, and every import test downstream of it fails for the
        reason this message names."""
        assert env.cannot_reproduce_reason() is None, env.describe_environment()

    def test_the_audit_build_is_named_as_unable_to_reproduce(self) -> None:
        audit = env.Environment(pymupdf="1.26.6", mupdf="1.26.11", python="3.12.14")
        reason = env.cannot_reproduce_reason(audit)
        assert reason is not None
        assert "1.26.6" in reason and env.PINNED_PYMUPDF in reason

    def test_every_measured_build_reproduces(self) -> None:
        for pymupdf, mupdf in env.REPRODUCING_BUILDS:
            build = env.Environment(pymupdf=pymupdf, mupdf=mupdf, python="3.10.6")
            assert env.cannot_reproduce_reason(build) is None, build

    def test_the_pin_is_one_of_the_measured_builds(self) -> None:
        assert (env.PINNED_PYMUPDF, env.PINNED_MUPDF) in env.REPRODUCING_BUILDS

    def test_an_unmeasured_interpreter_does_not_fail_the_gate(self) -> None:
        """The interpreter was measured not to matter, so it is reported by the
        pin and never treated as an inability to reproduce."""
        other = env.Environment(pymupdf=env.PINNED_PYMUPDF, mupdf=env.PINNED_MUPDF, python="3.12.14")
        assert env.cannot_reproduce_reason(other) is None
        assert env.off_pin_reason(other) is not None


# --------------------------------------------------------------------------- #
# The pin: informational
# --------------------------------------------------------------------------- #


class TestPin:
    def test_the_running_environment_is_on_the_pin(self) -> None:
        assert env.off_pin_reason() is None, env.describe_environment()

    def test_an_off_pin_extraction_library_is_named_as_the_reason(self) -> None:
        audit = env.Environment(pymupdf="1.26.6", mupdf="1.26.11", python="3.12.14")
        reason = env.off_pin_reason(audit)
        assert reason is not None
        assert "1.26.6" in reason and env.PINNED_PYMUPDF in reason

    def test_a_reproducing_build_can_still_be_off_pin(self) -> None:
        """PyMuPDF 1.28.0 carries MuPDF 1.29.0. It reproduces the artifacts and
        is not the declared environment, and the two answers differ."""
        other = env.Environment(pymupdf="1.28.0", mupdf="1.29.0", python="3.10.6")
        assert env.cannot_reproduce_reason(other) is None
        reason = env.off_pin_reason(other)
        assert reason is not None
        assert "1.28.0" in reason and env.PINNED_PYMUPDF in reason

    def test_an_unmeasured_interpreter_is_named_as_the_reason(self) -> None:
        other = env.Environment(pymupdf=env.PINNED_PYMUPDF, mupdf=env.PINNED_MUPDF, python="3.12.14")
        reason = env.off_pin_reason(other)
        assert reason is not None
        assert "3.12" in reason

    def test_every_measured_interpreter_is_on_the_pin_at_the_pinned_library(self) -> None:
        for minor in env.MEASURED_PYTHON:
            on_pin = env.Environment(
                pymupdf=env.PINNED_PYMUPDF, mupdf=env.PINNED_MUPDF, python=f"{minor}.0"
            )
            assert env.off_pin_reason(on_pin) is None, minor


class TestNotices:
    def test_describe_names_the_pin_the_measurement_and_the_diagnosis(self) -> None:
        text = env.describe_environment()
        assert env.PINNED_PYMUPDF in text
        assert env.measure().pymupdf in text
        assert env.DECISION_REL in text

    def test_the_staleness_notice_rules_the_library_out_when_it_reproduces(self) -> None:
        on_pin = env.Environment(pymupdf=env.PINNED_PYMUPDF, mupdf=env.PINNED_MUPDF, python="3.10.6")
        assert "not a library difference" in env.staleness_notice(on_pin)

    def test_the_staleness_notice_names_the_diagnosis_when_it_cannot_reproduce(self) -> None:
        audit = env.Environment(pymupdf="1.26.6", mupdf="1.26.11", python="3.10.6")
        notice = env.staleness_notice(audit)
        assert "1.26.6" in notice and env.DECISION_REL in notice


class TestRequirements:
    def test_requirements_pins_pymupdf_exactly_to_the_module_constant(self) -> None:
        lines = (REPO / "requirements.txt").read_text(encoding="utf-8").splitlines()
        pins = [ln.split("#")[0].strip() for ln in lines if ln.strip().lower().startswith("pymupdf")]
        assert pins == [f"pymupdf=={env.PINNED_PYMUPDF}"], pins

    def test_no_pymupdf_lower_bound_survives(self) -> None:
        """``pymupdf>=1.24.0`` admitted versions with no ``pymupdf`` module at
        all, and four versions that extract the candidate differently."""
        text = (REPO / "requirements.txt").read_text(encoding="utf-8")
        assert "pymupdf>=" not in text.lower()


# --------------------------------------------------------------------------- #
# The diagnosis
# --------------------------------------------------------------------------- #


class TestDecisionRecord:
    def test_it_records_the_pin_the_code_holds(self, decision: dict) -> None:
        pin = decision["pin"]
        assert pin["pymupdf"] == env.PINNED_PYMUPDF
        assert pin["mupdf"] == env.PINNED_MUPDF
        assert pin["python_minor_versions_measured"] == list(env.MEASURED_PYTHON)

    def test_it_records_every_build_the_code_treats_as_reproducing(self, decision: dict) -> None:
        recorded = {(r["pymupdf"], r["mupdf"]) for r in decision["pin"]["builds_measured_to_reproduce"]}
        assert recorded == set(env.REPRODUCING_BUILDS)

    def test_it_states_the_four_register_differences_the_audit_measured(self, decision: dict) -> None:
        rows = {r["measure"]: r for r in decision["divergence"]["register_differences"]}
        assert rows["sub_section_1.1_paragraphs"]["committed"] == 302
        assert rows["sub_section_1.1_paragraphs"]["off_pin"] == 307
        assert rows["sub_section_1.1_characters"]["committed"] == 19601
        assert rows["sub_section_1.1_characters"]["off_pin"] == 19606
        assert rows["sub_section_1.3_paragraphs"]["committed"] == 66
        assert rows["sub_section_1.3_paragraphs"]["off_pin"] == 69
        assert rows["sub_section_1.3_characters"]["committed"] == 10010
        assert rows["sub_section_1.3_characters"]["off_pin"] == 10013

    def test_the_cause_is_declared_confirmed_not_presumed(self, decision: dict) -> None:
        cause = decision["divergence"]["cause"]
        assert cause["declared_status"] == "Confirmed"
        assert cause["off_pin_document_version"] == "MSCA-DN-2025_sanitised_part_b@842a80dea6920270"

    def test_the_measured_matrix_covers_every_version_probed(self, decision: dict) -> None:
        matrix = decision["divergence"]["measured_matrix"]
        probed = {row["pymupdf"] for row in matrix}
        assert {"1.24.0", "1.26.6", "1.26.7", "1.27.1", "1.27.2.3", "1.28.0", "1.28.2"} <= probed
        reproduces = {row["pymupdf"] for row in matrix if row["reproduces_committed_artifacts"]}
        assert reproduces == {p for p, _ in env.REPRODUCING_BUILDS}

    def test_the_committed_versions_it_names_are_the_ones_on_disk(self, decision: dict) -> None:
        from runner.dev_graph.documents import DOCUMENTS_REL

        from tools.import_external_proposal import WORKSPACE_REL

        held = {
            p.stem[:16]
            for p in (REPO / WORKSPACE_REL / DOCUMENTS_REL / "MSCA-DN-2025_sanitised_part_b").glob("*.json")
        }
        named = {v.split("@")[1] for v in decision["reproduced_document_versions"]}
        assert named == held

    def test_the_arithmetic_of_the_character_difference_is_stated(self, decision: dict) -> None:
        """The characters rise while the text shrinks: each split block drops
        the space that joined its two halves and adds a paragraph separator."""
        rule = decision["divergence"]["cause"]["character_arithmetic"]
        assert "separator" in rule and "space" in rule

    def test_every_unresolved_matter_declares_itself_unresolved(self, decision: dict) -> None:
        """CLAUDE.md §12.2: a status is a field, not a turn of phrase inside a
        sentence."""
        for key, block in decision["open"].items():
            assert block["declared_status"] == "Unresolved", key
            assert block["owner"], key


# --------------------------------------------------------------------------- #
# The command-line affordance
# --------------------------------------------------------------------------- #


class TestCommands:
    @pytest.mark.parametrize("module", ["tools.import_external_proposal", "tools.author_msca_dn_workspace"])
    def test_environment_flag_prints_the_pin_and_exits_zero(self, module: str) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", module, "--environment"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert env.PINNED_PYMUPDF in proc.stdout
        assert env.DECISION_REL in proc.stdout

    def test_a_second_process_reproduces_the_committed_import(self) -> None:
        """The second-run criterion, across process boundaries rather than
        twice inside one interpreter."""
        proc = subprocess.run(
            [sys.executable, "-m", "tools.import_external_proposal", "--check"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert proc.stdout.strip().splitlines()[-1] == "up to date"
