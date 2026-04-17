"""
Tests for the continuation contract consistency fix.

Verifies that phase-scoped continuation bootstrap and gate_pass_recorded
are internally consistent: upstream gate evidence accepted by bootstrap
is also accepted by downstream gate_pass_recorded predicates.

Coverage:
  A. New-run continuation succeeds consistently
  B. Existing-run preservation
  C. No accepted continuation state → fail
  D. Failing prior upstream gate → fail
  E. No provenance falsification
  F. Non-continuation same-run behavior unchanged
  G. RunContext accepted_upstream_gates API
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from runner.dag_scheduler import (
    ManifestGraph,
    bootstrap_phase_prerequisites,
)
from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.predicates.gate_pass_predicates import (
    _check_continuation_acceptance,
    gate_pass_recorded,
)
from runner.predicates.types import (
    STALE_UPSTREAM_MISMATCH,
)
from runner.run_context import RunContext
from runner.versions import (
    CONSTITUTION_VERSION,
    LIBRARY_VERSION,
    MANIFEST_VERSION,
)


# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

_TIER4_ROOT_REL = "docs/tier4_orchestration_state"
_PRIOR_RUN_ID = "prior-run-aaaa-bbbb-cccc-dddddddddddd"
_CURRENT_RUN_ID = "current-run-1111-2222-3333-444444444444"
_FUTURE_TS = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _write_gate_result(
    repo_root: Path,
    gate_id: str,
    *,
    run_id: str = _PRIOR_RUN_ID,
    status: str = "pass",
) -> Path:
    rel_path = GATE_RESULT_PATHS.get(gate_id)
    if rel_path is None:
        rel_path = f"gate_results/{gate_id}.json"
    abs_path = repo_root / _TIER4_ROOT_REL / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "gate_id": gate_id,
        "status": status,
        "run_id": run_id,
        "manifest_version": MANIFEST_VERSION,
        "library_version": LIBRARY_VERSION,
        "constitution_version": CONSTITUTION_VERSION,
        "evaluated_at": _FUTURE_TS,
        "input_fingerprint": "sha256:abc123",
    }
    abs_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return abs_path


def _three_phase_manifest() -> dict:
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
# A. New-run continuation succeeds consistently
# ===========================================================================


class TestNewRunContinuationConsistent:
    """Prior Phase 1 gate passed under run A; new run B bootstraps upstream;
    downstream gate_pass_recorded(phase_01_gate) must succeed under run B."""

    def test_gate_pass_accepts_bootstrapped_evidence(self, tmp_path: Path):
        """After bootstrap, gate_pass_recorded succeeds for the accepted gate."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, _CURRENT_RUN_ID)

        # Phase 1 passed under a prior run.
        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )

        # Bootstrap accepts the evidence.
        bootstrapped = bootstrap_phase_prerequisites(
            ctx, graph, tmp_path, phase=2
        )
        assert "n01_call_analysis" in bootstrapped

        # Now gate_pass_recorded should succeed for phase_01_gate
        # even though the artifact has _PRIOR_RUN_ID, not _CURRENT_RUN_ID.
        tier4 = tmp_path / _TIER4_ROOT_REL
        result = gate_pass_recorded(
            "phase_01_gate",
            _CURRENT_RUN_ID,
            tier4,
            repo_root=tmp_path,
        )
        assert result.passed is True, (
            f"Expected pass but got: {result.reason}"
        )

    def test_transitive_bootstrap_gates_accepted(self, tmp_path: Path):
        """Phase 3 bootstrap accepts both phase_01_gate and phase_02_gate;
        gate_pass_recorded succeeds for both."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, _CURRENT_RUN_ID)

        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )
        _write_gate_result(
            tmp_path, "phase_02_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )

        bootstrapped = bootstrap_phase_prerequisites(
            ctx, graph, tmp_path, phase=3
        )
        assert len(bootstrapped) == 2

        tier4 = tmp_path / _TIER4_ROOT_REL
        for gate_id in ["phase_01_gate", "phase_02_gate"]:
            result = gate_pass_recorded(
                gate_id, _CURRENT_RUN_ID, tier4, repo_root=tmp_path
            )
            assert result.passed is True, (
                f"{gate_id}: expected pass but got: {result.reason}"
            )


# ===========================================================================
# B. Existing-run preservation
# ===========================================================================


class TestExistingRunPreservation:
    """Existing run with same run_id: gate_pass_recorded works as before."""

    def test_same_run_id_still_passes(self, tmp_path: Path):
        """When the gate artifact has the same run_id, it passes normally."""
        tier4 = tmp_path / "tier4"
        gate_data = {
            "gate_id": "phase_01_gate",
            "status": "pass",
            "run_id": _CURRENT_RUN_ID,
            "manifest_version": MANIFEST_VERSION,
            "library_version": LIBRARY_VERSION,
            "constitution_version": CONSTITUTION_VERSION,
            "evaluated_at": _FUTURE_TS,
            "input_fingerprint": "sha256:abc",
        }
        path = tier4 / GATE_RESULT_PATHS["phase_01_gate"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(gate_data), encoding="utf-8")

        result = gate_pass_recorded(
            "phase_01_gate", _CURRENT_RUN_ID, tier4, repo_root=tmp_path
        )
        assert result.passed is True


# ===========================================================================
# C. No accepted continuation state → fail
# ===========================================================================


class TestNoAcceptedContinuationFails:
    """Prior gate exists but was NOT accepted by bootstrap → still fails."""

    def test_prior_gate_without_bootstrap_fails(self, tmp_path: Path):
        """A prior-run gate artifact that was never accepted by bootstrap
        must still fail gate_pass_recorded with STALE_UPSTREAM_MISMATCH."""
        # Create a current-run RunContext (but don't bootstrap).
        ctx = RunContext.initialize(tmp_path, _CURRENT_RUN_ID)

        # Write a gate artifact from a prior run.
        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )

        tier4 = tmp_path / _TIER4_ROOT_REL
        result = gate_pass_recorded(
            "phase_01_gate", _CURRENT_RUN_ID, tier4, repo_root=tmp_path
        )

        assert result.passed is False
        assert result.failure_category == STALE_UPSTREAM_MISMATCH
        assert _PRIOR_RUN_ID in (result.details or {}).get(
            "recorded_run_id", ""
        )

    def test_accepted_wrong_original_run_id_fails(self, tmp_path: Path):
        """If the acceptance record has a different original_run_id than
        the artifact, it must still fail."""
        ctx = RunContext.initialize(tmp_path, _CURRENT_RUN_ID)
        # Record acceptance for a DIFFERENT prior run than the artifact.
        ctx.record_accepted_upstream_gate(
            "phase_01_gate",
            original_run_id="some-other-run-id",
            evidence_path="irrelevant",
        )
        ctx.save()

        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )

        tier4 = tmp_path / _TIER4_ROOT_REL
        result = gate_pass_recorded(
            "phase_01_gate", _CURRENT_RUN_ID, tier4, repo_root=tmp_path
        )

        assert result.passed is False
        assert result.failure_category == STALE_UPSTREAM_MISMATCH

    def test_no_repo_root_fails_closed(self, tmp_path: Path):
        """When repo_root is None, continuation check cannot proceed;
        run_id mismatch must fail as before."""
        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )

        tier4 = tmp_path / _TIER4_ROOT_REL
        result = gate_pass_recorded(
            "phase_01_gate", _CURRENT_RUN_ID, tier4, repo_root=None
        )

        assert result.passed is False
        assert result.failure_category == STALE_UPSTREAM_MISMATCH


# ===========================================================================
# D. Failing prior upstream gate → fail
# ===========================================================================


class TestFailingPriorGateFails:
    """Prior upstream gate with status != pass must not be accepted."""

    def test_failing_prior_gate_not_bootstrapped(self, tmp_path: Path):
        """Bootstrap does not accept status=fail evidence, so
        gate_pass_recorded has no acceptance record and fails."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, _CURRENT_RUN_ID)

        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="fail"
        )

        bootstrapped = bootstrap_phase_prerequisites(
            ctx, graph, tmp_path, phase=2
        )
        assert bootstrapped == []

        tier4 = tmp_path / _TIER4_ROOT_REL
        result = gate_pass_recorded(
            "phase_01_gate", _CURRENT_RUN_ID, tier4, repo_root=tmp_path
        )
        # Fails because: (a) no acceptance record and (b) status != pass
        assert result.passed is False


# ===========================================================================
# E. No provenance falsification
# ===========================================================================


class TestProvenancePreserved:
    """Original upstream artifact run_id remains unchanged;
    acceptance record is a separate, traceable entry."""

    def test_original_artifact_unchanged(self, tmp_path: Path):
        """After bootstrap, the gate result artifact on disk still has
        the original run_id — it is not overwritten."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, _CURRENT_RUN_ID)

        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )
        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        # Read the artifact back — run_id must still be the prior run's.
        artifact_path = (
            tmp_path
            / _TIER4_ROOT_REL
            / GATE_RESULT_PATHS["phase_01_gate"]
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert artifact["run_id"] == _PRIOR_RUN_ID

    def test_acceptance_record_is_distinct(self, tmp_path: Path):
        """The acceptance record in RunContext is separate from the
        gate artifact and carries the original_run_id for auditability."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, _CURRENT_RUN_ID)

        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )
        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        accepted = ctx.get_accepted_upstream_gate("phase_01_gate")
        assert accepted is not None
        assert accepted["original_run_id"] == _PRIOR_RUN_ID
        assert accepted["status"] == "pass"
        assert "accepted_at" in accepted
        assert "evidence_path" in accepted

    def test_acceptance_record_persisted_to_disk(self, tmp_path: Path):
        """The acceptance record survives save/load round-trip."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, _CURRENT_RUN_ID)

        _write_gate_result(
            tmp_path, "phase_01_gate", run_id=_PRIOR_RUN_ID, status="pass"
        )
        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        # Reload from disk.
        ctx2 = RunContext.load(tmp_path, _CURRENT_RUN_ID)
        accepted = ctx2.get_accepted_upstream_gate("phase_01_gate")
        assert accepted is not None
        assert accepted["original_run_id"] == _PRIOR_RUN_ID


# ===========================================================================
# F. Non-continuation same-run behavior unchanged
# ===========================================================================


class TestSameRunBehaviorUnchanged:
    """Ordinary same-run gate_pass_recorded must work exactly as before."""

    def test_same_run_pass(self, tmp_path: Path):
        tier4 = tmp_path / "tier4"
        gate_data = {
            "gate_id": "phase_01_gate",
            "status": "pass",
            "run_id": "same-run",
            "manifest_version": MANIFEST_VERSION,
            "library_version": LIBRARY_VERSION,
            "constitution_version": CONSTITUTION_VERSION,
            "evaluated_at": _FUTURE_TS,
            "input_fingerprint": "sha256:ok",
        }
        path = tier4 / GATE_RESULT_PATHS["phase_01_gate"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(gate_data), encoding="utf-8")

        result = gate_pass_recorded("phase_01_gate", "same-run", tier4)
        assert result.passed is True

    def test_same_run_status_fail(self, tmp_path: Path):
        tier4 = tmp_path / "tier4"
        gate_data = {
            "gate_id": "phase_01_gate",
            "status": "fail",
            "run_id": "same-run",
            "manifest_version": MANIFEST_VERSION,
            "library_version": LIBRARY_VERSION,
            "constitution_version": CONSTITUTION_VERSION,
            "evaluated_at": _FUTURE_TS,
            "input_fingerprint": "sha256:ok",
        }
        path = tier4 / GATE_RESULT_PATHS["phase_01_gate"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(gate_data), encoding="utf-8")

        result = gate_pass_recorded("phase_01_gate", "same-run", tier4)
        assert result.passed is False

    def test_run_id_mismatch_without_continuation_fails(
        self, tmp_path: Path
    ):
        """Plain run_id mismatch (no continuation context) still fails."""
        tier4 = tmp_path / "tier4"
        gate_data = {
            "gate_id": "phase_01_gate",
            "status": "pass",
            "run_id": "old-run",
            "manifest_version": MANIFEST_VERSION,
            "library_version": LIBRARY_VERSION,
            "constitution_version": CONSTITUTION_VERSION,
            "evaluated_at": _FUTURE_TS,
            "input_fingerprint": "sha256:ok",
        }
        path = tier4 / GATE_RESULT_PATHS["phase_01_gate"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(gate_data), encoding="utf-8")

        result = gate_pass_recorded(
            "phase_01_gate", "new-run", tier4, repo_root=tmp_path
        )
        assert result.passed is False
        assert result.failure_category == STALE_UPSTREAM_MISMATCH


# ===========================================================================
# G. RunContext accepted_upstream_gates API
# ===========================================================================


class TestRunContextAcceptedUpstreamGates:
    """Unit tests for the RunContext continuation acceptance API."""

    def test_no_accepted_gates_returns_none(self, tmp_path: Path):
        ctx = RunContext.initialize(tmp_path, "test-run")
        assert ctx.get_accepted_upstream_gate("phase_01_gate") is None

    def test_record_and_retrieve(self, tmp_path: Path):
        ctx = RunContext.initialize(tmp_path, "test-run")
        ctx.record_accepted_upstream_gate(
            "phase_01_gate", "prior-run", "path/to/evidence.json"
        )
        record = ctx.get_accepted_upstream_gate("phase_01_gate")
        assert record is not None
        assert record["original_run_id"] == "prior-run"
        assert record["evidence_path"] == "path/to/evidence.json"
        assert record["status"] == "pass"
        assert "accepted_at" in record

    def test_round_trip_persistence(self, tmp_path: Path):
        ctx = RunContext.initialize(tmp_path, "test-run")
        ctx.record_accepted_upstream_gate(
            "phase_02_gate", "run-A", "evidence/path.json"
        )
        ctx.save()

        ctx2 = RunContext.load(tmp_path, "test-run")
        record = ctx2.get_accepted_upstream_gate("phase_02_gate")
        assert record is not None
        assert record["original_run_id"] == "run-A"

    def test_multiple_gates_recorded(self, tmp_path: Path):
        ctx = RunContext.initialize(tmp_path, "test-run")
        ctx.record_accepted_upstream_gate("phase_01_gate", "run-A", "p1")
        ctx.record_accepted_upstream_gate("phase_02_gate", "run-A", "p2")
        ctx.save()

        ctx2 = RunContext.load(tmp_path, "test-run")
        assert ctx2.get_accepted_upstream_gate("phase_01_gate") is not None
        assert ctx2.get_accepted_upstream_gate("phase_02_gate") is not None
        assert ctx2.get_accepted_upstream_gate("phase_03_gate") is None


# ===========================================================================
# H. _check_continuation_acceptance unit tests
# ===========================================================================


class TestCheckContinuationAcceptance:
    """Direct unit tests for the internal acceptance check function."""

    def test_returns_false_without_repo_root(self):
        assert _check_continuation_acceptance(
            "phase_01_gate", "run-B", "run-A", None
        ) is False

    def test_returns_false_without_run_context(self, tmp_path: Path):
        assert _check_continuation_acceptance(
            "phase_01_gate", "nonexistent-run", "run-A", tmp_path
        ) is False

    def test_returns_false_without_acceptance_record(self, tmp_path: Path):
        ctx = RunContext.initialize(tmp_path, "run-B")
        assert _check_continuation_acceptance(
            "phase_01_gate", "run-B", "run-A", tmp_path
        ) is False

    def test_returns_true_with_matching_acceptance(self, tmp_path: Path):
        ctx = RunContext.initialize(tmp_path, "run-B")
        ctx.record_accepted_upstream_gate(
            "phase_01_gate", "run-A", "evidence.json"
        )
        ctx.save()

        assert _check_continuation_acceptance(
            "phase_01_gate", "run-B", "run-A", tmp_path
        ) is True

    def test_returns_false_with_wrong_original_run_id(self, tmp_path: Path):
        ctx = RunContext.initialize(tmp_path, "run-B")
        ctx.record_accepted_upstream_gate(
            "phase_01_gate", "run-X", "evidence.json"
        )
        ctx.save()

        assert _check_continuation_acceptance(
            "phase_01_gate", "run-B", "run-A", tmp_path
        ) is False
