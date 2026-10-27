# R9 — Runtime configuration from the secret (F4, F6): step sheet

| Field | Value |
|---|---|
| Ticket | `R9` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R9, as read in `plans/aws_redeployment_r9_handoff_2026-10-27.md` §3 |
| Decisions applied | OD1-r1 eu-north-1; OD7-orchestrator (`eu.anthropic.claude-opus-4-6-v1`); OD8 (a) the launcher reads the secret; OD12 (R10 keeps its own scope); R5 `RuntimeSecretRead` (`GetSecretValue` only); R6-D3; R8-D2, R8-D3, R8-D7, R8-D13, F-R8-8. The operator's answers of 2026-10-27 to the R9 handoff §4 points 1–12 and to points 13–20 added by the agent (below); they go into `aws-redeployment-r9-runtime-config_2026-10-27` after round 1 |
| Written by / on | agent (Claude) / 2026-10-27 |
| Account / region | none: **workstation only**. No AWS command, no `--profile`, no sign-in |
| IDs taken from | `evidence_v2/R8/R8_outputs.json` (secret name and ARN; used by the launcher's documentation and tests only) |
| Controls touched | Notes only on DC-33–DC-35 (launcher in place; evidenced on the host in R12b) |
| Cost created | **None.** R9 is code only |

## Settled with the operator (2026-10-27, "1–20 a")

1. **Launcher form (a):** a Python module, `runner/host_env.py`, run as
   `python -m runner.host_env --region <region> --secret-id <name> -- <command…>`. It calls
   `GetSecretValue` once through boto3, validates the object, sets the variables in a copy of the
   environment and replaces itself with the command (`os.execvpe`). No value passes through a shell,
   a file or stdout. boto3 is imported only at run time; the client is injectable.
2. **Its own Region and secret id (a):** both required arguments, no default. After the read the
   launcher refuses unless the secret's `AWS_REGION` equals `--region`. The secret is named, not
   addressed by ARN: `proposal-orchestrator/env-config` (export `proposal-orchestrator-secret-SecretName`).
3. **What it accepts (a):** a JSON object of exactly the five agreed keys, all strings;
   `ORCHESTRATOR_PRODUCTION_MODE` = `true`, `ORCHESTRATOR_DIAGNOSTIC_LEVEL` = `metadata`. Refused before
   anything is exported: an extra key, a missing key, a non-string value, a credential-shaped key name.
   The preset must resolve (`get_transport_preset`) before exec, so the launcher refuses the real secret
   until R9e adds `BEDROCK_CONVERSE_EU` (R8-D3).
4. **Precedence (b):** the launcher refuses when the caller's environment already sets one of the five
   keys to a different value. `AWS_DEFAULT_REGION` is set to the `AWS_REGION` value, or refused if the
   caller set it to a different one.
5. **"Without logging":** nothing printed on success. On failure only the failure kind, key **names**
   and the boto3 error code; never a value, the response object or raw exception text. No logging
   configuration, no value in `argv`. Exit codes: 2 configuration refused, 3 the AWS read failed.
   Tests use distinctive sentinel values and assert they reach none of stdout, stderr, `logging`
   records or the exec'd command's argv.
6. **Where a missing `AWS_REGION` is refused (a)+(c):** in `resolve_provider_config` (preset and
   explicit paths) for `bedrock_converse` under production mode, in `build_converse_backend`, and in the
   launcher. An empty value counts as missing; `AWS_DEFAULT_REGION` alone does not satisfy production
   mode. Outside production mode the preset's `default_region` applies when `AWS_REGION` is unset (F4(3)).
7. **F6 (a):** `bedrock` leaves `PRODUCTION_BACKENDS`; `BEDROCK_EU_PRODUCTION` keeps its name and
   becomes `production_suitable=False` with a note saying why; the tests that pin today's behaviour
   change in the same commit. The two documents that mention the preset
   (`docs/backend/transport_presets.md`, `plans/reports/security_compliance_brief.md`) go on R13's list.
8. **`offline_bundle verify` (a):** requires `AWS_REGION`; `AWS_DEFAULT_REGION` alone fails the region
   check. `ALLOWED_REGIONS` stays R9e's.
9. **Deployment guide (b):** R9 changes no document; the exact corrections are listed for R13 in the
   decision record.
10. **Tests and names:** `tests/test_host_env_launcher.py`; additions to `tests/test_production_mode.py`,
    `tests/test_transport_presets.py`, `tests/runner/test_offline_bundle.py`. The response's value-field
    name is assembled at run time (F-R8-8). No test fixes eu-north-1 as the only Region.
11. **Evidence (a):** this folder (`STEPS.md`, `RUNLOG.md`, `R9_<NN>_*.txt`, `VERIFICATION.md`);
    register v2 gets notes on DC-33–DC-35 only; a worklog entry.
12. **Order:** R9 lands first and changes only what the ticket needs; R10 and R9e rebase on it. The
    decision record lists for R9e: the `BEDROCK_CONVERSE_EU` preset, `ALLOWED_REGIONS` widened, the
    runbook's step 7 exports replaced by the launcher, the AN1c guard reading the host's drafter model.
13. **Baseline commit (a):** HEAD is `8c20087` ("starting R9"), which differs from `273cb7a`
    ("Close R8") only by the handoff file; the baseline runs on `8c20087` and names both hashes.
14. **F6 on the preset path (a):** `resolve_provider_config_from_preset` checks only
    `production_suitable`; it will also call `_enforce_production_backend` (today never called), so the
    backend rule holds on both paths.
15. **Existing tests amended on purpose:** tests that resolve `bedrock_converse` under production mode
    without `AWS_REGION` get `AWS_REGION`. The decision record names each one; the baseline comparison
    treats them as amended, not as new failures.
16. **`load_dotenv()` at import of `config.py`:** no change. The launcher takes an explicit environment
    mapping and its tests never read `os.environ` (the workstation `.env` sets a preset). On the host no
    `.env` is in the bundle roots, and `override=False` keeps the launcher's five keys.
17. **Scan trap, extended:** the second of the scan's four patterns is case-insensitive and so matches the
    standard AWS access-key environment variable name. R9 tests use other names; evidence runs use
    `-q --tb=line -rfE`, so no source line enters an evidence file.
18. **Windows and exec:** the exec function is injectable; no test performs a real exec. The launcher
    is for the Linux host.
19. **`BedrockConverseBackend(region_name=…)`:** required, no default (all three callers pass it).
20. **`AWS_REGION` differing from the preset's `default_region` in production:** allowed, recorded.
    `eu.` profiles answer from any EU source Region, and the private host has endpoints only in
    eu-north-1, so a wrong Region fails closed there.

## Before you start

- **Where commands run.** PowerShell in the VS Code terminal, repository root
  (`C:\Code\proposal_demo\proposal_orchestrator`). No AWS command and no sign-in in this ticket.
- **`$E` must be set in every new PowerShell window.** Every block below starts with it.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command; if you forget, say so and it
  is recorded as a deviation.
- **Which commit each run is on.** Round 1 runs on `8c20087` with **no change** in `runner/`, `tests/`,
  `harness/`, `tools/` or `deploy/`. Rounds 2 and later run on the R9 change, before its commit. The
  sheet says which in each step's heading.
- Run only the block asked for, in order. If a step fails, stop and report; do not improvise a fix.
- **Rounds.**
  - **Round 1 (this sheet now): step 01**, the baseline. Hand back. The agent then reads the files,
    writes the code, the tests and the decision record `aws-redeployment-r9-runtime-config_2026-10-27`,
    runs its own subset on the device VM, and adds steps 03–05 to this sheet. (Step 02 is the agent's.)
  - **Round 2: steps 03–05** — the R9 tests, the full suite after, the old-ID guard and the secret scan
    last. Then commit and confirm.

## Settled with the operator (2026-10-27, "21–23 a", after the baseline)

21. **Outbound HTTP in the suite (a):** the baseline run reached outside providers (F-R9-1). Recorded in
    the decision record; a follow-up ticket is proposed; not fixed in R9. The operator checks whether the
    `.env.harness` key needs revoking.
22. **`test_registry_count` (a):** untouched; stays in the baseline set; R9e updates it.
23. **Exit condition 4 (a):** PASS when the failing ids after R9 are a subset of the baseline set, except
    the ids amended on purpose (decision record R9-D15), which must pass. A baseline failure that passes
    afterwards is recorded, not counted.

---

## Steps

### Step 01 — Baseline: the full suite on `8c20087`, before any R9 change

What it does: records the commit, that the code tree is unchanged, the interpreter and the libraries the
R9 tests depend on, and the full suite's result, so that "no new failures" (exit condition 4) has a
reference. The full suite may take several minutes.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R9"
& { git log -1 --format="%H %s"; git log -1 --format="%H %s" 273cb7a; git diff --stat 273cb7a HEAD; "--- status ---"; git status --short } 2>&1 | Out-File -Encoding utf8 "$E\R9_01_commit.txt"
& { py -3.10 --version; py -3.10 -c "import boto3, botocore, dotenv, pytest; from importlib.metadata import version as v; print('boto3', v('boto3')); print('botocore', v('botocore')); print('python-dotenv', v('python-dotenv')); print('pytest', v('pytest'))" } 2>&1 | Out-File -Encoding utf8 "$E\R9_01_versions.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9_01_baseline-pytest.txt"
Get-Content "$E\R9_01_commit.txt", "$E\R9_01_versions.txt"; Get-Content "$E\R9_01_baseline-pytest.txt" -Tail 30
```

| Evidence file | PASS criterion |
|---|---|
| `R9_01_commit.txt` | First line starts `8c200878429d8eec918ee3aa1faff4a17e3929eb starting R9`; second line starts `273cb7a` and ends `Close R8`; the diff stat names only `plans/aws_redeployment_r9_handoff_2026-10-27.md`; under `--- status ---` nothing but `?? docs/infrastructure_security/evidence_v2/R9/` (this folder). Any other line under status is a deviation the agent records |
| `R9_01_versions.txt` | First line `Python 3.10.…`; four lines naming boto3, botocore, python-dotenv and pytest with their versions; no `ModuleNotFoundError`. A missing module is recorded, not a FAIL: the agent then plans the tests around it |
| `R9_01_baseline-pytest.txt` | First line `Python 3.10.…`; a pytest summary line (`N passed`, possibly with `failed`, `skipped`, `error`, `xfailed`) and `exit=`. **The result is recorded whatever it is.** Every failure and error is named by the `FAILED` / `ERROR` lines of the short summary; the agent lists them in `VERIFICATION.md` as the baseline set. A collection error that stops the run is a deviation to report in session |

---

## Round 2 — on the R9 change, **before its commit**

The working tree now holds the R9 change (decision record
`aws-redeployment-r9-runtime-config_2026-10-27`):

| Path | Change |
|---|---|
| `runner/host_env.py` | new: the launcher (R9-D1 to R9-D5, R9-D18) |
| `runner/transport/config.py` | Region refusal under production mode on both paths and at build; preset `default_region` outside production; `ProviderConfig.region`; F6 (`PRODUCTION_BACKENDS`, `BEDROCK_EU_PRODUCTION`, preset path) |
| `runner/transport/bedrock_converse.py` | `region_name` required |
| `runner/offline_bundle.py` | `verify` requires `AWS_REGION` |
| `tests/test_host_env_launcher.py` | new |
| `tests/test_production_mode.py`, `tests/test_transport_presets.py`, `tests/runner/test_offline_bundle.py` | additions; the amended ids are listed in R9-D15 |
| `plans/aws_redeployment_tickets.md` | a note under R9 (F-R9-1 follow-up; R9e inherits `for_r9e`); not ticked |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r9-runtime-config_2026-10-27.json` | new |

Do not commit before step 05 and the agent's check. Run `deactivate` first if `.venv-lint` is active.

### Step 03 — The diff, then the R9 tests and the touched transport tests

What it does: records which files the change touches, then runs the launcher tests and every test
module of the transport configuration, the production mode and the bundle check, in one process
(so the order dependence of F-R9-1 does not reach them).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R9"
& { git log -1 --format="%H %s"; git diff --stat; "--- status ---"; git status --short } 2>&1 | Out-File -Encoding utf8 "$E\R9_03_diff-stat.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE tests/test_host_env_launcher.py tests/test_production_mode.py tests/test_transport_presets.py tests/test_transport_config.py tests/test_bedrock_env_readiness.py tests/test_persistence_policy.py tests/runner/test_offline_bundle.py; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9_03_pytest.txt"
Get-Content "$E\R9_03_diff-stat.txt"; Get-Content "$E\R9_03_pytest.txt" -Tail 6
```

| Evidence file | PASS criterion |
|---|---|
| `R9_03_diff-stat.txt` | First line starts `8c200878429d8eec918ee3aa1faff4a17e3929eb`; the diff stat names exactly `plans/aws_redeployment_tickets.md` (the R9 note), `runner/offline_bundle.py`, `runner/transport/bedrock_converse.py`, `runner/transport/config.py`, `tests/runner/test_offline_bundle.py`, `tests/test_production_mode.py`, `tests/test_transport_presets.py`; under status, besides those, only `??` lines for `docs/infrastructure_security/evidence_v2/R9/`, `docs/tier4_orchestration_state/decision_log/aws-redeployment-r9-runtime-config_2026-10-27.json`, `runner/host_env.py`, `tests/test_host_env_launcher.py` |
| `R9_03_pytest.txt` | First line `Python 3.10.…`; the only `FAILED` line is `tests/test_transport_presets.py::TestPresetRegistry::test_registry_count` (baseline, R9-D22); no `ERROR`; summary `1 failed, 302 passed` (the agent's device run, Python 3.10.12: `2 failed, 301 passed`, the second being `tests/runner/test_offline_bundle.py::TestTheBundleIsSelfSufficient::test_both_host_smokes_run_from_the_bundled_roots_alone`, which needs PyMuPDF, absent on the device and passing in the workstation baseline); `exit=1` |

### Step 04 — The full suite after

What it does: the same command as step 01, on the R9 change. About 18 minutes.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R9"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9_04_full-pytest.txt"
Get-Content "$E\R9_04_full-pytest.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R9_04_full-pytest.txt` | First line `Python 3.10.…`; a summary line and `exit=`. The agent compares the `FAILED`/`ERROR` ids with the baseline set in `VERIFICATION.md` (point 23): every failing id is in the baseline set, and none of the R9-D15 ids fails |

### Step 05 — Old-ID guard, then the secret scan of this folder (last)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R9"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9_05_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R9_05_secret-scan.txt"
Get-Content "$E\R9_05_old-id-guard.txt", "$E\R9_05_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R9_05_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R9_05_secret-scan.txt` | `CLEAN: docs\infrastructure_security\evidence_v2\R9` (or with `/`); `exit=0` |

Hand back. The agent then writes `VERIFICATION.md`, the register v2 notes, the worklog entry and the
ticket tick; it re-runs the scan; the operator commits ("Close R9") and confirms in session.
