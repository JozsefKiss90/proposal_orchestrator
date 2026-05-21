"""
Unit test for Phase 8 artifact resolution pipeline — no Claude invocation.

Verifies the end-to-end chain:
  1. Skill writes artifact to canonical path (simulated)
  2. _resolve_auditable_artifact() finds the artifact for compliance/traceability checks
  3. _determine_can_evaluate_exit_gate() confirms gate-relevant artifacts exist on disk

This test exercises the pure-Python resolution logic in agent_runtime.py
using a minimal manifest fixture, without invoking Claude or the skill
runtime transport.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.agent_runtime import (
    _NODE_PRIMARY_AUDITABLE_ARTIFACT,
    _determine_can_evaluate_exit_gate,
    _get_artifacts_produced_by_node,
    _resolve_auditable_artifact,
    _artifact_registry_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_manifest(repo_root: Path, artifact_registry: list[dict]) -> Path:
    """Write a minimal manifest.compile.yaml with the given artifact_registry."""
    manifest_path = repo_root / ".claude" / "workflows" / "system_orchestration" / "manifest.compile.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "artifact_registry": artifact_registry,
        "node_registry": [],
    }
    manifest_path.write_text(yaml.dump(data), encoding="utf-8")
    return manifest_path


# Minimal artifact_registry matching the production manifest for Phase 8
# drafting nodes.  File-level entries so that each node's gate check
# verifies its exact artifact, not just "any .json in the directory".
_PHASE8_ARTIFACT_REGISTRY = [
    {
        "artifact_id": "a_t4_phase8",
        "path": "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/",
        "tier": "tier4_phase_output",
        "produced_by": [
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
            "n08d_assembly",
            "n08e_evaluator_review",
            "n08f_revision",
        ],
    },
    {
        "artifact_id": "a_t5_excellence_section",
        "path": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
        "tier": "tier5_deliverable",
        "produced_by": "n08a_excellence_drafting",
    },
    {
        "artifact_id": "a_t5_impact_section",
        "path": "docs/tier5_deliverables/proposal_sections/impact_section.json",
        "tier": "tier5_deliverable",
        "produced_by": "n08b_impact_drafting",
    },
    {
        "artifact_id": "a_t5_implementation_section",
        "path": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
        "tier": "tier5_deliverable",
        "produced_by": "n08c_implementation_drafting",
    },
    {
        "artifact_id": "a_t5_assembled_drafts",
        "path": "docs/tier5_deliverables/assembled_drafts/",
        "tier": "tier5_deliverable",
        "produced_by": ["n08d_assembly", "n08f_revision"],
    },
]


@pytest.fixture(autouse=True)
def _clear_artifact_cache():
    """Clear the module-level artifact registry cache between tests."""
    _artifact_registry_cache.clear()
    yield
    _artifact_registry_cache.clear()


# ===========================================================================
# _resolve_auditable_artifact: from all_outputs to artifact_path
# ===========================================================================


class TestResolveAuditableFromOutputs:
    """Verify _resolve_auditable_artifact finds the correct artifact
    when earlier skills have written outputs to all_outputs."""

    def test_excellence_from_all_outputs(self, tmp_path: Path) -> None:
        artifact_rel = "docs/tier5_deliverables/proposal_sections/excellence_section.json"
        _write_json(tmp_path / artifact_rel, {"schema_id": "orch.tier5.excellence_section.v1"})

        result = _resolve_auditable_artifact(
            "n08a_excellence_drafting",
            [artifact_rel],
            tmp_path,
        )
        assert result == artifact_rel

    def test_impact_from_all_outputs(self, tmp_path: Path) -> None:
        artifact_rel = "docs/tier5_deliverables/proposal_sections/impact_section.json"
        _write_json(tmp_path / artifact_rel, {"schema_id": "orch.tier5.impact_section.v1"})

        result = _resolve_auditable_artifact(
            "n08b_impact_drafting",
            [artifact_rel],
            tmp_path,
        )
        assert result == artifact_rel

    def test_implementation_from_all_outputs(self, tmp_path: Path) -> None:
        artifact_rel = "docs/tier5_deliverables/proposal_sections/implementation_section.json"
        _write_json(tmp_path / artifact_rel, {"schema_id": "orch.tier5.implementation_section.v1"})

        result = _resolve_auditable_artifact(
            "n08c_implementation_drafting",
            [artifact_rel],
            tmp_path,
        )
        assert result == artifact_rel

    def test_falls_back_to_primary_artifact_mapping(self, tmp_path: Path) -> None:
        """When all_outputs is empty, falls back to _NODE_PRIMARY_AUDITABLE_ARTIFACT."""
        artifact_rel = _NODE_PRIMARY_AUDITABLE_ARTIFACT["n08a_excellence_drafting"]
        _write_json(tmp_path / artifact_rel, {"schema_id": "test"})

        result = _resolve_auditable_artifact(
            "n08a_excellence_drafting",
            [],  # no all_outputs
            tmp_path,
        )
        assert result == artifact_rel

    def test_returns_none_when_nothing_exists(self, tmp_path: Path) -> None:
        result = _resolve_auditable_artifact(
            "n08a_excellence_drafting",
            [],
            tmp_path,
        )
        assert result is None

    def test_skips_gate_result_artifacts(self, tmp_path: Path) -> None:
        """gate_result.json should not be selected as the auditable artifact."""
        gate_rel = "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_result.json"
        section_rel = "docs/tier5_deliverables/proposal_sections/excellence_section.json"
        _write_json(tmp_path / gate_rel, {"gate": "result"})
        _write_json(tmp_path / section_rel, {"schema_id": "test"})

        result = _resolve_auditable_artifact(
            "n08a_excellence_drafting",
            [gate_rel, section_rel],
            tmp_path,
        )
        assert result == section_rel


# ===========================================================================
# _determine_can_evaluate_exit_gate: artifact presence on disk
# ===========================================================================


class TestGateRelevantArtifactDiscovery:
    """Verify _determine_can_evaluate_exit_gate checks the correct paths."""

    def test_excellence_node_gate_ready(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(tmp_path, _PHASE8_ARTIFACT_REGISTRY)

        # Simulate skill output: write excellence_section.json
        _write_json(
            tmp_path / "docs/tier5_deliverables/proposal_sections/excellence_section.json",
            {"schema_id": "orch.tier5.excellence_section.v1", "content": "test"},
        )
        # Phase 8 review dir needs at least one file
        _write_json(
            tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/placeholder.json",
            {"placeholder": True},
        )

        result = _determine_can_evaluate_exit_gate(
            "n08a_excellence_drafting",
            tmp_path,
            manifest_path=manifest_path,
        )
        assert result is True

    def test_excellence_node_not_ready_missing_section(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(tmp_path, _PHASE8_ARTIFACT_REGISTRY)

        # Phase 8 review dir exists but proposal_sections/ does NOT
        _write_json(
            tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/placeholder.json",
            {"placeholder": True},
        )

        result = _determine_can_evaluate_exit_gate(
            "n08a_excellence_drafting",
            tmp_path,
            manifest_path=manifest_path,
        )
        assert result is False

    def test_excellence_node_not_ready_empty_dir(self, tmp_path: Path) -> None:
        """Directory exists but the specific file does not."""
        manifest_path = _write_manifest(tmp_path, _PHASE8_ARTIFACT_REGISTRY)

        # proposal_sections/ exists but excellence_section.json is absent
        (tmp_path / "docs/tier5_deliverables/proposal_sections").mkdir(parents=True)
        _write_json(
            tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/placeholder.json",
            {"placeholder": True},
        )

        result = _determine_can_evaluate_exit_gate(
            "n08a_excellence_drafting",
            tmp_path,
            manifest_path=manifest_path,
        )
        assert result is False

    def test_each_drafting_node_declares_exact_file(self, tmp_path: Path) -> None:
        """Each drafting node must declare its exact file, not the shared directory."""
        manifest_path = _write_manifest(tmp_path, _PHASE8_ARTIFACT_REGISTRY)

        expected = {
            "n08a_excellence_drafting": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
            "n08b_impact_drafting": "docs/tier5_deliverables/proposal_sections/impact_section.json",
            "n08c_implementation_drafting": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
        }
        for node_id, expected_file in expected.items():
            paths = _get_artifacts_produced_by_node(
                node_id, tmp_path, manifest_path=manifest_path
            )
            assert expected_file in paths, (
                f"{node_id}: expected {expected_file} in {paths}"
            )
            # Must NOT contain the directory-level path
            assert "docs/tier5_deliverables/proposal_sections/" not in paths, (
                f"{node_id}: should not have directory-level path in {paths}"
            )

    def test_wrong_section_does_not_satisfy_gate(self, tmp_path: Path) -> None:
        """n08a gate must NOT pass when only impact_section.json exists."""
        manifest_path = _write_manifest(tmp_path, _PHASE8_ARTIFACT_REGISTRY)

        # Write impact_section.json (n08b's artifact) but NOT excellence_section.json
        _write_json(
            tmp_path / "docs/tier5_deliverables/proposal_sections/impact_section.json",
            {"schema_id": "orch.tier5.impact_section.v1", "content": "test"},
        )
        _write_json(
            tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/placeholder.json",
            {"placeholder": True},
        )

        result = _determine_can_evaluate_exit_gate(
            "n08a_excellence_drafting",
            tmp_path,
            manifest_path=manifest_path,
        )
        assert result is False, (
            "n08a gate should NOT pass when only impact_section.json exists"
        )


# ===========================================================================
# End-to-end: skill artifact write -> auditable resolution -> gate discovery
# ===========================================================================


class TestArtifactPipelineEndToEnd:
    """Simulates the complete pipeline for each Phase 8 drafting node:
    skill writes artifact -> _resolve_auditable_artifact finds it ->
    _determine_can_evaluate_exit_gate confirms gate readiness."""

    @pytest.mark.parametrize(
        "node_id,filename",
        [
            ("n08a_excellence_drafting", "excellence_section.json"),
            ("n08b_impact_drafting", "impact_section.json"),
            ("n08c_implementation_drafting", "implementation_section.json"),
        ],
    )
    def test_pipeline(self, tmp_path: Path, node_id: str, filename: str) -> None:
        manifest_path = _write_manifest(tmp_path, _PHASE8_ARTIFACT_REGISTRY)

        # Step 1: Simulate skill writing artifact to canonical path
        artifact_rel = f"docs/tier5_deliverables/proposal_sections/{filename}"
        artifact_data = {
            "schema_id": f"orch.tier5.{filename.replace('.json', '')}.v1",
            "run_id": "test-run-001",
            "content": {"sections": ["placeholder"]},
        }
        _write_json(tmp_path / artifact_rel, artifact_data)

        # Also populate the phase8 review dir (required gate-relevant artifact)
        _write_json(
            tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/summary.json",
            {"placeholder": True},
        )

        # Step 2: Resolve auditable artifact (as agent_runtime does for
        # constitutional-compliance-check and traceability-check)
        all_outputs = [artifact_rel]
        auditable = _resolve_auditable_artifact(node_id, all_outputs, tmp_path)
        assert auditable == artifact_rel, (
            f"Expected {artifact_rel}, got {auditable}"
        )

        # Step 3: Confirm gate-relevant artifact discovery passes
        can_evaluate = _determine_can_evaluate_exit_gate(
            node_id, tmp_path, manifest_path=manifest_path
        )
        assert can_evaluate is True, (
            f"Gate readiness check failed for {node_id} after writing {filename}"
        )

    @pytest.mark.parametrize(
        "node_id,filename",
        [
            ("n08a_excellence_drafting", "excellence_section.json"),
            ("n08b_impact_drafting", "impact_section.json"),
            ("n08c_implementation_drafting", "implementation_section.json"),
        ],
    )
    def test_pipeline_fails_without_artifact(self, tmp_path: Path, node_id: str, filename: str) -> None:
        manifest_path = _write_manifest(tmp_path, _PHASE8_ARTIFACT_REGISTRY)

        # Phase 8 review dir exists but NO section artifact
        _write_json(
            tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/summary.json",
            {"placeholder": True},
        )

        # Step 2: No artifact written -> auditable resolution returns None
        auditable = _resolve_auditable_artifact(node_id, [], tmp_path)
        assert auditable is None

        # Step 3: Gate discovery should fail (proposal_sections dir empty/missing)
        can_evaluate = _determine_can_evaluate_exit_gate(
            node_id, tmp_path, manifest_path=manifest_path
        )
        assert can_evaluate is False


# ===========================================================================
# Path consistency: catalog writes_to == _NODE_PRIMARY_AUDITABLE_ARTIFACT
# ===========================================================================


class TestPathConsistency:
    """Verify that the paths in skill_catalog writes_to, _NODE_PRIMARY_AUDITABLE_ARTIFACT,
    and the manifest artifact_registry are all consistent."""

    def test_primary_artifact_mapping_matches_expected_paths(self) -> None:
        expected = {
            "n08a_excellence_drafting": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
            "n08b_impact_drafting": "docs/tier5_deliverables/proposal_sections/impact_section.json",
            "n08c_implementation_drafting": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
            "n08d_assembly": "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json",
        }
        for node_id, expected_path in expected.items():
            assert _NODE_PRIMARY_AUDITABLE_ARTIFACT[node_id] == expected_path, (
                f"{node_id}: expected {expected_path}, got {_NODE_PRIMARY_AUDITABLE_ARTIFACT[node_id]}"
            )

    def test_all_section_paths_under_same_directory(self) -> None:
        """All three section artifacts must live under proposal_sections/."""
        expected_dir = "docs/tier5_deliverables/proposal_sections/"
        for node_id in ["n08a_excellence_drafting", "n08b_impact_drafting", "n08c_implementation_drafting"]:
            path = _NODE_PRIMARY_AUDITABLE_ARTIFACT[node_id]
            assert path.startswith(expected_dir), (
                f"{node_id} artifact {path} is not under {expected_dir}"
            )


# ===========================================================================
# Production manifest invariant: file-level artifact_registry entries
# ===========================================================================


class TestProductionManifestInvariant:
    """Verify the production manifest.compile.yaml declares file-level
    artifact_registry entries for each Phase 8 section node, not a shared
    directory-level entry."""

    @pytest.fixture(autouse=True)
    def _load_production_manifest(self) -> None:
        """Load the production manifest once for all tests in this class."""
        _artifact_registry_cache.clear()
        repo_root = Path(__file__).resolve().parents[2]
        self._repo_root = repo_root
        self._manifest_path = (
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )

    @pytest.mark.parametrize(
        "node_id,expected_file",
        [
            ("n08a_excellence_drafting", "docs/tier5_deliverables/proposal_sections/excellence_section.json"),
            ("n08b_impact_drafting", "docs/tier5_deliverables/proposal_sections/impact_section.json"),
            ("n08c_implementation_drafting", "docs/tier5_deliverables/proposal_sections/implementation_section.json"),
        ],
    )
    def test_node_declares_exact_file_path(self, node_id: str, expected_file: str) -> None:
        """Each section node must produce its exact file, not the directory."""
        paths = _get_artifacts_produced_by_node(
            node_id, self._repo_root, manifest_path=self._manifest_path
        )
        assert expected_file in paths, (
            f"Production manifest: {node_id} should declare {expected_file}, "
            f"got {paths}"
        )

    @pytest.mark.parametrize(
        "node_id",
        [
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
        ],
    )
    def test_node_does_not_declare_directory(self, node_id: str) -> None:
        """No section node should declare the shared directory path."""
        paths = _get_artifacts_produced_by_node(
            node_id, self._repo_root, manifest_path=self._manifest_path
        )
        assert "docs/tier5_deliverables/proposal_sections/" not in paths, (
            f"Production manifest: {node_id} must not declare the directory "
            f"path; found {paths}"
        )
