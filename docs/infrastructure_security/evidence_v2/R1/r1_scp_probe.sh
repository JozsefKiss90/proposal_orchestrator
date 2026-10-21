#!/usr/bin/env bash
# R1 — probe whether the AWS-managed service control policies allow the actions the
# redeployment needs, WITHOUT creating anything. Run in CloudShell:
#   bash r1_scp_probe.sh <output.json> <region>
# EC2 probes use --dry-run against REAL ids (the default VPC, its first subnet, the
# current AL2023 AMI); only DryRunOperation counts as allowed. If the real ids cannot
# be read, the EC2 probes are reported as inconclusive_no_ids, never as allowed.
# Read-only probes (__READ__) count as allowed when they exit 0, even with empty output.
# Every other probe is a request that is invalid on purpose (malformed policy,
# non-existent resource). An SCP denial names a service control policy; a validation
# or not-found error is reported as validation_error, which some services return
# before authorization, so it does not prove the action is allowed.
set -uo pipefail
out="${1:?usage: bash r1_scp_probe.sh <output.json> <region>}"
R="${2:?usage: bash r1_scp_probe.sh <output.json> <region>}"
A=$(aws sts get-caller-identity --query Account --output text)
NOPE="po-probe-does-not-exist-$A"
FAKE_KEY="arn:aws:kms:$R:$A:key/00000000-0000-0000-0000-000000000000"

default_vpc=$(aws ec2 describe-vpcs --region $R --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text 2>/dev/null)
ids_ok=1
{ [ "$default_vpc" = "None" ] || [ -z "$default_vpc" ] || ! [[ "$default_vpc" == vpc-* ]]; } && { default_vpc="vpc-00000000000000000"; ids_ok=0; }
default_subnet=$(aws ec2 describe-subnets --region $R --filters Name=vpc-id,Values="$default_vpc" --query 'Subnets[0].SubnetId' --output text 2>/dev/null)
{ [ "$default_subnet" = "None" ] || [ -z "$default_subnet" ] || ! [[ "$default_subnet" == subnet-* ]]; } && { default_subnet="subnet-00000000000000000"; ids_ok=0; }
ami=$(aws ssm get-parameter --region $R --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query Parameter.Value --output text 2>/dev/null)
[[ "$ami" == ami-* ]] || { ami=ami-00000000000000000; ids_ok=0; }

tmp=$(mktemp)
# probe <name> <action> <expected-when-allowed regex> -- <aws args...>
probe() {
  local name="$1" action="$2" expect="$3"; shift 4
  local is_ec2=0; [[ "$action" == ec2:* ]] && is_ec2=1
  local res rc outcome
  res=$(aws "$@" 2>&1); rc=$?
  if printf '%s' "$res" | grep -qi 'service control policy'; then outcome=scp_denied
  elif [ $is_ec2 -eq 1 ] && printf '%s' "$res" | grep -q "DryRunOperation"; then outcome=allowed
  elif [ $is_ec2 -eq 1 ] && [ $ids_ok -eq 0 ]; then outcome=inconclusive_no_ids
  elif [ "$expect" = "__READ__" ] && [ $rc -eq 0 ]; then outcome=allowed
  elif [ $is_ec2 -eq 0 ] && [ $rc -eq 0 ] && printf '%s' "$res" | grep -qiE "$expect"; then outcome=allowed
  elif [ $is_ec2 -eq 0 ] && printf '%s' "$res" | grep -qiE "$expect"; then outcome=validation_error
  elif [ $rc -eq 0 ]; then outcome=UNEXPECTED_SUCCESS
  elif printf '%s' "$res" | grep -qiE 'AccessDenied|UnauthorizedOperation|not authorized'; then outcome=denied_other
  else outcome=inconclusive; fi
  jq -n --arg name "$name" --arg action "$action" --arg outcome "$outcome" --argjson rc "$rc" \
        --arg message "$(printf '%s' "$res" | grep -v '^Encoded authorization' | sed 's/Encoded authorization failure message:.*//' | head -c 400)" \
        '{probe: $name, action: $action, outcome: $outcome, exit_code: $rc, message: $message}' >> "$tmp"
  printf '%-34s %s\n' "$name" "$outcome" >&2
}
DRY='DryRunOperation'

probe vpc            ec2:CreateVpc              "$DRY" -- ec2 create-vpc --region $R --cidr-block 10.99.0.0/16 --dry-run
probe subnet         ec2:CreateSubnet           "$DRY" -- ec2 create-subnet --region $R --vpc-id "$default_vpc" --cidr-block 172.31.250.0/28 --dry-run
probe security_group ec2:CreateSecurityGroup    "$DRY" -- ec2 create-security-group --region $R --group-name po-probe --description po-probe --vpc-id "$default_vpc" --dry-run
probe route_table    ec2:CreateRouteTable       "$DRY" -- ec2 create-route-table --region $R --vpc-id "$default_vpc" --dry-run
probe interface_endpoint ec2:CreateVpcEndpoint  "$DRY" -- ec2 create-vpc-endpoint --region $R --vpc-id "$default_vpc" --vpc-endpoint-type Interface --service-name com.amazonaws.$R.bedrock-runtime --subnet-ids "$default_subnet" --dry-run
probe gateway_endpoint ec2:CreateVpcEndpoint    "$DRY" -- ec2 create-vpc-endpoint --region $R --vpc-id "$default_vpc" --vpc-endpoint-type Gateway --service-name com.amazonaws.$R.s3 --dry-run
probe flow_logs      ec2:CreateFlowLogs         "$DRY" -- ec2 create-flow-logs --region $R --resource-type VPC --resource-ids "$default_vpc" --traffic-type ALL --log-group-name /proposal-orchestrator/probe --deliver-logs-permission-arn arn:aws:iam::$A:role/$NOPE --dry-run
probe run_t3_medium  ec2:RunInstances           "$DRY" -- ec2 run-instances --region $R --image-id "$ami" --instance-type t3.medium --subnet-id "$default_subnet" --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1 --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeType=gp3,VolumeSize=30,Encrypted=true,DeleteOnTermination=true}' --dry-run
probe iam_create_role   iam:CreateRole          'MalformedPolicyDocument|ValidationError' -- iam create-role --role-name po-probe --assume-role-policy-document '{}'
probe iam_create_policy iam:CreatePolicy        'MalformedPolicyDocument|ValidationError' -- iam create-policy --policy-name po-probe --policy-document '{}'
probe iam_boundary   iam:PutRolePermissionsBoundary 'NoSuchEntity' -- iam put-role-permissions-boundary --role-name "$NOPE" --permissions-boundary arn:aws:iam::aws:policy/ReadOnlyAccess
probe iam_instance_profile iam:AddRoleToInstanceProfile 'NoSuchEntity' -- iam add-role-to-instance-profile --instance-profile-name "$NOPE" --role-name "$NOPE"
probe kms_create_key kms:CreateKey              'MalformedPolicyDocument' -- kms create-key --region $R --policy '{}'
probe cloudtrail_trail cloudtrail:CreateTrail   'S3BucketDoesNotExist|InsufficientS3BucketPolicy' -- cloudtrail create-trail --region $R --name po-probe --s3-bucket-name "$NOPE"
probe s3_bucket_policy s3:PutBucketPolicy       'NoSuchBucket' -- s3api put-bucket-policy --bucket "$NOPE" --policy '{}'
probe secret_policy  secretsmanager:PutResourcePolicy 'ResourceNotFound|MalformedPolicyDocument' -- secretsmanager put-resource-policy --region $R --secret-id "$NOPE" --resource-policy '{}'
probe logs_group_kms logs:CreateLogGroup        'InvalidParameter|AccessDeniedException.*kms|not authorized to use|KMS' -- logs create-log-group --region $R --log-group-name /proposal-orchestrator/probe --kms-key-id "$FAKE_KEY"
probe cfn_create_stack cloudformation:CreateStack 'ValidationError' -- cloudformation create-stack --region $R --stack-name po-probe --template-body 'not-a-template'
probe ssm_send_command ssm:SendCommand          'InvalidInstanceId' -- ssm send-command --region $R --instance-ids i-00000000000000000 --document-name AWS-RunShellScript --parameters commands=true
probe bedrock_list   bedrock:ListFoundationModels '__READ__' -- bedrock list-foundation-models --region $R --by-provider anthropic --query '{modelSummaries: length(modelSummaries)}' --output json
probe bedrock_logging_read bedrock:GetModelInvocationLoggingConfiguration '__READ__' -- bedrock get-model-invocation-logging-configuration --region $R --output json

jq -s --arg account "$A" --arg region "$R" --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg vpc "$default_vpc" --arg subnet "$default_subnet" --arg ami "$ami" --argjson ids_ok "$ids_ok" \
  '{account: $account, region: $region, collected_utc: $at, real_ids_used: ($ids_ok == 1), default_vpc: $vpc, default_subnet: $subnet, ami: $ami,
    summary: (group_by(.outcome) | map({key: .[0].outcome, value: map(.probe)}) | from_entries),
    probes: .}' "$tmp" > "$out"
rm -f "$tmp"
jq .summary "$out"
