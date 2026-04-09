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

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
