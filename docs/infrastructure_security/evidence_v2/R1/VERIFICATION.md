# R1 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-21 |
| Step sheets | `STEPS.md`, as replaced in part by `STEPS_fix1.md` (account model), `STEPS_fix2.md` (us-east-1 refusals, probe), `STEPS_fix3.md` (project Region, Bedrock), `STEPS_fix4.md` (eu-north-1), `STEPS_cleanup.md` (Part C) |
| Secret scan | `py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/R1` → `CLEAN` |
| Old-ID check | No file in the folder contains the old account id |
| Decisions applied | `aws-redeployment-od11-admin-identity-r2_2026-10-21`, `aws-redeployment-od1-region-r1_2026-10-21`, `aws-redeployment-r1-baseline-deviations_2026-10-21` |

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 00 | Console identity is `AccountFullAccessRole` in 797661577394 | `R1_00_caller-identity.json` | PASS | `assumed-role/AccountFullAccessRole/…` |
| 00 | Organization recorded | `R1_00_organization.json` | PASS | `o-81s4kwxswn`, management account 323258891184, SCPs enabled |
| 00 | `Users` 0, `AccountAccessKeysPresent` 0 | `R1_00_account-summary.json` | PASS | 0 and 0 (`AccountMFAEnabled` 0: no usable root, F-OD11r2-6) |
| 00 | Role trust only `account-access.amazonaws.com` | `R1_00_role.json` | PASS | — |
| 00 | Exactly `AdministratorAccess` attached; no inline | `R1_00_role-policies.json`, `R1_00_role-inline.json` | PASS | — |
| 00 | Roles before cleanup recorded | `R1_00_roles.json` | PASS | 3 Explore roles found, removed in C3 |
| 00 / 15 | One COST, MONTHLY, 10 USD budget excluding Credit and Refund | `R1_00_budgets.json` | PASS | — |
| 00 | Plan FREE, ACTIVE | `R1_00_plan-state.json` | PASS | 199.99 USD credits, expires 2027-04-19 |
| 01 | Owner MFA registered | `R1_01_builder-id-mfa.png` | PASS | Builder ID, one WEBAUTHN device |
| 02–05 | IAM billing access; `po-admin` | — | N/A | Cancelled by STEPS_fix1 (no IAM console users in this account model; OD11-r2) |
| 07–09 | Account summary, identity, admin | `R1_00_*` | PASS | Covered by step 00 (STEPS_fix1) |
| 10 | Workstation `aws login` as `AccountFullAccessRole`; CLI ≥ 2.32.0 | `R1_10_workstation-identity.json`, RUNLOG | PASS | aws-cli 2.34.54 |
| 11 | Console default Region | `R1_11_unified-settings-unavailable.png`, `R1_11_default-region.png` | N/A | Unified Settings needs the paid plan; project Region is eu-north-1 (R1-D1) |
| 12 | EBS encryption by default | `R1_12_ebs-default-encryption-eu-north-1.json` | PASS | `true` in eu-north-1 (us-east-1 refusal kept as history) |
| 13 | S3 Block Public Access, account level | `R1_13_s3-account-bpa.json` | PASS | all four `true` |
| 14 | IMDSv2 required, hop limit 1 | `R1_14_imds-defaults-eu-north-1.json` | PASS | `required`, 1, `ManagedBy` account (us-east-1 refusal kept as history) |
| 16 | No budget actions | `R1_16_budget-actions.json` | PASS | empty |
| 17 | ACTUAL notification to the ELTE address | `R1_17_budget-notifications.json` | PASS | ACTUAL 85 %, ACTUAL 100 %, FORECASTED 100 % |
| 18 | Recipient Active | `R1_18_recipient-inactive-verification-denied.png` | N/A | Inactive; verification denied by SCP. Replaced per R1-D2 |
| 19 | Test budget 0.01 USD excluding credits | `R1_19_test-budget.json` | PASS | ActualSpend 0.006 USD |
| 20 | Test alert received | `R1_20_test-alert-state.json` | PASS (alternative, R1-D2) | Notification state `ALARM`; e-mail delivery not possible |
| 21 | Only the 10 USD budget remains | `R1_21_budgets-after-test.json` | PASS | — |
| 22 | eu-north-1 scanned without error; errors only in denied Regions | `R1_22_inventory-before.json` | PASS | findings in eu-north-1 only: key pair, SG, Lambda |
| 24 | SCP probe in us-east-1 | `R1_24_scp-probe.json` | PASS (history) | Recorded; its `allowed` results are not evidence (RUNLOG agent correction) |
| 25 | Decoded refusal | `R1_25_decoded-createvpc.json` | PASS | statement `UsEast1Partitional` |
| 26 | One Region allowed | `R1_26_region-access.txt` | PASS | eu-north-1 |
| 27 | Probe in eu-north-1 with real ids; nothing created | `R1_27_scp-probe-eu-north-1.json` | PASS (note) | `real_ids_used` true; no SCP denial. The one `UNEXPECTED_SUCCESS` is `bedrock_logging_read`, a read-only Get that returned empty; the then-script classified any exit 0 that way. Nothing was created (C4 inventory). |
| 28 | Claude profiles and models listed | `R1_28_claude-profiles-eu-north-1.json`, `R1_28_claude-models-eu-north-1.json` | PASS | 26 profiles, 14 models (profile-only) |
| 29 | Converse through an `eu.` profile | `R1_29_converse-eu-profile.json` | PASS | `OK` from `eu.anthropic.claude-haiku-4-5-20251001-v1:0` |
| 31 | Pre-deletion inspection | `R1_31_cleanup-inspection.json` | PASS | — |
| C1–C3 | Every deletion succeeded | `R1_33_cleanup-log.txt` | PASS | Attempt 1 (11:38Z) deleted all eight items; attempt 2 after a console crash got NotFound for each |
| C4 | No findings; errors only in denied Regions | `R1_34_inventory-after.json` | PASS | — |
| C4 | No role at path `/` | `R1_35_roles-after.json` | PASS | 13 roles, all AWS-managed |
| C4 | No log groups | `R1_36_log-groups-after.json` | PASS | empty |
| 30 | Workstation profile Region eu-north-1 | RUNLOG | OPEN | Ran in CloudShell instead of PowerShell; repeat on the workstation (not a ticket criterion) |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| Each item has CLI output or console evidence, verified against its PASS criterion. | PASS | Table above; N/A items per OD11-r2 and R1-D1 |
| The budget recipient shows as verified, and a test alert has arrived. | PASS (alternative) | Not possible in this account (SCP); `ALARM` state evidenced and CLI monitoring adopted (R1-D2, operator-approved) |
| No billable resource is running outside the plan, in any region. | PASS | `R1_34_inventory-after.json`, `R1_35_roles-after.json`, `R1_36_log-groups-after.json` |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS, or N/A with a stated reason (step 30 is a convenience, not a criterion).
- [x] Register v2 updated for: none required; DC-40 note and the Region field updated during R1.
- [x] Worklog v2 entry: 2026-10-21T12:07:00Z.
- [ ] Operator confirmed in session on `<YYYY-MM-DD>`.

## Findings carried forward

- R2: Bedrock is reachable through `eu.` profiles from eu-north-1; quotas and the routed Regions per profile are R2's.
- R3–R11: this account cannot use CloudFormation, CloudTrail or SSM in any Region but eu-north-1; templates and step sheets target eu-north-1 only.
- R14: script the credit and alert-state check (R1-D2).
