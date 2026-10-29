# R16 — DC-38 deferred per OD12: step sheet

| Field | Value |
|---|---|
| Ticket | `R16` in `plans/aws_redeployment_tickets.md`, second criterion only ("DC-38 is DEFERRED in register v2, with OD12 cited") |
| Decision record | `aws-redeployment-r16-dc38-deferred_2026-10-29` (R16-D1–D3) |
| Decisions applied | OD12; R10 (F5 closed); R12a-D14 (point 14 asked after R12a); the operator's "14 a" of 2026-10-29 |
| Written by / on | agent (Claude) / 2026-10-29 |
| Account / region | none: **workstation only**. No AWS command, no `--profile`, no sign-in |
| Controls touched | DC-38: NOT_STARTED → DEFERRED |
| Cost created | **None** |

## What changed (in the working tree, before its commit)

| Path | Change |
|---|---|
| `docs/infrastructure_security/aws_hardening_control_register_v2.md` | DC-38: status DEFERRED; evidence `evidence_v2/R16/` (`VERIFICATION.md`); notes cite OD12 verbatim and the new record and keep R10's scope note (R16-D2) |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r16-dc38-deferred_2026-10-29.json` | new: the override of R16's R11 dependency for its second criterion (R16-D1); R16 stays open as deferred (R16-D3) |

Agent's device runs (Python 3.10.12): the 41 test modules that read the decision log or register v2
(`tests/test_msca_dn_*` and `test_docx_exporter.py` aside) and the four `msca_dn` decision-log readers,
on a `git archive e0d9da6` copy against the same copy with the change: identical failure sets
(19 and 1, the baseline ids).

## Before you start

- PowerShell in the VS Code terminal, repository root. Run `deactivate` first if `.venv-lint` is active.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.

## Step 01 — The diff, the register and guard tests, the guard, then the secret scan last

What it does: records that only the register row and the new record changed, runs the tests that read
register v2 (the scaffold's status and evidence rules for DEFERRED, the guard, the collector's coverage
map), then the old-ID guard and, last, the secret scan over this folder.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R16"
& { git log -1 --format="%H %s"; git diff --stat HEAD; "--- status ---"; git status --short -uall } 2>&1 | Out-File -Encoding utf8 "$E\R16_01_diff-stat.txt"
& { py -3.10 --version; py -3.10 -m pytest -q --tb=short -rfE tests/test_evidence_protocol_scaffold.py tests/test_old_id_guard.py tests/tools/test_collect_evidence_v2.py; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R16_01_pytest.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R16_01_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R16_01_secret-scan.txt"
Get-Content "$E\R16_01_diff-stat.txt"; Get-Content "$E\R16_01_pytest.txt" -Tail 3; Get-Content "$E\R16_01_old-id-guard.txt", "$E\R16_01_secret-scan.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R16_01_diff-stat.txt` | First line starts `e0d9da6` and ends `close R12a`; the diff stat names exactly `docs/infrastructure_security/aws_hardening_control_register_v2.md` (1 line changed); under `--- status ---` that file as ` M` and `??` only for the new decision record, `plans/aws_redeployment_r16_handoff_2026-10-29.md` and this folder's files |
| `R16_01_pytest.txt` | First line `Python 3.10.…`; `exit=0`; no `FAILED` / `ERROR` (one skip in `test_collect_evidence_v2.py` is the Windows symlink case of R12a) |
| `R16_01_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`, `exit=0` |
| `R16_01_secret-scan.txt` | `CLEAN: docs/infrastructure_security/evidence_v2/R16` (or with backslashes), `exit=0` |

Hand back: say "01 kész". The agent then writes `VERIFICATION.md`, the worklog v2 entry and the ticket
mark (second criterion ticked; R16 open as deferred); the operator commits everything together (e.g.
`R16 DC-38 deferred`) and confirms in session.
