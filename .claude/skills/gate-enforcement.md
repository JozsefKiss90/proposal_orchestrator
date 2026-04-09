---
skill_id: gate-enforcement
purpose_summary: >
  Evaluate all deterministic and semantic predicates for a named phase gate against
  the canonical phase artifact, and return a structured predicate evaluation summary
  as a SkillResult payload to the invoking agent. The runner — not this skill —
  writes the GateResult artifact and declares gate pass or fail.
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
| SkillResult payload (in-memory — returned to invoking agent, not written to disk by this skill) | Predicate evaluation summary — passed to invoking agent, which forwards it to the runner; the runner writes the GateResult artifact | N/A — SkillResult payload | gate_id, overall_status (pass/fail), deterministic_predicates.passed[], deterministic_predicates.failed[] (predicate_id, type, function, args, failure_category, fail_message, prose_condition), semantic_predicates.passed[], semantic_predicates.failed[] (predicate_id, function, agent, constitutional_rule, findings[]), hard_block (boolean — only for gate_09 absent-response failure), evaluated_at (ISO 8601) | Yes — run_id in payload | overall_status derived from Step 2.4; predicate detail arrays from Steps 2.1–2.3; forwarded by invoking agent to runner, which constructs and writes the GateResult artifact at the canonical_path from artifact_schema_specification.yaml |
| `docs/tier4_orchestration_state/decision_log/` | Gate failure decision log entry (written by this skill ONLY when overall_status is "fail" and the failure is material to future interpretation) | N/A — decision log entry | decision_id; decision_type: "gate_failure"; gate_id; failure_reason; predicates_failed list; tier_authority_applied (referencing CLAUDE.md §6 and §7 gate condition rules); resolution_required boolean; timestamp | No | Derived from predicate evaluation when overall_status is "fail"; provides durable traceability of the failure |

**Note:** GateResult artifacts (gate_result.json and its named variants) are written exclusively by the DAG scheduler runner, not by this skill. This skill evaluates predicates and returns the predicate evaluation summary as a SkillResult payload. The invoking agent forwards this payload to the runner, which constructs the GateResult with schema_id "orch.gate_result.v1", computes input_fingerprint, and writes to the canonical path. A gate failure is a valid and correct output. Fabricating a pass when gate conditions are not met is a constitutional violation (CLAUDE.md §13.7, §15).

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| SkillResult payload (in-memory, not a file) | Not applicable — payload forwarded by invoking agent to runner; runner writes the GateResult file | This skill (predicate evaluation only) |
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent) |

**GateResult files are runner-owned artifacts, not skill outputs.** The canonical paths for gate result files (phase_01_gate, phase_03_gate, phase_04_gate, phase_05_gate, phase_06_gate, gate_09_budget_consistency, gate_10_part_b_completeness, gate_11_review_closure, gate_12_constitutional_compliance) are defined in artifact_schema_specification.yaml and written by the DAG scheduler runner after receiving the predicate evaluation summary from the invoking agent.

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Confirm the invoking agent provides `gate_id` as a context parameter (e.g., "phase_01_gate", "gate_09_budget_consistency"). If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="gate_id required; invoking agent must specify which gate to evaluate") and halt.
- Step 1.2: Look up the gate_id in the gate-to-artifact mapping below. If the gate_id is not in the mapping: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="gate_id '<gate_id>' not recognised") and halt.
- Step 1.3: Identify the canonical artifact path for this gate from the mapping. Confirm the canonical artifact exists. If absent: proceed to Step 2 with `artifact_present = false` (the gate will fail on presence predicate).
- Step 1.4: If the canonical artifact exists: confirm its `schema_id` matches the expected value from the mapping. If schema_id does not match: record a predicate failure for `schema_id_match`; continue evaluation (do not halt; gate result will be "fail").

**Gate-to-artifact mapping (canonical artifacts per gate):**

| gate_id | Canonical Artifact Path | Expected schema_id |
|---------|------------------------|-------------------|
| gate_01_source_integrity | (entry gate — validated by dir_non_empty checks on source directories) | N/A |
| phase_01_gate | `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | `orch.phase1.call_analysis_summary.v1` |
| phase_02_gate | `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | `orch.phase2.concept_refinement_summary.v1` |
| phase_03_gate | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | `orch.phase3.wp_structure.v1` |
| phase_04_gate | `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | `orch.phase4.gantt.v1` |
| phase_05_gate | `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | `orch.phase5.impact_architecture.v1` |
| phase_06_gate | `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | `orch.phase6.implementation_architecture.v1` |
| gate_09_budget_consistency | `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | `orch.phase7.budget_gate_assessment.v1` |
| gate_10_part_b_completeness | `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` | `orch.phase8.drafting_review_status.v1` |
| gate_11_review_closure | `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` | `orch.phase8.drafting_review_status.v1` |
| gate_12_constitutional_compliance | `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` | `orch.phase8.drafting_review_status.v1` |

### 2. Core Processing Logic

- Step 2.1: Evaluate **deterministic predicates** for the gate_id. Deterministic predicates are structural checks that have a definite true/false result from reading artifact fields. Apply the following checks per gate:

  **For all gates with a canonical artifact:**
  - `artifact_present`: artifact exists at canonical path — true/false.
  - `schema_id_match`: `artifact.schema_id` equals expected value — true/false.
  - `run_id_match`: `artifact.run_id` equals the current `run_id` provided by the invoking agent — true/false.
  - `artifact_not_invalid`: `artifact.artifact_status` is absent or not equal to "invalid" — true/false.

  **Gate-specific deterministic predicates:**
  - `phase_01_gate`: `evaluation_matrix` is non-empty object; `compliance_checklist` is non-empty array; `resolved_instrument_type` is non-empty string.
  - `phase_02_gate`: `topic_mapping_rationale` is non-empty object; `scope_conflict_log` is an array; `strategic_differentiation` is non-empty string; all entries in `topic_mapping_rationale` have non-empty `tier2b_source_ref` and `tier3_evidence_ref`.
  - `phase_03_gate`: `work_packages` is non-empty array; every WP has `deliverables` non-empty; every WP has `lead_partner` non-null; `dependency_map` is non-null with `nodes` and `edges` arrays; `cycle_detected` is false (cycle_detected: true = predicate failure); `partner_role_matrix` is non-empty.
  - `phase_04_gate`: `tasks` is non-empty array; every task has `start_month` and `end_month` non-null; every task's `end_month` ≤ project_duration_months (from selected_call.json); `milestones` is non-empty array; every milestone has `due_month` and `verifiable_criterion` non-empty; `critical_path` is non-empty array.
  - `phase_05_gate`: `impact_pathways` is non-empty array; every `expected_impact_id` from `expected_impacts.json` appears in at least one pathway; every pathway's `project_outputs` array is non-empty; `kpis` is non-empty; every KPI's `traceable_to_deliverable` is a valid deliverable_id from wp_structure.json; `dissemination_plan` is non-null; `exploitation_plan` is non-null; `sustainability_mechanism` is non-null.
  - `phase_06_gate`: `risk_register` is non-empty array; every risk entry has non-null `likelihood`, `impact`, `mitigation`; `ethics_assessment` is non-null; `ethics_assessment.self_assessment_statement` is non-empty; `governance_matrix` is non-empty; every `management_roles` entry has `assigned_to` that exists in Tier 3 partners.json; `instrument_sections_addressed` is non-empty array.
  - `gate_09_budget_consistency`: `gate_pass_declaration` equals "pass"; `budget_response_reference` non-empty; `validation_artifact_reference` non-empty; no entry in `blocking_inconsistencies` has `resolution: "unresolved"`.
  - `gate_10_part_b_completeness`: `section_completion_log` non-empty; all mandatory sections from section_schema_registry.json have an entry; `revision_actions` array exists.
  - `gate_11_review_closure`: all entries in `revision_actions` are present; review packet exists at canonical path.
  - `gate_12_constitutional_compliance`: all critical `revision_actions` have `status: "resolved"` OR have `reason` non-empty; final_export.json exists at canonical path; `revision_log` is non-empty.

- Step 2.2: Evaluate **semantic predicates** for the gate_id. Semantic predicates require agent judgment over artifact content. Apply the following per gate:
  - `phase_01_gate`: semantic_pred — `no_generic_programme_knowledge_substitution`: all call requirement claims in the artifact reference named Tier 2B source files, not generic programme knowledge.
  - `phase_02_gate`: semantic_pred — `no_unresolved_scope_conflicts`: `scope_conflict_log` contains no entries with `resolution_status: "unresolved"`.
  - `phase_03_gate`: semantic_pred — `all_partners_in_tier3`: every `lead_partner` and `contributing_partners` value across all WPs exists as a `partner_id` in Tier 3 partners.json.
  - `phase_05_gate`: semantic_pred — `no_generic_impact_language`: every pathway's `impact_narrative` is project-specific (not boilerplate like "the project will have a positive impact on society").
  - `phase_06_gate`: semantic_pred — `instrument_sections_complete`: all sections in `instrument_sections_addressed` that correspond to mandatory sections from section_schema_registry.json have `status: "addressed"` (not "deferred" without reason).
  - `gate_09_budget_consistency`: semantic_pred — `no_internal_budget_figures`: no budget numeric values appear in the assessment beyond those received from the external system.
  - `gate_12_constitutional_compliance`: semantic_pred — `no_constitutional_violations`: compliance reports in validation_reports/ for this run show no critical violations.

- Step 2.3: Compile the full predicate evaluation:
  - `deterministic_predicates.passed`: list of predicate_ids that passed.
  - `deterministic_predicates.failed`: list of predicate_ids that failed, each with `failure_category` and `fail_message`.
  - `semantic_predicates.passed`: list of semantic predicate_ids that passed.
  - `semantic_predicates.failed`: list that failed, each with findings.
- Step 2.4: Determine overall gate `status`:
  - If ALL deterministic and semantic predicates pass: `status: "pass"`.
  - If ANY predicate fails: `status: "fail"`. Gate failure is a valid and correct output. Never declare "pass" when any predicate fails.
  - Special case for `gate_09_budget_consistency`: if `received/` directory is absent or empty: `status: "fail"`, `hard_block: true`.

### 3. Output Construction

**Predicate evaluation summary (SkillResult payload — returned to invoking agent, NOT written to disk by this skill):**

This skill returns a SkillResult with the following payload. The invoking agent forwards this payload to the DAG scheduler runner, which constructs and writes the GateResult artifact.

- `gate_id`: the gate_id evaluated
- `overall_status`: "pass" if ALL deterministic and semantic predicates passed; "fail" if ANY predicate failed — derived from Step 2.4
- `hard_block`: boolean — true only when gate_09_budget_consistency and `received/` directory is absent or empty; false in all other cases
- `evaluated_at`: ISO 8601 timestamp of evaluation
- `run_id`: copied from invoking agent's run_id parameter
- `deterministic_predicates.passed`: array of predicate_ids that passed
- `deterministic_predicates.failed`: array of `{predicate_id, type, function, args, failure_category, fail_message, prose_condition}` for each failing predicate
- `semantic_predicates.passed`: array of semantic predicate_ids that passed
- `semantic_predicates.failed`: array of `{predicate_id, function, agent, constitutional_rule, findings[claim, violated_rule, evidence_path, severity]}` for each failing semantic predicate

The runner uses this payload to construct the GateResult artifact with schema_id "orch.gate_result.v1", adds input_fingerprint, input_artifact_fingerprints, manifest_version, library_version, constitution_version, repo_root, and gate_kind, then writes to the canonical path from artifact_schema_specification.yaml `gate_result_schema.canonical_paths.<gate_id>`.

**Decision log entry (written by this skill ONLY when overall_status is "fail"):**
- `decision_id`: `"gate_failure_<gate_id>_<agent_id>_<ISO8601_timestamp>"`
- `decision_type`: `"gate_failure"`
- `gate_id`: the gate_id
- `failure_reason`: summary of all failed predicates
- `predicates_failed`: array of failed predicate_ids
- `tier_authority_applied`: `"CLAUDE.md §6 (phase gate conditions are mandatory), §7 (phase-specific gate definitions), §12.4 (missing mandatory inputs trigger gate failure), §15 (prefer explicit gate failure over fabricated completion)"`
- `resolution_required`: true
- `timestamp`: ISO 8601

### 4. Conformance Stamping

This skill does not write the GateResult artifact and therefore does not apply conformance stamping to it. Conformance stamping of GateResult artifacts (setting schema_id, run_id, input_fingerprint, evaluated_at) is performed exclusively by the DAG scheduler runner after receiving the predicate evaluation summary payload from the invoking agent.

The decision log entry written by this skill (when overall_status is "fail") does not carry schema_id or artifact_status — decision log entries are not canonical phase output artifacts.

### 5. Write Sequence

- Step 5.1: Return the predicate evaluation summary as the SkillResult payload to the invoking agent. This is the primary output of this skill. The payload is an in-memory return value; this skill does not write it to disk.
- Step 5.2: If overall_status is "fail": write the decision log entry to `docs/tier4_orchestration_state/decision_log/<decision_id>.json`.
- Step 5.3: Do NOT write gate_result.json or any named gate result variant (gate_01_result.json, gate_10_result.json, gate_11_result.json, gate_12_result.json). These are runner-owned artifacts written by the DAG scheduler after receiving the SkillResult payload via the invoking agent.

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
