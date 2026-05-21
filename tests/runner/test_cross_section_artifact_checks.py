"""
Deterministic artifact-based tests for cross-section consistency enforcement.

Tests the enhanced cross_section_consistency predicate which performs
artifact-driven validation beyond the consistency_log check.

Test Groups:
    A. Objective Consistency — All objectives appear in Excellence, all
       referenced objectives match canonical IDs
    B. Partner Naming — No mixed naming forms without mapping
    C. Deliverable/KPI Alignment — KPIs do not masquerade as deliverables
    D. Metric Completeness — All numeric targets preserved
    E. Terminology Consistency — Canonical naming enforced

All tests are static — no live Claude invocations.
All tests use fixture data — fully project-agnostic test logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _make_assembled_draft(
    *,
    consistency_log: list[dict] | None = None,
    section_count: int = 3,
) -> dict:
    """Build a minimal assembled draft fixture that passes Layer 1 checks."""
    sections = []
    criteria = ["Excellence", "Impact", "Implementation"]
    for i in range(section_count):
        crit = criteria[i] if i < len(criteria) else f"Section{i+1}"
        sections.append({
            "section_id": f"s{i+1}",
            "criterion": crit,
            "order": i + 1,
            "artifact_path": f"sections/{crit.lower()}_section.json",
        })
    return {
        "schema_id": "orch.tier5.part_b_assembled_draft.v1",
        "run_id": "test-artifact-checks",
        "sections": sections,
        "consistency_log": consistency_log or [],
    }


def _make_section(
    *,
    criterion: str = "Excellence",
    content: str = "",
    sub_sections: list[dict] | None = None,
) -> dict:
    """Build a minimal section artifact."""
    schema_map = {
        "Excellence": "orch.tier5.excellence_section.v1",
        "Impact": "orch.tier5.impact_section.v1",
        "Implementation": "orch.tier5.implementation_section.v1",
    }
    result = {
        "schema_id": schema_map.get(criterion, "orch.tier5.section.v1"),
        "run_id": "test-run",
        "criterion": criterion,
        "sub_sections": sub_sections or [
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


def _make_objectives(*obj_specs: tuple[str, str, str]) -> dict:
    """Create objectives.json with (id, title, measurable_target) tuples."""
    return {
        "objectives": [
            {
                "id": oid,
                "title": title,
                "measurable_target": target,
                "target_month": 36,
                "responsible_partner": "ATU",
            }
            for oid, title, target in obj_specs
        ],
    }


def _make_partners(*partner_specs: tuple[str, str]) -> dict:
    """Create partners.json with (short_name, legal_name) tuples."""
    return {
        "partners": [
            {
                "partner_number": i + 1,
                "short_name": short,
                "legal_name": legal,
                "country": "DE",
                "organisation_type": "HES",
            }
            for i, (short, legal) in enumerate(partner_specs)
        ],
    }


def _setup_repo(
    tmp_path: Path,
    *,
    assembled: dict | None = None,
    excellence_content: str = "",
    impact_content: str = "",
    implementation_content: str = "",
    objectives: dict | None = None,
    partners: dict | None = None,
    impact_architecture: dict | None = None,
    wp_structure: dict | None = None,
) -> Path:
    """Set up a minimal repo structure for cross_section_consistency tests."""
    sections_dir = tmp_path / "sections"
    tier3_dir = tmp_path / "tier3"

    # Write assembled draft
    if assembled is None:
        assembled = _make_assembled_draft()
    _write_json(tmp_path / "assembled.json", assembled)

    # Write section files
    if excellence_content:
        _write_json(
            sections_dir / "excellence_section.json",
            _make_section(criterion="Excellence", content=excellence_content),
        )
    if impact_content:
        _write_json(
            sections_dir / "impact_section.json",
            _make_section(criterion="Impact", content=impact_content),
        )
    if implementation_content:
        _write_json(
            sections_dir / "implementation_section.json",
            _make_section(
                criterion="Implementation", content=implementation_content,
            ),
        )

    # Write Tier 3 artifacts
    if objectives is not None:
        _write_json(
            tier3_dir / "architecture_inputs" / "objectives.json",
            objectives,
        )
    if partners is not None:
        _write_json(tier3_dir / "consortium" / "partners.json", partners)

    # Write Tier 4 artifacts (reachable via repo_root)
    if impact_architecture is not None:
        _write_json(
            tmp_path
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase5_impact_architecture"
            / "impact_architecture.json",
            impact_architecture,
        )
    if wp_structure is not None:
        _write_json(
            tmp_path
            / "docs"
            / "tier4_orchestration_state"
            / "phase_outputs"
            / "phase3_wp_design"
            / "wp_structure.json",
            wp_structure,
        )

    return tmp_path


# ===========================================================================
# TEST GROUP A — OBJECTIVE CONSISTENCY
# ===========================================================================


class TestObjectiveConsistency:
    """Verify all objectives appear in Excellence and referenced IDs match."""

    def test_all_objectives_present_passes(self, tmp_path: Path) -> None:
        """When all Tier 3 objectives are mentioned in Excellence, passes."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Planning engine", "≥40% improvement"),
            ("OBJ-2", "Memory system", "≥30% improvement"),
            ("OBJ-3", "Coordination protocol", "≥25% improvement"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-1 plans. OBJ-2 memory. OBJ-3 coordinates.",
            impact_content=(
                "Impact of OBJ-1 with ≥40% gain and OBJ-2 with ≥30% gain."
            ),
            implementation_content="WP2 implements OBJ-1.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_missing_objective_in_excellence_fails(
        self, tmp_path: Path,
    ) -> None:
        """When Excellence omits an objective from Tier 3, fails."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Planning engine", "≥40%"),
            ("OBJ-2", "Memory system", "≥30%"),
            ("OBJ-7", "Open framework release", "≥500 stars"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-1 plans. OBJ-2 memory.",  # Missing OBJ-7
            impact_content="Impact section.",
            implementation_content="Implementation.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        assert any(
            "OBJ-7" in str(issue.get("details", ""))
            for issue in result.details.get("issues", [])
        )

    def test_unknown_objective_id_in_section_fails(
        self, tmp_path: Path,
    ) -> None:
        """When a section references an objective ID not in Tier 3, fails."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Planning engine", "≥40%"),
            ("OBJ-2", "Memory system", "≥30%"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-1 and OBJ-2 are defined.",
            impact_content="OBJ-1 and OBJ-99 have impact.",  # OBJ-99 unknown
            implementation_content="Implementation.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert any(
            "OBJ-99" in str(issue.get("details", ""))
            for issue in result.details.get("issues", [])
        )

    def test_all_objectives_exact_count_passes(self, tmp_path: Path) -> None:
        """When exactly N objectives from Tier 3 appear in Excellence, passes."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Engine", ""),
            ("OBJ-2", "Memory", ""),
            ("OBJ-3", "Protocol", ""),
            ("OBJ-4", "Demo A", ""),
            ("OBJ-5", "Demo B", ""),
            ("OBJ-6", "Demo C", ""),
            ("OBJ-7", "Release", ""),
            ("OBJ-8", "Layer", ""),
        )
        _setup_repo(
            tmp_path,
            excellence_content=(
                "OBJ-1 OBJ-2 OBJ-3 OBJ-4 OBJ-5 OBJ-6 OBJ-7 OBJ-8"
            ),
            impact_content="Impact.",
            implementation_content="Implementation.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_missing_one_of_eight_objectives_fails(
        self, tmp_path: Path,
    ) -> None:
        """When 7 of 8 objectives appear (one missing), fails."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Engine", ""),
            ("OBJ-2", "Memory", ""),
            ("OBJ-3", "Protocol", ""),
            ("OBJ-4", "Demo A", ""),
            ("OBJ-5", "Demo B", ""),
            ("OBJ-6", "Demo C", ""),
            ("OBJ-7", "Release", ""),
            ("OBJ-8", "Layer", ""),
        )
        _setup_repo(
            tmp_path,
            # OBJ-7 missing from Excellence
            excellence_content=(
                "OBJ-1 OBJ-2 OBJ-3 OBJ-4 OBJ-5 OBJ-6 OBJ-8"
            ),
            impact_content="Impact.",
            implementation_content="Implementation.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert any(
            "OBJ-7" in str(issue.get("details", ""))
            for issue in result.details.get("issues", [])
        )


# ===========================================================================
# TEST GROUP B — PARTNER NAMING
# ===========================================================================


class TestPartnerNaming:
    """Verify partner legal names are not truncated."""

    def test_full_legal_names_passes(self, tmp_path: Path) -> None:
        """When full legal names (with suffix) are used, passes."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        partners = _make_partners(
            ("ELI", "EuroLog International AG"),
            ("BAL", "Boreal AI Labs Oy"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="EuroLog International AG contributes.",
            impact_content="Boreal AI Labs Oy leads.",
            implementation_content=(
                "EuroLog International AG and Boreal AI Labs Oy participate."
            ),
            partners=partners,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_truncated_legal_name_fails(self, tmp_path: Path) -> None:
        """When 'EuroLog International' appears without 'AG', fails."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        partners = _make_partners(
            ("ELI", "EuroLog International AG"),
            ("BAL", "Boreal AI Labs Oy"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="EuroLog International AG contributes.",
            impact_content="Boreal AI Labs Oy leads.",
            # Implementation uses truncated name
            implementation_content="EuroLog International contributes logistics.",
            partners=partners,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        assert result.failure_category == "CROSS_ARTIFACT_INCONSISTENCY"
        issues = result.details.get("issues", [])
        partner_issues = [
            i for i in issues if i.get("check") == "partner_naming"
        ]
        assert len(partner_issues) >= 1
        assert "EuroLog International" in str(partner_issues[0]["details"])

    def test_truncated_oy_suffix_fails(self, tmp_path: Path) -> None:
        """When 'Boreal AI Labs' appears without 'Oy', fails."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        partners = _make_partners(
            ("BAL", "Boreal AI Labs Oy"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="Boreal AI Labs leads WP9.",  # Missing "Oy"
            impact_content="Impact.",
            implementation_content="Implementation.",
            partners=partners,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        partner_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "partner_naming"
        ]
        assert len(partner_issues) >= 1
        assert "Oy" in str(partner_issues[0]["details"])

    def test_short_name_only_passes(self, tmp_path: Path) -> None:
        """When only short_name (abbreviation) is used, no false positive."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        partners = _make_partners(
            ("ELI", "EuroLog International AG"),
        )
        _setup_repo(
            tmp_path,
            # Only uses short name "ELI", not the prefix "EuroLog International"
            excellence_content="ELI leads the logistics demonstrator.",
            impact_content="ELI validates cross-sector transfer.",
            implementation_content="ELI (WP7 lead) coordinates.",
            partners=partners,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_partner_without_known_suffix_skipped(
        self, tmp_path: Path,
    ) -> None:
        """Partners without known legal suffixes are not checked for truncation."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        partners = _make_partners(
            ("ATU", "Alpenstadt Technical University"),  # No legal suffix
        )
        _setup_repo(
            tmp_path,
            # Uses "Alpenstadt Technical" (truncated) but suffix is not
            # in _LEGAL_SUFFIXES so no false positive
            excellence_content="Alpenstadt Technical leads the project.",
            impact_content="Impact.",
            implementation_content="Implementation.",
            partners=partners,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_multiple_truncations_all_reported(self, tmp_path: Path) -> None:
        """Multiple truncated names are all reported in issues."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        partners = _make_partners(
            ("ELI", "EuroLog International AG"),
            ("BAL", "Boreal AI Labs Oy"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="EuroLog International and Boreal AI Labs.",
            impact_content="Impact.",
            implementation_content="Implementation.",
            partners=partners,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        partner_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "partner_naming"
        ]
        assert len(partner_issues) >= 2


# ===========================================================================
# TEST GROUP C — DELIVERABLE/KPI ALIGNMENT
# ===========================================================================


class TestDeliverableKpiAlignment:
    """Verify KPIs do not masquerade as deliverables."""

    def test_correct_deliverable_titles_passes(self, tmp_path: Path) -> None:
        """When Impact references deliverable by correct canonical title, passes."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        wp_structure = {
            "work_packages": [
                {
                    "wp_id": "WP4",
                    "deliverables": [
                        {
                            "deliverable_id": "D4-01",
                            "title": "Multi-agent coordination protocol specification",
                            "due_month": 18,
                        },
                    ],
                },
            ],
        }
        impact_arch = {
            "kpis": [
                {
                    "kpi_id": "KPI-08",
                    "description": "Standardisation submission",
                    "target": "≥1 submission to ISO/IEC",
                    "traceable_to_deliverable": "D4-01",
                },
            ],
        }
        _setup_repo(
            tmp_path,
            excellence_content="Excellence.",
            impact_content=(
                "D4-01 multi-agent coordination protocol specification "
                "enables standardisation tracked as KPI-08."
            ),
            implementation_content="Implementation.",
            wp_structure=wp_structure,
            impact_architecture=impact_arch,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_deliverable_missing_canonical_title_fails(
        self, tmp_path: Path,
    ) -> None:
        """When Impact references deliverable ID but canonical title is absent,
        flags potential KPI conflation."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        wp_structure = {
            "work_packages": [
                {
                    "wp_id": "WP4",
                    "deliverables": [
                        {
                            "deliverable_id": "D4-01",
                            "title": "Multi-agent coordination protocol specification",
                            "due_month": 18,
                        },
                    ],
                },
            ],
        }
        impact_arch = {
            "kpis": [
                {
                    "kpi_id": "KPI-08",
                    "description": "Standardisation submission",
                    "target": "≥1 submission to ISO/IEC",
                    "traceable_to_deliverable": "D4-01",
                },
            ],
        }
        _setup_repo(
            tmp_path,
            excellence_content="Excellence.",
            # Impact uses D4-01 but describes it as standardisation
            # (KPI-08 purpose), not by its canonical title
            impact_content=(
                "CERIA submits formal standardisation proposal (D4-01) "
                "to ISO/IEC JTC 1/SC 42 by M48."
            ),
            implementation_content="Implementation.",
            wp_structure=wp_structure,
            impact_architecture=impact_arch,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        kpi_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "deliverable_kpi_alignment"
        ]
        assert len(kpi_issues) >= 1
        assert "D4-01" in str(kpi_issues[0]["details"])

    def test_no_kpis_or_deliverables_passes(self, tmp_path: Path) -> None:
        """When no KPIs or deliverables data is available, skips gracefully."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        _setup_repo(
            tmp_path,
            excellence_content="Excellence content.",
            impact_content="Impact content.",
            implementation_content="Implementation content.",
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed


# ===========================================================================
# TEST GROUP D — METRIC COMPLETENESS
# ===========================================================================


class TestMetricCompleteness:
    """Verify all numeric targets from objectives are preserved."""

    def test_all_metrics_present_passes(self, tmp_path: Path) -> None:
        """When all percentage targets appear in Impact, passes."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-6", "Logistics demo", "≥20% recovery AND ≥15% adherence"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-6 logistics.",
            impact_content=(
                "OBJ-6 targets ≥20% improvement in disruption recovery "
                "and ≥15% improvement in delivery schedule adherence."
            ),
            implementation_content="Implementation.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_partial_metric_loss_fails(self, tmp_path: Path) -> None:
        """When one of two percentage targets is missing from Impact, fails."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-6", "Logistics demo", "≥20% recovery AND ≥15% adherence"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-6 logistics.",
            # Impact only mentions ≥20%, omits ≥15%
            impact_content=(
                "OBJ-6 achieves ≥20% improvement in disruption recovery."
            ),
            implementation_content="Implementation.",
            objectives=objectives,
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
        assert "≥15%" in str(metric_issues[0]["details"])

    def test_metric_without_qualifier_still_matches(
        self, tmp_path: Path,
    ) -> None:
        """A metric like '≥40%' passes if '40%' appears (bare form)."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Engine", "≥40% improvement in plan success"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-1 engine.",
            impact_content="OBJ-1 achieves 40% plan success improvement.",
            implementation_content="Implementation.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_objective_not_in_impact_skipped(self, tmp_path: Path) -> None:
        """Objectives not mentioned in Impact are not checked for metrics."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Engine", "≥40% improvement"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-1 engine.",
            # Impact does NOT mention OBJ-1 at all — metric check skipped
            impact_content="General impact narrative without objective refs.",
            implementation_content="Implementation.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_multiple_missing_metrics_all_reported(
        self, tmp_path: Path,
    ) -> None:
        """Multiple missing metrics are all reported."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-5", "Manufacturing", "≥15% defect AND ≥10% energy"),
            ("OBJ-6", "Logistics", "≥20% recovery AND ≥15% adherence"),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-5 manufacturing. OBJ-6 logistics.",
            # Impact mentions objectives but omits some metrics
            impact_content="OBJ-5 reduces defects. OBJ-6 improves recovery.",
            implementation_content="Implementation.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        metric_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "metric_completeness"
        ]
        # Should flag ≥15%, ≥10%, ≥20%, ≥15% (4 missing metrics)
        assert len(metric_issues) >= 4


# ===========================================================================
# TEST GROUP E — TERMINOLOGY CONSISTENCY
# ===========================================================================


class TestTerminologyConsistency:
    """Verify canonical component names are used consistently."""

    def test_consistent_terminology_passes(self, tmp_path: Path) -> None:
        """When canonical component name is used in all sections, passes."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-8", "External Tool and API Orchestration Layer", "≥30 tools"),
        )
        _setup_repo(
            tmp_path,
            excellence_content=(
                "OBJ-8 — External Tool and API Orchestration Layer provides."
            ),
            impact_content=(
                "The External Tool and API Orchestration Layer enables OBJ-8."
            ),
            implementation_content=(
                "External Tool and API Orchestration Layer is in WP2."
            ),
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_terminology_drift_detected(self, tmp_path: Path) -> None:
        """When a section uses variant wording instead of canonical name, fails."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-8", "External Tool and API Orchestration Layer", "≥30 tools"),
        )
        _setup_repo(
            tmp_path,
            excellence_content=(
                "OBJ-8 — External Tool and API Orchestration Layer provides."
            ),
            # Impact uses "capability" instead of "Layer"
            impact_content=(
                "The external tool and API orchestration capability enables "
                "broad integration of OBJ-8 targets."
            ),
            implementation_content=(
                "External Tool and API Orchestration Layer is in WP2."
            ),
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        term_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "terminology_consistency"
        ]
        assert len(term_issues) >= 1
        assert "impact" in str(term_issues[0].get("section", ""))

    def test_non_component_titles_not_checked(self, tmp_path: Path) -> None:
        """Objectives without component keywords in title are not checked."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            # Title doesn't contain engine/layer/architecture/etc.
            ("OBJ-4", "Healthcare demonstrator validation", ""),
        )
        _setup_repo(
            tmp_path,
            excellence_content="OBJ-4 healthcare demo validates clinicians.",
            impact_content="OBJ-4 shows clinical decision support potential.",
            implementation_content="OBJ-4 is in WP5.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_component_name_case_sensitivity(self, tmp_path: Path) -> None:
        """Canonical name must appear with exact casing (not lowercased)."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Neuro-symbolic Planning Engine", "≥40%"),
        )
        _setup_repo(
            tmp_path,
            # Excellence uses the exact canonical name
            excellence_content=(
                "OBJ-1 Neuro-symbolic Planning Engine decomposes goals."
            ),
            # Impact uses stem with different ending
            impact_content=(
                "The neuro-symbolic planning capability of OBJ-1."
            ),
            implementation_content="WP2 implements OBJ-1.",
            objectives=objectives,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        term_issues = [
            i for i in result.details.get("issues", [])
            if i.get("check") == "terminology_consistency"
        ]
        assert len(term_issues) >= 1


# ===========================================================================
# INTEGRATION TESTS — COMBINED CHECKS
# ===========================================================================


class TestCombinedArtifactChecks:
    """Integration tests verifying multiple check dimensions simultaneously."""

    def test_fully_consistent_repo_passes(self, tmp_path: Path) -> None:
        """A fully consistent set of artifacts passes all checks."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Neuro-symbolic Planning Engine", "≥40% improvement"),
            ("OBJ-2", "Adaptive Memory Architecture", "≥30% coherence"),
            ("OBJ-3", "Multi-agent Coordination Protocol", "≥25% joint task"),
        )
        partners = _make_partners(
            ("ATU", "Alpenstadt Technical University"),
            ("ELI", "EuroLog International AG"),
            ("BAL", "Boreal AI Labs Oy"),
        )
        _setup_repo(
            tmp_path,
            excellence_content=(
                "OBJ-1 Neuro-symbolic Planning Engine targets ≥40%. "
                "OBJ-2 Adaptive Memory Architecture targets ≥30%. "
                "OBJ-3 Multi-agent Coordination Protocol targets ≥25%. "
                "EuroLog International AG leads logistics. "
                "Boreal AI Labs Oy manages exploitation."
            ),
            impact_content=(
                "OBJ-1 Neuro-symbolic Planning Engine achieves ≥40%. "
                "OBJ-2 Adaptive Memory Architecture achieves ≥30%. "
                "OBJ-3 Multi-agent Coordination Protocol achieves ≥25%. "
                "EuroLog International AG validates. "
                "Boreal AI Labs Oy disseminates."
            ),
            implementation_content=(
                "WP2 Neuro-symbolic Planning Engine (OBJ-1). "
                "WP3 Adaptive Memory Architecture (OBJ-2). "
                "WP4 Multi-agent Coordination Protocol (OBJ-3). "
                "EuroLog International AG and Boreal AI Labs Oy deliver."
            ),
            objectives=objectives,
            partners=partners,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed

    def test_multiple_issues_all_aggregated(self, tmp_path: Path) -> None:
        """Multiple types of issues are all aggregated in result."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        objectives = _make_objectives(
            ("OBJ-1", "Planning Engine", "≥40% success"),
            ("OBJ-7", "Open framework release", "≥500 stars"),
        )
        partners = _make_partners(
            ("ELI", "EuroLog International AG"),
        )
        _setup_repo(
            tmp_path,
            # Missing OBJ-7 in Excellence + truncated partner name
            excellence_content="OBJ-1 Planning Engine. EuroLog International.",
            impact_content="OBJ-1 targets met.",
            implementation_content="Implementation.",
            objectives=objectives,
            partners=partners,
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        issues = result.details.get("issues", [])
        check_types = {i.get("check") for i in issues}
        # Should have both objective_coverage and partner_naming issues
        assert "objective_coverage" in check_types
        assert "partner_naming" in check_types

    def test_consistency_log_failure_takes_precedence(
        self, tmp_path: Path,
    ) -> None:
        """Consistency log failures are checked before artifact-level checks."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        assembled = _make_assembled_draft(
            consistency_log=[
                {
                    "check_id": "CC-01",
                    "status": "inconsistency_flagged",
                    "description": "Objective mismatch",
                },
            ],
        )
        _setup_repo(
            tmp_path,
            assembled=assembled,
            excellence_content="Content.",
            impact_content="Content.",
            implementation_content="Content.",
        )
        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert not result.passed
        # Should report the consistency_log failure, not artifact checks
        assert "flagged_checks" in result.details
        assert "CC-01" in result.details["flagged_checks"]

    def test_no_section_files_skips_artifact_checks(
        self, tmp_path: Path,
    ) -> None:
        """When section files don't exist, artifact checks are skipped."""
        from runner.predicates.criterion_predicates import (
            cross_section_consistency,
        )

        _write_json(tmp_path / "assembled.json", _make_assembled_draft())
        # Don't write any section files or Tier 3 data
        (tmp_path / "sections").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tier3").mkdir(parents=True, exist_ok=True)

        result = cross_section_consistency(
            "assembled.json", "sections/", "tier3/", repo_root=tmp_path,
        )
        assert result.passed
