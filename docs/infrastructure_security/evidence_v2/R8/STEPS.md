# R8 — Runtime secret (`proposal-orchestrator/env-config`): step sheet

| Field | Value |
|---|---|
| Ticket | `R8` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R8, as read in `plans/aws_redeployment_r8_handoff_2026-10-26.md` §3 |
| Decisions applied | OD1-r1 eu-north-1; OD2 (a) one hardened runtime role; OD6-r3 (stacks, change sets, guards, outputs contract, `AdminRoleArn` and `TransportModelId` parameters); OD7-orchestrator (`eu.anthropic.claude-opus-4-6-v1`, interim); OD8 (a) the launcher reads the secret; OD11-r2 (admin = `AccountFullAccessRole`, no root user, F-OD11r2-3); R5 `RuntimeSecretRead` (identity policy and boundary, `GetSecretValue` only); R6-D3 (runtime decrypt via Secrets Manager), R6-D4 (no key-policy change; `AdminRoleArn` stays a secret-stack parameter); F-R7-7 (no simulation of a resource policy for a role); R1-D2 session-start check; OD10 Free plan, no upgrade. The operator's answers of 2026-10-26 to the R8 handoff §4 points and to points 11–16 added by the agent (below); they go into `aws-redeployment-r8-secret_2026-10-26` after round 1 |
| Written by / on | agent (Claude) / 2026-10-26 |
| Account / region | `797661577394` / `eu-north-1`. Every `secretsmanager`, `kms`, `iam` and `cloudformation` command names `--region eu-north-1`; the one `pricing` call names `--region us-east-1` (the Price List API answers only in us-east-1, eu-central-1 and ap-south-1) |
| IDs taken from | Round 1: `evidence_v2/R5/R5_outputs.json` (runtime role), `R6/R6_outputs.json` (key), `R4`/`R7` outputs for the export count, `R1/R1_00_role.json` (admin role), checked against the live export list (step 03f). From step 06 on: `R8_outputs.json` |
| Controls touched | DC-20 (secret encrypted with the CMK), DC-21 (resource policy scoped), DC-22 (rotation: NOT_APPLICABLE, point 14); notes on DC-19 (runtime grant via Secrets Manager) and DC-33–DC-35 (values stored; read on the host in R12b) |
| Cost created | **No hourly cost.** Once the stack exists, the secret is billed per month, prorated, plus API calls, from credits (point 1; the eu-north-1 figure is taken from step 03g, not quoted before). **Round 1 creates nothing**; the Price List API call is free. |

## Settled with the operator (2026-10-26, "1-16a")

1. **Cost:** proceed; the "free (secret: monthly)" case of OD6-r3, acknowledged as R6-D1 was for the key. The eu-north-1 figure comes from step 03g (point 11).
2. **Values enter through the template:** the secret's value property is a JSON object of the five keys built with `!Sub` from the parameters and pseudo parameters. The values are configuration, not credentials. Rule: the values change only by a template UPDATE, never by `put-secret-value`. Evidence uses `describe-change-set` without `--include-property-values`.
3. **Preset name (a):** `ORCHESTRATOR_TRANSPORT_PRESET` = `BEDROCK_CONVERSE_EU` (backend `bedrock_converse`, default Region eu-north-1, `eu.` profiles). A lasting rule for R9e: it implements a preset of exactly this name, with a test that the name stored by `50-secret.yaml` exists in `runner/transport/config.py`. Until then a launcher reading the secret fails closed on the unknown preset.
4. **Resource policy:** deny-only, `BlockPublicPolicy: true`, shaped by points 12 and 13. No Allow statement (same-account access comes from R5's identity policy).
5. **Retention:** `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` on the secret; the resource policy goes with the stack; the secret stack is not deleted.
6. **Rotation and replicas:** none; the test pins both absences.
7. **Key names and metadata only:** `describe-secret`, `list-secrets` filtered by name, `get-resource-policy` (compared with the template by script), and one read of the value by the admin role through a script in `tools/` (outside this folder) that prints only the sorted key names and a SHA-256 of the canonical JSON; the agent compares the hash with that of the expected object.
8. **Runtime read:** DC-20 and DC-21 `VERIFIED_PASS` at policy level, noted "runtime read through `secretsmanager.eu-north-1.amazonaws.com` exercised in R11"; DC-33–DC-35 stay `NOT_STARTED` with a note that R8 stores the values.
9. **Tests and guard:** `tests/test_aws_env_config_template.py` in the R5–R7 style (not `test_aws_` + `secret_template.py` as the handoff wrote: that name contains one of the scan's four patterns and would refuse any evidence file or log line that names it); the guard changes only after the reference pages.
10. **Round-1 lookups:** as in step 03 below, including every secret in the Region, also those scheduled for deletion.
11. **Price evidence:** `aws pricing get-products` for `AWSSecretsManager` in eu-north-1 (step 03g); if refused, the pricing page text instead.
12. **Admin lockout (c):** there is no root user in this account, so a root exception protects nothing; the IAM reference does not say whether `aws:PrincipalArn` carries the `/managed/` path. Therefore (a) no deny touches `secretsmanager:GetResourcePolicy`, `PutResourcePolicy`, `DeleteResourcePolicy` or `DescribeSecret` for principals in the account other than the runtime role (which point 13 limits to `GetSecretValue`; it is no lockout risk), and (b) the admin exception matches the role ARN with and without the path (`ArnLike`). Round 2 shows the match with live calls by the admin role.
13. **Deny scope (b), by action group:** the runtime role is denied everything but `GetSecretValue`; `GetSecretValue` is denied to every principal except the runtime role and the admin role; value-changing, deletion, restore, tagging, rotation and replication actions are denied to every principal except the admin role; every action is denied to principals outside the account (`aws:PrincipalAccount`). Exact action names and condition keys are checked on the Secrets Manager reference pages before writing.
14. **DC-22:** `NOT_APPLICABLE` — no API-key secret exists; `bedrock_converse` authenticates through IAM and R8 stores no credential.
15. **Description and tags:** only the tag `project=proposal-orchestrator`; a description stating that the secret holds no credential.
16. **`KmsKeyId`:** the imported `KeyArn` (`proposal-orchestrator-kms-KeyArn`), not the alias, so that `describe-secret` shows the ARN of `R6_outputs.json`.

## Before you start

- **Sign in with `aws login --profile po-r1`**, never bare `aws login`.
- **Where commands run.** PowerShell in the VS Code terminal, repository root
  (`C:\Code\proposal_demo\proposal_orchestrator`). Every AWS command names `--profile po-r1`.
  CloudShell is the fallback only (end of this sheet).
- **`$E` must be set in every new PowerShell window.** Every block below starts with it.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command (none in round 1).
- The AWS CLI v2 exits **254** when the service answers with an error, and PowerShell wraps long error
  text inside the file. Criteria below are written on substrings, not on one-line quotes.
- **Never read the secret's value with the CLI**, not even in a later round: no `get-secret-value`
  command appears on this sheet. The one read (point 7) goes through a script in `tools/` in round 2.
- Never save secret values, access keys, session tokens or passwords. No step below prints any.
- If a step fails, stop, report the error in session, and do not improvise a fix.
- **Rounds.**
  - **Round 1 (this sheet now): steps 01–03**, read-only. Hand back. The agent then checks the files,
    reads the CloudFormation and Secrets Manager reference pages, fills
    `deploy/aws/templates/50-secret.yaml`, writes `tests/test_aws_env_config_template.py`, the `tools/`
    script of point 7 and the decision record `aws-redeployment-r8-secret_2026-10-26`, and adds steps
    04–05 to this sheet.
  - **Round 1b: steps 04–05** (lint, guards, tests, change set). Hand back; both read the change set;
    the operator gives the go.
  - **Round 2:** execute, outputs, read-only evidence, policy comparison, the admin's key-name and hash
    read, credits, then tests, the old-ID guard and the scan over the finished folder, commit.

---

## Steps

### Step 01 — Session-start check: credits, budget, alert states (R1-D2)

What it does: confirms that the Free plan is active, the credits are intact and no budget alert is in
`ALARM`, before anything else runs.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_01_budget-notifications.json"
Get-Content "$E\R8_01_plan-state.json", "$E\R8_01_budgets.json", "$E\R8_01_budget-notifications.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R8_01_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `199.00` (R7 left 199.99, `R7_10_plan-state-after.json`; the key's monthly fee and R7's S3/Logs/KMS usage may have started to show — the figure is recorded either way); `accountPlanExpirationDate` starts `2027-04-19` |
| `R8_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` = `10.0`, `spend` < `8.5` |
| `R8_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` = `OK` |

**STOP rule.** If the plan is not `ACTIVE`, the credits are below 199.00 USD, or any notification is in
`ALARM`, stop here and report it.

### Step 02 — Who is calling

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_02_caller-identity.json"
Get-Content "$E\R8_02_caller-identity.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R8_02_caller-identity.json` | `Account` = `797661577394`; `Arn` starts with `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Any other account: stop. Nothing below may run.

### Step 03 — Read-only lookups (nothing is created)

What it does: collects, before the template is written, the facts it is written from (handoff §7a):

- **03a** the secret name is free: `describe-secret` answers `ResourceNotFoundException`;
- **03b** every secret in eu-north-1, **including those scheduled for deletion** (a secret waiting out its
  recovery window still holds its name), with no `proposal-orchestrator/` name among them;
- **03c** the `proposal-orchestrator-secret` stack does not exist yet;
- **03d** the key is `Enabled` and its policy is still the R6 policy (the secret is encrypted with it, and
  the runtime role's decrypt via Secrets Manager rests on it, R6-D3);
- **03e** the admin role still exists with the `/managed/` path the secret policy names (points 12–13);
- **03f** the project exports: network, iam, kms and audit, among them the two the secret stack imports;
- **03g** the Secrets Manager prices for eu-north-1 from the Price List API (point 11).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
# 03a — the secret name (an error is the expected result)
& { aws secretsmanager describe-secret --profile po-r1 --region eu-north-1 --secret-id proposal-orchestrator/env-config --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_03_describe-before.txt"
# 03b — every secret in the Region, scheduled deletions included (metadata only)
aws secretsmanager list-secrets --profile po-r1 --region eu-north-1 --include-planned-deletion --query "SecretList[].{name:Name,arn:ARN,kms:KmsKeyId,deleted:DeletedDate,created:CreatedDate}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_03_secrets-before.json"
# 03c — the secret stack must not exist yet (an error is the expected result)
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_03_secret-stack-before.txt"
# 03d — the key: state and policy
aws kms describe-key --profile po-r1 --region eu-north-1 --key-id arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561 --query "KeyMetadata.{KeyId:KeyId,Arn:Arn,KeyState:KeyState,KeyManager:KeyManager,KeySpec:KeySpec,MultiRegion:MultiRegion}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_03_key-before.json"
aws kms get-key-policy --profile po-r1 --region eu-north-1 --key-id arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561 --policy-name default --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_03_key-policy-before.json"
# 03e — the admin role and its path
aws iam get-role --profile po-r1 --role-name AccountFullAccessRole --query "Role.{RoleName:RoleName,Path:Path,Arn:Arn}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_03_admin-role.json"
# 03f — project exports (network, iam, kms, audit)
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-')].{name:Name,value:Value,stack:ExportingStackId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_03_exports.json"
# 03g — Secrets Manager prices in eu-north-1 (Price List API, free; answers in us-east-1)
& { aws pricing get-products --profile po-r1 --region us-east-1 --service-code AWSSecretsManager --filters Type=TERM_MATCH,Field=regionCode,Value=eu-north-1 --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_03_pricing.txt"
Get-ChildItem "$E\R8_03_*" | Where-Object { $_.Name -ne "R8_03_pricing.txt" } | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
Get-Content "$E\R8_03_pricing.txt" -Tail 1
```

| Evidence file | PASS criterion |
|---|---|
| `R8_03_describe-before.txt` | Contains `ResourceNotFoundException`; last line `exit=254` |
| `R8_03_secrets-before.json` | A JSON list (may be empty). No `name` starts with `proposal-orchestrator/`, whether or not `deleted` is set. Any other secret is **not** a FAIL: report it; the agent records it |
| `R8_03_secret-stack-before.txt` | Contains `ValidationError` and `does not exist` for `proposal-orchestrator-secret` (the name may wrap); last line `exit=254` |
| `R8_03_key-before.json` | `Arn` = the `KeyArn` of `R6_outputs.json` (`arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561`); `KeyState` = `Enabled`; `KeyManager` = `CUSTOMER`; `KeySpec` = `SYMMETRIC_DEFAULT`; `MultiRegion` = `false` |
| `R8_03_key-policy-before.json` | `PolicyName` = `default`; the `Policy` string equals the one in `R6/R6_08_key-policy.json` (agent compares by script: same five statements by `Sid`) |
| `R8_03_admin-role.json` | `RoleName` = `AccountFullAccessRole`; `Path` = `/managed/`; `Arn` = `arn:aws:iam::797661577394:role/managed/AccountFullAccessRole` (= `AdminRoleArn` in `deploy/aws/parameters/secret.json` and `R1_00_role.json`) |
| `R8_03_exports.json` | Exactly 23 names: seven `proposal-orchestrator-network-*`, seven `proposal-orchestrator-iam-*`, three `proposal-orchestrator-kms-*`, six `proposal-orchestrator-audit-*`; none starts `proposal-orchestrator-secret-`. Values equal to the outputs files, in particular `iam-RuntimeRoleArn` = `arn:aws:iam::797661577394:role/proposal-orchestrator-runtime-role` and `kms-KeyArn` = `arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561` |
| `R8_03_pricing.txt` | Last line `exit=0`; a `PriceList` with at least one entry whose `regionCode` is `eu-north-1`. The agent extracts the per-secret-month and per-API-request prices and their `publicationDate`/`effectiveDate`. If the call is refused (`AccessDenied` or similar, `exit=254`): **not** a STOP — report it; the agent then gives a console path to the pricing page for a text copy (point 11) |

**STOP rule.** If the secret name answers anything other than `ResourceNotFoundException`, any
`proposal-orchestrator/` secret is listed (also one scheduled for deletion), the secret stack exists, an
`proposal-orchestrator-secret-*` export exists, the key is not `Enabled` or its policy differs from R6,
the admin role's ARN or path differs from `AdminRoleArn`, or one of the two import values is missing or
differs: stop and report. Nothing is written over an occupied name, a changed key policy or a missing
import.

**Hand back here (end of round 1).** Report steps 01–03 in session (UTC times, any deviation). The agent
checks every file in the device shell (criteria, key-policy comparison, prices, secret scan, old-ID
guard), then writes the template, the test, the `tools/` script, the decision record and steps 04–05
below.

---

*Round 1 done 2026-10-26 (~21:50 UTC): steps 01–03 PASS (`RUNLOG.md`). Prices in eu-north-1: 0.40 USD
per secret-month, 0.05 USD per 10,000 API requests (`R8_03_pricing.txt`, R8-D1). Template, test, digest
script and decision record `aws-redeployment-r8-secret_2026-10-26` written; steps 04–05 added below.*

### Step 04 — Lint, guards and tests on the filled template (workstation only, no AWS call)

What it does: proves, before anything is created, that `50-secret.yaml` lints for eu-north-1, keeps the
template rules, carries no old-account id, and has the shape `tests/test_aws_env_config_template.py` pins
(decision record `aws-redeployment-r8-secret_2026-10-26`, R8-D1 to R8-D16), including the derivation the
digest script uses (`tools/env_config_digest.py`). Run `deactivate` first if `.venv-lint` is active (lint
still runs through its own executable). Pytest runs with `-q`.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_04_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_04_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_04_old-id-guard.txt"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_aws_env_config_template.py tests/test_old_id_guard.py } 2>&1 | Out-File -Encoding utf8 "$E\R8_04_pytest.txt"
Get-Content "$E\R8_04_cfn-lint.txt", "$E\R8_04_template-guard.txt", "$E\R8_04_old-id-guard.txt"; Get-Content "$E\R8_04_pytest.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R8_04_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R8_04_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R8_04_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R8_04_pytest.txt` | First line `Python 3.10.…`; last line `196 passed` (the agent's run under Python 3.10.12) with no `failed`, `error` or `skipped` |

**STOP rule.** Any non-zero exit or failed test: stop. The template is not deployed until this step is
clean.

### Step 05 — Create the change set and read it (nothing is created yet)

What it does: asks CloudFormation to plan the secret stack. A change set of type CREATE builds nothing
until it is executed. **No `--capabilities`:** the stack holds no IAM resource and no macro (if
CloudFormation asks for one anyway, `create-change-set` fails with `InsufficientCapabilities`: stop and
hand back). The two `Fn::ImportValue` references (`kms-KeyArn`, `iam-RuntimeRoleArn`) are resolved here.
`describe-change-set` is run **without** `--include-property-values`, so the five configuration values do
not enter the evidence (R8-D2); the folder is scanned at the end of the step.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret --change-set-name r8-create-01 --change-set-type CREATE --template-body file://deploy/aws/templates/50-secret.yaml --parameters file://deploy/aws/parameters/secret.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_05_create-change-set.json"
Get-Content "$E\R8_05_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret --change-set-name r8-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret --change-set-name r8-create-01 --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_05_change-set.json"
Get-Content "$E\R8_05_change-set.json"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_05_secret-scan.txt"
Get-Content "$E\R8_05_secret-scan.txt"
```

If `create-change-set` itself returns an error, or `wait` reports a terminal failure, still run the
`describe-change-set` line: `Status` and `StatusReason` in `R8_05_change-set.json` are the evidence.
Then stop and hand back.

| Evidence file | PASS criterion |
|---|---|
| `R8_05_create-change-set.json` | `Id` starts `arn:aws:cloudformation:eu-north-1:797661577394:changeSet/r8-create-01/`; `StackId` starts `arn:aws:cloudformation:eu-north-1:797661577394:stack/proposal-orchestrator-secret/` |
| `R8_05_change-set.json` | `Status` = `CREATE_COMPLETE`; `ExecutionStatus` = `AVAILABLE`; `Capabilities` absent or `[]`; `Tags` = `[{project: proposal-orchestrator}]`; `Parameters` show exactly `ExpectedAccountId` 797661577394, `ExpectedRegion` eu-north-1, `ProjectName` proposal-orchestrator, `AdminRoleArn` `arn:aws:iam::797661577394:role/managed/AccountFullAccessRole` and `TransportModelId` `eu.anthropic.claude-opus-4-6-v1`; `Changes` holds **exactly two** entries, each `ResourceChange.Action` = `Add`: `EnvConfigSecret` (`AWS::SecretsManager::Secret`) and `EnvConfigSecretPolicy` (`AWS::SecretsManager::ResourcePolicy`). No configuration value appears in the file |
| `R8_05_secret-scan.txt` | `CLEAN: docs\infrastructure_security\evidence_v2\R8` (or with forward slashes); `exit=0` |

**Hand back here (end of round 1b).** Report steps 04–05 in session. Both of us read
`R8_05_change-set.json` against the criterion. **Step 06 runs only after you have confirmed in session
that the change set lists exactly those two resources and given the go.** Executing it starts the
secret's monthly fee (0.40 USD per month, prorated, from credits; R8-D1) and creates a secret that is
retained (R8-D5): if the creation fails and rolls back, a created secret may remain and is handled by a
follow-up step sheet, never by hand. If the change set itself failed (for example an organization policy
refusing a Secrets Manager or KMS action, or `BlockPublicPolicy` refusing the policy), the agent records
the error verbatim in `RUNLOG.md` and a successor decision is settled before the template changes;
nothing is executed. The agent adds steps 06 onward after the go.

---

*Round 1b done 2026-10-27 (~15:50 UTC): steps 04–05 PASS; change set `r8-create-01` read by both (two `Add`). **Operator's go in session: 2026-10-27 ~15:52 UTC ("go").***

## Round 2 — steps 06–10 (execute, outputs, read-only evidence, key names and digest, credits)

### Step 06 — Execute the change set (creates the secret and its policy; the monthly fee starts)

**Only after the operator's go in session on `R8_05_change-set.json` (given 2026-10-27).** What it does:
creates the two resources of the change set, and nothing else: first the secret (encrypted with the CMK
through the admin role's IAM delegation on the key), then its resource policy. This is where Secrets
Manager applies `BlockPublicPolicy` and where an organization RCP would refuse (R8-D4 known gap).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
& { aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret --change-set-name r8-create-01; "execute exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_06_execute-exit.txt"
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_06_stack-status.json"
aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_06_stack-events.json"
Get-Content "$E\R8_06_execute-exit.txt", "$E\R8_06_stack-status.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R8_06_execute-exit.txt` | `execute exit=0` and no error line |
| `R8_06_stack-status.json` | `status` = `CREATE_COMPLETE`; `capabilities` null or `[]`; `tags` hold `project` = `proposal-orchestrator` |
| `R8_06_stack-events.json` | `EnvConfigSecret`, `EnvConfigSecretPolicy` and the stack `proposal-orchestrator-secret` each reach `CREATE_COMPLETE`; no `*_FAILED` and no `ROLLBACK` status anywhere |

**STOP rule.** On a rollback or any `*_FAILED` event: stop, report it (the `reason` of the first failed
event matters most), and **do not delete the stack or the secret by hand**. The secret is retained by
`DeletionPolicy: Retain` and may still exist after a rollback; the agent then writes `STEPS_fix1.md`. A
failure naming `BlockPublicPolicy`, an explicit deny or KMS leads to a successor record before anything
changes.

### Step 07 — Save the stack outputs (ids for every later step and ticket)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-secret --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_outputs.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-secret-')]" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_07_exports.json"
aws cloudformation list-imports --profile po-r1 --region eu-north-1 --export-name proposal-orchestrator-kms-KeyArn --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_07_imports-keyarn.json"
aws cloudformation list-imports --profile po-r1 --region eu-north-1 --export-name proposal-orchestrator-iam-RuntimeRoleArn --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_07_imports-runtimerolearn.json"
Get-Content "$E\R8_outputs.json", "$E\R8_07_imports-keyarn.json", "$E\R8_07_imports-runtimerolearn.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R8_outputs.json` | Exactly the two contract keys, each with `ExportName` `proposal-orchestrator-secret-<Key>`: `SecretName` = `proposal-orchestrator/env-config`; `SecretArn` matches `arn:aws:secretsmanager:eu-north-1:797661577394:secret:proposal-orchestrator/env-config-` followed by six characters (the suffix Secrets Manager appends; it matches R5's grant `…/env-config-*`) |
| `R8_07_exports.json` | The same two export names and values, `ExportingStackId` the secret stack of step 05 |
| `R8_07_imports-keyarn.json` | `Imports` contains `proposal-orchestrator-secret` (besides `proposal-orchestrator-audit`) |
| `R8_07_imports-runtimerolearn.json` | `Imports` contains `proposal-orchestrator-secret` (besides the kms and audit stacks) |

### Step 08 — Read-only evidence of what was created (metadata only; ids from `R8_outputs.json` only)

What it does: shows the secret's metadata (name, key, no rotation, no replica, tag, one version) and its
resource policy, as the admin role sees them (DC-20, DC-21; points 7, 12, 13, 16). These calls also show
that `DescribeSecret` and `GetResourcePolicy` stay open to the admin role (point 12). No call here reads
the value.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
$O = Get-Content "$E\R8_outputs.json" -Raw | ConvertFrom-Json
$ARN = ($O | Where-Object OutputKey -eq 'SecretArn').OutputValue
"SecretArn=$ARN"
aws secretsmanager describe-secret --profile po-r1 --region eu-north-1 --secret-id $ARN --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_08_describe-secret.json"
aws secretsmanager list-secrets --profile po-r1 --region eu-north-1 --include-planned-deletion --filters Key=name,Values=proposal-orchestrator/ --query "SecretList[].{name:Name,arn:ARN,kms:KmsKeyId,deleted:DeletedDate,rotation:RotationEnabled}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_08_list-secrets.json"
aws secretsmanager get-resource-policy --profile po-r1 --region eu-north-1 --secret-id $ARN --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_08_resource-policy.json"
aws secretsmanager list-secret-version-ids --profile po-r1 --region eu-north-1 --secret-id $ARN --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_08_version-ids.json"
Get-Content "$E\R8_08_describe-secret.json", "$E\R8_08_list-secrets.json", "$E\R8_08_resource-policy.json", "$E\R8_08_version-ids.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R8_08_describe-secret.json` | `ARN` = `SecretArn`; `Name` = `proposal-orchestrator/env-config`; `KmsKeyId` = `arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561` (`KeyArn`, R8-D16, DC-20); no `RotationEnabled` true and no `RotationRules` / `RotationLambdaARN`; no `ReplicationStatus` and `PrimaryRegion` absent or eu-north-1; no `DeletedDate`; `Tags` = exactly `project` = `proposal-orchestrator` plus any `aws:cloudformation:*` tags CloudFormation adds; `VersionIdsToStages` holds exactly one version, with `AWSCURRENT` |
| `R8_08_list-secrets.json` | Exactly one entry: `name` `proposal-orchestrator/env-config`, `arn` = `SecretArn`, `kms` = `KeyArn`, `deleted` null, `rotation` null or false |
| `R8_08_resource-policy.json` | `ARN` = `SecretArn`; the `ResourcePolicy` string equals the template's four statements resolved (agent compares by script, statement by `Sid`, lists order-insensitive; imports resolved from `R8_03_exports.json`, `AdminRoleArn` and its pathless form from `secret.json`) |
| `R8_08_version-ids.json` | `Versions` holds exactly one entry, `VersionStages` `["AWSCURRENT"]` (the value was set once, by the template) |

### Step 09 — Key names and digest of the value, read by the admin role (point 7)

What it does: the admin role reads the current version once through `tools/env_config_digest.py`. The
script keeps the answer in memory and prints only the name, the version stages, the sorted key names and
the SHA-256 of the canonical JSON, then compares them with the object the template and `secret.json`
define (`MATCH` / `MISMATCH`). A refusal with an explicit deny means that neither admin form of point 12
matched. Run `deactivate` first if `.venv-lint` is active.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
$O = Get-Content "$E\R8_outputs.json" -Raw | ConvertFrom-Json
$ARN = ($O | Where-Object OutputKey -eq 'SecretArn').OutputValue
& { py -3.10 -m tools.env_config_digest --profile po-r1 --region eu-north-1 --secret-id $ARN --template deploy/aws/templates/50-secret.yaml --parameters deploy/aws/parameters/secret.json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_09_key-names-digest.txt"
Get-Content "$E\R8_09_key-names-digest.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R8_09_key-names-digest.txt` | `name: proposal-orchestrator/env-config`; `version_stages: AWSCURRENT`; `key_count: 5`; `keys: AWS_REGION, ORCHESTRATOR_DIAGNOSTIC_LEVEL, ORCHESTRATOR_PRODUCTION_MODE, ORCHESTRATOR_TRANSPORT_MODEL, ORCHESTRATOR_TRANSPORT_PRESET`; `sha256:` = `expected_sha256:` = `1306b9914d0c1366ada204429d23200480d3aa7165cc4cab1553d0066fa6318a` (the agent's derivation from the template and `secret.json`, eu-north-1); `keys: MATCH`; `sha256: MATCH`; last line `exit=0`. No configuration value in the file |

**STOP rule.** `exit=1` (a `MISMATCH`) or `exit=2` (an error; an `explicit deny` in the text is the
point-12 case): stop and report. Do not retry with the CLI.

### Step 10 — Session-end credits (read-only)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R8_10_plan-state-after.json"
Get-Content "$E\R8_10_plan-state-after.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R8_10_plan-state-after.json` | `FREE` / `ACTIVE`; credits ≥ `199.00`. The secret's fee is billed with a delay, so the figure may still read 199.99 |

**Hand back here (end of round 2).** The agent verifies every file (the resource policy by script), writes
`VERIFICATION.md`, the register v2 rows (DC-20, DC-21, DC-22; notes on DC-19 and DC-33–DC-35) and the
worklog entry; then you run step 11.

*Round 2 done 2026-10-27 (~16:05 UTC): steps 06–10 PASS, step 06's exit file by substitute evidence (point 17, "17a", R8-D17); steps 07–10 re-run in order after a first attempt before step 06 (`RUNLOG.md`). Resource policy equal to the template by script; digest `MATCH`.*

17. (added after round 2, operator "17a", 2026-10-27 ~16:04 UTC) `R8_06_execute-exit.txt` holds a refused repeat of step 06; the criterion is PASS on substitute evidence (the refusal's `EXECUTE_COMPLETE`, the stack events, the first run's `exit=0` in `RUNLOG.md`), recorded as a deviation (R8-D17).

## Round 3 — closing

### Step 11 — Closing: tests, old-ID guard, then the secret scan over the finished folder

Runs only after the agent has written `VERIFICATION.md`, the register v2 rows and the worklog entry, so
the scan sees the final folder. Run `deactivate` first if `.venv-lint` is active. The scan runs last.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R8"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_aws_env_config_template.py tests/test_old_id_guard.py } 2>&1 | Out-File -Encoding utf8 "$E\R8_11_pytest.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_11_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R8_11_secret-scan.txt"
Get-Content "$E\R8_11_pytest.txt" -Tail 1; Get-Content "$E\R8_11_old-id-guard.txt", "$E\R8_11_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R8_11_pytest.txt` | First line `Python 3.10.…`; last line `196 passed` with no `failed`, `error` or `skipped` |
| `R8_11_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R8_11_secret-scan.txt` | `CLEAN: docs\infrastructure_security\evidence_v2\R8` (or with forward slashes); `exit=0` |

Then commit (template, test, digest script, decision record, README, tickets, register, worklog,
`evidence_v2/R8/`) and confirm in session. The agent ticks R8.

---

## CloudShell fallback (round 1)

Only if PowerShell is unavailable. In CloudShell (eu-north-1), drop `--profile po-r1`, and replace each
`… 2>&1 | Out-File -Encoding utf8 "$E\<file>"` with `… > <file> 2>&1`; for the three lines wrapped in
`& { …; "exit=$LASTEXITCODE" }`, use `{ <command>; echo "exit=$?"; } > <file> 2>&1`. The `--query`
strings and `--filters` work unchanged inside single quotes. Download the files into
`docs\infrastructure_security\evidence_v2\R8\` before handing back.
