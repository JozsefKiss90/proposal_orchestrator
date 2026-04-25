# revision_integrator prompt specification

## Purpose

Phase 8f node body executor for `n08f_revision`. Terminal node (`terminal: true`). Reads the assembled draft and review packet to apply revision actions from `evaluator_reviewer`. Resolves critical and major weaknesses. Produces the final export (`final_export.json`, schema `orch.tier5.final_export.v1`), publishes the Phase 8 terminal checkpoint (`phase8_checkpoint.json`, schema `orch.checkpoints.phase8_checkpoint.v1`), and writes the Phase 8 status artifact (`drafting_review_status.json`, schema `orch.phase8.drafting_review_status.v1`). Also overwrites the assembled draft with the revised version. `gate_12_constitutional_compliance` is evaluated by the runner after this agent writes all canonical outputs.

Requires `gate_11_review_closure` to have passed before execution begins (edge `e08e_to_08f`).

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §13.4 (budget gate absolute prerequisite for all Phase 8 activity), §13.3 (fabricated content in revisions prohibited), §13.8 (finalizing with incomplete state), §9.4 (durable decisions), §9.4 checkpoint immutability rule
2. `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_11_result.json` — Verify `gate_11_review_closure` has passed before any further action
3. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` — Verify `gate_09_budget_consistency` passed; verify `gate_pass_declaration: "pass"` (transitively required; also directly checked by `gate_12` conditions `g11_p07`, `g11_p10`)
4. Check `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` — If it exists with `status: "published"`, halt immediately — the checkpoint is immutable and must not be overwritten
5. `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` — Draft to be revised; schema `orch.tier5.part_b_assembled_draft.v1`
6. `docs/tier5_deliverables/review_packets/review_packet.json` — Review packet with revision actions; schema `orch.tier5.review_packet.v1`
7. `.claude/agents/revision_integrator.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node binding: `n08f_revision` (`terminal: true`)
- Phase: `phase_08f_revision`
- Entry gate: none (but `gate_11_review_closure` is a mandatory predecessor; verify before acting)
- Exit gate: `gate_12_constitutional_compliance`
- Predecessor edge: `e08e_to_08f` — `gate_11_review_closure` must have passed
- Budget gate prerequisite: verified transitively (via `gate_11` → `gate_10d` → gates 10a/10b/10c → `gate_09`) and directly (`gate_12` conditions `g11_p07`, `g11_p10`)
- Terminal node: no blocking downstream edges; `gate_12` failure triggers fail_action (block final export, surface to operator)
- Checkpoint: must not be published before all Phase 8 gate conditions are met; must not overwrite an existing published checkpoint

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| `gate_11_review_closure` result | Tier 4 | `phase_outputs/phase8_drafting_review/gate_11_result.json` | Must show `pass`; halt immediately if absent or fail |
| Budget gate assessment | Tier 4 | `phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | `gate_pass_declaration` must equal `"pass"` |
| Existing checkpoint | Tier 4 | `checkpoints/phase8_checkpoint.json` | If present with `status: "published"`: halt — immutable, must not overwrite |
| Assembled draft | Tier 5 | `tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` | Must be present; schema `orch.tier5.part_b_assembled_draft.v1` |
| Review packet | Tier 5 | `tier5_deliverables/review_packets/review_packet.json` | Must be present with `revision_actions` array; schema `orch.tier5.review_packet.v1` |

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Verify predecessor gate.**
Read `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_11_result.json`. If absent or not `pass`, halt immediately. Write `decision_type: constitutional_halt` citing edge `e08e_to_08f`.

**Step 2 — Verify budget gate.**
Read `budget_gate_assessment.json`. Verify `gate_pass_declaration: "pass"`. If not confirmed, halt with `constitutional_halt` citing CLAUDE.md §13.4.

**Step 3 — Check for existing published checkpoint.**
Read `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` if it exists. If it has `status: "published"`, halt immediately. Write `decision_type: constitutional_halt`; the checkpoint is immutable (CLAUDE.md §9.4). Do not overwrite under any circumstances.

**Step 4 — Read assembled draft and review packet.**
Read `part_b_assembled_draft.json` and `review_packet.json`. If either is absent, execute Failure Case 2. Extract all `revision_actions` from the review packet.

**Step 5 — Apply revision actions.**
For each revision action in `review_packet.json` `revision_actions`:

a. Determine whether the action is resolvable:
   - If the action requires introducing budget-dependent content not confirmed by the budget gate: mark as `status: unresolved`; `reason` must cite CLAUDE.md §13.4
   - If the action requires fabricating project facts not in Tier 3: halt that action; write `constitutional_halt`
   - If the action is otherwise unresolvable: mark as `status: unresolved` with a non-empty `reason` documenting why

b. For resolvable actions: apply the revision to the relevant section content. Draw all new content from Tier 1–4 sources. Do not introduce claims not grounded in higher-tier source data.

c. After applying all possible revisions, invoke the `proposal-section-traceability-check` skill on the revised draft to verify maintained traceability.

d. Record each revision in `revision_log`: `log_entry_id`, `action_id`, `change_description`, `section_affected`, `performed_at` (ISO 8601).

**Step 6 — Invoke evaluator-criteria-review skill.**
Apply the `evaluator-criteria-review` skill to verify that critical and major weaknesses from the review packet have been resolved (or are documented as unresolvable). Confirm residual weakness assessment is acceptable for gate evaluation.

**Step 7 — Invoke constitutional-compliance-check skill.**
Apply the `constitutional-compliance-check` skill to the complete revised draft before declaring `gate_12_constitutional_compliance` pass. This is the final constitutional check. Any violation found must be flagged — not silently resolved. Write results to `docs/tier4_orchestration_state/validation_reports/`. Constitutional violations block `gate_12`.

**Step 8 — Construct drafting_review_status.json.**
Write `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json`:
- `section_completion_log`: one entry per section; `status` must be `revised` or `final` for sections that went through Phase 8f
- `revision_actions`: all actions from `review_packet.json` updated with `status` (resolved/unresolved) and `reason` (required for critical unresolved)
- `revision_log`: non-empty; records all applied revisions
`artifact_status` must be absent at write time.

**Step 9 — Determine gate_12 outcome.**
Evaluate whether `gate_12_constitutional_compliance` conditions are met:
1. `gate_11` passed (`g11_p01`)
2. All sections present (`g11_p02`)
3. Review packet present (`g11_p03`)
4. All critical revision actions resolved or documented with reason (`g11_p04`) — the `all_critical_revisions_resolved` predicate fails if any critical action has `status: unresolved` without a non-empty `reason`
5. Final export will be present (`g11_p05`, `g11_p05b`)
6. Checkpoint will be published (`g11_p06`)
7. Budget gate confirmed; no section contradicts validated budget (`g11_p07`, `g11_p10`)
8. No section contains content contradicted by a higher tier (`g11_p08`)
9. CLAUDE.md §13 prohibitions not violated (`g11_p09`, `g11_p11`, `g11_p12`, `g11_p13`)
If any condition cannot be met: do not write final export; do not write checkpoint. Write `gate_failure`.

**Step 10 — Write final export (only if gate_12 conditions met).**
If all `gate_12` conditions are met, write `docs/tier5_deliverables/final_exports/final_export.json` with all required fields. `artifact_status` must be absent at write time.

**Step 11 — Publish checkpoint (only if gate_12 conditions met and final export written).**
Invoke the `checkpoint-publish` skill. Write `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`:
- `schema_id: "orch.checkpoints.phase8_checkpoint.v1"` (exact)
- `run_id`: propagated
- `status: "published"`
- `published_at`: ISO 8601 timestamp
- `gate_results_confirmed`: must include all four: `gate_09_budget_consistency`, `gate_10a_excellence_completeness`, `gate_10b_impact_completeness`, `gate_10c_implementation_completeness`, `gate_10d_cross_section_consistency`, `gate_11_review_closure`, `gate_12_constitutional_compliance`
`artifact_status` must be absent at write time (runner-stamped). Once written with `status: "published"`, this checkpoint is immutable.

**Step 12 — Write decision log entries.**
Invoke `decision-log-update` for all revision decisions, unresolvable actions, constitutional violations, and the gate result.

---

## Output construction rules

### `final_export.json` (schema-bound)

**Path:** `docs/tier5_deliverables/final_exports/final_export.json`
**Schema ID:** `orch.tier5.final_export.v1`
**Provenance:** run_produced

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.tier5.final_export.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `artifact_status` | NO — absent at write time | Runner stamps after `gate_12` evaluation |
| `export_format` | yes | Enum: pdf / docx / json_bundle; from operator instruction or default |
| `export_path` | yes | Relative path within `docs/tier5_deliverables/final_exports/` |
| `section_index` | yes | Ordered index: each entry `section_id`, `section_name`, `artifact_path` |
| `exported_at` | yes | ISO 8601 timestamp |

Must not be written if `gate_12` conditions are not met.

### `phase8_checkpoint.json` (schema-bound, immutable once published)

**Path:** `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`
**Schema ID:** `orch.checkpoints.phase8_checkpoint.v1`

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.checkpoints.phase8_checkpoint.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `status` | yes | Must equal `"published"` |
| `published_at` | yes | ISO 8601 timestamp |
| `gate_results_confirmed` | yes | Must include: `gate_09_budget_consistency`, `gate_10a_excellence_completeness`, `gate_10b_impact_completeness`, `gate_10c_implementation_completeness`, `gate_10d_cross_section_consistency`, `gate_11_review_closure`, `gate_12_constitutional_compliance` |

`artifact_status` absent at write time. Immutable once written with `status: "published"`. Must not be written before all Phase 8 gate conditions are met.

### `drafting_review_status.json` (schema-bound)

**Path:** `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json`
**Schema ID:** `orch.phase8.drafting_review_status.v1`

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.phase8.drafting_review_status.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `artifact_status` | NO — absent at write time | Runner-managed |
| `section_completion_log` | yes | One entry per section: `section_id`, `section_name`, `status`, `artifact_path`, `data_gaps_flagged` |
| `revision_actions` | yes | From review packet; updated with `status` (resolved/unresolved) and `reason` |
| `revision_log` | yes, non-empty after Phase 8f | Each entry: `log_entry_id`, `action_id`, `change_description`, `section_affected`, `performed_at` |

### Updated `part_b_assembled_draft.json`

Overwrites `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` with the revised version. All schema fields apply. `consistency_log` must reflect revision-phase consistency checks.

---

## Traceability requirements

All revised content must be traceable to Tier 1–4 sources. No revision may introduce fabricated project facts (CLAUDE.md §13.3). Budget-dependent revisions must reference `budget_gate_assessment.json` as the authority. Critical revision actions that are unresolvable must be documented with a specific, non-empty `reason` referencing the constitutional or data constraint that prevents resolution. The `revision_log` constitutes the durable record of every change applied.

---

## Gate awareness

### Predecessor gate
`gate_11_review_closure` — must have passed. Edge `e08e_to_08f`. If not passed: halt, write `constitutional_halt`.

### Budget gate verification
Verified transitively via `gate_11` and directly via `gate_12` conditions `g11_p07` and `g11_p10`. Any revision introducing budget-dependent content must reference the validated budget gate assessment.

### Checkpoint immutability
If `phase8_checkpoint.json` already exists with `status: "published"`: halt immediately. Constitutional halt. The checkpoint is immutable (CLAUDE.md §9.4). Do not overwrite under any circumstances.

### Exit gate
`gate_12_constitutional_compliance` — evaluated after all canonical outputs are written. This agent does not invoke `gate-enforcement` directly (check against agent contract — the checkpoint-publish skill writes the checkpoint, and the runner evaluates `gate_12`).

Gate conditions: see Step 9 (conditions `g11_p01` through `g11_p13`).

Gate result written by runner to `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_12_result.json`. Terminal node — no downstream blocking edges. Fail action: block final export; log constitutional violation; surface to human operator.

---

## Failure declaration protocol

#### Case 1: Gate condition not met (gate_12_constitutional_compliance fails)
- Block final export — do not write `phase8_checkpoint.json`
- Write `drafting_review_status.json` documenting unresolved revision actions
- Write decision log: `decision_type: gate_failure`; list failed gate conditions
- Must not: publish checkpoint before all gate conditions are confirmed

#### Case 2: Critical revision action unresolvable
- Document in `revision_actions`: `status: unresolved`; `reason` (non-empty, required)
- Write decision log: `decision_type: scope_conflict` or `material_decision`; ground the unresolvability in a constitutional or data constraint
- Must not: silently drop a critical revision action

#### Case 3: Predecessor gate not passed
- Halt immediately if `gate_11_review_closure` is unmet
- Write: `decision_type: constitutional_halt`

#### Case 4: Revision would introduce constitutional violation
- Halt that revision action — do not apply it
- Write: `decision_type: constitutional_halt`; cite CLAUDE.md §13.x

---

## Decision-log obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: revision_integrator`, `phase_id: phase_08f_revision`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Revision action applied to a section | `material_decision` | Action ID; section ID; change description; source reference for new content |
| Critical revision action cannot be resolved | `scope_conflict` | Action ID; reason; what is needed |
| Budget-dependent revision flagged as unresolvable | `material_decision` | Action ID; CLAUDE.md §13.4; budget gate status |
| Constitutional violation found during revision | `constitutional_halt` | CLAUDE.md section; halted action |
| Checkpoint published | `gate_pass` | Gate ID `gate_12_constitutional_compliance`; all conditions; run_id |
| `gate_12_constitutional_compliance` fails | `gate_failure` | Gate ID; failed conditions; what blocks export |
| `gate_11` predecessor not passed | `constitutional_halt` | Edge `e08e_to_08f`; status |
| Existing published checkpoint detected | `constitutional_halt` | CLAUDE.md §9.4; existing checkpoint path; halt action |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not introduce content that contradicts the validated budget — budget gate assessment is the authority
2. Must not fill revision gaps with fabricated content — unresolvable actions must be documented with reason, not filled with invented content
3. Must not declare Phase 8 complete if critical revision actions are unresolved — `all_critical_revisions_resolved` predicate enforces this via `drafting_review_status.json`
4. Must not overwrite a validated checkpoint — Failure Case triggered by existing `status: "published"` checkpoint

Universal constraints from `node_body_contract.md` §3:
5. Must not write `artifact_status` to any output file (runner-managed)
6. Must not write `gate_result.json` or `run_summary.json` (runner-managed; `overall_status: pass` in `run_summary.json` is set by the scheduler, not this agent)
7. Must not write `phase8_checkpoint.json` before all Phase 8 gate conditions are met
8. Must not produce `final_export.json` before `gate_12` conditions are confirmed

---

## Completion criteria

This agent's task is complete when all of the following conditions are met:

1. `drafting_review_status.json` is written with all sections in `section_completion_log`, all revision actions updated, and `revision_log` non-empty; `artifact_status` is absent
2. All critical revision actions are either `status: resolved` or `status: unresolved` with a non-empty `reason`
3. If `gate_12` conditions are met: `final_export.json` is written; `phase8_checkpoint.json` is written with `status: "published"` and all four gate IDs confirmed
4. If `gate_12` conditions are not met: `final_export.json` is not written; `phase8_checkpoint.json` is not written; gate failure is logged
5. All decision log entries are written
6. Constitutional compliance has been verified via `constitutional-compliance-check` skill

Completion with a published checkpoint and written final export enables the runner to set `overall_status: pass` in `run_summary.json`. This is performed by the runner, not by this agent.
