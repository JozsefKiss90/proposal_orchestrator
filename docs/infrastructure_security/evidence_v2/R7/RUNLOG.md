# R7 — run log

| Field | Value |
|---|---|
| Ticket | R7 (audit and storage stack) |
| Step sheet | `STEPS.md` |
| Kept by | agent (Claude), from the operator's reports in session |

## Round 1 — steps 01–03 (read-only)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| sign-in | 2026-10-26 ~17:20 | operator | `aws login --profile po-r1` from the VS Code PowerShell, repository root (`.venv-lint` active; no `py` command in this round) | none |
| 01 | 2026-10-26 ~17:22 | operator | Plan FREE / ACTIVE, credits 199.99 USD (the key's monthly fee not yet visible), expiry 2027-04-19; budget spend 0.006 of 10.0; three notifications OK | none |
| 02 | 2026-10-26 ~17:22 | operator | Account 797661577394, assumed-role/AccountFullAccessRole | none |
| 03a–03h | 2026-10-26 ~17:22 | operator | Both bucket names 404 (free); no bucket in the account; no trail; no log group at all; no flow log; one subnet in the project VPC; invocation logging unset (`exit=0`, empty body); audit stack does not exist (`exit=254`); key Enabled, policy as R6; 17 exports, the four import values as in the outputs files | none. PowerShell wrapped the three expected errors in `NativeCommandError` records |
| check | 2026-10-26 ~17:26 | agent | All eighteen files PASS against `STEPS.md`; key policy equal to `R6_08_key-policy.json` by `Sid`; secret scan of this folder and old-ID guard CLEAN | — |
| fill | 2026-10-26 ~17:45 | agent | `40-audit.yaml` filled, `outputs_contract.json` consumers changed (R7-D11), `tests/test_aws_audit_template.py`, decision record `aws-redeployment-r7-audit_2026-10-26`, README; agent's run: cfn-lint 1.57.2 exit 0, template guard CLEAN (6), old-ID guard CLEAN, 177 passed (Python 3.10.12). Steps 04–05 added | — |

## Round 1b — steps 04–05 (lint, guards, tests, change set)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 04 | 2026-10-26 ~17:32 | operator | cfn-lint 1.57.2 exit 0; template guard CLEAN (6); old-ID guard CLEAN; Python 3.10.6, 177 passed | `.venv-lint` was active during the `py -3.10` commands (the sheet says to `deactivate` first); harmless, `py -3.10` resolves to the system interpreter |
| 05 | 2026-10-26 17:33:20 | operator | Change set `r7-create-01` `CREATE_COMPLETE` / `AVAILABLE`; `Capabilities` `[]`; tag `project`; three parameters; seven `Add`: `TrailBucket`, `TrailBucketPolicy`, `Trail`, `DeployBucket`, `DeployBucketPolicy`, `FlowLogGroup`, `VpcFlowLog`. The stack now exists in `REVIEW_IN_PROGRESS` with no resources | none |
| check | 2026-10-26 ~17:37 | agent | Steps 04–05 files PASS against `STEPS.md`; secret scan of this folder and old-ID guard CLEAN | — |
| go | 2026-10-26 ~17:39 | operator | Go in session ("17 a, go 06") on `R7_05_change-set.json`: seven `Add`, as listed; point 17 (test uploads) accepted. Agent added steps 06–10 to `STEPS.md` (R7-D17; a simulation of the runtime role against the bucket policy was drafted and dropped, F-R7-7) | — |

## Round 2 — steps 06–10 (execute, outputs, read-only evidence, test uploads, credits)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 06 | 2026-10-26 ~17:44 | operator | `execute exit=0`; stack `CREATE_COMPLETE`, 25 events, no `FAILED`/`ROLLBACK`; trail logging since 17:44:09 UTC (created without a CloudTrail decrypt grant: R6-D10 holds at creation); deploy bucket policy with `NotResource` accepted | `.venv-lint` active (no `py` command in this round) |
| 07 | 2026-10-26 ~17:45 | operator | Six outputs as the contract; `FlowLogId` `fl-018e0a5b5610c35c7`; `VpcId` imported only by the audit stack | none |
| 08 | 2026-10-26 ~17:46 | operator | Both buckets: SSE-KMS with the CMK (Bucket Key false / true), BPA four true, versioning Enabled, `BucketOwnerEnforced`, tags; both policies equal the template; lifecycles as decided; trail as decided (validation on, CMK, `IsLogging` true, default selectors); one log group (CMK, 90 days); flow log `ACTIVE` / `SUCCESS` on the VPC; invocation logging unset; no `/aws/bedrock` group | S3 also reports `BlockedEncryptionTypes: SSE-C` in both encryption rules (an S3 default the template does not set; harmless, recorded) |
| 09 | 2026-10-26 ~17:47 | operator | Header-less PUT accepted with the CMK and the Bucket Key (11 bytes); `AES256` and key-less `aws:kms` PUTs refused with an explicit deny in the resource-based policy (`exit=254`); the accepted version deleted by version id; nothing left under the test prefix | The pasted transcript shows `--outputjson` on the 09b line; a terminal-wrap artifact (R4 lesson), the result file is the expected refusal |
| 10 | 2026-10-26 ~17:47 | operator | FREE / ACTIVE, credits 199.99 USD | none |
| check | 2026-10-26 ~17:55 | agent | All round-2 files PASS (36 checks; bucket policies compared statement by statement with the resolved template); secret scan of this folder and old-ID guard CLEAN | — |

## Round 3 — step 11 (delivery)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 11 | 2026-10-26 ~18:57 | operator | `IsLogging` true; latest delivery 18:52:24 UTC, latest digest 18:00:48 UTC, no errors; 14 log files and 1 digest under `cloudtrail/proposal-orchestrator/AWSLogs/797661577394/` (plus CloudTrail's two zero-byte folder keys), all SSE-KMS with the CMK and no Bucket Key; `validate-logs` `1/1 digest files valid`, exit 0, but no log file covered yet; flow log `ACTIVE` / `SUCCESS`, no stream (no interface in the VPC, R7-D18) | The opening digest covers no log file; step 11b added to validate log files against the next hourly digest |
| check | 2026-10-26 ~19:05 | agent | Step 11 files PASS except the log-file half of `R7_11_validate-logs.txt` (pending, step 11b); secret scan CLEAN | — |
| 11b | 2026-10-26 ~19:35 | operator | `IsLogging` true; latest digest 19:01:20 UTC, latest delivery 19:31:44 UTC, no errors; `validate-logs` 17:44:09Z–18:44:09Z: `2/2 digest files valid`, `12/12 log files valid`, exit 0 | Pasted in session as text (no attachment); verified from the files |
| check | 2026-10-26 ~19:40 | agent | Step 11b PASS; `VERIFICATION.md`, register v2 rows, DC-19 note, worklog entries written; decision record F-R7-9; secret scan CLEAN | — |

## Round 4 — step 12 (closing)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 12 | 2026-10-26 ~20:27 | operator | `deactivate` first; Python 3.10.6, 177 passed; old-ID guard CLEAN; secret scan of this folder CLEAN, run last | none |
| check | 2026-10-26 ~20:30 | agent | Step 12 files PASS; `VERIFICATION.md` completed except the commit; agent re-ran the secret scan after the edit → CLEAN | — |
