---
skill_id: governance-model-builder
purpose_summary: >
  Build the project governance model and populate the implementation architecture
  base artifact — management body composition, meeting frequency and decision scope,
  escalation paths, ethics self-assessment, and instrument-mandated section coverage —
  derived from Tier 1 extracted governance/implementation rules, Tier 3 consortium
  data, WP structure, compliance profile, and the Tier 2A section schema registry.
used_by_agents:
  - implementation_architect
reads_from:
  - docs/tier1_normative_framework/extracted/governance_principles.json
  - docs/tier1_normative_framework/extracted/implementation_constraints.json
  - docs/tier3_project_instantiation/consortium/partners.json
  - docs/tier3_project_instantiation/consortium/roles.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json
  - docs/tier3_project_instantiation/call_binding/compliance_profile.json
  - docs/tier3_project_instantiation/call_binding/selected_call.json
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
  - docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
  - docs/tier2b_topic_and_call_sources/extracted/call_constraints.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
constitutional_constraints:
  - "Governance roles must be assigned to Tier 3 consortium members only"
  - "Management structure must be consistent with WP lead assignments"
  - "Ethics self-assessment must not be omitted, null, or 'N/A'"
  - "Tier 1 programme-rule claims must be sourced to docs/tier1_normative_framework/extracted/; if no Tier 1 rule exists, the output must mark the element as an explicit assumption rather than generic 'standard RIA practice'"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool.

**Declared input files to read:**
- `docs/tier1_normative_framework/extracted/governance_principles.json`
- `docs/tier1_normative_framework/extracted/implementation_constraints.json`
- `docs/tier3_project_instantiation/consortium/partners.json`
- `docs/tier3_project_instantiation/consortium/roles.json`
- `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`
- `docs/tier3_project_instantiation/call_binding/compliance_profile.json`
- `docs/tier3_project_instantiation/call_binding/selected_call.json`
- `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`
- `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json`
- `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json`

**Boundary constraints:**
- Do not read files outside the declared input set.
- Do not assume implicit context or reconstruct inputs from memory.
- Read each required file explicitly before using it.
- Base all reasoning ONLY on retrieved file content.
- Do not use generic Horizon Europe / RIA governance heuristics as a substitute for Tier 1 extracted rules when Tier 1 extracted files are present.
- If Tier 1 extracted files do not contain a rule for a governance design choice (for example meeting frequency or escalation wording), you may still make the design choice, but you MUST mark it as an explicit assumption rooted in project-operational need rather than label it as “standard RIA practice”.

Return a SINGLE valid JSON object matching the schema.
Do not include explanations outside the JSON.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier1_normative_framework/extracted/governance_principles.json` | Tier 1 extracted governance and implementation-governance rules | grant_agreement_implementation_articles, consortium_agreement_guidance, no_prescribed_governance_body_names, no_prescribed_meeting_frequency, escalation_constraints, source_documents[] | `tier1.governance_principles.v1` | Provides the authoritative Tier 1 basis for governance-related claims. Prevents generic “standard RIA practice” assumptions from being used as if they were sourced programme rules. |
| `docs/tier1_normative_framework/extracted/implementation_constraints.json` | Tier 1 extracted implementation constraints | ethics_self_assessment_required, ethics_appraisal_summary, gender_equality_requirements, management_balance_guidance, source_documents[] | `tier1.implementation_constraints.v1` | Provides the authoritative Tier 1 basis for ethics and implementation-related claims and constraints. |
| `docs/tier3_project_instantiation/consortium/` | Consortium directory: partners.json, roles.json (and any supporting files) | partners.json: partner_id list, partner_name, partner_type, country; roles.json: role assignments per partner, management responsibilities | N/A — Tier 3 source directory | Provides the complete list of consortium partners and their roles; governance body composition must draw exclusively from partner_id values in this directory |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].wp_id; work_packages[].lead_partner (must be consistent with governance role assignments); partner_role_matrix[].partner_id, wps_as_lead | `orch.phase3.wp_structure.v1` | Provides WP lead assignments that must be reflected in governance roles; management structure must be consistent with WP leads declared here |
| `docs/tier3_project_instantiation/call_binding/compliance_profile.json` | compliance_profile.json — Tier 3 call binding artifact | ethics_review_required, gender_plan_required, open_science_requirements[], eligibility_confirmed | N/A — Tier 3 source | Determines whether ethics issues must be identified; drives `ethics_assessment.ethics_issues_identified` and informs `self_assessment_statement` content |
| `docs/tier3_project_instantiation/call_binding/selected_call.json` | selected_call.json — Tier 3 call binding artifact | instrument_type | N/A — Tier 3 source | Resolves the active instrument type (e.g. "RIA") to look up mandatory implementation sections in section_schema_registry.json |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | section_schema_registry.json — Tier 2A extracted registry | instruments[].instrument_type, instruments[].sections[].section_id, section_name, section_type, mandatory | N/A — Tier 2A extracted | Provides the list of instrument-mandated sections; each mandatory implementation_section must appear in `instrument_sections_addressed` |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | Tier 2B extracted scope requirements for the active call | requirements[].requirement_id, description, mandatory, source_section | N/A — Tier 2B extracted | Provides Tier 2B primary evidence for call-specific scope requirements (e.g. AI-on-demand platform sharing). Used to ground call-mandate claims that would otherwise rely only on the Tier 3 compliance_profile.json derivative. |
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | Tier 2B extracted call constraints for the active call | constraints[].constraint_id, description, constraint_type, source_section | N/A — Tier 2B extracted | Provides Tier 2B primary evidence for call-level constraints. Used alongside scope_requirements.json to ground call-mandate claims in Tier 2B traceability per CLAUDE.md §13.2. |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | implementation_architecture.json | `orch.phase6.implementation_architecture.v1` | schema_id, run_id, governance_matrix (array), management_roles (array), risk_register (array — placeholder, populated by risk-register-builder), ethics_assessment (object — populated by this skill from compliance_profile.json), instrument_sections_addressed (array — populated by this skill from section_schema_registry.json) | Yes | governance_matrix: Tier 1 constraints + Tier 3 consortium/roles/WP data; management_roles: Tier 3 roles + wp_structure.json; ethics_assessment: Tier 1 implementation constraints + compliance_profile.json; instrument_sections_addressed: Tier 2A section schema registry + selected_call.json|

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. This skill populates governance_matrix, management_roles, ethics_assessment, and instrument_sections_addressed. The risk_register field is set to `[]` (placeholder) and populated by the risk-register-builder skill in a subsequent invocation. The full implementation_architecture.json must be complete before the Phase 6 gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | Yes — artifact_id: a_t4_phase6 (directory); canonical file within that directory | n06_implementation_architecture |

## Execution Specification

### 1. Input Validation Sequence

### 1. Input Validation Sequence

- Step 1.1: Confirm `docs/tier1_normative_framework/extracted/governance_principles.json` exists and is parseable JSON with `schema_id = "tier1.governance_principles.v1"`. If absent or malformed: return `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="governance_principles.json not found or malformed; Tier 1 governance grounding is required to avoid generic programme-rule assumptions")`.
- Step 1.2: Confirm `docs/tier1_normative_framework/extracted/implementation_constraints.json` exists and is parseable JSON with `schema_id = "tier1.implementation_constraints.v1"`. If absent or malformed: return `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="implementation_constraints.json not found or malformed; Tier 1 implementation constraints are required for ethics and implementation grounding")`.
- Step 1.3: Confirm `docs/tier3_project_instantiation/consortium/partners.json` exists and contains at least one partner entry. Build the **valid_partner_ids** set from `partner_id` values.
- Step 1.4: Confirm `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` exists with `schema_id = "orch.phase3.wp_structure.v1"`. If absent or schema mismatch: fail with `MISSING_INPUT`.
- Step 1.5: If `wp_structure.json` has `artifact_status = "invalid"`: fail with `MALFORMED_ARTIFACT`.
- Step 1.6: Confirm `compliance_profile.json`, `selected_call.json`, and `section_schema_registry.json` are present and parseable. Extract `instrument_type` from selected_call.json.

### 2. Core Processing Logic

- Step 2.1: Build governance from **Tier 1 constraints first, Tier 3 project facts second**.
- Step 2.2: Extract from `partners.json` and `roles.json`: partner facts, explicit role assignments, explicit governance bodies, meeting frequencies, and escalation rules.
- Step 2.3: Extract from `wp_structure.json`: WP identifiers, lead partners, and partner_role_matrix.
- Step 2.4: Build `governance_matrix`:
  - Use explicit Tier 3 body names and meeting frequencies if present.
  - If Tier 1 contains a prescribed rule, use it and cite it in `source_basis`.
  - If Tier 1 says no prescribed frequency exists, choose a reasonable project-operational cadence but record `assumption_note: "Meeting frequency not specified in Tier 3 and not prescribed in Tier 1 extracted; selected as a project-operational assumption"`.
  - Do **not** use phrases such as `standard RIA governance practice` or `standard operational practice`.
  - If the output refers to Grant Agreement or Consortium Agreement obligations, the wording must be traceable to Tier 1 extracted files through `source_basis`; otherwise it must be framed as a project-operational escalation path, not as a normative programme rule.
- Step 2.5: Build `management_roles` from explicit Tier 3 roles or, where necessary, transparent inference from WP lead assignments.
- Step 2.6: Set `risk_register` to `[]` (placeholder for risk-register-builder).
- Step 2.7: Build `ethics_assessment` from `implementation_constraints.json` + `compliance_profile.json` + project scope visible in `wp_structure.json`.
  - Step 2.7.1 — **Gender-dimension wording constraint (§13.2 guard):** The Tier 1 rule `gender_dimension_in_content` states that integration of the gender dimension is mandatory unless the topic explicitly states non-relevance. When including this rule in the `self_assessment_statement`, you MUST NOT assert that the specific call or topic does or does not exempt the topic (e.g., "this call does not exempt the topic") UNLESS `traceability_footer.primary_sources[]` contains a Tier 2B source path within `docs/tier2b_topic_and_call_sources/extracted/` that explicitly evidences whether the topic text states non-relevance. If no Tier 2B source is cited in the traceability footer for this claim, use the following safe wording instead: "Integration of the gender dimension in research and innovation content follows the Tier 1 default rule that it is mandatory unless the topic explicitly states non-relevance. No Tier 2B exemption source is currently cited in this Phase 6 artifact; Phase 8 drafting must either add the relevant Tier 2B topic-source reference or keep the claim framed as pending call-specific confirmation." This constraint prevents §13.2 violations by ensuring no call-specific factual assertion is emitted without Tier 2B traceability.
  - Step 2.7.2 — **Compliance-profile derivative labeling constraint (§13.2 guard):** When citing `compliance_profile.json` fields (e.g., `ethics_review_required`, `open_science_requirements`) in `source_basis` fields of ethics_assessment issues, management_roles, or instrument_sections_addressed notes, you MUST distinguish between:
    - **(a) Claims backed by Tier 2B evidence:** If a matching requirement exists in `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` or `call_constraints.json`, cite the Tier 2B source directly (requirement_id and source_section) and add it to `traceability_footer.primary_sources[]`. The compliance_profile.json may be cited as a secondary/confirming reference.
    - **(b) Claims NOT backed by Tier 2B evidence:** If no matching Tier 2B extracted entry exists, the `source_basis` MUST frame the compliance_profile.json field as a Tier 3 derivative compliance flag, NOT as a confirmed call-specific mandate. Use wording such as: "The Tier 3 compliance_profile.json records [field]: [value] as a compliance flag derived during call binding; no Tier 2B extracted source path cites [requirement] as a topic-specific mandate for this call."
    - Emitting a call-specific mandate claim sourced only to compliance_profile.json without Tier 2B traceability is a §13.2 violation.
- Step 2.8: Build `instrument_sections_addressed` from `section_schema_registry.json`, `selected_call.json`, and `implementation_constraints.json`.
- Step 2.9: Build `traceability_footer` — construct an artifact-level provenance record listing every declared input file actually read during this invocation, using **full repo-relative paths** (not abbreviated file names). The `traceability_footer.primary_sources[]` array must include at minimum every Tier 1 extracted file used (with tier: 1) and should include Tier 2–4 sources where their content grounds claims in the artifact. **Tier 2B inclusion rule:** If any claim in the artifact cites a call-specific requirement that is confirmed in `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` or `call_constraints.json`, the corresponding Tier 2B file MUST appear in `primary_sources[]` with `tier: 2` and `source_path` starting with `docs/tier2b_topic_and_call_sources/extracted/`. This is necessary to satisfy the §13.2 traceability check performed by constitutional-compliance-check. Each entry must use the full path starting with `docs/` (e.g., `docs/tier1_normative_framework/extracted/governance_principles.json`, not just `governance_principles.json`). Include `relevant_fields` where helpful for auditability.

### 3. Output Construction

**`implementation_architecture.json`:**
- `schema_id`: set to "orch.phase6.implementation_architecture.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `governance_matrix`: derived from Step 2.4 — array of `{body_name, composition[], decision_scope, meeting_frequency, escalation_path}`
- `management_roles`: derived from Step 2.5 — array of `{role_id, role_name, assigned_to, responsibilities[]}`
- `risk_register`: `[]` — populated by risk-register-builder
- `ethics_assessment`: derived from Step 2.7 — object with `{ethics_issues_identified, issues[], self_assessment_statement}`
- `instrument_sections_addressed`: derived from Step 2.8 — array of `{section_id, section_name, status}`
- `traceability_footer`: derived from Step 2.9 — object with `primary_sources[]` array; each entry: `{tier (integer 1–4), source_path (full repo-relative path starting with "docs/"), relevant_fields[] (optional)}`. Must include at minimum:
  - `{tier: 1, source_path: "docs/tier1_normative_framework/extracted/governance_principles.json"}`
  - `{tier: 1, source_path: "docs/tier1_normative_framework/extracted/implementation_constraints.json"}`
  - Plus Tier 2A, Tier 3, and Tier 4 sources actually used
  - **Tier 2B entries are required** when the artifact cites call-specific requirements confirmed in Tier 2B extracted files (e.g., AI-on-demand platform sharing from scope_requirements.json SR-10 / call_constraints.json CC-05). Include `{tier: 2, source_path: "docs/tier2b_topic_and_call_sources/extracted/<file>.json"}` for each Tier 2B file used.

### 4. Conformance Stamping

- `schema_id`: set to "orch.phase6.implementation_architecture.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/` if not present.
- Step 5.2: Write `implementation_architecture.json` to `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`. If the file already exists (because another skill will update it), read the existing content first and merge: update only the `governance_matrix`, `management_roles`, `ethics_assessment`, `instrument_sections_addressed`, and `traceability_footer` fields; preserve all other fields.

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

---

### Constraint 3: "Call-specific assertions about gender-dimension exemption require Tier 2B traceability"

**Decision point in execution logic:** Step 2.7.1 — at the point the `self_assessment_statement` includes wording about the gender dimension in research and innovation content.

**Exact failure condition:** The `self_assessment_statement` asserts a call-specific fact about whether the topic does or does not exempt the gender dimension (e.g., "this call does not exempt the topic", "the topic does not state non-relevance"), AND `traceability_footer.primary_sources[]` contains no entry with a `source_path` within `docs/tier2b_topic_and_call_sources/extracted/` that could evidence review of the specific topic text for a gender-dimension exemption statement.

**Enforcement mechanism:** In Step 2.7.1, before writing any call-specific gender-dimension assertion, check whether the `traceability_footer.primary_sources[]` includes at least one entry with `tier: 2` and `source_path` starting with `docs/tier2b_topic_and_call_sources/extracted/`. If no such entry exists: the `self_assessment_statement` must use the safe fallback wording specified in Step 2.7.1. If such an entry exists AND its content explicitly confirms that the topic text was reviewed and contains no gender-dimension exemption statement: the call-specific assertion is permitted, and the Tier 2B source entry must remain in the traceability footer. Emitting a call-specific assertion without a Tier 2B traceability source is a validation issue that will cause a §13.2 violation at constitutional-compliance-check.

**Failure output:** Not a hard skill failure — the skill produces valid output using the safe fallback wording. The constraint prevents the violation from being emitted rather than halting the skill.

**Hard failure confirmation:** No — this is a wording guard, not a halt condition. The skill succeeds with safe wording when Tier 2B evidence is absent.

**CLAUDE.md §13 cross-reference:** §13.2 — "Inventing call constraints, scope requirements, expected outcomes, or expected impacts not present in Tier 2B source documents." A negative assertion about the topic text ("this call does not exempt") is a call-specific factual claim requiring Tier 2B evidence.

---

### Constraint 4: "Call-specific mandate claims sourced to compliance_profile.json require Tier 2B traceability or derivative labeling"

**Decision point in execution logic:** Steps 2.5 (management_roles source_basis), 2.7 (ethics_assessment source_basis), 2.7.2 (compliance-profile derivative labeling), and 2.8 (instrument_sections_addressed notes) — at every point where `compliance_profile.json` fields are cited as the basis for a call-specific requirement.

**Exact failure condition:** Any `source_basis` field, `self_assessment_statement` text, or `instrument_sections_addressed` note asserts a call-specific mandate (e.g., "open science requirement", "ethics review required as a call condition") sourced to `compliance_profile.json` without EITHER: (a) a corresponding Tier 2B extracted source path in `traceability_footer.primary_sources[]`, OR (b) explicit derivative labeling framing the claim as a Tier 3 compliance flag pending Tier 2B confirmation.

**Enforcement mechanism:** In Steps 2.5, 2.7, 2.7.2, and 2.8, before writing any call-specific requirement claim sourced to compliance_profile.json: check whether the requirement is also confirmed in `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` or `call_constraints.json`. If yes: cite the Tier 2B source directly in `source_basis` and add it to `traceability_footer.primary_sources[]`. If no: frame the compliance_profile.json field as a Tier 3 derivative compliance flag using the wording pattern: "The Tier 3 compliance_profile.json records [field]: [value] as a compliance flag derived during call binding; no Tier 2B extracted source path cites [requirement] as a topic-specific mandate for this call." Emitting a call-specific mandate claim sourced only to compliance_profile.json without Tier 2B traceability or derivative labeling will cause a §13.2 violation at constitutional-compliance-check.

**Failure output:** Not a hard skill failure — the skill produces valid output using either Tier 2B citation or derivative labeling. The constraint prevents the violation from being emitted rather than halting the skill.

**Hard failure confirmation:** No — this is a wording guard, not a halt condition. The skill succeeds with proper sourcing or derivative framing when the constraint is applied.

**CLAUDE.md §13 cross-reference:** §13.2 — "Inventing call constraints, scope requirements, expected outcomes, or expected impacts not present in Tier 2B source documents." Asserting a compliance_profile.json derivative as a confirmed call mandate without Tier 2B traceability constitutes an invented call constraint.

---

- Do not present an unsourced project design choice as if it were a Tier 1 programme rule.
- If a Tier 1 source is present and relevant, use it.
- If a Tier 1 source is absent or explicitly non-prescriptive, the output must mark the design choice as an assumption or project-operational decision rather than a normative Horizon rule.

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

**Co-production rationale:** The Phase 6 canonical artifact is co-produced by two skills: governance-model-builder (this skill) produces the base artifact with governance_matrix, management_roles, ethics_assessment, and instrument_sections_addressed; risk-register-builder subsequently enriches the risk_register field via merge-on-write.

**Required fields checked (this skill's scope):**

| Field | Required | Status | Notes |
|-------|----------|--------|-------|
| schema_id | true | ✓ Implemented | Set to "orch.phase6.implementation_architecture.v1" in Step 3 and Step 4 |
| run_id | true | ✓ Implemented | Propagated from invoking agent run_id |
| artifact_status | false | ✓ Absent at write time | Runner-stamped post-gate |
| governance_matrix | true | ✓ Implemented | Built in Step 2.4 with body_name, composition[], decision_scope per body |
| management_roles | true | ✓ Implemented | Built in Step 2.5 with role_id, role_name, assigned_to (partner_id), responsibilities[] |
| risk_register | true | ✓ Placeholder ([]) — populated by risk-register-builder | Final population required before Phase 6 gate |
| ethics_assessment | true | ✓ Implemented | Built in Step 2.7 from compliance_profile.json with ethics_issues_identified, issues[], self_assessment_statement |
| instrument_sections_addressed | true | ✓ Implemented | Built in Step 2.8 from section_schema_registry.json filtered by active instrument type |
| traceability_footer | false | ✓ Implemented | Built in Step 2.9 with primary_sources[] listing all Tier 1–4 input files using full repo-relative paths |

**Reads_from compliance:** governance_matrix and management_roles derived from consortium/partners.json, consortium/roles.json, wp_structure.json. ethics_assessment derived from compliance_profile.json. instrument_sections_addressed derived from section_schema_registry.json and selected_call.json. traceability_footer derived from the declared reads_from set with full repo-relative paths. All sources are in declared reads_from. No external fields introduced.

**Corrections applied:** Steps 2.7 and 2.8 changed from placeholder values (null / []) to substantive production from declared inputs. This eliminates the dependency on agent-body reasoning that the runtime does not execute.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
