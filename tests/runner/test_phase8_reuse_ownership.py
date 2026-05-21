"""
Tests for Phase 8 reuse-aware run ownership validation.

Covers:
1. Fresh ownership unchanged (artifact.run_id == current_run_id passes)
2. Valid reuse ownership passes (all 11 conditions met)
3. Reuse ownership fail-closed cases (each condition failure)
4. Scope restriction (n08d/n08e/n08f excluded, Phase 1-7 excluded)
5. Regression for run 1d799589 scenario
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from runner.phase8_reuse import (
    FINGERPRINT_INPUTS,
    REUSE_ELIGIBLE_NODES,
    REUSE_METADATA_DIR,
    _ARTIFACT_PATH_TO_NODE,
    _VALIDATION_REPORTS_DIR,
    artifact_sha256,
    compute_input_fingerprint,
    is_reuse_owned_artifact_valid,
    write_reuse_metadata,
)
from runner.predicates.file_predicates import artifact_owned_by_run
from runner.predicates.types import PredicateResult
from runner.run_context import RUNS_DIR_REL


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
    """Write a gate result at the canonical Tier 4 path."""
    from runner.gate_result_registry import GATE_RESULT_PATHS

    rel = GATE_RESULT_PATHS.get(gate_id)
    if rel is None:
        return
    _write_json(
        repo / "docs/tier4_orchestration_state" / rel,
        {"status": status, "gate_id": gate_id, "run_id": run_id},
    )


def _make_audit_reports(repo: Path, run_id: str) -> None:
    """Create current-run audit report files."""
    prefix = run_id.split("-")[0] if "-" in run_id else run_id[:8]
    reports_dir = repo / _VALIDATION_REPORTS_DIR
    _write_json(
        reports_dir / f"proposal-section-traceability-check_{prefix}.json",
        {
            "skill_id": "proposal-section-traceability-check",
            "run_id_reference": run_id,
            "claim_audit_results": [],
        },
    )
    _write_json(
        reports_dir / f"constitutional-compliance-check_{prefix}.json",
        {
            "skill_id": "constitutional-compliance-check",
            "run_id_reference": run_id,
            "section13_checks": [],
        },
    )


def _make_run_manifest(
    repo: Path,
    current_run_id: str,
    reuse_decisions: dict | None = None,
) -> None:
    """Create a run manifest with optional reuse decisions."""
    manifest = {
        "run_id": current_run_id,
        "node_states": {},
    }
    if reuse_decisions is not None:
        manifest["reuse_decisions"] = reuse_decisions
    manifest_path = repo / RUNS_DIR_REL / current_run_id / "run_manifest.json"
    _write_json(manifest_path, manifest)


def _setup_full_reuse_env(
    repo: Path,
    node_id: str,
    source_run_id: str = "source-run-001",
    current_run_id: str = "current-run-002",
) -> str:
    """Set up a complete valid reuse environment. Returns input fingerprint."""
    cfg = REUSE_ELIGIBLE_NODES[node_id]

    # Create fingerprint inputs
    _make_fingerprint_inputs(repo, node_id)

    # Create valid artifact
    _make_valid_artifact(repo, node_id, run_id=source_run_id)

    # Create gate result
    _make_gate_result(repo, cfg["gate_id"], "pass", run_id=source_run_id)

    # Compute fingerprint
    fp = compute_input_fingerprint(node_id, repo)
    assert fp is not None

    # Write reuse metadata
    art_path = repo / cfg["artifact_path"]
    art_hash = artifact_sha256(art_path)
    assert art_hash is not None
    write_reuse_metadata(
        node_id=node_id,
        repo_root=repo,
        source_run_id=source_run_id,
        artifact_path=cfg["artifact_path"],
        schema_id=cfg["schema_id"],
        gate_id=cfg["gate_id"],
        input_fingerprint=fp,
        artifact_hash=art_hash,
    )

    # Create audit reports for current run
    _make_audit_reports(repo, current_run_id)

    # Create run manifest with reuse decision
    _make_run_manifest(repo, current_run_id, reuse_decisions={
        node_id: {
            "status": "reused",
            "mode": "drafting_skipped_audit_executed",
            "source_run_id": source_run_id,
            "artifact_run_id": source_run_id,
            "artifact_path": cfg["artifact_path"],
            "input_fingerprint": fp,
            "gate_id": cfg["gate_id"],
        }
    })

    return fp


# ===========================================================================
# 1. Fresh ownership unchanged
# ===========================================================================


class TestFreshOwnership:
    """Verify that fresh artifacts (run_id matches) still pass normally."""

    def test_fresh_artifact_passes(self, tmp_path: Path) -> None:
        """Artifact with matching run_id passes ownership."""
        current_run = "current-run-001"
        artifact = {"run_id": current_run, "schema_id": "test"}
        art_path = tmp_path / "artifact.json"
        _write_json(art_path, artifact)

        result = artifact_owned_by_run(
            str(art_path), current_run, repo_root=tmp_path
        )
        assert result.passed is True

    def test_mismatched_run_id_fails_without_reuse(self, tmp_path: Path) -> None:
        """Artifact with non-matching run_id fails when no reuse exists."""
        artifact = {"run_id": "other-run", "schema_id": "test"}
        art_path = tmp_path / "artifact.json"
        _write_json(art_path, artifact)

        result = artifact_owned_by_run(
            str(art_path), "current-run", repo_root=tmp_path
        )
        assert result.passed is False
        assert result.failure_category == "STALE_UPSTREAM_MISMATCH"

    def test_phase8_path_mismatched_run_id_fails_without_reuse_env(
        self, tmp_path: Path
    ) -> None:
        """Phase 8 artifact path with mismatched run_id fails without valid reuse."""
        # Use the canonical path but without any reuse environment set up
        node_id = "n08c_implementation_drafting"
        cfg = REUSE_ELIGIBLE_NODES[node_id]
        artifact = {"run_id": "other-run", "schema_id": cfg["schema_id"]}
        _write_json(tmp_path / cfg["artifact_path"], artifact)

        result = artifact_owned_by_run(
            cfg["artifact_path"], "current-run", repo_root=tmp_path
        )
        assert result.passed is False


# ===========================================================================
# 2. Valid reuse ownership passes
# ===========================================================================


class TestValidReuseOwnership:
    """Verify that properly reused Phase 8 artifacts pass ownership."""

    @pytest.mark.parametrize("node_id", list(REUSE_ELIGIBLE_NODES.keys()))
    def test_valid_reuse_passes_all_nodes(
        self, tmp_path: Path, node_id: str
    ) -> None:
        """Valid reuse environment causes ownership to pass for all eligible nodes."""
        source_run = "505b5bfa-66bd-42de-b31f-2e66683bf48e"
        current_run = "1d799589-bfc5-464d-9a10-dd5113653c50"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _setup_full_reuse_env(
            tmp_path, node_id,
            source_run_id=source_run,
            current_run_id=current_run,
        )

        result = artifact_owned_by_run(
            cfg["artifact_path"], current_run, repo_root=tmp_path
        )
        assert result.passed is True
        assert result.details.get("approved_via_phase8_reuse") is True
        assert result.details.get("reuse_node_id") == node_id

    def test_valid_reuse_helper_directly(self, tmp_path: Path) -> None:
        """Test is_reuse_owned_artifact_valid directly returns True."""
        node_id = "n08a_excellence_drafting"
        source_run = "source-run-001"
        current_run = "current-run-002"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _setup_full_reuse_env(
            tmp_path, node_id,
            source_run_id=source_run,
            current_run_id=current_run,
        )

        artifact = json.loads(
            (tmp_path / cfg["artifact_path"]).read_text(encoding="utf-8")
        )

        valid, reason = is_reuse_owned_artifact_valid(
            node_id=node_id,
            artifact_path=cfg["artifact_path"],
            artifact=artifact,
            current_run_id=current_run,
            repo_root=tmp_path,
        )
        assert valid is True
        assert reason == "all_reuse_ownership_conditions_met"


# ===========================================================================
# 3. Reuse ownership fail-closed cases
# ===========================================================================


class TestReuseFailClosed:
    """Every condition failure must cause rejection."""

    def _setup_and_get_artifact(
        self, tmp_path: Path, node_id: str = "n08c_implementation_drafting"
    ) -> tuple[str, str, dict]:
        """Set up full env and return (source_run, current_run, artifact)."""
        source_run = "source-run-001"
        current_run = "current-run-002"
        _setup_full_reuse_env(
            tmp_path, node_id,
            source_run_id=source_run,
            current_run_id=current_run,
        )
        cfg = REUSE_ELIGIBLE_NODES[node_id]
        artifact = json.loads(
            (tmp_path / cfg["artifact_path"]).read_text(encoding="utf-8")
        )
        return source_run, current_run, artifact

    def test_fails_when_reuse_decision_missing(self, tmp_path: Path) -> None:
        """Fails when no reuse decision exists in manifest."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        # Overwrite manifest without reuse decisions
        _make_run_manifest(tmp_path, current_run, reuse_decisions={})

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"],
            artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "no_reuse_decision_for_node"

    def test_fails_when_status_not_reused(self, tmp_path: Path) -> None:
        """Fails when decision status != 'reused'."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        _make_run_manifest(tmp_path, current_run, reuse_decisions={
            node_id: {"status": "not_reused", "reason": "test"}
        })

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"],
            artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "reuse_decision_status_not_reused"

    def test_fails_when_mode_wrong(self, tmp_path: Path) -> None:
        """Fails when mode is missing or incorrect."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        cfg = REUSE_ELIGIBLE_NODES[node_id]
        _make_run_manifest(tmp_path, current_run, reuse_decisions={
            node_id: {
                "status": "reused",
                "mode": "wrong_mode",
                "source_run_id": source_run,
                "artifact_path": cfg["artifact_path"],
            }
        })

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "reuse_decision_mode_wrong"

    def test_fails_when_source_run_id_mismatch(self, tmp_path: Path) -> None:
        """Fails when decision source_run_id != artifact.run_id."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        cfg = REUSE_ELIGIBLE_NODES[node_id]
        _make_run_manifest(tmp_path, current_run, reuse_decisions={
            node_id: {
                "status": "reused",
                "mode": "drafting_skipped_audit_executed",
                "source_run_id": "wrong-source-run",
                "artifact_path": cfg["artifact_path"],
            }
        })

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "reuse_decision_source_run_id_mismatch"

    def test_fails_when_artifact_path_mismatch_in_decision(
        self, tmp_path: Path
    ) -> None:
        """Fails when decision artifact_path doesn't match."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        cfg = REUSE_ELIGIBLE_NODES[node_id]
        _make_run_manifest(tmp_path, current_run, reuse_decisions={
            node_id: {
                "status": "reused",
                "mode": "drafting_skipped_audit_executed",
                "source_run_id": source_run,
                "artifact_path": "wrong/path.json",
            }
        })

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "reuse_decision_artifact_path_mismatch"

    def test_fails_when_metadata_missing(self, tmp_path: Path) -> None:
        """Fails when reuse metadata file is absent."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        # Remove metadata file
        meta_path = tmp_path / REUSE_METADATA_DIR / f"{node_id}.reuse.json"
        meta_path.unlink()

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"],
            artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "reuse_metadata_missing"

    def test_passes_when_metadata_source_run_id_stale_but_hash_matches(
        self, tmp_path: Path
    ) -> None:
        """Passes when metadata artifact_run_id/source_run_id is stale but
        hash and fingerprint still match (condition 7 removed; conditions 8+9
        are the authoritative integrity checks)."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        # Corrupt both artifact_run_id and source_run_id in metadata
        meta_path = tmp_path / REUSE_METADATA_DIR / f"{node_id}.reuse.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["source_run_id"] = "wrong-source"
        meta["artifact_run_id"] = "wrong-source"
        _write_json(meta_path, meta)

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"],
            artifact, current_run, tmp_path,
        )
        # With condition 7 removed, hash+fingerprint match is sufficient
        assert valid is True
        assert reason == "all_reuse_ownership_conditions_met"

    def test_fails_when_artifact_hash_mismatch(self, tmp_path: Path) -> None:
        """Fails when artifact SHA-256 doesn't match metadata."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        # Modify artifact on disk (changing hash)
        cfg = REUSE_ELIGIBLE_NODES[node_id]
        art_path = tmp_path / cfg["artifact_path"]
        modified = json.loads(art_path.read_text(encoding="utf-8"))
        modified["extra_field"] = "hash_breaker"
        _write_json(art_path, modified)

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], modified, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "artifact_hash_mismatch"

    def test_fails_when_fingerprint_mismatch(self, tmp_path: Path) -> None:
        """Fails when input fingerprint doesn't match metadata."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        # Add a new input file (changing fingerprint)
        _write_json(
            tmp_path / "docs/tier3_project_instantiation/new_data.json",
            {"changed": True},
        )

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"],
            artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "input_fingerprint_mismatch"

    def test_fails_when_traceability_audit_missing(
        self, tmp_path: Path
    ) -> None:
        """Fails when traceability audit report is missing."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        # Remove traceability report
        prefix = current_run.split("-")[0]
        report_path = (
            tmp_path / _VALIDATION_REPORTS_DIR
            / f"proposal-section-traceability-check_{prefix}.json"
        )
        report_path.unlink()

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"],
            artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "missing_audit_report_proposal-section-traceability-check"

    def test_fails_when_constitutional_audit_missing(
        self, tmp_path: Path
    ) -> None:
        """Fails when constitutional compliance audit report is missing."""
        node_id = "n08c_implementation_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        # Remove compliance report
        prefix = current_run.split("-")[0]
        report_path = (
            tmp_path / _VALIDATION_REPORTS_DIR
            / f"constitutional-compliance-check_{prefix}.json"
        )
        report_path.unlink()

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"],
            artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "missing_audit_report_constitutional-compliance-check"

    def test_fails_when_validation_status_unresolved(
        self, tmp_path: Path
    ) -> None:
        """Fails when artifact has overall_status=unresolved."""
        node_id = "n08c_implementation_drafting"
        source_run = "source-run-001"
        current_run = "current-run-002"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        # Set up env but with unresolved validation status
        _make_fingerprint_inputs(tmp_path, node_id)
        content = {
            "schema_id": cfg["schema_id"],
            "run_id": source_run,
            "validation_status": {
                "overall_status": "unresolved",
                "claim_statuses": [],
            },
            "traceability_footer": {
                "primary_sources": [],
                "no_unsupported_claims_declaration": True,
            },
        }
        _write_json(tmp_path / cfg["artifact_path"], content)
        _make_gate_result(tmp_path, cfg["gate_id"], "pass", run_id=source_run)

        fp = compute_input_fingerprint(node_id, tmp_path)
        art_hash = artifact_sha256(tmp_path / cfg["artifact_path"])
        write_reuse_metadata(
            node_id=node_id, repo_root=tmp_path,
            source_run_id=source_run, artifact_path=cfg["artifact_path"],
            schema_id=cfg["schema_id"], gate_id=cfg["gate_id"],
            input_fingerprint=fp, artifact_hash=art_hash,
        )
        _make_audit_reports(tmp_path, current_run)
        _make_run_manifest(tmp_path, current_run, reuse_decisions={
            node_id: {
                "status": "reused",
                "mode": "drafting_skipped_audit_executed",
                "source_run_id": source_run,
                "artifact_path": cfg["artifact_path"],
                "input_fingerprint": fp,
                "gate_id": cfg["gate_id"],
            }
        })

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], content, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "validation_status_unresolved"

    def test_fails_when_assumed_claim(self, tmp_path: Path) -> None:
        """Fails when artifact has an assumed claim."""
        node_id = "n08b_impact_drafting"
        source_run = "source-run-001"
        current_run = "current-run-002"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _make_fingerprint_inputs(tmp_path, node_id)
        content = {
            "schema_id": cfg["schema_id"],
            "run_id": source_run,
            "validation_status": {
                "overall_status": "confirmed",
                "claim_statuses": [
                    {"claim_id": "C-01", "status": "assumed"},
                ],
            },
            "traceability_footer": {
                "primary_sources": [],
                "no_unsupported_claims_declaration": True,
            },
        }
        _write_json(tmp_path / cfg["artifact_path"], content)
        _make_gate_result(tmp_path, cfg["gate_id"], "pass", run_id=source_run)

        fp = compute_input_fingerprint(node_id, tmp_path)
        art_hash = artifact_sha256(tmp_path / cfg["artifact_path"])
        write_reuse_metadata(
            node_id=node_id, repo_root=tmp_path,
            source_run_id=source_run, artifact_path=cfg["artifact_path"],
            schema_id=cfg["schema_id"], gate_id=cfg["gate_id"],
            input_fingerprint=fp, artifact_hash=art_hash,
        )
        _make_audit_reports(tmp_path, current_run)
        _make_run_manifest(tmp_path, current_run, reuse_decisions={
            node_id: {
                "status": "reused",
                "mode": "drafting_skipped_audit_executed",
                "source_run_id": source_run,
                "artifact_path": cfg["artifact_path"],
                "input_fingerprint": fp,
                "gate_id": cfg["gate_id"],
            }
        })

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], content, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "claim_status_assumed"

    def test_fails_when_no_unsupported_claims_false(
        self, tmp_path: Path
    ) -> None:
        """Fails when no_unsupported_claims_declaration is false."""
        node_id = "n08a_excellence_drafting"
        source_run, current_run, artifact = self._setup_and_get_artifact(
            tmp_path, node_id
        )
        # Modify the artifact's traceability footer
        artifact["traceability_footer"]["no_unsupported_claims_declaration"] = False

        valid, reason = is_reuse_owned_artifact_valid(
            node_id, REUSE_ELIGIBLE_NODES[node_id]["artifact_path"],
            artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "unsupported_claims_declaration_false"


# ===========================================================================
# 4. Scope restriction
# ===========================================================================


class TestScopeRestriction:
    """Reuse ownership exception must NOT apply to ineligible nodes."""

    @pytest.mark.parametrize("node_id", [
        "n08d_assembly",
        "n08e_evaluator_review",
        "n08f_revision",
    ])
    def test_not_eligible_for_n08d_e_f(
        self, tmp_path: Path, node_id: str
    ) -> None:
        """Reuse exception does not apply to assembly/review/revision."""
        artifact = {"run_id": "other-run", "schema_id": "test"}

        valid, reason = is_reuse_owned_artifact_valid(
            node_id=node_id,
            artifact_path="docs/tier5_deliverables/some_artifact.json",
            artifact=artifact,
            current_run_id="current-run",
            repo_root=tmp_path,
        )
        assert valid is False
        assert reason == "node_not_reuse_eligible"

    @pytest.mark.parametrize("artifact_path", [
        "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
        "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
        "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json",
        "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json",
        "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json",
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json",
    ])
    def test_phase1_7_artifacts_not_eligible(
        self, tmp_path: Path, artifact_path: str
    ) -> None:
        """Phase 1-7 artifacts never get the reuse ownership exception."""
        # These paths should not appear in _ARTIFACT_PATH_TO_NODE
        assert artifact_path not in _ARTIFACT_PATH_TO_NODE

    def test_predicate_rejects_non_phase8_path(self, tmp_path: Path) -> None:
        """artifact_owned_by_run does not invoke reuse for non-Phase-8 paths."""
        artifact = {"run_id": "other-run", "schema_id": "test"}
        art_path = tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json"
        _write_json(art_path, artifact)

        result = artifact_owned_by_run(
            "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
            "current-run",
            repo_root=tmp_path,
        )
        assert result.passed is False
        assert result.failure_category == "STALE_UPSTREAM_MISMATCH"

    def test_n08d_assembly_path_not_eligible(self, tmp_path: Path) -> None:
        """Assembly artifact path is not in the reuse-eligible mapping."""
        assert (
            "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json"
            not in _ARTIFACT_PATH_TO_NODE
        )

    def test_review_packet_path_not_eligible(self, tmp_path: Path) -> None:
        """Review packet path is not in the reuse-eligible mapping."""
        assert (
            "docs/tier5_deliverables/review_packets/review_packet.json"
            not in _ARTIFACT_PATH_TO_NODE
        )


# ===========================================================================
# 5. Regression for run 1d799589 scenario
# ===========================================================================


class TestRegressionRun1d799589:
    """Simulate the exact scenario from the bug report."""

    def test_implementation_section_reuse_passes(self, tmp_path: Path) -> None:
        """
        Regression: run 1d799589, artifact from 505b5bfa, node n08c.

        Previously failed because artifact.run_id (505b5bfa) != current (1d799589).
        With reuse-aware ownership, this should pass.
        """
        source_run = "505b5bfa-66bd-42de-b31f-2e66683bf48e"
        current_run = "1d799589-bfc5-464d-9a10-dd5113653c50"
        node_id = "n08c_implementation_drafting"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _setup_full_reuse_env(
            tmp_path, node_id,
            source_run_id=source_run,
            current_run_id=current_run,
        )

        # Call the predicate as the gate evaluator would
        result = artifact_owned_by_run(
            cfg["artifact_path"],
            current_run,
            repo_root=tmp_path,
        )

        assert result.passed is True
        assert result.details["approved_via_phase8_reuse"] is True
        assert result.details["reuse_node_id"] == node_id
        assert result.details["artifact_run_id"] == source_run
        assert result.details["current_run_id"] == current_run

    def test_excellence_and_impact_fresh_still_pass(
        self, tmp_path: Path
    ) -> None:
        """
        In the same run, n08a and n08b ran fresh and should still pass
        with normal run_id matching.
        """
        current_run = "1d799589-bfc5-464d-9a10-dd5113653c50"

        for node_id in ("n08a_excellence_drafting", "n08b_impact_drafting"):
            cfg = REUSE_ELIGIBLE_NODES[node_id]
            artifact = {"run_id": current_run, "schema_id": cfg["schema_id"]}
            _write_json(tmp_path / cfg["artifact_path"], artifact)

            result = artifact_owned_by_run(
                cfg["artifact_path"],
                current_run,
                repo_root=tmp_path,
            )
            assert result.passed is True
            assert result.details.get("run_id") == current_run


# ===========================================================================
# Additional: RunContext integration
# ===========================================================================


class TestRunContextReuseDecision:
    """Verify RunContext record/get reuse decision methods."""

    def test_record_and_get(self, tmp_path: Path) -> None:
        from runner.run_context import RunContext

        ctx = RunContext.initialize(tmp_path, "test-run-001")
        decision = {
            "status": "reused",
            "mode": "drafting_skipped_audit_executed",
            "source_run_id": "source-001",
        }
        ctx.record_reuse_decision("n08c_implementation_drafting", decision)
        ctx.save()

        # Reload and verify
        ctx2 = RunContext.load(tmp_path, "test-run-001")
        got = ctx2.get_reuse_decision("n08c_implementation_drafting")
        assert got == decision

    def test_get_returns_none_when_absent(self, tmp_path: Path) -> None:
        from runner.run_context import RunContext

        ctx = RunContext.initialize(tmp_path, "test-run-001")
        assert ctx.get_reuse_decision("n08c_implementation_drafting") is None


# ===========================================================================
# 6. read_artifact_run_id helper
# ===========================================================================


class TestReadArtifactRunId:
    """Tests for the read_artifact_run_id helper."""

    def test_reads_run_id_from_valid_artifact(self, tmp_path: Path) -> None:
        from runner.phase8_reuse import read_artifact_run_id

        art = tmp_path / "artifact.json"
        _write_json(art, {"run_id": "abc-123", "schema_id": "test"})
        assert read_artifact_run_id(art) == "abc-123"

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        from runner.phase8_reuse import read_artifact_run_id

        assert read_artifact_run_id(tmp_path / "missing.json") is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        from runner.phase8_reuse import read_artifact_run_id

        art = tmp_path / "bad.json"
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text("not json", encoding="utf-8")
        assert read_artifact_run_id(art) is None

    def test_returns_none_for_non_dict(self, tmp_path: Path) -> None:
        from runner.phase8_reuse import read_artifact_run_id

        art = tmp_path / "list.json"
        _write_json(art, [1, 2, 3])
        assert read_artifact_run_id(art) is None

    def test_returns_none_for_missing_run_id_key(self, tmp_path: Path) -> None:
        from runner.phase8_reuse import read_artifact_run_id

        art = tmp_path / "no_rid.json"
        _write_json(art, {"schema_id": "test"})
        assert read_artifact_run_id(art) is None

    def test_returns_none_for_non_string_run_id(self, tmp_path: Path) -> None:
        from runner.phase8_reuse import read_artifact_run_id

        art = tmp_path / "int_rid.json"
        _write_json(art, {"run_id": 123})
        assert read_artifact_run_id(art) is None


# ===========================================================================
# 7. write_reuse_metadata new fields
# ===========================================================================


class TestWriteMetadataNewFields:
    """Verify artifact_run_id and last_validated_run_id in written metadata."""

    def test_metadata_contains_artifact_run_id(self, tmp_path: Path) -> None:
        path = write_reuse_metadata(
            node_id="n08a_excellence_drafting",
            repo_root=tmp_path,
            source_run_id="src-run",
            artifact_path="docs/t5/excel.json",
            schema_id="orch.tier5.excellence_section.v1",
            gate_id="gate_10a_excellence_completeness",
            input_fingerprint="fp1",
            artifact_hash="hash1",
            artifact_run_id="art-run-001",
            last_validated_run_id="val-run-002",
        )
        from runner.phase8_reuse import load_reuse_metadata
        loaded = load_reuse_metadata("n08a_excellence_drafting", tmp_path)
        assert loaded["artifact_run_id"] == "art-run-001"
        assert loaded["last_validated_run_id"] == "val-run-002"

    def test_source_run_id_equals_artifact_run_id_not_last_validated(
        self, tmp_path: Path
    ) -> None:
        """source_run_id must be artifact_run_id (artifact origin), not
        last_validated_run_id (validating run)."""
        write_reuse_metadata(
            node_id="n08b_impact_drafting",
            repo_root=tmp_path,
            source_run_id="ignored",
            artifact_path="docs/t5/impact.json",
            schema_id="orch.tier5.impact_section.v1",
            gate_id="gate_10b_impact_completeness",
            input_fingerprint="fp2",
            artifact_hash="hash2",
            artifact_run_id="art-origin",
            last_validated_run_id="val-run",
        )
        from runner.phase8_reuse import load_reuse_metadata
        loaded = load_reuse_metadata("n08b_impact_drafting", tmp_path)
        assert loaded["source_run_id"] == "art-origin"
        assert loaded["source_run_id"] != "val-run"

    def test_fallback_when_artifact_run_id_is_none(self, tmp_path: Path) -> None:
        """When artifact_run_id=None, falls back to source_run_id."""
        write_reuse_metadata(
            node_id="n08c_implementation_drafting",
            repo_root=tmp_path,
            source_run_id="fallback-run",
            artifact_path="docs/t5/impl.json",
            schema_id="orch.tier5.implementation_section.v1",
            gate_id="gate_10c_implementation_completeness",
            input_fingerprint="fp3",
            artifact_hash="hash3",
        )
        from runner.phase8_reuse import load_reuse_metadata
        loaded = load_reuse_metadata("n08c_implementation_drafting", tmp_path)
        assert loaded["artifact_run_id"] == "fallback-run"
        assert loaded["source_run_id"] == "fallback-run"
        assert loaded["last_validated_run_id"] == "fallback-run"


# ===========================================================================
# 8. Backward compat and fail-closed v1 metadata
# ===========================================================================


class TestV1MetadataBackwardCompat:
    """Backward compatibility with v1 metadata (no artifact_run_id key)."""

    def test_v1_metadata_correct_source_run_id_passes(
        self, tmp_path: Path
    ) -> None:
        """v1 metadata where source_run_id == artifact.run_id still passes
        via fallback."""
        node_id = "n08a_excellence_drafting"
        source_run = "original-run-001"
        current_run = "current-run-002"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _make_fingerprint_inputs(tmp_path, node_id)
        _make_valid_artifact(tmp_path, node_id, run_id=source_run)
        _make_gate_result(tmp_path, cfg["gate_id"], "pass", run_id=source_run)

        fp = compute_input_fingerprint(node_id, tmp_path)
        art_hash = artifact_sha256(tmp_path / cfg["artifact_path"])

        # Write v1-style metadata (no artifact_run_id key)
        meta_path = tmp_path / REUSE_METADATA_DIR / f"{node_id}.reuse.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        v1_metadata = {
            "node_id": node_id,
            "artifact_path": cfg["artifact_path"],
            "schema_id": cfg["schema_id"],
            "source_run_id": source_run,  # correct: matches artifact.run_id
            "gate_id": cfg["gate_id"],
            "gate_status": "pass",
            "input_fingerprint": fp,
            "artifact_sha256": art_hash,
            "reuse_policy_version": "phase8.section.v1",
        }
        _write_json(meta_path, v1_metadata)

        _make_audit_reports(tmp_path, current_run)
        _make_run_manifest(tmp_path, current_run, reuse_decisions={
            node_id: {
                "status": "reused",
                "mode": "drafting_skipped_audit_executed",
                "source_run_id": source_run,
                "artifact_path": cfg["artifact_path"],
                "input_fingerprint": fp,
                "gate_id": cfg["gate_id"],
            }
        })

        artifact = json.loads(
            (tmp_path / cfg["artifact_path"]).read_text(encoding="utf-8")
        )
        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], artifact, current_run, tmp_path,
        )
        assert valid is True

    def test_v1_metadata_corrupted_source_run_id_fails(
        self, tmp_path: Path
    ) -> None:
        """v1 metadata where source_run_id was overwritten to a validation-run
        ID (not artifact origin) correctly REJECTS."""
        node_id = "n08b_impact_drafting"
        artifact_origin_run = "original-run-001"
        corrupted_validation_run = "validation-run-002"
        current_run = "current-run-003"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _make_fingerprint_inputs(tmp_path, node_id)
        _make_valid_artifact(tmp_path, node_id, run_id=artifact_origin_run)
        _make_gate_result(tmp_path, cfg["gate_id"], "pass")

        fp = compute_input_fingerprint(node_id, tmp_path)
        art_hash = artifact_sha256(tmp_path / cfg["artifact_path"])

        # Write v1-style metadata with CORRUPTED source_run_id
        meta_path = tmp_path / REUSE_METADATA_DIR / f"{node_id}.reuse.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        v1_metadata = {
            "node_id": node_id,
            "artifact_path": cfg["artifact_path"],
            "schema_id": cfg["schema_id"],
            "source_run_id": corrupted_validation_run,  # BUG: != artifact.run_id
            "gate_id": cfg["gate_id"],
            "gate_status": "pass",
            "input_fingerprint": fp,
            "artifact_sha256": art_hash,
            "reuse_policy_version": "phase8.section.v1",
        }
        _write_json(meta_path, v1_metadata)

        _make_audit_reports(tmp_path, current_run)
        _make_run_manifest(tmp_path, current_run, reuse_decisions={
            node_id: {
                "status": "reused",
                "mode": "drafting_skipped_audit_executed",
                "source_run_id": corrupted_validation_run,
                "artifact_path": cfg["artifact_path"],
                "input_fingerprint": fp,
                "gate_id": cfg["gate_id"],
            }
        })

        artifact = json.loads(
            (tmp_path / cfg["artifact_path"]).read_text(encoding="utf-8")
        )
        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], artifact, current_run, tmp_path,
        )
        assert valid is False
        assert reason == "reuse_decision_source_run_id_mismatch"


# ===========================================================================
# 9. Multi-run reuse regression (exact bug reproduction)
# ===========================================================================


class TestMultiRunReuseRegression:
    """Reproduce the exact 3-run scenario from the bug report."""

    def test_metadata_preserves_artifact_run_id_after_reuse_gate_pass(
        self, tmp_path: Path
    ) -> None:
        """
        Run A: artifact freshly produced (artifact.run_id = run_a).
        Run B: artifact reused, gate passes, metadata rewritten.
        After Run B, metadata must have artifact_run_id = run_a (not run_b).
        """
        node_id = "n08a_excellence_drafting"
        run_a = "1d799589-bfc5-464d-9a10-dd5113653c50"
        run_b = "f367f022-1234-5678-9abc-def012345678"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        # Run A: fresh artifact produced
        _make_fingerprint_inputs(tmp_path, node_id)
        _make_valid_artifact(tmp_path, node_id, run_id=run_a)

        fp = compute_input_fingerprint(node_id, tmp_path)
        art_hash = artifact_sha256(tmp_path / cfg["artifact_path"])

        # Run A metadata (fresh production)
        write_reuse_metadata(
            node_id=node_id,
            repo_root=tmp_path,
            source_run_id=run_a,
            artifact_path=cfg["artifact_path"],
            schema_id=cfg["schema_id"],
            gate_id=cfg["gate_id"],
            input_fingerprint=fp,
            artifact_hash=art_hash,
            artifact_run_id=run_a,
            last_validated_run_id=run_a,
        )

        # Run B: reuse gate passes, metadata rewritten with CORRECT semantics
        from runner.phase8_reuse import read_artifact_run_id
        art_path = tmp_path / cfg["artifact_path"]
        _art_run_id = read_artifact_run_id(art_path)

        write_reuse_metadata(
            node_id=node_id,
            repo_root=tmp_path,
            source_run_id=_art_run_id or run_b,
            artifact_path=cfg["artifact_path"],
            schema_id=cfg["schema_id"],
            gate_id=cfg["gate_id"],
            input_fingerprint=fp,
            artifact_hash=art_hash,
            artifact_run_id=_art_run_id or run_b,
            last_validated_run_id=run_b,
        )

        # Verify metadata preserved artifact origin
        from runner.phase8_reuse import load_reuse_metadata
        loaded = load_reuse_metadata(node_id, tmp_path)
        assert loaded["artifact_run_id"] == run_a
        assert loaded["source_run_id"] == run_a
        assert loaded["last_validated_run_id"] == run_b

    @pytest.mark.parametrize("node_id", [
        "n08a_excellence_drafting",
        "n08b_impact_drafting",
    ])
    def test_run_c_validates_after_run_b_metadata(
        self, tmp_path: Path, node_id: str,
    ) -> None:
        """
        After Run B's correct metadata update, Run C's ownership validation
        passes for n08a/n08b.
        """
        run_a = "1d799589-bfc5-464d-9a10-dd5113653c50"
        run_b = "f367f022-1234-5678-9abc-def012345678"
        run_c = "62d7acae-906e-4b8f-9f85-4ff89b6a13f2"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        # Set up artifact produced in Run A
        _make_fingerprint_inputs(tmp_path, node_id)
        _make_valid_artifact(tmp_path, node_id, run_id=run_a)
        _make_gate_result(tmp_path, cfg["gate_id"], "pass", run_id=run_a)

        fp = compute_input_fingerprint(node_id, tmp_path)
        art_hash = artifact_sha256(tmp_path / cfg["artifact_path"])

        # Run B rewrites metadata with correct artifact_run_id
        write_reuse_metadata(
            node_id=node_id,
            repo_root=tmp_path,
            source_run_id=run_a,
            artifact_path=cfg["artifact_path"],
            schema_id=cfg["schema_id"],
            gate_id=cfg["gate_id"],
            input_fingerprint=fp,
            artifact_hash=art_hash,
            artifact_run_id=run_a,
            last_validated_run_id=run_b,
        )

        # Run C: set up reuse decision and audit reports
        _make_audit_reports(tmp_path, run_c)
        _make_run_manifest(tmp_path, run_c, reuse_decisions={
            node_id: {
                "status": "reused",
                "mode": "drafting_skipped_audit_executed",
                "source_run_id": run_a,
                "artifact_run_id": run_a,
                "artifact_path": cfg["artifact_path"],
                "input_fingerprint": fp,
                "gate_id": cfg["gate_id"],
            }
        })

        # Verify ownership passes
        artifact = json.loads(
            (tmp_path / cfg["artifact_path"]).read_text(encoding="utf-8")
        )
        valid, reason = is_reuse_owned_artifact_valid(
            node_id, cfg["artifact_path"], artifact, run_c, tmp_path,
        )
        assert valid is True, f"Expected pass for {node_id}, got: {reason}"

    @pytest.mark.parametrize("node_id", list(REUSE_ELIGIBLE_NODES.keys()))
    def test_predicate_passes_all_three_nodes_with_v2_metadata(
        self, tmp_path: Path, node_id: str,
    ) -> None:
        """artifact_owned_by_run passes for all 3 nodes with correct v2 metadata."""
        source_run = "original-run-001"
        current_run = "current-run-003"
        cfg = REUSE_ELIGIBLE_NODES[node_id]

        _setup_full_reuse_env(
            tmp_path, node_id,
            source_run_id=source_run,
            current_run_id=current_run,
        )

        result = artifact_owned_by_run(
            cfg["artifact_path"], current_run, repo_root=tmp_path,
        )
        assert result.passed is True
        assert result.details.get("approved_via_phase8_reuse") is True
