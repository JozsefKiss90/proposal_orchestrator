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
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | section_schema_registry.json — Tier 2A extracted (updated in place) | N/A — Tier 2A extracted artifact (not a phase output canonical artifact; no schema_id or run_id required by artifact_schema_specification.yaml) | Per-instrument entry: instrument_type, sections array (section_id, section_name, mandatory boolean, page_limit, field_requirements); all values read from application form template | No — Tier 2A extracted artifact | Section identifiers, names, page limits, and mandatory flags derived from application form template documents; must not be authored from generic memory |

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
- Step 2.2: Parse the application form to extract all sections. For each section found: record `section_id` (the identifier as it appears in the form, e.g., "1.1", "Section B1", "Excellence"), `section_name` (full name), `mandatory` (boolean — true if the form marks this section as required, false if optional; if the form does not mark it explicitly, set to true and record as Assumed), `page_limit` (integer or null — read directly from the form; do not estimate or assume if not stated; set to null if absent), `field_requirements` (array of strings — each string describes a field or content requirement stated in the form for this section).
- Step 2.3: From the section data, extract two additional structural fields for the instrument entry: `max_wp_count` (integer or null — the maximum number of work packages allowed; read from the form's instructions; null if not specified), `project_duration_months` (integer or null — the standard project duration for this instrument; read from the form or call context provided by the invoking agent; null if not specified), `max_deliverable_count` (integer or null — any stated deliverable count limit).
- Step 2.4: Read existing `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`. If the file does not exist, initialise an empty registry object `{}`. If it exists, parse it to get existing instrument entries.
- Step 2.5: Build the updated instrument entry: `{ instrument_type: <resolved_instrument_type>, source_document: <application_form_filename>, extracted_at: <ISO8601 timestamp>, sections: [<array from Step 2.2>], max_wp_count: <from Step 2.3>, project_duration_months: <from Step 2.3>, max_deliverable_count: <from Step 2.3> }`.
- Step 2.6: Upsert the instrument entry into the registry: if `section_schema_registry.json` already contains an entry for `resolved_instrument_type`, replace it with the newly extracted entry. If not present, add it as a new entry. Do not modify entries for other instrument types.

### 3. Output Construction

**`section_schema_registry.json`** (updated in place):
- Top-level structure: object where keys are instrument_type values
- Key `<resolved_instrument_type>`: derived from Step 2.5 — `{instrument_type, source_document, extracted_at, sections[], max_wp_count, project_duration_months, max_deliverable_count}`
- Each section entry: `{section_id, section_name, mandatory (boolean), page_limit (integer or null), field_requirements (array of strings)}`
- All values derived from the application form template file identified in Step 2.1; no values assumed from generic memory

### 4. Conformance Stamping

This is a Tier 2A extracted artifact, not a phase output canonical artifact. No `schema_id`, `run_id`, or `artifact_status` field applies at the top level. Do not add these fields to the registry.

### 5. Write Sequence

- Step 5.1: Write the updated `section_schema_registry.json` to `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`, preserving all existing instrument entries except the one being upserted.

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
