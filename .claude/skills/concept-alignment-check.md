---
skill_id: concept-alignment-check
purpose_summary: >
  Check the alignment between the project concept and the call expected outcomes and
  scope requirements, identifying vocabulary gaps, framing mismatches, and uncovered
  expected outcomes.
used_by_agents:
  - concept_refiner
reads_from:
  - docs/tier3_project_instantiation/project_brief/
  - docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json
  - docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Alignment must be tested against Tier 2B extracted files, not assumed from concept vocabulary"
  - "Uncovered expected outcomes must be flagged, not silently assumed covered"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/project_brief/` | Project brief directory: concept_note (PDF/DOCX/MD), project_summary (PDF/DOCX/MD), strategic_positioning (PDF/DOCX/MD) | Concept description; stated objectives; target outcomes; approach narrative; differentiation claims; vocabulary used | N/A — Tier 3 source directory | Source of the project concept being evaluated; the text is compared term-by-term and claim-by-claim against Tier 2B expected outcomes and scope requirements |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | expected_outcomes.json — Tier 2B extracted | Expected outcome entries: outcome_id, description, source_section, source_document, status | N/A — Tier 2B extracted artifact | The authoritative list of call-required expected outcomes that the concept must address; uncovered outcomes must be flagged |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | scope_requirements.json — Tier 2B extracted | Scope boundary entries: scope element descriptions, source_section, source_document, status | N/A — Tier 2B extracted artifact | Defines the thematic scope boundary; concept claims outside this boundary are flagged as scope mismatches |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | concept_refinement_summary.json | `orch.phase2.concept_refinement_summary.v1` | schema_id, run_id, topic_mapping_rationale (object: topic_element_id, mapping_to_concept, tier2b_source_ref, tier3_evidence_ref per entry), scope_conflict_log (array: conflict_id, description, resolution_status, resolution_note, tier2b_source_ref per entry), strategic_differentiation (string, non-empty) | Yes | topic_mapping_rationale entries derived from expected_outcomes.json entries matched against project_brief content; scope_conflict_log derived from scope mismatches found; strategic_differentiation derived from strategic_positioning document in project_brief |
| `docs/tier4_orchestration_state/decision_log/` | Per-invocation decision log entry file | N/A — decision log entry | decision_id; decision_type: "concept_alignment"; invoking_agent; phase_context; alignment_findings; uncovered_outcomes list; vocabulary_gaps list; tier2b_source_refs; resolution_status; timestamp | No | Vocabulary gaps and uncovered outcomes derived from comparing concept vocabulary against expected_outcomes.json and scope_requirements.json entries |

**Note:** `artifact_status` must be ABSENT at write time for concept_refinement_summary.json; the runner stamps it post-gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | Yes — artifact_id: a_t4_phase2 (directory); canonical file within that directory | n02_concept_refinement |
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry | n02_concept_refinement |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
