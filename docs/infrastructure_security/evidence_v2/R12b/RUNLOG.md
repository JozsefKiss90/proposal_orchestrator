# R12b — run log

| Field | Value |
|---|---|
| Ticket | R12b (full re-evidence and register v2) |
| Step sheet | `STEPS.md` |
| Kept by | agent (Claude), from the operator's reports in session |

## Settling

| When (UTC, approx.) | Who | What |
|---|---|---|
| 2026-11-11 22:58 | operator | "R11 confirmed, the two decisions review, check the R11 ticket, 12b is a go". The go came before any R12b sheet existed |
| 2026-11-12 | operator | Answers to the agent's three questions: DC-33–DC-35 deferred to R15; F7 bucket in a second account the operator controls; the go holds for the one creation once the sheet is reviewed (`STEPS.md` points 1–3) |
| 2026-11-12 | agent | Wrote `STEPS.md` (steps 01–12, points 1–9). DC-39 source read for point 8: AWS Service Terms §1.14.1, "These Service Terms incorporate the AWS Data Processing Addendum ("DPA"), when you use AWS Services to process Customer Data (as defined in the DPA)", page "Last Updated: November 5, 2026", read 2026-11-12 (https://aws.amazon.com/service-terms/) |
| 2026-11-12, before round 1 | operator | "points 4, 7, 8 confirmed; round 1 is complete" |

## Round 1 — steps 01–04 (read-only, workstation, unexecuted change set)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 01 | 2026-11-11, ~23:09 | operator | FREE / ACTIVE, credits 199.25 USD (unchanged: R11 usage not yet billed); one budget, spend 0.492 of 10.0 (R11 F01: 0.478); three notifications `OK`; caller `AccountFullAccessRole` in 797661577394 | none |
| 02 | 2026-11-11, ~23:09 | operator | Host stack does not exist (`exit=254`); only the S3 gateway endpoint; no network interface, no instance; base stacks and 25 exports equal `R11_03_*` | none |
| 03 | 2026-11-11, ~23:10 | operator | cfn-lint 1.57.2 exit 0; template guard and old-ID guard CLEAN; Python 3.10.6, `324 passed, 1 skipped`; collector plan `exit=0`, 82 commands with `--profile po-r1`, the 13 host checks "host stack outputs absent", no `get-secret-value` | `.venv-lint` was active (the prompt shows it); `py -3.10` ran the system interpreter regardless, as the first pytest line shows |
| 04 | 2026-11-11 23:10:51 | operator | Change set `r12b-create-01`: `CREATE_COMPLETE` / `AVAILABLE`, no capabilities, tag `project`; parameter values equal `R11_fix1_05_change-set.json` (`c7i-flex.large`; the image is the same as R11's); exactly seven `Add` | none |
| check | 2026-11-12 | agent | Every round 1 criterion PASS by script (`utf-8-sig`); plan ids all from the R4–R8 outputs files. The change set lists the seven expected additions, so the go of point 3 holds for step 06 without a further go | — |

## Round 2 — steps 05–11 (first creation)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 05 | 2026-11-11, before 23:36 | operator | Not reported. At step 09 the URL file did not exist | See step 09 |
| 06 | 2026-11-11 23:36:41 | operator | `execute exit=0`; `CREATE_COMPLETE` (stack status 23:38); 24 events, all seven resources and the stack `CREATE_COMPLETE`, none failed; tag `project`. **Hourly charges start** | none |
| 07 | 2026-11-11 ~23:40 | operator | `R12b_outputs.json`: seven keys, no export, seven distinct ids, none equal to R11's; `InstanceId` `i-05230b6ee9543190d` | none |
| 08 | 2026-11-11 ~23:40 | operator | `Online`, Amazon Linux 2023, agent 3.3.5700.0, `EC2Instance` | none |
| 09 | 2026-11-11 23:40:48 | operator | **`REFUSED: the F7 URL file cannot be read`, `exit=2`.** The collector stops before any AWS call; no `R12b_09_collector` folder; nothing collected | The URL file did not exist when the collector read it (`OSError`). Handled per point 6: no re-run, straight to step 10 |
| 10 | 2026-11-11 23:41:23 – ~23:45 | operator | `delete exit=0`; stack does not exist (`exit=254`); no interface, instance or project volume; base stacks equal step 02. **Hourly charges end** (~9 minutes) | none |
| 11 | 2026-11-11 ~23:47 | operator | Ran without a collector folder: `started_utc` empty, so `lookup-events` failed on `--start-time` (`ParamValidation`) and `R12b_11_converse-events.json` holds one all-null record | Invalid run, two minutes after the delete. The files stay as evidence of the deviation and support no criterion. Not reported: whether the URL file and the outside bucket were removed |
| check | 2026-11-12 | agent | Steps 06, 07, 08 and 10 PASS by script. Steps 09 and 11 FAIL (no collection). `STEPS_fix1.md` written: the URL file is written and read by the collector's `--plan` before the stack exists; new change set `r12b-create-02`; fix-run files `R12b_fix1_*`. A second creation needs a new go (point 3 covered one) | — |

## Fix 1 — round 1b (steps F01, F04, F05; nothing billable)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| F01 | — | operator | Not reported | Run before F06 |
| F04 | 2026-11-11 23:52:11 | operator | Change set `r12b-create-02`: equal to `R12b_04_change-set.json` in status, capabilities, tag, the seven `Add` and every parameter value (same image) — PASS by script. It waits unexecuted (no cost) | none |
| F05 (plan first) | 2026-11-11 ~23:53 | operator | `exists=False`; the collector's plan refused with `the F7 URL file cannot be read`, `exit=2` (`R12b_fix1_05_collector-plan.txt`) | Order reversed: the read check ran before `STEPS.md` step 05. The check worked as intended: it stopped the run before any stack existed |
| F05 (step 05) | 2026-11-11 ~23:54 | operator | Run with the placeholders `<outside-profile>` and `<outside-bucket-name>` unreplaced: `The config profile (<outside-profile>) could not be found`; `Out-File` left an **empty** `po-f7-url.txt` (0 bytes) | No URL was created; nothing reached AWS in either account. Blocked on the second account's CLI profile (asked in session) |
| settle | 2026-11-12 | operator | No second AWS account: "use this one". Point 2 changes: the URL is presigned with `po-r1` for a random bucket name this account does not own; no bucket is created. `STEPS_fix1.md` F05 rewritten (head-bucket classification, URL, then the collector's plan reads it). The test now rests on the endpoint policy's Allow list (only reads on the deploy bucket), not on an outside signer | — |
