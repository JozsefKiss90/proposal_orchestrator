"""
Tests for n08d_assembly fixes: skill ordering, artifact registration,
impact D8-01 mislabel, and excellence TRL qualification.

Targeted static tests — no live Claude invocations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.runtime_models import AgentResult, SkillInvocationRecord, SkillResult
from runner.agent_runtime import (
    run_agent,
    _resolve_skill_sequence,
    _get_artifacts_produced_by_node,
    _determine_can_evaluate_exit_gate,
    _load_artifact_registry,
    _resolve_auditable_artifact,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RUN_SKILL_TARGET = "runner.agent_runtime.run_skill"


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear module-level caches between tests."""
    import runner.agent_runtime as _ar
    import runner.skill_runtime as _sr
    _ar._agent_catalog_cache.clear()
    _ar._artifact_registry_cache.clear()
    _ar._node_exit_gate_cache.clear()
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


def _success_skill(outputs: list[str] | None = None) -> SkillResult:
    return SkillResult(
        status="success",
        outputs_written=outputs or [],
    )


def _failure_skill(
    category: str = "MISSING_INPUT",
    reason: str = "test failure",
) -> SkillResult:
    return SkillResult(
        status="failure",
        failure_reason=reason,
        failure_category=category,
    )


def _load_prompt_spec_from_repo() -> str:
    """Load the production proposal_integrator_prompt_spec.md."""
    repo_root = Path(__file__).resolve().parents[2]
    spec_path = (
        repo_root / ".claude" / "agents" / "prompts"
        / "proposal_integrator_prompt_spec.md"
    )
    return spec_path.read_text(encoding="utf-8-sig")


def _load_skill_spec(skill_name: str) -> str:
    """Load a production skill .md file."""
    repo_root = Path(__file__).resolve().parents[2]
    spec_path = repo_root / ".claude" / "skills" / f"{skill_name}.md"
    return spec_path.read_text(encoding="utf-8-sig")


def _load_manifest() -> dict:
    """Load the production manifest.compile.yaml."""
    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "manifest.compile.yaml"
    )
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))


# ===========================================================================
# 1. n08d ORDERING TESTS
# ===========================================================================


class TestN08dSkillOrdering:
    """Verify cross-section-consistency-check runs before audit skills."""

    def test_prompt_spec_mentions_consistency_check_before_audits(self) -> None:
        """The prompt spec must mention cross-section-consistency-check (exact
        skill ID, with hyphens) before proposal-section-traceability-check and
        constitutional-compliance-check."""
        spec = _load_prompt_spec_from_repo()
        pos_cscc = spec.find("cross-section-consistency-check")
        pos_pstc = spec.find("proposal-section-traceability-check")
        pos_ccc = spec.find("constitutional-compliance-check")

        assert pos_cscc >= 0, (
            "cross-section-consistency-check (exact skill ID) not found "
            "in proposal_integrator_prompt_spec.md"
        )
        assert pos_pstc >= 0, (
            "proposal-section-traceability-check not found in prompt spec"
        )
        assert pos_ccc >= 0, (
            "constitutional-compliance-check not found in prompt spec"
        )
        assert pos_cscc < pos_pstc, (
            "cross-section-consistency-check must appear before "
            "proposal-section-traceability-check in prompt spec; "
            f"found at {pos_cscc} vs {pos_pstc}"
        )
        assert pos_cscc < pos_ccc, (
            "cross-section-consistency-check must appear before "
            "constitutional-compliance-check in prompt spec; "
            f"found at {pos_cscc} vs {pos_ccc}"
        )

    def test_resolve_skill_sequence_orders_correctly(self) -> None:
        """_resolve_skill_sequence uses prompt spec mention order. With the
        fixed prompt spec, cross-section-consistency-check must come first."""
        spec = _load_prompt_spec_from_repo()
        skill_ids = [
            "cross-section-consistency-check",
            "proposal-section-traceability-check",
            "constitutional-compliance-check",
        ]
        ordered = _resolve_skill_sequence(
            "proposal_integrator", skill_ids, spec
        )
        assert ordered[0] == "cross-section-consistency-check", (
            f"Expected cross-section-consistency-check first, got {ordered}"
        )
        assert ordered.index("proposal-section-traceability-check") > 0
        assert ordered.index("constitutional-compliance-check") > 0

    def test_audit_skills_get_artifact_path_after_producer(
        self, tmp_path: Path,
    ) -> None:
        """When n08d runs, audit skills receive artifact_path pointing to
        part_b_assembled_draft.json only after cross-section-consistency-check
        has produced it."""
        repo_root = tmp_path

        # Set up agent catalog
        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "agent_catalog.yaml",
            {"agent_catalog": [
                {
                    "id": "proposal_integrator",
                    "reads_from": [
                        "docs/tier5_deliverables/proposal_sections/",
                        "docs/tier2a_instrument_schemas/application_forms/",
                        "docs/tier3_project_instantiation/",
                    ],
                    "writes_to": [
                        "docs/tier5_deliverables/assembled_drafts/"
                        "part_b_assembled_draft.json",
                    ],
                },
            ]},
        )

        # Set up skill catalog
        _write_yaml(
            repo_root / ".claude" / "workflows" / "system_orchestration"
            / "skill_catalog.yaml",
            {"skill_catalog": [
                {
                    "id": "cross-section-consistency-check",
                    "used_by_agents": ["proposal_integrator"],
                    "reads_from": [],
                    "writes_to": [],
                    "constitutional_constraints": [],
                },
                {
                    "id": "proposal-section-traceability-check",
                    "used_by_agents": ["proposal_integrator"],
                    "reads_from": [],
                    "writes_to": [],
                    "constitutional_constraints": [],
                },
                {
                    "id": "constitutional-compliance-check",
                    "used_by_agents": ["proposal_integrator"],
                    "reads_from": [],
                    "writes_to": [],
                    "constitutional_constraints": [],
                },
            ]},
        )

        # Use the PRODUCTION prompt spec (with the fix)
        agent_dir = repo_root / ".claude" / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "proposal_integrator.md").write_text(
            "# proposal_integrator\nTest.", encoding="utf-8"
        )
        prompts_dir = agent_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "proposal_integrator_prompt_spec.md").write_text(
            _load_prompt_spec_from_repo(), encoding="utf-8"
        )

        # Manifest with n08d_assembly artifact
        assembled_draft_path = (
            "docs/tier5_deliverables/assembled_drafts/"
            "part_b_assembled_draft.json"
        )
        manifest_data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {
                    "node_id": "n08d_assembly",
                    "agent": "proposal_integrator",
                    "skills": [
                        "cross-section-consistency-check",
                        "proposal-section-traceability-check",
                        "constitutional-compliance-check",
                    ],
                    "phase_id": "phase_08d_assembly",
                    "exit_gate": "gate_10d_cross_section_consistency",
                },
            ],
            "edge_registry": [],
            "artifact_registry": [
                {
                    "artifact_id": "a_t5_part_b_assembled_draft",
                    "path": assembled_draft_path,
                    "tier": "tier5_deliverable",
                    "produced_by": "n08d_assembly",
                },
            ],
        }
        manifest_path = repo_root / "manifest_test.yaml"
        _write_yaml(manifest_path, manifest_data)

        # Create input dirs (empty is fine — skills are mocked)
        for d in [
            "docs/tier5_deliverables/proposal_sections",
            "docs/tier2a_instrument_schemas/application_forms",
            "docs/tier3_project_instantiation",
        ]:
            (repo_root / d).mkdir(parents=True, exist_ok=True)
        # Write stub input files so agent input resolution passes
        _write_json(
            repo_root / "docs/tier5_deliverables/proposal_sections"
            / "excellence_section.json",
            {"schema_id": "test"},
        )

        captured_calls: list[dict] = []

        def _capture_run_skill(skill_id, run_id, repo_root, inputs=None, **kw):
            ctx = kw.get("caller_context")
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": ctx,
            })
            # cross-section-consistency-check produces the assembled draft
            if skill_id == "cross-section-consistency-check":
                _write_json(
                    repo_root / assembled_draft_path,
                    {"schema_id": "orch.tier5.part_b_assembled_draft.v1",
                     "sections": [], "consistency_log": []},
                )
                return _success_skill([assembled_draft_path])
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture_run_skill):
            result = run_agent(
                agent_id="proposal_integrator",
                node_id="n08d_assembly",
                run_id="run-test-n08d",
                repo_root=repo_root,
                manifest_path=manifest_path,
                skill_ids=[
                    "cross-section-consistency-check",
                    "proposal-section-traceability-check",
                    "constitutional-compliance-check",
                ],
                phase_id="phase_08d_assembly",
            )

        # Verify ordering
        skill_order = [c["skill_id"] for c in captured_calls]
        assert skill_order[0] == "cross-section-consistency-check", (
            f"Expected cross-section-consistency-check first, got {skill_order}"
        )

        # Verify audit skills received artifact_path
        for c in captured_calls:
            if c["skill_id"] in (
                "proposal-section-traceability-check",
                "constitutional-compliance-check",
            ):
                ctx = c["caller_context"]
                assert ctx is not None, (
                    f"Skill {c['skill_id']} should receive caller_context"
                )
                assert ctx.get("artifact_path") == assembled_draft_path, (
                    f"Skill {c['skill_id']} should receive "
                    f"artifact_path={assembled_draft_path!r}, "
                    f"got {ctx.get('artifact_path')!r}"
                )


# ===========================================================================
# 2. n08d ARTIFACT REGISTRY TESTS
# ===========================================================================


class TestN08dArtifactRegistry:
    """Verify n08d produces exact file-level artifact."""

    def test_production_manifest_has_file_level_artifact(self) -> None:
        """The production manifest must declare a file-level (not directory)
        artifact for n08d_assembly at the exact assembled draft path."""
        manifest = _load_manifest()
        registry = manifest.get("artifact_registry", [])

        n08d_artifacts = [
            e for e in registry
            if isinstance(e, dict)
            and (
                e.get("produced_by") == "n08d_assembly"
                or (
                    isinstance(e.get("produced_by"), list)
                    and "n08d_assembly" in e["produced_by"]
                    and len(e["produced_by"]) == 1
                )
            )
        ]

        # Must have at least one sole-producer file-level artifact
        sole_producer_file = [
            e for e in n08d_artifacts
            if e.get("produced_by") == "n08d_assembly"
            and not e.get("path", "").endswith("/")
        ]
        assert len(sole_producer_file) >= 1, (
            "n08d_assembly must have at least one sole-producer file-level "
            f"artifact in artifact_registry; found: {n08d_artifacts}"
        )

        # The exact path must be part_b_assembled_draft.json
        paths = [e["path"] for e in sole_producer_file]
        expected = (
            "docs/tier5_deliverables/assembled_drafts/"
            "part_b_assembled_draft.json"
        )
        assert expected in paths, (
            f"Expected {expected!r} in n08d sole-producer artifacts; "
            f"found: {paths}"
        )

    def test_get_artifacts_produced_by_n08d_returns_exact_file(
        self, tmp_path: Path,
    ) -> None:
        """_get_artifacts_produced_by_node('n08d_assembly') returns the exact
        file path, not a directory."""
        manifest_data = {
            "artifact_registry": [
                {
                    "artifact_id": "a_t5_part_b_assembled_draft",
                    "path": "docs/tier5_deliverables/assembled_drafts/"
                            "part_b_assembled_draft.json",
                    "tier": "tier5_deliverable",
                    "produced_by": "n08d_assembly",
                },
                {
                    "artifact_id": "a_t5_assembled_drafts",
                    "path": "docs/tier5_deliverables/assembled_drafts/",
                    "tier": "tier5_deliverable",
                    "produced_by": "n08f_revision",
                },
            ],
        }
        manifest_path = tmp_path / "manifest.yaml"
        _write_yaml(manifest_path, manifest_data)

        paths = _get_artifacts_produced_by_node(
            "n08d_assembly", tmp_path, manifest_path=manifest_path,
        )
        assert len(paths) == 1
        assert paths[0] == (
            "docs/tier5_deliverables/assembled_drafts/"
            "part_b_assembled_draft.json"
        )

    def test_gate_readiness_true_when_exact_file_exists(
        self, tmp_path: Path,
    ) -> None:
        """can_evaluate_exit_gate is True when the exact assembled draft file
        exists and contains valid JSON."""
        manifest_data = {
            "artifact_registry": [
                {
                    "path": "docs/tier5_deliverables/assembled_drafts/"
                            "part_b_assembled_draft.json",
                    "tier": "tier5_deliverable",
                    "produced_by": "n08d_assembly",
                },
            ],
        }
        manifest_path = tmp_path / "manifest.yaml"
        _write_yaml(manifest_path, manifest_data)

        _write_json(
            tmp_path / "docs" / "tier5_deliverables" / "assembled_drafts"
            / "part_b_assembled_draft.json",
            {"schema_id": "orch.tier5.part_b_assembled_draft.v1",
             "sections": [], "consistency_log": []},
        )

        result = _determine_can_evaluate_exit_gate(
            "n08d_assembly", tmp_path, manifest_path=manifest_path,
        )
        assert result is True

    def test_gate_readiness_false_when_only_sibling_exists(
        self, tmp_path: Path,
    ) -> None:
        """can_evaluate_exit_gate is False when a different file exists in
        assembled_drafts/ but not the exact expected file."""
        manifest_data = {
            "artifact_registry": [
                {
                    "path": "docs/tier5_deliverables/assembled_drafts/"
                            "part_b_assembled_draft.json",
                    "tier": "tier5_deliverable",
                    "produced_by": "n08d_assembly",
                },
            ],
        }
        manifest_path = tmp_path / "manifest.yaml"
        _write_yaml(manifest_path, manifest_data)

        # Write a sibling file, NOT the expected file
        _write_json(
            tmp_path / "docs" / "tier5_deliverables" / "assembled_drafts"
            / "some_other.json",
            {"data": "not the assembled draft"},
        )

        result = _determine_can_evaluate_exit_gate(
            "n08d_assembly", tmp_path, manifest_path=manifest_path,
        )
        assert result is False

    def test_multi_producer_directory_not_gate_relevant_for_n08d(
        self, tmp_path: Path,
    ) -> None:
        """A directory artifact with produced_by as a multi-element list
        must not be returned as a gate-relevant artifact for n08d."""
        manifest_data = {
            "artifact_registry": [
                {
                    "path": "docs/tier5_deliverables/assembled_drafts/",
                    "tier": "tier5_deliverable",
                    "produced_by": ["n08d_assembly", "n08f_revision"],
                },
            ],
        }
        manifest_path = tmp_path / "manifest.yaml"
        _write_yaml(manifest_path, manifest_data)

        paths = _get_artifacts_produced_by_node(
            "n08d_assembly", tmp_path, manifest_path=manifest_path,
        )
        assert len(paths) == 0, (
            "Multi-producer directory artifact should not be gate-relevant "
            f"for n08d; got {paths}"
        )

    def test_production_manifest_n08d_does_not_declare_only_directory(
        self,
    ) -> None:
        """The production manifest must not declare ONLY a directory-level
        artifact for n08d. It must have a file-level artifact."""
        manifest = _load_manifest()
        registry = manifest.get("artifact_registry", [])

        n08d_sole_producer = [
            e for e in registry
            if isinstance(e, dict)
            and e.get("produced_by") == "n08d_assembly"
        ]

        file_level = [
            e for e in n08d_sole_producer
            if not e.get("path", "").endswith("/")
        ]
        assert len(file_level) >= 1, (
            "n08d_assembly must have at least one file-level sole-producer "
            f"artifact; found only: {n08d_sole_producer}"
        )


# ===========================================================================
# 3. IMPACT CONTENT-SPEC TESTS (D8-01 mislabel)
# ===========================================================================


class TestImpactD801Constraint:
    """Verify impact-section-drafting.md forbids D8-01 orchestration mislabel."""

    def test_d801_constraint_present(self) -> None:
        """The skill spec must contain a constraint preventing D8-01 from
        being cited as the External Tool/API Orchestration Layer."""
        spec = _load_skill_spec("impact-section-drafting")
        assert "D8-01" in spec, "D8-01 should be mentioned in constraint"
        assert "evaluation framework" in spec.lower() or \
               "benchmark specification" in spec.lower(), (
            "D8-01 must be described as evaluation framework / benchmark spec"
        )

    def test_d801_not_orchestration_layer(self) -> None:
        """The skill spec must explicitly state that D8-01 MUST NOT be cited
        as the orchestration layer."""
        spec = _load_skill_spec("impact-section-drafting")
        # Check for the prohibition
        assert re.search(
            r"D8-01.*MUST NOT.*orchestration",
            spec,
            re.IGNORECASE | re.DOTALL,
        ) or re.search(
            r"D8-01.*must not.*orchestration",
            spec,
            re.IGNORECASE | re.DOTALL,
        ), (
            "impact-section-drafting.md must prohibit citing D8-01 as "
            "the orchestration layer"
        )

    def test_out9_grounding_guidance(self) -> None:
        """The skill spec must guide OUT-9 as the orchestration-layer
        grounding when no dedicated deliverable exists."""
        spec = _load_skill_spec("impact-section-drafting")
        assert "OUT-9" in spec, (
            "impact-section-drafting.md must mention OUT-9 as orchestration-"
            "layer grounding"
        )
        assert "outcomes.json" in spec or "architecture_inputs" in spec, (
            "impact-section-drafting.md must reference architecture_inputs/"
            "outcomes.json for OUT-9 grounding"
        )

    def test_deliverable_identity_constraint_is_gate_critical(self) -> None:
        """The deliverable identity constraint must be marked GATE-CRITICAL."""
        spec = _load_skill_spec("impact-section-drafting")
        # Find the constraint section
        idx_d801 = spec.find("Deliverable identity constraint")
        assert idx_d801 >= 0, (
            "impact-section-drafting.md must contain a 'Deliverable identity "
            "constraint' section"
        )
        # Check it's marked GATE-CRITICAL
        constraint_section = spec[idx_d801:idx_d801 + 200]
        assert "GATE-CRITICAL" in constraint_section, (
            "Deliverable identity constraint must be marked GATE-CRITICAL"
        )


# ===========================================================================
# 4. EXCELLENCE TRL CONTENT-SPEC TESTS
# ===========================================================================


class TestExcellenceTRLQualification:
    """Verify excellence-section-drafting.md requires qualified TRL language."""

    def test_trl_constraint_present(self) -> None:
        """The skill spec must contain a TRL qualification constraint."""
        spec = _load_skill_spec("excellence-section-drafting")
        assert "TRL qualification" in spec or "TRL" in spec, (
            "excellence-section-drafting.md must contain TRL constraint"
        )

    def test_forbids_unqualified_trl5(self) -> None:
        """The skill spec must forbid unqualified 'project targets TRL 5
        by project end'."""
        spec = _load_skill_spec("excellence-section-drafting")
        # Check for the prohibition
        assert re.search(
            r"[Ff]orbidden.*unqualified",
            spec,
            re.DOTALL,
        ) or re.search(
            r"Do NOT.*unqualified.*TRL",
            spec,
            re.DOTALL,
        ), (
            "excellence-section-drafting.md must forbid unqualified TRL claims"
        )

    def test_requires_wp4_out3_trl4_distinction(self) -> None:
        """The skill spec must require distinguishing WP4/OUT-3 TRL 4 from
        integrated framework TRL 5."""
        spec = _load_skill_spec("excellence-section-drafting")
        assert "WP4" in spec or "WP4/OUT-3" in spec, (
            "excellence-section-drafting.md must mention WP4/OUT-3"
        )
        assert "TRL 4" in spec, (
            "excellence-section-drafting.md must mention TRL 4 for WP4/OUT-3"
        )
        assert "TRL 5" in spec, (
            "excellence-section-drafting.md must mention TRL 5 for "
            "demonstrators/framework"
        )

    def test_trl_constraint_is_gate_critical(self) -> None:
        """The TRL qualification constraint must be marked GATE-CRITICAL."""
        spec = _load_skill_spec("excellence-section-drafting")
        idx_trl = spec.find("TRL qualification constraint")
        assert idx_trl >= 0, (
            "excellence-section-drafting.md must contain a 'TRL qualification "
            "constraint' section"
        )
        constraint_section = spec[idx_trl:idx_trl + 200]
        assert "GATE-CRITICAL" in constraint_section, (
            "TRL qualification constraint must be marked GATE-CRITICAL"
        )

    def test_permitted_wording_patterns(self) -> None:
        """The skill spec must provide permitted wording patterns showing
        the TRL distinction."""
        spec = _load_skill_spec("excellence-section-drafting")
        assert "Permitted wording" in spec, (
            "excellence-section-drafting.md must provide permitted wording "
            "patterns for TRL"
        )
        # At least one pattern must mention both TRL 5 and TRL 4
        idx = spec.find("Permitted wording")
        section = spec[idx:idx + 1000]
        assert "TRL 5" in section and "TRL 4" in section, (
            "Permitted wording section must include both TRL 5 and TRL 4"
        )


# ===========================================================================
# 5. CROSS-SECTION CONSISTENCY FIXTURE TESTS
# ===========================================================================


def _make_minimal_assembled_draft(
    *,
    impact_ei05_content: str = "",
    excellence_trl_content: str = "",
    impact_d801_source_ref: str | None = None,
    excellence_trl_source_ref: str | None = None,
) -> dict:
    """Build a minimal assembled draft fixture for consistency checking."""
    draft = {
        "schema_id": "orch.tier5.part_b_assembled_draft.v1",
        "run_id": "test-fixture",
        "sections": [
            {
                "section_id": "excellence",
                "criterion": "Excellence",
                "order": 1,
                "artifact_path": "docs/tier5_deliverables/proposal_sections/"
                                 "excellence_section.json",
                "word_count": 500,
            },
            {
                "section_id": "impact",
                "criterion": "Impact",
                "order": 2,
                "artifact_path": "docs/tier5_deliverables/proposal_sections/"
                                 "impact_section.json",
                "word_count": 500,
            },
            {
                "section_id": "implementation",
                "criterion": "Implementation",
                "order": 3,
                "artifact_path": "docs/tier5_deliverables/proposal_sections/"
                                 "implementation_section.json",
                "word_count": 500,
            },
        ],
        "consistency_log": [],
    }
    return draft


def _make_impact_section(
    *,
    ei05_content: str = "",
    ei05_source_ref: str = "",
) -> dict:
    """Build a minimal impact_section.json fixture."""
    return {
        "schema_id": "orch.tier5.impact_section.v1",
        "run_id": "test-fixture",
        "criterion": "Impact",
        "sub_sections": [
            {
                "sub_section_id": "B.2.1",
                "title": "Expected impacts",
                "content": ei05_content,
                "word_count": len(ei05_content.split()),
            },
        ],
        "impact_pathway_refs": ["PATH-EI-05"],
        "dec_coverage": {
            "dissemination_addressed": True,
            "exploitation_addressed": True,
            "communication_addressed": True,
        },
        "validation_status": {
            "overall_status": "confirmed",
            "claim_statuses": [
                {
                    "claim_id": "EI-05",
                    "claim_summary": "External Tool Orchestration Layer",
                    "status": "confirmed",
                    "source_ref": ei05_source_ref,
                },
            ],
        },
        "traceability_footer": {
            "primary_sources": [],
            "no_unsupported_claims_declaration": True,
        },
    }


def _make_excellence_section(*, trl_content: str = "") -> dict:
    """Build a minimal excellence_section.json fixture."""
    return {
        "schema_id": "orch.tier5.excellence_section.v1",
        "run_id": "test-fixture",
        "criterion": "Excellence",
        "sub_sections": [
            {
                "sub_section_id": "B.1.1",
                "title": "Objectives and ambition",
                "content": trl_content,
                "word_count": len(trl_content.split()),
            },
        ],
        "validation_status": {
            "overall_status": "confirmed",
            "claim_statuses": [],
        },
        "traceability_footer": {
            "primary_sources": [],
            "no_unsupported_claims_declaration": True,
        },
    }


class TestCrossSectionConsistencyFixtures:
    """Fixture-based tests for cross-section consistency detection.

    These test the data patterns that the cross-section-consistency-check
    skill should detect. They verify the fix expectations without invoking
    Claude.
    """

    def test_d801_mislabel_is_detectable(self) -> None:
        """An impact section citing D8-01 as orchestration layer should be
        flagged as inconsistent with implementation's D8-01 definition."""
        impact = _make_impact_section(
            ei05_content=(
                "The External Tool and API Orchestration Layer (OUT-9, D8-01) "
                "provides typed tool registry."
            ),
            ei05_source_ref="Tier 4: impact_architecture.json PATH-EI-05",
        )
        # D8-01 in implementation is "Evaluation framework and benchmark spec"
        # The mislabel: impact says D8-01 = orchestration layer
        ei05_claim = impact["validation_status"]["claim_statuses"][0]
        # Simulating the check: content says "(OUT-9, D8-01)" for orch layer
        content = impact["sub_sections"][0]["content"]
        assert "D8-01" in content
        # The content wrongly associates D8-01 with orchestration layer
        assert "Orchestration Layer" in content or "orchestration" in content.lower()
        # This combination is what the cross-section check should flag as CC-04

    def test_corrected_d801_wording_is_consistent(self) -> None:
        """Impact section with corrected OUT-9 wording (not citing D8-01 as
        orchestration layer) should not trigger CC-04."""
        impact = _make_impact_section(
            ei05_content=(
                "The External Tool and API Orchestration Layer (OUT-9), "
                "described as a cross-cutting capability in the project "
                "outcomes and architecture inputs, provides typed tool "
                "registry. Its impact is validated through the WP8 "
                "evaluation framework and benchmark suite, including "
                "D8-01 and D8-02, but D8-01 itself is the evaluation "
                "framework specification, not the orchestration-layer "
                "artifact."
            ),
            ei05_source_ref="Tier 3: outcomes.json OUT-9",
        )
        content = impact["sub_sections"][0]["content"]
        # D8-01 is mentioned but NOT as the orchestration layer
        assert "D8-01 itself is the evaluation framework" in content
        # OUT-9 is the orchestration layer grounding
        assert "(OUT-9)" in content

    def test_unqualified_trl5_creates_ambiguity(self) -> None:
        """Excellence claiming unqualified TRL 5 while impact has OUT-3
        at TRL 4 creates detectable ambiguity (CC-09)."""
        excellence = _make_excellence_section(
            trl_content="The project targets TRL 5 by project end."
        )
        # This unqualified claim conflicts with OUT-3 at TRL 4
        content = excellence["sub_sections"][0]["content"]
        assert "TRL 5" in content
        # Check it's unqualified (no mention of exceptions)
        assert "TRL 4" not in content
        assert "WP4" not in content
        # This pattern should trigger CC-09

    def test_qualified_trl_wording_resolves_ambiguity(self) -> None:
        """Excellence with qualified TRL language distinguishing framework
        TRL 5 from WP4/OUT-3 TRL 4 should not trigger CC-09."""
        excellence = _make_excellence_section(
            trl_content=(
                "MAESTRO targets TRL 5 validation for the integrated "
                "framework and the healthcare/manufacturing/logistics "
                "demonstrators by project end, while foundational "
                "coordination-protocol outputs such as WP4/OUT-3 remain "
                "positioned at TRL 4 where their primary contribution is "
                "formal specification, verification, and protocol proof."
            )
        )
        content = excellence["sub_sections"][0]["content"]
        assert "TRL 5" in content
        assert "TRL 4" in content
        assert "WP4/OUT-3" in content
        # Both TRL levels are explicitly addressed — no ambiguity
