"""
Tests for Step 5 — runner/predicates/schema_predicates.py

Covers all 13 predicate functions across §4.2 and §4.8.

All tests use synthetic temp files via pytest ``tmp_path``.  No dependency
on live repository artifacts.

Test organisation
-----------------
  §json_field_present     — 6 test cases
  §json_fields_present    — 3 test cases
  §instrument_type_matches_schema — 4 test cases
  §interface_contract_conforms    — 7 test cases
  §risk_register_populated        — 2 test cases
  §ethics_assessment_explicit     — 5 test cases
  §governance_matrix_present      — 2 test cases
  §no_blocking_inconsistencies    — 3 test cases
  §budget_gate_confirmation_present — 3 test cases
  §findings_categorised_by_severity — 3 test cases
  §revision_action_list_present   — 2 test cases
  §all_critical_revisions_resolved — 3 test cases
  §checkpoint_published           — 3 test cases
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.predicates.schema_predicates import (
    all_critical_revisions_resolved,
    budget_gate_confirmation_present,
    checkpoint_published,
    ethics_assessment_explicit,
    findings_categorised_by_severity,
    governance_matrix_present,
    instrument_type_matches_schema,
    interface_contract_conforms,
    json_field_present,
    json_fields_present,
    no_blocking_inconsistencies,
    revision_action_list_present,
    risk_register_populated,
)
from runner.predicates.types import (
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, content: object) -> Path:
    """Write *content* as JSON to *tmp_path/name* and return the path."""
    p = tmp_path / name
    p.write_text(json.dumps(content), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# §json_field_present
# ---------------------------------------------------------------------------


class TestJsonFieldPresent:
    def test_pass_field_exists_and_non_null(self, tmp_path):
        p = _write(tmp_path, "a.json", {"key": "value"})
        result = json_field_present(p, "key")
        assert result.passed

    def test_fail_missing_file(self, tmp_path):
        result = json_field_present(tmp_path / "missing.json", "key")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json", encoding="utf-8")
        result = json_field_present(p, "key")
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_non_object_json(self, tmp_path):
        p = _write(tmp_path, "a.json", [1, 2, 3])
        result = json_field_present(p, "key")
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_field_missing(self, tmp_path):
        p = _write(tmp_path, "a.json", {"other": "value"})
        result = json_field_present(p, "key")
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "key" in result.details.get("missing_field", "")

    def test_fail_field_null(self, tmp_path):
        p = _write(tmp_path, "a.json", {"key": None})
        result = json_field_present(p, "key")
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "key" in result.details.get("null_field", "")


# ---------------------------------------------------------------------------
# §json_fields_present
# ---------------------------------------------------------------------------


class TestJsonFieldsPresent:
    def test_pass_all_fields_present_and_non_null(self, tmp_path):
        p = _write(tmp_path, "a.json", {"a": 1, "b": "x", "c": True})
        result = json_fields_present(p, ["a", "b", "c"])
        assert result.passed
        assert result.details["fields_checked"] == ["a", "b", "c"]

    def test_fail_one_missing(self, tmp_path):
        p = _write(tmp_path, "a.json", {"a": 1, "c": True})
        result = json_fields_present(p, ["a", "b", "c"])
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "b" in result.details["missing_fields"]

    def test_fail_one_null(self, tmp_path):
        p = _write(tmp_path, "a.json", {"a": 1, "b": None, "c": True})
        result = json_fields_present(p, ["a", "b", "c"])
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "b" in result.details["null_fields"]


# ---------------------------------------------------------------------------
# §instrument_type_matches_schema
# ---------------------------------------------------------------------------


class TestInstrumentTypeMatchesSchema:
    def test_pass_instrument_type_found_in_registry(self, tmp_path):
        call = _write(tmp_path, "call.json", {"instrument_type": "RIA", "call_id": "HE-2025"})
        registry = _write(tmp_path, "registry.json", {"RIA": {}, "IA": {}, "CSA": {}})
        result = instrument_type_matches_schema(call, registry)
        assert result.passed
        assert result.details["instrument_type"] == "RIA"

    def test_fail_missing_instrument_type_field(self, tmp_path):
        call = _write(tmp_path, "call.json", {"call_id": "HE-2025"})
        registry = _write(tmp_path, "registry.json", {"RIA": {}})
        result = instrument_type_matches_schema(call, registry)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["missing_field"] == "instrument_type"

    def test_fail_instrument_type_not_found_in_registry(self, tmp_path):
        call = _write(tmp_path, "call.json", {"instrument_type": "UNKNOWN"})
        registry = _write(tmp_path, "registry.json", {"RIA": {}, "IA": {}})
        result = instrument_type_matches_schema(call, registry)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert "UNKNOWN" in result.reason

    def test_fail_malformed_registry(self, tmp_path):
        call = _write(tmp_path, "call.json", {"instrument_type": "RIA"})
        bad_registry = tmp_path / "registry.json"
        bad_registry.write_text("{invalid json", encoding="utf-8")
        result = instrument_type_matches_schema(call, bad_registry)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_null_instrument_type(self, tmp_path):
        call = _write(tmp_path, "call.json", {"instrument_type": None})
        registry = _write(tmp_path, "registry.json", {"RIA": {}})
        result = instrument_type_matches_schema(call, registry)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["null_field"] == "instrument_type"

    def test_fail_missing_call_file(self, tmp_path):
        registry = _write(tmp_path, "registry.json", {"RIA": {}})
        result = instrument_type_matches_schema(tmp_path / "missing.json", registry)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_schema_file(self, tmp_path):
        call = _write(tmp_path, "call.json", {"instrument_type": "RIA"})
        result = instrument_type_matches_schema(call, tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT


# ---------------------------------------------------------------------------
# §interface_contract_conforms
# ---------------------------------------------------------------------------


class TestInterfaceContractConforms:
    def test_pass_valid_contract_and_conforming_response(self, tmp_path):
        response_dir = tmp_path / "responses"
        response_dir.mkdir()
        _write(response_dir, "response.json", {"name": "test", "value": 42})
        contract = _write(
            tmp_path,
            "contract.json",
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "integer"},
                },
                "required": ["name"],
            },
        )
        result = interface_contract_conforms(response_dir, contract)
        assert result.passed
        assert result.details["json_files_validated"] == 1

    def test_fail_invalid_response_json(self, tmp_path):
        response_dir = tmp_path / "responses"
        response_dir.mkdir()
        bad = response_dir / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        contract = _write(tmp_path, "contract.json", {})
        result = interface_contract_conforms(response_dir, contract)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_contract_violation(self, tmp_path):
        response_dir = tmp_path / "responses"
        response_dir.mkdir()
        _write(response_dir, "response.json", {"name": 99})  # name should be string
        contract = _write(
            tmp_path,
            "contract.json",
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        )
        result = interface_contract_conforms(response_dir, contract)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert len(result.details["violations"]) >= 1

    def test_fail_missing_contract(self, tmp_path):
        response_dir = tmp_path / "responses"
        response_dir.mkdir()
        result = interface_contract_conforms(response_dir, tmp_path / "missing_contract.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_response_dir(self, tmp_path):
        contract = _write(tmp_path, "contract.json", {})
        result = interface_contract_conforms(tmp_path / "missing_dir", contract)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_pass_no_json_files_in_dir(self, tmp_path):
        """
        No .json files in directory → pass (presence confirmed by dir_non_empty).
        """
        response_dir = tmp_path / "responses"
        response_dir.mkdir()
        (response_dir / "not_json.txt").write_text("hello", encoding="utf-8")
        contract = _write(tmp_path, "contract.json", {})
        result = interface_contract_conforms(response_dir, contract)
        assert result.passed
        assert result.details["json_files_validated"] == 0

    def test_pass_empty_contract_accepts_any_json(self, tmp_path):
        """Empty contract {} is a valid JSON Schema that accepts everything."""
        response_dir = tmp_path / "responses"
        response_dir.mkdir()
        _write(response_dir, "r.json", {"anything": [1, 2, 3], "nested": {"x": True}})
        contract = _write(tmp_path, "contract.json", {})
        result = interface_contract_conforms(response_dir, contract)
        assert result.passed

    def test_fail_response_path_is_a_file_not_dir(self, tmp_path):
        file_path = _write(tmp_path, "not_a_dir.json", {})
        contract = _write(tmp_path, "contract.json", {})
        result = interface_contract_conforms(file_path, contract)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT


# ---------------------------------------------------------------------------
# §risk_register_populated
# ---------------------------------------------------------------------------


class TestRiskRegisterPopulated:
    def _full_register(self, tmp_path: Path) -> Path:
        return _write(
            tmp_path,
            "impl.json",
            {
                "risk_register": [
                    {
                        "risk_id": "R1",
                        "description": "Budget overrun",
                        "likelihood": "medium",
                        "impact": "high",
                        "mitigation": "Monthly financial reviews",
                    }
                ]
            },
        )

    def test_pass_valid_register(self, tmp_path):
        p = self._full_register(tmp_path)
        result = risk_register_populated(p)
        assert result.passed
        assert result.details["risk_register_count"] == 1

    def test_fail_risk_register_absent(self, tmp_path):
        p = _write(tmp_path, "impl.json", {"other": "data"})
        result = risk_register_populated(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_empty_risk_register(self, tmp_path):
        p = _write(tmp_path, "impl.json", {"risk_register": []})
        result = risk_register_populated(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_missing_mitigation(self, tmp_path):
        p = _write(
            tmp_path,
            "impl.json",
            {
                "risk_register": [
                    {
                        "risk_id": "R1",
                        "likelihood": "low",
                        "impact": "low",
                        # mitigation absent
                    }
                ]
            },
        )
        result = risk_register_populated(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["missing_or_null_field"] == "mitigation"

    def test_fail_null_likelihood(self, tmp_path):
        p = _write(
            tmp_path,
            "impl.json",
            {
                "risk_register": [
                    {
                        "risk_id": "R1",
                        "likelihood": None,
                        "impact": "medium",
                        "mitigation": "Some measure",
                    }
                ]
            },
        )
        result = risk_register_populated(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["missing_or_null_field"] == "likelihood"


# ---------------------------------------------------------------------------
# §ethics_assessment_explicit
# ---------------------------------------------------------------------------


class TestEthicsAssessmentExplicit:
    def test_pass_valid_object_with_statement(self, tmp_path):
        p = _write(
            tmp_path,
            "impl.json",
            {
                "ethics_assessment": {
                    "ethics_issues_identified": False,
                    "issues": [],
                    "self_assessment_statement": "No ethics issues identified.",
                }
            },
        )
        result = ethics_assessment_explicit(p)
        assert result.passed

    def test_fail_field_absent(self, tmp_path):
        p = _write(tmp_path, "impl.json", {"other": "data"})
        result = ethics_assessment_explicit(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_placeholder_sentinel_string(self, tmp_path):
        """Top-level field set to the sentinel string "N/A"."""
        p = _write(tmp_path, "impl.json", {"ethics_assessment": "N/A"})
        result = ethics_assessment_explicit(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert "N/A" in result.reason

    def test_fail_empty_string(self, tmp_path):
        p = _write(tmp_path, "impl.json", {"ethics_assessment": ""})
        result = ethics_assessment_explicit(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_object_with_sentinel_statement(self, tmp_path):
        """self_assessment_statement set to sentinel "N/A"."""
        p = _write(
            tmp_path,
            "impl.json",
            {
                "ethics_assessment": {
                    "ethics_issues_identified": False,
                    "issues": [],
                    "self_assessment_statement": "N/A",
                }
            },
        )
        result = ethics_assessment_explicit(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION

    def test_fail_object_with_empty_statement(self, tmp_path):
        p = _write(
            tmp_path,
            "impl.json",
            {
                "ethics_assessment": {
                    "ethics_issues_identified": True,
                    "issues": [],
                    "self_assessment_statement": "   ",
                }
            },
        )
        result = ethics_assessment_explicit(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_object_missing_statement(self, tmp_path):
        p = _write(
            tmp_path,
            "impl.json",
            {
                "ethics_assessment": {
                    "ethics_issues_identified": False,
                    "issues": [],
                    # self_assessment_statement absent
                }
            },
        )
        result = ethics_assessment_explicit(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT


# ---------------------------------------------------------------------------
# §governance_matrix_present
# ---------------------------------------------------------------------------


class TestGovernanceMatrixPresent:
    def test_pass_non_empty_array(self, tmp_path):
        p = _write(
            tmp_path,
            "impl.json",
            {
                "governance_matrix": [
                    {
                        "body_name": "Project Board",
                        "composition": ["P1", "P2"],
                        "decision_scope": "Strategic",
                    }
                ]
            },
        )
        result = governance_matrix_present(p)
        assert result.passed
        assert result.details["governance_matrix_entries"] == 1

    def test_fail_empty_array(self, tmp_path):
        p = _write(tmp_path, "impl.json", {"governance_matrix": []})
        result = governance_matrix_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["length"] == 0

    def test_fail_field_absent(self, tmp_path):
        p = _write(tmp_path, "impl.json", {"other": "data"})
        result = governance_matrix_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT


# ---------------------------------------------------------------------------
# §no_blocking_inconsistencies
# ---------------------------------------------------------------------------


class TestNoBlockingInconsistencies:
    def test_pass_field_absent(self, tmp_path):
        p = _write(tmp_path, "budget.json", {"gate_pass_declaration": "pass"})
        result = no_blocking_inconsistencies(p)
        assert result.passed
        assert result.details["blocking_inconsistencies"] == "absent"

    def test_pass_all_resolved(self, tmp_path):
        p = _write(
            tmp_path,
            "budget.json",
            {
                "blocking_inconsistencies": [
                    {
                        "inconsistency_id": "I1",
                        "description": "WP3 missing",
                        "severity": "blocking",
                        "resolution": "resolved",
                    }
                ]
            },
        )
        result = no_blocking_inconsistencies(p)
        assert result.passed

    def test_fail_unresolved_entry_exists(self, tmp_path):
        p = _write(
            tmp_path,
            "budget.json",
            {
                "blocking_inconsistencies": [
                    {
                        "inconsistency_id": "I2",
                        "description": "Partner mismatch",
                        "severity": "blocking",
                        "resolution": "unresolved",
                    }
                ]
            },
        )
        result = no_blocking_inconsistencies(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert "I2" in result.details["unresolved_ids"]


# ---------------------------------------------------------------------------
# §budget_gate_confirmation_present
# ---------------------------------------------------------------------------


class TestBudgetGateConfirmationPresent:
    def test_pass_declaration_is_pass(self, tmp_path):
        p = _write(tmp_path, "budget.json", {"gate_pass_declaration": "pass"})
        result = budget_gate_confirmation_present(p)
        assert result.passed

    def test_fail_declaration_is_fail(self, tmp_path):
        p = _write(tmp_path, "budget.json", {"gate_pass_declaration": "fail"})
        result = budget_gate_confirmation_present(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert result.details["gate_pass_declaration"] == "fail"

    def test_fail_field_absent(self, tmp_path):
        p = _write(tmp_path, "budget.json", {"other": "data"})
        result = budget_gate_confirmation_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_field_null(self, tmp_path):
        p = _write(tmp_path, "budget.json", {"gate_pass_declaration": None})
        result = budget_gate_confirmation_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT


# ---------------------------------------------------------------------------
# §findings_categorised_by_severity
# ---------------------------------------------------------------------------


class TestFindingsCategorisedBySeverity:
    def test_pass_all_findings_have_valid_severity(self, tmp_path):
        p = _write(
            tmp_path,
            "review.json",
            {
                "findings": [
                    {
                        "finding_id": "F1",
                        "section_id": "S1",
                        "criterion": "Excellence",
                        "description": "Weak objectives",
                        "severity": "major",
                    },
                    {
                        "finding_id": "F2",
                        "section_id": "S2",
                        "criterion": "Impact",
                        "description": "Good pathway",
                        "severity": "minor",
                    },
                ]
            },
        )
        result = findings_categorised_by_severity(p)
        assert result.passed
        assert result.details["findings_count"] == 2

    def test_fail_invalid_severity_value(self, tmp_path):
        p = _write(
            tmp_path,
            "review.json",
            {
                "findings": [
                    {
                        "finding_id": "F1",
                        "section_id": "S1",
                        "criterion": "C1",
                        "description": "D1",
                        "severity": "blocker",  # not in allowed set
                    }
                ]
            },
        )
        result = findings_categorised_by_severity(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert "blocker" in result.reason

    def test_fail_missing_severity(self, tmp_path):
        p = _write(
            tmp_path,
            "review.json",
            {
                "findings": [
                    {
                        "finding_id": "F1",
                        "section_id": "S1",
                        "criterion": "C1",
                        "description": "D1",
                        # severity absent
                    }
                ]
            },
        )
        result = findings_categorised_by_severity(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_findings_field_absent(self, tmp_path):
        p = _write(tmp_path, "review.json", {"other": "data"})
        result = findings_categorised_by_severity(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_pass_empty_findings_array(self, tmp_path):
        """Empty findings array: no entries to violate — predicate passes."""
        p = _write(tmp_path, "review.json", {"findings": []})
        result = findings_categorised_by_severity(p)
        assert result.passed
        assert result.details["findings_count"] == 0


# ---------------------------------------------------------------------------
# §revision_action_list_present
# ---------------------------------------------------------------------------


class TestRevisionActionListPresent:
    def test_pass_non_empty_list(self, tmp_path):
        p = _write(
            tmp_path,
            "review.json",
            {
                "revision_actions": [
                    {
                        "action_id": "A1",
                        "finding_id": "F1",
                        "priority": 1,
                        "action_description": "Rewrite section 1",
                        "target_section": "S1",
                        "severity": "critical",
                    }
                ]
            },
        )
        result = revision_action_list_present(p)
        assert result.passed
        assert result.details["revision_actions_count"] == 1

    def test_fail_empty_list(self, tmp_path):
        p = _write(tmp_path, "review.json", {"revision_actions": []})
        result = revision_action_list_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["length"] == 0

    def test_fail_field_absent(self, tmp_path):
        p = _write(tmp_path, "review.json", {"other": "data"})
        result = revision_action_list_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT


# ---------------------------------------------------------------------------
# §all_critical_revisions_resolved
# ---------------------------------------------------------------------------


class TestAllCriticalRevisionsResolved:
    # ------------------------------------------------------------------
    # Structural validation — MALFORMED_ARTIFACT (corrective patch)
    # ------------------------------------------------------------------

    def test_fail_field_absent(self, tmp_path):
        """revision_actions is required: true per schema §1.8 — absent → MALFORMED."""
        p = _write(tmp_path, "status.json", {"section_completion_log": []})
        result = all_critical_revisions_resolved(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_field_absent_details(self, tmp_path):
        p = _write(tmp_path, "status.json", {"section_completion_log": []})
        result = all_critical_revisions_resolved(p)
        assert result.details.get("missing_field") == "revision_actions"

    def test_fail_wrong_type_string(self, tmp_path):
        """revision_actions is type: array per schema — string → MALFORMED."""
        p = _write(tmp_path, "status.json", {"revision_actions": "oops"})
        result = all_critical_revisions_resolved(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_wrong_type_dict(self, tmp_path):
        """revision_actions is type: array per schema — object → MALFORMED."""
        p = _write(tmp_path, "status.json", {"revision_actions": {}})
        result = all_critical_revisions_resolved(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_wrong_type_details_contain_actual_type(self, tmp_path):
        p = _write(tmp_path, "status.json", {"revision_actions": "oops"})
        result = all_critical_revisions_resolved(p)
        assert result.details.get("actual_type") == "str"

    # ------------------------------------------------------------------
    # Empty list — pass (non-empty requirement belongs to revision_action_list_present)
    # ------------------------------------------------------------------

    def test_pass_empty_list(self, tmp_path):
        """Empty revision_actions list has no violations — passes."""
        p = _write(tmp_path, "status.json", {"revision_actions": []})
        result = all_critical_revisions_resolved(p)
        assert result.passed

    # ------------------------------------------------------------------
    # Policy logic — POLICY_VIOLATION
    # ------------------------------------------------------------------

    def test_fail_unresolved_critical_without_reason(self, tmp_path):
        p = _write(
            tmp_path,
            "status.json",
            {
                "revision_actions": [
                    {
                        "action_id": "A2",
                        "section_id": "S2",
                        "severity": "critical",
                        "description": "Impact section incomplete",
                        "status": "unresolved",
                        # reason absent
                    }
                ]
            },
        )
        result = all_critical_revisions_resolved(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert "A2" in result.details["unresolved_critical_ids"]

    def test_fail_unresolved_critical_with_blank_reason(self, tmp_path):
        p = _write(
            tmp_path,
            "status.json",
            {
                "revision_actions": [
                    {
                        "action_id": "A3",
                        "section_id": "S3",
                        "severity": "critical",
                        "description": "Missing evidence",
                        "status": "unresolved",
                        "reason": "   ",  # blank — not acceptable
                    }
                ]
            },
        )
        result = all_critical_revisions_resolved(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION

    # ------------------------------------------------------------------
    # Pass cases — policy logic
    # ------------------------------------------------------------------

    def test_pass_unresolved_critical_with_reason(self, tmp_path):
        """Unresolved critical with non-empty reason is acceptable per plan."""
        p = _write(
            tmp_path,
            "status.json",
            {
                "revision_actions": [
                    {
                        "action_id": "A1",
                        "section_id": "S1",
                        "severity": "critical",
                        "description": "Unresolvable scope conflict",
                        "status": "unresolved",
                        "reason": "Call scope closed before resolution possible",
                    }
                ]
            },
        )
        result = all_critical_revisions_resolved(p)
        assert result.passed

    def test_pass_critical_resolved(self, tmp_path):
        """Critical entry with status resolved — no violation."""
        p = _write(
            tmp_path,
            "status.json",
            {
                "revision_actions": [
                    {
                        "action_id": "A1",
                        "section_id": "S1",
                        "severity": "critical",
                        "description": "Fix this",
                        "status": "resolved",
                    }
                ]
            },
        )
        result = all_critical_revisions_resolved(p)
        assert result.passed

    def test_pass_non_critical_unresolved_without_reason(self, tmp_path):
        """Major/minor unresolved without reason: not governed by this predicate."""
        p = _write(
            tmp_path,
            "status.json",
            {
                "revision_actions": [
                    {
                        "action_id": "A4",
                        "section_id": "S4",
                        "severity": "major",
                        "description": "Minor formatting",
                        "status": "unresolved",
                    }
                ]
            },
        )
        result = all_critical_revisions_resolved(p)
        assert result.passed

    def test_pass_minor_unresolved_without_reason(self, tmp_path):
        p = _write(
            tmp_path,
            "status.json",
            {
                "revision_actions": [
                    {
                        "action_id": "A5",
                        "section_id": "S5",
                        "severity": "minor",
                        "description": "Typo",
                        "status": "unresolved",
                    }
                ]
            },
        )
        result = all_critical_revisions_resolved(p)
        assert result.passed


# ---------------------------------------------------------------------------
# §checkpoint_published
# ---------------------------------------------------------------------------


class TestCheckpointPublished:
    def test_pass_status_published(self, tmp_path):
        p = _write(
            tmp_path,
            "checkpoint.json",
            {
                "status": "published",
                "run_id": "run-001",
                "published_at": "2026-01-01T00:00:00Z",
                "gate_results_confirmed": ["gate_09_budget_consistency"],
            },
        )
        result = checkpoint_published(p)
        assert result.passed
        assert result.details["status"] == "published"

    def test_fail_status_not_published(self, tmp_path):
        p = _write(tmp_path, "checkpoint.json", {"status": "pending"})
        result = checkpoint_published(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert "pending" in result.reason

    def test_fail_status_absent(self, tmp_path):
        p = _write(tmp_path, "checkpoint.json", {"run_id": "run-001"})
        result = checkpoint_published(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_missing_file(self, tmp_path):
        result = checkpoint_published(tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_invalid_json(self, tmp_path):
        p = tmp_path / "checkpoint.json"
        p.write_text("{bad json", encoding="utf-8")
        result = checkpoint_published(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
