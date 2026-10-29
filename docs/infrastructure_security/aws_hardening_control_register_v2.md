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
| DC-03 | VPC endpoint security group (TCP 443 only) | Dedicated SG allowing only TCP 443 inbound from the host SG; no other rules apart from the loopback placeholder (`-1` to `127.0.0.1/32`) that replaces AWS's default egress (R4-D1); attached to every interface endpoint | R4 (SG), R11 (attached) | IN_PROGRESS | `evidence_v2/R4/` (`VERIFICATION.md`; `R4_07_security-groups.json`, `R4_07_security-group-rules.json`) | SG half verified 2026-10-24: the endpoint SG (`EndpointSecurityGroupId` in `R4_outputs.json`), one ingress `tcp` 443 from the host SG, one egress entry = the placeholder, nothing else; the VPC's default SG emptied (`R4_08_default-sg-after.json`, R4-D2). Wording amended for the placeholder. Attachment to the six interface endpoints is R11. |
| DC-04 | VPC endpoint policy scoped to runtime role and Claude models | Bedrock endpoint policy restricts to invocation actions on the OD7 model resources, for the runtime role | R11 | NOT_STARTED | — | — |
| DC-05 | Supporting VPC endpoints | Interface endpoints for secretsmanager, sts, ssm, ssmmessages, ec2messages; gateway endpoint for S3 | R4 (S3), R11 (interface) | IN_PROGRESS | `evidence_v2/R4/` (`VERIFICATION.md`; `R4_07_vpc-endpoint.json`, `R4_07_route-table.json`) | S3 half verified 2026-10-24: the gateway endpoint (`S3GatewayEndpointId` in `R4_outputs.json`), `available`, on the private route table, policy read-only on the deploy bucket with `aws:ResourceAccount` and `aws:PrincipalAccount` (F7; R4-D3). The five interface endpoints are R11. |
| DC-06 | No internet route in deployment subnet | Deployment subnet route table has no `0.0.0.0/0` route and no IGW or NAT target | R4 | VERIFIED_PASS | `evidence_v2/R4/` (`VERIFICATION.md`; `R4_07_route-table.json`, `R4_07_internet-gateways.json`, `R4_07_nat-gateways.json`) | Verified 2026-10-24: the private route table (`PrivateRouteTableId` in `R4_outputs.json`) holds exactly two routes, `local` and the S3 prefix list → the S3 gateway endpoint; no Internet Gateway attached to the VPC, no NAT Gateway in it. The template guard refuses any `AWS::EC2::Route` (R4-D4). R12b re-evidences. |
| DC-37 | End-to-end Bedrock Converse call succeeds | `converse()` call succeeds from the host via PrivateLink, attributed to the hardened runtime role | R11 | NOT_STARTED | — | — |
| PL-8 | VPC DNS settings | `enableDnsHostnames` and `enableDnsSupport` both `true` | R4 | VERIFIED_PASS | `evidence_v2/R4/` (`VERIFICATION.md`; `R4_07_vpc-dns-support.json`, `R4_07_vpc-dns-hostnames.json`) | Verified 2026-10-24 on the dedicated VPC (`VpcId` in `R4_outputs.json`): both attributes `true`. R12b re-evidences. |

---

## Control Group 2 — IAM Least Privilege

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-09 | IAM role for Bedrock execution | Dedicated runtime role with correct trust policy; it is the role the host's instance profile uses (F1) | R5 (role, profile), R11 (host) | IN_PROGRESS | `evidence_v2/R5/` (`VERIFICATION.md`; `R5_08_runtime-role.json`, `R5_08_instance-profile.json`) | Role and profile verified 2026-10-25: `proposal-orchestrator-runtime-role` (`RuntimeRoleArn` in `R5_outputs.json`) carries the boundary and the explicit deny, and `proposal-orchestrator-runtime-profile` holds exactly that role. That the host uses the profile is shown in R11 (DC-14), R5-D9. |
| DC-10 | Bedrock invocation policy | Invoke scoped to the OD7 profiles and the foundation models in every region they route to (F2) | R5 | VERIFIED_PASS | `evidence_v2/R5/` (`VERIFICATION.md`; `R5_08_policy-version-proposal-orchestrator-bedrock-invoke.json`, `R5_09_allow-profiles.json`, `R5_09_allow-fm-*.json`) | Verified 2026-10-25: the two OD7 profiles (requested in eu-north-1) and the twelve routed foundation models (only through those profiles, in the routed Regions), from parameters; simulation allows all fourteen. Live routed call: R11 (F-R5-2 Inferred). |
| DC-11 | Explicit deny statements | Deny Bedrock admin actions, non-Bedrock services outside the policy, and non-Claude models | R5 | VERIFIED_PASS | `evidence_v2/R5/` (`VERIFICATION.md`; `R5_08_policy-version-proposal-orchestrator-explicit-deny.json`, `R5_09_deny-*.json`, `R5_12_deny-*.json`) | Verified 2026-10-25 on the runtime role: Bedrock administration (incl. invocation-logging changes), iam/ec2/lambda/sqs/sns/dynamodb, everything but `eu.` Claude profiles and Claude models (`global.` denied, OD7-global), S3 outside the deploy bucket's `bundles/` (R5-D2); simulation shows `explicitDeny` from this policy in each case. |
| DC-12 | Permission boundary attached | Boundary limiting the runtime role to exactly what it needs, attached to the runtime role | R5 | VERIFIED_PASS | `evidence_v2/R5/` (`VERIFICATION.md`; `R5_08_runtime-role.json`, `R5_08_policy-version-proposal-orchestrator-boundary.json`) | Verified 2026-10-25: `PermissionBoundaryArn` is the runtime role's boundary; it allows only invoke on the OD7 resources, the runtime secret, `kms:Decrypt`/`DescribeKey` (granted by R6's key policy), caller identity, the 25 SSM Agent actions of `AmazonSSMManagedInstanceCore` v2, and read on `bundles/`. Simulation reports `AllowedByPermissionsBoundary` true for the allowed cases. |
| DC-13 | Trust policy for compute service | Trust policy allows only the approved compute service | R5 | VERIFIED_PASS | `evidence_v2/R5/` (`VERIFICATION.md`; `R5_08_runtime-role.json`) | Verified 2026-10-25: one statement, `ec2.amazonaws.com`, `sts:AssumeRole`. (The flow-logs role trusts `vpc-flow-logs.amazonaws.com` only, for this account's flow logs.) |
| DC-14 | Instance profile associated with deployment host | Host uses the instance profile, not long-term keys | R11 | NOT_STARTED | — | — |
| DC-15 | No long-term access keys on deployment host | No long-term key variables in files or environment on the host; in-host negative tests collected | R12b | NOT_STARTED | — | v1 never collected the in-host tests |

---

## Control Group 3 — Region Enforcement

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-16 | Region enforcement via IAM condition | `aws:RequestedRegion` condition limits calls to the OD1 region and the regions the OD7 profiles route to | R5, R12b | IN_PROGRESS | `evidence_v2/R5/` (`VERIFICATION.md`; `R5_08_policy-version-proposal-orchestrator-explicit-deny.json`, `R5_09_deny-unapproved-region.json`) | Condition in place 2026-10-25: the explicit deny refuses invoke when `aws:RequestedRegion` is not one of the six routed Regions (eu-north-1 among them); simulated us-east-1 → `explicitDeny`. Negative test from the host: R12b (DC-17), R5-D9. |
| DC-17 | Negative region test | A Bedrock call to an unapproved region fails | R12b | NOT_STARTED | — | — |
| DC-40 | SCP for region restriction (if Organization) | SCP denying Bedrock in non-approved regions, if the account is in an Organization | R12b | NOT_STARTED | — | Re-assess. R1 step 00: the account is a member of the AWS-managed organization of the new sign-up experience (management account outside this project), with SCPs enabled and managed by AWS |

---

## Control Group 4 — KMS Encryption

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-18 | Customer-managed KMS key with rotation | Symmetric CMK with alias `alias/proposal-orchestrator`, automatic rotation enabled | R6 | VERIFIED_PASS | `evidence_v2/R6/` (`VERIFICATION.md`; `R6_08_describe-key.json`, `R6_08_rotation-status.json`, `R6_08_describe-by-alias.json`, `R6_08_aliases-of-key.json`) | Verified 2026-10-26: customer-managed `SYMMETRIC_DEFAULT` / `ENCRYPT_DECRYPT` single-Region key `4ccc45a1-…` (`KeyArn` in `R6_outputs.json`), enabled, rotation on every 365 days (next 2027-10-26); `alias/proposal-orchestrator` resolves to it. Retained on stack deletion (R6-D5). |
| DC-19 | KMS key policy scoped | Key policy grants the account root, the runtime role, CloudTrail (SourceArn) and CloudWatch Logs (log-group prefix) only | R6 | VERIFIED_PASS | `evidence_v2/R6/` (`VERIFICATION.md`; `R6_08_key-policy.json`, `R6_08_key-grants.json`, `R6_09_deny-kms-identity-grant.json`) | Verified 2026-10-26 at policy level: five statements equal the template — root `kms:*` (IAM delegation, no separate admin statement, R6-D4); the runtime role `kms:Decrypt`/`DescribeKey` only via Secrets Manager or S3 in eu-north-1 (R6-D3), and no identity policy or grant gives it Decrypt separately; CloudTrail `GenerateDataKey*`/`DescribeKey` for `trail/proposal-orchestrator-bedrock-trail` by `aws:SourceArn` (R6-D2; no CloudTrail decrypt, R6-D10); CloudWatch Logs in eu-north-1 for `log-group:/proposal-orchestrator/*`. CloudTrail and CloudWatch Logs grants exercised in R7 (2026-10-26: trail created and delivering SSE-KMS objects, digests valid; flow-log group associated with the key; `evidence_v2/R7/`); the runtime grant is exercised in R11: R8 (2026-10-27) created the secret encrypted with the key by the admin role through the root statement's IAM delegation, not by the runtime role (no host before R11). |

---

## Control Group 5 — Secrets Manager

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-20 | Secret created and encrypted with CMK | `proposal-orchestrator/env-config` stored encrypted with the CMK (or the OD8 (b) design, restated) | R8 | VERIFIED_PASS | `evidence_v2/R8/` (`VERIFICATION.md`; `R8_08_describe-secret.json`, `R8_08_list-secrets.json`, `R8_08_version-ids.json`, `R8_09_key-names-digest.txt`) | Verified 2026-10-27 at policy level (R8-D8): `proposal-orchestrator/env-config-KTsWow`, `KmsKeyId` = the R6 `KeyArn` (R8-D16), one `AWSCURRENT` version encrypted with it, no rotation, no replica, retained (R8-D5). It holds five non-credential keys (preset `BEDROCK_CONVERSE_EU`, production mode, diagnostic level, Region, model; R8-D2, R8-D3), shown by key names and SHA-256 only. Runtime read through `secretsmanager.eu-north-1.amazonaws.com` exercised in R11. |
| DC-21 | Secret resource policy scoped | Resource policy names only the runtime identity, plus an admin role if one exists | R8 | VERIFIED_PASS | `evidence_v2/R8/` (`VERIFICATION.md`; `R8_08_resource-policy.json`, `R8_09_key-names-digest.txt`) | Verified 2026-10-27 at policy level (R8-D8): deny-only with `BlockPublicPolicy` (R8-D4), four statements equal to the template — the runtime role may only `GetSecretValue`; only the runtime role and the admin role (`AccountFullAccessRole`, with and without `/managed/`, R8-D12) read the value; only the admin role changes, deletes, tags, rotates or replicates it; nothing outside the account (R8-D13). Same-account grants come from IAM (R5 `RuntimeSecretRead`). The admin's read was not denied (one admin form matches). Runtime half exercised in R11 (no simulation of a resource policy for a role, F-R7-7). |
| DC-22 | API key rotation configured (if applicable) | Rotation for any API-key secret | R8 | NOT_APPLICABLE | `evidence_v2/R8/VERIFICATION.md` | 2026-10-27 (R8-D14): no API-key secret exists; `bedrock_converse` authenticates through IAM and the runtime secret holds no credential. Re-assessed only if a later record adds an API-key secret. |

---

## Control Group 6 — CloudTrail

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-23 | CloudTrail trail with KMS encryption | Trail `proposal-orchestrator-bedrock-trail` encrypted with the CMK | R7 | VERIFIED_PASS | `evidence_v2/R7/` (`VERIFICATION.md`; `R7_08_trail.json`, `R7_08_trail-status.json`, `R7_11_trail-status.json`, `R7_11_log-object-encryption.json`) | Verified 2026-10-26: trail `TrailArn` in `R7_outputs.json`, single-Region, home eu-north-1, `KmsKeyId` = the CMK, `IsLogging` true since 17:44:09Z; log and digest objects delivered under `cloudtrail/proposal-orchestrator/` are SSE-KMS with the CMK, without an S3 Bucket Key; created and delivering without a CloudTrail decrypt grant (R6-D10). Management events by default (R7-D6); DC-26 (Converse events) is R11. |
| DC-24 | Log file validation enabled | Digest files enabled | R7 | VERIFIED_PASS | `evidence_v2/R7/` (`VERIFICATION.md`; `R7_08_trail.json`, `R7_11_digest-object-encryption.json`, `R7_11b_trail-status.json`, `R7_11b_validate-logs.txt`) | Verified 2026-10-26: `LogFileValidationEnabled` true; hourly digests delivered (latest 19:01:20Z), SSE-KMS with the CMK; `aws cloudtrail validate-logs` over 17:44:09Z–18:44:09Z: 2/2 digest files and 12/12 log files valid (R7-D15). |
| DC-25 | Trail S3 bucket secured | Encryption, deny insecure transport and unencrypted objects, versioning, Block Public Access | R7 | VERIFIED_PASS | `evidence_v2/R7/` (`VERIFICATION.md`; `R7_08_trail-bucket-encryption.json`, `-public-access-block.json`, `-versioning.json`, `-ownership.json`, `-policy.json`) | Verified 2026-10-26 on `TrailBucketName` (`R7_outputs.json`): default SSE-KMS with the CMK, no Bucket Key (R6-D10, R7-D1); Block Public Access all four; versioning Enabled; `BucketOwnerEnforced` (R7-D12); policy equal to the template (four statements: CloudTrail ACL check and write by `aws:SourceArn`, deny unencrypted objects, deny insecure transport). Retained on stack deletion (R7-D4). The deploy bucket (not a DC row) is evidenced in the same folder: CMK with Bucket Key, the same three settings, deny-only policy; test uploads in `R7_09_*` (R7-D17). |
| DC-26 | CloudTrail captures Bedrock Converse events | Converse events appear in CloudTrail after the test call | R11 | NOT_STARTED | — | — |
| DC-27 | S3 lifecycle policy for trail logs | Glacier Instant Retrieval after 90 days, expiry after 365 days | R7 | VERIFIED_PASS | `evidence_v2/R7/` (`VERIFICATION.md`; `R7_08_trail-bucket-lifecycle.json`) | Verified 2026-10-26: one enabled rule on prefix `cloudtrail/proposal-orchestrator/` (the trail prefix): `GLACIER_IR` after 90 days, expiration after 365 days, noncurrent versions after 30 days (R7-D7). |

---

## Control Group 7 — CloudWatch

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-28 | Bedrock model invocation logging disabled | Invocation-logging configuration is empty | R7 | VERIFIED_PASS | `evidence_v2/R7/` (`VERIFICATION.md`; `R7_03_invocation-logging-before.txt`, `R7_08_invocation-logging-after.txt`) | Verified 2026-10-26 in eu-north-1 before and after the audit stack: `get-model-invocation-logging-configuration` returns no configuration (exit 0, empty). The runtime role is explicitly denied changing it (DC-11). |
| DC-29 | No Bedrock invocation log groups | No `/aws/bedrock` log groups exist | R7 | VERIFIED_PASS | `evidence_v2/R7/` (`VERIFICATION.md`; `R7_03_log-groups-bedrock-before.json`, `R7_08_log-groups-bedrock-after.json`) | Verified 2026-10-26 in eu-north-1: no log group under `/aws/bedrock`, before and after the audit stack. |
| DC-30 | Operational log groups encrypted, retention set | Log groups use the CMK and at most 90-day retention | R7 | VERIFIED_PASS | `evidence_v2/R7/` (`VERIFICATION.md`; `R7_03_log-groups-before.json`, `R7_08_log-groups.json`) | Verified 2026-10-26 over every log group in eu-north-1 (R7-D14): none before R7; after R7 exactly `/proposal-orchestrator/vpc-flow-logs`, `kmsKeyId` the CMK, retention 90 days, retained on stack deletion. The CloudWatch Logs grant of the key policy was exercised by this association (DC-19). |

---

## Control Group 8 — Data Egress Prevention

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-07 | Host SG restricts outbound | Outbound TCP 443 to the endpoint SG and to the Region's S3 prefix list only; no inbound rule; no `0.0.0.0/0`; attached to the host | R4 (SG), R11 | IN_PROGRESS | `evidence_v2/R4/` (`VERIFICATION.md`; `R4_07_security-groups.json`, `R4_07_security-group-rules.json`) | Wording corrected 2026-10-24 (v1 read "to the endpoint SG only"; the S3 prefix-list egress was always needed for the gateway endpoint, F7). SG half verified 2026-10-24: the host SG (`HostSecurityGroupId` in `R4_outputs.json`), two egress rules `tcp` 443 (→ the Region's S3 prefix list, → the endpoint SG), no ingress. Attachment to the host is R11. |
| DC-08 | VPC flow logs enabled | Flow logs with traffic type ALL on every subnet, to CloudWatch Logs | R7 | VERIFIED_PASS | `evidence_v2/R7/` (`VERIFICATION.md`; `R7_08_flow-logs.json`, `R7_08_subnets.json`, `R7_11_flow-log-status.json`) | Verified 2026-10-26 on configuration (R7-D18): one flow log (`FlowLogId` in `R7_outputs.json`) on the VPC, which covers its one subnet and any later one; `TrafficType` ALL; CloudWatch Logs `/proposal-orchestrator/vpc-flow-logs` (CMK); `MaxAggregationInterval` 600; `FlowLogStatus` ACTIVE, `DeliverLogsStatus` SUCCESS. The VPC has no network interface before R11, so no records exist yet: delivered records, and the R5-D4 known gap (scoped `logs:DescribeLogGroups`), are shown by R11. |
| DC-31 | No Claude CLI binary on deployment host | `which claude` returns not found | R12b | NOT_STARTED | — | — |
| DC-32 | Internet egress blocked from deployment host | Requests to public endpoints from the host time out or fail | R12b | NOT_STARTED | — | — |

---

## Control Group 9 — Production Application Configuration

| Control ID | Control Name | Requirement Summary | Ticket | Status | Evidence (v2) | Notes |
|---|---|---|---|---|---|---|
| DC-33 | `ORCHESTRATOR_PRODUCTION_MODE=true` | Production mode set, read on the host through the R9 launcher | R8, R9, R12b | NOT_STARTED | — | R8 (2026-10-27) stores the value in `proposal-orchestrator/env-config` (R8-D2, R8-D3; key names and SHA-256 in `evidence_v2/R8/R8_09_key-names-digest.txt`); read on the host through the R9 launcher in R12b. R9 (2026-10-27): the launcher `runner/host_env.py` is in place and tested (`evidence_v2/R9/`, decision record `aws-redeployment-r9-runtime-config_2026-10-27`); it refuses the real secret until R9e adds `BEDROCK_CONVERSE_EU` (R8-D3); production mode now refuses to run without `AWS_REGION`. |
| DC-34 | Converse transport preset | Transport preset selects the Bedrock Converse backend for the OD1 region | R8, R9, R12b | NOT_STARTED | — | R8 (2026-10-27) stores the value in `proposal-orchestrator/env-config` (R8-D2, R8-D3; key names and SHA-256 in `evidence_v2/R8/R8_09_key-names-digest.txt`); read on the host through the R9 launcher in R12b — the preset `BEDROCK_CONVERSE_EU` exists only after R9e. R9 (2026-10-27): the launcher `runner/host_env.py` is in place and tested (`evidence_v2/R9/`, decision record `aws-redeployment-r9-runtime-config_2026-10-27`); it refuses the real secret until R9e adds `BEDROCK_CONVERSE_EU` (R8-D3); production mode now refuses to run without `AWS_REGION`. |
| DC-35 | `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` | Diagnostic level prevents prompt and response content being written to disk | R8, R9, R12b | NOT_STARTED | — | R8 (2026-10-27) stores the value in `proposal-orchestrator/env-config` (R8-D2, R8-D3; key names and SHA-256 in `evidence_v2/R8/R8_09_key-names-digest.txt`); read on the host through the R9 launcher in R12b. R9 (2026-10-27): the launcher `runner/host_env.py` is in place and tested (`evidence_v2/R9/`, decision record `aws-redeployment-r9-runtime-config_2026-10-27`); it refuses the real secret until R9e adds `BEDROCK_CONVERSE_EU` (R8-D3); production mode now refuses to run without `AWS_REGION`. R10 (2026-10-28): the Phase 8 decomposed drafter honours the diagnostic level: at `metadata` it writes only a content-free `<sub>.response_meta.json` and no response excerpt in error messages (decision record `aws-redeployment-r10-drafter-transport_2026-10-28`, R10-D7, R10-D17; `evidence_v2/R10/`); R12b's evidence can cite it. Open: the skill runtime's failure reason still carries a response head at any level (F-R10-1). |
| DC-36 | Model availability confirmed in target region | The OD7 models answer in the OD1 region | R2, R11 | IN_PROGRESS | `evidence_v2/R2/` (`VERIFICATION.md`; `R2_07_converse-sonnet-4-6.json`, `R2_14_converse-opus-4-6-v1.json`, `R2_08_quotas-applied.json`) | R2 part verified 2026-10-21: the OD7 models (`aws-redeployment-od7-model-set_2026-10-21`) `eu.anthropic.claude-opus-4-6-v1` and `eu.anthropic.claude-sonnet-4-6` answer from eu-north-1 (CloudShell); RPM 5 / 10. Newer models refused for this account. Host-side call through PrivateLink remains for R11. |
| DC-38 | Full DAG run succeeds with production config | All phases complete, all gates pass under production configuration | R16 | DEFERRED | `evidence_v2/R16/` (`VERIFICATION.md`) | Deferred 2026-10-29 per OD12 (`aws-redeployment-operator-decisions_2026-10-21`: "No. DC-38 stays deferred, but F5 is fixed anyway (R10)."). R16 stays open as deferred; recorded before R11 by the operator's override of R16's R11 dependency (`aws-redeployment-r16-dc38-deferred_2026-10-29`). Reopened only by a successor to OD12, which would make R16 a full DAG run on the host. Scope per OD12 R10 (2026-10-28): F5 closed — the Phase 8 drafter resolves its provider through the transport layer and under production mode never reaches the Claude CLI transport, which itself refuses (R10-D1, R10-D6; `evidence_v2/R10/`). No Phase 8 run on the host. |

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
