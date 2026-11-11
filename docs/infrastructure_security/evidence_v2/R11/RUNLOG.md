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
| check | 2026-11-11 | agent | All 22 files PASS against `STEPS.md` (`utf-8-sig`, by script): the 25 export values equal the R4–R8 outputs files (7 network, 7 iam, 3 kms, 6 audit, 2 secret); `FoundationModelArns`, `InferenceProfileArns`, `ExpectedAccountId` and `ExpectedRegion` equal `deploy/aws/parameters/host.json`; `ProjectName` and `InstanceType` take the template defaults; the resolved AMI equals `R11_03_image.json`. Secret scan of this folder (AKIA, aws_secret, SecretString, SessionToken) and old-ID guard CLEAN | — |

**STOP — end of round 1.** Step 06 starts hourly charges. It runs only after the operator's explicit go
in session on `R11_05_change-set.json`, recorded below with its UTC time and the operator's words.

## Round 2 — steps 06–23

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| go | | operator | | |
