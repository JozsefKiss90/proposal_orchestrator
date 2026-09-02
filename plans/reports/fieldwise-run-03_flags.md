# FIELDWISE run-03 — pre-run consistency report and manual-edit flag list

Date: 2026-09-02. Branch: `fieldwise-run-03`. Authority:
`decision_log/fieldwise-run03-instantiation_2026-09-02.json`.

This file has two audiences. The operator reads it before dispatching Phases 1–8 from the
CLI. The condensation pass reads it when turning the run-03 export into the submission
master.

## Pre-run consistency results (all mechanical checks pass)

- All 17 Tier 3 JSON files parse.
- WP containers are WP1 (merged, M1–M14), WP3, WP4, WP5. WP2 no longer exists; every
  remaining "WP2" string in Tier 3 is a historical or Pack-citation note, not a container
  reference.
- 27 tasks, 11 deliverables. Every task has a month allocation inside its WP range. No
  duplicate ids.
- Milestones: MS1 (M2), MS6 (M3, model freeze), MS2 (M14), MS3 (M18), MS4 (M24),
  MS5 (M30). All link to existing WPs and fall within the 30-month duration.
- Every KPI traces to an existing deliverable; every deliverable has at least one KPI.
- Every objective addresses an existing WP, and every WP is addressed by an objective.
- Fellow person-months sum to exactly 30.0 (merged WP1 carries 9.0).
- All referenced declaration keys exist in `working_assumptions.json`;
  `hollos_supervisor_acceptance` is withdrawn as intended.

No phase blocker was identified. The gates that re-evaluate against changed fingerprints
will do so fail-closed (ST-1); an honest failure there is reviewable output, not a defect
in this update.

## Watch items for the phase run (operator)

1. **Phase 4 concurrency, M1–M3.** OD-1 front-loads T1.1–T1.5 (M1–M2) and T2.1–T2.3
   (M2–M3) alongside WP4's M1 start. The seed documents the constraint; the
   phase_04_gate concurrency check is the arbiter. If it fails, that is an honest gate
   failure to review, not something to pre-fix by hand.
2. **Phase 6 supervision narrative.** The spine is entirely Assumed. Drafts must carry the
   supervision arrangement flagged as pending written confirmation, per §13.8.

## Manual-edit flags for the condensation pass

1. **Display renumbering.** Apply the recorded display mapping: WP1→"WP1", WP3→"WP2",
   WP4→"WP3", WP5→"WP4"; task and deliverable display ids follow the displayed WP number.
   The mapping's single authority is `workpackage_seed.json`
   `_provenance.od1_merge_2026_09_02`.
2. **Supervisor track record.** Prof. Janda's publications and profile for §3.2/§1.3 must
   be drawn from the committed CV
   (`source_materials/cv/JT_CV-HUN-2025-MGI-Janda-Tibor.pdf`) and his Scholar profile.
   Tier 3 deliberately carries no publication list for him; do not author one from memory.
3. **"HUN-REN-led predictive workflow."** The Pack-lifted one-sentence summary in
   `project_summary.json` still says this. With ML leadership now on the ELTE side, the
   condensed text should say "HUN-REN-hosted" or name both strands. Check the wording.
4. **OD-2 coverage check.** The instruction was "don't change anything if already covered
   in the draft." Compare the regenerated hierarchy passage against the 2026-08-30 master
   before replacing it.
5. **Assumed content stays visible.** The spine, Farmer 2, and the standing OD-4/5/6
   declarations appear in the draft with their Assumed flags. Do not condense the flags
   away.

## Open inputs (chase before the 2026-09-06 freeze)

- Written confirmations: Janda supervision seat, Hollós ELTE-side ML seat, Jung
  continuation, ATK hosting/contact, Farmer 2 backup access.
- Prof. Janda's ORCID and position details (arrive with ATK's confirmation).
- ELTE-side ML team member person-months (Hollós): not quantified anywhere; an evaluator
  may ask. Operator to supply or accept the gap.
- Steering-calendar ratification note (R3-D9): MS1/MS6 verdicts are ratified at the M6
  meeting. This is an operator note, not partner writing — confirm or amend.
- OD-4/5/6 fallbacks stand; MATE, farmer and AgroVIR confirmations still convert
  Assumed→Confirmed if they arrive before the freeze.

## Schedule

| Date | Action |
|------|--------|
| 2026-09-02 | Tier 3 updated on `fieldwise-run-03` (this record) |
| 2026-09-03/04 | Operator runs Phases 1–8 from the CLI |
| 2026-09-04/05 | Condensation of the run-03 export; flags above applied; operator review |
| 2026-09-06 | Submission master frozen (hash recorded, ticket T10) |
| 2026-09-07/08 | Buffer; portal upload |
| 2026-09-09 | Call deadline |
