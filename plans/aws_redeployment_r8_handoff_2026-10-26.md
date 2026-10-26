# AWS redeployment: handoff for R8 (runtime secret)

| Field | Value |
|---|---|
| Date | 2026-10-26 |
| Branch at writing | `msca-dn-pre-eval`; R7 committed as `874edeb` (`completed r7`) and confirmed 2026-10-26. The "Close R7" commit — R7 ticked in the tickets file, `evidence_v2/R7/VERIFICATION.md` done conditions, the closing worklog entry, this file — is the operator's to make if `git log` does not show it yet. |
| For | The agent that runs ticket R8 with the operator in a new session |
| Read first | `CLAUDE.md`; `plans/aws_redeployment_tickets.md` (inherited constraints; R8; R9, R9e, R11, R12b for what consumes R8's outputs); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F4, §5 OD8, §6 R8, §7, §7a, §8; §2 of this file (and the R4–R7 handoffs' §2); `docs/tier4_orchestration_state/decision_log/aws-redeployment-operator-decisions_2026-10-21.json` (OD2, OD8); `aws-redeployment-od11-admin-identity-r2_2026-10-21.json`; `aws-redeployment-od6-stack-layout-r3_2026-10-22.json` (OD6-r3-parameters: `AdminRoleArn`, `TransportModelId`); `aws-redeployment-od7-model-set_2026-10-21.json` (OD7-orchestrator); `aws-redeployment-r5-iam_2026-10-25.json` (the runtime role's `RuntimeSecretRead` in its identity policy and its boundary; R5-D6); `aws-redeployment-r6-kms_2026-10-26.json` (R6-D3, R6-D4, R6-D8, R6-D9); `aws-redeployment-r7-audit_2026-10-26.json` (F-R7-7); `deploy/aws/templates/50-secret.yaml`, `deploy/aws/parameters/secret.json`; `runner/transport/config.py` (the presets); `deploy/aws/README.md`; `docs/infrastructure_security/evidence_v2/R5/`, `R6/`, `R7/VERIFICATION.md` ("Notes for later tickets"); the v1 folder `docs/infrastructure_security/evidence/05_secrets_manager/` (`secret_resource_policy.json`, `CG5_steps.txt`, the `EV-SM-*` and `SM-E*` files, partly UTF-16) — **as history to be corrected, not as source** (old account, us-east-1, the bedrock role no process used) |
| Decision records in force | as listed in the R7 handoff, plus `aws-redeployment-r7-audit_2026-10-26` |
| Status | E0, R0–R7 done. Frontier: **R8**, R12a, R9, R9e, R10. R11 waits only on R8. |

## 1. Facts that govern R8

| Fact | Record / evidence |
|---|---|
| Account `797661577394`, Free plan, 199.99 USD credits after R7 (the key's monthly fee had not yet appeared); regional work in **eu-north-1**. Every `secretsmanager`, `kms` and `cloudformation` command names `--region eu-north-1`. | `evidence_v2/R7/R7_10_plan-state-after.json` |
| R8 fills **`proposal-orchestrator-secret`** (`deploy/aws/templates/50-secret.yaml`, parameters `deploy/aws/parameters/secret.json`: `ExpectedAccountId`, `ExpectedRegion`, `AdminRoleArn` = `arn:aws:iam::797661577394:role/managed/AccountFullAccessRole` (with its `/managed/` path, F-OD6r3-1), `TransportModelId` = `eu.anthropic.claude-opus-4-6-v1` (OD7-orchestrator, interim). Both are already checked by `tests/test_aws_iac_contract.py`. | OD6-r3-parameters; R6-D4 (`AdminRoleArn` stays a secret-stack parameter); skeleton |
| Outputs to add, exports `proposal-orchestrator-secret-<Key>`: `SecretArn` (R9, R11, R12a), `SecretName` (R9, R12a). | `deploy/aws/outputs_contract.json` |
| Imports: `proposal-orchestrator-kms-KeyArn` and `proposal-orchestrator-iam-RuntimeRoleArn`; the contract already names R8 among both exports' consumers. | `R6_outputs.json`, `R5_outputs.json`; contract |
| **Secret name** `${ProjectName}/env-config`. Secrets Manager appends `-` and six random characters to the ARN; the runtime role's grant is `arn:${AWS::Partition}:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${ProjectName}/env-config-*`, **`secretsmanager:GetSecretValue` only**, in its identity policy (`RuntimeSecretRead`) and in its boundary. The explicit deny does not cover Secrets Manager. | `20-iam.yaml`; R5 decision record |
| **The key**: `KeyArn` from `R6_outputs.json`. Its policy lets the runtime role `kms:Decrypt` / `kms:DescribeKey` only with `kms:ViaService` = `secretsmanager.eu-north-1.amazonaws.com` (or S3); the admin role uses the key through the root statement's IAM delegation. No key-policy change is planned. | R6-D3, R6-D4; `R6_08_key-policy.json` (unchanged in `R7_03_key-policy-before.json`) |
| **Values** (ticket R8; handoff §6 R8): `ORCHESTRATOR_TRANSPORT_PRESET`, `ORCHESTRATOR_PRODUCTION_MODE=true`, `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata`, `AWS_REGION` (eu-north-1), `ORCHESTRATOR_TRANSPORT_MODEL` (= `TransportModelId`). No credential. | tickets; skeleton description |
| **No EU Converse preset exists yet.** `runner/transport/config.py` has `BEDROCK_CONVERSE_US` (us-east-1, `us.` model) and two mantle `bedrock` EU presets (eu-west-1, API key). R9e (open, reopened 2026-10-21 when OD1 became eu-north-1) adds the EU Converse preset. The preset value R8 stores is therefore a point to settle (§4). | `runner/transport/config.py`; `evidence_v2/R9e/VERIFICATION.md` |
| **CloudFormation `AWS::SecretsManager::Secret`**: omitting both `SecretString` and `GenerateSecretString` creates an empty secret; `KmsKeyId` defaults to `aws/secretsmanager`; `Name` change requires replacement; `Ref` returns the ARN; the page recommends dynamic references and `GenerateSecretString` for passwords. It takes `Tags`. `AWS::SecretsManager::ResourcePolicy` is already in `UNTAGGABLE_TYPES`. Deletion behaviour (recovery window under stack deletion) is not on that page: read the Secrets Manager guide before choosing the deletion policy. | CloudFormation reference, read 2026-10-26 (R7 session); `tools/aws_template_guard.py` |
| **Secret-scan trap.** The name of the secret's value field is one of the four patterns `tools/evidence_secret_scan.py` refuses (case-insensitive). No `STEPS*.md`, `RUNLOG.md`, `VERIFICATION.md` or evidence file in `evidence_v2/R8/` may contain it — not even in a `--query` string. Any step that reads the value must call a script that lives outside the evidence folder and prints only key names and a hash (§4). | `tools/evidence_secret_scan.py`; R5 handoff §2 |
| **The runtime role cannot read the secret before R11.** It trusts `ec2.amazonaws.com` only, and no host exists. R8 evidences DC-20/DC-21 at policy level; the runtime read (and with it R6-D3's Secrets Manager path) is exercised in R11. The IAM simulator does not simulate resource-based policies for roles (F-R7-7), so no simulation of the secret's policy is used either. | `R5_08_runtime-role.json` (trust: EC2 only, DC-13); R6-D8, R6-D9 pattern; F-R7-7 |
| v1: one secret `proposal-orchestrator/env-config` with `alias/proposal-orchestrator`, no rotation, a resource policy allowing `GetSecretValue` and `DescribeSecret` with `Resource: "*"` to two roles (one of which no process used). | `evidence/05_secrets_manager/secret_resource_policy.json`, `EV-SM-002`, `EV-SM-005` |
| Cost: Secrets Manager bills per secret per month, prorated, plus API calls (about 0.40 USD/month and 0.05 USD per 10,000 calls in the 2026-10-21 handoff §8, us-east-1 estimates). The README counts the stack as "free (secret: monthly)". **Verify against the eu-north-1 pricing page before quoting a figure**, and have the operator acknowledge it as R6-D1 did for the key. No hourly cost. | `deploy/aws/README.md`; handoff 2026-10-21 §8 |
| SCPs and AWS-managed RCPs apply (OD11-r2): RCPs can affect Secrets Manager and KMS. A refusal shows as an explicit deny at the change set or at creation. | OD11-r2 known gap |
| Template rules as before (guard, project tag, no literal, ≤ 51,200 bytes, `Metadata.FillDecision`, placeholder removed). Check `AWS::SecretsManager::Secret` and `AWS::SecretsManager::ResourcePolicy` (`BlockPublicPolicy`, `ResourcePolicy`) on their reference pages before writing. | `tools/aws_template_guard.py` |

## 2. How the operator works (additions from R7)

Everything in the R4–R7 handoffs' §2 holds. Measured in R7:

- The operator reports each round as an attached transcript (once pasted as text). Verify from the files on disk only; pasted lines wrap and can lose a space (`--outputjson` again in R7, harmless).
- `.venv-lint` is usually active, also during `py -3.10` steps; the operator ran `deactivate` before the closing step when the sheet asked. Record it in `RUNLOG.md` as a deviation, do not fail it.
- **The agent's device VM may come up without the lint tools.** In R7, `cfn-lint` was missing: `pip install --user pytest pyyaml cfn-lint==1.57.2`, then `export PATH=$HOME/.local/bin:$PATH`. The demo tests need `dotenv`, which the VM lacks; that is not an R8 failure.
- The operator answers settled points as "1–N a" with variants ("2 = 2a igen + 2b (b)"); points added later get their own number and answer, including the go ("17 a, go 06").
- **Agent-side lessons from R7:**
  - Read the reference pages before writing: a property name can differ from the CLI output's (`KMSKeyId` on the trail vs `KmsKeyId` in `describe-trails`), and `Ref` can be documented inconsistently (use `Fn::GetAtt` where the page offers it).
  - Before adding an IAM simulation, check that the simulator supports the case (F-R7-7).
  - A live test of a resource policy by the admin role (R7 step 09) was cheap and closed a known gap before a later ticket depended on it.
  - After editing `VERIFICATION.md` following the operator's scan, re-run the scan yourself and say so in the report.
  - `aws_hardening_control_register_v2.md`'s `## Summary` counts are stale since E0 (R4–R7 updated rows only); leave them to R12b/R13 unless the operator asks.
- `git add .` warns about LF→CRLF on the agent's files; harmless.

## 3. R8 as it reads

Ticket exit conditions:

1. **The secret uses the CMK, and its policy names no principal outside the allowed set.**
2. **Evidence records the key names and metadata only. The E0 scan passes on the folder.**
3. **DC-20 and DC-21 are evidenced or restated.**

## 4. Points to settle with the operator before writing the template

- **Cost.** About 0.40 USD/month (verify on the eu-north-1 pricing page) plus API calls, from credits. Proposal: proceed, as the "free (secret: monthly)" case of OD6-r3, acknowledged like R6-D1.
- **How the values enter the secret.** (a) `SecretString` built in the template with `!Sub` from the parameters and pseudo parameters (a JSON object of the five keys): reproducible from the repository, reviewed in the change set, no credential involved — but the values then sit in the template; (b) an empty secret from CloudFormation, then `put-secret-value` by the operator from a file outside the repository: the value stays out of the template and the stack, but outside IaC and drift detection; (c) `GenerateSecretString` — not applicable (no generated value). Proposal: (a); the values are configuration already present in the parameter file, not credentials.
- **The preset value.** No EU Converse preset exists until R9e. Options: (a) R8 fixes the name now (proposal: `BEDROCK_CONVERSE_EU`, eu-north-1, `eu.` profiles) as a lasting rule that R9e must implement, with a test in R9e that the secret template's preset name exists in `runner/transport/config.py`; (b) no preset key: store `ORCHESTRATOR_TRANSPORT_BACKEND=bedrock_converse` instead, with region and model already explicit; (c) wait for R9e before R8. Proposal: (a) — DC-34 speaks of a preset, R11 does not need the launcher, and R9/R9e land before R12b reads the secret on the host. Note that until R9e exists, a launcher reading the secret fails closed on an unknown preset.
- **Resource policy.** Same-account Allow statements would duplicate R5's identity grant (as in R7-D3). Options: (a) Allow-only, v1 style with new ARNs: the runtime role `GetSecretValue` on `*` (the secret), the admin role `secretsmanager:*`; (b) deny-only: deny every Secrets Manager action to any principal whose `aws:PrincipalArn` is not the runtime role, the admin role or the account root (root kept to avoid a lockout: a deny that also refused root and the admin role's `PutResourcePolicy`/`DeleteResourcePolicy` could make the policy unchangeable), plus a deny of everything but `GetSecretValue` for the runtime role; `BlockPublicPolicy: true` in both. Proposal: (b), with the lockout exceptions checked on the Secrets Manager resource-policy page before writing. Whether `DescribeSecret` is needed by the R9 launcher is R9's to say; R5 grants only `GetSecretValue`.
- **Retention and deletion.** Proposal: `DeletionPolicy: Retain` / `UpdateReplacePolicy: Retain` on the secret (the name cannot be reused while a deleted secret waits out its recovery window, and the host depends on it); the resource policy goes with the stack; the secret stack is not deleted. Read the Secrets Manager guide on deletion and recovery windows first.
- **Rotation and replicas.** Proposal: no rotation (no credential; DC-20 as v1) and no `ReplicaRegions`; tests pin both absences.
- **How "key names and metadata only" is evidenced.** Proposal: `describe-secret` (name, ARN, `KmsKeyId`, no rotation, tags, `VersionIdsToStages`), `get-resource-policy` (compared with the template by script), `list-secrets` filtered by name, and one read of the value by the admin role through a small script in `tools/` (outside the evidence folder) that prints only the sorted key names and a SHA-256 of the canonical JSON, compared by the agent with the hash of the expected object. The script's name and the step's text must not contain the scan's patterns. Alternative: no read of the value at all; key names then rest on the template alone.
- **The runtime read.** Proposal: DC-20 and DC-21 `VERIFIED_PASS` at policy level (as R6-D9 for DC-19), noted "runtime read through `secretsmanager.eu-north-1.amazonaws.com` exercised in R11"; DC-33 to DC-35 stay `NOT_STARTED` (R12b reads them on the host through the R9 launcher), with a note that R8 stores the values.
- **Tests and guard.** `tests/test_aws_secret_template.py` in the R5–R7 style (resources, name, key, Retain, no rotation or replicas, the value object's keys and sources, the policy statements, imports equal the exports whose consumers name R8, outputs equal the contract); guard additions only after the reference pages.
- **Round-1 lookups.** Proposal: the secret name is free (`describe-secret` → `ResourceNotFoundException`, `exit=254`; `list-secrets --include-planned-deletion` shows no `proposal-orchestrator/` secret, since a secret scheduled for deletion still holds the name); the secret stack does not exist; the key is `Enabled` and its policy equals R6's; the network, iam, kms and audit exports (20) with `KeyArn` and `RuntimeRoleArn` as in the outputs files.

## 5. Step sheet outline (suggestion)

`evidence_v2/R8/STEPS.md`, rounds as in R7.

1. Session-start check (R1-D2), credits ≥ 199.00 (the key fee may have started to show; report the figure).
2. Caller identity.
3. **Read-only lookups** (§4 last point). Hand back; the agent fills the template, the test, the decision record and steps 04–05.
4. Lint, guards, tests (`-q`).
5. Change set (no IAM resources: no capability expected) → the agreed `Add` list (secret and resource policy). The change set shows no value; still check `R8_05_*` with the scan. Hand back; the operator's go.
6. Execute; status; events.
7. Outputs → `R8_outputs.json`; exports.
8. Read-only evidence per §4; the resource policy compared by script.
9. (If agreed) key names and hash of the value through the `tools/` script.
10. Session-end credits.
11. Tests, old-ID guard, secret scan last; commit; confirm.

## 6. Files

| Path | What |
|---|---|
| `deploy/aws/templates/50-secret.yaml` | Filled; `SkeletonPlaceholder` removed; `Metadata.FillDecision` |
| `deploy/aws/parameters/secret.json` | Unchanged unless §4 adds a parameter |
| `tests/test_aws_secret_template.py` | The R8 shape test |
| `tools/<script>` | Only if §4 agrees on the key-name and hash read |
| `tools/aws_template_guard.py` | Only if a reference page shows an untaggable type |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r8-secret_<date>.json` | The §4 answers (and the preset-name rule for R9e, if (a)) |
| `docs/infrastructure_security/evidence_v2/R8/` | `STEPS.md`, `RUNLOG.md`, `R8_<NN>_<name>`, `R8_outputs.json`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_control_register_v2.md` | DC-20, DC-21; notes on DC-33–DC-35 |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | One entry per R8 milestone |
| `deploy/aws/README.md` | "Filled so far" line; the test list |
| `plans/aws_redeployment_tickets.md` | R9e: the preset-name rule, if §4 (a) |

## 7. Done for R8

Every `VERIFICATION.md` criterion PASS (or N/A with reason); the R3–R8 tests pass with `py -3.10`; the template guard and the old-ID guard are CLEAN; the secret scan of `evidence_v2/R8` is CLEAN (run after the tests); register v2 rows updated; worklog entries; the operator commits and confirms in session. Then tick R8 in `plans/aws_redeployment_tickets.md`. R11 is then unblocked, and needs the operator's explicit go (the first hourly cost).
