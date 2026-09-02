# Tickets — Proposal Issues Remediation (2026-09 submission window)

Status: ACTIVE. Governs the remediation of `plans/proposal_issues.md` against the
submission master for the 2026-09-09 deadline (HORIZON-MSCA-2026-PF-01-01).

Session decisions behind this file:
`docs/tier4_orchestration_state/decision_log/fieldwise-proposal-issues-triage_2026-08-31.json`.
Open decisions (issues #1, #4, #5, #8) live in
`plans/reports/FIELDWISE_open_decisions_round2_2026-08-31.md` — they are NOT tickets here
until answered; ticket T9 applies their answers.

## Ground rules

1. **Submission master** = `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_manual-condensed_2026-08-30.docx`
   (edit as a dated copy per ticket T0; never edit the 2026-08-30 file in place).
2. **Paired edits.** Every content ticket lands in TWO places in the same pass: the
   submission master AND the matching Tier 3 artifact. The repo must never contradict the
   submitted text (CLAUDE.md §11.4). Where Tier 3 already carries the correct content, the
   Tier 3 half is a verification, not an edit.
3. **No new facts.** Tickets only reword, re-insert existing Tier 3 content, or weaken
   claims. Anything that would strengthen a claim or add a project fact belongs in the
   open-decisions doc, not here (§13.3).
4. **Operator runs all pipeline phases from the CLI.** No ticket dispatches the runner.
5. **Schedule spine:** open-decision answers needed by **2026-09-03 EOD**; apply answers
   2026-09-04/05 (T9); freeze master **2026-09-06** (T10); upload by 2026-09-08.

## Tickets

### T0 — Working copy of the submission master
Create `FIELDWISE_Part_B1_master_2026-09.docx` as a copy of the 2026-08-30 condensed docx;
all subsequent tickets edit the copy. The 2026-08-30 file stays as the pre-remediation
snapshot.
- Verify: both files exist; git tracks the new copy.

### T1 — Issue #11: career-development wording
- Docx: replace "single remaining competence gap" with "principal methodological
  competence gap" (phrase exists only in the manual docx; not present in Tier 3).
- Tier 3: verify `project_brief/training_and_career_development.md` does not carry the
  "single remaining" formulation (confirmed absent 2026-08-31); no edit expected.
- Verify: phrase search over the docx returns zero hits for "single remaining".

### T2 — Issue #12 + closure framing (¶14/¶16 of proposal_issues.md)
- Docx: insert the one-sentence model explanation ("the model learns the relationship
  between operational predictors — soil-water, weather, spectral/EO data — and an
  independently measured physiological water-stress target") at the first model mention;
  align the research-gap statement and the closure narrative (five-season dataset →
  unseen-year validation → pre-season freeze → prospective commercial-field test →
  validated functions into DrR MVP) with ¶14/¶16.
  NOTE: the "freeze before the new field season" clause in ¶16 depends on OD-1; until
  OD-1 is answered, use the closure narrative WITHOUT a freeze-timing commitment.
- Tier 3: `project_brief/concept_note.md` — verify the central-research-question and gap
  sections carry the same formulation; patch wording only where they diverge.
- Verify: the core sentence appears verbatim (or near-verbatim) in both surfaces.

### T3 — Issue #2: the eleven KPIs
- Docx: re-insert K1–K11 from `architecture_inputs/impacts.json` (`kpis.items`, all
  Confirmed, each traceable to a deliverable) in condensed table form; or, if page budget
  forbids, name all eleven in running text. The bare "11 KPIs" claim must not stand
  without the list.
- Tier 3: source already correct — verification only.
- Verify: count of KPI identifiers in the docx = 11; each maps to a deliverable id that
  exists in `workpackage_seed.json`.

### T4 — Issue #3: RQ1–RQ5
- Docx: re-insert RQ1–RQ5 from `project_brief/concept_note.md` (§Research questions),
  condensed as needed; or remove the RQ numbering everywhere. Preference: re-insert.
- Tier 3: source already correct — verification only.
- Verify: every "RQn" reference in the docx resolves to a stated RQ.

### T5 — Issue #6: decision-value framing
- Docx: remove/reword any implication that FIELDWISE proves water savings. Decision value
  = correct stress detection, lead time, uncertainty honesty, usability, and
  irrigation-attention relevance. Literature magnitude context (8–30% range) may remain
  as context, never as a project promise (this matches the existing Tier 3 discipline).
- Tier 3: `architecture_inputs/impacts.json` `adopted_claim_form` — align the "will
  quantify its own outcome prospectively and report water saving" sentence with the
  sharper #6 framing: prospective water-saving quantification may only be claimed to the
  extent the farmer-field irrigation-treatment arrangement (working assumption
  `farmer_field_access`) actually supports it; otherwise report detection/lead-time/
  uncertainty outcomes. Also mirror in `project_brief/strategic_positioning.md` line ~75.
  Flag for OD-2/OD-3 owners if the boundary is unclear.
- Verify: no sentence in the docx asserts a project-attributed water-saving figure or
  "proves/demonstrates water savings".

### T6 — Issue #7: Skanzen contingency demotion
- Docx: where the Szentendre Skanzen model-garden contingency appears, state explicitly
  that activation preserves the physiological measurement programme but does NOT
  substitute for independent commercial-field transferability evidence; if activated, the
  commercial-transferability claim is downgraded/deferred and reported as such.
- Tier 3: `architecture_inputs/risks.json` — mirror the demotion in the relevant risk's
  mitigation text; `architecture_inputs/workpackage_seed.json` T3.6 note — append the
  same boundary.
- Verify: contingency text in all three surfaces carries the measurement-backup-only
  boundary.

### T7 — Issue #9: AgroVIR placement presentational reframe
- Docx: rewrite the placement passage to lead with what the placement delivers —
  monthly structured face-to-face technical reviews, protected-data interoperability
  work, MD-level named supervisor (Miklós Maróti), pre-placement access testing (T4.5) —
  and drop the phrase "mainly remote". FACTS UNCHANGED: the arrangement remains the
  Confirmed mainly-remote-with-monthly-f2f arrangement of the 2026-08-28 supersession
  record; no wording may imply routine on-site presence (§13.3).
- Tier 3: no factual edit. `consortium/partners.json` `placement_arrangement` and
  `roles.json` keep the plain factual description (internal records need no reframing).
- Verify: docx contains no "mainly remote"; docx contains no claim of on-site work
  beyond monthly meetings.

### T8 — Issue #10: cross-crop claim discipline
- Docx: claims limited to — processing tomato is validated; the architecture (T2.6
  crop-transfer specification, crop-configurable DrR core) is designed for later
  adaptation to other irrigated high-value crops. No implied cross-crop validation.
- Tier 3: `workpackage_seed.json` T2.6/D2.2 already carry the correct boundary —
  verification only.
- Verify: no sentence claims validation on any crop other than processing tomato.

### T9 — Apply confirmed open-decision answers (2026-09-04/05)
For each OD in `FIELDWISE_open_decisions_round2_2026-08-31.md` answered by 09-03 EOD:
apply the confirmed answer as a paired edit (docx + named Tier 3 landing artifact +
`working_assumptions.json` status flip Assumed→Confirmed where applicable, with the
confirmation source recorded in `call_binding/confirmation_checklist.json`).
For each OD NOT answered: apply its stated fallback and record the miss in the decision
log. OD-1 adoption additionally ripples: Gantt/milestones (`milestones_seed.json`),
KPI anchoring check (K1–K11 vs. shifted deliverable months), and T2's closure narrative.
- Verify: every OD is either applied-confirmed or fallback-applied; none silently open.

### T10 — Freeze the submission master (2026-09-06)
- Record the frozen docx's SHA-256 in the decision log (append to the triage record or a
  new freeze record); commit. After freeze, only defect fixes with operator sign-off.
- Verify: hash recorded; working tree clean.

### T11 — Divergence + submission record
- Author `decision_log/fieldwise-submission-2026-09-09_<date>.json`: what was submitted,
  the frozen hash, every known divergence between the submitted text and Tier 1–4 state
  (target: zero content divergences given the paired-edit rule; condensation/formatting
  divergences listed as a class), and the §13.8 flags that went in unresolved (unanswered
  ODs). Update `MEMORY`-relevant state is NOT part of this ticket (agent-side concern).
- Verify: record exists and enumerates ODs by id with final status.

### T12 — POST-SUBMISSION: fieldwise-run-03 reconciliation run
Operator-run (CLI), after 2026-09-09:
1. Branch/run-id `fieldwise-run-03`; Tier 3 is already synced (paired edits), so step one
   is a Tier 3 consistency read-through, not a transcription.
2. **Archive `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` before
   the rerun** (write-once guard) — as established after run d0675cf5.
3. Rerun Phases 1–8 from the CLI; gates re-evaluate against the updated fingerprints
   (ST-1 content-based staleness makes stale gates fail closed, as intended).
4. Compare the regenerated Part B export against the frozen submitted docx; log residual
   presentation-only differences. The pipeline export is the durable record; the frozen
   docx remains the submitted artifact of record.
- Verify: run-03 gate results green through gate_12, or failures logged as honest gate
  failures (§15); comparison report written to `docs/tier4_orchestration_state/`.
