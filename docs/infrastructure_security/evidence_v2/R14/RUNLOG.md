# R14 — run log

| Field | Value |
|---|---|
| Ticket | R14 (operations and cost) |
| Step sheet | `STEPS.md` |
| Kept by | agent (Claude), from the operator's reports in session |

## Settling

| When (UTC, approx.) | Who | What |
|---|---|---|
| 2026-11-12 | agent | `STEPS.md` written. Points 1–8 wait for the operator; 9–13 for confirmation on review. Round 0 (scripts, cost check, checklist, tests) not started |
| 2026-11-12 | operator | "points 1-8 confirmed, start round 0". Point 6: no HUF/USD rate given, so `budget.json` holds none and the report shows USD only. Points 9–13 still open for review |
| 2026-11-12 | agent | Round 0 done (`10b467bf`): `deploy/aws/scripts/host-lifecycle.ps1` and `.sh`, `tools/aws_cost_check.py`, `deploy/aws/pricing/budget.json` (no approved amount, no rate), `docs/infrastructure_security/aws_od10_upgrade_checklist.md`, `tests/test_aws_host_lifecycle_scripts.py` (50: both forms against a fake CLI, Git Bash for the CloudShell form), `tests/tools/test_aws_cost_check.py` (15). Deviation from the sheet: the profile parameter is `-AwsProfile` (`$Profile` is reserved in PowerShell); stop and teardown evidence names updated in `STEPS.md`. **Stated for step 03:** `217 passed`. **Stated for step 06** (SHA-256 of the workstation files you upload): script `6dee8cb6d65d5a08b665396310b91b47830d0502b215e6ab5fe47d821db94dcc`, template `d21723cbf5bdba274050513b60c7ec998d5b750a4de3b5c034a0382b7303771c` (working copy, CRLF), parameters `3847dadab3d8bdc4507bf6a10f76383577c39e9e01542dc46e526610a4e58f7b`. Not yet run against AWS |
| 2026-11-12 | operator | "points 9-13 confirmed, round 1 done". Points 9–13 (one file per form; CloudShell evidence in `~/r14.tar.gz`; weekly runs in `evidence_v2/ops/cost/<date>/`; tokens per run; the checklist's blanks) confirmed |
| 2026-11-12 | agent | **Expected cost of round 3** (from `R14_05_cost-check/report.json`: running hour 0.154686 USD, stopped hour 0.063916 USD). Plan: two creations, each about 0.75 h running and 0.25 h stopped, so 1.5 h running and 0.5 h stopped in all: **about 0.26 USD**. Ceiling if the sitting runs 4 h with the host running throughout: **0.62 USD**. Tokens: none (the lifecycle scripts and the F7 check call no model). The throwaway bucket, its few requests and the endpoint data processed add under 0.01 USD. All of it draws on the 199.19 USD credits; month-to-date spend would stay under 1.2 USD against the 10 USD budget, below the 85 % alert. Waiting for the operator's go before step 07 |

## Runs

| Step | When (UTC) | Who | Result | Deviation |
|---|---|---|---|---|
| 01 | 2026-11-12 | operator | Pass, checked by script. Free plan `ACTIVE`, expiry `2027-04-19`; credits left 199.19 USD; one budget (10 USD, spend 0.523 USD); notifications ACTUAL 85, ACTUAL 100, FORECASTED 100; caller in `797661577394` | — |
| 02 | 2026-11-12 | operator | Pass, checked by script. No host stack (`exit=254`, does not exist); one endpoint, the R4 S3 gateway, `available`; no instances; no project volumes; base stacks equal to `R12b_fix1_10_base-stacks.json` | — |
| 03 | 2026-11-12 | operator | Pass, checked by script. cfn-lint 1.57.2 clean; template guard CLEAN (6); old-ID guard CLEAN; `217 passed in 139.18s` as stated; plan `exit=0`, 29 `aws` lines all ending `--region eu-north-1 --profile po-r1`, one `delete-stack` naming the host stack | — |
| 04 | 2026-11-12 | operator, agent | Price List API refused all eight items with `AccessDeniedException` (`R14_04_price-list-console.txt`, `exit=0`). Point 4 fallback: the agent downloaded the public eu-north-1 offer files (anonymous HTTPS, no account access) and wrote `deploy/aws/pricing/eu-north-1.json` and `R14_04_agent-offer-extract.json` (13 SKUs, offer versions and URLs). Running hour 0.154686 USD, stopped hour 0.063916 USD (host 0.09077; six endpoints 0.063; 8 GB gp3 0.000916) | Prices read from the offer files, not the API and not the HTML pages. `source_url` is the offer file read; `page_url` names the public page, not read. 730 h/month is recorded as Assumed. Bedrock: the Regional (`eu.` profile) prices per 1M tokens: Opus 4.6 in 5.5, out 27.5; Sonnet 4.6 in 3.3, out 16.5. New test in `tests/tools/test_aws_cost_check.py` (16 tests): the step 03 list now gives `218 passed` |
| 05 | 2026-11-12 11:46 | operator | Pass, checked by script. `exit=0`. Credits 199.19 USD, equal to step 01; Cost Explorer answered: month-to-date usage 0.522633 USD by service, offset by credits; budget 10 USD, spend 0.523 USD; approved HUF `pending`; running hour 0.154686 USD, stopped 0.063916 USD; five creations (`r11-create-01`, `r11-fix1-create-01`, `r11-create-02`, `r12b-create-01`, `r12b-create-02`) with start, end, hours, upper stack cost and Opus 4.6 tokens (14 in / 7 out in two of them, 0.000269 USD each); 13 price rows with URL and date | The price rows cite the offer file read (`source_url`), as recorded at step 04. Cost Explorer shows Bedrock 0.000269 USD, one call's worth, against two calls in CloudWatch: the call at 2026-11-12 00:34 UTC is probably not billed yet (Cost Explorer lags up to 24 h). The one call billed matches the Regional price exactly (14 × 5.5 + 7 × 27.5 per 1M tokens). `.venv-lint` was active, against the sheet's note; no effect on the result |
| 06 | 2026-11-12 11:51 | operator | Pass, checked by script. CloudShell is offered in `eu-north-1` (point 8). `aws-cli/2.39.6`; caller `797661577394`, role `AccountFullAccessRole`; Region `eu-north-1`; the three SHA-256 values equal those stated at round 0; `RESULT=ready` | — |
