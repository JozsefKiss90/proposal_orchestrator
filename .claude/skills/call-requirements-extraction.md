---
skill_id: call-requirements-extraction
purpose_summary: >
  Extract binding topic-specific requirements from work programme and call extract
  documents, producing structured output with a source section reference for every
  extracted element.
used_by_agents:
  - call_analyzer
reads_from:
  - docs/tier2b_topic_and_call_sources/work_programmes/
  - docs/tier2b_topic_and_call_sources/call_extracts/
writes_to:
  - docs/tier2b_topic_and_call_sources/extracted/
constitutional_constraints:
  - "Must not invent call requirements not present in source documents"
  - "Must carry source section references for every extracted element"
  - "Must apply Confirmed/Inferred/Assumed/Unresolved status"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier2b_topic_and_call_sources/work_programmes/` | Work programme source documents (PDF/DOCX) for the relevant Horizon Europe cluster | Full document text; section identifiers; topic descriptions; expected outcomes; expected impacts; scope requirements; eligibility conditions; evaluation criteria | N/A — source document directory (dir_non_empty check only) | Primary authoritative source from which all Tier 2B extracted fields are read; every extracted element must carry a section reference back to this directory |
| `docs/tier2b_topic_and_call_sources/call_extracts/` | Call extract documents (PDF/DOCX) for the specific topic | Topic identifier; call deadline; scope narrative; specific conditions; evaluation priority weightings | N/A — source document directory (dir_non_empty check only) | Supplements the work programme with call-specific constraints and priority weighting; used when topic-level detail not fully present in the work programme |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | call_constraints.json | N/A — Tier 2B extracted (not a phase output canonical artifact) | constraint entries with source_section and source_document per item; Confirmed/Inferred/Assumed/Unresolved status per item | No — Tier 2B extracted artifact, not a phase output | Extracted directly from work programme and call extract source documents |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | expected_outcomes.json | N/A — Tier 2B extracted | expected outcome entries with source_section, source_document, and status per item | No | Extracted from work programme expected outcomes sections |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | expected_impacts.json | N/A — Tier 2B extracted | expected impact entries with source_section, source_document, and status per item; impact_id used as join key in Phase 5 | No | Extracted from work programme expected impacts sections |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | scope_requirements.json | N/A — Tier 2B extracted | scope boundary entries with source_section, source_document, and status per item | No | Extracted from topic scope sections of work programme and call extract |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | eligibility_conditions.json | N/A — Tier 2B extracted | eligibility condition entries with source_section, source_document, and status per item | No | Extracted from eligibility and participation conditions in work programme |
| `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | evaluation_priority_weights.json | N/A — Tier 2B extracted | criterion-level weight entries with source_section, source_document per item | No | Extracted from evaluation criteria weighting tables in call extract and work programme |

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | Yes — artifact_id: a_t2b_call_constraints | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | Yes — artifact_id: a_t2b_expected_outcomes | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Yes — artifact_id: a_t2b_expected_impacts | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | Yes — artifact_id: a_t2b_scope_requirements | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | Yes — artifact_id: a_t2b_eligibility_conditions | n01_call_analysis |
| `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | Yes — artifact_id: a_t2b_evaluation_priority_weights | n01_call_analysis |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier2b_topic_and_call_sources/work_programmes/` exists and is non-empty (dir_non_empty). If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="work_programmes/ directory is empty; cannot extract call requirements without source documents") and halt.
- Step 1.2: Presence check — confirm `docs/tier2b_topic_and_call_sources/call_extracts/` exists and is non-empty (dir_non_empty). If empty: log as Assumed (work programme is the sole source) and continue; do not halt.
- Step 1.3: Confirm that the invoking agent has provided the target topic identifier (from `docs/tier3_project_instantiation/call_binding/selected_call.json`) as context. If not provided: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="selected_call topic identifier required to scope extraction") and halt.
- Step 1.4: Confirm source documents in work_programmes/ are readable (not corrupted or inaccessible). If any file is unreadable: log as Unresolved in pre-extraction notes; continue with readable files only, but flag in all output files that coverage may be incomplete.

### 2. Core Processing Logic

- Step 2.1: Index all files in `docs/tier2b_topic_and_call_sources/work_programmes/` and `docs/tier2b_topic_and_call_sources/call_extracts/`. For each file, record the filename and parse the section structure (section identifiers and headings).
- Step 2.2: Locate sections in the work programme documents that correspond to the target topic identifier from selected_call.json. Mark these sections as the primary extraction scope.
- Step 2.3: Extract **call_constraints** entries: for each section stating what the call requires, excludes, or mandates (e.g., technology readiness levels, excluded activities, mandatory consortium types), create one entry. Each entry must carry: a `constraint_id` (unique, e.g., "CC-01"), `description` (verbatim or close paraphrase of the source text), `source_section` (e.g., "Section 2.1.3"), `source_document` (filename), and `status`. Status assignment rules: Confirmed = the constraint is explicitly stated as a requirement, exclusion, or mandate in the source text. Inferred = the constraint is logically derivable from stated requirements (must state the derivation chain in an `inference_note` field). Assumed = the constraint is structurally expected for this instrument type but not explicitly stated (must declare the assumption in an `assumption_note` field). Unresolved = the work programme and call extract give conflicting signals about the constraint (must name both sources and describe the conflict in a `conflict_note` field).
- Step 2.4: Extract **expected_outcomes** entries: for each outcome statement in the work programme (typically under "Expected outcomes" headings), create one entry. Each entry must carry: `outcome_id` (unique, e.g., "EO-01"), `description`, `source_section`, `source_document`, `status` (same assignment rules as Step 2.3). The `outcome_id` value becomes the join key for Phase 2 alignment checking.
- Step 2.5: Extract **expected_impacts** entries: for each impact statement in the work programme (typically under "Expected impacts" headings), create one entry. Each entry must carry: `impact_id` (unique, e.g., "EI-01"), `description`, `source_section`, `source_document`, `status`. The `impact_id` value is the join key for Phase 5 impact pathway mapping and must be preserved exactly as assigned here throughout all downstream phases.
- Step 2.6: Extract **scope_requirements** entries: for each statement defining the thematic scope, required focus areas, or explicitly excluded topics, create one entry. Each entry must carry: `scope_element_id` (unique, e.g., "SR-01"), `description`, `boundary_type` (one of: `required_focus`, `excluded_topic`, `conditional_requirement`), `source_section`, `source_document`, `status`.
- Step 2.7: Extract **eligibility_conditions** entries: for each participation eligibility condition (minimum consortium size, partner type requirements, country restrictions, ethics requirements), create one entry. Each entry must carry: `condition_id` (unique, e.g., "EC-01"), `description`, `condition_type` (one of: `consortium_composition`, `partner_type`, `country_restriction`, `ethics`, `other`), `source_section`, `source_document`, `status`.
- Step 2.8: Extract **evaluation_priority_weights** entries: for each evaluation criterion with an explicit or implied weighting (often in weighting tables or "evaluation criteria" sections of the call extract), create one entry. Each entry must carry: `criterion_id` (matching the form criterion label, e.g., "Excellence", "Impact"), `weight` (numeric percentage if stated, null if not stated), `priority_note` (any call-specific priority statement), `source_section`, `source_document`, `status`.
- Step 2.9: If the call extract contains information that supplements or conflicts with the work programme for any of the six extraction categories above: for supplementary information, add additional entries from the call extract with `source_document` pointing to the call extract file. For conflicting information: set `status` to "Unresolved" on all affected entries and populate `conflict_note` naming both sources.
- Step 2.10: Count total entries across all six output files. If any output file would be empty (zero entries): do not write that file. Return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="<filename> contains zero extractable entries; source document may not correspond to the target topic") and halt.

### 3. Output Construction

For each of the six output JSON files, the structure is an array of entries as defined below.

**`call_constraints.json`:**
- Root field: `constraints` — array of entries produced in Step 2.3
- Each entry: `constraint_id` (string, unique), `description` (string), `source_section` (string, non-empty), `source_document` (string, filename from work_programmes/ or call_extracts/), `status` (one of: "Confirmed", "Inferred", "Assumed", "Unresolved"), and conditionally: `inference_note` (if Inferred), `assumption_note` (if Assumed), `conflict_note` (if Unresolved)

**`expected_outcomes.json`:**
- Root field: `expected_outcomes` — array of entries produced in Step 2.4
- Each entry: `outcome_id` (string, unique), `description` (string), `source_section` (string), `source_document` (string), `status` (Confirmed/Inferred/Assumed/Unresolved), and conditional note fields

**`expected_impacts.json`:**
- Root field: `expected_impacts` — array of entries produced in Step 2.5
- Each entry: `impact_id` (string, unique — preserved as join key for Phase 5), `description` (string), `source_section` (string), `source_document` (string), `status`, and conditional note fields

**`scope_requirements.json`:**
- Root field: `scope_requirements` — array of entries produced in Step 2.6
- Each entry: `scope_element_id` (string, unique), `description` (string), `boundary_type` (string, one of required_focus/excluded_topic/conditional_requirement), `source_section` (string), `source_document` (string), `status`, and conditional note fields

**`eligibility_conditions.json`:**
- Root field: `eligibility_conditions` — array of entries produced in Step 2.7
- Each entry: `condition_id` (string, unique), `description` (string), `condition_type` (string), `source_section` (string), `source_document` (string), `status`, and conditional note fields

**`evaluation_priority_weights.json`:**
- Root field: `evaluation_priority_weights` — array of entries produced in Step 2.8
- Each entry: `criterion_id` (string — must match the evaluation form criterion label for the active instrument), `weight` (number or null), `priority_note` (string), `source_section` (string), `source_document` (string), `status`, and conditional note fields

### 4. Conformance Stamping

These are Tier 2B extracted artifacts, not phase output canonical artifacts. No `schema_id`, `run_id`, or `artifact_status` field applies. Do not add these fields.

### 5. Write Sequence

- Step 5.1: Write `call_constraints.json` to `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json`
- Step 5.2: Write `expected_outcomes.json` to `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json`
- Step 5.3: Write `expected_impacts.json` to `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json`
- Step 5.4: Write `scope_requirements.json` to `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json`
- Step 5.5: Write `eligibility_conditions.json` to `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json`
- Step 5.6: Write `evaluation_priority_weights.json` to `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json`
- All six files must be written before the skill returns success. If any write fails: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="<filename> could not be written") and halt.

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
