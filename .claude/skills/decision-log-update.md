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

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
