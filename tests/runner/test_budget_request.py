"""
Tests for the deterministic lump-sum budget request composer.

The composer is a deterministic component (CLAUDE.md §17.5.3 / C2) bound to the
``n07_budget_gate`` node body.  It reads the interface contract, the request
template, the call binding, the Phase 3 WP structure, the Phase 4 Gantt, the
Phase 6 implementation architecture and the Tier 3 consortium, and writes
``docs/tier3_project_instantiation/integration/budget_request.json``.

What these tests pin
--------------------
* It computes **no budget figure** (§8.1, §8.3).  Every effort and cost field
  carries the sentinel ``requires_external_computation``.
* The request **conforms to the interface contract** (§8.5).
* It copies partner identity **verbatim** from Tier 3 — pseudonym and
  country slot, never a derived or invented name.
* It is **deterministic**: two composes of the same inputs are byte-equal.
* It **skips** cleanly for a unit-cost instrument, whose budget is the internal
  derivation, not an external request.
* It **fails closed** on a missing or malformed input rather than composing a
  partial request.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.budget_request import (
    OUTPUT_REL,
    REQUIRES_EXTERNAL_COMPUTATION,
    BudgetRequestError,
    compose_budget_request,
    derive_budget_request,
)
from runner.interface_contract import validate_payload

RUN_ID = "run-budget-request-001"


# ---------------------------------------------------------------------------
# Fixture world
# ---------------------------------------------------------------------------


def _contract() -> dict:
    return {
        "contract_version": "1.0",
        "protocol": "lump_sum_budget_planner_v1",
        "request_schema": {
            "required_fields": [
                "request_id",
                "call_id",
                "project_duration_months",
                "work_packages",
                "partners",
            ],
            "work_package_entry": {
                "required_fields": ["wp_id", "title", "lead_partner"]
            },
            "partner_entry": {
                "required_fields": ["partner_id", "name", "country", "role"]
            },
        },
        "response_schema": {
            "required_fields": ["response_id", "schema_version"],
        },
        "validation_rules": {"no_negative_values": "non-negative"},
    }


def _call(**overrides) -> dict:
    data = {
        "call_id": "CALL-1",
        "topic_code": "TOPIC-1",
        "instrument_type": "RIA",
        "type_of_action": "HORIZON-RIA",
        "project_duration_months": 48,
        "budget_regime": "lump_sum",
    }
    data.update(overrides)
    return data


def _wp_structure() -> dict:
    return {
        "schema_id": "orch.phase3.wp_structure.v1",
        "run_id": RUN_ID,
        "work_packages": [
            {
                "wp_id": "WP2",
                "title": "Second",
                "lead_partner": "P02",
                "contributing_partners": ["P01"],
                "tasks": [{"task_id": "T2.1", "responsible_partner": "P02"}],
                "deliverables": [{"deliverable_id": "D2.1", "due_month": 24}],
            },
            {
                "wp_id": "WP1",
                "title": "First",
                "lead_partner": "P01",
                "contributing_partners": ["P02"],
                "tasks": [
                    {"task_id": "T1.1", "responsible_partner": "P01"},
                    {"task_id": "T1.2", "responsible_partner": "P02"},
                ],
                "deliverables": [{"deliverable_id": "D1.1", "due_month": 6}],
            },
        ],
    }


def _gantt() -> dict:
    return {
        "schema_id": "orch.phase4.gantt.v1",
        "run_id": RUN_ID,
        "tasks": [
            {"task_id": "T1.1", "wp_id": "WP1", "start_month": 1, "end_month": 12},
            {"task_id": "T1.2", "wp_id": "WP1", "start_month": 6, "end_month": 30},
            {"task_id": "T2.1", "wp_id": "WP2", "start_month": 13, "end_month": 48},
        ],
        "milestones": [],
    }


def _partners() -> dict:
    return {
        "coordinator": {"partner_id": "P01"},
        "partners": [
            {
                "partner_id": "P01",
                "legal_name": "P01",
                "country": "C1",
                "country_slot": "C1",
                "country_slot_class": "MS",
                "organisation_type": "research_institute",
                "participation_role": "beneficiary",
                "participation_status": "Assumed",
                "is_coordinator": True,
            },
            {
                "partner_id": "P02",
                "legal_name": "P02",
                "country": "C2",
                "country_slot": "C2",
                "country_slot_class": "AC",
                "organisation_type": "sme",
                "participation_role": "beneficiary",
                "participation_status": "Assumed",
                "is_coordinator": False,
            },
        ],
    }


def _implementation() -> dict:
    return {
        "schema_id": "orch.phase6.implementation_architecture.v1",
        "run_id": RUN_ID,
        "management_roles": [
            {"role_id": "MR-COORD", "role_name": "Coordinator", "assigned_to": "P01"},
            {"role_id": "MR-WP2", "role_name": "WP2 Lead", "assigned_to": "P02"},
        ],
    }


def _template() -> dict:
    return {
        "request_id": "",
        "call_id": "",
        "project_duration_months": 0,
        "work_packages": [
            {"wp_id": "", "title": "", "lead_partner": "", "contributing_partners": []}
        ],
        "partners": [{"partner_id": "", "name": "", "country": "", "role": ""}],
    }


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A minimal repository with everything the composer reads."""

    def write(rel: str, data: dict) -> None:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    write("docs/integrations/lump_sum_budget_planner/interface_contract.json", _contract())
    write(
        "docs/integrations/lump_sum_budget_planner/request_templates/"
        "budget_request_template.json",
        _template(),
    )
    write("docs/tier3_project_instantiation/call_binding/selected_call.json", _call())
    write("docs/tier3_project_instantiation/consortium/partners.json", _partners())
    write(
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
        "wp_structure.json",
        _wp_structure(),
    )
    write(
        "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/"
        "gantt.json",
        _gantt(),
    )
    write(
        "docs/tier4_orchestration_state/phase_outputs/"
        "phase6_implementation_architecture/implementation_architecture.json",
        _implementation(),
    )
    return tmp_path


def _compose(repo: Path) -> dict:
    written = derive_budget_request(RUN_ID, repo)
    assert written is not None
    return json.loads(written.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# No budget figure — §8.1, §8.3
# ---------------------------------------------------------------------------


class TestNoBudgetFigure:
    def test_every_effort_and_cost_field_is_a_sentinel(self, repo):
        request = _compose(repo)
        for wp in request["work_packages"]:
            assert wp["effort_person_months"] == REQUIRES_EXTERNAL_COMPUTATION
            assert wp["lump_sum_eur"] == REQUIRES_EXTERNAL_COMPUTATION
        for partner in request["partners"]:
            assert partner["total_effort_pm"] == REQUIRES_EXTERNAL_COMPUTATION
            assert partner["cost_eur"] == REQUIRES_EXTERNAL_COMPUTATION

    def test_the_request_names_the_fields_it_leaves_to_the_planner(self, repo):
        request = _compose(repo)
        assert sorted(request["fields_requiring_external_computation"]) == [
            "partners[].cost_eur",
            "partners[].total_effort_pm",
            "work_packages[].effort_person_months",
            "work_packages[].lump_sum_eur",
        ]

    def test_no_euro_amount_from_the_call_binding_reaches_the_request(self, repo):
        """A call-level indicative budget is not this project's figure."""
        call = _call(
            expected_eu_contribution_per_project_eur=5_000_000,
            indicative_call_budget_eur=10_000_000,
        )
        (
            repo
            / "docs/tier3_project_instantiation/call_binding/selected_call.json"
        ).write_text(json.dumps(call, indent=2), encoding="utf-8")
        request = _compose(repo)
        serialised = json.dumps(request)
        assert "5000000" not in serialised
        assert "10000000" not in serialised

    def test_the_only_numbers_are_months_copied_from_upstream(self, repo):
        request = _compose(repo)

        def numbers(node, where="$"):
            if isinstance(node, bool):
                return []
            if isinstance(node, (int, float)):
                return [(where, node)]
            if isinstance(node, dict):
                return [n for k, v in node.items() for n in numbers(v, f"{where}.{k}")]
            if isinstance(node, list):
                return [
                    n for i, v in enumerate(node) for n in numbers(v, f"{where}[{i}]")
                ]
            return []

        found = numbers(request)
        assert found, "the request should carry the month fields"
        for where, _value in found:
            # Months come from Phase 4 and the call binding; ``tier`` is a
            # source reference's tier number. Nothing else in a budget request
            # may be a number, because the only other numbers are figures.
            assert where.rsplit(".", 1)[-1] in {
                "project_duration_months",
                "start_month",
                "end_month",
                "due_month",
                "tier",
            }, where


# ---------------------------------------------------------------------------
# Contract conformance — §8.5
# ---------------------------------------------------------------------------


class TestContractConformance:
    def test_the_composed_request_conforms(self, repo):
        request = _compose(repo)
        assert validate_payload(request, _contract(), role="request") == []

    def test_every_contract_required_field_is_populated(self, repo):
        request = _compose(repo)
        for field in _contract()["request_schema"]["required_fields"]:
            assert request[field] not in (None, "", [], {})

    def test_a_non_conforming_request_is_refused_not_written(self, repo):
        """A contract the composer cannot satisfy halts it; nothing is written."""
        contract = _contract()
        contract["request_schema"]["required_fields"].append("total_budget_eur")
        (
            repo
            / "docs/integrations/lump_sum_budget_planner/interface_contract.json"
        ).write_text(json.dumps(contract, indent=2), encoding="utf-8")
        with pytest.raises(BudgetRequestError) as exc:
            derive_budget_request(RUN_ID, repo)
        assert "total_budget_eur" in str(exc.value)
        assert not (repo / OUTPUT_REL).exists()


# ---------------------------------------------------------------------------
# Coverage of the WP structure and the consortium
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_every_phase3_wp_appears_once_in_wp_id_order(self, repo):
        request = _compose(repo)
        assert [wp["wp_id"] for wp in request["work_packages"]] == ["WP1", "WP2"]

    def test_every_tier3_partner_appears_once_in_partner_id_order(self, repo):
        request = _compose(repo)
        assert [p["partner_id"] for p in request["partners"]] == ["P01", "P02"]

    def test_wp_months_come_from_the_gantt_task_window(self, repo):
        request = _compose(repo)
        by_id = {wp["wp_id"]: wp for wp in request["work_packages"]}
        assert by_id["WP1"]["start_month"] == 1
        assert by_id["WP1"]["end_month"] == 30
        assert by_id["WP2"]["start_month"] == 13
        assert by_id["WP2"]["end_month"] == 48

    def test_a_wp_with_no_gantt_task_carries_no_invented_window(self, repo):
        gantt = _gantt()
        gantt["tasks"] = [t for t in gantt["tasks"] if t["wp_id"] != "WP2"]
        (
            repo
            / "docs/tier4_orchestration_state/phase_outputs/"
            "phase4_gantt_milestones/gantt.json"
        ).write_text(json.dumps(gantt, indent=2), encoding="utf-8")
        request = _compose(repo)
        by_id = {wp["wp_id"]: wp for wp in request["work_packages"]}
        assert by_id["WP2"]["start_month"] is None
        assert by_id["WP2"]["end_month"] is None

    def test_partner_roles_carry_the_phase6_management_role(self, repo):
        request = _compose(repo)
        by_id = {p["partner_id"]: p for p in request["partners"]}
        assert by_id["P01"]["management_roles"] == ["Coordinator"]
        assert by_id["P02"]["management_roles"] == ["WP2 Lead"]

    def test_wps_as_lead_is_derived_from_the_wp_structure(self, repo):
        request = _compose(repo)
        by_id = {p["partner_id"]: p for p in request["partners"]}
        assert by_id["P01"]["wps_as_lead"] == ["WP1"]
        assert by_id["P02"]["wps_as_lead"] == ["WP2"]


# ---------------------------------------------------------------------------
# Pseudonymity — the request carries Tier 3 identity verbatim
# ---------------------------------------------------------------------------


class TestPseudonymity:
    def test_name_is_the_tier3_pseudonym_verbatim(self, repo):
        request = _compose(repo)
        assert [p["name"] for p in request["partners"]] == ["P01", "P02"]

    def test_country_is_the_tier3_country_slot_verbatim(self, repo):
        request = _compose(repo)
        assert [p["country"] for p in request["partners"]] == ["C1", "C2"]

    def test_a_partner_whose_country_leaves_its_slot_is_refused(self, repo):
        """The composer copies; it does not choose between two country fields."""
        partners = _partners()
        partners["partners"][0]["country"] = "Hungary"
        (
            repo / "docs/tier3_project_instantiation/consortium/partners.json"
        ).write_text(json.dumps(partners, indent=2), encoding="utf-8")
        with pytest.raises(BudgetRequestError) as exc:
            derive_budget_request(RUN_ID, repo)
        assert "P01" in str(exc.value)
        assert not (repo / OUTPUT_REL).exists()

    def test_no_field_outside_the_declared_set_is_copied_from_a_partner(self, repo):
        partners = _partners()
        partners["partners"][0]["internal_note"] = "contact the lab in Szeged"
        (
            repo / "docs/tier3_project_instantiation/consortium/partners.json"
        ).write_text(json.dumps(partners, indent=2), encoding="utf-8")
        request = _compose(repo)
        assert "Szeged" not in json.dumps(request)


# ---------------------------------------------------------------------------
# Determinism — the component's closure guarantee
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_composes_are_byte_equal(self, repo):
        first = derive_budget_request(RUN_ID, repo)
        assert first is not None
        first_bytes = first.read_bytes()
        second = derive_budget_request(RUN_ID, repo)
        assert second is not None
        assert second.read_bytes() == first_bytes

    def test_the_pure_core_is_byte_equal_for_the_same_inputs(self):
        args = (
            RUN_ID,
            _call(),
            _wp_structure(),
            _gantt(),
            _implementation(),
            _partners(),
        )
        assert json.dumps(
            compose_budget_request(*args), sort_keys=True
        ) == json.dumps(compose_budget_request(*args), sort_keys=True)

    def test_the_request_carries_no_wall_clock_field(self, repo):
        request = _compose(repo)
        serialised = json.dumps(request)
        assert "composed_at" not in serialised
        assert "timestamp" not in serialised

    def test_the_request_id_is_stable_across_runs(self, repo):
        first = _compose(repo)
        (repo / OUTPUT_REL).unlink()
        second = derive_budget_request("a-different-run-id", repo)
        assert second is not None
        assert json.loads(second.read_text(encoding="utf-8"))["request_id"] == (
            first["request_id"]
        )

    def test_the_run_id_is_recorded_for_traceability(self, repo):
        assert _compose(repo)["run_id"] == RUN_ID


# ---------------------------------------------------------------------------
# Instrument guard and fail-closed behaviour
# ---------------------------------------------------------------------------


class TestInstrumentGuard:
    def test_a_unit_cost_instrument_is_skipped_and_nothing_is_written(self, repo):
        (
            repo
            / "docs/tier3_project_instantiation/call_binding/selected_call.json"
        ).write_text(
            json.dumps(_call(budget_regime="unit_cost"), indent=2), encoding="utf-8"
        )
        assert derive_budget_request(RUN_ID, repo) is None
        assert not (repo / OUTPUT_REL).exists()

    def test_an_unresolvable_regime_writes_nothing(self, repo):
        """Neither budget component writes, so gate_09 blocks on the absence.

        The alternative — compose on silence — is what let both components
        write on the same call.
        """
        call = _call()
        del call["budget_regime"]
        (
            repo
            / "docs/tier3_project_instantiation/call_binding/selected_call.json"
        ).write_text(json.dumps(call, indent=2), encoding="utf-8")
        # No Tier 2A instrument registry in this fixture, so nothing resolves.
        assert derive_budget_request(RUN_ID, repo) is None
        assert not (repo / OUTPUT_REL).exists()

    def test_exactly_one_budget_component_claims_any_given_call(self, repo):
        """The property the manifest asserts, checked rather than asserted.

        The two components share one guard, so they cannot both answer yes.
        """
        from runner.instrument_profile import owns_budget_regime

        for regime, expected in (("lump_sum", "lump_sum"), ("unit_cost", "unit_cost")):
            (
                repo
                / "docs/tier3_project_instantiation/call_binding/selected_call.json"
            ).write_text(
                json.dumps(_call(budget_regime=regime), indent=2), encoding="utf-8"
            )
            claims = [
                r
                for r in ("lump_sum", "unit_cost")
                if owns_budget_regime(repo, r)
            ]
            assert claims == [expected]

    def test_an_unknown_regime_is_claimed_by_neither(self, repo):
        from runner.instrument_profile import owns_budget_regime

        (
            repo
            / "docs/tier3_project_instantiation/call_binding/selected_call.json"
        ).write_text(
            json.dumps(_call(budget_regime="flat_rate"), indent=2), encoding="utf-8"
        )
        assert not owns_budget_regime(repo, "lump_sum")
        assert not owns_budget_regime(repo, "unit_cost")
        assert derive_budget_request(RUN_ID, repo) is None


class TestFailsClosed:
    @pytest.mark.parametrize(
        "rel",
        [
            "docs/integrations/lump_sum_budget_planner/interface_contract.json",
            "docs/tier3_project_instantiation/consortium/partners.json",
            "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
            "wp_structure.json",
            "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/"
            "gantt.json",
            "docs/tier4_orchestration_state/phase_outputs/"
            "phase6_implementation_architecture/implementation_architecture.json",
        ],
    )
    def test_a_missing_input_raises_and_writes_nothing(self, repo, rel):
        (repo / rel).unlink()
        with pytest.raises(BudgetRequestError):
            derive_budget_request(RUN_ID, repo)
        assert not (repo / OUTPUT_REL).exists()

    def test_an_absent_call_binding_skips_rather_than_raises(self, repo):
        """No call binding means no resolvable regime, so no component owns it.

        Skipping is not papering over the gap: nothing is written, and
        gate_09 blocks on the missing artifact exactly as §12.4 requires. The
        unit-cost deriver answers the same way through the same guard.
        """
        (
            repo
            / "docs/tier3_project_instantiation/call_binding/selected_call.json"
        ).unlink()
        assert derive_budget_request(RUN_ID, repo) is None
        assert not (repo / OUTPUT_REL).exists()

    def test_a_malformed_input_raises(self, repo):
        (
            repo
            / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
            "wp_structure.json"
        ).write_text("{not json", encoding="utf-8")
        with pytest.raises(BudgetRequestError):
            derive_budget_request(RUN_ID, repo)

    def test_an_empty_work_package_list_raises(self, repo):
        structure = _wp_structure()
        structure["work_packages"] = []
        (
            repo
            / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
            "wp_structure.json"
        ).write_text(json.dumps(structure, indent=2), encoding="utf-8")
        with pytest.raises(BudgetRequestError):
            derive_budget_request(RUN_ID, repo)

    def test_a_wp_lead_absent_from_the_consortium_raises(self, repo):
        structure = _wp_structure()
        structure["work_packages"][0]["lead_partner"] = "P99"
        (
            repo
            / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
            "wp_structure.json"
        ).write_text(json.dumps(structure, indent=2), encoding="utf-8")
        with pytest.raises(BudgetRequestError) as exc:
            derive_budget_request(RUN_ID, repo)
        assert "P99" in str(exc.value)

    def test_a_duplicate_wp_id_raises(self, repo):
        structure = _wp_structure()
        structure["work_packages"].append(dict(structure["work_packages"][0]))
        (
            repo
            / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
            "wp_structure.json"
        ).write_text(json.dumps(structure, indent=2), encoding="utf-8")
        with pytest.raises(BudgetRequestError):
            derive_budget_request(RUN_ID, repo)
