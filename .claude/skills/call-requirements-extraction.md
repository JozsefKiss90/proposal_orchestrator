---
skill_id: call-requirements-extraction
purpose_summary: >
  Extract binding topic-specific requirements from work programme and call extract
  documents, producing structured output with a source section reference for every
  extracted element.
used_by_agents:
  - call_analyzer
reads_from:
  - docs/tier2b_topic_and_call_sources/work_programmes/
  - docs/tier2b_topic_and_call_sources/call_extracts/
writes_to:
  - docs/tier2b_topic_and_call_sources/extracted/
constitutional_constraints:
  - "Must not invent call requirements not present in source documents"
  - "Must carry source section references for every extracted element"
  - "Must apply Confirmed/Inferred/Assumed/Unresolved status"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier2b_topic_and_call_sources/work_programmes/` | Work programme source documents (PDF/DOCX) for the relevant Horizon Europe cluster | Full document text; section identifiers; topic descriptions; expected outcomes; expected impacts; scope requirements; eligibility conditions; evaluation criteria | N/A — source document directory (dir_non_empty check only) | Primary authoritative source from which all Tier 2B extracted fields are read; every extracted element must carry a section reference back to this directory |
| `docs/tier2b_topic_and_call_sources/call_extracts/` | Call extract documents (PDF/DOCX) for the specific topic | Topic identifier; call deadline; scope narrative; specific conditions; evaluation priority weightings | N/A — source document directory (dir_non_empty check only) | Supplements the work programme with call-specific constraints and priority weighting; used when topic-level detail not fully present in the work programme |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | call_constraints.json | N/A — Tier 2B extracted (not a phase output canonical artifact) | constraint entries with source_section and source_document per item; Confirmed/Inferred/Assumed/Unresolved status per item | No — Tier 2B extracted artifact, not a phase output | Extracted directly from work programme and call extract source documents |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | expected_outcomes.json | N/A — Tier 2B extracted | expected outcome entries with source_section, source_document, and status per item | No | Extracted from work programme expected outcomes sections |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | expected_impacts.json | N/A — Tier 2B extracted | expected impact entries with source_section, source_document, and status per item; impact_id used as join key in Phase 5 | No | Extracted from work programme expected impacts sections |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | scope_requirements.json | N/A — Tier 2B extracted | scope boundary entries with source_section, source_document, and status per item | No | Extracted from topic scope sections of work programme and call extract |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | eligibility_conditions.json | N/A — Tier 2B extracted | eligibility condition entries with source_section, source_document, and status per item | No | Extracted from eligibility and participation conditions in work programme |
| `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | evaluation_priority_weights.json | N/A — Tier 2B extracted | criterion-level weight entries with source_section, source_document per item | No | Extracted from evaluation criteria weighting tables in call extract and work programme |

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | Yes — artifact_id: a_t2b_call_constraints | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | Yes — artifact_id: a_t2b_expected_outcomes | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Yes — artifact_id: a_t2b_expected_impacts | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | Yes — artifact_id: a_t2b_scope_requirements | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | Yes — artifact_id: a_t2b_eligibility_conditions | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | Yes — artifact_id: a_t2b_evaluation_priority_weights | n01_call_analysis |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier2b_topic_and_call_sources/work_programmes/` exists and is non-empty (dir_non_empty). If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="work_programmes/ directory is empty; cannot extract call requirements without source documents") and halt.
- Step 1.2: Presence check — confirm `docs/tier2b_topic_and_call_sources/call_extracts/` exists and is non-empty (dir_non_empty). If empty: log as Assumed (work programme is the sole source) and continue; do not halt.
- Step 1.3: Confirm that the invoking agent has provided the target topic identifier (from `docs/tier3_project_instantiation/call_binding/selected_call.json`) as context. If not provided: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="selected_call topic identifier required to scope extraction") and halt.
- Step 1.4: Confirm source documents in work_programmes/ are readable (not corrupted or inaccessible). If any file is unreadable: log as Unresolved in pre-extraction notes; continue with readable files only, but flag in all output files that coverage may be incomplete.

### 2. Core Processing Logic

- Step 2.1: Index all files in `docs/tier2b_topic_and_call_sources/work_programmes/` and `docs/tier2b_topic_and_call_sources/call_extracts/`. For each file, record the filename and parse the section structure (section identifiers and headings).
- Step 2.2: Locate sections in the work programme documents that correspond to the target topic identifier from selected_call.json. Mark these sections as the primary extraction scope.
- Step 2.3: Extract **call_constraints** entries: for each section stating what the call requires, excludes, or mandates (e.g., technology readiness levels, excluded activities, mandatory consortium types), create one entry. Each entry must carry: a `constraint_id` (unique, e.g., "CC-01"), `description` (verbatim or close paraphrase of the source text), `source_section` (e.g., "Section 2.1.3"), `source_document` (filename), and `status`. Status assignment rules: Confirmed = the constraint is explicitly stated as a requirement, exclusion, or mandate in the source text. Inferred = the constraint is logically derivable from stated requirements (must state the derivation chain in an `inference_note` field). Assumed = the constraint is structurally expected for this instrument type but not explicitly stated (must declare the assumption in an `assumption_note` field). Unresolved = the work programme and call extract give conflicting signals about the constraint (must name both sources and describe the conflict in a `conflict_note` field).
- Step 2.4: Extract **expected_outcomes** entries: for each outcome statement in the work programme (typically under "Expected outcomes" headings), create one entry. Each entry must carry: `outcome_id` (unique, e.g., "EO-01"), `description`, `source_section`, `source_document`, `status` (same assignment rules as Step 2.3). The `outcome_id` value becomes the join key for Phase 2 alignment checking.
- Step 2.5: Extract **expected_impacts** entries: for each impact statement in the work programme (typically under "Expected impacts" headings), create one entry. Each entry must carry: `impact_id` (unique, e.g., "EI-01"), `description`, `source_section`, `source_document`, `status`. The `impact_id` value is the join key for Phase 5 impact pathway mapping and must be preserved exactly as assigned here throughout all downstream phases.
- Step 2.6: Extract **scope_requirements** entries: for each statement defining the thematic scope, required focus areas, or explicitly excluded topics, create one entry. Each entry must carry: `scope_element_id` (unique, e.g., "SR-01"), `description`, `boundary_type` (one of: `required_focus`, `excluded_topic`, `conditional_requirement`), `source_section`, `source_document`, `status`.
- Step 2.7: Extract **eligibility_conditions** entries: for each participation eligibility condition (minimum consortium size, partner type requirements, country restrictions, ethics requirements), create one entry. Each entry must carry: `condition_id` (unique, e.g., "EC-01"), `description`, `condition_type` (one of: `consortium_composition`, `partner_type`, `country_restriction`, `ethics`, `other`), `source_section`, `source_document`, `status`.
- Step 2.8: Extract **evaluation_priority_weights** entries: for each evaluation criterion with an explicit or implied weighting (often in weighting tables or "evaluation criteria" sections of the call extract), create one entry. Each entry must carry: `criterion_id` (matching the form criterion label, e.g., "Excellence", "Impact"), `weight` (numeric percentage if stated, null if not stated), `priority_note` (any call-specific priority statement), `source_section`, `source_document`, `status`.
- Step 2.9: If the call extract contains information that supplements or conflicts with the work programme for any of the six extraction categories above: for supplementary information, add additional entries from the call extract with `source_document` pointing to the call extract file. For conflicting information: set `status` to "Unresolved" on all affected entries and populate `conflict_note` naming both sources.
- Step 2.10: Count total entries across all six output files. If any output file would be empty (zero entries): do not write that file. Return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="<filename> contains zero extractable entries; source document may not correspond to the target topic") and halt.

### 3. Output Construction

For each of the six output JSON files, the structure is an array of entries as defined below.

**`call_constraints.json`:**
- Root field: `constraints` — array of entries produced in Step 2.3
- Each entry: `constraint_id` (string, unique), `description` (string), `constraint_type` (string, one of: eligibility/scope/methodological/partnership/reporting/other — required per tier2b_extracted_schemas.call_constraints spec), `source_section` (string, non-empty), `source_document` (string, filename from work_programmes/ or call_extracts/), `status` (one of: "Confirmed", "Inferred", "Assumed", "Unresolved"), and conditionally: `inference_note` (if Inferred), `assumption_note` (if Assumed), `conflict_note` (if Unresolved)

**`expected_outcomes.json`:**
- Root field: `outcomes` — array of entries produced in Step 2.4 (matches tier2b_extracted_schemas.expected_outcomes spec)
- Each entry: `outcome_id` (string, unique), `description` (string), `source_section` (string), `source_document` (string), `status` (Confirmed/Inferred/Assumed/Unresolved), and conditional note fields

**`expected_impacts.json`:**
- Root field: `impacts` — array of entries produced in Step 2.5 (matches tier2b_extracted_schemas.expected_impacts spec)
- Each entry: `impact_id` (string, unique — preserved as join key for Phase 5), `description` (string), `impact_type` (string, one of: scientific/societal/economic/policy/technological/environmental — required per spec), `source_section` (string), `source_document` (string), `status`, and conditional note fields

**`scope_requirements.json`:**
- Root field: `requirements` — array of entries produced in Step 2.6 (matches tier2b_extracted_schemas.scope_requirements spec)
- Each entry: `requirement_id` (string, unique), `description` (string), `mandatory` (boolean — required per spec; true if the source marks the scope element as required/must-do, false if it is a conditional or optional scope element), `source_section` (string), `source_document` (string), `status`, and conditional note fields

**`eligibility_conditions.json`:**
- Root field: `conditions` — array of entries produced in Step 2.7 (matches tier2b_extracted_schemas.eligibility_conditions spec)
- Each entry: `condition_id` (string, unique), `description` (string), `condition_type` (string, one of: consortium_composition/trl_level/budget_limit/geographic/open_access/other — enum per spec), `source_section` (string), `source_document` (string), `status`, and conditional note fields

**`evaluation_priority_weights.json`:**
- Root field: `criteria` — array of entries produced in Step 2.8 (matches tier2b_extracted_schemas.evaluation_priority_weights spec)
- Each entry: `criterion_id` (string — must match the evaluation form criterion label for the active instrument), `criterion_name` (string — required per spec), `weight` (number or null), `priority_notes` (string, optional — spec field name), `source_section` (string), `source_document` (string), `status`, and conditional note fields

### 4. Conformance Stamping

These are Tier 2B extracted artifacts, not phase output canonical artifacts. No `schema_id`, `run_id`, or `artifact_status` field applies. Do not add these fields.

### 5. Write Sequence

- Step 5.1: Write `call_constraints.json` to `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json`
- Step 5.2: Write `expected_outcomes.json` to `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json`
- Step 5.3: Write `expected_impacts.json` to `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json`
- Step 5.4: Write `scope_requirements.json` to `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json`
- Step 5.5: Write `eligibility_conditions.json` to `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json`
- Step 5.6: Write `evaluation_priority_weights.json` to `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json`
- All six files must be written before the skill returns success. If any write fails: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="<filename> could not be written") and halt.

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Must not invent call requirements not present in source documents"

**Decision point in execution logic:** Step 2.3–2.9 — at the moment each extracted entry is created. Every constraint, outcome, impact, scope element, eligibility condition, and evaluation weight entry is subject to this constraint at the instant it is written.

**Exact failure condition:** Any extracted entry is assigned `status: "Confirmed"` or `status: "Inferred"` without a non-empty `source_section` and a non-empty `source_document` that identifies an actual file in `docs/tier2b_topic_and_call_sources/work_programmes/` or `docs/tier2b_topic_and_call_sources/call_extracts/`. Equivalently: any entry is constructed from agent prior knowledge of Horizon Europe rather than from the source documents read in Step 2.1–2.2.

**Enforcement mechanism — deterministic branching rule:**

IF `status ∈ {Confirmed, Inferred}`:
→ `source_section` MUST be non-empty AND `source_document` MUST be non-empty
→ If either is absent → CONSTITUTIONAL_HALT immediately

IF `status ∈ {Assumed, Unresolved}`:
→ `source_section` and `source_document` MAY be absent
→ BUT the entry MUST include `assumption_note` (if Assumed) OR `conflict_note` (if Unresolved) explaining the absence
→ If neither note field is present when source fields are absent → CONSTRAINT_VIOLATION

If the skill cannot produce any confirmed entry without relying on prior knowledge, it must return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="No extractable entries can be sourced from the provided documents; inventing call requirements is a constitutional prohibition per CLAUDE.md §13.2") and halt. Partial extraction (some Confirmed, some Unresolved) is permitted, but any entry emitted as Confirmed must have a traceable source.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No partial output written to `docs/tier2b_topic_and_call_sources/extracted/`. This skill does not have write scope to the decision log — the invoking agent must log the halt.

**Hard failure confirmation:** Yes — immediate halt; no six output files are written if this constraint is triggered at halt level.

**CLAUDE.md §13 cross-reference:** §13.2 — "Inventing call constraints, scope requirements, expected outcomes, or expected impacts not present in Tier 2B source documents."

---

### Constraint 2: "Must carry source section references for every extracted element"

**Decision point in execution logic:** Step 3 (Output Construction) — at the point each entry object is constructed for any of the six output JSON files.

**Exact failure condition:** Any entry in any of the six output JSON files has an empty string or null value for `source_section` or `source_document`, AND the entry has `status ∈ {Confirmed, Inferred}`.

**Enforcement mechanism:** Apply the deterministic branching rule from Constraint 1. After constructing each entry but before appending it to the output array:

IF `status ∈ {Confirmed, Inferred}` AND (`source_section` is absent/empty OR `source_document` is absent/empty):
→ CONSTITUTIONAL_HALT immediately — return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Entry <entry_id> has status Confirmed/Inferred but carries no source_section or source_document reference; CLAUDE.md §10.5 requires every material claim to identify its source")
→ No output files are written

IF `status ∈ {Assumed, Unresolved}` AND (`source_section` is absent/empty OR `source_document` is absent/empty):
→ The entry MUST include `assumption_note` (if Assumed) OR `conflict_note` (if Unresolved)
→ If neither note field is present: CONSTRAINT_VIOLATION — return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="Entry <entry_id> has status Assumed/Unresolved with absent source fields but no explanatory note field")
→ If note field IS present: entry is a declared gap and is acceptable

**Failure output:** If a Confirmed or Inferred entry is found at write time with missing source references: SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Entry <entry_id> has status Confirmed/Inferred but carries no source_section or source_document reference; CLAUDE.md §10.5 requires every material claim to identify its source"). No output files are written.

**Hard failure confirmation:** Yes — for Confirmed/Inferred entries without source references; not a warning.

**CLAUDE.md §13 cross-reference:** §10.5 (not §13 directly) — "Agents must be able to identify, for each material claim in its output, the Tier 1–4 source from which the claim derives. Unattributed claims must be flagged, not asserted." Also §12.2 — Confirmed status requires naming the source artifact.

---

### Constraint 3: "Must apply Confirmed/Inferred/Assumed/Unresolved status"

**Decision point in execution logic:** Steps 2.3–2.8 — at the point each entry's `status` field is set.

**Exact failure condition:** Any entry in any output file has a `status` value other than exactly one of: "Confirmed", "Inferred", "Assumed", "Unresolved". Or: a `status` field is absent from any entry.

**Enforcement mechanism:** The status assignment rules in Steps 2.3–2.8 are exhaustive. The skill must verify at output construction time (Step 3) that every entry carries a status value from the permitted vocabulary. If any entry lacks a valid status: it must be assigned `status: "Unresolved"` with a flag_reason, not omitted. If the status field is missing entirely from an output entry: SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Entry <entry_id> is missing required status field; all entries must carry Confirmed/Inferred/Assumed/Unresolved status per CLAUDE.md §12.2").

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). No output files written.

**Hard failure confirmation:** Yes — missing or invalid status is a hard failure; the output is non-conformant.

**CLAUDE.md §13 cross-reference:** §12.2 — "Every phase output must apply the validation status vocabulary: Confirmed, Inferred, Assumed, Unresolved."

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier2b_topic_and_call_sources/work_programmes/` directory is empty or absent → `failure_reason="work_programmes/ directory is empty; cannot extract call requirements without source documents"`
- Step 1.3: Invoking agent has not provided the target topic identifier from `selected_call.json` → `failure_reason="selected_call topic identifier required to scope extraction"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill reads from source document directories (not structured schema-validated artifacts). No MALFORMED_ARTIFACT conditions are defined; input absence is handled by MISSING_INPUT.

**Artifact write behavior:** Not applicable for this skill.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
- Constraint 2 (source section references), Assumed/Unresolved entries: Any entry has `status ∈ {Assumed, Unresolved}` with absent source fields but no explanatory note field (`assumption_note` or `conflict_note`) → `failure_reason="Entry <entry_id> has status Assumed/Unresolved with absent source fields but no explanatory note field"`
- Constraint 3 (status vocabulary): Any entry is missing a valid `status` value from the permitted vocabulary → `failure_reason="Entry <entry_id> is missing required status field; all entries must carry Confirmed/Inferred/Assumed/Unresolved status per CLAUDE.md §12.2"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the failure.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Step 2.10: Any output file would contain zero extractable entries → `failure_reason="<filename> contains zero extractable entries; source document may not correspond to the target topic"`
- Step 5 (Write Sequence): Any of the six output files cannot be written → `failure_reason="<filename> could not be written"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 1 (no invented call requirements): Any extracted entry is assigned `status: "Confirmed"` or `status: "Inferred"` without a non-empty `source_section` and `source_document` traceable to actual source files; OR the skill cannot produce any confirmed entry without relying on prior knowledge → `failure_reason="No extractable entries can be sourced from the provided documents; inventing call requirements is a constitutional prohibition per CLAUDE.md §13.2"` or `failure_reason="Entry <entry_id> has status Confirmed/Inferred but carries no source_section or source_document reference; CLAUDE.md §10.5 requires every material claim to identify its source"`
- Constraint 2 (source section references), Confirmed/Inferred entries: Any Confirmed or Inferred entry at write time is missing source references → `failure_reason="Entry <entry_id> has status Confirmed/Inferred but carries no source_section or source_document reference"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the constitutional halt.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` is `docs/tier2b_topic_and_call_sources/extracted/` only; no exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Validation of Output Construction against `artifact_schema_specification.yaml` §7 (tier2b_extracted_schemas). Group C note: these Tier 2B extracted artifacts are `provenance_class: manually_placed`; they do not carry `schema_id`, `run_id`, or `artifact_status`. The skill additionally applies the CLAUDE.md §12.2 Confirmed/Inferred/Assumed/Unresolved vocabulary as an augmentation enabling gate status tracking.*

---

### Artifact 1: `call_constraints.json`

**Spec:** `tier2b_extracted_schemas.call_constraints` — root field `constraints`; item_schema requires `constraint_id`, `description`, `constraint_type` (enum: eligibility/scope/methodological/partnership/reporting/other), `source_section`, `source_document`.

**Gap identified:** Original Output Construction omitted the required `constraint_type` enum field.

**Correction applied:** Added `constraint_type` (enum per spec) to each entry in `constraints[]`.

### Artifact 2: `expected_outcomes.json`

**Spec:** `tier2b_extracted_schemas.expected_outcomes` — root field `outcomes`; item_schema requires `outcome_id`, `description`, `source_section`, `source_document`.

**Gap identified:** Original Output Construction used root field name `expected_outcomes` instead of spec's `outcomes`.

**Correction applied:** Root field renamed to `outcomes`.

### Artifact 3: `expected_impacts.json`

**Spec:** `tier2b_extracted_schemas.expected_impacts` — root field `impacts`; item_schema requires `impact_id`, `description`, `impact_type` (enum: scientific/societal/economic/policy/technological/environmental), `source_section`, `source_document`.

**Gaps identified:** (a) Root field name mismatch (`expected_impacts` vs `impacts`); (b) missing required `impact_type` enum field.

**Corrections applied:** Root field renamed to `impacts`; `impact_type` added per entry.

### Artifact 4: `scope_requirements.json`

**Spec:** `tier2b_extracted_schemas.scope_requirements` — root field `requirements`; item_schema requires `requirement_id`, `description`, `mandatory` (boolean), `source_section`, `source_document`.

**Gaps identified:** (a) Root field name mismatch (`scope_requirements` vs `requirements`); (b) id field mismatch (`scope_element_id` vs `requirement_id`); (c) skill used freeform `boundary_type` instead of required boolean `mandatory`.

**Corrections applied:** Root renamed to `requirements`; id renamed to `requirement_id`; `boundary_type` removed and replaced with required boolean `mandatory`.

### Artifact 5: `eligibility_conditions.json`

**Spec:** `tier2b_extracted_schemas.eligibility_conditions` — root field `conditions`; item_schema requires `condition_id`, `description`, `condition_type` (enum: consortium_composition/trl_level/budget_limit/geographic/open_access/other), `source_section`, `source_document`.

**Gaps identified:** (a) Root field name mismatch (`eligibility_conditions` vs `conditions`); (b) `condition_type` enum mismatch — skill originally listed `[consortium_composition, partner_type, country_restriction, ethics, other]` which is not the spec enum.

**Corrections applied:** Root renamed to `conditions`; `condition_type` enum restated to match spec `[consortium_composition, trl_level, budget_limit, geographic, open_access, other]`.

### Artifact 6: `evaluation_priority_weights.json`

**Spec:** `tier2b_extracted_schemas.evaluation_priority_weights` — root field `criteria`; item_schema requires `criterion_id`, `criterion_name`, `source_section`, `source_document`; optional `weight` (number), `priority_notes` (string).

**Gaps identified:** (a) Root field name mismatch (`evaluation_priority_weights` vs `criteria`); (b) missing required `criterion_name`; (c) field name `priority_note` (singular) vs spec's `priority_notes`.

**Corrections applied:** Root renamed to `criteria`; `criterion_name` added as required; `priority_note` renamed to `priority_notes`.

### Conformance summary

- **reads_from compliance:** Reads only from `docs/tier2b_topic_and_call_sources/work_programmes/` and `docs/tier2b_topic_and_call_sources/call_extracts/` — both declared in frontmatter. Compliant.
- **writes_to compliance:** Writes only to `docs/tier2b_topic_and_call_sources/extracted/` — declared in frontmatter. Compliant.
- **`schema_id` / `run_id` / `artifact_status`:** Spec treats these artifacts as `manually_placed` (no schema_id_value). Step 4 correctly states these fields do not apply and must not be added. Compliant.
- **Validation status vocabulary:** Skill correctly enforces Confirmed/Inferred/Assumed/Unresolved per CLAUDE.md §12.2 across all six files, via Constraint 3 (INCOMPLETE_OUTPUT). This augments the base spec (which is silent on status fields for Tier 2B) without conflicting with it.
- **`source_section` / `source_document` required on every item:** Spec marks both fields as required across all six common_item_fields. Skill enforces presence via Constraint 2 (CONSTITUTIONAL_HALT for Confirmed/Inferred without source refs). For Assumed/Unresolved entries, source fields may be absent provided an explanatory note is present — this is a declared gap pattern consistent with CLAUDE.md §12.2.

**Overall corrections applied:** 6 root-field renames, 2 required enum fields added (constraint_type, impact_type), 1 id field rename (scope_element_id→requirement_id), 1 field replacement (boundary_type→mandatory), 1 enum restated (condition_type), 1 field rename (priority_note→priority_notes), 1 required field added (criterion_name).

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
