"""
Tests for Step 7 — runner/predicates/coverage_predicates.py

Covers all 11 predicate functions:

    all_wps_have_deliverable_and_lead
    all_partners_in_tier3
    all_management_roles_in_tier3
    all_tasks_have_months
    all_impacts_mapped
    kpis_traceable_to_wps
    instrument_sections_addressed
    all_sections_drafted
    all_sections_have_traceability_footer
    wp_budget_coverage_match
    partner_budget_coverage_match

All tests use synthetic temp files via pytest ``tmp_path``.
No dependency on live repository artifacts.

Test organisation
-----------------
  §all_wps_have_deliverable_and_lead    — 7 cases
  §all_partners_in_tier3               — 6 cases
  §all_management_roles_in_tier3       — 6 cases
  §all_tasks_have_months               — 8 cases
  §all_impacts_mapped                  — 7 cases
  §kpis_traceable_to_wps               — 7 cases
  §instrument_sections_addressed       — 6 cases
  §all_sections_drafted                — 6 cases
  §all_sections_have_traceability_footer — 6 cases
  §wp_budget_coverage_match            — 6 cases
  §partner_budget_coverage_match       — 6 cases
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.predicates.coverage_predicates import (
    all_impacts_mapped,
    all_management_roles_in_tier3,
    all_partners_in_tier3,
    all_sections_drafted,
    all_sections_have_traceability_footer,
    all_tasks_have_months,
    all_wps_have_deliverable_and_lead,
    instrument_sections_addressed,
    kpis_traceable_to_wps,
    partner_budget_coverage_match,
    wp_budget_coverage_match,
)
from runner.predicates.types import (
    CROSS_ARTIFACT_INCONSISTENCY,
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, content: object) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(content), encoding="utf-8")
    return p


def _mkdir(tmp_path: Path, name: str) -> Path:
    d = tmp_path / name
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_WP_STRUCTURE = {
    "schema_id": "orch.phase3.wp_structure.v1",
    "run_id": "run-001",
    "work_packages": [
        {
            "wp_id": "WP1",
            "title": "WP 1",
            "lead_partner": "UNIV_A",
            "contributing_partners": ["INST_B"],
            "tasks": [
                {"task_id": "T1.1", "title": "Task 1.1", "responsible_partner": "UNIV_A"},
                {"task_id": "T1.2", "title": "Task 1.2", "responsible_partner": "INST_B"},
            ],
            "deliverables": [
                {"deliverable_id": "D1.1", "title": "Del 1.1", "type": "report",
                 "due_month": 12, "responsible_partner": "UNIV_A"},
            ],
            "dependencies": [],
        },
        {
            "wp_id": "WP2",
            "title": "WP 2",
            "lead_partner": "INST_B",
            "contributing_partners": [],
            "tasks": [
                {"task_id": "T2.1", "title": "Task 2.1", "responsible_partner": "INST_B"},
            ],
            "deliverables": [
                {"deliverable_id": "D2.1", "title": "Del 2.1", "type": "dataset",
                 "due_month": 24, "responsible_partner": "INST_B"},
            ],
            "dependencies": [],
        },
    ],
    "dependency_map": {"nodes": ["WP1", "WP2"], "edges": []},
    "partner_role_matrix": [],
}

_PARTNERS_ARRAY = [
    {"partner_id": "UNIV_A", "name": "University A"},
    {"partner_id": "INST_B", "name": "Institute B"},
]

_GANTT = {
    "schema_id": "orch.phase4.gantt.v1",
    "run_id": "run-001",
    "tasks": [
        {"task_id": "T1.1", "wp_id": "WP1", "start_month": 1, "end_month": 6,
         "responsible_partner": "UNIV_A"},
        {"task_id": "T1.2", "wp_id": "WP1", "start_month": 3, "end_month": 12,
         "responsible_partner": "INST_B"},
        {"task_id": "T2.1", "wp_id": "WP2", "start_month": 1, "end_month": 36,
         "responsible_partner": "INST_B"},
    ],
    "milestones": [],
    "critical_path": ["T1.1", "T2.1"],
}

_IMPACT_ARCH = {
    "schema_id": "orch.phase5.impact_architecture.v1",
    "run_id": "run-001",
    "impact_pathways": [
        {
            "pathway_id": "P1",
            "expected_impact_id": "EI1",
            "project_outputs": ["D1.1"],
            "outcomes": [],
            "impact_narrative": "Narrative 1",
            "tier2b_source_ref": "§2.1",
        },
        {
            "pathway_id": "P2",
            "expected_impact_id": "EI2",
            "project_outputs": ["D2.1"],
            "outcomes": [],
            "impact_narrative": "Narrative 2",
            "tier2b_source_ref": "§2.2",
        },
    ],
    "kpis": [
        {
            "kpi_id": "KPI1",
            "description": "Measure X",
            "target": "100%",
            "measurement_method": "survey",
            "traceable_to_deliverable": "D1.1",
        },
    ],
    "dissemination_plan": {"activities": [], "open_access_policy": "open"},
    "exploitation_plan": {"activities": []},
    "sustainability_mechanism": {"description": "Sustain", "responsible_partners": []},
}

_EXPECTED_IMPACTS = [
    {"impact_id": "EI1", "description": "Impact 1", "source_section": "§2.1"},
    {"impact_id": "EI2", "description": "Impact 2", "source_section": "§2.2"},
]

_IMPL_ARCH = {
    "schema_id": "orch.phase6.implementation_architecture.v1",
    "run_id": "run-001",
    "risk_register": [],
    "ethics_assessment": {
        "ethics_issues_identified": False,
        "issues": [],
        "self_assessment_statement": "No ethics issues.",
    },
    "governance_matrix": [],
    "management_roles": [
        {
            "role_id": "R1",
            "role_name": "Project Coordinator",
            "assigned_to": "UNIV_A",
            "responsibilities": ["coordination"],
        },
    ],
    "instrument_sections_addressed": [
        {
            "section_id": "sec_management",
            "section_name": "Management Structure",
            "status": "addressed",
        },
        {
            "section_id": "sec_ethics",
            "section_name": "Ethics",
            "status": "addressed",
        },
    ],
}

_SECTION_REGISTRY_ARRAY = [
    {"section_id": "sec_objectives", "mandatory": True},
    {"section_id": "sec_impact", "mandatory": True},
    {"section_id": "sec_management", "section_type": "implementation", "mandatory": True},
    {"section_id": "sec_ethics", "section_type": "implementation", "mandatory": True},
    {"section_id": "sec_optional", "mandatory": False},
]

_GOOD_SECTION = {
    "schema_id": "orch.tier5.proposal_section.v1",
    "run_id": "run-001",
    "section_id": "sec_objectives",
    "section_name": "Objectives",
    "content": "The project objectives are ...",
    "word_count": 500,
    "validation_status": {
        "overall_status": "confirmed",
        "claim_statuses": [],
    },
    "traceability_footer": {
        "primary_sources": [
            {"tier": 3, "source_path": "docs/tier3/.../objectives.json"},
        ],
        "no_unsupported_claims_declaration": True,
    },
}


# ===========================================================================
# §all_wps_have_deliverable_and_lead
# ===========================================================================


class TestAllWpsHaveDeliverableAndLead:

    def test_pass_all_wps_valid(self, tmp_path):
        p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = all_wps_have_deliverable_and_lead(p)
        assert result.passed
        assert result.details["wps_checked"] == 2

    def test_fail_missing_file(self, tmp_path):
        result = all_wps_have_deliverable_and_lead(tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_invalid_json(self, tmp_path):
        p = tmp_path / "wp_structure.json"
        p.write_text("{bad json", encoding="utf-8")
        result = all_wps_have_deliverable_and_lead(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_missing_work_packages_field(self, tmp_path):
        p = _write(tmp_path, "wp_structure.json", {"schema_id": "x", "run_id": "r"})
        result = all_wps_have_deliverable_and_lead(p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_wp_missing_lead_partner(self, tmp_path):
        data = json.loads(json.dumps(_WP_STRUCTURE))
        data["work_packages"][0]["lead_partner"] = ""
        p = _write(tmp_path, "wp_structure.json", data)
        result = all_wps_have_deliverable_and_lead(p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert any("WP1" in str(v) for v in result.details["violations"])

    def test_fail_wp_empty_deliverables(self, tmp_path):
        data = json.loads(json.dumps(_WP_STRUCTURE))
        data["work_packages"][1]["deliverables"] = []
        p = _write(tmp_path, "wp_structure.json", data)
        result = all_wps_have_deliverable_and_lead(p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert any("WP2" in str(v) for v in result.details["violations"])

    def test_fail_multiple_wps_invalid(self, tmp_path):
        data = json.loads(json.dumps(_WP_STRUCTURE))
        data["work_packages"][0]["lead_partner"] = None
        data["work_packages"][1]["deliverables"] = []
        p = _write(tmp_path, "wp_structure.json", data)
        result = all_wps_have_deliverable_and_lead(p)
        assert not result.passed
        assert len(result.details["violations"]) == 2


# ===========================================================================
# §all_partners_in_tier3
# ===========================================================================


class TestAllPartnersInTier3:

    def test_pass_all_partners_present(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        result = all_partners_in_tier3(wp_p, par_p)
        assert result.passed

    def test_fail_missing_wp_file(self, tmp_path):
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        result = all_partners_in_tier3(tmp_path / "missing.json", par_p)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_partners_file(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = all_partners_in_tier3(wp_p, tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_partner_not_in_tier3(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        # partners.json missing INST_B
        par_p = _write(tmp_path, "partners.json",
                       [{"partner_id": "UNIV_A", "name": "University A"}])
        result = all_partners_in_tier3(wp_p, par_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "INST_B" in result.details["missing_from_tier3"]

    def test_pass_partners_as_object(self, tmp_path):
        """partners.json in dict-of-entries form."""
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        par_p = _write(tmp_path, "partners.json", {
            "UNIV_A": {"name": "University A"},
            "INST_B": {"name": "Institute B"},
        })
        result = all_partners_in_tier3(wp_p, par_p)
        assert result.passed

    def test_fail_invalid_partners_json(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        par_p = tmp_path / "partners.json"
        par_p.write_text("{bad json", encoding="utf-8")
        result = all_partners_in_tier3(wp_p, par_p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_pass_wrapped_array_with_short_name(self, tmp_path):
        """partners.json in {"partners": [...]} form using short_name field."""
        wp_data = {
            "schema_id": "orch.phase3.wp_structure.v1",
            "run_id": "run-001",
            "work_packages": [
                {
                    "wp_id": "WP1",
                    "title": "WP 1",
                    "lead_partner": "ATU",
                    "contributing_partners": ["CERIA", "BIIS"],
                    "tasks": [],
                    "deliverables": [{"deliverable_id": "D1.1"}],
                },
            ],
        }
        wp_p = _write(tmp_path, "wp_structure.json", wp_data)
        par_p = _write(tmp_path, "partners.json", {
            "partners": [
                {"partner_number": 1, "short_name": "ATU", "legal_name": "Alpenstadt TU",
                 "country": "DE", "coordinator": True},
                {"partner_number": 2, "short_name": "CERIA", "legal_name": "CERIA",
                 "country": "FR", "coordinator": False},
                {"partner_number": 3, "short_name": "BIIS", "legal_name": "BIIS",
                 "country": "NL", "coordinator": False},
            ]
        })
        result = all_partners_in_tier3(wp_p, par_p)
        assert result.passed

    def test_fail_wrapped_array_missing_partner(self, tmp_path):
        """Wrapped array partners.json with one partner missing → fail."""
        wp_data = {
            "schema_id": "orch.phase3.wp_structure.v1",
            "run_id": "run-001",
            "work_packages": [
                {
                    "wp_id": "WP1",
                    "lead_partner": "ATU",
                    "contributing_partners": ["UNKNOWN_PARTNER"],
                    "tasks": [],
                    "deliverables": [{"deliverable_id": "D1.1"}],
                },
            ],
        }
        wp_p = _write(tmp_path, "wp_structure.json", wp_data)
        par_p = _write(tmp_path, "partners.json", {
            "partners": [
                {"short_name": "ATU", "legal_name": "Alpenstadt TU"},
            ]
        })
        result = all_partners_in_tier3(wp_p, par_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "UNKNOWN_PARTNER" in result.details["missing_from_tier3"]

    def test_pass_short_name_in_flat_array(self, tmp_path):
        """Flat array partners.json with short_name field (no partner_id/id)."""
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        par_p = _write(tmp_path, "partners.json", [
            {"short_name": "UNIV_A", "legal_name": "University A"},
            {"short_name": "INST_B", "legal_name": "Institute B"},
        ])
        result = all_partners_in_tier3(wp_p, par_p)
        assert result.passed

    def test_pass_real_consortium_structure(self, tmp_path):
        """Full real-like consortium structure with 8 partners in wrapped array form."""
        partners = [
            "ATU", "CERIA", "BIIS", "ISIA", "NIHS", "ELI", "BAL", "FIIT"
        ]
        wp_data = {
            "schema_id": "orch.phase3.wp_structure.v1",
            "run_id": "run-001",
            "work_packages": [
                {
                    "wp_id": "WP1",
                    "lead_partner": "ATU",
                    "contributing_partners": ["CERIA", "BIIS", "ISIA", "NIHS", "ELI", "BAL", "FIIT"],
                    "tasks": [],
                    "deliverables": [{"deliverable_id": "D1.1"}],
                },
            ],
        }
        wp_p = _write(tmp_path, "wp_structure.json", wp_data)
        par_p = _write(tmp_path, "partners.json", {
            "partners": [
                {"partner_number": i + 1, "short_name": sn, "legal_name": f"Org {sn}",
                 "country": "XX", "coordinator": i == 0}
                for i, sn in enumerate(partners)
            ]
        })
        result = all_partners_in_tier3(wp_p, par_p)
        assert result.passed
        assert result.details["partners_checked"] == 8


# ===========================================================================
# §all_management_roles_in_tier3
# ===========================================================================


class TestAllManagementRolesInTier3:

    def test_pass_all_roles_valid(self, tmp_path):
        impl_p = _write(tmp_path, "impl.json", _IMPL_ARCH)
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        result = all_management_roles_in_tier3(impl_p, par_p)
        assert result.passed

    def test_fail_missing_impl_file(self, tmp_path):
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        result = all_management_roles_in_tier3(tmp_path / "missing.json", par_p)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_management_roles_field(self, tmp_path):
        data = {"schema_id": "x", "run_id": "r"}
        impl_p = _write(tmp_path, "impl.json", data)
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        result = all_management_roles_in_tier3(impl_p, par_p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_assignee_not_in_tier3(self, tmp_path):
        data = json.loads(json.dumps(_IMPL_ARCH))
        data["management_roles"][0]["assigned_to"] = "UNKNOWN_PARTNER"
        impl_p = _write(tmp_path, "impl.json", data)
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        result = all_management_roles_in_tier3(impl_p, par_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "UNKNOWN_PARTNER" in result.details["missing_from_tier3"]

    def test_pass_empty_management_roles(self, tmp_path):
        """No management roles → vacuous pass."""
        data = json.loads(json.dumps(_IMPL_ARCH))
        data["management_roles"] = []
        impl_p = _write(tmp_path, "impl.json", data)
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        result = all_management_roles_in_tier3(impl_p, par_p)
        assert result.passed

    def test_fail_partners_malformed(self, tmp_path):
        impl_p = _write(tmp_path, "impl.json", _IMPL_ARCH)
        par_p = tmp_path / "partners.json"
        par_p.write_text("not-json!!!", encoding="utf-8")
        result = all_management_roles_in_tier3(impl_p, par_p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT


# ===========================================================================
# §all_tasks_have_months
# ===========================================================================


class TestAllTasksHaveMonths:

    def test_pass_all_tasks_scheduled(self, tmp_path):
        gantt_p = _write(tmp_path, "gantt.json", _GANTT)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = all_tasks_have_months(gantt_p, wp_p)
        assert result.passed
        assert result.details["tasks_checked"] == 3

    def test_fail_missing_gantt_file(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = all_tasks_have_months(tmp_path / "missing.json", wp_p)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_wp_file(self, tmp_path):
        gantt_p = _write(tmp_path, "gantt.json", _GANTT)
        result = all_tasks_have_months(gantt_p, tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_gantt_tasks_field_absent(self, tmp_path):
        gantt_p = _write(tmp_path, "gantt.json", {"schema_id": "x", "run_id": "r"})
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = all_tasks_have_months(gantt_p, wp_p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_task_missing_from_gantt(self, tmp_path):
        gantt_data = json.loads(json.dumps(_GANTT))
        # Remove T2.1 from gantt
        gantt_data["tasks"] = [t for t in gantt_data["tasks"] if t["task_id"] != "T2.1"]
        gantt_p = _write(tmp_path, "gantt.json", gantt_data)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = all_tasks_have_months(gantt_p, wp_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        missing_tasks = [v["task_id"] for v in result.details["violations"]]
        assert "T2.1" in missing_tasks

    def test_fail_task_null_start_month(self, tmp_path):
        gantt_data = json.loads(json.dumps(_GANTT))
        gantt_data["tasks"][0]["start_month"] = None
        gantt_p = _write(tmp_path, "gantt.json", gantt_data)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = all_tasks_have_months(gantt_p, wp_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        violation_ids = [v["task_id"] for v in result.details["violations"]]
        assert "T1.1" in violation_ids

    def test_fail_task_null_end_month(self, tmp_path):
        gantt_data = json.loads(json.dumps(_GANTT))
        gantt_data["tasks"][1]["end_month"] = None
        gantt_p = _write(tmp_path, "gantt.json", gantt_data)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = all_tasks_have_months(gantt_p, wp_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_pass_no_tasks_in_wps(self, tmp_path):
        """No WP tasks → vacuous pass."""
        data = json.loads(json.dumps(_WP_STRUCTURE))
        for wp in data["work_packages"]:
            wp["tasks"] = []
        gantt_p = _write(tmp_path, "gantt.json", _GANTT)
        wp_p = _write(tmp_path, "wp_structure.json", data)
        result = all_tasks_have_months(gantt_p, wp_p)
        assert result.passed
        assert result.details["tasks_checked"] == 0


# ===========================================================================
# §all_impacts_mapped
# ===========================================================================


class TestAllImpactsMapped:

    def test_pass_all_impacts_covered(self, tmp_path):
        impact_p = _write(tmp_path, "impact_architecture.json", _IMPACT_ARCH)
        exp_p = _write(tmp_path, "expected_impacts.json", _EXPECTED_IMPACTS)
        result = all_impacts_mapped(impact_p, exp_p)
        assert result.passed
        assert result.details["expected_impacts_checked"] == 2

    def test_fail_missing_impact_file(self, tmp_path):
        exp_p = _write(tmp_path, "expected_impacts.json", _EXPECTED_IMPACTS)
        result = all_impacts_mapped(tmp_path / "missing.json", exp_p)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_expected_impacts_file(self, tmp_path):
        impact_p = _write(tmp_path, "impact_architecture.json", _IMPACT_ARCH)
        result = all_impacts_mapped(impact_p, tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_impact_pathways_field_absent(self, tmp_path):
        impact_p = _write(tmp_path, "impact_architecture.json", {"schema_id": "x", "run_id": "r"})
        exp_p = _write(tmp_path, "expected_impacts.json", _EXPECTED_IMPACTS)
        result = all_impacts_mapped(impact_p, exp_p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_expected_impact_not_mapped(self, tmp_path):
        data = json.loads(json.dumps(_IMPACT_ARCH))
        # Remove EI2 pathway
        data["impact_pathways"] = [p for p in data["impact_pathways"]
                                   if p["expected_impact_id"] != "EI2"]
        impact_p = _write(tmp_path, "impact_architecture.json", data)
        exp_p = _write(tmp_path, "expected_impacts.json", _EXPECTED_IMPACTS)
        result = all_impacts_mapped(impact_p, exp_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "EI2" in result.details["missing"]

    def test_fail_impact_mapped_but_no_project_outputs(self, tmp_path):
        data = json.loads(json.dumps(_IMPACT_ARCH))
        data["impact_pathways"][1]["project_outputs"] = []
        impact_p = _write(tmp_path, "impact_architecture.json", data)
        exp_p = _write(tmp_path, "expected_impacts.json", _EXPECTED_IMPACTS)
        result = all_impacts_mapped(impact_p, exp_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "EI2" in result.details["missing"]

    def test_pass_empty_expected_impacts(self, tmp_path):
        """Empty expected_impacts.json → vacuous pass."""
        impact_p = _write(tmp_path, "impact_architecture.json", _IMPACT_ARCH)
        exp_p = _write(tmp_path, "expected_impacts.json", [])
        result = all_impacts_mapped(impact_p, exp_p)
        assert result.passed
        assert result.details["expected_impacts_checked"] == 0


# ===========================================================================
# §kpis_traceable_to_wps
# ===========================================================================


class TestKpisTraceableToWps:

    def test_pass_all_kpis_traceable(self, tmp_path):
        impact_p = _write(tmp_path, "impact_architecture.json", _IMPACT_ARCH)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = kpis_traceable_to_wps(impact_p, wp_p)
        assert result.passed
        assert result.details["kpis_checked"] == 1

    def test_fail_missing_impact_file(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = kpis_traceable_to_wps(tmp_path / "missing.json", wp_p)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_wp_file(self, tmp_path):
        impact_p = _write(tmp_path, "impact_architecture.json", _IMPACT_ARCH)
        result = kpis_traceable_to_wps(impact_p, tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_kpis_field_absent(self, tmp_path):
        data = {"schema_id": "x", "run_id": "r", "impact_pathways": []}
        impact_p = _write(tmp_path, "impact_architecture.json", data)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = kpis_traceable_to_wps(impact_p, wp_p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_kpi_deliverable_not_in_wps(self, tmp_path):
        data = json.loads(json.dumps(_IMPACT_ARCH))
        data["kpis"][0]["traceable_to_deliverable"] = "D9.9_NONEXISTENT"
        impact_p = _write(tmp_path, "impact_architecture.json", data)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = kpis_traceable_to_wps(impact_p, wp_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert any(v.get("traceable_to_deliverable") == "D9.9_NONEXISTENT"
                   for v in result.details["violations"])

    def test_fail_kpi_missing_traceable_field(self, tmp_path):
        data = json.loads(json.dumps(_IMPACT_ARCH))
        del data["kpis"][0]["traceable_to_deliverable"]
        impact_p = _write(tmp_path, "impact_architecture.json", data)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = kpis_traceable_to_wps(impact_p, wp_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_pass_no_kpis(self, tmp_path):
        """Empty kpis list → vacuous pass."""
        data = json.loads(json.dumps(_IMPACT_ARCH))
        data["kpis"] = []
        impact_p = _write(tmp_path, "impact_architecture.json", data)
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = kpis_traceable_to_wps(impact_p, wp_p)
        assert result.passed
        assert result.details["kpis_checked"] == 0


# ===========================================================================
# §instrument_sections_addressed
# ===========================================================================


class TestInstrumentSectionsAddressed:

    def test_pass_all_impl_sections_addressed(self, tmp_path):
        impl_p = _write(tmp_path, "impl.json", _IMPL_ARCH)
        schema_p = _write(tmp_path, "registry.json", _SECTION_REGISTRY_ARRAY)
        result = instrument_sections_addressed(impl_p, schema_p)
        assert result.passed
        assert result.details["required_sections_checked"] == 2  # sec_management + sec_ethics

    def test_fail_missing_impl_file(self, tmp_path):
        schema_p = _write(tmp_path, "registry.json", _SECTION_REGISTRY_ARRAY)
        result = instrument_sections_addressed(tmp_path / "missing.json", schema_p)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_instrument_sections_addressed_field_absent(self, tmp_path):
        data = {"schema_id": "x", "run_id": "r"}
        impl_p = _write(tmp_path, "impl.json", data)
        schema_p = _write(tmp_path, "registry.json", _SECTION_REGISTRY_ARRAY)
        result = instrument_sections_addressed(impl_p, schema_p)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_fail_required_section_missing(self, tmp_path):
        data = json.loads(json.dumps(_IMPL_ARCH))
        # Remove sec_ethics from addressed list
        data["instrument_sections_addressed"] = [
            e for e in data["instrument_sections_addressed"]
            if e["section_id"] != "sec_ethics"
        ]
        impl_p = _write(tmp_path, "impl.json", data)
        schema_p = _write(tmp_path, "registry.json", _SECTION_REGISTRY_ARRAY)
        result = instrument_sections_addressed(impl_p, schema_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "sec_ethics" in result.details["missing_or_deferred"]

    def test_fail_section_status_deferred(self, tmp_path):
        data = json.loads(json.dumps(_IMPL_ARCH))
        data["instrument_sections_addressed"][0]["status"] = "deferred"
        impl_p = _write(tmp_path, "impl.json", data)
        schema_p = _write(tmp_path, "registry.json", _SECTION_REGISTRY_ARRAY)
        result = instrument_sections_addressed(impl_p, schema_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_pass_empty_registry(self, tmp_path):
        """Empty registry → vacuous pass."""
        impl_p = _write(tmp_path, "impl.json", _IMPL_ARCH)
        schema_p = _write(tmp_path, "registry.json", [])
        result = instrument_sections_addressed(impl_p, schema_p)
        assert result.passed
        assert result.details["required_sections_checked"] == 0


# ===========================================================================
# §all_sections_drafted
# ===========================================================================


class TestAllSectionsDrafted:

    def test_pass_all_required_sections_present(self, tmp_path):
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        schema_p = _write(tmp_path, "registry.json", _SECTION_REGISTRY_ARRAY)
        # Create all mandatory section files
        for sec_id in ("sec_objectives", "sec_impact", "sec_management", "sec_ethics"):
            _write(sections_dir, f"{sec_id}.json", {"section_id": sec_id})
        result = all_sections_drafted(sections_dir, schema_p)
        assert result.passed
        assert result.details["required_sections_checked"] == 4

    def test_fail_sections_dir_missing(self, tmp_path):
        schema_p = _write(tmp_path, "registry.json", _SECTION_REGISTRY_ARRAY)
        result = all_sections_drafted(tmp_path / "nonexistent", schema_p)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_schema_file_missing(self, tmp_path):
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        result = all_sections_drafted(sections_dir, tmp_path / "missing.json")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_required_section_file_absent(self, tmp_path):
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        schema_p = _write(tmp_path, "registry.json", _SECTION_REGISTRY_ARRAY)
        # Only create some section files, missing sec_impact
        _write(sections_dir, "sec_objectives.json", {"section_id": "sec_objectives"})
        _write(sections_dir, "sec_management.json", {"section_id": "sec_management"})
        _write(sections_dir, "sec_ethics.json", {"section_id": "sec_ethics"})
        result = all_sections_drafted(sections_dir, schema_p)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "sec_impact" in result.details["missing_files"]

    def test_pass_empty_registry(self, tmp_path):
        """No required sections in registry → vacuous pass."""
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        schema_p = _write(tmp_path, "registry.json", [])
        result = all_sections_drafted(sections_dir, schema_p)
        assert result.passed
        assert result.details["required_sections_checked"] == 0

    def test_pass_object_registry_form(self, tmp_path):
        """Registry as object: keys are section IDs."""
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        registry = {
            "sec_objectives": {"mandatory": True},
            "sec_optional": {"mandatory": False},
        }
        schema_p = _write(tmp_path, "registry.json", registry)
        _write(sections_dir, "sec_objectives.json", {"section_id": "sec_objectives"})
        result = all_sections_drafted(sections_dir, schema_p)
        assert result.passed
        assert result.details["required_sections_checked"] == 1


# ===========================================================================
# §all_sections_have_traceability_footer
# ===========================================================================


class TestAllSectionsHaveTraceabilityFooter:

    def test_pass_all_sections_have_footer(self, tmp_path):
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        _write(sections_dir, "sec_objectives.json", _GOOD_SECTION)
        result = all_sections_have_traceability_footer(sections_dir)
        assert result.passed
        assert result.details["files_checked"] == 1

    def test_fail_directory_missing(self, tmp_path):
        result = all_sections_have_traceability_footer(tmp_path / "nonexistent")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_pass_empty_directory(self, tmp_path):
        """Empty directory → vacuous pass."""
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        result = all_sections_have_traceability_footer(sections_dir)
        assert result.passed
        assert result.details["files_checked"] == 0

    def test_fail_missing_traceability_footer_field(self, tmp_path):
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        data = json.loads(json.dumps(_GOOD_SECTION))
        del data["traceability_footer"]
        _write(sections_dir, "sec_objectives.json", data)
        result = all_sections_have_traceability_footer(sections_dir)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert any(v["file"] == "sec_objectives.json" for v in result.details["violations"])

    def test_fail_empty_primary_sources(self, tmp_path):
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        data = json.loads(json.dumps(_GOOD_SECTION))
        data["traceability_footer"]["primary_sources"] = []
        _write(sections_dir, "sec_objectives.json", data)
        result = all_sections_have_traceability_footer(sections_dir)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY

    def test_fail_multiple_sections_some_invalid(self, tmp_path):
        sections_dir = _mkdir(tmp_path, "proposal_sections")
        _write(sections_dir, "sec_good.json", _GOOD_SECTION)
        bad = {"section_id": "sec_bad", "traceability_footer": {"primary_sources": []}}
        _write(sections_dir, "sec_bad.json", bad)
        result = all_sections_have_traceability_footer(sections_dir)
        assert not result.passed
        violation_files = [v["file"] for v in result.details["violations"]]
        assert "sec_bad.json" in violation_files
        assert "sec_good.json" not in violation_files


# ===========================================================================
# §wp_budget_coverage_match
# ===========================================================================


class TestWpBudgetCoverageMatch:

    def _make_budget_dir(self, tmp_path: Path, wp_ids: list[str]) -> Path:
        """Create a budget received/ dir with a response JSON containing the given WP IDs."""
        budget_dir = _mkdir(tmp_path, "received")
        budget_response = {
            "work_package_budgets": [
                {"wp_id": wp_id, "total_cost": 100000}
                for wp_id in wp_ids
            ]
        }
        _write(budget_dir, "budget_response.json", budget_response)
        return budget_dir

    def test_pass_all_wps_in_budget(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        budget_dir = self._make_budget_dir(tmp_path, ["WP1", "WP2"])
        result = wp_budget_coverage_match(wp_p, budget_dir)
        assert result.passed
        assert result.details["wps_checked"] == 2

    def test_fail_missing_wp_file(self, tmp_path):
        budget_dir = self._make_budget_dir(tmp_path, ["WP1"])
        result = wp_budget_coverage_match(tmp_path / "missing.json", budget_dir)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_budget_dir(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        result = wp_budget_coverage_match(wp_p, tmp_path / "nonexistent_dir")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_wp_not_in_budget(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        # Budget only contains WP1, missing WP2
        budget_dir = self._make_budget_dir(tmp_path, ["WP1"])
        result = wp_budget_coverage_match(wp_p, budget_dir)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "WP2" in result.details["missing_from_budget"]

    def test_fail_work_packages_field_absent(self, tmp_path):
        wp_p = _write(tmp_path, "wp_structure.json", {"schema_id": "x", "run_id": "r"})
        budget_dir = self._make_budget_dir(tmp_path, ["WP1"])
        result = wp_budget_coverage_match(wp_p, budget_dir)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT

    def test_pass_deep_nested_wp_ids(self, tmp_path):
        """Budget response with wp_id nested deeply is still found."""
        wp_p = _write(tmp_path, "wp_structure.json", _WP_STRUCTURE)
        budget_dir = _mkdir(tmp_path, "received")
        _write(budget_dir, "budget_response.json", {
            "project": {
                "financials": {
                    "work_packages": [
                        {"wp_id": "WP1", "cost": 100},
                        {"wp_id": "WP2", "cost": 200},
                    ]
                }
            }
        })
        result = wp_budget_coverage_match(wp_p, budget_dir)
        assert result.passed


# ===========================================================================
# §partner_budget_coverage_match
# ===========================================================================


class TestPartnerBudgetCoverageMatch:

    def _make_budget_dir(self, tmp_path: Path, partner_ids: list[str]) -> Path:
        budget_dir = _mkdir(tmp_path, "received")
        budget_response = {
            "partner_costs": [
                {"partner_id": pid, "total_cost": 50000}
                for pid in partner_ids
            ]
        }
        _write(budget_dir, "budget_response.json", budget_response)
        return budget_dir

    def test_pass_all_partners_in_budget(self, tmp_path):
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        budget_dir = self._make_budget_dir(tmp_path, ["UNIV_A", "INST_B"])
        result = partner_budget_coverage_match(par_p, budget_dir)
        assert result.passed
        assert result.details["partners_checked"] == 2

    def test_fail_missing_partners_file(self, tmp_path):
        budget_dir = self._make_budget_dir(tmp_path, ["UNIV_A"])
        result = partner_budget_coverage_match(tmp_path / "missing.json", budget_dir)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_missing_budget_dir(self, tmp_path):
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        result = partner_budget_coverage_match(par_p, tmp_path / "nonexistent_dir")
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_fail_partner_not_in_budget(self, tmp_path):
        par_p = _write(tmp_path, "partners.json", _PARTNERS_ARRAY)
        # Budget only has UNIV_A
        budget_dir = self._make_budget_dir(tmp_path, ["UNIV_A"])
        result = partner_budget_coverage_match(par_p, budget_dir)
        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "INST_B" in result.details["missing_from_budget"]

    def test_pass_partners_as_dict_form(self, tmp_path):
        """partners.json in dict-of-entries form."""
        par_p = _write(tmp_path, "partners.json", {
            "UNIV_A": {"name": "Univ A"},
            "INST_B": {"name": "Inst B"},
        })
        budget_dir = self._make_budget_dir(tmp_path, ["UNIV_A", "INST_B"])
        result = partner_budget_coverage_match(par_p, budget_dir)
        assert result.passed

    def test_fail_invalid_partners_json(self, tmp_path):
        par_p = tmp_path / "partners.json"
        par_p.write_text("{not valid json!!", encoding="utf-8")
        budget_dir = self._make_budget_dir(tmp_path, ["UNIV_A"])
        result = partner_budget_coverage_match(par_p, budget_dir)
        assert not result.passed
        assert result.failure_category == MALFORMED_ARTIFACT


# ===========================================================================
# §gate_and_gate_enforcement_alignment — integration-style sanity checks
# ===========================================================================


class TestGateAndGateEnforcementAlignment:
    """
    Focused integration-style tests ensuring the real gate predicate
    (all_partners_in_tier3) produces results consistent with the actual
    Tier 3 consortium structure used by the project.

    These tests verify that the predicate correctly resolves partner
    identifiers from the same ``partners.json`` format that the
    gate-enforcement skill reads.  If these tests pass, there is no
    semantic drift between the real gate evaluator and the gate-enforcement
    evidence on partner coverage.
    """

    def test_alignment_wrapped_array_short_name_matches_wp_partners(self, tmp_path):
        """
        Given a wrapped-array partners.json using short_name and a
        wp_structure.json referencing the same short names:
        - all_partners_in_tier3 must pass
        - the partner set resolved from partners.json matches the WP references

        This is the exact scenario where the real gate evaluator and
        gate-enforcement evidence previously disagreed.
        """
        partner_names = ["ATU", "CERIA", "BIIS", "ISIA", "NIHS", "ELI", "BAL", "FIIT"]
        partners_data = {
            "partners": [
                {
                    "partner_number": i + 1,
                    "short_name": sn,
                    "legal_name": f"Organisation {sn}",
                    "country": "XX",
                    "organisation_type": "HES",
                    "coordinator": i == 0,
                }
                for i, sn in enumerate(partner_names)
            ]
        }
        wp_data = {
            "schema_id": "orch.phase3.wp_structure.v1",
            "run_id": "test-alignment",
            "work_packages": [
                {
                    "wp_id": "WP1",
                    "lead_partner": "ATU",
                    "contributing_partners": ["CERIA", "BIIS", "ISIA", "NIHS", "ELI", "BAL", "FIIT"],
                    "tasks": [],
                    "deliverables": [{"deliverable_id": "D1.1"}],
                },
                {
                    "wp_id": "WP2",
                    "lead_partner": "CERIA",
                    "contributing_partners": ["ATU", "BIIS"],
                    "tasks": [],
                    "deliverables": [{"deliverable_id": "D2.1"}],
                },
            ],
        }

        wp_p = _write(tmp_path, "wp_structure.json", wp_data)
        par_p = _write(tmp_path, "partners.json", partners_data)
        result = all_partners_in_tier3(wp_p, par_p)

        assert result.passed, (
            f"all_partners_in_tier3 failed but should pass: {result.reason}"
        )
        assert result.details["partners_checked"] == 8
        assert result.details["all_found_in_tier3"] is True

    def test_alignment_unknown_partner_still_fails(self, tmp_path):
        """
        Even with the wrapped-array format fix, referencing a truly
        unknown partner must still fail.
        """
        partners_data = {
            "partners": [
                {"short_name": "ATU", "legal_name": "Alpenstadt TU"},
            ]
        }
        wp_data = {
            "schema_id": "orch.phase3.wp_structure.v1",
            "run_id": "test-alignment",
            "work_packages": [
                {
                    "wp_id": "WP1",
                    "lead_partner": "ATU",
                    "contributing_partners": ["NONEXISTENT_ORG"],
                    "tasks": [],
                    "deliverables": [{"deliverable_id": "D1.1"}],
                },
            ],
        }

        wp_p = _write(tmp_path, "wp_structure.json", wp_data)
        par_p = _write(tmp_path, "partners.json", partners_data)
        result = all_partners_in_tier3(wp_p, par_p)

        assert not result.passed
        assert result.failure_category == CROSS_ARTIFACT_INCONSISTENCY
        assert "NONEXISTENT_ORG" in result.details["missing_from_tier3"]
