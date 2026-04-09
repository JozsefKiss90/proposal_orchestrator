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

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier2a_instrument_schemas/evaluation_forms/` exists and is non-empty (dir_non_empty). If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="evaluation_forms/ directory is empty; cannot build evaluation matrix without an evaluation form template") and halt.
- Step 1.2: Presence check — confirm `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="evaluation_priority_weights.json not found; call-requirements-extraction must run before evaluation-matrix-builder") and halt.
- Step 1.3: Non-empty check — confirm `evaluation_priority_weights.json` is non-empty (has at least one entry in its root array). If empty: log as Unresolved (no call-specific weights available); continue with instrument default weights only; flag in call_analysis_notes.
- Step 1.4: Validate that the invoking agent context provides a `resolved_instrument_type` value (from `docs/tier3_project_instantiation/call_binding/selected_call.json`). If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="resolved_instrument_type required from selected_call.json") and halt.
- Step 1.5: Confirm at least one evaluation form file in `evaluation_forms/` corresponds to the `resolved_instrument_type`. If no matching form is found: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="No evaluation form found for instrument type <resolved_instrument_type>") and halt.

### 2. Core Processing Logic

- Step 2.1: Identify the evaluation form file(s) in `docs/tier2a_instrument_schemas/evaluation_forms/` that correspond to the `resolved_instrument_type`. If multiple files exist (e.g., different language versions), prefer the English version or the most recent dated version; record the choice in `call_analysis_notes`.
- Step 2.2: Parse the evaluation form to extract all evaluation criteria. For each criterion found: record `criterion_id` (the label as it appears in the form, e.g., "Excellence", "Impact", "Implementation"), `criterion_name` (full name), sub-criteria (list of strings describing what the evaluator assesses under this criterion), scoring thresholds (the numeric scale, e.g., 0-5 with descriptors), and grade descriptors (the text associated with each score value). Record the `source_section` (section number in the evaluation form) and `source_document` (filename of the evaluation form) for each criterion.
- Step 2.3: Parse `evaluation_priority_weights.json`. Build a lookup map keyed by `criterion_id`. For each entry in evaluation_priority_weights.json, locate the matching criterion_id in the evaluation matrix built in Step 2.2. If a matching criterion_id is found: overwrite the `weight` field with the value from evaluation_priority_weights.json; record `weight_source` as "tier2b_evaluation_priority_weights.json". If no matching criterion_id is found for a weights entry: log in `call_analysis_notes` that the weight entry could not be matched; do not discard the weight entry.
- Step 2.4: Build the `evaluation_matrix` object. Keys are `criterion_id` values. For each criterion: populate `criterion_id`, `criterion_name`, `weight` (from Step 2.3 if overlaid, otherwise from the evaluation form if explicitly stated, otherwise null), `source_section` (from the evaluation form), `source_document` (evaluation form filename). The evaluation_matrix must not be empty.
- Step 2.5: Build the `compliance_checklist` array. Source: the eligibility and compliance section of the evaluation form (if present). For each compliance requirement found in the evaluation form: assign `requirement_id` (unique, e.g., "CR-01"), `description`, `status` (one of: confirmed, requires_review, not_applicable), `source_section`, `source_document` (evaluation form filename). The compliance_checklist must not be empty; if no compliance requirements are found in the evaluation form, generate at least one entry from the instrument's known minimum consortium requirements with status: requires_review. Note: `eligibility_conditions.json` is not in this skill's `reads_from` and must not be read directly; if the invoking agent wishes to supplement the checklist with Tier 2B eligibility data, it must pass that data as context.
- Step 2.6: Set `resolved_instrument_type` from the invoking agent's context (the value read from selected_call.json). Do not infer it.
- Step 2.7: Set `call_analysis_notes` to a string summarising: (a) the evaluation form file used, (b) any weights overlay applied, (c) any unmatched weight entries, (d) any assumptions or inferences made during matrix construction.

### 3. Output Construction

**`call_analysis_summary.json`:**
- `schema_id`: set to "orch.phase1.call_analysis_summary.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `resolved_instrument_type`: derived from invoking agent context — `selected_call.json`.instrument_type field
- `evaluation_matrix`: derived from Step 2.4 — object keyed by criterion_id; each value is `{criterion_id, criterion_name, weight, source_section, source_document}`
- `compliance_checklist`: derived from Step 2.5 — array of `{requirement_id, description, status, source_section, source_document}`
- `call_analysis_notes`: derived from Step 2.7 — string summarising extraction decisions

### 4. Conformance Stamping

- `schema_id`: set to "orch.phase1.call_analysis_summary.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Write `call_analysis_summary.json` to `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json`
- If the target directory does not exist, create it before writing.

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
