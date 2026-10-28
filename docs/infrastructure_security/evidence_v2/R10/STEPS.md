# R10 — Phase 8 drafter through the transport layer (F5): step sheet

| Field | Value |
|---|---|
| Ticket | `R10` in `plans/aws_redeployment_tickets.md` |
| Handoff | `plans/aws_redeployment_r10_handoff_2026-10-28.md` §1, §3, §4 |
| Decisions applied | OD12; OD7-orchestrator, F-R2-2; R9-D6, R9-D7, R9-D12, R9-D15, R9-D21–D23, F-R9-1, F-R9-4, F-R9-5; R9e-D8, R9e-D10, R9e-D18, F-R9e-1. The operator's answers of 2026-10-28 to points 1–21 (below); they go into `aws-redeployment-r10-drafter-transport_2026-10-28` after round 1 |
| Written by / on | agent (Claude) / 2026-10-28 |
| Account / region | none: **workstation only**. No AWS command, no `--profile`, no sign-in |
| Controls touched | none (no register row; notes on DC-35 and DC-38 only) |
| Cost created | **None.** R10 is code only |

## Settled with the operator (2026-10-28, "1–21 a")

1. **Where the routing lives (a):** in `runner/decomposed_drafting.py` only. The production drafter
   resolves `resolve_provider_config()`; `claude_cli` keeps `invoke_claude_text`; `bedrock_converse`
   uses `build_converse_backend` + `run_tool_loop`; other tool-calling backends `build_openai_backend`
   + the same loop. `run_skill` untouched.
2. **Backends (a):** the skill runtime's set; a backend without tool calling is refused (TAPM).
3. **Model, limits, timeout (a):** non-CLI backends use `provider_config.model` (refused when missing);
   the CLI path keeps `_DRAFTER_MODEL`; timeout 1800 s; `max_rounds` the loop default (25);
   `max_tokens` per point 15.
4. **TAPM boundary (a):** `allowed_prefixes = _GROUNDING_INPUTS`; a test shows a read outside them refused.
5. **Resolution caching (a):** once per `_default_claude_drafter(...)` call, no process cache (F-R9-1).
   In `draft_section_decomposed` this runs before stale drafts are removed, so a refusal leaves them intact.
6. **Defence in depth (a):** `runner/claude_transport.invoke_claude_text` refuses under production mode
   before resolving or spawning the CLI (error type per point 21).
7. **DC-35 gap (a):** under `metadata` the drafter writes no response or stdout/stderr content, only a
   `{sub_id}.response_meta.json` (sizes, backend, rounds, files read, exhausted, exception class,
   `sanitize_error_message` text); `full` unchanged; tests for both levels.
8. **Failing test (a):** new `tests/runner/test_decomposed_drafting_transport.py` (production + Converse
   with a fake `boto3` client and a CLI tripwire; production + `claude_cli` refused before any CLI call;
   production + a direct `invoke_claude_text` call refused; one test through `draft_section_decomposed`);
   all with `clear=True`. Shown failing on the start commit in the device copy before the change.
9. **Amended tests (a):** the two `TestProductionDrafterPromptHardening` tests get an explicit
   non-production `claude_cli` environment (`clear=True`); named by id in the decision record.
10. **Criterion 3 (a):** the diff touches `runner/decomposed_drafting.py`, `runner/claude_transport.py`
    and tests only; step 03 records the diff stat.
11. **Evidence (a):** this folder, as R9e; comparison by id (R9-D23); register v2 notes on DC-35 and
    DC-38, statuses unchanged.
12. **Scope (a):** no Phase 8 run on the host (R16), no prompt, quota or retry change, no F-R9-1 fix.
13. **Baseline commit (a):** there is no `starting R10` commit: the handoff went into `265f88d tick R9e`.
    The baseline runs on `265f88d`; recorded as a deviation from handoff §5 step 1. No commit in round 1.
14. **Line endings (a):** `runner/decomposed_drafting.py`, `runner/claude_transport.py` and
    `tests/runner/test_excellence_decomposed_drafting.py` are CRLF in the working copy (`i/lf w/crlf`;
    the handoff said LF); each edited file keeps its working-copy endings.
15. **`max_tokens` (a):** `_DRAFTER_MAX_TOKENS` becomes 32000. The CLI ignores it (its ceiling is
    already 32000 via `CLAUDE_CODE_MAX_OUTPUT_TOKENS`); Converse enforces it, and 8000 would cut a
    sub-section reply (the run 0395b136 class). Converse's 600 s per-request read timeout is recorded
    as a risk, not changed.
16. **Empty or exhausted loop (a):** the drafter raises `DecomposedDraftingError` when the loop text
    is empty or `exhausted_rounds` is true (deadline or round limit).
17. **Excerpt in the error message (a):** under `metadata` the parse-failure message carries no
    response excerpt (length only), since it reaches `run_summary.json`.
18. **Same gap in the skill runtime (a):** `failure_reason` carries `Head: response_text[:300]` at any
    level; not fixed in R10 (`run_skill` untouched); finding F-R10-1 for R12b or a new ticket.
19. **Benchmark instrumentation (a):** the drafter stays uninstrumented, as today.
20. **Throttling (a):** Converse runs with `max_attempts=0` against 5 requests per minute; a fast tool
    loop can fail on `ThrottlingException`. Not R10; finding F-R10-2 for R11/R16.
21. **Error type (a):** new `ClaudeCLIProductionModeError(ClaudeCLIUnavailableError)`, message naming
    `ORCHESTRATOR_PRODUCTION_MODE=true`: the subscription judge does not retry it, the skill runtime
    classifies it `CLI_UNAVAILABLE`.

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
  - **Round 1 (this sheet now): step 01**, the baseline. Hand back. The agent then shows the
    criterion-1 test failing on the start commit (device copy), writes the code, the tests and the
    decision record, runs its own subset on the device VM, and adds steps 03–05 to this sheet.
    (Step 02 is the agent's.)
  - **Round 2: steps 03–05** — the R10 tests and touched modules, the full suite after, the old-ID
    guard and the secret scan last. Then commit and confirm.

---

## Steps

### Step 01 — Baseline: the full suite before any R10 change

What it does: records the commit (no new commit, point 13), that only the R9e tick and the R10 handoff
changed since `47a32d4 close r9e`, the interpreter and libraries, and the full suite's result, so that
"no new failures" has a reference. The full suite takes 12–18 minutes.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R10"
& { git log -2 --format="%H %s"; git diff --stat 47a32d4 HEAD; "--- status ---"; git status --short } 2>&1 | Out-File -Encoding utf8 "$E\R10_01_commit.txt"
& { py -3.10 --version; py -3.10 -c "import boto3, botocore, dotenv, pytest; from importlib.metadata import version as v; print('boto3', v('boto3')); print('botocore', v('botocore')); print('python-dotenv', v('python-dotenv')); print('pytest', v('pytest'))" } 2>&1 | Out-File -Encoding utf8 "$E\R10_01_versions.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R10_01_baseline-pytest.txt"
Get-Content "$E\R10_01_commit.txt", "$E\R10_01_versions.txt"; Get-Content "$E\R10_01_baseline-pytest.txt" -Tail 30
```

| Evidence file | PASS criterion |
|---|---|
| `R10_01_commit.txt` | First line starts `265f88d` and ends `tick R9e`; second line starts `47a32d4` and ends `close r9e`; the diff stat names exactly `aws_hardening_worklog_v2.md`, `evidence_v2/R9e/RUNLOG.md`, `evidence_v2/R9e/VERIFICATION.md`, `plans/aws_redeployment_r10_handoff_2026-10-28.md` and `plans/aws_redeployment_tickets.md` (no `runner/`, `harness/` or `tests/` path); under `--- status ---` only `??` lines for this folder's files (or the folder). Any other line under status is a deviation the agent records |
| `R10_01_versions.txt` | First line `Python 3.10.…`; four lines naming boto3, botocore, python-dotenv and pytest with their versions; no `ModuleNotFoundError` |
| `R10_01_baseline-pytest.txt` | First line `Python 3.10.…`; a pytest summary line and `exit=`. **The result is recorded whatever it is.** Every `FAILED` / `ERROR` line of the short summary is the baseline set, listed by id in `VERIFICATION.md`; the agent compares it with the R9e after-run set (`R9e_04`, 200). A collection error that stops the run is a deviation to report in session |

Hand back: say "01 kész" (and any deviation). Do not commit anything.

## After the baseline (2026-10-28)

The step 01 result was checked (RUNLOG): the 200 failing ids equal the R9e after-run set; `.venv-lint`
was active (recorded, the run stands). Step 02 (agent, device VM) showed the criterion-1 tests failing
on `265f88d`: `R10_02_head-criterion1.txt`. The operator approved the code ("jóváhagyom").

---

## Round 2 — on the R10 change, **before its commit**

The working tree now holds the R10 change (decision record
`aws-redeployment-r10-drafter-transport_2026-10-28`):

| Path | Change |
|---|---|
| `runner/decomposed_drafting.py` | provider resolution in `_default_claude_drafter` (R10-D1–D5); `_DRAFTER_MAX_TOKENS` 32000 (R10-D15); exhausted or empty tool loop fails closed (R10-D16); capture by diagnostic level, no excerpt at `metadata` (R10-D7, D17) |
| `runner/claude_transport.py` | `ClaudeCLIProductionModeError`; `invoke_claude_text` refuses under production mode (R10-D6, D21) |
| `tests/runner/test_decomposed_drafting_transport.py` | new, 19 tests (R10-D8) |
| `tests/runner/test_excellence_decomposed_drafting.py` | `TestProductionDrafterPromptHardening` pins a non-production `claude_cli` environment (R10-D9) |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r10-drafter-transport_2026-10-28.json` | new |

Line endings: the three edited files kept their CRLF working-copy endings; the new test file is CRLF;
the decision record is LF like the other records (R10-D14). git may print `LF will be replaced by CRLF`
(PowerShell shows it as `NativeCommandError`) for the decision record; that is not an error.

The agent's device runs (Python 3.10.12 venv, boto3 1.42.68, python-dotenv 1.2.2, PyMuPDF 1.28.2):
step 03's set `2 failed, 477 passed, 4 skipped` (483; the two failures are environment-specific there:
no python-docx, a Windows-only tree-kill case); the whole suite in 13 chunks on a `git archive HEAD`
copy against the same copy with the change: identical failure sets in every chunk, the 19 new tests
passing; the decision-log readers with the new record: identical. Old-ID guard CLEAN.

Run `deactivate` first if `.venv-lint` is active.

### Step 03 — The diff, then the R10 tests and the touched modules

What it does: records the commit and which files the change touches (criterion 3), then runs the R10
tests and every test module of the touched code in one process.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R10"
& { git log -1 --format="%H %s"; "--- working tree ---"; git diff --stat; "--- status ---"; git status --short } 2>&1 | Out-File -Encoding utf8 "$E\R10_03_diff-stat.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE tests/runner/test_decomposed_drafting_transport.py tests/runner/test_excellence_decomposed_drafting.py tests/runner/test_impact_implementation_decomposed_drafting.py tests/runner/test_agent_runtime.py tests/runner/test_e2e_msca_pf_run.py tests/runner/test_section_extra_fields.py tests/runner/test_preseed_suppression_scheduler.py tests/runner/test_claude_transport.py tests/runner/test_claude_transport_treekill.py tests/test_production_mode.py tests/test_persistence_policy.py tests/harness/test_converse_judge.py; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R10_03_pytest.txt"
Get-Content "$E\R10_03_diff-stat.txt"; Get-Content "$E\R10_03_pytest.txt" -Tail 8
```

| Evidence file | PASS criterion |
|---|---|
| `R10_03_diff-stat.txt` | First line starts `265f88d` and ends `tick R9e`; the working-tree diff stat names exactly `runner/claude_transport.py`, `runner/decomposed_drafting.py` and `tests/runner/test_excellence_decomposed_drafting.py` (no `agent_runtime`, `dag_scheduler`, `gate_evaluator`, `skill_runtime` or manifest path: criterion 3); under status, besides those three (` M`), only `??` lines for this folder's files, `tests/runner/test_decomposed_drafting_transport.py` and `docs/tier4_orchestration_state/decision_log/aws-redeployment-r10-drafter-transport_2026-10-28.json` |
| `R10_03_pytest.txt` | First line `Python 3.10.…`; no `ERROR`; passed + failed + skipped = 483; the only `FAILED` id allowed is the baseline's `tests/runner/test_claude_transport.py::TestCliPathResolution::test_unset_pin_uses_absolute_path_search_result` (F-R10-3); every test of `test_decomposed_drafting_transport.py` and `test_excellence_decomposed_drafting.py` passes |

### Step 04 — The full suite after

What it does: the same command as step 01, on the R10 change. 12–18 minutes. Close files open under
`docs\tier4_orchestration_state\dev_graph` first (F-R9e-1).

```powershell
$E = "docs\infrastructure_security\evidence_v2\R10"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=line -rfE; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R10_04_full-pytest.txt"
Get-Content "$E\R10_04_full-pytest.txt" -Tail 12
```

| Evidence file | PASS criterion |
|---|---|
| `R10_04_full-pytest.txt` | First line `Python 3.10.…`; summary and `exit=`. The agent compares by id (R9-D23): PASS when every `FAILED`/`ERROR` id is in the step 01 set; the amended ids (decision record `amended_test_ids`) and the 19 new tests pass; a baseline failure that passes now is recorded, not counted |

### Step 05 — Old-ID guard, then the secret scan of this folder (last)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R10"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R10_05_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R10_05_secret-scan.txt"
Get-Content "$E\R10_05_old-id-guard.txt", "$E\R10_05_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R10_05_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R10_05_secret-scan.txt` | `CLEAN: docs\infrastructure_security\evidence_v2\R10` (or with `/`); `exit=0` |

Hand back after step 05 (or at the first step that fails). The agent then writes `VERIFICATION.md`, the
register v2 notes (DC-35, DC-38) and the worklog entry; it re-runs the scan; the operator commits
("close R10") and confirms; then the ticket tick.
