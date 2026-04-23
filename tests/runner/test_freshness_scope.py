"""
Tests for freshness-scope refinement — helper artifacts vs source-of-truth inputs.

Validates that:
  1. Phase 1 gate reuse is NOT invalidated by regeneration of call slices
     (generated helpers in call_extracts/) when no real sources changed.
  2. Phase 2 gate freshness still fails when project_brief source files change.
  3. Phase 3 gate freshness still fails when concept_refinement_summary changes.
  4. Bootstrap and exit-gate freshness remain consistent after the refinement.
  5. The invariant is preserved: no node executes with stale upstream gates.
  6. Directory paths that contain only externally-placed content (e.g.
     integrations/received/) still correctly invalidate their gates.
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
_RA_TARGET = "runner.dag_scheduler.run_agent"
_SUCCESS_AGENT = AgentResult(status="success", can_evaluate_exit_gate=True)
_TIER4_ROOT_REL = "docs/tier4_orchestration_state"


@pytest.fixture(autouse=True)
def _mock_run_agent():
    with patch(_RA_TARGET, return_value=_SUCCESS_AGENT):
        yield


def _write_gate_result(
    repo_root: Path,
    gate_id: str,
    status: str = "pass",
    evaluated_at: str | None = None,
    **extra: object,
) -> Path:
    rel_path = GATE_RESULT_PATHS.get(gate_id)
    if rel_path is None:
        rel_path = f"gate_results/{gate_id}.json"
    abs_path = repo_root / _TIER4_ROOT_REL / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    if evaluated_at is None:
        evaluated_at = datetime.now(timezone.utc).isoformat()
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


def _write_file(repo_root: Path, rel_path: str, content: str = "{}") -> Path:
    abs_path = repo_root / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    return abs_path


def _three_phase_manifest() -> dict:
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {"node_id": "n01_call_analysis", "phase_number": 1,
             "phase_id": "phase_01", "agent": "a1", "skills": [],
             "exit_gate": "phase_01_gate", "terminal": False},
            {"node_id": "n02_concept_refinement", "phase_number": 2,
             "phase_id": "phase_02", "agent": "a2", "skills": [],
             "exit_gate": "phase_02_gate", "terminal": False},
            {"node_id": "n03_wp_design", "phase_number": 3,
             "phase_id": "phase_03", "agent": "a3", "skills": [],
             "exit_gate": "phase_03_gate", "terminal": True},
        ],
        "edge_registry": [
            {"edge_id": "e01_to_02", "from_node": "n01_call_analysis",
             "to_node": "n02_concept_refinement",
             "gate_condition": "phase_01_gate"},
            {"edge_id": "e02_to_03", "from_node": "n02_concept_refinement",
             "to_node": "n03_wp_design",
             "gate_condition": "phase_02_gate"},
        ],
    }


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


# ===========================================================================
# 1. Phase 1 gate NOT invalidated by call slice regeneration
# ===========================================================================


class TestPhase1NotInvalidatedByHelperArtifacts:
    """Phase 1 gate must remain fresh when only generated helpers change."""

    def test_call_extracts_dir_not_in_phase01_freshness(self) -> None:
        """call_extracts directory is not a freshness input for phase_01_gate."""
        paths = UPSTREAM_REQUIRED_INPUTS.get("phase_01_gate", [])
        assert not any("call_extracts" in p for p in paths), (
            "call_extracts/ should not be in phase_01_gate freshness inputs "
            "because it contains generated call slices"
        )

    def test_work_programmes_dir_not_in_phase01_freshness(self) -> None:
        """work_programmes directory is not a freshness input for phase_01_gate."""
        paths = UPSTREAM_REQUIRED_INPUTS.get("phase_01_gate", [])
        assert not any("work_programmes" in p for p in paths), (
            "work_programmes/ dir should not be in phase_01_gate freshness "
            "inputs because dir mtime is sensitive to sibling operations"
        )

    def test_selected_call_still_tracked(self) -> None:
        """selected_call.json IS still a freshness input for phase_01_gate."""
        paths = UPSTREAM_REQUIRED_INPUTS.get("phase_01_gate", [])
        assert any("selected_call.json" in p for p in paths)

    def test_phase01_fresh_despite_slice_regeneration(self, tmp_path: Path) -> None:
        """Phase 1 gate stays fresh when a call slice is regenerated.

        Simulates the scenario: Phase 1 ran and passed, then on a new run
        generate_call_slice() writes a new *.slice.json into call_extracts/.
        Phase 1 gate must NOT be invalidated by this.
        """
        # Write selected_call.json FIRST (the only tracked input)
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/call_binding/selected_call.json",
            '{"topic_code": "TEST-01", "work_programme": "cluster_digital"}',
        )
        time.sleep(0.05)

        # Gate evaluated AFTER the source input
        eval_time = datetime.now(timezone.utc).isoformat()
        data = {"evaluated_at": eval_time}

        time.sleep(0.05)
        # Simulate call slice regeneration (writing into call_extracts dir)
        _write_file(
            tmp_path,
            "docs/tier2b_topic_and_call_sources/call_extracts/TEST-01.slice.json",
            '{"sliced_by": "runner/call_slicer.py"}',
        )

        # Gate must still be fresh
        fresh, reason, stale = is_gate_fresh("phase_01_gate", data, tmp_path)
        assert fresh is True, (
            f"Phase 1 gate should be fresh despite slice regeneration: {reason}"
        )

    def test_phase01_bootstrap_survives_slice_regeneration(self, tmp_path: Path) -> None:
        """Bootstrap accepts phase_01_gate even when call slice was regenerated."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "slice-regen")

        # Write selected_call.json first
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/call_binding/selected_call.json",
            '{"topic_code": "TEST-01"}',
        )
        time.sleep(0.05)

        # Write gate result AFTER source input
        eval_time = datetime.now(timezone.utc).isoformat()
        _write_gate_result(tmp_path, "phase_01_gate", evaluated_at=eval_time)

        time.sleep(0.05)
        # Regenerate call slice (touches call_extracts dir)
        _write_file(
            tmp_path,
            "docs/tier2b_topic_and_call_sources/call_extracts/TEST-01.slice.json",
            '{"sliced_by": "runner/call_slicer.py"}',
        )

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)
        assert "n01_call_analysis" in bootstrapped


# ===========================================================================
# 2. Phase 2 gate still invalidated by project_brief changes
# ===========================================================================


class TestPhase2InvalidatedBySourceChanges:
    """Phase 2 gate must be invalidated when project_brief source files change."""

    def test_concept_note_change_invalidates_phase02(self, tmp_path: Path) -> None:
        """Modifying concept_note.md after gate evaluation invalidates phase_02_gate."""
        # Write all Phase 2 upstream inputs first
        _write_file(
            tmp_path,
            "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/concept_note.md",
            "# Original concept",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/project_summary.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/strategic_positioning.md",
            "# Original positioning",
        )
        time.sleep(0.05)
        eval_time = datetime.now(timezone.utc).isoformat()
        time.sleep(0.05)

        # Modify concept_note.md AFTER evaluation
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/concept_note.md",
            "# Revised concept with new objectives",
        )

        data = {"evaluated_at": eval_time}
        fresh, reason, stale = is_gate_fresh("phase_02_gate", data, tmp_path)
        assert fresh is False
        assert any("concept_note.md" in p for p in stale)

    def test_project_summary_change_invalidates_phase02(self, tmp_path: Path) -> None:
        """Modifying project_summary.json after gate evaluation invalidates."""
        _write_file(
            tmp_path,
            "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/project_summary.json",
        )
        time.sleep(0.05)
        eval_time = datetime.now(timezone.utc).isoformat()
        time.sleep(0.05)

        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/project_summary.json",
            '{"title": "Changed Title"}',
        )

        data = {"evaluated_at": eval_time}
        fresh, reason, stale = is_gate_fresh("phase_02_gate", data, tmp_path)
        assert fresh is False
        assert any("project_summary.json" in p for p in stale)

    def test_phase02_fresh_when_no_sources_changed(self, tmp_path: Path) -> None:
        """Phase 2 gate stays fresh when sources predate evaluation."""
        _write_file(
            tmp_path,
            "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/concept_note.md",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/project_summary.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/project_brief/strategic_positioning.md",
        )
        time.sleep(0.05)
        eval_time = datetime.now(timezone.utc).isoformat()

        data = {"evaluated_at": eval_time}
        fresh, reason, stale = is_gate_fresh("phase_02_gate", data, tmp_path)
        assert fresh is True


# ===========================================================================
# 3. Phase 3 gate still invalidated by concept_refinement_summary changes
# ===========================================================================


class TestPhase3InvalidatedByUpstreamPhaseOutput:
    """Phase 3 gate invalidated when Phase 2 canonical output changes."""

    def test_concept_refinement_summary_change_invalidates(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
        )
        time.sleep(0.05)
        eval_time = datetime.now(timezone.utc).isoformat()
        time.sleep(0.05)

        # Phase 2 reruns and produces new concept_refinement_summary.json
        _write_file(
            tmp_path,
            "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
            '{"updated": true}',
        )

        data = {"evaluated_at": eval_time}
        fresh, reason, stale = is_gate_fresh("phase_03_gate", data, tmp_path)
        assert fresh is False
        assert any("concept_refinement_summary.json" in p for p in stale)

    def test_workpackage_seed_change_invalidates(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
        )
        time.sleep(0.05)
        eval_time = datetime.now(timezone.utc).isoformat()
        time.sleep(0.05)

        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json",
            '{"new_wp": true}',
        )

        data = {"evaluated_at": eval_time}
        fresh, reason, stale = is_gate_fresh("phase_03_gate", data, tmp_path)
        assert fresh is False
        assert any("workpackage_seed.json" in p for p in stale)


# ===========================================================================
# 4. Bootstrap and exit-gate freshness remain consistent
# ===========================================================================


class TestBootstrapExitGateConsistency:
    """Invariant: bootstrap freshness and exit-gate freshness must agree."""

    def test_selected_call_change_blocks_both(self, tmp_path: Path) -> None:
        """If selected_call.json changes, both bootstrap AND is_gate_fresh reject."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)

        # Write gate result with old evaluated_at
        _write_gate_result(
            tmp_path, "phase_01_gate",
            evaluated_at="2020-01-01T00:00:00+00:00",
        )
        # Write selected_call.json NOW (newer than gate)
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/call_binding/selected_call.json",
            '{"topic_code": "NEW-CALL"}',
        )

        # is_gate_fresh rejects
        data = {"evaluated_at": "2020-01-01T00:00:00+00:00"}
        fresh, _, _ = is_gate_fresh("phase_01_gate", data, tmp_path)
        assert fresh is False

        # bootstrap also rejects
        ctx = RunContext.initialize(tmp_path, "consistency-test")
        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)
        assert "n01_call_analysis" not in bootstrapped


# ===========================================================================
# 5. Freshness-scope model: explicit path classifications
# ===========================================================================


class TestFreshnessPathClassifications:
    """Verify the structural correctness of the refined UPSTREAM_REQUIRED_INPUTS."""

    def test_no_directory_paths_in_phase01(self) -> None:
        """Phase 1 gate should have no directory paths (all specific files)."""
        for p in UPSTREAM_REQUIRED_INPUTS.get("phase_01_gate", []):
            assert not p.endswith("/"), f"Unexpected trailing slash: {p}"
            # Heuristic: directory paths don't have file extensions
            assert "." in p.split("/")[-1], (
                f"Suspected directory path without extension in "
                f"phase_01_gate: {p}"
            )

    def test_no_directory_paths_in_entry_gate(self) -> None:
        """Entry gate should have no directory paths."""
        for p in UPSTREAM_REQUIRED_INPUTS.get("gate_01_source_integrity", []):
            assert "." in p.split("/")[-1], (
                f"Suspected directory path in gate_01_source_integrity: {p}"
            )

    def test_phase02_tracks_specific_project_brief_files(self) -> None:
        """phase_02_gate should track individual project_brief files,
        not the directory."""
        paths = UPSTREAM_REQUIRED_INPUTS.get("phase_02_gate", [])
        assert not any(p.rstrip("/") == "docs/tier3_project_instantiation/project_brief" for p in paths), (
            "project_brief/ directory should not be in phase_02_gate; "
            "use specific files instead"
        )
        assert any("concept_note.md" in p for p in paths)
        assert any("project_summary.json" in p for p in paths)

    def test_integration_dirs_still_tracked_for_budget_gate(self) -> None:
        """Budget gate integration dirs (externally placed) are still tracked."""
        paths = UPSTREAM_REQUIRED_INPUTS.get("gate_09_budget_consistency", [])
        assert any("received" in p for p in paths)
        assert any("validation" in p for p in paths)

    def test_phase05_unchanged(self) -> None:
        """Phase 5 gate inputs should be unchanged (all specific files)."""
        paths = UPSTREAM_REQUIRED_INPUTS.get("phase_05_gate", [])
        assert any("outcomes.json" in p for p in paths)
        assert any("impacts.json" in p for p in paths)
        assert any("expected_outcomes.json" in p for p in paths)
        assert any("expected_impacts.json" in p for p in paths)
        assert any("concept_refinement_summary.json" in p for p in paths)


# ===========================================================================
# 6. End-to-end: no regression to bootstrap invariant
# ===========================================================================


class TestNoInvariantRegression:
    """The invariant 'no node executes with stale upstream gates' still holds."""

    def test_stale_source_still_blocks_dispatch(self, tmp_path: Path) -> None:
        """When selected_call.json is modified after Phase 1 gate,
        Phase 2 must NOT dispatch."""
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        ctx = RunContext.initialize(tmp_path, "invariant-recheck")

        _write_gate_result(
            tmp_path, "phase_01_gate",
            evaluated_at="2020-01-01T00:00:00+00:00",
        )
        _write_file(
            tmp_path,
            "docs/tier3_project_instantiation/call_binding/selected_call.json",
        )

        bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        sched = DAGScheduler(
            graph, ctx, tmp_path, manifest_path=manifest_path, phase=2,
        )
        with pytest.raises(RunAbortedError) as exc_info:
            sched.run()

        summary = exc_info.value.summary
        assert "n02_concept_refinement" not in summary.dispatched_nodes
        assert summary.overall_status == "aborted"
