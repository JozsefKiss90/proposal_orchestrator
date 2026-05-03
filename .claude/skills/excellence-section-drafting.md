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
- Base all reasoning ONLY on retrieved file content.

Return a SINGLE valid JSON object matching the output schema below.
Do not include ANY text before or after the JSON object — no prose, no
verification summaries, no markdown fencing. The response must begin with `{`
and end with `}`. Any non-JSON output causes a pipeline failure.

**Output size ceiling:** The total JSON response MUST be under 20,000 characters.
To stay within budget:
- B.1 sub-section content: concise evaluator-oriented paragraphs (3-5 sentences per sub-section). Do NOT reproduce full objective tables or WP task lists in prose.
- Keep each sub_sections[].content field under 2,500 characters.
- Keep each claim_statuses[].source_ref under 120 characters (path + ID only).
- Limit claim_statuses to 15 aggregated entries; group related claims.
- Use compact primary_sources entries (path only).

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Read `budget_gate_assessment.json`. Check `gate_pass_declaration` equals `"pass"`. If absent or not `"pass"`: return `{"status": "failure", "failure_reason": "Budget gate has not passed", "failure_category": "CONSTITUTIONAL_HALT"}` and halt.
- Step 1.2: Read `section_schema_registry.json`. Identify Excellence section entries. If empty or unreadable: return failure with `MISSING_INPUT`.
- Step 1.3: Read `evaluator_expectation_registry.json`. Identify the Excellence criterion entry. If absent: return failure with `MISSING_INPUT`.
- Step 1.4: Read `call_analysis_summary.json`. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.5: Read `concept_refinement_summary.json`. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.6: Read `wp_structure.json`. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.7: Read Tier 3 project data. Confirm at least `project_brief/` and `architecture_inputs/objectives.json` are present. If absent: return failure with `MISSING_INPUT`.
- Step 1.8: **Grant Agreement Annex guard** -- if any structural reference identifies a Grant Agreement Annex as the schema source: return failure with `CONSTITUTIONAL_HALT` and halt.

### 2. Core Processing Logic

- Step 2.1: **Identify Excellence sub-sections.** From `section_schema_registry.json`, extract the ordered list of mandatory sub-sections for the Excellence section. Do not add sub-sections not present in the registry.

- Step 2.2: **Read evaluation framing.** From `evaluator_expectation_registry.json`, extract the Excellence criterion's sub-criteria and scoring thresholds. Frame all sub-section content to address these sub-criteria directly.

- Step 2.3: **Draft each sub-section.** For each Excellence sub-section identified in Step 2.1:

  - Step 2.3.1: **Source project-specific content.** Draw all project facts exclusively from Tier 3. Do not fabricate partner names, capabilities, objectives, or prior work not present in Tier 3.

  - Step 2.3.2: **Apply call-aligned vocabulary.** Use the refined concept vocabulary from `concept_refinement_summary.json`. Align with the topic mapping rationale.

  - Step 2.3.3: **Ground methodology in WP structure.** Reference concrete WP tasks, deliverables, and approaches from `wp_structure.json`. Methodology claims must be traceable to specific WP activities.

  - Step 2.3.4: **Address evaluator sub-criteria.** For each sub-criterion in the Excellence evaluation criterion, ensure the sub-section content addresses it with presence, evidence, and project-specific detail.

  - Step 2.3.5: **TRL qualification.** If different WPs or outputs have different TRL targets per `architecture_inputs/objectives.json`, qualify TRL language accordingly. Do not make unqualified project-level TRL claims that imply all outputs reach the same TRL.

  - Step 2.3.6: **SSH and Gender dimension.** For SSH: if not substantively specified in Tier 3, state proportionately that the project is primarily technical. For gender dimension: only include claims traceable to both Tier 2A schema requirements and Tier 3/Tier 4 artifacts. Do not assert HR/recruitment practices (gender-balanced recruitment, etc.) unless explicitly described in Tier 3.

  - Step 2.3.7: Do not reference unvalidated budget figures.

  - Step 2.3.8: Follow all Canonical Consistency Rules (CCR-1 through CCR-4) below.

- Step 2.4: **Build validation_status.** Produce up to 15 aggregated claim_status entries grouping related claims. Each entry: claim_id, claim_summary, status ("confirmed" or "inferred"), source_ref (path + ID, max 120 chars). Set `overall_status` to the weakest status across all claims. OMIT any claim that cannot be confirmed or inferred — do not include "assumed" or "unresolved" entries.

- Step 2.5: **Build traceability_footer.** Populate `primary_sources` array. Include direct Tier 2B extracted source paths when the section asserts call scope, expected outcomes, or expected impacts. All `tier` values MUST be numeric integers (use 2 for Tier 2A/2B, 3 for Tier 3, 4 for Tier 4). Set `no_unsupported_claims_declaration` to `true` only if all claim_statuses are "confirmed" or "inferred" with non-null source_refs.

- Step 2.6: **Handle data gaps.** OMIT unsourceable claims. If the gap prevents drafting a mandatory sub-section entirely, return failure with `INCOMPLETE_OUTPUT`.

- Step 2.7: **Self-Check: Canonical Terminology and Deliverable Identity.** Before producing the final JSON output, scan the generated content and verify:
  1. Every canonical name from `objectives.json` or `outcomes.json` that contains a component keyword (engine, layer, architecture, protocol, framework, system) appears verbatim when that concept is referenced — not shortened or paraphrased.
  2. No WP or component label drops leading modifiers, trailing nouns, or other words present in the canonical objective title from `objectives.json`. If the WP title in `wp_structure.json` is shorter than the corresponding objective title, the full objective title must appear alongside or in place of the abbreviated WP label.
  3. Every deliverable ID cited is referenced with its canonical title and owning WP from `wp_structure.json`. No deliverable is attributed to a different objective, WP, or partner than its canonical source supports.
  4. Ownership verbs (delivers, produces, implements) are used only where the source artifact explicitly supports ownership; support verbs (validates, integrates, enables, benchmarks) are used otherwise.
  If any issue is found: revise the relevant sub-section content before outputting.

### 3. Output Schema

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
      {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json"},
      {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json"},
      {"tier": 3, "source_path": "docs/tier3_project_instantiation/..."},
      {"tier": 4, "source_path": "docs/tier4_orchestration_state/..."}
    ],
    "no_unsupported_claims_declaration": true
  }
}
```

- `schema_id`: const "orch.tier5.excellence_section.v1"
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

**WP/objective label overlap rule:** When a WP label or parenthetical description derives from or overlaps with a canonical objective title from `objectives.json`, the drafted content must either: (a) use the exact WP title from `wp_structure.json` and separately introduce the exact objective/component title from `objectives.json`, or (b) explicitly state the relationship between the WP and the canonical objective/component title without replacing one with the other. If the WP title in `wp_structure.json` is a shortened form of the corresponding objective title in `objectives.json` (e.g., the WP title drops a leading modifier or trailing noun), the canonical objective title governs component naming in evaluator-facing text because gate_10d enforces objective-title-level terminology.

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

### Rule CCR-4: Canonical Component / System Naming

All named components, systems, layers, and architectural elements referenced in drafted content MUST use their canonical names exactly as defined in Tier 3 artifacts (`architecture_inputs/objectives.json` titles, `architecture_inputs/outcomes.json` titles).

**Prohibited:**
- Truncating a canonical name (e.g., if the source title is "A B C", do not shorten it to "B C" when the shortened form could be interpreted as a different component)
- Extending a canonical name (e.g., appending words not in the source title)
- Substituting synonyms for any word in the canonical name
- Using a lowercased or differently-cased variant when the canonical name has specific casing

**Permitted aliasing:** A short alias MAY be used ONLY if:
1. The full canonical name is introduced first in the same sub-section
2. The alias is explicitly defined at introduction (e.g., "the [full canonical name] (hereafter [alias])")

**Enforcement:** gate_10d extracts canonical component names from Tier 3 objective titles containing component keywords (engine, layer, architecture, protocol, framework, system). If the name stem appears in section content but the full canonical name does not, gate_10d flags a terminology inconsistency.

**WP label terminology rule:** When enumerating WPs with descriptive labels in parentheses, and a WP's descriptive concept derives from a canonical objective title, the full canonical objective title from `objectives.json` must be used — not a potentially abbreviated WP title from `wp_structure.json`. No WP or component label may drop leading modifiers, trailing nouns, or other words that are present in the canonical objective title. If two source artifacts provide different labels for overlapping concepts, use the higher-tier canonical artifact designated by this skill for that concept, or avoid collapsing them into one label.

### Additional Conventions

When enumerating objectives, include every objective ID present in `architecture_inputs/objectives.json` exactly once. When linking objectives or components to WPs, use only WP/deliverable/task mappings explicitly present in `wp_structure.json`; if no explicit mapping exists, avoid exact WP lists. Use partner `short_name` or full `legal_name` from `consortium/partners.json` — do not truncate legal names by dropping suffixes (AG, Oy, GmbH, etc.). These conventions and all CCR rules are enforced deterministically by gate predicates (gate_10a, gate_10d).

### 4. Write Sequence

- Step 4.1: Create directory `docs/tier5_deliverables/proposal_sections/` if not present.
- Step 4.2: Write `excellence_section.json` to `docs/tier5_deliverables/proposal_sections/excellence_section.json`.
