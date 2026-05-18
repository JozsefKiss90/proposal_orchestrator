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
    When drafting Impact content, partial measurable-target reproduction is forbidden.
    If any quantitative or formal component from a canonical objective's measurable_target is used, every component from that same measurable_target MUST appear together in the same sentence or immediately adjacent clause. If the full bundle is too long, omit all objective-level metric components for that objective and use qualitative phrasing instead.

    For this MAESTRO run, the following hard bundles MUST be preserved whenever the corresponding objective, WP, outcome, deliverable, demonstrator, or pathway is discussed with any metric/formal target language:

    - OBJ-3 / WP4 / OUT-3 / Decentralised Multi-Agent Coordination:
      include ≥5 heterogeneous agents, ≥25% improvement in joint task completion, and formal proof of protocol convergence. Do not write only "provable convergence" or "formally specified protocols" if the pathway is presented as a target/impact claim.

    - OBJ-6 / WP7 / OUT-6 / Logistics Transfer Demonstrator — Cross-Sector Generalisation:
      include ≥20% improvement in disruption recovery time, ≥15% improvement in delivery schedule adherence, and validation across 3 supply chain corridors. Do not discuss WP7, ELI-led logistics transfer, D7-02, disruption recovery, transferability, or supply chain corridors as an impact target while omitting the ≥15% delivery schedule adherence component.

    - OBJ-7 / WP9 / OUT-7 / OUT-8 / Open framework release and ecosystem contribution:
      include ≥500 GitHub stars within 6 months of release, AI-on-demand platform contribution, validation through ≥2 TEFs, and technology transfer through ≥3 EDIHs. Do not mention ≥2 TEFs, ≥3 EDIHs, AI-on-demand platform contribution, open-source framework release, or SME/startup adoption while omitting ≥500 GitHub stars within 6 months of release.

    The preferred safe drafting pattern is to include the full bundles above verbatim in B.2.1 or B.2.2.

- 2.5a: **Required MAESTRO Impact Metric Sentences.** To prevent gate_10d CC-06 failures, include the following sentence content unless it directly contradicts a source artifact:
  - WP4/CERIA impact sentence must state that Decentralised Multi-Agent Coordination targets coordination of ≥5 heterogeneous agents, ≥25% improvement in joint task completion over independent baselines, and formal proof of protocol convergence.
  - WP7/ELI impact sentence must state that the Logistics Transfer Demonstrator targets ≥20% improvement in disruption recovery time and ≥15% improvement in delivery schedule adherence, validated across 3 supply chain corridors.
  - WP9/BAL ecosystem sentence must state that the open-source MAESTRO framework targets ≥500 GitHub stars within 6 months of release, AI-on-demand platform contribution, validation through ≥2 TEFs, and technology transfer through ≥3 EDIHs.

- 2.5b. MAESTRO Full Objective KPI Coverage (CC-06 Hard Enforcement)

For this MAESTRO run, the Impact section MUST ensure that every objective whose WP, outcome, deliverable, or demonstrator is referenced in B.2.1 or B.2.2 is either:

(A) fully represented with its complete measurable_target bundle, OR  
(B) completely omitted from quantitative discussion (qualitative phrasing only)

Partial reproduction is strictly forbidden.

The following objective bundles are REQUIRED when their corresponding WP or outcome is discussed:

- OBJ-4 / WP5 / Healthcare Demonstrator — Clinical Decision Support:
  MUST include ALL:
  - diagnostic reasoning accuracy within 10% of specialist clinician performance
  - evaluation on 500 de-identified clinical cases
  - spanning 5 diagnostic domains

  Forbidden pattern:
  mentioning "500 de-identified cases" without the accuracy threshold and domain scope.

- OBJ-8 / WP2 / External Tool and API Orchestration Layer:
  MUST include ALL:
  - typed tool registry supporting ≥30 external tools/APIs
  - tool invocation success rate ≥95%
  - mean recovery time from tool failure ≤5s
  - full provenance traces for 100% of tool invocations

  Forbidden pattern:
  mentioning WP2, orchestration, tool integration, or EO-01 advancement without including these KPI targets.

If full inclusion is not natural in the sentence, omit ALL quantitative elements for that objective and use qualitative phrasing instead.

Safe drafting rule:
When in doubt, explicitly include the full KPI bundle verbatim.

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
- 2.12: **Pillar Naming Consistency (CC-09 Prevention):**
  When describing research pillars adjacent to their WP IDs (e.g. in
  parenthetical or appositive position), use the canonical WP title from
  canonical_reference_pack.json, not abbreviated stems. Specifically:
  - WP2 → "Neuro-Symbolic Planning and Reasoning Engine" (not "neuro-symbolic planning")
  - WP3 → "Adaptive Memory Architecture" (not "adaptive memory")
  - WP4 → "Decentralised Multi-Agent Coordination" (not "multi-agent coordination")
  When a WP ID appears in parenthetical or appositive position, the
  accompanying descriptive label must include the canonical component keywords
  (engine, architecture, decentralised). Short references without a WP ID
  are acceptable in flowing prose.

### 3. Canonical Copying Rules

- Use `canonical_reference_pack.json` when available.
- Copy objective titles, outcome titles, WP titles, deliverable IDs/titles/due months, milestone IDs/titles, partner legal names, and partner short names exactly from declared source artifacts.
- Do not rename, shorten, paraphrase, or reassign IDs.
- Do not infer ownership. If ownership or relationship is unclear, omit the claim.
- Do not cite a deliverable unless its ID, title, parent WP, and due month are present in the source artifact.
- Keep the output concise and schema-conformant.
- **Partner Naming Form Consistency (CC-03 Prevention):** Within each
  sub-section, use ONE naming form consistently: either all short names
  (e.g. ATU, BIIS, CERIA) or all paired notation (legal_name (short_name)).
  Do not mix short names and full legal names within the same sub-section
  without explicit pairing. Prefer short-name-only form for conciseness.

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
