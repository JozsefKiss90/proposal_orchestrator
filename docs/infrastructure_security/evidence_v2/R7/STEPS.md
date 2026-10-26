# R7 — Audit and storage stack (trail, trail bucket, deploy bucket, flow logs): step sheet

| Field | Value |
|---|---|
| Ticket | `R7` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R7, as read in `plans/aws_redeployment_r7_handoff_2026-10-26.md` §3 |
| Decisions applied | OD1-r1 eu-north-1; OD6-r3 (stacks, change sets, guards, derived bucket names, outputs contract); OD11-r2 (admin = AccountFullAccessRole); R4-D3 (S3 gateway endpoint policy, unchanged); R5-D1 (`bundles/` read only), R5-D2, R5-D4 (flow-log group name, flow-logs role); R6-D2 (trail name and home Region), R6-D3 (runtime decrypt via S3), R6-D5, R6-D10 (no S3 Bucket Key on the trail bucket); R1-D2 session-start check; OD10 Free plan, no upgrade. The operator's answers of 2026-10-26 to the R7 handoff §4 points and to points 11–16 added by the agent (below); they go into `aws-redeployment-r7-audit_2026-10-26` after round 1 |
| Written by / on | agent (Claude) / 2026-10-26 |
| Account / region | `797661577394` / `eu-north-1`. Every `s3api`, `cloudtrail`, `logs`, `ec2`, `bedrock`, `kms` and `cloudformation` command names `--region eu-north-1` |
| IDs taken from | Round 1: `evidence_v2/R4/R4_outputs.json` (VPC, subnet), `R5/R5_outputs.json` (flow-logs role, runtime role), `R6/R6_outputs.json` (key), checked against the live export list (step 03h). From step 06 on: `R7_outputs.json` |
| Controls touched | DC-08 (flow logs), DC-23 (trail with the CMK), DC-24 (log-file validation), DC-25 (trail bucket secured), DC-27 (trail-bucket lifecycle), DC-28 (invocation logging unset), DC-29 (no `/aws/bedrock` log group), DC-30 (log groups: CMK, ≤ 90-day retention); DC-19 note (CloudTrail and CloudWatch Logs grants exercised). DC-26 waits for R11 |
| Cost created | **No hourly cost.** Once the stack exists: S3 storage of the trail logs and the bundles, CloudWatch Logs ingestion and storage of the flow logs, and KMS requests (no Bucket Key on the trail bucket) are billed by usage from credits. The first copy of management events in CloudTrail is free. No figure is quoted until checked on the pricing pages. **Round 1 creates nothing.** |

## Settled with the operator (2026-10-26, "1–16 a, 2 = 2a igen + 2b (b), 3 (b), 5 (a) 600 s")

1. **Trail bucket encryption:** default SSE-KMS with `KeyArn`, `BucketKeyEnabled: false` (R6-D10); the trail's own `KmsKeyId` = `KeyArn`.
2. **Deny unencrypted objects.** 2a: the trail bucket keeps the v1 statement (deny `s3:PutObject` when
   `s3:x-amz-server-side-encryption` is not `aws:kms`). 2b (b): the deploy bucket gets an `…IfExists`
   deny instead: a PUT that sends an encryption header must send `aws:kms` and exactly `KeyArn`; a PUT
   without headers gets the bucket default (the CMK). Exact condition keys and header format are checked
   on the S3 reference pages before writing.
3. **Deploy bucket policy (b):** deny insecure transport; deny any principal outside the account; for
   the runtime role (`aws:PrincipalArn` = imported `RuntimeRoleArn`) a deny of every S3 action except
   `s3:GetObject`, `s3:ListBucket`, `s3:GetBucketLocation`, and of `s3:GetObject` outside `bundles/*`.
   No Allow statement (same-account access comes from R5's identity policy). `BucketKeyEnabled: true`
   on the deploy bucket.
4. **Retention:** `DeletionPolicy` / `UpdateReplacePolicy: Retain` on both buckets and the log group;
   the trail and the flow log go with the stack. The audit stack is not deleted.
5. **Flow logs (a), 600 s:** one flow log on the VPC (covers every subnet, now and later), traffic
   type `ALL`, destination CloudWatch Logs `/proposal-orchestrator/vpc-flow-logs`,
   `DeliverLogsPermissionArn` = `FlowLogsRoleArn`, default record format,
   `MaxAggregationInterval: 600`.
6. **Trail:** `proposal-orchestrator-bedrock-trail`, single-Region, home eu-north-1,
   `IncludeGlobalServiceEvents: true`, `EnableLogFileValidation: true`, `IsLogging: true`, S3 key
   prefix `cloudtrail/${ProjectName}`, `DependsOn` the trail bucket policy, no `EventSelectors`
   property (default: management events All, no data events).
7. **Trail-bucket lifecycle:** prefix `cloudtrail/${ProjectName}/`, 90 days → `GLACIER_IR`, expiry 365
   days, noncurrent versions expire after 30 days (total retention about 395 days).
8. **Tests and guard:** `tests/test_aws_audit_template.py` pins the stack's shape; the guard changes only
   if a reference page shows an untaggable type.
9. **Evidence:** the handoff §4 list for both buckets, policies compared with the template by script;
   delivery (trail object, flow-log stream, `DeliverLogsStatus`) may need a later session. A flow-log
   delivery `FAILED` is the R5-D4 known gap: stop, successor record, UPDATE of the iam stack.
10. **Register v2:** DC-08, DC-23–DC-25, DC-27–DC-30 `VERIFIED_PASS` once delivery is shown; DC-19
    note updated; DC-26 stays with R11.
11. The audit stack also imports `proposal-orchestrator-network-VpcId`; `outputs_contract.json` adds
    R7 to its consumers, and the contract test follows.
12. Both buckets set `OwnershipControls` `BucketOwnerEnforced` explicitly (checked on the CloudTrail
    page before writing).
13. Deploy-bucket lifecycle: noncurrent versions expire after 30 days, incomplete multipart uploads
    abort after 7 days; current versions do not expire.
14. DC-30 covers every log group in eu-north-1 (step 03c lists all of them).
15. DC-24 is also evidenced by one `aws cloudtrail validate-logs` run in the delivery round.
16. The trail bucket does **not** pin the KMS key id in its deny (v1 statement only).
17. (added after round 1b, operator "17 a", 2026-10-26 ~17:39 UTC) Round 2 tests the deploy bucket's
    encryption denies with three test uploads by the admin role under `bundles/` (no header: accepted with
    the CMK; `AES256`: refused; `aws:kms` without key id: refused), then removes the accepted object's
    version (R7-D17).
18. (added after round 2, operator "18a", 2026-10-26 ~17:55 UTC) DC-08 is verified on configuration
    (flow log `ACTIVE` / `SUCCESS` on the VPC, `ALL`, to the CMK group); the register note records that
    delivered records, and with them the R5-D4 known gap, are shown by R11, when the VPC first has a
    network interface (R7-D18).

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
    reads the CloudFormation reference pages, fills `deploy/aws/templates/40-audit.yaml`, updates the
    outputs contract (point 11), writes `tests/test_aws_audit_template.py` and the decision record
    `aws-redeployment-r7-audit_2026-10-26`, and adds steps 04–05 to this sheet.
  - **Round 1b: steps 04–05** (lint, guards, tests, change set). Hand back; both read the change set;
    the operator gives the go.
  - **Round 2:** execute, outputs, read-only evidence, policy comparison, credits.
  - **Round 3 (may be a later session):** delivery evidence (trail objects, digest, `validate-logs`,
    flow-log stream), then tests, the old-ID guard and the scan over the finished folder, commit.

---

## Steps

### Step 01 — Session-start check: credits, budget, alert states (R1-D2)

What it does: confirms that the Free plan is active, the credits are intact and no budget alert is in
`ALARM`, before anything else runs.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_01_budget-notifications.json"
Get-Content "$E\R7_01_plan-state.json", "$E\R7_01_budgets.json", "$E\R7_01_budget-notifications.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_01_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `199.00` (R6 left 199.99, `R6_10_plan-state-after.json`; the key's monthly fee may have started to show — the figure is recorded either way); `accountPlanExpirationDate` starts `2027-04-19` |
| `R7_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` = `10.0`, `spend` < `8.5` |
| `R7_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` = `OK` |

**STOP rule.** If the plan is not `ACTIVE`, the credits are below 199.00 USD, or any notification is in
`ALARM`, stop here and report it.

### Step 02 — Who is calling

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_02_caller-identity.json"
Get-Content "$E\R7_02_caller-identity.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_02_caller-identity.json` | `Account` = `797661577394`; `Arn` starts with `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Any other account: stop. Nothing below may run.

### Step 03 — Read-only lookups (nothing is created)

What it does: collects, before the template is written, the facts it is written from (handoff §7a):

- **03a** the two bucket names are free. S3 bucket names are global: `head-bucket` answers `404 Not Found`
  for a free name and `403 Forbidden` for a name another account owns; `list-buckets` shows this
  account's buckets;
- **03b** no trail in eu-north-1 (organization shadow trails included);
- **03c** the log groups in eu-north-1: all of them (point 14), and explicitly none under
  `/proposal-orchestrator/` or `/aws/bedrock` (DC-29);
- **03d** no flow log in eu-north-1, and the subnets of the project VPC (DC-08 "every subnet");
- **03e** the Bedrock invocation-logging configuration, before (DC-28);
- **03f** the `proposal-orchestrator-audit` stack does not exist yet;
- **03g** the key is enabled and its policy is the R6 policy (the trail and the log group depend on it);
- **03h** the network, iam and kms exports, among them the five values the audit stack imports.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
# 03a — bucket names (an error is the expected result for both head-bucket calls)
& { aws s3api head-bucket --profile po-r1 --region eu-north-1 --bucket proposal-orchestrator-cloudtrail-797661577394; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_03_head-trail-bucket.txt"
& { aws s3api head-bucket --profile po-r1 --region eu-north-1 --bucket proposal-orchestrator-deploy-797661577394; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_03_head-deploy-bucket.txt"
aws s3api list-buckets --profile po-r1 --region eu-north-1 --query "Buckets[].{name:Name,created:CreationDate}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_buckets-before.json"
# 03b — trails
aws cloudtrail describe-trails --profile po-r1 --region eu-north-1 --include-shadow-trails --query "trailList[].{name:Name,arn:TrailARN,home:HomeRegion,org:IsOrganizationTrail,multi:IsMultiRegionTrail,bucket:S3BucketName}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_trails-before.json"
# 03c — log groups: all, then the two prefixes
aws logs describe-log-groups --profile po-r1 --region eu-north-1 --query "logGroups[].{name:logGroupName,kms:kmsKeyId,retention:retentionInDays}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_log-groups-before.json"
aws logs describe-log-groups --profile po-r1 --region eu-north-1 --log-group-name-prefix /proposal-orchestrator/ --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_log-groups-project-before.json"
aws logs describe-log-groups --profile po-r1 --region eu-north-1 --log-group-name-prefix /aws/bedrock --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_log-groups-bedrock-before.json"
# 03d — flow logs (all in the Region) and the project VPC's subnets
aws ec2 describe-flow-logs --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_flow-logs-before.json"
aws ec2 describe-subnets --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=vpc-0f33f9ced5a78b09f --query "Subnets[].{id:SubnetId,az:AvailabilityZone,cidr:CidrBlock,vpc:VpcId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_subnets.json"
# 03e — Bedrock model invocation logging (expected: no configuration)
& { aws bedrock get-model-invocation-logging-configuration --profile po-r1 --region eu-north-1 --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_03_invocation-logging-before.txt"
# 03f — the audit stack must not exist yet (an error here is the expected result)
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_03_audit-stack-before.txt"
# 03g — the key: state and policy
aws kms describe-key --profile po-r1 --region eu-north-1 --key-id arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561 --query "KeyMetadata.{KeyId:KeyId,Arn:Arn,KeyState:KeyState,KeyManager:KeyManager,KeySpec:KeySpec,MultiRegion:MultiRegion}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_key-before.json"
aws kms get-key-policy --profile po-r1 --region eu-north-1 --key-id arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561 --policy-name default --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_key-policy-before.json"
# 03h — project exports (network, iam, kms)
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-')].{name:Name,value:Value,stack:ExportingStackId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_03_exports.json"
Get-ChildItem "$E\R7_03_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R7_03_head-trail-bucket.txt` | Contains `(404)` and `Not Found`; last line `exit=254` |
| `R7_03_head-deploy-bucket.txt` | Contains `(404)` and `Not Found`; last line `exit=254` |
| `R7_03_buckets-before.json` | A JSON list (may be empty). No `name` starts with `proposal-orchestrator-`. Any other bucket is **not** a FAIL: report it; the agent records it |
| `R7_03_trails-before.json` | `[]`. Any trail is reported; a trail named `proposal-orchestrator-bedrock-trail` is a STOP |
| `R7_03_log-groups-before.json` | `[]` (as `R1_36_log-groups-after.json`). Any group is **not** a FAIL by itself: report it; under point 14 it falls under DC-30 and we decide |
| `R7_03_log-groups-project-before.json` | `logGroups` = `[]` |
| `R7_03_log-groups-bedrock-before.json` | `logGroups` = `[]` |
| `R7_03_flow-logs-before.json` | `FlowLogs` = `[]` |
| `R7_03_subnets.json` | Exactly one entry: `id` = `subnet-018cd285bbe5cbdaf`, `az` = `eu-north-1a`, `cidr` = `10.60.0.0/25`, `vpc` = `vpc-0f33f9ced5a78b09f` (`R4_outputs.json`) |
| `R7_03_invocation-logging-before.txt` | Last line `exit=0`; no `loggingConfig` key in the file (the body is `{}` or empty) |
| `R7_03_audit-stack-before.txt` | Contains `ValidationError` and `does not exist` for `proposal-orchestrator-audit` (the name may wrap); last line `exit=254` |
| `R7_03_key-before.json` | `Arn` = the `KeyArn` of `R6_outputs.json`; `KeyState` = `Enabled`; `KeyManager` = `CUSTOMER`; `KeySpec` = `SYMMETRIC_DEFAULT`; `MultiRegion` = `false` |
| `R7_03_key-policy-before.json` | `PolicyName` = `default`; the `Policy` string equals the one in `R6/R6_08_key-policy.json` (agent compares by script: same five statements by `Sid`) |
| `R7_03_exports.json` | Exactly 17 names: seven `proposal-orchestrator-network-*`, seven `proposal-orchestrator-iam-*`, three `proposal-orchestrator-kms-*`; none starts `proposal-orchestrator-audit-`. Values equal to the outputs files: `network-VpcId` = `vpc-0f33f9ced5a78b09f`, `network-PrivateSubnetId` = `subnet-018cd285bbe5cbdaf`, `iam-FlowLogsRoleArn` = `arn:aws:iam::797661577394:role/proposal-orchestrator-flow-logs-role`, `iam-RuntimeRoleArn` = `arn:aws:iam::797661577394:role/proposal-orchestrator-runtime-role`, `kms-KeyArn` = `arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561` |

**STOP rule.** If either bucket name answers anything other than `404` (a `403` means another account
owns the name), a trail named `proposal-orchestrator-bedrock-trail` or a `/proposal-orchestrator/` or
`/aws/bedrock` log group exists, a flow log exists, invocation logging is configured, the audit stack
exists, an `proposal-orchestrator-audit-*` export exists, the key is not `Enabled` or its policy differs
from R6, or one of the five import values is missing or differs: stop and report. Nothing is written
over an occupied name, a changed key policy or a missing import.

**Hand back here (end of round 1).** Report steps 01–03 in session (UTC times, any deviation). The agent
checks every file in the device shell (criteria, key-policy comparison, secret scan, old-ID guard), then
writes the template, the test, the decision record and steps 04–05 below.

---

## CloudShell fallback (round 1)

Only if PowerShell is unavailable. In CloudShell (eu-north-1), drop `--profile po-r1`, and replace each
`… 2>&1 | Out-File -Encoding utf8 "$E\<file>"` with `… > <file> 2>&1`; for the four lines wrapped in
`& { …; "exit=$LASTEXITCODE" }`, use `{ <command>; echo "exit=$?"; } > <file> 2>&1`. The `--query`
strings and `--filters` work unchanged inside single quotes. Download the files into
`docs\infrastructure_security\evidence_v2\R7\` before handing back.

---

*Round 1 done 2026-10-26 (~17:22 UTC): all eighteen files PASS (agent's check in the device shell; key policy equal to `R6_08_key-policy.json` statement by statement; secret scan and old-ID guard CLEAN). Findings F-R7-1 and F-R7-2 of `aws-redeployment-r7-audit_2026-10-26`.*

### Step 04 — Lint, guards and tests on the filled template (workstation only, no AWS call)

What it does: proves, before anything is created, that `40-audit.yaml` lints for eu-north-1, keeps the
template rules, carries no old-account id, and has the shape `tests/test_aws_audit_template.py` pins
(decision record `aws-redeployment-r7-audit_2026-10-26`, R7-D1 to R7-D16); and that the contract test
accepts the changed consumers of `VpcId` and `PrivateSubnetId` (R7-D11). Run `deactivate` first if
`.venv-lint` is active (lint still runs through its own executable). Pytest runs with `-q`.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_04_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_04_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_04_old-id-guard.txt"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_old_id_guard.py } 2>&1 | Out-File -Encoding utf8 "$E\R7_04_pytest.txt"
Get-Content "$E\R7_04_cfn-lint.txt", "$E\R7_04_template-guard.txt", "$E\R7_04_old-id-guard.txt"; Get-Content "$E\R7_04_pytest.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R7_04_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R7_04_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R7_04_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R7_04_pytest.txt` | First line `Python 3.10.…`; last line `177 passed` (the agent's run under Python 3.10.12) with no `failed`, `error` or `skipped` |

**STOP rule.** Any non-zero exit or failed test: stop. The template is not deployed until this step is
clean.

### Step 05 — Create the change set and read it (nothing is created yet)

What it does: asks CloudFormation to plan the audit stack. A change set of type CREATE builds nothing
until it is executed. **No `--capabilities`:** the stack holds no IAM resource and no macro (if
CloudFormation asks for one anyway, `create-change-set` fails with `InsufficientCapabilities`: stop and
hand back). The four `Fn::ImportValue` references (`kms-KeyArn`, `network-VpcId`, `iam-FlowLogsRoleArn`,
`iam-RuntimeRoleArn`) are resolved here: a missing export would fail the change set.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit --change-set-name r7-create-01 --change-set-type CREATE --template-body file://deploy/aws/templates/40-audit.yaml --parameters file://deploy/aws/parameters/audit.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_05_create-change-set.json"
Get-Content "$E\R7_05_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit --change-set-name r7-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit --change-set-name r7-create-01 --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_05_change-set.json"
Get-Content "$E\R7_05_change-set.json"
```

If `create-change-set` itself returns an error, or `wait` reports a terminal failure, still run the
`describe-change-set` line: `Status` and `StatusReason` in `R7_05_change-set.json` are the evidence.
Then stop and hand back.

| Evidence file | PASS criterion |
|---|---|
| `R7_05_create-change-set.json` | `Id` starts `arn:aws:cloudformation:eu-north-1:797661577394:changeSet/r7-create-01/`; `StackId` starts `arn:aws:cloudformation:eu-north-1:797661577394:stack/proposal-orchestrator-audit/` |
| `R7_05_change-set.json` | `Status` = `CREATE_COMPLETE`; `ExecutionStatus` = `AVAILABLE`; `Capabilities` absent or `[]`; `Tags` = `[{project: proposal-orchestrator}]`; `Parameters` show exactly `ExpectedAccountId` 797661577394, `ExpectedRegion` eu-north-1 and `ProjectName` proposal-orchestrator; `Changes` holds **exactly seven** entries, each `ResourceChange.Action` = `Add`: `TrailBucket` (`AWS::S3::Bucket`), `TrailBucketPolicy` (`AWS::S3::BucketPolicy`), `Trail` (`AWS::CloudTrail::Trail`), `DeployBucket` (`AWS::S3::Bucket`), `DeployBucketPolicy` (`AWS::S3::BucketPolicy`), `FlowLogGroup` (`AWS::Logs::LogGroup`), `VpcFlowLog` (`AWS::EC2::FlowLog`). Nothing else. The CREATE type is evidenced by the command line, by `R7_03_audit-stack-before.txt` and by the seven `Add` entries |

**Hand back here (end of round 1b).** Report steps 04–05 in session. Both of us read
`R7_05_change-set.json` against the criterion. **Step 06 runs only after you have confirmed in session
that the change set lists exactly those seven resources and given the go.** Executing it starts
usage-based charges (S3 storage, log ingestion, KMS requests) from credits, and creates two buckets and
a log group that are retained: if the creation fails and rolls back, the retained resources may remain
and are handled by a follow-up step sheet, never by hand. If the change set itself failed (for example an
organization policy refusing an S3, CloudTrail or Logs action), the agent records the error verbatim in
`RUNLOG.md` and a successor decision is settled before the template changes; nothing is executed. The
agent adds steps 06 onward after the go.

*Round 1b done 2026-10-26 (~17:37 UTC): steps 04–05 PASS; change set `r7-create-01` read by both (seven `Add`). **Operator's go in session: 2026-10-26 ~17:39 UTC ("go 06"), together with point 17 "a".***

### Step 06 — Execute the change set (creates the seven resources; usage-based charges start)

**Only after the operator's go in session on `R7_05_change-set.json` (given 2026-10-26).** What it does:
creates the seven resources of the change set, and nothing else. CloudFormation creates the buckets and
the log group first, then the bucket policies, then the trail (`DependsOn`) and the flow log. This is
where CloudTrail checks the bucket policy and the key (R6-D10) and S3 checks the deploy bucket policy
(`NotResource`, R7-D3 known gap).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
& { aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit --change-set-name r7-create-01; "execute exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_06_execute-exit.txt"
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_06_stack-status.json"
aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_06_stack-events.json"
Get-Content "$E\R7_06_execute-exit.txt", "$E\R7_06_stack-status.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_06_execute-exit.txt` | `execute exit=0` and no error line |
| `R7_06_stack-status.json` | `status` = `CREATE_COMPLETE`; `capabilities` null or `[]`; `tags` hold `project` = `proposal-orchestrator` |
| `R7_06_stack-events.json` | The seven logical ids and the stack `proposal-orchestrator-audit` each reach `CREATE_COMPLETE`; no `*_FAILED` and no `ROLLBACK` status anywhere |

**STOP rule.** On a rollback or any `*_FAILED` event: stop, report it (the `reason` of the first failed
event matters most), and **do not delete the stack or any bucket**. The two buckets and the log group are
retained by `DeletionPolicy: Retain` and may still exist after a rollback; the agent then writes
`STEPS_fix1.md`. A trail failure that names KMS is the R6-D10 case (successor record, UPDATE of the kms
stack first).

### Step 07 — Save the stack outputs (ids for every later step and ticket)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-audit --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_outputs.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-audit-')]" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_07_exports.json"
aws cloudformation list-imports --profile po-r1 --region eu-north-1 --export-name proposal-orchestrator-network-VpcId --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_07_imports-vpcid.json"
Get-Content "$E\R7_outputs.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_outputs.json` | Exactly the six contract keys, each with `ExportName` `proposal-orchestrator-audit-<Key>`: `TrailBucketName` = `proposal-orchestrator-cloudtrail-797661577394`; `DeployBucketName` = `proposal-orchestrator-deploy-797661577394`; `TrailArn` = `arn:aws:cloudtrail:eu-north-1:797661577394:trail/proposal-orchestrator-bedrock-trail` (R6-D2); `FlowLogGroupName` = `/proposal-orchestrator/vpc-flow-logs`; `FlowLogGroupArn` = `arn:aws:logs:eu-north-1:797661577394:log-group:/proposal-orchestrator/vpc-flow-logs:*`; `FlowLogId` starts `fl-` |
| `R7_07_exports.json` | The same six export names and values, `ExportingStackId` the audit stack of step 05 |
| `R7_07_imports-vpcid.json` | `Imports` = `["proposal-orchestrator-audit"]` (R7-D11) |

### Step 08 — Read-only evidence of what was created (ids from `R7_outputs.json` only)

What it does: records, for both buckets, encryption, Block Public Access, versioning, Object Ownership,
policy, lifecycle and tags (DC-25, DC-27, exit condition 1); the trail, its status and selectors (DC-23,
DC-24, exit condition 2); every log group (DC-30); the flow log (DC-08, exit condition 3); and the
invocation-logging configuration after R7 (DC-28, DC-29, exit condition 4). The agent compares both
bucket policies with the template by script (intrinsics resolved with the parameter file and the
round-1 exports), statement by statement.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
$O = Get-Content "$E\R7_outputs.json" -Raw | ConvertFrom-Json
$TB = ($O | Where-Object OutputKey -eq 'TrailBucketName').OutputValue
$DB = ($O | Where-Object OutputKey -eq 'DeployBucketName').OutputValue
$TA = ($O | Where-Object OutputKey -eq 'TrailArn').OutputValue
$FL = ($O | Where-Object OutputKey -eq 'FlowLogId').OutputValue
"TrailBucket=$TB"; "DeployBucket=$DB"; "TrailArn=$TA"; "FlowLogId=$FL"
foreach ($b in @(@{n=$TB; t="trail-bucket"}, @{n=$DB; t="deploy-bucket"})) {
  aws s3api get-bucket-encryption --profile po-r1 --region eu-north-1 --bucket $b.n --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_$($b.t)-encryption.json"
  aws s3api get-public-access-block --profile po-r1 --region eu-north-1 --bucket $b.n --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_$($b.t)-public-access-block.json"
  aws s3api get-bucket-versioning --profile po-r1 --region eu-north-1 --bucket $b.n --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_$($b.t)-versioning.json"
  aws s3api get-bucket-ownership-controls --profile po-r1 --region eu-north-1 --bucket $b.n --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_$($b.t)-ownership.json"
  aws s3api get-bucket-policy --profile po-r1 --region eu-north-1 --bucket $b.n --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_$($b.t)-policy.json"
  aws s3api get-bucket-lifecycle-configuration --profile po-r1 --region eu-north-1 --bucket $b.n --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_$($b.t)-lifecycle.json"
  aws s3api get-bucket-tagging --profile po-r1 --region eu-north-1 --bucket $b.n --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_$($b.t)-tags.json"
}
aws cloudtrail describe-trails --profile po-r1 --region eu-north-1 --trail-name-list $TA --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_trail.json"
aws cloudtrail get-trail-status --profile po-r1 --region eu-north-1 --name $TA --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_trail-status.json"
aws cloudtrail get-event-selectors --profile po-r1 --region eu-north-1 --trail-name $TA --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_trail-event-selectors.json"
aws cloudtrail list-tags --profile po-r1 --region eu-north-1 --resource-id-list $TA --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_trail-tags.json"
aws logs describe-log-groups --profile po-r1 --region eu-north-1 --query "logGroups[].{name:logGroupName,arn:arn,kms:kmsKeyId,retention:retentionInDays,klass:logGroupClass}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_log-groups.json"
aws ec2 describe-flow-logs --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_flow-logs.json"
aws ec2 describe-subnets --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=vpc-0f33f9ced5a78b09f --query "Subnets[].{id:SubnetId,vpc:VpcId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_subnets.json"
& { aws bedrock get-model-invocation-logging-configuration --profile po-r1 --region eu-north-1 --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_08_invocation-logging-after.txt"
aws logs describe-log-groups --profile po-r1 --region eu-north-1 --log-group-name-prefix /aws/bedrock --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_08_log-groups-bedrock-after.json"
Get-Content "$E\R7_08_trail.json", "$E\R7_08_trail-status.json", "$E\R7_08_log-groups.json", "$E\R7_08_flow-logs.json", "$E\R7_08_invocation-logging-after.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_08_trail-bucket-encryption.json` | One rule: `SSEAlgorithm` `aws:kms`, `KMSMasterKeyID` = the round-1 `KeyArn`, `BucketKeyEnabled` false (R6-D10, R7-D1) |
| `R7_08_deploy-bucket-encryption.json` | One rule: `SSEAlgorithm` `aws:kms`, `KMSMasterKeyID` = `KeyArn`, `BucketKeyEnabled` true (R7-D3) |
| `R7_08_*-public-access-block.json` (2) | All four settings true |
| `R7_08_*-versioning.json` (2) | `Status` = `Enabled` |
| `R7_08_*-ownership.json` (2) | One rule, `ObjectOwnership` = `BucketOwnerEnforced` (R7-D12) |
| `R7_08_trail-bucket-policy.json` | The four statements of the template with ARNs resolved for this account and Region, nothing else (agent's script; R7-D2 2a) |
| `R7_08_deploy-bucket-policy.json` | The eight deny statements of the template, `RuntimeRoleArn` and `KeyArn` resolved, nothing else (agent's script; R7-D2 2b, R7-D3) |
| `R7_08_trail-bucket-lifecycle.json` | One enabled rule on prefix `cloudtrail/proposal-orchestrator/`: transition 90 days `GLACIER_IR`, expiration 365 days, noncurrent 30 days (DC-27) |
| `R7_08_deploy-bucket-lifecycle.json` | One enabled rule, no prefix: noncurrent 30 days, abort incomplete multipart after 7 days, no current-version expiration (R7-D13) |
| `R7_08_*-tags.json` (2) | `Name` = the bucket name and `project` = `proposal-orchestrator` (CloudFormation may add `aws:cloudformation:*` tags) |
| `R7_08_trail.json` | One trail: `Name` `proposal-orchestrator-bedrock-trail`, `TrailARN` = `TrailArn`, `HomeRegion` `eu-north-1`, `IsMultiRegionTrail` false, `IncludeGlobalServiceEvents` true, `LogFileValidationEnabled` true, `KmsKeyId` = `KeyArn`, `S3BucketName` = trail bucket, `S3KeyPrefix` `cloudtrail/proposal-orchestrator`, `IsOrganizationTrail` false (DC-23, DC-24) |
| `R7_08_trail-status.json` | `IsLogging` true. Delivery fields may still be empty here; they are round 3's |
| `R7_08_trail-event-selectors.json` | One selector: `ReadWriteType` `All`, `IncludeManagementEvents` true, `DataResources` `[]` (R7-D6) |
| `R7_08_trail-tags.json` | `Name` and `project` tags on the trail |
| `R7_08_log-groups.json` | Exactly one group: `/proposal-orchestrator/vpc-flow-logs`, `kms` = `KeyArn`, `retention` 90 (DC-30, R7-D14) |
| `R7_08_flow-logs.json` | Exactly one flow log: `FlowLogId` = `FlowLogId`, `ResourceId` `vpc-0f33f9ced5a78b09f`, `TrafficType` `ALL`, `LogDestinationType` `cloud-watch-logs`, `LogGroupName` `/proposal-orchestrator/vpc-flow-logs`, `DeliverLogsPermissionArn` the flow-logs role, `MaxAggregationInterval` 600, `FlowLogStatus` `ACTIVE`; `DeliverLogsStatus` not `FAILED` (DC-08) |
| `R7_08_subnets.json` | Exactly `subnet-018cd285bbe5cbdaf` in that VPC (the flow log on the VPC covers it) |
| `R7_08_invocation-logging-after.txt` | Last line `exit=0`; no `loggingConfig` (DC-28) |
| `R7_08_log-groups-bedrock-after.json` | `logGroups` = `[]` (DC-29) |

**STOP rule.** `DeliverLogsStatus` = `FAILED` (with its `DeliverLogsErrorMessage`) is the R5-D4 known gap:
report it; the agent writes the successor and the iam UPDATE. Any other difference: report it; nothing
is changed by hand.

### Step 09 — Test the deploy bucket's encryption denies (R7-D17; writes and then removes one object)

What it does: the admin role puts the same small file three times under `bundles/`. Expected: (a) no
encryption header → accepted, encrypted with the CMK and the Bucket Key (the bucket default); (b)
`AES256` → `AccessDenied` (`DenyEncryptionHeaderOtherThanKms`); (c) `aws:kms` without a key id →
`AccessDenied` (`DenyKmsHeaderWithoutKeyId`; S3 would otherwise use the AWS managed key). Then the
accepted object's version is deleted by its version id, so no object and no delete marker remain. The
test file is written to your temp folder, not into the repository; it holds the fixed text
`R7_SSE_TEST` only.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
$O = Get-Content "$E\R7_outputs.json" -Raw | ConvertFrom-Json
$DB = ($O | Where-Object OutputKey -eq 'DeployBucketName').OutputValue
$F = Join-Path $env:TEMP "r7-sse-test.txt"
Set-Content -Path $F -Value "R7_SSE_TEST" -Encoding ascii -NoNewline
# 09a — no encryption header (expected: accepted)
aws s3api put-object --profile po-r1 --region eu-north-1 --bucket $DB --key bundles/r7-sse-test-default.txt --body $F --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_09_put-default.json"
aws s3api head-object --profile po-r1 --region eu-north-1 --bucket $DB --key bundles/r7-sse-test-default.txt --query "{sse:ServerSideEncryption,key:SSEKMSKeyId,bucketKey:BucketKeyEnabled,version:VersionId,length:ContentLength}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_09_head-default.json"
# 09b — SSE-S3 header (expected: AccessDenied)
& { aws s3api put-object --profile po-r1 --region eu-north-1 --bucket $DB --key bundles/r7-sse-test-aes256.txt --body $F --server-side-encryption AES256 --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_09_put-aes256.txt"
# 09c — aws:kms without a key id (expected: AccessDenied)
& { aws s3api put-object --profile po-r1 --region eu-north-1 --bucket $DB --key bundles/r7-sse-test-kms-nokey.txt --body $F --server-side-encryption aws:kms --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_09_put-kms-nokey.txt"
# 09d — remove the accepted object's version, then list what is left under the test prefix
$V = (Get-Content "$E\R7_09_put-default.json" -Raw | ConvertFrom-Json).VersionId
"VersionId=$V"
aws s3api delete-object --profile po-r1 --region eu-north-1 --bucket $DB --key bundles/r7-sse-test-default.txt --version-id $V --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_09_delete-version.json"
aws s3api list-object-versions --profile po-r1 --region eu-north-1 --bucket $DB --prefix bundles/r7-sse-test --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_09_versions-after.json"
Remove-Item $F
Get-Content "$E\R7_09_put-default.json", "$E\R7_09_head-default.json", "$E\R7_09_put-aes256.txt", "$E\R7_09_put-kms-nokey.txt", "$E\R7_09_versions-after.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_09_put-default.json` | An `ETag` and a `VersionId`; `ServerSideEncryption` `aws:kms`; `SSEKMSKeyId` = `KeyArn`; `BucketKeyEnabled` true |
| `R7_09_head-default.json` | `sse` `aws:kms`; `key` = `KeyArn`; `bucketKey` true; `version` = the `VersionId` above; `length` 11 |
| `R7_09_put-aes256.txt` | Contains `AccessDenied`; last line `exit=254` |
| `R7_09_put-kms-nokey.txt` | Contains `AccessDenied`; last line `exit=254` |
| `R7_09_delete-version.json` | `VersionId` = the `VersionId` above; no `DeleteMarker` true |
| `R7_09_versions-after.json` | No `Versions` and no `DeleteMarkers` (or both empty) |

**STOP rule.** If 09a is refused, or 09b or 09c is accepted: stop after 09d (still remove any accepted
object by its version id, with the same `delete-object` line and the `VersionId` its `put-object` printed),
report it; the agent writes the successor record and the policy UPDATE.

### Step 10 — Session-end credits (read-only)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_10_plan-state-after.json"
Get-Content "$E\R7_10_plan-state-after.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_10_plan-state-after.json` | `FREE` / `ACTIVE`; credits ≥ `199.00`. Usage charges are billed with a delay, so the figure may still read 199.99. |

**Hand back here (end of round 2).** The agent verifies every file (both bucket policies by script),
and adds the delivery round (round 3, at least one hour after step 06: trail log and digest objects
under the prefix, `get-trail-status` delivery times, `validate-logs`; flow-log delivery status), then
the closing scan, test and commit step.

*Round 2 done 2026-10-26 (~17:47 UTC): steps 06–10 PASS (agent's check: 36 criteria, both bucket policies equal the resolved template statement by statement; secret scan and old-ID guard CLEAN). Finding F-R7-8.*

## Round 3 — delivery (run no earlier than 2026-10-26 18:50 UTC, i.e. 19:50 Budapest)

The trail started logging at 17:44:09 UTC (`R7_08_trail-status.json`). CloudTrail delivers log files
about every five minutes and a digest file about every hour, so this round runs at least one hour after
that time, in this session or a later one. Start a new session with step 01's credit check if the
sign-in has expired.

### Step 11 — Trail delivery and log-file integrity (DC-23, DC-24, DC-25; read-only)

What it does: shows that the trail writes log and digest files under its prefix, encrypted with the CMK
(exit condition 2), and that `validate-logs` verifies them (R7-D15). Object keys hold only the account,
Region, date and a file id. The flow log is read again: the VPC has no network interface before R11, so
no log stream is expected yet; only the status matters here.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
$O = Get-Content "$E\R7_outputs.json" -Raw | ConvertFrom-Json
$TB = ($O | Where-Object OutputKey -eq 'TrailBucketName').OutputValue
$TA = ($O | Where-Object OutputKey -eq 'TrailArn').OutputValue
$FL = ($O | Where-Object OutputKey -eq 'FlowLogId').OutputValue
$START = (Get-Content "$E\R7_08_trail-status.json" -Raw | ConvertFrom-Json).TimeLoggingStarted
"Start=$START"
aws cloudtrail get-trail-status --profile po-r1 --region eu-north-1 --name $TA --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_11_trail-status.json"
aws s3api list-objects-v2 --profile po-r1 --region eu-north-1 --bucket $TB --prefix cloudtrail/proposal-orchestrator/AWSLogs/797661577394/ --query "Contents[].{key:Key,size:Size,modified:LastModified}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_11_trail-objects.json"
$K = (Get-Content "$E\R7_11_trail-objects.json" -Raw | ConvertFrom-Json) | Where-Object { $_.key -like "*/CloudTrail/eu-north-1/*" } | Select-Object -First 1 -ExpandProperty key
$D = (Get-Content "$E\R7_11_trail-objects.json" -Raw | ConvertFrom-Json) | Where-Object { $_.key -like "*/CloudTrail-Digest/eu-north-1/*" } | Select-Object -First 1 -ExpandProperty key
"LogKey=$K"; "DigestKey=$D"
aws s3api head-object --profile po-r1 --region eu-north-1 --bucket $TB --key $K --query "{sse:ServerSideEncryption,key:SSEKMSKeyId,bucketKey:BucketKeyEnabled}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_11_log-object-encryption.json"
aws s3api head-object --profile po-r1 --region eu-north-1 --bucket $TB --key $D --query "{sse:ServerSideEncryption,key:SSEKMSKeyId,bucketKey:BucketKeyEnabled}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_11_digest-object-encryption.json"
& { aws cloudtrail validate-logs --profile po-r1 --region eu-north-1 --trail-arn $TA --start-time $START; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_11_validate-logs.txt"
aws ec2 describe-flow-logs --profile po-r1 --region eu-north-1 --flow-log-ids $FL --query "FlowLogs[].{id:FlowLogId,status:FlowLogStatus,deliver:DeliverLogsStatus,error:DeliverLogsErrorMessage}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_11_flow-log-status.json"
aws logs describe-log-streams --profile po-r1 --region eu-north-1 --log-group-name /proposal-orchestrator/vpc-flow-logs --query "logStreams[].{name:logStreamName,last:lastEventTimestamp}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_11_flow-log-streams.json"
Get-Content "$E\R7_11_trail-status.json", "$E\R7_11_log-object-encryption.json", "$E\R7_11_digest-object-encryption.json", "$E\R7_11_validate-logs.txt", "$E\R7_11_flow-log-status.json", "$E\R7_11_flow-log-streams.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_11_trail-status.json` | `IsLogging` true; `LatestDeliveryTime` and `LatestDigestDeliveryTime` set and after `TimeLoggingStarted`; no `LatestDeliveryError` and no `LatestDigestDeliveryError` (or empty) |
| `R7_11_trail-objects.json` | At least one key under `…/AWSLogs/797661577394/CloudTrail/eu-north-1/` and at least one under `…/AWSLogs/797661577394/CloudTrail-Digest/eu-north-1/`, all keys starting `cloudtrail/proposal-orchestrator/` (the prefix of the bucket policy and the lifecycle rule) |
| `R7_11_log-object-encryption.json` | `sse` `aws:kms`; `key` = `KeyArn`; `bucketKey` null or false (R6-D10, DC-23) |
| `R7_11_digest-object-encryption.json` | `sse` `aws:kms`; `key` = `KeyArn`; `bucketKey` null or false |
| `R7_11_validate-logs.txt` | Last line `exit=0`; reports at least `1/1` digest files valid and every log file found valid (`N/N log files valid`), and nothing `INVALID` (DC-24, R7-D15) |
| `R7_11_flow-log-status.json` | `status` `ACTIVE`; `deliver` `SUCCESS`; `error` null (DC-08) |
| `R7_11_flow-log-streams.json` | A JSON list: `[]` is expected (no network interface in the VPC before R11; point 18); any stream shows delivery |

**STOP rule.** A delivery error, a log object not encrypted with `KeyArn`, an `INVALID` file, or
`DeliverLogsStatus` `FAILED`: stop and report. If `validate-logs` reports no digest yet, wait a further
hour and repeat only that line; nothing else changes.

*Step 11 run 2026-10-26 ~18:57 UTC: every file PASS except the log-file half of `R7_11_validate-logs.txt`. The only digest so far (`…_20261026T174409Z.json.gz`, delivered 18:00:49 UTC) is the trail's opening digest; it covers 17:44:09 to 17:44:09 and therefore no log file. The 14 log files delivered from 17:53 UTC are covered by the next hourly digest, due shortly after 19:00 UTC. Step 11b repeats only the two lines that depend on it.*

### Step 11b — Second digest and log-file validation (run no earlier than 2026-10-26 19:10 UTC, i.e. 20:10 Budapest)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
$O = Get-Content "$E\R7_outputs.json" -Raw | ConvertFrom-Json
$TA = ($O | Where-Object OutputKey -eq 'TrailArn').OutputValue
$START = (Get-Content "$E\R7_08_trail-status.json" -Raw | ConvertFrom-Json).TimeLoggingStarted
aws cloudtrail get-trail-status --profile po-r1 --region eu-north-1 --name $TA --output json 2>&1 | Out-File -Encoding utf8 "$E\R7_11b_trail-status.json"
& { aws cloudtrail validate-logs --profile po-r1 --region eu-north-1 --trail-arn $TA --start-time $START; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_11b_validate-logs.txt"
Get-Content "$E\R7_11b_trail-status.json", "$E\R7_11b_validate-logs.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_11b_trail-status.json` | `IsLogging` true; `LatestDigestDeliveryTime` after 19:00 UTC (20:00 Budapest; the file shows local offset `+01:00`); no delivery or digest error |
| `R7_11b_validate-logs.txt` | Last line `exit=0`; `2/2 digest files valid` (or more, all valid); a line `N/N log files valid` with N ≥ 1; nothing `INVALID` (DC-24, R7-D15) |

If the second digest is not there yet (`LatestDigestDeliveryTime` still 19:00:48 Budapest), wait ten minutes and repeat the block; the files are overwritten.

**Hand back here (end of round 3).** The agent verifies the files, writes `VERIFICATION.md`, the register
v2 rows (R7-D10, as point 18 settles DC-08), the DC-19 note and the worklog entry, then step 12.

### Step 12 — Closing: tests, old-ID guard, then the secret scan over the finished folder

Runs only after the agent has written `VERIFICATION.md`, the register v2 rows and the worklog entry, so
the scan sees the final folder. Run `deactivate` first if `.venv-lint` is active. The scan runs last.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R7"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_old_id_guard.py } 2>&1 | Out-File -Encoding utf8 "$E\R7_12_pytest.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_12_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R7_12_secret-scan.txt"
Get-Content "$E\R7_12_pytest.txt" -Tail 1; Get-Content "$E\R7_12_old-id-guard.txt", "$E\R7_12_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R7_12_pytest.txt` | First line `Python 3.10.…`; last line `177 passed` with no `failed`, `error` or `skipped` |
| `R7_12_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R7_12_secret-scan.txt` | `CLEAN: docs\infrastructure_security\evidence_v2\R7` (or with forward slashes); `exit=0` |

Then commit (operator), and confirm R7 in session; the agent ticks R7 in `plans/aws_redeployment_tickets.md`.
