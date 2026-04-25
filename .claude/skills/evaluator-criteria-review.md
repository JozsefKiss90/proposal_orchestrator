---
skill_id: evaluator-criteria-review
purpose_summary: >
  Assess proposal content against the scoring logic of the applicable evaluation
  criterion, identifying weaknesses by severity and producing structured feedback
  aligned to evaluator sub-criteria. Supports two modes: assembled-draft review
  (reads part_b_assembled_draft.json) and criterion-scoped review (reads a single
  criterion section artifact).
used_by_agents:
  - evaluator_reviewer
  - revision_integrator
reads_from:
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
  - docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json
  - docs/tier5_deliverables/proposal_sections/
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
| `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` | part_b_assembled_draft.json — canonical Tier 5 artifact | sections[].section_id, artifact_path; consistency_log[] | `orch.tier5.part_b_assembled_draft.v1` | The assembled draft being reviewed (assembled-draft mode); sections referenced in this artifact are evaluated against each evaluation criterion |
| `docs/tier5_deliverables/proposal_sections/<section>.json` (criterion-scoped mode) | Single criterion section artifact (excellence_section.json, impact_section.json, or implementation_section.json) | criterion, sub_sections[].content, validation_status, traceability_footer | `orch.tier5.excellence_section.v1` / `orch.tier5.impact_section.v1` / `orch.tier5.implementation_section.v1` | The single section being reviewed in criterion-scoped mode; only the criterion-specific evaluation sub-criteria are applied |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier5_deliverables/review_packets/review_packet.json` | review_packet.json | `orch.tier5.review_packet.v1` | schema_id, run_id, findings (array: finding_id, section_id, criterion[from evaluation form], description, severity[critical/major/minor], evidence, recommendation per finding), revision_actions (array: action_id, finding_id, priority, action_description, target_section, severity[critical/major/minor] per action) | Yes | findings: each finding mapped to a criterion_id from call_analysis_summary.json evaluation_matrix; criterion value drawn directly from the evaluation form (not from generic memory); evidence quoted from assembled_draft.json sections; severity assigned per finding; revision_actions: prioritised list derived from findings, with priority ordering by severity |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. Evaluation must not apply grant agreement annex requirements as criteria.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier5_deliverables/review_packets/review_packet.json` | Yes — artifact_id: a_t5_review_packets (directory); canonical file within that directory | n08e_evaluator_review |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier2a_instrument_schemas/evaluation_forms/` exists and is non-empty. If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="evaluation_forms/ directory is empty; cannot evaluate without the active instrument's evaluation form") and halt.
- Step 1.2: **Grant Agreement Annex guard** — inspect the identified evaluation form file. If the document's title or header contains "Annex", "Grant Agreement", "Model Grant Agreement", or "AGA": return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Document appears to be a Grant Agreement Annex. CLAUDE.md §13.1 prohibits evaluating against Grant Agreement Annex requirements") and halt.
- Step 1.3: Presence check and schema check — confirm `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` exists with `schema_id` = "orch.phase1.call_analysis_summary.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="call_analysis_summary.json not found or schema mismatch") and halt.
- Step 1.4: **Mode determination.** The invoking agent specifies the review mode via context:
  - **Assembled-draft mode** (default): review the complete assembled Part B draft. Proceed to Step 1.4a.
  - **Criterion-scoped mode**: review a single criterion-aligned section artifact. Proceed to Step 1.4b.
- Step 1.4a (assembled-draft mode): Presence check and schema check — confirm `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` exists with `schema_id` = "orch.tier5.part_b_assembled_draft.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="part_b_assembled_draft.json not found or schema mismatch") and halt.
- Step 1.4b (criterion-scoped mode): Presence check and schema check — confirm the section artifact at the path specified by the invoking agent exists and its `schema_id` matches one of: "orch.tier5.excellence_section.v1", "orch.tier5.impact_section.v1", or "orch.tier5.implementation_section.v1". If absent or schema mismatch: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="Criterion section artifact not found or schema mismatch") and halt.
- Step 1.5 (assembled-draft mode only): Confirm at least one section file referenced in `part_b_assembled_draft.json sections[].artifact_path` exists and is readable. If no section files are accessible: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="No section files found in assembled draft") and halt.

### 2. Core Processing Logic

- Step 2.1: Identify and read the evaluation form file in `evaluation_forms/` that corresponds to the `resolved_instrument_type` from `call_analysis_summary.json`. Parse the form to extract:
  - All evaluation criteria (criterion_id, criterion_name, sub-criteria descriptions, scoring thresholds, grade descriptors for each score value on the 0–5 scale).
  - The scoring logic for each criterion (what constitutes a score of 0, 1, 2, 3, 4, 5 for each criterion).
- Step 2.2: Read `call_analysis_summary.json evaluation_matrix`. This provides the weighted criterion list. Build a **criteria set**: ordered list of `{criterion_id, criterion_name, weight}` from the evaluation_matrix. For each criterion_id in the evaluation_matrix: look up the corresponding sub-criteria and scoring descriptors from Step 2.1. If a criterion_id in the evaluation_matrix has no match in the evaluation form: log as Unresolved and continue.
- Step 2.3: Build the **section content map**:
  - *Assembled-draft mode*: Read each section file referenced in `part_b_assembled_draft.json sections[].artifact_path`. Build a map keyed by `section_id`, value is the `content` string. Also record `word_count` for each section.
  - *Criterion-scoped mode*: Read the single criterion section artifact. Build a map with one entry: the section's `criterion` as key, the concatenation of all `sub_sections[].content` as value. Record the aggregate `word_count`.
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

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Evaluation must apply the active instrument evaluation criteria only"

**Decision point in execution logic:** Step 2.2 — at the point the `criteria set` is built from `call_analysis_summary.json evaluation_matrix` and Step 2.4 — at the point findings are generated for each criterion.

**Exact failure condition:** (a) The criteria set used for evaluation contains criterion_ids that do not exist in `call_analysis_summary.json evaluation_matrix` (i.e., criteria invented from prior knowledge); OR (b) findings are generated for evaluation criteria not present in the active instrument's evaluation form (i.e., generic evaluation dimensions not specific to the active instrument).

**Enforcement mechanism:** In Step 2.2, the criteria set must be built exclusively from the `evaluation_matrix` in `call_analysis_summary.json`. No criterion may be added from agent prior knowledge of "typical" Horizon Europe evaluation criteria. In Step 2.4.1, if a section is being evaluated against a criterion_id that is not in the `evaluation_matrix`: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Evaluation criterion <criterion_id> not found in call_analysis_summary.json evaluation_matrix; evaluation must apply active instrument criteria only per CLAUDE.md §11.2 and §10.6"). No `review_packet.json` written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No output written.

**Hard failure confirmation:** Yes — evaluating against criteria not in the active instrument evaluation form is a categorical prohibition.

**CLAUDE.md §13 cross-reference:** §10.6 — "Agents must not substitute their prior knowledge of Horizon Europe requirements for the contents of Tier 1 and Tier 2 source documents." §11.2 — "Deliverables must be compliant with the active instrument's application form structure and constraints."

---

### Constraint 2: "Must not evaluate against grant agreement annex requirements"

**Decision point in execution logic:** Step 1.2 — the Grant Agreement Annex guard is applied at input validation before any processing begins.

**Exact failure condition:** The evaluation form file identified in `evaluation_forms/` has a title, header, or filename containing "Annex", "Grant Agreement", "Model Grant Agreement", or "AGA" — AND the skill continues to use it as the evaluation authority without halting.

**Enforcement mechanism:** Step 1.2 is an unconditional guard that fires before Step 2 begins. If the guard condition triggers: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Document '<filename>' appears to be a Grant Agreement Annex. CLAUDE.md §13.1 prohibits evaluating against Grant Agreement Annex requirements; evaluation must apply the active instrument evaluation form criteria only") and halt. This guard cannot be bypassed, disabled, or deferred. Its enforcement is identical in structure to the guard in `instrument-schema-normalization` — both implement the same categorical prohibition from CLAUDE.md §13.1 in their respective domains.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). Immediate halt before any evaluation. No `review_packet.json` written.

**Hard failure confirmation:** Yes — unconditional halt; this is a categorical prohibition with no exceptions.

**CLAUDE.md §13 cross-reference:** §13.1 — "Treating Grant Agreement Annex templates as the governing structural schema for proposal writing." The same prohibition applies to evaluation: Grant Agreement Annexes may not serve as evaluation criteria.

---

### Constraint 3: "Weakness severity (critical/major/minor) must be assigned to each finding"

**Decision point in execution logic:** Step 2.4.3 — at the point severity is determined for each weakness, and Step 3 — at the point `findings` array entries are constructed.

**Exact failure condition:** Any finding entry in the `findings` array has a `severity` field that is absent, null, or contains a value other than exactly "critical", "major", or "minor".

**Enforcement mechanism:**

DETERMINISTIC BRANCHING RULE:
IF mandatory sub-criterion has zero coverage: severity = "critical"
IF evidence required but only general assertion present: severity = "major"
IF specificity weak but criterion substantially addressed: severity = "minor"
IF severity field is absent or not in {critical, major, minor} at write time:
→ INCOMPLETE_OUTPUT (halt before writing)
→ return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Finding <finding_id> is missing a valid severity assignment (critical/major/minor); severity must be assigned to each finding per skill constitutional constraints and CLAUDE.md §12.2")
→ No `review_packet.json` written

Every finding record produced in Step 2.4.4 MUST carry a severity value from the enumeration {critical, major, minor}. No other values are valid.

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). No output written.

**Hard failure confirmation:** Yes — findings without severity assignments are non-conformant outputs that may not be written to canonical paths.

**CLAUDE.md §13 cross-reference:** §12.2 — validation status vocabulary applies to validation outputs. §12.1 — "Every phase output must be reviewable." A finding without severity is not reviewable in a structured way.

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier2a_instrument_schemas/evaluation_forms/` directory is empty → `failure_reason="evaluation_forms/ directory is empty; cannot evaluate without the active instrument's evaluation form"`
- Step 1.3: `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` is absent or schema mismatch → `failure_reason="call_analysis_summary.json not found or schema mismatch"`
- Step 1.4a (assembled-draft mode): `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` is absent or schema mismatch → `failure_reason="part_b_assembled_draft.json not found or schema mismatch"`
- Step 1.4b (criterion-scoped mode): Criterion section artifact at specified path is absent or schema mismatch → `failure_reason="Criterion section artifact not found or schema mismatch"`
- Step 1.5 (assembled-draft mode): No section files referenced in `part_b_assembled_draft.json` are accessible → `failure_reason="No section files found in assembled draft"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill reads from source document directories and canonical phase artifacts. Schema mismatch conditions for `call_analysis_summary.json` and `part_b_assembled_draft.json` (or criterion section artifact in criterion-scoped mode) are captured in Steps 1.3 and 1.4 as MISSING_INPUT (per the existing Input Validation Sequence). No additional MALFORMED_ARTIFACT conditions are defined.

**Artifact write behavior:** Not applicable for this skill.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use CONSTITUTIONAL_HALT or INCOMPLETE_OUTPUT as appropriate.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 3 (weakness severity must be assigned to each finding): Any finding entry in the `findings` array has a `severity` field that is absent, null, or not in {critical, major, minor} at write time → `failure_reason="Finding <finding_id> is missing a valid severity assignment (critical/major/minor); severity must be assigned to each finding per skill constitutional constraints and CLAUDE.md §12.2"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Step 1.2 (Grant Agreement Annex guard): The evaluation form file contains "Annex", "Grant Agreement", "Model Grant Agreement", or "AGA" in its title or header → `failure_reason="Document '<filename>' appears to be a Grant Agreement Annex. CLAUDE.md §13.1 prohibits evaluating against Grant Agreement Annex requirements"`
- Constraint 1 (active instrument evaluation criteria only): Evaluation is attempted against a criterion_id not present in `call_analysis_summary.json evaluation_matrix` → `failure_reason="Evaluation criterion <criterion_id> not found in call_analysis_summary.json evaluation_matrix; evaluation must apply active instrument criteria only per CLAUDE.md §11.2 and §10.6"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No `review_packet.json` written. Decision log write is not in this skill's declared `writes_to` scope; the invoking agent is responsible for logging the constitutional halt.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: skills whose `writes_to` includes `decision_log/` or `validation_reports/` MAY write failure records to those paths even when the primary output fails. This skill's `writes_to` is `docs/tier5_deliverables/review_packets/` only; no exception applies.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Validation of Output Construction against `artifact_schema_specification.yaml` for `review_packet.json`.*

---

### Artifact: `review_packet.json`

**Schema ID:** `orch.tier5.review_packet.v1`

**Spec location:** `artifact_schema_specification.yaml` §2.2 (Tier 5 deliverables) — `review_packet` entry.

**Required fields per spec:**
- `schema_id` (string, const "orch.tier5.review_packet.v1")
- `run_id` (string)
- `findings` (array) — each entry has required `finding_id`, `section_id`, `criterion`, `description`, `severity` (enum: critical/major/minor); optional `evidence`, `recommendation`
- `revision_actions` (array) — each entry has required `action_id`, `finding_id`, `priority` (integer, 1-based), `action_description`, `target_section`, `severity` (enum: critical/major/minor)
- `artifact_status` (optional, enum [valid, invalid]) — runner-stamped; must be ABSENT at write time

**Output Construction (Step 3) verification:**
| Field | Set by skill? | Value source | Conformant? |
|-------|---------------|--------------|-------------|
| `schema_id` | Yes (Step 3, Step 4) | const "orch.tier5.review_packet.v1" | Yes — exact match |
| `run_id` | Yes (Step 3, Step 4) | invoking agent's run_id context parameter | Yes |
| `findings[]` | Yes (Step 2.4.4, Step 3) | each finding built with finding_id, section_id, criterion (from evaluation_matrix), description, severity (enum-validated in Step 2.4.3 and Constraint 3), evidence (quoted text), recommendation | Yes — all required item_schema fields present; severity restricted to enum |
| `revision_actions[]` | Yes (Step 2.5, Step 3) | each action built with action_id, finding_id, priority (integer, 1-based), action_description, target_section, severity | Yes — all required item_schema fields present; priority correctly 1-based integer; severity enum-compliant |
| `artifact_status` | ABSENT at write time (Step 4 explicit) | runner stamps post-gate | Yes — correctly absent |

**reads_from compliance:** Skill reads from `docs/tier2a_instrument_schemas/evaluation_forms/`, `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/`, and `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` (assembled-draft mode) or criterion section artifacts in `docs/tier5_deliverables/proposal_sections/` (criterion-scoped mode). All declared in frontmatter `reads_from`. Compliant.

**writes_to compliance:** Skill writes only to `docs/tier5_deliverables/review_packets/review_packet.json`. Declared in frontmatter `writes_to`. Compliant.

**Severity enum alignment:** The spec restricts `findings[].severity` and `revision_actions[].severity` to `[critical, major, minor]`. The skill enforces this via Constraint 3 (INCOMPLETE_OUTPUT) and the deterministic branching rule in Step 2.4.3. Enforcement matches the schema enum exactly.

**Gaps identified:** None.

**Corrections applied:** None — Output Construction is already fully conformant with `orch.tier5.review_packet.v1`.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
