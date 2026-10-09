# V03 completion report — the named PE-09 acceptance lane

Date: 2026-10-09.
Branch: `msca-dn-pre-eval`, from `7195681`.
Ticket: V03 of `plans/msca_dn_historical_validation_tickets.md`.
Closes: finding F08 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-acceptance-lane_2026-10-09.json`.
Input: `plans/reports/v02_focused_suite_completion_2026-10-09.md`.

Four of four acceptance criteria are met. V03's gate, G1 closure, additionally depends on the amended
dependency gate recorded in the ledger and in section 1 below. No other gate closes here, no assessor
ran, and the official 2025 baseline is not validated.

## Environment

Python 3.10.6 and PyMuPDF 1.28.2 over MuPDF 1.28.2 — the pin V01 established
(`docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`).
The lane reports the running environment before it runs anything, and refuses to certify a result on a
build that was not measured to reproduce the committed import artifacts.

## 1. The dependency gate V03 inherited

V03 is blocked by V01, V02a, V02b, V02c and V02d. V01, V02b and V02d closed in full. V02a and V02c each
left one box open, and a gate cannot rest on an unexplained open box. Neither box is checked, and
neither is described as a pass.

### V02a criterion 2 — transferred to V05

The criterion reads: *the two integrity-audit integration failures pass against the reproduced document
identity and the V05 provenance-derived wording.*

Its first half holds. Both checks pass against the reproduced identity, and
`tests/harness/test_integrity_audit.py` is green in the lane's provenance area. Its second half cannot
hold yet: V05 is open, no wording has been derived from candidate provenance, and
`harness/integrity_audit.py` still sets its grounding reason from a module constant.

**Downstream owner: V05.** The ledger already recorded V02a as blocked by V05, so the owner was implied
by the dependency shape and is now written down. V05 carries the criterion as its own sixth acceptance
criterion, citing this report and the V02 report. Transferred, not dropped: if V05 closes without it,
the box fails in V05's own list.

### V02c criterion 1 — a scoped exclusion, not a pass

The criterion reads: *the rubric-report fixture and the `confirmation_checklist` contract agree, and the
change is made in one direction with a stated reason.*

The second half holds: the change went towards the engine, and the V02 report states why. The first half
cannot hold. The two sides cannot agree while the engine stands at its `CLAUDE.md` §2 project-agnostic
default, because `docs/tier3_project_instantiation/call_binding/confirmation_checklist.json` does not
exist for the real-file half to agree with.

So the real-file half is recorded as **excluded**, with its node id, its reason, its replacement
evidence and the work that would lift it, in three places:

| Where | What it holds |
|---|---|
| `harness/DATASET_DISPOSITIONS.md` | the row a reader of harness status meets |
| `harness/acceptance_lanes/msca_dn_historical.json` | the row the lane reconciles each run against |
| `harness/ACCEPTANCE_LANE.md` | the same row, in the lane's own documentation |

`tests/harness/test_acceptance_lane.py::TestTheDependencyGate` fails if the exclusion disappears from
either document, and `tests/harness/test_acceptance_lane.py::TestExclusions` fails if the lane and the
disposition table disagree. The exclusion is not a passing check anywhere, and nothing counts it toward
suite health.

### The amendment

The ledger's V03 entry now reads **Blocked by: V01, V02a (criterion 2 → V05), V02b, V02c (criterion 1
excluded), V02d**, with a `Dependency gate, amended 2026-10-09` subsection stating both dispositions.
The amendment is to the gate, not to the criteria: V02a's and V02c's acceptance lists are unchanged
apart from an annotation on each open box naming its disposition.

## 2. The lane

One command, documented in `harness/ACCEPTANCE_LANE.md`:

```
py -3.10 -m harness.commands.acceptance_lane
```

It runs 62 test modules in 13 named areas and then reads the run back against its own declaration.

**The declaration is data.** `harness/acceptance_lanes/msca_dn_historical.json` holds the areas, the
exclusions, the audit baseline and the no-calibration statement. `harness/acceptance_lane.py` reads it
and carries no instrument name, which is the separation `harness/profile.py` already keeps from its
profiles. That was not the first design: the first draft put the declaration in Python and failed the
agnosticism lint over `harness/**/*.py`. Section 5 records that.

**Seven areas the run depends on, and six that carry the rest.** Each area declares whether the
historical run depends on its invariant. That flag is what turns criterion 2's second half into a
measurement: every declared exclusion must sit in an area marked **no**, and the command refuses to run
when one does not.

The E4 golden-set and E5f rubric lanes have their own **regression** area for that reason. Four of
their checks are excluded, and `harness/HARNESS.md` makes the lane merge-advisory and human-decided, so
the historical run does not depend on it. Putting them under **freeze** — where the first draft had
them — would have placed four exclusions inside a depended-on invariant.

| Area | Run depends on it | Invariant | Modules |
|---|---|---|---:|
| importer | yes | Both sanitised candidate revisions replay byte-equal from the committed PDFs, under the extraction build V01 pinned, and derive the recorded document identity. | 4 |
| profile | yes | An instrument profile resolves to its own rubrics, scorecard and criterion routing, and a criterion cannot be scored under a profile that does not declare it. | 5 |
| preflight | yes | Evidence selection is pinned before an assessor runs: the pack set hashes, the manifest pin binds, and a pack whose anchors do not resolve fails closed. | 2 |
| freeze | yes | The baseline freeze binds what it froze and refuses what it must, and the frozen 74.60 report still passes the gate it was frozen under. | 2 |
| regression | no | The E4 section golden-set and the E5f rubric lane compare and report as their fixtures specify. Merge-advisory and human-decided by harness/HARNESS.md, so the historical run does not depend on it. | 2 |
| comparison | yes | The ESR comparison replays from the recorded inputs, and a disposition is the operator's decision rather than a measurement the tool makes for them. | 6 |
| provenance | yes | Every recorded identity, hash binding and declaration describes the committed bytes, and the integrity audit reports what it parsed rather than what it assumed. | 4 |
| isolation | yes | The blind lane stays blind: no feedback reaches the assessor, the judge refuses to run inside the repository, and a production run writes no diagnostic copy. | 5 |
| scoring | no | A criterion score is derived from the draws by the declared arithmetic, and a malformed assessor response is refused and checkpointed rather than scored. | 5 |
| ledger | no | Claims are extracted, statused and measured from the committed sections, and a status the sources do not support is Unresolved rather than Confirmed. | 11 |
| judge | no | The judge transport, its response cache and its run log behave offline and deterministically, so a recorded run can be read back. | 4 |
| graph | no | The development-graph substrate the workspace and candidate records sit on compiles, projects and replays without drift. | 10 |
| exclusions | no | Every check the harness cannot run is listed with its reason, and neither the disposition table nor this lane can grow an exclusion the other does not know. | 2 |

**The lane is a superset of the audit's command.** It runs `tests/harness`,
`tests/runner/test_dev_graph*.py` and `tests/test_msca_dn*.py`. Three modules more join them:
`tests/test_extraction_environment.py`, which is V01's own pin, and
`tests/test_sandbox_hardening.py` and `tests/test_production_mode.py`, two isolation checks the focused
globs missed. `tests/test_persistence_policy.py` was considered and left out. One of its cases fails on
a missing optional `botocore` extra, which is an environment dependency and not an acceptance
invariant.

**Five guards run before any test.** A declared module that is not in the tree fails the lane. So does
a module inside the audit's command and outside every area. So does a declared exclusion the
disposition document does not name, and an exclusion sitting in an area the run depends on. A
declaration with a missing field, or an unrecognised schema, is refused outright.

**The run is reconciled in both directions.** A skip no exclusion declares fails the lane as an
*undeclared skip*. A declared exclusion the run never reports fails it as a *stale exclusion*. Any
failure or setup error is an *unexplained failure*, because an excluded check skips and therefore never
explains a failure.

## 3. The result

V03's verification line asks for two runs *from a clean checkout*. Both runs below ran in a fresh
worktree checked out at `4f2c275`, the commit that carries this work, with only the gitignored `.env`
copied in. A fresh worktree is the stronger reading: it also proves that no untracked fixture in the
development tree is load-bearing for the lane.

Both runs, consecutive, in that worktree under the V01 pin:

| | Run 1 | Run 2 |
|---|---:|---:|
| Passed | 2,121 | 2,121 |
| Failed | 0 | 0 |
| Errors | 0 | 0 |
| Skipped — declared exclusions | 17 | 17 |
| Collected | 2,138 | 2,138 |
| Unexplained failures | 0 | 0 |
| Undeclared skips | 0 | 0 |
| Stale exclusions | 0 | 0 |
| Duration | 4 min 30 s | 5 min 07 s |

Verbatim verdict line from each run:

```
run 1: GREEN: 2,121 passed, 0 failed, 0 errors, 17 declared exclusions.
run 2: GREEN: 2,121 passed, 0 failed, 0 errors, 17 declared exclusions.
```

### Against the audit's baseline

| | Audit at `ca0a443` | This lane |
|---|---:|---:|
| Passed | 1,864 | 2,121 |
| Failed | 44 | 0 |
| Errors | 48 | 0 |
| Skipped | 8 | 17, every one declared |
| Collected | 1,964 | 2,138 |

Every item of the audit's measurement is resolved or explicitly scoped:

- **The 44 failures and 48 errors are gone.** V01's extraction pin closed the largest family by one
  cause: the importer, workspace, fidelity-register and adoption fixtures. V02a to V02d closed the
  rest, and the V02 report reclassifies each of the audit's eight failure families individually.
- **The 8 skips are among the 17 declared exclusions.** The dataset absences they reported are
  unchanged. Nine further absences were found during V02d and V03 and declared rather than left
  failing or left invisible.
- **The two collected counts are not comparable case for case.** V01 and V02a to V02d added cases, this
  work added its own test module, and the lane runs three modules the focused command did not. The
  comparable measure is the failing set, which is empty.

One correction to the V02 report's arithmetic. It recorded the post-V02 focused command as 1,965 passed
over 1,982 collected. Measured again at `7195681`, before this work added any module, the same command
collects 1,983 and passes 1,966 — one case more. Collection in that command is deterministic: no module in it uses
`pytest_generate_tests`, and every `parametrize` in it ranges over a literal. The V02 figure was one
short, and nothing in the repository changed to produce the difference.

## 4. All 17 skips, with their reasons

Every skip the lane reports is one of the fourteen declared exclusion rows. One row stands for four
checks, which is why fourteen rows account for seventeen skips. Each row's substrate is absent from this
checkout; none covers a check the historical run depends on.

| # | Check | Substrate | Reason | Replacement evidence | Lifted by |
|---|---|---|---|---|---|
| 1 | `test_regression_golden.py::TestGoldenSetStanding::test_golden_baselines_are_committed` | E4 goldens | no golden set is committed | test_regression.py::TestFreezeFingerprint and TestRoundtrip cover freezing and reloading a baseline on fixtures | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 2 | `test_regression_golden.py::TestGoldenSetStanding::test_sections_match_golden_set` | E4 goldens | nothing to diff the current sections against | test_regression.py::TestRegressionReport covers the comparison on fixtures | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 3 | `test_regression_golden.py::TestGoldenSetStanding::test_drifted_sections_are_surfaced_even_when_not_breaking` | E4 goldens | nothing to diff the current sections against | test_regression.py::TestRegressionReport covers the report contract on fixtures | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 4 | `test_regression_golden.py::TestRubricLaneStanding::test_frozen_rubric_baseline_is_self_consistent` | E5f rubric baseline | E5f has frozen no baseline | test_rubric_run.py::TestFreezeRubricBaseline and TestCompareRubricBaseline cover the same contract on fixtures | the first E5f rubric freeze |
| 5 | `test_measure_ledger_granularity.py::test_report_shape_and_offline` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 6 | `test_measure_ledger_granularity.py::test_prose_byte_identical_all_sub_sections` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 7 | `test_measure_ledger_granularity.py::test_cardinality_gap` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 8 | `test_measure_ledger_granularity.py::test_status_axis_graph_honest_vs_drafter_confirmed_heavy` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 9 | `test_measure_ledger_granularity.py::test_e4_golden_diff_detects_the_gap` | E4 goldens | the measurement's drafter-era side reads the goldens, which are absent | Git history only: `32b5606` records every measured number | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 10 | `test_expectations.py::TestCriterionSectionMap::test_golden_paths_resolve` | E4 goldens | no golden set is committed | fixture coverage in the same module | an operator refreeze, then re-pointing the granularity suite (DATASET_DISPOSITIONS.md) |
| 11–14 | `test_gold_set.py::TestSeededExcellenceTemplate` | gold-set template | the seeded template is not in the tree; `fd38b0a` removed it as instance-derived data | fixture coverage in the same module | ticket X03, which a human labels |
| 15 | `test_rubric_report.py::TestStandingLane::test_real_spine_register_loads_and_is_fully_confirmed` | Tier 3 confirmation checklist | no Tier 3 instantiation, so no spine register exists to load | test_rubric_report.py::TestSpineRegistry covers the loader contract on fixtures | a project instantiation, which the project-agnostic default does not ask for |
| 16 | `test_status_faithfulness.py::TestResolveClaimSourceText::test_real_checklist_blob_not_truncated_at_default_cap` | Tier 3 confirmation checklist | the same absence: there is no real blob to resolve | TestResolveClaimSourceText's fixture cases cover the truncation rule | a project instantiation, which the project-agnostic default does not ask for |
| 17 | `test_rubric_report.py::TestStandingLane::test_frozen_report_renders_if_present` | E5f rubric report | E5f has frozen no report | test_rubric_report.py::TestRender covers rendering a report on fixtures | the first E5f rubric freeze |

Row 12 is V02c's open criterion in its real-file half. V02d's dispositions are the E4 and gold-set
rows. The two Tier 3 rows and the E5f report row were added when the review of V02d found them
excluded on disk and missing from its table.

**None of these is a pass.** Seventeen skips are seventeen absences. No dataset was created, no
calibration ran, and the lane prints all three no-calibration sentences with every result.

## 5. What the lane found on its first run

The lane's first complete run was not green, and both findings are the lane doing its job. A count-only
suite would have reported neither: one check was already skipping, and the other was a document row
nobody had re-read.

**A stale exclusion row.** `harness/DATASET_DISPOSITIONS.md` named
`test_expectations.py::TestRealSubstrate::test_golden_paths_resolve`. The class had been renamed to
`TestCriterionSectionMap`, so the row matched nothing. The lane reported the exclusion as *stale* and the
same skip as *undeclared*. That pair of symptoms is what a wrong node id produces. The row was corrected
in both documents and in the declaration. A new check,
`TestExclusions::test_every_exclusion_names_a_class_that_is_in_that_module`, closes the gap —
`tests/harness/test_dataset_dispositions.py` verified only that the module existed.

**An instrument literal in harness Python.** `tests/harness/test_profile.py::TestNoInstrumentLiterals`
lints every `harness/**/*.py` for an instrument name outside the profile loader, which is how `CLAUDE.md`
§2 project-agnosticism is held at the code layer. The lane's first draft named the instrument in Python
and failed it. The fix was to move the declaration into JSON and make the reader generic, not to exempt
the module: a second instance now declares a second lane and the reader does not change. Weakening the
lint was considered and rejected.

## 6. The whole repository

A whole-run count is not a stable number in this repository. The same invocation returns different
counts on consecutive runs, because some modules depend on execution order and on runtime state
`CLAUDE.md` §9.2 keeps out of git. Failing **identifier sets** are compared instead, as the R02, R04
and V02 records established.

The baseline is the whole suite on a fresh worktree at `3b4cde8`, the commit before V02a to V02d. Two
comparison runs were made, because the choice of "after" side changes the answer:

| | Failing ids | New failures | Baseline failures resolved |
|---|---:|---:|---:|
| Baseline, fresh worktree at `3b4cde8` | 220 | — | — |
| **After, development tree** (V02's method) | 194 | **0** | **26** |
| **After, fresh worktree at `4f2c275`** | 201 | **0** | **19** |

**V02's figure reproduces exactly.** Comparing the worktree baseline against the development tree gives
0 new failures and 26 resolved, the figure the V02 report recorded. Nothing V03 added changed it.

**The stricter comparison gives 19.** With a fresh worktree on both sides, 7 of those 26 do not count
as resolved, because they fail on both sides rather than on neither. All 7 are demo checks that read
untracked run records under `.claude/runs`:

| Resolved only in the development tree |
|---|
| `test_demo_candidate_blind_baseline.py::TestThePhase8BlockIsLifted::test_every_phase_8_node_released` |
| `test_demo_change_scenarios.py::TestRecordsOnDisk::test_the_index_is_current` |
| `test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_rewriting_the_records_changes_no_byte` |
| `test_demo_dev_graph_run_records.py::TestDocument::test_the_written_artifact_is_current` |
| `test_demo_dev_graph_snapshot.py::TestTheSnapshot::test_the_whole_run_replays_byte_equal` |
| `test_demo_phase7_budget_gate.py::TestTheRequestConforms::test_it_recomposes_byte_equal` |
| `test_demo_report.py::TestTheScenarioFigures::test_seven_scenarios_eleven_arms_sixteen_refusals` |

The V02 report called these out and counted eight of them. Measured here there are seven, and the
arithmetic closes: 19 + 7 = 26. The V02 figure is correct under its own method; the one-case difference
is in how many of its 26 it attributed to the worktree rather than to the tickets.

**Both comparisons agree on the measure that matters: zero new failures.** The 197 to 201 that remain
are concentrated in `tests/runner/test_skill_runtime*.py`, the phase artifact-production modules and
`tests/test_transport_*.py`. None is in a module this work touched, and none was introduced here.

### One defect the comparison found, and its fix

The first clean-worktree comparison reported three new failures:

```
tests/test_demo_change_scenarios.py::TestComparedRuns::test_every_compared_run_has_a_manifest
tests/test_demo_change_scenarios.py::TestComparedRuns::test_no_compared_run_manifest_records_a_reuse_decision
tests/test_preserve_run_manifests.py::TestTheLiveRecords::test_check_mode_reports_the_preserved_records_unchanged
```

They were not V03 regressions, and they were not noise either. Measured:

| Where | Result |
|---|---|
| Fresh worktree at `3b4cde8`, no prior lane run | 3 skipped |
| Fresh worktree at `7195681`, no prior lane run | 3 skipped |
| Fresh worktree at `4f2c275`, no prior lane run | 3 skipped |
| Fresh worktree at `4f2c275`, after two lane runs | **3 failed** |
| Development tree | 3 passed |

The cause is a leaked run record. `tests/test_production_mode.py::TestStartupBackendLogging::
test_startup_returns_3_on_production_config_error` calls `runner.__main__.main` with a run id, and the
startup path creates `.claude/runs/test-00000000-0000-0000-0000-000000000000/` before the transport
config fails. The directory outlived the test. The three checks above skip when `.claude/runs` is
absent — the §9.2 state of a fresh checkout — and fail when a directory is there without the manifest
they read. So running the lane and then the whole suite in one tree produced three failures the lane
itself had caused.

The lane put `tests/test_production_mode.py` in its isolation area, which is why this surfaced now.
The fix is at the source. That test class now removes the run directory it created, and only when it
created it. A directory that was already there is a developer's run state, not the test's debris.
`tests/test_production_mode.py` is 34 passed with the fix, and the 65 checks in the two affected
modules pass in the development tree.

One side effect to record. An earlier form of the fix removed a pre-existing
`.claude/runs/test-00000000-0000-0000-0000-000000000000/` from the development tree, left by a previous
run of that same test. It is gitignored §9.2 runtime state, not constitutional source truth, and the
65 dependent checks pass without it. The fix is now conditional, so it cannot recur.

## 7. Preserved artifact bindings

| Artifact | State |
|---|---|
| The frozen 74.60 baseline and its freeze record | Unchanged. The lane's freeze area runs against it and passes. Its recorded total, criterion medians and spreads, and every binding are as committed. |
| The committed sanitised PDFs, document records, page sources, import manifests | Unchanged. No import ran, and no identifier was regenerated. |
| Both fidelity registers | Unchanged, bytes and hashes. |
| The 2026-10-08 operator approval records | Unchanged, exactly as written. |
| The approved dispositions, comparison records, revision plan, committed integrity audits | Unchanged. |

**The approval record's bindings measure 24 of 26, as V02a reported.** Re-verified on this checkout by
hashing every path the record pins: 24 match, 2 differ, 0 missing. The two that differ are the two
declaration-draft hashes V02a superseded, and nothing else in the record moved.

The successor record for those two hashes is
`docs/tier4_orchestration_state/decision_log/msca-dn-declaration-draft-rerender_2026-10-09.json`. It
states the before and after values, why the drafts went stale, and the scope of what the approval record
still binds. Both recorded `after` values were re-verified against the files on disk today and match.
V03 changes nothing in either record. **The operator's acknowledgement of the re-render is still open**,
as the V02 report requested; this report does not close it.

## 8. Changed files

| File | Change |
|---|---|
| `harness/acceptance_lane.py` | new — the lane reader and reconciler, instrument-free |
| `harness/acceptance_lanes/msca_dn_historical.json` | new — the declaration: 13 areas, 14 exclusion rows, the audit baseline |
| `harness/commands/acceptance_lane.py` | new — the command, with `--list`, `--lane`, `--area`, `-k`, `--junit`, `--from-junit`, `--allow-unreproducing-build` |
| `harness/ACCEPTANCE_LANE.md` | new — the lane's documentation, including what a green result is not evidence of |
| `tests/harness/test_acceptance_lane.py` | new — 53 checks over the declaration, the loader, the reader, the reconciliation, the documentation and the ledger amendment |
| `harness/DATASET_DISPOSITIONS.md` | the stale class name corrected; a section pointing at the lane |
| `harness/HARNESS.md` | a section naming the lane and its command |
| `tests/harness/test_commands.py` | the new command added to the import-side-effect-free list |
| `tests/test_production_mode.py` | the leaked run record removed by the test class that creates it; section 6 |
| `plans/msca_dn_historical_validation_tickets.md` | the V03 dependency-gate amendment; V02a and V02c annotations; V05's inherited criterion; V03's criteria checked |
| `plans/msca_dn_v04_v11_preparation_2026-10-09.md` | new — preparation for the five tickets V03 unblocks |
| `docs/tier4_orchestration_state/decision_log/msca-dn-acceptance-lane_2026-10-09.json` | new — the decision record |
| `plans/reports/v03_acceptance_lane_completion_2026-10-09.md` | new — this report |

Two commits: `4f2c275` carries the work, and the follow-up records the measured result. The report was
committed with its result table unfilled rather than with a figure whose source did not yet exist.

## 9. Checks actually run

| Check | Result |
|---|---|
| `py -3.10 -m harness.commands.acceptance_lane`, twice, in a clean worktree at `4f2c275` | section 3 |
| `py -3.10 -m pytest tests/harness/test_acceptance_lane.py` | 53 passed |
| `py -3.10 -m pytest` over the whole repository, three runs | 0 new failures both ways; section 6 |
| `py -3.10 -m pytest tests/test_production_mode.py` | 34 passed, and no run record left behind |
| `py -3.10 -m pytest tests/test_demo_change_scenarios.py tests/test_preserve_run_manifests.py` | 65 passed |
| `py -3.10 -m mypy harness/acceptance_lane.py harness/commands/acceptance_lane.py` | no error in either module; the repository carries pre-existing errors elsewhere |
| `py -3.10 -m tools.draft_fidelity_declarations --check` | exit 0, `up to date` |
| Approval-record hash verification, 26 pins | 24 match, 2 superseded, 0 missing |
| `py -3.10 -m harness.commands.acceptance_lane --lane nope` | refused, naming the available declaration |
| `py -3.10 -m harness.commands.acceptance_lane --from-junit <report>` | reconciles a recorded run without running tests |

## 10. Remaining uncertainties

- **V02a criterion 2 is open**, owned by V05. The integrity audit's grounding reason is still a module
  constant, and that wording would misstate the official original.
- **V02c criterion 1 is excluded**, not closed. A project instantiation lifts it; the project-agnostic
  default does not ask for one.
- **The operator's acknowledgement of the declaration-draft re-render is open.**
- **Seventeen checks cannot run.** No expert-labelled validation data exists, no E4 goldens are
  committed, E5f has frozen nothing, and there is no Tier 3 checklist.
- **A green lane is not coverage of value.** The audit's observation stands: the passing baseline tests
  did not catch the defects the freeze probes reproduced. V04 is the ticket that closes that, and the
  lane will run the hardened freeze checks once V04 lands.
- **The whole-repository comparison depends on which tree is the "after" side.** 26 resolved against
  the development tree, 19 against a fresh worktree; zero new failures either way. Section 6 gives both
  and reconciles them. A future comparison should say which side it used.
- **197 to 201 whole-repository failures remain**, pre-existing and outside every module this work
  touched. They are not V03's to close, and no ticket in this ledger claims them.

## 11. What this report does not claim

A green lane says the code behaves as its fixtures specify. It is not evidence of calibration, not
evidence of forecast accuracy, and not evidence of grounded evaluation.

No assessor ran. No quota was spent. No component was tuned toward 85.80 or any other score. The private
assessment was not executed, and the official 2025 baseline is **not** validated. V05 to V14 stand open,
the 2025 authority documents G3 depends on are not in the repository, and G6 and G7 are the operator's
decisions.

F08 closes with this report. G1 closure is V03's gate and rests on the amended dependency gate in
section 1, not on any box this report checks for another ticket.
