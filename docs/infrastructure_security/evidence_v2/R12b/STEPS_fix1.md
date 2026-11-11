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

Run in **the same PowerShell window** you will use for steps F06–F09, right before F06:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
$F7 = Join-Path $env:USERPROFILE "po-f7-url.txt"
$OB = "po-f7-outside-" + -join ((1..12) | ForEach-Object { "{0:x}" -f (Get-Random -Maximum 16) })
& { aws s3api head-bucket --profile po-r1 --region eu-north-1 --bucket $OB 2>&1 | Out-Null; "head_bucket_exit=$LASTEXITCODE" }
py -3.10 -c "import boto3,sys; from botocore.config import Config; s=boto3.Session(profile_name='po-r1').client('s3', region_name='eu-north-1', config=Config(signature_version='s3v4', s3={'addressing_style':'virtual'})); print(s.generate_presigned_url('put_object', Params={'Bucket': sys.argv[1], 'Key': 'f7-negative-test.txt'}, ExpiresIn=1800))" $OB | Out-File -Encoding ascii $F7
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
