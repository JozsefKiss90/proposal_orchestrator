"""The historical-profile reader, over a synthetic profile and matrix.

Every finding is exercised against a declaration built here rather than against
the committed one. A reader tested only on a green artifact is a reader whose
findings have never fired.

The declarations below name no instrument and no year, which is also the
reader's own contract: the declaration supplies both.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from harness import historical_profile as hp


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


MATRIX_ROWS: list[dict[str, Any]] = [
    {"id": "A-01", "verdict": "equivalent"},
    {"id": "A-02", "verdict": "differs"},
    {"id": "B-01", "verdict": "era_neutral"},
    {"id": "C-01", "verdict": "unresolved"},
]


def _matrix_doc(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema": "synthetic_matrix/1",
        "declared_status": "Inferred",
        "rows": MATRIX_ROWS if rows is None else rows,
    }


def _profile_doc(
    *,
    matrix_path: str,
    matrix_sha: str,
    index_path: str,
    index_sha: str,
    counterpart_path: str,
    counterpart_sha: str,
    sourced: dict[str, Any] | None = None,
    limitations: list[dict[str, Any]] | None = None,
    harness_own: list[dict[str, Any]] | None = None,
    declared_status: str = "Inferred",
) -> dict[str, Any]:
    return {
        "schema": hp.SCHEMA,
        "profile_id": "synthetic_historical",
        "label": "a synthetic historical profile",
        "authored_on": "2026-10-13",
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": declared_status,
        "purpose": "exercise the reader",
        "written_by": "tests",
        "counterpart": {"path": counterpart_path, "sha256": counterpart_sha},
        "authored_from": {
            "matrix": {"path": matrix_path, "sha256": matrix_sha},
            "source_index": {"path": index_path, "sha256": index_sha},
            "rule": "both pinned",
        },
        "sourced_from_the_matrix": (
            {
                "criteria": {"matrix_rows": ["A-01"], "verdicts": ["equivalent"]},
                "thresholds": {"matrix_rows": ["A-02"], "verdicts": ["differs"]},
            }
            if sourced is None
            else sourced
        ),
        "declared_limitations": (
            [
                {
                    "element": "target_call",
                    "matrix_row": "C-01",
                    "verdict": "unresolved",
                    "limitation": "the binding is declared by two records and evidenced by none",
                }
            ]
            if limitations is None
            else limitations
        ),
        "the_harness_own_instruments": (
            [
                {
                    "element": "rubric_set",
                    "matrix_rows": ["B-01"],
                    "why": "the grading instrument is this harness's own, not a rule of a call",
                }
            ]
            if harness_own is None
            else harness_own
        ),
    }


@pytest.fixture
def world(tmp_path: Path):
    """A root with a matrix, an index and a counterpart profile on disk."""
    (tmp_path / "authority").mkdir(parents=True, exist_ok=True)
    (tmp_path / "profiles").mkdir(parents=True, exist_ok=True)
    matrix = tmp_path / "authority/matrix.json"
    index = tmp_path / "authority/index.json"
    counterpart = tmp_path / "profiles/current.json"
    profile = tmp_path / "profiles/historical.json"
    index.write_text(json.dumps({"sources": []}), encoding="utf-8")
    counterpart.write_text(json.dumps({"profile_id": "synthetic_current"}), encoding="utf-8")

    def build(
        rows: list[dict[str, Any]] | None = None, **overrides: Any
    ) -> tuple[hp.HistoricalProfile, dict[str, str]]:
        matrix.write_text(json.dumps(_matrix_doc(rows)), encoding="utf-8")
        doc = _profile_doc(
            matrix_path="authority/matrix.json",
            matrix_sha=_sha(matrix),
            index_path="authority/index.json",
            index_sha=_sha(index),
            counterpart_path="profiles/current.json",
            counterpart_sha=_sha(counterpart),
            **overrides,
        )
        profile.write_text(json.dumps(doc), encoding="utf-8")
        return hp.load_historical_profile(profile), hp.load_matrix_rows(matrix)

    build.root = tmp_path  # type: ignore[attr-defined]
    build.paths = {  # type: ignore[attr-defined]
        "matrix": matrix,
        "index": index,
        "counterpart": counterpart,
        "profile": profile,
    }
    return build


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


class TestLoading:
    def test_a_green_declaration_loads_and_checks_green(self, world) -> None:
        profile, rows = world()
        report = hp.check(profile, rows, world.root)
        assert report.green, report.lines()
        assert report.findings_total == 0

    def test_a_foreign_schema_is_refused(self, world) -> None:
        profile, _ = world()
        path = world.paths["profile"]
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["schema"] = "something_else/1"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(hp.HistoricalProfileError, match="schema is"):
            hp.load_historical_profile(path)

    def test_an_element_with_no_row_is_refused_at_load(self, world) -> None:
        with pytest.raises(hp.HistoricalProfileError, match="names no row"):
            world(sourced={"criteria": {"matrix_rows": [], "verdicts": []}})

    def test_a_row_count_that_does_not_match_its_verdicts_is_refused(self, world) -> None:
        with pytest.raises(hp.HistoricalProfileError, match="one per row"):
            world(sourced={"criteria": {"matrix_rows": ["A-01", "A-02"], "verdicts": ["equivalent"]}})

    def test_an_empty_limitation_is_refused(self, world) -> None:
        with pytest.raises(hp.HistoricalProfileError, match="says nothing"):
            world(
                limitations=[
                    {
                        "element": "target_call",
                        "matrix_row": "C-01",
                        "verdict": "unresolved",
                        "limitation": "   ",
                    }
                ]
            )

    def test_a_matrix_with_no_rows_is_refused(self, world) -> None:
        with pytest.raises(hp.HistoricalProfileError, match="carries no rows"):
            world(rows=[])


# --------------------------------------------------------------------------- #
# The findings
# --------------------------------------------------------------------------- #


class TestTheFindings:
    def test_an_element_naming_a_row_the_matrix_lacks(self, world) -> None:
        profile, rows = world(
            sourced={
                "criteria": {"matrix_rows": ["Z-99"], "verdicts": ["equivalent"]},
                "thresholds": {"matrix_rows": ["A-02"], "verdicts": ["differs"]},
            }
        )
        report = hp.check(profile, rows, world.root)
        assert report.elements_naming_a_missing_row == ("criteria: Z-99",)

    def test_an_element_sourced_to_an_open_row(self, world) -> None:
        """The finding the whole module exists for.

        An element resting on a row that records something as open is the
        profile claiming the matrix settled what it said it had not.
        """
        profile, rows = world(
            sourced={
                "criteria": {"matrix_rows": ["C-01"], "verdicts": ["unresolved"]},
                "thresholds": {"matrix_rows": ["A-02"], "verdicts": ["differs"]},
            },
            limitations=[],
        )
        report = hp.check(profile, rows, world.root)
        assert report.elements_sourced_to_a_row_that_cannot_source == (
            "criteria: C-01 is unresolved",
        )

    def test_a_row_no_element_reads(self, world) -> None:
        profile, rows = world(
            sourced={"criteria": {"matrix_rows": ["A-01"], "verdicts": ["equivalent"]}}
        )
        report = hp.check(profile, rows, world.root)
        assert report.rows_no_element_reads == ("A-02",)

    def test_a_limitation_whose_row_has_since_been_sourced(self, world) -> None:
        profile, rows = world(
            limitations=[
                {
                    "element": "target_call",
                    "matrix_row": "A-01",
                    "verdict": "equivalent",
                    "limitation": "a limitation over a row the matrix now sources",
                }
            ]
        )
        report = hp.check(profile, rows, world.root)
        assert report.limitations_whose_row_is_no_longer_open == (
            "target_call: A-01 is now equivalent",
        )
        assert report.rows_no_element_reads == ("C-01",)

    def test_a_declaration_whose_verdict_is_out_of_date(self, world) -> None:
        """Two committed records drifting apart, reported as that.

        The declaration records the verdict it was written against, so a
        matrix whose verdict moved is a finding rather than a silent change
        of meaning.
        """
        profile, rows = world(
            sourced={
                "criteria": {"matrix_rows": ["A-01"], "verdicts": ["differs"]},
                "thresholds": {"matrix_rows": ["A-02"], "verdicts": ["differs"]},
            }
        )
        report = hp.check(profile, rows, world.root)
        assert report.verdicts_the_declaration_has_wrong == (
            "criteria: A-01 declared differs, the matrix says equivalent",
        )

    def test_a_pinned_input_whose_bytes_moved(self, world) -> None:
        profile, rows = world()
        world.paths["index"].write_text(json.dumps({"sources": ["moved"]}), encoding="utf-8")
        report = hp.check(profile, rows, world.root)
        assert report.stale_inputs == ("source_index: authority/index.json",)

    def test_a_pinned_input_that_is_gone(self, world) -> None:
        profile, rows = world()
        world.paths["index"].unlink()
        report = hp.check(profile, rows, world.root)
        assert report.missing_inputs == ("source_index: authority/index.json",)

    def test_the_counterpart_profile_being_edited(self, world) -> None:
        """The ticket requires the other profile be left alone.

        This record pinned its bytes, so it is the record that reports them
        moving.
        """
        profile, rows = world()
        world.paths["counterpart"].write_text(
            json.dumps({"profile_id": "synthetic_current", "edited": True}), encoding="utf-8"
        )
        report = hp.check(profile, rows, world.root)
        assert report.counterpart_moved == ("profiles/current.json",)

    def test_a_status_more_certain_than_the_matrix(self, world) -> None:
        profile, rows = world(declared_status="Confirmed")
        report = hp.check(profile, rows, world.root, matrix_status="Inferred")
        assert report.status_the_matrix_cannot_carry
        assert "Confirmed" in report.status_the_matrix_cannot_carry[0]

    def test_a_status_less_certain_than_the_matrix_is_not_a_finding(self, world) -> None:
        """Understating is allowed; overstating is not."""
        profile, rows = world(declared_status="Assumed")
        report = hp.check(profile, rows, world.root, matrix_status="Inferred")
        assert not report.status_the_matrix_cannot_carry


# --------------------------------------------------------------------------- #
# The reading
# --------------------------------------------------------------------------- #


class TestTheReading:
    def test_it_names_every_element_and_its_rows(self, world) -> None:
        profile, rows = world()
        reading = hp.render(profile, rows)
        assert "`A-01`" in reading
        assert "`A-02`" in reading
        assert "criteria" in reading
        assert "thresholds" in reading

    def test_it_prints_the_matrix_verdict_and_not_the_declared_one(self, world) -> None:
        """A reading that echoed the declaration could not show a drift."""
        profile, rows = world(
            sourced={
                "criteria": {"matrix_rows": ["A-01"], "verdicts": ["differs"]},
                "thresholds": {"matrix_rows": ["A-02"], "verdicts": ["differs"]},
                "other": {"matrix_rows": ["C-01"], "verdicts": ["unresolved"]},
            },
            limitations=[],
        )
        reading = hp.render(profile, rows)
        criteria_row = next(l for l in reading.splitlines() if l.startswith("| criteria |"))
        assert "equivalent" in criteria_row

    def test_it_states_what_the_matrix_leaves_open(self, world) -> None:
        profile, rows = world()
        reading = hp.render(profile, rows)
        assert "What the matrix leaves open" in reading
        assert "evidenced by none" in reading

    def test_it_separates_what_neither_call_states(self, world) -> None:
        profile, rows = world()
        reading = hp.render(profile, rows)
        assert "What neither call states" in reading
        assert "rubric_set" in reading

    def test_it_names_the_rows_a_missing_row_would_not_resolve(self, world) -> None:
        profile, rows = world(
            sourced={
                "criteria": {"matrix_rows": ["Z-99"], "verdicts": ["equivalent"]},
                "thresholds": {"matrix_rows": ["A-02"], "verdicts": ["differs"]},
            }
        )
        reading = hp.render(profile, rows)
        assert "not in the matrix" in reading
