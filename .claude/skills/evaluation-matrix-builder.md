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

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Evaluation criteria must reflect the active evaluation form, not a generic template"

**Decision point in execution logic:** Step 1.5 and Step 2.2 — at the point the evaluation form file is identified and parsed. The form file must be the actual Tier 2A evaluation form for the resolved_instrument_type, not a generic criteria list or prior-knowledge template.

**Exact failure condition:** (a) No evaluation form file in `evaluation_forms/` matches the `resolved_instrument_type` (caught at Step 1.5); OR (b) the evaluation form identified in Step 2.1 does not correspond to the active instrument type — e.g., the form is for a different instrument type or is a generic criteria document (caught at Step 2.2 when parsing fails to find instrument-specific section identifiers); OR (c) the evaluation_matrix is constructed from agent prior knowledge of evaluation criteria rather than from the parsed form content.

**Enforcement mechanism:** Step 2.2 must parse criteria exclusively from the file identified in Step 2.1. If the skill cannot parse at least one evaluation criterion with `source_section` and `source_document` populated from the file: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Evaluation criteria cannot be sourced from the provided form file for instrument type <resolved_instrument_type>; constructing criteria from generic knowledge is prohibited by CLAUDE.md §13.9 and §10.6"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No `call_analysis_summary.json` written.

**Hard failure confirmation:** Yes — immediate halt; generic criteria may not substitute for source-read criteria.

**CLAUDE.md §13 cross-reference:** §13.9 — "Using agent-local knowledge of Horizon Europe programme rules as a substitute for reading Tier 1 source documents when those documents are present and accessible." Also §10.6 — agents must not substitute prior knowledge for source documents.

---

### Constraint 2: "Sub-criterion weights must be traceable to Tier 2B extracted files"

**Decision point in execution logic:** Step 2.3 and Step 2.4 — at the point weights are assigned to each criterion entry in the evaluation_matrix.

**Exact failure condition:** Any criterion entry in the `evaluation_matrix` has a non-null `weight` value that was NOT sourced from `evaluation_priority_weights.json` and has no `weight_source` field referencing that file. Equivalently: a weight is invented by the skill from prior knowledge rather than read from the Tier 2B extracted file.

**Enforcement mechanism:** In Step 2.3, every weight value applied to an entry must be traced to a specific entry in `evaluation_priority_weights.json`. The `weight_source` field must be set to "tier2b_evaluation_priority_weights.json" for any weight that was overlaid from Tier 2B. If no Tier 2B weight exists for a criterion, the criterion's `weight` must be set to null (not assigned a value from prior knowledge) and `weight_source` must be absent or null. Assigning a non-null weight without a Tier 2B source reference is a constitutional violation.

**Failure output:** SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="Criterion <criterion_id> has weight <value> with no traceable Tier 2B source; weights must originate from evaluation_priority_weights.json per skill constitutional constraints"). No `call_analysis_summary.json` written.

**Hard failure confirmation:** Yes — no output produced when this violation is detected.

**CLAUDE.md §13 cross-reference:** §10.5 — "Agents must be able to identify, for each material claim in its output, the Tier 1–4 source from which the claim derives." Weight values are material claims about call evaluation structure; they must be sourced from Tier 2B.

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier2a_instrument_schemas/evaluation_forms/` directory is empty → `failure_reason="evaluation_forms/ directory is empty; cannot build evaluation matrix without an evaluation form template"`
- Step 1.2: `evaluation_priority_weights.json` does not exist → `failure_reason="evaluation_priority_weights.json not found; call-requirements-extraction must run before evaluation-matrix-builder"`
- Step 1.4: Invoking agent context does not provide `resolved_instrument_type` → `failure_reason="resolved_instrument_type required from selected_call.json"`
- Step 1.5: No evaluation form file in `evaluation_forms/` matches the `resolved_instrument_type` → `failure_reason="No evaluation form found for instrument type <resolved_instrument_type>"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill reads from source document directories and a Tier 2B extracted artifact (not a structured canonical artifact with schema_id). No MALFORMED_ARTIFACT conditions are defined; input absence is handled by MISSING_INPUT.

**Artifact write behavior:** Not applicable for this skill.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
- Constraint 2 (sub-criterion weights traceable to Tier 2B): Any criterion entry in `evaluation_matrix` has a non-null `weight` value not sourced from `evaluation_priority_weights.json` and lacking a `weight_source` field referencing that file → `failure_reason="Criterion <criterion_id> has weight <value> with no traceable Tier 2B source; weights must originate from evaluation_priority_weights.json per skill constitutional constraints"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the failure.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
No INCOMPLETE_OUTPUT conditions are defined explicitly in the execution logic. Output construction failures would surface as CONSTRAINT_VIOLATION or CONSTITUTIONAL_HALT. If a write error occurs at Step 5.1, return `failure_reason="call_analysis_summary.json could not be written"`.

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 1 (evaluation criteria from active evaluation form only): The skill cannot parse at least one evaluation criterion with `source_section` and `source_document` from the identified form file; OR criteria are constructed from prior knowledge rather than from the parsed form → `failure_reason="Evaluation criteria cannot be sourced from the provided form file for instrument type <resolved_instrument_type>; constructing criteria from generic knowledge is prohibited by CLAUDE.md §13.9 and §10.6"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No `call_analysis_summary.json` written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the constitutional halt.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` is `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/` only; no exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Validates output construction against artifact_schema_specification.yaml.*

---

### Canonical Artifact: `call_analysis_summary.json`

**Schema ID verified:** `orch.phase1.call_analysis_summary.v1` ✓

**Required fields checked:**

| Field | Required | Status | Notes |
|-------|----------|--------|-------|
| schema_id | true | ✓ Implemented | Set to "orch.phase1.call_analysis_summary.v1" in Step 3 and Step 4 |
| run_id | true | ✓ Implemented | Propagated from invoking agent run_id |
| artifact_status | false | ✓ Absent at write time | Runner-stamped post-gate |
| resolved_instrument_type | true | ✓ Implemented | Derived from selected_call.json via agent context |
| evaluation_matrix | true | ✓ Implemented | Built in Step 2.4 with criterion_id, criterion_name, weight, source_section, source_document per entry |
| compliance_checklist | true | ✓ Implemented | Built in Step 2.5 with requirement_id, description, status (enum), source_section, source_document |
| call_analysis_notes | false | ✓ Implemented | Optional summary string |

**Reads_from compliance:** All output fields derived from declared reads_from sources (evaluation_forms/ and evaluation_priority_weights.json) plus invoking-agent context for resolved_instrument_type. No external fields introduced.

**Corrections applied:** None. Output Construction and Outputs table already list every required schema field with correct schema_id and enum-compliant status values.

<!-- Step 8 complete: schema validation performed -->
