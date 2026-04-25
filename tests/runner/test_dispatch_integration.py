"""
Tests for scheduler integration — _dispatch_node() with agent runtime.

Covers §14 test cases 7, 8, 11–18:
  7.  agent failure (can_evaluate_exit_gate=False) preventing exit-gate evaluation
  8.  successful node body + exit gate pass → released
  11. HARD_BLOCK preserved after budget gate failure with failure_origin="agent_body"
  12. HARD_BLOCK preserved after budget gate failure with failure_origin="exit_gate"
  13. run summary node_failure_details correctly classifies all three origins
  14. exit_gate_evaluated is False for entry_gate and agent_body failures
  15. exit_gate_evaluated is True for exit_gate failures
  16. CONSTITUTIONAL_HALT propagates as agent_body failure
  17. RunContext persists failure_origin and exit_gate_evaluated
  18. _dispatch_node() skips exit gate when can_evaluate_exit_gate is False
      even if status=="success"

All tests use patched evaluate_gate and run_agent with synthetic manifests.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from runner.dag_scheduler import (
    DAGScheduler,
    DAGSchedulerError,
    ManifestGraph,
    RunAbortedError,
    RunSummary,
)
from runner.run_context import PHASE_8_NODE_IDS, RunContext
from runner.runtime_models import AgentResult, NodeExecutionResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EG_TARGET = "runner.dag_scheduler.evaluate_gate"
_RA_TARGET = "runner.dag_scheduler.run_agent"
_GATE_PASS = {"status": "pass"}
_GATE_FAIL = {"status": "fail", "reason": "gate failed"}


def _success_agent(**overrides) -> AgentResult:
    defaults = {"status": "success", "can_evaluate_exit_gate": True}
    defaults.update(overrides)
    return AgentResult(**defaults)


def _failure_agent(**overrides) -> AgentResult:
    defaults = {
        "status": "failure",
        "can_evaluate_exit_gate": False,
        "failure_reason": "agent body failed",
        "failure_category": "SKILL_FAILURE",
    }
    defaults.update(overrides)
    return AgentResult(**defaults)


# ---------------------------------------------------------------------------
# Helpers — synthetic manifest and scheduler
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _single_node_manifest(
    node_id: str = "n01_call_analysis",
    exit_gate: str = "phase_01_gate",
    entry_gate: str | None = None,
    terminal: bool = False,
) -> dict:
    node: dict = {"node_id": node_id, "exit_gate": exit_gate, "terminal": terminal}
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


def _gate09_manifest() -> dict:
    """Manifest where n07 holds gate_09_budget_consistency.

    Topology: n07 fans out to n08a/n08b/n08c (parallel drafting),
    those three converge on n08d (assembly), then n08d → n08e → n08f.
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
                "node_id": "n08a_excellence_drafting",
                "exit_gate": "gate_10a_excellence_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08b_impact_drafting",
                "exit_gate": "gate_10b_impact_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08c_implementation_drafting",
                "exit_gate": "gate_10c_implementation_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08d_assembly",
                "exit_gate": "gate_10d_cross_section_consistency",
                "terminal": False,
            },
            {
                "node_id": "n08e_evaluator_review",
                "exit_gate": "gate_11_review_closure",
                "terminal": False,
            },
            {
                "node_id": "n08f_revision",
                "exit_gate": "gate_12_constitutional_compliance",
                "terminal": True,
            },
        ],
        "edge_registry": [
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


def _make_scheduler(
    tmp_path: Path,
    manifest_data: dict,
    run_id: str = "test-run",
) -> DAGScheduler:
    mp = _write_manifest(tmp_path, manifest_data)
    graph = ManifestGraph.load(mp)
    ctx = RunContext.initialize(tmp_path, run_id)
    sched = DAGScheduler(graph, ctx, tmp_path, manifest_path=mp)
    # Inject mock NodeResolver
    mock_resolver = MagicMock()
    mock_resolver.resolve_agent_id.return_value = "test_agent"
    mock_resolver.resolve_sub_agent_id.return_value = None
    mock_resolver.resolve_pre_gate_agent_id.return_value = None
    mock_resolver.resolve_skill_ids.return_value = []
    mock_resolver.resolve_phase_id.return_value = "phase1"
    sched._DAGScheduler__node_resolver = mock_resolver
    return sched


def _read_run_summary(tmp_path: Path, run_id: str) -> dict:
    path = tmp_path / ".claude" / "runs" / run_id / "run_summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# §14 test 7 — agent failure prevents exit-gate evaluation
# ---------------------------------------------------------------------------


class TestAgentFailurePreventsExitGate:
    """Confirm that when AgentResult.can_evaluate_exit_gate == False,
    the scheduler skips exit gate evaluation unconditionally."""

    def test_exit_gate_not_called_on_agent_failure(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())

        with (
            patch(_RA_TARGET, return_value=_failure_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg,
        ):
            result = sched.run()

        # evaluate_gate should NOT have been called for exit gate
        # (no entry gate in this manifest, so only agent body runs)
        mock_eg.assert_not_called()
        assert result["node_states"]["n01_call_analysis"] == "blocked_at_exit"

    def test_exit_gate_not_called_with_entry_gate_pass(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01_source_integrity"),
        )

        call_count = 0

        def _pass_entry_only(gate_id, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _GATE_PASS

        with (
            patch(_RA_TARGET, return_value=_failure_agent()),
            patch(_EG_TARGET, side_effect=_pass_entry_only),
        ):
            result = sched.run()

        # evaluate_gate called once (entry gate), NOT twice (exit skipped)
        assert call_count == 1
        assert result["node_states"]["n01_call_analysis"] == "blocked_at_exit"


# ---------------------------------------------------------------------------
# §14 test 8 — successful node body + exit gate pass → released
# ---------------------------------------------------------------------------


class TestSuccessfulNodeBodyAndGate:
    """Test the complete happy-path flow: agent executes successfully,
    exit gate passes, node transitions to released."""

    def test_released_after_success(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest(terminal=True))

        with (
            patch(_RA_TARGET, return_value=_success_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            result = sched.run()

        assert result["node_states"]["n01_call_analysis"] == "released"
        assert result["overall_status"] == "pass"

    def test_released_with_entry_gate(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(
                entry_gate="gate_01", terminal=True
            ),
        )

        with (
            patch(_RA_TARGET, return_value=_success_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            result = sched.run()

        assert result["node_states"]["n01_call_analysis"] == "released"


# ---------------------------------------------------------------------------
# §14 test 11 — HARD_BLOCK with failure_origin="agent_body"
# ---------------------------------------------------------------------------


class TestHardBlockAgentBody:
    """Test that when n07_budget_gate agent body fails,
    mark_hard_block_downstream() is called, freezing Phase 8 nodes."""

    def test_hard_block_on_agent_body_failure(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _gate09_manifest())

        with (
            patch(_RA_TARGET, return_value=_failure_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            # Phase 8 nodes become hard_block_upstream (not pending),
            # so overall_status is "fail" — no RunAbortedError.
            result = sched.run()

        assert result["node_states"]["n07_budget_gate"] == "blocked_at_exit"
        assert result["overall_status"] == "fail"
        # Phase 8 nodes should be hard-blocked
        for nid in ["n08a_excellence_drafting", "n08b_impact_drafting",
                     "n08c_implementation_drafting", "n08d_assembly",
                     "n08e_evaluator_review", "n08f_revision"]:
            assert result["node_states"][nid] == "hard_block_upstream"
        assert result["hard_blocked_nodes"] != []


# ---------------------------------------------------------------------------
# §14 test 12 — HARD_BLOCK with failure_origin="exit_gate"
# ---------------------------------------------------------------------------


class TestHardBlockExitGate:
    """Test that when n07_budget_gate exit gate fails,
    mark_hard_block_downstream() is called, freezing Phase 8 nodes."""

    def test_hard_block_on_exit_gate_failure(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _gate09_manifest())

        def _fail_gate09(gate_id, *args, **kwargs):
            if gate_id == "gate_09_budget_consistency":
                return _GATE_FAIL
            return _GATE_PASS

        with (
            patch(_RA_TARGET, return_value=_success_agent()),
            patch(_EG_TARGET, side_effect=_fail_gate09),
        ):
            result = sched.run()

        assert result["node_states"]["n07_budget_gate"] == "blocked_at_exit"
        assert result["overall_status"] == "fail"
        for nid in ["n08a_excellence_drafting", "n08b_impact_drafting",
                     "n08c_implementation_drafting", "n08d_assembly",
                     "n08e_evaluator_review", "n08f_revision"]:
            assert result["node_states"][nid] == "hard_block_upstream"


# ---------------------------------------------------------------------------
# §14 test 13 — node_failure_details classifies all three origins
# ---------------------------------------------------------------------------


class TestNodeFailureDetailsClassification:
    """Verify that run_summary.json correctly populates
    node_failure_details[node_id].failure_origin for all three origins."""

    def test_entry_gate_origin(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01"),
        )
        with (
            patch(_RA_TARGET, return_value=_success_agent()),
            patch(_EG_TARGET, return_value=_GATE_FAIL),
        ):
            result = sched.run()

        details = result["node_failure_details"]
        assert "n01_call_analysis" in details
        assert details["n01_call_analysis"]["failure_origin"] == "entry_gate"

    def test_agent_body_origin(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with (
            patch(_RA_TARGET, return_value=_failure_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            result = sched.run()

        details = result["node_failure_details"]
        assert "n01_call_analysis" in details
        assert details["n01_call_analysis"]["failure_origin"] == "agent_body"

    def test_exit_gate_origin(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with (
            patch(_RA_TARGET, return_value=_success_agent()),
            patch(_EG_TARGET, return_value=_GATE_FAIL),
        ):
            result = sched.run()

        details = result["node_failure_details"]
        assert "n01_call_analysis" in details
        assert details["n01_call_analysis"]["failure_origin"] == "exit_gate"


# ---------------------------------------------------------------------------
# §14 test 14 — exit_gate_evaluated is False for entry_gate and agent_body
# ---------------------------------------------------------------------------


class TestExitGateEvaluatedFalse:
    """Confirm exit_gate_evaluated is false when failure_origin is
    entry_gate or agent_body."""

    def test_false_for_entry_gate_failure(self, tmp_path: Path) -> None:
        sched = _make_scheduler(
            tmp_path,
            _single_node_manifest(entry_gate="gate_01"),
        )
        with (
            patch(_RA_TARGET, return_value=_success_agent()),
            patch(_EG_TARGET, return_value=_GATE_FAIL),
        ):
            result = sched.run()

        details = result["node_failure_details"]["n01_call_analysis"]
        assert details["exit_gate_evaluated"] is False

    def test_false_for_agent_body_failure(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with (
            patch(_RA_TARGET, return_value=_failure_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            result = sched.run()

        details = result["node_failure_details"]["n01_call_analysis"]
        assert details["exit_gate_evaluated"] is False


# ---------------------------------------------------------------------------
# §14 test 15 — exit_gate_evaluated is True for exit_gate failures
# ---------------------------------------------------------------------------


class TestExitGateEvaluatedTrue:
    """Confirm exit_gate_evaluated is true when failure_origin is exit_gate."""

    def test_true_for_exit_gate_failure(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _single_node_manifest())
        with (
            patch(_RA_TARGET, return_value=_success_agent()),
            patch(_EG_TARGET, return_value=_GATE_FAIL),
        ):
            result = sched.run()

        details = result["node_failure_details"]["n01_call_analysis"]
        assert details["exit_gate_evaluated"] is True


# ---------------------------------------------------------------------------
# §14 test 16 — CONSTITUTIONAL_HALT propagates as agent_body failure
# ---------------------------------------------------------------------------


class TestConstitutionalHaltPropagation:
    """Test that CONSTITUTIONAL_HALT from a skill propagates through the
    agent and surfaces in the scheduler as failure_origin="agent_body"
    with failure_category="CONSTITUTIONAL_HALT"."""

    def test_constitutional_halt_in_node_failure_details(self, tmp_path: Path) -> None:
        halt_agent = AgentResult(
            status="failure",
            can_evaluate_exit_gate=False,
            failure_reason="CONSTITUTIONAL_HALT from skill",
            failure_category="CONSTITUTIONAL_HALT",
        )
        sched = _make_scheduler(tmp_path, _single_node_manifest())

        with (
            patch(_RA_TARGET, return_value=halt_agent),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            result = sched.run()

        details = result["node_failure_details"]["n01_call_analysis"]
        assert details["failure_origin"] == "agent_body"
        assert details["exit_gate_evaluated"] is False
        assert details["failure_category"] == "CONSTITUTIONAL_HALT"


# ---------------------------------------------------------------------------
# §14 test 17 — RunContext persists failure_origin and exit_gate_evaluated
# ---------------------------------------------------------------------------


class TestRunContextPersistence:
    """Verify that ctx.set_node_state() correctly persists extended failure
    metadata and that RunSummary.build() reads them."""

    def test_failure_details_persisted(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, "run-persist-test")
        ctx.set_node_state(
            "n01_call_analysis",
            "blocked_at_exit",
            failure_origin="agent_body",
            exit_gate_evaluated=False,
            failure_reason="skill failed",
            failure_category="SKILL_FAILURE",
        )
        ctx.save()

        # Reload and verify
        ctx2 = RunContext.load(tmp_path, "run-persist-test")
        details = ctx2.get_node_failure_details("n01_call_analysis")
        assert details is not None
        assert details["failure_origin"] == "agent_body"
        assert details["exit_gate_evaluated"] is False
        assert details["failure_reason"] == "skill failed"
        assert details["failure_category"] == "SKILL_FAILURE"

    def test_no_failure_details_on_success(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, "run-no-fail")
        ctx.set_node_state("n01_call_analysis", "released")
        ctx.save()

        ctx2 = RunContext.load(tmp_path, "run-no-fail")
        assert ctx2.get_node_failure_details("n01_call_analysis") is None

    def test_2_arg_backward_compat(self, tmp_path: Path) -> None:
        """Existing 2-arg set_node_state() calls still work."""
        ctx = RunContext.initialize(tmp_path, "run-compat")
        ctx.set_node_state("n01_call_analysis", "blocked_at_exit")
        ctx.save()
        assert ctx.get_node_state("n01_call_analysis") == "blocked_at_exit"

    def test_run_summary_reads_failure_details(self, tmp_path: Path) -> None:
        """RunSummary contains node_failure_details from persisted state."""
        sched = _make_scheduler(tmp_path, _single_node_manifest())

        with (
            patch(_RA_TARGET, return_value=_failure_agent(
                failure_reason="test reason",
                failure_category="SKILL_FAILURE",
            )),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            result = sched.run()

        nfd = result["node_failure_details"]
        assert "n01_call_analysis" in nfd
        assert nfd["n01_call_analysis"]["failure_reason"] == "test reason"

    def test_run_summary_json_contains_node_failure_details(
        self, tmp_path: Path
    ) -> None:
        """run_summary.json written to disk includes node_failure_details."""
        run_id = "run-json-check"
        sched = _make_scheduler(tmp_path, _single_node_manifest(), run_id=run_id)

        with (
            patch(_RA_TARGET, return_value=_failure_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            sched.run()

        summary_on_disk = _read_run_summary(tmp_path, run_id)
        assert "node_failure_details" in summary_on_disk
        assert "n01_call_analysis" in summary_on_disk["node_failure_details"]


# ---------------------------------------------------------------------------
# §14 test 18 — skip exit gate even if status=="success" when
#   can_evaluate_exit_gate is False
# ---------------------------------------------------------------------------


class TestSkipExitGateOnCanEvaluateFalse:
    """Test the critical semantic: even when an agent reports success status,
    if can_evaluate_exit_gate == False, the exit gate is skipped and the node
    blocks."""

    def test_success_but_no_gate_eval(self, tmp_path: Path) -> None:
        """Agent status="success" but can_evaluate_exit_gate=False → blocked."""
        weird_agent = AgentResult(
            status="success",
            can_evaluate_exit_gate=False,
        )
        sched = _make_scheduler(tmp_path, _single_node_manifest())

        with (
            patch(_RA_TARGET, return_value=weird_agent),
            patch(_EG_TARGET, return_value=_GATE_PASS) as mock_eg,
        ):
            result = sched.run()

        # Exit gate must NOT have been called
        mock_eg.assert_not_called()
        assert result["node_states"]["n01_call_analysis"] == "blocked_at_exit"
        details = result["node_failure_details"]["n01_call_analysis"]
        assert details["failure_origin"] == "agent_body"
        assert details["exit_gate_evaluated"] is False


# ---------------------------------------------------------------------------
# Combined scenario: two-node chain with agent failure at n01
# ---------------------------------------------------------------------------


class TestTwoNodeAgentFailure:
    """Agent body failure at n01 → n02 stalls → RunAbortedError."""

    def test_downstream_stalls(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _two_node_linear_manifest())

        with (
            patch(_RA_TARGET, return_value=_failure_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        assert summary["node_states"]["n01_call_analysis"] == "blocked_at_exit"
        assert summary["node_states"]["n02_concept_refinement"] == "pending"


# ---------------------------------------------------------------------------
# hard_block_upstream in node_failure_details
# ---------------------------------------------------------------------------


class TestHardBlockInFailureDetails:
    """Phase 8 nodes hard-blocked after n07 failure have failure_origin=None."""

    def test_hard_block_nodes_have_null_origin(self, tmp_path: Path) -> None:
        sched = _make_scheduler(tmp_path, _gate09_manifest())

        with (
            patch(_RA_TARGET, return_value=_failure_agent()),
            patch(_EG_TARGET, return_value=_GATE_PASS),
        ):
            result = sched.run()

        nfd = result["node_failure_details"]
        for nid in ["n08a_excellence_drafting", "n08b_impact_drafting",
                     "n08c_implementation_drafting", "n08d_assembly",
                     "n08e_evaluator_review", "n08f_revision"]:
            assert nfd[nid]["failure_origin"] is None
            assert nfd[nid]["exit_gate_evaluated"] is False
