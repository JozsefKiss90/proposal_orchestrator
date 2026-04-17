---
skill_id: concept-alignment-check
purpose_summary: >
  Check the alignment between the project concept and the call expected outcomes and
  scope requirements, identifying vocabulary gaps, framing mismatches, and uncovered
  expected outcomes.
used_by_agents:
  - concept_refiner
reads_from:
  - docs/tier3_project_instantiation/project_brief/
  - docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json
  - docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
  - docs/tier2b_topic_and_call_sources/extracted/call_constraints.json
  - docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
  - docs/tier4_orchestration_state/decision_log/
  - docs/tier3_project_instantiation/call_binding/topic_mapping.json
  - docs/tier3_project_instantiation/call_binding/compliance_profile.json
constitutional_constraints:
  - "Alignment must be tested against Tier 2B extracted files, not assumed from concept vocabulary"
  - "Uncovered expected outcomes must be flagged, not silently assumed covered"
---

## Input Access (TAPM Mode)

Read the files listed in the Declared Inputs section from disk using the Read tool.
For the project brief, read `docs/tier3_project_instantiation/project_brief/` as a directory: use Glob to list its contents, then Read each file — including `.md` and `.json` files (concept_note.md, strategic_positioning.md, project_summary.json).
Read `expected_outcomes.json` and `scope_requirements.json` — these are the Tier 2B extracted files that define alignment targets.
Read `call_constraints.json` if present — provides call-specific constraints for compliance profile derivation.
Read `eligibility_conditions.json` if present — provides eligibility conditions for compliance profile derivation.
Do not read files outside the declared input set.
Do not read work programme source documents, grouped JSON files, or other Tier 2B extracted files not listed in the declared inputs.
Return your output as a single JSON object in your response. The response must include fields for all three output artifacts: concept_refinement_summary (flat at top level), topic_mapping (nested under key `topic_mapping`), and compliance_profile (nested under key `compliance_profile`). Returning an empty object `{}` for any artifact is invalid and will be treated as a failure.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/project_brief/` | Project brief directory: concept_note (PDF/DOCX/MD), project_summary (PDF/DOCX/MD), strategic_positioning (PDF/DOCX/MD) | Concept description; stated objectives; target outcomes; approach narrative; differentiation claims; vocabulary used | N/A — Tier 3 source directory | Source of the project concept being evaluated; the text is compared term-by-term and claim-by-claim against Tier 2B expected outcomes and scope requirements |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | expected_outcomes.json — Tier 2B extracted | Expected outcome entries: outcome_id, description, source_section, source_document, status | N/A — Tier 2B extracted artifact | The authoritative list of call-required expected outcomes that the concept must address; uncovered outcomes must be flagged |
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | scope_requirements.json — Tier 2B extracted | Scope boundary entries: scope element descriptions, source_section, source_document, status | N/A — Tier 2B extracted artifact | Defines the thematic scope boundary; concept claims outside this boundary are flagged as scope mismatches |
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | call_constraints.json — Tier 2B extracted (optional) | Constraint entries: constraint_id, description, constraint_type, source_section, source_document | N/A — Tier 2B extracted artifact | Provides call-specific constraints (eligibility, scope, methodological) used to derive compliance profile flags; optional — continue with conservative defaults if absent |
| `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json` | eligibility_conditions.json — Tier 2B extracted (optional) | Condition entries: condition_id, description, condition_type, source_section, source_document | N/A — Tier 2B extracted artifact | Provides eligibility conditions for compliance profile derivation; optional — set eligibility_confirmed to false if absent |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | concept_refinement_summary.json | `orch.phase2.concept_refinement_summary.v1` | schema_id, run_id, topic_mapping_rationale (object: topic_element_id, mapping_to_concept, tier2b_source_ref, tier3_evidence_ref per entry), scope_conflict_log (array: conflict_id, description, resolution_status, resolution_note, tier2b_source_ref per entry), strategic_differentiation (string, non-empty) | Yes | topic_mapping_rationale entries derived from expected_outcomes.json entries matched against project_brief content; scope_conflict_log derived from scope mismatches found; strategic_differentiation derived from strategic_positioning document in project_brief |
| `docs/tier4_orchestration_state/decision_log/` | Per-invocation decision log entry file | N/A — decision log entry | decision_id; decision_type: "concept_alignment"; invoking_agent; phase_context; alignment_findings; uncovered_outcomes list; vocabulary_gaps list; tier2b_source_refs; resolution_status; timestamp | No | Vocabulary gaps and uncovered outcomes derived from comparing concept vocabulary against expected_outcomes.json and scope_requirements.json entries |
| `docs/tier3_project_instantiation/call_binding/topic_mapping.json` | topic_mapping.json — Tier 3 call binding | mappings (array: topic_element_id, tier2b_source_ref, tier3_evidence_ref, mapping_description per entry) | N/A — Tier 3 source artifact (no schema_id, no run_id) | Derived from topic_mapping_rationale in Step 2.11; maps each call topic element to the project concept with bidirectional source references |
| `docs/tier3_project_instantiation/call_binding/compliance_profile.json` | compliance_profile.json — Tier 3 call binding | eligibility_confirmed (boolean), ethics_review_required (boolean), gender_plan_required (boolean), open_science_requirements (array of strings) | N/A — Tier 3 source artifact (no schema_id, no run_id) | Derived from call constraints and eligibility conditions analysis in Step 2.12; records compliance flags for downstream phases |

**Note:** `artifact_status` must be ABSENT at write time for concept_refinement_summary.json; the runner stamps it post-gate. `topic_mapping.json` and `compliance_profile.json` are Tier 3 artifacts — they do NOT carry `schema_id`, `run_id`, or `artifact_status`.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | Yes — artifact_id: a_t4_phase2 (directory); canonical file within that directory | n02_concept_refinement |
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry | n02_concept_refinement |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier3_project_instantiation/project_brief/` exists and is non-empty (dir_non_empty). If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="project_brief/ directory is empty; concept alignment cannot proceed without project concept text") and halt.
- Step 1.2: Presence check — confirm `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="expected_outcomes.json not found; call-requirements-extraction must run before concept-alignment-check") and halt.
- Step 1.3: Non-empty check — confirm `expected_outcomes.json` contains at least one entry. If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="expected_outcomes.json is empty; cannot check alignment without expected outcome definitions") and halt.
- Step 1.4: Presence check — confirm `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` exists and is non-empty. If absent or empty: log as Unresolved; continue without scope constraint checking, but flag this gap in scope_conflict_log.
- Step 1.5: Read all files in `project_brief/` (concept_note, project_summary, strategic_positioning). Concatenate their text content into a single **concept corpus** for analysis. If no readable files are found: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="project_brief/ contains no readable concept documents") and halt.
- Step 1.6: Presence check — attempt to read `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json`. If absent: log as Assumed; continue without call constraint data. Compliance profile derivation (Step 2.12) will use conservative defaults.
- Step 1.7: Presence check — attempt to read `docs/tier2b_topic_and_call_sources/extracted/eligibility_conditions.json`. If absent: log as Assumed; set `eligibility_confirmed` to `false` in the compliance profile (conservative default). Continue.

### 2. Core Processing Logic

- Step 2.1: Build the **expected outcomes list** from `expected_outcomes.json`: extract all entries, each with `outcome_id`, `description`, `source_section`, `source_document`.
- Step 2.2: Build the **scope boundary list** from `scope_requirements.json` (if available): extract all entries with `scope_element_id`, `description`, `boundary_type`.
- Step 2.3: Extract the **vocabulary set** from the concept corpus: collect all significant noun phrases, domain terms, and technical terminology present in the concept text. Normalise to lowercase for comparison.
- Step 2.4: For each expected outcome entry (from Step 2.1), perform the following alignment assessment:
  - Extract the **key terms** from the expected outcome `description`: noun phrases are extracted by identifying consecutive nouns and noun-adjective combinations of 1–4 words that name a domain concept, technology, or activity (e.g., "machine learning", "clinical trial", "carbon emissions", "policy framework"). Domain terms are any technical or field-specific single-word terms not in common general vocabulary. Synonyms are limited to terms that are definitionally equivalent (not merely related in subject area); a synonym must be explicitly recognised as an alias for the same concept — if uncertain, do not treat as a synonym, record as a vocabulary gap instead.
  - For each key term: check whether it (case-insensitive exact match) or a definitionally equivalent synonym appears in the concept corpus vocabulary set (Step 2.3). A match requires either: (a) exact string match (case-insensitive), or (b) an exact synonym from a recognised controlled vocabulary (e.g., the term appears in the same ontology entry or is the official EU programme alias for the same concept). Partial matches (related but not equivalent terms) do not count as a match; they are recorded as vocabulary gaps.
  - Evaluate **mechanism coverage**: check whether the concept corpus contains at least one sentence that describes a specific project activity (method, approach, tool, task, or work package objective) whose stated purpose or expected result is consistent with producing or contributing to the expected outcome's stated description.
  - Assign status per the following criteria:
    - **Confirmed**: At least one key term from the expected outcome description appears verbatim (or as a recognised synonym) in the concept corpus, AND the concept describes a specific mechanism (activity, method, approach) that would produce or contribute to this outcome, AND no contradicting statement is present in the concept. Record `tier3_evidence_ref` as the filename + approximate location in project_brief/ where the evidence appears.
    - **Inferred**: The concept does not use the same vocabulary as the expected outcome but describes an approach that logically leads to this outcome. The inference chain must be stated explicitly as: "The concept describes [X activity] which leads to [Y result] which satisfies outcome [outcome_id description]." Record this in `mapping_to_concept`.
    - **Assumed**: The concept does not explicitly address this outcome and no logical derivation is evident, but the general project domain is the same as the outcome domain. The assumption must be explicitly declared: "No direct coverage found; assumed to be covered by project's general [domain] focus." This is a weak status and flags a real gap.
    - **Unresolved**: The concept contains statements that directly contradict this expected outcome (e.g., the outcome requires multi-country collaboration but the concept is single-institution), OR the outcome description is Unresolved in the source Tier 2B data (source status was Unresolved) and cannot be evaluated. Must record `conflict_note`.
  - Vocabulary gap: if key terms from the expected outcome do not appear in the concept corpus, record these terms in a `vocabulary_gaps` array for this outcome entry.
- Step 2.5: Build the `topic_mapping_rationale` object. Keys are `topic_element_id` values from expected_outcomes.json (i.e., `outcome_id` values). For each entry: `{ topic_element_id, mapping_to_concept (string describing how addressed), tier2b_source_ref (source_section + source_document from expected_outcomes.json entry), tier3_evidence_ref (project_brief/ filename + approximate location), status (Confirmed/Inferred/Assumed/Unresolved), vocabulary_gaps (array of strings) }`.
- Step 2.6: Identify **framing mismatches**: cases where the concept addresses the outcome topic but uses a frame inconsistent with the call's framing (e.g., the call frames the outcome as a societal transformation but the concept frames it as a commercial product). A framing mismatch is when: the concept addresses the subject of the outcome but the mechanism, beneficiary, or impact type differs materially from the outcome's stated framing. Record framing mismatches as entries in the `scope_conflict_log` with `conflict_type: "framing_mismatch"`.
- Step 2.7: Identify **scope conflicts** using the scope boundary list from Step 2.2: for each `excluded_topic` boundary entry, check whether the concept corpus discusses this topic. If so: create a scope_conflict_log entry with `conflict_id`, `description` (what was found in the concept vs. the boundary), `resolution_status: "unresolved"`, `tier2b_source_ref`. For `conditional_requirement` entries: check whether the concept meets the condition; if not met and not flagged as inapplicable, create an entry with `resolution_status: "unresolved"`.
- Step 2.8: Build the `scope_conflict_log` array: all framing mismatches (from Step 2.6) and scope conflicts (from Step 2.7). If none found, the array is empty. Each entry must have: `conflict_id`, `description`, `resolution_status` (resolved / unresolved), `resolution_note` (required when resolved), `tier2b_source_ref`, `conflict_type` (framing_mismatch / scope_violation / conditional_unmet).
- Step 2.9: Build `strategic_differentiation` from the `strategic_positioning` file in project_brief/ (if present). Extract the core differentiation statement (what distinguishes this project from others in the call scope). If no strategic positioning file is present: set strategic_differentiation to "No strategic positioning document provided — differentiation statement required." (This will cause the Phase 2 gate semantic predicate to flag the gap.)
- Step 2.10: Build the decision log entry: compile `alignment_findings` (summary of Confirmed/Inferred/Assumed/Unresolved counts), `uncovered_outcomes` (list of outcome_ids with status Assumed or Unresolved), `vocabulary_gaps` (aggregate list of terms from all outcomes), `tier2b_source_refs` (list of source_section + source_document pairs consulted).
- Step 2.11: **Derive `topic_mapping`** from `topic_mapping_rationale` (Step 2.5). For each entry in `topic_mapping_rationale`, create a corresponding entry in the `mappings` array with: `topic_element_id` (same as `topic_element_id`), `tier2b_source_ref` (same as `tier2b_source_ref`), `tier3_evidence_ref` (same as `tier3_evidence_ref`), `mapping_description` (same as `mapping_to_concept`). The `mappings` array must be non-empty — it must contain one entry per expected outcome from `expected_outcomes.json`. If `topic_mapping_rationale` is empty (which should not happen given Constraint 2), this constitutes an INCOMPLETE_OUTPUT failure.
- Step 2.12: **Derive `compliance_profile`** from call constraints (Step 1.6), eligibility conditions (Step 1.7), and scope requirements (Step 2.2):
  - `eligibility_confirmed`: Set to `true` if `eligibility_conditions.json` is present and all conditions with `condition_type: "consortium_composition"` are satisfiable based on the concept (i.e., the concept does not explicitly contradict them). Set to `false` if eligibility_conditions.json is absent or any condition is contradicted. When uncertain, set to `false` (conservative).
  - `ethics_review_required`: Set to `true` if any constraint in `call_constraints.json` has `constraint_type: "scope"` or description mentioning ethics review, OR if the concept corpus mentions human subjects, personal data, animal experimentation, dual use, or other ethics-triggering activities. Set to `false` only when no ethics triggers are found. When uncertain, set to `true` (conservative).
  - `gender_plan_required`: Set to `true` if any scope requirement or call constraint mentions gender equality plan, gender dimension, or gender-related requirements. Default to `true` for RIA and IA instrument types (conservative).
  - `open_science_requirements`: Extract from call constraints and scope requirements any requirements related to open access, open data, FAIR principles, or open science mandates. Return as an array of requirement description strings. If none found, return an empty array `[]`.
  - `notes`: Optional string with any additional compliance observations.

### 3. Output Construction

**`concept_refinement_summary.json`:**
- `schema_id`: set to "orch.phase2.concept_refinement_summary.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `topic_mapping_rationale`: derived from Step 2.5 — object keyed by outcome_id; each value: `{topic_element_id, mapping_to_concept, tier2b_source_ref, tier3_evidence_ref, status, vocabulary_gaps}`
- `scope_conflict_log`: derived from Step 2.8 — array of `{conflict_id, description, resolution_status, resolution_note, tier2b_source_ref, conflict_type}`
- `strategic_differentiation`: derived from Step 2.9 — string from strategic_positioning document

**Decision log entry file (`concept_alignment_<agent_id>_<timestamp>.json`):**
- `decision_id`: `"concept_alignment_<agent_id>_<ISO8601_timestamp>"`
- `decision_type`: `"concept_alignment"`
- `invoking_agent`: from agent context
- `phase_context`: `"phase_02_concept_refinement"`
- `alignment_findings`: from Step 2.10 — summary object with outcome counts by status
- `uncovered_outcomes`: from Step 2.10 — array of outcome_ids (Assumed or Unresolved)
- `vocabulary_gaps`: from Step 2.10 — aggregate array of gap terms
- `tier2b_source_refs`: from Step 2.10 — array of source references consulted
- `tier_authority_applied`: string — must reference the specific Tier 2B files used as the alignment authority (e.g., "Tier 2B expected_outcomes.json; Tier 2B scope_requirements.json"); required per CLAUDE.md §9.4 and decision-log-update skill contract
- `resolution_status`: "unresolved" if any Unresolved scope conflicts or Unresolved outcome statuses; otherwise "resolved"
- `timestamp`: ISO 8601

**`topic_mapping` (nested under key `topic_mapping` in the response):**
- `mappings`: derived from Step 2.11 — array of `{topic_element_id, tier2b_source_ref, tier3_evidence_ref, mapping_description}` — must be non-empty
- Do NOT include `schema_id`, `run_id`, or `artifact_status` — this is a Tier 3 source artifact

**`compliance_profile` (nested under key `compliance_profile` in the response):**
- `eligibility_confirmed`: derived from Step 2.12 — boolean
- `ethics_review_required`: derived from Step 2.12 — boolean
- `gender_plan_required`: derived from Step 2.12 — boolean
- `open_science_requirements`: derived from Step 2.12 — array of strings (may be empty `[]`)
- `notes`: optional string — any additional compliance observations
- Do NOT include `schema_id`, `run_id`, or `artifact_status` — this is a Tier 3 source artifact

### 4. Conformance Stamping

- `schema_id`: set to "orch.phase2.concept_refinement_summary.v1" at write time (concept_refinement_summary only)
- `run_id`: copied from invoking agent's run_id parameter (concept_refinement_summary only)
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)
- `topic_mapping.json` and `compliance_profile.json` do NOT carry `schema_id`, `run_id`, or `artifact_status` — they are Tier 3 source artifacts

### 5. Write Sequence

- Step 5.1: Write `concept_refinement_summary.json` to `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json`
- Step 5.2: Write decision log entry to `docs/tier4_orchestration_state/decision_log/<decision_id>.json`
- Step 5.3: Write `topic_mapping.json` to `docs/tier3_project_instantiation/call_binding/topic_mapping.json` — derived from Step 2.11. Must contain a non-empty `mappings` array.
- Step 5.4: Write `compliance_profile.json` to `docs/tier3_project_instantiation/call_binding/compliance_profile.json` — derived from Step 2.12. Must contain all four required fields.

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Alignment must be tested against Tier 2B extracted files, not assumed from concept vocabulary"

**Decision point in execution logic:** Step 2.4 — at the point each expected outcome entry from `expected_outcomes.json` is matched against the concept corpus.

**Exact failure condition:** Any expected outcome entry is assigned `status: "Confirmed"` or `status: "Inferred"` in `topic_mapping_rationale` without: (a) a `tier2b_source_ref` that identifies the specific `source_section` and `source_document` from `expected_outcomes.json`; AND (b) a `tier3_evidence_ref` that identifies a specific file and location in `docs/tier3_project_instantiation/project_brief/` where the matching concept evidence was found. Equivalently: any alignment judgment is made from the skill's prior knowledge of what "aligned concepts" look like rather than from comparing the actual concept corpus against the actual Tier 2B file entries.

**Enforcement mechanism:** In Step 2.5, for every entry in `topic_mapping_rationale`: before setting `status: "Confirmed"` or `status: "Inferred"`, the skill must verify that `tier2b_source_ref` is non-empty (populated from `expected_outcomes.json` entry data) AND `tier3_evidence_ref` is non-empty (populated from actual file evidence in project_brief/). If either is absent: the status must be downgraded to "Assumed" or "Unresolved" as appropriate. It is never acceptable to mark an outcome "Confirmed" without both references. If the skill cannot perform any Tier 2B-grounded alignment evaluation: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Alignment evaluation cannot be performed without Tier 2B extracted files; assuming alignment from concept vocabulary alone is prohibited by CLAUDE.md §10.6") and halt.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No `concept_refinement_summary.json` written.

**Hard failure confirmation:** Yes — alignment judgments must be grounded in Tier 2B source files; prior knowledge cannot substitute.

**CLAUDE.md §13 cross-reference:** §13.9 — generic programme knowledge may not substitute for Tier 2B source documents. §10.5 — every material claim must identify its Tier 1–4 source.

---

### Constraint 2: "Uncovered expected outcomes must be flagged, not silently assumed covered"

**Decision point in execution logic:** Step 2.5 and Step 2.10 — at the point `topic_mapping_rationale` is built and the decision log entry's `uncovered_outcomes` list is compiled.

**Exact failure condition:** Any expected outcome entry from `expected_outcomes.json` is absent from the `topic_mapping_rationale` output (i.e., no entry exists for its `outcome_id`). OR: an expected outcome entry is present but has `status: "Assumed"` or `status: "Unresolved"` without being listed in the decision log entry's `uncovered_outcomes` array.

**Enforcement mechanism:** In Step 2.5, every `outcome_id` from `expected_outcomes.json` must have a corresponding entry in `topic_mapping_rationale` — no omissions permitted. The `uncovered_outcomes` list in the decision log entry (Step 2.10) must include every outcome_id with status Assumed or Unresolved.

DETERMINISTIC COMPLETENESS CHECK:
AT output construction time, before writing `concept_refinement_summary.json`:
- Build set A = {outcome_id for all entries in expected_outcomes.json}
- Build set B = {topic_element_id for all entries in topic_mapping_rationale}
- IF A ≠ B (any element in A missing from B): INCOMPLETE_OUTPUT — halt immediately
→ return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Expected outcome <outcome_id> from expected_outcomes.json has no entry in topic_mapping_rationale; uncovered outcomes must be explicitly flagged per CLAUDE.md §12.4 and §13.7")
→ No output written

Silently omitting an uncovered outcome is a constitutional violation equivalent to fabricated completion.

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). No output written.

**Hard failure confirmation:** Yes — every expected outcome must appear in the mapping rationale; omission is a constitutional violation.

**CLAUDE.md §13 cross-reference:** §12.4 — "Missing mandatory inputs must trigger a gate failure; they must not be papered over by hallucinated completion, generic programme knowledge, or optimistic inference." §15 — "The system must prefer explicit gate failure over fabricated completion."

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier3_project_instantiation/project_brief/` directory is empty → `failure_reason="project_brief/ directory is empty; concept alignment cannot proceed without project concept text"`
- Step 1.2: `expected_outcomes.json` does not exist → `failure_reason="expected_outcomes.json not found; call-requirements-extraction must run before concept-alignment-check"`
- Step 1.3: `expected_outcomes.json` contains zero entries → `failure_reason="expected_outcomes.json is empty; cannot check alignment without expected outcome definitions"`
- Step 1.5: No readable files found in `project_brief/` → `failure_reason="project_brief/ contains no readable concept documents"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill reads from Tier 3 source directories and Tier 2B extracted artifact files (not structured canonical artifacts with schema_id). No MALFORMED_ARTIFACT conditions are defined; input absence is handled by MISSING_INPUT.

**Artifact write behavior:** Not applicable for this skill.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use CONSTITUTIONAL_HALT or INCOMPLETE_OUTPUT as appropriate.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 2 (uncovered expected outcomes explicitly flagged): At output construction time, any `outcome_id` from `expected_outcomes.json` is absent from `topic_mapping_rationale` (set A ≠ set B in the deterministic completeness check) → `failure_reason="Expected outcome <outcome_id> from expected_outcomes.json has no entry in topic_mapping_rationale; uncovered outcomes must be explicitly flagged per CLAUDE.md §12.4 and §13.7"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 1 (alignment tested against Tier 2B extracted files): The skill cannot perform any Tier 2B-grounded alignment evaluation; any expected outcome entry is assigned `status: "Confirmed"` or `"Inferred"` without both `tier2b_source_ref` and `tier3_evidence_ref` populated from actual source data → `failure_reason="Alignment evaluation cannot be performed without Tier 2B extracted files; assuming alignment from concept vocabulary alone is prohibited by CLAUDE.md §10.6"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No `concept_refinement_summary.json` written. A decision log entry MAY be written to `docs/tier4_orchestration_state/decision_log/` documenting the constitutional halt, as `decision_log/` is in this skill's declared `writes_to` scope.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: this skill's `writes_to` includes `docs/tier4_orchestration_state/decision_log/`; a failure record MAY be written there even when the primary output fails.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Validates output construction against artifact_schema_specification.yaml.*

---

### Canonical Artifact: `concept_refinement_summary.json`

**Schema ID verified:** `orch.phase2.concept_refinement_summary.v1` ✓

**Required fields checked:**

| Field | Required | Status | Notes |
|-------|----------|--------|-------|
| schema_id | true | ✓ Implemented | Set to "orch.phase2.concept_refinement_summary.v1" in Step 3 and Step 4 |
| run_id | true | ✓ Implemented | Propagated from invoking agent run_id |
| artifact_status | false | ✓ Absent at write time | Runner-stamped post-gate |
| topic_mapping_rationale | true | ✓ Implemented | Built in Step 2.5 with topic_element_id, mapping_to_concept, tier2b_source_ref, tier3_evidence_ref per entry |
| scope_conflict_log | true | ✓ Implemented | Built in Step 2.8 with conflict_id, description, resolution_status (enum), resolution_note (when resolved), tier2b_source_ref |
| strategic_differentiation | true | ✓ Implemented | Built in Step 2.9 — non-empty string |

**Reads_from compliance:** All output fields derived from declared reads_from sources (project_brief/, expected_outcomes.json, scope_requirements.json). No external fields introduced.

**Corrections applied:** None. Output Construction already lists every required schema field with correct schema_id and enum-compliant resolution_status values.

---

### Secondary Output: decision_log/ entry

*Validation status vocabulary check:* Confirmed/Inferred/Assumed/Unresolved vocabulary per CLAUDE.md §12.2 is used in Step 2.4 for outcome alignment status assignment, and propagated into the decision log entry's `alignment_findings` summary. The decision log entry includes `decision_id`, `decision_type`, `tier_authority_applied`, `resolution_status`, and ISO 8601 `timestamp`, conforming to decision-log-update structure.

### Tier 3 Artifact: `topic_mapping.json`

**Canonical schema in `artifact_schema_specification.yaml`:** Section 6.2 — `tier3_source_schemas.topic_mapping`.

**Schema governance:** Tier 3 source artifact (`provenance_class: manually_placed`). No `schema_id`, `run_id`, or `artifact_status` fields.

**Required fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `mappings` | Yes (Step 2.11) | array, required: true; each item: topic_element_id, tier2b_source_ref, tier3_evidence_ref, mapping_description | Yes — derived 1:1 from topic_mapping_rationale entries |

**Validation rule:** `mappings` array must be non-empty. An empty array or missing field constitutes INCOMPLETE_OUTPUT.

---

### Tier 3 Artifact: `compliance_profile.json`

**Canonical schema in `artifact_schema_specification.yaml`:** Section 6.3 — `tier3_source_schemas.compliance_profile`.

**Schema governance:** Tier 3 source artifact (`provenance_class: manually_placed`). No `schema_id`, `run_id`, or `artifact_status` fields.

**Required fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `eligibility_confirmed` | Yes (Step 2.12) | boolean, required: true | Yes |
| `ethics_review_required` | Yes (Step 2.12) | boolean, required: true | Yes |
| `gender_plan_required` | Yes (Step 2.12) | boolean, required: true | Yes |
| `open_science_requirements` | Yes (Step 2.12) | array of strings, required: true | Yes — may be empty `[]` |

**Validation rule:** All four required fields must be present. Missing any field constitutes INCOMPLETE_OUTPUT.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
