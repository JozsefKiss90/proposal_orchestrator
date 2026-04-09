---
skill_id: governance-model-builder
purpose_summary: >
  Build the project governance model — management body composition, meeting frequency
  and decision scope, escalation paths, and quality assurance procedures — derived
  from Tier 3 consortium data and WP structure.
used_by_agents:
  - implementation_architect
reads_from:
  - docs/tier3_project_instantiation/consortium/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
constitutional_constraints:
  - "Governance roles must be assigned to Tier 3 consortium members only"
  - "Management structure must be consistent with WP lead assignments"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/consortium/` | Consortium directory: partners.json, roles.json (and any supporting files) | partners.json: partner_id list, partner_name, partner_type, country; roles.json: role assignments per partner, management responsibilities | N/A — Tier 3 source directory | Provides the complete list of consortium partners and their roles; governance body composition must draw exclusively from partner_id values in this directory |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].wp_id; work_packages[].lead_partner (must be consistent with governance role assignments); partner_role_matrix[].partner_id, wps_as_lead | `orch.phase3.wp_structure.v1` | Provides WP lead assignments that must be reflected in governance roles; management structure must be consistent with WP leads declared here |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | implementation_architecture.json | `orch.phase6.implementation_architecture.v1` | schema_id, run_id, governance_matrix (array: body_name, composition[partner_id list], decision_scope, meeting_frequency, escalation_path per body), management_roles (array: role_id, role_name, assigned_to[partner_id], responsibilities per role), risk_register (array — populated by risk-register-builder skill), ethics_assessment (object — populated separately), instrument_sections_addressed (array — populated separately) | Yes | governance_matrix: body composition derived from consortium/partners.json partner_ids; management_roles: assigned_to values derived from consortium/roles.json; meeting_frequency and escalation_path may be inferred but must be flagged if no Tier 3 source |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. This skill populates the governance_matrix and management_roles fields; risk_register, ethics_assessment, and instrument_sections_addressed are populated by other skills (risk-register-builder, implementation_architect). The full implementation_architecture.json must be complete before the Phase 6 gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | Yes — artifact_id: a_t4_phase6 (directory); canonical file within that directory | n06_implementation_architecture |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
