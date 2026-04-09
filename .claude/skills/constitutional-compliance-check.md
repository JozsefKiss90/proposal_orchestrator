---
skill_id: constitutional-compliance-check
purpose_summary: >
  Verify that a phase output or deliverable does not violate any prohibition in
  CLAUDE.md, checking for fabricated project facts, fabricated call constraints,
  budget-dependent content before the budget gate, grant annex schema usage, and
  other constitutional violations.
used_by_agents:
  - compliance_validator
  - call_analyzer
  - concept_refiner
  - proposal_writer
  - revision_integrator
  - budget_gate_validator
reads_from:
  - CLAUDE.md
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier5_deliverables/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Must check against CLAUDE.md Section 13 prohibitions as a minimum"
  - "Constitutional violations must be flagged; they must not be silently resolved"
  - "CLAUDE.md governs this skill; this skill does not govern CLAUDE.md"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `CLAUDE.md` | Repository constitution | Section 13 prohibitions (13.1–13.12); Section 7 gate conditions; Section 8 budget integration rules; Section 11 deliverable rules | N/A — constitutional document | The binding authority that defines all prohibited actions; every violation check is mapped to a named section in this document |
| `docs/tier4_orchestration_state/phase_outputs/` | Phase output directory — canonical artifacts from phases 1–8 | Phase-specific canonical artifact fields (varies by phase: call_analysis_summary, concept_refinement_summary, wp_structure, gantt, impact_architecture, implementation_architecture, budget_gate_assessment, drafting_review_status) | Context-dependent: the schema_id of the artifact being checked | Phase outputs being audited for constitutional violations; checked for fabricated facts, schema mismatches, gate bypasses, and other Section 13 violations |
| `docs/tier5_deliverables/` | Deliverable directory — proposal_sections/, assembled_drafts/, review_packets/, final_exports/ | content fields; traceability_footer; validation_status; section_completion_log | Context-dependent: orch.tier5.proposal_section.v1, orch.tier5.assembled_draft.v1, orch.tier5.review_packet.v1, orch.tier5.final_export.v1 | Deliverables being audited for constitutional violations; checked for budget-dependent content before gate pass, unsupported Tier 5 claims, and grant annex schema usage |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/validation_reports/` | Per-invocation constitutional compliance report file (e.g., `compliance_check_<artifact>_<timestamp>.json`) | N/A — validation report | report_id; skill_id: "constitutional-compliance-check"; invoking_agent; run_id_reference; artifact_audited (path); section13_checks (array: prohibition_id[e.g., "13.1"], prohibition_description, check_status[pass/violation], violation_evidence, severity[critical/major]); summary (total_prohibitions_checked, violations_found); timestamp | No — validation reports are not phase output canonical artifacts | section13_checks: each prohibition in CLAUDE.md §13 applied to the artifact being audited; violation_evidence quotes specific content from the audited artifact; critical violations must block downstream use |
| `docs/tier4_orchestration_state/decision_log/` | Constitutional violation decision log entry (when a violation is found and a resolution decision is made) | N/A — decision log entry | decision_id; decision_type: "constitutional_violation"; violation_id; constitutional_rule_ref (e.g., "CLAUDE.md §13.3"); artifact_affected; resolution_status; resolution_note; tier_authority_applied; timestamp | No | Entries written when a constitutional violation requires an explicit resolution decision; the resolution must identify the tier authority applied and why |

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/validation_reports/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent per invoking agent) |
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent per invoking agent) |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
