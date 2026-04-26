---
skill_id: impact-section-drafting
purpose_summary: >
  Draft the Impact section of the RIA/IA Part B from Phase 5 impact architecture,
  DEC plans, and Tier 2B expected impacts. Produces impact_section.json conforming
  to orch.tier5.impact_section.v1.
used_by_agents:
  - impact_writer
reads_from:
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier2b_topic_and_call_sources/extracted/
  - docs/tier3_project_instantiation/
  - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
writes_to:
  - docs/tier5_deliverables/proposal_sections/impact_section.json
constitutional_constraints:
  - "Must verify budget gate passed before producing content"
  - "Must not fabricate impact coverage for unmapped call expected impacts"
  - "Must not use Grant Agreement Annex structure"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool.

**Declared input files to read (in order):**
1. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` -- MUST be read first; verify `gate_pass_declaration` equals `"pass"` before any other action
2. `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` -- section identifiers, page limits for Impact section
3. `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` -- Impact criterion scoring logic and sub-criteria
4. `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` -- impact pathways, KPIs, DEC plans, sustainability mechanisms
5. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` -- WP deliverables for grounding impact claims in project activities
6. `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` -- call expected outcomes
7. `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` -- call expected impacts
8. `docs/tier3_project_instantiation/` -- project data (use Glob to discover, then Read relevant files: architecture_inputs/outcomes.json, architecture_inputs/impacts.json, consortium/)

**Boundary constraints:**
- Do not read files outside the declared input set.
- Do not assume implicit context or reconstruct inputs from memory.
- Read each required file explicitly before using it.
- Base all reasoning ONLY on retrieved file content.
- Do not use generic Horizon Europe knowledge as a substitute for reading Tier 1-4 sources.

Return a SINGLE valid JSON object matching the output schema below.
Do not include ANY text before or after the JSON object — no prose, no
verification summaries, no markdown fencing. The response must begin with `{`
and end with `}`. Any non-JSON output causes a pipeline failure.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | Budget gate assessment | `gate_pass_declaration` | `orch.phase7.budget_gate_assessment.v1` | Verify budget gate passed before any drafting; CLAUDE.md Section 8.4 absolute prerequisite |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | Section schema registry | Impact section entries (section identifiers, page limits, mandatory sub-sections) | `orch.tier2a.section_schema_registry.v1` | Structural authority for Impact section sub-sections and page limits |
| `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` | Evaluator expectations | Impact criterion entry (criterion_id, sub-criteria, scoring thresholds, grade descriptors) | `orch.tier2a.evaluator_expectation_registry.v1` | Evaluation framing: what evaluators look for in Impact section |
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | Impact architecture | impact_pathways, kpis, dissemination_plan, exploitation_plan, sustainability_mechanism | `orch.phase5.impact_architecture.v1` | Primary source for impact pathway narratives, KPI definitions, and DEC plan content |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | WP structure | WP deliverables, tasks | `orch.phase3.wp_structure.v1` | Grounds impact claims in concrete project deliverables and activities |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | Call expected outcomes | Expected outcome entries with source references | N/A -- Tier 2B extracted | Call-specific expected outcomes that the Impact section must address |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Call expected impacts | Expected impact entries with source references | N/A -- Tier 2B extracted | Call-specific expected impacts that impact pathways must map to |
| `docs/tier3_project_instantiation/` | Project data (architecture_inputs/outcomes.json, impacts.json, consortium/) | Project outcomes, impacts, consortium capabilities | N/A -- Tier 3 root directory | Project-specific impact claims and consortium dissemination capacity |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier5_deliverables/proposal_sections/impact_section.json` | Impact section draft | `orch.tier5.impact_section.v1` | schema_id, run_id, criterion (const "Impact"), sub_sections (array: sub_section_id, title, content, word_count), impact_pathway_refs (array of pathway IDs), dec_coverage (object: dissemination_addressed, exploitation_addressed, communication_addressed), validation_status, traceability_footer | Yes | sub_sections: drafted from Phase 5 impact architecture and Tier 3 data, framed against Tier 2A Impact criterion scoring logic; impact_pathway_refs: all pathway IDs from impact_architecture.json; dec_coverage: booleans derived from DEC plan presence in impact_architecture.json |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier5_deliverables/proposal_sections/impact_section.json` | Yes -- artifact_id: a_t5_impact_section | n08b_impact_drafting |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Read `budget_gate_assessment.json`. Check `gate_pass_declaration` equals `"pass"`. If absent or not `"pass"`: return `{"status": "failure", "failure_reason": "Budget gate has not passed (gate_pass_declaration is not 'pass'); CLAUDE.md Section 8.4 prohibits any Phase 8 activity before budget gate passes", "failure_category": "CONSTITUTIONAL_HALT"}` and halt.
- Step 1.2: Read `section_schema_registry.json`. Identify Impact section entries. If empty or unreadable: return failure with `MISSING_INPUT`.
- Step 1.3: Read `evaluator_expectation_registry.json`. Identify the Impact criterion entry. If absent: return failure with `MISSING_INPUT`.
- Step 1.4: Read `impact_architecture.json`. Check schema_id. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.5: Read `wp_structure.json`. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.6: Read `expected_outcomes.json` and `expected_impacts.json` from Tier 2B. If absent: return failure with `MISSING_INPUT`.
- Step 1.7: Read Tier 3 project data: `architecture_inputs/outcomes.json`, `architecture_inputs/impacts.json`. If absent: return failure with `MISSING_INPUT`.
- Step 1.8: **Grant Agreement Annex guard** -- inspect the section schema source. If any structural reference identifies a Grant Agreement Annex, Model Grant Agreement Annex, or "AGA" template: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Section schema source appears to be a Grant Agreement Annex; CLAUDE.md Section 13.1") and halt.

### 2. Core Processing Logic

- Step 2.1: **Identify Impact sub-sections.** From `section_schema_registry.json`, extract the ordered list of mandatory sub-sections for the Impact section. For RIA/IA, these typically cover:
  - Project results and expected impacts
  - Measures to maximise impact (dissemination, exploitation, communication)
  - Summary of impact pathways

  The exact sub-section list is governed by the application form template via the section schema registry. Do not add sub-sections not present in the registry.

- Step 2.2: **Read evaluation framing.** From `evaluator_expectation_registry.json`, extract the Impact criterion's sub-criteria, scoring thresholds, and grade descriptors. Frame all sub-section content to address these sub-criteria directly.

- Step 2.3: **Map impact pathways.** From `impact_architecture.json`, extract all `impact_pathways`. For each pathway:
  - Verify it maps to at least one call expected impact from `expected_impacts.json`.
  - Identify the project output(s) and WP deliverable(s) that produce the pathway's starting point.
  - Record the pathway ID in `impact_pathway_refs`.

- Step 2.4: **Check call expected impact coverage.** For each expected impact in `expected_impacts.json`:
  - Verify at least one impact pathway in `impact_architecture.json` maps to it.
  - If an expected impact has no mapping: this is a coverage gap. Do NOT fabricate a pathway that doesn't exist in Phase 5. Record the gap in `validation_status` with status "Unresolved" and document it explicitly in the section content (CLAUDE.md Section 13.2).

- Step 2.5: **Draft each sub-section.** For each Impact sub-section identified in Step 2.1:

  - Step 2.5.1: **Source impact content from Phase 5.** Draw impact pathway narratives, KPIs, target values, and baseline data from `impact_architecture.json`. Do not invent impact claims not present in Phase 5 output.

  - Step 2.5.2: **Source DEC content from Phase 5.** Draw dissemination, exploitation, and communication plan content from `impact_architecture.json` fields (`dissemination_plan`, `exploitation_plan`, `sustainability_mechanism`). If any DEC field is null or absent in `impact_architecture.json`: flag in `validation_status` as Unresolved.

  - Step 2.5.3: **Ground impact claims in project activities.** Reference concrete WP deliverables and tasks from `wp_structure.json` when describing how impacts will be achieved. Every impact claim must be traceable to a project mechanism (CLAUDE.md Section 7, Phase 5 gate condition).

  - Step 2.5.4: **Apply evaluator sub-criteria.** Address each Impact criterion sub-criterion from the evaluation form. Apply specificity tests.

  - Step 2.5.5: **Do not reference unvalidated budget figures.** (CLAUDE.md Section 8.3)

- Step 2.6: **Populate impact_pathway_refs.** Array of all pathway IDs from `impact_architecture.json` that are covered in the drafted section content.

- Step 2.7: **Set dec_coverage.** From the drafted content and `impact_architecture.json`:
  - `dissemination_addressed`: true if the section addresses dissemination measures with specificity.
  - `exploitation_addressed`: true if the section addresses exploitation measures with specificity.
  - `communication_addressed`: true if the section addresses communication measures with specificity.
  Set to false for any category not substantively addressed.

- Step 2.8: **Build validation_status.** Per-claim Confirmed/Inferred classification. **GATE-CRITICAL: The output MUST NOT contain any claim_status with status = "assumed" or "unresolved".** If a claim cannot be confirmed or inferred with a valid source_ref chain, OMIT the claim from the drafted content entirely. The gate predicate `no_unresolved_material_claims` checks `validation_status.overall_status`; any value other than "confirmed" or "inferred" causes gate failure. Set `overall_status` to the weakest status across all claims — must be "confirmed" or "inferred". Every claim_status MUST have a non-null source_ref. **Output size constraint for `source_ref`:** Use concise references only — file path plus field/ID (e.g. `"Tier 4: impact_architecture.json PATH-EI-01"` or `"Tier 2B: expected_impacts.json EI-02"`). Maximum 120 characters per `source_ref`. Do NOT include prose explanations or inference chains in `source_ref`. Limit `claim_statuses` to the 15 most material claims; group minor claims from the same source into aggregated entries.

- Step 2.9: **Build traceability_footer.** Populate `primary_sources` array. **GATE-CRITICAL tier value format:** All `primary_sources[].tier` values MUST be numeric integers, not strings:
  - Tier 2A sources (docs/tier2a_instrument_schemas/...): use `"tier": 2`
  - Tier 2B sources (docs/tier2b_topic_and_call_sources/...): use `"tier": 2`
  - Tier 3 sources: use `"tier": 3`
  - Tier 4 sources: use `"tier": 4`
  Do NOT output string tier values such as "2a", "2b", "tier2b", or "Tier 2B". The sub-tier distinction (2A vs 2B) is preserved through the `source_path` field — Tier 2B sources are identifiable by their path prefix `docs/tier2b_topic_and_call_sources/extracted/...`.
  Set `no_unsupported_claims_declaration` to `true` only if ALL claim_statuses are "confirmed" or "inferred" with non-null source_refs.

- Step 2.10: **Handle data gaps.** If Phase 5 impact architecture is incomplete for any Impact sub-section element: OMIT the unsourceable claim from the drafted content. Do not include it with "assumed" or "unresolved" status. Do not fabricate content (CLAUDE.md Section 11.5, Section 13.8). If the gap prevents drafting a mandatory sub-section entirely, return failure with `INCOMPLETE_OUTPUT`.

- Step 2.11: **Gate-readiness check.** After building `validation_status`, verify:
  - No claim_status has status "assumed" or "unresolved"
  - All claim_statuses have non-null source_ref
  - overall_status is "confirmed" or "inferred"
  - All primary_sources[].tier values are numeric integers (not strings)
  - no_unsupported_claims_declaration is true
  If any condition fails: do NOT produce the output artifact. Instead, return `{"status": "failure", "failure_reason": "Impact section has non-gate-ready claims or schema issues: <list specifics>.", "failure_category": "INCOMPLETE_OUTPUT"}`. This prevents writing a gate-blocking artifact.

### 3. Output Construction

Return a single JSON object conforming to `orch.tier5.impact_section.v1`:

```json
{
  "schema_id": "orch.tier5.impact_section.v1",
  "run_id": "<from task metadata>",
  "criterion": "Impact",
  "sub_sections": [
    {
      "sub_section_id": "<from section_schema_registry.json>",
      "title": "<from section_schema_registry.json>",
      "content": "<evaluator-oriented prose, grounded in Tier 1-4>",
      "word_count": "<actual word count of content>"
    }
  ],
  "impact_pathway_refs": ["pathway_1", "pathway_2"],
  "dec_coverage": {
    "dissemination_addressed": true,
    "exploitation_addressed": true,
    "communication_addressed": true
  },
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
      {"tier": 4, "source_path": "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json"},
      {"tier": 3, "source_path": "docs/tier3_project_instantiation/..."},
      {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json"},
      {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json"},
      {"tier": 2, "source_path": "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json"}
    ],
    "no_unsupported_claims_declaration": true
  }
}
```

### 4. Conformance Stamping

- `schema_id`: set to "orch.tier5.impact_section.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier5_deliverables/proposal_sections/` if not present.
- Step 5.2: Write `impact_section.json` to `docs/tier5_deliverables/proposal_sections/impact_section.json`.

## Constitutional Constraint Enforcement

*Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md Section 13.*

---

### Constraint 1: "Must verify budget gate passed before producing content"

**Decision point in execution logic:** Step 1.1 -- the budget gate check is the first action before any content processing.

**Exact failure condition:** `budget_gate_assessment.json` is absent, OR its `gate_pass_declaration` field does not equal `"pass"`.

**Enforcement mechanism:** Step 1.1 is an unconditional guard. If triggered: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Budget gate has not passed; CLAUDE.md Section 8.4 prohibits any Phase 8 activity before budget gate passes"). Cannot be bypassed.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No output written.

**Hard failure confirmation:** Yes -- absolute prohibition.

**CLAUDE.md Section 13 cross-reference:** Section 13.4.

---

### Constraint 2: "Must not fabricate impact coverage for unmapped call expected impacts"

**Decision point in execution logic:** Step 2.4 -- at the point call expected impact coverage is verified against Phase 5 impact pathways.

**Exact failure condition:** The drafted section asserts that a call expected impact is addressed by the project, but no impact pathway in `impact_architecture.json` maps to that expected impact.

**Enforcement mechanism:** In Step 2.4, each call expected impact is checked against `impact_architecture.json` pathways. If no pathway maps to an expected impact, the gap must be recorded in `validation_status` with status "Unresolved" and documented in the section content as an explicit gap. Fabricating a pathway that does not exist in Phase 5 output is prohibited. If a claim asserting coverage of an unmapped expected impact is assigned Confirmed or Inferred status: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Impact coverage for expected impact <impact_id> fabricated; no pathway in impact_architecture.json maps to this expected impact; CLAUDE.md Section 13.2 prohibits inventing call constraints/coverage").

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No output written.

**Hard failure confirmation:** Yes -- fabricating impact coverage is a categorical prohibition.

**CLAUDE.md Section 13 cross-reference:** Section 13.2 -- "Inventing call constraints, scope requirements, expected outcomes, or expected impacts not present in Tier 2B source documents." Also Section 10.5 -- impact claims must be traceable.

---

### Constraint 3: "Must not use Grant Agreement Annex structure"

**Decision point in execution logic:** Step 1.8 -- Grant Agreement Annex guard during input validation.

**Exact failure condition:** Section schema source identifies a Grant Agreement Annex as governing structural schema.

**Enforcement mechanism:** Unconditional guard. Return CONSTITUTIONAL_HALT on trigger.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). Immediate halt.

**Hard failure confirmation:** Yes.

**CLAUDE.md Section 13 cross-reference:** Section 13.1.

<!-- Constitutional constraint enforcement complete -->

## Failure Protocol

*All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.2: `section_schema_registry.json` absent or unreadable -> `failure_reason="section_schema_registry.json not found; cannot determine Impact section structure"`
- Step 1.3: `evaluator_expectation_registry.json` absent -> `failure_reason="evaluator_expectation_registry.json not found; cannot determine Impact criterion scoring logic"`
- Step 1.4: `impact_architecture.json` absent or schema mismatch -> `failure_reason="impact_architecture.json not found or schema mismatch"`
- Step 1.5: `wp_structure.json` absent or schema mismatch -> `failure_reason="wp_structure.json not found or schema mismatch"`
- Step 1.6: `expected_outcomes.json` or `expected_impacts.json` absent -> `failure_reason="Tier 2B expected outcomes/impacts files not found"`
- Step 1.7: Tier 3 outcomes.json or impacts.json absent -> `failure_reason="Tier 3 project outcomes/impacts data not found"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.4: `impact_architecture.json` has incorrect schema_id -> `failure_reason="impact_architecture.json schema mismatch"`
- Step 1.5: `wp_structure.json` has incorrect schema_id -> `failure_reason="wp_structure.json schema mismatch"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined; all constitutional constraint failures use CONSTITUTIONAL_HALT.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Step 2.5: Any mandatory sub-section cannot be drafted -> `failure_reason="Mandatory sub-section <sub_section_id> cannot be drafted"`
- Step 3: Output JSON missing required fields -> `failure_reason="Output artifact missing required fields per orch.tier5.impact_section.v1"`
- Step 2.6: `impact_pathway_refs` array is empty when `impact_architecture.json` has pathways -> `failure_reason="impact_pathway_refs is empty despite pathways existing in impact_architecture.json"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Step 1.1: Budget gate not passed -> `failure_reason="Budget gate has not passed; CLAUDE.md Section 8.4"`
- Step 1.8: Grant Agreement Annex guard -> `failure_reason="Section schema source is a Grant Agreement Annex; CLAUDE.md Section 13.1"`
- Constraint 2: Fabricated impact coverage -> `failure_reason="Impact coverage for expected impact <impact_id> fabricated; CLAUDE.md Section 13.2"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No `impact_section.json` written.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. The invoking agent receives the `SkillResult` and is responsible for logging the failure.
4. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md Section 15.

<!-- Failure protocol complete -->

## Schema Validation

*Validation of Output Construction against `artifact_schema_specification.yaml` for `impact_section.json`.*

---

### Artifact: `impact_section.json`

**Schema ID:** `orch.tier5.impact_section.v1`

**Spec location:** `artifact_schema_specification.yaml` Section 2.1c (Tier 5 deliverables) -- `impact_section` entry.

**Required fields per spec:**
- `schema_id` (string, const "orch.tier5.impact_section.v1")
- `run_id` (string)
- `criterion` (string, const "Impact")
- `sub_sections` (array) -- each: sub_section_id, title, content, word_count
- `impact_pathway_refs` (array of strings)
- `dec_coverage` (object) -- dissemination_addressed, exploitation_addressed, communication_addressed (all boolean, required)
- `validation_status` (object, required)
- `traceability_footer` (object, required)
- `artifact_status` (optional, enum [valid, invalid]) -- runner-stamped; must be ABSENT at write time

**Output Construction (Step 3) verification:**
| Field | Set by skill? | Value source | Conformant? |
|-------|---------------|--------------|-------------|
| `schema_id` | Yes (Step 3, Step 4) | const "orch.tier5.impact_section.v1" | Yes |
| `run_id` | Yes (Step 3, Step 4) | invoking agent's run_id | Yes |
| `criterion` | Yes (Step 3) | const "Impact" | Yes |
| `sub_sections[]` | Yes (Step 2.5, Step 3) | sub_section_id, title from section_schema_registry; content from Phase 5/Tier 3; word_count computed | Yes |
| `impact_pathway_refs` | Yes (Step 2.6) | pathway IDs from impact_architecture.json | Yes |
| `dec_coverage` | Yes (Step 2.7) | booleans from content and impact_architecture.json | Yes -- all three fields present |
| `validation_status` | Yes (Step 2.8) | per-claim classification | Yes |
| `traceability_footer` | Yes (Step 2.9) | primary_sources array | Yes |
| `artifact_status` | ABSENT at write time (Step 4) | runner stamps post-gate | Yes |

**reads_from compliance:** All declared. Compliant.

**writes_to compliance:** Single path declared. Compliant.

**Gaps identified:** None.

<!-- Schema validation complete -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour -- SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation -- must conform to that contract.
