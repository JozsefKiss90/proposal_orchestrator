"""
Targeted tests for Phase 8 canonicalization architecture.

Verifies:
  1. Spec leanness — heavy self-validation removed, concise guidance retained
  2. Drafting spec fail-fast scope — only cheap guards remain
  3. Deterministic validator tests — gate predicates enforce canonicalization
  4. Positive validator tests — correct artifacts pass
  5. Gate integration — predicates are callable without error
  6. Fingerprint invalidation — spec changes invalidate correct nodes

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

EXCELLENCE_SPEC = SKILLS_DIR / "excellence-section-drafting.md"
IMPACT_SPEC = SKILLS_DIR / "impact-section-drafting.md"
IMPLEMENTATION_SPEC = SKILLS_DIR / "implementation-section-drafting.md"
CONSISTENCY_SPEC = SKILLS_DIR / "cross-section-consistency-check.md"


def _read_spec(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ===========================================================================
# 1. SPEC LEANNESS — heavy self-validation removed
# ===========================================================================


class TestSpecLeanness:
    """Drafting specs must NOT contain broad exhaustive scan requirements."""

    @pytest.fixture(autouse=True)
    def _load_specs(self) -> None:
        self.excellence = _read_spec(EXCELLENCE_SPEC)
        self.impact = _read_spec(IMPACT_SPEC)
        self.implementation = _read_spec(IMPLEMENTATION_SPEC)

    def test_excellence_no_cross_section_self_check(self) -> None:
        """Excellence spec no longer requires cross-section self-check."""
        assert "Cross-Section Self-Check Before Output" not in self.excellence

    def test_excellence_no_broad_pre_output_scan(self) -> None:
        """Excellence spec no longer requires scanning all objectives for metrics."""
        assert "Before writing the JSON artifact, scan the draft and verify every" not in self.excellence
        assert "scan the draft and verify" not in self.excellence

    def test_excellence_no_component_extraction_from_multiple_artifacts(self) -> None:
        """Excellence spec does not require extracting components from impact/impl architectures."""
        assert "Extract canonical component/system names from:" not in self.excellence

    def test_impact_no_cross_section_self_check(self) -> None:
        """Impact spec no longer requires cross-section self-check."""
        assert "Cross-Section Self-Check Before Output" not in self.impact

    def test_impact_no_broad_pre_output_metric_scan(self) -> None:
        """Impact spec no longer requires pre-output metric extraction scan."""
        # The old block had "Pre-output scan: Before producing output, for each objective"
        assert "Pre-output scan:" not in self.impact

    def test_impact_no_terminology_pre_output_scan(self) -> None:
        """Impact spec no longer has terminology pre-output scan block."""
        assert "Extract the multi-word component phrase" not in self.impact

    def test_impact_no_extract_every_quantified_metric(self) -> None:
        """Impact spec must not contain exhaustive metric extraction instruction."""
        assert "Extract every quantified metric" not in self.impact
        assert "extract every quantified metric" not in self.impact

    def test_impact_no_verify_each_extracted_metric(self) -> None:
        """Impact spec must not contain exhaustive metric verification instruction."""
        assert "Verify each extracted metric appears" not in self.impact
        assert "verify each extracted metric appears" not in self.impact

    def test_impact_no_component_keyword_scan(self) -> None:
        """Impact spec must not require component keyword verification scan."""
        assert "component keyword" not in self.impact

    def test_impact_no_objective_title_precedence_rule(self) -> None:
        """Impact spec must not contain objective-vs-outcome title precedence logic."""
        assert "objective title takes precedence" not in self.impact

    def test_impact_no_cross_section_self_check_instruction(self) -> None:
        """Impact spec must not contain cross-section self-check instruction."""
        assert "cross-section self-check" not in self.impact.lower()

    def test_implementation_no_cross_section_self_check(self) -> None:
        """Implementation spec no longer requires cross-section self-check."""
        assert "Cross-Section Self-Check Before Output" not in self.implementation

    def test_implementation_no_broad_component_extraction(self) -> None:
        """Implementation spec does not require component extraction from architectures."""
        assert "Extract canonical component/system names from:" not in self.implementation


# ===========================================================================
# 2. CONCISE GUIDANCE RETAINED
# ===========================================================================


class TestConciseGuidancePresent:
    """Drafting specs retain concise canonical reference guidance."""

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

    def test_all_have_drafting_guidance_section(self) -> None:
        """All specs have the concise 'Drafting Guidance' section."""
        for name, content in self.all_specs.items():
            assert (
                "Drafting Guidance — Canonical References" in content
            ), f"{name} spec missing concise drafting guidance"

    def test_all_mention_objectives_json(self) -> None:
        """All specs reference objectives.json for canonical IDs/titles."""
        for name, content in self.all_specs.items():
            assert "objectives.json" in content, f"{name} spec missing objectives.json ref"

    def test_all_mention_wp_structure(self) -> None:
        """All specs reference wp_structure.json for WP mappings."""
        for name, content in self.all_specs.items():
            assert "wp_structure.json" in content, f"{name} spec missing wp_structure.json ref"

    def test_all_mention_gate_predicates(self) -> None:
        """All specs note that enforcement is by gate predicates."""
        for name, content in self.all_specs.items():
            assert (
                "enforced deterministically by gate predicates" in content
            ), f"{name} spec missing gate predicate delegation note"

    def test_all_mention_legal_name_truncation(self) -> None:
        """All specs mention not truncating legal names."""
        for name, content in self.all_specs.items():
            assert (
                "truncate legal names" in content
            ), f"{name} spec missing legal name guidance"

    def test_impact_has_preserve_numeric_values(self) -> None:
        """Impact spec retains 'preserve numeric values' concise guidance."""
        assert "preserve" in self.impact.lower() and "numeric" in self.impact.lower()

    def test_impact_has_do_not_invent_wp_mappings(self) -> None:
        """Impact spec retains 'Do not invent WP mappings' guidance."""
        assert "Do not invent WP mappings" in self.impact

    def test_impact_has_do_not_describe_kpis_as_deliverables(self) -> None:
        """Impact spec retains 'Do not describe KPIs as deliverables' guidance."""
        assert "Do not describe KPIs as deliverables" in self.impact

    def test_impact_has_deterministic_gate_predicates(self) -> None:
        """Impact spec delegates canonicalization to deterministic gate predicates."""
        assert "deterministic gate predicates" in self.impact

    def test_impact_has_use_objective_ids(self) -> None:
        """Impact spec retains 'Use objective IDs' guidance."""
        assert "Use objective IDs" in self.impact


# ===========================================================================
# 3. DRAFTING SPEC FAIL-FAST SCOPE
# ===========================================================================


class TestFailFastScope:
    """Drafting specs keep only cheap fail-fast guards, not broad validation."""

    @pytest.fixture(autouse=True)
    def _load_specs(self) -> None:
        self.excellence = _read_spec(EXCELLENCE_SPEC)
        self.impact = _read_spec(IMPACT_SPEC)

    def test_excellence_keeps_budget_gate_guard(self) -> None:
        assert "budget gate" in self.excellence.lower()

    def test_excellence_keeps_missing_input_guard(self) -> None:
        assert "MISSING_INPUT" in self.excellence

    def test_excellence_keeps_unresolved_claims_guard(self) -> None:
        assert "assumed" in self.excellence and "unresolved" in self.excellence

    def test_excellence_keeps_objective_enumeration(self) -> None:
        """Objective enumeration completeness is cheap and retained."""
        assert "objective ID from" in self.excellence

    def test_excellence_no_terminology_drift_failfast(self) -> None:
        """Terminology drift is now enforced by gates, not as a skill fail-fast."""
        assert 'Terminology drift: canonical name' not in self.excellence

    def test_impact_keeps_budget_gate_guard(self) -> None:
        assert "budget gate" in self.impact.lower()

    def test_impact_keeps_missing_input_guard(self) -> None:
        assert "MISSING_INPUT" in self.impact

    def test_impact_keeps_unresolved_claims_guard(self) -> None:
        assert "assumed" in self.impact and "unresolved" in self.impact

    def test_impact_keeps_d401_guard(self) -> None:
        """D4-01 identity guard is bounded and retained."""
        assert "D4-01" in self.impact

    def test_impact_no_metric_completeness_failfast(self) -> None:
        """Metric completeness is enforced by gate, not as skill fail-fast."""
        assert "Partial metric loss for" not in self.impact

    def test_impact_no_terminology_drift_failfast(self) -> None:
        """Terminology drift is enforced by gate, not as skill fail-fast."""
        assert "Terminology drift: canonical name" not in self.impact

    def test_impact_no_exhaustive_canonicalization_failfast(self) -> None:
        """INCOMPLETE_OUTPUT must not be required for broad metric/terminology canonicalization."""
        # Find all INCOMPLETE_OUTPUT contexts in the spec
        # The spec should not mandate INCOMPLETE_OUTPUT for canonicalization mismatches
        assert "return INCOMPLETE_OUTPUT" not in self.impact or \
            "canonicalization" not in self.impact.lower().split("return incomplete_output")[0][-200:]
        # More direct: the specific canonicalization fail-fast patterns must not exist
        assert "missing measurable_target component" not in self.impact
        assert "canonical terminology drift" not in self.impact
        assert "unsupported WP attribution" not in self.impact


# ===========================================================================
# 4. DETERMINISTIC VALIDATOR TESTS (gate predicates)
# ===========================================================================


class TestDeterministicValidators:
    """Gate predicates correctly enforce canonicalization rules."""

    def _make_objectives(self, *specs: tuple[str, str, str]) -> dict:
        return {
            "objectives": [
                {"id": oid, "title": title, "measurable_target": target,
                 "target_month": 36, "responsible_partner": "ATU"}
                for oid, title, target in specs
            ]
        }

    def _make_partners(self, *specs: tuple[str, str]) -> dict:
        return {
            "partners": [
                {"partner_number": i + 1, "short_name": s, "legal_name": l,
                 "country": "DE", "organisation_type": "HES"}
                for i, (s, l) in enumerate(specs)
            ]
        }

    def _make_section(self, criterion: str, content: str) -> dict:
        schema_map = {
            "Excellence": "orch.tier5.excellence_section.v1",
            "Impact": "orch.tier5.impact_section.v1",
            "Implementation": "orch.tier5.implementation_section.v1",
        }
        result = {
            "schema_id": schema_map[criterion],
            "run_id": "test-run",
            "criterion": criterion,
            "sub_sections": [{"sub_section_id": "B.1.1", "title": "Main", "content": content}],
        }
        if criterion == "Impact":
            result["impact_pathway_refs"] = []
            result["dec_coverage"] = {"dissemination_addressed": True,
                                      "exploitation_addressed": True,
                                      "communication_addressed": True}
        if criterion == "Implementation":
            result["wp_table_refs"] = ["WP1"]
            result["gantt_ref"] = "g.json"
            result["milestone_refs"] = ["MS1"]
            result["risk_register_ref"] = "r.json"
        return result

    def _make_assembled(self, consistency_log=None) -> dict:
        return {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1",
            "run_id": "test",
            "sections": [
                {"section_id": "excellence", "criterion": "Excellence", "order": 1, "artifact_path": "e.json"},
                {"section_id": "impact", "criterion": "Impact", "order": 2, "artifact_path": "i.json"},
                {"section_id": "implementation", "criterion": "Implementation", "order": 3, "artifact_path": "impl.json"},
            ],
            "consistency_log": consistency_log or [],
        }

    def _setup(self, tmp_path, *, exc="", imp_content="", impact="", objectives=None, partners=None):
        from runner.predicates.criterion_predicates import cross_section_consistency
        _write_json(tmp_path / "assembled.json", self._make_assembled())
        sec = tmp_path / "sections"
        if exc:
            _write_json(sec / "excellence_section.json", self._make_section("Excellence", exc))
        if impact:
            _write_json(sec / "impact_section.json", self._make_section("Impact", impact))
        if imp_content:
            _write_json(sec / "implementation_section.json", self._make_section("Implementation", imp_content))
        tier3 = tmp_path / "tier3"
        if objectives:
            _write_json(tier3 / "architecture_inputs" / "objectives.json", objectives)
        if partners:
            _write_json(tier3 / "consortium" / "partners.json", partners)
        return cross_section_consistency

    def test_missing_objective_in_excellence_fails(self, tmp_path: Path) -> None:
        """Missing objective ID in Excellence fails objective coverage."""
        objs = self._make_objectives(("OBJ-1", "Engine", "≥40%"), ("OBJ-2", "Memory", "≥30%"))
        fn = self._setup(tmp_path, exc="OBJ-1 plans.", impact="Impact.", imp_content="Impl.", objectives=objs)
        result = fn("assembled.json", "sections/", "tier3/", repo_root=tmp_path)
        assert not result.passed
        assert any("OBJ-2" in str(i.get("details", "")) for i in result.details.get("issues", []))

    def test_missing_metric_component_in_impact_fails(self, tmp_path: Path) -> None:
        """Missing metric component in Impact fails metric completeness."""
        objs = self._make_objectives(("OBJ-6", "Logistics demo", "≥20% recovery AND ≥15% adherence"))
        fn = self._setup(tmp_path, exc="OBJ-6 logistics.", impact="OBJ-6 achieves ≥20% recovery.",
                         imp_content="Impl.", objectives=objs)
        result = fn("assembled.json", "sections/", "tier3/", repo_root=tmp_path)
        assert not result.passed
        issues = [i for i in result.details.get("issues", []) if i.get("check") == "metric_completeness"]
        assert len(issues) >= 1
        assert "≥15%" in str(issues[0]["details"])

    def test_component_noun_substitution_fails_terminology(self, tmp_path: Path) -> None:
        """Component noun substitution fails canonical terminology check."""
        objs = self._make_objectives(("OBJ-8", "External Tool and API Orchestration Layer", "≥30 tools"))
        fn = self._setup(
            tmp_path,
            exc="OBJ-8 External Tool and API Orchestration Layer.",
            impact="The external tool and API orchestration capability provides OBJ-8.",
            imp_content="Impl.",
            objectives=objs,
        )
        result = fn("assembled.json", "sections/", "tier3/", repo_root=tmp_path)
        assert not result.passed
        issues = [i for i in result.details.get("issues", []) if i.get("check") == "terminology_consistency"]
        assert len(issues) >= 1

    def test_legal_name_truncation_fails_partner_naming(self, tmp_path: Path) -> None:
        """Legal-name truncation fails partner naming check."""
        partners = self._make_partners(("ELI", "EuroLog International AG"))
        fn = self._setup(
            tmp_path, exc="EuroLog International contributes.", impact="Impact.",
            imp_content="Impl.", partners=partners,
        )
        result = fn("assembled.json", "sections/", "tier3/", repo_root=tmp_path)
        assert not result.passed
        issues = [i for i in result.details.get("issues", []) if i.get("check") == "partner_naming"]
        assert len(issues) >= 1

    def test_deliverable_repurposed_as_kpi_fails(self, tmp_path: Path) -> None:
        """Deliverable ID repurposed as KPI/activity fails deliverable/KPI identity."""
        from runner.predicates.criterion_predicates import cross_section_consistency
        _write_json(tmp_path / "assembled.json", self._make_assembled())
        sec = tmp_path / "sections"
        _write_json(sec / "excellence_section.json", self._make_section("Excellence", "content"))
        _write_json(sec / "impact_section.json", self._make_section(
            "Impact", "CERIA submits formal standardisation proposal (D4-01) to ISO/IEC."))
        _write_json(sec / "implementation_section.json", self._make_section("Implementation", "content"))
        # Tier 4 artifacts
        _write_json(tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json",
                    {"kpis": [{"kpi_id": "KPI-08", "description": "Standardisation", "target": "≥1",
                               "traceable_to_deliverable": "D4-01"}]})
        _write_json(tmp_path / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
                    {"work_packages": [{"wp_id": "WP4", "deliverables": [
                        {"deliverable_id": "D4-01", "title": "Multi-agent coordination protocol specification", "due_month": 18}
                    ]}]})
        result = cross_section_consistency("assembled.json", "sections/", "tier3/", repo_root=tmp_path)
        assert not result.passed


# ===========================================================================
# 5. POSITIVE VALIDATOR TESTS
# ===========================================================================


class TestPositiveValidation:
    """Correct artifacts pass deterministic checks."""

    def test_all_objectives_present_passes(self, tmp_path: Path) -> None:
        from runner.predicates.criterion_predicates import cross_section_consistency
        objs = {"objectives": [
            {"id": "OBJ-1", "title": "Planning Engine", "measurable_target": "≥40%"},
            {"id": "OBJ-2", "title": "Memory Architecture", "measurable_target": "≥30%"},
        ]}
        _write_json(tmp_path / "assembled.json", {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1", "run_id": "t",
            "sections": [
                {"section_id": "excellence", "criterion": "Excellence", "order": 1, "artifact_path": "e.json"},
                {"section_id": "impact", "criterion": "Impact", "order": 2, "artifact_path": "i.json"},
                {"section_id": "implementation", "criterion": "Implementation", "order": 3, "artifact_path": "impl.json"},
            ], "consistency_log": []})
        sec = tmp_path / "sections"
        _write_json(sec / "excellence_section.json", {
            "schema_id": "orch.tier5.excellence_section.v1", "run_id": "t", "criterion": "Excellence",
            "sub_sections": [{"sub_section_id": "B.1.1", "title": "M", "content": "OBJ-1 Planning Engine ≥40%. OBJ-2 Memory Architecture ≥30%."}]})
        _write_json(sec / "impact_section.json", {
            "schema_id": "orch.tier5.impact_section.v1", "run_id": "t", "criterion": "Impact",
            "sub_sections": [{"sub_section_id": "B.2.1", "title": "M", "content": "OBJ-1 achieves ≥40%. OBJ-2 achieves ≥30%."}],
            "impact_pathway_refs": [], "dec_coverage": {"dissemination_addressed": True, "exploitation_addressed": True, "communication_addressed": True}})
        _write_json(sec / "implementation_section.json", {
            "schema_id": "orch.tier5.implementation_section.v1", "run_id": "t", "criterion": "Implementation",
            "sub_sections": [{"sub_section_id": "B.3.1", "title": "M", "content": "WP2 implements OBJ-1."}],
            "wp_table_refs": ["WP1"], "gantt_ref": "g.json", "milestone_refs": ["MS1"], "risk_register_ref": "r.json"})
        _write_json(tmp_path / "tier3/architecture_inputs/objectives.json", objs)
        result = cross_section_consistency("assembled.json", "sections/", "tier3/", repo_root=tmp_path)
        assert result.passed

    def test_full_legal_names_pass(self, tmp_path: Path) -> None:
        from runner.predicates.criterion_predicates import cross_section_consistency
        partners = {"partners": [{"partner_number": 1, "short_name": "ELI", "legal_name": "EuroLog International AG",
                                   "country": "CH", "organisation_type": "PRC"}]}
        _write_json(tmp_path / "assembled.json", {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1", "run_id": "t",
            "sections": [
                {"section_id": "excellence", "criterion": "Excellence", "order": 1, "artifact_path": "e.json"},
                {"section_id": "impact", "criterion": "Impact", "order": 2, "artifact_path": "i.json"},
                {"section_id": "implementation", "criterion": "Implementation", "order": 3, "artifact_path": "impl.json"},
            ], "consistency_log": []})
        sec = tmp_path / "sections"
        _write_json(sec / "excellence_section.json", {
            "schema_id": "orch.tier5.excellence_section.v1", "run_id": "t", "criterion": "Excellence",
            "sub_sections": [{"sub_section_id": "B.1.1", "title": "M", "content": "EuroLog International AG leads."}]})
        _write_json(sec / "impact_section.json", {
            "schema_id": "orch.tier5.impact_section.v1", "run_id": "t", "criterion": "Impact",
            "sub_sections": [{"sub_section_id": "B.2.1", "title": "M", "content": "EuroLog International AG validates."}],
            "impact_pathway_refs": [], "dec_coverage": {"dissemination_addressed": True, "exploitation_addressed": True, "communication_addressed": True}})
        _write_json(sec / "implementation_section.json", {
            "schema_id": "orch.tier5.implementation_section.v1", "run_id": "t", "criterion": "Implementation",
            "sub_sections": [{"sub_section_id": "B.3.1", "title": "M", "content": "EuroLog International AG participates."}],
            "wp_table_refs": ["WP1"], "gantt_ref": "g.json", "milestone_refs": ["MS1"], "risk_register_ref": "r.json"})
        _write_json(tmp_path / "tier3/consortium/partners.json", partners)
        result = cross_section_consistency("assembled.json", "sections/", "tier3/", repo_root=tmp_path)
        assert result.passed


# ===========================================================================
# 6. FINGERPRINT INVALIDATION TESTS
# ===========================================================================


class TestFingerprintInvalidation:
    """Spec changes invalidate the correct Phase 8 node fingerprints."""

    @pytest.fixture(autouse=True)
    def _setup_paths(self, tmp_path: Path) -> None:
        from runner.phase8_reuse import FINGERPRINT_INPUTS, compute_input_fingerprint
        self.repo = tmp_path
        self.compute = compute_input_fingerprint

        for node_id in ["n08a_excellence_drafting", "n08b_impact_drafting",
                        "n08c_implementation_drafting"]:
            for rel_path in FINGERPRINT_INPUTS[node_id]:
                if rel_path.endswith("/"):
                    (tmp_path / rel_path).mkdir(parents=True, exist_ok=True)
                    (tmp_path / rel_path / "data.json").write_text('{"v": 1}', encoding="utf-8")
                else:
                    p = tmp_path / rel_path
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("spec content placeholder", encoding="utf-8")

    def test_excellence_spec_change_invalidates_only_n08a(self) -> None:
        fp_a = self.compute("n08a_excellence_drafting", self.repo)
        fp_b = self.compute("n08b_impact_drafting", self.repo)
        fp_c = self.compute("n08c_implementation_drafting", self.repo)

        (self.repo / ".claude/skills/excellence-section-drafting.md").write_text("MUTATED", encoding="utf-8")

        assert self.compute("n08a_excellence_drafting", self.repo) != fp_a
        assert self.compute("n08b_impact_drafting", self.repo) == fp_b
        assert self.compute("n08c_implementation_drafting", self.repo) == fp_c

    def test_impact_spec_change_invalidates_only_n08b(self) -> None:
        fp_a = self.compute("n08a_excellence_drafting", self.repo)
        fp_b = self.compute("n08b_impact_drafting", self.repo)
        fp_c = self.compute("n08c_implementation_drafting", self.repo)

        (self.repo / ".claude/skills/impact-section-drafting.md").write_text("MUTATED", encoding="utf-8")

        assert self.compute("n08a_excellence_drafting", self.repo) == fp_a
        assert self.compute("n08b_impact_drafting", self.repo) != fp_b
        assert self.compute("n08c_implementation_drafting", self.repo) == fp_c

    def test_implementation_spec_change_invalidates_only_n08c(self) -> None:
        fp_a = self.compute("n08a_excellence_drafting", self.repo)
        fp_b = self.compute("n08b_impact_drafting", self.repo)
        fp_c = self.compute("n08c_implementation_drafting", self.repo)

        (self.repo / ".claude/skills/implementation-section-drafting.md").write_text("MUTATED", encoding="utf-8")

        assert self.compute("n08a_excellence_drafting", self.repo) == fp_a
        assert self.compute("n08b_impact_drafting", self.repo) == fp_b
        assert self.compute("n08c_implementation_drafting", self.repo) != fp_c

    def test_validator_code_change_does_not_invalidate_drafting(self) -> None:
        """Changes to runner/predicates/ do not force drafting reuse invalidation."""
        fp_a = self.compute("n08a_excellence_drafting", self.repo)
        fp_b = self.compute("n08b_impact_drafting", self.repo)
        fp_c = self.compute("n08c_implementation_drafting", self.repo)

        # Simulate a validator code change (not in fingerprint inputs)
        p = self.repo / "runner/predicates/criterion_predicates.py"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# modified validator", encoding="utf-8")

        assert self.compute("n08a_excellence_drafting", self.repo) == fp_a
        assert self.compute("n08b_impact_drafting", self.repo) == fp_b
        assert self.compute("n08c_implementation_drafting", self.repo) == fp_c
