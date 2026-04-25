"""
Step 9 — End-to-End Vertical Slice Scenarios.

Integration tests that exercise the complete runtime stack:
scheduler → agent runtime → skill runtime → canonical writes →
gate evaluation → node release/blocking.

Each scenario tests the full dispatch cycle including ``_dispatch_node()``'s
5-step contract (§9.2): set running → entry gate → agent body → exit gate →
return ``NodeExecutionResult``.  ``run_agent`` and ``evaluate_gate`` are
mocked to control outcomes; the scheduler, ``RunContext``, ``ManifestGraph``,
``RunSummary``, and ``node_failure_details`` all execute with real code.

Scenarios
---------
1. LinearAllPass       — 13 nodes (n01→…→n08f), all pass.
2. AgentBodyFailN02    — n01 passes; n02 agent body fails; downstream stalls.
3. ExitGateFailN03     — n01, n02 pass; n03 exit gate fails; downstream stalls.
4. BudgetAgentFail     — n01–n06 pass; n07 agent body fails; Phase 8 HARD_BLOCK.
5. BudgetExitGateFail  — n01–n06 pass; n07 exit gate fails; Phase 8 HARD_BLOCK.
6. ConstitutionalHalt  — n01 passes; n02 CONSTITUTIONAL_HALT; downstream stalls.
7. Phase8MultiNode     — n08a + n08b + n08c dispatched as separate agent invocations.

Test philosophy
---------------
- Real ``DAGScheduler``, ``ManifestGraph``, ``RunContext``, ``RunSummary``.
- Synthetic manifest files written to ``tmp_path`` via YAML.
- ``evaluate_gate`` patched at ``runner.dag_scheduler.evaluate_gate``.
- ``run_agent`` patched at ``runner.dag_scheduler.run_agent``.
- Assertions cover: ``overall_status``, ``dispatched_nodes`` order,
  ``node_states``, ``node_failure_details`` (failure_origin,
  exit_gate_evaluated, failure_category), ``hard_blocked_nodes``,
  ``run_summary.json`` artifact presence and content.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock, patch

import pytest
import yaml

from runner.dag_scheduler import (
    DAGScheduler,
    ManifestGraph,
    RunAbortedError,
    RunSummary,
)
from runner.run_context import PHASE_8_NODE_IDS, RunContext
from runner.runtime_models import AgentResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EG_TARGET = "runner.dag_scheduler.evaluate_gate"
_RA_TARGET = "runner.dag_scheduler.run_agent"
_PASS = {"status": "pass"}
_FAIL = {"status": "fail", "reason": "gate failed"}


# ---------------------------------------------------------------------------
# AgentResult factories
# ---------------------------------------------------------------------------


def _agent_success() -> AgentResult:
    return AgentResult(status="success", can_evaluate_exit_gate=True)


def _agent_failure(
    reason: str = "agent body failed",
    category: str = "SKILL_FAILURE",
) -> AgentResult:
    return AgentResult(
        status="failure",
        can_evaluate_exit_gate=False,
        failure_reason=reason,
        failure_category=category,
    )


def _agent_constitutional_halt() -> AgentResult:
    return AgentResult(
        status="failure",
        can_evaluate_exit_gate=False,
        failure_reason="CONSTITUTIONAL_HALT from skill 'concept-alignment-check'",
        failure_category="CONSTITUTIONAL_HALT",
    )


# ---------------------------------------------------------------------------
# Manifest construction helpers
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _node(
    node_id: str,
    exit_gate: str,
    *,
    entry_gate: str | None = None,
    terminal: bool = False,
    agent: str | None = None,
) -> dict:
    entry: dict = {"node_id": node_id, "exit_gate": exit_gate, "terminal": terminal}
    if entry_gate:
        entry["entry_gate"] = entry_gate
    if agent:
        entry["agent"] = agent
    return entry


def _edge(edge_id: str, from_node: str, to_node: str, gate_condition: str) -> dict:
    return {
        "edge_id": edge_id,
        "from_node": from_node,
        "to_node": to_node,
        "gate_condition": gate_condition,
    }


def _manifest(name: str, nodes: list[dict], edges: list[dict]) -> dict:
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
    mp = _write_manifest(tmp_path, manifest_data)
    graph = ManifestGraph.load(mp)
    ctx = RunContext.initialize(tmp_path, run_id)
    sched = DAGScheduler(graph, ctx, tmp_path, library_path=None, manifest_path=mp)
    # Inject mock NodeResolver — synthetic manifests lack agent fields
    mock_resolver = MagicMock()
    mock_resolver.resolve_agent_id.return_value = "test_agent"
    mock_resolver.resolve_sub_agent_id.return_value = None
    mock_resolver.resolve_pre_gate_agent_id.return_value = None
    mock_resolver.resolve_skill_ids.return_value = []
    mock_resolver.resolve_phase_id.return_value = "phase1"
    sched._DAGScheduler__node_resolver = mock_resolver
    return sched


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _gate_pass_except(*failing_gates: str) -> Callable:
    """evaluate_gate side-effect: pass all except listed gates."""
    fail_set = set(failing_gates)

    def _side_effect(gate_id: str, *args, **kwargs) -> dict:
        return _FAIL if gate_id in fail_set else _PASS

    return _side_effect


def _agent_success_except(
    failing_nodes: dict[str, AgentResult],
) -> Callable:
    """run_agent side-effect: succeed for all nodes except those in *failing_nodes*.

    *failing_nodes* maps node_id → AgentResult to return when that node
    is dispatched.
    """

    def _side_effect(
        agent_id: str,
        node_id: str,
        run_id: str,
        repo_root,
        **kwargs,
    ) -> AgentResult:
        if node_id in failing_nodes:
            return failing_nodes[node_id]
        return _agent_success()

    return _side_effect


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------


def _read_run_summary(tmp_path: Path, run_id: str) -> dict:
    path = tmp_path / ".claude" / "runs" / run_id / "run_summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary_exists(tmp_path: Path, run_id: str) -> bool:
    path = tmp_path / ".claude" / "runs" / run_id / "run_summary.json"
    return path.exists()


# ---------------------------------------------------------------------------
# Scenario manifest definitions
# ---------------------------------------------------------------------------


def _full_manifest() -> dict:
    """
    Full 13-node DAG matching the production topology:
        n01 → n02 → n03 → n04 → n05 → n06 → n07 ──┬──→ n08a ──┐
                                                     ├──→ n08b ──┼──→ n08d → n08e → n08f
                                                     └──→ n08c ──┘

    n01 has entry gate gate_01_source_integrity.
    n07 exit gate is gate_09_budget_consistency (HARD_BLOCK trigger).
    n07 fans out to n08a, n08b, n08c (parallel drafting).
    n08a, n08b, n08c converge on n08d (assembly).
    n08d → n08e → n08f (sequential).
    n08f is the sole terminal node.
    """
    return _manifest(
        "test_full",
        nodes=[
            _node("n01_call_analysis", "phase_01_gate",
                  entry_gate="gate_01_source_integrity"),
            _node("n02_concept_refinement", "phase_02_gate"),
            _node("n03_wp_design", "phase_03_gate"),
            _node("n04_gantt_milestones", "phase_04_gate"),
            _node("n05_impact_architecture", "phase_05_gate"),
            _node("n06_implementation_architecture", "phase_06_gate"),
            _node("n07_budget_gate", "gate_09_budget_consistency"),
            _node("n08a_excellence_drafting", "gate_10a_excellence_completeness"),
            _node("n08b_impact_drafting", "gate_10b_impact_completeness"),
            _node("n08c_implementation_drafting", "gate_10c_implementation_completeness"),
            _node("n08d_assembly", "gate_10d_cross_section_consistency"),
            _node("n08e_evaluator_review", "gate_11_review_closure"),
            _node("n08f_revision", "gate_12_constitutional_compliance", terminal=True),
        ],
        edges=[
            _edge("e01", "n01_call_analysis", "n02_concept_refinement", "phase_01_gate"),
            _edge("e02", "n02_concept_refinement", "n03_wp_design", "phase_02_gate"),
            _edge("e03", "n03_wp_design", "n04_gantt_milestones", "phase_03_gate"),
            _edge("e04", "n04_gantt_milestones", "n05_impact_architecture", "phase_04_gate"),
            _edge("e05", "n05_impact_architecture", "n06_implementation_architecture", "phase_05_gate"),
            _edge("e06", "n06_implementation_architecture", "n07_budget_gate", "phase_06_gate"),
            # Fan-out from n07 to three parallel drafting nodes
            _edge("e07a", "n07_budget_gate", "n08a_excellence_drafting", "gate_09_budget_consistency"),
            _edge("e07b", "n07_budget_gate", "n08b_impact_drafting", "gate_09_budget_consistency"),
            _edge("e07c", "n07_budget_gate", "n08c_implementation_drafting", "gate_09_budget_consistency"),
            # Three drafting nodes converge on assembly
            _edge("e08a", "n08a_excellence_drafting", "n08d_assembly", "gate_10a_excellence_completeness"),
            _edge("e08b", "n08b_impact_drafting", "n08d_assembly", "gate_10b_impact_completeness"),
            _edge("e08c", "n08c_implementation_drafting", "n08d_assembly", "gate_10c_implementation_completeness"),
            # Sequential: assembly → review → revision
            _edge("e09", "n08d_assembly", "n08e_evaluator_review", "gate_10d_cross_section_consistency"),
            _edge("e10", "n08e_evaluator_review", "n08f_revision", "gate_11_review_closure"),
        ],
    )


_ALL_13_NODES = [
    "n01_call_analysis",
    "n02_concept_refinement",
    "n03_wp_design",
    "n04_gantt_milestones",
    "n05_impact_architecture",
    "n06_implementation_architecture",
    "n07_budget_gate",
    "n08a_excellence_drafting",
    "n08b_impact_drafting",
    "n08c_implementation_drafting",
    "n08d_assembly",
    "n08e_evaluator_review",
    "n08f_revision",
]


def _phase8_multi_node_manifest() -> dict:
    """
    Minimal manifest for Phase 8 multi-node scenario:
        n07 ──┬──→ n08a (excellence_writer) ──┐
              ├──→ n08b (impact_writer)       ├──→ n08d (assembly) → n08f (terminal)
              └──→ n08c (implementation_writer)┘

    n08a, n08b, n08c are separate parallel nodes fanning out from n07,
    converging on n08d.  Each has a separate agent invocation.
    """
    return _manifest(
        "test_phase8_multi",
        nodes=[
            _node("n07_budget_gate", "gate_09_budget_consistency"),
            _node("n08a_excellence_drafting", "gate_10a_excellence_completeness",
                  agent="excellence_writer"),
            _node("n08b_impact_drafting", "gate_10b_impact_completeness",
                  agent="impact_writer"),
            _node("n08c_implementation_drafting", "gate_10c_implementation_completeness",
                  agent="implementation_writer"),
            _node("n08d_assembly", "gate_10d_cross_section_consistency",
                  agent="proposal_integrator"),
            _node("n08f_revision", "gate_12_constitutional_compliance",
                  terminal=True),
        ],
        edges=[
            _edge("e07a", "n07_budget_gate", "n08a_excellence_drafting",
                  "gate_09_budget_consistency"),
            _edge("e07b", "n07_budget_gate", "n08b_impact_drafting",
                  "gate_09_budget_consistency"),
            _edge("e07c", "n07_budget_gate", "n08c_implementation_drafting",
                  "gate_09_budget_consistency"),
            _edge("e08a", "n08a_excellence_drafting", "n08d_assembly",
                  "gate_10a_excellence_completeness"),
            _edge("e08b", "n08b_impact_drafting", "n08d_assembly",
                  "gate_10b_impact_completeness"),
            _edge("e08c", "n08c_implementation_drafting", "n08d_assembly",
                  "gate_10c_implementation_completeness"),
            _edge("e09", "n08d_assembly", "n08f_revision",
                  "gate_10d_cross_section_consistency"),
        ],
    )


# ===========================================================================
# Scenario 1 — Linear pass: all nodes n01–n08d succeed
# ===========================================================================


class TestLinearAllPass:
    """
    All 13 nodes from n01 through n08f succeed.
    overall_status == "pass".  node_failure_details is empty.
    run_summary.json reflects the passing run.
    """

    RUN_ID = "linear-all-pass"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _full_manifest(), self.RUN_ID)

    def test_overall_status_is_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert summary.overall_status == "pass"

    def test_all_13_nodes_dispatched(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert set(summary.dispatched_nodes) == set(_ALL_13_NODES)

    def test_all_nodes_released(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        for nid, state in summary.node_states.items():
            assert state == "released", f"{nid} is {state!r}, expected 'released'"

    def test_node_failure_details_empty(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert summary.node_failure_details == {}

    def test_terminal_node_reached(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert summary.terminal_nodes_reached == ["n08f_revision"]

    def test_run_summary_json_written(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            sched.run()
        assert _run_summary_exists(tmp_path, self.RUN_ID)

    def test_run_summary_json_node_failure_details_empty(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["node_failure_details"] == {}

    def test_no_hard_blocked_nodes(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert summary.hard_blocked_nodes == []


# ===========================================================================
# Scenario 2 — Agent-body failure at n02
# ===========================================================================


class TestAgentBodyFailN02:
    """
    n01 passes (entry + exit gate).  n02 agent body fails.
    n02 state = blocked_at_exit, failure_origin="agent_body",
    exit_gate_evaluated=false.  n03+ stalled.  RunAbortedError raised.
    run_summary.json has correct node_failure_details.
    """

    RUN_ID = "agent-fail-n02"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _full_manifest(), self.RUN_ID)

    def test_raises_run_aborted(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError):
                sched.run()

    def test_n02_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        summary = exc_info.value.summary
        assert summary["node_states"]["n02_concept_refinement"] == "blocked_at_exit"

    def test_n02_failure_origin_agent_body(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        nfd = exc_info.value.summary["node_failure_details"]
        assert nfd["n02_concept_refinement"]["failure_origin"] == "agent_body"

    def test_n02_exit_gate_not_evaluated(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        nfd = exc_info.value.summary["node_failure_details"]
        assert nfd["n02_concept_refinement"]["exit_gate_evaluated"] is False

    def test_downstream_stalled(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        summary = exc_info.value.summary
        for nid in ["n03_wp_design", "n04_gantt_milestones",
                     "n05_impact_architecture", "n06_implementation_architecture",
                     "n07_budget_gate", "n08a_excellence_drafting",
                     "n08b_impact_drafting", "n08c_implementation_drafting",
                     "n08d_assembly", "n08e_evaluator_review", "n08f_revision"]:
            assert summary["node_states"][nid] == "pending", (
                f"Expected {nid} pending, got {summary['node_states'][nid]}"
            )

    def test_n01_released(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        assert exc_info.value.summary["node_states"]["n01_call_analysis"] == "released"

    def test_run_summary_json_written(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError):
                sched.run()
        assert _run_summary_exists(tmp_path, self.RUN_ID)

    def test_run_summary_json_has_node_failure_details(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError):
                sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert "n02_concept_refinement" in on_disk["node_failure_details"]
        assert on_disk["node_failure_details"]["n02_concept_refinement"][
            "failure_origin"
        ] == "agent_body"


# ===========================================================================
# Scenario 3 — Exit-gate failure at n03
# ===========================================================================


class TestExitGateFailN03:
    """
    n01, n02 pass.  n03 agent body succeeds but exit gate fails.
    n03 state = blocked_at_exit, failure_origin="exit_gate",
    exit_gate_evaluated=true.  n04+ stalled.
    """

    RUN_ID = "exit-gate-fail-n03"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _full_manifest(), self.RUN_ID)

    def test_n03_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        assert exc_info.value.summary["node_states"]["n03_wp_design"] == "blocked_at_exit"

    def test_n03_failure_origin_exit_gate(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        nfd = exc_info.value.summary["node_failure_details"]
        assert nfd["n03_wp_design"]["failure_origin"] == "exit_gate"

    def test_n03_exit_gate_evaluated_true(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        nfd = exc_info.value.summary["node_failure_details"]
        assert nfd["n03_wp_design"]["exit_gate_evaluated"] is True

    def test_n01_n02_released(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        states = exc_info.value.summary["node_states"]
        assert states["n01_call_analysis"] == "released"
        assert states["n02_concept_refinement"] == "released"

    def test_downstream_stalled(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        states = exc_info.value.summary["node_states"]
        for nid in ["n04_gantt_milestones", "n05_impact_architecture",
                     "n06_implementation_architecture", "n07_budget_gate",
                     "n08a_excellence_drafting", "n08b_impact_drafting",
                     "n08c_implementation_drafting", "n08d_assembly",
                     "n08e_evaluator_review", "n08f_revision"]:
            assert states[nid] == "pending"

    def test_run_summary_json_has_node_failure_details(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except("phase_03_gate")),
        ):
            with pytest.raises(RunAbortedError):
                sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        nfd = on_disk["node_failure_details"]
        assert nfd["n03_wp_design"]["failure_origin"] == "exit_gate"
        assert nfd["n03_wp_design"]["exit_gate_evaluated"] is True


# ===========================================================================
# Scenario 4 — Budget gate agent-body failure (n07)
# ===========================================================================


class TestBudgetAgentBodyFail:
    """
    n01–n06 pass.  n07 agent body fails (absent budget response).
    n07 state = blocked_at_exit, failure_origin="agent_body".
    Phase 8 nodes = hard_block_upstream.
    run_summary.json confirms HARD_BLOCK.
    """

    RUN_ID = "budget-agent-fail"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _full_manifest(), self.RUN_ID)

    def test_n07_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n07_budget_gate": _agent_failure("budget response absent")}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            # Phase 8 nodes become hard_block_upstream (not pending),
            # so overall_status is "fail" — no RunAbortedError.
            summary = sched.run()
        assert summary["node_states"]["n07_budget_gate"] == "blocked_at_exit"
        assert summary["overall_status"] == "fail"

    def test_n07_failure_origin_agent_body(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n07_budget_gate": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        nfd = summary["node_failure_details"]
        assert nfd["n07_budget_gate"]["failure_origin"] == "agent_body"
        assert nfd["n07_budget_gate"]["exit_gate_evaluated"] is False

    def test_phase8_hard_blocked(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n07_budget_gate": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        for nid in PHASE_8_NODE_IDS:
            assert summary["node_states"][nid] == "hard_block_upstream", (
                f"Expected {nid} hard_block_upstream, got {summary['node_states'][nid]}"
            )

    def test_n01_through_n06_released(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n07_budget_gate": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        for nid in _ALL_13_NODES[:6]:  # n01–n06
            assert summary["node_states"][nid] == "released"

    def test_hard_blocked_nodes_in_summary(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n07_budget_gate": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        hb = set(summary["hard_blocked_nodes"])
        assert PHASE_8_NODE_IDS <= hb

    def test_run_summary_json_confirms_hard_block(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n07_budget_gate": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        nfd = on_disk["node_failure_details"]
        # n07 has agent_body origin
        assert nfd["n07_budget_gate"]["failure_origin"] == "agent_body"
        # Phase 8 nodes have null origin (frozen by propagation)
        for nid in PHASE_8_NODE_IDS:
            assert nfd[nid]["failure_origin"] is None
            assert nfd[nid]["exit_gate_evaluated"] is False


# ===========================================================================
# Scenario 5 — Budget gate exit-gate failure (n07)
# ===========================================================================


class TestBudgetExitGateFail:
    """
    n01–n06 pass.  n07 agent body succeeds but gate_09 fails.
    Same HARD_BLOCK behavior.  failure_origin="exit_gate".
    """

    RUN_ID = "budget-exit-gate-fail"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _full_manifest(), self.RUN_ID)

    def test_n07_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except(
                "gate_09_budget_consistency"
            )),
        ):
            summary = sched.run()
        assert summary["node_states"]["n07_budget_gate"] == "blocked_at_exit"
        assert summary["overall_status"] == "fail"

    def test_n07_failure_origin_exit_gate(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except(
                "gate_09_budget_consistency"
            )),
        ):
            summary = sched.run()
        nfd = summary["node_failure_details"]
        assert nfd["n07_budget_gate"]["failure_origin"] == "exit_gate"
        assert nfd["n07_budget_gate"]["exit_gate_evaluated"] is True

    def test_phase8_hard_blocked(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except(
                "gate_09_budget_consistency"
            )),
        ):
            summary = sched.run()
        for nid in PHASE_8_NODE_IDS:
            assert summary["node_states"][nid] == "hard_block_upstream"

    def test_run_summary_json_confirms_hard_block(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, side_effect=_gate_pass_except(
                "gate_09_budget_consistency"
            )),
        ):
            sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        nfd = on_disk["node_failure_details"]
        assert nfd["n07_budget_gate"]["failure_origin"] == "exit_gate"
        for nid in PHASE_8_NODE_IDS:
            assert nfd[nid]["failure_origin"] is None


# ===========================================================================
# Scenario 6 — CONSTITUTIONAL_HALT propagation
# ===========================================================================


class TestConstitutionalHaltPropagation:
    """
    n01 passes.  n02 agent invokes a skill that returns CONSTITUTIONAL_HALT.
    n02 halts with failure_category="CONSTITUTIONAL_HALT",
    can_evaluate_exit_gate=False.  Downstream stalled.
    """

    RUN_ID = "constitutional-halt"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _full_manifest(), self.RUN_ID)

    def test_n02_blocked_at_exit(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_constitutional_halt()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        assert exc_info.value.summary["node_states"]["n02_concept_refinement"] == "blocked_at_exit"

    def test_n02_failure_category_constitutional_halt(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_constitutional_halt()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        nfd = exc_info.value.summary["node_failure_details"]
        assert nfd["n02_concept_refinement"]["failure_category"] == "CONSTITUTIONAL_HALT"

    def test_n02_exit_gate_not_evaluated(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_constitutional_halt()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        nfd = exc_info.value.summary["node_failure_details"]
        assert nfd["n02_concept_refinement"]["exit_gate_evaluated"] is False
        assert nfd["n02_concept_refinement"]["failure_origin"] == "agent_body"

    def test_downstream_stalled(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_constitutional_halt()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        states = exc_info.value.summary["node_states"]
        assert states["n01_call_analysis"] == "released"
        for nid in _ALL_13_NODES[2:]:  # n03 onwards
            assert states[nid] == "pending"

    def test_run_summary_json_has_constitutional_halt(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n02_concept_refinement": _agent_constitutional_halt()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError):
                sched.run()
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        nfd = on_disk["node_failure_details"]
        assert nfd["n02_concept_refinement"]["failure_category"] == "CONSTITUTIONAL_HALT"
        assert nfd["n02_concept_refinement"]["failure_origin"] == "agent_body"


# ===========================================================================
# Scenario 7 — Phase 8 multi-node (n08a + n08b with same proposal_writer)
# ===========================================================================


class TestPhase8MultiNode:
    """
    Verify that n08a, n08b, n08c are dispatched as separate nodes with separate
    agent invocations (parallel fan-out from n07), converging on n08d.
    """

    RUN_ID = "phase8-multi-node"

    def _sched(self, tmp_path: Path) -> DAGScheduler:
        return _make_scheduler(tmp_path, _phase8_multi_node_manifest(), self.RUN_ID)

    def test_all_drafting_nodes_dispatched(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert "n08a_excellence_drafting" in summary.dispatched_nodes
        assert "n08b_impact_drafting" in summary.dispatched_nodes
        assert "n08c_implementation_drafting" in summary.dispatched_nodes
        assert "n08d_assembly" in summary.dispatched_nodes

    def test_separate_agent_invocations(self, tmp_path: Path) -> None:
        """run_agent is called once per node — each drafting node is separate."""
        sched = self._sched(tmp_path)
        invoked_nodes: list[str] = []

        def _track_agent(agent_id, node_id, *args, **kwargs):
            invoked_nodes.append(node_id)
            return _agent_success()

        with (
            patch(_RA_TARGET, side_effect=_track_agent),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            sched.run()

        assert "n08a_excellence_drafting" in invoked_nodes
        assert "n08b_impact_drafting" in invoked_nodes
        assert "n08c_implementation_drafting" in invoked_nodes
        assert "n08d_assembly" in invoked_nodes
        # All three drafting nodes must be invoked before assembly
        n08a_idx = invoked_nodes.index("n08a_excellence_drafting")
        n08b_idx = invoked_nodes.index("n08b_impact_drafting")
        n08c_idx = invoked_nodes.index("n08c_implementation_drafting")
        n08d_idx = invoked_nodes.index("n08d_assembly")
        assert n08a_idx < n08d_idx
        assert n08b_idx < n08d_idx
        assert n08c_idx < n08d_idx

    def test_all_released(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert summary.node_states["n08a_excellence_drafting"] == "released"
        assert summary.node_states["n08b_impact_drafting"] == "released"
        assert summary.node_states["n08c_implementation_drafting"] == "released"
        assert summary.node_states["n08d_assembly"] == "released"

    def test_overall_status_pass(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert summary.overall_status == "pass"

    def test_node_failure_details_empty(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            summary = sched.run()
        assert summary.node_failure_details == {}

    def test_n08a_failure_blocks_assembly_not_siblings(
        self, tmp_path: Path
    ) -> None:
        """When n08a fails, n08d (assembly) is blocked but n08b/n08c proceed independently."""
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, side_effect=_agent_success_except(
                {"n08a_excellence_drafting": _agent_failure()}
            )),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()
        states = exc_info.value.summary["node_states"]
        assert states["n08a_excellence_drafting"] == "blocked_at_exit"
        # Siblings can still run (they don't depend on n08a)
        assert states["n08b_impact_drafting"] == "released"
        assert states["n08c_implementation_drafting"] == "released"
        # Assembly is blocked because it needs all three drafting nodes
        assert states["n08d_assembly"] == "pending"

    def test_run_summary_json_written(self, tmp_path: Path) -> None:
        sched = self._sched(tmp_path)
        with (
            patch(_RA_TARGET, return_value=_agent_success()),
            patch(_EG_TARGET, return_value=_PASS),
        ):
            sched.run()
        assert _run_summary_exists(tmp_path, self.RUN_ID)
        on_disk = _read_run_summary(tmp_path, self.RUN_ID)
        assert on_disk["node_failure_details"] == {}
