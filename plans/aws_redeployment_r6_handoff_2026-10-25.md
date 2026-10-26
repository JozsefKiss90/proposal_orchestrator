# AWS redeployment: handoff for R6 (KMS key: the runtime role decrypts through the key policy)

| Field | Value |
|---|---|
| Date | 2026-10-25 |
| Branch at writing | `msca-dn-pre-eval`; R5 committed as `8dccd77` (`R5 completed`) and confirmed 2026-10-26. The "Close R5" commit — R5 ticked in the tickets file, `evidence_v2/R5/VERIFICATION.md` done conditions, the closing worklog entry, this header — is the operator's to make if `git log` does not show it yet. |
| For | The agent that runs ticket R6 with the operator in a new session |
| Read first | `CLAUDE.md`; `plans/aws_redeployment_tickets.md` (inherited constraints; R6; R7, R8, R11 for what consumes R6's outputs); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F1, §5 OD2, OD8, OD11, §6 R6, §7, §7a; §2 of this file (and the R4/R5 handoffs' §2); `docs/tier4_orchestration_state/decision_log/aws-redeployment-r5-iam_2026-10-25.json` (R5-D4 log-group rule, R5-D6 KMS, F-R5-2); `aws-redeployment-od6-stack-layout-r3_2026-10-22.json` (OD6-r3-parameters: `AdminRoleArn`, F-OD6r3-1 the `/managed/` path); `aws-redeployment-od11-admin-identity-r2_2026-10-21.json`; `deploy/aws/README.md`; `docs/infrastructure_security/evidence_v2/R5/VERIFICATION.md` ("Notes for later tickets"); the v1 key policy `docs/infrastructure_security/evidence/04_kms/kms_key_policy.json` and `CG4_steps.txt` — **as history to be corrected, not as source** (old account, us-east-1, grants the bedrock role that no process used) |
| Decision records in force | as listed in the R5 handoff, plus `aws-redeployment-r4-network_2026-10-24` and `aws-redeployment-r5-iam_2026-10-25` |
| Status | E0, R0–R5 done. Frontier: **R6**, R12a, R9, R9e, R10. R7 waits for R6 (and R4, done); R8 for R6; R11 for R6–R8. |

## 1. Facts that govern R6

| Fact | Record / evidence |
|---|---|
| Account `797661577394`, Free plan, 199.99 USD credits after R5; regional work in **eu-north-1**. KMS is regional: every `kms` and `cloudformation` command names `--region eu-north-1`. | OD1-r1; `evidence_v2/R5/R5_10_plan-state-after.json` |
| R6 fills **`proposal-orchestrator-kms`** (`deploy/aws/templates/30-kms.yaml`, parameters `deploy/aws/parameters/kms.json`: `ExpectedAccountId`, `ExpectedRegion`, `AdminRoleArn` = `arn:aws:iam::797661577394:role/managed/AccountFullAccessRole`, tested against `R1_00_role.json`). | OD6-r3-parameters; `tests/test_aws_iac_contract.py::test_admin_role_is_the_r1_role_arn_with_its_path` |
| Outputs to add, exports `proposal-orchestrator-kms-<Key>`: `KeyArn` (R7, R8, R12a), `KeyId` (R12a), `KeyAliasName` (R12a). | `deploy/aws/outputs_contract.json` |
| **The runtime role decrypts through the key policy, not through an IAM side grant** (ticket R6). R5 left no identity policy granting `kms:*` (`R5_09_deny-kms-identity-grant.json`: `implicitDeny`); the boundary admits `kms:Decrypt` and `kms:DescribeKey` on `arn:aws:kms:eu-north-1:797661577394:key/*`. The key policy must name the **role ARN** (`proposal-orchestrator-iam-RuntimeRoleArn`, imported), which the boundary limits; never the session ARN. | R5-D6; `evidence_v2/R5/R5_08_policy-version-proposal-orchestrator-boundary.json`; IAM user guide, permissions boundaries |
| R5-D6 put any **`kms:ViaService`** narrowing **here**, built with `${AWS::Region}` (`secretsmanager.${AWS::Region}.amazonaws.com` for R8's secret, `s3.${AWS::Region}.amazonaws.com` for R7's CMK-encrypted deploy bucket). | R5-D6 |
| **CloudWatch Logs** scoped to the prefix `/${ProjectName}/` (R5-D4: the flow-log group is `/${ProjectName}/vpc-flow-logs`, created by R7). Per the CloudWatch Logs guide, the principal is `logs.${AWS::Region}.amazonaws.com` (the key's own Region), actions `kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, `kms:Describe*`, condition `ArnLike` `kms:EncryptionContext:aws:logs:arn` = `arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/${ProjectName}/*`. | https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html, read 2026-10-25 |
| **CloudTrail**: per the CloudTrail guide, `kms:GenerateDataKey*` with `StringEquals aws:SourceArn` = the trail ARN **and** `StringLike kms:EncryptionContext:aws:cloudtrail:arn` = `arn:…:cloudtrail:*:<account>:trail/*`; `kms:DescribeKey` with the same `aws:SourceArn`. The guide adds a decrypt statement for named principals (`Null kms:EncryptionContext:aws:cloudtrail:arn` = false); the account root statement already covers the admin through IAM. `aws:SourceAccount` is supported but "not recommended". | https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-kms-key-policy-for-cloudtrail.html, read 2026-10-25 |
| **The trail does not exist yet** (R7), so its name must be fixed now. Register v2 DC-23 names it `proposal-orchestrator-bedrock-trail` (the v1 name). | register v2 DC-23 |
| **Cost.** "Each AWS KMS key that you create in AWS KMS costs $1/month (prorated hourly)"; each of the first two rotations adds $1/month; 20,000 free requests per month. The README and OD6-r3 count the key as "free (key: monthly)". The inherited constraint says nothing billable *by the hour* before R11; a monthly key fee prorated hourly is the case OD6-r3 already accepted, but the operator should acknowledge it explicitly before the change set (see §4). | https://aws.amazon.com/kms/pricing/, read 2026-10-25; `deploy/aws/README.md` stacks table |
| `AWS::KMS::Key` takes `Tags` (project tag required by the guard); `AWS::KMS::Alias` takes none and is already in `UNTAGGABLE_TYPES`. Confirm `AWS::KMS::Key`'s properties (`EnableKeyRotation`, `RotationPeriodInDays`, `PendingWindowInDays`, `KeySpec`, `KeyUsage`, `MultiRegion`, `KeyPolicy`, `Tags`) on its reference page before writing. | `tools/aws_template_guard.py`; CloudFormation reference `aws-resource-kms-key.html` (to read in R6) |
| The account sits in an AWS-managed organization with SCPs (F-OD11r2-2). In us-east-1 they deny regional actions; in eu-north-1 KMS was not denied (F-OD1r1-4). Any IAM simulation must pass `aws:RequestedRegion` and check `AllowedByOrganizations` (R5 step-09 lesson). | OD11-r2, OD1-r1; `evidence_v2/R5/STEPS_fix1.md` |
| Template rules as before: no account or Region literal (`${AWS::AccountId}`, `${AWS::Region}`, `${AWS::Partition}`), project tag, no "temporary"/"validation", ≤ 51,200 bytes; `Metadata.Decision` stays OD6-r3, `Metadata.FillDecision` names R6's record; `SkeletonPlaceholder` removed. | `tools/aws_template_guard.py`; `tests/test_aws_iac_contract.py` |

## 2. How the operator works (additions from R5)

Everything in the R4 and R5 handoffs' §2 holds (PowerShell in VS Code, repository root, `aws login --profile po-r1`, `$E` at the top of every block, `Out-File -Encoding utf8`, `utf-8-sig` on read, the agent's Linux device shell with `cfn-lint` 1.57.2 in `$HOME/.local/bin`, rounds with hand-backs, the operator commits). Measured in R5:

- **The operator runs every AWS step**, also when already signed in; the agent's shell has no AWS credentials. Asked in R5 whether the agent could run steps 01–03: no, by protocol and by construction.
- **AWS CLI v2 exits 254 on a service error** (e.g. "stack does not exist"), not 255; PowerShell wraps long error text inside the file. Write criteria on substrings, not on one-line quotes.
- **`describe-change-set` returns no `ChangeSetType` field.** Evidence the CREATE type by the command line, a "before" lookup and the `Add` entries.
- **IAM simulation includes the organization's SCPs.** Pass `aws:RequestedRegion` for every regional action; require `OrganizationsDecisionDetail.AllowedByOrganizations` = true and the expected `MatchedStatements` in every result. A `simulate-principal-policy` result also carries `PermissionsBoundaryDecisionDetail`.
- **Secret-scan trap.** The scaffold tests' verbose ids, a refused scan's output, and any step-sheet text that quotes a pattern name all write the four pattern names into the scanned folder. In evidence: run pytest with `-q`; run the scan **after** the tests; never quote a pattern name in a `STEPS*.md`. If a scan refuses, remove the refused output files and re-collect (`evidence_v2/R5/STEPS_fix1.md` step 13).
- Policy documents were verified by script: resolve the template's intrinsics with the parameter file, then compare statement by statement (sort by `Sid`). Reuse that for the key policy (`get-key-policy`).
- The operator sometimes runs the next round right away (R5: step 11 before verification). Harmless, but put the scan and test step where its inputs are final.

## 3. R6 as it reads

Ticket exit conditions:

1. **Rotation is on, and the alias resolves to the new key.**
2. **The key policy names the runtime role. No IAM policy grants that role Decrypt separately.**
3. **DC-18 and DC-19 are evidenced.**

What the template must hold (ticket R6, handoff §6 R6, R5-D4, R5-D6):

- **Key**: `AWS::KMS::Key`, symmetric (`SYMMETRIC_DEFAULT`, `ENCRYPT_DECRYPT`), single-Region, `EnableKeyRotation: true`, `Description` without "temporary"/"validation", `Name` and `project` tags, and a key policy with:
  - account root (`arn:${AWS::Partition}:iam::${AWS::AccountId}:root`) `kms:*` — the default that delegates to IAM and prevents a lockout (the admin role then works through its AdministratorAccess);
  - the runtime role (`!ImportValue proposal-orchestrator-iam-RuntimeRoleArn`): `kms:Decrypt`, `kms:DescribeKey`, with `kms:ViaService` per §4;
  - CloudTrail: `kms:GenerateDataKey*` and `kms:DescribeKey`, conditioned as in §1, on the trail name of §4;
  - CloudWatch Logs: as in §1, prefix `/${ProjectName}/`;
  - the admin role, only if §4 decides so.
- **Alias** `alias/${ProjectName}` → the key.
- Three contract outputs with exports.

## 4. Points to settle with the operator before writing the template

- **Cost acknowledgement.** The key is $1/month prorated hourly (plus $1/month for each of the first two rotations, so about $3/month from the second year), paid from credits. Proposal: **(a)** proceed, the operator acknowledging in session that this monthly fee is the "free (key: monthly)" case of OD6-r3, not an hourly-billed resource of the kind R11 gates; record it in R6's decision record. (b) Defer R6 (then R7 and R8 wait too).
- **Trail name.** Proposal: lasting rule `${ProjectName}-bedrock-trail` (register DC-23's name), trail ARN `arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/${ProjectName}-bedrock-trail`; R7 creates exactly that trail. Alternative: `${ProjectName}-trail`.
- **`kms:ViaService` on the runtime role's grant.** Proposal: **(a)** yes, `StringEquals kms:ViaService` = [`secretsmanager.${AWS::Region}.amazonaws.com`, `s3.${AWS::Region}.amazonaws.com`] — the host never calls KMS directly; R8 (secret) and R7/R15 (deploy bucket objects) go through those services. (b) No condition. Note: `DescribeKey` called directly by an SDK would then be refused; nothing in the code path is known to do that — at writing, `runner/` and `deploy/*.sh` contain no `kms` call (grep, 2026-10-25); the agent re-checks before deciding, and R11's live run shows it.
- **An admin statement for `AdminRoleArn`.** The parameter exists since R3. Options: **(a)** keep the root statement as the only administrative grant (the admin role has AdministratorAccess through IAM), and drop `AdminRoleArn` from the KMS stack (template, parameter file, contract test's stack list for that parameter) — DC-19's wording ("root, the runtime role, CloudTrail, CloudWatch Logs only") then holds literally; (b) add an explicit key-administration statement for `AdminRoleArn` (no `kms:Decrypt`), and correct DC-19's wording in register v2. Proposal: (a), simpler and matches the ticket; the agent checks what `test_admin_role_is_the_r1_role_arn_with_its_path` asserts before editing.
- **Retention and deletion.** Proposal: `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` on the key, `PendingWindowInDays: 30`: deleting or replacing the stack must never schedule the deletion of a key that encrypts the trail, the logs and the secret. Consequence: deleting the KMS stack leaves the key (and its monthly fee) until it is scheduled for deletion by hand; the alias goes with the stack. Alternative: no retain.
- **Rotation period.** Proposal: default 365 days (`RotationPeriodInDays` unset or 365). Shorter periods cost more rotations' worth of key material fees only in the first two rotations; no benefit for this workload.
- **Guard and tests.** (a) `tests/test_aws_kms_template.py` in the R5 style: exactly two resources (key, alias); rotation on; symmetric; single-Region; retain policies (if adopted); the key policy's statements and principals exactly as decided, the runtime role only through `Fn::ImportValue`, no `kms:Decrypt` for any principal but the runtime role, CloudWatch Logs and (through `kms:*`) root; conditions as in §1/§4; no Region or account literal; alias `alias/${ProjectName}`; outputs = contract. (b) Nothing new in the template guard unless the reference pages show an untaggable type.
- **How "no IAM policy grants that role Decrypt separately" is evidenced.** Proposal: re-run `list-attached-role-policies` / `list-role-policies` for the runtime role and one IAM simulation of `kms:Decrypt` on the new key ARN **without** a resource policy (expect `implicitDeny`, `AllowedByOrganizations` true, `aws:RequestedRegion` = eu-north-1) — the identity side has no grant; plus `get-key-policy` showing the key-policy grant. Optionally a second simulation passing the key policy via `--resource-policy` and `--resource-owner`/`--caller-arn` as the docs allow, if they allow it for KMS keys (read the `simulate-principal-policy` reference first; if unclear, leave it to R8/R11's live calls).
- **Register v2.** Proposal: DC-18 → `VERIFIED_PASS` (rotation, alias, symmetric CMK); DC-19 → `VERIFIED_PASS` on the policy-level criterion (principals and conditions as decided), with the note that the CloudTrail and CloudWatch Logs grants are exercised in R7 and the runtime grant in R8/R11.

## 5. Step sheet outline (suggestion)

`evidence_v2/R6/STEPS.md`, PowerShell first, rounds as in R5. Say in the header that the key has a monthly fee (the operator's acknowledgement from §4).

1. Session-start check (R1-D2), credits ≥ 199.00; STOP rule.
2. Caller identity.
3. **Read-only lookups:** `aws kms list-aliases --region eu-north-1` → no `alias/proposal-orchestrator` yet (R6 must not collide with an old alias); `aws kms list-keys` (customer-managed keys before; expected none, AWS-managed `aws/*` keys may exist); `describe-stacks proposal-orchestrator-kms` → does not exist (`exit=254`); `list-exports` → the seven `proposal-orchestrator-iam-*` exports present (the import target). Hand back; the agent fills the template, the test, the decision record and steps 04–05.
4. Lint, guards, tests (`-q`) → `R6_04_*`.
5. `create-change-set` (no IAM capability needed; check whether `ImportValue` needs none either), describe → **two `Add`** (key, alias). Hand back; both read it; the operator's go.
6. Execute, wait, status, events.
7. Outputs → `R6_outputs.json`; exports.
8. **Read-only evidence, ids from `R6_outputs.json`:** `describe-key` (symmetric, enabled, customer-managed, single-Region), `get-key-rotation-status` (`KeyRotationEnabled` true, period) → DC-18; `list-aliases --key-id` → alias resolves (exit condition 1); `get-key-policy --policy-name default` → DC-19, compared by script with the template; the runtime role's attached and inline policies (unchanged since R5) → exit condition 2.
9. IAM simulation of the runtime role, `kms:Decrypt` on `KeyArn`, `aws:RequestedRegion` = eu-north-1 → `implicitDeny` on the identity side (exit condition 2); optional resource-policy simulation per §4.
10. Session-end credits.
11. Tests (`-q`), then secret scan, then old-ID guard; commit; confirm.

## 6. Files

| Path | What |
|---|---|
| `deploy/aws/templates/30-kms.yaml` | Filled: key, alias, outputs; `SkeletonPlaceholder` removed; `Metadata.FillDecision` |
| `deploy/aws/parameters/kms.json` | Unchanged, or `AdminRoleArn` removed per §4 (a), with the contract test adjusted |
| `tests/test_aws_kms_template.py` | The R6 shape test |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r6-kms_<date>.json` | The §4 answers; lasting rule: trail name |
| `docs/infrastructure_security/evidence_v2/R6/` | `STEPS.md`, `RUNLOG.md`, `R6_<NN>_<name>`, `R6_outputs.json`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_control_register_v2.md` | DC-18, DC-19 |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | One entry per R6 milestone |
| `deploy/aws/README.md` | "Filled so far" line; the test list |

## 7. Done for R6

Every `VERIFICATION.md` criterion PASS (or N/A with reason); the R3–R6 tests pass with `py -3.10`; the template guard and the old-ID guard are CLEAN; the secret scan of `evidence_v2/R6` is CLEAN (run after the tests); register v2 rows updated; worklog entries; the operator commits and confirms in session. Then tick R6 in `plans/aws_redeployment_tickets.md`. R7 then opens (imports `KeyArn` and `FlowLogsRoleArn`, creates the trail under the §4 name and the flow-log group `/proposal-orchestrator/vpc-flow-logs`); R8 after R6 as well.
