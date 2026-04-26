---
skill_id: implementation-section-drafting
purpose_summary: >
  Draft the Implementation section (Quality and efficiency) of the RIA/IA Part B
  from Phase 3 WP structure, Phase 4 Gantt, and Phase 6 implementation
  architecture. Produces implementation_section.json conforming to
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
writes_to:
  - docs/tier5_deliverables/proposal_sections/implementation_section.json
constitutional_constraints:
  - "Must verify budget gate passed before producing content"
  - "Must not redesign the consortium or WP structure"
  - "Must not use Grant Agreement Annex structure"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool.

**Declared input files to read (in order):**
1. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` -- MUST be read first; verify `gate_pass_declaration` equals `"pass"` before any other action
2. `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` -- section identifiers, page limits for Implementation section
3. `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` -- Quality criterion scoring logic and sub-criteria
4. `docs/tier2b_topic_and_call_sources/extracted/` -- Tier 2B extracted files (use Glob to discover, then Read: scope_requirements.json, call_constraints.json). Required when asserting call constraints (CC-*) or scope requirements (SR-*) in drafted content.
5. `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` -- WP definitions, tasks, deliverables, dependencies
6. `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` -- task schedule, milestone dates, critical path
7. `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` -- management structure, risk register, ethics, governance
8. `docs/tier3_project_instantiation/` -- project data (use Glob to discover, then Read: consortium/partners.json, consortium/roles.json, architecture_inputs/risks.json, call_binding/selected_call.json)

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

**Output size ceiling:** The total JSON response MUST be under 20,000 characters.
Exceeding this limit causes transport truncation and a pipeline failure. To stay
within budget:
- B.3.1 work-plan content: write a concise narrative overview, NOT an expanded
  application-form table dump. Summarize WPs in compact paragraphs (3-5 sentences
  each). Do NOT reproduce full task lists or deliverable tables in prose.
- B.3.2 consortium content: write a concise consortium-capacity narrative. One
  paragraph per partner (2-3 sentences). Do NOT expand role matrices into prose.
- Move long enumerations (dependency edges, deliverable lists, milestone lists)
  into compact arrays or terse summary sentences, not verbose tables.
- Keep each sub_sections[].content field under 2,000 characters.
- Keep each claim_statuses[].source_ref under 120 characters (file path + ID only).
- Limit claim_statuses to 15 entries maximum.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | Budget gate assessment | `gate_pass_declaration` | `orch.phase7.budget_gate_assessment.v1` | Verify budget gate passed; CLAUDE.md Section 8.4 absolute prerequisite |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | Section schema registry | Implementation section entries (sub-sections, page limits, mandatory elements) | `orch.tier2a.section_schema_registry.v1` | Structural authority for Implementation section |
| `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` | Evaluator expectations | Quality criterion entry (sub-criteria, scoring thresholds, grade descriptors) | `orch.tier2a.evaluator_expectation_registry.v1` | Evaluation framing for Quality and efficiency criterion |
| `docs/tier2b_topic_and_call_sources/extracted/` | Tier 2B extracted files (scope_requirements.json, call_constraints.json) | Scope requirements (SR-*), call constraints (CC-*), expected outcomes, expected impacts | N/A -- Tier 2B extracted directory | Authoritative source for any call constraint (CC-*) or scope requirement (SR-*) claims in drafted content; must be cited in traceability_footer when asserting SR/CC identifiers |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | WP structure | WP definitions, tasks, deliverables, responsible leads, dependencies | `orch.phase3.wp_structure.v1` | Primary source for work plan content, WP descriptions, deliverable tables |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | Gantt chart | Task schedule, milestone entries, critical path | `orch.phase4.gantt.v1` | Timeline narrative, milestone table, Gantt chart description |
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | Implementation architecture | management_structure, decision_matrix, risk_register, ethics_assessment, instrument_sections | `orch.phase6.implementation_architecture.v1` | Management structure, risk register, governance, ethics content |
| `docs/tier3_project_instantiation/` | Project data (consortium/, architecture_inputs/, call_binding/) | Partners, roles, capabilities, risks, selected call, project duration | N/A -- Tier 3 root directory | Consortium composition, partner descriptions, role assignments |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier5_deliverables/proposal_sections/implementation_section.json` | Implementation section draft | `orch.tier5.implementation_section.v1` | schema_id, run_id, criterion (const "Quality and efficiency of the implementation"), sub_sections (array: sub_section_id, title, content, word_count), wp_table_refs (array of WP IDs), gantt_ref (string), milestone_refs (array of milestone IDs), risk_register_ref (string), validation_status, traceability_footer | Yes | sub_sections: drafted from Phase 3/4/6 outputs and Tier 3 data, framed against Quality criterion scoring logic; structural references populated from source artifacts |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier5_deliverables/proposal_sections/implementation_section.json` | Yes -- artifact_id: a_t5_implementation_section | n08c_implementation_drafting |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Read `budget_gate_assessment.json`. Check `gate_pass_declaration` equals `"pass"`. If absent or not `"pass"`: return `{"status": "failure", "failure_reason": "Budget gate has not passed (gate_pass_declaration is not 'pass'); CLAUDE.md Section 8.4 prohibits any Phase 8 activity before budget gate passes", "failure_category": "CONSTITUTIONAL_HALT"}` and halt.
- Step 1.2: Read `section_schema_registry.json`. Identify Implementation section entries. If empty or unreadable: return failure with `MISSING_INPUT`.
- Step 1.3: Read `evaluator_expectation_registry.json`. Identify the Quality and efficiency criterion entry. If absent: return failure with `MISSING_INPUT`.
- Step 1.4: Read `wp_structure.json`. Check schema_id. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.5: Read `gantt.json`. Check schema_id. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.6: Read `implementation_architecture.json`. Check schema_id. If absent or schema mismatch: return failure with `MISSING_INPUT`.
- Step 1.7: Read Tier 3 consortium data (`partners.json`, `roles.json`). If absent: return failure with `MISSING_INPUT`.
- Step 1.8: **Grant Agreement Annex guard** -- inspect the section schema source. If any structural reference identifies a Grant Agreement Annex: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Section schema source appears to be a Grant Agreement Annex; CLAUDE.md Section 13.1") and halt.

### 2. Core Processing Logic

- Step 2.1: **Identify Implementation sub-sections.** From `section_schema_registry.json`, extract the ordered list of mandatory sub-sections. For RIA/IA, these typically cover:
  - Work plan and work packages (WP descriptions, task lists, deliverable table)
  - Gantt chart and timeline
  - Milestones table
  - Management structure and procedures
  - Risk management
  - Consortium as a whole
  - Resources to be committed

  The exact sub-section list is governed by the section schema registry. Do not add sub-sections not present in the registry.

- Step 2.2: **Read evaluation framing.** From `evaluator_expectation_registry.json`, extract the Quality and efficiency criterion's sub-criteria and scoring logic. Frame content to address these directly.

- Step 2.3: **Draft work plan sub-sections.** For each WP in `wp_structure.json`:

  - Step 2.3.1: **WP descriptions.** Draft per-WP descriptions including: WP title, lead partner, objectives, tasks with descriptions, deliverables with types and due months, person-months (only if confirmed in budget gate assessment). Do not redesign the WP structure -- present it as defined in Phase 3 (Constraint 2).

  - Step 2.3.2: **Deliverable table.** Build a structured deliverable table from `wp_structure.json` deliverable entries. Columns: deliverable number, deliverable name, WP, lead, type, dissemination level, due month.

  - Step 2.3.3: **Gantt narrative.** From `gantt.json`, describe the project timeline, critical path, task sequencing, and dependencies. Reference specific task IDs and months. **Dependency edge count:** The `wp_structure.json` dependency map contains 16 confirmed inter-WP data-input edges forming an acyclic graph. When referring to the full dependency map, state "16 confirmed inter-WP dependency edges". If referring only to pillar-to-demonstrator edges (WP2/3/4 to WP5/6/7), explicitly say "9 pillar-to-demonstrator edges" and do not include WP8 or WP9 in that count. **FORBIDDEN wording:** Do NOT write "nine dependency edges" when describing the full dependency map. Preferred safe wording: "The dependency map contains 16 confirmed inter-WP data-input edges forming an acyclic graph; within this, the three research pillar WPs feed the three demonstrator WPs through 9 pillar-to-demonstrator edges."

  - Step 2.3.4: **Milestones table.** From `gantt.json` milestone entries, build a milestone table with: milestone number, milestone name, WP, due month, verification criterion, responsible partner.

- Step 2.4: **Draft management and risk sub-sections.** From `implementation_architecture.json`:

  - Step 2.4.1: **Management structure.** Describe management bodies, meeting frequency, decision-making scope, escalation paths. Draw from `management_structure` field. Roles must reference only Tier 3 consortium partners. Do not assert programme-rule claims (e.g. "consortium agreement guidance") unless directly traceable to a Tier 1 normative source in reads_from. If governance structure references call constraints (CC-*) or scope requirements (SR-*), cite the specific Tier 2B extracted file in traceability_footer.primary_sources.

  - Step 2.4.2: **Risk register summary.** Present top risks with category, likelihood, impact, and mitigation measures from `risk_register` field.

  - Step 2.4.3: **Ethics self-assessment.** Summarize ethics flags from `ethics_assessment` field.

- Step 2.5: **Draft consortium sub-section.** From Tier 3 `partners.json` and `roles.json`, cross-referenced against Tier 4 `wp_structure.json`:

  - Step 2.5.1: **Partner WP lead and contributor roles.** Use `wp_structure.json` as the CANONICAL source for WP lead assignments and contributing partner lists. Tier 4 governs over Tier 3 when there is a conflict (CLAUDE.md Section 3, Priority 7 > Priority 6).

  - Step 2.5.2: **FORBIDDEN: "each partner leads exactly one WP" claim.** Do NOT assert that "each of the N partners leads exactly one functional WP" or equivalent. **FORBIDDEN phrases:** "each partner leads exactly one", "each of the 8 partners leads exactly one". ATU leads both WP1 and WP2 per wp_structure.json. Instead, use: "WP leadership is distributed across the consortium: ATU leads both WP1 and WP2, while BIIS, CERIA, NIHS, ISIA, ELI, FIIT, and BAL each lead one major functional WP."

  - Step 2.5.3: **Partner WP contributions must match Tier 4.** For each partner, state only WP participation roles that are confirmed in wp_structure.json `contributing_partners` arrays (or equivalent field). Do NOT claim a partner contributes to a WP unless wp_structure.json lists that partner for that WP. For example, if BAL is not listed as a contributing partner for WP4 in wp_structure.json, do NOT claim BAL contributes to WP4 regardless of what Tier 3 roles.json may suggest.

  - Step 2.5.4: **No unsourced programme-rule assertions.** Do NOT assert Tier 1 programme-rule obligations unless the skill reads the specific Tier 1 normative source AND includes it in reads_from and traceability_footer.primary_sources[]. This skill does NOT read Tier 1 sources. **FORBIDDEN phrases** (must not appear in any sub_sections[].content unless a Tier 1 source is explicitly read and cited): "GEP eligibility obligations", "required to hold Gender Equality Plans", "per Tier 1 programme rules", "at grant signature". Instead, for eligibility and administrative compliance topics, use: "Administrative eligibility declarations are handled outside this B.3.2 narrative and are not repeated here unless directly required by the section schema and traceable to a declared source." Do NOT cite Tier 1 programme rules from agent knowledge.

  - Step 2.5.5: Describe each partner's role, expertise, and contribution. Do not assign roles to partners not present in Tier 3 (Constraint 2, CLAUDE.md Section 13.3).

- Step 2.6: **Draft resources sub-section.** Describe resource allocation at the level confirmed by the budget gate. Do not cite specific budget figures not validated in `budget_gate_assessment.json` (CLAUDE.md Section 8.3).

- Step 2.7: **Populate structural references.**
  - `wp_table_refs`: array of all WP IDs from `wp_structure.json`.
  - `gantt_ref`: path to `gantt.json` (`docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json`).
  - `milestone_refs`: array of all milestone IDs from `gantt.json`.
  - `risk_register_ref`: path to `implementation_architecture.json` (`docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`).

- Step 2.8: **Build validation_status.** Per-claim Confirmed/Inferred classification. **GATE-CRITICAL: The output MUST NOT contain any claim_status with status = "assumed" or "unresolved".** If a claim cannot be confirmed or inferred with a valid source_ref chain, OMIT the claim from the drafted content entirely. The gate predicate `no_unresolved_material_claims` checks `validation_status.overall_status`; any value other than "confirmed" or "inferred" causes gate failure. Set `overall_status` to the weakest across all claims — must be "confirmed" or "inferred". Every claim_status MUST have a non-null source_ref. **Dissemination level claims:** If SEN/PU dissemination levels for deliverables are not directly present in wp_structure.json, gantt.json, or budget sources, mark them as "inferred" with a source chain (e.g. inferred from ethics_assessment ETHICS-02 for health data → SEN). Do NOT use "assumed" status. **Output size constraint for `source_ref`:** Use concise references only — file path plus field/ID (e.g. `"Tier 4: wp_structure.json WP2"` or `"Tier 3: consortium/partners.json"`). Maximum 120 characters per `source_ref`. Do NOT include prose or inference chains in `source_ref`. Limit `claim_statuses` to the 15 most material claims; group minor claims from the same source into aggregated entries.

- Step 2.9: **Build traceability_footer.** Populate `primary_sources` array. **Tier value format:** All `primary_sources[].tier` values MUST be numeric integers: Tier 2A/2B both use `"tier": 2`, Tier 3 uses `"tier": 3`, Tier 4 uses `"tier": 4`. Do NOT output string tier values. Include direct Tier 2B extracted source paths (scope_requirements.json, call_constraints.json) when the section asserts SR/CC identifiers.

- Step 2.10: **Handle data gaps.** OMIT unsourceable claims from the drafted content. Do not include them with "assumed" or "unresolved" status. Do not fabricate content. If a gap prevents drafting a mandatory sub-section entirely, return failure with `INCOMPLETE_OUTPUT`.

- Step 2.11: **Gate-readiness check.** After building `validation_status`, verify:
  - No claim_status has status "assumed" or "unresolved"
  - All claim_statuses have non-null source_ref
  - overall_status is "confirmed" or "inferred"
  - All primary_sources[].tier values are numeric integers (not strings)
  - no_unsupported_claims_declaration is true
  - No "each partner leads exactly one WP" claim present in content
  - No "nine dependency edges" when describing the full dependency map
  - No partner-WP-contributor claims contradicted by wp_structure.json
  - No unsourced Tier 1 programme-rule assertions or GEP forbidden phrases
  - Total JSON response under 20,000 characters
  If any condition fails: do NOT produce the output artifact. Instead, return `{"status": "failure", "failure_reason": "Implementation section has non-gate-ready content: <list specifics>.", "failure_category": "INCOMPLETE_OUTPUT"}`. This prevents writing a gate-blocking artifact.

### 3. Output Construction

Return a single JSON object conforming to `orch.tier5.implementation_section.v1`:

```json
{
  "schema_id": "orch.tier5.implementation_section.v1",
  "run_id": "<from task metadata>",
  "criterion": "Quality and efficiency of the implementation",
  "sub_sections": [
    {
      "sub_section_id": "<from section_schema_registry.json>",
      "title": "<from section_schema_registry.json>",
      "content": "<evaluator-oriented prose, grounded in Tier 1-4>",
      "word_count": "<actual word count of content>"
    }
  ],
  "wp_table_refs": ["WP1", "WP2", "WP3"],
  "gantt_ref": "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json",
  "milestone_refs": ["MS1", "MS2", "MS3"],
  "risk_register_ref": "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json",
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
      {"tier": 4, "source_path": "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"},
      {"tier": 4, "source_path": "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json"},
      {"tier": 4, "source_path": "docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json"},
      {"tier": 3, "source_path": "docs/tier3_project_instantiation/consortium/partners.json"},
      {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json"},
      {"tier": 2, "source_path": "docs/tier2b_topic_and_call_sources/extracted/call_constraints.json"}
    ],
    "no_unsupported_claims_declaration": true
  }
}
```

### 4. Conformance Stamping

- `schema_id`: set to "orch.tier5.implementation_section.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create directory `docs/tier5_deliverables/proposal_sections/` if not present.
- Step 5.2: Write `implementation_section.json` to `docs/tier5_deliverables/proposal_sections/implementation_section.json`.

## Constitutional Constraint Enforcement

*Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure.*

---

### Constraint 1: "Must verify budget gate passed before producing content"

**Decision point in execution logic:** Step 1.1.

**Exact failure condition:** `budget_gate_assessment.json` absent or `gate_pass_declaration` != "pass".

**Enforcement mechanism:** Unconditional guard at Step 1.1. Return CONSTITUTIONAL_HALT on trigger.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT").

**Hard failure confirmation:** Yes -- absolute prohibition.

**CLAUDE.md Section 13 cross-reference:** Section 13.4.

---

### Constraint 2: "Must not redesign the consortium or WP structure"

**Decision point in execution logic:** Step 2.3 -- at the point WP content is drafted; Step 2.5 -- at the point consortium descriptions are drafted.

**Exact failure condition:** (a) The drafted content introduces WPs, tasks, deliverables, or dependencies not present in `wp_structure.json`. (b) The drafted content assigns roles to partners not present in Tier 3 `partners.json` or `roles.json`. (c) The drafted content modifies WP lead assignments, task structures, or dependency chains from the Phase 3 design.

**Enforcement mechanism:** In Step 2.3.1, WP descriptions must present the structure as defined in `wp_structure.json` without modification. The skill does not have write access to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` and must not alter WP design. In Step 2.5, consortium descriptions must reference only partners from Tier 3. If the drafted content introduces a partner or role not in Tier 3: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Draft introduces partner/role not present in Tier 3; CLAUDE.md Section 13.3 prohibits fabricating project facts").

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT").

**Hard failure confirmation:** Yes -- redesigning the WP structure or consortium in the drafting phase is scope violation.

**CLAUDE.md Section 13 cross-reference:** Section 13.3 -- "Inventing project facts." Also Section 16.3 -- agents must not "redefine phase purposes or boundaries."

---

### Constraint 3: "Must not use Grant Agreement Annex structure"

**Decision point in execution logic:** Step 1.8.

**Exact failure condition:** Section schema source is a Grant Agreement Annex.

**Enforcement mechanism:** Unconditional guard. Return CONSTITUTIONAL_HALT on trigger.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT").

**Hard failure confirmation:** Yes.

**CLAUDE.md Section 13 cross-reference:** Section 13.1.

<!-- Constitutional constraint enforcement complete -->

## Failure Protocol

*All five failure categories are handled.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.2: `section_schema_registry.json` absent -> `failure_reason="section_schema_registry.json not found"`
- Step 1.3: `evaluator_expectation_registry.json` absent -> `failure_reason="evaluator_expectation_registry.json not found"`
- Step 1.4: `wp_structure.json` absent or schema mismatch -> `failure_reason="wp_structure.json not found or schema mismatch"`
- Step 1.5: `gantt.json` absent or schema mismatch -> `failure_reason="gantt.json not found or schema mismatch"`
- Step 1.6: `implementation_architecture.json` absent or schema mismatch -> `failure_reason="implementation_architecture.json not found or schema mismatch"`
- Step 1.7: Tier 3 consortium data absent -> `failure_reason="Tier 3 consortium data (partners.json, roles.json) not found"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Input artifacts with incorrect schema_id values -> `failure_reason="<artifact> schema mismatch"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

---

### CONSTRAINT_VIOLATION

No CONSTRAINT_VIOLATION conditions defined; all use CONSTITUTIONAL_HALT.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Mandatory sub-section cannot be drafted -> `failure_reason="Mandatory sub-section <sub_section_id> cannot be drafted"`
- `wp_table_refs` empty when WPs exist -> `failure_reason="wp_table_refs is empty despite WPs existing in wp_structure.json"`
- Output JSON missing required fields -> `failure_reason="Output missing required fields per orch.tier5.implementation_section.v1"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Step 1.1: Budget gate not passed -> `failure_reason="Budget gate has not passed; CLAUDE.md Section 8.4"`
- Step 1.8: Grant Agreement Annex guard -> `failure_reason="CLAUDE.md Section 13.1"`
- Constraint 2: WP/consortium redesign or fabrication -> `failure_reason="Draft introduces partner/role not present in Tier 3; CLAUDE.md Section 13.3"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No `implementation_section.json` written.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written when any failure category fires.
3. The invoking agent is responsible for logging the failure.
4. Failure is a correct and valid output per CLAUDE.md Section 15.

<!-- Failure protocol complete -->

## Schema Validation

*Validation of Output Construction against `artifact_schema_specification.yaml` for `implementation_section.json`.*

---

### Artifact: `implementation_section.json`

**Schema ID:** `orch.tier5.implementation_section.v1`

**Spec location:** `artifact_schema_specification.yaml` Section 2.1d (Tier 5 deliverables) -- `implementation_section` entry.

**Required fields per spec:**
- `schema_id` (string, const "orch.tier5.implementation_section.v1")
- `run_id` (string)
- `criterion` (string, const "Quality and efficiency of the implementation")
- `sub_sections` (array) -- each: sub_section_id, title, content, word_count
- `wp_table_refs` (array of strings)
- `gantt_ref` (string)
- `milestone_refs` (array of strings)
- `risk_register_ref` (string)
- `validation_status` (object, required)
- `traceability_footer` (object, required)
- `artifact_status` (optional, enum [valid, invalid]) -- runner-stamped; must be ABSENT at write time

**Output Construction (Step 3) verification:**
| Field | Set by skill? | Value source | Conformant? |
|-------|---------------|--------------|-------------|
| `schema_id` | Yes (Step 3, Step 4) | const "orch.tier5.implementation_section.v1" | Yes |
| `run_id` | Yes (Step 3, Step 4) | invoking agent's run_id | Yes |
| `criterion` | Yes (Step 3) | const "Quality and efficiency of the implementation" | Yes |
| `sub_sections[]` | Yes (Step 2.3-2.6, Step 3) | all sub-sections from section_schema_registry | Yes |
| `wp_table_refs` | Yes (Step 2.7) | WP IDs from wp_structure.json | Yes |
| `gantt_ref` | Yes (Step 2.7) | path to gantt.json | Yes |
| `milestone_refs` | Yes (Step 2.7) | milestone IDs from gantt.json | Yes |
| `risk_register_ref` | Yes (Step 2.7) | path to implementation_architecture.json | Yes |
| `validation_status` | Yes (Step 2.8) | per-claim classification | Yes |
| `traceability_footer` | Yes (Step 2.9) | primary_sources array | Yes |
| `artifact_status` | ABSENT at write time (Step 4) | runner stamps post-gate | Yes |

**reads_from compliance:** All declared (including Tier 2B extracted for SR/CC traceability). Compliant.

**writes_to compliance:** Single path declared. Compliant.

**Gaps identified:** None.

<!-- Schema validation complete -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour -- SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation -- must conform to that contract.
