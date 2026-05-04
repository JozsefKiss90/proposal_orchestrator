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
  - docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/canonical_reference_pack.json
writes_to:
  - docs/tier5_deliverables/proposal_sections/impact_section.json
constitutional_constraints:
  - "Must verify budget gate passed before producing content"
  - "Must not fabricate impact coverage for unmapped call expected impacts"
  - "Must not use Grant Agreement Annex structure"
---

## Input Access (TAPM Mode)

This skill executes in TAPM. Read declared inputs from disk using the Read tool.

**Declared inputs (read in order):**
1. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` -- verify `gate_pass_declaration` equals `"pass"` before any other action
2. `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` -- Impact section identifiers, page limits
3. `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` -- Impact criterion scoring logic
4. `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` -- impact pathways, KPIs, DEC plans
5. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` -- deliverables for grounding impact claims
6. `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json`
7. `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json`
8. `docs/tier3_project_instantiation/` -- Glob then Read: architecture_inputs/outcomes.json, architecture_inputs/impacts.json, architecture_inputs/objectives.json, consortium/
9. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/canonical_reference_pack.json` -- if present, use as authoritative source for canonical terms (objective titles, WP titles, deliverable IDs/titles/months, partner names)

Do not read files outside this set. Base all reasoning on retrieved file content only.

Return a SINGLE valid JSON object. No prose, no markdown fencing. Response must begin with `{` and end with `}`. Non-JSON output causes a pipeline failure.

**Output size ceiling:** Total JSON response MUST be under 18,000 characters.
- Sub-section content: 3-5 concise sentences each. Do not reproduce full KPI tables or pathway detail.
- DEC content: one compact paragraph per category.
- Each sub_sections[].content under 2,000 characters.
- Each claim_statuses[].source_ref under 120 characters.
- Limit claim_statuses to 8-10 aggregated entries.

## Execution Specification

### 1. Input Validation

- 1.1: Read `budget_gate_assessment.json`. If `gate_pass_declaration` is not `"pass"`: return `{"status": "failure", "failure_reason": "Budget gate has not passed", "failure_category": "CONSTITUTIONAL_HALT"}`.
- 1.2: Read `section_schema_registry.json`. Identify Impact entries. If absent: failure `MISSING_INPUT`.
- 1.3: Read `evaluator_expectation_registry.json`. Identify Impact criterion. If absent: failure `MISSING_INPUT`.
- 1.4: Read `impact_architecture.json`. If absent: failure `MISSING_INPUT`.
- 1.5: Read `wp_structure.json`. If absent: failure `MISSING_INPUT`.
- 1.6: Read `expected_outcomes.json` and `expected_impacts.json`. If absent: failure `MISSING_INPUT`.
- 1.7: Read Tier 3: `objectives.json`, `outcomes.json`, `impacts.json`. If absent: failure `MISSING_INPUT`.

### 2. Core Processing

- 2.1: **Identify sub-sections** from `section_schema_registry.json`. Do not add sub-sections not in the registry.
- 2.2: **Read evaluation framing** from `evaluator_expectation_registry.json`. Frame content to address sub-criteria directly.
- 2.3: **Map impact pathways** from `impact_architecture.json`. For each pathway, verify it maps to at least one call expected impact.
- 2.4: **Check call expected impact coverage.** For each expected impact in `expected_impacts.json`, verify at least one pathway maps to it. If an expected impact has no mapping: record gap in `validation_status`. Do not fabricate a pathway.
- 2.5: **Draft each sub-section:**
  - Source impact content from `impact_architecture.json` (pathways, KPIs, targets).
  - Source DEC content from `impact_architecture.json` (dissemination_plan, exploitation_plan, sustainability_mechanism). If any DEC field is null: flag in `validation_status`.
  - Ground impact claims in concrete WP deliverables from `wp_structure.json`.
  - Address each Impact criterion sub-criterion from the evaluation form.
  - Do not reference unvalidated budget figures.
  - **Measurable Target Consistency Rule (CC-06 Prevention):**
    When drafting Impact content, if an objective ID (e.g. OBJ-1, OBJ-7) is
    explicitly referenced, OR if an outcome ID is referenced that is linked to an
    objective, THEN: if ANY quantitative component from that objective's
    measurable_target is used, EVERY quantitative component from that same
    measurable_target MUST appear together in the same sentence or immediately
    adjacent clause. Partial reproduction is strictly forbidden.
    Example: if OBJ-7.measurable_target contains ≥500, ≥2, and ≥3, the drafted
    text must either include all three values (≥500, ≥2, ≥3) together, or omit
    all objective-level numeric target components and use qualitative phrasing.
    Including ≥2 and ≥3 while omitting ≥500 is a violation.
    If full reproduction would make the sentence too long or unnatural, DO NOT
    include any measurable_target metrics at all — use qualitative phrasing instead.
    Activation: this rule triggers ONLY on explicit objective ID reference or
    linked outcome ID reference. Do not infer activation from deliverable mentions,
    partner names, WP names, or domain words.
- 2.6: **Populate impact_pathway_refs** -- array of pathway IDs covered in drafted content.
- 2.7: **Set dec_coverage** -- each boolean true only if substantively addressed.
- 2.8: **Build validation_status.** 8-10 aggregated claim_status entries. Each: claim_id, claim_summary, status ("confirmed"/"inferred"), source_ref (max 120 chars). `overall_status` = weakest.
- 2.9: **Build traceability_footer.** All `tier` values MUST be numeric integers. Set `no_unsupported_claims_declaration` true only if all claims confirmed/inferred with non-null source_refs.
- 2.10: **Handle data gaps.** Omit unsourceable claims. If a mandatory sub-section cannot be drafted: failure `INCOMPLETE_OUTPUT`.
- 2.11: **Tier 1 Regulatory Claim Restriction.**
  The Impact section MUST NOT introduce regulatory or policy claims that require
  Tier 1 normative sources unless those sources are explicitly read. This includes
  (but is not limited to): Plan S compliance statements; specific open access
  licenses (e.g. CC-BY); mandatory publication timelines (e.g. "within six months");
  legal obligations derived from Horizon Europe Grant Agreement or Annexes.
  Allowed: generic statements such as "open access dissemination" or "alignment
  with EU open science practices". If such regulatory claims are not present in
  Tier 2A, Tier 2B, or Tier 3 inputs, they MUST be omitted.

### 3. Canonical Copying Rules

- Use `canonical_reference_pack.json` when available.
- Copy objective titles, outcome titles, WP titles, deliverable IDs/titles/due months, milestone IDs/titles, partner legal names, and partner short names exactly from declared source artifacts.
- Do not rename, shorten, paraphrase, or reassign IDs.
- Do not infer ownership. If ownership or relationship is unclear, omit the claim.
- Do not cite a deliverable unless its ID, title, parent WP, and due month are present in the source artifact.
- Keep the output concise and schema-conformant.

### 4. Output Schema

Return JSON conforming to `orch.tier5.impact_section.v1`:

```json
{
  "schema_id": "orch.tier5.impact_section.v1",
  "run_id": "<from task metadata>",
  "criterion": "Impact",
  "sub_sections": [
    {
      "sub_section_id": "<from section_schema_registry.json>",
      "title": "<from section_schema_registry.json>",
      "content": "<evaluator-oriented prose>",
      "word_count": "<actual word count>"
    }
  ],
  "impact_pathway_refs": ["pathway_1", "pathway_2"],
  "dec_coverage": {
    "dissemination_addressed": true,
    "exploitation_addressed": true,
    "communication_addressed": true
  },
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
      {"tier": 4, "source_path": "docs/tier4_.../impact_architecture.json"},
      {"tier": 3, "source_path": "docs/tier3_..."},
      {"tier": 2, "source_path": "docs/tier2b_.../expected_impacts.json"}
    ],
    "no_unsupported_claims_declaration": true
  }
}
```

- `schema_id`: const `"orch.tier5.impact_section.v1"`
- `run_id`: from invoking agent's run_id
- `artifact_status`: MUST be absent at write time

### 5. Write Sequence

- Create `docs/tier5_deliverables/proposal_sections/` if not present.
- Write to `docs/tier5_deliverables/proposal_sections/impact_section.json`.
