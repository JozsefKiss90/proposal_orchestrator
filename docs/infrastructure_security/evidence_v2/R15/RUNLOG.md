# R15 — run log

| Field | Value |
|---|---|
| Ticket | R15 (host install and Converse smoke run, rescoped 2026-11-11) |
| Step sheet | `STEPS.md` |
| Kept by | agent (Claude), from the operator's reports in session |

## Settling

| When (UTC, approx.) | Who | What |
|---|---|---|
| 2026-11-12 | agent | `STEPS.md` written. Points 1–8 wait for the operator; 9–12 for confirmation on review. Round 0 (the Run Command sender, six host scripts, the DC-33–35 vars file, tests) not started. No hourly-cost go given |
| 2026-11-12 | operator | "points 1–8 accepted". Points 9–12 stand as the agent decided them, open to change on review |
| 2026-11-12 | agent | Round 0 done (after steps 01–05, R15-D1). `deploy/aws/scripts/host-run.ps1`; `host/r15_07_fetch.sh`, `r15_08_install.sh`, `r15_09_verify.sh`, `r15_11_prepare.sh`, `r15_12_receipt.sh`, `r15_13_assess.sh`; `host/dc33_35.vars.json`; `tests/test_aws_host_run_script.py` (31 passed); `tests/fixtures/fake_aws_lifecycle.py` now records `file://` contents. Step 03 list plus the new file: `289 passed, 1 skipped`. Step 05 hashes unchanged. Secret scan and old-ID guard `CLEAN` |
| 2026-11-12 | agent | Expected cost of round 2, stated before the go (below). No go given yet |

## Runs

| Step | When (UTC) | Who | Result | Deviation |
|---|---|---|---|---|
| 01 | 2026-11-12 | operator | PASS. FREE / ACTIVE to 2027-04-19, credits 199.19 USD; one budget, 0.567 of 10 USD; ACTUAL 85, ACTUAL 100, FORECASTED 100, all `OK`; account 797661577394, `AccountFullAccessRole` | R15-D1 |
| 02 | 2026-11-12 | operator | PASS. Host stack absent (`exit=254`); only the S3 gateway endpoint of R4, `available`; no instance, no project volume; base stacks equal `R14_02_base-stacks.json` (checked by script); secret `changed` equals `R8_08_describe-secret.json`, one `AWSCURRENT` version; `bundles/` count 0 | R15-D1 |
| 03 | 2026-11-12 | operator | PASS. Tag and branch both `17e32d54`; tarball sha256 `9c5351ef…132a`, 92,413,570 bytes, `.sha256` file agrees; manifest `04f8218f…19dd`; guard `CLEAN`, `exit=0`; Python 3.10.6, `258 passed, 1 skipped`; plan `exit=0`, 29 `aws` lines, all ending with Region and profile | R15-D1: the count was not stated beforehand |
| 04 | 2026-11-12 | operator | PASS. Both `cp_exit=0`; tarball 92,413,570 and `.sha256` 100 bytes; both `aws:kms` with the R6 `KeyArn` (checked by script), bucket key on, a version each | R15-D1 |
| 05 | 2026-11-12 16:21:34 | operator | PASS. R14's CloudShell files removed; `caller_account=797661577394`, `region=eu-north-1`; script `5fe74934…a44f` (the F-R14-2 fix), template `d21723cb…771c`, parameters `3847dada…f58f7b`, all as stated; `RESULT=ready`. AWS CLI 2.39.6 in CloudShell | — |

Secret scan over `R15/` after steps 01–04 (agent): `CLEAN`.

## Notes

- **R15-D1. Steps 01–04 ran before round 0 and before points 1–8 were answered.** None of the four
  steps uses a round 0 file, so their evidence stands. Step 03's test list lacks the sender's test file
  and its count was not stated in advance. The agent accepts `258 passed, 1 skipped` as the baseline for
  this list. Step 16 reruns the list with the sender's tests added. Step 04 put the bundle in the deploy
  bucket, as point 2 proposes. If the operator answers point 2 with "no", the bundle is removed at the
  end of R15.

## Expected cost of round 2 (stated by the agent before the go)

| Item | Planned | Upper bound | Basis |
|---|---|---|---|
| Host stack, steps 06–14 | 1.0 h, 0.15 USD | 2.0 h, 0.31 USD | 0.154686 USD per running hour (`R14_05_cost-check/report.json`). Create and teardown took about 10 and 5 minutes at R14; step 13 is capped at 60 minutes (point 7) |
| Bedrock input tokens, step 13 | about 15,000 tokens, 0.05 USD | 30,000 tokens, 0.10 USD | 24 Converse calls and about 48,000 characters sent, measured by running the pass against the fake client of `tests/harness/test_converse_smoke.py`; 3.3 USD per 1M tokens |
| Bedrock output tokens, step 13 | about 24,000 tokens, 0.40 USD | 24 × 4,096 tokens, 1.62 USD | 16.5 USD per 1M tokens. 4,096 is the transport's default `maxTokens`; step 11 records the value the host uses. Retries of malformed answers would add calls |
| **Round 2** | **about 0.60 USD** | **about 2.05 USD** | Budget: 0.567 of 10 USD spent at step 01; credits 199.19 USD |
