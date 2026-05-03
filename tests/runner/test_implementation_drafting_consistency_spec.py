"""
Targeted tests for Implementation drafting consistency invariants (CCR-5, CCR-6, CCR-7).

Verifies that implementation-section-drafting.md contains project-agnostic rules
enforcing:
  1. Complete measurable_target preservation (no metric compression)
  2. Objective ownership vs integration/support role separation
  3. Pre-output consistency self-check
  4. validation_status.claim_statuses[] metric completeness

Also includes artifact-level fixture tests that exercise the existing
cross_section_consistency predicate for Implementation-specific failures.

All tests are static — no live Claude invocations.
All fixture data is project-agnostic (no hard-coded real project IDs).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"
IMPLEMENTATION_SPEC = SKILLS_DIR / "implementation-section-drafting.md"


def _read_spec() -> str:
    return IMPLEMENTATION_SPEC.read_text(encoding="utf-8")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===========================================================================
# 1. SPEC INVARIANT — METRIC PRESERVATION
# ===========================================================================


class TestSpecMetricPreservation:
    """Implementation spec requires all measurable_target components preserved."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_requires_all_measurable_target_components(self) -> None:
        """Spec mandates preserving every metric component of measurable_target."""
        assert "measurable_target" in self.spec
        assert "ALL components must appear" in self.spec or \
               "all measurable_target components" in self.spec.lower() or \
               "every metric component" in self.spec.lower()

    def test_spec_mentions_conjunctions(self) -> None:
        """Spec explicitly addresses AND/conjunction handling."""
        assert "AND" in self.spec
        assert "conjunct" in self.spec.lower() or "conjunction" in self.spec.lower()

    def test_spec_mentions_ccr5(self) -> None:
        """Spec defines CCR-5 for metric preservation."""
        assert "CCR-5" in self.spec

    def test_spec_mentions_gate_critical(self) -> None:
        """CCR-5 is marked GATE-CRITICAL."""
        assert "GATE-CRITICAL" in self.spec


# ===========================================================================
# 2. SPEC INVARIANT — NO METRIC COMPRESSION
# ===========================================================================


class TestSpecNoMetricCompression:
    """Implementation spec forbids compressing dual/multi-metric targets."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_forbids_single_metric_compression(self) -> None:
        """Spec explicitly prohibits compressing a multi-metric target into one."""
        spec_lower = self.spec.lower()
        assert "compressing" in spec_lower or "compress" in spec_lower

    def test_spec_forbids_retaining_only_first_target(self) -> None:
        """Spec forbids retaining only the first quantitative target."""
        assert "Retaining only the first quantitative target" in self.spec or \
               "retaining only the first" in self.spec.lower()

    def test_spec_forbids_generic_replacement(self) -> None:
        """Spec forbids replacing multi-component target with generic phrase."""
        assert "performance improvement" in self.spec.lower()

    def test_spec_forbids_dropping_non_primary_components(self) -> None:
        """Spec forbids dropping non-primary metric components."""
        assert "non-primary" in self.spec.lower()


# ===========================================================================
# 3. SPEC INVARIANT — OWNERSHIP SEPARATION
# ===========================================================================


class TestSpecOwnershipSeparation:
    """Implementation spec distinguishes responsible_partner from integration/support WP."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_mentions_responsible_partner(self) -> None:
        """Spec references responsible_partner from objectives.json."""
        assert "responsible_partner" in self.spec

    def test_spec_distinguishes_integration_wp(self) -> None:
        """Spec distinguishes integration/support WPs from responsible parties."""
        spec_lower = self.spec.lower()
        assert "integration" in spec_lower
        assert "support" in spec_lower

    def test_spec_defines_ccr6(self) -> None:
        """Spec defines CCR-6 for ownership separation."""
        assert "CCR-6" in self.spec

    def test_spec_forbids_unsupported_ownership_reassignment(self) -> None:
        """Spec forbids asserting ownership not supported by Tier 3/wp_structure."""
        assert "implements" in self.spec and "delivers" in self.spec
        # Should list these as prohibited patterns
        spec_lower = self.spec.lower()
        assert "prohibited" in spec_lower

    def test_spec_mentions_wp_structure_for_ownership(self) -> None:
        """Spec requires reading wp_structure.json for ownership validation."""
        assert "wp_structure.json" in self.spec


# ===========================================================================
# 4. SPEC INVARIANT — SAFE INTEGRATION WORDING
# ===========================================================================


class TestSpecSafeIntegrationWording:
    """Implementation spec includes neutral integration/support wording patterns."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_provides_neutral_wording_integrates(self) -> None:
        """Spec provides 'integrates outputs from' pattern."""
        assert "integrates outputs from" in self.spec

    def test_spec_provides_neutral_wording_validates(self) -> None:
        """Spec provides 'validates interfaces for' pattern."""
        assert "validates interfaces for" in self.spec

    def test_spec_provides_neutral_wording_supports(self) -> None:
        """Spec provides 'supports deployment of' pattern."""
        assert "supports deployment of" in self.spec

    def test_spec_provides_neutral_wording_consumes(self) -> None:
        """Spec provides 'consumes the output of' pattern."""
        assert "consumes the output of" in self.spec

    def test_spec_provides_ownership_safe_pattern(self) -> None:
        """Spec provides the required safer wording pattern with responsible partner."""
        assert "develops/delivers" in self.spec or \
               "develops" in self.spec and "delivers" in self.spec
        assert "integrates the resulting" in self.spec


# ===========================================================================
# 5. SPEC INVARIANT — VALIDATION_STATUS CONSISTENCY
# ===========================================================================


class TestSpecValidationStatusConsistency:
    """validation_status.claim_statuses[] must preserve all objective target components."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_mandates_claim_summary_completeness(self) -> None:
        """Spec requires claim_summary to retain all metric components."""
        assert "claim_summary" in self.spec
        # The spec should say claim_summary must retain all components
        assert "claim_summary MUST retain all metric components" in self.spec or \
               "claim_summary must retain all" in self.spec.lower()

    def test_spec_forbids_partial_representation_in_claims(self) -> None:
        """Spec forbids partially representing a target in claim_summary."""
        assert "partially represent" in self.spec.lower()


# ===========================================================================
# 6. ARTIFACT-LEVEL FIXTURE TEST — METRIC LOSS IN IMPLEMENTATION
# ===========================================================================


class TestArtifactMetricLossInImplementation:
    """Fixture test: metric loss in Implementation is caught via consistency_log."""

    def _make_assembled(self, consistency_log=None) -> dict:
        return {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1",
            "run_id": "test-metric-loss",
            "sections": [
                {"section_id": "excellence", "criterion": "Excellence", "order": 1, "artifact_path": "e.json"},
                {"section_id": "impact", "criterion": "Impact", "order": 2, "artifact_path": "i.json"},
                {"section_id": "implementation", "criterion": "Implementation", "order": 3, "artifact_path": "impl.json"},
            ],
            "consistency_log": consistency_log or [],
        }

    def test_consistency_log_cc06_metric_loss_fails_gate(self, tmp_path: Path) -> None:
        """When consistency_log flags CC-06 (metric loss), predicate fails."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        assembled = self._make_assembled(consistency_log=[
            {
                "check_id": "CC-06",
                "status": "inconsistency_flagged",
                "description": (
                    "OBJ-2 measurable_target contains '≥30% coherence AND factual consistency' "
                    "but Implementation mentions only '≥30% coherence improvement'"
                ),
            },
        ])
        _write_json(tmp_path / "assembled.json", assembled)
        (tmp_path / "sections").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tier3").mkdir(parents=True, exist_ok=True)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert "CC-06" in result.details.get("flagged_checks", [])

    def test_no_metric_loss_passes(self, tmp_path: Path) -> None:
        """When consistency_log has no flagged entries, passes."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        assembled = self._make_assembled(consistency_log=[
            {
                "check_id": "CC-06",
                "status": "consistent",
                "description": "All measurable_target components preserved in Implementation",
            },
        ])
        _write_json(tmp_path / "assembled.json", assembled)
        (tmp_path / "sections").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tier3").mkdir(parents=True, exist_ok=True)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_metric_loss_detected_in_implementation_via_predicate(
        self, tmp_path: Path,
    ) -> None:
        """When Implementation mentions objective but omits a metric conjunct,
        the deterministic metric_completeness check catches it (for sections
        that are checked). This tests that Impact-level check applies."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        objectives = {
            "objectives": [
                {
                    "id": "OBJ-2",
                    "title": "Adaptive Memory Architecture",
                    "measurable_target": "≥30% task coherence AND ≥25% factual consistency",
                    "target_month": 36,
                    "responsible_partner": "ATU",
                },
            ],
        }
        sections_dir = tmp_path / "sections"
        _write_json(tmp_path / "assembled.json", self._make_assembled())
        _write_json(sections_dir / "excellence_section.json", {
            "schema_id": "orch.tier5.excellence_section.v1", "run_id": "t",
            "criterion": "Excellence",
            "sub_sections": [{"sub_section_id": "B.1.1", "title": "M",
                              "content": "OBJ-2 Adaptive Memory Architecture."}],
        })
        _write_json(sections_dir / "impact_section.json", {
            "schema_id": "orch.tier5.impact_section.v1", "run_id": "t",
            "criterion": "Impact",
            "sub_sections": [{"sub_section_id": "B.2.1", "title": "M",
                              "content": "OBJ-2 achieves ≥30% coherence only."}],
            "impact_pathway_refs": [],
            "dec_coverage": {"dissemination_addressed": True,
                             "exploitation_addressed": True,
                             "communication_addressed": True},
        })
        _write_json(sections_dir / "implementation_section.json", {
            "schema_id": "orch.tier5.implementation_section.v1", "run_id": "t",
            "criterion": "Implementation",
            "sub_sections": [{"sub_section_id": "B.3.1", "title": "M",
                              "content": "OBJ-2 targets ≥30% coherence improvement."}],
            "wp_table_refs": ["WP1"], "gantt_ref": "g.json",
            "milestone_refs": ["MS1"], "risk_register_ref": "r.json",
        })
        _write_json(tmp_path / "tier3/architecture_inputs/objectives.json", objectives)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        # The deterministic predicate checks Impact for metric loss
        assert not result.passed
        metric_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "metric_completeness"
        ]
        assert len(metric_issues) >= 1
        assert "≥25%" in str(metric_issues[0]["details"])


# ===========================================================================
# 7. ARTIFACT-LEVEL FIXTURE TEST — OWNERSHIP REASSIGNMENT
# ===========================================================================


class TestArtifactOwnershipReassignment:
    """Fixture test: ownership reassignment is caught via consistency_log."""

    def _make_assembled(self, consistency_log=None) -> dict:
        return {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1",
            "run_id": "test-ownership",
            "sections": [
                {"section_id": "excellence", "criterion": "Excellence", "order": 1, "artifact_path": "e.json"},
                {"section_id": "impact", "criterion": "Impact", "order": 2, "artifact_path": "i.json"},
                {"section_id": "implementation", "criterion": "Implementation", "order": 3, "artifact_path": "impl.json"},
            ],
            "consistency_log": consistency_log or [],
        }

    def test_consistency_log_cc01_ownership_conflict_fails_gate(
        self, tmp_path: Path,
    ) -> None:
        """When consistency_log flags CC-01 (ownership conflict), predicate fails."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        assembled = self._make_assembled(consistency_log=[
            {
                "check_id": "CC-01",
                "status": "inconsistency_flagged",
                "description": (
                    "OBJ-8 responsible_partner is ATU in Tier 3 and Excellence, "
                    "but Implementation routes OBJ-8 delivery under WP8/FIIT"
                ),
            },
        ])
        _write_json(tmp_path / "assembled.json", assembled)
        (tmp_path / "sections").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tier3").mkdir(parents=True, exist_ok=True)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert "CC-01" in result.details.get("flagged_checks", [])

    def test_neutral_integration_wording_passes(self, tmp_path: Path) -> None:
        """When Implementation uses neutral integration wording, no CC-01 flag."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        assembled = self._make_assembled(consistency_log=[
            {
                "check_id": "CC-01",
                "status": "consistent",
                "description": "Objective ownership consistent across sections",
            },
        ])
        _write_json(tmp_path / "assembled.json", assembled)
        (tmp_path / "sections").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tier3").mkdir(parents=True, exist_ok=True)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_both_cc01_and_cc06_flagged_reports_both(self, tmp_path: Path) -> None:
        """When both CC-01 and CC-06 are flagged, both appear in failure details."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        assembled = self._make_assembled(consistency_log=[
            {
                "check_id": "CC-01",
                "status": "inconsistency_flagged",
                "description": "Ownership conflict for OBJ-8",
            },
            {
                "check_id": "CC-06",
                "status": "inconsistency_flagged",
                "description": "Metric loss for OBJ-2",
            },
        ])
        _write_json(tmp_path / "assembled.json", assembled)
        (tmp_path / "sections").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tier3").mkdir(parents=True, exist_ok=True)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        flagged = result.details.get("flagged_checks", [])
        assert "CC-01" in flagged
        assert "CC-06" in flagged


# ===========================================================================
# 8. SPEC INVARIANT — PRE-OUTPUT CONSISTENCY CHECK
# ===========================================================================


class TestSpecPreOutputCheck:
    """Implementation spec includes a pre-output consistency self-check."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_has_pre_output_check(self) -> None:
        """Spec defines a pre-output consistency check."""
        assert "Pre-Output Consistency" in self.spec or \
               "pre-output consistency" in self.spec.lower()

    def test_spec_pre_output_check_references_ccr5(self) -> None:
        """Pre-output check references CCR-5 for metric preservation."""
        assert "CCR-5" in self.spec

    def test_spec_pre_output_check_references_ccr6(self) -> None:
        """Pre-output check references CCR-6 for ownership separation."""
        assert "CCR-6" in self.spec

    def test_spec_pre_output_check_is_bounded(self) -> None:
        """Pre-output check is bounded to mentioned objectives, not exhaustive."""
        assert "bounded" in self.spec.lower() or \
               "objectives actually mentioned" in self.spec.lower()

    def test_spec_pre_output_says_revise_before_output(self) -> None:
        """Spec says to revise content before writing if check fails."""
        assert "revise" in self.spec.lower()
        assert "before writing" in self.spec.lower() or \
               "before output" in self.spec.lower()
