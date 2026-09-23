# Data Flow and Data Protection Assessment

## Proposal Orchestrator — AWS Bedrock Deployment

| Field | Value |
|---|---|
| Document type | Data Flow and Data Protection Assessment |
| Classification | Internal — GDPR Compliance Review |
| Date | 2026-06-03 |
| System | Proposal Orchestrator (Horizon Europe proposal preparation) |
| Deployment | AWS Account `232538551827`, Region `us-east-1` |
| Infrastructure baseline | 38/41 controls VERIFIED_PASS |

---

## 1. Purpose of Processing

The Proposal Orchestrator is an automated system that assists in the preparation of research and innovation proposals for submission under the European Commission's Horizon Europe Framework Programme. It processes structured project inputs through an eight-phase workflow, invoking a large language model (Claude Sonnet 4.6 via Amazon Bedrock) to generate evaluator-oriented proposal sections.

The system is operated by university research staff for the purpose of:

- Analysing Horizon Europe call requirements and evaluation criteria.
- Refining project concepts against call-specific vocabulary and scope.
- Designing work package structures, timelines, and milestone definitions.
- Constructing impact pathways aligned with call expected outcomes.
- Defining implementation and risk management architectures.
- Drafting proposal sections for all required application form parts.
- Conducting structured review against evaluation criteria.

The processing is conducted in the context of institutional research administration. The system is a preparation tool; it does not submit proposals to the European Commission.

---

## 2. Categories of Data Processed

### 2.1 Data Classification

| Category | Examples | Classification | May Contain Personal Data |
|---|---|---|---|
| Horizon Europe call documents | Work programme texts, call extracts, evaluation criteria, eligibility conditions | Public (published by European Commission) | No |
| Proposal drafts | Excellence sections, impact narratives, implementation plans, management descriptions | Institutional IP — Confidential | Potentially (see 2.2) |
| Work package descriptions | Task definitions, deliverable descriptions, effort allocations, dependency maps | Institutional IP — Confidential | No |
| Partner organisation information | Organisation names, departments, declared capabilities, roles, prior project references | Organisational — Confidential | Potentially (see 2.2) |
| Research project information | Project objectives, expected outcomes, expected impacts, risk assessments, budget structures | Institutional IP — Confidential | No |
| Application form structural data | Section schemas, field definitions, page limits | Regulatory — Public/Restricted | No |
| Orchestration state | Phase outputs, decision logs, validation reports, gate results | Operational — Internal | No |

### 2.2 Personal Data Assessment

The system is designed to process institutional and project-level data. However, the following categories may incidentally contain personal data:

**Consortium partner information** may include the names, affiliations, and professional qualifications of named researchers when such details are included in the project brief or consortium data files (Tier 3 `consortium/` directory). This constitutes professional contact data and is processed on the basis of the legitimate interests of the consortium in preparing a joint proposal submission.

**Proposal draft text** may refer to named principal investigators, work package leaders, or key personnel when such references are required by the application form structure (e.g., Section 3.2 "Quality and efficiency of the implementation — Capacity of participants").

**The system does not process:**
- Special category data (Article 9 GDPR)
- Financial data of natural persons
- National identification numbers
- Health data
- Data relating to criminal convictions

### 2.3 Data Minimisation

The system processes only the data provided in the Tier 3 project instantiation inputs. It does not retrieve, scrape, or infer personal data from external sources. The scope of personal data processing is determined by the content of the input documents prepared by the operator.

---

## 3. Data Storage Locations

### 3.1 EC2 Host Runtime Storage

| Location | Content | Persistence | Encryption |
|---|---|---|---|
| `/opt/proposal-orchestrator/docs/tier1_*` through `tier3_*` | Input documents (call data, project data, consortium data) | Persistent on EBS volume | EBS default encryption |
| `/opt/proposal-orchestrator/docs/tier4_orchestration_state/` | Phase outputs, decision logs, validation reports | Persistent on EBS volume | EBS default encryption |
| `/opt/proposal-orchestrator/docs/tier5_deliverables/` | Generated proposal sections, assembled drafts | Persistent on EBS volume | EBS default encryption |
| `/opt/proposal-orchestrator/.claude/runs/` | Runtime execution state (run summaries, invocation ledgers) | Persistent on EBS volume | EBS default encryption |

**Note on diagnostic data:** The application is configured with `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` (DC-35, evidence `CG9_logs.txt`). This setting prevents prompt content and model response content from being written to the local filesystem. Only metadata (character counts, timing, error classifications) is persisted. This is enforced by the application code and verified by 40 repository-side security tests.

### 3.2 AWS CloudTrail Logs

| Location | Content | Retention | Encryption |
|---|---|---|---|
| S3 bucket `proposal-orchestrator-cloudtrail-232538551827` | API event metadata: caller identity, timestamp, source IP, VPC endpoint ID, model ID, event name, TLS version | 365 days (lifecycle policy), archived to Glacier IR after 90 days | Customer-managed KMS key |

**CloudTrail logs do not contain prompt or response content.** Bedrock invocation logging is explicitly disabled (DC-28, evidence `CG7_logs.txt`). CloudTrail records the occurrence and metadata of API calls, not their payload.

### 3.3 CloudWatch Logs

| Location | Content | Retention | Encryption |
|---|---|---|---|
| Log group `/proposal-orchestrator/vpc-flow-logs` | VPC Flow Log records: source/destination IP, port, protocol, action, byte count | 90 days | Customer-managed KMS key |

**VPC Flow Logs do not contain application-layer data.** They record network-level metadata only (IP addresses, ports, byte counts).

### 3.4 AWS Secrets Manager

| Location | Content | Encryption |
|---|---|---|
| Secret `proposal-orchestrator/env-config` | Application configuration values: transport preset, production mode flag, diagnostic level, region, model ID | Customer-managed KMS key (`alias/proposal-orchestrator`) |

The secret does not contain personal data. It contains operational configuration parameters only.

### 3.5 Amazon Bedrock (Transient)

| Location | Content | Retention | Encryption |
|---|---|---|---|
| Bedrock runtime memory | Prompt content and model response content during API call execution | **Zero retention** — data is not stored after the API response is returned | In-transit TLS 1.3 (verified in CloudTrail events) |

Amazon Bedrock provides a contractual zero-retention guarantee (AWS Bedrock Service Terms, Section 50.3): input prompts and output completions are not stored by AWS after the API response is returned, and are not used to train or improve foundation models.

---

## 4. Data Transfers

### 4.1 Transfer Inventory

| Transfer | Source | Destination | Protocol | Network Path | Traverses Public Internet |
|---|---|---|---|---|---|
| Bedrock inference | EC2 host | Bedrock Runtime | HTTPS (TLS 1.3) | VPC Interface Endpoint -> AWS PrivateLink | **No** |
| Secret retrieval | EC2 host | Secrets Manager | HTTPS | VPC Interface Endpoint -> AWS PrivateLink | **No** |
| STS role assumption | EC2 host | AWS STS | HTTPS | VPC Interface Endpoint -> AWS PrivateLink | **No** |
| Deployment artefact transfer | S3 bucket | EC2 host | HTTPS | S3 Gateway Endpoint (internal routing) | **No** |
| CloudTrail log delivery | CloudTrail | S3 bucket | Internal AWS | AWS-internal delivery | **No** |
| VPC Flow Log delivery | VPC | CloudWatch Logs | Internal AWS | AWS-internal delivery | **No** |
| Operator session | User workstation | EC2 host | HTTPS (SSM) | SSM Interface Endpoints -> AWS PrivateLink | **No** (SSM WebSocket over TLS) |

### 4.2 Confirmation of No Public Internet Transit

All data transfers between the EC2 host and AWS services occur through VPC endpoints within the private network. This is confirmed by the following evidence:

- **Route table** (`rtb-085481996de5e3ed9`): contains only `local` (172.31.0.0/16) and S3 prefix list (`pl-63a5400a`). No `0.0.0.0/0` route to an Internet Gateway or NAT Gateway exists (DC-06, evidence `EV-PL-006-route-table.json`).
- **Host security group** (`sg-076f724aed2429771`): egress rules permit TCP 443 to the VPC endpoint security group and S3 prefix list only. No `0.0.0.0/0` egress rules exist (DC-07, evidence `EV-DEP-002-host-sg.json`).
- **DNS resolution**: `bedrock-runtime.us-east-1.amazonaws.com` resolves to private VPC IP addresses (172.31.27.207, 172.31.80.15), not public IPs (DC-02, evidence `EV-PL-005-private-dns-resolution.txt`).
- **Negative test**: curl to `api.anthropic.com` and `api.together.ai` times out from the host (DC-32, evidence `REG-E03-negative-region-test.txt`).
- **CloudTrail events**: Bedrock Converse events show `sourceIPAddress: 172.31.93.116` (VPC private IP) and `vpcEndpointId: vpce-0843d225c5b1ef6d5` (DC-26, evidence `CT-E06-bedrock-converse-events.json`).

### 4.3 International Data Transfers

The system is deployed in AWS region `us-east-1` (US East, N. Virginia). Bedrock inference requests are processed in this region.

**EU-US data transfer consideration:** If the deploying institution is an EU-based entity (e.g., a European university), the transfer of proposal data to the US-East region constitutes an international data transfer under GDPR Chapter V. The legal basis for this transfer is:

- The EU-US Data Privacy Framework (DPF), adopted by European Commission adequacy decision on 10 July 2023.
- AWS's participation in the DPF, documented in AWS compliance materials.
- The AWS Online Data Processing Addendum (DPA), incorporated into the AWS Customer Agreement since November 2018, which includes Standard Contractual Clauses as a supplementary transfer mechanism.

**Alternative:** If institutional data residency requirements mandate EU-only processing, the system can be redeployed to `eu-west-1` (Ireland). The IAM policy already authorises this region (evidence `EV-IAM-003-policy-proposal-orchestrator-bedrock-invoke.json`). Model availability in `eu-west-1` should be confirmed before migration.

---

## 5. Data Residency

| Data Category | Storage Region | Service | Residency Control |
|---|---|---|---|
| Proposal input data | `us-east-1` | EC2 EBS | Instance deployed in us-east-1 |
| Generated deliverables | `us-east-1` | EC2 EBS | Instance deployed in us-east-1 |
| Bedrock inference data | `us-east-1` (transient) | Bedrock Runtime | IAM region condition (DC-16), VPC endpoint in us-east-1 (DC-01) |
| CloudTrail logs | `us-east-1` | S3 | Bucket in us-east-1, trail is single-region |
| VPC Flow Logs | `us-east-1` | CloudWatch Logs | Log group in us-east-1 |
| Secrets | `us-east-1` | Secrets Manager | Endpoint in us-east-1 |
| KMS key | `us-east-1` | KMS | Key created in us-east-1 |

**Region enforcement:** IAM policy condition `aws:RequestedRegion` restricts Bedrock API calls to `eu-west-1` and `us-east-1` only. An attempt to invoke Bedrock in an unapproved region (tested: `ap-southeast-1`) is denied by both network isolation (no VPC endpoint) and IAM policy (DC-17, evidence `REG-E03-negative-region-test.txt`).

---

## 6. Data Retention

| Data Store | Retention Period | Mechanism | Evidence |
|---|---|---|---|
| CloudTrail logs (S3) | 365 days, archived to Glacier IR after 90 days | S3 lifecycle policy | `CT-E08-s3-lifecycle.json` |
| VPC Flow Logs (CloudWatch) | 90 days | CloudWatch Logs retention setting | `CG_8_logs.txt` lines 79-90 |
| Bedrock inference data | Zero retention | AWS Bedrock Service Terms, Section 50.3 | AWS contractual guarantee |
| Secrets Manager secret | Indefinite (until explicitly deleted) | Manual management | Assumption — no automated deletion policy configured |
| EC2 host data (proposals, deliverables) | Indefinite (until instance terminated or data deleted) | Manual management | Assumption — no automated retention policy on EBS |

**Assumption:** Retention of proposal input data and generated deliverables on the EC2 host is managed by the operator. No automated deletion policy is configured for the host filesystem. Institutional records management policies should be applied to determine appropriate retention periods for proposal preparation artefacts.

---

## 7. GDPR Considerations

### 7.1 Data Controller

The institution operating the Proposal Orchestrator (e.g., the university preparing the Horizon Europe proposal) is the data controller for any personal data processed by the system. The institution determines the purposes and means of processing.

### 7.2 AWS as Processor

Amazon Web Services acts as a data processor. The processing relationship is governed by:

- The AWS Customer Agreement.
- The AWS Online Data Processing Addendum (DPA), which supplements the Service Terms with GDPR-specific commitments including data processing roles, sub-processor obligations, and data transfer mechanisms.
- No separate DPA acceptance is required; the terms are incorporated by default since November 2018 (DC-39, evidence `COMP-E01-gdpr-dpa-assessment.txt`).

### 7.3 Bedrock Usage and Data Protection

Amazon Bedrock processes proposal data transiently during inference. The following protections apply:

- **Zero retention:** Input prompts and output completions are not stored by AWS Bedrock after the API response is returned (AWS Bedrock Service Terms, Section 50.3).
- **No model training:** Model invocation data is not used to train or improve foundation models.
- **Private network transit:** All inference traffic traverses AWS PrivateLink within the private network; no data crosses the public internet.
- **No prompt logging:** Bedrock invocation logging is explicitly disabled (DC-28). CloudTrail records only event metadata, not prompt or response content.

### 7.4 Encryption

All data at rest within the system boundary is encrypted:

| Data Store | Encryption | Key Management |
|---|---|---|
| Secrets Manager | AES-256 via KMS | Customer-managed key (`alias/proposal-orchestrator`) |
| CloudTrail S3 bucket | AES-256 via KMS | Customer-managed key |
| CloudWatch Logs | AES-256 via KMS | Customer-managed key |
| EC2 EBS volume | AES-256 | AWS-managed EBS encryption key (default) |

Data in transit is encrypted via TLS 1.3 (verified in CloudTrail event records, evidence `CT-E06-bedrock-converse-events.json`).

### 7.5 Auditability

The system provides an auditable record of all Bedrock API invocations through:

- **CloudTrail events** capturing caller identity, timestamp, source IP (VPC private IP), VPC endpoint ID, model ID, and TLS version for every Bedrock Converse call.
- **VPC Flow Logs** recording all network traffic on the deployment subnets.
- **Log integrity verification** via CloudTrail log file validation (DC-24).
- **Tamper-evident trail storage** via S3 bucket versioning and deny-unencrypted-object policy.

### 7.6 Access Control

Access to the processing environment is restricted by:

- **IAM identity authentication** for all AWS API interactions.
- **SSM Session Manager** for host access (no SSH, no inbound ports).
- **IAM permission boundary** limiting the Bedrock role to invoke, decrypt, and identity operations only (DC-12).
- **Explicit deny statements** preventing the Bedrock role from accessing non-Bedrock services (S3, EC2, IAM, Lambda, SQS, SNS, DynamoDB) (DC-11).
- **Resource-level policies** on the Secrets Manager secret restricting access to named roles (DC-21).

### 7.7 Data Subject Rights

If personal data of consortium partners or researchers is processed:

- **Right of access / rectification / erasure:** The operator can modify or delete the relevant Tier 3 input files on the EC2 host.
- **Right to restriction of processing:** The operator can remove specific data from the input files before executing the orchestrator.
- **Data portability:** Input data is stored in structured JSON and Markdown files that can be exported.

The institution's data protection officer should assess whether a Data Protection Impact Assessment (DPIA) is required under Article 35 GDPR, taking into account the limited scope and incidental nature of personal data processing.

---

## 8. Conclusion

The Proposal Orchestrator deployment on AWS Bedrock implements a data protection architecture that is appropriate for controlled institutional proposal preparation activities. The key properties of the architecture are:

1. **Private network isolation.** All data transfers between the EC2 host and AWS services occur through VPC endpoints within a private network. No traffic traverses the public internet. This is verified by route table configuration, security group rules, DNS resolution evidence, and CloudTrail source IP records.

2. **Zero-retention inference.** Amazon Bedrock's contractual zero-retention guarantee ensures that proposal data is not stored by the inference service after each API call completes. Bedrock invocation logging is explicitly disabled to prevent prompt content from being recorded in CloudWatch or S3.

3. **Encryption at rest.** All stored data (secrets, CloudTrail logs, VPC Flow Logs) is encrypted with a customer-managed KMS key with automatic annual rotation.

4. **Least-privilege access.** IAM policies, permission boundaries, and explicit deny statements restrict the Bedrock execution role to the minimum required operations. Instance profile authentication eliminates the need for long-term access keys.

5. **Audit trail.** CloudTrail provides a tamper-evident, KMS-encrypted record of all Bedrock API invocations with caller identity and VPC endpoint attribution.

6. **Minimal personal data.** The system processes institutional and project-level data. Personal data processing is incidental, limited to named researchers in consortium descriptions, and can be controlled by the operator through input data preparation.

**This architecture is suitable for institutional use in the preparation of Horizon Europe proposals, subject to the institution's own data governance policies and any additional requirements imposed by institutional data protection officers.**

---

*Document prepared for GDPR-oriented internal compliance review. Evidence references cite artefacts from the CG1-CG10 hardening programme. Assumptions are explicitly marked where evidence is not available.*
