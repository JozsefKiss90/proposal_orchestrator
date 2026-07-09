<#
.SYNOPSIS
    Collects AWS infrastructure security evidence for all 41 Deployment Controls (DC-01 through DC-40).

.DESCRIPTION
    Runs AWS CLI commands against the live AWS environment and writes evidence artifacts
    to the evidence directory tree. Each command maps to a specific DC from the control
    register (aws_hardening_control_register.md).

    Designed for reproducibility: re-running this script regenerates all evidence from
    the live environment, allowing auditors to diff current state against baseline.

.PARAMETER Region
    AWS region to query. Default: us-east-1.

.PARAMETER EvidenceRoot
    Root directory for evidence output. Default: script's parent directory (evidence/).

.PARAMETER SkipHostTests
    Skip tests that must run ON the deployment host (DNS resolution, curl egress, claude CLI check).
    Use this when running from CloudShell or a local workstation.

.EXAMPLE
    .\collect_evidence.ps1
    .\collect_evidence.ps1 -Region us-east-1 -SkipHostTests
#>

param(
    [string]$Region = "us-east-1",
    [string]$EvidenceRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$SkipHostTests
)

$ErrorActionPreference = "Continue"

# ---------------------------------------------------------------------------
# Resource IDs from verified control register
# ---------------------------------------------------------------------------
$AccountId          = "232538551827"
$VpcId              = "vpc-050a09774560fd774"
$SubnetA            = "subnet-023c6e3ea5451ea47"
$SubnetB            = "subnet-01d969bb1421a3042"
$RouteTableId       = "rtb-085481996de5e3ed9"
$VpceSg             = "sg-013d5e4d4eb55dfd9"
$HostSg             = "sg-076f724aed2429771"
$BedrockVpce        = "vpce-0843d225c5b1ef6d5"
$BedrockRole        = "proposal-orchestrator-bedrock-role"
$BedrockRoleArn     = "arn:aws:iam::${AccountId}:role/${BedrockRole}"
$Ec2SsmRole         = "proposal-orchestrator-ec2-ssm-role"
$KmsAlias           = "alias/proposal-orchestrator"
$KmsKeyId           = "887638e8-358b-4664-9270-368aec0ea1f1"
$SecretId           = "proposal-orchestrator/env-config"
$TrailName          = "proposal-orchestrator-bedrock-trail"
$TrailBucket        = "proposal-orchestrator-cloudtrail-232538551827"
$HostInstanceId     = "i-0045af36dbf5f1272"
$FlowLogGroupName   = "/proposal-orchestrator/vpc-flow-logs"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Evidence {
    param([string]$SubDir, [string]$FileName, [scriptblock]$Command)
    $dir = Join-Path $EvidenceRoot $SubDir
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $outPath = Join-Path $dir $FileName
    Write-Host "  [$SubDir/$FileName] " -NoNewline
    try {
        $result = & $Command 2>&1
        $resultText = $result | Out-String
        $resultText | Out-File -FilePath $outPath -Encoding utf8
        # Detect AWS CLI auth/session errors (not IAM simulation results which legitimately contain deny decisions)
        $isSimulation = $resultText -match "EvalDecisionDetails" -or $resultText -match "EvalActionName"
        # AWSOrganizationsNotInUseException is expected evidence for DC-40 (account not in Organization)
        $isExpectedError = $resultText -match "AWSOrganizationsNotInUseException"
        $isAwsError = (-not $isExpectedError) -and (
                      $resultText -match "\[ERROR\]" -or $resultText -match "ExpiredToken" -or
                      $resultText -match "session has expired" -or
                      ($resultText -match "AccessDenied" -and -not $isSimulation))
        if ($isAwsError) {
            $script:failCount++
            Write-Host "AWS_ERROR" -ForegroundColor Red
        }
        elseif ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null -and -not $isExpectedError) {
            $script:failCount++
            Write-Host "EXIT_$LASTEXITCODE" -ForegroundColor Yellow
        }
        else {
            $script:passCount++
            Write-Host "OK" -ForegroundColor Green
        }
    }
    catch {
        "ERROR: $_" | Out-File -FilePath $outPath -Encoding utf8
        $script:failCount++
        Write-Host "FAIL: $_" -ForegroundColor Red
    }
}

$script:passCount = 0
$script:failCount = 0
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
Write-Host "================================================================="
Write-Host " AWS Infrastructure Security Evidence Collection"
Write-Host " Region:       $Region"
Write-Host " Account:      $AccountId"
Write-Host " Timestamp:    $timestamp"
Write-Host " Evidence root: $EvidenceRoot"
Write-Host " Skip host tests: $SkipHostTests"
Write-Host "================================================================="
Write-Host ""

# ===================================================================
# CG1 — VPC Endpoint / AWS PrivateLink  (DC-01..DC-06, DC-37, PL-8)
# ===================================================================
Write-Host "--- CG1: VPC Endpoint / PrivateLink ---" -ForegroundColor Cyan

# DC-01: VPC interface endpoint for bedrock-runtime (state, Private DNS)
Write-Evidence "01_privatelink" "EV-PL-001-vpc-endpoints.json" {
    aws ec2 describe-vpc-endpoints `
        --filters "Name=service-name,Values=com.amazonaws.$Region.bedrock-runtime" `
        --region $Region --output json
}

# DC-01 + DC-05: All VPC endpoints (bedrock, secretsmanager, sts, s3, ssm)
Write-Evidence "01_privatelink" "EV-PL-001-all-endpoints.json" {
    aws ec2 describe-vpc-endpoints `
        --filters "Name=vpc-id,Values=$VpcId" `
        --query "VpcEndpoints[].{Id:VpcEndpointId,Service:ServiceName,State:State,Type:VpcEndpointType,PrivateDns:PrivateDnsEnabled}" `
        --region $Region --output json
}

# DC-02: Private DNS resolution (must run on deployment host)
if (-not $SkipHostTests) {
    Write-Evidence "01_privatelink" "EV-PL-002-dns-resolution.txt" {
        nslookup "bedrock-runtime.$Region.amazonaws.com" 2>&1
    }
}

# DC-03: VPC endpoint security group
Write-Evidence "01_privatelink" "EV-PL-003-vpce-security-group.json" {
    aws ec2 describe-security-groups `
        --group-ids $VpceSg `
        --region $Region --output json
}

# DC-04: VPC endpoint policy (scoped to Bedrock role + Claude models)
Write-Evidence "01_privatelink" "EV-PL-004-endpoint-policy.json" {
    aws ec2 describe-vpc-endpoints `
        --vpc-endpoint-ids $BedrockVpce `
        --query "VpcEndpoints[].PolicyDocument" `
        --region $Region --output json
}

# DC-06: Route table — no internet route
Write-Evidence "01_privatelink" "EV-PL-006-route-table.json" {
    aws ec2 describe-route-tables `
        --route-table-ids $RouteTableId `
        --region $Region --output json
}

# PL-8: VPC DNS settings
Write-Evidence "01_privatelink" "EV-PL-008-vpc-dns-hostnames.json" {
    aws ec2 describe-vpc-attribute `
        --vpc-id $VpcId --attribute enableDnsHostnames `
        --region $Region --output json
}
Write-Evidence "01_privatelink" "EV-PL-008-vpc-dns-support.json" {
    aws ec2 describe-vpc-attribute `
        --vpc-id $VpcId --attribute enableDnsSupport `
        --region $Region --output json
}

# ===================================================================
# CG2 — IAM Least Privilege  (DC-09..DC-15)
# ===================================================================
Write-Host ""
Write-Host "--- CG2: IAM Least Privilege ---" -ForegroundColor Cyan

# DC-09: IAM role configuration
Write-Evidence "02_iam" "EV-IAM-001-role-config.json" {
    aws iam get-role --role-name $BedrockRole --output json
}

# DC-09 + DC-13: Trust policy
Write-Evidence "02_iam" "EV-IAM-010-trust-policy.json" {
    aws iam get-role --role-name $BedrockRole `
        --query "Role.AssumeRolePolicyDocument" --output json
}

# DC-10: Attached policies list
Write-Evidence "02_iam" "EV-IAM-002-attached-policies.json" {
    aws iam list-attached-role-policies --role-name $BedrockRole --output json
}

# DC-10: Bedrock invoke policy document
Write-Evidence "02_iam" "EV-IAM-003-policy-bedrock-invoke.json" {
    $policies = aws iam list-attached-role-policies --role-name $BedrockRole --output json | ConvertFrom-Json
    foreach ($p in $policies.AttachedPolicies) {
        if ($p.PolicyName -match "bedrock-invoke") {
            $ver = aws iam get-policy --policy-arn $p.PolicyArn --query "Policy.DefaultVersionId" --output text
            aws iam get-policy-version --policy-arn $p.PolicyArn --version-id $ver --output json
        }
    }
}

# DC-11: Explicit deny policy document
Write-Evidence "02_iam" "EV-IAM-003-policy-explicit-deny.json" {
    $policies = aws iam list-attached-role-policies --role-name $BedrockRole --output json | ConvertFrom-Json
    foreach ($p in $policies.AttachedPolicies) {
        if ($p.PolicyName -match "explicit-deny") {
            $ver = aws iam get-policy --policy-arn $p.PolicyArn --query "Policy.DefaultVersionId" --output text
            aws iam get-policy-version --policy-arn $p.PolicyArn --version-id $ver --output json
        }
    }
}

# DC-12: Permission boundary metadata
Write-Evidence "02_iam" "EV-IAM-004-boundary-metadata.json" {
    aws iam get-role --role-name $BedrockRole `
        --query "Role.PermissionsBoundary" --output json
}

# DC-12: Boundary policy document
Write-Evidence "02_iam" "EV-IAM-003-policy-boundary.json" {
    $policies = aws iam list-attached-role-policies --role-name $BedrockRole --output json | ConvertFrom-Json
    foreach ($p in $policies.AttachedPolicies) {
        if ($p.PolicyName -match "boundary") {
            $ver = aws iam get-policy --policy-arn $p.PolicyArn --query "Policy.DefaultVersionId" --output text
            aws iam get-policy-version --policy-arn $p.PolicyArn --version-id $ver --output json
        }
    }
}

# DC-11: Supporting services policy document
Write-Evidence "02_iam" "EV-IAM-003-policy-supporting-services.json" {
    $policies = aws iam list-attached-role-policies --role-name $BedrockRole --output json | ConvertFrom-Json
    foreach ($p in $policies.AttachedPolicies) {
        if ($p.PolicyName -match "supporting-services") {
            $ver = aws iam get-policy --policy-arn $p.PolicyArn --query "Policy.DefaultVersionId" --output text
            aws iam get-policy-version --policy-arn $p.PolicyArn --version-id $ver --output json
        }
    }
}

# DC-04 (CG1 cross-ref): VPC endpoint policy via IAM evidence directory
Write-Evidence "02_iam" "EV-VPC-004-bedrock-endpoint-policy.json" {
    aws ec2 describe-vpc-endpoints `
        --vpc-endpoint-ids $BedrockVpce `
        --query "VpcEndpoints[0].PolicyDocument" `
        --region $Region --output json
}

# DC-10 + DC-11: IAM policy simulation — allowed action (Claude in us-east-1)
Write-Evidence "02_iam" "EV-IAM-005-sim-allowed-invoke.json" {
    aws iam simulate-principal-policy `
        --policy-source-arn "arn:aws:iam::${AccountId}:role/${BedrockRole}" `
        --action-names bedrock:InvokeModel `
        --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0" `
        --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=us-east-1,ContextKeyType=string" `
        --output json
}

# DC-11: IAM simulation — denied admin action
Write-Evidence "02_iam" "EV-IAM-006-sim-denied-admin.json" {
    aws iam simulate-principal-policy `
        --policy-source-arn "arn:aws:iam::${AccountId}:role/${BedrockRole}" `
        --action-names bedrock:PutModelInvocationLoggingConfiguration `
        --resource-arns "*" `
        --output json
}

# DC-11: IAM simulation — denied non-Claude model
Write-Evidence "02_iam" "EV-IAM-007-sim-denied-non-claude.json" {
    aws iam simulate-principal-policy `
        --policy-source-arn "arn:aws:iam::${AccountId}:role/${BedrockRole}" `
        --action-names bedrock:InvokeModel `
        --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-1-70b-instruct-v1:0" `
        --output json
}

# DC-11: IAM simulation — denied non-Bedrock services (s3, ec2, iam)
Write-Evidence "02_iam" "EV-IAM-006-sim-denied-s3.json" {
    aws iam simulate-principal-policy `
        --policy-source-arn "arn:aws:iam::${AccountId}:role/${BedrockRole}" `
        --action-names s3:ListAllMyBuckets `
        --resource-arns "*" `
        --output json
}
Write-Evidence "02_iam" "EV-IAM-006-sim-denied-ec2.json" {
    aws iam simulate-principal-policy `
        --policy-source-arn "arn:aws:iam::${AccountId}:role/${BedrockRole}" `
        --action-names ec2:DescribeInstances `
        --resource-arns "*" `
        --output json
}
Write-Evidence "02_iam" "EV-IAM-006-sim-denied-iam.json" {
    aws iam simulate-principal-policy `
        --policy-source-arn "arn:aws:iam::${AccountId}:role/${BedrockRole}" `
        --action-names iam:ListRoles `
        --resource-arns "*" `
        --output json
}

# DC-14: Caller identity from host (must run on host)
if (-not $SkipHostTests) {
    Write-Evidence "02_iam" "EV-IAM-008-caller-identity.json" {
        aws sts get-caller-identity --output json
    }
}

# ===================================================================
# CG3 — Region Enforcement  (DC-16, DC-17, DC-40)
# ===================================================================
Write-Host ""
Write-Host "--- CG3: Region Enforcement ---" -ForegroundColor Cyan

# DC-16: Region condition in bedrock-invoke policy (cross-ref CG2 EV-IAM-003)
# Already collected above. Collect explicit region simulation here.
Write-Evidence "03_region_enforcement" "EV-REG-001-sim-approved-region.json" {
    aws iam simulate-principal-policy `
        --policy-source-arn "arn:aws:iam::${AccountId}:role/${BedrockRole}" `
        --action-names bedrock:InvokeModel `
        --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0" `
        --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=us-east-1,ContextKeyType=string" `
        --output json
}

# DC-17: Negative region test — unapproved region simulation
Write-Evidence "03_region_enforcement" "EV-REG-003-sim-denied-region.json" {
    aws iam simulate-principal-policy `
        --policy-source-arn "arn:aws:iam::${AccountId}:role/${BedrockRole}" `
        --action-names bedrock:InvokeModel `
        --resource-arns "arn:aws:bedrock:ap-southeast-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0" `
        --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=ap-southeast-1,ContextKeyType=string" `
        --output json
}

# DC-17: Live negative region test (from host — network-level deny)
if (-not $SkipHostTests) {
    Write-Evidence "03_region_enforcement" "EV-REG-003-negative-region-test.txt" {
        Write-Output "=== Negative region test: ap-southeast-1 ==="
        $env:AWS_DEFAULT_REGION = "ap-southeast-1"
        aws bedrock-runtime converse `
            --model-id "us.anthropic.claude-sonnet-4-6" `
            --messages '[{\"role\":\"user\",\"content\":[{\"text\":\"Say REGION_TEST\"}]}]' `
            --inference-config '{\"maxTokens\":10}' `
            --region ap-southeast-1 2>&1
        Write-Output "Exit code: $LASTEXITCODE"
        Write-Output ""
        Write-Output "=== Control: us-east-1 (should succeed) ==="
        $env:AWS_DEFAULT_REGION = $Region
        aws bedrock-runtime converse `
            --model-id "us.anthropic.claude-sonnet-4-6" `
            --messages '[{\"role\":\"user\",\"content\":[{\"text\":\"Say REGION_TEST\"}]}]' `
            --inference-config '{\"maxTokens\":10}' `
            --region $Region 2>&1
        Write-Output "Exit code: $LASTEXITCODE"
    }
}

# DC-40: Organization / SCP check
Write-Evidence "03_region_enforcement" "EV-REG-004-organization-check.txt" {
    aws organizations describe-organization --output json 2>&1
}

# ===================================================================
# CG4 — KMS Encryption  (DC-18, DC-19)
# ===================================================================
Write-Host ""
Write-Host "--- CG4: KMS Encryption ---" -ForegroundColor Cyan

# DC-18: Key description
Write-Evidence "04_kms" "EV-KMS-001-key-description.json" {
    aws kms describe-key --key-id $KmsAlias --output json
}

# DC-18: Rotation status (requires key ID, not alias)
Write-Evidence "04_kms" "EV-KMS-002-rotation-status.json" {
    aws kms get-key-rotation-status --key-id $KmsKeyId --output json
}

# DC-19: Key policy (requires key ID, not alias)
Write-Evidence "04_kms" "EV-KMS-003-key-policy.json" {
    aws kms get-key-policy --key-id $KmsKeyId --policy-name default --output text
}

# DC-18: Key aliases
Write-Evidence "04_kms" "EV-KMS-004-aliases.json" {
    aws kms list-aliases `
        --query "Aliases[?AliasName=='$KmsAlias']" --output json
}

# ===================================================================
# CG5 — Secrets Manager  (DC-20, DC-21, DC-22)
# ===================================================================
Write-Host ""
Write-Host "--- CG5: Secrets Manager ---" -ForegroundColor Cyan

# DC-20: Secrets list
Write-Evidence "05_secrets_manager" "EV-SM-001-secrets-list.json" {
    aws secretsmanager list-secrets `
        --filters Key=name,Values=proposal-orchestrator `
        --output json
}

# DC-20: Secret description
Write-Evidence "05_secrets_manager" "EV-SM-002-secret-description.json" {
    aws secretsmanager describe-secret `
        --secret-id $SecretId --output json
}

# DC-20: KMS key association
Write-Evidence "05_secrets_manager" "EV-SM-003-kms-key-association.txt" {
    aws secretsmanager describe-secret `
        --secret-id $SecretId `
        --query "KmsKeyId" --output text
}

# DC-21: Resource policy
Write-Evidence "05_secrets_manager" "EV-SM-004-resource-policy.json" {
    aws secretsmanager get-resource-policy `
        --secret-id $SecretId --output json
}

# DC-22: Rotation configuration
Write-Evidence "05_secrets_manager" "EV-SM-005-rotation-configuration.json" {
    aws secretsmanager describe-secret `
        --secret-id $SecretId `
        --query "{RotationEnabled:RotationEnabled,RotationRules:RotationRules,RotationLambdaARN:RotationLambdaARN}" `
        --output json
}

# DC-21: Retrieval test (from host only — needs role assumption)
if (-not $SkipHostTests) {
    Write-Evidence "05_secrets_manager" "EV-SM-006-retrieval-test.txt" {
        aws secretsmanager get-secret-value `
            --secret-id $SecretId `
            --query "Name" --output text 2>&1
        Write-Output "Exit code: $LASTEXITCODE"
    }
}

# ===================================================================
# CG6 — CloudTrail  (DC-23..DC-27)
# ===================================================================
Write-Host ""
Write-Host "--- CG6: CloudTrail ---" -ForegroundColor Cyan

# DC-23: Trail configuration
Write-Evidence "06_cloudtrail" "EV-CT-001-trail-configuration.json" {
    aws cloudtrail describe-trails `
        --trail-name-list $TrailName `
        --region $Region --output json
}

# DC-23: Trail status (IsLogging)
Write-Evidence "06_cloudtrail" "EV-CT-002-trail-status.json" {
    aws cloudtrail get-trail-status `
        --name $TrailName `
        --region $Region --output json
}

# DC-24: Log file validation
Write-Evidence "06_cloudtrail" "EV-CT-003-log-file-validation.txt" {
    aws cloudtrail describe-trails `
        --trail-name-list $TrailName `
        --query "trailList[0].LogFileValidationEnabled" `
        --region $Region --output text
}

# DC-23: KMS encryption
Write-Evidence "06_cloudtrail" "EV-CT-004-kms-encryption.txt" {
    aws cloudtrail describe-trails `
        --trail-name-list $TrailName `
        --query "trailList[0].KmsKeyId" `
        --region $Region --output text
}

# DC-23: Event selectors
Write-Evidence "06_cloudtrail" "EV-CT-005-event-selectors.json" {
    aws cloudtrail get-event-selectors `
        --trail-name $TrailName `
        --region $Region --output json
}

# DC-26: Recent Bedrock Converse events
Write-Evidence "06_cloudtrail" "EV-CT-006-bedrock-converse-events.json" {
    aws cloudtrail lookup-events `
        --lookup-attributes AttributeKey=EventName,AttributeValue=Converse `
        --max-results 10 `
        --region $Region --output json
}

# DC-26: Recent Bedrock InvokeModel events (may be empty if only Converse used)
Write-Evidence "06_cloudtrail" "EV-CT-006b-bedrock-invokemodel-events.json" {
    aws cloudtrail lookup-events `
        --lookup-attributes AttributeKey=EventName,AttributeValue=InvokeModel `
        --max-results 10 `
        --region $Region --output json
}

# DC-25: Trail S3 bucket policy
Write-Evidence "06_cloudtrail" "EV-CT-007-s3-bucket-policy.json" {
    aws s3api get-bucket-policy --bucket $TrailBucket --output json
}

# DC-27: S3 lifecycle configuration
Write-Evidence "06_cloudtrail" "EV-CT-008-s3-lifecycle.json" {
    aws s3api get-bucket-lifecycle-configuration --bucket $TrailBucket --output json
}

# DC-25: S3 versioning status
Write-Evidence "06_cloudtrail" "EV-CT-009-s3-versioning.json" {
    aws s3api get-bucket-versioning --bucket $TrailBucket --output json
}

# DC-25: S3 public access block
Write-Evidence "06_cloudtrail" "EV-CT-010-s3-public-access-block.json" {
    aws s3api get-public-access-block --bucket $TrailBucket --output json
}

# ===================================================================
# CG7 — CloudWatch  (DC-28, DC-29, DC-30)
# ===================================================================
Write-Host ""
Write-Host "--- CG7: CloudWatch ---" -ForegroundColor Cyan

# DC-28: Bedrock invocation logging configuration (should be null/empty)
Write-Evidence "07_cloudwatch" "EV-CW-001-invocation-logging-config.json" {
    aws bedrock get-model-invocation-logging-configuration `
        --region $Region --output json
}

# DC-29: No /aws/bedrock log groups
Write-Evidence "07_cloudwatch" "EV-CW-003-bedrock-log-groups.json" {
    aws logs describe-log-groups `
        --log-group-name-prefix "/aws/bedrock" `
        --region $Region --output json
}

# DC-30: Operational log groups (encryption + retention)
Write-Evidence "07_cloudwatch" "EV-CW-004-operational-log-groups.json" {
    aws logs describe-log-groups `
        --log-group-name-prefix "/proposal-orchestrator" `
        --region $Region --output json
}

# ===================================================================
# CG8 — Data Egress Prevention  (DC-07, DC-08, DC-31, DC-32)
# ===================================================================
Write-Host ""
Write-Host "--- CG8: Data Egress Prevention ---" -ForegroundColor Cyan

# DC-07: Host security group (outbound rules)
Write-Evidence "08_data_egress" "EV-DEP-002-host-sg.json" {
    aws ec2 describe-security-groups `
        --group-ids $HostSg `
        --region $Region --output json
}

# DC-08: VPC flow logs on both subnets
Write-Evidence "08_data_egress" "EV-DEP-003-flow-logs-subnet-a.json" {
    aws ec2 describe-flow-logs `
        --filter "Name=resource-id,Values=$SubnetA" `
        --region $Region --output json
}
Write-Evidence "08_data_egress" "EV-DEP-003-flow-logs-subnet-b.json" {
    aws ec2 describe-flow-logs `
        --filter "Name=resource-id,Values=$SubnetB" `
        --region $Region --output json
}

# DC-08: Flow logs log group (retention + encryption)
Write-Evidence "08_data_egress" "EV-DEP-003-flow-log-group.json" {
    aws logs describe-log-groups `
        --log-group-name-prefix $FlowLogGroupName `
        --region $Region --output json
}

# DC-31: No Claude CLI on deployment host (must run on host)
if (-not $SkipHostTests) {
    Write-Evidence "08_data_egress" "EV-DEP-004-no-claude-cli.txt" {
        Write-Output "=== which claude ==="
        which claude 2>&1
        Write-Output "Exit code: $LASTEXITCODE"
        Write-Output ""
        Write-Output "=== claude --version ==="
        claude --version 2>&1
        Write-Output "Exit code: $LASTEXITCODE"
    }
}

# DC-32: Internet egress blocked (must run on host)
if (-not $SkipHostTests) {
    Write-Evidence "08_data_egress" "EV-DEP-005-egress-tests.txt" {
        Write-Output "=== curl api.anthropic.com ==="
        curl -s --connect-timeout 5 https://api.anthropic.com 2>&1
        Write-Output "Exit code: $LASTEXITCODE"
        Write-Output ""
        Write-Output "=== curl api.together.ai ==="
        curl -s --connect-timeout 5 https://api.together.ai 2>&1
        Write-Output "Exit code: $LASTEXITCODE"
    }
}

# DC-06 + DC-32: Route table (cross-ref CG1 — collected again for completeness)
Write-Evidence "08_data_egress" "EV-DEP-001-route-table.json" {
    aws ec2 describe-route-tables `
        --route-table-ids $RouteTableId `
        --query "RouteTables[].Routes" `
        --region $Region --output json
}

# ===================================================================
# CG9 — Production Application Configuration  (DC-33..DC-36)
# ===================================================================
Write-Host ""
Write-Host "--- CG9: Production Application Config ---" -ForegroundColor Cyan

# DC-33, DC-34, DC-35: Secret env-config values (name only — not secret value)
Write-Evidence "09_production_config" "EV-APP-001-secret-metadata.json" {
    aws secretsmanager describe-secret `
        --secret-id $SecretId --output json
}

# DC-33, DC-34, DC-35: Secret key names (from host — redacts values for audit)
if (-not $SkipHostTests) {
    Write-Evidence "09_production_config" "EV-APP-001-config-keys.txt" {
        Write-Output "=== Secret key names (values redacted) ==="
        $val = aws secretsmanager get-secret-value --secret-id $SecretId --query "SecretString" --output text
        # Only output key names, not values
        ($val | ConvertFrom-Json).PSObject.Properties | ForEach-Object { "$($_.Name)=<REDACTED>" }
    }
}

# DC-36: Model availability in target region
Write-Evidence "09_production_config" "EV-APP-002-model-availability.json" {
    aws bedrock list-foundation-models `
        --region $Region `
        --query "modelSummaries[?contains(modelId,'claude-sonnet')].[modelId,modelName,providerName]" `
        --output json
}

# DC-36: Inference profile availability
Write-Evidence "09_production_config" "EV-APP-002-inference-profiles.json" {
    aws bedrock list-inference-profiles `
        --region $Region `
        --query "inferenceProfileSummaries[?contains(inferenceProfileId,'claude')].[inferenceProfileId,status]" `
        --output json
}

# ===================================================================
# CG10 — Compliance  (DC-39)
# ===================================================================
Write-Host ""
Write-Host "--- CG10: Compliance ---" -ForegroundColor Cyan

# DC-39: GDPR DPA — check if evidence already exists (this is a manual/document review)
Write-Evidence "10_compliance" "EV-COMP-001-gdpr-dpa-check.txt" {
    Write-Output "=== GDPR DPA Assessment ==="
    Write-Output "AWS GDPR Data Processing terms are incorporated into the AWS Customer Agreement"
    Write-Output "by default since November 2018. No separate DPA acceptance required."
    Write-Output ""
    Write-Output "Verification: AWS Artifact > Agreements (console review required)"
    Write-Output "Account: $AccountId"
    Write-Output "Date: $timestamp"
}

# ===================================================================
# Functional Validation (DC-37, DC-38)
# ===================================================================
Write-Host ""
Write-Host "--- Functional Validation ---" -ForegroundColor Cyan

# DC-37: End-to-end Bedrock Converse call (must run on host)
if (-not $SkipHostTests) {
    Write-Evidence "09_production_config" "EV-E2E-001-converse-test.txt" {
        python3 -c @"
import boto3, time, json
client = boto3.client('bedrock-runtime', region_name='$Region')
start = time.time()
try:
    response = client.converse(
        modelId='us.anthropic.claude-sonnet-4-6',
        messages=[{'role': 'user', 'content': [{'text': 'Respond with exactly: MODEL_AVAILABLE'}]}],
        inferenceConfig={'maxTokens': 10}
    )
    elapsed = int((time.time() - start) * 1000)
    status = response['ResponseMetadata']['HTTPStatusCode']
    output = response['output']['message']['content'][0]['text']
    caller = boto3.client('sts').get_caller_identity()
    print(f'Status: {status}')
    print(f'Output: {output}')
    print(f'Latency: {elapsed}ms')
    print(f'Caller: {caller["Arn"]}')
    print(f'Account: {caller["Account"]}')
except Exception as e:
    print(f'ERROR: {e}')
"@
    }
}

# ===================================================================
# Integrity Manifest
# ===================================================================
Write-Host ""
Write-Host "--- Generating integrity manifest ---" -ForegroundColor Cyan

Write-Evidence "11_audit_package" "evidence_integrity_manifest.txt" {
    Write-Output "Evidence Integrity Manifest"
    Write-Output "Generated: $timestamp"
    Write-Output "Git commit: $(git -C (Split-Path $EvidenceRoot) rev-parse HEAD 2>$null)"
    Write-Output "Algorithm: SHA-256"
    Write-Output "---"
    Get-ChildItem -Path $EvidenceRoot -Recurse -File |
        Where-Object { $_.FullName -notmatch "11_audit_package" } |
        Sort-Object FullName |
        ForEach-Object {
            $hash = (Get-FileHash -Path $_.FullName -Algorithm SHA256).Hash.ToLower()
            $rel = $_.FullName.Substring($EvidenceRoot.Length + 1).Replace('\', '/')
            "$hash  $rel"
        }
}

# ===================================================================
# Summary
# ===================================================================
Write-Host ""
$summaryColor = if ($script:failCount -eq 0) { "Green" } else { "Red" }
Write-Host "=================================================================" -ForegroundColor $summaryColor
Write-Host " Evidence collection complete." -ForegroundColor $summaryColor
Write-Host ""
Write-Host " Results:  $($script:passCount) OK / $($script:failCount) FAILED"
Write-Host " Evidence root: $EvidenceRoot"
Write-Host " Manifest:      11_audit_package/evidence_integrity_manifest.txt"
Write-Host ""
if ($SkipHostTests) {
    Write-Host " NOTE: Host-only tests were skipped (-SkipHostTests)." -ForegroundColor Yellow
    Write-Host " The following evidence requires running ON the deployment host:" -ForegroundColor Yellow
    Write-Host "   EV-PL-002  (DNS resolution)" -ForegroundColor Yellow
    Write-Host "   EV-IAM-008 (caller identity)" -ForegroundColor Yellow
    Write-Host "   EV-REG-003 (live negative region test)" -ForegroundColor Yellow
    Write-Host "   EV-SM-006  (secret retrieval test)" -ForegroundColor Yellow
    Write-Host "   EV-DEP-004 (no Claude CLI)" -ForegroundColor Yellow
    Write-Host "   EV-DEP-005 (egress tests)" -ForegroundColor Yellow
    Write-Host "   EV-APP-001 (config keys)" -ForegroundColor Yellow
    Write-Host "   EV-E2E-001 (Converse test)" -ForegroundColor Yellow
}
Write-Host "================================================================="
