"""
Unit tests for Step 8 — Cycle predicate (runner/predicates/cycle_predicates.py).

All tests use synthetic temporary files; no live repository artifacts are
read.  Tests are grouped by pass / fail case as specified in the task brief.

Dependency-map structure assumed by these tests
-----------------------------------------------
The predicate reads ``dependency_map`` from ``wp_structure.json``:

    {
        "dependency_map": {
            "nodes": ["WP1", "WP2", ...],
            "edges": [
                {"from": "WP1", "to": "WP2", "edge_type": "finish_to_start"},
                ...
            ]
        }
    }

This contract is defined in artifact_schema_specification.yaml §1.3.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from runner.predicates.cycle_predicates import no_dependency_cycles
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_wp(tmp_dir: str, content: Any) -> str:
    """Write *content* as JSON to a wp_structure.json in *tmp_dir*."""
    path = os.path.join(tmp_dir, "wp_structure.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(content, fh)
    return path


def _make_dep_map(nodes: list[str], edges: list[dict]) -> dict:
    """Return a minimal valid wp_structure dict with the given dependency_map."""
    return {
        "schema_id": "orch.phase3.wp_structure.v1",
        "run_id": "test-run-001",
        "dependency_map": {
            "nodes": nodes,
            "edges": edges,
        },
    }


def _edge(from_id: str, to_id: str, edge_type: str = "finish_to_start") -> dict:
    return {"from": from_id, "to": to_id, "edge_type": edge_type}


# ---------------------------------------------------------------------------
# PASS cases
# ---------------------------------------------------------------------------


class TestPassCases:
    """Cases where no_dependency_cycles should return passed=True."""

    def test_empty_dependency_map(self, tmp_path):
        """Valid artifact with empty nodes and edges should pass (vacuous)."""
        path = _write_wp(str(tmp_path), _make_dep_map([], []))
        result = no_dependency_cycles(path)
        assert result.passed is True

    def test_single_node_no_dependencies(self, tmp_path):
        """Single node with no edges cannot form a cycle."""
        path = _write_wp(str(tmp_path), _make_dep_map(["WP1"], []))
        result = no_dependency_cycles(path)
        assert result.passed is True

    def test_simple_dag_linear(self, tmp_path):
        """A → B → C with no back-edge should pass."""
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(
                ["A", "B", "C"],
                [_edge("A", "B"), _edge("B", "C")],
            ),
        )
        result = no_dependency_cycles(path)
        assert result.passed is True

    def test_branching_dag(self, tmp_path):
        """A → B, A → C, B → D, C → D — diamond DAG, no cycle."""
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(
                ["A", "B", "C", "D"],
                [
                    _edge("A", "B"),
                    _edge("A", "C"),
                    _edge("B", "D"),
                    _edge("C", "D"),
                ],
            ),
        )
        result = no_dependency_cycles(path)
        assert result.passed is True

    def test_empty_nodes_only(self, tmp_path):
        """Nodes declared but no edges — no cycle possible."""
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(["WP1", "WP2", "WP3"], []),
        )
        result = no_dependency_cycles(path)
        assert result.passed is True

    def test_details_on_pass_include_counts(self, tmp_path):
        """Passing result should carry node_count and edge_count in details."""
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(["WP1", "WP2"], [_edge("WP1", "WP2")]),
        )
        result = no_dependency_cycles(path)
        assert result.passed is True
        assert "node_count" in result.details
        assert "edge_count" in result.details


# ---------------------------------------------------------------------------
# FAIL cases
# ---------------------------------------------------------------------------


class TestFailCases:
    """Cases where no_dependency_cycles should return passed=False."""

    # ---- MISSING_MANDATORY_INPUT ----

    def test_missing_file(self, tmp_path):
        """Non-existent path → MISSING_MANDATORY_INPUT."""
        path = str(tmp_path / "nonexistent.json")
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT
        assert result.reason is not None

    # ---- MALFORMED_ARTIFACT ----

    def test_invalid_json(self, tmp_path):
        """File present but not valid JSON → MALFORMED_ARTIFACT."""
        path = str(tmp_path / "wp_structure.json")
        Path(path).write_text("{ this is not : json }", encoding="utf-8")
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_json_array_not_object(self, tmp_path):
        """Top-level JSON array (not object) → MALFORMED_ARTIFACT."""
        path = _write_wp(str(tmp_path), [{"nodes": [], "edges": []}])
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_missing_dependency_map_field(self, tmp_path):
        """Object present but no 'dependency_map' field → MALFORMED_ARTIFACT."""
        path = _write_wp(
            str(tmp_path),
            {"schema_id": "orch.phase3.wp_structure.v1", "run_id": "x"},
        )
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "dependency_map" in result.reason

    def test_dependency_map_null(self, tmp_path):
        """dependency_map: null → MALFORMED_ARTIFACT."""
        data = _make_dep_map([], [])
        data["dependency_map"] = None
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_dependency_map_scalar(self, tmp_path):
        """dependency_map: 42 (scalar) → MALFORMED_ARTIFACT."""
        data = _make_dep_map([], [])
        data["dependency_map"] = 42
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_dependency_map_is_array(self, tmp_path):
        """dependency_map: [] (wrong container type) → MALFORMED_ARTIFACT."""
        data = _make_dep_map([], [])
        data["dependency_map"] = []
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_nodes_is_not_array(self, tmp_path):
        """dependency_map.nodes is a string → MALFORMED_ARTIFACT."""
        data = _make_dep_map([], [])
        data["dependency_map"]["nodes"] = "WP1"
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_nodes_contains_non_string(self, tmp_path):
        """dependency_map.nodes contains integer → MALFORMED_ARTIFACT."""
        data = _make_dep_map([], [])
        data["dependency_map"]["nodes"] = ["WP1", 99]
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_edges_is_not_array(self, tmp_path):
        """dependency_map.edges is a dict → MALFORMED_ARTIFACT."""
        data = _make_dep_map([], [])
        data["dependency_map"]["edges"] = {"from": "WP1", "to": "WP2"}
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_edge_is_not_dict(self, tmp_path):
        """An edge entry that is a string → MALFORMED_ARTIFACT."""
        data = _make_dep_map(["WP1", "WP2"], ["WP1→WP2"])
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_edge_missing_from_field(self, tmp_path):
        """Edge dict missing 'from' field → MALFORMED_ARTIFACT."""
        data = _make_dep_map(["WP1", "WP2"], [{"to": "WP2", "edge_type": "finish_to_start"}])
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_edge_missing_to_field(self, tmp_path):
        """Edge dict missing 'to' field → MALFORMED_ARTIFACT."""
        data = _make_dep_map(
            ["WP1", "WP2"], [{"from": "WP1", "edge_type": "finish_to_start"}]
        )
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_edge_from_is_null(self, tmp_path):
        """Edge dict with null 'from' value → MALFORMED_ARTIFACT."""
        data = _make_dep_map(
            ["WP1", "WP2"],
            [{"from": None, "to": "WP2", "edge_type": "finish_to_start"}],
        )
        path = _write_wp(str(tmp_path), data)
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT

    # ---- CROSS_ARTIFACT_INCONSISTENCY (cycles) ----

    def test_simple_cycle_two_nodes(self, tmp_path):
        """A → B → A (two-node cycle) → CROSS_ARTIFACT_INCONSISTENCY."""
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(
                ["A", "B"],
                [_edge("A", "B"), _edge("B", "A")],
            ),
        )
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_longer_cycle_three_nodes(self, tmp_path):
        """A → B → C → A (three-node cycle) → CROSS_ARTIFACT_INCONSISTENCY."""
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(
                ["A", "B", "C"],
                [_edge("A", "B"), _edge("B", "C"), _edge("C", "A")],
            ),
        )
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_self_loop(self, tmp_path):
        """A → A (self-loop) → CROSS_ARTIFACT_INCONSISTENCY."""
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(["A"], [_edge("A", "A")]),
        )
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_disconnected_graph_one_cyclic_component(self, tmp_path):
        """
        Graph with a DAG component (X → Y) and a cyclic component (A → B → A).
        Mixed graph must still fail because one component is cyclic.
        """
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(
                ["X", "Y", "A", "B"],
                [
                    _edge("X", "Y"),   # DAG component
                    _edge("A", "B"),   # cyclic component start
                    _edge("B", "A"),   # back-edge forming cycle
                ],
            ),
        )
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    # ---- Detail diagnostics for cyclic failures ----

    def test_cycle_details_contain_cycle_nodes(self, tmp_path):
        """
        For a two-node cycle A → B → A, the returned details should include
        'cycle_nodes' containing both A and B.
        """
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(
                ["A", "B"],
                [_edge("A", "B"), _edge("B", "A")],
            ),
        )
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "cycle_nodes" in result.details
        cycle_nodes = result.details["cycle_nodes"]
        assert isinstance(cycle_nodes, list)
        assert "A" in cycle_nodes
        assert "B" in cycle_nodes

    def test_cycle_details_contain_remaining_count(self, tmp_path):
        """
        For a three-node cycle, remaining_count should equal the number of
        cyclic nodes and processed_count should reflect the acyclic prefix.
        """
        # D is a pure source with no back-edge; A → B → C → A is the cycle
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(
                ["A", "B", "C", "D"],
                [
                    _edge("D", "A"),   # D is a source; not cyclic
                    _edge("A", "B"),
                    _edge("B", "C"),
                    _edge("C", "A"),   # back-edge
                ],
            ),
        )
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "remaining_count" in result.details
        assert "processed_count" in result.details
        # D and A (reached via D before the cycle is detected) — D processed,
        # A/B/C remain because of the cycle
        assert result.details["remaining_count"] == 3
        assert result.details["processed_count"] == 1
        assert "cycle_nodes" in result.details
        cycle_nodes = set(result.details["cycle_nodes"])
        assert cycle_nodes == {"A", "B", "C"}

    def test_cycle_failure_reason_is_informative(self, tmp_path):
        """reason string should name the cyclic nodes for operator inspection."""
        path = _write_wp(
            str(tmp_path),
            _make_dep_map(["WP1", "WP2"], [_edge("WP1", "WP2"), _edge("WP2", "WP1")]),
        )
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert result.reason is not None
        assert "WP1" in result.reason or "WP2" in result.reason

    # ---- Path included in all results ----

    def test_details_path_present_on_pass(self, tmp_path):
        path = _write_wp(str(tmp_path), _make_dep_map([], []))
        result = no_dependency_cycles(path)
        assert "path" in result.details

    def test_details_path_present_on_missing(self, tmp_path):
        path = str(tmp_path / "absent.json")
        result = no_dependency_cycles(path)
        assert "path" in result.details

    def test_details_path_present_on_malformed(self, tmp_path):
        path = _write_wp(str(tmp_path), {"schema_id": "x"})
        result = no_dependency_cycles(path)
        assert result.passed is False
        assert "path" in result.details
