# R16 — verification

| Field | Value |
|---|---|
| Ticket | R16 (orchestrator bundle and DC-38), second criterion only |
| Step sheet | `STEPS.md` |
| Decision record | `docs/tier4_orchestration_state/decision_log/aws-redeployment-r16-dc38-deferred_2026-10-29.json` (R16-D1–D3) |
| Decisions applied | OD12 (`aws-redeployment-operator-decisions_2026-10-21`); the operator's "14 a" of 2026-10-29 (R16-D1) |
| Verified by | agent (Claude), device shell, files read as `utf-8-sig` |
| Account / region | none: workstation only, no AWS call, no cost |
| Status | **Second criterion PASS; R16 open as deferred (OD12).** Not DONE (R16-D3): the first criterion is not attempted and keeps its blockers (R9, R10, R11, and a successor to OD12) |

## Round 1 — step 01 (on `d1e8527f starting R16`)

| Criterion | Evidence | Result | Reason |
|---|---|---|---|
| Commit and tree | `R16_01_diff-stat.txt` | PASS (deviation recorded) | HEAD `d1e8527fb6a415ac6775ce089ae36ed5db991b86 starting R16`, then `e0d9da68f56496d21ead6d3b1413901c3b48c017 close R12a`. `e0d9da6..HEAD` exactly the 5 R16 files: register v2 (`2 +-`, the DC-38 row), `RUNLOG.md`, `STEPS.md`, the R16 decision record, the R16 handoff; 199+, 1−. Worktree vs HEAD empty; status only `?? R16_01_diff-stat.txt`. The operator had committed the change before step 01, so the step's first line was adapted in session (`RUNLOG.md`, step 01) |
| Register and guard tests | `R16_01_pytest.txt` | PASS | Python 3.10.6; `tests/test_evidence_protocol_scaffold.py`, `tests/test_old_id_guard.py`, `tests/tools/test_collect_evidence_v2.py`: `118 passed, 1 skipped`; `exit=0`; no `FAILED` / `ERROR`. The skip is in `test_collect_evidence_v2.py`, the R12a Windows symlink case. The scaffold tests accept DC-38 as DEFERRED with its note and evidence path |
| Old-ID guard (default scope) | `R16_01_old-id-guard.txt` | PASS | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| Secret scan (last) | `R16_01_secret-scan.txt` | PASS | `CLEAN: docs/infrastructure_security/evidence_v2/R16`; `exit=0`. Re-run by the agent on the device VM after this report and the run-log row were written: CLEAN |

Before step 01 (agent, device VM, Python 3.10.12): the 41 test modules that read the decision log or
register v2 and the four `msca_dn` decision-log readers gave identical failure sets on `git archive e0d9da6`
with and without the change (19 and 1, the baseline ids) (`STEPS.md`, "What changed"). No full-suite run:
the change holds no code (handoff §1, §4).

## Ticket criteria (`plans/aws_redeployment_tickets.md`, R16)

| # | Criterion | Result | Evidence and reason |
|---|---|---|---|
| 1 | DC-38 is marked VERIFIED_PASS or VERIFIED_FAIL, with the run summary as evidence | N/A: deferred per OD12, not attempted | OD12: "No. DC-38 stays deferred, but F5 is fixed anyway (R10)." No orchestrator bundle on the host and no full DAG run under production configuration exist. Keeps every blocker (R9, R10, R11) and is reopened only by a successor to OD12 (R16-D1, R16-D3; record `known_gaps`) |
| 2 | Or: DC-38 is DEFERRED in register v2, with OD12 cited | PASS | `docs/infrastructure_security/aws_hardening_control_register_v2.md`, DC-38 row: status `DEFERRED`, evidence `` `evidence_v2/R16/` (`VERIFICATION.md`) ``, notes citing OD12 verbatim and `aws-redeployment-r16-dc38-deferred_2026-10-29`, R10's scope note kept (R16-D2). Met before R11 by the operator's recorded override of R16's R11 dependency for this criterion only (R16-D1) |

Not evidence of: that a full DAG run succeeds under production configuration (DC-38 is deferred, not
verified). The register v2 Summary table is not touched (F-R12a-1, R12b).

Register v2: DC-38 NOT_STARTED → DEFERRED (in `d1e8527f`). Worklog: entry of 2026-10-29, R16.
