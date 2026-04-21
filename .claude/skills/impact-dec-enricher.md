---
skill_id: impact-dec-enricher
purpose_summary: >
  Enrich the existing impact_architecture.json by populating the dissemination_plan,
  exploitation_plan, and sustainability_mechanism fields. Reads the partial artifact
  produced by impact-pathway-core-builder and overwrites it with the complete version.
  Does NOT modify impact_pathways or kpis.
used_by_agents:
  - impact_architect
reads_from:
  - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
  - docs/tier3_project_instantiation/architecture_inputs/impacts.json
  - docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json
  - docs/tier2a_instrument_schemas/extracted/section_schema_registry.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/
constitutional_constraints:
  - "DEC plans must be specific to the project; generic templates are insufficient"
  - "Target groups must be defined with specificity"
  - "Must preserve existing impact_pathways and kpis fields without modification"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool.

**Declared input files to read:**
- `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json`
- `docs/tier3_project_instantiation/architecture_inputs/impacts.json`
- `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json`
- `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json`

**Boundary constraints:**
- Do not read files outside the declared input set.
- Do not read wp_structure.json, outcomes.json, or Tier 5 deliverables.
- Return your output as a single JSON object in your response.

## Scope Limitation

This skill ONLY populates three fields in the existing `impact_architecture.json`:
- `dissemination_plan`
- `exploitation_plan`
- `sustainability_mechanism`

It MUST preserve unchanged:
- `schema_id`
- `run_id`
- `impact_pathways` (copy verbatim from existing artifact)
- `kpis` (copy verbatim from existing artifact)

Do NOT recompute pathways or KPIs. Do NOT modify their content.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Purpose |
|------|--------------------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | Partial Phase 5 artifact with impact_pathways and kpis populated, DEC fields null | Base artifact to enrich |
| `docs/tier3_project_instantiation/architecture_inputs/impacts.json` | Project impacts with dissemination, exploitation, sustainability data | Source for DEC plan content |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Call expected impacts | DEC plans must address call-specific requirements |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | Instrument DEC section requirements | Ensures DEC plans cover mandatory instrument sections |

### Outputs

| Path | Schema ID | Notes |
|------|-----------|-------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | `orch.phase5.impact_architecture.v1` | Overwrites partial artifact with complete version |

## Execution Specification

### 1. Input Validation

- Step 1.1: Confirm `impact_architecture.json` exists with `schema_id` = "orch.phase5.impact_architecture.v1". If absent: MISSING_INPUT.
- Step 1.2: Confirm `impact_architecture.json` contains non-empty `impact_pathways` and `kpis` arrays. If empty: MISSING_INPUT (core builder did not run).
- Step 1.3: Confirm `impacts.json` exists. If absent: MISSING_INPUT.
- Step 1.4: Confirm `expected_impacts.json` exists. If absent: MISSING_INPUT.

### 2. Core Processing — Read Existing Artifact

- Step 2.1: Read the existing `impact_architecture.json` from disk.
- Step 2.2: Extract and preserve verbatim: `schema_id`, `run_id`, `impact_pathways`, `kpis`.

### 3. Core Processing — Dissemination Plan

- Step 3.1: Build `dissemination_plan` from `impacts.json` dissemination data.
- Step 3.2: `activities` array — each entry: `activity_type`, `target_audience` (specific group, not "general public"), `responsible_partner`, `timing`.
- Step 3.3: `open_access_policy` — non-empty statement about the project's open access approach.
- Step 3.4: If `impacts.json` lacks dissemination data, construct minimal compliant entries using impact pathway data and call expected impacts.

### 4. Core Processing — Exploitation Plan

- Step 4.1: Build `exploitation_plan` from `impacts.json` exploitation data.
- Step 4.2: `activities` array — each entry: `activity_type`, `expected_result`, `responsible_partner`, `timing`.
- Step 4.3: `ipr_strategy` — string (may be brief if no explicit IPR data in Tier 3).

### 5. Core Processing — Sustainability Mechanism

- Step 5.1: Build `sustainability_mechanism` from `impacts.json` sustainability data.
- Step 5.2: `description` — non-empty string describing how results persist post-project.
- Step 5.3: `responsible_partners` — non-empty array of partner_ids from `impacts.json`.

### 6. Output Construction

Produce a complete `impact_architecture.json` with ALL fields:

```json
{
  "schema_id": "<preserved from existing>",
  "run_id": "<preserved from existing>",
  "impact_pathways": "<preserved verbatim from existing>",
  "kpis": "<preserved verbatim from existing>",
  "dissemination_plan": { "activities": [...], "open_access_policy": "..." },
  "exploitation_plan": { "activities": [...], "ipr_strategy": "..." },
  "sustainability_mechanism": { "description": "...", "responsible_partners": [...] }
}
```

- `artifact_status` MUST be absent at write time.
- `impact_pathways` and `kpis` MUST be identical to the existing artifact.

## Failure Protocol

| Category | Trigger | Artifact Written |
|----------|---------|-----------------|
| MISSING_INPUT | Existing impact_architecture.json absent or incomplete | No |
| CONSTRAINT_VIOLATION | Generic DEC language without project specificity | No |
| MALFORMED_ARTIFACT | Existing artifact has invalid schema_id | No |

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`.
