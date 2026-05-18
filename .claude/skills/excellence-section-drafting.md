---
skill_id: excellence-section-drafting
purpose_summary: >
  Draft the Excellence section of the RIA/IA Part B. Produces
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
  - docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/canonical_reference_pack.json
writes_to:
  - docs/tier5_deliverables/proposal_sections/excellence_section.json
constitutional_constraints:
  - "Must verify budget gate passed before producing content"
  - "Must not fabricate project facts not present in Tier 3"
  - "Must not use Grant Agreement Annex structure"
---

## Input Access (TAPM Mode)

This skill executes in TAPM. Read declared inputs from disk using the Read tool.

**Declared inputs (read in order):**
1. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` -- verify `gate_pass_declaration` equals `"pass"` before any other action
2. `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` -- Excellence section identifiers, page limits
3. `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` -- Excellence criterion scoring logic
4. `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json`
5. `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json`
6. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`
7. `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json`
8. `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json`
9. `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json`
10. `docs/tier3_project_instantiation/` -- Glob then Read: project_brief/, consortium/, architecture_inputs/objectives.json
11. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/canonical_reference_pack.json` -- if present, use as authoritative source for canonical terms (objective titles, WP titles, deliverable IDs/titles/months, partner names)

Do not read files outside this set. Base all reasoning on retrieved file content only.

Return a SINGLE valid JSON object. No prose, no markdown fencing. Response must begin with `{` and end with `}`. Non-JSON output causes a pipeline failure.

**Output size ceiling:** Total JSON response MUST be under 20,000 characters.
- Sub-section content: 3-5 concise sentences each. Do not reproduce full objective tables or WP task lists.
- Each sub_sections[].content under 2,500 characters.
- Each claim_statuses[].source_ref under 120 characters.
- Limit claim_statuses to 15 aggregated entries.

## Execution Specification

### 1. Input Validation

- 1.1: Read `budget_gate_assessment.json`. If `gate_pass_declaration` is not `"pass"`: return `{"status": "failure", "failure_reason": "Budget gate has not passed", "failure_category": "CONSTITUTIONAL_HALT"}`.
- 1.2: Read `section_schema_registry.json`. Identify Excellence entries. If absent: failure `MISSING_INPUT`.
- 1.3: Read `evaluator_expectation_registry.json`. Identify Excellence criterion. If absent: failure `MISSING_INPUT`.
- 1.4-1.6: Read `call_analysis_summary.json`, `concept_refinement_summary.json`, `wp_structure.json`. If absent: failure `MISSING_INPUT`.
- 1.7: Read Tier 3. Confirm `project_brief/` and `architecture_inputs/objectives.json` present. If absent: failure `MISSING_INPUT`.
- 1.8: If any structural reference identifies a Grant Agreement Annex as schema source: failure `CONSTITUTIONAL_HALT`.

### 2. Core Processing

- 2.1: **Identify sub-sections** from `section_schema_registry.json`. Do not add sub-sections not in the registry.
- 2.2: **Read evaluation framing** from `evaluator_expectation_registry.json`. Frame content to address sub-criteria directly.
- 2.3: **Draft each sub-section:**
  - Source all project facts from Tier 3. Do not fabricate partner names, capabilities, or objectives.
  - Use refined concept vocabulary from `concept_refinement_summary.json`.
  - Ground methodology in WP tasks and deliverables from `wp_structure.json`.
  - Address each evaluator sub-criterion with evidence and project-specific detail.
  - If different WPs have different TRL targets per `objectives.json`, qualify TRL language accordingly.
  - SSH: if not specified in Tier 3, state proportionately that the project is primarily technical. Gender dimension: include only claims traceable to Tier 2A requirements and Tier 3/4 artifacts.
  - Do not reference unvalidated budget figures.
- 2.4: **Build validation_status.** Up to 15 aggregated claim_status entries. Each: claim_id, claim_summary, status ("confirmed"/"inferred"), source_ref (max 120 chars). `overall_status` = weakest. Omit claims that cannot be confirmed or inferred.
- 2.5: **Build traceability_footer.** All `tier` values MUST be numeric integers. Set `no_unsupported_claims_declaration` true only if all claims confirmed/inferred with non-null source_refs.
- 2.6: **Handle data gaps.** Omit unsourceable claims. If a mandatory sub-section cannot be drafted: failure `INCOMPLETE_OUTPUT`.

### 3. Canonical Copying Rules

- Use `canonical_reference_pack.json` when available.
- Copy objective titles, outcome titles, WP titles, deliverable IDs/titles/due months, milestone IDs/titles, partner legal names, and partner short names exactly from declared source artifacts.
- Do not rename, shorten, paraphrase, or reassign IDs.
- Do not infer ownership. If ownership or relationship is unclear, omit the claim.
- Do not cite a deliverable unless its ID, title, parent WP, and due month are present in the source artifact.
- Keep the output concise and schema-conformant.

### 3a. All-Objectives Enumeration Rule

When the drafted text uses any of the following phrases — "all objectives", "project objectives", "measurable objectives", "all project objectives", "each of the objectives" — or states a numeric objective count (e.g., "seven objectives", "eight measurable objectives"), the section MUST:

1. **Enumerate every objective ID** present in `canonical_reference_pack.json` → `objectives[]`. No objective may be omitted.
2. **Include all quantitative components** from each objective's `measurable_target` field (e.g., `≥40%`, `≥30%`, `≤5s`). Each numeric threshold with its comparator must appear verbatim in the section content.
3. **Match the stated count** to the actual number of objectives in the canonical pack. Do not write a numeric count (e.g., "eight objectives") unless it equals `len(canonical_reference_pack.objectives)`.

If the section cannot enumerate all objectives with their full measurable targets within the output size ceiling, do not use all-objectives or count language. Instead, reference objectives individually or by subset.

### 3b. MAESTRO Hard Guardrail for OBJ-7 (CC-01 Prevention)

For this MAESTRO run, OBJ-7 MUST NOT be summarized without its full quantified adoption target. Whenever drafting OBJ-7, "Open framework release and ecosystem contribution", include all of the following in the same OBJ-7 sentence or immediately adjacent clause:

- open-source release
- ≥500 GitHub stars within 6 months of release
- AI-on-demand platform contribution
- validation through ≥2 TEFs
- technology transfer through ≥3 EDIHs

Forbidden pattern: mentioning open-source release, AI-on-demand platform contribution, ≥2 TEFs, or ≥3 EDIHs while omitting ≥500 GitHub stars within 6 months of release. If space is tight, keep the full OBJ-7 bundle and compress another objective instead.

### 4. Output Schema

Return JSON conforming to `orch.tier5.excellence_section.v1`:

```json
{
  "schema_id": "orch.tier5.excellence_section.v1",
  "run_id": "<from task metadata>",
  "criterion": "Excellence",
  "sub_sections": [
    {
      "sub_section_id": "<from section_schema_registry.json>",
      "title": "<from section_schema_registry.json>",
      "content": "<evaluator-oriented prose>",
      "word_count": "<actual word count>"
    }
  ],
  "validation_status": {
    "overall_status": "confirmed|inferred",
    "claim_statuses": [
      {
        "claim_id": "<unique>",
        "claim_summary": "<brief>",
        "status": "confirmed|inferred",
        "source_ref": "<path + ID, max 120 chars>"
      }
    ]
  },
  "traceability_footer": {
    "primary_sources": [
      {"tier": 2, "source_path": "docs/tier2b_..."},
      {"tier": 3, "source_path": "docs/tier3_..."},
      {"tier": 4, "source_path": "docs/tier4_..."}
    ],
    "no_unsupported_claims_declaration": true
  }
}
```

- `schema_id`: const `"orch.tier5.excellence_section.v1"`
- `run_id`: from invoking agent's run_id
- `artifact_status`: MUST be absent at write time

### 5. Write Sequence

- Create `docs/tier5_deliverables/proposal_sections/` if not present.
- Write to `docs/tier5_deliverables/proposal_sections/excellence_section.json`.
