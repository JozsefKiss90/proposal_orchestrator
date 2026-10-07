"""
The operator review table over a written ESR comparison (ticket R02).

Four groups:

* The notes file — the declared half: vocabulary, coverage, and the rule that
  a row which is not "agreed, retain" must carry a question for the operator.
  A notes file may never declare its own approval.
* Binding and resolution: every input the comparison names is re-hashed, and
  every reference it recorded is resolved again against the artifact it names.
  An artifact that moved under the report refuses it; nothing is written.
* The rendered artifacts: criticisms counted apart from strengths, the
  decisions list, quotes out of table cells, determinism, and no overwrite.
* The committed MSCA-DN artifacts: the review notes in the repository cover
  the ESR record's 29 observations exactly once, every reference still
  resolves, and re-rendering reproduces the committed report.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import harness.commands.blind_assessment as cmd
import harness.esr_comparison as ec
import harness.operator_review as orv
from harness.rubrics import load_profile_bundle
from runner.paths import find_repo_root
from tests.harness.test_blind_baseline import (
    _write_json,
    bundle,  # noqa: F401 - fixture
    world,  # noqa: F401 - fixture
)
from tests.harness.test_blind_leakage import FROZEN
from tests.harness.test_esr_comparison import (  # noqa: F401 - fixtures
    DN_AUDITS,
    DN_BASELINE,
    DN_CANDIDATES,
    DN_DISPOSITIONS,
    DN_ESR,
    DN_PROFILE,
    DN_REGISTER,
    _compare,
    frozen_world,
    inputs,
)

REPO = find_repo_root()
DN_COMPARISON = REPO / "docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json"
DN_NOTES = REPO / "docs/tier4_orchestration_state/msca_dn/esr/review_notes_f60ae6e0a2a1.json"
DN_REVIEWS = REPO / "docs/tier4_orchestration_state/msca_dn/reviews"

_GENERATED = re.compile(r"^Generated: .*$", re.MULTILINE)


# --------------------------------------------------------------------------- #
# The synthetic world: a written comparison and notes for its four rows
# --------------------------------------------------------------------------- #


def _notes(comparison_sha: str) -> dict:
    """Notes for the four synthetic observations: one of each shape."""
    return {
        "record_type": orv.REVIEW_NOTES_RECORD_TYPE,
        "schema_version": orv.REVIEW_SCHEMA_VERSION,
        "advisory": True,
        "blocking": False,
        "comparison": "comparisons/comparison.json",
        "comparison_sha256": comparison_sha,
        "declared_by": "test reviewer",
        "declared_on": "2026-10-07",
        "review_state": orv.REVIEW_STATE_PENDING,
        "rows": [
            {
                "observation_id": "OBS-1",
                "semantic_agreement": orv.AGREEMENT_AGREED,
                "agreement_basis": "The blind shortcoming names objective two.",
                "declared_status": "Inferred",
                "esr_complaint": orv.COMPLAINT_INADEQUATE,
                "recommendation": orv.RECOMMENDATION_RETAIN,
                "recommended_disposition": "independently_detected",
            },
            {
                "observation_id": "OBS-2",
                "semantic_agreement": orv.AGREEMENT_NOT_APPLICABLE,
                "agreement_basis": "No finding names the point, so there is nothing to compare.",
                "declared_status": "Inferred",
                "esr_complaint": orv.COMPLAINT_ABSENT,
                "uncertainty": "Whether the start month survived the copy is declared, not measured.",
                "recommendation": orv.RECOMMENDATION_AFTER_DECLARATION,
                "recommended_disposition": "not_detected_despite_sufficient_preserved_evidence",
                "operator_decision": "Confirm the start month is preserved before the miss is counted.",
            },
            {
                "observation_id": "OBS-3",
                "semantic_agreement": orv.AGREEMENT_DISPUTED,
                "agreement_basis": "The blind strength praises the table, the ESR praises the definitions.",
                "declared_status": "Assumed",
                "esr_complaint": orv.COMPLAINT_NOT_APPLICABLE,
                "recommendation": orv.RECOMMENDATION_R03,
                "recommended_disposition": "independently_detected",
                "operator_decision": "Decide whether a praised table stands for praised definitions.",
            },
            {
                "observation_id": "OBS-4",
                "semantic_agreement": orv.AGREEMENT_UNRESOLVED,
                "agreement_basis": "The removed figure cannot be read from this copy.",
                "declared_status": "Assumed",
                "esr_complaint": orv.COMPLAINT_OTHER,
                "recommendation": orv.RECOMMENDATION_AFTER_PRIVATE_NETWORK,
                "recommended_disposition": "not_assessable_from_this_copy",
                "operator_decision": "Confirm the figure existed in the submission.",
            },
        ],
    }


@pytest.fixture
def written(inputs):  # noqa: F811 - fixture
    """A comparison written in the synthetic world, with notes bound to it."""
    code, out = _compare(inputs)
    assert code == 0
    comparison = next(out.glob("comparison_*.json"))
    notes = _write_json(
        inputs["world"] / "docs" / "review" / "notes.json",
        _notes(orv.file_sha256(comparison)),
    )
    return {**inputs, "comparison": comparison, "notes": notes, "reviews": out.parent / "reviews"}


def _review(written, *, out: Path | None = None) -> tuple[int, Path]:
    reviews = out or written["reviews"]
    code = cmd.main(
        [
            "review",
            "--comparison", str(written["comparison"]),
            "--notes", str(written["notes"]),
            "--repo-root", str(written["world"]),
            "--profile", str(written["bundle"].profile.source_path),
            "--out-dir", str(reviews),
        ],
        clock=lambda: FROZEN,
    )
    return code, reviews


def _edit(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    _write_json(path, data)


def _rebind(written) -> None:
    """Re-bind the notes to the comparison's current bytes."""
    _edit(
        written["notes"],
        lambda d: d.__setitem__("comparison_sha256", orv.file_sha256(written["comparison"])),
    )


def _report_text(written) -> str:
    code, reviews = _review(written)
    assert code == 0
    return next(reviews.glob("operator_review_*.md")).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# The notes
# --------------------------------------------------------------------------- #


class TestTheNotes:
    def test_a_file_that_is_not_a_notes_record_is_refused(self, tmp_path):
        p = _write_json(tmp_path / "n.json", {"record_type": "something_else"})
        with pytest.raises(orv.OperatorReviewError, match="esr_review_notes"):
            orv.load_review_notes(p)

    def test_invalid_json_is_refused_by_name(self, tmp_path):
        p = tmp_path / "n.json"
        p.write_text("{not json", encoding="utf-8")
        with pytest.raises(orv.OperatorReviewError, match="not valid JSON"):
            orv.load_review_notes(p)

    @pytest.mark.parametrize(
        "key",
        [
            "schema_version",
            "comparison",
            "comparison_sha256",
            "declared_by",
            "declared_on",
            "review_state",
        ],
    )
    def test_a_missing_header_field_is_refused(self, tmp_path, key):
        data = _notes("0" * 64)
        del data[key]
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match=key):
            orv.load_review_notes(p)

    def test_a_notes_file_may_not_declare_its_own_approval(self, tmp_path):
        data = _notes("0" * 64)
        data["review_state"] = "operator_approved"
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match="never records operator approval"):
            orv.load_review_notes(p)

    @pytest.mark.parametrize(
        "field,value", [("advisory", False), ("blocking", True), ("advisory", None)]
    )
    def test_notes_that_do_not_carry_the_advisory_invariant_are_refused(
        self, tmp_path, field, value
    ):
        """Every harness record states it gates nothing; this one is no exception."""
        data = _notes("0" * 64)
        if value is None:
            del data[field]
        else:
            data[field] = value
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match="advisory=true and blocking=false"):
            orv.load_review_notes(p)

    def test_notes_of_an_unknown_schema_version_are_refused(self, tmp_path):
        data = _notes("0" * 64)
        data["schema_version"] = "2.0"
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match="schema version"):
            orv.load_review_notes(p)

    def test_an_observation_reviewed_twice_is_refused(self, tmp_path):
        data = _notes("0" * 64)
        data["rows"].append(dict(data["rows"][0]))
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match="OBS-1 is reviewed twice"):
            orv.load_review_notes(p)

    @pytest.mark.parametrize(
        "key,value",
        [
            ("semantic_agreement", "mostly"),
            ("esr_complaint", "too_short"),
            ("recommendation", "ignore"),
            ("declared_status", "Probable"),
            ("recommended_disposition", "fixed"),
        ],
    )
    def test_a_value_outside_the_vocabulary_is_refused(self, tmp_path, key, value):
        data = _notes("0" * 64)
        data["rows"][0][key] = value
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match=key):
            orv.load_review_notes(p)

    def test_an_empty_basis_is_refused(self, tmp_path):
        data = _notes("0" * 64)
        data["rows"][0]["agreement_basis"] = "   "
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match="agreement_basis"):
            orv.load_review_notes(p)

    def test_a_basis_that_is_not_text_is_refused(self, tmp_path):
        data = _notes("0" * 64)
        data["rows"][0]["agreement_basis"] = ["a", "list"]
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match="must be text"):
            orv.load_review_notes(p)

    def test_a_disputed_row_needs_a_question_for_the_operator(self, tmp_path):
        data = _notes("0" * 64)
        del data["rows"][2]["operator_decision"]
        p = _write_json(tmp_path / "n.json", data)
        with pytest.raises(orv.OperatorReviewError, match="needs an 'operator_decision'"):
            orv.load_review_notes(p)

    def test_an_agreed_and_retained_row_needs_no_question(self, tmp_path):
        p = _write_json(tmp_path / "n.json", _notes("0" * 64))
        notes = orv.load_review_notes(p)
        assert notes.rows["OBS-1"].get("operator_decision") is None
        assert set(notes.rows) == {"OBS-1", "OBS-2", "OBS-3", "OBS-4"}


# --------------------------------------------------------------------------- #
# Binding: nothing is taken on the comparison's word
# --------------------------------------------------------------------------- #


class TestBinding:
    def test_notes_bound_to_another_comparison_are_refused(self, written, capsys):
        _edit(written["notes"], lambda d: d.__setitem__("comparison_sha256", "f" * 64))
        code, reviews = _review(written)
        assert code == 2
        assert "bound to comparison" in capsys.readouterr().err
        assert not list(reviews.glob("*.md")) if reviews.is_dir() else True

    def test_an_esr_record_edited_after_the_comparison_is_refused(self, written, capsys):
        _edit(written["esr"], lambda d: d["observations"][0].__setitem__("text", "Reworded."))
        code, _reviews = _review(written)
        assert code == 2
        assert "the ESR record" in capsys.readouterr().err

    def test_a_dispositions_file_edited_after_the_comparison_is_refused(self, written, capsys):
        _edit(written["dispositions"], lambda d: d.__setitem__("declared_on", "2026-10-08"))
        code, _reviews = _review(written)
        assert code == 2
        assert "the dispositions" in capsys.readouterr().err

    def test_a_register_edited_after_the_comparison_is_refused(self, written, capsys):
        _edit(written["register"], lambda d: d["derived"].__setitem__("figures", {"images_on_any_page": 3}))
        code, _reviews = _review(written)
        assert code == 2
        assert "the fidelity register" in capsys.readouterr().err

    def test_a_candidate_that_changed_is_refused(self, written, capsys):
        section = next(Path(written["candidate"]).glob("*.json"))
        data = json.loads(section.read_text(encoding="utf-8"))
        data["sub_sections"][0]["content"] += " An added sentence."
        _write_json(section, data)
        code, _reviews = _review(written)
        assert code == 2
        assert "hashes to" in capsys.readouterr().err

    def test_the_inventory_names_every_input_with_its_hash(self, written):
        bundle_ = written["bundle"]
        resolved = orv.resolve_inputs(
            written["comparison"], repo_root=written["world"], profile=bundle_.profile
        )
        roles = [item.role for item in resolved.inventory]
        assert roles[:2] == ["comparison report", "ESR record"]
        for role in ("dispositions", "frozen blind baseline", "candidate", "fidelity register"):
            assert role in roles
        assert all(item.sha256 for item in resolved.inventory)


# --------------------------------------------------------------------------- #
# Coverage and resolution
# --------------------------------------------------------------------------- #


class TestCoverageAndResolution:
    def test_an_observation_without_a_note_is_refused(self, written, capsys):
        _edit(written["notes"], lambda d: d["rows"].pop(1))
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "OBS-2" in capsys.readouterr().err

    def test_a_note_for_an_unknown_observation_is_refused(self, written, capsys):
        _edit(
            written["notes"],
            lambda d: d["rows"].append({**d["rows"][0], "observation_id": "OBS-9"}),
        )
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "OBS-9" in capsys.readouterr().err

    def test_rows_that_are_not_the_esr_records_observations_are_refused(self, written, capsys):
        _edit(written["comparison"], lambda d: d["rows"].pop(0))
        _edit(written["notes"], lambda d: d["rows"].pop(0))
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "not the ESR record's observations" in capsys.readouterr().err

    def test_a_blind_finding_whose_text_moved_is_refused(self, written, capsys):
        def mutate(data):
            data["rows"][0]["blind_findings"][0]["text"] = "Something the baseline never said."
        _edit(written["comparison"], mutate)
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "text the comparison did not record" in capsys.readouterr().err

    def test_a_blind_finding_that_no_longer_resolves_is_refused(self, written, capsys):
        def mutate(data):
            data["rows"][0]["blind_findings"][0]["index"] = 99
        _edit(written["comparison"], mutate)
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "has no shortcoming 99" in capsys.readouterr().err

    def test_a_quote_that_is_no_longer_in_the_candidate_is_refused(self, written, capsys):
        def mutate(data):
            data["rows"][0]["current_proposal_evidence"][0]["quote"] = "never written anywhere"
        _edit(written["comparison"], mutate)
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "is not found in" in capsys.readouterr().err

    def test_a_register_pointer_whose_value_moved_is_refused(self, written, capsys):
        def mutate(data):
            row = next(r for r in data["rows"] if r["evidence_basis"])
            row["evidence_basis"][0]["value"] = "a value the register does not hold"
        _edit(written["comparison"], mutate)
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "now holds" in capsys.readouterr().err

    def test_every_reference_of_every_row_is_counted_as_resolved(self, written):
        bundle_ = written["bundle"]
        resolved = orv.resolve_inputs(
            written["comparison"], repo_root=written["world"], profile=bundle_.profile
        )
        notes = orv.load_review_notes(written["notes"])
        review = orv.build_review(resolved, notes, clock=lambda: FROZEN)
        by_id = {r.observation_id: r.references for r in review.rows}
        assert by_id["OBS-1"].blind == 1
        assert by_id["OBS-1"].current_quotes == 1
        assert by_id["OBS-4"].register_entries == 2
        assert by_id["OBS-2"].blind == 0


# --------------------------------------------------------------------------- #
# Counts
# --------------------------------------------------------------------------- #


class TestCounts:
    def test_criticisms_and_strengths_are_counted_apart(self, written):
        counts = orv.recount(json.loads(written["comparison"].read_text(encoding="utf-8"))["rows"])
        assert counts["observations"] == 4
        assert counts["criticisms"]["total"] == 3
        assert counts["strengths"]["total"] == 1
        assert counts["kinds"]["shortcoming"] == 1
        assert counts["kinds"]["minor_shortcoming"] == 2
        assert counts["criticisms"]["by_disposition"]["independently_detected"] == 1
        assert counts["strengths"]["by_disposition"]["independently_detected"] == 1

    def test_lanes_are_attributed_per_row(self, written):
        counts = orv.recount(json.loads(written["comparison"].read_text(encoding="utf-8"))["rows"])
        assert counts["criticisms"]["by_lane"][orv.LANE_BLIND_ONLY] == 1
        assert counts["criticisms"]["by_lane"][orv.LANE_NEITHER] == 2
        assert counts["criticisms"]["by_lane"][orv.LANE_BOTH] == 0

    @pytest.mark.parametrize(
        "field,value,expected",
        [
            ("observations", 7, "the comparison's summary says 7"),
            ("by_kind", {"shortcoming": 2, "minor_shortcoming": 2, "strength": 1}, "of kind"),
            ("strengths_contested_by_blind_findings", 3, "contested strength"),
        ],
    )
    def test_a_summary_that_disagrees_with_the_rows_is_refused(
        self, written, capsys, field, value, expected
    ):
        _edit(written["comparison"], lambda d: d["summary"].__setitem__(field, value))
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert expected in capsys.readouterr().err

    def test_a_disposition_count_that_disagrees_is_refused(self, written, capsys):
        _edit(
            written["comparison"],
            lambda d: d["summary"]["by_disposition"].__setitem__("independently_detected", 5),
        )
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "disposed 'independently_detected'" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# The rendered artifacts
# --------------------------------------------------------------------------- #


class TestTheRenderedReport:
    def test_both_artifacts_are_written_and_share_a_sequence_number(self, written):
        code, reviews = _review(written)
        assert code == 0
        review = next(reviews.glob("operator_review_*.md"))
        decisions = next(reviews.glob("operator_decisions_*.md"))
        assert review.stem.rsplit("_", 1)[1] == decisions.stem.rsplit("_", 1)[1] == "0001"

    def test_nothing_is_overwritten(self, written):
        assert _review(written)[0] == 0
        code, reviews = _review(written)
        assert code == 0
        assert {p.name.rsplit("_", 1)[1] for p in reviews.glob("operator_review_*.md")} == {
            "0001.md",
            "0002.md",
        }

    def test_every_observation_appears_exactly_once_as_a_heading(self, written):
        text = _report_text(written)
        for oid in ("OBS-1", "OBS-2", "OBS-3", "OBS-4"):
            assert len(re.findall(rf"^### {oid} — ", text, re.MULTILINE)) == 1

    def test_the_title_names_the_subject_from_the_comparisons_own_bindings(self, written):
        """No instrument or call name is written into the module: the harness is
        instrument-agnostic (tests/harness/test_profile.py's lint) and the
        subject is read from the baseline's intake id."""
        text = _report_text(written)
        assert text.startswith("# Operator review — the 4 ESR observations of INTAKE-1")

    def test_the_report_states_the_review_state_and_calls_itself_provisional(self, written):
        text = _report_text(written)
        assert orv.REVIEW_STATE_PENDING in text
        assert "provisional" in text
        assert "agent-drafted" in text

    def test_counts_keep_criticisms_apart_from_strengths(self, written):
        text = _report_text(written)
        assert "**3 criticisms**" in text
        assert "**1 strengths**" in text
        assert "### Criticisms" in text and "### Strengths" in text

    def test_reference_resolution_and_semantic_agreement_are_separate_fields(self, written):
        text = _report_text(written)
        assert "**Reference check (measured):**" in text
        assert "**Semantic agreement (declared, provisional):**" in text

    def test_the_decisions_section_lists_exactly_the_rows_with_questions(self, written):
        code, reviews = _review(written)
        assert code == 0
        decisions = next(reviews.glob("operator_decisions_*.md")).read_text(encoding="utf-8")
        assert "## 1. OBS-2" in decisions
        assert "## 2. OBS-3" in decisions
        assert "## 3. OBS-4" in decisions
        assert "OBS-1" not in decisions

    def test_the_misses_and_the_contested_strengths_are_highlighted(self, written):
        text = _report_text(written)
        assert "### The six alleged misses" in text or "alleged misses" in text
        assert "### The contested strengths" in text

    def test_a_candidate_quote_never_lands_in_a_table_cell(self, written):
        text = _report_text(written)
        quoted = [line for line in text.splitlines() if line.startswith("> ")]
        assert quoted
        for line in text.splitlines():
            if line.startswith("|"):
                assert "objective one and objective two" not in line

    def test_a_pipe_in_a_cell_is_escaped(self, written):
        _edit(
            written["notes"],
            lambda d: d["rows"][2].__setitem__(
                "operator_decision", "Decide A | or B before R03."
            ),
        )
        _rebind(written)
        text = _report_text(written)
        assert "Decide A \\| or B before R03." in text

    def test_two_renders_of_the_same_inputs_are_byte_identical(self, written):
        first = _report_text(written)
        second = _report_text(written)
        assert first == second

    def test_the_rendering_does_not_depend_on_the_directory_it_ran_from(
        self, written, monkeypatch, tmp_path
    ):
        """Every path in the report is written relative to the repo root, so a
        committed artifact replays from anywhere."""
        first = _report_text(written)
        monkeypatch.chdir(tmp_path)
        assert _report_text(written) == first

    def test_the_terminal_summary_names_the_bindings_and_the_counts(self, written, capsys):
        code, _reviews = _review(written)
        assert code == 0
        out = capsys.readouterr().out
        assert "OPERATOR REVIEW" in out
        assert "criticisms 3" in out
        assert "decisions required:  3 of 4 rows" in out

    def test_a_recommended_change_of_disposition_needs_a_question(self, written, capsys):
        def mutate(data):
            data["rows"][0]["recommended_disposition"] = "partially_observable"
        _edit(written["notes"], mutate)
        _rebind(written)
        code, _reviews = _review(written)
        assert code == 2
        assert "a question for the operator" in capsys.readouterr().err

    def test_a_recommended_change_is_marked_in_the_row(self, written):
        def mutate(data):
            data["rows"][0]["recommended_disposition"] = "partially_observable"
            data["rows"][0]["recommendation"] = orv.RECOMMENDATION_R03
            data["rows"][0]["operator_decision"] = "Decide whether part of the point was found."
        _edit(written["notes"], mutate)
        _rebind(written)
        text = _report_text(written)
        assert "(**a change from the comparison**)" in text


# --------------------------------------------------------------------------- #
# The committed MSCA-DN review
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    not DN_COMPARISON.is_file() or not DN_NOTES.is_file(), reason="MSCA-DN artifacts absent"
)
class TestCommittedMscaDn:
    def _build(self) -> orv.Review:
        profile = load_profile_bundle(str(DN_PROFILE), repo_root=REPO)
        resolved = orv.resolve_inputs(DN_COMPARISON, repo_root=REPO, profile=profile.profile)
        notes = orv.load_review_notes(DN_NOTES)
        return orv.build_review(resolved, notes, clock=lambda: FROZEN)

    def test_the_notes_cover_the_esr_records_observations_exactly_once(self):
        review = self._build()
        esr = ec.load_esr_record(DN_ESR)
        assert [r.observation_id for r in review.rows] == [o["id"] for o in esr.observations]
        assert len(review.rows) == 29

    def test_every_reference_still_resolves_against_its_named_artifact(self):
        review = self._build()
        assert sum(r.references.total for r in review.rows) > 100
        assert all(r.note.get("agreement_basis") for r in review.rows)

    def test_the_counts_are_the_fifteen_criticisms_and_fourteen_strengths(self):
        counts = self._build().counts
        assert counts["observations"] == 29
        assert counts["criticisms"]["total"] == 15
        assert counts["strengths"]["total"] == 14
        assert counts["criticisms"]["by_disposition"]["independently_detected"] == 6
        assert (
            counts["criticisms"]["by_disposition"][
                "not_detected_despite_sufficient_preserved_evidence"
            ]
            == 6
        )
        assert counts["strengths"]["contested"] == 8

    def test_every_disputed_or_unresolved_row_carries_a_question(self):
        review = self._build()
        for row in review.rows:
            agreement = row.note.get("semantic_agreement")
            if agreement != orv.AGREEMENT_AGREED:
                assert row.decision, f"{row.observation_id} has no operator decision"

    def test_no_note_recommends_a_disposition_change_without_a_question(self):
        review = self._build()
        for row in review.rows:
            if row.note.get("recommended_disposition") != row.comparison.get("disposition"):
                assert row.decision, row.observation_id

    @pytest.mark.skipif(not DN_REVIEWS.is_dir(), reason="the review has not been written yet")
    def test_the_committed_report_is_reproduced_by_re_rendering(self):
        review = self._build()
        report = sorted(DN_REVIEWS.glob("operator_review_*.md"))[-1]
        decisions = sorted(DN_REVIEWS.glob("operator_decisions_*.md"))[-1]
        for path, rendered in (
            (report, orv.render_review(review)),
            (decisions, orv.render_decisions(review, review_name=report.name)),
        ):
            recorded = path.read_text(encoding="utf-8")
            assert _GENERATED.sub("", recorded) == _GENERATED.sub("", rendered), path.name

    def test_the_two_committed_artifacts_name_each_other_and_share_a_run(self):
        report = sorted(DN_REVIEWS.glob("operator_review_*.md"))[-1]
        decisions = sorted(DN_REVIEWS.glob("operator_decisions_*.md"))[-1]
        text = decisions.read_text(encoding="utf-8")
        assert f"`{report.name}`" in text
        stamped = {
            _GENERATED.search(p.read_text(encoding="utf-8")).group(0)
            for p in (report, decisions)
        }
        assert len(stamped) == 1, "the pair was not written by one run"
