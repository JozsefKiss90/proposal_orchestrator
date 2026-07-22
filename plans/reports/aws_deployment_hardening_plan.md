# AWS Deployment Hardening Plan

## Proposal Orchestrator — Infrastructure Security, Auditability, and Evidence Collection

**Date:** 2026-05-29
**Baseline:** `security_compliance_brief.md`, `security_hardening_implementation_plan.md`, `smoke_run_validation_report.md`
**Prerequisite:** Repository-side hardening Phases 0-3 completed and validated
**Target:** Institutional deployment on AWS Bedrock Converse API
**Target model:** Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`)
**Approved backend:** `bedrock_converse` (native boto3 Converse API with IAM credentials)
**Scope:** AWS infrastructure controls, deployment validation, auditability, evidence collection
**Status:** PENDING — Infrastructure implementation not yet started

---

## 1. Executive Summary

The Proposal Orchestrator processes Horizon Europe research and innovation proposal data including project concepts, consortium partner details, work package structures, budget allocations, impact narratives, and evaluator-facing deliverable text. This data constitutes institutional intellectual property (proposal IP) that must not leave the controlled AWS environment through infrastructure misconfiguration.

Repository-side security hardening has been completed across four phases:

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 0 | `.gitignore` expansion, credential hygiene, `.env.example` audit | PASS |
| Phase 1 | Production backend enforcement, semantic dispatch routing, fail-closed defaults | PASS |
| Phase 2 | Pre-commit secret scanning, path resolution tests, sandbox hardening tests | PASS |
| Phase 3 | Environment-scoped persistence policy, diagnostic sanitization, error truncation | PASS |

All CRITICAL and HIGH repository-side findings are resolved. The application enforces `bedrock_converse`-only operation in production mode, rejects non-production backends, writes no prompt or response content to disk in production, and sanitizes error messages to prevent content leakage.

**This document addresses the remaining infrastructure-side controls required for institutional deployment.** It defines the AWS configuration, verification procedures, evidence requirements, and acceptance criteria for every infrastructure security control. It is designed so that an independent reviewer can validate the AWS environment using only this document and the collected evidence package.

### Infrastructure Controls Summary

| Area | Controls | Severity | Status |
|------|----------|----------|--------|
| VPC / PrivateLink | Bedrock runtime endpoint, DNS resolution, security groups | CRITICAL | PENDING |
| IAM | Scoped Bedrock role, permission boundaries, deny statements | CRITICAL | PENDING |
| Region enforcement | Region-locked IAM, SCP considerations | HIGH | PENDING |
| KMS | Encryption at rest, key policy, key rotation | MEDIUM | PENDING |
| Secrets Manager | Credential storage, rotation, access policy | HIGH | PENDING |
| CloudTrail | API event logging, S3 storage, log integrity | HIGH | PENDING |
| CloudWatch | Invocation logging disabled, operational logging, retention | MEDIUM | PENDING |
| Data egress prevention | Network, service, IAM, Bedrock-specific controls | CRITICAL | PENDING |

---

## 2. Security Architecture Overview

### Target Deployment Architecture

```
Deployment Host (EC2 / ECS / Lambda)
    |
    +-- Proposal Orchestrator Application
    |       |
    |       +-- ORCHESTRATOR_PRODUCTION_MODE=true
    |       +-- ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US
    |       +-- ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
    |       |
    |       +-- boto3.client("bedrock-runtime")
    |               |
    |               +-- IAM Role (instance profile / task role)
    |                       |
    |                       +-- bedrock:InvokeModel (scoped to Claude models)
    |                       +-- bedrock:InvokeModelWithResponseStream
    |                       +-- Region-locked: eu-west-1 / us-east-1
    |
    +-- VPC Private Subnet
            |
            +-- VPC Endpoint (Interface) for bedrock-runtime
            |       |
            |       +-- PrivateLink → Bedrock service
            |       +-- Private DNS enabled
            |       +-- Security group: egress to endpoint only
            |
            +-- No Internet Gateway route
            +-- No NAT Gateway route (for Bedrock traffic)
            +-- VPC Endpoint for Secrets Manager
            +-- VPC Endpoint for CloudTrail (S3 gateway)
```

### Data Flow Classification

| Data Category | Classification | AWS Handling |
|---|---|---|
| Proposal concept text | Institutional IP — Confidential | Sent to Bedrock via PrivateLink. Zero retention by Bedrock. |
| Consortium partner details | Personal / organizational — Confidential | Sent to Bedrock via PrivateLink. Zero retention by Bedrock. |
| Budget allocations | Financial — Confidential | Sent to Bedrock via PrivateLink. Zero retention by Bedrock. |
| LLM responses (proposal sections) | Generated IP — Confidential | Received from Bedrock via PrivateLink. Not written to disk in production. |
| IAM credentials | Secret | Managed via instance profile or Secrets Manager. Never in files. |
| API event metadata | Operational | Logged to CloudTrail (no prompt content). |
| Diagnostic metadata | Operational | Written to local disk (metadata only — char counts, timing, error class). |

### Bedrock Zero-Retention Guarantee

AWS Bedrock provides a contractual zero-retention guarantee for model invocation data:

- Input prompts and output completions are not stored by AWS Bedrock after the API response is returned
- Model invocation data is not used to train or improve foundation models
- This applies to all Bedrock foundation model providers including Anthropic
- Verification: AWS Bedrock Service Terms, Section 50.3

This guarantee is the foundation of the data protection architecture. The infrastructure controls in this document ensure that prompts reach Bedrock only through controlled, auditable, private network paths.

---

## 3. Infrastructure Security Objectives

| ID | Objective | Threat Mitigated | Priority |
|---|---|---|---|
| ISO-1 | All Bedrock API traffic traverses AWS private network only (no public internet) | Network interception, data exfiltration via transit | CRITICAL |
| ISO-2 | IAM permissions are scoped to only required Bedrock actions, models, and regions | Privilege escalation, unauthorized model access | CRITICAL |
| ISO-3 | No prompt or response data is retained in any AWS service beyond the API call duration | Persistent data exposure in AWS infrastructure | CRITICAL |
| ISO-4 | All Bedrock API invocations are logged with caller identity and timestamp | Undetected unauthorized access | HIGH |
| ISO-5 | AWS credentials are never stored in plaintext files on deployment hosts | Credential theft via filesystem access | HIGH |
| ISO-6 | Data residency is enforced at the IAM level to approved AWS regions only | Data residency violation for EU institutional requirements | HIGH |
| ISO-7 | Encryption at rest is applied to all stored artifacts (logs, trails, secrets) | Data exposure from storage compromise | MEDIUM |
| ISO-8 | Deployment host cannot reach non-Bedrock internet endpoints | Data exfiltration via application-level vulnerability | CRITICAL |

---

## 4. AWS Bedrock Deployment Model

### 4.1 Service Selection

| Component | AWS Service | Justification |
|---|---|---|
| LLM inference | Amazon Bedrock (Converse API) | Native AWS service with zero-retention guarantee, IAM auth, PrivateLink support |
| Network isolation | VPC + PrivateLink | Eliminates public internet transit for API calls |
| Authentication | IAM Roles (instance profile / task role) | No long-term access keys; automatic credential rotation |
| Secret management | AWS Secrets Manager | Encrypted storage, automatic rotation, IAM-scoped access |
| Encryption | AWS KMS | Customer-managed keys for secrets, logs, and trail encryption |
| Audit logging | AWS CloudTrail | Tamper-evident API call records with S3 delivery |
| Operational monitoring | Amazon CloudWatch | Infrastructure metrics and alarms (no prompt logging) |

### 4.2 Model Configuration

| Parameter | Value | Notes |
|---|---|---|
| Model ID | `us.anthropic.claude-sonnet-4-6` | Inference profile for cross-region routing |
| Direct model ID | `anthropic.claude-sonnet-4-20250514-v1:0` | Region-specific model ID (alternative) |
| API | Bedrock Converse API (`bedrock-runtime:Converse`) | Structured message format with tool calling |
| Max output tokens | 32768 | Configured in application (`SKILL_MAX_TOKENS`) |
| Streaming | Not used | Application uses synchronous `Converse` calls |
| Guardrails | Not configured (optional enhancement) | Can be added for content filtering |

### 4.3 Approved Regions

| Region | Region Code | Use Case | Priority |
|---|---|---|---|
| EU (Ireland) | `eu-west-1` | Primary — EU data residency for institutional requirements | PRIMARY |
| US East (N. Virginia) | `us-east-1` | Fallback — model availability, cross-region inference profiles | SECONDARY |

Region selection must be confirmed based on:
1. Model availability in the target region
2. Institutional data residency requirements
3. Latency requirements for the deployment location

### 4.4 Repository-Side Production Configuration

The application requires the following environment variables in production:

```bash
ORCHESTRATOR_PRODUCTION_MODE=true
ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US
ORCHESTRATOR_TRANSPORT_MODEL=us.anthropic.claude-sonnet-4-6
ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
AWS_REGION=eu-west-1
```

The application code enforces:
- `ORCHESTRATOR_PRODUCTION_MODE=true` rejects `claude_cli`, `together_ai`, `ollama`, `openai_compatible` backends
- `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` prevents prompt/response content from being written to disk
- `ORCHESTRATOR_DIAGNOSTIC_LEVEL=full` is rejected as a policy violation in production mode

These controls are verified by 74 repository-side security tests (34 production mode + 40 persistence policy).

---

## 5. VPC Endpoint / AWS PrivateLink Hardening

### 5.1 Objective

Ensure all Bedrock API calls from the deployment host traverse AWS private network infrastructure via PrivateLink, eliminating public internet transit for proposal IP.

### 5.2 Required Configuration

#### 5.2.1 VPC Interface Endpoint for Bedrock Runtime

| Setting | Required Value |
|---|---|
| Service name | `com.amazonaws.<region>.bedrock-runtime` |
| Endpoint type | Interface |
| VPC | The VPC containing the deployment host |
| Subnets | All subnets where the deployment host may run |
| Security group | Dedicated security group (see 5.2.3) |
| Private DNS | **Enabled** |
| Policy | Full access (or scoped — see 5.2.4) |

**Private DNS must be enabled** so that the standard Bedrock API hostname (`bedrock-runtime.<region>.amazonaws.com`) resolves to the VPC endpoint's private IP addresses. This ensures boto3 automatically routes through PrivateLink without application changes.

#### 5.2.2 Additional VPC Endpoints (Supporting Services)

| Service | Endpoint Type | Purpose |
|---|---|---|
| `com.amazonaws.<region>.secretsmanager` | Interface | Credential retrieval without internet |
| `com.amazonaws.<region>.sts` | Interface | IAM role assumption without internet |
| `com.amazonaws.<region>.s3` | Gateway | CloudTrail log delivery without internet |
| `com.amazonaws.<region>.logs` | Interface | CloudWatch Logs delivery without internet (if used) |
| `com.amazonaws.<region>.monitoring` | Interface | CloudWatch Metrics without internet (if used) |

#### 5.2.3 Security Group for VPC Endpoint

| Rule | Direction | Protocol | Port | Source/Destination | Purpose |
|---|---|---|---|---|---|
| Allow HTTPS inbound | Inbound | TCP | 443 | Deployment host security group | Allow application to reach endpoint |
| Default deny | Inbound | All | All | 0.0.0.0/0 | Block all other inbound |
| Default deny | Outbound | All | All | 0.0.0.0/0 | No outbound from endpoint required |

#### 5.2.4 VPC Endpoint Policy (Optional — Defense in Depth)

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowBedrockConverseOnly",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::<ACCOUNT_ID>:role/<BEDROCK_ROLE_NAME>"
            },
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:*:*:inference-profile/us.anthropic.claude-*"
            ]
        }
    ]
}
```

### 5.3 Verification Procedure

#### Step 1: Confirm endpoint exists

```bash
# CloudShell / AWS CLI
aws ec2 describe-vpc-endpoints \
    --filters "Name=service-name,Values=com.amazonaws.<region>.bedrock-runtime" \
    --query "VpcEndpoints[].{ID:VpcEndpointId,State:State,Service:ServiceName,PrivateDns:PrivateDnsEnabled,VpcId:VpcId}" \
    --output table
```

**Expected output:** One endpoint in `available` state with `PrivateDns: True`.

#### Step 2: Confirm private DNS resolution

```bash
# From deployment host (within VPC)
nslookup bedrock-runtime.<region>.amazonaws.com
# OR
dig bedrock-runtime.<region>.amazonaws.com +short
```

**Expected output:** Private IP addresses (10.x.x.x or 172.x.x.x), NOT public IPs.

#### Step 3: Confirm security group rules

```bash
aws ec2 describe-security-groups \
    --group-ids <ENDPOINT_SG_ID> \
    --query "SecurityGroups[].IpPermissions" \
    --output json
```

**Expected output:** Only TCP 443 inbound from deployment host security group.

#### Step 4: Confirm functional connectivity

```bash
# From deployment host
python3 -c "
import boto3
client = boto3.client('bedrock-runtime', region_name='<region>')
response = client.converse(
    modelId='us.anthropic.claude-sonnet-4-6',
    messages=[{'role': 'user', 'content': [{'text': 'Say OK'}]}],
    inferenceConfig={'maxTokens': 10}
)
print('Status:', response['ResponseMetadata']['HTTPStatusCode'])
print('Output:', response['output']['message']['content'][0]['text'])
"
```

**Expected output:** Status 200 and a response from the model.

### 5.4 Evidence Collection

| Evidence ID | Evidence | Collection Method | Format |
|---|---|---|---|
| VPC-E01 | VPC endpoint configuration | `aws ec2 describe-vpc-endpoints --output json > vpc_endpoint_config.json` | JSON export |
| VPC-E02 | Private DNS resolution proof | Screenshot of `nslookup` or `dig` output from deployment host | Screenshot |
| VPC-E03 | Security group rules | `aws ec2 describe-security-groups --group-ids <SG_ID> --output json > endpoint_sg.json` | JSON export |
| VPC-E04 | VPC endpoint policy | `aws ec2 describe-vpc-endpoints --query "VpcEndpoints[].PolicyDocument" --output json > endpoint_policy.json` | JSON export |
| VPC-E05 | Functional Bedrock call from VPC | Screenshot of successful `converse()` call output | Screenshot |
| VPC-E06 | Route table — no internet route | `aws ec2 describe-route-tables --route-table-ids <RT_ID> --output json > route_table.json` | JSON export |

### 5.5 PASS / FAIL Criteria

| Criterion | PASS | FAIL |
|---|---|---|
| Endpoint exists | VPC interface endpoint for `bedrock-runtime` in `available` state | No endpoint, or endpoint in `pending` / `failed` state |
| Private DNS | `bedrock-runtime.<region>.amazonaws.com` resolves to private IPs from within VPC | Resolves to public IPs, or resolution fails |
| Security group | Only TCP 443 inbound from deployment host SG; no 0.0.0.0/0 rules | Open inbound rules, or missing security group |
| Functional test | `converse()` call succeeds from deployment host within VPC | Call fails, or call routes through public internet |
| No internet route | Deployment host subnet route table has no `0.0.0.0/0` route to IGW/NAT for Bedrock traffic | Route to IGW or NAT exists for Bedrock traffic |

---

## 6. IAM Least Privilege Hardening

### 6.1 Objective

Ensure the deployment host's IAM identity has only the minimum permissions required to invoke Bedrock Converse API for approved models in approved regions, with no ability to perform administrative actions, access other AWS services beyond what is required, or invoke non-approved models.

### 6.2 Required Configuration

#### 6.2.1 Bedrock Invocation Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowBedrockConverse",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:*:*:inference-profile/us.anthropic.claude-*"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": ["eu-west-1", "us-east-1"]
                }
            }
        }
    ]
}
```

#### 6.2.2 Supporting Service Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowSecretsRetrieval",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:<region>:<account>:secret:proposal-orchestrator/*"
            ]
        },
        {
            "Sid": "AllowKMSDecrypt",
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:DescribeKey"
            ],
            "Resource": [
                "arn:aws:kms:<region>:<account>:key/<KEY_ID>"
            ]
        }
    ]
}
```

#### 6.2.3 Explicit Deny Statements (Defense in Depth)

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyBedrockAdministration",
            "Effect": "Deny",
            "Action": [
                "bedrock:CreateModelCustomizationJob",
                "bedrock:CreateProvisionedModelThroughput",
                "bedrock:DeleteModelInvocationLoggingConfiguration",
                "bedrock:PutModelInvocationLoggingConfiguration",
                "bedrock:CreateGuardrail",
                "bedrock:DeleteGuardrail",
                "bedrock:TagResource",
                "bedrock:UntagResource"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DenyNonBedrockServices",
            "Effect": "Deny",
            "Action": [
                "ec2:*",
                "s3:*",
                "iam:*",
                "lambda:*",
                "sqs:*",
                "sns:*",
                "dynamodb:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DenyNonClaudeModels",
            "Effect": "Deny",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "NotResource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:*:*:inference-profile/us.anthropic.claude-*"
            ]
        }
    ]
}
```

#### 6.2.4 Permission Boundary

Apply a permission boundary to the Bedrock execution role that limits the maximum scope of any attached policies:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PermissionBoundary",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "secretsmanager:GetSecretValue",
                "kms:Decrypt",
                "kms:DescribeKey",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

#### 6.2.5 IAM Role Trust Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceVpc": "<VPC_ID>"
                }
            }
        }
    ]
}
```

Adjust `Principal.Service` based on compute platform:
- EC2: `ec2.amazonaws.com`
- ECS: `ecs-tasks.amazonaws.com`
- Lambda: `lambda.amazonaws.com`

### 6.3 Verification Procedure

#### Step 1: Confirm role exists and policies are attached

```bash
aws iam get-role --role-name <BEDROCK_ROLE_NAME> --output json > iam_role.json

aws iam list-attached-role-policies --role-name <BEDROCK_ROLE_NAME> --output json > role_policies.json

aws iam list-role-policies --role-name <BEDROCK_ROLE_NAME> --output json > inline_policies.json
```

#### Step 2: Verify effective permissions

```bash
# Verify allowed actions
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::<ACCOUNT>:role/<BEDROCK_ROLE_NAME> \
    --action-names bedrock:InvokeModel \
    --resource-arns "arn:aws:bedrock:eu-west-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0" \
    --output table

# Verify denied actions
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::<ACCOUNT>:role/<BEDROCK_ROLE_NAME> \
    --action-names bedrock:CreateModelCustomizationJob \
    --resource-arns "*" \
    --output table

# Verify non-Claude model is denied
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::<ACCOUNT>:role/<BEDROCK_ROLE_NAME> \
    --action-names bedrock:InvokeModel \
    --resource-arns "arn:aws:bedrock:eu-west-1::foundation-model/meta.llama3-1-70b-instruct-v1:0" \
    --output table
```

#### Step 3: Verify permission boundary

```bash
aws iam get-role --role-name <BEDROCK_ROLE_NAME> \
    --query "Role.PermissionsBoundary" \
    --output json
```

#### Step 4: Confirm caller identity from deployment host

```bash
# From deployment host
aws sts get-caller-identity --output json
```

**Expected:** Role ARN matches `<BEDROCK_ROLE_NAME>`. No access key IDs in the response (instance profile credentials).

#### Step 5: Negative test — attempt unauthorized action

```bash
# From deployment host (should fail with AccessDeniedException)
aws s3 ls 2>&1 || echo "EXPECTED: AccessDeniedException"
aws ec2 describe-instances 2>&1 || echo "EXPECTED: AccessDeniedException"
```

### 6.4 Evidence Collection

| Evidence ID | Evidence | Collection Method | Format |
|---|---|---|---|
| IAM-E01 | Role configuration | `aws iam get-role --output json` | JSON export |
| IAM-E02 | Attached policies | `aws iam list-attached-role-policies --output json` + each policy version | JSON export |
| IAM-E03 | Inline policies | `aws iam list-role-policies --output json` + each policy document | JSON export |
| IAM-E04 | Permission boundary | `aws iam get-role --query Role.PermissionsBoundary --output json` | JSON export |
| IAM-E05 | Allowed action simulation | `aws iam simulate-principal-policy` for `bedrock:InvokeModel` on Claude | CLI output |
| IAM-E06 | Denied action simulation | `aws iam simulate-principal-policy` for denied actions | CLI output |
| IAM-E07 | Non-Claude model denial | `aws iam simulate-principal-policy` for non-Claude model ARN | CLI output |
| IAM-E08 | Caller identity | `aws sts get-caller-identity` from deployment host | CLI output / screenshot |
| IAM-E09 | Negative test results | `aws s3 ls`, `aws ec2 describe-instances` failure output | CLI output |
| IAM-E10 | Trust policy | `aws iam get-role --query Role.AssumeRolePolicyDocument --output json` | JSON export |

### 6.5 PASS / FAIL Criteria

| Criterion | PASS | FAIL |
|---|---|---|
| Least privilege | Role has only Bedrock invoke, Secrets Manager get, KMS decrypt, STS identity | Role has broad permissions (`*` actions or `*` resources without conditions) |
| Region lock | `aws:RequestedRegion` condition limits to approved regions | No region condition, or condition includes unapproved regions |
| Model scope | Only `anthropic.claude-*` model ARNs in resource statements | Wildcard model ARNs or non-Claude models allowed |
| Deny statements | Explicit deny for Bedrock admin actions and non-Bedrock services | No deny statements; reliance only on absence of allow |
| Permission boundary | Boundary attached and limits maximum scope | No permission boundary, or boundary is overly permissive |
| No access keys | Deployment host uses instance profile / task role | Long-term access keys found in files or environment |
| Negative tests | Unauthorized AWS API calls fail with `AccessDeniedException` | Unauthorized calls succeed |

---

## 7. Bedrock Region Enforcement

### 7.1 Objective

Ensure Bedrock API calls can only be made to approved AWS regions, preventing accidental or intentional data routing to regions that violate institutional data residency requirements.

### 7.2 Approved Regions

| Region | Code | Status | Justification |
|---|---|---|---|
| EU (Ireland) | `eu-west-1` | APPROVED | EU data residency for Horizon Europe institutional requirements |
| US East (N. Virginia) | `us-east-1` | APPROVED | Inference profile routing, model availability |
| All other regions | — | DENIED | Not approved for proposal IP processing |

### 7.3 Region Restriction Strategy

#### Layer 1: IAM Condition Key (Primary)

The IAM policy (Section 6.2.1) includes `aws:RequestedRegion` condition:

```json
"Condition": {
    "StringEquals": {
        "aws:RequestedRegion": ["eu-west-1", "us-east-1"]
    }
}
```

This is the primary enforcement mechanism. Any Bedrock API call to an unapproved region will fail with `AccessDeniedException`.

#### Layer 2: Application Configuration (Secondary)

The application configures `AWS_REGION` explicitly:

```bash
AWS_REGION=eu-west-1
```

boto3 uses this to determine the API endpoint. This is a configuration-level control, not an enforcement mechanism — IAM is the enforcement layer.

#### Layer 3: Service Control Policy (SCP) — Organizational (Optional)

If the AWS account is part of an AWS Organization, an SCP can enforce region restrictions at the organizational level:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyBedrockOutsideApprovedRegions",
            "Effect": "Deny",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*",
            "Condition": {
                "StringNotEquals": {
                    "aws:RequestedRegion": ["eu-west-1", "us-east-1"]
                }
            }
        }
    ]
}
```

SCPs are defense-in-depth. They prevent ANY principal in the account from bypassing region restrictions, even if the principal's IAM policy allows it.

### 7.4 Verification Procedure

```bash
# Verify IAM region condition exists in the policy
aws iam get-policy-version \
    --policy-arn <POLICY_ARN> \
    --version-id <VERSION_ID> \
    --query "PolicyVersion.Document" \
    --output json | python3 -c "
import sys, json
doc = json.load(sys.stdin)
for stmt in doc.get('Statement', []):
    cond = stmt.get('Condition', {})
    regions = cond.get('StringEquals', {}).get('aws:RequestedRegion', [])
    if regions:
        print(f'Region restriction found: {regions}')
        break
else:
    print('WARNING: No region restriction found')
"

# Negative test: attempt call to unapproved region
aws bedrock-runtime invoke-model \
    --region ap-southeast-1 \
    --model-id anthropic.claude-sonnet-4-20250514-v1:0 \
    --content-type application/json \
    --body '{"messages":[{"role":"user","content":"test"}],"max_tokens":10,"anthropic_version":"bedrock-2023-05-31"}' \
    /dev/null 2>&1 || echo "EXPECTED: AccessDeniedException for unapproved region"
```

### 7.5 Evidence Collection

| Evidence ID | Evidence | Collection Method | Format |
|---|---|---|---|
| REG-E01 | IAM policy with region condition | Policy document export | JSON export |
| REG-E02 | Successful call in approved region | `converse()` output from eu-west-1 or us-east-1 | CLI output |
| REG-E03 | Failed call in unapproved region | `invoke-model` failure from ap-southeast-1 | CLI output |
| REG-E04 | SCP (if applicable) | `aws organizations list-policies` + policy document | JSON export |
| REG-E05 | Application AWS_REGION setting | Environment variable configuration | Screenshot / config export |

### 7.6 PASS / FAIL Criteria

| Criterion | PASS | FAIL |
|---|---|---|
| IAM region lock | `aws:RequestedRegion` condition present with only approved regions | No region condition, or condition includes unapproved regions |
| Negative test | Bedrock call to unapproved region fails with `AccessDeniedException` | Call to unapproved region succeeds |
| Application config | `AWS_REGION` set to an approved region | `AWS_REGION` set to an unapproved region |

---

## 8. AWS KMS Hardening

### 8.1 Objective

Ensure all stored artifacts (CloudTrail logs, Secrets Manager secrets, any EBS volumes) are encrypted with customer-managed KMS keys with appropriate key policies, and that key rotation is enabled.

### 8.2 Required Configuration

#### 8.2.1 Customer-Managed Key (CMK) for Proposal Orchestrator

| Setting | Value |
|---|---|
| Key type | Symmetric (ENCRYPT_DECRYPT) |
| Key usage | Encrypt and decrypt |
| Key rotation | Enabled (annual automatic rotation) |
| Key alias | `alias/proposal-orchestrator` |
| Key administrators | IAM admin role(s) only |
| Key users | Bedrock execution role, CloudTrail service |

#### 8.2.2 Key Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowKeyAdministration",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::<ACCOUNT>:role/<ADMIN_ROLE>"
            },
            "Action": [
                "kms:Create*",
                "kms:Describe*",
                "kms:Enable*",
                "kms:List*",
                "kms:Put*",
                "kms:Update*",
                "kms:Revoke*",
                "kms:Disable*",
                "kms:Get*",
                "kms:Delete*",
                "kms:TagResource",
                "kms:UntagResource",
                "kms:ScheduleKeyDeletion",
                "kms:CancelKeyDeletion"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AllowKeyUsage",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::<ACCOUNT>:role/<BEDROCK_ROLE_NAME>"
            },
            "Action": [
                "kms:Decrypt",
                "kms:DescribeKey"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AllowCloudTrailEncryption",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": [
                "kms:GenerateDataKey*",
                "kms:DescribeKey"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceArn": "arn:aws:cloudtrail:<region>:<ACCOUNT>:trail/<TRAIL_NAME>"
                }
            }
        }
    ]
}
```

### 8.3 Verification Procedure

```bash
# List keys and find the proposal-orchestrator key
aws kms list-aliases --query "Aliases[?AliasName=='alias/proposal-orchestrator']" --output json

# Describe key
aws kms describe-key --key-id alias/proposal-orchestrator --output json > kms_key_describe.json

# Verify rotation is enabled
aws kms get-key-rotation-status --key-id alias/proposal-orchestrator --output json

# Export key policy
aws kms get-key-policy --key-id alias/proposal-orchestrator --policy-name default --output text > kms_key_policy.json
```

### 8.4 Evidence Collection

| Evidence ID | Evidence | Collection Method | Format |
|---|---|---|---|
| KMS-E01 | Key description | `aws kms describe-key --output json` | JSON export |
| KMS-E02 | Key rotation status | `aws kms get-key-rotation-status --output json` | JSON export |
| KMS-E03 | Key policy | `aws kms get-key-policy --output text` | JSON export |
| KMS-E04 | Key aliases | `aws kms list-aliases --output json` | JSON export |

### 8.5 PASS / FAIL Criteria

| Criterion | PASS | FAIL |
|---|---|---|
| CMK exists | Customer-managed key with alias `proposal-orchestrator` exists and is enabled | No CMK, or only AWS-managed keys used |
| Key rotation | Automatic rotation enabled | Rotation disabled |
| Key policy | Administration limited to admin roles; usage limited to Bedrock role and CloudTrail | Overly permissive key policy (wildcard principals) |
| Encryption usage | CloudTrail, Secrets Manager, and EBS volumes use this CMK | Default encryption or no encryption |

---

## 9. AWS Secrets Manager Hardening

### 9.1 Objective

Ensure all credentials and configuration secrets required by the deployment host are stored in AWS Secrets Manager, encrypted with the customer-managed KMS key, accessible only by the Bedrock execution role, and rotated on a defined schedule.

### 9.2 Required Configuration

#### 9.2.1 Secrets to Store

| Secret Name | Content | Rotation |
|---|---|---|
| `proposal-orchestrator/env-config` | Non-sensitive environment variables (preset, model, region) | Manual (config changes only) |
| `proposal-orchestrator/transport-api-key` | Bedrock API key (if using bedrock-mantle backend) | 90-day automatic |

**Note:** When using `bedrock_converse` (the approved production backend), no API key is required — authentication is via IAM instance profile. The API key secret is only needed if `bedrock` (mantle) is used as a secondary backend.

#### 9.2.2 Secret Configuration

| Setting | Value |
|---|---|
| Encryption key | `alias/proposal-orchestrator` (customer-managed KMS key) |
| Resource policy | Scoped to Bedrock execution role only |
| Rotation | Lambda-based rotation (90-day schedule) for API keys |
| Tags | `project:proposal-orchestrator`, `environment:production` |

#### 9.2.3 Secret Resource Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowBedrockRoleAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::<ACCOUNT>:role/<BEDROCK_ROLE_NAME>"
            },
            "Action": "secretsmanager:GetSecretValue",
            "Resource": "*"
        },
        {
            "Sid": "DenyAllOtherAccess",
            "Effect": "Deny",
            "NotPrincipal": {
                "AWS": [
                    "arn:aws:iam::<ACCOUNT>:role/<BEDROCK_ROLE_NAME>",
                    "arn:aws:iam::<ACCOUNT>:role/<ADMIN_ROLE>"
                ]
            },
            "Action": "secretsmanager:GetSecretValue",
            "Resource": "*"
        }
    ]
}
```

### 9.3 Verification Procedure

```bash
# List secrets
aws secretsmanager list-secrets \
    --filters Key=name,Values=proposal-orchestrator \
    --output json > secrets_list.json

# Describe secret (metadata only, not the value)
aws secretsmanager describe-secret \
    --secret-id proposal-orchestrator/env-config \
    --output json > secret_describe.json

# Verify KMS key is customer-managed
aws secretsmanager describe-secret \
    --secret-id proposal-orchestrator/env-config \
    --query "KmsKeyId" \
    --output text

# Verify resource policy
aws secretsmanager get-resource-policy \
    --secret-id proposal-orchestrator/env-config \
    --output json > secret_policy.json

# Test retrieval from deployment host
aws secretsmanager get-secret-value \
    --secret-id proposal-orchestrator/env-config \
    --query "Name" \
    --output text
```

### 9.4 Evidence Collection

| Evidence ID | Evidence | Collection Method | Format |
|---|---|---|---|
| SM-E01 | Secrets list | `aws secretsmanager list-secrets --output json` | JSON export |
| SM-E02 | Secret description (each) | `aws secretsmanager describe-secret --output json` | JSON export |
| SM-E03 | KMS key association | `describe-secret --query KmsKeyId` output | CLI output |
| SM-E04 | Resource policy | `aws secretsmanager get-resource-policy --output json` | JSON export |
| SM-E05 | Rotation configuration | `describe-secret --query RotationRules` output | JSON export |
| SM-E06 | Successful retrieval test | `get-secret-value --query Name` from deployment host | CLI output |

### 9.5 PASS / FAIL Criteria

| Criterion | PASS | FAIL |
|---|---|---|
| Secret storage | All credentials stored in Secrets Manager | Credentials in plaintext files, environment variables from `.env`, or hardcoded |
| KMS encryption | Secrets encrypted with customer-managed KMS key | Secrets use default AWS-managed key or no encryption |
| Access policy | Resource policy limits access to Bedrock role and admin role only | Overly permissive policy or no resource policy |
| Rotation | API key secrets have rotation enabled (90-day maximum) | No rotation configured for long-lived credentials |
| No plaintext secrets | No `.env` file with credentials on deployment host | `.env` file with `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` present |

---

## 10. CloudTrail Hardening

### 10.1 Objective

Ensure all Bedrock API invocations are logged with tamper-evident, encrypted, and retention-managed audit trails that capture caller identity, timestamp, source IP, and request metadata (but not prompt content).

### 10.2 Required Configuration

#### 10.2.1 Trail Configuration

| Setting | Value |
|---|---|
| Trail name | `proposal-orchestrator-bedrock-trail` |
| Multi-region | No (single region matching deployment) |
| Log file encryption | KMS (`alias/proposal-orchestrator`) |
| Log file validation | Enabled (digest files for integrity verification) |
| S3 bucket | Dedicated bucket with versioning and lifecycle policy |
| S3 key prefix | `cloudtrail/proposal-orchestrator/` |
| CloudWatch Logs | Optional — for real-time alerting |
| Management events | Read and Write |
| Data events | Bedrock model invocation (optional — see 10.2.2) |

#### 10.2.2 Event Selectors

```bash
aws cloudtrail put-event-selectors \
    --trail-name proposal-orchestrator-bedrock-trail \
    --event-selectors '[
        {
            "ReadWriteType": "All",
            "IncludeManagementEvents": true,
            "DataResources": [],
            "ExcludeManagementEventSources": []
        }
    ]'
```

**Note:** Bedrock `InvokeModel` calls are management events in CloudTrail. They are captured by the default management event selector. No data event configuration is required.

#### 10.2.3 S3 Bucket Policy for Trail Delivery

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AWSCloudTrailAclCheck",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": "s3:GetBucketAcl",
            "Resource": "arn:aws:s3:::<TRAIL_BUCKET>"
        },
        {
            "Sid": "AWSCloudTrailWrite",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::<TRAIL_BUCKET>/cloudtrail/proposal-orchestrator/AWSLogs/<ACCOUNT>/*",
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-acl": "bucket-owner-full-control"
                }
            }
        },
        {
            "Sid": "DenyUnencryptedObjects",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::<TRAIL_BUCKET>/*",
            "Condition": {
                "StringNotEquals": {
                    "s3:x-amz-server-side-encryption": "aws:kms"
                }
            }
        },
        {
            "Sid": "DenyInsecureTransport",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::<TRAIL_BUCKET>",
                "arn:aws:s3:::<TRAIL_BUCKET>/*"
            ],
            "Condition": {
                "Bool": {
                    "aws:SecureTransport": "false"
                }
            }
        }
    ]
}
```

#### 10.2.4 S3 Lifecycle Policy

| Rule | Transition | Purpose |
|---|---|---|
| Archive after 90 days | S3 Standard → S3 Glacier Instant Retrieval | Cost optimization |
| Delete after 365 days | Permanent deletion | Retention policy compliance |

Adjust retention period based on institutional audit requirements.

### 10.3 Verification Procedure

```bash
# Describe trail
aws cloudtrail describe-trails \
    --trail-name-list proposal-orchestrator-bedrock-trail \
    --output json > trail_config.json

# Verify trail is logging
aws cloudtrail get-trail-status \
    --name proposal-orchestrator-bedrock-trail \
    --output json > trail_status.json

# Verify log file validation is enabled
aws cloudtrail describe-trails \
    --query "trailList[?TrailARN=='<TRAIL_ARN>'].LogFileValidationEnabled" \
    --output text

# Verify KMS encryption
aws cloudtrail describe-trails \
    --query "trailList[?TrailARN=='<TRAIL_ARN>'].KmsKeyId" \
    --output text

# Look up a recent Bedrock event (after making a test call)
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=InvokeModel \
    --max-results 5 \
    --output json > recent_bedrock_events.json
```

### 10.4 Evidence Collection

| Evidence ID | Evidence | Collection Method | Format |
|---|---|---|---|
| CT-E01 | Trail configuration | `aws cloudtrail describe-trails --output json` | JSON export |
| CT-E02 | Trail logging status | `aws cloudtrail get-trail-status --output json` | JSON export |
| CT-E03 | Log file validation | `describe-trails --query LogFileValidationEnabled` | CLI output |
| CT-E04 | KMS encryption key | `describe-trails --query KmsKeyId` | CLI output |
| CT-E05 | Event selectors | `aws cloudtrail get-event-selectors --output json` | JSON export |
| CT-E06 | Recent Bedrock event | `aws cloudtrail lookup-events` for InvokeModel | JSON export |
| CT-E07 | S3 bucket policy | `aws s3api get-bucket-policy --output json` | JSON export |
| CT-E08 | S3 lifecycle configuration | `aws s3api get-bucket-lifecycle-configuration --output json` | JSON export |
| CT-E09 | S3 versioning status | `aws s3api get-bucket-versioning --output json` | JSON export |

### 10.5 PASS / FAIL Criteria

| Criterion | PASS | FAIL |
|---|---|---|
| Trail exists | Trail `proposal-orchestrator-bedrock-trail` exists and is logging | No trail, or trail is not logging |
| Log validation | Log file validation enabled | Validation disabled |
| Encryption | Trail uses customer-managed KMS key | No encryption, or AWS-managed key only |
| Event capture | `InvokeModel` events appear in CloudTrail after test call | Bedrock events not captured |
| S3 security | Bucket denies unencrypted objects and insecure transport | Bucket allows unencrypted or HTTP access |
| Retention | Lifecycle policy defines archive and deletion rules | No lifecycle policy |

---

## 11. CloudWatch Hardening

### 11.1 Objective

Ensure that (1) Bedrock model invocation logging is NOT enabled in CloudWatch (preventing prompt/response retention in AWS infrastructure), and (2) operational CloudWatch metrics and alarms are configured for infrastructure monitoring without capturing sensitive content.

### 11.2 Critical: Model Invocation Logging Must Be Disabled

AWS Bedrock offers optional model invocation logging to CloudWatch Logs or S3. When enabled, this feature captures full prompt inputs and model completions. **This must be verified as disabled** — it is disabled by default, but can be enabled through the AWS console or API.

### 11.3 Verification Procedure

#### Step 1: Verify invocation logging is disabled

```bash
aws bedrock get-model-invocation-logging-configuration \
    --region <region> \
    --output json > bedrock_logging_config.json
```

**Expected output:**

```json
{
    "loggingConfig": null
}
```

OR an empty/minimal response indicating no logging configuration exists. If `loggingConfig` contains `cloudWatchConfig` or `s3Config` with defined destinations, invocation logging is ENABLED and must be disabled.

**Alternative verification via console:**

1. Navigate to Amazon Bedrock > Settings > Model invocation logging
2. Verify the toggle is set to "Off" or "Disabled"
3. Screenshot the settings page

#### Step 2: Verify no invocation log groups exist

```bash
aws logs describe-log-groups \
    --log-group-name-prefix "/aws/bedrock" \
    --output json > bedrock_log_groups.json
```

**Expected output:** Empty `logGroups` array, or no log groups matching the Bedrock invocation pattern.

### 11.4 Operational Monitoring (Permitted)

The following CloudWatch monitoring is permitted and recommended:

| Metric | Source | Sensitive? | Purpose |
|---|---|---|---|
| `InvocationCount` | Bedrock model metrics | No | Usage tracking |
| `InvocationLatency` | Bedrock model metrics | No | Performance monitoring |
| `InvocationServerErrors` | Bedrock model metrics | No | Error detection |
| `InvocationClientErrors` | Bedrock model metrics | No | Error detection |
| `InvocationThrottles` | Bedrock model metrics | No | Capacity planning |
| EC2/ECS instance metrics | CloudWatch agent | No | Host health |

#### Recommended Alarms

| Alarm | Metric | Threshold | Action |
|---|---|---|---|
| High error rate | `InvocationServerErrors` | > 5 in 5 minutes | SNS notification |
| High throttling | `InvocationThrottles` | > 10 in 5 minutes | SNS notification |
| High latency | `InvocationLatency` p99 | > 60 seconds | SNS notification |

### 11.5 Log Retention Controls

If any CloudWatch log groups are created for operational purposes (not invocation logging):

| Setting | Value |
|---|---|
| Retention period | 90 days (or per institutional policy) |
| Encryption | KMS (`alias/proposal-orchestrator`) |
| Log content | Operational metrics only — never prompt/response content |

```bash
# Set retention on operational log groups
aws logs put-retention-policy \
    --log-group-name /proposal-orchestrator/operational \
    --retention-in-days 90

# Set encryption
aws logs associate-kms-key \
    --log-group-name /proposal-orchestrator/operational \
    --kms-key-id alias/proposal-orchestrator
```

### 11.6 Evidence Collection

| Evidence ID | Evidence | Collection Method | Format |
|---|---|---|---|
| CW-E01 | Bedrock invocation logging config | `aws bedrock get-model-invocation-logging-configuration --output json` | JSON export |
| CW-E02 | Console screenshot — logging disabled | Bedrock > Settings > Model invocation logging | Screenshot |
| CW-E03 | Bedrock log groups (expected empty) | `aws logs describe-log-groups --log-group-name-prefix /aws/bedrock --output json` | JSON export |
| CW-E04 | Operational log group retention | `aws logs describe-log-groups` for operational groups | JSON export |
| CW-E05 | Log group encryption | `aws logs describe-log-groups --query logGroups[].kmsKeyId` | CLI output |

### 11.7 PASS / FAIL Criteria

| Criterion | PASS | FAIL |
|---|---|---|
| Invocation logging disabled | `get-model-invocation-logging-configuration` returns null/empty config | Logging configuration exists with CloudWatch or S3 destination |
| No invocation log groups | No `/aws/bedrock` log groups exist | Log groups with Bedrock invocation data exist |
| Operational log retention | Retention policy set (max 90 days or per institutional policy) | Indefinite retention |
| Log encryption | Operational log groups encrypted with CMK | Unencrypted log groups |

---

## 12. Data Egress Prevention Controls

### 12.1 Objective

Prevent proposal IP from leaving the controlled AWS environment through any channel: network, service, application, or misconfiguration.

### 12.2 Network Controls

#### 12.2.1 VPC Network Architecture

| Control | Requirement | Purpose |
|---|---|---|
| No Internet Gateway | Deployment subnet has no route to IGW | Prevent direct internet egress |
| No NAT Gateway (for Bedrock traffic) | Bedrock calls route through VPC endpoint only | Prevent Bedrock traffic from traversing NAT |
| VPC Flow Logs | Enabled on deployment subnet | Detect unexpected network traffic |
| Security group — deployment host | Outbound: TCP 443 to VPC endpoint SG only | Restrict outbound to PrivateLink only |
| Network ACL | Default deny with explicit allow for VPC endpoint subnet | Defense in depth |

#### 12.2.2 Security Group for Deployment Host

| Rule | Direction | Protocol | Port | Destination | Purpose |
|---|---|---|---|---|---|
| Allow HTTPS to VPC endpoints | Outbound | TCP | 443 | VPC endpoint security group | Bedrock, Secrets Manager, STS |
| Allow SSH inbound (if needed) | Inbound | TCP | 22 | Bastion host SG or CIDR | Administration |
| Default deny outbound | Outbound | All | All | 0.0.0.0/0 | Block all internet egress |

#### 12.2.3 VPC Flow Logs

```bash
# Enable flow logs on deployment subnet
aws ec2 create-flow-logs \
    --resource-type Subnet \
    --resource-ids <SUBNET_ID> \
    --traffic-type ALL \
    --log-destination-type cloud-watch-logs \
    --log-group-name /vpc/proposal-orchestrator/flow-logs \
    --deliver-logs-permission-arn arn:aws:iam::<ACCOUNT>:role/<FLOW_LOGS_ROLE>
```

### 12.3 Service Controls

| Control | Mechanism | Purpose |
|---|---|---|
| IAM deny for non-Bedrock services | Explicit deny for EC2, S3, Lambda, SQS, SNS, DynamoDB | Prevent data exfiltration via other AWS services |
| VPC endpoint policy | Restrict endpoint to Bedrock actions only | Prevent endpoint misuse |
| No S3 access from execution role | IAM deny for `s3:PutObject` on non-trail buckets | Prevent data staging to S3 |

### 12.4 IAM Controls

| Control | Mechanism | Purpose |
|---|---|---|
| Deny `bedrock:PutModelInvocationLoggingConfiguration` | Explicit deny in IAM policy | Prevent enabling invocation logging |
| Deny `iam:*` | Explicit deny | Prevent privilege escalation |
| Permission boundary | Maximum scope limited to Bedrock invoke + Secrets Manager + KMS | Ceiling on any attached policy |

### 12.5 Bedrock-Specific Controls

| Control | Mechanism | Purpose |
|---|---|---|
| Zero retention | Bedrock default — no configuration needed | Prompts/responses not stored by AWS |
| Invocation logging disabled | Verified via `get-model-invocation-logging-configuration` | No prompt data in CloudWatch/S3 |
| Region lock | IAM `aws:RequestedRegion` condition | Data stays in approved regions |
| Model lock | IAM resource ARN scoped to `anthropic.claude-*` | No data sent to non-Anthropic models |

### 12.6 Application-Level Controls (Repository-Side — Completed)

| Control | Status | Mechanism |
|---|---|---|
| Production backend enforcement | RESOLVED | `ORCHESTRATOR_PRODUCTION_MODE=true` rejects non-Bedrock backends |
| Diagnostic persistence policy | RESOLVED | `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` prevents content writes |
| Error message sanitization | RESOLVED | Exception messages truncated to 200 chars in production |
| No Claude CLI binary | REQUIRED | Deployment host must not have `claude` binary installed |

### 12.7 Verification Procedure

```bash
# 1. Verify no internet route
aws ec2 describe-route-tables --route-table-ids <RT_ID> \
    --query "RouteTables[].Routes[?GatewayId!='local']" \
    --output json

# 2. Verify security group restricts outbound
aws ec2 describe-security-groups --group-ids <HOST_SG_ID> \
    --query "SecurityGroups[].IpPermissionsEgress" \
    --output json

# 3. Verify VPC flow logs enabled
aws ec2 describe-flow-logs \
    --filters "Name=resource-id,Values=<SUBNET_ID>" \
    --output json

# 4. Verify no Claude CLI binary on deployment host
which claude 2>&1 || echo "PASS: claude binary not found"
claude --version 2>&1 || echo "PASS: claude binary not available"

# 5. Attempt outbound internet connection (should fail)
curl -s --connect-timeout 5 https://api.anthropic.com 2>&1 || echo "PASS: No internet egress"
curl -s --connect-timeout 5 https://api.together.ai 2>&1 || echo "PASS: No internet egress"
```

### 12.8 Evidence Collection

| Evidence ID | Evidence | Collection Method | Format |
|---|---|---|---|
| DEP-E01 | Route table (no internet route) | `aws ec2 describe-route-tables --output json` | JSON export |
| DEP-E02 | Deployment host security group | `aws ec2 describe-security-groups --output json` | JSON export |
| DEP-E03 | VPC flow logs configuration | `aws ec2 describe-flow-logs --output json` | JSON export |
| DEP-E04 | No Claude CLI binary | `which claude` and `claude --version` output | CLI output / screenshot |
| DEP-E05 | Failed internet egress tests | `curl` timeout output for anthropic.com, together.ai | CLI output |
| DEP-E06 | Network ACL rules | `aws ec2 describe-network-acls --output json` | JSON export |
| DEP-E07 | IAM deny statements | Policy document export showing deny statements | JSON export |
| DEP-E08 | Bedrock invocation logging disabled | `aws bedrock get-model-invocation-logging-configuration` | JSON export |

### 12.9 PASS / FAIL Criteria

| Criterion | PASS | FAIL |
|---|---|---|
| No internet route | Deployment subnet has no route to IGW or NAT for outbound traffic | Route to IGW or NAT exists |
| Security group | Outbound restricted to VPC endpoint SG on TCP 443 only | Outbound allows 0.0.0.0/0 or other destinations |
| VPC flow logs | Flow logs enabled on deployment subnet | Flow logs not enabled |
| No Claude CLI | `claude` binary not found on deployment host | `claude` binary present |
| Internet egress blocked | `curl` to external endpoints times out or fails | External endpoints reachable |
| IAM deny | Deny statements prevent non-Bedrock service access | No deny statements, or deny statements are incomplete |

---

## 13. Production Deployment Checklist

| ID | Control | Category | Owner | Status | Evidence Ref |
|---|---|---|---|---|---|
| DC-01 | VPC interface endpoint for `bedrock-runtime` created and available | Network | AWS Admin | PENDING | VPC-E01 |
| DC-02 | Private DNS enabled on VPC endpoint | Network | AWS Admin | PENDING | VPC-E02 |
| DC-03 | VPC endpoint security group configured (TCP 443 only) | Network | AWS Admin | PENDING | VPC-E03 |
| DC-04 | VPC endpoint policy scoped to Bedrock role and Claude models | Network | AWS Admin | PENDING | VPC-E04 |
| DC-05 | Supporting VPC endpoints created (Secrets Manager, STS, S3) | Network | AWS Admin | PENDING | VPC-E01 |
| DC-06 | No internet route in deployment subnet route table | Network | AWS Admin | PENDING | DEP-E01 |
| DC-07 | Deployment host security group restricts outbound to VPC endpoints | Network | AWS Admin | PENDING | DEP-E02 |
| DC-08 | VPC flow logs enabled on deployment subnet | Network | AWS Admin | PENDING | DEP-E03 |
| DC-09 | IAM role for Bedrock execution created | IAM | AWS Admin | PENDING | IAM-E01 |
| DC-10 | Bedrock invocation policy attached (scoped to Claude models + approved regions) | IAM | AWS Admin | PENDING | IAM-E02 |
| DC-11 | Explicit deny statements attached (Bedrock admin, non-Bedrock services, non-Claude models) | IAM | AWS Admin | PENDING | IAM-E03 |
| DC-12 | Permission boundary attached to Bedrock role | IAM | AWS Admin | PENDING | IAM-E04 |
| DC-13 | IAM role trust policy configured for compute service | IAM | AWS Admin | PENDING | IAM-E10 |
| DC-14 | Instance profile / task role associated with deployment host | IAM | AWS Admin | PENDING | IAM-E08 |
| DC-15 | No long-term access keys on deployment host | IAM | AWS Admin | PENDING | IAM-E08 |
| DC-16 | Region enforcement via IAM condition verified | Region | AWS Admin | PENDING | REG-E01 |
| DC-17 | Negative region test passed (unapproved region denied) | Region | AWS Admin | PENDING | REG-E03 |
| DC-18 | Customer-managed KMS key created with rotation enabled | Encryption | AWS Admin | PENDING | KMS-E01, KMS-E02 |
| DC-19 | KMS key policy scoped to admin and Bedrock roles | Encryption | AWS Admin | PENDING | KMS-E03 |
| DC-20 | Secrets Manager secrets created and encrypted with CMK | Secrets | AWS Admin | PENDING | SM-E01, SM-E03 |
| DC-21 | Secret resource policy scoped to Bedrock role | Secrets | AWS Admin | PENDING | SM-E04 |
| DC-22 | API key rotation configured (90-day, if applicable) | Secrets | AWS Admin | PENDING | SM-E05 |
| DC-23 | CloudTrail trail created with KMS encryption | Audit | AWS Admin | PENDING | CT-E01, CT-E04 |
| DC-24 | CloudTrail log file validation enabled | Audit | AWS Admin | PENDING | CT-E03 |
| DC-25 | CloudTrail S3 bucket secured (encryption, deny HTTP, versioning) | Audit | AWS Admin | PENDING | CT-E07, CT-E09 |
| DC-26 | CloudTrail capturing Bedrock InvokeModel events | Audit | AWS Admin | PENDING | CT-E06 |
| DC-27 | S3 lifecycle policy configured for trail logs | Audit | AWS Admin | PENDING | CT-E08 |
| DC-28 | Bedrock model invocation logging DISABLED | CloudWatch | AWS Admin | PENDING | CW-E01, CW-E02 |
| DC-29 | No Bedrock invocation log groups in CloudWatch | CloudWatch | AWS Admin | PENDING | CW-E03 |
| DC-30 | Operational log groups encrypted with CMK and retention set | CloudWatch | AWS Admin | PENDING | CW-E04, CW-E05 |
| DC-31 | No Claude CLI binary on deployment host | Egress | DevOps | PENDING | DEP-E04 |
| DC-32 | Internet egress blocked from deployment host | Egress | DevOps | PENDING | DEP-E05 |
| DC-33 | `ORCHESTRATOR_PRODUCTION_MODE=true` set | Application | DevOps | PENDING | — |
| DC-34 | `ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US` set | Application | DevOps | PENDING | — |
| DC-35 | `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` set | Application | DevOps | PENDING | — |
| DC-36 | Model availability confirmed in target region | Operational | DevOps | PENDING | — |
| DC-37 | End-to-end Bedrock Converse call succeeds from deployment host | Validation | DevOps | PENDING | VPC-E05 |
| DC-38 | Full DAG run (Phase 1-8) succeeds with production configuration | Validation | DevOps | PENDING | — |
| DC-39 | GDPR DPA executed via AWS Artifact | Compliance | Legal | PENDING | — |
| DC-40 | SCP for region restriction applied (if Organization) | Region | AWS Admin | PENDING | REG-E04 |

---

## 14. Incident Response Readiness

### 14.1 Bedrock Misuse Scenarios

| Scenario | Detection | Containment | Recovery |
|---|---|---|---|
| Unauthorized model invocation | CloudTrail alert on unexpected caller identity or unusual invocation volume | Revoke IAM role session credentials; disable instance profile | Investigate caller identity; rotate credentials; review CloudTrail |
| Non-approved model access attempt | CloudTrail `AccessDeniedException` events for non-Claude model ARNs | Review IAM policies for unexpected allow statements | Tighten IAM policies; verify deny statements |
| Unusual invocation volume (abuse) | CloudWatch alarm on `InvocationCount` exceeding baseline by 3x | Throttle or revoke IAM role | Review CloudTrail for invocation patterns; identify source |
| Invocation from unexpected region | CloudTrail events from unapproved regions (should be denied by IAM) | Verify IAM region condition; apply SCP if needed | Audit IAM policy history; check for policy modifications |

### 14.2 Credential Compromise Scenarios

| Scenario | Detection | Containment | Recovery |
|---|---|---|---|
| Instance profile credential theft | CloudTrail shows API calls from unexpected source IP | Terminate compromised instance; revoke temporary credentials via `aws sts` | Launch new instance with fresh profile; investigate exfiltration vector |
| Secrets Manager secret exposure | CloudTrail shows `GetSecretValue` from unexpected principal | Rotate secret immediately; update IAM policy | Audit access logs; determine exposure scope |
| KMS key compromise | CloudTrail shows unexpected `Decrypt` calls | Disable key; re-encrypt secrets with new key | Full credential rotation; investigate key usage history |
| Access key leak (development) | `detect-secrets` pre-commit hook or manual discovery | Deactivate access key immediately via IAM console | Rotate key; audit CloudTrail for unauthorized use during exposure window |

### 14.3 Unexpected Egress Scenarios

| Scenario | Detection | Containment | Recovery |
|---|---|---|---|
| Data exfiltration via S3 | IAM deny should prevent S3 access; CloudTrail shows attempt | Verify IAM deny statements; check for policy modifications | Re-apply deny statements; investigate attempt source |
| Data exfiltration via non-Bedrock API | IAM deny should prevent access; CloudTrail shows attempt | Verify IAM deny statements | Re-apply deny statements; investigate |
| Invocation logging accidentally enabled | CloudTrail shows `PutModelInvocationLoggingConfiguration` | Disable immediately via `DeleteModelInvocationLoggingConfiguration` | Delete any captured log data; review who enabled it |
| Application sends data to non-Bedrock endpoint | VPC flow logs show outbound traffic to unexpected IPs | Verify security group rules block outbound | Re-apply security group; investigate application change |

### 14.4 Logging Review Procedures

#### 14.4.1 Routine Review (Weekly)

```bash
# Review Bedrock invocations from the past 7 days
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=InvokeModel \
    --start-time $(date -d '7 days ago' '+%Y-%m-%dT%H:%M:%S') \
    --max-results 100 \
    --output json

# Check for any access denied events
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=InvokeModel \
    --start-time $(date -d '7 days ago' '+%Y-%m-%dT%H:%M:%S') \
    --output json | python3 -c "
import sys, json
events = json.load(sys.stdin).get('Events', [])
denied = [e for e in events if 'errorCode' in json.loads(e['CloudTrailEvent'])]
print(f'Total events: {len(events)}, Denied: {len(denied)}')
for d in denied:
    ct = json.loads(d['CloudTrailEvent'])
    print(f'  {d[\"EventTime\"]} - {ct.get(\"errorCode\")}: {ct.get(\"errorMessage\",\"\")[:100]}')
"
```

#### 14.4.2 Incident Review

```bash
# Deep investigation: all Bedrock events from a specific principal
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::BedrockRuntime::Model \
    --start-time <INCIDENT_START> \
    --end-time <INCIDENT_END> \
    --output json > incident_events.json

# Check for IAM policy changes
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=PutRolePolicy \
    --start-time <INCIDENT_START> \
    --output json > iam_changes.json

# Check for invocation logging changes
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=PutModelInvocationLoggingConfiguration \
    --start-time <INCIDENT_START> \
    --output json > logging_changes.json
```

### 14.5 Containment Procedures

#### Immediate Containment (< 15 minutes)

1. **Revoke active sessions:** `aws iam update-role --role-name <ROLE> --max-session-duration 3600` followed by terminating existing sessions
2. **Terminate compromised instance:** `aws ec2 terminate-instances --instance-ids <ID>`
3. **Disable access keys (if any):** `aws iam update-access-key --access-key-id <KEY> --status Inactive`

#### Follow-Up (< 1 hour)

4. **Rotate secrets:** `aws secretsmanager rotate-secret --secret-id <SECRET>`
5. **Review CloudTrail:** Export all events during incident window
6. **Disable invocation logging (if enabled):** `aws bedrock delete-model-invocation-logging-configuration`
7. **Document incident:** Record timeline, evidence, and remediation steps

---

## 15. Audit Evidence Register

### 15.1 Evidence Matrix

| Evidence ID | Control Name | Required Evidence Type | Collection Method | Storage Location | Reviewer | Approval Criteria |
|---|---|---|---|---|---|---|
| VPC-E01 | VPC endpoint configuration | JSON export | `aws ec2 describe-vpc-endpoints --output json` | `evidence/vpc/endpoint_config.json` | AWS Admin | Endpoint in `available` state, Private DNS enabled |
| VPC-E02 | Private DNS resolution | Screenshot | `nslookup` from deployment host | `evidence/vpc/dns_resolution.png` | AWS Admin | Resolves to private IPs (10.x.x.x / 172.x.x.x) |
| VPC-E03 | Endpoint security group | JSON export | `aws ec2 describe-security-groups --output json` | `evidence/vpc/endpoint_sg.json` | AWS Admin | TCP 443 inbound from host SG only |
| VPC-E04 | Endpoint policy | JSON export | `aws ec2 describe-vpc-endpoints --query PolicyDocument` | `evidence/vpc/endpoint_policy.json` | AWS Admin | Scoped to Bedrock role and Claude models |
| VPC-E05 | Functional Bedrock call | Screenshot | Python `converse()` call output | `evidence/vpc/functional_test.png` | DevOps | HTTP 200, model response received |
| VPC-E06 | Route table | JSON export | `aws ec2 describe-route-tables --output json` | `evidence/vpc/route_table.json` | AWS Admin | No 0.0.0.0/0 route to IGW/NAT |
| IAM-E01 | Role configuration | JSON export | `aws iam get-role --output json` | `evidence/iam/role_config.json` | AWS Admin | Role exists with correct trust policy |
| IAM-E02 | Attached policies | JSON export | `aws iam list-attached-role-policies` + policy docs | `evidence/iam/attached_policies/` | AWS Admin | Only Bedrock invoke + supporting policies |
| IAM-E03 | Inline/deny policies | JSON export | `aws iam list-role-policies` + policy docs | `evidence/iam/inline_policies/` | AWS Admin | Deny statements for admin, non-Bedrock, non-Claude |
| IAM-E04 | Permission boundary | JSON export | `aws iam get-role --query PermissionsBoundary` | `evidence/iam/permission_boundary.json` | AWS Admin | Boundary attached and limits scope |
| IAM-E05 | Allowed action simulation | CLI output | `aws iam simulate-principal-policy` | `evidence/iam/allowed_simulation.txt` | AWS Admin | `bedrock:InvokeModel` on Claude models: allowed |
| IAM-E06 | Denied action simulation | CLI output | `aws iam simulate-principal-policy` | `evidence/iam/denied_simulation.txt` | AWS Admin | Bedrock admin, non-Bedrock services: denied |
| IAM-E07 | Non-Claude model denial | CLI output | `aws iam simulate-principal-policy` | `evidence/iam/non_claude_denial.txt` | AWS Admin | Non-Claude model ARN: denied |
| IAM-E08 | Caller identity | CLI output / screenshot | `aws sts get-caller-identity` from host | `evidence/iam/caller_identity.txt` | DevOps | Role ARN matches, no access key ID |
| IAM-E09 | Negative tests | CLI output | `aws s3 ls`, `aws ec2 describe-instances` | `evidence/iam/negative_tests.txt` | DevOps | AccessDeniedException for both |
| IAM-E10 | Trust policy | JSON export | `aws iam get-role --query AssumeRolePolicyDocument` | `evidence/iam/trust_policy.json` | AWS Admin | Only approved compute service, VPC condition |
| REG-E01 | IAM region condition | JSON export | Policy document with `aws:RequestedRegion` | `evidence/region/iam_region_policy.json` | AWS Admin | Only eu-west-1 and us-east-1 |
| REG-E02 | Approved region call | CLI output | Bedrock call from approved region | `evidence/region/approved_call.txt` | DevOps | Call succeeds |
| REG-E03 | Unapproved region denied | CLI output | Bedrock call from ap-southeast-1 | `evidence/region/denied_call.txt` | DevOps | AccessDeniedException |
| REG-E04 | SCP (if applicable) | JSON export | `aws organizations` policy export | `evidence/region/scp_policy.json` | AWS Admin | Region deny for non-approved regions |
| REG-E05 | Application AWS_REGION | Screenshot / config | Environment variable configuration | `evidence/region/app_config.png` | DevOps | Set to approved region |
| KMS-E01 | Key description | JSON export | `aws kms describe-key --output json` | `evidence/kms/key_description.json` | AWS Admin | Key enabled, symmetric, encrypt/decrypt |
| KMS-E02 | Key rotation status | JSON export | `aws kms get-key-rotation-status --output json` | `evidence/kms/rotation_status.json` | AWS Admin | `KeyRotationEnabled: true` |
| KMS-E03 | Key policy | JSON export | `aws kms get-key-policy --output text` | `evidence/kms/key_policy.json` | AWS Admin | Admin and Bedrock role only |
| KMS-E04 | Key aliases | JSON export | `aws kms list-aliases --output json` | `evidence/kms/key_aliases.json` | AWS Admin | `alias/proposal-orchestrator` exists |
| SM-E01 | Secrets list | JSON export | `aws secretsmanager list-secrets --output json` | `evidence/secrets/secrets_list.json` | AWS Admin | Required secrets exist |
| SM-E02 | Secret description | JSON export | `aws secretsmanager describe-secret --output json` | `evidence/secrets/secret_describe.json` | AWS Admin | Encrypted with CMK, tags present |
| SM-E03 | KMS association | CLI output | `describe-secret --query KmsKeyId` | `evidence/secrets/kms_association.txt` | AWS Admin | Customer-managed key ID |
| SM-E04 | Resource policy | JSON export | `aws secretsmanager get-resource-policy --output json` | `evidence/secrets/resource_policy.json` | AWS Admin | Scoped to Bedrock and admin roles |
| SM-E05 | Rotation config | JSON export | `describe-secret --query RotationRules` | `evidence/secrets/rotation_config.json` | AWS Admin | Rotation enabled, <= 90 days |
| SM-E06 | Retrieval test | CLI output | `get-secret-value --query Name` from host | `evidence/secrets/retrieval_test.txt` | DevOps | Successfully retrieved |
| CT-E01 | Trail configuration | JSON export | `aws cloudtrail describe-trails --output json` | `evidence/cloudtrail/trail_config.json` | AWS Admin | Trail exists, KMS enabled |
| CT-E02 | Trail status | JSON export | `aws cloudtrail get-trail-status --output json` | `evidence/cloudtrail/trail_status.json` | AWS Admin | `IsLogging: true` |
| CT-E03 | Log validation | CLI output | `describe-trails --query LogFileValidationEnabled` | `evidence/cloudtrail/log_validation.txt` | AWS Admin | `true` |
| CT-E04 | KMS encryption | CLI output | `describe-trails --query KmsKeyId` | `evidence/cloudtrail/kms_encryption.txt` | AWS Admin | Customer-managed key ARN |
| CT-E05 | Event selectors | JSON export | `aws cloudtrail get-event-selectors --output json` | `evidence/cloudtrail/event_selectors.json` | AWS Admin | Management events included |
| CT-E06 | Bedrock event sample | JSON export | `aws cloudtrail lookup-events` for InvokeModel | `evidence/cloudtrail/bedrock_event.json` | AWS Admin | Event captured with caller identity |
| CT-E07 | S3 bucket policy | JSON export | `aws s3api get-bucket-policy --output json` | `evidence/cloudtrail/s3_policy.json` | AWS Admin | Deny unencrypted, deny HTTP |
| CT-E08 | S3 lifecycle | JSON export | `aws s3api get-bucket-lifecycle-configuration` | `evidence/cloudtrail/s3_lifecycle.json` | AWS Admin | Archive + delete rules present |
| CT-E09 | S3 versioning | JSON export | `aws s3api get-bucket-versioning --output json` | `evidence/cloudtrail/s3_versioning.json` | AWS Admin | Versioning enabled |
| CW-E01 | Invocation logging config | JSON export | `aws bedrock get-model-invocation-logging-configuration` | `evidence/cloudwatch/invocation_logging.json` | AWS Admin | Config is null/empty |
| CW-E02 | Console screenshot | Screenshot | Bedrock > Settings > Model invocation logging | `evidence/cloudwatch/logging_disabled.png` | AWS Admin | Toggle shows "Disabled" / "Off" |
| CW-E03 | Bedrock log groups | JSON export | `aws logs describe-log-groups --log-group-name-prefix /aws/bedrock` | `evidence/cloudwatch/bedrock_log_groups.json` | AWS Admin | Empty array |
| CW-E04 | Operational log retention | JSON export | `aws logs describe-log-groups` for operational groups | `evidence/cloudwatch/log_retention.json` | AWS Admin | Retention <= 90 days |
| CW-E05 | Log encryption | CLI output | `describe-log-groups --query kmsKeyId` | `evidence/cloudwatch/log_encryption.txt` | AWS Admin | CMK key ID present |
| DEP-E01 | Route table | JSON export | `aws ec2 describe-route-tables --output json` | `evidence/egress/route_table.json` | AWS Admin | No 0.0.0.0/0 route |
| DEP-E02 | Host security group | JSON export | `aws ec2 describe-security-groups --output json` | `evidence/egress/host_sg.json` | AWS Admin | Outbound to VPC endpoint SG only |
| DEP-E03 | VPC flow logs | JSON export | `aws ec2 describe-flow-logs --output json` | `evidence/egress/flow_logs.json` | AWS Admin | Flow logs enabled |
| DEP-E04 | No Claude CLI | CLI output / screenshot | `which claude` output | `evidence/egress/no_claude_cli.txt` | DevOps | Binary not found |
| DEP-E05 | Internet egress blocked | CLI output | `curl` timeout results | `evidence/egress/egress_tests.txt` | DevOps | All external endpoints unreachable |
| DEP-E06 | Network ACLs | JSON export | `aws ec2 describe-network-acls --output json` | `evidence/egress/network_acls.json` | AWS Admin | Appropriate deny rules |
| DEP-E07 | IAM deny statements | JSON export | Policy documents with deny statements | `evidence/egress/iam_deny.json` | AWS Admin | Deny for non-Bedrock services |
| DEP-E08 | Bedrock logging disabled | JSON export | `aws bedrock get-model-invocation-logging-configuration` | `evidence/egress/bedrock_logging.json` | AWS Admin | Config null/empty |

### 15.2 Allowed Evidence Types

| Type | Format | Acceptable For |
|---|---|---|
| AWS CLI JSON export | `.json` | Configuration state, policy documents, resource descriptions |
| CloudShell command output | `.txt` or `.log` | Verification commands, negative tests |
| AWS Console screenshot | `.png` or `.jpg` | Visual confirmation of console settings (with timestamp) |
| CloudTrail event export | `.json` | Audit event verification |
| CloudWatch export | `.json` or `.csv` | Log group configuration, metric data |
| IAM policy export | `.json` | Policy documents, permission boundaries |
| VPC configuration export | `.json` | Endpoint, security group, route table, NACL configuration |
| Security group export | `.json` | Inbound/outbound rule verification |
| Route table export | `.json` | Network route verification |
| Secrets Manager export | `.json` | Secret metadata (never secret values) |
| KMS policy export | `.json` | Key policy documents |
| Spreadsheet inventory | `.xlsx` or `.csv` | Summary inventories, control matrices |
| PDF evidence package | `.pdf` | Compiled evidence bundles for formal review |

### 15.3 Evidence Storage

All evidence must be stored in a dedicated directory structure:

```
evidence/
    vpc/
    iam/
        attached_policies/
        inline_policies/
    region/
    kms/
    secrets/
    cloudtrail/
    cloudwatch/
    egress/
    validation/
    assessment/
```

Evidence files must be timestamped (filename or metadata) and must not be modified after collection. The evidence directory must not be committed to the application repository — it contains AWS configuration details.

---

## 16. Infrastructure Validation Procedure

This section defines a step-by-step workflow to validate the complete infrastructure deployment. Execute after all controls have been implemented.

### Phase 1: Network Validation (30 minutes)

| Step | Action | Expected Result | Evidence |
|---|---|---|---|
| 1.1 | Verify VPC endpoint exists | Endpoint in `available` state | VPC-E01 |
| 1.2 | Verify private DNS from deployment host | Private IPs returned | VPC-E02 |
| 1.3 | Verify endpoint security group | TCP 443 only from host SG | VPC-E03 |
| 1.4 | Verify route table | No internet route | DEP-E01 |
| 1.5 | Verify host security group | Outbound to VPC endpoints only | DEP-E02 |
| 1.6 | Verify VPC flow logs | Enabled on deployment subnet | DEP-E03 |
| 1.7 | Test internet egress (negative) | `curl` to external endpoints fails | DEP-E05 |

### Phase 2: IAM Validation (30 minutes)

| Step | Action | Expected Result | Evidence |
|---|---|---|---|
| 2.1 | Verify role exists with policies | Role with Bedrock invoke + deny policies | IAM-E01, IAM-E02, IAM-E03 |
| 2.2 | Verify permission boundary | Boundary attached | IAM-E04 |
| 2.3 | Verify caller identity from host | Role ARN, no access keys | IAM-E08 |
| 2.4 | Simulate allowed actions | `bedrock:InvokeModel` on Claude: allowed | IAM-E05 |
| 2.5 | Simulate denied actions | Bedrock admin, S3, EC2: denied | IAM-E06 |
| 2.6 | Simulate non-Claude model | Non-Claude model ARN: denied | IAM-E07 |
| 2.7 | Negative tests from host | `aws s3 ls`, `aws ec2 describe-instances`: denied | IAM-E09 |

### Phase 3: Encryption and Secrets Validation (20 minutes)

| Step | Action | Expected Result | Evidence |
|---|---|---|---|
| 3.1 | Verify KMS key exists with rotation | Key enabled, rotation on | KMS-E01, KMS-E02 |
| 3.2 | Verify KMS key policy | Admin + Bedrock role only | KMS-E03 |
| 3.3 | Verify secrets exist | Required secrets in Secrets Manager | SM-E01 |
| 3.4 | Verify secret encryption | CMK used for encryption | SM-E03 |
| 3.5 | Verify secret access policy | Scoped to Bedrock + admin roles | SM-E04 |
| 3.6 | Test secret retrieval from host | Successful retrieval | SM-E06 |

### Phase 4: Audit and Monitoring Validation (20 minutes)

| Step | Action | Expected Result | Evidence |
|---|---|---|---|
| 4.1 | Verify CloudTrail trail | Trail exists and is logging | CT-E01, CT-E02 |
| 4.2 | Verify trail encryption | CMK used | CT-E04 |
| 4.3 | Verify log file validation | Enabled | CT-E03 |
| 4.4 | Verify S3 bucket security | Encryption, deny HTTP, versioning | CT-E07, CT-E09 |
| 4.5 | Verify S3 lifecycle policy | Archive + delete rules | CT-E08 |
| 4.6 | Verify invocation logging disabled | Config null/empty | CW-E01, CW-E02 |
| 4.7 | Verify no Bedrock log groups | Empty array | CW-E03 |

### Phase 5: Region and Egress Validation (15 minutes)

| Step | Action | Expected Result | Evidence |
|---|---|---|---|
| 5.1 | Verify IAM region condition | Approved regions only | REG-E01 |
| 5.2 | Test approved region call | Bedrock call succeeds | REG-E02 |
| 5.3 | Test unapproved region call | AccessDeniedException | REG-E03 |
| 5.4 | Verify no Claude CLI | Binary not found | DEP-E04 |
| 5.5 | Verify IAM deny statements | Non-Bedrock services denied | DEP-E07 |

### Phase 6: End-to-End Validation (60+ minutes)

| Step | Action | Expected Result | Evidence |
|---|---|---|---|
| 6.1 | Set production environment variables | All ORCHESTRATOR_* vars configured | Screenshot |
| 6.2 | Make test Bedrock Converse call | HTTP 200, model response | VPC-E05 |
| 6.3 | Verify CloudTrail captured the event | InvokeModel event appears | CT-E06 |
| 6.4 | Verify no diagnostic content files | No `_response.txt`, `_parsed.txt`, `_system_prompt.txt`, `_user_prompt.txt` | Manual check |
| 6.5 | Run full DAG (Phase 1-8) with production config | Phases complete, gates pass | Run summary |
| 6.6 | Verify no prompt content on disk | `find .claude/ -name "*_response.txt" -o -name "*_prompt.txt"` returns empty | CLI output |
| 6.7 | Compile evidence package | All evidence files collected | Evidence directory |

---

## 17. Infrastructure Security Readiness Verdict Framework

### 17.1 Verdict Definitions

| Verdict | Definition | Deployment Decision |
|---|---|---|
| **PASS** | All controls are implemented, verified, and evidenced. All PASS criteria are met. No FAIL criteria are triggered. Evidence package is complete and reviewable. | Proceed to production deployment. |
| **CONDITIONAL PASS** | All CRITICAL controls pass. One or more HIGH or MEDIUM controls have minor deviations that are documented, risk-accepted, and have a defined remediation timeline. No data egress risk. | Proceed to production with documented conditions and remediation timeline. |
| **FAIL** | One or more CRITICAL controls fail, OR a data egress risk is identified, OR evidence is insufficient for independent verification. | Do not deploy. Remediate failing controls before reassessment. |

### 17.2 Control Criticality for Verdict

| Category | Criticality | FAIL on this category blocks deployment? |
|---|---|---|
| VPC / PrivateLink (DC-01 through DC-06) | CRITICAL | Yes |
| IAM least privilege (DC-09 through DC-15) | CRITICAL | Yes |
| Region enforcement (DC-16, DC-17) | HIGH | Yes, if no alternative enforcement exists |
| Data egress prevention (DC-31, DC-32) | CRITICAL | Yes |
| Bedrock invocation logging disabled (DC-28, DC-29) | CRITICAL | Yes |
| KMS encryption (DC-18, DC-19) | MEDIUM | No — can use AWS-managed keys with risk acceptance |
| Secrets Manager (DC-20 through DC-22) | HIGH | Yes, if plaintext credentials found |
| CloudTrail (DC-23 through DC-27) | HIGH | Conditional — can deploy with audit gap documented |
| CloudWatch operational (DC-30) | MEDIUM | No — operational enhancement |
| GDPR DPA (DC-39) | HIGH (for EU institutional) | Depends on institutional policy |
| End-to-end validation (DC-37, DC-38) | CRITICAL | Yes |

### 17.3 Evidence Sufficiency

A verdict of PASS requires:

1. **All evidence IDs** listed in Section 15.1 are present in the evidence directory
2. **All JSON exports** are valid JSON and contain the expected fields
3. **All screenshots** include a visible timestamp and clearly show the verified setting
4. **All CLI outputs** include the full command and untruncated output
5. **All negative tests** demonstrate the expected denial or failure
6. **No evidence is stale** — all evidence collected within 7 days of the assessment date

---

## 18. Final Infrastructure Security Readiness Assessment Template

Complete this template after all AWS-side controls have been implemented and verified.

---

### Infrastructure Security Readiness Assessment

**Assessment date:** _______________
**Assessor:** _______________
**AWS Account ID:** _______________
**Target region:** _______________
**Deployment host type:** EC2 / ECS / Lambda / Other: _______________

---

#### Section A: Control Status

| ID | Control | Status | Evidence Ref | Notes |
|---|---|---|---|---|
| DC-01 | VPC endpoint for bedrock-runtime | PASS / FAIL | VPC-E01 | |
| DC-02 | Private DNS enabled | PASS / FAIL | VPC-E02 | |
| DC-03 | Endpoint security group | PASS / FAIL | VPC-E03 | |
| DC-04 | Endpoint policy scoped | PASS / FAIL | VPC-E04 | |
| DC-05 | Supporting VPC endpoints | PASS / FAIL | VPC-E01 | |
| DC-06 | No internet route | PASS / FAIL | DEP-E01 | |
| DC-07 | Host SG restricts outbound | PASS / FAIL | DEP-E02 | |
| DC-08 | VPC flow logs | PASS / FAIL | DEP-E03 | |
| DC-09 | Bedrock IAM role | PASS / FAIL | IAM-E01 | |
| DC-10 | Bedrock invocation policy | PASS / FAIL | IAM-E02 | |
| DC-11 | Deny statements | PASS / FAIL | IAM-E03 | |
| DC-12 | Permission boundary | PASS / FAIL | IAM-E04 | |
| DC-13 | Trust policy | PASS / FAIL | IAM-E10 | |
| DC-14 | Instance profile assigned | PASS / FAIL | IAM-E08 | |
| DC-15 | No access keys | PASS / FAIL | IAM-E08 | |
| DC-16 | Region enforcement | PASS / FAIL | REG-E01 | |
| DC-17 | Unapproved region denied | PASS / FAIL | REG-E03 | |
| DC-18 | KMS key with rotation | PASS / FAIL | KMS-E01, KMS-E02 | |
| DC-19 | KMS key policy scoped | PASS / FAIL | KMS-E03 | |
| DC-20 | Secrets in Secrets Manager | PASS / FAIL | SM-E01 | |
| DC-21 | Secret policy scoped | PASS / FAIL | SM-E04 | |
| DC-22 | Rotation configured | PASS / FAIL | SM-E05 | |
| DC-23 | CloudTrail trail | PASS / FAIL | CT-E01 | |
| DC-24 | Log validation | PASS / FAIL | CT-E03 | |
| DC-25 | Trail S3 secured | PASS / FAIL | CT-E07, CT-E09 | |
| DC-26 | Bedrock events captured | PASS / FAIL | CT-E06 | |
| DC-27 | S3 lifecycle policy | PASS / FAIL | CT-E08 | |
| DC-28 | Invocation logging disabled | PASS / FAIL | CW-E01 | |
| DC-29 | No Bedrock log groups | PASS / FAIL | CW-E03 | |
| DC-30 | Operational logs encrypted | PASS / FAIL | CW-E05 | |
| DC-31 | No Claude CLI binary | PASS / FAIL | DEP-E04 | |
| DC-32 | Internet egress blocked | PASS / FAIL | DEP-E05 | |
| DC-33 | PRODUCTION_MODE=true | PASS / FAIL | — | |
| DC-34 | TRANSPORT_PRESET set | PASS / FAIL | — | |
| DC-35 | DIAGNOSTIC_LEVEL=metadata | PASS / FAIL | — | |
| DC-36 | Model available in region | PASS / FAIL | — | |
| DC-37 | Bedrock call succeeds | PASS / FAIL | VPC-E05 | |
| DC-38 | Full DAG run succeeds | PASS / FAIL | — | |
| DC-39 | GDPR DPA executed | PASS / FAIL / N/A | — | |
| DC-40 | SCP applied (if Org) | PASS / FAIL / N/A | REG-E04 | |

---

#### Section B: Findings Summary

| Category | PASS | FAIL | N/A |
|---|---|---|---|
| CRITICAL controls | ___ / ___ | ___ / ___ | ___ / ___ |
| HIGH controls | ___ / ___ | ___ / ___ | ___ / ___ |
| MEDIUM controls | ___ / ___ | ___ / ___ | ___ / ___ |

---

#### Section C: Risk Acceptances (if CONDITIONAL PASS)

| Control ID | Finding | Risk Level | Accepted By | Remediation Timeline |
|---|---|---|---|---|
| | | | | |

---

#### Section D: Evidence Package

| Item | Present? | Path |
|---|---|---|
| VPC evidence (VPC-E01 through VPC-E06) | YES / NO | `evidence/vpc/` |
| IAM evidence (IAM-E01 through IAM-E10) | YES / NO | `evidence/iam/` |
| Region evidence (REG-E01 through REG-E05) | YES / NO | `evidence/region/` |
| KMS evidence (KMS-E01 through KMS-E04) | YES / NO | `evidence/kms/` |
| Secrets evidence (SM-E01 through SM-E06) | YES / NO | `evidence/secrets/` |
| CloudTrail evidence (CT-E01 through CT-E09) | YES / NO | `evidence/cloudtrail/` |
| CloudWatch evidence (CW-E01 through CW-E05) | YES / NO | `evidence/cloudwatch/` |
| Egress prevention evidence (DEP-E01 through DEP-E08) | YES / NO | `evidence/egress/` |

---

#### Section E: Verdict

| Field | Value |
|---|---|
| **Verdict** | PASS / CONDITIONAL PASS / FAIL |
| **Justification** | |
| **Conditions (if CONDITIONAL PASS)** | |
| **Blocking findings (if FAIL)** | |
| **Assessor signature** | |
| **Date** | |

---

*AWS Deployment Hardening Plan produced 2026-05-29. Based on repository-side security hardening Phases 0-3 (completed 2026-05-28/29). This plan governs AWS infrastructure security validation for institutional deployment of the Proposal Orchestrator on AWS Bedrock Converse API.*
