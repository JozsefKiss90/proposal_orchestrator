# R11 — run log

| Field | Value |
|---|---|
| Ticket | R11 (endpoints and host: first PrivateLink call) |
| Step sheet | `STEPS.md` |
| Kept by | agent (Claude), from the operator's reports in session |

## Settling

| When (UTC, approx.) | Who | What |
|---|---|---|
| 2026-11-11 | agent | Wrote `STEPS.md` round 1, with points 1–10 the agent decided where no decision record settles them |
| 2026-11-11 | operator | "Having reviewed the R11 steps, I would also like to merge them." Merged as `34a4e2e1` |
| 2026-11-11 | operator | "R11: I'll run steps 01–05 and hand back the change set." |

## Round 1 — steps 01–05 (read-only, then an unexecuted change set)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| sign-in | 2026-11-11, before 19:02 | operator | VS Code PowerShell, repository root, profile `po-r1`, `.venv-lint` active | none |
| 01 | 2026-11-11, before 19:02 | operator | Plan FREE / ACTIVE, credits 199.25 USD (floor 195.00), expiry 2027-04-19; one budget, spend 0.478 of 10.0; three notifications OK | none |
| 02 | 2026-11-11, before 19:02 | operator | Account 797661577394, assumed-role/AccountFullAccessRole | none |
| 03a–03h | 2026-11-11, before 19:02 | operator | Host stack does not exist (`exit=254`); only the S3 gateway endpoint `vpce-0770a3016be1317ef`, no network interface, no instance; five base stacks `CREATE_COMPLETE`; 25 exports; image `ami-04005916a1c241ff5` (`al2023-ami-2023.12.20261109.0-kernel-6.18-x86_64`, x86_64, amazon, `/dev/xvda`, 8 GiB); dry run `DryRunOperation` (`t3.medium` accepted on the Free plan); invocation logging unset (`exit=0`, no `loggingConfig`); EBS encryption by default true, key `alias/aws/ebs`; IMDS defaults `required`, hop limit 1 | none. PowerShell wrapped the two expected errors in `NativeCommandError` records |
| 04 | 2026-11-11, before 19:02 | operator | cfn-lint 1.57.2 `exit=0`, no finding; template guard CLEAN (6); old-ID guard CLEAN (20 ids); Python 3.10.6, 259 passed | none. Run with `.venv-lint` active; the sheet asks for `deactivate` first, and `py -3.10` ran regardless |
| 05 | 2026-11-11 19:02:19 | operator | Change set `r11-create-01` (`7225569d-12c8-45a3-9d8d-655d96d33653`): `CREATE_COMPLETE`, `AVAILABLE`, no capabilities, tag `project=proposal-orchestrator`; exactly seven `Add` changes: six `AWS::EC2::VPCEndpoint` (`BedrockRuntimeEndpoint`, `StsEndpoint`, `SecretsManagerEndpoint`, `SsmEndpoint`, `SsmMessagesEndpoint`, `Ec2MessagesEndpoint`) and `Host` (`AWS::EC2::Instance`) | none |
| check | 2026-11-11 | agent | All 22 files PASS against `STEPS.md` (`utf-8-sig`, by script): the 25 export values equal the R4–R8 outputs files (7 network, 7 iam, 3 kms, 6 audit, 2 secret); `FoundationModelArns`, `InferenceProfileArns`, `ExpectedAccountId` and `ExpectedRegion` equal `deploy/aws/parameters/host.json`; `ProjectName` and `InstanceType` take the template defaults; the resolved AMI equals `R11_03_image.json`. Secret scan of this folder (the four patterns of `STEPS.md` step 23) and old-ID guard CLEAN | — |

**STOP — end of round 1.** Step 06 starts hourly charges. It runs only after the operator's explicit go
in session on `R11_05_change-set.json`, recorded below with its UTC time and the operator's words.

## Round 2 — steps 06–23

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| go | — | operator | Not recorded in session before execution. The operator executed step 06 and reported the result afterwards, in session on 2026-11-11 | The sheet asks for the go and its UTC time in this log before step 06 |
| 06 (run 1) | 2026-11-11 20:12:14–20:19:02 | operator | `execute-change-set` started creation at 20:12:14. The six endpoints reached `CREATE_COMPLETE` between 20:13:13 and 20:13:23. `Host` started at 20:13:23 and failed at 20:13:25: "The specified instance type is not eligible for Free Tier". Rollback deleted all seven resources by 20:19:01; the stack is `ROLLBACK_COMPLETE` (20:19:02). The host never ran; the six endpoints existed for about seven minutes | **STOP rule of step 06.** First failed event: `Host` `CREATE_FAILED`. `R11_06_stack-status.json` and `R11_06_stack-events.json` are this run's |
| 06 (run 2) | 2026-11-11, after 20:19 | operator | The step 06 block ran a second time. `execute-change-set` answered `ChangeSetNotFound` (`exit=254`): run 1 had consumed `r11-create-01` | `R11_06_execute-exit.txt` holds run 2's output; run 1's execute output was overwritten and is not kept |
| check | 2026-11-11 | agent | The refusal answers OD9's known gap: the Free plan does not admit `t3.medium`. Step 03g's dry run returned `DryRunOperation` for `t3.medium`, so a dry run does not evaluate Free Tier eligibility | Operator chose `c7i-flex.large` in session. Fix sheet: `STEPS_fix1.md` |

## Round 1b — `STEPS_fix1.md` steps F01–F05

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| merge | 2026-11-11, before 20:51 | operator | `aws/r11-fix1-instance-type` merged `--no-ff` as `d2cadc0d` | none |
| F01 | 2026-11-11, before 20:51 | operator | Plan FREE / ACTIVE, credits 199.25 USD (floor 195.00), expiry 2027-04-19; one budget, spend 0.478 of 10.0; three notifications OK; account 797661577394, assumed-role/AccountFullAccessRole | none |
| F02 | 2026-11-11, before 20:51 | operator | Stack before: `ROLLBACK_COMPLETE`; `delete exit=0`; stack after: `ValidationError`, does not exist, `exit=254`; VPC holds only the S3 gateway endpoint `vpce-0770a3016be1317ef` (`available`), no network interface, no instance | none. PowerShell wrapped the expected error in a `NativeCommandError` record |
| F03a | 2026-11-11, before 20:51 | operator | Six Free Tier eligible types: `c7i-flex.large` (x86_64, 2 vCPU, 4096 MiB, not burstable); `m7i-flex.large` (x86_64, 2 vCPU, 8192 MiB, not burstable); `t4g.small` (arm64, 2 vCPU, 2048 MiB, burstable); `t4g.micro` (arm64, 2 vCPU, 1024 MiB, burstable); `t3.small` (x86_64, 2 vCPU, 2048 MiB, burstable); `t3.micro` (x86_64, 2 vCPU, 1024 MiB, burstable). No `t3.medium` | none |
| F03b | 2026-11-11, before 20:51 | operator | `c7i-flex.large` and `t3.micro` both offered in `eu-north-1a` (`PrivateSubnetAz`) | none |
| F03c | 2026-11-11, before 20:51 | operator | Image `ami-04005916a1c241ff5` (equals `R11_03_image.json`); dry run of `c7i-flex.large` without a credit option: `DryRunOperation`, `exit=254` | none |
| F03d | 2026-11-11, before 20:51 | operator | Dry run with `CpuCredits=standard`: also `DryRunOperation`, `exit=254`. EC2's dry run does not refuse the credit option on this non-burstable type | Informational, no criterion |
| F04 | 2026-11-11, before 20:51 | operator | cfn-lint 1.57.2 `exit=0`, no finding; template guard CLEAN (6); old-ID guard CLEAN (20 ids); Python 3.10.6, 260 passed | none |
| F05 | 2026-11-11 20:51:08 | operator | Change set `r11-fix1-create-01` (`56f5efbe-2e22-4905-8f54-ec1f7e70ec03`), stack id `9efe1ce0-de11-11f1-ad55-0affe3c28faf`: `CREATE_COMPLETE`, `AVAILABLE`, no capabilities, tag `project=proposal-orchestrator`; exactly seven `Add` changes, the same six `AWS::EC2::VPCEndpoint` and `Host` as step 05 | none |
| check | 2026-11-11 | agent | All 20 files PASS against `STEPS_fix1.md` (`utf-8-sig`, by script): `FoundationModelArns`, `InferenceProfileArns`, `ExpectedAccountId` and `ExpectedRegion` equal `host.json`; `ProjectName`, `InstanceType` (`c7i-flex.large`) and `LatestAmiId` take the template defaults; the resolved image equals F03c's. Secret scan of the `R11_fix1_*` files CLEAN. OD9-r1 updated with the F03 measurements | — |

**STOP — end of round 1b.** Step 06 (as amended in `STEPS_fix1.md`) starts hourly charges. It runs only
after the operator's explicit go in session on `R11_fix1_05_change-set.json`, recorded below with its UTC
time and the operator's words.

## Round 2b — steps 06–23 (amended by `STEPS_fix1.md`)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| go | 2026-11-11 21:00:40 | operator | "OD9-r1 confirmed; go for R11 step 06", in session on `R11_fix1_05_change-set.json`. Recorded before execution. Step 13 deletes the stack in this same session (OD5) | none |
| 06 | 2026-11-11 21:03:42–21:04:56 | operator | `r11-fix1-create-01` executed once: `execute exit=0`; stack `CREATE_COMPLETE`, capabilities null, tag `project=proposal-orchestrator`. `Host` started 21:04:42 and completed 21:04:56; 24 events, none failed. Hourly charges run from 21:03:42 until step 13 | none. Files `R11_fix1_06_*`; run 1's `R11_06_*` kept |
| 07–12 | 2026-11-11, 21:05–21:09 | operator | Reported PASS by the operator. Agent spot check: host `i-03308c50670917059` `c7i-flex.large`, x86_64, eu-north-1a, no public IP; step 12 Converse from the host `converse_exit=0`, reply the fixed test string, Run Command `Success` (21:08:57) | Step 09: `R11_09_credit-specification.json` reports `CpuCredits` `standard` for the c7i-flex host although the template omits the option (OD9-r1 known gap 2, answered) |
| 13 | 2026-11-11, after 21:09 | operator | 13a: runtime role ARN and boundary equal `R5_outputs.json`; the four attached policies equal `R5_08_runtime-role-attached.json`, explicit deny included. 13b: `delete exit=0`; stack after: `ValidationError`, does not exist, `exit=254`. Hourly charges stopped at the delete (exact time not reported) | none. PowerShell wrapped the expected error in a `NativeCommandError` record |
| 14 | 2026-11-11, after 21:15 | operator | Only the S3 gateway endpoint `vpce-0770a3016be1317ef` (`available`); no network interface; instance `i-03308c50670917059` `terminated`; root volume `vol-08e9986a6f901c566` `InvalidVolume.NotFound`, `exit=254`. Base stacks and the 25 exports equal `R11_03_base-stacks.json` and `R11_03_exports.json` (by script). Imports: no list names the host stack; four exports not imported by any stack | **Sheet error, not a run error.** `STEPS.md` asked for all six exports to be unimported, but `network-VpcId` is imported by `-audit` and `iam-RuntimeRoleArn` by `-kms`, `-audit` and `-secret`, by design of the base templates. Criterion corrected in `STEPS_fix1.md` (step 14 row); PASS against it |
