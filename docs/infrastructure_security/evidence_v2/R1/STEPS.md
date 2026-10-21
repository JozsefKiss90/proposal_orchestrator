# R1 — Account baseline: step sheet

| Field | Value |
|---|---|
| Ticket | `R1` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R1 |
| Decisions applied | R0 record `aws-redeployment-operator-decisions_2026-10-21` (OD1 us-east-1, OD13 budgets), OD11 successor `aws-redeployment-od11-admin-identity_2026-10-21` (IAM user `po-admin`) |
| Written by / on | agent (Claude) / 2026-10-21 |
| Account / region | `797661577394` / `us-east-1` |
| IDs taken from | none (R1 creates no stack) |
| Controls touched | none directly; R1 is the account baseline the controls rest on |
| Hourly cost created | none |

## Before you start

- Run every step yourself, in order. Record each one in `RUNLOG.md` (copy `../_templates/RUNLOG.md`).
- Never save secret values, access keys, session tokens, passwords, MFA seeds or QR codes, prompt or
  proposal text. Do **not** create access keys for root or for `po-admin`, at any point.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or egress rule. Do not upgrade the account or
  enter billing or tax details (OD10).
- If a step fails, stop, write the error in `RUNLOG.md`, and do not improvise a fix.
- **Where commands run.** Part A is console only, as root. Parts B and C run in **CloudShell in
  us-east-1 as `po-admin`**, except step 10, which runs in **PowerShell** on the workstation. CloudShell
  writes UTF-8 and needs no workstation credentials, so the evidence commands are given in that one
  form. If you run a command in PowerShell instead, pipe it to `Out-File -Encoding utf8 <file>`; never
  use `>` there, which writes UTF-16.
- **Steps 20 and 21 are asynchronous.** Budget alerts are evaluated a few times a day; start step 19
  early and carry on.

---

## Part A — as root, console only

### Step 01 — Root MFA

Console: account menu (top right) → **Security credentials** → **Multi-factor authentication (MFA)** →
**Assign MFA device**. A passkey/security key or an authenticator app. Do not photograph the QR code.
Evidence for this step is collected in step 07.

### Step 02 — Let IAM users see billing

Console: account menu → **Account** → **IAM user and role access to Billing information** → **Edit** →
tick **Activate IAM Access** → **Update**. Without this, `po-admin` cannot manage budgets.

| Evidence file | PASS criterion |
|---|---|
| `R1_02_iam-billing-access.png` | The section reads that IAM user/role access to billing information is activated |

### Step 03 — Create `po-admin`

Console: **IAM** → **Users** → **Create user**.
- User name: `po-admin`. Tick **Provide user access to the AWS Management Console** → **I want to
  create an IAM user** → custom password (keep it in your password manager, nowhere else).
- Permissions: **Attach policies directly** → `AdministratorAccess` only.
- Tags: `project` = `proposal-orchestrator`.
- **Do not** create access keys.

Evidence for this step is collected in step 09.

### Step 04 — MFA for `po-admin`

Console: **IAM** → **Users** → `po-admin` → **Security credentials** → **Assign MFA device**.

### Step 05 — Sign out root

Note the sign-in URL shown on the IAM dashboard (`https://797661577394.signin.aws.amazon.com/console`).
Sign out. Root is not used again in R1 or afterwards.

---

## Part B — as `po-admin`

### Step 06 — Open CloudShell and prepare the folder

Sign in as `po-admin` with MFA. Set the console Region to **US East (N. Virginia)** and open
**CloudShell**. **Actions → Upload file** → `docs/infrastructure_security/evidence_v2/R1/r1_inventory.sh`.

```bash
mkdir -p ~/R1 && mv ~/r1_inventory.sh ~/R1/ && cd ~/R1 && sed -i 's/\r$//' r1_inventory.sh && aws --version
```

(`sed` strips Windows line endings, in case the file was saved with CRLF.)

All later CloudShell steps run in `~/R1`. No evidence file.

### Step 07 — Root MFA on, no root keys

```bash
aws iam get-account-summary --output json > R1_07_account-summary.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_07_account-summary.json` | `SummaryMap.AccountMFAEnabled` = `1` and `SummaryMap.AccountAccessKeysPresent` = `0` |

### Step 08 — CloudShell runs as `po-admin`

```bash
aws sts get-caller-identity --output json > R1_08_cloudshell-identity.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_08_cloudshell-identity.json` | `Account` = `797661577394`; `Arn` = `arn:aws:iam::797661577394:user/po-admin` |

### Step 09 — `po-admin`: policy, MFA, no keys

```bash
jq -n \
  --argjson user     "$(aws iam get-user --user-name po-admin --output json)" \
  --argjson policies "$(aws iam list-attached-user-policies --user-name po-admin --output json)" \
  --argjson inline   "$(aws iam list-user-policies --user-name po-admin --output json)" \
  --argjson groups   "$(aws iam list-groups-for-user --user-name po-admin --output json)" \
  --argjson mfa      "$(aws iam list-mfa-devices --user-name po-admin --output json)" \
  --argjson keys     "$(aws iam list-access-keys --user-name po-admin --output json)" \
  '{user: $user.User, attached_policies: $policies.AttachedPolicies, inline_policies: $inline.PolicyNames,
    groups: $groups.Groups, mfa_devices: $mfa.MFADevices, access_keys: $keys.AccessKeyMetadata}' \
  > R1_09_admin-user.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_09_admin-user.json` | `attached_policies` is exactly `AdministratorAccess`; `inline_policies` and `groups` empty; `mfa_devices` has 1 entry; `access_keys` empty; `user.Tags` holds `project=proposal-orchestrator` |

### Step 10 — Workstation CLI through `aws login` (PowerShell)

```powershell
aws --version
```

If the version is below `aws-cli/2.32.0`, install the current AWS CLI v2 MSI first, then reopen
PowerShell. Then, from the repository root:

```powershell
aws login --profile po-admin
aws sts get-caller-identity --profile po-admin --output json |
  Out-File -Encoding utf8 docs\infrastructure_security\evidence_v2\R1\R1_10_workstation-identity.json
```

`aws login` opens the browser; sign in as `po-admin` with MFA; give `us-east-1` if asked for a Region.
Write the `aws --version` line into `RUNLOG.md`.

| Evidence file | PASS criterion |
|---|---|
| `R1_10_workstation-identity.json` | `Arn` = `arn:aws:iam::797661577394:user/po-admin`; RUNLOG shows CLI ≥ 2.32.0 |

### Step 11 — Console default Region

Console: gear icon (top right) → **See all user settings** → **Localization and default Region** →
**Edit** → Default Region **US East (N. Virginia) us-east-1** → **Save**.

| Evidence file | PASS criterion |
|---|---|
| `R1_11_default-region.png` | Default Region shows US East (N. Virginia) |

### Step 12 — EBS encryption by default (us-east-1)

```bash
aws ec2 enable-ebs-encryption-by-default --region us-east-1 --output json > /dev/null
aws ec2 get-ebs-encryption-by-default --region us-east-1 --output json > R1_12_ebs-default-encryption.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_12_ebs-default-encryption.json` | `EbsEncryptionByDefault` = `true` |

### Step 13 — S3 Block Public Access, account level

```bash
aws s3control put-public-access-block --account-id 797661577394 \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3control get-public-access-block --account-id 797661577394 --output json > R1_13_s3-account-bpa.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_13_s3-account-bpa.json` | All four of `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets` = `true` |

### Step 14 — IMDSv2 required by default (us-east-1)

```bash
aws ec2 modify-instance-metadata-defaults --region us-east-1 \
  --http-tokens required --http-put-response-hop-limit 1 --output json > /dev/null
aws ec2 get-instance-metadata-defaults --region us-east-1 --output json > R1_14_imds-defaults.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_14_imds-defaults.json` | `AccountLevel.HttpTokens` = `required`; `AccountLevel.HttpPutResponseHopLimit` = `1`; `ManagedBy` = `account` |

### Step 15 — The 10 USD budget (OD13)

```bash
aws budgets describe-budgets --account-id 797661577394 --output json > R1_15_budgets.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_15_budgets.json` | One budget with `BudgetType` = `COST`, `TimeUnit` = `MONTHLY`, `BudgetLimit` = `10` `USD`, and `CostTypes.IncludeCredit` = `false` |

If `IncludeCredit` is `true`, the budget counts credits against cost, so it reads near zero while the
credits last and never alerts. Fix it in the console (**Billing and Cost Management → Budgets** → the
budget → **Edit** → **Advanced options** → untick **Credits** → **Save**), note it in `RUNLOG.md`, and
re-run this step.

### Step 16 — No budget actions (OD13)

```bash
aws budgets describe-budget-actions-for-account --account-id 797661577394 --output json > R1_16_budget-actions.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_16_budget-actions.json` | `Actions` is empty |

### Step 17 — Alert and recipient of the 10 USD budget

```bash
for b in $(aws budgets describe-budgets --account-id 797661577394 --query 'Budgets[].BudgetName' --output text); do
  aws budgets describe-notifications-for-budget --account-id 797661577394 --budget-name "$b" --output json |
  jq -c --arg b "$b" '.Notifications[]' | while read -r n; do
    s=$(aws budgets describe-subscribers-for-notification --account-id 797661577394 --budget-name "$b" --notification "$n" --output json)
    jq -n --arg budget "$b" --argjson notification "$n" --argjson subs "$s" \
      '{budget: $budget, notification: $notification, subscribers: $subs.Subscribers}'
  done
done | jq -s . > R1_17_budget-notifications.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_17_budget-notifications.json` | At least one notification with `NotificationType` = `ACTUAL`; its subscribers include `EMAIL` `kissjozsef@inf.elte.hu` |

### Step 18 — Recipient verified

Console: **Billing and Cost Management → Budgets** → the 10 USD budget → alert recipients. If the
address shows **Pending** or **Inactive**, choose **Resend verification** / **Send Notification**, open
the e-mail within 12 hours, follow the link and sign in to this account (as `po-admin`).

| Evidence file | PASS criterion |
|---|---|
| `R1_18_recipient-verified.png` | `kissjozsef@inf.elte.hu` shows status **Active** |

### Step 19 — Temporary test budget

Console: **Budgets** → **Create budget** → **Customize (advanced)** → **Cost budget**.
- Name `po-alert-test`; period **Monthly**; **Fixed**; amount **0.01** USD.
- **Advanced options**: untick **Credits** (so gross cost counts).
- Alert: **Actual**, threshold **1 %** of budgeted amount, recipient `kissjozsef@inf.elte.hu`.
- No actions.

Then:

```bash
aws budgets describe-budget --account-id 797661577394 --budget-name po-alert-test --output json > R1_19_test-budget.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_19_test-budget.json` | `BudgetLimit` = `0.01` `USD`; `CostTypes.IncludeCredit` = `false`; `CalculatedSpend.ActualSpend` present (its amount is recorded, not judged) |

If the account has had no gross spend this month, this budget cannot cross its threshold and no alert
comes. Write the `ActualSpend` amount into `RUNLOG.md`; the agent then writes `STEPS_fix1.md`.

### Step 20 — The test alert arrives (asynchronous)

Wait for the alert e-mail (up to about a day).

| Evidence file | PASS criterion |
|---|---|
| `R1_20_test-alert.png` | An AWS Budgets alert for `po-alert-test` received at `kissjozsef@inf.elte.hu`, with its receive time visible |

### Step 21 — Remove the test budget (after step 20)

```bash
aws budgets delete-budget --account-id 797661577394 --budget-name po-alert-test
aws budgets describe-budgets --account-id 797661577394 --output json > R1_21_budgets-after-test.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_21_budgets-after-test.json` | Only the 10 USD budget remains |

### Step 22 — Inventory of every enabled Region (read-only)

```bash
bash r1_inventory.sh R1_22_inventory-before.json
```

It prints the Regions with findings and with errors. It changes nothing. It takes a few minutes.

| Evidence file | PASS criterion |
|---|---|
| `R1_22_inventory-before.json` | `regions_with_errors` is empty; `regions_scanned` ≥ 17. Findings are expected here (Explore AWS leftovers) and are not judged in this step |

### Step 23 — Bring the evidence home

```bash
cd ~ && zip -r R1_evidence.zip R1 -x 'R1/r1_inventory.sh'
```

CloudShell **Actions → Download file** → `R1_evidence.zip`. Then in PowerShell, from the repository root:

```powershell
Expand-Archive -Path "$HOME\Downloads\R1_evidence.zip" -DestinationPath "$env:TEMP\R1_evidence" -Force
Copy-Item "$env:TEMP\R1_evidence\R1\R1_*" docs\infrastructure_security\evidence_v2\R1\
```

Add the screenshots (`R1_02`, `R1_11`, `R1_18`, later `R1_20`) to the same folder.

**Hand back here.** The agent reads `R1_22_inventory-before.json` and writes **Part C** (cleanup) as
`STEPS_cleanup.md`, with exact delete commands for exactly what was found. Deleting is irreversible,
so the list is written from your inventory, not guessed in advance.

---

## Part C — cleanup (written after step 22)

See `STEPS_cleanup.md` once it exists. Its last step repeats the inventory as
`R1_<NN>_inventory-after.json`, whose PASS criterion is: in every Region, no instance, volume,
snapshot, key pair, non-default security group, Elastic IP, NAT gateway, VPC endpoint, non-default VPC,
load balancer, Lambda function or RDS resource, and no errors.

## Outputs

R1 creates no stack. No `R1_outputs.json`.

## Before you hand back

- [ ] Every evidence file listed above exists in this folder, under exactly its name.
- [ ] You opened each file and checked it for the items under "Before you start".
- [ ] `RUNLOG.md` records the UTC time, who ran each step, any deviation and any error.
