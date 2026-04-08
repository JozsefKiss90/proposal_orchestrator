"""
Step 6 — Full DAG integration scenarios.

End-to-end scheduler tests that exercise the real DAGScheduler,
ManifestGraph, and RunContext on synthetic multi-node DAGs written to
tmp_path.  ``evaluate_gate`` is patched to control pass/fail outcomes;
no live repository artifacts are required.

Scenarios
---------
1. LinearAllPass   — 4-node chain (n01→n02→n03→n04); all gates pass.
2. ParallelPath    — Fork at n01 to n04 and n05; join at n06 (terminal).
3. EarlyFailStall  — n02 exit gate fails; n03+n04 stall; RunAbortedError raised.
4. HardBlock       — gate_09 fails on n07_budget_gate; Phase 8 nodes frozen.
5. PartialPass     — Two terminal branches from n01; one passes, one fails.

Test philosophy
---------------
- Real ``DAGScheduler``, ``ManifestGraph``, ``RunContext``.
- Synthetic manifest files written to ``tmp_path`` via YAML.
- ``evaluate_gate`` patched at ``runner.dag_scheduler.evaluate_gate``.
- Assertions cover: ``overall_status``, ``dispatched_nodes`` order,
  ``terminal_nodes_reached``, ``stalled_nodes``, ``hard_blocked_nodes``,
  ``node_states``, ``gate_results_index`` form, and ``run_summary.json``
  artifact presence and content.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from unittest.mock import patch

import pytest
import yaml

from runner.dag_scheduler import (
    DAGScheduler,
    ManifestGraph,
    RunAbortedError,
    RunSummary,
)
from runner.run_context import PHASE_8_NODE_IDS, RunContext


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EG_TARGET = "runner.dag_scheduler.evaluate_gate"
_PASS = {"status": "pass"}
_FAIL = {"status": "fail"}


# ---------------------------------------------------------------------------
# Manifest construction helpers
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    """Write *data* as YAML to ``tmp_path/manifest.yaml`` and return the path."""
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _node(
    node_id: str,
    exit_gate: str,
    *,
    entry_gate: str | None = None,
    terminal: bool = False,
) -> dict:
    """Return a minimal node-registry entry dict."""
    entry: dict = {"node_id": node_id, "exit_gate": exit_gate, "terminal": terminal}
    if entry_gate:
        entry["entry_gate"] = entry_gate
    return entry


def _edge(edge_id: str, from_node: str, to_node: str, gate_condition: str) -> dict:
    """Return a minimal edge-registry entry dict."""
    return {
        "edge_id": edge_id,
        "from_node": from_node,
        "to_node": to_node,
        "gate_condition": gate_condition,
    }


def _manifest(name: str, nodes: list[dict], edges: list[dict]) -> dict:
    """Assemble a synthetic manifest dict."""
    return {
        "name": name,
        "version": "1.1",
        "node_registry": nodes,
        "edge_registry": edges,
    }


# ---------------------------------------------------------------------------
# Scheduler factory
# ---------------------------------------------------------------------------


def _make_scheduler(
    tmp_path: Path,
    manifest_data: dict,
    run_id: str,
) -> DAGScheduler:
    """
    Build a ``DAGScheduler`` from a synthetic manifest and a fresh RunContext.

    The scheduler uses ``tmp_path`` as the repo root so all run artifacts
    land inside the pytest tmp directory.
    """
    mp = _write_manifest(tmp_path, manifest_data)
    graph = ManifestGraph.load(mp)
    ctx = RunContext.initialize(tmp_path, run_id)
    return DAGScheduler(graph, ctx, tmp_path, library_path=None, manifest_path=mp)


# ---------------------------------------------------------------------------
# Mock helper
# ---------------------------------------------------------------------------


def _gate_pass_except(*failing_gates: str) -> Callable:
    """
    Return an ``evaluate_gate`` side-effect that passes all gates except
    those listed in *failing_gates*.
    """
    fail_set = set(failing_gates)

    def _side_effect(gate_id: str, *args, **kwargs) -> dict:
        return _FAIL if gate_id in fail_set else _PASS

    return _side_effect


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------


def _read_run_summary(tmp_path: Path, run_id: str) -> dict:
    """Read and return the ``run_summary.json`` written for *run_id*."""
    path = tmp_path / ".claude" / "runs" / run_id / "run_summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary_exists(tmp_path: Path, run_id: str) -> bool:
    path = tmp_path / ".claude" / "runs" / run_id / "run_summary.json"
    return path.exists()


# ---------------------------------------------------------------------------
# Scenario manifest definitions
# ---------------------------------------------------------------------------


def _linear_manifest() -> dict:
    """
    4-node linear chain:
        n01_call_analysis (entry=gate_01_source_integrity, exit=phase_01_gate)
        → n02_concept_refinement (exit=phase_02_gate)
        → n03_wp_design          (exit=phase_03_gate)
        → n04_gantt_milestones   (exit=phase_04_gate, terminal)
    """
    return _manifest(
        "test_linear",
        nodes=[
            _node(
                "n01_call_analysis",
                "phase_01_gate",
                entry_gate="gate_01_source_integrity",
            ),
            _node("n02_concept_refinement", "phase_02_gate"),
            _node("n03_wp_design", "phase_03_gate"),
            _node("n04_gantt_milestones", "phase_04_gate", terminal=True),
        ],
        edges=[
            _edge("e01", "n01_call_analysis", "n02_concept_refinement", "phase_01_gate"),
            _edge("e02", "n02_concept_refinement", "n03_wp_design", "phase_02_gate"),
            _edge("e03", "n03_wp_design", "n04_gantt_milestones", "phase_03_gate"),
        ],
    )


def _parallel_path_manifest() -> dict:
    """
    Fork-join:
        n01_call_analysis → n04_gantt_milestones  (branch A)
        n01_call_analysis → n05_impact_architecture (branch B)
        n04 + n05 → n06_implementation_architecture (join, terminal)

    n06 requires both n04 (via phase_04_gate) and n05 (via phase_05_gate)
    to be released before it is ready.  The two separate incoming edges
    implement the AND-join semantics.
    """
    return _manifest(
        "test_parallel",
        nodes=[
            _node("n01_call_analysis", "phase_01_gate"),
            _node("n04_gantt_milestones", "phase_04_gate"),
            _node("n05_impact_architecture", "phase_05_gate"),
            _node("n06_implementation_architecture", "phase_06_gate", terminal=True),
        ],
        edges=[
            _edge("e01", "n01_call_analysis", "n04_gantt_milestones", "phase_01_gate"),
            _edge("e02", "n01_call_analysis", "n05_impact_architecture", "phase_01_gate"),
            _edge(
                "e03",
                "n04_gantt_milestones",
                "n06_implementation_architecture",
                "phase_04_gate",
            ),
            _edge(
                "e04",
                "n05_impact_architecture",
                "n06_implementation_architecture",
                "phase_05_gate",
            ),
        ],
    )


def _early_fail_manifest() -> dict:
    """
    4-node linear chain where n02's exit gate will fail:
        n01 (pass) → n02 (FAIL) → n03 (stall) → n04 (stall, terminal)
    """
    return _manifest(
        "test_early_fail",
        nodes=[
            _node("n01_call_analysis", "phase_01_gate"),
            _node("n02_concept_refinement", "phase_02_gate"),
            _node("n03_wp_design", "phase_03_gate"),
            _node("n04_gantt_milestones", "phase_04_gate", terminal=True),
        ],
        edges=[
            _edge("e01", "n01_call_analysis", "n02_concept_refinement", "phase_01_gate"),
            _edge("e02", "n02_concept_refinement", "n03_wp_design", "phase_02_gate"),
            _edge("e03", "n03_wp_design", "n04_gantt_milestones", "phase_03_gate"),
        ],
    )


def _hard_block_manifest() -> dict:
    """
    n07_budget_gate (exit=gate_09_budget_consistency, no incoming edges)
    → n08a_section_drafting (via explicit edge)

    n08b, n08c, n08d are in the node registry but have no incoming edges
    in this manifest; they are frozen by mark_hard_block_downstream()
    when gate_09 fails, not by edge-graph starvation.

    This tests that HARD_BLOCK propagation works irrespective of edge
    connectivity.
    """
    return _manifest(
        "test_hard_block",
        nodes=[
            _node("n07_budget_gate", "gate_09_budget_consistency"),
            _node("n08a_section_drafting", "gate_10_part_b_completeness"),
            _node("n08b_assembly", "gate_10_part_b_completeness"),
            _node("n08c_evaluator_review", "gate_11_review_closure"),
            _node("n08d_revision", "gate_12_constitutional_compliance", terminal=True),
        ],
        edges=[
            _edge(
                "e07_to_08a",
                "n07_budget_gate",
                "n08a_section_drafting",
                "gate_09_budget_consistency",
            ),
        ],
    )


def _partial_pass_manifest() -> dict:
    """
    n01 forks to two terminal nodes:
        n01 (pass) → n02 (pass, terminal)
                  → n03 (FAIL, terminal)

    n02 reaches terminal; n03 is blocked_at_exit.
    Expected overall_status: partial_pass.
    """
    return _manifest(
        "test_partial_pass",
        nodes=[
            _node("n01_call_analysis", "phase_01_gate"),
            _node("n02_concept_refinement", "phase_02_gate", terminal=True),
            _node("n03_wp_design", "phase_03_gate", terminal=True),
        ],
        edges=[
            _edge("e01", "n01_call_analysis", "n02_concept_refinement", "phase_01_gate"),
            _edge("e02", "n01_call_analysis", "n03_wp_design", "phase_01_gate"),
        ],
    )


# ===========================================================================
# Scenario 1: Linear all-pass run
# ===========================================================================


class TestLinearAllPass:
    """
    4-node linear chain with entry gate on n01; all gates pass.

    Verifies: dispatch order, overall_status==pass, terminal node reached,
    run_summary.json artifact, gate_results_index canonical paths.
    """

    RUN_ID = "linear-pass-run"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _linear_manifest(), self.RUN_ID)

    # --- overall_status ---

    def test_overall_status_is_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.overall_status == "pass"

    # --- dispatch order ---

    def test_nodes_dispatched_in_dependency_order(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.dispatched_nodes == [
            "n01_call_analysis",
            "n02_concept_refinement",
            "n03_wp_design",
            "n04_gantt_milestones",
        ]

    def test_all_four_nodes_dispatched(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert len(summary.dispatched_nodes) == 4

    # --- terminal node ---

    def test_terminal_node_reached(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.terminal_nodes_reached == ["n04_gantt_milestones"]

    # --- no failures ---

    def test_no_stalled_nodes(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.stalled_nodes == []

    def test_no_hard_blocked_nodes(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.hard_blocked_nodes == []

    def test_all_nodes_released(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        for node_id, state in summary.node_states.items():
            assert state == "released", f"{node_id} has state {state!r}, expected 'released'"

    # --- run_summary.json ---

    def test_run_summary_json_written(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            sched.run()
        assert _run_summary_exists(tmp_path, self.RUN_ID)

    def test_run_summary_json_overall_status(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["overall_status"] == "pass"

    def test_run_summary_json_matches_returned_summary(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["overall_status"] == summary.overall_status
        assert on_disk["terminal_nodes_reached"] == summary.terminal_nodes_reached
        assert on_disk["node_states"] == dict(summary.node_states)
        assert on_disk["run_id"] == self.RUN_ID

    # --- gate_results_index ---

    def test_gate_results_index_contains_all_evaluated_gates(
        self, tmp_path: Path
    ) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        idx = summary.gate_results_index
        expected_gates = [
            "gate_01_source_integrity",  # entry gate for n01
            "phase_01_gate",             # exit gate for n01
            "phase_02_gate",             # exit gate for n02
            "phase_03_gate",             # exit gate for n03
            "phase_04_gate",             # exit gate for n04
        ]
        for gate_id in expected_gates:
            assert gate_id in idx, f"gate {gate_id!r} missing from gate_results_index"

    def test_gate_results_index_uses_canonical_tier4_paths(
        self, tmp_path: Path
    ) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        for gate_id, path in summary.gate_results_index.items():
            assert path.startswith("docs/tier4_orchestration_state/"), (
                f"Non-canonical path for gate {gate_id!r}: {path!r}"
            )

    def test_gate_results_index_no_duplicates(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        keys = list(summary.gate_results_index.keys())
        assert len(keys) == len(set(keys)), "gate_results_index must not have duplicate keys"


# ===========================================================================
# Scenario 2: Parallel-path (fork-join)
# ===========================================================================


class TestParallelPath:
    """
    n01 forks to n04 and n05; both join at n06 (terminal).

    Verifies: both branches dispatched after n01; registry order within
    same ready batch; n06 not dispatched until both branches release;
    overall_status==pass.
    """

    RUN_ID = "parallel-path-run"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _parallel_path_manifest(), self.RUN_ID)

    # --- overall_status ---

    def test_overall_status_is_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.overall_status == "pass"

    # --- dispatch ordering ---

    def test_both_branches_dispatched_after_n01(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        dispatched = summary.dispatched_nodes
        n01_idx = dispatched.index("n01_call_analysis")
        n04_idx = dispatched.index("n04_gantt_milestones")
        n05_idx = dispatched.index("n05_impact_architecture")
        assert n01_idx < n04_idx, "n04 must dispatch after n01"
        assert n01_idx < n05_idx, "n05 must dispatch after n01"

    def test_registry_order_respected_within_same_ready_batch(
        self, tmp_path: Path
    ) -> None:
        """
        n04 and n05 become ready in the same dispatch iteration.
        n04 appears before n05 in node_registry, so it must dispatch first.
        """
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        dispatched = summary.dispatched_nodes
        n04_idx = dispatched.index("n04_gantt_milestones")
        n05_idx = dispatched.index("n05_impact_architecture")
        assert n04_idx < n05_idx, "n04 must dispatch before n05 (registry order)"

    def test_join_node_dispatched_after_both_branches_released(
        self, tmp_path: Path
    ) -> None:
        """
        n06 requires both n04 and n05 released.
        It must appear in dispatched_nodes after both branch nodes.
        """
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        dispatched = summary.dispatched_nodes
        n04_idx = dispatched.index("n04_gantt_milestones")
        n05_idx = dispatched.index("n05_impact_architecture")
        n06_idx = dispatched.index("n06_implementation_architecture")
        assert n06_idx > n04_idx, "n06 must dispatch after n04"
        assert n06_idx > n05_idx, "n06 must dispatch after n05"

    def test_all_four_nodes_dispatched(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert len(summary.dispatched_nodes) == 4

    # --- terminal ---

    def test_join_node_is_terminal_node_reached(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert "n06_implementation_architecture" in summary.terminal_nodes_reached

    # --- no failures ---

    def test_no_stalled_or_hard_blocked_nodes(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.stalled_nodes == []
        assert summary.hard_blocked_nodes == []

    # --- artifact ---

    def test_run_summary_json_written_with_pass_status(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["overall_status"] == "pass"
        assert "n06_implementation_architecture" in on_disk["terminal_nodes_reached"]


# ===========================================================================
# Scenario 3: Early gate failure causing downstream stall
# ===========================================================================


class TestEarlyFailStall:
    """
    n02 exit gate fails; n03 and n04 can never become ready.
    RunAbortedError raised; run_summary.json written before exception.
    """

    RUN_ID = "early-fail-run"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _early_fail_manifest(), self.RUN_ID)

    # --- abort raised ---

    def test_run_aborted_error_raised(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError):
                sched.run()

    def test_exception_carries_summary(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        assert isinstance(exc_info.value.summary, RunSummary)

    # --- overall_status ---

    def test_summary_overall_status_aborted(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        assert exc_info.value.summary.overall_status == "aborted"

    # --- stalled nodes identification ---

    def test_stalled_nodes_includes_n03_and_n04(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        stalled_ids = [e["node_id"] for e in exc_info.value.summary.stalled_nodes]
        assert "n03_wp_design" in stalled_ids
        assert "n04_gantt_milestones" in stalled_ids

    def test_n01_released_n02_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        states = exc_info.value.summary.node_states
        assert states["n01_call_analysis"] == "released"
        assert states["n02_concept_refinement"] == "blocked_at_exit"

    def test_n03_stall_unsatisfied_condition_points_to_n02(
        self, tmp_path: Path
    ) -> None:
        """
        n03 stall entry must report the immediate upstream source (n02,
        blocked_at_exit) as the unsatisfied condition.
        """
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        stalled_by_id = {
            e["node_id"]: e for e in exc_info.value.summary.stalled_nodes
        }
        n03_entry = stalled_by_id["n03_wp_design"]
        conditions = n03_entry["unsatisfied_conditions"]
        assert len(conditions) == 1
        assert conditions[0]["gate_id"] == "phase_02_gate"
        assert conditions[0]["source_node_id"] == "n02_concept_refinement"
        assert conditions[0]["source_node_state"] == "blocked_at_exit"

    def test_n04_stall_unsatisfied_condition_points_to_n03_pending(
        self, tmp_path: Path
    ) -> None:
        """
        n04 stall entry must report n03 (pending, cascading stall) as
        the unsatisfied condition.
        """
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        stalled_by_id = {
            e["node_id"]: e for e in exc_info.value.summary.stalled_nodes
        }
        n04_entry = stalled_by_id["n04_gantt_milestones"]
        conditions = n04_entry["unsatisfied_conditions"]
        assert len(conditions) == 1
        assert conditions[0]["gate_id"] == "phase_03_gate"
        assert conditions[0]["source_node_id"] == "n03_wp_design"
        assert conditions[0]["source_node_state"] == "pending"

    # --- run_summary.json written before exception ---

    def test_run_summary_json_exists_before_exception_observed(
        self, tmp_path: Path
    ) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError):
                sched.run()
        assert _run_summary_exists(tmp_path, self.RUN_ID), (
            "run_summary.json must be written before RunAbortedError propagates"
        )

    def test_run_summary_json_overall_status_aborted(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError):
                sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["overall_status"] == "aborted"

    def test_run_summary_json_stalled_ids_match_exception(
        self, tmp_path: Path
    ) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        disk_stalled_ids = [e["node_id"] for e in on_disk["stalled_nodes"]]
        exc_stalled_ids = [
            e["node_id"] for e in exc_info.value.summary.stalled_nodes
        ]
        assert sorted(disk_stalled_ids) == sorted(exc_stalled_ids)

    # --- backward-compat .result dict ---

    def test_exception_result_dict_is_consistent_with_summary(
        self, tmp_path: Path
    ) -> None:
        """exc.result must equal exc.summary.to_dict() (backward-compat contract)."""
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_02_gate")):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        exc = exc_info.value
        assert exc.result == exc.summary.to_dict()
        assert exc.result["overall_status"] == "aborted"


# ===========================================================================
# Scenario 4: HARD_BLOCK scenario (gate_09 failure)
# ===========================================================================


class TestHardBlock:
    """
    gate_09_budget_consistency fails on n07_budget_gate.
    All Phase 8 nodes must be frozen as hard_block_upstream.
    No pending nodes remain, so RunAbortedError is NOT raised.
    """

    RUN_ID = "hard-block-run"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _hard_block_manifest(), self.RUN_ID)

    # --- no abort ---

    def test_run_returns_normally_without_raising(self, tmp_path: Path) -> None:
        """
        gate_09 failure freezes all Phase 8 nodes (hard_block_upstream).
        No pending nodes remain → no RunAbortedError.
        """
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        assert summary is not None

    # --- overall_status ---

    def test_overall_status_is_fail(self, tmp_path: Path) -> None:
        """
        n08d is the only terminal node; it is hard_blocked (not released).
        No terminal reached → overall_status == 'fail'.
        """
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        assert summary.overall_status == "fail"

    def test_no_terminal_nodes_reached(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        assert summary.terminal_nodes_reached == []

    # --- Phase 8 node states ---

    def test_all_phase8_nodes_are_hard_block_upstream(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        for node_id in PHASE_8_NODE_IDS:
            assert summary.node_states.get(node_id) == "hard_block_upstream", (
                f"{node_id} expected 'hard_block_upstream', "
                f"got {summary.node_states.get(node_id)!r}"
            )

    def test_all_phase8_nodes_in_hard_blocked_nodes_list(
        self, tmp_path: Path
    ) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        for node_id in PHASE_8_NODE_IDS:
            assert node_id in summary.hard_blocked_nodes, (
                f"{node_id} missing from hard_blocked_nodes"
            )

    def test_phase8_nodes_not_dispatched(self, tmp_path: Path) -> None:
        """Hard-blocked nodes must never be dispatched."""
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        for node_id in PHASE_8_NODE_IDS:
            assert node_id not in summary.dispatched_nodes, (
                f"{node_id} must not appear in dispatched_nodes"
            )

    def test_phase8_nodes_not_duplicated_as_stalled(self, tmp_path: Path) -> None:
        """
        Hard-blocked nodes are settled (not pending) and must not appear
        in stalled_nodes.  No double-counting between the two lists.
        """
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        stalled_ids = {e["node_id"] for e in summary.stalled_nodes}
        for node_id in PHASE_8_NODE_IDS:
            assert node_id not in stalled_ids, (
                f"{node_id} must not appear in stalled_nodes (is hard_block_upstream)"
            )

    def test_stalled_nodes_empty(self, tmp_path: Path) -> None:
        """After gate_09 failure all nodes are settled; no pending nodes remain."""
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        assert summary.stalled_nodes == []

    def test_n07_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        assert summary.node_states["n07_budget_gate"] == "blocked_at_exit"

    # --- artifact ---

    def test_run_summary_json_written(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            sched.run()
        assert _run_summary_exists(tmp_path, self.RUN_ID)

    def test_run_summary_json_hard_blocked_nodes(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["overall_status"] == "fail"
        assert set(on_disk["hard_blocked_nodes"]) == PHASE_8_NODE_IDS

    # --- gate_results_index ---

    def test_gate09_in_gate_results_index(self, tmp_path: Path) -> None:
        """gate_09 was evaluated (and failed); it must appear in the index."""
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        assert "gate_09_budget_consistency" in summary.gate_results_index

    def test_gate_results_index_canonical_paths(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET, side_effect=_gate_pass_except("gate_09_budget_consistency")
        ):
            summary = sched.run()
        for gate_id, path in summary.gate_results_index.items():
            assert path.startswith("docs/tier4_orchestration_state/"), (
                f"Non-canonical path for {gate_id!r}: {path!r}"
            )


# ===========================================================================
# Scenario 5: Partial-pass scenario
# ===========================================================================


class TestPartialPass:
    """
    n01 forks to two terminal nodes:
        n02 (passes, terminal) and n03 (fails, terminal).

    Both settle without pending nodes remaining → no RunAbortedError.
    Expected: overall_status == 'partial_pass'.
    """

    RUN_ID = "partial-pass-run"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _partial_pass_manifest(), self.RUN_ID)

    # --- no abort ---

    def test_run_does_not_raise(self, tmp_path: Path) -> None:
        """
        n02 released, n03 blocked_at_exit — both settled, no pending nodes.
        RunAbortedError must not be raised.
        """
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        assert summary is not None

    # --- overall_status ---

    def test_overall_status_is_partial_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        assert summary.overall_status == "partial_pass"

    # --- terminal nodes ---

    def test_n02_in_terminal_nodes_reached(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        assert "n02_concept_refinement" in summary.terminal_nodes_reached

    def test_n03_not_in_terminal_nodes_reached(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        assert "n03_wp_design" not in summary.terminal_nodes_reached

    def test_only_one_terminal_node_reached(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        assert len(summary.terminal_nodes_reached) == 1

    # --- node states ---

    def test_node_states_correct(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        assert summary.node_states["n01_call_analysis"] == "released"
        assert summary.node_states["n02_concept_refinement"] == "released"
        assert summary.node_states["n03_wp_design"] == "blocked_at_exit"

    # --- no stall ---

    def test_no_stalled_nodes(self, tmp_path: Path) -> None:
        """Both n02 and n03 are settled after the run; none remain pending."""
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        assert summary.stalled_nodes == []

    def test_no_hard_blocked_nodes(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        assert summary.hard_blocked_nodes == []

    # --- artifact ---

    def test_run_summary_json_partial_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["overall_status"] == "partial_pass"
        assert "n02_concept_refinement" in on_disk["terminal_nodes_reached"]
        assert "n03_wp_design" not in on_disk["terminal_nodes_reached"]

    # --- gate_results_index ---

    def test_gate_results_index_includes_failed_gate(self, tmp_path: Path) -> None:
        """phase_03_gate was evaluated (and failed); it must appear in the index."""
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")):
            summary = sched.run()
        idx = summary.gate_results_index
        for gate_id in ["phase_01_gate", "phase_02_gate", "phase_03_gate"]:
            assert gate_id in idx, f"{gate_id!r} missing from gate_results_index"
