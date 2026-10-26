# R5 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-25 (round 1 read ~14:30 UTC; round 1b ~14:45 UTC, before execution; round 2 ~21:45 UTC; `STEPS_fix1.md` ~21:50 UTC) |
| Step sheets | `STEPS.md` (steps 01–11) and `STEPS_fix1.md` (steps 12–13), run as in `RUNLOG.md` |
| Secret scan | Operator: `STEPS_fix1.md` step 13, `R5_11_secret-scan.txt` → `CLEAN`, `exit=0`, run after the tests. Agent re-run over the whole `evidence_v2` tree → `CLEAN`. |
| Old-ID guard | Operator: `R5_11_old-id-guard.txt` → `CLEAN` (20 ids). Agent re-run over the default v2 scope (this report included) → `CLEAN`. |
| Stack | `proposal-orchestrator-iam` (change set `r5-create-01`, created 2026-10-25T14:42:58Z, executed after the operator's go), `CREATE_COMPLETE`. Nothing with an hourly cost. Credits 199.99 USD before and after. |

Every check below was re-run by the agent on the saved files (`utf-8-sig`) in the device shell, by
script, not taken from the pasted terminal output. Policy documents were compared statement by
statement with `20-iam.yaml` after filling in `iam.json` and the pseudo parameters.

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01 | `FREE`, `ACTIVE`, credits ≥ 199.00, expiration 2027-04-19 | `R5_01_plan-state.json` | PASS | FREE, ACTIVE, 199.99 USD |
| 01 | One budget, limit 10.0, spend < 8.5 | `R5_01_budgets.json` | PASS | `My Monthly Cost Budget`, 10.0, spend 0.006 |
| 01 | Three notifications, each `OK` | `R5_01_budget-notifications.json` | PASS | ACTUAL 100, ACTUAL 85, FORECASTED 100, all `OK` |
| 02 | Account 797661577394, `AccountFullAccessRole` | `R5_02_caller-identity.json` | PASS | As required |
| 03a | `AmazonSSMManagedInstanceCore`, default version present | `R5_03_ssm-core-policy-meta.json` | PASS | `DefaultVersionId` `v2` (updated 2019-05-23) |
| 03a | Default version document, ssm / ssmmessages / ec2messages actions | `R5_03_ssm-core-policy.json` | PASS | `v2`, `IsDefaultVersion` true; 15 + 4 + 6 = 25 actions on `*` (F-R5-1); copied verbatim, `tests/test_aws_iam_template.py` compares both copies with this file |
| 03b | No customer-managed policy | `R5_03_local-policies-before.json` | PASS | `[]` |
| 03b | No `proposal-orchestrator` / temporary / validation role | `R5_03_roles-before.json` | PASS | 13 roles: three AWS-managed under `/managed/`, ten service-linked (F-R5-4). The two `/managed/` roles besides `AccountFullAccessRole` were reported in session; AWS-managed, created with the account |
| 03b | No instance profile | `R5_03_instance-profiles-before.json` | PASS | `[]` |
| 03c | ≥ 1 non-Anthropic model ARN in eu-north-1 | `R5_03_non-claude-models.json` | PASS | Seven Amazon models; `amazon.nova-pro-v1:0` used in step 09 |
| 03d | Stack does not exist; `exit=254` (criterion corrected, F-R5-5) | `R5_03_iam-stack-before.txt` | PASS | `ValidationError … does not exist`, `exit=254` |
| 04 | cfn-lint 1.57.2, exit 0 | `R5_04_cfn-lint.txt` | PASS | Two lines exactly |
| 04 | Template guard `CLEAN: 6`, old-ID guard `CLEAN` | `R5_04_template-guard.txt`, `R5_04_old-id-guard.txt` | PASS | As required |
| 04 | Python 3.10, `146 passed` | `R5_04_pytest.txt` | PASS | Python 3.10.6, `146 passed` |
| 05 | `Id` / `StackId` ARNs | `R5_05_create-change-set.json` | PASS | eu-north-1, 797661577394, `r5-create-01`, `proposal-orchestrator-iam` |
| 05 | `CREATE_COMPLETE` / `AVAILABLE`; `CAPABILITY_NAMED_IAM`; tag; parameters; **exactly nine** `Add` (criterion corrected: no `ChangeSetType` field) | `R5_05_change-set.json` | PASS | Change map and parameters equal the expected ones by script. Operator gave the go in session before step 06 |
| 06 | `execute exit=0` | `R5_06_execute-exit.txt` | PASS | As required |
| 06 | `CREATE_COMPLETE`, capability, tag | `R5_06_stack-status.json` | PASS | As required |
| 06 | Nine ids and the stack `CREATE_COMPLETE`, no failure or rollback | `R5_06_stack-events.json` | PASS | Ten ids, no `FAILED` / `ROLLBACK` |
| 07 | Seven contract keys with export names | `R5_outputs.json`, `R5_07_exports.json` | PASS | Equal key sets and values |
| 08 | Trust `ec2.amazonaws.com` only (**DC-13**); boundary = `PermissionBoundaryArn` (**DC-12**); `Path /`; tags | `R5_08_runtime-role.json` | PASS | One statement, `Allow`, `sts:AssumeRole`; `PermissionsBoundaryType` `Policy`; `Name`, `project` |
| 08 | Exactly four attached policies; no inline | `R5_08_runtime-role-attached.json`, `R5_08_runtime-role-inline.json` | PASS | invoke, supporting-services, deploy-bucket-read, explicit-deny (**DC-11** attached); `PolicyNames` `[]` |
| 08 | Instance profile holds exactly the runtime role (**DC-09**, profile half) | `R5_08_instance-profile.json` | PASS | As required |
| 08 | Flow-logs role trust and attachment | `R5_08_flow-logs-role.json`, `R5_08_flow-logs-role-attached.json` | PASS | `vpc-flow-logs.amazonaws.com` only, `aws:SourceAccount` 797661577394, `aws:SourceArn` `arn:aws:ec2:eu-north-1:797661577394:vpc-flow-log/*`; one policy `flow-logs-write` |
| 08 | Exactly six customer-managed policies; boundary used once as a boundary | `R5_08_local-policies-after.json` | PASS | As required |
| 08 | No "temporary" / "validation" in any description (**exit condition 4**) | `R5_08_policy-*.json` (six) | PASS | Six descriptions checked case-insensitively |
| 08 | Documents equal the template (**DC-10**, **DC-11**, **DC-12**) | `R5_08_policy-version-*.json` (six) | PASS | boundary 10 statements, bedrock-invoke 2, explicit-deny 5, supporting-services 5, deploy-bucket-read 3, flow-logs-write 1: all equal |
| 09 | Profiles `allowed`; boundary allows | `R5_09_allow-profiles.json` | PASS | 2 actions × 2 profiles `allowed`; matched `bedrock-invoke`; `AllowedByPermissionsBoundary` true; `AllowedByOrganizations` true |
| 09 | Twelve routed models `allowed` with Region and profile context (**exit condition 1**) | `R5_09_allow-fm-*.json` (12) | PASS | Each `allowed`, matched `bedrock-invoke`, organizations true |
| 09 | `explicitDeny`: admin / logging, `global.` profile, non-Claude model, us-east-1, iam | `R5_09_deny-admin-logging.json`, `-global-profile`, `-non-claude-model`, `-unapproved-region`, `-iam` | PASS | Each matched `proposal-orchestrator-explicit-deny`; organizations true |
| 09 | `implicitDeny`: model without profile, Haiku eu. profile, direct `kms:Decrypt` | `R5_09_deny-fm-without-profile.json`, `-eu-profile-not-od7`, `-kms-identity-grant` | PASS | As expected; organizations true |
| 09 | Seven cases without Region context | `R5_09_allow-s3-get-bundle.json`, `-allow-s3-list-bundles`, `-allow-secret`, `-allow-sts-ssm`, `-deny-ec2`, `-deny-s3-other-bucket`, `-deny-s3-put-bundle` | N/A | **Superseded** by step 12: decided by the organization's SCP (`AllowedByOrganizations` false), not by R5's policies — a step-sheet error, kept as history (`STEPS_fix1.md`) |
| 10 | Credits ≥ 199.00 | `R5_10_plan-state-after.json` | PASS | 199.99 USD, unchanged |
| 12 | S3 get / list on `bundles/`, secret, sts + SSM `allowed`, boundary allows, organizations true | `R5_12_allow-*.json` (4) | PASS | Matched `deploy-bucket-read` / `supporting-services` |
| 12 | List outside `bundles/`, put / delete on `bundles/` `implicitDeny` (R5-D1, R5-D2) | `R5_12_deny-s3-list-outside-bundles.json`, `R5_12_deny-s3-put-bundle.json` | PASS | As expected, organizations true |
| 12 | Other bucket, ec2 `explicitDeny` from our deny | `R5_12_deny-s3-other-bucket.json`, `R5_12_deny-ec2.json` | PASS | Matched `proposal-orchestrator-explicit-deny`, organizations true |
| 13 | `168 passed`, no test ids | `R5_11_pytest.txt` | PASS | Python 3.10.6, `168 passed`; no pattern string (the first two runs of this file were re-collected, `RUNLOG.md`) |
| 13 | Secret scan `CLEAN`, `exit=0` (after the tests) | `R5_11_secret-scan.txt` | PASS | As required |
| 13 | Old-ID guard `CLEAN`, `exit=0` | `R5_11_old-id-guard.txt` | PASS | As required |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| IAM simulation allows invoke for each OD7 model and its routed foundation models. | PASS | `R5_09_allow-profiles.json` and the twelve `R5_09_allow-fm-*.json`. Simulation supplies the context; that a live routed call carries the destination Region is Inferred (F-R5-2) and is shown by R11 |
| IAM simulation denies admin actions, non-Claude models, `global.` profiles, and S3, EC2 and IAM actions outside the policy. | PASS | Explicit: `R5_09_deny-admin-logging`, `-global-profile`, `-non-claude-model`, `-unapproved-region`, `-iam`, `R5_12_deny-s3-other-bucket`, `R5_12_deny-ec2`. Implicit (no grant): `R5_12_deny-s3-put-bundle`, `-s3-list-outside-bundles`, `R5_09_deny-fm-without-profile`, `-eu-profile-not-od7`, `-kms-identity-grant` |
| The boundary and explicit deny are attached to the role the instance profile uses. DC-09 to DC-13 are evidenced on that role. | PASS | `R5_08_runtime-role.json` (boundary), `R5_08_runtime-role-attached.json` (explicit deny among four), `R5_08_instance-profile.json` (that role). DC-10–DC-13 VERIFIED_PASS; DC-09 IN_PROGRESS by R5-D9 (that the **host** uses the profile is R11, DC-14) |
| No policy in the account carries "temporary" or "validation" in its name or description. | PASS | `R5_03_local-policies-before.json` `[]`; `R5_08_local-policies-after.json` six `proposal-orchestrator-*` names; `R5_08_policy-*.json` descriptions |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS, or N/A with its reason (seven superseded step-09 files).
- [x] Register v2 updated for DC-09, DC-10, DC-11, DC-12, DC-13, DC-16 (2026-10-25).
- [x] Worklog v2 entries: 2026-10-25T14:50:00Z (template, decisions, step sheet) and 2026-10-25T21:55:00Z (verification).
- [x] Operator committed R5 as `8dccd77` (94 files) and confirmed in session on 2026-10-26.

## Notes for later tickets

- **Ids:** `R5_outputs.json` is the source. Runtime role `arn:aws:iam::797661577394:role/proposal-orchestrator-runtime-role` (no path); instance profile `proposal-orchestrator-runtime-profile`; boundary `…:policy/proposal-orchestrator-boundary`; explicit deny `…:policy/proposal-orchestrator-explicit-deny`; flow-logs role `…:role/proposal-orchestrator-flow-logs-role`. Import by export name `proposal-orchestrator-iam-<Key>`.
- **R6:** the key policy names `RuntimeRoleArn` (the role ARN, not a session ARN; the boundary admits `kms:Decrypt` / `kms:DescribeKey`); no identity policy grants Decrypt (`R5_09_deny-kms-identity-grant.json`); `kms:ViaService`, if wanted, goes into the key policy (R5-D6). CloudWatch Logs scoped to the prefix `/proposal-orchestrator/`.
- **R7:** flow-log group named exactly `/proposal-orchestrator/vpc-flow-logs` (R5-D4); flow logs use `FlowLogsRoleArn`. Deploy-bucket policy limits the runtime role to `bundles/` read (R5-D1). Delivered flow logs show whether `logs:DescribeLogGroups` scoped to the group suffices (known gap).
- **R8:** secret named `proposal-orchestrator/env-config` (the role's grant is `…:secret:proposal-orchestrator/env-config-*`); resource policy names `RuntimeRoleArn`.
- **R11:** the Bedrock endpoint policy admits the same profile and model ARNs; the first live routed Converse call proves F-R5-2 (if refused: stop, successor record, UPDATE change set — never a "temporary" policy). If Run Command needs the SSM Agent's regional buckets, both R4-D3's endpoint policy and `DenyS3OutsideDeployBundles` change.
- **R12a / R12b, every later simulation:** pass `aws:RequestedRegion` for every regional action, and check `OrganizationsDecisionDetail.AllowedByOrganizations` = true and the matched statement; otherwise the organization's SCP decides (step 09 lesson).
- **Evidence tooling:** run the secret scan after the tests, and keep pytest output quiet (`-q`) in evidence: a refused scan, and the scaffold tests' verbose ids, write the pattern names into the scanned folder. A small fix to `tools/evidence_secret_scan.py` (report line numbers without the pattern text) would remove the trap; not done in R5.
- **R4 VERIFICATION, step 04:** its criterion line lists `CREATE` as checked, but `R4_04_change-set.json` has no `ChangeSetType` field either; the CREATE type was evidenced by the command and the eight `Add` entries. Wording only.

## Follow-up

`STEPS_fix1.md` (steps 12–13): closed, all PASS.
