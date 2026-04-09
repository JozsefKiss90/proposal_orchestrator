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

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
