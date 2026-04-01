"""
Upstream required input paths for gate freshness checking.

Maps gate_id → list of artifact paths whose modification times are checked
against the gate result's evaluated_at timestamp in gate_pass_recorded.

If any listed artifact exists and its mtime is strictly later than the gate
result's evaluated_at, the gate result is considered stale and the predicate
fails with STALE_UPSTREAM_MISMATCH.

Paths are relative to the repository root. Pass repo_root to resolve them;
if repo_root is None, they are resolved relative to the current working
directory (see runner.paths.resolve_repo_path).

Directory paths are included where a phase consumed a directory of source
documents rather than a single canonical file. The directory's own mtime
(which changes on add/remove/rename of direct children) is used. This does
not perform a recursive scan.

This table reflects the required_inputs described in CLAUDE.md §7 (Phase
Definitions and Gate Conditions) and the artifact_registry in
manifest.compile.yaml.
"""

UPSTREAM_REQUIRED_INPUTS: dict[str, list[str]] = {

    # entry gate for n01 — checks sources are present before Phase 1 starts
    "gate_01_source_integrity": [
        "docs/tier3_project_instantiation/call_binding/selected_call.json",
        "docs/tier2b_topic_and_call_sources/work_programmes",
        "docs/tier2b_topic_and_call_sources/call_extracts",
    ],

    # exit gate for n01 — Phase 1 consumed call binding + Tier 2B source dirs
    "phase_01_gate": [
        "docs/tier3_project_instantiation/call_binding/selected_call.json",
        "docs/tier2b_topic_and_call_sources/work_programmes",
        "docs/tier2b_topic_and_call_sources/call_extracts",
    ],

    # exit gate for n02 — Phase 2 consumed Phase 1 output + project brief dir
    "phase_02_gate": [
        "docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json",
        "docs/tier3_project_instantiation/project_brief",
    ],

    # exit gate for n03 — Phase 3 consumed Phase 2 output + WP and objectives seeds
    "phase_03_gate": [
        "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
        "docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json",
        "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
    ],

    # exit gate for n04 — Phase 4 consumed Phase 3 output + call duration + consortium roles
    "phase_04_gate": [
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
        "docs/tier3_project_instantiation/call_binding/selected_call.json",
        "docs/tier3_project_instantiation/consortium/roles.json",
    ],

    # exit gate for n05 — Phase 5 consumed Phase 2 output + impact seeds + Tier 2B extracts
    "phase_05_gate": [
        "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
        "docs/tier3_project_instantiation/architecture_inputs/outcomes.json",
        "docs/tier3_project_instantiation/architecture_inputs/impacts.json",
        "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json",
        "docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json",
    ],

    # exit gate for n06 — Phase 6 consumed Phases 3+4+5 outputs + consortium + risks
    "phase_06_gate": [
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
        "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json",
        "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json",
        "docs/tier3_project_instantiation/consortium/partners.json",
        "docs/tier3_project_instantiation/architecture_inputs/risks.json",
        "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
    ],

    # exit gate for n07 — Phase 7 consumed Phases 3+4+6 outputs + integration dirs
    "gate_09_budget_consistency": [
        "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json",
        "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json",
        "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json",
        "docs/integrations/lump_sum_budget_planner/received",
        "docs/integrations/lump_sum_budget_planner/validation",
    ],

    # exit gate for n08b — Phase 8b consumed Phase 7 output + drafted sections dir
    "gate_10_part_b_completeness": [
        "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json",
        "docs/tier5_deliverables/proposal_sections",
    ],

    # exit gate for n08c — Phase 8c consumed assembled draft + proposal sections dir
    "gate_11_review_closure": [
        "docs/tier5_deliverables/assembled_drafts/assembled_draft.json",
        "docs/tier5_deliverables/proposal_sections",
    ],

    # exit gate for n08d — Phase 8d consumed review packet + assembled draft + status
    "gate_12_constitutional_compliance": [
        "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json",
        "docs/tier5_deliverables/assembled_drafts/assembled_draft.json",
        "docs/tier5_deliverables/review_packets/review_packet.json",
    ],
}
