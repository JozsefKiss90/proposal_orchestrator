# E0 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-21 |
| Step sheet | none — E0 is code and templates only; no AWS step, so no `STEPS.md` or `RUNLOG.md` (N/A) |
| Secret scan | `py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2` → `CLEAN` |
| Test run | Agent: `python -m pytest tests/test_evidence_protocol_scaffold.py` → 20 passed (Linux, Python 3.10.12). Operator: `py -3.10 -m pytest tests/test_evidence_protocol_scaffold.py` → 20 passed (win32, Python 3.10.6), 2026-10-21. |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| The new evidence tree exists. No file in the v1 tree changed. | PASS | `evidence_v2/` with `README.md`, `_templates/`, `E0/`; `test_evidence_v2_tree_exists_beside_v1`. `git diff -- docs/infrastructure_security/evidence` is empty, and `git status` lists no change to register v1 or worklog v1. |
| The templates match the §7a fields. | PASS | `_templates/STEPS.md` (numbered steps, PowerShell and CloudShell blocks, console path, evidence file name per step, PASS criterion per file, outputs file), `RUNLOG.md` (UTC time, who ran each step, deviations, errors and action), `VERIFICATION.md` (PASS/FAIL/MISSING/N/A per criterion, scan result, done conditions); `test_*_template_has_section_7a_fields`. |
| A test plants each forbidden pattern; the scan refuses each; a clean folder passes. | PASS | `test_scan_refuses_each_forbidden_pattern` (4 cases), `test_clean_folder_passes`. Also: nested and binary files are scanned, a missing folder is an error, and a refusal never prints the matching text. |
| Register v2 lists all 41 controls, carries no old-account id, and links register v1 as history. | PASS | `aws_hardening_control_register_v2.md`; `test_register_v2_lists_all_41_controls_as_not_started`, `test_register_v2_carries_no_old_id`, `test_register_v2_links_v1_as_history`. |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS.
- [x] Register v2 updated for: none — E0 creates the register; it touches no control.
- [x] Worklog v2 entry: 2026-10-21T08:29:00Z.
- [x] Operator confirmed in session on 2026-10-21, with a Windows re-run: 20 tests passed; a planted probe folder outside the repository was refused (exit 1); `evidence_v2` scanned CLEAN (exit 0).

## Notes

- The scan, run read-only over the v1 tree, reports 6 findings there. Under the v2 rule that old
  evidence would have been refused. It stays unchanged as history.
- Worklog v2 is new. The tickets require a worklog entry per ticket; a v2 file keeps the new account's
  log apart from v1, as the register does.

## Follow-up

none
