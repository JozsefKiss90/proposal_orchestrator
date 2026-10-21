# R1 — Account baseline: step sheet, fix 1

| Field | Value |
|---|---|
| Replaces | `STEPS.md` steps 01–05, 07–09, and the PASS criteria of 15 and 19. Every other step of `STEPS.md` stands as written. |
| Why | Step 00 (RUNLOG) measured that account `797661577394` was created through "Sign up for AWS (new)". The Builder ID owns it; root sign-in is refused; the console identity is `assumed-role/AccountFullAccessRole/…` (`AdministratorAccess`); the account is a member of the AWS-managed organization `o-81s4kwxswn`. In that model IAM users cannot sign in to the console, so `po-admin` cannot be the admin identity. |
| Decision applied | OD11 successor `aws-redeployment-od11-admin-identity-r2_2026-10-21` (supersedes r1) |
| Written by / on | agent (Claude) / 2026-10-21 |
| Account / region | `797661577394` / `us-east-1` |

All rules under "Before you start" in `STEPS.md` still apply. Sign in with the **Builder ID**; every
CloudShell step runs in `~/R1` in us-east-1. Do **not** create IAM users or access keys.

---

## Replaced steps

### Step 00 — Baseline diagnosis (already run)

The files are in CloudShell `~/R1`. Their criteria:

| Evidence file | PASS criterion |
|---|---|
| `R1_00_caller-identity.json` | `Account` = `797661577394`; `Arn` = `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/<session>` |
| `R1_00_organization.json` | Records the organization the account belongs to (fact, not judged) |
| `R1_00_account-summary.json` | `Users` = `0`; `AccountAccessKeysPresent` = `0` |
| `R1_00_role.json` | `RoleName` = `AccountFullAccessRole`; trust only `account-access.amazonaws.com` |
| `R1_00_role-policies.json` | Exactly `AdministratorAccess` attached |
| `R1_00_role-inline.json` | `PolicyNames` empty |
| `R1_00_roles.json` | Lists the roles present before cleanup (fact; Explore AWS leftovers go to Part C) |
| `R1_00_budgets.json` | One `COST` budget, `MONTHLY`, `10.0` `USD`, whose `FilterExpression` excludes `RECORD_TYPE` `Credit` and `Refund` (this replaces the step 15 criterion) |
| `R1_00_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE` (remaining credits recorded) |

### Step 01 — Owner MFA (Builder ID) — done, evidence only

The MFA registered on the Builder ID profile (RUNLOG step 01, attempt 1) is the owner identity's MFA.
Open `https://profile.aws.amazon.com` → **Security** and take a screenshot of the
**Multi-factor authentication (MFA) devices** box **only**. Crop out the **Signed in devices** box; it
shows your IP address.

| Evidence file | PASS criterion |
|---|---|
| `R1_01_builder-id-mfa.png` | At least one MFA device registered (type `WEBAUTHN`) |

### Steps 02–05 — cancelled

IAM billing access (02) is not needed: the console role already reads budgets and the plan state
(`R1_00_budgets.json`, `R1_00_plan-state.json`). No `po-admin` user is created (03–05).

### Steps 07–09 — covered by step 00

`R1_00_account-summary.json`, `R1_00_caller-identity.json` and the three `R1_00_role*.json` files
replace `R1_07`, `R1_08` and `R1_09`. Nothing to run.

### Step 10 — Workstation CLI through `aws login` — now a test

Run it exactly as in `STEPS.md`, signing in with the Builder ID in the browser. Its criterion becomes:

| Evidence file | PASS criterion |
|---|---|
| `R1_10_workstation-identity.json` | `Arn` = `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/<session>`; RUNLOG shows CLI ≥ 2.32.0 |

If `aws login` refuses this kind of sign-in, write the error in `RUNLOG.md` and stop the step: the
criterion becomes **N/A**, and later tickets run their CLI steps in CloudShell only.

### Step 19 — Temporary test budget, created from the CLI

This copies the filter of the 10 USD budget, so gross cost (0.006 USD so far) counts:

```bash
aws budgets create-budget --account-id 797661577394 \
  --budget '{"BudgetName":"po-alert-test","BudgetType":"COST","TimeUnit":"MONTHLY","BudgetLimit":{"Amount":"0.01","Unit":"USD"},"FilterExpression":{"Not":{"Dimensions":{"Key":"RECORD_TYPE","Values":["Credit","Refund"]}}},"Metrics":["UnblendedCost"]}' \
  --notifications-with-subscribers '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":1,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"kissjozsef@inf.elte.hu"}]}]'
aws budgets describe-budget --account-id 797661577394 --budget-name po-alert-test --output json > R1_19_test-budget.json
```

If `create-budget` rejects `FilterExpression` or `Metrics`, write the error in `RUNLOG.md` and create
the same budget in the console instead (amount 0.01 USD, exclude charge types Credit and Refund,
Actual alert at 1 %, the same recipient).

| Evidence file | PASS criterion |
|---|---|
| `R1_19_test-budget.json` | `BudgetLimit` = `0.01` `USD`; `FilterExpression` excludes `Credit`; `CalculatedSpend.ActualSpend` present (amount recorded) |

---

## Part C additions (cleanup)

`R1_00_roles.json` shows three customer roles from Explore AWS: `PowerUser-lambda-1`, `PowerUserRole`,
`rds-monitoring-role`. `STEPS_cleanup.md` will remove them together with whatever
`R1_22_inventory-before.json` lists. The roles under `/managed/` and `/aws-service-role/` belong to
AWS and are never touched.

## Order from here

01 (screenshot) → 06 (upload the script) → 10 → 11 → 12 → 13 → 14 → 16 → 17 → 18 → 19 → 22 → 23 → hand back.
20 and 21 follow when the alert arrives.
