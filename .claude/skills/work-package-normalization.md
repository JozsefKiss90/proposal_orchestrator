---
skill_id: work-package-normalization
purpose_summary: >
  Normalize a work package structure to ensure each WP has all required elements:
  unique identifier, title, objective, tasks with identifiers, deliverables with due
  months and types, milestones with verifiable criteria, and a responsible lead.
used_by_agents:
  - wp_designer
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
constitutional_constraints:
  - "WP leads must be drawn from Tier 3 consortium data only"
  - "WP count must not exceed instrument limits from Tier 2A"
  - "Deliverables must have due months within project duration"
---

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
