"""
Tests for the Lump Sum Budget Planner interface-contract validator.

``docs/integrations/lump_sum_budget_planner/interface_contract.json`` is a
*contract document* — it carries ``request_schema`` / ``response_schema``
blocks naming required fields — not a JSON Schema.  Read as a JSON Schema it
has no recognised keyword at its root, so it accepts every payload: the §8.5
obligation ("responses that do not conform must be rejected and flagged, not
silently accepted") was unenforced.  This module covers the validator that
interprets the contract document, for both roles.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.interface_contract import (
    ContractViolation,
    is_planner_contract,
    validate_payload,
)

REPO_CONTRACT = Path(
    "docs/integrations/lump_sum_budget_planner/interface_contract.json"
)
REPO_TEMPLATE = Path(
    "docs/integrations/lump_sum_budget_planner/request_templates/"
    "budget_request_template.json"
)


@pytest.fixture()
def contract() -> dict:
    return json.loads(REPO_CONTRACT.read_text(encoding="utf-8-sig"))


def _response(**overrides) -> dict:
    payload = {
        "response_id": "resp-1",
        "schema_version": "1.0",
        "work_packages": [{"wp_id": "WP1", "lump_sum": 100.0}],
        "partners": [{"partner_id": "P01", "total_effort_pm": 12.0}],
    }
    payload.update(overrides)
    return payload


def _request(**overrides) -> dict:
    payload = {
        "request_id": "req-1",
        "call_id": "CALL-1",
        "project_duration_months": 48,
        "work_packages": [{"wp_id": "WP1", "title": "T", "lead_partner": "P01"}],
        "partners": [
            {
                "partner_id": "P01",
                "name": "P01",
                "country": "C1",
                "role": "beneficiary",
            }
        ],
    }
    payload.update(overrides)
    return payload


class TestContractRecognition:
    def test_repo_contract_is_a_planner_contract_not_a_json_schema(self, contract):
        assert is_planner_contract(contract)

    def test_a_json_schema_is_not_a_planner_contract(self):
        assert not is_planner_contract(
            {"type": "object", "properties": {"a": {"type": "string"}}}
        )

    def test_empty_contract_is_not_a_planner_contract(self):
        assert not is_planner_contract({})

    def test_non_object_is_not_a_planner_contract(self):
        assert not is_planner_contract([1, 2, 3])


class TestResponseValidation:
    def test_conforming_response_has_no_violations(self, contract):
        assert validate_payload(_response(), contract, role="response") == []

    def test_missing_top_level_required_field_is_a_violation(self, contract):
        payload = _response()
        del payload["schema_version"]
        violations = validate_payload(payload, contract, role="response")
        assert [v.field for v in violations] == ["schema_version"]
        assert violations[0].requirement == "response_schema.required_fields"

    def test_null_required_field_counts_as_missing(self, contract):
        violations = validate_payload(
            _response(response_id=None), contract, role="response"
        )
        assert [v.field for v in violations] == ["response_id"]

    def test_empty_string_required_field_counts_as_missing(self, contract):
        violations = validate_payload(
            _response(response_id=""), contract, role="response"
        )
        assert [v.field for v in violations] == ["response_id"]

    def test_zero_is_a_value_not_a_missing_field(self, contract):
        payload = _response(
            work_packages=[{"wp_id": "WP1", "lump_sum": 0}],
            partners=[{"partner_id": "P01", "total_effort_pm": 0}],
        )
        assert validate_payload(payload, contract, role="response") == []

    def test_missing_work_package_entry_field_is_a_violation(self, contract):
        payload = _response(work_packages=[{"wp_id": "WP1"}])
        violations = validate_payload(payload, contract, role="response")
        assert [v.field for v in violations] == ["work_packages[0].lump_sum"]
        assert violations[0].requirement == "response_schema.work_package_entry"

    def test_missing_partner_entry_field_is_a_violation(self, contract):
        payload = _response(partners=[{"total_effort_pm": 4}])
        violations = validate_payload(payload, contract, role="response")
        assert [v.field for v in violations] == ["partners[0].partner_id"]

    def test_entry_collection_must_be_a_list(self, contract):
        violations = validate_payload(
            _response(work_packages={"wp_id": "WP1"}), contract, role="response"
        )
        assert [v.field for v in violations] == ["work_packages"]
        assert "list" in violations[0].detail

    def test_entry_must_be_an_object(self, contract):
        violations = validate_payload(
            _response(work_packages=["WP1"]), contract, role="response"
        )
        assert [v.field for v in violations] == ["work_packages[0]"]

    def test_negative_value_violates_no_negative_values(self, contract):
        payload = _response(work_packages=[{"wp_id": "WP1", "lump_sum": -1}])
        violations = validate_payload(payload, contract, role="response")
        assert [v.field for v in violations] == ["work_packages[0].lump_sum"]
        assert violations[0].requirement == "validation_rules.no_negative_values"

    def test_negative_value_at_any_depth_is_found(self, contract):
        payload = _response(
            work_packages=[
                {"wp_id": "WP1", "lump_sum": 1, "breakdown": {"personnel": -5}}
            ]
        )
        violations = validate_payload(payload, contract, role="response")
        assert [v.field for v in violations] == [
            "work_packages[0].breakdown.personnel"
        ]

    def test_booleans_are_not_treated_as_numbers(self, contract):
        payload = _response(
            work_packages=[{"wp_id": "WP1", "lump_sum": 1, "confirmed": False}]
        )
        assert validate_payload(payload, contract, role="response") == []

    def test_every_violation_is_reported_not_just_the_first(self, contract):
        payload = {"work_packages": [{"lump_sum": -1}], "partners": [{}]}
        violations = validate_payload(payload, contract, role="response")
        fields = [v.field for v in violations]
        assert "response_id" in fields
        assert "schema_version" in fields
        assert "work_packages[0].wp_id" in fields
        assert "work_packages[0].lump_sum" in fields
        assert "partners[0].partner_id" in fields
        assert "partners[0].total_effort_pm" in fields

    def test_payload_must_be_an_object(self, contract):
        violations = validate_payload([1, 2], contract, role="response")
        assert [v.field for v in violations] == ["$"]


class TestRequestValidation:
    def test_conforming_request_has_no_violations(self, contract):
        assert validate_payload(_request(), contract, role="request") == []

    def test_the_shipped_template_is_not_itself_a_conforming_request(self, contract):
        """The template carries empty placeholders. It is a shape, not a payload."""
        template = json.loads(REPO_TEMPLATE.read_text(encoding="utf-8-sig"))
        violations = validate_payload(template, contract, role="request")
        assert [v.field for v in violations] == [
            "request_id",
            "call_id",
            "work_packages[0].wp_id",
            "work_packages[0].title",
            "work_packages[0].lead_partner",
            "partners[0].partner_id",
            "partners[0].name",
            "partners[0].country",
            "partners[0].role",
        ]

    def test_request_role_uses_the_request_schema_required_fields(self, contract):
        payload = _request()
        del payload["project_duration_months"]
        violations = validate_payload(payload, contract, role="request")
        assert [v.field for v in violations] == ["project_duration_months"]

    def test_unknown_role_is_rejected(self, contract):
        with pytest.raises(ValueError):
            validate_payload(_request(), contract, role="banana")

    def test_a_contract_without_the_role_block_is_rejected(self):
        with pytest.raises(ValueError):
            validate_payload({}, {"request_schema": {}}, role="response")


class TestViolationShape:
    def test_violation_is_comparable_and_rendered(self, contract):
        violations = validate_payload(
            _response(response_id=""), contract, role="response"
        )
        assert isinstance(violations[0], ContractViolation)
        assert "response_id" in str(violations[0])
