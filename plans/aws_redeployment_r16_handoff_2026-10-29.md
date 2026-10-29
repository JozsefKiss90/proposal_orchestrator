# AWS redeployment: handoff for R16 (DC-38 deferred per OD12)

| Field | Value |
|---|---|
| Date | 2026-10-29 |
| Branch at writing | `msca-dn-pre-eval`; HEAD `e0d9da6 close R12a`. R12a is **done and committed** (tick, `VERIFICATION.md` DONE, worklog). The R16 work below is in the working tree, **not committed**; this file is uncommitted too and goes into the R16 commit. |
| For | The agent that finishes R16 with the operator in a new session |
| Read first | `CLAUDE.md` (§9.4, §12, §13); `plans/aws_redeployment_tickets.md` (inherited constraints; R16; R11, R12b for what stays blocked); §2 of this file and of `plans/aws_redeployment_r12a_handoff_2026-10-28.md`; decision records `aws-redeployment-operator-decisions_2026-10-21` (OD12), `aws-redeployment-r10-drafter-transport_2026-10-28`, `aws-redeployment-r12a-collector_2026-10-28` (R12a-D14, F-R12a-1–3), `aws-redeployment-r16-dc38-deferred_2026-10-29` (new, R16-D1–D3); `docs/infrastructure_security/aws_hardening_control_register_v2.md` (DC-38 row); `docs/infrastructure_security/evidence_v2/R16/STEPS.md`, `RUNLOG.md`; for formats: `evidence_v2/R12a/VERIFICATION.md` and the last two R12a entries of `aws_hardening_worklog_v2.md` |
| Status | E0, R0–R10, R9e, R12a done. R16: settled ("14 a"), changed in the tree, **operator's step 01 pending**. R11 held by the operator (hourly cost); R12b, R13, R14, R15 wait on R11. |

## 1. Facts that govern the rest of R16

| Fact | Record / evidence |
|---|---|
| **The operator chose "14 a" (2026-10-29 ~11:00 UTC):** mark DC-38 DEFERRED now, overriding R16's "Blocked by: R9, R10, R11" for the **second criterion only**. The first criterion (a full DAG run under production configuration on the host, run summary as evidence) keeps every blocker. | `aws-redeployment-r16-dc38-deferred_2026-10-29` R16-D1; `evidence_v2/R16/RUNLOG.md` |
| **R16 is not DONE.** OD12's consequence: "R16 stays open as deferred with OD12 cited, and register v2 marks DC-38 DEFERRED when R16 is closed that way." The ticket's own text: "the ticket stays open as deferred with that reason." So: tick the second criterion, mark R16 "open as deferred (OD12)", do **not** mark it done. Reopened only by a successor to OD12. | OD12; R16-D3 |
| **What is already in the working tree (uncommitted):** (1) register v2, DC-38 row: `DEFERRED`, evidence `` `evidence_v2/R16/` (`VERIFICATION.md`) ``, notes citing OD12 verbatim and the new record, R10's scope note kept, the old "Still deferred (OD12, R16);" fragment dropped (diff: 1 line); (2) the new record `docs/tier4_orchestration_state/decision_log/aws-redeployment-r16-dc38-deferred_2026-10-29.json` (LF); (3) `evidence_v2/R16/STEPS.md` (one operator step, 01) and `RUNLOG.md` (settling rows; step 01 row empty); (4) this handoff. `git status`: ` M` register v2, `??` the record, `evidence_v2/R16/`, this file. | agent, 2026-10-29 ~16:05 UTC |
| **Agent check already done:** on the device VM (Python 3.10.12), the 41 test modules that read the decision log or register v2 (`msca_dn` and `test_docx_exporter.py` aside) and the 4 `msca_dn` decision-log readers, `git archive e0d9da6` vs the same copy with the change: identical failure sets (19 and 1, baseline ids). Secret scan of `evidence_v2/R16/` and old-ID guard (default scope) CLEAN. | `STEPS.md` "What changed" |
| **No full-suite baseline for R16:** the change is one register row and one decision record (no code); the step sheet runs the register and guard tests instead. If the operator wants a full-suite comparison, it is a new step (02) with `R12a_04` as the reference set (200 ids). | R16 `STEPS.md` |
| **The register Summary table is stale** (F-R12a-1). Not touched in R16; R12b updates it. | R12a record |
| **Line endings:** register v2, worklog v2 and the ticket list are LF in the working copy; decision records LF. | agent check |

## 2. How the operator works

Everything in the R4–R12a handoffs' §2 holds:

- The operator answers "1–N a"; new points get new numbers.
- The operator may skip a commit or run a step out of order: check `git log` and `git status` at every hand-back and record a deviation rather than asking for a rerun.
- `.venv-lint` may be active; `py -3.10` names the version, so a run stands; record it.
- The operator may paste the console instead of attaching a file; read the saved evidence files on the device, not only the console tail.
- **Agent-side lessons:**
  - Never run a git command that writes in the connected folder. Compare on `git archive HEAD | tar -x -C $HOME/<dir>` copies with `git init -q`; the device VM's git has no `core.autocrlf`: read diffs with `git -c core.autocrlf=true diff --stat`.
  - Device VM venv: `uv venv $HOME/r9venv --python 3.10`; `uv pip install --python $HOME/r9venv/bin/python python-dotenv==1.2.2 boto3==1.42.68 pytest httpx pyyaml jsonschema pymupdf==1.28.2` (`$HOME` may be new; re-create). No python-docx: leave `tests/runner/test_docx_exporter.py` out. A device call is capped at ~180 s.
  - Edit with exact-match, all-or-nothing read-modify-write that keeps each file's line endings; check the old text occurs exactly as often as expected before writing.
  - Run the secret scan on every evidence draft and the old-ID guard after every edit; no scan pattern and no old id in any record.

## 3. Remaining steps

1. **Operator: step 01** of `evidence_v2/R16/STEPS.md` (diff stat; `tests/test_evidence_protocol_scaffold.py`, `tests/test_old_id_guard.py`, `tests/tools/test_collect_evidence_v2.py`; old-ID guard; secret scan last). Expected: HEAD `e0d9da6 close R12a`; diff only the register (1 line); status `??` only the record, `evidence_v2/R16/` and this handoff (the step sheet lists it; it belongs to the R16 commit); tests `exit=0` with one skip (the R12a Windows symlink case); guard and scan CLEAN.
2. **Agent:** read the four `R16_01_*` files on the device; add the step 01 row to `RUNLOG.md`; write `evidence_v2/R16/VERIFICATION.md` (as R12a's: round table, ticket criteria table — criterion 1 "N/A: deferred per OD12, not attempted", criterion 2 PASS citing the register row and OD12; status "second criterion PASS; R16 open as deferred (OD12)"); add a worklog v2 entry "R16: DC-38 deferred per OD12" (Control ID DC-38; action; evidence; result; next action: frontier R11 held, R12b after R11); re-run the secret scan and the guard.
3. **Operator confirms in session.** Agent then edits `plans/aws_redeployment_tickets.md` R16: tick only "Or: DC-38 is DEFERRED in register v2, with OD12 cited." with its evidence path, and add one line under the ticket's text: "Open as deferred (OD12), 2026-10-29: second criterion met before R11 by the operator's override (`aws-redeployment-r16-dc38-deferred_2026-10-29`); the first criterion keeps its blockers." Do **not** tick the first criterion or call R16 done.
4. **Operator commits** everything together (e.g. `R16 DC-38 deferred`): register v2, the record, `evidence_v2/R16/`, worklog v2, the ticket list, this handoff.

## 4. Open questions to raise only if they come up

- Whether the operator wants a full-suite run for R16 (see §1); default: no, the change holds no code.
- Nothing else is open in R16. The next frontier is R11 (the operator's explicit go, hourly cost); R12b then needs F-R12a-1–3 settled (stale summary table, DC-26 timing, owner of the host bundle and of the F7 outside bucket).
