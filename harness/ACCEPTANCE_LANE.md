# The PE-09 acceptance lane — what it covers, and what a green result does not say

One command reproduces the acceptance suite:

```
py -3.10 -m harness.commands.acceptance_lane
```

It runs every module the declaration names, then reads the run back against that declaration.
`--list` prints the declaration and runs nothing. `--area NAME` and `-k EXPR` narrow the run and stamp
the result PARTIAL, because a narrowed run is a diagnostic.

The declaration is data, not code: `harness/acceptance_lanes/msca_dn_historical.json` holds the areas,
the exclusions and the audit baseline, and `harness/acceptance_lane.py` reads it. The reader carries no
instrument name, which is the same separation `harness/profile.py` keeps from its profiles, and which
`tests/harness/test_profile.py` lints over all of `harness`. With several declarations in the tree,
`--lane NAME` names one and an unqualified run refuses rather than guessing.

Authored under ticket V03 of `plans/msca_dn_historical_validation_tickets.md`, which closes finding
F08 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`. Decision record:
`docs/tier4_orchestration_state/decision_log/msca-dn-acceptance-lane_2026-10-09.json`.

## Why areas and not a path list

The audit's own finding was that a count is not coverage. Its focused command passed 1,864 cases at
`ca0a443`, and four reproduced defects still got through. A count answers whether anything broke. It
does not answer whether the thing about to be accepted is checked at all.

So the lane is declared as areas. Each area names one acceptance invariant and the modules that check
it. A reader asks which invariant covers the importer and gets a named answer. Three guards keep the
declaration from rotting:

- An area naming a module that is not in the tree fails the lane before any test runs.
- A module inside the audit's own focused command and outside every area fails the lane the same way.
  The lane is a superset of that command by construction.
- A declared exclusion the exclusion document does not name fails the lane, and so does an
  exclusion sitting in an area the run depends on. Both are checked by the command before any test.
- `tests/harness/test_acceptance_lane.py` asserts all of it, plus every claim this document makes.

A fourth guard came from the lane's own first run. A disposition row named
`TestRealSubstrate::test_golden_paths_resolve`, and the class had been renamed to
`TestCriterionSectionMap`. The row matched nothing, so the exclusion read as declared while the skip
read as undeclared. The lane reported both halves, the row was corrected, and a test now asserts that
every exclusion names a class its module actually defines.

## The environment

The lane refuses to certify a result on an extraction build that was not measured to reproduce the
committed import artifacts. PyMuPDF 1.28.2 with MuPDF 1.28.2 is the pin V01 established; the measured
alternatives are in `runner/extraction_environment.py`. An off-pin build derives a different document
identity, so a green importer area under it would certify a replay of a different document.

`--allow-unreproducing-build` runs anyway and stamps the result NOT CERTIFIED. It is for an engineer
measuring a new build, not for accepting one.

## The thirteen areas

Seven areas carry invariants the historical run depends on. The other six carry the rest of
the audit's focused command, kept rather than dropped. Every declared exclusion sits in an area
marked **no**, and the lane refuses to run when one does not — that is how
*no exception covers a check the historical run depends on* is measured rather than asserted.

The E4 golden-set and E5f rubric lanes live in their own **regression** area for exactly this
reason. `harness/HARNESS.md` makes them merge-advisory and human-decided, so the historical run
does not depend on them, and four of their checks are excluded.

| Area | Run depends on it | Invariant | Modules |
|---|---|---|---|
| **importer** | yes | Both sanitised candidate revisions replay byte-equal from the committed PDFs, under the extraction build V01 pinned, and derive the recorded document identity. | `test_extraction_environment.py`, `test_msca_dn_import.py`, `test_msca_dn_workspace.py`, `test_blind_document_subsections.py` |
| **profile** | yes | An instrument profile resolves to its own rubrics, scorecard and criterion routing, and a criterion cannot be scored under a profile that does not declare it. | `test_profile.py`, `test_msca_dn_profile.py`, `test_ria_profile.py`, `test_rubrics.py`, `test_routing.py` |
| **preflight** | yes | Evidence selection is pinned before an assessor runs: the pack set hashes, the manifest pin binds, and a pack whose anchors do not resolve fails closed. | `test_evidence_preflight.py`, `test_evidence_pack.py` |
| **freeze** | yes | The baseline freeze binds what it froze and refuses what it must, and the frozen 74.60 report still passes the gate it was frozen under. | `test_blind_baseline.py`, `test_blind_assessment.py` |
| **regression** | no | The E4 section golden-set and the E5f rubric lane compare and report as their fixtures specify. Merge-advisory and human-decided by harness/HARNESS.md, so the historical run does not depend on it. | `test_regression.py`, `test_regression_golden.py` |
| **comparison** | yes | The ESR comparison replays from the recorded inputs, and a disposition is the operator's decision rather than a measurement the tool makes for them. | `test_esr_comparison.py`, `test_comparison_diff.py`, `test_operator_review.py`, `test_semantic_adjudications.py`, `test_msca_dn_approved_dispositions.py`, `test_msca_dn_successor_dispositions.py` |
| **provenance** | yes | Every recorded identity, hash binding and declaration describes the committed bytes, and the integrity audit reports what it parsed rather than what it assumed. | `test_provenance.py`, `test_integrity_audit.py`, `test_msca_dn_declaration_drafts.py`, `test_msca_dn_fidelity_declarations.py` |
| **isolation** | yes | The blind lane stays blind: no feedback reaches the assessor, the judge refuses to run inside the repository, and a production run writes no diagnostic copy. | `test_blind_leakage.py`, `test_subscription_judge.py`, `test_boundary.py`, `test_sandbox_hardening.py`, `test_production_mode.py` |
| **scoring** | no | A criterion score is derived from the draws by the declared arithmetic, and a malformed assessor response is refused and checkpointed rather than scored. | `test_criterion_scoring.py`, `test_verdict.py`, `test_report.py`, `test_rubric_report.py`, `test_rubric_run.py` |
| **ledger** | no | Claims are extracted, statused and measured from the committed sections, and a status the sources do not support is Unresolved rather than Confirmed. | `test_claim_ledger.py`, `test_measure_ledger_granularity.py`, `test_faithfulness.py`, `test_status_faithfulness.py`, `test_status_calibration.py`, `test_materiality.py`, `test_calibration.py`, `test_gold_set.py`, `test_expectations.py`, `test_expectation_coverage.py`, `test_expectation_grounding.py` |
| **judge** | no | The judge transport, its response cache and its run log behave offline and deterministically, so a recorded run can be read back. | `test_judge.py`, `test_response_cache.py`, `test_jsonl_log.py`, `test_commands.py` |
| **graph** | no | The development-graph substrate the workspace and candidate records sit on compiles, projects and replays without drift. | `test_dev_graph_documents.py`, `test_dev_graph_gate_invariants.py`, `test_dev_graph_impact.py`, `test_dev_graph_intake.py`, `test_dev_graph_packages.py`, `test_dev_graph_revisions.py`, `test_dev_graph_scenarios.py`, `test_dev_graph_shadow.py`, `test_dev_graph_snapshot.py`, `test_dev_graph_t03_end_to_end.py` |
| **exclusions** | no | Every check the harness cannot run is listed with its reason, and neither the disposition table nor this lane can grow an exclusion the other does not know. | `test_dataset_dispositions.py`, `test_acceptance_lane.py` |

### What the lane adds to the audit's command

The audit ran `tests/harness`, `tests/runner/test_dev_graph*.py` and `tests/test_msca_dn*.py`. The lane
runs all of that and three modules more:

| Module | Area | Why |
|---|---|---|
| `tests/test_extraction_environment.py` | importer | V01's own pin, which the lane runs under |
| `tests/test_sandbox_hardening.py` | isolation | an isolation check the historical run depends on |
| `tests/test_production_mode.py` | isolation | the same |

## The exclusions

Fourteen rows, seventeen checks: one row stands for four. Every skip a complete run reports is one of
these. A skip that is not fails the lane as an **undeclared skip**; a row the run never reports fails
it as a **stale exclusion**. `harness/DATASET_DISPOSITIONS.md` carries the same list for a reader of
harness status, and the command compares the two before running anything, so a row in one and not the
other fails the lane.

Every row names replacement evidence, and every row sits in an area the run does not depend on. Each
reads a substrate that is absent from this checkout: the E4 goldens, the gold-set template, the E5f
freeze, or a Tier 3 confirmation checklist the project-agnostic default does not create.

| Check | Substrate | Reason | Replacement evidence | Lifted by |
|---|---|---|---|---|
| `test_regression_golden.py::TestGoldenSetStanding::test_golden_baselines_are_committed` | E4 goldens | no golden set is committed | test_regression.py::TestFreezeFingerprint and TestRoundtrip cover freezing and reloading a baseline on fixtures | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_regression_golden.py::TestGoldenSetStanding::test_sections_match_golden_set` | E4 goldens | nothing to diff the current sections against | test_regression.py::TestRegressionReport covers the comparison on fixtures | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_regression_golden.py::TestGoldenSetStanding::test_drifted_sections_are_surfaced_even_when_not_breaking` | E4 goldens | nothing to diff the current sections against | test_regression.py::TestRegressionReport covers the report contract on fixtures | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_regression_golden.py::TestRubricLaneStanding::test_frozen_rubric_baseline_is_self_consistent` | E5f rubric baseline | E5f has frozen no baseline | test_rubric_run.py::TestFreezeRubricBaseline and TestCompareRubricBaseline cover the same contract on fixtures | the first E5f rubric freeze |
| `test_measure_ledger_granularity.py::test_report_shape_and_offline` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_measure_ledger_granularity.py::test_prose_byte_identical_all_sub_sections` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_measure_ledger_granularity.py::test_cardinality_gap` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_measure_ledger_granularity.py::test_status_axis_graph_honest_vs_drafter_confirmed_heavy` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_measure_ledger_granularity.py::test_e4_golden_diff_detects_the_gap` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_expectations.py::TestCriterionSectionMap::test_golden_paths_resolve` | E4 goldens | no golden set is committed | fixture coverage in the same module | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| `test_gold_set.py::TestSeededExcellenceTemplate` (4 checks) | gold-set template | the seeded template is not in the tree; `fd38b0a` removed it as instance-derived data | fixture coverage in the same module | ticket X03, which a human labels |
| `test_rubric_report.py::TestStandingLane::test_real_spine_register_loads_and_is_fully_confirmed` | Tier 3 confirmation checklist | no Tier 3 instantiation, so no spine register exists to load | test_rubric_report.py::TestSpineRegistry covers the loader contract on fixtures | a project instantiation, which the project-agnostic default does not ask for |
| `test_status_faithfulness.py::TestResolveClaimSourceText::test_real_checklist_blob_not_truncated_at_default_cap` | Tier 3 confirmation checklist | the same absence: there is no real blob to resolve | TestResolveClaimSourceText's fixture cases cover the truncation rule | a project instantiation, which the project-agnostic default does not ask for |
| `test_rubric_report.py::TestStandingLane::test_frozen_report_renders_if_present` | E5f rubric report | E5f has frozen no report | test_rubric_report.py::TestRender covers rendering a report on fixtures | the first E5f rubric freeze |

### The two Tier 3 rows carry a ticket's open criterion

`test_rubric_report.py::TestStandingLane::test_real_spine_register_loads_and_is_fully_confirmed` is
V02c's first acceptance criterion, in its real-file half. That criterion is recorded in the ledger as
**excluded, not passed**. The lane's job is to keep it visible: lose the row from either document, and
`tests/harness/test_acceptance_lane.py` fails.

## The result, against the audit's baseline

The lane prints its result beside the audit's measurement at `ca0a443`, so every item of that
measurement is resolved or explicitly scoped. The recorded run is in
`plans/reports/v03_acceptance_lane_completion_2026-10-09.md`.

| | Audit at `ca0a443` | The lane, 2026-10-09 |
|---|---:|---:|
| Passed | 1,864 | PASSED_1 |
| Failed | 44 | 0 |
| Errors | 48 | 0 |
| Skipped | 8 | 17, every one declared above |
| Collected | 1,964 | COLLECTED_1 |

The two collected counts are not comparable case for case. V01 and V02a–V02d added cases, and the lane
adds three modules the focused command did not run. What is comparable is the failing set: the audit's
92 failures and errors are gone, and no new one replaced them.

## What a green lane does not say

It says the code behaves as its fixtures specify. Read nothing else into it.

- A green lane is **not evidence of calibration**. No expert-labelled validation data exists for this
  harness. Nothing here measures any judge or assessor against human ground truth.
- A green lane is **not evidence of forecast accuracy**. No result here predicts what an evaluator
  would score. Five draws from one assessor are five draws from one assessor.
- A green lane is **not evidence of grounded evaluation**. The sanitised candidate's supporting sources
  are removed, the blind lane runs `--no-claims`, and grounding is unassessable by design.

Seventeen skips are seventeen absences. They are not seventeen passes, and the lane prints them as
exclusions every time it runs. `harness/DATASET_DISPOSITIONS.md` holds the same list with the work that
would lift each one.
