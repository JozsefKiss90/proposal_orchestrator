"""The committed historical pre-evaluation profile (V10, 2026-10-13).

The profile scores the submitted 2025 original under the rules of its own call.
Its whole claim is that each element is either sourced to a row of the V09
matrix or declared open because a row of that matrix is open. These tests hold
it to that, and hold the deriver to refusing when it cannot.

Four things they guard:

* The profile loads under the same loader the current profile loads under, and
  the current profile's bytes have not moved.
* Every element names rows that exist and can source it, and every matrix row
  reaches some element.
* A limitation is declared for exactly the rows the matrix leaves open.
* A freeze, preflight or scoring result made under one profile is refused
  against the other.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness import historical_profile as hp
from harness.profile import ProfileError, load_profile
from tools import author_msca_dn_historical_profile as author

REPO = Path(__file__).resolve().parents[1]
CRLF = b"\r\n"
LF = b"\n"
PROFILE = REPO / author.PROFILE_REL
CURRENT = REPO / author.CURRENT_PROFILE_REL
MATRIX = REPO / author.MATRIX_REL


@pytest.fixture(scope="module")
def declaration() -> hp.HistoricalProfile:
    return hp.load_historical_profile(PROFILE)


@pytest.fixture(scope="module")
def rows() -> dict[str, str]:
    return hp.load_matrix_rows(MATRIX)


# --------------------------------------------------------------------------- #
# 1. The deriver
# --------------------------------------------------------------------------- #


class TestTheDeriver:
    def test_the_tool_and_the_reader_declare_one_schema(self) -> None:
        """Deliberate double entry: a tool may not import the harness."""
        assert author.SCHEMA == hp.SCHEMA

    def test_the_tool_and_the_reader_agree_on_which_verdicts_can_source(self) -> None:
        assert author.SOURCING_VERDICTS == hp.SOURCING_VERDICTS

    def test_check_is_a_byte_equal_replay(self) -> None:
        assert author.check(REPO) == []

    def test_the_reading_is_committed_beside_the_declaration(self) -> None:
        assert PROFILE.with_suffix(".md").is_file()

    def test_both_files_carry_one_newline_convention(self) -> None:
        """The same bytes on every platform.

        The declaration's bytes are pinned by the decision record, and
        ``harness/profiles/** -text`` keeps git from renormalising them. A
        reading written through text mode would be CRLF on one platform and LF
        on another, so the same committed file would be fresh here and stale
        there over bytes nobody changed.
        """
        for path in (PROFILE, PROFILE.with_suffix(".md")):
            body = path.read_bytes()
            assert CRLF not in body, path.name
            assert body.count(LF) > 0, path.name
            assert body.count(b"\n") > 0, path.name

    def test_the_declaration_is_pending_operator_review(
        self, declaration: hp.HistoricalProfile
    ) -> None:
        assert declaration.review_state == "agent_drafted_pending_operator_review"

    def test_the_profile_declares_no_more_than_the_matrix_does(
        self, declaration: hp.HistoricalProfile
    ) -> None:
        """A profile cannot be more certain than its own source."""
        matrix = json.loads(MATRIX.read_text(encoding="utf-8-sig"))
        assert declaration.declared_status == matrix["declared_status"]
        assert declaration.declared_status != "Confirmed"


# --------------------------------------------------------------------------- #
# 2. Loading and the counterpart
# --------------------------------------------------------------------------- #


class TestLoading:
    def test_it_loads_under_the_same_loader_as_the_current_profile(self) -> None:
        historical = load_profile(PROFILE)
        current = load_profile(CURRENT)
        assert historical.profile_id != current.profile_id
        assert historical.profile_id == author.PROFILE_ID
        # One loader, two profiles: a second loader would be a second contract.
        assert [c.id for c in historical.criteria] == [c.id for c in current.criteria]

    def test_the_current_profile_is_unchanged(
        self, declaration: hp.HistoricalProfile
    ) -> None:
        """V10's third criterion, measured rather than asserted.

        The profile pins its counterpart's bytes, so an edit to the current
        profile shows up here and in the check.
        """
        assert declaration.counterpart is not None
        assert declaration.counterpart.path == author.CURRENT_PROFILE_REL.as_posix()
        assert (
            hashlib.sha256(CURRENT.read_bytes()).hexdigest()
            == declaration.counterpart.sha256
        )

    def test_the_two_profiles_name_different_calls(self) -> None:
        historical = json.loads(PROFILE.read_text(encoding="utf-8-sig"))
        current = json.loads(CURRENT.read_text(encoding="utf-8-sig"))
        assert historical["target_call"]["call_id"] != current["target_call"]["call_id"]
        assert historical["target_call"]["deadline"] == "2025-11-25"

    def test_the_structural_authority_is_the_2025_form(self) -> None:
        historical = json.loads(PROFILE.read_text(encoding="utf-8-sig"))
        current = json.loads(CURRENT.read_text(encoding="utf-8-sig"))
        assert historical["structural_authority"]["version"] == "5.0"
        assert current["structural_authority"]["version"] == "6.0"
        form = REPO / historical["structural_authority"]["path"]
        assert form.is_file()
        assert (
            hashlib.sha256(form.read_bytes()).hexdigest()
            == historical["structural_authority"]["sha256"]
        )


# --------------------------------------------------------------------------- #
# 3. The binding to the matrix
# --------------------------------------------------------------------------- #


class TestTheMatrixBinding:
    def test_the_check_is_green(
        self, declaration: hp.HistoricalProfile, rows: dict[str, str]
    ) -> None:
        report = hp.check(declaration, rows, REPO)
        assert report.green, report.lines()

    def test_every_element_names_rows_that_exist(
        self, declaration: hp.HistoricalProfile, rows: dict[str, str]
    ) -> None:
        for element in declaration.sourced:
            for row_id in element.rows:
                assert row_id in rows, f"{element.name}: {row_id}"

    def test_every_sourcing_row_can_source(
        self, declaration: hp.HistoricalProfile, rows: dict[str, str]
    ) -> None:
        """The finding that matters: no element rests on an open row."""
        for element in declaration.sourced:
            for row_id in element.rows:
                assert rows[row_id] in hp.SOURCING_VERDICTS, f"{element.name}: {row_id}"

    def test_every_matrix_row_reaches_an_element(
        self, declaration: hp.HistoricalProfile, rows: dict[str, str]
    ) -> None:
        """A row nobody reads is a rule the profile ignores in silence."""
        assert set(rows) - declaration.elements_read() == set()

    def test_a_limitation_is_declared_for_exactly_the_open_rows(
        self, declaration: hp.HistoricalProfile, rows: dict[str, str]
    ) -> None:
        open_rows = {rid for rid, verdict in rows.items() if verdict == "unresolved"}
        assert {lim.row for lim in declaration.limitations} == open_rows

    def test_each_limitation_names_the_rule_it_leaves_open(
        self, declaration: hp.HistoricalProfile
    ) -> None:
        for limitation in declaration.limitations:
            assert limitation.element.strip()
            assert len(limitation.limitation.split()) > 15, limitation.element

    def test_the_pinned_inputs_are_the_matrix_and_its_index(
        self, declaration: hp.HistoricalProfile
    ) -> None:
        pinned = {p.name: p for p in declaration.inputs}
        assert set(pinned) == {"matrix", "source_index"}
        for pin in pinned.values():
            path = REPO / pin.path
            assert path.is_file(), pin.path
            assert hashlib.sha256(path.read_bytes()).hexdigest() == pin.sha256, pin.path

    def test_the_harness_own_instruments_rest_on_era_neutral_rows(
        self, declaration: hp.HistoricalProfile, rows: dict[str, str]
    ) -> None:
        """Reusing an instrument is not a finding that a call prescribed it."""
        assert declaration.harness_own
        for element in declaration.harness_own:
            for row_id in element.rows:
                assert rows[row_id] == "era_neutral", f"{element.name}: {row_id}"


# --------------------------------------------------------------------------- #
# 4. The deriver refuses
# --------------------------------------------------------------------------- #


class TestTheDeriverRefuses:
    def test_an_element_sourced_to_a_row_the_matrix_does_not_have_refuses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(author.SOURCED_BY, "invented", ("ZZ-99",))
        with pytest.raises(author.HistoricalProfileError, match="no row ZZ-99"):
            author.render_profile(REPO)

    def test_an_element_sourced_to_an_open_row_refuses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The defect the profile exists to prevent.

        CI-01 records that the submission's binding to a call is not
        evidenced. An element sourced to it would be claiming the matrix
        settled that.
        """
        monkeypatch.setitem(author.SOURCED_BY, "criteria", ("CR-01", "CI-01"))
        with pytest.raises(author.HistoricalProfileError, match="cannot source an element"):
            author.render_profile(REPO)

    def test_a_limitation_over_a_row_that_is_sourced_refuses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        limited = tuple(
            (element, "TH-04" if element == "scorecard" else row, wording)
            for element, row, wording in author.LIMITED_BY
        )
        monkeypatch.setattr(author, "LIMITED_BY", limited)
        with pytest.raises(author.HistoricalProfileError, match="can be sourced instead"):
            author.render_profile(REPO)

    def test_a_matrix_row_no_element_reads_refuses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        trimmed = {k: v for k, v in author.SOURCED_BY.items() if k != "score_levels"}
        monkeypatch.setattr(author, "SOURCED_BY", trimmed)
        with pytest.raises(author.HistoricalProfileError, match="rows no profile element reads"):
            author.render_profile(REPO)

    def test_an_instrument_row_declared_the_harness_own_refuses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        own = tuple(
            (element, ("TH-01",) if element == "rubric_set" else ids, wording)
            for element, ids, wording in author.HARNESS_OWN
        )
        monkeypatch.setattr(author, "HARNESS_OWN", own)
        with pytest.raises(author.HistoricalProfileError, match="not era_neutral"):
            author.render_profile(REPO)

    def test_a_missing_document_refuses(self, tmp_path: Path) -> None:
        with pytest.raises(author.HistoricalProfileError, match="not in the tree"):
            author.render_profile(tmp_path)


# --------------------------------------------------------------------------- #
# 5. One profile's work is not another's
# --------------------------------------------------------------------------- #


class TestReuseAcrossAPairIsRefused:
    """V10's fifth criterion.

    A freeze, a preflight or a scoring result is made under one candidate and
    one profile. Reading it back under a different pair would carry a figure
    produced under other rules, which is the whole error the second profile
    exists to prevent.
    """

    def test_the_two_profiles_have_different_document_hashes(self) -> None:
        historical = load_profile(PROFILE)
        current = load_profile(CURRENT)
        assert historical.document_hash != current.document_hash

    def test_the_preflight_compares_the_profile_it_was_made_under(self) -> None:
        """The refusal is the existing machinery's, and it reads these fields."""
        body = (REPO / "harness/evidence_preflight.py").read_text(encoding="utf-8")
        # The comparison names both, so a report made under one profile is a
        # mismatch against the other rather than a silently reused figure.
        assert '_cmp("profile_id"' in body
        assert '_cmp("profile_version"' in body

    def test_the_freeze_binds_the_profile_version_it_was_made_under(self) -> None:
        body = (REPO / "harness/blind_baseline.py").read_text(encoding="utf-8")
        assert '"profile_id"' in body
        assert '"profile_version"' in body

    def test_a_profile_document_that_is_not_a_profile_is_refused(self) -> None:
        with pytest.raises(ProfileError):
            load_profile(MATRIX)
