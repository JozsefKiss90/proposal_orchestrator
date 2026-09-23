 Control Group 2 — IAM Least Privilege

  Controls

  ┌────────────┬───────────────────────────────────────────────────────────────────────────────┐
  │ Control ID │                                   Objective                                   │
  ├────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ DC-09      │ Create dedicated IAM role for Bedrock execution                               │
  ├────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ DC-10      │ Attach Bedrock invocation policy (scoped to Claude models + approved regions) │
  ├────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ DC-11      │ Attach explicit deny statements                                               │
  ├────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ DC-12      │ Attach permission boundary                                                    │
  ├────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ DC-13      │ Configure trust policy for EC2 with VPC condition                             │
  ├────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ DC-14      │ Associate instance profile with deployment host                               │
  ├────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ DC-15      │ Confirm no long-term access keys on host                                      │
  └────────────┴───────────────────────────────────────────────────────────────────────────────┘

  Implementation Steps

  Step 1: Create the Permission Boundary Policy

  Run from CloudShell or local AWS CLI:

  # Create the permission boundary policy
  aws iam create-policy \
      --policy-name proposal-orchestrator-boundary \
      --description "Permission boundary for Proposal Orchestrator Bedrock execution role" \
      --policy-document '{
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
      }' \
      --tags Key=project,Value=proposal-orchestrator \
      --region us-east-1

  Save the returned Policy ARN — you'll need it in Step 3.

  Step 2: Create the Bedrock Invocation Policy

  # Create the Bedrock invocation policy (scoped to Claude models + approved regions)
  aws iam create-policy \
      --policy-name proposal-orchestrator-bedrock-invoke \
      --description "Allow Bedrock Converse on Claude models in approved regions only" \
      --policy-document '{
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
      }' \
      --tags Key=project,Value=proposal-orchestrator \
      --region us-east-1

  Step 3: Create the Supporting Services Policy

  aws iam create-policy \
      --policy-name proposal-orchestrator-supporting-services \
      --description "Allow Secrets Manager retrieval and KMS decrypt for Proposal Orchestrator" \
      --policy-document '{
          "Version": "2012-10-17",
          "Statement": [
              {
                  "Sid": "AllowSecretsRetrieval",
                  "Effect": "Allow",
                  "Action": [
                      "secretsmanager:GetSecretValue"
                  ],
                  "Resource": [
                      "arn:aws:secretsmanager:us-east-1:232538551827:secret:proposal-orchestrator/*"
                  ]
              },
              {
                  "Sid": "AllowKMSDecrypt",
                  "Effect": "Allow",
                  "Action": [
                      "kms:Decrypt",
                      "kms:DescribeKey"
                  ],
                  "Resource": "*"
              }
          ]
      }' \
      --tags Key=project,Value=proposal-orchestrator \
      --region us-east-1

  Note: The KMS resource will be scoped to the specific key ARN after the CMK is created in Control Group 4. For now "*" is acceptable and will be tightened.

  Step 4: Create the Explicit Deny Policy

  aws iam create-policy \
      --policy-name proposal-orchestrator-explicit-deny \
      --description "Explicit deny for Bedrock admin, non-Bedrock services, and non-Claude models" \
      --policy-document '{
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
      }' \
      --tags Key=project,Value=proposal-orchestrator \
      --region us-east-1

  Step 5: Create the Bedrock Execution Role

  # Create the role with trust policy for EC2 + VPC condition
  aws iam create-role \
      --role-name proposal-orchestrator-bedrock-role \
      --assume-role-policy-document '{
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
                          "aws:SourceVpc": "vpc-050a09774560fd774"
                      }
                  }
              }
          ]
      }' \
      --permissions-boundary arn:aws:iam::232538551827:policy/proposal-orchestrator-boundary \
      --tags Key=project,Value=proposal-orchestrator \
      --region us-east-1

  Important note on aws:SourceVpc in trust policies: The aws:SourceVpc condition key on sts:AssumeRole is supported for VPC endpoint-based calls. However, if the EC2 instance assumes
  the role via the instance metadata service (IMDS), the condition may not match because IMDS calls don't traverse a VPC endpoint. If role assumption fails, remove the Condition block
  and rely on the instance profile binding instead. I'll note this as a potential issue to watch for.

  Step 6: Attach All Policies to the Role

  # Attach Bedrock invocation policy
  aws iam attach-role-policy \
      --role-name proposal-orchestrator-bedrock-role \
      --policy-arn arn:aws:iam::232538551827:policy/proposal-orchestrator-bedrock-invoke

  # Attach supporting services policy
  aws iam attach-role-policy \
      --role-name proposal-orchestrator-bedrock-role \
      --policy-arn arn:aws:iam::232538551827:policy/proposal-orchestrator-supporting-services

  # Attach explicit deny policy
  aws iam attach-role-policy \
      --role-name proposal-orchestrator-bedrock-role \
      --policy-arn arn:aws:iam::232538551827:policy/proposal-orchestrator-explicit-deny

  Step 7: Verify with simulate-principal-policy

  These commands verify the effective permissions without needing the role on an instance:

  # =====================================================
  # POSITIVE TESTS — should return "allowed"
  # =====================================================

  # Test 1: InvokeModel on Claude Sonnet in us-east-1
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:InvokeModel \
      --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0" \
      --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=us-east-1,ContextKeyType=string" \
      --output table

  # Test 2: InvokeModel on Claude inference profile
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:InvokeModel \
      --resource-arns "arn:aws:bedrock:us-east-1:232538551827:inference-profile/us.anthropic.claude-sonnet-4-6" \
      --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=us-east-1,ContextKeyType=string" \
      --output table

  # =====================================================
  # NEGATIVE TESTS — should return "implicitDeny" or "explicitDeny"
  # =====================================================

  # Test 3: Bedrock admin action (should be explicitly denied)
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:CreateModelCustomizationJob \
      --resource-arns "*" \
      --output table

  # Test 4: Non-Claude model (should be explicitly denied)
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:InvokeModel \
      --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-1-70b-instruct-v1:0" \
      --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=us-east-1,ContextKeyType=string" \
      --output table

  # Test 5: S3 access (should be explicitly denied)
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names s3:ListBuckets \
      --resource-arns "*" \
      --output table

  # Test 6: EC2 access (should be explicitly denied)
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names ec2:DescribeInstances \
      --resource-arns "*" \
      --output table

  # Test 7: IAM access (should be explicitly denied)
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names iam:ListRoles \
      --resource-arns "*" \
      --output table

  # Test 8: Unapproved region (should be implicitly denied — no allow for ap-southeast-1)
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:InvokeModel \
      --resource-arns "arn:aws:bedrock:ap-southeast-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0" \
      --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=ap-southeast-1,ContextKeyType=string" \
      --output table

  # Test 9: PutModelInvocationLoggingConfiguration (should be explicitly denied)
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:PutModelInvocationLoggingConfiguration \
      --resource-arns "*" \
      --output table

  Step 8: Collect Role Configuration Evidence

  # =====================================================
  # EVIDENCE COLLECTION — Control Group 2: IAM
  # Save to: docs/infrastructure_security/evidence/02_iam/
  # =====================================================

  # EV-IAM-001: Role configuration
  aws iam get-role \
      --role-name proposal-orchestrator-bedrock-role \
      --output json > EV-IAM-001-role-config.json

  # EV-IAM-002: Attached policies
  aws iam list-attached-role-policies \
      --role-name proposal-orchestrator-bedrock-role \
      --output json > EV-IAM-002-attached-policies.json

  # EV-IAM-003: Each policy document
  # Get the policy version for each attached policy
  for POLICY_ARN in \
      "arn:aws:iam::232538551827:policy/proposal-orchestrator-bedrock-invoke" \
      "arn:aws:iam::232538551827:policy/proposal-orchestrator-supporting-services" \
      "arn:aws:iam::232538551827:policy/proposal-orchestrator-explicit-deny"; do
      POLICY_NAME=$(echo $POLICY_ARN | awk -F/ '{print $NF}')
      VERSION=$(aws iam get-policy --policy-arn $POLICY_ARN --query 'Policy.DefaultVersionId' --output text)
      aws iam get-policy-version \
          --policy-arn $POLICY_ARN \
          --version-id $VERSION \
          --output json > "EV-IAM-003-policy-${POLICY_NAME}.json"
  done

  # EV-IAM-004: Permission boundary
  aws iam get-role \
      --role-name proposal-orchestrator-bedrock-role \
      --query "Role.PermissionsBoundary" \
      --output json > EV-IAM-004-permission-boundary.json

  # Export boundary policy document
  BOUNDARY_VERSION=$(aws iam get-policy \
      --policy-arn arn:aws:iam::232538551827:policy/proposal-orchestrator-boundary \
      --query 'Policy.DefaultVersionId' --output text)
  aws iam get-policy-version \
      --policy-arn arn:aws:iam::232538551827:policy/proposal-orchestrator-boundary \
      --version-id $BOUNDARY_VERSION \
      --output json > EV-IAM-004-boundary-policy-document.json

  # EV-IAM-005: Allowed action simulation results
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:InvokeModel \
      --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0" \
      --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=us-east-1,ContextKeyType=string" \
      --output json > EV-IAM-005-allowed-simulation.json

  # EV-IAM-006: Denied action simulations
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:CreateModelCustomizationJob s3:ListBuckets ec2:DescribeInstances iam:ListRoles \
      --resource-arns "*" \
      --output json > EV-IAM-006-denied-simulation.json

  # EV-IAM-007: Non-Claude model denied
  aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role \
      --action-names bedrock:InvokeModel \
      --resource-arns "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-1-70b-instruct-v1:0" \
      --context-entries "ContextKeyName=aws:RequestedRegion,ContextKeyValues=us-east-1,ContextKeyType=string" \
      --output json > EV-IAM-007-non-claude-denied.json

  # EV-IAM-010: Trust policy
  aws iam get-role \
      --role-name proposal-orchestrator-bedrock-role \
      --query "Role.AssumeRolePolicyDocument" \
      --output json > EV-IAM-010-trust-policy.json

  Step 9: Prepare Validation Host for Functional Test (DC-37 / PL-6)

  The existing instance profile uses an SSM-only role. To test Bedrock from the host, update the existing role to also have Bedrock permissions:

  # Attach Bedrock invocation policy to the existing SSM role
  aws iam attach-role-policy \
      --role-name proposal-orchestrator-ec2-ssm-role \
      --policy-arn arn:aws:iam::232538551827:policy/proposal-orchestrator-bedrock-invoke

  # Verify policies on SSM role
  aws iam list-attached-role-policies \
      --role-name proposal-orchestrator-ec2-ssm-role \
      --output table

  Then from the deployment host (via SSM Session Manager):

  # EV-IAM-008: Caller identity from host
  aws sts get-caller-identity --output json | tee /tmp/EV-IAM-008-caller-identity.json

  # DC-37 / PL-6: Functional Bedrock test
  python3 -c "
  import boto3, json, datetime
  print('=== DC-37/PL-6: Functional Bedrock Converse Test ===')
  print(f'Date: {datetime.datetime.utcnow().isoformat()}Z')
  print()
  try:
      client = boto3.client('bedrock-runtime', region_name='us-east-1')
      response = client.converse(
          modelId='us.anthropic.claude-sonnet-4-6',
          messages=[{'role': 'user', 'content': [{'text': 'Say OK'}]}],
          inferenceConfig={'maxTokens': 10}
      )
      print(f'HTTP Status: {response[\"ResponseMetadata\"][\"HTTPStatusCode\"]}')
      print(f'Model Output: {response[\"output\"][\"message\"][\"content\"][0][\"text\"]}')
      print(f'Request ID: {response[\"ResponseMetadata\"][\"RequestId\"]}')
      print('RESULT: PASS')
  except Exception as e:
      print(f'ERROR: {type(e).__name__}: {e}')
      print('RESULT: FAIL')
  " 2>&1 | tee /tmp/EV-PL-006-functional-test.txt

  # EV-IAM-009: Negative tests from host
  echo "=== Negative Test: aws s3 ls ===" > /tmp/EV-IAM-009-negative-tests.txt
  aws s3 ls 2>&1 >> /tmp/EV-IAM-009-negative-tests.txt
  echo "" >> /tmp/EV-IAM-009-negative-tests.txt
  echo "=== Negative Test: aws ec2 describe-instances ===" >> /tmp/EV-IAM-009-negative-tests.txt
  aws ec2 describe-instances 2>&1 >> /tmp/EV-IAM-009-negative-tests.txt
  cat /tmp/EV-IAM-009-negative-tests.txt

  Step 10: Scope the Bedrock VPC Endpoint Policy (Resolves DC-04 from CG1)

  After the role exists, tighten the endpoint policy:

  aws ec2 modify-vpc-endpoint \
      --vpc-endpoint-id vpce-0843d225c5b1ef6d5 \
      --policy-document '{
          "Version": "2012-10-17",
          "Statement": [
              {
                  "Sid": "AllowBedrockConverseOnly",
                  "Effect": "Allow",
                  "Principal": {
                      "AWS": [
                          "arn:aws:iam::232538551827:role/proposal-orchestrator-bedrock-role",
                          "arn:aws:iam::232538551827:role/proposal-orchestrator-ec2-ssm-role"
                      ]
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
      }' \
      --region us-east-1

  # Verify updated policy
  aws ec2 describe-vpc-endpoints \
      --vpc-endpoint-ids vpce-0843d225c5b1ef6d5 \
      --query "VpcEndpoints[].PolicyDocument" \
      --output json \
      --region us-east-1

  ---
  Evidence Artifact Summary

  Save all files under docs/infrastructure_security/evidence/02_iam/:

  ┌──────────────────────────────────────────┬─────────────────────────────────────────────────┬────────────────┐
  │              Evidence File               │                     Source                      │    Resolves    │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-001-role-config.json              │ aws iam get-role                                │ DC-09          │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-002-attached-policies.json        │ aws iam list-attached-role-policies             │ DC-10, DC-11   │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-003-policy-*.json                 │ Policy version documents (3 files)              │ DC-10, DC-11   │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-004-permission-boundary.json      │ get-role PermissionsBoundary                    │ DC-12          │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-004-boundary-policy-document.json │ Boundary policy document                        │ DC-12          │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-005-allowed-simulation.json       │ simulate-principal-policy for Claude            │ DC-10 positive │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-006-denied-simulation.json        │ simulate-principal-policy for admin/S3/EC2/IAM  │ DC-11          │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-007-non-claude-denied.json        │ simulate-principal-policy for Llama             │ DC-11          │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-008-caller-identity.json          │ sts get-caller-identity from host               │ DC-14, DC-15   │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-009-negative-tests.txt            │ aws s3 ls, aws ec2 describe-instances from host │ DC-15          │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-IAM-010-trust-policy.json             │ get-role AssumeRolePolicyDocument               │ DC-13          │
  ├──────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────┤
  │ EV-PL-006-functional-test.txt            │ converse() from host                            │ DC-37/PL-6     │
  └──────────────────────────────────────────┴─────────────────────────────────────────────────┴────────────────┘

  ---
  PASS / FAIL Criteria

  ┌───────┬────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────┐
  │   #   │     Criterion      │                                              PASS Condition                                               │             FAIL Condition              │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-1 │ Role exists        │ proposal-orchestrator-bedrock-role exists with correct trust policy (EV-IAM-001)                          │ Role missing or wrong trust             │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-2 │ Least privilege    │ Only Bedrock invoke + SecretsManager get + KMS decrypt allowed (EV-IAM-002, EV-IAM-003)                   │ Broad permissions (* without            │
  │       │                    │                                                                                                           │ conditions)                             │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-3 │ Region lock        │ aws:RequestedRegion condition in invocation policy limits to eu-west-1 and us-east-1 (EV-IAM-003,         │ No region condition or unapproved       │
  │       │                    │ EV-IAM-005)                                                                                               │ regions                                 │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-4 │ Model scope        │ Only anthropic.claude-* in resource statements (EV-IAM-003)                                               │ Wildcard model ARNs                     │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-5 │ Deny statements    │ Explicit deny for Bedrock admin, non-Bedrock services, non-Claude models (EV-IAM-003, EV-IAM-006,         │ Missing deny statements                 │
  │       │                    │ EV-IAM-007)                                                                                               │                                         │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-6 │ Permission         │ Boundary attached, limits max scope (EV-IAM-004)                                                          │ No boundary or overly permissive        │
  │       │ boundary           │                                                                                                           │                                         │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-7 │ No access keys     │ Host uses instance profile, no AWS_ACCESS_KEY_ID in env or files (EV-IAM-008)                             │ Long-term keys found                    │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-8 │ Negative tests     │ aws s3 ls and aws ec2 describe-instances fail from host (EV-IAM-009)                                      │ Unauthorized calls succeed              │
  ├───────┼────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ IAM-9 │ Functional test    │ converse() returns HTTP 200 from host (EV-PL-006)                                                         │ Call fails                              │
  └───────┴────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────┘

  ---
  Execution Order

  1. Steps 1-4: Create all policies (from CloudShell or local CLI)
  2. Steps 5-6: Create role and attach policies
  3. Step 7: Run simulation tests (verify before touching the instance)
  4. Step 8: Collect role configuration evidence
  5. Step 9: Add Bedrock permissions to SSM role, run functional test + negative tests from host
  6. Step 10: Scope the Bedrock VPC endpoint policy (resolves DC-04 from CG1)

  Save all evidence under docs/infrastructure_security/evidence/02_iam/ and confirm when ready for review.

  I am now waiting for you to implement and provide the evidence.
