"""
ST-1 — Phase 3-6 staleness judged by content, not wall-clock mtime.

A Tier-3 promote that rewrites ``architecture_inputs/*.json`` (adding a
provenance field, or re-serialising with identical bytes) bumps their mtimes
past the phase 3-6 gate results' ``evaluated_at``.  The pre-ST-1 freshness check
rejected such gates as stale purely on mtime, even when the content the gate
evaluated was unchanged.

ST-1 makes ``is_gate_fresh`` confirm mtime-suspect inputs by CONTENT: an input
whose current fingerprint matches the fingerprint recorded in the gate result's
``input_artifact_fingerprints`` at evaluation time is genuinely unchanged and
therefore fresh, regardless of mtime.  A genuinely changed input (fingerprint
differs) is still stale, and missing fingerprint evidence fails closed.

Test groups:
  1. ``is_gate_fresh`` unit — content-identical/newer-mtime accepted;
     changed-content rejected; fail-closed on absent/partial fingerprints;
     directory inputs.
  2. Bootstrap end-to-end — both directions through
     ``bootstrap_phase_prerequisites``.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runner.dag_scheduler import (
    ManifestGraph,
    bootstrap_phase_prerequisites,
)
from runner.fingerprints import MISSING_FINGERPRINT, fingerprint_path
from runner.gate_result_registry import GATE_RESULT_PATHS, GATE_RESULT_SCHEMA_ID
from runner.predicates.gate_pass_predicates import is_gate_fresh
from runner.run_context import RunContext
from runner.runtime_models import AgentResult
from runner.upstream_inputs import UPSTREAM_REQUIRED_INPUTS

_TIER4_ROOT_REL = "docs/tier4_orchestration_state"
_OLD_EVAL = "2020-01-01T00:00:00+00:00"  # far past → any just-written file is mtime-suspect
_RA_TARGET = "runner.dag_scheduler.run_agent"
_SUCCESS_AGENT = AgentResult(status="success", can_evaluate_exit_gate=True)


@pytest.fixture(autouse=True)
def _mock_run_agent():
    with patch(_RA_TARGET, return_value=_SUCCESS_AGENT):
        yield


def _write_file(repo_root: Path, rel_path: str, content: str) -> Path:
    abs_path = repo_root / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    return abs_path


def _record_fps(repo_root: Path, rel_paths: list[str]) -> dict[str, str]:
    """Fingerprint each path as the gate evaluator would at evaluation time."""
    return {rel: fingerprint_path(repo_root / rel) for rel in rel_paths}


def _write_gate_result(
    repo_root: Path,
    gate_id: str,
    *,
    evaluated_at: str = _OLD_EVAL,
    input_artifact_fingerprints: dict | None = None,
    status: str = "pass",
    include_fp_field: bool = True,
) -> Path:
    rel_path = GATE_RESULT_PATHS.get(gate_id, f"gate_results/{gate_id}.json")
    abs_path = repo_root / _TIER4_ROOT_REL / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_id": GATE_RESULT_SCHEMA_ID,
        "gate_id": gate_id,
        "status": status,
        "run_id": "prior-run-id",
        "manifest_version": "1.1",
        "library_version": "1.0",
        "constitution_version": "1.0",
        "evaluated_at": evaluated_at,
        "input_fingerprint": "sha256:combined",
    }
    if include_fp_field:
        result["input_artifact_fingerprints"] = input_artifact_fingerprints or {}
    abs_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
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
             "to_node": "n03_wp_design", "gate_condition": "phase_02_gate"},
        ],
    }


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


_PHASE03_INPUTS = UPSTREAM_REQUIRED_INPUTS["phase_03_gate"]


# ===========================================================================
# 1. is_gate_fresh unit — content-based staleness
# ===========================================================================


class TestContentIdenticalNewerMtimeIsFresh:
    """A newer-mtime input whose content matches the recorded fingerprint is FRESH."""

    def test_all_inputs_content_identical_is_fresh(self, tmp_path: Path) -> None:
        # Write inputs "now" (mtime far after _OLD_EVAL → all mtime-suspect).
        for rel in _PHASE03_INPUTS:
            _write_file(tmp_path, rel, '{"substantive": "content"}')
        # Gate result records the fingerprint of exactly this content.
        fps = _record_fps(tmp_path, _PHASE03_INPUTS)
        data = {"evaluated_at": _OLD_EVAL, "input_artifact_fingerprints": fps}

        fresh, reason, stale = is_gate_fresh("phase_03_gate", data, tmp_path)

        assert fresh is True, f"expected fresh, got stale: {reason}"
        assert reason is None
        assert stale == []

    def test_reserialised_identical_bytes_is_fresh(self, tmp_path: Path) -> None:
        """The motivating case: a promote rewrites the file with identical bytes."""
        rel = _PHASE03_INPUTS[0]
        _write_file(tmp_path, rel, '{"a": 1}')
        fps = _record_fps(tmp_path, [rel])
        # Rewrite with byte-identical content → mtime bumps, content unchanged.
        _write_file(tmp_path, rel, '{"a": 1}')
        data = {"evaluated_at": _OLD_EVAL, "input_artifact_fingerprints": fps}

        fresh, _, stale = is_gate_fresh("phase_03_gate", data, tmp_path)
        assert fresh is True
        assert stale == []


class TestChangedContentIsStale:
    """A newer-mtime input whose content differs from the recorded fingerprint is STALE."""

    def test_changed_content_is_stale(self, tmp_path: Path) -> None:
        for rel in _PHASE03_INPUTS:
            _write_file(tmp_path, rel, '{"original": true}')
        fps = _record_fps(tmp_path, _PHASE03_INPUTS)
        # A genuine change to one input after evaluation.
        changed_rel = _PHASE03_INPUTS[1]
        _write_file(tmp_path, changed_rel, '{"original": false, "changed": true}')
        data = {"evaluated_at": _OLD_EVAL, "input_artifact_fingerprints": fps}

        fresh, reason, stale = is_gate_fresh("phase_03_gate", data, tmp_path)

        assert fresh is False
        assert reason is not None
        assert changed_rel in stale
        # The two unchanged inputs must NOT be reported stale.
        assert all(p == changed_rel for p in stale)

    def test_newly_appeared_input_is_stale(self, tmp_path: Path) -> None:
        """An input that was MISSING at evaluation but now exists is a content change."""
        rel = _PHASE03_INPUTS[0]
        # Recorded fingerprint says the file was missing at evaluation time.
        data = {
            "evaluated_at": _OLD_EVAL,
            "input_artifact_fingerprints": {rel: MISSING_FINGERPRINT},
        }
        _write_file(tmp_path, rel, '{"now": "present"}')

        fresh, _, stale = is_gate_fresh("phase_03_gate", data, tmp_path)
        assert fresh is False
        assert rel in stale


class TestFailClosedOnMissingEvidence:
    """Absent fingerprint evidence must fail closed (stale), never accept."""

    def test_absent_fingerprint_field_is_stale(self, tmp_path: Path) -> None:
        """Gate result predating the fingerprint field → mtime behaviour (stale)."""
        for rel in _PHASE03_INPUTS:
            _write_file(tmp_path, rel, "{}")
        data = {"evaluated_at": _OLD_EVAL}  # no input_artifact_fingerprints

        fresh, _, stale = is_gate_fresh("phase_03_gate", data, tmp_path)
        assert fresh is False
        assert len(stale) == len(_PHASE03_INPUTS)

    def test_suspect_path_missing_from_map_is_stale(self, tmp_path: Path) -> None:
        """A mtime-suspect input absent from the recorded map cannot be confirmed."""
        for rel in _PHASE03_INPUTS:
            _write_file(tmp_path, rel, "{}")
        # Record fingerprints for all but one input.
        fps = _record_fps(tmp_path, _PHASE03_INPUTS[:-1])
        unmapped = _PHASE03_INPUTS[-1]
        data = {"evaluated_at": _OLD_EVAL, "input_artifact_fingerprints": fps}

        fresh, _, stale = is_gate_fresh("phase_03_gate", data, tmp_path)
        assert fresh is False
        assert unmapped in stale
        # The mapped-and-matching inputs are not reported stale.
        assert stale == [unmapped]


class TestMtimeFastPathUnchanged:
    """When no input postdates evaluation, freshness holds without content checks."""

    def test_no_suspects_is_fresh_without_fingerprints(self, tmp_path: Path) -> None:
        """Future evaluated_at → no input is mtime-suspect → fresh even with no map."""
        for rel in _PHASE03_INPUTS:
            _write_file(tmp_path, rel, "{}")
        data = {"evaluated_at": "2099-01-01T00:00:00+00:00"}

        fresh, reason, stale = is_gate_fresh("phase_03_gate", data, tmp_path)
        assert fresh is True
        assert stale == []


class TestDirectoryInputContentStaleness:
    """Directory inputs are content-checked by their direct-child NAME set.

    Per decision-log D6: ``fingerprint_path`` hashes a directory as the sorted
    set of its direct child names (non-recursive), matching what the gate
    evaluator recorded and the pre-ST-1 directory-mtime behaviour.  So a
    directory freshness check detects added/removed children but NOT an
    in-place change to a child file's bytes under an unchanged name.  This is a
    strict relaxation (never stricter than before), documented here so the
    granularity is explicit and not mistaken for a general content guarantee.
    """

    _DIR_REL = "docs/integrations/lump_sum_budget_planner/received"

    def test_dir_unchanged_children_newer_mtime_is_fresh(self, tmp_path: Path) -> None:
        _write_file(tmp_path, f"{self._DIR_REL}/response.json", '{"budget": 1}')
        fps = {self._DIR_REL: fingerprint_path(tmp_path / self._DIR_REL)}
        # Mutate a child's CONTENT (not the child set) → dir child-name set
        # unchanged → fresh (D6 granularity; same as the recorded fingerprint).
        _write_file(tmp_path, f"{self._DIR_REL}/response.json", '{"budget": 999}')
        data = {"evaluated_at": _OLD_EVAL, "input_artifact_fingerprints": fps}

        fresh, _, stale = is_gate_fresh("gate_09_budget_consistency", data, tmp_path)
        assert fresh is True
        assert stale == []

    def test_dir_new_child_is_stale(self, tmp_path: Path) -> None:
        _write_file(tmp_path, f"{self._DIR_REL}/response.json", '{"budget": 1}')
        fps = {self._DIR_REL: fingerprint_path(tmp_path / self._DIR_REL)}
        # Add a new child → directory fingerprint changes.
        _write_file(tmp_path, f"{self._DIR_REL}/extra.json", '{"unexpected": true}')
        data = {"evaluated_at": _OLD_EVAL, "input_artifact_fingerprints": fps}

        fresh, _, stale = is_gate_fresh("gate_09_budget_consistency", data, tmp_path)
        assert fresh is False
        assert self._DIR_REL in stale


# ===========================================================================
# 2. Bootstrap end-to-end — both directions
# ===========================================================================


class TestBootstrapContentStaleness:
    """bootstrap_phase_prerequisites honours content-based freshness."""

    def _setup(self, tmp_path: Path):
        manifest_path = _write_manifest(tmp_path, _three_phase_manifest())
        graph = ManifestGraph.load(manifest_path)
        return graph

    def test_content_identical_newer_mtime_bootstraps(self, tmp_path: Path) -> None:
        graph = self._setup(tmp_path)
        ctx = RunContext.initialize(tmp_path, "content-fresh")

        # phase_01_gate upstream input, written "now" (mtime > _OLD_EVAL).
        p01_inputs = UPSTREAM_REQUIRED_INPUTS["phase_01_gate"]
        for rel in p01_inputs:
            _write_file(tmp_path, rel, '{"selected": "call"}')
        fps = _record_fps(tmp_path, p01_inputs)
        _write_gate_result(
            tmp_path, "phase_01_gate",
            evaluated_at=_OLD_EVAL, input_artifact_fingerprints=fps,
        )

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert "n01_call_analysis" in bootstrapped
        assert ctx.get_node_state("n01_call_analysis") == "released"

    def test_changed_content_stays_pending(self, tmp_path: Path) -> None:
        graph = self._setup(tmp_path)
        ctx = RunContext.initialize(tmp_path, "content-stale")

        p01_inputs = UPSTREAM_REQUIRED_INPUTS["phase_01_gate"]
        for rel in p01_inputs:
            _write_file(tmp_path, rel, '{"selected": "original"}')
        fps = _record_fps(tmp_path, p01_inputs)
        # A genuine change after the recorded fingerprint.
        for rel in p01_inputs:
            _write_file(tmp_path, rel, '{"selected": "REBOUND"}')
        _write_gate_result(
            tmp_path, "phase_01_gate",
            evaluated_at=_OLD_EVAL, input_artifact_fingerprints=fps,
        )

        bootstrapped = bootstrap_phase_prerequisites(ctx, graph, tmp_path, phase=2)

        assert bootstrapped == []
        assert ctx.get_node_state("n01_call_analysis") == "pending"
