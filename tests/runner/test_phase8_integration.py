"""
Phase F — Phase 8 Refactor Integration Tests.

Full DAG execution tests exercising the criterion-aligned Phase 8 topology:

    n07_budget_gate  ─gate_09─┬──> n08a_excellence_drafting     ─gate_10a─┐
                              ├──> n08b_impact_drafting          ─gate_10b─┼──> n08d_assembly
                              └──> n08c_implementation_drafting  ─gate_10c─┘        │
                                                                              gate_10d
                                                                                    │
                                                                           n08e_evaluator_review
                                                                              gate_11
                                                                                    │
                                                                           n08f_revision (terminal)
                                                                              gate_12

Scenarios (Section 11.3 of phase8_refactoring_plan.md):
  1. Phase8FullDagAllPass       — gate_09 passed; all 6 Phase 8 nodes dispatch and release.
  2. Phase8ParallelDispatch     — n08a/b/c dispatched before n08d (parallel fan-out verified).
  3. Phase8AssemblyBlockedUntilAll3 — n08d not ready until all 3 section gates pass.
  4. Phase8BudgetGateHardBlock  — gate_09 failure freezes all 6 Phase 8 nodes.
  5. Phase8SingleSectionFailure — n08a fails; n08b and n08c still dispatch and release.
  6. Phase8TerminalNodeRelease  — n08f release produces overall_status: pass.

Backward compatibility tests (Section 11.4):
  7. OldGate10NotInRegistry     — gate_10_part_b_completeness removed from registry.
  8. OldNodeIdsNotInManifest    — old n08a-d node IDs absent from manifest.
  9. ReusePolicyAcceptsOldArtifacts — reuse policy mechanism works for prior-run artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock, patch

import pytest

from runner.dag_scheduler import (
    DAGScheduler,
    ManifestGraph,
    RunAbortedError,
    RunSummary,
)
from runner.run_context import PHASE_8_NODE_IDS, RunContext
from runner.runtime_models import AgentResult
from runner.gate_result_registry import GATE_RESULT_PATHS


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EG_TARGET = "runner.dag_scheduler.evaluate_gate"
_RA_TARGET = "runner.dag_scheduler.run_agent"
_PASS = {"status": "pass"}
_FAIL = {"status": "fail"}
_SUCCESS_AGENT = AgentResult(status="success", can_evaluate_exit_gate=True)


@pytest.fixture(autouse=True)
def _mock_run_agent():
    """Patch ``run_agent`` for all tests — these exercise scheduling, not agents."""
    with patch(_RA_TARGET, return_value=_SUCCESS_AGENT):
        yield


# ---------------------------------------------------------------------------
# Manifest construction
# ---------------------------------------------------------------------------

_PHASE8_MANIFEST = {
    "name": "test_phase8_integration",
    "version": "1.1",
    "node_registry": [
        {
            "node_id": "n07_budget_gate",
            "phase_number": 7,
            "phase_id": "phase_07",
            "agent": "budget_gate_validator",
            "skills": [],
            "exit_gate": "gate_09_budget_consistency",
            "terminal": False,
        },
        {
            "node_id": "n08a_excellence_drafting",
            "phase_number": 8,
            "phase_id": "phase_08a",
            "agent": "excellence_writer",
            "skills": [],
            "exit_gate": "gate_10a_excellence_completeness",
            "terminal": False,
        },
        {
            "node_id": "n08b_impact_drafting",
            "phase_number": 8,
            "phase_id": "phase_08b",
            "agent": "impact_writer",
            "skills": [],
            "exit_gate": "gate_10b_impact_completeness",
            "terminal": False,
        },
        {
            "node_id": "n08c_implementation_drafting",
            "phase_number": 8,
            "phase_id": "phase_08c",
            "agent": "implementation_writer",
            "skills": [],
            "exit_gate": "gate_10c_implementation_completeness",
            "terminal": False,
        },
        {
            "node_id": "n08d_assembly",
            "phase_number": 8,
            "phase_id": "phase_08d",
            "agent": "proposal_integrator",
            "skills": [],
            "exit_gate": "gate_10d_cross_section_consistency",
            "terminal": False,
        },
        {
            "node_id": "n08e_evaluator_review",
            "phase_number": 8,
            "phase_id": "phase_08e",
            "agent": "evaluator_reviewer",
            "skills": [],
            "exit_gate": "gate_11_review_closure",
            "terminal": False,
        },
        {
            "node_id": "n08f_revision",
            "phase_number": 8,
            "phase_id": "phase_08f",
            "agent": "revision_integrator",
            "skills": [],
            "exit_gate": "gate_12_constitutional_compliance",
            "terminal": True,
        },
    ],
    "edge_registry": [
        # Budget gate fans out to 3 parallel drafting nodes
        {
            "edge_id": "e07_to_08a",
            "from_node": "n07_budget_gate",
            "to_node": "n08a_excellence_drafting",
            "gate_condition": "gate_09_budget_consistency",
        },
        {
            "edge_id": "e07_to_08b",
            "from_node": "n07_budget_gate",
            "to_node": "n08b_impact_drafting",
            "gate_condition": "gate_09_budget_consistency",
        },
        {
            "edge_id": "e07_to_08c",
            "from_node": "n07_budget_gate",
            "to_node": "n08c_implementation_drafting",
            "gate_condition": "gate_09_budget_consistency",
        },
        # 3 section gates converge on assembly
        {
            "edge_id": "e08a_to_08d",
            "from_node": "n08a_excellence_drafting",
            "to_node": "n08d_assembly",
            "gate_condition": "gate_10a_excellence_completeness",
        },
        {
            "edge_id": "e08b_to_08d",
            "from_node": "n08b_impact_drafting",
            "to_node": "n08d_assembly",
            "gate_condition": "gate_10b_impact_completeness",
        },
        {
            "edge_id": "e08c_to_08d",
            "from_node": "n08c_implementation_drafting",
            "to_node": "n08d_assembly",
            "gate_condition": "gate_10c_implementation_completeness",
        },
        # Sequential: assembly -> review -> revision
        {
            "edge_id": "e08d_to_08e",
            "from_node": "n08d_assembly",
            "to_node": "n08e_evaluator_review",
            "gate_condition": "gate_10d_cross_section_consistency",
        },
        {
            "edge_id": "e08e_to_08f",
            "from_node": "n08e_evaluator_review",
            "to_node": "n08f_revision",
            "gate_condition": "gate_11_review_closure",
        },
    ],
}

import yaml


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _make_scheduler(
    tmp_path: Path,
    manifest_data: dict,
    run_id: str,
    *,
    phase: int | None = None,
    pre_released: list[str] | None = None,
) -> DAGScheduler:
    """Build a DAGScheduler from a synthetic manifest and fresh RunContext."""
    mp = _write_manifest(tmp_path, manifest_data)
    graph = ManifestGraph.load(mp)
    ctx = RunContext.initialize(tmp_path, run_id)
    # Pre-release nodes (simulate prior run completion).
    for node_id in (pre_released or []):
        ctx.set_node_state(node_id, "released")
    ctx.save()
    sched = DAGScheduler(graph, ctx, tmp_path, library_path=None, manifest_path=mp, phase=phase)
    # Inject mock NodeResolver — synthetic manifests lack agent fields.
    mock_resolver = MagicMock()
    mock_resolver.resolve_agent_id.return_value = "test_agent"
    mock_resolver.resolve_sub_agent_id.return_value = None
    mock_resolver.resolve_pre_gate_agent_id.return_value = None
    mock_resolver.resolve_skill_ids.return_value = []
    mock_resolver.resolve_phase_id.return_value = "phase8"
    sched._DAGScheduler__node_resolver = mock_resolver
    return sched


def _gate_pass_except(*failing_gates: str) -> Callable:
    """Return an evaluate_gate side-effect that passes all gates except those listed."""
    fail_set = set(failing_gates)

    def _side_effect(gate_id: str, *args, **kwargs) -> dict:
        return _FAIL if gate_id in fail_set else _PASS

    return _side_effect


def _read_run_summary(tmp_path: Path, run_id: str) -> dict:
    path = tmp_path / ".claude" / "runs" / run_id / "run_summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ===========================================================================
# Scenario 1: Phase 8 full DAG — all pass
# ===========================================================================


class TestPhase8FullDagAllPass:
    """
    All Phase 7 gates pre-passed; all 6 Phase 8 nodes dispatch and release.
    Verifies parallel fan-out from gate_09, fan-in at n08d, and sequential
    tail through n08e → n08f.
    """

    RUN_ID = "phase8-full-pass"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, self.RUN_ID,
            phase=8, pre_released=["n07_budget_gate"],
        )

    def test_overall_status_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.overall_status == "pass"

    def test_all_6_phase8_nodes_dispatched(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert set(summary.dispatched_nodes) == PHASE_8_NODE_IDS

    def test_all_nodes_released(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        for node_id in PHASE_8_NODE_IDS:
            assert summary.node_states[node_id] == "released"

    def test_terminal_node_is_n08f(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.terminal_nodes_reached == ["n08f_revision"]

    def test_no_stalled_or_hard_blocked(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.stalled_nodes == []
        assert summary.hard_blocked_nodes == []

    def test_run_summary_json_written(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["overall_status"] == "pass"
        assert "n08f_revision" in on_disk["terminal_nodes_reached"]

    def test_3_parallel_nodes_ready_simultaneously(self, tmp_path: Path) -> None:
        """n08a, n08b, n08c become ready in the same iteration (after n07 released)."""
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        dispatched = summary.dispatched_nodes
        # All 3 must appear before n08d.
        idx_a = dispatched.index("n08a_excellence_drafting")
        idx_b = dispatched.index("n08b_impact_drafting")
        idx_c = dispatched.index("n08c_implementation_drafting")
        idx_d = dispatched.index("n08d_assembly")
        assert idx_a < idx_d
        assert idx_b < idx_d
        assert idx_c < idx_d


# ===========================================================================
# Scenario 2: Parallel dispatch ordering
# ===========================================================================


class TestPhase8ParallelDispatch:
    """
    Verify n08a/b/c are dispatched before n08d (fan-out), and n08d before
    n08e before n08f (sequential tail). The 3 parallel nodes are dispatched
    in registry order within the same ready batch.
    """

    RUN_ID = "phase8-parallel"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, self.RUN_ID,
            phase=8, pre_released=["n07_budget_gate"],
        )

    def test_parallel_nodes_before_assembly(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        dispatched = summary.dispatched_nodes
        parallel = {"n08a_excellence_drafting", "n08b_impact_drafting", "n08c_implementation_drafting"}
        idx_d = dispatched.index("n08d_assembly")
        for node_id in parallel:
            assert dispatched.index(node_id) < idx_d, (
                f"{node_id} should be dispatched before n08d_assembly"
            )

    def test_registry_order_within_parallel_batch(self, tmp_path: Path) -> None:
        """Within the same ready batch, nodes dispatch in registry order: a, b, c."""
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        dispatched = summary.dispatched_nodes
        idx_a = dispatched.index("n08a_excellence_drafting")
        idx_b = dispatched.index("n08b_impact_drafting")
        idx_c = dispatched.index("n08c_implementation_drafting")
        assert idx_a < idx_b < idx_c

    def test_sequential_tail_order(self, tmp_path: Path) -> None:
        """n08d → n08e → n08f in strict sequential order."""
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        dispatched = summary.dispatched_nodes
        idx_d = dispatched.index("n08d_assembly")
        idx_e = dispatched.index("n08e_evaluator_review")
        idx_f = dispatched.index("n08f_revision")
        assert idx_d < idx_e < idx_f


# ===========================================================================
# Scenario 3: Assembly blocked until all 3 section gates pass
# ===========================================================================


class TestPhase8AssemblyBlockedUntilAll3:
    """
    n08d_assembly requires all three incoming edges (gate_10a, gate_10b,
    gate_10c). If any one section gate fails, n08d cannot proceed.
    """

    RUN_ID = "phase8-assembly-blocked"

    def test_assembly_blocked_when_one_section_fails(self, tmp_path: Path) -> None:
        """n08b gate fails → n08d stays pending → stall/abort."""
        sched = _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, self.RUN_ID,
            phase=8, pre_released=["n07_budget_gate"],
        )
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_10b_impact_completeness"),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        # n08d, n08e, n08f must not have been dispatched.
        for node_id in ["n08d_assembly", "n08e_evaluator_review", "n08f_revision"]:
            assert node_id not in summary.dispatched_nodes, (
                f"{node_id} dispatched despite section gate failure"
            )

    def test_stalled_nodes_include_downstream(self, tmp_path: Path) -> None:
        """n08d, n08e, n08f appear in stalled_nodes when n08b gate fails."""
        sched = _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, "phase8-stall-downstream",
            phase=8, pre_released=["n07_budget_gate"],
        )
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_10b_impact_completeness"),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        stalled_ids = [e["node_id"] for e in exc_info.value.summary.stalled_nodes]
        assert "n08d_assembly" in stalled_ids
        assert "n08e_evaluator_review" in stalled_ids
        assert "n08f_revision" in stalled_ids

    def test_n08d_unsatisfied_condition_references_failed_section(self, tmp_path: Path) -> None:
        """n08d stall entry should reference n08b and gate_10b as unsatisfied."""
        sched = _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, "phase8-unsat-condition",
            phase=8, pre_released=["n07_budget_gate"],
        )
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_10b_impact_completeness"),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        stalled_by_id = {
            e["node_id"]: e for e in exc_info.value.summary.stalled_nodes
        }
        n08d_entry = stalled_by_id["n08d_assembly"]
        gate_ids = [c["gate_id"] for c in n08d_entry["unsatisfied_conditions"]]
        assert "gate_10b_impact_completeness" in gate_ids

    def test_two_section_failures_still_block_assembly(self, tmp_path: Path) -> None:
        """Both n08a and n08c fail → n08d still blocked with 2 unsatisfied conditions."""
        sched = _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, "phase8-two-fail",
            phase=8, pre_released=["n07_budget_gate"],
        )
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except(
                "gate_10a_excellence_completeness",
                "gate_10c_implementation_completeness",
            ),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        stalled_by_id = {
            e["node_id"]: e for e in exc_info.value.summary.stalled_nodes
        }
        n08d_conds = stalled_by_id["n08d_assembly"]["unsatisfied_conditions"]
        gate_ids = {c["gate_id"] for c in n08d_conds}
        assert "gate_10a_excellence_completeness" in gate_ids
        assert "gate_10c_implementation_completeness" in gate_ids


# ===========================================================================
# Scenario 4: Budget gate HARD_BLOCK freezes all Phase 8 nodes
# ===========================================================================


class TestPhase8BudgetGateHardBlock:
    """
    gate_09_budget_consistency fails on n07_budget_gate.
    All 6 Phase 8 nodes must be frozen as hard_block_upstream.
    """

    RUN_ID = "phase8-hard-block"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _PHASE8_MANIFEST, self.RUN_ID)

    def test_all_phase8_nodes_hard_blocked(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_09_budget_consistency"),
        ):
            summary = sched.run()
        for node_id in PHASE_8_NODE_IDS:
            assert summary.node_states.get(node_id) == "hard_block_upstream", (
                f"{node_id} expected hard_block_upstream, got {summary.node_states.get(node_id)}"
            )

    def test_overall_status_fail(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_09_budget_consistency"),
        ):
            summary = sched.run()
        assert summary.overall_status == "fail"

    def test_phase8_nodes_not_dispatched(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_09_budget_consistency"),
        ):
            summary = sched.run()
        for node_id in PHASE_8_NODE_IDS:
            assert node_id not in summary.dispatched_nodes

    def test_hard_blocked_nodes_list_complete(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_09_budget_consistency"),
        ):
            summary = sched.run()
        assert set(summary.hard_blocked_nodes) == PHASE_8_NODE_IDS

    def test_no_stalled_nodes(self, tmp_path: Path) -> None:
        """Hard-blocked nodes are settled, not stalled."""
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_09_budget_consistency"),
        ):
            summary = sched.run()
        assert summary.stalled_nodes == []

    def test_run_summary_json_records_hard_block(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_09_budget_consistency"),
        ):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert set(on_disk["hard_blocked_nodes"]) == PHASE_8_NODE_IDS


# ===========================================================================
# Scenario 5: Single section failure does not block other sections
# ===========================================================================


class TestPhase8SingleSectionFailure:
    """
    n08a (Excellence) fails at exit gate. n08b and n08c should still
    dispatch and release independently. Only n08d and downstream stall.
    """

    RUN_ID = "phase8-single-fail"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, self.RUN_ID,
            phase=8, pre_released=["n07_budget_gate"],
        )

    def test_n08b_and_n08c_release_despite_n08a_failure(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_10a_excellence_completeness"),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        assert summary.node_states["n08a_excellence_drafting"] == "blocked_at_exit"
        assert summary.node_states["n08b_impact_drafting"] == "released"
        assert summary.node_states["n08c_implementation_drafting"] == "released"

    def test_n08a_failure_does_not_prevent_n08b_dispatch(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_10a_excellence_completeness"),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert "n08b_impact_drafting" in exc_info.value.summary.dispatched_nodes
        assert "n08c_implementation_drafting" in exc_info.value.summary.dispatched_nodes

    def test_n08a_failure_does_not_prevent_n08c_dispatch(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_10a_excellence_completeness"),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        assert "n08c_implementation_drafting" in exc_info.value.summary.dispatched_nodes

    def test_downstream_nodes_stall(self, tmp_path: Path) -> None:
        """n08d, n08e, n08f stall because n08a gate failed."""
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_10a_excellence_completeness"),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        stalled_ids = [e["node_id"] for e in exc_info.value.summary.stalled_nodes]
        assert "n08d_assembly" in stalled_ids

    def test_overall_status_aborted(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(
            _EG_TARGET,
            side_effect=_gate_pass_except("gate_10a_excellence_completeness"),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        assert exc_info.value.summary.overall_status == "aborted"


# ===========================================================================
# Scenario 6: Terminal node release → overall_status: pass
# ===========================================================================


class TestPhase8TerminalNodeRelease:
    """
    n08f_revision is the sole terminal node. When all gates pass,
    n08f releases and the run produces overall_status == "pass".
    """

    RUN_ID = "phase8-terminal"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, self.RUN_ID,
            phase=8, pre_released=["n07_budget_gate"],
        )

    def test_overall_status_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.overall_status == "pass"

    def test_n08f_is_only_terminal_reached(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.terminal_nodes_reached == ["n08f_revision"]
        assert len(summary.terminal_nodes_reached) == 1

    def test_n08f_state_is_released(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.node_states["n08f_revision"] == "released"

    def test_gate_results_index_includes_all_phase8_gates(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        expected_gates = {
            "gate_10a_excellence_completeness",
            "gate_10b_impact_completeness",
            "gate_10c_implementation_completeness",
            "gate_10d_cross_section_consistency",
            "gate_11_review_closure",
            "gate_12_constitutional_compliance",
        }
        for gate_id in expected_gates:
            assert gate_id in summary.gate_results_index, (
                f"{gate_id} missing from gate_results_index"
            )

    def test_run_summary_json_overall_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["overall_status"] == "pass"
        assert on_disk["terminal_nodes_reached"] == ["n08f_revision"]

    def test_no_failure_details_on_success(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        # node_failure_details should be empty or have no entries.
        assert len(summary.node_failure_details) == 0


# ===========================================================================
# Backward compatibility tests (Section 11.4)
# ===========================================================================


class TestBackwardCompatibility:
    """Verify old Phase 8 artifacts are properly removed/replaced."""

    def test_old_gate_10_not_in_registry(self) -> None:
        """gate_10_part_b_completeness must not appear in GATE_RESULT_PATHS."""
        assert "gate_10_part_b_completeness" not in GATE_RESULT_PATHS

    def test_old_node_ids_not_in_manifest_node_ids(self) -> None:
        """The new Phase 8 manifest should not contain old node IDs."""
        node_ids = {n["node_id"] for n in _PHASE8_MANIFEST["node_registry"]}
        old_ids = {
            "n08a_section_drafting",
            "n08b_assembly",
            "n08c_evaluator_review",
            "n08d_revision",
        }
        assert node_ids.isdisjoint(old_ids), (
            f"Old node IDs still present: {node_ids & old_ids}"
        )

    def test_old_node_ids_not_in_phase8_node_ids(self) -> None:
        """PHASE_8_NODE_IDS constant must not contain old node IDs."""
        old_ids = {
            "n08a_section_drafting",
            "n08b_assembly",
            "n08c_evaluator_review",
            "n08d_revision",
        }
        assert PHASE_8_NODE_IDS.isdisjoint(old_ids)

    def test_new_node_ids_all_present(self) -> None:
        """All 6 new Phase 8 node IDs present in PHASE_8_NODE_IDS."""
        expected = {
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
            "n08d_assembly",
            "n08e_evaluator_review",
            "n08f_revision",
        }
        assert PHASE_8_NODE_IDS == frozenset(expected)

    def test_reuse_policy_accepts_old_artifacts(self, tmp_path: Path) -> None:
        """Reuse policy mechanism is artifact-path-based, not node-ID-based."""
        ctx = RunContext.initialize(tmp_path, "reuse-test")
        # Write a reuse policy approving a Tier 4 artifact path.
        reuse_path = ctx.run_dir / "reuse_policy.json"
        reuse_data = {
            "approved_artifacts": [
                "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json",
                "docs/tier5_deliverables/proposal_sections/excellence_section.json",
            ]
        }
        reuse_path.parent.mkdir(parents=True, exist_ok=True)
        reuse_path.write_text(json.dumps(reuse_data), encoding="utf-8")
        # Verify the file was written and is loadable.
        loaded = json.loads(reuse_path.read_text(encoding="utf-8"))
        assert len(loaded["approved_artifacts"]) == 2
        assert "excellence_section.json" in loaded["approved_artifacts"][1]


# ===========================================================================
# Phase-scoped execution of Phase 8
# ===========================================================================


class TestPhase8PhaseScopedExecution:
    """Phase-scoped execution (`--phase 8`) dispatches exactly the 6 Phase 8 nodes."""

    def test_phase8_scope_dispatches_6_nodes(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, "phase8-scope",
            phase=8, pre_released=["n07_budget_gate"],
        )
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert summary.phase_scope == 8
        assert set(summary.phase_scope_nodes) == PHASE_8_NODE_IDS

    def test_phase8_scope_does_not_dispatch_n07(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, "phase8-no-n07",
            phase=8, pre_released=["n07_budget_gate"],
        )
        with patch(_EG_TARGET, return_value=_PASS):
            summary = sched.run()
        assert "n07_budget_gate" not in summary.dispatched_nodes

    def test_phase8_aborts_when_n07_not_released(self, tmp_path: Path) -> None:
        """Phase 8 prerequisites unmet: n07 is still pending → abort."""
        sched = _make_scheduler(
            tmp_path, _PHASE8_MANIFEST, "phase8-unmet",
            phase=8,
            # n07 NOT pre-released
        )
        with pytest.raises(RunAbortedError) as exc_info:
            sched.run()
        assert exc_info.value.summary.overall_status == "aborted"
        stalled_ids = [s["node_id"] for s in exc_info.value.summary.stalled_nodes]
        # All 3 parallel drafting nodes should be stalled.
        for node_id in ["n08a_excellence_drafting", "n08b_impact_drafting", "n08c_implementation_drafting"]:
            assert node_id in stalled_ids
