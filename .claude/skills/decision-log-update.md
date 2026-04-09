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

<!-- BODY: Execution specification — to be completed in Step 5 (execution logic) -->
<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
