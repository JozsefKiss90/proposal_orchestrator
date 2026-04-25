"""
Unit tests for Step 10 — runner/run_context.py.

All tests operate in temporary directories; no live repository state is
read or mutated.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from runner.run_context import (
    PHASE_8_NODE_IDS,
    REUSE_POLICY_FILENAME,
    RUN_MANIFEST_FILENAME,
    RUNS_DIR_REL,
    RunContext,
)
from runner.versions import CONSTITUTION_VERSION, LIBRARY_VERSION, MANIFEST_VERSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_dir(repo_root: Path, run_id: str) -> Path:
    return repo_root / RUNS_DIR_REL / run_id


def _manifest_path(repo_root: Path, run_id: str) -> Path:
    return _run_dir(repo_root, run_id) / RUN_MANIFEST_FILENAME


def _policy_path(repo_root: Path, run_id: str) -> Path:
    return _run_dir(repo_root, run_id) / REUSE_POLICY_FILENAME


# ---------------------------------------------------------------------------
# initialize — happy path
# ---------------------------------------------------------------------------


class TestRunContextInitialize:
    def test_initialize_creates_manifest_file(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-001")
        assert _manifest_path(tmp_path, "run-001").exists()

    def test_initialize_creates_reuse_policy_file(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-001")
        assert _policy_path(tmp_path, "run-001").exists()

    def test_initialize_manifest_contains_run_id(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-abc")
        manifest = json.loads(_manifest_path(tmp_path, "run-abc").read_text())
        assert manifest["run_id"] == "run-abc"

    def test_initialize_manifest_contains_version_fields(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-abc")
        manifest = json.loads(_manifest_path(tmp_path, "run-abc").read_text())
        assert manifest["manifest_version"] == MANIFEST_VERSION
        assert manifest["library_version"] == LIBRARY_VERSION
        assert manifest["constitution_version"] == CONSTITUTION_VERSION

    def test_initialize_manifest_contains_node_states(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-abc")
        manifest = json.loads(_manifest_path(tmp_path, "run-abc").read_text())
        assert "node_states" in manifest
        assert isinstance(manifest["node_states"], dict)

    def test_initialize_manifest_contains_created_at(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-abc")
        manifest = json.loads(_manifest_path(tmp_path, "run-abc").read_text())
        assert "created_at" in manifest
        assert manifest["created_at"]  # non-empty

    def test_initialize_reuse_policy_content(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-001")
        policy = json.loads(_policy_path(tmp_path, "run-001").read_text())
        assert policy["reuse_policy_for_run"] == "run-001"
        assert policy["approved_artifacts"] == []

    def test_initialize_auto_uuid_when_run_id_none(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path)
        assert ctx.run_id
        # Must be a valid UUID
        uuid.UUID(ctx.run_id)
        assert _manifest_path(tmp_path, ctx.run_id).exists()

    def test_initialize_explicit_run_id_used(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="explicit-id-xyz")
        assert ctx.run_id == "explicit-id-xyz"


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------


class TestRunContextLoad:
    def test_load_returns_matching_run_id(self, tmp_path: Path) -> None:
        RunContext.initialize(tmp_path, run_id="run-load-01")
        loaded = RunContext.load(tmp_path, "run-load-01")
        assert loaded.run_id == "run-load-01"

    def test_load_missing_manifest_raises_FileNotFoundError(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            RunContext.load(tmp_path, "nonexistent-run-id")

    def test_load_restores_node_states(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-restore")
        ctx.set_node_state("n01", "released")
        ctx.save()

        loaded = RunContext.load(tmp_path, "run-restore")
        assert loaded.get_node_state("n01") == "released"

    def test_load_creates_empty_reuse_policy_when_file_missing(
        self, tmp_path: Path
    ) -> None:
        """If reuse_policy.json is absent, load() creates an empty structure."""
        RunContext.initialize(tmp_path, run_id="run-nopolicy")
        # Delete the policy file manually
        _policy_path(tmp_path, "run-nopolicy").unlink()

        loaded = RunContext.load(tmp_path, "run-nopolicy")
        assert not loaded.is_artifact_approved("/some/path")


# ---------------------------------------------------------------------------
# Node state
# ---------------------------------------------------------------------------


class TestRunContextNodeState:
    def test_get_node_state_default_is_pending(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-ns")
        assert ctx.get_node_state("n01") == "pending"

    def test_set_and_get_node_state(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-ns2")
        ctx.set_node_state("n03", "blocked_at_entry")
        assert ctx.get_node_state("n03") == "blocked_at_entry"

    def test_set_node_state_multiple_nodes_independent(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-ns3")
        ctx.set_node_state("n01", "released")
        ctx.set_node_state("n02", "blocked_at_exit")
        assert ctx.get_node_state("n01") == "released"
        assert ctx.get_node_state("n02") == "blocked_at_exit"
        # Unset nodes still default to pending
        assert ctx.get_node_state("n99") == "pending"


# ---------------------------------------------------------------------------
# HARD_BLOCK propagation
# ---------------------------------------------------------------------------


class TestRunContextHardBlock:
    def test_mark_hard_block_downstream_sets_all_phase8_nodes(
        self, tmp_path: Path
    ) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-hb")
        ctx.mark_hard_block_downstream()
        for node_id in PHASE_8_NODE_IDS:
            assert ctx.get_node_state(node_id) == "hard_block_upstream"

    def test_mark_hard_block_downstream_sets_reason_in_manifest(
        self, tmp_path: Path
    ) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-hb2")
        ctx.mark_hard_block_downstream(reason="TEST_HARD_BLOCK")
        manifest = ctx.to_dict()
        assert manifest["hard_block_reason"] == "TEST_HARD_BLOCK"
        assert manifest["hard_block_gate"] == "gate_09_budget_consistency"

    def test_mark_hard_block_downstream_default_reason(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-hb3")
        ctx.mark_hard_block_downstream()
        manifest = ctx.to_dict()
        assert manifest["hard_block_reason"] == "HARD_BLOCK_UPSTREAM"

    def test_phase8_node_ids_are_expected_set(self) -> None:
        assert PHASE_8_NODE_IDS == frozenset(
            {
                "n08a_excellence_drafting",
                "n08b_impact_drafting",
                "n08c_implementation_drafting",
                "n08d_assembly",
                "n08e_evaluator_review",
                "n08f_revision",
            }
        )


# ---------------------------------------------------------------------------
# Reuse policy / artifact approval
# ---------------------------------------------------------------------------


class TestRunContextArtifactApproval:
    def test_is_artifact_approved_false_for_unknown(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-ap")
        assert not ctx.is_artifact_approved("/some/artifact.json")

    def test_is_artifact_approved_true_when_listed(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-ap2")
        # Manually inject an approved artifact into the private policy
        ctx._reuse_policy["approved_artifacts"].append(
            "/some/approved/artifact.json"
        )
        assert ctx.is_artifact_approved("/some/approved/artifact.json")

    def test_is_artifact_approved_false_for_partial_match(
        self, tmp_path: Path
    ) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-ap3")
        ctx._reuse_policy["approved_artifacts"].append("/approved/art.json")
        assert not ctx.is_artifact_approved("/approved/other.json")


# ---------------------------------------------------------------------------
# save / persistence
# ---------------------------------------------------------------------------


class TestRunContextSave:
    def test_save_persists_node_state_change(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-save")
        ctx.set_node_state("n05", "running")
        ctx.save()

        reloaded = RunContext.load(tmp_path, "run-save")
        assert reloaded.get_node_state("n05") == "running"

    def test_save_persists_hard_block(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-save2")
        ctx.mark_hard_block_downstream()
        ctx.save()

        reloaded = RunContext.load(tmp_path, "run-save2")
        assert reloaded.get_node_state("n08a_excellence_drafting") == "hard_block_upstream"

    def test_to_dict_returns_copy(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="run-dict")
        d = ctx.to_dict()
        d["run_id"] = "tampered"
        # Original must be unchanged
        assert ctx.run_id == "run-dict"
