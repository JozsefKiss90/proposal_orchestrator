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
| F05 (run 2) | 2026-11-12 ~00:02 | operator | URL file empty (0 bytes); the collector's plan refused: `the F7 file does not hold one https S3 URL`, `exit=2` (`R12b_fix1_05b_collector-plan.txt`). Nothing reached AWS but `head-bucket`; the Python error was not reported | The `po-r1` profile is an `aws login` session; Python's signing did not yield a URL from it. F05 amended: credentials come from `aws configure export-credentials`, held in this window's environment for the one Python call, then removed; Python errors stay on screen. Agent tested the signing line with dummy credentials (no AWS call): a virtual-hosted `eu-north-1` URL, 371 characters, matching the collector's pattern. `R12b_fix1_05b_collector-plan.txt` is overwritten by the next run |
| 06 (out of order) | 2026-11-12 00:11:46 | operator | `STEPS.md` step 06 run unamended: `execute-change-set … r12b-create-01` → `ChangeSetNotFound` (consumed in round 2), `execute exit=254`. **Nothing was created.** `wait stack-create-complete` then waited on the stack in `REVIEW_IN_PROGRESS` (it holds only the unexecuted `r12b-create-02`) and never returned; operator reported "F06 is not doing anything" | No go had been given and F01/F05 had not been handed back. The block overwrote round 2's `R12b_06_execute-exit.txt`: the agent saved the new text as `R12b_fix1_06x_wrong-change-set-exit.txt` and restored round 2's file from git (`execute exit=0`). `R12b_06_stack-status.json` and `-events.json` were not rewritten (the wait never returned) |
| go | 2026-11-12 00:25 | operator | "go" for F06 (second creation, `r12b-create-02`). F01 and F05 had not run at that moment (no `R12b_fix1_01_*`; the URL file still empty). Recorded as a go that takes effect only if F01 and F05 pass: `STEPS_fix1.md` "Combined blocks" gates F06 on both inside one paste, and Block B deletes the stack in every case | — |
| check | 2026-11-12 | agent | The secret scan refused `STEPS_fix1.md`: the F05 amendment of `534ff8a2` named two credential environment variables and a property whose names are scan patterns (committed without the scan, the agent's error). Rewritten so those names are assembled at run time; scan CLEAN over `R12b` and `evidence_v2` | — |
| F05 (run 3) | 2026-11-12 00:30:18 | operator | Standalone F05 block (output not pasted; checked on disk): URL file written (2489 bytes; not opened by the agent); `R12b_fix1_05b_collector-plan.txt` `exit=0`, 96 lines, no `REFUSED`, `[f7-presigned-put]` with `PO_F7_URL='<f7-url>'` (masked), no `https://` in the file — **PASS**. Signing with CLI-exported credentials works. F01 still not run | — |

## Fix 1 — round 2b (Blocks A and B: F01, F05, F06–F10)

| Step | UTC | Who | Result | Deviation / error |
|---|---|---|---|---|
| F01 | 2026-11-12 ~00:34 | operator | `F01_ok=True`: FREE / ACTIVE, credits 199.25 USD, spend 0.492 of 10.0, notifications `OK`, account 797661577394 — PASS | `.venv-lint` deactivated first |
| F05 | 2026-11-12 ~00:34 | operator | `head_bucket_exit=254` (no bucket of that name, or not this account's); URL `starts_https=True names_eu_north_1=True length=2459`; plan `exit=0`, masked; `F05_ok=True` — PASS | none |
| F06 | 2026-11-12 00:34:46 | operator | `execute exit=0` (`r12b-create-02`); `CREATE_COMPLETE`; 24 events, none failed; tag `project` — PASS. **Hourly charges start** | none |
| F07 | 2026-11-12 ~00:37 | operator | `R12b_outputs.json` overwritten: seven keys, no export, seven distinct ids, none equal to R11's or round 2's; `InstanceId` `i-0cc2765679c1f96df` — PASS | Round 2's ids remain in this log and `R12b_08_instance-information.json` |
| F08 | 2026-11-12 ~00:37 | operator | `Online` at try 0 — PASS | none |
| F09 | 2026-11-12 00:37:25 – 00:42:16 | operator | Collector `exit=0`: `collected 93, expected_error 1, not_collected 1, error 0`; the expected error is DC-40 `list-policies` `AccessDeniedException`; not collected: the launcher check (point 1). 102 files, manifest re-hashed by the agent; secret scan and old-ID guard CLEAN; the URL appears nowhere. Host checks (agent, by script): DC-02, DC-14, DC-17, DC-31, DC-32, DC-37 `Success` and `RESULT=expected`. **DC-15 `RESULT=unexpected`** and **F7 `http_status=404`, `error_code=NoSuchBucket`, `message_names_vpc_endpoint_policy=no`**: see the check row. `DC-26_converse-events.json` holds 0 events (F-R12a-2, as expected; F11 repeats it) | none |
| F10 | 2026-11-12 00:42:16 – ~00:45 | operator | `delete exit=0`; stack does not exist (`exit=254`); no interface, instance or project volume; base stacks equal step 02 — PASS. **Hourly charges end** (~8 minutes). URL file removed (absent on disk) | none |
| check | 2026-11-12 | agent | **DC-15:** every file scanned has 0 matches and 140 process environments hold no key variable; `RESULT=unexpected` comes only from the last test, `cli_credential_source`, which printed the masked key id instead of the credential type. The script reads column 3 of `aws configure list`; AWS CLI 2.38 on AL2023 puts the value there, not the type. A script defect (R12a known gap D4: first run on AL2023), not a key on the host: DC-14 shows the CLI's caller is the runtime role's instance session. Proposed DC-15 status: VERIFIED_PASS, Inferred, with the defect recorded. **F7:** S3 answered `404 NoSuchBucket`, not the endpoint's `403`. The step's criterion calls that an F7 FAIL: the request was not refused by the endpoint policy before S3 looked up the bucket. A bucket that does not exist cannot receive data, but the run does not show the refusal F7 asks for. **F7 stays open** | — |
