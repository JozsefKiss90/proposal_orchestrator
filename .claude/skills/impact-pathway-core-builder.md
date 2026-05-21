---
skill_id: impact-pathway-core-builder
purpose_summary: >
  Produce the structural backbone of the Phase 5 impact architecture: impact
  pathways mapping call expected impacts to project outputs, and KPIs traceable
  to WP deliverables. Writes the canonical impact_architecture.json with
  dissemination, exploitation, and sustainability fields set to null (populated
  by the downstream impact-dec-enricher skill).
used_by_agents:
  - impact_architect
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/outcomes.json
  - docs/tier3_project_instantiation/architecture_inputs/impacts.json
  - docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json
  - docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
constitutional_constraints:
  - "Every call expected impact must be explicitly mapped or flagged as uncovered"
  - "Impact claims must trace to a named WP deliverable or activity"
  - "Generic impact language must not substitute for project-specific pathways"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool. For directory
paths, use Glob to discover JSON files within the directory, then Read each
relevant file.

**Declared input files to read:**
- `docs/tier3_project_instantiation/architecture_inputs/outcomes.json`
- `docs/tier3_project_instantiation/architecture_inputs/impacts.json`
- `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json`
- `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json`
- `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`

**Boundary constraints:**
- Do not read files outside the declared input set.
- Do not read Tier 5 deliverables, integration artifacts, or grouped JSON files.
- Return your output as a single JSON object in your response.

## Scope Limitation

This skill produces ONLY the `impact_pathways` and `kpis` sections of
`impact_architecture.json`. The `dissemination_plan`, `exploitation_plan`,
and `sustainability_mechanism` fields MUST be set to `null` in the output.
These fields are populated by the downstream `impact-dec-enricher` skill.

Do NOT attempt to construct DEC plans or sustainability mechanisms. Doing so
exceeds the bounded execution scope of this skill and risks timeout.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Purpose |
|------|--------------------|---------|
| `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` | Project-specific outcome entries: outcome_id, description, linked_wp_ids, timeframe | Provides project outcomes for pathway construction |
| `docs/tier3_project_instantiation/architecture_inputs/impacts.json` | Project-specific impact entries: impact_id, description, target_group, mechanism | Provides project impacts mapped against call expected impacts |
| `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | Call expected outcomes: outcome_id, description, source_section | Call-required expected outcomes for pathway nodes |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Call expected impacts: impact_id, description, source_section | Every impact_id must appear in at least one pathway |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | WP structure with deliverable_ids | Provides valid deliverable reference set for KPI traceability |

### Outputs

| Path | Schema ID | Required Fields |
|------|-----------|-----------------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | `orch.phase5.impact_architecture.v1` | schema_id, run_id, impact_pathways, kpis, dissemination_plan (null), exploitation_plan (null), sustainability_mechanism (null) |

## Execution Specification

### 1. Input Validation

- Step 1.1: Confirm `expected_impacts.json` exists and is non-empty. If absent: MISSING_INPUT.
- Step 1.2: Confirm `expected_outcomes.json` exists and is non-empty. If absent: MISSING_INPUT.
- Step 1.3: Confirm `outcomes.json` exists. If absent: MISSING_INPUT.
- Step 1.4: Confirm `impacts.json` exists. If absent: MISSING_INPUT.
- Step 1.5: Confirm `wp_structure.json` exists with `schema_id` = "orch.phase3.wp_structure.v1". If absent or schema mismatch: MISSING_INPUT.

### 2. Core Processing — Impact Pathways

- Step 2.1: Extract all `impact_id` values from `expected_impacts.json`. These are the **required coverage set**.
- Step 2.2: Extract all `deliverable_id` values from `wp_structure.json work_packages[].deliverables[]`. These are the **valid deliverable reference set**.
- Step 2.3: Extract project outcomes from `outcomes.json` and project impacts from `impacts.json`.
- Step 2.4: For each expected_impact entry from `expected_impacts.json`:
  - Find matching project impact(s) by subject-matter alignment.
  - Resolve contributing WP deliverables **exclusively from explicit Tier 3 linkage data** (`linked_wp_ids`, `linked_deliverable_ids`).
  - **Heuristic matching by deliverable title or description is prohibited** (CLAUDE.md §13.3).
  - If no explicit linkage: set `project_outputs: []`, mark as Unresolved.
  - Find intermediate outcomes from `outcomes.json` connected via `linked_wp_ids`.
  - Build pathway entry with: `pathway_id`, `expected_impact_id`, `project_outputs[]`, `outcomes[]`, `impact_narrative`, `tier2b_source_ref`.
- Step 2.5: Verify every `impact_id` from the required coverage set appears in the pathways. Missing IDs trigger INCOMPLETE_OUTPUT.

### 3. Core Processing — KPIs

- Step 3.1: For each impact pathway, define at least one KPI.
- Step 3.2: Each KPI must have: `kpi_id`, `description`, `target`, `measurement_method`, `traceable_to_deliverable`.
- Step 3.3: `traceable_to_deliverable` must reference a `deliverable_id` from the valid deliverable reference set. Writing a non-existent deliverable_id triggers CONSTITUTIONAL_HALT.

### 4. Output Construction

```json
{
  "schema_id": "orch.phase5.impact_architecture.v1",
  "run_id": "<from invoking agent>",
  "impact_pathways": [ ... ],
  "kpis": [ ... ],
  "dissemination_plan": null,
  "exploitation_plan": null,
  "sustainability_mechanism": null
}
```

- `artifact_status` MUST be absent at write time.
- `dissemination_plan`, `exploitation_plan`, `sustainability_mechanism` MUST be `null`.

## Failure Protocol

| Category | Trigger | Artifact Written |
|----------|---------|-----------------|
| MISSING_INPUT | Any required input absent | No |
| INCOMPLETE_OUTPUT | Expected impact_id not in pathways | No |
| CONSTITUTIONAL_HALT | Fabricated deliverable_id | No |
| CONSTRAINT_VIOLATION | Generic impact narrative | No |

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`.
