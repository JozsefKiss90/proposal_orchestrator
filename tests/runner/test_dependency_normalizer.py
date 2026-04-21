"""Tests for runner.dependency_normalizer — Phase 4 scheduling constraint normalization."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from runner.dependency_normalizer import (
    DependencyNormalizerError,
    normalize_dependencies,
    SCHEMA_ID,
    WP_STRUCTURE_REL,
    WP_SEED_REL,
    SELECTED_CALL_REL,
    OUTPUT_REL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_wp_structure(*, edges=None, run_id="test-run-phase3"):
    """Build a minimal wp_structure.json dict."""
    return {
        "schema_id": "orch.phase3.wp_structure.v1",
        "run_id": run_id,
        "work_packages": [
            {
                "wp_id": "WP1",
                "title": "Management",
                "lead_partner": "P1",
                "contributing_partners": [],
                "objectives": ["Manage"],
                "tasks": [
                    {"task_id": "T1-01", "title": "Task 1", "responsible_partner": "P1", "contributing_partners": []},
                ],
                "deliverables": [
                    {"deliverable_id": "D1-01", "title": "Report", "type": "report", "due_month": 12, "responsible_partner": "P1"},
                ],
                "dependencies": [],
            },
            {
                "wp_id": "WP2",
                "title": "Research",
                "lead_partner": "P2",
                "contributing_partners": ["P1"],
                "objectives": ["Research"],
                "tasks": [
                    {"task_id": "T2-01", "title": "Task A", "responsible_partner": "P2", "contributing_partners": ["P1"]},
                    {"task_id": "T2-02", "title": "Task B", "responsible_partner": "P2", "contributing_partners": []},
                ],
                "deliverables": [
                    {"deliverable_id": "D2-01", "title": "Software", "type": "software", "due_month": 24, "responsible_partner": "P2"},
                ],
                "dependencies": [],
            },
            {
                "wp_id": "WP3",
                "title": "Demo",
                "lead_partner": "P1",
                "contributing_partners": ["P2"],
                "objectives": ["Demonstrate"],
                "tasks": [
                    {"task_id": "T3-01", "title": "Demo task", "responsible_partner": "P1", "contributing_partners": ["P2"]},
                ],
                "deliverables": [
                    {"deliverable_id": "D3-01", "title": "Demo report", "type": "report", "due_month": 36, "responsible_partner": "P1"},
                ],
                "dependencies": [],
            },
        ],
        "dependency_map": {
            "nodes": ["WP1", "WP2", "WP3", "T1-01", "T2-01", "T2-02", "T3-01"],
            "edges": edges if edges is not None else [],
        },
        "cycle_detected": False,
        "cycle_flags": [],
        "critical_path_nodes": ["WP2", "WP3"],
    }


def _minimal_seed(*, wp_bounds=None):
    """Build a minimal workpackage_seed.json dict."""
    default_bounds = [
        {"id": "WP1", "title": "Management", "lead": "P1", "participants": [], "start_month": 1, "end_month": 48, "person_months": 24},
        {"id": "WP2", "title": "Research", "lead": "P2", "participants": ["P1"], "start_month": 1, "end_month": 36, "person_months": 60},
        {"id": "WP3", "title": "Demo", "lead": "P1", "participants": ["P2"], "start_month": 12, "end_month": 42, "person_months": 30},
    ]
    return {"work_packages": wp_bounds if wp_bounds is not None else default_bounds}


def _minimal_call(*, duration_field="max_project_duration_months", duration_value=48):
    """Build a minimal selected_call.json dict."""
    return {
        "call_id": "TEST-CALL-01",
        "topic_code": "TEST-TOPIC-01",
        "instrument_type": "RIA",
        "work_programme_area": "test",
        duration_field: duration_value,
    }


def _write_fixtures(tmp_path, *, wp_structure=None, seed=None, call=None):
    """Write the three input fixtures to tmp_path in the canonical layout."""
    wp_dir = tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design"
    wp_dir.mkdir(parents=True, exist_ok=True)
    (wp_dir / "wp_structure.json").write_text(
        json.dumps(wp_structure or _minimal_wp_structure(), indent=2),
        encoding="utf-8",
    )

    seed_dir = tmp_path / "docs/tier3_project_instantiation/architecture_inputs"
    seed_dir.mkdir(parents=True, exist_ok=True)
    (seed_dir / "workpackage_seed.json").write_text(
        json.dumps(seed or _minimal_seed(), indent=2),
        encoding="utf-8",
    )

    call_dir = tmp_path / "docs/tier3_project_instantiation/call_binding"
    call_dir.mkdir(parents=True, exist_ok=True)
    (call_dir / "selected_call.json").write_text(
        json.dumps(call or _minimal_call(), indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHappyPath:
    """Test 1: correct strict/non-strict classification with mixed edges."""

    def test_mixed_edges_classified_correctly(self, tmp_path):
        edges = [
            # WP-level finish_to_start: WP2 ends M36, WP3 starts M12 → infeasible → non_strict
            {"from": "WP2", "to": "WP3", "edge_type": "finish_to_start"},
            # Task-level finish_to_start → strict
            {"from": "T2-02", "to": "T3-01", "edge_type": "finish_to_start"},
            # data_input → non_strict
            {"from": "T2-01", "to": "T3-01", "edge_type": "data_input"},
        ]
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(edges=edges),
        )

        result_path = normalize_dependencies("run-001", tmp_path)
        assert result_path.exists()

        data = json.loads(result_path.read_text())
        assert data["schema_id"] == SCHEMA_ID
        assert data["run_id"] == "run-001"
        assert data["project_duration_months"] == 48
        assert len(data["unresolved_constraints"]) == 0

        # 1 strict (task-level f2s), 2 non-strict (WP-level reclassified + data_input)
        assert len(data["strict_constraints"]) == 1
        assert data["strict_constraints"][0]["from"] == "T2-02"
        assert data["strict_constraints"][0]["action"] == "preserved"

        assert len(data["non_strict_constraints"]) == 2
        wp_reclassified = [c for c in data["non_strict_constraints"] if c["from"] == "WP2"]
        assert len(wp_reclassified) == 1
        assert wp_reclassified[0]["action"] == "reclassified"

        # normalization_log has all 3 entries
        assert len(data["normalization_log"]) == 3


class TestWPLevelInfeasible:
    """Test 2: WP-level finish_to_start with infeasible timing → non_strict."""

    def test_infeasible_wp_edge_reclassified(self, tmp_path):
        edges = [
            {"from": "WP2", "to": "WP3", "edge_type": "finish_to_start"},
        ]
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(edges=edges),
        )

        data = json.loads(
            normalize_dependencies("run-002", tmp_path).read_text()
        )
        assert len(data["strict_constraints"]) == 0
        assert len(data["non_strict_constraints"]) == 1
        assert data["non_strict_constraints"][0]["action"] == "reclassified"
        assert "infeasible" in data["non_strict_constraints"][0]["reason"]


class TestTaskLevelPreserved:
    """Test 3: task-level finish_to_start → preserved as strict."""

    def test_task_f2s_stays_strict(self, tmp_path):
        edges = [
            {"from": "T2-02", "to": "T3-01", "edge_type": "finish_to_start"},
        ]
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(edges=edges),
        )

        data = json.loads(
            normalize_dependencies("run-003", tmp_path).read_text()
        )
        assert len(data["strict_constraints"]) == 1
        assert data["strict_constraints"][0]["action"] == "preserved"
        assert len(data["non_strict_constraints"]) == 0


class TestDataInputAlwaysNonStrict:
    """Test 4: data_input edges → always non_strict regardless of node level."""

    def test_data_input_at_wp_level(self, tmp_path):
        edges = [
            {"from": "WP1", "to": "WP2", "edge_type": "data_input"},
        ]
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(edges=edges),
        )

        data = json.loads(
            normalize_dependencies("run-004", tmp_path).read_text()
        )
        assert len(data["strict_constraints"]) == 0
        assert len(data["non_strict_constraints"]) == 1
        assert data["non_strict_constraints"][0]["action"] == "preserved"

    def test_data_input_at_task_level(self, tmp_path):
        edges = [
            {"from": "T2-01", "to": "T3-01", "edge_type": "data_input"},
        ]
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(edges=edges),
        )

        data = json.loads(
            normalize_dependencies("run-004b", tmp_path).read_text()
        )
        assert len(data["strict_constraints"]) == 0
        assert len(data["non_strict_constraints"]) == 1


class TestMissingInputFiles:
    """Tests 5-7: missing input files → DependencyNormalizerError."""

    def test_missing_wp_structure(self, tmp_path):
        _write_fixtures(tmp_path)
        (tmp_path / WP_STRUCTURE_REL).unlink()

        with pytest.raises(DependencyNormalizerError, match="wp_structure.json not found"):
            normalize_dependencies("run-err1", tmp_path)

    def test_missing_workpackage_seed(self, tmp_path):
        _write_fixtures(tmp_path)
        (tmp_path / WP_SEED_REL).unlink()

        with pytest.raises(DependencyNormalizerError, match="workpackage_seed.json not found"):
            normalize_dependencies("run-err2", tmp_path)

    def test_missing_selected_call(self, tmp_path):
        _write_fixtures(tmp_path)
        (tmp_path / SELECTED_CALL_REL).unlink()

        with pytest.raises(DependencyNormalizerError, match="selected_call.json not found"):
            normalize_dependencies("run-err3", tmp_path)


class TestMalformedJSON:
    """Test 8: malformed JSON → DependencyNormalizerError."""

    def test_invalid_json(self, tmp_path):
        _write_fixtures(tmp_path)
        (tmp_path / WP_STRUCTURE_REL).write_text("{invalid json", encoding="utf-8")

        with pytest.raises(DependencyNormalizerError, match="not valid JSON"):
            normalize_dependencies("run-err4", tmp_path)


class TestEmptyEdges:
    """Test 9: empty dependency_map.edges → valid output with empty arrays."""

    def test_empty_edges_produces_valid_output(self, tmp_path):
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(edges=[]),
        )

        data = json.loads(
            normalize_dependencies("run-005", tmp_path).read_text()
        )
        assert data["schema_id"] == SCHEMA_ID
        assert data["strict_constraints"] == []
        assert data["non_strict_constraints"] == []
        assert data["normalization_log"] == []
        assert data["unresolved_constraints"] == []


class TestDurationFieldFallback:
    """Test 10: max_project_duration_months used when project_duration_months absent."""

    def test_fallback_to_max_project_duration_months(self, tmp_path):
        _write_fixtures(
            tmp_path,
            call=_minimal_call(
                duration_field="max_project_duration_months",
                duration_value=36,
            ),
        )

        data = json.loads(
            normalize_dependencies("run-006", tmp_path).read_text()
        )
        assert data["project_duration_months"] == 36

    def test_primary_field_used_when_present(self, tmp_path):
        call = {
            "call_id": "TEST",
            "topic_code": "TEST",
            "instrument_type": "RIA",
            "work_programme_area": "test",
            "project_duration_months": 24,
            "max_project_duration_months": 48,
        }
        _write_fixtures(tmp_path, call=call)

        data = json.loads(
            normalize_dependencies("run-006b", tmp_path).read_text()
        )
        assert data["project_duration_months"] == 24


class TestRunIdPropagation:
    """Test 11: run_id and source_wp_structure_run_id are propagated correctly."""

    def test_run_ids_propagated(self, tmp_path):
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(run_id="phase3-run-abc"),
        )

        data = json.loads(
            normalize_dependencies("phase4-run-xyz", tmp_path).read_text()
        )
        assert data["run_id"] == "phase4-run-xyz"
        assert data["source_wp_structure_run_id"] == "phase3-run-abc"


class TestIdempotency:
    """Test 12: same inputs → same output (modulo timestamp)."""

    def test_idempotent_modulo_timestamp(self, tmp_path):
        edges = [
            {"from": "WP2", "to": "WP3", "edge_type": "finish_to_start"},
            {"from": "T2-01", "to": "T3-01", "edge_type": "data_input"},
        ]
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(edges=edges),
        )

        data1 = json.loads(
            normalize_dependencies("run-idem", tmp_path).read_text()
        )
        data2 = json.loads(
            normalize_dependencies("run-idem", tmp_path).read_text()
        )

        # Remove timestamp for comparison
        data1.pop("normalization_timestamp")
        data2.pop("normalization_timestamp")
        assert data1 == data2


class TestFeasibleWPEdge:
    """Extra: WP-level finish_to_start that IS feasible stays strict."""

    def test_feasible_wp_edge_stays_strict(self, tmp_path):
        # WP1 ends M48, WP3 starts M12 → infeasible (48 > 12)
        # Use custom bounds: WP1 ends M10, WP3 starts M12 → feasible (10 <= 12)
        custom_seed = _minimal_seed(wp_bounds=[
            {"id": "WP1", "title": "Mgmt", "lead": "P1", "participants": [], "start_month": 1, "end_month": 10, "person_months": 10},
            {"id": "WP2", "title": "Research", "lead": "P2", "participants": [], "start_month": 1, "end_month": 36, "person_months": 60},
            {"id": "WP3", "title": "Demo", "lead": "P1", "participants": [], "start_month": 12, "end_month": 42, "person_months": 30},
        ])
        edges = [
            {"from": "WP1", "to": "WP3", "edge_type": "finish_to_start"},
        ]
        _write_fixtures(
            tmp_path,
            wp_structure=_minimal_wp_structure(edges=edges),
            seed=custom_seed,
        )

        data = json.loads(
            normalize_dependencies("run-feasible", tmp_path).read_text()
        )
        assert len(data["strict_constraints"]) == 1
        assert data["strict_constraints"][0]["action"] == "preserved"
        assert "feasible" in data["strict_constraints"][0]["reason"]
        assert len(data["non_strict_constraints"]) == 0
