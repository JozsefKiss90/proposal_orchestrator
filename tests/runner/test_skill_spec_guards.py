"""
Static tests for skill spec content guards.

Verifies that impact-section-drafting.md and implementation-section-drafting.md
contain the required guardrails under the slimmed skill spec architecture.

After Phase 8 skill slimming, verbose inline guards (forbidden-pattern lists,
gate-readiness check sections, project-specific D8-01 rules) were removed.
Enforcement is now delegated to:
  1. canonical_reference_pack.json as a declared TAPM input
  2. Preflight predicates registered in gates 10a/10b/10c
     (partner_names_preserved, deliverable_identity_preserved,
      canonical_terms_preserved in phase8_section_predicates.py)
  3. Canonical Copying Rules section mandating exact copying from sources

These tests verify the new architecture is intact: declared inputs, Canonical
Copying Rules section, JSON-only output mandate, output size ceiling, and
basic structural soundness. They do not invoke Claude.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"
GATE_LIBRARY_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "workflows" / "system_orchestration" / "gate_rules_library.yaml"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_skill(name: str) -> str:
    """Read a skill spec file and return its full text."""
    path = SKILLS_DIR / name
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


def _read_gate_library() -> str:
    """Read the gate rules library YAML and return its full text."""
    assert GATE_LIBRARY_PATH.is_file(), (
        f"Gate rules library not found: {GATE_LIBRARY_PATH}"
    )
    return GATE_LIBRARY_PATH.read_text(encoding="utf-8")


# ===========================================================================
# Task A — impact-section-drafting.md
# ===========================================================================


class TestImpactSectionDraftingSpec:
    """Verify impact-section-drafting.md contains required guardrails.

    After skill slimming, the spec relies on:
    - canonical_reference_pack.json as declared input
    - Canonical Copying Rules section
    - Predicates in gate_10b for partner/deliverable/term preservation
    - JSON-only output mandate and output size ceiling
    """

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("impact-section-drafting.md")

    def test_contains_total_response_length_guidance(self) -> None:
        """Spec must contain explicit output size ceiling below 18,000 chars."""
        assert "18,000" in self.text or "18000" in self.text
        assert "output size ceiling" in self.text.lower() or "Output size ceiling" in self.text

    def test_requires_json_only_output(self) -> None:
        """Spec must require JSON-only output with begin/end braces."""
        lower = self.text.lower()
        assert "begin with `{`" in self.text
        assert "end with `}`" in self.text
        assert "pipeline failure" in lower

    def test_declares_canonical_reference_pack_input(self) -> None:
        """Spec must declare canonical_reference_pack.json as a TAPM input."""
        assert "canonical_reference_pack.json" in self.text
        # Must be in the reads_from frontmatter AND in the declared inputs list
        assert "phase8_drafting_review/canonical_reference_pack.json" in self.text

    def test_has_canonical_copying_rules_section(self) -> None:
        """Spec must contain a Canonical Copying Rules section."""
        assert "Canonical Copying Rules" in self.text
        # The section must mandate exact copying
        idx = self.text.find("Canonical Copying Rules")
        assert idx >= 0
        rules_section = self.text[idx:]
        assert "Do not rename" in rules_section
        assert "Do not infer ownership" in rules_section

    def test_requires_compact_source_ref(self) -> None:
        """Spec must require compact source_ref values (max 120 chars)."""
        assert "120 characters" in self.text or "120 chars" in self.text
        assert "source_ref" in self.text


# ===========================================================================
# Task C — implementation-section-drafting.md
# ===========================================================================


class TestImplementationSectionDraftingSpec:
    """Verify implementation-section-drafting.md contains required guardrails.

    After skill slimming, verbose inline guards (bimonthly, ethics categories,
    Apply AI sectors, Gate-readiness check) were removed. Enforcement is
    delegated to:
    - canonical_reference_pack.json as declared input
    - Canonical Copying Rules section mandating exact copying
    - Predicates in gate_10c (partner_names_preserved,
      deliverable_identity_preserved, canonical_terms_preserved)
    - General processing rules in section 2.4/2.5 for ethics and consortium
    """

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("implementation-section-drafting.md")

    def test_declares_canonical_reference_pack_input(self) -> None:
        """Spec must declare canonical_reference_pack.json as a TAPM input."""
        assert "canonical_reference_pack.json" in self.text
        assert "phase8_drafting_review/canonical_reference_pack.json" in self.text

    def test_has_canonical_copying_rules_section(self) -> None:
        """Spec must contain a Canonical Copying Rules section."""
        assert "Canonical Copying Rules" in self.text
        idx = self.text.find("Canonical Copying Rules")
        assert idx >= 0
        rules_section = self.text[idx:]
        assert "Do not rename" in rules_section
        assert "Do not infer ownership" in rules_section

    def test_ethics_guarded_by_tier1_condition(self) -> None:
        """Spec must guard ethics assertions with a Tier 1 source condition.

        The slim spec delegates to processing rule 2.4 which requires
        'Do not cite numbered ethics category classifications unless a
        Tier 1 source is explicitly read.'
        """
        lower = self.text.lower()
        assert "ethics" in lower
        assert "tier 1" in lower

    def test_forbids_overclaiming_scope_coverage(self) -> None:
        """Spec must forbid overclaiming scope-requirement coverage.

        The slim spec delegates to processing rule 2.5 which says
        'Do not overclaim scope-requirement coverage.'
        """
        assert "overclaim" in self.text.lower()

    def test_consortium_conflict_handling(self) -> None:
        """Spec must address conflict between Tier 3 and Tier 4 on roles.

        The slim spec in section 2.5 instructs: 'When Tier 3 and Tier 4
        conflict on contributor roles, state WP leads and domain expertise
        without enumerating conflict-prone contributor lists.'
        """
        assert "conflict-prone" in self.text.lower() or "Conflict-prone" in self.text

    def test_requires_json_only_output(self) -> None:
        """Spec must require JSON-only output."""
        lower = self.text.lower()
        assert "begin with `{`" in self.text
        assert "end with `}`" in self.text
        assert "pipeline failure" in lower

    def test_preflight_predicates_registered_in_gate_10c(self) -> None:
        """Gate 10c must register partner, deliverable, and term predicates.

        The verbose inline guards were replaced by deterministic predicates
        (partner_names_preserved, deliverable_identity_preserved,
        canonical_terms_preserved) registered in gate_10c_implementation_completeness.
        """
        gate_lib = _read_gate_library()
        # Find the gate_10c section
        idx = gate_lib.find("gate_10c_implementation_completeness")
        assert idx >= 0, "gate_10c_implementation_completeness not found in gate library"
        gate_section = gate_lib[idx:]
        # Predicates must be registered
        assert "partner_names_preserved" in gate_section
        assert "deliverable_identity_preserved" in gate_section
        assert "canonical_terms_preserved" in gate_section

    def test_preflight_predicates_registered_in_gate_10b(self) -> None:
        """Gate 10b must register partner, deliverable, and term predicates.

        Validates the impact-side predicate registration as well.
        """
        gate_lib = _read_gate_library()
        idx = gate_lib.find("gate_10b_impact_completeness")
        assert idx >= 0, "gate_10b_impact_completeness not found in gate library"
        gate_section = gate_lib[idx:]
        assert "partner_names_preserved" in gate_section
        assert "deliverable_identity_preserved" in gate_section
        assert "canonical_terms_preserved" in gate_section

    def test_frequencies_and_intervals_exact(self) -> None:
        """Spec must require exact use of frequencies/intervals from sources.

        The slim spec in section 2.4 requires: 'Use frequencies and intervals
        exactly as stated.' This replaces the old verbose bimonthly prohibition.
        """
        assert "exactly as stated" in self.text
