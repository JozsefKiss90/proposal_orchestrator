# R14 — Operations and cost: step sheet

| Field | Value |
|---|---|
| Ticket | `R14` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R14 (with OD10, OD13 and the pricing rule of §7); `.scratch/overhaul-2026-11/handoff-session-2026-11-11.md` A3 |
| Decisions applied | OD1-r1 eu-north-1; OD5 (the host stack lives one session); OD6-r3 (change sets, outputs contract); OD9-r1 (`c7i-flex.large`); OD10 (Free plan; upgrade only after ELTE approval, operator only); OD13 (10 USD budget while on credits; after the upgrade, the approved HUF amount with alerts at 50/80/100 %); R12b-D9 (F7 retest in the next host session, against a bucket that exists); F-R12b-5 (workstation signing uses `aws configure export-credentials`); the operator's answers to points 1–8 below, once given |
| Written by / on | agent (Claude) / 2026-11-12 |
| Account / region | `797661577394` / `eu-north-1`. The scripts read both from `deploy/aws/parameters/host.json` and refuse any other caller account. Every command names `--region eu-north-1`, also in CloudShell |
| IDs taken from | `R4_outputs.json` (VPC), the host stack's live outputs (written by the start script as `<prefix>_outputs.json`), `R11_*` and `R12b_*` for the creation times the cost check prices |
| Controls touched | None changes status. The start script keeps OD5 and the template guard's rules; the F7 retest (step 08) evidences R12b criterion 2 (DC-05, DC-07) |
| Hourly cost created | **Yes, in round 3 only: two creations of the host stack (steps 07–11 and 12–15).** Six interface endpoints, one `c7i-flex.large` host and its gp3 root volume. While the host is stopped (steps 09–10, 13–14) the endpoints and the volume still cost. **No figure is quoted here.** Step 05 prices every item from the AWS price list; the agent then states the expected cost of round 3, and the operator's go is recorded in `RUNLOG.md` before step 07 |

## What the agent builds first (round 0, no AWS call)

The ticket asks for scripts, a cost check and a checklist. None exists yet. The agent writes them on
`harness_overhaul`, with tests, before round 1. This sheet fixes their interface so the steps below
are exact.

| File | What it does |
|---|---|
| `deploy/aws/scripts/host-lifecycle.ps1` | PowerShell form. `-Action start`, `stop`, `teardown` or `plan`; `-Profile`, `-OutDir`, `-Prefix`. Writes `<Prefix>_<name>` files into `-OutDir` |
| `deploy/aws/scripts/host-lifecycle.sh` | CloudShell form. `start`, `stop`, `teardown` or `check`, then `<outdir> <prefix>`. Same files and checks; no profile (CloudShell uses the console session). Reads `90-host.yaml` and `host.json` from its own folder |
| `tools/aws_cost_check.py` | `prices` captures unit prices from the AWS Price List API. `report` writes the weekly cost check |
| `deploy/aws/pricing/eu-north-1.json` | Unit prices, each with its price-list SKU, the public pricing page URL and the date read. Built by the agent from step 04 |
| `deploy/aws/pricing/budget.json` | The approved HUF amount (`null` until ELTE approves), the HUF/USD rate, its source and its date |
| `docs/infrastructure_security/aws_od10_upgrade_checklist.md` | The OD10 checklist. Marked operator-only |
| `tests/test_aws_host_lifecycle_scripts.py`, `tests/tools/test_aws_cost_check.py` | Both script forms run against a fake `aws` that records each call; the cost check runs against recorded responses |

What the start script does, in both forms:

1. Refuses unless the caller account equals `ExpectedAccountId` of `host.json`.
2. Reads the stack state. No stack: the create path. Stack `CREATE_COMPLETE` with the host `stopped`:
   the resume path. Host already `running`: reports it and exits 0. Any other state, including
   `REVIEW_IN_PROGRESS`: refuses and names the cleanup command.
3. Create path: creates change set `session-<UTC time>`, then checks it. It needs exactly seven `Add`
   changes (the six endpoints and `Host`), no capabilities, the stack tag and the parameters of
   `host.json`. It prints the instance type and image, then waits for you to type `create`. Anything
   else deletes the unexecuted change set and exits 3. It waits for completion only if
   `execute-change-set` exited 0 (the R12b hang).
4. Resume path: waits for you to type `start`, then starts the instance.
5. Both paths wait up to 10 minutes for `Online` in SSM, then write the outputs and the instance record.

The stop script stops the instance and waits for `stopped`. It records that the endpoints and the
volume still exist and still cost. The teardown script waits for you to type `delete`. It then deletes
the stack and checks that no endpoint interface, instance or project volume remains, and that the five
base stacks are unchanged. No script touches a base stack, writes a credential, or adds a route or a
security-group rule.

## Points for the operator to settle (answers recorded in `RUNLOG.md` before round 1)

1. **What "stop" means.** The agent proposes: stop stops the instance only. The six endpoints keep
   billing by the hour, so stop is for a pause within a working day; it keeps the host's disk, for
   example an installed R15 bundle. At the end of a day, teardown. Step 05 prices both states, so you
   can choose with figures.
2. **Two creations.** Each script form must run once end to end, and the create path and the resume
   path are different code. The agent proposes two creations in one sitting. Creation A: PowerShell
   start (create), PowerShell stop, CloudShell start (resume), CloudShell teardown. Creation B:
   CloudShell start (create), CloudShell stop, PowerShell start (resume), PowerShell teardown. One
   creation would leave two paths unrun.
3. **Typed confirmation.** The start and teardown scripts wait for a typed word. This sits on top of
   the go in `RUNLOG.md`, not in place of it. Stop asks nothing, because it only lowers cost.
4. **Where prices come from.** The ticket asks for the AWS pricing pages. The agent proposes the AWS
   Price List API, which serves the same prices as files with a publication date, and records the
   public pricing page URL beside each price. You run the capture (step 04), so the prices are
   evidence, not the agent's recollection. The API answers in `us-east-1`, `eu-central-1` and
   `ap-south-1`. The step uses `eu-central-1`. If the organization's policy refuses that Region, the
   agent reads the pricing pages instead and records each page and date. The agent does not yet know
   whether the price list carries the Anthropic model prices. If it does not, the Bedrock pricing page
   is the source.
5. **Cost Explorer.** The spend figures come from `ce get-cost-and-usage`. AWS charges 0.01 USD per
   request of that API. One report makes about four requests. If Cost Explorer has never been opened
   in this account, its data may take up to 24 hours to appear. Step 05 then reports spend as
   "not available" rather than zero.
6. **The HUF amount.** ELTE has not approved the reimbursement route. `budget.json` therefore holds
   `approved_huf: null`, and the report prints "approved amount: pending". The handoff's figure of
   about 300,000 HUF is not used as an approved amount. For the conversion, give the agent a rate with
   its source and date (for example the MNB official rate of a named day). Without one, the report
   shows USD only.
7. **F7 retest in creation A (R12b-D9).** The agent proposes this:
   - You create a throwaway bucket in this account, in `eu-north-1`, with a random name.
   - The host PUTs to it through a URL presigned by `po-r1`.
   - The bucket exists and is not the deploy bucket, so the gateway endpoint policy refuses the PUT.
     The expected answer is `403` `AccessDenied`, naming the VPC endpoint policy.
   - If the PUT were accepted, the object would land in your own empty bucket, which step 08 deletes.
   - The check sends the collector's fixed `f7_presigned_put.sh` by Run Command, without a collector
     run. The open collector defects F-R12b-2 to -4 therefore do not block it.
   - The evidence goes to the R12b folder as `R12b_fix2_*`, so R12b criterion 2 reads it there.
   - The limit recorded at R12b stays: signer and bucket both belong to this account.
8. **CloudShell Region.** The scripts name `--region eu-north-1` on every call, so the CloudShell
   Region does not matter for what they do. Step 06 opens CloudShell in `eu-north-1` and records
   whether it is offered there.

## Points the agent decided (the operator confirms or changes each on review)

9. **One file per form, three actions.** CloudShell needs the script, `90-host.yaml` and `host.json`
   uploaded. One file per form keeps that to three files.
10. **CloudShell evidence comes back as one archive.** The script writes into `~/r14/` in CloudShell.
    You download `~/r14.tar.gz` (Actions → Download file) and unpack it into this folder.
11. **Weekly runs after R14** write to `evidence_v2/ops/cost/<YYYY-MM-DD>/`, not into this ticket's
    folder. R13's operational procedure carries the weekly routine.
12. **Bedrock tokens per run.** Invocation logging stays off, so token counts come from the CloudWatch
    `AWS/Bedrock` metrics `InputTokenCount` and `OutputTokenCount` per `ModelId`. A "run" is one host
    creation, from `ExecuteChangeSet` to `DeleteStack` in CloudTrail (90 days kept). The first report
    covers R11's two creations, R12b's two and none of R14's (step 05 runs before them).
13. **OD10 checklist content.** The agent drafts the items and marks each fact it could not confirm
    from an AWS page as "operator to confirm". It holds no ELTE detail: no billing address, VAT number
    or contact. Those fields are blanks only the operator fills, in the console, at upgrade time.

## Before you start

- **Sign in with `aws login --profile po-r1`**, never bare `aws login`.
- **Where commands run.** PowerShell in the VS Code terminal, repository root, for every step except
  the CloudShell ones (06, 10, 11, 12, 13). Every workstation AWS command names `--profile po-r1`.
- **`$E` must be set in every new PowerShell window.** Every block starts with it.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command.
- **Paste each block whole.** A cut paste leaves PowerShell at `>>`. Press Ctrl+C and paste again.
  For a block longer than 15 lines, the agent also gives you a script file.
- **Never save** secret values, access keys, session tokens, passwords, the IMDS token, instance
  credentials, the F7 URL, prompt or proposal text, or model output other than the fixed test string
  `DEPLOY_OK`.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or `0.0.0.0/0` egress rule, not even temporarily.
  Bedrock model invocation logging stays disabled.
- If a step fails, stop, report the error in session, and do not improvise a fix. **If the host stack
  exists when you stop, run the teardown (step 15's command) unless the agent asks you to keep it. It
  costs by the hour.**
- **Rounds.**
  - **Round 0 (agent):** the files above, with tests. The agent commits them and says so in session.
  - **Round 1: steps 01–04.** Nothing billable. Hand back. The agent builds the price file from step 04.
  - **Round 2: steps 05–06.** Nothing billable by the hour (step 05 costs about 0.04 USD in Cost
    Explorer requests). Hand back. The agent states the expected cost of round 3 from step 05, and you
    give or withhold the go.
  - **Round 3: steps 07–15, in one sitting**, under the recorded go. Charges run from step 07 to step
    11 and from step 12 to step 15.
  - **Round 4: step 16** after the agent has written `VERIFICATION.md` and the worklog entry.

---

## Steps

### Step 01 — Session-start check and identity (R1-D2)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R14_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R14_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R14_01_budget-notifications.json"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R14_01_caller-identity.json"
Get-ChildItem "$E\R14_01_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R14_01_plan-state.json` | `accountPlanType` `FREE`; `accountPlanStatus` `ACTIVE`; `accountPlanExpirationDate` starts `2027-04-19`; `accountPlanRemainingCredits.amount` recorded (no threshold: R11 and R12b usage may only now reach the credits) |
| `R14_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` `10.0`; `spend` recorded |
| `R14_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100) |
| `R14_01_caller-identity.json` | `Account` `797661577394`; `Arn` starts `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Plan not `ACTIVE`, or another account: stop and report. A notification in `ALARM`: report
it and wait for the agent before round 3.

### Step 02 — Read-only lookups (nothing is created)

Confirms that R12b left nothing behind.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$VPC = O "$V2\R4\R4_outputs.json" VpcId
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_02_host-stack-before.txt"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R14_02_vpc-endpoints-before.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query "Reservations[].Instances[].{id:InstanceId,state:State.Name}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R14_02_instances-before.json"
aws ec2 describe-volumes --profile po-r1 --region eu-north-1 --filters Name=tag:project,Values=proposal-orchestrator --query "Volumes[].{id:VolumeId,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R14_02_volumes-before.json"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R14_02_base-stacks.json"
Get-ChildItem "$E\R14_02_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R14_02_host-stack-before.txt` | Contains `ValidationError` and `does not exist`; last line `exit=254` |
| `R14_02_vpc-endpoints-before.json` | Exactly one entry: the S3 gateway endpoint of `R4_outputs.json`, `available` |
| `R14_02_instances-before.json` | `[]` |
| `R14_02_volumes-before.json` | `[]` |
| `R14_02_base-stacks.json` | Equal to `R12b_fix1_10_base-stacks.json` |

**STOP rule.** Any difference: stop and report.

### Step 03 — Workstation checks and both scripts in plan mode (no AWS call)

The plan modes print every command the scripts would run. They call nothing.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_03_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_03_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_03_old-id-guard.txt"
$T = "tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_host_template.py tests/test_old_id_guard.py tests/test_aws_host_lifecycle_scripts.py tests/tools/test_aws_cost_check.py tests/test_evidence_protocol_scaffold.py".Split(" ")
& { py -3.10 --version; py -3.10 -m pytest -q @T } 2>&1 | Out-File -Encoding utf8 "$E\R14_03_pytest.txt"
& { powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action plan -Profile po-r1 -OutDir $E -Prefix R14_03; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_03_ps-plan.txt"
Get-Content "$E\R14_03_cfn-lint.txt", "$E\R14_03_template-guard.txt", "$E\R14_03_old-id-guard.txt"; Get-Content "$E\R14_03_pytest.txt" -Tail 1; Get-Content "$E\R14_03_ps-plan.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R14_03_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R14_03_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R14_03_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R14_03_pytest.txt` | First line `Python 3.10.…`; last line the count the agent states at the end of round 0; no `failed` or `error` |
| `R14_03_ps-plan.txt` | Last line `exit=0`; every `aws` line names `--profile po-r1` and `--region eu-north-1`; the stack name is `proposal-orchestrator-host` only; no `delete-stack` of any other stack |

**STOP rule.** Any non-zero exit or failed test: stop.

### Step 04 — Capture the unit prices (Price List API; no cost)

`prices` asks the Price List API for each item R14 prices in `eu-north-1`. The items are the
`c7i-flex.large` Linux on-demand hour, the gp3 GB-month, the interface endpoint hour and GB processed,
the KMS key month and request, the Secrets Manager secret month and request, and CloudWatch Logs
ingestion and storage. Bedrock input and output tokens for both OD7 models come from the price list if
it carries them. The tool keeps the SKU, the description, the unit, the USD price, the effective date
and the offer's publication date, and drops the rest.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
& { py -3.10 -m tools.aws_cost_check prices --profile po-r1 --api-region eu-central-1 --out "$E\R14_04_price-list.json"; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_04_price-list-console.txt"
Get-Content "$E\R14_04_price-list-console.txt" -Tail 20
```

| Evidence file | PASS criterion |
|---|---|
| `R14_04_price-list-console.txt` | Last line `exit=0`; one `found` line per item; Bedrock lines may read `not in price list` (point 4) |
| `R14_04_price-list.json` | One entry per found item: `sku`, `description`, `unit`, `usd`, `effective_date`, `publication_date`; `regionCode` `eu-north-1` (Bedrock: the Region the price list gives for the `eu.` profile) |

**STOP — hand back here (end of round 1).** An `AccessDenied` for `eu-central-1` is not a failure:
report it (point 4). The agent checks the file by script, writes `deploy/aws/pricing/eu-north-1.json`
with the page URL and date per price, and commits it.

---

### Step 05 — The cost check, first run

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
& { py -3.10 -m tools.aws_cost_check report --profile po-r1 --prices deploy\aws\pricing\eu-north-1.json --budget deploy\aws\pricing\budget.json --out "$E\R14_05_cost-check"; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_05_cost-check-console.txt"
Get-Content "$E\R14_05_cost-check-console.txt" -Tail 25
```

| Evidence | PASS criterion |
|---|---|
| `R14_05_cost-check-console.txt` | Last line `exit=0` |
| `R14_05_cost-check/report.json` and `report.md` | Credits remaining equal `R14_01_plan-state.json` or a later value; month-to-date spend by service, or "not available" (point 5); the 10 USD budget and its spend; the approved HUF amount as "pending" (point 6); the cost of one running hour and one stopped hour; per host creation since 2026-11-11 its start, end, hours, priced cost and Bedrock input and output tokens per model; every price row cites its page URL and date |

### Step 06 — CloudShell readiness (no cost)

Open the console in `eu-north-1`, then CloudShell. Note in `RUNLOG.md` whether CloudShell is offered in
`eu-north-1` (point 8). Upload three files (Actions → Upload file): `deploy/aws/scripts/host-lifecycle.sh`,
`deploy/aws/templates/90-host.yaml` and `deploy/aws/parameters/host.json`. Then run:

```bash
mkdir -p ~/r14 && bash ~/host-lifecycle.sh check ~/r14 R14_06 && tar -czf ~/r14.tar.gz -C ~/r14 . && ls -l ~/r14
```

Download `~/r14.tar.gz` (Actions → Download file) and unpack it into this folder:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
tar -xzf "$env:USERPROFILE\Downloads\r14.tar.gz" -C $E; Get-Content "$E\R14_06_check.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R14_06_check.txt` | `aws-cli/2.…`; caller account `797661577394`; the SHA-256 of the three uploaded files equals the values the agent states at the end of round 0; `RESULT=ready` |

**STOP — hand back here (end of round 2).** The agent states the expected cost of round 3 from
`report.json`: two creations, the planned hours per state and the token use of one F7 check (none).
You give or withhold the go. The agent records it in `RUNLOG.md` before step 07.

---

### Step 07 — Creation A: PowerShell start, create path (hourly charges start)

**Only under the recorded go.** Run the block **once**. Type `create` when the script asks.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action start -Profile po-r1 -OutDir $E -Prefix R14_07
```

| Evidence file | PASS criterion |
|---|---|
| `R14_07_log.txt` | Start and end UTC; `path=create`; `confirmed=create`; last line `RESULT=started` |
| `R14_07_change-set.json` | Seven `Add` changes (six endpoints, `Host`); no capabilities; tag `project`; `InstanceType` `c7i-flex.large` |
| `R14_07_stack-status.json` | `CREATE_COMPLETE` |
| `R14_07_outputs.json` | The seven contract keys; values differ from `R12b_outputs.json` |
| `R14_07_instance-information.json` | `ping` `Online`, `Amazon Linux` `2023` |

**STOP rule.** Any other last line: report it, and run the teardown (step 15's command with prefix
`R14_07x`) unless the stack does not exist.

### Step 08 — F7 retest: PUT to a throwaway bucket that exists (R12b criterion 2)

Writes into the **R12b** folder. Run right after step 07 in the same window. The bucket gets a random
name, lives in this account in `eu-north-1`, and is deleted at the end of the block. Nothing is printed
or written except the evidence files below. The Run Command parameters, which hold the URL, pass
through one temporary file outside the repository, deleted on the same line: Windows PowerShell 5.1
strips the quotes of inline JSON passed to `aws`. As at R12b, SSM keeps the parameters in the account's
command history; the URL expires after 15 minutes. Two credential variable names are assembled at run time,
so this sheet passes the evidence secret scan.

**Run this block from the script file the agent gives, not as a paste.** It is long, and its `return`
stops a script but not a paste.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"; $R = "docs\infrastructure_security\evidence_v2\R12b"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$I = O "$E\R14_07_outputs.json" InstanceId
$OB = "po-f7-target-" + -join ((1..12) | ForEach-Object { "{0:x}" -f (Get-Random -Maximum 16) })
& { aws s3api create-bucket --profile po-r1 --region eu-north-1 --bucket $OB --create-bucket-configuration LocationConstraint=eu-north-1 --output json | Out-Null; "create_bucket_exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$R\R12b_fix2_08_bucket.txt"
& { aws s3api head-bucket --profile po-r1 --region eu-north-1 --bucket $OB 2>&1 | Out-Null; "head_bucket_exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 -Append "$R\R12b_fix2_08_bucket.txt"
$c = aws configure export-credentials --profile po-r1 --format process | ConvertFrom-Json
$k = "AWS_" + "SECRET_ACCESS_KEY"; $t = "Session" + "Token"
[Environment]::SetEnvironmentVariable("AWS_ACCESS_KEY_ID", $c.AccessKeyId, "Process"); [Environment]::SetEnvironmentVariable($k, $c.SecretAccessKey, "Process"); [Environment]::SetEnvironmentVariable("AWS_SESSION_TOKEN", $c.$t, "Process"); $c = $null
$U = py -3.10 -c "import boto3,sys; from botocore.config import Config; s=boto3.client('s3', region_name='eu-north-1', config=Config(signature_version='s3v4', s3={'addressing_style':'virtual'})); print(s.generate_presigned_url('put_object', Params={'Bucket': sys.argv[1], 'Key': 'f7-negative-test.txt'}, ExpiresIn=900))" $OB
foreach ($v in "AWS_ACCESS_KEY_ID", $k, "AWS_SESSION_TOKEN") { [Environment]::SetEnvironmentVariable($v, $null, "Process") }
if (-not ("$U".StartsWith("https://") -and "$U".Contains(".s3.eu-north-1.amazonaws.com/"))) { "url_ok=False: stop, remove the bucket (last two lines), report"; return }
$S = (Get-Content tools\collector_host_checks\f7_presigned_put.sh -Raw) -replace "`r`n", "`n"
$PF = Join-Path $env:TEMP "po-f7-params.json"
@{ commands = @("export PO_F7_URL='$U'") + ($S -split "`n") } | ConvertTo-Json -Compress | Out-File -Encoding ascii $PF; $U = $null
$CID = aws ssm send-command --profile po-r1 --region eu-north-1 --instance-ids $I --document-name AWS-RunShellScript --parameters "file://$PF" --query "Command.CommandId" --output text; Remove-Item $PF
for ($n = 0; $n -lt 12; $n++) { Start-Sleep -Seconds 5; $st = aws ssm get-command-invocation --profile po-r1 --region eu-north-1 --command-id $CID --instance-id $I --query Status --output text 2>$null; if ($st -in "Success", "Failed", "TimedOut", "Cancelled") { break } }
aws ssm get-command-invocation --profile po-r1 --region eu-north-1 --command-id $CID --instance-id $I --query "{status:Status,responseCode:ResponseCode,stdout:StandardOutputContent,stderr:StandardErrorContent}" --output json 2>&1 | Out-File -Encoding utf8 "$R\R12b_fix2_08_f7-presigned-put.json"
& { aws s3api list-objects-v2 --profile po-r1 --region eu-north-1 --bucket $OB --query "KeyCount" --output text; aws s3 rb "s3://$OB" --profile po-r1 --region eu-north-1 --force | Out-Null; "rb_exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$R\R12b_fix2_08_bucket-removed.txt"
Get-Content "$R\R12b_fix2_08_bucket.txt", "$R\R12b_fix2_08_f7-presigned-put.json", "$R\R12b_fix2_08_bucket-removed.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R12b_fix2_08_bucket.txt` | `create_bucket_exit=0`; `head_bucket_exit=0` (the bucket exists) |
| `R12b_fix2_08_f7-presigned-put.json` | `status` `Success`; stdout `http_status=403`, `error_code=AccessDenied`, `message_names_vpc_endpoint_policy=yes`, `RESULT=expected`; no `https://` in the file (the agent checks by script) |
| `R12b_fix2_08_bucket-removed.txt` | First line `0` (no object arrived); `rb_exit=0` |

A `403` naming the endpoint policy **closes F7** within the limit of point 7. A `2xx` or a first line
above `0` in the last file is an F7 FAIL to report. Any other answer is reported as found; the agent
records it and the operator decides.

### Step 09 — Creation A: PowerShell stop

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action stop -Profile po-r1 -OutDir $E -Prefix R14_09
```

| Evidence file | PASS criterion |
|---|---|
| `R14_09_log.txt` | Start and end UTC; last line `RESULT=stopped` |
| `R14_09_instance.json` | `state` `stopped`; root volume `in-use` |
| `R14_09_vpc-endpoints.json` | Seven endpoints `available` (six interface, the S3 gateway): they still cost |

### Step 10 — Creation A: CloudShell start, resume path

In CloudShell. Type `start` when the script asks. The host-outputs file of step 07 is not needed: the
script reads the stack.

```bash
rm -rf ~/r14 && mkdir -p ~/r14 && bash ~/host-lifecycle.sh start ~/r14 R14_10; tar -czf ~/r14.tar.gz -C ~/r14 .
```

Download and unpack as in step 06.

| Evidence file | PASS criterion |
|---|---|
| `R14_10_log.txt` | `path=resume`; `confirmed=start`; last line `RESULT=started` |
| `R14_10_instance-information.json` | Same `InstanceId` as `R14_07_outputs.json`; `ping` `Online` |

### Step 11 — Creation A: CloudShell teardown (end of the first billable window)

Type `delete` when the script asks.

```bash
rm -rf ~/r14 && mkdir -p ~/r14 && bash ~/host-lifecycle.sh teardown ~/r14 R14_11; tar -czf ~/r14.tar.gz -C ~/r14 .
```

Download and unpack as in step 06. Write the delete time (UTC) in `RUNLOG.md`.

| Evidence file | PASS criterion |
|---|---|
| `R14_11_log.txt` | `confirmed=delete`; last line `RESULT=deleted` |
| `R14_11_host-stack-after.txt` | `does not exist` |
| `R14_11_after.json` | No interface endpoint, no endpoint network interface, no instance, no project volume; the five base stacks as `R14_02_base-stacks.json` |

### Step 12 — Creation B: CloudShell start, create path (hourly charges start again)

Type `create` when the script asks.

```bash
rm -rf ~/r14 && mkdir -p ~/r14 && bash ~/host-lifecycle.sh start ~/r14 R14_12; tar -czf ~/r14.tar.gz -C ~/r14 .
```

Download and unpack as in step 06. Criteria: as step 07 with `R14_12_*`. The outputs differ from
`R14_07_outputs.json`.

### Step 13 — Creation B: CloudShell stop

```bash
rm -rf ~/r14 && mkdir -p ~/r14 && bash ~/host-lifecycle.sh stop ~/r14 R14_13; tar -czf ~/r14.tar.gz -C ~/r14 .
```

Download and unpack. Criteria: as step 09 with `R14_13_*`.

### Step 14 — Creation B: PowerShell start, resume path

Type `start` when the script asks.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action start -Profile po-r1 -OutDir $E -Prefix R14_14
```

Criteria: as step 10 with `R14_14_*`, and the same `InstanceId` as `R14_12_outputs.json`.

### Step 15 — Creation B: PowerShell teardown (end of the second billable window)

Type `delete` when the script asks. Write the delete time (UTC) in `RUNLOG.md`.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action teardown -Profile po-r1 -OutDir $E -Prefix R14_15
```

Criteria: as step 11 with `R14_15_*`. From here nothing billable by the hour exists.

### Step 16 — Closing: tests, old-ID guard, then the secret scan over both folders

Runs only after the agent has written `VERIFICATION.md`, the R12b `VERIFICATION.md` addendum for F7 and
the worklog entry. The scans run last.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R14"; $R = "docs\infrastructure_security\evidence_v2\R12b"
$T = "tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_host_template.py tests/test_old_id_guard.py tests/test_aws_host_lifecycle_scripts.py tests/tools/test_aws_cost_check.py tests/test_evidence_protocol_scaffold.py".Split(" ")
& { py -3.10 --version; py -3.10 -m pytest -q @T } 2>&1 | Out-File -Encoding utf8 "$E\R14_16_pytest.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_16_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $R; "exit=$LASTEXITCODE"; py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R14_16_secret-scan.txt"
Get-Content "$E\R14_16_pytest.txt" -Tail 1; Get-Content "$E\R14_16_old-id-guard.txt", "$E\R14_16_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R14_16_pytest.txt` | First line `Python 3.10.…`; last line the count the agent states with `VERIFICATION.md`; no `failed` or `error` |
| `R14_16_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R14_16_secret-scan.txt` | `CLEAN` for the R12b folder and for the R14 folder, each followed by `exit=0` |

Then commit, and confirm R14 (and F7) in session. The agent ticks the R14 criteria and R12b criterion 2.

## Outputs

Each start writes `<prefix>_outputs.json` (`R14_07`, `R14_12`). Both stacks are deleted in this ticket,
so no later sheet takes ids from them.

## Before you hand back

- [ ] Every evidence file listed above exists in this folder (step 08's in the R12b folder), under
      exactly its name.
- [ ] `RUNLOG.md` records the UTC times, both create and delete times, the typed confirmations, any
      deviation and any error.
- [ ] `proposal-orchestrator-host` does not exist (`R14_15_host-stack-after.txt`).
- [ ] The F7 bucket is gone (`R12b_fix2_08_bucket-removed.txt`), and `~/r14`, `~/r14.tar.gz` and the
      three uploaded files are removed from CloudShell.
