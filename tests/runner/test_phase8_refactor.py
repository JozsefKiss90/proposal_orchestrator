"""
Unit tests for Phase A of the Phase 8 refactoring plan.

Covers:
  - PHASE_8_NODE_IDS membership and HARD_BLOCK propagation (run_context.py)
  - Gate result paths for gates 10a-10d (gate_result_registry.py)
  - Upstream inputs for new gates (upstream_inputs.py)
  - Node auditable fallback dirs (agent_runtime.py)
  - New predicate functions: schema_id_matches, no_unresolved_material_claims,
    impact_pathways_covered, implementation_coverage_complete,
    cross_section_consistency (criterion_predicates.py)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.run_context import PHASE_8_NODE_IDS, RunContext
from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.upstream_inputs import UPSTREAM_REQUIRED_INPUTS
from runner.agent_runtime import (
    _NODE_AUDITABLE_FALLBACK_DIRS,
    _resolve_auditable_artifact,
)
from runner.predicates.criterion_predicates import (
    cross_section_consistency,
    impact_pathways_covered,
    implementation_coverage_complete,
    no_unresolved_material_claims,
    schema_id_matches,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===========================================================================
# PHASE_8_NODE_IDS (run_context.py)
# ===========================================================================


class TestPhase8NodeIds:
    def test_contains_all_6_new_ids(self) -> None:
        expected = {
            "n08a_excellence_drafting",
            "n08b_impact_drafting",
            "n08c_implementation_drafting",
            "n08d_assembly",
            "n08e_evaluator_review",
            "n08f_revision",
        }
        assert PHASE_8_NODE_IDS == frozenset(expected)

    def test_does_not_contain_old_ids(self) -> None:
        old_ids = {
            "n08a_section_drafting",
            "n08b_assembly",
            "n08c_evaluator_review",
            "n08d_revision",
        }
        assert PHASE_8_NODE_IDS.isdisjoint(old_ids)

    def test_hard_block_freezes_all_6_nodes(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="hb-test")
        ctx.mark_hard_block_downstream()
        for node_id in PHASE_8_NODE_IDS:
            assert ctx.get_node_state(node_id) == "hard_block_upstream"

    def test_hard_block_persists_after_save_load(self, tmp_path: Path) -> None:
        ctx = RunContext.initialize(tmp_path, run_id="hb-persist")
        ctx.mark_hard_block_downstream()
        ctx.save()
        reloaded = RunContext.load(tmp_path, "hb-persist")
        for node_id in PHASE_8_NODE_IDS:
            assert reloaded.get_node_state(node_id) == "hard_block_upstream"


# ===========================================================================
# Gate result paths (gate_result_registry.py)
# ===========================================================================


class TestGateResultPaths:
    def test_gate_10a_path_exists(self) -> None:
        assert "gate_10a_excellence_completeness" in GATE_RESULT_PATHS
        assert GATE_RESULT_PATHS["gate_10a_excellence_completeness"] == (
            "phase_outputs/phase8_drafting_review/gate_10a_result.json"
        )

    def test_gate_10b_path_exists(self) -> None:
        assert "gate_10b_impact_completeness" in GATE_RESULT_PATHS
        assert GATE_RESULT_PATHS["gate_10b_impact_completeness"] == (
            "phase_outputs/phase8_drafting_review/gate_10b_result.json"
        )

    def test_gate_10c_path_exists(self) -> None:
        assert "gate_10c_implementation_completeness" in GATE_RESULT_PATHS
        assert GATE_RESULT_PATHS["gate_10c_implementation_completeness"] == (
            "phase_outputs/phase8_drafting_review/gate_10c_result.json"
        )

    def test_gate_10d_path_exists(self) -> None:
        assert "gate_10d_cross_section_consistency" in GATE_RESULT_PATHS
        assert GATE_RESULT_PATHS["gate_10d_cross_section_consistency"] == (
            "phase_outputs/phase8_drafting_review/gate_10d_result.json"
        )

    def test_old_gate_10_removed(self) -> None:
        assert "gate_10_part_b_completeness" not in GATE_RESULT_PATHS

    def test_gate_11_and_12_unchanged(self) -> None:
        assert "gate_11_review_closure" in GATE_RESULT_PATHS
        assert "gate_12_constitutional_compliance" in GATE_RESULT_PATHS


# ===========================================================================
# Upstream inputs (upstream_inputs.py)
# ===========================================================================


class TestUpstreamInputs:
    def test_gate_10a_inputs(self) -> None:
        inputs = UPSTREAM_REQUIRED_INPUTS["gate_10a_excellence_completeness"]
        assert "docs/tier5_deliverables/proposal_sections/excellence_section.json" in inputs
        assert any("budget_gate_assessment" in p for p in inputs)

    def test_gate_10b_inputs(self) -> None:
        inputs = UPSTREAM_REQUIRED_INPUTS["gate_10b_impact_completeness"]
        assert "docs/tier5_deliverables/proposal_sections/impact_section.json" in inputs

    def test_gate_10c_inputs(self) -> None:
        inputs = UPSTREAM_REQUIRED_INPUTS["gate_10c_implementation_completeness"]
        assert "docs/tier5_deliverables/proposal_sections/implementation_section.json" in inputs

    def test_gate_10d_inputs(self) -> None:
        inputs = UPSTREAM_REQUIRED_INPUTS["gate_10d_cross_section_consistency"]
        assert "docs/tier5_deliverables/proposal_sections/excellence_section.json" in inputs
        assert "docs/tier5_deliverables/proposal_sections/impact_section.json" in inputs
        assert "docs/tier5_deliverables/proposal_sections/implementation_section.json" in inputs
        assert "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json" in inputs

    def test_gate_11_updated_path(self) -> None:
        inputs = UPSTREAM_REQUIRED_INPUTS["gate_11_review_closure"]
        assert "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json" in inputs

    def test_gate_12_updated_path(self) -> None:
        inputs = UPSTREAM_REQUIRED_INPUTS["gate_12_constitutional_compliance"]
        assert "docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json" in inputs

    def test_old_gate_10_removed(self) -> None:
        assert "gate_10_part_b_completeness" not in UPSTREAM_REQUIRED_INPUTS


# ===========================================================================
# Node auditable fallback dirs (agent_runtime.py)
# ===========================================================================


class TestNodeAuditableFallbackDirs:
    def test_new_excellence_drafting_node(self) -> None:
        dirs = _NODE_AUDITABLE_FALLBACK_DIRS["n08a_excellence_drafting"]
        assert "docs/tier5_deliverables/proposal_sections" in dirs

    def test_new_impact_drafting_node(self) -> None:
        dirs = _NODE_AUDITABLE_FALLBACK_DIRS["n08b_impact_drafting"]
        assert "docs/tier5_deliverables/proposal_sections" in dirs

    def test_new_implementation_drafting_node(self) -> None:
        dirs = _NODE_AUDITABLE_FALLBACK_DIRS["n08c_implementation_drafting"]
        assert "docs/tier5_deliverables/proposal_sections" in dirs

    def test_assembly_node(self) -> None:
        dirs = _NODE_AUDITABLE_FALLBACK_DIRS["n08d_assembly"]
        assert "docs/tier5_deliverables/assembled_drafts" in dirs

    def test_evaluator_review_node(self) -> None:
        dirs = _NODE_AUDITABLE_FALLBACK_DIRS["n08e_evaluator_review"]
        assert "docs/tier5_deliverables/review_packets" in dirs
        assert "docs/tier5_deliverables/assembled_drafts" in dirs

    def test_revision_node(self) -> None:
        dirs = _NODE_AUDITABLE_FALLBACK_DIRS["n08f_revision"]
        assert "docs/tier5_deliverables/assembled_drafts" in dirs
        assert "docs/tier5_deliverables/proposal_sections" in dirs
        assert "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review" in dirs

    def test_old_node_ids_absent(self) -> None:
        for old_id in ["n08a_section_drafting", "n08b_assembly",
                        "n08c_evaluator_review", "n08d_revision"]:
            assert old_id not in _NODE_AUDITABLE_FALLBACK_DIRS

    def test_resolve_auditable_from_fallback(self, tmp_path: Path) -> None:
        sections_dir = tmp_path / "docs" / "tier5_deliverables" / "proposal_sections"
        sections_dir.mkdir(parents=True)
        _write_json(
            sections_dir / "excellence_section.json",
            {"schema_id": "test", "content": "test"},
        )
        result = _resolve_auditable_artifact(
            "n08a_excellence_drafting", [], tmp_path
        )
        assert result is not None
        assert "excellence_section.json" in result


# ===========================================================================
# Predicate: schema_id_matches
# ===========================================================================


class TestSchemaIdMatches:
    def test_pass_when_matches(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "art.json",
            {"schema_id": "orch.tier5.excellence_section.v1", "data": "ok"},
        )
        result = schema_id_matches(
            "art.json",
            "orch.tier5.excellence_section.v1",
            repo_root=tmp_path,
        )
        assert result.passed

    def test_fail_when_mismatch(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "art.json",
            {"schema_id": "orch.tier5.impact_section.v1"},
        )
        result = schema_id_matches(
            "art.json",
            "orch.tier5.excellence_section.v1",
            repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "mismatch" in result.reason.lower()

    def test_fail_when_missing_field(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "art.json", {"data": "no schema_id"})
        result = schema_id_matches(
            "art.json", "orch.tier5.excellence_section.v1", repo_root=tmp_path
        )
        assert not result.passed
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_fail_when_file_missing(self, tmp_path: Path) -> None:
        result = schema_id_matches(
            "nonexistent.json", "orch.tier5.v1", repo_root=tmp_path
        )
        assert not result.passed
        assert result.failure_category == "MISSING_MANDATORY_INPUT"


# ===========================================================================
# Predicate: no_unresolved_material_claims
# ===========================================================================


class TestNoUnresolvedMaterialClaims:
    def test_pass_when_confirmed(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "section.json",
            {"validation_status": {"overall_status": "confirmed"}},
        )
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        assert result.passed

    def test_fail_when_unresolved(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "section.json",
            {"validation_status": {"overall_status": "unresolved"}},
        )
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        assert not result.passed
        assert result.failure_category == "POLICY_VIOLATION"

    def test_pass_when_no_validation_status(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {"content": "ok"})
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        assert result.passed

    def test_pass_when_inferred(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / "section.json",
            {"validation_status": {"overall_status": "inferred"}},
        )
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        assert result.passed


# ===========================================================================
# Predicate: impact_pathways_covered
# ===========================================================================


class TestImpactPathwaysCovered:
    def test_all_mapped_canonical_key(self, tmp_path: Path) -> None:
        """Canonical Phase 5 artifact uses 'impact_pathways'."""
        _write_json(tmp_path / "section.json", {
            "impact_pathway_refs": ["pw1", "pw2"],
            "dec_coverage": {
                "dissemination_addressed": True,
                "exploitation_addressed": True,
                "communication_addressed": True,
            },
        })
        _write_json(tmp_path / "arch.json", {
            "impact_pathways": [
                {"pathway_id": "pw1"},
                {"pathway_id": "pw2"},
            ],
        })
        result = impact_pathways_covered(
            "section.json", "arch.json", repo_root=tmp_path
        )
        assert result.passed

    def test_fallback_pathways_key(self, tmp_path: Path) -> None:
        """Falls back to 'pathways' when 'impact_pathways' is absent."""
        _write_json(tmp_path / "section.json", {
            "impact_pathway_refs": ["pw1"],
            "dec_coverage": {
                "dissemination_addressed": True,
                "exploitation_addressed": True,
                "communication_addressed": True,
            },
        })
        _write_json(tmp_path / "arch.json", {
            "pathways": [{"pathway_id": "pw1"}],
        })
        result = impact_pathways_covered(
            "section.json", "arch.json", repo_root=tmp_path
        )
        assert result.passed

    def test_missing_pathway(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "impact_pathway_refs": ["pw1"],
            "dec_coverage": {
                "dissemination_addressed": True,
                "exploitation_addressed": True,
                "communication_addressed": True,
            },
        })
        _write_json(tmp_path / "arch.json", {
            "impact_pathways": [
                {"pathway_id": "pw1"},
                {"pathway_id": "pw2"},
            ],
        })
        result = impact_pathways_covered(
            "section.json", "arch.json", repo_root=tmp_path
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert "pw2" in str(result.details.get("missing_pathways", []))

    def test_dec_gap_detected(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "impact_pathway_refs": ["pw1"],
            "dec_coverage": {
                "dissemination_addressed": True,
                "exploitation_addressed": False,
                "communication_addressed": True,
            },
        })
        _write_json(tmp_path / "arch.json", {
            "pathways": [{"pathway_id": "pw1"}],
        })
        result = impact_pathways_covered(
            "section.json", "arch.json", repo_root=tmp_path
        )
        assert not result.passed
        assert "exploitation_addressed" in str(result.details.get("dec_gaps", []))

    def test_vacuous_pass_empty_architecture(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "impact_pathway_refs": [],
        })
        _write_json(tmp_path / "arch.json", {"pathways": []})
        result = impact_pathways_covered(
            "section.json", "arch.json", repo_root=tmp_path
        )
        assert result.passed


# ===========================================================================
# Predicate: implementation_coverage_complete
# ===========================================================================


class TestImplementationCoverageComplete:
    def test_complete_coverage(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "wp_table_refs": ["WP1", "WP2"],
            "gantt_ref": "gantt.json",
            "milestone_refs": ["MS1"],
            "risk_register_ref": "risk.json",
        })
        _write_json(tmp_path / "wp.json", {
            "work_packages": [
                {"wp_id": "WP1"},
                {"wp_id": "WP2"},
            ],
        })
        _write_json(tmp_path / "gantt.json", {"timeline": []})
        result = implementation_coverage_complete(
            "section.json", "wp.json", "gantt.json", repo_root=tmp_path
        )
        assert result.passed

    def test_missing_wp_reference(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "wp_table_refs": ["WP1"],
            "gantt_ref": "gantt.json",
            "milestone_refs": ["MS1"],
            "risk_register_ref": "risk.json",
        })
        _write_json(tmp_path / "wp.json", {
            "work_packages": [
                {"wp_id": "WP1"},
                {"wp_id": "WP2"},
            ],
        })
        _write_json(tmp_path / "gantt.json", {"timeline": []})
        result = implementation_coverage_complete(
            "section.json", "wp.json", "gantt.json", repo_root=tmp_path
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert "WP2" in str(result.details.get("missing_wps", []))

    def test_missing_gantt_ref(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "wp_table_refs": ["WP1"],
            "gantt_ref": "",
            "milestone_refs": ["MS1"],
            "risk_register_ref": "risk.json",
        })
        _write_json(tmp_path / "wp.json", {"work_packages": [{"wp_id": "WP1"}]})
        _write_json(tmp_path / "gantt.json", {"timeline": []})
        result = implementation_coverage_complete(
            "section.json", "wp.json", "gantt.json", repo_root=tmp_path
        )
        assert not result.passed
        assert "gantt_ref" in result.details.get("missing_fields", [])

    def test_missing_risk_register_ref(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "wp_table_refs": ["WP1"],
            "gantt_ref": "gantt.json",
            "milestone_refs": ["MS1"],
            "risk_register_ref": "",
        })
        _write_json(tmp_path / "wp.json", {"work_packages": [{"wp_id": "WP1"}]})
        _write_json(tmp_path / "gantt.json", {"timeline": []})
        result = implementation_coverage_complete(
            "section.json", "wp.json", "gantt.json", repo_root=tmp_path
        )
        assert not result.passed
        assert "risk_register_ref" in result.details.get("missing_fields", [])


# ===========================================================================
# Predicate: cross_section_consistency
# ===========================================================================


class TestCrossSectionConsistency:
    def test_pass_no_inconsistencies(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "assembled.json", {
            "sections": [
                {"section_id": "s1", "criterion": "Excellence", "order": 1, "artifact_path": "a.json"},
                {"section_id": "s2", "criterion": "Impact", "order": 2, "artifact_path": "b.json"},
                {"section_id": "s3", "criterion": "Implementation", "order": 3, "artifact_path": "c.json"},
            ],
            "consistency_log": [
                {"check_id": "chk1", "status": "consistent", "description": "test"},
            ],
        })
        result = cross_section_consistency(
            "assembled.json",
            "sections/",
            "tier3/",
            repo_root=tmp_path,
        )
        assert result.passed

    def test_fail_inconsistency_flagged(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "assembled.json", {
            "sections": [
                {"section_id": "s1", "criterion": "Excellence", "order": 1, "artifact_path": "a.json"},
                {"section_id": "s2", "criterion": "Impact", "order": 2, "artifact_path": "b.json"},
                {"section_id": "s3", "criterion": "Implementation", "order": 3, "artifact_path": "c.json"},
            ],
            "consistency_log": [
                {"check_id": "partner_names", "status": "inconsistency_flagged",
                 "description": "Partner ACME in Excellence but not in Impact"},
            ],
        })
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert "partner_names" in result.details.get("flagged_checks", [])

    def test_fail_wrong_section_count(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "assembled.json", {
            "sections": [
                {"section_id": "s1", "criterion": "Excellence", "order": 1, "artifact_path": "a.json"},
            ],
            "consistency_log": [],
        })
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_fail_file_missing(self, tmp_path: Path) -> None:
        result = cross_section_consistency(
            "nonexistent.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "MISSING_MANDATORY_INPUT"


# ===========================================================================
# Gate evaluator registry — new predicates are registered
# ===========================================================================


class TestPredicateRegistry:
    def test_new_predicates_in_registry(self) -> None:
        from runner.gate_evaluator import PREDICATE_REGISTRY

        for name in [
            "schema_id_matches",
            "no_unresolved_material_claims",
            "impact_pathways_covered",
            "implementation_coverage_complete",
            "cross_section_consistency",
        ]:
            assert name in PREDICATE_REGISTRY, f"{name} not in PREDICATE_REGISTRY"
