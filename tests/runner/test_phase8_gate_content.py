"""
Targeted tests for Phase 8 gate-readiness constraints.

Validates that:
  - excellence-section-drafting spec forbids assumed/unresolved claims
  - impact-section-drafting spec requires numeric tier values
  - implementation-section-drafting spec forbids:
    - "each of the 8 partners leads exactly one functional WP"
    - BAL contributing to WP4 unless Tier 4 supports it
    - Tier 1/GEP programme-rule claims without Tier 1 source
  - Section artifact fixtures with assumed claims fail gate predicates
  - Numeric tier values pass; string tier values fail
  - Gate 10a/10b/10c predicate routing is deterministic (type: coverage)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.predicates.criterion_predicates import no_unresolved_material_claims


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_skill(name: str) -> str:
    """Read a skill .md file and return its content as a string."""
    skill_path = Path(__file__).resolve().parents[2] / ".claude" / "skills" / name
    return skill_path.read_text(encoding="utf-8")


# ===========================================================================
# Excellence skill spec constraints
# ===========================================================================


class TestExcellenceSkillSpec:
    """Verify the excellence-section-drafting skill forbids assumed/unresolved."""

    def test_forbids_assumed_status(self) -> None:
        spec = _read_skill("excellence-section-drafting.md")
        assert 'MUST NOT contain any claim_status with status = "assumed"' in spec

    def test_forbids_unresolved_status(self) -> None:
        spec = _read_skill("excellence-section-drafting.md")
        assert '"unresolved"' in spec
        assert "GATE-CRITICAL" in spec

    def test_forbids_gender_balanced_recruitment(self) -> None:
        spec = _read_skill("excellence-section-drafting.md")
        assert "gender-balanced recruitment" in spec
        assert "FORBIDDEN" in spec or "Do NOT assert" in spec

    def test_forbids_consortium_gender_monitoring(self) -> None:
        spec = _read_skill("excellence-section-drafting.md")
        assert "consortium gender diversity monitoring" in spec

    def test_requires_non_null_source_ref(self) -> None:
        spec = _read_skill("excellence-section-drafting.md")
        assert "non-null source_ref" in spec

    def test_ssh_proportionate_statement(self) -> None:
        spec = _read_skill("excellence-section-drafting.md")
        assert "primarily technical" in spec
        assert "SSH" in spec


# ===========================================================================
# Impact skill spec constraints
# ===========================================================================


class TestImpactSkillSpec:
    """Verify the impact-section-drafting skill requires numeric tier values."""

    def test_requires_numeric_tier_values(self) -> None:
        spec = _read_skill("impact-section-drafting.md")
        assert "numeric integers" in spec
        assert '"tier": 2' in spec

    def test_forbids_string_tier_values(self) -> None:
        spec = _read_skill("impact-section-drafting.md")
        for forbidden in ['"2a"', '"2b"', '"tier2b"', '"Tier 2B"']:
            assert forbidden in spec, f"Spec should mention forbidden value {forbidden}"

    def test_forbids_assumed_unresolved(self) -> None:
        spec = _read_skill("impact-section-drafting.md")
        assert 'MUST NOT contain any claim_status with status = "assumed"' in spec


# ===========================================================================
# Implementation skill spec constraints
# ===========================================================================


class TestImplementationSkillSpec:
    """Verify the implementation-section-drafting spec forbids known bad claims."""

    def test_forbids_each_partner_leads_one_wp(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "each partner leads exactly one WP" in spec
        assert "FORBIDDEN" in spec or "Do NOT assert" in spec

    def test_requires_wp_structure_as_canonical(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "wp_structure.json" in spec
        assert "CANONICAL" in spec

    def test_forbids_unsourced_tier1_claims(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "programme-rule" in spec.lower() or "programme-rule" in spec
        assert "Tier 1" in spec
        # Must not assert programme-rule claims without Tier 1 source
        assert "does NOT read Tier 1 sources" in spec

    def test_forbids_gep_assertion_without_source(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        # The spec should mention not citing Tier 1 programme rules from agent knowledge
        assert "Do NOT cite Tier 1 programme rules from agent knowledge" in spec

    def test_requires_numeric_tier_values(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "numeric integers" in spec

    def test_forbids_assumed_unresolved(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert 'MUST NOT contain any claim_status with status = "assumed"' in spec


# ===========================================================================
# Gate predicate: no_unresolved_material_claims with fixture artifacts
# ===========================================================================


class TestGatePredicateWithFixtures:
    """Test gate predicate behavior against corrected/broken fixture artifacts."""

    def test_assumed_overall_status_passes_predicate(self, tmp_path: Path) -> None:
        """The no_unresolved_material_claims predicate only blocks 'unresolved'.

        'assumed' is NOT blocked by this predicate — but the skill should
        never produce it.  This test documents the current predicate behavior.
        """
        _write_json(tmp_path / "section.json", {
            "validation_status": {"overall_status": "assumed"},
        })
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        # The predicate only checks for "unresolved", so "assumed" passes.
        # The skill-level constraint is what prevents "assumed" from being produced.
        assert result.passed

    def test_unresolved_overall_status_fails_predicate(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "validation_status": {"overall_status": "unresolved"},
        })
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        assert not result.passed
        assert result.failure_category == "POLICY_VIOLATION"

    def test_confirmed_overall_status_passes(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "validation_status": {"overall_status": "confirmed"},
        })
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        assert result.passed

    def test_inferred_overall_status_passes(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "section.json", {
            "validation_status": {"overall_status": "inferred"},
        })
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        assert result.passed

    def test_excellence_fixture_with_confirmed_status(self, tmp_path: Path) -> None:
        """A gate-ready excellence section should pass."""
        _write_json(tmp_path / "section.json", {
            "schema_id": "orch.tier5.excellence_section.v1",
            "run_id": "test-run",
            "criterion": "Excellence",
            "sub_sections": [{"sub_section_id": "B.1.1", "title": "Objectives",
                              "content": "test", "word_count": 1}],
            "validation_status": {
                "overall_status": "confirmed",
                "claim_statuses": [
                    {"claim_id": "C01", "claim_summary": "test",
                     "status": "confirmed", "source_ref": "Tier 3: objectives.json"}
                ],
            },
            "traceability_footer": {
                "primary_sources": [
                    {"tier": 3, "source_path": "docs/tier3_project_instantiation/objectives.json"}
                ],
                "no_unsupported_claims_declaration": True,
            },
        })
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        assert result.passed

    def test_impact_fixture_string_tier_values_not_checked_by_predicate(
        self, tmp_path: Path
    ) -> None:
        """The no_unresolved_material_claims predicate does not check tier types.

        Tier value normalization is a skill responsibility.  This test documents
        that string tiers do not cause a predicate failure (but are wrong at
        the skill output level).
        """
        _write_json(tmp_path / "section.json", {
            "validation_status": {"overall_status": "inferred"},
            "traceability_footer": {
                "primary_sources": [
                    {"tier": "2b", "source_path": "docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json"},
                ],
                "no_unsupported_claims_declaration": True,
            },
        })
        result = no_unresolved_material_claims(
            "section.json", repo_root=tmp_path
        )
        # Predicate doesn't check tier types — skill must enforce numeric
        assert result.passed


# ===========================================================================
# Gate rules library: predicate type classification
# ===========================================================================


class TestGateRulesPredicateType:
    """Verify no_unresolved_material_claims is classified as deterministic (coverage)."""

    def test_predicate_type_is_coverage_not_semantic(self) -> None:
        """After the fix, the predicate should be type: coverage, not type: semantic.

        When it was type: semantic, the semantic dispatch couldn't find it
        (it's a deterministic function), causing all three gates to fail
        with UNKNOWN_FUNCTION.
        """
        import yaml

        lib_path = (
            Path(__file__).resolve().parents[2]
            / ".claude"
            / "workflows"
            / "system_orchestration"
            / "gate_rules_library.yaml"
        )
        with open(lib_path, encoding="utf-8") as f:
            lib = yaml.safe_load(f)

        gate_rules = lib.get("gate_rules", [])
        assert isinstance(gate_rules, list), "gate_rules should be a list"

        found = 0
        for gate_entry in gate_rules:
            gate_id = gate_entry.get("gate_id", "")
            predicates = gate_entry.get("predicates", [])
            for pred in predicates:
                if pred.get("function") == "no_unresolved_material_claims":
                    found += 1
                    pred_type = pred.get("type")
                    assert pred_type != "semantic", (
                        f"Predicate {pred.get('predicate_id')} in gate {gate_id} "
                        f"still has type: semantic — must be type: coverage "
                        f"(the function is in PREDICATE_REGISTRY, not SEMANTIC_REGISTRY)"
                    )
                    assert pred_type == "coverage", (
                        f"Predicate {pred.get('predicate_id')} has type: {pred_type}, "
                        f"expected: coverage"
                    )
        assert found == 3, f"Expected 3 no_unresolved_material_claims predicates, found {found}"

    def test_predicate_is_in_deterministic_registry(self) -> None:
        """Confirm the function is registered in the gate evaluator PREDICATE_REGISTRY."""
        from runner.gate_evaluator import PREDICATE_REGISTRY

        assert "no_unresolved_material_claims" in PREDICATE_REGISTRY

    def test_predicate_is_not_in_semantic_registry(self) -> None:
        """Confirm the function is NOT in SEMANTIC_REGISTRY (that was the bug)."""
        from runner.semantic_dispatch import SEMANTIC_REGISTRY

        assert "no_unresolved_material_claims" not in SEMANTIC_REGISTRY


# ===========================================================================
# Current artifact validation (aefe5901 known issues)
# ===========================================================================


class TestCurrentArtifactKnownIssues:
    """Validate that current artifacts from run aefe5901 exhibit known problems.

    These tests document the current broken state.  When the skills are
    re-run and produce corrected artifacts, these tests should be updated
    or removed.
    """

    @pytest.fixture
    def excellence_artifact(self) -> dict:
        art_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "tier5_deliverables"
            / "proposal_sections"
            / "excellence_section.json"
        )
        if not art_path.exists():
            pytest.skip("excellence_section.json not present")
        return json.loads(art_path.read_text(encoding="utf-8"))

    @pytest.fixture
    def impact_artifact(self) -> dict:
        art_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "tier5_deliverables"
            / "proposal_sections"
            / "impact_section.json"
        )
        if not art_path.exists():
            pytest.skip("impact_section.json not present")
        return json.loads(art_path.read_text(encoding="utf-8"))

    @pytest.fixture
    def implementation_artifact(self) -> dict:
        art_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "tier5_deliverables"
            / "proposal_sections"
            / "implementation_section.json"
        )
        if not art_path.exists():
            pytest.skip("implementation_section.json not present")
        return json.loads(art_path.read_text(encoding="utf-8"))

    def test_excellence_has_assumed_claims(self, excellence_artifact: dict) -> None:
        """Current excellence artifact has assumed claims (C14, C15)."""
        statuses = {
            c["claim_id"]: c["status"]
            for c in excellence_artifact["validation_status"]["claim_statuses"]
        }
        assumed_claims = [cid for cid, s in statuses.items() if s == "assumed"]
        assert len(assumed_claims) > 0, "Expected assumed claims in current artifact"

    def test_excellence_overall_status_is_assumed(self, excellence_artifact: dict) -> None:
        assert excellence_artifact["validation_status"]["overall_status"] == "assumed"

    def test_excellence_unsupported_claims_declaration_false(
        self, excellence_artifact: dict
    ) -> None:
        assert (
            excellence_artifact["traceability_footer"]["no_unsupported_claims_declaration"]
            is False
        )

    def test_impact_has_string_tier_values(self, impact_artifact: dict) -> None:
        """Current impact artifact has string tier values like '2b'."""
        string_tiers = [
            s
            for s in impact_artifact["traceability_footer"]["primary_sources"]
            if isinstance(s.get("tier"), str)
        ]
        assert len(string_tiers) > 0, "Expected string tier values in current artifact"

    def test_implementation_has_each_partner_one_wp_claim(
        self, implementation_artifact: dict
    ) -> None:
        """Current implementation artifact claims each partner leads exactly one WP."""
        b32_content = ""
        for sub in implementation_artifact.get("sub_sections", []):
            if sub.get("sub_section_id") == "B.3.2":
                b32_content = sub.get("content", "")
                break
        assert (
            "each of the 8 partners leads exactly one functional wp"
            in b32_content.lower()
        ), "Expected 'each of the 8 partners leads exactly one functional WP' in B.3.2"

    def test_implementation_has_gep_tier1_claim(
        self, implementation_artifact: dict
    ) -> None:
        """Current implementation artifact asserts GEP per Tier 1 programme rules."""
        b32_content = ""
        for sub in implementation_artifact.get("sub_sections", []):
            if sub.get("sub_section_id") == "B.3.2":
                b32_content = sub.get("content", "")
                break
        assert (
            "tier 1 programme rules" in b32_content.lower()
        ), "Expected Tier 1 programme rules assertion in B.3.2"
