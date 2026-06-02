 Control Group 1 — VPC Endpoint / AWS PrivateLink for Bedrock
                                                                                                                                                                                         
  Target Architecture
                                                                                                                                                                                         
  Deployment Host (EC2/ECS, private subnet)                                        
      |
      +-- boto3.client("bedrock-runtime")
      |       |
      |       +-- DNS: bedrock-runtime.<region>.amazonaws.com
      |               |
      |               +-- Resolves to PRIVATE IPs (10.x.x.x / 172.x.x.x)
      |                       via Private DNS on VPC Endpoint
      |
      +-- VPC Private Subnet (no IGW route, no NAT for Bedrock)
              |
              +-- VPC Interface Endpoint: com.amazonaws.<region>.bedrock-runtime
              |       +-- Private DNS: ENABLED
              |       +-- Security Group: TCP 443 inbound from host SG only
              |       +-- Endpoint Policy: scoped to Bedrock invoke + Claude models
              |       +-- Powered by AWS PrivateLink
              |
              +-- VPC Interface Endpoint: com.amazonaws.<region>.secretsmanager
              +-- VPC Interface Endpoint: com.amazonaws.<region>.sts
              +-- VPC Gateway Endpoint: com.amazonaws.<region>.s3
              +-- (Optional) Interface Endpoints: logs, monitoring

  Key principle: When Private DNS is enabled on the VPC endpoint, the standard Bedrock hostname (bedrock-runtime.<region>.amazonaws.com) automatically resolves to the endpoint's private
   IPs. No endpoint_url parameter is needed in boto3 — traffic routes through PrivateLink transparently. This is the recommended configuration per the AWS docs.

  If Private DNS is NOT enabled, you must explicitly pass endpoint_url="https://<vpce-id>.bedrock-runtime.<region>.vpce.amazonaws.com" to every boto3 client call. Enable Private DNS to
  avoid this.

  ---
  Implementation Steps

  Prerequisites

  Before starting, confirm:
  1. You have a VPC with at least one private subnet (no IGW route)
  2. You know your VPC ID, subnet IDs, and the security group ID of the deployment host
  3. You have decided on your primary region (eu-west-1 or us-east-1)
  4. DNS hostnames and DNS resolution are enabled on the VPC

  Replace these placeholders throughout:
  - <REGION> — your target region (e.g., eu-west-1)
  - <VPC_ID> — your VPC ID (e.g., vpc-0abc123def456)
  - <SUBNET_IDS> — comma-separated subnet IDs
  - <ACCOUNT_ID> — your AWS account ID
  - <HOST_SG_ID> — security group of the deployment host
  - <BEDROCK_ROLE_NAME> — name of the Bedrock execution IAM role (created in Control Group 2)

  ---
  Step 1: Create the VPC Endpoint Security Group

  AWS Console

  1. Go to VPC > Security Groups > Create security group
  2. Name: proposal-orchestrator-vpce-sg
  3. Description: Security group for Bedrock VPC endpoints - TCP 443 only
  4. VPC: select your deployment VPC
  5. Inbound rules:
    - Type: HTTPS, Protocol: TCP, Port: 443, Source: <HOST_SG_ID> (the deployment host's security group)
  6. Outbound rules:
    - Remove the default "allow all" outbound rule (VPC endpoints don't need outbound)
  7. Tags: Name=proposal-orchestrator-vpce-sg, project=proposal-orchestrator
  8. Click Create security group

  AWS CLI / CloudShell

  # Create security group for VPC endpoints
  VPCE_SG_ID=$(aws ec2 create-security-group \
      --group-name "proposal-orchestrator-vpce-sg" \
      --description "Security group for Bedrock VPC endpoints - TCP 443 only" \
      --vpc-id <VPC_ID> \
      --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=proposal-orchestrator-vpce-sg},{Key=project,Value=proposal-orchestrator}]' \
      --query 'GroupId' \
      --output text \
      --region <REGION>)
  echo "Created VPC Endpoint SG: $VPCE_SG_ID"

  # Add inbound rule: TCP 443 from deployment host SG
  aws ec2 authorize-security-group-ingress \
      --group-id $VPCE_SG_ID \
      --protocol tcp \
      --port 443 \
      --source-group <HOST_SG_ID> \
      --region <REGION>

  # Revoke default outbound allow-all rule
  aws ec2 revoke-security-group-egress \
      --group-id $VPCE_SG_ID \
      --protocol all \
      --port all \
      --cidr 0.0.0.0/0 \
      --region <REGION>

  ---
  Step 2: Create the Bedrock Runtime VPC Endpoint

  AWS Console

  1. Go to VPC > Endpoints > Create endpoint
  2. Name tag: proposal-orchestrator-bedrock-runtime
  3. Service category: AWS services
  4. Service name: search for bedrock-runtime, select com.amazonaws.<REGION>.bedrock-runtime
  5. VPC: select your deployment VPC
  6. Enable DNS name: checked (Private DNS)
    - Note: VPC must have DNS hostnames and DNS resolution enabled
  7. Subnets: select all subnets where deployment host may run
  8. Security groups: select proposal-orchestrator-vpce-sg
  9. Policy: Custom — paste the scoped policy below (or use Full Access initially, then scope later)
  10. Tags: project=proposal-orchestrator
  11. Click Create endpoint

  AWS CLI / CloudShell

  # Create Bedrock Runtime VPC endpoint with Private DNS enabled
  aws ec2 create-vpc-endpoint \
      --vpc-endpoint-type Interface \
      --service-name com.amazonaws.<REGION>.bedrock-runtime \
      --vpc-id <VPC_ID> \
      --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
      --security-group-ids $VPCE_SG_ID \
      --private-dns-enabled \
      --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=proposal-orchestrator-bedrock-runtime},{Key=project,Value=proposal-orchestrator}]' \
      --region <REGION>

  VPC Endpoint Policy (Defense in Depth — recommended)

  After creating the endpoint (or during creation via Console "Custom" policy), attach this scoped policy:

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

  Note: If you haven't created the IAM role yet (Control Group 2), use "Principal": "*" temporarily with just the action and resource restrictions, then update it after the role exists.
   Alternatively, use the simpler policy from AWS docs:

  {
      "Version": "2012-10-17",
      "Statement": [
          {
              "Principal": "*",
              "Effect": "Allow",
              "Action": [
                  "bedrock:InvokeModel",
                  "bedrock:InvokeModelWithResponseStream"
              ],
              "Resource": "*"
          }
      ]
  }

  Then tighten after IAM role creation.

  ---
  Step 3: Create Supporting VPC Endpoints

  These are needed so the deployment host can reach Secrets Manager, STS, and S3 without internet access.

  AWS CLI / CloudShell

  # Secrets Manager (Interface endpoint)
  aws ec2 create-vpc-endpoint \
      --vpc-endpoint-type Interface \
      --service-name com.amazonaws.<REGION>.secretsmanager \
      --vpc-id <VPC_ID> \
      --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
      --security-group-ids $VPCE_SG_ID \
      --private-dns-enabled \
      --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=proposal-orchestrator-secretsmanager},{Key=project,Value=proposal-orchestrator}]' \
      --region <REGION>

  # STS (Interface endpoint)
  aws ec2 create-vpc-endpoint \
      --vpc-endpoint-type Interface \
      --service-name com.amazonaws.<REGION>.sts \
      --vpc-id <VPC_ID> \
      --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
      --security-group-ids $VPCE_SG_ID \
      --private-dns-enabled \
      --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=proposal-orchestrator-sts},{Key=project,Value=proposal-orchestrator}]' \
      --region <REGION>

  # S3 (Gateway endpoint — attached to route table, not subnet)
  aws ec2 create-vpc-endpoint \
      --vpc-endpoint-type Gateway \
      --service-name com.amazonaws.<REGION>.s3 \
      --vpc-id <VPC_ID> \
      --route-table-ids <ROUTE_TABLE_ID> \
      --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=proposal-orchestrator-s3},{Key=project,Value=proposal-orchestrator}]' \
      --region <REGION>

  # (Optional) CloudWatch Logs
  aws ec2 create-vpc-endpoint \
      --vpc-endpoint-type Interface \
      --service-name com.amazonaws.<REGION>.logs \
      --vpc-id <VPC_ID> \
      --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
      --security-group-ids $VPCE_SG_ID \
      --private-dns-enabled \
      --tag-specifications 'ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=proposal-orchestrator-logs},{Key=project,Value=proposal-orchestrator}]' \
      --region <REGION>

  ---
  Step 4: Verify Route Table Has No Internet Route

  AWS Console

  1. Go to VPC > Route tables
  2. Select the route table associated with the deployment subnet
  3. Check the Routes tab
  4. Confirm there is NO 0.0.0.0/0 route pointing to an Internet Gateway (igw-*) or NAT Gateway (nat-*)
  5. The only routes should be the local VPC CIDR route and the S3 gateway endpoint prefix list route

  AWS CLI / CloudShell

  # Get route table for deployment subnet
  RT_ID=$(aws ec2 describe-route-tables \
      --filters "Name=association.subnet-id,Values=<SUBNET_ID_1>" \
      --query "RouteTables[0].RouteTableId" \
      --output text \
      --region <REGION>)

  # Show all routes
  aws ec2 describe-route-tables \
      --route-table-ids $RT_ID \
      --query "RouteTables[].Routes[]" \
      --output table \
      --region <REGION>

  Expected: Only local route for VPC CIDR and possibly an S3 prefix list route. No igw-* or nat-* destinations.

  ---
  Step 5: Verify Endpoints and Collect Evidence

  Wait approximately 2-5 minutes for endpoints to transition from pending to available.

  Run the following evidence collection commands from AWS CloudShell or any machine with AWS CLI configured:

  # ============================================================
  # EVIDENCE COLLECTION — Control Group 1: PrivateLink
  # Run from CloudShell or admin workstation
  # Save outputs to: docs/infrastructure_security/evidence/01_privatelink/
  # ============================================================

  # EV-PL-001: All VPC endpoints (full configuration)
  aws ec2 describe-vpc-endpoints \
      --filters "Name=vpc-id,Values=<VPC_ID>" \
      --output json \
      --region <REGION> > EV-PL-001-vpc-endpoints.json

  # EV-PL-002: Bedrock runtime endpoint details
  aws ec2 describe-vpc-endpoints \
      --filters "Name=service-name,Values=com.amazonaws.<REGION>.bedrock-runtime" \
      --query
  "VpcEndpoints[].{ID:VpcEndpointId,State:State,Service:ServiceName,PrivateDns:PrivateDnsEnabled,VpcId:VpcId,PolicyDocument:PolicyDocument,SubnetIds:SubnetIds,Groups:Groups}" \
      --output json \
      --region <REGION> > EV-PL-002-bedrock-runtime-endpoint.json

  # EV-PL-003: VPC endpoint security group rules
  VPCE_SG_ID=$(aws ec2 describe-vpc-endpoints \
      --filters "Name=service-name,Values=com.amazonaws.<REGION>.bedrock-runtime" \
      --query "VpcEndpoints[0].Groups[0].GroupId" \
      --output text \
      --region <REGION>)

  aws ec2 describe-security-groups \
      --group-ids $VPCE_SG_ID \
      --output json \
      --region <REGION> > EV-PL-003-security-groups.json

  # EV-PL-004: Route table for deployment subnet
  aws ec2 describe-route-tables \
      --filters "Name=association.subnet-id,Values=<SUBNET_ID_1>" \
      --output json \
      --region <REGION> > EV-PL-004-route-tables.json

  # EV-PL-005: Private DNS resolution test (run FROM DEPLOYMENT HOST only)
  # Save output of this command run from within the VPC:
  #   nslookup bedrock-runtime.<REGION>.amazonaws.com > EV-PL-005-private-dns-resolution.txt
  #   -- OR --
  #   dig bedrock-runtime.<REGION>.amazonaws.com +short >> EV-PL-005-private-dns-resolution.txt

  # EV-PL-006: Functional Bedrock call (run FROM DEPLOYMENT HOST only)
  # Save output of this Python command run from within the VPC:
  #   python3 -c "
  #   import boto3, json
  #   client = boto3.client('bedrock-runtime', region_name='<REGION>')
  #   response = client.converse(
  #       modelId='us.anthropic.claude-sonnet-4-6',
  #       messages=[{'role': 'user', 'content': [{'text': 'Say OK'}]}],
  #       inferenceConfig={'maxTokens': 10}
  #   )
  #   print('Status:', response['ResponseMetadata']['HTTPStatusCode'])
  #   print('Output:', response['output']['message']['content'][0]['text'])
  #   " > EV-PL-006-functional-test.txt 2>&1

  # EV-PL-007: VPC endpoint policy document
  aws ec2 describe-vpc-endpoints \
      --filters "Name=service-name,Values=com.amazonaws.<REGION>.bedrock-runtime" \
      --query "VpcEndpoints[].PolicyDocument" \
      --output json \
      --region <REGION> > EV-PL-007-endpoint-policy.json

  # EV-PL-008: VPC DNS settings (hostnames + resolution must be enabled)
  aws ec2 describe-vpc-attribute \
      --vpc-id <VPC_ID> \
      --attribute enableDnsHostnames \
      --output json \
      --region <REGION> > EV-PL-008-vpc-dns-settings.json

  aws ec2 describe-vpc-attribute \
      --vpc-id <VPC_ID> \
      --attribute enableDnsSupport \
      --output json \
      --region <REGION> >> EV-PL-008-vpc-dns-settings.json

  ---
  Evidence Artifact Summary

  Save all files under docs/infrastructure_security/evidence/01_privatelink/:

  ┌─────────────────────────────────────────┬──────────────┬───────────────────────┬────────────────────────────────────────────────────────────────┐
  │              Evidence File              │    Source    │    Collected From     │                             Notes                              │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-001-vpc-endpoints.json            │ AWS CLI      │ CloudShell / admin    │ All VPC endpoints in the VPC                                   │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-002-bedrock-runtime-endpoint.json │ AWS CLI      │ CloudShell / admin    │ Bedrock runtime endpoint — state, Private DNS, policy, subnets │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-003-security-groups.json          │ AWS CLI      │ CloudShell / admin    │ Endpoint SG — must show TCP 443 from host SG only              │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-004-route-tables.json             │ AWS CLI      │ CloudShell / admin    │ Deployment subnet route table — must have no IGW/NAT route     │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-005-private-dns-resolution.txt    │ nslookup/dig │ Deployment host       │ Must show private IPs (10.x/172.x), NOT public IPs             │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-006-functional-test.txt           │ Python boto3 │ Deployment host       │ Must show HTTP 200 + model response                            │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-007-endpoint-policy.json          │ AWS CLI      │ CloudShell / admin    │ Endpoint policy document                                       │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-008-vpc-dns-settings.json         │ AWS CLI      │ CloudShell / admin    │ VPC DNS hostnames + resolution both enabled                    │
  ├─────────────────────────────────────────┼──────────────┼───────────────────────┼────────────────────────────────────────────────────────────────┤
  │ EV-PL-009-console-screenshot.png        │ Console      │ Screenshot (optional) │ Supporting — VPC endpoint console page showing status          │
  └─────────────────────────────────────────┴──────────────┴───────────────────────┴────────────────────────────────────────────────────────────────┘

  ---
  PASS / FAIL Criteria

  ┌──────┬─────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────────┐
  │  #   │        Criterion        │                                          PASS Condition                                          │               FAIL Condition                │
  ├──────┼─────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ PL-1 │ Endpoint exists         │ VPC interface endpoint for com.amazonaws.<region>.bedrock-runtime is in available state          │ No endpoint, or state is                    │
  │      │                         │ (EV-PL-002)                                                                                      │ pending/failed/deleting                     │
  ├──────┼─────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ PL-2 │ Private DNS enabled     │ PrivateDnsEnabled: true in EV-PL-002                                                             │ PrivateDnsEnabled: false or missing         │
  ├──────┼─────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ PL-3 │ DNS resolves to private │ nslookup/dig from deployment host returns IPs in 10.x.x.x or 172.x.x.x range (EV-PL-005)         │ Returns public IPs, or resolution fails     │
  │      │  IPs                    │                                                                                                  │                                             │
  ├──────┼─────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ PL-4 │ Security group          │ EV-PL-003 shows ONLY TCP 443 inbound from deployment host SG. No 0.0.0.0/0 inbound rules. No     │ Open inbound rules, missing SG, or wildcard │
  │      │                         │ broad outbound rules.                                                                            │  source                                     │
  ├──────┼─────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ PL-5 │ No internet route       │ EV-PL-004 shows no 0.0.0.0/0 route to igw-* or nat-*                                             │ Route to IGW or NAT exists                  │
  ├──────┼─────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ PL-6 │ Functional test         │ converse() call returns HTTP 200 and model response from deployment host (EV-PL-006)             │ Call fails or times out                     │
  ├──────┼─────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ PL-7 │ Supporting endpoints    │ EV-PL-001 shows endpoints for secretsmanager, sts, and s3 in available state                     │ Missing supporting endpoints                │
  ├──────┼─────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────┤
  │ PL-8 │ VPC DNS settings        │ Both enableDnsHostnames and enableDnsSupport are true (EV-PL-008)                                │ Either is false                             │
  └──────┴─────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────────┘

  All 8 criteria must pass for Control Group 1 to be marked VERIFIED_PASS.

  Criteria PL-3 and PL-6 require evidence collected from the deployment host (within the VPC), not from CloudShell or an external workstation. CloudShell runs outside your VPC and will
  resolve public DNS.

  ---
  Next Steps

  1. Implement the steps above (Steps 1-4)
  2. Collect evidence by running the commands in Step 5
  3. Save all evidence files under docs/infrastructure_security/evidence/01_privatelink/
  4. Confirm when evidence is saved, or paste the outputs directly

  I will then:
  - Review each evidence artifact against the PASS/FAIL criteria
  - Update the control register with the verification result
  - Update the worklog
  - Proceed to Control Group 2 (IAM) only after PrivateLink is verified

  I am now waiting for you to implement and provide the evidence.