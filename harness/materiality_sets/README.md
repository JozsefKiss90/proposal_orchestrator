# Materiality sets (E3)

Calibration data for the **§10.5 materiality classifier**
(`harness/materiality.py`) — the bar that decides which prose assertions the
escaped-claim detector (`harness/claim_ledger.py`) requires a `claim_id` for.
Without this bar the "unledgered assertion" diff floods with transitions and
framing and gets ignored; with an uncalibrated bar, a misclassified material
assertion is a silently missed escape.

## The two-anchor rule (who labels what)

- **Positives are the engine's own enumeration — auto-labeled, legitimately.**
  `materiality_positives_ledger.jsonl` carries the de-duplicated
  `claim_summary` values of all three real sections' `claim_statuses`
  (393 examples, `material: true`, `origin: ledger`, each tagged with its
  disambiguated `entry_key`). The ledger *is* what the engine treats as
  material-and-attributable (ticket E3: "§10.5 says *what*; the ledger says
  *which*"), so no human or AI invented these labels.
- **Negatives are a human's call — never fabricated.**
  `materiality_negatives_TEMPLATE.jsonl` holds 30 deterministically-drawn
  candidate sentences from the sections' prose, all **unlabeled**
  (`material: null`, `labeling_status: TO_BE_LABELED_BY_HUMAN`). A human
  labels each `false` (genuine framing / transition / definitional prose) or
  `true` (actually a material claim the seeder happened to pick). Unlike the
  positives, "this sentence is non-material" is not something the engine ever
  asserted — an AI filling these labels would reintroduce the
  grader–generator correlation the harness exists to avoid (the E1.5 rule).

## What is measurable when

- **Now (positives only):** classifier **recall** over the ledger positives —
  the number that bounds the risk of a material assertion being misclassified
  non-material (a silently missed escape). `calibrate_materiality` computes it
  immediately.
- **Not yet — precision.** With zero labeled negatives the confusion matrix's
  precision would be a spurious `tp/(tp+0) = 1.0`, so
  `MaterialityCalibration` forces `precision: null` until labeled negatives
  exist. Label the template to unlock it.
- Every `LedgerCompletenessResult` report stamps the calibration state in its
  notes (`uncalibrated` / `partially calibrated: recall=… precision
  unmeasured` / `calibrated`), so a reader always knows how much to trust the
  non-material exclusions.

## Workflow

1. Copy `materiality_negatives_TEMPLATE.jsonl` to a working file, label each
   example's `material`, optionally set `note`.
2. Merge with the positives (both files are JSONL of the same
   `MaterialityExample` shape) and run
   `calibrate_materiality(examples, judge)` → recall **and** precision,
   keyed to the pinned judge (`applies_to`; a repin re-opens the
   uncalibrated state).
3. Pass the resulting `MaterialityCalibration` to
   `evaluate_ledger_completeness(..., materiality_calibration=...)` so the
   report's trust note reflects it.

Regenerate both files after M2-T10 re-points the sections at graph-sourced
artifacts (`seed_materiality_positives` / `seed_negative_candidates` are
deterministic).
