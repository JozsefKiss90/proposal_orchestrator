# R8 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-26 (round 1 ~21:58 UTC) and 2026-10-27 (round 1b ~15:50 UTC, before execution; round 2 ~16:05 UTC; step 11 ~16:12 UTC) |
| Step sheet | `STEPS.md` (steps 01–11), run as in `RUNLOG.md` |
| Secret scan | Operator: step 05, `R8_05_secret-scan.txt` → `CLEAN`; step 11, `R8_11_secret-scan.txt` → `CLEAN`, `exit=0`, run after the tests. Agent re-run over `evidence_v2/R8` after each round and after this report's last edit → `CLEAN`. |
| Old-ID guard | Operator: `R8_04_old-id-guard.txt` and `R8_11_old-id-guard.txt` → `CLEAN` (20 ids). Agent re-run over the default v2 scope (this report included) → `CLEAN`. |
| Stack | `proposal-orchestrator-secret` (change set `r8-create-01`, created 2026-10-27T15:44:31Z, executed 15:56:21Z after the operator's go), `CREATE_COMPLETE` 15:56:29Z. No hourly cost; the secret is billed 0.40 USD per month, prorated, plus 0.05 USD per 10,000 API requests (R8-D1). Credits 199.99 USD before, 199.98 USD after (the key's fee from R6 beginning to show). |

Every check below was re-run by the agent on the saved files (`utf-8-sig`) in the device shell, by
script, not taken from the pasted terminal output. The resource policy was compared statement by
statement (by `Sid`, lists order-insensitive) with `50-secret.yaml` after resolving `${AWS::Partition}`,
`${AWS::AccountId}`, `AdminRoleArn` and its pathless form (`Fn::Select` / `Fn::Split`, from
`secret.json`) and the `Fn::ImportValue` references (from `R8_03_exports.json`). No evidence file holds a
configuration value: the agent searched every round-2 file for the five values' distinctive strings and
found none; the value was read once, by `tools/env_config_digest.py`, which prints key names and a
SHA-256 only.

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01 | `FREE`, `ACTIVE`, credits ≥ 199.00, expiration 2027-04-19 | `R8_01_plan-state.json` | PASS | FREE, ACTIVE, 199.99 USD |
| 01 | One budget, limit 10.0, spend < 8.5 | `R8_01_budgets.json` | PASS | `My Monthly Cost Budget`, 10.0, spend 0.006 |
| 01 | Three notifications, each `OK` | `R8_01_budget-notifications.json` | PASS | ACTUAL 100, ACTUAL 85, FORECASTED 100, all `OK` |
| 02 | Account 797661577394, `AccountFullAccessRole` | `R8_02_caller-identity.json` | PASS | As required |
| 03a | Secret name free | `R8_03_describe-before.txt` | PASS | `ResourceNotFoundException`, `exit=254` |
| 03b | No `proposal-orchestrator/` secret, scheduled deletions included | `R8_03_secrets-before.json` | PASS | `[]`: no secret at all in the Region |
| 03c | Secret stack absent | `R8_03_secret-stack-before.txt` | PASS | `ValidationError … does not exist`, `exit=254` |
| 03d | Key enabled; policy = R6 | `R8_03_key-before.json`, `R8_03_key-policy-before.json` | PASS | Enabled, customer-managed, symmetric, single-Region; five statements equal `R6/R6_08_key-policy.json` by `Sid` |
| 03e | Admin role with `/managed/` path = `AdminRoleArn` | `R8_03_admin-role.json` | PASS | `arn:aws:iam::797661577394:role/managed/AccountFullAccessRole`, Path `/managed/` (F-R8-3) |
| 03f | 23 exports equal the outputs files; no secret export | `R8_03_exports.json` | PASS | 7 network, 7 iam, 3 kms, 6 audit; values equal R4–R7 outputs; `RuntimeRoleArn`, `KeyArn` as required (F-R8-1) |
| 03g | Price List API answers for eu-north-1 | `R8_03_pricing.txt` | PASS | `exit=0`; 0.40 USD per secret, 0.05 USD per 10,000 requests (F-R8-2) |
| 04 | cfn-lint 1.57.2, exit 0 | `R8_04_cfn-lint.txt` | PASS | Two lines exactly |
| 04 | Template guard `CLEAN: 6`, old-ID guard `CLEAN` | `R8_04_template-guard.txt`, `R8_04_old-id-guard.txt` | PASS | As required |
| 04 | Python 3.10, `196 passed` | `R8_04_pytest.txt` | PASS | Python 3.10.6, `196 passed`, no failed / error / skipped |
| 05 | `Id` / `StackId` ARNs | `R8_05_create-change-set.json` | PASS | eu-north-1, 797661577394, `r8-create-01`, `proposal-orchestrator-secret` |
| 05 | `CREATE_COMPLETE` / `AVAILABLE`; no capability; tag; five parameters; **exactly two** `Add`; no value | `R8_05_change-set.json` | PASS | `Capabilities` `[]`; `EnvConfigSecret`, `EnvConfigSecretPolicy`; parameters as `secret.json`. Operator gave the go in session before step 06 |
| 05 | Scan `CLEAN` | `R8_05_secret-scan.txt` | PASS | `exit=0` |
| 06 | `execute exit=0` | `R8_06_execute-exit.txt` | PASS (deviation, point 17) | The file holds a **repeat** of step 06 run after the stack existed: `InvalidChangeSetStatus … EXECUTE_COMPLETE`, `exit=254`. The first run (15:56:21Z) returned `execute exit=0` in the session transcript (`RUNLOG.md`); the refusal text itself states the change set was executed, and the events below show the user-initiated creation. Accepted by the operator ("17a", R8-D17) |
| 06 | Stack `CREATE_COMPLETE`; no failure or rollback | `R8_06_stack-status.json`, `R8_06_stack-events.json` | PASS | Nine events: create `User Initiated` 15:56:21Z, `EnvConfigSecret` `CREATE_COMPLETE` 15:56:27Z, `EnvConfigSecretPolicy` 15:56:28Z, stack 15:56:29Z; no `FAILED` / `ROLLBACK`; `capabilities` null; tag `project` |
| 07 | Two contract outputs with export names; `SecretArn` = name + six characters | `R8_outputs.json`, `R8_07_exports.json` | PASS | `SecretArn` `arn:aws:secretsmanager:eu-north-1:797661577394:secret:proposal-orchestrator/env-config-KTsWow`; `SecretName` `proposal-orchestrator/env-config`; exports from the secret stack |
| 07 | The secret stack imports `kms-KeyArn` and `iam-RuntimeRoleArn` | `R8_07_imports-keyarn.json`, `R8_07_imports-runtimerolearn.json` | PASS | Both list `proposal-orchestrator-secret` |
| 08 | Name, ARN, `KmsKeyId` = `KeyArn`; no rotation; no replica; not deleted; tags; one `AWSCURRENT` version (**DC-20**) | `R8_08_describe-secret.json` | PASS | No `RotationEnabled`, `ReplicationStatus` or `DeletedDate` key; tags `project` plus CloudFormation's three `aws:cloudformation:*` |
| 08 | One secret by name, `KeyArn`, not deleted, no rotation | `R8_08_list-secrets.json` | PASS | As required |
| 08 | Resource policy = template (**DC-21**) | `R8_08_resource-policy.json` | PASS | Four Deny statements, equal to the resolved template by script; no Allow; principals named only the runtime role and the admin role (with and without `/managed/`) |
| 08 | One version, `AWSCURRENT` | `R8_08_version-ids.json` | PASS | `e10bb0e0-…`, encrypted with `KeyArn` |
| 09 | Five key names; `sha256` = expected; `MATCH`; `exit=0`; no value | `R8_09_key-names-digest.txt` | PASS | `1306b991…6318a` both; `keys: MATCH`, `sha256: MATCH`. The admin role's read was not denied, so one of the two admin forms matches (R8-D12) |
| 10 | Credits ≥ 199.00 | `R8_10_plan-state-after.json` | PASS | 199.98 USD |
| 11 | Python 3.10, `196 passed`; old-ID guard `CLEAN`; secret scan `CLEAN`, run last | `R8_11_pytest.txt`, `R8_11_old-id-guard.txt`, `R8_11_secret-scan.txt` | PASS | Python 3.10.6, `196 passed`, no failed / error / skipped; both `CLEAN`, `exit=0` |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| The secret uses the CMK, and its policy names no principal outside the allowed set. | PASS | `R8_08_describe-secret.json`, `R8_08_list-secrets.json`, `R8_08_version-ids.json` (`KmsKeyId` = `KeyArn`); `R8_08_resource-policy.json` (deny-only; it names only the runtime role and the admin role, R8-D4, R8-D12, R8-D13) |
| Evidence records the key names and metadata only. The E0 scan passes on the folder. | PASS | `R8_09_key-names-digest.txt` (key names and SHA-256); no configuration value in any evidence file; `R8_05_secret-scan.txt`, `R8_11_secret-scan.txt` and the agent's re-runs `CLEAN` |
| DC-20 and DC-21 are evidenced or restated. | PASS | Register v2 rows DC-20, DC-21 VERIFIED_PASS at policy level (R8-D8); DC-22 NOT_APPLICABLE (R8-D14); DC-19 and DC-33–DC-35 notes |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS (step 06's exit file on substitute evidence, R8-D17; no N/A).
- [x] Register v2 updated for DC-20, DC-21, DC-22 and the DC-19 and DC-33–DC-35 notes (2026-10-27).
- [x] Worklog v2 entries: 2026-10-26T22:20:00Z (template, decisions, change set) and 2026-10-27T16:05:00Z (created and verified).
- [x] Step 11 run by the operator (2026-10-27 ~16:10 UTC): 196 passed, old-ID guard and secret scan CLEAN.
- [x] Operator confirmed in session on 2026-10-27 ("Zárd le az R8-at és commitolok", ~16:11 UTC) and commits R8 together with this closing (template, test, digest script, decision record, README, tickets, register, worklog, `evidence_v2/R8/`). R8 ticked in `plans/aws_redeployment_tickets.md`.

## Notes for later tickets

- **Ids:** `R8_outputs.json` is the source. Secret `arn:aws:secretsmanager:eu-north-1:797661577394:secret:proposal-orchestrator/env-config-KTsWow`. Import by export name `proposal-orchestrator-secret-<Key>`.
- **R9 / R9e:** the secret stores the preset `BEDROCK_CONVERSE_EU`, which does not exist yet (R8-D3); a launcher reading it fails closed until R9e adds it. Only `GetSecretValue` is allowed to the runtime role, by IAM and by the resource policy; a launcher needing `DescribeSecret` would need a successor record (R8-D13).
- **R11:** the runtime role's first read, through the `secretsmanager` interface endpoint, exercises R5's grant, the resource policy's runtime exceptions and R6-D3's `kms:ViaService` grant (DC-19, DC-20, DC-21 runtime half).
- **Model switch (OD7 target):** change `TransportModelId` and UPDATE the secret stack; never `put-secret-value` (R8-D2). Re-run `tools/env_config_digest.py` afterwards.
- **The secret stack is not deleted** (R8-D5). While it imports `kms-KeyArn` and `iam-RuntimeRoleArn`, those exports cannot change.
- **Register summary table:** still not recounted since E0 (R12b or R13).
