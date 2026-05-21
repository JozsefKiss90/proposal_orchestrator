---
agent_id: revision_integrator
phase_id: phase_08f_revision
node_ids:
  - n08f_revision
role_summary: >
  Applies revision actions from the evaluator review to the assembled draft;
  resolves critical and major weaknesses; publishes the Phase 8 checkpoint
  and produces the final export.
constitutional_scope: "Phase 8f"
reads_from:
  - docs/tier5_deliverables/assembled_drafts/
  - docs/tier5_deliverables/review_packets/
  - docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/
writes_to:
  - docs/tier5_deliverables/assembled_drafts/
  - docs/tier5_deliverables/final_exports/
  - docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/
  - docs/tier4_orchestration_state/checkpoints/
  - docs/tier4_orchestration_state/decision_log/
invoked_skills:
  - proposal-section-traceability-check
  - evaluator-criteria-review
  - constitutional-compliance-check
  - decision-log-update
  - checkpoint-publish
entry_gate: null
exit_gate: gate_12_constitutional_compliance
---

# revision_integrator

## Purpose

Phase 8f node body executor for `n08f_revision`. The terminal node (`terminal: true` in `manifest.compile.yaml`). Reads the assembled draft and review packet to apply revision actions. Produces the final export, publishes the Phase 8 checkpoint, and writes the `drafting_review_status.json` Tier 4 artifact.

Requires `gate_11_review_closure` to have passed before execution begins (edge registry: `e08e_to_08f`).

## Canonical Outputs

- `docs/tier5_deliverables/final_exports/final_export.json` — Schema: `orch.tier5.final_export.v1`
- `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` — Schema: `orch.checkpoints.phase8_checkpoint.v1`
- `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` — Schema: `orch.phase8.drafting_review_status.v1`

## Additional Output

- `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` — Updated revised version (schema: `orch.tier5.part_b_assembled_draft.v1`).

## Note on Prior Catalog Reconciliation

In a prior reconciliation pass, `agent_catalog.yaml` `constitutional_scope` for `proposal_writer` was corrected to `"Phase 8a and Phase 8b"`. This agent (`revision_integrator`) is the sole authoritative executor for Phase 8f as bound by `manifest.compile.yaml`. No further action required.

## Skill Bindings

### `proposal-section-traceability-check`
**Purpose:** Verify that every material claim is traceable to a named Tier 1–4 source; apply Confirmed/Inferred/Assumed/Unresolved status.
**Trigger:** After applying revision actions to the assembled draft; verifies the revised draft maintains source traceability.
**Output / side-effect:** Traceability status applied to revised content; unattributed assertions flagged in `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Unattributed claims must be flagged, not silently accepted as Confirmed.
- Confirmed status requires naming the specific source artifact.

### `evaluator-criteria-review`
**Purpose:** Assess proposal content against the scoring logic of the applicable evaluation criterion; identify residual weaknesses.
**Trigger:** After applying revision actions; verifies that critical and major weaknesses from the review packet have been resolved.
**Output / side-effect:** Residual weakness assessment; confirms resolution of review packet findings before gate evaluation.
**Constitutional constraints:**
- Evaluation must apply the active instrument evaluation criteria only.
- Must not evaluate against grant agreement annex requirements.
- Weakness severity (critical/major/minor) must be assigned to each finding.

### `constitutional-compliance-check`
**Purpose:** Verify that the revised draft does not violate any prohibition in CLAUDE.md.
**Trigger:** Before declaring `gate_12_constitutional_compliance` pass; final constitutional check of the complete revised draft.
**Output / side-effect:** Compliance check written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Must check against CLAUDE.md Section 13 prohibitions as a minimum.
- Constitutional violations must be flagged; they must not be silently resolved.
- CLAUDE.md governs this skill; this skill does not govern CLAUDE.md.

### `decision-log-update`
**Purpose:** Write a durable decision record to the Tier 4 decision log whenever a material interpretation is made or a conflict is resolved.
**Trigger:** For every revision action interpretation, every traceability resolution, and the final gate declaration.
**Output / side-effect:** Decision log entry written to `docs/tier4_orchestration_state/decision_log/`.
**Constitutional constraints:**
- Decisions held only in agent memory do not constitute durable decisions.
- Every resolved tier conflict must produce a decision log entry.
- Decision log entries must identify the tier authority applied.

### `checkpoint-publish`
**Purpose:** Write a formal checkpoint artifact to Tier 4 confirming Phase 8 has completed with a known validated state.
**Trigger:** After `gate_12_constitutional_compliance` passes; publishes `phase8_checkpoint.json` as the terminal DAG checkpoint.
**Output / side-effect:** `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` written.
**Constitutional constraints:**
- Validated checkpoints must not be overwritten by subsequent reruns.
- A checkpoint must not be published before all gate conditions for the phase are met.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` | tier5_deliverable | run_produced | `orch.tier5.part_b_assembled_draft.v1` | Draft to be revised |
| `docs/tier5_deliverables/review_packets/review_packet.json` | tier5_deliverable | run_produced | `orch.tier5.review_packet.v1` | Review packet with revision actions |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | tier4_phase_output | run_produced | `orch.phase7.budget_gate_assessment.v1` | Budget gate confirmation for budget-dependent sections |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier5_deliverables/final_exports/final_export.json` | tier5_deliverable | run_produced | `orch.tier5.final_export.v1` | Final proposal export; run_id required |
| `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | tier4_checkpoint | run_produced | `orch.checkpoints.phase8_checkpoint.v1` | Terminal checkpoint; must not be overwritten once validated |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` | tier4_phase_output | run_produced | `orch.phase8.drafting_review_status.v1` | Phase 8 status artifact; run_id required |
| `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` | tier5_deliverable | run_produced | `orch.tier5.part_b_assembled_draft.v1` | Updated revised draft (overwrites assembly version) |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not introduce content that contradicts the validated budget.
- Must not fill revision gaps with fabricated content.
- Must not declare Phase 8 complete if critical revision actions are unresolved.
- Must not overwrite a validated checkpoint.

Universal constraints from `node_body_contract.md` §3 also apply.

## Predecessor Gate

`gate_11_review_closure` must have passed (edge registry: `e08e_to_08f`). Verify before any action is taken.

## Terminal Node

This is the terminal node of the DAG (`terminal: true`). A `pass` result for `gate_12_constitutional_compliance` sets `overall_status: pass` in `run_summary.json` (written by the scheduler, not this agent).

---

## Output Schema Contracts

### 1. `final_export.json` — Primary Canonical Output

**Canonical path:** `docs/tier5_deliverables/final_exports/final_export.json`
**Schema ID:** `orch.tier5.final_export.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.tier5.final_export.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after `gate_12_constitutional_compliance` evaluation |
| `export_format` | string | **yes** | Enum: pdf / docx / json_bundle; determined by operator instruction or default |
| `export_path` | string | **yes** | Relative path to the exported file within `docs/tier5_deliverables/final_exports/` |
| `section_index` | array | **yes** | Ordered index of all sections in the export; each entry: `section_id`, `section_name`, `artifact_path` |
| `exported_at` | string | **yes** | ISO 8601 timestamp at time of final export production |

### 2. `drafting_review_status.json` — Phase 8 Tier 4 Status Artifact

**Canonical path:** `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json`
**Schema ID:** `orch.phase8.drafting_review_status.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.phase8.drafting_review_status.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after gate evaluation |
| `section_completion_log` | array | **yes** | One entry per section in the active instrument schema; each: `section_id`, `section_name`, `status` (enum: drafted/assembled/reviewed/revised/final), `artifact_path`, `data_gaps_flagged` (boolean) |
| `revision_actions` | array | **yes** | From `review_packet.json` `revision_actions`; updated with resolution status; each: `action_id`, `section_id`, `severity`, `description`, `status` (resolved/unresolved), `reason` (required when severity: critical and status: unresolved); `all_critical_revisions_resolved` predicate fails if any critical action has `status: unresolved` without a non-empty `reason` |
| `revision_log` | array | **yes** | Non-empty after Phase 8f; each entry: `log_entry_id`, `action_id`, `change_description`, `section_affected`, `performed_at` (ISO 8601) |

### 3. `phase8_checkpoint.json` — Terminal Checkpoint

**Canonical path:** `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`
**Schema ID:** `orch.checkpoints.phase8_checkpoint.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.checkpoints.phase8_checkpoint.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `status` | string | **yes** | Must equal `"published"` for `checkpoint_published` predicate to pass; written only after all Phase 8 gates have passed |
| `published_at` | string | **yes** | ISO 8601 timestamp |
| `gate_results_confirmed` | array | **yes** | Must include (at minimum): `gate_09_budget_consistency`, `gate_10a_excellence_completeness`, `gate_10b_impact_completeness`, `gate_10c_implementation_completeness`, `gate_10d_cross_section_consistency`, `gate_11_review_closure`, `gate_12_constitutional_compliance` |

Note: This checkpoint is immutable once published. Must not be overwritten by subsequent reruns.

### 4. Updated `part_b_assembled_draft.json` — Revised Draft

**Canonical path:** `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json`
**Schema ID:** `orch.tier5.part_b_assembled_draft.v1`

This is an overwrite of the assembly-phase artifact with the revised version. All schema fields apply as defined for `proposal_writer`'s output. The `consistency_log` must reflect revision-phase consistency checks.

---

## Gate Awareness and Failure Behaviour

### Budget Gate Prerequisite (Phase 8 Agent)

`gate_09_budget_consistency` must have passed (verified transitively via `gate_11_review_closure` → `gate_10a_excellence_completeness`, `gate_10b_impact_completeness`, `gate_10c_implementation_completeness`, `gate_10d_cross_section_consistency` → `g09_p01`). Additionally, `gate_12_constitutional_compliance` condition `g11_p07` and `g11_p10` verify budget gate confirmation is present and no section contradicts the validated budget.

If any revision action would require introducing budget-dependent content not confirmed by the budget gate, this agent must flag the action as unresolvable with reason citing CLAUDE.md §13.4.

### Predecessor Gate Requirements

**Predecessor:** `gate_11_review_closure` — must have passed. Source: edge `e08e_to_08f`. Verify via `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_11_result.json`.

If `gate_11_review_closure` has not passed, halt immediately. Write `decision_type: constitutional_halt`.

**Entry gate:** none.

### Exit Gate

**Exit gate:** `gate_12_constitutional_compliance` — evaluated after this agent writes all canonical outputs.

Gate conditions (source: `manifest.compile.yaml`, `quality_gates.yaml`):
1. `gate_11` passed (`g11_p01`)
2. All sections required by active application form present (`g11_p02`)
3. Review packet present (`g11_p03`)
4. All critical revision actions resolved or logged as unresolvable with reason (`g11_p04`)
5. Final export present in `final_exports/` (`g11_p05`, `g11_p05b`)
6. Phase 8 checkpoint published (`g11_p06`)
7. Budget gate confirmation present and no section contradicts validated budget (`g11_p07`, `g11_p10`)
8. No section contains content contradicted by a higher tier (`g11_p08`)
9. No constitutional prohibitions from CLAUDE.md §13 violated (`g11_p09`, `g11_p11`, `g11_p12`, `g11_p13`)

Gate result: `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_12_result.json`. No blocking downstream edges (terminal node). fail_action: "Block final export; log constitutional violation; surface to human operator."

### Failure Protocol

#### Case 1: Gate condition not met (`gate_12_constitutional_compliance` fails)
- **Halt:** Block final export. Do not write `phase8_checkpoint.json`.
- **Write:** `drafting_review_status.json` documenting which revision actions remain unresolved; `final_export.json` must not be produced if `g11_p05` would otherwise fail.
- **Decision log:** `decision_type: gate_failure`; list failed gate conditions.
- **Must not:** Publish the checkpoint before all gate conditions are confirmed. Must not produce a final export with critical unresolved findings.

#### Case 2: Critical revision action unresolvable
- **Document in `revision_actions`:** Set `status: unresolved`, `reason` (non-empty — required); this logs the limitation explicitly as permitted.
- **Write:** Decision log `decision_type: scope_conflict` or `material_decision`; the unresolvability must be grounded in a constitutional or data constraint.
- **Must not:** Silently drop a critical revision action.

#### Case 3: Predecessor gate not passed
- **Halt immediately** if `gate_11_review_closure` is unmet.
- **Write:** `decision_type: constitutional_halt`.

#### Case 4: Revision would introduce constitutional violation
- **Halt that revision action:** Do not apply a revision that would fabricate project facts, invent call constraints, or introduce budget-dependent content without gate passage.
- **Write:** `decision_type: constitutional_halt`; cite CLAUDE.md §13.x.

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: revision_integrator`, `phase_id: phase_08f_revision`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Revision action applied to a section | `material_decision` | Action ID; section ID; change description; source reference for new content |
| Critical revision action cannot be resolved | `scope_conflict` | Action ID; reason for unresolvability; what is needed |
| Budget-dependent revision flagged as unresolvable | `material_decision` | Action ID; CLAUDE.md §13.4; budget gate status |
| Constitutional violation found during revision | `constitutional_halt` | CLAUDE.md section; halted action |
| Checkpoint published | `gate_pass` | Gate ID `gate_12_constitutional_compliance`; all conditions; run_id |
| `gate_12_constitutional_compliance` fails | `gate_failure` | Gate ID; failed conditions; what blocks export |
| `gate_11` predecessor not passed | `constitutional_halt` | Edge `e08e_to_08f`; status |

---

## Constitutional Review

### 1. Scope compliance

`reads_from` and `writes_to` in the front matter exactly match `agent_catalog.yaml`. Concrete write targets: `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` (revised version), `docs/tier5_deliverables/final_exports/final_export.json`, `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json`, `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json`, and `docs/tier4_orchestration_state/decision_log/`. All are declared in the catalog. This agent does not write to `docs/tier5_deliverables/review_packets/` (read-only input) or `docs/tier5_deliverables/proposal_sections/` (input, not modified by revision). No undeclared path access is implied.

### 2. Manifest authority compliance

Node binding is `n08f_revision` (`terminal: true`). Exit gate is `gate_12_constitutional_compliance` — matches manifest. This is the only agent with authority to write `final_exports/` and `checkpoints/`. The Terminal Node section correctly notes that `overall_status: pass` in `run_summary.json` is set by the scheduler (not by this agent). No confusion about runner-owned artifacts (`run_summary.json`, `gate_result.json`, `artifact_status`) exists.

**Checkpoint authority:** The `checkpoint-publish` skill is listed in both the manifest skill list for `n08f_revision` and in this agent's `invoked_skills`. This agent is the only Phase 8 agent with write authority to `checkpoints/`. The must_not constraint "Must not overwrite a validated checkpoint" is in place. The Output Schema Contracts section states the checkpoint is immutable once published.

**Budget gate prerequisite:** The Budget Gate Prerequisite section describes transitive verification (via gate_11 → gate_10d → gates 10a/10b/10c → gate_09) and also the direct check via `gate_12` conditions `g11_p07` and `g11_p10`. Any revision action that would introduce budget-dependent content not confirmed by the budget gate must be flagged as unresolvable. No softening of the budget gate exists.

### 3. Forbidden-action review against CLAUDE.md §13 and §8

- **§13.4/§8.4 — Phase 8 before budget gate:** Budget Gate Prerequisite section is explicit. Failure Protocol Case 4 halts revision actions that would introduce budget-dependent content without gate passage. The `gate_12` conditions `g11_p07` and `g11_p10` verify budget gate confirmation and no section contradicts the validated budget. Risk: low.
- **§13.3 — Fabricated project facts in revisions:** Must_not includes "fill revision gaps with fabricated content." Failure Protocol Case 2 requires setting `status: unresolved` with a non-empty `reason` rather than fabricating content to resolve a critical action. Risk: low.
- **§13.10/§11.4 — Unsupported Tier 5 claims introduced by revision:** The `proposal-section-traceability-check` skill is invoked after applying revision actions to verify the revised draft maintains source traceability. `gate_12` condition `g11_p08` checks "No section contains content contradicted by a higher tier." Risk: low.
- **§13.8 — Finalizing text with incomplete state:** Must_not includes "declare Phase 8 complete if critical revision actions are unresolved." Failure Protocol Case 1 blocks final export and checkpoint if `gate_12` fails. Risk: low.
- **§13.5 — Durable decisions in memory:** Decision-log write path is declared; decision-log write obligations table covers all material events. Risk: low.
- **Checkpoint-before-gate (§9.4):** Must_not includes "overwrite a validated checkpoint." Output schema for `phase8_checkpoint.json` states "immutable once published." Failure Protocol Case 1 explicitly: "Do not write `phase8_checkpoint.json`" if gate_12 fails. Risk: low.
- **§13.1 — Grant Agreement Annex schema:** `evaluator-criteria-review` skill constraint prohibits evaluating against grant agreement annex requirements. Risk: low.

### 4. Must-not integrity

All four must_not items from `agent_catalog.yaml` are present verbatim. Step 6–7 additions do not weaken them. The addition of `gate_12_constitutional_compliance` conditions `g11_p09`, `g11_p11`, `g11_p12`, `g11_p13` (CLAUDE.md §13 prohibitions) as explicit gate conditions creates a stronger enforcement mechanism than the catalog constraint alone.

**Universal constraint note:** `artifact_status` must not be written by the agent — confirmed in Output Schema Contracts field tables for all three produced artifacts.

### 5. Conflict status

Constitutional review result: no conflict identified
