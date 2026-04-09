---
skill_id: work-package-normalization
purpose_summary: >
  Normalize a work package structure to ensure each WP has all required elements:
  unique identifier, title, objective, tasks with identifiers, deliverables with due
  months and types, milestones with verifiable criteria, and a responsible lead.
used_by_agents:
  - wp_designer
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
constitutional_constraints:
  - "WP leads must be drawn from Tier 3 consortium data only"
  - "WP count must not exceed instrument limits from Tier 2A"
  - "Deliverables must have due months within project duration"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` | workpackage_seed.json — Tier 3 architecture input | Seed WP entries: wp_id, title, objectives (array), lead_partner, tasks array (task_id, title, responsible_partner), deliverables array (deliverable_id, title, type, due_month), dependencies array | N/A — Tier 3 source artifact | Provides the initial WP structure to be normalized; all WP identifiers, leads, tasks, and deliverables must originate from this file or Tier 3 consortium data |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | section_schema_registry.json — Tier 2A extracted | Active instrument entry: max_wp_count, max_deliverable_count, mandatory_wp_types, project_duration_months | N/A — Tier 2A extracted artifact | Provides structural constraints for the active instrument (maximum WP count, deliverable constraints, mandatory WP types) that the normalized structure must comply with |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | wp_structure.json | `orch.phase3.wp_structure.v1` | schema_id, run_id, work_packages (array: wp_id, title, objectives, lead_partner, contributing_partners, tasks[task_id, title, responsible_partner, contributing_partners], deliverables[deliverable_id, title, type, due_month, responsible_partner], dependencies[depends_on_wp_id, dependency_type, notes] per WP), dependency_map (object: nodes array, edges array[from, to, edge_type]), partner_role_matrix (array: partner_id, wps_as_lead, wps_as_contributor per partner) | Yes | work_packages derived from workpackage_seed.json normalized and validated against section_schema_registry.json constraints; dependency_map derived from dependencies arrays; partner_role_matrix derived from lead_partner and contributing_partners fields |

**Note:** `artifact_status` must be ABSENT at write time; the runner stamps it post-gate. WP leads must be validated against `docs/tier3_project_instantiation/consortium/partners.json` (read by the invoking agent, not directly listed in skill reads_from).

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | Yes — artifact_id: a_t4_phase3 (directory); canonical file within that directory | n03_wp_design |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Presence check — confirm `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="workpackage_seed.json not found; WP normalization requires a seed WP structure in Tier 3") and halt.
- Step 1.2: Non-empty check — confirm `workpackage_seed.json` is parseable JSON and contains at least one WP entry. If empty or unparseable: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="workpackage_seed.json is empty or invalid JSON") and halt.
- Step 1.3: Presence check — confirm `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` exists. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="section_schema_registry.json not found; instrument-schema-normalization must run before work-package-normalization") and halt.
- Step 1.4: Schema conformance check — read `section_schema_registry.json`; confirm it contains an entry for the `resolved_instrument_type` provided by the invoking agent. If the entry is missing: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="section_schema_registry.json has no entry for instrument type <resolved_instrument_type>") and halt.
- Step 1.5: Confirm the invoking agent has provided the consortium partner list as context (the `valid_partner_ids` set derived from `docs/tier3_project_instantiation/consortium/partners.json` — this file is read by the invoking agent, not directly by this skill, per the Output Note). If the partner list is not provided in context: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="valid_partner_ids not provided in context; the invoking agent must read partners.json and pass the partner_id set as context before invoking this skill") and halt. Build the **valid_partner_ids** set from the context-supplied partner list.

### 2. Core Processing Logic

- Step 2.1: Extract structural constraints from `section_schema_registry.json` for the active instrument: `max_wp_count` (integer or null), `max_deliverable_count` (integer or null), `project_duration_months` (integer or null).
- Step 2.2: Read all WP seed entries from `workpackage_seed.json`. Assign a canonical `wp_id` to each WP: if the seed entry already has a `wp_id` field that is a unique string, keep it. If missing or duplicate, assign a sequential identifier: "WP1", "WP2", ..., "WPn". Record any reassignments.
- Step 2.3: Validate WP count: count the total number of WP entries. If `max_wp_count` is not null and the count exceeds `max_wp_count`: return SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION", failure_reason="WP count <n> exceeds instrument limit <max_wp_count> from section_schema_registry.json") and halt. This is a hard constraint from Tier 2A.
- Step 2.4: For each WP entry, validate and normalise:
  - `objectives`: must be a non-empty array of strings. If missing or empty: this is a validation failure — record in a `normalization_issues` list but do not halt; the gate will fail on this WP.
  - `tasks`: must be a non-empty array. For each task: `task_id` must be present and unique across the whole WP structure. If `task_id` is missing, assign "T<wp_number>-<task_number>" (e.g., "T1-01"). `title` must be non-empty. `responsible_partner` must be a value in the valid_partner_ids set; if not: record a normalization_issue.
  - `deliverables`: must be a non-empty array. For each deliverable: `deliverable_id` must be present and unique. If missing, assign "D<wp_number>-<deliverable_number>". `type` must be one of [report, dataset, software, other]. `due_month` must be an integer ≥ 1; if `project_duration_months` is not null, `due_month` must be ≤ `project_duration_months`. If `due_month` exceeds `project_duration_months`: record a normalization_issue. `responsible_partner` must be in valid_partner_ids.
  - `lead_partner`: must be a value in the valid_partner_ids set. If not present or not a valid partner_id: record a normalization_issue (this will cause the Phase 3 gate to fail).
  - `dependencies`: must be an array (empty array is valid). For each entry: `depends_on_wp_id` must reference a wp_id that exists in the WP set. `dependency_type` must be one of [finish_to_start, start_to_start, data_input, partial_output].
- Step 2.5: Build the `dependency_map` object:
  - `nodes`: array containing all `wp_id` values plus all `task_id` values across all WPs.
  - `edges`: array of directed edges built from `dependencies[]` arrays. For each WP's `dependencies[]` array, for each entry: create an edge `{ from: depends_on_wp_id, to: current_wp_id, edge_type: dependency_type }`. At this stage, only WP-to-WP edges are added; task-level cross-WP edges are added by wp-dependency-analysis.
- Step 2.6: Build the `partner_role_matrix` array: for each distinct partner_id that appears as a lead_partner or in contributing_partners across the WP set: create an entry `{ partner_id, wps_as_lead: [list of wp_ids where this partner is lead_partner], wps_as_contributor: [list of wp_ids where this partner is in contributing_partners] }`.
- Step 2.7: If any normalization_issues were recorded: evaluate whether a complete, conformant `wp_structure.json` can still be produced. If every required field for every WP entry can be populated (even with flagged values): write the output and include a `normalization_issues` array in the artifact documenting each issue; the gate will fail on the affected predicates. If the normalization_issues make it impossible to produce a structurally complete artifact (e.g., zero valid WPs remain): return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="normalization issues prevent producing a conformant wp_structure.json") and do not write any partial output to the canonical path.

### 3. Output Construction

**`wp_structure.json`:**
- `schema_id`: set to "orch.phase3.wp_structure.v1"
- `run_id`: copied from invoking agent's run_id parameter
- `work_packages`: derived from Steps 2.2–2.4 — array of normalised WP entries; each entry: `{wp_id, title, objectives[], lead_partner, contributing_partners[], tasks[], deliverables[], dependencies[]}`
- `dependency_map`: derived from Step 2.5 — `{nodes: [], edges: []}` — nodes = all wp_ids + task_ids; edges = WP-level dependency edges
- `partner_role_matrix`: derived from Step 2.6 — array of `{partner_id, wps_as_lead[], wps_as_contributor[]}`

### 4. Conformance Stamping

- `schema_id`: set to "orch.phase3.wp_structure.v1" at write time
- `run_id`: copied from invoking agent's run_id parameter
- `artifact_status`: MUST be absent at write time (runner stamps post-gate)

### 5. Write Sequence

- Step 5.1: Create target directory `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/` if it does not exist.
- Step 5.2: Write `wp_structure.json` to `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`.

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
