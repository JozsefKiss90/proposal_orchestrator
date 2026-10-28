# R9e — EU region support: step sheet

| Field | Value |
|---|---|
| Ticket | `R9e` in `plans/aws_redeployment_tickets.md` |
| Handoff | `plans/aws_redeployment_r9e_handoff_2026-10-27.md` §1, §3, §4 |
| Decisions applied | OD1-r1 (eu-north-1); OD7-orchestrator, OD7-an12, OD7-assessor, OD7-global; R8-D2, R8-D3; R9-D3, R9-D6, R9-D7, R9-D15, R9-D17, R9-D21–D23 and the record's `for_r9e` list; F-R9-1, F-R9-2, F-R9-5, F-R9-7. The operator's answers of 2026-10-27 to points 1–18 (below); they go into `aws-redeployment-r9e-eu-region_2026-10-27` after round 1 |
| Written by / on | agent (Claude) / 2026-10-27 |
| Account / region | none: **workstation only**. No AWS command, no `--profile`, no sign-in |
| Controls touched | none (no register row) |
| Cost created | **None.** R9e is code and one runbook only |

## Settled with the operator (2026-10-27, "1–18 a")

1. **Preset model (a):** `BEDROCK_CONVERSE_EU` has no default model; the model comes only from
   `ORCHESTRATOR_TRANSPORT_MODEL` (the secret's, R8-D2). Backend `bedrock_converse`, default Region
   eu-north-1, `production_suitable=True`, capabilities of `bedrock_converse`; notes cite OD1-r1,
   OD7-global (no `global.` profiles) and R8-D3.
2. **Secret-name test (a):** in `tests/test_aws_env_config_template.py` the preset stored by
   `50-secret.yaml` must be in `PRESET_REGISTRY`, production-suitable, with a backend in
   `PRODUCTION_BACKENDS`; a new test passes the template's resolved value through
   `runner.host_env.validate` for eu-north-1 and expects it accepted.
3. **`test_registry_count` (a):** asserts the exact set of preset names, not a count.
4. **Criterion 2 (a):** no test asserts a Converse Region literal; the four mantle endpoint-override lines
   with `us-east-1` (`tests/test_transport_config.py`, `tests/test_transport_presets.py`) take a sentinel
   Region; assertions about the mantle presets' own `eu-west-1` value stay.
5. **`ALLOWED_REGIONS` (a):** `("eu-north-1", "eu-west-1", "us-east-1")`, comment citing OD1-r1 until
   ADR-001 A2 (R13) decides whether to narrow.
6. **Runbook and launcher (a):** every host `python -m` line (steps 7, 8, 10, 11, 12, 13) runs through
   `python -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config --`;
   no `export` lines.
7. **Region and id rule (a):** `--region eu-north-1`; only the two OD7 `eu.` system-defined profiles;
   no bare ids, no `global.`; OD7-an12 and the assessor model named in the text, placeholders in the
   commands; assessor tag `bedrock-converse-eu-north-1@<YYYY-MM-DD>`.
8. **AN1c guard (a):** `harness.judge.drafter_models()` adds `ORCHESTRATOR_TRANSPORT_MODEL` only under
   `ORCHESTRATOR_PRODUCTION_MODE=true`; tested in both modes.
9. **`converse_smoke` Region (a):** `AWS_REGION` only; example tags name eu-north-1.
10. **Evidence (a):** this folder; `VERIFICATION.md` is replaced, the 2026-10-21 N/A text kept as a
    history section; pytest runs `-q --tb=line -rfE`; comparison by id (as R9-D23); no register row.
11. **Scope (a):** no other document (R13), no collector Region (R12a), no test isolation (F-R9-1),
    no drafter path (R10).
12. **Baseline commit (a):** the operator commits the handoff file as `starting R9e`; the baseline runs
    on that commit.
13. **Outbound HTTP (a):** the full suite runs as in R9, `.env.harness` in place (the operator's answer
    "a": the key is no longer valid).
14. **Runbook guard test (a):** learns the launcher prefix (parsed by `runner.host_env`'s own parser);
    Part 2–4 lines must carry it, Part 1 lines must not; the Regions in a line agree; no export of the
    five keys, no `us-east-1`, `us.` or `global.` id left.
15. **`TestTheRealSecretsPreset` (a):** becomes unconditional acceptance.
16. **Error message (a):** the production-preset refusal suggests `BEDROCK_CONVERSE_EU`;
    `BEDROCK_CONVERSE_US` unchanged.
17. **Runbook steps 12–13 (a):** the lost line continuation is restored.
18. **Line endings (a):** the agent keeps each edited file's line endings (the runbook is CRLF).

## Before you start

- **Where commands run.** PowerShell in the VS Code terminal, repository root
  (`C:\Code\proposal_demo\proposal_orchestrator`). No AWS command and no sign-in in this ticket.
- **`$E` must be set in every new PowerShell window.** Every block below starts with it.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command; if you forget, say so and it
  is recorded as a deviation.
- Run only the block asked for, in order. If a step fails, stop and report; do not improvise a fix.
- **Rounds.**
  - **Round 1 (this sheet now): step 01**, the commit of the handoff and the baseline. Hand back. The
    agent then writes the code, the tests, the runbook change and the decision record, runs its own
    subset on the device VM, and adds steps 03–05 to this sheet. (Step 02 is the agent's.)
  - **Round 2: steps 03–05** — the R9e tests, the full suite after, the old-ID guard and the secret scan
    last. Then commit and confirm.

---

## Steps

### Step 01 — Commit the handoff, then the baseline: the full suite before any R9e change

What it does: first commits the staged handoff file (point 12), then records the commit, that the code
tree is unchanged since `d1e767b`, the interpreter and libraries, and the full suite's result, so that
"no new failures" has a reference. The full suite takes 12–18 minutes.

PowerShell, first the commit (only the staged handoff file goes in; this folder stays untracked):

```powershell
git status --short
git commit -m "starting R9e"
```

`git status --short` should show `A  plans/aws_redeployment_r9e_handoff_2026-10-27.md` and the two
untracked files of this folder (`STEPS.md`, `RUNLOG.md`). If it shows anything else staged, stop and
report before committing.

Then the evidence block:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R9e"
& { git log -1 --format="%H %s"; git log -1 --format="%H %s" d1e767b; git diff --stat d1e767b HEAD; "--- status ---"; git status --short } 2>&1 | Out-File -Encoding utf8 "$E\R9e_01_commit.txt"
& { py -3.10 --version; py -3.10 -c "import boto3, botocore, dotenv, pytest; from importlib.metadata import version as v; print('boto3', v('boto3')); print('botocore', v('botocore')); print('python-dotenv', v('python-dotenv')); print('pytest', v('pytest'))" } 2>&1 | Out-File -Encoding utf8 "$E\R9e_01_versions.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9e_01_baseline-pytest.txt"
Get-Content "$E\R9e_01_commit.txt", "$E\R9e_01_versions.txt"; Get-Content "$E\R9e_01_baseline-pytest.txt" -Tail 30
```

| Evidence file | PASS criterion |
|---|---|
| `R9e_01_commit.txt` | First line ends `starting R9e`; second line starts `d1e767b` and ends `close R9`; the diff stat names only `plans/aws_redeployment_r9e_handoff_2026-10-27.md`; under `--- status ---` only `??` lines for this folder's `STEPS.md` and `RUNLOG.md` (or the folder). Any other line under status is a deviation the agent records |
| `R9e_01_versions.txt` | First line `Python 3.10.…`; four lines naming boto3, botocore, python-dotenv and pytest with their versions; no `ModuleNotFoundError` |
| `R9e_01_baseline-pytest.txt` | First line `Python 3.10.…`; a pytest summary line and `exit=`. **The result is recorded whatever it is.** Every `FAILED` / `ERROR` line of the short summary is the baseline set, listed by id in `VERIFICATION.md`; `tests/test_transport_presets.py::TestPresetRegistry::test_registry_count` is expected among them (F-R9-2). A collection error that stops the run is a deviation to report in session |

Hand back: say "01 kész" (and any deviation). Do not commit anything else.

## Settled with the operator (2026-10-27, "19–20 a", after the baseline)

19. **The baseline ran before the `starting R9e` commit (a):** recorded as a deviation; the baseline
    stands (it ran on `d1e767b` with the handoff staged; the code tree equals `d1e767b`). The operator
    makes the commit at the start of round 2.
20. **Transient file lock (a):** `tests/test_demo_change_scenarios.py::…[n08a_excellence_drafting]`
    failed with WinError 32 on a file the test writes under `docs\tier4_orchestration_state\dev_graph`.
    It stays in the baseline set (F-R9e-1); before step 04 close any file or folder view open under
    that directory in VS Code.

---

## Round 2 — on the R9e change, **before its commit**

The working tree now holds the R9e change (decision record
`aws-redeployment-r9e-eu-region_2026-10-27`):

| Path | Change |
|---|---|
| `runner/transport/config.py` | `BEDROCK_CONVERSE_EU` (R9e-D1); production refusal suggests it (R9e-D16) |
| `runner/anonymisation_rewrite.py` | `ALLOWED_REGIONS` adds eu-north-1 (R9e-D5) |
| `harness/judge.py` | `drafter_models()` counts `ORCHESTRATOR_TRANSPORT_MODEL` under production mode (R9e-D8) |
| `harness/commands/converse_smoke.py`, `harness/commands/_converse_judge.py` | Region from `AWS_REGION` only; example tag (R9e-D9) |
| `plans/msca_dn_an12_host_runbook.md` | launcher on every host line; eu-north-1; id rule; tag; steps 12–13 (R9e-D6, D7, D17) |
| `tests/test_transport_presets.py`, `tests/test_transport_config.py` | new preset tests; exact registry set; sentinel URLs (R9e-D1, D3, D4, D16) |
| `tests/test_aws_env_config_template.py`, `tests/test_host_env_launcher.py` | the stored preset exists; the launcher accepts the template's value (R9e-D2, D15) |
| `tests/test_anonymisation_host_runbook.py` | the launcher prefix, Regions, exports, id rule (R9e-D14) |
| `tests/harness/test_judge.py`, `tests/harness/test_converse_judge.py`, `tests/harness/test_converse_smoke.py` | AN1c on the host; Region source (R9e-D8, D9) |
| `tests/runner/test_anonymisation_rewrite.py`, `tests/runner/test_offline_bundle.py` | eu-north-1 allowed; the launcher's environment passes `verify` |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r9e-eu-region_2026-10-27.json` | new |

Line endings: each edited file kept its working-copy endings (R9e-D18). git may print
`LF will be replaced by CRLF` (PowerShell shows it as `NativeCommandError`) for files that were already
LF in the working copy, as in R9; that is not an error.

The agent's device runs (Python 3.10.12 venv, boto3 1.42.68, python-dotenv 1.2.2, PyMuPDF 1.28.2):
step 03's set `573 passed`; the whole suite in chunks on a `git archive HEAD` copy versus the same copy
with the change: identical failure sets in every chunk (all environment-specific: no `.claude/runs`,
no python-docx), except `test_registry_count`, which no longer exists (R9e-D3). Old-ID guard CLEAN.

Run `deactivate` first if `.venv-lint` is active.

### Step 02b — Commit the handoff (point 19)

```powershell
git status --short
git commit -m "starting R9e"
```

Before committing, `git status --short` must show the handoff as `A ` (staged) and nothing else staged:
the R9e change shows as ` M` (unstaged) and `??` lines. If anything else is staged, stop and report.
Only the handoff file goes into this commit.

### Step 03 — The diff, then the R9e tests and the touched modules

What it does: records the commit and which files the change touches, then runs the R9e tests and every
test module of the touched code in one process.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R9e"
& { git log -2 --format="%H %s"; git diff --stat d1e767b HEAD; "--- working tree ---"; git diff --stat; "--- status ---"; git status --short } 2>&1 | Out-File -Encoding utf8 "$E\R9e_03_diff-stat.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE tests/test_transport_presets.py tests/test_transport_config.py tests/test_bedrock_env_readiness.py tests/test_production_mode.py tests/test_host_env_launcher.py tests/test_aws_env_config_template.py tests/test_anonymisation_host_runbook.py tests/test_anonymisation_host_smoke.py tests/test_persistence_policy.py tests/harness/test_judge.py tests/harness/test_converse_judge.py tests/harness/test_converse_smoke.py tests/runner/test_anonymisation_rewrite.py tests/runner/test_anonymisation_attack.py tests/runner/test_offline_bundle.py; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9e_03_pytest.txt"
Get-Content "$E\R9e_03_diff-stat.txt"; Get-Content "$E\R9e_03_pytest.txt" -Tail 6
```

| Evidence file | PASS criterion |
|---|---|
| `R9e_03_diff-stat.txt` | First line ends `starting R9e`, second line is `d1e767b… close R9`; the first diff stat names only `plans/aws_redeployment_r9e_handoff_2026-10-27.md`; the working-tree diff stat names exactly the 16 files of the table above (6 code/runbook, 10 tests); under status, besides those (` M`), only `??` lines for this folder's files and `docs/tier4_orchestration_state/decision_log/aws-redeployment-r9e-eu-region_2026-10-27.json` |
| `R9e_03_pytest.txt` | First line `Python 3.10.…`; no `FAILED`, no `ERROR`; summary `573 passed` (possibly with warnings); `exit=0` |

### Step 04 — The full suite after

What it does: the same command as step 01, on the R9e change. 12–18 minutes. Close files open under
`docs\tier4_orchestration_state\dev_graph` first (point 20).

```powershell
$E = "docs\infrastructure_security\evidence_v2\R9e"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9e_04_full-pytest.txt"
Get-Content "$E\R9e_04_full-pytest.txt" -Tail 12
```

| Evidence file | PASS criterion |
|---|---|
| `R9e_04_full-pytest.txt` | First line `Python 3.10.…`; summary and `exit=`. The agent compares by id (R9-D23, R9e-D10): PASS when every `FAILED`/`ERROR` id is in the step 01 set, except the amended ids (decision record `amended_test_ids`), which must pass; a baseline failure that passes now is recorded, not counted |

### Step 05 — Old-ID guard, then the secret scan of this folder (last)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R9e"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9e_05_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9e_05_secret-scan.txt"
Get-Content "$E\R9e_05_old-id-guard.txt", "$E\R9e_05_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R9e_05_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R9e_05_secret-scan.txt` | `CLEAN: docs\infrastructure_security\evidence_v2\R9e` (or with `/`); `exit=0` |

Hand back after step 05 (or at the first step that fails). The agent then writes `VERIFICATION.md`, the
worklog entry and the ticket tick; it re-runs the scan; the operator commits ("close R9e") and confirms.
