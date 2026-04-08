"""
Tests for runner.dag_scheduler (DAG scheduler Steps 1–4).

Step 2 coverage:
  1.  single-node: entry gate passes, exit gate passes → released
  2.  single-node: entry gate fails → blocked_at_entry, never reaches exit
  3.  two-node linear: first released → second dispatched and released
  4.  two-node linear: first exit gate fails → second stays pending → RunAbortedError
  5.  dispatch order follows manifest registry order
  6.  run() stops when no nodes are ready
  7.  gate_09_budget_consistency failure triggers mark_hard_block_downstream()
  8.  after gate_09 failure, all canonical Phase 8 node IDs are hard_block_upstream
  9.  _dispatch_node() forwards library_path and manifest_path to evaluate_gate()
  10. run() result dict reports correct released / blocked / pending / hard_blocked

Step 2 additional invariant tests:
  - node with no exit gate raises DAGSchedulerError
  - run() with no nodes in graph produces empty result
  - single-node with no entry gate skips straight to exit gate evaluation
  - ctx.mark_hard_block_downstream() called even when evaluate_gate is mocked

Step 3 coverage:
  - _settle_stalled_nodes() returns empty list when all nodes are settled
  - _settle_stalled_nodes() returns one entry per stalled pending node
  - stall report includes gate_id and source_node_state for each unsatisfied condition
  - pending node with multiple unsatisfied incoming conditions reports all of them
  - run() raises RunAbortedError when pending nodes remain
  - RunAbortedError.result carries the full lightweight result dict
  - aborted result dict includes pending_nodes, stall_report, hard_blocked_nodes
  - gate_09 failure → hard_block_upstream nodes (not stalled pending)
  - both hard-blocked and independently stalled nodes are distinguished in abort result
  - hard-blocked nodes are not touched by _settle_stalled_nodes()
  - run() does not raise when all nodes are settled, even if some are blocked
  - abort is driven by pending nodes, not by released/blocked nodes

All tests use patched evaluate_gate and synthetic manifests / RunContext
instances backed by tmp_path.  No live repository artifacts are read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
import yaml

from runner.dag_scheduler import (
    DAGScheduler,
    DAGSchedulerError,
    ManifestGraph,
    RunAbortedError,
)
from runner.run_context import PHASE_8_NODE_IDS, RunContext


# ---------------------------------------------------------------------------
# Helpers — synthetic manifest and context builders
# ---------------------------------------------------------------------------

_GATE_PASS = {"status": "pass"}
_GATE_FAIL = {"status": "fail"}


def _write_manifest(tmp_path: Path, data: dict, name: str = "manifest.yaml") -> Path:
    path = tmp_path / name
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _single_node_manifest(
    node_id: str = "n01_call_analysis",
    exit_gate: str = "phase_01_gate",
    entry_gate: str | None = None,
    terminal: bool = False,
) -> dict:
    node: dict = {
        "node_id": node_id,
        "exit_gate": exit_gate,
        "terminal": terminal,
    }
    if entry_gate:
        node["entry_gate"] = entry_gate
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [node],
        "edge_registry": [],
    }


def _two_node_linear_manifest(
    n1: str = "n01_call_analysis",
    n1_exit: str = "phase_01_gate",
    n2: str = "n02_concept_refinement",
    n2_exit: str = "phase_02_gate",
) -> dict:
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {"node_id": n1, "exit_gate": n1_exit, "terminal": False},
            {"node_id": n2, "exit_gate": n2_exit, "terminal": True},
        ],
        "edge_registry": [
            {
                "edge_id": "e01",
                "from_node": n1,
                "to_node": n2,
                "gate_condition": n1_exit,
            }
        ],
    }


def _gate09_node_manifest() -> dict:
    """
    Minimal two-node manifest where n07 holds gate_09_budget_consistency and
    Phase 8 nodes are n08a_section_drafting / n08b_assembly.
    Used to test HARD_BLOCK propagation.
    """
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": "n07_budget_gate",
                "exit_gate": "gate_09_budget_consistency",
                "terminal": False,
            },
            {
                "node_id": "n08a_section_drafting",
                "exit_gate": "gate_10_part_b_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08b_assembly",
                "exit_gate": "gate_10_part_b_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08c_evaluator_review",
                "exit_gate": "gate_11_review_closure",
                "terminal": False,
            },
            {
                "node_id": "n08d_revision",
                "exit_gate": "gate_12_constitutional_compliance",
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
        ],
    }


def _make_scheduler(
    tmp_path: Path,
    manifest_data: dict,
    run_id: str = "test-run",
    library_path: Path | None = None,
    manifest_path: Path | None = None,
) -> DAGScheduler:
    """Build a DAGScheduler from a synthetic manifest and a fresh RunContext."""
    mp = _write_manifest(tmp_path, manifest_data)
    graph = ManifestGraph.load(mp)
    ctx = RunContext.initialize(tmp_path, run_id)
    return DAGScheduler(
        graph,
        ctx,
        tmp_path,
        library_path=library_path,
        manifest_path=manifest_path,
    )


# ---------------------------------------------------------------------------
# Fixture: shared patch target
# ---------------------------------------------------------------------------

_EG_TARGET = "runner.dag_scheduler.evaluate_gate"


# ---------------------------------------------------------------------------
# 1. Single-node: entry gate passes, exit gate passes → released
# ---------------------------------------------------------------------------


class TestSingleNodeFullPass:
    def test_node_released_after_both_gates_pass(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg:
            result = sched.run()

        assert "n01_call_analysis" in result["released_nodes"]
        assert result["blocked_nodes"] == []
        assert result["pending_nodes"] == []

    def test_evaluate_gate_called_for_entry_and_exit(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg:
            sched.run()

        gate_ids_called = [c.args[0] for c in mock_eg.call_args_list]
        assert "gate_01_source_integrity" in gate_ids_called
        assert "phase_01_gate" in gate_ids_called
        assert gate_ids_called.index("gate_01_source_integrity") < gate_ids_called.index(
            "phase_01_gate"
        ), "entry gate must be evaluated before exit gate"

    def test_node_in_dispatched_list(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()
        assert result["dispatched_nodes"] == ["n01_call_analysis"]

    def test_stalled_false_when_all_complete(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()
        assert result["stalled"] is False


# ---------------------------------------------------------------------------
# 2. Single-node: entry gate fails → blocked_at_entry
# ---------------------------------------------------------------------------


class TestSingleNodeEntryFail:
    def test_node_blocked_at_entry(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert "n01_call_analysis" in result["blocked_nodes"]
        assert result["released_nodes"] == []

    def test_exit_gate_never_called_after_entry_fail(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL) as mock_eg:
            sched.run()

        gate_ids_called = [c.args[0] for c in mock_eg.call_args_list]
        assert "gate_01_source_integrity" in gate_ids_called
        assert "phase_01_gate" not in gate_ids_called, (
            "exit gate must not be evaluated after entry gate failure"
        )

    def test_node_state_is_blocked_at_entry(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.run()

        ctx = RunContext.load(tmp_path, "test-run")
        assert ctx.get_node_state("n01_call_analysis") == "blocked_at_entry"

    def test_stalled_false_when_only_node_is_blocked(self, tmp_path: Path) -> None:
        """
        The single node is blocked_at_entry (settled), not pending.
        No unsettled-pending nodes remain → stalled=False.
        """
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()
        assert result["stalled"] is False


# ---------------------------------------------------------------------------
# 3. Two-node linear: first released → second dispatched and released
# ---------------------------------------------------------------------------


class TestTwoNodeLinearBothPass:
    def test_both_nodes_released(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert set(result["released_nodes"]) == {"n01_call_analysis", "n02_concept_refinement"}
        assert result["blocked_nodes"] == []
        assert result["pending_nodes"] == []

    def test_dispatched_order_is_n1_then_n2(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        dispatched = result["dispatched_nodes"]
        assert dispatched.index("n01_call_analysis") < dispatched.index(
            "n02_concept_refinement"
        )

    def test_exit_gates_called_in_order(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg:
            sched.run()

        gate_ids = [c.args[0] for c in mock_eg.call_args_list]
        assert gate_ids.index("phase_01_gate") < gate_ids.index("phase_02_gate")


# ---------------------------------------------------------------------------
# 4. Two-node linear: first exit gate fails → second stays pending → abort
#
# Step 3 contract: run() raises RunAbortedError instead of returning when
# pending nodes remain.  These tests were updated from the Step 2 versions
# (which checked result["stalled"]) to use pytest.raises and inspect
# exc.result instead.
# ---------------------------------------------------------------------------


class TestTwoNodeLinearFirstFails:
    def test_n2_remains_pending(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert "n02_concept_refinement" in exc_info.value.result["pending_nodes"]

    def test_n1_is_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert "n01_call_analysis" in exc_info.value.result["blocked_nodes"]

    def test_n2_never_dispatched(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert "n02_concept_refinement" not in exc_info.value.result["dispatched_nodes"]

    def test_stalled_true(self, tmp_path: Path) -> None:
        """stalled=True is preserved in exc.result for backward compatibility."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert exc_info.value.result["stalled"] is True


# ---------------------------------------------------------------------------
# 5. Dispatch order follows manifest registry order
# ---------------------------------------------------------------------------


class TestDispatchOrder:
    def test_parallel_nodes_dispatched_in_registry_order(
        self, tmp_path: Path
    ) -> None:
        """
        Fork: n01 → n02 and n01 → n03 (parallel).
        Both n02 and n03 become ready when n01 is released.
        They must be dispatched in registry order (n02 before n03).
        """
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {"node_id": "n01", "exit_gate": "g01", "terminal": False},
                {"node_id": "n02", "exit_gate": "g02", "terminal": False},
                {"node_id": "n03", "exit_gate": "g03", "terminal": True},
            ],
            "edge_registry": [
                {"edge_id": "e1", "from_node": "n01", "to_node": "n02", "gate_condition": "g01"},
                {"edge_id": "e2", "from_node": "n01", "to_node": "n03", "gate_condition": "g01"},
            ],
        }
        sched = _make_scheduler(tmp_path, data)
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        dispatched = result["dispatched_nodes"]
        assert dispatched[0] == "n01", f"expected n01 first, got {dispatched}"
        n02_idx = dispatched.index("n02")
        n03_idx = dispatched.index("n03")
        assert n02_idx < n03_idx, (
            f"n02 (registry position 1) must be dispatched before n03 "
            f"(registry position 2); got order {dispatched!r}"
        )


# ---------------------------------------------------------------------------
# 6. run() stops when no nodes are ready
# ---------------------------------------------------------------------------


class TestRunStopsWhenNoReady:
    def test_run_exits_immediately_on_empty_graph(self, tmp_path: Path) -> None:
        """An empty graph has no nodes → loop exits immediately."""
        data = {"name": "test", "version": "1.1", "node_registry": [], "edge_registry": []}
        mp = _write_manifest(tmp_path, data)
        graph = ManifestGraph.load(mp)
        ctx = RunContext.initialize(tmp_path, "run-empty")
        sched = DAGScheduler(graph, ctx, tmp_path)
        with patch(_EG_TARGET) as mock_eg:
            result = sched.run()
        mock_eg.assert_not_called()
        assert result["dispatched_nodes"] == []
        assert result["stalled"] is False

    def test_run_stops_after_upstream_blocks(self, tmp_path: Path) -> None:
        """Once upstream fails, no downstream node becomes ready; loop stops.

        Step 3: run() raises RunAbortedError; the call count and pending list
        are inspected via exc.result.
        """
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL) as mock_eg:
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        # evaluate_gate called exactly once (for n01's exit gate only)
        assert mock_eg.call_count == 1
        assert exc_info.value.result["pending_nodes"] == ["n02_concept_refinement"]


# ---------------------------------------------------------------------------
# 7. gate_09 failure triggers mark_hard_block_downstream()
# ---------------------------------------------------------------------------


class TestGate09HardBlock:
    def test_mark_hard_block_downstream_called_on_gate09_failure(
        self, tmp_path: Path
    ) -> None:
        sched = _make_scheduler(tmp_path, _gate09_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with patch.object(sched.ctx.__class__, "mark_hard_block_downstream") as mock_hb:
                # Use a side_effect to track calls across reload cycles
                # Instead, spy via the RunContext class method
                pass

        # Simpler: verify via state outcome after run
        sched2 = _make_scheduler(tmp_path, _gate09_node_manifest(), run_id="run-hb")
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched2.run()

        ctx = RunContext.load(tmp_path, "run-hb")
        assert ctx.get_node_state("n07_budget_gate") == "blocked_at_exit"
        # mark_hard_block_downstream sets hard_block_gate in manifest
        manifest_data = ctx.to_dict()
        assert manifest_data.get("hard_block_gate") == "gate_09_budget_consistency"

    def test_hard_block_reason_set_in_manifest(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _gate09_node_manifest(), run_id="run-hb2")
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.run()

        ctx = RunContext.load(tmp_path, "run-hb2")
        manifest_data = ctx.to_dict()
        assert "hard_block_reason" in manifest_data


# ---------------------------------------------------------------------------
# 8. After gate_09 failure, all canonical Phase 8 node IDs are hard_block_upstream
# ---------------------------------------------------------------------------


class TestGate09HardBlockPhase8Nodes:
    def test_all_phase8_node_ids_frozen(self, tmp_path: Path) -> None:
        """
        Build a manifest containing all four canonical Phase 8 nodes.
        When gate_09 fails, all of them must transition to hard_block_upstream.
        """
        # Full Phase 8 subgraph manifest (no edges from n07 to n08a yet
        # since we only need the HARD_BLOCK to apply to those nodes directly
        # via mark_hard_block_downstream)
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {
                    "node_id": "n07_budget_gate",
                    "exit_gate": "gate_09_budget_consistency",
                    "terminal": False,
                },
                {
                    "node_id": "n08a_section_drafting",
                    "exit_gate": "gate_10_part_b_completeness",
                    "terminal": False,
                },
                {
                    "node_id": "n08b_assembly",
                    "exit_gate": "gate_10_part_b_completeness",
                    "terminal": False,
                },
                {
                    "node_id": "n08c_evaluator_review",
                    "exit_gate": "gate_11_review_closure",
                    "terminal": False,
                },
                {
                    "node_id": "n08d_revision",
                    "exit_gate": "gate_12_constitutional_compliance",
                    "terminal": True,
                },
            ],
            "edge_registry": [],
        }
        sched = _make_scheduler(tmp_path, data, run_id="run-p8")
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.run()

        ctx = RunContext.load(tmp_path, "run-p8")
        for phase8_id in PHASE_8_NODE_IDS:
            assert ctx.get_node_state(phase8_id) == "hard_block_upstream", (
                f"Expected hard_block_upstream for {phase8_id!r}, "
                f"got {ctx.get_node_state(phase8_id)!r}"
            )

    def test_phase8_nodes_not_in_dispatched_after_hard_block(
        self, tmp_path: Path
    ) -> None:
        """Phase 8 nodes must not be dispatched after HARD_BLOCK."""
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {
                    "node_id": "n07_budget_gate",
                    "exit_gate": "gate_09_budget_consistency",
                    "terminal": False,
                },
                {
                    "node_id": "n08a_section_drafting",
                    "exit_gate": "gate_10_part_b_completeness",
                    "terminal": False,
                },
            ],
            "edge_registry": [
                {
                    "edge_id": "e07_to_08a",
                    "from_node": "n07_budget_gate",
                    "to_node": "n08a_section_drafting",
                    "gate_condition": "gate_09_budget_consistency",
                }
            ],
        }
        sched = _make_scheduler(tmp_path, data, run_id="run-p8b")
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert "n08a_section_drafting" not in result["dispatched_nodes"]


# ---------------------------------------------------------------------------
# 9. _dispatch_node() forwards library_path and manifest_path to evaluate_gate()
# ---------------------------------------------------------------------------


class TestKwargsPassthrough:
    def test_library_path_forwarded(self, tmp_path: Path) -> None:
        lib_path = tmp_path / "my_library.yaml"
        sched = _make_scheduler(
            tmp_path, _single_node_manifest(), library_path=lib_path
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg:
            sched.run()

        for c in mock_eg.call_args_list:
            assert c.kwargs.get("library_path") == lib_path, (
                f"library_path not forwarded: {c.kwargs!r}"
            )

    def test_manifest_path_forwarded(self, tmp_path: Path) -> None:
        man_path = tmp_path / "my_manifest.yaml"
        sched = _make_scheduler(
            tmp_path, _single_node_manifest(), manifest_path=man_path
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg:
            sched.run()

        for c in mock_eg.call_args_list:
            assert c.kwargs.get("manifest_path") == man_path, (
                f"manifest_path not forwarded: {c.kwargs!r}"
            )

    def test_run_id_forwarded(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="my-run-id")
        with patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg:
            sched.run()

        for c in mock_eg.call_args_list:
            assert c.args[1] == "my-run-id", f"run_id not forwarded: {c.args!r}"

    def test_repo_root_forwarded(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg:
            sched.run()

        for c in mock_eg.call_args_list:
            assert Path(c.args[2]) == tmp_path, f"repo_root not forwarded: {c.args!r}"


# ---------------------------------------------------------------------------
# 10. run() result dict correctness
# ---------------------------------------------------------------------------


class TestRunResultDict:
    def test_result_contains_all_required_keys(self, tmp_path: Path) -> None:
        """
        run() now returns a RunSummary.  Verify required keys are present
        in to_dict() (which backs __getitem__ / __contains__).
        """
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        required_keys = {
            "run_id",
            "dispatched_nodes",
            "released_nodes",
            "blocked_nodes",
            "hard_blocked_nodes",
            "pending_nodes",
            "stalled",
        }
        result_dict = result.to_dict()
        assert required_keys.issubset(result_dict.keys()), (
            f"Missing keys: {required_keys - result_dict.keys()!r}"
        )

    def test_run_id_matches_context(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="check-id")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()
        assert result["run_id"] == "check-id"

    def test_released_nodes_correct_after_full_pass(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert sorted(result["released_nodes"]) == sorted(
            ["n01_call_analysis", "n02_concept_refinement"]
        )
        assert result["blocked_nodes"] == []
        assert result["hard_blocked_nodes"] == []
        assert result["pending_nodes"] == []

    def test_blocked_nodes_correct_after_exit_fail(self, tmp_path: Path) -> None:
        """
        Two-node linear fail: n01 blocked, n02 pending → RunAbortedError.
        Step 3: inspect exc.result for the node state breakdown.
        """
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        result = exc_info.value.result
        assert result["blocked_nodes"] == ["n01_call_analysis"]
        assert result["released_nodes"] == []
        assert result["pending_nodes"] == ["n02_concept_refinement"]

    def test_hard_blocked_nodes_in_result(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _gate09_node_manifest(), run_id="run-res")
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert "n08a_section_drafting" in result["hard_blocked_nodes"]
        assert "n08b_assembly" in result["hard_blocked_nodes"]
        assert "n08c_evaluator_review" in result["hard_blocked_nodes"]
        assert "n08d_revision" in result["hard_blocked_nodes"]


# ---------------------------------------------------------------------------
# Additional edge-case / invariant tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_node_with_no_exit_gate_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [{"node_id": "n01_call_analysis", "terminal": False}],
            "edge_registry": [],
        }
        sched = _make_scheduler(tmp_path, data)
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            with pytest.raises(DAGSchedulerError, match="no exit_gate"):
                sched.run()

    def test_node_with_no_entry_gate_skips_to_exit(self, tmp_path: Path) -> None:
        """A node with no entry_gate must evaluate only the exit gate."""
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(),  # no entry_gate
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg:
            sched.run()

        gate_ids = [c.args[0] for c in mock_eg.call_args_list]
        assert "phase_01_gate" in gate_ids
        assert len(gate_ids) == 1, (
            f"Expected exactly one evaluate_gate call (exit only); got {gate_ids!r}"
        )

    def test_exit_gate_fail_sets_blocked_at_exit_in_ctx(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.run()

        ctx = RunContext.load(tmp_path, "test-run")
        assert ctx.get_node_state("n01_call_analysis") == "blocked_at_exit"

    def test_running_state_set_then_overwritten(self, tmp_path: Path) -> None:
        """
        Node passes through 'running' during dispatch; final state must be
        'released' (not stuck in 'running').
        """
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            sched.run()

        ctx = RunContext.load(tmp_path, "test-run")
        assert ctx.get_node_state("n01_call_analysis") == "released"
        assert ctx.get_node_state("n01_call_analysis") != "running"

    def test_scheduler_uses_real_is_ready_logic(self, tmp_path: Path) -> None:
        """
        Uses ManifestGraph.is_ready() without mocking the graph.
        n02 must NOT be dispatched until n01 is released.
        """
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        dispatch_log: list[str] = []

        def _fake_eg(gate_id, run_id, repo_root, **kwargs):
            # Identify the call order by checking n01's state
            ctx = RunContext.load(repo_root, run_id)
            if gate_id == "phase_02_gate":
                # At this point n01 must already be released
                assert ctx.get_node_state("n01_call_analysis") == "released", (
                    "n02's exit gate evaluated before n01 was released"
                )
            dispatch_log.append(gate_id)
            return _GATE_PASS

        with patch(_EG_TARGET, side_effect=_fake_eg):
            sched.run()

        assert "phase_01_gate" in dispatch_log
        assert "phase_02_gate" in dispatch_log

    def test_run_id_in_result_dict(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="run-xyz")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()
        assert result["run_id"] == "run-xyz"


# ===========================================================================
# Step 3 — _settle_stalled_nodes() and RunAbortedError
# ===========================================================================


# ---------------------------------------------------------------------------
# Helpers: additional synthetic manifest builders used by Step 3 tests
# ---------------------------------------------------------------------------


def _three_node_fork_join_manifest(
    n1: str = "n01",
    n2: str = "n02",
    n3: str = "n03",
) -> dict:
    """
    Fork-join: n01 → n03 and n02 → n03.
    n03 requires both n01 and n02 to be released.
    Used to test multiple unsatisfied incoming conditions on one stalled node.
    """
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {"node_id": n1, "exit_gate": "g01", "terminal": False},
            {"node_id": n2, "exit_gate": "g02", "terminal": False},
            {"node_id": n3, "exit_gate": "g03", "terminal": True},
        ],
        "edge_registry": [
            {"edge_id": "e1", "from_node": n1, "to_node": n3, "gate_condition": "g01"},
            {"edge_id": "e2", "from_node": n2, "to_node": n3, "gate_condition": "g02"},
        ],
    }


def _mixed_stall_and_hard_block_manifest() -> dict:
    """
    Manifest with:
    - n01 → n02 (linear chain; n01 may fail to stall n02)
    - n07_budget_gate → n08a_section_drafting (gate_09 triggers HARD_BLOCK)

    Used to verify that hard_blocked nodes and stalled nodes are
    independently tracked and do not interfere.
    """
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": "n01_call_analysis",
                "exit_gate": "phase_01_gate",
                "terminal": False,
            },
            {
                "node_id": "n02_concept_refinement",
                "exit_gate": "phase_02_gate",
                "terminal": False,
            },
            {
                "node_id": "n07_budget_gate",
                "exit_gate": "gate_09_budget_consistency",
                "terminal": False,
            },
            {
                "node_id": "n08a_section_drafting",
                "exit_gate": "gate_10_part_b_completeness",
                "terminal": True,
            },
        ],
        "edge_registry": [
            {
                "edge_id": "e01",
                "from_node": "n01_call_analysis",
                "to_node": "n02_concept_refinement",
                "gate_condition": "phase_01_gate",
            },
            {
                "edge_id": "e07",
                "from_node": "n07_budget_gate",
                "to_node": "n08a_section_drafting",
                "gate_condition": "gate_09_budget_consistency",
            },
        ],
    }


# ---------------------------------------------------------------------------
# _settle_stalled_nodes() unit tests (call the method directly)
# ---------------------------------------------------------------------------


class TestSettleStalledNodes:
    """Tests for DAGScheduler._settle_stalled_nodes() in isolation."""

    def test_returns_empty_when_all_nodes_released(self, tmp_path: Path) -> None:
        """When every node is released there are no stalled nodes."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            sched.run()

        # run() returned normally (no exception) → call _settle_stalled_nodes
        # on the post-run context directly to verify it returns [].
        report = sched._settle_stalled_nodes()
        assert report == []

    def test_returns_empty_when_only_blocked_nodes_remain(
        self, tmp_path: Path
    ) -> None:
        """
        A single node whose exit gate failed is blocked_at_exit (settled),
        not pending.  _settle_stalled_nodes must return [].
        """
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.run()  # single-node fail → blocked_at_exit → no abort

        report = sched._settle_stalled_nodes()
        assert report == []

    def test_returns_one_entry_for_two_node_linear_stall(
        self, tmp_path: Path
    ) -> None:
        """n01 fails → n02 is stalled pending → report has exactly one entry."""
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="stall-1"
        )
        # Drive the dispatch manually: dispatch n01 only (fails) so n02 stays pending.
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.ctx.set_node_state("n01_call_analysis", "running")
            sched.ctx.save()
            sched._dispatch_node("n01_call_analysis")
        # n01 is now blocked_at_exit; n02 is still pending.
        report = sched._settle_stalled_nodes()
        assert len(report) == 1
        assert report[0]["node_id"] == "n02_concept_refinement"

    def test_stall_report_includes_gate_id(self, tmp_path: Path) -> None:
        """The unsatisfied condition entry must record the gate_id."""
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="stall-gid"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.ctx.set_node_state("n01_call_analysis", "running")
            sched.ctx.save()
            sched._dispatch_node("n01_call_analysis")

        report = sched._settle_stalled_nodes()
        assert len(report) == 1
        cond = report[0]["unsatisfied_conditions"][0]
        assert cond["gate_id"] == "phase_01_gate"

    def test_stall_report_includes_source_node_state(self, tmp_path: Path) -> None:
        """The unsatisfied condition entry must record the source node's actual state."""
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="stall-state"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.ctx.set_node_state("n01_call_analysis", "running")
            sched.ctx.save()
            sched._dispatch_node("n01_call_analysis")

        report = sched._settle_stalled_nodes()
        cond = report[0]["unsatisfied_conditions"][0]
        assert cond["source_node_id"] == "n01_call_analysis"
        assert cond["source_node_state"] == "blocked_at_exit"

    def test_multiple_unsatisfied_conditions_all_reported(
        self, tmp_path: Path
    ) -> None:
        """
        Fork-join: n03 requires both n01 (g01) and n02 (g02).
        When both n01 and n02 fail, n03's stall report must list both
        unsatisfied conditions.
        """
        manifest = _three_node_fork_join_manifest()
        sched = _make_scheduler(tmp_path, manifest, run_id="multi-cond")

        # Drive dispatches manually: both n01 and n02 fail.
        for nid in ("n01", "n02"):
            with patch(_EG_TARGET, return_value=_GATE_FAIL):
                sched.ctx.set_node_state(nid, "running")
                sched.ctx.save()
                sched._dispatch_node(nid)

        report = sched._settle_stalled_nodes()
        assert len(report) == 1
        stalled = report[0]
        assert stalled["node_id"] == "n03"
        gate_ids = {c["gate_id"] for c in stalled["unsatisfied_conditions"]}
        assert gate_ids == {"g01", "g02"}

    def test_hard_blocked_nodes_excluded_from_stall_report(
        self, tmp_path: Path
    ) -> None:
        """
        hard_block_upstream nodes are settled (not pending) and must not
        appear in the stall report.
        """
        sched = _make_scheduler(
            tmp_path, _gate09_node_manifest(), run_id="hb-excl"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            sched.run()  # n07 fails, Phase 8 nodes hard_block_upstream → no abort

        report = sched._settle_stalled_nodes()
        stalled_ids = [e["node_id"] for e in report]
        for p8_id in PHASE_8_NODE_IDS:
            assert p8_id not in stalled_ids, (
                f"hard_block_upstream node {p8_id!r} must not appear in stall report"
            )


# ---------------------------------------------------------------------------
# RunAbortedError raising in run()
# ---------------------------------------------------------------------------


class TestRunAbortedErrorRaised:
    def test_run_raises_when_pending_nodes_remain(self, tmp_path: Path) -> None:
        """run() must raise RunAbortedError when at least one node stays pending."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError):
                sched.run()

    def test_exception_carries_result_dict(self, tmp_path: Path) -> None:
        """RunAbortedError.result must be a dict (not None)."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert isinstance(exc_info.value.result, dict)

    def test_aborted_result_contains_pending_nodes(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        result = exc_info.value.result
        assert "pending_nodes" in result
        assert "n02_concept_refinement" in result["pending_nodes"]

    def test_aborted_result_contains_stall_report(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        result = exc_info.value.result
        assert "stall_report" in result
        assert isinstance(result["stall_report"], list)
        assert len(result["stall_report"]) == 1
        assert result["stall_report"][0]["node_id"] == "n02_concept_refinement"

    def test_aborted_result_contains_hard_blocked_nodes(
        self, tmp_path: Path
    ) -> None:
        """
        When gate_09 fails (HARD_BLOCK) AND a separate upstream failure
        also stalls a node, the abort result must include hard_blocked_nodes.
        """
        sched = _make_scheduler(
            tmp_path,
            _mixed_stall_and_hard_block_manifest(),
            run_id="hb-mixed",
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        result = exc_info.value.result
        assert "hard_blocked_nodes" in result
        # n08a_section_drafting should be hard_block_upstream
        assert "n08a_section_drafting" in result["hard_blocked_nodes"]

    def test_aborted_result_aborted_flag_is_true(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert exc_info.value.result["aborted"] is True

    def test_exception_message_names_stalled_nodes(self, tmp_path: Path) -> None:
        """RunAbortedError message should reference the stalled node IDs."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert "n02_concept_refinement" in str(exc_info.value)


# ---------------------------------------------------------------------------
# HARD_BLOCK + stall interplay
# ---------------------------------------------------------------------------


class TestHardBlockAndStallInterplay:
    def test_gate09_failure_leaves_no_pending_phase8_nodes(
        self, tmp_path: Path
    ) -> None:
        """
        When gate_09 fails, Phase 8 nodes become hard_block_upstream (not
        pending), so no RunAbortedError is raised from the _gate09_node_manifest.
        """
        sched = _make_scheduler(
            tmp_path, _gate09_node_manifest(), run_id="hb-no-abort"
        )
        # Must NOT raise — all nodes are settled after HARD_BLOCK.
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert result["aborted"] is False
        assert result["hard_blocked_nodes"] != []

    def test_mixed_stall_and_hard_block_abort_distinguishes_them(
        self, tmp_path: Path
    ) -> None:
        """
        In a run with both a HARD_BLOCK path and an independent stalled path,
        the abort result must show:
        - hard_blocked_nodes (Phase 8 frozen nodes)
        - pending_nodes (genuinely stalled upstream-failure victims)
        - stall_report (detailing the stalled node's unsatisfied conditions)
        """
        sched = _make_scheduler(
            tmp_path,
            _mixed_stall_and_hard_block_manifest(),
            run_id="hb-mixed2",
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        result = exc_info.value.result
        # n02_concept_refinement is stalled (pending) because n01 failed
        assert "n02_concept_refinement" in result["pending_nodes"]
        # n08a_section_drafting is hard_blocked (not pending)
        assert "n08a_section_drafting" in result["hard_blocked_nodes"]
        assert "n08a_section_drafting" not in result["pending_nodes"]
        # stall_report only mentions the truly stalled node
        stalled_ids = [e["node_id"] for e in result["stall_report"]]
        assert "n02_concept_refinement" in stalled_ids
        assert "n08a_section_drafting" not in stalled_ids

    def test_hard_blocked_nodes_not_in_stall_report(self, tmp_path: Path) -> None:
        """
        _settle_stalled_nodes() must not include hard_block_upstream nodes
        in the stall report; those nodes are settled, not pending.
        """
        sched = _make_scheduler(
            tmp_path,
            _mixed_stall_and_hard_block_manifest(),
            run_id="hb-report",
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        stall_ids = [e["node_id"] for e in exc_info.value.result["stall_report"]]
        for p8_id in PHASE_8_NODE_IDS:
            assert p8_id not in stall_ids


# ---------------------------------------------------------------------------
# No false abort
# ---------------------------------------------------------------------------


class TestNoFalseAbort:
    def test_no_abort_when_all_nodes_released(self, tmp_path: Path) -> None:
        """Full-pass run must return normally without raising."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()  # must not raise

        assert result["aborted"] is False
        assert result["pending_nodes"] == []

    def test_no_abort_single_node_blocked_at_entry(self, tmp_path: Path) -> None:
        """A single node blocked_at_entry is settled; no RunAbortedError."""
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()  # must not raise

        assert result["aborted"] is False
        assert result["blocked_nodes"] == ["n01_call_analysis"]
        assert result["pending_nodes"] == []

    def test_no_abort_single_node_blocked_at_exit(self, tmp_path: Path) -> None:
        """A single node blocked_at_exit is settled; no RunAbortedError."""
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()  # must not raise

        assert result["aborted"] is False
        assert result["blocked_nodes"] == ["n01_call_analysis"]
        assert result["pending_nodes"] == []

    def test_no_abort_on_empty_graph(self, tmp_path: Path) -> None:
        """An empty graph has no pending nodes; run() returns normally."""
        data = {"name": "t", "version": "1.1", "node_registry": [], "edge_registry": []}
        mp = _write_manifest(tmp_path, data)
        graph = ManifestGraph.load(mp)
        ctx = RunContext.initialize(tmp_path, "empty-run")
        sched = DAGScheduler(graph, ctx, tmp_path)
        with patch(_EG_TARGET):
            result = sched.run()

        assert result["aborted"] is False
        assert result["pending_nodes"] == []

    def test_abort_driven_by_pending_not_by_blocked(self, tmp_path: Path) -> None:
        """
        Blocked (settled) nodes must not trigger an abort.
        Only genuinely pending nodes matter for the abort decision.
        """
        # Single node, exit gate fails → blocked_at_exit (settled, not pending)
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="no-abort")
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        # blocked_at_exit is settled → aborted=False
        assert result["aborted"] is False
        assert result["stalled"] is False

    def test_stall_report_empty_on_full_pass(self, tmp_path: Path) -> None:
        """On a full-pass run, stall_report must be an empty list."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert result["stall_report"] == []

    def test_result_contains_stall_report_key_on_success(
        self, tmp_path: Path
    ) -> None:
        """stall_report key must be present even on a successful run."""
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert "stall_report" in result
        assert "aborted" in result


# ===========================================================================
# Step 4 — RunSummary structure, persistence, overall_status, gate index
# ===========================================================================

import json as _json  # local alias to avoid shadowing if any

from runner.dag_scheduler import RunSummary
from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.versions import CONSTITUTION_VERSION, LIBRARY_VERSION, MANIFEST_VERSION


# ---------------------------------------------------------------------------
# Helpers: additional manifest builders for Step 4 scenarios
# ---------------------------------------------------------------------------


def _two_terminal_manifest() -> dict:
    """
    Fork: n01 → n02 (terminal) and n01 → n03 (terminal).
    Used for partial_pass tests (n02 passes, n03 fails → one terminal reached).
    """
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {"node_id": "n01", "exit_gate": "g01", "terminal": False},
            {"node_id": "n02", "exit_gate": "g02", "terminal": True},
            {"node_id": "n03", "exit_gate": "g03", "terminal": True},
        ],
        "edge_registry": [
            {"edge_id": "e1", "from_node": "n01", "to_node": "n02", "gate_condition": "g01"},
            {"edge_id": "e2", "from_node": "n01", "to_node": "n03", "gate_condition": "g01"},
        ],
    }


def _read_summary_json(run_dir: Path) -> dict:
    """Read and parse the run_summary.json written inside *run_dir*."""
    path = run_dir / "run_summary.json"
    assert path.exists(), f"run_summary.json not found at {path}"
    return _json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# RunSummary structure
# ---------------------------------------------------------------------------


class TestRunSummaryStructure:
    """run() returns a RunSummary with all required plan-schema fields."""

    _PLAN_SCHEMA_KEYS = {
        "run_id",
        "manifest_version",
        "library_version",
        "constitution_version",
        "started_at",
        "completed_at",
        "overall_status",
        "terminal_nodes_reached",
        "stalled_nodes",
        "hard_blocked_nodes",
        "node_states",
        "gate_results_index",
    }

    def test_run_returns_run_summary_instance(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert isinstance(result, RunSummary)

    def test_summary_has_all_plan_schema_fields(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        d = result.to_dict()
        assert self._PLAN_SCHEMA_KEYS.issubset(d.keys())

    def test_summary_version_fields_match_constants(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert result.manifest_version == MANIFEST_VERSION
        assert result.library_version == LIBRARY_VERSION
        assert result.constitution_version == CONSTITUTION_VERSION

    def test_summary_run_id_matches_context(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="schema-id")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert result.run_id == "schema-id"

    def test_summary_node_states_contains_all_graph_nodes(
        self, tmp_path: Path
    ) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert set(result.node_states.keys()) == {
            "n01_call_analysis",
            "n02_concept_refinement",
        }

    def test_summary_dispatched_nodes_present(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert result.dispatched_nodes == [
            "n01_call_analysis",
            "n02_concept_refinement",
        ]


# ---------------------------------------------------------------------------
# run_summary.json persistence
# ---------------------------------------------------------------------------


class TestRunSummaryPersistence:
    def test_summary_file_written_on_successful_run(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="write-pass")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            sched.run()

        run_dir = tmp_path / ".claude" / "runs" / "write-pass"
        assert (run_dir / "run_summary.json").exists()

    def test_summary_file_written_on_aborted_run(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="write-abort"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError):
                sched.run()

        run_dir = tmp_path / ".claude" / "runs" / "write-abort"
        assert (run_dir / "run_summary.json").exists()

    def test_written_json_contains_plan_schema_keys(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="json-keys")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            sched.run()

        run_dir = tmp_path / ".claude" / "runs" / "json-keys"
        d = _read_summary_json(run_dir)
        plan_keys = {
            "run_id", "manifest_version", "library_version", "constitution_version",
            "started_at", "completed_at", "overall_status",
            "terminal_nodes_reached", "stalled_nodes", "hard_blocked_nodes",
            "node_states", "gate_results_index",
        }
        assert plan_keys.issubset(d.keys())

    def test_written_json_matches_returned_summary(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _single_node_manifest(), run_id="json-match"
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            summary = sched.run()

        run_dir = tmp_path / ".claude" / "runs" / "json-match"
        d = _read_summary_json(run_dir)
        assert d["run_id"] == summary.run_id
        assert d["overall_status"] == summary.overall_status
        assert d["node_states"] == summary.node_states

    def test_written_json_path_returned_by_write(self, tmp_path: Path) -> None:
        """RunSummary.write() returns the path of the written file."""
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        ctx = RunContext.initialize(tmp_path, "write-path")
        summary = RunSummary.build(
            ctx=ctx,
            graph=graph,
            dispatched_nodes=[],
            evaluated_gates=[],
            stalled_nodes=[],
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:01+00:00",
        )
        written_path = summary.write(ctx.run_dir)
        assert written_path.name == "run_summary.json"
        assert written_path.exists()

    def test_summary_written_before_exception_on_abort(
        self, tmp_path: Path
    ) -> None:
        """
        The summary file must exist on disk when RunAbortedError is caught.
        """
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="before-exc"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            try:
                sched.run()
            except RunAbortedError:
                pass  # file must already be written

        run_dir = tmp_path / ".claude" / "runs" / "before-exc"
        assert (run_dir / "run_summary.json").exists()


# ---------------------------------------------------------------------------
# overall_status
# ---------------------------------------------------------------------------


class TestOverallStatus:
    def test_pass_on_full_release(self, tmp_path: Path) -> None:
        """All terminal nodes reached → overall_status == "pass"."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert result.overall_status == "pass"

    def test_fail_on_single_node_blocked_at_exit(self, tmp_path: Path) -> None:
        """No terminal nodes + blocked failure → overall_status == "fail"."""
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert result.overall_status == "fail"

    def test_fail_on_single_node_blocked_at_entry(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert result.overall_status == "fail"

    def test_aborted_on_stalled_run(self, tmp_path: Path) -> None:
        """Pending nodes remain → overall_status == "aborted"."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert exc_info.value.summary.overall_status == "aborted"

    def test_partial_pass_on_fork_with_one_terminal_released(
        self, tmp_path: Path
    ) -> None:
        """
        Fork: n01 released, n02 (terminal) released, n03 (terminal) blocked
        → partial_pass.
        The mock alternates pass/fail: n01 passes, n02 passes, n03 fails.
        """
        call_count = [0]

        def _alternating(gate_id, run_id, repo_root, **kwargs):
            call_count[0] += 1
            # g01 (n01 exit) → pass; g02 (n02 exit) → pass; g03 (n03 exit) → fail
            if gate_id == "g03":
                return _GATE_FAIL
            return _GATE_PASS

        sched = _make_scheduler(
            tmp_path, _two_terminal_manifest(), run_id="partial"
        )
        with patch(_EG_TARGET, side_effect=_alternating):
            result = sched.run()

        assert result.overall_status == "partial_pass"
        assert "n02" in result.terminal_nodes_reached
        assert "n03" not in result.terminal_nodes_reached

    def test_pass_on_empty_graph(self, tmp_path: Path) -> None:
        """An empty graph has no failures → overall_status == "pass"."""
        data = {
            "name": "t",
            "version": "1.1",
            "node_registry": [],
            "edge_registry": [],
        }
        mp = _write_manifest(tmp_path, data)
        graph = ManifestGraph.load(mp)
        ctx = RunContext.initialize(tmp_path, "empty-status")
        sched = DAGScheduler(graph, ctx, tmp_path)
        with patch(_EG_TARGET):
            result = sched.run()

        assert result.overall_status == "pass"

    def test_fail_on_hard_block_with_no_terminal_nodes(
        self, tmp_path: Path
    ) -> None:
        """
        gate_09 failure → hard_block_upstream on Phase 8 nodes → no terminal
        nodes in manifest → overall_status == "fail".
        """
        sched = _make_scheduler(
            tmp_path, _gate09_node_manifest(), run_id="hb-status"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert result.overall_status == "fail"


# ---------------------------------------------------------------------------
# Stalled / hard-blocked reporting in RunSummary
# ---------------------------------------------------------------------------


class TestSummaryBlockingReporting:
    def test_stalled_nodes_in_summary_after_abort(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="sum-stall"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        stalled_ids = [e["node_id"] for e in summary.stalled_nodes]
        assert "n02_concept_refinement" in stalled_ids

    def test_hard_blocked_nodes_in_summary(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _gate09_node_manifest(), run_id="sum-hb"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        for p8 in PHASE_8_NODE_IDS:
            assert p8 in result.hard_blocked_nodes

    def test_hard_blocked_not_in_stalled_nodes(self, tmp_path: Path) -> None:
        """hard_block_upstream nodes must not appear in stalled_nodes."""
        sched = _make_scheduler(
            tmp_path, _gate09_node_manifest(), run_id="sum-hb-sep"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        stalled_ids = [e["node_id"] for e in result.stalled_nodes]
        for p8 in PHASE_8_NODE_IDS:
            assert p8 not in stalled_ids


# ---------------------------------------------------------------------------
# RunAbortedError carries RunSummary
# ---------------------------------------------------------------------------


class TestRunAbortedErrorCarriesSummary:
    def test_exception_has_summary_attribute(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert isinstance(exc_info.value.summary, RunSummary)

    def test_summary_and_result_are_consistent(self, tmp_path: Path) -> None:
        """exc.result must equal exc.summary.to_dict() for backward compat."""
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="compat"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        exc = exc_info.value
        assert exc.result["run_id"] == exc.summary.run_id
        assert exc.result["overall_status"] == exc.summary.overall_status
        assert exc.result["overall_status"] == "aborted"

    def test_summary_file_exists_when_exception_caught(
        self, tmp_path: Path
    ) -> None:
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="file-on-exc"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError):
                sched.run()

        run_dir = tmp_path / ".claude" / "runs" / "file-on-exc"
        assert (run_dir / "run_summary.json").exists()

    def test_aborted_summary_overall_status_in_json(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _two_node_linear_manifest(), run_id="aborted-json"
        )
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            with pytest.raises(RunAbortedError):
                sched.run()

        run_dir = tmp_path / ".claude" / "runs" / "aborted-json"
        d = _read_summary_json(run_dir)
        assert d["overall_status"] == "aborted"


# ---------------------------------------------------------------------------
# gate_results_index
# ---------------------------------------------------------------------------


class TestGateResultsIndex:
    def test_index_present_in_summary(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _single_node_manifest(), run_id="gri-present"
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert isinstance(result.gate_results_index, dict)

    def test_index_contains_evaluated_exit_gate(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _single_node_manifest(), run_id="gri-exit"
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        # phase_01_gate is the exit gate for n01_call_analysis
        assert "phase_01_gate" in result.gate_results_index

    def test_index_contains_entry_gate_when_evaluated(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
            run_id="gri-entry",
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert "gate_01_source_integrity" in result.gate_results_index
        assert "phase_01_gate" in result.gate_results_index

    def test_registered_gate_uses_canonical_tier4_path(
        self, tmp_path: Path
    ) -> None:
        """
        A gate_id in GATE_RESULT_PATHS must map to the correct Tier 4 path.
        """
        sched = _make_scheduler(
            tmp_path, _single_node_manifest(), run_id="gri-canonical"
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        expected_suffix = GATE_RESULT_PATHS["phase_01_gate"]
        path_str = result.gate_results_index["phase_01_gate"]
        assert path_str.startswith("docs/tier4_orchestration_state/")
        assert path_str.endswith(expected_suffix)

    def test_unregistered_gate_uses_fallback_path(self, tmp_path: Path) -> None:
        """
        A gate_id not in GATE_RESULT_PATHS uses the fallback sub-path.
        This exercises synthetic test gates like "g01".
        """
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {"node_id": "n01", "exit_gate": "synthetic_gate_xyz", "terminal": False}
            ],
            "edge_registry": [],
        }
        sched = _make_scheduler(tmp_path, data, run_id="gri-fallback")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert "synthetic_gate_xyz" in result.gate_results_index
        path_str = result.gate_results_index["synthetic_gate_xyz"]
        assert "gate_results/synthetic_gate_xyz.json" in path_str

    def test_empty_graph_has_empty_index(self, tmp_path: Path) -> None:
        data = {
            "name": "t",
            "version": "1.1",
            "node_registry": [],
            "edge_registry": [],
        }
        mp = _write_manifest(tmp_path, data)
        graph = ManifestGraph.load(mp)
        ctx = RunContext.initialize(tmp_path, "gri-empty")
        sched = DAGScheduler(graph, ctx, tmp_path)
        with patch(_EG_TARGET):
            result = sched.run()

        assert result.gate_results_index == {}

    def test_index_in_written_json(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _single_node_manifest(), run_id="gri-json"
        )
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            sched.run()

        run_dir = tmp_path / ".claude" / "runs" / "gri-json"
        d = _read_summary_json(run_dir)
        assert "gate_results_index" in d
        assert isinstance(d["gate_results_index"], dict)


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


class TestTimestamps:
    def test_started_at_and_completed_at_present(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="ts-keys")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert result.started_at
        assert result.completed_at

    def test_timestamps_are_iso8601_strings(self, tmp_path: Path) -> None:
        from datetime import datetime

        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="ts-fmt")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        # Should parse without error
        datetime.fromisoformat(result.started_at)
        datetime.fromisoformat(result.completed_at)

    def test_started_at_not_after_completed_at(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id="ts-order")
        with patch(_EG_TARGET, return_value=_GATE_PASS):
            result = sched.run()

        assert result.started_at <= result.completed_at


# ===========================================================================
# Step 5 — CLI entry point (runner/__main__.py)
# ===========================================================================
#
# Tests use patched external dependencies so no live repository artifacts
# are required.  All patches target names as imported in runner.__main__:
#
#   runner.__main__.find_repo_root
#   runner.__main__.ManifestGraph.load  (via runner.__main__.ManifestGraph)
#   runner.__main__.RunContext.initialize
#   runner.__main__.DAGScheduler
#
# The DAGScheduler constructor is patched as a class so that
# ``mock_cls.return_value`` is the scheduler instance and
# ``mock_cls.return_value.run`` is the method under test.
# ---------------------------------------------------------------------------


from runner.__main__ import main as cli_main  # noqa: E402
from runner.dag_scheduler import RunSummary  # noqa: E402  (already imported above, harmless re-import)


# Patch target constants for Step 5
_FR = "runner.__main__.find_repo_root"
_ML = "runner.__main__.ManifestGraph.load"
_RI = "runner.__main__.RunContext.initialize"
_DS = "runner.__main__.DAGScheduler"


def _make_mock_summary(overall_status: str = "pass") -> MagicMock:
    """Return a MagicMock that quacks like a RunSummary."""
    s = MagicMock()
    s.overall_status = overall_status
    s.terminal_nodes_reached = []
    s.stalled_nodes = []
    s.hard_blocked_nodes = []
    s.node_states = {}
    return s


def _make_mock_graph(
    node_ids: list | None = None, ready: bool = False
) -> MagicMock:
    g = MagicMock()
    g.node_ids.return_value = node_ids or []
    g.is_ready.return_value = ready
    return g


def _base_argv(tmp_path: Path, extra: list | None = None) -> list:
    """Minimal argv that supplies --run-id and --repo-root."""
    argv = ["--run-id", "cli-test", "--repo-root", str(tmp_path)]
    if extra:
        argv += extra
    return argv


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


class TestCLIExitCodes:
    def test_exit_0_on_pass(self, tmp_path: Path) -> None:
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    code = cli_main(_base_argv(tmp_path))
        assert code == 0

    def test_exit_1_on_fail(self, tmp_path: Path) -> None:
        summary = _make_mock_summary("fail")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    code = cli_main(_base_argv(tmp_path))
        assert code == 1

    def test_exit_1_on_partial_pass(self, tmp_path: Path) -> None:
        summary = _make_mock_summary("partial_pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    code = cli_main(_base_argv(tmp_path))
        assert code == 1

    def test_exit_2_on_run_aborted(self, tmp_path: Path) -> None:
        summary = _make_mock_summary("aborted")
        exc = RunAbortedError("stalled", summary)
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.side_effect = exc
                    code = cli_main(_base_argv(tmp_path))
        assert code == 2

    def test_exit_3_on_dag_scheduler_error(self, tmp_path: Path) -> None:
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.side_effect = DAGSchedulerError("bad cfg")
                    code = cli_main(_base_argv(tmp_path))
        assert code == 3

    def test_exit_3_on_find_repo_root_failure(self) -> None:
        """RuntimeError from find_repo_root (no --repo-root given) → exit 3."""
        with patch(_FR, side_effect=RuntimeError("no root")):
            code = cli_main(["--run-id", "no-root"])
        assert code == 3

    def test_exit_3_on_manifest_load_error(self, tmp_path: Path) -> None:
        with patch(_ML, side_effect=FileNotFoundError("missing manifest")):
            with patch(_RI):
                code = cli_main(_base_argv(tmp_path))
        assert code == 3

    def test_run_id_required_raises_system_exit(self) -> None:
        with pytest.raises(SystemExit):
            cli_main([])


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestCLIDryRun:
    def test_dry_run_prints_ready_nodes(self, tmp_path: Path, capsys) -> None:
        graph = _make_mock_graph(
            node_ids=["n01_call_analysis", "n02_concept_refinement"],
            ready=True,
        )
        with patch(_ML, return_value=graph):
            with patch(_RI):
                with patch(_DS):
                    code = cli_main(_base_argv(tmp_path, ["--dry-run"]))

        out = capsys.readouterr().out
        assert "n01_call_analysis" in out
        assert "n02_concept_refinement" in out
        assert code == 0

    def test_dry_run_does_not_call_scheduler_run(self, tmp_path: Path) -> None:
        graph = _make_mock_graph(node_ids=["n01_call_analysis"], ready=True)
        with patch(_ML, return_value=graph):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    cli_main(_base_argv(tmp_path, ["--dry-run"]))
                    mock_cls.return_value.run.assert_not_called()

    def test_dry_run_exits_0_with_no_ready_nodes(self, tmp_path: Path) -> None:
        graph = _make_mock_graph(node_ids=[], ready=False)
        with patch(_ML, return_value=graph):
            with patch(_RI):
                with patch(_DS):
                    code = cli_main(_base_argv(tmp_path, ["--dry-run"]))
        assert code == 0

    def test_dry_run_skips_non_ready_nodes(self, tmp_path: Path, capsys) -> None:
        """Only nodes where graph.is_ready() returns True are printed."""
        graph = MagicMock()
        graph.node_ids.return_value = ["n01_call_analysis", "n02_concept_refinement"]
        graph.is_ready.side_effect = lambda nid, ctx: nid == "n01_call_analysis"
        with patch(_ML, return_value=graph):
            with patch(_RI):
                with patch(_DS):
                    cli_main(_base_argv(tmp_path, ["--dry-run"]))

        out = capsys.readouterr().out
        assert "n01_call_analysis" in out
        assert "n02_concept_refinement" not in out


# ---------------------------------------------------------------------------
# JSON output mode
# ---------------------------------------------------------------------------


class TestCLIJsonMode:
    def test_all_lines_valid_json(self, tmp_path: Path, capsys) -> None:
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    cli_main(_base_argv(tmp_path, ["--json"]))

        lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
        assert lines, "Expected at least one JSON line"
        for ln in lines:
            obj = json.loads(ln)
            assert "event" in obj
            assert "timestamp" in obj

    def test_summary_event_present_on_pass(self, tmp_path: Path, capsys) -> None:
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    cli_main(_base_argv(tmp_path, ["--json"]))

        lines = capsys.readouterr().out.splitlines()
        events = [json.loads(ln)["event"] for ln in lines if ln.strip()]
        assert "summary" in events

    def test_summary_event_present_on_abort(self, tmp_path: Path, capsys) -> None:
        summary = _make_mock_summary("aborted")
        exc = RunAbortedError("stalled", summary)
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.side_effect = exc
                    cli_main(_base_argv(tmp_path, ["--json"]))

        lines = capsys.readouterr().out.splitlines()
        events = [json.loads(ln)["event"] for ln in lines if ln.strip()]
        assert "summary" in events

    def test_error_event_on_config_failure(self, tmp_path: Path, capsys) -> None:
        with patch(_ML, side_effect=FileNotFoundError("missing")):
            with patch(_RI):
                cli_main(_base_argv(tmp_path, ["--json"]))

        out = capsys.readouterr().out.strip()
        obj = json.loads(out)
        assert obj["event"] == "error"

    def test_dry_run_ready_events_in_json(self, tmp_path: Path, capsys) -> None:
        graph = _make_mock_graph(node_ids=["n01_call_analysis"], ready=True)
        with patch(_ML, return_value=graph):
            with patch(_RI):
                with patch(_DS):
                    cli_main(_base_argv(tmp_path, ["--dry-run", "--json"]))

        lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
        events = [json.loads(ln)["event"] for ln in lines]
        assert "ready" in events
        ready_objs = [json.loads(ln) for ln in lines if json.loads(ln)["event"] == "ready"]
        assert ready_objs[0]["node_id"] == "n01_call_analysis"


# ---------------------------------------------------------------------------
# Path wiring
# ---------------------------------------------------------------------------


class TestCLIPathWiring:
    def test_repo_root_arg_forwarded_to_run_context(self, tmp_path: Path) -> None:
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI) as mock_init:
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    cli_main(["--run-id", "path-test", "--repo-root", str(tmp_path)])

        call_args = mock_init.call_args
        assert call_args[0][0] == Path(str(tmp_path)).resolve()

    def test_custom_manifest_path_passed_to_graph_load(self, tmp_path: Path) -> None:
        custom = str(tmp_path / "custom_manifest.yaml")
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()) as mock_load:
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    cli_main(_base_argv(tmp_path, ["--manifest-path", custom]))

        mock_load.assert_called_once_with(Path(custom))

    def test_custom_library_path_forwarded_to_dag_scheduler(self, tmp_path: Path) -> None:
        custom_lib = str(tmp_path / "custom_library.yaml")
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    cli_main(_base_argv(tmp_path, ["--library-path", custom_lib]))

        _, kwargs = mock_cls.call_args
        assert kwargs.get("library_path") == Path(custom_lib)

    def test_find_repo_root_called_without_repo_root_arg(self) -> None:
        summary = _make_mock_summary("pass")
        fake_root = Path("/fake/repo")
        with patch(_FR, return_value=fake_root) as mock_fr:
            with patch(_ML, return_value=_make_mock_graph()):
                with patch(_RI):
                    with patch(_DS) as mock_cls:
                        mock_cls.return_value.run.return_value = summary
                        cli_main(["--run-id", "auto-root"])
        mock_fr.assert_called_once()

    def test_run_id_forwarded_to_run_context_initialize(self, tmp_path: Path) -> None:
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI) as mock_init:
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    cli_main(["--run-id", "my-run-id", "--repo-root", str(tmp_path)])

        call_args = mock_init.call_args
        assert call_args[0][1] == "my-run-id"


# ---------------------------------------------------------------------------
# Summary output content
# ---------------------------------------------------------------------------


class TestCLISummaryOutput:
    def test_summary_line_contains_overall_status(self, tmp_path: Path, capsys) -> None:
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    cli_main(_base_argv(tmp_path))

        out = capsys.readouterr().out
        assert "overall_status=pass" in out

    def test_run_start_line_contains_run_id(self, tmp_path: Path, capsys) -> None:
        summary = _make_mock_summary("pass")
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.return_value = summary
                    cli_main(_base_argv(tmp_path))

        out = capsys.readouterr().out
        assert "cli-test" in out  # run_id from _base_argv

    def test_summary_line_emitted_after_abort(self, tmp_path: Path, capsys) -> None:
        summary = _make_mock_summary("aborted")
        exc = RunAbortedError("stalled", summary)
        with patch(_ML, return_value=_make_mock_graph()):
            with patch(_RI):
                with patch(_DS) as mock_cls:
                    mock_cls.return_value.run.side_effect = exc
                    cli_main(_base_argv(tmp_path))

        out = capsys.readouterr().out
        assert "overall_status=aborted" in out

