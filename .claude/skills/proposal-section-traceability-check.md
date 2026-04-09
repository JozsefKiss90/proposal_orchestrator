---
skill_id: proposal-section-traceability-check
purpose_summary: >
  Verify that every material claim in a proposal section is traceable to a named
  Tier 1–4 source, flagging unattributed assertions and applying
  Confirmed/Inferred/Assumed/Unresolved status to each claim.
used_by_agents:
  - proposal_writer
  - revision_integrator
  - traceability_auditor
reads_from:
  - docs/tier5_deliverables/proposal_sections/
  - docs/tier5_deliverables/assembled_drafts/
  - docs/tier1_normative_framework/extracted/
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier2b_topic_and_call_sources/extracted/
  - docs/tier3_project_instantiation/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
constitutional_constraints:
  - "Unattributed claims must be flagged, not silently accepted as Confirmed"
  - "Confirmed status requires naming the specific source artifact"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier5_deliverables/proposal_sections/` | Individual proposal section JSON files (<section_id>.json) | content (full section text); validation_status.claim_statuses[]; traceability_footer.primary_sources[] | `orch.tier5.proposal_section.v1` (per section file) | The proposal sections under audit; material claims are extracted from content and their stated source references in traceability_footer are verified against Tier 1–4 artifacts |
| `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` | assembled_draft.json — canonical Tier 5 artifact | sections[].section_id, artifact_path; consistency_log[] | `orch.tier5.assembled_draft.v1` | Provides the assembly index and consistency log; used when performing cross-section traceability audit on the assembled draft |
| `docs/tier1_normative_framework/extracted/` | Tier 1 extracted rule and compliance files | Rule entries with source references; compliance requirements; legal constraints | N/A — Tier 1 extracted directory | Reference set for verifying claims attributed to Tier 1 (legislation, programme guidance, grant architecture); Confirmed status requires naming a specific file from this directory |
| `docs/tier2a_instrument_schemas/extracted/` | Tier 2A extracted files (section_schema_registry.json, evaluator_expectation_registry.json) | Section schema entries; evaluation criteria entries | N/A — Tier 2A extracted directory | Reference set for claims attributed to instrument schema or evaluation criteria; Confirmed status requires naming a specific Tier 2A extracted file |
| `docs/tier2b_topic_and_call_sources/extracted/` | Tier 2B extracted files (call_constraints, expected_outcomes, expected_impacts, scope_requirements, eligibility_conditions, evaluation_priority_weights) | All extracted call requirement entries | N/A — Tier 2B extracted directory | Reference set for claims attributed to call or topic requirements; Confirmed status requires naming a specific Tier 2B extracted file and entry |
| `docs/tier3_project_instantiation/` | Tier 3 project data (all subdirectories: project_brief/, consortium/, call_binding/, architecture_inputs/) | Project facts: partner names, capabilities, objectives, outcomes, impacts, WP seeds, risks | N/A — Tier 3 root directory (semantic scope root) | Reference set for project-specific claims; every partner name, capability, objective, or project fact in the proposal must be traceable to a specific Tier 3 file |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/validation_reports/` | Per-invocation traceability report file (e.g., `traceability_<section_id>_<timestamp>.json`) | N/A — validation report | report_id; skill_id: "proposal-section-traceability-check"; invoking_agent; run_id_reference; section_id_audited; claim_audit_results (array: claim_id, claim_summary, status[confirmed/inferred/assumed/unresolved], source_ref, flag_reason); summary (total_claims, confirmed, inferred, assumed, unresolved); no_unsupported_claims_declaration boolean; timestamp | No — validation reports are not phase output canonical artifacts | claim_audit_results: each claim extracted from section content; status assigned based on whether source_ref in traceability_footer points to an actual entry in Tier 1–4 artifacts; unattributed claims receive status: unresolved and flag_reason: "no source reference provided" |

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/validation_reports/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent: n08a_section_drafting, n08b_assembly, or n08d_revision per invoking agent) |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
