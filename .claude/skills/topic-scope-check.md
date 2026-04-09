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

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
