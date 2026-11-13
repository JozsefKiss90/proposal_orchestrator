# V14 — step sheet

| Field | Value |
|---|---|
| Ticket | V14 (lane H2), runbook `plans/msca_dn_pe09_runbook.md` §4–§6 |
| Bundle | O5: tag `msca-dn-freeze-2026-11-12`, revision `17e32d54` |
| Decisions | `RUNLOG.md`: V14-OP1 to OP9, V14-A1, V14-D1 and D2 |
| Rehearsal | `REHEARSAL.md`. Every workstation command below ran there over an invented document |
| Who | The operator runs every step. The agent sees only the lines each step says to report, and the evidence files part H names |
| Account / region | `797661577394` / `eu-north-1`. Every AWS command names `--profile po-r1 --region eu-north-1` |
| Charges | Part W starts none. Part H starts hourly charges at H03 and needs the operator's go first |

## Names used below

| Name | What it is |
|---|---|
| `F` | `C:\Code\proposal_demo\freeze_bundle`, the freeze worktree at `17e32d54` |
| `R` | The private root: a new folder outside every checkout and outside any cloud-synced folder |
| `O` | The output folder for the archive: outside `R` and outside every checkout |
| `PF` | The workstation preflight folder: outside `R` and outside every checkout |
| `<workspace_rel>` | The `workspace_rel` you declare in the configuration input |
| `<manifest_name>` | The `manifest_name` of the revision you declare in the configuration input |

The original's document id is `MSCA-DN-2025_part_b_as_submitted` and its intake id is `msca-dn-2025-original`, both
fixed by the importer's `official_original` configuration.

## Part W — workstation (no AWS, no charges)

**Done 2026-11-12.** The results are in `RUNLOG.md` (Settling, V14-F7, V14-F8, the measured cost).

Run every `py -3.10 -m` line from `F` (`Set-Location C:\Code\proposal_demo\freeze_bundle`).

### W01 — the freeze worktree

```
git -C C:\Code\proposal_demo\freeze_bundle rev-parse HEAD
git -C C:\Code\proposal_demo\freeze_bundle status --porcelain
```

Expect `17e32d54f2bd60c1d69d9a1b6caa8688c34f036e`, then no output. **Report:** both.

### W02 — the private root

Create `R`. Put the authenticated PDF under it, for example at
`R\private\msca_dn_original\part_b_as_submitted.pdf`. The configuration's `pdf_rel` names that path later.

### W03 — §4 step 1a: measure the original

```
py -3.10 -m tools.import_external_proposal --document official_original --describe
py -3.10 -m tools.import_external_proposal --environment
py -3.10 -m tools.dry_import_original --pdf C:\Private\v14\R\private\msca_dn_original\part_b_as_submitted.pdf --expect-sha256 <hash from the authoritative source> --out C:\Private\v14\R\v08_dry_import --submission-id <the proposal number> --call-id <the 2025 call id>
```

Reconcile the worksheet against the PDF and fill in the acceptance record, as
`plans/msca_dn_v08_original_dry_import_procedure.md` says. Then:

```
py -3.10 -m tools.dry_import_original --check-acceptance C:\Private\v14\R\v08_dry_import\extraction_fidelity_acceptance.json
```

**Report:** the exit code of each line. Nothing else.

### W04 — §4 step 1b: configure and author the workspace

Copy `tools\original_configuration_template.json` to `R\original_configuration.json` and answer every value. Then:

```
py -3.10 -m tools.author_original_workspace --root C:\Private\v14\R --config-input original_configuration.json
```

Here `--config-input` is relative to `R`. **Report:** the exit code.

### W05 — §4 step 1c: import, in-process (V14-F3)

Do not run the runbook's `py -3.10 -m tools.import_external_proposal` form. At the tag it refuses after writing one
file (REHEARSAL.md R2). Run the same code in one module instance:

```
py -3.10 -c "import sys; from tools import import_external_proposal as m; sys.exit(m.main())" --document official_original --config-input C:\Private\v14\R\original_configuration.json --repo-root C:\Private\v14\R
```

Here `--config-input` is a full path under `R`. Read the measured checks against runbook §4's table yourself.
**Report:** the exit code, and the `findings:` and `unchecked:` counts.

### W06 — pack the inbound archive

```
py -3.10 C:\Code\proposal_demo\proposal_orchestrator\docs\infrastructure_security\evidence_v2\V14\workstation\v14_pack.py --freeze C:\Code\proposal_demo\freeze_bundle --root C:\Private\v14\R --config-input original_configuration.json --out-dir <O>
```

It writes the ten supplement files into `R` from the tag, checks each sha256, and refuses if an ESR record is under
`R`. It packs the workspace, the register and the supplement, and no PDF, dry-import record or configuration input
(V14-A1). It prints metadata only. **Report:** every line it prints.

### W07 — the workstation preflight

```
py -3.10 -m harness.commands.blind_assessment preflight --repo-root C:\Private\v14\R --document MSCA-DN-2025_part_b_as_submitted --graph-root C:\Private\v14\R\<workspace_rel> --profile harness/profiles/msca_dn_2025_historical.json --transport bedrock-converse --no-claims --grounding-scope content_focused --package-budget 400000 --criterion-budget 40000 --import-manifest C:\Private\v14\R\<workspace_rel>\docs\tier4_orchestration_state\dev_graph\imports\<manifest_name> --out-dir <PF>
```

No model call. Read the report yourself, flags included. Both budgets are required (V14-F7): at the defaults the package is
refused and the excellence criterion goes unscored. Two flags are expected and explained, tables 250 against 275 and
the word scan (V14-F8). **Report:** the exit code, the `pack set:` hash, and the
number of flags.

### W08 — the measured cost, and a clean worktree

```
py -3.10 C:\Code\proposal_demo\proposal_orchestrator\docs\infrastructure_security\evidence_v2\V14\workstation\v14_cost.py <PF>\preflight_<hash>_0001.json
git -C C:\Code\proposal_demo\freeze_bundle status --porcelain
```

The cost script prints counts, token totals and USD only. **Report:** its seven lines, and confirm that `status`
prints nothing.

The agent then replaces the cost statement's planned and upper figures with these and asks for the go. Done:
`RUNLOG.md`, cost statement.

## Part H — host

### How part H runs

- **Before you start.** Sign in with `aws login --profile po-r1`. Run every PowerShell block from the repository
  root in the VS Code terminal, and set `$E` first. Pipe to `Out-File -Encoding utf8`, never `>`. Paste each block
  whole. If `.venv-lint` is active, run `deactivate` first.
- **Host steps** go through `deploy/aws/scripts/host-run.ps1` (Run Command, as `root`), as at R15. Each host script
  is in `host/`, prints `key=value` metadata only and ends `RESULT=expected` or `RESULT=unexpected`. Its logs stay
  in `/root/v14` on the host.
- **The private root on the host** is `/root/v14/R` (mode 700). The receipt, the prepared lines and the logs sit
  beside it in `/root/v14`. Every command runs with `--repo-root /root/v14/R`.
- **Reading text (V14-OP4).** Only in an interactive Session Manager session, with the default document (V14-OP8):
  `aws ssm start-session --profile po-r1 --region eu-north-1 --target <InstanceId>`, with no `--document-name`, or
  the console's Connect button. Then `sudo -i`. Never read a report, a log or a comparison in Run Command output.
- **Never save** secret values, keys, session tokens, passwords, the IMDS token, instance credentials, prompt or
  proposal text, or model output. No Internet Gateway, NAT Gateway or `0.0.0.0/0` route or rule. Bedrock invocation
  logging stays off.
- **If a step fails,** stop and report it in session. If the host stack exists when you stop, run H07 (stop) unless
  the agent asks otherwise, and H11d (teardown) if the failure ends V14.
- **Evidence names.** `V14_<step>_<name>`, in this folder. The agent checks each file by script.

### P — points the go covers

The agent proposes these. The go accepts them, or you change them first.

- **P1. The assessor.** `eu.anthropic.claude-sonnet-4-6` (OD7-assessor), version tag
  `bedrock-converse-eu-north-1@<run date, UTC>`. The drafter is the secret's `eu.anthropic.claude-opus-4-6-v1`, so
  AN1c passes. `maxTokens` and the region come from the runtime secret through the launcher, as at R15.
- **P2. The receipt's attestations** (`host/v14_h05b_receipt.sh`, between the `FILL` markers). `review_state`
  `operator_reviewed`, `declared_status` `Confirmed`, the dates the run date, `verified_by` "the operator". Three
  values need your reading in particular:
  - `processing_route.authority`: the operator's own wording, given with the go on 2026-11-13 and recorded in
    `RUNLOG.md`. AN0 O6 approves the Converse transport only; it does not name the original's text, so the
    authority is the operator's decision.
  - `processing_route.processing`: the Part B page extract, declared Inferred, as packed in
    `input-20261112-40eb1f.tar.gz`; no Part A.
  - `processing_route.export`: metadata, numeric scores and spreads only (V14-OP2).
- **P3. Run Command timeout for the pass: 7,200 s.** 45 calls, with up to 6 retries each. If it times out, the
  checkpoint holds every answer so far: start H06 again with `host/v14_resume.vars.json` (V14-D2). Nothing is
  redrawn.
- **P4. Sittings.** Sitting 1: H03 to H06, then H07 (stop). Sitting 2: H08 to H09, then H07. Sitting 3 only for
  H08c (route ii). H10 runs from the workstation at any time 15 minutes after a window. H11 when V14 is confirmed.

### H01 — before any charge: budget, identity, session preferences, lookups

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$DB = O "$V2\R7\R7_outputs.json" DeployBucketName
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\V14_H01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\V14_H01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\V14_H01_budget-notifications.json"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\V14_H01_caller-identity.json"
$raw = aws ssm get-document --profile po-r1 --region eu-north-1 --name SSM-SessionManagerRunShell --query Content --output text 2>&1; $rc = $LASTEXITCODE
if ($rc -ne 0) { $sel = [ordered]@{ document = "absent"; exit = $rc; invalid_document = [bool](($raw | Out-String) -match "InvalidDocument") } }
else { $in = (($raw | Out-String) | ConvertFrom-Json).inputs
  $sel = [ordered]@{ document = "present"; s3BucketName = $in.s3BucketName; s3EncryptionEnabled = $in.s3EncryptionEnabled; cloudWatchLogGroupName = $in.cloudWatchLogGroupName; cloudWatchEncryptionEnabled = $in.cloudWatchEncryptionEnabled; cloudWatchStreamingEnabled = $in.cloudWatchStreamingEnabled } }
ConvertTo-Json -InputObject $sel | Out-File -Encoding utf8 "$E\V14_H01_session-preferences.json"; $raw = $null; $in = $null
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\V14_H01_host-stack-before.txt"
aws s3api list-objects-v2 --profile po-r1 --region eu-north-1 --bucket $DB --prefix bundles/ --query "Contents[].{key:Key,size:Size}" --output json 2>&1 | Out-File -Encoding utf8 "$E\V14_H01_bundles-before.json"
Get-ChildItem "$E\V14_H01_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `V14_H01_plan-state.json` | `ACTIVE`; credits recorded |
| `V14_H01_budgets.json`, `V14_H01_budget-notifications.json` | One budget, limit `10.0`; three notifications, none in `ALARM` |
| `V14_H01_caller-identity.json` | Account `797661577394`, role `AccountFullAccessRole` |
| `V14_H01_session-preferences.json` | `document` `absent` with `invalid_document` true (any other failure, such as an expired session, is not absence: rerun), or present with `s3BucketName` and `cloudWatchLogGroupName` empty and `cloudWatchStreamingEnabled` false or empty (V14-OP4, OP8). Only these fields are saved |
| `V14_H01_host-stack-before.txt` | `does not exist`; `exit=254` |
| `V14_H01_bundles-before.json` | The O5 tarball and its `.sha256` under `bundles/msca-dn-freeze-2026-11-12/`; no `input-…` key |

**STOP rule.** Session logging configured, or anything else different: stop and report.

### H02 — upload the input archive (no hourly cost)

Set `$O` to your output folder `O`. The bucket encrypts with the project key by default (R7-D17).

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $V2 = "docs\infrastructure_security\evidence_v2"; $O = "<O>"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$DB = O "$V2\R7\R7_outputs.json" DeployBucketName; $N = "input-20261112-40eb1f.tar.gz"
if ($O -match '[<>]' -or -not (Test-Path -LiteralPath "$O\$N")) { throw "H02 refused: set `$O to the W06 output folder holding $N" }
& { (Get-FileHash "$O\$N" -Algorithm SHA256).Hash.ToLower(); (Get-Item "$O\$N").Length; aws s3 cp "$O\$N" "s3://$DB/bundles/$N" --profile po-r1 --region eu-north-1 --only-show-errors; "cp_exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\V14_H02_upload.txt"
aws s3api head-object --profile po-r1 --region eu-north-1 --bucket $DB --key "bundles/$N" --query "{length:ContentLength,sse:ServerSideEncryption,kmsKey:SSEKMSKeyId,bucketKey:BucketKeyEnabled,version:VersionId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\V14_H02_head.json"
Get-Content "$E\V14_H02_upload.txt", "$E\V14_H02_head.json"
```

| Evidence file | PASS criterion |
|---|---|
| `V14_H02_upload.txt` | `406b15dcb1f790da957faf6720b338c908511fc4716b8b4f79f1ace126605174`; `194572`; `cp_exit=0` |
| `V14_H02_head.json` | `length` `194572`; `sse` `aws:kms`; `kmsKey` = `KeyArn` of `R6_outputs.json`; `bucketKey` true; a `version` |

**STOP — the go.** The agent records your go in `RUNLOG.md`, with P1 to P4, before H03.

### H03 — create the host stack (hourly charges start)

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action start -AwsProfile po-r1 -OutDir $E -Prefix V14_H03
```

Type `create` when it asks. **PASS:** as R15 step 06: `V14_H03_log.txt` ends `RESULT=started` with `path=create`;
seven `Add` changes; `CREATE_COMPLETE`; the host `Online`. Write the create time (UTC) in `RUNLOG.md`.

### H04 — bundle, install, verify, input

Four sends, in order. Each prints the host script's output.

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $S = "deploy\aws\scripts\host-run.ps1"; $X = "$E\V14_H03_outputs.json"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h04a_fetch.sh" -TimeoutSeconds 600 -Out "$E\V14_H04a_fetch.json"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h04b_install.sh" -TimeoutSeconds 900 -Out "$E\V14_H04b_install.json"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h04c_verify.sh" -TimeoutSeconds 300 -Out "$E\V14_H04c_verify.json"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_inbound.sh" -VarsFile "$E\host\v14_input.vars.json" -TimeoutSeconds 300 -Out "$E\V14_H04d_input.json"
```

| Evidence file | PASS criterion |
|---|---|
| `V14_H04a_fetch.json`, `V14_H04b_install.json`, `V14_H04c_verify.json` | As R15 steps 07, 08 and 09 |
| `V14_H04d_input.json` | `archive_sha256_matches=yes`; `members=19`, `workspace_files=8`, `registers=1`, `supplement_files=10`, `import_manifests=1`, `esr_records=0`; `in_app_equal=8`, `in_app_differ=0`; `root_mode=700`; `local_archive_removed=yes`; `RESULT=expected` |

Then delete every version of the input object, delete markers included (V14-OP1):

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $V2 = "docs\infrastructure_security\evidence_v2"; $N = "input-20261112-40eb1f.tar.gz"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$DB = O "$V2\R7\R7_outputs.json" DeployBucketName
& { $vs = aws s3api list-object-versions --profile po-r1 --region eu-north-1 --bucket $DB --prefix "bundles/$N" --query "{v:Versions[].VersionId,d:DeleteMarkers[].VersionId}" --output json | ConvertFrom-Json
  foreach ($v in @($vs.v) + @($vs.d)) { if ($v) { aws s3api delete-object --profile po-r1 --region eu-north-1 --bucket $DB --key "bundles/$N" --version-id $v --output json | Out-Null; "delete_exit=$LASTEXITCODE" } }
  aws s3api list-object-versions --profile po-r1 --region eu-north-1 --bucket $DB --prefix "bundles/$N" --query "{versions:length(Versions || ``[]``),markers:length(DeleteMarkers || ``[]``)}" --output json } 2>&1 | Out-File -Encoding utf8 "$E\V14_H04e_delete.txt"
Get-Content "$E\V14_H04e_delete.txt"
```

**PASS:** one or more `delete_exit=0` lines; then `versions` 0 and `markers` 0. An `AccessDenied` is a finding: stop and
report. The archive is already off the host's disk (`local_archive_removed=yes`).

### H05 — preflight and receipt on the host (no model call)

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $S = "deploy\aws\scripts\host-run.ps1"; $X = "$E\V14_H03_outputs.json"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h05a_prepare.sh" -TimeoutSeconds 900 -Out "$E\V14_H05a_prepare.json"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h05b_receipt.sh" -TimeoutSeconds 300 -Out "$E\V14_H05b_receipt.json"
```

| Evidence file | PASS criterion |
|---|---|
| `V14_H05a_prepare.json` | `preflight_exit=1` (the two V14-F8 flags) or 0; `pack_set_matches_w07=yes` (`sha256:fe975e4b8489`); `flags=2` with categories `tables` and `word scan`; `package_completeness=complete`, `package_budget=400000`; `packs=10`; `checkpoint_exists=no`; `repository_revision=17e32d54…`; `model_pin` per P1; the rendered request `model_id` the P1 model, `temperature` 0, `tool_config_present` false, `region` `eu-north-1`, `max_tokens` recorded; the thirteen placeholders; `RESULT=expected` |
| `V14_H05b_receipt.json` | `placeholders_left=none`; `receipt_mode=600`; `check_exit=0`; last check line `receipt check: green`; `RESULT=expected` |

**STOP rule.** Another pack set means the host measured another package than W07: stop. A receipt finding: report
it, and nothing is assessed until it is green.

### H06 — the blind pass and the freeze (the only model step)

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $S = "deploy\aws\scripts\host-run.ps1"; $X = "$E\V14_H03_outputs.json"
"assess_sent_utc=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))" | Out-File -Encoding utf8 "$E\V14_H06_window.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h06_assess.sh" -TimeoutSeconds 7200 -Out "$E\V14_H06_assess.json"
"assess_done_utc=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))" | Out-File -Encoding utf8 -Append "$E\V14_H06_window.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `V14_H06_assess.json` | `receipt_before_exit=0`; `assess_exit=0`; `report_count=1`; `candidate_count=1`; `live_calls` + `replayed_calls` = 45 + `discarded_draws` (V14-F9); `requests` recorded; `tool_config_sent=False`, `child_process=False`; `inference_config` `temperature` 0.0; `unscored_criteria=0`; `freeze_exit=0`; `baseline_files=2`; `freeze_checks_passed=22`; `receipt_after_exit=0`, `receipt check: green`; `RESULT=expected` |
| `V14_H06_window.txt` | Both UTC times |

**If it times out or stops** (`assess_exit` not 0, `report_count=0`, `checkpoint_lines` recorded): run the same
block with `-VarsFile "$E\host\v14_resume.vars.json"` and `-Out "$E\V14_H06_resume.json"`. It replays every answer
in the checkpoint and goes live from the first it lacks (V14-D2). A refusal (exit 2) is reported, not resumed.

Then stop the host (H07) unless you go straight on to H08.

### H07 — stop and start between sittings (V14-OP3, V14-D1)

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action stop -AwsProfile po-r1 -OutDir $E -Prefix V14_H07_stop<N>
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action start -AwsProfile po-r1 -OutDir $E -Prefix V14_H07_start<N>
```

`<N>` counts the sittings: 1, 2, 3. Stop ends `RESULT=stopped`. Start takes the resume path, asks for `start`, and
ends `RESULT=started`. A started host keeps `/root/v14`. After a start, use `V14_H07_start<N>_outputs.json` as
`$X` (the instance id is unchanged). Stopped, the stack costs 0.063916 USD an hour.

### H08 — after the freeze: the ESR record, the audit, the first comparison

**H08a. The ESR record, in its own archive.** On the workstation:

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $O = "<O>"
if ($O -match '[<>]') { throw "H08a refused: set `$O to your output folder" }
py -3.10 "$E\workstation\v14_pack_one.py" --freeze C:\Code\proposal_demo\freeze_bundle --esr --out-dir $O --vars-out "$E\host\v14_esr.vars.json"
```

It prints the archive name and sha256 and `member_sha256=5c9b9c8e9f89f501e30256aaa90b55921ce2c3673b2218fa2c0bcd6b7d54b0a9`.
Upload it as H02 with `$N` the new name (evidence `V14_H08a_upload.txt`, `V14_H08a_head.json`), send
`host/v14_inbound.sh` with `-VarsFile "$E\host\v14_esr.vars.json"` (`V14_H08a_esr.json`), then delete its versions
as in H04 (`V14_H08a_delete.txt`).

**PASS** for `V14_H08a_esr.json`: `archive_sha256_matches=yes`; `members=1`; `member_sha256` as above;
`esr_present_before=no`; `RESULT=expected`.

**H08b. The first audit.**

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $S = "deploy\aws\scripts\host-run.ps1"; $X = "<the latest outputs file>"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h08_audit.sh" -VarsFile "$E\host\v14_audit_first.vars.json" -TimeoutSeconds 900 -Out "$E\V14_H08b_audit.json"
```

**PASS:** `esr_present=yes`; `audit_exit` 0 or 1 (1 when it flags, which is advisory); `audit_reports=1`;
`audit_flags` recorded; `baseline_bound=bound`; `RESULT=expected`.

**H08c. The first comparison and its review, by route (iii), in an interactive session.** You write the dispositions
and the notes (V14-OP4). The commands, after `sudo -i`:

```bash
cd /opt/msca-dn-anonymisation/app
P=/opt/msca-dn-anonymisation/python/bin/python3
L="$P -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config --"
R=/root/v14/R; mkdir -p $R/private/msca_dn_original/esr_work
ls $R/reports/candidates $R/audit/first $R/private/msca_dn_original
```

Copy the rows of `$R/docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json`, not its
`esr_record_sha256` (runbook §6), into `$R/private/msca_dn_original/esr_work/dispositions_first.json`, schema 1.2. A
miss whose preservation is not declared stands `Inferred`, with no `fidelity_to_submitted_original` pointer
(V14-OP9). Then:

```bash
$L $P -m harness.commands.blind_assessment compare --repo-root $R --baseline-dir $R/baseline --esr $R/docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-original-esr.json --dispositions $R/private/msca_dn_original/esr_work/dispositions_first.json --candidate $R/reports/candidates/<the one directory> --register $R/private/msca_dn_original/<the register file> --audit $R/audit/first/<the audit file> --profile harness/profiles/msca_dn_2025_historical.json --out-dir $R/comparisons
$L $P -m harness.commands.blind_assessment review --repo-root $R --comparison $R/comparisons/<the comparison> --notes $R/private/msca_dn_original/esr_work/notes_first.json --profile harness/profiles/msca_dn_2025_historical.json --out-dir $R/reviews
```

`compare` exits 1 when it flags, which is advisory. Read the comparison and the review in the session only. Before
any route (ii) step, finish every `review` and `diff` that reads this comparison (V14-F6).

**H08d. Status.** After each interactive sitting:

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $S = "deploy\aws\scripts\host-run.ps1"; $X = "<the latest outputs file>"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_status.sh" -TimeoutSeconds 300 -Out "$E\V14_H08d_status<N>.json"
```

**PASS:** `RESULT=expected`; `root_mode=700`; the comparison, review and dispositions files listed by path, size and
sha256 only.

### H08e — route (ii), only for misses whose diagnosis needs `Confirmed` (V14-OP9)

1. **Workstation.** Write the declaration input at `<R>\private\msca_dn_original\declarations\<revision_id>.json`, a
   `fidelity_to_submitted_original` block in each needed `sub_sections` row (runbook §6). Run the W05 line with
   `--check` first. It must name the register alone. Then run it without `--check`.
2. **Pack and ship the register.**
   `py -3.10 "$E\workstation\v14_pack_one.py" --freeze C:\Code\proposal_demo\freeze_bundle --root <R> --register private/msca_dn_original/<the register file> --out-dir <O> --vars-out "$E\host\v14_register.vars.json"`.
   Upload as H02 (`V14_H08e_upload.txt`, `V14_H08e_head.json`). Send `host/v14_inbound.sh` with that vars file
   (`V14_H08e_register.json`). Delete its versions (`V14_H08e_delete.txt`). **PASS:** `members=1`;
   `register_sha256_before` and `register_sha256_after` differ; `register_kept_as` recorded; `RESULT=expected`.
3. **The successor audit:** H08b with `v14_audit_successor.vars.json`, out `V14_H08e_audit.json`.
4. **Interactive:** successor dispositions `dispositions_successor.json`, with `supersedes` the first and the
   `Confirmed` rows citing `declared/sub_sections/<id>/fidelity_to_submitted_original`. Then `compare` with
   `--audit $R/audit/successor/<file>`, `review`, and `diff` only between comparisons over the new register
   (`--before`, `--after`, `--out-dir $R/diffs`). Read the first comparison against the successor by observation id
   (V14-F6).
5. **Status:** H08d.

### H09 — what returns (V14-OP2)

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $S = "deploy\aws\scripts\host-run.ps1"; $X = "<the latest outputs file>"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h09_return.sh" -TimeoutSeconds 300 -Out "$E\V14_H09_return.json"
```

The script prints, by whitelist, the binding, call counts, each cell's score, agreement and sample scores, and each
criterion's score, spread, sample scores and weighting. No rationale, strength, shortcoming, quote, finding,
disposition or declaration. **PASS:** `reports=1`; `report_sha256` equal to H06's; no line holds prose; `RESULT=expected`.
The agent writes the repository record from this file alone.

### H10 — CloudTrail (no earlier than 15 minutes after a window)

**H10a. The pass's Converse events (DC-26).** The R15 step 15 block with `$E` set to this folder, the window from
`V14_H06_window.txt`, and out `V14_H10a_converse-events.json`. **PASS:** as R15 step 15, the caller the H03 instance,
`vpcEndpointId` the `BedrockRuntimeEndpointId` of `V14_H03_outputs.json`; the count recorded against
`live_calls` of H06.

**H10b. Session starts, with no document named (V14-OP8).**

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $FROM = "<the create time of H03, UTC>"; $TO = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$raw = aws cloudtrail lookup-events --profile po-r1 --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=StartSession --start-time $FROM --end-time $TO --max-items 200 --query "Events[].CloudTrailEvent" --output json
$sel = @(($raw | Out-String | ConvertFrom-Json) | ForEach-Object { $ev = $_ | ConvertFrom-Json
  [ordered]@{ eventTime = $ev.eventTime; callerArn = $ev.userIdentity.arn; target = $ev.requestParameters.target; documentName = $ev.requestParameters.documentName; errorCode = $ev.errorCode } })
ConvertTo-Json -InputObject $sel -Depth 3 | Out-File -Encoding utf8 "$E\V14_H10b_start-session.json"; $raw = $null; $sel = $null
"events=$((Get-Content "$E\V14_H10b_start-session.json" -Raw | ConvertFrom-Json).Count)"
```

**PASS:** one event per interactive session you opened; each `documentName` null; `target` the H03 instance.

### H11 — final teardown, when V14 is confirmed (V14-OP7, V14-D1)

**H11a. Credential check (counts only).**

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"; $S = "deploy\aws\scripts\host-run.ps1"; $X = "<the latest outputs file>"
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\v14_h11_credcheck.sh" -TimeoutSeconds 900 -Out "$E\V14_H11a_credcheck.json"
```

**PASS:** every `area` line `files_with_hit=0`; `RESULT=expected`. A hit: stop. No snapshot is taken, and the agent
reads the `hit_file` paths with you.

**H11b. Stop the host:** H07 stop with prefix `V14_H11b`. It writes `V14_H11b_volumes.json`.

**H11c. The snapshot: encrypted, private, dated.**

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"
$VOL = ((Get-Content "$E\V14_H11b_volumes.json" -Raw | ConvertFrom-Json) | Select-Object -First 1).id
$SNAP = aws ec2 create-snapshot --profile po-r1 --region eu-north-1 --volume-id $VOL --description "V14 private outputs (V14-OP7)" --tag-specifications "ResourceType=snapshot,Tags=[{Key=project,Value=proposal-orchestrator},{Key=purpose,Value=v14-private-outputs},{Key=delete-after,Value=2027-03-31}]" --query SnapshotId --output text
aws ec2 wait snapshot-completed --profile po-r1 --region eu-north-1 --snapshot-ids $SNAP
aws ec2 describe-snapshots --profile po-r1 --region eu-north-1 --snapshot-ids $SNAP --query "Snapshots[].{state:State,encrypted:Encrypted,kmsKey:KmsKeyId,size:VolumeSize,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\V14_H11c_snapshot.json"
aws ec2 describe-snapshot-attribute --profile po-r1 --region eu-north-1 --snapshot-id $SNAP --attribute createVolumePermission --query "CreateVolumePermissions" --output json 2>&1 | Out-File -Encoding utf8 "$E\V14_H11c_snapshot-permissions.json"
Get-Content "$E\V14_H11c_snapshot.json", "$E\V14_H11c_snapshot-permissions.json"
```

**PASS:** `state` `completed`; `encrypted` true; `kmsKey` the account's default EBS key (the volume's key, `90-host.yaml`);
tag `delete-after` `2027-03-31`; `V14_H11c_snapshot-permissions.json` is `[]`. When V16 is confirmed, the agent gives
the earlier date (30 days after), and you re-tag it.

**H11d. Teardown.** R15 step 14 in CloudShell, with `~/v14` and prefix `V14_H11d`:
`rm -rf ~/r15 ~/r15.tar.gz ~/v14 && mkdir -p ~/v14 && bash ~/host-lifecycle.sh teardown ~/v14 V14_H11d; tar -czf ~/v14.tar.gz -C ~/v14 .`
**PASS:** as R15 step 14. The snapshot is not a volume; it stays.

### H12 — closing (no AWS)

```powershell
$E = "docs\infrastructure_security\evidence_v2\V14"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\V14_H12_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\V14_H12_secret-scan.txt"
Get-Content "$E\V14_H12_old-id-guard.txt", "$E\V14_H12_secret-scan.txt"
```

**PASS:** `CLEAN`, `exit=0` both. Then commit, and confirm V14 in session.
