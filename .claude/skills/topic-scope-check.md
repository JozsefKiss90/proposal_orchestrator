---
skill_id: topic-scope-check
purpose_summary: >
  Verify that a project concept or proposal section is within the thematic scope
  defined by Tier 2B scope requirements, and flag any out-of-scope claims to the
  decision log.
used_by_agents:
  - call_analyzer
  - concept_refiner
reads_from:
  - docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json
  - docs/tier2b_topic_and_call_sources/extracted/call_constraints.json
writes_to:
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Scope boundary is defined by Tier 2B only; must not infer scope from generic programme knowledge"
  - "Out-of-scope flags must be written to decision log"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` | scope_requirements.json — Tier 2B extracted | Scope boundary entries; scope element descriptions; source_section; source_document; status (Confirmed/Inferred/Assumed/Unresolved) | N/A — Tier 2B extracted artifact | Defines the authoritative thematic scope boundary against which the project concept or proposal section is checked; any claim outside these boundaries is out-of-scope |
| `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | call_constraints.json — Tier 2B extracted | Constraint entries; constraint descriptions; source_section; source_document; status | N/A — Tier 2B extracted artifact | Provides call-specific constraints (e.g., excluded activities, mandatory approaches) that supplement scope boundaries; used to identify constraint violations |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/decision_log/` | Per-invocation decision log entry file (e.g., `scope_check_<timestamp>.json`) | N/A — decision log entry (no canonical schema_id in artifact_schema_specification.yaml for individual decision log entries) | decision_id; decision_type: "scope_check"; invoking_agent; phase_context; scope_findings array (claim, scope_element_ref, status: in_scope/out_of_scope/flagged); tier2b_source_refs; resolution_status; timestamp | No — decision log entries are not phase output canonical artifacts | Out-of-scope findings derived from comparison of the concept/section text against scope_requirements.json and call_constraints.json entries; every flagged claim must reference the Tier 2B scope element that defines the boundary |

**Note:** The decision log directory is not a canonical artifact with a schema_id. Entries are written as individual files per invocation. The directory path `docs/tier4_orchestration_state/decision_log/` is not directly registered in the artifact_registry as a single artifact; individual entries are written there by convention.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry. Decision log is a durable output directory used by multiple agents across phases; not tied to a single producing node. | Multiple nodes (context-dependent: n01_call_analysis or n02_concept_refinement per invoking agent) |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="scope_requirements.json not found; call-requirements-extraction must run before topic-scope-check") and halt.
- Step 1.2: Non-empty check — confirm `scope_requirements.json` contains at least one entry. If empty: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="scope_requirements.json is empty; cannot evaluate scope without scope boundary definitions") and halt.
- Step 1.3: Presence check — confirm `docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` exists. If absent: log as Assumed (constraint checking skipped); continue without call_constraints data.
- Step 1.4: Confirm the invoking agent has provided the content to check as context (the text of the project concept or proposal section being evaluated). If no content is provided: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="No content provided for scope checking; invoking agent must supply concept or section text as context") and halt.

### 2. Core Processing Logic

- Step 2.1: Build the **scope boundary set** from `scope_requirements.json`: a list of scope boundary entries, each with `scope_element_id`, `description`, `boundary_type` (required_focus / excluded_topic / conditional_requirement), and `source_section`.
- Step 2.2: Build the **constraint set** from `call_constraints.json` (if present): a list of constraint entries, each with `constraint_id`, `description`, `source_section`.
- Step 2.3: Decompose the provided content (concept or section text) into individual **claims**. A claim is any assertion that: (a) describes a project activity or topic focus, (b) references a technology, domain, or methodology, or (c) states an objective or intended outcome. Each claim is a discrete textual fragment that can be evaluated independently against the scope boundary set.
- Step 2.4: For each claim, evaluate it against every scope boundary entry as follows:
  - **in_scope**: The claim's topic or activity matches or is a specific instance of a `required_focus` boundary entry, AND does not conflict with any `excluded_topic` boundary entry. Status = in_scope.
  - **out_of_scope**: The claim's topic or activity matches an `excluded_topic` boundary entry, OR the claim is about a topic not covered by any `required_focus` boundary entry AND is not a natural extension of any `required_focus` entry. Status = out_of_scope. Flag required.
  - **flagged**: The claim is borderline — it partially overlaps with a `required_focus` entry but also partially overlaps with an `excluded_topic` entry, OR the relevant scope boundary entry has status "Unresolved" in scope_requirements.json, OR the claim could be interpreted either way depending on project framing. Status = flagged. Must record `flag_reason` explaining the ambiguity and naming the specific `scope_element_id` involved.
- Step 2.5: For each claim not flagged as out_of_scope, evaluate it against the constraint set (if available): check whether the claim asserts an activity explicitly excluded by any constraint entry. If so: override status to out_of_scope and add `constraint_ref` to the finding.
- Step 2.6: Build the `scope_findings` array: one entry per claim, containing: `claim` (the claim text), `scope_element_ref` (the `scope_element_id` from scope_requirements.json that is most relevant to this claim, or null if no match), `constraint_ref` (the `constraint_id` from call_constraints.json if applicable, otherwise null), `status` (in_scope / out_of_scope / flagged), `flag_reason` (non-empty string when status is out_of_scope or flagged; null otherwise).
- Step 2.7: Determine the overall `resolution_status` for this invocation: if any finding has status out_of_scope or flagged: resolution_status = "unresolved". If all findings have status in_scope: resolution_status = "resolved".
- Step 2.8: Collect all `tier2b_source_refs`: unique list of `source_section` values from scope_requirements.json entries consulted during this evaluation.

### 3. Output Construction

**Decision log entry file (e.g., `scope_check_<agent_id>_<ISO8601_timestamp>.json`):**
- `decision_id`: string — `"scope_check_<agent_id>_<ISO8601_timestamp>"`
- `decision_type`: string — `"scope_check"`
- `invoking_agent`: string — derived from agent context parameter
- `phase_context`: string — derived from agent context parameter (e.g., "phase_01_call_analysis" or "phase_02_concept_refinement")
- `scope_findings`: array — derived from Step 2.6 — each entry: `{claim, scope_element_ref, constraint_ref, status, flag_reason}`
- `tier2b_source_refs`: array of strings — derived from Step 2.8 — unique source_section values consulted
- `tier_authority_applied`: string — must reference the specific Tier 2B source files used as the scope boundary authority (e.g., "Tier 2B scope_requirements.json; Tier 2B call_constraints.json"); generic strings are not acceptable; required per CLAUDE.md §9.4 and decision-log-update skill contract
- `resolution_status`: string — derived from Step 2.7 — one of "resolved" / "unresolved"
- `timestamp`: string — ISO 8601 timestamp of this invocation

### 4. Conformance Stamping

Decision log entries are not phase output canonical artifacts. No `schema_id`, `run_id`, or `artifact_status` field applies.

### 5. Write Sequence

- Step 5.1: Write the decision log entry file to `docs/tier4_orchestration_state/decision_log/<decision_id>.json`
- The filename must match the `decision_id` value exactly.

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Scope boundary is defined by Tier 2B only; must not infer scope from generic programme knowledge"

**Decision point in execution logic:** Steps 2.1–2.5 — at the point scope boundary entries are built and used to evaluate each claim. The boundary set must be constructed exclusively from `scope_requirements.json` and `call_constraints.json`.

**Exact failure condition:** (a) The scope boundary set used for evaluation contains entries not sourced from `scope_requirements.json` or `call_constraints.json` — i.e., entries constructed from agent prior knowledge of what the call "typically" requires; OR (b) any claim is marked `in_scope` based on a generic programme-level judgment (e.g., "this topic is generally within Horizon Europe scope") rather than a match against a specific Tier 2B `scope_element_id`.

**Enforcement mechanism:** Every `scope_element_ref` in the `scope_findings` array must reference a `scope_element_id` from `scope_requirements.json` or a `constraint_id` from `call_constraints.json`. Any claim evaluated as `in_scope` without a matching `scope_element_ref` from the loaded Tier 2B data must instead be assigned `status: "flagged"` with `flag_reason: "No Tier 2B scope element found to confirm this claim is in-scope; scope boundary is defined by Tier 2B only"`. If the skill cannot evaluate any claim without relying on prior programme knowledge: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="Scope evaluation requires Tier 2B source data; inferring scope from generic programme knowledge is prohibited by CLAUDE.md §13.2 and §13.9") and halt.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT"). No decision log entry written.

**Hard failure confirmation:** Yes — scope boundary is exclusively Tier 2B; prior knowledge cannot expand or substitute for it.

**CLAUDE.md §13 cross-reference:** §13.2 — "Inventing call constraints, scope requirements, expected outcomes, or expected impacts not present in Tier 2B source documents." §13.9 — "Using agent-local knowledge … as a substitute for reading Tier 1 source documents."

---

### Constraint 2: "Out-of-scope flags must be written to decision log"

**Decision point in execution logic:** Step 5.1 — at the point the decision log entry is written. The decision log entry must be written for every invocation where `resolution_status = "unresolved"` (i.e., at least one out-of-scope or flagged finding exists).

**Exact failure condition:** The skill invocation identifies one or more out-of-scope or flagged claims (resolution_status = "unresolved") but does NOT write a decision log entry to `docs/tier4_orchestration_state/decision_log/`.

**Enforcement mechanism:** In Step 5.1, if `resolution_status = "unresolved"`, the decision log entry write is not optional — it is mandatory. If the write fails for any reason (e.g., directory not accessible): return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Decision log entry could not be written; out-of-scope flags must be persisted to the decision log per skill constitutional constraints and CLAUDE.md §9.4") and halt. An invocation that returns `status="success"` without having written the decision log entry when unresolved flags exist is a constitutional violation.

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT") if decision log write fails.

**Hard failure confirmation:** Yes — the decision log write for unresolved scope flags is not advisory; it is mandatory per CLAUDE.md §9.4.

**CLAUDE.md §13 cross-reference:** §13.5 (analogous) — "Storing durable decisions only in agent memory without writing them to Tier 4." §9.4 — "Every decision that affects future interpretation, traceability, or reproducibility must be written to the decision log."

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` is absent → `failure_reason="scope_requirements.json not found; call-requirements-extraction must run before topic-scope-check"`
- Step 1.2: `scope_requirements.json` contains zero entries → `failure_reason="scope_requirements.json is empty; cannot evaluate scope without scope boundary definitions"`
- Step 1.4: Invoking agent has not provided concept or section text as context → `failure_reason="No content provided for scope checking; invoking agent must supply concept or section text as context"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill reads from Tier 2B extracted artifact files (not structured canonical artifacts with schema_id). No MALFORMED_ARTIFACT conditions are defined; input absence is handled by MISSING_INPUT.

**Artifact write behavior:** Not applicable for this skill.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use CONSTITUTIONAL_HALT or INCOMPLETE_OUTPUT as appropriate.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 2 (out-of-scope flags written to decision log): The skill identifies out-of-scope or flagged claims (`resolution_status = "unresolved"`) but the decision log write at Step 5.1 fails → `failure_reason="Decision log entry could not be written; out-of-scope flags must be persisted to the decision log per skill constitutional constraints and CLAUDE.md §9.4"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 1 (scope boundary defined by Tier 2B only): The skill cannot evaluate any claim without relying on prior programme knowledge as the scope boundary; scope boundary set cannot be constructed from Tier 2B sources → `failure_reason="Scope evaluation requires Tier 2B source data; inferring scope from generic programme knowledge is prohibited by CLAUDE.md §13.2 and §13.9"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No decision log entry written. A decision log entry MAY be written to `docs/tier4_orchestration_state/decision_log/` documenting the constraint violation, as `decision_log/` is in this skill's declared `writes_to` scope.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: this skill's `writes_to` includes `docs/tier4_orchestration_state/decision_log/`; a failure record MAY be written there even when the primary output fails.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. This is a Group C skill whose sole output is a decision log entry file in `docs/tier4_orchestration_state/decision_log/`. There is no canonical `schema_id` in `artifact_schema_specification.yaml` for individual decision log entries; conformance is governed by CLAUDE.md §9.4 (durable decision logging) and §12.2 (validation status vocabulary).*

---

### Artifact: `scope_check_<agent_id>_<ISO8601_timestamp>.json` (decision log entry)

**Canonical schema in `artifact_schema_specification.yaml`:** None — decision log entries are operational artifacts not defined in the schema registry. Conformance is governed by (a) CLAUDE.md §12.2 status vocabulary, (b) skill-defined decision log entry fields, and (c) consistency with upstream Tier 2B field names.

**Output Construction fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `decision_id` | Yes (Step 3) | skill-defined | Yes |
| `decision_type` | Yes — "scope_check" | skill-defined | Yes |
| `invoking_agent` | Yes | agent context | Yes |
| `phase_context` | Yes | agent context | Yes |
| `scope_findings[]` | Yes (Step 2.6, Step 3) | each finding: claim, scope_element_ref, constraint_ref, status, flag_reason | Yes — status values (in_scope/out_of_scope/flagged) are deterministic per Step 2.4 |
| `tier2b_source_refs` | Yes | unique source_section list | Yes |
| `tier_authority_applied` | Yes | explicit Tier 2B file references | Yes |
| `resolution_status` | Yes | enum: resolved/unresolved | Yes |
| `timestamp` | Yes | ISO 8601 | Yes |

**CLAUDE.md §12.2 vocabulary compliance:** The skill's `resolution_status` values (resolved/unresolved) are operational status for scope findings, not the §12.2 validation status enum. This is consistent with §12.2, which applies to validation reports, not to the scope-check decision log entries. Individual scope findings use in_scope/out_of_scope/flagged per skill contract — these are the scope-specific status vocabulary, not a substitution for the §12.2 enum. No conflict.

**Upstream Tier 2B field-name alignment (cross-skill consistency):** The skill reads `scope_requirements.json`, whose spec (`tier2b_extracted_schemas.scope_requirements`) uses root `requirements[]` with item id `requirement_id` and boolean `mandatory`. The skill's Step 2.1 refers to `scope_element_id` and `boundary_type` — legacy terminology that predates the spec alignment corrections in call-requirements-extraction. The `scope_element_ref` field in the decision log entry is a back-pointer: its value must reference the id field as it appears in the upstream Tier 2B file, which per spec is `requirement_id`. Cross-skill consistency is preserved by interpreting `scope_element_ref` as holding a `requirement_id` value.

**Gap identified:** Step 2.1 and §2.4 of this skill use legacy field names (`scope_element_id`, `boundary_type`, enum `required_focus/excluded_topic/conditional_requirement`) inconsistent with the spec (`requirement_id`, boolean `mandatory`). This is an execution-logic gap, not an Output Construction gap — per Step 8 task scope, Output Construction corrections take minimal form only. The downstream decision log entry field `scope_element_ref` is documented here as carrying the upstream `requirement_id` value. Execution logic steps 2.1 and 2.4 should be reconciled in a future skill-logic update; flagged here for traceability without modifying the execution specification.

**Correction applied to Output Construction:** None — Output Construction fields are conformant with decision log entry conventions. The upstream naming gap is documented as a known future reconciliation item.

**reads_from compliance:** Reads from `docs/tier2b_topic_and_call_sources/extracted/scope_requirements.json` and `call_constraints.json`. Both declared in frontmatter. Compliant.

**writes_to compliance:** Writes only to `docs/tier4_orchestration_state/decision_log/`. Declared in frontmatter. Compliant.

<!-- Step 8 complete: schema validation performed -->
