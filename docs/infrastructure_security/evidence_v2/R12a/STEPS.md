# R12a — Parameterised evidence collector: step sheet

| Field | Value |
|---|---|
| Ticket | `R12a` in `plans/aws_redeployment_tickets.md` |
| Handoff | `plans/aws_redeployment_r12a_handoff_2026-10-28.md` §1, §3, §4 |
| Decisions applied | OD1-r1, OD6-r3 (stack layout and `outputs_contract.json`), OD7, OD12; R8-D7 (key names and SHA-256 only), F-R8-8; R9-D23 (comparison by id), F-R9-1, F-R9-5; R9e-D18, F-R9e-1; R10-D13, F-R10-1. The operator's answers of 2026-10-28 to points 1–21 (below); they go into `aws-redeployment-r12a-collector_2026-10-28` after round 1 |
| Written by / on | agent (Claude) / 2026-10-28 |
| Account / region | none: **workstation only**. No AWS command, no `--profile`, no sign-in |
| Controls touched | none (no register row changes) |
| Cost created | **None.** R12a is code only; it collects nothing |

## Settled with the operator (2026-10-28, "1–21 a")

1. **Language and shape (a):** a Python module `tools/collect_evidence_v2.py` with a CLI
   (`py -3.10 -m tools.collect_evidence_v2 …`). It runs the AWS CLI through one injected runner, always
   with `--profile`, `--region` and `--output json`; the tests replace the runner with a fake.
2. **Inputs (a):** ids only from the `<ticket>_outputs.json` files located through
   `deploy/aws/outputs_contract.json` (stack → ticket → path; the outputs root is a parameter so that the
   tests point it at fixtures); account and Region from the parameter files' `ExpectedAccountId` /
   `ExpectedRegion`, refused when the files disagree, and cross-checked at run time against
   `sts get-caller-identity`; model ids and routed Regions from `iam.json` / `host.json`. No id or Region
   literal in the module, not even for global services (the CLI routes IAM and Organizations itself;
   to be confirmed in R12b).
3. **Per-session host stack (a):** host checks need `--host-outputs <path>` (default: the contract's
   `R11_outputs.json`). Without it they are recorded "not collected: host stack outputs absent"; with it,
   every host id is first confirmed live, or the run refuses as stale.
4. **Host checks (a):** from the workstation through SSM Run Command (`send-command` with a fixed script
   per check, then `get-command-invocation`), scripts kept in the repository and asserted by tests. The
   evidence is the `get-command-invocation` output with `Status` and `StandardOutputContent` (§7a), see 16.
5. **F7 and DC-15 (a):** written in R12a as host checks with offline tests; first run in R12b. F7's input
   per point 17.
6. **Output location and the v1 refusal (a):** the output path must resolve (symlinks resolved) inside
   `docs/infrastructure_security/evidence_v2/`; anything inside the v1 tree (`evidence/`, `audit_package/`,
   register and worklog v1) or outside `evidence_v2/` is refused before any AWS call; an existing folder is
   refused (no overwrite). Folder shape per point 20; a SHA-256 manifest written last. A test per refusal.
7. **Coverage map (a):** one declarative table, control id → checks (contract outputs and parameters used,
   command, evidence file, scope account / Region / global / host). All 41 register v2 rows appear;
   non-command rows marked (DC-22 N/A per R8, DC-38 R16 / OD12, DC-39 document review, DC-40 per point 18,
   DC-36 R2 plus the host). A test ties the table to register v2's row set.
8. **Read-only by construction (a):** read verbs only, plus `ssm send-command` / `get-command-invocation`;
   on the host read-only scripts, the one exception the F7 PUT attempt that must fail; never
   `get-secret-value` from the workstation; the secret on the host by key names and SHA-256 only; the
   Converse check records only whether the reply equals the fixed test string. A test asserts the verb
   allowlist over the table.
9. **Criterion 1's test (a):** synthetic fixture outputs and parameters of the real shapes; the fake runner
   records every command; every AWS-id-shaped token in every recorded command and host script must be in
   the fixtures; a second test swaps the fixture ids and the commands follow; a third asserts that no
   fixture id equals a real value of the R4–R8 outputs or the parameter files.
10. **After a run (a):** the collector runs the secret scan over its output folder and exits non-zero on a
    finding, never editing a file; non-zero on any AWS error not declared as expected for that check in the
    table (no global regex); a per-control summary: collected, not collected (reason), error.
11. **Criterion 3 and the guard (a):** step evidence of `py -3.10 -m tools.old_id_guard` over the collector,
    its host scripts and its tests and fixtures; the guard's default scope gains
    `tools/collect_evidence_v2.py`, `tools/collector_host_checks/` and `tests/tools/fixtures/collector/`
    (`tools/old_id_guard.py` and `tests/test_old_id_guard.py` change).
12. **Evidence (a):** this folder (`STEPS.md`, `RUNLOG.md`, `R12a_<NN>_*`, `VERIFICATION.md`); comparison by
    id (R9-D23); no register row change; decision record `aws-redeployment-r12a-collector_2026-10-28`.
13. **Scope (a):** no AWS call (not even read-only against the base stacks), the old collector and the v1
    tree untouched, no register row change, no F-R10-1 or F-R9-1 fix.
14. **R16 (a):** asked after R12a; not part of it.
15. **Inputs outside outputs and parameters (a):** a checked-in `deploy/aws/collector_inputs.json` holding the
    DC-17 unapproved Region, the DC-32 public egress probe hosts, the fixed Converse test string, the DC-15
    host paths and the F7 input slot, each with its source or reason; tied to the module by a test. The
    unapproved Region is the operator's choice (outside `RoutedRegions`), recorded in the decision record.
16. **Scan patterns in host scripts (a):** the scripts assemble the access-key variable names and the key-id
    prefix at run time and print counts or yes/no only; the evidence keeps `get-command-invocation` and each
    script's SHA-256, not the `send-command` response; a test runs the secret scan and the old-ID guard over
    the scripts folder.
17. **F7 outside bucket (a):** R12a writes the interface for a short-lived presigned PUT URL from an
    account the operator controls, given as an input file at run time; the URL never reaches the evidence
    (HTTP status and error code only). Who provides the bucket is decided in R12b.
18. **DC-40 (a):** the account is a member of an Organization (`evidence_v2/R1/R1_00_organization.json`), so
    `AWSOrganizationsNotInUseException` is not expected; the collector runs `describe-organization` with a
    `--query` that leaves out the management account's e-mail, and records the expected `AccessDenied` on
    SCP listing from a member account. Re-assessment is R12b.
19. **DC-33–35 through the R9 launcher (a):** the host check runs `python -m runner.host_env …` from a bundle
    path given as input, printing key names and SHA-256 only; without a bundle "not collected". How the
    bundle reaches the host is R12b's question.
20. **Folder shape (a):** each run creates a new folder `evidence_v2/<ticket>/<ticket>_<NN>_collector/`
    (it must not exist; `--ticket` and `--step` name it) holding `<control>_<check>.json|txt`,
    `summary.json` and, last, `MANIFEST.sha256`.
21. **Register v2 summary table (a):** stale (40 NOT_STARTED, 1 IN_PROGRESS while 19 rows are PASS or N/A);
    not touched in R12a; finding F-R12a-1 for R12b.

Deviation recorded before round 1 (R12a-D22): there is no `close R10` commit. The R10 change, its evidence,
its decision record, register and worklog v2, the R10 tick and this ticket's handoff are all in
`215727b starting R12a` (21 files). The tree is clean; the baseline runs on `215727b`. No rerun.

## Before you start

- **Where commands run.** PowerShell in the VS Code terminal, repository root
  (`C:\Code\proposal_demo\proposal_orchestrator`). No AWS command and no sign-in in this ticket.
- **`$E` must be set in every new PowerShell window.** Every block below starts with it.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command; if you forget, say so and it
  is recorded as a deviation.
- Close any file or folder view open under `docs\tier4_orchestration_state\dev_graph` in VS Code before
  the full suite (F-R9e-1).
- Run only the block asked for, in order. If a step fails, stop and report; do not improvise a fix.
- **Rounds.**
  - **Round 1 (this sheet now): step 01**, the baseline. Hand back. The agent then writes the collector,
    its host scripts, fixtures, tests and the decision record, runs its subset and the chunked suite
    comparison on the device VM, and adds steps 03–05 to this sheet. (Step 02 is the agent's.)
  - **Round 2: steps 03–05** — diff stat, the R12a tests and touched modules, the old-ID guard over the
    collector (criterion 3), the full suite after, the old-ID guard over the default scope and the secret
    scan last. Then commit and confirm.

---

## Steps

### Step 01 — Baseline: the full suite before any R12a change

What it does: records the commit, what changed since `265f88d tick R9e` (R12a-D22), the interpreter and
libraries, and the full suite's result, so that "no new failures" has a reference. The full suite takes
12–18 minutes.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12a"
& { git log -2 --format="%H %s"; git diff --stat 265f88d HEAD; "--- status ---"; git status --short } 2>&1 | Out-File -Encoding utf8 "$E\R12a_01_commit.txt"
& { py -3.10 --version; py -3.10 -c "import boto3, botocore, dotenv, pytest; from importlib.metadata import version as v; print('boto3', v('boto3')); print('botocore', v('botocore')); print('python-dotenv', v('python-dotenv')); print('pytest', v('pytest'))" } 2>&1 | Out-File -Encoding utf8 "$E\R12a_01_versions.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12a_01_baseline-pytest.txt"
Get-Content "$E\R12a_01_commit.txt", "$E\R12a_01_versions.txt"; Get-Content "$E\R12a_01_baseline-pytest.txt" -Tail 30
```

| Evidence file | PASS criterion |
|---|---|
| `R12a_01_commit.txt` | First line starts `215727b` and ends `starting R12a`; second line starts `265f88d` and ends `tick R9e`; the diff stat names exactly the 21 files of R12a-D22 (register and worklog v2; 14 files under `evidence_v2/R10/`; the R10 decision record; `plans/aws_redeployment_r12a_handoff_2026-10-28.md`; `plans/aws_redeployment_tickets.md`; `runner/claude_transport.py`; `runner/decomposed_drafting.py`; `tests/runner/test_decomposed_drafting_transport.py`; `tests/runner/test_excellence_decomposed_drafting.py`), i.e. 21 files changed; under `--- status ---` only `??` lines for this folder's files (or the folder). Any other line under status is a deviation the agent records |
| `R12a_01_versions.txt` | First line `Python 3.10.…`; four lines naming boto3, botocore, python-dotenv and pytest with their versions; no `ModuleNotFoundError` |
| `R12a_01_baseline-pytest.txt` | First line `Python 3.10.…`; a pytest summary line and `exit=`. **The result is recorded whatever it is.** Every `FAILED` / `ERROR` line of the short summary is the baseline set, listed by id in `VERIFICATION.md`; the agent compares it with the R10 after-run set (`R10_04`, 200). A collection error that stops the run is a deviation to report in session |

Hand back: say "01 kész" (and any deviation). Do not commit anything.

## After the baseline (2026-10-28)

The step 01 result was checked (RUNLOG): 200 failed, 9016 passed, 86 skipped; the 200 failing ids equal
the R10 after-run set (`R10_04`) exactly; `.venv-lint` was deactivated first. Step 02 (agent, device VM)
showed the R12a tests failing on `215727b`: `R12a_02_head-criteria.txt` (the new test module cannot
import the collector; the amended guard test fails on the old default scope).

---

## Round 2 — on the R12a change, **before its commit**

The working tree now holds the R12a change (decision record `aws-redeployment-r12a-collector_2026-10-28`):

| Path | Change |
|---|---|
| `tools/collect_evidence_v2.py` | new: the collector (R12a-D1–D20, D24–D27) |
| `tools/collector_host_checks/` | new: `README.md` and nine host scripts (DC-02, DC-14, DC-15, DC-17, DC-31, DC-32, DC-33–35, DC-37, F7) (R12a-D4, D5, D16, D17, D19) |
| `deploy/aws/collector_inputs.json` | new: the inputs no stack holds, each with its source (R12a-D15, D23) |
| `deploy/aws/README.md` | a section on `collector_inputs.json` |
| `tools/old_id_guard.py` | `DEFAULT_SCOPE` gains the collector, its scripts and its fixtures; docstring (R12a-D11) |
| `tests/test_old_id_guard.py` | `test_default_scope_is_the_v2_side_only` amended to the new tuple (R12a-D11) |
| `tests/tools/test_collect_evidence_v2.py` | new, 65 tests (criteria 1–3 and points 3–20) |
| `tests/tools/fixtures/collector/` | new: synthetic outputs (R4–R8, R11), parameter files, inputs, `README.md` |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r12a-collector_2026-10-28.json` | new |

Line endings: every new and edited file is LF, like its neighbours (`tools/old_id_guard.py`,
`tests/test_old_id_guard.py` and `deploy/aws/README.md` are LF in the working copy). git may print
`LF will be replaced by CRLF` (PowerShell shows it as `NativeCommandError`); that is not an error.

The agent's device runs (Python 3.10.12 venv, boto3 1.42.68, python-dotenv 1.2.2, PyMuPDF 1.28.2): the R12a
tests and the touched modules `193 passed`; the whole suite in 16 chunks on a `git archive HEAD` copy
against the same copy with the change: identical failure sets in every chunk, the 65 new tests passing;
the 44 test modules that read the decision log, with the new record: identical. Old-ID guard (new
default scope) CLEAN; secret scan over the host scripts and the fixtures CLEAN.

Run `deactivate` first if `.venv-lint` is active. No AWS command and no sign-in: `--plan` calls nothing.

### Step 03 — The diff, the R12a tests, the guard over the collector, and a plan over the real files

What it does: records which files the change touches (scope, R12a-D13), runs the R12a tests and the test
modules of the touched code in one process, runs the old-ID guard over the collector (criterion 3), and
prints every command the collector would run against the repository's real outputs and parameter files
(R12a-D27). `--plan` calls nothing and writes no run folder.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12a"
& { git log -1 --format="%H %s"; git diff --stat HEAD; "--- status ---"; git status --short -uall } 2>&1 | Out-File -Encoding utf8 "$E\R12a_03_diff-stat.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=short -rfE tests/tools/test_collect_evidence_v2.py tests/test_old_id_guard.py tests/test_aws_iac_contract.py tests/test_evidence_protocol_scaffold.py tests/test_aws_template_guard.py tests/test_host_env_launcher.py; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12a_03_pytest.txt"
& { py -3.10 -m tools.old_id_guard tools/collect_evidence_v2.py tools/collector_host_checks tests/tools/test_collect_evidence_v2.py tests/tools/fixtures/collector deploy/aws/collector_inputs.json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12a_03_old-id-guard-collector.txt"
& { py -3.10 -m tools.collect_evidence_v2 --ticket R12a --step 03 --profile po-r1 --plan; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12a_03_collector-plan.txt"
Get-Content "$E\R12a_03_diff-stat.txt"; Get-Content "$E\R12a_03_pytest.txt" -Tail 5; Get-Content "$E\R12a_03_old-id-guard-collector.txt"; Get-Content "$E\R12a_03_collector-plan.txt" -Tail 6
```

| Evidence file | PASS criterion |
|---|---|
| `R12a_03_diff-stat.txt` | First line starts `215727b` and ends `starting R12a`; the diff stat names exactly `deploy/aws/README.md`, `tests/test_old_id_guard.py` and `tools/old_id_guard.py`; under `--- status ---` those three as ` M` and `??` lines only for the new paths of the table above and this folder's files. No `runner/`, `harness/`, `docs/infrastructure_security/evidence/` or register path (criterion 2's tree untouched, R12a-D13) |
| `R12a_03_pytest.txt` | First line `Python 3.10.…`; `exit=0`; no `FAILED` / `ERROR` line; the count includes the 65 tests of `tests/tools/test_collect_evidence_v2.py` (criteria 1 and 2: `TestCriterion1`, `TestCriterion2`) |
| `R12a_03_old-id-guard-collector.txt` | `CLEAN: no old-account id in tools/collect_evidence_v2.py, …` and `exit=0` (**criterion 3**) |
| `R12a_03_collector-plan.txt` | Last line `exit=0`; every command carries `--profile po-r1` and, but for `iam` and `organizations`, `--region eu-north-1`; the ids are those of `R4_outputs.json`–`R8_outputs.json` and the parameter files; the host checks, `interface-endpoints`, `host-instance`, `instance-profile-association` and `ssm-instance` read `not collected: host stack outputs absent`; no `get-secret-value`; no run folder `R12a_03_collector` is created |

Hand back: say "03 kész" (and any deviation). Do not commit anything.

### Step 04 — The full suite after the change

What it does: the same run as step 01, now with the change, so that "no new failures" is judged by id
(R9-D23). 12–18 minutes. Close any view under `docs\tier4_orchestration_state\dev_graph` first (F-R9e-1).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12a"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12a_04_full-pytest.txt"
Get-Content "$E\R12a_04_full-pytest.txt" -Tail 5
```

| Evidence file | PASS criterion |
|---|---|
| `R12a_04_full-pytest.txt` | First line `Python 3.10.…`; every `FAILED` / `ERROR` id is in the step 01 set (no new failure, by id); the passed count is the step 01 count plus the 65 new tests (a different count is explained by id in `VERIFICATION.md`) |

Hand back: say "04 kész".

### Step 05 — The old-ID guard over the default scope, then the secret scan last

What it does: the guard over its (now wider) default scope, then the secret scan over this folder as the
last evidence step.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R12a"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12a_05_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R12a_05_secret-scan.txt"
Get-Content "$E\R12a_05_old-id-guard.txt", "$E\R12a_05_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R12a_05_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`, `exit=0` |
| `R12a_05_secret-scan.txt` | `CLEAN: docs/infrastructure_security/evidence_v2/R12a` (or with backslashes), `exit=0` |

Hand back: say "05 kész". The agent then writes `VERIFICATION.md`, the worklog v2 entry and the ticket
tick; the operator commits everything together (e.g. `close R12a`) and confirms in session.
