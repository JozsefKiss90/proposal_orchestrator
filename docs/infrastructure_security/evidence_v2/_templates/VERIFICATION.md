# <ticket-id> — verification report

| Field | Value |
|---|---|
| Verified by / on | `<agent>` / `<YYYY-MM-DD>` |
| Step sheet | `STEPS.md` (and `STEPS_fix<N>.md` if any) |
| Secret scan | `py -3.10 -m tools.evidence_secret_scan <folder>` → `CLEAN` / `REFUSED` (findings listed below) |

A REFUSED scan stops the verification here: the evidence is collected again, never edited.

## Criteria

One line per PASS criterion in the step sheet. Status is PASS, FAIL, MISSING, or N/A (with a reason).

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01 | `<criterion as written in STEPS.md>` | `<ticket-id>_01_<short-name>.json` | `PASS` | `<what the file shows>` |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| `<criterion>` | `PASS` / `FAIL` / `N/A` | `<file or report line>` |

## Done conditions (handoff §7a)

- [ ] Every criterion above is PASS, or N/A with a stated reason.
- [ ] Register v2 updated for: `<DC-xx, …>`.
- [ ] Worklog v2 entry: `<timestamp>`.
- [ ] Operator confirmed in session on `<YYYY-MM-DD>`.

## Follow-up

`none` / `STEPS_fix<N>.md written for: <failed criteria>`
