# R15 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-11-12 |
| Step sheet | `STEPS.md` (steps 01–16, points 1–12), run as in `RUNLOG.md` |
| Decisions | `msca-dn-an12-host-run-r15_2026-11-12` (R15-D1–D4, F-R15-1), successor to `msca-dn-an12-offline-bundle_2026-10-16` |
| Stack | `proposal-orchestrator-host`, once. Executed 17:00:54, delete issued 17:19:59, `RESULT=deleted` 17:24:07 UTC |
| Cost | About 0.39 billable host hours, at most 0.06 USD at the running rate. Bedrock: 24 successful calls of Sonnet 4.6 at `max_tokens` 2048, inside the stated 2.05 USD upper bound. Stated before the go: about 0.60 USD planned |
| Secret scan | Agent over `R15/` after steps 01–04 and after steps 06–15: CLEAN |
| Confirmed | Pending: the operator, after step 16 |

Every check below was re-run by the agent on the saved files (`utf-8-sig`), by script.

## Criteria

| Step | Criterion | Evidence | Status | Reason |
|---|---|---|---|---|
| 01 | Plan, budget, notifications, caller | `R15_01_*` | PASS (R15-D1) | FREE / ACTIVE to 2027-04-19, 199.19 USD; 0.567 of 10 USD; three notifications `OK`; account 797661577394 |
| 02 | Nothing left by R14 | `R15_02_*` | PASS (R15-D1) | Host stack absent; only the S3 gateway endpoint; no instance or project volume; base stacks equal R14's; secret unchanged since R8; `bundles/` empty |
| 03 | Freeze, guard, tests, plan | `R15_03_*` | PASS (R15-D1) | Tag and branch `17e32d54`; tarball and manifest as O5; guard CLEAN; `258 passed, 1 skipped`; plan `exit=0`, 29 `aws` lines |
| 04 | Bundle upload | `R15_04_*` | PASS (R15-D1) | 92,413,570 bytes and `.sha256`; SSE-KMS with the R6 key, bucket key on |
| 05 | CloudShell readiness | `R15_05_*` | PASS | Caller and Region correct; three SHA-256 as stated; `RESULT=ready` |
| 06 | PowerShell start, create path | `R15_06_*` | PASS (R15-D4) | Seven `Add`, `c7i-flex.large`; `confirmed=create`; `CREATE_COMPLETE`; seven outputs; `Online` |
| 07 | Fetch from the deploy bucket | `R15_07_fetch.json` | PASS | `Success`; both `cp` exit 0; size and sha256 equal O5; `sha256sum_check=OK` |
| 08 | Install | `R15_08_install.json` | PASS | `install_exit=0`; 17 sums OK; `Python 3.11.16`; 299 files match the manifest |
| 09 | Offline verify with the probe | `R15_09_verify.json` | PASS | `verify_exit=0`; 11 of 11 checks pass; probe `pypi.org:443` unreachable, no fallback needed |
| 10 | DC-33–35 through the launcher | `R15_10_dc33-35.json` | PASS | `launcher_exit=0`; five key names; digest equals R8's (`sha256_matches_template=yes`) |
| 11 | Prepare the receipt draft | `R15_11_prepare.json` | PASS | Assessor Sonnet 4.6 `eu.` profile, not the drafter's Opus (AN1c); temperature 0.0; `max_tokens` 2048; `eu-north-1`; exactly the 13 placeholders |
| 12 | Fill and check the receipt | `R15_12_receipt.json` | PASS | No placeholder left; mode 600; `receipt green` |
| 13 | Converse blind pass and freeze | `R15_13_assess.json`, `R15_13_window.txt` | PASS | `assess_exit=0`; one report; checkpoint 25 lines; two baseline files with size and sha256; receipt hash unchanged; `receipt green` |
| 14 | CloudShell teardown | `R15_14_*` | PASS (R15-D4) | `confirmed=delete`; `RESULT=deleted`; stack absent; only the S3 gateway; no ENI, instance or volume; five base stacks equal step 02 |
| 15 | CloudTrail Converse events (DC-26) | `R15_15_converse-events.json` | PASS with R15-D2, R15-D3 | 26 events. All 26: `eu-north-1`, `AssumedRole`, the runtime role on this host's instance, issuer `RuntimeRoleArn` of R5, the Bedrock endpoint of step 06, Sonnet 4.6. 24 without error, 2 `ThrottlingException`. Run 12 minutes 40 seconds after the pass, not 15 |
| 16 | Tests, guard, scan last | `R15_16_*` | Pending | Expected: `289 passed, 1 skipped`; old-ID guard CLEAN, `exit=0`; secret scan CLEAN, `exit=0` |

## Ticket checklist

| Ticket criterion (`plans/aws_redeployment_tickets.md`, R15) | Status | Evidence |
|---|---|---|
| The bundle's sha256 on the host equals the one recorded at O5 | PASS | Step 07: `9c5351ef…132a` on the host, `sha256sum_check=OK` |
| `runner.offline_bundle verify --probe-no-internet` passes on the host | PASS | Step 09: `record_passed=true`, `no_internet_route` passed on `pypi.org:443` |
| The production configuration is verified on the host (AN12 criterion 1) | PASS | Step 09: production mode `true`, diagnostic level `metadata`, preset `BEDROCK_CONVERSE_EU` to `bedrock_converse`, Region `eu-north-1`. Step 10: the secret's key names and digest through the launcher |
| The synthetic Converse blind pass freezes on the host with a validated receipt (AN12 criterion 3) | PASS, with R15-D3 | Steps 12 and 13: receipt green before and after the pass; baseline frozen. Step 15: every call through the private endpoint as the runtime role |
| The successor decision record is committed | Drafted | `msca-dn-an12-host-run-r15_2026-11-12`; committed with this report |

## Gaps of the AN12 record that R15 closes

| AN12 known gap | After R15 |
|---|---|
| The host's glibc taken as 2.34 (Assumed) | Measured: glibc 2.34; the wheels need 2.28 (step 09) |
| `install_host.sh` has not run on Linux | Ran on Amazon Linux 2023: `install_exit=0` (step 08) |
| Private resolution shows where the name points, not that every call takes that path | For this pass, CloudTrail shows all 26 calls with the Bedrock interface endpoint (step 15). The probe still tests one internet endpoint |

## Findings

- **F-R15-1. The assessor is throttled at the pass's pace.** Two of 26 calls drew a
  `ThrottlingException` within 20 seconds of each other, near the end of the pass. The retry wrapper
  of `harness/judge_factory.py` retried both, so the pass completed. The Converse route is unpaced
  (`paced=False`) and allows 6 retries. A larger pass, such as V14's, may draw more throttles. Before
  V14, check the account's Sonnet 4.6 quota and decide whether the route should be paced.

## Done conditions

- [x] Every step 01–15 above is PASS or carries its recorded deviation.
- [x] The host stack does not exist (`R15_14_host-stack-after.txt`).
- [x] Register v2 rows DC-33–35 updated; DC-26 re-evidenced.
- [x] Decision record `msca-dn-an12-host-run-r15_2026-11-12` drafted.
- [ ] Operator answers R15-D4 (typed-ahead tests) and reruns step 15 (R15-D2).
- [ ] Step 16: PASS.
- [ ] Operator confirms R15.

## Notes for later tickets

- **V14 and V16:** the bundle and its `.sha256` stay under `bundles/msca-dn-freeze-2026-11-12/`
  (point 2). Fetch, install and verify ran in under a minute of host time (steps 07–09).
- **F-R15-1** before V14: check the retry budget and the Bedrock quota.
- **Collector fixes F-R12b-2, -3, -4** remain before the collector's next run. R15 avoided them by
  sending the DC-33–35 script alone.
