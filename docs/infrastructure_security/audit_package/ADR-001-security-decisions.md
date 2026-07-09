# ADR-001 — Security Architecture and Deployment Decisions

| Field | Value |
|---|---|
| ADR ID | ADR-001 |
| Title | Security Architecture and Deployment Decisions |
| Status | Accepted |
| Date | 2026-06-03 |
| Scope | Production inference provider selection, network architecture, identity management, secret storage, encryption key governance, audit infrastructure, data egress prevention, deployment strategy, transport abstraction |
| Supersedes | None |
| Related documents | `security_architecture_diagram.md`, `data_flow_document.md`, `risk_acceptance_register.md`, `operational_procedure.md`, `aws_deployment_hardening_plan.md`, `aws_hardening_control_register.md` |

---

## Executive Summary

The Proposal Orchestrator processes institutional intellectual property — Horizon Europe proposal concepts, consortium details, work package designs, impact narratives, and evaluator-facing deliverable text. The security architecture must prevent this data from leaving a controlled environment through infrastructure misconfiguration, application-level vulnerability, or operator error, while remaining auditable and suitable for institutional review.

This document records the nine principal architecture and security decisions that shaped the production deployment. Each decision identifies the alternatives considered, the rationale for the selected approach, and the trade-offs accepted.

The resulting architecture routes all LLM inference through Amazon Bedrock via AWS PrivateLink within a private VPC that has no internet route, authenticates through IAM instance profiles with no long-term credentials, encrypts all stored artefacts with a customer-managed KMS key, and produces a tamper-evident audit trail through CloudTrail. The application layer enforces production-only backend selection, prevents prompt and response content from being written to disk, and sanitises error messages to prevent content leakage.

Forty-one infrastructure controls across ten control groups have been defined, implemented, and verified. Thirty-eight controls pass verification. Two are not applicable to the deployed configuration. One is deferred pending full DAG execution on the production host.

---

## Decision 1 — AWS Bedrock as Production Inference Provider

### Context

The Proposal Orchestrator requires access to a large language model capable of structured reasoning over call documents, proposal architectures, and evaluation criteria. The system was initially developed using the Claude CLI (`claude -p`) as its inference transport — a convenience path that routes requests through Anthropic's infrastructure via the operator's personal subscription.

For institutional deployment, this path is unsuitable. Proposal data constitutes institutional IP. The inference provider must offer network isolation, identity-based access control, audit logging, and a contractual data handling framework compatible with EU institutional requirements.

### Alternatives Considered

**Claude CLI (baseline).** The development transport. Invocations route through Anthropic's public API infrastructure. The operator authenticates via a personal Claude Code Max subscription. There is no network isolation, no IAM integration, no audit trail beyond local logs, and no contractual framework between the institution and Anthropic for data processed through this path. The CLI binary itself is a data egress vector: it can reach arbitrary Anthropic endpoints from any host where it is installed.

**Together AI.** Evaluated as a validation backend during transport layer development (preset `TOGETHER_VALIDATION`). Together AI provides an OpenAI-compatible API endpoint. Data transits the public internet to US-based infrastructure. There is no PrivateLink equivalent, no IAM integration, and no zero-retention guarantee equivalent to Bedrock's. The service was useful for validating the transport abstraction's multi-backend capability but is not production-suitable for institutional IP.

**Self-hosted models (Ollama, vLLM, TGI).** A comprehensive migration plan (`docs/internal_llm_migration_plan.md`, 1,844 lines, dated 2026-05-18) evaluates closed-network deployment using locally-hosted models such as Qwen3-32B. This path offers complete data sovereignty — no data leaves the institution's own infrastructure. However, it introduces substantial operational complexity: GPU server provisioning, model hosting, mTLS configuration, capacity management, and the expectation of reduced output quality on smaller models. The migration plan recommends a hybrid approach where local models handle structured extraction skills while Claude-class models handle semantic reasoning. This path remains a strategic option but is not ready for production. The preset `OLLAMA_LOCAL` exists in the transport configuration for pilot evaluation.

**Amazon Bedrock (selected).** Bedrock provides native AWS infrastructure integration: VPC PrivateLink for private network transit, IAM for identity-based access control, CloudTrail for API-level audit logging, and a contractual zero-retention guarantee (AWS Bedrock Service Terms, Section 50.3) ensuring that input prompts and output completions are not stored after the API response is returned and are not used for model training. The Converse API provides a structured message format with tool calling support, which the skill runtime uses directly through boto3.

### Rationale

Bedrock was selected because it satisfies four requirements simultaneously:

1. **PrivateLink support.** All inference traffic can be routed through a VPC interface endpoint, eliminating public internet transit. No other evaluated provider offers an equivalent private network path.

2. **IAM integration.** Authentication uses the standard AWS credential chain — instance profiles, role assumption, temporary credentials. No API keys need to be stored, rotated, or transmitted. The Bedrock execution role can be scoped to specific actions, models, and regions through standard IAM policy syntax.

3. **Institutional suitability.** AWS provides a contractual framework (Customer Agreement, Online DPA) that EU institutions can evaluate through established procurement and data governance processes. The zero-retention guarantee addresses the primary data protection concern: that proposal IP is not retained by the inference provider.

4. **Auditability.** Every Bedrock API call is recorded in CloudTrail with caller identity, timestamp, source IP, VPC endpoint ID, model ID, and TLS version. This produces the audit trail required for institutional security review without logging prompt or response content.

### Trade-offs

- **Vendor dependency.** The institution depends on AWS for inference availability. A regional Bedrock outage would interrupt proposal preparation. This is accepted as RSK-05 in the risk register, mitigated by the IAM policy authorising both `us-east-1` and `eu-west-1`.
- **Model availability risk.** Anthropic model availability on Bedrock is subject to AWS's model onboarding process. Model deprecation or capacity constraints could require reconfiguration. This is accepted as RSK-06.
- **Cost opacity.** Bedrock pricing is per-token. The Phase 1 smoke test consumed approximately 438,839 tokens in 6 minutes. Full DAG runs across 8 phases will consume substantially more. Cost projection is documented in the benchmark framework but is not yet computed for full runs.

### Evidence

- Production smoke test: `docs/benchmark_reports/smoke-phase1-001/run_benchmark_summary.json` — 16 invocations, 0 failures, 366.7 seconds.
- Model availability verification: DC-36, evidence `CG9_logs.txt`.
- Transport preset definition: `runner/transport/config.py`, preset `BEDROCK_CONVERSE_US`.

---

## Decision 2 — PrivateLink Instead of Public Internet Access

### Context

The standard method of accessing Amazon Bedrock is through its public API endpoint (`bedrock-runtime.<region>.amazonaws.com`), which resolves to public IP addresses and routes traffic over the public internet with TLS encryption.

For a system processing institutional proposal IP, the question is whether TLS encryption in transit is sufficient, or whether the network path itself must be private.

### Alternatives Considered

**Public API with TLS.** The Bedrock public endpoint encrypts all traffic with TLS. Data confidentiality in transit depends on the TLS implementation. This approach is simpler to configure — no VPC endpoints, no private DNS, no endpoint security groups. However, traffic traverses the public internet, which introduces exposure to network-level observation (metadata, traffic analysis) and requires the deployment host to have an internet route, which in turn creates a potential data egress path.

**VPC Interface Endpoint with PrivateLink (selected).** A VPC interface endpoint creates elastic network interfaces within the VPC's private subnets. With private DNS enabled, the standard Bedrock API hostname resolves to these private IPs. Traffic between the EC2 host and Bedrock never leaves the AWS private network backbone. The host does not require an internet route.

### Rationale

PrivateLink was selected for two reasons:

1. **Elimination of the internet route.** With PrivateLink, the deployment subnet's route table requires no Internet Gateway or NAT Gateway route. This removes the primary data egress vector. The host cannot reach the public internet regardless of application-level misconfiguration, compromised dependencies, or operator error. This is the single most consequential security control in the architecture.

2. **Reduction of the trust boundary.** With the public API, the operator must trust that TLS is correctly implemented end-to-end and that no intermediary can observe traffic metadata. With PrivateLink, traffic remains within the AWS network backbone. The trust boundary is reduced to the AWS infrastructure itself, which is the same boundary the institution already trusts for compute and storage.

### Trade-offs

- **Operational complexity.** PrivateLink requires provisioning VPC endpoints, configuring private DNS, creating dedicated security groups, and managing endpoint policies. Seven VPC endpoints are deployed in the current architecture (Bedrock, Secrets Manager, STS, S3, SSM x3). Each requires its own availability monitoring.
- **Cost.** VPC interface endpoints incur hourly charges and per-GB data processing fees. These are modest for the expected traffic volume but are a recurring cost absent from the public API approach.
- **Air-gap deployment constraints.** The absence of internet access means that standard package management (`dnf`, `pip install` from PyPI) does not work on the host. This necessitated the offline deployment bundle approach (Decision 8).

### Evidence

- VPC endpoint state: DC-01, evidence `EV-PL-001-vpc-endpoints.json`.
- Private DNS resolution to VPC-internal IPs: DC-02, evidence `EV-PL-005-private-dns-resolution.txt` (172.31.27.207, 172.31.80.15).
- Route table with no internet route: DC-06, evidence `EV-PL-006-route-table.json`.
- Endpoint security group restricting to TCP 443 from host SG only: DC-03, evidence `EV-PL-003-vpce-security-group.json`.
- CloudTrail events confirming private source IP and VPC endpoint attribution: DC-26, evidence `CT-E06-bedrock-converse-events.json`.

---

## Decision 3 — IAM Roles Instead of Static API Keys

### Context

Access to Amazon Bedrock requires AWS credentials. The two standard approaches are static access keys (long-lived `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` pairs) and IAM roles assumed through the instance metadata service (instance profiles for EC2, task roles for ECS).

### Alternatives Considered

**Static access keys.** An IAM user is created, an access key pair is generated, and the keys are stored on the deployment host — typically in `~/.aws/credentials`, environment variables, or a `.env` file. This approach is simple to configure but introduces several risks: the keys do not expire unless explicitly rotated, they can be extracted from the filesystem by anyone with host access, they can be accidentally committed to version control, and their compromise grants persistent access until revocation.

**IAM instance profile (selected).** An IAM role is created with the required permissions. An instance profile binds the role to the EC2 instance. The instance metadata service provides temporary credentials (with automatic rotation) to any process running on the instance. No access key pair is stored anywhere on the host.

### Rationale

Instance profiles were selected because they eliminate the credential lifecycle problem entirely:

1. **No stored credentials.** There are no access keys on the filesystem, in environment variables, or in application configuration. The `sts get-caller-identity` output from the host shows a role assumption ARN, not an access key ID (DC-14, DC-15).

2. **Automatic rotation.** Temporary credentials obtained through the instance metadata service expire and are refreshed automatically. The application (boto3) handles this transparently. There is no rotation procedure for the operator to manage.

3. **Scoped role assumption.** The instance profile role (`proposal-orchestrator-ec2-ssm-role`) is distinct from the Bedrock execution role (`proposal-orchestrator-bedrock-role`). The Bedrock role has a permission boundary (`proposal-orchestrator-boundary`) that caps its maximum scope to Bedrock invoke, Secrets Manager get, KMS decrypt, and STS identity operations (DC-12). The role's trust policy restricts assumption to the EC2 service (DC-13).

4. **Defence in depth.** Even if the role's allow policies were misconfigured, explicit deny statements block Bedrock administration actions, access to non-Bedrock services (EC2, S3, IAM, Lambda, SQS, SNS, DynamoDB), and invocation of non-Claude models (DC-11). IAM simulation tests verify both allowed and denied paths.

### Trade-offs

- **Instance-bound access.** Credentials are only available on the specific EC2 instance. This is a constraint, not a deficiency — it means Bedrock access cannot be exercised from any other location without separate authorisation.
- **Trust policy design.** The trust policy does not include an `aws:SourceVpc` condition because the EC2 instance metadata service does not traverse VPC endpoints. This is a deliberate design choice, documented in the control register. Compensation is provided by the security-group-to-security-group binding and private subnet isolation.

### Evidence

- Role configuration: DC-09, evidence `EV-IAM-001-role-config.json`.
- Permission boundary: DC-12, evidence `EV-IAM-004-boundary-metadata.json`, `EV-IAM-003-policy-proposal-orchestrator-boundary.json`.
- Explicit deny statements: DC-11, evidence `EV-IAM-003-policy-proposal-orchestrator-explicit-deny.json`.
- Caller identity (role assumption, no access key): DC-14, evidence `IAM_Least_Privilege_logs.txt` lines 805-808.
- IAM simulation (allowed): `EV-IAM-005-sim-allowed-invoke.json` — `EvalDecision: "allowed"`.
- IAM simulation (denied admin): `EV-IAM-006-sim-denied-admin.json` — `EvalDecision: "explicitDeny"`.
- IAM simulation (denied non-Claude): `EV-IAM-007-sim-denied-non-claude.json` — `EvalDecision: "explicitDeny"`.

---

## Decision 4 — Secrets Manager Instead of .env Files

### Context

The application requires five configuration values at runtime: transport preset, production mode flag, diagnostic level, AWS region, and model ID. These values determine which backend the application uses, whether it writes prompt content to disk, and which model it invokes. Misconfiguration of any value can weaken the security posture.

### Alternatives Considered

**Local `.env` files.** The development workflow uses `python-dotenv` to load environment variables from `.env` files. This is convenient for development but unsuitable for production: `.env` files are plaintext, their access is controlled only by filesystem permissions, there is no audit trail for reads, and they cannot be centrally managed across multiple deployment instances.

**AWS Secrets Manager (selected).** Configuration values are stored in a single secret (`proposal-orchestrator/env-config`) encrypted with the customer-managed KMS key. Access is controlled by a resource policy scoped to two named IAM roles. Retrieval is logged in CloudTrail. The secret can be updated centrally without modifying the host filesystem.

### Rationale

1. **Encryption at rest.** The secret is encrypted with the customer-managed KMS key (`alias/proposal-orchestrator`), not the default `aws/secretsmanager` key. This provides full key policy control and rotation governance (DC-20).

2. **Access control.** The resource policy permits `GetSecretValue` and `DescribeSecret` for only two roles: `proposal-orchestrator-bedrock-role` and `proposal-orchestrator-ec2-ssm-role`. No wildcards are used (DC-21).

3. **Auditability.** Every retrieval of the secret is recorded in CloudTrail, providing a verifiable record of when configuration was accessed and by which identity.

4. **Centralised management.** If the deployment scales to multiple instances, the secret provides a single source of truth for configuration. Value changes propagate without host-level file modifications.

### Trade-offs

- **Network dependency.** Secret retrieval requires a functioning VPC endpoint to Secrets Manager (`vpce-08ba482a3b11f7d64`). If this endpoint is unavailable, the application cannot start. This is accepted as part of the VPC endpoint dependency set.
- **No automatic rotation.** The current secret contains configuration values, not API keys. Automatic rotation (DC-22) is not applicable because the values are not credentials. If API key secrets are introduced in the future, rotation must be configured.
- **Deviation from strict deny pattern.** The resource policy uses an Allow-only pattern (two Allow statements for named roles) rather than the more restrictive NotPrincipal Deny pattern. This is a practical deviation documented in the control register as adequate security for the current single-account, two-role configuration.

### Evidence

- Secret with CMK encryption: DC-20, evidence `SM-E01-secrets-list.json`, `SM-E03-kms-key-association.txt`.
- Resource policy: DC-21, evidence `SM-E04-resource-policy.json`.
- Retrieval test from host: `SM-E06-retrieval-test.txt`.

---

## Decision 5 — Customer-Managed KMS Key

### Context

Multiple AWS services in this architecture store data at rest: Secrets Manager (configuration values), CloudTrail (API event logs via S3), and CloudWatch Logs (VPC Flow Logs). Each service offers default encryption with an AWS-managed key (`aws/<service-name>`). The question is whether this default is sufficient or whether a customer-managed key is warranted.

### Alternatives Considered

**AWS-managed keys (default).** Each service encrypts data with its own AWS-managed key. Key rotation is handled by AWS. Key policies are not editable. The institution cannot control which principals may use the key, cannot audit key usage through its own KMS event trail, and cannot revoke access by modifying the key policy. If the institution needs to prove to an auditor that encryption keys are under institutional control, AWS-managed keys are insufficient.

**Customer-managed key (selected).** A single symmetric CMK (`887638e8-358b-4664-9270-368aec0ea1f1`, alias `proposal-orchestrator`) is created with an explicit key policy. The key is used across all three services. Automatic rotation is enabled with a 365-day period.

### Rationale

1. **Institutional key governance.** The key policy contains four explicit statements: root account full access (lockout prevention), Bedrock role usage (Decrypt + DescribeKey), CloudTrail encryption (GenerateDataKey with SourceArn scope), and CloudWatch Logs encryption (scoped to `/proposal-orchestrator/*` log groups). No other principals can use the key (DC-19).

2. **Auditability.** All key usage events (Decrypt, GenerateDataKey, DescribeKey) are logged in CloudTrail. An auditor can verify which principals used the key, when, and for which service.

3. **Revocability.** If the institution needs to deny all access to encrypted data, modifying the key policy achieves this without needing to contact each downstream service individually. This is a capability not available with AWS-managed keys.

4. **Rotation governance.** Automatic rotation is enabled and verifiable. The rotation period (365 days) and next rotation date (2027-06-01) are recorded in evidence (DC-18). With AWS-managed keys, rotation occurs but is not independently verifiable.

### Trade-offs

- **Key deletion risk.** Accidental deletion or scheduling for deletion of the CMK would render all encrypted data permanently inaccessible. KMS enforces a minimum 7-day waiting period, and the key policy includes root full access to prevent lockout. This is accepted as RSK-15 in the risk register, rated low residual risk.
- **Single key for multiple services.** Using one key across Secrets Manager, CloudTrail, and CloudWatch simplifies management but means that any principal with Decrypt permission can potentially decrypt data from all three services. The key policy limits Decrypt to the Bedrock role only; CloudTrail and CloudWatch have GenerateDataKey permissions scoped by SourceArn and log group prefix respectively.

### Evidence

- Key description and rotation: DC-18, evidence `KMS-E01-key-description.json`, `KMS-E02-rotation-status.json`.
- Key policy (4 statements): DC-19, evidence `KMS-E03-key-policy.json`.
- Key alias: `KMS-E04-aliases.json`.

---

## Decision 6 — CloudTrail with Disabled Invocation Logging

### Context

An institutional deployment must produce an auditable record of LLM inference activity. Two distinct logging mechanisms are available in Bedrock: CloudTrail (API event metadata) and Bedrock Model Invocation Logging (full prompt and response content to CloudWatch or S3).

### Alternatives Considered

**Bedrock Model Invocation Logging (rejected).** This feature logs the full content of prompts and responses to CloudWatch Logs or an S3 bucket. Enabling it would create a persistent copy of all proposal IP — the exact data the architecture is designed to protect. The zero-retention guarantee provided by Bedrock would be negated by the institution's own logging configuration. This option was rejected as architecturally contradictory.

**CloudTrail only (selected).** CloudTrail records API event metadata: event name, caller identity (IAM role ARN), source IP address, VPC endpoint ID, timestamp, TLS version, model ID, HTTP status code. It does not record prompt or response content. This provides auditability of who invoked which model, when, and from where, without persisting the data that the architecture is designed to protect.

### Rationale

The architecture's data protection objective requires two properties simultaneously: (a) an audit trail that proves every inference call was authorised, attributable, and routed through the private network, and (b) no persistent copy of proposal content in any AWS service after each call completes. CloudTrail satisfies both. Invocation logging satisfies (a) but violates (b).

Complementary controls:

- **Log file validation** is enabled for integrity verification (DC-24). Digest files allow detection of log tampering.
- **Trail S3 bucket** is secured with a four-statement bucket policy (AclCheck, Write with SourceArn, DenyUnencryptedObjects, DenyInsecureTransport), versioning, and a lifecycle policy archiving to Glacier IR after 90 days and expiring after 365 days (DC-25, DC-27).
- **VPC Flow Logs** on both deployment subnets capture all network-level traffic metadata, providing a secondary audit source for network activity (DC-08).

### Trade-offs

- **No prompt-level audit.** If an incident investigation requires determining what was sent to Bedrock during a specific invocation, CloudTrail cannot answer that question. The institution accepts this as the cost of not persisting proposal content. The application's diagnostic metadata (character counts, timing, error classifications) provides limited forensic context.
- **Flow Log limitations.** VPC Flow Logs record source/destination IP, port, protocol, and byte count. They do not record application-layer data. They confirm that traffic occurred between the host and the VPC endpoint but cannot characterise its content.

### Evidence

- Trail configuration and active logging: DC-23, evidence `CT-E01-trail-configuration.json`, `CT-E02-trail-status.json`.
- KMS encryption: `CT-E04-kms-encryption.txt`.
- Converse events captured with caller identity and VPC endpoint attribution: DC-26, evidence `CT-E06-bedrock-converse-events.json`.
- Invocation logging confirmed disabled: DC-28, evidence `CG7_logs.txt`.
- No `/aws/bedrock` log groups: DC-29, evidence `CG7_logs.txt`.
- VPC Flow Logs active on both subnets: DC-08, evidence `EV-DEP-003-flow-logs-subnet-a.json`.

---

## Decision 7 — Defence-in-Depth Data Egress Prevention

### Context

The primary threat to institutional proposal IP is data exfiltration — proposal content leaving the controlled environment through a network path, a compromised application dependency, an operator-installed tool, or a misconfigured service. The architecture must make exfiltration structurally infeasible, not merely policy-prohibited.

### Threat Model

| Vector | Description |
|---|---|
| Network egress | Traffic routed to public internet via IGW, NAT, or misconfigured route |
| Application egress | Compromised Python dependency opens outbound connection |
| Tool-based egress | Operator installs Claude CLI or another tool that can reach external endpoints |
| Service egress | Bedrock invocation logging enabled, creating persistent content copies |
| Prompt leakage | Application writes prompt/response content to local disk or log files |

### Controls Implemented

**Network layer:**
- Route table contains no Internet Gateway or NAT Gateway route. Only `local` (172.31.0.0/16) and S3 prefix list (`pl-63a5400a`) entries exist (DC-06).
- Host security group permits TCP 443 egress only to the VPC endpoint security group (`sg-013d5e4d4eb55dfd9`) and the S3 prefix list (`pl-63a5400a`). No `0.0.0.0/0` egress rules exist (DC-07).

**VPC endpoint layer:**
- Endpoint policy on the Bedrock VPC endpoint restricts to `proposal-orchestrator-bedrock-role` and `ec2-ssm-role`, actions `InvokeModel` and `InvokeModelWithResponseStream`, resources `anthropic.claude-*` (DC-04).
- Supporting endpoints (Secrets Manager, STS, S3 gateway, SSM x3) ensure all required service access is private (DC-05).

**IAM layer:**
- Explicit deny statements prevent the Bedrock role from accessing non-Bedrock services. IAM simulation confirms: `s3:ListAllMyBuckets` → `explicitDeny`, `ec2:DescribeInstances` → `explicitDeny`, `iam:ListRoles` → `explicitDeny` (DC-11).
- Region enforcement via `aws:RequestedRegion` condition limits Bedrock calls to `eu-west-1` and `us-east-1` (DC-16). Negative test confirms: `ap-southeast-1` → timeout/deny (DC-17).

**Application layer:**
- `ORCHESTRATOR_PRODUCTION_MODE=true` rejects all non-Bedrock backends (`claude_cli`, `together_ai`, `ollama`, `openai_compatible`). Enforcement is verified by 34 security tests (DC-33).
- `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` prevents prompt and response content from being written to disk. Enforcement is verified by 40 persistence policy tests (DC-35).
- Error message sanitisation truncates exception messages to 200 characters in production, preventing prompt content leakage through error reporting.
- No Claude CLI binary exists on the host (`which claude` → not found, `find / -name claude` → no results) (DC-31).

**S3 gateway exception.** The host security group includes a TCP 443 egress rule to the S3 prefix list (`pl-63a5400a`). This was added post-hardening to enable deployment artefact transfer via the S3 gateway endpoint. The S3 prefix list covers only AWS-owned S3 IP ranges routed internally by the gateway. The route table still has no `0.0.0.0/0` route. The Bedrock execution role's permission boundary does not include `s3:PutObject`, preventing data exfiltration to S3 via the Bedrock role. The `ec2-ssm-role` has broader S3 permissions for deployment operations; this is documented in the deployment guide security impact assessment.

### Trade-offs

- **Operational friction.** The air-gapped host cannot install packages, pull Docker images, or access external documentation. All software must be pre-bundled and transferred via S3 (see Decision 8).
- **S3 residual path.** The `ec2-ssm-role` can write to S3 buckets that its IAM policy permits. This is a controlled residual risk: the role is used for deployment and evidence collection, not by the orchestrator application during inference.

### Evidence

- Route table: `EV-PL-006-route-table.json`.
- Host SG egress rules: `EV-DEP-002-host-sg.json`.
- Endpoint policy: `EV-VPC-004-bedrock-endpoint-policy.json`.
- IAM deny simulations: `EV-IAM-006-sim-denied-s3.json`, `EV-IAM-006-sim-denied-ec2.json`, `EV-IAM-006-sim-denied-iam.json`.
- Negative region test: `REG-E03-negative-region-test.txt`.
- No Claude CLI: `CG_8_logs.txt` lines 92-114.

---

## Decision 8 — Offline Deployment Bundle Instead of Direct Internet Deployment

### Context

Standard deployment patterns for Python applications involve installing dependencies from PyPI at deploy time, pulling Docker images from a registry, or using a CI/CD pipeline with internet access. The hardened host has no internet access by design (Decision 2, Decision 7). This creates a deployment constraint that must be addressed without weakening the network isolation.

### Alternatives Considered

**Docker-based deployment via ECR.** The repository includes a Dockerfile with a multi-stage build (builder + runtime, non-root user). However, Docker cannot be installed on the host because `dnf install` requires access to Amazon Linux 2023 package repositories, which resolve to public S3 URLs unreachable from the private subnet. ECR pull would also require an ECR VPC endpoint not currently provisioned. This path was attempted and abandoned.

**NAT Gateway for package access.** A NAT Gateway would allow the host to reach the public internet for `dnf install` and `pip install`. This directly contradicts Decision 7 — the entire egress prevention architecture depends on the absence of an internet route. Provisioning a NAT Gateway, even temporarily, would create a window during which the host could reach arbitrary internet endpoints.

**S3-based offline bundle (selected).** All Python dependencies are downloaded as platform-specific wheels on the operator's workstation, bundled into a tarball with the application code, uploaded to an S3 bucket, and downloaded to the host through the S3 gateway endpoint. On the host, `python3 -m ensurepip` bootstraps pip from CPython's bundled module (no internet required), and `pip install --no-index --find-links=deploy_deps/` installs all wheels from the local bundle.

### Rationale

1. **Preserves network isolation.** The host never requires internet access. The S3 gateway endpoint routes traffic internally through the AWS backbone. The deployment path is consistent with the production data path — all traffic stays within the private network.

2. **Reproducibility.** The deployment tarball is a self-contained, versioned artefact. The same tarball can be deployed to any host with the same Python version without dependency resolution. There is no risk of PyPI version drift between deployments.

3. **Supply-chain risk reduction.** Dependencies are downloaded once, on the operator's workstation, where they can be inspected or scanned before bundling. The host never contacts PyPI. The dependency set is minimal: boto3, pyyaml, jsonschema, python-dotenv, plus their transitive dependencies (RSK-12 in the risk register).

4. **Auditable.** The contents of the deployment tarball are deterministic and can be listed, hashed, and compared across deployments. The S3 upload and SSM Run Command execution are logged in CloudTrail and SSM logs respectively.

### Trade-offs

- **Manual process.** Deployment requires the operator to build the tarball locally, upload to S3, and invoke an SSM Run Command. This is documented in the operational procedure but is not automated through CI/CD. The lack of CI/CD is a deferred security finding (Phase 2 hardening, P2-4).
- **Platform targeting.** Wheels must be downloaded for the correct platform (`manylinux2014_x86_64`, Python 3.9). If the host platform changes (e.g., ARM migration), the wheel download step must be updated.
- **No Docker.** The production deployment path does not use Docker. The Dockerfile remains available for local development and testing but does not apply to production.

### Evidence

- Deployment guide Sections 4-5: tarball creation, S3 upload, SSM Run Command deployment.
- `deploy_deps/` directory: pre-downloaded wheel files.
- S3 gateway endpoint: DC-05, `vpce-0ee5648ce182bf85a`.
- Host SG S3 prefix list rule: deployment guide Section 2, `sgr-0cc4c7112cd8277c2`.

---

## Decision 9 — Provider-Agnostic Transport Layer

### Context

The system was initially built with a single transport path: the Claude CLI. As institutional deployment requirements were understood, it became clear that the transport layer must support multiple backends without modifying the workflow logic, gate conditions, or skill specifications.

### Design

The transport layer (`runner/transport/`) implements a backend abstraction with the following components:

- **Configuration layer** (`config.py`): Seven named presets, environment variable resolution, production mode enforcement, `ProviderConfig` data contract.
- **Bedrock Converse backend** (`bedrock_converse.py`): Native boto3 Converse API with IAM authentication and tool calling support.
- **OpenAI-compatible backend** (`openai_compatible.py`): HTTP client for `/v1/chat/completions` endpoints supporting Ollama, vLLM, TGI, and similar services.
- **Tool executor** (`tool_executor.py`): Local Read/Glob tool emulation with deterministic path validation, sandbox enforcement, and read budget limits for non-Claude backends.
- **Claude CLI transport** (`claude_transport.py`): The original subprocess-based transport, retained for development use.

The skill runtime (`runner/skill_runtime.py`) resolves the transport backend at invocation time and routes through one of three execution paths (Claude CLI, Bedrock Converse, or OpenAI-compatible), each supporting both cli-prompt and TAPM (Tool-Augmented Prompt Mode) execution modes.

### Rationale

1. **Migration flexibility.** The institution can move between backends without workflow changes. The transition from Claude CLI to Bedrock Converse required no modifications to skill specifications, agent definitions, gate conditions, or the DAG scheduler. Only the environment variable `ORCHESTRATOR_TRANSPORT_PRESET` changed.

2. **Vendor lock-in reduction.** The strategic migration plan (`docs/internal_llm_migration_plan.md`) identifies a path to self-hosted models. The transport abstraction makes this path achievable without re-architecting the system. Ollama and vLLM backends are already implemented and can be selected via preset.

3. **Security boundary enforcement.** The production mode gate (`PRODUCTION_BACKENDS = frozenset(["bedrock_converse", "bedrock"])`) is enforced at the transport configuration layer. The application cannot reach a non-production backend when `ORCHESTRATOR_PRODUCTION_MODE=true`, regardless of what other environment variables are set. This is verified by 34 security tests.

4. **Benchmark validation.** The multi-backend architecture allows the same workload to be executed against different providers for quality and cost comparison. The benchmark framework (`docs/benchmark_reports/`) captures invocation counts, token economics, and timing profiles per provider. The Phase 1 smoke test validates that the production path (Bedrock Converse) produces outputs that pass the gate evaluator.

### Trade-offs

- **Abstraction complexity.** The skill runtime now supports six execution paths (3 backends x 2 modes). Each path has its own prompt assembly, response parsing, and error handling logic. This increases the surface area for transport-layer bugs.
- **Tool executor limitations.** For non-Claude backends, the local tool executor emulates Read and Glob tools with deterministic path validation. This provides stronger sandbox enforcement than prompt-based constraints but requires maintenance as the tool interface evolves.
- **Semantic predicate quality.** The gate evaluator uses LLM-based semantic predicates to evaluate gate conditions. The quality of these evaluations depends on the model's reasoning capability. The migration plan acknowledges that smaller self-hosted models may produce weaker semantic judgments and recommends a hybrid approach where structured extraction uses local models while semantic reasoning uses a Claude-class model.

### Evidence

- Transport presets: `runner/transport/config.py` — 7 presets defined, 2 production-suitable.
- Production mode enforcement: `runner/transport/config.py` — `_enforce_production_backend()`.
- Security tests: `tests/test_production_mode.py` — 34 tests.
- Phase 1 smoke test (Bedrock Converse path): `docs/benchmark_reports/smoke-phase1-001/run_benchmark_summary.json` — 16 invocations, 0 failures.

---

## Residual Risks

The following risks are accepted after the implementation of all security controls. Full details, including likelihood, impact ratings, and mitigation descriptions, are documented in `risk_acceptance_register.md`.

### Model Hallucination (RSK-07)

The language model may generate factually incorrect or unsupported claims in proposal text. The orchestrator's gate-controlled workflow and review packet generation provide structural safeguards, but the ultimate responsibility for content accuracy rests with the human operator. No infrastructure control can prevent a model from producing plausible but incorrect statements. This risk is rated High likelihood, Medium impact, and is classified as Operationally Managed.

### Provider Outage (RSK-05, RSK-06)

An AWS regional outage or Bedrock model unavailability would interrupt proposal preparation. The IAM policy authorises two regions (`us-east-1`, `eu-west-1`), providing a documented fallback path, but region failover is not automated. This risk is rated Low likelihood (RSK-05) and Medium likelihood (RSK-06), with Medium impact, and is classified as Accepted (RSK-05) and Operationally Managed (RSK-06).

### Human Review Dependency (RSK-07, RSK-08, RSK-13)

The system is a preparation tool, not a submission tool. All generated content must be reviewed by the operator before use. The quality of the final proposal depends on the operator's ability to identify errors, verify compliance with call requirements, and correct model-generated content. No automated control substitutes for domain-expert review. These risks are classified as Operationally Managed (RSK-07, RSK-08) and Accepted (RSK-13).

### Configuration Drift (RSK-11)

Infrastructure configurations (security groups, IAM policies, route tables, endpoint policies) may be modified after initial hardening. CloudTrail logs all modification events, and the `collect_evidence.ps1` script enables periodic re-verification against the baseline. However, detection depends on the operator actually running the evidence collection and reviewing the results. This risk is classified as Operationally Managed with monthly review cadence.

### EBS Volume Persistence (RSK-14)

Proposal data persists on the EC2 host's EBS volume until the instance is terminated and the volume is deleted. EBS default encryption is assumed but has not been independently verified in this hardening programme. The `DeleteOnTermination` flag on the root volume has not been confirmed. This risk is classified as Accepted with low residual risk, given that AWS EBS data erasure guarantees are contractual.

---

## Final Architecture Position

The Proposal Orchestrator is deployed on a hardened EC2 instance within a private VPC subnet that has no internet route. All LLM inference traffic reaches Amazon Bedrock through a VPC PrivateLink endpoint that restricts access to a specifically scoped IAM role and Claude model ARNs. The host authenticates through an instance profile with temporary credentials. All stored artefacts are encrypted with a customer-managed KMS key under institutional control. CloudTrail produces a tamper-evident audit trail of every Bedrock API call without persisting prompt content. The application enforces production-only backend selection, prevents content persistence, and sanitises error messages.

This architecture was selected because no evaluated alternative simultaneously satisfies the four institutional requirements:

1. **Private network transit.** PrivateLink eliminates public internet exposure for inference traffic. No other evaluated provider offers this capability.

2. **Identity-based access control.** IAM roles, permission boundaries, and explicit deny statements enforce least-privilege access without static credentials. The approach is native to the AWS infrastructure the institution already operates within.

3. **Zero content retention.** Bedrock's contractual zero-retention guarantee, combined with disabled invocation logging and metadata-only diagnostic persistence, ensures that proposal IP is not stored by any AWS service after each inference call completes.

4. **Auditable evidence trail.** CloudTrail, VPC Flow Logs, and the automated evidence collection script produce a reproducible, verifiable security posture that can be presented to institutional reviewers without requiring them to trust the system operator's assertions.

The architecture accepts trade-offs in operational convenience (air-gapped deployment, manual deployment process, no CI/CD), cost visibility (per-token Bedrock pricing without full-run cost projection), and vendor dependency (AWS availability). These trade-offs are documented, rated, and accepted in the risk register.

The transport abstraction preserves a migration path to self-hosted models if institutional requirements evolve toward complete data sovereignty. The infrastructure controls and security governance framework are independent of the specific inference provider and would apply equally to an Ollama or vLLM deployment in a private network.

---

*Architecture Decision Record prepared for institutional audit package. All control references cite verified evidence artefacts from the CG1-CG10 infrastructure hardening programme (2026-05-29 to 2026-06-01). Repository-side security hardening (Phases 0-3) was completed and validated prior to infrastructure deployment.*
