"""The authority source index and the rule-equivalence matrix reader (V09).

Synthetic worlds only. Every case builds a two-document index and a one-row
matrix in a temporary tree, so each rule is exercised on its own rather than
through the committed artifacts — which ``tests/test_msca_dn_authority_matrix.py``
reconciles separately.

The groups follow the acceptance criteria of ticket V09:

* **Loading** fails closed: an unknown vocabulary term, a missing field, a hash
  on an unobtained document, an obtained document with no hash, a citation with
  two locators or none.
* **The rule that matters.** A row marked equivalent or differs with no citation
  into an obtained historical source is reported. That is criterion 4: no row is
  marked equivalent because no difference was found.
* **Defaulting is declared as defaulting**, with the rule it affects named.
* **A citation does not overreach**: not beyond a record's measured scope
  (criterion 5), not a call-wide claim on evidence about one submission, not a
  Confirmed row on bytes nothing vouches for.
* **Criterion 3**: every row resolves to a pinned document and a located
  passage, or carries a recorded limitation.
* **The records themselves**: absent, edited, stale, and a stale index binding.
* **The command** writes two readings and exits non-zero on a finding.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import harness.commands.authority_matrix as cmd
from harness import authority_matrix as am

# --------------------------------------------------------------------------- #
# A synthetic world
# --------------------------------------------------------------------------- #

HISTORICAL_RECORD = {
    "result": {"weight": 50, "wording": "Criterion 1 weight 50.00%"},
    "rows": [1, 2, 3],
}
CURRENT_RECORD = {"weight": 50, "note": "the current configuration"}


def _index_entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "path": "records/historical.json",
        "class": "evaluation_output",
        "era": "historical",
        "authentication": "operator_supplied",
        "authentication_basis": "the record's own authored_by field names the operator",
        "role": "immutable_evidence",
        "states": "the historical evaluation's own record",
    }
    entry.update(overrides)
    return entry


def _write_world(root: Path) -> dict[str, Path]:
    """Two records on disk, plus the directory the declarations live in."""
    (root / "records").mkdir(parents=True, exist_ok=True)
    (root / "authority").mkdir(parents=True, exist_ok=True)
    (root / "records/historical.json").write_text(
        json.dumps(HISTORICAL_RECORD), encoding="utf-8"
    )
    (root / "records/current.json").write_text(json.dumps(CURRENT_RECORD), encoding="utf-8")
    (root / "records/notes.md").write_text(
        "A decision: five samples per criterion.\n", encoding="utf-8"
    )
    return {
        "index": root / "authority/index.json",
        "matrix": root / "authority/matrix.json",
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_doc(root: Path, sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if sources is None:
        sources = [
            _index_entry(sha256=_sha(root / "records/historical.json")),
            {
                "path": "records/current.json",
                "class": "derived_configuration",
                "era": "current",
                "authentication": "computed_only",
                "role": "tracked_input",
                "sha256": _sha(root / "records/current.json"),
                "states": "the current configuration",
            },
        ]
    return {
        "schema": am.SCHEMA_INDEX,
        "index_name": "synthetic_sources",
        "subject": "a synthetic instrument's two eras",
        "authored_on": "2026-10-12",
        "purpose": "exercise the reader",
        "historical_label": "before",
        "current_label": "after",
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": "Inferred",
        "supersedes": "nothing",
        "uncertainties": ["synthetic"],
        "written_by": "tests",
        "sources": sources,
    }


def _row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": "R-01",
        "area": "weights",
        "rule": "the criterion weight",
        "affects": "a number",
        "verdict": "equivalent",
        "settles": "as_applied_to_this_submission",
        "declared_status": "Inferred",
        "status_basis": "both records state it",
        "consequence": "the historical profile keeps the weight",
        "citations": [
            {
                "source": "records/historical.json",
                "field": "result/weight",
                "states": "the weight the historical evaluation applied",
            }
        ],
    }
    row.update(overrides)
    return row


def _matrix_doc(
    index_path: Path,
    index_sha: str,
    rows: list[dict[str, Any]] | None = None,
    required_areas: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": am.SCHEMA_MATRIX,
        "matrix_name": "synthetic_matrix",
        "subject": "a synthetic instrument",
        "authored_on": "2026-10-12",
        "purpose": "exercise the checker",
        "review_state": "agent_drafted_pending_operator_review",
        "declared_status": "Inferred",
        "supersedes": "nothing",
        "uncertainties": ["synthetic"],
        "required_areas": ["weights"] if required_areas is None else required_areas,
        "source_index": {"path": index_path, "sha256": index_sha},
        "written_by": "tests",
        "rows": [_row()] if rows is None else rows,
    }


@pytest.fixture
def world(tmp_path: Path):
    """A root with two records, and a writer for the two declarations."""
    paths = _write_world(tmp_path)

    def build(
        rows: list[dict[str, Any]] | None = None,
        sources: list[dict[str, Any]] | None = None,
        required_areas: list[str] | None = None,
    ) -> tuple[am.Matrix, am.SourceIndex]:
        index_doc = _index_doc(tmp_path, sources)
        paths["index"].write_text(json.dumps(index_doc), encoding="utf-8")
        matrix_doc = _matrix_doc(
            "authority/index.json", _sha(paths["index"]), rows, required_areas
        )
        paths["matrix"].write_text(json.dumps(matrix_doc), encoding="utf-8")
        index = am.load_source_index(paths["index"], repo_root=tmp_path)
        matrix = am.load_matrix(paths["matrix"], repo_root=tmp_path)
        return matrix, index

    build.root = tmp_path  # type: ignore[attr-defined]
    build.paths = paths  # type: ignore[attr-defined]
    return build


# --------------------------------------------------------------------------- #
# 1. Loading fails closed
# --------------------------------------------------------------------------- #


class TestLoading:
    def test_a_well_formed_world_loads_and_checks_green(self, world):
        matrix, index = world()
        assert am.check(matrix, index, world.root).green
        assert matrix.areas() == ("weights",)
        assert index.obtained() == index.sources

    def test_wrong_index_schema_refuses(self, world, tmp_path):
        world()
        doc = json.loads(world.paths["index"].read_text(encoding="utf-8"))
        doc["schema"] = "something_else/1"
        world.paths["index"].write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(am.AuthorityMatrixError, match="schema is"):
            am.load_source_index(world.paths["index"], repo_root=tmp_path)

    def test_wrong_matrix_schema_refuses(self, world, tmp_path):
        world()
        doc = json.loads(world.paths["matrix"].read_text(encoding="utf-8"))
        doc["schema"] = "something_else/1"
        world.paths["matrix"].write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(am.AuthorityMatrixError, match="schema is"):
            am.load_matrix(world.paths["matrix"], repo_root=tmp_path)

    @pytest.mark.parametrize(
        "field,value",
        [("class", "gossip"), ("era", "sometime"), ("authentication", "trust me"), ("role", "x")],
    )
    def test_unknown_source_vocabulary_refuses(self, world, field, value):
        entry = _index_entry(sha256="a" * 64, **{field: value})
        with pytest.raises(am.AuthorityMatrixError, match="expected one of"):
            world(sources=[entry])

    def test_a_hash_on_an_unobtained_document_refuses(self, world):
        entry = _index_entry(authentication="not_obtained", sha256="a" * 64)
        with pytest.raises(am.AuthorityMatrixError, match="not obtained, yet a sha256"):
            world(sources=[entry])

    def test_an_obtained_document_with_no_hash_refuses(self, world):
        with pytest.raises(am.AuthorityMatrixError, match="obtained, yet no sha256"):
            world(sources=[_index_entry()])

    def test_a_missing_index_field_refuses(self, world, tmp_path):
        world()
        doc = json.loads(world.paths["index"].read_text(encoding="utf-8"))
        del doc["historical_label"]
        world.paths["index"].write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(am.AuthorityMatrixError, match="historical_label"):
            am.load_source_index(world.paths["index"], repo_root=tmp_path)

    @pytest.mark.parametrize("field", ["verdict", "settles", "affects", "declared_status"])
    def test_unknown_row_vocabulary_refuses(self, world, field):
        with pytest.raises(am.AuthorityMatrixError, match="expected one of"):
            world(rows=[_row(**{field: "nonsense"})])

    def test_a_citation_with_two_locators_refuses(self, world):
        row = _row(
            citations=[
                {
                    "source": "records/historical.json",
                    "field": "result/weight",
                    "page": 2,
                    "states": "both at once",
                }
            ]
        )
        with pytest.raises(am.AuthorityMatrixError, match="both a page and a field"):
            world(rows=[row])

    def test_a_citation_with_no_locator_refuses(self, world):
        row = _row(citations=[{"source": "records/historical.json", "states": "nowhere"}])
        with pytest.raises(am.AuthorityMatrixError, match="neither a page nor a field"):
            world(rows=[row])

    def test_a_measurement_with_no_expectation_refuses(self, world):
        row = _row(
            measurements=[
                {
                    "id": "M1",
                    "claim": "the weight",
                    "record": "records/historical.json",
                    "field": "result/weight",
                }
            ]
        )
        with pytest.raises(am.AuthorityMatrixError, match="no expected value"):
            world(rows=[row])


# --------------------------------------------------------------------------- #
# 2. The rule that matters: equivalence needs historical evidence
# --------------------------------------------------------------------------- #


class TestEquivalenceNeedsHistoricalEvidence:
    @pytest.mark.parametrize("verdict", ["equivalent", "differs"])
    def test_a_relation_on_current_sources_alone_is_reported(self, world, verdict):
        row = _row(
            verdict=verdict,
            difference="the current record says 60" if verdict == "differs" else "",
            citations=[
                {
                    "source": "records/current.json",
                    "field": "weight",
                    "states": "the current configuration's weight",
                }
            ],
        )
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.equivalence_without_historical_evidence == ("R-01",)

    def test_defaulted_needs_no_historical_citation(self, world):
        row = _row(
            verdict="defaulted",
            citations=[
                {
                    "source": "records/current.json",
                    "field": "weight",
                    "states": "the current configuration's weight",
                }
            ],
            defaulting={
                "carried_from": "the current configuration",
                "affected_rule": "the weight applied to criterion 1",
                "risk": "a changed weight changes the total",
            },
        )
        matrix, index = world(rows=[row])
        assert am.check(matrix, index, world.root).green

    def test_a_citation_of_an_unobtained_document_does_not_count_as_historical(self, world):
        sources = [
            _index_entry(sha256=_sha(world.root / "records/historical.json")),
            {
                "path": "records/absent.pdf",
                "class": "work_programme",
                "era": "historical",
                "authentication": "not_obtained",
                "role": "immutable_evidence",
                "states": "the historical work programme, not obtained",
            },
        ]
        row = _row(
            citations=[
                {
                    "source": "records/absent.pdf",
                    "page": 3,
                    "quote": "something",
                    "states": "what the missing document would say",
                }
            ]
        )
        matrix, index = world(rows=[row], sources=sources)
        result = am.check(matrix, index, world.root)
        assert result.citations_of_unobtained_sources == ("R-01 citation 1: records/absent.pdf",)
        assert result.equivalence_without_historical_evidence == ("R-01",)


# --------------------------------------------------------------------------- #
# 3. Defaulting is declared as defaulting
# --------------------------------------------------------------------------- #


class TestDefaultingIsDeclared:
    def test_a_defaulted_row_with_no_defaulting_block_is_reported(self, world):
        row = _row(
            verdict="defaulted",
            citations=[
                {
                    "source": "records/current.json",
                    "field": "weight",
                    "states": "the current weight",
                }
            ],
        )
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.defaulting_without_an_affected_rule == ("R-01: no defaulting block",)

    def test_a_defaulted_row_that_names_no_affected_rule_is_reported(self, world):
        row = _row(
            verdict="defaulted",
            citations=[
                {
                    "source": "records/current.json",
                    "field": "weight",
                    "states": "the current weight",
                }
            ],
            defaulting={"carried_from": "the current configuration", "risk": "the total moves"},
        )
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.defaulting_without_an_affected_rule == ("R-01: no affected rule named",)

    def test_a_defaulting_block_with_no_risk_refuses_at_load(self, world):
        row = _row(
            verdict="defaulted",
            defaulting={"carried_from": "x", "affected_rule": "y"},
        )
        with pytest.raises(am.AuthorityMatrixError, match="risk"):
            world(rows=[row])


# --------------------------------------------------------------------------- #
# 4. A citation does not overreach
# --------------------------------------------------------------------------- #


class TestOverreach:
    def _restricted_sources(self, root: Path) -> list[dict[str, Any]]:
        return [
            _index_entry(sha256=_sha(root / "records/historical.json")),
            {
                "path": "records/current.json",
                "class": "derived_configuration",
                "era": "current",
                "authentication": "computed_only",
                "role": "tracked_input",
                "sha256": _sha(root / "records/current.json"),
                "states": "the current configuration, with an equivalence record inside it",
                "scope_restrictions": [
                    {
                        "field_prefix": "note",
                        "settles_areas": ["section_mapping"],
                        "measured": "structure only",
                    }
                ],
            },
        ]

    def test_a_restricted_passage_cited_from_another_area_is_reported(self, world):
        row = _row(
            citations=[
                {
                    "source": "records/historical.json",
                    "field": "result/weight",
                    "states": "the historical weight",
                },
                {
                    "source": "records/current.json",
                    "field": "note",
                    "states": "read as settling the weight",
                },
            ]
        )
        matrix, index = world(rows=[row], sources=self._restricted_sources(world.root))
        result = am.check(matrix, index, world.root)
        assert len(result.citations_outside_their_declared_scope) == 1
        assert "cited from area weights" in result.citations_outside_their_declared_scope[0]

    def test_the_same_passage_cited_from_its_own_area_is_accepted(self, world):
        row = _row(
            area="section_mapping",
            citations=[
                {
                    "source": "records/historical.json",
                    "field": "result/weight",
                    "states": "the historical side",
                },
                {
                    "source": "records/current.json",
                    "field": "note",
                    "states": "within the structure it measured",
                },
            ],
        )
        matrix, index = world(
            rows=[row],
            sources=self._restricted_sources(world.root),
            required_areas=["section_mapping"],
        )
        assert am.check(matrix, index, world.root).green

    def test_a_call_wide_claim_on_submission_evidence_alone_is_reported(self, world):
        row = _row(settles="call_wide")
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.call_wide_claims_on_submission_evidence == ("R-01",)
        # The historical citation is real, so the equivalence rule is satisfied.
        assert not result.equivalence_without_historical_evidence

    def test_a_call_wide_claim_on_a_historical_call_document_is_accepted(self, world):
        sources = [
            _index_entry(
                sha256=_sha(world.root / "records/historical.json"),
                **{"class": "work_programme"},
            ),
            {
                "path": "records/current.json",
                "class": "derived_configuration",
                "era": "current",
                "authentication": "computed_only",
                "role": "tracked_input",
                "sha256": _sha(world.root / "records/current.json"),
                "states": "the current configuration",
            },
        ]
        matrix, index = world(rows=[_row(settles="call_wide")], sources=sources)
        assert am.check(matrix, index, world.root).green

    def test_a_confirmed_row_on_unvouched_bytes_is_reported(self, world):
        matrix, index = world(rows=[_row(declared_status="Confirmed")])
        result = am.check(matrix, index, world.root)
        assert result.confirmed_without_an_authenticated_source == ("R-01",)

    def test_a_confirmed_row_on_an_issuer_hash_is_accepted(self, world):
        sources = [
            _index_entry(
                authentication="issuer_hash_confirmed",
                sha256=_sha(world.root / "records/historical.json"),
            ),
        ]
        matrix, index = world(rows=[_row(declared_status="Confirmed")], sources=sources)
        assert am.check(matrix, index, world.root).green


# --------------------------------------------------------------------------- #
# 5. Every row resolves, or records its limitation
# --------------------------------------------------------------------------- #


class TestRowsResolve:
    def test_a_citation_of_an_undeclared_source_is_reported(self, world):
        row = _row(
            citations=[
                {"source": "records/nowhere.json", "field": "x", "states": "unbound"},
            ]
        )
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.citations_of_undeclared_sources == (
            "R-01 citation 1: records/nowhere.json",
        )

    def test_a_field_that_does_not_resolve_is_reported(self, world):
        row = _row(
            citations=[
                {
                    "source": "records/historical.json",
                    "field": "result/absent",
                    "states": "nowhere in the record",
                }
            ]
        )
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.citations_that_do_not_resolve == (
            "R-01 citation 1: result/absent does not resolve",
        )

    def test_a_passage_missing_from_a_non_json_record_is_reported(self, world):
        sources = _index_doc(world.root)["sources"] + [
            {
                "path": "records/notes.md",
                "class": "repository_decision",
                "era": "cross_era",
                "authentication": "computed_only",
                "role": "tracked_input",
                "sha256": _sha(world.root / "records/notes.md"),
                "states": "a decision record in prose",
            }
        ]
        row = _row(
            citations=[
                {
                    "source": "records/historical.json",
                    "field": "result/weight",
                    "states": "the historical weight",
                },
                {
                    "source": "records/notes.md",
                    "field": "seven samples per criterion",
                    "states": "a decision that was reworded",
                },
            ]
        )
        matrix, index = world(rows=[row], sources=sources)
        result = am.check(matrix, index, world.root)
        assert result.citations_that_do_not_resolve == (
            "R-01 citation 2: seven samples per criterion is not in the record",
        )

    def test_a_passage_present_in_a_non_json_record_resolves(self, world):
        sources = _index_doc(world.root)["sources"] + [
            {
                "path": "records/notes.md",
                "class": "repository_decision",
                "era": "cross_era",
                "authentication": "computed_only",
                "role": "tracked_input",
                "sha256": _sha(world.root / "records/notes.md"),
                "states": "a decision record in prose",
            }
        ]
        row = _row(
            citations=[
                {
                    "source": "records/historical.json",
                    "field": "result/weight",
                    "states": "the historical weight",
                },
                {
                    "source": "records/notes.md",
                    "field": "five samples per criterion",
                    "states": "the decision as written",
                },
            ]
        )
        matrix, index = world(rows=[row], sources=sources)
        assert am.check(matrix, index, world.root).green

    def test_a_page_beyond_the_pinned_document_is_reported(self, world):
        sources = [
            {
                "path": "records/historical.json",
                "class": "instrument_application_form",
                "era": "historical",
                "authentication": "computed_only",
                "role": "immutable_evidence",
                "sha256": _sha(world.root / "records/historical.json"),
                "pages": 4,
                "states": "a four-page form",
            }
        ]
        row = _row(
            citations=[
                {
                    "source": "records/historical.json",
                    "page": 9,
                    "quote": "a passage",
                    "states": "past the end",
                }
            ]
        )
        matrix, index = world(rows=[row], sources=sources)
        result = am.check(matrix, index, world.root)
        assert len(result.citations_that_do_not_resolve) == 1
        assert "page 9" in result.citations_that_do_not_resolve[0]

    def test_a_page_citation_with_no_quote_is_reported(self, world):
        sources = [
            {
                "path": "records/historical.json",
                "class": "instrument_application_form",
                "era": "historical",
                "authentication": "computed_only",
                "role": "immutable_evidence",
                "sha256": _sha(world.root / "records/historical.json"),
                "pages": 4,
                "states": "a four-page form",
            }
        ]
        row = _row(
            citations=[
                {"source": "records/historical.json", "page": 2, "states": "a page, no passage"}
            ]
        )
        matrix, index = world(rows=[row], sources=sources)
        result = am.check(matrix, index, world.root)
        assert result.document_citations_without_a_quote == ("R-01 citation 1",)

    def test_a_row_with_no_citation_is_reported(self, world):
        matrix, index = world(rows=[_row(citations=[])])
        result = am.check(matrix, index, world.root)
        assert result.rows_without_a_citation == ("R-01",)

    def test_an_era_neutral_row_may_cite_nothing(self, world):
        row = _row(
            verdict="era_neutral",
            citations=[],
            why_era_neutral="the rule is the harness's own and no call document states it",
        )
        matrix, index = world(rows=[row])
        assert am.check(matrix, index, world.root).green

    def test_an_unresolved_row_needs_a_limitation(self, world):
        row = _row(verdict="unresolved")
        matrix, index = world(rows=[row])
        assert am.check(matrix, index, world.root).unresolved_without_a_limitation == ("R-01",)

    def test_a_differs_row_needs_a_difference(self, world):
        row = _row(verdict="differs")
        matrix, index = world(rows=[row])
        assert am.check(matrix, index, world.root).differences_not_described == ("R-01",)

    def test_an_era_neutral_row_needs_a_justification(self, world):
        row = _row(verdict="era_neutral", citations=[])
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.era_neutral_without_a_justification == ("R-01",)

    @pytest.mark.parametrize("field", ["rule", "status_basis", "consequence"])
    def test_an_empty_row_field_is_reported(self, world, field):
        matrix, index = world(rows=[_row(**{field: "  "})])
        result = am.check(matrix, index, world.root)
        assert result.rows_missing_field == (f"R-01: {field}",)

    def test_a_duplicate_row_id_is_reported(self, world):
        matrix, index = world(rows=[_row(), _row(area="weights")])
        assert am.check(matrix, index, world.root).duplicate_row_ids == ("R-01",)

    def test_a_row_naming_an_undeclared_future_source_is_reported(self, world):
        row = _row(
            verdict="unresolved",
            limitation="no source states it",
            would_be_settled_by=["records/nobody_declared_this.pdf"],
        )
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.rows_naming_an_undeclared_future_source == (
            "R-01: records/nobody_declared_this.pdf",
        )

    def test_a_row_naming_a_declared_absent_source_is_accepted(self, world):
        sources = [
            _index_entry(sha256=_sha(world.root / "records/historical.json")),
            {
                "path": "records/absent.pdf",
                "class": "work_programme",
                "era": "historical",
                "authentication": "not_obtained",
                "role": "immutable_evidence",
                "states": "the historical work programme",
                "would_settle": ["R-01"],
            },
        ]
        row = _row(
            verdict="unresolved",
            limitation="no source states it",
            would_be_settled_by=["records/absent.pdf"],
        )
        matrix, index = world(rows=[row], sources=sources)
        assert am.check(matrix, index, world.root).green

    def test_a_required_area_no_row_covers_is_reported(self, world):
        matrix, index = world(required_areas=["weights", "thresholds"])
        result = am.check(matrix, index, world.root)
        assert result.areas_required_but_not_covered == ("thresholds",)


# --------------------------------------------------------------------------- #
# 6. Measurements
# --------------------------------------------------------------------------- #


class TestMeasurements:
    def test_a_measurement_the_record_contradicts_is_reported(self, world):
        row = _row(
            measurements=[
                {
                    "id": "M1",
                    "claim": "the weight",
                    "record": "records/historical.json",
                    "field": "result/weight",
                    "expected": 30,
                }
            ]
        )
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.failed_measurements == ("R-01/M1: result/weight is 50, expected 30",)

    def test_a_length_measurement_is_checked(self, world):
        row = _row(
            measurements=[
                {
                    "id": "M1",
                    "claim": "three rows",
                    "record": "records/historical.json",
                    "field": "rows",
                    "expected_length": 3,
                }
            ]
        )
        matrix, index = world(rows=[row])
        assert am.check(matrix, index, world.root).green

    def test_a_measurement_of_an_undeclared_source_is_reported(self, world):
        row = _row(
            measurements=[
                {
                    "id": "M1",
                    "claim": "nowhere",
                    "record": "records/nowhere.json",
                    "field": "x",
                    "expected": 1,
                }
            ]
        )
        matrix, index = world(rows=[row])
        result = am.check(matrix, index, world.root)
        assert result.measurements_of_undeclared_sources == ("R-01/M1: records/nowhere.json",)


# --------------------------------------------------------------------------- #
# 7. The records themselves
# --------------------------------------------------------------------------- #


class TestBoundRecords:
    def test_an_absent_source_is_reported_once(self, world):
        matrix, index = world()
        (world.root / "records/historical.json").unlink()
        result = am.check(matrix, index, world.root)
        assert result.missing_sources == ("records/historical.json",)
        # The citation into it is not reported a second time as unresolved.
        assert not result.citations_that_do_not_resolve

    def test_an_edited_immutable_source_is_reported(self, world):
        matrix, index = world()
        (world.root / "records/historical.json").write_text(
            json.dumps({"result": {"weight": 30}, "rows": []}), encoding="utf-8"
        )
        result = am.check(matrix, index, world.root)
        assert result.edited_immutable_sources == ("records/historical.json",)
        assert not result.stale_tracked_inputs

    def test_a_moved_tracked_input_is_reported_separately(self, world):
        matrix, index = world()
        (world.root / "records/current.json").write_text(
            json.dumps({"weight": 50, "note": "reworded"}), encoding="utf-8"
        )
        result = am.check(matrix, index, world.root)
        assert result.stale_tracked_inputs == ("records/current.json",)
        assert not result.edited_immutable_sources

    def test_a_moved_index_makes_the_matrix_stale(self, world):
        matrix, index = world()
        doc = json.loads(world.paths["index"].read_text(encoding="utf-8"))
        doc["purpose"] = "reworded"
        world.paths["index"].write_text(json.dumps(doc), encoding="utf-8")
        reread = am.load_source_index(world.paths["index"], repo_root=world.root)
        result = am.check(matrix, reread, world.root)
        assert len(result.stale_source_index) == 1
        assert "bytes differ" in result.stale_source_index[0]

    def test_a_page_count_on_an_unobtained_document_is_reported(self, world):
        sources = [
            _index_entry(sha256=_sha(world.root / "records/historical.json")),
            {
                "path": "records/absent.pdf",
                "class": "work_programme",
                "era": "historical",
                "authentication": "not_obtained",
                "role": "immutable_evidence",
                "pages": 112,
                "states": "an absent document with a page count",
            },
        ]
        matrix, index = world(sources=sources)
        result = am.check(matrix, index, world.root)
        assert result.unobtained_sources_declared_with_pages == ("records/absent.pdf: pages 112",)

    def test_a_vouched_authentication_without_a_basis_is_reported(self, world):
        """A rank above computed_only has to say where the vouching is recorded."""
        entry = _index_entry(sha256=_sha(world.root / "records/historical.json"))
        entry.pop("authentication_basis")
        matrix, index = world(sources=[entry])
        result = am.check(matrix, index, world.root)
        assert result.authentications_claimed_without_a_basis == (
            "records/historical.json: operator_supplied",
        )

    def test_a_blank_basis_counts_as_none(self, world):
        entry = _index_entry(
            sha256=_sha(world.root / "records/historical.json"), authentication_basis="   "
        )
        matrix, index = world(sources=[entry])
        result = am.check(matrix, index, world.root)
        assert result.authentications_claimed_without_a_basis == (
            "records/historical.json: operator_supplied",
        )

    def test_computed_only_needs_no_basis(self, world):
        """It claims nothing, so there is nothing to record."""
        entry = _index_entry(
            sha256=_sha(world.root / "records/historical.json"), authentication="computed_only"
        )
        entry.pop("authentication_basis")
        matrix, index = world(sources=[entry], rows=[_row(declared_status="Inferred")])
        assert am.check(matrix, index, world.root).green


# --------------------------------------------------------------------------- #
# 8. Rendering and the command
# --------------------------------------------------------------------------- #


class TestTheThreeAxes:
    """Byte integrity, source authenticity and historical applicability.

    They are separate questions, and the reader's job is to stop one answer
    standing in for another.
    """

    def test_an_entry_declaring_nothing_reads_as_origin_unrecorded(self, world):
        """What a version-1 index means, stated once here.

        Older indexes declare none of these fields. Their entries must read as
        a held file with no recorded origin, never as a corroborated one.
        """
        _, index = world()
        for source in index.obtained():
            assert source.source_authenticity == "unrecorded"
            assert source.historical_applicability == "not_applicable"
            assert source.provenance is None
            assert not source.origin_recorded
            assert source.applicability_conclusive

    def test_a_corroborating_copy_with_other_bytes_is_refused_at_load(self, world):
        sources = [
            _index_entry(
                sha256=_sha(world.root / "records/historical.json"),
                source_authenticity="independently_corroborated",
                source_authenticity_basis="a second host served the same bytes",
                provenance={
                    "official_url": "https://example.invalid/a.json",
                    "retrieved_on": "2026-10-13",
                    "corroborating_copies": [
                        {"url": "https://example.invalid/mirror/a.json", "sha256": "0" * 64}
                    ],
                },
            )
        ]
        with pytest.raises(am.AuthorityMatrixError, match="corroborates nothing"):
            world(sources=sources)

    def test_an_authenticity_with_no_basis_is_reported(self, world):
        sources = [
            _index_entry(
                sha256=_sha(world.root / "records/historical.json"),
                source_authenticity="retrieved_from_official_url",
                provenance={
                    "official_url": "https://example.invalid/a.json",
                    "retrieved_on": "2026-10-13",
                },
            )
        ]
        matrix, index = world(sources=sources)
        report = am.check(matrix, index, world.root)
        assert report.authenticities_claimed_without_a_basis
        assert not report.green

    def test_an_applicability_with_no_basis_is_reported(self, world):
        sources = [
            _index_entry(
                sha256=_sha(world.root / "records/historical.json"),
                historical_applicability="in_force_confirmed",
            )
        ]
        matrix, index = world(sources=sources)
        report = am.check(matrix, index, world.root)
        assert report.applicabilities_claimed_without_a_basis

    def test_a_rank_its_provenance_does_not_carry_is_reported(self, world):
        """The basis says an act happened; the record has to carry it.

        Corroboration with neither a capture nor a copy recorded is a sentence
        about an act with nothing beside it.
        """
        sources = [
            _index_entry(
                sha256=_sha(world.root / "records/historical.json"),
                source_authenticity="independently_corroborated",
                source_authenticity_basis="two hosts agreed",
                provenance={"official_url": "https://example.invalid/a.json"},
            )
        ]
        matrix, index = world(sources=sources)
        report = am.check(matrix, index, world.root)
        assert report.ranks_unsupported_by_their_provenance
        assert "a second capture or a corroborating copy" in (
            report.ranks_unsupported_by_their_provenance[0]
        )

    def test_a_confirmed_row_on_a_bracketed_source_is_reported(self, world):
        """The finding the third axis exists for.

        The bytes can be fixed and their origin settled while the document's
        place in a closed call is not. A confirmation resting there confirms
        a wording, not a rule that governed.
        """
        sources = [
            _index_entry(
                sha256=_sha(world.root / "records/historical.json"),
                authentication="issuer_hash_confirmed",
                authentication_basis="an expected hash from the issuing body matched",
                source_authenticity="retrieved_from_web_archive",
                source_authenticity_basis="read from an archive of the published address",
                historical_applicability="bracketed_not_conclusive",
                historical_applicability_basis="two captures surround the window",
                provenance={
                    "official_url": "https://example.invalid/a.json",
                    "retrieved_on": "2026-10-13",
                    "archive_captures": [
                        {"url": "https://example.invalid/t1/a.json", "captured_on": "2025-06-19"}
                    ],
                },
            )
        ]
        matrix, index = world(rows=[_row(declared_status="Confirmed")], sources=sources)
        report = am.check(matrix, index, world.root)
        # Byte integrity and origin are both settled, so the older finding is
        # silent and only the applicability one fires.
        assert not report.confirmed_without_an_authenticated_source
        assert report.confirmed_on_inconclusive_applicability

    def test_an_absence_claiming_an_origin_is_refused_at_load(self, world):
        sources = [
            {
                "path": "records/absent.pdf",
                "class": "work_programme",
                "era": "historical",
                "authentication": "not_obtained",
                "source_authenticity": "retrieved_from_official_url",
                "role": "immutable_evidence",
                "states": "a document nobody has",
            }
        ]
        with pytest.raises(am.AuthorityMatrixError, match="claims source_authenticity"):
            world(sources=sources)


class TestRendering:
    def test_both_readings_name_what_the_verdicts_mean(self, world):
        matrix, index = world()
        reading = am.render_matrix(matrix, index)
        assert "No verdict means *no difference was found*" in reading
        assert "**not** equivalence" in reading
        index_reading = am.render_index(index)
        # The reading is hard-wrapped, so the sentence is matched after the
        # wrapping is collapsed. Asserting on the wrapped text makes the test
        # fail when a word earlier in the paragraph changes length.
        assert "may not declare Confirmed" in " ".join(index_reading.split())

    def test_the_index_reading_lists_what_is_missing(self, world):
        sources = [
            _index_entry(sha256=_sha(world.root / "records/historical.json")),
            {
                "path": "records/absent.pdf",
                "class": "work_programme",
                "era": "historical",
                "authentication": "not_obtained",
                "role": "immutable_evidence",
                "states": "the historical work programme",
                "would_settle": ["R-01"],
            },
        ]
        _, index = world(sources=sources)
        reading = am.render_index(index)
        assert "## What is not obtained" in reading
        assert "the historical work programme" in reading

    def test_an_undeclared_citation_renders_as_undeclared(self, world):
        row = _row(
            citations=[{"source": "records/nowhere.json", "field": "x", "states": "unbound"}]
        )
        matrix, index = world(rows=[row])
        assert "UNDECLARED" in am.render_matrix(matrix, index)


class TestCommand:
    def test_a_green_world_writes_two_readings_and_exits_zero(self, world, capsys):
        world()
        code = cmd.main(
            ["--matrix", "authority/matrix.json", "--repo-root", str(world.root)]
        )
        assert code == 0
        assert (world.root / "authority/matrix.md").is_file()
        assert (world.root / "authority/index.md").is_file()
        assert "matrix check: green" in capsys.readouterr().out

    def test_check_exits_one_when_a_reading_would_change(self, world, capsys):
        world()
        code = cmd.main(
            ["--matrix", "authority/matrix.json", "--repo-root", str(world.root), "--check"]
        )
        assert code == 1
        assert not (world.root / "authority/matrix.md").exists()
        assert "would change" in capsys.readouterr().out

    def test_check_exits_zero_once_the_readings_are_written(self, world):
        world()
        argv = ["--matrix", "authority/matrix.json", "--repo-root", str(world.root)]
        assert cmd.main(argv) == 0
        assert cmd.main(argv + ["--check"]) == 0

    def test_no_render_leaves_the_readings_alone(self, world):
        world()
        code = cmd.main(
            [
                "--matrix",
                "authority/matrix.json",
                "--repo-root",
                str(world.root),
                "--no-render",
            ]
        )
        assert code == 0
        assert not (world.root / "authority/matrix.md").exists()

    def test_a_finding_exits_one(self, world, capsys):
        world(rows=[_row(declared_status="Confirmed")])
        code = cmd.main(["--matrix", "authority/matrix.json", "--repo-root", str(world.root)])
        assert code == 1
        out = capsys.readouterr().out
        assert "matrix check: FAILED" in out
        assert "CONFIRMED WITHOUT AN AUTHENTICATED SOURCE" in out

    def test_an_unreadable_declaration_is_refused(self, world, capsys):
        world()
        world.paths["matrix"].write_text("{not json", encoding="utf-8")
        code = cmd.main(["--matrix", "authority/matrix.json", "--repo-root", str(world.root)])
        assert code == 1
        assert "refused" in capsys.readouterr().err
