---
skill_id: risk-register-builder
purpose_summary: >
  Populate the risk register from Tier 3 risk seeds, assigning likelihood, impact,
  mitigation, and monitoring for each risk, and flagging any material risks not in the
  seed file for Tier 3 update.
used_by_agents:
  - implementation_architect
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/risks.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
constitutional_constraints:
  - "Risks not in Tier 3 seeds must be flagged for operator review, not silently added"
  - "Mitigation measures must be traceable to project activities, not generic"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/architecture_inputs/risks.json` | risks.json — Tier 3 architecture input | Risk seed entries: risk_id, description, category, initial_likelihood, initial_impact, mitigation_seed, responsible_partner | N/A — Tier 3 source artifact | Authoritative source of project risks; the register must be populated from these seeds; any risk not in this file must be flagged for operator review rather than silently added |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json — canonical Phase 3 artifact | work_packages[].wp_id, tasks[], deliverables[] — to identify activities that mitigation measures can be traced to; partner_role_matrix for responsible_partner validation | `orch.phase3.wp_structure.v1` | Provides WP activities and deliverables as traceable anchors for mitigation measures; mitigation measures must reference a project activity or deliverable, not be generic |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | gantt.json — canonical Phase 4 artifact | milestones[].milestone_id, due_month — as monitoring trigger points for risk monitoring | `orch.phase4.gantt.v1` | Provides milestone due months as risk monitoring trigger points; risk monitoring schedule should align with project milestones |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | implementation_architecture.json (risk_register field) | `orch.phase6.implementation_architecture.v1` | schema_id, run_id (already set by governance-model-builder); risk_register (array: risk_id, description, category[technical/financial/organisational/ethical/external/other], likelihood[low/medium/high], impact[low/medium/high], mitigation[non-empty string], responsible_partner per entry) | Yes — same run_id as the full implementation_architecture.json | risk_register entries: risk_id, description, category from risks.json seeds; likelihood and impact refined from initial values; mitigation derived from mitigation_seed with specific reference to WP activities from wp_structure.json; monitoring_triggers derived from gantt.json milestone due months |

**Note:** `artifact_status` must be ABSENT at write time. This skill populates the risk_register field within the implementation_architecture.json file. If material risks are identified during analysis of wp_structure or gantt that are NOT in risks.json, they must be documented in a flag record (not added to the register) and surfaced to the operator via the decision log.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | Yes — artifact_id: a_t4_phase6 (directory); canonical file within that directory | n06_implementation_architecture |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
