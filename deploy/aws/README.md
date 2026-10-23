# deploy/aws — CloudFormation for the private-network redeployment

Infrastructure as code for the hardened Bedrock environment in account `797661577394`, Region
`eu-north-1`. Layout decided in `docs/tier4_orchestration_state/decision_log/aws-redeployment-od6-stack-layout-r3_2026-10-22.json`
(successor to OD6). Tickets: `plans/aws_redeployment_tickets.md`. Evidence protocol:
`docs/infrastructure_security/evidence_v2/README.md`.

`deploy/` beside this folder holds the AN12 host install (`install_host.sh`, `offline_bundle.json`,
`requirements-host.txt`); this folder does not touch it.

## Stacks, in deploy order

| # | Stack | Template | Parameters | Filled by | Cost | Exports |
|---|---|---|---|---|---|---|
| 1 | `proposal-orchestrator-network` | `templates/10-network.yaml` | `parameters/network.json` | R4 | free | yes |
| 2 | `proposal-orchestrator-iam` | `templates/20-iam.yaml` | `parameters/iam.json` | R5 | free | yes |
| 3 | `proposal-orchestrator-kms` | `templates/30-kms.yaml` | `parameters/kms.json` | R6 | free (key: monthly) | yes |
| 4 | `proposal-orchestrator-audit` | `templates/40-audit.yaml` | `parameters/audit.json` | R7 | free (storage: usage) | yes |
| 5 | `proposal-orchestrator-secret` | `templates/50-secret.yaml` | `parameters/secret.json` | R8 | free (secret: monthly) | yes |
| 6 | `proposal-orchestrator-host` | `templates/90-host.yaml` | `parameters/host.json` | R11 | **hourly** | no |

Stacks 1–5 are the base: created once, in this order, and kept. Stack 6 holds the interface endpoints
and the host. It is created at the start of a working session and deleted at its end (OD5), each time
with the operator's explicit go. It imports from the base and exports nothing, so deleting it never
blocks the base.

"Free" means no hourly charge. The CMK and the secret have a small monthly charge and the buckets
and logs are billed by usage; all of it is paid from credits.

R3 wrote every template as a **skeleton**: parameters, the `DeployTarget` rule and one no-cost
`SkeletonPlaceholder` (`AWS::CloudFormation::WaitConditionHandle`). The ticket in "Filled by"
replaces the placeholder with the real resources and adds the outputs.

Filled so far: `10-network.yaml` (R4, `aws-redeployment-r4-network_2026-10-24`; its shape is pinned by
`tests/test_aws_network_template.py`).

## Rules every template keeps

Checked by `tools/aws_template_guard.py` (and `tests/test_aws_template_guard.py`):

- No Internet Gateway, egress-only gateway, NAT Gateway, Elastic IP or gateway attachment, and no
  `AWS::EC2::Route` at all: the S3 gateway endpoint adds the one prefix-list route itself (R4).
- No `0.0.0.0/0` or `::/0` anywhere: no such route and no such security-group rule.
- Every resource that takes tags carries `project` = `proposal-orchestrator`. The stack tag is set
  on every change set too.
- No "temporary" or "validation" in a logical id, name or description.
- No Region name except as a parameter default; no account id at all. Names and ARNs use
  `${AWS::Region}` and `${AWS::AccountId}`.
- Each template stays under 51,200 bytes, so `--template-body` works without a staging bucket.

No old-account id may appear anywhere in this folder. This is checked by `tools/old_id_guard.py`
(and `tests/test_old_id_guard.py`).

## Parameters

Each stack has a parameter file in the `create-change-set --parameters` format. Every value comes
from evidence or a decision record, and `tests/test_aws_iac_contract.py` checks each one against its
source:

| Parameter | Stacks | Source |
|---|---|---|
| `ExpectedAccountId` | all | `evidence_v2/R1/R1_00_caller-identity.json` |
| `ExpectedRegion` | all | `aws-redeployment-od1-region-r1_2026-10-21` |
| `InferenceProfileArns`, `FoundationModelArns` | iam, host | `aws-redeployment-od7-model-set_2026-10-21`, `OD7-resources` |
| `RoutedRegions` | iam | the Regions of those foundation-model ARNs |
| `AdminRoleArn` | kms, secret | `evidence_v2/R1/R1_00_role.json` `Role.Arn` (it includes the `/managed/` path) |
| `TransportModelId` | secret | OD7-orchestrator |
| `AvailabilityZone` | network | `evidence_v2/R3/R3_05_endpoint-services.json` (set once that file exists) |
| `S3PrefixListId` | network | `evidence_v2/R3/R3_06_s3-prefix-list.json` (set once that file exists) |

Parameters with defaults (`ProjectName`, `VpcCidr`, `PrivateSubnetCidr`, `InstanceType`,
`LatestAmiId`) are listed in the parameter file only to override them. To switch to the target
Opus model, change both model lists and `TransportModelId` and write a successor OD7 record.

## Outputs

`outputs_contract.json` names every output, its export (`proposal-orchestrator-<stack>-<OutputKey>`,
base stacks only) and the tickets that read it. After each create or update, save the outputs into
the ticket's evidence folder:

```powershell
aws cloudformation describe-stacks --profile po-r1 --region eu-north-1 --stack-name <stack> --query "Stacks[0].Outputs" --output json | Out-File -Encoding utf8 docs\infrastructure_security\evidence_v2\<ticket>\<ticket>_outputs.json
```

```bash
aws cloudformation describe-stacks --region eu-north-1 --stack-name <stack> --query 'Stacks[0].Outputs' --output json > <ticket>_outputs.json
```

Later step sheets and the R12a evidence collector take ids only from these files.

## Lint (workstation)

`cfn-lint` runs in its own virtual environment, which keeps its dependencies out of the `py -3.10`
test environment. One-time setup, from the repository root in PowerShell:

```powershell
py -3.10 -m venv .venv-lint
.\.venv-lint\Scripts\python.exe -m pip install -r deploy\aws\requirements-lint.txt
```

Each run:

```powershell
.\.venv-lint\Scripts\cfn-lint.exe --version
.\.venv-lint\Scripts\cfn-lint.exe --regions eu-north-1 -- deploy/aws/templates/*.yaml
py -3.10 -m tools.aws_template_guard deploy/aws/templates
py -3.10 -m tools.old_id_guard
py -3.10 -m pytest tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_old_id_guard.py
```

`cfn-lint` exits 0 when it finds nothing. A ticket's step sheet saves this output as evidence.

## Deploying a stack (R4 onwards; R3 creates nothing)

The operator runs every step and approves each change set. The `iam` stack also needs
`--capabilities CAPABILITY_NAMED_IAM`. The examples are for the network stack, from the repository
root. Start each session with the R1-D2 session check from the ticket's step sheet.

PowerShell:

```powershell
aws sts get-caller-identity --profile po-r1 --query Account --output text   # must print 797661577394
aws cloudformation create-change-set --profile po-r1 --region eu-north-1 `
  --stack-name proposal-orchestrator-network --change-set-name r4-create-01 --change-set-type CREATE `
  --template-body file://deploy/aws/templates/10-network.yaml `
  --parameters file://deploy/aws/parameters/network.json `
  --tags Key=project,Value=proposal-orchestrator --output json
aws cloudformation wait change-set-create-complete --profile po-r1 --region eu-north-1 `
  --stack-name proposal-orchestrator-network --change-set-name r4-create-01
aws cloudformation describe-change-set --profile po-r1 --region eu-north-1 `
  --stack-name proposal-orchestrator-network --change-set-name r4-create-01 --output json `
  | Out-File -Encoding utf8 docs\infrastructure_security\evidence_v2\R4\R4_NN_change-set.json
# Read the change set. Execute it only if it creates exactly what the step sheet lists.
aws cloudformation execute-change-set --profile po-r1 --region eu-north-1 `
  --stack-name proposal-orchestrator-network --change-set-name r4-create-01
aws cloudformation wait stack-create-complete --profile po-r1 --region eu-north-1 `
  --stack-name proposal-orchestrator-network
```

CloudShell (eu-north-1, after uploading the template and parameter file to `~/R4`):

```bash
aws sts get-caller-identity --query Account --output text   # must print 797661577394
aws cloudformation create-change-set --region eu-north-1 \
  --stack-name proposal-orchestrator-network --change-set-name r4-create-01 --change-set-type CREATE \
  --template-body file://10-network.yaml --parameters file://network.json \
  --tags Key=project,Value=proposal-orchestrator --output json
aws cloudformation wait change-set-create-complete --region eu-north-1 \
  --stack-name proposal-orchestrator-network --change-set-name r4-create-01
aws cloudformation describe-change-set --region eu-north-1 \
  --stack-name proposal-orchestrator-network --change-set-name r4-create-01 --output json > R4_NN_change-set.json
aws cloudformation execute-change-set --region eu-north-1 \
  --stack-name proposal-orchestrator-network --change-set-name r4-create-01
aws cloudformation wait stack-create-complete --region eu-north-1 --stack-name proposal-orchestrator-network
```

For an update, use `--change-set-type UPDATE` and `wait stack-update-complete`. The host stack is
deleted with `aws cloudformation delete-stack` and `wait stack-delete-complete` at the end of every
session. R14 scripts that cycle.
