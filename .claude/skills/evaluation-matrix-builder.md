---
skill_id: evaluation-matrix-builder
purpose_summary: >
  Build a structured evaluation matrix from the applicable evaluation form and call
  priority weights, mapping evaluation criteria, sub-criteria, scoring thresholds,
  and relative weights.
used_by_agents:
  - call_analyzer
  - instrument_schema_resolver
reads_from:
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
constitutional_constraints:
  - "Evaluation criteria must reflect the active evaluation form, not a generic template"
  - "Sub-criterion weights must be traceable to Tier 2B extracted files"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier2a_instrument_schemas/evaluation_forms/` | Evaluation form templates for the active instrument type (PDF/DOCX) | Criterion identifiers; criterion names; sub-criteria; scoring thresholds; weighting tables; overall scoring logic | N/A — source document directory (dir_non_empty check only) | Primary structural source defining the evaluation criteria and scoring logic that evaluators will apply; governs what the matrix must contain |
| `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | evaluation_priority_weights.json — Tier 2B extracted | criterion-level weight entries; source_section; source_document | N/A — Tier 2B extracted artifact | Provides call-specific evaluation priority weights to overlay on top of the instrument evaluation form criteria |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | call_analysis_summary.json | `orch.phase1.call_analysis_summary.v1` | schema_id, run_id, resolved_instrument_type, evaluation_matrix (object: structured mapping of criteria; each entry contains criterion_id, criterion_name, weight, source_section, source_document), compliance_checklist (array: requirement_id, description, status, source_section, source_document per entry) | Yes | evaluation_matrix entries derived from evaluation form templates; weights overlaid from evaluation_priority_weights.json; resolved_instrument_type from selected_call.json via call_analyzer context |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | Yes — artifact_id: a_t4_phase1 (directory); canonical file within that directory | n01_call_analysis |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
