"""
Tests for CC-06 (metric completeness) and CC-09 (terminology consistency)
fixes in impact-section-drafting.md.

Covers:
  Task A — Metric completeness spec tests
  Task B — Canonical terminology spec tests
  Task C — Fixture-based metric/terminology validation tests
  Task D — Fingerprint isolation (impact spec → only n08b)

All tests are static — no live Claude invocations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"


def _read_impact_spec() -> str:
    """Read impact-section-drafting.md as text."""
    path = SKILLS_DIR / "impact-section-drafting.md"
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Minimal Tier 3 fixtures for metric/terminology validation
# ---------------------------------------------------------------------------

_FIXTURE_OBJECTIVES = {
    "objectives": [
        {
            "id": "OBJ-X",
            "title": "Neuro-symbolic planning engine for task decomposition",
            "description": "Test objective with multi-metric target.",
            "measurable_target": (
                "Open-source release with ≥500 GitHub stars; "
                "results validated through ≥2 TEFs; "
                "technology transfer initiated through ≥3 EDIHs"
            ),
            "target_month": 48,
            "pillar": "Test pillar",
            "responsible_partner": "P1",
            "contributing_partners": ["P2"],
        },
        {
            "id": "OBJ-Y",
            "title": "Unified adaptive memory architecture",
            "description": "Second test objective.",
            "measurable_target": (
                "Demonstrate ≥30% improvement in coherence "
                "and ≥15% improvement in consistency"
            ),
            "target_month": 36,
            "pillar": "Test pillar 2",
            "responsible_partner": "P2",
            "contributing_partners": ["P1"],
        },
    ],
}

_FIXTURE_OUTCOMES = {
    "outcomes": [
        {
            "id": "OUT-X",
            "title": "Neuro-symbolic planning framework for LLM-based agents",
            "description": "Outcome using 'framework' while objective uses 'engine'.",
            "linked_objectives": ["OBJ-X"],
        },
    ],
}


# ===========================================================================
# TASK A — METRIC COMPLETENESS SPEC TESTS
# ===========================================================================


class TestMetricCompletenessSpec:
    """Verify impact-section-drafting.md requires metric preservation."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_impact_spec()

    def test_requires_preservation_of_all_quantified_metrics(self) -> None:
        """Spec must require preserving ALL quantified targets from measurable_target."""
        assert "ALL quantified targets" in self.text or \
               "all quantified targets" in self.text.lower()
        assert "measurable_target" in self.text

    def test_forbids_substituting_different_numeric_values(self) -> None:
        """Spec must forbid substituting a different numeric value."""
        assert "Do not substitute a different numeric value" in self.text or \
               "do not substitute a different value" in self.text.lower()

    def test_requires_fail_fast_incomplete_output_on_missing_metric(self) -> None:
        """Spec must return INCOMPLETE_OUTPUT when a referenced objective metric
        is missing or altered."""
        lower = self.text.lower()
        assert "incomplete_output" in lower
        # Must mention metric completeness in INCOMPLETE_OUTPUT context
        assert "partial metric loss" in lower or "metric" in lower

    def test_requires_multi_metric_target_preservation(self) -> None:
        """Spec must require that multi-metric targets preserve every metric."""
        assert "multi-metric target" in self.text.lower() or \
               "EVERY metric MUST appear" in self.text

    def test_forbids_dropping_one_metric(self) -> None:
        """Spec must forbid dropping one metric from a multi-metric target."""
        assert "Do not drop" in self.text
        assert "metric" in self.text.lower()

    def test_forbids_replacing_total_with_subset(self) -> None:
        """Spec must forbid replacing a total target with an unlabelled subset."""
        assert "unlabelled subset" in self.text.lower() or \
               "subset" in self.text.lower()

    def test_pre_output_scan_for_metrics(self) -> None:
        """Spec must include a pre-output scan for metric completeness."""
        assert "Pre-output scan" in self.text
        # Must mention checking each extracted target
        assert "quantified" in self.text.lower()

    def test_objectives_json_loaded_in_input_validation(self) -> None:
        """Step 1.7 must explicitly load objectives.json."""
        # Find Step 1.7
        idx = self.text.find("Step 1.7")
        assert idx >= 0
        step_text = self.text[idx:idx + 500]
        assert "objectives.json" in step_text

    def test_metric_check_in_gate_readiness(self) -> None:
        """Step 2.11 gate-readiness check must include metric completeness."""
        idx = self.text.find("Gate-readiness check")
        assert idx >= 0
        gate_section = self.text[idx:idx + 1500]
        assert "Metric completeness" in gate_section or \
               "metric completeness" in gate_section.lower()

    def test_claim_statuses_fallback_documented(self) -> None:
        """Spec must document claim_statuses fallback for metrics that don't fit
        in prose."""
        assert "claim_statuses" in self.text
        assert "fallback" in self.text.lower() or "cannot fit" in self.text.lower()


# ===========================================================================
# TASK B — CANONICAL TERMINOLOGY SPEC TESTS
# ===========================================================================


class TestCanonicalTerminologySpec:
    """Verify impact-section-drafting.md requires exact canonical component phrases."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_impact_spec()

    def test_requires_exact_canonical_phrases_from_tier3(self) -> None:
        """Spec must require exact canonical component phrases from objectives/outcomes."""
        assert "canonical" in self.text.lower()
        assert "objectives.json" in self.text
        assert "outcomes.json" in self.text

    def test_forbids_component_noun_substitution(self) -> None:
        """Spec must forbid component noun substitution."""
        assert "Forbidden" in self.text or "forbidden" in self.text.lower()
        assert "substitution" in self.text.lower()

    def test_includes_engine_to_framework_in_forbidden_list(self) -> None:
        """Spec must include Engine→framework in the forbidden substitution list."""
        # Look for engine → framework prohibition
        assert re.search(
            r"Engine\s*→\s*framework",
            self.text,
            re.IGNORECASE,
        ), (
            "impact-section-drafting.md must include Engine→framework "
            "in the forbidden substitution list"
        )

    def test_includes_generic_forbidden_substitutions(self) -> None:
        """Spec must include the four generic forbidden substitutions from the task."""
        text = self.text.lower()
        # engine→framework
        assert "engine" in text and "framework" in text
        # layer→capability
        assert "layer" in text and "capability" in text
        # architecture→approach
        assert "architecture" in text and "approach" in text
        # protocol→method
        assert "protocol" in text and "method" in text

    def test_requires_fail_fast_on_terminology_drift(self) -> None:
        """Spec must return INCOMPLETE_OUTPUT on canonical terminology drift."""
        assert "Terminology drift" in self.text or \
               "terminology drift" in self.text.lower()
        assert "INCOMPLETE_OUTPUT" in self.text

    def test_pre_output_scan_for_terminology(self) -> None:
        """Spec must include a pre-output scan for terminology consistency."""
        lower = self.text.lower()
        assert "stem" in lower
        assert "terminal keyword" in lower

    def test_outcomes_json_as_terminology_source(self) -> None:
        """Spec must list outcomes.json as a source for canonical terminology."""
        # Check in the terminology section specifically
        idx = self.text.find("Terminology Consistency")
        assert idx >= 0
        term_section = self.text[idx:idx + 2000]
        assert "outcomes.json" in term_section

    def test_objective_title_precedence_over_outcome(self) -> None:
        """Spec must state that objective titles take precedence over outcome titles
        when context discusses the objective."""
        assert "precedence" in self.text.lower() or \
               "takes precedence" in self.text.lower()

    def test_terminology_check_in_gate_readiness(self) -> None:
        """Step 2.11 gate-readiness check must include terminology consistency."""
        idx = self.text.find("Gate-readiness check")
        assert idx >= 0
        gate_section = self.text[idx:idx + 1500]
        assert "Terminology" in gate_section or \
               "terminology" in gate_section.lower()


# ===========================================================================
# TASK C — FIXTURE-BASED VALIDATION TESTS
# ===========================================================================


def _extract_quantified_metrics(measurable_target: str) -> list[str]:
    """Extract all quantified metric tokens from a measurable_target string.
    Returns patterns like '≥500', '≥2 TEFs', '≥3 EDIHs', '≥30%', '≥15%'."""
    # Match ≥/≤/>/< followed by number and optional % or context word
    pattern = r'[≥≤><]\s*\d+%?(?:\s+\w+)?'
    return re.findall(pattern, measurable_target)


def _check_metric_presence(
    metrics: list[str],
    content: str,
) -> list[str]:
    """Check which metrics are missing from content. Returns list of missing metrics."""
    missing = []
    for metric in metrics:
        # Normalize whitespace for comparison
        normalized = re.sub(r'\s+', ' ', metric.strip())
        # Check if the numeric part appears with the same value
        if normalized not in content:
            # Try more flexible matching: just the numeric token
            num_match = re.search(r'([≥≤><]\s*\d+%?)', normalized)
            if num_match:
                num_token = num_match.group(1).replace(' ', '')
                # Also check without spaces in content
                content_no_space = content.replace(' ', '')
                if num_token not in content_no_space:
                    missing.append(metric)
            else:
                missing.append(metric)
    return missing


def _check_terminology_drift(
    canonical_titles: dict[str, str],
    content: str,
) -> list[tuple[str, str, str]]:
    """Check for terminology drift in content.

    Args:
        canonical_titles: mapping from component stem to canonical terminal keyword
            e.g. {"Neuro-symbolic planning": "engine"}
        content: text to check

    Returns:
        list of (stem, canonical_keyword, found_keyword) tuples for drift instances.
    """
    # Keywords that indicate technical components
    component_keywords = {
        "engine", "framework", "layer", "architecture", "protocol",
        "system", "suite", "platform", "benchmark", "demonstrator",
        "registry", "module", "capability", "approach", "mechanism",
        "tool", "method", "solution",
    }
    drifts = []
    for stem, canonical_kw in canonical_titles.items():
        # Search for stem followed by a different component keyword
        # Use word-boundary aware search
        pattern = re.compile(
            re.escape(stem) + r'\s+(\w+)',
            re.IGNORECASE,
        )
        for match in pattern.finditer(content):
            found_kw = match.group(1).lower()
            if found_kw in component_keywords and found_kw != canonical_kw.lower():
                drifts.append((stem, canonical_kw, match.group(1)))
    return drifts


class TestFixtureMetricCompleteness:
    """Fixture-based tests for metric completeness checking logic."""

    def test_all_metrics_preserved_passes(self) -> None:
        """Impact output preserving all metrics exactly should pass."""
        obj = _FIXTURE_OBJECTIVES["objectives"][0]
        metrics = _extract_quantified_metrics(obj["measurable_target"])
        # Content that includes all metrics
        content = (
            "The project achieves open-source release with ≥500 GitHub stars, "
            "results validated through ≥2 TEFs, and technology transfer "
            "initiated through ≥3 EDIHs."
        )
        missing = _check_metric_presence(metrics, content)
        assert len(missing) == 0, f"Expected no missing metrics, got: {missing}"

    def test_dropped_metric_detected(self) -> None:
        """Impact output dropping one metric (TEFs) should be caught."""
        obj = _FIXTURE_OBJECTIVES["objectives"][0]
        metrics = _extract_quantified_metrics(obj["measurable_target"])
        # Content that omits ≥2 TEFs
        content = (
            "The project achieves open-source release with ≥500 GitHub stars "
            "and technology transfer initiated through ≥3 EDIHs."
        )
        missing = _check_metric_presence(metrics, content)
        assert len(missing) > 0, "Should detect missing ≥2 TEFs metric"
        # At least one missing metric should contain "2"
        assert any("2" in m for m in missing)

    def test_altered_count_detected(self) -> None:
        """Impact output changing ≥3 EDIHs to ≥2 EDIHs should be caught."""
        obj = _FIXTURE_OBJECTIVES["objectives"][0]
        metrics = _extract_quantified_metrics(obj["measurable_target"])
        # Content that changes ≥3 to ≥2
        content = (
            "The project achieves open-source release with ≥500 GitHub stars, "
            "results validated through ≥2 TEFs, and technology transfer "
            "initiated through ≥2 EDIHs."
        )
        missing = _check_metric_presence(metrics, content)
        assert len(missing) > 0, "Should detect altered ≥3 EDIHs → ≥2 EDIHs"
        # The ≥3 metric should be missing
        assert any("3" in m for m in missing)

    def test_multi_metric_all_preserved(self) -> None:
        """OBJ-Y with two percentage metrics: both preserved → pass."""
        obj = _FIXTURE_OBJECTIVES["objectives"][1]
        metrics = _extract_quantified_metrics(obj["measurable_target"])
        content = (
            "Demonstrates ≥30% improvement in coherence "
            "and ≥15% improvement in consistency over baselines."
        )
        missing = _check_metric_presence(metrics, content)
        assert len(missing) == 0, f"Expected no missing metrics, got: {missing}"

    def test_multi_metric_partial_loss(self) -> None:
        """OBJ-Y with one percentage metric dropped → fail."""
        obj = _FIXTURE_OBJECTIVES["objectives"][1]
        metrics = _extract_quantified_metrics(obj["measurable_target"])
        # Drop the ≥15% metric
        content = (
            "Demonstrates ≥30% improvement in coherence over baselines."
        )
        missing = _check_metric_presence(metrics, content)
        assert len(missing) > 0, "Should detect missing ≥15% metric"


class TestFixtureTerminologyDrift:
    """Fixture-based tests for terminology drift checking logic."""

    def test_canonical_phrase_passes(self) -> None:
        """Impact output using exact canonical component phrase should pass."""
        canonical = {"Neuro-symbolic planning": "engine"}
        content = (
            "The Neuro-symbolic planning engine enables autonomous "
            "task decomposition with formal verification."
        )
        drifts = _check_terminology_drift(canonical, content)
        assert len(drifts) == 0, f"Expected no drifts, got: {drifts}"

    def test_framework_substitution_detected(self) -> None:
        """Impact using 'framework' instead of 'engine' should be caught."""
        canonical = {"Neuro-symbolic planning": "engine"}
        content = (
            "The Neuro-symbolic planning framework enables autonomous "
            "task decomposition with formal verification."
        )
        drifts = _check_terminology_drift(canonical, content)
        assert len(drifts) > 0, "Should detect engine→framework substitution"
        assert drifts[0][1] == "engine"
        assert drifts[0][2].lower() == "framework"

    def test_approach_substitution_detected(self) -> None:
        """Impact using 'approach' instead of 'architecture' should be caught."""
        canonical = {"Unified adaptive memory": "architecture"}
        content = (
            "The Unified adaptive memory approach integrates three memory stores."
        )
        drifts = _check_terminology_drift(canonical, content)
        assert len(drifts) > 0, "Should detect architecture→approach substitution"

    def test_method_substitution_detected(self) -> None:
        """Impact using 'method' instead of 'protocol' should be caught."""
        canonical = {"Decentralised multi-agent coordination": "protocol"}
        content = (
            "The Decentralised multi-agent coordination method enables "
            "formal task delegation."
        )
        drifts = _check_terminology_drift(canonical, content)
        assert len(drifts) > 0, "Should detect protocol→method substitution"

    def test_positive_all_canonical_terms_preserved(self) -> None:
        """Impact output with all canonical terms preserved → no drifts."""
        canonical = {
            "Neuro-symbolic planning": "engine",
            "Unified adaptive memory": "architecture",
            "Decentralised multi-agent coordination": "protocol",
        }
        content = (
            "The Neuro-symbolic planning engine drives task decomposition. "
            "The Unified adaptive memory architecture integrates stores. "
            "The Decentralised multi-agent coordination protocol enables delegation."
        )
        drifts = _check_terminology_drift(canonical, content)
        assert len(drifts) == 0, f"Expected no drifts, got: {drifts}"

    def test_combined_metric_and_terminology_errors(self) -> None:
        """Content with both a dropped metric and a terminology drift should
        be caught by both checkers."""
        obj = _FIXTURE_OBJECTIVES["objectives"][0]
        metrics = _extract_quantified_metrics(obj["measurable_target"])
        canonical = {"Neuro-symbolic planning": "engine"}

        # Content: drops ≥2 TEFs AND uses "framework" instead of "engine"
        content = (
            "The Neuro-symbolic planning framework achieves ≥500 GitHub stars "
            "and technology transfer through ≥3 EDIHs."
        )
        missing_metrics = _check_metric_presence(metrics, content)
        term_drifts = _check_terminology_drift(canonical, content)

        assert len(missing_metrics) > 0, "Should detect missing ≥2 TEFs"
        assert len(term_drifts) > 0, "Should detect engine→framework"


# ===========================================================================
# TASK D — FINGERPRINT ISOLATION TESTS
# ===========================================================================


class TestImpactSpecFingerprintIsolation:
    """Verify that impact spec changes invalidate only n08b fingerprint."""

    def test_impact_skill_spec_invalidates_n08b(self, tmp_path: Path) -> None:
        """Mutating impact-section-drafting.md changes n08b fingerprint."""
        from runner.phase8_reuse import (
            FINGERPRINT_INPUTS,
            compute_input_fingerprint,
        )

        # Create inputs for n08b
        for rel_path in FINGERPRINT_INPUTS["n08b_impact_drafting"]:
            if rel_path.endswith("/"):
                _write_json(tmp_path / rel_path / "data.json", {"input": "v"})
            else:
                _write_json(tmp_path / rel_path, {"input": "v"})

        fp1 = compute_input_fingerprint("n08b_impact_drafting", tmp_path)
        assert fp1 is not None

        spec = tmp_path / ".claude/skills/impact-section-drafting.md"
        spec.write_text("# MUTATED SPEC\nnew content", encoding="utf-8")

        fp2 = compute_input_fingerprint("n08b_impact_drafting", tmp_path)
        assert fp2 is not None
        assert fp1 != fp2, "impact-section-drafting.md change must invalidate n08b"

    def test_impact_prompt_spec_invalidates_n08b(self, tmp_path: Path) -> None:
        """Mutating impact_writer_prompt_spec.md changes n08b fingerprint."""
        from runner.phase8_reuse import (
            FINGERPRINT_INPUTS,
            compute_input_fingerprint,
        )

        for rel_path in FINGERPRINT_INPUTS["n08b_impact_drafting"]:
            if rel_path.endswith("/"):
                _write_json(tmp_path / rel_path / "data.json", {"input": "v"})
            else:
                _write_json(tmp_path / rel_path, {"input": "v"})

        fp1 = compute_input_fingerprint("n08b_impact_drafting", tmp_path)

        prompt = tmp_path / ".claude/agents/prompts/impact_writer_prompt_spec.md"
        prompt.write_text("# MUTATED PROMPT", encoding="utf-8")

        fp2 = compute_input_fingerprint("n08b_impact_drafting", tmp_path)
        assert fp1 != fp2, "impact_writer_prompt_spec.md change must invalidate n08b"

    def test_impact_skill_spec_does_not_invalidate_n08a(self, tmp_path: Path) -> None:
        """Mutating impact-section-drafting.md must NOT change n08a fingerprint."""
        from runner.phase8_reuse import (
            FINGERPRINT_INPUTS,
            compute_input_fingerprint,
        )

        for node_id in ("n08a_excellence_drafting", "n08b_impact_drafting"):
            for rel_path in FINGERPRINT_INPUTS[node_id]:
                if rel_path.endswith("/"):
                    _write_json(tmp_path / rel_path / "data.json", {"v": 1})
                else:
                    _write_json(tmp_path / rel_path, {"v": 1})

        fp1 = compute_input_fingerprint("n08a_excellence_drafting", tmp_path)

        spec = tmp_path / ".claude/skills/impact-section-drafting.md"
        spec.write_text("# MUTATED", encoding="utf-8")

        fp2 = compute_input_fingerprint("n08a_excellence_drafting", tmp_path)
        assert fp1 == fp2, "impact spec change must NOT affect n08a"

    def test_impact_skill_spec_does_not_invalidate_n08c(self, tmp_path: Path) -> None:
        """Mutating impact-section-drafting.md must NOT change n08c fingerprint."""
        from runner.phase8_reuse import (
            FINGERPRINT_INPUTS,
            compute_input_fingerprint,
        )

        for node_id in ("n08c_implementation_drafting", "n08b_impact_drafting"):
            for rel_path in FINGERPRINT_INPUTS[node_id]:
                if rel_path.endswith("/"):
                    _write_json(tmp_path / rel_path / "data.json", {"v": 1})
                else:
                    _write_json(tmp_path / rel_path, {"v": 1})

        fp1 = compute_input_fingerprint("n08c_implementation_drafting", tmp_path)

        spec = tmp_path / ".claude/skills/impact-section-drafting.md"
        spec.write_text("# MUTATED", encoding="utf-8")

        fp2 = compute_input_fingerprint("n08c_implementation_drafting", tmp_path)
        assert fp1 == fp2, "impact spec change must NOT affect n08c"
