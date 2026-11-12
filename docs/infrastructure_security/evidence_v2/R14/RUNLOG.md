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

## Runs

| Step | When (UTC) | Who | Result | Deviation |
|---|---|---|---|---|
