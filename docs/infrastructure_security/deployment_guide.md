# Deployment Guide — Proposal Orchestrator on AWS

**Date:** 2026-06-02
**Branch:** `AWS_deployment`
**Prerequisite:** All infrastructure security controls implemented and verified (CG1-CG10, 38/41 VERIFIED_PASS)
**Remaining control:** DC-38 — Full DAG run with production config (execute after deployment)

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
| Route table | `rtb-085481996de5e3ed9` (local + S3 only, no IGW/NAT) |
| EC2 host | `i-0045af36dbf5f1272` (t3.micro, AL2023) |
| Instance profile | `proposal-orchestrator-ec2-ssm-profile` |
| Bedrock role | `proposal-orchestrator-bedrock-role` |
| Bedrock VPC endpoint | `vpce-0843d225c5b1ef6d5` (bedrock-runtime, Private DNS) |
| Secrets Manager endpoint | `vpce-08ba482a3b11f7d64` |
| STS endpoint | `vpce-067abd500c89e2bc4` |
| S3 gateway endpoint | `vpce-0ee5648ce182bf85a` |
| SSM endpoints | `vpce-06a268f54ecc1f754`, `vpce-0824e9fbb2f099e37`, `vpce-0ec79b44974bfd85b` |
| KMS CMK | `887638e8-358b-4664-9270-368aec0ea1f1` (alias/proposal-orchestrator) |
| Secrets Manager secret | `proposal-orchestrator/env-config` |
| CloudTrail trail | `proposal-orchestrator-bedrock-trail` |

### Network Constraints

The deployment host has **no internet access**. Outbound traffic is restricted to VPC endpoints only (TCP 443 to endpoint security group). All file transfers to the host must go through S3 (gateway endpoint) or SSM.

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

## 2. Docker Containerisation

The application is packaged as a Docker container using a multi-stage build. The `Dockerfile`, `.dockerignore`, and `requirements.txt` are in the repository root.

### 2.1 Python Dependencies

| Package | Purpose |
|---|---|
| `boto3` | Native AWS Bedrock Converse API calls via IAM credentials |
| `pyyaml` | Manifest and gate library parsing |
| `jsonschema` | Artifact schema validation |
| `python-dotenv` | Environment variable loading from `.env` files |

### 2.2 Build the Image Locally

```bash
# From the repository root
docker build -t proposal-orchestrator:latest .
```

The multi-stage build:
1. **Builder stage**: installs dependencies into a virtualenv
2. **Runtime stage**: copies only the virtualenv and application code, runs as non-root `orchestrator` user

### 2.3 Image Contents

| Path in container | Source |
|---|---|
| `/app/runner/` | DAG scheduler, agent/skill runtimes, transport layer |
| `/app/docs/` | Tiered source documents, orchestration state, deliverables |
| `/app/.claude/agents/` | Agent specifications (22 agents) |
| `/app/.claude/skills/` | Skill specifications (30 skills) |
| `/app/.claude/workflows/` | Manifest, gate library, workflow definitions |
| `/app/CLAUDE.md` | Repository constitution |
| `/app/.git/` | Marker directory (empty, required by `find_repo_root()`) |

### 2.4 Verify the Image Locally

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

---

## 3. Deployment Path A — ECR + Docker on Host

This path pushes the image to Amazon ECR and pulls it on the host via a VPC endpoint. Use this if Docker is installed on the deployment host.

### 3.1 Prerequisites

- Docker installed on the EC2 host (AL2023: `sudo dnf install -y docker && sudo systemctl enable --now docker`)
- ECR VPC interface endpoint created (`com.amazonaws.us-east-1.ecr.api` and `com.amazonaws.us-east-1.ecr.dkr`)
- S3 gateway endpoint already exists (required for ECR layer pulls)

### 3.2 Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name proposal-orchestrator \
  --region us-east-1 \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=KMS,kmsKey=alias/proposal-orchestrator
```

### 3.3 Push the Image

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 232538551827.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag proposal-orchestrator:latest \
  232538551827.dkr.ecr.us-east-1.amazonaws.com/proposal-orchestrator:latest

docker push \
  232538551827.dkr.ecr.us-east-1.amazonaws.com/proposal-orchestrator:latest
```

### 3.4 Pull and Run on Host

Connect to the host via SSM:

```bash
aws ssm start-session --target i-0045af36dbf5f1272 --region us-east-1
```

On the host:

```bash
# Authenticate Docker to ECR (host uses instance profile credentials)
aws ecr get-login-password --region us-east-1 | \
  sudo docker login --username AWS --password-stdin 232538551827.dkr.ecr.us-east-1.amazonaws.com

# Pull the image
sudo docker pull \
  232538551827.dkr.ecr.us-east-1.amazonaws.com/proposal-orchestrator:latest

# Run — see Section 5 for run commands
```

---

## 4. Deployment Path B — S3 Image Transfer (Air-Gapped)

This path exports the Docker image as a tarball, uploads it to S3, and loads it on the host. Use this if ECR VPC endpoints are not available or Docker is not installed (in which case, skip to Section 4.3 for the non-Docker variant).

### 4.1 Export and Upload the Image

On your local machine:

```bash
# Save the image as a tarball
docker save proposal-orchestrator:latest | gzip > orchestrator-image.tar.gz

# Create deployment bucket (one-time)
aws s3 mb s3://proposal-orchestrator-deploy-232538551827 --region us-east-1

# Upload
aws s3 cp orchestrator-image.tar.gz \
  s3://proposal-orchestrator-deploy-232538551827/orchestrator-image.tar.gz
```

### 4.2 Load on Host (Docker)

Via SSM on the host:

```bash
# Download from S3
aws s3 cp s3://proposal-orchestrator-deploy-232538551827/orchestrator-image.tar.gz /tmp/

# Load the image
sudo docker load < /tmp/orchestrator-image.tar.gz

# Verify
sudo docker images proposal-orchestrator:latest
```

### 4.3 Non-Docker Variant (Direct Python)

If Docker is not available on the host, deploy the application directly:

```bash
# --- On your local machine ---

# Bundle the application (without Docker)
tar czf orchestrator-deploy.tar.gz \
  runner/ \
  .claude/agents/ \
  .claude/skills/ \
  .claude/workflows/ \
  docs/ \
  CLAUDE.md \
  pyproject.toml \
  requirements.txt

# Bundle Python wheels for offline install
pip download -r requirements.txt -d ./deploy_deps
tar czf orchestrator-deps.tar.gz deploy_deps/

# Upload both to S3
aws s3 cp orchestrator-deploy.tar.gz \
  s3://proposal-orchestrator-deploy-232538551827/orchestrator-deploy.tar.gz
aws s3 cp orchestrator-deps.tar.gz \
  s3://proposal-orchestrator-deploy-232538551827/orchestrator-deps.tar.gz
```

Via SSM on the host:

```bash
# Download
cd /tmp
aws s3 cp s3://proposal-orchestrator-deploy-232538551827/orchestrator-deploy.tar.gz .
aws s3 cp s3://proposal-orchestrator-deploy-232538551827/orchestrator-deps.tar.gz .

# Install Python (AL2023)
sudo dnf install -y python3 python3-pip

# Set up application directory
sudo mkdir -p /opt/proposal-orchestrator
sudo tar xzf orchestrator-deploy.tar.gz -C /opt/proposal-orchestrator
sudo tar xzf orchestrator-deps.tar.gz -C /opt/proposal-orchestrator

# Create .git marker for find_repo_root()
sudo mkdir -p /opt/proposal-orchestrator/.git

# Install dependencies offline
cd /opt/proposal-orchestrator
sudo pip3 install --no-index --find-links=deploy_deps/ -r requirements.txt

# Verify
python3 -c "import boto3; import yaml; import jsonschema; print('deps OK')"

# Create writable state directories
sudo mkdir -p .claude/runs .claude/cache .claude/logs
sudo chown -R ssm-user:ssm-user /opt/proposal-orchestrator
```

---

## 5. Running the Orchestrator

### 5.1 Environment Configuration

The production environment variables are stored in Secrets Manager. Load them before running:

```bash
# Fetch and export config from Secrets Manager
SECRET_JSON=$(aws secretsmanager get-secret-value \
  --secret-id "proposal-orchestrator/env-config" \
  --query "SecretString" --output text --region us-east-1)

export ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US
export ORCHESTRATOR_PRODUCTION_MODE=true
export ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata
export AWS_DEFAULT_REGION=us-east-1
export SKILL_MODEL=us.anthropic.claude-sonnet-4-6
```

### 5.2 Docker Run Commands

```bash
# Dry run (verify config resolution and graph loading)
sudo docker run --rm \
  -e ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US \
  -e ORCHESTRATOR_PRODUCTION_MODE=true \
  -e ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e SKILL_MODEL=us.anthropic.claude-sonnet-4-6 \
  proposal-orchestrator:latest \
  --run-id dry-run-001 --dry-run --verbose

# Single-phase run (Phase 1 — lightest real execution)
sudo docker run --rm \
  -e ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US \
  -e ORCHESTRATOR_PRODUCTION_MODE=true \
  -e ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e SKILL_MODEL=us.anthropic.claude-sonnet-4-6 \
  -v /opt/orchestrator-state:/app/docs/tier4_orchestration_state \
  proposal-orchestrator:latest \
  --run-id phase1-001 --phase 1 --verbose --json

# Full DAG run
sudo docker run --rm \
  -e ORCHESTRATOR_TRANSPORT_PRESET=BEDROCK_CONVERSE_US \
  -e ORCHESTRATOR_PRODUCTION_MODE=true \
  -e ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e SKILL_MODEL=us.anthropic.claude-sonnet-4-6 \
  -v /opt/orchestrator-state:/app/docs/tier4_orchestration_state \
  -v /opt/orchestrator-deliverables:/app/docs/tier5_deliverables \
  proposal-orchestrator:latest \
  --run-id production-001 --verbose --json
```

**IAM credentials**: The container inherits IAM credentials from the EC2 instance metadata service (IMDS) automatically. No additional credential configuration is needed — boto3 discovers the instance profile via the standard AWS credential chain.

**Volume mounts**: Mount host directories for Tier 4 (orchestration state) and Tier 5 (deliverables) to persist outputs across container runs. Without mounts, outputs are lost when the container exits.

### 5.3 Direct Python Run Commands (Non-Docker)

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

### 5.4 Launcher Script

For convenience, create a launcher script on the host:

```bash
cat > /opt/proposal-orchestrator/run.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

# Load config from Secrets Manager
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

---

## 6. Smoke Test Sequence

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

## 7. DC-38 Validation — Full DAG Run

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

## 8. Instance Sizing Guidance

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

## 9. Security Checklist for Deployment

Before running production workloads, confirm:

- [ ] Instance profile `proposal-orchestrator-ec2-ssm-profile` is attached
- [ ] No AWS access keys are present on the host (`env | grep AWS_ACCESS` returns empty)
- [ ] No Claude CLI is installed (`which claude` returns not found)
- [ ] Internet egress is blocked (`curl -m 5 https://api.anthropic.com` times out)
- [ ] Bedrock Converse call succeeds via PrivateLink (Step 1 smoke test)
- [ ] Environment variables resolve to production values
- [ ] `ORCHESTRATOR_PRODUCTION_MODE=true` is set
- [ ] `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata` is set (not `full`)
- [ ] Container runs as non-root user (Docker path)
- [ ] Tier 4 and Tier 5 volume mounts are configured (Docker path)

---

## 10. Troubleshooting

### Container cannot reach Bedrock

```
botocore.exceptions.EndpointConnectionError
```

**Cause**: VPC endpoint not reachable or security group blocks traffic.
**Fix**: Verify host SG (`sg-076f724aed2429771`) has TCP 443 egress to VPCE SG (`sg-013d5e4d4eb55dfd9`). Verify endpoint state is `available`.

### Transport configuration error at startup

```
Transport configuration error: ORCHESTRATOR_PRODUCTION_MODE=true but backend 'claude_cli' is not production-suitable
```

**Cause**: Environment variables not set or not passed to the container.
**Fix**: Ensure all `-e` flags are present in `docker run`, or source the env vars for direct Python.

### find_repo_root() fails

```
RuntimeError: Repository root not found: no ancestor directory contains both CLAUDE.md and .git/
```

**Cause**: Missing `.git/` marker in the container or deployment directory.
**Fix**: The Dockerfile creates `.git/` automatically. For direct Python deployments, run `mkdir -p /opt/proposal-orchestrator/.git`.

### AccessDeniedException on Bedrock call

```
Bedrock auth failed: AccessDeniedException
```

**Cause**: Instance profile role lacks Bedrock invoke permissions, or wrong region.
**Fix**: Verify the instance is using `proposal-orchestrator-ec2-ssm-profile`. Verify `AWS_DEFAULT_REGION=us-east-1`. Check IAM role `proposal-orchestrator-bedrock-role` has the invoke policy attached.

### Insufficient memory during full DAG run

**Cause**: t3.micro (1 GB) may be insufficient for a full 8-phase run.
**Fix**: Resize to t3.medium or t3.large (see Section 8).
