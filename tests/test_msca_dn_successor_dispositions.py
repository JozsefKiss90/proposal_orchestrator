"""
The successor ESR dispositions and the comparison written from them (ticket R05).

Three groups:

* The renderer: ``--check`` is a byte-equal replay, every binding is computed
  from the file on disk, and the record refuses a shortcoming it has no plan
  for.
* The declarations: only the three adjudicated rows change what they declare,
  the fourteen strengths are carried through untouched, and no row claims
  operator approval or Confirmed preservation.
* The traceability the plans assert: every role is quoted from the candidate's
  own text and every proposal location names a sub-section the candidate has.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

import harness.commands.blind_assessment as cmd
import harness.esr_comparison as ec
from harness.blind_assessment import load_candidate
from harness.rubrics import load_profile_bundle
from runner.paths import find_repo_root
from tools import author_successor_dispositions as asd

REPO = find_repo_root()
DN = REPO / "docs/tier4_orchestration_state/msca_dn"
BASELINE = DN / "baselines/resolved_fixes_2026-10-06"
CANDIDATE = DN / "audit/candidates/MSCA-DN-2025_sanitised_part_b@b51a103520b58ded"
HISTORICAL = DN / "audit/candidates/MSCA-DN-2025_sanitised_part_b@bdb8670f6987e4db"
SUCCESSOR_COMPARISON = DN / "comparisons/comparison_f60ae6e0a2a1_0002.json"
PROFILE = REPO / "harness/profiles/msca_dn_2026_default.json"
REGISTER = REPO / asd.REGISTER_REL

MOVED = ("ESR-E-04", "ESR-Q-01", "ESR-Q-03")

pytestmark = pytest.mark.skipif(
    not (REPO / asd.PREDECESSOR_REL).is_file(),
    reason="the MSCA-DN PE-08 dispositions are absent",
)


def _read(rel: Path) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def successor() -> dict:
    return _read(asd.SUCCESSOR_REL)


@pytest.fixture(scope="module")
def predecessor() -> dict:
    return _read(asd.PREDECESSOR_REL)


@pytest.fixture(scope="module")
def esr_kinds() -> dict[str, str]:
    esr = _read(asd.ESR_RECORD_REL)
    return {str(o["id"]): str(o["kind"]) for o in esr["observations"]}


@pytest.fixture(scope="module")
def candidate_text() -> dict[tuple[str, str], str]:
    bundle = load_profile_bundle(str(PROFILE), repo_root=REPO)
    candidate = load_candidate(CANDIDATE, bundle.profile)
    return {
        (section_id, str(sub["sub_section_id"])): str(sub.get("content") or "")
        for section_id, content in candidate.contents.items()
        for sub in content.get("sub_sections") or []
    }


# --------------------------------------------------------------------------- #
# The renderer
# --------------------------------------------------------------------------- #


class TestRenderer:
    def test_the_committed_record_is_a_byte_equal_replay(self):
        assert asd.check(REPO) == []

    def test_every_binding_is_the_hash_of_the_file_on_disk(self, successor):
        assert successor["supersedes_sha256"] == asd._sha256(REPO, asd.PREDECESSOR_REL)
        assert successor["esr_record_sha256"] == asd._sha256(REPO, asd.ESR_RECORD_REL)
        assert successor["fidelity_register_sha256"] == asd._sha256(REPO, asd.REGISTER_REL)
        inputs = successor["review_inputs"]
        assert inputs["adjudication_record_sha256"] == asd._sha256(REPO, asd.ADJUDICATIONS_REL)
        assert inputs["review_notes_sha256"] == asd._sha256(REPO, asd.REVIEW_NOTES_REL)

    def test_the_register_is_the_one_the_predecessor_cited(self, successor, predecessor):
        """R04's drafts are not adopted, so the register has not moved."""
        assert successor["fidelity_register"] == predecessor["fidelity_register"]
        assert successor["baseline_report_sha256"] == predecessor["baseline_report_sha256"]
        assert successor["esr_record_sha256"] == predecessor["esr_record_sha256"]

    def test_a_shortcoming_without_a_plan_is_refused(self, monkeypatch):
        plans = {k: v for k, v in asd.REVISION_PLANS.items() if k != "ESR-Q-04"}
        monkeypatch.setattr(asd, "REVISION_PLANS", plans)
        with pytest.raises(asd.SuccessorError, match="ESR-Q-04 is a shortcoming with no revision plan"):
            asd.render(REPO)

    def test_a_miss_without_an_enumerated_register_basis_is_refused(self, monkeypatch):
        basis = {k: v for k, v in asd.MISS_EVIDENCE_BASIS.items() if k != "ESR-E-02"}
        monkeypatch.setattr(asd, "MISS_EVIDENCE_BASIS", basis)
        with pytest.raises(asd.SuccessorError, match="ESR-E-02 is a miss"):
            asd.render(REPO)

    def test_a_plan_for_an_unknown_observation_is_refused(self, monkeypatch):
        plans = dict(asd.REVISION_PLANS)
        plans["ESR-X-99"] = plans["ESR-Q-04"]
        monkeypatch.setattr(asd, "REVISION_PLANS", plans)
        with pytest.raises(asd.SuccessorError, match="unknown observation\\(s\\): ESR-X-99"):
            asd.render(REPO)


# --------------------------------------------------------------------------- #
# The declarations
# --------------------------------------------------------------------------- #


class TestDeclarations:
    def test_the_record_claims_no_operator_approval(self, successor):
        assert successor["review_state"] == asd.REVIEW_STATE
        assert successor["advisory"] is True and successor["blocking"] is False
        assert "pending operator review" in successor["declared_by"]
        assert successor["decision_state"]["state"] == asd.REVIEW_STATE
        assert successor["open_operator_decisions"]
        assert all(d["declared_pending"] is True for d in successor["open_operator_decisions"])

    def test_only_three_rows_change_what_they_declare(self, successor, predecessor):
        """Three additions apply across the record and are not declarations about
        the point: the review status every row gains, the plan every shortcoming
        gains, and the register basis schema 1.1 makes a miss name. Strip all
        three and exactly the three adjudicated rows have moved."""
        before = {str(r["observation_id"]): r for r in predecessor["rows"]}
        moved: list[str] = []
        for row in successor["rows"]:
            oid = str(row["observation_id"])
            stripped = copy.deepcopy(row)
            stripped.pop("review_status", None)
            revision = stripped.get("proposed_revision")
            if isinstance(revision, dict):
                revision.pop("revision_plan", None)
            if oid in asd.MISS_EVIDENCE_BASIS:
                stripped.pop("evidence_basis", None)
                if "evidence_basis" in before[oid]:
                    stripped["evidence_basis"] = before[oid]["evidence_basis"]
            if stripped != before[oid]:
                moved.append(oid)
        assert sorted(moved) == sorted(MOVED)
        state = successor["decision_state"]
        assert state["rows_whose_declarations_changed"] == list(MOVED)
        assert state["rows_whose_register_basis_grew"] == sorted(asd.MISS_EVIDENCE_BASIS)
        assert state["revision_plans_added"] == 15

    def test_the_fourteen_strengths_are_carried_through_untouched(
        self, successor, predecessor, esr_kinds
    ):
        before = {str(r["observation_id"]): r for r in predecessor["rows"]}
        strengths = [
            row for row in successor["rows"] if esr_kinds[str(row["observation_id"])] == "strength"
        ]
        assert len(strengths) == 14
        for row in strengths:
            carried = {k: v for k, v in row.items() if k != "review_status"}
            assert carried == before[str(row["observation_id"])]
        assert successor["decision_state"]["rows_carried_through_untouched"] == 14

    def test_esr_e_04_becomes_a_miss_with_both_statuses_unresolved(self, successor):
        row = next(r for r in successor["rows"] if r["observation_id"] == "ESR-E-04")
        assert row["disposition"] == "not_detected_despite_sufficient_preserved_evidence"
        assert "blind_findings" not in row
        assert row["declared_status"] == "Unresolved"
        assert row["evidence_preserved_status"] == "Unresolved"
        assert "A06" in row["explanation"]

    def test_esr_q_01_keeps_two_of_three_citations(self, successor, predecessor):
        before = next(r for r in predecessor["rows"] if r["observation_id"] == "ESR-Q-01")
        after = next(r for r in successor["rows"] if r["observation_id"] == "ESR-Q-01")
        assert len(before["blind_findings"]) == 3 and len(after["blind_findings"]) == 2
        assert all(
            not (ref["sample_index"] == 0 and ref["index"] == 3)
            for ref in after["blind_findings"]
        )
        assert after["disposition"] == before["disposition"]
        assert "A05" in after["explanation"]

    def test_esr_q_03_rests_on_one_audit_finding_in_the_successor_audit(self, successor):
        row = next(r for r in successor["rows"] if r["observation_id"] == "ESR-Q-03")
        assert "blind_findings" not in row
        assert row["audit_findings"] == [
            {
                "report": asd.SUCCESSOR_AUDIT_REL.as_posix(),
                "check": "milestone_dependencies",
                "index": 15,
            }
        ]
        assert row["declared_status"] == "Unresolved"

    def test_every_shortcoming_carries_a_plan_and_no_strength_does(self, successor, esr_kinds):
        for row in successor["rows"]:
            oid = str(row["observation_id"])
            revision = row.get("proposed_revision")
            plan = (revision or {}).get("revision_plan") if isinstance(revision, dict) else None
            if esr_kinds[oid] == "strength":
                assert plan is None, oid
            else:
                assert plan is not None, oid
                assert set(plan) >= set(ec.REVISION_PLAN_FIELDS)
                assert plan["commitment_kind"] in ec.REVISION_COMMITMENT_KINDS

    def test_no_plan_is_editorial(self, successor):
        """Not one of the fifteen can be written from what this copy carries."""
        kinds = {
            row["proposed_revision"]["revision_plan"]["commitment_kind"]
            for row in successor["rows"]
            if isinstance(row.get("proposed_revision"), dict)
            and row["proposed_revision"].get("revision_plan")
        }
        assert ec.REVISION_COMMITMENT_EDITORIAL not in kinds

    def test_a_commitment_names_what_has_to_be_confirmed(self, successor):
        for row in successor["rows"]:
            revision = row.get("proposed_revision")
            plan = (revision or {}).get("revision_plan") if isinstance(revision, dict) else None
            if plan and plan["commitment_kind"] != ec.REVISION_COMMITMENT_EDITORIAL:
                assert plan["requires_confirmation"], row["observation_id"]

    def test_no_miss_claims_confirmed_preservation_while_the_declared_half_is_empty(
        self, successor
    ):
        register = json.loads(REGISTER.read_text(encoding="utf-8-sig"))
        assert register["declared"]["sub_sections"] == []
        for row in successor["rows"]:
            assert row.get("evidence_preserved_status") != "Confirmed", row["observation_id"]

    def test_every_miss_names_its_register_basis(self, successor):
        for row in successor["rows"]:
            if row["disposition"] == "not_detected_despite_sufficient_preserved_evidence":
                assert row.get("evidence_basis"), row["observation_id"]

    def test_the_schema_version_is_the_one_that_enforces_that(self, successor):
        assert successor["schema_version"] == "1.1"
        assert successor["schema_version"] in ec.DISPOSITIONS_SCHEMA_VERSIONS


class TestReviewStatus:
    """Acceptance criterion 2: every successor observation has a traceable
    disposition *and review status*."""

    def test_the_record_declares_the_state_the_module_reads(self, successor):
        assert successor["review_state"] == ec.REVIEW_STATE_AGENT_DRAFTED
        assert successor["review_state"] in ec.RECORD_REVIEW_STATES

    def test_every_row_carries_a_review_status(self, successor):
        for row in successor["rows"]:
            assert row["review_status"] in ec.ROW_REVIEW_STATES, row["observation_id"]

    def test_no_row_is_operator_confirmed(self, successor):
        assert all(r["review_status"] != "operator_confirmed" for r in successor["rows"])

    def test_the_rows_needing_a_decision_are_both_records_questions(self, successor):
        """A successor that marked only its own five would read as if the R03
        review notes' other fourteen were settled."""
        expected = asd.rows_needing_an_operator_decision(REPO)
        marked = {
            str(r["observation_id"]) for r in successor["rows"]
            if r["review_status"] == "operator_decision_required"
        }
        assert marked == expected
        assert len(marked) == 19
        assert successor["decision_state"]["rows_needing_an_operator_decision"] == sorted(expected)
        own = {str(d["observation_id"]) for d in asd.OPEN_OPERATOR_DECISIONS}
        assert own <= marked


# --------------------------------------------------------------------------- #
# Traceability: the plans point at the candidate, not at an invention
# --------------------------------------------------------------------------- #


_LOCATION = re.compile(r"^(?P<section>[a-z_]+)/(?P<sub>[0-9](?:\.[0-9]+)*)")


class TestPlansPointAtTheCandidate:
    def test_every_role_anchor_is_quoted_from_the_sub_section_it_names(self, candidate_text):
        for key, role in asd.ROLES.items():
            section, sub = role["source"].split("/", 1)
            content = candidate_text.get((section, sub))
            assert content is not None, f"{key}: {role['source']} is not a candidate sub-section"
            assert ec.normalise_text(role["anchor"]) in ec.normalise_text(content), key

    def test_every_proposal_location_names_a_sub_section_the_candidate_has(
        self, successor, candidate_text
    ):
        for row in successor["rows"]:
            revision = row.get("proposed_revision")
            plan = (revision or {}).get("revision_plan") if isinstance(revision, dict) else None
            if not plan:
                continue
            for location in plan["proposal_location"]:
                match = _LOCATION.match(location)
                assert match, f"{row['observation_id']}: {location!r} names no sub-section"
                key = (match.group("section"), match.group("sub"))
                assert key in candidate_text, f"{row['observation_id']}: {key} is not in the candidate"

    def test_every_role_used_is_one_of_the_enumerated_ones(self, successor):
        known = {(r["role"], r["source"]) for r in asd.ROLES.values()}
        for row in successor["rows"]:
            revision = row.get("proposed_revision")
            plan = (revision or {}).get("revision_plan") if isinstance(revision, dict) else None
            if not plan:
                continue
            role = plan["responsible_role"]
            assert (role["role"], role["source"]) in known, row["observation_id"]


# --------------------------------------------------------------------------- #
# The comparison written from the successor
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not SUCCESSOR_COMPARISON.is_file(), reason="the successor comparison is absent")
class TestSuccessorComparison:
    def _replay(self, out: Path) -> int:
        argv = [
            "compare",
            "--baseline-dir", str(BASELINE),
            "--esr", str(REPO / asd.ESR_RECORD_REL),
            "--dispositions", str(REPO / asd.SUCCESSOR_REL),
            "--candidate", str(CANDIDATE),
            "--historical-candidate", str(HISTORICAL),
            "--register", str(REGISTER),
            "--audit", str(REPO / asd.SUCCESSOR_AUDIT_REL),
            "--audit", str(REPO / asd.FIRST_REVISION_AUDIT_REL),
            "--repo-root", str(REPO),
            "--profile", str(PROFILE),
            "--out-dir", str(out),
        ]
        return cmd.main(argv, clock=lambda: "2026-10-07T00:00:00+00:00")

    def test_the_committed_comparison_replays_from_its_documented_inputs(self, tmp_path):
        assert self._replay(tmp_path) == 0
        fresh = ec.load_comparison(next(tmp_path.glob("comparison_*.json")))
        recorded = json.loads(SUCCESSOR_COMPARISON.read_text(encoding="utf-8-sig"))
        volatile = {"compared_at", "writes", "revisions_artifact", "baseline"}
        assert {k: v for k, v in fresh.items() if k not in volatile} == {
            k: v for k, v in recorded.items() if k not in volatile
        }
        assert fresh["baseline"]["report_sha256"] == recorded["baseline"]["report_sha256"]

    def test_the_successor_counts_are_the_successor_rows(self, tmp_path):
        recorded = json.loads(SUCCESSOR_COMPARISON.read_text(encoding="utf-8-sig"))
        summary = recorded["summary"]
        by_disposition = summary["by_disposition"]
        from collections import Counter

        counted = Counter(r["disposition"] for r in recorded["rows"])
        assert {k: v for k, v in by_disposition.items() if v} == dict(counted)
        assert summary["observations"] == len(recorded["rows"]) == 29
        assert by_disposition["not_detected_despite_sufficient_preserved_evidence"] == 7
        assert by_disposition["partially_observable"] == 6
        detection = summary["detection"]
        assert detection["rated"] == 14
        assert detection["independently_detected"] == 6
        assert detection["partially_observable"] == 1
        assert detection["not_detected"] == 7
        assert detection["by_lane"] == {"blind_lane": 6, "integrity_audit": 1}

    def test_the_comparison_says_whose_declarations_it_resolved(self):
        recorded = json.loads(SUCCESSOR_COMPARISON.read_text(encoding="utf-8-sig"))
        assert recorded["dispositions"]["review_state"] == ec.REVIEW_STATE_AGENT_DRAFTED
        state = recorded["review_state"]
        assert state["state"] == ec.REVIEW_STATE_AGENT_DRAFTED
        assert len(state["rows_needing_an_operator_decision"]) == 19
        predecessor = json.loads(
            (REPO / asd.PREDECESSOR_COMPARISON_REL).read_text(encoding="utf-8-sig")
        )
        assert "review_state" not in predecessor

    def test_the_two_unresolved_rows_are_named_beside_the_counts(self):
        """They are counted under the disposition they declare; the summary says
        which figures are provisional on an operator decision."""
        recorded = json.loads(SUCCESSOR_COMPARISON.read_text(encoding="utf-8-sig"))
        block = recorded["summary"]["declarations_unresolved"]
        assert block["rows"] == ["ESR-E-04", "ESR-Q-03"]
        assert "§12.2" in block["statement"]
        statuses = {
            str(r["observation_id"]): r["disposition_status"] for r in recorded["rows"]
        }
        assert statuses["ESR-E-04"] == statuses["ESR-Q-03"] == "Unresolved"

    def test_the_historical_scores_are_untouched(self, tmp_path):
        recorded = json.loads(SUCCESSOR_COMPARISON.read_text(encoding="utf-8-sig"))
        predecessor = json.loads(
            (REPO / asd.PREDECESSOR_COMPARISON_REL).read_text(encoding="utf-8-sig")
        )
        assert recorded["score_comparison"] == predecessor["score_comparison"]

    def test_every_shortcoming_is_still_open_in_the_revision_plan(self):
        revisions = json.loads(
            (DN / "comparisons/revisions_f60ae6e0a2a1_0002.json").read_text(encoding="utf-8-sig")
        )
        recorded = json.loads(SUCCESSOR_COMPARISON.read_text(encoding="utf-8-sig"))
        shortcomings = {
            str(r["observation_id"]) for r in recorded["rows"] if r["kind"] != "strength"
        }
        assert shortcomings == {str(e["observation_id"]) for e in revisions["open"]}
        assert all(e["revision_plan"] for e in revisions["open"])
        assert revisions["closed"] == []

    def test_the_predecessor_artifacts_are_untouched(self):
        """R05 writes successors; it never edits what the operator already read."""
        predecessor = json.loads(
            (REPO / asd.PREDECESSOR_COMPARISON_REL).read_text(encoding="utf-8-sig")
        )
        assert predecessor["dispositions"]["path"] == asd.PREDECESSOR_REL.as_posix()
        assert predecessor["dispositions"]["sha256"] == asd._sha256(REPO, asd.PREDECESSOR_REL)


# --------------------------------------------------------------------------- #
# The decision-log record
# --------------------------------------------------------------------------- #


DECISION = Path("docs/tier4_orchestration_state/decision_log/msca-dn-successor-dispositions_2026-10-07.json")


@pytest.mark.skipif(not (REPO / DECISION).is_file(), reason="the R05 decision record is absent")
class TestDecisionRecord:
    def test_every_recorded_hash_is_the_file_on_disk(self):
        """A decision record whose hashes have drifted records a different state."""
        record = _read(DECISION)
        artifacts = record["artifacts"]
        for group in ("written", "unchanged_and_still_cited"):
            for key, entry in artifacts[group].items():
                assert entry["sha256"] == asd._sha256(REPO, Path(entry["path"])), f"{group}/{key}"

    def test_the_replay_inventory_pins_the_inputs_the_command_takes(self):
        record = _read(DECISION)
        inventory = record["artifacts"]["input_inventory_for_the_replay"]
        assert inventory["dispositions_sha256"] == asd._sha256(REPO, asd.SUCCESSOR_REL)
        assert inventory["register_sha256"] == asd._sha256(REPO, asd.REGISTER_REL)
        assert inventory["esr_record_sha256"] == asd._sha256(REPO, asd.ESR_RECORD_REL)
        assert inventory["assessor_calls"] == 0
        for audit in inventory["audits"]:
            assert audit["sha256"] == asd._sha256(REPO, Path(audit["path"]))
