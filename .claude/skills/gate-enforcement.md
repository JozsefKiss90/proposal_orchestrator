---
skill_id: gate-enforcement
purpose_summary: >
  Evaluate whether a phase gate condition is met, declare pass or failure, write
  the gate status to Tier 4, and block downstream phases if the gate has not passed.
used_by_agents:
  - call_analyzer
  - wp_designer
  - gantt_designer
  - impact_architect
  - implementation_architect
  - budget_gate_validator
  - proposal_writer
  - revision_integrator
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier3_project_instantiation/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Gate conditions are defined in this workflow and in CLAUDE.md; they must not be weakened"
  - "Gate failure must be declared explicitly; fabricated completion is a constitutional violation"
  - "A gate cannot be declared passed without confirming all gate conditions"
---

## Canonical Inputs and Outputs

### Inputs

This skill is phase-context-driven. The specific canonical artifact read from `docs/tier4_orchestration_state/phase_outputs/` depends on the invoking agent and the gate being evaluated. The table below shows the mapping:

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/<phase_dir>/<canonical_artifact>.json` | The phase-specific canonical artifact for the gate being evaluated (see gate-to-artifact mapping below) | All required fields for the gate condition predicates (schema_id, run_id, phase-specific mandatory fields) | Phase-dependent (see mapping) | The primary artifact whose gate conditions are evaluated; the gate declares pass only when all deterministic and semantic predicates are satisfied |
| `docs/tier3_project_instantiation/` | Tier 3 project data (context-dependent: partners.json, selected_call.json, compliance_profile.json) | partner_id values; project_duration_months; selected instrument type | N/A — Tier 3 source directory (semantic scope root) | Provides reference data for cross-artifact consistency predicates (e.g., all_partners_in_tier3, timeline_within_duration) |

**Gate-to-artifact mapping (reads_from context):**

| Invoking Agent | Gate | Canonical Artifact Read | Schema ID |
|----------------|------|------------------------|-----------|
| call_analyzer | phase_01_gate | `phase1_call_analysis/call_analysis_summary.json` | `orch.phase1.call_analysis_summary.v1` |
| wp_designer | phase_03_gate | `phase3_wp_design/wp_structure.json` | `orch.phase3.wp_structure.v1` |
| gantt_designer | phase_04_gate | `phase4_gantt_milestones/gantt.json` | `orch.phase4.gantt.v1` |
| impact_architect | phase_05_gate | `phase5_impact_architecture/impact_architecture.json` | `orch.phase5.impact_architecture.v1` |
| implementation_architect | phase_06_gate | `phase6_implementation_architecture/implementation_architecture.json` | `orch.phase6.implementation_architecture.v1` |
| budget_gate_validator | gate_09_budget_consistency | `phase7_budget_gate/budget_gate_assessment.json` | `orch.phase7.budget_gate_assessment.v1` |
| proposal_writer | gate_10_part_b_completeness | `phase8_drafting_review/drafting_review_status.json` | `orch.phase8.drafting_review_status.v1` |
| revision_integrator | gate_11_review_closure, gate_12_constitutional_compliance | `phase8_drafting_review/drafting_review_status.json` | `orch.phase8.drafting_review_status.v1` |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/<phase_dir>/gate_result.json` (or gate_01_result.json, gate_10_result.json, gate_11_result.json, gate_12_result.json per canonical_paths in artifact_schema_specification.yaml) | GateResult artifact — written by the runner | `orch.gate_result.v1` | schema_id, gate_id, gate_kind[entry/exit], run_id, manifest_version, library_version, constitution_version, input_fingerprint (SHA-256 over required inputs), input_artifact_fingerprints (map path→hash), evaluated_at (ISO 8601), repo_root, status[pass/fail], hard_block (boolean, only for gate_09 absent-response failure), deterministic_predicates.passed[], deterministic_predicates.failed[] (predicate_id, type, function, args, failure_category, fail_message, prose_condition), semantic_predicates.passed[], semantic_predicates.failed[] (predicate_id, function, agent, constitutional_rule, findings[claim, violated_rule, evidence_path, severity]) | Yes | status derived from evaluation of all gate predicates; input_fingerprint computed from canonical artifact content; failure details enumerated per predicate |
| `docs/tier4_orchestration_state/decision_log/` | Gate failure decision log entry (when gate fails and the failure reason is material to future interpretation) | N/A — decision log entry | decision_id; decision_type: "gate_failure"; gate_id; failure_reason; predicates_failed list; resolution_required boolean; timestamp | No | Derived from gate evaluation output when gate status is "fail"; documents the failure for durable traceability |

**Note:** Gate result files are runner-written, not agent-written in the ordinary sense. The gate-enforcement skill prepares the evaluation; the runner writes the GateResult artifact. A gate failure is a valid and correct output. Fabricating a pass when gate conditions are not met is a constitutional violation (CLAUDE.md §13.7, §15).

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json` | Yes — canonical_paths.phase_01_gate in artifact_schema_specification.yaml | n01_call_analysis (runner) |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json` | Yes — canonical_paths.phase_03_gate | n03_wp_design (runner) |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gate_result.json` | Yes — canonical_paths.phase_04_gate | n04_gantt_milestones (runner) |
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json` | Yes — canonical_paths.phase_05_gate | n05_impact_architecture (runner) |
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/gate_result.json` | Yes — canonical_paths.phase_06_gate | n06_implementation_architecture (runner) |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/gate_result.json` | Yes — canonical_paths.gate_09_budget_consistency | n07_budget_gate (runner) |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10_result.json` | Yes — canonical_paths.gate_10_part_b_completeness | n08 nodes (runner) |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_11_result.json` | Yes — canonical_paths.gate_11_review_closure | n08 nodes (runner) |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_12_result.json` | Yes — canonical_paths.gate_12_constitutional_compliance | n08 nodes (runner) |
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent) |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
