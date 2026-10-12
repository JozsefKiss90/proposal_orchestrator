# V04 completion report — the freeze refuses incomplete and inconsistent reports

Date: 2026-10-12.
Branch: `msca-dn-pre-eval`, from `437ca89`.
Ticket: V04 of `plans/msca_dn_historical_validation_tickets.md`.
Closes: finding F03 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-freeze-completeness_2026-10-12.json`.

Seven of seven acceptance criteria are closed. F03 closes. Gate G4 does not: V06 is still open. No
assessor ran, no quota was spent, and the frozen 74.60 baseline is untouched — this ticket is the one
that proves it still freezes.

Environment: Python 3.10.6, the pin V01 established
(`docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`).

## 1. What was wrong

The audit built four invalid variants from copies of the committed baseline report. The complete
`freeze_baseline` path accepted all four, each with 15 checks passed.

| Probe | At `437ca89` | Now |
|---|---|---|
| Keep 1 of 10 cells | Accepted | Refused: `cell_identity` names the 9 absent cells |
| Keep 1 of 3 criterion scores | Accepted | Refused: `criterion_identity` and `total_recomputed` |
| Remove `assessor_invocation` | Accepted | Refused: `invocation_evidence` names the transport |
| Replace the total 74.6 with 99.9 | Accepted | Refused: `total_recomputed` names both numbers |

One small correction to the ticket's own problem statement: `BASELINE_CHECKS` named fifteen conditions
at `437ca89`, not sixteen. The audit's probe table and its "15 checks passed" are right.

The cause was structural, not an oversight in one check. Every check that walked the report's entries
walked the entries that were *present*: it bound them to the report, required a panel and a spread on
each, and required a non-null total. Deleting records therefore left the loops nothing to refuse. No
check compared the report with what a complete report holds, and no check re-derived a recorded number
from the draws under it.

## 2. What was built

`harness/blind_baseline.py` gained six checks. `BASELINE_CHECKS` is 15 names at `437ca89` and 21 now.

| Check | What it refuses |
|---|---|
| `invocation_evidence` | A report whose transport owes isolation evidence and does not carry it |
| `cell_identity` | Cells that are not exactly the profile's grid: absent, unexpected, or repeated |
| `cell_members` | A panel with the wrong number of members, a member score off the unit interval, or a mean, agreement or majority call the members do not give |
| `criterion_identity` | Criterion scores that are not exactly the profile's criteria |
| `criterion_arithmetic` | A sample count the report does not declare, a sample off the scorecard's scale, or a median, spread, weight, factor or weighted-point figure its own samples do not give |
| `total_recomputed` | A total the criterion scores do not produce under the scorecard's weighting, and a declared maximum, threshold or threshold verdict the scorecard does not give |

Three decisions carry the work.

**The profile bundle is the authority for completeness.** `freeze_baseline` took a
`PreEvaluationProfile`. It now takes the loaded `ProfileBundle`. A profile alone cannot say which cells
a complete report holds — that is the rubric set crossed with the criterion-to-section map — nor what
scale and weighting its scores must satisfy. The redundant `profile_version` parameter is gone with it:
the version is `bundle.version`, so a caller can no longer pass a version the bundle contradicts.

**The cell grid has one definition.** `harness.blind_assessment.cell_grid` returns every
`(rubric, section_id)` pair an assessment grades, and `expected_cells` names the same pairs by
identity. `assess_candidate` walks the first. The freeze compares against the second. The expected set
cannot drift from the produced set, because they are the same function.

**Recomputation calls the producer, never a copy of it.** Each arithmetic check runs the function that
formed the number. A cell's panel is rebuilt as `Verdict` members and put back through
`harness.verdict.majority_vote`. The mean, the agreement and the majority call are therefore re-derived
by the code that produced them. A panel that will not re-vote at all is refused with that function's own
reason — too few members, or members about different properties.

A criterion's median, spread and weighted points come from `median_score`, `score_spread` and
`weighted_points_for`, extracted from `harness/criterion_scoring.py` so the grader and the checker share
one statement of each. The total comes from `weighted_total`. A figure that does not reproduce is a
refusal. Nothing is corrected, and no number of the freeze's own enters the record.

`off_scale_reason` is factored out of `harness/criterion_scoring.py`'s sample parser, so the scale rule
has one statement and two readers. The parser rejects a draw the assessor cannot have meant. The freeze
re-checks every recorded score against the same rule.

## 3. Transport-appropriate, and what that cost

The ticket asks for *transport-appropriate* evidence. `TRANSPORT_ISOLATION_EVIDENCE` is the table:

| Transport | What a baseline requires |
|---|---|
| `claude-cli` | `assessor_invocation` declaring `tools: ""`, `strict_mcp_config: true`, `working_directory_outside_repository: true`, plus the directory itself |
| `openai-compatible` | Nothing. The backend runs no child process and declares no isolation of its own. |
| Anything else | Refused. The freeze cannot say what evidence would be appropriate. |

One of those declarations is measured rather than read. The record names the working directory as well
as claiming it lay outside the repository, and a path either falls under `--repo-root` or it does not.
The freeze compares the two and refuses a record whose directory sits inside the repository, whatever
the declaration says. A record that claims the property and names no directory is refused as
unmeasurable. The other two declarations remain the backend's word; the audit's F04 point about declared
identifiers still holds for them, and section 8 says so.

An API-transport report therefore reaches a check that cannot apply. Listing it among the passes would
be a false claim, so `BaselineCheckRun` separates the checks that ran from the checks that did not, and
`checks_passed` is derived from the first. The freeze record gains `checks_not_applicable`, each row
carrying its check and its reason, and the rendered screen prints the count and names any exception.
The freeze schema moves 1.0.0 → 1.1.0 for the added key.

`blind_baseline` cannot import the command it is called by, so the transport names are a second literal.
Two tests keep them in step. One asserts the table's keys are the command's two `--transport` choices.
The other builds a real subscription backend and asserts that the declarations the table requires are
the declarations that backend makes.

## 4. The control still freezes

`tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline` runs the real `freeze_baseline`
over the committed report, with the real candidate at
`harness/blind_reports/candidates/MSCA-DN-2025_sanitised_part_b@b51a103520b58ded` and
`load_profile_bundle('harness/profiles/msca_dn_2026_default.json')`. Every case works on its own copy
under `tmp_path`.

- The control freezes with 21 of 21 checks passed, no check not applicable, 10 cells, 3 criterion
  scores and the total 74.6.
- Its freeze record reproduces the committed freeze's `report_sha256`, its `report_copy` name and every
  one of its 25 bindings, and the copy is byte-identical to the committed report.
- `run_baseline_checks` over the committed report returns no failure and no exception.
- Each of the audit's four probes raises `BlindBaselineError` naming its check and its reason, and the
  baseline directory is never created.

Nothing under `docs/` was written by any test. The committed baseline, its freeze record, both fidelity
registers, the approval records and the committed audits are untouched.

## 5. Checks run

| Check | Result |
|---|---|
| `tests/harness/test_blind_baseline.py` | 75 passed |
| `tests/harness/` (whole directory) | 1,487 passed, 17 skipped — the 17 declared exclusions, unchanged |
| `tests/test_msca_dn_*.py` (6 modules) | 317 passed |
| `tests/runner/test_dev_graph_{documents,intake,packages}.py` | 120 passed |
| `tests/runner/test_agnosticism_lint.py`, `test_agnosticism_second_instance.py`, `tests/harness/test_boundary.py` | 44 passed |
| `py -3.10 -m harness.commands.acceptance_lane` | GREEN, exit 0 — section 6 |

No new skip was introduced, so the lane's declared count of 17 still reconciles.

## 6. The acceptance lane

`py -3.10 -m harness.commands.acceptance_lane`, run after the last change in this ticket:

| | audit `ca0a443` | this lane |
|---|---|---|
| passed | 1,864 | 2,244 |
| failed | 44 | 0 |
| errors | 48 | 0 |
| skipped (declared exclusions) | 8 | 17 |
| collected | 1,964 | 2,261 |

`GREEN: 2,244 passed, 0 failed, 0 errors, 17 declared exclusions`, exit 0. No new skip, so the
declaration's count of 17 still reconciles. The lane's `freeze` area carries the invariant this ticket
strengthens:

> The baseline freeze binds what it froze and refuses what it must, and the frozen 74.60 report still
> passes the gate it was frozen under.

Both halves are now measured rather than assumed. What a green lane is not evidence of is printed with
every result and listed in `harness/ACCEPTANCE_LANE.md`.

## 7. What this is not evidence of

- Not evidence that gate G4 closes. V06 — the grounding scope in preflight, report and freeze — is open.
- Not evidence that the official 2025 original has been imported, assessed or frozen. V07 to V09 are
  open and V09 is the operator's.
- Not evidence that the 74.60 result is correct, calibrated or predictive. The freeze checks that a
  report is complete and internally consistent. It judges no score.
- Not evidence that the runbook is correct. It still describes fifteen freeze checks and claims the
  planted-marker test is one of them. Both statements are V12's to correct. Neither is corrected here.
- Not a new assessor run. No quota was spent.

## 8. Changes the ticket did not ask for, declared

Three things in this diff are not in V04's seven criteria. Each is named here rather than left to read
as required work.

| Change | Why it is here |
|---|---|
| `assess_candidate` walks the new `cell_grid` | Criterion 1 asks the freeze to enforce "the profile's exact expected cell set". A second definition of that set would be a second thing to keep in step. Walking one grid makes the expected set and the produced set the same function. Iteration order is preserved, and the committed report's 10 cells reproduce. |
| `off_scale_reason`, `median_score`, `score_spread`, `weighted_points_for` extracted from `harness/criterion_scoring.py` | Criteria 2 and 3 ask the freeze to re-derive scores the grader produced. Re-stating the grader's arithmetic in the checker would let the two drift silently, which is the defect's own shape. The four functions are moved, not changed, and the sample parser's messages are byte-identical. |
| `freeze_baseline` loses `profile_version`, and `render_freeze` gains a checks line | The first is redundant once the bundle is the argument: the version is `bundle.version`, so no caller can pass one the bundle contradicts. The second keeps the printed screen honest about the new third outcome, since `checks_not_applicable` would otherwise appear only in the file. |

## 9. Remaining uncertainties

- **Two of the three isolation declarations are still the backend's word.** `tools: ""` and
  `strict_mcp_config: true` are read from the record. Only the working directory is measured. The
  audit's F04 warning about declared identifiers rather than runtime attestation therefore still
  applies to those two, and closing it needs the operator's isolation receipt (V13), not a freeze check.
- **The unit-interval bound on member scores is the harness's own convention**, not a scorecard
  declaration: `grade_expectation` normalises a coverage verdict to `[0, 1]`. If a future rubric set
  scores cells on another scale, `cell_members` is the check to amend.
- **The identity comparison is over cell and criterion ids, not over rubric content.** A report whose
  cell carries the right triple and a rationale about something else is not refused here. The rubric
  fingerprint the report already binds is what covers that, and it is not re-derived at freeze time.
- **No committed report exercises the API-transport branch.** `openai-compatible` is covered by the
  synthetic world and by a mutated copy of the committed report, not by a real API-transport baseline.
- **A cell's identity is a bare triple of ids.** It travels as `tuple[str, str, str]` through
  `expected_cells`, the two counters and the failure labels. A named type would read better. A tuple is what a
  `Counter` key wants, so it stayed.
