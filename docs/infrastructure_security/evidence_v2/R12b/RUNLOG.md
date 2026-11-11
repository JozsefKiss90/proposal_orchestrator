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
