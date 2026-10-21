# R1 — Account baseline: step sheet, fix 4 (eu-north-1)

| Field | Value |
|---|---|
| Replaces | The Region of every remaining regional step. Steps 11, 12 and 14 are rewritten for eu-north-1 (fix 2's N/A applies only if eu-north-1 refuses them too). Step 22's criterion is rewritten. Adds step 30. Steps 16–21 and 23 stand as written in `STEPS.md` / `STEPS_fix1.md`. |
| Why | OD1 is revised to eu-north-1 (`aws-redeployment-od1-region-r1_2026-10-21`): it is the only Region this project account can build in (steps 25–27). |
| Written by / on | agent (Claude) / 2026-10-21 |
| Account / region | `797661577394` / `eu-north-1` (regional); us-east-1 for global services |

**Keep CloudShell in us-east-1.** CloudShell keeps a separate home directory per Region, and the R1
files are in the us-east-1 one. Every regional command below names `--region eu-north-1`; IAM,
Budgets and STS are global and need no Region.

### Step 11 — Console default Region: Stockholm

Console: gear icon → **See all user settings** → **Localization and default Region** → **Edit** →
Default Region **Europe (Stockholm) eu-north-1** → **Save**.

| Evidence file | PASS criterion |
|---|---|
| `R1_11_default-region.png` | Default Region shows Europe (Stockholm) |

### Step 12 — EBS encryption by default, eu-north-1

```bash
cd ~/R1
aws ec2 enable-ebs-encryption-by-default --region eu-north-1 --output json > /dev/null
aws ec2 get-ebs-encryption-by-default --region eu-north-1 --output json > R1_12_ebs-default-encryption-eu-north-1.json 2>&1
cat R1_12_ebs-default-encryption-eu-north-1.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_12_ebs-default-encryption-eu-north-1.json` | `EbsEncryptionByDefault` = `true`. If it holds an SCP refusal instead, fix 2's N/A (compensated in R11) applies. |

### Step 14 — IMDSv2 required by default, eu-north-1

```bash
aws ec2 modify-instance-metadata-defaults --region eu-north-1 \
  --http-tokens required --http-put-response-hop-limit 1 --output json > /dev/null
aws ec2 get-instance-metadata-defaults --region eu-north-1 --output json > R1_14_imds-defaults-eu-north-1.json 2>&1
cat R1_14_imds-defaults-eu-north-1.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_14_imds-defaults-eu-north-1.json` | `AccountLevel.HttpTokens` = `required`; `AccountLevel.HttpPutResponseHopLimit` = `1`. If it holds an SCP refusal instead, fix 2's N/A applies. |

The us-east-1 refusals (`R1_12_…-denied.txt`, `R1_14_…-denied.txt`) stay as evidence of why.

### Step 22 — Inventory: criterion for this account

Run as in `STEPS.md`. In the 16 Regions the project cannot use, every call is refused, so those
Regions report errors; nothing can exist there either.

| Evidence file | PASS criterion |
|---|---|
| `R1_22_inventory-before.json` | eu-north-1 is not in `regions_with_errors`; every Region in `regions_with_errors` is one of the 16 marked `denied` in `R1_26_region-access.txt`. Findings are not judged in this step. |

### Step 30 — Workstation profile to eu-north-1 (PowerShell)

```powershell
aws configure set region eu-north-1 --profile po-r1
aws configure get region --profile po-r1
```

No evidence file; write the printed Region into `RUNLOG.md`.

## Order from here

11 → 12 → 14 → 16 → 17 → 18 → 19 → 22 → 30 → 23 → hand back. 20 and 21 follow when the alert arrives.
