# R6 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-26 (round 1 ~16:40 UTC; round 1b ~16:50 UTC, before execution; round 2 ~17:05 UTC; round 3 ~17:06 UTC) |
| Step sheet | `STEPS.md` (steps 01–11), run as in `RUNLOG.md` |
| Secret scan | Operator: step 11, `R6_11_secret-scan.txt` → `CLEAN`, `exit=0`, run after the tests. Agent re-run over `evidence_v2/R6` after each round → `CLEAN`. |
| Old-ID guard | Operator: `R6_11_old-id-guard.txt` → `CLEAN` (20 ids). Agent re-run over the default v2 scope (this report included) → `CLEAN`. |
| Stack | `proposal-orchestrator-kms` (change set `r6-create-01`, created 2026-10-26T16:46:56Z, executed after the operator's go), `CREATE_COMPLETE`. Key `4ccc45a1-f205-4775-aa0b-195290bf1561` created 2026-10-26T16:54:37Z. No hourly cost; the key's monthly fee runs from creation (R6-D1). Credits 199.99 USD before and after. |

Every check below was re-run by the agent on the saved files (`utf-8-sig`) in the device shell, by
script, not taken from the pasted terminal output. The key policy was compared statement by statement
(by `Sid`, lists order-insensitive) with `30-kms.yaml` after resolving `${AWS::Partition}`,
`${AWS::Region}`, `${AWS::AccountId}`, `ProjectName` and the `Fn::ImportValue` (from `R6_03_exports.json`).

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01 | `FREE`, `ACTIVE`, credits ≥ 199.00, expiration 2027-04-19 | `R6_01_plan-state.json` | PASS | FREE, ACTIVE, 199.99 USD |
| 01 | One budget, limit 10.0, spend < 8.5 | `R6_01_budgets.json` | PASS | `My Monthly Cost Budget`, 10.0, spend 0.006 |
| 01 | Three notifications, each `OK` | `R6_01_budget-notifications.json` | PASS | ACTUAL 100, ACTUAL 85, FORECASTED 100, all `OK` |
| 02 | Account 797661577394, `AccountFullAccessRole` | `R6_02_caller-identity.json` | PASS | As required |
| 03a | No `alias/proposal-orchestrator` | `R6_03_aliases-before.json` | PASS | Twelve aliases, all `alias/aws/*` |
| 03b | Keys listed; no customer-managed key | `R6_03_keys-before.json`, `R6_03_keys-detail-before.json` | PASS | Two keys, both `KeyManager` `AWS` (RDS and Lambda default keys) (F-R6-1) |
| 03c | Stack does not exist; `exit=254` | `R6_03_kms-stack-before.txt` | PASS | `ValidationError … does not exist`, `exit=254` |
| 03d | Seven iam exports; `RuntimeRoleArn` = `R5_outputs.json`; no kms export | `R6_03_exports.json` | PASS | 7 iam + 7 network exports; `arn:aws:iam::797661577394:role/proposal-orchestrator-runtime-role` (F-R6-2) |
| 03e | Runtime role: the four R5 policies; no inline | `R6_03_runtime-role-attached-before.json`, `R6_03_runtime-role-inline-before.json` | PASS | Same set as `R5_08_runtime-role-attached.json`; `PolicyNames` `[]` |
| 03f | Trail name free | `R6_03_trails-before.json` | PASS | `[]`: no trail visible in eu-north-1, shadow trails included |
| 04 | cfn-lint 1.57.2, exit 0 | `R6_04_cfn-lint.txt` | PASS | Two lines exactly |
| 04 | Template guard `CLEAN: 6`, old-ID guard `CLEAN` | `R6_04_template-guard.txt`, `R6_04_old-id-guard.txt` | PASS | As required |
| 04 | Python 3.10, `157 passed` | `R6_04_pytest.txt` | PASS | Python 3.10.6, `157 passed`, no failed / error / skipped |
| 05 | `Id` / `StackId` ARNs | `R6_05_create-change-set.json` | PASS | eu-north-1, 797661577394, `r6-create-01`, `proposal-orchestrator-kms` |
| 05 | `CREATE_COMPLETE` / `AVAILABLE`; no capability; tag; three parameters, no `AdminRoleArn`; **exactly two** `Add` | `R6_05_change-set.json` | PASS | `Capabilities` `[]`; `ProjectKey` (AWS::KMS::Key), `ProjectKeyAlias` (AWS::KMS::Alias). Operator gave the go in session before step 06 |
| 06 | `execute exit=0` | `R6_06_execute-exit.txt` | PASS | As required |
| 06 | `CREATE_COMPLETE`, capabilities null, tag | `R6_06_stack-status.json` | PASS | As required |
| 06 | Key, alias and stack `CREATE_COMPLETE`, no failure or rollback | `R6_06_stack-events.json` | PASS | Three ids, no `FAILED` / `ROLLBACK` |
| 07 | Three contract keys with export names | `R6_outputs.json`, `R6_07_exports.json` | PASS | `KeyArn` `arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-…`, `KeyId` the same uuid, `KeyAliasName` `alias/proposal-orchestrator`; exports equal, from the kms stack of step 05 |
| 08 | Customer-managed, enabled, symmetric, `ENCRYPT_DECRYPT`, `AWS_KMS`, single-Region; description clean (**DC-18**) | `R6_08_describe-key.json` | PASS | As required |
| 08 | Rotation on, 365 days (**DC-18**, **exit condition 1**) | `R6_08_rotation-status.json` | PASS | `KeyRotationEnabled` true, `RotationPeriodInDays` 365, `NextRotationDate` 2027-10-26 |
| 08 | The alias resolves to the new key (**exit condition 1**) | `R6_08_describe-by-alias.json`, `R6_08_aliases-of-key.json` | PASS | `describe-key alias/proposal-orchestrator` → `KeyId` 4ccc45a1-…; the key has exactly that one alias |
| 08 | Key policy = template, five statements (**DC-19**, **exit condition 2**) | `R6_08_key-policy.json` | PASS | `PolicyName` `default`; Version 2012-10-17; the five Sids equal the resolved template by script; the runtime role named by its role ARN |
| 08 | `Name` and `project` tags | `R6_08_key-tags.json` | PASS | Exactly those two |
| 08 | No grants | `R6_08_key-grants.json` | PASS | `Grants` `[]` |
| 08 | Runtime role unchanged: four policies, no inline (**exit condition 2**) | `R6_08_runtime-role-attached.json`, `R6_08_runtime-role-inline.json` | PASS | Same set as step 03e; `PolicyNames` `[]` |
| 09 | `kms:Decrypt`, `kms:DescribeKey` on `KeyArn`: `implicitDeny`, no matched statement, organizations and boundary allow (**exit condition 2**) | `R6_09_deny-kms-identity-grant.json` | PASS | As required. `MissingContextValues` lists `bedrock:InferenceProfileArn` and `s3:prefix`: these keys occur only in the conditions of two Allow statements whose actions are Bedrock invoke and `s3:ListBucket` (`20-iam.yaml`, checked by script), so they cannot grant a KMS action; the decision is unaffected |
| 10 | Credits ≥ 199.00 | `R6_10_plan-state-after.json` | PASS | 199.99 USD (the key's fee is billed with a delay) |
| 11 | Python 3.10, `179 passed`, no failed / error / skipped | `R6_11_pytest.txt` | PASS | Python 3.10.6, `179 passed`; quiet output, no test ids |
| 11 | Old-ID guard `CLEAN`, `exit=0` | `R6_11_old-id-guard.txt` | PASS | As required (20 ids) |
| 11 | Secret scan `CLEAN`, `exit=0`, run after the tests | `R6_11_secret-scan.txt` | PASS | As required; agent re-run over the folder → `CLEAN` |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| Rotation is on, and the alias resolves to the new key. | PASS | `R6_08_rotation-status.json` (on, 365 days); `R6_08_describe-by-alias.json`, `R6_08_aliases-of-key.json` (alias → `4ccc45a1-…`, created by this stack) |
| The key policy names the runtime role. No IAM policy grants that role Decrypt separately. | PASS | `R6_08_key-policy.json` (`AllowRuntimeRoleDecryptViaServices`, principal the runtime role ARN, via Secrets Manager / S3 only); `R6_08_runtime-role-attached.json` and `-inline.json` unchanged since R5; `R6_08_key-grants.json` `[]`; `R6_09_deny-kms-identity-grant.json` `implicitDeny` with the boundary allowing |
| DC-18 and DC-19 are evidenced. | PASS | Register v2 rows DC-18, DC-19 (R6-D9): DC-18 VERIFIED_PASS; DC-19 VERIFIED_PASS on the policy-level criterion, the grants themselves exercised in R7 (CloudTrail, CloudWatch Logs) and R8/R11 (runtime role) |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS (no N/A).
- [x] Register v2 updated for DC-18, DC-19 (2026-10-26).
- [x] Worklog v2 entries: 2026-10-26T16:50:00Z (template, decisions, change set) and 2026-10-26T17:05:00Z (verification).
- [x] Operator committed R6 as `0487e68` (48 files) and confirmed in session on 2026-10-26 ("Kész a commit. zárd le az R6-ot", ~17:08 UTC).

## Notes for later tickets

- **Ids:** `R6_outputs.json` is the source. Key `arn:aws:kms:eu-north-1:797661577394:key/4ccc45a1-f205-4775-aa0b-195290bf1561`, alias `alias/proposal-orchestrator`. Import by export name `proposal-orchestrator-kms-<Key>`.
- **R7:** the trail is named exactly `proposal-orchestrator-bedrock-trail`, home Region eu-north-1, `KmsKeyId` = `KeyArn` (R6-D2); the trail bucket has **no S3 Bucket Key** on this CMK (R6-D10); the flow-log group is `/proposal-orchestrator/vpc-flow-logs` (covered by the Logs grant's `/proposal-orchestrator/*` prefix); the deploy bucket is SSE-KMS with `KeyArn` (the runtime role reads through `s3.eu-north-1.amazonaws.com`). A refused trail creation or log-group association is a FAIL that leads to a successor record and an UPDATE of the kms stack.
- **R8:** the secret uses `KeyArn`; the runtime role's `GetSecretValue` exercises the key-policy grant through `secretsmanager.eu-north-1.amazonaws.com`.
- **The kms stack is never deleted** (R6-D5): the key is retained and would keep billing without its alias. An UPDATE changes the key policy in place; `KeySpec`, `KeyUsage`, `MultiRegion` and `Origin` cannot change.
- **Imports:** while the kms stack imports `proposal-orchestrator-iam-RuntimeRoleArn`, the IAM stack cannot change that export; replacing the runtime role means updating the kms stack (and R8's) first.
