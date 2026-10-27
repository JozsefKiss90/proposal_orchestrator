# AWS redeployment: handoff for R9e (EU region support)

| Field | Value |
|---|---|
| Date | 2026-10-27 |
| Branch at writing | `msca-dn-pre-eval`; R9 committed and closed as `d1e767b` (`close R9`), confirmed 2026-10-27. This file is the operator's to commit if `git log` does not show it yet. |
| For | The agent that runs ticket R9e with the operator in a new session |
| Read first | `CLAUDE.md`; `plans/aws_redeployment_tickets.md` (inherited constraints; R9e; R9's note; R15, R13 for what consumes R9e); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F4, F9, §5 OD1, §6 R9e, §7, §7a; §2 of this file and of the R4–R9 handoffs; decision records `aws-redeployment-od1-region-r1_2026-10-21` (OD1-r1), `aws-redeployment-od7-model-set_2026-10-21` (OD7-orchestrator, OD7-an12, OD7-assessor, OD7-global), `aws-redeployment-r8-secret_2026-10-26` (R8-D2, R8-D3), **`aws-redeployment-r9-runtime-config_2026-10-27` (all of it, above all `for_r9e`, R9-D3, R9-D6, R9-D7, R9-D15, R9-D21–D23, F-R9-1, F-R9-2, F-R9-5, F-R9-7)**; `docs/infrastructure_security/evidence_v2/R9/VERIFICATION.md` (the baseline failure set) and `RUNLOG.md` (the agent's git incident); `docs/infrastructure_security/evidence_v2/R9e/VERIFICATION.md` (the superseded N/A closing); `runner/transport/config.py`, `runner/host_env.py`, `runner/anonymisation_rewrite.py` (`ALLOWED_REGIONS`), `runner/anonymisation_attack.py`, `runner/offline_bundle.py` (`_region`, `_private_endpoint`), `runner/model_ids.py`, `harness/judge.py` (`drafter_models`), `harness/commands/_converse_judge.py`, `harness/commands/converse_smoke.py`, `tools/anonymisation_host_smoke.py`; `deploy/aws/templates/50-secret.yaml`; `plans/msca_dn_an12_host_runbook.md` (Part 2 step 7, Part 3, Part 4) and `tests/test_anonymisation_host_runbook.py`; `tests/test_transport_presets.py`, `tests/test_transport_config.py`, `tests/test_host_env_launcher.py`, `tests/test_aws_env_config_template.py`, `tests/harness/test_converse_judge.py` |
| Decision records in force | as listed in the R9 handoff, plus `aws-redeployment-r9-runtime-config_2026-10-27` |
| Status | E0, R0–R9 done. Frontier: **R9e**, R10, R12a. R11 is unblocked and needs the operator's explicit go (first hourly cost). R15 needs R9e. |

## 1. Facts that govern R9e

| Fact | Record / evidence |
|---|---|
| **R9e is code (and one runbook) only.** No AWS step, no resource, no cost. Evidence is test output and the repository diff, as in R9. | ticket R9e; R9 precedent |
| **The preset name is fixed:** `BEDROCK_CONVERSE_EU`, backend `bedrock_converse`, default Region eu-north-1, `eu.` profiles; a test asserts that the name stored by `deploy/aws/templates/50-secret.yaml` exists in `runner/transport/config.py`. The secret stores it (line 80 of the template, inside an `!Sub` string). | R8-D3; ticket R9e criterion 1 |
| **The R9 launcher refuses the real secret until the preset exists and is production-suitable with a backend in `PRODUCTION_BACKENDS`** (R9-D3). `tests/test_host_env_launcher.py::TestTheRealSecretsPreset` flips automatically once the preset exists; it must then pass on the accepting branch. | R9-D3; `runner/host_env.py` `_preset_problem` |
| **Production mode requires `AWS_REGION`** on both resolution paths and at build; outside production a Converse preset's `default_region` applies (R9-D6). The new preset's `default_region` therefore matters only off the host. `PRODUCTION_BACKENDS = {"bedrock_converse"}` (R9-D7). | R9 record |
| **`test_registry_count` fails today** (expects 6, registry has 7) and is in the R9 baseline set; R9 left it to R9e (R9-D22, F-R9-2). Adding the preset makes 8. | R9 `VERIFICATION.md` |
| **Region-fixed transport tests (criterion 2)**, as read 2026-10-27: `tests/test_transport_config.py` lines ~103/111 and `tests/test_transport_presets.py` lines ~298/303 (an explicit mantle endpoint with `us-east-1` in the URL); `BEDROCK_EU_DEVELOPMENT`/`BEDROCK_EU_PRODUCTION` tests pin `eu-west-1` as the presets' own value; `tests/test_bedrock_env_readiness.py` uses `eu-central-1`/`eu-west-1`. The R9 tests use sentinel Regions or the preset's own attribute. Re-grep before deciding what "fixes the region" covers (§4). | grep 2026-10-27 |
| **`ALLOWED_REGIONS = ("eu-west-1", "us-east-1")`** in `runner/anonymisation_rewrite.py`, labelled "ADR-001: Bedrock only in these regions". Consumers: `anonymisation_rewrite.build_converse_backend`, `anonymisation_attack.build_converse_backend`, `offline_bundle._region` and `_private_endpoint`, `tools/anonymisation_host_smoke.py --region`, `harness/commands/converse_smoke.py`. eu-north-1 is in none, so R15 (AN12 on the host) cannot run until R9e changes it. ADR-001's own amendment for the new Region (A2) is R13's, after R12b. | code read 2026-10-27; tickets R13, R15 |
| **The AN12 runbook** (`plans/msca_dn_an12_host_runbook.md`): Part 2 step 7 exports `ORCHESTRATOR_PRODUCTION_MODE`, `ORCHESTRATOR_DIAGNOSTIC_LEVEL`, `ORCHESTRATOR_TRANSPORT_BACKEND=bedrock_converse`, `AWS_REGION=us-east-1` by hand; Part 3 says "Use `us.anthropic.claude-*` inference profiles or bare `anthropic.claude-*` ids in `us-east-1`" and runs `--region us-east-1`; Part 4 uses `--assessor-version bedrock-converse-us-east-1@<YYYY-MM-DD>`. `tests/test_anonymisation_host_runbook.py` parses every `python -m` line with the module's own parser, checks required flags and cited paths. | runbook; F9 |
| **OD7 for the host:** A3 `eu.anthropic.claude-sonnet-4-6`, A5 `eu.anthropic.claude-opus-4-6-v1` (must differ); orchestrator/drafter `eu.anthropic.claude-opus-4-6-v1` (interim, target Opus 5); assessor `eu.anthropic.claude-sonnet-4-6`, version tag naming `bedrock-converse` and eu-north-1; `global.` profiles excluded and denied. | OD7 record |
| **AN1c guard (OD7-assessor consequence: "R9e checks this").** `harness/judge.py::drafter_models()` returns only the CLI constants `skill_runtime.SKILL_MODEL` and `semantic_dispatch.AGENT_MODEL`; on the host the drafter is `ORCHESTRATOR_TRANSPORT_MODEL` from the secret, which the guard does not see. **Trap:** on the workstation `.env.harness` puts the *judge's* model into `ORCHESTRATOR_TRANSPORT_MODEL` (the harness speaks to the judge through the same variables), so naively adding that variable to `drafter_models()` would make every workstation judge fail its own independence check. | `harness/judge.py`; `harness/commands/_common.py`; F-R9-1 |
| **`harness/commands/converse_smoke.py`** still reads `AWS_REGION` or `AWS_DEFAULT_REGION` (F-R9-7); its error text and `_converse_judge.py`'s example tag name `eu-west-1`. | R9 `for_r9e` |
| **Full suite.** The R9 baseline (202 failed on `8c20087`) and the R9 after-run (201 failed) are by id in `evidence_v2/R9/`; the suite makes outbound HTTP requests and is order-dependent (F-R9-1), so exit condition "no new failures" is judged by id as in R9-D23. A new baseline on `d1e767b` is still the clean reference. | R9 evidence |
| `CLAUDE.md` §17 governs `runner/`; R9e changes configuration data and region lists, not the call graph, contracts or failure semantics. No ticket amends `CLAUDE.md`. | tickets inherited constraints |

## 2. How the operator works (additions from R9)

Everything in the R4–R9 handoffs' §2 holds. Measured in R9:

- The operator answers "1–N a"; new points get new numbers. He ran each block as asked; `.venv-lint` was active in steps 04–05 (recorded as a deviation).
- The full suite takes 12–18 minutes on the workstation; split it into its own step.
- **Agent-side lessons from R9:**
  - **Never run a git command that writes (`stash`, `checkout`, `reset`, `commit`) in the connected folder.** Deletion is not permitted there, so git leaves `.lock` files and half-applied state (R9 `RUNLOG.md`). To compare old and new code, export HEAD with `git archive HEAD | tar -x -C $HOME/<dir>` (read-only) and overlay the changed files in a VM copy.
  - The device VM can host a test venv: `uv venv $HOME/r9venv --python 3.10` and `uv pip install python-dotenv==1.2.2 boto3==1.42.68 pytest httpx pyyaml jsonschema`. PyMuPDF is absent, so `test_offline_bundle.py::TestTheBundleIsSelfSufficient::test_both_host_smokes_run_from_the_bundled_roots_alone` fails there only.
  - Tests over the mounted folder are slow (file-heavy fixtures; a device call is capped at ~180 s and background processes die with it); run large sets in the VM copy.
  - Editing a file on the device writes LF where the Windows working copy has CRLF; git normalises on commit, but the operator sees `LF will be replaced by CRLF` warnings. Either preserve CRLF on write or say so in the step sheet.
  - Run the secret scan on every draft; naming one of the scan's patterns, even in prose, is a finding (F-R9-5).

## 3. R9e as it reads

1. **An EU Converse preset exists and is tested** — `BEDROCK_CONVERSE_EU` (backend `bedrock_converse`, default Region eu-north-1, `eu.` profiles), with a test that the preset name stored by `50-secret.yaml` exists in `runner/transport/config.py`.
2. **No transport test fixes the region.**
3. **The runbook guard test passes on the edited runbook** (region lines and id rule).

## 4. Points to settle with the operator before writing code

- **Preset definition.** Default model: (a) none — the model comes only from `ORCHESTRATOR_TRANSPORT_MODEL` (the secret supplies it on the host; with no model, `build_converse_backend` refuses); (b) `eu.anthropic.claude-opus-4-6-v1` (OD7-orchestrator, interim); (c) `eu.anthropic.claude-sonnet-4-6`. Proposal: (a) — the model is the secret's (R8-D2) and will change (OD7 target), so a preset default would go stale silently. `production_suitable=True`, capabilities `CAPABILITIES_REGISTRY["bedrock_converse"]`, notes citing OD1-r1, OD7-global (no `global.`), R8-D3.
- **The secret-name test.** Where and how: a test that reads `50-secret.yaml` with the CloudFormation loader already used by `tests/test_aws_env_config_template.py`, extracts `ORCHESTRATOR_TRANSPORT_PRESET` from the `!Sub` JSON, and asserts it is in `PRESET_REGISTRY` and production-suitable. Proposal: in `tests/test_aws_env_config_template.py` (it already owns the template), plus the launcher test's accepting branch.
- **`test_registry_count`.** (a) Replace the count with the exact set of preset names; (b) update to 8. Proposal: (a), so the next preset changes one line that names it.
- **What criterion 2 covers.** Proposal: no test may assert that a *Converse* Region, or the Region the production path uses, is a particular literal; tests read Regions from the preset's attribute or use sentinels. The mantle-endpoint override tests (an explicit URL echoed back) and the eu-west-1 assertions about the mantle presets' own values are not "fixing the region" of the transport, but the agent proposes neutral URLs for the override tests anyway. Re-grep for `us-east-1`, `eu-west-1`, `eu-central-1` in `tests/test_transport_*`, `tests/test_production_mode.py`, `tests/test_bedrock_env_readiness.py` first.
- **`ALLOWED_REGIONS`.** (a) Add eu-north-1: `("eu-north-1", "eu-west-1", "us-east-1")`, comment citing OD1-r1 until ADR-001 A2 (R13); (b) replace with `("eu-north-1",)` only — strongest residency, but every anonymisation, offline-bundle and smoke test using eu-west-1 changes; (c) leave to R13 — blocks R15. Proposal: (a), with R13's A2 deciding whether to narrow; the decision record says the code runs ahead of the ADR text on OD1-r1's authority.
- **Runbook step 7 and the launcher.** (a) Each host `python -m …` line that needs the configuration is prefixed by `python -m runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config --` (no exports; the guard test must parse through the prefix); (b) one launcher call starts a shell (`-- bash`) and the steps run inside it; (c) keep `export` lines with corrected values. Proposal: (a) — no value in a shell, matching R9-D1; the guard test learns the prefix. Check which steps actually read the environment (`offline_bundle verify` does; the smoke tools take `--region` and model ids as flags).
- **Runbook region lines and id rule.** `--region us-east-1` → `eu-north-1`; the id rule becomes "`eu.anthropic.claude-*` inference profiles in eu-north-1; never `global.` (OD7-global)"; the assessor tag becomes `bedrock-converse-eu-north-1@<YYYY-MM-DD>`. Model ids: placeholders as today, with OD7-an12's ids named in the text. Proposal: so.
- **AN1c guard on the host.** (a) `drafter_models()` adds `ORCHESTRATOR_TRANSPORT_MODEL` only when `ORCHESTRATOR_PRODUCTION_MODE=true` (the host; the workstation's `.env.harness` judge model is never production); (b) a dedicated variable for the drafter — would add a sixth key to the secret (R8-D2 change, stack UPDATE); (c) R9e only documents the gap and R15 checks the ids by hand. Proposal: (a), with tests for both modes, including that the workstation judge stays independent. Confirm first how the assessor runs on the host (through the launcher, so production mode is on).
- **`converse_smoke.py` Region source (F-R9-7).** Proposal: `AWS_REGION` only, as R9-D8 did for `verify`; fix the example tags that name eu-west-1 where they are user-facing advice.
- **Evidence.** As R9: `evidence_v2/R9e/` with a new `STEPS.md` (the 2026-10-21 `VERIFICATION.md` is superseded; keep it as history, write the new one beside or replace it — operator's choice), baseline full suite on `d1e767b`, the R9e tests, the full suite after (by id, R9-D23), old-ID guard, scan last. No register row (R9e touches no control) unless the operator wants a DC-16 note (approved Regions).
- **What R9e does not do.** Documents other than the AN12 runbook (R13); the evidence collector's Region (R12a); the test-isolation follow-up (F-R9-1, its own ticket); R10's drafter path.

## 5. Step sheet outline (suggestion)

`evidence_v2/R9e/STEPS.md`, workstation only.

1. Baseline: `git log -1` shows `d1e767b` (or the commit of this handoff); full suite → `R9e_01_baseline-pytest.txt`. Hand back.
2. The agent writes the preset, the tests, the region list, the runbook and guard-test changes, the AN1c change and the decision record `aws-redeployment-r9e-eu-region_<date>`; runs its subset in the VM copy.
3. Diff stat; R9e tests and the touched modules (transport, launcher, anonymisation, offline bundle, runbook guard, judge) → `R9e_03_*`.
4. Full suite after → `R9e_04_full-pytest.txt`, compared by id.
5. Old-ID guard; secret scan last. Commit; confirm.

## 6. Files (expected)

| Path | What |
|---|---|
| `runner/transport/config.py` | `BEDROCK_CONVERSE_EU` |
| `runner/anonymisation_rewrite.py` | `ALLOWED_REGIONS` |
| `harness/judge.py` | AN1c drafter model on the host (§4) |
| `harness/commands/converse_smoke.py`, `harness/commands/_converse_judge.py` | Region source; example tags |
| `plans/msca_dn_an12_host_runbook.md` | step 7, Part 3 region and id rule, Part 4 tag |
| `tests/test_transport_presets.py`, `tests/test_transport_config.py`, `tests/test_aws_env_config_template.py`, `tests/test_anonymisation_host_runbook.py`, `tests/harness/test_converse_judge.py` (+ others the grep finds) | tests |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r9e-eu-region_<date>.json` | the §4 answers |
| `docs/infrastructure_security/evidence_v2/R9e/` | `STEPS.md`, `RUNLOG.md`, `R9e_<NN>_*`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | entries |
| `plans/aws_redeployment_tickets.md` | R9e ticked |

## 7. Done for R9e

Every `VERIFICATION.md` criterion PASS; the three ticket criteria PASS; the full suite shows no failure that is not in the R9e baseline (by id); `tests/test_host_env_launcher.py` passes with the launcher accepting `BEDROCK_CONVERSE_EU`; old-ID guard and secret scan CLEAN (scan last); worklog entry; the operator commits and confirms. Then tick R9e. R15 then needs R11 and R12b.
