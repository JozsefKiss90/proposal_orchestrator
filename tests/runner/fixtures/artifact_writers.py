"""
Canonical artifact writers for Step 12 gate fixture tests.

Each function writes one canonical artifact to its standard repository-relative
path under *repo_root*.  The data produced is structurally valid and satisfies
the relevant predicate contracts, unless the caller explicitly overrides a field
to build a failing fixture.

All paths match the real gate_rules_library.yaml so that tests that use the real
gate library file will find artifacts at the expected locations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.runner.fixtures.repo_builders import write_json

# ---------------------------------------------------------------------------
# Tier 3 — Project instantiation
# ---------------------------------------------------------------------------

_CALL_BINDING = "docs/tier3_project_instantiation/call_binding"
_CONSORTIUM = "docs/tier3_project_instantiation/consortium"
_ARCH_INPUTS = "docs/tier3_project_instantiation/architecture_inputs"

# Canonical partner IDs reused across multiple artifact writers.
_DEFAULT_PARTNERS = [
    {"partner_id": "P1", "name": "Alpha Institute", "country": "DE", "role": "coordinator"},
    {"partner_id": "P2", "name": "Beta University", "country": "FR", "role": "partner"},
]

# Canonical WP/task/deliverable IDs reused across phase outputs.
_WP_ID = "WP1"
_TASK_ID = "T1.1"
_DELIV_ID = "D1.1"
_IMPACT_ID = "EI1"

_DEFAULT_DURATION = 36


def write_selected_call(
    repo_root: Path,
    *,
    instrument_type: str = "RIA",
    call_id: str = "HORIZON-TEST-2025-01",
    topic_code: str = "HE-TEST-TOPIC-01",
    duration: int = _DEFAULT_DURATION,
    extra: dict | None = None,
) -> Path:
    """Write ``selected_call.json`` with all required fields."""
    data: dict[str, Any] = {
        "call_id": call_id,
        "topic_code": topic_code,
        "instrument_type": instrument_type,
        "work_programme_area": "Digital, Industry and Space",
        "project_duration_months": duration,
    }
    if extra:
        data.update(extra)
    path = repo_root / _CALL_BINDING / "selected_call.json"
    write_json(path, data)
    return path


def write_topic_mapping(
    repo_root: Path,
    *,
    with_source_refs: bool = True,
) -> Path:
    """Write ``topic_mapping.json`` with (optionally) valid source refs."""
    entry: dict[str, Any] = {
        "topic_code": "HE-TEST-TOPIC-01",
        "scope_alignment": "Full alignment with call scope",
    }
    if with_source_refs:
        entry["tier2b_source_ref"] = "work_programme.pdf §3.1"
        entry["tier3_evidence_ref"] = "project_brief.json §concept"
    data = {"mappings": [entry]}
    path = repo_root / _CALL_BINDING / "topic_mapping.json"
    write_json(path, data)
    return path


def write_compliance_profile(repo_root: Path) -> Path:
    """Write ``compliance_profile.json``."""
    path = repo_root / _CALL_BINDING / "compliance_profile.json"
    write_json(path, {"compliance_items": [{"item": "eligibility", "status": "confirmed"}]})
    return path


def write_partners(
    repo_root: Path,
    *,
    partners: list[dict] | None = None,
) -> Path:
    """
    Write ``partners.json`` as a direct JSON array.

    The ``_extract_partner_ids`` helper in coverage_predicates.py processes
    the parsed value directly; it expects an array of dicts with ``partner_id``
    fields, not a wrapped ``{"partners": [...]}`` object.
    """
    path = repo_root / _CONSORTIUM / "partners.json"
    write_json(path, partners if partners is not None else _DEFAULT_PARTNERS)
    return path


def write_roles(repo_root: Path) -> Path:
    """Write ``roles.json`` consortium roles file."""
    path = repo_root / _CONSORTIUM / "roles.json"
    write_json(path, {
        "roles": [
            {"partner_id": "P1", "role": "coordinator"},
            {"partner_id": "P2", "role": "partner"},
        ]
    })
    return path


def write_milestones_seed(repo_root: Path) -> Path:
    path = repo_root / _ARCH_INPUTS / "milestones_seed.json"
    write_json(path, {"milestones": [{"milestone_id": "M1", "due_month": 12, "description": "First milestone"}]})
    return path


def write_workpackage_seed(repo_root: Path) -> Path:
    path = repo_root / _ARCH_INPUTS / "workpackage_seed.json"
    write_json(path, {"work_packages": [{"wp_id": _WP_ID, "title": "Management"}]})
    return path


def write_objectives(repo_root: Path) -> Path:
    path = repo_root / _ARCH_INPUTS / "objectives.json"
    write_json(path, {"objectives": [{"id": "O1", "description": "Deliver results"}]})
    return path


def write_outcomes(repo_root: Path) -> Path:
    path = repo_root / _ARCH_INPUTS / "outcomes.json"
    write_json(path, {"outcomes": [{"id": "OUT1", "description": "Improved practice"}]})
    return path


def write_impacts(repo_root: Path) -> Path:
    path = repo_root / _ARCH_INPUTS / "impacts.json"
    write_json(path, {"impacts": [{"id": _IMPACT_ID, "description": "Societal impact"}]})
    return path


def write_risks(repo_root: Path) -> Path:
    path = repo_root / _ARCH_INPUTS / "risks.json"
    write_json(path, {"risks": [{"risk_id": "R1", "description": "Delay risk", "likelihood": "medium"}]})
    return path


def write_project_brief(repo_root: Path) -> Path:
    """Write a minimal project brief file to the project_brief directory."""
    path = repo_root / "docs/tier3_project_instantiation/project_brief/concept_note.json"
    write_json(path, {"concept": "Innovative research proposal"})
    return path


# ---------------------------------------------------------------------------
# Tier 2A extracted
# ---------------------------------------------------------------------------

_T2A_EXTRACTED = "docs/tier2a_instrument_schemas/extracted"


def write_section_schema_registry(
    repo_root: Path,
    *,
    # Used by instrument_type_matches_schema (keys = instrument types)
    instrument_types: list[str] | None = None,
    # Used by all_sections_drafted (keys/ids = section IDs)
    section_ids: list[str] | None = None,
    include_impl_sections: list[str] | None = None,
) -> Path:
    """
    Write ``section_schema_registry.json``.

    This function reconciles the two different interpretations of the file:

    * ``instrument_type_matches_schema`` expects top-level keys to be
      instrument type identifiers (e.g. ``"RIA"``).
    * ``all_sections_drafted`` and ``instrument_sections_addressed`` treat
      top-level keys as section IDs.

    Since these two predicates never appear in the same gate, the caller
    selects the appropriate form via the keyword arguments:

    * ``instrument_types`` (default ``["RIA"]``) — object keys are instrument
      types; used for ``phase_01_gate`` tests.
    * ``section_ids`` (default ``["excellence", "impact", "implementation"]``)
      with optional ``include_impl_sections`` — list format where each item
      carries ``section_id``, ``mandatory``, and optionally ``section_type``;
      used for ``gate_10`` / ``gate_12`` tests.
    """
    path = repo_root / _T2A_EXTRACTED / "section_schema_registry.json"

    if section_ids is not None:
        # List form for all_sections_drafted / instrument_sections_addressed
        entries: list[dict] = []
        impl_set = set(include_impl_sections or [])
        for sid in section_ids:
            entry: dict[str, Any] = {"section_id": sid, "mandatory": True}
            if sid in impl_set:
                entry["section_type"] = "implementation"
            entries.append(entry)
        write_json(path, entries)
    else:
        # Dict form keyed by instrument type for instrument_type_matches_schema
        types = instrument_types if instrument_types is not None else ["RIA"]
        write_json(path, {t: {} for t in types})

    return path


def write_evaluator_expectation_registry(repo_root: Path) -> Path:
    path = repo_root / _T2A_EXTRACTED / "evaluator_expectation_registry.json"
    write_json(path, {"expectations": [{"criterion": "Excellence", "weight": 0.33}]})
    return path


# ---------------------------------------------------------------------------
# Tier 2B extracted
# ---------------------------------------------------------------------------

_T2B_EXTRACTED = "docs/tier2b_topic_and_call_sources/extracted"

_SOURCE_ITEM = {
    "id": "CC1",
    "description": "Constraint 1",
    "source_section": "WP2024 §3.1",
    "source_document": "work_programme.pdf",
}


def _t2b_file(name: str) -> str:
    return f"{_T2B_EXTRACTED}/{name}"


def write_call_constraints(repo_root: Path, *, valid: bool = True) -> Path:
    path = repo_root / _t2b_file("call_constraints.json")
    if valid:
        write_json(path, [dict(_SOURCE_ITEM, id="CC1")])
    else:
        # Invalid JSON
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{invalid json content!!!", encoding="utf-8")
    return path


def write_expected_outcomes(repo_root: Path) -> Path:
    path = repo_root / _t2b_file("expected_outcomes.json")
    write_json(path, [{"id": "OUT1", "description": "Better outcomes",
                       "source_section": "WP2024 §4.1", "source_document": "work_programme.pdf"}])
    return path


def write_expected_impacts(
    repo_root: Path,
    *,
    impact_id: str = _IMPACT_ID,
) -> Path:
    path = repo_root / _t2b_file("expected_impacts.json")
    write_json(path, [{"impact_id": impact_id, "description": "Societal benefit",
                       "source_section": "WP2024 §5.1", "source_document": "work_programme.pdf"}])
    return path


def write_scope_requirements(repo_root: Path) -> Path:
    path = repo_root / _t2b_file("scope_requirements.json")
    write_json(path, [{"id": "SR1", "requirement": "Must address digital transformation",
                       "source_section": "WP2024 §2.1", "source_document": "work_programme.pdf"}])
    return path


def write_eligibility_conditions(repo_root: Path) -> Path:
    path = repo_root / _t2b_file("eligibility_conditions.json")
    write_json(path, [{"id": "EC1", "condition": "At least 3 partners",
                       "source_section": "WP2024 §1.2", "source_document": "work_programme.pdf"}])
    return path


def write_evaluation_priority_weights(repo_root: Path) -> Path:
    path = repo_root / _t2b_file("evaluation_priority_weights.json")
    write_json(path, [{"criterion": "Excellence", "weight": 0.33,
                       "source_section": "WP2024 §6.1", "source_document": "work_programme.pdf"}])
    return path


def write_all_tier2b_extracted(repo_root: Path) -> None:
    """Write all six Tier 2B extracted files with valid source refs."""
    write_call_constraints(repo_root, valid=True)
    write_expected_outcomes(repo_root)
    write_expected_impacts(repo_root)
    write_scope_requirements(repo_root)
    write_eligibility_conditions(repo_root)
    write_evaluation_priority_weights(repo_root)


def write_source_dirs(repo_root: Path) -> None:
    """Write a placeholder file in each Tier 2B source directory."""
    for subdir in (
        "docs/tier2b_topic_and_call_sources/work_programmes",
        "docs/tier2b_topic_and_call_sources/call_extracts",
        "docs/tier2a_instrument_schemas/application_forms",
        "docs/tier2a_instrument_schemas/evaluation_forms",
    ):
        d = repo_root / subdir
        d.mkdir(parents=True, exist_ok=True)
        (d / "placeholder.txt").write_text("source file", encoding="utf-8")


# ---------------------------------------------------------------------------
# Tier 4 — Phase outputs
# ---------------------------------------------------------------------------

_T4 = "docs/tier4_orchestration_state/phase_outputs"


def write_call_analysis_summary(repo_root: Path, run_id: str) -> Path:
    path = repo_root / _T4 / "phase1_call_analysis/call_analysis_summary.json"
    write_json(path, {
        "run_id": run_id,
        "phase": "phase1_call_analysis",
        "summary": "Call analysis complete",
        "extracted_files": ["call_constraints.json"],
    })
    return path


def write_concept_refinement_summary(
    repo_root: Path,
    run_id: str,
    *,
    override_run_id: str | None = None,
) -> Path:
    """
    Write ``concept_refinement_summary.json``.

    *override_run_id* allows writing a stale or inherited artifact by setting
    a different run_id in the JSON content while the file is created in the
    correct canonical location.
    """
    path = repo_root / _T4 / "phase2_concept_refinement/concept_refinement_summary.json"
    write_json(path, {
        "run_id": override_run_id if override_run_id is not None else run_id,
        "phase": "phase2_concept_refinement",
        "summary": "Concept refined and aligned with call scope",
    })
    return path


def write_wp_structure(
    repo_root: Path,
    run_id: str,
    *,
    override_run_id: str | None = None,
    wp_id: str = _WP_ID,
    task_id: str = _TASK_ID,
    deliv_id: str = _DELIV_ID,
    lead_partner: str = "P1",
    contributing_partners: list[str] | None = None,
) -> Path:
    """Write ``wp_structure.json``."""
    actual_run_id = override_run_id if override_run_id is not None else run_id
    path = repo_root / _T4 / "phase3_wp_design/wp_structure.json"
    write_json(path, {
        "run_id": actual_run_id,
        "work_packages": [
            {
                "wp_id": wp_id,
                "title": "Management and Coordination",
                "tasks": [{"task_id": task_id, "title": "Project management"}],
                "deliverables": [{"deliverable_id": deliv_id, "title": "Progress report"}],
                "lead_partner": lead_partner,
                "contributing_partners": contributing_partners or ["P2"],
            }
        ],
        "dependency_map": {wp_id: []},
    })
    return path


def write_gantt(
    repo_root: Path,
    run_id: str,
    *,
    task_id: str = _TASK_ID,
    start_month: int = 1,
    end_month: int = 12,
    duration: int = _DEFAULT_DURATION,
) -> Path:
    """Write ``gantt.json``. Set ``end_month > duration`` to trigger a timeline violation."""
    path = repo_root / _T4 / "phase4_gantt_milestones/gantt.json"
    write_json(path, {
        "run_id": run_id,
        "tasks": [
            {"task_id": task_id, "wp_id": _WP_ID, "start_month": start_month, "end_month": end_month},
        ],
        "milestones": [
            {
                "milestone_id": "M1",
                "due_month": min(end_month, duration),
                "verifiable_criterion": "First progress report delivered and accepted",
            }
        ],
        "critical_path": [task_id],
    })
    return path


def write_impact_architecture(
    repo_root: Path,
    run_id: str,
    *,
    impact_id: str = _IMPACT_ID,
    deliv_id: str = _DELIV_ID,
    include_dissemination: bool = True,
    include_exploitation: bool = True,
    include_sustainability: bool = True,
) -> Path:
    """Write ``impact_architecture.json``."""
    data: dict[str, Any] = {
        "run_id": run_id,
        "impact_pathways": [
            {
                "expected_impact_id": impact_id,
                "outputs": [deliv_id],
                "outcome": "Improved research methods",
                "impact": "Societal benefit",
            }
        ],
        "kpis": [
            {
                "kpi_id": "KPI1",
                "deliverable_id": deliv_id,
                "metric": "Number of publications",
                "target": 3,
            }
        ],
    }
    if include_dissemination:
        data["dissemination_plan"] = {"channels": ["conferences", "open access"]}
    if include_exploitation:
        data["exploitation_plan"] = {"approach": "Open access publication"}
    if include_sustainability:
        data["sustainability_mechanism"] = {"strategy": "Community open source"}

    path = repo_root / _T4 / "phase5_impact_architecture/impact_architecture.json"
    write_json(path, data)
    return path


def write_implementation_architecture(
    repo_root: Path,
    run_id: str,
    *,
    management_partner_ids: list[str] | None = None,
    include_governance: bool = True,
    include_ethics: bool = True,
    include_risk: bool = True,
    addressed_sections: list[dict] | None = None,
) -> Path:
    """Write ``implementation_architecture.json``."""
    mgmt_roles = [
        {"role": "Project Coordinator", "assigned_to": pid}
        for pid in (management_partner_ids or ["P1"])
    ]
    data: dict[str, Any] = {
        "run_id": run_id,
        "management_roles": mgmt_roles,
        "addressed_sections": addressed_sections or [
            {"section_id": "management", "status": "addressed", "section_type": "implementation"}
        ],
    }
    if include_risk:
        data["risk_register"] = [
            {
                "risk_id": "R1",
                "description": "Potential delay in data collection",
                "likelihood": "medium",
                "impact": "medium",
                "mitigation": "Build 2-month buffer into WP1 schedule",
            }
        ]
    if include_ethics:
        data["ethics_assessment"] = {
            "self_assessment_statement": "No ethical issues identified. Data collected is anonymous.",
            "involves_human_participants": False,
        }
    if include_governance:
        data["governance_matrix"] = [
            {
                "body": "Steering Committee",
                "composition": ["P1", "P2"],
                "decision_scope": "Strategic project decisions",
            }
        ]

    path = repo_root / _T4 / "phase6_implementation_architecture/implementation_architecture.json"
    write_json(path, data)
    return path


def write_budget_gate_assessment(
    repo_root: Path,
    run_id: str,
    *,
    gate_pass_declaration: str = "pass",
    blocking_inconsistencies: list[dict] | None = None,
) -> Path:
    """Write ``budget_gate_assessment.json``."""
    path = repo_root / _T4 / "phase7_budget_gate/budget_gate_assessment.json"
    write_json(path, {
        "run_id": run_id,
        "gate_pass_declaration": gate_pass_declaration,
        "blocking_inconsistencies": blocking_inconsistencies or [],
        "assessment_summary": "Budget response received and validated",
        "validated_at": "2026-01-01T12:00:00+00:00",
    })
    return path


def write_drafting_review_status(
    repo_root: Path,
    run_id: str,
    *,
    revision_actions: list[dict] | None = None,
) -> Path:
    """Write ``drafting_review_status.json``."""
    path = repo_root / _T4 / "phase8_drafting_review/drafting_review_status.json"
    default_actions = [
        {
            "action_id": "A1",
            "description": "Clarify innovation narrative",
            "severity": "major",
            "status": "resolved",
            "reason": "Addressed in revision",
        }
    ]
    write_json(path, {
        "run_id": run_id,
        "revision_actions": revision_actions if revision_actions is not None else default_actions,
    })
    return path


def write_phase8_checkpoint(repo_root: Path, *, status: str = "published") -> Path:
    """Write ``phase8_checkpoint.json`` to the checkpoints directory."""
    path = repo_root / "docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json"
    write_json(path, {"status": status, "published_at": "2026-01-01T14:00:00+00:00"})
    return path


# ---------------------------------------------------------------------------
# Tier 5 — Deliverables
# ---------------------------------------------------------------------------


def write_proposal_section(
    repo_root: Path,
    section_id: str,
    run_id: str,
    *,
    traceability_footer: list[str] | None = None,
) -> Path:
    """Write a section JSON file to ``proposal_sections/``."""
    path = repo_root / f"docs/tier5_deliverables/proposal_sections/{section_id}.json"
    write_json(path, {
        "section_id": section_id,
        "run_id": run_id,
        "content": f"Draft content for section {section_id}.",
        "traceability_footer": traceability_footer or [f"tier2b: {section_id}_constraints.json"],
    })
    return path


def write_assembled_draft(repo_root: Path, run_id: str) -> Path:
    path = repo_root / "docs/tier5_deliverables/assembled_drafts/assembled_draft.json"
    write_json(path, {
        "run_id": run_id,
        "sections": ["excellence", "impact", "implementation"],
        "assembled_at": "2026-01-01T12:00:00+00:00",
    })
    return path


def write_review_packet(
    repo_root: Path,
    run_id: str,
    *,
    findings: list[dict] | None = None,
    revision_actions: list[dict] | None = None,
) -> Path:
    """Write ``review_packet.json``."""
    path = repo_root / "docs/tier5_deliverables/review_packets/review_packet.json"
    default_findings = [
        {
            "finding_id": "F1",
            "description": "Impact section lacks KPI baselines",
            "severity": "major",
        }
    ]
    default_actions = [
        {"action_id": "RA1", "description": "Add KPI baselines", "priority": "high"}
    ]
    write_json(path, {
        "run_id": run_id,
        "findings": findings if findings is not None else default_findings,
        "revision_actions": revision_actions if revision_actions is not None else default_actions,
    })
    return path


def write_final_export(repo_root: Path, run_id: str) -> Path:
    path = repo_root / "docs/tier5_deliverables/final_exports/final_export.json"
    write_json(path, {
        "run_id": run_id,
        "export_date": "2026-01-01T16:00:00+00:00",
        "sections_included": ["excellence", "impact", "implementation"],
    })
    return path


# ---------------------------------------------------------------------------
# Integration artifacts
# ---------------------------------------------------------------------------


def write_budget_received(repo_root: Path, *, wp_ids: list[str] | None = None, partner_ids: list[str] | None = None) -> Path:
    """Write a minimal conforming budget response to ``received/``."""
    received_dir = repo_root / "docs/integrations/lump_sum_budget_planner/received"
    received_dir.mkdir(parents=True, exist_ok=True)
    response_path = received_dir / "budget_response.json"
    write_json(response_path, {
        "response_id": "BR-001",
        "schema_version": "1.0",
        "work_packages": [{"wp_id": wp_id, "lump_sum": 150000} for wp_id in (wp_ids or [_WP_ID])],
        "partners": [{"partner_id": pid, "total_effort_pm": 12} for pid in (partner_ids or ["P1", "P2"])],
    })
    return response_path


def write_budget_validation(repo_root: Path) -> Path:
    """Write a minimal validation artifact to ``validation/``."""
    val_dir = repo_root / "docs/integrations/lump_sum_budget_planner/validation"
    val_dir.mkdir(parents=True, exist_ok=True)
    val_path = val_dir / "validation_report.json"
    write_json(val_path, {
        "validated": True,
        "conforms_to_contract": True,
        "validated_at": "2026-01-01T10:00:00+00:00",
    })
    return val_path


def write_interface_contract(repo_root: Path) -> Path:
    """Write a minimal ``interface_contract.json``."""
    path = repo_root / "docs/integrations/lump_sum_budget_planner/interface_contract.json"
    write_json(path, {
        "schema_version": "1.0",
        "required_fields": ["response_id", "schema_version", "work_packages", "partners"],
    })
    return path
