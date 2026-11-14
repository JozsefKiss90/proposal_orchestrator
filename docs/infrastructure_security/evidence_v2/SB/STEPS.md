# SB — step sheet

| Field | Value |
|---|---|
| Lane | Stage B drafting (MSCA-DN 2026 resubmission). Tickets in `.scratch/overhaul-2026-11/issues/` |
| Decisions | `docs/tier4_orchestration_state/decision_log/msca-dn-stage-b-drafting-lane_2026-11-14.json` (O1 to O5); `msca-dn-stage-b-export-route_2026-11-14.json` (E1 to E9, the export route) |
| Run log | `RUNLOG.md` |
| Who | The operator runs every step. The agent sees only the lines each step says to report, and the evidence files it names |
| Account / region | `797661577394` / `eu-north-1`. Every AWS command names `--profile po-r1 --region eu-north-1`. `host-run.ps1` and `sb_fetch.ps1` take `-AwsProfile po-r1` and read the region from `deploy/aws/parameters/host.json` |
| Charges | SB-T0 creates the lane's host stack and starts hourly charges. Stopped between sittings (SB-T4), the stack still costs about 0.064 USD an hour. Kept for the drafting lane (SB-OP1 in `RUNLOG.md`) |
| Scope so far | The tunnel's steps (B03) and the lane host's creation and stops (SB-T0, SB-T4). Later lane tickets add their own steps to this sheet |

## Names used below

| Name | What it is |
|---|---|
| `X` | The lane host's stack outputs file, with its `InstanceId`: `SB_T0_outputs.json`, or after a restart the newest `SB_T4_start<N>_outputs.json` (the instance id does not change) |
| `D` | The private landing folder: outside every checkout and outside any cloud-synced folder (E6). `sb_fetch.ps1` refuses a folder inside a git work tree; the cloud-sync part rests on you |
| `<n>` | The fetch number in this lane: 1, 2, 3 and so on. Never reused |

## How the steps run

- **Before you start.** Sign in with `aws login --profile po-r1 --region eu-north-1`. Run every PowerShell block from the repository
  root in the VS Code terminal. Pipe to `Out-File -Encoding utf8`, never `>`. Paste each block whole. If
  `.venv-lint` is active, run `deactivate` first.
- **Host steps** go through `deploy/aws/scripts/host-run.ps1` (Run Command, as `root`). Each host script prints
  `key=value` metadata only and ends `RESULT=expected` or `RESULT=unexpected`.
- **Reading text (V14-OP4, which stands: E4).** Only in an interactive Session Manager session:
  `aws ssm start-session --profile po-r1 --region eu-north-1 --target <InstanceId>`, with no `--document-name`.
  Then `sudo -i`. Never read a draft, a report or a log in Run Command output.
- **A fetch** opens a second kind of session, `AWS-StartPortForwardingSession`. E3 sets aside V14-OP8 for this
  lane only, so this document is allowed here and nowhere else.
- **Never save** secret values, keys, session tokens, passwords, the IMDS token, instance credentials, prompt or
  proposal text, or model output. **Nor the token of a fetch:** do not copy it from the Run Command history, the
  console or the host, and do not list Run Command parameters into any file (decision record G3). No Internet
  Gateway, NAT Gateway or `0.0.0.0/0` route or rule. Bedrock invocation logging stays off.
- **No fetch is retried by the script.** A failed fetch ends with exit 1. Run it again with the next `<n>`; it
  makes a new token.
- **If a step fails,** stop and report it in session.
- **Evidence names.** `SB_<step>_<name>`, in this folder. The agent checks each file by script, the token check
  included.

### P — points the operator fills before B04

The agent proposed these. The operator gave both on 2026-11-14.

- **P1. The decision record's two open points. Given 2026-11-14.** E5: every file the lane writes to
  `/root/sb/outbound/`, no narrower list of kinds. E7: the operator only, by SB-T2 into `D`; no onward channel yet
  (record G7).
- **P2. The export sentence of the Stage B receipt** (`processing_route.export`). The lane's receipt step copies
  this sentence verbatim between its `FILL` markers, as P2 was handled at V14 (`V14/host/v14_h05b_receipt.sh`).

```
FILL
the files the drafting lane writes to /root/sb/outbound/, as one archive served once on the host's loopback
address through a Session Manager port-forward session to a private folder on the operator's workstation, kept
only when its sha256 and size equal the host's (msca-dn-stage-b-export-route_2026-11-14, E1, E2, E5); the operator
is the only recipient (E7); nothing else leaves the host
FILL
```

## SB-T0 — create the lane's host (hourly charges start)

**SB-T0a. Before any charge: identity, session preferences, no host stack.**

```powershell
$E = "docs\infrastructure_security\evidence_v2\SB"
aws sts get-caller-identity --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\SB_T0a_caller-identity.json"
$raw = aws ssm get-document --profile po-r1 --region eu-north-1 --name SSM-SessionManagerRunShell --query Content --output text 2>&1; $rc = $LASTEXITCODE
if ($rc -ne 0) { $sel = [ordered]@{ document = "absent"; exit = $rc; invalid_document = [bool](($raw | Out-String) -match "InvalidDocument") } }
else { $in = (($raw | Out-String) | ConvertFrom-Json).inputs
  $sel = [ordered]@{ document = "present"; s3BucketName = $in.s3BucketName; s3EncryptionEnabled = $in.s3EncryptionEnabled; cloudWatchLogGroupName = $in.cloudWatchLogGroupName; cloudWatchEncryptionEnabled = $in.cloudWatchEncryptionEnabled; cloudWatchStreamingEnabled = $in.cloudWatchStreamingEnabled } }
ConvertTo-Json -InputObject $sel | Out-File -Encoding utf8 "$E\SB_T0a_session-preferences.json"; $raw = $null; $in = $null
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\SB_T0a_host-stack-before.txt"
Get-ChildItem "$E\SB_T0a_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `SB_T0a_caller-identity.json` | Account `797661577394`, role `AccountFullAccessRole` |
| `SB_T0a_session-preferences.json` | `document` `absent` with `invalid_document` true (any other failure, such as an expired session, is not absence: rerun), or present with `s3BucketName` and `cloudWatchLogGroupName` empty and `cloudWatchStreamingEnabled` false or empty (E8) |
| `SB_T0a_host-stack-before.txt` | `does not exist`; `exit=254` |

Also report `plugin=$(session-manager-plugin --version)`. **PASS:** a version number. `sb_fetch.ps1` and every
interactive session need the plugin on PATH. Not found: install it, open a new PowerShell window, rerun the line.

**STOP rule.** Session logging configured, a host stack already there, no plugin, or anything else different: stop
and report.

**SB-T0b. Create the host stack.**

```powershell
$E = "docs\infrastructure_security\evidence_v2\SB"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action start -AwsProfile po-r1 -OutDir $E -Prefix SB_T0
```

Type `create` when it asks. **PASS:** as V14 H03: `SB_T0_log.txt` ends `RESULT=started` with `path=create`; seven
`Add` changes; `CREATE_COMPLETE`; the host `Online`. **Report:** the last line, and the create time (UTC), which the
agent writes in `RUNLOG.md`. SB-T3 counts from that time. Then SB-T1 at once.

The host is bare: no bundle, no inputs. The smoke needs none. The serve script uses the system `python3` when the
bundled interpreter is absent, and prints which one in `interpreter=`.

## SB-T1 — smoke on an invented file (ticket B04)

Before the first fetch. No private file is on the host. The smoke file is invented text that `sb_smoke_seed.sh`
writes on the host.

**SB-T1a. The plugin, and the bucket before.**

```powershell
$E = "docs\infrastructure_security\evidence_v2\SB"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$DB = O "$V2\R7\R7_outputs.json" DeployBucketName
"plugin=$(session-manager-plugin --version)"
aws s3api list-objects-v2 --profile po-r1 --region eu-north-1 --bucket $DB --prefix bundles/ --query "Contents[].{key:Key,size:Size}" --output json 2>&1 | Out-File -Encoding utf8 "$E\SB_T1_bundles-before.json"
```

**Report:** the `plugin=` line.

**SB-T1b. Seed, then fetch.** Set `$X` and `$D`. The vars file holds a size only, so it may sit in the temp folder.

```powershell
$E = "docs\infrastructure_security\evidence_v2\SB"; $S = "deploy\aws\scripts\host-run.ps1"; $X = "<X>"; $D = "<D>"
$V = Join-Path $env:TEMP "po-sb-seed.json"; [IO.File]::WriteAllText($V, '{"PO_BYTES": "1000000"}')
powershell -NoProfile -ExecutionPolicy Bypass -File $S -AwsProfile po-r1 -Outputs $X -Script "$E\host\sb_smoke_seed.sh" -VarsFile $V -TimeoutSeconds 600 -Out "$E\SB_T1_seed.json"; Remove-Item $V
powershell -NoProfile -ExecutionPolicy Bypass -File "$E\workstation\sb_fetch.ps1" -AwsProfile po-r1 -Outputs $X -Dest $D -Out "$E\SB_T1_fetch.json"; "exit=$LASTEXITCODE"
```

**Report:** the `result=` line and `exit=`.

**SB-T1c. Check the smoke file.** It unpacks the archive into a new sub-folder of `D` and hashes `smoke.txt`.

```powershell
$E = "docs\infrastructure_security\evidence_v2\SB"; $D = "<D>"; $F = "$E\SB_T1_fetch.json"
$A = (Get-Content $F -Raw | ConvertFrom-Json).archive; $C = Join-Path $D ("check-" + $A.Replace(".tar.gz", ""))
New-Item -ItemType Directory $C | Out-Null; tar -xzf (Join-Path $D $A) -C $C
"files=$((Get-ChildItem $C -Recurse -File).Count) smoke_sha256=$((Get-FileHash (Join-Path $C 'smoke.txt') -Algorithm SHA256).Hash.ToLower())"
```

**Report:** the line. **PASS:** `files=1`, and `smoke_sha256` equals `seed_sha256` in `SB_T1_seed.json`.

**SB-T1d. Empty the host folder.** In an interactive session (no document named), as `root`:
`rm -f /root/sb/outbound/smoke.txt && ls -A /root/sb/outbound | wc -l`. **Report:** the count, which must be `0`.

**SB-T1e. Seed and fetch again at 5,000,000 bytes.** SB-T1b with `"PO_BYTES": "5000000"` and out files
`SB_T1_seed2.json` and `SB_T1_fetch2.json`, then SB-T1c with `$F = "$E\SB_T1_fetch2.json"`, then SB-T1d.

**SB-T1f. Host state after the fetches.** No script in the tree prints it yet, so read it in an interactive
session (no document named), as `root`:
`ss -Hltn 'sport = :8765' | wc -l; ls -A /root/sb/outbound | wc -l; ls -A /root/sb/export | wc -l`.
**Report:** the three counts. B04 names an evidence file `SB_T1_after.json` for this; see `RUNLOG.md`, SB-F1.

**SB-T1g. The bucket after.** SB-T1a with out `SB_T1_bundles-after.json`, then
`Compare-Object (Get-Content "$E\SB_T1_bundles-before.json") (Get-Content "$E\SB_T1_bundles-after.json")`.
**Report:** whether `Compare-Object` printed anything.

**SB-T1h.** Delete the fetched archives and the `check-` folders from `D`.

**SB-T1i.** Stop the host: SB-T4 stop with `<N>` 1. Run SB-T3 15 minutes after the second fetch; it needs no running host.

| Evidence | PASS criterion |
|---|---|
| `SB_T1_seed.json`, `SB_T1_seed2.json` | status `Success`; stdout `seed_bytes` 1000000 (then 5000000), `RESULT=expected` |
| `SB_T1_fetch.json`, `SB_T1_fetch2.json` | the reported `exit=0`; `kept` true; `sha256_match` true; `session_terminated` true; `host_lines`: `served=yes`, `listening=127.0.0.1:8765`, `refused_requests=0`, `members=1`, `archive_deleted=yes`, `RESULT=expected` |
| SB-T1c, twice | `files=1`; `smoke_sha256` equal to that fetch's `seed_sha256` |
| SB-T1f | `0`, `0`, `0` |
| `SB_T1_bundles-*.json` | `Compare-Object` prints nothing |
| Every `SB_T1_*` file | no 64-hex value outside the named sha256 fields (`seed_sha256`, `archive_sha256`, `host_sha256`, `local_sha256`, and host-run's `script_sha256`); the agent checks by script |

The agent records each fetch's seconds (`end_utc` minus `start_utc`) in `RUNLOG.md`. They cover the whole fetch, Run
Command start-up and clean-up included, so they are not a throughput measure. Then SB-T3, no earlier than
15 minutes after the second fetch.

**If it fails.** `start-session` refused or the plugin too old: report the error line; the fix is on the
workstation or in the role. The tunnel opens but no download starts: report the fetch file. Two failed attempts
after a fix: stop, and use the fallback of decision record E9 for the first drafting run.

## SB-T4 — stop and start between sittings (SB-OP1)

```powershell
$E = "docs\infrastructure_security\evidence_v2\SB"
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action stop -AwsProfile po-r1 -OutDir $E -Prefix SB_T4_stop<N>
powershell -NoProfile -ExecutionPolicy Bypass -File deploy\aws\scripts\host-lifecycle.ps1 -Action start -AwsProfile po-r1 -OutDir $E -Prefix SB_T4_start<N>
```

Run one line, not both. `<N>` counts the sittings: 1, 2, 3. Stop ends `RESULT=stopped`. Start takes the resume
path, asks for `start`, and ends `RESULT=started`; then use `SB_T4_start<N>_outputs.json` as `X`. A started host
keeps `/root/sb`. **Report:** the last line of the log. Teardown is the drafting lane's own step, when the lane ends.

## SB-T2 — fetch (every later export)

The drafting lane has written its files to `/root/sb/outbound/`. They must be only the kinds E5 allows.

```powershell
$E = "docs\infrastructure_security\evidence_v2\SB"; $X = "<X>"; $D = "<D>"; $N = "<n>"
powershell -NoProfile -ExecutionPolicy Bypass -File "$E\workstation\sb_fetch.ps1" -AwsProfile po-r1 -Outputs $X -Dest $D -Out "$E\SB_T2_fetch-$N.json"; "exit=$LASTEXITCODE"
```

**Report:** the `result=` line and `exit=`.

**PASS:** the reported `exit=0`; in `SB_T2_fetch-<n>.json`, `kept` true, `sha256_match` true, `bytes` equal to `host_bytes`,
`session_terminated` true, and `host_lines` with `served=yes`, `refused_requests=0` and `RESULT=expected`. Only
`kept` true proves delivery (E2): `served=yes` means sent, not received.

**After a PASS.** The archive stays in `D`. The files in `/root/sb/outbound/` stay on the host until the lane's own
step clears them. A second fetch of the same files is a new `<n>`. The serve script refuses an outbound folder that
holds nothing.

## SB-T3 — CloudTrail, no earlier than 15 minutes after a fetch

CloudTrail can take 15 minutes to show an event, so an earlier run undercounts. Set `$FROM` to the creation time of
the lane's host stack, UTC, and `$OUT` to the evidence name: `SB_T3_start-session.json` for B04, then
`SB_T3_start-session-<n>.json` with the next free number. Each run covers every session since the host was
made.

```powershell
$E = "docs\infrastructure_security\evidence_v2\SB"; $X = "<X>"; $OUT = "<SB_T3_start-session.json or SB_T3_start-session-<n>.json>"; $FROM = "<the creation time of the lane's host stack, UTC>"; $TO = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$I = ((Get-Content $X -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq InstanceId).OutputValue
$raw = aws cloudtrail lookup-events --profile po-r1 --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=StartSession --start-time $FROM --end-time $TO --max-items 200 --query "Events[].CloudTrailEvent" --output json
$sel = @(($raw | Out-String | ConvertFrom-Json) | ForEach-Object { $ev = $_ | ConvertFrom-Json
  [ordered]@{ eventTime = $ev.eventTime; callerArn = $ev.userIdentity.arn; target = $ev.requestParameters.target; documentName = $ev.requestParameters.documentName; errorCode = $ev.errorCode } })
ConvertTo-Json -InputObject $sel -Depth 3 | Out-File -Encoding utf8 "$E\$OUT"; $raw = $null
"events=$($sel.Count) port_forward=$(@($sel | Where-Object { $_.documentName -eq 'AWS-StartPortForwardingSession' }).Count) interactive=$(@($sel | Where-Object { -not $_.documentName -and -not $_.errorCode }).Count) other_caller=$(@($sel | Where-Object { $_.callerArn -notlike '*:assumed-role/AccountFullAccessRole/*' }).Count) other_target=$(@($sel | Where-Object { $_.target -ne $I }).Count) errors=$(@($sel | Where-Object { $_.errorCode }).Count)"; $sel = $null
```

**Report:** the counts line, and how many fetches and interactive sessions you made since the host was created.

**PASS:**

- every `StartSession` is by the operator's role (`assumed-role/AccountFullAccessRole/`) and targets the lane's
  instance;
- a fetch shows `documentName` `AWS-StartPortForwardingSession`; an interactive session shows it null;
- `port_forward` equals the fetches you made, and `interactive` equals the interactive sessions you opened;
- `other_caller=0`, `other_target=0` and `errors=0`.

An event by any other caller fails the step, even a refused one, as the instance role's three calls in V14-F10
would. Stop and give your account of it in session.
