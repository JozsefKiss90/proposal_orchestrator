"""
Tests for single-node scoped execution (Phase 8 stepwise ticket 2).

Coverage:
  1. ManifestGraph.resolve_node_scope() — canonical id, substep shorthand,
     unknown id/substep rejection, ambiguity rejection, node_phase_number()
  2. Node-scoped dispatch runs exactly the named node
  3. Fail-closed when predecessors are not released (never dispatched,
     unmet predecessors named)
  4. Exit-gate evaluation unchanged under node scope (scheduler-owned)
  5. RunSummary node_scope field in to_dict() and write()
  6. CLI: --node/--phase mutual exclusion, _parse_phase substep rejection,
     unknown node scope error, --dry-run and --json under node scope
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from runner.dag_scheduler import (
    DAGScheduler,
    DAGSchedulerError,
    ManifestGraph,
    RunAbortedError,
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


def _seed_tier3_tier4(repo: Path) -> None:
    """Write minimal Tier 3/4 sources so the canonical reference pack builds."""
    _obj = repo / "docs/tier3_project_instantiation/architecture_inputs/objectives.json"
    _wp = repo / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
    _pt = repo / "docs/tier3_project_instantiation/consortium/partners.json"
    for p in (_obj, _wp, _pt):
        p.parent.mkdir(parents=True, exist_ok=True)
    _obj.write_text('{"objectives":[{"id":"OBJ-1","title":"T","measurable_target":"≥1"}]}', encoding="utf-8")
    _wp.write_text('{"work_packages":[{"wp_id":"WP1","title":"T","lead_partner":"P","deliverables":[{"deliverable_id":"D1-01","title":"D","due_month":3}]}]}', encoding="utf-8")
    _pt.write_text('{"partners":[{"short_name":"P","legal_name":"Partner One"}]}', encoding="utf-8")


def _phase8_substep_manifest() -> dict:
    """Phase 7 (n07) followed by phase 8 with six substep nodes (a–f).

    Mirrors the production topology: n07 fans out to n08a/n08b/n08c,
    which converge on n08d → n08e → n08f (terminal).  Phase 8 nodes carry
    the manifest ``substep`` field this ticket resolves.
    """
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
                "node_id": "n08a_excellence_drafting",
                "phase_number": 8,
                "substep": "a",
                "phase_id": "phase_08a",
                "agent": "excellence_writer",
                "skills": [],
                "exit_gate": "gate_10a_excellence_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08b_impact_drafting",
                "phase_number": 8,
                "substep": "b",
                "phase_id": "phase_08b",
                "agent": "impact_writer",
                "skills": [],
                "exit_gate": "gate_10b_impact_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08c_implementation_drafting",
                "phase_number": 8,
                "substep": "c",
                "phase_id": "phase_08c",
                "agent": "implementation_writer",
                "skills": [],
                "exit_gate": "gate_10c_implementation_completeness",
                "terminal": False,
            },
            {
                "node_id": "n08d_assembly",
                "phase_number": 8,
                "substep": "d",
                "phase_id": "phase_08d",
                "agent": "proposal_integrator",
                "skills": [],
                "exit_gate": "gate_10d_cross_section_consistency",
                "terminal": False,
            },
            {
                "node_id": "n08e_evaluator_review",
                "phase_number": 8,
                "substep": "e",
                "phase_id": "phase_08e",
                "agent": "evaluator_reviewer",
                "skills": [],
                "exit_gate": "gate_11_review_closure",
                "terminal": False,
            },
            {
                "node_id": "n08f_revision",
                "phase_number": 8,
                "substep": "f",
                "phase_id": "phase_08f",
                "agent": "revision_integrator",
                "skills": [],
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


def _graph() -> ManifestGraph:
    data = _phase8_substep_manifest()
    return ManifestGraph(data["node_registry"], data["edge_registry"])


# ---------------------------------------------------------------------------
# ManifestGraph.resolve_node_scope / node_phase_number
# ---------------------------------------------------------------------------


class TestResolveNodeScope:
    """Manifest-only resolution of single-node scope specs (§16.5)."""

    def test_canonical_node_id_resolves_to_itself(self):
        graph = _graph()
        assert (
            graph.resolve_node_scope("n08b_impact_drafting")
            == "n08b_impact_drafting"
        )

    def test_substep_shorthand_resolves(self):
        graph = _graph()
        assert graph.resolve_node_scope("8a") == "n08a_excellence_drafting"
        assert graph.resolve_node_scope("8b") == "n08b_impact_drafting"
        assert graph.resolve_node_scope("8f") == "n08f_revision"

    def test_shorthand_is_case_and_zero_pad_tolerant(self):
        graph = _graph()
        assert graph.resolve_node_scope("8B") == "n08b_impact_drafting"
        assert graph.resolve_node_scope("08a") == "n08a_excellence_drafting"
        assert graph.resolve_node_scope(" 8c ") == "n08c_implementation_drafting"

    def test_unknown_substep_rejected(self):
        graph = _graph()
        with pytest.raises(DAGSchedulerError, match="Unknown node scope '8z'"):
            graph.resolve_node_scope("8z")

    def test_substep_of_phase_without_substeps_rejected(self):
        """Phase 7's node declares no substep — '7a' must not resolve."""
        graph = _graph()
        with pytest.raises(DAGSchedulerError, match="Unknown node scope '7a'"):
            graph.resolve_node_scope("7a")

    def test_unknown_node_id_rejected(self):
        graph = _graph()
        with pytest.raises(DAGSchedulerError, match="Unknown node scope 'n99_bogus'"):
            graph.resolve_node_scope("n99_bogus")

    def test_bare_phase_number_rejected(self):
        """A bare phase number is not a node scope."""
        graph = _graph()
        with pytest.raises(DAGSchedulerError, match="Unknown node scope '8'"):
            graph.resolve_node_scope("8")

    def test_ambiguous_substep_rejected(self):
        """Two nodes claiming the same phase+substep is a manifest defect."""
        registry = [
            {"node_id": "nx1", "phase_number": 9, "substep": "x", "exit_gate": "g1"},
            {"node_id": "nx2", "phase_number": 9, "substep": "x", "exit_gate": "g2"},
        ]
        graph = ManifestGraph(registry, [])
        with pytest.raises(DAGSchedulerError, match="Ambiguous node scope '9x'"):
            graph.resolve_node_scope("9x")

    def test_node_phase_number(self):
        graph = _graph()
        assert graph.node_phase_number("n07_budget_gate") == 7
        assert graph.node_phase_number("n08d_assembly") == 8

    def test_node_phase_number_unknown_node_raises(self):
        graph = _graph()
        with pytest.raises(DAGSchedulerError, match="Unknown node_id"):
            graph.node_phase_number("n99_bogus")


# ---------------------------------------------------------------------------
# Node-scoped dispatch: exactly the named node runs
# ---------------------------------------------------------------------------


class TestNodeScopedDispatch:
    """A scoped run dispatches the named node and nothing else."""

    def test_single_node_dispatch_by_id(self, tmp_path: Path):
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-id")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                node="n08a_excellence_drafting",
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == ["n08a_excellence_drafting"]
        assert summary.node_scope == "n08a_excellence_drafting"
        assert summary.phase_scope is None
        assert summary.phase_scope_nodes == []
        # Siblings and downstream nodes remain untouched.
        assert summary.node_states["n08b_impact_drafting"] == "pending"
        assert summary.node_states["n08c_implementation_drafting"] == "pending"
        assert summary.node_states["n08d_assembly"] == "pending"
        assert summary.stalled_nodes == []

    def test_single_node_dispatch_by_shorthand(self, tmp_path: Path):
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-shorthand")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                node="8b",
            )
            summary = sched.run()

        assert summary.dispatched_nodes == ["n08b_impact_drafting"]
        assert summary.node_scope == "n08b_impact_drafting"

    def test_mid_sequence_node_with_released_predecessors(self, tmp_path: Path):
        """n08d runs alone when a/b/c are already released in the RunContext."""
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-mid")
        for nid in (
            "n07_budget_gate",
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
        ):
            ctx.set_node_state(nid, "released")
        ctx.save()

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                node="8d",
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == ["n08d_assembly"]
        # Downstream of the scoped node is never dispatched.
        assert summary.node_states["n08e_evaluator_review"] == "pending"

    def test_unknown_node_scope_raises_before_dispatch(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-unknown")

        sched = DAGScheduler(
            graph, ctx, tmp_path,
            manifest_path=manifest_path,
            node="8z",
        )
        with pytest.raises(DAGSchedulerError, match="Unknown node scope '8z'"):
            sched.run()

    def test_phase_and_node_scope_mutually_exclusive(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-mutex")

        with pytest.raises(DAGSchedulerError, match="mutually exclusive"):
            DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=8,
                node="8a",
            )


# ---------------------------------------------------------------------------
# Fail-closed: predecessors not released → never dispatched
# ---------------------------------------------------------------------------


class TestNodeScopedFailClosed:
    """A scoped node with unmet predecessors is never dispatched (§13.7)."""

    def test_not_ready_node_fails_closed_naming_predecessors(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-notready")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        evaluate_gate_calls: list[str] = []

        def _record_gate(gate_id, *args, **kwargs):
            evaluate_gate_calls.append(gate_id)
            return _GATE_PASS

        with patch("runner.dag_scheduler.evaluate_gate", side_effect=_record_gate):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                node="8d",
            )
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        assert summary.overall_status == "aborted"
        assert summary.node_scope == "n08d_assembly"
        # Never dispatched; no gate was evaluated.
        assert summary.dispatched_nodes == []
        assert evaluate_gate_calls == []
        assert summary.node_states["n08d_assembly"] == "pending"
        # The stall report names each unmet predecessor and its gate.
        assert len(summary.stalled_nodes) == 1
        entry = summary.stalled_nodes[0]
        assert entry["node_id"] == "n08d_assembly"
        unmet_sources = {
            c["source_node_id"] for c in entry["unsatisfied_conditions"]
        }
        assert unmet_sources == {
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
        }
        # The abort message itself names the unmet predecessors.
        assert "Unmet predecessors" in str(exc_info.value)
        assert "n08a_excellence_drafting" in str(exc_info.value)

    def test_pending_upstream_phase_fails_closed(self, tmp_path: Path):
        """n08a with n07 still pending is refused, naming n07."""
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-upstream")

        sched = DAGScheduler(
            graph, ctx, tmp_path,
            manifest_path=manifest_path,
            node="8a",
        )
        with pytest.raises(RunAbortedError) as exc_info:
            sched.run()

        summary = exc_info.value.summary
        assert summary.dispatched_nodes == []
        entry = summary.stalled_nodes[0]
        assert entry["node_id"] == "n08a_excellence_drafting"
        assert entry["unsatisfied_conditions"][0]["source_node_id"] == "n07_budget_gate"
        assert "n07_budget_gate=pending" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Gate evaluation unchanged under node scope
# ---------------------------------------------------------------------------


class TestNodeScopedGateEvaluation:
    """Entry/exit gates run exactly as in a full-phase run, scheduler-owned."""

    def test_exit_gate_evaluated_for_scoped_node(self, tmp_path: Path):
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-gate")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        evaluated: list[str] = []

        def _record_gate(gate_id, *args, **kwargs):
            evaluated.append(gate_id)
            return _GATE_PASS

        with patch("runner.dag_scheduler.evaluate_gate", side_effect=_record_gate):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                node="8a",
            )
            summary = sched.run()

        assert "gate_10a_excellence_completeness" in evaluated
        assert summary.node_states["n08a_excellence_drafting"] == "released"

    def test_exit_gate_failure_blocks_scoped_node(self, tmp_path: Path):
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-gatefail")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_FAIL):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                node="8a",
            )
            summary = sched.run()

        assert summary.overall_status == "fail"
        assert summary.node_states["n08a_excellence_drafting"] == "blocked_at_exit"
        assert summary.node_scope == "n08a_excellence_drafting"


# ---------------------------------------------------------------------------
# RunSummary node_scope serialisation
# ---------------------------------------------------------------------------


class TestRunSummaryNodeScope:
    def test_to_dict_and_write_include_node_scope(self, tmp_path: Path):
        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-node-summary")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                node="8a",
            )
            summary = sched.run()

        assert summary.to_dict()["node_scope"] == "n08a_excellence_drafting"
        data = json.loads(
            (ctx.run_dir / "run_summary.json").read_text(encoding="utf-8")
        )
        assert data["node_scope"] == "n08a_excellence_drafting"
        assert data["phase_scope"] is None
        assert data["phase_scope_nodes"] == []

    def test_full_dag_summary_has_null_node_scope(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "test-null-node")
        _seed_tier3_tier4(tmp_path)

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
            )
            summary = sched.run()

        assert summary.node_scope is None
        assert summary.to_dict()["node_scope"] is None


# ---------------------------------------------------------------------------
# CLI: argument handling and end-to-end node scope
# ---------------------------------------------------------------------------

_TRANSPORT_PC = SimpleNamespace(
    backend_name="mock", model="mock-model", preset_name="MOCK"
)


def _cli_patches():
    """Hermetic patches for in-process main() calls."""
    return (
        patch(
            "runner.transport.config.resolve_provider_config",
            return_value=_TRANSPORT_PC,
        ),
        patch("runner.transport.config.is_production_mode", return_value=False),
        patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS),
    )


class TestCLINodeArgument:
    def test_parse_phase_rejects_substep_shorthand(self):
        import argparse

        from runner.__main__ import _parse_phase

        with pytest.raises(argparse.ArgumentTypeError, match="--node"):
            _parse_phase("8a")
        with pytest.raises(argparse.ArgumentTypeError, match="--node"):
            _parse_phase("08b")

    def test_parse_phase_still_accepts_full_phase_ids(self):
        """Regression guard: existing spellings keep working."""
        from runner.__main__ import _parse_phase

        assert _parse_phase("8") == 8
        assert _parse_phase("phase_01") == 1
        assert _parse_phase("phase_01_call_analysis") == 1

    def test_phase_and_node_flags_mutually_exclusive(self):
        from runner.__main__ import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--run-id", "x", "--phase", "8", "--node", "8a"])
        assert exc_info.value.code == 2

    def test_unknown_node_scope_is_distinct_error(self, tmp_path: Path, capsys):
        from runner.__main__ import main

        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        code = main([
            "--run-id", "cli-unknown-node",
            "--repo-root", str(tmp_path),
            "--manifest-path", str(manifest_path),
            "--node", "8z",
        ])
        assert code == 3
        assert "Unknown node scope '8z'" in capsys.readouterr().err

    def test_dry_run_under_node_scope(self, tmp_path: Path, capsys):
        from runner.__main__ import main

        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "cli-node-dry")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        p1, p2, p3 = _cli_patches()
        with p1, p2, p3:
            code = main([
                "--run-id", "cli-node-dry",
                "--repo-root", str(tmp_path),
                "--manifest-path", str(manifest_path),
                "--node", "8a",
                "--dry-run",
            ])
        assert code == 0
        out = capsys.readouterr().out
        ready_lines = [l for l in out.splitlines() if l.startswith("[READY]")]
        assert ready_lines == ["[READY] n08a_excellence_drafting"]

    def test_json_node_scoped_run(self, tmp_path: Path, capsys):
        from runner.__main__ import main

        _seed_tier3_tier4(tmp_path)
        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())
        ctx = RunContext.initialize(tmp_path, "cli-node-json")
        ctx.set_node_state("n07_budget_gate", "released")
        ctx.save()

        p1, p2, p3 = _cli_patches()
        with p1, p2, p3:
            code = main([
                "--run-id", "cli-node-json",
                "--repo-root", str(tmp_path),
                "--manifest-path", str(manifest_path),
                "--node", "8a",
                "--json",
            ])
        assert code == 0
        events = [
            json.loads(line)
            for line in capsys.readouterr().out.splitlines()
            if line.strip().startswith("{")
        ]
        run_start = next(e for e in events if e["event"] == "run_start")
        assert run_start["node"] == "n08a_excellence_drafting"
        summary_ev = next(e for e in events if e["event"] == "summary")
        assert summary_ev["node_scope"] == "n08a_excellence_drafting"
        assert summary_ev["overall_status"] == "pass"

        run_summary = json.loads(
            (tmp_path / ".claude" / "runs" / "cli-node-json" / "run_summary.json")
            .read_text(encoding="utf-8")
        )
        assert run_summary["dispatched_nodes"] == ["n08a_excellence_drafting"]
        assert run_summary["node_scope"] == "n08a_excellence_drafting"

    def test_cli_fail_closed_reports_unmet_predecessors(
        self, tmp_path: Path, capsys
    ):
        """Not-ready scoped node: exit code 2, [BLOCKED] names predecessors."""
        from runner.__main__ import main

        manifest_path = _write_manifest(tmp_path, _phase8_substep_manifest())

        p1, p2, p3 = _cli_patches()
        with p1, p2, p3:
            code = main([
                "--run-id", "cli-node-blocked",
                "--repo-root", str(tmp_path),
                "--manifest-path", str(manifest_path),
                "--node", "8a",
            ])
        assert code == 2
        out = capsys.readouterr().out
        assert "[BLOCKED] n08a_excellence_drafting" in out
        assert "n07_budget_gate=pending" in out
        assert "gate_09_budget_consistency" in out
