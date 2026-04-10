---
skill_id: risk-register-builder
purpose_summary: >
  Populate the risk register from Tier 3 risk seeds, assigning likelihood, impact,
  mitigation, and monitoring for each risk, and flagging any material risks not in the
  seed file for Tier 3 update.
used_by_agents:
  - implementation_architect
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/risks.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
constitutional_constraints:
  - "Risks not in Tier 3 seeds must be flagged for operator review, not silently added"
  - "Mitigation measures must be traceable to project activities, not generic"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/architecture_inputs/risks.json` | risks.json — Tier 3 architecture input | Risk seed entries: risk_id, description, category, initial_likelihood, initial_impact, mitigation_seed, responsible_partner | N/A — Tier 3 source artifact | Authoritative source of project risks; the register must be populated from these seeds; any risk not in this file must be flagged for operator review rather than silently added |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].wp_id, tasks[], deliverables[] — to identify activities that mitigation measures can be traced to; partner_role_matrix for responsible_partner validation | `orch.phase3.wp_structure.v1` | Provides WP activities and deliverables as traceable anchors for mitigation measures; mitigation measures must reference a project activity or deliverable, not be generic |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | gantt.json — canonical Phase 4 artifact | milestones[].milestone_id, due_month — as monitoring trigger points for risk monitoring | `orch.phase4.gantt.v1` | Provides milestone due months as risk monitoring trigger points; risk monitoring schedule should align with project milestones |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | implementation_architecture.json (risk_register field) | `orch.phase6.implementation_architecture.v1` | schema_id, run_id (already set by governance-model-builder); risk_register (array: risk_id, description, category[technical/financial/organisational/ethical/external/other], likelihood[low/medium/high], impact[low/medium/high], mitigation[non-empty string], responsible_partner per entry) | Yes — same run_id as the full implementation_architecture.json | risk_register entries: risk_id, description, category from risks.json seeds; likelihood and impact refined from initial values; mitigation derived from mitigation_seed with specific reference to WP activities from wp_structure.json; monitoring_triggers derived from gantt.json milestone due months |

**Note:** `artifact_status` must be ABSENT at write time. This skill populates the risk_register field within the implementation_architecture.json file. If material risks are identified during analysis of wp_structure or gantt that are NOT in risks.json, they must be documented as flag records (not added to the register) and returned in the SkillResult payload's `flagged_gap_risks` array so the invoking agent can invoke decision-log-update. This skill does not write to the decision log directly.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | Yes — artifact_id: a_t4_phase6 (directory); canonical file within that directory | n06_implementation_architecture |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier3_project_instantiation/architecture_inputs/risks.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="risks.json not found; risk seeds must be provided in Tier 3 before risk register can be built") and halt.
- Step 1.2: Non-empty check — confirm `risks.json` contains at least one entry. If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="risks.json is empty; at least one risk seed is required") and halt.
- Step 1.3: Presence check and schema check — confirm `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` exists with `schema_id` = "orch.phase3.wp_structure.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="wp_structure.json not found or schema mismatch") and halt.
- Step 1.4: Presence check and schema check — confirm `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` exists with `schema_id` = "orch.phase4.gantt.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="gantt.json not found or schema mismatch") and halt.
- Step 1.5: Presence check — confirm `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` exists (created by governance-model-builder). If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="implementation_architecture.json not found; governance-model-builder must run first") and halt.

### 2. Core Processing Logic

- Step 2.1: Extract **risk seeds** from `risks.json`: each seed entry with `risk_id`, `description`, `category`, `initial_likelihood`, `initial_impact`, `mitigation_seed`, `responsible_partner`.
- Step 2.2: Build a **WP activity catalogue** from `wp_structure.json`: for each WP, collect all task titles and deliverable titles. For each task: record `{ task_id, title, wp_id, responsible_partner }`. For each deliverable: record `{ deliverable_id, title, type, wp_id, responsible_partner }`. This catalogue is used to anchor mitigation measures to specific project activities.
- Step 2.3: Extract **milestone monitoring points** from `gantt.json`: for each milestone, record `{ milestone_id, due_month, responsible_wp }`. These become candidate monitoring trigger points for risk monitoring.
- Step 2.4: Build the **valid_partner_ids** set from the consortium partner list provided by the invoking agent as context. This skill does not read `docs/tier3_project_instantiation/consortium/partners.json` directly (not in reads_from); the invoking agent must supply the partner_id list as a context parameter before invoking this skill.
- Step 2.5: For each risk seed entry, build a full risk register entry:
  - `risk_id`: from seed `risk_id` — preserve exactly.
  - `description`: from seed `description` — preserve exactly; do not paraphrase or elaborate.
  - `category`: from seed `category`. Must be one of [technical, financial, organisational, ethical, external, other]. If seed category does not match: map to the closest matching category and record the mapping in the decision log.
  - `likelihood`: use `initial_likelihood` from seed if it is already one of [low, medium, high]. If it is numeric or otherwise formatted: convert — 1-2 → low, 3 → medium, 4-5 → high; record the conversion. Must not be null.
  - `impact`: same conversion as likelihood. Must not be null.
  - `mitigation`: take `mitigation_seed` from the seed entry and augment it with a specific reference to a project activity from the WP activity catalogue (Step 2.2). The mitigation statement must include at least one explicit reference to a task_id or deliverable_id from the catalogue. Format: "[mitigation_seed text]. This is addressed in [task_title] (task_id: [task_id], WP[n])." If the mitigation_seed does not relate to any catalogued activity, record the mitigation as-is but flag with a `mitigation_traceability_issue: true` field and note it requires operator review.
  - `responsible_partner`: from seed `responsible_partner`. Verify it is in valid_partner_ids. If not: record a validation issue but continue; the Phase 6 gate will flag this.
- Step 2.6: **Gap risk scan** — examine the WP activity catalogue for structural risk indicators not covered by any seed entry:
  - Indicator A: any task with a `responsible_partner` that appears as the sole responsible partner for ≥ 3 critical deliverables (single-point-of-failure risk).
  - Indicator B: any task that has no `contributing_partners` (solo task with no fallback partner).
  - Indicator C: any milestone in the first 6 months of the project with no predecessor tasks from multiple partners (insufficient early collaboration risk).
  - For each identified gap risk indicator: do NOT add a risk entry to the register. Instead, record it in the `flagged_gap_risks` array of the SkillResult payload: `{ risk_indicator: <A/B/C>, description: <what was found>, affected_elements: [task_id or milestone_id list], resolution_required: true }`. Do not write a decision log entry directly — this skill does not write to decision_log/. The invoking agent must invoke decision-log-update with decision_type: "gap_risk_flagged" for each entry in the SkillResult payload's flagged_gap_risks array to produce durable decision log records.
- Step 2.7: Read the existing `implementation_architecture.json`. Verify `schema_id` = "orch.phase6.implementation_architecture.v1". Extract all existing fields. Replace the `risk_register` field with the newly built register array from Step 2.5. Preserve all other fields (schema_id, run_id, governance_matrix, management_roles, ethics_assessment, instrument_sections_addressed) unchanged.

### 3. Output Construction

**`implementation_architecture.json`** (updated in place — only `risk_register` field replaced):
- `schema_id`: preserved as "orch.phase6.implementation_architecture.v1"
- `run_id`: preserved from existing file
- `risk_register`: derived from Step 2.5 — array of `{risk_id, description, category, likelihood, impact, mitigation, responsible_partner}` — one entry per risk seed
- All other fields: preserved unchanged from the file read in Step 2.7

### 4. Conformance Stamping

- `schema_id`: preserved as "orch.phase6.implementation_architecture.v1" (this skill does not change schema_id)
- `run_id`: preserved from existing file (this skill does not change run_id)
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Write the updated `implementation_architecture.json` back to `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`.
- Step 5.2: Return the SkillResult payload to the invoking agent. If any gap risk indicators were identified in Step 2.6, they must be included in the SkillResult payload's `flagged_gap_risks` array so the invoking agent can invoke decision-log-update. This skill does not write to `docs/tier4_orchestration_state/decision_log/`.

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Risks not in Tier 3 seeds must be flagged for operator review, not silently added"

**Decision point in execution logic:** Step 2.6 — at the point gap risk indicators are identified from the WP activity catalogue and milestone scan.

**Exact failure condition:** Any risk entry that is NOT derived from a seed in `docs/tier3_project_instantiation/architecture_inputs/risks.json` is written to the `risk_register` array in `implementation_architecture.json` (i.e., added to the register without being in Tier 3 seeds). Equivalently: the skill creates a new risk entry from its own analysis of WP activities and writes it directly to the register rather than flagging it for operator review.

**Enforcement mechanism:** Step 2.6 is the boundary enforcement point. When gap risk indicators (A, B, or C) are identified: the indicator is recorded in the `flagged_gap_risks` array of the SkillResult payload — NEVER added to the `risk_register` in `implementation_architecture.json`. The `risk_register` written to the output file must contain only entries derived from risk seed entries in `risks.json` (Step 2.5). After building the risk_register (Step 2.7), the skill must count entries and verify: `risk_register.length == risks.json seed count`. If any discrepancy exists: return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="risk_register contains <n> entries but only <m> risk seeds exist in risks.json; unsourced risks must not be added to the register; they must be flagged for operator review per skill constitutional constraints and CLAUDE.md §13.3"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION"). No `implementation_architecture.json` update written.

**Hard failure confirmation:** Yes — adding unsourced risks to the register is a constitutional violation per CLAUDE.md §13.3; flagging is the only permitted response.

**CLAUDE.md §13 cross-reference:** §13.3 — "Inventing project facts … not present in Tier 3." Risk entries not in Tier 3 seeds are unvalidated project facts that must not be finalised without operator confirmation.

---

### Constraint 2: "Mitigation measures must be traceable to project activities, not generic"

**Decision point in execution logic:** Step 2.5 — at the point each risk entry's `mitigation` field is constructed.

**Exact failure condition:** Any `mitigation` string in a risk_register entry does not contain a specific reference to a task_id, deliverable_id, or WP name from the WP activity catalogue (Step 2.2). Equivalently: the mitigation text is a generic statement ("regular monitoring", "the consortium will manage this risk", "contingency plans will be developed") without naming a specific project activity from wp_structure.json or gantt.json.

**Enforcement mechanism:** In Step 2.5, after constructing the `mitigation` string for each risk entry: the skill must verify that the mitigation text contains at least one reference to a `task_id` or `deliverable_id` from the WP activity catalogue, using the format: "addressed in [task_title] (task_id: [task_id], WP[n])". If the `mitigation_seed` from `risks.json` does not relate to any catalogued activity: the mitigation must be written as-is with `mitigation_traceability_issue: true` — but NOT silently padded with a fabricated activity reference. If `mitigation_traceability_issue` is set to true for any entry: the invoking agent must be notified via the SkillResult payload so it can request operator review. Writing a generic mitigation without traceability note when catalogue matches exist is a constitutional violation: return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="Risk <risk_id> mitigation text has no traceable project activity reference despite available WP activity catalogue entries; mitigations must trace to project activities per skill constitutional constraints and CLAUDE.md §10.5"). No output written.

**Failure output:** Entries with `mitigation_traceability_issue: true` → written to register with flag (not a SkillResult failure). Mitigation without traceability when catalogue matches exist → SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION").

**Hard failure confirmation:** Yes for the fabrication case. For genuinely unmatched seeds: explicit `mitigation_traceability_issue` flag is the correct hard-declared response (not suppression).

**CLAUDE.md §13 cross-reference:** §10.5 — every material claim must be traceable to a Tier 1–4 source. Mitigation measures that reference project activities must name specific activities. §13.3 — generic mitigations not grounded in Tier 3/4 data are unverifiable project facts.

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier3_project_instantiation/architecture_inputs/risks.json` does not exist → `failure_reason="risks.json not found; risk seeds must be provided in Tier 3 before risk register can be built"`
- Step 1.2: `risks.json` contains zero entries → `failure_reason="risks.json is empty; at least one risk seed is required"`
- Step 1.3: `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` is absent or schema mismatch → `failure_reason="wp_structure.json not found or schema mismatch"`
- Step 1.4: `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` is absent or schema mismatch → `failure_reason="gantt.json not found or schema mismatch"`
- Step 1.5: `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` does not exist → `failure_reason="implementation_architecture.json not found; governance-model-builder must run first"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill reads schema-validated canonical artifacts (wp_structure.json and gantt.json). Schema mismatch conditions are captured in Step 1.3 and Step 1.4 as MISSING_INPUT (per the existing Input Validation Sequence). If `implementation_architecture.json` has an unexpected schema_id detected at Step 2.7: `failure_reason="implementation_architecture.json schema_id does not match 'orch.phase6.implementation_architecture.v1'"`.

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Skill halts immediately.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
- Constraint 1 (risks not in Tier 3 seeds must be flagged, not silently added): At Step 2.7, `risk_register.length` does not equal the count of risk seeds in `risks.json` — meaning an unsourced risk was added to the register → `failure_reason="risk_register contains <n> entries but only <m> risk seeds exist in risks.json; unsourced risks must not be added to the register; they must be flagged for operator review per skill constitutional constraints and CLAUDE.md §13.3"`
- Constraint 2 (mitigation measures traceable to project activities): A `mitigation` string does not contain a specific reference to a task_id or deliverable_id when catalogue matches exist → `failure_reason="Risk <risk_id> mitigation text has no traceable project activity reference despite available WP activity catalogue entries; mitigations must trace to project activities per skill constitutional constraints and CLAUDE.md §10.5"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the failure.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
No INCOMPLETE_OUTPUT conditions are explicitly defined. Write errors at Step 5.1 should return `failure_reason="implementation_architecture.json (risk_register field) could not be written"`.

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
No CONSTITUTIONAL_HALT conditions are defined for this skill. Constitutional constraint failures (unsourced risks in register, untraceable mitigations) are handled as CONSTRAINT_VIOLATION. Gap risk indicators from Step 2.6 are returned in the SkillResult payload's `flagged_gap_risks` array — they are never added to the register and do not trigger CONSTITUTIONAL_HALT.

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

### Canonical Artifact: `implementation_architecture.json` (risk_register field, merge update)

**Schema ID verified:** `orch.phase6.implementation_architecture.v1` ✓ (preserved from existing file at Step 2.7)

**Required fields checked (this skill's scope — risk_register subschema):**

| Field | Required | Status | Notes |
|-------|----------|--------|-------|
| schema_id | true | ✓ Preserved | Skill does not change schema_id |
| run_id | true | ✓ Preserved | Skill does not change run_id |
| artifact_status | false | ✓ Absent at write time | Runner-stamped post-gate |
| risk_register | true | ✓ Implemented | Built in Step 2.5; each entry has risk_id, description, category (enum: technical/financial/organisational/ethical/external/other), likelihood (enum: low/medium/high), impact (enum: low/medium/high), mitigation (non-empty), responsible_partner |
| governance_matrix, management_roles, ethics_assessment, instrument_sections_addressed | true | ✓ Preserved unchanged | Read at Step 2.7 and re-written; this skill does not modify these fields |

**Reads_from compliance:** risk_register entries derived exclusively from declared reads_from (risks.json seeds + WP activity catalogue from wp_structure.json + milestone monitoring points from gantt.json). valid_partner_ids is supplied by the invoking agent as context (partners.json explicitly excluded from reads_from per Step 2.4). No external fields introduced.

**Corrections applied:** None. Output Construction enforces enum-compliant category, likelihood, and impact values, and preserves all non-risk_register fields by merge.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
