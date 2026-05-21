"""
Tests for bootstrap freshness enforcement — upstream gate staleness detection.

Validates the invariant:
    A node must not execute if its upstream gates would fail exit-gate
    freshness validation.

The bootstrap (``bootstrap_phase_prerequisites``) must reject stale upstream
gate results before seeding nodes as ``released``.  This prevents the scenario
where a node executes successfully but then fails at exit-gate evaluation due
to stale upstream dependencies.

Test groups:
  1. ``is_gate_fresh`` — unit tests for the reusable freshness function.
  2. Bootstrap rejects stale gates — integration tests proving that bootstrap
     refuses to accept gate results with upstream inputs modified after
     ``evaluated_at``.
  3. Bootstrap accepts fresh gates — proves that the fix does not break
     valid continuation scenarios.
  4. End-to-end invariant — stale upstream causes abort, not exit-gate failure.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
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
from runner.predicates.gate_pass_predicates import is_gate_fresh
from runner.run_context import RunContext
from runner.runtime_models import AgentResult
from runner.upstream_inputs import UPSTREAM_REQUIRED_INPUTS

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
    evaluated_at: str = "2026-04-16T00:00:00+00:00",
    **extra: object,
) -> Path:
    """Write a canonical gate result artifact to Tier 4."""
    rel_path = GATE_RESULT_PATHS.get(gate_id)
    if rel_path is None:
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
        "evaluated_at": evaluated_at,
        "input_fingerprint": "sha256:abc123",
        **extra,
    }
    abs_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return abs_path


def _write_upstream_input(repo_root: Path, rel_path: str, content: str = "{}") -> Path:
    """Write an upstream input file at the given repo-relative path."""
    abs_path = repo_root / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
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


# ===========================================================================
# 1. is_gate_fresh — unit tests
# ===========================================================================


class TestIsGateFresh:
    """Unit tests for the reusable freshness function."""

    def test_fresh_when_no_upstream_inputs_exist(self, tmp_path: Path) -> None:
        """Gate is fresh when no upstream input paths exist on disk."""
        data = {"evaluated_at": "2026-04-16T00:00:00+00:00"}
        fresh, reason, stale = is_gate_fresh("phase_02_gate", data, tmp_path)
        assert fresh is True
        assert reason is None
        assert stale == []

    def test_fresh_when_inputs_predate_evaluation(self, tmp_path: Path) -> None:
        """Gate is fresh when all upstream inputs are older than evaluated_at."""
        # Write upstream inputs FIRST
        for rel_path in UPSTREAM_REQUIRED_INPUTS.get("phase_02_gate", []):
            _write_upstream_input(tmp_path, rel_path, '{"test": true}')

        # Small pause to ensure evaluated_at is strictly later
        time.sleep(0.05)
        eval_time = datetime.now(timezone.utc).isoformat()

        data = {"evaluated_at": eval_time}
        fresh, reason, stale = is_gate_fresh("phase_02_gate", data, tmp_path)
        assert fresh is True
        assert reason is None
        assert stale == []

    def test_stale_when_input_postdates_evaluation(self, tmp_path: Path) -> None:
        """Gate is stale when an upstream input was modified after evaluated_at."""
        # Set evaluated_at to a past time
        eval_time = "2026-04-16T00:00:00+00:00"
        data = {"evaluated_at": eval_time}

        # Write upstream input NOW (mtime will be far after 2026-04-16)
        # But wait — the test filesystem mtime will be "now" in real time,
        # which is before 2026-04-16 in the future. Use a different approach:
        # set evaluated_at to a very old time.
        old_eval = "2020-01-01T00:00:00+00:00"
        data = {"evaluated_at": old_eval}

        for rel_path in UPSTREAM_REQUIRED_INPUTS.get("phase_02_gate", []):
            _write_upstream_input(tmp_path, rel_path, '{"test": true}')

        fresh, reason, stale = is_gate_fresh("phase_02_gate", data, tmp_path)
        assert fresh is False
        assert reason is not None
        assert "stale" in reason
        assert len(stale) > 0

    def test_stale_returns_specific_paths(self, tmp_path: Path) -> None:
        """Stale result includes the specific paths that are newer."""
        old_eval = "2020-01-01T00:00:00+00:00"
        data = {"evaluated_at": old_eval}

        upstream_paths = UPSTREAM_REQUIRED_INPUTS.get("phase_02_gate", [])
        for rel_path in upstream_paths:
            _write_upstream_input(tmp_path, rel_path, '{"test": true}')

        fresh, _, stale = is_gate_fresh("phase_02_gate", data, tmp_path)
        assert fresh is False
        # All written paths should appear in stale list
        for rel_path in upstream_paths:
            assert rel_path in stale

    def test_missing_evaluated_at_is_not_fresh(self) -> None:
        """Gate with no evaluated_at is not fresh."""
        fresh, reason, stale = is_gate_fresh("phase_02_gate", {}, None)
        assert fresh is False
        assert "no evaluated_at" in reason

    def test_unparseable_evaluated_at_is_not_fresh(self) -> None:
        """Gate with unparseable evaluated_at is not fresh."""
        data = {"evaluated_at": "not-a-timestamp"}
        fresh, reason, stale = is_gate_fresh("phase_02_gate", data, None)
        assert fresh is False
        assert "unparseable" in reason

    def test_gate_without_upstream_inputs_is_always_fresh(self, tmp_path: Path) -> None:
        """A gate_id not in UPSTREAM_REQUIRED_INPUTS is considered fresh."""
        data = {"evaluated_at": "2020-01-01T00:00:00+00:00"}
        fresh, reason, stale = is_gate_fresh(
            "nonexistent_gate_id", data, tmp_path
        )
        assert fresh is True


# ===========================================================================
# 2. Bootstrap rejects stale gates
# ===========================================================================


class TestBootstrapRejectsStaleGates:
    """Bootstrap must refuse to accept gate results with stale upstream inputs."""

    def test_stale_gate_leaves_node_pending(self, tmp_path: Path) -> None:
        """When upstream inputs are newer than the gate's evaluated_at,
        the node is NOT bootstrapped — it stays pending."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "stale-reject")

        # Write gate result with old evaluated_at
        _write_gate_result(
            tmp_path, "phase_01_gate", status="pass",
            evaluated_at="2020-01-01T00:00:00+00:00",
        )

        # Write upstream inputs that are "newer" (written now)
        for rel_path in UPSTREAM_REQUIRED_INPUTS.get("phase_01_gate", []):
            _write_upstream_input(tmp_path, rel_path, '{"test": true}')

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == []
        assert ctx.get_node_state("n01_call_analysis") == "pending"

    def test_stale_gate_causes_abort(self, tmp_path: Path) -> None:
        """Stale upstream gate → node not bootstrapped → phase aborts."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "stale-abort")

        _write_gate_result(
            tmp_path, "phase_01_gate", status="pass",
            evaluated_at="2020-01-01T00:00:00+00:00",
        )
        for rel_path in UPSTREAM_REQUIRED_INPUTS.get("phase_01_gate", []):
            _write_upstream_input(tmp_path, rel_path, '{"test": true}')

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
        assert "n02_concept_refinement" not in summary.dispatched_nodes

    def test_one_stale_one_fresh_partial_bootstrap(self, tmp_path: Path) -> None:
        """When bootstrapping phase 3, if phase_01_gate is fresh but
        phase_02_gate is stale, only n01 is bootstrapped."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "partial-fresh")

        # phase_01_gate: fresh (no upstream inputs exist)
        _write_gate_result(tmp_path, "phase_01_gate", status="pass")

        # phase_02_gate: stale (upstream inputs exist and are newer)
        _write_gate_result(
            tmp_path, "phase_02_gate", status="pass",
            evaluated_at="2020-01-01T00:00:00+00:00",
        )
        for rel_path in UPSTREAM_REQUIRED_INPUTS.get("phase_02_gate", []):
            _write_upstream_input(tmp_path, rel_path, '{"test": true}')

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=3)

        assert "n01_call_analysis" in bootstrapped
        assert "n02_concept_refinement" not in bootstrapped
        assert ctx.get_node_state("n01_call_analysis") == "released"
        assert ctx.get_node_state("n02_concept_refinement") == "pending"


# ===========================================================================
# 3. Bootstrap accepts fresh gates (no regression)
# ===========================================================================


class TestBootstrapAcceptsFreshGates:
    """Fresh gate results are still accepted — the fix must not break this."""

    def test_fresh_gate_bootstraps_normally(self, tmp_path: Path) -> None:
        """Gate result with no stale inputs is accepted as before."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "fresh-ok")

        # Write gate result (no upstream inputs on disk → fresh by default)
        _write_gate_result(tmp_path, "phase_01_gate", status="pass")

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == ["n01_call_analysis"]
        assert ctx.get_node_state("n01_call_analysis") == "released"

    def test_fresh_gate_with_old_inputs(self, tmp_path: Path) -> None:
        """Gate result is fresh when all upstream inputs predate evaluated_at."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "inputs-older")

        # Write upstream inputs first
        for rel_path in UPSTREAM_REQUIRED_INPUTS.get("phase_01_gate", []):
            _write_upstream_input(tmp_path, rel_path, '{"test": true}')

        # Small pause then write gate result with a future evaluated_at
        time.sleep(0.05)
        eval_time = datetime.now(timezone.utc).isoformat()
        _write_gate_result(
            tmp_path, "phase_01_gate", status="pass",
            evaluated_at=eval_time,
        )

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == ["n01_call_analysis"]

    def test_fresh_gate_records_acceptance(self, tmp_path: Path) -> None:
        """Accepted upstream gate is recorded for gate_pass_recorded continuity."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "acceptance-recorded")

        _write_gate_result(tmp_path, "phase_01_gate", status="pass")
        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        accepted = ctx.get_accepted_upstream_gate("phase_01_gate")
        assert accepted is not None
        assert accepted["original_run_id"] == "prior-run-id"
        assert accepted["status"] == "pass"


# ===========================================================================
# 4. End-to-end invariant enforcement
# ===========================================================================


class TestEndToEndInvariant:
    """After the fix, exit gate must NOT discover new freshness failures.

    If a node runs, its upstream gates are guaranteed valid by bootstrap.
    """

    def test_node_does_not_execute_with_stale_upstream(self, tmp_path: Path) -> None:
        """BEFORE fix: Phase 2 would run → fail at exit.
        AFTER fix: Phase 2 does NOT run — scheduler reports blocked/aborted."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "invariant-test")

        # phase_01_gate passed but inputs were modified after
        _write_gate_result(
            tmp_path, "phase_01_gate", status="pass",
            evaluated_at="2020-01-01T00:00:00+00:00",
        )
        for rel_path in UPSTREAM_REQUIRED_INPUTS.get("phase_01_gate", []):
            _write_upstream_input(tmp_path, rel_path, '{"test": true}')

        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        sched = DAGScheduler(
            graph, ctx, tmp_path,
            manifest_path=manifest_path,
            phase=2,
        )

        with pytest.raises(RunAbortedError) as exc_info:
            sched.run()

        summary = exc_info.value.summary
        # n02 must NOT have been dispatched
        assert "n02_concept_refinement" not in summary.dispatched_nodes
        # The run aborted because n01 was not released
        assert summary.overall_status == "aborted"
        assert summary.node_states["n01_call_analysis"] == "pending"
