# R5 — IAM stack: the hardened role is the runtime role: step sheet

| Field | Value |
|---|---|
| Ticket | `R5` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R5, as read in `plans/aws_redeployment_r5_handoff_2026-10-24.md` §3 |
| Decisions applied | OD2 (a) one hardened host role; OD7 (`OD7-resources`, `OD7-global`: `global.` denied); OD1-r1 eu-north-1; OD6-r3 (stacks, change sets, guards); R4-D3 (endpoint policy: read-only on the deploy bucket); R1-D2 session-start check; OD10 Free plan, no upgrade. The operator's answers of 2026-10-25 to the R5 handoff §4 points ("1-9 a"), recorded in `aws-redeployment-r5-iam_2026-10-25` (R5-D1 to R5-D9) |
| Written by / on | agent (Claude) / 2026-10-25 |
| Account / region | `797661577394` / `eu-north-1`. **IAM is global:** every `aws iam` command runs **without** `--region`; the stack itself is created in eu-north-1 (every `cloudformation` and `bedrock` command names `--region eu-north-1`) |
| IDs taken from | Round 1: none (lookups only). From step 06 on: `R5_outputs.json`. Model ARNs: `deploy/aws/parameters/iam.json` (tied to OD7 by `tests/test_aws_iac_contract.py`); a `global.` profile ARN from `evidence_v2/R2/R2_03_profiles.json`; a non-Claude model ARN from `R5_03_non-claude-models.json` (step 03) |
| Controls touched | DC-09 (role and profile; "the host uses it" is R11, DC-14), DC-10, DC-11, DC-12, DC-13, DC-16 (condition in place; negative test is R12b, DC-17) |
| Hourly cost created | **none**. IAM roles, policies and instance profiles are free. The change set (step 05) is still read before it is executed. |

## Before you start

- **Sign in with `aws login --profile po-r1`**, never bare `aws login` (the bare form offers to
  overwrite the `default` profile; decline if it ever asks).
- **Where commands run.** PowerShell in the VS Code terminal, repository root
  (`C:\Code\proposal_demo\proposal_orchestrator`). Every AWS command names `--profile po-r1`.
  CloudShell is the fallback only (end of this sheet).
- **`$E` must be set in every new PowerShell window.** Every block below starts with it.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command.
- Pasted terminal output can lose spaces when it wraps (R4: `--outputjson`). The agent verifies from
  the files in this folder, not from the paste.
- Never save secret values, access keys, session tokens or passwords. No step below prints any.
- If a step fails, stop, report the error in session, and do not improvise a fix.
- **Rounds.**
  - **Round 1 (this sheet now): steps 01–03**, read-only. Hand back. The agent then copies the SSM
    Agent's actions from `R5_03_ssm-core-policy.json`, fills `deploy/aws/templates/20-iam.yaml`,
    extends the template guard, writes `tests/test_aws_iam_template.py` and the decision record, and
    adds steps 04–05 to this sheet.
  - **Round 1b: steps 04–05** (lint, guards, tests, change set). Hand back; both read the change set.
  - **Round 2: steps 06–10** (execute, outputs, read-only evidence, IAM simulation, credits).
  - **Round 3: step 11** (scan and guards over the finished folder, tests, commit).

---

## Steps

### Step 01 — Session-start check: credits, budget, alert states (R1-D2)

What it does: confirms that the Free plan is active, the credits are intact and no budget alert is in
`ALARM`, before anything else runs.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_01_budget-notifications.json"
Get-Content "$E\R5_01_plan-state.json", "$E\R5_01_budgets.json", "$E\R5_01_budget-notifications.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R5_01_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `199.00` (R4 left 199.99); `accountPlanExpirationDate` starts `2027-04-19` |
| `R5_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` = `10.0`, `spend` < `8.5` |
| `R5_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` = `OK` |

**STOP rule.** If the plan is not `ACTIVE`, the credits are below 199.00 USD, or any notification is in
`ALARM`, stop here and report it.

### Step 02 — Who is calling

What it does: records that the CLI runs as the OD11-r2 identity in the right account.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_02_caller-identity.json"
Get-Content "$E\R5_02_caller-identity.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R5_02_caller-identity.json` | `Account` = `797661577394`; `Arn` starts with `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Any other account: stop. Nothing below may run.

### Step 03 — Read-only lookups (nothing is created)

What it does: collects, before the template is written, the facts it is written from (handoff §7a:
from evidence, not memory):

- **03a** the current default version of the AWS managed policy `AmazonSSMManagedInstanceCore`. Its
  action list is copied verbatim into the permission boundary and the supporting-services policy
  (decision point 7 (a): full list, not trimmed, not attached as a managed policy);
- **03b** the account's customer-managed (local) policies, roles and instance profiles **before** R5:
  nothing named `proposal-orchestrator-*`, "temporary" or "validation" may exist (exit condition 4),
  and the fixed names R5 uses must be free;
- **03c** a real non-Claude foundation-model ARN in eu-north-1, for the step 09 deny case (R1 lesson:
  real ids, not placeholders);
- **03d** that the `proposal-orchestrator-iam` stack does not exist yet.

PowerShell (IAM commands without `--region`; the second line reads the version id the first file names):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
# 03a — AmazonSSMManagedInstanceCore, metadata and default version document
aws iam get-policy --profile po-r1 --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_03_ssm-core-policy-meta.json"
$V = aws iam get-policy --profile po-r1 --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore --query "Policy.DefaultVersionId" --output text
"DefaultVersionId=$V"
aws iam get-policy-version --profile po-r1 --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore --version-id $V --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_03_ssm-core-policy.json"
# 03b — what exists in IAM before R5
aws iam list-policies --profile po-r1 --scope Local --query "Policies[].{name:PolicyName,path:Path,arn:Arn,attachments:AttachmentCount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_03_local-policies-before.json"
aws iam list-roles --profile po-r1 --query "Roles[].{name:RoleName,path:Path,arn:Arn,created:CreateDate}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_03_roles-before.json"
aws iam list-instance-profiles --profile po-r1 --query "InstanceProfiles[].{name:InstanceProfileName,path:Path,roles:Roles[].RoleName}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_03_instance-profiles-before.json"
# 03c — non-Claude foundation models in eu-north-1 (Amazon's own), ids and ARNs only
aws bedrock list-foundation-models --profile po-r1 --region eu-north-1 --by-provider amazon --query "modelSummaries[].{id:modelId,arn:modelArn}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_03_non-claude-models.json"
# 03d — the IAM stack must not exist yet (an error here is the expected result)
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_03_iam-stack-before.txt"
Get-Content "$E\R5_03_ssm-core-policy-meta.json", "$E\R5_03_local-policies-before.json", "$E\R5_03_roles-before.json", "$E\R5_03_instance-profiles-before.json", "$E\R5_03_iam-stack-before.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R5_03_ssm-core-policy-meta.json` | `Policy.Arn` = `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore`; `Policy.DefaultVersionId` present (the agent records it in the decision record) |
| `R5_03_ssm-core-policy.json` | `PolicyVersion.IsDefaultVersion` = `true`; `PolicyVersion.VersionId` = the `DefaultVersionId` above; `PolicyVersion.Document.Statement` holds the `Allow` statements with `ssm:*`, `ssmmessages:*` and `ec2messages:*` actions. The agent copies the action list from this file and from nowhere else. |
| `R5_03_local-policies-before.json` | `[]`: no customer-managed policy exists, so none carries "temporary" or "validation" and the six R5 policy names are free |
| `R5_03_roles-before.json` | No role whose name contains `proposal-orchestrator`, `temporar` or `validation`. Expected: `AccountFullAccessRole` under `/managed/` and AWS service-linked roles under `/aws-service-role/`. Any other role is **not** a FAIL by itself: report it in session and we decide (it may be an Explore AWS leftover R1 did not cover). |
| `R5_03_instance-profiles-before.json` | `[]` (so `proposal-orchestrator-runtime-profile` is free) |
| `R5_03_non-claude-models.json` | At least one entry; every `arn` starts `arn:aws:bedrock:eu-north-1::foundation-model/` and no `id` starts `anthropic.` |
| `R5_03_iam-stack-before.txt` | Contains `ValidationError` and `does not exist` for the stack `proposal-orchestrator-iam` (PowerShell may wrap the name across two lines); last line `exit=254` |

*Correction 2026-10-25, after round 1 (agent):* this criterion first said `exit=255` and quoted the error on one line. The AWS CLI v2 returns 254 when the service answers with an error, and PowerShell wraps the error text at the console width inside the file. The criterion is corrected; the evidence is unchanged (decision record `aws-redeployment-r5-iam_2026-10-25`, F-R5-5).

**STOP rule.** If `R5_03_local-policies-before.json` is not `[]`, `R5_03_instance-profiles-before.json`
is not `[]`, a `proposal-orchestrator-*` role exists, or the IAM stack exists: stop and report. The
template is not written over an occupied name. If only 03a fails (e.g. a policy read is refused),
report it; the SSM action list is not taken from memory instead.

**Hand back here (end of round 1).** Report steps 01–03 in session. The agent checks every file in the
device shell (criteria, secret scan, old-ID guard), then writes the template, the guard extension, the
R5 test, the decision record `aws-redeployment-r5-iam_2026-10-25`, and steps 04–05 below. *(Done 2026-10-25.)*

### Step 04 — Lint, guards and tests on the filled template (workstation only, no AWS call)

What it does: proves, before anything is created, that `20-iam.yaml` lints for eu-north-1, keeps the
template rules (tags where a type takes them, no literals, no "temporary"/"validation"), carries no
old-account id, and has the shape `tests/test_aws_iam_template.py` pins (decision record
`aws-redeployment-r5-iam_2026-10-25`, R5-D1 to R5-D8). Run `deactivate` first if `.venv-lint` is active
(lint still runs through its own executable).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_04_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_04_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_04_old-id-guard.txt"
py -3.10 -m pytest tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_old_id_guard.py 2>&1 | Out-File -Encoding utf8 "$E\R5_04_pytest.txt"
Get-Content "$E\R5_04_cfn-lint.txt", "$E\R5_04_template-guard.txt", "$E\R5_04_old-id-guard.txt"; Get-Content "$E\R5_04_pytest.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R5_04_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R5_04_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R5_04_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R5_04_pytest.txt` | Header shows `Python 3.10`; last line `146 passed` (the agent's run under Python 3.10.12) with no `failed`, `error` or `skipped` |

**STOP rule.** Any non-zero exit or failed test: stop. The template is not deployed until this step is
clean.

### Step 05 — Create the change set with `CAPABILITY_NAMED_IAM` and read it (nothing is created yet)

What it does: asks CloudFormation to plan the IAM stack. A change set of type CREATE builds nothing
until it is executed. `CAPABILITY_NAMED_IAM` is required because every role, profile and policy has a
fixed name (R5-D5); it acknowledges that, it grants nothing by itself.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam --change-set-name r5-create-01 --change-set-type CREATE --template-body file://deploy/aws/templates/20-iam.yaml --parameters file://deploy/aws/parameters/iam.json --capabilities CAPABILITY_NAMED_IAM --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_05_create-change-set.json"
Get-Content "$E\R5_05_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam --change-set-name r5-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam --change-set-name r5-create-01 --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_05_change-set.json"
Get-Content "$E\R5_05_change-set.json"
```

If `create-change-set` itself returns an error, or `wait` reports a terminal failure, still run the
`describe-change-set` line: `Status` and `StatusReason` in `R5_05_change-set.json` are the evidence.
Then stop and hand back.

| Evidence file | PASS criterion |
|---|---|
| `R5_05_create-change-set.json` | `Id` starts `arn:aws:cloudformation:eu-north-1:797661577394:changeSet/r5-create-01/`; `StackId` starts `arn:aws:cloudformation:eu-north-1:797661577394:stack/proposal-orchestrator-iam/` |
| `R5_05_change-set.json` | `Status` = `CREATE_COMPLETE`; `ExecutionStatus` = `AVAILABLE`; `Capabilities` = `["CAPABILITY_NAMED_IAM"]`; `Tags` = `[{project: proposal-orchestrator}]`; `Parameters` show `ExpectedAccountId` 797661577394, `ExpectedRegion` eu-north-1, `ProjectName` proposal-orchestrator, `InferenceProfileArns` (2 ARNs), `FoundationModelArns` (12 ARNs) and `RoutedRegions` (6 Regions) exactly as in `deploy/aws/parameters/iam.json`; `Changes` holds **exactly nine** entries, each `ResourceChange.Action` = `Add`, with these `LogicalResourceId` / `ResourceType` pairs and nothing else: `PermissionBoundary`, `BedrockInvokePolicy`, `ExplicitDenyPolicy`, `SupportingServicesPolicy`, `DeployBucketReadPolicy`, `FlowLogsWritePolicy` (each AWS::IAM::ManagedPolicy), `RuntimeRole` and `FlowLogsRole` (AWS::IAM::Role), `RuntimeInstanceProfile` (AWS::IAM::InstanceProfile). No other resource type; nothing with an hourly cost. |

*Correction 2026-10-25, after round 1b (agent):* this criterion first also asked for `ChangeSetType` = `CREATE`. `describe-change-set` does not return that field (nor did it in R4, `R4_04_change-set.json`); the CREATE type is evidenced by the command line (`--change-set-type CREATE`), by `R5_03_iam-stack-before.txt` (no stack before) and by nine `Add` entries. The criterion is corrected; the evidence is unchanged.

**Hand back here (end of round 1b).** Report steps 04–05 in session. Both of us read
`R5_05_change-set.json` against the criterion. Step 06 runs only after you have confirmed in session
that the change set lists exactly those nine resources. If the change set failed, the agent records the
error verbatim in `RUNLOG.md` and the successor decision is settled before the template changes;
nothing is executed.

### Step 06 — Execute the change set (creates the stack; no hourly cost)

**Only after the operator's go in session on `R5_05_change-set.json`.** What it does: creates the nine
IAM resources of the change set, and nothing else.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
& { aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam --change-set-name r5-create-01; "execute exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_06_execute-exit.txt"
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_06_stack-status.json"
aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_06_stack-events.json"
Get-Content "$E\R5_06_execute-exit.txt", "$E\R5_06_stack-status.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R5_06_execute-exit.txt` | `execute exit=0` and no error line |
| `R5_06_stack-status.json` | `status` = `CREATE_COMPLETE`; `capabilities` = `["CAPABILITY_NAMED_IAM"]`; `tags` hold `project` = `proposal-orchestrator` |
| `R5_06_stack-events.json` | Each of the nine logical ids and the stack reach `CREATE_COMPLETE`; no `*_FAILED` and no `ROLLBACK` status anywhere |

**STOP rule.** On a rollback or any `*_FAILED` event: stop, do not delete the stack, report it.

### Step 07 — Save the stack outputs (ids for every later step and ticket)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-iam --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_outputs.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-iam-')]" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_07_exports.json"
Get-Content "$E\R5_outputs.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R5_outputs.json` | Exactly the seven contract keys (`RuntimeRoleName`, `RuntimeRoleArn`, `InstanceProfileName`, `InstanceProfileArn`, `PermissionBoundaryArn`, `ExplicitDenyPolicyArn`, `FlowLogsRoleArn`), each with `ExportName` `proposal-orchestrator-iam-<Key>`; role ARNs `arn:aws:iam::797661577394:role/proposal-orchestrator-runtime-role` and `…:role/proposal-orchestrator-flow-logs-role`; profile `…:instance-profile/proposal-orchestrator-runtime-profile`; policies `…:policy/proposal-orchestrator-boundary` and `…:policy/proposal-orchestrator-explicit-deny` |
| `R5_07_exports.json` | The same seven export names and values |

### Step 08 — Read-only evidence of what was created (ARNs from `R5_outputs.json` only)

What it does: records the role, its trust policy, boundary, tags and attached policies; every policy
document; the instance profile; and every customer-managed policy in the account after R5. IAM is
global: no `--region`.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
$O = Get-Content "$E\R5_outputs.json" -Raw | ConvertFrom-Json
$RNAME = ($O | Where-Object OutputKey -eq 'RuntimeRoleName').OutputValue
$PNAME = ($O | Where-Object OutputKey -eq 'InstanceProfileName').OutputValue
$BARN  = ($O | Where-Object OutputKey -eq 'PermissionBoundaryArn').OutputValue
$FNAME = (($O | Where-Object OutputKey -eq 'FlowLogsRoleArn').OutputValue -split '/')[-1]
"runtime=$RNAME profile=$PNAME flowlogs=$FNAME"
aws iam get-role --profile po-r1 --role-name $RNAME --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_runtime-role.json"
aws iam list-attached-role-policies --profile po-r1 --role-name $RNAME --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_runtime-role-attached.json"
aws iam list-role-policies --profile po-r1 --role-name $RNAME --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_runtime-role-inline.json"
aws iam get-instance-profile --profile po-r1 --instance-profile-name $PNAME --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_instance-profile.json"
aws iam get-role --profile po-r1 --role-name $FNAME --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_flow-logs-role.json"
aws iam list-attached-role-policies --profile po-r1 --role-name $FNAME --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_flow-logs-role-attached.json"
aws iam list-policies --profile po-r1 --scope Local --query "Policies[].{name:PolicyName,arn:Arn,attachments:AttachmentCount,boundaryUses:PermissionsBoundaryUsageCount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_local-policies-after.json"
# every customer-managed policy: metadata (with Description) and its default version document
$ARNS = (Get-Content "$E\R5_08_local-policies-after.json" -Raw | ConvertFrom-Json).arn
foreach ($a in $ARNS) {
  $n = ($a -split '/')[-1]
  aws iam get-policy --profile po-r1 --policy-arn $a --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_policy-$n.json"
  $v = aws iam get-policy --profile po-r1 --policy-arn $a --query "Policy.DefaultVersionId" --output text
  aws iam get-policy-version --profile po-r1 --policy-arn $a --version-id $v --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_08_policy-version-$n.json"
}
Get-ChildItem "$E\R5_08_*" | Select-Object Name, Length
```

| Evidence file | PASS criterion |
|---|---|
| `R5_08_runtime-role.json` | `RoleName` `proposal-orchestrator-runtime-role`, `Path` `/`; `AssumeRolePolicyDocument` has one statement, `Allow`, `Principal.Service` = `ec2.amazonaws.com`, `sts:AssumeRole` (**DC-13**); `PermissionsBoundary.PermissionsBoundaryArn` = `PermissionBoundaryArn` from `R5_outputs.json`, `PermissionsBoundaryType` `Policy` (**DC-12**); tags `Name` and `project` |
| `R5_08_runtime-role-attached.json` | Exactly four policies: `proposal-orchestrator-bedrock-invoke`, `-supporting-services`, `-deploy-bucket-read`, `-explicit-deny` (**DC-11** attached) |
| `R5_08_runtime-role-inline.json` | `PolicyNames` = `[]` |
| `R5_08_instance-profile.json` | `InstanceProfileName` `proposal-orchestrator-runtime-profile`; `Roles` holds exactly one role, `proposal-orchestrator-runtime-role` (**DC-09**, profile half) |
| `R5_08_flow-logs-role.json` | Trust: `vpc-flow-logs.amazonaws.com` only, with `aws:SourceAccount` = 797661577394 and `aws:SourceArn` like `arn:aws:ec2:eu-north-1:797661577394:vpc-flow-log/*`; tags `Name` and `project` |
| `R5_08_flow-logs-role-attached.json` | Exactly one policy, `proposal-orchestrator-flow-logs-write` |
| `R5_08_local-policies-after.json` | **Exactly six** customer-managed policies, all named `proposal-orchestrator-*`: `boundary` (attachments 0, boundaryUses 1), `explicit-deny`, `bedrock-invoke`, `supporting-services`, `deploy-bucket-read` and `flow-logs-write` (attachments 1 each). No other policy. |
| `R5_08_policy-<name>.json` (six) | `Description` contains neither "temporary" nor "validation" (case-insensitive) (**exit condition 4**) |
| `R5_08_policy-version-<name>.json` (six) | `IsDefaultVersion` true; the document equals the template's policy with the parameters filled in (agent compares statement by statement; **DC-10** invoke, **DC-11** deny, **DC-12** boundary) |

### Step 09 — IAM simulation against the runtime role (read-only)

What it does: asks IAM how the runtime role's policies **and its boundary** decide each case. The
simulator does not call Bedrock; the context values are supplied here. In particular, it cannot prove
that a routed call carries the destination Region as `aws:RequestedRegion` (F-R5-2); R11's live call
does. Every file's `EvalDecision` is the criterion.

PowerShell (run as one block; the function only builds the argument list):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
$O = Get-Content "$E\R5_outputs.json" -Raw | ConvertFrom-Json
$RARN = ($O | Where-Object OutputKey -eq 'RuntimeRoleArn').OutputValue
$P = Get-Content "deploy\aws\parameters\iam.json" -Raw | ConvertFrom-Json
$FMS   = (($P | Where-Object ParameterKey -eq 'FoundationModelArns').ParameterValue) -split ','
$PROFS = (($P | Where-Object ParameterKey -eq 'InferenceProfileArns').ParameterValue) -split ','
$INV = @('bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream')
function Ctx([string]$k, [string]$v) { "ContextKeyName=$k,ContextKeyValues=$v,ContextKeyType=string" }
function Sim([string]$Name, [string[]]$Actions, [string[]]$Resources, [string[]]$Context) {
  $a = @('iam', 'simulate-principal-policy', '--profile', 'po-r1', '--policy-source-arn', $RARN, '--action-names') + $Actions + @('--resource-arns') + $Resources
  if ($Context) { $a += @('--context-entries') + $Context }
  $a += @('--output', 'json')
  & aws @a 2>&1 | Out-File -Encoding utf8 "$E\R5_09_$Name.json"
}
# --- expected: allowed (exit condition 1) ---
Sim 'allow-profiles' $INV $PROFS @(Ctx 'aws:RequestedRegion' 'eu-north-1')
foreach ($fm in $FMS) {
  $reg = $fm.Split(':')[3]; $model = $fm.Split('/')[-1]
  $prof = $PROFS | Where-Object { $_.EndsWith("/eu.$model") }
  Sim "allow-fm-$reg-$model" $INV @($fm) @((Ctx 'aws:RequestedRegion' $reg), (Ctx 'bedrock:InferenceProfileArn' $prof))
}
Sim 'allow-s3-get-bundle' @('s3:GetObject') @('arn:aws:s3:::proposal-orchestrator-deploy-797661577394/bundles/orchestrator.tar.gz') $null
Sim 'allow-s3-list-bundles' @('s3:ListBucket') @('arn:aws:s3:::proposal-orchestrator-deploy-797661577394') @(Ctx 's3:prefix' 'bundles/')
Sim 'allow-secret' @('secretsmanager:GetSecretValue') @('arn:aws:secretsmanager:eu-north-1:797661577394:secret:proposal-orchestrator/env-config-AbCdEf') $null
Sim 'allow-sts-ssm' @('sts:GetCallerIdentity', 'ssm:UpdateInstanceInformation', 'ssmmessages:OpenControlChannel', 'ec2messages:GetMessages') @('*') $null
# --- expected: denied (exit condition 2) ---
Sim 'deny-admin-logging' @('bedrock:PutModelInvocationLoggingConfiguration', 'bedrock:CreateProvisionedModelThroughput') @('*') @(Ctx 'aws:RequestedRegion' 'eu-north-1')
Sim 'deny-global-profile' $INV @('arn:aws:bedrock:eu-north-1:797661577394:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0') @(Ctx 'aws:RequestedRegion' 'eu-north-1')
Sim 'deny-non-claude-model' $INV @('arn:aws:bedrock:eu-north-1::foundation-model/amazon.nova-pro-v1:0') @(Ctx 'aws:RequestedRegion' 'eu-north-1')
Sim 'deny-unapproved-region' $INV @($PROFS[0]) @(Ctx 'aws:RequestedRegion' 'us-east-1')
Sim 'deny-fm-without-profile' $INV @($FMS[1]) @(Ctx 'aws:RequestedRegion' $FMS[1].Split(':')[3])
Sim 'deny-eu-profile-not-od7' $INV @('arn:aws:bedrock:eu-north-1:797661577394:inference-profile/eu.anthropic.claude-haiku-4-5-20251001-v1:0') @(Ctx 'aws:RequestedRegion' 'eu-north-1')
Sim 'deny-s3-put-bundle' @('s3:PutObject', 's3:DeleteObject') @('arn:aws:s3:::proposal-orchestrator-deploy-797661577394/bundles/orchestrator.tar.gz') $null
Sim 'deny-s3-other-bucket' @('s3:GetObject', 's3:PutObject') @('arn:aws:s3:::proposal-orchestrator-cloudtrail-797661577394/x') $null
Sim 'deny-ec2' @('ec2:DescribeInstances', 'ec2:RunInstances') @('*') $null
Sim 'deny-iam' @('iam:ListRoles', 'iam:PassRole') @('*') $null
Sim 'deny-kms-identity-grant' @('kms:Decrypt') @('arn:aws:kms:eu-north-1:797661577394:key/00000000-0000-0000-0000-000000000000') $null
Get-ChildItem "$E\R5_09_*" | Select-Object Name, Length
```

Expect 28 files (`R5_09_*.json`): 17 allowed cases, 11 denied. The key ids above are illustrative resource names, not lookups:
the secret suffix `AbCdEf` and the all-zero key id stand for "any secret of that name" and "any key of
this account"; nothing reads them.

| Evidence file | Expected `EvalDecision` (every action, every resource) | Why |
|---|---|---|
| `R5_09_allow-profiles.json` | `allowed`; and `PermissionsBoundaryDecisionDetail.AllowedByPermissionsBoundary` = `true` | DC-10, DC-12; the boundary is evaluated |
| `R5_09_allow-fm-<region>-<model>.json` (twelve) | `allowed` | DC-10, F2: each routed model, through its profile, in its Region |
| `R5_09_allow-s3-get-bundle.json`, `…-list-bundles.json` | `allowed` | R5-D1 |
| `R5_09_allow-secret.json`, `R5_09_allow-sts-ssm.json` | `allowed` | supporting services, R5-D7 |
| `R5_09_deny-admin-logging.json` | `explicitDeny` | DC-11 (invocation logging stays off) |
| `R5_09_deny-global-profile.json` | `explicitDeny` | OD7-global (a real `global.` id from `R2_03_profiles.json`) |
| `R5_09_deny-non-claude-model.json` | `explicitDeny` | DC-11 (a real id from `R5_03_non-claude-models.json`) |
| `R5_09_deny-unapproved-region.json` | `explicitDeny` | DC-16 |
| `R5_09_deny-fm-without-profile.json` | `implicitDeny` | R5-D3: a model only through an OD7 profile |
| `R5_09_deny-eu-profile-not-od7.json` | `implicitDeny` | OD7-resources: Haiku 4.5 is not in the set |
| `R5_09_deny-s3-put-bundle.json` | `implicitDeny` | R5-D2: no S3 write is granted |
| `R5_09_deny-s3-other-bucket.json` | `explicitDeny` | R5-D2, F7 |
| `R5_09_deny-ec2.json`, `R5_09_deny-iam.json` | `explicitDeny` | DC-11 |
| `R5_09_deny-kms-identity-grant.json` | `implicitDeny` | R5-D6: Decrypt comes from R6's key policy, not from an identity policy |

**STOP rule.** None: a different decision is a FAIL to report, not something to fix here.

*Follow-up 2026-10-25 (agent):* seven cases above lacked the `aws:RequestedRegion` context and were decided by the organization's SCP, not by R5's policies; and step 11's verbose test log tripped the secret scan. Both are re-run by `STEPS_fix1.md` (steps 12 and 13); the original files stay as history. The agent
writes `STEPS_fix1.md` if any file deviates.

### Step 10 — Session-end credits (read-only)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R5_10_plan-state-after.json"
Get-Content "$E\R5_10_plan-state-after.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R5_10_plan-state-after.json` | `FREE` / `ACTIVE`; credits ≥ `199.00` (IAM is free; expected unchanged at 199.99) |

**Hand back here (end of round 2).** The agent verifies every file, writes `VERIFICATION.md`, the
register v2 rows (R5-D9) and the worklog entry.

### Step 11 — Guards and secret scan over the finished folder (round 3, workstation only)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_11_secret-scan.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_11_old-id-guard.txt"
py -3.10 -m pytest tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_old_id_guard.py tests/test_evidence_protocol_scaffold.py 2>&1 | Out-File -Encoding utf8 "$E\R5_11_pytest.txt"
Get-Content "$E\R5_11_secret-scan.txt", "$E\R5_11_old-id-guard.txt"; Get-Content "$E\R5_11_pytest.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R5_11_secret-scan.txt` | `CLEAN: …R5`; `exit=0` |
| `R5_11_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R5_11_pytest.txt` | Python 3.10; `N passed`, no `failed` (agent's figure given at hand-back) |

Then commit, and confirm R5 in session.

---

## CloudShell fallback

Only if the workstation sign-in fails. Use the **eu-north-1** CloudShell, `mkdir -p ~/R5 && cd ~/R5`,
and translate each PowerShell line: drop `--profile po-r1`; replace
`2>&1 | Out-File -Encoding utf8 "$E\<file>"` with `> <file> 2>&1`; write
`V=$(aws iam get-policy --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore --query Policy.DefaultVersionId --output text)`
and use `--version-id "$V"`; for 03d use `{ aws cloudformation describe-stacks --region eu-north-1 --stack-name proposal-orchestrator-iam --output json; echo "exit=$?"; } > R5_03_iam-stack-before.txt 2>&1`.
Bring the files home by zip as in R2 (`cd ~ && zip -r R5_evidence.zip R5`, download,
`Expand-Archive`, copy into this folder).

## Before you hand back

- [ ] Every evidence file of the round exists in this folder, under exactly its name.
- [ ] You opened each file and checked that it holds no secret value, key or token.
- [ ] You reported each step in session (UTC time, any deviation, any error). The agent keeps
      `RUNLOG.md` from your reports.
