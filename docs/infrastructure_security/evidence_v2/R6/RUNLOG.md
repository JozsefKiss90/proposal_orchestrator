# R6 — run log

| Field | Value |
|---|---|
| Ticket | R6 (KMS key) |
| Step sheet | `STEPS.md` |
| Kept by | agent (Claude), from the operator's reports in session |

## Round 1 — steps 01–03 (read-only)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| sign-in | 2026-10-26 16:34 | operator | `aws login --profile po-r1` from the VS Code PowerShell, repository root (`.venv-lint` active; no `py` command in this round) | none |
| 01 | 2026-10-26 16:35 | operator | Plan FREE / ACTIVE, credits 199.99 USD, expiry 2027-04-19; budget spend 0.006 of 10.0; three notifications OK | none |
| 02 | 2026-10-26 16:35 | operator | Account 797661577394, assumed-role/AccountFullAccessRole | none |
| 03a–03f | 2026-10-26 16:35 | operator | Twelve `alias/aws/*` aliases, no project alias; two AWS-managed keys (RDS, Lambda defaults), no customer-managed key; kms stack does not exist (`exit=254`); 14 project exports, iam `RuntimeRoleArn` as in `R5_outputs.json`; runtime role: the four R5 policies, no inline; no trail in eu-north-1 | none. PowerShell wrapped the 03c error in a `NativeCommandError` record, as expected |
| check | 2026-10-26 ~16:40 | agent | All fourteen files PASS against `STEPS.md`; secret scan of this folder and old-ID guard CLEAN | — |

## Round 1b — steps 04–05 (lint, guards, tests, change set)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 04 | 2026-10-26 16:46 | operator | cfn-lint 1.57.2 exit 0; template guard CLEAN (6); old-ID guard CLEAN; Python 3.10.6, 157 passed | `.venv-lint` was active during the `py -3.10` commands (the sheet says to `deactivate` first); harmless, `py -3.10` resolves to the system interpreter and the result is as expected |
| 05 | 2026-10-26 16:46:56 | operator | Change set `r6-create-01` `CREATE_COMPLETE` / `AVAILABLE`; `Capabilities` `[]`; tag `project`; three parameters, no `AdminRoleArn`; two `Add`: `ProjectKeyAlias` (AWS::KMS::Alias), `ProjectKey` (AWS::KMS::Key). The stack now exists in `REVIEW_IN_PROGRESS` with no resources | none |
| check | 2026-10-26 ~16:50 | agent | Both files PASS against `STEPS.md` step 05; step 04 files PASS; secret scan of this folder and old-ID guard CLEAN | — |
| go | 2026-10-26 ~16:51 | operator | Go in session ("mehet") on `R6_05_change-set.json`: two `Add`, as listed. Agent added steps 06–11 to `STEPS.md` | — |

## Round 2 — steps 06–10 (execute, outputs, read-only evidence, simulation, credits)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 06 | 2026-10-26 16:54 | operator | `execute exit=0`; stack `CREATE_COMPLETE`; key created 16:54:37Z, alias 16:54:41Z | none (`.venv-lint` active; no `py` command in this round) |
| 07 | 2026-10-26 ~16:56 | operator | Three outputs and exports (`KeyArn`, `KeyId`, `KeyAliasName`) | none |
| 08 | 2026-10-26 ~16:57 | operator | Key, rotation, alias, key policy, tags, grants, runtime role policies saved | none |
| 09 | 2026-10-26 ~16:58 | operator | `implicitDeny` for both actions; organizations and boundary allow | none |
| 10 | 2026-10-26 ~16:59 | operator | FREE / ACTIVE, 199.99 USD | none |
| check | 2026-10-26 ~17:05 | agent | All files PASS; key policy equal to the resolved template; `VERIFICATION.md`, register v2 DC-18/DC-19 and worklog written; secret scan and old-ID guard CLEAN | — |

## Round 3 — step 11 (tests, old-ID guard, secret scan)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 11 | 2026-10-26 ~17:04 | operator | Python 3.10.6, `179 passed`; old-ID guard `CLEAN`, `exit=0`; secret scan `CLEAN`, `exit=0` (run last) | none (`.venv-lint` not active) |
| check | 2026-10-26 ~17:06 | agent | Three files PASS; `VERIFICATION.md` complete except the operator's commit and confirmation | — |
