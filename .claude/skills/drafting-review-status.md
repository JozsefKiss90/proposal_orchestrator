---
skill_id: drafting-review-status
purpose_summary: >
  Disposition every revision action from the Phase-8e review packet against
  the current assembled draft, WITHOUT modifying any prose, and produce
  drafting_review_status.json (orch.phase8.drafting_review_status.v1) — the
  artifact gate_12's all_critical_revisions_resolved predicate (g11_p04)
  evaluates. Replaces the former n08f re-run of evaluator-criteria-review,
  which rewrote review_packet.json and thereby invalidated gate_11's
  recorded input fingerprint (ST-1 content-based staleness).
used_by_agents:
  - revision_integrator
reads_from:
  - docs/tier5_deliverables/review_packets/review_packet.json
  - docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json
  - docs/tier5_deliverables/proposal_sections/
writes_to:
  - docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json
constitutional_constraints:
  - "Must not modify, rewrite, or overwrite any proposal prose or the review packet"
  - "Must not mark an action resolved unless the current draft substantively addresses it"
  - "Critical unresolved actions require a specific, non-empty reason (§12.4 honest declaration)"
  - "Must not fabricate resolutions or content to satisfy gate predicates (§13.8)"
---

## TAPM Input Boundary

You have access to the Read and Glob tools. Read ONLY the files listed below.
Do not read files outside the declared set. Do not use Glob to discover files
beyond the declared input directories.

### Files to Read

1. `docs/tier5_deliverables/review_packets/review_packet.json`
   - The Phase-8e evaluator review. Extract `findings[]` and
     `revision_actions[]`. Do NOT write to this file.
2. `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json`
   - Extract `sections[].section_id`, `sections[].criterion`,
     `sections[].artifact_path`.
3. Each section artifact referenced by `sections[].artifact_path`:
   - Read `sub_sections[].content` (to judge whether an action is already
     addressed) and `validation_status` / `traceability_footer` (for
     `data_gaps_flagged`).

## Disposition Rules

This skill is a **status recorder, not a reviser**. The following constraints
are mandatory:

1. **No prose changes.** You do not edit sections, the assembled draft, or
   the review packet. Your single output is the status artifact.

2. **Do not re-review.** Do not generate new findings or new revision
   actions. The review packet's `revision_actions` array is the complete
   and authoritative action list; every entry in it must appear in your
   output exactly once, and no other actions may appear.

3. **`resolved` requires evidence in the current draft.** Mark an action
   `resolved` ONLY if the current section content already substantively
   addresses the action's recommendation — i.e. the reviewer's premise is
   already satisfied by prose that exists now. When judging, quote nothing;
   just verify presence. When uncertain, the action is `unresolved`.

4. **`unresolved` requires a reason for critical severity.** Every action
   with `severity: critical` and `status: unresolved` MUST carry a
   specific, non-empty `reason` naming the actual constraint, one of:
   - the resolution requires project facts absent from Tier 3 (§13.3 —
     name the missing data);
   - the resolution requires budget figures or effort allocations beyond
     the validated budget gate assessment (§13.4);
   - the resolution requires new or rewritten prose, and Phase 8f performs
     no automated prose revision — the action is explicitly deferred to an
     operator-directed revision cycle (name the affected sub-section).
   A generic reason ("cannot be fixed") is a validation failure in spirit;
   be specific enough that an operator can act on it.

5. **Honesty over gate progress.** The gate predicate accepts unresolved
   critical actions when they carry a reason. It is constitutionally
   correct (§12.4) for this artifact to document unresolved actions; it is
   a violation (§13.8) to mark them resolved to make the gate pass.

## Execution Steps

### Step 1: Read and Validate Inputs

1. Read `review_packet.json`. Verify `schema_id` is
   `orch.tier5.review_packet.v1`. Extract `findings` and `revision_actions`.
2. Read `part_b_assembled_draft.json`. Verify `schema_id` is
   `orch.tier5.part_b_assembled_draft.v1`. Extract `sections[]`.
3. For each section in `sections[]`, read the artifact at `artifact_path`.

If any required input is missing or has a schema mismatch, return a
failure JSON with `failure_category: "MISSING_INPUT"`.

### Step 2: Disposition Each Revision Action

For each entry in the review packet's `revision_actions` (in order):

1. Locate the target section (`target_section`) and read its relevant
   `sub_sections[].content`.
2. Judge per Disposition Rule 3: `resolved` or `unresolved`.
3. For `unresolved` + `severity: critical`: write a specific `reason`
   per Disposition Rule 4. A `reason` on major/minor unresolved actions
   is welcome but optional.
4. Build the output action record:
   - `action_id`: copied verbatim
   - `section_id`: the packet's `target_section`, verbatim
   - `severity`: copied verbatim
   - `description`: the packet's `action_description`, verbatim
   - `status`: `resolved` or `unresolved`
   - `reason`: as above (omit or leave non-empty; never write an empty string)
   - `source_finding_id`: the packet's `finding_id`, verbatim

### Step 3: Build the Section Completion Log

One entry per section in the assembled draft's `sections[]`:
- `section_id`, `artifact_path`: copied verbatim
- `section_name`: the section's `criterion`, verbatim
- `status`: `final` when no unresolved critical action targets the
  section; `reviewed` when at least one unresolved critical action
  targets it
- `data_gaps_flagged`: `true` iff the section artifact's
  `validation_status.overall_status` is `unresolved` or its traceability
  footer declares unsupported claims; otherwise `false`

### Step 4: Build the Revision Log

One entry per revision action, recording the disposition decision (this is
the durable record required to be non-empty):
- `log_entry_id`: `L-<n>` (1-based, packet order)
- `action_id`: the action dispositioned
- `change_description`: for `resolved` — one sentence naming the existing
  prose that satisfies the action; for `unresolved` — `"no content change;
  dispositioned unresolved"` plus a pointer to the reason
- `section_affected`: the action's `target_section`
- `performed_at`: ISO 8601 timestamp (UTC, now)

### Step 5: Construct Output

Return a single JSON object:

```json
{
  "schema_id": "orch.phase8.drafting_review_status.v1",
  "run_id": "<from task metadata>",
  "section_completion_log": [...],
  "revision_actions": [...],
  "revision_log": [...]
}
```

- Do NOT include `artifact_status` (runner-stamped post-gate).
- `revision_actions` must contain exactly the packet's actions — no
  additions, no omissions.

## Output Schema

**Path:** `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json`
**Schema ID:** `orch.phase8.drafting_review_status.v1`

| Field | Required | Type |
|-------|----------|------|
| `schema_id` | yes | `"orch.phase8.drafting_review_status.v1"` |
| `run_id` | yes | string |
| `section_completion_log` | yes | array of section entries |
| `revision_actions` | yes | array of dispositioned actions |
| `revision_log` | yes | non-empty array of disposition records |
| `artifact_status` | ABSENT | runner-stamped |

**Section entry:** `section_id`, `section_name`, `status`
(enum: drafted/assembled/reviewed/revised/final), `artifact_path`,
`data_gaps_flagged` (boolean)

**Action entry:** `action_id`, `section_id`, `severity`
(enum: critical/major/minor), `description`, `status`
(enum: resolved/unresolved), `reason` (required non-empty when critical +
unresolved), `source_finding_id`

**Log entry:** `log_entry_id`, `action_id`, `change_description`,
`section_affected`, `performed_at` (ISO 8601)

## Failure Protocol

On failure, return a JSON object with:
- `status`: `"failure"`
- `failure_reason`: descriptive string
- `failure_category`: one of `MISSING_INPUT`, `CONSTITUTIONAL_HALT`, `INCOMPLETE_OUTPUT`

No artifact is written on failure.
