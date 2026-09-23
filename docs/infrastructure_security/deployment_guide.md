# Deployment Guide — Proposal Orchestrator on AWS

**Date:** 2026-06-03 (updated)
**Branch:** `AWS_deployment`
**Prerequisite:** All infrastructure security controls implemented and verified (CG1-CG10, 38/41 VERIFIED_PASS)
**Remaining control:** DC-38 — Full DAG run with production config (execute after deployment)

### Deployment Status

| Milestone | Status | Date | Notes |
|---|---|---|---|
| Infrastructure hardening (CG1-CG10) | COMPLETE | 2026-06-01 | 38/41 VERIFIED_PASS, 2 N/A, 1 DEFERRED (DC-38) |
| S3 gateway SG rule (`sgr-0cc4c7112cd8277c2`) | APPLIED | 2026-06-02 | TCP 443 egress to `pl-63a5400a` added to host SG |
| IAM deploy-bucket-access policy | APPLIED | 2026-06-02 | S3 read on deploy bucket + write to `evidence/` for `ec2-ssm-role` |
| Python 3.9 compatibility fix | APPLIED | 2026-06-02 | `gate_pass_predicates.py` — `Union` replaces `\|` in runtime type alias |
| Application deployed to host | COMPLETE | 2026-06-02 | `/opt/proposal-orchestrator`, pip via `ensurepip`, offline wheel install |
| Dry run verification | PASS | 2026-06-02 | `transport=bedrock_converse`, `production_mode=True`, `[READY] n01_call_analysis` |
| Smoke test — Phase 1 | PASS | 2026-06-03 | `overall_status=pass`, 4 skills OK, entry+exit gates pass, 6m 7s, ~438K tokens |
| DC-38 — Full DAG run | PENDING | — | — |

---

## 1. Infrastructure Summary

All AWS infrastructure is provisioned and hardened. This guide covers application deployment only.

### Provisioned Resources

| Resource | ID / Value |
|---|---|
| AWS Account | `232538551827` |
| Region | `us-east-1` |
| VPC | `vpc-050a09774560fd774` (172.31.0.0/16) |
| Deployment subnets | `subnet-023c6e3ea5451ea47` (us-east-1a), `subnet-01d969bb1421a3042` (us-east-1b) |
| Route table | `rtb-085481996de5e3ed9` (local + S3 prefix list only, no IGW/NAT) |
| EC2 host | `i-0045af36dbf5f1272` (t3.micro, AL2023, Python 3.9.25 pre-installed) |
| Instance profile | `proposal-orchestrator-ec2-ssm-profile` |
| Bedrock role | `proposal-orchestrator-bedrock-role` |
| Bedrock VPC endpoint | `vpce-0843d225c5b1ef6d5` (bedrock-runtime, Private DNS) |
| Secrets Manager endpoint | `vpce-08ba482a3b11f7d64` |
| STS endpoint | `vpce-067abd500c89e2bc4` |
| S3 gateway endpoint | `vpce-0ee5648ce182bf85a` |
| S3 prefix list | `pl-63a5400a` (in route table, **not** in host SG — see Section 2) |
| SSM endpoints | `vpce-06a268f54ecc1f754`, `vpce-0824e9fbb2f099e37`, `vpce-0ec79b44974bfd85b` |
| Host SG | `sg-076f724aed2429771` (TCP 443 egress to VPCE SG only) |
| VPCE SG | `sg-013d5e4d4eb55dfd9` (TCP 443 inbound from host SG) |
| KMS CMK | `887638e8-358b-4664-9270-368aec0ea1f1` (alias/proposal-orchestrator) |
| Secrets Manager secret | `proposal-orchestrator/env-config` |
| CloudTrail trail | `proposal-orchestrator-bedrock-trail` |

### Network Constraints and Deployment Implications

The deployment host has **no internet access**. The hardened network creates three constraints that directly affect deployment:

1. **No package manager access.** `dnf install` fails because the AL2023 package repos (`al2023-repos-us-east-1-de612dc2.s3.dualstack.us-east-1.amazonaws.com`) resolve to public S3 IPs that are unreachable from the private subnet. This means **Docker cannot be installed** on the host via `dnf`, and neither can `pip3` or any other system package.

2. **S3 gateway endpoint requires a security group change.** The S3 gateway endpoint (`vpce-0ee5648ce182bf85a`) routes traffic via the S3 prefix list (`pl-63a5400a`) in the route table. However, the host security group (`sg-076f724aed2429771`) only allows TCP 443 egress to the VPC **interface** endpoint SG (`sg-013d5e4d4eb55dfd9`). S3 gateway endpoint traffic goes to public S3 IPs (routed internally by the prefix list), which do not belong to the VPCE SG. **Without an additional SG egress rule, all S3 operations from the host time out** — including `aws s3 cp`.

3. **SSM sessions have idle timeouts.** Interactive SSM sessions terminate before large downloads complete. Use SSM Run Command (`aws ssm send-command`) for all long-running operations.

### Deployment Strategy

Given these constraints, the only viable deployment path is:

1. Open the host SG to allow S3 traffic (Section 2)
2. Bundle the application + all Python wheels locally (Section 4)
3. Upload the bundle to S3 (Section 4)
4. Download and install on the host via SSM Run Command, bootstrapping pip from a bundled wheel (Section 5)

Docker and ECR-based deployment paths are not viable because Docker cannot be installed on the air-gapped host without package manager access. The Dockerfile in the repository root remains useful for local containerised builds and testing (Section 3).

### Production Environment Variables

Stored in Secrets Manager (`proposal-orchestrator/env-config`):

```
ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US
ORCHESTRATOR_PRODUCTION_MODE=true
ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
AWS_DEFAULT_REGION=us-east-1
SKILL_MODEL=us.anthropic.claude-sonnet-4-6
```

---

## 2. Security Group Change — Enable S3 Gateway Endpoint Access

### Why This Is Needed

The hardened host SG (DC-07, `sg-076f724aed2429771`) restricts all egress to TCP 443 destined for the VPCE interface endpoint SG (`sg-013d5e4d4eb55dfd9`). This was correct for Bedrock, Secrets Manager, STS, and SSM — all of which use **interface** endpoints with ENIs inside the VPC that belong to the VPCE SG.

However, the S3 **gateway** endpoint works differently. It does not create ENIs inside the VPC. Instead, it adds a route table entry pointing the S3 prefix list (`pl-63a5400a`) to the gateway endpoint. Traffic to S3 is addressed to **public S3 IP ranges** (e.g. `52.216.x.x`, `16.15.x.x`) which are intercepted by the route table prefix list rule and routed internally through the gateway — but the host SG evaluates against the **destination IP**, not the gateway. Since those IPs are not in `sg-013d5e4d4eb55dfd9`, the SG blocks the traffic.

### The Change

Add a single egress rule to the host SG allowing TCP 443 to the S3 prefix list:

**PowerShell:**

```powershell
aws ec2 authorize-security-group-egress `
  --group-id sg-076f724aed2429771 `
  --ip-permissions "IpProtocol=tcp,FromPort=443,ToPort=443,PrefixListIds=[{PrefixListId=pl-63a5400a}]" `
  --region us-east-1
```

**Bash:**

```bash
aws ec2 authorize-security-group-egress \
  --group-id sg-076f724aed2429771 \
  --ip-permissions 'IpProtocol=tcp,FromPort=443,ToPort=443,PrefixListIds=[{PrefixListId=pl-63a5400a}]' \
  --region us-east-1
```

### Security Impact Assessment

| Aspect | Before | After |
|---|---|---|
| Host SG egress rules | TCP 443 to `sg-013d5e4d4eb55dfd9` (VPCE SG) | TCP 443 to `sg-013d5e4d4eb55dfd9` (VPCE SG) **+ TCP 443 to `pl-63a5400a` (S3 prefix list)** |
| S3 access from host | Blocked (connection timeout) | Allowed via S3 gateway endpoint only |
| Internet access | None (no IGW/NAT in route table) | Still none — the S3 prefix list only covers AWS-owned S3 IP ranges, and the route table still has no 0.0.0.0/0 route |
| Data egress risk | Minimal | Low increase — host can now write to S3 buckets that its IAM role permits. The IAM permission boundary (`proposal-orchestrator-boundary`) does **not** include `s3:PutObject`, so the Bedrock execution role cannot exfiltrate data to S3. The `ec2-ssm-role` used by the host may have broader S3 permissions; review if needed. |
| Affected controls | DC-07 (host SG restricts outbound to VPC endpoints) | DC-07 wording should be updated to reflect: "TCP 443 egress to VPCE SG + S3 prefix list". The control intent (no internet egress) is preserved. DC-32 (internet egress blocked) is unaffected — the route table still has no IGW/NAT route. |

### Post-Change: Update Control Register

After applying this change, update the following in `docs/infrastructure_security/aws_hardening_control_register.md`:

- **DC-07**: Update "Reviewer Notes" to document the additional S3 prefix list rule and its justification (deployment artifact transfer via S3 gateway endpoint)
- Log the change in `docs/infrastructure_security/aws_hardening_worklog.md`

### Verification

After applying the rule, verify S3 access from the host:

**PowerShell:**

```powershell
aws ssm send-command `
  --instance-ids i-0045af36dbf5f1272 `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["aws s3 ls s3://proposal-orchestrator-deploy-232538551827/ --region us-east-1 2>&1"]' `
  --region us-east-1 `
  --timeout-seconds 60 `
  --output json
```

Check the result with `get-command-invocation`. Expected: bucket listing succeeds (Status: Success) instead of connection timeout.

---

## 3. Docker Containerisation (Local Build and Testing)

The repository includes a `Dockerfile`, `.dockerignore`, and `requirements.txt` for containerised builds. These are used for **local development and testing only** — the production host cannot run Docker because it cannot be installed on the air-gapped host (no `dnf` access).

### 3.1 Python Dependencies

| Package | Purpose |
|---|---|
| `boto3` | Native AWS Bedrock Converse API calls via IAM credentials |
| `pyyaml` | Manifest and gate library parsing |
| `jsonschema` | Artifact schema validation |
| `python-dotenv` | Environment variable loading from `.env` files |

### 3.2 Build the Image Locally

```bash
# From the repository root
docker build -t proposal-orchestrator:latest .
```

The multi-stage build:
1. **Builder stage**: installs dependencies into a virtualenv
2. **Runtime stage**: copies only the virtualenv and application code, runs as non-root `orchestrator` user

### 3.3 Image Contents

| Path in container | Source |
|---|---|
| `/app/runner/` | DAG scheduler, agent/skill runtimes, transport layer |
| `/app/docs/` | Tiered source documents, orchestration state, deliverables |
| `/app/.claude/agents/` | Agent specifications (22 agents) |
| `/app/.claude/skills/` | Skill specifications (30 skills) |
| `/app/.claude/workflows/` | Manifest, gate library, workflow definitions |
| `/app/CLAUDE.md` | Repository constitution |
| `/app/.git/` | Marker directory (empty, required by `find_repo_root()`) |

### 3.4 Verify the Image Locally

```bash
# Check image size
docker images proposal-orchestrator:latest

# Verify Python deps load
docker run --rm proposal-orchestrator:latest \
  python -c "import boto3; import yaml; import jsonschema; print('OK')"

# Dry run (will fail without AWS credentials — expected locally)
docker run --rm proposal-orchestrator:latest \
  --run-id local-test-001 --dry-run --verbose
```

### 3.5 Local Docker Run (with AWS credentials)

If you have local AWS credentials configured:

```bash
docker run --rm \
  -e ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US \
  -e ORCHESTRATOR_PRODUCTION_MODE=true \
  -e ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e SKILL_MODEL=us.anthropic.claude-sonnet-4-6 \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_SESSION_TOKEN \
  -v $(pwd)/docs/tier4_orchestration_state:/app/docs/tier4_orchestration_state \
  proposal-orchestrator:latest \
  --run-id local-run-001 --phase 1 --verbose --json
```

---

## 4. Package the Application Locally

### 4.1 Download Python Wheels for the Host

The host has Python 3.9.25 (AL2023 x86_64) but **no `pip3`**. Pip is bootstrapped on the host using `python3 -m ensurepip` (bundled with CPython, no internet required). All application dependencies must be bundled as wheels and transferred via S3.

**PowerShell:**

```powershell
# Download wheels targeting the host platform (Linux x86_64, Python 3.9)
pip download -r requirements.txt -d ./deploy_deps `
  --python-version 3.9 `
  --only-binary=:all: `
  --platform manylinux2014_x86_64 `
  --platform manylinux_2_17_x86_64 `
  --platform linux_x86_64
```

**Bash:**

```bash
pip download -r requirements.txt -d ./deploy_deps \
  --python-version 3.9 \
  --only-binary=:all: \
  --platform manylinux2014_x86_64 \
  --platform manylinux_2_17_x86_64 \
  --platform linux_x86_64
```

### 4.2 Create the Deployment Tarball

The tarball includes the application code, all Python wheels, and the requirements file. The host's existing Python 3.9.25 is used — no system packages need to be installed.

```bash
tar czf orchestrator-deploy.tar.gz \
  runner/ \
  .claude/agents/ \
  .claude/skills/ \
  .claude/workflows/ \
  docs/ \
  CLAUDE.md \
  pyproject.toml \
  requirements.txt \
  deploy_deps/
```

**PowerShell (Windows tar):**

```powershell
tar czf orchestrator-deploy.tar.gz `
  runner/ `
  .claude/agents/ `
  .claude/skills/ `
  .claude/workflows/ `
  docs/ `
  CLAUDE.md `
  pyproject.toml `
  requirements.txt `
  deploy_deps/
```

### 4.3 Upload to S3

```powershell
# Create deployment bucket (one-time)
aws s3 mb s3://proposal-orchestrator-deploy-232538551827 --region us-east-1

# Upload
aws s3 cp orchestrator-deploy.tar.gz `
  s3://proposal-orchestrator-deploy-232538551827/orchestrator-deploy.tar.gz
```

---

## 5. Deploy to the EC2 Host

**Prerequisite:** Section 2 (S3 security group rule) must be completed first. Without the S3 prefix list egress rule, all `aws s3` commands on the host will time out.

All host-side operations are executed via **SSM Run Command** (`aws ssm send-command`), not interactive SSM sessions. Run Command executes directly on the host without a session and is not subject to session idle timeouts.

### 5.1 Download, Extract, and Install

From your **local machine**, run the full deployment as a single SSM Run Command:

**PowerShell:**

```powershell
aws ssm send-command `
  --instance-ids i-0045af36dbf5f1272 `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["set -euo pipefail","echo === Downloading deployment tarball ===","cd /tmp","aws s3 cp s3://proposal-orchestrator-deploy-232538551827/orchestrator-deploy.tar.gz . 2>&1","echo === Extracting ===","sudo rm -rf /opt/proposal-orchestrator","sudo mkdir -p /opt/proposal-orchestrator","sudo tar xzf orchestrator-deploy.tar.gz -C /opt/proposal-orchestrator","sudo mkdir -p /opt/proposal-orchestrator/.git","echo === Bootstrapping pip via ensurepip ===","cd /opt/proposal-orchestrator","sudo python3 -m ensurepip --upgrade 2>&1 || true","echo === Installing dependencies ===","sudo python3 -m pip install --no-index --find-links=deploy_deps/ -r requirements.txt 2>&1","echo === Verifying imports ===","python3 -c \"import boto3; import yaml; import jsonschema; print(\\\"deps OK\\\")\"","echo === Creating runtime directories ===","sudo mkdir -p .claude/runs .claude/cache .claude/logs","sudo chown -R ssm-user:ssm-user /opt/proposal-orchestrator","echo === DEPLOY_COMPLETE ==="]' `
  --region us-east-1 `
  --timeout-seconds 600 `
  --output json
```

**Bash:**

```bash
aws ssm send-command \
  --instance-ids i-0045af36dbf5f1272 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["set -euo pipefail","echo === Downloading deployment tarball ===","cd /tmp","aws s3 cp s3://proposal-orchestrator-deploy-232538551827/orchestrator-deploy.tar.gz . 2>&1","echo === Extracting ===","sudo rm -rf /opt/proposal-orchestrator","sudo mkdir -p /opt/proposal-orchestrator","sudo tar xzf orchestrator-deploy.tar.gz -C /opt/proposal-orchestrator","sudo mkdir -p /opt/proposal-orchestrator/.git","echo === Bootstrapping pip via ensurepip ===","cd /opt/proposal-orchestrator","sudo python3 -m ensurepip --upgrade 2>&1 || true","echo === Installing dependencies ===","sudo python3 -m pip install --no-index --find-links=deploy_deps/ -r requirements.txt 2>&1","echo === Verifying imports ===","python3 -c \"import boto3; import yaml; import jsonschema; print(\\\"deps OK\\\")\"","echo === Creating runtime directories ===","sudo mkdir -p .claude/runs .claude/cache .claude/logs","sudo chown -R ssm-user:ssm-user /opt/proposal-orchestrator","echo === DEPLOY_COMPLETE ==="]' \
  --region us-east-1 \
  --timeout-seconds 600 \
  --output json
```

### 5.2 Monitor Progress

The `send-command` output contains a `CommandId`. Check progress:

**PowerShell:**

```powershell
aws ssm get-command-invocation `
  --command-id "<COMMAND_ID>" `
  --instance-id i-0045af36dbf5f1272 `
  --region us-east-1
```

**Bash:**

```bash
aws ssm get-command-invocation \
  --command-id "<COMMAND_ID>" \
  --instance-id i-0045af36dbf5f1272 \
  --region us-east-1
```

The `Status` field progresses from `InProgress` to `Success` (or `Failed`). Look for `deps OK` and `DEPLOY_COMPLETE` in `StandardOutputContent`.

### 5.3 What the Deployment Does

| Step | Command | Purpose |
|---|---|---|
| 1 | `aws s3 cp ... orchestrator-deploy.tar.gz` | Download the 185 MB tarball via S3 gateway endpoint |
| 2 | `tar xzf` | Extract app code, docs, wheels into `/opt/proposal-orchestrator` |
| 3 | `mkdir .git` | Create marker directory so `find_repo_root()` can locate the repo |
| 4 | `python3 -m ensurepip --upgrade` | Bootstrap pip using CPython's bundled ensurepip module (no internet, no `dnf`) |
| 5 | `python3 -m pip install --no-index ...` | Install boto3, pyyaml, jsonschema, python-dotenv from bundled wheels |
| 6 | `mkdir .claude/runs .claude/cache .claude/logs` | Create writable directories for runtime state |
| 7 | `chown ssm-user` | Ensure the SSM user can write runtime state |

---

## 6. Running the Orchestrator

### 6.1 Environment Configuration

The production environment variables are stored in Secrets Manager. Load them before running:

```bash
export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US
export ORCHESTRATOR_PRODUCTION_MODE=true
export ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
export AWS_DEFAULT_REGION=us-east-1
export SKILL_MODEL=us.anthropic.claude-sonnet-4-6
```

### 6.2 Run Commands (via SSM Session)

Connect to the host:

```bash
aws ssm start-session --target i-0045af36dbf5f1272 --region us-east-1
```

On the host:

```bash
cd /opt/proposal-orchestrator

# Source environment
export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US
export ORCHESTRATOR_PRODUCTION_MODE=true
export ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
export AWS_DEFAULT_REGION=us-east-1
export SKILL_MODEL=us.anthropic.claude-sonnet-4-6

# Dry run
python3 -m runner --run-id dry-run-001 --dry-run --verbose

# Phase 1
python3 -m runner --run-id phase1-001 --phase 1 --verbose --json

# Full DAG
python3 -m runner --run-id production-001 --verbose --json
```

### 6.3 Launcher Script

For convenience, create a launcher script on the host:

```bash
cat > /opt/proposal-orchestrator/run.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US
export ORCHESTRATOR_PRODUCTION_MODE=true
export ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
export AWS_DEFAULT_REGION=us-east-1
export SKILL_MODEL=us.anthropic.claude-sonnet-4-6

cd /opt/proposal-orchestrator
exec python3 -m runner "$@"
SCRIPT
chmod +x /opt/proposal-orchestrator/run.sh

# Usage:
/opt/proposal-orchestrator/run.sh --run-id my-run-001 --verbose --json
/opt/proposal-orchestrator/run.sh --run-id my-run-002 --phase 1 --verbose
```

### 6.4 Run via SSM Run Command (Long-Running Phases)

For full DAG runs that may exceed SSM session timeouts, use Run Command:

**PowerShell:**

```powershell
aws ssm send-command `
  --instance-ids i-0045af36dbf5f1272 `
  --document-name "AWS-RunShellScript" `
  --parameters 'commands=["export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US","export ORCHESTRATOR_PRODUCTION_MODE=true","export ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata","export AWS_DEFAULT_REGION=us-east-1","export SKILL_MODEL=us.anthropic.claude-sonnet-4-6","cd /opt/proposal-orchestrator","python3 -m runner --run-id production-001 --verbose --json 2>&1 | tee /tmp/dag-run.log","echo exit_code=$?"]' `
  --region us-east-1 `
  --timeout-seconds 7200 `
  --output json
```

---

## 7. Smoke Test Sequence

Run these in order to validate the deployment:

### Step 1: Verify connectivity to Bedrock

```bash
aws bedrock-runtime converse \
  --model-id us.anthropic.claude-sonnet-4-6 \
  --messages '[{"role":"user","content":[{"text":"Respond with exactly: DEPLOY_OK"}]}]' \
  --inference-config '{"maxTokens":20}' \
  --region us-east-1 \
  --output json
```

Expected: model responds with `"DEPLOY_OK"`.

### Step 2: Dry run

```bash
python3 -m runner --run-id smoke-dry-001 --dry-run --verbose
```

Expected: prints `[READY]` nodes, exits with code 0.

### Step 3: Phase 1 execution

```bash
python3 -m runner --run-id smoke-phase1-001 --phase 1 --verbose --json
```

Expected: `[BACKEND] transport=bedrock_converse`, Phase 1 skills execute, exit code 0 or 1 (depending on gate outcomes).

### Step 4: Check outputs

```bash
ls -la docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/
ls -la .claude/runs/smoke-phase1-001/
```

Expected: phase output artifacts exist on disk.

---

## 8. DC-38 Validation — Full DAG Run

This is the final remaining infrastructure control. Execute after successful smoke tests.

```bash
# Full DAG run with production config
python3 -m runner --run-id dc38-validation-001 --verbose --json \
  2>&1 | tee /tmp/dc38-full-dag-run.log

# Capture exit code
echo "exit_code=$?" >> /tmp/dc38-full-dag-run.log

# Upload evidence to S3
aws s3 cp /tmp/dc38-full-dag-run.log \
  s3://proposal-orchestrator-deploy-232538551827/evidence/dc38-full-dag-run.log

# Also copy run summary if produced
aws s3 cp .claude/runs/dc38-validation-001/run_summary.json \
  s3://proposal-orchestrator-deploy-232538551827/evidence/dc38-run-summary.json \
  2>/dev/null || echo "No run summary produced"
```

After collecting evidence, update the control register:
- `docs/infrastructure_security/aws_hardening_control_register.md`: DC-38 status to VERIFIED_PASS or VERIFIED_FAIL
- `docs/infrastructure_security/aws_hardening_worklog.md`: new entry with evidence references

---

## 9. Instance Sizing Guidance

| Workload | Recommended Instance | Notes |
|---|---|---|
| Smoke tests / single phase | `t3.micro` (1 vCPU, 1 GB) | Current host; sufficient for validation |
| Full DAG run (all 8 phases) | `t3.medium` (2 vCPU, 4 GB) | 30 skills, sustained Bedrock calls |
| Concurrent / repeated runs | `t3.large` (2 vCPU, 8 GB) | Headroom for Tier 4 state accumulation |

To resize the current instance:

```bash
# Stop the instance (from your local machine, not via SSM)
aws ec2 stop-instances --instance-ids i-0045af36dbf5f1272 --region us-east-1

# Change instance type
aws ec2 modify-instance-attribute \
  --instance-id i-0045af36dbf5f1272 \
  --instance-type '{"Value":"t3.medium"}' \
  --region us-east-1

# Restart
aws ec2 start-instances --instance-ids i-0045af36dbf5f1272 --region us-east-1
```

---

## 10. Security Checklist for Deployment

Before running production workloads, confirm:

- [ ] S3 prefix list egress rule applied to host SG (Section 2) and DC-07 updated
- [ ] Instance profile `proposal-orchestrator-ec2-ssm-profile` is attached
- [ ] No AWS access keys are present on the host (`env | grep AWS_ACCESS` returns empty)
- [ ] No Claude CLI is installed (`which claude` returns not found)
- [ ] Internet egress is blocked (`curl -m 5 https://api.anthropic.com` times out)
- [ ] Bedrock Converse call succeeds via PrivateLink (Step 1 smoke test)
- [ ] Environment variables resolve to production values
- [ ] `ORCHESTRATOR_PRODUCTION_MODE=true` is set
- [ ] `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` is set (not `full`)

---

## 11. Troubleshooting

### S3 operations time out from the host

```
fatal error: Connect timeout on endpoint URL:
"https://proposal-orchestrator-deploy-232538551827.s3.us-east-1.amazonaws.com/..."
```

**Cause**: The host SG does not allow egress to the S3 prefix list. The S3 gateway endpoint routes via public S3 IPs that are not in the VPCE interface endpoint SG.
**Fix**: Apply the S3 prefix list egress rule per Section 2.

### `dnf install` fails (cannot install Docker, pip, or system packages)

```
Errors during downloading metadata for repository 'amazonlinux':
  - Curl error (28): Timeout was reached for https://al2023-repos-us-east-1-de612dc2.s3.dualstack.us-east-1.amazonaws.com/...
```

**Cause**: The AL2023 package repos use S3 dualstack URLs (`s3.dualstack.us-east-1.amazonaws.com`) that resolve to public IPs unreachable from the private subnet. Even with the S3 prefix list SG rule, the dualstack hostname may not route through the gateway endpoint.
**Not fixable** without additional infrastructure (NAT gateway or S3 interface endpoint with private DNS). This is why the deployment uses pre-bundled Python wheels instead of system package installation.

### find_repo_root() fails

```
RuntimeError: Repository root not found: no ancestor directory contains both CLAUDE.md and .git/
```

**Cause**: Missing `.git/` marker in the deployment directory.
**Fix**: Run `mkdir -p /opt/proposal-orchestrator/.git`. The deployment script in Section 5 does this automatically.

### Transport configuration error at startup

```
Transport configuration error: ORCHESTRATOR_PRODUCTION_MODE=true but backend 'claude_cli' is not production-suitable
```

**Cause**: Environment variables not set.
**Fix**: Source the environment variables before running (Section 6.1), or use the launcher script (Section 6.3).

### AccessDeniedException on Bedrock call

```
Bedrock auth failed: AccessDeniedException
```

**Cause**: Instance profile role lacks Bedrock invoke permissions, or wrong region.
**Fix**: Verify the instance is using `proposal-orchestrator-ec2-ssm-profile`. Verify `AWS_DEFAULT_REGION=us-east-1`. Check IAM role `proposal-orchestrator-bedrock-role` has the invoke policy attached.

### SSM session terminates during long operation

```
Session terminated unexpectedly
```

**Cause**: Interactive SSM sessions have idle timeouts (default 20 min) and maximum session duration limits.
**Fix**: Use SSM Run Command (`aws ssm send-command`) instead. See Section 5 for deployment and Section 6.4 for DAG runs. Run Command has its own `--timeout-seconds` parameter (up to 172800s / 48h).

### Insufficient memory during full DAG run

**Cause**: t3.micro (1 GB) may be insufficient for a full 8-phase run.
**Fix**: Resize to t3.medium or t3.large (see Section 9).

---

## Appendix A: Approaches That Do Not Work

These approaches were attempted during deployment and failed due to the air-gapped network configuration. They are documented here to prevent re-attempts.

| Approach | Failure Mode | Root Cause |
|---|---|---|
| `sudo dnf install -y docker` | `Curl error (28): Timeout was reached` for AL2023 repo metadata | Package repos use `s3.dualstack` URLs unreachable from private subnet |
| `sudo dnf install -y python3-pip` | Same as above | Same — all `dnf` operations require repo access |
| Docker image pull via ECR | Cannot install Docker (see above) | Docker is a prerequisite that cannot be met |
| Docker image load via S3 | Cannot install Docker (see above) | Same |
| `aws s3 cp` without SG change | `Connect timeout on endpoint URL` | Host SG blocks traffic to S3 prefix list IPs (only allows VPCE SG) |
