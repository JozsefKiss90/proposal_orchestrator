# Operational Procedure

## Proposal Orchestrator — AWS Bedrock Deployment

| Field | Value |
|---|---|
| Document type | Operational Runbook |
| Classification | Internal — Operational |
| Date | 2026-06-03 |
| System | Proposal Orchestrator on AWS Bedrock |
| AWS account | `232538551827` |
| Region | `us-east-1` |
| Host | `i-0045af36dbf5f1272` (EC2, t3.micro, AL2023) |

---

## 1. System Purpose

The Proposal Orchestrator is an automated system for preparing Horizon Europe research and innovation proposals. It processes structured project inputs through an eight-phase workflow, invoking Amazon Bedrock (Claude Sonnet 4.6) to generate evaluator-oriented proposal deliverables. The system runs on a hardened EC2 instance in a private VPC subnet with no internet access.

---

## 2. Roles and Responsibilities

### 2.1 Proposal Operator

**Scope:** Day-to-day use of the system for proposal preparation.

**Responsibilities:**
- Prepare and upload proposal input data (Tier 3 project instantiation files).
- Validate the environment configuration before each run.
- Execute the orchestrator and monitor progress.
- Review generated outputs for accuracy, completeness, and compliance.
- Archive deliverables according to institutional records management policy.
- Report any anomalous behaviour or suspected security incidents.

**Required access:** SSM Session Manager access to the EC2 host. IAM identity with `ssm:StartSession` permission for the target instance.

### 2.2 System Administrator

**Scope:** Infrastructure maintenance, deployment updates, and access management.

**Responsibilities:**
- Deploy and update the orchestrator application on the EC2 host.
- Manage IAM roles, policies, and instance profiles.
- Manage Secrets Manager configuration values.
- Manage EC2 instance lifecycle (start, stop, resize).
- Run the evidence collection script (`collect_evidence.ps1`) and review results.
- Apply security patches to the host operating system (within air-gap constraints).
- Maintain the deployment guide and operational procedures.

**Required access:** IAM identity with EC2, IAM, SecretsManager, and SSM administrative permissions.

### 2.3 Security Reviewer

**Scope:** Periodic security assessment and compliance verification.

**Responsibilities:**
- Review CloudTrail logs for unexpected API calls or access patterns.
- Review VPC Flow Logs for unexpected network traffic.
- Run the evidence collection script and compare output against the baseline integrity manifest.
- Review the risk acceptance register and update risk ratings.
- Review IAM policies, security groups, and endpoint configurations for drift.
- Conduct or coordinate the annual full security reassessment.

**Required access:** Read-only IAM identity with CloudTrail, CloudWatch Logs, EC2, IAM, and KMS describe/get permissions.

---

## 3. New Proposal Execution Procedure

### 3.1 Prepare Proposal Inputs

1. **Populate Tier 3 project instantiation files** on the operator's workstation:
   - `docs/tier3_project_instantiation/project_brief/` — concept note, project summary.
   - `docs/tier3_project_instantiation/consortium/` — partner details, capabilities, roles.
   - `docs/tier3_project_instantiation/call_binding/selected_call.json` — target call identifier.
   - `docs/tier3_project_instantiation/architecture_inputs/` — objectives, outcomes, impacts, WP seeds, risks, milestones.

2. **Populate Tier 2B call sources** if not already present:
   - `docs/tier2b_topic_and_call_sources/` — work programme documents, call extracts.

3. **Verify data completeness.** All mandatory fields in the project brief and call binding must be populated. The orchestrator will declare a gate failure for missing mandatory inputs rather than fabricating content.

### 3.2 Upload Inputs to Host

Transfer the updated repository to the EC2 host via S3:

```powershell
# Create deployment tarball
tar czf orchestrator-deploy.tar.gz runner/ .claude/ docs/ CLAUDE.md pyproject.toml requirements.txt deploy_deps/

# Upload to S3
aws s3 cp orchestrator-deploy.tar.gz s3://proposal-orchestrator-deploy-232538551827/orchestrator-deploy.tar.gz

# Deploy to host via SSM Run Command
aws ssm send-command `
  --instance-ids i-0045af36dbf5f1272 `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["cd /tmp","aws s3 cp s3://proposal-orchestrator-deploy-232538551827/orchestrator-deploy.tar.gz .","sudo rm -rf /opt/proposal-orchestrator/docs","sudo tar xzf orchestrator-deploy.tar.gz -C /opt/proposal-orchestrator","sudo chown -R ssm-user:ssm-user /opt/proposal-orchestrator","echo UPDATE_COMPLETE"]' `
  --region us-east-1 --timeout-seconds 300 --output json
```

### 3.3 Validate Environment

Connect to the host and verify configuration before execution:

```bash
aws ssm start-session --target i-0045af36dbf5f1272 --region us-east-1
```

On the host:

```bash
cd /opt/proposal-orchestrator

# 1. Source environment
export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US
export ORCHESTRATOR_PRODUCTION_MODE=true
export ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
export AWS_DEFAULT_REGION=us-east-1
export SKILL_MODEL=us.anthropic.claude-sonnet-4-6

# 2. Verify no access keys
env | grep AWS_ACCESS  # Expect: empty

# 3. Verify Bedrock connectivity
aws bedrock-runtime converse \
  --model-id us.anthropic.claude-sonnet-4-6 \
  --messages '[{"role":"user","content":[{"text":"Say OK"}]}]' \
  --inference-config '{"maxTokens":10}' \
  --region us-east-1 --output json
# Expect: model responds "OK"

# 4. Dry run
python3 -m runner --run-id pre-check-001 --dry-run --verbose
# Expect: [READY] nodes listed, exit code 0
```

### 3.4 Execute Orchestrator

**Phase-by-phase execution** (recommended for first runs or when reviewing intermediate outputs):

```bash
# Phase 1: Call Analysis
python3 -m runner --run-id proposal-001 --phase 1 --verbose --json

# Review Phase 1 outputs before proceeding
ls docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/

# Continue to subsequent phases as needed
python3 -m runner --run-id proposal-001 --phase 2 --verbose --json
```

**Full DAG execution** (for experienced operators with validated inputs):

```bash
python3 -m runner --run-id proposal-001 --verbose --json 2>&1 | tee /tmp/run.log
```

For long-running full DAG executions, use SSM Run Command to avoid session timeouts:

```powershell
aws ssm send-command `
  --instance-ids i-0045af36dbf5f1272 `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US","export ORCHESTRATOR_PRODUCTION_MODE=true","export ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata","export AWS_DEFAULT_REGION=us-east-1","export SKILL_MODEL=us.anthropic.claude-sonnet-4-6","cd /opt/proposal-orchestrator","python3 -m runner --run-id proposal-001 --verbose --json 2>&1 | tee /tmp/dag-run.log","echo exit_code=$?"]' `
  --region us-east-1 --timeout-seconds 7200 --output json
```

### 3.5 Review Outputs

1. **Inspect phase outputs:**
   ```bash
   ls -la docs/tier4_orchestration_state/phase_outputs/
   ```

2. **Inspect run summary:**
   ```bash
   cat .claude/runs/proposal-001/run_summary.json | python3 -m json.tool
   ```

3. **Review deliverables:**
   ```bash
   ls -la docs/tier5_deliverables/proposal_sections/
   ls -la docs/tier5_deliverables/assembled_drafts/
   ls -la docs/tier5_deliverables/review_packets/
   ```

4. **Review the review packet** for flagged assumptions, inferences, and unresolved items. All generated content must be reviewed by the operator before use in any submission.

### 3.6 Archive Deliverables

Download deliverables from the host to the operator's workstation via S3:

```bash
# On the host
tar czf /tmp/deliverables-proposal-001.tar.gz \
  docs/tier4_orchestration_state/ \
  docs/tier5_deliverables/ \
  .claude/runs/proposal-001/

aws s3 cp /tmp/deliverables-proposal-001.tar.gz \
  s3://proposal-orchestrator-deploy-232538551827/deliverables/deliverables-proposal-001.tar.gz
```

```powershell
# On the workstation
aws s3 cp s3://proposal-orchestrator-deploy-232538551827/deliverables/deliverables-proposal-001.tar.gz .
```

Archive in accordance with institutional records management policy.

---

## 4. Evidence Collection Procedure

### 4.1 Purpose

The `collect_evidence.ps1` script re-collects infrastructure security evidence for all 41 deployment controls (DC-01 through DC-40) from the live AWS environment. Running this script produces a timestamped evidence snapshot that can be compared against the baseline to detect configuration drift.

### 4.2 Location

```
docs/infrastructure_security/evidence/11_audit_package/collect_evidence.ps1
```

### 4.3 Execution

**From a workstation or CloudShell with valid AWS credentials:**

```powershell
# Collect API-queryable evidence (all controls except host-only tests)
.\collect_evidence.ps1 -SkipHostTests

# Full collection including host-only tests (run ON the deployment host)
.\collect_evidence.ps1
```

### 4.4 Output

The script produces:

- Individual evidence files in the `evidence/01_privatelink/` through `evidence/10_compliance/` directories, named with `EV-` prefixes.
- An integrity manifest at `evidence/11_audit_package/evidence_integrity_manifest.txt` with SHA-256 hashes of all evidence files.
- A summary showing pass/fail counts for each command.

### 4.5 Verification

Compare the current evidence against the baseline:

```powershell
# Re-run evidence collection
.\collect_evidence.ps1 -SkipHostTests

# Compare SHA-256 hashes against the previous manifest
# Any changed hashes indicate configuration drift
```

### 4.6 Host-Only Tests

The following evidence requires execution on the deployment host and is skipped when `-SkipHostTests` is specified:

| Evidence | DC | Test |
|---|---|---|
| `EV-PL-002` | DC-02 | DNS resolution of Bedrock endpoint to private IPs |
| `EV-IAM-008` | DC-14 | `sts get-caller-identity` showing instance profile |
| `EV-REG-003` | DC-17 | Live negative region test (ap-southeast-1 denied) |
| `EV-SM-006` | DC-21 | Secret retrieval test from host |
| `EV-DEP-004` | DC-31 | Verification that `claude` binary is not present |
| `EV-DEP-005` | DC-32 | Egress tests (curl to api.anthropic.com) |
| `EV-APP-001` | DC-33..35 | Configuration key verification |
| `EV-E2E-001` | DC-37 | End-to-end Bedrock Converse call |

---

## 5. Security Validation Procedure

### 5.1 Bedrock Connectivity Validation

**Purpose:** Confirm that the Bedrock Converse API is reachable via PrivateLink and returns a valid model response.

```bash
# From the deployment host
aws bedrock-runtime converse \
  --model-id us.anthropic.claude-sonnet-4-6 \
  --messages '[{"role":"user","content":[{"text":"Respond with: VALIDATION_OK"}]}]' \
  --inference-config '{"maxTokens":20}' \
  --region us-east-1 --output json
```

**Expected result:** HTTP 200, model responds with `"VALIDATION_OK"`.

**Failure action:** Verify the Bedrock VPC endpoint is in `available` state. Verify the host security group permits TCP 443 to the VPCE security group. Verify the IAM role has the invoke policy attached. Check CloudTrail for `AccessDeniedException` events.

### 5.2 IAM Validation

**Purpose:** Confirm that IAM policies enforce least-privilege access.

```powershell
# Allowed action: Claude invoke in approved region
aws iam simulate-principal-policy `
  --policy-source-arn "arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role" `
  --action-names bedrock:InvokeModel `
  --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0" `
  --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=us-east-1,ContextKeyType=string" `
  --output json
# Expect: EvalDecision = "allowed"

# Denied action: admin operation
aws iam simulate-principal-policy `
  --policy-source-arn "arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role" `
  --action-names bedrock:PutModelInvocationLoggingConfiguration `
  --resource-arns "*" --output json
# Expect: EvalDecision = "explicitDeny"

# Denied action: non-Claude model
aws iam simulate-principal-policy `
  --policy-source-arn "arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role" `
  --action-names bedrock:InvokeModel `
  --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-1-70b-instruct-v1:0" `
  --output json
# Expect: EvalDecision = "explicitDeny"
```

### 5.3 CloudTrail Validation

**Purpose:** Confirm that Bedrock API calls are being recorded.

```powershell
aws cloudtrail lookup-events `
  --lookup-attributes AttributeKey=EventName,AttributeValue=Converse `
  --max-results 5 --region us-east-1 --output json
```

**Expected result:** Recent Converse events with caller identity, VPC endpoint ID, and private source IP.

**Failure action:** Verify the trail is active (`get-trail-status`). Verify the trail S3 bucket is accessible. Check for IAM permission issues on the trail.

### 5.4 Egress Validation

**Purpose:** Confirm that the host cannot reach the public internet.

```bash
# From the deployment host
curl -s --connect-timeout 5 https://api.anthropic.com 2>&1
# Expect: connection timeout

curl -s --connect-timeout 5 https://api.together.ai 2>&1
# Expect: connection timeout

which claude 2>&1
# Expect: not found
```

**Failure action:** If any egress test succeeds, immediately check the route table for an IGW/NAT route and the host security group for `0.0.0.0/0` egress rules. Treat successful egress as a security incident (see Section 6).

---

## 6. Incident Response Procedure

### 6.1 Unauthorised Access

**Indicators:** Unexpected CloudTrail events, unfamiliar `sts:AssumeRole` calls, API calls from unexpected source IPs or at unexpected times.

**Actions:**
1. Identify the affected IAM identity from CloudTrail events.
2. Disable the compromised IAM identity or revoke its session tokens.
3. Review all API actions taken by the identity since the suspected compromise.
4. Rotate the Secrets Manager secret if the compromised identity had secret access.
5. Rotate the KMS key if the compromised identity had key usage permissions.
6. Notify the institutional information security officer.
7. Preserve CloudTrail logs and VPC Flow Logs as evidence.

### 6.2 Unexpected Network Activity

**Indicators:** VPC Flow Log entries showing traffic to unexpected destinations, traffic on unexpected ports, or traffic volumes inconsistent with normal operation.

**Actions:**
1. Query CloudWatch Logs Insights on the `/proposal-orchestrator/vpc-flow-logs` log group to identify the source and destination of unexpected traffic.
2. Compare against the expected traffic pattern: TCP 443 to VPC endpoint ENIs and S3 prefix list IPs only.
3. If traffic to public internet destinations is observed, treat as a potential data exfiltration event:
   - Stop the EC2 instance immediately.
   - Preserve the EBS volume for forensic analysis.
   - Review the route table and security group for unauthorised modifications.
   - Notify the institutional information security officer.

### 6.3 Failed Bedrock Invocations

**Indicators:** Orchestrator returns transport errors, `AccessDeniedException`, or timeout errors during skill invocations.

**Actions:**
1. Check the run log for the specific error message and affected skill.
2. Verify the Bedrock VPC endpoint state: `aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-0843d225c5b1ef6d5`.
3. Verify IAM role and policies: `aws iam get-role --role-name proposal-orchestrator-bedrock-role`.
4. Check model availability: `aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId,'claude-sonnet')]"`.
5. Check CloudTrail for the specific failed event.
6. If the issue is transient (Bedrock service issue), retry after a delay. If persistent, escalate to AWS Support.

### 6.4 Secrets Compromise

**Indicators:** Secret accessed by an unexpected role (visible in CloudTrail), secret value modified unexpectedly, `AccessDeniedException` on secret retrieval from the expected role.

**Actions:**
1. Identify the accessor from CloudTrail events.
2. Rotate the secret immediately: create a new secret version with updated values.
3. Review the secret resource policy for unauthorised modifications.
4. If the secret contained API keys (not currently the case — IAM auth is used), revoke the compromised keys.
5. Notify the institutional information security officer.

---

## 7. Change Management

### 7.1 Updating Orchestrator Code

1. Make code changes in the repository on the development workstation.
2. Run the test suite locally: `python -m pytest tests/ -v`.
3. Rebuild the deployment tarball (Section 3.2 of the deployment guide).
4. Upload to S3 and redeploy to the host (Section 3.2 above).
5. Run a dry run and Phase 1 smoke test to verify.
6. Document the change in the deployment guide or a change log.

### 7.2 Updating the Deployment Bundle

1. If Python dependencies have changed, re-download wheels for the host platform:
   ```powershell
   pip download -r requirements.txt -d ./deploy_deps `
     --python-version 3.9 --only-binary=:all: `
     --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform linux_x86_64
   ```
2. Rebuild the tarball, upload, and redeploy.
3. Verify imports on the host: `python3 -c "import boto3; import yaml; import jsonschema; print('OK')"`.

### 7.3 Updating IAM Permissions

1. Document the proposed change: what permission is being added or removed, and why.
2. Apply the change using the AWS CLI or Console.
3. Run the IAM simulation tests from `collect_evidence.ps1` to verify that allowed and denied actions are correct.
4. Update the control register (`aws_hardening_control_register.md`) if the change affects a DC.
5. Log the change in the worklog (`aws_hardening_worklog.md`).

### 7.4 Updating Endpoint Policies

1. Document the proposed change.
2. Apply using `aws ec2 modify-vpc-endpoint --policy-document`.
3. Re-collect evidence: run `collect_evidence.ps1 -SkipHostTests`.
4. Verify that the functional Bedrock test still succeeds.
5. Update the control register if the change affects DC-04.

### 7.5 Change Approval

All changes to IAM policies, security groups, route tables, endpoint policies, or KMS key policies require:
- Written justification.
- Pre-change evidence collection (baseline).
- Post-change evidence collection (verification).
- Update to the control register and worklog.

---

## 8. Periodic Review Requirements

### 8.1 Monthly Reviews

| Review | Action | Responsible |
|---|---|---|
| Evidence re-collection | Run `collect_evidence.ps1 -SkipHostTests`. Compare SHA-256 hashes against the previous integrity manifest. Investigate any changed hashes. | System Administrator |
| IAM policy review | Verify attached policies on `proposal-orchestrator-bedrock-role` match the expected set. Check for new inline policies or permission boundary changes. | System Administrator |
| Security group review | Verify host SG (`sg-076f724aed2429771`) and VPCE SG (`sg-013d5e4d4eb55dfd9`) have no unexpected rules. | System Administrator |

### 8.2 Quarterly Reviews

| Review | Action | Responsible |
|---|---|---|
| CloudTrail audit | Review CloudTrail events for the quarter. Look for: unexpected caller identities, API calls outside business hours, infrastructure modification events (CreateSecurityGroup, ModifyVpcEndpoint, PutRolePolicy, etc.), `AccessDeniedException` events indicating blocked access attempts. | Security Reviewer |
| VPC Flow Log review | Query CloudWatch Logs Insights for traffic to unexpected destinations. Verify all traffic is to VPC endpoint ENIs or S3 prefix list IPs. | Security Reviewer |
| Risk register review | Review all risks in `risk_acceptance_register.md`. Reassess likelihood and impact. Update mitigation status. Add new risks if identified. | Security Reviewer |
| Architecture review | Verify the deployed architecture matches the security architecture document. Check for new services, endpoints, or resources that were not present at hardening time. | Security Reviewer |

### 8.3 Annual Reviews

| Review | Action | Responsible |
|---|---|---|
| Full security reassessment | Re-run the complete evidence collection including host-only tests. Review all 41 DCs against current state. Update the control register. Produce an updated audit report. | Security Reviewer |
| Model and service review | Verify model availability, review Bedrock service changes, assess whether model updates require IAM or endpoint policy changes. | System Administrator |
| Dependency review | Review Python dependencies for known vulnerabilities. Update `requirements.txt` and redeploy if necessary. | System Administrator |
| Access review | Review all IAM identities with access to the account and EC2 host. Remove access for personnel who no longer require it. | System Administrator |
| GDPR review | Reassess data processing activities, data flows, and data transfer mechanisms. Update the data flow document if the architecture has changed. | Security Reviewer |

### 8.4 Review Records

All periodic reviews should be documented with:
- Date of review.
- Reviewer identity.
- Findings (including "no findings" if all checks pass).
- Any corrective actions taken.
- Date of next scheduled review.

Records should be stored in `docs/infrastructure_security/audit_package/review_records/` or the institutional information security management system.

---

## Appendix A: Key Commands Reference

| Task | Command |
|---|---|
| Connect to host | `aws ssm start-session --target i-0045af36dbf5f1272 --region us-east-1` |
| Dry run | `python3 -m runner --run-id <id> --dry-run --verbose` |
| Phase execution | `python3 -m runner --run-id <id> --phase <N> --verbose --json` |
| Full DAG | `python3 -m runner --run-id <id> --verbose --json` |
| Bedrock test | `aws bedrock-runtime converse --model-id us.anthropic.claude-sonnet-4-6 --messages '[{"role":"user","content":[{"text":"Say OK"}]}]' --inference-config '{"maxTokens":10}' --region us-east-1 --output json` |
| Collect evidence | `.\collect_evidence.ps1 -SkipHostTests` |
| Check trail status | `aws cloudtrail get-trail-status --name proposal-orchestrator-bedrock-trail --region us-east-1` |
| Check instance state | `aws ec2 describe-instance-status --instance-ids i-0045af36dbf5f1272 --region us-east-1` |
| Start instance | `aws ec2 start-instances --instance-ids i-0045af36dbf5f1272 --region us-east-1` |
| Stop instance | `aws ec2 stop-instances --instance-ids i-0045af36dbf5f1272 --region us-east-1` |

---

## Appendix B: Contact Points

| Role | Contact | Notes |
|---|---|---|
| System Administrator | *[To be completed by institution]* | Primary operational contact |
| Security Reviewer | *[To be completed by institution]* | Periodic review and incident escalation |
| Institutional CISO / ISO | *[To be completed by institution]* | Incident reporting and policy authority |
| Data Protection Officer | *[To be completed by institution]* | GDPR queries and DPIA assessment |
| AWS Support | AWS Support Centre | Infrastructure-level issues |

---

*Document prepared for operational use. All resource IDs, commands, and procedures reflect the deployed infrastructure as of 2026-06-03. Update this document when infrastructure changes are applied.*
