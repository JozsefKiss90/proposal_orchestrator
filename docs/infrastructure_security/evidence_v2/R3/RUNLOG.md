# R3 — run log

Kept by the agent from what the operator reports in session (marked as such).

| Field | Value |
|---|---|
| Step sheet | `STEPS.md` |
| Run date (UTC) | 2026-10-22 (steps 01–10), 2026-10-23 (steps 11–12) |
| Operator | the operator (József) |
| Where run | PowerShell in the VS Code terminal on the workstation, repository root, profile `po-r1` (`aws login` at ~14:45 UTC as `assumed-role/AccountFullAccessRole/<session>`) |
| Hourly-cost go given | n/a (R3 creates nothing) |

## Steps

| Step | Started (UTC) | Run by | Result | Deviation from the step sheet | Error, and what was done about it |
|---|---|---|---|---|---|
| 01 | ~14:47 | operator (reported in session) | ok | none | none. Plan FREE / ACTIVE, credits 199.99 USD, expires 2027-04-19; one budget `My Monthly Cost Budget` 10.0 USD, spend 0.006; notifications ACTUAL 100, ACTUAL 85, FORECASTED 100 all `OK`. STOP rule not triggered. Files are UTF-8 with BOM (Windows PowerShell `Out-File`). |
| 02 | ~14:51 | operator (reported in session) | ok | none | none. `Account` 797661577394; `Arn` assumed-role/AccountFullAccessRole/<session>. |
| 03 | ~14:52 | operator (reported in session) | ok | none | none. `.venv-lint` created with `py -3.10`; pip installed cfn-lint 1.57.2 and its dependencies (pip's own upgrade notice ignored). Lint output: `cfn-lint 1.57.2`, `cfn-lint exit=0`, nothing between. `.venv-lint/` does not show in `git status` (ignored). |
| 04 | ~14:53 | operator (reported in session) | ok | none | none. Three zones, all `availability-zone`, `available`, `opt-in-not-required`: eu-north-1a (eun1-az1), eu-north-1b (eun1-az2), eu-north-1c (eun1-az3). |
| 05 | ~14:54 | operator (reported in session) | ok | none | none. Six `Interface` services, each with private DNS, each offered in eu-north-1a, -1b and -1c. Intersection: all three; agent picks the first by name, **eu-north-1a (eun1-az1)**. |
| 06 | ~14:55 | operator (reported in session) | ok | none | none. One list: `pl-c3aa4faa`, `com.amazonaws.eu-north-1.s3`, owner `AWS`, `create-complete`. |
| 07 | ~14:55 | operator (reported in session) | ok | none | none. AL2023 x86_64 public parameter readable in eu-north-1: one `String` parameter, value `ami-0111419d42d14a400` (modified 2026-10-22T02:08:22.139000+02:00); `invalid` empty. |
| 08 | ~14:57 | operator (reported in session) | ok | none | none. `validate-template` exit 0 for all six skeletons. Agent check of the six JSON files: each `Parameters` key set equals the template's declared parameters; `Description` present; no `Capabilities`; no other keys. The CloudFormation service answers in eu-north-1 and no SCP refused the call. |
| 09 | ~15:00 | operator (reported in session) | ok | none | none. `list-stacks` `[]`; `list-exports` `Exports: []`. R3 created nothing. |
| 10 | ~15:01 | operator (reported in session) | ok | none | none. FREE / ACTIVE, credits 199.99 USD, unchanged from step 01. First round (steps 01–10) complete. |
| 11 | 2026-10-23 ~14:35 | operator (reported in session) | ok after a re-run | First attempt in a new PowerShell window: `$E` was unset, so `Out-File` targeted `C:\R3_11_*.txt` and was refused (access denied; nothing written). The lint venv was also active. Re-run after `deactivate` and setting `$E` again | none on the re-run. pytest `Python 3.10.6`, `105 passed`; template guard `CLEAN: 6 template(s)`, `exit=0`; old-ID guard `CLEAN … (20 ids checked)`, `exit=0`. |
| 12 | 2026-10-23 ~14:37 | operator (reported in session) | ok | none | none. `CLEAN: docs/infrastructure_security/evidence_v2/R3`, `exit=0`. |
| 11 | 2026-10-22 ~15:03 | operator (files found by the agent on 2026-10-23; the run was not reported in session) | ok | none | none. `R3_11_pytest.txt`: win32, Python 3.10.6 (system interpreter, not the lint venv), 105 passed. `R3_11_template-guard.txt`: CLEAN, 6 templates, exit=0. `R3_11_old-id-guard.txt`: CLEAN, 20 ids, exit=0. |
| 11 (repeat) | 2026-10-23 ~14:30 | operator (reported in session) | failed, no effect | Run in a new PowerShell window without `$E` set | `Out-File` was refused access to `C:\R3_11_*.txt` (the path resolved to the drive root). Nothing was written; the 2026-10-22 step 11 files are unchanged (mtime 2026-10-22 15:03–15:04 UTC). Agent: the 2026-10-22 run stands as step 11's evidence; `$E` to be set again before step 12. |
| 09 | ~14:59 | operator (reported in session) | ok | none | none. `list-stacks` `[]`; `list-exports` `Exports` `[]`. |
| 10 | ~15:00 | operator (reported in session) | ok | none | none. FREE / ACTIVE, credits 199.99 USD (unchanged from step 01). |

## Notes

- 2026-10-22 ~14:56 UTC (agent): after steps 05 and 06, wrote `AvailabilityZone` = `eu-north-1a` and `S3PrefixListId` = `pl-c3aa4faa` into `deploy/aws/parameters/network.json`, taken from `R3_05_endpoint-services.json` (first zone by name of the six-service intersection) and `R3_06_s3-prefix-list.json`.

- 2026-10-22, before the run (agent): the templates, parameter files, contract, guards and tests
  were written after the operator's answers in session ("1a, 2 ok, 3 igen, 4 ok, A igen/igen, B igen,
  C venv"; decision record `aws-redeployment-od6-stack-layout-r3_2026-10-22`). The agent pre-ran
  `cfn-lint` 1.57.2 (exit 0), both guards (CLEAN) and the three R3 test files (105 passed) under
  Python 3.10.12 in the device's Linux shell. That run is not evidence; steps 03 and 11 on the
  workstation are.
