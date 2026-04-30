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

**Deliverable identity constraint:** Use deliverable IDs only with their canonical title, type, and due month as defined in wp_structure.json. See Canonical Consistency Rules (CCR-2) below.

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
  - Use objective IDs, outcome names, KPI labels, and deliverable IDs exactly as stated in source artifacts. Do not rename components or repurpose deliverable IDs. Follow all Canonical Consistency Rules (CCR-1 through CCR-4) below.

- Step 2.6: **Build measurable_target coverage map.** For every objective referenced anywhere in the drafted sub-sections:
  1. Retrieve its `measurable_target` from `architecture_inputs/objectives.json`.
  2. Decompose it into constituent components (each distinct metric clause, target dimension, or quantitative value).
  3. For each component, identify its representation in the Impact content — via a pathway, KPI, DEC mechanism, or validation/deployment channel.
  4. If any component lacks representation: extend the relevant sub-section content to include it before proceeding.
  5. Do NOT mark the section as complete until every component of every referenced objective's `measurable_target` is mapped.

- Step 2.7: **Populate impact_pathway_refs.** Array of all pathway IDs from `impact_architecture.json` covered in the drafted content.

- Step 2.8: **Set dec_coverage.** Set each boolean (`dissemination_addressed`, `exploitation_addressed`, `communication_addressed`) to true only if the section substantively addresses that category.

- Step 2.9: **Build validation_status.** Produce 8-10 aggregated claim_status entries grouping related claims. Each entry: claim_id, claim_summary, status ("confirmed" or "inferred"), source_ref (path + ID, max 120 chars). Set `overall_status` to the weakest status across all claims.

- Step 2.10: **Build traceability_footer.** Populate `primary_sources` array. All `tier` values MUST be numeric integers (use 2 for Tier 2A/2B, 3 for Tier 3, 4 for Tier 4). Set `no_unsupported_claims_declaration` to `true` only if all claim_statuses are "confirmed" or "inferred" with non-null source_refs.

- Step 2.11: **Handle data gaps.** If Phase 5 data is incomplete for any element: OMIT the unsourceable claim. If the gap prevents drafting a mandatory sub-section entirely, return failure with `INCOMPLETE_OUTPUT`.

- Step 2.12: **Self-Check: KPI Completeness.** Before producing the final JSON output, verify:
  1. No objective referenced in the Impact section has partial `measurable_target` coverage — every component of every referenced objective's target is present in the content.
  2. No metric component that would be present in the Excellence section is absent from the Impact section — there must be no cross-section KPI inconsistency.
  3. For each referenced objective, count the metric clauses in `measurable_target` and count their representations in the Impact content. If any count mismatches: revise the relevant sub-section content to restore full coverage before outputting.
  If any violation is detected: revise the Impact sub-section content to include the missing components. Do NOT emit the final JSON until all measurable_target components are represented.

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

## Canonical Consistency Rules (GATE-CRITICAL — Cross-Section Enforcement)

These rules are enforced deterministically by gate_10d_cross_section_consistency. Violations cause gate failure. All four rules apply to every `sub_sections[].content` field in the output.

### Rule CCR-1: Canonical Objective Title Preservation

When referencing any objective from `architecture_inputs/objectives.json`, the objective `title` field MUST be reproduced verbatim in the drafted content.

**Prohibited:**
- Abbreviating the title (e.g., dropping words)
- Paraphrasing the title (e.g., substituting synonyms)
- Truncating the title (e.g., using only the first part)
- Extending the title (e.g., appending additional words)
- Substituting synonyms for any word in the title

**Permitted shorthand:** After the full canonical title has been introduced once in the section, subsequent references MAY use the objective ID only (e.g., "OBJ-1"). However, the full canonical title must appear at least once in the section content.

**Enforcement:** gate_10d checks that every objective `title` from Tier 3 that contains a component keyword (engine, layer, architecture, protocol, framework, system) appears verbatim in the section content when that objective is referenced.

### Rule CCR-2: Deliverable ID Semantic Consistency

A deliverable ID (e.g., "D4-01") represents a single semantic artifact as defined in `wp_structure.json`. When referencing a deliverable ID in drafted content:

**Required:**
- The deliverable's purpose must match its canonical `title` from `wp_structure.json`
- The deliverable's timing must match its canonical `due_month` from `wp_structure.json`

**Prohibited:**
- Assigning a deliverable ID a different meaning or purpose than its canonical definition
- Changing the temporal context of a deliverable (e.g., describing a M18 deliverable as a M48 output)
- Using a deliverable ID to refer to a KPI or impact activity instead of its canonical deliverable artifact

**When a deliverable enables a downstream activity** (e.g., a protocol specification deliverable enables a standardisation submission): explicitly frame the relationship as "deliverable D4-01 (<canonical title>) enables/supports <downstream activity>". Do NOT describe the downstream activity AS the deliverable.

### Rule CCR-3: Objective Metric Completeness

When an objective from `architecture_inputs/objectives.json` is referenced in the drafted content and its `measurable_target` contains quantitative values, ALL quantitative targets MUST be preserved.

**Required:**
- If `measurable_target` contains multiple metrics joined by "AND" (e.g., "≥20% X AND ≥15% Y"), ALL metrics must appear in the content when that objective's targets are discussed
- Numeric values and their comparators (≥, ≤, >, <) must be preserved exactly

**Prohibited:**
- Selecting only a subset of metrics from a multi-metric target
- Silently omitting any quantitative target value
- Rounding or approximating target values

**Permitted reformatting:** Metrics may be presented in prose form, bullet lists, or KPI tables — but all values must be present regardless of format.

**Impact pathway metric completeness:** When an Impact pathway, KPI, target group, demonstrator claim, deliverable claim, or exploitation/dissemination claim references or derives from an objective with a multi-clause measurable_target, copy every quantitative metric clause from that objective's measurable_target into the Impact text unless the objective is mentioned only as an ID without describing its target. Do not reduce A AND B targets to only A. If space is limited, compress prose but retain all numeric values, comparators, units, and target dimensions. For multi-metric objectives, prefer a single compact sentence containing all metric clauses joined by "AND".

**Operational check:** Before writing the Impact JSON, check every objective ID or objective-derived KPI used in the Impact content. For each referenced objective, ensure all quantitative clauses from its measurable_target are present in the relevant Impact sentence or KPI sentence.

### Rule CCR-4: Canonical Component / System Naming

All named components, systems, layers, and architectural elements referenced in drafted content MUST use their canonical names exactly as defined in Tier 3 artifacts (`architecture_inputs/objectives.json` titles, `architecture_inputs/outcomes.json` titles).

**Prohibited:**
- Truncating a canonical name (e.g., dropping "External" from "External Tool and API Orchestration Layer")
- Extending a canonical name (e.g., appending "and Reasoning" to a defined title)
- Substituting synonyms for any word (e.g., "capability" instead of "Layer", "module" instead of "Engine")
- Using a lowercased or differently-cased variant when the canonical name has specific casing

**Permitted aliasing:** A short alias MAY be used ONLY if:
1. The full canonical name is introduced first in the same sub-section
2. The alias is explicitly defined at introduction (e.g., "the Neuro-symbolic Planning Engine (hereafter NPE)")

**Enforcement:** gate_10d extracts canonical component names from Tier 3 objective titles containing component keywords (engine, layer, architecture, protocol, framework, system). If the name stem appears in section content but the full canonical name does not, gate_10d flags a terminology inconsistency.

### Rule CCR-5: KPI Preservation Invariant (Cross-Section Consistency)

For every objective referenced in this section:

- Retrieve its `measurable_target` from `architecture_inputs/objectives.json`
- Decompose it into its constituent components (each distinct metric, dimension, or target clause)
- Ensure that ALL components are represented somewhere in the Impact section

Representation rules:
- Components may be expressed via:
  - impact pathways
  - KPIs or target metrics
  - DEC measures (dissemination, exploitation, communication mechanisms)
  - validation or deployment mechanisms
- Exact wording is NOT required — functional presence IS required
- A component is "functionally present" if its metric dimension, target value, and comparator can be identified in the Impact content

STRICT PROHIBITION:
- Do NOT omit any measurable_target component for any referenced objective
- Do NOT partially represent multi-component objectives (e.g., preserving metric A but dropping metric B)
- If Excellence preserves all components of a measurable_target, Impact MUST also preserve all components — no cross-section metric loss is permitted

### Additional Conventions

Use partner `short_name` or full `legal_name` from `consortium/partners.json` — do not truncate legal names by dropping suffixes (AG, Oy, GmbH, etc.). These conventions and all CCR rules are enforced deterministically by gate predicates (gate_10b, gate_10d).

### 4. Write Sequence

- Step 4.1: Create directory `docs/tier5_deliverables/proposal_sections/` if not present.
- Step 4.2: Write `impact_section.json` to `docs/tier5_deliverables/proposal_sections/impact_section.json`.
