"""The anonymised consortium of instance two, held to its own records.

The consortium ticket in `plans/dev_graph_demo_tickets.md` writes twelve
pseudonymous partners, their roles, the operator declarations behind them, a
Tier 4 gap analysis and a decision log entry. These checks hold those artifacts
to each other and to the tiers they cite (CLAUDE.md §10.5, §13.3).

The checks that matter most are the ones a reader cannot do by eye:

* no Tier 3 artifact carries a real country name, web address, email or
  instance-one noun, checked mechanically rather than asserted;
* every Tier 2B requirement in the gap analysis resolves to a span that is
  actually in the call extract, and every covering partner exists;
* the report's composition block is byte-equal to a fresh evaluator run, so a
  change to the partner set that is not reflected in the report fails here;
* every partner, the coordinator and the slot assignment carry a declaration in
  `working_assumptions.json`, and each declared value is derived from the
  partner's own record, so a declaration cannot drift from the registry.

One group exists because an adversarial review found this ticket's first output
claiming more than it had earned. `TestGapAnalysis` now checks that the report
does **not** call the branch anonymity-clean, that the pre-existing leak is
recorded with its path, and that a derived capability is not marked Confirmed on
the strength of a document held outside the repository.
"""
from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest

from runner.consortium_composition import (
    AC,
    MS,
    evaluate_composition,
    evaluate_scenarios,
    load_composition_rule,
    load_partners,
)
from runner.leakage_scan import scan_partner_records, scan_tree
from runner.paths import find_repo_root
from runner.working_assumptions import load_working_assumptions
from tests._tier_sources import STATUSES

REPO = find_repo_root()

TIER3 = REPO / "docs/tier3_project_instantiation"
PARTNERS = TIER3 / "consortium/partners.json"
ROLES = TIER3 / "consortium/roles.json"

TIER4 = REPO / "docs/tier4_orchestration_state"
GAP_REPORT = (
    TIER4 / "validation_reports/demo-consortium-gap-analysis_2026-09-30.json"
)
DECISION = TIER4 / "decision_log/demo-consortium_2026-09-30.json"

CALL_EXTRACT = (
    REPO
    / "docs/tier2b_topic_and_call_sources/call_extracts"
    / "HORIZON-CL6-2027-01-BIODIV-01.json"
)

#: The twelve pseudonyms, in order.
PARTNER_IDS = tuple(f"P{n:02d}" for n in range(1, 13))

#: P01 to P06 are anonymised from instance one; P07 to P12 are invented.
DERIVED_IDS = PARTNER_IDS[:6]
GAP_IDS = PARTNER_IDS[6:]

#: The organisation types the artifact schema enumerates.
ORGANISATION_TYPES = frozenset(
    {
        "university",
        "research_institute",
        "sme",
        "large_company",
        "public_body",
        "ngo",
        "other",
    }
)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def partners() -> dict:
    return _read(PARTNERS)


@pytest.fixture(scope="module")
def records(partners: dict) -> dict:
    """The partner records, keyed by pseudonym."""
    return {entry["partner_id"]: entry for entry in partners["partners"]}


@pytest.fixture(scope="module")
def roles() -> dict:
    return _read(ROLES)


@pytest.fixture(scope="module")
def report() -> dict:
    return _read(GAP_REPORT)


@pytest.fixture(scope="module")
def extract() -> dict:
    return _read(CALL_EXTRACT)


# ---------------------------------------------------------------------------
# The partner registry
# ---------------------------------------------------------------------------


class TestPartnerRegistry:
    def test_it_holds_the_twelve_pseudonyms_in_order(self, partners: dict) -> None:
        assert [p["partner_id"] for p in partners["partners"]] == list(PARTNER_IDS)

    def test_every_record_carries_the_schema_required_fields(
        self, records: dict
    ) -> None:
        for pid, record in records.items():
            for field in (
                "partner_id",
                "legal_name",
                "country",
                "organisation_type",
                "is_coordinator",
            ):
                assert field in record, f"{pid} is missing {field}"

    def test_every_organisation_type_is_in_the_schema_enum(
        self, records: dict
    ) -> None:
        for pid, record in records.items():
            assert record["organisation_type"] in ORGANISATION_TYPES, pid

    def test_exactly_one_coordinator(self, records: dict) -> None:
        coordinators = [p for p, r in records.items() if r["is_coordinator"]]
        assert coordinators == ["P01"]

    def test_the_capability_bases_split_derived_from_fictional(
        self, records: dict
    ) -> None:
        for pid in DERIVED_IDS:
            assert records[pid]["capability_basis"] == "derived"
        for pid in GAP_IDS:
            assert records[pid]["capability_basis"] == "fictional"

    def test_every_partner_carries_a_capability_list_and_a_role(
        self, records: dict
    ) -> None:
        for pid, record in records.items():
            assert record["capabilities"], f"{pid} has no capability"
            assert record["role_in_the_action"].strip(), f"{pid} has no role"

    def test_every_gap_partner_names_the_gap_it_closes(self, records: dict) -> None:
        for pid in GAP_IDS:
            assert records[pid]["gap_closed"].strip(), pid

    def test_no_derived_partner_claims_a_gap(self, records: dict) -> None:
        """A derived partner closes no gap: the gaps are what it left open."""
        for pid in DERIVED_IDS:
            assert "gap_closed" not in records[pid], pid

    def test_every_partner_is_an_independent_beneficiary(
        self, records: dict
    ) -> None:
        """An affiliated entity counts nothing towards the composition minimum."""
        for pid, record in records.items():
            assert record["independent_legal_entity"] is True, pid
            assert record["participation_role"] == "beneficiary", pid

    def test_every_participation_status_is_assumed(self, records: dict) -> None:
        for pid, record in records.items():
            assert record["participation_status"] == "Assumed", pid

    def test_every_country_slot_class_is_ms_or_ac(self, records: dict) -> None:
        for pid, record in records.items():
            assert record["country_slot_class"] in (MS, AC), pid

    def test_the_country_field_repeats_the_slot_token(self, records: dict) -> None:
        """The schema requires a country; the slot token is what it may hold."""
        for pid, record in records.items():
            assert record["country"] == record["country_slot"], pid

    def test_the_slot_table_agrees_with_the_partner_records(
        self, partners: dict, records: dict
    ) -> None:
        table = {
            key: value
            for key, value in partners["country_slots"].items()
            if key.startswith("C")
        }
        from_records = {
            r["country_slot"]: r["country_slot_class"] for r in records.values()
        }
        assert table == from_records
        assert sorted(table) == ["C1", "C2", "C3", "C4", "C5", "C6"]

    def test_the_derived_partners_span_two_slots(self, records: dict) -> None:
        slots = {records[pid]["country_slot"] for pid in DERIVED_IDS}
        assert slots == {"C1", "C2"}

    def test_the_gap_partners_add_four_slots(self, records: dict) -> None:
        slots = {records[pid]["country_slot"] for pid in GAP_IDS}
        assert slots == {"C3", "C4", "C5", "C6"}

    def test_every_field_status_is_one_of_the_four_categories(
        self, partners: dict
    ) -> None:
        for field, status in partners["field_status"].items():
            assert status in STATUSES, f"{field} carries {status!r}"

    def test_no_personnel_entry_reads_as_a_personal_name(
        self, records: dict
    ) -> None:
        """A role descriptor ends in its partner pseudonym, never a name."""
        for pid, record in records.items():
            for entry in record["personnel_roles"]:
                assert entry.endswith(pid), f"{pid}: {entry!r}"
                assert entry[0].islower(), f"{pid}: {entry!r} starts capitalised"


# ---------------------------------------------------------------------------
# Anonymity
# ---------------------------------------------------------------------------


class TestAnonymity:
    def test_the_leakage_scan_is_clean_over_tiers_3_to_5_and_the_vault(self) -> None:
        report = scan_tree(REPO)
        assert report.ok, report.format()

    def test_no_partner_record_carries_a_country_name_or_an_address(self) -> None:
        violations = scan_partner_records(REPO)
        assert violations == (), "\n".join(
            f"{v.path}: {v.noun}" for v in violations
        )

    def test_no_artifact_of_this_ticket_carries_a_name_shaped_acronym(
        self, records: dict
    ) -> None:
        """legal_name is the pseudonym, and nothing else is acronym-shaped."""
        for pid, record in records.items():
            assert record["legal_name"] == pid, pid
            assert "acronym" not in record

    def test_the_registry_says_the_mapping_is_held_outside_the_repository(
        self, partners: dict
    ) -> None:
        mapping = partners["anonymisation"]["pseudonym_mapping"]
        assert "outside the repository" in mapping


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


class TestRoles:
    def test_every_management_role_names_a_partner_that_exists(
        self, roles: dict, records: dict
    ) -> None:
        for entry in roles["management_roles"]:
            assert entry["partner_id"] in records, entry["role"]

    def test_no_partner_holds_two_management_roles(self, roles: dict) -> None:
        """Phase 6 asks for non-overlapping management roles."""
        held = [entry["partner_id"] for entry in roles["management_roles"]]
        assert len(held) == len(set(held))

    def test_every_partner_holds_one_management_role(
        self, roles: dict, records: dict
    ) -> None:
        held = {entry["partner_id"] for entry in roles["management_roles"]}
        assert held == set(records)

    def test_every_role_name_is_unique(self, roles: dict) -> None:
        names = [entry["role"] for entry in roles["management_roles"]]
        assert len(names) == len(set(names))

    def test_the_coordinator_role_matches_the_partner_registry(
        self, roles: dict, records: dict
    ) -> None:
        coordinator = next(
            e for e in roles["management_roles"] if e["role"] == "coordinator"
        )
        assert records[coordinator["partner_id"]]["is_coordinator"] is True

    def test_every_coordination_interface_names_a_tier2b_key_that_exists(
        self, roles: dict, extract: dict
    ) -> None:
        available = set(extract["cross_cutting_requirements"])
        for entry in roles["coordination_interfaces"]:
            assert entry["tier2b_requirement"] in available, entry["interface"]

    def test_every_interface_partner_exists(
        self, roles: dict, records: dict
    ) -> None:
        for entry in roles["coordination_interfaces"]:
            assert entry["owning_partner"] in records
            for pid in entry["contributing_partners"]:
                assert pid in records, pid

    def test_the_four_coordination_interfaces_the_scope_names_are_present(
        self, roles: dict
    ) -> None:
        keys = {e["tier2b_requirement"] for e in roles["coordination_interfaces"]}
        assert {
            "gbif_obis_lucas_cooperation",
            "jrc_participation",
            "lucas_grassland_and_embal",
            "esa_futureo_coordination",
        } <= keys

    def test_it_names_interface_owners_not_earmarked_resources(
        self, roles: dict
    ) -> None:
        """Earmarking is Phase 3 and Phase 6 work against a budget this
        repository does not hold. This file records the role fact only."""
        note = roles["coordination_interfaces_note"]
        assert "not what it costs" in note
        for entry in roles["coordination_interfaces"]:
            assert "owning_partner" in entry
            assert "budget" not in json.dumps(entry).lower()

    def test_work_package_leads_are_left_to_phase_3(self, roles: dict) -> None:
        assert roles["work_package_leads"]["status"] == "not assigned here"
        assert roles["field_status"]["work_package_leads"] == "Unresolved"

    def test_every_personnel_role_names_a_partner_that_exists(
        self, roles: dict, records: dict
    ) -> None:
        for entry in roles["personnel_roles"]["roles"]:
            assert entry.rsplit(", ", 1)[-1] in records, entry

    def test_the_personnel_roles_match_the_partner_records(
        self, roles: dict, records: dict
    ) -> None:
        from_roles = set(roles["personnel_roles"]["roles"])
        from_records = {
            entry for r in records.values() for entry in r["personnel_roles"]
        }
        assert from_roles == from_records


# ---------------------------------------------------------------------------
# The operator declarations
# ---------------------------------------------------------------------------


class TestWorkingAssumptions:
    @pytest.fixture(scope="class")
    def declared(self):
        return load_working_assumptions(REPO)

    def test_the_shared_reader_loads_it(self, declared) -> None:
        assert declared.present
        assert not declared.is_empty

    def test_every_partner_has_a_participation_declaration(
        self, declared, records: dict
    ) -> None:
        for pid in records:
            declaration = declared.declaration(f"{pid}_participation")
            assert declaration is not None, pid
            assert declaration.rationale and declaration.rationale.strip()

    def test_a_declared_value_carries_the_fact_not_the_status(
        self, declared, records: dict
    ) -> None:
        """The schema's contract: `value` is the declared fact, which the W1
        predicate compares against a claim's `claim_summary`. The status is
        Assumed for every declaration and the shared reader stamps it, so writing
        'Assumed' into `value` would both duplicate it and break that contract.
        """
        for pid, record in records.items():
            value = declared.declaration(f"{pid}_participation").value
            assert value != "Assumed"
            assert record["participation_role"] in value, pid
            assert record["organisation_type"] in value, pid
            assert record["country_slot"] in value, pid
            assert record["country_slot_class"] in value, pid

    def test_no_declared_value_drifts_from_the_registry(
        self, declared, records: dict
    ) -> None:
        """Each participation value is derived from the partner's own record, so
        a declaration and the registry cannot disagree."""
        for pid, record in records.items():
            expected = (
                f"{record['participation_role']}, {record['organisation_type']}, "
                f"country slot {record['country_slot']} "
                f"({record['country_slot_class']})"
            )
            assert declared.declaration(f"{pid}_participation").value == expected

    def test_every_gap_partner_is_declared_fictional_with_its_gap(
        self, declared
    ) -> None:
        gap = {d.key for d in declared.by_checklist_ref("CONSORTIUM_GAP")}
        assert gap == {f"{pid}_participation" for pid in GAP_IDS}
        for pid in GAP_IDS:
            rationale = declared.declaration(f"{pid}_participation").rationale
            assert "does not exist" in rationale, pid
            assert "Closes" in rationale, pid

    def test_the_derived_partners_are_not_declared_as_gap_partners(
        self, declared
    ) -> None:
        gap = {d.key for d in declared.by_checklist_ref("CONSORTIUM_GAP")}
        for pid in DERIVED_IDS:
            assert f"{pid}_participation" not in gap

    def test_the_coordinator_the_slots_and_the_condition_are_declared(
        self, declared
    ) -> None:
        assert declared.declared_value("coordinator") == "P01"
        assert declared.declared_value("country_slot_assignment")
        assert (
            declared.declared_value("composition_condition")
            == "met only under assumption"
        )

    def test_every_declaration_is_surfaced_as_assumed(self, declared) -> None:
        for entry in declared.as_surface():
            assert entry["status"] == "Assumed"
            assert entry["provenance_class"] == "manually_placed"

    def test_every_assumed_partner_field_has_a_declaration(
        self, declared, records: dict
    ) -> None:
        """No Assumed status anywhere in the registry is undeclared."""
        keys = {d.key for d in declared.declarations}
        for pid in records:
            assert f"{pid}_participation" in keys
        assert {"coordinator", "country_slot_assignment"} <= keys


# ---------------------------------------------------------------------------
# The Tier 4 gap analysis
# ---------------------------------------------------------------------------


class TestGapAnalysis:
    def test_it_covers_every_requirement_class_the_extract_carries(
        self, report: dict, extract: dict
    ) -> None:
        rows = report["requirement_coverage"]
        by_class: dict[str, int] = {}
        for row in rows:
            by_class[row["requirement_class"]] = (
                by_class.get(row["requirement_class"], 0) + 1
            )
        assert by_class["expected_outcome"] == len(extract["expected_outcomes"])
        assert by_class["scope_requirement"] == len(extract["scope_requirements"])
        assert by_class["ecosystem_realm"] == len(
            extract["ecosystem_realms"]["realms"]
        )
        assert by_class["cross_cutting_requirement"] == len(
            extract["cross_cutting_requirements"]
        )

    def test_no_requirement_is_left_without_a_covering_partner(
        self, report: dict
    ) -> None:
        for row in report["requirement_coverage"]:
            assert row["covering_partners"], row["requirement_id"]
            assert row["how_covered"].strip(), row["requirement_id"]

    def test_every_covering_partner_exists(
        self, report: dict, records: dict
    ) -> None:
        for row in report["requirement_coverage"]:
            for pid in row["covering_partners"]:
                assert pid in records, f"{row['requirement_id']} names {pid}"

    def test_every_requirement_id_is_unique(self, report: dict) -> None:
        ids = [row["requirement_id"] for row in report["requirement_coverage"]]
        assert len(ids) == len(set(ids))

    def test_every_span_reference_resolves_in_the_call_extract(
        self, report: dict, extract: dict
    ) -> None:
        """A coverage row that cites a span the extract does not carry is a
        claim about a requirement nobody can check."""
        for row in report["requirement_coverage"]:
            ref = row["tier2b_span_ref"]
            assert _resolve(extract, ref) is not None, (
                f"{row['requirement_id']} cites {ref}, which the extract does "
                "not carry"
            )

    def test_every_coverage_row_carries_assumed(self, report: dict) -> None:
        for row in report["requirement_coverage"]:
            assert row["status"] == "Assumed", row["requirement_id"]

    def test_every_gap_names_the_partner_that_closes_it(
        self, report: dict, records: dict
    ) -> None:
        for gap in report["gaps_the_derived_six_left"]:
            assert gap["closed_by"].strip()
            assert gap["requirement_exposed"]

    def test_the_six_capability_gaps_are_closed_by_the_six_gap_partners(
        self, report: dict
    ) -> None:
        closers = {
            gap["closed_by"]
            for gap in report["gaps_the_derived_six_left"]
            if gap["closed_by"] in GAP_IDS
        }
        assert closers == set(GAP_IDS)

    def test_every_exposed_requirement_is_a_row_or_the_condition(
        self, report: dict
    ) -> None:
        known = {row["requirement_id"] for row in report["requirement_coverage"]}
        known.add("composition_condition")
        for gap in report["gaps_the_derived_six_left"]:
            for requirement in gap["requirement_exposed"]:
                assert requirement in known, requirement

    def test_every_status_in_the_summary_is_a_category(self, report: dict) -> None:
        for field, status in report["status_summary"].items():
            assert status in STATUSES, f"{field} carries {status!r}"

    def test_each_finding_carries_a_resolution_and_a_status(
        self, report: dict
    ) -> None:
        for finding in report["findings"]:
            assert finding["id"]
            assert finding["finding"].strip()
            assert finding["resolution"].strip()
            assert finding["disposition"] in ("open", "resolved"), finding["id"]

    def test_every_finding_status_is_a_category(self, report: dict) -> None:
        """A finding's lifecycle is `disposition`; `status` stays reserved for the
        four §12.2 categories, so the report uses one vocabulary for one thing."""
        for finding in report["findings"]:
            assert finding["status"] in STATUSES, (
                f"{finding['id']} carries status {finding['status']!r}"
            )

    def test_the_report_does_not_claim_the_branch_is_anonymity_clean(
        self, report: dict
    ) -> None:
        """The defect an adversarial review found: a scan reporting a clean
        result it had not earned. The report must not restate it."""
        assert report["status_summary"]["anonymity"] == "Unresolved"
        assert "Not clean" in report["anonymity_check"]["result"]
        assert "not anonymity-clean" in report["answer"]

    def test_it_records_the_pre_existing_leak_with_its_path(
        self, report: dict
    ) -> None:
        f8 = next(f for f in report["findings"] if f["id"] == "F8")
        assert "project-purge-clean-engine-base" in f8["evidence"]
        assert f8["status"] == "Unresolved"
        assert f8["residual"].strip()

    def test_it_records_that_the_vault_leg_has_not_run(self, report: dict) -> None:
        f9 = next(f for f in report["findings"] if f["id"] == "F9")
        assert "vault" in f9["finding"].lower()
        assert report["anonymity_check"]["coverage"]["vault"].startswith("Zero")

    def test_a_derived_capability_is_not_claimed_confirmed(
        self, report: dict, partners: dict
    ) -> None:
        """Its evidence is a document outside Tier 1-3, so §12.2 Confirmed —
        'directly evidenced by a named source in Tier 1-3' — does not apply."""
        assert report["status_summary"]["derived_capabilities"] == "Assumed"
        assert partners["field_status"]["derived_capabilities"] == "Assumed"

    def test_the_realm_rows_are_not_claimed_as_a_declared_class(
        self, report: dict
    ) -> None:
        note = report["requirement_coverage_note"]
        assert "not a fourth class" in note
        assert "SR2" in note


# ---------------------------------------------------------------------------
# The composition check, held to a fresh evaluator run
# ---------------------------------------------------------------------------


class TestCompositionCheck:
    @pytest.fixture(scope="class")
    def fresh(self):
        rule = load_composition_rule(REPO)
        return rule, evaluate_scenarios(
            load_partners(REPO),
            rule,
            derived_ids=list(DERIVED_IDS),
            gap_ids=list(GAP_IDS),
        )

    def test_the_report_block_equals_a_fresh_evaluator_run(
        self, report: dict, fresh
    ) -> None:
        """Not transcribed. A partner change the report does not reflect fails."""
        _, scenarios = fresh
        expected = []
        for scenario in scenarios:
            result = asdict(scenario.result)
            result.pop("citations")
            expected.append(
                {
                    "scenario": scenario.name,
                    "question": scenario.question,
                    "partners_evaluated": len(scenario.partner_ids),
                    "result": result,
                }
            )
        assert report["composition_check"]["scenarios"] == json.loads(
            json.dumps(expected)
        )

    def test_the_thresholds_in_the_report_come_from_tier_1(
        self, report: dict, fresh
    ) -> None:
        rule, _ = fresh
        thresholds = report["composition_check"]["thresholds"]
        assert (
            thresholds["minimum_independent_beneficiaries"]
            == rule.minimum_independent_beneficiaries
        )
        assert (
            thresholds["minimum_distinct_countries"]
            == rule.minimum_distinct_countries
        )
        assert thresholds["affiliated_entities_count_towards_the_minimum"] is False

    def test_it_cites_the_tier_1_span(self, report: dict) -> None:
        citations = report["composition_check"]["citations"]
        assert citations
        for citation in citations:
            assert citation["quote"].strip()
            assert citation["source_document"].endswith(".pdf")
            assert citation["source_page"] > 0

    def test_the_three_readings_the_ticket_asks_for_are_present(
        self, report: dict
    ) -> None:
        names = {s["scenario"] for s in report["composition_check"]["scenarios"]}
        assert "all_partners" in names
        assert "derived_partners_only" in names
        assert {f"without_{pid}" for pid in GAP_IDS} <= names

    def test_all_twelve_meet_the_condition(self, report: dict) -> None:
        scenario = _scenario(report, "all_partners")
        assert scenario["result"]["met"] is True
        assert len(scenario["result"]["distinct_country_slots"]) == 6

    def test_the_derived_six_do_not_meet_it(self, report: dict) -> None:
        scenario = _scenario(report, "derived_partners_only")
        assert scenario["result"]["met"] is False
        assert "distinct_countries" in scenario["result"]["failed_limbs"]

    def test_removing_any_single_gap_partner_still_meets_it(
        self, report: dict
    ) -> None:
        for pid in GAP_IDS:
            scenario = _scenario(report, f"without_{pid}")
            assert scenario["result"]["met"] is True, pid
            assert len(scenario["result"]["distinct_country_slots"]) >= 3, pid

    def test_the_verdict_does_not_claim_the_condition_is_confirmed(
        self, report: dict
    ) -> None:
        verdict = report["composition_check"]["verdict"]
        assert "under assumption" in verdict
        assert report["status_summary"]["composition_condition"] == "Assumed"

    def test_the_joint_research_centre_is_not_counted(self, report: dict) -> None:
        assert "not_counted" in report["composition_check"]

    def test_an_affiliated_partner_would_not_count(self) -> None:
        """The reason every partner is recorded as an independent beneficiary.

        Three slots meet the condition. Demote the partners holding the third
        slot to affiliated entities and the same consortium fails, because an
        affiliated entity does not sign the grant agreement.
        """
        rule = load_composition_rule(REPO)
        three_slots = [
            p for p in load_partners(REPO) if p.country_slot in ("C1", "C2", "C3")
        ]
        demoted = [
            replace(p, independent=False) if p.country_slot == "C3" else p
            for p in three_slots
        ]
        assert evaluate_composition(three_slots, rule).met
        assert not evaluate_composition(demoted, rule).met


# ---------------------------------------------------------------------------
# The decision log entry
# ---------------------------------------------------------------------------


class TestDecisionRecord:
    @pytest.fixture(scope="module")
    def decision(self) -> dict:
        return _read(DECISION)

    def test_it_records_both_operator_decisions(self, decision: dict) -> None:
        questions = decision["operator_decisions"]
        assert len(questions) == 2
        for entry in questions:
            assert entry["question"].strip()
            assert entry["decision"].strip()
            assert entry["reasoning"].strip()
            assert len(entry["options_put"]) >= 2

    def test_the_recorded_statuses_match_the_artifacts(
        self, decision: dict, records: dict
    ) -> None:
        assert "Assumed for all twelve" in decision["operator_decisions"][0][
            "decision"
        ]
        assert all(r["participation_status"] == "Assumed" for r in records.values())
        assert "P01" in decision["operator_decisions"][1]["decision"]

    def test_it_cites_the_constitution(self, decision: dict) -> None:
        assert "CLAUDE.md" in decision["authority"]
        assert "§9.4" in decision["authority"]

    def test_every_artifact_it_claims_to_have_written_exists(
        self, decision: dict
    ) -> None:
        for rel in decision["artifacts_written"]:
            assert (REPO / rel).is_file(), rel

    def test_it_states_that_the_protected_components_are_untouched(
        self, decision: dict
    ) -> None:
        components = decision["unmodified"]["components"]
        assert "runner/dag_scheduler.py" in components
        assert "runner/gate_evaluator.py" in components
        assert "runner/agnosticism_lint.py" in components

    def test_it_says_tier_3_is_not_frozen_here(self, decision: dict) -> None:
        assert decision["tier_3_freeze"]["status"] == "not frozen here"

    def test_every_open_item_names_where_it_goes(self, decision: dict) -> None:
        for item in decision["open_items_carried_forward"]:
            assert item["carried_to"].strip()

    def test_the_findings_it_carries_are_in_the_validation_report(
        self, decision: dict, report: dict
    ) -> None:
        report_ids = {finding["id"] for finding in report["findings"]}
        for item in decision["open_items_carried_forward"]:
            assert item["id"] in report_ids, item["id"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scenario(report: dict, name: str) -> dict:
    """The named scenario row of the report's composition block."""
    for scenario in report["composition_check"]["scenarios"]:
        if scenario["scenario"] == name:
            return scenario
    raise AssertionError(f"the report carries no scenario {name!r}")


def _resolve(node: Any, ref: str) -> Any:
    """Resolve a ``$.a.b[0]`` reference against a parsed JSON tree.

    Returns ``None`` when the reference does not resolve, which is what the span
    check treats as a failure.
    """
    assert ref.startswith("$"), ref
    current = node
    for part in ref[1:].split("."):
        if not part:
            continue
        name, _, rest = part.partition("[")
        if name:
            if not isinstance(current, dict) or name not in current:
                return None
            current = current[name]
        while rest:
            index_text, _, rest = rest.partition("]")
            if not isinstance(current, list):
                return None
            index = int(index_text)
            if index >= len(current):
                return None
            current = current[index]
            rest = rest.lstrip("[")
    return current
