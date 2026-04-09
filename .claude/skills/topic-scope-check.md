---
skill_id: topic-scope-check
purpose_summary: >
  Verify that a project concept or proposal section is within the thematic scope
  defined by Tier 2B scope requirements, and flag any out-of-scope claims to the
  decision log.
used_by_agents:
  - call_analyzer
  - concept_refiner
reads_from:
  - docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
  - docs/tier2b_topic_and_call_sources/extracted/call_constraints.json
writes_to:
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Scope boundary is defined by Tier 2B only; must not infer scope from generic programme knowledge"
  - "Out-of-scope flags must be written to decision log"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | scope_requirements.json — Tier 2B extracted | Scope boundary entries; scope element descriptions; source_section; source_document; status (Confirmed/Inferred/Assumed/Unresolved) | N/A — Tier 2B extracted artifact | Defines the authoritative thematic scope boundary against which the project concept or proposal section is checked; any claim outside these boundaries is out-of-scope |
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | call_constraints.json — Tier 2B extracted | Constraint entries; constraint descriptions; source_section; source_document; status | N/A — Tier 2B extracted artifact | Provides call-specific constraints (e.g., excluded activities, mandatory approaches) that supplement scope boundaries; used to identify constraint violations |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/decision_log/` | Per-invocation decision log entry file (e.g., `scope_check_<timestamp>.json`) | N/A — decision log entry (no canonical schema_id in artifact_schema_specification.yaml for individual decision log entries) | decision_id; decision_type: "scope_check"; invoking_agent; phase_context; scope_findings array (claim, scope_element_ref, status: in_scope/out_of_scope/flagged); tier2b_source_refs; resolution_status; timestamp | No — decision log entries are not phase output canonical artifacts | Out-of-scope findings derived from comparison of the concept/section text against scope_requirements.json and call_constraints.json entries; every flagged claim must reference the Tier 2B scope element that defines the boundary |

**Note:** The decision log directory is not a canonical artifact with a schema_id. Entries are written as individual files per invocation. The directory path `docs/tier4_orchestration_state/decision_log/` is not directly registered in the artifact_registry as a single artifact; individual entries are written there by convention.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry. Decision log is a durable output directory used by multiple agents across phases; not tied to a single producing node. | Multiple nodes (context-dependent: n01_call_analysis or n02_concept_refinement per invoking agent) |

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
