# Faithfulness gold sets (E1.5)

Human-labeled `(claim, source_ref, supported?)` triples used to **calibrate the
judge** (`harness/calibration.py`). The judge's precision/recall against these
labels is what lets a metric graduate from *advisory* to *human-gating* — until
the judge clears the bar, everything stays advisory.

## The one rule: the label is a human's, not the engine's

`supported` is the **human ground truth**: does the cited source *genuinely*
support the claim? It is deliberately **not** the engine's `status`
(`confirmed` / `inferred` / `assumed`). The whole reason to calibrate is that the
engine can stamp a claim `confirmed` while its source does not actually support
it — a "gap masked as confirmed." The engine's `status` is carried as
`engine_status` (a prior, informational only).

An AI must **not** fill these labels: an AI labeling the gold set for an AI judge
reintroduces exactly the grader–generator correlation the harness exists to
avoid. Labeling is a human task.

## Files

- `faithfulness_gold_excellence_TEMPLATE.jsonl` — a **seeded template**: 30 real
  candidate pairs drawn deterministically (stratified by status) from
  `docs/tier5_deliverables/proposal_sections/excellence_section.json`'s
  `claim_statuses`. Every pair is **unlabeled** (`supported: null`,
  `labeling_status: TO_BE_LABELED_BY_HUMAN`). This file is the starting point,
  not a usable gold set — calibration on it fails closed until a human labels it.

## How to produce a usable gold set

1. Copy the template to a working file, e.g.
   `faithfulness_gold_excellence.jsonl`.
2. For each pair, a human:
   - opens the `source_ref`, finds the passage that bears on the `claim`, and
     pastes it into `source_excerpt` (keeps calibration self-contained and
     bounded);
   - sets `supported` to `true` if that passage genuinely states/entails the
     claim, `false` otherwise;
   - optionally sets `labeler` and a `note`.
3. Load it with `load_gold_set(path)` (default `require_labeled=True`) — it will
   refuse any pair still unlabeled.
4. Calibrate: `calibrate_with_judge(gold_set, judge, ...)` → a `CalibrationReport`
   recording `{judge_model, judge_version, precision, recall}`; feed it through
   `graduation_for(judge.config, report)` to get the advisory / gating decision.

Re-label and re-run whenever the pinned judge model or version changes — a repin
re-opens the advisory-only state (`CalibrationReport.applies_to` /
`graduation_for` enforce this).
