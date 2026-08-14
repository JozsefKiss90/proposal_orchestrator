"""FIELDWISE ticket 6 — operator-answer fold acceptance tests.

Pins the five acceptance criteria of plans/fieldwise_tickets.md ticket 6:

1. No consortium record remains Unresolved for a reason the input pack answered.
2. Every Assumed fact in Tier 3 has a matching declaration in
   ``working_assumptions.json``.
3. ``confirmation_checklist.json`` covers the identity spine and every operator
   decision.
4. Items the operator deferred remain Unresolved and are listed for the
   authorisation packet.
5. Each of the eight decision items has a decision-log record.

Read-only: these tests never write to docs/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TIER3 = REPO_ROOT / "docs" / "tier3_project_instantiation"
CONSORTIUM = TIER3 / "consortium"
ARCHITECTURE = TIER3 / "architecture_inputs"
CALL_BINDING = TIER3 / "call_binding"
DECISION_LOG = (
    REPO_ROOT / "docs" / "tier4_orchestration_state" / "decision_log"
)

VALID_STATUSES = {"Confirmed", "Inferred", "Assumed", "Unresolved"}

#: The pack copy ticket 2 instructs ticket 6 to place in Tier 3.
INPUT_PACK_IN_TIER3 = (
    TIER3 / "source_materials" / "operator_input_pack"
    / "fieldwise_operator_input_pack.md"
)

#: The eight items the input pack offered a drafted candidate for, and the
#: decision-log record each one must have.
DECISION_ITEM_RECORDS = {
    3: "fieldwise-item3-ethics_2026-08-12.json",
    4: "fieldwise-item4-governance_2026-08-12.json",
    5: "fieldwise-item5-kpis_2026-08-12.json",
    6: "fieldwise-item6-career-development-plan_2026-08-12.json",
    8: "fieldwise-item8-person-months_2026-08-12.json",
    9: "fieldwise-item9-unit-cost-lines_2026-08-12.json",
    13: "fieldwise-item13-security-green-charter_2026-08-12.json",
    14: "fieldwise-item14-page-budget_2026-08-12.json",
}

#: The three organisations items 1 and 2 answered.
ANSWERED_PARTICIPANTS = {
    "DATA_PARTNER": "MATE",
    "TRANSFER_PARTNER": "MVCRI",
    "VALIDATION_PARTNER": "AgroVIR",
}

#: Every checklist_ref token Tier 3 carries must resolve in the checklist.
SPINE_TOKENS = [
    "FELLOW",
    "HOST",
    "SUPERVISOR",
    "CO_SUPERVISOR",
    "DATA_PARTNER",
    "TRANSFER_PARTNER",
    "VALIDATION_PARTNER",
    "FELLOWSHIP_TYPE",
    "DURATION",
    "CALL_BINDING",
    "MOBILITY_ELIGIBILITY",
]

#: Fields the operator deferred in item 12, which must stay Unresolved.
DEFERRED_CAPACITY_FIELDS = [
    "ELTE recent_projects_and_publications",
    "ELTE previous_msca_hosting",
    "MATE recent_projects_and_publications",
    "AgroVIR key_people",
    "AgroVIR relevant_track_record",
]


def _load(path: Path) -> dict:
    assert path.is_file(), f"{path.relative_to(REPO_ROOT)} does not exist"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _iter_status_records(obj, path="$"):
    """Yield (json_path, record) for every dict carrying validation_status."""
    if isinstance(obj, dict):
        if "validation_status" in obj:
            yield path, obj
        for key, value in obj.items():
            yield from _iter_status_records(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _iter_status_records(item, f"{path}[{i}]")


def _iter_status_fields(obj, path="$"):
    """Yield (json_path, key, value) for every ``*_status`` string field."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.endswith("_status") and isinstance(value, str):
                yield f"{path}.{key}", key, value
            yield from _iter_status_fields(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _iter_status_fields(item, f"{path}[{i}]")


@pytest.fixture(scope="module")
def partners() -> dict:
    return _load(CONSORTIUM / "partners.json")


@pytest.fixture(scope="module")
def roles() -> dict:
    return _load(CONSORTIUM / "roles.json")


@pytest.fixture(scope="module")
def capabilities() -> dict:
    return _load(CONSORTIUM / "capabilities.json")


@pytest.fixture(scope="module")
def checklist() -> dict:
    return _load(CALL_BINDING / "confirmation_checklist.json")


@pytest.fixture(scope="module")
def declarations():
    """The parsed working_assumptions.json, read through the shared reader."""
    from runner.working_assumptions import load_working_assumptions

    return load_working_assumptions(REPO_ROOT)


class TestInputPackInTier3:
    def test_pack_copied_into_tier3_source_materials(self):
        assert INPUT_PACK_IN_TIER3.is_file(), (
            "ticket 2 instructs ticket 6 to copy the completed pack into "
            "source_materials/operator_input_pack/ as the lift source"
        )

    def test_copy_matches_the_authored_form(self):
        authored = REPO_ROOT / "plans" / "fieldwise_operator_input_pack.md"
        assert INPUT_PACK_IN_TIER3.read_bytes() == authored.read_bytes()


class TestCriterion1NoAnsweredRecordStaysUnresolved:
    @pytest.mark.parametrize("token", sorted(ANSWERED_PARTICIPANTS))
    def test_partner_record_is_no_longer_unresolved(self, partners, token):
        record = next(
            p for p in partners["partners"] if p["partner_id"] == token
        )
        assert record["validation_status"] == "Confirmed"

    @pytest.mark.parametrize("token", sorted(ANSWERED_PARTICIPANTS))
    def test_role_record_is_no_longer_unresolved(self, roles, token):
        record = next(r for r in roles["roles"] if r["role_token"] == token)
        assert record["validation_status"] == "Confirmed"

    @pytest.mark.parametrize("token", sorted(ANSWERED_PARTICIPANTS))
    def test_legal_name_and_participation_mode_are_folded(
        self, partners, roles, token
    ):
        partner = next(
            p for p in partners["partners"] if p["partner_id"] == token
        )
        role = next(r for r in roles["roles"] if r["role_token"] == token)
        for record in (partner, role):
            assert record["legal_name"], f"{token} legal_name not folded"
            assert record["participation_mode"] in {
                "associated_partner",
                "non_academic_placement_host",
            }

    def test_the_two_verified_pics_are_present(self, partners):
        by_id = {p["partner_id"]: p for p in partners["partners"]}
        assert by_id["DATA_PARTNER"]["pic"] == "891269563"
        assert by_id["TRANSFER_PARTNER"]["pic"] == "999533009"

    def test_agrovir_pic_is_confirmed_absent_not_guessed(self, partners):
        agrovir = next(
            p
            for p in partners["partners"]
            if p["partner_id"] == "VALIDATION_PARTNER"
        )
        assert agrovir["pic"] is None
        assert agrovir["pic_status"] == "Confirmed"
        assert "Participant Register" in agrovir["pic_note"]

    def test_agrovir_is_the_placement_host_for_six_months(self, partners):
        agrovir = next(
            p
            for p in partners["partners"]
            if p["partner_id"] == "VALIDATION_PARTNER"
        )
        assert agrovir["participation_mode"] == "non_academic_placement_host"
        assert agrovir["placement_months"] == 6

    def test_kpis_are_folded_with_a_deliverable_each(self):
        impacts = _load(ARCHITECTURE / "impacts.json")
        kpis = impacts["kpis"]
        assert kpis["validation_status"] == "Confirmed"
        confirmed = {
            k["kpi_id"]
            for k in kpis["items"]
            if k["validation_status"] == "Confirmed"
        }
        # K1-K10 are what the ticket 6 fold confirmed from input pack item 5.
        # K11 was raised there and left undecided; ticket 7 decided it, so it
        # may be Confirmed too and is pinned by the ticket 7 test instead.
        assert {f"K{i}" for i in range(1, 11)} <= confirmed
        wp_seed = _load(ARCHITECTURE / "workpackage_seed.json")
        known = {
            d["deliverable_id"]
            for wp in wp_seed["work_packages"]
            for d in wp["deliverables"]
        }
        for kpi in kpis["items"]:
            assert kpi["traceable_to_deliverable"] in known, (
                f"{kpi['kpi_id']} names a deliverable that does not exist in "
                f"workpackage_seed.json"
            )

    def test_all_six_expected_impacts_are_mapped(self):
        impacts = _load(ARCHITECTURE / "impacts.json")
        coverage = impacts["expected_impact_coverage"]
        assert coverage["validation_status"] == "Confirmed"
        mapped = {m["expected_impact_id"] for m in coverage["mappings"]}
        tier2b = _load(
            REPO_ROOT
            / "docs"
            / "tier2b_topic_and_call_sources"
            / "extracted"
            / "expected_impacts.json"
        )
        assert mapped == {i["impact_id"] for i in tier2b["impacts"]}
        for mapping in coverage["mappings"]:
            assert mapping["mapped_measure"], (
                f"{mapping['expected_impact_id']} carries no measure"
            )

    def test_ei04_carries_no_hrs4r_claim(self):
        """C8: ELTE does not hold the award; the claim is removed permanently."""
        impacts = _load(ARCHITECTURE / "impacts.json")
        ei04 = next(
            m
            for m in impacts["expected_impact_coverage"]["mappings"]
            if m["expected_impact_id"] == "EI-04"
        )
        assert "HR Excellence in Research" not in ei04["mapped_measure"]
        assert "HRS4R" not in ei04["mapped_measure"]

    def test_person_months_are_folded_and_total_the_duration(self):
        wp_seed = _load(ARCHITECTURE / "workpackage_seed.json")
        person_months = wp_seed["person_months"]
        assert person_months["validation_status"] == "Confirmed"
        fellow = person_months["fellow_allocation"]
        total = sum(a["person_months"] for a in fellow["allocations"])
        assert total == pytest.approx(fellow["total"])
        call = _load(CALL_BINDING / "selected_call.json")
        assert total == pytest.approx(call["project_duration_months"])

    def test_wp5_and_task_months_reach_the_placement_window(self):
        wp_seed = _load(ARCHITECTURE / "workpackage_seed.json")
        wp5 = next(w for w in wp_seed["work_packages"] if w["id"] == "WP5")
        assert wp5["end_month"] == 30
        assert wp5["draft_end_month"] == 24
        duration = _load(CALL_BINDING / "selected_call.json")[
            "project_duration_months"
        ]
        allocations = wp_seed["task_month_allocation"]["allocations"]
        assert all(a["end_month"] <= duration for a in allocations)
        wp5_tasks = [
            a for a in allocations if a["task_id"].startswith("T5.")
        ]
        assert {a["end_month"] for a in wp5_tasks} == {30}


class TestCriterion2EveryAssumedFactIsDeclared:
    def test_declaration_file_parses_and_is_operator_owned(self, declarations):
        assert declarations.present
        assert not declarations.is_empty
        for decl in declarations.declarations:
            assert decl.declared_by
            assert decl.declared_on
            assert decl.rationale, f"{decl.key} declares no rationale"

    def test_every_declaration_key_is_referenced_by_a_tier3_record(
        self, declarations
    ):
        tier3_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(TIER3.rglob("*.json"))
            if path.name
            not in {"working_assumptions.json", "working_assumptions.example.json"}
        )
        for decl in declarations.declarations:
            assert decl.key in tier3_text, (
                f"declaration {decl.key!r} backs no Tier 3 record"
            )

    def test_every_assumed_person_month_names_its_declaration(
        self, declarations
    ):
        wp_seed = _load(ARCHITECTURE / "workpackage_seed.json")
        in_kind = wp_seed["person_months"]["partner_in_kind_effort"]
        assert in_kind["validation_status"] == "Assumed"
        for entry in in_kind["entries"]:
            assert entry["validation_status"] == "Assumed"
            decl = declarations.declaration(entry["declaration_key"])
            assert decl is not None, (
                f"{entry['organisation']} names an undeclared key"
            )
            assert decl.value == pytest.approx(entry["person_months"])
        assert sum(e["person_months"] for e in in_kind["entries"]) == (
            pytest.approx(in_kind["total"])
        )

    def test_the_three_optional_budget_lines_are_declared(self, declarations):
        for key in (
            "family_allowance",
            "long_term_leave_allowance",
            "special_needs_allowance",
        ):
            decl = declarations.declaration(key)
            assert decl is not None, f"{key} is not declared"
            assert decl.value == "does not apply"
            assert decl.checklist_ref == "BUDGET_OPTIONAL_LINES"

    def test_the_mobility_fact_is_confirmed_and_no_longer_declared(
        self, declarations, checklist
    ):
        """C5 was promoted to Confirmed by operator override on 2026-08-14.

        Until then this asserted the opposite, on the rule that a declaration
        never makes a fact Confirmed.  The operator's explicit instruction
        outranks that rule (CLAUDE.md §3).  What must still hold is the
        *exclusivity*: the fact is held in exactly one register.  A Confirmed
        record with a live declaration behind it would report Assumed through
        every machine surface while Tier 3 read Confirmed.
        """
        record = next(
            r
            for r in checklist["spine_identity"]
            if r["id"] == "MOBILITY_ELIGIBILITY"
        )
        assert record["status"] == "Confirmed"
        assert declarations.declaration("mobility_eligibility") is None, (
            "a Confirmed fact must not also be declared — the reader stamps "
            "every declaration Assumed"
        )

    def test_duration_and_host_country_stay_in_the_call_binding(
        self, declarations
    ):
        """A Confirmed call-binding fact must not be re-declared as Assumed."""
        assert declarations.declaration("project_duration_months") is None
        assert declarations.declaration("DURATION") is None
        assert declarations.declaration("host_country") is None
        call = _load(CALL_BINDING / "selected_call.json")
        assert call["project_duration_months"] == 30
        assert call["project_duration_status"] == "Confirmed"
        assert call["host_country"] == "HU"
        assert call["host_country_status"] == "Confirmed"

    @pytest.mark.parametrize(
        "name",
        [
            "consortium/partners.json",
            "consortium/roles.json",
            "consortium/capabilities.json",
            "architecture_inputs/impacts.json",
            "architecture_inputs/workpackage_seed.json",
            "architecture_inputs/milestones_seed.json",
        ],
    )
    def test_status_vocabulary_stays_closed(self, name):
        data = _load(TIER3 / name)
        for path, record in _iter_status_records(data):
            assert record["validation_status"] in VALID_STATUSES, (
                f"{name} {path} carries an unknown status"
            )
        for path, key, value in _iter_status_fields(data):
            if key in {"validation_status", "spine_status"}:
                continue
            assert value in VALID_STATUSES, (
                f"{name} {path} carries an unknown status {value!r}"
            )


class TestCriterion3ChecklistCoverage:
    def test_checklist_is_fieldwise_and_cites_the_in_tier_pack(self, checklist):
        assert checklist["record_type"] == "spine_confirmation_checklist"
        assert checklist["project"] == "FIELDWISE"
        assert "operator_input_pack" in checklist["source"]
        assert "13B" not in json.dumps(checklist, ensure_ascii=False), (
            "no demo-run provenance may re-enter the checklist"
        )

    @pytest.mark.parametrize("token", SPINE_TOKENS)
    def test_every_spine_token_is_registered(self, checklist, token):
        ids = {r["id"] for r in checklist["spine_identity"]}
        assert token in ids

    def test_every_spine_record_carries_a_valid_status_and_source(
        self, checklist
    ):
        for record in checklist["spine_identity"]:
            assert record["status"] in VALID_STATUSES
            assert record["confirmation_source"]

    def test_every_checklist_ref_in_tier3_resolves(self, checklist):
        known = {r["id"] for r in checklist["spine_identity"]}
        known |= {
            r
            for record in checklist["operator_decisions"]
            for r in [record.get("checklist_ref_resolved")]
            if r
        }
        referenced = set()
        for path in sorted(TIER3.rglob("*.json")):
            if path.name == "working_assumptions.example.json":
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            for _, record in _iter_status_records(data):
                ref = record.get("checklist_ref")
                if isinstance(ref, str):
                    referenced.add(ref)
            if path.name == "workpackage_seed.json":
                for wp in data["work_packages"]:
                    for deliverable in wp["deliverables"]:
                        ref = deliverable.get("checklist_ref")
                        if isinstance(ref, str):
                            referenced.add(ref)
        assert referenced, "no checklist_ref tokens found in Tier 3"
        assert referenced <= known, (
            f"unresolved checklist_ref tokens: {sorted(referenced - known)}"
        )

    @pytest.mark.parametrize("item", sorted(DECISION_ITEM_RECORDS))
    def test_every_decision_item_is_registered(self, checklist, item):
        items = {d["item"] for d in checklist["operator_decisions"]}
        assert item in items

    def test_the_deferred_and_answered_items_are_registered_too(
        self, checklist
    ):
        items = {d["item"] for d in checklist["operator_decisions"]}
        assert {10, 11, 12} <= items

    def test_every_decision_record_carries_a_status_and_a_source(
        self, checklist
    ):
        for record in checklist["operator_decisions"]:
            assert record["status"] in VALID_STATUSES
            assert record["decision"]
            assert record.get("source_ref") or record.get("decision_record")

    def test_the_superseded_demo_run_records_are_registered(self, checklist):
        ids = {r["id"] for r in checklist["superseded_records"]}
        assert {"DATA_PROVIDERS", "RQ1_TO_RQ10"} == ids


class TestCriterion4DeferredItemsStayUnresolvedAndListed:
    def test_the_five_deferred_capacity_fields_are_named(self, capabilities):
        """All five fields the operator deferred on 2026-08-11 stay accounted for.

        Ticket 7 answered one of the five, AgroVIR key_people, in part. The
        ticket 6 guarantee is that no deferred field disappears silently, so
        each of the five must still be named somewhere on this record: four as
        still deferred, and any that were later answered as answered.
        """
        detail = capabilities["part_b2_capacity_detail"]
        assert detail["validation_status"] == "Unresolved"
        still_deferred = detail["deferred_fields_named_by_the_operator"]
        answered = detail.get("answered_in_part_at_ticket_7", [])
        accounted = " | ".join(still_deferred + answered)
        for field in DEFERRED_CAPACITY_FIELDS:
            assert field in accounted, (
                f"{field} was deferred on 2026-08-11 and is no longer named"
            )

    def test_the_deferred_fields_are_null_on_their_own_records(
        self, capabilities
    ):
        by_short_name = {
            entry["short_name"]: entry
            for entry in capabilities["participant_capacity"]
        }
        # AgroVIR key_people was the fifth. Ticket 7 answered it in part, so it
        # is pinned by the ticket 7 test rather than here.  ELTE
        # previous_msca_hosting was the sixth: the operator answered it at the
        # 2026-08-14 open-items fold, so it moved to Assumed and is asserted
        # below rather than here.  Only the organisations themselves can supply
        # what is left, so these three stay null and named.
        expected_unresolved = [
            ("ELTE", "recent_projects_and_publications"),
            ("MATE", "recent_projects_and_publications"),
            ("AgroVIR", "relevant_track_record"),
        ]
        for short_name, field in expected_unresolved:
            entry = by_short_name[short_name]
            assert entry[field] is None, f"{short_name} {field} was guessed"
            assert entry[f"{field}_status"] == "Unresolved"

        # Answered 2026-08-14 as a stated absence and declared, not Confirmed:
        # the ELTE research office holds the institutional record.
        elte = by_short_name["ELTE"]
        assert elte["previous_msca_hosting_status"] == "Assumed"
        assert elte["previous_msca_hosting"] is not None
        # The distinction the field protected throughout must survive: an
        # application at ELTE is not a funded hosting.
        assert "PLANTDIGISENSE" in elte["previous_msca_hosting_note"]

    def test_answered_capacity_fields_are_filled(self, capabilities):
        elte = next(
            e
            for e in capabilities["participant_capacity"]
            if e["short_name"] == "ELTE"
        )
        assert elte["hosting_arrangements_status"] == "Confirmed"
        assert elte["hosting_arrangements_and_support_services"]
        mvcri = next(
            e
            for e in capabilities["participant_capacity"]
            if e["short_name"] == "MVCRI"
        )
        assert mvcri["recent_projects_and_publications_status"] == "Confirmed"

    def test_the_researcher_cv_is_folded_with_its_open_fields_named(
        self, capabilities
    ):
        cv = capabilities["researcher_profile"]
        assert cv["validation_status"] == "Confirmed"
        # The ORCID stays Assumed: supplied by the operator and still not
        # independently verifiable through any of the three routes tried.
        assert cv["orcid_status"] == "Assumed"
        # invited_talks was the CV's one Unresolved field.  The operator closed
        # it at the 2026-08-14 fold by confirming the absence, which is the one
        # form of answer the field's own note said §1.4 could use.
        assert cv["invited_talks_status"] == "Confirmed"
        assert cv["invited_talks"] == "None to date."

    def test_undecided_candidates_are_not_folded_as_accepted(self):
        """A candidate may only leave Unresolved by an operator decision.

        Ticket 6 left K11 and the placement-window monitoring undecided. Ticket
        7 closed both, so the durable guarantee is no longer that they are
        Unresolved: it is that neither turned Confirmed without an operator
        decision record behind it, and that no milestone was invented for the
        placement window.
        """
        impacts = _load(ARCHITECTURE / "impacts.json")
        k11 = next(
            k for k in impacts["kpis"]["items"] if k["kpi_id"] == "K11"
        )
        if k11["validation_status"] != "Unresolved":
            assert "decision_log/" in k11["source_ref"], (
                "K11 left Unresolved without citing an operator decision"
            )

        milestones = _load(ARCHITECTURE / "milestones_seed.json")
        # The draft carries five. Any milestone beyond them must be an operator
        # decision with a decision-log source, must not claim a draft
        # paragraph, and must not be Confirmed on evidence that does not exist.
        draft_milestones = [
            m for m in milestones["milestones"] if "¶" in m["source_ref"]
        ]
        assert len(draft_milestones) == 5
        for extra in milestones["milestones"][len(draft_milestones):]:
            assert "decision_log/" in extra["source_ref"], (
                f"{extra['milestone_id']} was invented for the placement window"
            )
            assert extra["validation_status"] in {"Inferred", "Confirmed"}
            assert extra.get("note", "").strip()

        monitoring = milestones["placement_period_monitoring"]
        if monitoring["validation_status"] != "Unresolved":
            assert "decision_log/" in monitoring["source_ref"], (
                "the monitoring gap was closed without an operator decision"
            )
            assert monitoring["decided"], (
                "a closed monitoring record must say what was decided"
            )
        else:
            assert monitoring["candidates_raised_not_decided"]

    def test_the_authorisation_packet_list_covers_the_open_items(
        self, checklist
    ):
        open_items = checklist["open_for_authorisation"]["items"]
        assert len(open_items) >= 10
        for entry in open_items:
            assert entry["what"]
            assert entry["why_open"]
        blob = json.dumps(open_items, ensure_ascii=False)
        for expected in ("C5", "invited_talks", "PIC"):
            assert expected in blob, f"{expected} is not listed for ticket 7"
        # K11 was listed here at ticket 6 and closed at ticket 7. An item may
        # leave the open list only by being recorded as closed.
        closed = json.dumps(
            checklist["open_for_authorisation"].get("closed_on_2026_08_12", []),
            ensure_ascii=False,
        )
        assert "K11" in blob or "K11" in closed, (
            "K11 left the open list without being recorded as closed"
        )


class TestCriterion5DecisionLogRecords:
    @pytest.mark.parametrize("item", sorted(DECISION_ITEM_RECORDS))
    def test_each_decision_item_has_a_record(self, item):
        record = _load(DECISION_LOG / DECISION_ITEM_RECORDS[item])
        assert record["record_type"] == "decision"
        assert record["decided_on"] == "2026-08-11"
        assert record["branch"] == "fieldwise-run-01"
        assert record["status"]
        assert record["why"] or record.get("decision")

    def test_the_fold_record_names_every_artifact_it_wrote(self):
        record = _load(DECISION_LOG / "fieldwise-ticket6-fold_2026-08-12.json")
        for relative in record["artifacts_written"]:
            assert (REPO_ROOT / relative).is_file(), (
                f"{relative} is named in the fold record but does not exist"
            )

    def test_the_fold_record_points_at_each_item_record(self):
        record = _load(DECISION_LOG / "fieldwise-ticket6-fold_2026-08-12.json")
        referenced = set(record["per_item_records"].values())
        referenced.discard(record["per_item_records"]["note"])
        for relative in referenced:
            assert (DECISION_LOG / Path(relative).name).is_file()
        assert len(referenced) == len(DECISION_ITEM_RECORDS)

    def test_the_lift_record_carries_the_ticket6_extension(self):
        lift = _load(DECISION_LOG / "fieldwise-tier3-lift_2026-08-11.json")
        tickets = {e["ticket"] for e in lift["extensions"]}
        assert {4, 5, 6} <= tickets

    def test_the_provenance_manifest_covers_the_folded_artifacts(self):
        manifest = _load(TIER3 / "hand_lift_provenance.json")
        folded = {a["artifact"] for a in manifest["folded_artifacts"]}
        assert {
            "call_binding/confirmation_checklist.json",
            "working_assumptions.json",
            "consortium/partners.json",
            "consortium/roles.json",
            "consortium/capabilities.json",
            "architecture_inputs/impacts.json",
            "architecture_inputs/workpackage_seed.json",
        } <= folded
        not_seeded = " ".join(manifest["not_seeded"])
        assert "confirmation_checklist" not in not_seeded
        assert "working_assumptions" not in not_seeded
