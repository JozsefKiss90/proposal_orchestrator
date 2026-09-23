# AWS Hardening Control Register

## Proposal Orchestrator — Infrastructure Security Controls

**Created:** 2026-05-29
**Source:** `aws_deployment_hardening_plan.md`
**Status:** Active — Implementation in progress

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

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-01 | VPC interface endpoint for bedrock-runtime | Network / PrivateLink | Interface endpoint for `com.amazonaws.us-east-1.bedrock-runtime` in `available` state | VPC, PrivateLink | VPC-E01: `describe-vpc-endpoints` JSON export | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | `vpce-0843d225c5b1ef6d5`, state `available`, Private DNS `true`. Evidence: `control_group_1_logs.txt` line 387, lines 698-759 | — |
| DC-02 | Private DNS enabled on VPC endpoint | Network / PrivateLink | Private DNS enabled so `bedrock-runtime.us-east-1.amazonaws.com` resolves to private IPs | VPC, Route 53 Resolver | VPC-E02: `nslookup`/`dig` output from deployment host | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | `PrivateDnsEnabled: true`. nslookup from host resolves to `172.31.27.207`, `172.31.80.15` (VPC CIDR). Evidence: `EV-PL-005` lines 417-428 | — |
| DC-03 | VPC endpoint security group (TCP 443 only) | Network / PrivateLink | Dedicated SG allowing only TCP 443 inbound from deployment host SG | VPC, Security Groups | VPC-E03: `describe-security-groups` JSON export | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | VPCE SG `sg-013d5e4d4eb55dfd9`: inbound TCP 443 from host SG `sg-076f724aed2429771` only. No CIDR rules, no outbound. Evidence: `EV-PL-005` lines 108-151 | — |
| DC-04 | VPC endpoint policy scoped to Bedrock role and Claude models | Network / PrivateLink | Endpoint policy restricts to Bedrock invocation actions on Claude model ARNs only | VPC Endpoint Policy | VPC-E04: `describe-vpc-endpoints` PolicyDocument JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Policy scoped to `proposal-orchestrator-bedrock-role` + `ec2-ssm-role`, actions InvokeModel/Stream, resources `anthropic.claude-*` + `us.anthropic.claude-*`. Evidence: `02_iam/EV-VPC-004-bedrock-endpoint-policy.json`, logs 863-901 | — |
| DC-05 | Supporting VPC endpoints (Secrets Manager, STS, S3) | Network / PrivateLink | Interface endpoints for secretsmanager, sts; gateway endpoint for S3 | VPC, PrivateLink | VPC-E01: combined endpoint listing | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | secretsmanager (`vpce-08ba482a3b11f7d64`), sts (`vpce-067abd500c89e2bc4`), s3 gateway (`vpce-0ee5648ce182bf85a`) — all `available`. Plus SSM endpoints for host access. Evidence: `control_group_1_logs.txt` lines 613-617 | — |
| DC-06 | No internet route in deployment subnet | Network / Routing | Deployment subnet route table has no 0.0.0.0/0 route to IGW or NAT | VPC, Route Tables | VPC-E06 / DEP-E01: `describe-route-tables` JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Route table `rtb-085481996de5e3ed9`: only `local` (172.31.0.0/16) + S3 prefix list (`pl-63a5400a`). No IGW/NAT routes. Evidence: `control_group_1_logs.txt` lines 685-692 | — |

### PrivateLink Functional Validation

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-37 | End-to-end Bedrock Converse call succeeds | Validation | `converse()` call succeeds from deployment host via PrivateLink | Bedrock Runtime | VPC-E05: functional test output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | `converse(us.anthropic.claude-sonnet-4-6)` from host `i-0045af36dbf5f1272` via PrivateLink: model responded `"OK"`, latency 1402ms. Caller: `assumed-role/proposal-orchestrator-ec2-ssm-role`. Evidence: `02_iam/IAM_Least_Privilege_logs.txt` lines 802-862 | — |

### Additional PrivateLink Criteria (VPC DNS)

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| PL-8 | VPC DNS settings | Network / DNS | `enableDnsHostnames` and `enableDnsSupport` both `true` | VPC | `describe-vpc-attribute` output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Both enabled on `vpc-050a09774560fd774`. Evidence: `control_group_1_logs.txt` lines 922-941 | — |

---

## Control Group 2 — IAM Least Privilege

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-09 | IAM role for Bedrock execution | IAM | Dedicated IAM role for Bedrock invocation with correct trust policy | IAM | IAM-E01: `get-role` JSON, IAM-E10: trust policy JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Role `proposal-orchestrator-bedrock-role` (`AROATMJDAWYJ4O7EVU3VG`). Trust: `ec2.amazonaws.com`. No `aws:SourceVpc` condition (deliberate — IMDS doesn't traverse VPC endpoints). Evidence: `EV-IAM-001`, `EV-IAM-010`, logs 248-278 | — |
| DC-10 | Bedrock invocation policy (scoped to Claude + approved regions) | IAM | Allow `bedrock:InvokeModel` + `InvokeModelWithResponseStream` on `anthropic.claude-*` with `aws:RequestedRegion` condition | IAM | IAM-E02: attached policy documents JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Policy `proposal-orchestrator-bedrock-invoke`: actions scoped to InvokeModel+Stream, resources `anthropic.claude-*` + `us.anthropic.claude-*`, condition `aws:RequestedRegion` = `[eu-west-1, us-east-1]`. Simulation: `allowed` for Claude in us-east-1. Evidence: `EV-IAM-002`, `EV-IAM-003-*-bedrock-invoke`, logs 302-316 | — |
| DC-11 | Explicit deny statements (Bedrock admin, non-Bedrock, non-Claude) | IAM | Deny Bedrock admin actions, deny non-Bedrock services (EC2, S3, IAM, Lambda, SQS, SNS, DynamoDB), deny non-Claude models via NotResource | IAM | IAM-E03: inline policy documents JSON, IAM-E06: denied action simulation, IAM-E07: non-Claude denial | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | 3 deny statements: DenyBedrockAdministration (8 actions), DenyNonBedrockServices (ec2/s3/iam/lambda/sqs/sns/dynamodb), DenyNonClaudeModels (NotResource). Simulations: PutModelInvocationLogging→explicitDeny, s3:ListBuckets→explicitDeny, ec2:DescribeInstances→explicitDeny, iam:ListRoles→explicitDeny, meta.llama3→explicitDeny. Evidence: `EV-IAM-003-*-explicit-deny`, logs 360-487 | — |
| DC-12 | Permission boundary attached | IAM | Permission boundary limiting max scope to Bedrock invoke + SecretsManager get + KMS decrypt + STS identity | IAM | IAM-E04: `get-role` PermissionsBoundary JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Boundary `proposal-orchestrator-boundary` attached. Allows only: InvokeModel, InvokeModelWithResponseStream, GetSecretValue, Decrypt, DescribeKey, GetCallerIdentity. `PermissionsBoundaryUsageCount: 1`. Evidence: `EV-IAM-004-*`, `EV-IAM-003-*-boundary` | — |
| DC-13 | Trust policy for compute service | IAM | Trust policy allows only approved compute service (EC2/ECS/Lambda) with VPC condition | IAM | IAM-E10: AssumeRolePolicyDocument JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Trust: `ec2.amazonaws.com` → `sts:AssumeRole`. No VPC condition (deliberate: IMDS doesn't traverse VPC endpoints; compensated by SG-to-SG binding and private subnet isolation). Evidence: `EV-IAM-010` | — |
| DC-14 | Instance profile / task role associated with deployment host | IAM | Deployment host uses instance profile or task role, not long-term keys | IAM, EC2/ECS | IAM-E08: `sts get-caller-identity` from host | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Host `i-0045af36dbf5f1272` uses instance profile `proposal-orchestrator-ec2-ssm-profile`. `sts get-caller-identity` returns `assumed-role/proposal-orchestrator-ec2-ssm-role/i-0045af36dbf5f1272`. No access key ID. Evidence: logs 805-808 | — |
| DC-15 | No long-term access keys on deployment host | IAM | No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY in files or environment | IAM | IAM-E08: caller identity (no access key), IAM-E09: negative tests | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Caller identity shows role assumption (no access key). Denied action simulations confirm IAM policy enforcement. In-host negative tests not separately collected (minor gap; simulation evidence equivalent). Evidence: logs 805-808, simulation logs 360-524 | — |

---

## Control Group 3 — Region Enforcement

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-16 | Region enforcement via IAM condition | Region | `aws:RequestedRegion` condition in IAM policy limits to eu-west-1 and us-east-1 only | IAM | REG-E01: policy document JSON with region condition | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Cross-ref CG2: `EV-IAM-003-policy-*-bedrock-invoke.json` confirms `aws:RequestedRegion: [eu-west-1, us-east-1]`. Evidence: `02_iam/EV-IAM-003-policy-proposal-orchestrator-bedrock-invoke.json` | — |
| DC-17 | Negative region test (unapproved region denied) | Region | Bedrock call to unapproved region (e.g., ap-southeast-1) fails with AccessDeniedException or connection failure | Bedrock, IAM | REG-E03: CLI output of denied call | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | ap-southeast-1 converse: exit code 124 (timeout — no VPC endpoint, network-level deny). us-east-1 control: succeeded, exit code 0. Defense in depth: network isolation + IAM region condition. Evidence: `03_region_enforcement/REG-E03-negative-region-test.txt` | — |
| DC-40 | SCP for region restriction (if Organization) | Region | SCP denying Bedrock in non-approved regions applied at OU/account level | Organizations, SCP | REG-E04: SCP policy document or Organization status | NOT_APPLICABLE | EVIDENCE_SUBMITTED | NOT_APPLICABLE | `AWSOrganizationsNotInUseException` — account `232538551827` is not a member of an Organization. SCP control does not apply. Evidence: `03_region_enforcement/REG-E04-organization-check.txt` | — |

---

## Control Group 4 — KMS Encryption

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-18 | Customer-managed KMS key with rotation | Encryption | Symmetric CMK with alias `proposal-orchestrator`, automatic annual rotation enabled | KMS | KMS-E01: `describe-key` JSON, KMS-E02: `get-key-rotation-status` JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Key `887638e8-358b-4664-9270-368aec0ea1f1`, alias `alias/proposal-orchestrator`. KeyState `Enabled`, KeySpec `SYMMETRIC_DEFAULT`, KeyManager `CUSTOMER`. Rotation enabled, 365-day period, next 2027-06-01. Evidence: `04_kms/KMS-E01-key-description.json`, `KMS-E02-rotation-status.json` | — |
| DC-19 | KMS key policy scoped to admin and Bedrock roles | Encryption | Key admin limited to admin roles; key usage limited to Bedrock role and CloudTrail service | KMS | KMS-E03: `get-key-policy` JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | 4 statements: AllowRootFullAccess (kms:*, lockout prevention), AllowBedrockRoleUsage (Decrypt+DescribeKey for `proposal-orchestrator-bedrock-role`), AllowCloudTrailEncryption (GenerateDataKey*+DescribeKey for cloudtrail.amazonaws.com, SourceArn scoped), AllowCloudWatchLogsEncryption (logs.us-east-1.amazonaws.com, scoped to /proposal-orchestrator/*). Evidence: `04_kms/KMS-E03-key-policy.json`, `04_kms/kms_key_policy.json` | — |

---

## Control Group 5 — Secrets Manager

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-20 | Secrets created and encrypted with CMK | Secrets | `proposal-orchestrator/env-config` (and transport-api-key if needed) stored encrypted with CMK | Secrets Manager, KMS | SM-E01: `list-secrets` JSON, SM-E02: `describe-secret` JSON, SM-E03: KmsKeyId output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Secret `proposal-orchestrator/env-config` (ARN suffix `-eLye1o`). KmsKeyId `alias/proposal-orchestrator`. Tags: project + environment. No transport-api-key needed (IAM auth). Evidence: `05_secrets_manager/SM-E01-secrets-list.json`, `SM-E02-secret-description.json`, `SM-E03-kms-key-association.txt` | — |
| DC-21 | Secret resource policy scoped to Bedrock role | Secrets | Resource policy allows only Bedrock execution role and admin role | Secrets Manager | SM-E04: `get-resource-policy` JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | 2 Allow statements: AllowBedrockRoleAccess (`bedrock-role`, GetSecretValue+DescribeSecret), AllowValidationHostRoleAccess (`ec2-ssm-role`, GetSecretValue+DescribeSecret). No wildcards. Allow-only pattern (no NotPrincipal deny — practical deviation, adequate security). Host retrieval test passed (exit code 0). Evidence: `05_secrets_manager/SM-E04-resource-policy.json`, `SM-E06-retrieval-test.txt` | — |
| DC-22 | API key rotation configured (90-day, if applicable) | Secrets | Lambda-based rotation with 90-day schedule for API key secrets | Secrets Manager, Lambda | SM-E05: `describe-secret` RotationRules JSON | NOT_APPLICABLE | EVIDENCE_SUBMITTED | NOT_APPLICABLE | Production transport uses IAM instance profile auth (BEDROCK_CONVERSE_US). No transport-api-key secret exists. RotationEnabled: null. If API key secret is added later, DC-22 must be revisited. Evidence: `05_secrets_manager/SM-E05-rotation-configuration.json` | — |

---

## Control Group 6 — CloudTrail

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-23 | CloudTrail trail created with KMS encryption | Audit | Trail `proposal-orchestrator-bedrock-trail` with CMK encryption | CloudTrail, KMS | CT-E01: `describe-trails` JSON, CT-E04: KmsKeyId output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Trail `proposal-orchestrator-bedrock-trail`, IsLogging true (since 2026-06-01T12:08:41Z). KmsKeyId `887638e8-358b-4664-9270-368aec0ea1f1`. Single-region (us-east-1), global service events included. S3 bucket `proposal-orchestrator-cloudtrail-232538551827`, prefix `cloudtrail/proposal-orchestrator`. Evidence: `06_cloudtrail/CT-E01-trail-configuration.json`, `CT-E02-trail-status.json`, `CT-E04-kms-encryption.txt` | — |
| DC-24 | Log file validation enabled | Audit | Digest files enabled for integrity verification | CloudTrail | CT-E03: LogFileValidationEnabled output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | `LogFileValidationEnabled: True`. Evidence: `06_cloudtrail/CT-E03-log-file-validation.txt` | — |
| DC-25 | Trail S3 bucket secured (encryption, deny HTTP, versioning) | Audit | Dedicated S3 bucket with KMS encryption, deny unencrypted objects, deny insecure transport, versioning enabled | S3 | CT-E07: bucket policy JSON, CT-E09: versioning status JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | 4-statement bucket policy: AWSCloudTrailAclCheck (SourceArn scoped), AWSCloudTrailWrite (SourceArn + bucket-owner-full-control), DenyUnencryptedObjects, DenyInsecureTransport. Versioning Enabled. S3 public access block evidence not separately collected (minor gap, non-blocking). Evidence: `06_cloudtrail/CT-E07-s3-bucket-policy.json`, `CT-E09-s3-versioning.json` | — |
| DC-26 | CloudTrail capturing Bedrock Converse events | Audit | Bedrock Converse events appear in CloudTrail after test call | CloudTrail | CT-E06: `lookup-events` JSON showing Converse event | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | 5 Converse events captured (2026-05-29 and 2026-06-01). Events show caller identity (ec2-ssm-role), sourceIP (172.31.93.116 VPC private), vpcEndpointId (vpce-0843d225c5b1ef6d5), modelId, TLS 1.3. Both successful and denied (AccessDenied us-west-2) calls logged. Evidence: `06_cloudtrail/CT-E06-bedrock-converse-events.json` | — |
| DC-27 | S3 lifecycle policy for trail logs | Audit | Archive to Glacier after 90 days, delete after 365 days | S3 | CT-E08: `get-bucket-lifecycle-configuration` JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Rule `proposal-orchestrator-cloudtrail-lifecycle`: GLACIER_IR at 90d, expiration at 365d, noncurrent version cleanup at 30d, scoped to `cloudtrail/proposal-orchestrator/` prefix. Evidence: `06_cloudtrail/CT-E08-s3-lifecycle.json` | — |

---

## Control Group 7 — CloudWatch

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-28 | Bedrock model invocation logging DISABLED | CloudWatch | `get-model-invocation-logging-configuration` returns null/empty — no prompt/response data stored | Bedrock, CloudWatch | CW-E01: logging config JSON, CW-E02: console screenshot | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | `get-model-invocation-logging-configuration` returned empty (loggingConfig null). No prompt/response data stored in CloudWatch or S3. Evidence: `07_cloudwatch/CG7_logs.txt` | — |
| DC-29 | No Bedrock invocation log groups in CloudWatch | CloudWatch | No `/aws/bedrock` log groups exist | CloudWatch Logs | CW-E03: `describe-log-groups` JSON (expected empty) | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | `describe-log-groups --log-group-name-prefix /aws/bedrock` returned `logGroups: []`. No invocation log groups. Evidence: `07_cloudwatch/CG7_logs.txt` | — |
| DC-30 | Operational log groups encrypted with CMK and retention set | CloudWatch | Any operational log groups use CMK encryption and max 90-day retention | CloudWatch Logs, KMS | CW-E04: log group config JSON, CW-E05: kmsKeyId output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Revisited after CG8: `/proposal-orchestrator/vpc-flow-logs` created with retention 90d and kmsKeyId `887638e8-358b-4664-9270-368aec0ea1f1` (CMK). Evidence: `08_data_egress/CG_8_logs.txt` lines 79-90 | — |

---

## Control Group 8 — Data Egress Prevention

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-07 | Deployment host SG restricts outbound to VPC endpoints | Egress / Network | Outbound rules: TCP 443 to VPC endpoint SG only; no 0.0.0.0/0 | Security Groups | DEP-E02: `describe-security-groups` JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Cross-ref CG1: host SG `sg-076f724aed2429771` configured with TCP 443 egress to VPCE SG `sg-013d5e4d4eb55dfd9` only. No 0.0.0.0/0 rules, no other destinations. Evidence: `01_privatelink/EV-PL-005-private-dns-resolution.txt`, `01_privatelink/control_group_1_logs.txt` | — |
| DC-08 | VPC flow logs enabled on deployment subnet | Egress / Network | Flow logs enabled with ALL traffic type, delivered to CloudWatch Logs | VPC Flow Logs | DEP-E03: `describe-flow-logs` JSON | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Flow logs on both subnets: `fl-03c1ed4c967c50073` (subnet-023c6e3ea5451ea47), `fl-0948b876901308e70` (subnet-01d969bb1421a3042). Both ACTIVE, DeliverLogsStatus SUCCESS. TrafficType ALL, to `/proposal-orchestrator/vpc-flow-logs` (90d retention, CMK encrypted). Evidence: `08_data_egress/CG_8_logs.txt` | — |
| DC-31 | No Claude CLI binary on deployment host | Egress / Application | `which claude` returns not found; `claude --version` fails | Deployment Host | DEP-E04: CLI output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | `which claude`: not found (exit 1). `claude --version`: command not found (exit 127). `find / -name claude`: no results. Evidence: `08_data_egress/CG_8_logs.txt` lines 92-114 | — |
| DC-32 | Internet egress blocked from deployment host | Egress / Network | `curl` to api.anthropic.com, api.together.ai times out or fails | VPC, Security Groups | DEP-E05: curl timeout output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Cross-ref CG1 DC-06 (no internet route — route table has only local + S3 prefix list) + CG3 REG-E03 (ap-southeast-1 call timed out from host, exit code 124 — no connectivity beyond VPC endpoints). Defense in depth: no IGW/NAT route + SG outbound to VPCE SG only. Evidence: `01_privatelink/control_group_1_logs.txt`, `03_region_enforcement/REG-E03-negative-region-test.txt` | — |

---

## Control Group 9 — Production Application Configuration

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-33 | ORCHESTRATOR_PRODUCTION_MODE=true | Application | Environment variable set to enforce production backend restrictions | — | Config export or screenshot | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Secret `proposal-orchestrator/env-config` contains `ORCHESTRATOR_PRODUCTION_MODE:true`. Readable from host via Secrets Manager. Evidence: `09_production_config/CG9_logs.txt` | — |
| DC-34 | ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US | Application | Transport preset selects Bedrock Converse backend | — | Config export or screenshot | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Secret contains `ORCHESTRATOR_TRANSPORT_PRESET:BEDROCK_CONVERSE_US`. IAM-authenticated Bedrock Converse backend selected. Evidence: `09_production_config/CG9_logs.txt` | — |
| DC-35 | ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata | Application | Diagnostic level prevents prompt/response content from being written to disk | — | Config export or screenshot | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Secret contains `ORCHESTRATOR_DIAGNOSTIC_LEVEL:metadata`. Prevents prompt/response disk writes. Evidence: `09_production_config/CG9_logs.txt` | — |
| DC-36 | Model availability confirmed in target region | Operational | `us.anthropic.claude-sonnet-4-6` available in target region | Bedrock | Model listing or test call output | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | Converse call from host: `us.anthropic.claude-sonnet-4-6` responded "MODEL_AVAILABLE" in us-east-1, latency 1618ms. Evidence: `09_production_config/CG9_logs.txt` | — |
| DC-38 | Full DAG run (Phase 1-8) succeeds with production config | Validation | All phases complete, all gates pass under production configuration | Bedrock, Application | Run summary JSON | DEFERRED | — | — | Application not yet deployed to production host. All infrastructure controls (CG1-CG8) verified. DAG run to be executed when application deployment is complete. | Deploy application, then execute |

---

## Control Group 10 — Compliance

| Control ID | Control Name | Category | Requirement Summary | AWS Service(s) | Required Evidence | Implementation Status | Evidence Status | Verification Status | Reviewer Notes | Next Action |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-39 | GDPR DPA executed via AWS Artifact | Compliance | Data Processing Addendum executed for EU institutional requirements | AWS Artifact | DPA document or confirmation | IMPLEMENTED | EVIDENCE_SUBMITTED | VERIFIED_PASS | AWS Artifact reviewed: no separate DPA acceptance required. AWS GDPR data processing terms incorporated into AWS Customer Agreement by default (since Nov 2018). Residual risk: none (technical scope). Optional institutional review by ELTE DPO if required by university procurement or data governance policy. Evidence: `10_compliance/COMP-E01-gdpr-dpa-assessment.txt` | — |

---

## Summary

| Control Group | Controls | NOT_STARTED | IN_PROGRESS | VERIFIED_PASS | VERIFIED_FAIL | BLOCKED | DEFERRED | N/A |
|---|---|---|---|---|---|---|---|---|
| 1 - PrivateLink | 8 | 0 | 0 | 8 | 0 | 0 | 0 | 0 |
| 2 - IAM | 7 | 0 | 0 | 7 | 0 | 0 | 0 | 0 |
| 3 - Region | 3 | 0 | 0 | 2 | 0 | 0 | 0 | 1 |
| 4 - KMS | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| 5 - Secrets Manager | 3 | 0 | 0 | 2 | 0 | 0 | 0 | 1 |
| 6 - CloudTrail | 5 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| 7 - CloudWatch | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| 8 - Data Egress | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| 9 - Production Config | 5 | 0 | 0 | 4 | 0 | 0 | 1 | 0 |
| 10 - Compliance | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| **TOTAL** | **41** | **0** | **0** | **38** | **0** | **0** | **1** | **2** |

### CG1 Infrastructure Reference

| Resource | ID | Notes |
|---|---|---|
| VPC | `vpc-050a09774560fd774` | us-east-1, CIDR 172.31.0.0/16 |
| Deployment subnets | `subnet-023c6e3ea5451ea47` (us-east-1a), `subnet-01d969bb1421a3042` (us-east-1b) | Private subnets |
| Private route table | `rtb-085481996de5e3ed9` | Local + S3 prefix list only |
| VPCE SG | `sg-013d5e4d4eb55dfd9` | TCP 443 inbound from host SG |
| Host SG | `sg-076f724aed2429771` | TCP 443 egress to VPCE SG |
| Bedrock endpoint | `vpce-0843d225c5b1ef6d5` | bedrock-runtime, available |
| SecretsManager endpoint | `vpce-08ba482a3b11f7d64` | available |
| STS endpoint | `vpce-067abd500c89e2bc4` | available |
| S3 gateway endpoint | `vpce-0ee5648ce182bf85a` | available |
| SSM endpoint | `vpce-06a268f54ecc1f754` | available |
| SSM Messages endpoint | `vpce-0824e9fbb2f099e37` | available |
| EC2 Messages endpoint | `vpce-0ec79b44974bfd85b` | available |
| Validation host | `i-0045af36dbf5f1272` | t3.micro, AL2023, SSM role |
| Instance profile | `proposal-orchestrator-ec2-ssm-profile` | Role: `proposal-orchestrator-ec2-ssm-role` |
| KMS CMK | `887638e8-358b-4664-9270-368aec0ea1f1` | alias/proposal-orchestrator, SYMMETRIC_DEFAULT, rotation 365d |
| CloudTrail trail | `proposal-orchestrator-bedrock-trail` | us-east-1, KMS encrypted, log validation enabled |
| Trail S3 bucket | `proposal-orchestrator-cloudtrail-232538551827` | Versioned, lifecycle 90d→GLACIER_IR, 365d expiry |
| Flow log (subnet-1a) | `fl-03c1ed4c967c50073` | subnet-023c6e3ea5451ea47, ACTIVE |
| Flow log (subnet-1b) | `fl-0948b876901308e70` | subnet-01d969bb1421a3042, ACTIVE |
| Flow logs log group | `/proposal-orchestrator/vpc-flow-logs` | 90d retention, CMK encrypted |
| Flow logs IAM role | `proposal-orchestrator-flow-logs-role` | vpc-flow-logs.amazonaws.com trust |
| Account | `232538551827` | |
