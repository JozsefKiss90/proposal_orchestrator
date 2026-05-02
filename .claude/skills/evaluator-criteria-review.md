---
skill_id: evaluator-criteria-review
purpose_summary: >
  Bounded evaluator review of proposal content against the scoring logic of
  the applicable evaluation criteria. Reads assembled draft and section
  artifacts from disk via TAPM tools. Produces review_packet.json conforming
  to orch.tier5.review_packet.v1. Does not re-run traceability or
  cross-section consistency (already performed by gates 10a–10d).
used_by_agents:
  - evaluator_reviewer
  - revision_integrator
reads_from:
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
  - docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json
  - docs/tier5_deliverables/proposal_sections/
writes_to:
  - docs/tier5_deliverables/review_packets/
constitutional_constraints:
  - "Evaluation must apply the active instrument evaluation criteria only"
  - "Must not evaluate against grant agreement annex requirements"
  - "Weakness severity (critical/major/minor) must be assigned to each finding"
---

## TAPM Input Boundary

You have access to the Read and Glob tools. Read ONLY the files listed below.
Do not read files outside the declared set. Do not use Glob to discover files
beyond the declared input directories.

### Files to Read

1. `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json`
   - Extract `sections[].section_id` and `sections[].artifact_path`
2. Each section artifact referenced by `sections[].artifact_path`:
   - Read the relevant section artifact for each criterion being evaluated
   - Extract evaluator-relevant evidence from `sub_sections[].content`
3. `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json`
   - Extract `evaluation_matrix` (criterion_id, criterion_name, weight)
4. `docs/tier2a_instrument_schemas/evaluation_forms/`
   - Glob this directory, then read the evaluation form for the active instrument
   - Extract criterion sub-criteria, scoring thresholds, grade descriptors

### Grant Agreement Annex Guard

Before using any evaluation form file, verify it is NOT a Grant Agreement
Annex. If the filename or title contains "Annex", "Grant Agreement", "Model
Grant Agreement", or "AGA": return a failure JSON with
`failure_category: "CONSTITUTIONAL_HALT"`. Do not proceed.

## Bounded Evaluator Review Rules

This skill performs a **bounded evaluator review**. The following constraints
are mandatory:

1. **Do not re-run traceability.** Traceability was verified by
   `proposal-section-traceability-check` and gates 10a–10c. Do not
   re-audit material claims or source attribution.

2. **Do not re-run cross-section consistency.** Cross-section consistency
   was verified by `cross-section-consistency-check` and gate 10d. Do not
   re-check inter-section alignment or terminology consistency.

3. **Active evaluation criteria only.** Review against the evaluation
   criteria from the active instrument's evaluation form and the
   evaluation_matrix in call_analysis_summary.json. Do not evaluate
   against generic Horizon Europe knowledge, grant agreement annex
   requirements, or criteria from a different instrument.

4. **Maximum 12 findings total.** Prioritize score-affecting weaknesses.
   Omit low-value stylistic comments.

5. **Maximum 4 findings per criterion.** Focus on the most impactful
   weaknesses for each evaluation criterion.

6. **Severity required for every finding.** Each finding must have
   `severity` set to exactly one of: `critical`, `major`, or `minor`.

7. **If no material weakness is found for a criterion**, do not invent
   findings. It is valid to have zero findings for a criterion.

8. **Keep evidence quotes short.** When quoting from the draft, use brief
   excerpts (1-2 sentences) that illustrate the weakness. Do not
   reproduce entire sections.

## Execution Steps

### Step 1: Read and Validate Inputs

1. Read `call_analysis_summary.json`. Verify `schema_id` is
   `orch.phase1.call_analysis_summary.v1`. Extract `evaluation_matrix`.
2. Glob `docs/tier2a_instrument_schemas/evaluation_forms/` and read the
   evaluation form. Verify it is not a Grant Agreement Annex.
3. Read `part_b_assembled_draft.json`. Verify `schema_id` is
   `orch.tier5.part_b_assembled_draft.v1`.
4. For each section in `sections[]`, read the artifact at `artifact_path`.

If any required input is missing or has a schema mismatch, return a
failure JSON with `failure_category: "MISSING_INPUT"`.

### Step 2: Build Criteria Set

From the `evaluation_matrix`, build the criteria set: ordered list of
`{criterion_id, criterion_name, weight}`. Look up sub-criteria and
scoring descriptors from the evaluation form for each criterion.

Map criteria to sections:
- Excellence criterion → excellence section artifact
- Impact criterion → impact section artifact
- Quality and efficiency of implementation criterion → implementation section artifact

### Step 3: Evaluate Each Criterion

For each criterion in the criteria set:

1. Read the corresponding section artifact's `sub_sections[].content`.
2. For each sub-criterion from the evaluation form:
   - **Presence test**: does the section address this sub-criterion?
     Absent = critical.
   - **Evidence test**: if evidence is required, does the section provide
     specific evidence rather than general assertions? Missing = major.
   - **Specificity test**: does the section provide project-specific
     detail where the grade descriptors require it? Weak = minor or major.
3. Assign severity per finding:
   - `critical`: mandatory sub-criterion has zero coverage, or content
     contradicts criterion requirements
   - `major`: significant sub-criterion is missing or weakly addressed
   - `minor`: sub-criterion is substantially addressed but lacks
     specificity
4. Build finding record with: `finding_id`, `section_id`, `criterion`,
   `description`, `severity`, `evidence` (brief quote), `recommendation`.

Respect the bounds: maximum 12 findings total, maximum 4 per criterion.

### Step 4: Build Revision Actions

For each finding, produce a revision action:
- `action_id`: unique (e.g. `A-1`, `A-2`)
- `finding_id`: reference to the finding
- `priority`: integer, 1-based (critical first, then major, then minor;
  within severity, higher-weight criterion first)
- `action_description`: specific change to make
- `target_section`: section_id affected
- `severity`: matching the finding severity

### Step 5: Construct Output

Return a single JSON object:

```json
{
  "schema_id": "orch.tier5.review_packet.v1",
  "run_id": "<from task metadata>",
  "findings": [...],
  "revision_actions": [...]
}
```

- `findings` and `revision_actions` may be empty arrays if no material
  weaknesses are found — this is a valid outcome.
- Do NOT include `artifact_status` (runner-stamped post-gate).

## Output Schema

**Path:** `docs/tier5_deliverables/review_packets/review_packet.json`
**Schema ID:** `orch.tier5.review_packet.v1`

| Field | Required | Type |
|-------|----------|------|
| `schema_id` | yes | `"orch.tier5.review_packet.v1"` |
| `run_id` | yes | string |
| `findings` | yes | array of finding objects |
| `revision_actions` | yes | array of action objects |
| `artifact_status` | ABSENT | runner-stamped |

**Finding object:** `finding_id`, `section_id`, `criterion`, `description`,
`severity` (enum: critical/major/minor), `evidence`, `recommendation`

**Action object:** `action_id`, `finding_id`, `priority` (integer, 1-based),
`action_description`, `target_section`, `severity` (enum: critical/major/minor)

## Failure Protocol

On failure, return a JSON object with:
- `status`: `"failure"`
- `failure_reason`: descriptive string
- `failure_category`: one of `MISSING_INPUT`, `CONSTITUTIONAL_HALT`, `INCOMPLETE_OUTPUT`

No artifact is written on failure.
