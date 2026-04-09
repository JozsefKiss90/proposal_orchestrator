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

## Execution Specification

This skill has two invocation modes, determined by the agent context parameter `invocation_mode`:
- **Mode A** (`request_validation`): validate a budget request before submission to the external system.
- **Mode B** (`response_validation`): validate a budget response received from the external system and produce the budget gate assessment.

The invoking agent must provide `invocation_mode` as a context parameter. If absent or invalid: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="invocation_mode required; must be 'request_validation' or 'response_validation'") and halt.

---

### Mode A — Request Validation

#### 1. Input Validation Sequence (Mode A)

- Step A.1.1: Presence check — confirm `docs/integrations/lump_sum_budget_planner/interface_contract.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="interface_contract.json not found") and halt.
- Step A.1.2: Presence check — confirm `docs/integrations/lump_sum_budget_planner/request_templates/` exists and is non-empty. If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="request_templates/ directory is empty") and halt.

#### 2. Core Processing Logic (Mode A)

- Step A.2.1: Read `interface_contract.json`. Extract the request schema: required fields list, field types, protocol version.
- Step A.2.2: For each file in `request_templates/`: parse the file as JSON. For each required field in the contract request schema: check whether the field is present and of the correct type. Record non-conformances.
- Step A.2.3: Build the conformance result: `conformance_status` = "conforms" if all required fields are present and correctly typed; "non_conforming" if any required field is missing or incorrectly typed.
- Step A.2.4: MUST NOT read any budget figures from any source, compute any budget values, or write any budget figure to any output. Any budget numeric data that appears in the template is pass-through only; this skill validates structure, not values.

#### 3. Output Construction (Mode A)

**Budget validation artifact (e.g., `budget_validation_request_<timestamp>.json`):**
- `validation_id`: `"budget_validation_request_<ISO8601_timestamp>"`
- `validation_type`: `"request_conformance"`
- `contract_version`: from interface_contract.json version field
- `validated_file_reference`: filename of the request template validated
- `conformance_status`: "conforms" or "non_conforming"
- `non_conformance_findings`: array — each entry: `{field_name, issue_type (missing/wrong_type), contract_requirement}`
- `structural_consistency_findings`: `[]` (not applicable for Mode A)
- `timestamp`: ISO 8601

#### 4. Write Sequence (Mode A)

- Step A.4.1: Write the validation artifact to `docs/integrations/lump_sum_budget_planner/validation/<validation_id>.json`

---

### Mode B — Response Validation

#### 1. Input Validation Sequence (Mode B)

- Step B.1.1: **Received directory check** — confirm `docs/integrations/lump_sum_budget_planner/received/` exists and is non-empty (dir_non_empty). If empty or absent: this is a BLOCKING GATE FAILURE. Do not proceed to any further steps. Set `gate_pass_declaration: "fail"`, `failure_reason: "received/ directory is empty or absent — absent budget artifacts constitute a blocking gate failure per CLAUDE.md §8.4 and §13.4"`. Write budget_gate_assessment.json immediately with gate_pass_declaration: "fail". Return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="No budget response in received/; this is a blocking gate failure").
- Step B.1.2: Presence check — confirm `docs/integrations/lump_sum_budget_planner/interface_contract.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="interface_contract.json not found") and halt.
- Step B.1.3: Presence check and schema check — confirm `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` exists with `schema_id` = "orch.phase3.wp_structure.v1". If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="wp_structure.json not found") and halt.

#### 2. Core Processing Logic (Mode B)

- Step B.2.1: Read `interface_contract.json`. Extract the response schema: required fields, field types, WP coverage requirements, partner coverage requirements.
- Step B.2.2: Identify the budget response file(s) in `received/`. If multiple files: use the most recently dated file. Record the filename as `budget_response_reference`.
- Step B.2.3: Parse the budget response file as JSON. For each required field in the contract response schema: check whether the field is present and of the correct type. Build `non_conformance_findings`.
- Step B.2.4: If the response does not conform to the interface contract schema (any required field missing or wrong type): set `conformance_status: "non_conforming"`. This is a blocking inconsistency.
- Step B.2.5: Build the **WP coverage check**: extract all `wp_id` values from `wp_structure.json work_packages[]`. For each wp_id: check whether a corresponding budget line entry exists in the budget response (by matching the wp_id field or equivalent identifier in the response). Build `wp_coverage_results`: for each wp_id: `{ wp_id, present_in_budget: boolean, budget_line_reference: string or null, inconsistencies: [] }`. If `present_in_budget` is false: add `"WP not found in budget response"` to the inconsistencies array.
- Step B.2.6: Build the **partner coverage check**: extract all `partner_id` values from `wp_structure.json partner_role_matrix[]`. For each partner_id: check whether a corresponding budget allocation entry exists in the budget response. Build `partner_coverage_results`: for each partner_id: `{ partner_id, present_in_budget: boolean, budget_line_reference: string or null, inconsistencies: [] }`. If `present_in_budget` is false: add `"Partner not found in budget response"` to inconsistencies.
- Step B.2.7: Build `blocking_inconsistencies` array: collect all unresolved issues where `severity: "blocking"`. These include: contract non-conformance, any WP not found in budget, any partner not found in budget. Non-blocking findings (format issues, optional field absence) are recorded with `severity: "non_blocking"`.
- Step B.2.8: Determine `gate_pass_declaration`: "pass" if AND ONLY IF all of the following hold: (1) received/ is non-empty, (2) response conforms to interface contract, (3) no blocking_inconsistencies with resolution: "unresolved" exist. Otherwise: "fail".
- Step B.2.9: MUST NOT read, record, compute, estimate, or write any numeric budget value. The skill checks structural coverage only. Any budget figures in the response are pass-through; they are not read or recorded in any output field.

#### 3. Output Construction (Mode B)

**Budget validation artifact (e.g., `budget_validation_response_<timestamp>.json`):**
- `validation_id`: `"budget_validation_response_<ISO8601_timestamp>"`
- `validation_type`: `"response_conformance"`
- `contract_version`: from interface_contract.json
- `validated_file_reference`: filename of the budget response file
- `conformance_status`: "conforms" or "non_conforming"
- `non_conformance_findings`: array from Step B.2.3
- `structural_consistency_findings`: consolidated list of all coverage issues from Steps B.2.5 and B.2.6
- `timestamp`: ISO 8601

**`budget_gate_assessment.json`:**
- `schema_id`: set to "orch.phase7.budget_gate_assessment.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `gate_pass_declaration`: derived from Step B.2.8 — "pass" or "fail"
- `budget_response_reference`: derived from Step B.2.2 — filename in received/
- `validation_artifact_reference`: filename of the validation artifact written to validation/
- `wp_coverage_results`: derived from Step B.2.5 — array of `{wp_id, present_in_budget, budget_line_reference, inconsistencies[]}`
- `partner_coverage_results`: derived from Step B.2.6 — array of `{partner_id, present_in_budget, budget_line_reference, inconsistencies[]}`
- `blocking_inconsistencies`: derived from Step B.2.7 — array of `{inconsistency_id, description, severity, resolution, resolution_note}`

### 4. Conformance Stamping (Mode B)

- `schema_id`: set to "orch.phase7.budget_gate_assessment.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence (Mode B)

- Step B.5.1: Write validation artifact to `docs/integrations/lump_sum_budget_planner/validation/<validation_id>.json`
- Step B.5.2: Create directory `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/` if not present.
- Step B.5.3: Write `budget_gate_assessment.json` to `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json`

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
