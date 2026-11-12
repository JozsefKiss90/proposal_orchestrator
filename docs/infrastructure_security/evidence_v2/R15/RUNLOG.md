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
| 2026-11-12 | operator | **Go for round 2**, in session: "go for round 2". Given after the expected cost (about 0.60 USD, upper bound about 2.05 USD) was stated. Covers one creation of the host stack, steps 06–15 |

## Runs

| Step | When (UTC) | Who | Result | Deviation |
|---|---|---|---|---|
| 01 | 2026-11-12 | operator | PASS. FREE / ACTIVE to 2027-04-19, credits 199.19 USD; one budget, 0.567 of 10 USD; ACTUAL 85, ACTUAL 100, FORECASTED 100, all `OK`; account 797661577394, `AccountFullAccessRole` | R15-D1 |
| 02 | 2026-11-12 | operator | PASS. Host stack absent (`exit=254`); only the S3 gateway endpoint of R4, `available`; no instance, no project volume; base stacks equal `R14_02_base-stacks.json` (checked by script); secret `changed` equals `R8_08_describe-secret.json`, one `AWSCURRENT` version; `bundles/` count 0 | R15-D1 |
| 03 | 2026-11-12 | operator | PASS. Tag and branch both `17e32d54`; tarball sha256 `9c5351ef…132a`, 92,413,570 bytes, `.sha256` file agrees; manifest `04f8218f…19dd`; guard `CLEAN`, `exit=0`; Python 3.10.6, `258 passed, 1 skipped`; plan `exit=0`, 29 `aws` lines, all ending with Region and profile | R15-D1: the count was not stated beforehand |
| 04 | 2026-11-12 | operator | PASS. Both `cp_exit=0`; tarball 92,413,570 and `.sha256` 100 bytes; both `aws:kms` with the R6 `KeyArn` (checked by script), bucket key on, a version each | R15-D1 |
| 05 | 2026-11-12 16:21:34 | operator | PASS. R14's CloudShell files removed; `caller_account=797661577394`, `region=eu-north-1`; script `5fe74934…a44f` (the F-R14-2 fix), template `d21723cb…771c`, parameters `3847dada…f58f7b`, all as stated; `RESULT=ready`. AWS CLI 2.39.6 in CloudShell | — |
| 06 | 16:59:14–17:02:43 | operator | PASS. Stack `ABSENT`, `path=create`; change set seven `Add`, `c7i-flex.large`; `confirmed=create` on the first prompt; **executed 17:00:54** (charges start); `CREATE_COMPLETE`; seven outputs; ping `Online` at try 0, Amazon Linux 2023 | Typed-ahead test not reported (R15-D4) |
| 07 | 17:07:22 | operator | PASS. Both `cp` exit 0; 92,413,570 bytes; sha256 `9c5351ef…132a`, equal to O5; `sha256sum_check=OK`. The host read `bundles/` (R5-D2 holds) | — |
| 08 | 17:10:03 | operator | PASS. `tar_exit=0`, `install_exit=0`; `SHA256SUMS` 17 OK, 0 failed; `Python 3.11.16`; `all 299 files match the manifest`; 281,836 KB installed | — |
| 09 | 17:10:48 | operator | PASS. Probe `pypi.org:443` (no fallback); `verify_exit=0`; all 11 checks `true`; glibc 2.34 measured; `bedrock-runtime` resolves to a private address; `pypi.org:443 unreachable`; manifest `04f8218f…19dd`, revision `17e32d54` | — |
| 10 | 17:11:42 | operator | PASS. `launcher_exit=0`; the five key names; sha256 `1306b991…318a`, `sha256_matches_template=yes` (DC-33–35) | — |
| 11 | 17:12:28 | operator | PASS. `prepare_exit=0`; tag `bedrock-converse-eu-north-1@2026-11-12`; revision `17e32d54`; rendered request Sonnet 4.6 `eu.` profile, temperature 0.0, `max_tokens` 2048, no tool config, `eu-north-1`; the 13 placeholders; `draft_as_expected=yes` | — |
| 12 | 17:12:49 | operator | PASS. `placeholders_left=none`; receipt `e3aa19c8…6be9`, mode 600; `receipt green` | — |
| 13 | 17:13:16–17:14:54 | operator | PASS. `assess_exit=0`, `receipt green`; one report; checkpoint 25 lines; two baseline files (`.json` 70,304 bytes, `.freeze.json` 6,401 bytes); receipt unchanged; `check_exit=0`, `receipt green`. 1.5 minutes of the 60 allowed | — |
| 14 | 17:19:52–17:24:07 | operator | PASS. `confirmed=delete` on the first prompt; **delete issued 17:19:59** (charges end); `RESULT=deleted`; stack `does not exist`; only the S3 gateway endpoint; no ENI, instance or volume; `base_stacks_complete=5`, names equal step 02. The CloudShell teardown ran to its last line (closes R14-D5) | Typed-ahead test not reported (R15-D4) |
| 15 | 17:27:34 | operator | PASS with deviations. 26 `Converse` events, all with the stated Region, caller, issuer, endpoint and model; 24 without error, 2 `ThrottlingException` (17:14:06, 17:14:25) | R15-D2, R15-D3 |

Secret scan over `R15/` after steps 01–04 (agent): `CLEAN`. After steps 06–15 (agent): `CLEAN`.

Host stack lifetime: executed 17:00:54, delete issued 17:19:59, gone by 17:24:07 UTC. About 0.39 hours,
at most 0.06 USD at the running rate.

## Notes

- **R15-D1. Steps 01–04 ran before round 0 and before points 1–8 were answered.** None of the four
  steps uses a round 0 file, so their evidence stands. Step 03's test list lacks the sender's test file
  and its count was not stated in advance. The agent accepts `258 passed, 1 skipped` as the baseline for
  this list. Step 16 reruns the list with the sender's tests added. Step 04 put the bundle in the deploy
  bucket, as point 2 proposes. If the operator answers point 2 with "no", the bundle is removed at the
  end of R15.
- **R15-D2. Step 15 ran early.** The lookup ran at 17:27:34, 12 minutes 40 seconds after
  `assess_done_utc` (17:14:54). The step asks for at least 15 minutes. The lookup still found 24
  successful calls. That equals the checkpoint's 24 responses (25 lines, one of them the header). The
  agent asks the operator to rerun step 15 once, overwriting the file. The rerun calls nothing billable.
- **R15-D3. Two `Converse` calls were throttled.** At 17:14:06 and 17:14:25 Bedrock answered
  `ThrottlingException`. The step 15 criterion asks for `errorCode` null on every event, so these two
  events miss it. The transport marks throttling retryable. The retry wrapper of
  `harness/judge_factory.py` waited and retried; the Converse route is unpaced and allows 6 retries. All 24 calls then succeeded. Every one of the 26
  events has the stated Region, caller, issuer, endpoint and model, so DC-26 holds. Finding F-R15-1.
- **R15-D4. The typed-ahead tests were not reported.** The operator's console shows `create` and
  `delete` typed at their prompts and accepted first time. It does not show whether Enter was pressed
  twice while each script worked. The agent asks the operator whether it was. Until then, the R14
  known gap on the input discard (F-R14-2) stays open.

## Expected cost of round 2 (stated by the agent before the go)

| Item | Planned | Upper bound | Basis |
|---|---|---|---|
| Host stack, steps 06–14 | 1.0 h, 0.15 USD | 2.0 h, 0.31 USD | 0.154686 USD per running hour (`R14_05_cost-check/report.json`). Create and teardown took about 10 and 5 minutes at R14; step 13 is capped at 60 minutes (point 7) |
| Bedrock input tokens, step 13 | about 15,000 tokens, 0.05 USD | 30,000 tokens, 0.10 USD | 24 Converse calls and about 48,000 characters sent, measured by running the pass against the fake client of `tests/harness/test_converse_smoke.py`; 3.3 USD per 1M tokens |
| Bedrock output tokens, step 13 | about 24,000 tokens, 0.40 USD | 24 × 4,096 tokens, 1.62 USD | 16.5 USD per 1M tokens. 4,096 is the transport's default `maxTokens`; step 11 records the value the host uses. Retries of malformed answers would add calls |
| **Round 2** | **about 0.60 USD** | **about 2.05 USD** | Budget: 0.567 of 10 USD spent at step 01; credits 199.19 USD |
