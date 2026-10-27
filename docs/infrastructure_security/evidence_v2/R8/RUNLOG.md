# R8 — run log

| Field | Value |
|---|---|
| Ticket | R8 (runtime secret `proposal-orchestrator/env-config`) |
| Step sheet | `STEPS.md` |
| Kept by | agent (Claude), from the operator's reports in session |

## Settling

| When (UTC, approx.) | Who | What |
|---|---|---|
| 2026-10-26 ~21:25 | agent | Read the R8 handoff and its sources; put the handoff §4 points 1–10 and points 11–16 to the operator |
| 2026-10-26 ~21:30 | operator | "1-16a" |
| 2026-10-26 ~21:32 | agent | Wrote `STEPS.md` round 1. Its first draft named the test as the handoff proposed; the agent's own scan refused it (the name contains one of the four patterns, F-R8-8); renamed to `tests/test_aws_env_config_template.py` before any operator step |

## Round 1 — steps 01–03 (read-only)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| sign-in | 2026-10-26 ~21:50 | operator | VS Code PowerShell, repository root, profile `po-r1` (`.venv-lint` active; no `py` command in this round) | none |
| 01 | 2026-10-26 ~21:50 | operator | Plan FREE / ACTIVE, credits 199.99 USD (the key's monthly fee not yet visible), expiry 2027-04-19; budget spend 0.006 of 10.0; three notifications OK | none |
| 02 | 2026-10-26 ~21:51 | operator | Account 797661577394, assumed-role/AccountFullAccessRole | none |
| 03a–03g | 2026-10-26 ~21:51–21:52 | operator | Secret name free (`ResourceNotFoundException`, `exit=254`); no secret in the Region, scheduled deletions included (`[]`); secret stack does not exist (`exit=254`); key Enabled, policy as R6; admin role `/managed/AccountFullAccessRole`; 23 exports; Price List API `exit=0` | none. PowerShell wrapped the two expected errors in `NativeCommandError` records |
| check | 2026-10-26 ~21:58 | agent | All ten files PASS against `STEPS.md` (device shell, `utf-8-sig`, by script): key policy equal to `R6_08_key-policy.json` by `Sid`; the 23 export values equal the R4–R7 outputs files; prices 0.40 USD per secret, 0.05 USD per 10,000 requests (eu-north-1, publication 2026-09-11, effective 2025-07-01). Secret scan of this folder and old-ID guard CLEAN | — |
| fill | 2026-10-26 ~22:20 | agent | `50-secret.yaml` filled (placeholder removed, `Metadata.FillDecision`); `tests/test_aws_env_config_template.py`; `tools/env_config_digest.py`; decision record `aws-redeployment-r8-secret_2026-10-26`; README; tickets R9e (R8-D3 rule). Agent's run: cfn-lint 1.57.2 exit 0, template guard CLEAN (6), old-ID guard CLEAN, 196 passed (Python 3.10.12). Steps 04–05 added | — |

## Round 1b — steps 04–05 (lint, guards, tests, change set)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 04 | 2026-10-27 ~15:43 | operator | cfn-lint 1.57.2 exit 0; template guard CLEAN (6); old-ID guard CLEAN; Python 3.10.6, 196 passed | `.venv-lint` was active during the `py -3.10` commands (the sheet says to `deactivate` first); harmless, `py -3.10` resolves to the system interpreter |
| 05 | 2026-10-27 15:44:31 | operator | Change set `r8-create-01` `CREATE_COMPLETE` / `AVAILABLE`; `Capabilities` `[]`; tag `project`; five parameters as in `secret.json`; two `Add`: `EnvConfigSecret` (`AWS::SecretsManager::Secret`), `EnvConfigSecretPolicy` (`AWS::SecretsManager::ResourcePolicy`). No configuration value in the file. Scan of the folder CLEAN. The stack now exists in `REVIEW_IN_PROGRESS` with no resources | none |
| check | 2026-10-27 ~15:50 | agent | Steps 04–05 files PASS against `STEPS.md` (device shell, by script) | — |
| go | 2026-10-27 ~15:52 | operator | Go in session ("go") on `R8_05_change-set.json`: two `Add`, as listed. Agent added steps 06–11 to `STEPS.md` | — |

## Round 2 — steps 06–10

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 07–10 (first attempt) | 2026-10-27 15:55:18–15:55:43 | operator | Run **before** step 06, while the stack was still `REVIEW_IN_PROGRESS` with no resources: `R8_outputs.json` `null`; no secret export; imports without the secret stack; `$ARN` empty, so steps 08 and 09 stopped at argument validation (`--secret-id: expected one argument`, `exit=2`) — no Secrets Manager call reached AWS and nothing read the value; `list-secrets` `[]`; credits 199.98 USD | **Order deviation.** These files are not evidence of the created stack; steps 07–10 are re-run in order after step 06 and overwrite them (re-collection, not editing). Secret scan of the folder CLEAN after the attempt |
| 06 | 2026-10-27 15:56:21–15:56:29 | operator | `execute exit=0`; stack `CREATE_COMPLETE`, `capabilities` null, tag `project`; events: `EnvConfigSecret` `CREATE_COMPLETE` 15:56:27, `EnvConfigSecretPolicy` `CREATE_COMPLETE` 15:56:28, stack `CREATE_COMPLETE` 15:56:29; no failure, no rollback (`BlockPublicPolicy` accepted the deny-only policy; no RCP refusal) | none |
| 06 (repeat) | 2026-10-27 ~16:00 | operator | Step 06's block run a second time before re-running 07–10: `execute-change-set` refused with `InvalidChangeSetStatus` (`EXECUTE_COMPLETE`), `execute exit=254`; `describe-stacks` and `describe-stack-events` re-read: `CREATE_COMPLETE`, same nine events (create `User Initiated` 15:56:21, both resources `CREATE_COMPLETE`, no failure) | **Deviation.** `R8_06_execute-exit.txt` now holds the refused repeat, not the first run's `execute exit=0` (that run is recorded in the row above, from the session transcript). Nothing was created or changed by the repeat. Settled as point 17 |
| 07–10 (in order) | 2026-10-27 ~16:00 | operator | Two outputs (`SecretArn` `…/env-config-KTsWow`, `SecretName`); both exports; the secret stack imports `kms-KeyArn` and `iam-RuntimeRoleArn`; `describe-secret` with `KmsKeyId` = `KeyArn`, no rotation, no replica, one `AWSCURRENT` version; resource policy read back; `env_config_digest`: five keys, `sha256` `MATCH`, `exit=0` (the admin role's read was not denied); credits 199.98 USD | Re-collection after the first attempt; files overwritten as planned. `.venv-lint` active during step 09's `py -3.10` (harmless) |
| check | 2026-10-27 ~16:05 | agent | All round-2 files checked by script: stack events without failure; outputs and exports as the contract; `SecretArn` matches `…/env-config-` + six characters; the live resource policy equals the template resolved (four statements by `Sid`, lists order-insensitive; imports from `R8_03_exports.json`, the admin ARN with and without `/managed/`); no configuration value in any evidence file; secret scan CLEAN | — |

## Round 3 — step 11 (closing)

| Step | UTC (approx.) | Who | Result | Deviation / error |
|---|---|---|---|---|
| 11 | 2026-10-27 ~16:10 | operator | Python 3.10.6, 196 passed; old-ID guard CLEAN; secret scan CLEAN (run last) | `.venv-lint` active during `py -3.10` (harmless) |
| check | 2026-10-27 ~16:12 | agent | Step 11 files PASS; `VERIFICATION.md` completed (every criterion PASS); agent re-ran the secret scan and the old-ID guard after this edit: CLEAN | — |
