# AWS redeployment: handoff for R7 (audit and storage stack: trail, two buckets, flow logs)

| Field | Value |
|---|---|
| Date | 2026-10-26 |
| Branch at writing | `msca-dn-pre-eval`; R6 committed as `0487e68` (`R6 completed`) and confirmed 2026-10-26. The "Close R6" commit — R6 ticked in the tickets file, `evidence_v2/R6/VERIFICATION.md` done conditions, the closing worklog entry, this file — is the operator's to make if `git log` does not show it yet. |
| For | The agent that runs ticket R7 with the operator in a new session |
| Read first | `CLAUDE.md`; `plans/aws_redeployment_tickets.md` (inherited constraints; R7; R11, R12b, R15 for what consumes R7's outputs); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F7, §6 R7, §7, §7a; §2 of this file (and the R4–R6 handoffs' §2); `docs/tier4_orchestration_state/decision_log/aws-redeployment-r6-kms_2026-10-26.json` (R6-D2 trail name, R6-D3 runtime grant via S3, R6-D5, R6-D10 no Bucket Key on the trail bucket); `aws-redeployment-r5-iam_2026-10-25.json` (R5-D1 `bundles/`, R5-D2, R5-D4 flow-log group and its known gap); `aws-redeployment-r4-network_2026-10-24.json` (R4-D3 S3 gateway endpoint policy); `aws-redeployment-od6-stack-layout-r3_2026-10-22.json` (layout: audit imports the key, the subnet and the flow-logs role; derived bucket names); `deploy/aws/README.md`; `docs/infrastructure_security/evidence_v2/R6/VERIFICATION.md` and `evidence_v2/R5/VERIFICATION.md` ("Notes for later tickets"); the v1 files `evidence/06_cloudtrail/trail_bucket_policy.json`, `lifecycle_policy.json`, `CT-E01-trail-configuration.json` (UTF-16), `CT-E05-event-selectors.json` (UTF-16), `CG6_steps.txt` and `evidence/07_cloudwatch/` — **as history to be corrected, not as source** (old account, us-east-1) |
| Decision records in force | as listed in the R6 handoff, plus `aws-redeployment-r6-kms_2026-10-26` |
| Status | E0, R0–R6 done. Frontier: **R7**, R8, R12a, R9, R9e, R10. R11 waits for R7 and R8. |

## 1. Facts that govern R7

| Fact | Record / evidence |
|---|---|
| Account `797661577394`, Free plan, 199.99 USD credits after R6 (the key's monthly fee had not yet appeared); regional work in **eu-north-1**. Every `s3api`, `cloudtrail`, `logs`, `ec2`, `bedrock` and `cloudformation` command names `--region eu-north-1`. | `evidence_v2/R6/R6_10_plan-state-after.json` |
| R7 fills **`proposal-orchestrator-audit`** (`deploy/aws/templates/40-audit.yaml`, parameters `deploy/aws/parameters/audit.json`: `ExpectedAccountId`, `ExpectedRegion`). Bucket names are derived, not passed: `${ProjectName}-cloudtrail-${AWS::AccountId}` and `${ProjectName}-deploy-${AWS::AccountId}`. | OD6-r3-parameters; skeleton |
| Outputs to add, exports `proposal-orchestrator-audit-<Key>`: `TrailBucketName`, `DeployBucketName` (R12a, R15), `TrailArn`, `FlowLogGroupName`, `FlowLogGroupArn`, `FlowLogId`. One `FlowLogId` in the contract. | `deploy/aws/outputs_contract.json` |
| Imports: `proposal-orchestrator-kms-KeyArn`, `proposal-orchestrator-network-PrivateSubnetId` (and/or `-VpcId`, see §4), `proposal-orchestrator-iam-FlowLogsRoleArn`; for the deploy-bucket policy, `proposal-orchestrator-iam-RuntimeRoleArn`. | OD6-r3-layout; `R6_outputs.json`, `R5_outputs.json`, `R4_outputs.json` |
| **Trail name and home Region are fixed by R6's key policy**: `proposal-orchestrator-bedrock-trail`, ARN `arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/${ProjectName}-bedrock-trail`, home eu-north-1, `KmsKeyId` = `KeyArn`. The key grants CloudTrail `kms:GenerateDataKey*` (aws:SourceArn + CloudTrail encryption context) and `kms:DescribeKey` (aws:SourceArn), **no Decrypt**. | R6-D2, R6-D10; `R6_08_key-policy.json` |
| **The trail bucket has no S3 Bucket Key on the CMK** (R6-D10), because CloudTrail's guide requires a CloudTrail Decrypt grant when the bucket uses one. If R7 shows trail creation needs Decrypt anyway, stop; successor record; UPDATE of the kms stack first. | R6-D10, F-R6-4 |
| **CloudWatch Logs** may use the key only for log groups under `/proposal-orchestrator/` in eu-north-1. The flow-log group is exactly `/proposal-orchestrator/vpc-flow-logs` (R5-D4); its retention 90 days, `KmsKeyId` = `KeyArn` (DC-30). The flow-logs role writes only to that group's ARN (`…:log-group:/proposal-orchestrator/vpc-flow-logs:*`) and trusts `vpc-flow-logs.amazonaws.com` only for `aws:SourceAccount` = the account and `aws:SourceArn` like `arn:…:ec2:${AWS::Region}:${AWS::AccountId}:vpc-flow-log/*`. Known gap: whether `logs:DescribeLogGroups` scoped to the group suffices — delivered flow logs show it. | R5-D4; `R5_08_policy-version-proposal-orchestrator-flow-logs-write.json`, `R5_08_flow-logs-role.json` |
| **Deploy bucket**: SSE-KMS with `KeyArn`; Block Public Access; versioning; the runtime role reads only `bundles/` (R5-D1: `s3:ListBucket` with `s3:prefix` `bundles/*`, `s3:GetBucketLocation`, `s3:GetObject` on `bundles/*`); the runtime role decrypts through `s3.eu-north-1.amazonaws.com` (R6-D3). The S3 gateway endpoint policy (R4-D3) already admits read-only actions on this bucket for principals of this account; it is not changed by R7. The explicit deny refuses the runtime role every other S3 resource (R5-D2). | R5-D1, R5-D2, R4-D3, R6-D3 |
| **Trail bucket** (ticket R7): versioning, Block Public Access, the v1 bucket policy with new ARNs (CloudTrail ACL check and write by `aws:SourceArn`, deny unencrypted objects, deny insecure transport), lifecycle 90 days → `GLACIER_IR`, expiry 365 days (v1 also expired noncurrent versions after 30 days and used the prefix `cloudtrail/proposal-orchestrator/`). | ticket R7; DC-25, DC-27; v1 history |
| v1 trail: single-Region (us-east-1), `IncludeGlobalServiceEvents` true, log-file validation on, management events only (`ReadWriteType` All, no data resources); its Converse calls were captured. Whether that still holds for `eu.` profile calls made in eu-north-1 is DC-26, shown by R11. | `evidence/06_cloudtrail/CT-E01*`, `CT-E05*` (UTF-16); register v2 DC-26 |
| **Invocation logging stays unset** (constraint; DC-28); no `/aws/bedrock` log group (DC-29). R7 evidences both read-only. | tickets inherited constraints |
| Cost: CloudTrail's first copy of management events is free; S3 storage and CloudWatch Logs ingestion are billed by usage (the README counts the stack as "free (storage: usage)"). No hourly cost. Verify against the pricing pages before quoting a figure. | `deploy/aws/README.md`; handoff 2026-10-21 §8 |
| SCPs and AWS-managed RCPs apply (OD11-r2): RCPs can affect S3 and KMS. A refusal shows as an explicit deny at the change set or at creation. | OD11-r2 known gap; R6 known gap |
| Template rules as before (guard, project tag, no literal, ≤ 51,200 bytes, `Metadata.FillDecision`, placeholder removed). Check on their reference pages, before writing, whether `AWS::S3::Bucket`, `AWS::S3::BucketPolicy`, `AWS::CloudTrail::Trail`, `AWS::Logs::LogGroup` and `AWS::EC2::FlowLog` take `Tags`; a type without one joins `UNTAGGABLE_TYPES` only after that check (the guard's rule). | `tools/aws_template_guard.py`; R5-D8 pattern |

## 2. How the operator works (additions from R6)

Everything in the R4–R6 handoffs' §2 holds. Measured in R6:

- The operator reports rounds as pasted terminal transcripts; the agent verifies from the files on disk only.
- `.venv-lint` is often active during AWS and `py -3.10` steps; harmless so far (`py -3.10` resolves to the system interpreter). Record it in `RUNLOG.md` as a deviation, do not fail it.
- A CREATE change set leaves the stack in `REVIEW_IN_PROGRESS` with no resources; free.
- `describe-stacks` returns `capabilities: null` for a stack created without capabilities.
- A live resource policy is compared with the template by script: resolve `Fn::Sub`, `Ref` and `Fn::ImportValue` (from the saved export list), compare statement by statement by `Sid`, lists order-insensitive. Reuse it for the bucket policies (`get-bucket-policy`, a JSON string in `Policy`).
- `simulate-principal-policy` lists `MissingContextValues` for condition keys of unrelated statements; check that those statements cannot grant the action under test before calling it harmless.
- The operator answers settled points as "1–N a"; points the agent adds after reading the docs get their own number and answer.

## 3. R7 as it reads

Ticket exit conditions:

1. **Both buckets show Block Public Access, versioning and the CMK.**
2. **The trail validates log files and logs to the trail bucket.**
3. **Flow logs are active on every subnet.**
4. **The invocation-logging configuration is empty.**
5. **DC-08, DC-23 to DC-25 and DC-27 to DC-30 are evidenced. DC-26 waits for R11.**

## 4. Points to settle with the operator before writing the template

- **Trail bucket encryption.** The ticket says both buckets show the CMK. Options: (a) default encryption SSE-KMS with `KeyArn`, `BucketKeyEnabled` false (R6-D10), plus the trail's own `KmsKeyId`; (b) default SSE-S3 with the trail writing SSE-KMS objects. Proposal: (a) — "the bucket shows the CMK" then holds for the bucket configuration and for every object.
- **"Deny unencrypted objects".** v1 denied `s3:PutObject` when `s3:x-amz-server-side-encryption` is not `aws:kms`. `StringNotEquals` is also true when the header is absent, so a PUT that relies on default encryption is refused. CloudTrail sends the header (v1 delivered); the operator's own uploads would need `--sse aws:kms`. Proposal: keep the v1 statement on the trail bucket; decide separately whether the deploy bucket gets it (R15 uploads by the admin role).
- **Deploy bucket policy.** Proposal: deny insecure transport; allow the runtime role `bundles/` read (mirroring R5-D1, with the role ARN imported); optionally deny any principal outside the account. Decide whether `BucketKeyEnabled` is true there (fewer KMS requests; the decrypt is still via S3, R6-D3).
- **Retention.** Proposal: `DeletionPolicy: Retain` / `UpdateReplacePolicy: Retain` on both buckets and the log group (audit data must outlive the stack; a non-empty bucket blocks deletion anyway); the trail and the flow log go with the stack. The audit stack is not deleted.
- **Flow-log scope.** R4 has one private subnet. Options: (a) one flow log on the VPC (covers every subnet, present and future; one `FlowLogId` as in the contract); (b) one per subnet. Traffic type `ALL`, destination CloudWatch Logs, `DeliverLogsPermissionArn` = `FlowLogsRoleArn`; aggregation interval (60 or 600 s) to decide. DC-08's wording "on every subnet" is shown by `describe-flow-logs` on the VPC plus the subnet list.
- **Trail settings.** Proposal: single-Region trail in eu-north-1 (as v1, and as R6-D2's ARN assumes), `IncludeGlobalServiceEvents` true, `EnableLogFileValidation` true, management events All, no data events, S3 key prefix `cloudtrail/${ProjectName}`, `IsLogging` true. Read the `AWS::CloudTrail::Trail` page for `DependsOn` on the bucket policy (CloudTrail checks the policy at creation).
- **Lifecycle.** Proposal: as v1 with new names: prefix `cloudtrail/${ProjectName}/`, 90 days → `GLACIER_IR`, expire 365 days, noncurrent versions expire after 30 days.
- **Tests and guard.** `tests/test_aws_audit_template.py` in the R5/R6 style; guard additions only after the reference pages.
- **Evidence.** `get-bucket-encryption`, `get-public-access-block`, `get-bucket-versioning`, `get-bucket-policy`, `get-bucket-lifecycle-configuration` for both buckets; `describe-trails`, `get-trail-status` (delivery, `LatestDeliveryTime` after some minutes), `get-event-selectors`; `describe-log-groups`; `describe-flow-logs` (status `ACTIVE`, then `DeliverLogsStatus` SUCCESS and a log stream once traffic exists); `aws bedrock get-model-invocation-logging-configuration` (empty) and `describe-log-groups --log-group-name-prefix /aws/bedrock` (empty). Delivery evidence may need a second session.
- **Register v2.** Proposal: DC-08, DC-23–DC-25, DC-27–DC-30 `VERIFIED_PASS` on their criteria once delivery is shown; DC-19 note updated ("CloudTrail and CloudWatch Logs grants exercised in R7").

## 5. Step sheet outline (suggestion)

`evidence_v2/R7/STEPS.md`, rounds as in R6.

1. Session-start check (R1-D2), credits ≥ 199.00 (the key fee may have started to show; report the figure).
2. Caller identity.
3. **Read-only lookups:** the two bucket names free (`head-bucket` → 404/403; `list-buckets`); no trail in eu-north-1; no log group under `/proposal-orchestrator/` or `/aws/bedrock`; flow logs on the VPC (none); invocation-logging configuration (empty, before); the audit stack absent (`exit=254`); exports of network, iam and kms present. Hand back; the agent fills the template, the test, the decision record and steps 04–05.
4. Lint, guards, tests (`-q`).
5. Change set (no IAM resources: no capability expected) → the agreed `Add` list. Hand back; the operator's go.
6. Execute; status; events.
7. Outputs → `R7_outputs.json`; exports.
8. Read-only evidence per §4; policies compared by script.
9. Delivery: trail status and an object under the prefix; flow-log stream (may be a later session).
10. Session-end credits.
11. Tests, old-ID guard, secret scan last; commit; confirm.

## 6. Files

| Path | What |
|---|---|
| `deploy/aws/templates/40-audit.yaml` | Filled; `SkeletonPlaceholder` removed; `Metadata.FillDecision` |
| `deploy/aws/parameters/audit.json` | Unchanged unless §4 adds a parameter |
| `tests/test_aws_audit_template.py` | The R7 shape test |
| `tools/aws_template_guard.py` | Only if a reference page shows an untaggable type |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r7-audit_<date>.json` | The §4 answers |
| `docs/infrastructure_security/evidence_v2/R7/` | `STEPS.md`, `RUNLOG.md`, `R7_<NN>_<name>`, `R7_outputs.json`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_control_register_v2.md` | DC-08, DC-23–DC-25, DC-27–DC-30; DC-19 note |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | One entry per R7 milestone |
| `deploy/aws/README.md` | "Filled so far" line; the test list |

## 7. Done for R7

Every `VERIFICATION.md` criterion PASS (or N/A with reason); the R3–R7 tests pass with `py -3.10`; the template guard and the old-ID guard are CLEAN; the secret scan of `evidence_v2/R7` is CLEAN (run after the tests); register v2 rows updated; worklog entries; the operator commits and confirms in session. Then tick R7 in `plans/aws_redeployment_tickets.md`. R11 then waits only on R8.
