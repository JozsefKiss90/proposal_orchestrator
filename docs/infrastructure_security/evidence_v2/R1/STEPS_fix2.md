# R1 — Account baseline: step sheet, fix 2

| Field | Value |
|---|---|
| Replaces | The commands and PASS criteria of `STEPS.md` steps 12 and 14. Adds step 24. Everything else in `STEPS.md` and `STEPS_fix1.md` stands. |
| Why | Steps 12 and 14 (RUNLOG) were refused: the AWS-managed SCP `p-woqvv0rt` of organization `o-81s4kwxswn` explicitly denies `ec2:EnableEbsEncryptionByDefault`, `ec2:GetEbsEncryptionByDefault`, `ec2:ModifyInstanceMetadataDefaults` and `ec2:GetInstanceMetadataDefaults` to `AccountFullAccessRole`. The account-level defaults can neither be set nor read. Step 13 (S3 Block Public Access) succeeded. |
| Written by / on | agent (Claude) / 2026-10-21 |
| Account / region | `797661577394` / `us-east-1` |

The `>` redirection in steps 12 and 14 left **empty** `R1_12_…json` and `R1_14_…json` files in `~/R1`.
They are not evidence; the commands below remove them and save the refusals instead.

### Step 12 — EBS encryption by default: record the refusal

```bash
cd ~/R1 && rm -f R1_12_ebs-default-encryption.json
aws ec2 get-ebs-encryption-by-default --region us-east-1 --output json > R1_12_ebs-default-encryption-denied.txt 2>&1
```

| Evidence file | PASS criterion |
|---|---|
| `R1_12_ebs-default-encryption-denied.txt` | The refusal names `ec2:GetEbsEncryptionByDefault` and an explicit deny in a service control policy. The ticket item becomes **N/A (SCP)**, compensated in R11: the host's root volume is encrypted gp3 in the template, and R11 evidences `Encrypted=true` on the volume. |

### Step 14 — IMDSv2 default: record the refusal

```bash
cd ~/R1 && rm -f R1_14_imds-defaults.json
aws ec2 get-instance-metadata-defaults --region us-east-1 --output json > R1_14_imds-defaults-denied.txt 2>&1
```

| Evidence file | PASS criterion |
|---|---|
| `R1_14_imds-defaults-denied.txt` | The refusal names `ec2:GetInstanceMetadataDefaults` and an explicit deny in a service control policy. The ticket item becomes **N/A (SCP)**, compensated in R11: the host sets `HttpTokens=required`, hop limit 1, and R11 evidences both from `describe-instances`. |

### Step 24 — Probe the SCPs against the whole plan (creates nothing)

**Actions → Upload file** → `docs/infrastructure_security/evidence_v2/R1/r1_scp_probe.sh`, then:

```bash
mv ~/r1_scp_probe.sh ~/R1/ && cd ~/R1 && sed -i 's/\r$//' r1_scp_probe.sh
bash r1_scp_probe.sh R1_24_scp-probe.json
```

It checks, without creating anything, the actions R3–R11 need: VPC, subnet, security group, route
table, interface and gateway endpoints, flow logs, a t3.medium launch with encrypted gp3 and IMDSv2
(EC2 `--dry-run`); IAM role, policy, boundary and instance profile; KMS key; CloudTrail trail; S3
bucket policy; Secrets Manager policy; CloudWatch log group with KMS; CloudFormation stack; SSM Run
Command; and two read-only Bedrock calls. The non-EC2 probes send requests that are invalid on purpose,
so an allowed action ends in a validation or not-found error and nothing is made.

| Evidence file | PASS criterion |
|---|---|
| `R1_24_scp-probe.json` | No probe is `UNEXPECTED_SUCCESS`. Every probe's outcome is recorded; `scp_denied` and `inconclusive` probes are analysed by the agent, not judged here. |

If any probe shows `UNEXPECTED_SUCCESS`, stop and report it: something may have been created.
