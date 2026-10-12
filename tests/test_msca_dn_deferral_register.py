"""The committed open-deferral register (V11, 2026-10-12).

Three groups:

* The renderer. ``--check`` is a byte-equal replay, the register check is green,
  every binding is the hash of the file on disk, and nothing the register reads
  was edited.
* The rows. Each group is reconciled against the record it is derived from: the
  ten deferred rows and the ten agent-recommended rows against the approved
  dispositions' own lists, the two qualified interpretations against the
  intersection the record states, the single unresolved marker against the only
  row declared Unresolved, the eight deferred questions against the approval's
  own table, and the one ticket criterion against the unchecked box in the
  predecessor ledger. Every row is open, names an owner and closure evidence,
  and declares whether the original is needed.
* The statements. Both are measured against bound records, and the tool refuses
  to render a statement the records no longer support.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

import harness.commands.deferral_register as cmd
from harness import deferral_register as dr
from runner.paths import find_repo_root
from tools import author_deferral_register as adr

REPO = find_repo_root()

pytestmark = pytest.mark.skipif(
    not (REPO / adr.REGISTER_REL).is_file(), reason="the deferral register is absent"
)


def _read(rel: Path) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def register() -> dr.Register:
    return dr.load_register(REPO / adr.REGISTER_REL, repo_root=REPO)


@pytest.fixture(scope="module")
def dispositions() -> dict:
    return _read(adr.DISPOSITIONS_REL)


@pytest.fixture(scope="module")
def approval() -> str:
    return (REPO / adr.APPROVAL_REL).read_text(encoding="utf-8-sig")


# --------------------------------------------------------------------------- #
# 1. The renderer
# --------------------------------------------------------------------------- #


class TestTheRenderer:
    def test_the_rendering_replays_byte_equal(self):
        assert adr.check(REPO) == []

    def test_the_register_check_is_green(self, register: dr.Register):
        result = dr.check(register, REPO)
        assert result.green, result.lines()

    def test_the_authoring_tool_and_the_reader_declare_one_schema(self):
        """Deliberate double entry: the tool may not import the harness, so the
        schema string exists twice and this is what keeps the two in step."""
        assert adr.SCHEMA == dr.SCHEMA

    def test_the_command_checks_and_reproduces_the_reading(self, capsys):
        assert cmd.main(["--register", adr.REGISTER_REL.as_posix(), "--check"]) == 0
        printed = capsys.readouterr().out
        assert "register check: green" in printed
        assert "would change" not in printed

    def test_every_binding_is_the_hash_of_the_file_on_disk(self, register: dr.Register):
        for source in register.sources:
            path = REPO / source.path
            assert path.is_file(), source.path
            assert source.sha256 == dr.file_sha256(path), source.path

    def test_the_approval_record_and_the_dispositions_are_bound_as_immutable(
        self, register: dr.Register
    ):
        roles = {s.path: s.role for s in register.sources}
        assert roles[adr.APPROVAL_REL.as_posix()] == "immutable_evidence"
        assert roles[adr.DISPOSITIONS_REL.as_posix()] == "immutable_evidence"
        assert roles[adr.LEDGER_REL.as_posix()] == "tracked_input"

    def test_the_approval_record_still_carries_the_hash_the_dispositions_pinned(
        self, dispositions: dict
    ):
        """Neither this register nor anything else edited the approval record:
        its hash is the one the approved dispositions recorded on 2026-10-08."""
        pinned = dispositions["review_inputs"]["approval_record_sha256"]
        assert dr.file_sha256(REPO / adr.APPROVAL_REL) == pinned

    def test_the_rendered_reading_is_written_beside_the_register(self):
        reading = cmd.reading_path(REPO / adr.REGISTER_REL)
        assert reading.is_file()
        assert reading.name.endswith(".md")

    def test_the_register_closes_nothing(self, register: dr.Register):
        assert register.closed_rows() == ()
        assert len(register.open_rows()) == len(register.rows)


# --------------------------------------------------------------------------- #
# 2. The rows
# --------------------------------------------------------------------------- #


class TestTheRows:
    def test_the_row_groups_are_the_ticket_s_enumeration(self, register: dr.Register):
        assert register.open_rows_by_kind() == {
            "ticket_criterion": 1,
            "operator_decision_required": 10,
            "agent_recommendation": 10,
            "qualified_interpretation": 2,
            "assessor_validation_case": 2,
            "unresolved_disposition": 1,
            "deferred_question": 8,
        }
        assert len(register.rows) == 34

    def test_every_row_id_is_unique(self, register: dr.Register):
        duplicates = [i for i, n in Counter(r.id for r in register.rows).items() if n > 1]
        assert duplicates == []

    def test_every_row_names_an_owner_and_its_closure_evidence(self, register: dr.Register):
        for row in register.rows:
            assert row.owner.strip(), row.id
            assert row.closure_evidence.strip(), row.id
            assert isinstance(row.original_required, bool), row.id

    def test_the_deferred_rows_are_the_dispositions_own_list(
        self, register: dr.Register, dispositions: dict
    ):
        declared = dispositions["decision_state"]["rows_operator_decision_required"]
        rows = [r for r in register.rows if r.kind == "operator_decision_required"]
        assert [r.observation_ids[0] for r in rows] == declared
        assert all(r.original_required for r in rows)

    def test_the_agent_recommended_rows_are_the_dispositions_own_list(
        self, register: dr.Register, dispositions: dict
    ):
        declared = dispositions["decision_state"]["rows_agent_recommended"]
        rows = [r for r in register.rows if r.kind == "agent_recommendation"]
        assert [r.observation_ids[0] for r in rows] == declared
        assert not any(r.original_required for r in rows)

    def test_the_qualified_interpretations_are_the_intersection_the_record_states(
        self, register: dr.Register, dispositions: dict
    ):
        """The approved dispositions' own statement: two rows are confirmed on
        their disposition and also carry a deferral."""
        state = dispositions["decision_state"]
        deferred = {e["observation_id"] for e in dispositions["open_operator_decisions"]}
        expected = [o for o in state["rows_operator_confirmed"] if o in deferred]
        rows = [r for r in register.rows if r.kind == "qualified_interpretation"]
        assert [r.observation_ids[0] for r in rows] == expected
        assert expected == ["ESR-Q-01", "ESR-Q-03"]

    def test_the_unresolved_marker_is_the_only_row_declared_unresolved(
        self, register: dr.Register, dispositions: dict
    ):
        expected = [
            r["observation_id"]
            for r in dispositions["rows"]
            if r.get("declared_status") == "Unresolved"
        ]
        rows = [r for r in register.rows if r.kind == "unresolved_disposition"]
        assert [r.observation_ids[0] for r in rows] == expected == ["ESR-E-04"]

    def test_the_validation_cases_are_the_records_own_two(
        self, register: dr.Register, dispositions: dict
    ):
        cases = dispositions["assessor_validation_cases"]
        rows = [r for r in register.rows if r.kind == "assessor_validation_case"]
        assert [r.id for r in rows] == [c["id"] for c in cases] == ["AVC-01", "AVC-02"]
        for row, case in zip(rows, cases):
            assert row.observation_ids == tuple(case["observation_ids"])
            # Read off the recorded limit rather than decided here.
            assert row.original_required == ("original-dependent" in case["limit"])

    def test_the_deferred_questions_are_the_approval_records_own_table(
        self, register: dr.Register, approval: str
    ):
        table = adr._deferred_table(approval)
        rows = [r for r in register.rows if r.kind == "deferred_question"]
        assert len(rows) == len(table) == 8
        for row, entry in zip(rows, table):
            assert entry["evidence"] in row.closure_evidence
            assert row.original_required

    def test_the_ticket_criterion_row_carries_its_unmet_precondition(
        self, register: dr.Register
    ):
        rows = [r for r in register.rows if r.kind == "ticket_criterion"]
        assert len(rows) == 1
        row = rows[0]
        assert "D13" in row.precondition
        assert adr.R04_CRITERION in row.subject
        assert row.source.startswith(adr.LEDGER_REL.as_posix() + "#")

    def test_the_ticket_criterion_is_still_unchecked_in_the_ledger(self):
        line = adr._r04_criterion_line(
            (REPO / adr.LEDGER_REL).read_text(encoding="utf-8-sig")
        )
        assert line.startswith(adr.R04_CRITERION)

    def test_rendering_refuses_once_the_ledger_checks_the_criterion(self):
        """The row exists because the box is unchecked. Checking the box has to
        close the row with evidence, not re-derive it as open."""
        with pytest.raises(adr.DeferralAuthoringError, match="now checked"):
            adr._r04_criterion_line(f"- [x] {adr.R04_CRITERION} (done)")

    def test_rows_over_one_observation_are_cross_referenced(self, register: dr.Register):
        """ESR-E-04 is open three times for three reasons. A reader who counted
        them as three repairs would be counting one observation."""
        observations = register.observations()
        assert observations["ESR-E-04"] == ("ODR-ESR-E-04", "UNR-ESR-E-04", "DQ-01")
        assert observations["ESR-Q-01"] == ("QI-ESR-Q-01", "AVC-01", "DQ-06")

    def test_the_rows_needing_the_original_are_counted(self, register: dr.Register):
        needing = register.rows_requiring_the_original()
        assert len(needing) == 22
        assert "AGR-ESR-E-06" not in needing


# --------------------------------------------------------------------------- #
# 3. The statements
# --------------------------------------------------------------------------- #


class TestTheStatements:
    def test_both_required_statements_are_present_and_measured(self, register: dr.Register):
        assert [s.id for s in register.statements] == ["S1", "S2"]
        for statement in register.statements:
            assert statement.measurements, statement.id

    def test_the_finding_sequence_statement_is_the_three_audits_own_totals(
        self, register: dr.Register
    ):
        totals = [
            _read(rel)["findings_total"]
            for rel in (adr.AUDIT_R03_REL, adr.AUDIT_R04_REL, adr.AUDIT_APPROVED_REL)
        ]
        assert totals == [40, 29, 13]
        claim = next(s for s in register.statements if s.id == "S1").claim
        assert "40 to 29 to 13" in claim
        assert "27" in claim
        assert "not 27 repaired proposal defects" in claim

    def test_the_three_readings_are_of_one_unchanged_candidate(self):
        records = [
            _read(rel)
            for rel in (adr.AUDIT_R03_REL, adr.AUDIT_R04_REL, adr.AUDIT_APPROVED_REL)
        ]
        assert len({r["candidate_hash"] for r in records}) == 1
        assert len({r["document_id"] for r in records}) == 1

    def test_every_criticism_still_carries_open_revision_work(self, register: dr.Register):
        revisions = _read(adr.REVISIONS_REL)
        esr = _read(adr.ESR_REL)
        criticisms = {o["id"] for o in esr["observations"] if o["kind"] != "strength"}
        assert len(criticisms) == 15
        assert {r["observation_id"] for r in revisions["open"]} == criticisms
        assert revisions["closed"] == []
        claim = next(s for s in register.statements if s.id == "S2").claim
        assert "All 15" in claim

    def test_rendering_refuses_once_a_revision_row_closes(self):
        """The statement that every criticism has open revision work cannot be
        reprinted over a plan that has closed one."""
        revisions = {"open": [], "closed": [{"observation_id": "ESR-E-01"}]}
        with pytest.raises(adr.DeferralAuthoringError, match="revision rows are closed"):
            adr._statements(revisions, _read(adr.ESR_REL), {}, "h", "d")

    def test_rendering_refuses_when_the_open_rows_are_not_the_criticisms(self):
        esr = _read(adr.ESR_REL)
        revisions = {"open": [{"observation_id": "ESR-E-01"}], "closed": []}
        with pytest.raises(adr.DeferralAuthoringError, match="not the criticisms"):
            adr._statements(revisions, esr, {}, "h", "d")


# --------------------------------------------------------------------------- #
# 4. The ledger's shared constraints on a new artifact
# --------------------------------------------------------------------------- #


class TestTheSharedConstraints:
    """"Every new artifact identifies its inputs, review state, uncertainties
    and relationship to earlier versions." — the ledger's shared constraints."""

    def test_it_identifies_its_inputs(self, register: dr.Register):
        assert len(register.sources) == 8

    def test_it_declares_its_review_state_and_claims_no_review(
        self, register: dr.Register
    ):
        assert register.review_state == "agent_drafted_pending_operator_review"

    def test_its_own_reading_is_inferred_rather_than_confirmed(self, register: dr.Register):
        """That a row is still open is read off the absence of a closing
        decision, and an absence is not a confirmation."""
        assert register.declared_status == "Inferred"

    def test_it_states_its_relationship_to_earlier_versions(self, register: dr.Register):
        assert register.supersedes.startswith("nothing")

    def test_it_carries_its_uncertainties_in_the_artifact(self, register: dr.Register):
        assert len(register.uncertainties) >= 4
        joined = " ".join(register.uncertainties)
        assert "tracked input" in joined
        assert "No row has ever been closed" in joined

    def test_the_reading_prints_all_four(self, register: dr.Register):
        rendered = dr.render_report(register)
        assert "Review state:" in rendered
        assert "Relationship to earlier versions:" in rendered
        assert "## What the author of this register is unsure of" in rendered
        assert "## The records this register binds" in rendered
