# R5 — follow-up step sheet 1: simulation with the Region context, and a clean step-11 test log

| Field | Value |
|---|---|
| Ticket | `R5` in `plans/aws_redeployment_tickets.md` |
| Follows | `STEPS.md` steps 09 and 11 (round 2, run 2026-10-25) |
| Written by / on | agent (Claude) / 2026-10-25 |
| Account / region | `797661577394` / `eu-north-1` (IAM global, no `--region`) |
| IDs taken from | `R5_outputs.json`; model ARNs from `deploy/aws/parameters/iam.json` |
| Hourly cost created | **none** (read-only simulation and local tests) |

## Why this sheet exists (two step-sheet errors, both the agent's)

1. **Step 09: seven cases carried no `aws:RequestedRegion` context.** `simulate-principal-policy` also
   evaluates the organization's service control policies (`OrganizationsDecisionDetail`). Without the
   context it evaluates the request as made in the IAM endpoint's Region, us-east-1, where the AWS-managed
   SCP denies every regional action (F-OD1r1-1). So in `R5_09_allow-s3-get-bundle`, `-allow-s3-list-bundles`,
   `-allow-secret`, `-allow-sts-ssm` (the three SSM actions), `-deny-ec2`, `-deny-s3-other-bucket` and
   `-deny-s3-put-bundle` the decision came from the SCP (`AllowedByOrganizations` false, no matched
   statement of ours), not from the runtime role's policies. Those seven files stay in the folder as
   history and are **superseded** by the step 12 files below; they prove nothing about R5. The other 21
   step 09 files carried the context and are unaffected (`AllowedByOrganizations` true in each).
   The criteria are tightened: every result must show `AllowedByOrganizations` = `true`, and every
   `explicitDeny` must name `proposal-orchestrator-explicit-deny` among its `MatchedStatements`.
2. **Step 11: the test log tripped the secret scan.** The step ran the scaffold tests with pytest's
   verbose ids, whose parametrised names spell out the four forbidden patterns; the log, written
   into the scanned folder while the run was going, then failed `test_evidence_v2_tree_is_itself_clean`
   and makes a fresh secret scan of the folder REFUSE. Nothing secret is in it (agent read lines 150–190).
   Step 13 re-collects it with `-q` (no test ids in the output) and runs the scan **after** the tests.
   *Correction 2026-10-25 (agent):* the first version of this paragraph quoted one of the pattern names
   itself, so this sheet tripped the scan on the first run of step 13 and the failing test printed the
   finding into the log. The quotation is removed; step 13 is run again unchanged.

## Steps

### Step 12 — Re-simulate the seven cases with `aws:RequestedRegion` = eu-north-1 (read-only)

PowerShell (one block):

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
$O = Get-Content "$E\R5_outputs.json" -Raw | ConvertFrom-Json
$RARN = ($O | Where-Object OutputKey -eq 'RuntimeRoleArn').OutputValue
function Ctx([string]$k, [string]$v) { "ContextKeyName=$k,ContextKeyValues=$v,ContextKeyType=string" }
function Sim([string]$Name, [string[]]$Actions, [string[]]$Resources, [string[]]$Context) {
  $a = @('iam', 'simulate-principal-policy', '--profile', 'po-r1', '--policy-source-arn', $RARN, '--action-names') + $Actions + @('--resource-arns') + $Resources
  if ($Context) { $a += @('--context-entries') + $Context }
  $a += @('--output', 'json')
  & aws @a 2>&1 | Out-File -Encoding utf8 "$E\R5_12_$Name.json"
}
$R = Ctx 'aws:RequestedRegion' 'eu-north-1'
Sim 'allow-s3-get-bundle' @('s3:GetObject') @('arn:aws:s3:::proposal-orchestrator-deploy-797661577394/bundles/orchestrator.tar.gz') @($R)
Sim 'allow-s3-list-bundles' @('s3:ListBucket') @('arn:aws:s3:::proposal-orchestrator-deploy-797661577394') @($R, (Ctx 's3:prefix' 'bundles/'))
Sim 'allow-secret' @('secretsmanager:GetSecretValue') @('arn:aws:secretsmanager:eu-north-1:797661577394:secret:proposal-orchestrator/env-config-AbCdEf') @($R)
Sim 'allow-sts-ssm' @('sts:GetCallerIdentity', 'ssm:UpdateInstanceInformation', 'ssmmessages:OpenControlChannel', 'ec2messages:GetMessages') @('*') @($R)
Sim 'deny-s3-list-outside-bundles' @('s3:ListBucket') @('arn:aws:s3:::proposal-orchestrator-deploy-797661577394') @($R, (Ctx 's3:prefix' 'other/'))
Sim 'deny-s3-put-bundle' @('s3:PutObject', 's3:DeleteObject') @('arn:aws:s3:::proposal-orchestrator-deploy-797661577394/bundles/orchestrator.tar.gz') @($R)
Sim 'deny-s3-other-bucket' @('s3:GetObject', 's3:PutObject') @('arn:aws:s3:::proposal-orchestrator-cloudtrail-797661577394/x') @($R)
Sim 'deny-ec2' @('ec2:DescribeInstances', 'ec2:RunInstances') @('*') @($R)
Get-ChildItem "$E\R5_12_*" | Select-Object Name, Length
```

Eight files: the seven cases again, plus one new case (`deny-s3-list-outside-bundles`) that shows the
`s3:prefix` condition of R5-D1 refusing a listing outside `bundles/`.

| Evidence file | Expected `EvalDecision` (every action) | Also required in every result |
|---|---|---|
| `R5_12_allow-s3-get-bundle.json`, `R5_12_allow-s3-list-bundles.json` | `allowed` (matched: `proposal-orchestrator-deploy-bucket-read`) | `OrganizationsDecisionDetail.AllowedByOrganizations` = `true`; `PermissionsBoundaryDecisionDetail.AllowedByPermissionsBoundary` = `true` |
| `R5_12_allow-secret.json`, `R5_12_allow-sts-ssm.json` | `allowed` (matched: `proposal-orchestrator-supporting-services`) | as above |
| `R5_12_deny-s3-list-outside-bundles.json` | `implicitDeny` | `AllowedByOrganizations` = `true` |
| `R5_12_deny-s3-put-bundle.json` | `implicitDeny` (R5-D2: no write is granted; the object lies inside the deny's `NotResource`) | `AllowedByOrganizations` = `true` |
| `R5_12_deny-s3-other-bucket.json` | `explicitDeny`, matched `proposal-orchestrator-explicit-deny` | `AllowedByOrganizations` = `true` |
| `R5_12_deny-ec2.json` | `explicitDeny`, matched `proposal-orchestrator-explicit-deny` | `AllowedByOrganizations` = `true` |

**STOP rule.** None; a different decision is a FAIL for the agent to report.

### Step 13 — Round 3 again: tests (quiet), then the secret scan and the old-ID guard

*Revised 2026-10-25 after its first run (agent):* a refused scan writes the pattern names into its own
output file, which then poisons the next run. So the step first **removes the two refused files**
(`R5_11_pytest.txt`, `R5_11_secret-scan.txt`; re-collection, as the scan's REFUSED message asks — no
file is edited), then runs the tests, and only then the scan.

PowerShell:

```powershell
$E = "docs\infrastructure_security\evidence_v2\R5"
Remove-Item "$E\R5_11_pytest.txt", "$E\R5_11_secret-scan.txt"
py -3.10 -m pytest -q tests/test_aws_iac_contract.py tests/test_aws_template_guard.py tests/test_aws_network_template.py tests/test_aws_iam_template.py tests/test_old_id_guard.py tests/test_evidence_protocol_scaffold.py 2>&1 | Out-File -Encoding utf8 "$E\R5_11_pytest.txt"
& { py -3.10 -m tools.evidence_secret_scan $E; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_11_secret-scan.txt"
& { py -3.10 -m tools.old_id_guard; "exit=$LASTEXITCODE" } 2>&1 | Out-File -Encoding utf8 "$E\R5_11_old-id-guard.txt"
Get-Content "$E\R5_11_pytest.txt" -Tail 3; Get-Content "$E\R5_11_secret-scan.txt", "$E\R5_11_old-id-guard.txt"
```

| Evidence file | PASS criterion |
|---|---|
| `R5_11_pytest.txt` | Per-file dot lines only (no test ids); last line `168 passed`, no `failed`; none of the four forbidden patterns in the file |
| `R5_11_secret-scan.txt` | `CLEAN: docs/infrastructure_security/evidence_v2/R5`; `exit=0` |
| `R5_11_old-id-guard.txt` | `CLEAN: …`; `exit=0` |

**Hand back.** The agent verifies, writes `VERIFICATION.md`, the register rows and the worklog entry;
then you commit and confirm R5 in session.
