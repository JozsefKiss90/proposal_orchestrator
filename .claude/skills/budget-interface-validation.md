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

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Must not generate or estimate budget figures"

**Decision point in execution logic:** Steps A.2.4 (Mode A) and B.2.9 (Mode B) — the active prohibition on reading, recording, computing, estimating, or writing any numeric budget value.

**Exact failure condition:** Any numeric budget value (cost, person-months, amount in any currency, estimated budget allocation) that does NOT originate verbatim from the `received/` budget response file is written to any skill output artifact. This includes: computing a budget figure by arithmetic from other figures, estimating a missing value, defaulting to a prior budget figure from agent memory, or filling in a missing budget line with an assumed value.

**Enforcement mechanism — explicit allowed/forbidden boundary:**

ALLOWED:
- Reading structural keys from the budget response: wp_id, partner_id, field names, presence/absence of entries
- Checking whether a WP or partner identifier is present or absent in the response
- Passing through non-numeric identifier strings (e.g., wp_id values, partner_id values)

FORBIDDEN (triggers CONSTITUTIONAL_HALT):
- Computing any numeric value (sum, average, ratio, allocation, person-month count, cost)
- Estimating a missing numeric value
- Copying any numeric amount from the budget response into any output artifact field
- Writing any currency amount, numeric budget figure, person-month count, or cost figure to any output
- Referencing a numeric amount in a validation finding or assessment field

DETERMINISTIC RULE:
IF any numeric value (integer or float representing a cost, amount, or effort) is present in any output artifact written by this skill:
→ CONSTITUTIONAL_HALT immediately
→ Reason: numeric budget values must not be materialized, stored, or written to any output artifact
→ return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Numeric budget value <value> was generated/estimated internally; this skill must not compute, estimate, or invent budget figures per CLAUDE.md §8.1, §8.3, and §13.3")
→ No output written

The check applies at write time: before writing any output field, verify no numeric budget value has been included. This applies to both Mode A and Mode B outputs.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No validation artifact or budget_gate_assessment.json written.

**Hard failure confirmation:** Yes — unconditional halt; budget figure generation is a categorical prohibition with no exceptions.

**CLAUDE.md §13 cross-reference:** §8.1 — "This repository does not compute, estimate, or generate lump-sum budgets." §8.3 — "No agent may invent, substitute, approximate, or silently generate budget figures." §13.3 (analogous) — budget figures not received from the external system are fabricated project facts.

---

### Constraint 2: "Must not accept a response that does not conform to the interface contract"

**Decision point in execution logic:** Steps B.2.3 and B.2.4 (Mode B) — at the point the budget response is parsed for schema conformance against `interface_contract.json`.

**Exact failure condition:** The budget response file in `received/` does not conform to the interface contract (any required field missing or of wrong type per the contract schema), AND the skill writes `conformance_status: "conforms"` to the validation artifact; OR the skill does not write a blocking inconsistency entry for the non-conformance; OR the skill proceeds to build a passing budget_gate_assessment despite non-conformance.

**Enforcement mechanism:** In Step B.2.4: if `conformance_status: "non_conforming"`, this MUST be added to `blocking_inconsistencies` with `severity: "blocking"`. The non-conformance check is a necessary condition for gate_pass_declaration: "pass" — a non-conforming response means `gate_pass_declaration` MUST be "fail". The skill must not write `conformance_status: "conforms"` unless every required field is present and of the correct type as specified in the interface contract. Any logic that skips or downgrades a non-conformance finding to non-blocking is a constitutional violation: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Non-conforming budget response accepted as conforming; this violates the interface contract and CLAUDE.md §8.5"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT") for false-conformance case. For correctly detected non-conformance: blocking_inconsistency recorded, gate_pass_declaration: "fail" — this is the correct and constitutional outcome (not a SkillResult failure).

**Hard failure confirmation:** Yes — falsely accepting a non-conforming response is a constitutional violation; correctly identifying non-conformance and declaring gate failure is the required behavior.

**CLAUDE.md §13 cross-reference:** §8.5 — "The interface contract at docs/integrations/lump_sum_budget_planner/interface_contract.json defines the schema and exchange protocol for budget requests and responses. Responses that do not conform to the interface contract must be rejected and flagged, not silently accepted."

---

### Constraint 3: "Must not declare the budget gate passed if blocking inconsistencies exist"

**Decision point in execution logic:** Step B.2.8 — at the point `gate_pass_declaration` is set.

**Exact failure condition:** `gate_pass_declaration` is set to "pass" when any entry in `blocking_inconsistencies` has `resolution: "unresolved"`.

**Enforcement mechanism:** Step B.2.8 is a deterministic check: `gate_pass_declaration` = "pass" if and only if ALL of the following hold simultaneously: (1) received/ is non-empty, (2) response conforms to interface contract, (3) no blocking_inconsistency with resolution: "unresolved" exists. The conjunction is unconditional — any single failing condition forces `gate_pass_declaration` = "fail". The skill must evaluate `blocking_inconsistencies` exhaustively before setting `gate_pass_declaration`. If the skill sets "pass" when any blocking inconsistency is unresolved: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="gate_pass_declaration set to pass despite unresolved blocking inconsistencies; CLAUDE.md §7 Phase 7 gate and §13.4 prohibit declaring the budget gate passed when blocking inconsistencies exist"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No budget_gate_assessment.json written.

**Hard failure confirmation:** Yes — setting gate_pass_declaration: "pass" with unresolved blocking inconsistencies is an unconditional constitutional violation.

**CLAUDE.md §13 cross-reference:** §13.4 — "Commencing any Phase 8 activity … before the budget gate (Phase 7) has passed." §7 Phase 7 gate — "No blocking inconsistencies are unresolved."

---

### Constraint 4: "Must not treat absent response as a non-failing state"

**Decision point in execution logic:** Step B.1.1 (Mode B) — the very first step in Mode B, before any other processing.

**Exact failure condition:** `docs/integrations/lump_sum_budget_planner/received/` is empty or absent, AND the skill does not immediately return a blocking gate failure.

**Enforcement mechanism:** Step B.1.1 is an unconditional BLOCKING GATE FAILURE trigger. If received/ is empty or absent: `gate_pass_declaration` must be set to "fail"; `budget_gate_assessment.json` must be written immediately with this declaration (no other processing proceeds); SkillResult must be returned with status="failure", failure_category="MISSING_INPUT". No further steps in Mode B execute. There is no conditional branch, no wait state, no "soft failure" — absent budget artifacts are a hard block. Setting any other state (e.g., "pending", "not_yet_received", "hold") is a constitutional violation: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Attempted to treat absent budget response as a non-failing state; CLAUDE.md §8.4 defines absent budget artifacts as a blocking gate failure, not a hold state").

**Failure output:** SkillResult(status="failure", failure_category="MISSING_INPUT") when received/ is absent/empty — plus writing budget_gate_assessment.json with gate_pass_declaration: "fail" as a durable record of the blocking failure.

**Hard failure confirmation:** Yes — absent response is unconditionally a blocking gate failure; no other state is constitutionally permissible.

**CLAUDE.md §13 cross-reference:** §8.4 — "Absent budget artifacts in docs/integrations/lump_sum_budget_planner/received/ constitute a blocking gate failure, not a hold state." §13.4 — no Phase 8 activity may begin until the budget gate passes.

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Pre-step: Invoking agent does not provide `invocation_mode` context parameter → `failure_reason="invocation_mode required; must be 'request_validation' or 'response_validation'"`
- Step A.1.1 (Mode A): `docs/integrations/lump_sum_budget_planner/interface_contract.json` does not exist → `failure_reason="interface_contract.json not found"`
- Step A.1.2 (Mode A): `request_templates/` directory is empty → `failure_reason="request_templates/ directory is empty"`
- Step B.1.1 (Mode B): `docs/integrations/lump_sum_budget_planner/received/` directory is empty or absent — BLOCKING GATE FAILURE → `failure_reason="No budget response in received/; this is a blocking gate failure"` (additionally writes `budget_gate_assessment.json` with `gate_pass_declaration: "fail"`)
- Step B.1.2 (Mode B): `interface_contract.json` does not exist → `failure_reason="interface_contract.json not found"`
- Step B.1.3 (Mode B): `wp_structure.json` is absent → `failure_reason="wp_structure.json not found"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. For the Mode B absent-response case: `budget_gate_assessment.json` is written immediately with `gate_pass_declaration: "fail"` as required by the constitutional blocking-gate-failure rule; this is the one exception to the no-write rule and is constitutionally required.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill validates structure of external artifacts (budget response, interface contract). Schema violations in the budget response are findings recorded in the validation artifact (with `conformance_status: "non_conforming"` and `gate_pass_declaration: "fail"`) — not MALFORMED_ARTIFACT failures of the skill itself. No MALFORMED_ARTIFACT conditions are defined for this skill's own inputs.

**Artifact write behavior:** Not applicable for this skill.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use CONSTITUTIONAL_HALT as appropriate.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
No INCOMPLETE_OUTPUT conditions are explicitly defined. Write errors at write sequence steps should return `failure_reason="<artifact name> could not be written"`.

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 1 (must not generate or estimate budget figures): Any numeric budget value (cost, person-months, currency amount) that does not originate verbatim from the `received/` budget response file is written to any output artifact → `failure_reason="Numeric budget value <value> was generated/estimated internally; this skill must not compute, estimate, or invent budget figures per CLAUDE.md §8.1, §8.3, and §13.3"`
- Constraint 2 (must not accept non-conforming response as conforming): The skill writes `conformance_status: "conforms"` when a required field is missing or of wrong type in the budget response → `failure_reason="Non-conforming budget response accepted as conforming; this violates the interface contract and CLAUDE.md §8.5"`
- Constraint 3 (must not declare gate passed with blocking inconsistencies): `gate_pass_declaration` is set to "pass" when any entry in `blocking_inconsistencies` has `resolution: "unresolved"` → `failure_reason="gate_pass_declaration set to pass despite unresolved blocking inconsistencies; CLAUDE.md §7 Phase 7 gate and §13.4 prohibit declaring the budget gate passed when blocking inconsistencies exist"`
- Constraint 4 (absent response treated as non-failing): Any attempt to treat absent `received/` directory as a state other than blocking gate failure → `failure_reason="Attempted to treat absent budget response as a non-failing state; CLAUDE.md §8.4 defines absent budget artifacts as a blocking gate failure, not a hold state"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the constitutional halt.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires, with one constitutionally-required exception: Mode B absent-response (Step B.1.1) MUST write `budget_gate_assessment.json` with `gate_pass_declaration: "fail"` as a durable record of the blocking gate failure.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` includes `docs/integrations/lump_sum_budget_planner/validation/` and `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/`; no decision log exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->
