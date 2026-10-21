# Evidence v2 — AWS private-network redeployment

Evidence for the rebuild of the hardened Bedrock environment in AWS account `797661577394`.
Plan: `plans/aws_redeployment_handoff_2026-10-21.md` (§7a is the protocol this tree implements).
Tickets: `plans/aws_redeployment_tickets.md`. Register: `../aws_hardening_control_register_v2.md`.
Worklog: `../aws_hardening_worklog_v2.md`.

The first hardening's evidence, in `../evidence/`, is history. Nothing in this tree is copied from it,
and nothing writes into it.

## Layout

```
evidence_v2/
  README.md            this file
  _templates/          STEPS.md, RUNLOG.md, VERIFICATION.md — copy into a ticket folder
  <ticket-id>/         one folder per ticket (R1, R2, R4, …)
    STEPS.md           written by the agent before the operator starts
    STEPS_fix1.md      only after a FAIL; never an edit to the evidence
    RUNLOG.md          written by the operator while running the steps
    <ticket-id>_<NN>_<short-name>.<json|txt|png>   one file per evidence step
    <ticket-id>_outputs.json                       stack or create outputs, if the ticket creates anything
    VERIFICATION.md    written by the agent after reading the evidence
```

## How a ticket gets ticked

1. The agent copies `_templates/STEPS.md` into the ticket folder and fills it: numbered steps, the
   command in PowerShell and CloudShell forms (or the console path), the evidence file each step
   produces, and the PASS criterion for each file. IDs come only from earlier `<ticket-id>_outputs.json`
   files, never from memory or from the old documents.
2. The operator runs the steps, saves each output under its file name, and keeps `RUNLOG.md`.
3. The agent runs the secret scan over the folder and refuses the evidence if it reports anything:

   ```powershell
   py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/<ticket-id>
   ```

   The patterns it refuses are listed in `tools/evidence_secret_scan.py`. A refusal means the evidence
   is collected again; the file is never edited to pass.
4. The agent reads every file against `STEPS.md` and writes `VERIFICATION.md`.
5. The ticket is done only when every criterion is PASS (or N/A with a reason), the register v2 rows
   are updated, a worklog v2 entry exists, and the operator confirms in session.

## Never save here

Secret values, access keys, session tokens, passwords, MFA seeds, prompt or proposal text, or model
responses beyond a fixed test string such as `OK` or `DEPLOY_OK`. Evidence records metadata only.
