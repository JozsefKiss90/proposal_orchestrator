# Regression golden baselines (E4)

Frozen fingerprints of the Phase-8 section artifacts in
`docs/tier5_deliverables/proposal_sections/` — the E4 regression golden-set.
One `<section_id>.golden.json` per section, produced by
`harness/regression.py` (`freeze_section_fingerprint`).

Each fingerprint records, per section:

- the **claim ledger** — every `claim_statuses` entry as
  `(claim_summary, status, source_ref)` with its `entry_key` label
  (`C01#171`; bare `claim_id` is not a key — ids repeat across drafting
  blocks),
- the **per-sub-section prose hashes** (sha256 + char count, not the text —
  git history holds the text),
- a **canonical whole-artifact hash** (formatting-invariant).

## What this protects

A prompt change, a drafting soft-cap lift (D2/D3), or a model swap regenerates
the sections. The golden diff (`python -m harness.regression check`, or the
standing pytest lane `-m harness_regression`) surfaces every integrity-relevant
drift: a **removed claim**, a **status change**, a **source_ref swap**, or a
**dropped sub-section** is a *breaking* finding; added claims, prose growth,
prose-changed-while-ledger-unchanged (the escaped-claim risk zone — re-run
E2/E3 there), and a confirmed-share drop are advisory context.

## Merge-advisory, human-decided — never run-blocking

A breaking finding is **advice to a human**, not an automatic block: if the
change is intentional (a sanctioned redraft), refreeze —

```
py -3.10 -m harness.regression freeze
```

— and commit the updated goldens *in the same PR*, so the diff of the golden
files documents exactly what the redraft changed. If the change is not
intentional, investigate before merging. Nothing in `runner` reads these
files; no DAG run consumes this lane (see `harness/HARNESS.md`).

The judge half of the golden set (per-claim grounding baselines via E2's
`freeze_baseline`) is exposed by `freeze_section_grounding` /
`compare_section_grounding` and runs once the pinned judge is live; the
fingerprint lane here is fully deterministic and needs no judge.

## Current status: no golden set is committed

This directory holds this README only. The FIELDWISE purge removed the drafter-era sections these
fingerprints described, and the goldens were not refrozen against the sections that replaced them. The
standing lane therefore records an exclusion rather than a comparison. Every affected check is named,
with the operator refreeze that would lift it, in
[`../DATASET_DISPOSITIONS.md`](../DATASET_DISPOSITIONS.md).
