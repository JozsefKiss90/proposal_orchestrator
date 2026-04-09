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

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
