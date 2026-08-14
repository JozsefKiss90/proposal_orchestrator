"""FIELDWISE ticket 7 — authorisation packet acceptance tests.

Pins the durable acceptance criteria of plans/fieldwise_tickets.md ticket 7:

1. The packet enumerates every seeded record with status and source reference.
2. Every remaining Unresolved item is listed with the gate it blocks.
3. Operator authorisation is recorded in the decision log before any phase runs.

Criterion 3 is pinned as an invariant rather than as a fact: the packet may sit
unauthorised, but ``action_confirmation_ref`` and ``action_confirmation_status``
must agree with each other and with the decision log either way.  The operator
authorised the seed on 2026-08-12, so the authorised branch of that invariant is
the live one, and ``TestAuthorisationRecorded`` pins what the record must say.

The file also pins the authorisation-review fold of 2026-08-12 (AR-1 to AR-8),
which answered the AgroVIR placement gap in part and closed three of the four
one-line decisions the packet put to the operator.

Read-only: these tests never write to docs/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TIER3 = REPO_ROOT / "docs" / "tier3_project_instantiation"
TIER4 = REPO_ROOT / "docs" / "tier4_orchestration_state"
PACKET = (
    TIER4
    / "validation_reports"
    / "fieldwise_authorisation_packet_2026-08-12.md"
)
PLACEMENT_RECORD = (
    TIER4 / "decision_log" / "fieldwise-placement-hosting_2026-08-12.json"
)
OPEN_ITEMS_RECORD = (
    TIER4 / "decision_log" / "fieldwise-ticket7-open-items_2026-08-12.json"
)
AUTHORISATION_RECORD = (
    TIER4 / "decision_log" / "fieldwise-authorisation_2026-08-12.json"
)

VALID_STATUSES = {"Confirmed", "Inferred", "Assumed", "Unresolved"}

TIER3_ARTIFACTS = [
    "call_binding/selected_call.json",
    "call_binding/confirmation_checklist.json",
    "project_brief/project_summary.json",
    "project_brief/concept_note.md",
    "project_brief/strategic_positioning.md",
    "architecture_inputs/objectives.json",
    "architecture_inputs/outcomes.json",
    "architecture_inputs/impacts.json",
    "architecture_inputs/workpackage_seed.json",
    "architecture_inputs/milestones_seed.json",
    "architecture_inputs/risks.json",
    "consortium/roles.json",
    "consortium/partners.json",
    "consortium/capabilities.json",
    "working_assumptions.json",
]

# Every Unresolved status field in Tier 3, keyed by its JSON path, mapped to a
# string the packet must contain for that gap to count as listed.  A new
# Unresolved record with no entry here fails the coverage test, which is the
# point: the packet must not silently stop covering the open state.
UNRESOLVED_COVERAGE = {
    # .action_confirmation_status was Unresolved until the operator authorised
    # the seed on 2026-08-12.  It is Confirmed now, so it no longer reaches this
    # map; the entry is kept because a rerun on an unauthorised branch must
    # still find the packet covering it.
    ".action_confirmation_status": "action_confirmation",
    ".participant_capacity[0].recent_projects_and_publications_status":
        "ELTE `recent_projects_and_publications`",
    ".participant_capacity[0].previous_msca_hosting_status":
        "ELTE `previous_msca_hosting`",
    ".participant_capacity[1].recent_projects_and_publications_status":
        "MATE `recent_projects_and_publications`",
    ".participant_capacity[3].relevant_track_record_status":
        "AgroVIR `relevant_track_record`",
    ".participant_capacity[3].key_people[0].title_status":
        "Miklós Maróti's title and seniority",
    ".participant_capacity[3].key_people[1].title_status":
        "Roles and titles for Takács (MATE) and Balázs (AgroVIR)",
    ".participant_capacity[3].hosting_capacity_for_the_placement."
    "validation_status": "AgroVIR workspace and system access",
    ".participant_capacity[3].hosting_capacity_for_the_placement."
    "workspace_and_system_access.validation_status":
        "AgroVIR workspace and system access",
    ".participant_capacity[3].hosting_capacity_status":
        "AgroVIR workspace and system access",
    ".researcher_profile.invited_talks_status": "`invited_talks`",
    ".part_b2_capacity_detail.validation_status": "`part_b2_capacity_detail`",
    ".partners[5].signatory_authority_status": "MVCRI `signatory_authority`",
    ".partners[6].company_registration_number_status":
        "AgroVIR `company_registration_number`",
    ".placement_verification.open_sequencing_question.validation_status":
        "Which point in the timeline D5.4 belongs to",
}


def _load(path: Path) -> dict:
    assert path.is_file(), f"{path.relative_to(REPO_ROOT)} does not exist"
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_statuses(node, path=""):
    """Yield (json_path, key, value) for every four-category status field."""
    if isinstance(node, dict):
        for key, value in node.items():
            if (
                isinstance(value, str)
                and value in VALID_STATUSES
                and (key == "validation_status" or key.endswith("_status"))
            ):
                yield path + "." + key, key, value
            yield from _iter_statuses(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _iter_statuses(value, f"{path}[{index}]")


@pytest.fixture(scope="module")
def packet() -> str:
    assert PACKET.is_file(), f"{PACKET.relative_to(REPO_ROOT)} does not exist"
    return PACKET.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def checklist() -> dict:
    return _load(TIER3 / "call_binding" / "confirmation_checklist.json")


@pytest.fixture(scope="module")
def capabilities() -> dict:
    return _load(TIER3 / "consortium" / "capabilities.json")


class TestPacketLocation:
    """The packet is Tier 4 orchestration state, not a planning file."""

    def test_the_packet_lives_in_tier4(self):
        assert PACKET.is_file()
        assert not (REPO_ROOT / "plans" / "fieldwise_authorisation_packet.md").exists(), (
            "the plans/ copy must not survive the move to Tier 4"
        )

    def test_the_packet_names_its_own_tier_and_ticket(self, packet):
        assert "ticket 7" in packet
        assert "Tier 4" in packet
        assert "fieldwise-run-01" in packet


class TestCriterion1EveryRecordEnumerated:
    """The packet enumerates every seeded record with status and source ref."""

    def test_every_tier3_artifact_is_named(self, packet):
        for artifact in TIER3_ARTIFACTS:
            leaf = artifact.split("/")[-1]
            assert leaf in packet, f"{artifact} is not enumerated in the packet"

    @pytest.mark.parametrize(
        "identifier",
        [f"O{i}" for i in range(1, 7)]
        + [f"WP{i}" for i in range(1, 6)]
        + [f"MS{i}" for i in range(1, 6)]
        + [f"R{i:02d}" for i in range(1, 14)]
        + [f"K{i}" for i in range(1, 12)]
        + [f"EI-0{i}" for i in range(1, 7)]
        + [f"TR{i}" for i in range(1, 7)]
        + [
            "D1.1", "D1.2", "D1.3", "D2.1", "D2.2", "D3.1", "D3.2",
            "D4.1", "D4.2", "D4.3", "D5.1", "D5.2", "D5.3", "D5.4", "D5.5",
        ]
        + [
            "FELLOW", "HOST", "SUPERVISOR", "CO_SUPERVISOR",
            "DATA_PARTNER", "TRANSFER_PARTNER", "VALIDATION_PARTNER",
        ],
    )
    def test_every_record_identifier_appears(self, packet, identifier):
        assert identifier in packet, f"{identifier} is not enumerated"

    @pytest.mark.parametrize(
        "group",
        [
            "OC1 to OC6",
            "T1.1-T1.5",
            "T2.1-T2.6",
            "T3.1-T3.7",
            "T4.1-T4.7",
            "T5.1-T5.7",
        ],
    )
    def test_grouped_identifier_ranges_appear(self, packet, group):
        """Ranges stand in for per-record rows and must name both endpoints."""
        assert group in packet, f"{group} is not enumerated"

    def test_the_status_vocabulary_is_the_four_categories(self, packet):
        for status in sorted(VALID_STATUSES):
            assert status in packet
        assert "§12.2" in packet

    def test_paragraph_references_are_carried(self, packet):
        for anchor in ("¶240-241", "¶317", "¶384-422", "¶21-79"):
            assert anchor in packet, f"source reference {anchor} is missing"

    def test_the_status_totals_match_the_artifacts(self, packet):
        """The totals table is recomputed, not copied forward."""
        counts = {status: 0 for status in VALID_STATUSES}
        for path in sorted(TIER3.rglob("*.json")):
            if "source_materials" in str(path) or "example" in path.name:
                continue
            for _, _, value in _iter_statuses(_load(path)):
                counts[value] += 1
        checklist = _load(TIER3 / "call_binding" / "confirmation_checklist.json")
        for group in ("spine_identity", "superseded_records", "operator_decisions"):
            for record in checklist[group]:
                counts[record["status"]] += 1
        for record in checklist["authorisation_review_decisions"]["decisions"]:
            counts[record["status"]] += 1
        declarations = _load(TIER3 / "working_assumptions.json")["declarations"]
        counts["Assumed"] += len(declarations)
        counts["Confirmed"] += 2  # the two narrative front matters
        total = sum(counts.values())

        for status in sorted(VALID_STATUSES):
            assert f"| {status} | {counts[status]} |" in packet, (
                f"the packet's {status} total is not {counts[status]}"
            )
        assert f"**{total}**" in packet, f"the packet's grand total is not {total}"


class TestCriterion2UnresolvedItemsListedWithTheirGate:
    """Every remaining Unresolved item is listed with the gate it blocks."""

    def test_every_unresolved_record_is_covered_by_the_packet(self, packet):
        missing = []
        for path in sorted(TIER3.rglob("*.json")):
            if "source_materials" in str(path) or "example" in path.name:
                continue
            for json_path, _, value in _iter_statuses(_load(path)):
                if value != "Unresolved":
                    continue
                expected = UNRESOLVED_COVERAGE.get(json_path)
                assert expected is not None, (
                    f"{path.name} {json_path} is Unresolved and has no entry "
                    "in UNRESOLVED_COVERAGE; the packet cannot be shown to "
                    "cover it"
                )
                if expected not in packet:
                    missing.append(f"{path.name} {json_path} -> {expected}")
        assert not missing, "the packet does not list: " + "; ".join(missing)

    def test_the_open_items_in_the_checklist_are_all_in_the_packet(
        self, packet, checklist
    ):
        for entry in checklist["open_for_authorisation"]["items"]:
            assert entry["what"] and entry["why_open"]
        def _normalise(text: str) -> str:
            # The checklist writes prose ("company registration number") and
            # the packet writes field names ("`company_registration_number`").
            # Compare on the words, not on the punctuation.
            return text.lower().replace("_", " ").replace("`", "")

        blob = _normalise(
            json.dumps(
                checklist["open_for_authorisation"]["items"], ensure_ascii=False
            )
        )
        flat_packet = _normalise(packet)
        for token in (
            "c5",
            "workspace",
            "invited talks",
            "pic",
            "signatory",
            "company registration number",
            "background-ip",
        ):
            assert token in blob, f"{token} is not in the checklist open list"
            assert token in flat_packet, f"{token} is not in the packet"

    def test_each_open_item_is_grouped_under_a_gate_verdict(self, packet):
        for heading in (
            "Blocks no gate — costs Part B-1 §3.2",
            "Blocks no gate — the remaining placement gap",
            "Blocks no gate — quality and drafting",
            "Blocks no gate — binds later, outside the run",
            "Blocks submission, not a gate",
            "The one place an open item can fail a gate",
        ):
            assert heading in packet, f"gate grouping '{heading}' is missing"

    def test_the_phase8_exposure_names_its_predicates(self, packet):
        for predicate in (
            "g09a_p06",
            "g09b_p07",
            "g09c_p07",
            "g09a_p11",
            "g09b_p12",
            "g09c_p11",
        ):
            assert predicate in packet

    def test_the_absent_pic_is_reported_as_a_submission_block(self, packet):
        """The g04_p07 finding, verified in the implementation."""
        assert "g04_p07" in packet
        assert "coverage_predicates.py:720" in packet
        partners = _load(TIER3 / "consortium" / "partners.json")["partners"]
        agrovir = next(p for p in partners if p["partner_id"] == "VALIDATION_PARTNER")
        assert agrovir["pic"] is None
        assert agrovir["pic_status"] == "Confirmed"

    def test_the_phase_readiness_table_covers_every_gate(self, packet):
        for gate in (
            "gate_01_source_integrity",
            "phase_01_gate",
            "phase_02_gate",
            "phase_03_gate",
            "phase_04_gate",
            "phase_05_gate",
            "phase_06_gate",
            "gate_09_budget_consistency",
            "gate_10d",
            "gate_11",
            "gate_12",
        ):
            assert gate in packet, f"{gate} has no readiness verdict"


class TestCriterion3AuthorisationRecord:
    """Authorisation is recorded before any phase runs, or not claimed at all."""

    def test_action_confirmation_fields_agree(self):
        call = _load(TIER3 / "call_binding" / "selected_call.json")
        ref = call["action_confirmation_ref"]
        status = call["action_confirmation_status"]
        if ref is None:
            assert status == "Unresolved", (
                "a null action_confirmation_ref may not be Confirmed"
            )
        else:
            assert status == "Confirmed"
            assert (REPO_ROOT / ref).is_file(), (
                f"action_confirmation_ref points at {ref}, which does not exist"
            )

    def test_no_phase_output_exists_before_authorisation(self):
        call = _load(TIER3 / "call_binding" / "selected_call.json")
        if call["action_confirmation_ref"] is not None:
            return
        phase_outputs = TIER4 / "phase_outputs"
        produced = [
            path
            for path in phase_outputs.rglob("*")
            if path.is_file() and path.name != ".gitkeep"
        ]
        assert not produced, (
            "phase outputs exist while the run is unauthorised: "
            + ", ".join(str(p.relative_to(REPO_ROOT)) for p in produced)
        )


class TestAuthorisationRecorded:
    """Criterion 3: the operator authorised the seed on 2026-08-12.

    These tests read the record rather than restate it.  What they pin is that
    the record says what an authorisation must say, that the call binding points
    at it, and that the state it authorised is the state on disk.
    """

    @pytest.fixture(scope="class")
    def record(self) -> dict:
        return _load(AUTHORISATION_RECORD)

    def test_the_record_exists_and_carries_the_envelope(self, record):
        assert record["record_type"] == "decision"
        assert record["date"] == "2026-08-12"
        assert record["branch"] == "fieldwise-run-01"
        assert record["authorised"] is True
        assert record["operator_instruction"]

    def test_the_call_binding_points_at_the_record(self):
        call = _load(TIER3 / "call_binding" / "selected_call.json")
        assert call["action_confirmation_status"] == "Confirmed"
        ref = REPO_ROOT / call["action_confirmation_ref"]
        assert ref.resolve() == AUTHORISATION_RECORD.resolve()

    def test_the_record_names_the_packet_it_authorises(self, record):
        authorised = record["what_was_authorised"]
        packet_ref = REPO_ROOT / authorised["packet"]
        assert packet_ref.resolve() == PACKET.resolve()
        assert authorised["packet_revision"] == 3

    def test_the_record_carries_every_open_item(self, record, checklist):
        """Authorisation lists what it accepted as open, not a summary of it."""
        accepted = record["open_items_accepted"]
        items = accepted["items"]
        assert accepted["count"] == len(items)
        recorded = {entry["what"] for entry in items}
        expected = {
            entry["what"] for entry in checklist["open_for_authorisation"]["items"]
        }
        assert recorded == expected, (
            "the authorisation record and the checklist disagree about what is "
            f"open: {sorted(recorded ^ expected)}"
        )
        for entry in items:
            assert entry["status"] and entry["why_open"]

    def test_the_record_carries_every_declaration(self, record):
        declared = {
            d["key"]
            for d in _load(TIER3 / "working_assumptions.json")["declarations"]
        }
        standing = record["declarations_standing"]
        assert set(standing["keys"]) == declared
        assert standing["count"] == len(declared)

    def test_the_record_states_what_it_does_not_do(self, record):
        limits = record["what_this_authorisation_does_not_do"]
        for key in ("status", "gates", "budget", "submission", "amendment"):
            assert limits[key].strip(), f"{key} limit is not stated"
        assert "waives no gate" in limits["gates"]

    def test_authorisation_promotes_no_status(self, record):
        """The one status that moved is the authorisation field itself."""
        assert "changes no record status" in (
            record["what_this_authorisation_does_not_do"]["status"]
        )
        assert "Assumed" in record["c5_override_carried_without_promotion"]
        checklist = _load(TIER3 / "call_binding" / "confirmation_checklist.json")
        mobility = next(
            r for r in checklist["spine_identity"] if r["id"] == "MOBILITY_ELIGIBILITY"
        )
        assert mobility["status"] == "Assumed"

    def test_the_authorised_state_is_the_state_on_disk(self, record):
        """A fingerprinted artifact that moved must say so in ``amendments``.

        Authorisation is of a state.  If a later ticket edits one of the
        fifteen artifacts, that is allowed and is not a fault — but it must be
        declared in the record, not left for a reader to discover.
        """
        from runner.fingerprints import fingerprint_path

        fingerprints = record["authorised_state_fingerprint"]
        recorded = fingerprints["per_artifact"]
        assert fingerprints["artifact_count"] == len(recorded) == 15

        declared = {
            entry["artifact"] for entry in record["amendments"]
        }
        drifted = [
            path
            for path, digest in sorted(recorded.items())
            if fingerprint_path(REPO_ROOT / path) != digest and path not in declared
        ]
        assert not drifted, (
            "these artifacts changed after authorisation and no amendments entry "
            "declares it: " + ", ".join(drifted)
        )

    def test_the_packet_records_the_authorisation(self, packet):
        assert "AUTHORISED 2026-08-12" in packet
        assert "fieldwise-authorisation_2026-08-12.json" in packet
        assert "## 12. What authorisation recorded" in packet
        assert "Ticket 8 is unblocked" in packet

    def test_the_ticket_marks_criterion_three_met(self):
        ticket = (REPO_ROOT / "plans" / "fieldwise_tickets.md").read_text(
            encoding="utf-8"
        )
        criterion = "Operator authorisation is recorded in the decision log"
        assert f"- [x] {criterion}" in ticket, (
            "ticket 7's third checkbox is not ticked"
        )


class TestAuthorisationReviewFold:
    """AR-1 to AR-8, folded 2026-08-12."""

    def test_both_decision_records_exist_and_parse(self):
        for path in (PLACEMENT_RECORD, OPEN_ITEMS_RECORD):
            record = _load(path)
            assert record["record_type"] == "decision"
            assert record["date"] == "2026-08-12"
            assert record["branch"] == "fieldwise-run-01"

    def test_the_records_do_not_claim_to_authorise(self):
        for path in (PLACEMENT_RECORD, OPEN_ITEMS_RECORD):
            record = _load(path)
            assert "what_this_record_does_not_do" in record
            assert "does not authorise" in record["what_this_record_does_not_do"]

    def test_all_ten_decisions_are_in_the_checklist(self, checklist):
        decisions = checklist["authorisation_review_decisions"]["decisions"]
        assert [d["id"] for d in decisions] == [f"AR-{i}" for i in range(1, 11)]
        for decision in decisions:
            assert decision["status"] in VALID_STATUSES
            assert decision["title"]

    def test_the_placement_supervisor_is_assumed_and_declared(self, capabilities):
        agrovir = next(
            entry
            for entry in capabilities["participant_capacity"]
            if entry["short_name"] == "AgroVIR"
        )
        supervisor = next(
            person
            for person in agrovir["key_people"]
            if person["name"] == "Miklós Maróti"
        )
        assert supervisor["validation_status"] == "Assumed"
        assert supervisor["declaration_key"] == "placement_supervisor_AgroVIR"
        # Title answered by the operator at the 2026-08-14 open-items fold and
        # declared under its own key, on the same footing as the name: still
        # operator-supplied and still not independently verifiable.
        assert supervisor["title"] == "Senior research officer"
        assert supervisor["title_status"] == "Assumed"

    def test_the_workspace_answer_was_not_adopted_as_workspace(self, capabilities):
        agrovir = next(
            entry
            for entry in capabilities["participant_capacity"]
            if entry["short_name"] == "AgroVIR"
        )
        hosting = agrovir["hosting_capacity_for_the_placement"]
        workspace = hosting["workspace_and_system_access"]
        # Answered at the 2026-08-14 open-items fold for three of the four
        # fields and declared; the fourth is named, not inferred.
        assert workspace["validation_status"] == "Assumed"
        assert workspace["declaration_key"] == "placement_workspace_AgroVIR"
        assert len(workspace["answered_fields"]) == 3
        assert workspace["missing_fields"] == ["The team she joins"]
        # The rejected field-access answer is still rejected as workspace: the
        # fold answered the question asked, it did not retrofit the old answer.
        assert "not adopted" in workspace["supplied_answer_not_adopted"].lower()
        # The supplied field-access answer survives, as a supplementary fact.
        supplementary = hosting["supplementary_field_access"]
        assert supplementary["validation_status"] == "Confirmed"
        assert "supplementary" in supplementary["note"].lower()

    def test_the_work_content_invents_no_deliverable(self, capabilities):
        agrovir = next(
            entry
            for entry in capabilities["participant_capacity"]
            if entry["short_name"] == "AgroVIR"
        )
        content = agrovir["hosting_capacity_for_the_placement"][
            "six_month_work_content"
        ]
        assert content["validation_status"] == "Confirmed"
        assert len(content["items"]) == 4
        assert "decision_log/" in content["source_ref"]

        wp_seed = _load(TIER3 / "architecture_inputs" / "workpackage_seed.json")
        known = {
            d["deliverable_id"]
            for wp in wp_seed["work_packages"]
            for d in wp["deliverables"]
        }
        for deliverable in ("D5.4", "D5.5"):
            assert deliverable in known
        assert len(known) == 15, "the placement fold must add no deliverable"

    def test_d5_1_precedes_the_placement_window(self):
        wp_seed = _load(TIER3 / "architecture_inputs" / "workpackage_seed.json")
        wp5 = next(wp for wp in wp_seed["work_packages"] if wp["id"] == "WP5")
        check = wp5["deliverable_sequencing_check"]
        assert check["validation_status"] == "Inferred"
        milestones = _load(TIER3 / "architecture_inputs" / "milestones_seed.json")
        ms5 = next(m for m in milestones["milestones"] if m["milestone_id"] == "MS5")
        assert ms5["due_month"] == 23 < 25, (
            "MS5 is what forces D5.1 before the M25-M30 window"
        )

    def test_k11_is_confirmed_and_traces_to_d1_3(self):
        impacts = _load(TIER3 / "architecture_inputs" / "impacts.json")
        k11 = next(k for k in impacts["kpis"]["items"] if k["kpi_id"] == "K11")
        assert k11["validation_status"] == "Confirmed"
        assert k11["traceable_to_deliverable"] == "D1.3"
        assert "decision_log/" in k11["source_ref"]

    def test_every_deliverable_now_carries_a_kpi(self):
        impacts = _load(TIER3 / "architecture_inputs" / "impacts.json")
        tracked = {k["traceable_to_deliverable"] for k in impacts["kpis"]["items"]}
        assert "D1.3" in tracked, "D1.3 was the deliverable with no KPI"

    def test_the_co_supervisor_figure_is_confirmed_at_two(self):
        wp_seed = _load(TIER3 / "architecture_inputs" / "workpackage_seed.json")
        in_kind = wp_seed["person_months"]["partner_in_kind_effort"]
        entries = {e["role_token"]: e["person_months"] for e in in_kind["entries"]}
        assert entries["CO_SUPERVISOR"] == 2.0
        assert round(sum(entries.values()), 2) == in_kind["total"] == 11.4
        contradiction = in_kind["co_supervisor_figure_contradiction"]
        assert "2026-08-12" in contradiction["operator_confirmation"]
        # Operator confirmation of a reading does not promote an estimate.
        assert in_kind["validation_status"] == "Assumed"

    def test_the_m27_steering_point_exists(self):
        milestones = _load(TIER3 / "architecture_inputs" / "milestones_seed.json")
        points = milestones["steering_decision_points"]
        months = [p["month"] for p in points["points"]]
        assert months == [6, 12, 16, 20, 27]
        monitoring = milestones["placement_period_monitoring"]
        assert monitoring["validation_status"] == "Confirmed"
        assert monitoring["reversal_note"], (
            "AR-7 declined the milestone and AR-9 adopted it; the reversal "
            "must stay legible"
        )

    def test_the_governance_record_carries_the_amended_schedule(self, checklist):
        item4 = next(
            d for d in checklist["operator_decisions"] if d["item"] == 4
        )
        assert "M27" in item4["decision"]["governance_body"]
        assert "M27" in item4["decision"]["governance_body_amendment"]

    def test_the_career_plan_gains_an_m27_review(self, checklist):
        """AR-10: five steering points and five plan reviews, not four."""
        item6 = next(
            d for d in checklist["operator_decisions"] if d["item"] == 6
        )
        assert item6["decision"]["review_points"] == [6, 12, 16, 20, 27]
        assert item6["decision"]["review_points_amendment"]

    def test_no_record_still_claims_four_review_points(self):
        """The AR-10 knock-ons: every record carrying the count reads five."""
        impacts = _load(TIER3 / "architecture_inputs" / "impacts.json")
        k11 = next(k for k in impacts["kpis"]["items"] if k["kpi_id"] == "K11")
        assert "five steering points" in k11["target"]
        assert "four" not in k11["target"]

        for name in ("outcomes.json", "workpackage_seed.json"):
            blob = (TIER3 / "architecture_inputs" / name).read_text(
                encoding="utf-8"
            )
            assert "M6/M12/M16/M20/M27" in blob, (
                f"{name} still describes four Career Development Plan reviews"
            )
            assert "M6/M12/M16/M20." not in blob

        milestones = _load(TIER3 / "architecture_inputs" / "milestones_seed.json")
        consequence = milestones["steering_decision_points"]["consequence"]
        assert "five points" in consequence

    def test_the_item6_decision_record_is_amended_not_rewritten(self):
        record = _load(
            TIER4
            / "decision_log"
            / "fieldwise-item6-career-development-plan_2026-08-12.json"
        )
        # The decision text states what was decided on 2026-08-11 and stands.
        assert "M6, M12, M16 and M20 alongside" in record["decision"]
        amendment = record["amended_by"]
        assert amendment["decision_id"] == "AR-10"
        assert "M27" in amendment["what"]


class TestPlacementVerification:
    """AR-9: the placement window carries a milestone and a named evidence base."""

    def test_ms6_is_seeded_as_inferred_with_its_derivation(self):
        milestones = _load(TIER3 / "architecture_inputs" / "milestones_seed.json")
        ms6 = next(
            m for m in milestones["milestones"] if m["milestone_id"] == "MS6"
        )
        assert ms6["due_month"] == 30
        assert ms6["validation_status"] == "Inferred", (
            "MS6 has no draft source and may not be Confirmed"
        )
        assert "¶" not in ms6["source_ref"], (
            "MS6 must not claim a draft paragraph"
        )
        assert "decision_log/" in ms6["source_ref"]
        assert ms6["carried_by_deliverables"] == ["D5.4", "D5.5"]
        assert ms6["supersedes"], "the AR-7 reversal must be stated"

    def test_ms6_invents_no_deliverable_task_or_month(self):
        wp_seed = _load(TIER3 / "architecture_inputs" / "workpackage_seed.json")
        wp5 = next(wp for wp in wp_seed["work_packages"] if wp["id"] == "WP5")
        assert wp5["end_month"] == 30, "MS6's month is WP5's end month"
        deliverables = {
            d["deliverable_id"]
            for wp in wp_seed["work_packages"]
            for d in wp["deliverables"]
        }
        assert len(deliverables) == 15
        tasks = [t for wp in wp_seed["work_packages"] for t in wp["tasks"]]
        assert len(tasks) == 32

    def test_the_verification_names_the_deliverables_that_carry_it(self):
        milestones = _load(TIER3 / "architecture_inputs" / "milestones_seed.json")
        verification = milestones["placement_verification"]
        assert verification["validation_status"] == "Confirmed"
        assert "D5.4" in verification["statement"]
        assert "D5.5" in verification["statement"]
        assert "g05_p05" in verification["gate_position"]

    def test_the_d5_4_double_claim_is_recorded_unresolved(self, packet):
        milestones = _load(TIER3 / "architecture_inputs" / "milestones_seed.json")
        question = milestones["placement_verification"][
            "open_sequencing_question"
        ]
        assert question["validation_status"] == "Unresolved"
        assert "MS5" in question["what"] and "D5.4" in question["what"]
        assert question["not_resolved_here"]
        assert "D5.4" in packet, "the packet must carry the sequencing question"

    def test_both_ar9_and_ar10_are_in_the_round2_record(self):
        record = _load(
            TIER4
            / "decision_log"
            / "fieldwise-ticket7-review-round2_2026-08-12.json"
        )
        assert [d["id"] for d in record["decisions"]] == ["AR-9", "AR-10"]
        assert "does not authorise" in record["what_this_record_does_not_do"]
        first_round = _load(
            TIER4 / "decision_log" / "fieldwise-ticket7-open-items_2026-08-12.json"
        )
        assert first_round["superseded_in_part_by"]["record"].endswith(
            "fieldwise-ticket7-review-round2_2026-08-12.json"
        )

    def test_invited_talks_closed_as_a_confirmed_absence(self, capabilities):
        """Closed at the 2026-08-14 fold, on the terms the field itself set.

        The standing note made the closing action explicit — 'supply or confirm
        none' — on the ground that 'not supplied' and 'there are none' are
        different facts and only the second can be written into §1.4.  The
        operator confirmed the second, so this is a Confirmed absence rather
        than a deferral, and the record must still carry the deferral history.
        """
        profile = capabilities["researcher_profile"]
        assert profile["invited_talks"] == "None to date."
        assert profile["invited_talks_status"] == "Confirmed"
        note = profile["invited_talks_note"]
        assert "2026-08-12" in note, "the deferral history must survive"
        assert "2026-08-14" in note, "the closing date must be named"


class TestInvariantsThePacketRestsOn:
    """What the packet asserts about Tier 3 must be true of Tier 3."""

    def test_every_declaration_key_referenced_in_tier3_exists(self):
        declarations = {
            d["key"]
            for d in _load(TIER3 / "working_assumptions.json")["declarations"]
        }
        referenced = set()

        def walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "declaration_key" and isinstance(value, str):
                        referenced.add(value)
                    if key == "assumed_declarations" and isinstance(value, list):
                        referenced.update(v for v in value if isinstance(v, str))
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        for path in sorted(TIER3.rglob("*.json")):
            if "source_materials" in str(path) or "example" in path.name:
                continue
            walk(_load(path))

        assert not referenced - declarations, (
            f"dangling declaration keys: {sorted(referenced - declarations)}"
        )
        assert not declarations - referenced, (
            f"declarations backing nothing: {sorted(declarations - referenced)}"
        )

    def test_the_c5_override_is_never_promoted_to_confirmed(self, capabilities):
        checklist = _load(TIER3 / "call_binding" / "confirmation_checklist.json")
        record = next(
            r for r in checklist["spine_identity"] if r["id"] == "MOBILITY_ELIGIBILITY"
        )
        assert record["status"] == "Assumed"
        profile_status = capabilities["researcher_profile"]["mobility_eligibility"][
            "validation_status"
        ]
        assert profile_status == "Assumed"
        declaration = next(
            d
            for d in _load(TIER3 / "working_assumptions.json")["declarations"]
            if d["key"] == "mobility_eligibility"
        )
        assert declaration["declared_by"].startswith("operator")

    def test_the_c5_basis_and_date_are_carried_into_the_packet(self, packet):
        assert "7.05" in packet and "15.81" in packet and "8.76" in packet
        assert "2026-08-11" in packet
        assert "promoted to Confirmed" in packet

    def test_the_duration_is_confirmed_in_the_call_binding_only(self):
        call = _load(TIER3 / "call_binding" / "selected_call.json")
        assert call["project_duration_months"] == 30
        assert call["project_duration_status"] == "Confirmed"
        assert call["max_project_duration_months"] == 36
        declarations = {
            d["key"]
            for d in _load(TIER3 / "working_assumptions.json")["declarations"]
        }
        assert "project_duration_months" not in declarations
        assert "host_country" not in declarations

    def test_the_stale_c5_wording_is_corrected_everywhere(self):
        summary = _load(TIER3 / "project_brief" / "project_summary.json")
        note = summary["spine_note"]
        assert "overrode" in note
        assert "mobility_eligibility" in note
        call = _load(TIER3 / "call_binding" / "selected_call.json")
        assert "overrode" in call["notes"]

    def test_the_provenance_manifest_covers_the_ticket7_artifacts(self):
        manifest = _load(TIER3 / "hand_lift_provenance.json")
        review = manifest["authorisation_review_artifacts"]
        covered = {entry["artifact"] for entry in review["artifacts"]}
        for artifact in (
            "consortium/capabilities.json",
            "architecture_inputs/impacts.json",
            "architecture_inputs/milestones_seed.json",
            "architecture_inputs/workpackage_seed.json",
            "working_assumptions.json",
            "call_binding/confirmation_checklist.json",
            "project_brief/project_summary.json",
        ):
            assert artifact in covered, f"{artifact} is not in the manifest"
        # selected_call.json was the one artifact the reviews did not touch,
        # because authorisation is a separate act.  It joined the block when
        # the operator authorised the seed.
        assert "call_binding/selected_call.json" in covered
        assert "Nothing" in review["not_written"]
