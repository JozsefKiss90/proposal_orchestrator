---
skill_id: instrument-schema-normalization
purpose_summary: >
  Resolve the active instrument type to its application form section schema, extracting
  section identifiers, field requirements, page limits, mandatory elements, and
  structural constraints.
used_by_agents:
  - instrument_schema_resolver
  - proposal_writer
reads_from:
  - docs/tier2a_instrument_schemas/application_forms/
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
writes_to:
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
constitutional_constraints:
  - "Must resolve from the actual Tier 2A application form, not from generic memory"
  - "Must never substitute a Grant Agreement Annex as a section schema source"
  - "Page limits and section constraints must be read from the template, not assumed"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier2a_instrument_schemas/application_forms/` | Application form templates for the active instrument type (PDF/DOCX) | Section identifiers; section names; field requirements; page limits; mandatory elements; structural constraints; instrument type label | N/A — source document directory (dir_non_empty check only) | Primary structural source for the active instrument's application form; defines what sections exist, their page limits, and what must be addressed |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | section_schema_registry.json — Tier 2A extracted (read before update) | Existing instrument entries; section_id list; mandatory flags; page limits; field constraints | N/A — Tier 2A extracted artifact | Read to determine whether the registry already contains an entry for the resolved instrument type; provides baseline for update/population |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | section_schema_registry.json — Tier 2A extracted (updated in place) | N/A — Tier 2A extracted artifact (not a phase output canonical artifact; no schema_id or run_id required by artifact_schema_specification.yaml) | Per-instrument entry: instrument_type, sections array (section_id, section_name, mandatory boolean, page_limit, field_requirements, source_document); all values read from application form template. Each section entry: {section_id, section_name, mandatory (boolean), page_limit (integer or null), field_requirements (array of strings), source_document (string — filename of the application form template from which this section was extracted)} | No — Tier 2A extracted artifact | Section identifiers, names, page limits, mandatory flags, and source_document derived from application form template documents; must not be authored from generic memory |

**Note:** This skill updates a Tier 2A extracted artifact rather than writing a phase output. No `artifact_status` sentinel applies. The updated registry must be traceable to the specific application form template file read.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | Yes — artifact_id: a_t2a_section_schema_registry | n01_call_analysis |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier2a_instrument_schemas/application_forms/` exists and is non-empty (dir_non_empty). If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="application_forms/ directory is empty; cannot normalize instrument schema without an application form template") and halt.
- Step 1.2: Confirm that the invoking agent context provides a `resolved_instrument_type` value. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="resolved_instrument_type required to identify the correct application form") and halt.
- Step 1.3: Confirm at least one application form file in `application_forms/` corresponds to the `resolved_instrument_type`. If no matching form is found: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="No application form found for instrument type <resolved_instrument_type>") and halt.
- Step 1.4: **Grant Agreement Annex guard** — inspect the identified application form file. If the document's title or header contains any of the following markers: "Annex", "Grant Agreement", "Model Grant Agreement", "AGA", "Annotated Grant Agreement": return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Document appears to be a Grant Agreement Annex, not an application form template. CLAUDE.md §13.1 and §5 (Tier 2A) prohibit using Grant Agreement Annex templates as proposal schema sources") and halt. This check is mandatory and cannot be bypassed.
- Step 1.5: Presence check — confirm `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` exists. If absent: it will be created fresh in Step 5. Log this as a note; do not halt.

### 2. Core Processing Logic

- Step 2.1: Identify the application form file in `docs/tier2a_instrument_schemas/application_forms/` that corresponds to the `resolved_instrument_type`. If multiple files match, prefer the most recent dated version; record the choice.
- Step 2.2: Parse the application form to extract all sections. For each section found: record `section_id` (the identifier as it appears in the form, e.g., "1.1", "Section B1", "Excellence"), `section_name` (full name), `mandatory` (boolean — true if the form marks this section as required, false if optional; if the form does not mark it explicitly, set to true and record as Assumed), `page_limit` (integer or null — read directly from the form; do not estimate or assume if not stated; set to null if absent), `field_requirements` (array of strings — each string describes a field or content requirement stated in the form for this section), `source_document` (string — set to the filename of the application form file identified in Step 2.1; this field is required for every section entry).
- Step 2.3: From the section data, extract two additional structural fields for the instrument entry: `max_wp_count` (integer or null — the maximum number of work packages allowed; read from the form's instructions; null if not specified), `project_duration_months` (integer or null — the standard project duration for this instrument; read from the form or call context provided by the invoking agent; null if not specified), `max_deliverable_count` (integer or null — any stated deliverable count limit).
- Step 2.4: Read existing `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`. If the file does not exist, initialise an empty registry object `{}`. If it exists, parse it to get existing instrument entries.
- Step 2.5: Build the updated instrument entry: `{ instrument_type: <resolved_instrument_type>, source_document: <application_form_filename>, extracted_at: <ISO8601 timestamp>, sections: [<array from Step 2.2>], max_wp_count: <from Step 2.3>, project_duration_months: <from Step 2.3>, max_deliverable_count: <from Step 2.3> }`.
- Step 2.6: Upsert the instrument entry into the registry: if `section_schema_registry.json` already contains an entry for `resolved_instrument_type`, replace it with the newly extracted entry. If not present, add it as a new entry. Do not modify entries for other instrument types.

### 3. Output Construction

**`section_schema_registry.json`** (updated in place):
- Top-level structure: object with required `instruments` array (matches `tier2a_extracted_schemas.section_schema_registry` spec)
- Each item in `instruments[]`: `{instrument_type (string, required), sections (array, required), max_work_packages (integer, optional — spec field name), evaluation_form_ref (string, required — filename of the evaluation form template in tier2a_instrument_schemas/evaluation_forms/ for this instrument)}`
- Each section entry in `sections[]`: `{section_id (string, required), section_name (string, required), mandatory (boolean, required), section_type (string, required, enum: [proposal_section, implementation_section, cover_page, annexe]), page_limit (integer, optional — omit or null when absent from form), word_limit (integer, optional)}`
- Auxiliary (non-spec) fields retained for traceability only, and only when traceable to the form: `source_document` (filename of application form), `field_requirements` (array of strings), `extracted_at` (ISO 8601), `project_duration_months`, `max_deliverable_count`. These auxiliary fields must not conflict with the spec's required fields and must not be substituted for them.
- All values derived from the application form template file identified in Step 2.1; no values assumed from generic memory
- Upsert semantics (Step 2.6): when updating the registry, locate the existing `instruments[]` entry by `instrument_type` and replace it; if none exists, append the new entry; entries for other instrument types remain unchanged

### 4. Conformance Stamping

This is a Tier 2A extracted artifact, not a phase output canonical artifact. No `schema_id`, `run_id`, or `artifact_status` field applies at the top level. Do not add these fields to the registry.

### 5. Write Sequence

- Step 5.1: Write the updated `section_schema_registry.json` to `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`, preserving all existing instrument entries except the one being upserted.

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Must resolve from the actual Tier 2A application form, not from generic memory"

**Decision point in execution logic:** Step 1.3 and Step 2.2 — at the point the application form file is identified (Step 1.3) and at the point section data is parsed from it (Step 2.2).

**Exact failure condition:** (a) No application form file in `application_forms/` matches the resolved_instrument_type (caught at Step 1.3); OR (b) the section entries in `section_schema_registry.json` are constructed from agent prior knowledge rather than from parsing the identified form file — detectable when `source_document` is absent or does not match a file present in `application_forms/`.

**Enforcement mechanism:** Every section entry produced in Step 2.2 MUST carry a `source_document` value that matches the filename of the application form file identified in Step 2.1. At output construction time (Step 3), before writing any section entry, verify:

IF `source_document` is absent or empty for any section entry:
→ CONSTITUTIONAL_HALT immediately
→ return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Section entry has no source_document reference; instrument schema normalization must derive all sections from the actual Tier 2A application form, not from prior knowledge. CLAUDE.md §10.6 and §13.9 prohibit substituting agent knowledge for source documents.")
→ `section_schema_registry.json` not updated

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). `section_schema_registry.json` not updated.

**Hard failure confirmation:** Yes — immediate halt; no registry update without source-traceable section entries.

**CLAUDE.md §13 cross-reference:** §13.9 — "Using agent-local knowledge of Horizon Europe programme rules as a substitute for reading Tier 1 source documents when those documents are present and accessible." Also §10.6.

---

### Constraint 2: "Must never substitute a Grant Agreement Annex as a section schema source"

**Decision point in execution logic:** Step 1.4 — the Grant Agreement Annex guard is applied at input validation, before any processing begins.

**Exact failure condition:** The document file identified as the application form for `resolved_instrument_type` in `application_forms/` has a title, header, or filename containing any of the following strings (case-insensitive): "Annex", "Grant Agreement", "Model Grant Agreement", "AGA", "Annotated Grant Agreement".

**Enforcement mechanism:** Step 1.4 is an unconditional check that fires before Step 2 begins. If the guard condition triggers: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Document '<filename>' appears to be a Grant Agreement Annex, not an application form template. CLAUDE.md §13.1 and §5 (Tier 2A) prohibit using Grant Agreement Annex templates as proposal schema sources. The instrument schema must be read from the application form template.") and halt. This guard cannot be bypassed, disabled, or conditioned on any other factor.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). Immediate halt before any extraction. `section_schema_registry.json` not modified.

**Hard failure confirmation:** Yes — unconditional halt; this is a categorical prohibition with no exceptions.

**CLAUDE.md §13 cross-reference:** §13.1 — "Treating Grant Agreement Annex templates as the governing structural schema for proposal writing. Annex templates govern post-award implementation reporting. Application form templates (Tier 2A) govern proposal writing."

---

### Constraint 3: "Page limits and section constraints must be read from the template, not assumed"

**Decision point in execution logic:** Step 2.2 and Step 2.3 — at the point `page_limit`, `mandatory`, and `max_wp_count` / `max_deliverable_count` values are set for each section and instrument entry.

**Exact failure condition:** Any `page_limit` value is set to a non-null integer without form text evidence. OR: `mandatory` is set to `true` with no form evidence and no `assumption_note` recorded. OR: `max_wp_count` or `max_deliverable_count` is set to a non-null integer with no form text evidence.

**Enforcement mechanism — three-field enforcement (source_document, page_limit, mandatory):**

IF any section entry has `source_document` absent or empty:
→ CONSTITUTIONAL_HALT immediately
→ Reason: `source_document` is required for every section entry to make the extraction traceable

IF `page_limit` is non-null AND was NOT read from the form text:
→ `page_limit` MUST be set to null instead; do NOT estimate
→ IF a non-null `page_limit` was written without form evidence: CONSTITUTIONAL_HALT
→ return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="page_limit for section <section_id> was assigned a non-null value not traceable to the application form template; must be null when absent from form")

IF `mandatory` is set to true AND no explicit form marking exists:
→ `mandatory` MUST be recorded as Assumed with `assumption_note` present
→ IF `mandatory: true` is written without form evidence AND without `assumption_note`: CONSTRAINT_VIOLATION
→ return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="mandatory: true for section <section_id> was written without form evidence and without assumption_note")

IF `max_wp_count` or `max_deliverable_count` is non-null AND was NOT read from the form:
→ Set to null; do NOT estimate
→ IF non-null value written without form evidence: CONSTITUTIONAL_HALT
→ return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="<field_name> was assigned a non-null value not traceable to the application form template; must be null when absent from form")

No output written when any CONSTITUTIONAL_HALT or CONSTRAINT_VIOLATION is triggered.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT") for source_document, page_limit, or max_wp_count/max_deliverable_count violations. SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION") for mandatory without assumption_note. `section_schema_registry.json` not updated in either case.

**Hard failure confirmation:** Yes — structural constraint values fabricated from prior knowledge trigger an immediate halt.

**CLAUDE.md §13 cross-reference:** §10.6 — "Agents must not substitute their prior knowledge of Horizon Europe requirements for the contents of Tier 1 and Tier 2 source documents. When source documents are present, they govern."

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier2a_instrument_schemas/application_forms/` directory is empty → `failure_reason="application_forms/ directory is empty; cannot normalize instrument schema without an application form template"`
- Step 1.2: Invoking agent context does not provide `resolved_instrument_type` → `failure_reason="resolved_instrument_type required to identify the correct application form"`
- Step 1.3: No application form file in `application_forms/` matches the `resolved_instrument_type` → `failure_reason="No application form found for instrument type <resolved_instrument_type>"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill reads from source document directories (application form files, not structured schema-validated artifacts). No MALFORMED_ARTIFACT conditions are defined; input absence is handled by MISSING_INPUT.

**Artifact write behavior:** Not applicable for this skill.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
- Constraint 3 (page limits and section constraints from template): Any section entry has `mandatory: true` written without form evidence AND without `assumption_note` → `failure_reason="mandatory: true for section <section_id> was written without form evidence and without assumption_note"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. `section_schema_registry.json` not updated. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the failure.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
No INCOMPLETE_OUTPUT conditions are explicitly defined. If a write error occurs at Step 5.1, the skill should return `failure_reason="section_schema_registry.json could not be written"`.

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Step 1.4 (Grant Agreement Annex guard): The identified application form file's title or header contains "Annex", "Grant Agreement", "Model Grant Agreement", "AGA", or "Annotated Grant Agreement" → `failure_reason="Document '<filename>' appears to be a Grant Agreement Annex, not an application form template. CLAUDE.md §13.1 and §5 (Tier 2A) prohibit using Grant Agreement Annex templates as proposal schema sources"`
- Constraint 1 (resolve from actual Tier 2A form): Any section entry at output construction time has `source_document` absent or empty → `failure_reason="Section entry has no source_document reference; instrument schema normalization must derive all sections from the actual Tier 2A application form, not from prior knowledge. CLAUDE.md §10.6 and §13.9 prohibit substituting agent knowledge for source documents."`
- Constraint 3 (page limits from template): Any `page_limit` is non-null without form text evidence; or `max_wp_count`/`max_deliverable_count` is non-null without form evidence → `failure_reason="<field_name> was assigned a non-null value not traceable to the application form template; must be null when absent from form"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. `section_schema_registry.json` not updated. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the constitutional halt.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` is `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` only; no exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Validation of Output Construction against `artifact_schema_specification.yaml` §8 (tier2a_extracted_schemas). This is a Tier 2A extracted artifact (`provenance_class: manually_placed`); no `schema_id`, `run_id`, or `artifact_status` applies.*

---

### Artifact: `section_schema_registry.json`

**Spec location:** `tier2a_extracted_schemas.section_schema_registry`

**Required top-level field:** `instruments` (array)

**Required per-instrument item fields:** `instrument_type` (string), `sections` (array), `evaluation_form_ref` (string — filename of evaluation form template)

**Optional per-instrument fields:** `max_work_packages` (integer)

**Required per-section item_schema fields:** `section_id` (string), `section_name` (string), `mandatory` (boolean), `section_type` (string, enum: [proposal_section, implementation_section, cover_page, annexe])

**Optional per-section fields:** `page_limit` (integer), `word_limit` (integer)

**Gaps identified in original Output Construction:**
1. Top-level structure was described as "object where keys are instrument_type values" — spec requires root `instruments` array.
2. Field name `max_wp_count` does not match spec's `max_work_packages`.
3. Missing required `evaluation_form_ref` per instrument entry.
4. Missing required `section_type` enum field per section entry.

**Corrections applied:** Root structure restated as `instruments[]` array; `max_wp_count` renamed to `max_work_packages`; `evaluation_form_ref` added as required; `section_type` enum field added as required per section; upsert semantics clarified to operate over the `instruments[]` array by `instrument_type` join key.

**Auxiliary fields (non-spec, retained):** `source_document`, `field_requirements`, `extracted_at`, `project_duration_months`, `max_deliverable_count` are not defined in the spec but are preserved at the instrument/section level as traceability metadata, consistent with the skill's constitutional enforcement that every section must be sourced to the application form file. These fields do not override or conflict with spec-required fields.

**reads_from compliance:** Reads from `docs/tier2a_instrument_schemas/application_forms/` and `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`. Both declared in frontmatter. Compliant.

**writes_to compliance:** Writes only to `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`. Declared in frontmatter. Compliant.

**Conformance note (`section_type` enforcement):** When parsing the application form, each section must be classified into one of the four enum values. This is a new enforcement obligation created by the spec; the skill's Step 2.2 must assign `section_type` per section from form evidence (proposal body sections → `proposal_section`; management/implementation annex sections → `implementation_section`; title/cover page → `cover_page`; annexes → `annexe`). If classification is not derivable from the form, the section entry must flag the classification as Assumed with an `assumption_note`, consistent with the skill's Constraint 3 pattern for `mandatory` without form evidence.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
