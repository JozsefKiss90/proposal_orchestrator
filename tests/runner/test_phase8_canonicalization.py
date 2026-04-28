"""
Targeted tests for the Phase 8 project-agnostic canonicalization patch.

Covers:
  1. Shared spec invariant tests — all three specs contain required rules
  2. Excellence-specific tests — methodology terminology, WP attribution
  3. Impact-specific tests — metric completeness, sourced WP attribution, terminology
  4. Implementation-specific tests — WP labels vs canonical titles
  5. Cross-section consistency output tests — traceability_footer, source_refs
  6. Fingerprint invalidation tests — spec changes invalidate correct nodes

All tests are static — no live Claude invocations.
All fixture data is project-agnostic (no hard-coded real project IDs).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"

EXCELLENCE_SPEC = SKILLS_DIR / "excellence-section-drafting.md"
IMPACT_SPEC = SKILLS_DIR / "impact-section-drafting.md"
IMPLEMENTATION_SPEC = SKILLS_DIR / "implementation-section-drafting.md"
CONSISTENCY_SPEC = SKILLS_DIR / "cross-section-consistency-check.md"


def _read_spec(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ===========================================================================
# 1. SHARED SPEC INVARIANT TESTS
# ===========================================================================


class TestSharedCanonicalArtifactReferenceRules:
    """All three section specs must contain the shared canonicalization rules."""

    @pytest.fixture(autouse=True)
    def _load_specs(self) -> None:
        self.excellence = _read_spec(EXCELLENCE_SPEC)
        self.impact = _read_spec(IMPACT_SPEC)
        self.implementation = _read_spec(IMPLEMENTATION_SPEC)
        self.all_specs = {
            "excellence": self.excellence,
            "impact": self.impact,
            "implementation": self.implementation,
        }

    def test_all_contain_canonical_artifact_reference_rules_header(self) -> None:
        """All three specs have the shared section header."""
        for name, content in self.all_specs.items():
            assert (
                "Canonical Artifact Reference Rules (GATE-CRITICAL — Shared Cross-Section Canonicalization)"
                in content
            ), f"{name} spec missing shared canonicalization header"

    def test_all_forbid_objective_title_paraphrase(self) -> None:
        """All three specs forbid paraphrasing objective titles."""
        for name, content in self.all_specs.items():
            assert (
                "Do not paraphrase, shorten, rename, or substitute canonical objective titles"
                in content
            ), f"{name} spec missing objective title paraphrase prohibition"

    def test_all_require_complete_measurable_target_preservation(self) -> None:
        """All three specs require preserving all metric components."""
        for name, content in self.all_specs.items():
            assert (
                "Preserve every quantified metric and conjunctive metric component"
                in content
            ), f"{name} spec missing metric completeness requirement"

    def test_all_forbid_component_noun_substitution(self) -> None:
        """All three specs list forbidden component noun substitutions."""
        forbidden_pairs = [
            "engine ↔ framework",
            "architecture ↔ system",
            "layer ↔ capability",
            "protocol ↔ method",
            "platform ↔ tool",
        ]
        for name, content in self.all_specs.items():
            for pair in forbidden_pairs:
                assert pair in content, (
                    f"{name} spec missing forbidden substitution: {pair}"
                )

    def test_all_forbid_guessed_wp_attribution(self) -> None:
        """All three specs forbid inventing WP attributions."""
        for name, content in self.all_specs.items():
            assert (
                "Do not invent WP attributions from local reasoning"
                in content
            ), f"{name} spec missing WP attribution discipline"

    def test_all_require_incomplete_output_on_violation(self) -> None:
        """All three specs specify INCOMPLETE_OUTPUT on canonicalization violation."""
        for name, content in self.all_specs.items():
            assert (
                "On violation: return INCOMPLETE_OUTPUT"
                in content
            ), f"{name} spec missing INCOMPLETE_OUTPUT violation instruction"

    def test_all_require_cross_section_self_check(self) -> None:
        """All three specs require a cross-section self-check before output."""
        for name, content in self.all_specs.items():
            assert (
                "Cross-Section Self-Check Before Output"
                in content
            ), f"{name} spec missing cross-section self-check"


# ===========================================================================
# 2. EXCELLENCE-SPECIFIC TESTS
# ===========================================================================


class TestExcellenceSpecificRules:
    """Excellence spec has methodology terminology and WP attribution rules."""

    @pytest.fixture(autouse=True)
    def _load_spec(self) -> None:
        self.spec = _read_spec(EXCELLENCE_SPEC)

    def test_methodology_must_preserve_b11_names(self) -> None:
        """Excellence spec requires B.1.2 to reuse B.1.1 canonical names."""
        assert (
            "B.1.2 methodology narrative MUST reuse the same canonical objective/component names introduced in B.1.1"
            in self.spec
        )

    def test_methodology_forbids_renaming(self) -> None:
        """Excellence spec forbids B.1.2 from renaming B.1.1 names."""
        assert (
            "B.1.2 MUST NOT rename X to a synonym or abbreviation"
            in self.spec
        )

    def test_wp_attribution_consistency_with_other_sections(self) -> None:
        """Excellence must not assign different WP sets than other sections."""
        assert (
            "Excellence MUST NOT assign different WP integration sets than Impact or Implementation"
            in self.spec
        )

    def test_exact_wp_list_forbidden_without_mapping(self) -> None:
        """Exact WP list is forbidden when no explicit artifact mapping exists."""
        assert (
            "avoid providing an exact WP list for that objective/component"
            in self.spec
        )


# ===========================================================================
# 3. IMPACT-SPECIFIC TESTS
# ===========================================================================


class TestImpactSpecificRules:
    """Impact spec has metric completeness, WP attribution, and terminology rules."""

    @pytest.fixture(autouse=True)
    def _load_spec(self) -> None:
        self.spec = _read_spec(IMPACT_SPEC)

    def test_impact_requires_complete_metric_text(self) -> None:
        """Impact spec requires complete metric text for all referenced objectives."""
        assert (
            "Impact Pathways Must Not Compress Metrics"
            in self.spec
        )
        assert (
            "claim_statuses` MUST include complete metric text"
            in self.spec
        )

    def test_impact_requires_sourced_wp_attribution(self) -> None:
        """Impact spec requires sourced WP attribution or omission."""
        assert (
            "Impact Pathways Must Not Assign Guessed WP Sets"
            in self.spec
        )
        assert (
            "source_ref` MUST point to the artifact field that contains that WP set"
            in self.spec
        )

    def test_impact_requires_canonical_component_names(self) -> None:
        """Impact spec requires canonical component names, not WP labels."""
        assert (
            "Impact MUST use canonical objective/outcome component names"
            in self.spec
        )
        assert (
            "Impact MUST NOT use WP labels as substitutes for canonical system/component titles"
            in self.spec
        )


# ===========================================================================
# 4. IMPLEMENTATION-SPECIFIC TESTS
# ===========================================================================


class TestImplementationSpecificRules:
    """Implementation spec distinguishes WP labels from canonical titles."""

    @pytest.fixture(autouse=True)
    def _load_spec(self) -> None:
        self.spec = _read_spec(IMPLEMENTATION_SPEC)

    def test_wp_labels_vs_canonical_titles_rule(self) -> None:
        """Implementation spec distinguishes WP labels from objective/component names."""
        assert (
            "WP Labels vs Canonical Component Titles"
            in self.spec
        )
        assert (
            "WP table labels may retain canonical WP names from `wp_structure.json`"
            in self.spec
        )

    def test_forbids_wp_labels_replacing_objective_titles(self) -> None:
        """Implementation spec forbids WP labels replacing objective titles."""
        assert (
            "Do NOT allow WP labels to replace objective/component names"
            in self.spec
        )

    def test_objective_to_wp_mapping_discipline(self) -> None:
        """Implementation spec requires explicit mapping for WP ownership claims."""
        assert (
            "Objective-to-WP Mapping Discipline"
            in self.spec
        )
        assert (
            "do NOT imply canonical WP ownership for an objective"
            in self.spec
        )


# ===========================================================================
# 5. CROSS-SECTION CONSISTENCY OUTPUT TESTS
# ===========================================================================


class TestCrossSectionConsistencyTraceability:
    """Cross-section consistency spec traceability_footer and source_refs."""

    @pytest.fixture(autouse=True)
    def _load_spec(self) -> None:
        self.spec = _read_spec(CONSISTENCY_SPEC)

    def test_traceability_footer_includes_tier3_paths(self) -> None:
        """Spec requires Tier 3 objective paths in primary_sources."""
        assert (
            "docs/tier3_project_instantiation/architecture_inputs/objectives.json"
            in self.spec
        )

    def test_traceability_footer_includes_tier4_wp_structure(self) -> None:
        """Spec requires Tier 4 wp_structure path in primary_sources."""
        assert (
            "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
            in self.spec
        )

    def test_consistency_log_requires_source_refs_or_source_basis(self) -> None:
        """Spec requires source_refs or source_basis in each consistency_log entry."""
        assert "source_refs" in self.spec
        assert "source_basis" in self.spec
        assert (
            "Each `consistency_log` entry MUST include either"
            in self.spec
        )

    def test_no_unsupported_claims_false_when_inconsistency_flagged(self) -> None:
        """Spec sets no_unsupported_claims_declaration=false on inconsistency_flagged."""
        assert (
            'Set to `false` if ANY entry has `status: "inconsistency_flagged"'
            in self.spec
        )

    def test_no_unsupported_claims_true_requires_source_refs(self) -> None:
        """Spec requires source_refs/source_basis for true declaration."""
        assert (
            "all entries include either `source_refs` or `source_basis`"
            in self.spec
        )

    def test_reads_from_includes_tier4_paths(self) -> None:
        """Spec reads_from includes Tier 4 phase output paths for grounding."""
        assert (
            "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
            in self.spec
        )
        assert (
            "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/"
            in self.spec
        )


# ===========================================================================
# 6. FINGERPRINT INVALIDATION TESTS
# ===========================================================================


class TestFingerprintInvalidation:
    """Spec changes invalidate the correct Phase 8 node fingerprints."""

    @pytest.fixture(autouse=True)
    def _setup_paths(self, tmp_path: Path) -> None:
        """Set up a minimal repo with fingerprint inputs."""
        from runner.phase8_reuse import FINGERPRINT_INPUTS, compute_input_fingerprint

        self.repo = tmp_path
        self.compute = compute_input_fingerprint

        # Create minimal input files for all three nodes
        for node_id in ["n08a_excellence_drafting", "n08b_impact_drafting",
                        "n08c_implementation_drafting"]:
            for rel_path in FINGERPRINT_INPUTS[node_id]:
                if rel_path.endswith("/"):
                    (tmp_path / rel_path).mkdir(parents=True, exist_ok=True)
                    (tmp_path / rel_path / "data.json").write_text(
                        '{"v": 1}', encoding="utf-8"
                    )
                else:
                    p = tmp_path / rel_path
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("spec content placeholder", encoding="utf-8")

    def test_excellence_spec_change_invalidates_only_n08a(self) -> None:
        """Mutation to excellence spec changes only n08a fingerprint."""
        fp_a = self.compute("n08a_excellence_drafting", self.repo)
        fp_b = self.compute("n08b_impact_drafting", self.repo)
        fp_c = self.compute("n08c_implementation_drafting", self.repo)

        # Mutate excellence spec
        spec_path = self.repo / ".claude/skills/excellence-section-drafting.md"
        spec_path.write_text("MUTATED SPEC CONTENT", encoding="utf-8")

        fp_a2 = self.compute("n08a_excellence_drafting", self.repo)
        fp_b2 = self.compute("n08b_impact_drafting", self.repo)
        fp_c2 = self.compute("n08c_implementation_drafting", self.repo)

        assert fp_a != fp_a2, "n08a fingerprint should change on excellence spec mutation"
        assert fp_b == fp_b2, "n08b fingerprint should NOT change on excellence spec mutation"
        assert fp_c == fp_c2, "n08c fingerprint should NOT change on excellence spec mutation"

    def test_impact_spec_change_invalidates_only_n08b(self) -> None:
        """Mutation to impact spec changes only n08b fingerprint."""
        fp_a = self.compute("n08a_excellence_drafting", self.repo)
        fp_b = self.compute("n08b_impact_drafting", self.repo)
        fp_c = self.compute("n08c_implementation_drafting", self.repo)

        # Mutate impact spec
        spec_path = self.repo / ".claude/skills/impact-section-drafting.md"
        spec_path.write_text("MUTATED SPEC CONTENT", encoding="utf-8")

        fp_a2 = self.compute("n08a_excellence_drafting", self.repo)
        fp_b2 = self.compute("n08b_impact_drafting", self.repo)
        fp_c2 = self.compute("n08c_implementation_drafting", self.repo)

        assert fp_a == fp_a2, "n08a fingerprint should NOT change on impact spec mutation"
        assert fp_b != fp_b2, "n08b fingerprint should change on impact spec mutation"
        assert fp_c == fp_c2, "n08c fingerprint should NOT change on impact spec mutation"

    def test_implementation_spec_change_invalidates_only_n08c(self) -> None:
        """Mutation to implementation spec changes only n08c fingerprint."""
        fp_a = self.compute("n08a_excellence_drafting", self.repo)
        fp_b = self.compute("n08b_impact_drafting", self.repo)
        fp_c = self.compute("n08c_implementation_drafting", self.repo)

        # Mutate implementation spec
        spec_path = self.repo / ".claude/skills/implementation-section-drafting.md"
        spec_path.write_text("MUTATED SPEC CONTENT", encoding="utf-8")

        fp_a2 = self.compute("n08a_excellence_drafting", self.repo)
        fp_b2 = self.compute("n08b_impact_drafting", self.repo)
        fp_c2 = self.compute("n08c_implementation_drafting", self.repo)

        assert fp_a == fp_a2, "n08a fingerprint should NOT change on implementation spec mutation"
        assert fp_b == fp_b2, "n08b fingerprint should NOT change on implementation spec mutation"
        assert fp_c != fp_c2, "n08c fingerprint should change on implementation spec mutation"

    def test_consistency_spec_does_not_affect_drafting_nodes(self) -> None:
        """Mutation to cross-section-consistency-check.md does not affect n08a/b/c."""
        fp_a = self.compute("n08a_excellence_drafting", self.repo)
        fp_b = self.compute("n08b_impact_drafting", self.repo)
        fp_c = self.compute("n08c_implementation_drafting", self.repo)

        # Mutate consistency spec (not in any drafting node's FINGERPRINT_INPUTS)
        spec_path = self.repo / ".claude/skills/cross-section-consistency-check.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text("MUTATED CONSISTENCY SPEC", encoding="utf-8")

        fp_a2 = self.compute("n08a_excellence_drafting", self.repo)
        fp_b2 = self.compute("n08b_impact_drafting", self.repo)
        fp_c2 = self.compute("n08c_implementation_drafting", self.repo)

        assert fp_a == fp_a2, "n08a fingerprint should NOT change on consistency spec mutation"
        assert fp_b == fp_b2, "n08b fingerprint should NOT change on consistency spec mutation"
        assert fp_c == fp_c2, "n08c fingerprint should NOT change on consistency spec mutation"
