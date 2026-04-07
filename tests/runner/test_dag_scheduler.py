"""
Tests for runner.dag_scheduler.DAGScheduler (DAG scheduler Step 2).

Covers:
  1.  single-node: entry gate passes, exit gate passes → released
  2.  single-node: entry gate fails → blocked_at_entry, never reaches exit
  3.  two-node linear: first released → second dispatched and released
  4.  two-node linear: first exit gate fails → second stays pending, stalled=True
  5.  dispatch order follows manifest registry order
  6.  run() stops when no nodes are ready
  7.  gate_09_budget_consistency failure triggers mark_hard_block_downstream()
  8.  after gate_09 failure, all canonical Phase 8 node IDs are hard_block_upstream
  9.  _dispatch_node() forwards library_path and manifest_path to evaluate_gate()
  10. run() result dict reports correct released / blocked / pending / hard_blocked

Additional invariant tests:
  - node with no exit gate raises DAGSchedulerError
  - run() with no nodes in graph produces empty result
  - single-node with no entry gate skips straight to exit gate evaluation
  - ctx.mark_hard_block_downstream() called even when evaluate_gate is mocked

All tests use patched evaluate_gate and synthetic manifests / RunContext
instances backed by tmp_path.  No live repository artifacts are read.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
import yaml

from runner.dag_scheduler import DAGScheduler, DAGSchedulerError, ManifestGraph
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
# 4. Two-node linear: first exit gate fails → second stays pending, stalled
# ---------------------------------------------------------------------------


class TestTwoNodeLinearFirstFails:
    def test_n2_remains_pending(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert "n02_concept_refinement" in result["pending_nodes"]

    def test_n1_is_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert "n01_call_analysis" in result["blocked_nodes"]

    def test_n2_never_dispatched(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert "n02_concept_refinement" not in result["dispatched_nodes"]

    def test_stalled_true(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

        assert result["stalled"] is True


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
        """Once upstream fails, no downstream node becomes ready; loop stops."""
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL) as mock_eg:
            result = sched.run()

        # evaluate_gate called exactly once (for n01's exit gate only)
        assert mock_eg.call_count == 1
        assert result["pending_nodes"] == ["n02_concept_refinement"]


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
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - result.keys()!r}"
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
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())
        with patch(_EG_TARGET, return_value=_GATE_FAIL):
            result = sched.run()

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
