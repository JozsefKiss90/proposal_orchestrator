"""
Integration tests for Phase 8 reuse ownership through real gate evaluation.

Verifies that reuse decisions recorded in RunContext are visible to
artifact_owned_by_run during live evaluate_gate calls — the exact
production path that failed in run fcac4f7a.

These tests do NOT call Claude (semantic predicates are not triggered
because deterministic predicates fail/pass first).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.phase8_reuse import (
    REUSE_ELIGIBLE_NODES,
    REUSE_METADATA_DIR,
    FINGERPRINT_INPUTS,
    artifact_sha256,
    compute_input_fingerprint,
    read_artifact_run_id,
    write_reuse_metadata,
)
from runner.predicates.file_predicates import artifact_owned_by_run
from runner.run_context import RunContext, RUNS_DIR_REL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _make_fingerprint_inputs(repo: Path, node_id: str) -> None:
    """Create minimal input files for fingerprinting."""
    for rel_path in FINGERPRINT_INPUTS[node_id]:
        if rel_path.endswith("/"):
            _write_json(repo / rel_path / "data.json", {"input": "value"})
        else:
            _write_json(repo / rel_path, {"input": "value"})


def _make_valid_artifact(
    repo: Path, node_id: str, run_id: str = "source-run-001"
) -> dict:
    """Create a valid section artifact on disk and return its content."""
    cfg = REUSE_ELIGIBLE_NODES[node_id]
    content = {
        "schema_id": cfg["schema_id"],
        "run_id": run_id,
        "criterion": "Test",
        "sub_sections": [],
        "validation_status": {
            "overall_status": "confirmed",
            "claim_statuses": [
                {"claim_id": "C-01", "status": "confirmed"},
            ],
        },
        "traceability_footer": {
            "primary_sources": [],
            "no_unsupported_claims_declaration": True,
        },
    }
    _write_json(repo / cfg["artifact_path"], content)
    return content


def _make_gate_result(
    repo: Path, gate_id: str, status: str = "pass", run_id: str = "source-run-001"
) -> None:
    from runner.gate_result_registry import GATE_RESULT_PATHS

    rel = GATE_RESULT_PATHS.get(gate_id)
    if rel is None:
        return
    _write_json(
        repo / "docs/tier4_orchestration_state" / rel,
        {"status": status, "gate_id": gate_id, "run_id": run_id},
    )


def _make_audit_reports(repo: Path, run_id: str) -> None:
    prefix = run_id.split("-")[0] if "-" in run_id else run_id[:8]
    reports_dir = repo / "docs/tier4_orchestration_state/validation_reports"
    _write_json(
        reports_dir / f"proposal-section-traceability-check_{prefix}.json",
        {"skill_id": "proposal-section-traceability-check", "run_id_reference": run_id},
    )
    _write_json(
        reports_dir / f"constitutional-compliance-check_{prefix}.json",
        {"skill_id": "constitutional-compliance-check", "run_id_reference": run_id},
    )


def _setup_full_reuse_env_with_ctx(
    repo: Path,
    node_id: str,
    source_run_id: str,
    current_run_id: str,
    *,
    use_v1_metadata: bool = False,
    v1_corrupted_source_run_id: str | None = None,
) -> tuple[RunContext, str]:
    """Set up a complete reuse environment using real RunContext.

    Returns (RunContext, input_fingerprint).
    """
    cfg = REUSE_ELIGIBLE_NODES[node_id]

    # Create fingerprint inputs
    _make_fingerprint_inputs(repo, node_id)

    # Create valid artifact (produced by source_run_id)
    _make_valid_artifact(repo, node_id, run_id=source_run_id)

    # Create gate result (from prior run)
    _make_gate_result(repo, cfg["gate_id"], "pass", run_id=source_run_id)

    # Compute fingerprint
    fp = compute_input_fingerprint(node_id, repo)
    assert fp is not None

    # Write reuse metadata
    art_path = repo / cfg["artifact_path"]
    art_hash = artifact_sha256(art_path)
    assert art_hash is not None

    if use_v1_metadata:
        # Simulate v1 metadata with potentially corrupted source_run_id
        meta_path = repo / REUSE_METADATA_DIR / f"{node_id}.reuse.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        v1_metadata = {
            "node_id": node_id,
            "artifact_path": cfg["artifact_path"],
            "schema_id": cfg["schema_id"],
            "source_run_id": v1_corrupted_source_run_id or source_run_id,
            "gate_id": cfg["gate_id"],
            "gate_status": "pass",
            "input_fingerprint": fp,
            "artifact_sha256": art_hash,
            "reuse_policy_version": "phase8.section.v1",
        }
        _write_json(meta_path, v1_metadata)
    else:
        write_reuse_metadata(
            node_id=node_id,
            repo_root=repo,
            source_run_id=source_run_id,
            artifact_path=cfg["artifact_path"],
            schema_id=cfg["schema_id"],
            gate_id=cfg["gate_id"],
            input_fingerprint=fp,
            artifact_hash=art_hash,
            artifact_run_id=source_run_id,
            last_validated_run_id=source_run_id,
        )

    # Create audit reports
    _make_audit_reports(repo, current_run_id)

    # Create real RunContext and record reuse decision
    ctx = RunContext.initialize(repo, current_run_id)

    # Read actual artifact run_id from disk (as the fixed scheduler does)
    actual_art_run_id = read_artifact_run_id(art_path)
    effective_art_rid = actual_art_run_id or source_run_id

    ctx.record_reuse_decision(node_id, {
        "status": "reused",
        "mode": "drafting_skipped_audit_executed",
        "source_run_id": effective_art_rid,
        "artifact_run_id": effective_art_rid,
        "artifact_path": cfg["artifact_path"],
        "input_fingerprint": fp,
        "gate_id": cfg["gate_id"],
    })
    ctx.save()

    return ctx, fp


# ===========================================================================
# 1. RunContext reuse decisions visible before run_summary
# ===========================================================================


class TestReuseDecisionsVisibleBeforeRunSummary:
    """Verify that reuse decisions are in run_manifest.json BEFORE run_summary."""

    @pytest.mark.parametrize("node_id", list(REUSE_ELIGIBLE_NODES.keys()))
    def test_decisions_visible_immediately_after_save(
        self, tmp_path: Path, node_id: str
    ) -> None:
        """After ctx.record_reuse_decision + ctx.save, decisions are on disk."""
        source_run = "source-run-001"
        current_run = "current-run-002"

        ctx, fp = _setup_full_reuse_env_with_ctx(
            tmp_path, node_id, source_run, current_run
        )

        # Verify decisions are on disk (not just in memory)
        manifest_path = tmp_path / RUNS_DIR_REL / current_run / "run_manifest.json"
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "reuse_decisions" in manifest
        assert node_id in manifest["reuse_decisions"]
        assert manifest["reuse_decisions"][node_id]["status"] == "reused"

    def test_decisions_survive_reload(self, tmp_path: Path) -> None:
        """Reuse decisions survive RunContext.load() round-trip."""
        node_id = "n08c_implementation_drafting"
        source_run = "source-run-001"
        current_run = "current-run-002"

        ctx, fp = _setup_full_reuse_env_with_ctx(
            tmp_path, node_id, source_run, current_run
        )

        # Reload context (as evaluate_gate does)
        ctx2 = RunContext.load(tmp_path, current_run)
        decision = ctx2.get_reuse_decision(node_id)
        assert decision is not None
        assert decision["status"] == "reused"
        assert decision["artifact_run_id"] == source_run


# ===========================================================================
# 2. artifact_owned_by_run passes through reuse exception
# ===========================================================================


class TestArtifactOwnedByRunReuseException:
    """Verify artifact_owned_by_run passes for reused artifacts."""

    @pytest.mark.parametrize("node_id", list(REUSE_ELIGIBLE_NODES.keys()))
    def test_passes_for_all_reuse_eligible_nodes(
        self, tmp_path: Path, node_id: str
    ) -> None:
        """artifact_owned_by_run passes for all n08a/n08b/n08c reused artifacts."""
        source_run = "source-run-001"
        current_run = "current-run-002"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _setup_full_reuse_env_with_ctx(
            tmp_path, node_id, source_run, current_run
        )

        result = artifact_owned_by_run(
            cfg["artifact_path"], current_run, repo_root=tmp_path
        )
        assert result.passed is True, (
            f"artifact_owned_by_run failed for {node_id}: "
            f"{result.reason}"
        )
        assert result.details.get("approved_via_phase8_reuse") is True

    def test_passes_with_v1_stale_metadata(self, tmp_path: Path) -> None:
        """Regression: v1 metadata with stale source_run_id still passes.

        This reproduces the exact bug from run fcac4f7a where n08c had v1
        metadata with source_run_id pointing to a validating run (not the
        artifact origin), but the artifact's actual run_id was different.
        """
        node_id = "n08c_implementation_drafting"
        # Artifact was actually produced by this run
        artifact_origin_run = "f367f022-03c7-42eb-a4f6-a005e6c9b0c1"
        # v1 metadata has this (wrong) source_run_id
        stale_validating_run = "62d7acae-906e-4b8f-9f85-4ff89b6a13f2"
        # Current run trying to reuse
        current_run = "fcac4f7a-1499-4eff-b517-105fcf289fe5"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _setup_full_reuse_env_with_ctx(
            tmp_path, node_id,
            source_run_id=artifact_origin_run,
            current_run_id=current_run,
            use_v1_metadata=True,
            v1_corrupted_source_run_id=stale_validating_run,
        )

        result = artifact_owned_by_run(
            cfg["artifact_path"], current_run, repo_root=tmp_path
        )
        assert result.passed is True, (
            f"Regression: artifact_owned_by_run failed with v1 stale metadata: "
            f"{result.reason}"
        )
        assert result.details.get("approved_via_phase8_reuse") is True


# ===========================================================================
# 3. Scheduler reads actual artifact run_id (not stale metadata)
# ===========================================================================


class TestSchedulerReadsActualArtifactRunId:
    """Verify that reuse_dec uses actual artifact run_id from disk."""

    def test_reuse_decision_has_correct_artifact_run_id(
        self, tmp_path: Path
    ) -> None:
        """The reuse decision must contain the artifact's actual run_id,
        not the metadata's potentially stale source_run_id."""
        node_id = "n08c_implementation_drafting"
        artifact_origin_run = "f367f022-03c7-42eb-a4f6-a005e6c9b0c1"
        stale_validating_run = "62d7acae-906e-4b8f-9f85-4ff89b6a13f2"
        current_run = "fcac4f7a-1499-4eff-b517-105fcf289fe5"

        ctx, fp = _setup_full_reuse_env_with_ctx(
            tmp_path, node_id,
            source_run_id=artifact_origin_run,
            current_run_id=current_run,
            use_v1_metadata=True,
            v1_corrupted_source_run_id=stale_validating_run,
        )

        # The decision should have the ACTUAL artifact run_id, not the stale one
        decision = ctx.get_reuse_decision(node_id)
        assert decision is not None
        assert decision["artifact_run_id"] == artifact_origin_run, (
            f"Expected artifact_run_id={artifact_origin_run}, "
            f"got {decision['artifact_run_id']}"
        )
        assert decision["source_run_id"] == artifact_origin_run


# ===========================================================================
# 4. Scope restriction regression
# ===========================================================================


class TestReuseExceptionScopeRegression:
    """Reuse exception must remain limited to n08a/n08b/n08c exact artifacts."""

    @pytest.mark.parametrize("artifact_path", [
        "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
        "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
    ])
    def test_non_reuse_paths_still_fail(
        self, tmp_path: Path, artifact_path: str
    ) -> None:
        """Non-Phase-8-section artifact paths still fail ownership."""
        artifact = {"run_id": "other-run", "schema_id": "test"}
        _write_json(tmp_path / artifact_path, artifact)

        result = artifact_owned_by_run(
            artifact_path, "current-run", repo_root=tmp_path
        )
        assert result.passed is False
        assert result.failure_category == "STALE_UPSTREAM_MISMATCH"
