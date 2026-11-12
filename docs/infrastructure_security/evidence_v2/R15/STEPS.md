# R15 — Host install and Converse smoke run: step sheet

| Field | Value |
|---|---|
| Ticket | `R15` in `plans/aws_redeployment_tickets.md` (rescoped 2026-11-11, `plan-order-reliability_2026-11-11` D3) |
| Handoff exit condition | `.scratch/overhaul-2026-11/handoff-session-2026-11-11.md` A4; `plans/msca_dn_an12_host_runbook.md` Parts 2 and 4 (Part 3 is out of scope, D1) |
| Decisions applied | OD1-r1 eu-north-1; OD5 (the host stack lives one session); OD7-orchestrator, OD7-assessor, OD7-global; R5-D1/D2 (the host reads the deploy bucket's `bundles/` only); R9e (every host command through `runner.host_env`); AN12 D1–D4, R1–R8; AN1c (the assessor is not the drafter's model); V13 (a green receipt before the pass); ticket 13 (receipts outside every checkout); R12b point 1 (DC-33–35 collected in R15); R14 F-R14-2 and R14-D5 (the carry-overs below); the operator's answers to points 1–8, once given |
| Written by / on | agent (Claude) / 2026-11-12 |
| Account / region | `797661577394` / `eu-north-1`. Every command names `--region eu-north-1` |
| What runs | The O5 bundle: tag `msca-dn-freeze-2026-11-12` → `17e32d54f2bd60c1d69d9a1b6caa8688c34f036e`; tarball sha256 `9c5351ef709905c391fd82d06ccdacf1a806c255350241c6d88a21b4d0f2132a`, 92,413,570 bytes; `bundle_manifest.json` sha256 `04f8218f5c5e715d91e9bcad5efbc654d005c57fd30e0ecc8265de8c0a2319dd`, 299 files (decision record `msca-dn-refreeze-o5_2026-11-12`). Nothing is rebuilt for R15 |
| IDs taken from | `R7_outputs.json` (deploy bucket), `R6_outputs.json` (key), `R5_outputs.json` (runtime role), the host stack's live outputs (`R15_06_outputs.json`, written by the start script) |
| Controls touched | DC-33, DC-34, DC-35 (DEFERRED to R15 at R12b point 1): collected at step 10. DC-26: the pass's Converse events at step 15. No other status changes |
| Hourly cost created | **Yes, in round 2 only: one creation of the host stack (steps 06–14).** Six interface endpoints, one `c7i-flex.large` host and its 8 GB gp3 volume: 0.154686 USD per running hour (`R14_05_cost-check/report.json`). Bedrock tokens at step 13 (Sonnet 4.6, Regional: 3.3 USD in, 16.5 USD out per 1M tokens). **The agent states the expected cost of round 2 at the end of round 1. The operator's go is recorded in `RUNLOG.md` before step 06** |

## The carry-overs from R14

- **CloudShell teardown, end to end (R14-D5).** At R14 the CloudShell teardown issued the delete and was
  then interrupted, so its after-checks came from a recovery block. Step 14 runs it through to
  `RESULT=deleted` with the script's own after-checks.
- **Typed-ahead input at a real terminal (F-R14-2).** Both forms now discard what was typed while the
  script ran, before each typed-word prompt. The fake-CLI tests pipe their answers, so the discard has
  never run at a terminal. Step 06 tests it in PowerShell and step 14 in CloudShell.
- **The fixed CloudShell script.** Its sha256 changed with the fix. Step 05 uploads it and records the new
  hash.

## What the agent builds first (round 0, no AWS call)

| File | What it does |
|---|---|
| `deploy/aws/scripts/host-run.ps1` | Sends one host script by Run Command (`AWS-RunShellScript`) and waits for it. `-AwsProfile`, `-Outputs` (the start script's outputs file, for `InstanceId`), `-Script` (an LF shell file), optional `-VarsFile` (a JSON object of `PO_…` values, each sent as one `export` line before the script), `-TimeoutSeconds`, `-Out`. The parameters pass through one temporary file outside the repository, deleted after the send (the R14 step 08 route). Writes `-Out` as JSON: script path and sha256 (LF), vars file, instance, command id, sent and finished UTC, `status`, `responseCode`, `stdout`, `stderr`, and `stdout_truncated` (SSM returns at most 24,000 characters) |
| `docs/infrastructure_security/evidence_v2/R15/host/r15_07_fetch.sh` … `r15_13_assess.sh` | One fixed script per host step (07, 08, 09, 11, 12, 13), LF. Each prints `key=value` lines only and ends `RESULT=expected` or `RESULT=unexpected`, as the collector's host checks do. Each keeps full logs in `/root/r15` on the host, never in its output |
| `docs/infrastructure_security/evidence_v2/R15/host/dc33_35.vars.json` | The six `PO_` values `tools/collector_host_checks/dc33_35_launcher_config.sh` needs (step 10) |
| `tests/test_aws_host_run_script.py` | The sender against a fake `aws` that records each call: one `send-command` with the export lines first, the timeout passed, the temporary file removed, the truncation flag set |

Nothing in round 0 touches the bundle, the tag or `msca-dn-pre-eval`. The scripts run on the host
against the installed bundle; they are not part of it.

## Points for the operator to settle (answers recorded in `RUNLOG.md` before round 0)

1. **How commands reach the host.** The agent proposes Run Command for every host step, sent by
   `host-run.ps1` from the workstation, as at R11, R12b and R14 step 08. Every output then lands in an
   evidence file by script, and no Session Manager plugin is needed. Run Command runs as `root`, and
   `ssm-user` exists only after a Session Manager session. So the working directory is `/root/r15`, not
   the runbook's `/home/ssm-user/an12`. The install target stays `/opt/msca-dn-anonymisation`. This is a
   recorded deviation from the runbook, not a change to it.
2. **Where the bundle lives.** The tarball and its `.sha256` go to
   `s3://<DeployBucketName>/bundles/msca-dn-freeze-2026-11-12/`. They stay there after R15: V14 and V16
   install the same bundle (W05's locked-revision rule), on fresh hosts. Storage is under 0.1 GB, under
   0.01 USD a month.
3. **One creation, both prompt forms.** PowerShell start (create path, step 06), CloudShell teardown
   (step 14). That runs each form's typed prompt once at a real terminal in one creation. **The test:**
   while the script works, before its prompt appears, press Enter twice. The prompt must still wait, and
   the log must show the word you typed after it. If the discard fails, the buffered Enter answers the
   prompt with `confirmed=no`, and nothing is created or deleted. That is a safe failure, recorded as a
   finding.
4. **Teardown at the end of R15.** The agent proposes no host survives R15. A stopped host still costs
   0.063916 USD an hour, about 1.53 USD a day, and V14 has no date yet. V14 creates a fresh host and
   installs from the same bucket object. R15 shows that install works.
5. **The receipt's attestations.** The pass refuses until the receipt's operator fields are filled.
   `r15_12_receipt.sh` writes them from fixed values, which the agent proposes here:
   - `authored_on`, `processing_route.verified_on`, `isolation_check.verified_on`: the run date (UTC,
     host clock).
   - `review_state` `operator_reviewed`; `declared_status` `Confirmed`; `written_by` "the operator, from
     values drafted by the agent in evidence_v2/R15/STEPS.md and approved in session".
   - `purpose`: "R15 (AN12 criterion 3): the synthetic Converse blind pass on the private host".
   - `processing_route.authority`: "ADR-001 for the new account (OD1-r1 eu-north-1, OD7 model set) and
     AN0 O6 (msca-dn-anonymisation-operator-decisions_2026-10-14): the harness blind assessor may call
     Bedrock Converse".
   - `processing_route.processing`: "the synthetic dev-graph world only
     (tests/fixtures/dev_graph_synthetic); no proposal text".
   - `processing_route.export`: "metadata only: exit codes, receipt check lines, file names, sizes and
     sha256 values; no model output leaves the host".
   - `processing_route.verified_by`, `isolation_check.verified_by`: "the operator".
   - `isolation_check.evidence`: `tests/harness/test_converse_judge.py::TestTheJudgeBuildsConverse`,
     `tests/harness/test_converse_smoke.py`, and "the rendered request in receipt_draft.json:
     tool_config_present false (step 11)".
6. **What comes back from the host.** Only metadata, and no model output:
   - the verification record, whole. Its values are versions, hashes and three settings that are
     written literally in `deploy/aws/templates/50-secret.yaml`;
   - for `prepare`: the exit code, the draft's sha256, the placeholder keys left, and the rendered
     request's five fields;
   - for `assess`: the exit code, the `check` lines, the name, size and sha256 of each file under
     `converse/baseline/`, and the checkpoint's line count.

   The assess log, the blind report, the frozen baseline and the receipt stay on the host and are
   deleted with it at step 14. They hold the synthetic world's model output. The receipt's sha256 and
   its `check` lines are the evidence, and the receipt is never stored in a checkout (ticket 13).
7. **Cost guard for the pass.** `r15_13_assess.sh` runs with a 3,600-second Run Command timeout. If it
   times out, stop, report, and go to step 14. The pass has no token budget of its own (AN12 known gap).
   Its size is fixed by the synthetic world: three criteria at the default sample counts.
8. **DC-33–35.** The agent proposes sending the collector's fixed `dc33_35_launcher_config.sh` alone by
   Run Command (step 10), as R14 sent the F7 script, not a collector run. The collector's open defects
   F-R12b-2 to -4 therefore do not block it. The agent then updates register v2 rows DC-33–35 and cites
   the step 10 file.

## Points the agent decided (the operator confirms or changes each on review)

9. **The verify probe.** `pypi.org:443` first. If its name does not resolve, the route is not measured
   (AN12 R8), and the script reruns the probe against `1.1.1.1:443` in the same step, as the runbook says.
10. **Assessor and tag.** Assessor `eu.anthropic.claude-sonnet-4-6` (OD7-assessor). Version tag
    `bedrock-converse-eu-north-1@<run date>`. The drafter is the secret's
    `eu.anthropic.claude-opus-4-6-v1`, so AN1c passes.
11. **The successor decision record.** `msca-dn-an12-host-run-r15_<date>.json`, successor to
    `msca-dn-an12-offline-bundle_2026-10-16.json`. It records criteria 1 and 3 as measured and closes
    three known gaps there: `install_host.sh` has run on Linux, the host's glibc is measured, and the
    private endpoint is measured. Criterion 2 stays out of scope (D1).
12. **Evidence names.** `R15_<step>_<name>`. CloudShell evidence comes back as `~/r15.tar.gz`, as at R14.

## Before you start

- **Sign in with `aws login --profile po-r1`**, never bare `aws login`.
- **Where commands run.** PowerShell in the VS Code terminal, repository root, for every step except
  05 and 14 (CloudShell). Every workstation AWS command names `--profile po-r1`.
- **`$E` must be set in every new PowerShell window.** Every block starts with it.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`. If `.venv-lint` is active, run `deactivate`
  before any `py -3.10` command.
- **Paste each block whole.** A cut paste leaves PowerShell at `>>`. Press Ctrl+C and paste again.
- **Never save** secret values, access keys, session tokens, passwords, the IMDS token, instance
  credentials, prompt or proposal text, or model output.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or `0.0.0.0/0` egress rule, not even temporarily.
  Bedrock model invocation logging stays disabled.
- If a step fails, stop, report the error in session, and do not improvise a fix. **If the host stack
  exists when you stop, run the teardown (step 14) unless the agent asks you to keep it. It costs by the
  hour.**
- **Rounds.**
  - **Round 0 (agent):** the files above, with tests. The agent commits them and states the step 03
    test count and the step 05 hashes.
  - **Round 1: steps 01–05.** Nothing billable by the hour. Hand back. The agent states the expected cost
    of round 2, and you give or withhold the go.
  - **Round 2: steps 06–15, in one sitting**, under the recorded go. Charges run from step 06 to step 14.
  - **Round 3: step 16** after the agent has written `VERIFICATION.md`, the decision record, the
    register rows and the worklog entry.

---

## Steps

### Step 01 — Session-start check and identity (R1-D2)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_01_budget-notifications.json"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_01_caller-identity.json"
Get-ChildItem "$E\R15_01_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R15_01_plan-state.json` | `accountPlanType` `FREE`; `accountPlanStatus` `ACTIVE`; expiry starts `2027-04-19`; credits recorded |
| `R15_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` `10.0`; `spend` recorded |
| `R15_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100) |
| `R15_01_caller-identity.json` | `Account` `797661577394`; `Arn` starts `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Plan not `ACTIVE`, or another account: stop and report. A notification in `ALARM`: report
it and wait for the agent.

### Step 02 — Read-only lookups (nothing is created)

Confirms that R14 left nothing behind, that the runtime secret exists, and what the bundle prefix holds.
The secret lookup reads its name and dates only, never its value.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$VPC = O "$V2\R4\R4_outputs.json" VpcId; $DB = O "$V2\R7\R7_outputs.json" DeployBucketName
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R15_02_host-stack-before.txt"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_02_vpc-endpoints-before.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query "Reservations[].Instances[].{id:InstanceId,state:State.Name}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_02_instances-before.json"
aws ec2 describe-volumes --profile po-r1 --region eu-north-1 --filters Name=tag:project,Values=proposal-orchestrator --query "Volumes[].{id:VolumeId,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_02_volumes-before.json"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_02_base-stacks.json"
aws secretsmanager describe-secret --profile po-r1 --region eu-north-1 --secret-id proposal-orchestrator/env-config --query "{name:Name,created:CreatedDate,changed:LastChangedDate,stages:VersionIdsToStages}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_02_secret.json"
aws s3api list-objects-v2 --profile po-r1 --region eu-north-1 --bucket $DB --prefix bundles/ --query "{count:length(Contents || ``[]``),keys:Contents[].Key}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R15_02_bundles-before.json"
Get-ChildItem "$E\R15_02_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R15_02_host-stack-before.txt` | Contains `ValidationError` and `does not exist`; last line `exit=254` |
| `R15_02_vpc-endpoints-before.json` | Exactly one entry: the S3 gateway endpoint of `R4_outputs.json`, `available` |
| `R15_02_instances-before.json`, `R15_02_volumes-before.json` | `[]` |
| `R15_02_base-stacks.json` | Equal to `R14_02_base-stacks.json` |
| `R15_02_secret.json` | `name` `proposal-orchestrator/env-config`; one version staged `AWSCURRENT`; `changed` equal to R8's |
| `R15_02_bundles-before.json` | `count` recorded; no key under `bundles/msca-dn-freeze-2026-11-12/` |

**STOP rule.** Any difference: stop and report.

### Step 03 — Workstation checks (no AWS call)

Checks that the tag and the tarball are still what O5 recorded, then runs the tests and the plan mode.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"; $B = "$HOME\o5\out"
& { git rev-parse 'msca-dn-freeze-2026-11-12^{commit}'; git rev-parse msca-dn-pre-eval; (Get-FileHash "$B\msca-dn-anonymisation-host.tar.gz" -Algorithm SHA256).Hash.ToLower(); (Get-Item "$B\msca-dn-anonymisation-host.tar.gz").Length; Get-Content "$B\msca-dn-anonymisation-host.tar.gz.sha256"; (Get-FileHash "$B\bundle_manifest.json" -Algorithm SHA256).Hash.ToLower() } 2>&1 | Out-File -Encoding utf8 "$E\R15_03_bundle.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R15_03_old-id-guard.txt"
$T = "tests/test_aws_host_lifecycle_scripts.py tests/runner/test_offline_bundle.py tests/harness/test_converse_smoke.py tests/test_anonymisation_host_runbook.py tests/tools/test_collect_evidence_v2.py tests/test_evidence_protocol_scaffold.py".Split(" ")
& { py -3.10 --version; py -3.10 -m pytest -q @T } 2>&1 | Out-File -Encoding utf8 "$E\R15_03_pytest.txt"
& { powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action plan -AwsProfile po-r1 -OutDir $E -Prefix R15_03; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R15_03_ps-plan.txt"
Get-Content "$E\R15_03_bundle.txt", "$E\R15_03_old-id-guard.txt"; Get-Content "$E\R15_03_pytest.txt" -Tail 1; Get-Content "$E\R15_03_ps-plan.txt" -Tail 3
```

The sender's own test file joins `$T` at round 0; the agent states the final list and count then.

| Evidence file | PASS criterion |
|---|---|
| `R15_03_bundle.txt` | Lines 1–2 `17e32d54f2bd60c1d69d9a1b6caa8688c34f036e`; line 3 `9c5351ef…132a` (in full, as above); line 4 `92413570`; line 5 the same hash and the tarball's name; line 6 `04f8218f…19dd` (in full, as above) |
| `R15_03_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R15_03_pytest.txt` | First line `Python 3.10.…`; last line the count the agent states at round 0; no `failed` or `error` |
| `R15_03_ps-plan.txt` | Last line `exit=0`; every `aws` line ends `--region eu-north-1 --profile po-r1` |

**STOP rule.** Any other hash, revision or count: stop. The bundle is not rebuilt; a changed tarball ends R15.

### Step 04 — Upload the bundle to the deploy bucket (no hourly cost)

The bucket encrypts with the project key by default, so the upload sends no encryption header (R7-D17).

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"; $V2 = "docs\infrastructure_security\evidence_v2"; $B = "$HOME\o5\out"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$DB = O "$V2\R7\R7_outputs.json" DeployBucketName; $P = "bundles/msca-dn-freeze-2026-11-12"
& { foreach ($f in "msca-dn-anonymisation-host.tar.gz", "msca-dn-anonymisation-host.tar.gz.sha256") { aws s3 cp "$B\$f" "s3://$DB/$P/$f" --profile po-r1 --region eu-north-1 --only-show-errors; "cp_exit=$LASTEXITCODE $f" } } 2>&1 | Out-File -Encoding utf8 "$E\R15_04_upload.txt"
& { foreach ($f in "msca-dn-anonymisation-host.tar.gz", "msca-dn-anonymisation-host.tar.gz.sha256") { aws s3api head-object --profile po-r1 --region eu-north-1 --bucket $DB --key "$P/$f" --query "{key:'$f',length:ContentLength,sse:ServerSideEncryption,kmsKey:SSEKMSKeyId,bucketKey:BucketKeyEnabled,version:VersionId}" --output json } } 2>&1 | Out-File -Encoding utf8 "$E\R15_04_head.json"
Get-Content "$E\R15_04_upload.txt", "$E\R15_04_head.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_04_upload.txt` | Two lines, each `cp_exit=0` and a file name; nothing else |
| `R15_04_head.json` | Tarball `length` `92413570`, `.sha256` `length` `100`; both `sse` `aws:kms`, `kmsKey` = `KeyArn` of `R6_outputs.json`, `bucketKey` true, a `version` |

### Step 05 — CloudShell: clean up R14, upload the fixed script, readiness (no cost)

Open the console in `eu-north-1`, then CloudShell. First remove R14's files:

```bash
rm -rf ~/r14 ~/r14.tar.gz ~/host-lifecycle.sh ~/90-host.yaml ~/host.json && ls -la ~
```

Upload three files (Actions → Upload file): `deploy/aws/scripts/host-lifecycle.sh`,
`deploy/aws/templates/90-host.yaml` and `deploy/aws/parameters/host.json`. Then run:

```bash
mkdir -p ~/r15 && bash ~/host-lifecycle.sh check ~/r15 R15_05 && tar -czf ~/r15.tar.gz -C ~/r15 . && ls -l ~/r15
```

Download `~/r15.tar.gz` (Actions → Download file) and unpack it into this folder:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
tar -xzf "$env:USERPROFILE\Downloads\r15.tar.gz" -C $E; Remove-Item "$env:USERPROFILE\Downloads\r15.tar.gz"; Get-Content "$E\R15_05_check.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_05_check.txt` | `caller_account=797661577394`; `region=eu-north-1`; `sha256_script` = `5fe7493484bddf8053b98cb107aa15cca9a208b76c60c35ffb02ea8dcb17a44f` (the F-R14-2 fix; R14 recorded `6dee8cb6…`); `sha256_template` = `d21723cbf5bdba274050513b60c7ec998d5b750a4de3b5c034a0382b7303771c` and `sha256_parameters` = `3847dadab3d8bdc4507bf6a10f76383577c39e9e01542dc46e526610a4e58f7b` (as R14); last line `RESULT=ready` |

The agent restates these three hashes at round 0 if round 0 changes any of the files.

**STOP — hand back here (end of round 1).** The agent states the expected cost of round 2: the planned
running hours at 0.154686 USD and the pass's token estimate at the Sonnet 4.6 Regional price. You give or
withhold the go. The agent records it in `RUNLOG.md` before step 06.

---

### Step 06 — PowerShell start, create path, with the typed-ahead test (hourly charges start)

**Only under the recorded go.** Run the block **once**. While the script works, before it asks, press
**Enter twice** (point 3). Then type `create` when it asks.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action start -AwsProfile po-r1 -OutDir $E -Prefix R15_06
```

Write in `RUNLOG.md` that you pressed Enter twice before the prompt, and whether the prompt still waited.

| Evidence file | PASS criterion |
|---|---|
| `R15_06_log.txt` | Start and end UTC; `path=create`; `confirmed=create` on this first run; last line `RESULT=started` |
| `R15_06_change-set.json` | Seven `Add` changes (six endpoints, `Host`); no capabilities; tag `project`; `InstanceType` `c7i-flex.large` |
| `R15_06_stack-status.json` | `CREATE_COMPLETE` |
| `R15_06_outputs.json` | The seven contract keys; values differ from `R14_12_outputs.json` |
| `R15_06_instance-information.json` | `ping` `Online`, `Amazon Linux` `2023` |

**STOP rule.** `confirmed=no` with no stack created: the discard failed. Report it; the agent records a
finding, and you run the block again without pressing anything early. Any other last line: report it
and run step 14 unless the stack does not exist.

### Step 07 — Host: fetch the bundle and check its sha256 (ticket criterion 1)

From here to step 13 each host step is one sender call. Each prints the host script's output when done.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-run.ps1 -AwsProfile po-r1 -Outputs "$E\R15_06_outputs.json" -Script "$E\host\r15_07_fetch.sh" -TimeoutSeconds 600 -Out "$E\R15_07_fetch.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_07_fetch.json` | `status` `Success`; stdout `cp_tar_exit=0`, `cp_sha_exit=0`, `size=92413570`, `sha256=9c5351ef709905c391fd82d06ccdacf1a806c255350241c6d88a21b4d0f2132a`, `sha256sum_check=OK`, free space on `/` and `/tmp` recorded, `RESULT=expected` |

This is the first real read of the deploy bucket from a host. R5 and R12b only simulated it. An
`AccessDenied` here is a finding about R5-D2 or the key policy: stop and report.

### Step 08 — Host: extract and install (runbook step 6)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-run.ps1 -AwsProfile po-r1 -Outputs "$E\R15_06_outputs.json" -Script "$E\host\r15_08_install.sh" -TimeoutSeconds 900 -Out "$E\R15_08_install.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_08_install.json` | `status` `Success`; stdout `install_exit=0`; `sums_failed=0` with `sums_ok` recorded; `python_version=Python 3.11.16`; `files_detail=all 299 files match the manifest`; `install_complete=yes`; `RESULT=expected` |

This is the first run of `install_host.sh` on Linux (AN12 known gap).

### Step 09 — Host: verify under the production configuration (AN12 criterion 1; ticket criteria 2 and 3)

The script runs runbook step 7 through the launcher, with `--record /root/r15/verification.json`, and
prints the record. Point 9 covers a probe name that does not resolve.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-run.ps1 -AwsProfile po-r1 -Outputs "$E\R15_06_outputs.json" -Script "$E\host\r15_09_verify.sh" -TimeoutSeconds 300 -Out "$E\R15_09_verify.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_09_verify.json` | `status` `Success`; stdout `verify_exit=0`; the record: `repository_revision` `17e32d54…`, `manifest_sha256` `04f8218f…`, `passed` true. Every check `passed` true: `files` (299), `interpreter` (3.11.16, x86_64), `glibc` (measured, at least 2.28), `extraction_pin`, `distributions` (16), `production_mode`, `diagnostic_level` (`metadata`), `transport` (`bedrock_converse`), `region` (`eu-north-1`), `private_endpoint` (all addresses private), `no_internet_route` (unreachable); `RESULT=expected` |

**STOP rule.** `no_internet_route` passed false (a connection was accepted) is a DC-32 failure: stop,
run step 14, and report. Any other failed check: stop and report.

### Step 10 — Host: DC-33–35 through the launcher

The collector's fixed script, sent alone (point 8). It prints the configuration's key names and its
sha256, never a value. `dc33_35.vars.json` carries the expected sha256
`1306b9914d0c1366ada204429d23200480d3aa7165cc4cab1553d0066fa6318a` (`R8_09_key-names-digest.txt`).

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-run.ps1 -AwsProfile po-r1 -Outputs "$E\R15_06_outputs.json" -Script tools\collector_host_checks\dc33_35_launcher_config.sh -VarsFile "$E\host\dc33_35.vars.json" -TimeoutSeconds 120 -Out "$E\R15_10_dc33-35.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_10_dc33-35.json` | `status` `Success`; stdout `launcher_exit=0`, `key_names=` the five keys of R8, `sha256_matches_template=yes`, `RESULT=expected` |

### Step 11 — Host: prepare the Converse pass (no model call)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-run.ps1 -AwsProfile po-r1 -Outputs "$E\R15_06_outputs.json" -Script "$E\host\r15_11_prepare.sh" -TimeoutSeconds 600 -Out "$E\R15_11_prepare.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_11_prepare.json` | `status` `Success`; stdout `prepare_exit=0`; `draft_sha256` recorded; `repository_revision=17e32d54…`; `model_pin` names `eu.anthropic.claude-sonnet-4-6` and `bedrock-converse-eu-north-1@`; `rendered_request` `model_id` `eu.anthropic.claude-sonnet-4-6`, `temperature` 0, `max_tokens` recorded, `tool_config_present` false, `region` `eu-north-1`; `placeholders=` exactly the point 5 fields; `RESULT=expected` |

### Step 12 — Host: fill the receipt and read it before the pass (V13)

The script writes the point 5 values into a copy of the draft, `/root/r15/readiness_receipt.json`
(mode 600), then runs `converse_smoke check`. No model call.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-run.ps1 -AwsProfile po-r1 -Outputs "$E\R15_06_outputs.json" -Script "$E\host\r15_12_receipt.sh" -TimeoutSeconds 300 -Out "$E\R15_12_receipt.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_12_receipt.json` | `status` `Success`; stdout `fill_exit=0`; `placeholders_left=none`; `receipt_sha256` recorded; `check_exit=0` and the line `receipt green`; `RESULT=expected` |

**STOP rule.** Any finding: report it. The agent reads the finding, and nothing is assessed until the
receipt is green.

### Step 13 — Host: the Converse blind pass and freeze (AN12 criterion 3; ticket criterion 4)

**The only step that calls a model.** Up to 60 minutes (point 7). The assess log stays on the host.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
"assess_sent_utc=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))" | Out-File -Encoding utf8 "$E\R15_13_window.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-run.ps1 -AwsProfile po-r1 -Outputs "$E\R15_06_outputs.json" -Script "$E\host\r15_13_assess.sh" -TimeoutSeconds 3600 -Out "$E\R15_13_assess.json"
"assess_done_utc=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))" | Out-File -Encoding utf8 -Append "$E\R15_13_window.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_13_assess.json` | `status` `Success`; stdout `assess_exit=0`; `report_count=1`; `checkpoint_lines` recorded; each file under `converse/baseline/` with size and sha256; `check_exit=0` and the line `receipt green`; no other text of the report; `RESULT=expected` |
| `R15_13_window.txt` | Both UTC times |

`assess_exit=1` lists findings (the pass ran; the receipt disagrees with the report). `assess_exit=2` is
a refusal. Report either as found and go to step 14.

### Step 14 — CloudShell teardown, end to end, with the typed-ahead test (end of the billable window)

In CloudShell. Keep the tab in front and wait for the last line. At R14 the wait was about four
minutes. While the script works, before it asks, press **Enter twice**. Then type `delete` when it asks,
and press nothing more until the last line.

```bash
rm -rf ~/r15 && mkdir -p ~/r15 && bash ~/host-lifecycle.sh teardown ~/r15 R15_14; tar -czf ~/r15.tar.gz -C ~/r15 .
```

Download and unpack as in step 05. Write the delete time (UTC) in `RUNLOG.md`.

| Evidence file | PASS criterion |
|---|---|
| `R15_14_log.txt` | `confirmed=delete` on this first run; last line `RESULT=deleted` |
| `R15_14_host-stack-after.txt` | `does not exist` |
| `R15_14_after-vpc-endpoints.json` | Only the S3 gateway endpoint |
| `R15_14_after-network-interfaces.json`, `R15_14_after-instances.json`, `R15_14_after-volumes.json` | `[]` |
| `R15_14_after-base-stacks.json` | The five base stacks as `R15_02_base-stacks.json`; the log shows `base_stacks_complete=5` |

From here nothing billable by the hour exists. **STOP rule.** `confirmed=no`: the discard failed. Report
it, then run the line again without pressing anything early. If the script is cut off before its last
line, report it; the agent gives the recovery block (R14-D5).

### Step 15 — CloudTrail: the pass's Converse events, metadata only (DC-26)

**Run no earlier than 15 minutes after `assess_done_utc`.** Same form as R12b step 11. The lookup keeps
selected fields only, parsed in memory.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
$W = Get-Content "$E\R15_13_window.txt"; $FROM = ($W[0] -split "=")[1]; $TO = ($W[1] -split "=")[1]
$raw = aws cloudtrail lookup-events --profile po-r1 --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=Converse --start-time $FROM --end-time $TO --max-items 500 --query "Events[].CloudTrailEvent" --output json
$sel = @(($raw | Out-String | ConvertFrom-Json) | ForEach-Object {
  $ev = $_ | ConvertFrom-Json
  [ordered]@{
    eventTime = $ev.eventTime; eventSource = $ev.eventSource; awsRegion = $ev.awsRegion
    userIdentityType = $ev.userIdentity.type; callerArn = $ev.userIdentity.arn
    sessionIssuerArn = $ev.userIdentity.sessionContext.sessionIssuer.arn; vpcEndpointId = $ev.vpcEndpointId
    modelId = $ev.requestParameters.modelId; errorCode = $ev.errorCode
  } })
ConvertTo-Json -InputObject $sel -Depth 3 | Out-File -Encoding utf8 "$E\R15_15_converse-events.json"
$raw = $null; $sel = $null
"events=$((Get-Content "$E\R15_15_converse-events.json" -Raw | ConvertFrom-Json).Count)"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_15_converse-events.json` | At least one event; the count recorded against `checkpoint_lines` of step 13. Every event: `awsRegion` `eu-north-1`; `userIdentityType` `AssumedRole`; `callerArn` = `arn:aws:sts::797661577394:assumed-role/proposal-orchestrator-runtime-role/<InstanceId of R15_06_outputs.json>`; `sessionIssuerArn` = `RuntimeRoleArn` of `R5_outputs.json`; `vpcEndpointId` = `BedrockRuntimeEndpointId` of `R15_06_outputs.json`; `modelId` the Sonnet 4.6 `eu.` profile; `errorCode` null |

**STOP rule.** No event after 30 minutes: repeat once (overwriting). Still none is a DC-26 FAIL to report.

**STOP — hand back here (end of round 2).** The agent checks every file by script and writes
`VERIFICATION.md`, the decision record (point 11), register v2 rows DC-33–35 and the worklog entry.

---

### Step 16 — Closing: tests, old-ID guard, then the secret scan

```powershell
$E = "docs\infrastructure_security\evidence_v2\R15"
$T = "<the list the agent states at round 0>".Split(" ")
& { py -3.10 --version; py -3.10 -m pytest -q @T } 2>&1 | Out-File -Encoding utf8 "$E\R15_16_pytest.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R15_16_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R15_16_secret-scan.txt"
Get-Content "$E\R15_16_pytest.txt" -Tail 1; Get-Content "$E\R15_16_old-id-guard.txt", "$E\R15_16_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R15_16_pytest.txt` | First line `Python 3.10.…`; last line the count the agent states with `VERIFICATION.md`; no `failed` or `error` |
| `R15_16_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R15_16_secret-scan.txt` | `CLEAN`; `exit=0` |

Then commit, and confirm R15 in session. The agent ticks the R15 criteria and A4 in the handoff.

## Ticket criteria and where they are evidenced

| Criterion (`plans/aws_redeployment_tickets.md`, R15) | Evidence |
|---|---|
| The bundle's sha256 on the host equals the one recorded at O5 | Step 07 |
| `runner.offline_bundle verify --probe-no-internet` passes on the host | Step 09 |
| The production configuration is verified on the host (AN12 criterion 1) | Steps 09 and 10 |
| The synthetic Converse blind pass freezes on the host with a validated receipt (AN12 criterion 3) | Steps 12, 13 and 15 |
| The successor decision record is committed | After round 2 (point 11) |

## Before you hand back

- [ ] Every evidence file listed above exists in this folder, under exactly its name.
- [ ] `RUNLOG.md` records the UTC times, the create and delete times, the typed confirmations, both
      typed-ahead tests, any deviation and any error.
- [ ] `proposal-orchestrator-host` does not exist (`R15_14_host-stack-after.txt`).
- [ ] The bundle and its `.sha256` remain in the deploy bucket for V14 and V16 (point 2).
- [ ] `~/r15` and `~/r15.tar.gz` are removed from CloudShell. The three uploaded files may stay for V14.
