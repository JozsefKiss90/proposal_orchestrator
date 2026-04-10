---
skill_id: decision-log-update
purpose_summary: >
  Write a durable decision record to the Tier 4 decision log, capturing the decision
  taken, alternatives considered, the tier authority applied, and the rationale,
  whenever a material interpretation is made or a conflict is resolved.
used_by_agents:
  - concept_refiner
  - wp_designer
  - gantt_designer
  - impact_architect
  - implementation_architect
  - budget_gate_validator
  - revision_integrator
  - state_recorder
  - compliance_validator
  - traceability_auditor
reads_from:
  - "Any phase context requiring durable recording"
writes_to:
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Decisions held only in agent memory do not constitute durable decisions"
  - "Every resolved tier conflict must produce a decision log entry"
  - "Decision log entries must identify the tier authority applied"
---

## Canonical Inputs and Outputs

### Inputs

This skill has contextual inputs. The `reads_from` in the skill catalog is defined as "Any phase context requiring durable recording" — meaning there is no single structured artifact that this skill validates before writing. The inputs are the agent's in-context decision state at the point of invocation.

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| Any phase context requiring durable recording | The agent's current decision state: the decision taken, alternatives considered, the tier authority applied, and the rationale | Decision description; alternatives considered; tier authority reference (e.g., "CLAUDE.md §10.4", "Tier 2B scope_requirements.json"); rationale; invoking phase; agent identity | N/A — contextual; no structured artifact validation applies | Source of all fields written to the decision log entry; the agent constructs the entry from its current interpretation context, not from reading a structured input artifact |

**Constitutional basis:** CLAUDE.md §9.4 requires that every decision affecting future interpretation, traceability, or reproducibility be written to the decision log. This skill is the mechanism for that requirement.

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/decision_log/` | Per-invocation decision log entry file (naming convention: `<decision_type>_<agent_id>_<timestamp>.json`) | N/A — decision log entries do not have a canonical schema_id in artifact_schema_specification.yaml | decision_id (unique); decision_type (e.g., "scope_check", "concept_alignment", "wp_design_choice", "gate_failure", "tier_conflict_resolution", "constitutional_violation"); invoking_agent; phase_context; decision_description (non-empty); alternatives_considered (array, may be empty); tier_authority_applied (non-empty — must name a specific CLAUDE.md section or tier source); rationale (non-empty); resolution_status[resolved/unresolved]; timestamp (ISO 8601) | No — decision log entries are not phase output canonical artifacts | All fields derived from the invoking agent's current interpretation context; tier_authority_applied must reference a named authority (not generic); every resolved tier conflict requires an entry |

**Note:** Decision log entries are durable records required by CLAUDE.md §9.4. They are not canonical phase output artifacts and do not carry schema_id or run_id in the artifact_schema_specification.yaml sense. However, the run_id_reference field (referencing the current DAG runner run_id) should be included for traceability. Decisions held only in agent memory without a corresponding entry here do not constitute durable decisions.

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent: n02 through n08d per invoking agent) |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Confirm the invoking agent provides the following context parameters. All are required; any absent parameter is a failure:
  - `decision_description` (string, non-empty): what decision was made.
  - `tier_authority_applied` (string, non-empty): must name a specific authority — a CLAUDE.md section reference (e.g., "CLAUDE.md §9.4"), a tier file reference (e.g., "Tier 2B expected_outcomes.json"), or a phase gate reference (e.g., "phase_03_gate condition"). Generic strings like "standard practice" or "programme knowledge" are not acceptable tier authority references.
  - `rationale` (string, non-empty): why this decision was made.
  - `decision_type` (string): the decision category. Must be one of: "scope_check", "concept_alignment", "wp_design_choice", "gate_failure", "tier_conflict_resolution", "constitutional_violation", "gap_risk_flagged", "uncovered_expected_impact", "traceability_gap", "budget_gate_failure".
  - `invoking_agent` (string, non-empty): the agent_id making this invocation.
  - `phase_context` (string, non-empty): the phase in which this decision is being recorded (e.g., "phase_02_concept_refinement").
- Step 1.2: If `decision_description` is empty or null: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="decision_description must be non-empty") and halt.
- Step 1.3: If `tier_authority_applied` is empty, null, or contains only generic strings (does not reference a named document, section, or tier): return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="tier_authority_applied must reference a specific named authority; generic strings are not acceptable") and halt.
- Step 1.4: If `rationale` is empty or null: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="rationale must be non-empty") and halt.

### 2. Core Processing Logic

- Step 2.1: Generate `decision_id` as: `"<decision_type>_<agent_id>_<ISO8601_timestamp>"`. Use a full ISO 8601 timestamp with seconds (e.g., "concept_alignment_concept_refiner_2026-04-09T14:30:00Z"). Replace colons in the timestamp with hyphens for safe filename use (e.g., "2026-04-09T14-30-00Z").
- Step 2.2: Set `resolution_status`. If the invoking agent provides a `resolution_status` context parameter: use that value (must be "resolved" or "unresolved"). If not provided: default to "unresolved" for decision_types: "gate_failure", "constitutional_violation", "uncovered_expected_impact", "traceability_gap"; default to "resolved" for all others.
- Step 2.3: Collect `alternatives_considered`. If the invoking agent provides an `alternatives_considered` array in context: use it (may be empty array). If not provided: use empty array `[]`.
- Step 2.4: Set `run_id_reference`. If the invoking agent provides a `run_id` in context: include it as `run_id_reference`. If not provided: set to null.
- Step 2.5: Construct the complete decision log entry JSON object with all required fields.
- Step 2.6: Determine output filename: `"<decision_id>.json"` where decision_id is from Step 2.1 (with hyphens replacing colons in the timestamp portion).

### 3. Output Construction

**Decision log entry file (`<decision_id>.json`):**
- `decision_id`: derived from Step 2.1 — `"<decision_type>_<agent_id>_<ISO8601_timestamp_safe>"`
- `decision_type`: from agent context parameter — one of the enumerated types
- `invoking_agent`: from agent context parameter
- `phase_context`: from agent context parameter
- `run_id_reference`: from agent context or null
- `decision_description`: from agent context parameter — must be non-empty
- `alternatives_considered`: from agent context or `[]`
- `tier_authority_applied`: from agent context parameter — must reference a named authority
- `rationale`: from agent context parameter — must be non-empty
- `resolution_status`: derived from Step 2.2 — "resolved" or "unresolved"
- `timestamp`: ISO 8601 timestamp of entry creation (at write time)

### 4. Conformance Stamping

Decision log entries are not phase output canonical artifacts. No `schema_id`, `run_id` (as a top-level required field), or `artifact_status` applies. The `run_id_reference` field is included for traceability but is not a gate-evaluated field.

### 5. Write Sequence

- Step 5.1: Write the decision log entry to `docs/tier4_orchestration_state/decision_log/<decision_id>.json`
- The target directory must exist; create it if absent.
- The filename must exactly match `<decision_id>.json`.

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Decisions held only in agent memory do not constitute durable decisions"

**Decision point in execution logic:** Step 5.1 — at the point the decision log entry is written. The constraint enforces that writing actually occurs, not that a decision was made.

**Exact failure condition:** The skill is invoked with valid parameters (all input validation passes) but the decision log file write at Step 5.1 fails or is not attempted — meaning the decision exists in agent context but has not been persisted to `docs/tier4_orchestration_state/decision_log/`.

**Enforcement mechanism:** In Step 5.1, the file write is the constitutionally required action. If the write fails for any reason (directory inaccessible, file system error, permission denied): return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Decision log entry <decision_id> could not be written to docs/tier4_orchestration_state/decision_log/; decisions held only in agent memory do not constitute durable decisions per CLAUDE.md §9.4. Write must be retried or the operator must be notified of the write failure.") and halt. A SkillResult(status="success") may only be returned AFTER confirming the file has been written and is readable at the target path. Returning success without a confirmed write is a constitutional violation — the decision would remain only in agent memory.

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). No success returned until file write is confirmed.

**Hard failure confirmation:** Yes — an unwritten decision log entry is a constitutional violation regardless of how well-formed the decision content is.

**CLAUDE.md §13 cross-reference:** §13.5 — "Storing durable decisions only in agent memory without writing them to Tier 4." §9.4 — "Every decision that affects future interpretation, traceability, or reproducibility must be written to docs/tier4_orchestration_state/decision_log/ … Decisions held only in agent memory do not constitute durable decisions."

---

### Constraint 2: "Every resolved tier conflict must produce a decision log entry"

**Decision point in execution logic:** Step 1.1 — the decision_type validation; specifically when `decision_type = "tier_conflict_resolution"` is provided by the invoking agent.

**Exact failure condition:** The invoking agent calls this skill with `decision_type: "tier_conflict_resolution"` but: (a) `decision_description` does not describe which tiers were in conflict and which prevailed; OR (b) `tier_authority_applied` does not identify the tier that governed the resolution (e.g., "CLAUDE.md §3 — Tier 2B governs over Tier 3 in this conflict").

**Enforcement mechanism:** In Step 1.3, the `tier_authority_applied` validation is especially strict for `decision_type: "tier_conflict_resolution"`. For this decision type: `tier_authority_applied` must reference both the conflicting tiers and the governing authority (either "CLAUDE.md §3" or a specific tier document). A generic string like "programme knowledge" or "best practice" is always rejected. Additionally, in Step 1.2, for `decision_type: "tier_conflict_resolution"`: `decision_description` must contain at minimum: the name of the two tiers in conflict AND the specific issue. If either validation fails: return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="Tier conflict resolution entry missing tier identification or authority reference; every resolved tier conflict must produce a complete decision log entry per CLAUDE.md §12.3"). No entry written.

**Failure output:** SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT"). No entry written.

**Hard failure confirmation:** Yes — a tier conflict resolution without naming the tiers and authority is an incomplete record that does not constitute a durable decision.

**CLAUDE.md §13 cross-reference:** §12.3 — "Contradictions between tiers must be resolved explicitly. The resolution method, the tier that prevailed, and the reasoning must be recorded in the decision log. A contradiction must not be silently resolved by selecting the more convenient source."

---

### Constraint 3: "Decision log entries must identify the tier authority applied"

**Decision point in execution logic:** Step 1.3 — the `tier_authority_applied` validation before entry construction begins.

**Exact failure condition:** `tier_authority_applied` is empty, null, or contains only a generic string that does not reference: (a) a named CLAUDE.md section (e.g., "CLAUDE.md §9.4"), (b) a named tier document (e.g., "Tier 2B scope_requirements.json"), or (c) a named gate or phase reference (e.g., "phase_03_gate condition from CLAUDE.md §7"). Strings like "standard practice", "programme knowledge", "general requirement", or "common sense" are explicitly rejected.

**Enforcement mechanism:**

DETERMINISTIC VALIDATION RULE:
Acceptable `tier_authority_applied` values MUST match at least one of:
- Pattern A: starts with "CLAUDE.md §" followed by a section number
- Pattern B: starts with "Tier " followed by a tier number or name and a specific document reference
- Pattern C: starts with "phase_" or "gate_" followed by a phase/gate identifier

IF `tier_authority_applied` does not match any pattern: MALFORMED_ARTIFACT immediately
→ return SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason="tier_authority_applied '<value>' does not reference a specific named authority; decision log entries must identify the tier authority applied per CLAUDE.md §9.4 and §12.2. Must reference a CLAUDE.md section, tier document, or gate condition.")
→ No entry is constructed

IF `tier_authority_applied` matches a pattern but contains only "programme knowledge", "standard practice", "common sense", or "general requirement" as the sole justification: MALFORMED_ARTIFACT

This validation fires before any other processing and cannot be bypassed.

**Failure output:** SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT"). No entry written. No further steps executed.

**Hard failure confirmation:** Yes — an entry without a named tier authority does not fulfil the constitutional requirement of CLAUDE.md §9.4 and may not be written.

**CLAUDE.md §13 cross-reference:** §9.4 — "Every decision that affects future interpretation, traceability, or reproducibility must be written to the decision log." Traceability requires naming the authority. §12.2 — "Confirmed — directly evidenced by a named source in Tier 1–3; the source artifact must be named." The same naming principle applies to decision records.

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.2: `decision_description` context parameter is empty or null → `failure_reason="decision_description must be non-empty"`
- Step 1.4: `rationale` context parameter is empty or null → `failure_reason="rationale must be non-empty"`
- Step 1.1: Any other required context parameter (`invoking_agent`, `phase_context`) is absent → `failure_reason="<parameter_name> must be non-empty"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
- Step 1.3: `tier_authority_applied` does not match any of the acceptable patterns (does not start with "CLAUDE.md §", "Tier ", "phase_", or "gate_"); OR contains only generic strings ("standard practice", "programme knowledge", "general requirement", "common sense") → `failure_reason="tier_authority_applied '<value>' does not reference a specific named authority; decision log entries must identify the tier authority applied per CLAUDE.md §9.4 and §12.2"`
- Step 1.1: `decision_type` is not one of the enumerated valid types → `failure_reason="decision_type '<value>' is not a valid decision type"`
- Constraint 2 (tier conflict resolution): For `decision_type: "tier_conflict_resolution"`, `decision_description` does not name both conflicting tiers and the specific issue; or `tier_authority_applied` does not reference both conflicting tiers and the governing authority → `failure_reason="Tier conflict resolution entry missing tier identification or authority reference; every resolved tier conflict must produce a complete decision log entry per CLAUDE.md §12.3"`

**Required response:** `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT", failure_reason=<specific reason>)`

**Artifact write behavior:** No canonical artifact written. Skill halts immediately.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use INCOMPLETE_OUTPUT or MALFORMED_ARTIFACT as appropriate.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 1 (decisions written to decision log, not held in agent memory): The decision log file write at Step 5.1 fails for any reason — the decision is not persisted → `failure_reason="Decision log entry <decision_id> could not be written to docs/tier4_orchestration_state/decision_log/; decisions held only in agent memory do not constitute durable decisions per CLAUDE.md §9.4. Write must be retried or the operator must be notified of the write failure."`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before returning success.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
No CONSTITUTIONAL_HALT conditions are defined for this skill. The skill's constitutional constraint failures are handled via MALFORMED_ARTIFACT (malformed tier_authority reference) and INCOMPLETE_OUTPUT (write failure). This skill does not perform any operations that could trigger a §13 categorical prohibition halt.

**Artifact write behavior:** Not applicable.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: this skill's `writes_to` includes `docs/tier4_orchestration_state/decision_log/` — this IS the canonical output of this skill. When INCOMPLETE_OUTPUT fires because the write itself fails, no decision log entry is produced by definition.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Group C skill whose sole output is a decision log entry file in `docs/tier4_orchestration_state/decision_log/`. Decision log entries are not registered in the schema_id registry of `artifact_schema_specification.yaml`; conformance is governed by CLAUDE.md §9.4 (durable decision recording), §12.2 (validation status vocabulary), §12.3 (explicit conflict resolution), and §13.5 (no decisions held only in agent memory).*

---

### Artifact: `<decision_type>_<agent_id>_<timestamp>.json` (decision log entry)

**Canonical schema:** None — decision log entries are durable operational artifacts required by CLAUDE.md §9.4 but not included in the schema registry.

**Output Construction fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `decision_id` | Yes (Step 2.1, Step 3) | skill-defined unique id | Yes |
| `decision_type` | Yes | enum validated in Step 1.1: scope_check, concept_alignment, wp_design_choice, gate_failure, tier_conflict_resolution, constitutional_violation, gap_risk_flagged, uncovered_expected_impact, traceability_gap, budget_gate_failure | Yes — enforced via MALFORMED_ARTIFACT |
| `invoking_agent` | Yes | agent context, required | Yes |
| `phase_context` | Yes | agent context, required | Yes |
| `run_id_reference` | Yes (Step 2.4, Step 3) | optional agent context or null | Yes |
| `decision_description` | Yes | agent context, non-empty, enforced in Step 1.2 (MISSING_INPUT) | Yes |
| `alternatives_considered` | Yes (Step 2.3, Step 3) | agent context or [] | Yes |
| `tier_authority_applied` | Yes | agent context; must match Pattern A/B/C in Step 1.3 (MALFORMED_ARTIFACT enforced) | Yes — named-authority requirement satisfies §9.4 and §12.2 |
| `rationale` | Yes | agent context, non-empty, enforced in Step 1.4 (MISSING_INPUT) | Yes |
| `resolution_status` | Yes (Step 2.2, Step 3) | enum: resolved/unresolved; defaults by decision_type for gap/failure types | Yes — matches §12.2 Unresolved semantics |
| `timestamp` | Yes | ISO 8601 at write time | Yes |

**CLAUDE.md §9.4 compliance:** The skill's INCOMPLETE_OUTPUT protocol (Constraint 1) enforces that success is only returned after the file write is confirmed. This directly implements §13.5's prohibition on decisions held only in agent memory. Compliant.

**CLAUDE.md §12.2 vocabulary compliance:** `resolution_status` uses `{resolved, unresolved}` — a domain-specific binary that subsumes the §12.2 Unresolved state (mandatory for gate_failure, constitutional_violation, uncovered_expected_impact, traceability_gap). The per-decision `tier_authority_applied` field satisfies the §12.2 requirement that Confirmed evidence must name its source; here, every decision record names the authority under which the decision was taken. Compliant.

**CLAUDE.md §12.3 compliance:** For `decision_type: "tier_conflict_resolution"`, Constraint 2 enforces that `decision_description` must name both conflicting tiers and the issue, and `tier_authority_applied` must name the governing authority — implementing §12.3 ("The resolution method, the tier that prevailed, and the reasoning must be recorded in the decision log"). Compliant.

**`schema_id` / `artifact_status`:** Step 4 correctly states these do not apply to decision log entries. `run_id_reference` is an informational field, not the canonical `run_id` required by phase output schemas. Compliant.

**reads_from compliance:** The frontmatter declares `reads_from: "Any phase context requiring durable recording"` — reflecting that this skill takes no structured artifact input, only in-context decision state from the invoking agent. Consistent with the skill's purpose as a decision-recording mechanism. Compliant.

**writes_to compliance:** Writes only to `docs/tier4_orchestration_state/decision_log/`. Declared in frontmatter. Compliant.

**Gaps identified:** None.

**Corrections applied:** None.

<!-- Step 8 complete: schema validation performed -->
