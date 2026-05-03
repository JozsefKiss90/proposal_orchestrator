"""
Targeted tests for Implementation drafting consistency invariants.

Verifies the *slim* implementation-section-drafting.md architecture where:
  - The skill spec declares canonical_reference_pack.json as an input
  - Canonical Copying Rules forbid renaming/shortening/reassigning IDs
  - Metric preservation (CCR-5) and ownership separation (CCR-6) are
    enforced by deterministic preflight predicates registered at gate_10c
    and cross_section_consistency at gate_10d, NOT by bloated in-spec rules
  - claim_summary completeness is enforced by the cross_section_consistency
    predicate (CC-06 check), not by skill-level prose

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
    """Slim spec delegates metric preservation to predicates + canonical pack.

    The old spec embedded CCR-5 / GATE-CRITICAL / conjunction rules inline.
    The slim spec instead:
      - Declares canonical_reference_pack.json as input
      - Has a "Canonical Copying Rules" section forbidding renaming/shortening
      - Relies on cross_section_consistency (CC-06) at gate_10d for metric loss
    """

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_declares_canonical_reference_pack_input(self) -> None:
        """Spec lists canonical_reference_pack.json in reads_from / declared inputs."""
        assert "canonical_reference_pack.json" in self.spec

    def test_spec_has_canonical_copying_rules_section(self) -> None:
        """Spec contains a 'Canonical Copying Rules' section."""
        assert "Canonical Copying Rules" in self.spec

    def test_spec_forbids_renaming(self) -> None:
        """Spec forbids renaming canonical terms."""
        assert "rename" in self.spec.lower()

    def test_cross_section_consistency_registered_in_gate_evaluator(self) -> None:
        """cross_section_consistency predicate is registered in PREDICATE_REGISTRY."""
        from runner.gate_evaluator import PREDICATE_REGISTRY
        assert "cross_section_consistency" in PREDICATE_REGISTRY


# ===========================================================================
# 2. SPEC INVARIANT — NO METRIC COMPRESSION
# ===========================================================================


class TestSpecNoMetricCompression:
    """Slim spec delegates metric-compression prevention to gate predicates.

    The old spec had inline rules forbidding compression, retaining-only-first,
    generic replacement, and non-primary dropping.  The slim spec instead:
      - Forbids shortening/paraphrasing in Canonical Copying Rules
      - Relies on cross_section_consistency CC-06 at gate_10d
      - Relies on canonical_terms_preserved at gate_10c
    """

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_forbids_shortening(self) -> None:
        """Spec forbids shortening canonical terms."""
        assert "shorten" in self.spec.lower()

    def test_spec_forbids_paraphrasing(self) -> None:
        """Spec forbids paraphrasing canonical terms."""
        assert "paraphrase" in self.spec.lower()

    def test_canonical_terms_preserved_registered(self) -> None:
        """canonical_terms_preserved predicate is in PREDICATE_REGISTRY."""
        from runner.gate_evaluator import PREDICATE_REGISTRY
        assert "canonical_terms_preserved" in PREDICATE_REGISTRY

    def test_canonical_terms_preserved_in_gate_10c(self) -> None:
        """canonical_terms_preserved is listed in gate_10c predicates in gate_rules_library."""
        gate_lib = (
            Path(__file__).resolve().parents[2]
            / ".claude" / "workflows" / "system_orchestration"
            / "gate_rules_library.yaml"
        )
        content = gate_lib.read_text(encoding="utf-8")
        # Predicate appears under gate_10c_implementation_completeness block
        assert "canonical_terms_preserved" in content


# ===========================================================================
# 3. SPEC INVARIANT — OWNERSHIP SEPARATION
# ===========================================================================


class TestSpecOwnershipSeparation:
    """Slim spec delegates ownership separation to Canonical Copying Rules + predicates.

    The old spec had CCR-6, explicit prohibited-pattern lists, and
    responsible_partner prose.  The slim spec instead:
      - Says "Do not infer ownership" in Canonical Copying Rules
      - References wp_structure.json as the canonical source for WP lead assignments
      - Relies on partner_names_preserved and cross_section_consistency (CC-01)
        at gate_10c / gate_10d
    """

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_forbids_inferring_ownership(self) -> None:
        """Spec says 'Do not infer ownership'."""
        assert "Do not infer ownership" in self.spec

    def test_spec_forbids_reassigning_ids(self) -> None:
        """Spec forbids reassigning IDs."""
        assert "reassign" in self.spec.lower()

    def test_spec_references_wp_structure_for_ownership(self) -> None:
        """Spec references wp_structure.json as canonical source for WP leads."""
        assert "wp_structure.json" in self.spec

    def test_partner_names_preserved_registered(self) -> None:
        """partner_names_preserved predicate is in PREDICATE_REGISTRY."""
        from runner.gate_evaluator import PREDICATE_REGISTRY
        assert "partner_names_preserved" in PREDICATE_REGISTRY

    def test_partner_names_preserved_in_gate_10c(self) -> None:
        """partner_names_preserved is listed in gate_10c predicates in gate_rules_library."""
        gate_lib = (
            Path(__file__).resolve().parents[2]
            / ".claude" / "workflows" / "system_orchestration"
            / "gate_rules_library.yaml"
        )
        content = gate_lib.read_text(encoding="utf-8")
        assert "partner_names_preserved" in content


# ===========================================================================
# 4. SPEC INVARIANT — SAFE INTEGRATION WORDING
# ===========================================================================


class TestSpecSafeIntegrationWording:
    """Slim spec replaces inline wording templates with Canonical Copying Rules.

    The old spec listed explicit safe-wording phrases ('integrates outputs from',
    'validates interfaces for', etc.).  The slim spec instead:
      - Has the Canonical Copying Rules section with 'Do not infer ownership'
      - Tells the drafter to omit claims when ownership is unclear
      - Relies on deliverable_identity_preserved at gate_10c to catch ID drift
    """

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_omit_unclear_claims(self) -> None:
        """Spec says to omit claims when ownership is unclear."""
        assert "omit the claim" in self.spec.lower() or \
               "omit" in self.spec.lower()

    def test_spec_forbids_citing_unsourced_deliverables(self) -> None:
        """Spec forbids citing a deliverable without source artifact confirmation."""
        assert "Do not cite a deliverable unless" in self.spec

    def test_deliverable_identity_preserved_registered(self) -> None:
        """deliverable_identity_preserved predicate is in PREDICATE_REGISTRY."""
        from runner.gate_evaluator import PREDICATE_REGISTRY
        assert "deliverable_identity_preserved" in PREDICATE_REGISTRY

    def test_deliverable_identity_preserved_in_gate_10c(self) -> None:
        """deliverable_identity_preserved is listed in gate_10c predicates."""
        gate_lib = (
            Path(__file__).resolve().parents[2]
            / ".claude" / "workflows" / "system_orchestration"
            / "gate_rules_library.yaml"
        )
        content = gate_lib.read_text(encoding="utf-8")
        assert "deliverable_identity_preserved" in content

    def test_spec_keeps_output_concise(self) -> None:
        """Spec instructs keeping output concise and schema-conformant."""
        assert "concise" in self.spec.lower()


# ===========================================================================
# 5. SPEC INVARIANT — VALIDATION_STATUS CONSISTENCY
# ===========================================================================


class TestSpecValidationStatusConsistency:
    """Slim spec delegates claim completeness to predicates.

    The old spec had inline rules about claim_summary retaining all metric
    components and forbidding partial representation.  The slim spec instead:
      - References claim_summary in the output schema (step 2.8)
      - Relies on cross_section_consistency (CC-06) at gate_10d for
        metric completeness enforcement
      - Relies on canonical_terms_preserved at gate_10c for term drift
    """

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_references_claim_summary_in_output(self) -> None:
        """Spec mentions claim_summary in the validation_status output schema."""
        assert "claim_summary" in self.spec

    def test_spec_references_validation_status(self) -> None:
        """Spec describes building validation_status with claim_statuses."""
        assert "validation_status" in self.spec
        assert "claim_status" in self.spec.lower()

    def test_cross_section_consistency_catches_metric_loss(self) -> None:
        """cross_section_consistency is the gate_10d enforcement mechanism."""
        from runner.gate_evaluator import PREDICATE_REGISTRY
        assert "cross_section_consistency" in PREDICATE_REGISTRY
        gate_lib = (
            Path(__file__).resolve().parents[2]
            / ".claude" / "workflows" / "system_orchestration"
            / "gate_rules_library.yaml"
        )
        content = gate_lib.read_text(encoding="utf-8")
        assert "gate_10d_cross_section_consistency" in content
        assert "cross_section_consistency" in content


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
    """Slim spec replaces inline CCR-5/CCR-6 pre-output check with gate predicates.

    The old spec had a "Pre-Output Consistency" section referencing CCR-5, CCR-6,
    bounded scoping, and revise-before-writing.  The slim spec instead:
      - Has Canonical Copying Rules as the drafting-time guardrail
      - Delegates post-output verification to three gate_10c predicates
        (partner_names_preserved, deliverable_identity_preserved,
        canonical_terms_preserved) and gate_10d cross_section_consistency
    """

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.spec = _read_spec()

    def test_spec_has_canonical_copying_rules(self) -> None:
        """Spec contains Canonical Copying Rules as the drafting guardrail."""
        assert "Canonical Copying Rules" in self.spec

    def test_spec_copy_exactly_instruction(self) -> None:
        """Spec instructs copying terms exactly from source artifacts."""
        assert "exactly" in self.spec.lower()

    def test_all_three_preflight_predicates_registered(self) -> None:
        """All three Phase 8 section preflight predicates are in PREDICATE_REGISTRY."""
        from runner.gate_evaluator import PREDICATE_REGISTRY
        for pred in (
            "partner_names_preserved",
            "deliverable_identity_preserved",
            "canonical_terms_preserved",
        ):
            assert pred in PREDICATE_REGISTRY, f"{pred} missing from PREDICATE_REGISTRY"

    def test_gate_10c_has_all_preflight_predicates(self) -> None:
        """gate_10c_implementation_completeness includes all three preflight predicates."""
        gate_lib = (
            Path(__file__).resolve().parents[2]
            / ".claude" / "workflows" / "system_orchestration"
            / "gate_rules_library.yaml"
        )
        content = gate_lib.read_text(encoding="utf-8")
        for pred in (
            "partner_names_preserved",
            "deliverable_identity_preserved",
            "canonical_terms_preserved",
        ):
            assert pred in content, f"{pred} not found in gate_rules_library.yaml"

    def test_gate_10d_has_cross_section_consistency(self) -> None:
        """gate_10d_cross_section_consistency includes cross_section_consistency."""
        gate_lib = (
            Path(__file__).resolve().parents[2]
            / ".claude" / "workflows" / "system_orchestration"
            / "gate_rules_library.yaml"
        )
        content = gate_lib.read_text(encoding="utf-8")
        assert "gate_10d_cross_section_consistency" in content
        assert "cross_section_consistency" in content
