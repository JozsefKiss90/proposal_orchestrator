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

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
