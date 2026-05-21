"""
Canonical gate result paths (§6.3 of artifact_schema_specification.yaml).

Keys: gate_id strings matching gate_rules_library.yaml.
Values: paths relative to tier4_root (the docs/tier4_orchestration_state/
        directory in the live repository).

To construct an absolute gate result path:
    Path(tier4_root) / GATE_RESULT_PATHS[gate_id]

The full repo-relative equivalents (for documentation) are:
    docs/tier4_orchestration_state/ + GATE_RESULT_PATHS[gate_id]

This table is the authoritative runtime source for gate result path resolution.
It must remain consistent with §6.3 of artifact_schema_specification.yaml.
Any amendment to that section requires a corresponding update here.
"""

GATE_RESULT_PATHS: dict[str, str] = {
    # entry gate for n01 — evaluated before Phase 1 begins
    "gate_01_source_integrity": (
        "phase_outputs/phase1_call_analysis/gate_01_result.json"
    ),
    # exit gate for n01
    "phase_01_gate": (
        "phase_outputs/phase1_call_analysis/gate_result.json"
    ),
    # exit gate for n02
    "phase_02_gate": (
        "phase_outputs/phase2_concept_refinement/gate_result.json"
    ),
    # exit gate for n03
    "phase_03_gate": (
        "phase_outputs/phase3_wp_design/gate_result.json"
    ),
    # exit gate for n04
    "phase_04_gate": (
        "phase_outputs/phase4_gantt_milestones/gate_result.json"
    ),
    # exit gate for n05
    "phase_05_gate": (
        "phase_outputs/phase5_impact_architecture/gate_result.json"
    ),
    # exit gate for n06
    "phase_06_gate": (
        "phase_outputs/phase6_implementation_architecture/gate_result.json"
    ),
    # exit gate for n07 (mandatory/bypass_prohibited)
    "gate_09_budget_consistency": (
        "phase_outputs/phase7_budget_gate/gate_result.json"
    ),
    # exit gate for n08a (Excellence section completeness)
    "gate_10a_excellence_completeness": (
        "phase_outputs/phase8_drafting_review/gate_10a_result.json"
    ),
    # exit gate for n08b (Impact section completeness)
    "gate_10b_impact_completeness": (
        "phase_outputs/phase8_drafting_review/gate_10b_result.json"
    ),
    # exit gate for n08c (Implementation section completeness)
    "gate_10c_implementation_completeness": (
        "phase_outputs/phase8_drafting_review/gate_10c_result.json"
    ),
    # exit gate for n08d (Cross-section consistency)
    "gate_10d_cross_section_consistency": (
        "phase_outputs/phase8_drafting_review/gate_10d_result.json"
    ),
    # exit gate for n08e
    "gate_11_review_closure": (
        "phase_outputs/phase8_drafting_review/gate_11_result.json"
    ),
    # exit gate for n08f
    "gate_12_constitutional_compliance": (
        "phase_outputs/phase8_drafting_review/gate_12_result.json"
    ),
}
