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

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Confirm the invoking agent provides either: (a) a specific `section_id` as context (for per-section audit), or (b) an instruction to audit all sections from the assembled draft. If neither: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="section_id or assembled_draft audit mode required") and halt.
- Step 1.2 (per-section mode): Confirm the section file exists at `docs/tier5_deliverables/proposal_sections/<section_id>.json`. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="Proposal section file <section_id>.json not found") and halt.
- Step 1.3 (assembled draft mode): Confirm `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` exists with `schema_id` = "orch.tier5.assembled_draft.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="assembled_draft.json not found or schema mismatch") and halt. Extract `sections[].artifact_path` list; confirm each path exists.
- Step 1.4: Schema conformance check for each section file to be audited — confirm `schema_id` = "orch.tier5.proposal_section.v1". If mismatch: record as a traceability failure for that section and continue.
- Step 1.5: Confirm at least one Tier 1–4 reference directory is accessible: `docs/tier1_normative_framework/extracted/`, `docs/tier2a_instrument_schemas/extracted/`, `docs/tier2b_topic_and_call_sources/extracted/`, `docs/tier3_project_instantiation/`. If none are accessible: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="No Tier 1–4 reference artifacts accessible for traceability verification") and halt.

### 2. Core Processing Logic

- Step 2.1: For each section file to be audited, extract:
  - `content`: the full section text.
  - `validation_status.claim_statuses[]`: the pre-existing claim status array (if present).
  - `traceability_footer.primary_sources[]`: the declared source references.
- Step 2.2: **Material claim extraction** — from the `content` field, identify all material claims. A material claim is any of the following:
  - An assertion about a project fact: partner name, partner capability, consortium composition, project objective, approach, methodology, work package, deliverable, or timeline.
  - An assertion about call requirements: expected outcome, expected impact, scope requirement, eligibility condition.
  - An assertion about instrument requirements: section structure, page limit, evaluation criterion.
  - A quantitative or descriptive claim about project results, impacts, or KPIs.
  - Exclude: headings, cross-references (e.g., "as described in Section 2"), acknowledgement boilerplate.
  - Assign each material claim a `claim_id` (unique per section, e.g., "C1", "C2", ...) and a `claim_summary` (short descriptive string of what is being claimed).
- Step 2.3: For each material claim, evaluate traceability:
  - Step 2.3.1: Check whether `traceability_footer.primary_sources[]` contains a source reference that could reasonably be attributed to this claim. A source reference matches if: the `source_path` references a Tier 1–4 artifact and the `relevant_fields` (if present) or the source artifact's content domain is consistent with the claim subject matter.
  - Step 2.3.2: If a source reference is found, attempt to verify it: check whether the referenced path exists in the repository and whether the content of that file contains information consistent with the claim. This is a logical consistency check — does the named source plausibly support this claim?
  - Step 2.3.3: Assign status using the following criteria exactly:
    - **Confirmed**: A `primary_sources[]` entry references a specific Tier 1–4 artifact path that exists, AND the content of that artifact is directly consistent with the claim (the claim accurately represents what the source says). Both conditions required.
    - **Inferred**: A `primary_sources[]` entry references a Tier 1–4 artifact, AND the claim is a logical derivation from that source (not a direct statement). The derivation chain must be stateable: "Source [X] states [Y]; the claim derives [Z] from [Y] by [reasoning]". The derivation chain must be recorded in `source_ref`.
    - **Assumed**: No source reference is provided in `primary_sources[]`, but the claim is structurally expected (e.g., a generic statement about EU project management that no Tier 1–4 source needs to validate). The assumption must be explicitly declared — it is not silently treated as Confirmed. The `assumption_declared` flag must be set to true in `validation_status.claim_statuses[]` if present.
    - **Unresolved**: No source reference is provided AND the claim is about a project fact (partner capability, specific objective, specific outcome, or specific metric) — these cannot be Assumed and must have a Tier 3 source. OR: a source reference is provided but the referenced file does not exist or the content of the referenced file contradicts the claim. Flag reason must explain which condition applies.
- Step 2.4: Determine `no_unsupported_claims_declaration`: set to true only if ALL material claims have status Confirmed or Inferred (no Assumed or Unresolved claims remain). Set to false if any Assumed or Unresolved claims exist.
- Step 2.5: Build `claim_audit_results` array: one entry per material claim from Step 2.2.
- Step 2.6: Compute summary: `total_claims`, `confirmed` count, `inferred` count, `assumed` count, `unresolved` count.

### 3. Output Construction

**Traceability report file (e.g., `traceability_<section_id>_<agent_id>_<timestamp>.json`):**
- `report_id`: `"traceability_<section_id>_<agent_id>_<ISO8601_timestamp>"`
- `skill_id`: `"proposal-section-traceability-check"`
- `invoking_agent`: from agent context
- `run_id_reference`: from agent context
- `section_id_audited`: the section_id being audited (or "all_sections" for assembled draft mode)
- `claim_audit_results`: derived from Step 2.5 — array of `{claim_id, claim_summary, status (confirmed/inferred/assumed/unresolved), source_ref, flag_reason}`
- `summary`: derived from Step 2.6 — `{total_claims, confirmed, inferred, assumed, unresolved}`
- `no_unsupported_claims_declaration`: derived from Step 2.4 — boolean
- `timestamp`: ISO 8601

### 4. Conformance Stamping

Validation reports are not phase output canonical artifacts. No `schema_id` or `artifact_status` applies.

### 5. Write Sequence

- Step 5.1: Write the traceability report to `docs/tier4_orchestration_state/validation_reports/<report_id>.json`

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
