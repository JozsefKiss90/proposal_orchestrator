# Risk Acceptance Register

## Proposal Orchestrator — AWS Bedrock Deployment

| Field | Value |
|---|---|
| Document type | Risk Acceptance Register |
| Classification | Internal — Security Review |
| Date | 2026-06-03 |
| Review cycle | Quarterly (next: 2026-09-03) |
| System | Proposal Orchestrator on AWS Bedrock |
| AWS account | `232538551827` |

---

## 1. Executive Summary

This register documents the identified risks for the Proposal Orchestrator deployment on AWS Bedrock, their assessed likelihood and impact, the implemented mitigations, and the residual risk status.

**Risk posture summary:**

| Status | Count |
|---|---|
| Mitigated | 8 |
| Accepted | 3 |
| Operationally Managed | 4 |
| **Total** | **15** |

No risks are classified as unmitigated or unacceptable. Eight risks are mitigated to low residual risk through verified infrastructure controls. Three risks are accepted with documented justification. Four risks require ongoing operational management.

All mitigations reference verified infrastructure controls from the CG1-CG10 hardening programme (38/41 VERIFIED_PASS). Where a mitigation has not been independently verified, this is stated.

---

## 2. Rating Definitions

### Likelihood

| Rating | Definition |
|---|---|
| Low | Unlikely to occur under normal operating conditions; requires multiple control failures or deliberate action. |
| Medium | Could occur during the operational lifetime of the system; requires a single control failure or an uncommon external event. |
| High | Likely to occur without active management; known attack vectors exist or the condition is probable. |

### Impact

| Rating | Definition |
|---|---|
| Low | Minor operational disruption; no data exposure; recoverable without external action. |
| Medium | Partial service interruption or limited data exposure; recoverable with administrative action; possible institutional reputational concern. |
| High | Significant data exposure, loss of institutional IP, regulatory consequence, or inability to meet a submission deadline. |

### Residual Risk

| Classification | Definition |
|---|---|
| Low | Remaining risk is within institutional risk appetite after mitigation. |
| Medium | Remaining risk is notable; ongoing monitoring or periodic review is required. |
| High | Remaining risk exceeds institutional risk appetite; additional mitigations are needed. |

---

## 3. Risk Register

### RSK-01: Data Exfiltration via Internet

| Field | Value |
|---|---|
| Risk ID | RSK-01 |
| Risk description | Proposal data (institutional IP) is exfiltrated from the EC2 host to the public internet via a misconfigured network path, an application-level vulnerability, or a compromised dependency. |
| Likelihood | **Low** |
| Impact | **High** |
| Mitigation | Private subnet with no Internet Gateway or NAT Gateway route (DC-06). Host security group restricts egress to VPC endpoint SG and S3 prefix list only (DC-07). No Claude CLI binary on host (DC-31). Internet egress verified blocked by negative test (DC-32). VPC Flow Logs capture all network traffic (DC-08). |
| Evidence | `EV-PL-006-route-table.json`, `EV-DEP-002-host-sg.json`, `CG_8_logs.txt`, `REG-E03-negative-region-test.txt`, `EV-DEP-003-flow-logs-subnet-a.json` |
| Residual risk | **Low** |
| Status | **Mitigated** |

### RSK-02: Unauthorised AWS Access

| Field | Value |
|---|---|
| Risk ID | RSK-02 |
| Risk description | An unauthorised party gains access to the AWS account or the EC2 host and accesses proposal data, modifies infrastructure, or invokes Bedrock with malicious prompts. |
| Likelihood | **Low** |
| Impact | **High** |
| Mitigation | IAM authentication required for all API access. SSM Session Manager for host access (no SSH, no inbound ports). Permission boundary limits maximum scope of Bedrock role (DC-12). Explicit deny statements prevent non-Bedrock service access (DC-11). CloudTrail logs all API activity with caller identity (DC-23, DC-26). MFA should be enforced on IAM identities (operator responsibility). |
| Evidence | `EV-IAM-001-role-config.json`, `EV-IAM-004-boundary-metadata.json`, `EV-IAM-003-policy-explicit-deny.json`, `CT-E06-bedrock-converse-events.json` |
| Residual risk | **Low** |
| Status | **Mitigated** |
| Note | MFA enforcement on operator IAM identities is an institutional responsibility and is not verified by this register. |

### RSK-03: Credential Compromise

| Field | Value |
|---|---|
| Risk ID | RSK-03 |
| Risk description | AWS credentials (access keys, session tokens) are exposed through filesystem storage, environment variables, or application logs. |
| Likelihood | **Low** |
| Impact | **High** |
| Mitigation | Instance profile authentication — no long-term access keys on host (DC-14, DC-15). Credentials are obtained via STS role assumption with automatic rotation. Secrets Manager stores configuration encrypted with CMK (DC-20). Diagnostic level prevents prompt/response content in logs (DC-35). Pre-commit secret scanning in repository (Phase 2 hardening). |
| Evidence | `IAM_Least_Privilege_logs.txt` lines 805-808, `SM-E03-kms-key-association.txt`, `CG9_logs.txt` |
| Residual risk | **Low** |
| Status | **Mitigated** |

### RSK-04: Excessive IAM Permissions

| Field | Value |
|---|---|
| Risk ID | RSK-04 |
| Risk description | The Bedrock execution role has permissions beyond what is required, enabling unintended actions such as model administration, access to non-Claude models, or interaction with non-Bedrock AWS services. |
| Likelihood | **Low** |
| Impact | **Medium** |
| Mitigation | IAM policy scoped to `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on `anthropic.claude-*` model ARNs only (DC-10). Explicit deny for Bedrock admin actions, non-Bedrock services, and non-Claude models (DC-11). Permission boundary caps maximum scope (DC-12). IAM simulation tests verify allowed and denied actions. |
| Evidence | `EV-IAM-003-policy-bedrock-invoke.json`, `EV-IAM-003-policy-explicit-deny.json`, `EV-IAM-005-sim-allowed-invoke.json`, `EV-IAM-006-sim-denied-admin.json`, `EV-IAM-007-sim-denied-non-claude.json` |
| Residual risk | **Low** |
| Status | **Mitigated** |

### RSK-05: Cloud Provider Service Outage

| Field | Value |
|---|---|
| Risk ID | RSK-05 |
| Risk description | An AWS regional outage in `us-east-1` renders Bedrock, Secrets Manager, or other dependent services unavailable, preventing proposal preparation within a time-critical period. |
| Likelihood | **Low** |
| Impact | **Medium** |
| Mitigation | IAM policy authorises both `us-east-1` and `eu-west-1` regions, enabling redeployment to the alternative region if model availability is confirmed. Local copies of proposal input data and deliverables are on the operator's workstation. Orchestration state is durable on the host filesystem and can be resumed after service restoration. |
| Evidence | `EV-IAM-003-policy-bedrock-invoke.json` (region list: `[eu-west-1, us-east-1]`) |
| Residual risk | **Medium** |
| Status | **Accepted** |
| Justification | AWS regional outages are rare events. The redeployment procedure to `eu-west-1` is documented but not automated. The institution accepts the risk of temporary unavailability. |

### RSK-06: Bedrock Regional Model Unavailability

| Field | Value |
|---|---|
| Risk ID | RSK-06 |
| Risk description | The target model (`us.anthropic.claude-sonnet-4-6`) becomes temporarily or permanently unavailable in the deployed region due to provider capacity constraints, model deprecation, or service changes. |
| Likelihood | **Medium** |
| Impact | **Medium** |
| Mitigation | Model availability confirmed by functional test from host (DC-36, evidence `CG9_logs.txt`). IAM policy permits both `us-east-1` and `eu-west-1`. The transport layer supports model ID configuration via environment variable (`SKILL_MODEL`), enabling switch to an alternative Claude model without code changes. |
| Evidence | `CG9_logs.txt`, `EV-APP-002-model-availability.json` |
| Residual risk | **Medium** |
| Status | **Operationally Managed** |
| Action | Monitor Bedrock model availability announcements. Maintain awareness of alternative model IDs. |

### RSK-07: Model Hallucination in Proposal Content

| Field | Value |
|---|---|
| Risk ID | RSK-07 |
| Risk description | The language model generates factually incorrect, fabricated, or unsupported claims in proposal text that, if not detected, are submitted to the European Commission, leading to evaluation score reduction or reputational damage. |
| Likelihood | **High** |
| Impact | **Medium** |
| Mitigation | The orchestrator workflow includes structured review gates at each phase. Phase 8 (Drafting and Review) produces a review packet that distinguishes confirmed facts from inferences. The repository constitution (CLAUDE.md) prohibits fabrication of project facts (Section 13.3) and requires traceability of all deliverable claims to tiered source data (Section 11.4). Operator review of all generated content before use is mandatory. |
| Evidence | `CLAUDE.md` Sections 11 and 13 |
| Residual risk | **Medium** |
| Status | **Operationally Managed** |
| Action | Operators must review all generated proposal content against source data before use in any submission. The system is a preparation aid, not a submission system. |

### RSK-08: Incorrect or Non-Compliant Proposal Generation

| Field | Value |
|---|---|
| Risk ID | RSK-08 |
| Risk description | The orchestrator generates proposal sections that do not comply with the application form structure, exceed page limits, or fail to address mandatory evaluation criteria, resulting in a non-compliant submission. |
| Likelihood | **Medium** |
| Impact | **Medium** |
| Mitigation | The system uses extracted instrument schemas (Tier 2A) and extracted call constraints (Tier 2B) to govern section structure and content alignment. Gate conditions enforce phase sequencing and completeness checks. Validation reports flag assumptions and incomplete source data. The system is designed to fail explicitly (gate failure) rather than produce silently non-compliant output. |
| Evidence | `CLAUDE.md` Sections 6, 7, and 12 |
| Residual risk | **Medium** |
| Status | **Operationally Managed** |
| Action | Operators must verify compliance of generated content against the applicable application form template and call-specific requirements. |

### RSK-09: Secrets Exposure

| Field | Value |
|---|---|
| Risk ID | RSK-09 |
| Risk description | The Secrets Manager secret containing production configuration is accessed by an unauthorised role or exposed through an application error. |
| Likelihood | **Low** |
| Impact | **Medium** |
| Mitigation | Resource policy restricts secret access to `proposal-orchestrator-bedrock-role` and `proposal-orchestrator-ec2-ssm-role` only (DC-21). Secret is encrypted with customer-managed KMS key (DC-20). KMS key policy restricts decrypt permissions to the Bedrock role (DC-19). No API key secrets are stored; production uses IAM auth (DC-22 N/A). |
| Evidence | `SM-E04-resource-policy.json`, `SM-E03-kms-key-association.txt`, `KMS-E03-key-policy.json` |
| Residual risk | **Low** |
| Status | **Mitigated** |

### RSK-10: Audit Logging Failure

| Field | Value |
|---|---|
| Risk ID | RSK-10 |
| Risk description | CloudTrail stops logging, log delivery fails, or log integrity is compromised, creating a gap in the audit record of Bedrock API invocations. |
| Likelihood | **Low** |
| Impact | **Medium** |
| Mitigation | CloudTrail trail is active with `IsLogging: true` (DC-23). Log file validation is enabled for integrity verification (DC-24). S3 bucket has versioning enabled and a deny-insecure-transport policy (DC-25). S3 bucket lifecycle prevents accidental deletion before retention period (DC-27). |
| Evidence | `CT-E02-trail-status.json`, `CT-E03-log-file-validation.txt`, `CT-E09-s3-versioning.json`, `CT-E07-s3-bucket-policy.json` |
| Residual risk | **Low** |
| Status | **Mitigated** |

### RSK-11: Infrastructure Configuration Drift

| Field | Value |
|---|---|
| Risk ID | RSK-11 |
| Risk description | Security group rules, IAM policies, route table entries, or other infrastructure configurations are modified after initial hardening, weakening security controls without detection. |
| Likelihood | **Medium** |
| Impact | **Medium** |
| Mitigation | CloudTrail logs all infrastructure modification API calls. The `collect_evidence.ps1` script enables automated re-collection of all evidence artefacts, allowing comparison against the baseline. The hardening control register (`aws_hardening_control_register.md`) provides the authoritative baseline. Periodic review is documented in `operational_procedure.md`. |
| Evidence | `CT-E01-trail-configuration.json`, `collect_evidence.ps1` |
| Residual risk | **Medium** |
| Status | **Operationally Managed** |
| Action | Run `collect_evidence.ps1` monthly and compare output against baseline integrity manifest. Review CloudTrail for infrastructure modification events quarterly. |

### RSK-12: Supply Chain Dependency Risk

| Field | Value |
|---|---|
| Risk ID | RSK-12 |
| Risk description | A Python dependency (boto3, pyyaml, jsonschema, python-dotenv) contains a vulnerability or is compromised at the package repository level, introducing a security weakness into the application runtime. |
| Likelihood | **Low** |
| Impact | **Medium** |
| Mitigation | Dependencies are pinned in `requirements.txt`. The deployment uses pre-downloaded wheels bundled into the deployment tarball, not live package installation from PyPI. The host has no internet access, preventing runtime package downloads. The dependency set is minimal (4 packages plus transitive dependencies). |
| Evidence | Deployment guide Section 4 (offline wheel installation), DC-32 (no internet egress) |
| Residual risk | **Low** |
| Status | **Mitigated** |

### RSK-13: Human Operator Error

| Field | Value |
|---|---|
| Risk ID | RSK-13 |
| Risk description | An operator misconfigures environment variables, provides incorrect input data, runs the orchestrator in an incorrect mode, or misinterprets generated output, leading to incorrect proposal content or a security control bypass. |
| Likelihood | **Medium** |
| Impact | **Medium** |
| Mitigation | Production mode enforcement rejects non-Bedrock backends (DC-33). Diagnostic level enforcement prevents content logging (DC-35). The operational procedure (`operational_procedure.md`) defines step-by-step processes. The security checklist in the deployment guide (Section 10) provides pre-execution validation steps. |
| Evidence | `CG9_logs.txt`, deployment guide Section 10 |
| Residual risk | **Medium** |
| Status | **Accepted** |
| Justification | Operator training and procedural adherence are institutional responsibilities. The system provides technical guardrails (production mode, diagnostic level enforcement) but cannot prevent all forms of operator error. |

### RSK-14: EBS Volume Data Persistence After Instance Termination

| Field | Value |
|---|---|
| Risk ID | RSK-14 |
| Risk description | Proposal data and generated deliverables persist on the EBS volume after the instance is stopped or terminated, and could be accessed if the volume is not properly decommissioned. |
| Likelihood | **Low** |
| Impact | **Medium** |
| Mitigation | EBS volumes are encrypted by default (AWS account-level setting). Upon instance termination with `DeleteOnTermination=true` (default for root volumes), the volume is deleted and the underlying storage is wiped by AWS. For non-root volumes, explicit deletion is required. |
| Evidence | None — EBS encryption status and `DeleteOnTermination` flag have not been independently verified. |
| Residual risk | **Low** |
| Status | **Accepted** |
| Justification | AWS EBS data erasure guarantees are contractual (AWS shared responsibility model). The risk is low given encryption at rest and the controlled access environment. Verification of the `DeleteOnTermination` flag is recommended during periodic review. |
| Assumption | EBS default encryption is enabled at the account level. This has not been independently verified in the hardening programme. |

### RSK-15: KMS Key Compromise or Deletion

| Field | Value |
|---|---|
| Risk ID | RSK-15 |
| Risk description | The customer-managed KMS key is accidentally deleted or scheduled for deletion, rendering all encrypted data (secrets, CloudTrail logs, VPC Flow Logs) permanently inaccessible. |
| Likelihood | **Low** |
| Impact | **High** |
| Mitigation | KMS key policy includes `AllowRootFullAccess` statement for lockout prevention (evidence `KMS-E03-key-policy.json`). KMS enforces a minimum 7-day waiting period before key deletion. Key rotation is enabled with 365-day period (DC-18, evidence `KMS-E02-rotation-status.json`). |
| Evidence | `KMS-E03-key-policy.json`, `KMS-E02-rotation-status.json` |
| Residual risk | **Low** |
| Status | **Mitigated** |

---

## 4. Risk Matrix

| | **Low Impact** | **Medium Impact** | **High Impact** |
|---|---|---|---|
| **High Likelihood** | | RSK-07, RSK-08 | |
| **Medium Likelihood** | | RSK-06, RSK-11, RSK-13 | |
| **Low Likelihood** | | RSK-04, RSK-05, RSK-09, RSK-10, RSK-12, RSK-14 | RSK-01, RSK-02, RSK-03, RSK-15 |

---

## 5. Review Schedule

| Review | Frequency | Scope |
|---|---|---|
| Risk register review | Quarterly | All risks: reassess likelihood, impact, and mitigation effectiveness |
| Evidence re-collection | Monthly | Run `collect_evidence.ps1` and compare against baseline |
| CloudTrail review | Quarterly | Review for unexpected API calls, infrastructure modifications |
| Full security reassessment | Annual | Re-evaluate all controls, update risk register, reassess architecture |

**Next scheduled review:** 2026-09-03

---

*Document prepared for institutional security review. Risk ratings reflect the assessed state as of 2026-06-03. All mitigations citing DC references are backed by verified evidence artefacts from the CG1-CG10 hardening programme. Assumptions are explicitly identified where independent verification is not available.*
