"""
The demo's Phase 7: the budget request, and the hard block that is still intact.

Ticket "Budget request and the Phase 7 gate" in ``plans/dev_graph_demo_tickets.md``.
BIODIV-01 is a **lump-sum** RIA, so Phase 7 routes through the external Lump Sum
Budget Planner.  The repository composes the request; the operator runs the
planner and places the response in ``received/``.  Until that response exists,
``gate_09`` fails and every Phase 8 node is frozen (CLAUDE.md §8.4, §13.4).

These tests read the real repository.  They assert three things the ticket asks
for:

1. The composed request conforms to the interface contract and names
   pseudonymous partners only.
2. The response is absent, so the gate's own blocking condition is the recorded
   outcome — not a hold state, and not a fabricated pass.
3. The hard block on Phase 8 is intact: the gate that triggers it is still
   ``gate_09``, and the frozen set still covers every Phase 8 node.

No runner phase is dispatched here, and no gate result is written: gate
evaluation belongs to the scheduler (§17.1.4, §17.6.3).  What runs is the
deterministic composer and the gate's own predicate functions, which are pure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.budget_request import (
    OUTPUT_REL,
    REQUIRES_EXTERNAL_COMPUTATION,
    derive_budget_request,
)
from runner.dag_scheduler import _HARD_BLOCK_GATE
from runner.instrument_profile import resolve_instrument_profile
from runner.interface_contract import validate_payload
from runner.leakage_scan import iter_pseudonymity_files, scan_partner_records
from runner.predicates.coverage_predicates import (
    partner_budget_coverage_match,
    wp_budget_coverage_match,
)
from runner.predicates.file_predicates import dir_non_empty
from runner.predicates.schema_predicates import interface_contract_conforms
from runner.run_context import PHASE_8_NODE_IDS

REPO = Path(__file__).resolve().parents[1]

CONTRACT_REL = "docs/integrations/lump_sum_budget_planner/interface_contract.json"
RECEIVED_REL = "docs/integrations/lump_sum_budget_planner/received/"
VALIDATION_REL = "docs/integrations/lump_sum_budget_planner/validation/"
MANIFEST_REL = ".claude/workflows/system_orchestration/manifest.compile.yaml"
WP_STRUCTURE_REL = (
    "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
    "wp_structure.json"
)
PARTNERS_REL = "docs/tier3_project_instantiation/consortium/partners.json"


def _json(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def request_payload() -> dict:
    return _json(OUTPUT_REL)


@pytest.fixture(scope="module")
def contract() -> dict:
    return _json(CONTRACT_REL)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return yaml.safe_load((REPO / MANIFEST_REL).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The route: this topic is lump sum, so the request is the repository's job
# ---------------------------------------------------------------------------


class TestTheRoute:
    def test_the_selected_call_declares_the_lump_sum_regime(self):
        call = _json("docs/tier3_project_instantiation/call_binding/selected_call.json")
        assert call["budget_regime"] == "lump_sum"
        assert call["field_status"]["budget_regime"] == "Confirmed"

    def test_the_instrument_profile_resolves_to_the_same_regime(self):
        assert resolve_instrument_profile(REPO).budget_regime == "lump_sum"

    def test_the_composer_is_bound_to_the_budget_gate_node(self, manifest):
        node = next(
            n for n in manifest["node_registry"] if n["node_id"] == "n07_budget_gate"
        )
        assert "budget_request_composer" in node["deterministic_components"]
        assert "unit_cost_budget_deriver" in node["deterministic_components"]

    def test_the_composer_is_registered(self):
        from runner.deterministic_components import COMPONENT_REGISTRY

        assert "budget_request_composer" in COMPONENT_REGISTRY


# ---------------------------------------------------------------------------
# Criterion 1 — the request conforms, and names pseudonyms only
# ---------------------------------------------------------------------------


class TestTheRequestConforms:
    def test_the_request_exists(self, request_payload):
        assert request_payload["call_id"] == "HORIZON-CL6-2027-01"

    def test_it_conforms_to_the_interface_contract(self, request_payload, contract):
        assert validate_payload(request_payload, contract, role="request") == []

    def test_it_names_the_contract_version_it_was_composed_against(
        self, request_payload, contract
    ):
        assert request_payload["contract_version"] == contract["contract_version"]

    def test_it_covers_every_phase3_work_package(self, request_payload):
        structure = _json(WP_STRUCTURE_REL)
        assert [wp["wp_id"] for wp in request_payload["work_packages"]] == sorted(
            wp["wp_id"] for wp in structure["work_packages"]
        )

    def test_it_covers_every_tier3_partner(self, request_payload):
        partners = _json(PARTNERS_REL)
        assert [p["partner_id"] for p in request_payload["partners"]] == sorted(
            p["partner_id"] for p in partners["partners"]
        )

    def test_it_carries_no_budget_figure(self, request_payload):
        for wp in request_payload["work_packages"]:
            assert wp["lump_sum_eur"] == REQUIRES_EXTERNAL_COMPUTATION
            assert wp["effort_person_months"] == REQUIRES_EXTERNAL_COMPUTATION
        for partner in request_payload["partners"]:
            assert partner["cost_eur"] == REQUIRES_EXTERNAL_COMPUTATION
            assert partner["total_effort_pm"] == REQUIRES_EXTERNAL_COMPUTATION

    def test_the_calls_indicative_euro_amounts_are_not_carried_into_it(
        self, request_payload
    ):
        call = _json("docs/tier3_project_instantiation/call_binding/selected_call.json")
        serialised = json.dumps(request_payload)
        for key in (
            "expected_eu_contribution_per_project_eur",
            "indicative_call_budget_eur",
        ):
            assert str(call[key]) not in serialised

    def test_it_recomposes_byte_equal(self, request_payload):
        """The component's closure guarantee, checked on the real records."""
        before = (REPO / OUTPUT_REL).read_bytes()
        derive_budget_request(request_payload["run_id"], REPO)
        assert (REPO / OUTPUT_REL).read_bytes() == before


class TestTheRequestNamesPseudonymsOnly:
    def test_every_partner_name_is_its_tier3_pseudonym(self, request_payload):
        partners = {
            p["partner_id"]: p for p in _json(PARTNERS_REL)["partners"]
        }
        for entry in request_payload["partners"]:
            source = partners[entry["partner_id"]]
            assert entry["name"] == source["legal_name"]
            assert entry["country"] == source["country_slot"]

    def test_the_request_is_inside_the_pseudonymity_check_scope(self):
        scanned = {
            p.relative_to(REPO).as_posix() for p in iter_pseudonymity_files(REPO)
        }
        assert OUTPUT_REL in scanned

    def test_the_pseudonymity_check_finds_nothing_in_it(self):
        offenders = [
            v for v in scan_partner_records(REPO) if v.path.startswith("docs/tier3")
        ]
        assert [v for v in offenders if OUTPUT_REL in v.path] == []


# ---------------------------------------------------------------------------
# Criterion 2 — no response, so the blocking gate failure is the outcome
# ---------------------------------------------------------------------------


class TestTheMissingResponseBlocks:
    def test_the_received_directory_holds_no_response(self):
        result = dir_non_empty(RECEIVED_REL, repo_root=REPO)
        assert not result.passed, (
            "A response has appeared in received/. Re-run the Phase 7 ticket: "
            "this test pins the recorded blocking state, not a wish."
        )

    def test_the_validation_directory_holds_no_validation_artifact(self):
        assert not dir_non_empty(VALIDATION_REL, repo_root=REPO).passed

    def test_no_budget_gate_assessment_was_written(self):
        assert not (
            REPO
            / "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/"
            "budget_gate_assessment.json"
        ).exists()

    def test_the_coverage_predicates_report_every_wp_and_partner_uncovered(self):
        wp_result = wp_budget_coverage_match(
            WP_STRUCTURE_REL, RECEIVED_REL, repo_root=REPO
        )
        partner_result = partner_budget_coverage_match(
            PARTNERS_REL, RECEIVED_REL, repo_root=REPO
        )
        assert not wp_result.passed
        assert len(wp_result.details["missing_from_budget"]) == 7
        assert not partner_result.passed
        assert len(partner_result.details["missing_from_budget"]) == 12

    def test_an_absent_response_is_a_gate_failure_not_a_hold_state(self, manifest):
        gate = next(
            g
            for g in manifest["gate_registry"]
            if g["gate_id"] == "gate_09_budget_consistency"
        )
        assert gate["mandatory"] is True
        assert gate["bypass_prohibited"] is True
        assert gate["absent_artifacts_behavior"] == "blocking_gate_failure"


class TestAResponseWouldBeValidated:
    """§8.5: a non-conforming response must be rejected, not silently accepted.

    The operator's response does not exist yet, so what is checked here is that
    the machinery waiting for it discriminates — on the repository's own
    contract, not a fixture one.
    """

    def _received(self, tmp_path: Path, payload: dict) -> Path:
        received = tmp_path / "received"
        received.mkdir()
        (received / "response.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return received

    def _conforming(self) -> dict:
        structure = _json(WP_STRUCTURE_REL)
        partners = _json(PARTNERS_REL)
        return {
            "response_id": "resp-biodiv-01",
            "schema_version": "1.0",
            "work_packages": [
                {"wp_id": wp["wp_id"], "lump_sum": 0}
                for wp in structure["work_packages"]
            ],
            "partners": [
                {"partner_id": p["partner_id"], "total_effort_pm": 0}
                for p in partners["partners"]
            ],
        }

    def test_a_conforming_response_passes(self, tmp_path):
        received = self._received(tmp_path, self._conforming())
        result = interface_contract_conforms(
            received, REPO / CONTRACT_REL, repo_root=REPO
        )
        assert result.passed
        assert result.details["contract_mode"] == "planner_contract_document"

    def test_a_response_missing_a_required_field_is_rejected(self, tmp_path):
        payload = self._conforming()
        del payload["schema_version"]
        received = self._received(tmp_path, payload)
        assert not interface_contract_conforms(
            received, REPO / CONTRACT_REL, repo_root=REPO
        ).passed

    def test_a_response_with_a_negative_figure_is_rejected(self, tmp_path):
        payload = self._conforming()
        payload["work_packages"][0]["lump_sum"] = -1
        received = self._received(tmp_path, payload)
        assert not interface_contract_conforms(
            received, REPO / CONTRACT_REL, repo_root=REPO
        ).passed

    def test_a_response_that_is_not_a_budget_at_all_is_rejected(self, tmp_path):
        """The fail-open this ticket closed: a JSON Schema reading passed this."""
        received = self._received(tmp_path, {"hello": "world"})
        assert not interface_contract_conforms(
            received, REPO / CONTRACT_REL, repo_root=REPO
        ).passed

    def test_a_response_omitting_a_work_package_fails_coverage(self, tmp_path):
        payload = self._conforming()
        payload["work_packages"] = payload["work_packages"][1:]
        received = self._received(tmp_path, payload)
        result = wp_budget_coverage_match(
            REPO / WP_STRUCTURE_REL, received, repo_root=REPO
        )
        assert not result.passed
        assert result.details["missing_from_budget"] == ["WP1"]

    def test_a_full_response_satisfies_both_coverage_predicates(self, tmp_path):
        received = self._received(tmp_path, self._conforming())
        assert wp_budget_coverage_match(
            REPO / WP_STRUCTURE_REL, received, repo_root=REPO
        ).passed
        assert partner_budget_coverage_match(
            REPO / PARTNERS_REL, received, repo_root=REPO
        ).passed


# ---------------------------------------------------------------------------
# Criterion 3 — the hard block on Phase 8 is intact
# ---------------------------------------------------------------------------


class TestTheHardBlockIsIntact:
    def test_the_scheduler_still_hard_blocks_on_the_budget_gate(self):
        assert _HARD_BLOCK_GATE == "gate_09_budget_consistency"

    def test_the_frozen_set_covers_every_phase_8_node_in_the_manifest(self, manifest):
        manifest_phase8 = {
            n["node_id"] for n in manifest["node_registry"] if n["phase_number"] == 8
        }
        assert manifest_phase8 == set(PHASE_8_NODE_IDS)

    def test_the_budget_gate_blocks_the_edge_into_phase_8(self, manifest):
        blocked = [
            e
            for e in manifest["edge_registry"]
            if e.get("gate_condition") == "gate_09_budget_consistency"
        ]
        assert blocked
        assert all(e["from_node"] == "n07_budget_gate" for e in blocked)

    def test_the_first_drafting_gate_re_asserts_the_budget_gate(self, manifest):
        """gate_10a carries the budget gate forward, so no draft slips past it."""
        gate = next(
            g
            for g in manifest["gate_registry"]
            if g["gate_id"] == "gate_10a_excellence_completeness"
        )
        assert any(
            "Budget gate must have passed" in c["prose"] for c in gate["conditions"]
        )

    def test_no_phase_8_output_exists(self):
        phase8 = (
            REPO / "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review"
        )
        sections = REPO / "docs/tier5_deliverables/proposal_sections"
        assert not list(phase8.glob("*.json"))
        assert not list(sections.glob("*.json"))


# ---------------------------------------------------------------------------
# The record of the work (§9.4, §12.1)
# ---------------------------------------------------------------------------


REPORT_REL = (
    "docs/tier4_orchestration_state/validation_reports/"
    "demo-budget-request-phase7_2026-10-01.json"
)
DECISION_REL = (
    "docs/tier4_orchestration_state/decision_log/"
    "demo-budget-request-phase7_2026-10-01.json"
)
FREEZE_REL = (
    "docs/tier4_orchestration_state/decision_log/"
    "demo-tier3-freeze-budget-request_2026-10-01.json"
)


@pytest.fixture(scope="module")
def report() -> dict:
    return _json(REPORT_REL)


@pytest.fixture(scope="module")
def decision() -> dict:
    return _json(DECISION_REL)


class TestTheRecord:
    def test_both_records_exist(self, report, decision):
        assert report["report_id"] == "demo-budget-request-phase7_2026-10-01"
        assert decision["record_type"] == "decision"

    def test_the_decision_points_at_the_validation_report(self, decision):
        assert decision["validation_report"] == REPORT_REL

    def test_the_three_criteria_carry_the_same_disposition_in_both(
        self, report, decision
    ):
        """A record that disagrees with itself is worse than no record."""
        assert [c["disposition"] for c in report["acceptance_criteria"]] == [
            c["disposition"] for c in decision["acceptance_criteria"]
        ]

    def test_the_two_human_step_criteria_are_not_claimed_as_plain_met(self, report):
        dispositions = [c["disposition"] for c in report["acceptance_criteria"]]
        assert dispositions[0] == "met"
        assert dispositions[1:] == ["met on the second branch"] * 2

    def test_every_criterion_carries_its_evidence(self, report):
        for criterion in report["acceptance_criteria"]:
            assert len(criterion["evidence"]) > 200

    def test_every_finding_carries_a_disposition(self, report):
        assert len(report["findings"]) == 10
        for finding in report["findings"]:
            assert finding["id"].startswith("F")
            assert finding["disposition"].strip()

    def test_every_decision_carries_its_reasoning_and_where_it_landed(self, decision):
        assert len(decision["decisions"]) == 9
        for entry in decision["decisions"]:
            assert entry["reasoning"].strip()
            assert entry["recorded_in"].strip()

    def test_the_four_status_categories_are_all_answered(self, report):
        assert set(report["status_summary"]) == {
            "Confirmed",
            "Inferred",
            "Assumed",
            "Unresolved",
        }

    def test_every_budget_figure_is_unresolved(self, report):
        assert "figure" in report["status_summary"]["Unresolved"]

    def test_the_counts_in_the_report_are_the_artifacts_own(self, report, request_payload):
        """The seeds ticket's D9: derive a count, never type it."""
        derived = report["the_request"]
        assert derived["work_packages"] == len(request_payload["work_packages"])
        assert derived["partners"] == len(request_payload["partners"])
        assert derived["fields_left_to_the_planner"] == 2 * (
            len(request_payload["work_packages"]) + len(request_payload["partners"])
        )

    def test_the_freeze_record_names_the_request_as_not_frozen(self):
        freeze = _json(FREEZE_REL)["freeze_record"]
        assert OUTPUT_REL in freeze["not_frozen"]
        assert OUTPUT_REL not in freeze["artifacts"]
        assert freeze["not_frozen"][OUTPUT_REL].strip()
