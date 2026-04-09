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

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier2a_instrument_schemas/evaluation_forms/` exists and is non-empty. If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="evaluation_forms/ directory is empty; cannot evaluate without the active instrument's evaluation form") and halt.
- Step 1.2: **Grant Agreement Annex guard** — inspect the identified evaluation form file. If the document's title or header contains "Annex", "Grant Agreement", "Model Grant Agreement", or "AGA": return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Document appears to be a Grant Agreement Annex. CLAUDE.md §13.1 prohibits evaluating against Grant Agreement Annex requirements") and halt.
- Step 1.3: Presence check and schema check — confirm `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` exists with `schema_id` = "orch.phase1.call_analysis_summary.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="call_analysis_summary.json not found or schema mismatch") and halt.
- Step 1.4: Presence check and schema check — confirm `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` exists with `schema_id` = "orch.tier5.assembled_draft.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="assembled_draft.json not found or schema mismatch") and halt.
- Step 1.5: Confirm at least one section file referenced in `assembled_draft.json sections[].artifact_path` exists and is readable. If no section files are accessible: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="No section files found in assembled draft") and halt.

### 2. Core Processing Logic

- Step 2.1: Identify and read the evaluation form file in `evaluation_forms/` that corresponds to the `resolved_instrument_type` from `call_analysis_summary.json`. Parse the form to extract:
  - All evaluation criteria (criterion_id, criterion_name, sub-criteria descriptions, scoring thresholds, grade descriptors for each score value on the 0–5 scale).
  - The scoring logic for each criterion (what constitutes a score of 0, 1, 2, 3, 4, 5 for each criterion).
- Step 2.2: Read `call_analysis_summary.json evaluation_matrix`. This provides the weighted criterion list. Build a **criteria set**: ordered list of `{criterion_id, criterion_name, weight}` from the evaluation_matrix. For each criterion_id in the evaluation_matrix: look up the corresponding sub-criteria and scoring descriptors from Step 2.1. If a criterion_id in the evaluation_matrix has no match in the evaluation form: log as Unresolved and continue.
- Step 2.3: Read each section file referenced in `assembled_draft.json`. Build a **section content map**: keyed by `section_id`, value is the `content` string. Also record `word_count` for each section.
- Step 2.4: For each evaluation criterion in the criteria set (from Step 2.2):
  - Step 2.4.1: Identify which proposal section(s) from the section content map are relevant to this criterion. Relevance is determined by: matching the criterion's sub-criteria keywords against section names and content. Each criterion should map to at least one section; if no section addresses a criterion: this is a critical finding.
  - Step 2.4.2: For each relevant section, apply the scoring logic for this criterion:
    - Read the sub-criteria for this criterion from the evaluation form.
    - For each sub-criterion: check whether the section content addresses it by applying the following three tests in order: (1) Presence test — does the section contain at least one sentence whose subject matter is the same as the sub-criterion's stated requirement? If no such sentence exists: the sub-criterion is absent (score-affecting gap). (2) Evidence test — if the sub-criterion requires evidence, claims, or justification (as stated in its description or grade descriptor), check whether the section provides at least one concrete piece of evidence (a specific result, reference, metric, methodology name, or project activity) rather than a general assertion. If the sub-criterion requires evidence but only a general assertion is present: this is a major weakness. (3) Specificity test — if the sub-criterion requires quantification, specific naming, or project-specific detail (as indicated in the grade descriptors for scores 4–5 vs. 1–2), check whether the section provides those specifics. Generic or abstract language where project-specific detail is required constitutes a minor or major weakness depending on whether the sub-criterion is mandatory for a passing score.
    - Determine the scoring band applicable to the section's treatment of this criterion by reading the grade descriptors directly from the evaluation form (do not apply generic quality judgments). The scoring band is determined by the lowest-scoring test that applies: if any mandatory sub-criterion is absent = 0–1 band; if evidence is missing for a required sub-criterion = 2–3 band; if specificity is weak = 3–4 band; if all tests pass = 4–5 band. Record which descriptor band applies and which sub-criterion drove the band assignment.
  - Step 2.4.3: For each weakness identified, assign severity:
    - **critical**: the criterion is not addressed at all in the proposal (no content addressing the criterion's subject matter), OR the section contains a claim that directly contradicts the criterion's requirements (e.g., claims an approach the evaluation form identifies as insufficient for a high score), OR a mandatory sub-criterion has zero coverage. A critical finding blocks a satisfactory score.
    - **major**: the criterion is addressed but a significant sub-criterion is missing or weakly addressed (e.g., the criterion requires quantified impact but only qualitative statements are provided, OR the criterion requires a specific methodology justification that is absent). A major finding would prevent a score above the threshold.
    - **minor**: the criterion is substantially addressed but a minor sub-criterion is underweight or lacks specificity (e.g., reference to a specific best practice mentioned in the evaluation form is absent but the general approach is adequate). A minor finding can be improved without restructuring.
  - Step 2.4.4: Build a finding record: `{ finding_id: "F-<n>", section_id: <section being assessed>, criterion: <criterion_id from evaluation_matrix>, description: <specific description of the weakness, referencing the sub-criterion text from the evaluation form>, severity: critical/major/minor, evidence: <quoted text from the draft that illustrates the weakness or absence>, recommendation: <specific change required to address the finding> }`.
- Step 2.5: Build the `revision_actions` array from the findings:
  - Create one revision action per finding.
  - Assign `priority` (integer, 1-based): critical findings first (lower numbers = higher priority), then major, then minor. Within severity class, order by criterion weight (higher weight = earlier action).
  - Each action: `{ action_id: "A-<n>", finding_id: <finding_id>, priority: <integer>, action_description: <specific change to make>, target_section: <section_id>, severity: <critical/major/minor> }`.

### 3. Output Construction

**`review_packet.json`:**
- `schema_id`: set to "orch.tier5.review_packet.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `findings`: derived from Step 2.4 — array of `{finding_id, section_id, criterion, description, severity, evidence, recommendation}`
- `revision_actions`: derived from Step 2.5 — array of `{action_id, finding_id, priority, action_description, target_section, severity}`, ordered by priority ascending

### 4. Conformance Stamping

- `schema_id`: set to "orch.tier5.review_packet.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier5_deliverables/review_packets/` if not present.
- Step 5.2: Write `review_packet.json` to `docs/tier5_deliverables/review_packets/review_packet.json`.

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
