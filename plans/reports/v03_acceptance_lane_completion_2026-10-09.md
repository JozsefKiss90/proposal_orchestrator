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

It runs 62 test modules in 12 named areas and then reads the run back against its own declaration.

**The declaration is data.** `harness/acceptance_lanes/msca_dn_historical.json` holds the areas, the
exclusions, the audit baseline and the no-calibration statement. `harness/acceptance_lane.py` reads it
and carries no instrument name, which is the separation `harness/profile.py` already keeps from its
profiles. That was not the first design: the first draft put the declaration in Python and failed the
agnosticism lint over `harness/**/*.py`. Section 5 records that.

**The seven areas V03 names, and five more.** The first seven are the invariants the historical run
depends on. The remaining five carry the rest of the audit's focused command, kept rather than dropped.

| Area | Invariant | Modules |
|---|---|---:|
| importer | Both sanitised revisions replay byte-equal from the committed PDFs and derive the recorded identity | 4 |
| profile | A profile resolves to its own rubrics, scorecard and routing | 5 |
| preflight | Evidence selection is pinned, hashed and fails closed on unresolved anchors | 2 |
| freeze | The freeze binds what it froze, and the frozen 74.60 report still passes | 4 |
| comparison | The comparison replays, and a disposition stays the operator's decision | 6 |
| provenance | Every identity, hash binding and declaration describes the committed bytes | 4 |
| isolation | The blind lane stays blind and the judge refuses to run inside the repository | 5 |
| scoring | A score follows the declared arithmetic; a malformed response is refused | 5 |
| ledger | Claims are extracted and statused from the committed sections | 11 |
| judge | The transport, cache and run log behave offline and deterministically | 4 |
| graph | The development-graph substrate compiles, projects and replays | 10 |
| exclusions | Every unrunnable check is listed, and the two lists cannot drift | 2 |

**The lane is a superset of the audit's command.** It runs `tests/harness`,
`tests/runner/test_dev_graph*.py` and `tests/test_msca_dn*.py`. Three modules more join them:
`tests/test_extraction_environment.py`, which is V01's own pin, and
`tests/test_sandbox_hardening.py` and `tests/test_production_mode.py`, two isolation checks the focused
globs missed. `tests/test_persistence_policy.py` was considered and left out. One of its cases fails on
a missing optional `botocore` extra, which is an environment dependency and not an acceptance
invariant.

**Three guards run before any test.** A declared module that is not in the tree fails the lane. A module
inside the audit's command and outside every area fails it. A declaration with a missing field, or an
unrecognised schema, is refused.

**The run is reconciled in both directions.** A skip no exclusion declares fails the lane as an
*undeclared skip*. A declared exclusion the run never reports fails it as a *stale exclusion*. Any
failure or setup error is an *unexplained failure*, because an excluded check skips and therefore never
explains a failure.

## 3. The result

Both runs, consecutive, on this checkout under the V01 pin:

| | Run 1 | Run 2 |
|---|---:|---:|
| Passed | PASSED_1 | PASSED_2 |
| Failed | 0 | 0 |
| Errors | 0 | 0 |
| Skipped — declared exclusions | 17 | 17 |
| Collected | COLLECTED_1 | COLLECTED_2 |
| Unexplained failures | 0 | 0 |
| Undeclared skips | 0 | 0 |
| Stale exclusions | 0 | 0 |
| Duration | DURATION_1 | DURATION_2 |

Verbatim verdict line from each run:

```
VERDICT_BLOCK
```

### Against the audit's baseline

| | Audit at `ca0a443` | This lane |
|---|---:|---:|
| Passed | 1,864 | PASSED_1 |
| Failed | 44 | 0 |
| Errors | 48 | 0 |
| Skipped | 8 | 17, every one declared |
| Collected | 1,964 | COLLECTED_1 |

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
| 1 | `test_regression_golden.py::TestGoldenSetStanding::test_golden_baselines_are_committed` | E4 goldens | no golden set is committed | none | an operator refreeze, then re-pointing the granularity suite |
| 2 | `test_regression_golden.py::TestGoldenSetStanding::test_sections_match_golden_set` | E4 goldens | nothing to diff the current sections against | `test_regression.py::TestRegressionReport` covers the comparison on fixtures | the same |
| 3 | `test_regression_golden.py::TestGoldenSetStanding::test_drifted_sections_are_surfaced_even_when_not_breaking` | E4 goldens | nothing to diff the current sections against | `test_regression.py::TestRegressionReport` covers the report contract on fixtures | the same |
| 4 | `test_regression_golden.py::TestRubricLaneStanding::test_frozen_rubric_baseline_is_self_consistent` | E5f rubric baseline | E5f has frozen no baseline | none | the first E5f rubric freeze |
| 5 | `test_measure_ledger_granularity.py::test_report_shape_and_offline` | E4 goldens | the measurement's drafter-era side reads the goldens | git history only: `32b5606` | an operator refreeze, then re-pointing the suite |
| 6 | `test_measure_ledger_granularity.py::test_prose_byte_identical_all_sub_sections` | E4 goldens | the same | git history only: `32b5606` | the same |
| 7 | `test_measure_ledger_granularity.py::test_cardinality_gap` | E4 goldens | the same | git history only: `32b5606` | the same |
| 8 | `test_measure_ledger_granularity.py::test_status_axis_graph_honest_vs_drafter_confirmed_heavy` | E4 goldens | the same | git history only: `32b5606` | the same |
| 9 | `test_measure_ledger_granularity.py::test_e4_golden_diff_detects_the_gap` | E4 goldens | the same | git history only: `32b5606` | the same |
| 10 | `test_expectations.py::TestCriterionSectionMap::test_golden_paths_resolve` | E4 goldens | no golden set is committed | fixture coverage in the same module | an operator refreeze |
| 11–14 | `test_gold_set.py::TestSeededExcellenceTemplate` — four checks | gold-set template | the seeded template is not in the tree; `fd38b0a` removed it as instance-derived data | fixture coverage in the same module | ticket X03, which a human labels |
| 15 | `test_rubric_report.py::TestStandingLane::test_real_spine_register_loads_and_is_fully_confirmed` | Tier 3 confirmation checklist | no Tier 3 instantiation, so no spine register exists to load | `test_rubric_report.py::TestSpineRegistry` covers the loader contract on fixtures | a project instantiation |
| 16 | `test_status_faithfulness.py::TestResolveClaimSourceText::test_real_checklist_blob_not_truncated_at_default_cap` | Tier 3 confirmation checklist | the same absence: there is no real blob to resolve | the same class's fixture cases cover the truncation rule | a project instantiation |
| 17 | `test_rubric_report.py::TestStandingLane::test_frozen_report_renders_if_present` | E5f rubric report | E5f has frozen no report | none | the first E5f rubric freeze |

Row 15 is V02c's open criterion in its real-file half. Rows 1 to 14 are V02d's dispositions. Rows 15 to
17 were added to the table when the review of V02d found them excluded on disk and missing from it.

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

A whole-run count is not a stable number in this repository: the same invocation returns different
counts on consecutive runs, because some modules depend on execution order. Failing **identifier sets**
are compared instead, as the R02, R04 and V02 records established.

The baseline is the whole suite on a fresh worktree at `3b4cde8`, the commit before V02a to V02d. The
comparison run is the whole suite on this working tree, with V02 committed and V03 applied:

| | Failing ids |
|---|---:|
| Baseline, worktree at `3b4cde8` | BASE_IDS |
| After V02a–V02d and V03 | NOW_IDS |
| New failures introduced | **NEW_IDS** |
| Baseline failures now resolved | RESOLVED_IDS |

WHOLE_REPO_NOTE

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
| `harness/acceptance_lanes/msca_dn_historical.json` | new — the declaration: 12 areas, 14 exclusion rows, the audit baseline |
| `harness/commands/acceptance_lane.py` | new — the command, with `--list`, `--lane`, `--area`, `-k`, `--junit`, `--from-junit`, `--allow-unreproducing-build` |
| `harness/ACCEPTANCE_LANE.md` | new — the lane's documentation, including what a green result is not evidence of |
| `tests/harness/test_acceptance_lane.py` | new — 50 checks over the declaration, the loader, the reader, the reconciliation, the documentation and the ledger amendment |
| `harness/DATASET_DISPOSITIONS.md` | the stale class name corrected; a section pointing at the lane |
| `harness/HARNESS.md` | a section naming the lane and its command |
| `tests/harness/test_commands.py` | the new command added to the import-side-effect-free list |
| `plans/msca_dn_historical_validation_tickets.md` | the V03 dependency-gate amendment; V02a and V02c annotations; V05's inherited criterion; V03's criteria checked |
| `plans/msca_dn_v04_v11_preparation_2026-10-09.md` | new — preparation for the five tickets V03 unblocks |
| `docs/tier4_orchestration_state/decision_log/msca-dn-acceptance-lane_2026-10-09.json` | new — the decision record |
| `plans/reports/v03_acceptance_lane_completion_2026-10-09.md` | new — this report |

## 9. Checks actually run

| Check | Result |
|---|---|
| `py -3.10 -m harness.commands.acceptance_lane`, twice | GREEN both times; section 3 |
| `py -3.10 -m pytest tests/harness/test_acceptance_lane.py` | 50 passed |
| `py -3.10 -m pytest` over the whole repository | section 6 |
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

## 11. What this report does not claim

A green lane says the code behaves as its fixtures specify. It is not evidence of calibration, not
evidence of forecast accuracy, and not evidence of grounded evaluation.

No assessor ran. No quota was spent. No component was tuned toward 85.80 or any other score. The private
assessment was not executed, and the official 2025 baseline is **not** validated. V05 to V14 stand open,
the 2025 authority documents G3 depends on are not in the repository, and G6 and G7 are the operator's
decisions.

F08 closes with this report. G1 closure is V03's gate and rests on the amended dependency gate in
section 1, not on any box this report checks for another ticket.
