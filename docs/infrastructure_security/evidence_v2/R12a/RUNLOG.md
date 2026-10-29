# R12a — run log

| Field | Value |
|---|---|
| Ticket | R12a (parameterised evidence collector) |
| Step sheet | `STEPS.md` |
| Kept by | agent (Claude), from the operator's reports in session |

## Settling

| When (UTC, approx.) | Who | What |
|---|---|---|
| 2026-10-28 ~21:17–21:22 | agent | Read the R12a handoff and its sources (ticket R12a, R11, R12b, R16; handoff 2026-10-21 F7, F8, §6, §7a, §10; `deploy/aws/outputs_contract.json`, `README.md`, all six parameter files, `90-host.yaml` header; `tools/old_id_guard.py`, `tools/evidence_secret_scan.py`, `tools/env_config_digest.py`, `runner/host_env.py`; `tests/test_old_id_guard.py`, `tests/test_evidence_protocol_scaffold.py`, `tests/test_aws_iac_contract.py`; register v2; `evidence_v2/README.md`; R1 organization and SCP-probe evidence; R10 step sheet and run log; the old collector, read only). HEAD `215727b starting R12a`, tree clean; no `close R10` commit (R12a-D1). Put handoff §4 as points 1–14 and new points 15–21 to the operator. No write in the connected folder except this folder; git read-only |
| 2026-10-28 ~21:24 | operator | "1–21 a" |
| 2026-10-28 ~21:27 | agent | Wrote `STEPS.md` round 1 (step 01: baseline on `215727b`) and this log |

## Round 1 — step 01 (baseline)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 01 | ~21:31–21:46 | operator | ok | `.venv-lint` was active and was deactivated before the block (not a deviation). `R12a_01_commit.txt`: `215727b starting R12a` over `265f88d tick R9e`, 21 files, status only this folder (R12a-D22: no `close R10` commit). `R12a_01_versions.txt`: Python 3.10.6, boto3 1.42.68, botocore 1.42.68, python-dotenv 1.2.2, pytest 9.0.2. `R12a_01_baseline-pytest.txt`: 200 failed, 9016 passed, 86 skipped in 854.96 s, `exit=1`; the 200 failing ids equal `R10_04` exactly (agent, by id) |
| 02 | ~21:50–22:25 | agent | ok | Device VM (Python 3.10.12): wrote the collector, host scripts, inputs file, fixtures, tests, guard scope and decision record in a copy of `215727b`. `R12a_02_head-criteria.txt`: on the unchanged copy the new test module cannot import the collector (`exit=2`) and the amended guard test fails (`exit=1`). With the change: R12a tests and touched modules 193 passed; 16 chunks (the 190 `tests/test_*.py` and `tests/runner/test_*.py` files, `tests/harness`, `tests/tools`, `tests/runner/benchmark`, `tests/runner/predicates`; `test_docx_exporter.py` left out on both sides, no python-docx) identical failure sets HEAD copy vs change copy; the 44 decision-log readers identical with the new record. Old-ID guard (new default scope) CLEAN. Applied the 31 files to the connected folder by copy (byte-equal with the tested copy; the three edited files were equal to HEAD before, modulo line endings). No git write. The baseline deviation, called R12a-D1 in round 1, is renumbered R12a-D22 in `STEPS.md` so that R12a-D1–D21 match points 1–21 |

## Round 2 — steps 03–05 (on the change, before its commit)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 03 | ~22:27–22:50 | operator | ok | Approval first: 'jóváhagyom, 22–26 a' (~22:51; R12a-D23–D27 Confirmed). `R12a_03_diff-stat.txt`: HEAD `215727b`; diff stat exactly the three edited files; status ` M` for them and `??` only for the new paths and this folder; git's LF→CRLF warnings (`NativeCommandError`) are not errors. `R12a_03_pytest.txt`: Python 3.10.6, 230 passed, 1 skipped, `exit=0`; the skip is `TestCriterion2::test_a_symlink_into_the_v1_tree_is_refused` (Windows, no symlink privilege; passes on the device VM, decision record known gap). `R12a_03_old-id-guard-collector.txt`: CLEAN, `exit=0` (criterion 3). `R12a_03_collector-plan.txt`: `exit=0`, 95 lines, every command `--profile po-r1`, `--region eu-north-1` on all but `iam`/`organizations` (none there), no `get-secret-value`, 13 host-dependent checks `not collected: host stack outputs absent`; every id-shaped token is from the R4–R8 outputs, the parameter files or `collector_inputs.json` (agent check); no `R12a_03_collector` folder |
| 04 | ~22:52–23:28 | operator | ok | `R12a_04_full-pytest.txt`: Python 3.10.6, 200 failed, 9080 passed, 87 skipped in 1065.14 s, `exit=1`. The 200 failing ids equal the step 01 set exactly (agent, by id): no new failure. Passed 9016 + 64 new (65 R12a tests, one skipped on Windows: the symlink case, as in step 03); skipped 86 + 1 |
| 05 | ~23:55 | operator | ok | `R12a_05_old-id-guard.txt`: CLEAN (default scope, 20 ids), `exit=0`. `R12a_05_secret-scan.txt`: CLEAN, `exit=0` (last). Agent wrote `VERIFICATION.md` (all PASS) and the worklog entry; secret scan re-run CLEAN |
| close | ~00:03 (2026-10-29) | operator | ok | "zárd le az R12a-t". Agent ticked R12a, set `VERIFICATION.md` to DONE, added the closing worklog entry. Commit by the operator (`close R12a`) |
