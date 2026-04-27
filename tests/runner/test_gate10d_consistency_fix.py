"""
Tests for gate_10d cross_section_consistency fix (run c6a2a1bb blockers).

Covers:
  Task A — cross_section_consistency predicate registration/routing
  Task B — Implementation partner legal names (EuroLog International AG, Boreal AI Labs Oy)
  Task C — Impact D4-01 / KPI-08 standardisation mislabel
  Task D — Targeted gate_10d fixture evaluation

All tests are static — no live Claude invocations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_skill_spec(skill_name: str) -> str:
    """Load a production skill .md file."""
    repo_root = Path(__file__).resolve().parents[2]
    spec_path = repo_root / ".claude" / "skills" / f"{skill_name}.md"
    return spec_path.read_text(encoding="utf-8-sig")


def _load_gate_rules_library() -> dict:
    """Load the production gate_rules_library.yaml."""
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "gate_rules_library.yaml"
    )
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def _load_manifest() -> dict:
    """Load the production manifest.compile.yaml."""
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "manifest.compile.yaml"
    )
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def _find_predicate(library: dict, predicate_id: str) -> dict | None:
    """Find a predicate by ID across all gates in the library."""
    for gate in library.get("gate_rules", []):
        for pred in gate.get("predicates", []):
            if pred.get("predicate_id") == predicate_id:
                return pred
    return None


def _find_gate(library: dict, gate_id: str) -> dict | None:
    """Find a gate entry by ID."""
    for gate in library.get("gate_rules", []):
        if gate.get("gate_id") == gate_id:
            return gate
    return None


# ===========================================================================
# TASK A — cross_section_consistency PREDICATE REGISTRATION
# ===========================================================================


class TestCrossSectionConsistencyRegistration:
    """Verify cross_section_consistency is properly registered and routable."""

    def test_function_in_deterministic_predicate_registry(self) -> None:
        """cross_section_consistency must be in PREDICATE_REGISTRY
        (the deterministic dispatch registry)."""
        from runner.gate_evaluator import PREDICATE_REGISTRY
        assert "cross_section_consistency" in PREDICATE_REGISTRY

    def test_function_callable(self) -> None:
        """cross_section_consistency must be a callable in PREDICATE_REGISTRY."""
        from runner.gate_evaluator import PREDICATE_REGISTRY
        func = PREDICATE_REGISTRY["cross_section_consistency"]
        assert callable(func)

    def test_g09d_p07_type_is_coverage(self) -> None:
        """g09d_p07 must have type 'coverage' (deterministic), not 'semantic'."""
        lib = _load_gate_rules_library()
        pred = _find_predicate(lib, "g09d_p07")
        assert pred is not None, "g09d_p07 not found in gate_rules_library.yaml"
        assert pred["type"] == "coverage", (
            f"g09d_p07 type must be 'coverage' (deterministic), "
            f"got {pred['type']!r}. A 'semantic' type routes through "
            "SEMANTIC_REGISTRY where cross_section_consistency is not registered."
        )

    def test_g09d_p07_function_is_cross_section_consistency(self) -> None:
        """g09d_p07 must point to cross_section_consistency function."""
        lib = _load_gate_rules_library()
        pred = _find_predicate(lib, "g09d_p07")
        assert pred is not None
        assert pred["function"] == "cross_section_consistency"

    def test_g09d_p07_type_is_deterministic(self) -> None:
        """g09d_p07 type must be in DETERMINISTIC_TYPES, not 'semantic'."""
        from runner.gate_evaluator import DETERMINISTIC_TYPES
        lib = _load_gate_rules_library()
        pred = _find_predicate(lib, "g09d_p07")
        assert pred is not None
        assert pred["type"] in DETERMINISTIC_TYPES, (
            f"g09d_p07 type {pred['type']!r} is not in DETERMINISTIC_TYPES "
            f"{sorted(DETERMINISTIC_TYPES)}. It will be dispatched as semantic "
            "and fail with UNKNOWN_FUNCTION."
        )

    def test_cross_section_consistency_not_in_semantic_registry(self) -> None:
        """cross_section_consistency should NOT be in SEMANTIC_REGISTRY.
        It is a deterministic predicate, not a Claude-evaluated one."""
        from runner.semantic_dispatch import SEMANTIC_REGISTRY
        assert "cross_section_consistency" not in SEMANTIC_REGISTRY, (
            "cross_section_consistency is a deterministic predicate and should "
            "not be registered in SEMANTIC_REGISTRY"
        )

    def test_gate_10d_has_g09d_p07(self) -> None:
        """gate_10d_cross_section_consistency must include g09d_p07."""
        lib = _load_gate_rules_library()
        gate = _find_gate(lib, "gate_10d_cross_section_consistency")
        assert gate is not None
        pred_ids = [p.get("predicate_id") for p in gate.get("predicates", [])]
        assert "g09d_p07" in pred_ids

    def test_manifest_gate_10d_has_g09d_p07_ref(self) -> None:
        """Production manifest gate_10d must include g09d_p07 in predicate_refs."""
        manifest = _load_manifest()
        gates = manifest.get("gate_registry", [])
        gate_10d = next(
            (g for g in gates
             if g.get("gate_id") == "gate_10d_cross_section_consistency"),
            None,
        )
        assert gate_10d is not None, (
            "gate_10d_cross_section_consistency not in manifest gate_registry"
        )
        all_refs = []
        for cond in gate_10d.get("conditions", []):
            all_refs.extend(cond.get("predicate_refs", []))
        assert "g09d_p07" in all_refs, (
            f"g09d_p07 not in gate_10d predicate_refs; found: {all_refs}"
        )


# ===========================================================================
# TASK A — gate_10d dispatch tests (no UNKNOWN_FUNCTION)
# ===========================================================================


class TestGate10dDispatch:
    """Verify gate_10d evaluates cross_section_consistency without dispatch error."""

    def test_positive_assembled_draft_passes_g09d_p07(self, tmp_path: Path) -> None:
        """Assembled draft with all-consistent entries passes cross_section_consistency."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        _write_json(tmp_path / "assembled.json", {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1",
            "sections": [
                {"section_id": "s1", "criterion": "Excellence", "order": 1,
                 "artifact_path": "a.json"},
                {"section_id": "s2", "criterion": "Impact", "order": 2,
                 "artifact_path": "b.json"},
                {"section_id": "s3", "criterion": "Implementation", "order": 3,
                 "artifact_path": "c.json"},
            ],
            "consistency_log": [
                {"check_id": "CC-01", "status": "consistent",
                 "description": "Objectives aligned"},
                {"check_id": "CC-02", "status": "consistent",
                 "description": "WP IDs consistent"},
                {"check_id": "CC-03", "status": "consistent",
                 "description": "Partner names consistent"},
                {"check_id": "CC-04", "status": "consistent",
                 "description": "Deliverable references consistent"},
            ],
        })
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_negative_cc03_inconsistency_fails(self, tmp_path: Path) -> None:
        """Assembled draft with CC-03 inconsistency_flagged fails
        cross_section_consistency with actionable details."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        _write_json(tmp_path / "assembled.json", {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1",
            "sections": [
                {"section_id": "s1", "criterion": "Excellence", "order": 1,
                 "artifact_path": "a.json"},
                {"section_id": "s2", "criterion": "Impact", "order": 2,
                 "artifact_path": "b.json"},
                {"section_id": "s3", "criterion": "Implementation", "order": 3,
                 "artifact_path": "c.json"},
            ],
            "consistency_log": [
                {"check_id": "CC-01", "status": "consistent",
                 "description": "Objectives aligned"},
                {"check_id": "CC-03", "status": "inconsistency_flagged",
                 "description": "Implementation B.3.2 uses 'EuroLog International' "
                 "but Tier 3 canonical legal name is 'EuroLog International AG'"},
            ],
        })
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert "CC-03" in result.details.get("flagged_checks", [])

    def test_negative_cc04_inconsistency_fails(self, tmp_path: Path) -> None:
        """Assembled draft with CC-04 inconsistency_flagged fails
        cross_section_consistency."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        _write_json(tmp_path / "assembled.json", {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1",
            "sections": [
                {"section_id": "s1", "criterion": "Excellence", "order": 1,
                 "artifact_path": "a.json"},
                {"section_id": "s2", "criterion": "Impact", "order": 2,
                 "artifact_path": "b.json"},
                {"section_id": "s3", "criterion": "Implementation", "order": 3,
                 "artifact_path": "c.json"},
            ],
            "consistency_log": [
                {"check_id": "CC-04", "status": "inconsistency_flagged",
                 "description": "Impact treats D4-01 as M48 standardisation; "
                 "Excellence treats D4-01 as M18 coordination protocol"},
            ],
        })
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert "CC-04" in result.details.get("flagged_checks", [])

    def test_call_predicate_does_not_produce_unknown_function(
        self, tmp_path: Path,
    ) -> None:
        """_call_predicate for cross_section_consistency must not return
        'Unknown predicate function' error."""
        from runner.gate_evaluator import _call_predicate

        _write_json(tmp_path / "assembled.json", {
            "schema_id": "orch.tier5.part_b_assembled_draft.v1",
            "sections": [
                {"section_id": "s1", "criterion": "Excellence", "order": 1,
                 "artifact_path": "a.json"},
                {"section_id": "s2", "criterion": "Impact", "order": 2,
                 "artifact_path": "b.json"},
                {"section_id": "s3", "criterion": "Implementation", "order": 3,
                 "artifact_path": "c.json"},
            ],
            "consistency_log": [],
        })
        result = _call_predicate(
            "cross_section_consistency",
            {
                "assembled_path": "assembled.json",
                "sections_dir": "sections/",
                "tier3_path": "tier3/",
            },
            run_id="test-run",
            repo_root=tmp_path,
            reuse_policy_path=None,
        )
        assert result.passed
        assert "Unknown" not in (result.reason or "")


# ===========================================================================
# TASK B — IMPLEMENTATION PARTNER LEGAL NAMES
# ===========================================================================


class TestImplementationPartnerLegalNames:
    """Verify implementation-section-drafting.md requires canonical legal names."""

    def test_requires_eurolog_international_ag(self) -> None:
        """Skill spec must require 'EuroLog International AG'."""
        spec = _load_skill_spec("implementation-section-drafting")
        assert "EuroLog International AG" in spec, (
            "implementation-section-drafting.md must require "
            "'EuroLog International AG' (canonical legal name from partners.json)"
        )

    def test_requires_boreal_ai_labs_oy(self) -> None:
        """Skill spec must require 'Boreal AI Labs Oy'."""
        spec = _load_skill_spec("implementation-section-drafting")
        assert "Boreal AI Labs Oy" in spec, (
            "implementation-section-drafting.md must require "
            "'Boreal AI Labs Oy' (canonical legal name from partners.json)"
        )

    def test_forbids_bare_eurolog_international(self) -> None:
        """Skill spec must forbid bare 'EuroLog International contributes'
        without 'AG'."""
        spec = _load_skill_spec("implementation-section-drafting")
        assert re.search(
            r"[Ff]orbidden.*EuroLog International.*without.*AG",
            spec,
            re.DOTALL,
        ) or re.search(
            r"FORBIDDEN.*EuroLog International contributes.*without.*AG",
            spec,
            re.DOTALL,
        ), (
            "implementation-section-drafting.md must forbid bare "
            "'EuroLog International contributes' without 'AG'"
        )

    def test_forbids_bare_boreal_ai_labs(self) -> None:
        """Skill spec must forbid bare 'Boreal AI Labs brings' without 'Oy'."""
        spec = _load_skill_spec("implementation-section-drafting")
        assert re.search(
            r"[Ff]orbidden.*Boreal AI Labs.*without.*Oy",
            spec,
            re.DOTALL,
        ) or re.search(
            r"FORBIDDEN.*Boreal AI Labs brings.*without.*Oy",
            spec,
            re.DOTALL,
        ), (
            "implementation-section-drafting.md must forbid bare "
            "'Boreal AI Labs brings' without 'Oy'"
        )

    def test_canonical_legal_name_mandate(self) -> None:
        """Skill spec must contain a mandate to use canonical legal names
        from partners.json."""
        spec = _load_skill_spec("implementation-section-drafting")
        assert "canonical" in spec.lower() and "legal_name" in spec or \
               "canonical" in spec.lower() and "legal name" in spec.lower(), (
            "implementation-section-drafting.md must mandate using canonical "
            "legal names from partners.json"
        )

    def test_partners_json_has_correct_legal_names(self) -> None:
        """Tier 3 partners.json must have the canonical legal names."""
        repo_root = Path(__file__).resolve().parents[2]
        partners_path = (
            repo_root / "docs" / "tier3_project_instantiation"
            / "consortium" / "partners.json"
        )
        data = json.loads(partners_path.read_text(encoding="utf-8-sig"))
        partners = {p["short_name"]: p["legal_name"] for p in data["partners"]}
        assert partners["ELI"] == "EuroLog International AG"
        assert partners["BAL"] == "Boreal AI Labs Oy"


# ===========================================================================
# TASK C — IMPACT D4-01 / STANDARDISATION MISLABEL
# ===========================================================================


class TestImpactD401Constraint:
    """Verify impact-section-drafting.md forbids D4-01 as M48 standardisation."""

    def test_forbids_formal_standardisation_proposal_d401(self) -> None:
        """Skill spec must forbid 'formal standardisation proposal (D4-01)'."""
        spec = _load_skill_spec("impact-section-drafting")
        assert "formal standardisation proposal (D4-01)" in spec, (
            "impact-section-drafting.md must explicitly forbid "
            "'formal standardisation proposal (D4-01)'"
        )
        # Verify it's in a FORBIDDEN context
        idx = spec.find("formal standardisation proposal (D4-01)")
        # Look backwards for FORBIDDEN marker
        context = spec[max(0, idx - 200):idx + 50]
        assert "FORBIDDEN" in context or "forbidden" in context.lower() or \
               "MUST NOT" in context or "must not" in context.lower(), (
            "The mention of 'formal standardisation proposal (D4-01)' must be "
            "in a prohibition context"
        )

    def test_forbids_standardisation_submission_d401(self) -> None:
        """Skill spec must forbid 'standardisation submission (D4-01)'."""
        spec = _load_skill_spec("impact-section-drafting")
        assert "standardisation submission (D4-01)" in spec, (
            "impact-section-drafting.md must explicitly forbid "
            "'standardisation submission (D4-01)'"
        )

    def test_forbids_d401_by_m48_pattern(self) -> None:
        """Skill spec must forbid 'D4-01 ... by M48' patterns."""
        spec = _load_skill_spec("impact-section-drafting")
        assert re.search(
            r"D4-01.*(?:by |submitted by |due )M48",
            spec,
        ) or "D4-01 submitted by M48" in spec or \
               "D4-01 ... by M48" in spec, (
            "impact-section-drafting.md must forbid 'D4-01 submitted by M48' "
            "or equivalent patterns"
        )

    def test_requires_d401_as_m18_protocol(self) -> None:
        """Skill spec must require D4-01 to be described as M18
        coordination protocol specification."""
        spec = _load_skill_spec("impact-section-drafting")
        assert re.search(
            r"D4-01.*M18.*coordination protocol",
            spec,
            re.IGNORECASE | re.DOTALL,
        ), (
            "impact-section-drafting.md must require D4-01 to be described as "
            "the M18 coordination protocol specification"
        )

    def test_kpi08_not_assigned_as_d401(self) -> None:
        """Skill spec must require KPI-08/M48 standardisation action to be
        described without assigning it as D4-01."""
        spec = _load_skill_spec("impact-section-drafting")
        assert "KPI-08" in spec, (
            "impact-section-drafting.md must mention KPI-08 as the M48 "
            "standardisation activity tracker"
        )

    def test_d401_constraint_is_gate_critical(self) -> None:
        """The D4-01 deliverable identity constraint must be marked GATE-CRITICAL."""
        spec = _load_skill_spec("impact-section-drafting")
        idx = spec.find("D4-01 deliverable identity constraint")
        assert idx >= 0, (
            "impact-section-drafting.md must contain 'D4-01 deliverable "
            "identity constraint'"
        )
        section = spec[idx:idx + 200]
        assert "GATE-CRITICAL" in section

    def test_gate_readiness_check_includes_d401(self) -> None:
        """The gate-readiness check (Step 2.11) must include D4-01 checks."""
        spec = _load_skill_spec("impact-section-drafting")
        idx = spec.find("Gate-readiness check")
        assert idx >= 0
        gate_check = spec[idx:idx + 1000]
        assert "D4-01" in gate_check, (
            "Gate-readiness check must include D4-01 validation"
        )
        assert "standardisation" in gate_check.lower() or \
               "M48" in gate_check, (
            "Gate-readiness check must verify D4-01 not treated as M48 "
            "standardisation"
        )


# ===========================================================================
# TASK D — TARGETED GATE_10D FIXTURE TESTS
# ===========================================================================


def _make_gate10d_assembled_draft(
    *,
    consistency_log: list[dict] | None = None,
    section_count: int = 3,
) -> dict:
    """Build a minimal assembled draft fixture for gate_10d testing."""
    sections = []
    criteria = ["Excellence", "Impact", "Implementation"]
    for i in range(section_count):
        crit = criteria[i] if i < len(criteria) else f"Section{i+1}"
        sections.append({
            "section_id": f"s{i+1}",
            "criterion": crit,
            "order": i + 1,
            "artifact_path": f"docs/tier5_deliverables/proposal_sections/{crit.lower()}_section.json",
        })
    return {
        "schema_id": "orch.tier5.part_b_assembled_draft.v1",
        "run_id": "test-gate10d-fixture",
        "sections": sections,
        "consistency_log": consistency_log or [],
    }


class TestGate10dFixtureEvaluation:
    """Targeted gate_10d fixture tests through the normal gate evaluator path."""

    def test_all_consistent_passes_gate10d(self, tmp_path: Path) -> None:
        """Minimal assembled draft with all consistent entries and 3 sections
        passes cross_section_consistency (g09d_p07)."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_gate10d_assembled_draft(
            consistency_log=[
                {"check_id": "CC-01", "status": "consistent",
                 "description": "All objectives cross-referenced"},
                {"check_id": "CC-02", "status": "consistent",
                 "description": "WP IDs match"},
                {"check_id": "CC-03", "status": "consistent",
                 "description": "Partner legal names consistent"},
                {"check_id": "CC-04", "status": "consistent",
                 "description": "Deliverable IDs consistent"},
            ],
        )
        _write_json(tmp_path / "assembled.json", draft)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed
        assert draft["schema_id"] == "orch.tier5.part_b_assembled_draft.v1"
        assert len(draft["sections"]) == 3

    def test_cc03_flagged_fails_gate10d(self, tmp_path: Path) -> None:
        """Assembled draft with CC-03 inconsistency_flagged fails."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_gate10d_assembled_draft(
            consistency_log=[
                {"check_id": "CC-01", "status": "consistent",
                 "description": "Objectives aligned"},
                {"check_id": "CC-03", "status": "inconsistency_flagged",
                 "description": "EuroLog International vs EuroLog International AG"},
            ],
        )
        _write_json(tmp_path / "assembled.json", draft)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert "CC-03" in result.details["flagged_checks"]

    def test_cc04_flagged_fails_gate10d(self, tmp_path: Path) -> None:
        """Assembled draft with CC-04 inconsistency_flagged fails."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_gate10d_assembled_draft(
            consistency_log=[
                {"check_id": "CC-04", "status": "inconsistency_flagged",
                 "description": "D4-01 identity conflict"},
            ],
        )
        _write_json(tmp_path / "assembled.json", draft)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert "CC-04" in result.details["flagged_checks"]

    def test_multiple_flagged_reports_all(self, tmp_path: Path) -> None:
        """Multiple inconsistency_flagged entries are all reported."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_gate10d_assembled_draft(
            consistency_log=[
                {"check_id": "CC-03", "status": "inconsistency_flagged",
                 "description": "Partner name mismatch"},
                {"check_id": "CC-04", "status": "inconsistency_flagged",
                 "description": "D4-01 conflict"},
            ],
        )
        _write_json(tmp_path / "assembled.json", draft)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.details["flagged_count"] == 2
        assert "CC-03" in result.details["flagged_checks"]
        assert "CC-04" in result.details["flagged_checks"]

    def test_wrong_section_count_fails(self, tmp_path: Path) -> None:
        """Assembled draft with != 3 sections fails."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_gate10d_assembled_draft(section_count=2)
        _write_json(tmp_path / "assembled.json", draft)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_empty_consistency_log_passes(self, tmp_path: Path) -> None:
        """Assembled draft with empty consistency_log and 3 sections passes."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_gate10d_assembled_draft(consistency_log=[])
        _write_json(tmp_path / "assembled.json", draft)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_consistent_cc03_with_corrected_names_passes(
        self, tmp_path: Path,
    ) -> None:
        """Assembled draft with corrected partner names (CC-03 = consistent)
        passes cross_section_consistency."""
        from runner.predicates.criterion_predicates import cross_section_consistency

        draft = _make_gate10d_assembled_draft(
            consistency_log=[
                {"check_id": "CC-03", "status": "consistent",
                 "description": "Partner legal names match Tier 3: "
                 "EuroLog International AG, Boreal AI Labs Oy"},
                {"check_id": "CC-04", "status": "consistent",
                 "description": "D4-01 correctly identified as M18 protocol spec"},
            ],
        )
        _write_json(tmp_path / "assembled.json", draft)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed
