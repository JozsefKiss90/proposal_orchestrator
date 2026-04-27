"""
Static tests for skill spec content guards.

Verifies that impact-section-drafting.md and implementation-section-drafting.md
contain the required guardrails, forbidden patterns, and output constraints
identified from run fcac4f7a blockers.

These tests read skill spec files as text and check for presence/absence
of required/forbidden patterns. They do not invoke Claude.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_skill(name: str) -> str:
    """Read a skill spec file and return its full text."""
    path = SKILLS_DIR / name
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


# ===========================================================================
# Task A — impact-section-drafting.md
# ===========================================================================


class TestImpactSectionDraftingSpec:
    """Verify impact-section-drafting.md contains required guardrails."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("impact-section-drafting.md")

    def test_contains_total_response_length_guidance(self) -> None:
        """Spec must contain explicit output size ceiling below 18,000 chars."""
        assert "18,000" in self.text or "18000" in self.text
        assert "output size ceiling" in self.text.lower() or "Output size ceiling" in self.text

    def test_requires_json_only_output(self) -> None:
        """Spec must require JSON-only output."""
        assert "begin with `{`" in self.text or 'begin with `{`' in self.text
        assert "end with `}`" in self.text or 'end with `}`' in self.text
        assert "non-JSON output causes a pipeline failure" in self.text

    def test_forbids_d8_01_as_orchestration_layer(self) -> None:
        """Spec must forbid treating D8-01 as the orchestration-layer deliverable."""
        assert "D8-01" in self.text
        # Must say D8-01 is evaluation framework, NOT orchestration layer
        assert "evaluation framework" in self.text.lower()
        assert "MUST NOT be cited as" in self.text or "MUST NOT" in self.text

    def test_requires_d8_01_as_evaluation_framework(self) -> None:
        """Spec must describe D8-01 only as evaluation framework / benchmark."""
        assert "evaluation framework and benchmark specification" in self.text.lower() or \
               "evaluation framework" in self.text.lower()

    def test_requires_compact_source_ref(self) -> None:
        """Spec must require compact source_ref values (max 120 chars)."""
        assert "120 characters" in self.text
        assert "source_ref" in self.text


# ===========================================================================
# Task C — implementation-section-drafting.md
# ===========================================================================


class TestImplementationSectionDraftingSpec:
    """Verify implementation-section-drafting.md contains required guardrails."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("implementation-section-drafting.md")

    def test_forbids_bimonthly(self) -> None:
        """Spec must forbid 'bimonthly' wording."""
        assert "bimonthly" in self.text.lower()  # mentioned as forbidden
        # Must contain the correct alternative
        assert "every 6 months" in self.text or "six-monthly" in self.text

    def test_requires_six_monthly_wording(self) -> None:
        """Spec must require 'every 6 months' or 'six-monthly'."""
        has_correct = (
            "every 6 months" in self.text
            or "six-monthly" in self.text
        )
        assert has_correct

    def test_forbids_numbered_ethics_categories_without_tier1(self) -> None:
        """Spec must forbid 'Category 8', 'Category 4', 'Category 2' without Tier 1."""
        lower = self.text.lower()
        assert "category 8" in lower  # mentioned as forbidden
        assert "category 4" in lower
        assert "category 2" in lower
        # Must have Tier 1 condition
        assert "tier 1" in lower

    def test_forbids_all_three_apply_ai_sectors(self) -> None:
        """Spec must forbid 'covers all three Apply AI sectors'."""
        assert "covers all three Apply AI sectors" in self.text

    def test_requires_safe_healthcare_manufacturing_logistics_wording(self) -> None:
        """Spec must require safe wording mentioning logistics transfer."""
        assert "logistics transfer demonstrator" in self.text.lower() or \
               "logistics transfer" in self.text

    def test_forbids_conflict_prone_contributor_wp_lists(self) -> None:
        """Spec must forbid enumerating conflict-prone contributor WP lists."""
        assert "conflict-prone" in self.text.lower() or \
               "Conflict-prone" in self.text

    def test_gate_readiness_check_includes_bimonthly(self) -> None:
        """Gate readiness check must include 'bimonthly' as a forbidden word."""
        # Find the gate-readiness section
        idx = self.text.find("Gate-readiness check")
        assert idx >= 0
        gate_section = self.text[idx:]
        assert "bimonthly" in gate_section.lower()

    def test_gate_readiness_check_includes_ethics_categories(self) -> None:
        """Gate readiness check must include ethics category prohibition."""
        idx = self.text.find("Gate-readiness check")
        assert idx >= 0
        gate_section = self.text[idx:]
        assert "Category 8" in gate_section or "category" in gate_section.lower()

    def test_gate_readiness_check_includes_sr07_overclaim(self) -> None:
        """Gate readiness check must include SR-07 overclaim prohibition."""
        idx = self.text.find("Gate-readiness check")
        assert idx >= 0
        gate_section = self.text[idx:]
        assert "Apply AI sectors" in gate_section or "SR-07" in gate_section
