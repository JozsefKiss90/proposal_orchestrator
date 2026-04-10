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

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Unattributed claims must be flagged, not silently accepted as Confirmed"

**Decision point in execution logic:** Step 2.3.3 — at the point each material claim's status is assigned based on traceability_footer examination.

**Exact failure condition:** A material claim has no matching source reference in `traceability_footer.primary_sources[]` AND the claim is about a project fact (partner capability, specific objective, specific outcome, specific metric) — AND the claim is assigned status "Confirmed" or "Inferred" rather than "Unresolved".

**Enforcement mechanism:** In Step 2.3.3, the status assignment rules are deterministic:
- **Unresolved** is mandatory when: no source reference is provided AND the claim is about a project fact. There is no judgment threshold — absence of source reference for a project-fact claim always yields Unresolved, not Confirmed.
- **Assumed** is the weakest permissible non-flagged status, applicable only to generic structural statements that no source needs to validate. Project-fact claims cannot be Assumed — they must be Unresolved.

If any material claim about a project fact is assigned status "Confirmed" or "Inferred" without a verifiable source reference in `primary_sources[]`: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Material claim about project fact <claim_id> was assigned Confirmed/Inferred status without a Tier 1–4 source reference; unattributed project-fact claims must be flagged as Unresolved per CLAUDE.md §10.5 and §12.2"). No validation report written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No report written.

**Hard failure confirmation:** Yes — silently accepting unattributed project-fact claims as Confirmed is a categorical prohibition.

**CLAUDE.md §13 cross-reference:** §10.5 — "Unattributed claims must be flagged, not asserted." §12.2 — "Confirmed — directly evidenced by a named source in Tier 1–3; the source artifact must be named." §13.10 — "Producing outputs in Tier 5 that are not traceable to specific inputs in Tier 1–4."

---

### Constraint 2: "Confirmed status requires naming the specific source artifact"

**Decision point in execution logic:** Step 2.3.3 — at the point a claim is assigned status "Confirmed", and Step 3 — at the point the `claim_audit_results` array is constructed.

**Exact failure condition:** Any claim_audit_result entry has `status: "confirmed"` AND the `source_ref` field is empty, null, or contains only a directory path without a specific filename and relevant field identification. Equivalently: Confirmed status is assigned without naming the exact file in the Tier 1–4 hierarchy that supports the claim.

**Enforcement mechanism:** In Step 2.3.3, condition for Confirmed status requires both: (a) a `primary_sources[]` entry with a `source_path` referencing a specific Tier 1–4 file (not just a directory), AND (b) the content of that file being directly consistent with the claim.

DETERMINISTIC CHECK AT WRITE TIME:
IF `status == "confirmed"` AND `source_ref` is null, empty, OR is only a directory path (does not end in a filename with extension):
→ CONSTITUTIONAL_HALT immediately before writing the report
→ return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Claim <claim_id> assigned Confirmed status but source_ref does not name a specific artifact; CLAUDE.md §12.2 requires naming the specific source artifact for Confirmed status")
→ No report written

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No validation report written.

**Hard failure confirmation:** Yes — Confirmed status without a specific named source artifact is a constitutional violation per CLAUDE.md §12.2.

**CLAUDE.md §13 cross-reference:** §12.2 — "Confirmed — directly evidenced by a named source in Tier 1–3; the source artifact must be named." §10.5 — "Unattributed claims must be flagged, not asserted."

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: Invoking agent provides neither a `section_id` nor an assembled-draft audit mode instruction → `failure_reason="section_id or assembled_draft audit mode required"`
- Step 1.2 (per-section mode): Section file `<section_id>.json` does not exist at `docs/tier5_deliverables/proposal_sections/` → `failure_reason="Proposal section file <section_id>.json not found"`
- Step 1.3 (assembled draft mode): `assembled_draft.json` is absent or schema mismatch → `failure_reason="assembled_draft.json not found or schema mismatch"`
- Step 1.5: No Tier 1–4 reference directory is accessible → `failure_reason="No Tier 1–4 reference artifacts accessible for traceability verification"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.4: A section file to be audited has `schema_id` ≠ "orch.tier5.proposal_section.v1" → recorded as a traceability failure for that section; evaluation continues. This does not produce a MALFORMED_ARTIFACT SkillResult halt — the schema mismatch is treated as a finding.

Note: schema mismatch in section files is surfaced as a traceability finding in the report, not as a MALFORMED_ARTIFACT halt.

**Artifact write behavior:** Not applicable (schema mismatch produces a finding in the report, not a halt).

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use CONSTITUTIONAL_HALT as appropriate.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
No INCOMPLETE_OUTPUT conditions are explicitly defined in the execution logic. Write errors at Step 5.1 should return `failure_reason="Traceability report could not be written to validation_reports/"`.

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 1 (unattributed claims flagged, not silently accepted as Confirmed): Any material claim about a project fact is assigned status "Confirmed" or "Inferred" without a verifiable source reference in `traceability_footer.primary_sources[]` → `failure_reason="Material claim about project fact <claim_id> was assigned Confirmed/Inferred status without a Tier 1–4 source reference; unattributed project-fact claims must be flagged as Unresolved per CLAUDE.md §10.5 and §12.2"`
- Constraint 2 (Confirmed status requires naming the specific source artifact): Any claim_audit_result entry has `status: "confirmed"` AND `source_ref` is null, empty, or is only a directory path → `failure_reason="Claim <claim_id> assigned Confirmed status but source_ref does not name a specific artifact; CLAUDE.md §12.2 requires naming the specific source artifact for Confirmed status"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No validation report written. A validation report entry MAY be written to `docs/tier4_orchestration_state/validation_reports/` documenting the halt if the directory is accessible, as `validation_reports/` is in this skill's declared `writes_to` scope.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: this skill's `writes_to` includes `docs/tier4_orchestration_state/validation_reports/`; a failure record MAY be written there even when the primary output fails.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Group C skill whose sole output is a validation report file; no canonical `schema_id` applies. Conformance is governed by CLAUDE.md §10.5, §12.1, §12.2, §13.10.*

---

### Upstream input schema verification

- **Proposal section files** (`orch.tier5.proposal_section.v1`): skill reads `content`, `validation_status.claim_statuses[]`, `traceability_footer.primary_sources[]`. All three field paths match spec §3 (`tier5_proposal_section_schema`) exactly. The spec defines `validation_status.claim_statuses[].status` enum as lowercase `[confirmed, inferred, assumed, unresolved]` — the skill uses the same lowercase vocabulary. Compliant.
- **`assembled_draft.json`** (`orch.tier5.assembled_draft.v1`): skill reads `sections[].section_id, artifact_path`. Field paths match spec §2.1. Compliant.
- **Tier 1–4 reference directories**: skill declares all four `extracted/` and Tier 3 directories in `reads_from`; checks only path existence and content consistency for traceability verification. No schema_id binding required for reference reads.

### Artifact: `traceability_<section_id>_<timestamp>.json` (validation report)

**Canonical schema:** None — operational validation report, not registered.

**Output Construction fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `report_id` | Yes (Step 3) | skill-defined | Yes |
| `skill_id` | Yes | matches frontmatter | Yes |
| `invoking_agent` | Yes | agent context | Yes |
| `run_id_reference` | Yes | agent context | Yes |
| `section_id_audited` | Yes | `section_id` or "all_sections" | Yes |
| `claim_audit_results[]` | Yes (Step 2.5, Step 3) | per entry: claim_id, claim_summary, status (enum: confirmed/inferred/assumed/unresolved), source_ref, flag_reason | Yes — status enum matches §12.2 vocabulary exactly |
| `summary` | Yes (Step 2.6, Step 3) | total_claims, confirmed, inferred, assumed, unresolved | Yes |
| `no_unsupported_claims_declaration` | Yes (Step 2.4) | boolean — matches spec's `traceability_footer.no_unsupported_claims_declaration` semantics | Yes |
| `timestamp` | Yes | ISO 8601 | Yes |

**CLAUDE.md §12.2 vocabulary compliance:** This skill's `claim_audit_results[].status` field uses lowercase `{confirmed, inferred, assumed, unresolved}` — directly aligned with the CLAUDE.md §12.2 validation status vocabulary and consistent with the upstream `proposal_section.v1` schema's `validation_status.claim_statuses[].status` enum. Constraint 1 and Constraint 2 enforce the §12.2 semantics: Confirmed requires named source; Unresolved is mandatory for unattributed project-fact claims; Assumed is restricted to generic structural statements. Full vocabulary conformance.

**`schema_id` / `artifact_status`:** Step 4 correctly states these do not apply to validation reports.

**reads_from compliance:** All six declared reference directories are used in the execution logic (Step 1.5, Step 2.3). Compliant.

**writes_to compliance:** Writes only to `docs/tier4_orchestration_state/validation_reports/`. Compliant.

**Gaps identified:** None.

**Corrections applied:** None.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
