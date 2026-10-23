# R4 — Network base stack: step sheet

| Field | Value |
|---|---|
| Ticket | `R4` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R4, as read in `plans/aws_redeployment_r4_handoff_2026-10-23.md` §3 |
| Decisions applied | OD3 dedicated VPC, OD4 one zone, OD9 no repository buckets; OD6-r3 (six stacks, change sets, guards); R4-D1 to R4-D4 (`aws-redeployment-r4-network_2026-10-24`); OD1-r1 eu-north-1; R1-D2 session-start check; OD10 Free plan, no upgrade |
| Written by / on | agent (Claude) / 2026-10-24 |
| Account / region | `797661577394` / `eu-north-1`; Free Tier, Budgets and STS are global |
| IDs taken from | `R4_outputs.json`, written by step 06 of this sheet. Steps 07 and 08 take every id from it. Parameter values come from `deploy/aws/parameters/network.json` (zone and prefix list from R3 evidence). |
| Controls touched | DC-06, PL-8 (verified here); DC-03, DC-07 (security-group halves; attachment is R11); DC-05 (S3 half; interface endpoints are R11) |
| Hourly cost created | **none**. VPC, subnet, route table, security groups and an S3 gateway endpoint carry no charge. Still read the change set (step 04) before executing it. |

## Before you start

- **Where commands run.** Everything runs in **PowerShell in the VS Code terminal, from the repository
  root** (`C:\Code\proposal_demo\proposal_orchestrator`), signed in with `aws login --profile po-r1`.
  Every AWS command names `--profile po-r1`; every regional command also names `--region eu-north-1`.
  Evidence lands straight in this folder. CloudShell is the fallback only (see the end of this sheet).
- **`$E` must be set in every new PowerShell window.** Every PowerShell block below starts with the
  line, so copying a whole block is safe. (In R3 an unset `$E` sent `Out-File` to `C:\`.)
- In PowerShell, always pipe to `Out-File -Encoding utf8 <file>`, never use `>`. The files will be
  UTF-8 with BOM; the tests and the scan read them as such.
- If `.venv-lint` is active in your window, run `deactivate` before any `py -3.10` command; lint runs
  through `.\.venv-lint\Scripts\cfn-lint.exe` either way.
- Never save secret values, access keys, session tokens or passwords. No step below prints any.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or `0.0.0.0/0` egress rule, not even temporarily.
  The template contains none; the guard in step 03 proves it before anything is created.
- If a step fails, stop, report the error in session, and do not improvise a fix. In particular: do
  not retry `create-change-set` or `execute-change-set`, and do not delete a stack, without agreeing
  it in session first.
- **Three rounds.** Round 1: steps 01–04, then hand back; you and the agent read the change set.
  Round 2: steps 05–09, then hand back; the agent verifies and writes `VERIFICATION.md`, the register
  rows and the worklog entry. Round 3: step 10 over the finished folder, then commit.

---

## Steps

### Step 01 — Session-start check: credits, budget, alert states (R1-D2)

What it does: confirms that the Free plan is active, the credits are intact and no budget alert is in
`ALARM`, before anything else runs.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_01_budget-notifications.json"
Get-Content "$E\R4_01_plan-state.json", "$E\R4_01_budgets.json", "$E\R4_01_budget-notifications.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R4_01_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `199.00` (R3 left 199.99); `accountPlanExpirationDate` starts `2027-04-19` |
| `R4_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` = `10.0`, `spend` < `8.5` |
| `R4_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` = `OK` |

**STOP rule.** If the plan is not `ACTIVE`, the credits are below 199.00 USD, or any notification is in
`ALARM`, stop here and report it.

### Step 02 — Who is calling

What it does: records that the CLI runs as the OD11-r2 identity in the right account. This is the
account check the deploy step relies on whatever the `DeployTarget` rule does (F-OD6r3-2).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_02_caller-identity.json"
Get-Content "$E\R4_02_caller-identity.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R4_02_caller-identity.json` | `Account` = `797661577394`; `Arn` starts with `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** Any other account: stop. Nothing below may run.

### Step 03 — Lint, guards and tests on the filled template (workstation only, no AWS call)

What it does: proves, before anything is created, that `10-network.yaml` lints for eu-north-1, keeps
the template rules (no gateway, no route resource, no open CIDR, tags, no literals), carries no
old-account id, and has the shape the R4 tests pin.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R4_03_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R4_03_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R4_03_old-id-guard.txt"
py -3.10 -m pytest tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_old_id_guard.py 2>&1 | Out-File -Encoding utf8 "$E\R4_03_pytest.txt"
Get-Content "$E\R4_03_cfn-lint.txt", "$E\R4_03_template-guard.txt", "$E\R4_03_old-id-guard.txt"; Get-Content "$E\R4_03_pytest.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R4_03_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R4_03_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R4_03_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R4_03_pytest.txt` | Header shows `Python 3.10`; last line `N passed` (the agent's run gave 121) with no `failed`, `error` or `skipped` |

**STOP rule.** Any non-zero exit or failed test: stop. The template is not deployed until this step is
clean.

### Step 04 — Create the change set and read it (nothing is created yet)

What it does: asks CloudFormation to plan the stack. A change set of type CREATE builds nothing until
it is executed. Its description is the evidence of exactly what step 05 will create. This is also
where F-OD6r3-2 shows: if CloudFormation refuses the `DeployTarget` rule's pseudo-parameter
references, the error appears here.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-network --change-set-name r4-create-01 --change-set-type CREATE --template-body file://deploy/aws/templates/10-network.yaml --parameters file://deploy/aws/parameters/network.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_04_create-change-set.json"
Get-Content "$E\R4_04_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-network --change-set-name r4-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-network --change-set-name r4-create-01 --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_04_change-set.json"
Get-Content "$E\R4_04_change-set.json"
```

If `create-change-set` itself returns an error (the first file holds the error text instead of an
`Id`), or `wait` reports a terminal failure, still run the `describe-change-set` line: `Status` and
`StatusReason` in `R4_04_change-set.json` are the evidence. Then stop and hand back.

| Evidence file | PASS criterion |
|---|---|
| `R4_04_create-change-set.json` | `Id` starts `arn:aws:cloudformation:eu-north-1:797661577394:changeSet/r4-create-01/`; `StackId` starts `arn:aws:cloudformation:eu-north-1:797661577394:stack/proposal-orchestrator-network/` |
| `R4_04_change-set.json` | `Status` = `CREATE_COMPLETE`; `ExecutionStatus` = `AVAILABLE`; `ChangeSetType` = `CREATE`; `Capabilities` = `[]`; `Tags` = `[{project: proposal-orchestrator}]`; `Parameters` show `ExpectedAccountId` 797661577394, `ExpectedRegion` eu-north-1, `AvailabilityZone` eu-north-1a, `S3PrefixListId` pl-c3aa4faa, `VpcCidr` 10.60.0.0/24, `PrivateSubnetCidr` 10.60.0.0/25, `ProjectName` proposal-orchestrator; `Changes` holds **exactly eight** entries, each `ResourceChange.Action` = `Add`, with these `LogicalResourceId` / `ResourceType` pairs and nothing else: `Vpc` AWS::EC2::VPC, `PrivateSubnet` AWS::EC2::Subnet, `PrivateRouteTable` AWS::EC2::RouteTable, `PrivateSubnetRouteTableAssociation` AWS::EC2::SubnetRouteTableAssociation, `HostSecurityGroup` AWS::EC2::SecurityGroup, `EndpointSecurityGroup` AWS::EC2::SecurityGroup, `HostToEndpointEgress` AWS::EC2::SecurityGroupEgress, `S3GatewayEndpoint` AWS::EC2::VPCEndpoint. No `AWS::EC2::Route`, no gateway, no EIP, no instance, nothing with an hourly cost. |

**Hand back here (end of round 1).** Report step 04 in session. Both of us read `R4_04_change-set.json`
against the criterion. Step 05 runs only after you have confirmed in session that the change set
lists exactly those eight resources. If the change set failed, the agent records the error verbatim
in `RUNLOG.md` and the successor decision is settled before the template changes; nothing is executed.

### Step 05 — Execute the change set (creates the stack; no hourly cost)

What it does: creates the eight resources the change set listed, waits for the stack, and saves the
stack status and the event list.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-network --change-set-name r4-create-01
"execute-change-set exit=$LASTEXITCODE" | Out-File -Encoding utf8 "$E\R4_05_execute-exit.txt"
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-network
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-network --query "Stacks[0].{name:StackName,status:StackStatus,reason:StackStatusReason,tags:Tags,created:CreationTime}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_05_stack-status.json"
aws cloudformation describe-stack-events --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-network --query "StackEvents[].{time:Timestamp,id:LogicalResourceId,type:ResourceType,status:ResourceStatus,reason:ResourceStatusReason}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_05_stack-events.json"
Get-Content "$E\R4_05_execute-exit.txt", "$E\R4_05_stack-status.json"; Get-Content "$E\R4_05_stack-events.json"
```

If `wait` reports a failure, still run the two `describe-*` lines, then **stop**. A failed creation
leaves the stack in `ROLLBACK_COMPLETE`; it is deleted, and the change set re-created, only after the
cause is agreed in session. Do not re-run step 05.

| Evidence file | PASS criterion |
|---|---|
| `R4_05_execute-exit.txt` | `execute-change-set exit=0` |
| `R4_05_stack-status.json` | `status` = `CREATE_COMPLETE`; `tags` = `[{project: proposal-orchestrator}]` |
| `R4_05_stack-events.json` | For each of the eight logical ids a `CREATE_COMPLETE` event and, for the stack itself, `CREATE_COMPLETE`; no status ending in `_FAILED`; no `ROLLBACK` |

### Step 06 — Save the stack outputs (ids for every later step and ticket)

What it does: writes the seven exported outputs to `R4_outputs.json`, the only file later steps and
tickets take ids from (OD6-r3-outputs).

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-network --query "Stacks[0].Outputs" --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_outputs.json"
Get-Content "$E\R4_outputs.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R4_outputs.json` | Seven entries; `OutputKey` set = {`VpcId`, `PrivateSubnetId`, `PrivateSubnetAz`, `PrivateRouteTableId`, `HostSecurityGroupId`, `EndpointSecurityGroupId`, `S3GatewayEndpointId`}; each `ExportName` = `proposal-orchestrator-network-<OutputKey>`; values start `vpc-`, `subnet-`, `eu-north-1a`, `rtb-`, `sg-`, `sg-`, `vpce-` |

### Step 07 — Read-only evidence of what was created (ids from `R4_outputs.json` only)

What it does: records the VPC, its DNS attributes, the absence of any Internet or NAT gateway, the
subnet, the route table, both security groups with their rules, the gateway endpoint with its policy,
and the stack's exports.

PowerShell (one block; the first lines load the ids):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
$O = Get-Content "$E\R4_outputs.json" -Raw | ConvertFrom-Json
$VPC = ($O | Where-Object OutputKey -eq VpcId).OutputValue
$SUB = ($O | Where-Object OutputKey -eq PrivateSubnetId).OutputValue
$RT = ($O | Where-Object OutputKey -eq PrivateRouteTableId).OutputValue
$HSG = ($O | Where-Object OutputKey -eq HostSecurityGroupId).OutputValue
$ESG = ($O | Where-Object OutputKey -eq EndpointSecurityGroupId).OutputValue
$VPCE = ($O | Where-Object OutputKey -eq S3GatewayEndpointId).OutputValue
"vpc=$VPC subnet=$SUB rt=$RT host-sg=$HSG endpoint-sg=$ESG vpce=$VPCE"
aws ec2 describe-vpcs --profile po-r1 --region eu-north-1 --vpc-ids $VPC --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_vpc.json"
aws ec2 describe-vpc-attribute --profile po-r1 --region eu-north-1 --vpc-id $VPC --attribute enableDnsSupport --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_vpc-dns-support.json"
aws ec2 describe-vpc-attribute --profile po-r1 --region eu-north-1 --vpc-id $VPC --attribute enableDnsHostnames --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_vpc-dns-hostnames.json"
aws ec2 describe-internet-gateways --profile po-r1 --region eu-north-1 --filters Name=attachment.vpc-id,Values=$VPC --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_internet-gateways.json"
aws ec2 describe-nat-gateways --profile po-r1 --region eu-north-1 --filter Name=vpc-id,Values=$VPC --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_nat-gateways.json"
aws ec2 describe-subnets --profile po-r1 --region eu-north-1 --subnet-ids $SUB --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_subnet.json"
aws ec2 describe-route-tables --profile po-r1 --region eu-north-1 --route-table-ids $RT --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_route-table.json"
aws ec2 describe-security-groups --profile po-r1 --region eu-north-1 --group-ids $HSG $ESG --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_security-groups.json"
aws ec2 describe-security-group-rules --profile po-r1 --region eu-north-1 --filters Name=group-id,Values=$HSG,$ESG --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_security-group-rules.json"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --vpc-endpoint-ids $VPCE --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_vpc-endpoint.json"
aws cloudformation list-exports --profile po-r1 --region eu-north-1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_07_exports.json"
Get-ChildItem "$E\R4_07_*" | Select-Object Name, Length
```

| Evidence file | PASS criterion |
|---|---|
| `R4_07_vpc.json` | One VPC, `VpcId` = the output; `CidrBlock` `10.60.0.0/24`; `State` `available`; `IsDefault` `false`; tags `Name` `proposal-orchestrator-vpc`, `project` `proposal-orchestrator`, plus the three `aws:cloudformation:*` tags |
| `R4_07_vpc-dns-support.json` | `EnableDnsSupport.Value` = `true` (PL-8) |
| `R4_07_vpc-dns-hostnames.json` | `EnableDnsHostnames.Value` = `true` (PL-8) |
| `R4_07_internet-gateways.json` | `InternetGateways` = `[]` (exit condition 2; OD3) |
| `R4_07_nat-gateways.json` | `NatGateways` = `[]` |
| `R4_07_subnet.json` | One subnet; `VpcId` the output; `CidrBlock` `10.60.0.0/25`; `AvailabilityZone` `eu-north-1a`; `MapPublicIpOnLaunch` `false`; `AssignIpv6AddressOnCreation` `false`; `State` `available` |
| `R4_07_route-table.json` | One route table; `VpcId` the output; `Associations` holds exactly one entry with `SubnetId` = the subnet output and `Main` `false`; `Routes` holds **exactly two** entries: `DestinationCidrBlock` `10.60.0.0/24` with `GatewayId` `local`, and `DestinationPrefixListId` `pl-c3aa4faa` with `GatewayId` = the endpoint output; no `igw-`, `nat-`, `eni-`, `pcx-` or `0.0.0.0/0` anywhere (exit condition 2; DC-06) |
| `R4_07_security-groups.json` | Two groups, both in the VPC. Host group: `IpPermissions` `[]`; `IpPermissionsEgress` holds two entries, both `tcp` 443–443: one with `PrefixListIds` `[pl-c3aa4faa]`, one with `UserIdGroupPairs` naming the endpoint group. Endpoint group: `IpPermissions` holds one entry, `tcp` 443–443, `UserIdGroupPairs` naming the host group; `IpPermissionsEgress` holds one entry, `IpProtocol` `-1`, `IpRanges` `[127.0.0.1/32]` with the placeholder description (R4-D1). Tags `Name` and `project` on both |
| `R4_07_security-group-rules.json` | Exactly four rules in total: host egress to the prefix list; host egress to the endpoint group; endpoint ingress from the host group; endpoint egress `127.0.0.1/32`. No rule has `0.0.0.0/0` or `::/0`; every rule but the placeholder is `tcp` 443 (DC-03, DC-07 halves) |
| `R4_07_vpc-endpoint.json` | One endpoint; `VpcEndpointType` `Gateway`; `ServiceName` `com.amazonaws.eu-north-1.s3`; `State` `available`; `RouteTableIds` = `[the route-table output]`; `PolicyDocument` (a JSON string) holds one statement: `Effect` Allow, `Principal` `*`, actions exactly `s3:GetObject`, `s3:ListBucket`, `s3:GetBucketLocation`, resources `arn:aws:s3:::proposal-orchestrator-deploy-797661577394` and `…/*`, condition `StringEquals` with `aws:ResourceAccount` and `aws:PrincipalAccount` both `797661577394`; no other bucket named (exit condition 3; F7; DC-05 S3 half) |
| `R4_07_exports.json` | `Exports` holds exactly seven entries, all `ExportingStackId` of this stack, names `proposal-orchestrator-network-<Key>` for the seven keys, values equal to `R4_outputs.json` |

### Step 08 — Empty the VPC's default security group (R4-D2; before, revoke, after)

What it does: the VPC came with a default security group CloudFormation cannot manage, holding an
all-traffic self-ingress rule and an all-traffic egress rule. The lasting rule R4-D2 says it carries
no rule. This step records it, revokes both rules by rule id, and records it again. Nothing is or
will be attached to it.

PowerShell (one block):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
$O = Get-Content "$E\R4_outputs.json" -Raw | ConvertFrom-Json
$VPC = ($O | Where-Object OutputKey -eq VpcId).OutputValue
$DSG = aws ec2 describe-security-groups --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC Name=group-name,Values=default --query "SecurityGroups[0].GroupId" --output text
"vpc=$VPC default-sg=$DSG"
aws ec2 describe-security-group-rules --profile po-r1 --region eu-north-1 --filters Name=group-id,Values=$DSG --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_08_default-sg-before.json"
Get-Content "$E\R4_08_default-sg-before.json"
$R = (Get-Content "$E\R4_08_default-sg-before.json" -Raw | ConvertFrom-Json).SecurityGroupRules
$EG = ($R | Where-Object IsEgress -eq $true).SecurityGroupRuleId
$IN = ($R | Where-Object IsEgress -eq $false).SecurityGroupRuleId
"egress rule ids: $EG"; "ingress rule ids: $IN"
aws ec2 revoke-security-group-egress --profile po-r1 --region eu-north-1 --group-id $DSG --security-group-rule-ids $EG --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_08_default-sg-revoke-egress.json"
aws ec2 revoke-security-group-ingress --profile po-r1 --region eu-north-1 --group-id $DSG --security-group-rule-ids $IN --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_08_default-sg-revoke-ingress.json"
aws ec2 describe-security-group-rules --profile po-r1 --region eu-north-1 --filters Name=group-id,Values=$DSG --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_08_default-sg-after.json"
aws ec2 describe-security-groups --profile po-r1 --region eu-north-1 --group-ids $DSG --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_08_default-sg.json"
Get-Content "$E\R4_08_default-sg-revoke-egress.json", "$E\R4_08_default-sg-revoke-ingress.json", "$E\R4_08_default-sg-after.json"
```

If `$DSG` is empty or does not start with `sg-`, or either rule-id list is empty, stop before the
`revoke-*` lines and report. The `revoke-*` commands act only on the default group of the new VPC,
by rule id; they touch no template-managed group.

| Evidence file | PASS criterion |
|---|---|
| `R4_08_default-sg-before.json` | `SecurityGroupRules` holds exactly two rules for one `GroupId` (the default group, not the host or endpoint output): one `IsEgress` `true` (`IpProtocol` `-1`, `CidrIpv4` `0.0.0.0/0`) and one `IsEgress` `false` (`IpProtocol` `-1`, `ReferencedGroupInfo.GroupId` = the same group) |
| `R4_08_default-sg-revoke-egress.json` | `Return` `true`; `RevokedSecurityGroupRules` names the egress rule id |
| `R4_08_default-sg-revoke-ingress.json` | `Return` `true`; `RevokedSecurityGroupRules` names the ingress rule id |
| `R4_08_default-sg-after.json` | `SecurityGroupRules` = `[]` (R4-D2) |
| `R4_08_default-sg.json` | One group, `GroupName` `default`, `VpcId` the output, `IpPermissions` `[]`, `IpPermissionsEgress` `[]` |

### Step 09 — Session-end credits (read-only)

What it does: confirms that R4 spent nothing.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R4_09_plan-state-after.json"
Get-Content "$E\R4_09_plan-state-after.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R4_09_plan-state-after.json` | `FREE`, `ACTIVE`; `accountPlanRemainingCredits.amount` equal to step 01's |

**Hand back here (end of round 2).** Report steps 05–09 in session. The agent reads every file against
the criteria above, writes `VERIFICATION.md`, updates register v2 (DC-03, DC-05, DC-06, DC-07, PL-8)
and the worklog, and tells you when to run step 10.

### Step 10 — Guards and secret scan over the finished folder (workstation only)

What it does: the E0 refusal check and the old-ID guard over the R4 evidence, `VERIFICATION.md`
included, before it is committed.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R4"
& { py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/R4; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R4_10_secret-scan.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R4_10_old-id-guard.txt"
Get-Content "$E\R4_10_secret-scan.txt", "$E\R4_10_old-id-guard.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R4_10_secret-scan.txt` | `CLEAN: docs/infrastructure_security/evidence_v2/R4`; `exit=0` |
| `R4_10_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |

## Outputs

`R4_outputs.json` (step 06) holds the seven exported ids. R5–R8 and R11 import them by export name;
R7, R11 and R12a read this file. Nobody copies an id from a console page or from memory.

## CloudShell fallback

Only if the workstation sign-in fails. Use the **eu-north-1** CloudShell, `mkdir -p ~/R4 && cd ~/R4`,
upload `deploy/aws/templates/10-network.yaml` and `deploy/aws/parameters/network.json` there, and
translate each PowerShell line as follows: drop `--profile po-r1`; replace
`2>&1 | Out-File -Encoding utf8 "$E\<file>"` with `> <file> 2>&1`; replace `file://deploy/aws/templates/`
and `file://deploy/aws/parameters/` with `file://`; write the variable lines as
`VPC=$(jq -r '.[] | select(.OutputKey=="VpcId") | .OutputValue' R4_outputs.json)` and the like, and
`$EG`/`$IN` as `jq -r '.SecurityGroupRules[] | select(.IsEgress==true) | .SecurityGroupRuleId'`
(`false` for ingress). Steps 03 and 10 run on the workstation only. Bring the files home by zip as in
R2 (`cd ~ && zip -r R4_evidence.zip R4`, download, `Expand-Archive`, copy into this folder).

## Before you hand back

- [ ] Every evidence file listed above exists in this folder, under exactly its name.
- [ ] You opened each file and checked that it holds no secret value, key or token.
- [ ] You reported each step in session (UTC time, any deviation, any error). The agent keeps
      `RUNLOG.md` from your reports.
