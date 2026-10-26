# R7 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-26 (round 1 ~17:26 UTC; round 1b ~17:37 UTC, before execution; round 2 ~17:55 UTC; round 3 ~19:05 and ~19:40 UTC) |
| Step sheet | `STEPS.md` (steps 01–12, with 11b), run as in `RUNLOG.md` |
| Secret scan | Operator: step 12, `R7_12_secret-scan.txt` → `CLEAN`, `exit=0`, run after the tests. Agent re-run over `evidence_v2/R7` after each round and after this report's last edit → `CLEAN`. |
| Old-ID guard | Operator: `R7_04_old-id-guard.txt` and `R7_12_old-id-guard.txt` → `CLEAN` (20 ids). Agent re-run over the default v2 scope (this report included) → `CLEAN`. |
| Stack | `proposal-orchestrator-audit` (change set `r7-create-01`, created 2026-10-26T17:33:20Z, executed after the operator's go), `CREATE_COMPLETE`; trail logging since 17:44:09Z. No hourly cost; S3 storage, log ingestion and KMS requests are billed by usage. Credits 199.99 USD before and after. |

Every check below was re-run by the agent on the saved files (`utf-8-sig`) in the device shell, by
script, not taken from the pasted terminal output. Both bucket policies were compared statement by
statement (by `Sid`, lists order-insensitive) with `40-audit.yaml` after resolving `${AWS::Partition}`,
`${AWS::Region}`, `${AWS::AccountId}`, `ProjectName`, `${<Bucket>.Arn}` and the `Fn::ImportValue`
references (from `R7_03_exports.json`).

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01 | `FREE`, `ACTIVE`, credits ≥ 199.00, expiration 2027-04-19 | `R7_01_plan-state.json` | PASS | FREE, ACTIVE, 199.99 USD (the key's monthly fee not yet visible) |
| 01 | One budget, limit 10.0, spend < 8.5 | `R7_01_budgets.json` | PASS | `My Monthly Cost Budget`, 10.0, spend 0.006 |
| 01 | Three notifications, each `OK` | `R7_01_budget-notifications.json` | PASS | ACTUAL 100, ACTUAL 85, FORECASTED 100, all `OK` |
| 02 | Account 797661577394, `AccountFullAccessRole` | `R7_02_caller-identity.json` | PASS | As required |
| 03a | Both bucket names free (`404`); no project bucket | `R7_03_head-trail-bucket.txt`, `R7_03_head-deploy-bucket.txt`, `R7_03_buckets-before.json` | PASS | `(404) Not Found`, `exit=254` twice; the account had no bucket |
| 03b | No trail | `R7_03_trails-before.json` | PASS | `[]` (shadow trails included) |
| 03c | Log groups: none at all, none under the two prefixes | `R7_03_log-groups-before.json`, `R7_03_log-groups-project-before.json`, `R7_03_log-groups-bedrock-before.json` | PASS | All three empty |
| 03d | No flow log; one subnet in the VPC | `R7_03_flow-logs-before.json`, `R7_03_subnets.json` | PASS | `FlowLogs` `[]`; `subnet-018cd285bbe5cbdaf`, eu-north-1a, 10.60.0.0/25 |
| 03e | Invocation logging unset | `R7_03_invocation-logging-before.txt` | PASS | `exit=0`, empty body |
| 03f | Audit stack absent | `R7_03_audit-stack-before.txt` | PASS | `ValidationError … does not exist`, `exit=254` |
| 03g | Key enabled; policy = R6 | `R7_03_key-before.json`, `R7_03_key-policy-before.json` | PASS | Enabled, customer-managed, symmetric, single-Region; five statements equal `R6/R6_08_key-policy.json` by `Sid` |
| 03h | 17 exports; four import values as the outputs files | `R7_03_exports.json` | PASS | 7 network, 7 iam, 3 kms, no audit; `VpcId`, `FlowLogsRoleArn`, `RuntimeRoleArn`, `KeyArn` equal R4/R5/R6 outputs (F-R7-1, F-R7-2) |
| 04 | cfn-lint 1.57.2, exit 0 | `R7_04_cfn-lint.txt` | PASS | Two lines exactly |
| 04 | Template guard `CLEAN: 6`, old-ID guard `CLEAN` | `R7_04_template-guard.txt`, `R7_04_old-id-guard.txt` | PASS | As required |
| 04 | Python 3.10, `177 passed` | `R7_04_pytest.txt` | PASS | Python 3.10.6, `177 passed`, no failed / error / skipped |
| 05 | `Id` / `StackId` ARNs | `R7_05_create-change-set.json` | PASS | eu-north-1, 797661577394, `r7-create-01`, `proposal-orchestrator-audit` |
| 05 | `CREATE_COMPLETE` / `AVAILABLE`; no capability; tag; three parameters; **exactly seven** `Add` | `R7_05_change-set.json` | PASS | `Capabilities` `[]`; the seven logical ids and types as listed. Operator gave the go in session before step 06 |
| 06 | `execute exit=0`; stack `CREATE_COMPLETE`; no failure or rollback | `R7_06_execute-exit.txt`, `R7_06_stack-status.json`, `R7_06_stack-events.json` | PASS | 25 events; seven resources and the stack `CREATE_COMPLETE`; no `FAILED` / `ROLLBACK` |
| 07 | Six contract outputs with export names; exports; `VpcId` imported by the audit stack only | `R7_outputs.json`, `R7_07_exports.json`, `R7_07_imports-vpcid.json` | PASS | Bucket names, trail ARN, group name and ARN as decided; `FlowLogId` `fl-018e0a5b5610c35c7`; `Imports` `["proposal-orchestrator-audit"]` (R7-D11) |
| 08 | Trail bucket: SSE-KMS with the CMK, no Bucket Key; BPA; versioning; owner-enforced; tags | `R7_08_trail-bucket-*.json` | PASS | As required. S3 also reports `BlockedEncryptionTypes` SSE-C (its own default; harmless) |
| 08 | Deploy bucket: SSE-KMS with the CMK and the Bucket Key; BPA; versioning; owner-enforced; tags | `R7_08_deploy-bucket-*.json` | PASS | As required (same SSE-C note) |
| 08 | Both bucket policies = template | `R7_08_trail-bucket-policy.json`, `R7_08_deploy-bucket-policy.json` | PASS | 4 and 8 statements, equal to the resolved template by script |
| 08 | Lifecycles as decided (**DC-27**, R7-D13) | `R7_08_trail-bucket-lifecycle.json`, `R7_08_deploy-bucket-lifecycle.json` | PASS | Trail: prefix `cloudtrail/proposal-orchestrator/`, `GLACIER_IR` 90, expire 365, noncurrent 30. Deploy: whole bucket (`Prefix` ""), noncurrent 30, abort multipart 7, no current expiration |
| 08 | Trail as decided; logging; default selectors; tags (**DC-23**, **DC-24**) | `R7_08_trail.json`, `R7_08_trail-status.json`, `R7_08_trail-event-selectors.json`, `R7_08_trail-tags.json` | PASS | Single-Region, eu-north-1, global events, validation on, CMK, prefix; `IsLogging` true; one selector All / management / no data; `Name`, `project` |
| 08 | Exactly one log group: CMK, 90 days (**DC-30**) | `R7_08_log-groups.json` | PASS | `/proposal-orchestrator/vpc-flow-logs`, the CMK, 90, STANDARD |
| 08 | One flow log on the VPC, ALL, to the group, 600 s, `ACTIVE`, not `FAILED` (**DC-08**) | `R7_08_flow-logs.json`, `R7_08_subnets.json` | PASS | `fl-018e0a5b5610c35c7`, `DeliverLogsStatus` SUCCESS; the VPC's one subnet |
| 08 | Invocation logging unset; no `/aws/bedrock` group (**DC-28**, **DC-29**) | `R7_08_invocation-logging-after.txt`, `R7_08_log-groups-bedrock-after.json` | PASS | `exit=0`, empty; `[]` |
| 09 | Header-less PUT accepted with the CMK and the Bucket Key; head as put; 11 bytes | `R7_09_put-default.json`, `R7_09_head-default.json` | PASS | `aws:kms`, `KeyArn`, `BucketKeyEnabled` true |
| 09 | `AES256` and key-less `aws:kms` PUTs refused | `R7_09_put-aes256.txt`, `R7_09_put-kms-nokey.txt` | PASS | `AccessDenied … explicit deny in a resource-based policy`, `exit=254` twice (R7-D2 2b) |
| 09 | Accepted version deleted; nothing left | `R7_09_delete-version.json`, `R7_09_versions-after.json` | PASS | Same `VersionId`, no delete marker; no versions, no markers |
| 10 | Credits ≥ 199.00 | `R7_10_plan-state-after.json` | PASS | 199.99 USD |
| 11 | Trail delivering; no error | `R7_11_trail-status.json` | PASS | Latest delivery 18:52:24Z, latest digest 18:00:48Z, no error fields |
| 11 | Log and digest objects under the prefix | `R7_11_trail-objects.json` | PASS | 14 log files, 1 digest, plus CloudTrail's two zero-byte folder keys; all under `cloudtrail/proposal-orchestrator/AWSLogs/797661577394/` |
| 11 | Log and digest objects SSE-KMS with the CMK, no Bucket Key (**DC-23**) | `R7_11_log-object-encryption.json`, `R7_11_digest-object-encryption.json` | PASS | `aws:kms`, `KeyArn`, `bucketKey` null |
| 11 | `validate-logs`: digest valid, log files valid | `R7_11_validate-logs.txt` | PASS (digest half) | `1/1 digest files valid`, `exit=0`; the opening digest covers no log file, so the log-file half moved to 11b |
| 11 | Flow log `ACTIVE` / `SUCCESS`; streams listed | `R7_11_flow-log-status.json`, `R7_11_flow-log-streams.json` | PASS | As required; `[]` streams, expected before R11 (R7-D18) |
| 11b | Second digest after 19:00Z; no error | `R7_11b_trail-status.json` | PASS | Latest digest 19:01:20Z, latest delivery 19:31:44Z, no error fields |
| 11b | `≥2/2` digests valid, `N/N` log files valid with N ≥ 1, nothing `INVALID` (**DC-24**) | `R7_11b_validate-logs.txt` | PASS | `2/2 digest files valid`, `12/12 log files valid` for 17:44:09Z–18:44:09Z, `exit=0` |
| 12 | Python 3.10, `177 passed`; old-ID guard `CLEAN`; secret scan `CLEAN`, run last | `R7_12_pytest.txt`, `R7_12_old-id-guard.txt`, `R7_12_secret-scan.txt` | PASS | Python 3.10.6, `177 passed`, no failed / error / skipped; both `CLEAN`, `exit=0` |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| Both buckets show Block Public Access, versioning and the CMK. | PASS | `R7_08_trail-bucket-*.json`, `R7_08_deploy-bucket-*.json` (BPA four true, versioning Enabled, default SSE-KMS with `KeyArn`); delivered objects and the test object carry the CMK (`R7_11_*-object-encryption.json`, `R7_09_head-default.json`) |
| The trail validates log files and logs to the trail bucket. | PASS | `R7_08_trail.json` (`LogFileValidationEnabled` true, `S3BucketName` the trail bucket); `R7_11_trail-objects.json`; `R7_11b_validate-logs.txt` (2/2 digests, 12/12 log files valid) |
| Flow logs are active on every subnet. | PASS | `R7_08_flow-logs.json` (one flow log on the VPC, ALL, ACTIVE, SUCCESS) with `R7_08_subnets.json` (the VPC's one subnet); `R7_11_flow-log-status.json`. Records follow in R11 (R7-D18) |
| The invocation-logging configuration is empty. | PASS | `R7_03_invocation-logging-before.txt`, `R7_08_invocation-logging-after.txt` |
| DC-08, DC-23 to DC-25 and DC-27 to DC-30 are evidenced. DC-26 waits for R11. | PASS | Register v2 rows DC-08, DC-23, DC-24, DC-25, DC-27, DC-28, DC-29, DC-30 VERIFIED_PASS (R7-D10, R7-D18); DC-19 note updated; DC-26 unchanged (R11) |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS (no N/A).
- [x] Register v2 updated for DC-08, DC-23, DC-24, DC-25, DC-27, DC-28, DC-29, DC-30 and the DC-19 note (2026-10-26).
- [x] Worklog v2 entries: 2026-10-26T17:37:00Z (template, decisions, change set) and 2026-10-26T19:40:00Z (created and verified).
- [x] Step 12 run by the operator (2026-10-26 ~20:27 UTC): 177 passed, old-ID guard and secret scan CLEAN.
- [ ] R7 committed by the operator and confirmed in session.

## Notes for later tickets

- **Ids:** `R7_outputs.json` is the source. Trail bucket `proposal-orchestrator-cloudtrail-797661577394`, deploy bucket `proposal-orchestrator-deploy-797661577394`, trail `arn:aws:cloudtrail:eu-north-1:797661577394:trail/proposal-orchestrator-bedrock-trail`, group `/proposal-orchestrator/vpc-flow-logs`, flow log `fl-018e0a5b5610c35c7`. Import by export name `proposal-orchestrator-audit-<Key>`.
- **R11:** the first network interface in the VPC starts flow-log records; evidence a log stream and `DeliverLogsStatus` SUCCESS there (R7-D18), which also closes the R5-D4 known gap. DC-26: the Converse call should appear among the trail's management events (single-Region trail, eu-north-1).
- **R11 / R12b:** the deploy bucket's runtime-role denies (`bundles/` read only) are exercised only by live calls from the host (F-R7-7: no simulation of a resource policy for a role).
- **R15:** upload bundles to `bundles/` **without** encryption headers (the bucket default applies the CMK), or with `--sse aws:kms --sse-kms-key-id <KeyArn>`; a bare `--sse aws:kms` is refused (R7-D2, `R7_09_put-kms-nokey.txt`).
- **The audit stack is not deleted** (R7-D4): both buckets and the group are retained and would collide with a recreated stack. While it imports `network-VpcId`, `iam-FlowLogsRoleArn`, `iam-RuntimeRoleArn` and `kms-KeyArn`, those exports cannot change.
- **Register summary table:** the `## Summary` counts in register v2 have not been updated since E0 (R4–R7 rows changed individually); R12b or R13 should recount.
