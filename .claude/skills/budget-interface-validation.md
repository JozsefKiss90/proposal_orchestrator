---
skill_id: budget-interface-validation
purpose_summary: >
  Validate budget request conformance to the interface contract before submission,
  and validate budget response conformance and structural consistency upon receipt,
  producing validation artifacts.
used_by_agents:
  - budget_interface_coordinator
  - budget_gate_validator
reads_from:
  - docs/integrations/lump_sum_budget_planner/interface_contract.json
  - docs/integrations/lump_sum_budget_planner/request_templates/
  - docs/integrations/lump_sum_budget_planner/received/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/integrations/lump_sum_budget_planner/validation/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
constitutional_constraints:
  - "Must not generate or estimate budget figures"
  - "Must not accept a response that does not conform to the interface contract"
  - "Must not declare the budget gate passed if blocking inconsistencies exist"
  - "Must not treat absent response as a non-failing state"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/integrations/lump_sum_budget_planner/interface_contract.json` | interface_contract.json — integration schema authority | Request schema definition; response schema definition; required fields list; validation rules; protocol version | N/A — integration contract document | The binding structural authority for both request and response conformance; all validation is performed against this contract |
| `docs/integrations/lump_sum_budget_planner/request_templates/` | Budget request templates directory | Template structure; required request fields; WP-level effort request fields; partner-level cost fields | N/A — integration template directory | Provides the structural template for budget request preparation; requests must conform to these templates before submission |
| `docs/integrations/lump_sum_budget_planner/received/` | Externally supplied budget response files | Full budget response content; WP budget line entries; partner effort entries; total amounts per WP | N/A — external integration inbound directory (dir_non_empty check required) | The externally received budget response that must be validated for interface contract conformance and structural consistency with wp_structure.json; absent directory content is a blocking gate failure |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].wp_id; partner_role_matrix[].partner_id, wps_as_lead; work_packages[].deliverables[].deliverable_id | `orch.phase3.wp_structure.v1` | Provides the WP list and partner roles that the budget response must cover; used for structural consistency checking (every WP in wp_structure must appear in the budget response) |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/integrations/lump_sum_budget_planner/validation/` | Budget validation artifact file (e.g., `budget_validation_<timestamp>.json`) | N/A — integration validation artifact | validation_id; validation_type: request_conformance or response_conformance; contract_version; validated_file_reference; conformance_status: conforms/non_conforming; non_conformance_findings array; structural_consistency_findings array; timestamp | No — integration validation artifact | conformance_status derived from comparing received/ budget response against interface_contract.json schema; structural_consistency_findings derived from comparing budget response WP/partner entries against wp_structure.json |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | budget_gate_assessment.json | `orch.phase7.budget_gate_assessment.v1` | schema_id, run_id, gate_pass_declaration[pass/fail], budget_response_reference (filename in received/), validation_artifact_reference (filename in validation/), wp_coverage_results (array: wp_id, present_in_budget boolean, budget_line_reference, inconsistencies per WP), partner_coverage_results (array: partner_id, present_in_budget boolean, budget_line_reference, inconsistencies per partner), blocking_inconsistencies (array: inconsistency_id, description, severity[blocking/non_blocking], resolution[resolved/unresolved], resolution_note) | Yes | gate_pass_declaration derived from: response present in received/ AND conforms to interface contract AND no blocking inconsistencies; all other fields derived from structural consistency check of received response against wp_structure.json |

**Note:** `artifact_status` must be ABSENT at write time for budget_gate_assessment.json; the runner stamps it post-gate. If the received/ directory is empty, gate_pass_declaration must be "fail" — this is a blocking gate failure with hard_block: true per the gate result schema. This skill must never generate, estimate, or invent any budget figures.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/integrations/lump_sum_budget_planner/validation/` | Yes — artifact_id: a_int_budget_validation | n07_budget_gate |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | Yes — artifact_id: a_t4_phase7 (directory); canonical file within that directory | n07_budget_gate |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
