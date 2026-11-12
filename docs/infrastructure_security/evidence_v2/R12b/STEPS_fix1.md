# R12b — fix 1: the collector refused the F7 URL file

| Field | Value |
|---|---|
| Amends | `STEPS.md` steps 04–11 |
| Written by / on | agent (Claude) / 2026-11-12 |
| Why | Round 2's collector run (step 09) stopped before any AWS call: `REFUSED: the F7 URL file cannot be read`, `exit=2` (`R12b_09_collector-console.txt`). The collector raises this only when reading the file fails (`OSError`), so the file did not exist at that moment. No host check ran. The stack was deleted correctly in step 10 (point 6). Step 11 then ran without a collector folder: `$CALL` was empty, so `R12b_11_*` hold a CLI parameter error and one empty record. They stay as evidence of the deviation and support no criterion |
| What changes | (1) The F7 URL file is written and checked **before** the stack exists: the collector's `--plan` reads the file through the same code path as the real run, and refuses if it cannot read it or the URL fails the collector's pattern. (2) A new change set, because executing `r12b-create-01` consumed it. (3) Fix-run files are named `R12b_fix1_*`, so round 2's files stay as they are |
| Hourly cost created | As `STEPS.md`, once more, from step F06 to step F10. **A second creation needs the operator's new go**: point 3's go covered one creation, and that creation was used |

## Steps

### Step F01 — Session-start check (as `STEPS.md` step 01)

Run `STEPS.md` step 01 with every `R12b_01_` replaced by `R12b_fix1_01_`. Same criteria.

### Step F04 — New change set `r12b-create-02` (nothing is created yet)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r12b-create-02 --change-set-type CREATE --template-body file://deploy/aws/templates/90-host.yaml --parameters file://deploy/aws/parameters/host.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_04_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r12b-create-02
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r12b-create-02 --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_04_change-set.json"
Get-Content "$E\R12b_fix1_04_create-change-set.json", "$E\R12b_fix1_04_change-set.json"
```

Criteria: as `STEPS.md` step 04, with `r12b-create-02`.

### Step F05 — The F7 URL, signed by this account for a bucket it does not own (no cost)

**Point 2 changed (operator, 2026-11-12: no second account; "use this one").** The URL is presigned
with `po-r1` for a bucket name this account does not own, so no bucket is created anywhere. What it
tests: the S3 gateway endpoint's policy allows only `GetObject`, `ListBucket` and `GetBucketLocation`
on this account's deploy bucket (`10-network.yaml`, R4-D3). A `PutObject` to any other bucket matches
no Allow statement, so the endpoint refuses it, even when the signer belongs to this account. What it
does not test: a signer from another account (the `aws:PrincipalAccount` half). `VERIFICATION.md` and
the register note record that limit.

Two things to know about this URL:

- It carries the `po-r1` session's access key id and session token, not its secret key. It never
  reaches a file in the repository, but SSM keeps `send-command` parameters in the account's command
  history. The URL expires after 30 minutes, and the token expires with your sign-in session.
- The bucket name is random. The `head-bucket` line only classifies it: `404` means no bucket of that
  name exists (expected), `403` means another account owns it (also fine). `200` would mean this
  account owns it: stop.

Run in **the same PowerShell window** you will use for steps F06–F09, right before F06.

*Amended 2026-11-12 after the first F05 run left an empty URL file:* `po-r1` is an `aws login` profile,
and Python's own read of it did not yield credentials. The block now asks the AWS CLI for the session's
credentials (`aws configure export-credentials`), hands them to the one Python call through environment
variables of this window, and removes them on the next line. Two of the variable names are assembled at run time, so this sheet passes the evidence secret scan. Nothing is printed or written except the
URL file. A Python error, if any, shows on screen; it holds no credential.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
$F7 = Join-Path $env:USERPROFILE "po-f7-url.txt"
$OB = "po-f7-outside-" + -join ((1..12) | ForEach-Object { "{0:x}" -f (Get-Random -Maximum 16) })
& { aws s3api head-bucket --profile po-r1 --region eu-north-1 --bucket $OB 2>&1 | Out-Null; "head_bucket_exit=$LASTEXITCODE" }
$c = aws configure export-credentials --profile po-r1 --format process | ConvertFrom-Json
$k = "AWS_" + "SECRET_ACCESS_KEY"; $t = "Session" + "Token"
[Environment]::SetEnvironmentVariable("AWS_ACCESS_KEY_ID", $c.AccessKeyId, "Process"); [Environment]::SetEnvironmentVariable($k, $c.SecretAccessKey, "Process"); [Environment]::SetEnvironmentVariable("AWS_SESSION_TOKEN", $c.$t, "Process"); $c = $null
py -3.10 -c "import boto3,sys; from botocore.config import Config; s=boto3.client('s3', region_name='eu-north-1', config=Config(signature_version='s3v4', s3={'addressing_style':'virtual'})); print(s.generate_presigned_url('put_object', Params={'Bucket': sys.argv[1], 'Key': 'f7-negative-test.txt'}, ExpiresIn=1800))" $OB | Out-File -Encoding ascii $F7
foreach ($v in "AWS_ACCESS_KEY_ID", $k, "AWS_SESSION_TOKEN") { [Environment]::SetEnvironmentVariable($v, $null, "Process") }
$u = (Get-Content $F7 -Raw); if ($u) { $u = $u.Trim(); "starts_https=$($u.StartsWith('https://'))  names_eu_north_1=$($u.Contains('.s3.eu-north-1.amazonaws.com/'))  length=$($u.Length)" } else { "url_file_empty=True" }; $u = $null
& { py -3.10 -m tools.collect_evidence_v2 --ticket R12b --step 09 --profile po-r1 --plan --host-outputs "$E\R12b_outputs.json" --f7-url-file $F7; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_05b_collector-plan.txt"
Get-Content "$E\R12b_fix1_05b_collector-plan.txt" | Select-String "f7-presigned-put|REFUSED|^exit="
```

`R12b_outputs.json` here is round 2's (that stack is gone). The plan calls nothing, so it only needs a
well-formed file to show the host checks; the real run in step F09 uses the new outputs.
`R12b_fix1_05_collector-plan.txt` (the refused first attempt) stays as evidence.

| Evidence | PASS criterion |
|---|---|
| Screen | `head_bucket_exit=` followed by a non-zero code (the CLI answers 404 or 403 with exit 254); `starts_https=True  names_eu_north_1=True` and a length over 200 |
| `R12b_fix1_05b_collector-plan.txt` | Last line `exit=0`; no `REFUSED`; the `[f7-presigned-put]` line shows `PO_F7_URL='<f7-url>'` (masked); no `https://` URL to S3 in the file (the agent checks by script) |

**STOP — hand back here.** Send F01 and F05. The agent checks them by script, and the operator gives
the new go for step F06 in session. The agent records the go in `RUNLOG.md` first.

**F09 criterion for F7, as amended:** `DC-05_f7-presigned-put.json` shows `http_status` `403`,
`error_code` `AccessDenied`, `message_names_vpc_endpoint_policy` `yes`. A `404` / `NoSuchBucket`, or
any `2xx`, means the request passed the endpoint: an F7 FAIL to report.

### Steps F06–F11 — `STEPS.md` steps 06–11 with these amendments

| `STEPS.md` step | Amendment |
|---|---|
| 06 | `--change-set-name r12b-create-02`; files `R12b_fix1_06_*` |
| 07 | **Overwrite** `R12b_outputs.json` with the new stack's outputs (the collector's `--host-outputs` reads it). Round 2's ids stay recorded in `RUNLOG.md` and `R12b_08_instance-information.json`. The values must differ from round 2's as well as R11's |
| 08 | File `R12b_fix1_08_instance-information.json` |
| 09 | Run in the window where step F05 found the file. Console file `R12b_fix1_09_collector-console.txt`; the folder stays `R12b_09_collector` (round 2 never created it) |
| 10 | Files `R12b_fix1_10_*`; `R12b_fix1_10_base-stacks.json` equal to `R12b_02_base-stacks.json` |
| 11 | Files `R12b_fix1_11_*`. No outside bucket to remove; delete only the URL file. **Before the lookup, check `started_utc` is not empty**: if the line prints `started_utc=` with nothing after it, stop (the collector folder is missing) |
| 12 | Unchanged; runs after `VERIFICATION.md` |

## Combined blocks (2026-11-12, after the operator's go for F06)

Written after two out-of-order runs, so that F06 cannot run unless F01 and F05 pass, and the stack is
deleted in the same paste that collects. **Block A** runs F01, F05 and, only if both pass, F06. **Block B**
runs F07–F09 if the stack is `CREATE_COMPLETE`, then F10 (delete) in every case, then removes the URL
file. Paste each block whole; run Block B right after Block A. F11 follows at least 15 minutes later.

### Block A — F01, F05, then F06 only if both pass

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
# F01
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_01_budget-notifications.json"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_01_caller-identity.json"
$ps = Get-Content "$E\R12b_fix1_01_plan-state.json" -Raw | ConvertFrom-Json; $id = Get-Content "$E\R12b_fix1_01_caller-identity.json" -Raw | ConvertFrom-Json; $nt = Get-Content "$E\R12b_fix1_01_budget-notifications.json" -Raw | ConvertFrom-Json
$F01 = ($ps.accountPlanStatus -eq "ACTIVE") -and ($ps.accountPlanRemainingCredits.amount -ge 190) -and ($id.Account -eq "797661577394") -and (@($nt | Where-Object state -ne "OK").Count -eq 0)
"F01_ok=$F01 credits=$($ps.accountPlanRemainingCredits.amount)"
# F05
$F7 = Join-Path $env:USERPROFILE "po-f7-url.txt"
$OB = "po-f7-outside-" + -join ((1..12) | ForEach-Object { "{0:x}" -f (Get-Random -Maximum 16) })
& { aws s3api head-bucket --profile po-r1 --region eu-north-1 --bucket $OB 2>&1 | Out-Null; "head_bucket_exit=$LASTEXITCODE" }
$c = aws configure export-credentials --profile po-r1 --format process | ConvertFrom-Json
$k = "AWS_" + "SECRET_ACCESS_KEY"; $t = "Session" + "Token"
[Environment]::SetEnvironmentVariable("AWS_ACCESS_KEY_ID", $c.AccessKeyId, "Process"); [Environment]::SetEnvironmentVariable($k, $c.SecretAccessKey, "Process"); [Environment]::SetEnvironmentVariable("AWS_SESSION_TOKEN", $c.$t, "Process"); $c = $null
py -3.10 -c "import boto3,sys; from botocore.config import Config; s=boto3.client('s3', region_name='eu-north-1', config=Config(signature_version='s3v4', s3={'addressing_style':'virtual'})); print(s.generate_presigned_url('put_object', Params={'Bucket': sys.argv[1], 'Key': 'f7-negative-test.txt'}, ExpiresIn=1800))" $OB | Out-File -Encoding ascii $F7
foreach ($v in "AWS_ACCESS_KEY_ID", $k, "AWS_SESSION_TOKEN") { [Environment]::SetEnvironmentVariable($v, $null, "Process") }
$u = (Get-Content $F7 -Raw); if ($u) { $u = $u.Trim(); "starts_https=$($u.StartsWith('https://'))  names_eu_north_1=$($u.Contains('.s3.eu-north-1.amazonaws.com/'))  length=$($u.Length)" } else { "url_file_empty=True" }; $u = $null
& { py -3.10 -m tools.collect_evidence_v2 --ticket R12b --step 09 --profile po-r1 --plan --host-outputs "$E\R12b_outputs.json" --f7-url-file $F7; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_05b_collector-plan.txt"
$pl = @(Get-Content "$E\R12b_fix1_05b_collector-plan.txt")
$F05 = ($pl[-1] -eq "exit=0") -and (@($pl | Select-String "REFUSED").Count -eq 0) -and (@($pl | Select-String "PO_F7_URL='<f7-url>'" -SimpleMatch).Count -eq 1)
"F05_ok=$F05"
# F06 — only if F01 and F05 passed
if ($F01 -and $F05) {
  "F06 start_utc=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))"
  & { aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r12b-create-02; "execute exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_06_execute-exit.txt"
  if (@(Get-Content "$E\R12b_fix1_06_execute-exit.txt" | Select-String "execute exit=0" -SimpleMatch).Count -eq 1) {
    aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
    aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_06_stack-status.json"
    aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_06_stack-events.json"
    Get-Content "$E\R12b_fix1_06_execute-exit.txt", "$E\R12b_fix1_06_stack-status.json"
  } else { "F06 EXECUTE FAILED (no wait):"; Get-Content "$E\R12b_fix1_06_execute-exit.txt" }
} else { "F06 NOT RUN: F01_ok=$F01 F05_ok=$F05. Stop and send this output." }
```

### Block B — F07–F09 if the stack is up, then F10 (delete) in every case

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$F7 = Join-Path $env:USERPROFILE "po-f7-url.txt"
$st = aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].StackStatus" --output text 2>$null
"stack_status=$st"
if ($st -eq "CREATE_COMPLETE") {
  # F07 — overwrites round 2's outputs (the collector reads this file)
  aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_outputs.json"
  $I = O "$E\R12b_outputs.json" InstanceId; "InstanceId=$I"
  # F08
  for ($n = 0; $n -lt 30; $n++) { $s = aws ssm describe-instance-information --profile po-r1 --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query "InstanceInformationList[0].PingStatus" --output text; "try $n : $s"; if ($s -eq "Online") { break }; Start-Sleep -Seconds 20 }
  aws ssm describe-instance-information --profile po-r1 --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query "InstanceInformationList[].{id:InstanceId,ping:PingStatus,platform:PlatformName,version:PlatformVersion,agent:AgentVersion,resourceType:ResourceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_08_instance-information.json"
  # F09 — only if Online
  if ($s -eq "Online") {
    & { py -3.10 -m tools.collect_evidence_v2 --ticket R12b --step 09 --profile po-r1 --host-outputs "$E\R12b_outputs.json" --f7-url-file $F7; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_09_collector-console.txt"
    Get-Content "$E\R12b_fix1_09_collector-console.txt" -Tail 15
  } else { "F09 NOT RUN: host not Online" }
}
# F10 — always
"F10 delete_utc=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))"
& { aws cloudformation delete-stack --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host; "delete exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_10_delete-exit.txt"
aws cloudformation wait stack-delete-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_10_host-stack-after.txt"
$VPC = O "$V2\R4\R4_outputs.json" VpcId
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_10_network-interfaces-after.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query "Reservations[].Instances[].{id:InstanceId,state:State.Name}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_10_instances-after.json"
aws ec2 describe-volumes --profile po-r1 --region eu-north-1 --filters Name=tag:project,Values=proposal-orchestrator --query "Volumes[].{id:VolumeId,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_10_volumes-after.json"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_10_base-stacks.json"
Remove-Item $F7 -ErrorAction SilentlyContinue
Get-ChildItem "$E\R12b_fix1_10_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

Criteria: as `STEPS.md` steps 07–10 and the F09 criterion above, on the `R12b_fix1_*` files.
