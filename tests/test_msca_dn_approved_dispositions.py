"""
The PE-08 operator approval carried into the approved dispositions, notes,
comparison, review and diff (2026-10-08).

Three groups:

* The renderer: ``--check`` is a byte-equal replay, every binding is the hash
  of the file on disk, and the approval record it transcribes is the one on
  disk.
* The declarations: each row's review status follows the approval record's
  tables, only the enumerated rows change what they declare, every miss
  declares a failure mode, the beyond-ESR work is labelled and commits to
  nothing, and no row is raised to Confirmed by the approval.
* The artifacts written from the record: the comparison replays from its
  documented inputs under the identity pointer rule (V02), the counts are the
  rows, the score block is byte-identical to the predecessor's, the review
  and the diff reproduce, and every predecessor artifact is untouched.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

import harness.commands.blind_assessment as cmd
import harness.comparison_diff as cd
import harness.esr_comparison as ec
import harness.operator_review as orv
from harness.rubrics import load_profile_bundle
from runner.paths import find_repo_root
from tools import author_approved_dispositions as aad
from tools import author_successor_dispositions as asd

REPO = find_repo_root()
DN = REPO / "docs/tier4_orchestration_state/msca_dn"
BASELINE = DN / "baselines/resolved_fixes_2026-10-06"
CANDIDATE = DN / "audit/candidates/MSCA-DN-2025_sanitised_part_b@b51a103520b58ded"
HISTORICAL = DN / "audit/candidates/MSCA-DN-2025_sanitised_part_b@bdb8670f6987e4db"
APPROVED_COMPARISON = DN / "comparisons/comparison_f60ae6e0a2a1_0003.json"
APPROVED_REVISIONS = DN / "comparisons/revisions_f60ae6e0a2a1_0003.json"
PROFILE = REPO / "harness/profiles/msca_dn_2026_default.json"
FROZEN = "2026-10-08T00:00:00+00:00"

pytestmark = pytest.mark.skipif(
    not (REPO / aad.SUCCESSOR_REL).is_file(), reason="the approved dispositions are absent"
)


def _read(rel: Path) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def approved() -> dict:
    return _read(aad.SUCCESSOR_REL)


@pytest.fixture(scope="module")
def predecessor() -> dict:
    return _read(aad.PREDECESSOR_REL)


@pytest.fixture(scope="module")
def rows(approved) -> dict[str, dict]:
    return {str(r["observation_id"]): r for r in approved["rows"]}


@pytest.fixture(scope="module")
def approval_text() -> str:
    return (REPO / aad.APPROVAL_REL).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# The renderer
# --------------------------------------------------------------------------- #


class TestRenderer:
    def test_the_committed_records_are_a_byte_equal_replay(self):
        assert aad.check(REPO) == []

    def test_every_binding_is_the_hash_of_the_file_on_disk(self, approved):
        assert approved["supersedes_sha256"] == aad._sha256(REPO, aad.PREDECESSOR_REL)
        assert approved["esr_record_sha256"] == aad._sha256(REPO, aad.ESR_RECORD_REL)
        assert approved["fidelity_register_sha256"] == aad._sha256(REPO, aad.REGISTER_REL)
        assert approved["operator_approval"]["sha256"] == aad._sha256(REPO, aad.APPROVAL_REL)
        inputs = approved["review_inputs"]
        assert inputs["approval_record_sha256"] == aad._sha256(REPO, aad.APPROVAL_REL)
        assert inputs["predecessor_comparison_sha256"] == aad._sha256(
            REPO, aad.PREDECESSOR_COMPARISON_REL
        )
        assert inputs["review_notes_sha256"] == aad._sha256(REPO, aad.NOTES_PREDECESSOR_REL)
        assert inputs["adjudication_record_sha256"] == aad._sha256(REPO, aad.ADJUDICATIONS_REL)

    def test_the_bindings_are_the_predecessors(self, approved, predecessor):
        for key in ("baseline_report_sha256", "esr_record_sha256", "fidelity_register",
                    "fidelity_register_sha256", "candidate", "historical_candidate"):
            assert approved[key] == predecessor[key], key

    def test_the_schema_version_is_the_one_that_resolves_by_identity(self, approved):
        assert approved["schema_version"] == "1.2"
        assert "1.2" in ec.VERSIONS_WITH_IDENTITY_POINTERS
        assert "1.2" in ec.VERSIONS_REQUIRING_A_FAILURE_MODE

    def test_a_missing_approval_record_is_refused(self, monkeypatch):
        monkeypatch.setattr(aad, "APPROVAL_REL", Path("docs/nowhere.md"))
        with pytest.raises(aad.SuccessorError, match="nowhere.md"):
            aad.render(REPO)

    def test_a_miss_without_an_enumerated_failure_mode_is_refused(self, monkeypatch):
        monkeypatch.setattr(aad, "FAILURE_MODES", {k: v for k, v in aad.FAILURE_MODES.items() if k != "ESR-E-02"})
        with pytest.raises(aad.SuccessorError, match="ESR-E-02"):
            aad.render(REPO)

    def test_the_notes_are_rendered_only_over_the_bound_comparison(self):
        bound = aad.successor_comparison(REPO)
        assert bound is not None and bound.name == APPROVED_COMPARISON.name
        notes = _read(aad.NOTES_SUCCESSOR_REL)
        assert notes["comparison"] == APPROVED_COMPARISON.relative_to(REPO).as_posix()
        assert notes["comparison_sha256"] == aad.file_sha256(APPROVED_COMPARISON)


# --------------------------------------------------------------------------- #
# The transcription
# --------------------------------------------------------------------------- #


class TestTranscription:
    def test_every_transcribed_decision_is_in_the_approval_record(self, approval_text):
        for did, d in aad.DECISIONS.items():
            assert f"| {did} |" in approval_text, did
            for fragment in (d["decision"], d["limit"]):
                assert fragment in approval_text, (did, fragment[:40])

    def test_every_deferral_is_in_the_approval_record(self, approval_text):
        for oid, d in aad.DEFERRED.items():
            assert d["required_private_evidence"] in approval_text, oid
            assert d["disposition"] in approval_text, oid

    def test_the_approval_block_names_the_instruction_and_the_scope(self, approved):
        block = approved["operator_approval"]
        assert block["instruction"] == "Approve this decision package"
        assert block["approved_at"] == "2026-10-08T10:37:26+02:00"
        assert "authority fact" in block["scope"]
        assert block["decisions_applied"] == ["D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08", "D11", "D12"]

    def test_the_record_is_operator_reviewed_and_says_what_that_means(self, approved):
        assert approved["review_state"] == ec.REVIEW_STATE_OPERATOR_REVIEWED
        note = approved["review_status_note"]
        for status in ec.ROW_REVIEW_STATES:
            assert status in note


# --------------------------------------------------------------------------- #
# The declarations
# --------------------------------------------------------------------------- #


class TestDeclarations:
    def test_every_row_carries_the_status_the_approval_gives_it(self, rows):
        for oid, row in rows.items():
            expected = (
                "operator_confirmed" if oid in aad.CONFIRMED
                else "operator_decision_required" if oid in aad.DEFERRED
                else "agent_recommended_pending_operator_review"
            )
            assert row["review_status"] == expected, oid

    def test_a_confirmed_row_names_its_decisions_and_a_deferred_row_its_question(self, rows):
        for oid, row in rows.items():
            if oid in aad.CONFIRMED:
                assert row["operator_decision_ids"] == list(aad.CONFIRMED[oid]), oid
            else:
                assert "operator_decision_ids" not in row, oid
            if oid in aad.DEFERRED:
                assert aad.DEFERRED[oid]["required_private_evidence"] in row["deferred_to_private_network"], oid
            else:
                assert "deferred_to_private_network" not in row, oid

    def test_the_counts_by_status(self, approved):
        state = approved["decision_state"]
        assert len(state["rows_operator_confirmed"]) == 9
        assert len(state["rows_operator_decision_required"]) == 10
        assert len(state["rows_agent_recommended"]) == 10
        assert set(state["rows_operator_confirmed"]) & set(aad.DEFERRED) == {"ESR-Q-01", "ESR-Q-03"}

    def test_only_q_03_changes_its_disposition(self, rows, predecessor):
        before = {str(r["observation_id"]): r for r in predecessor["rows"]}
        moved = {
            oid for oid in rows
            if (rows[oid]["disposition"], rows[oid]["declared_status"])
            != (before[oid]["disposition"], before[oid]["declared_status"])
        }
        assert moved == {"ESR-Q-03"}

    def test_q_03_is_partial_on_the_audits_timing_finding_alone(self, rows):
        row = rows["ESR-Q-03"]
        assert row["disposition"] == "partially_observable"
        assert row["declared_status"] == "Inferred"
        assert "blind_findings" not in row
        assert row["audit_findings"] == [{
            "report": aad.SUCCESSOR_AUDIT_REL.as_posix(),
            "check": "milestone_dependencies",
            "index": 0,
        }]
        assert row["evidence_basis"] == ["derived/sub_sections/3.1"]
        assert row["operator_decision_ids"] == ["D06", "D12"]
        confirm = row["proposed_revision"]["revision_plan"]["requires_confirmation"]
        assert any("not exhaustive" in c for c in confirm)
        assert any("D11" in c for c in confirm)
        assert not any("that its due month follows them" in c for c in confirm)

    def test_the_audit_cited_is_the_one_written_after_d11(self):
        audit = _read(aad.SUCCESSOR_AUDIT_REL)
        (ms,) = [c for c in audit["checks"] if c["check_id"] == "milestone_dependencies"]
        assert ms["findings_by_kind"] == {"out_of_window": 1}
        assert ms["findings"][0]["subject"] == "M7.3"
        assert len(ms["context"]["milestones_without_a_named_dependency"]) == 16
        predecessor_audit = _read(aad.PREDECESSOR_AUDIT_REL)
        assert predecessor_audit["findings_total"] == 29 and audit["findings_total"] == 13

    def test_every_miss_declares_a_failure_mode_from_the_vocabulary(self, rows):
        misses = {oid for oid, r in rows.items() if r["disposition"] == ec.DISPOSITION_NOT_DETECTED}
        assert misses == set(aad.FAILURE_MODES) == set(aad.MISSES)
        for oid in misses:
            assert rows[oid]["failure_mode"] in ec.MISS_FAILURE_MODES, oid
            assert rows[oid]["failure_mode_basis"].strip(), oid
        for oid, r in rows.items():
            if oid not in misses:
                assert "failure_mode" not in r, oid

    def test_e_03_is_described_as_absent_from_the_output_not_unread(self, rows):
        row = rows["ESR-E-03"]
        assert row["failure_mode"] == ec.FAILURE_MODE_ABSENT
        assert "does not establish that the model did not read" in row["explanation"]
        assert "evidence_not_read" not in row["explanation"]

    def test_the_adequacy_disagreements_are_told_apart(self, rows):
        assert rows["ESR-E-07"]["failure_mode"] == ec.FAILURE_MODE_RATED_ADEQUATE
        assert rows["ESR-E-09"]["failure_mode"] == ec.FAILURE_MODE_RATED_ADEQUATE
        assert rows["ESR-Q-02"]["failure_mode"] == ec.FAILURE_MODE_MISATTRIBUTED

    def test_no_row_is_raised_to_confirmed_by_the_approval(self, rows, predecessor):
        before = {str(r["observation_id"]): r for r in predecessor["rows"]}
        for oid, row in rows.items():
            assert row.get("evidence_preserved_status") != "Confirmed", oid
            if before[oid]["declared_status"] != "Unresolved":
                assert row["declared_status"] == before[oid]["declared_status"], oid
        assert rows["ESR-E-04"]["declared_status"] == "Unresolved"
        assert rows["ESR-E-04"]["evidence_preserved_status"] == "Unresolved"

    def test_the_seven_misses_stay_provisional(self, approved):
        state = approved["decision_state"]
        assert state["preservation_provisional_rows"] == sorted(aad.MISSES)
        assert "provisional" in state["preservation_note"]

    def test_the_beyond_esr_work_is_labelled_and_commits_to_nothing(self, rows):
        rev = rows["ESR-I-S02"]["proposed_revision"]
        assert rev["scope"] == ec.REVISION_SCOPE_BEYOND
        plan = rev["revision_plan"]
        assert plan["commitment_kind"] == "requires_original_check"
        assert plan["responsible_role"] == dict(asd.ROLES["innovation_committee"])
        assert "No funding source" in plan["approved_limit"]
        (task,) = rows["ESR-I-02"]["proposed_revision"]["revision_plan"]["subtasks"]
        assert task["label"] == "societal_impact_indicators"
        assert task["scope"] == ec.REVISION_SCOPE_BEYOND
        assert task["approved_by"] == "D08"
        assert "No indicator, numerical target or clinical outcome is proposed" in task["text"]
        for oid, row in rows.items():
            if oid not in ("ESR-I-S02",) and row.get("review_status") and oid.split("-")[-1].startswith("S"):
                assert "proposed_revision" not in row, oid

    def test_the_validation_cases_name_their_decisions_and_rows(self, approved):
        cases = {c["id"]: c for c in approved["assessor_validation_cases"]}
        assert set(cases) == {"AVC-01", "AVC-02"}
        assert cases["AVC-01"]["decision_id"] == "D04"
        assert cases["AVC-01"]["observation_ids"] == ["ESR-Q-01", "ESR-Q-03"]
        assert cases["AVC-02"]["decision_id"] == "D05"
        assert cases["AVC-02"]["observation_ids"] == ["ESR-Q-02"]

    def test_the_rows_the_approval_did_not_address_are_carried_through(self, rows, predecessor):
        before = {str(r["observation_id"]): r for r in predecessor["rows"]}
        for oid, row in rows.items():
            if row["review_status"] != "agent_recommended_pending_operator_review" or oid == "ESR-I-02":
                continue
            stripped = {k: v for k, v in row.items() if k != "review_status"}
            assert stripped == {k: v for k, v in before[oid].items() if k != "review_status"}, oid


# --------------------------------------------------------------------------- #
# The artifacts written from the record
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not APPROVED_COMPARISON.is_file(), reason="the approved comparison is absent")
class TestWrittenArtifacts:
    def _replay(self, out: Path) -> int:
        argv = [
            "compare",
            "--baseline-dir", str(BASELINE),
            "--esr", str(REPO / aad.ESR_RECORD_REL),
            "--dispositions", str(REPO / aad.SUCCESSOR_REL),
            "--candidate", str(CANDIDATE),
            "--historical-candidate", str(HISTORICAL),
            "--register", str(REPO / aad.REGISTER_REL),
            "--audit", str(REPO / aad.SUCCESSOR_AUDIT_REL),
            "--audit", str(REPO / aad.FIRST_REVISION_AUDIT_REL),
            "--repo-root", str(REPO),
            "--profile", str(PROFILE),
            "--out-dir", str(out),
        ]
        return cmd.main(argv, clock=lambda: FROZEN)

    def test_the_committed_comparison_replays_from_its_documented_inputs(self, tmp_path):
        assert self._replay(tmp_path) == 0
        fresh = ec.load_comparison(next(tmp_path.glob("comparison_*.json")))
        recorded = json.loads(APPROVED_COMPARISON.read_text(encoding="utf-8-sig"))
        volatile = {"compared_at", "writes", "revisions_artifact", "baseline"}
        assert {k: v for k, v in fresh.items() if k not in volatile} == {
            k: v for k, v in recorded.items() if k not in volatile
        }

    def test_the_pointers_resolve_by_identity(self):
        recorded = json.loads(APPROVED_COMPARISON.read_text(encoding="utf-8-sig"))
        assert recorded["fidelity_register"]["pointer_resolution"] == ec.POINTER_RESOLUTION_IDENTITY
        register = _read(aad.REGISTER_REL)
        by_id = {str(s["sub_section_id"]): s for s in register["derived"]["sub_sections"]}
        rows = {str(r["observation_id"]): r for r in recorded["rows"]}
        values = {e["pointer"]: e["value"] for e in rows["ESR-Q-S02"]["evidence_basis"]}
        assert values["derived/sub_sections/8/characters"] == by_id["8"]["characters"]
        values = {e["pointer"]: e["value"] for e in rows["ESR-Q-S03"]["evidence_basis"]}
        assert values["derived/sub_sections/5/characters"] == by_id["5"]["characters"]
        # the predecessor recorded the ninth and sixth elements under the legacy rule
        predecessor = _read(aad.PREDECESSOR_COMPARISON_REL)
        old = {str(r["observation_id"]): r for r in predecessor["rows"]}
        assert {e["pointer"]: e["value"] for e in old["ESR-Q-S02"]["evidence_basis"]}[
            "derived/sub_sections/8/characters"
        ] == by_id["3.1"]["characters"]

    def test_the_counts_are_the_rows(self):
        recorded = json.loads(APPROVED_COMPARISON.read_text(encoding="utf-8-sig"))
        summary = recorded["summary"]
        counted = Counter(r["disposition"] for r in recorded["rows"])
        assert {k: v for k, v in summary["by_disposition"].items() if v} == dict(counted)
        detection = summary["detection"]
        assert detection["rated"] == 14
        assert detection["independently_detected"] == 5
        assert detection["partially_observable"] == 2
        assert detection["not_detected"] == 7
        assert detection["by_lane"] == {"blind_lane": 6, "integrity_audit": 1}
        modes = summary["misses_by_failure_mode"]["by_mode"]
        assert sorted(sum(modes.values(), [])) == sorted(aad.MISSES)
        assert modes["read_and_rated_adequate"] == ["ESR-E-07", "ESR-E-09"]
        assert summary["shared_esr_sentences"]["groups"][0]["observation_ids"] == ["ESR-E-01", "ESR-E-02"]

    def test_the_review_state_block_names_the_confirmed_rows(self):
        recorded = json.loads(APPROVED_COMPARISON.read_text(encoding="utf-8-sig"))
        state = recorded["review_state"]
        assert state["state"] == ec.REVIEW_STATE_OPERATOR_REVIEWED
        assert len(state["rows_operator_confirmed"]) == 9
        assert len(state["rows_needing_an_operator_decision"]) == 10
        assert state["operator_approval"]["record"] == aad.APPROVAL_REL.as_posix()

    def test_the_score_block_and_the_baseline_are_untouched(self):
        recorded = json.loads(APPROVED_COMPARISON.read_text(encoding="utf-8-sig"))
        predecessor = _read(aad.PREDECESSOR_COMPARISON_REL)
        assert recorded["score_comparison"] == predecessor["score_comparison"]
        assert recorded["score_comparison"]["total"]["blind"] == 74.6
        assert recorded["baseline"]["report_sha256"] == predecessor["baseline"]["report_sha256"]

    def test_every_shortcoming_is_still_open_and_the_beyond_esr_work_is_apart(self):
        revisions = json.loads(APPROVED_REVISIONS.read_text(encoding="utf-8-sig"))
        recorded = json.loads(APPROVED_COMPARISON.read_text(encoding="utf-8-sig"))
        shortcomings = {str(r["observation_id"]) for r in recorded["rows"] if r["kind"] != "strength"}
        assert shortcomings == {str(e["observation_id"]) for e in revisions["open"]}
        assert revisions["closed"] == []
        beyond = {(e["observation_id"], e["label"]) for e in revisions["beyond_esr_improvements"]}
        assert beyond == {
            ("ESR-I-S02", "post_project_sustainability_funding"),
            ("ESR-I-02", "societal_impact_indicators"),
        }

    def test_the_review_pair_reproduces_and_keeps_recorded_and_open_apart(self, tmp_path):
        profile = load_profile_bundle(str(PROFILE), repo_root=REPO)
        resolved = orv.resolve_inputs(APPROVED_COMPARISON, repo_root=REPO, profile=profile.profile)
        notes = orv.load_review_notes(REPO / aad.NOTES_SUCCESSOR_REL)
        review = orv.build_review(resolved, notes, clock=lambda: FROZEN)
        assert review.approval is not None
        assert {r.observation_id for r in review.recorded_decisions} == set(aad.CONFIRMED)
        assert {r.observation_id for r in review.decisions} == set(aad.DEFERRED)
        text = orv.render_decisions(review, review_name="x")
        assert "## Recorded decisions" in text and "## Open decisions" in text

    def test_the_corrected_counts_are_the_registers(self):
        notes = _read(aad.NOTES_SUCCESSOR_REL)
        rows = {str(r["observation_id"]): r for r in notes["rows"]}
        register = _read(aad.REGISTER_REL)
        by_id = {str(s["sub_section_id"]): s for s in register["derived"]["sub_sections"]}
        assert f"{by_id['8']['characters']:,} characters" in rows["ESR-Q-S02"]["uncertainty"]
        assert f"{by_id['5']['characters']:,} characters" in rows["ESR-Q-S03"]["uncertainty"]
        assert "28,087 was sub-section 3.1's" in rows["ESR-Q-S02"]["uncertainty"]

    def test_the_diff_against_the_r05_comparison_reproduces(self):
        diffs = sorted(DN.glob("comparisons/review_diff_*.json"))
        ours = [p for p in diffs if cd.load_diff(p)["successor"]["comparison"].endswith("_0003.json")]
        assert len(ours) == 1
        recorded = cd.load_diff(ours[0])
        before = cd.load_pair_member(REPO / aad.PREDECESSOR_COMPARISON_REL, what="predecessor")
        after = cd.load_pair_member(APPROVED_COMPARISON, what="successor")
        fresh = cd.diff_comparisons(before, after, repo_root=REPO, clock=lambda: FROZEN)
        volatile = {"diffed_at", "writes"}
        assert {k: v for k, v in fresh.items() if k not in volatile} == {
            k: v for k, v in recorded.items() if k not in volatile
        }
        moved = {r["observation_id"]: r["changed"] for r in recorded["rows"]}
        assert "evidence_basis_values" in moved["ESR-Q-S02"]
        assert "disposition" in moved["ESR-Q-03"]
        assert recorded["flags"] == []

    def test_the_predecessor_artifacts_are_untouched(self, predecessor):
        r05_log = _read(Path("docs/tier4_orchestration_state/decision_log/msca-dn-successor-dispositions_2026-10-07.json"))
        for group in ("written", "unchanged_and_still_cited"):
            for key, entry in r05_log["artifacts"][group].items():
                assert entry["sha256"] == aad._sha256(REPO, Path(entry["path"])), f"{group}/{key}"


# --------------------------------------------------------------------------- #
# The decision-log record
# --------------------------------------------------------------------------- #


DECISION = Path("docs/tier4_orchestration_state/decision_log/msca-dn-operator-approval_2026-10-08.json")


@pytest.mark.skipif(not (REPO / DECISION).is_file(), reason="the decision record is absent")
class TestDecisionRecord:
    def test_every_recorded_hash_is_the_file_on_disk(self):
        record = _read(DECISION)
        for group in ("written", "unchanged_and_still_cited"):
            for key, entry in record["artifacts"][group].items():
                assert entry["sha256"] == aad._sha256(REPO, Path(entry["path"])), f"{group}/{key}"

    def test_the_record_pins_the_approval_and_the_baseline(self):
        record = _read(DECISION)
        written = record["artifacts"]["written"]
        assert written["approval_record"]["path"] == aad.APPROVAL_REL.as_posix()
        cited = record["artifacts"]["unchanged_and_still_cited"]
        assert cited["baseline_report"]["sha256"].startswith("f60ae6e0a2a1")
