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

## Runs

| Step | When (UTC) | Who | Result | Deviation |
|---|---|---|---|---|
| 01 | 2026-11-12 | operator | PASS. FREE / ACTIVE to 2027-04-19, credits 199.19 USD; one budget, 0.567 of 10 USD; ACTUAL 85, ACTUAL 100, FORECASTED 100, all `OK`; account 797661577394, `AccountFullAccessRole` | R15-D1 |
| 02 | 2026-11-12 | operator | PASS. Host stack absent (`exit=254`); only the S3 gateway endpoint of R4, `available`; no instance, no project volume; base stacks equal `R14_02_base-stacks.json` (checked by script); secret `changed` equals `R8_08_describe-secret.json`, one `AWSCURRENT` version; `bundles/` count 0 | R15-D1 |
| 03 | 2026-11-12 | operator | PASS. Tag and branch both `17e32d54`; tarball sha256 `9c5351ef…132a`, 92,413,570 bytes, `.sha256` file agrees; manifest `04f8218f…19dd`; guard `CLEAN`, `exit=0`; Python 3.10.6, `258 passed, 1 skipped`; plan `exit=0`, 29 `aws` lines, all ending with Region and profile | R15-D1: the count was not stated beforehand |
| 04 | 2026-11-12 | operator | PASS. Both `cp_exit=0`; tarball 92,413,570 and `.sha256` 100 bytes; both `aws:kms` with the R6 `KeyArn` (checked by script), bucket key on, a version each | R15-D1 |
| 05 | — | operator | Not run yet (no `R15_05_check.txt`) | — |

Secret scan over `R15/` after steps 01–04 (agent): `CLEAN`.

## Notes

- **R15-D1. Steps 01–04 ran before round 0 and before points 1–8 were answered.** None of the four
  steps uses a round 0 file, so their evidence stands. Step 03's test list lacks the sender's test file
  and its count was not stated in advance. The agent accepts `258 passed, 1 skipped` as the baseline for
  this list. Step 16 reruns the list with the sender's tests added. Step 04 put the bundle in the deploy
  bucket, as point 2 proposes. If the operator answers point 2 with "no", the bundle is removed at the
  end of R15.
