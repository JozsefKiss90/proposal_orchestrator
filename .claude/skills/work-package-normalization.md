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

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` | workpackage_seed.json — Tier 3 architecture input | Seed WP entries: wp_id, title, objectives (array), lead_partner, tasks array (task_id, title, responsible_partner), deliverables array (deliverable_id, title, type, due_month), dependencies array | N/A — Tier 3 source artifact | Provides the initial WP structure to be normalized; all WP identifiers, leads, tasks, and deliverables must originate from this file or Tier 3 consortium data |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | section_schema_registry.json — Tier 2A extracted | Active instrument entry: max_wp_count, max_deliverable_count, mandatory_wp_types, project_duration_months | N/A — Tier 2A extracted artifact | Provides structural constraints for the active instrument (maximum WP count, deliverable constraints, mandatory WP types) that the normalized structure must comply with |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json | `orch.phase3.wp_structure.v1` | schema_id, run_id, work_packages (array: wp_id, title, objectives, lead_partner, contributing_partners, tasks[task_id, title, responsible_partner, contributing_partners], deliverables[deliverable_id, title, type, due_month, responsible_partner], dependencies[depends_on_wp_id, dependency_type, notes] per WP), dependency_map (object: nodes array, edges array[from, to, edge_type]), partner_role_matrix (array: partner_id, wps_as_lead, wps_as_contributor per partner) | Yes | work_packages derived from workpackage_seed.json normalized and validated against section_schema_registry.json constraints; dependency_map derived from dependencies arrays; partner_role_matrix derived from lead_partner and contributing_partners fields |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. WP leads must be validated against `docs/tier3_project_instantiation/consortium/partners.json` (read by the invoking agent, not directly listed in skill reads_from).

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | Yes — artifact_id: a_t4_phase3 (directory); canonical file within that directory | n03_wp_design |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
