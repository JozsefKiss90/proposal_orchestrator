"""
Tests for partial metric loss fix in impact-section-drafting.md.

Covers:
  1. Spec invariant — slim spec declares canonical-pack input and copying rules
     (metric enforcement delegated to preflight predicates and gate_10b/10d)
  2. Spec anti-regression — broad self-audit patterns NOT reintroduced
  3. Fixture-based metric loss detection via cross_section_consistency
  4. Fingerprint isolation — spec change invalidates only n08b

All tests are static — no live Claude invocations.
All fixture data is project-agnostic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"


def _read_impact_spec() -> str:
    path = SKILLS_DIR / "impact-section-drafting.md"
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===========================================================================
# 1. SPEC INVARIANT — slim spec delegates metric enforcement to preflight/gates
# ===========================================================================


class TestMetricLossSpecInvariant:
    """Verify impact-section-drafting.md declares the architectural hooks that
    replace the old verbose multi-metric preservation prose.

    After Phase 8 skill slimming, metric/terminology enforcement is delegated to:
      - canonical_reference_pack.json (built by runner/phase8_canonical_pack.py)
      - Preflight predicates (canonical_terms_preserved, deliverable_identity_preserved,
        partner_names_preserved) registered in gate_10b
      - cross_section_consistency predicate at gate_10d
    """

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_impact_spec()

    def test_declares_canonical_reference_pack_input(self) -> None:
        """Skill spec must declare canonical_reference_pack.json as an input."""
        assert "canonical_reference_pack.json" in self.text

    def test_has_canonical_copying_rules_section(self) -> None:
        """Skill spec must contain a 'Canonical Copying Rules' section."""
        assert "Canonical Copying Rules" in self.text

    def test_forbids_renaming_and_shortening(self) -> None:
        """Skill spec must forbid renaming, shortening, or paraphrasing canonical terms."""
        assert "Do not rename" in self.text
        assert "shorten" in self.text

    def test_incomplete_output_on_missing_section(self) -> None:
        """Skill spec must mention INCOMPLETE_OUTPUT for missing mandatory sub-sections."""
        assert "INCOMPLETE_OUTPUT" in self.text

    def test_forbids_reassigning_ids(self) -> None:
        """Skill spec must forbid reassigning IDs from source artifacts."""
        assert "reassign IDs" in self.text


# ===========================================================================
# 2. SPEC ANTI-REGRESSION — broad self-audit NOT reintroduced
# ===========================================================================


class TestMetricLossSpecAntiRegression:
    """Verify impact-section-drafting.md does NOT reintroduce bloat patterns."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_impact_spec()

    def test_no_gate_readiness_self_audit(self) -> None:
        assert "Gate-readiness check" not in self.text
        assert "gate-readiness self-audit" not in self.text.lower()

    def test_no_exhaustive_validation_scan(self) -> None:
        assert "Extract every quantified metric" not in self.text
        assert "Verify each extracted metric appears" not in self.text

    def test_no_step_2_11(self) -> None:
        assert "Step 2.11" not in self.text

    def test_no_broad_incomplete_output_canonicalization_block(self) -> None:
        assert "missing measurable_target component" not in self.text
        assert "canonical terminology drift" not in self.text
        assert "unsupported WP attribution" not in self.text

    def test_no_large_forbidden_pattern_lists(self) -> None:
        """No large forbidden-pattern enumerations (>5 items) reintroduced."""
        # Count "Forbidden:" sections — should be bounded
        forbidden_count = self.text.count("**Forbidden:**")
        # CCR-1 through CCR-4 each have one; that's fine
        # A new large enumeration would push this above 5
        assert forbidden_count <= 5, (
            f"Too many Forbidden sections ({forbidden_count}); "
            "may indicate large forbidden-pattern list reintroduced"
        )

    def test_no_pre_output_scan_with_colon(self) -> None:
        """Pre-output scan: pattern must not be reintroduced."""
        assert "Pre-output scan:" not in self.text

    def test_no_cross_section_self_check(self) -> None:
        assert "cross-section self-check" not in self.text.lower()


# ===========================================================================
# 3. FIXTURE-BASED METRIC LOSS DETECTION
# ===========================================================================


def _make_section(*, criterion: str, content: str) -> dict:
    schema_map = {
        "Excellence": "orch.tier5.excellence_section.v1",
        "Impact": "orch.tier5.impact_section.v1",
        "Implementation": "orch.tier5.implementation_section.v1",
    }
    result = {
        "schema_id": schema_map[criterion],
        "run_id": "test-metric-loss",
        "criterion": criterion,
        "sub_sections": [
            {"sub_section_id": "B.1.1", "title": "Main", "content": content},
        ],
    }
    if criterion == "Impact":
        result["impact_pathway_refs"] = []
        result["dec_coverage"] = {
            "dissemination_addressed": True,
            "exploitation_addressed": True,
            "communication_addressed": True,
        }
    if criterion == "Implementation":
        result["wp_table_refs"] = ["WP1"]
        result["gantt_ref"] = "gantt.json"
        result["milestone_refs"] = ["MS1"]
        result["risk_register_ref"] = "risk.json"
    return result


def _setup_metric_test(
    tmp_path: Path,
    *,
    impact_content: str,
    measurable_target: str = ">=20% improvement in recovery time AND >=15% improvement in schedule adherence",
    obj_id: str = "OBJ-X",
) -> None:
    """Set up minimal repo for metric completeness test."""
    assembled = {
        "schema_id": "orch.tier5.part_b_assembled_draft.v1",
        "run_id": "test-metric-loss",
        "sections": [
            {"section_id": "s1", "criterion": "Excellence", "order": 1,
             "artifact_path": "sections/excellence_section.json"},
            {"section_id": "s2", "criterion": "Impact", "order": 2,
             "artifact_path": "sections/impact_section.json"},
            {"section_id": "s3", "criterion": "Implementation", "order": 3,
             "artifact_path": "sections/implementation_section.json"},
        ],
        "consistency_log": [],
    }
    objectives = {
        "objectives": [
            {
                "id": obj_id,
                "title": "Generic multi-metric objective",
                "measurable_target": measurable_target,
                "target_month": 36,
                "responsible_partner": "P1",
            },
        ],
    }
    _write_json(tmp_path / "assembled.json", assembled)
    _write_json(
        tmp_path / "sections" / "excellence_section.json",
        _make_section(criterion="Excellence", content=f"{obj_id} defined."),
    )
    _write_json(
        tmp_path / "sections" / "impact_section.json",
        _make_section(criterion="Impact", content=impact_content),
    )
    _write_json(
        tmp_path / "sections" / "implementation_section.json",
        _make_section(criterion="Implementation", content="Implementation."),
    )
    _write_json(
        tmp_path / "tier3" / "architecture_inputs" / "objectives.json",
        objectives,
    )


class TestFixtureMetricLoss:
    """Fixture-based tests: partial metric loss detected by cross_section_consistency."""

    def test_partial_metric_loss_detected(self, tmp_path: Path) -> None:
        """Impact text with only the first metric clause flags CC-06-style failure."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        _setup_metric_test(
            tmp_path,
            measurable_target=(
                "\u226520% improvement in recovery time "
                "AND \u226515% improvement in schedule adherence"
            ),
            impact_content=(
                "OBJ-X achieves \u226520% improvement in recovery time."
            ),
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        metric_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "metric_completeness"
        ]
        assert len(metric_issues) >= 1, "Should flag missing \u226515% metric"
        assert "15%" in str(metric_issues[0]["details"])

    def test_both_metric_clauses_present_passes(self, tmp_path: Path) -> None:
        """Impact text with both metric clauses passes metric completeness."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        _setup_metric_test(
            tmp_path,
            measurable_target=(
                "\u226520% improvement in recovery time "
                "AND \u226515% improvement in schedule adherence"
            ),
            impact_content=(
                "OBJ-X achieves \u226520% improvement in recovery time "
                "AND \u226515% improvement in schedule adherence."
            ),
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_three_metric_objective_partial_loss(self, tmp_path: Path) -> None:
        """Objective with 3 percentage metric clauses: dropping one flags failure."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        _setup_metric_test(
            tmp_path,
            measurable_target=(
                "\u226540% improvement in plan success AND "
                "\u226530% improvement in coherence AND "
                "\u226525% improvement in joint task completion"
            ),
            impact_content=(
                "OBJ-X achieves \u226540% improvement in plan success and "
                "\u226525% improvement in joint task completion."
            ),
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        metric_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "metric_completeness"
        ]
        assert len(metric_issues) >= 1
        assert "30%" in str(metric_issues[0]["details"])

    def test_objective_not_referenced_skips_check(self, tmp_path: Path) -> None:
        """When Impact doesn't reference the objective at all, no metric error."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        _setup_metric_test(
            tmp_path,
            measurable_target=(
                "\u226520% recovery AND \u226515% adherence"
            ),
            impact_content="General impact narrative without objective reference.",
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed


# ===========================================================================
# 4. FINGERPRINT ISOLATION — impact spec change invalidates only n08b
# ===========================================================================


class TestMetricLossFingerprintIsolation:
    """Verify impact spec change invalidates n08b but not n08a/n08c."""

    def test_impact_spec_invalidates_n08b(self, tmp_path: Path) -> None:
        from runner.phase8_reuse import (
            FINGERPRINT_INPUTS,
            compute_input_fingerprint,
        )

        for rel_path in FINGERPRINT_INPUTS["n08b_impact_drafting"]:
            if rel_path.endswith("/"):
                _write_json(tmp_path / rel_path / "data.json", {"v": 1})
            else:
                _write_json(tmp_path / rel_path, {"v": 1})

        fp1 = compute_input_fingerprint("n08b_impact_drafting", tmp_path)
        assert fp1 is not None

        spec = tmp_path / ".claude/skills/impact-section-drafting.md"
        spec.write_text("# MUTATED SPEC — metric loss fix", encoding="utf-8")

        fp2 = compute_input_fingerprint("n08b_impact_drafting", tmp_path)
        assert fp2 is not None
        assert fp1 != fp2, "impact-section-drafting.md change must invalidate n08b"

    def test_impact_spec_does_not_invalidate_n08a(self, tmp_path: Path) -> None:
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

    def test_impact_spec_does_not_invalidate_n08c(self, tmp_path: Path) -> None:
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
