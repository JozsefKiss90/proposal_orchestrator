# OD10 upgrade checklist: leaving the AWS Free plan

**Operator only.** The agent does not carry out, script or schedule any item below, and holds no ELTE
billing detail. Every blank is filled by the operator, in the console, at upgrade time.

| Field | Value |
|---|---|
| Decision | OD10 (`plans/aws_redeployment_handoff_2026-10-21.md` §5): upgrade only after the ELTE financial office approves the reimbursement route, with ELTE billing details entered at the same moment |
| Budgets | OD13: 10 USD per month while on credits; after the upgrade, the approved HUF amount converted to USD, alerts at 50, 80 and 100 %; no automatic Budgets action on IAM |
| Account | `797661577394`; plan state today in `evidence_v2/R14/R14_01_plan-state.json` (Free plan, credits until `2027-04-19`) |
| Written by / on | agent (Claude) / 2026-11-12, ticket R14 |
| Status | Not started. Blocked by the ELTE approval |

Items marked **operator to confirm** state what the agent expects but could not confirm from an AWS
page. Check each one in the console before acting on it.

## 1. Before the upgrade

- [ ] The ELTE IK financial office has approved the reimbursement route in writing. Record the date and
      the approved amount in HUF: ______ HUF, approved on ______.
- [ ] `deploy/aws/pricing/budget.json`: set `approved_huf`, `approval_status`, and a HUF/USD rate with
      its source and date (for example the MNB official rate of the approval day). Commit it.
- [ ] Run the weekly cost check (`tools.aws_cost_check report`). Note the credits left and the
      month-to-date spend, so the first paid invoice can be checked against them.
- [ ] Confirm that no host stack exists (`proposal-orchestrator-host`), so nothing bills by the hour
      while the plan changes.
- [ ] **Operator to confirm:** what the upgrade changes. The agent expects that the remaining credits
      stay usable until their expiry date, that charges beyond the credits then go to the payment
      method, and that the upgrade cannot be undone.

## 2. At the upgrade (the same sitting)

- [ ] Billing and Cost Management → upgrade the account plan.
- [ ] **Tax settings:** enter the legal entity name, the address and the VAT number exactly as ELTE's
      financial office gives them. Legal name: ______. VAT number: ______. Address: ______.
- [ ] **Operator to confirm:** which AWS entity invoices this account (the agent expects AWS EMEA SARL for
      an EU billing address) and whether the financial office accepts it.
- [ ] **Payment method:** the one the financial office names. Do not store card details in this
      repository.
- [ ] **Operator to confirm:** the invoice currency the financial office wants, and whether AWS offers it
      as the payment currency.
- [ ] **Billing contact:** set the alternate billing contact the financial office names. Name and
      address: ______.
- [ ] **Invoice delivery:** the e-mail address the financial office names: ______.

## 3. Budgets after the upgrade (OD13)

- [ ] Create one budget for the approved amount: approved HUF ÷ rate of the approval day = ______ USD
      per ______ (month or project period, as the financial office sets it).
- [ ] Alerts at 50 %, 80 % and 100 % of actual spend, to the verified budget e-mail recipient (R1).
- [ ] Keep `My Monthly Cost Budget` (10 USD) while credits remain. Record whether it stays after that.
- [ ] No Budgets action that changes IAM or stops resources automatically (OD13).

## 4. After the upgrade

- [ ] Record the upgrade in `docs/infrastructure_security/aws_hardening_worklog_v2.md`: date, plan state
      (`aws freetier get-account-plan-state`), and the budgets (`aws budgets describe-budgets`). Save the
      two outputs as evidence. They hold no billing detail.
- [ ] Ask the agent for a decision record that succeeds OD10, so later step sheets drop the Free-plan
      checks of R1-D2.
- [ ] Run the cost check again within a week and compare spend against the new budget.

## Never

- Never paste the VAT number, address, payment details or invoices into a session, a commit or an
  evidence file.
- Never upgrade before the approval, even if a service asks for a paid plan. Report it instead (OD10).
