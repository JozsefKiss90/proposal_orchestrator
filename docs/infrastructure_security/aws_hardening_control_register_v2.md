# AWS Hardening Control Register — v2

## Proposal Orchestrator — Infrastructure Security Controls, redeployment

| Field | Value |
|---|---|
| Created | 2026-10-21 (ticket E0) |
| Account | `797661577394` |
| Region | `eu-north-1`, Bedrock through `eu.` profiles (OD1 successor `aws-redeployment-od1-region-r1_2026-10-21`); us-east-1 for global services only |
| Plan | `plans/aws_redeployment_handoff_2026-10-21.md` |
| Tickets | `plans/aws_redeployment_tickets.md` |
| Evidence tree | `evidence_v2/` (protocol: `evidence_v2/README.md`) |
| Worklog | `aws_hardening_worklog_v2.md` |
| History | Register v1: [`aws_hardening_control_register.md`](aws_hardening_control_register.md), with its evidence in `evidence/`. Both are kept unchanged as the record of the first hardening and describe resources that no longer exist. |

**How to read this register.** It lists the same 41 controls as v1 (DC-01 to DC-40, PL-8). The
requirement summaries are v1's, written region-neutrally until OD1 is decided; `<region>` stands for
the OD1 region. The *Ticket* column names the ticket whose evidence closes the control; R12b
re-evidences every control with the parameterised collector. A control's row is updated only when a
ticket's `VERIFICATION.md` shows the criterion verified, and the *Evidence (v2)* column then gives the
path under `evidence_v2/`. Nothing in this register is carried over from v1's evidence or IDs.

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| NOT_STARTED | Control has not been implemented |
| IN_PROGRESS | Implementation underway |
| IMPLEMENTED_PENDING_EVIDENCE | Implemented but evidence not yet collected or submitted |
| EVIDENCE_SUBMITTED | Evidence provided, awaiting review |
| VERIFIED_PASS | Evidence reviewed, control passes all criteria |
| VERIFIED_FAIL | Evidence reviewed, control fails one or more criteria |
| BLOCKED | Cannot proceed due to dependency or external blocker |
| NOT_APPLICABLE | Control does not apply to current deployment model |
| DEFERRED | Explicitly deferred with documented justification |

---

## Control Group 1 — VPC Endpoint / AWS PrivateLink

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-01 | VPC interface endpoint for bedrock-runtime | Interface endpoint for `com.amazonaws.<region>.bedrock-runtime` in `available` state | R11 | NOT_STARTED | — | — |
| DC-02 | Private DNS enabled on VPC endpoint | Private DNS enabled so `bedrock-runtime.<region>.amazonaws.com` resolves to private IPs from the host | R11 | NOT_STARTED | — | — |
| DC-03 | VPC endpoint security group (TCP 443 only) | Dedicated SG allowing only TCP 443 inbound from the host SG; no other rules | R4 (SG), R11 (attached) | NOT_STARTED | — | — |
| DC-04 | VPC endpoint policy scoped to runtime role and Claude models | Bedrock endpoint policy restricts to invocation actions on the OD7 model resources, for the runtime role | R11 | NOT_STARTED | — | — |
| DC-05 | Supporting VPC endpoints | Interface endpoints for secretsmanager, sts, ssm, ssmmessages, ec2messages; gateway endpoint for S3 | R4 (S3), R11 (interface) | NOT_STARTED | — | — |
| DC-06 | No internet route in deployment subnet | Deployment subnet route table has no `0.0.0.0/0` route and no IGW or NAT target | R4 | NOT_STARTED | — | — |
| DC-37 | End-to-end Bedrock Converse call succeeds | `converse()` call succeeds from the host via PrivateLink, attributed to the hardened runtime role | R11 | NOT_STARTED | — | — |
| PL-8 | VPC DNS settings | `enableDnsHostnames` and `enableDnsSupport` both `true` | R4 | NOT_STARTED | — | — |

---

## Control Group 2 — IAM Least Privilege

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-09 | IAM role for Bedrock execution | Dedicated runtime role with correct trust policy; it is the role the host's instance profile uses (F1) | R5 | NOT_STARTED | — | — |
| DC-10 | Bedrock invocation policy | Invoke scoped to the OD7 profiles and the foundation models in every region they route to (F2) | R5 | NOT_STARTED | — | — |
| DC-11 | Explicit deny statements | Deny Bedrock admin actions, non-Bedrock services outside the policy, and non-Claude models | R5 | NOT_STARTED | — | — |
| DC-12 | Permission boundary attached | Boundary limiting the runtime role to exactly what it needs, attached to the runtime role | R5 | NOT_STARTED | — | — |
| DC-13 | Trust policy for compute service | Trust policy allows only the approved compute service | R5 | NOT_STARTED | — | — |
| DC-14 | Instance profile associated with deployment host | Host uses the instance profile, not long-term keys | R11 | NOT_STARTED | — | — |
| DC-15 | No long-term access keys on deployment host | No long-term key variables in files or environment on the host; in-host negative tests collected | R12b | NOT_STARTED | — | v1 never collected the in-host tests |

---

## Control Group 3 — Region Enforcement

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-16 | Region enforcement via IAM condition | `aws:RequestedRegion` condition limits calls to the OD1 region and the regions the OD7 profiles route to | R5, R12b | NOT_STARTED | — | — |
| DC-17 | Negative region test | A Bedrock call to an unapproved region fails | R12b | NOT_STARTED | — | — |
| DC-40 | SCP for region restriction (if Organization) | SCP denying Bedrock in non-approved regions, if the account is in an Organization | R12b | NOT_STARTED | — | Re-assess. R1 step 00: the account is a member of the AWS-managed organization of the new sign-up experience (management account outside this project), with SCPs enabled and managed by AWS |

---

## Control Group 4 — KMS Encryption

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-18 | Customer-managed KMS key with rotation | Symmetric CMK with alias `alias/proposal-orchestrator`, automatic rotation enabled | R6 | NOT_STARTED | — | — |
| DC-19 | KMS key policy scoped | Key policy grants the account root, the runtime role, CloudTrail (SourceArn) and CloudWatch Logs (log-group prefix) only | R6 | NOT_STARTED | — | — |

---

## Control Group 5 — Secrets Manager

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-20 | Secret created and encrypted with CMK | `proposal-orchestrator/env-config` stored encrypted with the CMK (or the OD8 (b) design, restated) | R8 | NOT_STARTED | — | — |
| DC-21 | Secret resource policy scoped | Resource policy names only the runtime identity, plus an admin role if one exists | R8 | NOT_STARTED | — | — |
| DC-22 | API key rotation configured (if applicable) | Rotation for any API-key secret | R8 | NOT_STARTED | — | Re-assess; applies only if an API-key secret exists |

---

## Control Group 6 — CloudTrail

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-23 | CloudTrail trail with KMS encryption | Trail `proposal-orchestrator-bedrock-trail` encrypted with the CMK | R7 | NOT_STARTED | — | — |
| DC-24 | Log file validation enabled | Digest files enabled | R7 | NOT_STARTED | — | — |
| DC-25 | Trail S3 bucket secured | Encryption, deny insecure transport and unencrypted objects, versioning, Block Public Access | R7 | NOT_STARTED | — | — |
| DC-26 | CloudTrail captures Bedrock Converse events | Converse events appear in CloudTrail after the test call | R11 | NOT_STARTED | — | — |
| DC-27 | S3 lifecycle policy for trail logs | Glacier Instant Retrieval after 90 days, expiry after 365 days | R7 | NOT_STARTED | — | — |

---

## Control Group 7 — CloudWatch

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-28 | Bedrock model invocation logging disabled | Invocation-logging configuration is empty | R7 | NOT_STARTED | — | — |
| DC-29 | No Bedrock invocation log groups | No `/aws/bedrock` log groups exist | R7 | NOT_STARTED | — | — |
| DC-30 | Operational log groups encrypted, retention set | Log groups use the CMK and at most 90-day retention | R7 | NOT_STARTED | — | — |

---

## Control Group 8 — Data Egress Prevention

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-07 | Host SG restricts outbound | Outbound TCP 443 to the endpoint SG (and the S3 prefix list); no `0.0.0.0/0` | R4 (SG), R11 | NOT_STARTED | — | Wording to be corrected in R4 |
| DC-08 | VPC flow logs enabled | Flow logs with traffic type ALL on every subnet, to CloudWatch Logs | R7 | NOT_STARTED | — | — |
| DC-31 | No Claude CLI binary on deployment host | `which claude` returns not found | R12b | NOT_STARTED | — | — |
| DC-32 | Internet egress blocked from deployment host | Requests to public endpoints from the host time out or fail | R12b | NOT_STARTED | — | — |

---

## Control Group 9 — Production Application Configuration

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-33 | `ORCHESTRATOR_PRODUCTION_MODE=true` | Production mode set, read on the host through the R9 launcher | R8, R9, R12b | NOT_STARTED | — | — |
| DC-34 | Converse transport preset | Transport preset selects the Bedrock Converse backend for the OD1 region | R8, R9, R12b | NOT_STARTED | — | — |
| DC-35 | `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` | Diagnostic level prevents prompt and response content being written to disk | R8, R9, R12b | NOT_STARTED | — | — |
| DC-36 | Model availability confirmed in target region | The OD7 models answer in the OD1 region | R2, R11 | IN_PROGRESS | `evidence_v2/R2/` (`VERIFICATION.md`; `R2_07_converse-sonnet-4-6.json`, `R2_14_converse-opus-4-6-v1.json`, `R2_08_quotas-applied.json`) | R2 part verified 2026-10-21: the OD7 models (`aws-redeployment-od7-model-set_2026-10-21`) `eu.anthropic.claude-opus-4-6-v1` and `eu.anthropic.claude-sonnet-4-6` answer from eu-north-1 (CloudShell); RPM 5 / 10. Newer models refused for this account. Host-side call through PrivateLink remains for R11. |
| DC-38 | Full DAG run succeeds with production config | All phases complete, all gates pass under production configuration | R16 | NOT_STARTED | — | Scope per OD12 |

---

## Control Group 10 — Compliance

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-39 | GDPR DPA in effect | AWS data processing terms in effect for the new account | R12b | NOT_STARTED | — | — |

---

## Summary

| Control Group | Controls | NOT_STARTED | IN_PROGRESS | VERIFIED_PASS | VERIFIED_FAIL | BLOCKED | DEFERRED | N/A |
|---|---|---|---|---|---|---|---|---|
| 1 - PrivateLink | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 - IAM | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 - Region | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 - KMS | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 - Secrets Manager | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| 6 - CloudTrail | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| 7 - CloudWatch | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8 - Data Egress | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| 9 - Production Config | 5 | 4 | 1 | 0 | 0 | 0 | 0 | 0 |
| 10 - Compliance | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| **TOTAL** | **41** | **40** | **1** | **0** | **0** | **0** | **0** | **0** |

Resource IDs are not listed here. They live in each ticket's `<ticket-id>_outputs.json`.
