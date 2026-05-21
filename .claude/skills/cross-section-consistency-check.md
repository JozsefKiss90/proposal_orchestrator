---
skill_id: cross-section-consistency-check
purpose_summary: >
  Check cross-section consistency of the three criterion-aligned sections and
  produce the assembled Part B draft. Verifies objectives, WP references,
  partner names, deliverables, milestones, KPIs, impact claims, budget
  references, and terminology are consistent across all three sections.
used_by_agents:
  - proposal_integrator
reads_from:
  - docs/tier5_deliverables/proposal_sections/
  - docs/tier3_project_instantiation/
  - docs/tier2a_instrument_schemas/application_forms/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
writes_to:
  - docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json
constitutional_constraints:
  - "Must not silently normalise contradictions"
  - "Must flag all inconsistencies in the consistency_log"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool.

**Declared input files to read (in order):**
1. `docs/tier5_deliverables/proposal_sections/excellence_section.json` -- Excellence section artifact; schema `orch.tier5.excellence_section.v1`
2. `docs/tier5_deliverables/proposal_sections/impact_section.json` -- Impact section artifact; schema `orch.tier5.impact_section.v1`
3. `docs/tier5_deliverables/proposal_sections/implementation_section.json` -- Implementation section artifact; schema `orch.tier5.implementation_section.v1`
4. `docs/tier3_project_instantiation/` -- project data for authoritative reference (use Glob to discover, then Read relevant files: architecture_inputs/objectives.json, consortium/partners.json)
5. `docs/tier2a_instrument_schemas/application_forms/` -- application form template for Part B section ordering (use Glob to list, then Read)

**Boundary constraints:**
- Do not read files outside the declared input set.
- Do not assume implicit context or reconstruct inputs from memory.
- Read each required file explicitly before using it.
- Base all reasoning ONLY on retrieved file content.

Return a SINGLE valid JSON object matching the output schema below.
Do not include explanations outside the JSON.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier5_deliverables/proposal_sections/excellence_section.json` | Excellence section | criterion, sub_sections[].content, sub_sections[].sub_section_id, validation_status, traceability_footer | `orch.tier5.excellence_section.v1` | Excellence section content for cross-checking; objectives, methodology, concept claims |
| `docs/tier5_deliverables/proposal_sections/impact_section.json` | Impact section | criterion, sub_sections[].content, impact_pathway_refs, dec_coverage, validation_status, traceability_footer | `orch.tier5.impact_section.v1` | Impact section content for cross-checking; impact claims, pathway references, DEC coverage |
| `docs/tier5_deliverables/proposal_sections/implementation_section.json` | Implementation section | criterion, sub_sections[].content, wp_table_refs, gantt_ref, milestone_refs, risk_register_ref, validation_status, traceability_footer | `orch.tier5.implementation_section.v1` | Implementation section content for cross-checking; WP references, partner names, deliverables, milestones |
| `docs/tier3_project_instantiation/` | Project data | Authoritative partner names, objectives, consortium composition | N/A -- Tier 3 root | Ground-truth reference for resolving cross-section naming discrepancies |
| `docs/tier2a_instrument_schemas/application_forms/` | Application form template | Part B section ordering, structural requirements | N/A -- source directory | Section ordering authority for RIA/IA Part B assembly |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` | Assembled Part B draft | `orch.tier5.part_b_assembled_draft.v1` | schema_id, run_id, sections (array: section_id, criterion, order, artifact_path, word_count), consistency_log (array: check_id, description, sections_checked, status[consistent/inconsistency_flagged/resolved], inconsistency_note), traceability_footer (primary_sources[], no_unsupported_claims_declaration, derivation_note) | Yes | sections: ordered array from three input section artifacts; consistency_log: results of all cross-section consistency checks; traceability_footer: inherited traceability from section artifacts |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` | Yes -- artifact_id: a_t5_assembled_drafts | n08d_assembly |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check -- confirm `docs/tier5_deliverables/proposal_sections/excellence_section.json` exists and is non-empty. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="excellence_section.json not found; all three criterion-aligned sections must be present for assembly") and halt.
- Step 1.2: Presence check -- confirm `docs/tier5_deliverables/proposal_sections/impact_section.json` exists and is non-empty. If absent: return failure with `MISSING_INPUT`.
- Step 1.3: Presence check -- confirm `docs/tier5_deliverables/proposal_sections/implementation_section.json` exists and is non-empty. If absent: return failure with `MISSING_INPUT`.
- Step 1.4: Schema check -- confirm `excellence_section.json` has `schema_id` = "orch.tier5.excellence_section.v1". If mismatch: return failure with `MALFORMED_ARTIFACT`.
- Step 1.5: Schema check -- confirm `impact_section.json` has `schema_id` = "orch.tier5.impact_section.v1". If mismatch: return failure with `MALFORMED_ARTIFACT`.
- Step 1.6: Schema check -- confirm `implementation_section.json` has `schema_id` = "orch.tier5.implementation_section.v1". If mismatch: return failure with `MALFORMED_ARTIFACT`.
- Step 1.7: Read Tier 3 project data for authoritative reference. At minimum: `architecture_inputs/objectives.json` and `consortium/partners.json`. If unavailable: continue with degraded cross-checking (section-to-section only, without Tier 3 ground-truth comparison).

### 2. Core Processing Logic

Perform the following cross-section consistency checks. For each check, record a `consistency_log` entry with `check_id`, `description`, `sections_checked`, `status`, and (if applicable) `inconsistency_note`.

**Check CC-01: Objective consistency.**
- Extract objective statements from Excellence section content and Implementation section WP objectives.
- Verify that objectives stated in the Excellence section are consistent with the WP objectives in the Implementation section. Objectives must not contradict each other.
- Cross-check against Tier 3 `objectives.json` if available.
- Status: `consistent` if no contradictions; `inconsistency_flagged` with note if objectives differ materially.

**Check CC-02: WP reference consistency.**
- Extract WP references from all three sections (WP IDs, WP names).
- Verify that WP IDs referenced in the Excellence section (methodology) and Impact section (impact pathway grounding) match the WPs defined in the Implementation section (`wp_table_refs`).
- Status: `inconsistency_flagged` if any WP ID appears in one section but not in the canonical WP list from Implementation.

**Check CC-03: Partner name consistency.**
- Extract all partner names mentioned across all three sections.
- Verify that partner names are consistent (no variant spellings, abbreviation mismatches, or partners appearing in one section but not present in Tier 3).
- Cross-check against Tier 3 `partners.json` if available.
- Status: `inconsistency_flagged` if partner name variants detected or unnamed partners appear.

**Check CC-04: Deliverable ID consistency.**
- Extract deliverable IDs/names from Excellence (methodology deliverables), Impact (output deliverables for impact pathways), and Implementation (deliverable table).
- Verify consistent naming and ID references.
- Status: `inconsistency_flagged` if deliverable IDs do not match across sections.

**Check CC-05: Milestone ID consistency.**
- Extract milestone references from Impact (impact pathway milestones) and Implementation (milestone table, `milestone_refs`).
- Verify consistent naming and ID references.
- Status: `inconsistency_flagged` if milestone IDs do not match.

**Check CC-06: KPI consistency.**
- Extract KPIs from Impact section (impact pathway KPIs) and Implementation section (if any KPIs referenced in work plan).
- Verify consistent naming and target values.
- Status: `inconsistency_flagged` if KPI definitions or target values differ.

**Check CC-07: Impact claim grounding.**
- For each impact claim in the Impact section, verify that the cited project mechanism (WP, deliverable, task) exists in the Implementation section.
- Status: `inconsistency_flagged` if an impact claim references a WP or deliverable not present in Implementation.

**Check CC-08: Budget/resource claim consistency.**
- If any section references budget figures or resource allocations (person-months, costs), verify that these are consistent across all three sections.
- Status: `inconsistency_flagged` if budget/resource values differ between sections.

**Check CC-09: Terminology consistency.**
- Check for key technical terms, methodology names, and acronyms used across all three sections.
- Verify consistent use of terminology (same concept should use the same term).
- Status: `inconsistency_flagged` if significant terminology inconsistencies detected (minor variations are acceptable).

**Check CC-10: Section ordering and completeness.**
- Verify that all three sections are present and correspond to the Part B structure: Section 1 (Excellence), Section 2 (Impact), Section 3 (Implementation).
- Verify section ordering matches the application form template.
- Status: `consistent` if all three present in correct order.

**Check CC-11: Traceability footer consistency.**
- Verify that all three sections have non-empty `traceability_footer.primary_sources` arrays.
- Verify that `no_unsupported_claims_declaration` is consistent with `validation_status.overall_status`.
- Status: `inconsistency_flagged` if a section has `no_unsupported_claims_declaration: true` but `overall_status: unresolved`.

**Check CC-12: Validation status aggregation.**
- Record the `overall_status` from each section's `validation_status`.
- If any section has `overall_status: unresolved`: note this as a cross-section concern for downstream review.
- Status: informational (always `consistent` -- this is a status report, not a consistency check).

### 3. Output Construction

**`part_b_assembled_draft.json`:**

```json
{
  "schema_id": "orch.tier5.part_b_assembled_draft.v1",
  "run_id": "<from task metadata>",
  "sections": [
    {
      "section_id": "excellence",
      "criterion": "Excellence",
      "order": 1,
      "artifact_path": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
      "word_count": "<from excellence_section.json>"
    },
    {
      "section_id": "impact",
      "criterion": "Impact",
      "order": 2,
      "artifact_path": "docs/tier5_deliverables/proposal_sections/impact_section.json",
      "word_count": "<from impact_section.json>"
    },
    {
      "section_id": "implementation",
      "criterion": "Quality and efficiency of the implementation",
      "order": 3,
      "artifact_path": "docs/tier5_deliverables/proposal_sections/implementation_section.json",
      "word_count": "<from implementation_section.json>"
    }
  ],
  "consistency_log": [
    {
      "check_id": "CC-01",
      "description": "Objective consistency across Excellence and Implementation sections",
      "sections_checked": ["excellence", "implementation"],
      "status": "consistent",
      "inconsistency_note": null
    }
  ]
}
```

The `sections` array must be ordered: Excellence (1), Impact (2), Implementation (3).

The `consistency_log` array must contain one entry per check (CC-01 through CC-12). All 12 checks are mandatory. Checks that find no issues must record `status: "consistent"`. Checks that find issues must record `status: "inconsistency_flagged"` with a non-empty `inconsistency_note`.

**Source attribution in consistency_log entries (GATE-CRITICAL for traceability):**
Each `consistency_log` entry MUST include either:
- `source_refs`: an array of artifact paths used to perform that check (e.g., `["docs/tier3_project_instantiation/architecture_inputs/objectives.json", "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"]`), OR
- `source_basis`: a compact string naming the artifact categories used (e.g., `"Tier 3 objectives, Tier 4 wp_structure"`).

This ensures that consistency findings making project-fact assertions are traceable to their source artifacts. Keep references compact — use path-level references, not verbose excerpts.

Word counts are computed by summing `word_count` values across sub-sections within each section artifact.

**`traceability_footer`** — compact traceability summary for the assembled draft:

```json
"traceability_footer": {
  "primary_sources": [
    "docs/tier5_deliverables/proposal_sections/excellence_section.json",
    "docs/tier5_deliverables/proposal_sections/impact_section.json",
    "docs/tier5_deliverables/proposal_sections/implementation_section.json",
    "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
    "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
  ],
  "no_unsupported_claims_declaration": true,
  "derivation_note": "Assembled draft inherits section-level proposal claim traceability from referenced section artifacts; this artifact adds only section index and cross-section consistency findings."
}
```

Rules for `traceability_footer`:
- `primary_sources` MUST include:
  - The three section artifact paths (always).
  - `docs/tier3_project_instantiation/architecture_inputs/objectives.json` — if `consistency_log` cites objective titles, measurable targets, or component names.
  - `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` — if `consistency_log` cites outcome titles or output/component names.
  - `docs/tier3_project_instantiation/architecture_inputs/impacts.json` — if `consistency_log` cites impact pathway names.
  - `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` — if `consistency_log` cites WP IDs, deliverables, tasks, milestones, or WP attribution.
  - `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` — if `consistency_log` cites impact pathway mappings or KPIs.
  - `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` — if `consistency_log` cites implementation responsibility or resource architecture.
  - `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` — if CC-08 discusses budget/resource consistency.
- `no_unsupported_claims_declaration`: set to `true` ONLY if ALL `consistency_log` entries have `status: "consistent"` or `status: "resolved"` AND all entries include either `source_refs` or `source_basis`. Set to `false` if ANY entry has `status: "inconsistency_flagged"` or `status: "unresolved"`.
- `derivation_note`: always the fixed string shown above. This is project-agnostic.

### 4. Conformance Stamping

- `schema_id`: set to "orch.tier5.part_b_assembled_draft.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier5_deliverables/assembled_drafts/` if not present.
- Step 5.2: Write `part_b_assembled_draft.json` to `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json`.

## Constitutional Constraint Enforcement

*Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure.*

---

### Constraint 1: "Must not silently normalise contradictions"

**Decision point in execution logic:** Step 2 (all cross-section checks CC-01 through CC-12) -- at the point inconsistencies are detected and recorded in the `consistency_log`.

**Exact failure condition:** An inconsistency is detected during a cross-section check but the `consistency_log` entry records `status: "consistent"` instead of `"inconsistency_flagged"`, thereby silently normalising the contradiction.

**Enforcement mechanism:** For each check in Step 2, the status assignment rule is deterministic:
- If a material difference, contradiction, or naming inconsistency is detected between sections: `status` MUST be `"inconsistency_flagged"` with a non-empty `inconsistency_note`.
- `status: "consistent"` is only permissible when no material difference is detected.
- `status: "resolved"` is only permissible when an inconsistency was detected AND corrected (not applicable in assembly -- this skill does not rewrite section content; `resolved` would be set by a downstream revision).

If any inconsistency is detected but assigned `status: "consistent"`: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Cross-section inconsistency in check <check_id> was silently normalised to 'consistent'; CLAUDE.md Section 12.3 prohibits silently resolving contradictions"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT").

**Hard failure confirmation:** Yes -- silent normalisation of contradictions is a categorical prohibition.

**CLAUDE.md Section 13 cross-reference:** Section 12.3 -- "Contradictions between tiers must be resolved explicitly ... A contradiction must not be silently resolved by selecting the more convenient source."

---

### Constraint 2: "Must flag all inconsistencies in the consistency_log"

**Decision point in execution logic:** Step 3 -- at the point the `consistency_log` array is constructed and the output artifact is assembled.

**Exact failure condition:** (a) The `consistency_log` array has fewer than 12 entries (one per check CC-01 through CC-12); OR (b) an inconsistency detected during Step 2 does not appear as a `consistency_log` entry with `status: "inconsistency_flagged"`.

**Enforcement mechanism:**
- The output MUST contain exactly 12 `consistency_log` entries (CC-01 through CC-12).
- Every inconsistency detected in Step 2 MUST appear in the log.
- If the `consistency_log` would have fewer than 12 entries at write time: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="consistency_log has <n> entries; all 12 cross-section checks (CC-01 through CC-12) must be recorded").

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT").

**Hard failure confirmation:** Yes -- incomplete consistency logging makes the assembly output non-reviewable.

**CLAUDE.md Section 13 cross-reference:** Section 12.1 -- "Every phase output must be reviewable."

<!-- Constitutional constraint enforcement complete -->

## Failure Protocol

*All five failure categories are handled.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `excellence_section.json` absent -> `failure_reason="excellence_section.json not found; all three criterion-aligned sections must be present for assembly"`
- Step 1.2: `impact_section.json` absent -> `failure_reason="impact_section.json not found"`
- Step 1.3: `implementation_section.json` absent -> `failure_reason="implementation_section.json not found"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.4: `excellence_section.json` schema_id mismatch -> `failure_reason="excellence_section.json schema_id mismatch; expected orch.tier5.excellence_section.v1"`
- Step 1.5: `impact_section.json` schema_id mismatch -> `failure_reason="impact_section.json schema_id mismatch; expected orch.tier5.impact_section.v1"`
- Step 1.6: `implementation_section.json` schema_id mismatch -> `failure_reason="implementation_section.json schema_id mismatch; expected orch.tier5.implementation_section.v1"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written.

---

### CONSTRAINT_VIOLATION

No CONSTRAINT_VIOLATION conditions defined; all use CONSTITUTIONAL_HALT or INCOMPLETE_OUTPUT.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 2: `consistency_log` has fewer than 12 entries -> `failure_reason="consistency_log has <n> entries; all 12 checks required"`
- Output JSON missing required fields -> `failure_reason="Output missing required fields per orch.tier5.part_b_assembled_draft.v1"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 1: Inconsistency silently normalised to "consistent" -> `failure_reason="Cross-section inconsistency in check <check_id> was silently normalised; CLAUDE.md Section 12.3"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No `part_b_assembled_draft.json` written.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written when any failure category fires.
3. The invoking agent receives the `SkillResult` and is responsible for logging the failure.
4. Failure is a correct and valid output per CLAUDE.md Section 15.

<!-- Failure protocol complete -->

## Schema Validation

*Validation of Output Construction against `artifact_schema_specification.yaml` for `part_b_assembled_draft.json`.*

---

### Artifact: `part_b_assembled_draft.json`

**Schema ID:** `orch.tier5.part_b_assembled_draft.v1`

**Spec location:** `artifact_schema_specification.yaml` Section 2.1e (Tier 5 deliverables) -- `part_b_assembled_draft` entry.

**Required fields per spec:**
- `schema_id` (string, const "orch.tier5.part_b_assembled_draft.v1")
- `run_id` (string)
- `sections` (array) -- each: section_id, criterion, order (integer), artifact_path; word_count (optional)
- `consistency_log` (array) -- each: check_id, description, sections_checked (array), status (enum: consistent/inconsistency_flagged/resolved), inconsistency_note (optional)
- `artifact_status` (optional, enum [valid, invalid]) -- runner-stamped; must be ABSENT at write time

**Output Construction (Step 3) verification:**
| Field | Set by skill? | Value source | Conformant? |
|-------|---------------|--------------|-------------|
| `schema_id` | Yes (Step 3, Step 4) | const "orch.tier5.part_b_assembled_draft.v1" | Yes |
| `run_id` | Yes (Step 3, Step 4) | invoking agent's run_id | Yes |
| `sections[]` | Yes (Step 3) | three entries: Excellence (1), Impact (2), Implementation (3); each with section_id, criterion, order, artifact_path, word_count | Yes -- all required item_schema fields present; order is integer 1-based |
| `consistency_log[]` | Yes (Step 2, Step 3) | 12 entries (CC-01 through CC-12); each with check_id, description, sections_checked, status (enum-compliant), inconsistency_note | Yes -- status enum restricted to {consistent, inconsistency_flagged, resolved}; all required fields present |
| `traceability_footer` | Yes (Step 3) | primary_sources: three section artifact paths; no_unsupported_claims_declaration: derived from consistency_log statuses; derivation_note: fixed string | Yes -- inherits section-level traceability |
| `artifact_status` | ABSENT at write time (Step 4) | runner stamps post-gate | Yes |

**reads_from compliance:** All declared directories used. Compliant.

**writes_to compliance:** Single path declared. Compliant.

**Gaps identified:** None.

<!-- Schema validation complete -->

## Strengthened Validation Dimensions (GATE-CRITICAL)

The 12 mandatory consistency checks (CC-01 through CC-12) must enforce the following artifact-driven validation dimensions. Each dimension operates purely on canonical artifacts — no heuristics or vague similarity.

**1. Objective Coverage Completeness (CC-01):**
- Load ALL objective IDs from `docs/tier3_project_instantiation/architecture_inputs/objectives.json`.
- Verify: Excellence section enumerates ALL objectives (count must match Tier 3).
- Verify: every objective ID mentioned in Impact/Implementation exists in Tier 3.
- FAIL deterministically if any objective is missing or unrecognized.

**2. Objective Identity Consistency (CC-01):**
- For each objective referenced across sections, the `id` and `title` from Tier 3 must be used canonically.
- No paraphrased or partial objective references allowed.
- If objective has component keyword in title (engine, layer, architecture, protocol, framework, system), that exact title must be used.

**3. Partner Naming Consistency (CC-03):**
- Load `legal_name` and `short_name` for each partner from `consortium/partners.json`.
- When a partner's name appears in section content, it must match either `legal_name` exactly OR `short_name` exactly.
- If `legal_name` has a legal entity suffix (AG, Oy, GmbH, etc.) and the name appears WITHOUT that suffix, flag as `inconsistency_flagged`.
- No mixing of naming forms within a section without explicit mapping.

**4. Deliverable ↔ KPI Alignment (CC-04, CC-06):**
- Load deliverables from `phase3_wp_design/wp_structure.json` and KPIs from `phase5_impact_architecture/impact_architecture.json`.
- Verify: deliverable IDs used in sections match canonical deliverable titles from wp_structure.
- Verify: KPIs are NOT described AS deliverables. A KPI tracked by a deliverable ≠ that deliverable.
- If a deliverable ID is attributed a different purpose across sections, flag CC-04 as `inconsistency_flagged`.

**5. Metric Completeness (CC-06):**
- For each objective referenced in sections, extract ALL quantified targets from `measurable_target` in objectives.json.
- Verify: Impact section preserves ALL metrics (no partial loss of multi-target objectives).
- No partial metric loss: if target says "≥20% X AND ≥15% Y", both values must appear.

**6. Terminology Consistency (CC-09):**
- Extract canonical component/system names from Tier 3 objective titles.
- For each canonical name, identify its stem (name minus component keyword).
- If the stem appears in a section but the full canonical name does NOT, flag as `inconsistency_flagged`.
- Example: stem "External Tool and API Orchestration" found but "External Tool and API Orchestration Layer" absent → flag.

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour -- SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation -- must conform to that contract.
