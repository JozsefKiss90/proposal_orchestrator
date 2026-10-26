# R6 — KMS key: the runtime role decrypts through the key policy: step sheet

| Field | Value |
|---|---|
| Ticket | `R6` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R6, as read in `plans/aws_redeployment_r6_handoff_2026-10-25.md` §3 |
| Decisions applied | OD2 (a) one hardened runtime role; OD1-r1 eu-north-1; OD6-r3 (stacks, change sets, guards; `OD6-r3-parameters` narrowed for the kms stack, see below); OD11-r2 (admin = AccountFullAccessRole through IAM); R5-D4 (log-group prefix `/${ProjectName}/`); R5-D6 (KMS narrowing in the key policy); R1-D2 session-start check; OD10 Free plan, no upgrade. The operator's answers of 2026-10-26 to the R6 handoff §4 points ("1–9 a", 4b included; point 10 "10a"), recorded in `aws-redeployment-r6-kms_2026-10-26` |
| Written by / on | agent (Claude) / 2026-10-26 |
| Account / region | `797661577394` / `eu-north-1`. **KMS is regional:** every `kms`, `cloudformation` and `cloudtrail` command names `--region eu-north-1`. **IAM is global:** every `aws iam` command runs **without** `--region` |
| IDs taken from | Round 1: none (lookups only). The runtime role ARN from `evidence_v2/R5/R5_outputs.json` and, in this round, from the live export list (step 03d). From step 06 on: `R6_outputs.json` |
| Controls touched | DC-18 (CMK, alias, rotation), DC-19 (key policy scoped: root, runtime role, CloudTrail, CloudWatch Logs only) |
| Cost created | **No hourly cost.** The key itself has a **monthly fee**: 1 USD per month, prorated hourly, plus 1 USD per month for each of the first two rotations (about 3 USD/month from the second year), paid from credits. The operator acknowledged in session on 2026-10-26 that this is the "free (key: monthly)" case of OD6-r3, not an hourly-billed resource of the kind R11 gates. **Round 1 creates nothing.** The key exists only after step 06, which runs only after both have read the change set (step 05). |

## Settled with the operator (2026-10-26, "1–9 a", then "10a")

1. Cost: proceed; monthly key fee acknowledged (above).
2. Trail name, lasting rule: `${ProjectName}-bedrock-trail`, trail ARN
   `arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/${ProjectName}-bedrock-trail`.
   R7 creates exactly that trail with eu-north-1 as its home Region.
3. The runtime role's grant (`kms:Decrypt`, `kms:DescribeKey`) carries `StringEquals kms:ViaService` =
   `secretsmanager.${AWS::Region}.amazonaws.com`, `s3.${AWS::Region}.amazonaws.com`.
4. No admin statement: the account-root `kms:*` statement is the only administrative grant (the admin role
   works through IAM). `AdminRoleArn` leaves the kms template, `deploy/aws/parameters/kms.json`, the
   contract test's kms case and the README table. 4b: R6's decision record names this in `supersedes`
   as "OD6-r3-parameters, the kms stack's parameter list only".
5. `DeletionPolicy: Retain`, `UpdateReplacePolicy: Retain` on the key; `PendingWindowInDays: 30`. The kms
   stack is not deleted (deleting it would leave the key billing and the alias gone).
6. `RotationPeriodInDays: 365`, set explicitly.
7. `tests/test_aws_kms_template.py` pins the stack's shape; the template guard is unchanged.
8. Exit condition 2 is evidenced by the runtime role's policy lists, one IAM simulation of `kms:Decrypt`
   on the new key without a resource policy (expected `implicitDeny`, allowed by organizations and by the
   boundary), and the key policy read back. No key-policy simulation (the simulator documentation does not
   cover KMS keys); the grant is exercised in R8 and R11.
9. On a PASS verification: DC-18 `VERIFIED_PASS`; DC-19 `VERIFIED_PASS` on the policy-level criterion,
   noted "CloudTrail and CloudWatch Logs grants exercised in R7, runtime grant in R8/R11".
10. (added after round 1, operator "10a", 2026-10-26) CloudTrail gets no `kms:Decrypt`; lasting rule:
    R7 creates the trail bucket without an S3 Bucket Key on this CMK (R6-D10).

## Before you start

- **Sign in with `aws login --profile po-r1`**, never bare `aws login`.
- **Where commands run.** PowerShell in the VS Code terminal, repository root
  (`C:\Code\proposal_demo\proposal_orchestrator`). Every AWS command names `--profile po-r1`.
  CloudShell is the fallback only (end of this sheet).
- **`$E` must be set in every new PowerShell window.** Every block below starts with it.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command.
- The AWS CLI v2 exits **254** when the service answers with an error, and PowerShell wraps long error
  text inside the file. Criteria below are written on substrings, not on one-line quotes.
- Never save secret values, access keys, session tokens or passwords. No step below prints any.
- If a step fails, stop, report the error in session, and do not improvise a fix.
- **Rounds.**
  - **Round 1 (this sheet now): steps 01–03**, read-only. Hand back. The agent then checks the files,
    fills `deploy/aws/templates/30-kms.yaml`, removes `AdminRoleArn` from the kms stack (template,
    parameter file, contract test, README), writes `tests/test_aws_kms_template.py` and the decision
    record `aws-redeployment-r6-kms_2026-10-26`, and adds steps 04–05 to this sheet.
  - **Round 1b: steps 04–05** (lint, guards, tests, change set). Hand back; both read the change set;
    the operator gives the go.
  - **Round 2: steps 06–10** (execute, outputs, read-only evidence, IAM simulation, credits).
  - **Round 3: step 11** (tests, then the old-ID guard and the scan over the finished folder, commit).

---

## Steps

### Step 01 — Session-start check: credits, budget, alert states (R1-D2)

What it does: confirms that the Free plan is active, the credits are intact and no budget alert is in
`ALARM`, before anything else runs.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_01_budget-notifications.json"
Get-Content "$E\R6_01_plan-state.json", "$E\R6_01_budgets.json", "$E\R6_01_budget-notifications.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_01_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `199.00` (R5 left 199.99, `R5_10_plan-state-after.json`); `accountPlanExpirationDate` starts `2027-04-19` |
| `R6_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` = `10.0`, `spend` < `8.5` |
| `R6_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` = `OK` |

**STOP rule.** If the plan is not `ACTIVE`, the credits are below 199.00 USD, or any notification is in
`ALARM`, stop here and report it.

### Step 02 — Who is calling

What it does: records that the CLI runs as the OD11-r2 identity in the right account.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_02_caller-identity.json"
Get-Content "$E\R6_02_caller-identity.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_02_caller-identity.json` | `Account` = `797661577394`; `Arn` starts with `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Any other account: stop. Nothing below may run.

### Step 03 — Read-only lookups (nothing is created)

What it does: collects, before the template is written, the facts it is written from (handoff §7a:
from evidence, not memory):

- **03a** the KMS aliases in eu-north-1: `alias/proposal-orchestrator` must be free (an alias name is
  unique per account and Region; the create would fail on a collision);
- **03b** the KMS keys in eu-north-1 and, for each, who manages it: no customer-managed key is expected
  before R6 (AWS-managed `aws/*` keys may exist and are not a FAIL);
- **03c** that the `proposal-orchestrator-kms` stack does not exist yet;
- **03d** the stack exports: the seven `proposal-orchestrator-iam-*` exports, among them
  `RuntimeRoleArn`, the value the key policy imports;
- **03e** the runtime role's attached and inline policies **before** R6 (baseline for exit condition 2:
  R6 adds no identity grant);
- **03f** the CloudTrail trails visible in eu-north-1: the name `proposal-orchestrator-bedrock-trail`
  (point 2) must not be in use.

PowerShell (03e without `--region`: IAM is global):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
# 03a — aliases (AWS-managed and customer)
aws kms list-aliases --profile po-r1 --region eu-north-1 --query "Aliases[].{name:AliasName,target:TargetKeyId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_03_aliases-before.json"
# 03b — keys, then manager/state/spec of each (an empty list is a valid result)
aws kms list-keys --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_03_keys-before.json"
$ids = aws kms list-keys --profile po-r1 --region eu-north-1 --query "Keys[].KeyId" --output text
$meta = foreach ($k in (($ids -split "\s+") | Where-Object { $_ -and $_ -ne "None" })) {
  aws kms describe-key --profile po-r1 --region eu-north-1 --key-id $k --query "KeyMetadata.{KeyId:KeyId,KeyManager:KeyManager,KeyState:KeyState,KeySpec:KeySpec,MultiRegion:MultiRegion,Description:Description}" --output json | ConvertFrom-Json
}
ConvertTo-Json -InputObject @($meta) | Out-File -Encoding utf8 "$E\R6_03_keys-detail-before.json"
# 03c — the KMS stack must not exist yet (an error here is the expected result)
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R6_03_kms-stack-before.txt"
# 03d — project exports (network and iam)
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-')].{name:Name,value:Value,stack:ExportingStackId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_03_exports.json"
# 03e — the runtime role's identity policies before R6
aws iam list-attached-role-policies --profile po-r1 --role-name proposal-orchestrator-runtime-role --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_03_runtime-role-attached-before.json"
aws iam list-role-policies --profile po-r1 --role-name proposal-orchestrator-runtime-role --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_03_runtime-role-inline-before.json"
# 03f — trails visible in eu-north-1 (including organization trails shown as shadow trails)
aws cloudtrail describe-trails --profile po-r1 --region eu-north-1 --include-shadow-trails --query "trailList[].{name:Name,arn:TrailARN,home:HomeRegion,org:IsOrganizationTrail,multi:IsMultiRegionTrail,kms:KmsKeyId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_03_trails-before.json"
Get-Content "$E\R6_03_aliases-before.json", "$E\R6_03_keys-detail-before.json", "$E\R6_03_kms-stack-before.txt", "$E\R6_03_exports.json", "$E\R6_03_runtime-role-attached-before.json", "$E\R6_03_runtime-role-inline-before.json", "$E\R6_03_trails-before.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_03_aliases-before.json` | A JSON list. No entry `name` = `alias/proposal-orchestrator`. Entries starting `alias/aws/` are AWS-managed and allowed. |
| `R6_03_keys-before.json` | A JSON object with a `Keys` list (may be empty) |
| `R6_03_keys-detail-before.json` | One entry per key of the previous file (`[]` if there are none). No entry with `KeyManager` = `CUSTOMER`. Entries with `KeyManager` = `AWS` are allowed. A customer-managed key is **not** a FAIL by itself: report it in session and we decide (it may be a leftover R1 did not cover). |
| `R6_03_kms-stack-before.txt` | Contains `ValidationError` and `does not exist` for the stack `proposal-orchestrator-kms` (the name may wrap across two lines); last line `exit=254` |
| `R6_03_exports.json` | Exactly seven names starting `proposal-orchestrator-iam-` (the R5 contract keys: `RuntimeRoleName`, `RuntimeRoleArn`, `InstanceProfileName`, `InstanceProfileArn`, `PermissionBoundaryArn`, `ExplicitDenyPolicyArn`, `FlowLogsRoleArn`); `proposal-orchestrator-iam-RuntimeRoleArn` has the value `arn:aws:iam::797661577394:role/proposal-orchestrator-runtime-role`, equal to `R5_outputs.json`. No name starts `proposal-orchestrator-kms-`. The seven `proposal-orchestrator-network-*` exports are expected too. |
| `R6_03_runtime-role-attached-before.json` | `AttachedPolicies` lists exactly the four R5 managed policies (`proposal-orchestrator-bedrock-invoke`, `-supporting-services`, `-deploy-bucket-read`, `-explicit-deny`), the same set as `R5_08_runtime-role-attached.json` |
| `R6_03_runtime-role-inline-before.json` | `PolicyNames` = `[]` |
| `R6_03_trails-before.json` | A JSON list. No entry `name` = `proposal-orchestrator-bedrock-trail`. Any other trail (for example an organization trail of the AWS-managed organization) is **not** a FAIL: report it; the agent records it. |

**STOP rule.** If `alias/proposal-orchestrator` exists, the kms stack exists, an export
`proposal-orchestrator-kms-*` exists, `proposal-orchestrator-iam-RuntimeRoleArn` is missing or differs
from `R5_outputs.json`, the runtime role holds a policy R5 did not attach, or the trail name is taken:
stop and report. The template is not written over an occupied name or a missing import.

**Hand back here (end of round 1).** Report steps 01–03 in session (UTC times, any deviation). The agent
checks every file in the device shell (criteria, secret scan, old-ID guard), then writes the template,
the test, the decision record and steps 04–05 below.

---

*Round 1 done 2026-10-26 (~16:35 UTC): all fourteen files PASS (agent's check in the device shell; secret scan and old-ID guard CLEAN). Findings F-R6-1 and F-R6-2 of `aws-redeployment-r6-kms_2026-10-26`.*

### Step 04 — Lint, guards and tests on the filled template (workstation only, no AWS call)

What it does: proves, before anything is created, that `30-kms.yaml` lints for eu-north-1, keeps the
template rules, carries no old-account id, and has the shape `tests/test_aws_kms_template.py` pins
(decision record `aws-redeployment-r6-kms_2026-10-26`, R6-D2 to R6-D7); and that the contract test
accepts the kms stack without `AdminRoleArn` (R6-D4). Run `deactivate` first if `.venv-lint` is active
(lint still runs through its own executable). Pytest runs with `-q` (R5 lesson: verbose test ids would
put pattern names into this folder).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R6_04_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R6_04_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R6_04_old-id-guard.txt"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_old_id_guard.py } 2>&1 | Out-File -Encoding utf8 "$E\R6_04_pytest.txt"
Get-Content "$E\R6_04_cfn-lint.txt", "$E\R6_04_template-guard.txt", "$E\R6_04_old-id-guard.txt"; Get-Content "$E\R6_04_pytest.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R6_04_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R6_04_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R6_04_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R6_04_pytest.txt` | First line `Python 3.10.…`; last line `157 passed` (the agent's run under Python 3.10.12) with no `failed`, `error` or `skipped` |

**STOP rule.** Any non-zero exit or failed test: stop. The template is not deployed until this step is
clean.

### Step 05 — Create the change set and read it (nothing is created yet)

What it does: asks CloudFormation to plan the KMS stack. A change set of type CREATE builds nothing
until it is executed. **No `--capabilities`:** the stack holds no IAM resource and no macro, so none is
required (if CloudFormation asks for one anyway, `create-change-set` fails with
`InsufficientCapabilities`: stop and hand back, do not add a capability on your own). The
`Fn::ImportValue` of `proposal-orchestrator-iam-RuntimeRoleArn` is resolved here: if the export were
missing, the change set would fail.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms --change-set-name r6-create-01 --change-set-type CREATE --template-body file://deploy/aws/templates/30-kms.yaml --parameters file://deploy/aws/parameters/kms.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_05_create-change-set.json"
Get-Content "$E\R6_05_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms --change-set-name r6-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms --change-set-name r6-create-01 --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_05_change-set.json"
Get-Content "$E\R6_05_change-set.json"
```

If `create-change-set` itself returns an error, or `wait` reports a terminal failure, still run the
`describe-change-set` line: `Status` and `StatusReason` in `R6_05_change-set.json` are the evidence.
Then stop and hand back.

| Evidence file | PASS criterion |
|---|---|
| `R6_05_create-change-set.json` | `Id` starts `arn:aws:cloudformation:eu-north-1:797661577394:changeSet/r6-create-01/`; `StackId` starts `arn:aws:cloudformation:eu-north-1:797661577394:stack/proposal-orchestrator-kms/` |
| `R6_05_change-set.json` | `Status` = `CREATE_COMPLETE`; `ExecutionStatus` = `AVAILABLE`; `Capabilities` absent or `[]`; `Tags` = `[{project: proposal-orchestrator}]`; `Parameters` show exactly `ExpectedAccountId` 797661577394, `ExpectedRegion` eu-north-1 and `ProjectName` proposal-orchestrator, and **no** `AdminRoleArn`; `Changes` holds **exactly two** entries, each `ResourceChange.Action` = `Add`: `ProjectKey` (`AWS::KMS::Key`) and `ProjectKeyAlias` (`AWS::KMS::Alias`). Nothing else. The CREATE type is evidenced by the command line, by `R6_03_kms-stack-before.txt` and by the two `Add` entries (`describe-change-set` returns no `ChangeSetType` field). |

**Hand back here (end of round 1b).** Report steps 04–05 in session. Both of us read
`R6_05_change-set.json` against the criterion. **Step 06 runs only after you have confirmed in session
that the change set lists exactly those two resources and given the go**; executing it starts the key's
monthly fee (R6-D1). If the change set failed (for example an organization policy refusing
`kms:CreateKey` or `kms:PutKeyPolicy`), the agent records the error verbatim in `RUNLOG.md` and a
successor decision is settled before the template changes; nothing is executed. The agent adds steps
06–11 after the go.

*Round 1b done 2026-10-26 (~16:47 UTC): steps 04–05 PASS; change set `r6-create-01` read by both. **Operator's go in session: 2026-10-26 ~16:51 UTC ("mehet").***

### Step 06 — Execute the change set (creates the key and the alias; the key's monthly fee starts)

**Only after the operator's go in session on `R6_05_change-set.json` (given 2026-10-26).** What it does:
creates the two resources of the change set, and nothing else.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
& { aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms --change-set-name r6-create-01; "execute exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R6_06_execute-exit.txt"
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_06_stack-status.json"
aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_06_stack-events.json"
Get-Content "$E\R6_06_execute-exit.txt", "$E\R6_06_stack-status.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_06_execute-exit.txt` | `execute exit=0` and no error line |
| `R6_06_stack-status.json` | `status` = `CREATE_COMPLETE`; `capabilities` null or `[]`; `tags` hold `project` = `proposal-orchestrator` |
| `R6_06_stack-events.json` | `ProjectKey`, `ProjectKeyAlias` and the stack `proposal-orchestrator-kms` each reach `CREATE_COMPLETE`; no `*_FAILED` and no `ROLLBACK` status anywhere |

**STOP rule.** On a rollback or any `*_FAILED` event: stop, report it, and **do not delete the stack**.
(A rolled-back key is retained by `DeletionPolicy: Retain` and may still exist: the agent then writes
`STEPS_fix1.md` to find it and decide, with you, whether to schedule its deletion.)

### Step 07 — Save the stack outputs (ids for every later step and ticket)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-kms --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_outputs.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-kms-')]" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_07_exports.json"
Get-Content "$E\R6_outputs.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_outputs.json` | Exactly the three contract keys, each with `ExportName` `proposal-orchestrator-kms-<Key>`: `KeyArn` = `arn:aws:kms:eu-north-1:797661577394:key/<uuid>`; `KeyId` = that `<uuid>`; `KeyAliasName` = `alias/proposal-orchestrator` |
| `R6_07_exports.json` | The same three export names and values, `ExportingStackId` the kms stack of step 05 |

### Step 08 — Read-only evidence of what was created (ids from `R6_outputs.json` only)

What it does: records the key (DC-18), its rotation (DC-18, exit condition 1), that the alias resolves to
it (exit condition 1), its policy (DC-19, exit condition 2), its tags and grants, and the runtime role's
identity policies after R6 (exit condition 2). KMS commands name `--region eu-north-1`; the two IAM
commands do not. The agent compares `R6_08_key-policy.json` with the template by script (intrinsics
resolved with the parameter file and the step 03d export), statement by statement.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
$O = Get-Content "$E\R6_outputs.json" -Raw | ConvertFrom-Json
$KARN  = ($O | Where-Object OutputKey -eq 'KeyArn').OutputValue
$KID   = ($O | Where-Object OutputKey -eq 'KeyId').OutputValue
$ALIAS = ($O | Where-Object OutputKey -eq 'KeyAliasName').OutputValue
"KeyArn=$KARN"; "KeyId=$KID"; "Alias=$ALIAS"
aws kms describe-key --profile po-r1 --region eu-north-1 --key-id $KARN --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_describe-key.json"
aws kms get-key-rotation-status --profile po-r1 --region eu-north-1 --key-id $KARN --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_rotation-status.json"
aws kms describe-key --profile po-r1 --region eu-north-1 --key-id $ALIAS --query "KeyMetadata.{KeyId:KeyId,Arn:Arn,KeyState:KeyState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_describe-by-alias.json"
aws kms list-aliases --profile po-r1 --region eu-north-1 --key-id $KID --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_aliases-of-key.json"
aws kms get-key-policy --profile po-r1 --region eu-north-1 --key-id $KARN --policy-name default --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_key-policy.json"
aws kms list-resource-tags --profile po-r1 --region eu-north-1 --key-id $KARN --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_key-tags.json"
aws kms list-grants --profile po-r1 --region eu-north-1 --key-id $KARN --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_key-grants.json"
aws iam list-attached-role-policies --profile po-r1 --role-name proposal-orchestrator-runtime-role --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_runtime-role-attached.json"
aws iam list-role-policies --profile po-r1 --role-name proposal-orchestrator-runtime-role --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_08_runtime-role-inline.json"
Get-Content "$E\R6_08_describe-key.json", "$E\R6_08_rotation-status.json", "$E\R6_08_describe-by-alias.json", "$E\R6_08_aliases-of-key.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_08_describe-key.json` | `KeyMetadata.Arn` = `KeyArn`; `AWSAccountId` 797661577394; `KeyManager` `CUSTOMER`; `KeyState` `Enabled`; `Enabled` true; `KeySpec` `SYMMETRIC_DEFAULT`; `KeyUsage` `ENCRYPT_DECRYPT`; `Origin` `AWS_KMS`; `MultiRegion` false; `Description` names the project and contains neither "temporary" nor "validation" (DC-18) |
| `R6_08_rotation-status.json` | `KeyRotationEnabled` true; `RotationPeriodInDays` 365; `NextRotationDate` about one year after creation (DC-18, exit condition 1) |
| `R6_08_describe-by-alias.json` | `KeyId` = `KeyId` of `R6_outputs.json`, `KeyState` `Enabled` (the alias resolves to the new key: exit condition 1) |
| `R6_08_aliases-of-key.json` | Exactly one alias, `AliasName` `alias/proposal-orchestrator`, `TargetKeyId` = `KeyId` |
| `R6_08_key-policy.json` | `PolicyName` `default`; the `Policy` document equals the template's key policy resolved for this account and Region: the five statements `EnableRootAccountIamDelegation`, `AllowRuntimeRoleDecryptViaServices` (principal `arn:aws:iam::797661577394:role/proposal-orchestrator-runtime-role`), `AllowCloudTrailEncryptLogs`, `AllowCloudTrailDescribeKey`, `AllowCloudWatchLogsProjectLogGroups`, with their actions and conditions, nothing else (DC-19, R6-D2 to R6-D4, R6-D10; checked by the agent's script) |
| `R6_08_key-tags.json` | `Tags` hold `Name` = `proposal-orchestrator` and `project` = `proposal-orchestrator` (CloudFormation may add `aws:cloudformation:*` tags; allowed) |
| `R6_08_key-grants.json` | `Grants` = `[]`: no grant gives any principal a separate use of the key |
| `R6_08_runtime-role-attached.json` | The same four policies as `R6_03_runtime-role-attached-before.json` (R6 added no identity grant: exit condition 2) |
| `R6_08_runtime-role-inline.json` | `PolicyNames` = `[]` |

### Step 09 — IAM simulation: no identity policy grants the runtime role Decrypt (read-only)

What it does: asks IAM how the runtime role's **identity** policies and its boundary decide `kms:Decrypt`
and `kms:DescribeKey` on the new key, without any resource policy (R6-D8). Expected: the boundary would
allow it, the organization does not object, and no identity policy grants it, so the result is
`implicitDeny`. The key-policy grant that does allow it is evidenced by step 08 and exercised in R8/R11.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
$O = Get-Content "$E\R6_outputs.json" -Raw | ConvertFrom-Json
$KARN = ($O | Where-Object OutputKey -eq 'KeyArn').OutputValue
aws iam simulate-principal-policy --profile po-r1 --policy-source-arn arn:aws:iam::797661577394:role/proposal-orchestrator-runtime-role --action-names kms:Decrypt kms:DescribeKey --resource-arns $KARN --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=eu-north-1,ContextKeyType=string" --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_09_deny-kms-identity-grant.json"
Get-Content "$E\R6_09_deny-kms-identity-grant.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_09_deny-kms-identity-grant.json` | Two `EvaluationResults` (`kms:Decrypt`, `kms:DescribeKey`), each with `EvalResourceName` = `KeyArn`, `EvalDecision` = `implicitDeny`, `MatchedStatements` = `[]`, `OrganizationsDecisionDetail.AllowedByOrganizations` = true and `PermissionsBoundaryDecisionDetail.AllowedByPermissionsBoundary` = true (exit condition 2) |

**STOP rule.** None: a different decision is a FAIL to report, not something to fix here.

### Step 10 — Session-end credits (read-only)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R6_10_plan-state-after.json"
Get-Content "$E\R6_10_plan-state-after.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_10_plan-state-after.json` | `FREE` / `ACTIVE`; credits ≥ `199.00`. The key's fee accrues hourly and is billed with a delay, so the figure may still read 199.99. |

**Hand back here (end of round 2).** The agent verifies every file (and the key policy by script),
writes `VERIFICATION.md`, the register v2 rows (R6-D9) and the worklog entry.

### Step 11 — Tests, then the secret scan and the old-ID guard (round 3, workstation only)

Run only after the agent's verification of round 2, so the folder is final. The tests run first and
quietly (`-q`); the scan runs last (R5 lesson).

PowerShell (`deactivate` first if `.venv-lint` is active):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R6"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_old_id_guard.py tests/test_evidence_protocol_scaffold.py } 2>&1 | Out-File -Encoding utf8 "$E\R6_11_pytest.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R6_11_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R6_11_secret-scan.txt"
Get-Content "$E\R6_11_pytest.txt" -Tail 1; Get-Content "$E\R6_11_old-id-guard.txt", "$E\R6_11_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R6_11_pytest.txt` | First line `Python 3.10.…`; last line `179 passed` (the agent's run under Python 3.10.12, before round 2) with no `failed`, `error` or `skipped`; the agent gives the final figure at hand-back if round 2 changes it |
| `R6_11_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R6_11_secret-scan.txt` | `CLEAN: …R6`; `exit=0` |

If the scan refuses: do not edit any file; remove the refused output files and report it; the agent
writes `STEPS_fix1.md` (R5 step 13 pattern).

Then commit, and confirm R6 in session.

## CloudShell fallback

Only if the workstation sign-in fails. Use the **eu-north-1** CloudShell, `mkdir -p ~/R6 && cd ~/R6`,
and translate each PowerShell line: drop `--profile po-r1`; replace
`2>&1 | Out-File -Encoding utf8 "$E\<file>"` with `> <file> 2>&1`. For 03b use
`for k in $(aws kms list-keys --region eu-north-1 --query 'Keys[].KeyId' --output text); do aws kms describe-key --region eu-north-1 --key-id "$k" --query 'KeyMetadata.{KeyId:KeyId,KeyManager:KeyManager,KeyState:KeyState,KeySpec:KeySpec,MultiRegion:MultiRegion,Description:Description}' --output json; done | jq -s . > R6_03_keys-detail-before.json`;
for 03c use `{ aws cloudformation describe-stacks --region eu-north-1 --stack-name proposal-orchestrator-kms --output json; echo "exit=$?"; } > R6_03_kms-stack-before.txt 2>&1`;
in 03d quote the query with single quotes outside and backticks inside:
`--query 'Exports[?starts_with(Name, `proposal-orchestrator-`)].{name:Name,value:Value,stack:ExportingStackId}'`.
Bring the files home by zip as in R2 (`cd ~ && zip -r R6_evidence.zip R6`, download,
`Expand-Archive`, copy into this folder).

## Before you hand back

- [ ] Every evidence file of the round exists in this folder, under exactly its name.
- [ ] You opened each file and checked that it holds no secret value, key or token.
- [ ] You reported each step in session (UTC time, any deviation, any error). The agent keeps
      `RUNLOG.md` from your reports.
