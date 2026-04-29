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
- Base all reasoning ONLY on retrieved file content.

Return a SINGLE valid JSON object matching the output schema below.
Do not include ANY text before or after the JSON object — no prose, no
verification summaries, no markdown fencing. The response must begin with `{`
and end with `}`. Any non-JSON output causes a pipeline failure.

**Output size ceiling:** The total JSON response MUST be under 18,000 characters.
To stay within budget:
- B.2 sub-section content: concise evaluator-oriented paragraphs (3-5 sentences per sub-section). Do NOT reproduce full KPI tables or pathway detail in prose.
- DEC content: one compact paragraph per DEC category.
- Keep each sub_sections[].content field under 2,000 characters.
- Keep each claim_statuses[].source_ref under 120 characters (path + ID only).
- Limit claim_statuses to 8-10 aggregated entries; group related claims.
- Use compact primary_sources entries (path only).

**Deliverable identity constraint:** Use deliverable IDs only with their canonical title, type, and due month as defined in wp_structure.json.

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Read `budget_gate_assessment.json`. Check `gate_pass_declaration` equals `"pass"`. If absent or not `"pass"`: return `{"status": "failure", "failure_reason": "Budget gate has not passed", "failure_category": "CONSTITUTIONAL_HALT"}` and halt.
- Step 1.2: Read `section_schema_registry.json`. Identify Impact section entries. If empty or unreadable: return failure with `MISSING_INPUT`.
- Step 1.3: Read `evaluator_expectation_registry.json`. Identify the Impact criterion entry. If absent: return failure with `MISSING_INPUT`.
- Step 1.4: Read `impact_architecture.json`. If absent: return failure with `MISSING_INPUT`.
- Step 1.5: Read `wp_structure.json`. If absent: return failure with `MISSING_INPUT`.
- Step 1.6: Read `expected_outcomes.json` and `expected_impacts.json` from Tier 2B. If absent: return failure with `MISSING_INPUT`.
- Step 1.7: Read Tier 3 project data: `architecture_inputs/objectives.json`, `architecture_inputs/outcomes.json`, `architecture_inputs/impacts.json`. If absent: return failure with `MISSING_INPUT`.

### 2. Core Processing Logic

- Step 2.1: **Identify Impact sub-sections.** From `section_schema_registry.json`, extract the ordered list of mandatory sub-sections for the Impact section. Do not add sub-sections not present in the registry.

- Step 2.2: **Read evaluation framing.** From `evaluator_expectation_registry.json`, extract the Impact criterion's sub-criteria and scoring thresholds. Frame all sub-section content to address these sub-criteria directly.

- Step 2.3: **Map impact pathways.** From `impact_architecture.json`, extract all `impact_pathways`. For each pathway, verify it maps to at least one call expected impact. Record the pathway ID in `impact_pathway_refs`.

- Step 2.4: **Check call expected impact coverage.** For each expected impact in `expected_impacts.json`, verify at least one impact pathway maps to it. If an expected impact has no mapping: record the gap in `validation_status` with status "Unresolved". Do NOT fabricate a pathway that doesn't exist in Phase 5.

- Step 2.5: **Draft each sub-section.** For each Impact sub-section from Step 2.1:
  - Source impact content from `impact_architecture.json` (pathways, KPIs, targets).
  - Source DEC content from `impact_architecture.json` (dissemination_plan, exploitation_plan, sustainability_mechanism). If any DEC field is null: flag in `validation_status`.
  - Ground impact claims in concrete WP deliverables and tasks from `wp_structure.json`.
  - Address each Impact criterion sub-criterion from the evaluation form.
  - Do not reference unvalidated budget figures.
  - Use objective IDs, outcome names, KPI labels, and deliverable IDs exactly as stated in source artifacts. Do not rename components or repurpose deliverable IDs.

- Step 2.6: **Populate impact_pathway_refs.** Array of all pathway IDs from `impact_architecture.json` covered in the drafted content.

- Step 2.7: **Set dec_coverage.** Set each boolean (`dissemination_addressed`, `exploitation_addressed`, `communication_addressed`) to true only if the section substantively addresses that category.

- Step 2.8: **Build validation_status.** Produce 8-10 aggregated claim_status entries grouping related claims. Each entry: claim_id, claim_summary, status ("confirmed" or "inferred"), source_ref (path + ID, max 120 chars). Set `overall_status` to the weakest status across all claims.

- Step 2.9: **Build traceability_footer.** Populate `primary_sources` array. All `tier` values MUST be numeric integers (use 2 for Tier 2A/2B, 3 for Tier 3, 4 for Tier 4). Set `no_unsupported_claims_declaration` to `true` only if all claim_statuses are "confirmed" or "inferred" with non-null source_refs.

- Step 2.10: **Handle data gaps.** If Phase 5 data is incomplete for any element: OMIT the unsourceable claim. If the gap prevents drafting a mandatory sub-section entirely, return failure with `INCOMPLETE_OUTPUT`.

### 3. Output Schema

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
    "overall_status": "confirmed|inferred",
    "claim_statuses": [
      {
        "claim_id": "<unique>",
        "claim_summary": "<brief>",
        "status": "confirmed|inferred",
        "source_ref": "<tier and path, max 120 chars>"
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

- `schema_id`: const "orch.tier5.impact_section.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 4. Write Sequence

- Step 4.1: Create directory `docs/tier5_deliverables/proposal_sections/` if not present.
- Step 4.2: Write `impact_section.json` to `docs/tier5_deliverables/proposal_sections/impact_section.json`.
