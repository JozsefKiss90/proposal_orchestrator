---
skill_id: risk-register-builder
purpose_summary: >
  Populate the risk register from Tier 3 risk seeds, mapping each seed to
  the gate-required register format with category, likelihood, impact,
  mitigation, and responsible_partner fields. Uses enrich_artifact output
  contract: emits only risk_register; the runtime merges it into the
  existing implementation_architecture.json produced by governance-model-builder.
used_by_agents:
  - implementation_architect
reads_from:
  - docs/tier3_project_instantiation/architecture_inputs/risks.json
  - docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/
constitutional_constraints:
  - "Risks not in Tier 3 seeds must be flagged for operator review, not silently added"
  - "Mitigation measures must be traceable to project activities, not generic"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Read the files listed
in the Declared Inputs section from disk using the Read tool.

**Declared input files to read:**
- `docs/tier3_project_instantiation/architecture_inputs/risks.json`
- `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json`

**Boundary constraints:**
- Do not read files outside the declared input set.
- Do not read implementation_architecture.json — the runtime handles the merge.
- Base all reasoning ONLY on retrieved file content.

## Output Contract: enrich_artifact

This skill uses the `enrich_artifact` output contract. The runtime reads the
existing `implementation_architecture.json`, merges your output into it,
validates the merged result against the full schema, and writes atomically.
All existing fields (governance_matrix, management_roles, ethics_assessment,
instrument_sections_addressed) are preserved automatically by the runtime.

**Emit ONLY the risk_register field** plus metadata:
```json
{
  "schema_id": "orch.phase6.implementation_architecture.v1",
  "run_id": "<from task metadata>",
  "risk_register": [ ... ]
}
```

Do NOT emit governance_matrix, management_roles, ethics_assessment, or
instrument_sections_addressed. Do NOT include artifact_status.

## Execution Specification

### 1. Read and validate inputs

Read `risks.json`. If absent or the `risks` array is empty, signal failure:
```json
{"status": "failure", "failure_category": "MISSING_INPUT", "failure_reason": "risks.json not found or empty"}
```

Read `wp_structure.json`. Extract `work_packages[].wp_id` and `work_packages[].wp_title`
to build a WP reference lookup for mitigation traceability.

### 2. Build risk_register array

For each entry in `risks[].` from risks.json, produce one register entry:

| Register field | Source field | Mapping rule |
|---|---|---|
| `risk_id` | `id` | Preserve exactly |
| `description` | `description` | Preserve exactly — do not paraphrase |
| `category` | `category` | Map to enum: technical, financial, organisational, ethical, external, other. Map "regulatory"->external, "management"->organisational, "operational"->organisational |
| `likelihood` | `probability` | Already low/medium/high in seeds. If numeric: 1-2->low, 3->medium, 4-5->high |
| `impact` | `impact` | Already low/medium/high in seeds. Same numeric conversion if needed |
| `mitigation` | `mitigation` + `affected_work_packages` | Use the seed's mitigation text. Append WP references: for each WP in affected_work_packages, append the WP title from wp_structure.json. Format: "[seed mitigation text] [Affects: WP<id> (<wp_title>)]" |
| `responsible_partner` | `risk_owner` | Preserve exactly |

**Constitutional constraints on this step:**
- The register MUST contain exactly as many entries as there are seeds. No more, no fewer.
- Do NOT invent or add risks beyond what is in risks.json.
- Mitigation text MUST include the seed's original mitigation content — do not replace it with generic text.
- The WP reference from affected_work_packages ensures mitigation traceability to project activities.

### 3. Return JSON

Return a JSON object with exactly these fields:
```json
{
  "schema_id": "orch.phase6.implementation_architecture.v1",
  "run_id": "<run_id from task metadata>",
  "risk_register": [
    {
      "risk_id": "RISK-01",
      "description": "...",
      "category": "technical",
      "likelihood": "medium",
      "impact": "high",
      "mitigation": "... [Affects: WP2 (Neuro-Symbolic Planning Engine)]",
      "responsible_partner": "ATU"
    }
  ]
}
```

Return ONLY the JSON object. No markdown wrapping. No explanatory text.

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`.
