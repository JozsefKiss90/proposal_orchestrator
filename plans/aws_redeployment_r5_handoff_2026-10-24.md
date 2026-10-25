# AWS redeployment: handoff for R5 (IAM stack — the hardened role is the runtime role)

| Field | Value |
|---|---|
| Date | 2026-10-24 |
| Branch at writing | `msca-dn-pre-eval` at `5819488` (`completed R4`). The "Close R4" commit — R4 ticked in the tickets file, `evidence_v2/R4/VERIFICATION.md` done conditions, RUNLOG step 10, the closing worklog entry, and this handoff — is the operator's to make if `git log` does not show it yet. |
| For | The agent that runs ticket R5 with the operator in a new session |
| Read first | `CLAUDE.md`; `plans/aws_redeployment_tickets.md` (inherited constraints at the top; R5; R6, R7, R8, R11, R12a, R12b for what consumes R5's outputs); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F1, F2, F7, §5 OD2, OD7, OD8, §6 R5, §7, §7a; `plans/aws_redeployment_r4_handoff_2026-10-23.md` §2 and §2 of this file; `docs/tier4_orchestration_state/decision_log/aws-redeployment-od7-model-set_2026-10-21.json` (`OD7-resources`, `OD7-global`); `aws-redeployment-od6-stack-layout-r3_2026-10-22.json`; `aws-redeployment-r4-network_2026-10-24.json` (R4-D3: what the endpoint policy already admits); `deploy/aws/README.md`; `docs/infrastructure_security/evidence_v2/R4/VERIFICATION.md` ("Notes for later tickets"); the v1 policy documents in `docs/infrastructure_security/evidence/02_iam/` (`boundary-policy.json`, `explicit-deny-policy.json`, `bedrock-invoke-policy.json`, `bedrock-role-trust-policy.json`) and `evidence/08_data_egress/flow_logs_*_policy.json` — **as history to be corrected, not as source** (they carry old ids and the `us.` prefix) |
| Decision records in force | `aws-redeployment-operator-decisions_2026-10-21` (R0: OD2 a, OD8 a, OD13), `aws-redeployment-od1-region-r1_2026-10-21`, `aws-redeployment-od11-admin-identity-r2_2026-10-21`, `aws-redeployment-r1-baseline-deviations_2026-10-21`, `aws-redeployment-od7-model-set_2026-10-21`, `aws-redeployment-od6-stack-layout-r3_2026-10-22`, `aws-redeployment-r4-network_2026-10-24` |
| Status | E0, R0, R1, R2, R3, **R4** done. Frontier: **R5**, R12a, R9, R9e, R10. R6 waits for R5; R7 for R4 (done) and R6; R8 for R5 and R6; R11 for R4–R8. |

## 1. Facts that govern R5

| Fact | Record / evidence |
|---|---|
| Account `797661577394`, Free plan, 199.99 USD credits after R4; everything regional in **eu-north-1**. IAM is global: every `aws iam` command runs without `--region`; the stack is still created in eu-north-1 (`DeployTarget` rule, `--region eu-north-1` on every `cloudformation` command). | OD1-r1; `evidence_v2/R4/R4_09_plan-state-after.json` |
| R5 fills **`proposal-orchestrator-iam`** (`deploy/aws/templates/20-iam.yaml`, parameters `deploy/aws/parameters/iam.json`, already complete: `ExpectedAccountId`, `ExpectedRegion`, `InferenceProfileArns` (2), `FoundationModelArns` (12), `RoutedRegions` (6)). The contract test checks all three lists against the OD7 record. | OD6-r3-parameters; `tests/test_aws_iac_contract.py::test_model_lists_equal_the_od7_record` |
| The seven outputs R5 must add, exports `proposal-orchestrator-iam-<Key>`: `RuntimeRoleName`, `RuntimeRoleArn`, `InstanceProfileName`, `InstanceProfileArn`, `PermissionBoundaryArn`, `ExplicitDenyPolicyArn`, `FlowLogsRoleArn`. R6 (key policy), R7 (flow logs, bucket policy), R8 (secret policy), R11 (instance profile, endpoint policy) import them. | `deploy/aws/outputs_contract.json` |
| **OD2 (a):** one host role, itself hardened — boundary and explicit deny attached, boundary extended for exactly the SSM actions the host needs, plus a narrow deploy-bucket read. No second role, no STS assume-role code. | R0 OD2; F1 |
| **OD7:** profiles `eu.anthropic.claude-opus-4-6-v1` and `eu.anthropic.claude-sonnet-4-6`; routed Regions eu-north-1, eu-west-3, eu-south-1, eu-south-2, eu-west-1, eu-central-1; **`global.` excluded and denied in R5's explicit deny** (OD7-global). The `us.` prefix of the v1 policies is wrong for this account. | OD7-resources, OD7-global; F2 |
| Deploy by change set, as in R4, **with `--capabilities CAPABILITY_NAMED_IAM`** (the role, profile and policy names are set). Stack tag `project=proposal-orchestrator`. The change set is read before execution. | OD6-r3-deploy; `deploy/aws/README.md` |
| **`DeployTarget` rule:** accepted by CloudFormation at change-set creation (R4, F-R4-3 Confirmed as accepted); keep it unchanged. | `evidence_v2/R4/VERIFICATION.md` step 04 |
| **Boundaries limit resource-based grants to a role ARN.** "Resource-based policies that grant permissions to an IAM role ARN are limited by an implicit deny in a permissions boundary or session policy." So R6's key policy and R8's secret policy, which name the runtime role, only work if the boundary allows `kms:Decrypt` / `kms:DescribeKey` and `secretsmanager:GetSecretValue`. (Grants to the role *session* ARN are not limited that way, but no later ticket should use that form.) | https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html, read 2026-10-24 |
| **`AWS::IAM::ManagedPolicy` and `AWS::IAM::InstanceProfile` take no `Tags`**; `AWS::IAM::Role` does. Both untaggable types must be added to `UNTAGGABLE_TYPES` in `tools/aws_template_guard.py` (reference pages read 2026-10-24; cite them in the decision record). `AWS::IAM::Policy` (inline) takes none either, but prefer managed policies: each then has an ARN the evidence can `get-policy-version` on. | CloudFormation reference, `aws-resource-iam-managedpolicy.html`, `aws-resource-iam-instanceprofile.html` |
| The S3 gateway endpoint already admits only read-only actions on `proposal-orchestrator-deploy-797661577394` for this account's principals (R4-D3). R5's deploy-bucket read is the second belt and must not be wider than that; R7's bucket policy is the third. | `aws-redeployment-r4-network_2026-10-24` R4-D3; `evidence_v2/R4/R4_07_vpc-endpoint.json` |
| No policy, role or profile may carry "temporary" or "validation" in its name or description (ticket R5 exit condition 4; template guard `forbidden-word`). The v1 account had `proposal-orchestrator-validation-*` policies; nothing of that kind may exist in this account. | `tools/aws_template_guard.py`; ticket R5 |
| Register v2 carries **no resource id** (E0 test `test_register_v2_carries_no_old_id` refuses any `vpc-/sg-/subnet-/rtb-/vpce-/i-/fl-` id). Role and policy ARNs are not matched by that regex, but keep the R4 habit: the register points at evidence paths and `R5_outputs.json` keys, not at ARNs. | `tests/test_evidence_protocol_scaffold.py` |
| Every template keeps the R3 rules: no account literal (use `${AWS::AccountId}`), no Region literal outside a parameter default (the twelve foundation-model ARNs come in through the parameter, never as literals), project tag on every taggable resource, ≤ 51,200 bytes. | `tools/aws_template_guard.py` |

## 2. How the operator works (additions from R4)

Everything in the R4 handoff §2 still holds (PowerShell in the VS Code terminal, repository root, `--profile po-r1`, `$E` at the top of every block, `Out-File -Encoding utf8`, `utf-8-sig` on read, `deactivate` before `py -3.10`). Measured in R4:

- **Sign in with `aws login --profile po-r1`**, never bare `aws login`: the bare form tries to overwrite the `default` profile (which points at a session of the old account's root; the operator correctly declined). Put the exact line in the step sheet's "Before you start".
- Pasted terminal output can wrap so that a space disappears (`--outputjson`, `-Encodingutf8` appeared in R4's paste; the files on disk were correct). Verify from the files in the folder, never from the paste.
- **The agent's device shell is a Linux VM with Python 3.10.12**; `pip install --user pytest pyyaml cfn-lint==1.57.2` works there (`$HOME/.local/bin/cfn-lint`), so the agent can lint, run the guards and the tests before handing over. It still cannot run `py -3.10` (that is the operator's evidence) and cannot `git commit`.
- Three rounds worked: (1) session check, identity, read-only lookups, lint/guards/tests, change set → hand back and read it together; (2) execute, outputs, read-only evidence, simulations, session-end credits → hand back, agent verifies; (3) scan and guard over the finished folder, tests, commit, confirm.
- The agent edits files in place with `device_bash` (heredoc or a short Python read-modify-write). A Python edit script must assert *before* it writes (R4 RUNLOG got duplicated rows once because the assertion came after `write_text`).
- Evidence files are UTF-8 with BOM; `git add .` warns about LF→CRLF on the agent's files — harmless, `.gitattributes` governs the byte-exact artifacts only.

## 3. R5 as it reads

Ticket exit conditions:

1. **IAM simulation allows invoke for each OD7 model and its routed foundation models.**
2. **IAM simulation denies admin actions, non-Claude models, `global.` profiles, and S3, EC2 and IAM actions outside the policy.**
3. **The boundary and explicit deny are attached to the role the instance profile uses. DC-09 to DC-13 are evidenced on that role.**
4. **No policy in the account carries "temporary" or "validation" in its name or description.**

What the template must hold (ticket R5, handoff §6 R5, F1, F2, OD2 a):

- **Runtime role** (`RoleName` `${ProjectName}-runtime-role`): trust policy `ec2.amazonaws.com` only (DC-13), `PermissionsBoundary` = the boundary policy (DC-12), `ManagedPolicyArns` = invoke, supporting-services, deploy-bucket-read, explicit deny; `Name` and `project` tags.
- **Instance profile** (`InstanceProfileName` `${ProjectName}-runtime-profile`) holding that one role (DC-09, DC-14 in R11).
- **Permission boundary** (managed policy): Allow exactly — `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` on the OD7 resources; `secretsmanager:GetSecretValue`; `kms:Decrypt`, `kms:DescribeKey`; `sts:GetCallerIdentity`; the SSM Agent's actions (taken from the current `AmazonSSMManagedInstanceCore` document, step 03 of the outline, not from memory); `s3:GetObject`, `s3:ListBucket`, `s3:GetBucketLocation` on the deploy bucket only. Nothing else.
- **Invoke policy** (DC-10, F2): Allow the two invoke actions on `!Ref InferenceProfileArns` + `!Ref FoundationModelArns` (the lists, never literals), Condition `aws:RequestedRegion` = `eu-north-1` (the request is always made to eu-north-1; the routed Regions appear as *resources*, not as requested Regions — this is the F2 lesson). DC-16's approved set is `RoutedRegions`; see §4 for where it goes.
- **Explicit deny** (DC-11, `DenyNonClaudeModels` reshaped for `eu.`): deny Bedrock administration (the v1 list, plus `bedrock:PutModelInvocationLoggingConfiguration` and `bedrock:DeleteModelInvocationLoggingConfiguration`, which stay in it); deny `iam:*`, `ec2:*`, `lambda:*`, `sqs:*`, `sns:*`, `dynamodb:*`; deny the two invoke actions with `NotResource` = `inference-profile/eu.anthropic.claude-*` and `foundation-model/anthropic.claude-*` (so `global.*`, `us.*` and application profiles are denied — OD7-global); deny S3 outside the deploy bucket (§4); deny invoke when `aws:RequestedRegion` ∉ `RoutedRegions` (§4).
- **Supporting-services policy**: `AmazonSSMManagedInstanceCore`'s actions (from step 03), `sts:GetCallerIdentity`, `secretsmanager:GetSecretValue` on `arn:${AWS::Partition}:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${ProjectName}/env-config-*` (the secret does not exist before R8; the pattern is enough). **No `kms:Decrypt` here**: R6's key policy grants it (ticket R6, "not through an IAM side grant"); the boundary allows it.
- **Deploy-bucket read**: the three read-only actions on `arn:${AWS::Partition}:s3:::${ProjectName}-deploy-${AWS::AccountId}` and its prefixes (§4), consistent with R4-D3.
- **Flow-logs role** (`${ProjectName}-flow-logs-role`): trust `vpc-flow-logs.amazonaws.com`; permissions `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogGroups`, `logs:DescribeLogStreams` on the flow-log group (§4 for its name). `FlowLogsRoleArn` output.
- Seven contract outputs with exports; `SkeletonPlaceholder` removed; `Metadata.Decision` unchanged (the contract test pins it to OD6-r3) and `Metadata.FillDecision` naming R5's record, as R4 did.

## 4. Points to settle with the operator before writing the template

- **Deploy-bucket prefixes.** The handoff speaks of "the runtime role's prefixes" but names none; the old guide put `orchestrator-deploy.tar.gz` at the bucket root, and the AN12 runbook uploads a tarball and its `.sha256` "as in deployment guide §4.3". Proposal: one prefix, `bundles/`, read-only for the runtime role (`ListBucket` with `s3:prefix` condition `bundles/*`, `GetObject` on `bundles/*`); R7's bucket policy and R15's runbook use the same prefix. The S3 gateway endpoint policy (R4-D3) stays as it is — it does not know prefixes and need not. Record as a lasting rule in R5's decision record so R7 and R15 inherit it.
- **How S3 appears in the explicit deny.** The v1 deny had `s3:*` on `*`, which would now block the deploy-bucket read. Options: (a) `Deny s3:*` with `NotResource` = the deploy bucket and `bundles/*` (everything else in S3 is explicitly denied; the Allow policy and the boundary then bound the rest); (b) drop S3 from the deny and rely on boundary + Allow. Proposal: (a) — ticket exit condition 2 asks for an explicit deny of "S3 … actions outside the policy", and (a) is what IAM simulation can show as `explicitDeny`.
- **DC-16, where the Region condition lives.** Proposal: the invoke policy allows only `aws:RequestedRegion` = `eu-north-1`, and the explicit deny adds `Deny bedrock:InvokeModel*` when `aws:RequestedRegion` `StringNotEquals` `!Ref RoutedRegions`. The second statement is the one DC-16's wording describes ("limits calls to the OD1 region and the regions the OD7 profiles route to"); the first is tighter and is what the host actually needs. R12b's DC-17 negative test (a call to an unapproved Region fails) then has an explicit deny to hit. Confirm, or keep a single statement.
- **The flow-log group name.** R5's flow-logs role and R6's key policy must scope to the log group R7 creates, so its name has to be fixed now. Proposal: `/${ProjectName}/vpc-flow-logs` (the v1 name, re-derived), ARN `arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/${ProjectName}/vpc-flow-logs:*`. R6 scopes CloudWatch Logs to the prefix `/${ProjectName}/`. Record as a lasting rule.
- **Names.** `${ProjectName}-runtime-role`, `${ProjectName}-runtime-profile`, `${ProjectName}-boundary`, `${ProjectName}-explicit-deny`, `${ProjectName}-bedrock-invoke`, `${ProjectName}-supporting-services`, `${ProjectName}-deploy-bucket-read`, `${ProjectName}-flow-logs-role`, all under `Path` `/`. Fixed names need `CAPABILITY_NAMED_IAM` and give stable ARNs for R6/R8/R11 and for the evidence commands. Alternative: let CloudFormation name them (no capability, ARNs only through outputs). Proposal: fixed names.
- **Does the boundary also need `kms:GenerateDataKey*`?** Only if the host writes encrypted objects; with a read-only bucket role it does not. Proposal: no. (`kms:Decrypt` is needed for Secrets Manager and for reading CMK-encrypted deploy objects; add `kms:ViaService` conditions for `secretsmanager.eu-north-1.amazonaws.com` and `s3.eu-north-1.amazonaws.com` only if the operator wants them — they would be Region literals, so they must be built with `${AWS::Region}`.)
- **Guard and tests.** (a) `UNTAGGABLE_TYPES` += `AWS::IAM::ManagedPolicy`, `AWS::IAM::InstanceProfile` (reference pages checked 2026-10-24; the decision record cites them). (b) A new `tests/test_aws_iam_template.py` in the R4 style: exactly the expected resources; the role's trust policy names `ec2.amazonaws.com` only; `PermissionsBoundary` set; the four managed policies attached; the invoke policy's resources are the two list parameters and nothing literal; the deny's `NotResource` carries the `eu.` prefix and no `us.`/`global.`; no statement grants `s3:PutObject`/`DeleteObject`; no `kms:Decrypt` in an Allow (only in the boundary); the flow-logs role trusts `vpc-flow-logs.amazonaws.com` only; outputs = contract. (c) Optionally extend the template guard with a `wildcard-grant` check (no `Action: "*"` / `Resource: "*"` in an Allow statement outside the boundary's `sts:GetCallerIdentity`/SSM lines) — cheap, but decide whether it is a guard rule or an R5 test.
- **Register v2.** Proposal: DC-10, DC-11, DC-12, DC-13 → `VERIFIED_PASS` (policy-level criteria, evidenced on the runtime role); DC-09 → `IN_PROGRESS` (the role and profile exist; "it is the role the host's instance profile uses" is shown when R11 launches the host, DC-14); DC-16 → `IN_PROGRESS` (condition in place; the negative test is R12b DC-17). DC-08 untouched (R7 uses the flow-logs role).

## 5. Step sheet outline (suggestion)

`evidence_v2/R5/STEPS.md` from `_templates/`, PowerShell first, three rounds. IAM is free; say so in the header and still read the change set.

1. Session-start check (R1-D2), credits ≥ 199.00; STOP rule.
2. Caller identity.
3. **Read-only lookups:** `aws iam get-policy --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore` and `get-policy-version` on its `DefaultVersionId` → `R5_03_ssm-core-policy.json`. The boundary's and the supporting-services policy's SSM actions are copied from this file (handoff §7a: from evidence, not memory). Also `aws iam list-policies --scope Local` → `R5_03_local-policies-before.json` (must be `[]`: nothing "temporary"/"validation" pre-exists) and `aws iam list-roles` → `R5_03_roles-before.json` (the admin role and AWS service-linked roles only).
   **Hand back here** so the agent can fill the SSM action list, then the agent delivers the template and the tests.
4. Lint, template guard, old-ID guard, tests (`test_aws_iac_contract`, `test_aws_template_guard`, `test_aws_network_template`, `test_aws_iam_template`, `test_old_id_guard`) → `R5_04_*`.
5. `create-change-set … --capabilities CAPABILITY_NAMED_IAM`, wait, describe → `R5_05_change-set.json`. Expected: `Add` entries for the role, the profile, four (or five) managed policies, the flow-logs role and its policy; `Capabilities` = `["CAPABILITY_NAMED_IAM"]`. **Hand back; both read it.**
6. Execute, wait, stack status and events → `R5_06_*`.
7. Outputs → `R5_outputs.json`.
8. **Read-only evidence, ARNs from `R5_outputs.json` only:** `get-role` (trust policy, `PermissionsBoundary`, tags) → DC-12, DC-13; `list-attached-role-policies`; `get-policy` + `get-policy-version` for each attached policy and the boundary → DC-10, DC-11; `get-instance-profile` (the one role) → DC-09; `list-policies --scope Local` → every local policy name and description free of "temporary"/"validation" (exit condition 4); the flow-logs role's `get-role` and policy.
9. **IAM simulation** (`aws iam simulate-principal-policy --policy-source-arn <RuntimeRoleArn>`), one file per case, with `--context-entries ContextKeyName=aws:RequestedRegion,ContextKeyValues=eu-north-1,ContextKeyType=string` where the condition matters:
   - allowed: `bedrock:InvokeModel` and `InvokeModelWithResponseStream` on each of the 2 profile ARNs and 12 foundation-model ARNs (from `iam.json`, which the test ties to OD7) → exit condition 1;
   - denied: `bedrock:PutModelInvocationLoggingConfiguration`; invoke on a `global.anthropic.claude-*` profile ARN and on a non-Claude foundation-model ARN **taken from R2's model listing** (R1 lesson: real ids, not placeholders); invoke with `aws:RequestedRegion` = `us-east-1`; `s3:PutObject` on the deploy bucket; `s3:GetObject` on `arn:aws:s3:::proposal-orchestrator-cloudtrail-797661577394/*` (an in-account bucket outside the policy); `ec2:DescribeInstances`; `iam:ListRoles` → exit condition 2. Each file's `EvalDecision` is the criterion (`allowed` / `explicitDeny` / `implicitDeny`); record which deny is expected where.
   - Note in the step sheet: `simulate-principal-policy` evaluates the role's attached boundary; confirm in the first allowed case that `PermissionsBoundaryDecisionDetail.AllowedByPermissionsBoundary` is `true`.
10. Session-end credits.
11. Scan and old-ID guard over the folder (round 3), tests, commit, confirm.

Register rows, `VERIFICATION.md` with "Notes for later tickets" (the role ARN for R6/R8/R11, the prefix and log-group rules), worklog entries, and the R6 handoff at close.

## 6. Files

| Path | What |
|---|---|
| `deploy/aws/templates/20-iam.yaml` | Filled: role, profile, boundary, explicit deny, invoke, supporting-services, deploy-bucket-read, flow-logs role + policy; Outputs with exports; `SkeletonPlaceholder` removed; `Metadata.FillDecision` |
| `deploy/aws/parameters/iam.json` | Unchanged (complete since R3) |
| `tools/aws_template_guard.py` | `UNTAGGABLE_TYPES` += `AWS::IAM::ManagedPolicy`, `AWS::IAM::InstanceProfile` (+ any §4 guard rule); `tests/test_aws_template_guard.py` fixture for each addition |
| `tests/test_aws_iam_template.py` | The R5 shape test |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r5-iam_2026-10-24.json` | The §4 answers; lasting rules: deploy-bucket prefix, flow-log group name |
| `docs/infrastructure_security/evidence_v2/R5/` | `STEPS.md`, `RUNLOG.md`, `R5_<NN>_<name>`, `R5_outputs.json`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_control_register_v2.md` | DC-09 to DC-13, DC-16 |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | One entry per R5 milestone |
| `deploy/aws/README.md` | "Filled so far" line; any new guard rule |

## 7. Done for R5

Every `VERIFICATION.md` criterion PASS (or N/A with reason); the R3, R4 and R5 tests pass with `py -3.10`; the template guard and the old-ID guard are CLEAN; the secret scan of `evidence_v2/R5` is CLEAN; register v2 rows updated; worklog entries; the operator commits and confirms in session. Then tick R5 in `plans/aws_redeployment_tickets.md`. R6 then opens (it imports `RuntimeRoleArn`); R8 waits for R6; R11 for R6–R8.
