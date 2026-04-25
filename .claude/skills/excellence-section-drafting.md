---
skill_id: excellence-section-drafting
purpose_summary: >
  Draft the Excellence section of the RIA/IA Part B from Phase 2 concept
  refinement, Phase 3 WP structure, and Tier 3 project data. Produces
  excellence_section.json conforming to orch.tier5.excellence_section.v1.
used_by_agents:
  - excellence_writer
reads_from:
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier2b_topic_and_call_sources/extracted/
  - docs/tier3_project_instantiation/
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
writes_to:
  - docs/tier5_deliverables/proposal_sections/excellence_section.json
constitutional_constraints:
  - "Must verify budget gate passed before producing content"
  - "Must not fabricate project facts not present in Tier 3"
  - "Must not use Grant Agreement Annex structure"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool.

**Declared input files to read (in order):**
1. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` -- MUST be read first; verify `gate_pass_declaration` equals `"pass"` before any other action
2. `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` -- section identifiers, page limits, structural constraints for Excellence section
3. `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` -- Excellence criterion scoring logic and sub-criteria
4. `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` -- evaluation matrix and call priority weights
5. `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` -- refined concept, vocabulary alignment, topic mapping rationale
6. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` -- WP structure for methodology and interdisciplinarity grounding
7. `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` -- call expected outcomes for direct Tier 2B traceability of call-scope claims
8. `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` -- call expected impacts for direct Tier 2B traceability
9. `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` -- call scope requirements for direct Tier 2B traceability
10. `docs/tier3_project_instantiation/` -- project data (use Glob to discover, then Read relevant files: project_brief/, consortium/, architecture_inputs/objectives.json)

**Boundary constraints:**
- Do not read files outside the declared input set.
- Do not assume implicit context or reconstruct inputs from memory.
- Read each required file explicitly before using it.
- Base all reasoning ONLY on retrieved file content.
- Do not use generic Horizon Europe knowledge as a substitute for reading Tier 1-4 sources.

Return a SINGLE valid JSON object matching the output schema below.
Do not include explanations outside the JSON.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | Budget gate assessment | `gate_pass_declaration` | `orch.phase7.budget_gate_assessment.v1` | Verify budget gate passed before any drafting; CLAUDE.md Section 8.4 absolute prerequisite |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | Section schema registry | Section entries for Excellence (section identifiers, page limits, mandatory elements) | `orch.tier2a.section_schema_registry.v1` | Structural authority for Excellence section sub-sections and page limits |
| `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` | Evaluator expectations | Excellence criterion entry (criterion_id, sub-criteria, scoring thresholds, grade descriptors) | `orch.tier2a.evaluator_expectation_registry.v1` | Evaluation framing: what evaluators look for in Excellence section |
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | Call analysis summary | `evaluation_matrix` (criterion weights, source sections) | `orch.phase1.call_analysis_summary.v1` | Evaluation criterion weights and call-specific priorities |
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | Concept refinement summary | Refined concept, vocabulary alignment, topic mapping rationale | `orch.phase2.concept_refinement_summary.v1` | Call-aligned concept framing; evaluator vocabulary |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | WP structure | WP objectives, tasks, deliverables, interdependencies | `orch.phase3.wp_structure.v1` | Grounds methodology and interdisciplinarity claims in concrete project activities |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | Call expected outcomes | Expected outcome entries with source references | N/A -- Tier 2B extracted | Direct Tier 2B source for call expected outcomes; required in traceability_footer when making call-scope claims |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Call expected impacts | Expected impact entries with source references | N/A -- Tier 2B extracted | Direct Tier 2B source for call expected impacts; required in traceability_footer |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | Call scope requirements | Scope requirement entries with source references | N/A -- Tier 2B extracted | Direct Tier 2B source for call scope requirements; required in traceability_footer |
| `docs/tier3_project_instantiation/` | Project data (project_brief/, consortium/, architecture_inputs/) | Objectives, concept note, consortium capabilities, prior experience | N/A -- Tier 3 root directory | Sole source for all project-specific claims in the Excellence section |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier5_deliverables/proposal_sections/excellence_section.json` | Excellence section draft | `orch.tier5.excellence_section.v1` | schema_id, run_id, criterion (const "Excellence"), sub_sections (array: sub_section_id, title, content, word_count), validation_status, traceability_footer | Yes | sub_sections: drafted from Tier 3 project data and Phase 2-3 outputs, framed against Tier 2A Excellence criterion scoring logic; validation_status: per-claim Confirmed/Inferred/Assumed/Unresolved classification; traceability_footer: primary_sources array referencing Tier 1-4 artifacts |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier5_deliverables/proposal_sections/excellence_section.json` | Yes -- artifact_id: a_t5_excellence_section | n08a_excellence_drafting |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Read `budget_gate_assessment.json`. Check `gate_pass_declaration` equals `"pass"`. If absent or not `"pass"`: return `{"status": "failure", "failure_reason": "Budget gate has not passed (gate_pass_declaration is not 'pass'); CLAUDE.md Section 8.4 prohibits any Phase 8 activity before budget gate passes", "failure_category": "CONSTITUTIONAL_HALT"}` and halt.
- Step 1.2: Read `section_schema_registry.json`. Identify Excellence section entries (section identifiers, page limits, mandatory sub-sections). If empty or unreadable: return failure with `MISSING_INPUT`.
- Step 1.3: Read `evaluator_expectation_registry.json`. Identify the Excellence criterion entry with sub-criteria and scoring logic. If absent: return failure with `MISSING_INPUT`.
- Step 1.4: Read `call_analysis_summary.json`. Extract `evaluation_matrix` for Excellence criterion weight. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.5: Read `concept_refinement_summary.json`. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.6: Read `wp_structure.json`. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.7: Read Tier 3 project data. Confirm at least `project_brief/` and `architecture_inputs/objectives.json` are present. If absent: return failure with `MISSING_INPUT`.
- Step 1.8: **Grant Agreement Annex guard** -- inspect the section schema source. If any structural reference identifies a Grant Agreement Annex, Model Grant Agreement Annex, or "AGA" template as the schema source: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Section schema source appears to be a Grant Agreement Annex; CLAUDE.md Section 13.1 prohibits using Grant Agreement Annex structure for proposal writing") and halt.

### 2. Core Processing Logic

- Step 2.1: **Identify Excellence sub-sections.** From `section_schema_registry.json`, extract the ordered list of mandatory sub-sections for the Excellence section. For RIA/IA, these are:
  - Objectives and ambition
  - Relation to the work programme
  - Concept and methodology
  - Ambition
  - Interdisciplinary considerations
  - Gender dimension in research content

  The exact sub-section list is governed by the application form template via the section schema registry. Do not add sub-sections not present in the registry.

- Step 2.2: **Read evaluation framing.** From `evaluator_expectation_registry.json`, extract the Excellence criterion's sub-criteria, scoring thresholds, and grade descriptors. These define what evaluators look for. Frame all sub-section content to address these sub-criteria directly.

- Step 2.3: **Draft each sub-section.** For each Excellence sub-section identified in Step 2.1:

  - Step 2.3.1: **Source project-specific content.** Draw all project facts (objectives, concept, methodology, approach, consortium capabilities, prior experience) exclusively from Tier 3 (`docs/tier3_project_instantiation/`). Do not fabricate partner names, capabilities, objectives, or prior work not present in Tier 3 (CLAUDE.md Section 13.3).

  - Step 2.3.2: **Apply call-aligned vocabulary.** Use the refined concept vocabulary from `concept_refinement_summary.json` to frame content in call-specific language. Align with the topic mapping rationale.

  - Step 2.3.3: **Ground methodology in WP structure.** Reference concrete WP tasks, deliverables, and approaches from `wp_structure.json` when describing the methodology and concept. Methodology claims must be traceable to specific WP activities.

  - Step 2.3.4: **Address evaluator sub-criteria.** For each sub-criterion in the Excellence evaluation criterion (from Step 2.2), ensure the sub-section content addresses it. Apply the three-tier specificity test:
    - Presence: does the content address the sub-criterion's subject matter?
    - Evidence: does it provide concrete evidence (specific methods, prior results, references)?
    - Specificity: does it provide project-specific detail rather than generic assertions?

  - Step 2.3.5: **Respect page limits.** Check word count against page limits from `section_schema_registry.json`. Flag exceedances in `validation_status`.

  - Step 2.3.6: **Do not reference unvalidated budget figures.** Do not include budget amounts, person-months, or resource figures that are not confirmed in `budget_gate_assessment.json` (CLAUDE.md Section 8.3).

- Step 2.4: **Build validation_status.** For each material claim in the drafted content:
  - Assign Confirmed/Inferred/Assumed/Unresolved status per CLAUDE.md Section 12.2.
  - Confirmed requires naming the specific Tier 1-4 source artifact.
  - Project-fact claims without Tier 3 attribution must be Unresolved.
  - Set `overall_status` to the weakest status across all claims (unresolved > assumed > inferred > confirmed).
  - Build `claim_statuses` array with `claim_id`, `claim_summary`, `status`, `source_ref`.

- Step 2.5: **Build traceability_footer.** Populate `primary_sources` array with all Tier 1-4 artifacts used as sources for the section content. **Whenever the section asserts call scope, expected outcomes, expected impacts, or call requirements, include direct Tier 2B extracted source paths** (e.g., `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json`, `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json`) in `primary_sources[]` — not just indirect Tier 4 derivatives (Phase 1/2 outputs). This is required to pass the constitutional-compliance-check §13.2 check. Set `no_unsupported_claims_declaration` to true only if all claims are Confirmed or Inferred.

- Step 2.6: **Handle data gaps.** If Tier 3 is incomplete for any Excellence sub-section element: set the relevant claim status to Unresolved, document the gap in `claim_statuses`, and set `no_unsupported_claims_declaration: false`. Do not fabricate content to fill the gap (CLAUDE.md Section 11.5, Section 13.8).

- Step 2.7: **Gate-readiness check.** After building `validation_status`, check `overall_status`. If `overall_status` is `"unresolved"`: do NOT produce the output artifact. Instead, return `{"status": "failure", "failure_reason": "Excellence section has unresolved material claims: <list claim_ids with status unresolved>. Gate gate_10a_excellence_completeness requires no_unresolved_material_claims. Resolve the data gaps in Tier 3 before re-running.", "failure_category": "INCOMPLETE_OUTPUT"}`. This prevents writing a gate-blocking artifact. A declared failure is a correct output per CLAUDE.md Section 15.

### 3. Output Construction

Return a single JSON object conforming to `orch.tier5.excellence_section.v1`:

```json
{
  "schema_id": "orch.tier5.excellence_section.v1",
  "run_id": "<from task metadata>",
  "criterion": "Excellence",
  "sub_sections": [
    {
      "sub_section_id": "<from section_schema_registry.json>",
      "title": "<from section_schema_registry.json>",
      "content": "<evaluator-oriented prose, grounded in Tier 1-4>",
      "word_count": "<actual word count of content>"
    }
  ],
  "validation_status": {
    "overall_status": "confirmed|inferred|assumed|unresolved",
    "claim_statuses": [
      {
        "claim_id": "<unique>",
        "claim_summary": "<brief>",
        "status": "confirmed|inferred|assumed|unresolved",
        "source_ref": "<tier and path for confirmed/inferred>"
      }
    ]
  },
  "traceability_footer": {
    "primary_sources": [
      {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json"},
      {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json"},
      {"tier": 3, "source_path": "docs/tier3_project_instantiation/..."},
      {"tier": 4, "source_path": "docs/tier4_orchestration_state/..."}
    ],
    "no_unsupported_claims_declaration": true
  }
}
```

### 4. Conformance Stamping

- `schema_id`: set to "orch.tier5.excellence_section.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier5_deliverables/proposal_sections/` if not present.
- Step 5.2: Write `excellence_section.json` to `docs/tier5_deliverables/proposal_sections/excellence_section.json`.

## Constitutional Constraint Enforcement

*Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md Section 13.*

---

### Constraint 1: "Must verify budget gate passed before producing content"

**Decision point in execution logic:** Step 1.1 -- the budget gate check is the first action before any content processing.

**Exact failure condition:** `budget_gate_assessment.json` is absent, OR its `gate_pass_declaration` field does not equal `"pass"`.

**Enforcement mechanism:** Step 1.1 is an unconditional guard that fires before any drafting begins. If the guard condition triggers: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Budget gate has not passed (gate_pass_declaration is not 'pass'); CLAUDE.md Section 8.4 prohibits any Phase 8 activity before budget gate passes"). This guard cannot be bypassed, disabled, or deferred.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No output written.

**Hard failure confirmation:** Yes -- Phase 8 activity before budget gate is an absolute constitutional prohibition.

**CLAUDE.md Section 13 cross-reference:** Section 13.4 -- "Commencing any Phase 8 activity -- including preparatory drafting -- before the budget gate (Phase 7) has passed."

---

### Constraint 2: "Must not fabricate project facts not present in Tier 3"

**Decision point in execution logic:** Step 2.3.1 -- at the point project-specific content is sourced for each sub-section.

**Exact failure condition:** Any material claim in the drafted content names a partner, capability, objective, prior experience, budget figure, team size, or equipment item that does not have a corresponding entry in `docs/tier3_project_instantiation/`.

**Enforcement mechanism:** In Step 2.3.1, all project facts must be drawn exclusively from Tier 3. In Step 2.4, any project-fact claim that cannot be attributed to a specific Tier 3 file must be assigned status "Unresolved" (not "Confirmed" or "Inferred"). In Step 2.6, data gaps are documented rather than fabricated. If the skill were to produce content containing a project fact not present in Tier 3 and assign it Confirmed status: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Project fact <claim_summary> has no Tier 3 source; CLAUDE.md Section 13.3 prohibits fabricating project facts not present in Tier 3"). No output written.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No output written.

**Hard failure confirmation:** Yes -- fabricating project facts is a categorical prohibition.

**CLAUDE.md Section 13 cross-reference:** Section 13.3 -- "Inventing project facts -- partner names, capabilities, roles, objectives, prior experience, budget figures, team sizes, equipment -- not present in Tier 3."

---

### Constraint 3: "Must not use Grant Agreement Annex structure"

**Decision point in execution logic:** Step 1.8 -- the Grant Agreement Annex guard is applied during input validation.

**Exact failure condition:** The section schema source identified in `section_schema_registry.json` or any input structural reference identifies a Grant Agreement Annex, Model Grant Agreement, or "AGA" template as the governing structural schema for the Excellence section.

**Enforcement mechanism:** Step 1.8 is an unconditional guard. If the guard condition triggers: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Section schema source appears to be a Grant Agreement Annex; CLAUDE.md Section 13.1 prohibits using Grant Agreement Annex structure for proposal writing"). This guard is structurally identical to the one in `instrument-schema-normalization` and `evaluator-criteria-review`.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). Immediate halt. No output written.

**Hard failure confirmation:** Yes -- using Grant Agreement Annex as proposal schema is a categorical prohibition.

**CLAUDE.md Section 13 cross-reference:** Section 13.1 -- "Treating Grant Agreement Annex templates as the governing structural schema for proposal writing."

<!-- Constitutional constraint enforcement complete -->

## Failure Protocol

*All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.2: `section_schema_registry.json` absent or unreadable -> `failure_reason="section_schema_registry.json not found or empty; cannot determine Excellence section structure"`
- Step 1.3: `evaluator_expectation_registry.json` absent -> `failure_reason="evaluator_expectation_registry.json not found; cannot determine Excellence criterion scoring logic"`
- Step 1.4: `call_analysis_summary.json` absent or schema mismatch -> `failure_reason="call_analysis_summary.json not found or schema mismatch"`
- Step 1.5: `concept_refinement_summary.json` absent or schema mismatch -> `failure_reason="concept_refinement_summary.json not found or schema mismatch"`
- Step 1.6: `wp_structure.json` absent or schema mismatch -> `failure_reason="wp_structure.json not found or schema mismatch"`
- Step 1.7: Tier 3 project_brief/ or objectives.json absent -> `failure_reason="Tier 3 project data (project_brief/ or objectives.json) not found"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.4: `call_analysis_summary.json` has `schema_id` != "orch.phase1.call_analysis_summary.v1" -> `failure_reason="call_analysis_summary.json schema mismatch"`
- Step 1.5: `concept_refinement_summary.json` has incorrect schema_id -> `failure_reason="concept_refinement_summary.json schema mismatch"`
- Step 1.6: `wp_structure.json` has incorrect schema_id -> `failure_reason="wp_structure.json schema mismatch"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use CONSTITUTIONAL_HALT as appropriate.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Step 2.3: Any mandatory sub-section from `section_schema_registry.json` cannot be drafted (no content producible from available inputs) -> `failure_reason="Mandatory sub-section <sub_section_id> cannot be drafted; required input data is absent"`
- Step 3: Output JSON is malformed or missing required fields -> `failure_reason="Output artifact missing required fields per orch.tier5.excellence_section.v1"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Step 1.1 (budget gate check): `budget_gate_assessment.json` absent or `gate_pass_declaration` != "pass" -> `failure_reason="Budget gate has not passed; CLAUDE.md Section 8.4 prohibits any Phase 8 activity before budget gate passes"`
- Step 1.8 (Grant Agreement Annex guard): Schema source is a Grant Agreement Annex -> `failure_reason="Section schema source appears to be a Grant Agreement Annex; CLAUDE.md Section 13.1"`
- Constraint 2 (fabricated project facts): Project fact assigned Confirmed without Tier 3 source -> `failure_reason="Project fact <claim_summary> has no Tier 3 source; CLAUDE.md Section 13.3"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No `excellence_section.json` written.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
4. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md Section 15.

<!-- Failure protocol complete -->

## Schema Validation

*Validation of Output Construction against `artifact_schema_specification.yaml` for `excellence_section.json`.*

---

### Artifact: `excellence_section.json`

**Schema ID:** `orch.tier5.excellence_section.v1`

**Spec location:** `artifact_schema_specification.yaml` Section 2.1b (Tier 5 deliverables) -- `excellence_section` entry.

**Required fields per spec:**
- `schema_id` (string, const "orch.tier5.excellence_section.v1")
- `run_id` (string)
- `criterion` (string, const "Excellence")
- `sub_sections` (array) -- each entry has required `sub_section_id`, `title`, `content`, `word_count`
- `validation_status` (object, required)
- `traceability_footer` (object, required)
- `artifact_status` (optional, enum [valid, invalid]) -- runner-stamped; must be ABSENT at write time

**Output Construction (Step 3) verification:**
| Field | Set by skill? | Value source | Conformant? |
|-------|---------------|--------------|-------------|
| `schema_id` | Yes (Step 3, Step 4) | const "orch.tier5.excellence_section.v1" | Yes -- exact match |
| `run_id` | Yes (Step 3, Step 4) | invoking agent's run_id context parameter | Yes |
| `criterion` | Yes (Step 3) | const "Excellence" | Yes -- exact match |
| `sub_sections[]` | Yes (Step 2.3, Step 3) | each sub-section built with sub_section_id, title (from section_schema_registry), content (drafted from Tier 3/4), word_count (computed) | Yes -- all required item_schema fields present |
| `validation_status` | Yes (Step 2.4, Step 3) | overall_status and claim_statuses array | Yes -- status vocabulary matches CLAUDE.md Section 12.2 |
| `traceability_footer` | Yes (Step 2.5, Step 3) | primary_sources array and no_unsupported_claims_declaration boolean | Yes |
| `artifact_status` | ABSENT at write time (Step 4 explicit) | runner stamps post-gate | Yes -- correctly absent |

**reads_from compliance:** Skill reads from declared directories only. Compliant.

**writes_to compliance:** Skill writes only to `docs/tier5_deliverables/proposal_sections/excellence_section.json`. Declared in frontmatter. Compliant.

**Gaps identified:** None.

**Corrections applied:** None.

<!-- Schema validation complete -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour -- SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation -- must conform to that contract.
