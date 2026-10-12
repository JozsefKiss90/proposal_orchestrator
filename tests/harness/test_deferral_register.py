"""The open-deferral register reader and its check.

Seven groups:

* Loading fails closed. A missing field, an unknown schema, an unknown kind and
  an unknown state are refused rather than defaulted.
* The closure rule. A row marked ``closed`` without closure evidence fails the
  check, which is the register's reason to exist: nothing closes by
  inheritance.
* The sources. Every row cites a declared source, an immutable source whose
  bytes moved is an edit, and a tracked input whose bytes moved means the
  register is stale.
* The statements. A claim with no measurement fails, and a measurement the
  records contradict fails.
* The row pointers. A pointer into a JSON record resolves by field and one into
  any other record resolves as text, so a reworded criterion fails.
* The cross-reference. One row can name several observations and one
  observation can carry several rows.
* The command. It writes the reading, refuses a stale one under ``--check``, and
  exits 1 on a failing register or a malformed declaration.

Everything here runs on synthetic registers written into ``tmp_path``. The
committed register is checked by ``tests/test_msca_dn_deferral_register.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.commands.deferral_register as cmd
from harness import deferral_register as dr


# --------------------------------------------------------------------------- #
# Fixtures: a minimal valid register over two records on disk
# --------------------------------------------------------------------------- #


def _write_records(root: Path) -> None:
    """Two records a synthetic register can point at and measure."""
    (root / "records").mkdir(parents=True, exist_ok=True)
    (root / "records/decisions.json").write_text(
        json.dumps({"deferred": ["A", "B"], "total": 7}), encoding="utf-8"
    )
    (root / "records/approval.md").write_text("# approval\n", encoding="utf-8")


def _row(**over: object) -> dict:
    row = {
        "id": "ODR-A",
        "kind": "operator_decision_required",
        "subject": "Whether A holds is deferred to the private network.",
        "owner": "the private operator",
        "closure_evidence": "the original passage A names, compared with this copy",
        "original_required": True,
        "source": "records/decisions.json#deferred/#0",
        "state": "open",
    }
    row.update(over)
    return row


def _register(root: Path, **over: object) -> dict:
    data = {
        "schema": dr.SCHEMA,
        "register_name": "synthetic",
        "subject": "SYN-ALPHA-2099",
        "authored_on": "2099-01-01",
        "purpose": "One register of every open item, so nothing closes by inheritance.",
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": "Inferred",
        "supersedes": "nothing. This is the first register of this approval's deferrals.",
        "uncertainties": ["No row has ever been closed."],
        "sources": [
            {
                "path": "records/decisions.json",
                "sha256": dr.file_sha256(root / "records/decisions.json"),
                "role": "immutable_evidence",
                "holds": "the deferred decisions",
            },
            {
                "path": "records/approval.md",
                "sha256": dr.file_sha256(root / "records/approval.md"),
                "role": "tracked_input",
                "holds": "the approval prose",
            },
        ],
        "statements": [
            {
                "id": "S1",
                "claim": "Seven items were counted, and two are deferred.",
                "measurements": [
                    {
                        "id": "S1-M1",
                        "claim": "the record counts seven",
                        "record": "records/decisions.json",
                        "field": "total",
                        "expected": 7,
                    },
                    {
                        "id": "S1-M2",
                        "claim": "two are deferred",
                        "record": "records/decisions.json",
                        "field": "deferred",
                        "expected_length": 2,
                    },
                ],
            }
        ],
        "rows": [_row()],
    }
    data.update(over)
    return data


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    _write_records(tmp_path)
    return tmp_path


def _load(root: Path, data: dict) -> dr.Register:
    path = root / "register.json"
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return dr.load_register(path, repo_root=root)


# --------------------------------------------------------------------------- #
# 1. Loading fails closed
# --------------------------------------------------------------------------- #


class TestLoading:
    def test_a_valid_register_loads(self, root: Path):
        register = _load(root, _register(root))
        assert register.name == "synthetic"
        assert len(register.rows) == 1
        assert register.rows[0].original_required is True
        assert register.source == "register.json"
        assert register.review_state == "agent_drafted_pending_operator_review"
        assert register.declared_status == "Inferred"
        assert register.supersedes.startswith("nothing")
        assert register.uncertainties == ("No row has ever been closed.",)

    def test_a_foreign_schema_is_refused(self, root: Path):
        with pytest.raises(dr.DeferralRegisterError, match="schema"):
            _load(root, _register(root, schema="deferral_register/0"))

    @pytest.mark.parametrize(
        "key",
        [
            "register_name",
            "subject",
            "authored_on",
            "purpose",
            "review_state",
            "declared_status",
            "supersedes",
            "uncertainties",
            "sources",
            "rows",
        ],
    )
    def test_a_missing_top_level_field_is_refused(self, root: Path, key: str):
        data = _register(root)
        del data[key]
        with pytest.raises(dr.DeferralRegisterError, match=key):
            _load(root, data)

    @pytest.mark.parametrize(
        "key",
        ["id", "kind", "subject", "owner", "closure_evidence", "original_required", "source"],
    )
    def test_a_missing_row_field_is_refused(self, root: Path, key: str):
        row = _row()
        del row[key]
        with pytest.raises(dr.DeferralRegisterError, match=key):
            _load(root, _register(root, rows=[row]))

    def test_an_unknown_kind_is_refused(self, root: Path):
        with pytest.raises(dr.DeferralRegisterError, match="kind"):
            _load(root, _register(root, rows=[_row(kind="someday")]))

    def test_an_unknown_state_is_refused(self, root: Path):
        with pytest.raises(dr.DeferralRegisterError, match="state"):
            _load(root, _register(root, rows=[_row(state="in_progress")]))

    def test_an_unknown_review_state_is_refused(self, root: Path):
        with pytest.raises(dr.DeferralRegisterError, match="review_state"):
            _load(root, _register(root, review_state="looks_fine"))

    def test_a_status_outside_the_four_is_refused(self, root: Path):
        """CLAUDE.md section 12.2's vocabulary and no fifth term."""
        with pytest.raises(dr.DeferralRegisterError, match="declared_status"):
            _load(root, _register(root, declared_status="Probably"))

    def test_an_unknown_source_role_is_refused(self, root: Path):
        data = _register(root)
        data["sources"][0]["role"] = "whatever"
        with pytest.raises(dr.DeferralRegisterError, match="role"):
            _load(root, data)

    def test_a_measurement_declaring_neither_expectation_is_refused(self, root: Path):
        data = _register(root)
        del data["statements"][0]["measurements"][0]["expected"]
        with pytest.raises(dr.DeferralRegisterError, match="expected"):
            _load(root, data)

    def test_a_measurement_declaring_both_expectations_is_refused(self, root: Path):
        data = _register(root)
        data["statements"][0]["measurements"][0]["expected_length"] = 1
        with pytest.raises(dr.DeferralRegisterError, match="expected"):
            _load(root, data)

    def test_state_defaults_to_open(self, root: Path):
        row = _row()
        del row["state"]
        register = _load(root, _register(root, rows=[row]))
        assert register.rows[0].state == "open"


# --------------------------------------------------------------------------- #
# 2. The closure rule
# --------------------------------------------------------------------------- #


class TestTheClosureRule:
    def test_the_minimal_register_is_green(self, root: Path):
        check = dr.check(_load(root, _register(root)), root)
        assert check.green, check.lines()

    def test_a_closed_row_without_evidence_fails(self, root: Path):
        """The register's reason to exist. A box checked with nothing behind it
        is the failure mode the approval's own terms produce by inheritance."""
        register = _load(root, _register(root, rows=[_row(state="closed")]))
        check = dr.check(register, root)
        assert check.closed_without_evidence == ("ODR-A",)
        assert not check.green
        assert any("CLOSED WITHOUT EVIDENCE" in line for line in check.lines())

    def test_a_closed_row_with_evidence_passes(self, root: Path):
        register = _load(
            root,
            _register(
                root,
                rows=[
                    _row(
                        state="closed",
                        closed_by=["plans/reports/some_completion_report.md section 3"],
                        closed_on="2099-02-02",
                    )
                ],
            ),
        )
        check = dr.check(register, root)
        assert check.closed_without_evidence == ()
        assert check.green, check.lines()

    def test_closure_evidence_that_is_only_whitespace_does_not_close_a_row(self, root: Path):
        register = _load(
            root, _register(root, rows=[_row(state="closed", closed_by=["   ", ""])])
        )
        assert dr.check(register, root).closed_without_evidence == ("ODR-A",)

    def test_a_closed_row_without_a_date_fails(self, root: Path):
        """Closure evidence with no date cannot be placed against the records
        it claims to rest on."""
        register = _load(
            root, _register(root, rows=[_row(state="closed", closed_by=["a report"])])
        )
        check = dr.check(register, root)
        assert "ODR-A" in check.closed_without_date

    def test_an_open_row_carrying_closure_evidence_fails(self, root: Path):
        """Evidence recorded against an open row is either a closure nobody
        checked or evidence filed on the wrong row. Either way it is reported."""
        register = _load(root, _register(root, rows=[_row(closed_by=["a report"])]))
        check = dr.check(register, root)
        assert check.open_rows_carrying_closure == ("ODR-A",)

    def test_an_empty_owner_or_closure_evidence_fails(self, root: Path):
        register = _load(
            root,
            _register(
                root,
                rows=[
                    _row(id="R1", owner="  "),
                    _row(id="R2", closure_evidence=""),
                ],
            ),
        )
        check = dr.check(register, root)
        assert check.rows_missing_field == ("R1: owner", "R2: closure_evidence")

    def test_duplicate_row_ids_fail(self, root: Path):
        register = _load(root, _register(root, rows=[_row(), _row()]))
        assert dr.check(register, root).duplicate_row_ids == ("ODR-A",)

    def test_counts_report_the_open_rows_by_kind(self, root: Path):
        register = _load(
            root,
            _register(
                root,
                rows=[
                    _row(id="R1"),
                    _row(id="R2", kind="deferred_question", original_required=False),
                    _row(
                        id="R3",
                        kind="deferred_question",
                        state="closed",
                        closed_by=["a report"],
                        closed_on="2099-02-02",
                    ),
                ],
            ),
        )
        assert register.open_rows_by_kind() == {
            "operator_decision_required": 1,
            "deferred_question": 1,
        }
        assert register.rows_requiring_the_original() == ("R1",)
        assert register.closed_rows() == ("R3",)


# --------------------------------------------------------------------------- #
# 3. The pointers
# --------------------------------------------------------------------------- #


class TestThePointers:
    def test_a_row_citing_an_undeclared_source_fails(self, root: Path):
        register = _load(root, _register(root, rows=[_row(source="records/elsewhere.json#x")]))
        check = dr.check(register, root)
        assert check.rows_citing_undeclared_source == ("ODR-A: records/elsewhere.json",)

    def test_an_absent_source_fails(self, root: Path):
        data = _register(root)
        data["sources"].append(
            {
                "path": "records/gone.json",
                "sha256": "0" * 64,
                "role": "immutable_evidence",
                "holds": "nothing on disk",
            }
        )
        check = dr.check(_load(root, data), root)
        assert check.missing_sources == ("records/gone.json",)

    def test_an_edited_immutable_source_fails_as_an_edit(self, root: Path):
        register = _load(root, _register(root))
        (root / "records/decisions.json").write_text("{}", encoding="utf-8")
        check = dr.check(register, root)
        assert check.edited_immutable_sources == ("records/decisions.json",)
        assert check.stale_tracked_inputs == ()
        assert any("EDITED" in line for line in check.lines())

    def test_a_changed_tracked_input_fails_as_staleness(self, root: Path):
        """A tracked input is allowed to move. The register is then out of date,
        which is a different finding from an edited immutable record."""
        register = _load(root, _register(root))
        (root / "records/approval.md").write_text("# approval\n\nand more\n", encoding="utf-8")
        check = dr.check(register, root)
        assert check.stale_tracked_inputs == ("records/approval.md",)
        assert check.edited_immutable_sources == ()
        assert any("STALE" in line for line in check.lines())


# --------------------------------------------------------------------------- #
# 4. The statements
# --------------------------------------------------------------------------- #


class TestTheStatements:
    def test_a_statement_with_no_measurement_fails(self, root: Path):
        data = _register(root)
        data["statements"][0]["measurements"] = []
        check = dr.check(_load(root, data), root)
        assert check.statements_without_measurement == ("S1",)

    def test_a_measurement_the_record_contradicts_fails(self, root: Path):
        data = _register(root)
        data["statements"][0]["measurements"][0]["expected"] = 8
        check = dr.check(_load(root, data), root)
        assert check.failed_measurements == ("S1-M1: total is 7, expected 8",)

    def test_a_length_measurement_the_record_contradicts_fails(self, root: Path):
        data = _register(root)
        data["statements"][0]["measurements"][1]["expected_length"] = 3
        check = dr.check(_load(root, data), root)
        assert check.failed_measurements == ("S1-M2: deferred has length 2, expected 3",)

    def test_a_measurement_of_a_missing_field_fails(self, root: Path):
        data = _register(root)
        data["statements"][0]["measurements"][0]["field"] = "absent"
        check = dr.check(_load(root, data), root)
        assert check.failed_measurements == ("S1-M1: absent does not resolve",)

    def test_a_measurement_of_an_undeclared_record_fails(self, root: Path):
        data = _register(root)
        data["statements"][0]["measurements"][0]["record"] = "records/elsewhere.json"
        check = dr.check(_load(root, data), root)
        assert check.measurements_citing_undeclared_source == (
            "S1-M1: records/elsewhere.json",
        )

    def test_a_length_measurement_of_a_scalar_fails(self, root: Path):
        data = _register(root)
        data["statements"][0]["measurements"][1]["field"] = "total"
        check = dr.check(_load(root, data), root)
        assert check.failed_measurements == ("S1-M2: total has no length",)

    def test_a_nested_field_resolves(self, root: Path):
        (root / "records/decisions.json").write_text(
            json.dumps({"deferred": [], "total": 0, "state": {"rows": ["a"]}}), encoding="utf-8"
        )
        data = _register(root)
        data["sources"][0]["sha256"] = dr.file_sha256(root / "records/decisions.json")
        data["statements"][0]["measurements"] = [
            {
                "id": "S1-M1",
                "claim": "one row",
                "record": "records/decisions.json",
                "field": "state/rows",
                "expected_length": 1,
            }
        ]
        data["rows"] = [_row(source="records/decisions.json#state/rows")]
        check = dr.check(_load(root, data), root)
        assert check.green, check.lines()


# --------------------------------------------------------------------------- #
# 5. A row's pointer resolves
# --------------------------------------------------------------------------- #


class TestRowPointers:
    def test_a_json_pointer_that_does_not_resolve_fails(self, root: Path):
        register = _load(root, _register(root, rows=[_row(source="records/decisions.json#absent")]))
        check = dr.check(register, root)
        assert check.rows_whose_pointer_does_not_resolve == ("ODR-A: absent",)

    def test_a_json_source_with_no_pointer_resolves_to_the_record(self, root: Path):
        register = _load(root, _register(root, rows=[_row(source="records/decisions.json")]))
        assert dr.check(register, root).rows_whose_pointer_does_not_resolve == ()

    def test_a_text_pointer_the_document_carries_resolves(self, root: Path):
        register = _load(root, _register(root, rows=[_row(source="records/approval.md#approval")]))
        assert dr.check(register, root).rows_whose_pointer_does_not_resolve == ()

    def test_a_text_pointer_the_document_does_not_carry_fails(self, root: Path):
        register = _load(root, _register(root, rows=[_row(source="records/approval.md#rejection")]))
        check = dr.check(register, root)
        assert check.rows_whose_pointer_does_not_resolve == ("ODR-A: rejection",)
        assert any("POINTER" in line for line in check.lines())

    def test_a_pointer_into_an_absent_source_is_reported_once_as_the_missing_source(
        self, root: Path
    ):
        """The source is already reported absent. Reporting the pointer too
        would make one defect read as two."""
        data = _register(root)
        data["sources"].append(
            {
                "path": "records/gone.json",
                "sha256": "0" * 64,
                "role": "immutable_evidence",
                "holds": "nothing on disk",
            }
        )
        data["rows"] = [_row(source="records/gone.json#x")]
        check = dr.check(_load(root, data), root)
        assert check.missing_sources == ("records/gone.json",)
        assert check.rows_whose_pointer_does_not_resolve == ()


# --------------------------------------------------------------------------- #
# 6. The observation cross-reference
# --------------------------------------------------------------------------- #


class TestObservations:
    def test_rows_over_one_observation_are_mapped_together(self, root: Path):
        """A row can name several observations and an observation can carry
        several rows. Both are what keep 34 rows from reading as 34 items."""
        register = _load(
            root,
            _register(
                root,
                rows=[
                    _row(id="R1", observation_ids=["O-1"]),
                    _row(id="R2", kind="deferred_question", observation_ids=["O-1", "O-2"]),
                    _row(id="R3", kind="ticket_criterion"),
                ],
            ),
        )
        assert register.observations() == {"O-1": ("R1", "R2"), "O-2": ("R2",)}

    def test_a_row_naming_no_observation_is_in_no_group(self, root: Path):
        register = _load(root, _register(root, rows=[_row(id="R1")]))
        assert register.observations() == {}


# --------------------------------------------------------------------------- #
# 7. The command
# --------------------------------------------------------------------------- #


class TestTheCommand:
    def test_it_writes_the_reading_and_exits_zero(self, root: Path, capsys):
        _load(root, _register(root))
        assert cmd.main(["--register", "register.json", "--repo-root", str(root)]) == 0
        reading = root / "register.md"
        assert reading.is_file()
        assert "# Open-deferral register" in reading.read_text(encoding="utf-8")
        assert "register check: green" in capsys.readouterr().out

    def test_check_refuses_a_stale_reading_and_writes_nothing(self, root: Path, capsys):
        _load(root, _register(root))
        (root / "register.md").write_text("stale\n", encoding="utf-8")
        assert cmd.main(["--register", "register.json", "--repo-root", str(root), "--check"]) == 1
        assert (root / "register.md").read_text(encoding="utf-8") == "stale\n"
        assert "would change" in capsys.readouterr().out

    def test_it_exits_one_on_a_row_closed_without_evidence(self, root: Path, capsys):
        _load(root, _register(root, rows=[_row(state="closed")]))
        assert cmd.main(["--register", "register.json", "--repo-root", str(root)]) == 1
        assert "CLOSED WITHOUT EVIDENCE" in capsys.readouterr().out

    def test_it_refuses_a_malformed_declaration(self, root: Path, capsys):
        (root / "register.json").write_text('{"schema": "other"}', encoding="utf-8")
        assert cmd.main(["--register", "register.json", "--repo-root", str(root)]) == 1
        assert "refused" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# 8. An unreadable record is not a lost field
# --------------------------------------------------------------------------- #


class TestAnUnreadableRecord:
    def test_malformed_json_is_reported_as_unreadable(self, root: Path):
        """A record that cannot be parsed is a different defect from one whose
        shape moved. Reporting the second for the first sends a reader to the
        wrong place."""
        data = _register(root)
        (root / "records/decisions.json").write_text("{not json", encoding="utf-8")
        data["sources"][0]["sha256"] = dr.file_sha256(root / "records/decisions.json")
        data["rows"] = [_row(source="records/decisions.json")]
        check = dr.check(_load(root, data), root)
        assert check.failed_measurements == (
            "S1-M1: records/decisions.json is not readable JSON (JSONDecodeError)",
            "S1-M2: records/decisions.json is not readable JSON (JSONDecodeError)",
        )
