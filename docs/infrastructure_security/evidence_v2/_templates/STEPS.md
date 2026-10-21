# <ticket-id> — <ticket title>: step sheet

| Field | Value |
|---|---|
| Ticket | `<ticket-id>` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, `<R-id>` |
| Written by / on | `<agent>` / `<YYYY-MM-DD>` |
| Account / region | `797661577394` / `<OD1 region>` |
| IDs taken from | `<earlier-ticket>_outputs.json` (list each file), or "none" |
| Controls touched | `<DC-xx, …>` |
| Hourly cost created | `none` / `<what, and the operator's explicit go recorded in RUNLOG.md>` |

## Before you start

- Run every step yourself, in order. Record each one in `RUNLOG.md`.
- Never save secret values, access keys, session tokens, passwords, MFA seeds, prompt or proposal
  text, or model output beyond the fixed test string.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or `0.0.0.0/0` egress rule, not even
  temporarily. Bedrock model invocation logging stays disabled.
- If a step fails, stop, write the error in `RUNLOG.md`, and do not improvise a fix.

## Steps

### Step 01 — <short title>

What it does: <one sentence>.

PowerShell:

```powershell
<command> --output json > <ticket-id>_01_<short-name>.json
```

CloudShell:

```bash
<command> --output json > <ticket-id>_01_<short-name>.json
```

Console path (only if there is no CLI form): `<Service> → <page> → <tab>`; save a screenshot or the
page text.

| Evidence file | PASS criterion |
|---|---|
| `<ticket-id>_01_<short-name>.json` | `<exact field and the value it must have>` |

<!-- Repeat "### Step NN" for every step. Number from 01; keep file numbers equal to step numbers. -->

## Outputs

If this ticket creates resources, save the stack outputs or the create output as
`<ticket-id>_outputs.json`. Later step sheets take IDs only from that file.

## Before you hand back

- [ ] Every evidence file listed above exists in this folder, under exactly its name.
- [ ] You opened each file and checked it for the items under "Before you start".
- [ ] `RUNLOG.md` records the UTC time, who ran each step, any deviation and any error.
