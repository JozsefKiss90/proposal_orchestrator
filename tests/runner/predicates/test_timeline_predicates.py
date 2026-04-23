"""
Unit tests for Step 9 — Timeline predicates
(runner/predicates/timeline_predicates.py).

All tests use synthetic temporary files only.  No live repository artifacts
are read.

Artifact structural assumptions encoded in these tests
------------------------------------------------------
gantt.json:
    {"tasks": [...], "milestones": [...], "critical_path": [...]}

selected_call.json:
    {"project_duration_months": <int>, ...}

wp_structure.json:
    {"work_packages": [{"wp_id": "WP1", ...}, ...], ...}

section_schema_registry.json (Form A — instrument-type keys):
    {"RIA": {"max_work_packages": 8, ...}}

section_schema_registry.json (Form B — instruments array):
    {"instruments": [{"instrument_type": "RIA", "max_work_packages": 8}]}
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from runner.predicates.timeline_predicates import (
    all_milestones_have_criteria,
    critical_path_present,
    dependency_schedule_consistency,
    timeline_within_duration,
    wp_count_within_limit,
)
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_dir: Path, name: str, content: Any) -> str:
    path = tmp_dir / name
    path.write_text(json.dumps(content), encoding="utf-8")
    return str(path)


def _task(task_id: str, wp_id: str, start: int, end: int) -> dict:
    return {
        "task_id": task_id,
        "wp_id": wp_id,
        "start_month": start,
        "end_month": end,
        "responsible_partner": "P1",
    }


def _ms(ms_id: str, due: int, criterion: str) -> dict:
    return {
        "milestone_id": ms_id,
        "title": f"Title for {ms_id}",
        "due_month": due,
        "verifiable_criterion": criterion,
        "responsible_wp": "WP1",
    }


def _gantt(tasks: list, milestones: list, critical_path: Any = None) -> dict:
    data: dict = {
        "schema_id": "orch.phase4.gantt.v1",
        "run_id": "test-run-001",
        "tasks": tasks,
        "milestones": milestones,
    }
    if critical_path is not None:
        data["critical_path"] = critical_path
    return data


def _call(duration: Any = 36) -> dict:
    return {
        "call_id": "HORIZON-TEST-2024-01",
        "topic_code": "HORIZON-TEST-2024-01-01",
        "instrument_type": "RIA",
        "project_duration_months": duration,
    }


def _wp_structure(wp_ids: list[str]) -> dict:
    return {
        "schema_id": "orch.phase3.wp_structure.v1",
        "run_id": "test-run-001",
        "work_packages": [{"wp_id": w} for w in wp_ids],
    }


def _registry_form_a(max_wps: int, instrument: str = "RIA") -> dict:
    """Form A: object with instrument-type keys."""
    return {instrument: {"max_work_packages": max_wps, "sections": []}}


def _registry_form_b(max_wps: int, instrument: str = "RIA") -> dict:
    """Form B: object with instruments array."""
    return {
        "instruments": [
            {
                "instrument_type": instrument,
                "max_work_packages": max_wps,
                "sections": [],
                "evaluation_form_ref": "eval_form_ria.json",
            }
        ]
    }


# ===========================================================================
# timeline_within_duration
# ===========================================================================


class TestTimelineWithinDuration:
    def test_pass_all_tasks_within_duration(self, tmp_path):
        """All task end months ≤ 36 → pass."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(
                [_task("T1", "WP1", 1, 6), _task("T2", "WP1", 7, 18), _task("T3", "WP2", 1, 36)],
                [],
                ["T1", "T2", "T3"],
            ),
        )
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is True
        assert result.details["project_duration_months"] == 36
        assert result.details["task_count"] == 3

    def test_pass_empty_tasks(self, tmp_path):
        """No tasks → vacuous pass."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], ["T1"]))
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is True

    def test_fail_missing_gantt_file(self, tmp_path):
        """Missing gantt.json → MISSING_MANDATORY_INPUT."""
        gantt = str(tmp_path / "nonexistent_gantt.json")
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_call_file(self, tmp_path):
        """Missing selected_call.json → MISSING_MANDATORY_INPUT."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], []))
        call = str(tmp_path / "nonexistent_call.json")
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_invalid_gantt_json(self, tmp_path):
        """Invalid JSON in gantt → MALFORMED_ARTIFACT."""
        gantt = str(tmp_path / "gantt.json")
        Path(gantt).write_text("{ not valid json }", encoding="utf-8")
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_invalid_call_json(self, tmp_path):
        """Invalid JSON in call → MALFORMED_ARTIFACT."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], []))
        call = str(tmp_path / "selected_call.json")
        Path(call).write_text("not json", encoding="utf-8")
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_missing_duration_field(self, tmp_path):
        """selected_call.json without project_duration_months → MALFORMED_ARTIFACT."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], []))
        call = _write(tmp_path, "selected_call.json", {"call_id": "X"})
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "project_duration_months" in result.reason

    def test_fail_duration_is_string(self, tmp_path):
        """project_duration_months is a string → MALFORMED_ARTIFACT."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], []))
        call = _write(tmp_path, "selected_call.json", _call("36"))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_duration_is_float(self, tmp_path):
        """project_duration_months is a float → MALFORMED_ARTIFACT."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], []))
        call = _write(tmp_path, "selected_call.json", _call(36.5))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_duration_is_zero(self, tmp_path):
        """project_duration_months = 0 (non-positive) → MALFORMED_ARTIFACT."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], []))
        call = _write(tmp_path, "selected_call.json", _call(0))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_task_end_month_exceeds_duration(self, tmp_path):
        """One task ends at month 37, duration is 36 → CROSS_ARTIFACT_INCONSISTENCY."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(
                [_task("T1", "WP1", 1, 36), _task("T2", "WP2", 1, 37)],
                [],
                ["T1", "T2"],
            ),
        )
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert result.details["over_duration_count"] == 1
        assert any(e["task_id"] == "T2" for e in result.details["over_duration_tasks"])

    def test_fail_multiple_tasks_over_duration(self, tmp_path):
        """Two tasks exceed duration → all reported."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(
                [_task("T1", "WP1", 1, 40), _task("T2", "WP2", 1, 50)],
                [],
                ["T1"],
            ),
        )
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert result.details["over_duration_count"] == 2

    def test_fail_task_missing_end_month(self, tmp_path):
        """Task dict without end_month → MALFORMED_ARTIFACT."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(
                [{"task_id": "T1", "wp_id": "WP1", "start_month": 1}],
                [],
                [],
            ),
        )
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_task_end_month_is_string(self, tmp_path):
        """Task end_month is a string → MALFORMED_ARTIFACT."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(
                [{"task_id": "T1", "wp_id": "WP1", "start_month": 1, "end_month": "6"}],
                [],
                [],
            ),
        )
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_task_entry_not_dict(self, tmp_path):
        """Task entry is a string, not a dict → MALFORMED_ARTIFACT."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(["T1-WP1-1-6"], [], []),
        )
        call = _write(tmp_path, "selected_call.json", _call(36))
        result = timeline_within_duration(gantt, call)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT


# ===========================================================================
# all_milestones_have_criteria
# ===========================================================================


class TestAllMilestonesHaveCriteria:
    def test_pass_all_milestones_valid(self, tmp_path):
        """Valid milestones with criterion and due_month → pass."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(
                [],
                [
                    _ms("MS1", 6, "First prototype delivered to project steering committee"),
                    _ms("MS2", 18, "Beta software released on public repository"),
                ],
                ["MS1", "MS2"],
            ),
        )
        result = all_milestones_have_criteria(gantt)
        assert result.passed is True
        assert result.details["milestone_count"] == 2

    def test_pass_empty_milestones(self, tmp_path):
        """Empty milestones list → vacuous pass."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], []))
        result = all_milestones_have_criteria(gantt)
        assert result.passed is True

    def test_fail_missing_file(self, tmp_path):
        """Missing file → MISSING_MANDATORY_INPUT."""
        result = all_milestones_have_criteria(str(tmp_path / "missing.json"))
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_invalid_json(self, tmp_path):
        """Invalid JSON → MALFORMED_ARTIFACT."""
        p = str(tmp_path / "gantt.json")
        Path(p).write_text("not json", encoding="utf-8")
        result = all_milestones_have_criteria(p)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_milestones_field_missing(self, tmp_path):
        """gantt.json without milestones field → MALFORMED_ARTIFACT."""
        gantt = _write(tmp_path, "gantt.json", {"schema_id": "x", "tasks": []})
        result = all_milestones_have_criteria(gantt)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "milestones" in result.reason

    def test_fail_milestones_not_a_list(self, tmp_path):
        """milestones is a dict → MALFORMED_ARTIFACT."""
        data = _gantt([], {}, [])  # dict instead of list
        data["milestones"] = {"MS1": {}}
        gantt = _write(tmp_path, "gantt.json", data)
        result = all_milestones_have_criteria(gantt)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_milestone_missing_criterion_field(self, tmp_path):
        """Milestone without verifiable_criterion key → CROSS_ARTIFACT_INCONSISTENCY."""
        ms = {
            "milestone_id": "MS1",
            "title": "Something",
            "due_month": 6,
            # verifiable_criterion missing
            "responsible_wp": "WP1",
        }
        gantt = _write(tmp_path, "gantt.json", _gantt([], [ms], ["MS1"]))
        result = all_milestones_have_criteria(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_milestone_blank_criterion(self, tmp_path):
        """Blank-only verifiable_criterion → CROSS_ARTIFACT_INCONSISTENCY."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(
                [],
                [_ms("MS1", 6, "   ")],  # whitespace only
                ["MS1"],
            ),
        )
        result = all_milestones_have_criteria(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert result.details["incomplete_count"] == 1

    def test_fail_milestone_null_criterion(self, tmp_path):
        """verifiable_criterion is null → CROSS_ARTIFACT_INCONSISTENCY."""
        ms = _ms("MS1", 6, "placeholder")
        ms["verifiable_criterion"] = None
        gantt = _write(tmp_path, "gantt.json", _gantt([], [ms], ["MS1"]))
        result = all_milestones_have_criteria(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_milestone_missing_due_month(self, tmp_path):
        """Milestone without due_month → CROSS_ARTIFACT_INCONSISTENCY."""
        ms = {
            "milestone_id": "MS1",
            "title": "Something",
            "verifiable_criterion": "Report submitted to coordinator",
            "responsible_wp": "WP1",
            # due_month absent
        }
        gantt = _write(tmp_path, "gantt.json", _gantt([], [ms], ["MS1"]))
        result = all_milestones_have_criteria(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_milestone_null_due_month(self, tmp_path):
        """due_month is null → CROSS_ARTIFACT_INCONSISTENCY."""
        ms = _ms("MS1", 6, "Criterion text")
        ms["due_month"] = None
        gantt = _write(tmp_path, "gantt.json", _gantt([], [ms], ["MS1"]))
        result = all_milestones_have_criteria(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_partial_milestones_reports_all(self, tmp_path):
        """Multiple incomplete milestones → all reported in details."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt(
                [],
                [
                    _ms("MS1", 6, "Valid criterion"),
                    _ms("MS2", 12, "   "),  # blank
                    _ms("MS3", 18, "Another valid"),
                ],
                ["MS1", "MS2", "MS3"],
            ),
        )
        # Manually null the due_month on MS3
        data = json.loads(Path(_write(tmp_path, "gantt2.json", _gantt(
            [],
            [
                _ms("MS1", 6, "Valid criterion"),
                _ms("MS2", 12, "   "),   # blank
            ],
            [],
        ))).read_text(encoding="utf-8") if False else "null")

        # Simpler: write directly
        content = {
            "schema_id": "orch.phase4.gantt.v1",
            "run_id": "r1",
            "tasks": [],
            "milestones": [
                _ms("MS1", 6, "   "),  # blank
                _ms("MS2", 12, "   "),  # blank
            ],
            "critical_path": [],
        }
        p = _write(tmp_path, "gantt_multi.json", content)
        result = all_milestones_have_criteria(p)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert result.details["incomplete_count"] == 2

    # --- Backward-compatibility: optional depends_on_tasks / milestone_type ---

    def test_pass_milestone_with_depends_on_tasks(self, tmp_path):
        """Milestone with optional depends_on_tasks field still passes criteria check."""
        ms = _ms("MS1", 6, "Architecture review completed")
        ms["depends_on_tasks"] = ["T1-01"]
        ms["milestone_type"] = "intermediate_checkpoint"
        gantt = _write(tmp_path, "gantt.json", _gantt([], [ms], ["MS1"]))
        result = all_milestones_have_criteria(gantt)
        assert result.passed is True

    def test_pass_milestone_without_new_fields(self, tmp_path):
        """Legacy milestone without depends_on_tasks/milestone_type still passes."""
        gantt = _write(
            tmp_path, "gantt.json",
            _gantt([], [_ms("MS1", 6, "Valid criterion")], ["MS1"]),
        )
        result = all_milestones_have_criteria(gantt)
        assert result.passed is True

    def test_pass_wp_completion_milestone(self, tmp_path):
        """wp_completion milestone with all fields passes criteria check."""
        ms = _ms("MS1", 36, "All WP outputs delivered")
        ms["depends_on_tasks"] = ["T1-01", "T1-02"]
        ms["milestone_type"] = "wp_completion"
        gantt = _write(tmp_path, "gantt.json", _gantt([], [ms], ["MS1"]))
        result = all_milestones_have_criteria(gantt)
        assert result.passed is True


# ===========================================================================
# wp_count_within_limit
# ===========================================================================


class TestWpCountWithinLimit:
    def test_pass_count_below_limit_form_a(self, tmp_path):
        """3 WPs, limit = 8 (Form A registry) → pass."""
        wp = _write(tmp_path, "wp_structure.json", _wp_structure(["WP1", "WP2", "WP3"]))
        schema = _write(tmp_path, "section_schema_registry.json", _registry_form_a(8))
        result = wp_count_within_limit(wp, schema)
        assert result.passed is True
        assert result.details["wp_count"] == 3
        assert result.details["max_work_packages"] == 8

    def test_pass_count_equal_to_limit_form_b(self, tmp_path):
        """5 WPs, limit = 5 (Form B registry) → pass (boundary)."""
        wp = _write(
            tmp_path,
            "wp_structure.json",
            _wp_structure(["WP1", "WP2", "WP3", "WP4", "WP5"]),
        )
        schema = _write(tmp_path, "section_schema_registry.json", _registry_form_b(5))
        result = wp_count_within_limit(wp, schema)
        assert result.passed is True
        assert result.details["wp_count"] == 5

    def test_pass_zero_wps(self, tmp_path):
        """0 WPs, limit = 8 → pass."""
        wp = _write(tmp_path, "wp_structure.json", _wp_structure([]))
        schema = _write(tmp_path, "section_schema_registry.json", _registry_form_a(8))
        result = wp_count_within_limit(wp, schema)
        assert result.passed is True

    def test_fail_missing_wp_file(self, tmp_path):
        """Missing wp_structure.json → MISSING_MANDATORY_INPUT."""
        wp = str(tmp_path / "missing_wp.json")
        schema = _write(tmp_path, "section_schema_registry.json", _registry_form_a(8))
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_schema_file(self, tmp_path):
        """Missing schema registry → MISSING_MANDATORY_INPUT."""
        wp = _write(tmp_path, "wp_structure.json", _wp_structure(["WP1"]))
        schema = str(tmp_path / "missing_schema.json")
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_malformed_work_packages_not_list(self, tmp_path):
        """work_packages is a dict → MALFORMED_ARTIFACT."""
        wp = _write(tmp_path, "wp_structure.json", {"work_packages": {"WP1": {}}})
        schema = _write(tmp_path, "section_schema_registry.json", _registry_form_a(8))
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_missing_work_packages_field(self, tmp_path):
        """wp_structure.json without work_packages field → MALFORMED_ARTIFACT."""
        wp = _write(tmp_path, "wp_structure.json", {"schema_id": "x"})
        schema = _write(tmp_path, "section_schema_registry.json", _registry_form_a(8))
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_malformed_schema_registry(self, tmp_path):
        """Schema registry is an array (not supported) → MALFORMED_ARTIFACT."""
        wp = _write(tmp_path, "wp_structure.json", _wp_structure(["WP1"]))
        schema = _write(tmp_path, "section_schema_registry.json", [{"max_work_packages": 8}])
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_no_max_wp_constraint_form_a(self, tmp_path):
        """Registry has instruments but no max_work_packages → MALFORMED_ARTIFACT."""
        wp = _write(tmp_path, "wp_structure.json", _wp_structure(["WP1"]))
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {"RIA": {"sections": [], "evaluation_form_ref": "eval.json"}},  # no max_work_packages
        )
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "max_work_packages" in result.reason

    def test_fail_no_max_wp_constraint_form_b(self, tmp_path):
        """Form B registry with instruments but no max_work_packages → MALFORMED_ARTIFACT."""
        wp = _write(tmp_path, "wp_structure.json", _wp_structure(["WP1"]))
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {
                "instruments": [
                    {"instrument_type": "RIA", "sections": [], "evaluation_form_ref": "x.json"}
                ]
            },
        )
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_count_exceeds_limit(self, tmp_path):
        """9 WPs, limit = 8 → POLICY_VIOLATION."""
        wp = _write(
            tmp_path,
            "wp_structure.json",
            _wp_structure([f"WP{i}" for i in range(1, 10)]),  # 9 WPs
        )
        schema = _write(tmp_path, "section_schema_registry.json", _registry_form_a(8))
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == POLICY_VIOLATION
        assert result.details["wp_count"] == 9
        assert result.details["max_work_packages"] == 8

    def test_fail_count_exceeds_limit_uses_minimum_across_instruments(self, tmp_path):
        """
        Registry has two instruments: RIA limit 8, IA limit 6.
        6 WPs with minimum-based check should fail (min = 6, 6 ≤ 6 → pass? No, it passes).
        Use 7 WPs to fail.
        """
        wp = _write(
            tmp_path,
            "wp_structure.json",
            _wp_structure([f"WP{i}" for i in range(1, 8)]),  # 7 WPs
        )
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {"RIA": {"max_work_packages": 8}, "IA": {"max_work_packages": 6}},
        )
        result = wp_count_within_limit(wp, schema)
        # min(8, 6) = 6; 7 > 6 → POLICY_VIOLATION
        assert result.passed is False
        assert result.failure_category == POLICY_VIOLATION
        assert result.details["max_work_packages"] == 6  # minimum was applied

    def test_pass_minimum_across_instruments_within_limit(self, tmp_path):
        """5 WPs, min(8, 6) = 6 → 5 ≤ 6 → pass."""
        wp = _write(
            tmp_path,
            "wp_structure.json",
            _wp_structure([f"WP{i}" for i in range(1, 6)]),  # 5 WPs
        )
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {"RIA": {"max_work_packages": 8}, "IA": {"max_work_packages": 6}},
        )
        result = wp_count_within_limit(wp, schema)
        assert result.passed is True
        assert result.details["max_work_packages"] == 6

    # -----------------------------------------------------------------------
    # null max_work_packages — "no hard upper bound defined"
    # -----------------------------------------------------------------------

    def test_pass_null_max_wp_form_b(self, tmp_path):
        """Form B registry with max_work_packages: null → pass (no hard constraint)."""
        wp = _write(
            tmp_path,
            "wp_structure.json",
            _wp_structure([f"WP{i}" for i in range(1, 9)]),  # 8 WPs
        )
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {
                "instruments": [
                    {
                        "instrument_type": "RIA",
                        "max_work_packages": None,
                        "max_work_packages_note": "No maximum stated in form.",
                    }
                ]
            },
        )
        result = wp_count_within_limit(wp, schema)
        assert result.passed is True
        assert result.details["max_work_packages"] is None
        assert "no hard numeric wp limit" in result.details.get("note", "").lower()

    def test_pass_null_max_wp_form_a(self, tmp_path):
        """Form A registry with max_work_packages: null → pass (no hard constraint)."""
        wp = _write(
            tmp_path,
            "wp_structure.json",
            _wp_structure([f"WP{i}" for i in range(1, 11)]),  # 10 WPs
        )
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {"RIA": {"max_work_packages": None, "sections": []}},
        )
        result = wp_count_within_limit(wp, schema)
        assert result.passed is True
        assert result.details["max_work_packages"] is None

    def test_mixed_null_and_integer_uses_integer(self, tmp_path):
        """Registry with one null and one integer limit → uses the integer."""
        wp = _write(
            tmp_path,
            "wp_structure.json",
            _wp_structure([f"WP{i}" for i in range(1, 8)]),  # 7 WPs
        )
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {
                "RIA": {"max_work_packages": None},  # null
                "IA": {"max_work_packages": 6},  # integer
            },
        )
        result = wp_count_within_limit(wp, schema)
        # 7 > 6 → should fail using the integer limit
        assert result.passed is False
        assert result.failure_category == POLICY_VIOLATION
        assert result.details["max_work_packages"] == 6

    def test_fail_no_instrument_entries_at_all(self, tmp_path):
        """Empty registry with no instrument entries → MALFORMED_ARTIFACT."""
        wp = _write(tmp_path, "wp_structure.json", _wp_structure(["WP1"]))
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {"instruments": []},  # no entries
        )
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "no instrument entries" in result.reason.lower()

    def test_fail_field_absent_not_null(self, tmp_path):
        """Instrument entry exists but max_work_packages field absent → MALFORMED_ARTIFACT."""
        wp = _write(tmp_path, "wp_structure.json", _wp_structure(["WP1"]))
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {"RIA": {"sections": []}},  # no max_work_packages key at all
        )
        result = wp_count_within_limit(wp, schema)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_pass_real_registry_shape(self, tmp_path):
        """Registry matching the real section_schema_registry.json shape with null max → pass."""
        wp = _write(
            tmp_path,
            "wp_structure.json",
            _wp_structure([f"WP{i}" for i in range(1, 9)]),  # 8 WPs
        )
        # Mimics the actual repo structure
        schema = _write(
            tmp_path,
            "section_schema_registry.json",
            {
                "instruments": [
                    {
                        "instrument_type": "RIA",
                        "evaluation_form_ref": "ef_he-ria-ia_en.pdf",
                        "max_work_packages": None,
                        "max_work_packages_note": (
                            "No maximum work package count stated in form. "
                            "Form states: 'the number of work packages should be "
                            "proportionate to the scale and complexity of the project.'"
                        ),
                        "source_document": "af_he-ria-ia_en.pdf",
                        "sections": [],
                    }
                ]
            },
        )
        result = wp_count_within_limit(wp, schema)
        assert result.passed is True
        assert result.details["wp_count"] == 8
        assert result.details["max_work_packages"] is None


# ===========================================================================
# critical_path_present
# ===========================================================================


class TestCriticalPathPresent:
    def test_pass_non_empty_list(self, tmp_path):
        """Non-empty critical_path list → pass."""
        gantt = _write(
            tmp_path,
            "gantt.json",
            _gantt([], [], ["T1.1", "T2.3", "MS1"]),
        )
        result = critical_path_present(gantt)
        assert result.passed is True
        assert result.details["critical_path_type"] == "list"
        assert result.details["critical_path_length"] == 3

    def test_pass_non_empty_string(self, tmp_path):
        """Non-empty string critical_path → pass (alternative representation)."""
        data = _gantt([], [], None)
        data["critical_path"] = "T1.1 → T2.3 → MS1"
        gantt = _write(tmp_path, "gantt.json", data)
        result = critical_path_present(gantt)
        assert result.passed is True
        assert result.details["critical_path_type"] == "str"

    def test_pass_non_empty_object(self, tmp_path):
        """Non-empty dict critical_path → pass (alternative representation)."""
        data = _gantt([], [], None)
        data["critical_path"] = {"start": "T1.1", "end": "MS3"}
        gantt = _write(tmp_path, "gantt.json", data)
        result = critical_path_present(gantt)
        assert result.passed is True
        assert result.details["critical_path_type"] == "dict"
        assert result.details["critical_path_length"] == 2

    def test_fail_missing_file(self, tmp_path):
        """Missing file → MISSING_MANDATORY_INPUT."""
        result = critical_path_present(str(tmp_path / "missing.json"))
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_invalid_json(self, tmp_path):
        """Invalid JSON → MALFORMED_ARTIFACT."""
        p = str(tmp_path / "gantt.json")
        Path(p).write_text("[ unclosed", encoding="utf-8")
        result = critical_path_present(p)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_critical_path_missing(self, tmp_path):
        """gantt.json without critical_path field → CROSS_ARTIFACT_INCONSISTENCY."""
        data = {"schema_id": "x", "tasks": [], "milestones": []}
        gantt = _write(tmp_path, "gantt.json", data)
        result = critical_path_present(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_critical_path_null(self, tmp_path):
        """critical_path: null → CROSS_ARTIFACT_INCONSISTENCY."""
        data = _gantt([], [], None)
        data["critical_path"] = None
        gantt = _write(tmp_path, "gantt.json", data)
        result = critical_path_present(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_critical_path_empty_string(self, tmp_path):
        """critical_path: "" → CROSS_ARTIFACT_INCONSISTENCY."""
        data = _gantt([], [], None)
        data["critical_path"] = ""
        gantt = _write(tmp_path, "gantt.json", data)
        result = critical_path_present(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_critical_path_whitespace_string(self, tmp_path):
        """critical_path: "   " (whitespace) → CROSS_ARTIFACT_INCONSISTENCY."""
        data = _gantt([], [], None)
        data["critical_path"] = "   "
        gantt = _write(tmp_path, "gantt.json", data)
        result = critical_path_present(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_critical_path_empty_list(self, tmp_path):
        """critical_path: [] → CROSS_ARTIFACT_INCONSISTENCY."""
        gantt = _write(tmp_path, "gantt.json", _gantt([], [], []))
        result = critical_path_present(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_critical_path_empty_object(self, tmp_path):
        """critical_path: {} → CROSS_ARTIFACT_INCONSISTENCY."""
        data = _gantt([], [], None)
        data["critical_path"] = {}
        gantt = _write(tmp_path, "gantt.json", data)
        result = critical_path_present(gantt)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_details_path_present_on_all_results(self, tmp_path):
        """'path' key present in details for both pass and fail."""
        # Pass
        gantt_pass = _write(tmp_path, "gantt_pass.json", _gantt([], [], ["T1"]))
        r_pass = critical_path_present(gantt_pass)
        assert "path" in r_pass.details

        # Fail (missing)
        r_fail = critical_path_present(str(tmp_path / "absent.json"))
        assert "path" in r_fail.details


# ===========================================================================
# dependency_schedule_consistency tests
# ===========================================================================


class TestDependencyScheduleConsistency:
    """Tests for the Phase 4 dependency-schedule consistency predicate."""

    @staticmethod
    def _write_triple(tmp_path, gantt, wp_structure, sc):
        """Write gantt.json, wp_structure.json, and scheduling_constraints.json."""
        g = tmp_path / "gantt.json"
        g.write_text(json.dumps(gantt), encoding="utf-8")
        w = tmp_path / "wp_structure.json"
        w.write_text(json.dumps(wp_structure), encoding="utf-8")
        s = tmp_path / "scheduling_constraints.json"
        s.write_text(json.dumps(sc), encoding="utf-8")
        return str(g), str(w), str(s)

    @staticmethod
    def _base_wp_structure():
        return {
            "work_packages": [
                {"wp_id": "WP1", "tasks": [{"task_id": "T1-01"}, {"task_id": "T1-02"}]},
                {"wp_id": "WP2", "tasks": [{"task_id": "T2-01"}, {"task_id": "T2-02"}]},
            ],
        }

    def test_pass_all_strict_satisfied(self, tmp_path):
        """All strict constraints satisfied → PASS."""
        gantt = {
            "tasks": [
                {"task_id": "T1-01", "wp_id": "WP1", "start_month": 1, "end_month": 12},
                {"task_id": "T1-02", "wp_id": "WP1", "start_month": 6, "end_month": 18},
                {"task_id": "T2-01", "wp_id": "WP2", "start_month": 19, "end_month": 30},
                {"task_id": "T2-02", "wp_id": "WP2", "start_month": 24, "end_month": 36},
            ],
        }
        sc = {
            "strict_constraints": [
                # T1-02 ends M18, T2-01 starts M19 → 18 <= 19 ✓
                {"from": "T1-02", "to": "T2-01", "original_edge_type": "finish_to_start",
                 "action": "preserved", "reason": "task-level"},
            ],
            "non_strict_constraints": [],
        }
        gp, wp, sp = self._write_triple(tmp_path, gantt, self._base_wp_structure(), sc)
        result = dependency_schedule_consistency(gp, wp, sp)
        assert result.passed is True

    def test_fail_strict_violated(self, tmp_path):
        """Strict constraint violated → FAIL with CROSS_ARTIFACT_INCONSISTENCY."""
        gantt = {
            "tasks": [
                {"task_id": "T1-02", "wp_id": "WP1", "start_month": 1, "end_month": 30},
                {"task_id": "T2-01", "wp_id": "WP2", "start_month": 25, "end_month": 36},
            ],
        }
        sc = {
            "strict_constraints": [
                # T1-02 ends M30, T2-01 starts M25 → 30 > 25 ✗
                {"from": "T1-02", "to": "T2-01", "original_edge_type": "finish_to_start",
                 "action": "preserved", "reason": "task-level"},
            ],
            "non_strict_constraints": [],
        }
        gp, wp, sp = self._write_triple(tmp_path, gantt, self._base_wp_structure(), sc)
        result = dependency_schedule_consistency(gp, wp, sp)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert len(result.details["violations"]) == 1
        v = result.details["violations"][0]
        assert v["from"] == "T1-02"
        assert v["to"] == "T2-01"

    def test_non_strict_ignored(self, tmp_path):
        """Non-strict constraints don't cause failure even when violated."""
        gantt = {
            "tasks": [
                {"task_id": "T1-02", "wp_id": "WP1", "start_month": 1, "end_month": 30},
                {"task_id": "T2-01", "wp_id": "WP2", "start_month": 10, "end_month": 36},
            ],
        }
        sc = {
            # strict_constraints empty; only non-strict (would be violated)
            "strict_constraints": [],
            "non_strict_constraints": [
                {"from": "T1-02", "to": "T2-01", "original_edge_type": "finish_to_start",
                 "action": "reclassified", "reason": "WP-level infeasible"},
            ],
        }
        gp, wp, sp = self._write_triple(tmp_path, gantt, self._base_wp_structure(), sc)
        result = dependency_schedule_consistency(gp, wp, sp)
        assert result.passed is True

    def test_missing_gantt(self, tmp_path):
        """Missing gantt.json → MISSING_MANDATORY_INPUT."""
        wp = tmp_path / "wp.json"
        wp.write_text(json.dumps(self._base_wp_structure()), encoding="utf-8")
        sc = tmp_path / "sc.json"
        sc.write_text(json.dumps({"strict_constraints": [], "non_strict_constraints": []}), encoding="utf-8")
        result = dependency_schedule_consistency(
            str(tmp_path / "absent_gantt.json"), str(wp), str(sc)
        )
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_missing_scheduling_constraints(self, tmp_path):
        """Missing scheduling_constraints.json → MISSING_MANDATORY_INPUT."""
        gantt = tmp_path / "gantt.json"
        gantt.write_text(json.dumps({"tasks": []}), encoding="utf-8")
        wp = tmp_path / "wp.json"
        wp.write_text(json.dumps(self._base_wp_structure()), encoding="utf-8")
        result = dependency_schedule_consistency(
            str(gantt), str(wp), str(tmp_path / "absent_sc.json")
        )
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_empty_strict_constraints_passes(self, tmp_path):
        """Empty strict_constraints → passes trivially."""
        gantt = {
            "tasks": [
                {"task_id": "T1-01", "wp_id": "WP1", "start_month": 1, "end_month": 12},
            ],
        }
        sc = {"strict_constraints": [], "non_strict_constraints": []}
        gp, wp, sp = self._write_triple(tmp_path, gantt, self._base_wp_structure(), sc)
        result = dependency_schedule_consistency(gp, wp, sp)
        assert result.passed is True
        assert result.details["total_strict_constraints"] == 0

    def test_wp_level_strict_constraint(self, tmp_path):
        """WP-level strict constraint resolves to task max/min months."""
        gantt = {
            "tasks": [
                {"task_id": "T1-01", "wp_id": "WP1", "start_month": 1, "end_month": 10},
                {"task_id": "T1-02", "wp_id": "WP1", "start_month": 5, "end_month": 18},
                {"task_id": "T2-01", "wp_id": "WP2", "start_month": 19, "end_month": 30},
                {"task_id": "T2-02", "wp_id": "WP2", "start_month": 24, "end_month": 36},
            ],
        }
        sc = {
            "strict_constraints": [
                # WP1 max end = 18, WP2 min start = 19 → 18 <= 19 ✓
                {"from": "WP1", "to": "WP2", "original_edge_type": "finish_to_start",
                 "action": "preserved", "reason": "feasible WP-level"},
            ],
            "non_strict_constraints": [],
        }
        gp, wp, sp = self._write_triple(tmp_path, gantt, self._base_wp_structure(), sc)
        result = dependency_schedule_consistency(gp, wp, sp)
        assert result.passed is True
