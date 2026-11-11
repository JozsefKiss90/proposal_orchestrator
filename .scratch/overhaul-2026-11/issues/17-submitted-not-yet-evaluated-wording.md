# 17 — Wording for a submitted document that no ESR has evaluated yet

Status: ready-for-agent
Type: task
Blocked by: None — can start immediately (wave 2, batch O1, parallel with 01 and 04)
Source: `discovery/slice3-esr-review-2026-11-10.md` F1; the first Unresolved gap in
`docs/tier4_orchestration_state/decision_log/msca-dn-resubmission-2026-identity_2026-11-10.json`
Admitted: operator decision D5, `docs/tier4_orchestration_state/decision_log/plan-order-reliability_2026-11-11.json`
Lands: before the O5 re-freeze, so the V14/V16 bundle carries it

## What to build

Three places print fixed sentences that are true for one document and false for another.

1. **The V18 register.** `tools/author_original_workspace.py::render_submitted_register` writes "This file
   is the text the ESR evaluated" and "The ESR evaluated this text" for every submitted document. It files
   the call and submission ids under `historical_submission`. For the 2026 resubmission (ticket 11) no ESR
   exists at V16, so both sentences are false.
2. **The ESR comparison.** `harness/esr_comparison.py::_SCORE_STATEMENT` says the candidate is a sanitised
   derivative. Each row's `historical_proposal_evidence.note` says the submitted document is not
   available. For V14 the candidate is the submission itself.
3. **The operator review.** `harness/operator_review.py` calls the candidate "the materialised sanitised
   copy" and the historical candidate "the earlier sanitised copy". The row heading reads "The same passages
   in the earlier sanitised copy".

After this ticket the wording is keyed on two facts the code already holds:

- the register's `is_submitted_document`, which `compare` already loads;
- whether an ESR evaluated the text (true for the 2025 original, false for the 2026 resubmission).

## Decisions (operator, 2026-11-11, D5)

- Fix before the runs, not after V16.
- Committed sanitised comparisons and reviews replay **byte-equal**. Their wording does not change. Only
  a submitted-document input selects the new wording.
- The 2025 original keeps "the ESR evaluated this text"; that sentence is true for it.

## Acceptance criteria

Failing tests first:

- [ ] A register rendered for the 2026 resubmission on synthetic config contains neither "the text the ESR
      evaluated" nor "The ESR evaluated this text", and says no ESR has evaluated it yet.
- [ ] The 2026 register does not file its call and submission ids under a key named `historical_submission`.
      The 2025 original's register is unchanged byte for byte.
- [ ] A comparison whose register declares `is_submitted_document: true` carries a score statement that
      names assessor variance, the profile and the extraction, and does not call the candidate a sanitised
      derivative.
- [ ] In that comparison each row's `historical_proposal_evidence.note` does not say the submitted document
      is unavailable.
- [ ] An operator review over that comparison does not call either candidate a sanitised copy, in the
      inventory notes or in the row heading.
- [ ] Every committed comparison and review under `docs/tier4_orchestration_state/msca_dn/comparisons/`
      replays byte-equal.

Then:

- [ ] Targeted tests pass, including every module that imports a changed module (wave-1 lesson).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.
- [ ] Full suite at or above `plans/overhaul/BASELINE.md` §5 (operator, after merge).
- [ ] Acceptance lane GREEN (operator, after merge). The touched modules are lane modules.
- [ ] The identity record's first known gap is closed by a successor note or record (§9.4).

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/17-submitted-not-yet-evaluated-wording.md   Base commit: 60fca14e (step 0 on harness_overhaul)
Read first: CLAUDE.md §9, §12, §16–17; CONTEXT-MAP.md (+ harness/CONTEXT.md); docs/agents/*.md;
            plans/overhaul/BASELINE.md §5; .scratch/overhaul-2026-11/discovery/slice3-esr-review-2026-11-10.md;
            docs/tier4_orchestration_state/decision_log/msca-dn-resubmission-2026-identity_2026-11-10.json
Seam: wording selection only. No change to counts, bindings, hashes of inputs, or refusal rules.
Do not touch: the committed comparisons, reviews, registers and the 74.60 baseline; Tier 1–3 docs;
              V17 configuration code; the importer's document set.
Skills: tdd, then code-review since the base
Tests to run: every module that imports a changed module. On 2026-11-11 that grep
              (esr_comparison | operator_review | author_original_workspace) found 19 modules:
              tests/harness/test_{authority_matrix,comparison_diff,converse_judge,converse_smoke,
              deferral_register,esr_comparison,execution_receipt,historical_profile,operator_review,
              semantic_adjudications}.py; tests/runner/test_anonymisation_policy.py;
              tests/test_msca_dn_{anonymised_derivative,approved_dispositions,authority_matrix,
              deferral_register,historical_profile,original_import_route,pe09_runbook,
              successor_dispositions}.py. Re-run the grep before you commit.
Size: ~40–80 changed non-test lines
Record: a successor note to the identity record's first known gap (§9.4)
```

## Out of scope

- Any ESR record for 2026; V16 has none.
- The runbook (H1 owns it).
- Slice 3 F2 and F3 (runbook notes, H1).

## Comments
