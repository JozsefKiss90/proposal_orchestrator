# R2 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-21 |
| Step sheet | `STEPS.md` (steps 01–12) and `STEPS_fix1.md` (steps 13–15); added read-only steps 05r, 07d, 08d, 15b are recorded in `RUNLOG.md` |
| Secret scan | Agent: `python3 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/R2` → `CLEAN` (exit 0), 45 `R2_*` files. The operator's `py -3.10` run in PowerShell printed no line in session; to be repeated once and its `CLEAN` line reported before the commit. |

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01 | `accountPlanType` FREE; `accountPlanStatus` ACTIVE; credits ≥ 199.00; expiration starts 2027-04-19 | `R2_01_plan-state.json` | PASS | FREE, ACTIVE, 199.99 USD, `2027-04-19T09:00:47…` |
| 01 | Exactly one budget `My Monthly Cost Budget`, limit 10.0, spend < 8.5; `po-alert-test` gone | `R2_01_budgets.json` | PASS | One budget, limit `10.0`, spend `0.006` |
| 01 | Three notifications, each `OK` | `R2_01_budget-notifications.json` | PASS | ACTUAL 100, ACTUAL 85, FORECASTED 100, all `OK`; STOP rule not triggered |
| 02 | `Account` 797661577394; `Arn` starts `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` | `R2_02_caller-identity.json` | PASS | As required. CloudShell ran in eu-north-1, not us-east-1 (RUNLOG step 02); no effect on R2 |
| 03 | Anthropic profiles listed; every `eu.` profile ACTIVE and routes only to `eu-` Regions; compared with R1_28 | `R2_03_profiles.json` | PASS | 26 profiles, all ACTIVE; 12 `eu.`, 0 non-`eu-` routed Regions among them; id set identical to `R1_28` |
| 04 | Every line starts `eu.anthropic.`; matches the list confirmed in session | `R2_04_candidates.txt` | PASS | Five ids, the proposed list run unchanged (RUNLOG step 04) |
| 04 | Every candidate PRESENT | `R2_04_candidates-check.txt` | PASS | 5 × PRESENT |
| 05 | One line per candidate | `R2_05_availability-exit.txt` | PASS | 5 × `exit=0` |
| 05 | Agreement, authorisation, entitlement, Region availability recorded (fact) | `R2_05_availability-<model>.json` (5) | PASS | All AUTHORIZED, entitlement and Region AVAILABLE, agreement NOT_AVAILABLE. Reference `R2_05_availability-haiku-4-5-reference.json` (added 05r): agreement AVAILABLE after its R1 call |
| 06 | `exit=0` for every candidate | `R2_06_profile-exit.txt` | PASS | 5 × `exit=0` |
| 06 | ACTIVE; SYSTEM_DEFINED; ARN `arn:aws:bedrock:eu-north-1:797661577394:inference-profile/<id>`; all routed Regions `eu-`, one eu-north-1 | `R2_06_profile-<model>.json` (5) | PASS | All five: as required, 6 routed Regions each |
| 07 | One line per candidate | `R2_07_converse-exit.txt` | PASS | sonnet-4-6 `exit=0`; the other four `exit=254` |
| 07 | Usable (`text` OK, `end_turn`/`max_tokens`) or refused with the error verbatim; at least one usable | `R2_07_converse-<model>.json` (5) | PASS | `sonnet-4-6`: OK, end_turn, 12/4 tokens. `opus-4-8`, `opus-5-5`, `sonnet-5-5`, `haiku-5-5`: AccessDeniedException "… is not available for this account … contact AWS Sales". No retry (not a try-again error). Added 07d (`R2_07_availability-after-*.json`): sonnet-4-6 agreement now AVAILABLE; the four refused stay NOT_AVAILABLE |
| 13 | Five ids in order | `R2_13_candidates-ext.txt` | PASS | sonnet-5, opus-5, opus-4-7, opus-4-6-v1, opus-4-5-20251101-v1:0 |
| 13 | All five PRESENT | `R2_13_candidates-ext-check.txt` | PASS | 5 × PRESENT |
| 14 | One line for Sonnet 5; Opus lines stop at the first `exit=0` | `R2_14_converse-exit.txt` | PASS | sonnet-5 254; opus-5 254; opus-4-7 254; opus-4-6-v1 0; Opus 4.5 not called |
| 14 | Usable or refused verbatim | `R2_14_converse-<model>.json` (4) | PASS | `opus-4-6-v1`: OK, end_turn, 12/4 tokens. `sonnet-5`, `opus-5`, `opus-4-7`: same AccessDeniedException as step 07 |
| 15 | As step 06 for the models that answered (plus Haiku 4.5, added 15b) | `R2_15_profile-opus-4-6-v1.json`, `R2_15_profile-haiku-4-5-20251001-v1-0.json` | PASS | Both ACTIVE, SYSTEM_DEFINED, correct ARN, 6 `eu-` Regions incl. eu-north-1 |
| 15 | Agreement state after the successful call (fact) | `R2_15_availability-opus-4-6-v1.json` | PASS | AVAILABLE, AUTHORIZED |
| 08 | For every usable model a cross-Region TPM and RPM line with a numeric value | `R2_08_quotas-applied.json` | PASS | 97 lines; codes in the table below. Added 08d: cross-Region RPM lines exist only for Haiku 4.5, Opus 4.5, Opus 4.6, Sonnet 4.5 (incl. 1M context), Sonnet 4.6; all adjustable |
| 09 | Default value for every code used from step 08 | `R2_09_quotas-default.json` | PASS | 97 lines; all six codes present |
| 10 | Empty or `{}`, no `loggingConfig` | `R2_10_invocation-logging.json` | PASS | 0 bytes |
| 11 | ACTIVE; credits ≥ step 01 − 0.10 | `R2_11_plan-state-after.json` | PASS | ACTIVE, 199.99 USD |
| 12 | 45 files home; secret scan clean | (no file) | PASS (agent) / pending (operator line) | See "Secret scan" above |

## Usable models (ticket table)

Account `797661577394`, called from eu-north-1. Every profile below is `SYSTEM_DEFINED`, ARN
`arn:aws:bedrock:eu-north-1:797661577394:inference-profile/<profile id>`, and routes to the foundation
model in **eu-north-1, eu-west-3, eu-south-1, eu-south-2, eu-west-1, eu-central-1**
(`arn:aws:bedrock:<Region>::foundation-model/<model id>`).

| `eu.` profile id | Foundation model id | Converse (fixed `OK`) | RPM applied / default (code) | TPM applied / default (code) |
|---|---|---|---|---|
| `eu.anthropic.claude-opus-4-6-v1` | `anthropic.claude-opus-4-6-v1` | OK (`R2_14_converse-opus-4-6-v1.json`) | **5** / 10,000 (`L-11DFF789`) | 3,000,000 / 3,000,000 (`L-0AD9BBE8`) |
| `eu.anthropic.claude-sonnet-4-6` | `anthropic.claude-sonnet-4-6` | OK (`R2_07_converse-sonnet-4-6.json`) | **10** / 10,000 (`L-00FF3314`) | 6,000,000 / 6,000,000 (`L-15B8E632`) |
| `eu.anthropic.claude-haiku-4-5-20251001-v1:0` | `anthropic.claude-haiku-4-5-20251001-v1:0` | OK in R1 (`../R1/R1_29_converse-eu-profile.json`) | **10** / 10,000 (`L-CCA5DF70`) | 5,000,000 / 5,000,000 (`L-58BE175A`) |

Refused for this account (AccessDeniedException "… is not available for this account … contact AWS
Sales"): `eu.` Opus 5.5, Opus 5, Opus 4.8, Opus 4.7, Sonnet 5.5, Sonnet 5, Haiku 5.5. Not tried: Opus 4.5,
Sonnet 4.5 (older than a usable model of the same family). `global.` profiles not used (OD1-r1).

## Findings for the operator

- **F-R2-1 (Confirmed):** the account answers only the 4.6 generation and older; every newer model is
  refused at invoke time, although `get-foundation-model-availability` reports it AUTHORIZED.
- **F-R2-2 (Confirmed):** applied cross-Region RPM is 5 (Opus 4.6) and 10 (Sonnet 4.6, Haiku 4.5)
  against a default of 10,000; TPM is at default. All lines are adjustable.
- **F-R2-3 (Inferred):** the refused models have no cross-Region RPM quota line in this account (08d),
  so the refusal is an account-level model allow-list rather than an SCP or a missing form. Whether the
  OD10 upgrade or a quota request lifts it is unknown. Input to OD10.
- **F-R2-4 (Confirmed):** a successful first call creates the model's Marketplace agreement
  (NOT_AVAILABLE → AVAILABLE); a refused call creates none.

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| A table lists each usable model by profile id, with its quotas and the regions it routes to | PASS | "Usable models" above |
| The OD7 successor decision record is committed | PENDING (written) | `docs/tier4_orchestration_state/decision_log/aws-redeployment-od7-model-set_2026-10-21.json`, settled in session; awaits the operator's commit |
| If the Free plan blocks Bedrock, the ticket stops and the block is reported as OD10 input | N/A | Bedrock is not blocked: three models answer. The partial model restriction and RPM cut are reported as OD10 input (F-R2-1 to F-R2-3) |

## Done conditions (handoff §7a)

- [ ] Every criterion above is PASS, or N/A with a stated reason. (Open: operator's scan line, OD7 record.)
- [x] Register v2 updated for: DC-36 (IN_PROGRESS; R11 closes the host-side part).
- [x] Worklog v2 entry: 2026-10-21T21:05:00Z.
- [ ] Operator confirmed in session.

## Follow-up

`STEPS_fix1.md` was an extension decided by the operator after step 07, not a fix of a FAIL. No FAIL.
