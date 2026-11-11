# R11 — Endpoints and host: first PrivateLink call: step sheet

| Field | Value |
|---|---|
| Ticket | `R11` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R11 (with §4 F1, F2, F7; §7; §7a; §8) |
| Decisions applied | OD1-r1 eu-north-1; OD2 (a) one hardened runtime role; OD4 one zone; OD5 the host stack is created and deleted per working session; OD6-r3 (stacks, change sets, guards, imports, outputs contract); OD7-resources (model lists in `deploy/aws/parameters/host.json`), OD7-orchestrator (the Converse model); OD9 AL2023 x86_64, t3.medium; R1-D2 session-start check; R1-D3 (EBS encryption and IMDSv2 account defaults; set on the host as well); R4-D3 and R5 known gap (whether Run Command needs the SSM Agent's S3 buckets); R5-D9 (DC-09 closes with DC-14); R6-D3 (runtime decrypt only through Secrets Manager and S3); R7-D18 (flow-log records first shown here); R8-D3 (R11 does not need the launcher); R12a (fixed test string `converse_test_string` in `deploy/aws/collector_inputs.json`); OD10 Free plan, no upgrade |
| Written by / on | agent (Claude) / 2026-11-11 |
| Account / region | `797661577394` / `eu-north-1`. Every `ec2`, `ssm`, `cloudformation`, `cloudtrail`, `logs`, `iam`, `bedrock` and `sts` command names `--region eu-north-1` (IAM answers regardless) |
| IDs taken from | `evidence_v2/R4/R4_outputs.json` (VPC, subnet, zone, host and endpoint security groups), `R5/R5_outputs.json` (runtime role, instance profile, boundary, explicit deny), `R7/R7_outputs.json` (flow-log group and id), `R8/R8_outputs.json` (secret), each read by path inside the command blocks; checked against the live export list in step 03. The model id from `deploy/aws/parameters/secret.json` (`TransportModelId`), the test string from `deploy/aws/collector_inputs.json`. From step 07 on: `R11_outputs.json`; from step 17 on: `R11_17_outputs-recreated.json` |
| Controls touched | DC-01, DC-02, DC-04, DC-05 (interface half), DC-14, DC-26, DC-37 (the ticket's list); also DC-03 and DC-07 (attachment halves), DC-09 (closes with DC-14, R5-D9), DC-08 note (flow-log records, R7-D18), DC-19/DC-20/DC-21 notes (runtime read of the secret through Secrets Manager and the key), DC-28 (invocation logging still unset) |
| Hourly cost created | **Yes, from step 06 (and again from step 17).** Six interface endpoints in one zone (per endpoint-hour, plus per GB processed); one EC2 instance (`t3.medium`, per instance-hour; CPU credits `standard`, so no surplus-credit charge); one gp3 root volume (per GB-month, prorated while it exists). Usage on top: Bedrock tokens of one Converse call (max 10 output tokens), CloudWatch Logs ingestion of the flow-log records, KMS and Secrets Manager requests. No public IPv4 address is created. **No figure is quoted here: R14 prices each item from the AWS pricing pages for eu-north-1.** The operator's explicit go for each creation (step 05 → 06, step 16 → 17) is recorded in `RUNLOG.md`. The stack is deleted at the end of the session (OD5, steps 13 and 19) |

## Points the agent decided where no decision record settles them (the operator confirms or changes each before step 05)

1. **The Converse call uses the AWS CLI on the host, not the R9 launcher.** The launcher (`runner.host_env`)
   runs under the bundle's interpreter, and no bundle is on the host before R15; R8-D3 records that R11
   does not need the launcher. The call runs under the runtime role's instance-profile credentials, which
   is the identity the launcher's child process would use. The launcher's one AWS call (`GetSecretValue`
   on the runtime secret) is exercised in step 11 by the same role, through the `secretsmanager` endpoint,
   printing only the version stage. The call is the R12a collector's `dc37_converse.sh` pattern.
2. **Converse model:** `TransportModelId` of `deploy/aws/parameters/secret.json`
   (`eu.anthropic.claude-opus-4-6-v1`, OD7-orchestrator, 5 requests per minute; one call). Sonnet 4.6 is
   not called.
3. **Bedrock endpoint policy form:** `Principal: "*"` with `ArnEquals aws:PrincipalArn` = the imported
   `RuntimeRoleArn`, as the R8 secret policy names the role, rather than the role ARN as principal. Two
   Allow statements: invoke actions on the OD7 inference profiles, and on the routed foundation models
   (the same two parameter lists R5's invoke policy names, F2).
4. **The five supporting endpoints keep the AWS default endpoint policy.** The ticket asks for a policy on
   the Bedrock endpoint only. A restriction such as `aws:PrincipalAccount` = this account on `sts`,
   `secretsmanager`, `ssm`, `ssmmessages` and `ec2messages` (an F7-style guard against foreign
   credentials) is possible but untested against the SSM Agent; it is not added here.
5. **Root volume key:** `Encrypted: true` without `KmsKeyId`: EC2 uses the account's default EBS key
   (`R1_12`, R1-D3; step 03 records which key). The kms stack's key is not exported to R11
   (`outputs_contract.json`), and its policy (R6-D3) is scoped to Secrets Manager and S3. The volume
   size is the image's (no `VolumeSize`), so a larger AL2023 snapshot cannot fail the creation.
6. **CPU credits `standard`** on the t3 host (no surplus-credit charges), detailed monitoring off,
   shutdown from inside the host stops it.
7. **`VpcId` is imported although `outputs_contract.json` does not list R11 among its consumers.** An
   interface endpoint requires it. `tests/test_aws_host_template.py` names this one exception; adding
   R11 to the consumers of `proposal-orchestrator-network-VpcId` is left to the operator (one line in the
   contract, outside this commit).
8. **Outputs of the second creation** are saved as `R11_17_outputs-recreated.json`, not over
   `R11_outputs.json`; both stacks are deleted at the end of the session, so R12a reads a later session's
   outputs file with `--host-outputs`.
9. **The re-check after recreation** (step 18) repeats the structural checks and one Run Command, not the
   Converse call.
10. **Credit floor** for the session-start check: 195.00 USD (R8 left 199.98; the key and the secret
    accrue monthly fees).

## Before you start

- **Sign in with `aws login --profile po-r1`**, never bare `aws login`.
- **Where commands run.** PowerShell in the VS Code terminal, repository root. Every AWS command names
  `--profile po-r1`. Each step also gives the CloudShell form (no `--profile`); see "CloudShell setup".
- **`$E` and `$V2` must be set in every new PowerShell window.** Every block below starts with them.
- Always pipe to `Out-File -Encoding utf8 <file>`, never `>`.
- If `.venv-lint` is active, run `deactivate` before any `py -3.10` command.
- The AWS CLI v2 exits **254** when the service answers with an error, and PowerShell wraps long error
  text inside the file. Criteria below are written on substrings, not on one-line quotes.
- **Never save** secret values, access keys, session tokens, passwords, the IMDS token, instance
  credentials, prompt or proposal text, or model output other than the fixed test string `DEPLOY_OK`.
  No step below prints any of them: the host scripts compare the reply on the host and print it only
  when it equals the test string, the secret read prints only the version stage, and the CloudTrail step
  writes selected metadata fields only. Never query `iam/security-credentials` on the host.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or `0.0.0.0/0` egress rule, not even temporarily.
  Bedrock model invocation logging stays disabled.
- If a step fails, stop, report the error in session, and do not improvise a fix. **If the host stack
  exists when you stop, delete it (step 13's commands) unless the agent asks you to keep it for
  diagnosis; it costs by the hour.**
- **Rounds.**
  - **Round 1: steps 01–05** (read-only lookups, lint, guards, tests, change set). Nothing billable.
    Hand back; both read the change set; **STOP until you give the explicit go in session.**
  - **Round 2: steps 06–15** (execute, evidence, Run Command, Converse, delete, base intact, recreation
    change set). **STOP again before step 17 for the second go.** Run it in one sitting: the stack costs
    from step 06 to step 13.
  - **Round 3: steps 17–22** (recreate, re-check, delete, CloudTrail, flow logs, credits). Step 20 runs
    no earlier than 15 minutes after step 12.
  - **Round 4: step 23** after the agent has written `VERIFICATION.md`, the register v2 rows and the
    worklog entry.

### CloudShell setup (only if you use CloudShell)

Upload into CloudShell (Actions → Upload file), keeping these relative paths under `~/po`:
`evidence_v2/R4/R4_outputs.json`, `evidence_v2/R5/R5_outputs.json`, `evidence_v2/R7/R7_outputs.json`,
`evidence_v2/R8/R8_outputs.json`, `deploy/aws/templates/90-host.yaml`, `deploy/aws/parameters/host.json`,
`deploy/aws/parameters/secret.json`, `deploy/aws/collector_inputs.json`. Then, once per CloudShell session:

```bash
mkdir -p ~/po/R11 && cd ~/po/R11
V2=~/po/evidence_v2; D=~/po/deploy/aws
out() { sed '1s/^\xEF\xBB\xBF//' "$1" | jq -r --arg k "$2" '.[] | select(.OutputKey==$k) | .OutputValue'; }
```

Lint, guards and pytest (steps 04 and 23) run on the workstation only. Download every `R11_*` file into
`docs\infrastructure_security\evidence_v2\R11\` before handing back.

---

## Steps

### Step 01 — Session-start check: credits, budget, alert states (R1-D2)

What it does: confirms that the Free plan is active, the credits are intact and no budget alert is in
`ALARM`, before anything else runs.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_01_budget-notifications.json"
Get-Content "$E\R11_01_plan-state.json", "$E\R11_01_budgets.json", "$E\R11_01_budget-notifications.json"
```

CloudShell:

```bash
cd ~/po/R11
aws freetier get-account-plan-state --output json > R11_01_plan-state.json 2>&1
aws budgets describe-budgets --account-id 797661577394 --query 'Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}' --output json > R11_01_budgets.json 2>&1
aws budgets describe-notifications-for-budget --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query 'Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}' --output json > R11_01_budget-notifications.json 2>&1
cat R11_01_plan-state.json R11_01_budgets.json R11_01_budget-notifications.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_01_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `195.00` (R8 left 199.98, `R8_10_plan-state-after.json`); `accountPlanExpirationDate` starts `2027-04-19` |
| `R11_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` = `10.0`, `spend` < `8.5` |
| `R11_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` = `OK` |

**STOP rule.** If the plan is not `ACTIVE`, the credits are below 195.00 USD, or any notification is in
`ALARM`, stop here and report it.

### Step 02 — Who is calling

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_02_caller-identity.json"
Get-Content "$E\R11_02_caller-identity.json"
```

CloudShell:

```bash
cd ~/po/R11
aws sts get-caller-identity --output json > R11_02_caller-identity.json 2>&1; cat R11_02_caller-identity.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_02_caller-identity.json` | `Account` = `797661577394`; `Arn` starts with `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Any other account: stop. Nothing below may run.

### Step 03 — Read-only lookups (nothing is created)

What it does: collects the facts the stack depends on, before anything with an hourly cost exists:

- **03a** the `proposal-orchestrator-host` stack does not exist;
- **03b** the project VPC holds no interface endpoint (only the R4 S3 gateway endpoint) and no network
  interface;
- **03c** no EC2 instance in eu-north-1 that is not terminated;
- **03d** the five base stacks and their status (step 14 compares with this);
- **03e** the 25 project exports (step 14 compares with this; the agent compares the values with the
  R4, R5, R6, R7, R8 outputs files);
- **03f** the AL2023 image the template will resolve: x86_64, owned by Amazon, root device `/dev/xvda`
  (the template's `DeviceName`);
- **03g** a **dry run** of the host launch with the template's settings (no instance is created; the
  answer `DryRunOperation` means the request would have succeeded). This is where a Free plan refusal of
  `t3.medium` (OD9 known gap) shows;
- **03h** Bedrock invocation logging is unset (DC-28) and the account's EBS defaults (point 5).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$VPC = O "$V2\R4\R4_outputs.json" VpcId
$SUB = O "$V2\R4\R4_outputs.json" PrivateSubnetId
$HSG = O "$V2\R4\R4_outputs.json" HostSecurityGroupId
$IPN = O "$V2\R5\R5_outputs.json" InstanceProfileName
"VPC=$VPC SUB=$SUB HSG=$HSG IPN=$IPN"
# 03a
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_03_host-stack-before.txt"
# 03b
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_vpc-endpoints-before.json"
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,desc:Description}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_network-interfaces-before.json"
# 03c
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query "Reservations[].Instances[].{id:InstanceId,state:State.Name,type:InstanceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_instances-before.json"
# 03d, 03e
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_base-stacks.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-')].{name:Name,value:Value}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_exports.json"
# 03f
$AMI = aws ssm get-parameters --profile po-r1 --region eu-north-1 --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query "Parameters[0].Value" --output text
"AMI=$AMI"
aws ec2 describe-images --profile po-r1 --region eu-north-1 --image-ids $AMI --query "Images[].{id:ImageId,name:Name,arch:Architecture,owner:ImageOwnerAlias,root:RootDeviceName,rootType:RootDeviceType,size:BlockDeviceMappings[0].Ebs.VolumeSize}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_image.json"
# 03g — dry run: nothing is created (an error line with DryRunOperation is the expected result)
& { aws ec2 run-instances --dry-run --profile po-r1 --region eu-north-1 --image-id $AMI --instance-type t3.medium --iam-instance-profile Name=$IPN --network-interfaces "DeviceIndex=0,SubnetId=$SUB,Groups=$HSG,AssociatePublicIpAddress=false,DeleteOnTermination=true" --metadata-options "HttpEndpoint=enabled,HttpTokens=required,HttpPutResponseHopLimit=1" --block-device-mappings "DeviceName=/dev/xvda,Ebs={VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}" --credit-specification CpuCredits=standard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_03_run-instances-dry-run.txt"
# 03h
& { aws bedrock get-model-invocation-logging-configuration --profile po-r1 --region eu-north-1 --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_03_invocation-logging-before.txt"
aws ec2 get-ebs-encryption-by-default --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_ebs-encryption-default.json"
aws ec2 get-ebs-default-kms-key-id --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_ebs-default-key.json"
aws ec2 get-instance-metadata-defaults --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_03_imds-defaults.json"
Get-ChildItem "$E\R11_03_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

CloudShell:

```bash
cd ~/po/R11
VPC=$(out $V2/R4/R4_outputs.json VpcId); SUB=$(out $V2/R4/R4_outputs.json PrivateSubnetId)
HSG=$(out $V2/R4/R4_outputs.json HostSecurityGroupId); IPN=$(out $V2/R5/R5_outputs.json InstanceProfileName)
echo "VPC=$VPC SUB=$SUB HSG=$HSG IPN=$IPN"
{ aws cloudformation describe-stacks --region eu-north-1 --stack-name proposal-orchestrator-host --output json; echo "exit=$?"; } > R11_03_host-stack-before.txt 2>&1
aws ec2 describe-vpc-endpoints --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query 'VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}' --output json > R11_03_vpc-endpoints-before.json 2>&1
aws ec2 describe-network-interfaces --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query 'NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,desc:Description}' --output json > R11_03_network-interfaces-before.json 2>&1
aws ec2 describe-instances --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query 'Reservations[].Instances[].{id:InstanceId,state:State.Name,type:InstanceType}' --output json > R11_03_instances-before.json 2>&1
aws cloudformation describe-stacks --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json > R11_03_base-stacks.json 2>&1
aws cloudformation list-exports --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-')].{name:Name,value:Value}" --output json > R11_03_exports.json 2>&1
AMI=$(aws ssm get-parameters --region eu-north-1 --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query 'Parameters[0].Value' --output text); echo "AMI=$AMI"
aws ec2 describe-images --region eu-north-1 --image-ids $AMI --query 'Images[].{id:ImageId,name:Name,arch:Architecture,owner:ImageOwnerAlias,root:RootDeviceName,rootType:RootDeviceType,size:BlockDeviceMappings[0].Ebs.VolumeSize}' --output json > R11_03_image.json 2>&1
{ aws ec2 run-instances --dry-run --region eu-north-1 --image-id $AMI --instance-type t3.medium --iam-instance-profile Name=$IPN --network-interfaces "DeviceIndex=0,SubnetId=$SUB,Groups=$HSG,AssociatePublicIpAddress=false,DeleteOnTermination=true" --metadata-options "HttpEndpoint=enabled,HttpTokens=required,HttpPutResponseHopLimit=1" --block-device-mappings "DeviceName=/dev/xvda,Ebs={VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}" --credit-specification CpuCredits=standard; echo "exit=$?"; } > R11_03_run-instances-dry-run.txt 2>&1
{ aws bedrock get-model-invocation-logging-configuration --region eu-north-1 --output json; echo "exit=$?"; } > R11_03_invocation-logging-before.txt 2>&1
aws ec2 get-ebs-encryption-by-default --region eu-north-1 --output json > R11_03_ebs-encryption-default.json 2>&1
aws ec2 get-ebs-default-kms-key-id --region eu-north-1 --output json > R11_03_ebs-default-key.json 2>&1
aws ec2 get-instance-metadata-defaults --region eu-north-1 --output json > R11_03_imds-defaults.json 2>&1
for f in R11_03_*; do echo "== $f"; cat "$f"; done
```

| Evidence file | PASS criterion |
|---|---|
| `R11_03_host-stack-before.txt` | Contains `ValidationError` and `does not exist`; last line `exit=254` |
| `R11_03_vpc-endpoints-before.json` | Exactly one entry: `id` = `S3GatewayEndpointId` of `R4_outputs.json`, `type` `Gateway`, `state` `available` |
| `R11_03_network-interfaces-before.json` | `[]` |
| `R11_03_instances-before.json` | `[]` |
| `R11_03_base-stacks.json` | Exactly the five base stacks (`-network`, `-iam`, `-kms`, `-audit`, `-secret`), each `status` ending `_COMPLETE` and none containing `ROLLBACK`; no `proposal-orchestrator-host` |
| `R11_03_exports.json` | Exactly 25 names (7 network, 7 iam, 3 kms, 6 audit, 2 secret); every value equals the same key in `R4_outputs.json` … `R8_outputs.json` (agent compares by script). Among them the six the host stack imports: `network-VpcId`, `-PrivateSubnetId`, `-EndpointSecurityGroupId`, `-HostSecurityGroupId`, `iam-RuntimeRoleArn`, `-InstanceProfileName` |
| `R11_03_image.json` | One image: `arch` `x86_64`, `owner` `amazon`, `name` starts `al2023-ami-`, `root` `/dev/xvda`, `rootType` `ebs` |
| `R11_03_run-instances-dry-run.txt` | Contains `DryRunOperation` (`Request would have succeeded`); last line `exit=254` |
| `R11_03_invocation-logging-before.txt` | Last line `exit=0`; no `loggingConfig` key (DC-28) |
| `R11_03_ebs-encryption-default.json` | `EbsEncryptionByDefault` true (R1-D3) |
| `R11_03_ebs-default-key.json` | A `KmsKeyId` is reported (expected `alias/aws/ebs`); recorded for point 5 |
| `R11_03_imds-defaults.json` | `HttpTokens` `required`, `HttpPutResponseHopLimit` 1 (R1-D3) |

**STOP rule.** If the host stack exists, any interface endpoint, network interface or instance exists,
an export is missing or differs, the image is not x86_64 / `/dev/xvda`, invocation logging is configured,
or the dry run answers anything other than `DryRunOperation` (for example `UnauthorizedOperation` or an
explicit deny naming the instance type): stop and report. A refusal of `t3.medium` is the OD9 known gap;
the operator chooses between `t3.micro` (`InstanceType` override, smoke only) and the OD10 upgrade.

### Step 04 — Lint, guards and tests on the filled template (workstation only, no AWS call)

What it does: proves, before anything is created, that `90-host.yaml` lints for eu-north-1, keeps the
template rules, carries no old-account id, and has the shape `tests/test_aws_host_template.py` pins.
Run `deactivate` first if `.venv-lint` is active.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_04_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_04_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_04_old-id-guard.txt"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_aws_env_config_template.py tests/test_aws_host_template.py tests/test_old_id_guard.py tests/test_host_env_launcher.py } 2>&1 | Out-File -Encoding utf8 "$E\R11_04_pytest.txt"
Get-Content "$E\R11_04_cfn-lint.txt", "$E\R11_04_template-guard.txt", "$E\R11_04_old-id-guard.txt"; Get-Content "$E\R11_04_pytest.txt" -Tail 3
```

CloudShell: not applicable (repository tests and the lint environment are on the workstation).

| Evidence file | PASS criterion |
|---|---|
| `R11_04_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R11_04_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R11_04_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R11_04_pytest.txt` | First line `Python 3.10.…`; last line `259 passed` (the agent's run under Python 3.10.6) with no `failed`, `error` or `skipped` |

**STOP rule.** Any non-zero exit or failed test: stop. The template is not deployed until this step is
clean.

### Step 05 — Create the change set and save it for review (nothing is created yet)

What it does: asks CloudFormation to plan the host stack. A change set of type CREATE builds nothing
until it is executed. **No `--capabilities`:** the stack holds no IAM resource. The six
`Fn::ImportValue` references and the AMI parameter are resolved here; a missing export fails the change
set. `describe-change-set` runs without `--include-property-values`.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-01 --change-set-type CREATE --template-body file://deploy/aws/templates/90-host.yaml --parameters file://deploy/aws/parameters/host.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_05_create-change-set.json"
Get-Content "$E\R11_05_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-01 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_05_change-set.json"
Get-Content "$E\R11_05_change-set.json"
```

CloudShell:

```bash
cd ~/po/R11
aws cloudformation create-change-set --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-01 --change-set-type CREATE --template-body file://$D/templates/90-host.yaml --parameters file://$D/parameters/host.json --tags Key=project,Value=proposal-orchestrator --output json > R11_05_create-change-set.json 2>&1; cat R11_05_create-change-set.json
aws cloudformation wait change-set-create-complete --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-01
aws cloudformation describe-change-set --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-01 --output json > R11_05_change-set.json 2>&1; cat R11_05_change-set.json
```

If `create-change-set` returns an error, or `wait` reports a terminal failure, still run the
`describe-change-set` line: `Status` and `StatusReason` are the evidence. Then stop and hand back.

| Evidence file | PASS criterion |
|---|---|
| `R11_05_create-change-set.json` | `Id` starts `arn:aws:cloudformation:eu-north-1:797661577394:changeSet/r11-create-01/`; `StackId` starts `arn:aws:cloudformation:eu-north-1:797661577394:stack/proposal-orchestrator-host/` |
| `R11_05_change-set.json` | `Status` `CREATE_COMPLETE`; `ExecutionStatus` `AVAILABLE`; `Capabilities` absent or `[]`; `Tags` = `[{project: proposal-orchestrator}]`; `Parameters`: `ExpectedAccountId` 797661577394, `ExpectedRegion` eu-north-1, `ProjectName` proposal-orchestrator, `InstanceType` t3.medium, `InferenceProfileArns` and `FoundationModelArns` equal to `host.json`, `LatestAmiId` with `ResolvedValue` = the image of `R11_03_image.json`; `Changes` holds **exactly seven** entries, each `ResourceChange.Action` = `Add`: `BedrockRuntimeEndpoint`, `StsEndpoint`, `SecretsManagerEndpoint`, `SsmEndpoint`, `SsmMessagesEndpoint`, `Ec2MessagesEndpoint` (each `AWS::EC2::VPCEndpoint`) and `Host` (`AWS::EC2::Instance`). Nothing else |

**STOP — hand back here (end of round 1).** Both of us read `R11_05_change-set.json` against the
criterion. **Step 06 runs only after you have confirmed in session that the change set lists exactly
those seven resources and given the explicit go.** Executing it starts the hourly charges listed in the
header. Record the go (UTC time and your words) in `RUNLOG.md`. If the change set itself failed, the
agent records the error verbatim and nothing is executed; a stale change set is deleted with
`aws cloudformation delete-stack --stack-name proposal-orchestrator-host` (a stack in
`REVIEW_IN_PROGRESS` holds no resource).

---

### Step 06 — Execute the change set (creates the seven resources; hourly charges start)

**Only after the operator's explicit go in session on `R11_05_change-set.json`.** Write the start time
(UTC) in `RUNLOG.md`: the stack must be deleted in step 13 of this same session (OD5).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
& { aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-01; "execute exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_06_execute-exit.txt"
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_06_stack-status.json"
aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_06_stack-events.json"
Get-Content "$E\R11_06_execute-exit.txt", "$E\R11_06_stack-status.json"
```

CloudShell:

```bash
cd ~/po/R11
{ aws cloudformation execute-change-set --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-01; echo "execute exit=$?"; } > R11_06_execute-exit.txt 2>&1
aws cloudformation wait stack-create-complete --region eu-north-1 --stack-name proposal-orchestrator-host
aws cloudformation describe-stacks --region eu-north-1 --stack-name proposal-orchestrator-host --query 'Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,capabilities:Capabilities,tags:Tags}' --output json > R11_06_stack-status.json 2>&1
aws cloudformation describe-stack-events --region eu-north-1 --stack-name proposal-orchestrator-host --query 'StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}' --output json > R11_06_stack-events.json 2>&1
cat R11_06_execute-exit.txt R11_06_stack-status.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_06_execute-exit.txt` | `execute exit=0` and no error line |
| `R11_06_stack-status.json` | `status` `CREATE_COMPLETE`; `capabilities` null or `[]`; `tags` hold `project` = `proposal-orchestrator` |
| `R11_06_stack-events.json` | The seven logical ids and the stack each reach `CREATE_COMPLETE`; `Host` reaches `CREATE_IN_PROGRESS` after all six endpoints reached `CREATE_COMPLETE` (`DependsOn`); no `*_FAILED` and no `ROLLBACK` |

**STOP rule.** On a rollback or any `*_FAILED` event: report the `reason` of the first failed event. A
stack in `ROLLBACK_COMPLETE` holds nothing billable but must be deleted before a new attempt
(`delete-stack`, as in step 13). The agent writes `STEPS_fix1.md`.

### Step 07 — Save the stack outputs (ids for every later step and for R12a)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_outputs.json"
Get-Content "$E\R11_outputs.json"
```

CloudShell:

```bash
cd ~/po/R11
aws cloudformation describe-stacks --region eu-north-1 --stack-name proposal-orchestrator-host --query 'Stacks[0].Outputs' --output json > R11_outputs.json 2>&1; cat R11_outputs.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_outputs.json` | Exactly the seven contract keys, none with an `ExportName`: six `…EndpointId` values starting `vpce-` and all different, and `InstanceId` starting `i-` |

### Step 08 — Endpoints: available, private DNS, the one subnet, the endpoint group, the Bedrock policy (DC-01, DC-02, DC-03, DC-04, DC-05)

What it does: reads the six endpoints and every network interface in the VPC. The agent compares the
Bedrock endpoint's policy with the template by script (role ARN and model lists resolved from
`R5_outputs.json` and `host.json`), statement by statement.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$VPC = O "$V2\R4\R4_outputs.json" VpcId
$EP = @("BedrockRuntimeEndpointId","StsEndpointId","SecretsManagerEndpointId","SsmEndpointId","SsmMessagesEndpointId","Ec2MessagesEndpointId") | ForEach-Object { O "$E\R11_outputs.json" $_ }
"Endpoints=$($EP -join ' ')"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --vpc-endpoint-ids $EP --query "VpcEndpoints[].{id:VpcEndpointId,service:ServiceName,type:VpcEndpointType,state:State,privateDns:PrivateDnsEnabled,vpc:VpcId,subnets:SubnetIds,groups:Groups[].GroupId,enis:NetworkInterfaceIds,dns:DnsEntries[].DnsName,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_08_vpc-endpoints.json"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --vpc-endpoint-ids $EP[0] --query "VpcEndpoints[0].PolicyDocument" --output text 2>&1 | Out-File -Encoding utf8 "$E\R11_08_bedrock-endpoint-policy.json"
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,desc:Description,subnet:SubnetId,ip:PrivateIpAddress,publicIp:Association.PublicIp,groups:Groups[].GroupId,instance:Attachment.InstanceId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_08_network-interfaces.json"
Get-Content "$E\R11_08_vpc-endpoints.json", "$E\R11_08_bedrock-endpoint-policy.json", "$E\R11_08_network-interfaces.json"
```

CloudShell:

```bash
cd ~/po/R11
VPC=$(out $V2/R4/R4_outputs.json VpcId)
EP=$(for k in BedrockRuntimeEndpointId StsEndpointId SecretsManagerEndpointId SsmEndpointId SsmMessagesEndpointId Ec2MessagesEndpointId; do out R11_outputs.json $k; done | tr '\n' ' '); echo "Endpoints=$EP"
aws ec2 describe-vpc-endpoints --region eu-north-1 --vpc-endpoint-ids $EP --query 'VpcEndpoints[].{id:VpcEndpointId,service:ServiceName,type:VpcEndpointType,state:State,privateDns:PrivateDnsEnabled,vpc:VpcId,subnets:SubnetIds,groups:Groups[].GroupId,enis:NetworkInterfaceIds,dns:DnsEntries[].DnsName,tags:Tags}' --output json > R11_08_vpc-endpoints.json 2>&1
aws ec2 describe-vpc-endpoints --region eu-north-1 --vpc-endpoint-ids $(out R11_outputs.json BedrockRuntimeEndpointId) --query 'VpcEndpoints[0].PolicyDocument' --output text > R11_08_bedrock-endpoint-policy.json 2>&1
aws ec2 describe-network-interfaces --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query 'NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,desc:Description,subnet:SubnetId,ip:PrivateIpAddress,publicIp:Association.PublicIp,groups:Groups[].GroupId,instance:Attachment.InstanceId}' --output json > R11_08_network-interfaces.json 2>&1
cat R11_08_vpc-endpoints.json R11_08_bedrock-endpoint-policy.json R11_08_network-interfaces.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_08_vpc-endpoints.json` | Six entries, one per service `com.amazonaws.eu-north-1.{bedrock-runtime, sts, secretsmanager, ssm, ssmmessages, ec2messages}`; each `type` `Interface`, `state` `available` (DC-01, DC-05), `privateDns` true (DC-02), `vpc` = `VpcId`, `subnets` = [`PrivateSubnetId`] (OD4), `groups` = [`EndpointSecurityGroupId`] (DC-03 attached), exactly one ENI, `tags` with `project` = `proposal-orchestrator` |
| `R11_08_bedrock-endpoint-policy.json` | Exactly the two statements of the template (`RuntimeRoleInvokesOd7Profiles`, `RuntimeRoleInvokesRoutedModels`): `Allow`, `Principal` `*`, actions `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`, resources = the 2 profile ARNs and the 12 foundation-model ARNs of `host.json`, condition `ArnEquals aws:PrincipalArn` = `RuntimeRoleArn` of `R5_outputs.json`; nothing else (agent's script, DC-04) |
| `R11_08_network-interfaces.json` | Seven interfaces, all in `PrivateSubnetId`, **none with a `publicIp`**: six of type `vpc_endpoint` with groups [`EndpointSecurityGroupId`], one of type `interface` attached to `InstanceId` with groups [`HostSecurityGroupId`] (DC-07 attached) |

### Step 09 — The host: no public IP, IMDSv2 with hop limit 1, the profile, the root volume (DC-14, OD9)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$I = O "$E\R11_outputs.json" InstanceId; "InstanceId=$I"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --instance-ids $I --query "Reservations[0].Instances[0].{id:InstanceId,state:State.Name,type:InstanceType,image:ImageId,arch:Architecture,az:Placement.AvailabilityZone,subnet:SubnetId,vpc:VpcId,privateIp:PrivateIpAddress,publicIp:PublicIpAddress,publicDns:PublicDnsName,groups:SecurityGroups[].GroupId,profile:IamInstanceProfile.Arn,keyName:KeyName,metadata:MetadataOptions,rootDevice:RootDeviceName,blockDevices:BlockDeviceMappings,tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_09_instance.json"
$VOL = aws ec2 describe-instances --profile po-r1 --region eu-north-1 --instance-ids $I --query "Reservations[0].Instances[0].BlockDeviceMappings[?DeviceName=='/dev/xvda'].Ebs.VolumeId | [0]" --output text
"RootVolume=$VOL"
aws ec2 describe-volumes --profile po-r1 --region eu-north-1 --volume-ids $VOL --query "Volumes[].{id:VolumeId,type:VolumeType,encrypted:Encrypted,kms:KmsKeyId,size:Size,attach:Attachments[].{instance:InstanceId,device:Device,deleteOnTermination:DeleteOnTermination},tags:Tags}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_09_root-volume.json"
aws ec2 describe-iam-instance-profile-associations --profile po-r1 --region eu-north-1 --filters Name=instance-id,Values=$I --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_09_profile-association.json"
aws ec2 describe-instance-credit-specifications --profile po-r1 --region eu-north-1 --instance-ids $I --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_09_credit-specification.json"
Get-Content "$E\R11_09_instance.json", "$E\R11_09_root-volume.json", "$E\R11_09_profile-association.json", "$E\R11_09_credit-specification.json"
```

CloudShell:

```bash
cd ~/po/R11
I=$(out R11_outputs.json InstanceId); echo "InstanceId=$I"
aws ec2 describe-instances --region eu-north-1 --instance-ids $I --query 'Reservations[0].Instances[0].{id:InstanceId,state:State.Name,type:InstanceType,image:ImageId,arch:Architecture,az:Placement.AvailabilityZone,subnet:SubnetId,vpc:VpcId,privateIp:PrivateIpAddress,publicIp:PublicIpAddress,publicDns:PublicDnsName,groups:SecurityGroups[].GroupId,profile:IamInstanceProfile.Arn,keyName:KeyName,metadata:MetadataOptions,rootDevice:RootDeviceName,blockDevices:BlockDeviceMappings,tags:Tags}' --output json > R11_09_instance.json 2>&1
VOL=$(aws ec2 describe-instances --region eu-north-1 --instance-ids $I --query "Reservations[0].Instances[0].BlockDeviceMappings[?DeviceName=='/dev/xvda'].Ebs.VolumeId | [0]" --output text); echo "RootVolume=$VOL"
aws ec2 describe-volumes --region eu-north-1 --volume-ids $VOL --query 'Volumes[].{id:VolumeId,type:VolumeType,encrypted:Encrypted,kms:KmsKeyId,size:Size,attach:Attachments[].{instance:InstanceId,device:Device,deleteOnTermination:DeleteOnTermination},tags:Tags}' --output json > R11_09_root-volume.json 2>&1
aws ec2 describe-iam-instance-profile-associations --region eu-north-1 --filters Name=instance-id,Values=$I --output json > R11_09_profile-association.json 2>&1
aws ec2 describe-instance-credit-specifications --region eu-north-1 --instance-ids $I --output json > R11_09_credit-specification.json 2>&1
cat R11_09_instance.json R11_09_root-volume.json R11_09_profile-association.json R11_09_credit-specification.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_09_instance.json` | `state` `running`; `type` `t3.medium`; `image` = the image of `R11_03_image.json`; `arch` `x86_64`; `az` = `PrivateSubnetAz` and `subnet` = `PrivateSubnetId` of `R4_outputs.json`; **`publicIp` null and `publicDns` empty**; `groups` = [`HostSecurityGroupId`]; `profile` = `InstanceProfileArn` of `R5_outputs.json` (DC-14); `keyName` null; `metadata.HttpTokens` `required`, `metadata.HttpPutResponseHopLimit` 1, `metadata.HttpEndpoint` `enabled`, `metadata.State` `applied`; `rootDevice` `/dev/xvda` and exactly one block device; tags `Name` and `project` |
| `R11_09_root-volume.json` | One volume: `type` `gp3`, `encrypted` true, `kms` = the key of `R11_03_ebs-default-key.json` (resolved ARN; point 5), `attach` = one entry on `InstanceId`, device `/dev/xvda`, `deleteOnTermination` true; tag `project` |
| `R11_09_profile-association.json` | One association, `State` `associated`, `IamInstanceProfile.Arn` = `InstanceProfileArn` (DC-14, DC-09) |
| `R11_09_credit-specification.json` | `CpuCredits` `standard` (point 6) |

### Step 10 — SSM registration and a Run Command smoke test (exit condition 2)

What it does: waits until the SSM Agent on the host reports `Online` (through the `ssm`, `ssmmessages`
and `ec2messages` endpoints only), then runs one fixed `echo`. A command that never arrives answers the
R4-D3 / R5 known gap (the SSM Agent's regional S3 buckets): report it, do not open a route.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$I = O "$E\R11_outputs.json" InstanceId; "InstanceId=$I"
for ($n = 0; $n -lt 30; $n++) { $s = aws ssm describe-instance-information --profile po-r1 --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query "InstanceInformationList[0].PingStatus" --output text; "try $n : $s"; if ($s -eq "Online") { break }; Start-Sleep -Seconds 20 }
aws ssm describe-instance-information --profile po-r1 --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query "InstanceInformationList[].{id:InstanceId,ping:PingStatus,platform:PlatformName,version:PlatformVersion,agent:AgentVersion,ip:IPAddress,resourceType:ResourceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_10_instance-information.json"
function Send-R11($name, [string[]]$lines) {
  $p = Join-Path $env:TEMP "r11-$name.json"
  ConvertTo-Json -InputObject @{ commands = $lines; executionTimeout = @("120") } | Out-File -Encoding ascii $p
  $c = aws ssm send-command --profile po-r1 --region eu-north-1 --instance-ids $I --document-name AWS-RunShellScript --comment "R11 $name" --parameters "file://$p" --query "Command.CommandId" --output text
  Remove-Item $p; "CommandId=$c"
  aws ssm wait command-executed --profile po-r1 --region eu-north-1 --command-id $c --instance-id $I
  aws ssm get-command-invocation --profile po-r1 --region eu-north-1 --command-id $c --instance-id $I --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_$name.json"
  Get-Content "$E\R11_$name.json"
}
Send-R11 "10_run-command" @("echo R11_RUN_COMMAND_OK", "uname -m")
```

CloudShell:

```bash
cd ~/po/R11
I=$(out R11_outputs.json InstanceId); echo "InstanceId=$I"
for n in $(seq 0 29); do s=$(aws ssm describe-instance-information --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query 'InstanceInformationList[0].PingStatus' --output text); echo "try $n : $s"; [ "$s" = "Online" ] && break; sleep 20; done
aws ssm describe-instance-information --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query 'InstanceInformationList[].{id:InstanceId,ping:PingStatus,platform:PlatformName,version:PlatformVersion,agent:AgentVersion,ip:IPAddress,resourceType:ResourceType}' --output json > R11_10_instance-information.json 2>&1
send_r11() { name=$1; shift; jq -n '{commands: $ARGS.positional, executionTimeout: ["120"]}' --args "$@" > /tmp/r11-$name.json
  c=$(aws ssm send-command --region eu-north-1 --instance-ids "$I" --document-name AWS-RunShellScript --comment "R11 $name" --parameters file:///tmp/r11-$name.json --query Command.CommandId --output text)
  rm -f /tmp/r11-$name.json; echo "CommandId=$c"
  aws ssm wait command-executed --region eu-north-1 --command-id "$c" --instance-id "$I"
  aws ssm get-command-invocation --region eu-north-1 --command-id "$c" --instance-id "$I" --output json > R11_$name.json 2>&1; cat R11_$name.json; }
send_r11 10_run-command "echo R11_RUN_COMMAND_OK" "uname -m"
```

| Evidence file | PASS criterion |
|---|---|
| `R11_10_instance-information.json` | One entry: `id` = `InstanceId`, `ping` `Online`, `platform` `Amazon Linux`, `version` starts `2023`, `resourceType` `EC2Instance`, `ip` = the host's `privateIp` of step 09 |
| `R11_10_run-command.json` | `Status` `Success`; `ResponseCode` 0; `StandardOutputContent` = `R11_RUN_COMMAND_OK` and `x86_64` on two lines; `StandardErrorContent` empty |

**STOP rule.** If the agent never reaches `Online` within the 30 tries (10 minutes), or the command is
not `Success`: report it. Do not add an S3 or internet route; the agent writes the successor record
(R4-D3, R5 known gap). Continue with step 13 (delete) before the session ends.

### Step 11 — On the host: private DNS, IMDS, the identity, the secret read (DC-02, DC-14, DC-09; DC-19–DC-21 notes)

What it does, in one Run Command: resolves the six service names (they must resolve to the endpoints'
private addresses); shows that IMDSv1 is refused and an IMDSv2 token is issued (the token itself is
never printed); reads the instance profile ARN from IMDS (`iam/info`, never the credentials path); shows
the caller as the runtime role through the `sts` endpoint; reads the runtime secret through the
`secretsmanager` endpoint and the key (R6-D3), **printing only the version stage**, never the value.

PowerShell (`Send-R11` and `$I` from step 10 must exist in this window; if not, repeat step 10's
`function O`, `$I = …` and `function Send-R11` lines first):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
$SA = ((Get-Content "$V2\R8\R8_outputs.json" -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq SecretArn).OutputValue; "SecretArn=$SA"
$L = @("SECRET_ID=$SA") + (@'
REGION=eu-north-1
for s in bedrock-runtime sts secretsmanager ssm ssmmessages ec2messages; do echo "dns $s $(getent ahostsv4 $s.$REGION.amazonaws.com | awk '{print $1}' | sort -u | tr '\n' ' ')"; done
echo "imdsv1_http=$(curl -s -o /dev/null -w '%{http_code}' http://169.254.169.254/latest/meta-data/instance-id)"
T=$(curl -s -X PUT -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' http://169.254.169.254/latest/api/token)
if [ -n "$T" ]; then echo "imdsv2_token=issued"; else echo "imdsv2_token=none"; fi
echo "instance_profile_arn=$(curl -s -H "X-aws-ec2-metadata-token: $T" http://169.254.169.254/latest/meta-data/iam/info | sed -n 's/.*"InstanceProfileArn" *: *"\([^"]*\)".*/\1/p')"
T=""
echo "caller_arn=$(aws sts get-caller-identity --region $REGION --query Arn --output text 2>&1)"
echo "aws_cli=$(aws --version 2>&1 | cut -d' ' -f1)"
echo "secret_read=$(aws secretsmanager get-secret-value --region $REGION --secret-id "$SECRET_ID" --query VersionStages --output text 2>&1 | tr '\n\t' '  ')"
'@ -split "`r?`n" | Where-Object { $_ -ne "" })
Send-R11 "11_host-checks" $L
```

CloudShell (`send_r11` and `$I` from step 10):

```bash
cd ~/po/R11
SA=$(out $V2/R8/R8_outputs.json SecretArn); echo "SecretArn=$SA"
cat > /tmp/r11-11.sh <<'EOF'
REGION=eu-north-1
for s in bedrock-runtime sts secretsmanager ssm ssmmessages ec2messages; do echo "dns $s $(getent ahostsv4 $s.$REGION.amazonaws.com | awk '{print $1}' | sort -u | tr '\n' ' ')"; done
echo "imdsv1_http=$(curl -s -o /dev/null -w '%{http_code}' http://169.254.169.254/latest/meta-data/instance-id)"
T=$(curl -s -X PUT -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' http://169.254.169.254/latest/api/token)
if [ -n "$T" ]; then echo "imdsv2_token=issued"; else echo "imdsv2_token=none"; fi
echo "instance_profile_arn=$(curl -s -H "X-aws-ec2-metadata-token: $T" http://169.254.169.254/latest/meta-data/iam/info | sed -n 's/.*"InstanceProfileArn" *: *"\([^"]*\)".*/\1/p')"
T=""
echo "caller_arn=$(aws sts get-caller-identity --region $REGION --query Arn --output text 2>&1)"
echo "aws_cli=$(aws --version 2>&1 | cut -d' ' -f1)"
echo "secret_read=$(aws secretsmanager get-secret-value --region $REGION --secret-id "$SECRET_ID" --query VersionStages --output text 2>&1 | tr '\n\t' '  ')"
EOF
mapfile -t L < /tmp/r11-11.sh; rm -f /tmp/r11-11.sh
send_r11 11_host-checks "SECRET_ID=$SA" "${L[@]}"
```

| Evidence file | PASS criterion |
|---|---|
| `R11_11_host-checks.json` | `Status` `Success`. `StandardOutputContent`: six `dns <service> <address>` lines, each address inside the subnet CIDR (`10.60.0.0/25`, `R4_07_subnet.json`) and equal to the `ip` of the endpoint ENI for that service in `R11_08_network-interfaces.json` (agent maps ENI ids from `R11_08_vpc-endpoints.json`; DC-02); `imdsv1_http=401`; `imdsv2_token=issued`; `instance_profile_arn` = `InstanceProfileArn` of `R5_outputs.json` (DC-14); `caller_arn` starts `arn:aws:sts::797661577394:assumed-role/proposal-orchestrator-runtime-role/` and ends with `InstanceId` (DC-14, DC-09, F1); `aws_cli` starts `aws-cli/2.`; `secret_read=AWSCURRENT` (runtime read through Secrets Manager and the key; DC-19, DC-20, DC-21 notes). No other content |

**STOP rule.** A public address for any service, `imdsv1_http` other than `401`, a caller other than
the runtime role, or an `AccessDenied` on the secret read: report it (the secret read against DC-19 to
DC-21, R8 consequence). Continue with step 13 before the session ends.

### Step 12 — One Converse call from the host over PrivateLink (DC-37, exit condition 3)

What it does: one `Converse` call with the fixed prompt `Reply with exactly DEPLOY_OK` (test string
from `deploy/aws/collector_inputs.json`), at most 10 output tokens, to `TransportModelId` of
`deploy/aws/parameters/secret.json` (point 2), under the runtime role. The reply is compared **on the
host** and printed only if it equals the test string. The call time (UTC) is printed for step 20.

PowerShell (`Send-R11` and `$I` from step 10):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
$MODEL = ((Get-Content deploy\aws\parameters\secret.json -Raw | ConvertFrom-Json) | Where-Object ParameterKey -eq TransportModelId).ParameterValue
$TEST = (Get-Content deploy\aws\collector_inputs.json -Raw | ConvertFrom-Json).inputs.converse_test_string.value
"Model=$MODEL Test=$TEST"
$L = @("MODEL=$MODEL", "TEST=$TEST") + (@'
REGION=eu-north-1
echo "call_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '[{"role":"user","content":[{"text":"Reply with exactly %s"}]}]' "$TEST" > /tmp/r11-msg.json
reply=$(aws bedrock-runtime converse --region "$REGION" --model-id "$MODEL" --messages file:///tmp/r11-msg.json --inference-config '{"maxTokens":10}' --query 'output.message.content[0].text' --output text 2>/tmp/r11-err)
rc=$?
rm -f /tmp/r11-msg.json
echo "converse_exit=$rc"
code=$(sed -n 's/.*An error occurred (\([A-Za-z0-9.]*\)).*/\1/p' /tmp/r11-err | head -n 1)
rm -f /tmp/r11-err
[ -z "$code" ] || echo "error_code=$code"
reply=$(printf '%s' "$reply" | tr -d '\r\n' | sed 's/^ *//; s/ *$//')
if [ "$rc" -eq 0 ] && [ "$reply" = "$TEST" ]; then echo "reply=$TEST"; else echo "reply_equals_test_string=no"; fi
reply=""
echo "caller_arn=$(aws sts get-caller-identity --region $REGION --query Arn --output text 2>&1)"
'@ -split "`r?`n" | Where-Object { $_ -ne "" })
Send-R11 "12_converse" $L
```

CloudShell (`send_r11` and `$I` from step 10):

```bash
cd ~/po/R11
MODEL=$(jq -r '.[] | select(.ParameterKey=="TransportModelId") | .ParameterValue' $D/parameters/secret.json)
TEST=$(jq -r '.inputs.converse_test_string.value' $D/collector_inputs.json); echo "Model=$MODEL Test=$TEST"
cat > /tmp/r11-12.sh <<'EOF'
REGION=eu-north-1
echo "call_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '[{"role":"user","content":[{"text":"Reply with exactly %s"}]}]' "$TEST" > /tmp/r11-msg.json
reply=$(aws bedrock-runtime converse --region "$REGION" --model-id "$MODEL" --messages file:///tmp/r11-msg.json --inference-config '{"maxTokens":10}' --query 'output.message.content[0].text' --output text 2>/tmp/r11-err)
rc=$?
rm -f /tmp/r11-msg.json
echo "converse_exit=$rc"
code=$(sed -n 's/.*An error occurred (\([A-Za-z0-9.]*\)).*/\1/p' /tmp/r11-err | head -n 1)
rm -f /tmp/r11-err
[ -z "$code" ] || echo "error_code=$code"
reply=$(printf '%s' "$reply" | tr -d '\r\n' | sed 's/^ *//; s/ *$//')
if [ "$rc" -eq 0 ] && [ "$reply" = "$TEST" ]; then echo "reply=$TEST"; else echo "reply_equals_test_string=no"; fi
reply=""
echo "caller_arn=$(aws sts get-caller-identity --region $REGION --query Arn --output text 2>&1)"
EOF
mapfile -t L < /tmp/r11-12.sh; rm -f /tmp/r11-12.sh
send_r11 12_converse "MODEL=$MODEL" "TEST=$TEST" "${L[@]}"
```

| Evidence file | PASS criterion |
|---|---|
| `R11_12_converse.json` | `Status` `Success`; `StandardOutputContent` holds exactly: `call_utc=<UTC time>`, `converse_exit=0`, `reply=DEPLOY_OK`, `caller_arn=arn:aws:sts::797661577394:assumed-role/proposal-orchestrator-runtime-role/<InstanceId>`; no `error_code` and no `reply_equals_test_string=no` line; `StandardErrorContent` empty |

**STOP rule.** `converse_exit` non-zero: report the `error_code` only. `AccessDeniedException` is the
F-R5-2 / DC-04 case (the invoke policy or the endpoint policy refuses a routed call): the agent writes
the successor record and an UPDATE change set; no policy named or described as temporary is created.
`ThrottlingException`: wait one minute and repeat step 12 once (Opus 4.6 has 5 requests per minute,
F-R2-2; F-R10-2). `reply_equals_test_string=no` with exit 0: report it; the reply itself is not saved.
Continue with step 13 before the session ends.

### Step 13 — F1: the caller's role carries the boundary and the explicit deny; then delete the stack (OD5)

What it does: 13a records that the role seen in steps 11 and 12 carries the permission boundary and the
explicit deny (closes F1 together with step 20). 13b deletes the host stack: the hourly charges stop when
it reaches `DELETE_COMPLETE`. Write the delete time (UTC) in `RUNLOG.md`.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$RN = O "$V2\R5\R5_outputs.json" RuntimeRoleName
# 13a
aws iam get-role --profile po-r1 --role-name $RN --query "Role.{arn:Arn,boundary:PermissionsBoundary,maxSession:MaxSessionDuration}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_13_runtime-role.json"
aws iam list-attached-role-policies --profile po-r1 --role-name $RN --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_13_runtime-role-attached.json"
# 13b
& { aws cloudformation delete-stack --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host; "delete exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_13_delete-exit.txt"
aws cloudformation wait stack-delete-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_13_host-stack-after.txt"
Get-Content "$E\R11_13_runtime-role.json", "$E\R11_13_runtime-role-attached.json", "$E\R11_13_delete-exit.txt", "$E\R11_13_host-stack-after.txt"
```

CloudShell:

```bash
cd ~/po/R11
RN=$(out $V2/R5/R5_outputs.json RuntimeRoleName)
aws iam get-role --role-name $RN --query 'Role.{arn:Arn,boundary:PermissionsBoundary,maxSession:MaxSessionDuration}' --output json > R11_13_runtime-role.json 2>&1
aws iam list-attached-role-policies --role-name $RN --output json > R11_13_runtime-role-attached.json 2>&1
{ aws cloudformation delete-stack --region eu-north-1 --stack-name proposal-orchestrator-host; echo "delete exit=$?"; } > R11_13_delete-exit.txt 2>&1
aws cloudformation wait stack-delete-complete --region eu-north-1 --stack-name proposal-orchestrator-host
{ aws cloudformation describe-stacks --region eu-north-1 --stack-name proposal-orchestrator-host --output json; echo "exit=$?"; } > R11_13_host-stack-after.txt 2>&1
cat R11_13_runtime-role.json R11_13_runtime-role-attached.json R11_13_delete-exit.txt R11_13_host-stack-after.txt
```

| Evidence file | PASS criterion |
|---|---|
| `R11_13_runtime-role.json` | `arn` = `RuntimeRoleArn`; `boundary.PermissionsBoundaryType` `Policy` and `boundary.PermissionsBoundaryArn` = `PermissionBoundaryArn` of `R5_outputs.json` (DC-12 on the role that ran, F1) |
| `R11_13_runtime-role-attached.json` | Exactly the four R5 policies: `-bedrock-invoke`, `-supporting-services`, `-deploy-bucket-read` and `-explicit-deny` (= `ExplicitDenyPolicyArn`), as in `R5_08_runtime-role-attached.json` |
| `R11_13_delete-exit.txt` | `delete exit=0` |
| `R11_13_host-stack-after.txt` | Contains `ValidationError` and `does not exist`; last line `exit=254` |

**STOP rule.** If the wait fails (`DELETE_FAILED`): run the describe-stack-events line of step 06 into
`R11_13_stack-events.json`, report the failed resource and reason, and keep trying nothing else by hand;
the agent writes `STEPS_fix1.md`. A stuck endpoint or instance keeps costing until the delete succeeds.

### Step 14 — The deletion is clean and the base stacks are intact (exit condition 5)

What it does: shows that the endpoints, the host, its root volume and every network interface are gone,
that the five base stacks and the 25 exports are exactly as in step 03, and that no stack imports the
six exports any more.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$VPC = O "$V2\R4\R4_outputs.json" VpcId
$I = O "$E\R11_outputs.json" InstanceId
$VOL = ((Get-Content "$E\R11_09_root-volume.json" -Raw | ConvertFrom-Json) | Select-Object -First 1).id; "InstanceId=$I RootVolume=$VOL"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_14_vpc-endpoints-after.json"
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_14_network-interfaces-after.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --instance-ids $I --query "Reservations[].Instances[].{id:InstanceId,state:State.Name}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_14_instance-after.json"
& { aws ec2 describe-volumes --profile po-r1 --region eu-north-1 --volume-ids $VOL --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_14_root-volume-after.txt"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_14_base-stacks.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-')].{name:Name,value:Value}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_14_exports.json"
& { foreach ($x in @("network-VpcId","network-PrivateSubnetId","network-EndpointSecurityGroupId","network-HostSecurityGroupId","iam-RuntimeRoleArn","iam-InstanceProfileName")) { "== proposal-orchestrator-$x"; aws cloudformation list-imports --profile po-r1 --region eu-north-1 --export-name "proposal-orchestrator-$x" --output json; "exit=$LASTEXITCODE" } } 2>&1 | Out-File -Encoding utf8 "$E\R11_14_imports-after.txt"
Get-ChildItem "$E\R11_14_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

CloudShell:

```bash
cd ~/po/R11
VPC=$(out $V2/R4/R4_outputs.json VpcId); I=$(out R11_outputs.json InstanceId)
VOL=$(jq -r '.[0].id' R11_09_root-volume.json); echo "InstanceId=$I RootVolume=$VOL"
aws ec2 describe-vpc-endpoints --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query 'VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,state:State}' --output json > R11_14_vpc-endpoints-after.json 2>&1
aws ec2 describe-network-interfaces --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query 'NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType}' --output json > R11_14_network-interfaces-after.json 2>&1
aws ec2 describe-instances --region eu-north-1 --instance-ids $I --query 'Reservations[].Instances[].{id:InstanceId,state:State.Name}' --output json > R11_14_instance-after.json 2>&1
{ aws ec2 describe-volumes --region eu-north-1 --volume-ids $VOL --output json; echo "exit=$?"; } > R11_14_root-volume-after.txt 2>&1
aws cloudformation describe-stacks --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json > R11_14_base-stacks.json 2>&1
aws cloudformation list-exports --region eu-north-1 --query "Exports[?starts_with(Name, 'proposal-orchestrator-')].{name:Name,value:Value}" --output json > R11_14_exports.json 2>&1
{ for x in network-VpcId network-PrivateSubnetId network-EndpointSecurityGroupId network-HostSecurityGroupId iam-RuntimeRoleArn iam-InstanceProfileName; do echo "== proposal-orchestrator-$x"; aws cloudformation list-imports --region eu-north-1 --export-name "proposal-orchestrator-$x" --output json; echo "exit=$?"; done; } > R11_14_imports-after.txt 2>&1
for f in R11_14_*; do echo "== $f"; cat "$f"; done
```

| Evidence file | PASS criterion |
|---|---|
| `R11_14_vpc-endpoints-after.json` | Exactly the S3 gateway endpoint, as in `R11_03_vpc-endpoints-before.json` (a `deleted` interface entry may linger for a few minutes: repeat the line until it is gone) |
| `R11_14_network-interfaces-after.json` | `[]` (endpoint ENIs may take a few minutes to go: repeat the line) |
| `R11_14_instance-after.json` | One entry, `state` `terminated` |
| `R11_14_root-volume-after.txt` | Contains `InvalidVolume.NotFound`; last line `exit=254` (`DeleteOnTermination` worked) |
| `R11_14_base-stacks.json` | Equal to `R11_03_base-stacks.json` (same five stacks, same `status`, same `updated`); no `proposal-orchestrator-host` |
| `R11_14_exports.json` | Equal to `R11_03_exports.json` (25 names and values) |
| `R11_14_imports-after.txt` | For each of the six exports a `ValidationError` saying it is not imported by any stack, and `exit=254` |

### Step 15 — Create the recreation change set (nothing is created yet)

What it does: plans the host stack again from the same template and parameter file (exit condition 5,
"recreates from the templates").

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-02 --change-set-type CREATE --template-body file://deploy/aws/templates/90-host.yaml --parameters file://deploy/aws/parameters/host.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_15_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-02
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-02 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_15_change-set.json"
Get-Content "$E\R11_15_create-change-set.json", "$E\R11_15_change-set.json"
```

CloudShell:

```bash
cd ~/po/R11
aws cloudformation create-change-set --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-02 --change-set-type CREATE --template-body file://$D/templates/90-host.yaml --parameters file://$D/parameters/host.json --tags Key=project,Value=proposal-orchestrator --output json > R11_15_create-change-set.json 2>&1
aws cloudformation wait change-set-create-complete --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-02
aws cloudformation describe-change-set --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-02 --output json > R11_15_change-set.json 2>&1
cat R11_15_create-change-set.json R11_15_change-set.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_15_create-change-set.json` | As `R11_05_create-change-set.json`, with `r11-create-02` |
| `R11_15_change-set.json` | As `R11_05_change-set.json`: the same seven `Add` entries and the same parameters (`LatestAmiId` may resolve to a newer image; the agent records it) |

### Step 16 — STOP: the operator's second go

**Hand back here (end of round 2).** Report steps 06–15 in session. Both of us read
`R11_15_change-set.json`. **Step 17 runs only after your explicit go in session**; it starts the hourly
charges again until step 19. Record the go in `RUNLOG.md`. If you decide not to recreate today, delete
the change set's stack (`aws cloudformation delete-stack --stack-name proposal-orchestrator-host`, it
holds no resource) and run steps 20–22; the recreation then becomes a later session's first step.

No evidence file.

### Step 17 — Execute the recreation and save its outputs

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
& { aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-02; "execute exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_17_execute-exit.txt"
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_17_stack-events.json"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_17_outputs-recreated.json"
Get-Content "$E\R11_17_execute-exit.txt", "$E\R11_17_outputs-recreated.json"
```

CloudShell:

```bash
cd ~/po/R11
{ aws cloudformation execute-change-set --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-create-02; echo "execute exit=$?"; } > R11_17_execute-exit.txt 2>&1
aws cloudformation wait stack-create-complete --region eu-north-1 --stack-name proposal-orchestrator-host
aws cloudformation describe-stack-events --region eu-north-1 --stack-name proposal-orchestrator-host --query 'StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}' --output json > R11_17_stack-events.json 2>&1
aws cloudformation describe-stacks --region eu-north-1 --stack-name proposal-orchestrator-host --query 'Stacks[0].Outputs' --output json > R11_17_outputs-recreated.json 2>&1
cat R11_17_execute-exit.txt R11_17_outputs-recreated.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_17_execute-exit.txt` | `execute exit=0` |
| `R11_17_stack-events.json` | The seven logical ids and the stack reach `CREATE_COMPLETE`; no `*_FAILED`, no `ROLLBACK` |
| `R11_17_outputs-recreated.json` | The seven contract keys, no `ExportName`; every id **differs** from `R11_outputs.json` (new resources) |

### Step 18 — Re-check the recreated stack

What it does: the structural checks of steps 08 and 09 on the new ids, and one Run Command with the DNS
check (point 9). The commands are those of steps 08, 09, 10 and 11 with two changes: the outputs file is
`R11_17_outputs-recreated.json`, and the evidence names start `R11_18_`.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$OUT = "$E\R11_17_outputs-recreated.json"
$VPC = O "$V2\R4\R4_outputs.json" VpcId
$EP = @("BedrockRuntimeEndpointId","StsEndpointId","SecretsManagerEndpointId","SsmEndpointId","SsmMessagesEndpointId","Ec2MessagesEndpointId") | ForEach-Object { O $OUT $_ }
$I = O $OUT InstanceId; "InstanceId=$I Endpoints=$($EP -join ' ')"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --vpc-endpoint-ids $EP --query "VpcEndpoints[].{id:VpcEndpointId,service:ServiceName,type:VpcEndpointType,state:State,privateDns:PrivateDnsEnabled,vpc:VpcId,subnets:SubnetIds,groups:Groups[].GroupId,enis:NetworkInterfaceIds}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_18_vpc-endpoints.json"
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,subnet:SubnetId,ip:PrivateIpAddress,publicIp:Association.PublicIp,groups:Groups[].GroupId,instance:Attachment.InstanceId}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_18_network-interfaces.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --instance-ids $I --query "Reservations[0].Instances[0].{id:InstanceId,state:State.Name,type:InstanceType,publicIp:PublicIpAddress,publicDns:PublicDnsName,groups:SecurityGroups[].GroupId,profile:IamInstanceProfile.Arn,keyName:KeyName,metadata:MetadataOptions,rootDevice:RootDeviceName,blockDevices:BlockDeviceMappings}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_18_instance.json"
$VOL = aws ec2 describe-instances --profile po-r1 --region eu-north-1 --instance-ids $I --query "Reservations[0].Instances[0].BlockDeviceMappings[?DeviceName=='/dev/xvda'].Ebs.VolumeId | [0]" --output text
aws ec2 describe-volumes --profile po-r1 --region eu-north-1 --volume-ids $VOL --query "Volumes[].{id:VolumeId,type:VolumeType,encrypted:Encrypted,kms:KmsKeyId,attach:Attachments[].{instance:InstanceId,deleteOnTermination:DeleteOnTermination}}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_18_root-volume.json"
for ($n = 0; $n -lt 30; $n++) { $s = aws ssm describe-instance-information --profile po-r1 --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query "InstanceInformationList[0].PingStatus" --output text; "try $n : $s"; if ($s -eq "Online") { break }; Start-Sleep -Seconds 20 }
function Send-R11($name, [string[]]$lines) {
  $p = Join-Path $env:TEMP "r11-$name.json"
  ConvertTo-Json -InputObject @{ commands = $lines; executionTimeout = @("120") } | Out-File -Encoding ascii $p
  $c = aws ssm send-command --profile po-r1 --region eu-north-1 --instance-ids $I --document-name AWS-RunShellScript --comment "R11 $name" --parameters "file://$p" --query "Command.CommandId" --output text
  Remove-Item $p; "CommandId=$c"
  aws ssm wait command-executed --profile po-r1 --region eu-north-1 --command-id $c --instance-id $I
  aws ssm get-command-invocation --profile po-r1 --region eu-north-1 --command-id $c --instance-id $I --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_$name.json"
  Get-Content "$E\R11_$name.json"
}
Send-R11 "18_run-command" @("echo R11_RUN_COMMAND_OK", 'for s in bedrock-runtime sts secretsmanager ssm ssmmessages ec2messages; do echo "dns $s $(getent ahostsv4 $s.eu-north-1.amazonaws.com | awk ''{print $1}'' | sort -u | tr ''\n'' '' '')"; done')
Get-ChildItem "$E\R11_18_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

CloudShell (`send_r11` from step 10; it reads `$I`):

```bash
cd ~/po/R11
OUT=R11_17_outputs-recreated.json; VPC=$(out $V2/R4/R4_outputs.json VpcId)
EP=$(for k in BedrockRuntimeEndpointId StsEndpointId SecretsManagerEndpointId SsmEndpointId SsmMessagesEndpointId Ec2MessagesEndpointId; do out $OUT $k; done | tr '\n' ' ')
I=$(out $OUT InstanceId); echo "InstanceId=$I Endpoints=$EP"
aws ec2 describe-vpc-endpoints --region eu-north-1 --vpc-endpoint-ids $EP --query 'VpcEndpoints[].{id:VpcEndpointId,service:ServiceName,type:VpcEndpointType,state:State,privateDns:PrivateDnsEnabled,vpc:VpcId,subnets:SubnetIds,groups:Groups[].GroupId,enis:NetworkInterfaceIds}' --output json > R11_18_vpc-endpoints.json 2>&1
aws ec2 describe-network-interfaces --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query 'NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,subnet:SubnetId,ip:PrivateIpAddress,publicIp:Association.PublicIp,groups:Groups[].GroupId,instance:Attachment.InstanceId}' --output json > R11_18_network-interfaces.json 2>&1
aws ec2 describe-instances --region eu-north-1 --instance-ids $I --query 'Reservations[0].Instances[0].{id:InstanceId,state:State.Name,type:InstanceType,publicIp:PublicIpAddress,publicDns:PublicDnsName,groups:SecurityGroups[].GroupId,profile:IamInstanceProfile.Arn,keyName:KeyName,metadata:MetadataOptions,rootDevice:RootDeviceName,blockDevices:BlockDeviceMappings}' --output json > R11_18_instance.json 2>&1
VOL=$(aws ec2 describe-instances --region eu-north-1 --instance-ids $I --query "Reservations[0].Instances[0].BlockDeviceMappings[?DeviceName=='/dev/xvda'].Ebs.VolumeId | [0]" --output text)
aws ec2 describe-volumes --region eu-north-1 --volume-ids $VOL --query 'Volumes[].{id:VolumeId,type:VolumeType,encrypted:Encrypted,kms:KmsKeyId,attach:Attachments[].{instance:InstanceId,deleteOnTermination:DeleteOnTermination}}' --output json > R11_18_root-volume.json 2>&1
for n in $(seq 0 29); do s=$(aws ssm describe-instance-information --region eu-north-1 --filters "Key=InstanceIds,Values=$I" --query 'InstanceInformationList[0].PingStatus' --output text); echo "try $n : $s"; [ "$s" = "Online" ] && break; sleep 20; done
send_r11 18_run-command "echo R11_RUN_COMMAND_OK" 'for s in bedrock-runtime sts secretsmanager ssm ssmmessages ec2messages; do echo "dns $s $(getent ahostsv4 $s.eu-north-1.amazonaws.com | awk '"'"'{print $1}'"'"' | sort -u | tr '"'"'\n'"'"' '"'"' '"'"')"; done'
for f in R11_18_*; do echo "== $f"; cat "$f"; done
```

| Evidence file | PASS criterion |
|---|---|
| `R11_18_vpc-endpoints.json` | As `R11_08_vpc-endpoints.json` for the new ids: six, `Interface`, `available`, private DNS on, the one subnet, the endpoint group |
| `R11_18_network-interfaces.json` | Seven interfaces in the subnet, none with a `publicIp`; groups as in step 08 |
| `R11_18_instance.json` | `running`, `t3.medium`, `publicIp` null, `publicDns` empty, groups [`HostSecurityGroupId`], `profile` = `InstanceProfileArn`, `keyName` null, `HttpTokens` `required`, `HttpPutResponseHopLimit` 1, root `/dev/xvda` |
| `R11_18_root-volume.json` | `gp3`, `encrypted` true, the same `kms` as step 09, `deleteOnTermination` true |
| `R11_18_run-command.json` | `Status` `Success`; `R11_RUN_COMMAND_OK` and six `dns` lines with addresses in `10.60.0.0/25` |

### Step 19 — Delete the stack again (end of session, OD5)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
& { aws cloudformation delete-stack --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host; "delete exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_19_delete-exit.txt"
aws cloudformation wait stack-delete-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_19_host-stack-after.txt"
$VPC = O "$V2\R4\R4_outputs.json" VpcId
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_19_network-interfaces-after.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query "Reservations[].Instances[].{id:InstanceId,state:State.Name}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_19_instances-after.json"
aws ec2 describe-volumes --profile po-r1 --region eu-north-1 --filters Name=tag:project,Values=proposal-orchestrator --query "Volumes[].{id:VolumeId,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_19_volumes-after.json"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_19_base-stacks.json"
Get-ChildItem "$E\R11_19_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

CloudShell:

```bash
cd ~/po/R11
{ aws cloudformation delete-stack --region eu-north-1 --stack-name proposal-orchestrator-host; echo "delete exit=$?"; } > R11_19_delete-exit.txt 2>&1
aws cloudformation wait stack-delete-complete --region eu-north-1 --stack-name proposal-orchestrator-host
{ aws cloudformation describe-stacks --region eu-north-1 --stack-name proposal-orchestrator-host --output json; echo "exit=$?"; } > R11_19_host-stack-after.txt 2>&1
VPC=$(out $V2/R4/R4_outputs.json VpcId)
aws ec2 describe-network-interfaces --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query 'NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType}' --output json > R11_19_network-interfaces-after.json 2>&1
aws ec2 describe-instances --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query 'Reservations[].Instances[].{id:InstanceId,state:State.Name}' --output json > R11_19_instances-after.json 2>&1
aws ec2 describe-volumes --region eu-north-1 --filters Name=tag:project,Values=proposal-orchestrator --query 'Volumes[].{id:VolumeId,state:State}' --output json > R11_19_volumes-after.json 2>&1
aws cloudformation describe-stacks --region eu-north-1 --query "Stacks[?starts_with(StackName, 'proposal-orchestrator-')].{name:StackName,status:StackStatus,created:CreationTime,updated:LastUpdatedTime}" --output json > R11_19_base-stacks.json 2>&1
for f in R11_19_*; do echo "== $f"; cat "$f"; done
```

| Evidence file | PASS criterion |
|---|---|
| `R11_19_delete-exit.txt` | `delete exit=0` |
| `R11_19_host-stack-after.txt` | Contains `ValidationError` and `does not exist`; last line `exit=254` |
| `R11_19_network-interfaces-after.json` | `[]` (repeat the line after a few minutes if endpoint ENIs linger) |
| `R11_19_instances-after.json` | `[]` |
| `R11_19_volumes-after.json` | `[]` (no project-tagged volume left) |
| `R11_19_base-stacks.json` | Equal to `R11_03_base-stacks.json` |

Write the delete time (UTC) in `RUNLOG.md`. From here nothing billable by the hour exists.

### Step 20 — CloudTrail: the Converse event, metadata only (DC-26, DC-37, F1)

**Run no earlier than 15 minutes after `call_utc` of `R11_12_converse.json`** (CloudTrail delivers
events to lookup with a delay). What it does: 20a lists the matching events by their lookup metadata
only (`--query` keeps id, name, time, source and user name; no event body). 20b reads each event's
record **in memory** and writes only selected fields: identity type and ARNs, source, name, Region,
time, the VPC endpoint id, the model id, the **names** of the request parameters, whether response
elements exist, and the error code. No request or response body, no access key id and no source
address is written.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
$S = (Get-Content "$E\R11_12_converse.json" -Raw | ConvertFrom-Json).StandardOutputContent
$CALL = ([regex]::Match($S, 'call_utc=(\S+)')).Groups[1].Value; "call_utc=$CALL"
# 20a — lookup metadata only
aws cloudtrail lookup-events --profile po-r1 --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=Converse --start-time $CALL --max-results 20 --query "Events[].{id:EventId,name:EventName,time:EventTime,source:EventSource,user:Username}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_20_converse-lookup.json"
# 20b — selected fields, parsed in memory; the event record itself is never written
$raw = aws cloudtrail lookup-events --profile po-r1 --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=Converse --start-time $CALL --max-results 20 --query "Events[].CloudTrailEvent" --output json
$sel = @(($raw | Out-String | ConvertFrom-Json) | ForEach-Object {
  $ev = $_ | ConvertFrom-Json
  [ordered]@{
    eventId = $ev.eventID; eventTime = $ev.eventTime; eventSource = $ev.eventSource; eventName = $ev.eventName
    awsRegion = $ev.awsRegion; userIdentityType = $ev.userIdentity.type; callerArn = $ev.userIdentity.arn
    sessionIssuerArn = $ev.userIdentity.sessionContext.sessionIssuer.arn; vpcEndpointId = $ev.vpcEndpointId
    modelId = $ev.requestParameters.modelId
    requestParameterNames = $(if ($ev.requestParameters) { @($ev.requestParameters.PSObject.Properties.Name) } else { @() })
    responseElementsNull = ($null -eq $ev.responseElements); errorCode = $ev.errorCode
  } })
ConvertTo-Json -InputObject $sel -Depth 4 | Out-File -Encoding utf8 "$E\R11_20_converse-events.json"
$raw = $null; $sel = $null
Get-Content "$E\R11_20_converse-lookup.json", "$E\R11_20_converse-events.json"
```

CloudShell:

```bash
cd ~/po/R11
CALL=$(jq -r '.StandardOutputContent' R11_12_converse.json | sed -n 's/^call_utc=//p'); echo "call_utc=$CALL"
aws cloudtrail lookup-events --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=Converse --start-time "$CALL" --max-results 20 --query 'Events[].{id:EventId,name:EventName,time:EventTime,source:EventSource,user:Username}' --output json > R11_20_converse-lookup.json 2>&1
aws cloudtrail lookup-events --region eu-north-1 --lookup-attributes AttributeKey=EventName,AttributeValue=Converse --start-time "$CALL" --max-results 20 --query 'Events[].CloudTrailEvent' --output json \
  | jq '[.[] | fromjson | {eventId: .eventID, eventTime, eventSource, eventName, awsRegion, userIdentityType: .userIdentity.type, callerArn: .userIdentity.arn, sessionIssuerArn: .userIdentity.sessionContext.sessionIssuer.arn, vpcEndpointId, modelId: .requestParameters.modelId, requestParameterNames: ((.requestParameters // {}) | keys), responseElementsNull: (.responseElements == null), errorCode}]' > R11_20_converse-events.json
cat R11_20_converse-lookup.json R11_20_converse-events.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_20_converse-lookup.json` | At least one event, `name` `Converse`, `source` `bedrock.amazonaws.com`, `time` at or after `call_utc`; `user` = the host's `InstanceId` of `R11_outputs.json` (the role session name) |
| `R11_20_converse-events.json` | One entry for the step 12 call (`eventTime` within a minute of `call_utc`) with: `eventSource` `bedrock.amazonaws.com`, `eventName` `Converse`, `awsRegion` `eu-north-1`, `userIdentityType` `AssumedRole`, `callerArn` = `arn:aws:sts::797661577394:assumed-role/proposal-orchestrator-runtime-role/<InstanceId>`, `sessionIssuerArn` = `RuntimeRoleArn` of `R5_outputs.json` (the role whose boundary and explicit deny `R11_13_runtime-role*.json` show: **closes F1**, DC-26, DC-37), `vpcEndpointId` = `BedrockRuntimeEndpointId` of `R11_outputs.json` (the call came through PrivateLink), `modelId` = `TransportModelId` or its profile ARN, `errorCode` null. `requestParameterNames` and `responseElementsNull` are recorded (no body is saved either way). The file holds only the fields listed in the command |

**STOP rule.** No event after 30 minutes: repeat 20a and 20b once (overwriting); still none is a DC-26
FAIL to report. A `sessionIssuerArn` other than the runtime role is an F1 FAIL. A missing
`vpcEndpointId` is reported, not a FAIL by itself: the agent then rests the PrivateLink criterion on
steps 08 and 11 (private DNS answer from the endpoint ENIs) and R4 (no internet path), and records it.

### Step 21 — Flow-log delivery (DC-08 note, R7-D18, R5-D4 known gap)

What it does: the VPC had network interfaces from step 06 to step 19, so the flow log has delivered
records by now. Records hold addresses and ports only; this step saves the stream list and a count, not
the records.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$FL = O "$V2\R7\R7_outputs.json" FlowLogId; $FG = O "$V2\R7\R7_outputs.json" FlowLogGroupName; "FlowLogId=$FL Group=$FG"
aws ec2 describe-flow-logs --profile po-r1 --region eu-north-1 --flow-log-ids $FL --query "FlowLogs[].{id:FlowLogId,status:FlowLogStatus,deliver:DeliverLogsStatus,error:DeliverLogsErrorMessage}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_21_flow-log-status.json"
aws logs describe-log-streams --profile po-r1 --region eu-north-1 --log-group-name $FG --query "logStreams[].{name:logStreamName,first:firstEventTimestamp,last:lastEventTimestamp}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_21_flow-log-streams.json"
aws logs filter-log-events --profile po-r1 --region eu-north-1 --log-group-name $FG --limit 50 --query "length(events)" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_21_flow-log-event-count.json"
Get-Content "$E\R11_21_flow-log-status.json", "$E\R11_21_flow-log-streams.json", "$E\R11_21_flow-log-event-count.json"
```

CloudShell:

```bash
cd ~/po/R11
FL=$(out $V2/R7/R7_outputs.json FlowLogId); FG=$(out $V2/R7/R7_outputs.json FlowLogGroupName); echo "FlowLogId=$FL Group=$FG"
aws ec2 describe-flow-logs --region eu-north-1 --flow-log-ids $FL --query 'FlowLogs[].{id:FlowLogId,status:FlowLogStatus,deliver:DeliverLogsStatus,error:DeliverLogsErrorMessage}' --output json > R11_21_flow-log-status.json 2>&1
aws logs describe-log-streams --region eu-north-1 --log-group-name "$FG" --query 'logStreams[].{name:logStreamName,first:firstEventTimestamp,last:lastEventTimestamp}' --output json > R11_21_flow-log-streams.json 2>&1
aws logs filter-log-events --region eu-north-1 --log-group-name "$FG" --limit 50 --query 'length(events)' --output json > R11_21_flow-log-event-count.json 2>&1
cat R11_21_flow-log-status.json R11_21_flow-log-streams.json R11_21_flow-log-event-count.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_21_flow-log-status.json` | `status` `ACTIVE`; `deliver` `SUCCESS`; `error` null |
| `R11_21_flow-log-streams.json` | At least one stream named after a network interface (`eni-…`) of step 08 or 18, with `last` after step 06's time |
| `R11_21_flow-log-event-count.json` | A number ≥ 1 |

**STOP rule.** `deliver` `FAILED`, or no stream: report it; it is the R5-D4 known gap (successor record,
UPDATE of the iam stack). R11's other criteria are unaffected; DC-08 stays as R7 left it.

### Step 22 — Invocation logging still unset; session-end credits (read-only)

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
& { aws bedrock get-model-invocation-logging-configuration --profile po-r1 --region eu-north-1 --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_22_invocation-logging-after.txt"
aws logs describe-log-groups --profile po-r1 --region eu-north-1 --log-group-name-prefix /aws/bedrock --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_22_log-groups-bedrock-after.json"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_22_plan-state-after.json"
Get-Content "$E\R11_22_invocation-logging-after.txt", "$E\R11_22_log-groups-bedrock-after.json", "$E\R11_22_plan-state-after.json"
```

CloudShell:

```bash
cd ~/po/R11
{ aws bedrock get-model-invocation-logging-configuration --region eu-north-1 --output json; echo "exit=$?"; } > R11_22_invocation-logging-after.txt 2>&1
aws logs describe-log-groups --region eu-north-1 --log-group-name-prefix /aws/bedrock --output json > R11_22_log-groups-bedrock-after.json 2>&1
aws freetier get-account-plan-state --output json > R11_22_plan-state-after.json 2>&1
cat R11_22_invocation-logging-after.txt R11_22_log-groups-bedrock-after.json R11_22_plan-state-after.json
```

| Evidence file | PASS criterion |
|---|---|
| `R11_22_invocation-logging-after.txt` | Last line `exit=0`; no `loggingConfig` (DC-28; the Converse call did not turn logging on) |
| `R11_22_log-groups-bedrock-after.json` | `logGroups` = `[]` (DC-29) |
| `R11_22_plan-state-after.json` | `FREE` / `ACTIVE`; credits recorded. Usage is billed with a delay, so the figure may not yet show this session; R14 reconciles it |

**Hand back here (end of round 3).** The agent verifies every file (the Bedrock endpoint policy and the
export lists by script), writes `VERIFICATION.md`, the register v2 rows (DC-01, DC-02, DC-04, DC-05,
DC-14, DC-26, DC-37; the attachment halves of DC-03 and DC-07; DC-09; the DC-08 and DC-19 to DC-21
notes), the decision record and the worklog entry, then step 23.

### Step 23 — Closing: tests, old-ID guard, then the secret scan over the finished folder

Runs only after the agent has written `VERIFICATION.md`, the register v2 rows and the worklog entry, so
the scan sees the final folder. Run `deactivate` first if `.venv-lint` is active. The scan runs last.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_aws_env_config_template.py tests/test_aws_host_template.py tests/test_old_id_guard.py tests/test_host_env_launcher.py } 2>&1 | Out-File -Encoding utf8 "$E\R11_23_pytest.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_23_old-id-guard.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_23_secret-scan.txt"
Get-Content "$E\R11_23_pytest.txt" -Tail 1; Get-Content "$E\R11_23_old-id-guard.txt", "$E\R11_23_secret-scan.txt"
```

CloudShell: not applicable (workstation only).

| Evidence file | PASS criterion |
|---|---|
| `R11_23_pytest.txt` | First line `Python 3.10.…`; last line `259 passed` (or the count the agent states with `VERIFICATION.md`) with no `failed`, `error` or `skipped` |
| `R11_23_old-id-guard.txt` | `CLEAN: …`; `exit=0` |
| `R11_23_secret-scan.txt` | `CLEAN: docs\infrastructure_security\evidence_v2\R11` (or with forward slashes); `exit=0` |

Then commit (operator), and confirm R11 in session; the agent ticks R11 in `plans/aws_redeployment_tickets.md`.

## Outputs

`R11_outputs.json` (step 07) holds the first creation's ids; `R11_17_outputs-recreated.json` the
recreation's. Both stacks are deleted by the end of the session (OD5). R12a and later sessions save the
outputs of their own creation and pass that file to the collector with `--host-outputs`.

## Before you hand back

- [ ] Every evidence file listed above exists in this folder, under exactly its name.
- [ ] You opened each file and checked it for the items under "Before you start".
- [ ] `RUNLOG.md` records the UTC time, who ran each step, each explicit go, the create and delete times
      of both stacks, any deviation and any error.
- [ ] `proposal-orchestrator-host` does not exist (`R11_19_host-stack-after.txt`).
