---
skill_id: evaluator-criteria-review
purpose_summary: >
  Assess proposal content against the scoring logic of the applicable evaluation
  criterion, identifying weaknesses by severity and producing structured feedback
  aligned to evaluator sub-criteria.
used_by_agents:
  - evaluator_reviewer
  - revision_integrator
reads_from:
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
  - docs/tier5_deliverables/assembled_drafts/
writes_to:
  - docs/tier5_deliverables/review_packets/
constitutional_constraints:
  - "Evaluation must apply the active instrument evaluation criteria only"
  - "Must not evaluate against grant agreement annex requirements"
  - "Weakness severity (critical/major/minor) must be assigned to each finding"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier2a_instrument_schemas/evaluation_forms/` | Evaluation form templates for the active instrument (PDF/DOCX) | Criterion identifiers; criterion names; sub-criteria descriptions; scoring thresholds; scoring logic; grade descriptors | N/A — source document directory (dir_non_empty check only) | The binding structural authority for evaluation; assessment must apply the active instrument evaluation form criteria, not generic criteria or grant agreement annex requirements |
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | call_analysis_summary.json — canonical Phase 1 artifact | evaluation_matrix (object: structured mapping of evaluation criteria; each entry contains criterion_id, criterion_name, weight, source_section, source_document) | `orch.phase1.call_analysis_summary.v1` | Provides the extracted evaluation matrix with source references; evaluation findings are mapped to criterion_id values from this matrix to ensure the review covers all active criteria |
| `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` | assembled_draft.json — canonical Tier 5 artifact | sections[].section_id, artifact_path; consistency_log[] | `orch.tier5.assembled_draft.v1` | The assembled draft being reviewed; sections referenced in this artifact are evaluated against each evaluation criterion |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier5_deliverables/review_packets/review_packet.json` | review_packet.json | `orch.tier5.review_packet.v1` | schema_id, run_id, findings (array: finding_id, section_id, criterion[from evaluation form], description, severity[critical/major/minor], evidence, recommendation per finding), revision_actions (array: action_id, finding_id, priority, action_description, target_section, severity[critical/major/minor] per action) | Yes | findings: each finding mapped to a criterion_id from call_analysis_summary.json evaluation_matrix; criterion value drawn directly from the evaluation form (not from generic memory); evidence quoted from assembled_draft.json sections; severity assigned per finding; revision_actions: prioritised list derived from findings, with priority ordering by severity |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. Evaluation must not apply grant agreement annex requirements as criteria.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier5_deliverables/review_packets/review_packet.json` | Yes — artifact_id: a_t5_review_packets (directory); canonical file within that directory | n08c_evaluator_review |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
