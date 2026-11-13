# V14 — diagnosis record, public part

**State:** recorded, 2026-11-13. The categories, the three questions and the list of what returns are confirmed by the operator. Sections 1 to 5 carry the counts the operator's private record returned in H08f-r (sitting 3). Each divergence has an operator-decided entry; none is decided by rule.

The agent wrote this from material the repository may hold: the committed ESR record, the H09 return,
the H08d status, the operator's counts in `RUNLOG.md`, and the sanitised lineage's committed records. The
agent has not read the comparison, the dispositions, the review or any sample. Which observations are misses
is a disposition, so under V14-OP2 it stays on the host. This file therefore names no miss by id.

The diagnosis of each divergence lives in a private record on the host (runbook section 6: "Record each as a
Tier 4 note in the private environment"). This file holds its binding and its counts once the operator returns
them.

## Bindings

| Item | Value | Source |
|---|---|---|
| Frozen original baseline | `blind_baseline_f5c99a91adc9.json`, sha256 `f5c99a91…24bd`; freeze record `307d93fe…1add` | H06, H08d |
| ESR record | `msca-dn-2025-original-esr.json` (successor), sha256 `5c9b9c8e…b0a9` | H08a |
| First integrity audit | `integrity_96a09b983831_0001.json`, sha256 `fa24f1e1…05c0` | H08b, H08d |
| First comparison | `comparison_f5c99a91adc9_0001.json`, sha256 `d24dd56d…08ea` | H08d |
| Successor dispositions | `dispositions_second.json`, sha256 `ed323756…052b`, all 29 rows `operator_confirmed` | H08d, operator |
| Successor comparison | `comparison_f5c99a91adc9_0002.json`, sha256 `06fd1a7d…b796` | H08d |
| Review of the successor | `operator_review_06fd1a7d5919_0001.md` `eba8d44d…abe3`; `operator_decisions_06fd1a7d5919_0001.md` `8de0425a…0c7e` | H08d (V14-D3) |
| Private diagnosis record | `esr_work/diagnosis_private.json`, 12,098 bytes, mode 600, sha256 `ac7b8eb28d57a30b070c78a497c1109d314575eec227996f79a2c752ef9aa065`, written 21:18:09Z; binds the report `f5c99a91…24bd` and comparison `…_0002` `06fd1a7d…b796` | H08f-r, H08d status2 |

**Preserved unchanged (checked 2026-11-13 against the tag `msca-dn-freeze-2026-11-12`).** The sanitised 74.60
baseline and its freeze record (`baselines/resolved_fixes_2026-10-06/`), the approved dispositions
(`dispositions_f60ae6e0a2a1_approved.json`, `90484fcb…`) and the approved comparison
(`comparison_f60ae6e0a2a1_0003.json`, `14508ee2…`) have no change since the tag. The V14 result is a successor
lineage. It does not edit them.

## Diagnosis categories

The ticket names six. Each divergence takes exactly one, with a status from `CLAUDE.md` section 12.2. The
definitions below were drafted by the agent and confirmed by the operator on 2026-11-13.

| Category | Use it when |
|---|---|
| Evidence omission | The original carries the evidence, but the assessor's input did not: the pack selection or the input budget left it out. |
| Extraction | The original carries the evidence, but the extracted text lost or garbled it (tables, figures, reading order). |
| Rubric interpretation | The input carried the evidence. The assessor read it under a rubric or expectation that asks something other than the ESR asked. |
| Assessor error | The input carried the evidence, and the rubric asks the right thing. The assessor still misread it, for example by asserting an absence the input contradicts. |
| Historical subjectivity | The evidence and the reading are sound. The ESR's judgement is one an evaluator could reasonably make either way. |
| Unresolved cause | The evidence does not separate two or more of the above. The record names which. |

Three questions separate them, in this order. Is the evidence in the submitted original (the PDF, on the
workstation)? Is it in the extracted candidate on the host? Is it in the pack or criterion input the assessor
received?

## 1. Criterion deltas

The repository may hold these numbers in full (V14-OP2).

| Criterion | Weight | ESR | Blind (H09) | Difference | Spread, 5 samples |
|---|---|---|---|---|---|
| Excellence | 50 | 4.2 | 4.1 | −0.1 | 0.1 |
| Impact | 30 | 4.5 | 3.8 | −0.7 | 0.0 |
| Implementation | 20 | 4.2 | 4.1 | −0.1 | 0.0 |
| **Total** (S = 10·E + 6·I + 4·Impl) | | **85.8** | **80.2** | **−5.6** | |

- No deduction is attributed to any individual criticism.
- The sanitised −11.2 is not carried forward and is not a predictor. The original and the sanitised copy are
  two documents under two profiles and two baselines.
- The spreads are within-assessor repeatability of one pinned assessor. They are not an accuracy interval and
  not a panel of reviewers.
- The H09 cell `imp-magnitude` is the one uncovered cell (0.55). That is an observation, not a diagnosis of the
  impact difference.
- One draw on the implementation criterion was discarded and redrawn (V14-F9). Its thrown text is not a sample.

**Recorded.** All 3 deltas: `unresolved_cause`, `Assumed`, decided by the operator. So no criterion difference is
attributed to one cause. Which causes each entry names stays in the private record.

## 2. Misses

The operator reports 13 misses in the first comparison, 5 of 15 criticisms detected (0.33), and 16 of 29
observations detected. The successor's numbers are not yet returned. In `dispositions_second.json` the 13 misses
carry `failure_mode: undetermined`, quotes selected by script, and status `Assumed` (V14-L2).

The runbook's section 2.1 names the rows that only the original can answer: ESR-E-02, ESR-E-04, ESR-E-05,
ESR-E-08, ESR-E-S03, ESR-E-S05, ESR-I-S01, ESR-I-S04, ESR-Q-01, ESR-Q-03, ESR-Q-S02 and ESR-Q-S03. ESR-E-04 was
`Unresolved` in the sanitised lineage. Whether any of these is among the 13 is private.

**Recorded.** The successor comparison returns 16 detected and 13 not detected, 0 partially observable, 0 not
assessable and 0 addressed. It equals the comparison file. All 13 misses: `unresolved_cause`, `Assumed`, decided by
the operator. Which causes each entry names stays in the private record. The operator did not check whether each script-selected quote is relevant (V14-L2), so
Q2 is not settled for these rows. No miss is attributed to evidence omission or to extraction.

The operator judges that three of the 13 look detected on reading, two of them criticisms (RUNLOG V14-F12). The
record keeps them as misses. If all three were detections, 19 of 29 observations and 7 of 15 criticisms (0.47)
would be detected. Carried to V15 as an open question.

## 3. False positive

One, recorded by the operator: a shortcoming on the implementation criterion in 5 of 5 samples, diagnosed
`rubric interpretation`.

**Recorded.** `rubric_interpretation`, `Inferred`, decided by the operator; its basis is in the private record.
Whether it is AVC-01 or AVC-02 recurring: no (Inferred). It is present in 5 of 5 samples, and neither case recurs in
more than one sample (section 5).

## 4. Contested strengths

The sanitised lineage had 8: ESR-E-S03, ESR-E-S05, ESR-I-S01, ESR-I-S02, ESR-I-S04, ESR-I-S05, ESR-Q-S02 and
ESR-Q-S03 (`comparison_f60ae6e0a2a1_0003.json`). The first original comparison has 0.

At the tag, a strength row counts as contested only when its `blind_findings` lists a blind finding of polarity
`shortcoming` (`harness/esr_comparison.py`, the `contests` line). So 0 records which findings the dispositions
link. It is not a measurement that no blind shortcoming sits on a praised point.

**Recorded.** All 8 `unclear`, decided by the operator. So the record does not show, for any of the 8, whether the
H06 baseline holds a shortcoming on the same point. Status: Unresolved.

## 5. AVC-01 and AVC-02, at sample level

From `dispositions_f60ae6e0a2a1_approved.json`, `assessor_validation_cases`, and runbook section 2.3:

- **AVC-01.** In the sanitised lineage, one implementation sample stated that no intermediate milestones are
  shown, though its input carried the milestones table. Does the stage-A assessor repeat the claim against the
  original? Never edit a milestone to satisfy it.
- **AVC-02.** Four of five implementation samples credited the deliverables table with the milestones table's
  verification column. Does the stage-A assessor conflate the two tables against the original? This one needs the
  original.

**Recorded**, per sample, by the operator:

| Case | Repeated against the original | Not repeated | Unclear |
|---|---|---|---|
| AVC-01 | 0 of 5 | 5 of 5 | 0 |
| AVC-02 | 0 of 5 | 4 of 5 | 1 |

Neither sanitised-lineage case recurs against the original in any sample read as clear.

## What returns to the repository

Confirmed by the operator on 2026-11-13, under V14-OP2 as written: the private record's sha256; per class, the count of each category and
status; AVC-01 and AVC-02 as counts out of 5; and the successor comparison's summary counts. No id of a miss, no
text and no quote.

## Returned counts (H08f-r, `V14_H08f_return.json`)

| Class | Category or answer | Status | Decided by |
|---|---|---|---|
| Misses (13) | `unresolved_cause` 13 | `Assumed` 13 | operator 13 |
| False positives (1) | `rubric_interpretation` 1 | `Inferred` 1 | operator 1 |
| Criterion deltas (3) | `unresolved_cause` 3 | `Assumed` 3 | operator 3 |
| Contested strengths (8) | `unclear` 8 | | operator 8 |
| AVC-01 (5 samples) | `no` 5 | | operator 5 |
| AVC-02 (5 samples) | `no` 4, `unclear` 1 | | operator 5 |

`total.decided_by_rule=0`. The notes, ids and per-row answers stay in the private record.
