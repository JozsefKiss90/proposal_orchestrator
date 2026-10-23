# R3 — IaC skeleton and old-ID guard: step sheet

| Field | Value |
|---|---|
| Ticket | `R3` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R3, as read in `plans/aws_redeployment_r3_handoff_2026-10-22.md` §2 |
| Decisions applied | OD6-r3 (`aws-redeployment-od6-stack-layout-r3_2026-10-22`); OD1-r1 eu-north-1; OD4 one zone; OD7 model set; R1-D2 session-start check; OD10 Free plan, no upgrade |
| Written by / on | agent (Claude) / 2026-10-22 |
| Account / region | `797661577394` / `eu-north-1`; Free Tier, Budgets and STS are global |
| IDs taken from | none. R3 creates nothing and writes no `R3_outputs.json`. Steps 05 and 06 supply the values of `AvailabilityZone` and `S3PrefixListId` for `deploy/aws/parameters/network.json`. |
| Controls touched | none directly. Prepares DC-06 and PL-8 (R4) and the old-ID constraint of handoff §7. |
| Hourly cost created | **none**. Every AWS call below is read-only. |

## Before you start

- **Where commands run.** Everything runs in **PowerShell on the workstation, from the repository
  root** (`C:\Code\proposal_demo\proposal_orchestrator`), because step 08 needs the local template
  files. Sign in first with `aws login --profile po-r1`. Then the evidence lands straight in this
  folder, and no zip is needed. Every AWS command names `--profile po-r1`, and every regional command
  also names `--region eu-north-1`.
- CloudShell forms are given for the AWS steps except 08, in case the workstation sign-in fails. Use
  the **eu-north-1** CloudShell, in `~/R3`, and bring the files home by zip as in R2.
- In PowerShell, always pipe to `Out-File -Encoding utf8 <file>`, never use `>`. Set the folder
  variable once per PowerShell window:

  ```powershell
  $E = "docs\infrastructure_security\evidence_v2\R3"
  ```

- Never save secret values, access keys, session tokens or passwords. No step below prints any.
- Create nothing. Do not run any `create-*`, `deploy` or `execute-*` command in this ticket.
- If a step fails, stop, report the error in session, and do not improvise a fix.
- **Two rounds.** Run steps 01–10 and report. The agent then writes the zone and the prefix-list id
  from your evidence into `network.json`. After that, run steps 11–12.

---

## Steps

### Step 01 — Session-start check: credits, budget, alert states (R1-D2)

What it does: confirms that the Free plan is active, the credits are intact and no budget alert is in
`ALARM`, before anything else runs.

PowerShell:

```powershell
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query 'Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}' --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query 'Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}' --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_01_budget-notifications.json"
Get-Content "$E\R3_01_plan-state.json", "$E\R3_01_budgets.json", "$E\R3_01_budget-notifications.json"
```

CloudShell:

```bash
mkdir -p ~/R3 && cd ~/R3
aws freetier get-account-plan-state --output json > R3_01_plan-state.json 2>&1
aws budgets describe-budgets --account-id 797661577394 \
  --query 'Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}' \
  --output json > R3_01_budgets.json 2>&1
aws budgets describe-notifications-for-budget --account-id 797661577394 --budget-name "My Monthly Cost Budget" \
  --query 'Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}' \
  --output json > R3_01_budget-notifications.json 2>&1
cat R3_01_plan-state.json R3_01_budgets.json R3_01_budget-notifications.json
```

| Evidence file | PASS criterion |
|---|---|
| `R3_01_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `199.00` (R2 left 199.99); `accountPlanExpirationDate` starts `2027-04-19` |
| `R3_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` = `10.0`, `spend` < `8.5` |
| `R3_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` = `OK` |

**STOP rule.** If the plan is not `ACTIVE`, the credits are below 199.00 USD, or any notification is in
`ALARM`, stop here and report it.

### Step 02 — Who is calling

What it does: records that the CLI runs as the OD11-r2 identity in the right account.

PowerShell:

```powershell
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_02_caller-identity.json"
Get-Content "$E\R3_02_caller-identity.json"
```

CloudShell:

```bash
cd ~/R3 && aws sts get-caller-identity --output json > R3_02_caller-identity.json 2>&1 && cat R3_02_caller-identity.json
```

| Evidence file | PASS criterion |
|---|---|
| `R3_02_caller-identity.json` | `Account` = `797661577394`; `Arn` starts with `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

### Step 03 — Lint the templates (workstation only, no AWS call)

What it does: creates the lint virtual environment once, installs the pinned `cfn-lint`, and lints
all six templates for eu-north-1 (exit condition 1).

PowerShell:

```powershell
py -3.10 -m venv .venv-lint
.\.venv-lint\Scripts\python.exe -m pip install -r deploy\aws\requirements-lint.txt
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R3_03_cfn-lint.txt"
Get-Content "$E\R3_03_cfn-lint.txt"
```

The first two lines are needed only once. `.venv-lint\` is ignored by git.

| Evidence file | PASS criterion |
|---|---|
| `R3_03_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them (no error, warning or informational finding) |

### Step 04 — Availability zones of eu-north-1 (read-only)

What it does: lists the zones and their zone ids, so that the zone chosen in step 05 is recorded by
name and by id.

PowerShell:

```powershell
aws ec2 describe-availability-zones --profile po-r1 --region eu-north-1 --query "AvailabilityZones[].{name:ZoneName,id:ZoneId,state:State,optIn:OptInStatus,type:ZoneType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_04_availability-zones.json"
Get-Content "$E\R3_04_availability-zones.json"
```

CloudShell:

```bash
cd ~/R3 && aws ec2 describe-availability-zones --region eu-north-1 \
  --query 'AvailabilityZones[].{name:ZoneName,id:ZoneId,state:State,optIn:OptInStatus,type:ZoneType}' \
  --output json > R3_04_availability-zones.json 2>&1 && cat R3_04_availability-zones.json
```

| Evidence file | PASS criterion |
|---|---|
| `R3_04_availability-zones.json` | A non-empty list; every entry `type` = `availability-zone`; at least one entry `state` = `available` |

### Step 05 — Which zones offer all six interface endpoint services (read-only)

What it does: shows, for each service R11 needs, the zones where an interface endpoint can be
placed. OD4 puts every endpoint and the subnet in one zone, so that zone must offer all six.

PowerShell:

```powershell
$svc = "bedrock-runtime","sts","secretsmanager","ssm","ssmmessages","ec2messages" | ForEach-Object { "com.amazonaws.eu-north-1.$_" }
aws ec2 describe-vpc-endpoint-services --profile po-r1 --region eu-north-1 --service-names $svc --query "ServiceDetails[].{service:ServiceName,type:ServiceType[0].ServiceType,azs:AvailabilityZones,privateDns:PrivateDnsName}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_05_endpoint-services.json"
Get-Content "$E\R3_05_endpoint-services.json"
```

CloudShell:

```bash
cd ~/R3 && aws ec2 describe-vpc-endpoint-services --region eu-north-1 \
  --service-names $(for s in bedrock-runtime sts secretsmanager ssm ssmmessages ec2messages; do printf 'com.amazonaws.eu-north-1.%s ' "$s"; done) \
  --query 'ServiceDetails[].{service:ServiceName,type:ServiceType[0].ServiceType,azs:AvailabilityZones,privateDns:PrivateDnsName}' \
  --output json > R3_05_endpoint-services.json 2>&1 && cat R3_05_endpoint-services.json
```

| Evidence file | PASS criterion |
|---|---|
| `R3_05_endpoint-services.json` | Exactly six entries, one per service name above; each `type` = `Interface` and `privateDns` set; the intersection of their `azs` lists is non-empty. **The agent picks the first zone (in name order) of that intersection** as `AvailabilityZone` and records it in `VERIFICATION.md`. |

### Step 06 — The S3 prefix list of eu-north-1 (read-only)

What it does: finds the AWS-managed prefix list that the route table and the host security group
reference (R4).

PowerShell:

```powershell
aws ec2 describe-managed-prefix-lists --profile po-r1 --region eu-north-1 --filters Name=prefix-list-name,Values=com.amazonaws.eu-north-1.s3 --query "PrefixLists[].{id:PrefixListId,name:PrefixListName,owner:OwnerId,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_06_s3-prefix-list.json"
Get-Content "$E\R3_06_s3-prefix-list.json"
```

CloudShell:

```bash
cd ~/R3 && aws ec2 describe-managed-prefix-lists --region eu-north-1 \
  --filters Name=prefix-list-name,Values=com.amazonaws.eu-north-1.s3 \
  --query 'PrefixLists[].{id:PrefixListId,name:PrefixListName,owner:OwnerId,state:State}' \
  --output json > R3_06_s3-prefix-list.json 2>&1 && cat R3_06_s3-prefix-list.json
```

| Evidence file | PASS criterion |
|---|---|
| `R3_06_s3-prefix-list.json` | Exactly one entry: `name` = `com.amazonaws.eu-north-1.s3`, `owner` = `AWS`, `state` = `create-complete`, `id` starting `pl-`. The old-ID guard (step 11) confirms it is not the old account's us-east-1 list. |

### Step 07 — The AL2023 AMI public parameter is readable (read-only)

What it does: shows that the host template's `LatestAmiId` default can be resolved in eu-north-1
(R11).

PowerShell:

```powershell
aws ssm get-parameters --profile po-r1 --region eu-north-1 --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query "{found:Parameters[].{name:Name,type:Type,value:Value,modified:LastModifiedDate},invalid:InvalidParameters}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_07_al2023-ami-parameter.json"
Get-Content "$E\R3_07_al2023-ami-parameter.json"
```

CloudShell:

```bash
cd ~/R3 && aws ssm get-parameters --region eu-north-1 \
  --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query '{found:Parameters[].{name:Name,type:Type,value:Value,modified:LastModifiedDate},invalid:InvalidParameters}' \
  --output json > R3_07_al2023-ami-parameter.json 2>&1 && cat R3_07_al2023-ami-parameter.json
```

| Evidence file | PASS criterion |
|---|---|
| `R3_07_al2023-ami-parameter.json` | `found` has one entry with that `name`, `value` starting `ami-`; `invalid` is empty. An SCP denial or `AccessDenied` is a FAIL to report, not to work around. |

### Step 08 — CloudFormation reads each skeleton (read-only, workstation only)

What it does: `validate-template` on each of the six templates. It shows that the CloudFormation
service answers in eu-north-1, that no SCP refuses it, and that the service parses each skeleton. It
creates nothing.

PowerShell:

```powershell
$log = foreach ($t in "10-network","20-iam","30-kms","40-audit","50-secret","90-host") {
  $k = $t.Substring(3)
  aws cloudformation validate-template --profile po-r1 --region eu-north-1 --template-body "file://deploy/aws/templates/$t.yaml" --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_08_validate-$k.json"
  "$k exit=$LASTEXITCODE"
}
$log | Out-File -Encoding utf8 "$E\R3_08_validate-exit.txt"
Get-Content "$E\R3_08_validate-exit.txt"
```

There is no CloudShell form: the command needs the local template files. If the workstation sign-in
fails, report it, and the agent will give a zip-upload variant.

| Evidence file | PASS criterion |
|---|---|
| `R3_08_validate-exit.txt` | Six lines, `network`, `iam`, `kms`, `audit`, `secret`, `host`, each `exit=0` |
| `R3_08_validate-<stack>.json` (six files) | JSON with a `Parameters` list whose `ParameterKey` set equals the parameters the template declares; `Description` present; no `Capabilities` entry (skeletons create no IAM resource); no error text |

### Step 09 — Nothing was created (read-only)

What it does: shows that the account holds no CloudFormation stack and no export after R3.

PowerShell:

```powershell
aws cloudformation list-stacks --profile po-r1 --region eu-north-1 --query "StackSummaries[].{name:StackName,status:StackStatus}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_09_stacks.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_09_exports.json"
Get-Content "$E\R3_09_stacks.json", "$E\R3_09_exports.json"
```

CloudShell:

```bash
cd ~/R3
aws cloudformation list-stacks --region eu-north-1 --query 'StackSummaries[].{name:StackName,status:StackStatus}' --output json > R3_09_stacks.json 2>&1
aws cloudformation list-exports --region eu-north-1 --output json > R3_09_exports.json 2>&1
cat R3_09_stacks.json R3_09_exports.json
```

| Evidence file | PASS criterion |
|---|---|
| `R3_09_stacks.json` | `[]` |
| `R3_09_exports.json` | `Exports` is `[]` |

### Step 10 — Session-end credits (read-only)

What it does: confirms that R3 spent nothing.

PowerShell:

```powershell
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R3_10_plan-state-after.json"
Get-Content "$E\R3_10_plan-state-after.json"
```

CloudShell:

```bash
cd ~/R3 && aws freetier get-account-plan-state --output json > R3_10_plan-state-after.json 2>&1 && cat R3_10_plan-state-after.json
```

| Evidence file | PASS criterion |
|---|---|
| `R3_10_plan-state-after.json` | `FREE`, `ACTIVE`; `accountPlanRemainingCredits.amount` equal to step 01's |

**Hand back here.** Report steps 01–10 in session (CloudShell users: zip `~/R3`, download, and copy
the files into this folder first). The agent then writes `AvailabilityZone` (from step 05) and
`S3PrefixListId` (from step 06) into `deploy/aws/parameters/network.json` and tells you when to go on.

### Step 11 — Tests and guards (workstation only, no AWS call)

What it does: runs the three R3 test files with `py -3.10`, and both guards over the real tree (exit
conditions 1 to 3). Run it after the agent has filled `network.json`.

The E0 scaffold test is not run here. Its case
`test_register_v2_lists_all_41_controls_as_not_started` has failed since R2 legitimately set DC-36
to `IN_PROGRESS` (commit `690f90c`). That is a stale E0 criterion, not an R3 result, and it is
reported to the operator separately.

PowerShell:

```powershell
py -3.10 -m pytest tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_old_id_guard.py 2>&1 | Out-File -Encoding utf8 "$E\R3_11_pytest.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R3_11_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R3_11_old-id-guard.txt"
Get-Content "$E\R3_11_pytest.txt" -Tail 5; Get-Content "$E\R3_11_template-guard.txt", "$E\R3_11_old-id-guard.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R3_11_pytest.txt` | Header shows `Python 3.10`; last line `N passed` with no `failed`, `error` or `skipped` |
| `R3_11_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R3_11_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |

### Step 12 — Secret scan of this folder (workstation only)

What it does: the E0 refusal check over the R3 evidence before it is committed.

PowerShell:

```powershell
& { py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/R3; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R3_12_secret-scan.txt"
Get-Content "$E\R3_12_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R3_12_secret-scan.txt` | `CLEAN: docs/infrastructure_security/evidence_v2/R3`; `exit=0` |

## Outputs

R3 creates no resource and writes no `R3_outputs.json`. The output names every later ticket saves are
fixed in `deploy/aws/outputs_contract.json`.

## Before you hand back

- [ ] Every evidence file listed above exists in this folder, under exactly its name.
- [ ] You opened each file and checked that it holds no secret value, key or token.
- [ ] You reported each step in session (UTC time, any deviation, any error). The agent keeps
      `RUNLOG.md` from your reports.
