# R11 — fix 1: the host size the Free plan admits

| Field | Value |
|---|---|
| Ticket | `R11` in `plans/aws_redeployment_tickets.md` |
| Fixes | `STEPS.md` step 06, run 1 (2026-11-11 20:12–20:19 UTC): `Host` `CREATE_FAILED`, "The specified instance type is not eligible for Free Tier"; stack `ROLLBACK_COMPLETE` (`RUNLOG.md`) |
| Decisions applied | OD9-r1 (`aws-redeployment-od9-host-size-r1_2026-11-11`): `c7i-flex.large`, CPU credits only on a t3 type; OD10 Free plan, no upgrade; every decision `STEPS.md` applies |
| Template change | `deploy/aws/templates/90-host.yaml`: `InstanceType` default `c7i-flex.large`, allowed `c7i-flex.large` and `t3.micro`; condition `IsBurstable` sets `CreditSpecification` only for a t3 type |
| Written by / on | agent (Claude) / 2026-11-11 |
| Hourly cost created | **None in this sheet.** F01–F05 are read-only, a deletion, workstation checks and an unexecuted change set. Hourly charges start again only at step 06, after your explicit go |

## Before you start

- **Merge the fix branch first:** `git merge --no-ff aws/r11-fix1-instance-type`. Steps F04 and F05 read
  the merged template.
- Everything under "Before you start" in `STEPS.md` applies: sign in with `aws login --profile po-r1`;
  PowerShell in the repository root; `$E` set in every new window; `Out-File -Encoding utf8`, never `>`;
  `deactivate` before any `py -3.10` command if `.venv-lint` is active.
- This sheet gives PowerShell only.
- **Run each block once.** Executing a change set consumes it; a second run of the same block answers
  `ChangeSetNotFound` and overwrites the first run's file (step 06, run 2).
- If a step fails, stop and report it in session. Do not improvise a fix.

## Steps

### Step F01 — Session-start check and identity (R1-D2)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
aws freetier get-account-plan-state --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_01_plan-state.json"
aws budgets describe-budgets --profile po-r1 --account-id 797661577394 --query "Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_01_budgets.json"
aws budgets describe-notifications-for-budget --profile po-r1 --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query "Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_01_budget-notifications.json"
aws sts get-caller-identity --profile po-r1 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_01_caller-identity.json"
Get-Content "$E\R11_fix1_01_*"
```

| Evidence file | PASS criterion |
|---|---|
| `R11_fix1_01_plan-state.json` | `FREE`, `ACTIVE`; credits ≥ `195.00`; expiry starts `2027-04-19` |
| `R11_fix1_01_budgets.json` | One budget, `My Monthly Cost Budget`, `limit` `10.0`, `spend` < `8.5` |
| `R11_fix1_01_budget-notifications.json` | Three notifications, each `OK` |
| `R11_fix1_01_caller-identity.json` | `Account` `797661577394`; `Arn` starts `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

**STOP rule.** As `STEPS.md` steps 01 and 02.

### Step F02 — Delete the rolled-back stack

What it does: removes `proposal-orchestrator-host` in `ROLLBACK_COMPLETE`. It holds no resource, but a
stack of that name blocks a new `CREATE` change set. Then it confirms the VPC is back to the state of
step 03.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$VPC = O "$V2\R4\R4_outputs.json" VpcId
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --query "Stacks[0].{name:StackName,status:StackStatus}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_02_stack-before.json"
& { aws cloudformation delete-stack --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host; "delete exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_02_delete-exit.txt"
aws cloudformation wait stack-delete-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host
& { aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --output json; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_02_stack-after.txt"
aws ec2 describe-vpc-endpoints --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "VpcEndpoints[].{id:VpcEndpointId,type:VpcEndpointType,service:ServiceName,state:State}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_02_vpc-endpoints.json"
aws ec2 describe-network-interfaces --profile po-r1 --region eu-north-1 --filters Name=vpc-id,Values=$VPC --query "NetworkInterfaces[].{id:NetworkInterfaceId,type:InterfaceType,desc:Description}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_02_network-interfaces.json"
aws ec2 describe-instances --profile po-r1 --region eu-north-1 --filters Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down --query "Reservations[].Instances[].{id:InstanceId,state:State.Name,type:InstanceType}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_02_instances.json"
Get-ChildItem "$E\R11_fix1_02_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R11_fix1_02_stack-before.json` | `status` `ROLLBACK_COMPLETE` |
| `R11_fix1_02_delete-exit.txt` | `delete exit=0` and no error line |
| `R11_fix1_02_stack-after.txt` | Contains `ValidationError` and `does not exist`; last line `exit=254` |
| `R11_fix1_02_vpc-endpoints.json` | Exactly one entry: `S3GatewayEndpointId` of `R4_outputs.json`, `Gateway`, `available` |
| `R11_fix1_02_network-interfaces.json` | `[]` |
| `R11_fix1_02_instances.json` | `[]` |

**STOP rule.** If the deletion fails or anything other than the S3 gateway endpoint remains in the VPC,
stop and report it.

### Step F03 — Which types the Free plan admits here (read-only)

What it does:

- **F03a** lists the Free Tier eligible instance types in eu-north-1, with architecture, size and
  whether each is burstable. This list, not a dry run, answers eligibility (OD9-r1, F-OD9r1-2).
- **F03b** checks that `c7i-flex.large` and `t3.micro` are offered in the private subnet's zone.
- **F03c** dry-runs the host launch as the template now builds it: `c7i-flex.large`, no credit option.
- **F03d** dry-runs the same launch with `CpuCredits=standard`. This records how EC2 treats the credit
  option on a non-burstable type. It decides nothing: the template omits the option for that type.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"; $V2 = "docs\infrastructure_security\evidence_v2"
function O($f, $k) { ((Get-Content $f -Raw | ConvertFrom-Json) | Where-Object OutputKey -eq $k).OutputValue }
$SUB = O "$V2\R4\R4_outputs.json" PrivateSubnetId
$AZ  = O "$V2\R4\R4_outputs.json" PrivateSubnetAz
$HSG = O "$V2\R4\R4_outputs.json" HostSecurityGroupId
$IPN = O "$V2\R5\R5_outputs.json" InstanceProfileName
$AMI = aws ssm get-parameters --profile po-r1 --region eu-north-1 --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 --query "Parameters[0].Value" --output text
"SUB=$SUB AZ=$AZ HSG=$HSG IPN=$IPN AMI=$AMI"
# F03a
aws ec2 describe-instance-types --profile po-r1 --region eu-north-1 --filters Name=free-tier-eligible,Values=true --query "InstanceTypes[].{type:InstanceType,arch:ProcessorInfo.SupportedArchitectures,vcpu:VCpuInfo.DefaultVCpus,memMiB:MemoryInfo.SizeInMiB,burstable:BurstablePerformanceSupported}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_03_free-tier-types.json"
# F03b
aws ec2 describe-instance-type-offerings --profile po-r1 --region eu-north-1 --location-type availability-zone --filters Name=location,Values=$AZ Name=instance-type,Values=c7i-flex.large,t3.micro --query "InstanceTypeOfferings[].{type:InstanceType,az:Location}" --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_03_offerings.json"
# F03c — dry run: nothing is created
& { aws ec2 run-instances --dry-run --profile po-r1 --region eu-north-1 --image-id $AMI --instance-type c7i-flex.large --iam-instance-profile Name=$IPN --network-interfaces "DeviceIndex=0,SubnetId=$SUB,Groups=$HSG,AssociatePublicIpAddress=false,DeleteOnTermination=true" --metadata-options "HttpEndpoint=enabled,HttpTokens=required,HttpPutResponseHopLimit=1" --block-device-mappings "DeviceName=/dev/xvda,Ebs={VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}"; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_03_dry-run.txt"
# F03d — dry run with the credit option: nothing is created
& { aws ec2 run-instances --dry-run --profile po-r1 --region eu-north-1 --image-id $AMI --instance-type c7i-flex.large --iam-instance-profile Name=$IPN --network-interfaces "DeviceIndex=0,SubnetId=$SUB,Groups=$HSG,AssociatePublicIpAddress=false,DeleteOnTermination=true" --metadata-options "HttpEndpoint=enabled,HttpTokens=required,HttpPutResponseHopLimit=1" --block-device-mappings "DeviceName=/dev/xvda,Ebs={VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}" --credit-specification CpuCredits=standard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_03_dry-run-credits.txt"
Get-ChildItem "$E\R11_fix1_03_*" | ForEach-Object { "== $($_.Name)"; Get-Content $_.FullName }
```

| Evidence file | PASS criterion |
|---|---|
| `R11_fix1_03_free-tier-types.json` | Contains `c7i-flex.large` with `arch` [`x86_64`] and `burstable` false; also `t3.micro`. Contains no `t3.medium` (step 06 run 1). The agent records each listed type's vCPU and memory |
| `R11_fix1_03_offerings.json` | Two entries, `c7i-flex.large` and `t3.micro`, each with `az` = `PrivateSubnetAz` of `R4_outputs.json` |
| `R11_fix1_03_dry-run.txt` | Contains `DryRunOperation` (`Request would have succeeded`); last line `exit=254` |
| `R11_fix1_03_dry-run-credits.txt` | No criterion. Recorded for OD9-r1 (F-OD9r1-3): either `DryRunOperation` or an error naming the credit option |

**STOP rule.** If `c7i-flex.large` is missing from F03a or F03b, or F03c answers anything other than
`DryRunOperation`, stop. The operator chooses again among the listed types (OD9-r1 known gap); the
template's `AllowedValues` then change in a fix 2.

### Step F04 — Lint, guards and tests on the merged template (workstation only)

Run `deactivate` first if `.venv-lint` is active.

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
& { .\.venv-lint\Scripts\cfn-lint.exe --version; .\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml; "cfn-lint exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_04_cfn-lint.txt"
& { py -3.10 -m tools.aws_template_guard deploy/aws/templates; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_04_template-guard.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_04_old-id-guard.txt"
& { py -3.10 --version; py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_aws_kms_template.py tests/test_aws_audit_template.py tests/test_aws_env_config_template.py tests/test_aws_host_template.py tests/test_old_id_guard.py tests/test_host_env_launcher.py } 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_04_pytest.txt"
Get-Content "$E\R11_fix1_04_cfn-lint.txt", "$E\R11_fix1_04_template-guard.txt", "$E\R11_fix1_04_old-id-guard.txt"; Get-Content "$E\R11_fix1_04_pytest.txt" -Tail 3
```

| Evidence file | PASS criterion |
|---|---|
| `R11_fix1_04_cfn-lint.txt` | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; no line between them |
| `R11_fix1_04_template-guard.txt` | `CLEAN: 6 template(s): …`; `exit=0` |
| `R11_fix1_04_old-id-guard.txt` | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| `R11_fix1_04_pytest.txt` | First line `Python 3.10.…`; last line `260 passed` (one more than step 04: the credit-condition test) with no `failed`, `error` or `skipped` |

**STOP rule.** Any non-zero exit or failed test: stop.

### Step F05 — Create the change set and save it for review (nothing is created yet)

```powershell
$E = "docs\infrastructure_security\evidence_v2\R11"
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-fix1-create-01 --change-set-type CREATE --template-body file://deploy/aws/templates/90-host.yaml --parameters file://deploy/aws/parameters/host.json --tags Key=project,Value=proposal-orchestrator --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_05_create-change-set.json"
Get-Content "$E\R11_fix1_05_create-change-set.json"
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-fix1-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 --stack-name proposal-orchestrator-host --change-set-name r11-fix1-create-01 --output json 2>&1 | Out-File -Encoding utf8 "$E\R11_fix1_05_change-set.json"
Get-Content "$E\R11_fix1_05_change-set.json"
```

| Evidence file | PASS criterion |
|---|---|
| `R11_fix1_05_create-change-set.json` | `Id` contains `changeSet/r11-fix1-create-01/`; `StackId` contains `stack/proposal-orchestrator-host/` |
| `R11_fix1_05_change-set.json` | As `STEPS.md` step 05, except `InstanceType` = `c7i-flex.large`: `CREATE_COMPLETE`, `AVAILABLE`, no capabilities, tag `project`; the other parameters equal `host.json` or the template defaults; `LatestAmiId` resolves to the F03 image; exactly seven `Add` changes (six endpoints and `Host`) |

**STOP — hand back here.** Step 06 runs only after your explicit go in session on
`R11_fix1_05_change-set.json`. The agent records the go, with its UTC time and your words, in
`RUNLOG.md` before you run step 06.

## After the go: `STEPS.md` steps 06–23 with these amendments

| `STEPS.md` step | Amendment |
|---|---|
| Header, hourly cost | The instance is `c7i-flex.large` (per instance-hour). It has no CPU credits, so no surplus-credit charge applies |
| 06 | Use `--change-set-name r11-fix1-create-01`. Write `R11_fix1_06_execute-exit.txt`, `R11_fix1_06_stack-status.json` and `R11_fix1_06_stack-events.json`, so run 1's files stay as evidence. Run the block **once** |
| 09 | `R11_09_instance.json`: `type` `c7i-flex.large`. `R11_09_credit-specification.json`: no criterion; recorded for OD9-r1 (a c7i-flex instance has no CPU credit option). Every other criterion stands |
| 13 | Unchanged |
| 14 | `R11_14_imports-after.txt` (corrected 2026-11-11 after the run; the sheet's criterion was the agent's error): no import list names `proposal-orchestrator-host`. `network-VpcId` stays imported by `proposal-orchestrator-audit` (the flow log, `40-audit.yaml`) and `iam-RuntimeRoleArn` by `-kms`, `-audit` and `-secret` (key, bucket and secret policies), each `exit=0`. The other four exports: `ValidationError`, not imported by any stack, `exit=254`. Every other criterion stands |
| 15, 17 | Unchanged (`r11-create-02`). The recreation reads the merged template, so it builds `c7i-flex.large` |
| 18 | `R11_18_instance.json`: `type` `c7i-flex.large` |
| All others | Unchanged |

## Outputs

`R11_fix1_01_*` to `R11_fix1_05_*`, then the files of `STEPS.md` steps 06–23 as amended above. The agent
adds each round to `RUNLOG.md`. `VERIFICATION.md` follows step 22, as `STEPS.md` round 4 states.
