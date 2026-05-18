---
skill_id: implementation-section-drafting
purpose_summary: >
  Draft the Implementation section (Quality and efficiency) of the RIA/IA Part B.
  Produces implementation_section.json conforming to
  orch.tier5.implementation_section.v1.
used_by_agents:
  - implementation_writer
reads_from:
  - docs/tier2a_instrument_schemas/extracted/
  - docs/tier2b_topic_and_call_sources/extracted/
  - docs/tier3_project_instantiation/
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
  - docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
  - docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/canonical_reference_pack.json
writes_to:
  - docs/tier5_deliverables/proposal_sections/implementation_section.json
constitutional_constraints:
  - "Must verify budget gate passed before producing content"
  - "Must not redesign the consortium or WP structure"
  - "Must not use Grant Agreement Annex structure"
---

## Input Access (TAPM Mode)

This skill executes in TAPM. Read declared inputs from disk using the Read tool.

**Declared inputs (read in order):**
1. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` -- verify `gate_pass_declaration` equals `"pass"` before any other action
2. `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` -- Implementation section identifiers, page limits
3. `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` -- Quality criterion scoring logic
4. `docs/tier2b_topic_and_call_sources/extracted/` -- Glob then Read: scope_requirements.json, call_constraints.json (required when asserting SR-*/CC-* identifiers)
5. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`
6. `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json`
7. `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`
8. `docs/tier3_project_instantiation/` -- Glob then Read: consortium/partners.json, consortium/roles.json, architecture_inputs/risks.json, call_binding/selected_call.json
9. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/canonical_reference_pack.json` -- if present, use as authoritative source for canonical terms (objective titles, WP titles, deliverable IDs/titles/months, partner names)

Do not read files outside this set. Base all reasoning on retrieved file content only.

Return a SINGLE valid JSON object. No prose, no markdown fencing. Response must begin with `{` and end with `}`. Non-JSON output causes a pipeline failure.

**Output size ceiling:** Total JSON response MUST be under 20,000 characters.
- Work-plan content: concise narrative, not expanded table dump. Summarize WPs in 3-5 sentences each.
- Consortium content: one paragraph per partner (2-3 sentences).
- Each sub_sections[].content under 2,000 characters.
- Each claim_statuses[].source_ref under 120 characters.
- Limit claim_statuses to 15 entries.

## Execution Specification

### 1. Input Validation

- 1.1: Read `budget_gate_assessment.json`. If `gate_pass_declaration` is not `"pass"`: return `{"status": "failure", "failure_reason": "Budget gate has not passed", "failure_category": "CONSTITUTIONAL_HALT"}`.
- 1.2: Read `section_schema_registry.json`. Identify Implementation entries. If absent: failure `MISSING_INPUT`.
- 1.3: Read `evaluator_expectation_registry.json`. Identify Quality and efficiency criterion. If absent: failure `MISSING_INPUT`.
- 1.4: Read `wp_structure.json`. If absent: failure `MISSING_INPUT`.
- 1.5: Read `gantt.json`. If absent: failure `MISSING_INPUT`.
- 1.6: Read `implementation_architecture.json`. If absent: failure `MISSING_INPUT`.
- 1.7: Read Tier 3 consortium data (`partners.json`, `roles.json`). If absent: failure `MISSING_INPUT`.
- 1.8: If any structural reference identifies a Grant Agreement Annex as schema source: failure `CONSTITUTIONAL_HALT`.

### 2. Core Processing

- 2.1: **Identify sub-sections** from `section_schema_registry.json`. Do not add sub-sections not in the registry.

- 2.2: **Read evaluation framing** from `evaluator_expectation_registry.json`. Frame content to address Quality and efficiency sub-criteria directly.

- 2.3: **Draft work plan sub-sections.** For each WP in `wp_structure.json`:
  - **WP descriptions:** WP title, lead partner, objectives, tasks, deliverables with types and due months, person-months (only if confirmed in budget gate). Present the Phase 3 design -- do not redesign it.
  - **Deliverable table:** from `wp_structure.json` deliverable entries.
  - **Gantt narrative:** from `gantt.json`, describe timeline, critical path, task sequencing, dependencies. Use dependency counts exactly as stated -- do not invent or approximate.
  - **Milestones table:** from `gantt.json` milestone entries.

- 2.4: **Draft management and risk sub-sections.** From `implementation_architecture.json`:
  - **Management structure:** management bodies, meeting frequency, decision-making scope, escalation. Roles reference only Tier 3 consortium partners. Do not assert programme-rule claims unless directly traceable to a source in reads_from.
  - **Risk register:** top risks with category, likelihood, impact, mitigation. Use frequencies and intervals exactly as stated.
  - **Ethics self-assessment:** summarize ethics flags from `implementation_architecture.json`.
    **Tier 1 Ethics Category Restriction:** Do not state numbered ethics categories,
    programme-rule category labels, or Horizon Europe ethics classification numbers
    (e.g. "Category 8", "Category 4", "Category 2") unless Tier 1 normative sources
    are explicitly read and cited. This skill does not read Tier 1. If the source
    artifact contains category numbers, omit the numbers and describe only the
    project-specific ethics issue in plain language.
    Allowed phrasing examples:
    - "AI-system ethics considerations are tracked for WP2/WP4/WP5/WP6."
    - "Health-data processing and clinical expert involvement are tracked for WP5."
    - "Ethics mitigation and oversight responsibilities are described in the implementation architecture."
    Forbidden (unless Tier 1 is read): "Category 8", "Category 4", "Category 2",
    or any numbered HE ethics self-assessment classification.

- 2.5: **Draft consortium sub-section.** From Tier 3 `partners.json` and `roles.json`, cross-referenced against `wp_structure.json`:
  - Use `wp_structure.json` as the canonical source for WP lead assignments. Tier 4 governs over Tier 3 on conflict.
  - Derive WP leadership distribution from data -- do not assert uniform distribution unless literally true.
  - State only roles confirmed in `wp_structure.json`. When Tier 3 and Tier 4 conflict on contributor roles, state WP leads and domain expertise without enumerating conflict-prone contributor lists.
  - Do not assign roles to partners not in Tier 3.
  - Do not assert Tier 1 programme-rule obligations unless this skill reads the Tier 1 source.
  - Do not overclaim scope-requirement coverage.


- 2.6: **Draft resources sub-section.** Describe resource allocation at the level confirmed by the budget gate. Do not cite budget figures not validated in `budget_gate_assessment.json`.

- 2.7: **Populate structural references:** `wp_table_refs`, `gantt_ref`, `milestone_refs`, `risk_register_ref`.

- 2.8: **Build validation_status.** Up to 15 aggregated claim_status entries. Each: claim_id, claim_summary, status ("confirmed"/"inferred"), source_ref (max 120 chars). `overall_status` = weakest. Omit claims that cannot be confirmed or inferred. Ethics claim_statuses may cite `implementation_architecture.json` for project-specific ethics flags and mitigation ownership, but must not describe numbered ethics categories as "confirmed" unless Tier 1 is included in primary_sources.

- 2.9: **Build traceability_footer.** All `tier` values MUST be numeric integers. Include Tier 2B paths when asserting SR/CC identifiers. Set `no_unsupported_claims_declaration` true only if all claims confirmed/inferred with non-null source_refs.

- 2.10: **Handle data gaps.** Omit unsourceable claims. If a mandatory sub-section cannot be drafted: failure `INCOMPLETE_OUTPUT`.

### 3. Canonical Copying Rules

- Use `canonical_reference_pack.json` when available.
- Copy objective titles, outcome titles, WP titles, deliverable IDs/titles/due months, milestone IDs/titles, partner legal names, and partner short names exactly from declared source artifacts.
- Do not rename, shorten, paraphrase, or reassign IDs.
- Do not infer ownership. If ownership or relationship is unclear, omit the claim.
- Do not cite a deliverable unless its ID, title, parent WP, and due month are present in the source artifact.
- Keep the output concise and schema-conformant.

### 3a. Consortium Numeric Claims Rule

When the drafted text states the number of consortium countries (e.g., "partners from N countries", "N EU Member States"), the count MUST be derived by computing the number of distinct values in `canonical_reference_pack.partners[].country`. Do not guess, assume, or hard-code a country count.

Likewise, when stating the partner count, use `len(canonical_reference_pack.partners)`.

If `canonical_reference_pack.json` is not available or does not contain a `partners` array with `country` fields, do not state a numeric country count — use qualitative language instead (e.g., "partners across multiple EU Member States").


### 3b. WP Title Attachment Rule (gate_10c canonical term preservation)

When drafting B.3.2 consortium capacity text, do not attach partner capability descriptions directly to a WP ID using a colon, dash, parenthetical, or appositive unless the canonical WP title appears immediately with that WP ID. The deterministic gate treats nearby appositive text as a WP title; therefore capability prose must be separated from WP-title notation.

Use this safe pattern whenever a partner lead role and capability description appear in the same sentence:

- `leads WP2 (Neuro-Symbolic Planning and Reasoning Engine); expertise in ...`
- `leads WP4 (Decentralised Multi-Agent Coordination); expertise in ...`
- `leads WP6 (Manufacturing Demonstrator — Process Optimisation); expertise in ...`
- `leads WP8 (Integration, Evaluation and Benchmarking); expertise in ...`

Forbidden patterns:

- `leads WP2: expertise in ...`
- `leads WP4: formal multi-agent coordination protocols ...`
- `leads WP6: operational pilot factory environment ...`
- `leads WP8: AI evaluation methodology ...`

General rule: after any `WP*` reference followed by punctuation that introduces descriptive text, first write the exact canonical title from `canonical_reference_pack.wps[].title`, then separate capability descriptions with a semicolon or a new sentence. Do not let a capability phrase become the apparent title attached to the WP ID.

### 4. Output Schema

Return JSON conforming to `orch.tier5.implementation_section.v1`:

```json
{
  "schema_id": "orch.tier5.implementation_section.v1",
  "run_id": "<from task metadata>",
  "criterion": "Quality and efficiency of the implementation",
  "sub_sections": [
    {
      "sub_section_id": "<from section_schema_registry.json>",
      "title": "<from section_schema_registry.json>",
      "content": "<evaluator-oriented prose>",
      "word_count": "<actual word count>"
    }
  ],
  "wp_table_refs": ["WP1", "WP2"],
  "gantt_ref": "docs/tier4_.../gantt.json",
  "milestone_refs": ["MS1", "MS2"],
  "risk_register_ref": "docs/tier4_.../implementation_architecture.json",
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
      {"tier": 4, "source_path": "docs/tier4_.../wp_structure.json"},
      {"tier": 4, "source_path": "docs/tier4_.../gantt.json"},
      {"tier": 3, "source_path": "docs/tier3_.../partners.json"},
      {"tier": 2, "source_path": "docs/tier2b_.../scope_requirements.json"}
    ],
    "no_unsupported_claims_declaration": true
  }
}
```

- `schema_id`: const `"orch.tier5.implementation_section.v1"`
- `run_id`: from invoking agent's run_id
- `artifact_status`: MUST be absent at write time

### 5. Write Sequence

- Create `docs/tier5_deliverables/proposal_sections/` if not present.
- Write to `docs/tier5_deliverables/proposal_sections/implementation_section.json`.
