# R14 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-11-12 |
| Step sheet | `STEPS.md` (steps 01–16, points 1–13), run as in `RUNLOG.md` |
| Decisions | `aws-redeployment-r14-operations_2026-11-12` (R14-D1–D6, F-R14-1–4) |
| Stacks | `proposal-orchestrator-host`, twice. Creation A: executed 12:12:19, deleted 12:18:29 UTC. Creation B: executed 12:35:46, delete 12:51:33, `RESULT=deleted` 12:55:51 UTC. Two further change sets (step 12 tries 1–2) were never executed |
| Cost | About 0.44 billable hours in all, at most 0.07 USD at the running rate, against 0.26 USD stated before the go. Credits 199.19 USD at step 01 |
| Secret scan | Agent over `evidence_v2` after each edit: CLEAN. Operator step 16 after this report |

Every check below was re-run by the agent on the saved files (`utf-8-sig`), by script.

## Criteria

| Step | Criterion | Evidence | Status | Reason |
|---|---|---|---|---|
| 01 | Plan, budget, notifications, caller | `R14_01_*` | PASS | FREE / ACTIVE to 2027-04-19, 199.19 USD; one budget, 0.523 of 10 USD; ACTUAL 85, ACTUAL 100, FORECASTED 100; account 797661577394 |
| 02 | Nothing left by R12b | `R14_02_*` | PASS | Host stack absent (`exit=254`); only the S3 gateway endpoint; no instance, no project volume; base stacks equal `R12b_fix1_10_base-stacks.json` |
| 03 | Lint, guards, tests, PowerShell plan | `R14_03_*` | PASS | cfn-lint 1.57.2 clean; both guards CLEAN; `217 passed` as stated at round 0; plan `exit=0`, 29 `aws` lines with Region and profile, one `delete-stack` on the host stack |
| 04 | Unit prices from the Price List API | `R14_04_*` | Deviation (R14-D1) | The API refused all eight items (`AccessDeniedException`). Prices taken from the public offer files: `deploy/aws/pricing/eu-north-1.json`, extract `R14_04_agent-offer-extract.json` (13 SKUs) |
| 05 | Cost check, first run | `R14_05_cost-check/`, `R14_05_cost-check-console.txt` | PASS | `exit=0`; credits equal step 01; month-to-date by service; budget and spend; HUF `pending`; running 0.154686, stopped 0.063916 USD/h; five creations priced with Opus 4.6 tokens; 13 price rows with URL and date |
| 06 | CloudShell readiness | `R14_06_*` | PASS | CloudShell offered in `eu-north-1`; caller and Region correct; three SHA-256 equal to round 0; `RESULT=ready` |
| 07 | PowerShell start, create path | `R14_07_*` | PASS | Seven `Add`, no capabilities, tag, `c7i-flex.large`; `CREATE_COMPLETE`; seven outputs, none equal to R12b's; `Online`, Amazon Linux 2023 |
| 08 | F7 retest | `R12b/R12b_fix2_08_*` | PASS, operator-accepted (R14-D3, R14-D4) | Run in creation B, not A. `403 AccessDenied`, names the VPC endpoint policy, `RESULT=expected`; no URL in the file; bucket removed. Object count `None`, not `0` (F-R14-3) |
| 09 | PowerShell stop | `R14_09_*` | PASS | `stopped`; one 8 GB gp3 volume `in-use`; seven endpoints `available` |
| 10 | CloudShell start, resume path | console in `RUNLOG.md`; `R14_11r_trail-StartInstances.json` | PASS, Inferred (R14-D5) | Files lost before download. Console: `path=resume`, `confirmed=start`, `Online`, `RESULT=started`. CloudTrail `StartInstances` 12:17:36 on creation A's instance |
| 11 | CloudShell teardown | console in `RUNLOG.md`; `R14_11r_*` | PASS, after-checks by recovery (R14-D5) | The script issued the delete (12:18:28) and was then interrupted while waiting. Recovery: stack absent, `DELETE_COMPLETE` 12:18:29; only the S3 gateway; no ENI, instance or volume; base stacks equal step 02 |
| 12 | CloudShell start, create path | `R14_12_*` | PASS (third try) | Tries 1–2 `confirmed=no` from a buffered Enter (F-R14-2), nothing created. Try 3: seven `Add`; `CREATE_COMPLETE`; outputs all differ from step 07; `Online` |
| 13 | CloudShell stop | `R14_13_*` | PASS | As step 09. Unpacked by the agent from the operator's download |
| 14 | PowerShell start, resume path | `R14_14_*` | PASS | `path=resume`, `confirmed=start`; same `InstanceId` as step 12; `Online`. A first try ran the step 09 command and was refused before any AWS call |
| 15 | PowerShell teardown | `R14_15_*` | PASS | `confirmed=delete`, `RESULT=deleted`; stack absent; only the S3 gateway; no ENI, instance or volume; `base_stacks_complete=5`, equal to step 02 |
| 16 | Tests, guard, scans last | `R14_16_*` | Pending | After this report. Expected: `224 passed` (agent run 2026-11-12, after the F-R14-1 and F-R14-2 fixes) |

## Ticket checklist

| Ticket criterion (`plans/aws_redeployment_tickets.md`, R14) | Status | Evidence |
|---|---|---|
| Each script ran once end to end, with evidence | PASS, with two recovered steps (operator to confirm) | PowerShell form: create, stop, resume, teardown (07, 09, 14, 15), all from the script's own files. CloudShell form: check, create, stop (06, 12, 13) from its own files; resume (10) from the console and CloudTrail; teardown (11) issued by the script, after-checks by the recovery block |
| The cost check ran once. Every price in it cites its pricing page and date | PASS, with R14-D1 (operator to confirm) | `R14_05_cost-check/report.md`: each row cites the AWS price list offer file read and the date 2026-11-12. The Price List API was refused; the offer files are the same price list, read anonymously |
| The upgrade checklist exists and is marked operator-only | PASS | `docs/infrastructure_security/aws_od10_upgrade_checklist.md`: "Operator only" in its first line; status "Not started. Blocked by the ELTE approval" |

## Changes after round 3 (no AWS call)

- **F-R14-1 fixed.** The start refusal now gives advice per state: review (run teardown), any
  `*_IN_PROGRESS` (wait and run again), any other (teardown, then start). Both forms.
- **F-R14-2 fixed.** Before each typed-word prompt, both forms discard input typed while the script ran,
  only at a terminal (`[ -t 0 ]`; `[Console]::IsInputRedirected`). The fake-CLI tests pipe their answer,
  so they still read it. **Not yet run at a real terminal.**
- Tests: `test_start_refuses_a_stack_in_another_state_with_advice_for_that_state` (three states, both
  forms), `test_prompt_discards_input_typed_before_it_only_at_a_terminal`. The lifecycle file gives 56.
- The step 06 hashes change for the script files. The next CloudShell session uploads the new script
  and records new hashes.

## Done conditions

- [x] Every step above is PASS or carries its recorded deviation.
- [x] Price file and budget file committed; the HUF amount stays `null` (point 6).
- [x] R12b `VERIFICATION.md` addendum for F7 written.
- [x] Decision record `aws-redeployment-r14-operations_2026-11-12` drafted.
- [ ] Step 16 after this report.
- [ ] Operator confirms R14 (criteria 1 and 2 with their deviations) and F7.

## Notes for later tickets

- **R15:** the first host session with the fixed scripts. A CloudShell teardown there, run to its
  `RESULT=deleted`, also closes the only part of criterion 1 not shown by the script's own files.
- **F-R14-3:** if the F7 block is reused, count objects with `--no-paginate` or `length(Contents || [])`.
- **Weekly cost check:** `evidence_v2/ops/cost/<date>/` (point 11). Cost Explorer lags up to 24 hours:
  on 2026-11-12 it showed one of the two R11/R12b Converse calls.
- **Collector fixes F-R12b-2, -3, -4** remain before the collector's next run.
