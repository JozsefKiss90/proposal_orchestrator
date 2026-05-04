"""
Tests for the manifest.compile.yaml predicate_refs fix and strengthened
Phase 8 section predicates.

Covers:
  1. Gates 10a/10b/10c actually evaluate the new predicate IDs through
     manifest predicate_refs.
  2. gate_10a fails when a section claims all objectives but omits one
     objective ID/target.
  3. gate_10b fails when a multi-target measurable_target is partially
     dropped.
  4. gate_10a/10b/10c fail on canonical outcome/objective title variants.
  5. gate_10a fails on narrow/exclusive deliverable characterisation when
     canonical pack shows multiple linked outcomes.
  6. gate_10d remains unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.predicates.phase8_section_predicates import (
    canonical_terms_preserved,
    deliverable_identity_preserved,
    measurable_targets_preserved,
    partner_names_preserved,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_manifest() -> dict:
    """Load the production manifest.compile.yaml."""
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "manifest.compile.yaml"
    )
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def _load_gate_rules_library() -> dict:
    """Load the production gate_rules_library.yaml."""
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "gate_rules_library.yaml"
    )
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def _get_manifest_predicate_refs(manifest: dict, gate_id: str) -> list[str]:
    """Extract flat predicate_refs list for a gate from the manifest."""
    refs: list[str] = []
    for gate in manifest.get("gate_registry", []):
        if gate.get("gate_id") == gate_id:
            for cond in gate.get("conditions", []):
                if isinstance(cond, dict):
                    refs.extend(cond.get("predicate_refs", []))
            break
    return refs


def _find_predicate(library: dict, predicate_id: str) -> dict | None:
    """Find a predicate by ID across all gates in the library."""
    for gate in library.get("gate_rules", []):
        for pred in gate.get("predicates", []):
            if pred.get("predicate_id") == predicate_id:
                return pred
    return None


def _make_canonical_pack(
    *,
    objectives: list | None = None,
    outcomes: list | None = None,
    wps: list | None = None,
    deliverables: list | None = None,
    partners: list | None = None,
) -> dict:
    """Build a minimal canonical reference pack."""
    return {
        "schema_id": "orch.phase8.canonical_reference_pack.v1",
        "run_id": "test-run",
        "objectives": objectives or [],
        "outcomes": outcomes or [],
        "wps": wps or [],
        "deliverables": deliverables or [],
        "partners": partners or [],
        "aliases": [],
    }


def _make_section(
    name: str,
    sub_sections: list[dict] | None = None,
) -> dict:
    """Build a minimal section artifact."""
    return {
        "schema_id": f"orch.tier5.{name}.v1",
        "run_id": "test-run",
        "sub_sections": sub_sections or [],
        "traceability_footer": {"sources": []},
        "validation_status": {"overall_status": "confirmed"},
    }


# ===========================================================================
# 1. MANIFEST PREDICATE_REFS COMPLETENESS
# ===========================================================================


class TestManifestPredicateRefs:
    """Verify that gates 10a/10b/10c include the new predicate IDs."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.manifest = _load_manifest()
        self.library = _load_gate_rules_library()

    def test_gate_10a_includes_new_predicates(self) -> None:
        refs = _get_manifest_predicate_refs(
            self.manifest, "gate_10a_excellence_completeness"
        )
        for pid in ["g09a_p07", "g09a_p08", "g09a_p09", "g09a_p10"]:
            assert pid in refs, f"{pid} missing from gate_10a predicate_refs"

    def test_gate_10b_includes_new_predicates(self) -> None:
        refs = _get_manifest_predicate_refs(
            self.manifest, "gate_10b_impact_completeness"
        )
        for pid in ["g09b_p08", "g09b_p09", "g09b_p10", "g09b_p11"]:
            assert pid in refs, f"{pid} missing from gate_10b predicate_refs"

    def test_gate_10c_includes_new_predicates(self) -> None:
        refs = _get_manifest_predicate_refs(
            self.manifest, "gate_10c_implementation_completeness"
        )
        for pid in ["g09c_p08", "g09c_p09", "g09c_p10"]:
            assert pid in refs, f"{pid} missing from gate_10c predicate_refs"

    def test_new_predicates_resolvable_in_library(self) -> None:
        """Every new predicate ID in manifest must exist in the library."""
        new_ids = [
            "g09a_p07", "g09a_p08", "g09a_p09", "g09a_p10",
            "g09b_p08", "g09b_p09", "g09b_p10", "g09b_p11",
            "g09c_p08", "g09c_p09", "g09c_p10",
        ]
        for pid in new_ids:
            pred = _find_predicate(self.library, pid)
            assert pred is not None, (
                f"Predicate {pid} in manifest but not in gate_rules_library"
            )
            assert "function" in pred, f"{pid} missing 'function' field"
            assert "type" in pred, f"{pid} missing 'type' field"

    def test_gate_10d_unchanged(self) -> None:
        """gate_10d predicate_refs must only contain g09d_p01–p07."""
        refs = _get_manifest_predicate_refs(
            self.manifest, "gate_10d_cross_section_consistency"
        )
        expected = {
            "g09d_p01", "g09d_p02", "g09d_p03",
            "g09d_p04", "g09d_p05", "g09d_p06", "g09d_p07",
        }
        assert set(refs) == expected, (
            f"gate_10d predicate_refs changed: {refs}"
        )


# ===========================================================================
# 2. MEASURABLE_TARGETS_PRESERVED — "all objectives" claim
# ===========================================================================


class TestMeasurableTargetsAllObjectivesClaim:
    """gate_10a must fail when Excellence section claims all objectives
    but omits one objective ID or its measurable_target components."""

    def test_excellence_all_objectives_missing_one_id(
        self, tmp_path: Path,
    ) -> None:
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-1",
                    "title": "First objective title here",
                    "measurable_target": "Achieve ≥40% improvement",
                },
                {
                    "id": "OBJ-2",
                    "title": "Second objective title here",
                    "measurable_target": "Demonstrate ≥30% improvement",
                },
            ],
        )
        section = _make_section(
            "excellence_section",
            sub_sections=[{
                "content": (
                    "MAESTRO addresses all project objectives. "
                    "OBJ-1: First objective title here. "
                    "We achieve ≥40% improvement in plan success."
                    # OBJ-2 is omitted despite "all objectives" claim
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "excellence_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = measurable_targets_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert not result.passed
        # Should flag OBJ-2 missing
        issues = result.details.get("issues", [])
        claim_issues = [i for i in issues if i.get("check") == "all_objectives_claim"]
        assert len(claim_issues) >= 1
        assert "OBJ-2" in str(claim_issues)

    def test_excellence_all_objectives_target_partially_dropped(
        self, tmp_path: Path,
    ) -> None:
        """When Excellence claims all objectives and mentions OBJ-1,
        but drops one of two quantitative components."""
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-1",
                    "title": "First objective",
                    "measurable_target": (
                        "Achieve ≥40% improvement and ≥500 GitHub stars"
                    ),
                },
            ],
        )
        section = _make_section(
            "excellence_section",
            sub_sections=[{
                "content": (
                    "All objectives of the project are addressed. "
                    "OBJ-1: We achieve ≥40% improvement in planning."
                    # ≥500 is dropped
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "excellence_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = measurable_targets_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert not result.passed
        # Should flag the ≥500 component as missing
        comp_issues = [
            i for i in result.details.get("issues", [])
            if i.get("objective_id") == "OBJ-1"
        ]
        assert len(comp_issues) >= 1

    def test_implementation_lenient_on_all_objectives(
        self, tmp_path: Path,
    ) -> None:
        """Implementation section claiming 'all objectives' should NOT
        fail for missing objective IDs (lenient mode)."""
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-1",
                    "title": "First objective",
                    "measurable_target": "Achieve ≥40% improvement",
                },
                {
                    "id": "OBJ-2",
                    "title": "Second objective",
                    "measurable_target": "Demonstrate ≥30% improvement",
                },
            ],
        )
        section = _make_section(
            "implementation_section",
            sub_sections=[{
                "content": (
                    "The implementation addresses all objectives "
                    "through the work package structure."
                    # No OBJ IDs mentioned — implementation is lenient
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "implementation_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = measurable_targets_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert result.passed


# ===========================================================================
# 3. MEASURABLE_TARGETS_PRESERVED — multi-target partial drop (Impact)
# ===========================================================================


class TestMeasurableTargetsMultiClause:
    """gate_10b must fail when a multi-clause measurable_target is
    partially dropped."""

    def test_impact_multi_target_partial_drop(
        self, tmp_path: Path,
    ) -> None:
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-5",
                    "title": "Manufacturing demonstrator",
                    "measurable_target": (
                        "Demonstrate ≥15% reduction in defect rates and "
                        "≥10% reduction in energy consumption"
                    ),
                },
            ],
        )
        section = _make_section(
            "impact_section",
            sub_sections=[{
                "content": (
                    "OBJ-5 targets a ≥15% reduction in defect rates "
                    "at the pilot factory."
                    # ≥10% energy consumption is dropped
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "impact_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = measurable_targets_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        assert any(
            "≥10%" in str(i.get("missing_components", []))
            for i in issues
        )

    def test_impact_linked_outcome_triggers_check(
        self, tmp_path: Path,
    ) -> None:
        """If the Impact section mentions an outcome ID, objectives
        linked to that outcome must have their targets checked."""
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-3",
                    "title": "Decentralised multi-agent coordination",
                    "measurable_target": (
                        "Demonstrate coordination of ≥5 agents "
                        "with ≥25% improvement"
                    ),
                },
            ],
            outcomes=[
                {
                    "id": "OUT-3",
                    "title": "Formally verified coordination protocol",
                    "linked_objectives": ["OBJ-3"],
                    "linked_wp_ids": ["WP4"],
                    "linked_deliverable_ids": ["D4-01"],
                },
            ],
        )
        section = _make_section(
            "impact_section",
            sub_sections=[{
                "content": (
                    "OUT-3 — Formally verified coordination protocol suite — "
                    "delivers coordination capabilities."
                    # OBJ-3 not explicitly mentioned, but OUT-3 is,
                    # so OBJ-3's metrics should still be checked.
                    # Neither ≥5 nor ≥25% appear.
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "impact_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = measurable_targets_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        assert any(i.get("objective_id") == "OBJ-3" for i in issues)


# ===========================================================================
# 4. CANONICAL_TERMS_PRESERVED — outcome/objective title variants
# ===========================================================================


class TestCanonicalTermsOutcomeTitles:
    """gates 10a/10b/10c must fail when canonical outcome or objective
    titles are shortened or paraphrased."""

    def test_outcome_title_shortened(self, tmp_path: Path) -> None:
        pack = _make_canonical_pack(
            outcomes=[
                {
                    "id": "OUT-1",
                    "title": "Neuro-symbolic planning framework for LLM-based agents",
                    "linked_objectives": ["OBJ-1"],
                    "linked_wp_ids": ["WP2"],
                    "linked_deliverable_ids": ["D2-01"],
                },
            ],
        )
        section = _make_section(
            "excellence_section",
            sub_sections=[{
                "content": (
                    "OUT-1 delivers a planning framework."  # shortened
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "excellence_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = canonical_terms_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        assert any(
            i.get("term_type") == "outcome_title" and i.get("id") == "OUT-1"
            for i in issues
        )

    def test_objective_title_shortened(self, tmp_path: Path) -> None:
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-2",
                    "title": "Unified adaptive memory architecture",
                    "measurable_target": "≥30% improvement",
                },
            ],
        )
        section = _make_section(
            "impact_section",
            sub_sections=[{
                "content": (
                    "OBJ-2 creates a memory architecture."  # shortened
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "impact_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = canonical_terms_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        assert any(
            i.get("term_type") == "objective_title" and i.get("id") == "OBJ-2"
            for i in issues
        )

    def test_exact_titles_pass(self, tmp_path: Path) -> None:
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-2",
                    "title": "Unified adaptive memory architecture",
                    "measurable_target": "≥30% improvement",
                },
            ],
            outcomes=[
                {
                    "id": "OUT-1",
                    "title": "Neuro-symbolic planning framework for LLM-based agents",
                    "linked_objectives": ["OBJ-1"],
                    "linked_wp_ids": ["WP2"],
                    "linked_deliverable_ids": ["D2-01"],
                },
            ],
        )
        section = _make_section(
            "implementation_section",
            sub_sections=[{
                "content": (
                    "OBJ-2 — Unified adaptive memory architecture — "
                    "is delivered via WP3. "
                    "OUT-1 — Neuro-symbolic planning framework for "
                    "LLM-based agents — is the key output."
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "implementation_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = canonical_terms_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert result.passed


# ===========================================================================
# 5. DELIVERABLE_IDENTITY_PRESERVED — multi-outcome narrowing
# ===========================================================================


class TestDeliverableMultiOutcomeNarrowing:
    """gate_10a must fail when a multi-outcome deliverable is given an
    exclusive/narrow characterisation."""

    def test_exclusive_purpose_detected(self, tmp_path: Path) -> None:
        pack = _make_canonical_pack(
            deliverables=[
                {
                    "deliverable_id": "D8-01",
                    "title": "Evaluation framework and benchmark specification",
                    "due_month": 12,
                    "parent_wp": "WP8",
                },
            ],
            outcomes=[
                {
                    "id": "OUT-7",
                    "title": "MAESTRO evaluation benchmark suite",
                    "linked_objectives": ["OBJ-7"],
                    "linked_wp_ids": ["WP8"],
                    "linked_deliverable_ids": ["D8-01", "D8-02"],
                },
                {
                    "id": "OUT-8",
                    "title": "Open-source MAESTRO framework",
                    "linked_objectives": ["OBJ-7"],
                    "linked_wp_ids": ["WP8", "WP9"],
                    "linked_deliverable_ids": ["D8-01", "D8-02", "D9-02"],
                },
                {
                    "id": "OUT-9",
                    "title": "External tool orchestration layer",
                    "linked_objectives": ["OBJ-8"],
                    "linked_wp_ids": ["WP2", "WP8"],
                    "linked_deliverable_ids": ["D2-02", "D8-01"],
                },
            ],
        )
        section = _make_section(
            "excellence_section",
            sub_sections=[{
                "content": (
                    "WP8 produces D8-01 — Evaluation framework and "
                    "benchmark specification (month 12). "
                    "D8-01 is solely for the purpose of establishing "
                    "the evaluation benchmark."
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "excellence_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = deliverable_identity_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        narrowing_issues = [
            i for i in issues if i.get("check") == "multi_outcome_narrowing"
        ]
        assert len(narrowing_issues) >= 1
        assert narrowing_issues[0]["deliverable_id"] == "D8-01"
        # Should list all 3 linked outcomes
        assert len(narrowing_issues[0]["linked_outcome_ids"]) == 3

    def test_no_exclusive_purpose_passes(self, tmp_path: Path) -> None:
        """When multi-outcome deliverable is described neutrally, passes."""
        pack = _make_canonical_pack(
            deliverables=[
                {
                    "deliverable_id": "D8-01",
                    "title": "Evaluation framework and benchmark specification",
                    "due_month": 12,
                    "parent_wp": "WP8",
                },
            ],
            outcomes=[
                {
                    "id": "OUT-7",
                    "title": "MAESTRO evaluation benchmark suite",
                    "linked_objectives": ["OBJ-7"],
                    "linked_wp_ids": ["WP8"],
                    "linked_deliverable_ids": ["D8-01", "D8-02"],
                },
                {
                    "id": "OUT-8",
                    "title": "Open-source MAESTRO framework",
                    "linked_objectives": ["OBJ-7"],
                    "linked_wp_ids": ["WP8"],
                    "linked_deliverable_ids": ["D8-01", "D8-02"],
                },
            ],
        )
        section = _make_section(
            "excellence_section",
            sub_sections=[{
                "content": (
                    "WP8 produces D8-01 — Evaluation framework and "
                    "benchmark specification (month 12). "
                    "D8-01 supports multiple project outcomes."
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "excellence_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = deliverable_identity_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        # Should have no multi_outcome_narrowing issues
        narrowing_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "multi_outcome_narrowing"
        ]
        assert len(narrowing_issues) == 0


# ===========================================================================
# 6. PREDICATE FUNCTION ROUTING — library predicates match registry
# ===========================================================================


class TestPredicateFunctionRouting:
    """Verify that every new predicate's function name maps to a
    registered function in PREDICATE_REGISTRY."""

    def test_all_new_predicates_in_registry(self) -> None:
        from runner.gate_evaluator import PREDICATE_REGISTRY

        library = _load_gate_rules_library()
        new_ids = [
            "g09a_p07", "g09a_p08", "g09a_p09", "g09a_p10",
            "g09b_p08", "g09b_p09", "g09b_p10", "g09b_p11",
            "g09c_p08", "g09c_p09", "g09c_p10",
        ]
        for pid in new_ids:
            pred = _find_predicate(library, pid)
            assert pred is not None, f"Missing predicate {pid} in library"
            func_name = pred["function"]
            assert func_name in PREDICATE_REGISTRY, (
                f"Predicate {pid} function '{func_name}' not in "
                f"PREDICATE_REGISTRY"
            )


# ===========================================================================
# 7. MEASURABLE_TARGETS — happy path (all components present)
# ===========================================================================


class TestMeasurableTargetsHappyPath:
    """Verify that well-formed sections pass the predicate."""

    def test_all_components_present_passes(self, tmp_path: Path) -> None:
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-5",
                    "title": "Manufacturing demonstrator",
                    "measurable_target": (
                        "Demonstrate ≥15% reduction in defect rates and "
                        "≥10% reduction in energy consumption"
                    ),
                },
            ],
        )
        section = _make_section(
            "impact_section",
            sub_sections=[{
                "content": (
                    "OBJ-5 targets a ≥15% reduction in defect rates "
                    "and a ≥10% reduction in energy consumption."
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "impact_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = measurable_targets_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert result.passed

    def test_excellence_all_objectives_complete_passes(
        self, tmp_path: Path,
    ) -> None:
        """Excellence with 'all objectives' and all IDs/targets present."""
        pack = _make_canonical_pack(
            objectives=[
                {
                    "id": "OBJ-1",
                    "title": "First objective",
                    "measurable_target": "Achieve ≥40% improvement",
                },
                {
                    "id": "OBJ-2",
                    "title": "Second objective",
                    "measurable_target": "Demonstrate ≥30% improvement",
                },
            ],
        )
        section = _make_section(
            "excellence_section",
            sub_sections=[{
                "content": (
                    "MAESTRO addresses all project objectives. "
                    "OBJ-1: ≥40% improvement in planning. "
                    "OBJ-2: ≥30% improvement in coherence."
                ),
            }],
        )
        pack_path = tmp_path / "canonical_reference_pack.json"
        section_path = tmp_path / "excellence_section.json"
        _write_json(pack_path, pack)
        _write_json(section_path, section)

        result = measurable_targets_preserved(
            section_path=str(section_path),
            canonical_pack_path=str(pack_path),
            repo_root=tmp_path,
        )
        assert result.passed
