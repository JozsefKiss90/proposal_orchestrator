---
skill_id: concept-call-binding-derivation
purpose_summary: >
  Derive the Tier 3 call binding artifacts (topic_mapping.json and compliance_profile.json)
  from the concept refinement summary and Tier 2B extracted files. Performs deterministic,
  mechanical transformation of topic_mapping_rationale entries into structured mappings
  and derives compliance flags from call constraints and eligibility conditions.
used_by_agents:
  - concept_refiner
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json
  - docs/tier2b_topic_and_call_sources/extracted/call_constraints.json
  - docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json
  - docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json
  - docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
writes_to:
  - docs/tier3_project_instantiation/call_binding/topic_mapping.json
  - docs/tier3_project_instantiation/call_binding/compliance_profile.json
constitutional_constraints:
  - "topic_mapping entries must be derived from topic_mapping_rationale in concept_refinement_summary.json, not invented"
  - "compliance_profile flags must be derived from Tier 2B call_constraints and eligibility_conditions, not assumed from generic programme knowledge"
  - "Must fail closed if concept_refinement_summary.json is absent or empty"
---

## Input Access (TAPM Mode)

Read the files listed in the Declared Inputs section from disk using the Read tool.
Read `concept_refinement_summary.json` first — this is the mandatory primary input containing `topic_mapping_rationale`.
Read `call_constraints.json` if present — provides call-specific constraints for compliance profile derivation.
Read `eligibility_conditions.json` if present — provides eligibility conditions for compliance profile derivation.
Read `expected_outcomes.json` — required for completeness verification of the topic_mapping.
Read `scope_requirements.json` if present — provides scope-derived compliance data.
Do not read files outside the declared input set.
Return your output as a single JSON object with two keys: `topic_mapping` (containing a `mappings` array) and `compliance_profile` (containing the four required fields). Do NOT include `schema_id`, `run_id`, or `artifact_status` — these are Tier 3 source artifacts. Returning an empty object `{}` for either artifact is invalid and will be treated as a failure.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Purpose |
|------|--------------------|-----------------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | concept_refinement_summary.json — Tier 4 phase output | `topic_mapping_rationale` (object keyed by outcome_id; each entry: topic_element_id, mapping_to_concept, tier2b_source_ref, tier3_evidence_ref) | Primary data source for topic_mapping derivation; each rationale entry is mechanically transformed into a mapping entry |
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | call_constraints.json — Tier 2B extracted (optional) | Constraint entries: constraint_id, description, constraint_type, source_section, source_document | Provides call-specific constraints for compliance profile flags; optional — use conservative defaults if absent |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | eligibility_conditions.json — Tier 2B extracted (optional) | Condition entries: condition_id, description, condition_type, source_section, source_document | Provides eligibility conditions for compliance profile; optional — set eligibility_confirmed to false if absent |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | expected_outcomes.json — Tier 2B extracted | Expected outcome entries: outcome_id, description | Required for completeness check: every outcome_id must appear in the derived topic_mapping |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | scope_requirements.json — Tier 2B extracted (optional) | Scope requirement entries | Provides scope-derived compliance data (gender plan, open science); optional |

### Outputs

| Path | Artifact | Required Fields | Derivation Source |
|------|----------|-----------------|-------------------|
| `docs/tier3_project_instantiation/call_binding/topic_mapping.json` | topic_mapping.json — Tier 3 call binding | `mappings` (array, non-empty; each item: topic_element_id, tier2b_source_ref, tier3_evidence_ref, mapping_description) | Mechanically derived 1:1 from topic_mapping_rationale entries in concept_refinement_summary.json |
| `docs/tier3_project_instantiation/call_binding/compliance_profile.json` | compliance_profile.json — Tier 3 call binding | `eligibility_confirmed` (boolean), `ethics_review_required` (boolean), `gender_plan_required` (boolean), `open_science_requirements` (array of strings) | Derived from call_constraints.json + eligibility_conditions.json + scope_requirements.json with conservative defaults |

**Note:** Both outputs are Tier 3 source artifacts — they do NOT carry `schema_id`, `run_id`, or `artifact_status`.

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — read `concept_refinement_summary.json`. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="concept_refinement_summary.json not found; concept-alignment-check must run before concept-call-binding-derivation") and halt.
- Step 1.2: Non-empty check — confirm `concept_refinement_summary.json` is a non-empty JSON object. If empty `{}`: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="concept_refinement_summary.json is empty") and halt.
- Step 1.3: Field check — confirm `topic_mapping_rationale` field exists and is a non-empty object in the summary. If absent or empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="topic_mapping_rationale is absent or empty in concept_refinement_summary.json; concept-alignment-check did not produce rationale entries") and halt.
- Step 1.4: Presence check — read `expected_outcomes.json`. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="expected_outcomes.json not found; required for completeness verification") and halt.
- Step 1.5: Presence check — attempt to read `call_constraints.json`. If absent: log as Assumed; continue with conservative defaults for compliance profile.
- Step 1.6: Presence check — attempt to read `eligibility_conditions.json`. If absent: log as Assumed; set `eligibility_confirmed` to `false` (conservative default).
- Step 1.7: Presence check — attempt to read `scope_requirements.json`. If absent: continue without scope-derived compliance data.

### 2. Derive topic_mapping (mechanical transformation)

- Step 2.1: For each entry in `topic_mapping_rationale` from concept_refinement_summary.json, create a corresponding entry in the `mappings` array with:
  - `topic_element_id`: copied from the rationale entry's `topic_element_id`
  - `tier2b_source_ref`: copied from the rationale entry's `tier2b_source_ref`
  - `tier3_evidence_ref`: copied from the rationale entry's `tier3_evidence_ref`
  - `mapping_description`: copied from the rationale entry's `mapping_to_concept`
- Step 2.2: Completeness check — build set A = {outcome_id for all entries in expected_outcomes.json} and set B = {topic_element_id for all entries in mappings}. If any element in A is missing from B: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Expected outcome <missing_id> has no entry in topic_mapping; topic_mapping_rationale in concept_refinement_summary.json was incomplete") and halt.
- Step 2.3: Non-empty check — confirm `mappings` array is non-empty. If empty: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="mappings array is empty; no topic mapping entries could be derived") and halt.

### 3. Derive compliance_profile (flag extraction)

- Step 3.1: `eligibility_confirmed`: Set to `true` if `eligibility_conditions.json` is present and no conditions are explicitly contradicted by the concept (check against scope_conflict_log in the summary if available). Set to `false` if eligibility_conditions.json is absent or any condition appears contradicted. When uncertain, set to `false` (conservative).
- Step 3.2: `ethics_review_required`: Set to `true` if any constraint in `call_constraints.json` has `constraint_type: "scope"` or description mentioning ethics review. Set to `false` only when no ethics triggers are found in any input. When uncertain, set to `true` (conservative).
- Step 3.3: `gender_plan_required`: Set to `true` if any scope requirement or call constraint mentions gender equality plan, gender dimension, or gender-related requirements. Default to `true` (conservative).
- Step 3.4: `open_science_requirements`: Extract from call constraints and scope requirements any requirements related to open access, open data, FAIR principles, or open science mandates. Return as an array of requirement description strings. If none found, return an empty array `[]`.

### 4. Output Construction

Return a single JSON object with exactly two keys:

**`topic_mapping`:**
- `mappings`: derived from Step 2.1 — array of `{topic_element_id, tier2b_source_ref, tier3_evidence_ref, mapping_description}` — must be non-empty

**`compliance_profile`:**
- `eligibility_confirmed`: derived from Step 3.1 — boolean
- `ethics_review_required`: derived from Step 3.2 — boolean
- `gender_plan_required`: derived from Step 3.3 — boolean
- `open_science_requirements`: derived from Step 3.4 — array of strings (may be empty `[]`)

Do NOT include `schema_id`, `run_id`, or `artifact_status` in either output.

## Constitutional Constraint Enforcement

### Constraint 1: "topic_mapping entries must be derived from topic_mapping_rationale, not invented"

**Decision point:** Step 2.1 — at the point each mapping entry is created from a rationale entry.

**Enforcement:** Every field in each mapping entry must be copied directly from the corresponding topic_mapping_rationale entry. No mapping entry may be created that does not have a corresponding rationale entry. No fields may be invented or inferred beyond what the rationale provides.

**CLAUDE.md cross-reference:** §13.2 — must not invent call constraints not present in source. §10.5 — every claim must identify its source.

### Constraint 2: "compliance_profile flags must be derived from Tier 2B sources, not assumed"

**Decision point:** Steps 3.1–3.4 — at the point each compliance flag is set.

**Enforcement:** Each flag must be derived from reading the actual Tier 2B input files (call_constraints.json, eligibility_conditions.json, scope_requirements.json). When inputs are absent, conservative defaults are used and explicitly noted. Generic programme knowledge must not substitute for reading the Tier 2B files.

**CLAUDE.md cross-reference:** §13.9 — generic programme knowledge may not substitute for Tier 2B source documents.

### Constraint 3: "Must fail closed if concept_refinement_summary.json is absent or empty"

**Decision point:** Steps 1.1–1.3.

**Enforcement:** If the summary is absent, empty, or lacks topic_mapping_rationale, the skill halts immediately with MISSING_INPUT. No partial output is written.

## Failure Protocol

### MISSING_INPUT

**Trigger conditions:**
- Step 1.1: `concept_refinement_summary.json` does not exist
- Step 1.2: `concept_refinement_summary.json` is empty `{}`
- Step 1.3: `topic_mapping_rationale` is absent or empty in the summary
- Step 1.4: `expected_outcomes.json` does not exist

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`
**Artifact write behavior:** No artifact written. Skill halts immediately.

### INCOMPLETE_OUTPUT

**Trigger conditions:**
- Step 2.2: An expected outcome from expected_outcomes.json has no entry in mappings
- Step 2.3: mappings array is empty

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`
**Artifact write behavior:** No artifact written.

### CONSTITUTIONAL_HALT

**Trigger conditions:**
- A mapping entry would be created without a corresponding topic_mapping_rationale entry (fabricated mapping)

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`
**Artifact write behavior:** Immediate halt. No output written.

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written when any failure category fires.
3. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

## Schema Validation

### Tier 3 Artifact: `topic_mapping.json`

**Canonical schema in `artifact_schema_specification.yaml`:** Section 6.2 — `tier3_source_schemas.topic_mapping`.

**Schema governance:** Tier 3 source artifact (`provenance_class: manually_placed`). No `schema_id`, `run_id`, or `artifact_status` fields.

**Required fields:**
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `mappings` | array | yes | Non-empty; each item: topic_element_id (string), tier2b_source_ref (string), tier3_evidence_ref (string), mapping_description (string) |

### Tier 3 Artifact: `compliance_profile.json`

**Canonical schema in `artifact_schema_specification.yaml`:** Section 6.3 — `tier3_source_schemas.compliance_profile`.

**Schema governance:** Tier 3 source artifact (`provenance_class: manually_placed`). No `schema_id`, `run_id`, or `artifact_status` fields.

**Required fields:**
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `eligibility_confirmed` | boolean | yes | Must be present |
| `ethics_review_required` | boolean | yes | Must be present |
| `gender_plan_required` | boolean | yes | Must be present |
| `open_science_requirements` | array of strings | yes | Must be present; may be empty `[]` |

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping abstention (Tier 3), and scheduler separation — must conform to that contract.
