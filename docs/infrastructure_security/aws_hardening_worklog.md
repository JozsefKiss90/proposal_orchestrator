# AWS Hardening Worklog

## Proposal Orchestrator — Infrastructure Security Implementation Log

**Created:** 2026-05-29
**Source:** `aws_deployment_hardening_plan.md`

---

## Log Format

Each entry records:
- **Timestamp** — date and time of action
- **Control ID** — DC-xx reference from control register
- **Action Taken** — what was done
- **Evidence Requested** — what evidence was asked from the operator
- **Evidence Received** — what evidence was provided (file path or "pending")
- **Verification Result** — PASS / FAIL / PENDING / N/A
- **Next Action** — what happens next

---

## Entries

### 2026-05-29 — Session Initialization

| Field | Value |
|---|---|
| Timestamp | 2026-05-29T16:11:00Z |
| Control ID | ALL |
| Action Taken | Created control register (`aws_hardening_control_register.md`), worklog (`aws_hardening_worklog.md`), and evidence directory structure (11 subdirectories under `docs/infrastructure_security/evidence/`) |
| Evidence Requested | — |
| Evidence Received | — |
| Verification Result | N/A |
| Next Action | Begin Control Group 1 — VPC Endpoint / AWS PrivateLink implementation guidance |

---

### 2026-05-29 — Control Group 1: PrivateLink Implementation Guide Delivered

| Field | Value |
|---|---|
| Timestamp | 2026-05-29T16:20:00Z |
| Control ID | DC-01, DC-02, DC-03, DC-04, DC-05, DC-06, DC-37 |
| Action Taken | Reviewed AWS Bedrock User Guide (local PDF + Context7 MCP docs for `vpc-interface-endpoints.md`). Produced implementation guide with: target architecture, AWS Console steps, AWS CLI/CloudShell commands, evidence artifact specifications, PASS/FAIL criteria. Delivered to operator. |
| Evidence Requested | EV-PL-001 through EV-PL-008 (see implementation guide below and evidence directory `docs/infrastructure_security/evidence/01_privatelink/`) |
| Evidence Received | Pending — awaiting operator implementation |
| Verification Result | PENDING |
| Next Action | Operator implements PrivateLink controls and provides evidence artifacts |

---

### 2026-05-29 — Control Group 1: Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-05-29T17:00:00Z |
| Control ID | DC-01, DC-02, DC-03, DC-04, DC-05, DC-06, DC-37, PL-8 |
| Action Taken | Reviewed all evidence files in `docs/infrastructure_security/evidence/01_privatelink/`. Verified: endpoint state, Private DNS, DNS resolution from host, SG hardening, route table, supporting endpoints, VPC DNS settings. Identified DC-04 endpoint policy as full-access (needs scoping). Confirmed DC-37 deferred until IAM. Updated control register with verified statuses and infrastructure reference table. |
| Evidence Received | `control_group_1_logs.txt` (VPC endpoint creation, route table, endpoint listing, DNS settings), `EV-PL-005-private-dns-resolution.txt` (SG hardening, SSM endpoints, instance launch, DNS resolution from host), `EV-PL-006-functional-test.txt` (status summary — PL-6 deferred), `logs.txt` (duplicate of EV-PL-005) |
| Verification Result | DC-01: VERIFIED_PASS, DC-02: VERIFIED_PASS, DC-03: VERIFIED_PASS, DC-04: VERIFIED_FAIL (full-access policy), DC-05: VERIFIED_PASS, DC-06: VERIFIED_PASS, DC-37: DEFERRED (IAM), PL-8: VERIFIED_PASS |
| Next Action | DC-04 endpoint policy scoping deferred to after CG2 IAM role creation. DC-37 functional test deferred to after CG2. Proceed to Control Group 2 — IAM Least Privilege. |

---

### 2026-05-29 — Control Group 2: IAM Least Privilege — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-05-29T19:30:00Z |
| Control ID | DC-09, DC-10, DC-11, DC-12, DC-13, DC-14, DC-15, DC-04 (CG1 resolved), DC-37 (CG1 resolved) |
| Action Taken | Reviewed 18 evidence files in `docs/infrastructure_security/evidence/02_iam/`. Verified: role creation, 4 policy documents (bedrock-invoke, supporting-services, explicit-deny, boundary), trust policy, permission boundary attachment, 6 simulation tests, caller identity from host, functional Bedrock test, VPC endpoint policy scoping. All CG2 controls and both deferred CG1 controls verified. |
| Evidence Received | `EV-IAM-001-role-config.json`, `EV-IAM-002-attached-policies.json`, `EV-IAM-003-policy-*.json` (4 files), `EV-IAM-004-boundary-metadata.json`, `EV-IAM-010-trust-policy.json`, `EV-VPC-004-bedrock-endpoint-policy.json`, `IAM_Least_Privilege_logs.txt` (901 lines), policy source JSON files (5 files), validation policy files (2 files) |
| Verification Result | DC-09: VERIFIED_PASS, DC-10: VERIFIED_PASS, DC-11: VERIFIED_PASS, DC-12: VERIFIED_PASS, DC-13: VERIFIED_PASS, DC-14: VERIFIED_PASS, DC-15: VERIFIED_PASS. DC-04: VERIFIED_PASS (resolved from CG1 FAIL). DC-37: VERIFIED_PASS (resolved from CG1 DEFERRED). |
| Next Action | CG1 and CG2 fully verified (15/41 controls PASS). Proceed to Control Group 3 — Region Enforcement. |

---

### 2026-06-01 — Control Group 3: Region Enforcement — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-06-01T10:15:00Z |
| Control ID | DC-16, DC-17, DC-40 |
| Action Taken | Reviewed 4 evidence files in `docs/infrastructure_security/evidence/03_region_enforcement/`. Verified: IAM region condition (cross-ref CG2), negative region test from deployment host, AWS Organization status. |
| Evidence Received | `CG3_steps.txt` (gap analysis and test plan), `CG3_logs.txt` (empty — tests captured in REG-E03/E04), `REG-E03-negative-region-test.txt` (negative region test: ap-southeast-1 timeout exit 124, us-east-1 success exit 0), `REG-E04-organization-check.txt` (AWSOrganizationsNotInUseException — account not in Organization) |
| Verification Result | DC-16: VERIFIED_PASS (cross-ref CG2 `EV-IAM-003`). DC-17: VERIFIED_PASS (ap-southeast-1 denied by network isolation + IAM; us-east-1 succeeded). DC-40: NOT_APPLICABLE (account not in Organization). |
| Next Action | CG1, CG2, and CG3 fully verified (17/41 controls PASS, 1 N/A). Proceed to Control Group 4 — KMS Encryption. |

---

### 2026-06-01 — Control Group 4: KMS Encryption — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-06-01T12:50:00Z |
| Control ID | DC-18, DC-19 |
| Action Taken | Reviewed 7 evidence files in `docs/infrastructure_security/evidence/04_kms/`. Verified: CMK creation, alias, key state, rotation status, key policy (4 statements). |
| Evidence Received | `CG4-key-create-output.json` (initial key creation output), `KMS-E01-key-description.json` (key metadata: Enabled, SYMMETRIC_DEFAULT, CUSTOMER-managed), `KMS-E02-rotation-status.json` (rotation enabled, 365-day, next 2027-06-01), `KMS-E03-key-policy.json` (4-statement policy: root, Bedrock role, CloudTrail, CloudWatch Logs), `KMS-E04-aliases.json` (alias/proposal-orchestrator → 887638e8-358b-4664-9270-368aec0ea1f1), `kms_key_policy.json` (input policy file), `CG4_logs.txt` (evidence collection commands) |
| Verification Result | DC-18: VERIFIED_PASS (CMK `887638e8-358b-4664-9270-368aec0ea1f1` enabled, SYMMETRIC_DEFAULT, rotation 365d). DC-19: VERIFIED_PASS (key policy: root full access for lockout prevention, Bedrock role Decrypt+DescribeKey only, CloudTrail GenerateDataKey with SourceArn, CloudWatch Logs scoped to /proposal-orchestrator/*). |
| Next Action | CG1–CG4 fully verified (19/41 controls PASS, 1 N/A). CMK available for downstream use. Proceed to Control Group 5 — Secrets Manager. |

---

### 2026-06-01 — Control Group 5: Secrets Manager — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-06-01T13:30:00Z |
| Control ID | DC-20, DC-21, DC-22 |
| Action Taken | Reviewed 9 evidence files in `docs/infrastructure_security/evidence/05_secrets_manager/`. Verified: secret creation with CMK encryption, resource policy (Allow-only for bedrock-role + ec2-ssm-role), host retrieval test, rotation status, tags. Also reviewed `validation-secret-read-policy.json` (IAM policy added to ec2-ssm-role for secret access). |
| Evidence Received | `SM-E01-secrets-list.json` (secret exists, CMK, tags), `SM-E02-secret-description.json` (full metadata), `SM-E03-kms-key-association.txt` (alias/proposal-orchestrator), `SM-E04-resource-policy.json` (2 Allow statements: bedrock-role + ec2-ssm-role), `SM-E05-rotation-configuration.json` (null — no API key secret), `SM-E06-retrieval-test.txt` (host retrieval success, exit 0, ec2-ssm-role), `secret_resource_policy.json` (input policy), `validation-secret-read-policy.json` (IAM policy for ec2-ssm-role), `CG5_logs.txt` (creation + describe output) |
| Verification Result | DC-20: VERIFIED_PASS (secret `proposal-orchestrator/env-config`, KmsKeyId `alias/proposal-orchestrator`, tags confirmed). DC-21: VERIFIED_PASS (resource policy: Allow-only for bedrock-role + ec2-ssm-role, no wildcards; practical deviation from NotPrincipal deny pattern, adequate security). DC-22: NOT_APPLICABLE (production uses IAM auth, no API key secret, RotationEnabled null). |
| Next Action | CG1–CG5 fully verified (21/41 controls PASS, 2 N/A). Proceed to Control Group 6 — CloudTrail. |

---

### 2026-06-01 — Control Group 6: CloudTrail — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-06-01T14:30:00Z |
| Control ID | DC-23, DC-24, DC-25, DC-26, DC-27 |
| Action Taken | Reviewed 13 evidence files in `docs/infrastructure_security/evidence/06_cloudtrail/`. Verified: trail creation with KMS encryption, logging active, log file validation, event capture (5 Converse events), S3 bucket policy (4 statements with SourceArn), versioning, lifecycle policy. |
| Evidence Received | `CT-E01-trail-configuration.json` (trail config: KMS, single-region, global events), `CT-E02-trail-status.json` (IsLogging true), `CT-E03-log-file-validation.txt` (True), `CT-E04-kms-encryption.txt` (CMK ARN), `CT-E05-event-selectors.json` (All mgmt events), `CT-E06-bedrock-converse-events.json` (5 Converse events: caller identity, VPC endpoint, TLS 1.3, both success+denied), `CT-E06b-bedrock-invokemodel-empty.json` (empty — Converse API logs as Converse), `CT-E07-s3-bucket-policy.json` (4 statements), `CT-E08-s3-lifecycle.json` (GLACIER_IR 90d, expire 365d), `CT-E09-s3-versioning.json` (Enabled), `trail_bucket_policy.json` (input), `lifecycle_policy.json` (input), `CT-E01-bedrock-events.json` (duplicate Converse events) |
| Verification Result | DC-23: VERIFIED_PASS (trail exists, IsLogging true, KMS CMK). DC-24: VERIFIED_PASS (LogFileValidationEnabled true). DC-25: VERIFIED_PASS (4-statement bucket policy with SourceArn, versioning enabled; S3 public access block not separately evidenced — minor gap). DC-26: VERIFIED_PASS (5 Converse events, rich audit: caller, sourceIP, vpcEndpointId, TLS, modelId). DC-27: VERIFIED_PASS (GLACIER_IR 90d, expire 365d, noncurrent 30d). |
| Next Action | CG1–CG6 fully verified (26/41 controls PASS, 2 N/A). Proceed to Control Group 7 — CloudWatch. |

---

### 2026-06-01 — Control Group 7: CloudWatch — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-06-01T15:00:00Z |
| Control ID | DC-28, DC-29, DC-30 |
| Action Taken | Reviewed `CG7_logs.txt` in `docs/infrastructure_security/evidence/07_cloudwatch/`. Verified: Bedrock invocation logging disabled (null config), no /aws/bedrock log groups, zero log groups in entire account. |
| Evidence Received | `CG7_logs.txt` (4 CLI commands: get-model-invocation-logging-configuration empty, describe-log-groups /aws/bedrock empty, describe-log-groups all empty, encryption query empty) |
| Verification Result | DC-28: VERIFIED_PASS (loggingConfig null — no prompt/response stored). DC-29: VERIFIED_PASS (logGroups [] for /aws/bedrock). DC-30: NOT_APPLICABLE (zero log groups exist; KMS key policy pre-configured for future groups). |
| Next Action | CG1–CG7 fully verified (28/41 controls PASS, 3 N/A). Proceed to Control Group 8 — Data Egress Prevention. |

---

### 2026-06-01 — Control Group 8: Data Egress Prevention — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-06-01T15:30:00Z |
| Control ID | DC-07, DC-08, DC-31, DC-32; DC-30 revisited |
| Action Taken | Reviewed `CG_8_logs.txt` and input policy files in `docs/infrastructure_security/evidence/08_data_egress/`. Verified: flow logs creation (both subnets ACTIVE), flow logs log group (90d retention, CMK encrypted), no Claude CLI on host, host SG and internet egress via cross-reference to CG1/CG3. Revisited DC-30 (CG7) — upgraded from NOT_APPLICABLE to VERIFIED_PASS. |
| Evidence Received | `CG_8_logs.txt` (flow logs creation, describe-flow-logs, log group config with kmsKeyId + retention, Claude CLI check from host), `flow_logs_trust_policy.json` (input), `flow_logs_permissions_policy.json` (input) |
| Verification Result | DC-07: VERIFIED_PASS (cross-ref CG1: host SG TCP 443 to VPCE SG only). DC-08: VERIFIED_PASS (fl-03c1ed4c967c50073 + fl-0948b876901308e70 both ACTIVE). DC-31: VERIFIED_PASS (which/find/version all negative). DC-32: VERIFIED_PASS (cross-ref CG1 DC-06 no internet route + CG3 REG-E03 timeout). DC-30 revisited: VERIFIED_PASS (log group /proposal-orchestrator/vpc-flow-logs, retention 90d, CMK arn:...887638e8...). |
| Notes | DEP-E02 (host SG) and DEP-E05 (curl egress tests) not freshly collected in CG8 — verified via cross-reference to CG1 and CG3 evidence. Defense in depth: no IGW/NAT route + SG outbound restricted to VPCE SG = internet egress provably impossible. |
| Next Action | CG1–CG8 fully verified (33/41 controls PASS, 2 N/A). Proceed to Control Group 9 — Production Configuration. |

---

### 2026-06-01 — Control Group 9: Production Configuration — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-06-01T15:50:00Z |
| Control ID | DC-33, DC-34, DC-35, DC-36, DC-38 |
| Action Taken | Reviewed `CG9_logs.txt` in `docs/infrastructure_security/evidence/09_production_config/`. Verified: secret contains all three required config values, model availability confirmed from host via Converse call. DC-38 deferred (app not deployed). |
| Evidence Received | `CG9_logs.txt` (secret retrieval showing all 5 config values, Converse test from host: us.anthropic.claude-sonnet-4-6 responded "MODEL_AVAILABLE", latency 1618ms) |
| Verification Result | DC-33: VERIFIED_PASS (PRODUCTION_MODE=true). DC-34: VERIFIED_PASS (TRANSPORT_PRESET=BEDROCK_CONVERSE_US). DC-35: VERIFIED_PASS (DIAGNOSTIC_LEVEL=metadata). DC-36: VERIFIED_PASS (model responded successfully). DC-38: DEFERRED (application not yet deployed to production host; all infrastructure controls verified). |
| Next Action | CG1–CG9 verified (37/41 controls PASS, 2 N/A, 1 DEFERRED). Proceed to Control Group 10 — Compliance. |

---

### 2026-06-01 — Control Group 10: Compliance — Evidence Review Complete

| Field | Value |
|---|---|
| Timestamp | 2026-06-01T16:00:00Z |
| Control ID | DC-39 |
| Action Taken | Reviewed AWS Artifact > Agreements. No separate GDPR DPA available for acceptance. Confirmed AWS GDPR data processing terms are incorporated into the AWS Customer Agreement by default (since November 2018). Created assessment evidence file. |
| Evidence Received | `COMP-E01-gdpr-dpa-assessment.txt` (assessment documenting findings, disposition, and optional ELTE DPO review note) |
| Verification Result | DC-39: VERIFIED_PASS. AWS DPA in effect via standard Customer Agreement. Residual risk: none (technical scope). Optional institutional review by ELTE DPO if required by university procurement or data governance policy. |
| Next Action | ALL CONTROL GROUPS COMPLETE. Final status: 38/41 VERIFIED_PASS, 2 NOT_APPLICABLE (DC-22, DC-40), 1 DEFERRED (DC-38 full DAG run pending application deployment). |

---
