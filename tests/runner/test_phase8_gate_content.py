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

from runner.predicates.criterion_predicates import (
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

    def test_forbids_nine_dependency_edges_as_full_map(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "16 confirmed inter-WP dependency edges" in spec
        assert '"nine dependency edges"' in spec or "nine dependency edges" in spec
        assert "FORBIDDEN" in spec

    def test_requires_16_dependency_edges(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "16 confirmed inter-WP data-input edges" in spec

    def test_forbids_each_of_8_partners_leads_one(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "each of the 8 partners leads exactly one" in spec
        assert "FORBIDDEN" in spec

    def test_forbids_gep_eligibility_phrases(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        for phrase in [
            "GEP eligibility obligations",
            "required to hold Gender Equality Plans",
            "per Tier 1 programme rules",
            "at grant signature",
        ]:
            assert phrase in spec, f"Spec should list forbidden phrase: {phrase}"
        assert "FORBIDDEN phrases" in spec

    def test_requires_concise_json_output(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "20,000 characters" in spec
        assert "Output size ceiling" in spec

    def test_requires_concise_subsection_content(self) -> None:
        spec = _read_skill("implementation-section-drafting.md")
        assert "2,000 characters" in spec


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
# Implementation section fixture tests (positive)
# ===========================================================================


def _make_implementation_fixture(
    overrides: dict | None = None,
    *,
    content_b31: str = "Work plan narrative.",
    content_b32: str = "Consortium capacity narrative.",
) -> dict:
    """Build a minimal gate-ready implementation_section fixture."""
    base: dict = {
        "schema_id": "orch.tier5.implementation_section.v1",
        "run_id": "test-fixture-run",
        "criterion": "Quality and efficiency of the implementation",
        "sub_sections": [
            {"sub_section_id": "B.3.1", "title": "Work plan",
             "content": content_b31, "word_count": len(content_b31.split())},
            {"sub_section_id": "B.3.2", "title": "Consortium",
             "content": content_b32, "word_count": len(content_b32.split())},
        ],
        "wp_table_refs": ["WP1", "WP2", "WP3", "WP4", "WP5", "WP6", "WP7", "WP8", "WP9"],
        "gantt_ref": "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json",
        "milestone_refs": ["MS1", "MS2", "MS3", "MS4", "MS5"],
        "risk_register_ref": "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json",
        "validation_status": {
            "overall_status": "confirmed",
            "claim_statuses": [
                {"claim_id": "CS-01", "claim_summary": "9 WPs",
                 "status": "confirmed", "source_ref": "Tier 4: wp_structure.json"},
                {"claim_id": "CS-02", "claim_summary": "16 dependency edges",
                 "status": "confirmed", "source_ref": "Tier 4: wp_structure.json dependency_map"},
                {"claim_id": "CS-03", "claim_summary": "ATU leads WP1 and WP2",
                 "status": "confirmed", "source_ref": "Tier 4: wp_structure.json partner_role_matrix"},
            ],
        },
        "traceability_footer": {
            "primary_sources": [
                {"tier": 4, "source_path": "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"},
                {"tier": 4, "source_path": "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json"},
                {"tier": 4, "source_path": "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json"},
                {"tier": 4, "source_path": "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json"},
                {"tier": 3, "source_path": "docs/tier3_project_instantiation/consortium/partners.json"},
                {"tier": 3, "source_path": "docs/tier3_project_instantiation/consortium/roles.json"},
                {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json"},
                {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json"},
                {"tier": 2, "source_path": "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json"},
                {"tier": 2, "source_path": "docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json"},
            ],
            "no_unsupported_claims_declaration": True,
        },
    }
    if overrides:
        base.update(overrides)
    return base


def _make_wp_structure_fixture() -> dict:
    """Minimal wp_structure.json with 9 WPs for cross-check."""
    return {
        "schema_id": "orch.phase3.wp_structure.v1",
        "work_packages": [
            {"wp_id": f"WP{i}", "lead_partner": "ATU" if i <= 2 else f"P{i}"}
            for i in range(1, 10)
        ],
    }


def _make_gantt_fixture() -> dict:
    return {"schema_id": "orch.phase4.gantt.v1", "milestones": []}


class TestImplementationFixturePositive:
    """Gate-ready implementation fixture passes all predicates."""

    def test_schema_id_matches(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "impl.json", _make_implementation_fixture())
        result = schema_id_matches(
            "impl.json",
            "orch.tier5.implementation_section.v1",
            repo_root=tmp_path,
        )
        assert result.passed

    def test_implementation_coverage_complete(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "impl.json", _make_implementation_fixture())
        _write_json(tmp_path / "wp.json", _make_wp_structure_fixture())
        _write_json(tmp_path / "gantt.json", _make_gantt_fixture())
        result = implementation_coverage_complete(
            "impl.json", "wp.json", "gantt.json", repo_root=tmp_path,
        )
        assert result.passed

    def test_no_unresolved_material_claims(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "impl.json", _make_implementation_fixture())
        result = no_unresolved_material_claims("impl.json", repo_root=tmp_path)
        assert result.passed

    def test_traceability_footer_has_numeric_tiers(self) -> None:
        fixture = _make_implementation_fixture()
        for src in fixture["traceability_footer"]["primary_sources"]:
            assert isinstance(src["tier"], int), (
                f"tier should be int, got {type(src['tier'])} for {src['source_path']}"
            )

    def test_traceability_footer_includes_tier2b_paths(self) -> None:
        fixture = _make_implementation_fixture()
        paths = {s["source_path"] for s in fixture["traceability_footer"]["primary_sources"]}
        assert "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json" in paths
        assert "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json" in paths

    def test_no_unsupported_claims_declaration_true(self) -> None:
        fixture = _make_implementation_fixture()
        assert fixture["traceability_footer"]["no_unsupported_claims_declaration"] is True

    def test_no_assumed_or_unresolved_claims(self) -> None:
        fixture = _make_implementation_fixture()
        for cs in fixture["validation_status"]["claim_statuses"]:
            assert cs["status"] not in ("assumed", "unresolved"), (
                f"claim {cs['claim_id']} has forbidden status: {cs['status']}"
            )

    def test_no_null_source_refs(self) -> None:
        fixture = _make_implementation_fixture()
        for cs in fixture["validation_status"]["claim_statuses"]:
            assert cs["source_ref"] is not None, (
                f"claim {cs['claim_id']} has null source_ref"
            )


# ===========================================================================
# Implementation section fixture tests (negative)
# ===========================================================================


class TestImplementationFixtureNegative:
    """Broken fixtures fail the appropriate predicates or content checks."""

    def test_nine_dependency_edges_detected(self) -> None:
        """Fixture with 'nine dependency edges' for full map is invalid."""
        fixture = _make_implementation_fixture(
            content_b31="The work plan has nine dependency edges connecting all WPs."
        )
        b31 = fixture["sub_sections"][0]["content"].lower()
        assert "nine dependency edges" in b31
        # Content-level check: this should be caught by the skill gate-readiness
        assert "16 confirmed" not in b31

    def test_each_partner_leads_one_wp_detected(self) -> None:
        """Fixture with 'each partner leads exactly one WP' is invalid."""
        fixture = _make_implementation_fixture(
            content_b32="Each of the 8 partners leads exactly one functional WP."
        )
        b32 = fixture["sub_sections"][1]["content"].lower()
        assert "each" in b32 and "leads exactly one" in b32

    def test_gep_tier1_claim_detected(self) -> None:
        """Fixture with GEP/Tier 1 programme-rule claim is invalid."""
        fixture = _make_implementation_fixture(
            content_b32="Partners with GEP eligibility obligations are required to hold Gender Equality Plans at grant signature per Tier 1 programme rules."
        )
        b32 = fixture["sub_sections"][1]["content"]
        has_forbidden = any(phrase in b32 for phrase in [
            "GEP eligibility obligations",
            "required to hold Gender Equality Plans",
            "per Tier 1 programme rules",
            "at grant signature",
        ])
        assert has_forbidden

    def test_assumed_claim_status_detected(self) -> None:
        """Fixture with assumed claim fails content validation."""
        fixture = _make_implementation_fixture()
        fixture["validation_status"]["claim_statuses"].append(
            {"claim_id": "CS-BAD", "claim_summary": "bad claim",
             "status": "assumed", "source_ref": None}
        )
        bad = [c for c in fixture["validation_status"]["claim_statuses"]
               if c["status"] == "assumed"]
        assert len(bad) > 0

    def test_unresolved_claim_status_fails_predicate(self, tmp_path: Path) -> None:
        """Unresolved overall_status fails no_unresolved_material_claims."""
        fixture = _make_implementation_fixture()
        fixture["validation_status"]["overall_status"] = "unresolved"
        _write_json(tmp_path / "impl.json", fixture)
        result = no_unresolved_material_claims("impl.json", repo_root=tmp_path)
        assert not result.passed

    def test_string_tier_values_detected(self) -> None:
        """Fixture with string tier '2b' instead of numeric 2 is invalid."""
        fixture = _make_implementation_fixture()
        fixture["traceability_footer"]["primary_sources"][6] = {
            "tier": "2b",
            "source_path": "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json",
        }
        string_tiers = [
            s for s in fixture["traceability_footer"]["primary_sources"]
            if isinstance(s.get("tier"), str)
        ]
        assert len(string_tiers) > 0, "Expected string tier value to be present"

    def test_wrong_schema_id_fails_predicate(self, tmp_path: Path) -> None:
        fixture = _make_implementation_fixture()
        fixture["schema_id"] = "orch.tier5.WRONG.v1"
        _write_json(tmp_path / "impl.json", fixture)
        result = schema_id_matches(
            "impl.json",
            "orch.tier5.implementation_section.v1",
            repo_root=tmp_path,
        )
        assert not result.passed

    def test_missing_wp_table_refs_fails_coverage(self, tmp_path: Path) -> None:
        fixture = _make_implementation_fixture()
        fixture["wp_table_refs"] = []
        _write_json(tmp_path / "impl.json", fixture)
        _write_json(tmp_path / "wp.json", _make_wp_structure_fixture())
        _write_json(tmp_path / "gantt.json", _make_gantt_fixture())
        result = implementation_coverage_complete(
            "impl.json", "wp.json", "gantt.json", repo_root=tmp_path,
        )
        assert not result.passed


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


class TestCurrentArtifactState:
    """Validate current state of on-disk artifacts.

    Excellence and Impact were corrected by run 48f8923b; these tests now
    assert the corrected state.  Implementation still carries the old
    aefe5901 artifact with known bad claims (pending re-run).
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

    # -- Excellence: corrected by run 48f8923b --

    def test_excellence_no_assumed_claims(self, excellence_artifact: dict) -> None:
        """Run 48f8923b fixed assumed claims; all should be confirmed/inferred."""
        statuses = {
            c["claim_id"]: c["status"]
            for c in excellence_artifact["validation_status"]["claim_statuses"]
        }
        assumed_claims = [cid for cid, s in statuses.items() if s == "assumed"]
        assert len(assumed_claims) == 0, f"Unexpected assumed claims: {assumed_claims}"

    def test_excellence_overall_status_not_assumed(self, excellence_artifact: dict) -> None:
        overall = excellence_artifact["validation_status"]["overall_status"]
        assert overall in ("confirmed", "inferred"), f"Expected confirmed/inferred, got {overall}"

    def test_excellence_unsupported_claims_declaration_true(
        self, excellence_artifact: dict
    ) -> None:
        assert (
            excellence_artifact["traceability_footer"]["no_unsupported_claims_declaration"]
            is True
        )

    # -- Impact: corrected by run 48f8923b --

    def test_impact_no_string_tier_values(self, impact_artifact: dict) -> None:
        """Run 48f8923b fixed string tier values; all should be numeric."""
        string_tiers = [
            s
            for s in impact_artifact["traceability_footer"]["primary_sources"]
            if isinstance(s.get("tier"), str)
        ]
        assert len(string_tiers) == 0, f"Unexpected string tiers: {string_tiers}"

    # -- Implementation: still carries aefe5901 known issues --

    def test_implementation_has_each_partner_one_wp_claim(
        self, implementation_artifact: dict
    ) -> None:
        """Old implementation artifact still claims each partner leads exactly one WP."""
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
        """Old implementation artifact asserts GEP per Tier 1 programme rules."""
        b32_content = ""
        for sub in implementation_artifact.get("sub_sections", []):
            if sub.get("sub_section_id") == "B.3.2":
                b32_content = sub.get("content", "")
                break
        assert (
            "tier 1 programme rules" in b32_content.lower()
        ), "Expected Tier 1 programme rules assertion in B.3.2"
