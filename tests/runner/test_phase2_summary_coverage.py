"""
Tests for Phase 2 scope_coverage in concept_refinement_summary.json.

Validates the all_mandatory_scope_covered predicate that ensures
concept_refinement_summary.json explicitly encodes coverage status for
all mandatory Tier 2B scope requirements.

Test cases:
  1. All mandatory elements covered → PASS
  2. Missing SR-09 → FAIL
  3. Missing SR-11 → FAIL
  4. scope_conflict_log == [] but missing coverage → FAIL
  5. Covered + valid references → PASS
  6. Unresolved → appears in both structures → PASS (correct fail behavior)
  7. scope_coverage absent → FAIL (MALFORMED_ARTIFACT)
  8. Invalid coverage_status value → FAIL
  9. Unresolved in scope_coverage but not in scope_conflict_log → FAIL
  10. Partial coverage (partially_covered) → PASS
  11. not_applicable status → PASS
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.predicates.scope_coverage_predicates import all_mandatory_scope_covered


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _make_scope_requirements(tmp_path: Path, requirements: list[dict]) -> Path:
    path = tmp_path / "scope_requirements.json"
    _write_json(path, {"requirements": requirements})
    return path


def _make_call_constraints(tmp_path: Path, constraints: list[dict]) -> Path:
    path = tmp_path / "call_constraints.json"
    _write_json(path, {"constraints": constraints})
    return path


def _make_summary(tmp_path: Path, scope_coverage: object, scope_conflict_log: list | None = None) -> Path:
    data = {
        "schema_id": "orch.phase2.concept_refinement_summary.v1",
        "run_id": "test-run-001",
        "topic_mapping_rationale": {},
        "scope_coverage": scope_coverage,
        "scope_conflict_log": scope_conflict_log or [],
        "strategic_differentiation": "Test differentiation",
    }
    path = tmp_path / "concept_refinement_summary.json"
    _write_json(path, data)
    return path


def _covered_entry(element_id: str, constraint_ref: str | None = None) -> dict:
    return {
        "scope_element_id": element_id,
        "constraint_ref": constraint_ref,
        "coverage_status": "covered",
        "coverage_description": f"Concept explicitly addresses {element_id}.",
        "tier2b_source_ref": f"call_entry.scope from source.json",
        "tier3_evidence_ref": f"project_brief/concept_note.md section X",
    }


def _partial_entry(element_id: str) -> dict:
    return {
        "scope_element_id": element_id,
        "constraint_ref": None,
        "coverage_status": "partially_covered",
        "coverage_description": f"Concept partially addresses {element_id}.",
        "tier2b_source_ref": "call_entry.scope from source.json",
        "tier3_evidence_ref": "project_brief/concept_note.md section Y",
    }


def _unresolved_entry(element_id: str) -> dict:
    return {
        "scope_element_id": element_id,
        "constraint_ref": None,
        "coverage_status": "unresolved",
        "coverage_description": f"Concept does not address {element_id}.",
        "tier2b_source_ref": "call_entry.scope from source.json",
        "tier3_evidence_ref": "",
    }


def _na_entry(element_id: str) -> dict:
    return {
        "scope_element_id": element_id,
        "constraint_ref": None,
        "coverage_status": "not_applicable",
        "coverage_description": f"{element_id} does not apply.",
        "tier2b_source_ref": "call_entry.scope from source.json",
        "tier3_evidence_ref": "",
        "notes": "This constraint does not apply to this proposal type.",
    }


# Standard mandatory requirements for tests
_MANDATORY_SR = [
    {"requirement_id": "SR-01", "mandatory": True},
    {"requirement_id": "SR-04", "mandatory": True},
    {"requirement_id": "SR-06", "mandatory": True},
    {"requirement_id": "SR-07", "mandatory": True},
    {"requirement_id": "SR-09", "mandatory": True},
    {"requirement_id": "SR-10", "mandatory": True},
    {"requirement_id": "SR-11", "mandatory": True},
]

_CONSTRAINTS = [
    {"constraint_id": "CC-01", "constraint_type": "scope"},
    {"constraint_id": "CC-03", "constraint_type": "partnership"},
    {"constraint_id": "CC-05", "constraint_type": "reporting"},
]


# ---------------------------------------------------------------------------
# Test 1: All mandatory elements covered → PASS
# ---------------------------------------------------------------------------

class TestAllCovered:

    def test_all_mandatory_covered_passes(self, tmp_path: Path) -> None:
        """When all mandatory SR and CC elements have 'covered' status → pass."""
        all_ids = [r["requirement_id"] for r in _MANDATORY_SR] + [
            c["constraint_id"] for c in _CONSTRAINTS
        ]
        coverage = {eid: _covered_entry(eid) for eid in all_ids}

        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(tmp_path, _MANDATORY_SR)
        constraints_path = _make_call_constraints(tmp_path, _CONSTRAINTS)

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is True
        assert result.details["all_covered"] is True
        assert result.details["mandatory_elements_checked"] == len(all_ids)


# ---------------------------------------------------------------------------
# Test 2: Missing SR-09 → FAIL
# ---------------------------------------------------------------------------

class TestMissingSR09:

    def test_missing_sr09_fails(self, tmp_path: Path) -> None:
        """When SR-09 is mandatory but absent from scope_coverage → fail."""
        all_ids = [r["requirement_id"] for r in _MANDATORY_SR] + [
            c["constraint_id"] for c in _CONSTRAINTS
        ]
        coverage = {eid: _covered_entry(eid) for eid in all_ids}
        del coverage["SR-09"]

        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(tmp_path, _MANDATORY_SR)
        constraints_path = _make_call_constraints(tmp_path, _CONSTRAINTS)

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is False
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert "SR-09" in result.details["missing_elements"]


# ---------------------------------------------------------------------------
# Test 3: Missing SR-11 → FAIL
# ---------------------------------------------------------------------------

class TestMissingSR11:

    def test_missing_sr11_fails(self, tmp_path: Path) -> None:
        """When SR-11 is mandatory but absent from scope_coverage → fail."""
        all_ids = [r["requirement_id"] for r in _MANDATORY_SR] + [
            c["constraint_id"] for c in _CONSTRAINTS
        ]
        coverage = {eid: _covered_entry(eid) for eid in all_ids}
        del coverage["SR-11"]

        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(tmp_path, _MANDATORY_SR)
        constraints_path = _make_call_constraints(tmp_path, _CONSTRAINTS)

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is False
        assert "SR-11" in result.details["missing_elements"]


# ---------------------------------------------------------------------------
# Test 4: Empty scope_conflict_log but missing coverage → FAIL
# ---------------------------------------------------------------------------

class TestEmptyConflictLogMissingCoverage:

    def test_empty_conflict_log_missing_coverage_fails(self, tmp_path: Path) -> None:
        """scope_conflict_log == [] but SR-09/SR-11 missing from coverage → fail."""
        # Only cover a subset
        coverage = {
            "SR-01": _covered_entry("SR-01"),
            "SR-04": _covered_entry("SR-04"),
            "SR-06": _covered_entry("SR-06"),
            "SR-07": _covered_entry("SR-07"),
            "SR-10": _covered_entry("SR-10"),
            "CC-01": _covered_entry("CC-01"),
            "CC-03": _covered_entry("CC-03"),
            "CC-05": _covered_entry("CC-05"),
        }
        # SR-09 and SR-11 are missing

        summary_path = _make_summary(tmp_path, coverage, scope_conflict_log=[])
        scope_path = _make_scope_requirements(tmp_path, _MANDATORY_SR)
        constraints_path = _make_call_constraints(tmp_path, _CONSTRAINTS)

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is False
        assert "SR-09" in result.details["missing_elements"]
        assert "SR-11" in result.details["missing_elements"]


# ---------------------------------------------------------------------------
# Test 5: Covered with valid references → PASS
# ---------------------------------------------------------------------------

class TestCoveredWithReferences:

    def test_covered_with_references_passes(self, tmp_path: Path) -> None:
        """All elements covered with proper references → pass."""
        all_ids = [r["requirement_id"] for r in _MANDATORY_SR] + [
            c["constraint_id"] for c in _CONSTRAINTS
        ]
        coverage = {}
        for eid in all_ids:
            coverage[eid] = {
                "scope_element_id": eid,
                "constraint_ref": None,
                "coverage_status": "covered",
                "coverage_description": f"Addressed via Pillar 1 for {eid}.",
                "tier2b_source_ref": "call_entry.scope from HORIZON-CL4-2026-05.json",
                "tier3_evidence_ref": "project_brief/concept_note.md line 42",
            }

        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(tmp_path, _MANDATORY_SR)
        constraints_path = _make_call_constraints(tmp_path, _CONSTRAINTS)

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is True


# ---------------------------------------------------------------------------
# Test 6: Unresolved in both scope_coverage and scope_conflict_log → FAIL
# ---------------------------------------------------------------------------

class TestUnresolvedInBoth:

    def test_unresolved_in_both_structures_fails(self, tmp_path: Path) -> None:
        """Unresolved coverage correctly appears in both → fails (correctly)."""
        all_ids = [r["requirement_id"] for r in _MANDATORY_SR] + [
            c["constraint_id"] for c in _CONSTRAINTS
        ]
        coverage = {eid: _covered_entry(eid) for eid in all_ids}
        # Mark SR-07 as unresolved
        coverage["SR-07"] = _unresolved_entry("SR-07")

        conflict_log = [{
            "conflict_id": "SR-07",
            "description": "Concept does not demonstrate in required sectors.",
            "resolution_status": "unresolved",
            "tier2b_source_ref": "call_entry.scope",
        }]

        summary_path = _make_summary(tmp_path, coverage, conflict_log)
        scope_path = _make_scope_requirements(tmp_path, _MANDATORY_SR)
        constraints_path = _make_call_constraints(tmp_path, _CONSTRAINTS)

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is False
        assert "SR-07" in result.details["unresolved_elements"]


# ---------------------------------------------------------------------------
# Test 7: scope_coverage absent → FAIL (MALFORMED_ARTIFACT)
# ---------------------------------------------------------------------------

class TestScopeCoverageAbsent:

    def test_missing_scope_coverage_field_fails(self, tmp_path: Path) -> None:
        """Summary without scope_coverage → MALFORMED_ARTIFACT."""
        data = {
            "schema_id": "orch.phase2.concept_refinement_summary.v1",
            "run_id": "test-run-001",
            "topic_mapping_rationale": {},
            "scope_conflict_log": [],
            "strategic_differentiation": "Test",
        }
        summary_path = tmp_path / "summary.json"
        _write_json(summary_path, data)
        scope_path = _make_scope_requirements(tmp_path, _MANDATORY_SR)
        constraints_path = _make_call_constraints(tmp_path, _CONSTRAINTS)

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is False
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "scope_coverage" in result.reason


# ---------------------------------------------------------------------------
# Test 8: Invalid coverage_status value → FAIL
# ---------------------------------------------------------------------------

class TestInvalidCoverageStatus:

    def test_invalid_status_fails(self, tmp_path: Path) -> None:
        """Entry with invalid coverage_status → fail."""
        coverage = {
            "SR-01": {
                "scope_element_id": "SR-01",
                "coverage_status": "maybe_covered",  # invalid
                "coverage_description": "Test",
                "tier2b_source_ref": "test",
                "tier3_evidence_ref": "test",
            },
        }
        # Only SR-01 as mandatory
        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(
            tmp_path, [{"requirement_id": "SR-01", "mandatory": True}],
        )
        constraints_path = _make_call_constraints(tmp_path, [])

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is False
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"


# ---------------------------------------------------------------------------
# Test 9: Unresolved in scope_coverage but NOT in scope_conflict_log → FAIL
# ---------------------------------------------------------------------------

class TestUnresolvedNotInConflictLog:

    def test_unresolved_without_conflict_log_entry_fails(self, tmp_path: Path) -> None:
        """Unresolved in coverage but absent from conflict log → fail."""
        coverage = {
            "SR-01": _unresolved_entry("SR-01"),
        }
        # No corresponding conflict log entry
        summary_path = _make_summary(tmp_path, coverage, scope_conflict_log=[])
        scope_path = _make_scope_requirements(
            tmp_path, [{"requirement_id": "SR-01", "mandatory": True}],
        )
        constraints_path = _make_call_constraints(tmp_path, [])

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is False
        assert "SR-01" in result.details["unresolved_elements"]
        assert "SR-01" in result.details["consistency_violations"]


# ---------------------------------------------------------------------------
# Test 10: Partially covered → PASS
# ---------------------------------------------------------------------------

class TestPartiallyCovered:

    def test_partially_covered_passes(self, tmp_path: Path) -> None:
        """partially_covered is a passing status (not blocking)."""
        coverage = {
            "SR-01": _partial_entry("SR-01"),
        }
        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(
            tmp_path, [{"requirement_id": "SR-01", "mandatory": True}],
        )
        constraints_path = _make_call_constraints(tmp_path, [])

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is True


# ---------------------------------------------------------------------------
# Test 11: not_applicable status → PASS
# ---------------------------------------------------------------------------

class TestNotApplicable:

    def test_not_applicable_passes(self, tmp_path: Path) -> None:
        """not_applicable is a passing status when justified."""
        coverage = {
            "CC-13": _na_entry("CC-13"),
        }
        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(tmp_path, [])
        constraints_path = _make_call_constraints(
            tmp_path, [{"constraint_id": "CC-13", "constraint_type": "other"}],
        )

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is True


# ---------------------------------------------------------------------------
# Test 12: Missing summary file → MISSING_MANDATORY_INPUT
# ---------------------------------------------------------------------------

class TestMissingSummaryFile:

    def test_missing_summary_file_fails(self, tmp_path: Path) -> None:
        """Summary file absent → MISSING_MANDATORY_INPUT."""
        scope_path = _make_scope_requirements(tmp_path, _MANDATORY_SR)
        constraints_path = _make_call_constraints(tmp_path, _CONSTRAINTS)

        result = all_mandatory_scope_covered(
            tmp_path / "nonexistent.json", scope_path, constraints_path,
        )

        assert result.passed is False
        assert result.failure_category == "MISSING_MANDATORY_INPUT"


# ---------------------------------------------------------------------------
# Test 13: Optional non-mandatory requirements not enforced
# ---------------------------------------------------------------------------

class TestNonMandatoryNotEnforced:

    def test_non_mandatory_sr_not_checked(self, tmp_path: Path) -> None:
        """Non-mandatory requirements are not required in scope_coverage."""
        requirements = [
            {"requirement_id": "SR-01", "mandatory": True},
            {"requirement_id": "SR-12", "mandatory": False},
        ]
        coverage = {
            "SR-01": _covered_entry("SR-01"),
            # SR-12 intentionally omitted — it's not mandatory
        }
        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(tmp_path, requirements)
        constraints_path = _make_call_constraints(tmp_path, [])

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is True


# ---------------------------------------------------------------------------
# Test 14: Constraints file absent → still checks mandatory SRs
# ---------------------------------------------------------------------------

class TestConstraintsFileAbsent:

    def test_missing_constraints_still_checks_srs(self, tmp_path: Path) -> None:
        """When call_constraints.json is absent, only SRs are checked."""
        requirements = [{"requirement_id": "SR-01", "mandatory": True}]
        coverage = {"SR-01": _covered_entry("SR-01")}

        summary_path = _make_summary(tmp_path, coverage)
        scope_path = _make_scope_requirements(tmp_path, requirements)
        constraints_path = tmp_path / "nonexistent_constraints.json"

        result = all_mandatory_scope_covered(
            summary_path, scope_path, constraints_path,
        )

        assert result.passed is True
