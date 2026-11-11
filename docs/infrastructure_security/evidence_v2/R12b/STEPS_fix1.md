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

### Step F05 — The F7 URL file, then the collector reads it (no cost, no URL on screen)

First run `STEPS.md` step 05 unchanged, in **the same PowerShell window** you will use for steps F06–F09.
If the second-account bucket still exists from round 2, `create-bucket` reports
`BucketAlreadyOwnedByYou`; that is fine. Then:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12b"
$F7 = Join-Path $env:USERPROFILE "po-f7-url.txt"
"exists=$(Test-Path $F7)"
& { py -3.10 -m tools.collect_evidence_v2 --ticket R12b --step 09 --profile po-r1 --plan --host-outputs "$E\R12b_outputs.json" --f7-url-file $F7; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12b_fix1_05_collector-plan.txt"
Get-Content "$E\R12b_fix1_05_collector-plan.txt" | Select-String "f7-presigned-put|REFUSED|^exit="
```

`R12b_outputs.json` here is round 2's (that stack is gone). The plan calls nothing, so it only needs a
well-formed file to show the host checks; the real run in step F09 uses the new outputs.

| Evidence | PASS criterion |
|---|---|
| Screen | `exists=True` |
| `R12b_fix1_05_collector-plan.txt` | Last line `exit=0`; no `REFUSED`; the `[f7-presigned-put]` line shows `PO_F7_URL='<f7-url>'` (masked); the file holds no `https://` URL to S3 (the agent checks by script) |

**STOP — hand back here.** Send F01, F04 and F05. The agent checks them by script, and the operator gives
the new go for step F06 in session. The agent records the go in `RUNLOG.md` first.

### Steps F06–F11 — `STEPS.md` steps 06–11 with these amendments

| `STEPS.md` step | Amendment |
|---|---|
| 06 | `--change-set-name r12b-create-02`; files `R12b_fix1_06_*` |
| 07 | **Overwrite** `R12b_outputs.json` with the new stack's outputs (the collector's `--host-outputs` reads it). Round 2's ids stay recorded in `RUNLOG.md` and `R12b_08_instance-information.json`. The values must differ from round 2's as well as R11's |
| 08 | File `R12b_fix1_08_instance-information.json` |
| 09 | Run in the window where step F05 found the file. Console file `R12b_fix1_09_collector-console.txt`; the folder stays `R12b_09_collector` (round 2 never created it) |
| 10 | Files `R12b_fix1_10_*`; `R12b_fix1_10_base-stacks.json` equal to `R12b_02_base-stacks.json` |
| 11 | Files `R12b_fix1_11_*`. **Before the lookup, check `started_utc` is not empty**: if the line prints `started_utc=` with nothing after it, stop (the collector folder is missing) |
| 12 | Unchanged; runs after `VERIFICATION.md` |
