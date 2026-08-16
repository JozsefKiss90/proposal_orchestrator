# Handoff — n08d results, n08e/n08f readiness, open decisions

**For:** the next session, which will (a) run `n08e_evaluator_review`, (b) run `n08f_revision`, and (c) close the operator decisions in §4.
**Branch:** `fieldwise-run-01`. Last commit `c08e028`; only the n08d run outputs are dirty (§7).
**Run-id:** **`845413cf-88d3-4137-9c3f-b5413e679323`** — the consolidated Phase 8 run-id. Every remaining node MUST use it (§2). n01–n07 ride on bootstrapped cross-run evidence; n08a–n08d are released in this RunContext with gates evaluated under this run-id.

**Read first:** `plans/reports/HANDOFF_n08b_results_and_n08c_readiness_2026-08-16.md` and its predecessors. They remain accurate on the free-check recipes and the log-reading trap (drafting emits no `skill START` lines). This document records only what changed on 2026-08-16 afternoon/evening.

---

## 0. TL;DR

1. **n08d is green.** `gate_10d_cross_section_consistency` pass, 7/7 deterministic predicates, run `845413cf`. All 12 assembler consistency checks report `consistent`.
2. All Phase 8 sub-steps are consolidated under one run-id via the reuse channel plus operator-approved `approved_artifacts`. Three lessons about that path are recorded in §2 — read them before invoking anything.
3. **n08e is immediately runnable** (§5). n08f follows it; the checkpoint write-once hazard does NOT exist on this branch (§6).
4. The known test reds are now **7** (was 6): a third stale snapshot test surfaced when `implementation_section.json` came into existence (§4.3).
5. Do not re-run anything before n08e. Do not use a fresh run-id.

## 1. n08d — the numbers

- `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` (schema `orch.tier5.part_b_assembled_draft.v1`, 8.8 KB): a reference-based assembly, not an embedding. Three sections in MSCA-PF Part B order — Excellence 6,852 words, Impact 4,801, Implementation 4,088.
- `consistency_log`: 12 checks CC-01–CC-12, all `consistent`. Highlights: WP1–WP5 ids match across sections (CC-02); partner legal names match Tier 3 (CC-03); D1.1–D5.5 ids, titles and due months agree (CC-04); MS1–MS6 agree (CC-05); person-months agree — fellow 30.0, supervisor 2.5, co-supervisor 2.0, AgroVIR 3.0 in-kind (CC-08).
- CC-12 (informational, deliberate): all three sections report `validation_status.overall_status: assumed`, reflecting declared working assumptions (placement-host details, partner in-kind person-months), "flagged for downstream review" — i.e. for n08e.
- Claim ledgers across the three sections: Excellence 86 confirmed / 3 inferred / 7 assumed; Impact 75 / 3 / 4; Implementation 42 / 5 / 15. Zero unresolved anywhere. Every assumed claim is declaration-keyed.

## 2. The consolidation mechanics — three lessons paid for this session

**Lesson 1 — in-phase siblings are never bootstrapped cross-run, by design.** A `--node` scope seeds upstream *phases* from durable evidence (`runner/__main__.py` ~L362). Nodes inside the target phase stay `pending`: same-run-id resume is the only in-phase evidence carrier (ticket-2/3 operator decision). A fresh run-id for n08d aborted twice on exactly this. **Consequence: n08e and n08f must run under `845413cf`.**

**Lesson 2 — reused cross-run artifacts fail `artifact_owned_by_run` on assumed claims.** The automatic ownership path (`is_reuse_owned_artifact_valid`, `runner/phase8_reuse.py` ~L729) still carries the blanket "no assumed claims" rule the gates themselves dropped. Interim remedy in force: operator-approved `approved_artifacts` entries for `impact_section.json` and `implementation_section.json` in `.claude/runs/845413cf-…/reuse_policy.json`. Durable fix = ticket 7 (§4.1).

**Lesson 3 — a node persisted as `blocked_at_exit` is never re-dispatched.** `is_ready` requires `pending`; no reset flag exists. The sanctioned manual remedy (used once, for n08b): set the node's entry in `.claude/runs/845413cf-…/run_manifest.json` `node_states` back to `"pending"`. That is legitimate because RunContext is §9.2 runtime memory and the scheduler re-proves predecessors from durable Tier 4 evidence at dispatch. Recorded as a ticket-4 checkbox.

Also this session but upstream of n08d: the n08a re-run initially failed on a **fenced-decoy parse bug** — an intermediate assistant turn's `{"placeholder":"see final"}` shadowed the real 14 KB draft. Fixed in `runner/skill_runtime.py::_extract_json_response` (largest-span candidate competition; fences carry no positional priority) with regression tests. Committed.

## 3. What n08e and n08f will judge — the flagged material

No literal placeholder tokens survive in any section (the five n08a-era placeholders died with the n08a re-draft; regex-checked). What remains is Assumed-status **wording**, all declaration-keyed and correct per §12.2:

- Excellence (7): `placement_supervisor_AgroVIR`, `placement_supervisor_title_AgroVIR`, `placement_team_AgroVIR`, `placement_workspace_AgroVIR`, `person_months_ELTE_supervisor`, `person_months_ELTE_co_supervisor`, `person_months_AgroVIR`.
- Impact (4): `placement_supervisor_title_AgroVIR`, `placement_ip_ownership`, `agrovir_relevant_track_record` (twice — two sub-sections make the claim).
- Implementation (15): the placement/hosting cluster plus effort lines; §3.2 deliberately states the absence of AgroVIR EU-funded research participation — thin is correct there, per the still-open checklist item 12.

The evaluator review (n08e) is the designed consumer of CC-12's flag. Expect the review packet to raise these; the correct disposition is "declared working assumption, pending real-world confirmation," not a drafting fix.

## 4. Open decisions — the operator's, deliberately not taken

### 4.1 Ticket 7 — declared-assumed invariant (operator-signed-off, not yet built)

`plans/tickets_phase8_stepwise_execution.md` ticket 7: state as a test "assumed is acceptable iff operator-declared" and apply it to `is_reuse_owned_artifact_valid` and the two `test_excellence_no_assumed_claims`-class snapshot tests. Unblocked, independent of the pipeline. Once landed, retire the `approved_artifacts` reliance (§2.2).

### 4.2 When to hand-correct the Assumed wording

§3 items are flagged, not wrong. The question is whether any get real-world answers (the AgroVIR hosting agreement, the placement-IP written agreement) before submission-grade export (n08f) or stay declared assumptions in the final export. That is a project decision, not a pipeline one — n08f will carry whatever the declarations say at run time.

### 4.3 Third stale snapshot test

`test_phase8_gate_content.py::TestCurrentArtifactState::test_implementation_has_consortium_section` expects a `B.3.2` sub-section id; the fieldwise numbering scheme produces `3.1`/`3.2`. Red since `implementation_section.json` exists (n08c, 2026-08-16) — same stale-snapshot class as the §4.1 pair, different cause (numbering, not assumed-status). Fold into the ticket-7 session or fix separately; either way it is a test rewrite, not an artifact defect.

## 5. n08e readiness

**Dependencies are green.** Edge `e08d_to_08e`, condition `gate_10d_cross_section_consistency` — pass and fresh under `845413cf`. In-context states: n01–n08d all `released`; n08e/n08f absent from `node_states` (defaults to `pending` — no manifest edit needed, unlike the n08b retry).

**Roster** (manifest L265–277): agent `evaluator_reviewer`; skills `evaluator-criteria-review`, `proposal-section-traceability-check`, `constitutional-compliance-check`; exit gate `gate_11_review_closure` (predicates: gate_10d passed; review packet present in `docs/tier5_deliverables/review_packets/`; critical findings categorised by severity; prioritised revision action list produced).

**Command:**

```bash
py -3.10 -u -m runner --run-id 845413cf-88d3-4137-9c3f-b5413e679323 --node n08e_evaluator_review --verbose
```

If gate_11 fails, exhaust the free diagnostics first (gate result predicate detail, the review packet itself) and classify: a finding the review is *supposed* to raise (see §3) versus a machinery fault. If the node lands `blocked_at_exit`, apply the §2.3 pending-reset before retrying.

## 6. n08f readiness

**Runs only after gate_11 passes.** Same run-id. Roster (manifest L279–325): two deterministic components run first — `final_export_writer` (derives `part_b_json_bundle.json` + schema-bound `final_export.json`; idempotent overwrite), then `checkpoint_publisher` (CHK-1; write-once `checkpoints/phase8_checkpoint.json` with cross-run provenance quads for the seven bootstrapped gates in `accepted_upstream_gates`). Skills: `proposal-section-traceability-check`, `drafting-review-status` (produces `drafting_review_status.json`, the g11_p04 artifact — it dispositions the packet's revision actions *without touching the packet*), `constitutional-compliance-check`, `decision-log-update`. Exit gate `gate_12_constitutional_compliance`, 14 predicates.

**Checkpoint hazard: absent on this branch.** `docs/tier4_orchestration_state/checkpoints/` holds only `.gitkeep` — nothing to archive before n08f. (The archive-first rule applies only to *intentional reruns* after a publish; keep it in mind if n08f itself must be re-run after a partial failure that published the checkpoint.)

**Known n08f trap, already fixed in the manifest:** `evaluator-criteria-review` was removed from this node (run `531ec9f0`: its re-run staled `review_packet.json` under gate_11, failing gate_12/g11_p01 forever). Do not "helpfully" re-add it.

## 7. Uncommitted state

Dirty from the n08d run: `gate_10d_result.json`, `part_b_assembled_draft.json` (both untracked), plus the Step-0 call slice and the two `*_845413cf.json` validation reports (modified in place — each audit invocation overwrites them). Commit before running n08e.

## 8. Rules carried forward

- Gate failure is a valid and correct output; never hand-edit claim statuses or gate results to force a green (§15).
- Verify skill/drafting activity by artifact mtimes and embedded run-ids, never by the skill log.
- Same run-id `845413cf` for everything left in Phase 8; a fresh run-id re-creates the §2.1 block.
- A `blocked_at_exit` node needs the §2.3 pending-reset before retry; blocked-node retry needs no force (nothing downstream gated on it).
- Do not spend a run to learn something establishable for free — reuse validation, ownership checks, fingerprints and every gate predicate are replayable offline.
