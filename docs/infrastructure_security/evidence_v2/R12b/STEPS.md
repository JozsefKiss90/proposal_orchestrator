# R12b — Full re-evidence and register v2: step sheet

| Field | Value |
|---|---|
| Ticket | `R12b` in `plans/aws_redeployment_tickets.md` |
| Handoff | `.scratch/overhaul-2026-11/handoff-session-2026-11-11.md` §6 A2; `plans/aws_redeployment_handoff_2026-10-21.md` §4 F7, §7a |
| Decisions applied | OD1-r1 eu-north-1; OD5 (the host stack lives one session); OD6-r3; OD7; OD9-r1 (`c7i-flex.large`); OD12 (DC-38 deferred); R12a-D3, D4, D5, D7, D16–D19, D26 (`aws-redeployment-r12a-collector_2026-10-28`); F-R12a-1, F-R12a-2, F-R12a-3; R11-D1–D12 (`aws-redeployment-r11-host_2026-11-11`); the operator's answers of 2026-11-12, points 1–3 below |
| Written by / on | agent (Claude) / 2026-11-12 |
| Account / region | `797661577394` / `eu-north-1`. The collector takes both from the parameter files and refuses any other caller account |
| IDs taken from | The collector: `deploy/aws/outputs_contract.json`, `R4_outputs.json`–`R8_outputs.json`, the parameter files, `deploy/aws/collector_inputs.json`; the host ids from `R12b_outputs.json` (step 07) through `--host-outputs`. The hand-run steps read the same files by path |
| Controls touched | Every register v2 row (ticket criterion 1). Collected live: all command checks of the R12a coverage map. Host checks: DC-02, DC-14, DC-15, DC-17, DC-31, DC-32, DC-37, F7. Document review: DC-39. Re-assessed: DC-40. Deferred: DC-33–DC-35 (point 1), DC-38 (OD12) |
| Hourly cost created | **Yes, from step 06 to step 10.** The R11 stack, once: six interface endpoints and one `c7i-flex.large` host with its gp3 root volume. Usage on top: Bedrock tokens of the collector's one Converse call (DC-37, max 10 output tokens), CloudWatch Logs ingestion of flow-log records, KMS and Secrets Manager requests. **No figure is quoted here: R14 prices each item.** The operator's go is recorded in `RUNLOG.md` (point 3). The stack is deleted in step 10 of the same session |

## Settled with the operator (2026-11-12)

1. **DC-33–DC-35 are deferred to R15.** The R9 launcher imports boto3. Amazon Linux 2023 has no boto3,
   and the host has no internet route. The O5 bundle, which carries the launcher and its libraries, does
   not exist yet. The collector runs without `--host-bundle-dir`, so it records the launcher check as
   "not collected". Register v2 marks the three rows `DEFERRED`, with R15 as the ticket that collects
   them.
2. **F7 uses a bucket in a second AWS account the operator controls.** The bucket is in `eu-north-1`,
   so the PUT travels the same route an exfiltration would, through the S3 gateway endpoint. A bucket
   in another Region would fail for lack of a route and prove nothing about the endpoint policy. The
   operator presigns a short-lived PUT URL there (step 05). The URL lives in one file outside the
   repository and reaches only the `send-command` parameters (R12a-D17). The evidence holds the HTTP
   status, the S3 error code and whether the message names a VPC endpoint policy. After the session the
   operator deletes the URL file and the outside bucket.
3. **The go.** The operator gave the go for R12b on 2026-11-11 at 22:58 UTC, before this sheet existed.
   It covers the one creation in step 06 once the operator has reviewed and merged this sheet. If the
   change set of step 04 differs from the seven additions below, or the cost picture changes, the agent
   asks again.

## Points the agent decided (the operator confirms or changes each on review)

4. **One creation, no recreation.** R11 proved the delete and the recreation twice. R12b creates the
   stack once and deletes it in step 10, right after the collector run.
5. **DC-26 timing (F-R12a-2).** The collector's own `lookup-events` runs seconds after its Converse call
   and may come back empty. Step 11 repeats the lookup in R11 step 20's metadata-only form, no earlier
   than 15 minutes after that call. It runs after the delete, so the wait adds no host-hours.
6. **The first real collector run (R12a known gaps D1, D4).** The collector has run only against a fake
   CLI, and its host scripts have not run on AL2023. If the collector refuses, or exits 1 on a check
   that is not a control failure (for example a quoting error of the real CLI on Windows), the operator
   stops, runs step 10 (delete) and hands back. The agent fixes the collector on a branch with a test.
   The run is not repeated by hand, and no file is edited.
7. **DC-40 re-assessment.** R1 step 00 showed the account is a member of an AWS-managed organization
   from the new sign-up experience, with the management account outside this project. The project
   cannot attach an SCP there. Unless the evidence says otherwise, the agent proposes `NOT_APPLICABLE`:
   no SCP is under the project's control, and Region enforcement rests on DC-16 (IAM condition) and
   DC-17 (the negative test from the host). The operator decides in session.
8. **DC-39 by document review.** No AWS command shows a data processing agreement. The agent reads the
   AWS Service Terms and records the clause that incorporates the AWS Data Processing Addendum, with
   its URL, its "Last Updated" date and the date read. The agent proposes a status; the operator
   decides in session.
9. **Register v2 (F-R12a-1).** The agent updates every row and the stale Summary table. Each row gets a
   v2 evidence path: the R12b collector folder where the run re-collected it, an earlier ticket's
   folder where that stays the evidence (for example DC-36's R2 part), or the reason it is deferred or
   not applicable.

## Before you start

- **Sign in with `aws login --profile po-r1`**, never bare `aws login`. Step 05 alone uses the second
  account's own profile (`<outside-profile>` below).
- **Where commands run.** PowerShell in the VS Code terminal, repository root. Every AWS command of this
  account names `--profile po-r1`. The collector runs on the workstation only. CloudShell has no
  repository, so this sheet gives no CloudShell form.
- **`$E` and `$V2` must be set in every new PowerShell window.** Every block below starts with them.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command.
- **Paste each block whole.** A paste cut inside `{ … }` leaves PowerShell at `>>` and nothing runs
  (R11 step 23). Press Ctrl+C and paste the block again.
- **Never save** secret values, access keys, session tokens, passwords, the IMDS token, instance
  credentials, the F7 URL, prompt or proposal text, or model output other than the fixed test string
  `DEPLOY_OK`. The collector writes none of them; its secret scan refuses a folder that holds one.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or `0.0.0.0/0` egress rule, not even temporarily.
  Bedrock model invocation logging stays disabled.
- If a step fails, stop, report the error in session, and do not improvise a fix. **If the host stack
  exists when you stop, run step 10 unless the agent asks you to keep it for diagnosis. It costs by the
  hour.**
- **Rounds.**
  - **Round 1: steps 01–04** (session check, read-only lookups, workstation checks, change set).
    Nothing billable. Hand back; the agent checks the change set by script.
  - **Round 2: steps 05–11**, in one sitting, once the agent has confirmed round 1. The stack costs from
    step 06 to step 10. Step 11 runs no earlier than 15 minutes after the collector's Converse call.
  - **Round 3: step 12** after the agent has written `VERIFICATION.md`, the register v2 rows and the
    worklog entry.

---

## Steps

### Step 01 — Session-start check and identity (R1-D2)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"; $V2 = "docs\infrastructure_security\evidence_v2"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_01_budget-notifications.json"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_01_caller-identity.json"
Get-ChildItem "$E\R12b_01_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_01_plan-state.json` | `accountPlanType` `FREE`; `accountPlanStatus` `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `190.00`; `accountPlanExpirationDate` starts `2027-04-19` |
| `R12b_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` `10.0`, `spend` < `8.5` |
| `R12b_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` `OK` |
| `R12b_01_caller-identity.json` | `Account` `797661577394`; `Arn` starts `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Plan not `ACTIVE`, credits below 190.00 USD, a notification in `ALARM`, or another account:
stop and report. R11's usage may only now reach the credits (billing is delayed); report the figure
whatever it is.

### Step 02 — Read-only lookups (nothing is created)

Confirms that R11 left nothing behind and that the base stacks and exports are as R11 step 03 recorded.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$VPC = O "$V2\R4\R4_outputs.json" VpcId
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_02_host-stack-before.txt"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_02_vpc-endpoints-before.json"
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_02_network-interfaces-before.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query "Reservations[].Instances[].{id:InstanceId,state:State.Name}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_02_instances-before.json"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_02_base-stacks.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-')].{name:Name,value:Value}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_02_exports.json"
Get-ChildItem "$E\R12b_02_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_02_host-stack-before.txt` | Contains `ValidationError` and `does not exist`; last line `exit=254` |
| `R12b_02_vpc-endpoints-before.json` | Exactly one entry: the S3 gateway endpoint of `R4_outputs.json`, `available` |
| `R12b_02_network-interfaces-before.json` | `[]` |
| `R12b_02_instances-before.json` | `[]` |
| `R12b_02_base-stacks.json` | Equal to `R11_03_base-stacks.json` |
| `R12b_02_exports.json` | Equal to `R11_03_exports.json` (25 names) |

**STOP rule.** Any difference: stop and report.

### Step 03 — Workstation checks and the collector plan (no AWS call)

Run `deactivate` first if `.venv-lint` is active. The plan prints every command the collector would
run. It calls nothing and writes no folder.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_03_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_03_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_03_old-id-guard.txt"
$T = "tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_aws_env_config_template.py tests/test_aws_host_template.py tests/test_old_id_guard.py tests/test_host_env_launcher.py tests/tools/test_collect_evidence_v2.py".Split(" ")
& { py -3.10 --version; py -3.10 -m pytest -q @T } 2>&1 | Out-File -Encoding utf8 "$E\R12b_03_pytest.txt"
& { py -3.10 -m tools.collect_evidence_v2 --ticket R12b --step 09 --profile po-r1 --plan; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_03_collector-plan.txt"
Get-Content "$E\R12b_03_cfn-lint.txt", "$E\R12b_03_template-guard.txt", "$E\R12b_03_old-id-guard.txt"; Get-Content "$E\R12b_03_pytest.txt" -Tail 1; Get-Content "$E\R12b_03_collector-plan.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_03_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R12b_03_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R12b_03_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R12b_03_pytest.txt` | First line `Python 3.10.…`; last line `324 passed, 1 skipped` (the agent's run on 2026-11-12); the skip is the Windows symlink case of R12a-D6 |
| `R12b_03_collector-plan.txt` | Last line `exit=0`; every command names `--profile po-r1`; the host checks read `not collected: host stack outputs absent (--host-outputs)`; no `get-secret-value`. The agent compares the ids with the outputs files by script |

**STOP rule.** Any non-zero exit or failed test: stop.

### Step 04 — Create the change set (nothing is created yet)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r12b-create-01 --change-set-type CREATE --template-body file://deploy/aws/templates/90-host.yaml --parameters file://deploy/aws/parameters/host.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_04_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r12b-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r12b-create-01 --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_04_change-set.json"
Get-Content "$E\R12b_04_create-change-set.json", "$E\R12b_04_change-set.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_04_create-change-set.json` | `Id` contains `changeSet/r12b-create-01/`; `StackId` contains `stack/proposal-orchestrator-host/` |
| `R12b_04_change-set.json` | As `R11_fix1_05_change-set.json`: `CREATE_COMPLETE`, `AVAILABLE`, no capabilities, tag `project`; parameters equal `host.json` or the template defaults, `InstanceType` `c7i-flex.large`; `LatestAmiId` resolved (a newer image than R11's is allowed; the agent records it); exactly seven `Add` changes: the six endpoints and `Host` |

**STOP — hand back here (end of round 1).** The agent checks steps 01–04 by script and confirms in
session. Step 06 then runs under the go of point 3. A stale change set is removed with
`aws cloudformation delete-stack --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host`
(a stack in `REVIEW_IN_PROGRESS` holds no resource).

---

### Step 05 — F7: the presigned PUT URL in the second account (no file in the repository)

Run this just before step 06, so the URL is still valid when the collector runs in step 09. Use the
second account's own profile. Choose a bucket name that does not name this project or either account.
Nothing from this step is saved in the repository, and nothing is pasted into the session.

```powershell
$OP = "<outside-profile>"; $OB = "<outside-bucket-name>"
aws s3api create-bucket --profile $OP --region eu-north-1 --bucket $OB --create-bucket-configuration LocationConstraint=eu-north-1 --output json | Out-Null
$F7 = Join-Path $env:USERPROFILE "po-f7-url.txt"
py -3.10 -c "import boto3,sys; from botocore.config import Config; s=boto3.Session(profile_name=sys.argv[1]).client('s3', region_name='eu-north-1', config=Config(signature_version='s3v4', s3={'addressing_style':'virtual'})); print(s.generate_presigned_url('put_object', Params={'Bucket': sys.argv[2], 'Key': 'f7-negative-test.txt'}, ExpiresIn=7200))" $OP $OB | Out-File -Encoding ascii $F7
$u = (Get-Content $F7 -Raw).Trim(); "starts_https=$($u.StartsWith('https://'))  names_eu_north_1=$($u.Contains('.s3.eu-north-1.amazonaws.com/'))  length=$($u.Length)"; $u = $null
```

| Check (shown on screen, not saved) | PASS criterion |
|---|---|
| The last line | `starts_https=True  names_eu_north_1=True` and a length over 200 |

Write in `RUNLOG.md` only that step 05 ran and passed this check. If `names_eu_north_1` is `False`, stop:
a URL on the global S3 host does not test the gateway endpoint the same way.

### Step 06 — Execute the change set (hourly charges start)

**Only after the agent has confirmed round 1.** Write the start time (UTC) in `RUNLOG.md`. Run the
block **once**.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
& { aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r12b-create-01; "execute exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_06_execute-exit.txt"
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_06_stack-status.json"
aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_06_stack-events.json"
Get-Content "$E\R12b_06_execute-exit.txt", "$E\R12b_06_stack-status.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_06_execute-exit.txt` | `execute exit=0` and no error line |
| `R12b_06_stack-status.json` | `status` `CREATE_COMPLETE`; `capabilities` null or `[]`; tag `project` = `proposal-orchestrator` |
| `R12b_06_stack-events.json` | The seven logical ids and the stack each reach `CREATE_COMPLETE`; no `*_FAILED`, no `ROLLBACK` |

**STOP rule.** On a rollback: report the first failed event's `reason`, delete the stack (step 10's
first two lines) and hand back.

### Step 07 — Save the stack outputs

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_outputs.json"
Get-Content "$E\R12b_outputs.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_outputs.json` | Exactly the seven contract keys, none with an `ExportName`: six `…EndpointId` values starting `vpce-`, all different, and `InstanceId` starting `i-`; every value differs from `R11_outputs.json` and `R11_17_outputs-recreated.json` |

### Step 08 — Wait until the host is `Online` in SSM

The collector's host checks need the SSM Agent registered. This step only waits and records.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$I = O "$E\R12b_outputs.json" InstanceId; "InstanceId=$I"
for ($n = 0; $n -lt 30; $n++) { $s = aws ssm describe-instance-information --profile po-r1 --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query "InstanceInformationList[0].PingStatus" --output text; "try $n : $s"; if ($s -eq "Online") { break }; Start-Sleep -Seconds 20 }
aws ssm describe-instance-information --profile po-r1 --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query "InstanceInformationList[].{id:InstanceId,ping:PingStatus,platform:PlatformName,version:PlatformVersion,agent:AgentVersion,resourceType:ResourceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_08_instance-information.json"
Get-Content "$E\R12b_08_instance-information.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_08_instance-information.json` | One entry: `id` = `InstanceId`, `ping` `Online`, `platform` `Amazon Linux`, `version` starts `2023`, `resourceType` `EC2Instance` |

**STOP rule.** Not `Online` after 30 tries (10 minutes): report, run step 10, hand back.

### Step 09 — The collector run (every command check and every host check)

Writes the new folder `R12b\R12b_09_collector\`, which must not exist yet. The collector first compares
the caller's account and every stack's live outputs with the files, and refuses on a difference. It
then runs the read-only checks, sends the fixed host scripts through Run Command, writes `summary.json`
and `MANIFEST.sha256`, and runs the secret scan and the old-ID guard over the folder. The console log
(`R12b_09_collector-console.txt`) holds no URL: the collector masks it.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
$F7 = Join-Path $env:USERPROFILE "po-f7-url.txt"
& { py -3.10 -m tools.collect_evidence_v2 --ticket R12b --step 09 --profile po-r1 --host-outputs "$E\R12b_outputs.json" --f7-url-file $F7; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_09_collector-console.txt"
Get-Content "$E\R12b_09_collector-console.txt" -Tail 15
```

| Evidence | PASS criterion |
|---|---|
| `R12b_09_collector-console.txt` | Last line `exit=0`; a `summary:` line with `error 0`; no `REFUSED`, `SECRET SCAN` or `OLD-ID GUARD` line |
| `R12b_09_collector/summary.json` | `account` `797661577394`, `region` `eu-north-1`, `host_stack` `present`; every control `collected`, `partial` or `non_command`; `not_collected` only for the launcher check (point 1) |
| `R12b_09_collector/MANIFEST.sha256` | One line per file of the folder; the agent re-hashes them |
| Host checks (agent, by script) | Each host file: `Status` `Success` and `RESULT=expected`. In particular: DC-15 no long-term key variable or file; DC-17 the call to `us-east-1` fails; DC-31 no `claude` binary; DC-32 both probes fail; DC-37 (`DC-37_converse.json`) `reply_equals_test_string=yes` and `caller_arn` the runtime role; F7 (`DC-05_f7-presigned-put.json`) `http_status` `403`, `error_code` `AccessDenied`, `message_names_vpc_endpoint_policy` `yes` (**closes F7**) |

**STOP rule.** Exit 1 or a refusal: report the last 15 lines, run step 10, hand back (point 6). Do not
re-run the collector and do not edit the folder. An F7 result of `http_status=000` (no answer) is not a
pass: report it.

### Step 10 — Delete the stack (end of the billable window, OD5)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
& { aws cloudformation delete-stack --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host; "delete exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_10_delete-exit.txt"
aws cloudformation wait stack-delete-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_10_host-stack-after.txt"
$VPC = O "$V2\R4\R4_outputs.json" VpcId
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_10_network-interfaces-after.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query "Reservations[].Instances[].{id:InstanceId,state:State.Name}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_10_instances-after.json"
aws ec2 describe-volumes --profile po-r1 --region eu-north-1 --filters Name=tag:project,Values=proposal-orchestrator --query "Volumes[].{id:VolumeId,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_10_volumes-after.json"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_10_base-stacks.json"
Get-ChildItem "$E\R12b_10_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_10_delete-exit.txt` | `delete exit=0` |
| `R12b_10_host-stack-after.txt` | Contains `ValidationError` and `does not exist`; last line `exit=254` |
| `R12b_10_network-interfaces-after.json` | `[]` (repeat the line after a few minutes if endpoint ENIs linger) |
| `R12b_10_instances-after.json` | `[]` |
| `R12b_10_volumes-after.json` | `[]` |
| `R12b_10_base-stacks.json` | Equal to `R12b_02_base-stacks.json` |

Write the delete time (UTC) in `RUNLOG.md`. From here nothing billable by the hour exists.

### Step 11 — CloudTrail: the collector's Converse event, metadata only (DC-26, F-R12a-2)

**Run no earlier than 15 minutes after `finished_utc` in `R12b_09_collector\summary.json`.** The DC-37 host script prints no call time, so the lookup starts at the run's `started_utc`. Same form as R11
step 20: 11a writes lookup metadata only; 11b parses each event in memory and writes selected fields.
Then remove the F7 URL file and the outside bucket.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
$sum = Get-Content "$E\R12b_09_collector\summary.json" -Raw | ConvertFrom-Json
$CALL = $sum.started_utc; "started_utc=$CALL finished_utc=$($sum.finished_utc)"
aws cloudtrail lookup-events --profile po-r1 --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=Converse --start-time $CALL --max-results 20 --query "Events[].{id:EventId,name:EventName,time:EventTime,source:EventSource,user:Username}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_11_converse-lookup.json"
$raw = aws cloudtrail lookup-events --profile po-r1 --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=Converse --start-time $CALL --max-results 20 --query "Events[].CloudTrailEvent" --output json
$sel = @(($raw | Out-String | ConvertFrom-Json) | ForEach-Object {
  $ev = $_ | ConvertFrom-Json
  [ordered]@{
    eventId = $ev.eventID; eventTime = $ev.eventTime; eventSource = $ev.eventSource; eventName = $ev.eventName
    awsRegion = $ev.awsRegion; userIdentityType = $ev.userIdentity.type; callerArn = $ev.userIdentity.arn
    sessionIssuerArn = $ev.userIdentity.sessionContext.sessionIssuer.arn; vpcEndpointId = $ev.vpcEndpointId
    modelId = $ev.requestParameters.modelId
    requestParameterNames = $(if ($ev.requestParameters) { @($ev.requestParameters.PSObject.Properties.Name) } else { @() })
    responseElementsNull = ($null -eq $ev.responseElements); errorCode = $ev.errorCode
  } })
ConvertTo-Json -InputObject $sel -Depth 4 | Out-File -Encoding utf8 "$E\R12b_11_converse-events.json"
$raw = $null; $sel = $null
Get-Content "$E\R12b_11_converse-lookup.json", "$E\R12b_11_converse-events.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_11_converse-lookup.json` | At least one `Converse` event from `bedrock.amazonaws.com` between `started_utc` and `finished_utc`; `user` = `InstanceId` of `R12b_outputs.json` |
| `R12b_11_converse-events.json` | Exactly one entry between `started_utc` and `finished_utc` (the collector makes one call to eu-north-1; the DC-17 call to `us-east-1` has no route and is not expected here): `awsRegion` `eu-north-1`, `userIdentityType` `AssumedRole`, `callerArn` = `arn:aws:sts::797661577394:assumed-role/proposal-orchestrator-runtime-role/<InstanceId>`, `sessionIssuerArn` = `RuntimeRoleArn` of `R5_outputs.json`, `vpcEndpointId` = `BedrockRuntimeEndpointId` of `R12b_outputs.json`, `errorCode` null; only the fields listed in the command |

**STOP rule.** No event after 30 minutes: repeat once (overwriting); still none is a DC-26 FAIL to report.

Then, with the second account's profile (nothing saved; write only "done" in `RUNLOG.md`):

```powershell
$OP = "<outside-profile>"; $OB = "<outside-bucket-name>"
Remove-Item (Join-Path $env:USERPROFILE "po-f7-url.txt")
aws s3 rb "s3://$OB" --profile $OP --region eu-north-1 --force
```

### Step 12 — Closing: tests, old-ID guard, then the secret scan over the finished folder

Runs only after the agent has written `VERIFICATION.md`, the register v2 rows and the worklog entry.
Run `deactivate` first if `.venv-lint` is active. Paste the three lines one at a time if in doubt. The
scan runs last.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
$T = "tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_aws_env_config_template.py tests/test_aws_host_template.py tests/test_old_id_guard.py tests/test_host_env_launcher.py tests/tools/test_collect_evidence_v2.py tests/test_evidence_protocol_scaffold.py".Split(" ")
& { py -3.10 --version; py -3.10 -m pytest -q @T } 2>&1 | Out-File -Encoding utf8 "$E\R12b_12_pytest.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_12_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_12_secret-scan.txt"
Get-Content "$E\R12b_12_pytest.txt" -Tail 1; Get-Content "$E\R12b_12_old-id-guard.txt", "$E\R12b_12_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_12_pytest.txt` | First line `Python 3.10.…`; last line the count the agent states with `VERIFICATION.md`, no `failed` or `error`; the one skip is the symlink case |
| `R12b_12_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R12b_12_secret-scan.txt` | `CLEAN: docs\infrastructure_security\evidence_v2\R12b` (or with forward slashes); `exit=0` |

Then commit (operator), and confirm R12b in session; the agent ticks R12b in
`plans/aws_redeployment_tickets.md`.

## Before you hand back

- [ ] Every evidence file listed above exists in this folder, under exactly its name.
- [ ] `RUNLOG.md` records the UTC times, the create and delete times, any deviation and any error.
- [ ] `proposal-orchestrator-host` does not exist (`R12b_10_host-stack-after.txt`).
- [ ] The F7 URL file and the outside bucket are gone (step 11).
