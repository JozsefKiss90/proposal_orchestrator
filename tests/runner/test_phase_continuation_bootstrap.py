"""
Tests for phase-scoped continuation bootstrap.

Coverage:
  1. Existing run-id preservation — prior node states are not reset.
  2. New run-id bootstrap from durable gate evidence — upstream nodes
     seeded as released when canonical gate result shows pass.
  3. Fail-closed — absent or non-passing evidence does not bootstrap.
  4. No false release from artifact presence alone — phase output files
     without a passing gate result do not trigger bootstrap.
  5. Multi-upstream generality — later phases with multiple upstream
     dependencies are all bootstrapped correctly.
  6. Non-phase-scoped runs unchanged — full DAG execution unaffected.
  7. RunContext.load_or_initialize — preserves existing, creates new.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runner.dag_scheduler import (
    DAGScheduler,
    ManifestGraph,
    RunAbortedError,
    bootstrap_phase_prerequisites,
)
from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.run_context import RunContext
from runner.runtime_models import AgentResult

# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

_GATE_PASS = {"status": "pass"}
_GATE_FAIL = {"status": "fail", "reason": "test failure"}
_RA_TARGET = "runner.dag_scheduler.run_agent"
_SUCCESS_AGENT = AgentResult(status="success", can_evaluate_exit_gate=True)
_TIER4_ROOT_REL = "docs/tier4_orchestration_state"


@pytest.fixture(autouse=True)
def _mock_run_agent():
    """Patch run_agent for all tests — these exercise scheduling, not agents."""
    with patch(_RA_TARGET, return_value=_SUCCESS_AGENT):
        yield


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _write_gate_result(
    repo_root: Path,
    gate_id: str,
    status: str = "pass",
    **extra: object,
) -> Path:
    """Write a canonical gate result artifact to Tier 4."""
    rel_path = GATE_RESULT_PATHS.get(gate_id)
    if rel_path is None:
        # Fallback for gates not in registry
        rel_path = f"gate_results/{gate_id}.json"
    abs_path = repo_root / _TIER4_ROOT_REL / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "gate_id": gate_id,
        "status": status,
        "run_id": "prior-run-id",
        "manifest_version": "1.1",
        "library_version": "1.0",
        "constitution_version": "1.0",
        "evaluated_at": "2026-04-16T00:00:00+00:00",
        "input_fingerprint": "sha256:abc123",
        **extra,
    }
    abs_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return abs_path


def _three_phase_manifest() -> dict:
    """Three sequential phases: n01 → n02 → n03."""
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


def _diamond_manifest() -> dict:
    """Diamond DAG: n01 → n02, n03 → n04 (multi-upstream for n04).

    n01 (phase 1) → n02 (phase 2), n03 (phase 3)
    n02, n03 → n04 (phase 4)
    """
    return {
        "name": "test-diamond",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": "n01_call_analysis",
                "phase_number": 1,
                "phase_id": "phase_01",
                "agent": "a01",
                "skills": [],
                "exit_gate": "phase_01_gate",
                "terminal": False,
            },
            {
                "node_id": "n02_concept_refinement",
                "phase_number": 2,
                "phase_id": "phase_02",
                "agent": "a02",
                "skills": [],
                "exit_gate": "phase_02_gate",
                "terminal": False,
            },
            {
                "node_id": "n03_wp_design",
                "phase_number": 3,
                "phase_id": "phase_03",
                "agent": "a03",
                "skills": [],
                "exit_gate": "phase_03_gate",
                "terminal": False,
            },
            {
                "node_id": "n04_gantt_milestones",
                "phase_number": 4,
                "phase_id": "phase_04",
                "agent": "a04",
                "skills": [],
                "exit_gate": "phase_04_gate",
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
                "edge_id": "e01_to_03",
                "from_node": "n01_call_analysis",
                "to_node": "n03_wp_design",
                "gate_condition": "phase_01_gate",
            },
            {
                "edge_id": "e02_to_04",
                "from_node": "n02_concept_refinement",
                "to_node": "n04_gantt_milestones",
                "gate_condition": "phase_02_gate",
            },
            {
                "edge_id": "e03_to_04",
                "from_node": "n03_wp_design",
                "to_node": "n04_gantt_milestones",
                "gate_condition": "phase_03_gate",
            },
        ],
    }


# ===========================================================================
# 1. Existing run-id preservation
# ===========================================================================


class TestExistingRunIdPreservation:
    """Running with an existing run-id must not reset prior node states."""

    def test_load_or_initialize_preserves_existing_states(self, tmp_path: Path):
        """Given an existing run manifest with n01=released, loading the
        same run_id preserves the released state."""
        ctx1 = RunContext.initialize(tmp_path, "existing-run")
        ctx1.set_node_state("n01_call_analysis", "released")
        ctx1.save()

        # Simulate re-invocation with the same run_id.
        ctx2 = RunContext.load_or_initialize(tmp_path, "existing-run")
        assert ctx2.get_node_state("n01_call_analysis") == "released"

    def test_existing_run_phase2_uses_prior_states(self, tmp_path: Path):
        """Phase-scoped execution with an existing run-id that already has
        n01=released should allow n02 to become ready."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)

        # First run: release n01.
        ctx1 = RunContext.initialize(tmp_path, "reuse-run")
        ctx1.set_node_state("n01_call_analysis", "released")
        ctx1.save()

        # Second invocation: same run_id, phase=2.
        ctx2 = RunContext.load_or_initialize(tmp_path, "reuse-run")
        assert ctx2.get_node_state("n01_call_analysis") == "released"

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx2, tmp_path,
                manifest_path=manifest_path,
                phase=2,
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == ["n02_concept_refinement"]

    def test_existing_run_does_not_overwrite_blocked_state(self, tmp_path: Path):
        """A node in blocked_at_exit should stay blocked, not reset to pending."""
        ctx1 = RunContext.initialize(tmp_path, "blocked-run")
        ctx1.set_node_state("n01_call_analysis", "released")
        ctx1.set_node_state("n02_concept_refinement", "blocked_at_exit")
        ctx1.save()

        ctx2 = RunContext.load_or_initialize(tmp_path, "blocked-run")
        assert ctx2.get_node_state("n02_concept_refinement") == "blocked_at_exit"


# ===========================================================================
# 2. New run-id bootstrap from durable gate evidence
# ===========================================================================


class TestNewRunIdBootstrap:
    """New run-id with --phase bootstraps upstream from Tier 4 evidence."""

    def test_bootstrap_seeds_n01_from_gate_result(self, tmp_path: Path):
        """Given a passing phase_01_gate result on disk, bootstrap seeds
        n01_call_analysis as released for a phase 2 run."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "new-run-bootstrap")

        # Write passing gate result for phase_01_gate.
        _write_gate_result(tmp_path, "phase_01_gate", status="pass")

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == ["n01_call_analysis"]
        assert ctx.get_node_state("n01_call_analysis") == "released"

    def test_bootstrapped_node_enables_dispatch(self, tmp_path: Path):
        """After bootstrap, n02 becomes ready and dispatches successfully."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "dispatch-after-bootstrap")

        _write_gate_result(tmp_path, "phase_01_gate", status="pass")
        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=2,
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == ["n02_concept_refinement"]
        assert summary.node_states["n01_call_analysis"] == "released"

    def test_transitive_bootstrap_for_phase3(self, tmp_path: Path):
        """Phase 3 requires n01 and n02 released. Bootstrap seeds both
        from their gate results."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "transitive-bootstrap")

        _write_gate_result(tmp_path, "phase_01_gate", status="pass")
        _write_gate_result(tmp_path, "phase_02_gate", status="pass")

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=3)

        assert "n01_call_analysis" in bootstrapped
        assert "n02_concept_refinement" in bootstrapped
        assert ctx.get_node_state("n01_call_analysis") == "released"
        assert ctx.get_node_state("n02_concept_refinement") == "released"


# ===========================================================================
# 3. Fail-closed behavior
# ===========================================================================


class TestFailClosedBehavior:
    """Bootstrap must not mark nodes released without sufficient evidence."""

    def test_no_gate_result_file_leaves_pending(self, tmp_path: Path):
        """When no gate result artifact exists, the upstream node stays pending."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "no-evidence")

        # No gate result written — n01 should stay pending.
        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == []
        assert ctx.get_node_state("n01_call_analysis") == "pending"

    def test_failing_gate_result_leaves_pending(self, tmp_path: Path):
        """When the gate result shows status=fail, the node stays pending."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "fail-evidence")

        _write_gate_result(tmp_path, "phase_01_gate", status="fail")

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == []
        assert ctx.get_node_state("n01_call_analysis") == "pending"

    def test_corrupt_gate_result_leaves_pending(self, tmp_path: Path):
        """When the gate result file is corrupt JSON, the node stays pending."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "corrupt-evidence")

        # Write corrupt JSON at the canonical path.
        rel_path = GATE_RESULT_PATHS["phase_01_gate"]
        abs_path = tmp_path / _TIER4_ROOT_REL / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text("{not valid json", encoding="utf-8")

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == []
        assert ctx.get_node_state("n01_call_analysis") == "pending"

    def test_absent_evidence_causes_abort(self, tmp_path: Path):
        """Without evidence, phase 2 aborts because n01 is still pending."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "abort-no-evidence")

        # No gate result written, no bootstrap.
        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        sched = DAGScheduler(
            graph, ctx, tmp_path,
            manifest_path=manifest_path,
            phase=2,
        )

        with pytest.raises(RunAbortedError) as exc_info:
            sched.run()

        summary = exc_info.value.summary
        assert summary.overall_status == "aborted"
        assert summary.node_states["n01_call_analysis"] == "pending"

    def test_partial_evidence_only_bootstraps_proven(self, tmp_path: Path):
        """When running phase 3 but only phase_01_gate evidence exists,
        only n01 is bootstrapped; n02 stays pending."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "partial-evidence")

        _write_gate_result(tmp_path, "phase_01_gate", status="pass")
        # phase_02_gate evidence is absent.

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=3)

        assert bootstrapped == ["n01_call_analysis"]
        assert ctx.get_node_state("n01_call_analysis") == "released"
        assert ctx.get_node_state("n02_concept_refinement") == "pending"


# ===========================================================================
# 4. No false release from artifact presence alone
# ===========================================================================


class TestNoFalseRelease:
    """Phase output files without a passing gate result must not trigger bootstrap."""

    def test_phase_output_files_without_gate_result(self, tmp_path: Path):
        """Even if phase output directory has files, without a passing
        gate_result.json, the node is not bootstrapped."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "false-release")

        # Write some phase output files (but no gate result).
        phase_dir = (
            tmp_path / _TIER4_ROOT_REL / "phase_outputs" / "phase1_call_analysis"
        )
        phase_dir.mkdir(parents=True, exist_ok=True)
        (phase_dir / "summary.json").write_text('{"phase": 1}', encoding="utf-8")

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == []
        assert ctx.get_node_state("n01_call_analysis") == "pending"

    def test_gate_result_with_wrong_status_key(self, tmp_path: Path):
        """A gate result file with status='partial' (not 'pass') must not
        trigger bootstrap."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "wrong-status")

        _write_gate_result(tmp_path, "phase_01_gate", status="partial")

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == []


# ===========================================================================
# 5. Multi-upstream generality
# ===========================================================================


class TestMultiUpstreamGenerality:
    """Later phases with multiple upstream dependencies are handled correctly."""

    def test_diamond_dag_phase4_all_upstream_bootstrapped(self, tmp_path: Path):
        """Phase 4 depends on n02 and n03 (both depend on n01).
        All three must be bootstrapped from evidence."""
        manifest_path = _write_manifest(tmp_path, _diamond_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "diamond-all")

        _write_gate_result(tmp_path, "phase_01_gate", status="pass")
        _write_gate_result(tmp_path, "phase_02_gate", status="pass")
        _write_gate_result(tmp_path, "phase_03_gate", status="pass")

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=4)

        assert "n01_call_analysis" in bootstrapped
        assert "n02_concept_refinement" in bootstrapped
        assert "n03_wp_design" in bootstrapped
        assert len(bootstrapped) == 3

        # n04 should not be bootstrapped (it's the target phase).
        assert ctx.get_node_state("n04_gantt_milestones") == "pending"

    def test_diamond_dag_partial_evidence_blocks(self, tmp_path: Path):
        """If one upstream branch lacks evidence, n04 cannot proceed."""
        manifest_path = _write_manifest(tmp_path, _diamond_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "diamond-partial")

        _write_gate_result(tmp_path, "phase_01_gate", status="pass")
        _write_gate_result(tmp_path, "phase_02_gate", status="pass")
        # phase_03_gate is absent — n03 stays pending.

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=4)

        assert "n01_call_analysis" in bootstrapped
        assert "n02_concept_refinement" in bootstrapped
        assert "n03_wp_design" not in bootstrapped

        # n04 should not be ready (n03 is still pending).
        assert not graph.is_ready("n04_gantt_milestones", ctx)

    def test_diamond_dag_dispatch_with_full_evidence(self, tmp_path: Path):
        """With all upstream evidence, phase 4 dispatches successfully."""
        manifest_path = _write_manifest(tmp_path, _diamond_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "diamond-dispatch")

        _write_gate_result(tmp_path, "phase_01_gate", status="pass")
        _write_gate_result(tmp_path, "phase_02_gate", status="pass")
        _write_gate_result(tmp_path, "phase_03_gate", status="pass")
        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=4)

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
                phase=4,
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert summary.dispatched_nodes == ["n04_gantt_milestones"]


# ===========================================================================
# 6. Non-phase-scoped runs unchanged
# ===========================================================================


class TestNonPhaseScopedUnchanged:
    """Full DAG execution without --phase must behave exactly as before."""

    def test_full_dag_all_pass(self, tmp_path: Path):
        """Full DAG run dispatches all nodes in order."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "full-dag-ok")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_PASS):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
            )
            summary = sched.run()

        assert summary.overall_status == "pass"
        assert len(summary.dispatched_nodes) == 3
        assert summary.phase_scope is None

    def test_full_dag_stall_no_bootstrap_effect(self, tmp_path: Path):
        """Full DAG with n01 blocked still stalls downstream, even if
        a gate result artifact exists on disk."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "full-dag-stall")

        # Even with evidence on disk, full-DAG mode does not bootstrap.
        _write_gate_result(tmp_path, "phase_01_gate", status="pass")

        with patch("runner.dag_scheduler.evaluate_gate", return_value=_GATE_FAIL):
            sched = DAGScheduler(
                graph, ctx, tmp_path,
                manifest_path=manifest_path,
            )
            with pytest.raises(RunAbortedError) as exc_info:
                sched.run()

        summary = exc_info.value.summary
        assert summary.overall_status == "aborted"
        # n01 should have been dispatched (it's ready as entry node).
        # n02, n03 should be stalled.
        stalled_ids = [s["node_id"] for s in summary.stalled_nodes]
        assert "n02_concept_refinement" in stalled_ids
        assert "n03_wp_design" in stalled_ids

    def test_bootstrap_returns_empty_without_phase(self, tmp_path: Path):
        """Calling bootstrap for a non-existent phase returns empty list."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "no-phase")

        # Phase 99 has no nodes.
        result = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=99)
        assert result == []


# ===========================================================================
# 7. RunContext.load_or_initialize edge cases
# ===========================================================================


class TestLoadOrInitialize:
    """RunContext.load_or_initialize covers both paths."""

    def test_new_run_id_creates_fresh_context(self, tmp_path: Path):
        ctx = RunContext.load_or_initialize(tmp_path, "brand-new-id")
        assert ctx.run_id == "brand-new-id"
        assert ctx.get_node_state("anything") == "pending"

    def test_none_run_id_generates_uuid(self, tmp_path: Path):
        ctx = RunContext.load_or_initialize(tmp_path, None)
        assert ctx.run_id is not None
        assert len(ctx.run_id) > 0

    def test_preserves_all_node_states(self, tmp_path: Path):
        """All states (released, blocked_at_entry, blocked_at_exit, etc.)
        are preserved on reload."""
        ctx1 = RunContext.initialize(tmp_path, "multi-state")
        ctx1.set_node_state("n01", "released")
        ctx1.set_node_state("n02", "blocked_at_entry")
        ctx1.set_node_state("n03", "blocked_at_exit")
        ctx1.set_node_state("n04", "hard_block_upstream")
        ctx1.save()

        ctx2 = RunContext.load_or_initialize(tmp_path, "multi-state")
        assert ctx2.get_node_state("n01") == "released"
        assert ctx2.get_node_state("n02") == "blocked_at_entry"
        assert ctx2.get_node_state("n03") == "blocked_at_exit"
        assert ctx2.get_node_state("n04") == "hard_block_upstream"

    def test_bootstrap_skips_non_pending_nodes(self, tmp_path: Path):
        """Bootstrap only modifies 'pending' nodes. Already-released or
        blocked nodes from an existing run are untouched."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)

        # Existing run with n01 already released.
        ctx = RunContext.initialize(tmp_path, "skip-non-pending")
        ctx.set_node_state("n01_call_analysis", "released")
        ctx.save()

        # Write evidence (should be ignored since n01 is already released).
        _write_gate_result(tmp_path, "phase_01_gate", status="pass")

        ctx = RunContext.load_or_initialize(tmp_path, "skip-non-pending")
        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        # n01 was already released, so not in bootstrapped list.
        assert bootstrapped == []
        assert ctx.get_node_state("n01_call_analysis") == "released"
