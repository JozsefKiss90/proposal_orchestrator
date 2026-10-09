# Dataset dispositions — what the harness cannot measure, and why

`harness/gold_sets/` and `harness/regression_baselines/` hold only their READMEs, and no Tier 3
project instantiation is present. Every check that reads one of those three absent substrates is listed
below with its disposition. An excluded check is **excluded**: not passing, and
not quietly skipped. Each one is named here with its reason, its replacement evidence and the work
that would lift it.

Authored under ticket V02d of `plans/msca_dn_historical_validation_tickets.md`, which closes part of
finding F08 in `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`. Decision record:
`docs/tier4_orchestration_state/decision_log/msca-dn-dataset-dispositions_2026-10-09.json`.

## The three absences

**No expert-labelled validation data exists for this harness.** `harness/gold_sets/` holds its README
only. Even the seeded, wholly unlabelled template that README describes is absent: `fd38b0a` removed it
as instance-derived harness data. Nothing in this repository establishes the precision or
recall of any judge or assessor against human ground truth. Read no calibration claim into a green
harness lane.

**No Tier 3 project instantiation is present.** The engine stands at its `CLAUDE.md` §2
project-agnostic default, so `docs/tier3_project_instantiation/call_binding/confirmation_checklist.json`
does not exist. Two harness checks read it, and the E5f rubric freeze has not run.

**No E4 golden fingerprints are committed.** The FIELDWISE purge removed the drafter-era sections that
the goldens fingerprinted, and the graph compiler then wrote the sections now in
`docs/tier5_deliverables/proposal_sections/`. The goldens were not refrozen, so there is no committed
prior state to diff the current sections against.

## Dispositions

Fourteen rows, covering seventeen individual checks: one row stands for four. Those seventeen are
every skip the focused acceptance command reports. Thirteen are for the two dataset directories, two
for the Tier 3 checklist, two for the unfrozen E5f artifacts.

| Check | Dataset | Disposition | Reason | Replacement evidence |
|---|---|---|---|---|
| `test_regression_golden.py::TestGoldenSetStanding::test_golden_baselines_are_committed` | E4 goldens | Excluded | No golden set is committed | — |
| `test_regression_golden.py::TestGoldenSetStanding::test_sections_match_golden_set` | E4 goldens | Excluded | Nothing to diff against | `test_regression.py::TestRegressionReport` covers the comparison on fixtures |
| `test_regression_golden.py::TestGoldenSetStanding::test_drifted_sections_are_surfaced_even_when_not_breaking` | E4 goldens | Excluded | Nothing to diff against | `test_regression.py::TestRegressionReport` covers the report contract on fixtures |
| `test_regression_golden.py::TestRubricLaneStanding::test_frozen_rubric_baseline_is_self_consistent` | E5f rubric baseline | Excluded | E5f has frozen no baseline | — |
| `test_measure_ledger_granularity.py::test_report_shape_and_offline` | E4 goldens | Excluded | The report's drafter-era side reads the goldens | Git history only: `32b5606` (the LG-1 record and its commit message carry every measured number). The record was removed from the working tree by `da9f846` |
| `test_measure_ledger_granularity.py::test_prose_byte_identical_all_sub_sections` | E4 goldens | Excluded | Same | Git history only: `32b5606` |
| `test_measure_ledger_granularity.py::test_cardinality_gap` | E4 goldens | Excluded | Same | Git history only: `32b5606` |
| `test_measure_ledger_granularity.py::test_status_axis_graph_honest_vs_drafter_confirmed_heavy` | E4 goldens | Excluded | Same | Git history only: `32b5606` |
| `test_measure_ledger_granularity.py::test_e4_golden_diff_detects_the_gap` | E4 goldens | Excluded | Same | Git history only: `32b5606` |
| `test_expectations.py::TestRealSubstrate::test_golden_paths_resolve` | E4 goldens | Excluded | No golden set is committed | Fixture coverage in the same module |
| `test_gold_set.py::TestSeededExcellenceTemplate` (4 checks) | Gold-set template | Excluded | The seeded template is not in the tree | Fixture coverage in the same module |
| `test_rubric_report.py::TestStandingLane::test_real_spine_register_loads_and_is_fully_confirmed` | Tier 3 checklist | Excluded | No Tier 3 instantiation, so no spine register exists to load | `test_rubric_report.py::TestSpineRegistry` covers the loader contract on fixtures |
| `test_status_faithfulness.py::TestResolveClaimSourceText::test_real_checklist_blob_not_truncated_at_default_cap` | Tier 3 checklist | Excluded | The same absence: there is no real blob to resolve | `TestResolveClaimSourceText`'s fixture cases cover the truncation rule |
| `test_rubric_report.py::TestStandingLane::test_frozen_report_renders_if_present` | E5f rubric report | Excluded | E5f has frozen no report | — |

## What would lift each exclusion

**The Tier 3 checklist rows: a project instantiation.** When a project is instantiated and its
confirmation checklist is written, both checks run against it. Nothing else is needed, and nothing in
this document should be read as asking for one: the project-agnostic default is the engine's intended
resting state.

**The E5f row: the first rubric freeze.** E5f's grading run has not frozen a report.

**The gold-set rows: ticket X03.** Expert-labelled DN validation data, maintained, is the only thing
that lifts them. A human labels it; an AI labelling a gold set for an AI judge reintroduces the
grader–generator correlation the harness exists to detect. See `harness/gold_sets/README.md`.

**The E4 golden rows: an operator refreeze, plus one re-pointing.** The E4 lane is merge-advisory and
human-decided by construction, so the refreeze is the operator's call, not an agent's:

```
py -3.10 -m harness.regression freeze
```

That greens `TestGoldenSetStanding` against the current sections. It does **not** green
`test_measure_ledger_granularity.py`. That suite measures the drafter-era ledger against the
graph-sourced one, and a refreeze replaces the drafter-era side with the graph-sourced side. Its own
module docstring names the consequence. The suite must then be re-pointed at the LG-1 measurement
record recovered from `32b5606`, or re-sourced from git history at the graph-cutover commit. Budget
that work with the refreeze.

## What a green harness lane does and does not say

It says the code behaves as its fixtures specify. It does not say the judge is calibrated, that any
score forecasts an evaluator, or that a comparison against a prior section state has run. Five draws
from one assessor are five draws from one assessor.
