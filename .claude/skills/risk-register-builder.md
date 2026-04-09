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

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
