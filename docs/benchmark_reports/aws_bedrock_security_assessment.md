# AWS Bedrock Security Assessment

Provider security qualification matrix for AWS Bedrock, assessed against Proposal Orchestrator backend requirements.

Sources:
- Amazon Bedrock User Guide (2026) -- Bedrock-specific APIs, endpoints, IAM policy examples, VPC PrivateLink
- Choosing AWS security, identity, and governance services (AWS Decision guide, December 30, 2024)
- AWS Identity and Access Management User Guide (2026)
- What are Foundation Models? (AWS, 2026)
- AWS Service Authorization Reference

---

## Security Matrix

| Requirement | Required by Proposal Orchestrator | Pass/Gap | AWS Bedrock Evidence |
|---|---:|---|---|
| Zero data retention | Mandatory | PASS | AWS Bedrock does not store or log customer prompts or completions by default. Data is processed in-region and not retained after the API response. Customer controls opt-in logging via CloudWatch. No data is used for model training unless explicitly opted in. |
| Training opt-out default | Mandatory | PASS | AWS Bedrock does not use customer inputs or outputs to train foundation models. Training use requires explicit customer opt-in. This applies to all models available through Bedrock including third-party models (Claude, Llama, etc.). |
| Data residency controls | Preferred/Institutional | PASS | AWS operates in 30+ regions globally including multiple EU regions (eu-west-1, eu-central-1, etc.). Bedrock API calls are processed in the selected region. IAM policies can enforce region restrictions via `aws:RequestedRegion` condition keys. Data never leaves the selected region unless the customer configures cross-region replication. |
| Private networking / VPC / PrivateLink | Preferred | PASS | AWS security guide documents VPC, AWS Network Firewall ("stateful, managed network firewall and intrusion detection and prevention service with your VPC"), and AWS PrivateLink. Bedrock supports VPC endpoints via PrivateLink, enabling API calls that never traverse the public internet. |
| API key scope isolation | Mandatory | PASS | IAM User Guide documents "secure, fine-grained control over access to AWS workload resources." Supports identity-based policies, resource-based policies, ABAC, RBAC, least-privilege permissions, and permissions boundaries. Bedrock actions can be scoped to specific models, regions, and operations via IAM policy conditions. |
| Auditability | Mandatory | PASS | AWS security guide documents CloudTrail ("records actions taken by a user, role, or AWS service" as an audit trail), AWS Audit Manager ("continuously audit your AWS usage to simplify how you assess risk and compliance"), AWS Config ("detailed view of the configuration of AWS resources"). All Bedrock API calls are logged in CloudTrail. |
| OpenAI-compatible API | Mandatory | PASS | Bedrock UG (p.1111-1115): The `bedrock-mantle.{region}.amazonaws.com` endpoint supports OpenAI-compatible Responses API and Chat Completions API. The UG explicitly states: "Migrating from OpenAI API-compatible endpoint: Use OpenAI-compatible APIs: Responses API or Chat Completions API." The `bedrock-runtime` endpoint also supports Chat Completions alongside native Converse/Invoke APIs. VPC interface endpoints (PrivateLink) are explicitly recommended for keeping traffic within the AWS network. |
| Structured outputs/function support | Mandatory | PASS | Bedrock Converse API supports tool use (function calling) for supported models including Claude and Llama. JSON mode / structured output is available. Claude 3.5 Sonnet, Claude 3 Opus, and Llama models are listed as available foundation models. |
| Model routing transparency | Preferred | PASS | Bedrock model IDs are explicit and region-scoped (e.g., `anthropic.claude-3-sonnet-20240229-v1:0`). Caller selects the exact model. No opaque routing or silent model substitution. Provisioned Throughput reserves dedicated capacity for a specific model. |
| Contractual DPA availability | Mandatory institutional requirement | PASS | AWS security guide documents AWS Artifact which "provides on-demand downloads of AWS security and compliance documents." The AWS GDPR DPA is available as a self-service download via AWS Artifact. No sales contact required. |
| GDPR posture | Mandatory institutional requirement | PASS | AWS security guide explicitly references GDPR as a supported compliance standard. "AWS Compliance Programs provides information about the certifications, regulations, and frameworks that AWS aligns with." AWS operates EU regions with full data residency. DPA available via AWS Artifact. AWS publishes subprocessor lists. |
| Data outflow prevention compatibility | Mandatory | PASS | VPC endpoints (PrivateLink) ensure Bedrock API calls never leave the AWS network. AWS Network Firewall provides stateful inspection at the VPC boundary. Combined with IAM region-locking and CloudTrail logging, data outflow can be prevented and monitored at every layer. |

---

## Summary

| Verdict | Count | Requirements |
|---------|------:|---|
| PASS | 12 | Zero data retention, Training opt-out default, Data residency controls, Private networking / VPC / PrivateLink, API key scope isolation, Auditability, OpenAI-compatible API, Structured outputs/function support, Model routing transparency, Contractual DPA availability, GDPR posture, Data outflow prevention compatibility |
| GAP | 0 | -- |

### Key Findings

- AWS Bedrock passes all 12 of 12 requirements. It is the only evaluated provider with a clean sheet.
- The `bedrock-mantle` endpoint provides OpenAI-compatible Responses API and Chat Completions API, eliminating the previously identified API compatibility gap. This means the same OpenAI-compatible backend adapter built for Together AI in Phase E can be reused for Bedrock with only an endpoint/auth change.
- The security and institutional posture is the strongest of any evaluated provider. IAM, CloudTrail, VPC/PrivateLink, region-level data residency, and self-service DPA via AWS Artifact address every institutional requirement without requiring sales contact.
- Bedrock-specific IAM policies support model-level access control via ARN-scoped Deny/Allow policies (e.g., `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0`).

### Actions Required Before Production Use

1. Select target AWS region(s) for Bedrock deployment (EU regions for data residency).
2. Configure VPC endpoint for Bedrock via PrivateLink.
3. Create scoped IAM policies for Bedrock access (least-privilege, model-restricted).
4. Enable CloudTrail logging for Bedrock API calls.
5. Download and execute GDPR DPA via AWS Artifact.
6. Confirm model availability in the selected region (not all models are available in all regions).
7. Validate OpenAI-compatible Chat Completions API on `bedrock-mantle` endpoint against orchestration workloads.

---

## Comparative Assessment: AWS Bedrock vs Together AI

### Scorecard

| Requirement | Together AI | AWS Bedrock | Advantage |
|---|---|---|---|
| Zero data retention | PASS | PASS | Equivalent |
| Training opt-out default | PASS | PASS | Equivalent |
| Data residency controls | GAP | PASS | AWS |
| Private networking / VPC / PrivateLink | GAP | PASS | AWS |
| API key scope isolation | PARTIAL | PASS | AWS |
| Auditability | PARTIAL | PASS | AWS |
| OpenAI-compatible API | PASS | PASS | Equivalent |
| Structured outputs/function support | PASS | PASS | Equivalent |
| Model routing transparency | PASS | PASS | Equivalent |
| Contractual DPA availability | GAP | PASS | AWS |
| GDPR posture | PARTIAL | PASS | AWS |
| Data outflow prevention compatibility | PARTIAL | PASS | AWS |

### Totals

| Verdict | Together AI | AWS Bedrock |
|---------|------:|------:|
| PASS | 5 | 12 |
| PARTIAL | 4 | 0 |
| GAP | 3 | 0 |

### Analysis

**AWS Bedrock passes all 12 requirements.** With the discovery of the `bedrock-mantle` OpenAI-compatible endpoint (Responses API and Chat Completions API), the previously identified API compatibility gap is eliminated. AWS Bedrock is now the only evaluated provider with a clean sheet across all security, compliance, and technical requirements.

**Together AI remains useful for rapid Phase E iteration** due to its simple `base_url` + `api_key` swap pattern and per-token serverless pricing with no provisioning overhead. However, it has 3 GAPs and 4 PARTIALs that make it unsuitable for institutional production deployment without enterprise contract negotiation.

**The two providers now differ primarily on security posture, not on API compatibility:**

- **Together AI**: OpenAI-compatible (PASS), but lacks VPC/PrivateLink (GAP), data residency (GAP), DPA (GAP), fine-grained access control (PARTIAL), audit trails (PARTIAL), GDPR certification (PARTIAL), and data outflow prevention (PARTIAL).

- **AWS Bedrock**: OpenAI-compatible via `bedrock-mantle` (PASS), plus VPC/PrivateLink (PASS), data residency (PASS), DPA (PASS), IAM (PASS), CloudTrail (PASS), GDPR (PASS), and data outflow prevention (PASS).

**Revised recommended sequencing:**

1. Phase E: Build OpenAI-compatible backend abstraction.
2. Validate on Together AI for rapid iteration (low cost, no provisioning, simple auth).
3. Validate on AWS Bedrock `bedrock-mantle` endpoint using the same OpenAI-compatible backend -- the adapter should work with minimal changes (endpoint URL + AWS Signature V4 auth instead of Bearer token).
4. Production: Route through AWS Bedrock for institutional deployments requiring closed-network / GDPR / DPA compliance.
5. Together AI remains available for development, testing, and non-sensitive workloads.

**Key implication for Phase E design:** Since both Together AI and AWS Bedrock now support the OpenAI Chat Completions API, the Phase E transport abstraction does not need a Bedrock-specific adapter. A single OpenAI-compatible backend with configurable endpoint URL and auth mechanism covers both providers. The primary auth difference is that Together AI uses a Bearer token while Bedrock uses AWS Signature V4 (or API keys via the `bedrock-mantle` endpoint).

### Caveat

The Bedrock data retention and training opt-out assessments are based on well-known AWS Bedrock platform properties. The OpenAI-compatible API assessment is directly evidenced by the Bedrock User Guide (p.1111-1115), which documents the `bedrock-mantle` endpoint, Chat Completions API, Responses API, and explicit migration guidance for OpenAI API users. VPC PrivateLink support for Bedrock is directly documented in the Bedrock UG (p.1113): "consider using VPC interface endpoints (AWS PrivateLink) to keep traffic within the AWS network."
