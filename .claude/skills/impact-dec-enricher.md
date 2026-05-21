---
skill_id: impact-dec-enricher
purpose_summary: >
  Enrich the existing impact_architecture.json by populating the dissemination_plan,
  exploitation_plan, and sustainability_mechanism fields. Emits only the three DEC
  fields as a compact JSON patch; the runtime merges them into the existing base
  artifact produced by impact-pathway-core-builder. Does NOT emit or modify
  impact_pathways or kpis — those are preserved automatically by the runtime merge.
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

This skill ONLY produces three fields as a compact enrichment patch:
- `dissemination_plan`
- `exploitation_plan`
- `sustainability_mechanism`

The runtime will automatically merge these fields into the existing
`impact_architecture.json`, preserving `schema_id`, `run_id`,
`impact_pathways`, and `kpis` from the base artifact.

**Do NOT include `impact_pathways` or `kpis` in your output.**
**Do NOT recompute pathways or KPIs.**
The runtime merge handles preservation of all base artifact fields.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Purpose |
|------|--------------------|---------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | Partial Phase 5 artifact with impact_pathways and kpis populated, DEC fields null | Context for DEC plan construction (read impact pathways for alignment) |
| `docs/tier3_project_instantiation/architecture_inputs/impacts.json` | Project impacts with dissemination, exploitation, sustainability data | Source for DEC plan content |
| `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | Call expected impacts | DEC plans must address call-specific requirements |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | Instrument DEC section requirements | Ensures DEC plans cover mandatory instrument sections |

### Outputs

| Path | Schema ID | Notes |
|------|-----------|-------|
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | `orch.phase5.impact_architecture.v1` | Runtime merges enrichment patch into existing base artifact |

## Execution Specification

### 1. Input Validation

- Step 1.1: Confirm `impact_architecture.json` exists with `schema_id` = "orch.phase5.impact_architecture.v1". If absent: MISSING_INPUT.
- Step 1.2: Confirm `impact_architecture.json` contains non-empty `impact_pathways` and `kpis` arrays. If empty: MISSING_INPUT (core builder did not run).
- Step 1.3: Confirm `impacts.json` exists. If absent: MISSING_INPUT.
- Step 1.4: Confirm `expected_impacts.json` exists. If absent: MISSING_INPUT.

### 2. Core Processing — Read Context

- Step 2.1: Read the existing `impact_architecture.json` from disk.
- Step 2.2: Note the `schema_id` and `run_id` values — you will include these in your output.
- Step 2.3: Review `impact_pathways` to understand which project outputs, outcomes, and expected impacts are addressed — DEC plans should align with these pathways.

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

Produce a compact JSON enrichment patch with ONLY these fields:

```json
{
  "schema_id": "<copied from existing artifact>",
  "run_id": "<copied from existing artifact>",
  "dissemination_plan": { "activities": [...], "open_access_policy": "..." },
  "exploitation_plan": { "activities": [...], "ipr_strategy": "..." },
  "sustainability_mechanism": { "description": "...", "responsible_partners": [...] }
}
```

**Critical output rules:**
- `schema_id` and `run_id` MUST match the existing artifact values exactly.
- `artifact_status` MUST be absent.
- Do NOT include `impact_pathways` or `kpis` — the runtime preserves these from the base.
- Do NOT wrap the JSON in markdown code fences.
- Do NOT include any prose, explanation, or annotation outside the JSON object.
- The output must be a single, valid, self-contained JSON object.

## Failure Protocol

| Category | Trigger | Artifact Written |
|----------|---------|-----------------|
| MISSING_INPUT | Existing impact_architecture.json absent or incomplete | No |
| CONSTRAINT_VIOLATION | Generic DEC language without project specificity | No |
| MALFORMED_ARTIFACT | Existing artifact has invalid schema_id | No |

## Runtime Contract

This skill uses the `enrich_artifact` output contract. The runtime reads the
existing base artifact, merges this skill's output fields into it, validates
the merged result against the full `orch.phase5.impact_architecture.v1` schema,
and writes atomically. This skill is governed by the skill runtime contract at
`.claude/skills/skill_runtime_contract.md`.
