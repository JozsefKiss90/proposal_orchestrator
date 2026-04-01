"""
Tests for Step 6 — runner/predicates/source_ref_predicates.py

Covers both predicate functions:

    source_refs_present(path)
    all_mappings_have_source_refs(path)

All tests use synthetic temp files via pytest ``tmp_path``.  No dependency
on live repository artifacts.

Test organisation
-----------------
  §source_refs_present     — 14 cases
  §all_mappings_have_source_refs — 11 cases
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.predicates.source_ref_predicates import (
    all_mappings_have_source_refs,
    source_refs_present,
)
from runner.predicates.types import (
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, content: object) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(content), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# §source_refs_present
# ---------------------------------------------------------------------------


class TestSourceRefsPresent:
    # ── Pass cases ──────────────────────────────────────────────────────────

    def test_pass_array_with_source_ref(self, tmp_path):
        """Array form: every entry has 'source_ref'."""
        p = _write(
            tmp_path,
            "constraints.json",
            [
                {"constraint_id": "C1", "description": "D1", "source_ref": "§2.1"},
                {"constraint_id": "C2", "description": "D2", "source_ref": "§3.4"},
            ],
        )
        result = source_refs_present(p)
        assert result.passed
        assert result.details["entries_checked"] == 2

    def test_pass_array_with_source_section(self, tmp_path):
        """Array form: every entry has 'source_section'."""
        p = _write(
            tmp_path,
            "outcomes.json",
            [
                {"id": "O1", "text": "Some outcome", "source_section": "2.2.1"},
            ],
        )
        result = source_refs_present(p)
        assert result.passed

    def test_pass_array_mixed_fields(self, tmp_path):
        """Array form: some entries use 'source_ref', others 'source_section'."""
        p = _write(
            tmp_path,
            "mixed.json",
            [
                {"id": "A", "source_ref": "§1.1"},
                {"id": "B", "source_section": "3.2"},
                {"id": "C", "source_ref": "§5.0", "source_section": "5.0.1"},
            ],
        )
        result = source_refs_present(p)
        assert result.passed
        assert result.details["entries_checked"] == 3

    def test_pass_object_single_item_with_source_section(self, tmp_path):
        """Object form — single item: dict itself has 'source_section'."""
        p = _write(
            tmp_path,
            "item.json",
            {"id": "X1", "description": "A constraint", "source_section": "4.1"},
        )
        result = source_refs_present(p)
        assert result.passed
        assert result.details["entries_checked"] == 1

    def test_pass_object_dict_of_entries(self, tmp_path):
        """Object form — dict-of-entries: each value dict has 'source_ref'."""
        p = _write(
            tmp_path,
            "registry.json",
            {
                "entry_a": {"description": "A", "source_ref": "§1"},
                "entry_b": {"description": "B", "source_section": "2.3"},
            },
        )
        result = source_refs_present(p)
        assert result.passed
        assert result.details["entries_checked"] == 2

    def test_pass_empty_array_vacuous(self, tmp_path):
        """Empty array: vacuous pass (no entries to violate)."""
        p = _write(tmp_path, "empty.json", [])
        result = source_refs_present(p)
        assert result.passed
        assert result.details["entries_checked"] == 0
        assert "vacuous" in result.details["note"].lower()

    # ── Fail cases ──────────────────────────────────────────────────────────

    def test_fail_missing_file(self, tmp_path):
        result = source_refs_present(tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid json", encoding="utf-8")
        result = source_refs_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_unsupported_entry_type_scalar_in_array(self, tmp_path):
        """Array contains a scalar where dict is required → MALFORMED_ARTIFACT."""
        p = _write(tmp_path, "items.json", ["string_entry", {"source_ref": "§1"}])
        result = source_refs_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["entry_type"] == "str"

    def test_fail_unsupported_top_level_scalar(self, tmp_path):
        """Top-level is a scalar (not array or object) → MALFORMED_ARTIFACT."""
        p = _write(tmp_path, "bad.json", 42)
        result = source_refs_present(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_missing_both_source_fields(self, tmp_path):
        """Entry has neither 'source_ref' nor 'source_section' → POLICY_VIOLATION."""
        p = _write(
            tmp_path,
            "items.json",
            [
                {"id": "C1", "description": "No ref at all"},
            ],
        )
        result = source_refs_present(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert "[0]" in result.details["missing_source_ref_entries"]

    def test_fail_source_ref_null(self, tmp_path):
        """'source_ref' present but null: not a valid reference → POLICY_VIOLATION."""
        p = _write(
            tmp_path,
            "items.json",
            [{"id": "C1", "source_ref": None}],
        )
        result = source_refs_present(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION

    def test_fail_source_section_blank_string(self, tmp_path):
        """'source_section' present but blank → POLICY_VIOLATION."""
        p = _write(
            tmp_path,
            "items.json",
            [{"id": "C1", "source_section": "   "}],
        )
        result = source_refs_present(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION

    def test_fail_object_dict_of_entries_one_missing(self, tmp_path):
        """Dict-of-entries form: one value dict is missing source ref → POLICY_VIOLATION."""
        p = _write(
            tmp_path,
            "registry.json",
            {
                "entry_ok": {"description": "A", "source_ref": "§1"},
                "entry_bad": {"description": "B"},  # no source ref
            },
        )
        result = source_refs_present(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        assert "entry_bad" in result.details["missing_source_ref_entries"]

    def test_fail_partial_entries_report(self, tmp_path):
        """Multiple entries with missing refs: all are reported."""
        p = _write(
            tmp_path,
            "items.json",
            [
                {"id": "A", "source_ref": "§1"},
                {"id": "B"},
                {"id": "C", "source_section": "3.2"},
                {"id": "D"},
            ],
        )
        result = source_refs_present(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        missing = result.details["missing_source_ref_entries"]
        assert "[1]" in missing
        assert "[3]" in missing
        assert "[0]" not in missing  # A passes
        assert "[2]" not in missing  # C passes


# ---------------------------------------------------------------------------
# §all_mappings_have_source_refs
# ---------------------------------------------------------------------------


class TestAllMappingsHaveSourceRefs:
    # ── Pass cases ──────────────────────────────────────────────────────────

    def test_pass_valid_array_mapping_entries(self, tmp_path):
        """Array form: every entry has both required source channels."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            [
                {
                    "topic_element_id": "EO1",
                    "mapping_to_concept": "WP2 delivers outcome EO1",
                    "tier2b_source_ref": "WP2025-TOPIC §2.3",
                    "tier3_evidence_ref": "docs/tier3.../objectives.json#obj_1",
                },
                {
                    "topic_element_id": "EO2",
                    "mapping_to_concept": "WP3 addresses EO2",
                    "tier2b_source_ref": "WP2025-TOPIC §3.1",
                    "tier3_evidence_ref": "docs/tier3.../project_brief/concept.json",
                },
            ],
        )
        result = all_mappings_have_source_refs(p)
        assert result.passed
        assert result.details["entries_checked"] == 2

    def test_pass_object_single_entry(self, tmp_path):
        """Object form — single entry: dict itself has both required fields."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            {
                "topic_element_id": "EO1",
                "mapping_to_concept": "Maps perfectly",
                "tier2b_source_ref": "§2.4",
                "tier3_evidence_ref": "tier3/brief/concept.json",
            },
        )
        result = all_mappings_have_source_refs(p)
        assert result.passed
        assert result.details["entries_checked"] == 1

    def test_pass_object_dict_of_entries(self, tmp_path):
        """Object form — dict-of-entries: each value dict has both fields."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            {
                "EO1": {
                    "topic_element_id": "EO1",
                    "tier2b_source_ref": "WP §2.3",
                    "tier3_evidence_ref": "tier3/objectives.json",
                },
                "EO2": {
                    "topic_element_id": "EO2",
                    "tier2b_source_ref": "WP §3.1",
                    "tier3_evidence_ref": "tier3/brief/project_summary.json",
                },
            },
        )
        result = all_mappings_have_source_refs(p)
        assert result.passed
        assert result.details["entries_checked"] == 2

    def test_pass_empty_array_vacuous(self, tmp_path):
        p = _write(tmp_path, "topic_mapping.json", [])
        result = all_mappings_have_source_refs(p)
        assert result.passed
        assert result.details["entries_checked"] == 0

    # ── Fail cases ──────────────────────────────────────────────────────────

    def test_fail_missing_file(self, tmp_path):
        result = all_mappings_have_source_refs(tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid json", encoding="utf-8")
        result = all_mappings_have_source_refs(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_malformed_top_level_type(self, tmp_path):
        """Top-level is a scalar → MALFORMED_ARTIFACT."""
        p = _write(tmp_path, "bad.json", "not an array or object")
        result = all_mappings_have_source_refs(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_array_entry_not_a_dict(self, tmp_path):
        """Array entry is not an object → MALFORMED_ARTIFACT."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            [
                "plain string",
                {
                    "tier2b_source_ref": "§1",
                    "tier3_evidence_ref": "tier3/x.json",
                },
            ],
        )
        result = all_mappings_have_source_refs(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_missing_tier2b_source_ref(self, tmp_path):
        """Entry missing 'tier2b_source_ref' → POLICY_VIOLATION."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            [
                {
                    "topic_element_id": "EO1",
                    # tier2b_source_ref absent
                    "tier3_evidence_ref": "tier3/objectives.json",
                },
            ],
        )
        result = all_mappings_have_source_refs(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        viol = result.details["violations"]
        assert any("tier2b_source_ref" in v["missing"] for v in viol)

    def test_fail_missing_tier3_evidence_ref(self, tmp_path):
        """Entry missing 'tier3_evidence_ref' → POLICY_VIOLATION."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            [
                {
                    "topic_element_id": "EO1",
                    "tier2b_source_ref": "WP §2.3",
                    # tier3_evidence_ref absent
                },
            ],
        )
        result = all_mappings_have_source_refs(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        viol = result.details["violations"]
        assert any("tier3_evidence_ref" in v["missing"] for v in viol)

    def test_fail_blank_values(self, tmp_path):
        """Both fields present but blank strings → POLICY_VIOLATION."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            [
                {
                    "topic_element_id": "EO1",
                    "tier2b_source_ref": "   ",
                    "tier3_evidence_ref": "",
                },
            ],
        )
        result = all_mappings_have_source_refs(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        viol = result.details["violations"]
        assert viol[0]["entry"] == "[0]"
        assert "tier2b_source_ref" in viol[0]["missing"]
        assert "tier3_evidence_ref" in viol[0]["missing"]

    def test_fail_null_values(self, tmp_path):
        """Fields present but null → POLICY_VIOLATION."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            [
                {
                    "topic_element_id": "EO1",
                    "tier2b_source_ref": None,
                    "tier3_evidence_ref": None,
                },
            ],
        )
        result = all_mappings_have_source_refs(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION

    def test_fail_multiple_entry_report(self, tmp_path):
        """Multiple violating entries: all are identified in details."""
        p = _write(
            tmp_path,
            "topic_mapping.json",
            [
                {
                    "topic_element_id": "EO1",
                    "tier2b_source_ref": "§1",
                    "tier3_evidence_ref": "tier3/x.json",
                },  # passes
                {
                    "topic_element_id": "EO2",
                    "tier2b_source_ref": "§2",
                    # tier3_evidence_ref absent
                },
                {
                    "topic_element_id": "EO3",
                    # both absent
                },
            ],
        )
        result = all_mappings_have_source_refs(p)
        assert not result.passed
        assert result.failure_category == POLICY_VIOLATION
        viol_entries = [v["entry"] for v in result.details["violations"]]
        assert "[1]" in viol_entries
        assert "[2]" in viol_entries
        assert "[0]" not in viol_entries
        assert result.details["entries_checked"] == 3
