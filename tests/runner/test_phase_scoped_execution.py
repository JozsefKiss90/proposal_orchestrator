"""
Tests for phase-scoped execution mode in the DAG scheduler.

Coverage:
  1. Successful execution of a single eligible phase
  2. Refusal/abort when requested phase prerequisites are unmet
  3. Downstream phases do not execute in a single-phase run
  4. Backward compatibility of full-DAG execution (no phase arg)
  5. ManifestGraph.nodes_for_phase() and phase_numbers()
  6. RunSummary phase_scope fields in to_dict() and write()
  7. CLI --phase argument parsing
  8. Stall detection is scoped to the requested phase
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runner.dag_scheduler import (
    DAGScheduler,
    DAGSchedulerError,
    ManifestGraph,
    RunAbortedError,
    RunSummary,
)
from runner.run_context import RunContext
from runner.runtime_models import AgentResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GATE_PASS = {"status": "pass"}
_GATE_FAIL = {"status": "fail"}
_RA_TARGET = "runner.dag_scheduler.run_agent"
_SUCCESS_AGENT = AgentResult(status="success", can_evaluate_exit_gate=True)


@pytest.fixture(autouse=True)
def _mock_run_agent():
    """Patch ``run_agent`` for all tests — these exercise scheduling, not agents."""
    with patch(_RA_TARGET, return_value=_SUCCESS_AGENT):
        yield


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _three_phase_manifest() -> dict:
    """Three sequential phases: phase 1 (n01), phase 2 (n02), phase 3 (n03)."""
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": "n01_call_analysis",
                "phase_number": 1,
                "phase_id": "phase_01",
                "agent": "call_analyst",
                "skills": [],
                "exit_gate": "phase_01_gate",
                "terminal": False,
            },
            {
                "node_id": "n02_concept_refinement",
                "phase_number": 2,
                "phase_id": "phase_02",
                "agent": "concept_refiner",
                "skills": [],
                "exit_gate": "phase_02_gate",
                "terminal": False,
            },
            {
                "node_id": "n03_wp_design",
                "phase_number": 3,
                "phase_id": "phase_03",
                "agent": "wp_designer",
                "skills": [],
                "exit_gate": "phase_03_gate",
                "terminal": True,
            },
        ],
        "edge_registry": [
            {
                "edge_id": "e01_to_02",
                "from_node": "n01_call_analysis",
                "to_node": "n02_concept_refinement",
                "gate_condition": "phase_01_gate",
            },
            {
                "edge_id": "e02_to_03",
                "from_node": "n02_concept_refinement",
                "to_node": "n03_wp_design",
                "gate_condition": "phase_02_gate",
            },
        ],
    }


def _multi_node_phase_manifest() -> dict:
    """Phase 8 with two sub-nodes (8a, 8b), preceded by phase 7 (n07)."""
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": "n07_budget_gate",
                "phase_number": 7,
                "phase_id": "phase_07",
                "agent": "budget_validator",
                "skills": [],
                "exit_gate": "gate_09_budget_consistency",
                "terminal": False,
            },
            {
                "node_id": "n08a_section_drafting",
                "phase_number": 8,
                "phase_id": "phase_08a",
                "agent": "section_drafter",
                "skills": [],
                "exit_gate": "gate_10_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08b_assembly",
                "phase_number": 8,
                "phase_id": "phase_08b",
                "agent": "assembler",
                "skills": [],
                "exit_gate": "gate_10b_assembly",
                "terminal": True,
            },
        ],
        "edge_registry": [
            {
                "edge_id": "e07_to_08a",
                "from_node": "n07_budget_gate",
                "to_node": "n08a_section_drafting",
                "gate_condition": "gate_09_budget_consistency",
            },
            {
                "edge_id": "e08a_to_08b",
                "from_node": "n08a_section_drafting",
                "to_node": "n08b_assembly",
                "gate_condition": "gate_10_completeness",
            },
        ],
    }


# ---------------------------------------------------------------------------
# ManifestGraph phase queries
# ---------------------------------------------------------------------------


class TestManifestGraphPhaseQueries:
    """Tests for nodes_for_phase() and phase_numbers()."""

    def test_nodes_for_phase_returns_correct_nodes(self):
        graph = ManifestGraph(
            _three_phase_manifest()["node_registry"],
            _three_phase_manifest()["edge_registry"],
        )
        assert graph.nodes_for_phase(1) == ["n01_call_analysis"]
        assert graph.nodes_for_phase(2) == ["n02_concept_refinement"]
        assert graph.nodes_for_phase(3) == ["n03_wp_design"]

    def test_nodes_for_phase_unknown_returns_empty(self):
        graph = ManifestGraph(
            _three_phase_manifest()["node_registry"],
            _three_phase_manifest()["edge_registry"],
        )
        assert graph.nodes_for_phase(99) == []

    def test_phase_numbers_returns_sorted(self):
        graph = ManifestGraph(
            _three_phase_manifest()["node_registry"],
            _three_phase_manifest()["edge_registry"],
        )
        assert graph.phase_numbers() == [1, 2, 3]

    def test_multi_node_phase(self):
        graph = ManifestGraph(
            _multi_node_phase_manifest()["node_registry"],
            _multi_node_phase_manifest()["edge_registry"],
        )
        assert graph.nodes_for_phase(8) == [
            "n08a_section_drafting",
            "n08b_assembly",
        ]

    def test_no_phase_number_fields_gives_empty(self):
        """Nodes without phase_number are not indexed."""
        data = {
            "node_registry": [
                {"node_id": "n01", "exit_gate": "g01", "terminal": True},
            ],
            "edge_registry": [],
        }
        graph = ManifestGraph(data["node_registry"], data["edge_registry"])
        assert graph.phase_numbers() == []
        assert graph.nodes_for_phase(1) == []


# ---------------------------------------------------------------------------
# Phase-scoped execution: successful single-phase run
# ---------------------------------------------------------------------------


class TestPhaseScopedExecution:
    """Phase-scoped dispatch with all prerequisites met."""

    def test_phase1_runs_only_phase1_node(self, tmp_path: Path):
        """Phase 1 has no prerequisites — it should dispatch and release."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-phase1")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=1,
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == ["n01_call_analysis"]
        assert summary.phase_scope == 1
        assert summary.phase_scope_nodes == ["n01_call_analysis"]
        # Phase 2 and 3 remain pending — but NOT stalled (out of scope).
        assert summary.node_states["n02_concept_refinement"] == "pending"
        assert summary.node_states["n03_wp_design"] == "pending"
        assert summary.stalled_nodes == []

    def test_phase2_runs_when_phase1_already_released(self, tmp_path: Path):
        """Phase 2 runs only if phase 1 was released in a prior run."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-phase2")
        # Simulate phase 1 already released from a prior run.
        ctx.set_node_state("n01_call_analysis", "released")
        ctx.save()

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=2,
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == ["n02_concept_refinement"]
        assert summary.phase_scope == 2

    def test_downstream_phase_not_dispatched(self, tmp_path: Path):
        """Even when phase 1 passes, phase 2 must NOT run in a phase=1 invocation."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-no-downstream")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=1,
            )
            summary = sched.run()

        # n02 must still be pending (not dispatched).
        assert "n02_concept_refinement" not in summary.dispatched_nodes
        assert summary.node_states["n02_concept_refinement"] == "pending"


# ---------------------------------------------------------------------------
# Phase-scoped execution: prerequisites unmet → abort
# ---------------------------------------------------------------------------


class TestPhaseScopedPrerequisitesUnmet:
    """Phase requested but upstream phases have not been run."""

    def test_phase2_aborts_when_phase1_not_released(self, tmp_path: Path):
        """Phase 2 nodes cannot run because phase 1 is still pending."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-unmet")

        sched = DAGScheduler(
            graph, ctx, tmp_path,
            manifest_path=manifest_path,
            phase=2,
        )

        with pytest.raises(RunAbortedError) as exc_info:
            sched.run()

        summary = exc_info.value.summary
        assert summary.overall_status == "aborted"
        assert summary.phase_scope == 2
        assert len(summary.stalled_nodes) == 1
        assert summary.stalled_nodes[0]["node_id"] == "n02_concept_refinement"

    def test_phase3_aborts_when_phase2_blocked(self, tmp_path: Path):
        """Phase 3 cannot run when phase 2 is blocked_at_exit."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-unmet-blocked")
        ctx.set_node_state("n01_call_analysis", "released")
        ctx.set_node_state("n02_concept_refinement", "blocked_at_exit")
        ctx.save()

        sched = DAGScheduler(
            graph, ctx, tmp_path,
            manifest_path=manifest_path,
            phase=3,
        )

        with pytest.raises(RunAbortedError) as exc_info:
            sched.run()

        summary = exc_info.value.summary
        assert summary.overall_status == "aborted"
        stalled_ids = [s["node_id"] for s in summary.stalled_nodes]
        assert "n03_wp_design" in stalled_ids

    def test_unknown_phase_raises_error(self, tmp_path: Path):
        """Requesting a phase that has no nodes raises DAGSchedulerError."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-unknown")

        sched = DAGScheduler(
            graph, ctx, tmp_path,
            manifest_path=manifest_path,
            phase=99,
        )

        with pytest.raises(DAGSchedulerError, match="No nodes found for phase 99"):
            sched.run()


# ---------------------------------------------------------------------------
# Multi-node phase: partial completion
# ---------------------------------------------------------------------------


class TestMultiNodePhase:
    """Phase with multiple nodes (e.g. phase 8 substeps)."""

    def test_multi_node_phase_all_pass(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _multi_node_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-multi-pass")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=8,
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert set(summary.dispatched_nodes) == {
            "n08a_section_drafting",
            "n08b_assembly",
        }

    def test_multi_node_phase_partial_pass(self, tmp_path: Path):
        """First substep passes, second fails at exit gate → partial_pass."""
        manifest_path = _write_manifest(tmp_path, _multi_node_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-multi-partial")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        call_count = [0]

        def _gate_side_effect(*args, **kwargs):
            call_count[0] += 1
            # First two calls are for n08a (exit gate passes).
            # Third call is n08b exit gate → fail.
            if call_count[0] <= 1:
                return _GATE_PASS
            return _GATE_FAIL

        with patch("runner.dag_scheduler.evaluate_gate", side_effect=_gate_side_effect):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=8,
            )
            summary = sched.run()

        assert summary.overall_status == "partial_pass"
        assert summary.node_states["n08a_section_drafting"] == "released"
        assert summary.node_states["n08b_assembly"] == "blocked_at_exit"


# ---------------------------------------------------------------------------
# Backward compatibility: full-DAG execution without --phase
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Full DAG execution still works when no phase is specified."""

    def test_full_dag_runs_all_phases(self, tmp_path: Path):
        """Without phase arg, all nodes are dispatched in dependency order."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-full")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                # No phase argument.
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert len(summary.dispatched_nodes) == 3
        assert summary.phase_scope is None
        assert summary.phase_scope_nodes == []

    def test_full_dag_stall_detects_all_nodes(self, tmp_path: Path):
        """Full DAG: stall detection covers all pending nodes."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-full-stall")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_FAIL):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
            )
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        assert summary.overall_status == "aborted"
        stalled_ids = [s["node_id"] for s in summary.stalled_nodes]
        # n02 and n03 should be stalled (n01 blocked, n02/n03 pending).
        assert "n02_concept_refinement" in stalled_ids
        assert "n03_wp_design" in stalled_ids


# ---------------------------------------------------------------------------
# RunSummary phase fields
# ---------------------------------------------------------------------------


class TestRunSummaryPhaseFields:
    """RunSummary serialisation includes phase scope information."""

    def test_to_dict_includes_phase_scope(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-summary")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=1,
            )
            summary = sched.run()

        d = summary.to_dict()
        assert d["phase_scope"] == 1
        assert d["phase_scope_nodes"] == ["n01_call_analysis"]

    def test_write_includes_phase_scope(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-write")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=1,
            )
            summary = sched.run()

        json_path = ctx.run_dir / "run_summary.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["phase_scope"] == 1
        assert data["phase_scope_nodes"] == ["n01_call_analysis"]

    def test_full_dag_summary_has_null_phase_scope(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-null-phase")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
            )
            summary = sched.run()

        d = summary.to_dict()
        assert d["phase_scope"] is None
        assert d["phase_scope_nodes"] == []


# ---------------------------------------------------------------------------
# CLI --phase argument parsing
# ---------------------------------------------------------------------------


class TestCLIPhaseArgument:
    """Tests for the _parse_phase helper."""

    def test_parse_integer(self):
        from runner.__main__ import _parse_phase

        assert _parse_phase("1") == 1
        assert _parse_phase("8") == 8

    def test_parse_phase_prefix(self):
        from runner.__main__ import _parse_phase

        assert _parse_phase("phase1") == 1
        assert _parse_phase("phase_01") == 1
        assert _parse_phase("phase-3") == 3

    def test_parse_full_phase_id(self):
        from runner.__main__ import _parse_phase

        assert _parse_phase("phase_01_call_analysis") == 1

    def test_parse_invalid_raises(self):
        from runner.__main__ import _parse_phase

        with pytest.raises(Exception):
            _parse_phase("foobar")
