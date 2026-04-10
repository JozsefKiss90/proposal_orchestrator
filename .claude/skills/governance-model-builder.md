---
skill_id: governance-model-builder
purpose_summary: >
  Build the project governance model — management body composition, meeting frequency
  and decision scope, escalation paths, and quality assurance procedures — derived
  from Tier 3 consortium data and WP structure.
used_by_agents:
  - implementation_architect
reads_from:
  - docs/tier3_project_instantiation/consortium/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
constitutional_constraints:
  - "Governance roles must be assigned to Tier 3 consortium members only"
  - "Management structure must be consistent with WP lead assignments"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/consortium/` | Consortium directory: partners.json, roles.json (and any supporting files) | partners.json: partner_id list, partner_name, partner_type, country; roles.json: role assignments per partner, management responsibilities | N/A — Tier 3 source directory | Provides the complete list of consortium partners and their roles; governance body composition must draw exclusively from partner_id values in this directory |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].wp_id; work_packages[].lead_partner (must be consistent with governance role assignments); partner_role_matrix[].partner_id, wps_as_lead | `orch.phase3.wp_structure.v1` | Provides WP lead assignments that must be reflected in governance roles; management structure must be consistent with WP leads declared here |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | implementation_architecture.json | `orch.phase6.implementation_architecture.v1` | schema_id, run_id, governance_matrix (array: body_name, composition[partner_id list], decision_scope, meeting_frequency, escalation_path per body), management_roles (array: role_id, role_name, assigned_to[partner_id], responsibilities per role), risk_register (array — populated by risk-register-builder skill), ethics_assessment (object — populated separately), instrument_sections_addressed (array — populated separately) | Yes | governance_matrix: body composition derived from consortium/partners.json partner_ids; management_roles: assigned_to values derived from consortium/roles.json; meeting_frequency and escalation_path may be inferred but must be flagged if no Tier 3 source |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. This skill populates the governance_matrix and management_roles fields; risk_register, ethics_assessment, and instrument_sections_addressed are populated by other skills (risk-register-builder, implementation_architect). The full implementation_architecture.json must be complete before the Phase 6 gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | Yes — artifact_id: a_t4_phase6 (directory); canonical file within that directory | n06_implementation_architecture |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier3_project_instantiation/consortium/partners.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="partners.json not found; governance roles cannot be assigned without consortium partner data") and halt.
- Step 1.2: Non-empty check — confirm `partners.json` is parseable JSON and contains at least one partner entry. Build the **valid_partner_ids** set from `partner_id` values.
- Step 1.3: Presence check — confirm `docs/tier3_project_instantiation/consortium/roles.json` exists. If absent: log as Assumed (governance roles will be inferred from WP leads); continue — do not halt.
- Step 1.4: Presence check and schema check — confirm `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` exists with `schema_id` = "orch.phase3.wp_structure.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="wp_structure.json not found or schema mismatch") and halt.
- Step 1.5: Validated state check — if `wp_structure.json` has `artifact_status` = "invalid": return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="wp_structure.json has artifact_status: invalid; the artifact was invalidated by a prior gate failure and cannot be used as input until Phase 3 gate passes") and halt.

### 2. Core Processing Logic

- Step 2.1: Extract from `partners.json`: `partner_id`, `partner_name`, `partner_type`, `country` for each partner. These are the only permissible sources for governance role assignments.
- Step 2.2: Extract from `roles.json` (if present): any explicit role assignments (project coordinator, WP leads, financial officer, ethics officer, etc.). For each role: record `role_name`, `assigned_to` (partner_id). For each assigned_to value: verify it is in valid_partner_ids; if not: record a validation issue.
- Step 2.3: Extract from `wp_structure.json`: `partner_role_matrix` (partner_id → wps_as_lead list). Identify the partner with the most WPs as lead — this is the likely coordinator candidate if not specified in roles.json.
- Step 2.4: Build the `governance_matrix` array. At minimum, construct the following governance bodies:
  - **Project Management Board (PMB)** or equivalent: `{ body_name: "Project Management Board", composition: [<all partner_ids from valid_partner_ids>], decision_scope: "Strategic decisions, major changes, financial oversight, external communications", meeting_frequency: <from roles.json if present; otherwise "Quarterly" marked as Assumed>, escalation_path: "Escalation to project coordinator, then to funding agency if unresolved" }`.
  - **Project Coordination Team (PCT)** or equivalent: `{ body_name: "Project Coordination Team", composition: [<partner_ids with WP lead roles>], decision_scope: "Operational decisions, task scheduling, deliverable coordination, day-to-day management", meeting_frequency: <from roles.json if present; otherwise "Monthly" marked as Assumed> }`.
  - If `roles.json` specifies additional bodies (Technical Advisory Board, Ethics Committee, etc.): add those, with composition and decision_scope from roles.json data. All composition values must be partner_id values from valid_partner_ids.
  - For any `meeting_frequency` value that is not explicitly stated in Tier 3: add an `assumption_note: "meeting_frequency assumed; not stated in Tier 3 consortium data"`.
- Step 2.5: Build the `management_roles` array:
  - **Project Coordinator**: identify from roles.json or infer as the lead partner of WP1 (management WP) from wp_structure.json. `{ role_id: "COORD-01", role_name: "Project Coordinator", assigned_to: <partner_id>, responsibilities: ["Overall project management", "Liaison with funding agency", "Financial oversight", "Report submission"] }`. If inferred (not from roles.json): record `inference_note: "Coordinator assigned as lead partner of WP1; explicit assignment not found in roles.json"`.
  - **WP Lead roles**: for each WP in wp_structure.json, create a management role entry: `{ role_id: "WPL-<wp_id>", role_name: "WP<n> Lead", assigned_to: <lead_partner from wp_structure>, responsibilities: ["Lead WP<n> activities", "Ensure WP<n> deliverables are produced on schedule", "Report WP<n> progress to coordinator"] }`. The `assigned_to` value is taken directly from `work_packages[].lead_partner` in wp_structure.json.
  - All `assigned_to` values MUST exist in valid_partner_ids. If any does not: record a validation issue — this will cause the Phase 6 gate to fail.
- Step 2.6: Set `risk_register` to `[]` (empty array — populated by risk-register-builder skill in a subsequent invocation).
- Step 2.7: Set `ethics_assessment` to `null` (placeholder — populated separately by the implementation_architect agent).
- Step 2.8: Set `instrument_sections_addressed` to `[]` (empty array — populated separately after all governance, risk, and ethics elements are complete).

### 3. Output Construction

**`implementation_architecture.json`:**
- `schema_id`: set to "orch.phase6.implementation_architecture.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `governance_matrix`: derived from Step 2.4 — array of `{body_name, composition[], decision_scope, meeting_frequency, escalation_path}`
- `management_roles`: derived from Step 2.5 — array of `{role_id, role_name, assigned_to, responsibilities[]}`
- `risk_register`: `[]` — populated by risk-register-builder
- `ethics_assessment`: `null` — populated separately
- `instrument_sections_addressed`: `[]` — populated separately

### 4. Conformance Stamping

- `schema_id`: set to "orch.phase6.implementation_architecture.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/` if not present.
- Step 5.2: Write `implementation_architecture.json` to `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`. If the file already exists (because another skill will update it), read the existing content first and merge: update only the `governance_matrix` and `management_roles` fields; preserve all other fields.

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Governance roles must be assigned to Tier 3 consortium members only"

**Decision point in execution logic:** Steps 2.4 and 2.5 — at the point governance body composition arrays and management_roles `assigned_to` fields are populated.

**Exact failure condition:** Any `composition` array in `governance_matrix` contains a partner_id that is NOT in `valid_partner_ids`; OR any `assigned_to` field in `management_roles` contains a partner_id that is NOT in `valid_partner_ids`. Equivalently: a governance role or body member is invented or sourced from prior knowledge rather than from `docs/tier3_project_instantiation/consortium/partners.json`.

**Enforcement mechanism:** In Step 2.4, every partner_id added to a governance body's `composition` array must be verified against `valid_partner_ids` before being added. If a partner_id is not in `valid_partner_ids`: it must NOT be added to the composition array. Its absence must be recorded as a validation issue. In Step 2.5, every `assigned_to` value must be verified against `valid_partner_ids`. An `assigned_to` value not in `valid_partner_ids` is a validation issue that causes Phase 6 gate failure — it is not silently corrected by substituting a valid partner_id. If the validation issues make it impossible to produce any governance body with a valid composition (e.g., no valid partner_ids exist in Tier 3): return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="No valid partner_ids available from Tier 3 consortium data to assign governance roles; governance roles must be assigned to Tier 3 consortium members only per CLAUDE.md §13.3"). No output written.

**Failure output:** Individual invalid partner → validation_issue recorded (gate-blocking). Systemic failure → SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION").

**Hard failure confirmation:** Yes — assigning governance roles to non-Tier-3 partners is a constitutional violation per CLAUDE.md §13.3; silent correction by substitution is also prohibited.

**CLAUDE.md §13 cross-reference:** §13.3 — "Inventing project facts — partner names, capabilities, roles … not present in Tier 3." Governance role assignments are project facts; they must be traceable to Tier 3.

---

### Constraint 2: "Management structure must be consistent with WP lead assignments"

**Decision point in execution logic:** Step 2.5 — at the point WP lead management roles are created from `work_packages[].lead_partner` in wp_structure.json.

**Exact failure condition:** Any WP lead role entry in `management_roles` has an `assigned_to` value that differs from the `lead_partner` field for the corresponding WP in `wp_structure.json`. Equivalently: the management structure diverges from the WP lead assignments without a recorded explanation.

**Enforcement mechanism:** In Step 2.5, the WP lead role entries are derived directly from `work_packages[].lead_partner` in wp_structure.json. The `assigned_to` value for each "WPL-<wp_id>" role must equal the `lead_partner` value from the corresponding WP entry — no substitution, adjustment, or agent judgment override is permitted. If the lead_partner from wp_structure.json is not in valid_partner_ids (a pre-existing normalization issue): the inconsistency must be carried forward as a validation_issue in the output — it must not be silently resolved by assigning a different partner. At output construction time, the skill must verify consistency between every `management_roles[].assigned_to` value and the corresponding `wp_structure.work_packages[].lead_partner`. Any mismatch detected at write time triggers: return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="management_roles assigned_to for WP <wp_id> does not match lead_partner in wp_structure.json; management structure must be consistent with WP lead assignments"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION"). No `implementation_architecture.json` written.

**Hard failure confirmation:** Yes — management-WP lead inconsistency is not correctable by agent judgment; the source data must be corrected at Phase 3 level.

**CLAUDE.md §13 cross-reference:** §7 Phase 6 gate — "Consortium management roles are assigned and non-overlapping." §12.5 — review must check internal consistency.

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier3_project_instantiation/consortium/partners.json` does not exist → `failure_reason="partners.json not found; governance roles cannot be assigned without consortium partner data"`
- Step 1.4: `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` is absent or schema mismatch → `failure_reason="wp_structure.json not found or schema mismatch"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.5: `wp_structure.json` has `artifact_status: "invalid"` → `failure_reason="wp_structure.json has artifact_status: invalid; the artifact was invalidated by a prior gate failure and cannot be used as input until Phase 3 gate passes"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Skill halts immediately.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
- Constraint 1 (governance roles assigned to Tier 3 consortium members only — systemic failure): No valid partner_ids are available from Tier 3 consortium data to assign governance roles → `failure_reason="No valid partner_ids available from Tier 3 consortium data to assign governance roles; governance roles must be assigned to Tier 3 consortium members only per CLAUDE.md §13.3"`
- Constraint 2 (management structure consistent with WP lead assignments): At output construction time, any `management_roles[].assigned_to` value for a WP lead role does not match `lead_partner` for the corresponding WP in `wp_structure.json` → `failure_reason="management_roles assigned_to for WP <wp_id> does not match lead_partner in wp_structure.json; management structure must be consistent with WP lead assignments"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the failure.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
No INCOMPLETE_OUTPUT conditions are explicitly defined. Write errors at Step 5.2 should return `failure_reason="implementation_architecture.json could not be written"`.

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
No CONSTITUTIONAL_HALT conditions are defined for this skill. Constitutional constraint failures (invalid partner assignments, management-WP lead inconsistency) are handled as CONSTRAINT_VIOLATION. Individual invalid partner entries in governance body composition are recorded as validation_issues — not as CONSTITUTIONAL_HALT.

**Artifact write behavior:** Not applicable.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` is `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/` only; no exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Validates output construction against artifact_schema_specification.yaml.*

---

### Canonical Artifact: `implementation_architecture.json` (partial population — merge model)

**Schema ID verified:** `orch.phase6.implementation_architecture.v1` ✓

**Partial-population rationale:** The Phase 6 canonical artifact is co-produced by three skills (governance-model-builder, risk-register-builder, implementation_architect agent populating ethics and instrument sections). Step 5.2 specifies merge-on-write: this skill writes only governance_matrix and management_roles; placeholder values for risk_register, ethics_assessment, and instrument_sections_addressed are written only on first invocation and overwritten by the subsequent skills before the Phase 6 gate evaluates the artifact.

**Required fields checked (this skill's scope):**

| Field | Required | Status | Notes |
|-------|----------|--------|-------|
| schema_id | true | ✓ Implemented | Set to "orch.phase6.implementation_architecture.v1" in Step 3 and Step 4 |
| run_id | true | ✓ Implemented | Propagated from invoking agent run_id |
| artifact_status | false | ✓ Absent at write time | Runner-stamped post-gate |
| governance_matrix | true | ✓ Implemented | Built in Step 2.4 with body_name, composition[], decision_scope per body |
| management_roles | true | ✓ Implemented | Built in Step 2.5 with role_id, role_name, assigned_to (partner_id), responsibilities[] |
| risk_register | true | ✓ Placeholder ([]) — populated by risk-register-builder | Final population required before Phase 6 gate |
| ethics_assessment | true | ⚠ Placeholder (null) — populated by implementation_architect agent | Final population required before Phase 6 gate; schema requires non-null with ethics_issues_identified, issues[], self_assessment_statement |
| instrument_sections_addressed | true | ✓ Placeholder ([]) — populated by implementation_architect agent | Final population required before Phase 6 gate |

**Reads_from compliance:** governance_matrix and management_roles fields are derived exclusively from declared reads_from sources (consortium/partners.json, consortium/roles.json, wp_structure.json). No external fields introduced.

**Corrections applied:** None to Output Construction. The placeholder strategy is documented in Step 5.2 and is consistent with the merge-on-write contract; the artifact is not gate-evaluable until all co-producer skills have completed.

<!-- Step 8 complete: schema validation performed -->
